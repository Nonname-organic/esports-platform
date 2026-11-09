# RC1 変更一覧

ベースコミット `1ddefd798156b98df1caa3febe26aa15a03d238d` に対する作業ツリーの変更（未コミット）。
行数は git の差分（改行コードの違いは数えない）。分類:
A 外部公開に必須の修正 / B セキュリティ・安定性 / C 今回含める機能 / D 文書 / E 利用者が以前から持っていた変更 /
F 一時・検証用 / G リリースに含めない / H 判断材料が足りない

F（一時・検証用）は作業ツリーに無い。検証用のスクリプトと結果は作業ツリーの外に置いた。

## RC に含める（103 ファイル）

| ファイル | 分類 | 差分 | 内容 | 主な確認 |
|---|---|---|---|---|
| `.github/workflows/deploy-demo.yml` | B | +6 / -0 | デプロイ前に新しいイメージで本番設定を検査し、不備ならコンテナを入れ替えずに止める | RC イメージで検査コマンドを確認 |
| `.gitignore` | B | +2 / -2 | Playwright の認証状態（トークン）とキャッシュをサブディレクトリでも除外 | — |
| `backend/.env.example` | D | +5 / -1 | 本番の DB_PASSWORD の条件、メール本文のログ方針、ANALYTICS_EXPORT_BUCKET を追記 | — |
| `backend/alembic/versions/028_sync_tournament_visibility.py` | B | 新規 69 行 | 非公開・限定公開の大会が一覧に出ていた既存データを補正（退避表つき） | PG15 で適用・戻し・再実行・失敗時の巻き戻し |
| `backend/alembic/versions/029_match_result_reports.py` | C | 新規 42 行 | 試合結果の報告を保存する表 | test_match_flow・往復確認 |
| `backend/alembic/versions/030_widen_recruitment_post_type.py` | A | 新規 27 行 | 募集種別の列を広げ、player_seeks の投稿が 500 になるのを解消 | test_followups・往復と戻しの前提条件 |
| `backend/app/api/v1/admin.py` | C | +72 / -2 | ユーザー一覧・利用停止・ロール変更（監査ログ）。型注釈 | test_access_control・画面確認 |
| `backend/app/api/v1/analytics.py` | B | +20 / -6 | スタッツ非公開の選手を分析 API で返さない | test_sec_visibility |
| `backend/app/api/v1/auth.py` | B | +26 / -10 | パスワード照合を別スレッドで実行、変更・再設定にも強度ルール | test_journey・test_profile_notifications |
| `backend/app/api/v1/bot.py` | B | +39 / -90 | Bot の結果報告を Web と同じ報告処理・権限確認に統一 | test_match_flow・test_sec_discord |
| `backend/app/api/v1/discord.py` | B | +27 / -16 | 大会の Discord 設定 ID を主催者・管理者にだけ返す、OAuth の state | test_sec_discord |
| `backend/app/api/v1/lfp.py` | B | +18 / -20 | 他人のチームとしての募集掲載を防ぐ。型注釈 | test_sec_scout_input |
| `backend/app/api/v1/lft.py` | B | +17 / -20 | 他人の選手としての掲載を防ぐ。型注釈 | test_sec_scout_input |
| `backend/app/api/v1/matches.py` | C | +68 / -3 | 結果の報告・確認・異議・再開 API。OCR を主催者に限定し 5MB で止める | test_match_flow・test_access_control |
| `backend/app/api/v1/players.py` | B | +21 / -6 | スタッツ非公開・本名非公開を守る。型注釈 | test_sec_visibility |
| `backend/app/api/v1/riot.py` | B | +15 / -9 | Riot ID の連携を本人の選手に限定。型注釈 | test_sec_riot |
| `backend/app/api/v1/tags.py` | B | +5 / -2 | 1回に付けられるタグ数と長さの上限 | test_followups |
| `backend/app/api/v1/tournaments.py` | C | +14 / -2 | 参加辞退 API | test_match_flow・画面確認 |
| `backend/app/api/v1/upload.py` | B | +29 / -17 | 拡張子を Content-Type から決定、パストラバーサル修正、nosniff、ダウンロード名の注入対策 | test_upload |
| `backend/app/core/config.py` | B | +41 / -1 | 本番設定の検査（REQUIRE_STRONG_SECRETS）、設定エラーで値を出さない、分析の書き出し先を分離 | test_production_settings |
| `backend/app/core/dependencies.py` | A | +30 / -7 | DB の確定をレスポンス送信前に行う（直後の操作で変更が見えない不具合） | test_db_session_scope |
| `backend/app/core/email.py` | B | +9 / -6 | メール本文は DEBUG のみ、宛先はドメインだけ記録 | test_email_logging |
| `backend/app/core/security.py` | B | +16 / -2 | JWT を PyJWT に、パスワード計算を別スレッドに | 認証系テスト全般 |
| `backend/app/events/registry.py` | C | +7 / -0 | 利用停止・ロール変更・辞退の監査イベント | — |
| `backend/app/home/providers.py` | B | +10 / -4 | ホームに非公開・下書きの大会を出さない | test_access_control |
| `backend/app/main.py` | B | +5 / -2 | readiness が内部の例外内容を返さない | — |
| `backend/app/middleware/rate_limit.py` | B | +18 / -3 | 認証系の制限を IP 単位にし、検証できないトークンで識別子を作らない | test_sec_rate_limit |
| `backend/app/models/__init__.py` | C | +2 / -0 | 結果報告モデルの登録 | — |
| `backend/app/models/match_report.py` | C | 新規 36 行 | 結果報告モデル（新規） | test_match_flow |
| `backend/app/models/scout.py` | A | +1 / -1 | 募集種別の列長を 20 に | test_followups |
| `backend/app/player_profile/history.py` | B | +2 / -0 | 選手履歴に非公開の大会を出さない | test_sec_visibility |
| `backend/app/repositories/tag.py` | B | +18 / -2 | タグ検索に非公開の大会・募集を出さない | test_sec_visibility |
| `backend/app/repositories/tournament.py` | B | +15 / -3 | 公開判定（publicly_listed）を一か所に | test_access_control |
| `backend/app/schemas/scout.py` | B | +12 / -12 | スカウトの入力上限・型 | test_sec_scout_input |
| `backend/app/schemas/tournament.py` | B | +3 / -1 | 公開設定の値を検証 | test_access_control |
| `backend/app/search/providers.py` | B | +3 / -2 | 検索に非公開の大会を出さない | test_access_control |
| `backend/app/services/analytics_dashboard.py` | B | +4 / -2 | スタッツ非公開の選手をランキングに載せない、本名を出さない | test_sec_visibility |
| `backend/app/services/auth.py` | B | +12 / -5 | パスワード照合を別スレッドで、存在しないユーザーでも同じ時間をかける | test_journey |
| `backend/app/services/discord_service.py` | B | +45 / -5 | OAuth の state、サーバー設定前に Discord 上の管理権限を確認 | test_sec_discord |
| `backend/app/services/match.py` | B | +106 / -26 | 試合の操作を大会の主催者・管理者に限定、結果確定の整理、再開 | test_access_control・test_match_flow |
| `backend/app/services/match_report.py` | C | 新規 169 行 | 結果の報告・確認・異議の処理（新規） | test_match_flow |
| `backend/app/services/riot_service.py` | B | +25 / -11 | 本人の選手かを確認 | test_sec_riot |
| `backend/app/services/scout_service.py` | B | +22 / -6 | 代理投稿の検証 | test_sec_scout_input |
| `backend/app/services/stats_service.py` | B | +2 / -1 | 統計に非公開の大会を含めない | test_sec_visibility |
| `backend/app/services/tag_service.py` | A | +10 / -6 | タグに別の入力のラベルが付く不具合 | test_followups |
| `backend/app/services/tournament.py` | A | +35 / -1 | 公開設定を列に保存（非公開が一覧に出ていた）、参加辞退 | test_access_control・test_match_flow |
| `backend/app/workers/handlers/notification.py` | B | +24 / -0 | Webhook の送信先を Discord に限定（SSRF） | test_webhook_url |
| `backend/app/workers/handlers/stats_export.py` | B | +6 / -5 | 分析の夜間書き出しが画像用バケット・AWS S3 へ向かうのを止める | test_production_settings |
| `backend/requirements.txt` | B | +12 / -12 | fastapi・starlette・PyJWT・aiohttp・Pillow・opentelemetry の更新 | pytest 全件・pip-audit |
| `backend/tests/api/test_access_control.py` | B | 新規 247 行 | （新規テスト）他人の大会の操作・非公開大会の露出・OCR の上限 | — |
| `backend/tests/api/test_followups.py` | A | 新規 29 行 | （新規テスト）スキーマとタグの既存不具合 | — |
| `backend/tests/api/test_journey.py` | A | 新規 169 行 | （新規テスト）主要フローを HTTP で通す | — |
| `backend/tests/api/test_match_flow.py` | C | 新規 268 行 | （新規テスト）報告・確認・異議・再開・辞退・ダブルエリミネーション | — |
| `backend/tests/api/test_profile_notifications.py` | B | 新規 93 行 | （新規テスト）プロフィール更新と通知送信 | — |
| `backend/tests/api/test_sec_discord.py` | B | 新規 217 行 | （新規テスト）Discord 連携（API はモック） | — |
| `backend/tests/api/test_sec_riot.py` | B | 新規 131 行 | （新規テスト）Riot 連携（API はモック） | — |
| `backend/tests/api/test_sec_scout_input.py` | B | 新規 134 行 | （新規テスト）スカウトのなりすまし・入力 | — |
| `backend/tests/api/test_sec_visibility.py` | B | 新規 189 行 | （新規テスト）公開範囲 | — |
| `backend/tests/api/test_upload.py` | B | +30 / -1 | アップロードの回帰テストを追加 | — |
| `backend/tests/seed/golden_seed.py` | B | +3 / -0 | 固定日付の Golden 大会の状態を固定（worker の自動更新で E2E が崩れていた） | E2E |
| `backend/tests/test_db_session_scope.py` | A | 新規 26 行 | （新規テスト）応答前のコミット | — |
| `backend/tests/test_email_logging.py` | B | 新規 37 行 | （新規テスト）メールのログに宛先を残さない | — |
| `backend/tests/test_production_settings.py` | B | 新規 81 行 | （新規テスト）本番設定の検査・分析書き出しの停止 | — |
| `backend/tests/test_sec_rate_limit.py` | B | 新規 99 行 | （新規テスト）レート制限の識別子 | — |
| `backend/tests/test_webhook_url.py` | B | 新規 27 行 | （新規テスト）Webhook の送信先 | — |
| `docker-compose.conoha.yml` | A | +13 / -0 | DB 接続数を postgres の上限 20 に収める（api 6+6・worker 2+1・scheduler 2+1） | compose config・E2E で最大13接続 |
| `docker-compose.prod.yml` | B | +18 / -0 | REQUIRE_STRONG_SECRETS・USE_REDIS_QUEUE を固定、POSTGRES_PASSWORD を必須に | compose config で確認 |
| `docs/phase10_vps_conoha.md` | D | +198 / -5 | RC1 本番公開の手順（12 段階）、030 の戻し、バックアップ確認、DB_PASSWORD の扱い | — |
| `docs/qa/TEST_STRATEGY.md` | D | +6 / -0 | ローカル E2E の注意（Windows + Docker Desktop） | — |
| `docs/release/RC1_CHANGES.md` | D | 新規 127 行 | この変更一覧 | — |
| `docs/release/RC1_PRODUCTION_CHECKLIST.md` | D | 新規 125 行 | 本番環境の設定チェックリストと公開後の監視 | — |
| `docs/release/RC1_RELEASE_NOTES.md` | D | 新規 95 行 | リリースノート | — |
| `frontend/eslint.config.mjs` | B | 新規 19 行 | ESLint 設定（無いと npm run lint が対話待ちで止まる） | lint |
| `frontend/next.config.ts` | B | +5 / -0 | 画像最適化 API を停止（Next 15.5.27 の RCE） | build |
| `frontend/package-lock.json` | E・B | +401 / -332 | Next 15.5.29・postcss 8.5.32 の反映に、利用者の既存の更新（sharp・nanoid・semver・source-map-js）が入っている | npm ci・npm audit・build |
| `frontend/package.json` | B | +5 / -2 | next 15.5.29、postcss ^8.5.32 と overrides | build |
| `frontend/playwright.config.ts` | B | +4 / -1 | ローカルの並列数を 4 に（CPU 飽和で起動直後の E2E が時間切れ） | E2E |
| `frontend/src/app/(auth)/admin/_components/user-management.tsx` | C | 新規 118 行 | 管理画面のユーザー管理（新規） | 画面確認 |
| `frontend/src/app/(auth)/admin/matches/[id]/_components/status-controls.tsx` | C | +27 / -1 | 試合の再開ボタン | — |
| `frontend/src/app/(auth)/admin/page.tsx` | C | +4 / -0 | ユーザー管理を管理画面に表示 | 画面確認 |
| `frontend/src/app/(auth)/discord-link/page.tsx` | A | +3 / -1 | ログアウト時に落ちる（フックの順序） | — |
| `frontend/src/app/(auth)/discord/callback/page.tsx` | B | +9 / -3 | OAuth の state を返す、二重送信を防ぐ | — |
| `frontend/src/app/(auth)/organizer/tournaments/[id]/edit/page.tsx` | A | +6 / -4 | 生成できない大会形式を選択肢から外す、公開設定の説明 | — |
| `frontend/src/app/(auth)/organizer/tournaments/create/page.tsx` | A | +7 / -6 | 同上、フックの順序 | 画面表示を確認 |
| `frontend/src/app/(auth)/players/create/page.tsx` | A | +5 / -4 | ページ内リンクを Next の Link に（lint エラー） | lint |
| `frontend/src/app/(auth)/scout/lfp/new/page.tsx` | A | +3 / -2 | 同上 | lint |
| `frontend/src/app/(auth)/teams/create/page.tsx` | A | +3 / -1 | ログアウト時に落ちる（フックの順序） | — |
| `frontend/src/app/(auth)/tournaments/[id]/_components/entry-panel.tsx` | C | +31 / -1 | 参加辞退のボタンと表示 | 画面確認 |
| `frontend/src/app/(public)/login/page.tsx` | A | +4 / -4 | 入力欄とラベルの関連付け | E2E |
| `frontend/src/app/(public)/matches/[id]/_components/result-report-card.tsx` | C | 新規 102 行 | 結果報告・確認のカード（新規） | 画面確認 |
| `frontend/src/app/(public)/matches/[id]/page.tsx` | C | +3 / -0 | 試合ページに報告カードを表示 | 画面確認 |
| `frontend/src/app/(public)/register/page.tsx` | A | +8 / -8 | 入力欄とラベルの関連付け | E2E |
| `frontend/src/features/admin/api/admin-api.ts` | C | +18 / -0 | ユーザー管理 API の呼び出し | — |
| `frontend/src/features/admin/hooks/use-admin.ts` | C | +19 / -1 | ユーザー管理のフック | — |
| `frontend/src/features/discord/api/discord-api.ts` | B | +2 / -1 | OAuth の state を送る | — |
| `frontend/src/features/matches/api/match-api.ts` | C | +24 / -0 | 結果報告 API の呼び出し | — |
| `frontend/src/features/matches/hooks/use-match-admin.ts` | A | +1 / -1 | lint エラーの解消 | lint |
| `frontend/src/features/tournaments/api/tournament-api.ts` | C | +4 / -1 | 参加辞退 API の呼び出し | — |
| `frontend/src/features/tournaments/hooks/use-tournaments.ts` | C | +12 / -0 | 参加辞退のフック | — |
| `frontend/tests/e2e/journey.spec.ts` | B | +66 / -72 | 起動直後の安定化（networkidle をやめる）、条件付き成功の除去、並列ワーカーで衝突しないユーザー名 | E2E |
| `frontend/tests/e2e/visual.spec.ts` | B | +1 / -1 | 注記の形式の修正 | — |
| `nginx/nginx-tls.conf` | A | +3 / -1 | 受け付ける本文の上限 5m→11m（10MB の添付が 413 になっていた） | nginx -t |
| `nginx/nginx.conf` | A | +3 / -1 | 同上 | nginx -t・E2E |

`frontend/package-lock.json` は利用者の既存の更新を含む。package.json の Next・postcss の変更と対で必要なため RC に含めるが、
コミットするかは利用者が判断する（含めないと CI の `npm ci` が package.json と食い違って失敗する）。

## RC に含めない（3 ファイル。作業ツリーには残す）

| ファイル | 分類 | 差分 | 内容 | 理由 |
|---|---|---|---|---|
| `docs/interview_cheatsheet.md` | E・G | 新規 164 行 | 利用者の個人用資料（転職面談の想定問答） | 製品の文書ではない |
| `docs/phase11_rollback.md` | E・H | 新規 814 行 | 利用者のロールバック手順書（本文に「実機で未検証」と明記） | 内容の採否は利用者の判断。RC1 の手順書は phase10 に自己完結で書いた |
| `docs/runbook_p0-001_stage1.md` | E・G | 新規 1005 行 | 利用者の過去の個別作業の手順書（P0-001 の Blue-Green 切替） | 今回のリリースの手順ではない |
