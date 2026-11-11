# RC2 変更一覧

- 作成: 2026-11-09（RC2 統合・必須修正工程）
- 対象: ブランチ `release/rc2`。PR の土台は main `262bff2`
- RC2 の中身は次の 3 つ
  - RC1（`b3fdf11`。ツリー `f232403…` は RC1 の 103 ファイルと同じ）。詳細は [RC1_CHANGES.md](RC1_CHANGES.md)
  - main の取り込み（`c261cf7`）。3 ファイルの衝突を、関数単位で統合した（2 章）
  - RC2 の必須の修正（3 章）
- コミットのハッシュ・ツリー・マニフェスト・テスト結果は、この文書には書けない（書くと自分のハッシュが変わる）。PR の本文に載せる

## 1. コミット

| コミット | 内容 |
|---|---|
| `b3fdf11` | RC1 をそのままコミットした（103 ファイル。ツリーが RC1 の `f232403…` と一致することを確かめてから作った） |
| `c261cf7` | main（#40・#41・#42・#51）を取り込み、3 ファイルの衝突を解消した。隔離環境で作った統合案と同じツリー（`0e7391c…`） |
| `a564ef3` | S1: OCR の画像を、展開する前に形式と寸法で断る |
| `e1b385f` | S2: ログイン後の転送先を、同じサイトの相対パスに限る |
| `d246851` | 試合: 再開時に報告を消す、成績を置き換える、試合ごとの行ロック、異議の理由の公開範囲、異議中の報告 |
| `5003f22` | 大会: 辞退ボタンの表示、有効な登録を優先、主催者による辞退の取り消し |
| `88ee8ae` | Discord: 管理者にも Discord 側のサーバー管理権限が要ることをテストで固定 |
| `1681944` | テストの import の並び、`RateLimitError` の型注釈（ruff・mypy の新しい指摘をなくす） |
| （この文書を含むコミット） | 文書（RC2 の 5 本、phase10 の訂正）、ログイン後の転送先の E2E |

## 2. main との衝突の解消（関数単位）

判定の条件は RC1 の共通関数 `ensure_can_manage_match`（ADMIN か、その大会の主催者本人か）に一本化した。
main の API 側の確認（`MatchOrganizer` の Dependency）は、その関数を呼ぶ形で残した。

### `backend/app/services/match.py`

| 関数 | RC1 | main | RC2（統合後） | 認可の条件 |
|---|---|---|---|---|
| `require_organizer_authority` | なし | Dependency から呼ばれ、主催者本人か ADMIN かを自前で判定 | 試合を読み、無ければ 404。判定は `ensure_can_manage_match` に任せる | ADMIN、または大会の主催者本人 |
| `start_match`・`update_game_score`・`save_game_player_stats`・`register_result` | メソッドの中で `ensure_can_manage_match` を呼ぶ。`authorized=True`（Bot・Web の報告の確定）だけ省略 | 判定なし（Dependency だけ） | RC1 の判定を残す。REST では Dependency と二重に確かめる。Bot の没収試合など REST 以外の経路も守られる | 同上。`authorized=True` は呼び出し側で確かめ済みの経路だけ |
| `reopen_match` | メソッドの中で判定 | なし（RC1 の機能） | RC1 の判定を残し、route も `MatchOrganizer` を通す | 同上 |
| `register_ban_pick` | 主催者・ADMIN だけ（`ensure_can_manage_match`）。出場外のチームは 400 | `_require_ban_pick_authority`（#40）。チームの指定が出場チームか確かめる | main の判定に一本化。RC1 の主催者限定は外した（チーム側の登録が 403 になるため） | ADMIN、大会の主催者、出場チームのオーナー、出場チームの現役キャプテン。一般メンバー・控えは不可 |
| `set_stream_url` | `ensure_can_manage_match` | 同じ | 変更なし | ADMIN、または大会の主催者本人 |

### `backend/app/api/v1/matches.py`

| route | RC2 の Dependency | 備考 |
|---|---|---|
| `start_match`・`update_game_score`・`save_game_player_stats`・`register_result`・`parse_scoreboard`（OCR）・`reopen_match` | `MatchOrganizer`（main） | 拒否したリクエストは、サービス層・OCR・結果登録のロックに届かない。OCR の route の中にあった RC1 の重複した確認は外した（Dependency が先に走る）。5MB の上限は残した |
| `register_ban_pick` | `CurrentUser` | サービスの `_require_ban_pick_authority` が判定 |
| `set_stream_url` | `OrganizerUser` | サービスが主催者本人かを判定 |
| `report_result`・`confirm_result_report`・`dispute_result_report` | `CurrentUser` | `MatchReportService` が、対戦チームの代表（オーナー・現役キャプテン）か主催者・ADMIN かを判定する。main の「書き込みの route はすべて `MatchOrganizer` を通す」テストの除外一覧に、理由を書いて加えた |
| `get_result_report` | `CurrentUser` | 誰でも状態を見られる。異議の理由は当事者だけ（3 章） |

import は両方の和集合にした（`Annotated`・`Any`）。

### `backend/app/services/discord_service.py`

| 関数・定数 | RC1 | main | RC2（統合後） | 認可の条件 |
|---|---|---|---|---|
| `setup_tournament` | 引数 `user`。Discord 側の管理権限を確かめる | 引数 `current_user`。大会の主催者本人か ADMIN か（#51） | main の引数。所有者の確認 → 重複の確認 → Discord 側の管理権限の確認、の順 | アプリ側: ADMIN か大会の主催者本人。Discord 側: そのサーバーのオーナーか「サーバー管理」（`MANAGE_GUILD`）を持つ。**管理者も Discord 側の権限が要る** |
| `_require_guild_manager` | Discord 連携のトークンで `users/@me/guilds` を見る | なし | RC1 のまま。呼び出しは `current_user.id` | 連携なし・トークン失効・権限なしは 403 |
| `OAUTH_STATE_TTL`・`MANAGE_GUILD` | あり | なし | RC1 のまま | — |

main の Discord 設定のテスト（`p05_001`・`p05_002`）は、Discord 側の確認を通ったものとして記録する fixture（`guild_ok`）を加えて動かす。

## 3. RC2 の修正（ファイルごと）

| ファイル | 変更 | 理由 |
|---|---|---|
| `backend/app/services/scoreboard_ocr.py` | `cv2.imdecode` の前に、Pillow でヘッダーだけを読む。PNG・JPEG・WebP 以外、一辺 8192px 超、16,777,216 画素超を断る。Pillow の展開爆弾の上限を同じ値に揃え、WebP は展開用の領域を確保する前に断る | S1（HIGH） |
| `backend/app/services/scoreboard_import.py` | 同時に解析するのは 1 プロセスあたり 2 件まで。3 件目は待たせずに 429 | S1 |
| `backend/app/api/v1/matches.py` | OCR の upload は上限＋1 バイトまでしか読まない | S1 |
| `frontend/src/lib/safe-redirect.ts`・`login/page.tsx` | ログイン後の `?next=` は、先頭が `/` 1 つの相対パスだけ。制御文字・空白・`\` を含む値と、正規化した後に `//` で始まる値は `/dashboard` にする | S2（HIGH） |
| `backend/app/services/match.py` | `lock_match`（`SELECT … FOR UPDATE` で試合の行をロックし、読み直す）を、開始・スコア・成績・結果・再開で使う。結果の登録は、ゲームごとの成績を置き換える。再開すると、その試合と、チームを外した次の試合の報告を消す | S5・S6・S10 |
| `backend/app/services/match_report.py` | 報告・確認・異議も試合の行をロックする。異議の理由は両チームのオーナー・メンバーと主催者・ADMIN にだけ返す。異議中はチームから報告できない（主催者は裁定できる） | S5・S10・4-2・4-4 |
| `backend/app/api/v1/tournaments.py`・`services/tournament.py` | `my-registration` に `can_withdraw`。複数チームで関わる利用者には、有効な登録を先に返す | 4-1 |
| `frontend/…/entry-panel.tsx`・`tournament-api.ts` | 辞退ボタンは `can_withdraw` のときだけ出す | 4-1 |
| `frontend/…/organizer/tournaments/[id]/page.tsx` | 辞退済みの登録に「辞退を取り消して承認」を出す | 4-1 |
| `backend/app/core/exceptions.py` | `RateLimitError.__init__` に `-> None` | mypy |
| `docs/phase10_vps_conoha.md` | `alembic downgrade 027` と 030 を戻す手順を削除し、イメージだけを戻す方針に訂正。RC1 の節に RC2 の文書への案内 | S3・S4（HIGH） |

## 4. 追加したテスト

| ファイル | 内容 |
|---|---|
| `backend/tests/test_ocr_input_limits.py` | 通常の画像（PNG・JPEG・WebP）、上限ちょうど・1 超え、巨大な寸法を宣言した PNG・JPEG・WebP、展開爆弾の PNG、壊れた画像、未対応の形式、空、続けての送信、同時 3 件で 429。大きな画像は展開しない（ヘッダーだけの画像か、小さく差し替えた上限で確かめ、`cv2.imdecode` が呼ばれないことを見る） |
| `backend/tests/test_match_concurrency.py` | 別々のトランザクションで、行ロック中は他から取れない、同時の結果登録で確定は 1 件、同じマップの成績の同時保存で二重にならない、開始と確定が同時でも状態が食い違わない |
| `backend/tests/api/test_match_flow.py`（追加分） | 再開で次の試合の古い報告が消え、入れ替わった相手だけでは確定できない。再開した試合の報告・異議が消える。再開後の登録し直し・マップごとの保存の後の登録で成績が二重にならない。異議の理由の公開範囲。異議中の報告。辞退ボタン・辞退の取り消し・複数チーム |
| `backend/tests/api/test_sec_discord.py`（追加分） | 管理者でも、Discord 未連携・サーバー管理権限なしなら 403、権限があれば設定できる |
| `frontend/src/lib/safe-redirect.test.ts` | 外部ホスト・`javascript:`・`data:`・タブや改行・バックスラッシュ・1 回と 2 回のエンコード・正規化で `//` になる値・長すぎる値。最終的な遷移先が同じオリジンであること |
| `frontend/tests/e2e/login-redirect.spec.ts` | 実際のブラウザでログインし、`?next=` が外部・`javascript:` なら `/dashboard`、相対パスならそのページに留まること |

## 5. RC2 に含めないもの（作業ツリーに残す）

| 区分 | ファイル |
|---|---|
| 利用者の文書（3 本） | `docs/interview_cheatsheet.md`・`docs/runbook_p0-001_stage1.md`・`docs/phase11_rollback.md` |
| RC1 のレビュー資料（3 本） | `docs/release/RC1_REVIEW_REPORT.md`・`RC1_PR_DRAFT.md`・`RC1_PREDEPLOY_GATE.md` |
| RC2 の追加監査資料（4 本） | `docs/release/RC2_INTEGRATION_AUDIT.md`・`RC2_CONFLICT_RESOLUTION_PLAN.md`・`RC2_SECURITY_REVIEW.md`・`RC2_DEPLOYMENT_GAP_ANALYSIS.md` |
| RC2 の PR 準備資料 | `docs/release/RC2_PR_DRAFT.md`・`RC2_MANIFEST.sha256`（RC2 の識別情報。自分のハッシュを含められないため） |

`frontend/package-lock.json` は RC1 の 103 ファイルの 1 つとして RC1 のコミットに入っている（RC1 の依存の更新 42 項目と、それ以前からの利用者の変更 30 項目。RC1 のレビュー資料 `RC1_REVIEW_REPORT.md` の 4 章。リポジトリには含めない）。RC2 では依存を更新していない。
