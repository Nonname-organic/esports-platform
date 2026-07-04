# Notification Event Matrix（通知の Single Source of Truth）

「どのドメインイベントが・誰に・どのカテゴリで・どのチャネルへ通知されるか」の一覧。
`domain_events`（ADR-0001）→ OutboxRelay → **NotificationConsumer** が本Matrixに従って配信する。

- **コード上の SSOT**: `backend/app/notifications/matrix.py`（本ドキュメントと1対1で同期する）。
- 整合性の担保:
  - **Channel Provider**（Browser / Email / Discord）は Matrix の `channels` を実装対象とする。
  - **通知設定（③・ユーザーごとON/OFF）** は Matrix の `category` 単位で判定する。
  - 新イベントの通知化 = Matrix に1行追加（Registry 登録済みが前提 / ADR-0005, 0008）。

---

## 凡例

- **Event**: Event Registry の型（`domain.entity.action`）。dispatch=True のみ通知対象になり得る。
- **Category**: 通知設定の分類（`tournament` / `team` / `scout` / `match`）。ユーザーが category 単位で ON/OFF。
- **Channels**: 配信先。`browser`=アプリ内+WSプッシュ / `discord`=連携ユーザーにDM / `email`=（将来）。
- **Recipients**: 受信者解決ルール（コードの resolver キー）。
- **Status**: `implemented`（P1-2）/ `planned`（将来）。

---

## Matrix

| Event | Category | Channels | Recipients | Status |
|---|---|---|---|---|
| `tournament.registration.approved` | tournament | browser, discord | registered_team（申請チームの全メンバー） | **implemented** |
| `tournament.registration.rejected` | tournament | browser, discord | registered_team | **implemented** |
| `tournament.completed` | tournament | browser, discord | participants（承認済み全チームのメンバー） | planned (P1-3) |
| `tournament.published` | tournament | browser | followers（将来: フォロー機能） | planned |
| `tournament.match.result_updated` | match | browser, discord | match_teams（対戦2チーム） | planned |
| `team.member.added` | team | browser | team_members（本人 + 既存メンバー） | planned |
| `team.owner.changed` | team | browser, discord | team_members | planned |
| `scout.application.received` | scout | browser, discord | recruiter | planned |

> `implemented` 以外は将来行。Registry 側の `dispatch` フラグと本Matrixの `Status` を一致させること
> （通知したいイベントは Registry で `dispatch=True`、通知不要な純監査は `dispatch=False`）。

---

## チャネル仕様

| Channel | 実装 | 備考 |
|---|---|---|
| **browser** | `BrowserChannel` | `notifications` 行を作成 + Redis pub/sub `notifications:{user_id}` で WS プッシュ。**現在実装** |
| **discord** | `DiscordChannel` | `DiscordLink` があるユーザーへ Bot 経由 DM。**現在実装** |
| **email** | `EmailChannel` | **将来**（SES 等）。現在は未設定として skip（no-op + log） |

---

## 通知設定（③）との整合

- 判定順（precedence・将来 ③ 実装時）:
  `global channel OFF > per-entity mute > category OFF > default ON`
- 現フェーズ（③未実装）: `PreferenceResolver.is_enabled(...)` は常に `True`（全ON）を返すスタブ。
  → ③ 実装時、本 Matrix の `category` をキーに JSONB 設定を参照するだけで整合が取れる。

## 冪等・失敗（Outbox 前提 / ADR-0007）

- NotificationConsumer は **冪等であること**を目標とする。現フェーズは `notification_deliveries` による
  厳密な重複排除は未導入のため、Relay 再試行時に稀に重複通知が起こり得る（許容 / 将来 delivery ログで排除）。
- 1チャネルの送信失敗は隔離しログに残す（他チャネル・他受信者を止めない）。
  Consumer 全体が例外を送出した場合のみ Outbox が再試行する。
