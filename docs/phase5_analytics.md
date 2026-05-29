# Phase 5 — Data Analytics Infrastructure

## Overview

The analytics pipeline ingests raw match events, aggregates them into query-optimised tables, and caches the results in Redis for low-latency API responses.  It is designed to scale from a single Postgres instance (demo/MVP) to a full data-lake architecture (production) with no changes to the application layer.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│  Match API  (FastAPI)                                               │
│   POST /matches/{id}/result                                         │
│     └─ MatchService.register_result()                               │
│           ├─ DB: update Match.status = completed                    │
│           ├─ SQS: publish match_result_registered                   │
│           └─ DB: INSERT analytics_events (raw event)                │
└─────────────────────────────┬───────────────────────────────────────┘
                              │  SQS long-poll (WaitTimeSeconds=20)
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  SQS Worker  (sqs_consumer.py)                                      │
│   match_result_registered event                                     │
│     ├─ handle_match_result()      → RankingService.update_after_match│
│     └─ handle_analytics_aggregation()  ← Phase 5 (NEW)             │
│           ├─ AnalyticsRepository.upsert_team_stats_delta()          │
│           ├─ AnalyticsRepository.upsert_player_stats_delta()        │
│           ├─ AnalyticsRepository.upsert_map_stats_delta()           │
│           ├─ AnalyticsRepository.upsert_composition_stats_delta()   │
│           └─ RedisCache.delete_pattern()   (cache bust)             │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│  ARQ Scheduler  (etl_scheduler.py)  — nightly cron                 │
│   02:00 UTC  daily_aggregation                                      │
│     └─ Full rebuild of agg_player_stats for yesterday               │
│         (delete-and-reinsert from PlayerMatchStats JOIN Match)      │
│   03:00 UTC  daily_s3_export                                        │
│     └─ Batch-read unprocessed analytics_events                      │
│         └─ NDJSON → S3 (year/month/day partition)                  │
│             └─ mark events processed=true                           │
└─────────────────────────────────────────────────────────────────────┘

                    Analytics API  (FastAPI)
                      GET /analytics/players/{id}
                      GET /analytics/maps
                      GET /analytics/compositions
                      GET /analytics/tournaments/{id}/summary
                           │
                    Redis cache (30 min – 1 h TTL)
                           │  cache miss
                    Aggregate tables
                      agg_player_stats
                      agg_team_stats
                      agg_map_stats
                      agg_composition_stats
                           │  tables empty (demo/seed)
                    Realtime fallback (query PlayerMatchStats directly)
```

---

## ETL Strategy: Two-layer design

| Layer | Trigger | Latency | Scope |
|-------|---------|---------|-------|
| **Incremental** (`handle_analytics_aggregation`) | SQS event, immediately after match result | < 1 s | Single match delta |
| **Full rebuild** (`daily_aggregation`) | ARQ cron, 02:00 UTC | ~minutes | All matches for yesterday |

The incremental layer keeps stats current throughout the day.  The nightly rebuild acts as a correctness safety net, overwriting any drift caused by out-of-order events, retries, or bugs.

---

## Data Flow: Incremental Handler

```
SQS body (match_result_registered)
  ├─ team_stats_delta  ×2 teams  ×2 period_types (DAILY, TOURNAMENT)
  ├─ map_stats_delta   ×N maps   ×2 scopes (global, tournament)
  ├─ player_stats_delta ×M players ×2 period_types
  └─ composition_stats_delta ×K unique compositions ×2 scopes
```

All upserts use a **select-then-update-or-insert** pattern (no `ON CONFLICT` clause) because the application logic must compute running averages incrementally (Welford's online algorithm for mean, streak counting for team performance).

---

## Aggregate Tables

### `agg_player_stats`
Unique key: `(player_id, game, period_type, period_date, tournament_id)`

| Column | Notes |
|--------|-------|
| `games_played / games_won` | From DAILY incremental or nightly rebuild |
| `total_kills / deaths / assists` | Summed per period |
| `avg_kda` | Welford online mean: no need to store all individual KDAs |
| `agent_breakdown` | JSONB `{"Jett": {"games": 10, "wins": 7, "kda_sum": 25.3}}` |

### `agg_map_stats`
Unique key: `(map_id, game, tournament_id, calculated_date)`

Tracks attack/defense side win rates — useful for game balance analysis and
seeding map picks.

### `agg_composition_stats`
Unique key: `(game, tournament_id, map_id, composition, calculated_date)`

`composition` is a **sorted** array of agent/hero names stored as JSONB.
Sorting at write time (`sorted(agents)`) means `["Jett","Sage"]` and
`["Sage","Jett"]` map to the same row.

---

## S3 Export

### Why export to S3?
Postgres `analytics_events` is an append-only raw event log. It grows without
bound and is not optimised for ad-hoc analytical queries across millions of rows.
S3 + Athena (serverless SQL over Parquet) costs < $5/month at 10 M events/day.

### Partition layout
```
s3://<bucket>/analytics/raw/
  year=2025/month=01/day=15/
    3f2a1b4c-....jsonl    ← NDJSON (one JSON object per line)
    9d8e7f6a-....jsonl
```

Athena and AWS Glue read this layout natively with partition projection,
requiring no schema registry update when partitions are added.

### Format choice: NDJSON vs Parquet
NDJSON is chosen for the MVP because:
- No schema evolution friction (adding payload fields is transparent)
- Human-readable for debugging
- Directly queryable by Athena

At production scale (> 10 GB/day), a Glue job converts NDJSON → Parquet with
Snappy compression, reducing storage cost by ~10× and scan cost by ~20×.

---

## Cache Invalidation

After each incremental aggregation the following cache keys are busted:

| Key pattern | Reason |
|-------------|--------|
| `cache:map:stats:{game}` | Map pick/win rates changed |
| `cache:composition:{game}:*` | Composition win rates changed |
| `cache:ranking:tournament:{id}` | Rankings updated by ranking service |
| `cache:player:{id}:stats:*` | Per-player stats changed |

TTLs are conservative (30–60 min for live data, 1 h for map/comp) because
the nightly rebuild guarantees eventual consistency even if a bust is missed.

---

## Scaling Path

### Phase 1 — Demo ($0 additional cost)
- Single Postgres; agg tables co-located with app data
- S3 export disabled (`S3_BUCKET_NAME=""`)
- Realtime fallback provides stats from `PlayerMatchStats` directly

### Phase 2 — MVP ($5–15/month additional)
- Enable S3 export; set up Athena + Glue crawler
- Athena costs ~$5/TB scanned; < $1/month at MVP scale
- ARQ scheduler runs on the existing Worker container

### Phase 3 — Production ($50–200/month additional)
- Move agg tables to a read replica (offload analytics queries from primary)
- Glue ETL: NDJSON → Parquet (daily batch, triggered by CloudWatch Events)
- Consider Redshift Serverless for complex cross-game trend analysis
- OpenSearch for full-text player/team search with analytics aggregation

---

## Key Design Decisions

**Why not Celery?**
ARQ uses `asyncio` natively and runs within the same async Python process.
Celery requires a separate sync worker process with `gevent` or `eventlet`
to achieve concurrency.  At the scale of this platform (< 100 matches/day)
the complexity overhead of Celery is not justified.

**Why running averages instead of raw sums?**
Storing `avg_kda` as a running mean avoids reading all historical records to
compute an average at query time.  Welford's algorithm is numerically stable
and incremental: `mean += (new_val - mean) / n`.

**Why delete-and-reinsert in the nightly rebuild?**
`UPDATE ... SET` on computed aggregates requires knowing the previous state.
A fresh `INSERT` from a deterministic SQL GROUP BY is easier to reason about,
simpler to backfill, and avoids partial-update bugs if the job is interrupted.

**Why JSONB for `agent_breakdown` instead of a separate table?**
The breakdown is always read as a unit (never filtered on individual agents
at the DB level) and varies per game (VALORANT has agents, LoL has champions).
JSONB avoids a schema change per game and fits the read pattern.
