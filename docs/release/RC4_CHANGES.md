# RC4 の変更点（RC3 `b7f49f1` から）

- 作成: 2026-11-11。対象はブランチ `release/rc4`
- 利用者から見た内容は [RC4_RELEASE_NOTES.md](RC4_RELEASE_NOTES.md)

## マイグレーション

| ファイル | 内容 |
|---|---|
| `backend/alembic/versions/031_membership_consent.py` | `team_invitations`、`team_members` の `consent`・`confirmed_at`・`rejected_at`・`invitation_id`、出どころの判定、現役の重複の退避（`rc4_membership_dedup_backup`）、`ck_team_members_period`（違反があれば NOT VALID）、`uq_team_members_active`、`membership_migration_state` |
| `backend/alembic/versions/032_tournament_rosters.py` | `tournaments.roster_mode` と判定 3、`roster_locked_at`・`lineup_size`・`roster_max`、`matches.lineup_locked_at`、`tournament_roster_entries`・`match_lineup_entries`・`match_substitutions`・`participation_disputes`・`admin_corrections`、`player_match_stats.lineup_entry_id`、トリガー `trg_tournaments_roster_mode_guard` |

## バックエンド

| 区分 | ファイル | 内容 |
|---|---|---|
| モデル | `app/models/roster.py`（新）・`team.py`・`tournament.py`・`match.py` | 新しい表と列 |
| 所属 | `app/services/membership.py`（新）・`app/api/v1/memberships.py`（新） | 招待・返事・所属の確認と否認・管理者の否認の取り消し。正式な所属の判定（`formal_clause`） |
| チーム | `app/services/team.py`・`app/api/v1/teams.py` | メンバーの直接追加は 410。作成者の所属は `self`。メンバー一覧に承諾の状態 |
| 名簿・出場登録 | `app/services/roster.py`（新）・`app/api/v1/rosters.py`（新）・`app/api/v1/matches.py` | 名簿・出場登録の固定・交代・マップごとの実出場・異議・管理者の訂正の記録 |
| 試合 | `app/services/match.py` | 開始で固定、開始を経ない不戦勝、成績はそのマップの実出場者だけ、完了した大会は管理者の理由つきの訂正だけ、旧方式の大会は開始・再開しない、バイは再開しない |
| 大会 | `app/services/tournament.py`・`app/api/v1/tournaments.py` | 旧方式の大会を開催中・未開始から完了にしない、開催中で名簿を固定、旧方式 → 名簿の方式の切り替え、エントリー状況に参加登録の ID と名簿の管理の可否 |
| ワーカー | `app/workers/sqs_consumer.py` | 旧方式の大会は開催中・完了へ自動で変えない。大会ごとにセーブポイントで区切る（1 回分の処理を `apply_tournament_status_transitions` に切り出し） |
| 帰属 | `app/rankings/attribution.py`（新）・`rankings/aggregator.py`・`player_profile/history.py`・`player_profile/aggregator.py`・`services/career_service.py` | 個人の RP・大会履歴・通算成績の帰属（S8-2） |
| そのほか | `api/v1/bot.py`・`services/match_report.py`・`services/scoreboard_import.py`・`events/registry.py`・`core/config.py`・`core/exceptions.py`・`schemas/*` | 正式な所属のキャプテンだけ、Bot の不戦勝は開始を経ない不戦勝、スコアボードの候補は出場登録から、監査のイベント 15 種、招待の設定値、410 |
| スクリプト | `scripts/rc4_release_check.py`（新）・`scripts/prepare_demo_data.py` | 公開の確認（件数だけ）。デモデータの大会は名簿の方式 |

### 独立レビューの指摘への対応（2026-11-11）

| 指摘 | 対応 |
|---|---|
| マップの番号に上限が無く、大きな番号で出場の計算が止まる（主催者の機能は誰でも有効にできる） | スコア・成績の経路で 1〜9 に限る。出場の計算は実在するマップの番号だけを回す |
| 主催者が完了・中止した大会の状態を戻して、管理者だけの訂正の規則を避けられる。結果の登録・スコアの更新に完了した大会の制限が無い | 完了・中止した大会の状態の変更は管理者だけ。結果の登録・スコアの更新も管理者の理由つきの訂正（`result_change`）だけ |
| チームの結果報告の確定で、大会の開始の前に試合が始まり、大会全体の名簿が固定される | 主催者・管理者でない人の確定で予定の試合を開始するのは、大会が開催中のときだけ |
| 開始を経ない不戦勝の試合に、後から出場登録と成績を足せる | 開始を経ずに決着した試合には出場登録を作れず、名簿の方式の大会では出場登録の固定の前の試合にマップ・成績を記録できない |
| キャプテンでなくなった人が、自分の送った招待を取り消せる | 取り消しは常にチームの管理者だけ |
| 交代の一覧（自由記述の理由）が誰でも読める。外された出場登録の選手が異議を出せる | 交代の一覧は主催者・管理者だけ。異議は外されていない出場登録か成績に載った本人だけ |

## フロントエンド

| ファイル | 内容 |
|---|---|
| `src/features/teams/api/team-api.ts`・`hooks/use-teams.ts` | 招待・返事・所属の確認の API とフック（直接追加を削除） |
| `src/features/rosters/`（新） | 名簿・出場登録・交代・異議の API とフック |
| `src/app/(auth)/teams/[id]/members/page.tsx` | 招待の送信と一覧・取り消し、本人未確認の印 |
| `src/app/(auth)/teams/invitations/`・`settings/memberships/`・`tournaments/roster-invitations/`・`admin/disputes/`（新） | 本人の返事・所属の確認・名簿への参加・異議の裁定 |
| `src/app/(auth)/tournaments/[id]/_components/roster-panel.tsx`（新）・`entry-panel.tsx` | 大会の名簿の欄 |
| `src/app/(auth)/organizer/tournaments/[id]/page.tsx` | 大会の方式と切り替え |
| `src/app/(auth)/admin/matches/[id]/_components/status-controls.tsx`・`lineup-panel.tsx`（新） | 開始の理由・開始を経ない不戦勝・再開の理由・出場登録と交代 |
| `src/app/(public)/matches/[id]/_components/match-lineup.tsx`（新） | 出場登録の表示と異議 |

## CI/CD

| ファイル | 内容 |
|---|---|
| `.github/workflows/deploy-demo.yml` | 入れ替える前のイメージを digest で控える → 取得 → 設定の検査 → バックアップと確認 → 新しいイメージでマイグレーション → 入れ替え → readiness → 公開の確認（Q28・Q29） |

## テスト

| ファイル | 内容 |
|---|---|
| `tests/test_rc4_migrations.py`（新） | 030 の形のデータから 032 への上げ下げ、判定 3 での停止とまとめての戻り、出どころの判定、重複の退避と戻し、トリガー |
| `tests/api/test_rc4_roster.py`（新） | 招待と承諾、名簿、開始での固定、開始を経ない不戦勝、旧方式の大会の制限と切り替え、ワーカー、交代と実出場、異議、管理者の訂正、帰属 |
| `tests/test_rc4_release_check.py`（新） | 公開の確認 |
| 既存のテスト（`factories.py`・`test_match_flow.py`・`test_match_authz.py`・`test_access_control.py`・`test_match_concurrency.py`・`test_journey.py`・`test_sec_visibility.py`） | 名簿の方式（試合を作るテストは名簿と出場登録を用意する）・旧方式の大会（既存の大会の集計） |

## 文書

| ファイル | 内容 |
|---|---|
| `docs/release/RC4_*.md` | リリースノート・変更点・公開と切り戻しの手順 |
| `docs/qa/TEST_CASES.md`・`docs/SYSTEM_DESIGN.md`・`docs/adr/0016-season-rank-badge.md` | メンバーの招待・名簿の表と API・個人の RP の帰属（Q27） |
