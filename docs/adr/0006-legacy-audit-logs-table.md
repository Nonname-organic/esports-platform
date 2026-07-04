# ADR-0006: 既存 legacy `audit_logs` テーブルの扱い

- **Status**: Accepted
- **Date**: 2026-07-04
- **Deciders**: Solo developer

## Context
P0-3 実装中に、未使用の legacy テーブル `audit_logs`（モデル `AuditLog`）が存在することが判明した。
- スキーマ: `action / resource_type / resource_id / old_value / new_value / ip_address / user_agent`。
- 参照は `User.audit_logs` relationship のみ。**書き込みコードは 0**（dormant）。
一方、PHASED_ARCHITECTURE.md / ADR-0001 では監査を `domain_events`（`visibility='internal'`）で実現する方針であり、両者が併存する状態になった。

## Decision
- **`audit_logs` は dormant のまま残置する**（削除しない）。後方互換・マイグレーション連鎖の安定を優先。
- **監査の正（Source of Truth）は `domain_events`** とする。新規の監査記録はすべて `EventService.emit()` → `domain_events`（visibility=internal）で行う。
- `audit_logs` への新規書き込みは追加しない。

## Consequences
- (+) 既存スキーマ・マイグレーション履歴を壊さない。空テーブルの残置コストはほぼゼロ。
- (−) 「監査っぽいテーブルが2つある」ことによる一時的な混乱。→ 本ADRで由来と正を明示して解消。
- **将来の整理トリガー**: ADR-0001 の分離トリガー（`domain_events > 100万件`）到達時に、監査を物理テーブルへ投影/移送する。そのタイミングで `audit_logs` の統合または `DROP`（add-only原則の例外として別ADRで判断）を検討する。
- 現時点で `AuditLog` モデル・`User.audit_logs` relationship は残す（削除は後方互換リスク）。

## Alternatives considered
- 即 `DROP audit_logs`: 破壊的変更・後方互換違反。空テーブルを急いで消す利得なし。→ 却下。
- `audit_logs` を監査の正として再利用: スキーマが Envelope（trace/correlation/version/before/after/visibility）と乖離。将来の分離・拡張に不向き。→ 却下。
