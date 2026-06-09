# eSports Operating System — 現状設計書（画面・機能・できること）

> 最終更新: 2026-06-09 / 本番: https://d3r8lgt0kvo61v.cloudfront.net
> 本書は「いま動いている」機能の全体像。詳細設計は [SYSTEM_DESIGN.md](../SYSTEM_DESIGN.md) / [DISCORD_OS_DESIGN.md](./DISCORD_OS_DESIGN.md) 等を参照。

---

## 1. システム全体像

| レイヤ | 技術 | 役割 |
|--------|------|------|
| フロント | Next.js 15 App Router / React Query / Zustand / Tailwind / shadcn/ui | Web UI（SSR優先） |
| API | FastAPI / SQLAlchemy(async) / Pydantic v2 | REST API（公開＋認証＋Bot） |
| Bot | discord.py 2.4 | Discord Tournament OS（93コマンド） |
| DB | PostgreSQL 15（Alembic 001–008） | 永続化 |
| Cache/Queue | Redis（キャッシュ＋イベントキュー） | キャッシュ / Pub/Sub / SQS代替 |
| 配信 | CloudFront → Nginx → api/frontend(Docker) on EC2 | 公開 |

**3つのクライアント**が同じAPIに到達: ① Web ② Discord Bot ③（将来）外部連携。認証は JWT（Web）と `X-Bot-Secret`+`X-Discord-User-Id`（Bot代理実行）。

---

## 2. Web画面一覧

### 公開（ログイン不要）
| 画面 | パス | できること |
|------|------|-----------|
| ランディング | `/` | サービス紹介・主要導線 |
| ログイン/登録 | `/login` `/register` | アカウント作成・ログイン（JWT） |
| 大会一覧 | `/tournaments` | 一覧・ゲーム/状態フィルタ・検索 |
| 大会詳細 | `/tournaments/[id]` | 概要・参加チーム・日程・状態 |
| ブラケット | `/tournaments/[id]/bracket` | トーナメント表のビジュアル表示 |
| 試合詳細（Match Center） | `/matches/[id]` | スコア・ゲーム別・Ban/Pick・配信/VOD・選手スタッツ |
| プレイヤー詳細 | `/players/[id]` | タブ: 概要 / **Career** / **Achievements** / Trend / Matches / Agents / **Riot** |
| チーム詳細 | `/teams/[id]` | タブ: 概要 / **Career** / Roster / **Rivals** / Matches / Analytics |
| スカウトHub | `/scout` | スカウトプラットフォーム入口 |
| 選手検索 | `/scout/players` | ロール/ランク/勝率/レート/募集中で絞り込み |
| チーム検索 | `/scout/teams` | 募集中チーム・平均レート等で検索 |

### 認証（ログイン必要）
| 画面 | パス | できること | 権限 |
|------|------|-----------|------|
| ダッシュボード | `/dashboard` | 自分の大会/通知サマリ | ログイン |
| 通知センター | `/notifications` | 通知一覧・既読・🔔ベル | ログイン |
| アナリティクス | `/analytics` | マップ/構成/選手統計の可視化 | ログイン |
| 大会作成 | `/organizer/tournaments/create`・`/new` | 大会の新規作成 | Organizer |
| 大会運営 | `/organizer/tournaments/[id]` | 登録承認・状態遷移・ブラケット生成 | Organizer |
| 管理ダッシュボード | `/admin` | 全体KPI・運用 | Admin |
| 管理: 試合 | `/admin/matches/[id]` | スコア入力・結果確定 | Admin/Organizer |
| プレイヤー作成 | `/players/create` | 選手プロフィール作成 | ログイン |
| チーム作成/編集/メンバー | `/teams/create`・`/teams/[id]/edit`・`/members` | チーム編成 | オーナー/Captain |
| 募集 | `/scout/recruitment` | 募集投稿・応募管理 | ログイン |

---

## 3. Discord Bot（93コマンド / 15カテゴリ）

全コマンドRBAC（Spectator < Player < Captain < Organizer < Admin）+ Autocomplete + Modal/Button/Select。

| カテゴリ | 主なコマンド | できること |
|----------|-------------|-----------|
| Tournament | `/create-tournament` `/start` `/end` `/cancel` `/tournament(-info/-rules/-schedule/-standings/-participants)` | サーバー自動構築・状態遷移・情報参照 |
| Bracket | `/bracket` `/bracket-link` `/current-round` `/advance-match` `/regenerate-bracket` | 表示・勝者確定・生成 |
| Check-In | `/check-in` `/check-in-status` `/check-in-all` `/missed-check-in` | 出欠（本人/一括/集計） |
| Match | `/match` `/my-matches` `/next-match` `/match-history` `/match-stats` `/report-result` `/confirm-result` `/dispute-result` `/upload-screenshot` | 結果報告→相手確認→確定、異議、スクショ |
| Map Veto | `/ban-map` `/pick-map` `/current-veto` `/remaining-maps` `/confirm-veto` | VALORANT/CS2 のBan/Pick |
| Team | `/team` `/team-roster/-stats/-history/-rating/-achievements` `/invite-player`他 | 参照（編成書込はWeb） |
| Player | `/player(-profile/-stats/-career/-rating/-history/-achievements)` `/open-to-work` `/close-to-work` | 参照・求職フラグ |
| Scout | `/search-player` `/search-team` `/recommend-players` `/recommend-teams` `/player-availability` `/team-recruitment` | 検索・推薦・募集閲覧 |
| Analytics | `/map-stats` `/agent-stats` `/rankings` `/leaderboard` `/meta-analysis` | 統計・順位・メタ |
| Career | `/career` `/history` `/achievements` `/rating-history` `/performance-trend` | 本人/指定選手のキャリア |
| Notification | `/unread-notifications` `/subscriptions` `/notification-settings` `/reminders` | 通知 |
| Stream | `/stream` `/live` `/watch` `/stream-info` | 配信リンク |
| Moderator | `/warn` `/mute` `/unmute` `/kick-player` `/forfeit-match` `/reopen-match` | モデレーション |
| Support | `/support` `/contact-admin` `/report-player` `/report-team` | サポート・通報 |
| Help | `/help` | ロール別コマンド一覧 |

**自動化**: 試合開始→試合チャンネル自動生成（操作ガイド掲示）、結果確定→アーカイブ移動。**監視**: 全コマンドの利用履歴/エラーを `command_metrics`/`bot_error_logs` に記録。

---

## 4. バックエンドAPI（主要エンドポイント群）

`/api/v1` 配下: `auth` `tournaments` `matches` `rankings` `analytics` `admin` `teams` `players` `upload` `scout` `notifications` `discord` `riot` `bot`。

- **認証**: register/login/refresh/me（JWT + リフレッシュ、role claim）
- **大会**: CRUD・登録/承認・状態遷移・ブラケット生成/取得
- **試合**: 取得・開始・スコア・Ban/Pick・結果確定
- **ランキング/分析**: 大会順位・選手/マップ/構成統計・大会サマリ
- **チーム/選手**: CRUD・メンバー・**Career/実績/レート履歴/Rivals**
- **スカウト**: 選手/チーム検索・募集CRUD・応募・**双方向レコメンド**
- **通知**: 一覧・未読数・既読（Redis Pub/Subでリアルタイム）
- **Discord**: OAuth・大会セットアップ（イベント発行）
- **Riot**: 連携・同期・プロフィール（VALORANT戦績）
- **Bot**: `X-Bot-Secret`サービス認証 + Discordユーザー解決による代理実行（check-in/結果/異議/forfeit/reopen/メトリクス）

---

## 5. データモデル概要（PostgreSQL, Alembic 001–008）

users / players / teams・team_members / tournaments・tournament_registrations(出欠) / brackets・matches・match_games・ban_picks・match_results・player_match_stats / rankings / checkins(QR) / notifications / 集計(agg_*) / audit_logs / scout_profiles・recruitment_posts・recruitment_applications / **player_careers・team_careers・player_ratings(Glicko-2)・achievements・match_mvps** / discord_servers・discord_channels・discord_links / riot_profiles・riot_matches / **command_metrics・bot_error_logs・match_disputes**。

---

## 6. ペルソナ別「できること」

| | 観戦/ゲスト | Player | Captain | Organizer | Admin |
|---|---|---|---|---|---|
| 大会/試合/順位の閲覧（Web/Discord） | ✅ | ✅ | ✅ | ✅ | ✅ |
| 選手/チーム/キャリア/分析の閲覧 | ✅ | ✅ | ✅ | ✅ | ✅ |
| アカウント作成・プロフィール作成 | 登録のみ | ✅ | ✅ | ✅ | ✅ |
| チェックイン（自分のチーム） | – | ✅ | ✅ | ✅ | ✅ |
| 求職フラグ・募集応募 | – | ✅ | ✅ | ✅ | ✅ |
| チーム編成（招待/除外/昇格） | – | – | ✅ | ✅ | ✅ |
| 結果報告→相手確認→確定 / 異議 / veto | – | 一部 | ✅ | ✅ | ✅ |
| 大会作成/状態遷移/ブラケット/一括CI | – | – | – | ✅ | ✅ |
| モデレーション（warn/mute/kick/forfeit/reopen） | – | – | – | ✅(kick除く) | ✅ |
| 全体管理・KPI | – | – | – | – | ✅ |

---

## 7. 現状の制約・既知ギャップ

1. **Discordアカウント連携UIが未実装（最重要）**: バックエンドにOAuth(`/discord/oauth/*`)はあるが、フロントに「Discord連携」ボタンと `/link` Botコマンドが無いため、現状 `DiscordLink` を作成できず **Botの操作系（check-in/結果報告等）が実行不可**（参照系は公開APIなので動作）。→ コード方式連携（Webでコード発行→`/link code:XXXX`）の実装を提案中。
2. **チーム編成書込・募集投稿・大会編集・大会作成** は Web限定（user-JWT必須API）。Discordからは閲覧＋ディープリンク。
3. **Map veto** は単一Botインスタンス前提のメモリ保持（DB未永続）。
4. **試合開始/終了→Discord自動チャンネル**は publish 実装済みだが、大会進行サービスからの publish 呼び出しは未配線（手動 `/advance-match` 等で進行）。
5. **Riot定期同期**は手動同期のみ（cronワーカー未配線）。
6. **Terraform SSM**（BOT_API_TOKEN）は設計のみ。デモは `.env` 運用。

> 次の最優先は **#1（Discord連携導線）**。これが入ると参加者がDiscordだけで大会進行を完結できる状態になります。
