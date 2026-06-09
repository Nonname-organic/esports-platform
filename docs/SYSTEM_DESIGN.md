# e-Sports大会一元管理プラットフォーム 設計書

> 最終更新: 2026-06
> ステータス: デモ環境稼働中（https://d3r8lgt0kvo61v.cloudfront.net）

---

## 1. システム概要

e-Sportsトーナメントの **作成・運営・参加・観戦・分析・スカウト** をプラットフォーム内で完結するSaaS。
Discordは補助ツールとし、大会進行の主導権はプラットフォーム側が持つ設計。

### 対応ゲームタイトル
VALORANT / Apex Legends / Counter-Strike 2 / League of Legends / Overwatch 2 / Rocket League
（`SUPPORTED_GAMES` 定義への追加だけで拡張可能な設計）

---

## 2. アーキテクチャ全体図

```
                        ┌─────────────┐
   ユーザー ──HTTPS──▶  │ CloudFront  │ (CDN + キャッシュ)
                        └──────┬──────┘
                               │
                        ┌──────▼──────┐
                        │ EC2 (Nginx) │  リバースプロキシ
                        └──────┬──────┘
            ┌──────────────────┼──────────────────┐
            ▼                  ▼                  ▼
   ┌────────────────┐ ┌────────────────┐ ┌──────────────┐
   │ Next.js :3000  │ │ FastAPI :8000  │ │ Worker        │
   │ (Frontend)     │ │ (API+WS)       │ │ (SQS Consumer)│
   └────────────────┘ └───────┬────────┘ └──────┬───────┘
                               │                  │
                  ┌────────────┼──────────┐       │
                  ▼            ▼           ▼       ▼
            ┌──────────┐ ┌─────────┐ ┌──────┐ ┌──────────┐
            │   RDS    │ │  Redis  │ │  S3  │ │   SQS    │
            │PostgreSQL│ │ (Cache) │ │(画像)│ │(キュー)  │
            └──────────┘ └─────────┘ └──────┘ └──────────┘
```

---

## 3. 技術スタック

### Frontend
| 技術 | バージョン | 用途 |
|---|---|---|
| Next.js | 15 (App Router) | SSR/SSG・ルーティング |
| TypeScript | 5.7 | 型安全 |
| TailwindCSS | 3.4 | スタイリング |
| React Query | 5.62 | サーバー状態・キャッシュ |
| Zustand | 5.0 | 認証状態（persist + hydration制御） |
| React Hook Form | 7.54 | フォーム管理 |
| Zod | 3.23 | バリデーション |
| Recharts | 2.13 | グラフ描画 |
| Radix UI | - | アクセシブルUI |

### Backend
| 技術 | 用途 |
|---|---|
| FastAPI (Python 3.12) | REST API + WebSocket |
| SQLAlchemy (async) | 非同期ORM |
| Alembic | DBマイグレーション（001〜005） |
| Pydantic v2 | スキーマ検証 |
| asyncpg | PostgreSQL非同期ドライバ |
| python-jose | JWT認証 |
| structlog | 構造化ログ |
| boto3 | AWS連携（S3/SQS/EventBridge） |

### Infrastructure / DevOps
| 技術 | 用途 |
|---|---|
| AWS EC2 (t3.micro) | アプリサーバー |
| AWS RDS PostgreSQL 15 | メインDB |
| AWS CloudFront / S3 / SQS | CDN・ストレージ・キュー |
| Terraform | IaC（VPC/EC2/RDS/S3/SQS/IAM/CloudFront） |
| Docker Compose | コンテナオーケストレーション |
| GitHub Actions | CI/CD（Build & Push → Deploy） |
| GHCR | コンテナレジストリ |

---

## 4. 認証・認可設計

### 認証フロー
```
登録/ログイン → JWT発行（access 15min + refresh 7day）
            → localStorage保存（Zustand persist）
            → 401時に自動リフレッシュ → 失敗時ログイン画面へ
```

### ロール（RBAC）
| ロール | 権限 |
|---|---|
| `admin` | 全機能 + Admin Dashboard |
| `organizer` | 大会作成・管理・試合運営 |
| `player` | 大会参加・チーム所属・プロフィール |

### 重要な実装ポイント
- **Hydration制御**: Zustand `onRehydrateStorage` で localStorage 読込完了を待ち、新規タブでの誤ログアウトを防止
- **トークン自動更新**: `apiClient` が401検知→refresh→リトライを透過的に実行

---

## 5. データベース設計（主要テーブル）

### コアテーブル
| テーブル | 役割 |
|---|---|
| `users` | アカウント（email/role/auth） |
| `players` | プレイヤープロフィール（Riot ID/ランク/ロール） |
| `teams` | チーム（ロゴ/バナー/オーナー） |
| `team_members` | チームメンバー（ロール/背番号/soft delete） |
| `tournaments` | 大会（拡張済: tier/visibility/seeding他） |
| `tournament_registrations` | 参加申請（pending/approved/rejected） |
| `brackets` / `matches` | ブラケット・試合 |

### 大会拡張テーブル（正規化）
| テーブル | 役割 |
|---|---|
| `tournament_rules` | ゲーム別競技設定（JSONB） |
| `tournament_prizes` | 賞金配分 |
| `tournament_sponsors` | スポンサー |
| `tournament_streams` | 配信情報 |
| `tournament_discord` | Discord連携・通知設定 |
| `tournament_contacts` | 問い合わせ先 |
| `tournament_settings` | 分析設定 |

### 分析・競技データ
| テーブル | 役割 |
|---|---|
| `match_rounds` | ラウンド詳細（economy/win_condition） |
| `match_events` | キルフィード・タイムライン |
| `match_mvps` | MVP自動算出結果 |
| `match_summaries` | AI生成サマリー（枠） |
| `player_ratings` | Glicko-2レーティング |
| `player_rating_history` | レーティング履歴 |
| `player_achievements` / `team_achievements` | 実績 |
| `scout_profiles` | スカウト募集 |
| `platform_events` | ドメインイベントログ |

---

## 6. API設計（約10モジュール）

| プレフィックス | 主要エンドポイント |
|---|---|
| `/api/v1/auth` | register, login, refresh, me |
| `/api/v1/tournaments` | CRUD, mine, status変更, registrations承認/却下, bracket生成 |
| `/api/v1/matches` | get, listByTournament, start, score更新, result, banpick |
| `/api/v1/teams` | CRUD, members（追加/削除） |
| `/api/v1/players` | CRUD, me, roles |
| `/api/v1/analytics` | maps, agents, winrate, trend, rankings, players, heatmap |
| `/api/v1/admin` | dashboard, notifications |
| `/api/v1/scout` | players検索, teams検索, ratings |
| `/api/v1/upload` | image（S3アップロード） |
| `/ws/matches/{id}` | WebSocketリアルタイム更新 |

---

## 7. フロントエンド画面構成

### 公開ページ `(public)`
| URL | 機能 |
|---|---|
| `/` | トップページ |
| `/tournaments` | 大会一覧（検索/フィルター/ページネーション） |
| `/tournaments/[id]` | 大会詳細（Overview/Matches/Bracket/Standings/Analytics） |
| `/tournaments/[id]/bracket` | ブラケット（ズーム/SE・DE対応） |
| `/teams/[id]` | チーム詳細（Overview/Players/Matches/Analytics） |
| `/players/[id]` | プレイヤー詳細（KDA推移/勝率/Agent利用率） |
| `/matches/[id]` | Match Center（7タブ・WebSocket・MVP） |
| `/scout` | スカウト（プレイヤー/チーム検索） |
| `/login` `/register` | 認証（参加者/主催者選択） |

### 認証ページ `(auth)`
| URL | 機能 | 権限 |
|---|---|---|
| `/dashboard` | 主催者ダッシュボード（KPI・大会管理） | organizer |
| `/organizer/tournaments/create` | 12セクション大会作成（Autosave） | organizer |
| `/organizer/tournaments/[id]` | 大会管理（申請承認/ブラケット/削除） | organizer |
| `/analytics` | BIダッシュボード | 全認証 |
| `/admin` | Admin Dashboard（MAU/DAU/成長率） | admin |
| `/admin/matches/[id]` | 試合管理（スコア入力/Ban Pick/WS） | organizer |
| `/teams/create` | チーム作成（画像アップロード） | 全認証 |
| `/teams/[id]/edit` `/members` | チーム編集・メンバー管理 | owner |
| `/players/create` | プレイヤー登録 | 全認証 |

---

## 8. リアルタイム機能（WebSocket）

```
試合管理画面 ──スコア更新──▶ FastAPI WS ──broadcast──▶ 観戦者全員
                                  │
                            Redis Pub/Sub（複数インスタンス対応）

クライアント側: 401→自動リフレッシュ / 切断→3秒後自動再接続
```

---

## 9. 分析機能

### 算出ロジック
- **ACS**: スコア / ラウンド数（VALORANT準拠）
- **MVP**: ACS(35%) + KDA(25%) + FB率(20%) + 勝利貢献(20%)
- **レーティング**: Glicko-2（rating/deviation/volatility）

### 可視化（Recharts）
- KDA推移（ComposedChart）・勝率推移（AreaChart）
- Agent利用率（PieChart）・MAP×Agentヒートマップ
- 月別成績（BarChart）・成長率分析

---

## 10. CI/CDパイプライン

```
git push (main)
   │
   ▼
GitHub Actions: Build & Push
   ├── api / worker / frontend を並列ビルド
   ├── GHCR へpush（latest + sha-xxxxx）
   │
   ▼
Deploy — Demo (EC2)
   └── SSH → docker compose pull → up -d → alembic upgrade head
```

---

## 11. 既知の課題・今後の実装予定

### 既知の課題
- `/health` エンドポイントがNginx設定で404（実害なし）
- EC2再起動時にコンテナDNSキャッシュ問題（Nginx変数proxy_passで対応済み）
- 手動デプロイ運用（GitHub Secrets未設定のため自動SSH不可）

### 未実装（設計のみ）
- Discord Bot（サーバーテンプレート自動生成・/コマンド）
- AI Match Summary（OpenAI連携の枠のみ）
- 大会進行自動化（試合終了→次試合自動生成）
- EKS本番移行（Helm chart雛形あり）
- EventBridge完全非同期化（EventBus実装済、配線は途中）

---

## 12. ディレクトリ構成

```
esports-platform/
├── backend/
│   ├── app/
│   │   ├── api/v1/        # auth, tournaments, matches, teams,
│   │   │                  # players, analytics, admin, scout, upload
│   │   ├── models/        # SQLAlchemy ORM
│   │   ├── schemas/       # Pydantic
│   │   ├── services/      # ビジネスロジック
│   │   ├── repositories/  # データアクセス
│   │   ├── core/          # config, security, events, redis, deps
│   │   └── workers/       # SQS consumer
│   └── alembic/versions/  # 001〜005 マイグレーション
├── frontend/
│   └── src/
│       ├── app/
│       │   ├── (public)/  # 未認証アクセス可
│       │   └── (auth)/    # 認証必須
│       ├── features/      # 機能別（tournaments, teams, players, matches, analytics）
│       ├── components/    # 共通UI
│       ├── lib/           # api-client, utils
│       ├── store/         # Zustand
│       └── types/         # 型定義
├── infrastructure/
│   ├── terraform/         # VPC/EC2/RDS/S3/SQS/IAM/CloudFront
│   └── helm/              # K8s（本番用雛形）
└── docs/architecture/     # 設計ドキュメント
```
```
```
