# ADR-0005: Search / Notification / Report を Provider・Generator・Registry で拡張

- **Status**: Accepted
- **Date**: 2026-07-04
- **Deciders**: Solo developer (Principal review 反映)

## Context
検索対象（Team/Player/Tournament/Match）、通知チャネル（Browser/Email/Discord）、レポート種別（Tournament）は今後必ず増える（LFP/LFT/News/Analytics 検索、Webhook/Push/LINE チャネル、Player/Season レポート）。固定実装だと追加のたびに core を改修し、変更量が線形に増える。

## Decision
拡張が予想される3領域に **Provider / Generator + Registry パターン**を採用する。

- **Search**: `SearchProvider` Protocol（`name`, `weight`, `search(q,limit)->list[SearchHit(score0..1,...)]`）。`SearchRegistry` に register。現在 4 provider。
- **Notification**: `ChannelProvider` Protocol（`send(recipient,message)->DeliveryResult`）。現在 browser/email/discord。
- **Report**: `ReportGenerator` Protocol（`kind`, `generate(target_id)`）。現在 Tournament。

追加時の変更量 = **Provider/Generator 1ファイル + register 1行**（core・API 契約・フロント 無改修）。各 provider は「公開エンティティのみ返す」等の責務を自身に閉じ込める。

## Consequences
- (+) 拡張が O(1)。LFP/LFT/News/Analytics、Webhook/Push/LINE、Player/Season レポートを register で追加。
- (+) 検索実装（pg_trgm）やチャネル実装が provider 内に隠蔽され、将来 PGroonga/ES へ **Strategy 差し替え**が局所化。
- (−) 間接層が増え、単純な1機能には僅かなボイラープレート。拡張性の対価として許容。
- **Scale Trigger**: 検索 300ms超/日本語精度不足で SearchProvider を PGroonga 実装へ差し替え（core 不変）。

## Alternatives considered
- 固定 if 分岐 / 直書き: 追加のたび core 改修。→ 却下。
- プラグイン動的ロード: 現規模では過剰。静的 register で十分。→ 却下。
