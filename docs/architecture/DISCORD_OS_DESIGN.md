# Discord Tournament Operating System — 設計書

> 目的: **大会参加者がDiscord上だけで大会進行に必要な操作を完結できる**こと。
> 既存のFastAPI/PostgreSQL/Redis/SQS基盤・RBAC・データモデルを崩さず、Discord Botを「第2のクライアント」として全機能に到達させる。

---

## 1. アーキテクチャ

```
┌────────────────────────────── Discord ──────────────────────────────┐
│  Slash Commands (Autocomplete / Modal / Select / Button)              │
└───────────────┬──────────────────────────────────────────────────────┘
                │ interaction
        ┌───────▼────────┐   ① Discord側RBAC (即時UXゲート: Discordロール)
        │  Discord Bot   │   ② Backend RBAC (権威: DiscordLink→Userのrole/所有権)
        │  (discord.py)  │
        │  cogs / core / │── command metrics / error log ─┐
        │  ui / services │                                 │
        └───────┬────────┘                                 │
                │ HTTP (Bearer=user JWT  or  X-Bot-Secret) │
        ┌───────▼──────────────────────────────────────────▼──────────┐
        │                     FastAPI Backend                          │
        │  既存: /tournaments /matches /teams /players /scout          │
        │        /analytics /notifications /career /riot               │
        │  新規: /bot/*  (service-auth + on-behalf-of resolver)        │
        └───────┬──────────────────────────┬───────────────────────────┘
                │                          │ publish (SQS/Redis)
        ┌───────▼────────┐         ┌───────▼────────┐
        │  PostgreSQL    │         │  Event Queue   │── setup_tournament
        │  (+ 008 migr.) │         │  (SQS / Redis) │── create_match_channel
        └────────────────┘         └───────┬────────┘── archive_match_channel
                                           │
                                  Bot event_consumer (自動チャンネル生成/Archive)
```

### 認証モデル（最重要）

Botは2系統でAPIに到達する:

| 系統 | ヘッダ | 用途 | RBAC |
|------|--------|------|------|
| **公開読み取り** | なし | tournament/bracket/player/team/career/analytics/scout の参照 | 不要（公開API） |
| **on-behalf-of（代理実行）** | `X-Bot-Secret: <BOT_API_TOKEN>` + `X-Discord-User-Id: <id>` | 書き込み・操作系（report-result, start/end, advance, check-in, dispute…） | バックエンドが `DiscordLink → User` を解決し、**そのユーザーの実権限**で実行 |

→ 静的トークンで“なりすまし”できないよう、`X-Bot-Secret` は **Bot↔Backend間の共有秘密**（SSM/環境変数）。実際の権限判定は常に解決済みのプラットフォームUser基準。**Playerロールのユーザーが `/start-tournament` をBot経由で叩いても、バックエンドが拒否する**（多層防御）。

---

## 2. RBAC設計

### ロール対応

| Discordロール (テンプレ生成) | プラットフォーム `UserRole` | 説明 |
|---|---|---|
| Admin | `admin` | 全操作 |
| Organizer | `organizer` / `team_manager` | 大会運営 |
| Captain | `player` (かつ team の `captain`) | チーム運営・結果報告 |
| Player | `player` | 自分の参加操作 |
| Spectator | `viewer` / 未連携 | 閲覧のみ |

### 2層ゲート

1. **Discord側 (`core/rbac.py`)**: コマンドに必要な最小Discordロールを宣言 (`@requires(Role.ORGANIZER)`)。Discordロール or `guild_permissions` で即判定し、足りなければ ephemeral で拒否（API往復なし=高速UX）。
2. **Backend側 (`/bot/*` + 既存deps)**: 実データ変更は必ずバックエンドのRBAC（`OrganizerUser`等 + 所有権チェック）を通る。Discordロールは詐称可能なので**権威はバックエンド**。

### コマンド×ロール マトリクス（抜粋。完全版は §3 Command Tree の権限列）

| カテゴリ | Spectator | Player | Captain | Organizer | Admin |
|---|---|---|---|---|---|
| 参照系 (info/stats/career/bracket/scout/leaderboard) | ✅ | ✅ | ✅ | ✅ | ✅ |
| 自分の操作 (check-in/open-to-work/my-matches/apply) | – | ✅ | ✅ | ✅ | ✅ |
| チーム運営 (invite/remove/promote/report-result/veto) | – | – | ✅ | ✅ | ✅ |
| 大会運営 (create/start/end/advance/regenerate/check-in-all) | – | – | – | ✅ | ✅ |
| モデレーション (warn/mute/kick/forfeit/reopen) | – | – | – | ✅(一部) | ✅ |

---

## 3. Command Tree（全コマンド / 必要ロール / 連携先）

凡例: 🟢=既存公開API / 🔵=新 `/bot/*` 経由(on-behalf) / 🟡=Discordネイティブ操作 / ⚪=Bot内ロジック

### Tournament
| Command | Role | 連携 |
|---|---|---|
| `/create-tournament` | Organizer | 🔵 setup publish + template |
| `/edit-tournament` | Organizer | 🔵 PATCH /tournaments |
| `/start-tournament` | Organizer | 🔵 status→ongoing |
| `/end-tournament` | Organizer | 🔵 status→completed |
| `/cancel-tournament` | Organizer | 🔵 status→cancelled |
| `/tournament` `/tournament-info` | Spectator | 🟢 GET /tournaments/{id} |
| `/tournament-rules` | Spectator | 🟢 detail.rules |
| `/tournament-schedule` | Spectator | 🟢 matches scheduled |
| `/tournament-standings` | Spectator | 🟢 GET /rankings/tournaments/{id} |
| `/tournament-participants` | Spectator | 🟢 registrations / teams |

### Bracket
| Command | Role | 連携 |
|---|---|---|
| `/bracket` | Spectator | 🟢 GET bracket |
| `/bracket-image` | Spectator | ⚪ 画像生成(Pillow) |
| `/bracket-link` | Spectator | ⚪ public URL |
| `/next-match` | Player | 🟢 bracket→自チームの次戦 |
| `/current-round` | Spectator | 🟢 bracket round |
| `/advance-match` | Organizer | 🔵 result/advance |
| `/regenerate-bracket` | Organizer | 🔵 POST bracket |

### Team
| Command | Role | 連携 |
|---|---|---|
| `/team` `/team-roster` | Spectator | 🟢 GET team/members |
| `/team-history` `/team-stats` `/team-rating` `/team-achievements` | Spectator | 🟢 career/analytics |
| `/invite-player` | Captain | 🔵 add member (Modal) |
| `/remove-player` | Captain | 🔵 DELETE member |
| `/promote-player` | Captain | 🔵 PATCH member role |
| `/leave-team` | Player | 🔵 DELETE self |

### Player
| Command | Role | 連携 |
|---|---|---|
| `/player` `/player-profile` `/player-stats` `/player-career` `/player-rating` `/player-history` `/player-achievements` | Spectator | 🟢 players/career/analytics |
| `/open-to-work` `/close-to-work` | Player | 🔵 scout looking flag |

### Match
| Command | Role | 連携 |
|---|---|---|
| `/match` `/match-history` `/match-stats` `/match-summary` `/current-round` | Spectator | 🟢 GET match |
| `/my-matches` `/next-match` | Player | 🔵 自分の試合 |
| `/report-result` | Captain | 🔵 result (Modal+確認Button) |
| `/confirm-result` | Captain | 🔵 相手の確認 |
| `/dispute-result` | Captain | 🔵 dispute (Modal) |
| `/upload-screenshot` | Player | 🔵 upload + match添付 |

### Check-In
| Command | Role | 連携 |
|---|---|---|
| `/check-in` | Player | 🔵 self check-in |
| `/check-in-status` | Spectator | 🔵 集計 |
| `/check-in-all` | Organizer | 🔵 一括 |
| `/missed-check-in` | Organizer | 🔵 未チェックイン一覧 |

### Map Ban/Pick (VALORANT / CS2)
| Command | Role | 連携 |
|---|---|---|
| `/current-veto` | Spectator | ⚪ veto state (Redis) |
| `/ban-map` `/pick-map` | Captain | 🔵 POST banpick + state |
| `/remaining-maps` | Spectator | ⚪ |
| `/confirm-veto` | Captain | ⚪ 確定 |

### Scout
| Command | Role | 連携 |
|---|---|---|
| `/recommend-players` `/recommend-teams` | Player/Organizer | 🟢 recommendations |
| `/search-player` `/search-team` | Spectator | 🟢 scout/players,teams |
| `/player-availability` `/team-recruitment` | Spectator | 🟢 scout |
| `/post-recruitment` | Player | 🔵 POST recruitment (Modal) |
| `/apply-recruitment` | Player | 🔵 apply |
| `/invite-candidate` | Captain | 🔵 invite application |

### Analytics
| Command | Role | 連携 |
|---|---|---|
| `/player-stats` `/team-stats` `/map-stats` `/agent-stats` | Spectator | 🟢 analytics |
| `/leaderboard` `/rankings` | Spectator | 🟢 rankings |
| `/meta-analysis` | Spectator | 🟢 compositions/maps |

### Career
| Command | Role | 連携 |
|---|---|---|
| `/career` `/history` `/achievements` `/rating-history` `/performance-trend` | Spectator | 🟢 career |

### Notification
| Command | Role | 連携 |
|---|---|---|
| `/unread-notifications` | Player | 🔵 GET notifications |
| `/subscriptions` `/notification-settings` `/reminders` | Player | 🔵 settings |

### Stream
| Command | Role | 連携 |
|---|---|---|
| `/stream` `/live` `/watch` `/stream-info` | Spectator | 🟢 match.stream_url |

### Moderator
| Command | Role | 連携 |
|---|---|---|
| `/warn` `/mute` `/unmute` `/kick-player` | Organizer/Admin | 🟡 Discord操作 + 🔵 log |
| `/forfeit-match` `/reopen-match` | Organizer | 🔵 |

### Support
| Command | Role | 連携 |
|---|---|---|
| `/support` `/contact-admin` | Player | 🟡 サポートチャンネル/通知 |
| `/report-player` `/report-team` | Player | 🔵 log |

### Help
| Command | Role | 連携 |
|---|---|---|
| `/help` | Spectator | ⚪ ロール別表示 |

---

## 4. DB変更（migration `008_discord_os`）

既存テーブルは破壊しない。追加と最小限のカラム追加のみ。

| 対象 | 変更 |
|---|---|
| `tournament_registrations` | **ADD** `checked_in_at TIMESTAMPTZ NULL`, `checked_in_via VARCHAR(20) NULL` （既存check-in概念を登録に紐付け） |
| `command_metrics` (新規) | id, guild_id, discord_user_id, user_id(FK null), command, success bool, latency_ms int, error_type null, created_at — コマンド利用履歴 |
| `bot_error_logs` (新規) | id, guild_id null, discord_user_id null, command null, error_type, message text, traceback text null, created_at — Botエラーログ |
| `match_disputes` (新規) | id, match_id(FK), raised_by(FK users null), discord_user_id null, reason text, status(open/resolved/rejected), resolution text null, created_at, resolved_at null — 結果異議 |

> Map veto は既存 `POST /matches/{id}/banpick` + `match.ban_picks` を権威データとし、進行状態（手番・残りマップ）は**Redis**に持つ（`veto:{match_id}`）。新テーブル不要で整合性を保つ。
> check-in は QRベースの既存 `checkins` テーブルとは別レイヤ（登録単位の出欠）として `tournament_registrations` に持たせ、二重管理を避ける。

---

## 5. FastAPI連携（新 `/api/v1/bot` ルータ）

`X-Bot-Secret` 必須。`X-Discord-User-Id` があれば `DiscordLink`→`User` を解決し、その実権限で操作。

| Method | Path | 役割 | 権限判定 |
|---|---|---|---|
| GET | `/bot/resolve` | discord_user_id→user要約(role/player/teams) | secret |
| POST | `/bot/tournaments/{id}/status` | start/end/cancel | 解決userがorganizer/owner |
| POST | `/bot/tournaments/{id}/check-in` | self check-in | 解決userの所属チーム登録 |
| POST | `/bot/tournaments/{id}/check-in-all` | 一括 | organizer/owner |
| GET | `/bot/tournaments/{id}/check-in-status` | 集計 | secret |
| POST | `/bot/matches/{id}/report` | 結果報告(+確認フロー) | captain/organizer |
| POST | `/bot/matches/{id}/confirm` | 相手確認 | 相手captain |
| POST | `/bot/matches/{id}/dispute` | 異議 | 参加captain |
| POST | `/bot/matches/{id}/forfeit` | 不戦敗 | organizer |
| POST | `/bot/matches/{id}/reopen` | 再オープン | organizer |
| GET | `/bot/users/{discord_user_id}/matches` | 自分の試合 | secret |
| GET | `/bot/users/{discord_user_id}/notifications` | 通知 | secret |
| POST | `/bot/players/{id}/looking` | open/close to work | 本人 |
| POST | `/bot/metrics` | コマンドmetrics一括ingest | secret |
| POST | `/bot/errors` | エラーログ | secret |

既存の書き込みは可能な限り**既存サービス層を再利用**（例: report は `MatchService.submit_result`、status は `TournamentService.change_status`）。Botルータは「Discordユーザー解決 + 既存サービス呼び出し」の薄いアダプタに徹する。

---

## 6. Automation（イベント駆動）

```
試合開始 (status→ongoing / advance)
  → backend publish "create_match_channel" {channel_name: match-00N}
  → bot consumer: 🏆 MATCHES に match-00N 生成（既存実装を活用）

結果確定 (report→confirm or organizer確定)
  → backend: bracket更新 + 勝者を次ラウンドへ + Notification作成
  → publish "archive_match_channel"
  → bot consumer: 結果を #results に投稿 → 該当チャンネルを 📦 ARCHIVE へ移動・read-only
  → 関係Captainへ通知（DM or メンション）
```

イベント型は既存3種（setup_tournament/create_match_channel/archive_match_channel）を維持。結果投稿・通知は consumer に小さく追加。

---

## 7. Slash Command UX

- **Autocomplete**: tournament_id / match_id / team_id / player_id / map名 を `services/autocomplete.py` が候補化（API検索 + 直近キャッシュ）。IDの手入力を排除。
- **Modal**: `/report-result`(スコア入力) `/invite-player` `/post-recruitment` `/dispute-result` `/edit-tournament`。
- **Select Menu**: `/ban-map` `/pick-map`(残りマップ) `/promote-player`(ロール選択) `/check-in`(複数大会から選択)。
- **Buttons**: 結果確認(Confirm/Dispute)、veto確定、危険操作(cancel/forfeit)の二段確認、ページネーション。

`ui/` に Modal/View(Button)/Select を集約し、cogから再利用。

---

## 8. Monitoring

- `core/monitoring.py`: 各コマンドを `@track` でラップ → 成功可否・レイテンシ・error_type をバッファし、`POST /bot/metrics` でバッチ送信（`command_metrics`）。
- 例外は `core/errors.py` のグローバル `on_app_command_error` で捕捉 → ユーザへ整形メッセージ + `POST /bot/errors`（`bot_error_logs`）。
- メトリクスは将来 `/admin/dashboard` から集計表示可能（テーブルを共有）。

---

## 9. Terraform変更

- 既存 `modules/discord`（SQS + DLQ + SSM）を維持。
- **追加**: SSM Parameter `/{env}/discord/bot_api_token`（Bot↔Backend共有秘密, SecureString）。Backend(`BOT_API_TOKEN`) と Bot(`BOT_API_TOKEN`) の双方が参照。
- 公開URLは既存CloudFront。新規インフラ追加は無し（コスト据え置き）。

---

## 10. ディレクトリ構成（Bot）

```
discord-bot/
  bot.py                  # 起動/cogロード/sync/error handler/event consumer
  config.py               # env + MAPS + ロール定義
  core/
    rbac.py               # Role enum, @requires, Discord→Role解決
    monitoring.py         # @track, metricsバッファ/flush
    errors.py             # グローバルエラーハンドラ, 例外→embed
  services/
    api_client.py         # 公開API + /bot/* ラッパ（X-Bot-Secret/ X-Discord-User-Id）
    autocomplete.py       # tournament/match/team/player/map 補完
    template.py           # 既存: サーバ生成/チャンネル/Archive
  ui/
    common.py             # embedヘルパ, 確認View, ページネーション
    modals.py             # 各種Modal
    selects.py            # 各種Select
  cogs/
    tournament.py bracket.py team.py player.py match.py
    checkin.py veto.py scout.py analytics.py career.py
    notification.py stream.py moderator.py support.py help.py
```
