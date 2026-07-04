# ADR-0011: Activity Feed（公開イベントのタイムライン）

- **Status**: Accepted
- **Date**: 2026-07-04
- **Deciders**: Solo developer

## Context
機能②（Player プロフィール等の「最近の活動」タイムライン）を実装する。P0-3 で `domain_events` に `visibility`（internal/public）を用意済み。監査（internal）と活動（public）は同一テーブルで論理分離している（ADR-0001）。
Activity Feed の実装にあたり、以下を確定する必要がある:
- 公開タイムラインの **読み取り経路**（internal 監査データが漏れない保証）。
- 活動イベントの **payload 方針**（表示に必要な非機密情報をどう持つか）。
- 将来 `activity_feed` へ物理分離する際に **UI/APIを壊さない seam**。

## Decision

### 1. 読み取りは `visibility='public'` に限定・専用経路
- Activity Feed は **`domain_events` の `visibility='public'` のみ**を読む。
- 読み取りは **専用 Repository メソッド `list_activity(...)`**（監査 `list_audit()` とは別メソッド）を経由する。
  `WHERE visibility='public'` を Repository に閉じ込め、**internal(監査) データが公開経路に混入しない**ことを1箇所で保証する。
- Activity 用の payload は **`before`/`after` を返さない**（差分は監査の関心事）。公開に必要な表示情報は `metadata` と `type` から組み立てる。

### 2. 公開イベントは Registry で `visibility=public` を宣言
- どのイベントが公開タイムラインに載るかは **Event Registry（SSOT）で `visibility=public`** により決まる（呼び出し側で切り替えない / ADR-0005, 0008）。
- 現在の public イベント: `tournament.completed`。今後 `player.*`（大会参加/優勝/チーム加入 等）を public として追加していく。
- **表示補助情報は emit 時に `metadata`** へ（非機密のみ・ADR-0008）。例: `{player_name, team_name, tournament_name, placement}`。
  これにより Feed 表示時に N+1 の追加 DB 参照を避ける（metadata 優先、無ければ最小限のフォールバック取得）。

### 3. エンティティ別 Feed / グローバル Feed
- **エンティティ別**（Player/Team の活動）: `entity_type` + `entity_id` で絞る（`ix_events_entity` 利用）。
- **アクター別**（そのユーザーが起こした活動）: `actor_id` で絞る（将来 index 追加をトリガーで検討）。
- 現フェーズは **Player プロフィールの活動タブ**（対象=そのプレイヤー/ユーザーに関する public イベント）を実装する。

### 4. 将来の物理分離への seam（実装しない）
- 100万件超（ADR-0001 トリガー）で `activity_feed`（非正規化・公開専用）へ投影する際:
  - **Service/Router は `list_activity()` にのみ依存**。Repository の実装を差し替えるだけで UI/API は無変更。
  - 投影は Dispatcher に `ActivityProjector` consumer を register して行う（`EventDispatcher` interface / ADR-0002）。今は作らない。
- API レスポンスは **正規化 DTO（ActivityItem）** とし、内部が domain_events でも activity_feed でも同一契約を保つ。

## Consequences
- (+) 公開/監査の分離が Repository 1メソッドに集約 → 情報漏洩面が最小。
- (+) どのイベントが公開かは Registry で一元管理。公開イベント追加は `visibility=public` 登録 + Feed 表示の対応のみ。
- (+) 将来の物理分離が局所差し替えで可能（DTO 契約 + list_activity seam）。
- (−) 表示情報を metadata に持たせる分、emit 側に軽い記述が増える。N+1回避と疎結合の対価として許容。
- (−) `actor_id` インデックスは現状未整備（アクター別 Feed が重くなり得る）。エンティティ別を先行し、必要時に index 追加。

## Alternatives considered
- 監査と同じクエリに visibility フィルタを都度書く: フィルタ漏れで internal 漏洩リスク。→ 却下（Repository に閉じ込める）。
- 最初から `activity_feed` 物理テーブル: premature（ADR-0001）。→ 却下（seam のみ用意）。
- Feed 表示時に毎回 join で名前解決: N+1・結合コスト。→ 却下（metadata 非正規化を優先）。
