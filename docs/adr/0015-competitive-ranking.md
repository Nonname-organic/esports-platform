# ADR-0015: Competitive Ranking（RP + Tier / 読み取り集約）

- Status: Accepted
- Date: 2026-07-05
- Deciders: Lead Architect

## Context

既存の `rankings` テーブルは**大会内**の順位（team×tournament）のみを持つ。
プロダクトには「シーズン制・ランクバッジ・実績」を含む**横断的な競技ランキング**が必要。
一方で Architecture Growth Policy（Additive / 今必要なものだけ / 過剰設計禁止）に従い、
新しい重い書き込み経路や大規模マイグレーションは避けたい。

## Decision

競技ランキングを **読み取り専用の集約レイヤ** として実装する（ADR-0009 の Aggregator 系譜）。

1. **Ranking Point (RP) は既存データから算出**する。新テーブルを作らない（Additive・no migration）。
   出典: 完了大会（`tournaments.status=completed`）＋ `TournamentReport.data`（champion/runner_up/standings）。
   Report が無い大会は `TournamentReportAggregator` でオンザフライ集計にフォールバック。

2. **RP 付与式（SSOT: `app/ranking/tiers.py` の `PLACEMENT_RP`）**
   - champion: 1000 / runner_up: 600 / top4: 300 / 参加（standings掲載）: 100
   - チームのシーズンRP = 対象大会の placement RP の合計。

3. **Tier / Badge は RP のしきい値で決まる純関数（SSOT: `tier_for(rp)`）**
   - Bronze(0) / Silver(1000) / Gold(2500) / Platinum(5000) / Diamond(9000) / Master(15000) / Grandmaster(25000)
   - Provider/DTO は tier 構造へ直接依存せず、必ず SSOT 経由（ADR-0010 と同じ思想）。

4. **Season は「時間窓」で表現**する（テーブルなし）。
   - `all`（全期間）と `current`（現在の四半期: Q1–Q4）を提供。大会の `end_at` で窓判定。
   - 将来、正式なシーズン（賞金/報酬/確定順位）が必要になったら `seasons` テーブルを追加し、
     この集約を materialized snapshot に置き換える（下記「将来」）。

5. **3層維持**: `RankingAggregator`（service層・read-only・DB書き込み禁止）→ Router。
   既存 `RankingService`/`/rankings/tournaments/{id}` は不変（後方互換）。

6. **キャッシュ**: Redis `cache:ranking:global:{game}:{season}`（TTL 15分）。無くても再集約で動作。

## Consequences

- Pros: マイグレーション不要・後方互換・既存Report基盤を再利用・tier/RP が SSOT。
- Cons: 大会数に対して O(N) の Report 読み取り（キャッシュで緩和）。厳密な「確定順位/報酬」は持たない。
- Player ランキングは Phase 2（本ADRの team 版と同じ tier SSOT を流用）。

## Future（世界レベルへの発展点）

- `seasons` テーブル＋シーズン確定スナップショット（materialized `season_rankings`）。
- Event 経由の増分更新（`tournament.completed` → RP再計算 → `ranking.updated`）。
- Player RP（PlayerMatchStats / MVP / 所属チーム成績の重み付け）。
- 減衰（時間経過でのRPディケイ）・不正対策・Elo/Glicko 併用。
