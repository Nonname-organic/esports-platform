# Architecture Decision Records (ADR)

重要なアーキテクチャ判断を1件1ファイルで記録する。各ADRは不変（後で覆す場合は新ADRを追加し `Superseded by` で参照）。

フォーマット: Context（背景）/ Decision（決定）/ Consequences（結果・トレードオフ）/ Status。

判断基準は常に [Architecture Growth Policy](../architecture/PHASED_ARCHITECTURE.md#0-architecture-growth-policy設計思想最上位):
**「今必要か？」** と **「スケールトリガーに達したか？」** で決める。

| # | タイトル | Status |
|---|---|---|
| [0001](0001-domain-events-single-table-outbox.md) | domain_events を Event Log 兼 Transactional Outbox として単一テーブル運用 | Accepted |
| [0002](0002-in-process-event-dispatcher.md) | Event Dispatcher は InProcess のみ実装（SQS/Kafka は interface のみ） | Accepted |
| [0003](0003-docker-postgres-with-backup.md) | Docker PostgreSQL を維持し pg_dump→S3 バックアップを追加（RDS/HA は延期） | Accepted |
| [0004](0004-observability-minimal.md) | 可観測性は 構造化ログ + trace_id + Sentry のみ（OTel/Prometheus は延期） | Accepted |
| [0005](0005-provider-registry-pattern.md) | Search / Notification / Report を Provider・Generator・Registry で拡張 | Accepted |
| [0006](0006-legacy-audit-logs-table.md) | 既存 legacy `audit_logs` は dormant 残置・監査の正は domain_events | Accepted |
| [0007](0007-outbox-retry-and-terminal-failure.md) | Outbox 再試行上限(10) と Terminal Failure 方針 | Accepted |
