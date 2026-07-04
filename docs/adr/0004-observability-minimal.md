# ADR-0004: 可観測性は 構造化ログ + trace_id + Sentry のみ（OTel/Prometheus は延期）

- **Status**: Accepted
- **Date**: 2026-07-04
- **Deciders**: Solo developer (Principal review 反映)

## Context
公開前・本番前提のため、障害の可視性は最低ライン必須。Principalレビューは OpenTelemetry(trace) + Prometheus/CloudWatch(metrics) + Sentry を推奨したが、フルスタックの可観測性基盤（収集・保存・ダッシュボード・アラート）は運用者1人には過剰で、導入・維持コストが便益を上回る。

## Decision
現フェーズで導入するのは以下 **3点のみ**:
1. **構造化ログ**（既存の structlog 相当を継続）。
2. **trace_id**（リクエストミドルウェアで生成/伝播し、ログと Event Envelope に付与）。
3. **Sentry**（FE/BE の例外収集。trace_id を紐付け）。

**OpenTelemetry / Prometheus / Grafana は導入しない**（将来対応）。

## Consequences
- (+) 障害検知・原因追跡の最低ラインを低コストで確保。trace_id で 1リクエスト→複数イベント/通知を追える。
- (+) trace_id は Event Envelope が保持するため、**Envelope 実装(P0-2)と同時に入れるのが自然**。
- (−) メトリクス時系列（p95/スループット/飽和）の自動可視化は無い。当面は Sentry + ログ + 手動確認で代替。
- **Scale Trigger**: SLO 運用が必要になった段階、または障害頻度増で OpenTelemetry(trace) + Prometheus/CloudWatch(metrics) + Grafana を導入。

## Alternatives considered
- OTel フル導入: 過剰。全コード横断の計装コスト。→ 却下（将来）。
- 何も入れない: 公開前に障害盲目は不可。→ 却下。
