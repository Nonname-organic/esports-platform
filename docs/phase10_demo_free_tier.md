# Phase 10 — $0 運用インフラ（Oracle Cloud 版）

AWS（EC2 + CloudFront + S3）の無料期間終了に伴い、**完全無料で常時稼働**できる構成へ移行するためのガイドです。

> **2026-08 改訂**: 旧版は Fly.io + Neon + Upstash 前提でしたが、Fly.io は無料枠を廃止（新規は $5 トライアルのみ）、
> Koyeb も新規無料枠を停止したため全面改訂しました。2026年時点で「常時稼働コンテナが無料」なのは
> 実質 **Oracle Cloud Always Free** のみです。

---

## アーキテクチャ概要

**現行の EC2 構成（docker-compose 全部載せ）をそのまま Oracle Cloud の無料VMへ移す**方針です。
アプリケーションコードの変更は不要で、置き換わるのはインフラ層のみです。

```
ユーザー
  │ HTTPS
  ▼
DuckDNS (無料DNS: xxx.duckdns.org)
  │
  ▼
Oracle Cloud VM — VM.Standard.A1.Flex (ARM 2 OCPU / 12GB, Always Free)
  └─ docker compose
       ├─ nginx      ← Let's Encrypt でTLS終端（CloudFront の代替）
       ├─ frontend   ← Next.js
       ├─ api        ← FastAPI
       ├─ worker     ← バックグラウンドジョブ（Redis キュー）
       ├─ postgres   ← DB（RDS の代替・VM内）
       ├─ redis      ← キャッシュ + キュー（SQS の代替）
       └─ discord-bot（profile: discord）

Cloudflare R2 (S3互換・egress無料)
  └─ Hero動画・アップロードファイル（S3 + CloudFront 配信の代替）

GitHub Actions + GHCR
  └─ push → multi-arch (amd64+arm64) ビルド → SSH デプロイ（従来と同じ）
```

| 旧 (AWS) | 新 (無料) |
|---|---|
| EC2 t2.micro | Oracle VM.Standard.A1.Flex（2 OCPU / 12GB — 大幅スペックUP） |
| CloudFront (TLS/CDN) | nginx + Let's Encrypt（TLS）。CDNなし※ |
| S3 (動画・ファイル) | Cloudflare R2（10GB, egress 無料） |
| Route 53 相当 | DuckDNS（無料サブドメイン） |
| SQS | Redis リスト（実装済み `USE_REDIS_QUEUE=true`） |
| RDS 相当 | compose 内 PostgreSQL（従来どおり） |

※ 動画など重いアセットは R2 から直接配信するため、CDNなしでも体感への影響は小さい。
独自ドメインを取得すれば Cloudflare 無料プランのCDNを前段に置くことも可能（任意・ドメイン代のみ）。

## 各サービスの無料枠（2026-08 時点）

| サービス | 用途 | 無料枠 |
|----------|------|--------|
| **Oracle Cloud** | VM (API/Worker/DB/全部) | Always Free: Ampere A1 合計 2 OCPU / 12GB (2026-06 に 4/24 から縮小)、ブートボリューム 200GB まで |
| **Cloudflare R2** | 動画・ファイル | 10GB ストレージ、egress 無料、読み取り1000万回/月 |
| **DuckDNS** | DNS | 無料（5サブドメインまで） |
| **Let's Encrypt** | TLS証明書 | 無料（90日ごと自動更新） |
| **GitHub Actions/GHCR** | CI/CD | Public リポジトリは無制限 |

---

## セットアップ手順

### 1. Oracle Cloud — アカウントと VM 作成

1. [oracle.com/cloud/free](https://www.oracle.com/cloud/free/) でアカウント作成
   - **ホームリージョンは後から変更不可**。`Japan East (Tokyo)` か `Japan Central (Osaka)` を選択
   - クレジットカード登録が必要（Always Free 内なら課金なし）
2. Compute → Instances → Create Instance:
   - Shape: **VM.Standard.A1.Flex — 2 OCPU / 12GB**（Always Free 上限いっぱいを1台に割当）
   - Image: **Ubuntu 24.04 (aarch64)**
   - SSH公開鍵を登録（デプロイ用に新規作成推奨: `ssh-keygen -t ed25519 -f oci_deploy`）
   - ⚠️ 「Out of capacity」エラーが出る場合: 時間を変えて再試行するか、
     アカウントを **Pay As You Go にアップグレード**すると通りやすくなる
     （Always Free リソースのみ使う限り $0 のまま。さらに、無料アカウントの
     アイドルVM自動停止ポリシーの対象からも外れるため **PAYG化を推奨**）
3. **パブリックIPを予約IPに変更**（無料・インスタンス再作成でもIP維持）:
   - Instance → Attached VNICs → IPv4 Addresses → Edit → Reserved Public IP

### 2. ネットワーク開放（2箇所必要 — ハマりポイント）

**(a) OCI 側** — VCN → Security List に Ingress ルール追加:

| Port | Source |
|---|---|
| 80 | 0.0.0.0/0 |
| 443 | 0.0.0.0/0 |

**(b) VM 内の iptables** — Oracle の Ubuntu イメージは**デフォルトで 22 以外を REJECT** します:

```bash
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
sudo netfilter-persistent save
```

### 3. Docker インストールとアプリ配置

```bash
# VM に SSH ログイン (ubuntu ユーザー)
ssh -i oci_deploy ubuntu@<VMのIP>

# Docker
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker ubuntu && exit   # 入り直して反映

# アプリ配置（/opt/app 固定 — デプロイworkflowが参照）
sudo mkdir -p /opt/app && sudo chown ubuntu:ubuntu /opt/app
git clone https://github.com/<your-org>/esports-platform.git /opt/app
cd /opt/app
mkdir -p certbot-www nginx/ssl
```

> プライベートリポジトリの場合、clone には Fine-grained PAT（Contents: Read）を使用:
> `git clone https://<PAT>@github.com/<your-org>/esports-platform.git /opt/app`

`backend/.env` を作成（EC2 の `/opt/app/backend/.env` からコピーして以下を確認）:

```bash
SECRET_KEY=<32文字以上>
DB_PASSWORD=<任意>
USE_REDIS_QUEUE=true
ALLOWED_ORIGINS=https://<your-sub>.duckdns.org
PUBLIC_WEB_URL=https://<your-sub>.duckdns.org
# Cloudflare R2 (手順5で取得)
S3_BUCKET_NAME=esports-uploads
S3_ENDPOINT_URL=https://<account-id>.r2.cloudflarestorage.com
AWS_ACCESS_KEY_ID=<r2-key-id>
AWS_SECRET_ACCESS_KEY=<r2-secret>
```

Discord Bot を使う場合はルートにも `.env`（compose が参照）:

```bash
PUBLIC_WEB_URL=https://<your-sub>.duckdns.org
DISCORD_BOT_TOKEN=...
BOT_API_TOKEN=...
```

### 4. DuckDNS（無料DNS）

[duckdns.org](https://www.duckdns.org) に GitHub アカウント等でログイン → サブドメイン作成 → VM の**予約IP**を登録。
予約IPなら IP は変わらないため、DuckDNS の定期更新 cron は不要です。

### 5. Cloudflare R2（動画・ファイルストレージ）

1. Cloudflare ダッシュボード → R2 → バケット作成:
   - `esports-uploads`（API用・非公開）
   - `esports-media`（Hero動画用・**Settings → Public access → r2.dev subdomain を有効化**）
2. R2 API トークン作成（Object Read & Write）→ `backend/.env` の `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` へ
3. Hero 動画を `esports-media` にアップロードし、`https://pub-xxxx.r2.dev/hero.mp4` 形式の公開URLを控える

> R2 は boto3 互換。`S3_ENDPOINT_URL` を設定するだけでバックエンドは無変更で動作します。
> Hero動画が小さい（〜20MB程度）なら R2 を使わず `frontend/public/hero/hero.mp4` に同梱する選択肢もあります
> （その場合 HERO_VIDEO_* 変数は未設定のままでOK — ローカルパスにフォールバックします）。

### 6. GitHub Secrets / Variables の更新と初回デプロイ（HTTP）

Settings → Secrets and variables → Actions:

| 種別 | 名前 | 値 |
|---|---|---|
| Secret | `DEMO_SSH_HOST` | VM の予約IP |
| Secret | `DEMO_SSH_KEY` | `oci_deploy` 秘密鍵の中身 |
| Variable | `DEMO_SSH_USER` | `ubuntu` |
| Variable | `DEMO_DOMAIN` | `<your-sub>.duckdns.org` |
| Variable | `HERO_VIDEO_MP4` ほか | R2 の公開URL（`https://pub-xxxx.r2.dev/...`）。ローカル同梱なら削除 |

> ⚠️ `DEMO_COMPOSE_FILES` は**まだ設定しない**こと（証明書発行前に TLS 構成で起動すると nginx が起動失敗する）。
> 旧 `DEMO_EC2_HOST` / `DEMO_EC2_SSH_KEY` は AWS 解体後に削除してかまいません
> （`DEMO_SSH_*` が優先されるフォールバック実装のため、残っていても無害）。

設定できたら Actions タブ → **Build & Push** → Run workflow で手動実行。
完了すると **Deploy — Demo (SSH VM)** が連動し、新VMに HTTP 構成でスタック一式が起動します
（GHCR のプライベートイメージ認証は workflow が自動で行うため、初回起動は必ずこの経路で行う）。

`http://<your-sub>.duckdns.org/health` が 200 を返せば成功です。

### 7. Let's Encrypt 証明書発行と TLS 切替

HTTP 構成が動いている状態で、VM 上で webroot 方式により発行します:

```bash
ssh -i oci_deploy ubuntu@<VMのIP>
sudo apt install -y certbot
sudo certbot certonly --webroot -w /opt/app/certbot-www -d <your-sub>.duckdns.org

# TLS 設定のドメイン置換
cd /opt/app
sed -i 's/YOUR_DOMAIN/<your-sub>.duckdns.org/g' nginx/nginx-tls.conf

# TLS 構成で再起動（イメージは初回デプロイで取得済み）
IMAGE_ORG=<github-org小文字> docker compose \
  -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.tls.yml up -d
```

自動更新（90日ごと）時に nginx をリロードさせるフック:

```bash
sudo tee /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh <<'EOF'
#!/bin/sh
cd /opt/app && docker compose exec -T nginx nginx -s reload
EOF
sudo chmod +x /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh
```

最後に GitHub Variables に **`DEMO_COMPOSE_FILES` = `docker-compose.yml:docker-compose.prod.yml:docker-compose.tls.yml`** を追加。
以降の自動デプロイも TLS 構成を維持するようになります。

### 8. データ移行（EC2 → Oracle VM）

```bash
# 手元PC等から: EC2 でダンプ → 新VMへリストア
ssh ec2-user@<EC2-IP> "docker compose -f /opt/app/docker-compose.yml exec -T postgres \
  pg_dump -U esports_user -d esports_db --clean --if-exists" > dump.sql

scp -i oci_deploy dump.sql ubuntu@<新VM-IP>:/tmp/
ssh -i oci_deploy ubuntu@<新VM-IP> \
  "cd /opt/app && docker compose exec -T postgres psql -U esports_user -d esports_db < /tmp/dump.sql && rm /tmp/dump.sql"

# リストア後、スキーマを最新マイグレーションに揃える
ssh -i oci_deploy ubuntu@<新VM-IP> \
  "cd /opt/app && docker compose exec -T api alembic upgrade head"
```

S3 のアップロード済みファイルは `aws s3 sync s3://<bucket> ./s3-data` でローカルへ取得後、
rclone 等で R2 の `esports-uploads` へ転送します。

### 9. 動作確認チェックリスト

- [ ] `https://<your-sub>.duckdns.org/health` → 200
- [ ] `https://<your-sub>.duckdns.org` → フロントエンド表示・Hero動画再生
- [ ] ログイン → API 通信（`/api/`）が HTTPS で成功
- [ ] `main` に空コミットを push → Build & Push (arm64) → Deploy — Demo (SSH VM) が成功
- [ ] worker ログでキュー消化を確認: `docker compose logs -f worker`
- [ ] Discord Bot（使用時）: `docker compose --profile discord up -d`

---

## CI/CD フロー（変更点のみ）

```
git push main
  ├─► Build & Push: linux/amd64 + linux/arm64 のマルチアーチイメージを GHCR へ
  └─► Deploy — Demo (SSH VM): DEMO_SSH_HOST へ SSH → compose pull → up -d → alembic upgrade
```

従来の EC2 デプロイと同じ仕組みのまま、接続先だけが Oracle VM に変わります。
Private リポジトリで Actions の無料枠（2,000分/月）が厳しい場合は、EC2 廃止後に
`build.yml` の `platforms` を `linux/arm64` のみに絞るとビルド時間がほぼ半減します。

---

## AWS 解体手順（課金停止）

移行完了・動作確認後に実施。**順序どおりに**:

1. **CloudFront**: ディストリビューションを Disable → 反映後 Delete
2. **S3**: バケットを空にしてから Delete（動画は R2 へ移行済みであること）
3. **EC2**: インスタンス Terminate → 残った **EBS ボリューム / スナップショット** を削除
4. **Elastic IP**: 保持していれば Release（未使用EIPは課金対象）
5. Terraform 管理分は `cd infrastructure/terraform/environments/demo && terraform destroy` でも可
6. 数日後に **Billing ダッシュボードで請求が $0 になっていることを確認**
7. GitHub の旧 Secrets（`DEMO_EC2_*`）と `HERO_VIDEO_*` の CloudFront URL を削除・更新

---

## 代替案（参考）

### マネージド分割構成（Neon + Upstash + R2）

バックエンドには切替スイッチが実装済みのため、VM を使わず DB/Redis をマネージドに分割することも可能です:
`DB_SSL_REQUIRED=true`（Neon）、`REDIS_TLS=true`（Upstash）、`S3_ENDPOINT_URL`（R2）、`USE_REDIS_QUEUE=true`。
ただし **API/Worker を常時無料で動かせるコンテナ実行環境が現存しない**（Fly.io/Koyeb 無料枠廃止、
Render は Worker が $7/月〜）ため、2026年時点では Oracle VM 構成を推奨します。
`infrastructure/fly/` の設定は旧構成の名残であり、現在は使用していません。

### アクセス増加時の AWS 復帰

Terraform 一式（`infrastructure/terraform/environments/demo|mvp`）は維持しているため、いつでも戻せます:

| 変数 | 無料構成 | AWS |
|------|--------|-------|
| `USE_REDIS_QUEUE` | `true` | `false` + `SQS_*_QUEUE_URL` 設定 |
| `S3_ENDPOINT_URL` | R2 エンドポイント | （削除） |
| `DB_SSL_REQUIRED` | `false`（VM内DB） | `false`（VPC内RDS）/ Neon併用なら `true` |
| デプロイ先 | `DEMO_SSH_HOST`（Oracle） | `deploy-mvp.yml` / `deploy-production.yml` |

---

## トラブルシューティング

### A1 インスタンスが「Out of capacity」で作れない
時間帯を変えて再試行（早朝が通りやすい）。それでもダメなら PAYG へアップグレード（無料のまま優先度が上がる）。
OCPU を 1 に減らすと通ることもある（後から 2 に拡張可能）。

### ポート 80/443 に外から繋がらない
OCI Security List と VM 内 iptables の**両方**を確認（手順2）。`sudo iptables -L INPUT -n --line-numbers` で
REJECT ルールより上に ACCEPT が入っているか確認。

### 無料アカウントで VM が勝手に停止された
Always Free（未アップグレード）アカウントは、CPU/ネットワーク使用率が低いインスタンスを
Oracle が自動停止することがあります。PAYG へのアップグレードで対象外になります（課金リソースを作らない限り $0）。

### 証明書更新後も古い証明書が使われる
`/etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh` が実行可能か確認。
手動リロード: `cd /opt/app && docker compose exec nginx nginx -s reload`

### ARM イメージ関連のエラー（`exec format error`）
GHCR のイメージが arm64 を含んでいるか確認: `docker manifest inspect ghcr.io/<org>/esports-platform-api:latest`。
`build.yml` の `platforms: linux/amd64,linux/arm64` が効いた後のビルドを pull していること。

---

## 運用（デプロイ後に必ず設定する）

デプロイしただけでは、バックアップも障害検知も動きません。VM 上で以下を1度だけ実行します。

### 1. 運用ジョブの登録

```bash
cd /opt/app
sudo ./scripts/install-ops-cron.sh
```

登録されるもの:

| ジョブ | 頻度 | 内容 |
|---|---|---|
| `backup-db.sh` | 毎日 03:15 UTC | pg_dump → gzip。14世代保持。R2設定があれば同時アップロード |
| `healthcheck.sh` | 15分ごと | ディスク・コンテナ・API応答・証明書残日数・バックアップ鮮度を点検 |
| `docker system prune` | 毎週日曜 04:00 UTC | 未使用イメージとビルドキャッシュを削除 |

### 2. バックアップの保存先（推奨）

VM 内だけに置くと、VM ごと失ったときに復旧できません。`backend/.env` に R2 を設定します。

```bash
BACKUP_S3_BUCKET=axelia-backups
S3_ENDPOINT_URL=https://<account_id>.r2.cloudflarestorage.com
BACKUP_KEEP_DAYS=14
```

`aws` CLI が必要です（`sudo apt install -y awscli`）。認証情報は `aws configure` で R2 のアクセスキーを設定します。

### 3. 障害通知

`backend/.env` の `HEALTHCHECK_WEBHOOK_URL` に Discord Webhook を設定すると、
異常検知時にメッセージが飛びます。未設定でもログには残ります。

```bash
HEALTHCHECK_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

### 4. リソース設定を実機に合わせる

`docker-compose.yml` のメモリ上限は t2.micro (1GB) 時代のままです。
Oracle の A1 (12GB) では `docker-compose.oracle.yml` を重ねてください。
ログローテーション（1コンテナ最大30MB）もこのファイルで有効になります。

```bash
docker compose -f docker-compose.yml \
               -f docker-compose.prod.yml \
               -f docker-compose.tls.yml \
               -f docker-compose.oracle.yml up -d
```

### 5. 証明書の自動更新を確認

```bash
systemctl list-timers | grep certbot   # タイマーが有効か
sudo certbot renew --dry-run           # 更新が通るか
```

更新後に nginx を reload するフックは手順7で設定済みです。

---

## 復旧手順

### DB を戻す

```bash
cd /opt/app
./scripts/restore-db.sh --latest          # 最新のバックアップから
./scripts/restore-db.sh backups/xxx.sql.gz  # 世代を指定
```

実行前に確認を求められます。api / worker / scheduler は自動で停止・再開されます。

### R2 から取り寄せる

```bash
aws s3 ls s3://axelia-backups/db/ --endpoint-url "$S3_ENDPOINT_URL"
aws s3 cp s3://axelia-backups/db/esports_db-YYYYMMDD-HHMMSS.sql.gz backups/ \
  --endpoint-url "$S3_ENDPOINT_URL"
./scripts/restore-db.sh backups/esports_db-YYYYMMDD-HHMMSS.sql.gz
```

### バックアップが復元できることの確認（定期的に実施）

バックアップは「復元できて初めてバックアップ」です。本番を壊さずに検証できます。

```bash
docker compose exec -T postgres psql -U esports_user -d postgres \
  -c "CREATE DATABASE restore_test;"
gzip -dc backups/$(ls -1t backups | head -1) \
  | docker compose exec -T postgres psql -U esports_user -d restore_test -v ON_ERROR_STOP=1
docker compose exec -T postgres psql -U esports_user -d restore_test \
  -c "SELECT count(*) FROM tournaments;"
docker compose exec -T postgres psql -U esports_user -d postgres \
  -c "DROP DATABASE restore_test;"
```

---

## 無料枠で実際に起きること

| 症状 | 原因 | 対処 |
|---|---|---|
| ある日ディスクが 100% になる | Docker のログとイメージの蓄積 | `docker-compose.oracle.yml` のログ上限 + 週次 prune で回避。`healthcheck.sh` が80%で警告 |
| コンテナが落ちたまま気付かない | 監視なし | `healthcheck.sh` が15分ごとに検知して通知 |
| 証明書が切れてサイトが開けない | certbot タイマー停止 | `healthcheck.sh` が残14日で警告 |
| VM が勝手に停止された | Always Free のアイドル回収 | 手順9のトラブルシューティング参照。有料テナンシへの昇格（課金は発生しない）で回避可能 |
