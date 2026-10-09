# Phase 10 — 運用インフラ（ConoHa VPS 版）

VPS 1台に docker compose を全部載せて運用するためのガイドです。

> **2026-10 改訂**: Oracle Cloud Always Free 版から ConoHa VPS 版へ全面改訂しました。
> Oracle はアカウント作成にクレジットカードが必須で登録できなかったため、
> **コンビニ払い・銀行振込に対応した国内VPS**へ方針を変更しています。
> あわせて、画像の保存先を Cloudflare R2（カード必須）から
> **Supabase Storage**（カード不要）へ差し替えました。
>
> 旧版（Oracle / DuckDNS / R2 前提）の記述は本書では使いません。

---

## アーキテクチャ概要

アプリケーションコードの変更は不要で、置き換わるのはインフラ層だけです。

```
ユーザー
  │ HTTPS
  ▼
app.axelia-esports.jp（ムームーDNS の A レコード）
  │
  ▼
ConoHa VPS — 4GB / 4コア / SSD 100GB（東京リージョン）
  └─ docker compose
       ├─ nginx      ← Let's Encrypt で TLS 終端
       ├─ frontend   ← Next.js
       ├─ api        ← FastAPI（スコアボードOCRを含む）
       ├─ worker     ← バックグラウンドジョブ（Redis キュー）
       ├─ postgres   ← DB（VM内）
       ├─ redis      ← キャッシュ + キュー
       └─ discord-bot（profile: discord / 任意）

Supabase Storage（S3互換）
  └─ チームロゴ・バナー・添付ファイル

GitHub Actions + GHCR
  └─ push → ビルド → SSH デプロイ
```

| 移行元（デモ構成） | 移行先（ConoHa） |
|---|---|
| Netlify（フロント） | VPS 内 frontend + nginx |
| Render（API / ワーカー） | VPS 内 api / worker |
| Neon（PostgreSQL） | VPS 内 postgres |
| Upstash（Redis） | VPS 内 redis |
| コンテナ内の一時ディスク | Supabase Storage |
| `*.netlify.app` | `app.axelia-esports.jp` |

**移行後、Netlify / Render / Neon / Upstash はすべて不要になります。**

### なぜ VPS 1台に集約するのか

- Render 無料プランはアクセスが無いとスリープし、**初回アクセスに約60秒**かかる（実測52〜62秒）
- Render のディスクは揮発性で、**アップロード画像が再デプロイのたびに消える**
- 分散構成は無料枠の制限（Upstash のコマンド数、Neon の容量）を個別に気にする必要がある

VPS 1台なら、これらがまとめて解消します。

### なぜ 4GB なのか

compose のメモリ上限の合計は約1.4GBですが、これは t2.micro（1GB）時代の値です。
実運用では次の理由で足りません。

- **スコアボードOCRが一時的にメモリを食う** — `cv2` はインポートだけで100〜200MB、
  画像処理の配列コピーと Tesseract の日本語モデルが加わり、実行中の api は500〜800MBに達する
- レート制限は OCR を60秒あたり6回まで許すため、同時実行で倍増する
- 旧 `docker-compose.oracle.yml` に「frontend が 300M で頻繁に OOM 気味になる」
  というコメントが残っており、実機では既定値が不足していた記録がある

2GB では OCR 実行時にメモリを使い切るため、**4GB を選択**しています。

---

## セットアップ手順

### 1. ConoHa VPS — 契約とサーバー作成

1. [ConoHa VPS](https://www.conoha.jp/vps/) で以下を選択してサーバーを追加:
   - **メモリ 4GB**
   - **イメージ: アプリケーション → Docker**（OS は Ubuntu 系になる）
   - **リージョン: 東京**
   - **SSH Key: 新規追加**（下記で作った公開鍵を貼る）
2. 支払いは **ConoHaチャージ**（コンビニ払い・銀行決済・Amazon Pay）でカード無しでも可能
3. 作成後、管理画面でサーバーの **IPアドレス**を控える

デプロイ用の鍵はローカルで作ります（秘密鍵を外に出さないため）:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/conoha_axelia -N "" -C "axelia-deploy"
cat ~/.ssh/conoha_axelia.pub   # この内容を ConoHa の SSH Key に登録
```

### 2. ポート開放（2箇所）

**(a) ConoHa のセキュリティグループ** — 管理画面 → サーバー → ネットワーク情報 →
セキュリティグループで、**22 / 80 / 443** の受信を許可します。
既定の `IPv4v6-SSH` だけだと 80/443 が閉じたままです。

**(b) OS 側のファイアウォール**:

```bash
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable
sudo ufw status
```

> Oracle の Ubuntu イメージと違い、ConoHa は iptables で 80/443 を REJECT しません。
> ufw を有効にする場合は**必ず先に 22 を許可**すること（順序を誤ると SSH が切れます）。

### 3. サーバー初期設定とアプリ配置

```bash
ssh -i ~/.ssh/conoha_axelia root@<VPSのIP>

# 作業ユーザー（Docker テンプレートは root ログインのことが多い）
adduser --disabled-password --gecos "" deploy
usermod -aG docker,sudo deploy
mkdir -p /home/deploy/.ssh && cp ~/.ssh/authorized_keys /home/deploy/.ssh/
chown -R deploy:deploy /home/deploy/.ssh && chmod 700 /home/deploy/.ssh

# パスワード認証を無効化
sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
systemctl restart ssh
```

Docker の確認（テンプレート利用なら導入済み）:

```bash
docker --version
docker compose version   # v2 であること（v1 だと compose 定義が通らない）
```

入っていない場合:

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker deploy && exit   # 入り直して反映
```

アプリの配置（`/opt/app` 固定 — デプロイ workflow が参照します）:

```bash
sudo mkdir -p /opt/app && sudo chown deploy:deploy /opt/app
git clone https://github.com/<your-org>/esports-platform.git /opt/app
cd /opt/app
mkdir -p certbot-www nginx/ssl
```

> プライベートリポジトリの場合は Fine-grained PAT（Contents: Read）を使用:
> `git clone https://<PAT>@github.com/<your-org>/esports-platform.git /opt/app`

`backend/.env` を作成します:

```env
SECRET_KEY=<32文字以上>
DB_PASSWORD=<任意>
USE_REDIS_QUEUE=true
ALLOWED_ORIGINS=https://app.axelia-esports.jp
FRONTEND_BASE_URL=https://app.axelia-esports.jp
PUBLIC_WEB_URL=https://app.axelia-esports.jp

# メール（Resend）
SMTP_HOST=smtp.resend.com
SMTP_PORT=587
SMTP_USER=resend
SMTP_PASSWORD=<re_ で始まる APIキー>
MAIL_FROM=noreply@axelia-esports.jp
MAIL_FROM_NAME=AXELIA

# 画像保存先（手順5で取得）
S3_BUCKET_NAME=axelia-uploads
S3_ENDPOINT_URL=https://<project-ref>.supabase.co/storage/v1/s3
AWS_ACCESS_KEY_ID=<supabase-access-key>
AWS_SECRET_ACCESS_KEY=<supabase-secret-key>
AWS_REGION=ap-northeast-1
```

Discord Bot を使う場合はルートにも `.env`（compose が参照）:

```env
PUBLIC_WEB_URL=https://app.axelia-esports.jp
DISCORD_BOT_TOKEN=...
BOT_API_TOKEN=...
```

### 4. DNS（ムームードメイン）

ムームードメインのコントロールパネル → ムームーDNS → `axelia-esports.jp` の設定変更で、
**A レコードを1本追加**します。

| サブドメイン | 種別 | 内容 |
|---|---|---|
| `app` | A | `<VPSのIP>` |

**ネームサーバーの変更は不要**です。既存の分析ツール用レコードには一切触れません。

反映確認:

```bash
nslookup app.axelia-esports.jp
```

### 5. Supabase Storage（画像の保存先）

コンテナ内のディスクは揮発性で、チームロゴが再デプロイのたびに消えます。
S3 互換の外部ストレージへ逃がします。**Supabase はカード不要**で、無料枠は1GBです。

1. [supabase.com](https://supabase.com) でプロジェクト作成（リージョンは Tokyo）
2. Storage → New bucket → `axelia-uploads`（Private）
3. Project Settings → Storage → **S3 Connection** でエンドポイントURLを控える
4. S3 access keys を発行し、`backend/.env` の `AWS_ACCESS_KEY_ID` /
   `AWS_SECRET_ACCESS_KEY` へ設定

> `backend/app/core/storage.py` は `S3_ENDPOINT_URL` が設定されていれば
> S3 互換ストレージへ接続します。**コード変更は不要**です。
> 未設定だとコンテナ内 `/app/uploads` へのフォールバックになり、消える問題が再発します。

### 6. GitHub Secrets / Variables の更新と初回デプロイ（HTTP）

Settings → Secrets and variables → Actions:

| 種別 | 名前 | 値 |
|---|---|---|
| Secret | `DEMO_SSH_HOST` | VPS の IP |
| Secret | `DEMO_SSH_KEY` | `~/.ssh/conoha_axelia` の中身（秘密鍵） |
| Variable | `DEMO_SSH_USER` | `deploy` |
| Variable | `DEMO_DOMAIN` | `app.axelia-esports.jp` |

> ⚠️ `DEMO_COMPOSE_FILES` は**まだ設定しない**こと。
> 証明書発行前に TLS 構成で起動すると nginx が起動に失敗します。

Actions タブ → **Build & Push** を手動実行。完了すると **Deploy — Demo (SSH VM)** が
連動し、HTTP 構成でスタック一式が起動します。

`http://app.axelia-esports.jp/health` が 200 を返せば成功です。

### 7. Let's Encrypt 証明書発行と TLS 切替

HTTP 構成が動いている状態で、VPS 上で webroot 方式により発行します:

```bash
ssh -i ~/.ssh/conoha_axelia deploy@<VPSのIP>
sudo apt install -y certbot
sudo certbot certonly --webroot -w /opt/app/certbot-www -d app.axelia-esports.jp

# TLS 設定のドメイン置換
cd /opt/app
sed -i 's/YOUR_DOMAIN/app.axelia-esports.jp/g' nginx/nginx-tls.conf

# TLS 構成で再起動
IMAGE_ORG=<github-org小文字> docker compose \
  -f docker-compose.yml -f docker-compose.prod.yml \
  -f docker-compose.tls.yml -f docker-compose.conoha.yml up -d
```

自動更新（90日ごと）時に nginx をリロードさせるフック:

```bash
sudo tee /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh <<'EOF'
#!/bin/sh
cd /opt/app && docker compose exec -T nginx nginx -s reload
EOF
sudo chmod +x /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh
```

最後に GitHub Variables に
**`DEMO_COMPOSE_FILES` = `docker-compose.yml:docker-compose.prod.yml:docker-compose.tls.yml:docker-compose.conoha.yml`**
を追加します。以降の自動デプロイも TLS 構成とメモリ上限を維持します。

### 8. データ移行（Neon → VPS）

現行デモの PostgreSQL は Neon にあります。ダンプして VPS 内の postgres へ流し込みます。

```bash
# ローカルから: Neon をダンプ（接続文字列は Neon ダッシュボードで確認）
docker run --rm postgres:18-alpine pg_dump "<NEONの接続文字列>" \
  --clean --if-exists --no-owner | gzip -9 > neon_dump.sql.gz

# VPS へ転送してリストア
scp -i ~/.ssh/conoha_axelia neon_dump.sql.gz deploy@<VPSのIP>:/tmp/
ssh -i ~/.ssh/conoha_axelia deploy@<VPSのIP> \
  "cd /opt/app && gzip -dc /tmp/neon_dump.sql.gz | \
   docker compose exec -T postgres psql -U esports_user -d esports_db && rm /tmp/neon_dump.sql.gz"

# スキーマを最新マイグレーションに揃える
ssh -i ~/.ssh/conoha_axelia deploy@<VPSのIP> \
  "cd /opt/app && docker compose exec -T api alembic upgrade head"
```

Redis（Upstash）は**キャッシュとキューのみ**なので移行不要です。空から始まります。

アップロード済みの画像は、Render の揮発ディスク上にあったものは既に失われている
可能性があります。Supabase へ入れ直してください。

### 9. 動作確認チェックリスト

- [ ] `https://app.axelia-esports.jp/health` → 200
- [ ] `https://app.axelia-esports.jp` → フロントエンド表示
- [ ] 新規登録 → ログイン → API 通信が HTTPS で成功
- [ ] 大会ページでエントリー欄が表示される
- [ ] チームロゴをアップロード → **再デプロイ後も表示される**（Supabase 経由の確認）
- [ ] スコアボードOCRを実行 → `docker stats` で api のメモリが上限内に収まる
- [ ] `main` に空コミットを push → Build & Push → Deploy — Demo が成功
- [ ] worker ログでキュー消化を確認: `docker compose logs -f worker`

### 10. 主催者の流れを通しで検証する（任意）

大会作成から結果反映までが実際に動くかを、1コマンドで確認できます。

```bash
docker compose exec -T api python scripts/e2e_organizer_flow.py
```

既存の主催者とチームを使い、大会作成 → 公開 → 参加申請 → 抽選 →
Discord招待の通知 → チェックイン → ブラケット生成 → 試合結果登録 →
戦績への反映までを順に検証します。**作成した大会は最後に必ず削除する**
ので、本番のデータには残りません。

全29項目が `[OK]` になれば、主催者が使う一連の機能は動いています。
デプロイ後や大きな変更のあとに流しておくと、壊れた箇所を早く見つけられます。

---

## CI/CD フロー

```
git push main
  ├─► Build & Push: GHCR へイメージを push
  └─► Deploy — Demo (SSH VM): DEMO_SSH_HOST へ SSH → compose pull → up -d → alembic upgrade
```

接続先が変わるだけで、仕組みは従来どおりです。
ConoHa は x86 なので、`build.yml` の `platforms` を `linux/amd64` のみに絞ると
ビルド時間がほぼ半減します（ARM 向けビルドは不要になりました）。

---

## 旧デモ環境の停止手順

移行完了・動作確認後に実施します。**順序どおりに**:

1. **DNS を切り替え済みであることを確認**（`app.axelia-esports.jp` が VPS を向いている）
2. **Netlify**: サイトを停止、または Deploys を一時停止
3. **Render**: `axelia-api` サービスを Suspend → 問題なければ Delete
4. **Neon**: ダンプを取得済みであることを確認してからプロジェクトを削除
5. **Upstash**: データベースを削除（キャッシュのみなので退避不要）
6. GitHub の不要な Secrets（Render/Netlify 向け）を削除

> Netlify と Render は無料プランなので、**しばらく残しておいても費用は発生しません**。
> VPS が安定するまで1〜2週間は残し、切り戻し先として確保しておくことを推奨します。

---

## トラブルシューティング

### ポート 80/443 に外から繋がらない
ConoHa のセキュリティグループと OS の ufw の**両方**を確認（手順2）。
`sudo ufw status` で 80/443 が ALLOW になっているか、
ConoHa 管理画面でセキュリティグループが適用されているかを見ます。

### `docker compose` が「command not found」
Docker Compose v1（`docker-compose`）しか入っていません。v2 を入れ直します:

```bash
sudo apt install -y docker-compose-plugin
docker compose version
```

### OCR 実行時に api が落ちる（OOM）
`docker-compose.conoha.yml` が適用されているか確認します:

```bash
docker inspect $(docker compose ps -q api) --format '{{.HostConfig.Memory}}'
# 1073741824（1GB）になっていること
```

適用されていれば `docker stats` で実行中のメモリを観察してください。
それでも足りない場合は ConoHa のプランを 8GB へスケールアップします。

### 証明書更新後も古い証明書が使われる
`/etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh` が実行可能か確認。
手動リロード: `cd /opt/app && docker compose exec nginx nginx -s reload`

### ディスクが逼迫する
`docker-compose.conoha.yml` でログを1コンテナ最大30MBに制限していますが、
イメージの蓄積は別です。週次の prune が登録されているか確認してください（運用セクション）。

---

## 運用（デプロイ後に必ず設定する）

デプロイしただけでは、バックアップも障害検知も動きません。VPS 上で以下を1度だけ実行します。

### 1. 運用ジョブの登録

```bash
cd /opt/app
sudo ./scripts/install-ops-cron.sh
```

登録されるもの:

| ジョブ | 頻度 | 内容 |
|---|---|---|
| `backup-db.sh` | 毎日 03:15 UTC | pg_dump → gzip。14世代保持。S3設定があれば同時アップロード |
| `healthcheck.sh` | 15分ごと | ディスク・コンテナ・API応答・証明書残日数・バックアップ鮮度を点検 |
| `docker system prune` | 毎週日曜 04:00 UTC | 未使用イメージとビルドキャッシュを削除 |

### 2. バックアップの保存先（必須）

VPS 内だけに置くと、VPS ごと失ったときに復旧できません。`backend/.env` に設定します。

```env
BACKUP_S3_BUCKET=axelia-backups
S3_ENDPOINT_URL=https://<project-ref>.supabase.co/storage/v1/s3
BACKUP_KEEP_DAYS=14
```

Supabase 側に `axelia-backups` バケットを作っておきます。
`aws` CLI が必要です（`sudo apt install -y awscli`）。

### 3. 障害通知

`backend/.env` の `HEALTHCHECK_WEBHOOK_URL` に Discord Webhook を設定すると、
異常検知時にメッセージが飛びます。未設定でもログには残ります。

```env
HEALTHCHECK_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

### 4. リソース設定を実機に合わせる

`docker-compose.yml` のメモリ上限は t2.micro（1GB）時代のままです。
ConoHa 4GB では **`docker-compose.conoha.yml` を重ねてください**。
ログローテーション（1コンテナ最大30MB）もこのファイルで有効になります。

```bash
docker compose -f docker-compose.yml \
               -f docker-compose.prod.yml \
               -f docker-compose.tls.yml \
               -f docker-compose.conoha.yml up -d
```

上限の合計は約2.9GBで、OS と Docker の取り分（500MB前後）を引いても
4GB に収まる配分です。api に 1GB を割り当てているのは OCR のためです。

### 5. 証明書の自動更新を確認

```bash
systemctl list-timers | grep certbot   # タイマーが有効か
sudo certbot renew --dry-run           # 更新が通るか
```

---

## 復旧手順

### DB を戻す

```bash
cd /opt/app
./scripts/restore-db.sh --latest            # 最新のバックアップから
./scripts/restore-db.sh backups/xxx.sql.gz  # 世代を指定
```

実行前に確認を求められます。api / worker / scheduler は自動で停止・再開されます。

### ストレージから取り寄せる

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

## 運用中に実際に起きること

| 症状 | 原因 | 対処 |
|---|---|---|
| ある日ディスクが 100% になる | Docker のログとイメージの蓄積 | `docker-compose.conoha.yml` のログ上限 + 週次 prune で回避。`healthcheck.sh` が80%で警告 |
| OCR 実行時に api が再起動する | メモリ上限が既定（300M）のまま | `docker-compose.conoha.yml` を重ねているか確認 |
| コンテナが落ちたまま気付かない | 監視なし | `healthcheck.sh` が15分ごとに検知して通知 |
| 証明書が切れてサイトが開けない | certbot タイマー停止 | `healthcheck.sh` が残14日で警告 |
| アップロード画像が消える | `S3_BUCKET_NAME` 未設定でコンテナ内保存 | 手順5で Supabase を設定 |

---

## メール送信の設定（パスワードリセットに必須）

SMTP未設定でもアプリは動きますが、パスワードリセットのメールが届かず
本文がAPIログに出るだけになります。公開前に必ず設定してください。

### 方式A: Resend（独自ドメイン・推奨）

無料枠: 100通/日・3,000通/月。`axelia-esports.jp` は検証済みです。

1. [resend.com](https://resend.com) で **APIキーを発行**
2. Domains でドメインを追加し、表示される DNSレコード（SPF/DKIM）を
   ムームーDNS に登録（**ネームサーバーの変更は不要**）
3. `backend/.env` に設定:

```env
SMTP_HOST=smtp.resend.com
SMTP_PORT=587
SMTP_USER=resend
SMTP_PASSWORD=re_で始まるAPIキー
MAIL_FROM=noreply@axelia-esports.jp
MAIL_FROM_NAME=AXELIA
FRONTEND_BASE_URL=https://app.axelia-esports.jp
```

### 方式B: Gmail（個人運用向け）

無料枠: 500通/日。独自ドメインからは送れません。

1. Googleアカウントで **2段階認証を有効化**
2. [アプリパスワードを発行](https://myaccount.google.com/apppasswords)
3. `SMTP_HOST=smtp.gmail.com` / `SMTP_USER=<自分のGmail>` /
   `SMTP_PASSWORD=<16文字のアプリパスワード>` を設定

> 注意: Googleの通常パスワードでは送信できません。必ずアプリパスワードを使うこと。

### 反映と疎通確認

```bash
docker compose restart api worker
docker compose exec api python scripts/send_test_email.py 自分のアドレス
```

### FRONTEND_BASE_URL について

リセットメール内のリンク（`{FRONTEND_BASE_URL}/reset-password?token=...`）の
基点です。ここが違うと、届いたメールのリンクが開けません。

---

## Discord連携の運用方針

**botの導入は任意です。** 基本の運用は以下だけで完結します:

1. 主催者が大会設定に自分のDiscordサーバーの**招待リンクを貼る**
2. 参加申請が承認（抽選当選）されると、チーム全員のAXELIAアカウントへ
   **招待リンク入りの通知が自動で届く**（アプリ内通知）
3. 参加者はそのリンクから大会サーバーに入る

botを導入すると追加でチャンネル/ロールの自動生成やDiscord上での
チェックインが使えますが、無くても大会運営に支障はありません。

---

## 一括デプロイスクリプト

上記の手順3〜8を1コマンドに集約してあります。

```bash
scripts/deploy-to-vm.sh deploy@<VPSのIP> ~/.ssh/conoha_axelia
```

前提（先に済ませておく）:
1. 手順1〜2（VPS作成・ポート開放）
2. 手順4（ムームーDNS の A レコード）

スクリプトが自動で行うこと: 本番用 .env 生成（URL差し替え・docs非公開）→
コード+最新DBバックアップの転送 → Docker導入 → OS内FW開放 →
Let's Encrypt証明書取得 → TLS構成で起動 → migration → DBリストア →
運用cron登録。2回目以降の実行は更新デプロイとして機能します。

---

## 公開範囲について

現在は**限定公開**です。検索エンジンからの除外を3箇所で多重化しています。

- `frontend/src/app/robots.ts`
- `frontend/src/app/layout.tsx`（`robots: { index: false, follow: false }`）
- `frontend/next.config.ts` の `X-Robots-Tag` ヘッダ

一般公開へ切り替える際は、**この3箇所をまとめて解除**してください。
`netlify.toml` にも同じ指定がありますが、ConoHa 移行後は使われなくなります。

一般公開の前に残っている課題（モデレーション機能、運営者情報の明記、
サンプルデータの整理）は `docs/manual/AXELIA_運用手順書.pdf` もあわせて確認してください。
