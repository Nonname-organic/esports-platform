# ADR-0001: domain_events を Event Log 兼 Transactional Outbox として単一テーブル運用

- **Status**: Accepted
- **Date**: 2026-07-04
- **Deciders**: Solo developer (Principal review 反映)

## Context
監査ログ・Player活動・運営タイムラインを統一イベント基盤に載せたい。同時に「emit後に通知/レポートを副作用として発火」する必要があり、素朴に同期実行すると dual-write 問題（本体コミットと副作用の非原子性）で「通知が飛ばない/二重送信」が起きる。
一方、現フェーズは1人開発・数百人・イベント数少。Principalレビューは監査/活動の物理分離と別Outboxテーブルを推奨したが、保守コストが規模に見合わない。

## Decision
`domain_events` を**単一テーブル**とし、**Event Log と Transactional Outbox を兼ねる**。
- Envelope 列（type/version/actor/entity/before/after/metadata/trace_id/correlation_id/idempotency_key/producer/service/occurred_at/visibility）。
- Outbox 列（`dispatched_at` / `dispatch_attempts` / `last_error` / `locked_at` / `locked_by`）。
- 書き込みは `EventService.emit()` のみ、ドメイン処理と**同一トランザクション**で INSERT。
- 既存 worker 内の OutboxRelay が未dispatch行を `FOR UPDATE SKIP LOCKED` で拾い、Dispatcher へ渡す（at-least-once）。
- 監査/活動は `visibility`（internal/public）で**論理分離**。物理分離はしない。

## Consequences
- (+) dual-write を排除（本体と emit が原子的）。別テーブル・別MW不要で最小。
- (+) `visibility` と Repository の `list_audit()/list_activity()` により、将来の物理分離時も Service/Router 無変更。
- (−) 1テーブルにログとキュー状態が同居。行が肥大しうる。
- **Scale Trigger**: `domain_events > 100万件` で audit_logs / activity_feed への物理分離 + 月次パーティション + BRIN を検討（ADR追記予定）。
- **リスク緩和**: before/after に PII を格納しない（user_id 参照）。`visibility` フィルタは Repository に閉じ込め、漏洩面を1箇所に限定。

## Alternatives considered
- 別 `event_outbox` テーブル: 正統だが現規模では保守負債。→ 却下（将来トリガーで移行可能）。
- 3テーブル物理分離（audit/activity/timeline）: premature。→ 却下。
