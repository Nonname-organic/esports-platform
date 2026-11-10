# RC4 本番公開の手順（ConoHa VPS）

- 作成: 2026-11-11（RC4 自律完遂の工程）
- [RC2 の手順](RC2_DEPLOYMENT_RUNBOOK.md)を置き換える。切り戻しは [RC4_ROLLBACK_RUNBOOK.md](RC4_ROLLBACK_RUNBOOK.md)、内容は [RC4_RELEASE_NOTES.md](RC4_RELEASE_NOTES.md)
- 秘密情報の値は、どの手順でも画面・ログ・コマンドの引数に出さない
- 本番は RC2 より前の版（`sha-c0a80ad`、DB は 027）。RC4 の公開で、RC2・RC3・RC4 がまとめて入る

## 0. 全体の流れ

RC2 の手順では、先行マイグレーション・イメージの控え・入れ替えを人がサーバーで行っていた。RC4 では Deploy の workflow がすべて行う（Q29）。

| 段 | 作業 | 本番への影響 |
|---|---|---|
| 1 | マージ前の確認 | なし |
| 2 | Deploy の workflow を有効にする | なし（次の Build & Push の完了で走る） |
| 3 | PR を main へマージする | Build & Push の完了で Deploy が走る（4 の順に本番が変わる） |
| 4 | Deploy の workflow（自動） | 4-4 で本番 DB、4-5 でアプリのコンテナが変わる |
| 5 | 公開後の確認 | なし |
| 6 | Deploy の workflow を無効に戻す | なし |

## 1. マージ前の確認

- [ ] PR の CI（`qa.yml`）が通っている。PR の head が、作業記録に書いた RC4 のコミット・ツリーと同じ
- [ ] 開催中の大会が無い（公開の一覧で確かめる。限定公開・非公開も含めた最終の判定は 032 の判定 3 が行う）:
  `curl -fsS 'https://app.axelia-esports.jp/api/v1/tournaments?status=ongoing&limit=1'` の `data` が空
- [ ] Deploy workflow の状態: `gh api repos/Nonname-organic/esports-platform/actions/workflows/deploy-demo.yml --jq .state`

## 2. Deploy の workflow を有効にする

```bash
gh workflow enable deploy-demo.yml --repo Nonname-organic/esports-platform
```

マージの前に有効にしておくと、マージで走る Build & Push の完了で Deploy が 1 回だけ走る。マージの後に有効にした場合は、
`gh workflow run build.yml --ref main --repo Nonname-organic/esports-platform` で Build & Push を動かす（Deploy に手動実行の口は無い）。

## 3. PR を main へマージする

- マージで Build & Push が `ghcr.io/nonname-organic/esports-platform-{api,worker,frontend}:sha-<マージコミットの先頭 7 文字>` を作り、その完了で Deploy が走る
- `gh run watch --repo Nonname-organic/esports-platform` で見る

## 4. Deploy の workflow（自動。`.github/workflows/deploy-demo.yml`）

| 順 | 内容 | 失敗したとき |
|---|---|---|
| 4-1 | 入れ替える前の 4 サービス（api・worker・scheduler・frontend）のイメージを digest で `~/rollback-images-sha-<新>.yml` に控える（同じ版のやり直しでは上書きしない） | — |
| 4-2 | 新しいイメージの取得と、本番設定の検査（`import app.core.config`） | 入れ替えずに止まる。旧コードのまま |
| 4-3 | `scripts/backup-db.sh` でバックアップを取り、`gzip -t` と末尾の「PostgreSQL database dump complete」で確かめる | 止まる。旧コードのまま |
| 4-4 | 新しいイメージで `alembic upgrade head`（028〜032 を 1 つのトランザクションで）。開催中の大会・進行中の試合があると 032 が止め、すべて戻る | 止まる。版は 027 のまま、旧コードのまま（公開の延期。切り戻しは不要） |
| 4-5 | `docker compose up -d`（入れ替え）と readiness（12 回・60 秒） | 止まる。切り戻しの手順へ |
| 4-6 | 公開の確認 `scripts/rc4_release_check.py --since <4-4 の開始の時刻>`（件数だけ） | 止まる。切り戻しの手順へ |

- 4-4 から 4-5 の間（数十秒）は、旧コードが 032 のスキーマで動く。旧コードで作った大会は `roster` になり、旧コードで始めた旧方式の大会の試合は 4-6 が数える
- 4-6 が出す値は件数だけ（`rc4_release_check name=value`）。`RESULT=PASS` で終わる

## 5. 公開後の確認

- [ ] Deploy の実行が成功し、ログの最後が `rc4_release_check RESULT=PASS` と `Deploy sha-<新> complete`
- [ ] `curl -fsS https://app.axelia-esports.jp/health/ready` が 200
- [ ] 画面: ログイン（全員が一度ログインし直しになる）、大会一覧・詳細、試合ページ、チームページ、マイチーム → 届いた招待、設定 → 所属の確認
- [ ] 主催者の大会管理で、旧方式の未開始の大会に「名簿の方式に切り替える」が出る
- [ ] 公開の確認で出た `legacy_tournaments_not_started`（切り替えが要る大会の数）と `memberships_unconfirmed_active`（確認が要る所属の数）を作業記録に残し、主催者・利用者への案内に使う
- [ ] 問題がなければ、`~/rollback-images-sha-<新>.yml` と旧イメージは 1 週間残してから片付ける

## 6. Deploy の workflow を無効に戻す

```bash
gh workflow disable deploy-demo.yml --repo Nonname-organic/esports-platform
```

公開の前と同じ状態（main への push で本番が変わらない）に戻す。次の版を出すときに、この手順の 2 からやり直す。

## 7. 止める条件

次のどれかが起きたら、手で直そうとせずに止め、[切り戻しの手順](RC4_ROLLBACK_RUNBOOK.md)で判断する。

- 4-5 の readiness が通らない、または 4-6 が `RESULT=FAIL`
- 5 で 5xx が続く、ログに未知の列・表のエラーが続く、api のメモリが上限に近づく
- 4-4 で止まった（開催中の大会がある）ときは切り戻さない。大会が終わってから 3 をやり直す（Build & Push を手動で動かす）

## 8. 公開の後に別に行うサーバーの設定（RC2 の 4 章。今回の公開の条件ではない）

Deploy はイメージを入れ替えるだけで、サーバーの compose・nginx の設定ファイルは更新しない。RC2 で加わった次の設定は、
今のサーバーの設定ファイルのままでは効かない（無くても RC4 は動く）。入れるときは RC2 の手順書の 4 章の順に、別の作業として行う。

| 設定 | 効果 | 入れないとき |
|---|---|---|
| `/opt/app/.env` の `DB_PASSWORD` と、DB のパスワードの確認・変更 | 既定のパスワードでの起動を断る | 今のまま |
| compose の `REQUIRE_STRONG_SECRETS`・`USE_REDIS_QUEUE` の固定、接続数の上限（api 6+6 ほか） | 弱い秘密情報での起動を断る、混雑時の接続数超過を防ぐ | `.env` の設定のまま |
| nginx の `client_max_body_size 11m` | 5〜10MB の添付を受け付ける | 5MB を超える添付は 413 |
