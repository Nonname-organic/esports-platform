# ADR-0017: Tournament Detail Immersion

- Status: Accepted
- Date: 2026-07-05
- Deciders: Lead Architect
- Builds on: ADR-0009（Aggregator）, ADR-0011（Activity）, PHASED（LiveProvider/Transport）

## Context

大会詳細ページを VCT / BLAST / FACEIT のような「大会会場を見ている」没入体験へ進化させる。
「今何が起きているか / どこまで進んだか / 次に何を見るか」を一目で理解させたい。
一方で既存 API（Tournament / Bracket / Match）と DB は変更しない（Additive・no migration）。

## Decision

1. **Live は Read Model**（読み取り集約）。`TournamentImmersionService` が既存 Repository を
   read-only で束ね、表示用 DTO を返す。**保存禁止・集計のみ**（ADR-0009 の Aggregator 系譜）。

2. **Tournament 状態は Repository が唯一の取得点**。Service は `TournamentRepository` /
   `MatchRepository` /（完了時）`TournamentReportRepository` 経由でのみ読む。

3. **Live UI は Event に依存しない**。ドメインイベントを購読せず、Read Model をポーリングする。
   将来 `ranking.updated` / `match.result_updated` を購読する SSE/WS へ差し替え可能だが、
   **Consumer（UI Widget）は変更不要**な構造にする（データ源は Transport の差し替えのみ）。

4. **Summary API は保持**。既存 `GET /tournaments/{id}`・Bracket・Match は不変。
   追加は `GET /tournaments/{id}/overview | live | statistics` のみ（additive）。

5. **Widget 化**。Hero / StatusCard / StreamCard / LiveTicker / Upcoming / Statistics /
   Results / Participants は独立コンポーネント。各 Widget は自分の Read Model だけ参照する。

6. **キャッシュ**: Redis `tournament_overview:{id}` / `tournament_statistics:{id}`（TTL30s）、
   `tournament_live:{id}`（TTL10s）。無くても再集約で動作。

7. **Realtime**: 現状は Polling（overview/statistics 60s・live 30s、Visibility 対応）。
   LiveTransport 相当の差し替え点を維持（WebSocket/SSE 化で UI 不変）。

## Stream について

Tournament に stream カラムは無いため、**`tournaments.rules` JSONB（拡張フィールド）**の
`stream_url` を読む。無ければ現在の試合の `matches.stream_url` にフォールバック。DB変更なし。

## Consequences

- Pros: マイグレーション不要・既存API不変・Widget独立・WS/SSE/AI/Broadcast へ拡張可能。
- Cons: 3エンドポイントが matches を各々読む（短TTLキャッシュで緩和）。
- Future: Live Observer / AI Match Prediction / Round・Economy Timeline / OBS Broadcast Overlay。
