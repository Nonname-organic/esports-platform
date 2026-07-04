# ADR-0012: Audit Log Viewing（監査ログの閲覧）

- **Status**: Accepted
- **Date**: 2026-07-04
- **Deciders**: Solo developer

## Context
機能①の監査ログ閲覧UIを実装する。監査データは `domain_events`（`visibility='internal'`）に蓄積済み（ADR-0001, 0008）。Activity Feed で `list_audit()`（internal限定）も用意済み（ADR-0011）。
監査は「誰が・いつ・何を・before→after・IP」を含み、**機密性が高い**。閲覧UIの追加で以下を確定する必要がある:
- **誰が監査を見られるか**（全体 / エンティティ別の権限境界）。
- **どの情報を返すか**（before/after/IP を誰まで出すか）。
- Activity Feed（public）と混同しない読み取り経路。

## Decision

### 1. 読み取りは `list_audit()`（internal限定）のみ
- 監査UIは Activity（public）と**別経路**。必ず `EventRepository.list_audit()`（`visibility='internal'`）を使う。
- 公開フィード用 `list_activity()` と交差させない（漏洩面を分離 / ADR-0011）。

### 2. 権限境界（誰が見られるか）
| スコープ | 閲覧可能者 | API |
|---|---|---|
| **全体監査**（全 internal イベント） | **Admin のみ** | `GET /admin/audit` |
| **Team 監査**（entity_type=team, entity_id=team_id） | その Team の **owner/captain** または Admin | `GET /teams/{id}/audit` |
| **Tournament 監査**（entity_type=tournament, entity_id） | その大会の **organizer** または Admin | `GET /tournaments/{id}/audit` |
- 権限は既存の依存性（`AdminUser` / owner・organizer チェック）を再利用する。無権限は 403。

### 3. 返す情報（AuditLogItem DTO）
- 返却は **正規化 DTO**（内部が domain_events でも将来 audit_logs 分離でも同一契約）:
  `id / action(=type) / actor_id / actor_name / actor_ip / entity_type / entity_id / before / after / summary / created_at`。
- **`before`/`after`/`actor_ip` は監査スコープの権限保持者にのみ返す**（上記②の閲覧可能者）。
  - 監査は元々 internal 権限者しか到達できないため、DTO 全体を権限者向けとする（公開経路には出さない）。
- **PII は元データに入れていない**（ADR-0008: before/after は user_id 参照）。DTO も生メール等を持たない。
- `actor_name` は表示用に actor_id → username を解決（N+1 回避のため一括取得 / selectinload）。

### 4. ページング・フィルタ
- カーソル or offset ベース（既存踏襲）。フィルタ: `action(type)` / `actor_id` / 期間（将来）。
- 既存インデックス `ix_events_entity (entity_type, entity_id, created_at)` / `ix_events_visibility (visibility, type, created_at)` を利用。

### 5. 改ざん防止・保持（現フェーズは方針のみ）
- `domain_events` は **追記のみ**（更新/削除しない）＝実質 WORM。UI から編集手段を提供しない。
- ハッシュチェーン等の厳密な改ざん検知は将来（監査要件が発生した段階）。
- 保持: ADR-0001 の分離トリガー（100万件超）到達時に audit_logs へ投影 + 保持ポリシーを定義。

## Consequences
- (+) 監査/公開の経路が完全分離（list_audit / list_activity）。権限境界が明確（Admin / owner / organizer）。
- (+) DTO 契約により、将来 audit_logs 物理分離時も UI/API 無変更。
- (+) N+1 を actor 一括解決で回避。
- (−) 監査 UI は internal 権限者専用のため、一般ユーザーには不可視（意図通り）。
- (−) 期間フィルタ・改ざん検知は将来。現フェーズは最小の閲覧・フィルタに限定。

## Alternatives considered
- 監査を Activity と同一エンドポイントで visibility 切替: フィルタ漏れで internal 漏洩。→ 却下（別経路）。
- before/after を一般公開: 機密漏洩。→ 却下（権限者のみ）。
- 生 domain_events を返す: 内部表現が API に固定化。→ 却下（DTO 契約）。
