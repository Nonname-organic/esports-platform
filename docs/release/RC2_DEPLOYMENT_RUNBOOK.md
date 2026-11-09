# RC2 本番公開の手順（ConoHa VPS）

- 作成: 2026-11-09（RC2 統合・必須修正工程）。**本番ではどれも未実行**
- [phase10 の「RC1 本番公開の手順」](../phase10_vps_conoha.md#rc1-本番公開の手順2026-11)を置き換える
- 設定の中身と確認コマンドは [RC2_PRODUCTION_CHECKLIST.md](RC2_PRODUCTION_CHECKLIST.md)、切り戻しは [RC2_ROLLBACK_RUNBOOK.md](RC2_ROLLBACK_RUNBOOK.md)
- 秘密情報の値は、どの手順でも画面・ログ・コマンドの引数に出さない
- RC3 を出すときも、この手順をそのまま使う。RC2 との違い（デプロイ後に全利用者が一度ログインし直しになる、公開の集計のキャッシュ、切り戻し中のセッション）は [RC3_RELEASE_NOTES.md](RC3_RELEASE_NOTES.md) の「本番への反映について」

## 0. 全体の流れと承認

本番が変わる操作は 3 つ（4・5・6）。それぞれ別に承認を取る。PR のマージ（2）だけでは本番は変わらない。

| 段 | 作業 | 本番への影響 | 承認 |
|---|---|---|---|
| 1 | マージ前の確認 | なし | — |
| 2 | PR を main へマージ | なし（Deploy が無効なので、Build & Push がイメージを作るだけ） | コード統合の承認 |
| 3 | サーバーの状態を控える | なし（読み取りだけ） | — |
| 4 | サーバー側の事前作業（`.env`・DB パスワード・compose と nginx の更新） | nginx の再起動で数秒、DB パスワードの変更で新しい接続 | 要 |
| 5 | 先行マイグレーション（028〜030） | 本番 DB が変わる。旧コードはそのまま動く | 要 |
| 6 | Deploy の有効化と実行 | アプリのコンテナが新しい版に入れ替わる | 要（本番適用の開始） |
| 7 | デプロイ後の確認 | なし | — |

## 1. マージ前の確認

- [ ] PR の CI（qa.yml）が通っている
- [ ] PR の head が、PR の本文に書いた RC2 のコミット・ツリーと同じ
- [ ] Deploy workflow が無効のまま: `gh api repos/Nonname-organic/esports-platform/actions/workflows/deploy-demo.yml --jq .state` が `disabled_manually`

## 2. PR を main へマージする

- マージで Build & Push が走り、`ghcr.io/nonname-organic/esports-platform-{api,worker,frontend}:sha-<マージコミットの先頭 7 文字>` と `:latest` を作る
- Deploy は無効なので走らない。Build & Push の後に Deploy の実行が増えていないことを確かめる:
  `gh run list --workflow deploy-demo.yml --limit 3 --repo Nonname-organic/esports-platform`
- 新しい版のタグ（以下 `sha-<新>`）を控える

## 3. サーバーの状態を控える（読み取りだけ）

```bash
cd /opt/app
git rev-parse HEAD; git status --short                         # 手元の変更（nginx-tls.conf のドメインの置き換え）を確かめる
docker compose ps
docker compose exec -T postgres psql -U esports_user -d esports_db -tAc 'select version_num from alembic_version'   # 027 のはず

# 稼働中のイメージを digest で控え、切り戻し用の上書きファイルを作る（RC2_ROLLBACK_RUNBOOK の 1 章）
OUT=~/rollback-images.yml
echo "services:" > "$OUT"
for svc in api worker scheduler frontend; do
  ref=$(docker inspect --format '{{.Config.Image}}' "$(docker compose ps -q $svc)")
  dig=$(docker image inspect --format '{{index .RepoDigests 0}}' "$ref")
  printf '  %s:\n    image: %s\n' "$svc" "$dig" >> "$OUT"
  echo "$svc: $ref -> $dig"
done
```

- 4 サービスの版（今は `sha-c0a80ad` のはず）と digest を、作業記録に残す。`~/rollback-images.yml` は作業が終わるまで消さない
- digest が取れない（`RepoDigests` が空）場合は、そのイメージを `docker image save` で退避する。切り戻しで取得し直せない恐れがある
- サーバーから GHCR のイメージを取得できるかを確かめる（パッケージが非公開なら、`read:packages` だけを持つトークンで `docker login ghcr.io` が要る。前回の Deploy のログイン情報は期限が切れている）:
  `docker pull "$(sed -n 's/^    image: //p' ~/rollback-images.yml | head -1)"`

## 4. サーバー側の事前作業（順序どおり）

Deploy はイメージを入れ替えるだけで、サーバーの compose・nginx の設定は更新しない。RC2 の設定はここで入れる。

1. **Deploy は無効のまま**にしておく
2. バックアップを取り、確かめる（phase10「2. バックアップ」と同じ。`gzip -t` と末尾の「dump complete」）
3. **`/opt/app/.env` に `DB_PASSWORD` を入れる（新しい compose を置く前に）。** 逆の順にすると、新しい compose は `DB_PASSWORD` が無いと
   すべてのコマンドを止めるので、cron のバックアップ・死活監視も止まる。値は `backend/.env` と同じにする（チェックリスト 4 章の手順で、画面に出さずに入れる）
4. DB パスワードを確かめる。既定値なら変える（チェックリスト 4 章）。最後に「DB と一致」を必ず確かめる
5. 設定ファイルを RC2 の版にする
   ```bash
   cd /opt/app
   git diff --stat                                   # 手元の変更が nginx-tls.conf のドメインの置き換えだけであること
   git checkout -- nginx/nginx-tls.conf              # 置き換えを一度戻す
   git pull --ff-only origin main
   sed -i 's/YOUR_DOMAIN/app.axelia-esports.jp/g' nginx/nginx-tls.conf
   docker compose config --quiet && echo "compose OK"
   ```
6. nginx を**再起動**する（ファイル単体のバインドマウントなので、`nginx -s reload` では新しいファイルが見えない）
   ```bash
   IMAGE_ORG=nonname-organic IMAGE_TAG=sha-c0a80ad docker compose restart nginx   # IMAGE_TAG は稼働中の版
   docker compose exec -T nginx nginx -T 2>/dev/null | grep -c 'client_max_body_size 11m'   # 1 以上
   curl -fsS https://app.axelia-esports.jp/health/ready
   ```
7. SMTP を確かめる（自分のアドレスでパスワード再設定を 1 回。チェックリスト 3 章）
8. 週 1 回の `docker system prune` の cron が、切り戻し用の旧イメージを消さないようにする（作業が終わるまで止めるか、3 の `docker image save` で退避する）

## 5. 先行マイグレーション（推奨）

Deploy は `up -d` で入れ替えてから readiness を待ち、その後に `alembic upgrade head` を流す。その間（最大 60 秒ほど）、
新しいコードが 027 のスキーマで動き、結果の登録・確認が 500 になる（S13）。旧コード（`sha-c0a80ad`）は 030 のスキーマで動くので、
Deploy の前に、新しいイメージでマイグレーションだけを先に流す。

```bash
cd /opt/app
NEWTAG=sha-<新>                                     # 2 で控えた版。打ち間違えないよう、ここで一度だけ書く
docker pull ghcr.io/nonname-organic/esports-platform-api:$NEWTAG
docker image inspect --format '{{index .RepoDigests 0}}' ghcr.io/nonname-organic/esports-platform-api:$NEWTAG   # 記録する
./scripts/backup-db.sh                              # 直前のバックアップ（確かめ方は 4-2 と同じ）
IMAGE_ORG=nonname-organic IMAGE_TAG=$NEWTAG docker compose run --rm --no-deps -T api alembic upgrade head
docker compose exec -T postgres psql -U esports_user -d esports_db -tAc 'select version_num from alembic_version'   # 030
curl -fsS https://app.axelia-esports.jp/health/ready                                                                  # 旧コードのまま 200
```

- マイグレーションは 1 つのトランザクションで流れる。失敗したら版は 027 のまま、データも変わらない。原因を調べるまで先へ進まない
- 028 で非公開・限定公開に直る大会は、一覧・検索・ホームから消える（本来の動き）。事前に対象を見るには phase10 の「マイグレーション 028〜030 は戻さない」の SELECT を使う
- 旧コードのまま、ログイン・大会一覧・試合ページが開くことを確かめる

## 6. Deploy の有効化と実行

```bash
gh workflow enable deploy-demo.yml --repo Nonname-organic/esports-platform
gh workflow run build.yml --ref main --repo Nonname-organic/esports-platform -f reason="RC2 deploy"
gh run watch --repo Nonname-organic/esports-platform    # Build & Push の後に Deploy — Demo が走る
```

- Deploy には手動実行の口がない。main の Build & Push を手動で動かすと、その完了で Deploy が走る（次の push を待ってもよい）
- Deploy は、新しいイメージで設定を検査し（不備なら入れ替えずに止まる）、`up -d`、readiness（12 回・60 秒）、`alembic upgrade head`（5 を済ませていれば何もしない）の順に進む
- Deploy が失敗したら、Deploy をもう一度無効にしてから原因を調べる（同じ版の再デプロイを防ぐ）

## 7. デプロイ後の確認

- チェックリスト 5 章の「デプロイ直後」をすべて満たす。4 サービスの版が `sha-<新>`、`alembic_version` が 030
- 画面: ログイン、大会一覧・詳細・ブラケット、試合ページ、結果の報告（自分の大会で）、募集（「チームを探す」を含む）、通知
- 5xx は色の制御文字を除いてから数える（チェックリスト 5 章）
- 問題がなければ、`~/rollback-images.yml` と旧イメージは 1 週間残してから片付ける。prune の cron を止めていたら戻す

## 8. 止める条件

次のどれかが起きたら、手で直そうとせずに止め、切り戻すかを判断する（[RC2_ROLLBACK_RUNBOOK.md](RC2_ROLLBACK_RUNBOOK.md)）。

- 4 の後、readiness が 200 にならない、または「DB と不一致」
- 5 のマイグレーションが失敗した（版は 027 のまま。切り戻しは不要）
- 6 の Deploy が失敗した、または readiness が通らない
- 7 で 5xx が続く、ログに未知の列・表のエラーが続く、api のメモリが上限に近づく

## 9. main のブランチ保護（提案。今回は設定しない）

今の main には保護もルールセットもなく、QA の結果はマージにもデプロイにも効かない（Deploy は Build & Push の成功だけを条件にする）。
設定するなら次を提案する。設定の変更は別の承認で行う。

| 設定 | 値 | 理由 |
|---|---|---|
| 直接の push | 禁止（PR 経由のみ） | マージが本番適用の入口になりうるため |
| 必須のチェック | `qa.yml` の `quality-gate`（`backend-lint`・`backend-tests`・`security`・`frontend` の結果をまとめる job） | 回帰と認可のテストを通らない変更を main に入れない |
| レビュー | 1 名以上の承認、新しい push で承認を取り消す | 承認後の差し替えを防ぐ |
| 強制 push・ブランチの削除 | 禁止 | 履歴の書き換えで、デプロイした版を追えなくなるのを防ぐ |
| 管理者にも適用 | 有効 | 例外の経路を残さない |
| Deploy の条件（workflow の変更。別の作業） | `environment: demo` に必須のレビュー者を付ける | Build & Push の成功だけで本番が変わらないようにする |
