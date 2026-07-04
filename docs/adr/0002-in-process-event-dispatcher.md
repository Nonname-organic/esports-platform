# ADR-0002: Event Dispatcher は InProcess のみ実装（SQS/Redis/Kafka は interface のみ）

- **Status**: Accepted
- **Date**: 2026-07-04
- **Deciders**: Solo developer (Principal review 反映)

## Context
OutboxRelay が拾ったイベントを consumer（通知・レポート等）へ fan-out する必要がある。将来的には SQS / Redis Stream / Kafka による Event Bus 化が視野に入るが、現フェーズ（数百人・イベント少）でメッセージングMWを導入すると運用対象（可用性・監視・DLQ）が増え、1人運用に見合わない。

## Decision
`EventDispatcher` を **Protocol（interface）** として定義し、現在は **`InProcessDispatcher` のみ実装**する。
- OutboxRelay は `EventDispatcher` interface にのみ依存する。
- consumer は `EventConsumer` Protocol（`handles(type)` / `handle(envelope)`、**冪等必須**）。register で追加。
- 1 consumer の失敗は隔離し全体を止めない（失敗は last_error / Sentry）。

将来の `SqsDispatcher` / `RedisStreamDispatcher` / `KafkaDispatcher` は **interface だけ用意し実装しない**。差し替え時は Dispatcher 実装追加と Relay の向き先変更のみで、呼び出し側は無変更。

## Consequences
- (+) 追加インフラゼロ。既存 worker プロセスで完結。
- (+) 差し替え点が interface 1箇所に限定 → 将来の Event Bus 化が局所的。
- (−) InProcess ゆえ worker プロセス内でのみ fan-out（クロスサービス配信不可）。現フェーズでは不要。
- **Scale Trigger**: Outbox 未処理滞留 `> 1000 or 5分`、または外部連携/WS同時500超で SQS Dispatcher へ差し替えを検討。

## Alternatives considered
- 最初から SQS: 過剰。運用対象増。→ 却下。
- Celery/Redis Queue 導入: 既存に SQS/worker があり重複。→ 却下。
