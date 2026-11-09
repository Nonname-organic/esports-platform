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
SECRET_KEY=<32文字以上のランダム値（openssl rand -hex 32）>
DB_PASSWORD=<ランダム値（openssl rand -hex 24）。ルートの .env と同じ値>
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

ルートの `/opt/app/.env`（compose が参照）にも同じ `DB_PASSWORD` を入れる。postgres の初期化に使われ、
本番の compose（`docker-compose.prod.yml`）は未設定だとその場で止まる（既定値 `esports_pass` は使わない）。
`SECRET_KEY` が見本の値、`DB_PASSWORD` が空・既定値のときは、デプロイ前の設定検査で止まる
（[RC1_PRODUCTION_CHECKLIST.md](release/RC1_PRODUCTION_CHECKLIST.md)）。

```env
DB_PASSWORD=<backend/.env と同じ値>
```

Discord Bot を使う場合は、ルートの `.env` に次も加える:

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
IMAGE_ORG=<github-org小文字> IMAGE_TAG=<sha-xxxxxxx> docker compose \
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

## RC1 本番公開の手順（2026-11）

> **RC2 で置き換えた。** 公開は [RC2_DEPLOYMENT_RUNBOOK.md](release/RC2_DEPLOYMENT_RUNBOOK.md)、
> 切り戻しは [RC2_ROLLBACK_RUNBOOK.md](release/RC2_ROLLBACK_RUNBOOK.md) に従う。この節は RC1 時点の記録として残す。
> Deploy workflow は 2026-10-12 から無効で、main へのマージだけでは本番に出ない。下の「11. ロールバック」は使わない。

RC1（[リリースノート](release/RC1_RELEASE_NOTES.md)）を公開するときの手順。デプロイは従来どおり
main へのマージで自動に走り（Build & Push → Deploy）、**Deploy の最後にマイグレーション 028〜030 が自動で適用される**。
つまりマージした時点で本番 DB が変わる。各コマンドには、ローカルの使い捨て環境で確かめたかを書いた。
**本番ではどれも未実行。**

### 1. デプロイ前確認

- PR の CI（qa.yml）が通っている
- [チェックリスト](release/RC1_PRODUCTION_CHECKLIST.md)の「公開前の確認コマンド」がすべて OK
  （DB パスワードが既定値なら、同じ文書の手順で変えてからにする）
- 作業の時間帯を決める。デプロイ中は api / worker / scheduler / frontend が作り直され、数十秒落ちる

### 2. バックアップ（マージの直前）

```bash
cd /opt/app
./scripts/backup-db.sh                                  # cron と同じスクリプトで1世代取る
F=backups/$(ls -1t backups | head -1)
gzip -t "$F" && gzip -dc "$F" | tail -8 | grep -q "PostgreSQL database dump complete" \
  && echo "バックアップ OK: $F"
sha256sum "$F"
```

取得・整合性の確認・別 DB への復元は、postgres 15 の使い捨て DB で確認済み
（下の「バックアップが復元できることの確認」の手順）。

### 3. 現在のバージョンを控える

```bash
docker compose images api worker scheduler frontend     # 稼働中のタグ（sha-xxxxxxx）
docker compose exec -T api alembic current               # 027 (head) のはず
gh run list --workflow deploy-demo.yml --limit 5 --repo Nonname-organic/esports-platform
                                                          # 直近成功した Deploy の run-id（切り戻し用）
```

### 4. 新しい版の配置

PR を main へマージする。Build & Push のあと Deploy が自動で走る。手で `docker compose up` しない
（「サーバー上で docker compose を叩くときの注意」）。

### 5. DB マイグレーション

Deploy が readiness の通過後に `alembic upgrade head` を流す（028 → 029 → 030）。新しいコードが起動してから
適用が終わるまでの数秒は、結果報告と「チームを探す」募集の投稿が失敗しうる。終わったら確かめる:

```bash
docker compose exec -T api alembic current               # 030 (head)
```

028 で書き換わる大会を事前に控える場合は、下の「マイグレーション 028 を戻すとき」の読み取りクエリを使う。

### 6. コンテナの起動

Deploy は pull のあと、`docker compose up` の**前に**新しいイメージで本番設定を検査する
（`docker compose run --rm --no-deps -T api python -c "import app.core.config"`）。
DB パスワードが空・既定値、`SECRET_KEY` が見本値ならここで止まり、稼働中のコンテナはそのまま残る。
ログの「本番設定の不備: …」（値は出ない）を見て `.env` を直し、Deploy を再実行する。
検査そのものは RC1 のイメージで確認済み（既定値で終了コード 1・値の出力なし、固有の値で 0）。

### 7. ヘルスチェック

```bash
curl -fsS https://app.axelia-esports.jp/health/ready
docker compose ps                                         # すべて running、api は healthy
```

### 8. ログの確認

```bash
docker compose logs --since 10m api worker scheduler \
  | grep -i -E "error|traceback|too many clients|本番設定の不備" | grep -v -i bcrypt | tail -20
```

`error reading bcrypt version` の警告は passlib の既知の表示で、動作に影響しない。

### 9. 主要画面の確認

トップ、ログイン、大会一覧（期間「すべて」）、大会詳細の各タブ（Overview / Matches / Bracket）、試合ページ、
スカウト（LFP / LFT）、通知、ランキング、管理画面（管理者）。主催者で大会作成画面を開く
（作成まで試す場合は非公開で作り、確認後に削除する）。

### 10. 異常時の停止

readiness が通らない、5xx が続く、ログインできない、データの表示がおかしい、のいずれかなら公開を止める。
Deploy は設定検査と readiness で自動的に止まる。止まった状態から手で `docker compose up` はしない。
利用者への影響が続くなら 11 の切り戻しを先に行い、そのあと調べる。

### 11. ロールバック

RC2 で訂正した。以前ここにあった「直近成功の Deploy を再実行する」は使えない（Deploy workflow が無効の間は
再実行できず、再実行できるのも最初の実行から 30 日まで）。DB を戻す手順（`alembic downgrade`）も使わない。
イメージの版と digest を指定して戻す [RC2_ROLLBACK_RUNBOOK.md](release/RC2_ROLLBACK_RUNBOOK.md) に従う。
DB は 030 のままでよい（旧コードは 030 のスキーマで動く）。

### 12. 復旧後の確認

7〜9 をもう一度行い、`alembic current` が想定の版であることを確かめる。翌朝、03:15 UTC のバックアップが
取れていることを確認する。

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

## サーバー上で docker compose を叩くときの注意

**必ず `/opt/app` で実行する。** このサーバーは `.env` に `COMPOSE_FILE` を
持たせてあり、そこで初めて4つのオーバーレイが揃う。

```
COMPOSE_FILE=docker-compose.yml:docker-compose.prod.yml:docker-compose.tls.yml:docker-compose.conoha.yml
```

これが効かない状態（別ディレクトリ、`-f` を自分で並べて書き漏らす等）で
`docker compose up` を実行すると、素の `docker-compose.yml` だけで解決され、

- nginx が TLS 設定と証明書を失い、HTTPS が応答しなくなる
- 依存関係で api / frontend もローカルビルドのイメージに置き換わる

という壊れ方をする。実際に一度サイトを落としている。

`COMPOSE_FILE` が効いていれば、`IMAGE_ORG` / `IMAGE_TAG` を渡さない
`up` はイメージ解決に失敗してその場で止まる（黙って作り替えない）。
イメージを入れ替える操作はデプロイに任せ、手で `up` しないこと。

復旧させるときは、直近成功した Deploy を再実行するのが確実。

```bash
gh run rerun <直近の成功した Deploy の run-id> --repo Nonname-organic/esports-platform
```

### 切り戻しの判断

切り戻しは **直近成功した Deploy run の再実行** で行う。Deploy はタグを
`workflow_run.head_sha` から導出するので、再実行すればそのコミットの
イメージに戻る。手で `docker compose up` してイメージを差し替えないこと
（上に書いた壊れ方をする）。

ただし **イメージを戻せば元に戻る、とは限らない**。デプロイは `up -d` の
あとに `alembic upgrade head` を流すため、マイグレーションが成功した後に
イメージだけ戻すと、旧コードが新しいスキーマを読む状態になる。

| 戻す対象のデプロイ | 再実行だけで足りるか |
|---|---|
| マイグレーションを含まない | 足りる。スキーマは変化していない |
| add-only（`server_default` 付きの列追加など） | **旧アプリとの後方互換性を確認できた場合に限り** 足りる。未確認なら足りないものとして扱う |
| 列の削除・改名・型変更を含む | **足りない。** `alembic downgrade` が別途必要 |

判定は、戻す範囲に `backend/alembic/versions/` の追加があるかで見る。

```bash
git diff --name-only <戻したいSHA>..<現在のSHA> -- backend/alembic/versions/
```

add-only を「後方互換」と判断してよいのは、次を**実際に確認できたとき**だけ。
add-only という形だけでは根拠にならない。

- 追加した列が `NOT NULL` なら `server_default` が付いている（015 の
  `status_locked` が模範）
- 旧アプリのモデル定義・クエリが、増えた列やテーブルを要求しない
- 追加したテーブルを旧アプリが参照しない（外部キーの向きを含む）

確認できなければ `alembic downgrade` を含む手順が必要で、再実行だけでは戻らない。

なお PR #32（python-multipart の更新）はマイグレーションを含まないため1行目に
該当し、再実行だけで完全に戻る。ただしこれは**そのPR固有の事実**であって、
以後のデプロイへ一般化できる判断ではない。切り戻すたびに上の表で確認する。

## トラブルシューティング

### ポート 80/443 に外から繋がらない
ConoHa のセキュリティグループを確認（手順2）。管理画面で対象の
セキュリティグループがサーバーに適用されているかを見ます。

ufw は**無効のまま運用している**。有効にすると SSH だけが落ちる。
`/etc/default/ufw` が `MANAGE_BUILTINS=no` のため ufw は INPUT チェーンに
自分への分岐を入れず、ポリシーだけ DROP になって許可ルールに到達しない。
`MANAGE_BUILTINS=yes` にすると今度は FORWARD にも割り込み、既定 DROP で
コンテナ間通信が切れる恐れがある。外部に開いているホスト側のサービスは
sshd だけなので、絞り込みは ConoHa のセキュリティグループに任せている。

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
IMAGE_ORG=<github-org> IMAGE_TAG=<sha-xxxxxxx> \
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

もう一段確かめる場合（公開前・マイグレーション適用前に推奨）。2026-11 にローカルの使い捨て DB で
この手順どおりに取得→別DBへ復元→件数照合→アプリ起動まで確認済み。

```bash
F=backups/$(ls -1t backups | head -1)
gzip -t "$F" && echo "gzip OK"                                         # 壊れていない
gzip -dc "$F" | tail -8 | grep -q "PostgreSQL database dump complete" \
  && echo "最後まで出力されている"                                         # 途中で切れていない
sha256sum "$F"                                                          # 保存先へ送ったものと照合する

# 復元先（restore_test）と本番で主要テーブルの件数とマイグレーション版を比べる
Q="select 'users',count(*) from users union all select 'teams',count(*) from teams
   union all select 'tournaments',count(*) from tournaments
   union all select 'registrations',count(*) from tournament_registrations
   union all select 'matches',count(*) from matches
   union all select 'alembic',version_num::int from alembic_version"
docker compose exec -T postgres psql -U esports_user -d esports_db   -tAc "$Q" > /tmp/src.txt
docker compose exec -T postgres psql -U esports_user -d restore_test -tAc "$Q" > /tmp/dst.txt
diff /tmp/src.txt /tmp/dst.txt && echo "件数・版とも一致"
```

### マイグレーション 028〜030 は戻さない（RC2 で訂正）

以前この節にあった `alembic downgrade 027`（028 だけを戻す）と、030 を戻す手順は使わない。

- `alembic downgrade 027` は、030・029・028 をまとめて戻す。029 の表（`match_result_reports`）が消えるので、
  新しいイメージでは結果の登録がすべて 500 になる。旧イメージは 030 を知らないので、その中では実行もできない
- 030 を戻すには `player_seeks` の投稿を消す必要がある。応募（`recruitment_applications`）が ON DELETE CASCADE で
  一緒に消え、元に戻せない

切り戻しは、DB をそのままにしてイメージだけを前の版へ戻す。旧コード（027 まで）は 030 のスキーマで動く。
手順は [RC2_ROLLBACK_RUNBOOK.md](release/RC2_ROLLBACK_RUNBOOK.md) を参照する。

- 旧イメージで動かした期間の後に新しいイメージへ戻したら、028 の補正を流し直す（同じ文書の SQL。
  028 の UPDATE をそのまま流すと、その間に主催者が公開へ戻した大会が非公開に戻ってしまうので使わない）
- 028 の補正で公開範囲が主催者の意図と違ってしまった大会は、SQL ではなく、主催者か管理者が編集画面で設定し直す
  （列と `rules` の両方が書かれる。列だけを SQL で戻すと、次に補正を流したときにまた変わる）

補正の対象を控えておく場合（読み取りのみ）:

```bash
docker compose exec -T postgres psql -U esports_user -d esports_db -c "
  SELECT id, name, visibility, rules->>'visibility' FROM tournaments
   WHERE visibility = 'public' AND rules->>'visibility' IN ('limited', 'private');"
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

SMTP未設定でもアプリは動きますが、パスワードリセットのメールが届きません。
本文（再設定リンクを含む）は秘密情報にあたるため、通常のログには出さず
`LOG_LEVEL=DEBUG` のときだけ出します。宛先のアドレスはログに残さず、ドメインだけを記録します。
公開前に必ず設定してください。

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
