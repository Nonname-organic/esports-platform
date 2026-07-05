# ADR-0019: Home Personalization Architecture

- Status: Accepted
- Date: 2026-07-05
- Deciders: Lead Architect
- Builds on: ADR-0009（Aggregator）, ADR-0013（Provider Registry）, ADR-0015〜0018

## Context

ホームを「また来たくなる」パーソナライズ体験へ。おすすめ / AI予測 / 今起きていること /
次の行動を最優先で見せる。既存（Ranking/Achievement/Tournament/Analytics/Player/Live）は不変。

## Decision

1. **Home は Read Model**。`HomeAggregator` が **独立 Provider** を集約するだけ（保存禁止）。

2. **Provider Registry 方式**（ADR-0013 系）。各 Widget は `WidgetProvider` インターフェース
   （`key` + `async build(ctx)`）を実装し、`registry.py` の `PROVIDERS` に登録する。
   **Provider を追加しても `HomeAggregator` は変更不要**（News/Sponsor/Creator/LFP/LFT/Scrim…）。

3. **AI 差し替え点**。`RecommendationProvider` / `PredictionProvider` は初期 RuleBased 実装。
   将来 `OpenAI…` / `Claude…` / `Gemini…` 実装へ **registry の差し替えのみ**で交換可能
   （HomeAggregator=Consumer は変更しない）。

4. **既存の再利用（変更禁止）**:
   - LiveProvider → `StatsService.overview()` を read-only 参照。
   - ActivityProvider → `ActivityService.global_activity()`（公開イベントのみ）。
   - Trending/Prediction → `RankingAggregator`（Team/Player RP）を read-only 参照。

5. **キャッシュ**: Redis `home:{user}:{game}`（TTL60s）、trending/prediction は 120–300s。
   無くても再集約で動作。

6. 追加 API は `GET /home[, /home/recommendations, /trending, /predictions, /live]` のみ。
   既存 API・DB は不変（Additive・no migration）。

## データ方針

- **捏造禁止・実データのみ**（大会/賞金/順位/優勝/MVP/参加率/試合数/ランキング）。
- モック許可は **閲覧人数 / Activity 演出 / AI説明文 / Community Widget** に限定。
- 予測 % は RP からの**規則ベース算出（近似）**であり、実測ML値ではない旨をラベル。

## Consequences

- Pros: マイグレーション不要・既存不変・Provider追加で無限拡張・AI差し替え自由。
- Cons: 複数Read Model合成（短TTLで緩和）。personalizationは現状 game context のみ（拡張余地）。
- Future: News/Sponsor/Creator/Marketplace/LFP/LFT/Scrim/Coach/Academy Provider を追加。
