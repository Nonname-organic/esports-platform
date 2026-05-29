# Phase 3: Backend設計（FastAPI）

---

## 1. ディレクトリ構成

```
backend/
├── app/
│   ├── main.py                   # FastAPI エントリポイント
│   ├── core/
│   │   ├── config.py             # 設定（pydantic-settings）
│   │   ├── security.py           # JWT / パスワードハッシュ
│   │   ├── database.py           # 非同期SQLAlchemyセッション
│   │   ├── redis.py              # Redisクライアント
│   │   ├── dependencies.py       # FastAPI DI（認証・DB・Redis）
│   │   └── exceptions.py         # カスタム例外
│   ├── models/                   # Phase 2 で作成済み
│   ├── schemas/
│   │   ├── common.py             # 共通レスポンス形式
│   │   ├── auth.py               # 認証スキーマ
│   │   ├── tournament.py         # 大会スキーマ
│   │   ├── match.py              # 試合スキーマ
│   │   └── analytics.py          # 分析スキーマ
│   ├── repositories/             # DB操作の抽象化
│   │   ├── base.py               # 汎用CRUDリポジトリ
│   │   ├── tournament.py
│   │   ├── match.py
│   │   └── analytics.py
│   ├── services/                 # ビジネスロジック
│   │   ├── auth.py
│   │   ├── tournament.py
│   │   ├── match.py
│   │   ├── ranking.py
│   │   └── analytics.py
│   ├── api/
│   │   ├── v1/
│   │   │   ├── router.py         # v1 ルート集約
│   │   │   ├── auth.py
│   │   │   ├── tournaments.py
│   │   │   ├── matches.py
│   │   │   ├── rankings.py
│   │   │   └── analytics.py
│   │   └── ws/
│   │       └── match.py          # WebSocket
│   ├── workers/
│   │   ├── sqs_consumer.py       # SQS コンシューマー
│   │   └── handlers/
│   │       ├── match_result.py
│   │       └── notification.py
│   └── middleware/
│       ├── audit_log.py
│       └── rate_limit.py
├── tests/
│   ├── conftest.py
│   ├── api/
│   └── services/
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

## 2. Clean Architecture 適用方針

```
[API Layer]        HTTP/WebSocket エンドポイント・認証・バリデーション
      ↓ DI
[Service Layer]    ビジネスロジック・トランザクション管理
      ↓
[Repository Layer] DB操作の抽象化（SQLAlchemy）
      ↓
[Model Layer]      SQLAlchemy モデル（Phase 2）
```

**原則:**
- Service はRepositoryに依存する（逆は禁止）
- APIエンドポイントはServiceに依存する（Repository直接呼び出し禁止）
- Schema（Pydantic）はLayerをまたいで使用可

---

## 3. API 一覧

### 認証
| Method | Path | 説明 |
|--------|------|------|
| POST | `/api/v1/auth/register` | ユーザー登録 |
| POST | `/api/v1/auth/login` | ログイン（JWT発行） |
| POST | `/api/v1/auth/refresh` | トークンリフレッシュ |
| POST | `/api/v1/auth/logout` | ログアウト（Refresh無効化） |
| GET | `/api/v1/auth/me` | 現在のユーザー情報 |

### 大会管理
| Method | Path | 説明 |
|--------|------|------|
| GET | `/api/v1/tournaments` | 大会一覧（カーソルページネーション） |
| POST | `/api/v1/tournaments` | 大会作成 |
| GET | `/api/v1/tournaments/{id}` | 大会詳細 |
| PATCH | `/api/v1/tournaments/{id}` | 大会更新 |
| DELETE | `/api/v1/tournaments/{id}` | 大会削除 |
| POST | `/api/v1/tournaments/{id}/register` | 参加申請 |
| POST | `/api/v1/tournaments/{id}/bracket` | ブラケット生成 |
| GET | `/api/v1/tournaments/{id}/bracket` | ブラケット取得 |

### 試合管理
| Method | Path | 説明 |
|--------|------|------|
| GET | `/api/v1/matches/{id}` | 試合詳細 |
| PATCH | `/api/v1/matches/{id}/start` | 試合開始 |
| POST | `/api/v1/matches/{id}/result` | 試合結果登録 |
| POST | `/api/v1/matches/{id}/games/{num}/score` | ゲームスコア更新 |
| POST | `/api/v1/matches/{id}/banpick` | Ban/Pick登録 |

### ランキング
| Method | Path | 説明 |
|--------|------|------|
| GET | `/api/v1/rankings` | グローバルランキング |
| GET | `/api/v1/rankings/tournaments/{id}` | 大会別ランキング |

### 分析
| Method | Path | 説明 |
|--------|------|------|
| GET | `/api/v1/analytics/players/{id}/stats` | 選手統計 |
| GET | `/api/v1/analytics/teams/{id}/stats` | チーム統計 |
| GET | `/api/v1/analytics/maps/stats` | マップ統計 |
| GET | `/api/v1/analytics/compositions` | 構成分析 |
| GET | `/api/v1/analytics/tournaments/{id}/summary` | 大会サマリー |

### WebSocket
| Path | 説明 |
|------|------|
| `WS /ws/matches/{id}` | 試合リアルタイム更新 |
| `WS /ws/brackets/{tournament_id}` | ブラケット更新 |

---

## 4. レスポンス形式統一

```json
// 成功（単一）
{ "data": { ... }, "meta": null }

// 成功（リスト）
{ "data": [...], "meta": { "total": 100, "cursor": "xxx", "has_next": true } }

// エラー（RFC 7807）
{ "type": "validation_error", "title": "入力値エラー", "status": 422, "detail": "...", "errors": [...] }
```

---

## 5. RBAC 権限マトリクス

| エンドポイント | admin | organizer | team_manager | player | viewer |
|-------------|-------|-----------|-------------|--------|--------|
| 大会作成 | ✅ | ✅ | ❌ | ❌ | ❌ |
| 大会更新 | ✅ | 自分のみ | ❌ | ❌ | ❌ |
| 試合結果登録 | ✅ | 自分大会 | ❌ | ❌ | ❌ |
| ランキング閲覧 | ✅ | ✅ | ✅ | ✅ | ✅ |
| 分析閲覧 | ✅ | ✅ | ✅ | ✅ | ✅ |
| チーム登録 | ✅ | ❌ | 自分のみ | ❌ | ❌ |

---

## 6. WebSocket プロトコル

```json
// クライアント → サーバー
{ "type": "subscribe", "match_id": "uuid" }
{ "type": "ping" }

// サーバー → クライアント
{ "type": "score_update", "data": { "game_number": 1, "team1_score": 8, "team2_score": 4 } }
{ "type": "match_complete", "data": { "winner_id": "uuid", "score": "2-1" } }
{ "type": "bracket_update", "data": { "next_match_id": "uuid" } }
{ "type": "pong" }
```

---

*このドキュメントはPhase 3の設計を定義します。実装コードは backend/ ディレクトリにあります。*
