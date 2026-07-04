# ADR-0008: Event Emission Policy（イベント発火の共通ルール）

- **Status**: Accepted
- **Date**: 2026-07-04
- **Deciders**: Solo developer

## Context
P1-1 以降、Team / Tournament / Player / Match などへ `EventService.emit()` を広げていく。
発火場所・命名・タイミング・payload がブレると、監査/活動/通知の一貫性が崩れ、5年運用で技術的負債になる。
本ADRは、以降すべての emit に適用する**共通ルール**を定める（ADR-0001/0005/0007 を前提）。

## Decision

### 1. 発火場所（WHERE）— Service 層でのみ emit する
- emit は **Service 層のメソッド内でのみ**呼ぶ。Router / Repository / Model からは呼ばない。
  - Router は薄く保つ（HTTP 変換のみ）。Repository は永続化のみ。ドメインの「事実」を知るのは Service。
- **ドメイン状態の変更（repo.create/update/delete）と同一トランザクション・同一 AsyncSession** で emit する。
  ```python
  # Service 内
  team = await self._repo.update(team, **updates)
  await EventService(self._db).emit(EventEnvelope.build(...))
  # commit は Service/Router の既存フローが一括で行う（原子性 = ADR-0001）
  ```
- Service は **`self._db`（リクエストと同じセッション）を EventService に渡す**。別セッションを作らない。

### 2. タイミング（WHEN）— 成功後・コミット前
- emit は「その操作が**成功した後**（バリデーション・権限・repo反映が完了）」に呼ぶ。失敗パスでは emit しない。
- emit は **commit の前**（同一 Tx 内）。ドメイン変更がロールバックされたらイベントも消える＝**嘘のイベントを残さない**。
- 「起きた事実」を記録する。未来形・命令形のイベントは作らない（例: `approve_requested` ではなく `registration.approved`）。

### 3. 命名（NAMING）— `domain.entity.action`・過去形
- Registry の命名規則に従う: `<domain>.<entity>.<action>`（小文字・ドット区切り）。
- action は**過去形/完了を表す語**を優先（`created` / `updated` / `added` / `removed` / `approved` / `published` / `completed`）。
- 例外的に状態遷移は `status.changed` のように名詞化してよいが、**必ず Registry に登録**してから使う（野良イベント禁止 = emit が UnknownEventError）。
- 1つのビジネス操作 = 1イベントを基本とする。細かすぎる分割・重複発火をしない。

### 4. Payload（WHAT）— before/after の規約
- `before` / `after` には**変化した意味のあるフィールドのみ**入れる（全カラムのダンプ禁止）。
  - 例: ステータス変更 → `before={"status": old}`, `after={"status": new}`。
- **PII を格納しない**（メール・電話等）。人は `user_id` / `actor_id` で参照する（ADR-0001）。
- 大きなオブジェクト（画像バイナリ等）を入れない。URL/keyの参照に留める。
- 表示補助情報（チーム名など非機密）は `metadata` に入れてよい（activity表示の非正規化用）。

### 5. actor / visibility / dispatch — Registry と Context に委ねる
- `actor_id` / `actor_ip` / `trace_id` / `correlation_id` は **RequestContext から自動補完**（`EventEnvelope.build` が担当）。呼び出し側で手渡ししない。
- **system / bot 起因**（worker の自動遷移・Discord Bot 経由）は `actor_type` を明示し `actor_id=None`。
- `visibility` と `dispatch` は **Registry（SSOT）が唯一の決定者**。呼び出し側で指定しても emit が Registry 値で上書きする。
  - 監査のみ = `visibility=internal, dispatch=False`。公開活動/副作用あり = Registry で個別定義。

### 6. 冪等・失敗の非伝播
- 再実行が起こり得る操作（再試行・べき等API）には `idempotency_key` を付与する。
- emit の失敗は**ドメイン操作を壊してはならない**が、本方針では emit は同一 Tx なので「emit が例外 = 操作もロールバック」を許容する（未登録イベント等は開発時に検出すべきバグ）。運用時の consumer 失敗は Outbox 側（ADR-0007）で吸収する。

### 7. 二重発火の防止
- 同じ状態変化で複数の Service 経路がある場合、**イベントは1箇所（最も内側のドメイン確定点）でのみ発火**する。
- Router で「公開」→ Service.change_status のように、下位 Service が既に emit するなら上位で重ねて emit しない。

## Consequences
- (+) 発火場所・命名・タイミングが統一され、監査/活動/通知が一貫。レビューが「Registry登録 + Service内emit + 同Tx + 過去形」の4点チェックで済む。
- (+) 新エンティティへの拡張が機械的（同じ型に沿って追加するだけ）。
- (−) Service に emit 呼び出しが増える（薄いボイラープレート）。→ 一貫性の対価として許容。将来、状態変更を検知して自動 emit する仕組み（SQLAlchemy events 等）も検討可能だが、現フェーズは明示 emit を優先（可読性・意図の明確さ）。

## Checklist（PR時に確認）
1. イベント型は Registry に登録済みか（命名 `domain.entity.action`・過去形）。
2. emit は **Service 内**・ドメイン変更と**同一 Tx**か。
3. **成功後**に呼んでいるか（失敗パスで発火していないか）。
4. `before/after` は差分のみ・**PII なし**か。
5. system/bot は `actor_type` を明示しているか。
6. 二重発火していないか。
