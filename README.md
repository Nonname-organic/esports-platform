# e-Sports 大会一元管理プラットフォーム

VALORANT / League of Legends / Apex Legends などの e-Sports 大会を一元管理する Web プラットフォーム。  
エントリー管理・ブラケット自動生成・リアルタイムスコア更新・統計分析基盤を統合する個人開発プロジェクト。

> AWS / Docker / Terraform / CI/CD の**実践的な使い方**と、  
> フルスタック開発における**設計判断・技術選定の根拠**をポートフォリオとして提示することを目的に構築。

[![CI](https://github.com/your-username/esports-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/your-username/esports-platform/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 目次

- [プロジェクト概要](#プロジェクト概要)
- [技術スタック](#技術スタック)
- [アーキテクチャ設計と選定理由](#アーキテクチャ設計と選定理由)
- [バックエンド設計の工夫](#バックエンド設計の工夫)
- [フロントエンド設計の工夫](#フロントエンド設計の工夫)
- [データベース設計の工夫](#データベース設計の工夫)
- [インフラ設計とコスト戦略](#インフラ設計とコスト戦略)
- [AWS 無料枠 制限・注意事項](#aws-無料枠-制限注意事項)
- [セットアップ](#セットアップ)
- [ディレクトリ構成](#ディレクトリ構成)
- [CI/CD](#cicd)

---

## プロジェクト概要

### 解決する課題

e-Sports 大会の運営は現状、**Googleスプレッドシートで参加者管理、Challongeでブラケット管理、Discordで結果通知** という複数ツールの手動連携が一般的。  
これを一つのプラットフォームで完結させ、主催者の運営コストを削減する。

### 主要機能

| 機能 | 説明 |
|------|------|
| 大会管理 | 大会の作成・参加受付・チェックイン管理 |
| ブラケット自動生成 | シングル / ダブルエリミネーション / ラウンドロビン / スイス式 |
| リアルタイムスコア | WebSocket によるライブスコア更新・ブラケット反映 |
| 統計分析 | マップ勝率・エージェント構成・KDA ランキングの可視化 |
| 非同期通知 | SQS → Lambda → Discord Webhook による試合結果通知 |
| RBAC | Admin / Organizer / Team Manager / Player / Viewer の 5 ロール |

### フェーズ設計

| フェーズ | コスト | 規模の目安 | 主な変更点 |
|---------|--------|----------|-----------|
| **Demo（現在）** | **~$0.50/月** | 〜 50 チーム | EC2 t2.micro + Docker Compose |
| MVP | ~$185/月 | 〜 500 チーム | ECS Fargate + ALB + ElastiCache |
| Production | ~$1,100/月 | 5,000+ チーム | EKS + Aurora Serverless v2 + CloudFront |

---

## 技術スタック

| レイヤー | 技術 | 選定理由（後述） |
|---------|------|----------------|
| **Frontend** | Next.js 15 (App Router) / TypeScript / Tailwind CSS | SSR/ISR/CSR の使い分けによる UX 最適化 |
| **State** | TanStack Query v5 / Zustand v5 | Server State と Client State の明確な分離 |
| **Backend** | FastAPI / Python 3.12 / SQLAlchemy 2.0 async | 非同期 I/O による高スループット |
| **DB** | PostgreSQL 15 | JSONB・部分インデックス・tsvector による最適化 |
| **Cache / PubSub** | Redis 7 | WebSocket の水平スケーリングと分散ロック |
| **Queue** | AWS SQS | ランキング更新と通知の非同期デカップリング |
| **Infra** | AWS Free Tier / Terraform OSS / Docker Compose | コスト $0 から始め Terraform で IaC 管理 |
| **CI/CD** | GitHub Actions / GHCR | Public リポジトリなら Actions/GHCR とも無制限無料 |
| **Monitoring** | CloudWatch / Grafana Cloud / Sentry | すべて無料枠で本番同等の可観測性を実現 |

---

## アーキテクチャ設計と選定理由

### Demo フェーズ構成図

```
ユーザー
  │
  ▼
CloudFront (Always Free: 1TB転送/月)
  │ HTTPS
  ▼
EC2 t2.micro ─── Security Group ───▶ RDS db.t3.micro (PostgreSQL 15)
│  1GB RAM                            20GB, Single-AZ
│
├── Nginx          (64MB)   ← ALB の代替 ($6/月節約)
├── Next.js        (300MB)  ← SSR/ISR/CSR ハイブリッド
├── FastAPI        (300MB)  ← Async, Clean Architecture
├── Worker         (150MB)  ← SQS Consumer
└── Redis          (140MB)  ← Cache + PubSub ($15/月節約)
     合計: ~954MB / 1GB (スワップ 512MB で余裕確保)
│
├──▶ S3 (5GB, 12ヶ月無料)        ← 画像・CSV エクスポート
├──▶ SQS (1M req/月 Always Free) ← 試合結果イベントキュー
└──▶ Lambda (Always Free)        ← Discord Webhook 通知
```

**ALB / ElastiCache / NAT Gateway を使わない理由:**  
Demo フェーズでは月額 $0 を目標とした。ALB ($6~/月), ElastiCache ($15~/月), NAT Gateway ($32~/月) を排除し、  
Nginx・Docker Redis・Public Subnet で代替することで **$53+/月の節約** を実現。  
スケールアップ時は Terraform の `environments/mvp` に切り替えるだけで ECS + ALB + ElastiCache 構成に移行できる設計にしている。

---

### FastAPI を選んだ理由（Django REST / Spring Boot との比較）

| 観点 | FastAPI | Django REST | Spring Boot |
|------|---------|-------------|-------------|
| **非同期** | ネイティブ async/await | 3.1+ で部分対応 | WebFlux (別フレームワーク) |
| **型安全** | Pydantic v2 で入出力を自動バリデーション | Serializer で手動 | Bean Validation |
| **起動速度** | ~200ms (Uvicorn) | ~1s | ~5s (JVM warm-up) |
| **自動ドキュメント** | OpenAPI/Swagger 自動生成 | drf-spectacular 追加必要 | Springdoc 追加必要 |
| **学習コスト** | 低（Python + 型ヒントのみ） | 中（Django ORM の暗黙ルール） | 高（Java エコシステム） |

WebSocket を多用するリアルタイム更新・S3/SQS への非同期 I/O が多いため、**非同期ネイティブの FastAPI** を採用。

---

### PostgreSQL を選んだ理由（MySQL / DynamoDB との比較）

- **JSONB**: ゲームによってキルデス以外の固有スタット（ヘッドショット率, ランク等）が異なる。  
  `custom_stats JSONB` カラムにゲーム固有データを格納し、GIN インデックスで検索可能にした。  
  MySQL の JSON 型は GIN に相当する高速な全文検索インデックスを持たない。

- **BRIN インデックス**: 監査ログ (`audit_logs`) と分析イベント (`analytics_events`) は時系列で追記のみ。  
  B-Tree の 1/100 以下のサイズで済む BRIN インデックスを `created_at` に適用。

- **`tsvector` 全文検索**: 大会名・チーム名の日本語検索。`pg_bigm` + `generated column` で  
  アプリケーション側での形態素解析なしに全文検索インデックスを自動メンテナンス。

- **パーティショニング**: `analytics_events` / `audit_logs` を月次 Range パーティションで分割。  
  古いパーティションを `DROP PARTITION` 一発で削除でき、`VACUUM` コストを抑制。

---

## バックエンド設計の工夫

### 1. Clean Architecture による依存関係の制御

```
API Layer (FastAPI Router)
  │  HTTP リクエスト/レスポンスのみを責務とする
  ▼
Service Layer (Business Logic)
  │  トランザクション境界・ドメインルールを責務とする
  ▼
Repository Layer (Data Access)
  │  DB クエリを責務とする（Service は SQL を知らない）
  ▼
Model Layer (SQLAlchemy ORM)
```

**メリット**: Service のテストに DB が不要（Repository をモック可能）。  
DB を PostgreSQL → MySQL に変えても Service/API 層は無変更。

```python
# 依存注入は FastAPI の Depends で管理
async def register_result(
    match_id: UUID,
    data: ResultSchema,
    service: MatchService = Depends(get_match_service),  # ← DI
    current_user: AuthUser = Depends(require_roles("organizer", "admin")),
):
    return await service.register_result(match_id, data, current_user.id)
```

---

### 2. Redis 分散ロックによる二重登録防止

試合結果の登録は **複数の主催者が同時に操作する可能性** があり、二重登録するとランキングが狂う。  
楽観的ロック（バージョン番号）は DB ラウンドトリップが発生するため、  
**Redis の `SET NX EX`（Get-Or-Set Atomic）** で分散ロックを実装した。

```python
async def register_result(self, match_id: UUID, data: ResultSchema) -> Match:
    lock_key = f"lock:match_result:{match_id}"

    # Redis SET NX EX → 他プロセスがロック中なら即座に失敗
    if not await self._cache.acquire_lock(lock_key, ttl=10):
        raise ConflictError("結果を処理中です。しばらく待ってから再試行してください。")

    try:
        match = await self._repo.get_or_404(match_id)
        if match.status == MatchStatus.COMPLETED:
            raise ConflictError("すでに結果が登録されています。")
        # ... DB 更新、SQS 送信
    finally:
        await self._cache.delete(lock_key)  # ロック解放
```

---

### 3. WebSocket + Redis Pub/Sub による水平スケーリング対応

**問題**: EC2 1台なら WebSocket セッションをメモリで管理できるが、  
ECS/EKS で複数コンテナになると、チーム A の接続が container-1、  
チーム B の接続が container-2 にあると、container-1 からの Broadcast が container-2 のクライアントに届かない。

**解決**: スコア更新時に Redis の `PUBLISH` でチャンネルに配信し、  
各コンテナが `SUBSCRIBE` で受信して自身に接続している全クライアントに `send_text` する。

```
FastAPI (container-1)          FastAPI (container-2)
   WebSocket 接続 x 30            WebSocket 接続 x 25
         │                               │
         └──── SUBSCRIBE ────┐ ┌─── SUBSCRIBE ────┘
                             ▼ ▼
                        Redis PUBLISH
                      match:{id}:score
```

```python
# スコア更新 API → Redis Publish
await self._cache.publish(
    channel=f"match:{match_id}:score",
    message=json.dumps({"type": "score_update", "team1_score": 8, "team2_score": 5}),
)

# WebSocket ルーター → Redis Subscribe → 全クライアントへ Broadcast
async def redis_pubsub_listener(match_id: str, manager: ConnectionManager):
    async for message in cache.subscribe(f"match:{match_id}:score"):
        await manager.broadcast(match_id, message)
```

---

### 4. SQS による非同期デカップリング

試合結果登録の**同期処理**に含めると、ランキング再計算と Discord 通知が失敗しても API がエラーを返す。  
ランキング更新は試合結果の数秒後で許容できるため、SQS キューに投げて**非同期で処理**する。

```
POST /matches/{id}/result
  │
  ├── DB 更新（同期、失敗したら 500 エラー）
  └── SQS.send_message("match_result_event")  ← ノンクリティカル、失敗しても握りつぶす
        │
        └── Worker (SQS Consumer)
              ├── ランキング再計算（Redis キャッシュ削除 → 次回クエリで再集計）
              └── Lambda 呼び出し → Discord Webhook 送信
```

**SQS の Dead Letter Queue (DLQ)** を設定し、3 回リトライ後も失敗したイベントを DLQ に移動。  
CloudWatch アラームで DLQ メッセージ数が 0 より大きい場合に通知する設定を入れた。

---

### 5. RBAC の実装（5 ロール）

```python
class UserRole(str, enum.Enum):
    ADMIN         = "admin"         # 全操作
    ORGANIZER     = "organizer"     # 自身が主催する大会のみ管理
    TEAM_MANAGER  = "team_manager"  # 自チームのメンバー管理
    PLAYER        = "player"        # 試合履歴閲覧・プロフィール編集
    VIEWER        = "viewer"        # 閲覧のみ

# 権限チェックは Dependency として共通化
def require_roles(*roles: UserRole):
    async def check(current_user: AuthUser = Depends(get_current_user)):
        if current_user.role not in roles:
            raise ForbiddenError("この操作には権限が必要です。")
        return current_user
    return check
```

Organizer が他人の大会を操作できないよう、Service 層で `organizer_id == current_user.id` を追加検証。  
API 層のロールチェックと Service 層のオーナーシップ検証の**2 段階防御**。

---

### 6. ブラケット自動生成アルゴリズム

シングルエリミネーション: `n` チームを 2 のべき乗に切り上げ、  
超過分を Bye（不戦勝）として埋めることで奇数チームでも破綻しない。

```python
def _generate_single_elimination(self, teams: list[Team]) -> list[Match]:
    size = 2 ** math.ceil(math.log2(len(teams)))  # 例: 6チーム → 8
    padded = teams + [None] * (size - len(teams))  # None = Bye
    random.shuffle(padded)

    matches = []
    for i in range(0, size, 2):
        t1, t2 = padded[i], padded[i + 1]
        match = Match(team1=t1, team2=t2)
        if t2 is None:          # Bye → 自動的に t1 が勝者
            match.winner = t1
            match.status = MatchStatus.COMPLETED
        matches.append(match)

    # 勝者を next_match_id で連結（自己参照 FK）
    self._link_matches(matches)
    return matches
```

---

## フロントエンド設計の工夫

### レンダリング戦略の使い分け

Next.js App Router の SSG / ISR / SSR / CSR を**ページの性質に応じて使い分け**た。  
一律 CSR にすると SEO が死ぬ。一律 SSR にするとオリジンサーバー負荷が高い。

| ページ | 戦略 | 理由 |
|--------|------|------|
| `/` ホーム | **ISR** `revalidate=300` | 開催中大会は5分鮮度で十分。CDN キャッシュで負荷ゼロ |
| `/tournaments` 一覧 | **CSR** (TanStack Query `staleTime: 5min`) | ゲーム/ステータスフィルタ + 無限スクロールが必要 |
| `/tournaments/[id]` 詳細 | **SSR** `cache: "no-store"` | 参加チーム数が常に最新である必要。SEO のため Server Component |
| `/tournaments/[id]/bracket` | **SSR + CSR** ハイブリッド | SSR で初期描画しつつ、CSR で 30 秒ポーリング更新 |
| `/matches/[id]` 試合詳細 | **CSR + WebSocket** | リアルタイムスコアのため完全 CSR |
| `/analytics` 分析 | **CSR** | 認証必須ページ + インタラクティブなチャート操作 |

---

### TanStack Query v5 と SSR のハイドレーション

Bracket ページでは `Server Component` でデータを取得し、`BracketPageClient` に初期値として注入することで **初回 FCP を速く保ちながら**、以降は Client Side でポーリング更新する。

```tsx
// Server Component: SSR で初期データ取得
export default async function BracketPage({ params }) {
  const initialBracket = await serverFetch(`/api/v1/tournaments/${id}/bracket`);

  return (
    // 初期データを Client Component に渡す
    <BracketPageClient tournamentId={id} initialBracket={initialBracket} />
  );
}

// Client Component: SSR の初期値を TanStack Query キャッシュに注入
export function BracketPageClient({ tournamentId, initialBracket }) {
  const qc = useQueryClient();
  useEffect(() => {
    qc.setQueryData(["tournaments", "bracket", tournamentId], { data: initialBracket });
  }, [initialBracket]);

  // 30秒ポーリング（WS補完）
  const { data: bracket } = useBracket(tournamentId); // refetchInterval: 30s
  return <BracketView bracket={bracket ?? initialBracket} />;
}
```

---

### Server State vs Client State の分離

| 状態の種類 | 管理ライブラリ | 理由 |
|-----------|-------------|------|
| API レスポンス（大会/試合/ランキング） | **TanStack Query** | キャッシュ・staleTime・refetch・mutation の宣言的管理 |
| ユーザー認証（JWT, ロール） | **Zustand** + localStorage | ページリロード跨ぎの永続化が必要 |
| UI ローカル状態（モーダル, フィルタ） | **useState** | スコープが狭く他コンポーネントと共有不要 |

`useAuthStore` は `persist` middleware で localStorage に保存し、**次回アクセス時に再ログイン不要**。  
`setTokens` 呼び出し時に `localStorage.setItem("access_token")` も同時に行い、  
`api-client.ts` の `serverFetch` とも整合させた。

---

### Recharts によるデータ可視化

| チャート | 表示内容 | 工夫点 |
|---------|---------|--------|
| `BarChart` | マップ別攻撃/守備勝率 | 積み上げ棒グラフで攻守のバランスを直感的に表示 |
| `RadarChart` | 選手パフォーマンス比較 | KDA / Kills / Assists / FB / Win率 の 5 軸で最大 6 選手を重ねて比較 |
| `CompositionTable` | エージェント構成勝率 | 試合数が少ないと勝率がブレるため 3 試合以上のデータのみ表示 |

---

## データベース設計の工夫

### ER 図（主要テーブル）

```
tournaments ──< registrations
     │
     └──< matches ──< match_games ──< player_match_stats
               │
               └── next_match_id (自己参照FK: ブラケット進行)

teams ──< team_members >── users
players ──< player_stats (集計済みテーブル)

analytics_events (月次パーティション)
audit_logs       (月次パーティション)
```

### インデックス戦略

```sql
-- BRIN: 時系列追記テーブルに最適（B-Tree の 1/100 サイズ）
CREATE INDEX CONCURRENTLY idx_analytics_events_created_brin
  ON analytics_events USING BRIN (created_at);

-- GIN: JSONB の内部キー検索
CREATE INDEX CONCURRENTLY idx_player_stats_agent_breakdown_gin
  ON player_match_stats USING GIN (custom_stats);

-- 部分インデックス: 特定条件のクエリを絞り込み
CREATE INDEX CONCURRENTLY idx_matches_ongoing
  ON matches (tournament_id, scheduled_at)
  WHERE status = 'ongoing';

-- tsvector: 大会名の日本語全文検索（Generated Column で自動更新）
ALTER TABLE tournaments
  ADD COLUMN name_tsv tsvector
  GENERATED ALWAYS AS (to_tsvector('simple', name)) STORED;
CREATE INDEX idx_tournaments_name_fts ON tournaments USING GIN (name_tsv);
```

### UUID 主キーの採用理由

- オートインクリメント ID はシャーディング時に衝突する
- `gen_random_uuid()` (PostgreSQL 13+) で DB 側生成、アプリ側での採番が不要
- 外部に ID を晒す際も総件数・登録順が推測されない（セキュリティ）

### JSONB の活用

ゲームによって独自スタットが異なる問題を `custom_stats JSONB` で解決。  
スキーマ変更なしに新ゲームを追加できる。

```json
// VALORANT の custom_stats
{
  "headshot_rate": 0.35,
  "plants": 3,
  "defuses": 1,
  "first_bloods": 2,
  "rank": "Radiant"
}

// Apex の custom_stats
{
  "damage_dealt": 2847,
  "knockdowns": 4,
  "revives": 2,
  "legend": "Wraith"
}
```

---

## インフラ設計とコスト戦略

### Terraform による環境分離

```
terraform/
├── modules/
│   ├── ec2/        # 再利用: t2.micro → t3.medium → m5.xlarge
│   ├── rds/        # 再利用: db.t3.micro → db.t3.medium → Aurora
│   ├── ecs/        # MVP / Prod 用
│   ├── eks/        # Prod 用
│   └── networking/ # VPC / Subnet / Security Group
└── environments/
    ├── demo/       # EC2 + Docker Compose ($0.50/月)
    ├── mvp/        # ECS Fargate + RDS ($185/月)
    └── prod/       # EKS + Aurora Serverless v2 ($1,100/月)
```

モジュールを共通化することで、`demo` → `mvp` への移行は `environments/mvp` の `terraform apply` のみで完了。  
各環境の差分は `variables.tf` で管理し、モジュール本体は変更しない。

### Docker Compose メモリ管理（t2.micro 1GB 制約）

```yaml
services:
  nginx:    mem_limit: 64m
  frontend: mem_limit: 300m   # Next.js standalone (node server.js)
  api:      mem_limit: 300m   # FastAPI + Uvicorn
  worker:   mem_limit: 150m   # SQS Consumer
  redis:    mem_limit: 140m   # --save "" でディスク永続化なし
  # 合計: 954MB → スワップ 512MB で余裕を確保
```

Redis は揮発性（`--save ""`）で運用。キャッシュは再起動で消えて構わない設計。  
Next.js は `output: "standalone"` で不要ファイルを除去し、メモリ使用量を削減。

### Kubernetes への移行準備

Demo フェーズは Docker Compose だが、**Kubernetes への移行を前提とした設計**にしている。

- `ConfigMap` 相当: 環境変数を `.env` ファイルで外部化
- `Liveness Probe` 相当: Docker Compose `healthcheck` で起動順序を制御
- `HorizontalPodAutoscaler` 相当: `mem_limit` + OOM 再起動ポリシーで過負荷を回避
- Pub/Sub を Redis 経由にすることで、Pod が複数になっても WebSocket が機能する

---

## AWS 無料枠 制限・注意事項

> **⚠️ 本プロジェクトは AWS の無料枠を最大限活用しています。以下の制限を超えると料金が発生します。**

### 12ヶ月間無料（新規 AWS アカウントのみ）

| サービス | 無料枠 | 超過時の料金 | 期限切れ後の月額 |
|---------|-------|------------|----------------|
| EC2 t2.micro | **750 時間/月**（1 台なら 744h で収まる） | $0.0116/時 | **~$8.4/月** |
| RDS db.t3.micro | **750 時間/月、20GB** | $0.017/時、$0.115/GB | **~$12.4/月** |
| S3 | **5GB、PUT 2,000 回、GET 20,000 回** | $0.025/GB | **~$1/月** |
| ECR | **500MB/月** | $0.10/GB | ~$0.05/月 |
| データ転送 | **15GB アウトバウンド/月** | $0.114/GB | 注意 |

### Always Free（期限なし）

| サービス | 無料枠 |
|---------|-------|
| Lambda | 1M リクエスト/月、400K GB-秒/月 |
| SQS | 1M リクエスト/月 |
| CloudFront | 1TB 転送/月、10M リクエスト/月 |
| CloudWatch | 10 カスタムメトリクス、5GB ログ |
| EventBridge | ~無料（$1/100 万イベント） |

### 月額コスト試算

```
Route53 ホストゾーン: $0.50/月
その他すべて:         $0.00/月（無料枠内）
─────────────────────────────────────────
合計:                 $0.50/月

※ EC2 パブリック IP を直接使う場合は Route53 不要で $0.00/月も可能
```

### 無料枠超過を防ぐ設定

```
✅ EC2: 1台のみ運用（2台目から課金）
✅ RDS: Single-AZ（Multi-AZ は 2 倍カウント）
✅ RDS バックアップ保持: 1日（デフォルト 7 日より削減）
✅ CloudWatch ログ保持: 30 日（デフォルト無期限は危険）
✅ S3 アップロード: 1 ファイル 5MB 制限
✅ Billing Alert: $1 で即通知（Budgets → Create Budget）
✅ NAT Gateway: 不使用（$32/月節約）
✅ ALB: 不使用（$6~/月節約, Nginx で代替）
✅ ElastiCache: 不使用（$15~/月節約, Docker Redis で代替）
```

### 無料ツール（AWS 以外）

| ツール | 無料枠 | 用途 |
|-------|-------|------|
| GitHub Actions | Public: 無制限 / Private: 2,000 分/月 | CI/CD |
| GitHub Container Registry | Public: 無制限 | Docker イメージ |
| Terraform OSS | 完全無料 | IaC |
| Grafana Cloud | 3 ユーザー、10K メトリクス、14 日保持 | 監視 |
| Sentry | 5,000 イベント/月 | エラー追跡 |
| Discord Webhook | 完全無料 | 試合結果通知 |

> **GitHub Actions 消費量目安:**  
> PR 時 (lint + test): 約 8 分 × 20PR = 160 分  
> Deploy 時: 約 10 分 × 10 回 = 100 分  
> **合計: 約 260 分/月**（2,000 分中 13%）

---

## セットアップ

### 前提条件

- AWS アカウント（新規推奨）
- Terraform >= 1.9
- Docker / Docker Compose
- Python 3.12
- Node.js 20

### 1. クローン & 環境変数設定

```bash
git clone https://github.com/your-username/esports-platform.git
cd esports-platform
cp backend/.env.example backend/.env
```

```env
# Database
DB_HOST=your-rds-endpoint.rds.amazonaws.com
DB_NAME=esports_db
DB_USER=esports_user
DB_PASSWORD=your-secure-password

# Auth
SECRET_KEY=your-256bit-secret-key   # openssl rand -hex 32
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# AWS
AWS_REGION=ap-northeast-1
S3_BUCKET_NAME=esports-assets-{account-id}
SQS_QUEUE_URL=https://sqs.ap-northeast-1.amazonaws.com/{account}/match-queue

# Discord
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

### 2. Terraform でインフラ構築

```bash
cd terraform/environments/demo
terraform init
terraform plan
terraform apply   # EC2, RDS, S3, SQS, Lambda が作成される
```

### 3. EC2 初期セットアップ

```bash
ssh -i ~/.ssh/your-key.pem ec2-user@{ec2-ip}

# Docker インストール
sudo yum update -y && sudo yum install docker -y
sudo systemctl start docker
sudo usermod -aG docker ec2-user

# スワップ設定（t2.micro メモリ不足対策）
sudo dd if=/dev/zero of=/swapfile bs=128M count=4
sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile
echo '/swapfile swap swap defaults 0 0' | sudo tee -a /etc/fstab
```

### 4. アプリケーション起動

```bash
git clone https://github.com/your-username/esports-platform.git
cd esports-platform
cp backend/.env.example backend/.env && vim backend/.env

docker-compose up -d

# DB マイグレーション（初回のみ）
docker-compose exec api alembic upgrade head

# ログ確認
docker-compose logs -f
```

### 5. ローカル開発

```bash
# バックエンド
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# フロントエンド
cd frontend
npm install
npm run dev
```

---

## ディレクトリ構成

```
esports-platform/
├── backend/
│   ├── app/
│   │   ├── api/           # FastAPI ルーター (HTTP + WebSocket)
│   │   ├── core/          # 設定・JWT・Redis・依存注入
│   │   ├── models/        # SQLAlchemy 2.0 ORM モデル
│   │   ├── repositories/  # Repository パターン (DB アクセス層)
│   │   ├── services/      # ビジネスロジック (Clean Architecture)
│   │   └── schemas/       # Pydantic v2 入出力スキーマ
│   ├── alembic/           # マイグレーション (非同期 env.py)
│   └── tests/
├── frontend/
│   └── src/
│       ├── app/           # Next.js App Router ページ
│       │   ├── (public)/  # 認証不要ルート
│       │   └── (auth)/    # 認証必須ルート
│       ├── components/    # 共通 UI コンポーネント
│       ├── features/      # 機能別モジュール (API / Hooks / Components)
│       ├── store/         # Zustand (認証状態)
│       ├── types/         # TypeScript 型定義
│       └── lib/           # API クライアント / ユーティリティ
├── terraform/
│   ├── modules/           # 再利用可能な Terraform モジュール
│   └── environments/
│       ├── demo/          # EC2 + Docker Compose (~$0.50/月)
│       ├── mvp/           # ECS + RDS (~$185/月)
│       └── prod/          # EKS + Aurora (~$1,100/月)
├── .github/workflows/     # GitHub Actions CI/CD
├── docker-compose.yml
└── docs/
    ├── phase1_architecture.md
    ├── phase2_db_design.md
    ├── phase3_backend.md
    └── phase4_frontend.md
```

---

## CI/CD

```
PR オープン時 (~8分):
  ├── Backend: ruff lint → mypy → pytest
  └── Frontend: eslint → tsc --noEmit → jest

main マージ時 (~10分):
  ├── Docker Build (multi-stage)
  ├── GHCR Push (ghcr.io/your-username/esports-*)
  └── EC2 SSH Deploy (docker-compose pull && up -d)
```

詳細: [docs/phase8_cicd.md](docs/phase8_cicd.md)

---

## 今後の拡張（フェーズアップ）

| 条件 | 次フェーズ | 主な変更 |
|------|----------|---------|
| 登録チーム 50 超 or 12ヶ月後 | **MVP** (~$185/月) | ECS Fargate + RDS t3.medium + ALB + ElastiCache |
| 登録チーム 500 超 | **Production** (~$1,100/月) | EKS + Aurora Serverless v2 + CloudFront カスタムドメイン |
| 分析データ大量 | **Analytics 拡張** | S3 Data Lake + AWS Glue + Amazon Athena + QuickSight |

---

## ライセンス

MIT

---

*個人開発プロジェクト。AWS / Docker / Terraform / Kubernetes / CI/CD の実践と、フルスタック設計力のポートフォリオとして構築。*
