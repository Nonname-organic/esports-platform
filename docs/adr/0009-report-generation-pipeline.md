# ADR-0009: Report Generation Pipeline（レポート生成の責務分離）

- **Status**: Accepted
- **Date**: 2026-07-04
- **Deciders**: Solo developer

## Context
大会終了レポート（⑩）は「参加数・試合数・優勝・準優勝・MVP・人気Agent/Map・ベストマッチ・勝率」等を集計して生成する。
- 集計は O(試合数) 以上で重い → API リクエスト内での同期生成はタイムアウト源。
- 生成手順（どのイベントで・誰が・どう組み立てるか）が曖昧だと、Player/Season レポート追加時にロジックが重複・分岐する。
- Riot 非依存・ゲーム非依存を維持する必要がある（大会内 matches/results から算出）。

本ADRは、Report 生成パイプラインの**責務分離**を確定する（ADR-0001/0002/0005/0008 を前提）。

## Decision

### 1. 同期生成しない — Event 経由のみ
- Report は **API リクエスト内で同期生成しない**。
- 生成のトリガーは **ドメインイベントのみ**（`tournament.completed` 等）。
  `Service → emit(tournament.completed) → domain_events(dispatch=True) → OutboxRelay → ReportConsumer`。
- 手動再生成も **同じイベントを emit** して行う（同期パスを作らない）。
- API `GET /report` は **生成済みを読むだけ**（未生成=404 / 生成中=202）。

### 2. 責務分離 — Aggregator が集計、Generator は組み立てのみ
- **Aggregator**（集計担当）: DB（matches / results / players / teams）から**数値・ランキングを算出**する。
  - 例: `TournamentReportAggregator.aggregate(tournament_id) -> ReportData(dict)`。
  - N+1 を避け、必要な集計を効率的に行う。ゲーム別項目は分岐可能だがゲーム名をハードコードしない。
- **Generator**（組み立て担当）: Aggregator の出力を受け取り、**保存形（JSON + Markdown）に組み立てる**だけ。
  - 例: `TournamentReportGenerator.generate(target_id)`:
    1. `data = await aggregator.aggregate(target_id)`（集計は Aggregator に委譲）
    2. `markdown = render(data)`（テンプレート組み立て）
    3. `repo.upsert(target_id, data, markdown, version)`（保存）
  - **Generator 自身は集計しない**（DB を数え回さない）。集計の責務は Aggregator ただ一つ。
- **ReportGenerator は interface**（ADR-0005）: `kind`, `generate(target_id)`。
  将来 `PlayerReportGenerator` / `SeasonReportGenerator` を register で追加。各 Generator は
  それぞれの Aggregator を持つ（集計ロジックは Generator ではなく Aggregator 側で増える）。

### 3. 冪等・保存
- `tournament_reports(tournament_id UNIQUE, data JSONB, markdown, version, generated_at)` へ **UPSERT**（冪等）。
- 再生成は version++ で上書き。schema 進化は `data` の版で吸収。
- 生成済み Report は **materialized**（不変）なので Redis キャッシュ不要。
- **ReportConsumer**（EventConsumer）は自前セッションで生成し commit（Relay の Outbox 記録とは別Tx / P1-2 と同型）。

### 4. Analytics 連携（将来）
- `data` JSONB を**安定契約**とし、AXELIA Analytics / PDF 化は data を read-only 参照する（Report 生成に依存させない=疎結合）。

## Consequences
- (+) API は常に軽量（重い集計は worker）。生成手順が「Aggregator→Generator→保存」に固定され、レビューが容易。
- (+) Player/Season レポート追加時、**集計は Aggregator を足すだけ**で Generator の骨格は共通。
- (+) Riot/ゲーム非依存（大会内データから算出）。
- (−) Aggregator と Generator の2層になる（薄い間接）。責務明確化の対価として許容。
- **Scale Trigger**: Report 生成 > 5秒（PHASED）で worker 分散 / 集計の分割。

## Alternatives considered
- Generator が集計も行う（1層）: Player/Season 追加時に集計ロジックが Generator ごとに重複・肥大。→ 却下。
- API 同期生成 + キャッシュ: タイムアウト源。completed の瞬間に重い処理を request で走らせるのは不可。→ 却下。
- 生成を cron ポーリング: completed 検知が遅延・重複。Event 駆動が正確。→ 却下。
