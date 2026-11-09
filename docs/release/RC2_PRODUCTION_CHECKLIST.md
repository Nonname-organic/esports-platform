# RC2 本番環境の設定チェックリスト（ConoHa VPS）

[RC1 のチェックリスト](RC1_PRODUCTION_CHECKLIST.md)を置き換える。RC1 の DB パスワードの変更手順は、生成した値を `.env` に
書く方法がなく、そのとおりに進めると DB 側だけが変わってアプリが接続できなくなるので使わない（4 章の手順を使う）。

- 秘密情報の実値は、この文書にも確認コマンドの出力にも出さない。下のコマンドは「設定あり／なし」「一致／不一致」だけを表示する
- サーバー上の作業はすべて `/opt/app` で行う（[phase10](../phase10_vps_conoha.md#サーバー上で-docker-compose-を叩くときの注意) を参照）
- 作業の順序は [RC2_DEPLOYMENT_RUNBOOK.md](RC2_DEPLOYMENT_RUNBOOK.md) に従う。この文書は設定の中身と確認方法をまとめる

## 1. 必須の設定

| 変数 | 置き場所 | 条件 | 守らないと |
|---|---|---|---|
| `SECRET_KEY` | `backend/.env` | 32 文字以上のランダム値（例: `openssl rand -hex 32`）。見本の値（`change` 等を含む）は不可 | 起動しない（デプロイの入れ替え前の検査で止まる） |
| `DB_PASSWORD` | `/opt/app/.env` **と** `backend/.env`（同じ値） | 空・`esports_pass`・`password`・`postgres`・`changeme` は不可。DB の実際のパスワードと一致すること | `/opt/app/.env` に無い: RC2 の compose ではすべてのコマンド（cron のバックアップ・死活監視を含む）が止まる／`backend/.env` が既定値: API が起動しない／DB と不一致: 入れ替えた後で readiness が落ちる |
| `COMPOSE_FILE` | `/opt/app/.env` | `docker-compose.yml:docker-compose.prod.yml:docker-compose.tls.yml:docker-compose.conoha.yml` | TLS の設定が外れてサイトが落ちる |
| `ALLOWED_ORIGINS` | `backend/.env` | `https://app.axelia-esports.jp` | ブラウザからの API 呼び出しが CORS で失敗する |
| `ALLOWED_HOSTS` | `backend/.env` | API が呼ばれる名前（`app.axelia-esports.jp`）。`*` は不可。空なら `ALLOWED_ORIGINS` から導く。`localhost` / `127.0.0.1` / `api` は常に許可 | 400（Host 不一致） |
| `FRONTEND_BASE_URL`・`PUBLIC_WEB_URL` | `backend/.env` | `https://app.axelia-esports.jp` | メール内のリンク・Bot の案内先が誤る |

手で compose を操作するとき（Deploy の外）:

| 変数 | 条件 | 守らないと |
|---|---|---|
| `IMAGE_ORG`・`IMAGE_TAG` | `run`・`pull`・`up` では必ず指定する（例: `IMAGE_ORG=nonname-organic IMAGE_TAG=sha-<版>`）。`latest` への逃げ道はない（#42） | 「invalid reference format」で止まる。`config`・`ps`・`logs`・`exec`・`images` は指定なしでも動く |

compose（`docker-compose.prod.yml` / `docker-compose.conoha.yml`）が設定するので、`.env` で変えないもの:

| 変数 | 値 | 理由 |
|---|---|---|
| `REQUIRE_STRONG_SECRETS` | `true` | 既定値・見本値のまま起動しない |
| `USE_REDIS_QUEUE` | `true` | 未設定だとキューが AWS SQS に向かう |
| `DB_POOL_SIZE` / `DB_MAX_OVERFLOW` | api 6/6・worker 2/1・scheduler 2/1 | postgres の `max_connections=20` に収める（最大 18、残り 2 は運用作業用） |

## 2. 既定値のままにするもの・使ってはいけない値

| 変数 | 本番の値 | 理由 |
|---|---|---|
| `ENVIRONMENT` | `demo`（既定） | `prod` / `mvp` にすると、旧イベント発行が AWS EventBridge に向かう |
| `EXPOSE_API_DOCS` | `false`（既定） | 管理系を含む全 API の一覧が誰でも読める |
| `EXPOSE_METRICS` | `false`（既定） | 認証なしで内部の指標が読める |
| `LOG_LEVEL` | `INFO`（既定） | `DEBUG` ではパスワード再設定メールの本文（リンク）がログに出る |
| `ANALYTICS_EXPORT_BUCKET` | 空（既定） | 分析イベントの書き出しは停止。設定する場合は画像用とは別の非公開バケットにする |
| `DEBUG` | `false`（既定） | |

## 3. 機能ごとの設定

| 項目 | 設定 | 初期公開での扱い |
|---|---|---|
| HTTPS・ドメイン | `nginx/nginx-tls.conf`（Let's Encrypt、HSTS 180 日）。証明書の自動更新は `systemctl list-timers \| grep certbot` と `sudo certbot renew --dry-run` で確認 | 必須 |
| アップロードの上限 | nginx 11m（RC2 の `nginx.conf`・`nginx-tls.conf`）。添付 10MB、画像 5MB、スコアボード OCR 5MB | サーバーの nginx の設定を新しくしないと、5〜10MB の添付は 413 のまま |
| スコアボード OCR | 一辺 8192px・16,777,216 画素まで、PNG・JPEG・WebP。同時に 2 件まで（3 件目は 429） | 変更不要 |
| SMTP（Resend） | `SMTP_HOST` / `SMTP_PORT` / `SMTP_USER` / `SMTP_PASSWORD` / `MAIL_FROM` / `MAIL_FROM_NAME` | 未設定だとパスワード再設定メールが届かない（応答は同じで、利用者には分からない）。公開前に設定し、自分宛てに 1 通送って確認する |
| PostgreSQL | `postgres:15-alpine`、`max_connections=20`、データは `postgres_prod_data` ボリューム | — |
| Redis | `redis:7-alpine`、永続化なし（`--save ""`）。キャッシュ・キュー・レート制限に使う | 再起動でキューとレート制限のカウンタは消える |
| 画像の保存先 | `S3_BUCKET_NAME` / `S3_ENDPOINT_URL`（Supabase Storage） | 未設定ならコンテナ内（`uploads_data` ボリューム）に保存 |
| Discord | `DISCORD_CLIENT_ID` / `DISCORD_CLIENT_SECRET` / `DISCORD_REDIRECT_URI`、Bot は `DISCORD_BOT_TOKEN`・`BOT_API_TOKEN`（compose の `discord` プロファイル） | 設定しない。設定した場合、大会の Discord 設定には、主催者本人か管理者であることに加えて、Discord 側のサーバー管理権限が要る（管理者も同じ） |
| Riot | `RIOT_API_KEY` | 設定しない。未設定なら同期は「Riot API連携が未設定です」で止まり、Riot ID は自己申告の表示だけ |
| ログ | `docker-compose.conoha.yml` で 1 コンテナ最大 30MB（10MB×3）。`ENVIRONMENT=demo` では色付きで出る | 集計の前に色の制御文字を除く（5 章） |
| バックアップ | `scripts/install-ops-cron.sh` で毎日 03:15 UTC、14 世代。保存先は `BACKUP_S3_BUCKET` + `S3_ENDPOINT_URL` | 公開前に 1 回手で取得し、復元できることを確認する（phase10「バックアップが復元できることの確認」） |
| 障害通知 | `HEALTHCHECK_WEBHOOK_URL`（Discord Webhook） | 推奨 |

## 4. 公開前の確認コマンド（値は表示しない）

```bash
cd /opt/app

# DB_PASSWORD が両方にあり、同じ値で、既定値でないこと
for f in .env backend/.env; do
  printf '%-13s DB_PASSWORD: ' "$f"
  grep -q '^DB_PASSWORD=.\+' "$f" && echo "設定あり" || echo "未設定"
done
[ "$(grep '^DB_PASSWORD=' .env | cut -d= -f2- | sha256sum)" = \
  "$(grep '^DB_PASSWORD=' backend/.env | cut -d= -f2- | sha256sum)" ] && echo "一致" || echo "不一致"
grep -q -x -E 'DB_PASSWORD=(esports_pass|password|postgres|changeme)?' backend/.env \
  && echo "既定値・空（要変更）" || echo "既定値ではない"

# DB の実際のパスワードと backend/.env が一致すること（値は標準入力で渡し、結果だけを出す）
grep '^DB_PASSWORD=' backend/.env | cut -d= -f2- | docker compose exec -T postgres sh -c \
  'IFS= read -r PGPASSWORD; export PGPASSWORD; psql -h postgres -U esports_user -d esports_db -tAc "select 1" >/dev/null 2>&1 && echo "DB と一致" || echo "DB と不一致（または接続できない）"'

# SECRET_KEY が 32 文字以上で、見本の値でないこと
k=$(grep '^SECRET_KEY=' backend/.env | cut -d= -f2-)
[ ${#k} -ge 32 ] && echo "長さ OK" || echo "短い"
echo "$k" | grep -q -i -E 'change|example|your[-_]|dummy|placeholder|ci-test|replace' && echo "見本の値（要変更）" || echo "見本の値ではない"
unset k

# 公開してはいけない設定が有効になっていないこと
grep -i -E '^(EXPOSE_API_DOCS|EXPOSE_METRICS|DEBUG)=true' backend/.env && echo "要確認" || echo "OK"
grep -i -E '^LOG_LEVEL=DEBUG' backend/.env && echo "要確認" || echo "OK"
grep -i -E '^ENVIRONMENT=(prod|mvp)' backend/.env && echo "要確認（AWS へ向かう）" || echo "OK"
```

- すべて「設定あり／一致／既定値ではない／DB と一致／OK」になってから Deploy を有効にする
- DB との一致の確認では `-h postgres` を必ず付ける。コンテナの中でソケットから接続すると、パスワードなし（trust）で通ってしまい、確認にならない
- デプロイの入れ替え前の検査は値の強さだけを見て、DB に接続できるかは見ない。打ち間違いは上の「DB と一致」でしか見つからない

### DB パスワードが既定値だった場合の変更手順

postgres の `POSTGRES_PASSWORD` は**初回の初期化時にしか使われない**。`.env` を書き換えただけでは DB の実際のパスワードは変わらない。
DB 側と `.env` 側の両方を、値を画面に出さずに変える。この手順は使い捨ての postgres 15 で確かめた（本番では未実施）。

```bash
cd /opt/app
# 1. 退避（権限 600。作業が終わったら削除する）
install -m 600 .env ~/env-root.bak && install -m 600 backend/.env ~/env-backend.bak
# 2. 生成（変数にだけ置く。16 進なので SQL と sed でそのまま扱える）
NEW=$(openssl rand -hex 24)
# 3. DB 側（標準入力で渡すので、プロセス一覧と psql の画面に出ない）
printf "ALTER USER esports_user PASSWORD '%s';\n" "$NEW" \
  | docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -q -U esports_user -d esports_db
# 4. .env 側（/opt/app/.env に行がなければ先に足す）
grep -q '^DB_PASSWORD=' .env || echo 'DB_PASSWORD=' >> .env
sed -i "s/^DB_PASSWORD=.*/DB_PASSWORD=$NEW/" .env backend/.env
unset NEW
# 5. 上の「公開前の確認コマンド」で、2 ファイルの一致・既定値でないこと・DB と一致を確かめる
```

- 変えた直後から、稼働中の api・worker・scheduler は新しい接続を作れなくなる（プールに残った接続は使い続ける）。
  変更は Deploy を有効にする直前に行い、すぐにコンテナを作り直す
- **失敗したとき**:
  - 3 は通ったが 4 で失敗した: `.env` を退避から戻し、DB 側を元の値に戻す（3 と同じ形で元の値を渡す）か、新しい値で 2 からやり直す。
    生成した値はもう手元にないので、`.env` に同じ値を書き直すことはできない
  - 3 で失敗した: DB は変わっていない。`.env` も触っていないので、原因を直してからやり直す
  - 5 で「DB と不一致」: アプリを作り直す前に止まる。3〜5 をやり直す
- 値を `-e PGPASSWORD=...` やコマンドの引数で渡さない。アプリのコンテナで任意のコードを動かして接続を試さない

## 5. 公開後の初期監視

| いつ | 項目 | 確認方法（`/opt/app` で） | 期待値 |
|---|---|---|---|
| デプロイ直後 | API | `curl -fsS https://app.axelia-esports.jp/health/ready` | `{"status":"ready",...}` |
| デプロイ直後 | 画面 | `curl -s -o /dev/null -w '%{http_code}\n' https://app.axelia-esports.jp/` | 200 |
| デプロイ直後 | マイグレーション | `docker compose exec -T postgres psql -U esports_user -d esports_db -tAc 'select version_num from alembic_version'` | `030` |
| デプロイ直後 | 版 | `docker compose images` | api・worker・scheduler・frontend が新しい版 |
| デプロイ直後 | コンテナ | `docker compose ps` | すべて running、api は healthy |
| 当日 | DB 接続数 | `docker compose exec -T postgres psql -U esports_user -d esports_db -tAc "select count(*) from pg_stat_activity where datname='esports_db'"` | 18 以下 |
| 当日 | Redis | `docker compose exec -T redis redis-cli ping` | PONG |
| 当日 | 5xx | `docker compose logs --since 1h api \| sed -E 's/\x1b\[[0-9;]*m//g' \| grep -c 'status_code=5'` | 0 に近いこと。色の制御文字を除かないと数えられない |
| 当日 | 接続あふれ | `docker compose logs --since 1h \| grep -c -i 'too many clients'` | 0 |
| 当日 | OCR | `docker compose logs --since 1h api \| sed -E 's/\x1b\[[0-9;]*m//g' \| grep -c 'scoreboard-ocr.*status_code=429'`、`docker stats --no-stream` | 429 が続かない。api のメモリが上限（1GB）に近づかない |
| 当日 | worker・scheduler | `docker compose logs --since 1h worker scheduler \| tail -20` | 例外が続いていない |
| 当日 | メール | 自分のアドレスでパスワード再設定を 1 回実行 | 届く（SMTP 設定時） |
| 当日 | Discord・Riot | 連携画面を開く | 「未設定」の案内が出る（初期公開では無効） |
| 翌朝 | バックアップ | `ls -lt backups \| head -3`、保存先の一覧 | 当日の 03:15 UTC の分がある |
| 翌朝 | 夜間ジョブ | `docker compose logs --since 24h scheduler \| grep -E 'daily_(aggregation\|s3_export)'` | 実行され、書き出しは「not configured — skipping」 |
| 1 週間 | リソース | `docker stats --no-stream`、`df -h` | メモリ上限・ディスクに余裕がある |
| 1 週間 | 証明書 | `sudo certbot renew --dry-run` | 成功 |
