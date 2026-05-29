# Phase 9 — Observability

## Overview

Phase 9 wires three observability pillars into the platform:

| Pillar | Implementation |
|--------|---------------|
| **Logs** | structlog — JSON in production, coloured console in dev |
| **Traces** | OpenTelemetry SDK — spans exported to OTLP-compatible collector |
| **Metrics** | Prometheus client — scraped by Prometheus Operator via ServiceMonitor |

All three are correlated by `trace_id` and `request_id`, which appear in every
log record and can be used to jump from a Grafana alert directly to the relevant
trace in Jaeger or AWS X-Ray.

---

## File Map

```
backend/app/
  core/
    logging.py          structlog configuration (JSON / console renderer)
    telemetry.py        OpenTelemetry TracerProvider + auto-instrumentation
    metrics.py          Prometheus metric definitions (import from here to record)
  middleware/
    observability.py    ASGI middleware: request_id, structured log, Prometheus

infrastructure/
  helm/esports-platform/templates/
    servicemonitor.yaml  Prometheus Operator scrape target (gated by monitoring.enabled)
    prometheusrule.yaml  Alert rules for error rate, latency, queue depth

  monitoring/grafana/dashboards/
    platform.json        Grafana dashboard — HTTP, Workers, Business, k8s panels
```

---

## Structured Logging

`core/logging.py` exports `configure_structlog()`, called once at startup:

```python
configure_structlog(
    log_level=settings.LOG_LEVEL,
    json_logs=settings.ENVIRONMENT != "demo",
)
```

Every log record from any module automatically includes:

| Field | Source |
|-------|--------|
| `timestamp` | UTC ISO-8601 |
| `level` | log level |
| `logger` | module name |
| `request_id` | injected by ObservabilityMiddleware via `contextvars` |
| `method` | HTTP method (bound per request) |
| `path` | request path |
| `trace_id` | OTel current span context (if tracing is active) |
| `span_id` | OTel current span context |

**Usage in application code:**

```python
import structlog
logger = structlog.get_logger()

logger.info("match_result_registered",
            match_id=str(match.id),
            winner_team_id=str(winner.id))
```

The `request_id` and `trace_id` are bound to the contextvars at the middleware
layer — no need to thread them through function arguments.

**Log levels:** controlled by `LOG_LEVEL` env var (default `INFO`). Set `DEBUG`
in dev to see SQLAlchemy queries from the OTel SQLAlchemy instrumentor.

---

## OpenTelemetry Tracing

`core/telemetry.py` exports `setup_telemetry(app, settings)`, called in the
FastAPI lifespan:

```
┌────────────────────────────────────────────────────────────┐
│  FastAPI request                                           │
│    FastAPIInstrumentor  creates span: "GET /api/v1/..."   │
│      SQLAlchemyInstrumentor  child span per query          │
│      RedisInstrumentor       child span per cache op       │
│                                                            │
│  BatchSpanProcessor → OTLPSpanExporter → Collector         │
│    (only if OTLP_ENDPOINT is set in env)                   │
└────────────────────────────────────────────────────────────┘
```

If `OTLP_ENDPOINT` is not set, the tracer provider is created without an exporter
— spans exist in memory and are discarded. This means **zero config needed for
local development**.

**Production setup (EKS):**  
Run AWS Distro for OpenTelemetry (ADOT) Collector as a DaemonSet. Set:
```yaml
# values-production.yaml
env:
  OTLP_ENDPOINT: "http://adot-collector.monitoring.svc.cluster.local:4317"
```

The ADOT Collector can forward traces to AWS X-Ray and metrics to CloudWatch.

---

## Prometheus Metrics

All metrics are defined in `core/metrics.py` and imported per-module:

```python
from app.core.metrics import matches_processed_total

matches_processed_total.labels(game="VALORANT").inc()
```

### Metric Reference

| Metric | Type | Labels | Incremented by |
|--------|------|--------|----------------|
| `http_requests_total` | Counter | method, path, status_code | ObservabilityMiddleware |
| `http_request_duration_seconds` | Histogram | method, path | ObservabilityMiddleware |
| `esports_ws_connections_active` | Gauge | room_type | ws/match.py |
| `esports_worker_jobs_total` | Counter | event_type, status | sqs_consumer.py |
| `esports_sqs_queue_depth` | Gauge | queue | etl_scheduler.py |
| `esports_matches_processed_total` | Counter | game | handlers/match_result.py |
| `esports_analytics_events_total` | Counter | event_type, destination | analytics handler |
| `esports_active_tournaments_total` | Gauge | — | tournament service |
| `esports_app_info` | Info | version, environment | startup lifespan |

The `/metrics` endpoint (excluded from API docs, excluded from rate limiting) is
served directly by the FastAPI app:

```
GET /metrics → prometheus_client.generate_latest()
Content-Type: text/plain; version=0.0.4
```

### Path Normalisation

Prometheus labels must have bounded cardinality. The middleware normalises paths
before labelling:

```
/api/v1/tournaments/3fa85f64-5717-4562-b3fc-2c963f66afa6  →  /api/v1/tournaments/{id}
/api/v1/matches/42/games/1/score  →  /api/v1/matches/{id}/games/{id}/score
```

---

## ObservabilityMiddleware

Added as the **outermost** middleware (last `add_middleware()` call) so it sees
every request including those rejected by rate limiting or CORS:

```
ObservabilityMiddleware
  └── RateLimitMiddleware
        └── CORSMiddleware
              └── FastAPI routes
```

Per request:
1. Generate `request_id` (UUID4)
2. Bind `request_id`, `method`, `path` to structlog contextvars
3. Wait for inner middleware + handler
4. Record `http_requests_total` and `http_request_duration_seconds`
5. Log at INFO (< 400) or WARNING (≥ 400) with `status_code` and `duration_ms`
6. Append `X-Request-ID` response header (visible in browser devtools / API clients)

---

## Health Endpoints

Three endpoints serve different consumers:

| Path | Consumer | What it checks |
|------|----------|----------------|
| `GET /health` | Docker Compose healthcheck, ALB | Always 200 |
| `GET /health/live` | Kubernetes liveness probe | Always 200 if process is alive |
| `GET /health/ready` | Kubernetes readiness probe | DB + Redis reachability |

**Readiness probe design rationale:**  
A liveness failure causes pod restart (costly). A readiness failure only removes
the pod from the Service endpoint slice (traffic stops, but the pod stays up).
If the DB is temporarily unreachable, the pod should stop receiving traffic (readiness)
but not restart (liveness). Using separate endpoints for the two probes enforces
this correctly.

`values.yaml` was updated to use the specific endpoints:
```yaml
readinessProbe:
  httpGet:
    path: /health/ready  # was /health
livenessProbe:
  httpGet:
    path: /health/live   # was /health
```

---

## Kubernetes Monitoring (Prometheus Operator)

Enabled in `values-production.yaml`:
```yaml
monitoring:
  enabled: true
  scrapeInterval: 30s
  alerting:
    enabled: true
```

### ServiceMonitor

`templates/servicemonitor.yaml` tells the Prometheus Operator to scrape
`http://esports-platform-api-svc:8000/metrics` every 30 seconds and add
`environment=production` and `service=esports-platform-api` labels to all metrics.

### PrometheusRule (Alerts)

| Alert | Condition | Severity |
|-------|-----------|----------|
| `APIHighErrorRate` | 5xx rate > 5% for 5 min | critical |
| `APIHighP95Latency` | p95 > 2s for 5 min | warning |
| `APIPodsDown` | available replicas < 2 for 2 min | critical |
| `SQSQueueBacklog` | queue depth > 100 for 10 min | warning |
| `WorkerJobErrorRate` | worker error rate > 10% for 10 min | warning |

Alertmanager routes `critical` alerts to the #ops-alerts Discord channel (same
webhook as ArgoCD deploy notifications). Warning alerts go to #ops-warnings.

---

## Grafana Dashboard

`infrastructure/monitoring/grafana/dashboards/platform.json` — import into Grafana
via **Dashboards → Import → Upload JSON**.

Panels:
- **HTTP row**: Request rate, 5xx error rate, p50/p95/p99 latency
- **Workers row**: SQS queue depth, worker job rate, worker replica count
- **Business row**: Active tournaments, matches processed/min, active WebSockets
- **Kubernetes row**: API available vs desired replicas, app info table

The `$environment` template variable switches between `production` and `mvp` data
by filtering on the `environment` label added by the ServiceMonitor relabelings.

---

## Deployment Checklist

- [ ] Set `LOG_LEVEL=INFO` (or `DEBUG` for verbose) in env
- [ ] Set `IMAGE_TAG` to the deployed image tag (set automatically by CI)
- [ ] Set `OTLP_ENDPOINT` if running an ADOT/Jaeger collector
- [ ] In EKS: set `monitoring.enabled=true` in `values-production.yaml`
- [ ] Install `kube-prometheus-stack` Helm chart in the cluster:
  ```bash
  helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
  helm install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
    -n monitoring --create-namespace
  ```
- [ ] Import `platform.json` into Grafana
- [ ] Configure Alertmanager Discord receiver (reuse ArgoCD webhook URL)
