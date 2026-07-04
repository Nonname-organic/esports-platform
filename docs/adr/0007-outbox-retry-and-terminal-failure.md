# ADR-0007: Outbox の再試行上限と終端失敗（Terminal Failure）方針

- **Status**: Accepted
- **Date**: 2026-07-04
- **Deciders**: Solo developer

## Context
P0-4（Transactional Outbox）の OutboxRelay は at-least-once で consumer へ fan-out する。dispatch は一時的に失敗しうる（consumer 例外・下流の一時停止等）。無制限にリトライすると、**毒メッセージ（poison event）が永久にリトライされ、キューを塞ぎ、ログ/負荷を増やす**。初期公開フェーズに見合う、シンプルで堅牢な失敗方針が必要。

## Decision
- **再試行上限 `MAX_DISPATCH_ATTEMPTS = 10`** を設ける。
- dispatch 失敗ごとに `dispatch_attempts += 1` し、`last_error` に理由を記録、`locked_at` を解放して次サイクルで再試行する。
- `dispatch_attempts >= MAX_DISPATCH_ATTEMPTS` に達したイベントは **Terminal Failure（終端失敗）** とみなす。
  - Relay の取得クエリを `dispatched_at IS NULL AND dispatch_attempts < MAX` とし、**終端失敗は自動的にキューから外れる**（再試行しない・キューを塞がない）。
  - **新規カラムは追加しない**。終端失敗の定義は `dispatched_at IS NULL AND dispatch_attempts >= MAX`（＝クエリ可能な状態）。
  - 終端到達時に structured log（将来 Sentry）で警告する。
- 手動復旧: 運用者が `dispatch_attempts = 0` にリセットすれば再試行対象へ戻る（原因解消後）。

## Consequences
- (+) 作業量が有界。poison event が隔離され、正常イベントの処理を塞がない。
- (+) 終端失敗は `dispatch_attempts >= MAX AND dispatched_at IS NULL` で一覧・アラート可能。
- (+) スキーマ変更ゼロ（016 の `dispatch_attempts` を利用）。初期フェーズに十分。
- (−) 終端イベントはテーブルに残り続ける（消えない）。件数が増えれば要棚卸し。
- **将来トリガー（Growth Policy）**: 終端失敗が定常的に発生、または運用負荷増で、**専用 DLQ（Dead Letter Queue）+ 自動アラート + 再投入ワークフロー**を導入（SQS Dispatcher 化と同時が自然。ADR-0002 参照）。

## Alternatives considered
- 無制限リトライ: poison event でキュー閉塞。→ 却下。
- 終端時に `dispatched_at=now()` で「成功扱い」: 意味が誤り（送れていないのに dispatched）。監査・再投入で混乱。→ 却下。
- 専用 `failed_at` カラム / status 列の追加: 現フェーズには過剰。`dispatch_attempts` で終端を表現できる。→ 却下（将来 DLQ 導入時に再検討）。
