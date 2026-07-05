# ADR-0016: Season & Rank Badge Architecture

- Status: Accepted
- Date: 2026-07-05
- Deciders: Lead Architect
- Builds on: ADR-0015（Competitive Ranking）, ADR-0009（Aggregator）, ADR-0014（Achievement）

## Context

ADR-0015 で RP・Tier・Leaderboard は完成した。次は Rank を **プロフィール / チームページ /
シーズン** で可視化し、競技継続の動機（今のTier・今季の戦績・過去シーズン）を作る。
Faceit / VALORANT Premier / LoL Ranked のような競技プロフィールを目指す。

## Decision

1. **Rank は Tier SSOT のみ参照**する（`app/rankings/tiers.py` の `tier_for` / `tier_progress`）。
   UI は数値しきい値を持たず、Tier（key/label/color）と progress のみ受け取る。

2. **Badge は Rank から導出**する（`RankBadge` は Tier + Progress のみで描画）。
   Team / Player は**同一 RankCard / RankBadge** を利用（完全共通化）。

3. **Achievement と Ranking は別責務**。
   - Achievement（ADR-0014/Achievement Aggregator）＝「何を成し遂げたか」。
   - Ranking（本ADR）＝「今どれだけ強いか」。相互に import せず、UI で横並び配置するだけ。

4. **Season は時間窓（Materialize 可能な境界を維持）**。
   - 現段階: `all`（全期間）/ `current`（今四半期）/ `previous`（前四半期）を **`app/seasons/`** が生成。
   - `seasons` テーブルは作らない（Additive / no migration）。
   - 将来、確定シーズン（報酬/リセット/確定順位）が必要になれば `seasons` テーブル＋
     materialized snapshot に差し替える。SeasonService の `current()/previous()/list()` が境界。

5. **Season 履歴は ReadOnly Aggregation**。RankingAggregator が season 窓ごとに集計するだけ（保存禁止）。

6. **3層維持**: SeasonService / RankingAggregator（service層・read-only）→ Router。
   既存 Ranking API・Achievement Card・Tier/RP SSOT は不変（後方互換）。
   `/rankings/global` の `season` は `all|current|previous` を受理（値の追加＝後方互換）。

7. **キャッシュ**: `team_rank_card:{id}` / `player_rank_card:{id}`（TTL 15分）。
   将来 `ranking.updated` / `tier.promoted` / `season.finished` イベントで invalidate 可能な構造
   （今回は emit しない）。

## Player RP（Team RP SSOT の再利用）

- Player RP = 所属チームの Team RP 合計 ＋ MVP ボーナス（`MVP_RP`）。
- Win/Loss/Matches は既存 `CareerAggregationService` を再利用。
- 近似（過去の所属変更は現在の membership で近似）。将来 PlayerMatchStats ベースへ精緻化可能。

## Consequences

- Pros: マイグレーション不要・SSOT一貫・Team/Player 共通・Season materialize 余地。
- Cons: season 窓ごとに board 再集計（Redis で緩和）。Player RP は近似。
- Future: Materialized Season / Promotion・Demotion Match / Regional / AI Rank Prediction。
