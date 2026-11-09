# RC1 本番環境の設定チェックリスト（ConoHa VPS）

秘密情報の実値はこの文書にも、確認コマンドの出力にも出さない。下のコマンドは「設定あり／なし」「一致／不一致」だけを表示する。
サーバー上の作業はすべて `/opt/app` で行う（[phase10](../phase10_vps_conoha.md#サーバー上で-docker-compose-を叩くときの注意) を参照）。

## 1. 必須の設定

| 変数 | 置き場所 | 条件 | 守らないと |
|---|---|---|---|
| `SECRET_KEY` | `backend/.env` | 32 文字以上のランダム値（例: `openssl rand -hex 32`）。見本の値（`change` 等を含む）は不可 | 起動しない（デプロイ前の検査で止まる） |
| `DB_PASSWORD` | `/opt/app/.env` **と** `backend/.env`（同じ値） | 空・`esports_pass`・`password`・`postgres`・`changeme` は不可 | `/opt/app/.env` に無い: compose がその場で止まる／`backend/.env` が既定値: API が起動しない |
| `COMPOSE_FILE` | `/opt/app/.env` | `docker-compose.yml:docker-compose.prod.yml:docker-compose.tls.yml:docker-compose.conoha.yml` | TLS 設定が外れてサイトが落ちる |
| `ALLOWED_ORIGINS` | `backend/.env` | `https://app.axelia-esports.jp` | ブラウザからの API 呼び出しが CORS で失敗する |
| `ALLOWED_HOSTS` | `backend/.env` | API が呼ばれる名前（`app.axelia-esports.jp`）。`*` は不可。`localhost` / `127.0.0.1` / `api` は常に許可 | 400（Host 不一致） |
| `FRONTEND_BASE_URL`・`PUBLIC_WEB_URL` | `backend/.env` | `https://app.axelia-esports.jp` | メール内のリンク・Bot の案内先が誤る |

compose（`docker-compose.prod.yml` / `docker-compose.conoha.yml`）が設定するので、`.env` で変えないもの:

| 変数 | 値 | 理由 |
|---|---|---|
| `REQUIRE_STRONG_SECRETS` | `true` | 既定値・見本値のまま起動しない |
| `USE_REDIS_QUEUE` | `true` | 未設定だとキューが AWS SQS に向かう |
| `DB_POOL_SIZE` / `DB_MAX_OVERFLOW` | api 6/6・worker 2/1・scheduler 2/1 | postgres の `max_connections=20` に収める（最大18、残り2は運用作業用） |

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
| SMTP（Resend） | `SMTP_HOST` / `SMTP_PORT` / `SMTP_USER` / `SMTP_PASSWORD` / `MAIL_FROM` / `MAIL_FROM_NAME` | 未設定だとパスワード再設定メールが届かない（応答は同じで、利用者には分からない）。公開前に設定し、自分宛てに 1 通送って確認する |
| PostgreSQL | `postgres:15-alpine`、`max_connections=20`、データは `postgres_prod_data` ボリューム | — |
| Redis | `redis:7-alpine`、永続化なし（`--save ""`）。キャッシュ・キュー・レート制限に使う | 再起動でキューとレート制限のカウンタは消える |
| 画像の保存先 | `S3_BUCKET_NAME` / `S3_ENDPOINT_URL`（Supabase Storage） | 未設定ならコンテナ内（`uploads_data` ボリューム）に保存 |
| Discord | `DISCORD_CLIENT_ID` / `DISCORD_CLIENT_SECRET` / `DISCORD_REDIRECT_URI`、Bot は `DISCORD_BOT_TOKEN`・`BOT_API_TOKEN`（compose の `discord` プロファイル） | 実 API が未確認のため設定しない。未設定なら連携画面は「OAuth が未設定です」と案内し、Bot 用 API はすべて 401 |
| Riot | `RIOT_API_KEY` | 設定しない。未設定なら同期は「Riot API連携が未設定です」で止まり、Riot ID は自己申告の表示だけ |
| ログ | `docker-compose.conoha.yml` で 1 コンテナ最大 30MB（10MB×3） | — |
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

すべて「設定あり／一致／既定値ではない／OK」になってから main へマージする。
同じ検査はデプロイでも新しいイメージで自動に行われ、不備があれば稼働中のコンテナを入れ替えずに止まる。

### DB パスワードが既定値（`esports_pass`）だった場合

postgres の `POSTGRES_PASSWORD` は**初回の初期化時にしか使われない**。`.env` を書き換えただけでは
DB の実際のパスワードは変わらないので、DB 側も変える。値は画面に出さない。

```bash
cd /opt/app
NEW=$(openssl rand -hex 24)
docker compose exec -T postgres psql -U esports_user -d esports_db -c "ALTER USER esports_user PASSWORD '$NEW'"
# backend/.env と /opt/app/.env の DB_PASSWORD を同じ $NEW に書き換える（エディタで。echo しない）
unset NEW
```

変えた直後から、API などの新しい接続は古いパスワードでは通らなくなる。**RC1 のデプロイ直前**に行い、
続けてデプロイ（main へのマージ、または直近の Deploy の再実行）でコンテナを作り直す。
（`ALTER USER` での変更自体はローカルの使い捨て DB で確認した。本番では未実施）

## 5. 公開後の初期監視

### 公開前にローカルで確認済みのこと（2026-11-09）

- 本番と同じ構成（postgres 15・接続上限 20・同じプール設定・`REQUIRE_STRONG_SECRETS=true`・リポジトリの `nginx.conf`）で、
  起動直後の E2E が直列 1 回・並列 3 回とも 21/21。DB の同時接続数は最大 14（上限 20）
- デプロイ前の設定検査が、既定値なら止まり（値は出さない）、固有の値なら通る
- バックアップの取得・別 DB への復元・件数と版の一致（postgres 15）
- 028〜030 の適用・戻し、030 の戻しの前提条件、旧版のコードが 030 のスキーマで動くこと

### 公開後に確認すること

| いつ | 項目 | 確認方法（`/opt/app` で） | 期待値 |
|---|---|---|---|
| デプロイ直後 | API | `curl -fsS https://app.axelia-esports.jp/health/ready` | `{"status":"ready",...}` |
| デプロイ直後 | 画面 | `curl -s -o /dev/null -w '%{http_code}\n' https://app.axelia-esports.jp/` | 200 |
| デプロイ直後 | マイグレーション | `docker compose exec -T api alembic current` | `030 (head)` |
| デプロイ直後 | コンテナ | `docker compose ps` | すべて running、api は healthy |
| 当日 | DB 接続数 | `docker compose exec -T postgres psql -U esports_user -d esports_db -tAc "select count(*) from pg_stat_activity where datname='esports_db'"` | 18 以下 |
| 当日 | Redis | `docker compose exec -T redis redis-cli ping` | PONG |
| 当日 | エラー | `docker compose logs --since 1h api \| grep -c 'status_code=5'`、`docker compose logs --since 1h \| grep -c -i 'too many clients'` | 0 に近いこと／0 |
| 当日 | worker・scheduler | `docker compose logs --since 1h worker scheduler \| tail -20` | 例外が続いていない |
| 当日 | メール | 自分のアドレスでパスワード再設定を 1 回実行 | 届く（SMTP 設定時） |
| 当日 | Discord・Riot | 連携画面を開く | 「未設定」の案内が出る（初期公開では無効） |
| 翌朝 | バックアップ | `ls -lt backups \| head -3`、保存先の一覧 | 当日の 03:15 UTC の分がある |
| 翌朝 | 夜間ジョブ | `docker compose logs --since 24h scheduler \| grep -E 'daily_(aggregation\|s3_export)'` | 実行され、書き出しは「not configured — skipping」 |
| 1 週間 | リソース | `docker stats --no-stream`、`df -h` | メモリ上限・ディスクに余裕がある |
| 1 週間 | 証明書 | `sudo certbot renew --dry-run` | 成功 |
