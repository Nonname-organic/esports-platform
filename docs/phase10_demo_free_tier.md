# Phase 10 — $0 Demo インフラ

AWSを一切使わずに本番相当の構成を無料枠内で動かすためのセットアップガイドです。  
アクセスが増えてAWSへ移行する場合は末尾の「AWS移行手順」を参照してください。

---

## アーキテクチャ概要

```
ユーザー
  │
  ├─► Vercel (Next.js フロントエンド)   ← GitHub push で自動デプロイ
  │
  └─► Fly.io esports-platform-api      ← FastAPI
        │
        ├─ Neon (PostgreSQL)            ← アクセス時のみ起動するサーバーレスDB
        ├─ Upstash Redis                ← キャッシュ + ジョブキュー (SQS代替)
        └─ Cloudflare R2 (S3互換)      ← ファイルストレージ

  Fly.io esports-platform-worker        ← バックグラウンドジョブ処理
        │
        ├─ Neon (同上)
        └─ Upstash Redis (BRPOP でキュー取得)
```

---

## 各サービスの無料枠

| サービス | 用途 | 無料枠 |
|----------|------|--------|
| **Vercel** | Next.js ホスティング | 無制限 (Hobby) |
| **Fly.io** | API + Worker コンテナ | $5/月クレジット (shared-cpu-1x×2台で十分) |
| **Neon** | PostgreSQL | 0.5 GB、autosuspend あり |
| **Upstash** | Redis (キャッシュ + キュー) | 10,000 コマンド/日、256 MB |
| **Cloudflare R2** | ファイルストレージ | 10 GB ストレージ、無料 egress |

---

## セットアップ手順

### 1. Neon (PostgreSQL)

1. [neon.tech](https://neon.tech) でアカウント作成 → プロジェクト作成
2. 接続情報をメモ:
   - Host: `ep-xxx.ap-southeast-1.aws.neon.tech`
   - Database: `neondb` (または任意の名前)
   - User: `neondb_owner`
   - Password: コンソールで確認

3. マイグレーション用に `DB_SSL_REQUIRED=true` が必要です（後述の Fly.io セットアップで設定）。

### 2. Upstash Redis

1. [upstash.com](https://upstash.com) でアカウント作成 → Redis データベース作成 (region: `ap-northeast-1`)
2. 接続情報をメモ:
   - Host: `xxx.upstash.io`
   - Port: `6379`
   - Password: コンソールで確認

> Upstash は TLS 接続を要求します。既存の `redis_url` プロパティが `rediss://` スキームを使うよう、  
> `REDIS_PASSWORD` を設定すれば自動的に対応しています。

### 3. Cloudflare R2

1. Cloudflare ダッシュボード → R2 → バケット作成 (例: `esports-demo`)
2. R2 API トークン作成:
   - Access Key ID → `AWS_ACCESS_KEY_ID`
   - Secret Access Key → `AWS_SECRET_ACCESS_KEY`
3. エンドポイント URL: `https://<account-id>.r2.cloudflarestorage.com`

R2 は boto3 の S3 クライアントと互換性があります。`S3_ENDPOINT_URL` を設定するだけで切り替わります。

### 4. Fly.io — API

```bash
# flyctl インストール (macOS)
brew install flyctl
flyctl auth login

# アプリ作成
flyctl apps create esports-platform-api --org <your-org>

# シークレット設定 (値は各サービスのコンソールで確認)
flyctl secrets set --app esports-platform-api \
  SECRET_KEY="<32文字以上のランダム文字列>" \
  DB_HOST="ep-xxx.ap-southeast-1.aws.neon.tech" \
  DB_NAME="neondb" \
  DB_USER="neondb_owner" \
  DB_PASSWORD="<neon-password>" \
  REDIS_HOST="xxx.upstash.io" \
  REDIS_PORT="6379" \
  REDIS_PASSWORD="<upstash-password>" \
  S3_BUCKET_NAME="esports-demo" \
  S3_ENDPOINT_URL="https://<account-id>.r2.cloudflarestorage.com" \
  AWS_ACCESS_KEY_ID="<r2-key-id>" \
  AWS_SECRET_ACCESS_KEY="<r2-secret>" \
  ALLOWED_ORIGINS="https://<your-app>.vercel.app"
```

`fly.toml` は `infrastructure/fly/api/fly.toml` にあります。

### 5. Fly.io — Worker

```bash
flyctl apps create esports-platform-worker --org <your-org>

flyctl secrets set --app esports-platform-worker \
  SECRET_KEY="<同じ値>" \
  DB_HOST="<neon-host>" \
  DB_NAME="neondb" \
  DB_USER="neondb_owner" \
  DB_PASSWORD="<neon-password>" \
  REDIS_HOST="xxx.upstash.io" \
  REDIS_PORT="6379" \
  REDIS_PASSWORD="<upstash-password>" \
  S3_BUCKET_NAME="esports-demo" \
  S3_ENDPOINT_URL="https://<account-id>.r2.cloudflarestorage.com" \
  AWS_ACCESS_KEY_ID="<r2-key-id>" \
  AWS_SECRET_ACCESS_KEY="<r2-secret>"
```

`fly.toml` は `infrastructure/fly/worker/fly.toml` にあります。

### 6. GitHub Secrets の設定

GitHub リポジトリ → Settings → Secrets and variables → Actions:

| シークレット名 | 値 |
|---|---|
| `FLY_API_TOKEN` | `flyctl auth token` の出力 |

GitHub Variables:

| 変数名 | 値 |
|---|---|
| `DEMO_DOMAIN` | Fly.io の API URL (例: `esports-platform-api.fly.dev`) |

### 7. Vercel — フロントエンド

1. [vercel.com](https://vercel.com) でアカウント作成 → GitHub リポジトリをインポート
2. Root Directory: `frontend`
3. 環境変数を設定:
   - `NEXT_PUBLIC_API_URL=https://esports-platform-api.fly.dev`

push するたびに Vercel が自動デプロイします。

---

## CI/CD フロー

```
git push main
  │
  ├─► Build & Push (.github/workflows/build.yml)
  │     └─ GHCR に API/Worker/Frontend イメージをプッシュ
  │
  └─► Deploy — Demo (.github/workflows/deploy-demo.yml)
        ├─ flyctl deploy esports-platform-api   (新イメージで更新)
        ├─ flyctl deploy esports-platform-worker
        └─ flyctl ssh console -C "alembic upgrade head"  (マイグレーション)

  Vercel は GitHub push を検知して独自に自動デプロイ
```

---

## キュー動作の仕組み

デモ環境では `USE_REDIS_QUEUE=true` により、SQS の代わりに Upstash Redis のリストをキューとして使用します。

| 操作 | SQS (AWS) | Redis (デモ) |
|------|-----------|--------------|
| メッセージ送信 | `sqs.send_message` | `LPUSH queue:match_events <json>` |
| メッセージ受信 | `receive_message` (long poll) | `BRPOP queue:match_events 20` |
| 処理完了後 | `delete_message` | 不要 (POPで取得済み) |
| 再試行 | VisibilityTimeout 経由 | 失敗時は再PUSH (将来対応) |

---

## AWS 移行手順

アクセスが増えて Fly.io の無料枠を超えたら:

### 1. Terraform で AWS 環境を構築

```bash
cd infrastructure/terraform/environments/demo  # または mvp
terraform init
terraform apply
```

### 2. 環境変数の切り替え

| 変数 | デモ値 | AWS値 |
|------|--------|-------|
| `USE_REDIS_QUEUE` | `true` | `false` |
| `SQS_MATCH_QUEUE_URL` | (未設定) | SQS URL |
| `SQS_NOTIFICATION_QUEUE_URL` | (未設定) | SQS URL |
| `SQS_ANALYTICS_QUEUE_URL` | (未設定) | SQS URL |
| `S3_ENDPOINT_URL` | R2 エンドポイント | (削除) |
| `DB_SSL_REQUIRED` | `true` | `false` (VPC内接続) |

### 3. デプロイ先の切り替え

- Demo EC2/ECS: `.github/workflows/deploy-mvp.yml` が引き継ぐ
- EKS: `.github/workflows/deploy-production.yml` が引き継ぐ

---

## トラブルシューティング

### Fly.io で `flyctl ssh console` が失敗する

```bash
flyctl agent restart
flyctl ssh console --app esports-platform-api -C "alembic upgrade head"
```

### Neon の接続がタイムアウトする

Neon は 5分間アクセスがないとサスペンドします。最初のリクエストで2〜3秒かかることがありますが正常です。  
本番移行時に AWS RDS に切り替えることでこの問題はなくなります。

### Upstash の 10,000 コマンド/日の上限に達した

- Grafana でキューの深さ (`esports_sqs_queue_depth`) を確認
- イベント発火頻度を下げるか、Upstash の有料プランに移行 ($0.2/10万コマンド)
- または `USE_REDIS_QUEUE=false` + SQS に切り替え
