# ADR-0018: Player Profile Architecture

- Status: Accepted
- Date: 2026-07-05
- Deciders: Lead Architect
- Builds on: ADR-0009（Aggregator）, ADR-0015/0016（Ranking/Season）, ADR-0011（Activity）

## Context

Player ページを Tracker.gg / FACEIT / HLTV / OP.GG のような世界レベルの競技プロフィールへ。
実績・ランキング・履歴・AI分析までを1ページで完結させる。既存 API/DB は変更しない。

## Decision

1. **Profile は Read Model**。`PlayerProfileAggregator` が既存の
   `CareerAggregationService`（stats/agents/maps）・`RankingAggregator`（rank card）・
   Achievement・Activity を read-only で合成し、表示DTOを返す（保存禁止・ADR-0009系譜）。

2. **AI Analysis は Read Only・Provider化**。`PlayerAnalysisProvider` インターフェースを定義し、
   現段階は `RuleBasedAnalysisProvider`（career統計からルールベース導出）。
   将来 OpenAI / Claude / Gemini 実装へ**差し替え可能**（Consumer=Widget/DTOは不変）。

3. **Rank / Achievement / History は独立 Widget**。各Widgetは自分のRead Modelのみ参照し、
   単体でも SSR/取得できる（疎結合）。

4. **History は Read-Only Aggregation**。選手の所属チームが参加した完了大会の placement を
   report から集約（Ranking/Achievement と同一ロジック系）。

5. **Analytics は Provider 経由**。既存 Analytics/Career は変更せず再利用（reuse-only）。

6. **キャッシュ**: Redis `player_profile:{id}`（TTL15分）、`player_analysis:{id}`（TTL30分）。
   無くても再集約で動作。

7. 追加 API は `GET /players/{id}/profile | analysis | history` のみ（additive）。
   既存 Player / Ranking / Achievement / Activity / Analytics API は不変。

## Consequences

- Pros: マイグレーション不要・既存資産の再利用・AI差し替え自由・Widget疎結合。
- Cons: profile は複数Read Modelを合成（短TTLキャッシュで緩和）。Rule-Based分析は近似。
- Future: AI Match Review / Aim・Heatmap 分析 / Video 解析 / AI Coach / Scouting Score。
  いずれも `PlayerAnalysisProvider` の実装追加、または Widget 追加で拡張可能。
