# Feature Expansion Design — Tournament OS 拡張設計

対象機能: ①監査ログ ②Player最近の活動 ③通知設定 ④グローバル検索 ⑤タグ ⑥Team実績カード ⑦Teamスポンサー ⑧Tournamentルール ⑨運営ダッシュボード ⑩終了レポート

設計原則: 既存アーキテクチャ（FastAPI + SQLAlchemy async + Alembic + Pydantic / Next.js App Router + TanStack Query + Zustand）を維持。破壊的DB変更禁止・後方互換・N+1回避・非同期・ゲーム非依存・Riot非依存・JSONBによる拡張余地確保。

---

## 1. 全体アーキテクチャ

### 設計方針（3つの横断コンセプト）
既存の `Repository → Service → Router` 3層を踏襲し、10機能を**3つの再利用可能な基盤**に集約する。個別機能の寄せ集めにしない。

1. **Event基盤（Audit / Activity / Ops Timeline を統一）**
   `domain_events` を単一の追記専用テーブルとし、監査ログ(①)・Player活動(②)・運営タイムライン(⑨)を「同じイベントの異なるビュー」として実装する。`action` は文字列（enum化しない）で拡張自由。書き込みは `EventService.emit()` の1経路に集約。

2. **Preference / Config基盤（通知設定③）**
   JSONBで「種別 × チャネル」を保持し、種別追加時にマイグレーション不要にする。

3. **Taggable / Polymorphic基盤（タグ⑤・スポンサー⑦・レポート⑩・ルール⑧）**
   ポリモーフィックな関連（`entity_type` + `entity_id`）と JSONB ドキュメントで、Team/Tournament/LFP/LFT 横断の付加情報を後方互換に追加する。

```
┌──────────── Frontend (Next.js App Router) ────────────┐
│ features/{audit,activity,search,tags,ops,report,...}   │
│   api/*.ts (fetch)  hooks/*.ts (TanStack Query)        │
│ components/global-search.tsx (Header)                  │
│ store/search-store.ts (Zustand: 検索履歴/最近見た項目) │
└───────────────────────┬────────────────────────────────┘
                        │ REST (/api/v1/*)
┌───────────────────────┴────────────────────────────────┐
│ FastAPI Router → Service → Repository → SQLAlchemy      │
│  EventService / PreferenceService / SearchService /     │
│  TagService / OpsService / ReportService                │
│  既存: TournamentService, TeamService, NotificationSvc  │
├─────────────────────────────────────────────────────────┤
│ PostgreSQL (pg_trgm/GIN, JSONB, 追記ログ) + Redis(cache)│
└─────────────────────────────────────────────────────────┘
```

### 責務分離の原則
- **書き込み経路の一本化**: 監査・活動・運営イベントはドメインService内から `EventService.emit(...)` を呼ぶだけ。各Serviceに散らばらせない。
- **読み取り最適化**: 集計（Team実績⑥・レポート⑩）はRedisキャッシュ + 事前集計。検索④は pg_trgm GIN インデックス。
- **拡張点は文字列 + JSONB**: 新イベント種別・新通知種別・新タグ・新レポート項目は**コード追加のみ**（マイグレーション不要）。

---

## 2. DB設計

新規テーブル（すべて追加のみ・既存テーブル変更は「NULL許容カラム追加」のみ）。

### ① 監査ログ + ⑨ 運営タイムライン + ② Player活動 → `domain_events`（統合）
```
domain_events
  id            UUID PK
  actor_id      UUID FK users NULL         -- system イベントは NULL
  actor_ip      INET NULL                  -- 取得可能なら
  source        VARCHAR(16) NOT NULL       -- system | user | staff
  entity_type   VARCHAR(32) NOT NULL       -- team | tournament | match | registration | player ...
  entity_id     UUID NOT NULL
  action        VARCHAR(64) NOT NULL       -- team.member_added, tournament.published ... (拡張自由)
  summary       TEXT NULL                  -- 人間可読な要約
  before        JSONB NULL                 -- 変更前
  after         JSONB NULL                 -- 変更後
  extra_data    JSONB NULL                 -- 表示用の付随情報（player活動のタイトル等）
  visibility    VARCHAR(16) NOT NULL DEFAULT 'internal'  -- internal(監査) | public(活動/公開タイムライン)
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
  INDEX (entity_type, entity_id, created_at DESC)
  INDEX (actor_id, created_at DESC)
  INDEX (visibility, action)              -- Player活動の絞り込み用
```
> **1テーブルに統合する理由**: 監査(①)・活動(②)・運営タイムライン(⑨) は「誰が・いつ・何をしたか」で本質同型。`visibility` と `entity_type` でビューを分ける。ログ量が問題化したら BRIN インデックス + パーティション（月次）へ無停止移行可能。

### ③ 通知設定 → `notification_preferences`
```
notification_preferences
  user_id   UUID PK FK users
  prefs     JSONB NOT NULL DEFAULT '{}'    -- { "channels": {...}, "categories": {...} }
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
```
prefs 構造（種別追加でマイグレーション不要）:
```json
{
  "channels":   { "email": true, "browser": true, "discord": false },
  "categories": { "tournament": true, "scout": true, "team": true, "match": true }
}
```
未設定キー = デフォルトON（後方互換）。

### ④ グローバル検索 → インデックスのみ（+任意で履歴テーブル）
```
-- pg_trgm 拡張 + GIN インデックス（既存テーブルにインデックス追加のみ）
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX ix_teams_name_trgm        ON teams        USING gin (name gin_trgm_ops);
CREATE INDEX ix_players_ign_trgm       ON players      USING gin (in_game_name gin_trgm_ops);
CREATE INDEX ix_tournaments_name_trgm  ON tournaments  USING gin (name gin_trgm_ops);
-- 検索履歴（任意・クロスデバイス用。初期はクライアントZustandで十分）
search_history(id UUID PK, user_id UUID FK, query VARCHAR(200), created_at TIMESTAMPTZ)
```

### ⑤ タグ → `tags` + `taggables`（ポリモーフィック）
```
tags
  id        UUID PK
  slug      VARCHAR(50) UNIQUE NOT NULL   -- beginner, premier, online ...
  label     VARCHAR(50) NOT NULL
  category  VARCHAR(30) NULL              -- skill | event | region ...
  color     VARCHAR(20) NULL
  created_at TIMESTAMPTZ

taggables
  tag_id      UUID FK tags
  entity_type VARCHAR(32) NOT NULL        -- team | tournament | lfp | lft
  entity_id   UUID NOT NULL
  PRIMARY KEY (tag_id, entity_type, entity_id)
  INDEX (entity_type, entity_id)
  INDEX (tag_id, entity_type)             -- タグ検索
```

### ⑥ Team実績 → 集計（テーブル追加なし・Redisキャッシュ + 任意で materialized）
既存 `CareerAggregationService.get_team_career` を拡張。永続化が必要なら:
```
team_achievement_cache(team_id UUID PK, data JSONB, computed_at TIMESTAMPTZ)  -- 任意
```

### ⑦ Teamスポンサー → `team_sponsors`
```
team_sponsors
  id            UUID PK
  team_id       UUID FK teams
  name          VARCHAR(100) NOT NULL
  logo_url      TEXT NULL
  url           TEXT NULL
  sponsor_type  VARCHAR(30) NULL          -- title | gold | partner ... (拡張自由)
  display_order INT NOT NULL DEFAULT 0
  contract_start DATE NULL                -- 将来: 契約期間
  contract_end   DATE NULL
  created_at / updated_at TIMESTAMPTZ
  INDEX (team_id, display_order)
```

### ⑧ Tournamentルール → 既存 `tournaments` にカラム追加（NULL許容）
```
ALTER TABLE tournaments ADD COLUMN rules_doc JSONB NULL;
-- rules_doc = { "sections": [ {"key":"general","title":"大会ルール","body_md":"...","order":0}, ... ] }
```
> 既存 `rules`(JSONB, bo_format等の設定) とは別カラム。セクションは配列なので種別追加自由。Markdown本文は `body_md`。

### ⑩ 終了レポート → `tournament_reports`
```
tournament_reports
  id            UUID PK
  tournament_id UUID UNIQUE FK tournaments
  data          JSONB NOT NULL            -- 集計結果（下記全項目）
  markdown      TEXT NULL                 -- レンダリング済みMD（PDF化の元）
  version       INT NOT NULL DEFAULT 1
  generated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
```

### ⑨ 運営タスク（Todo）→ `tournament_ops_tasks`（タイムラインは domain_events を流用）
```
tournament_ops_tasks
  id            UUID PK
  tournament_id UUID FK tournaments
  title         VARCHAR(200) NOT NULL
  is_done       BOOLEAN NOT NULL DEFAULT false
  assignee_id   UUID FK users NULL
  display_order INT NOT NULL DEFAULT 0
  created_by    UUID FK users
  created_at / updated_at TIMESTAMPTZ
  INDEX (tournament_id, is_done, display_order)

ops_templates (将来のテンプレート化)
  id UUID PK, name VARCHAR(100), tasks JSONB, created_by UUID, created_at
```

---

## 3. Alembic追加内容

連番 016〜（現在 015 まで）。破壊的変更なし・すべて `add_column` / `create_table` / `create_index`。

| Rev | 内容 | ダウングレード |
|-----|------|----------------|
| 016 | `domain_events` テーブル + インデックス | drop_table |
| 017 | `notification_preferences` テーブル | drop_table |
| 018 | pg_trgm 拡張 + GIN インデックス3種 + `search_history` | drop index/table（拡張は保持可） |
| 019 | `tags` + `taggables` テーブル | drop_table |
| 020 | `team_sponsors` テーブル | drop_table |
| 021 | `tournaments.rules_doc` カラム追加（NULL） | drop_column |
| 022 | `tournament_reports` テーブル | drop_table |
| 023 | `tournament_ops_tasks` + `ops_templates` | drop_table |

各 migration の `server_default` を付け、既存行に安全に適用（NOT NULL 追加時は default 必須 = 015 の `status_locked` と同パターン）。GIN インデックスは `CREATE INDEX CONCURRENTLY` を検討（Alembic では `op.execute` + `autocommit_block`）で本番無停止。

---

## 4. SQLAlchemyモデル（既存パターン準拠: UUIDMixin/TimestampMixin/pg_enum/JSONB）

```python
# app/models/event.py
class DomainEvent(UUIDMixin, Base):
    __tablename__ = "domain_events"
    actor_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    actor_ip: Mapped[Optional[str]] = mapped_column(INET, nullable=True)
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="user")
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    before: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    after: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    extra_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    visibility: Mapped[str] = mapped_column(String(16), nullable=False, default="internal")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

# app/models/notification_pref.py
class NotificationPreference(Base):
    __tablename__ = "notification_preferences"
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    prefs: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

# app/models/tag.py
class Tag(UUIDMixin, Base):
    __tablename__ = "tags"
    slug: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    label: Mapped[str] = mapped_column(String(50), nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    color: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class Taggable(Base):
    __tablename__ = "taggables"
    tag_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(32), primary_key=True)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)

# app/models/team_sponsor.py  (UUIDMixin + TimestampMixin)
class TeamSponsor(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "team_sponsors"
    team_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    logo_url / url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sponsor_type: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    contract_start / contract_end: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

# app/models/tournament_report.py, tournament_ops.py も同様（UUIDMixin/TimestampMixin）
# tournaments.rules_doc は Tournament モデルに JSONB カラム追加（Optional）
```
> モデルは `app/models/__init__.py` に登録し、Alembic autogenerate と mapper 解決に載せる（既存 team_recruitment/player_lft と同様）。

---

## 5. Pydantic（スキーマ）

`Response[T]` / `ListResponse[T]` / `Meta` の既存ラッパを踏襲。代表例:

```python
# 監査ログ
class AuditLogItem(BaseModel):
    id: str; actor_id: str | None; actor_name: str | None; actor_ip: str | None
    action: str; summary: str | None
    before: dict | None; after: dict | None
    created_at: datetime
    model_config = {"from_attributes": True}

# Player活動（②）
class ActivityItem(BaseModel):
    id: str; type: str; title: str; extra_data: dict | None; occurred_at: datetime

# 通知設定（③）
class NotificationPrefs(BaseModel):
    channels: dict[str, bool] = {}
    categories: dict[str, bool] = {}
class NotificationPrefsUpdate(BaseModel):        # 部分更新
    channels: dict[str, bool] | None = None
    categories: dict[str, bool] | None = None

# 検索（④）
class SearchResults(BaseModel):
    players: list[SearchHit]; teams: list[SearchHit]
    tournaments: list[SearchHit]; matches: list[SearchHit]
class SearchHit(BaseModel):
    id: str; label: str; sub: str | None; image_url: str | None; url: str

# タグ（⑤）
class TagItem(BaseModel): id: str; slug: str; label: str; category: str | None; color: str | None
class TagAssignRequest(BaseModel): tag_slugs: list[str]  # まとめて付与

# スポンサー（⑦）
class SponsorCreate(BaseModel):
    name: str = Field(..., max_length=100); logo_url: str | None = None
    url: str | None = None; sponsor_type: str | None = None
    display_order: int = 0; contract_start: date | None = None; contract_end: date | None = None

# ルール（⑧）
class RulesSection(BaseModel):
    key: str; title: str; body_md: str = Field(..., max_length=20000); order: int = 0
class RulesDoc(BaseModel): sections: list[RulesSection]

# レポート（⑩）
class TournamentReport(BaseModel):
    tournament_id: str; data: dict; markdown: str | None; generated_at: datetime
```
バリデーション: `max_length`, Markdown本文の上限、`sponsor_type` は自由文字列（enum化しない=拡張性）。

---

## 6. API設計

REST・`/api/v1` プレフィックス・`Response`/`ListResponse` を返す既存規約。

```
# ① 監査ログ（管理画面/オーナー閲覧）
GET  /api/v1/audit?entity_type=&entity_id=&action=&actor_id=&cursor=&limit=
GET  /api/v1/teams/{id}/audit            # 対象別ショートカット
GET  /api/v1/tournaments/{id}/audit

# ② Player活動
GET  /api/v1/players/{id}/activity?cursor=&limit=

# ③ 通知設定
GET   /api/v1/notifications/preferences
PATCH /api/v1/notifications/preferences   # 部分更新（channels/categories）

# ④ グローバル検索
GET  /api/v1/search?q=&limit=8&types=players,teams,tournaments,matches
POST /api/v1/search/history               # 任意（クロスデバイス履歴）
GET  /api/v1/search/history

# ⑤ タグ
GET    /api/v1/tags?category=&q=          # タグカタログ（autocomplete）
PUT    /api/v1/{entity_type}/{id}/tags    # まとめて付与/差し替え（team|tournament|lfp|lft）
GET    /api/v1/tags/{slug}/entities?type= # タグ検索（横断）

# ⑥ Team実績
GET  /api/v1/teams/{id}/achievements

# ⑦ Teamスポンサー
GET    /api/v1/teams/{id}/sponsors
POST   /api/v1/teams/{id}/sponsors
PATCH  /api/v1/teams/{id}/sponsors/{sid}
DELETE /api/v1/teams/{id}/sponsors/{sid}
PATCH  /api/v1/teams/{id}/sponsors/reorder   # 表示順一括更新

# ⑧ Tournamentルール
GET   /api/v1/tournaments/{id}/rules
PUT   /api/v1/tournaments/{id}/rules       # RulesDoc 全体更新

# ⑨ 運営ダッシュボード
GET    /api/v1/tournaments/{id}/ops/summary   # 未承認/チェックイン/未報告/Discord/今日のタスク
GET    /api/v1/tournaments/{id}/ops/tasks
POST   /api/v1/tournaments/{id}/ops/tasks
PATCH  /api/v1/tournaments/{id}/ops/tasks/{tid}
DELETE /api/v1/tournaments/{id}/ops/tasks/{tid}
GET    /api/v1/tournaments/{id}/ops/timeline  # domain_events(system+staff) 統合
POST   /api/v1/tournaments/{id}/ops/timeline  # 運営イベント手動追加

# ⑩ 終了レポート
GET  /api/v1/tournaments/{id}/report          # 無ければ 404（未生成）
POST /api/v1/tournaments/{id}/report/generate # 手動再生成（自動は status→completed で発火）
```
ページングは既存のカーソル方式（`Meta.cursor` / `has_next`）を踏襲。

---

## 7. Router一覧

`app/api/v1/router.py` に追加（既存 include_router パターン）:
```python
api_router.include_router(audit.router)          # /audit, teams/tournaments配下は既存routerに委譲
api_router.include_router(search.router)         # /search
api_router.include_router(tags.router)           # /tags
# 既存routerに endpoint 追加:
#  players.py  += /players/{id}/activity
#  teams.py    += /teams/{id}/{audit,achievements,sponsors,tags}
#  tournaments.py += /tournaments/{id}/{audit,rules,ops/*,report}
#  notifications.py += /notifications/preferences
```
> 対象エンティティ配下（teams/tournaments/players）は**既存routerに endpoint 追加**して凝集度を保つ。横断機能（audit一覧/search/tags）のみ新router。

---

## 8. Service設計

新規Service（薄く・単一責務）:

| Service | 責務 |
|---|---|
| `EventService` | `emit(actor, ip, entity_type, entity_id, action, before, after, visibility)` の1メソッド。監査①・活動②・運営タイムライン⑨の唯一の書き込み口。`query(filters)` で読み取り。 |
| `PreferenceService` | 取得（デフォルトマージ）・部分更新。`is_enabled(user_id, category, channel)` を通知送信側へ提供。 |
| `SearchService` | 各エンティティを `asyncio.gather` で並列検索（pg_trgm similarity 上位N）。結果を SearchResults に整形。 |
| `TagService` | カタログ取得・付与(差分)・タグ検索。存在しない slug は自動作成 or 拒否（設定）。 |
| `TeamAchievementService` | 既存 `CareerAggregationService` を利用しつつ賞金・順位分布を集計。Redisキャッシュ（TTL 10分）。 |
| `SponsorService` | CRUD + reorder。owner/captain権限。 |
| `TournamentRulesService` | RulesDoc の取得/更新（tournaments.rules_doc）。 |
| `OpsService` | ops/summary 集計（既存 registration/checkin/match を横断read）、tasks CRUD、timeline(=EventService.query)。 |
| `ReportService` | `generate(tournament_id)`: matches/results/analytics から集計→`tournament_reports` upsert。status→completed で自動発火。 |

**既存Serviceへの差し込み**（監査・活動・運営イベント）:
```python
# 例: TournamentService.change_status 内（既に実装済みの箇所）
await self._events.emit(
    actor=current_user, ip=ctx.ip,
    entity_type="tournament", entity_id=tournament.id,
    action="tournament.status_changed",
    before={"status": old.value}, after={"status": new_status.value},
    visibility="internal",
)
```
IP は Router層で `Request` から抽出し `ctx`（依存性）で Service へ渡す（CloudFront→nginx 経由のため `X-Forwarded-For` 先頭を採用）。

---

## 9. Repository設計

既存 `BaseRepository[Model]` を継承。N+1回避を最優先。

- `EventRepository`: `list(filters, cursor, limit)` — `selectinload(DomainEvent.actor)` で actor をまとめて取得（N+1回避）。追記は単純 add。
- `SearchRepository`: エンティティごとに `similarity(name, :q) > 0.2 ORDER BY similarity DESC LIMIT n`（pg_trgm）。JOINで image/sub情報を1クエリに含める。
- `TagRepository`: `list_by_entity(type, ids[])` を**IN句 + 一括取得**して付与情報をまとめる（一覧画面のN+1防止）。
- `SponsorRepository`: `list_by_team(team_id) ORDER BY display_order`。
- `OpsTaskRepository`: `list_by_tournament`.
- `TournamentReportRepository`: `get_by_tournament`, `upsert`.

一覧系（大会一覧・チーム一覧）でタグを出す場合は、**親IDリストを集めて `taggables` を1クエリで取得しメモリ結合**（Data Loaderパターン）。

---

## 10. Frontend構成

```
features/
  audit/       api/audit-api.ts        hooks/use-audit.ts
  activity/    api/activity-api.ts     hooks/use-activity.ts
  search/      api/search-api.ts       hooks/use-search.ts
  tags/        api/tag-api.ts          hooks/use-tags.ts
  sponsors/    api/sponsor-api.ts      hooks/use-sponsors.ts
  ops/         api/ops-api.ts          hooks/use-ops.ts
  report/      api/report-api.ts       hooks/use-report.ts
  notifications/  (既存に preferences 追加)

components/
  global-search.tsx            # ヘッダー検索（Autocomplete/カテゴリ/最近見た）
  tag-input.tsx / tag-badge.tsx
  markdown.tsx                 # react-markdown ラッパ（⑧⑩共通）

app/(auth)/
  settings/notifications/page.tsx       # ③ 通知設定
  organizer/tournaments/[id]/ops/page.tsx  # ⑨ 運営ダッシュボード
  admin/audit/page.tsx                  # ① 監査ログ閲覧（Admin）

app/(auth)/players/[id]/_components/PlayerActivity.tsx   # ② 活動タブ
app/(public)/teams/[id]/_components/{achievements,sponsors,tags}-*.tsx  # ⑥⑦⑤
app/(auth)/tournaments/[id]/_components/rules-tab.tsx    # ⑧
app/(auth)/tournaments/[id]/_components/report-tab.tsx   # ⑩
```
Markdown表示は `react-markdown + remark-gfm`（新規依存・軽量）。既存の shadcn/Tailwind カードUIを流用。

---

## 11. Zustand追加内容

グローバル検索の「検索履歴」「最近見た項目」はサーバー不要のクライアント状態として `search-store`（既存 `auth-store` と同じ persist パターン）:
```ts
interface SearchState {
  recentQueries: string[];              // 最大10件
  recentlyViewed: { type: string; id: string; label: string; url: string }[]; // 最大10件
  addQuery(q: string): void;
  addViewed(item): void;
  clear(): void;
}
// persist({ name: "esports-search", partialize: recentQueries/recentlyViewed })
```
`recentlyViewed` は各詳細ページ表示時に `addViewed()` を呼ぶ。サーバー履歴（任意）は将来クロスデバイス同期時に併用。

---

## 12. TanStack Query設計

キー設計は既存 `xxxKeys` ファクトリ準拠。キャッシュ時間は用途別。

| Hook | queryKey | staleTime | 備考 |
|---|---|---|---|
| `useGlobalSearch(q)` | `["search", q]` | 30s | `enabled: q.length>=2`、`placeholderData: keepPreviousData`、300msデバウンス |
| `useAudit(filters)` | `["audit", filters]` | 60s | カーソルページング |
| `usePlayerActivity(id)` | `["activity", id]` | 60s | infinite query |
| `useNotificationPrefs()` | `["notif-prefs"]` | 5m | PATCHで楽観更新 |
| `useTeamAchievements(id)` | `["team", id, "achievements"]` | 5m | サーバー側もRedisキャッシュ |
| `useTags(category)` | `["tags", category]` | 10m | autocomplete |
| `useSponsors(teamId)` | `["team", teamId, "sponsors"]` | 5m | mutation後 invalidate |
| `useOpsSummary(id)` | `["ops", id, "summary"]` | 20s | `refetchInterval: 30s`（運営中の即時性） |
| `useReport(id)` | `["report", id]` | ∞ | 生成済みは不変 |

mutation は `onSuccess` で対象キー invalidate（既存パターン）。

---

## 13. UI一覧

| # | 画面/コンポーネント | 主な要素 |
|---|---|---|
| ① | Admin監査ログ / Team・Tournament設定内の履歴タブ | フィルタ(対象/操作/実行者/期間)、before→after差分表示、IP |
| ② | Playerプロフィール「活動」タブ | タイムライン（アイコン+タイトル+日時）、無限スクロール |
| ③ | 設定 > 通知設定 | チャネルToggle群 + 種別Toggle群、保存で楽観更新 |
| ④ | ヘッダー グローバル検索 | デバウンスAutocomplete、カテゴリ見出し、検索履歴/最近見た項目、⌘K |
| ⑤ | タグ入力/バッジ | Team/Tournament/LFP/LFT 編集画面に TagInput、一覧にバッジ、タグ検索 |
| ⑥ | Team実績カード | 優勝/準優勝/TOP4/TOP8/出場数/勝率/賞金 のカードグリッド |
| ⑦ | Teamスポンサー欄 | ロゴ+名前+リンク、種別、並び替え（オーナー編集） |
| ⑧ | Tournamentルールタブ | セクション別Markdown表示、編集はMarkdownエディタ |
| ⑨ | 運営ダッシュボード | サマリーカード(未承認/チェックイン/未報告/Discord/今日の作業) + Todoリスト + タイムライン(system/staff) |
| ⑩ | 終了レポートタブ | サマリー、優勝/準優勝/MVP、人気Agent/Map、ベストマッチ、Markdown/将来PDF出力ボタン |

---

## 14. 権限制御

既存 `CurrentUser` / `OrganizerUser` 依存性 + ロール/所有チェックを踏襲。

| 機能 | 閲覧 | 変更 |
|---|---|---|
| ① 監査(team/tournament) | Admin + 当該オーナー | 記録は自動（人間不可） |
| ① 監査(全体) | Admin のみ | — |
| ② Player活動 | 公開（visibility=public のみ） | 自動生成 |
| ③ 通知設定 | 本人 | 本人 |
| ④ 検索 | 全員（公開エンティティのみ結果に含む） | — |
| ⑤ タグ付与 | 全員閲覧 | Team=owner/captain, Tournament=organizer, LFP/LFT=作成者 |
| ⑥ 実績 | 公開 | 自動集計 |
| ⑦ スポンサー | 公開 | Team owner/captain |
| ⑧ ルール | 公開 | organizer |
| ⑨ 運営ダッシュボード | organizer/admin | organizer/admin |
| ⑩ レポート | 公開 | 生成=organizer/自動 |

監査ログの**IP/before/after は internal 可視性**とし、公開タイムライン(②)には露出しない（`visibility` で分離）。

---

## 15. バリデーション

- Pydantic `Field(max_length=...)`：ルール本文20,000字、スポンサー名100字、タグslug 50字。
- タグ slug は `^[a-z0-9-]+$`（正規化）。表示ラベルは自由。
- 通知設定は既知キーのみ許容（未知キーは無視）でスキーマ汚染防止。
- スポンサー `display_order` は 0..N、reorder は所属teamの全件整合を検証。
- ルールセクション `key` の重複禁止。
- レポート生成は `status == completed` を前提（それ以外は 409）。
- 検索 `q` は 2文字以上・上限長で DoS 抑制。

---

## 16. 通知連携

③の設定は**通知送信の分岐点**として機能。既存 `NotificationService` に `PreferenceService` を差し込む:
```python
async def dispatch(user_id, category, notif_type, payload):
    prefs = await self._prefs.get(user_id)
    if not prefs.category_enabled(category):
        return
    if prefs.channel_enabled("browser"):  await self._create_in_app(...)   # 既存
    if prefs.channel_enabled("email"):    await self._enqueue_email(...)    # 既存/将来
    if prefs.channel_enabled("discord"):  await self._enqueue_discord(...)  # 既存Bot連携
```
新イベント種別（スカウト/LFP応募など）は `category` 文字列を足すだけ。DB変更不要（③のJSONB設計）。監査・活動イベントの一部（大会承認/優勝など）は `EventService.emit` 後に該当ユーザーへ通知 dispatch をフックできる（疎結合）。

## 17. Discord連携

既存 Discord Bot / `/api/v1/bot/*`・通知キューを流用:
- ③ で discord チャネルOFFのユーザーには Discord通知を送らない（dispatch分岐）。
- ⑨ 運営ダッシュボードの「Discord通知状況」は既存の通知送信ログ/`command_metrics` を参照して未送信/失敗を可視化。
- ⑩ レポート生成時、大会Discordへ「大会終了・結果サマリー」を任意投稿（既存 webhook/bot 経由、organizer設定でON/OFF）。
Bot 側は新規コマンド不要（Web主導）。将来 `/report` `/standings` コマンド追加余地。

---

## 18. テスト設計

既存 pytest(async) + httpx AsyncClient を踏襲。

- **単体（Service）**: `EventService.emit` が正しい行を作る／`PreferenceService` のデフォルトマージ／`SearchService` の並列集約／`ReportService.generate` の集計正当性（既知データで期待値）。
- **Repository**: pg_trgm 検索が想定順位を返す（テストDBに拡張導入）／タグ一括取得のN+1が無い（クエリ数アサート）。
- **API（統合）**: 権限（非オーナーが監査/スポンサー編集で403）／通知設定の部分更新／検索レスポンス形状 `{players,teams,tournaments,matches}`／レポートは completed 以外で409。
- **回帰**: 既存 tournament status 変更が監査を記録しても既存挙動を壊さない（後方互換）。
- **フロント**: global-search のデバウンス/キーボード操作、Markdownレンダリングの XSS サニタイズ（react-markdown はデフォルトHTML無効）。
- **マイグレーション**: `alembic upgrade head` → `downgrade -1` の往復をCIで検証。

## 19. パフォーマンス考慮

- **N+1回避**: 監査 actor は `selectinload`。一覧のタグは親ID一括取得（Data Loader）。
- **検索**: pg_trgm GIN インデックス + `LIMIT n` + `asyncio.gather` 並列。`similarity` 閾値で候補削減。将来は `tsvector`(全文) へ拡張可能な列設計。
- **集計キャッシュ**: Team実績⑥・レポート⑩は Redis（TTL/イベント invalidation）。レポートは生成時に materialize（読み取りゼロ集計）。
- **運営サマリー⑨**: 30s ポーリングだが各カウントは軽量 `COUNT`/インデックス済み。集計を1エンドポイントに集約し往復削減。
- **ログ肥大**: `domain_events` は追記のみ・複合インデックス。将来は月次パーティション + BRIN、古いログの S3 アーカイブへ無停止移行。
- **書き込み負荷**: `emit` は同一トランザクション内（監査の一貫性優先）。高頻度化したら SQS/Redis Stream へ非同期化（既存 worker 基盤流用）。

## 20. 将来的な拡張性

- **イベント種別追加**: `action` 文字列 + JSONB のみ（マイグレーション不要）。監査/活動/運営が同基盤なので新イベントは全ビューに自動反映。
- **通知種別追加**: JSONB `categories` にキー追加のみ。
- **タグ拡張**: `tags` カタログにINSERTのみ。カテゴリ追加自由。
- **ゲーム追加**: 集計・レポートは `GameType` 非ハードコード（ゲーム別項目は `game_settings`/JSONBで分岐）。賞金など「対応ゲームのみ」の項目はフラグ制御。
- **Riot非依存**: レポート/実績は大会内データ(matches/results)から算出。Riotは任意の補助データソースに留める。
- **レポートのPDF/AI連携**: `markdown` を保存済みのため、PDF化（サーバー/クライアント）や AXELIA Analytics への `data` JSONB 連携は後付け可能。
- **運営テンプレート**: `ops_templates` により大会規模別チェックリストを保存・適用。固定フロー非採用ゆえゲーム/規模差に追従。
- **多言語/監査エクスポート/Webhook購読** 等も同一基盤上で追加容易。

---

### まとめ（設計の芯）
- **1つの追記イベント基盤（domain_events）で ①②⑨ を統一** — 重複実装を排し、拡張は文字列+JSONBのみ。
- **JSONB Preference で ③** — 通知種別追加にマイグレーション不要。
- **ポリモーフィック関連 + pg_trgm で ④⑤** — 横断検索・タグを後方互換に。
- **既存集計/キャッシュ資産の再利用で ⑥⑩** — Riot非依存・ゲーム非依存。
- すべて **add-only マイグレーション**・**既存3層/命名/Response規約準拠**で後方互換を担保。
```
