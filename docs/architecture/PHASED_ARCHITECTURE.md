# Phased Architecture — 「世界レベルまで成長できる」現実解（確定版）

前提フェーズ: **1人開発 / 公開前 / 本番前提 / 現在数百人 / 将来数万人**。
判断基準は常に **「今必要か？」**。オーバーエンジニアリング禁止。将来拡張は **Interface・責務分離・契約**だけ用意し、実体は**スケールトリガー到達後**に差し替える。

維持: 3層（Repository / Service / Router）・後方互換・Add-only Migration・JSONB拡張・既存API互換。

> 関連: `FEATURE_EXPANSION_DESIGN.md`（将来の到達点）/ `ARCHITECTURE_REVIEW.md`（レビュー）。本書が **現フェーズの実装の正**。

---

## 0. Architecture Growth Policy（設計思想・最上位）

```
# Architecture Growth Policy

Current Stage:

  Single Developer   ← 現在地
        ↓
  Public Beta
        ↓
  Commercial Release
        ↓
  Growth
        ↓
  Scale

The project prioritizes, in this order:

  1. Maintainability
  2. Simplicity
  3. Backward Compatibility
  4. Extensibility
  5. Performance

Principles:

  - Scalability features are introduced ONLY when a Scale Trigger is reached.
  - Never introduce infrastructure complexity before operational metrics justify it.
  - For the future, build INTERFACES, SEPARATION OF CONCERNS, and CONTRACTS — not implementations.
  - Infrastructure is swappable later; CONTRACTS must be correct now.
  - Every addition must answer one question first: "Is this needed now?"
```

**なぜ文章として残すか**: 半年後に「なぜ Kafka を入れていないのか」「なぜ CQRS でないのか」という議論を再燃させないため。**「意図的に入れていない」ことを設計判断として明文化**する。判断は「機能の有無」ではなく「スケールトリガー到達の有無」で行う。

このポリシーにより、各段階で導入する複雑性が決まる:

| Stage | 目安 | この段階で導入 |
|---|---|---|
| Single Developer（現在） | 〜数百人 | Event基盤(1テーブル+Outbox列) / InProcess Dispatcher / Provider契約 / backup / trace_id / Sentry |
| Public Beta | 〜数千人 | 通知チャネル拡充 / 検索Provider拡張 / 監査・活動UI |
| Commercial Release | 〜1万人 | Redisキャッシュ / 部分的な事前集計 / レート制限 |
| Growth | 〜数万人 | audit/activity 物理分離 / Redis Pub/Sub(WS) / PGroonga / SQS Dispatcher |
| Scale | 数万人〜 | Read Replica / CQRS投影 / Event Bus / RDS/Aurora移行 |

---

## 1. 修正版アーキテクチャ（現フェーズ）

```
Command（書き込み）
  Router → Service → Repository → Postgres
                        │ 同一Tx
                        └→ EventService.emit(envelope)
                              → domain_events INSERT (dispatched_at=NULL)   ← Event Log 兼 Outbox

OutboxRelay（既存 worker プロセス内 asyncio ループ / tournament_status_loop と同居）
  claim: UPDATE ... SET locked_at, locked_by WHERE dispatched_at IS NULL AND (locked_at IS NULL OR stale)
         （実体は SELECT ... FOR UPDATE SKIP LOCKED + locked列で可視化）
  → EventDispatcher.dispatch(envelope)          # InProcess（interface化・将来SQS/Redis/Kafka）
  → 成功: dispatched_at=now()  / 失敗: dispatch_attempts++, last_error 記録, 再試行

EventDispatcher（InProcess fan-out・冪等・consumer registry）
  ├ NotificationDispatcher → PreferenceResolver → ChannelProvider(browser/email/discord)
  ├ ReportGenerator(registry) → tournament_reports upsert（tournament.completed時）
  └ （将来 register で追加）Projector / WebhookDelivery / CacheInvalidator

Query（読み取り）
  Router → Service → Repository → Postgres（+一部 Redis cache）
  監査:  list_audit()    = domain_events WHERE visibility='internal'
  活動:  list_activity() = domain_events WHERE visibility='public'
  （将来 物理分離しても Repository の read メソッド差し替えのみ・Service/Router 不変）
```

**核心の割り切り**: `domain_events` = **Event Log かつ Transactional Outbox**（1テーブル）。`dispatched_at` 他の列で Outbox を実現し、別テーブル・別ミドルウェアを持たない。Dispatcher は InProcess だが **interface 化**してあり、スケールトリガー到達時に SQS/Redis/Kafka へ差し替えられる（呼び出し側無変更）。

---

## 2. 修正版Event基盤

責務:
- **EventService.emit()**: 唯一の書き込み口。Envelope を検証（Registry照合）し、同一Txで domain_events に INSERT。ドメイン処理と原子性を共有（dual-write撲滅）。
- **domain_events**: 追記のみの Event Log。同時に Outbox（未dispatch行のキュー）。
- **OutboxRelay**: 未dispatch行を拾い Dispatcher へ渡す（at-least-once）。
- **EventDispatcher**: consumer への fan-out。今は InProcess。
- **Consumers**: NotificationDispatcher / ReportGenerator。全て**冪等**（idempotency_key で重複排除）。

依存方向: `Router → Service → (Repository, EventService)`。Consumer は Service を呼んでよいが、Service は Consumer を知らない（一方向・疎結合）。

---

## 3. Event Envelope設計

全イベント共通の契約。Pydantic モデルで型付け、domain_events の列にマップ。

| フィールド | 型 | 意味 |
|---|---|---|
| `event_id` | UUID | イベント一意ID（= domain_events.id） |
| `event_version` | int | payload スキーマ版（Registry由来。upcasting用） |
| `type` | str | Registry管理の型名 `domain.entity.action` |
| `occurred_at` | datetime | **ドメイン上の発生時刻**（≠ DB挿入時刻 created_at） |
| `actor_id` | UUID? | 実行ユーザー（system/bot は NULL） |
| `actor_type` | str | `user` \| `system` \| `bot` |
| `actor_ip` | INET? | 取得可能なら（X-Forwarded-For 先頭） |
| `producer` | str | 発生元 bounded context（`tournament`/`team`/`scout`…） |
| `service` | str | 発生元プロセス（`api` \| `worker`） |
| `entity_type` / `entity_id` | str / UUID | 対象 |
| `before` / `after` | JSONB? | 変更前後（PII非格納。user_id参照） |
| `metadata` | JSONB? | 表示・拡張用の任意情報 |
| `trace_id` | UUID? | リクエスト相関（1 HTTP → 複数イベントを束ねる） |
| `correlation_id` | UUID? | 因果連鎖（イベント→派生イベント） |
| `idempotency_key` | str? | 冪等キー（UNIQUE部分制約） |
| `visibility` | str | `internal`（監査）\| `public`（活動） |

> `producer` と `service` を分ける理由: *どのドメイン文脈* で起きたか（producer）と *どの実行体* が書いたか（service=api/worker）は別軸。将来の分析・ルーティングで両方要る。
> `occurred_at` と `created_at` を分ける理由: 遅延書き込み・再取り込み時に「実際の発生時刻」を保持するため。

---

## 4. Event Registry設計

イベントを**文字列直書きせず**、コード上のカタログで一元管理（DB不要）。型・version・payload schema を保持。

### 命名規則
```
<domain>.<entity>.<action>     すべて小文字・ドット区切り
  domain : bounded context      (team, tournament, scout, player, notification …)
  entity : 集約/対象            (member, registration, bracket, status …)
  action : 動作                 (add, remove, approve, publish, complete …)

例:
  team.member.add
  team.member.remove
  team.owner.change
  tournament.registration.approved
  tournament.registration.rejected
  tournament.published
  tournament.status.changed
  tournament.bracket.generated
  tournament.completed
  match.result.updated
```
> 規約は「動詞は簡潔・一貫」。過去形/現在形はドメイン内で統一（例では現在形 add/remove、状態遷移は completed/approved）。**重要なのは Registry で一元管理し emit で検証すること**（タイポ・野良イベントの排除）。

### 構造（name / version / payload schema）
```python
# app/events/registry.py  — コードのみ
class Ev:
    TEAM_MEMBER_ADD          = "team.member.add"
    TEAM_MEMBER_REMOVE       = "team.member.remove"
    TOURNAMENT_PUBLISHED     = "tournament.published"
    TOURNAMENT_STATUS_CHANGED= "tournament.status.changed"
    TOURNAMENT_COMPLETED     = "tournament.completed"
    REGISTRATION_APPROVED    = "tournament.registration.approved"
    # ...

REGISTRY: dict[str, EventSpec] = {
    Ev.TEAM_MEMBER_ADD: EventSpec(
        version=1,
        visibility="internal",
        notify=True,                       # 通知対象か
        payload=TeamMemberAddPayload,      # Pydantic: after の期待スキーマ（任意・段階導入）
    ),
    Ev.TOURNAMENT_COMPLETED: EventSpec(
        version=1, visibility="public", notify=True, payload=TournamentCompletedPayload,
    ),
    # ...
}
```
- **emit() は `type` が REGISTRY に在ることを必須検証**（未登録は例外＝野良イベント禁止）。
- `payload` schema は**段階導入可**（最初は None 許容、重要イベントから型付け）。version と組で consumer 側 upcasting を可能にする。
- 新イベント追加 = REGISTRY に1エントリ + 定数1行（マイグレーション不要）。

---

## 5. Transactional Outbox設計（別テーブルなし）

`domain_events` に Outbox 用の列を追加し、**イベントログがそのままキュー**になる。

```
domain_events （Envelope列は §3、Outbox列は下記）
  ...envelope columns...
  dispatched_at    TIMESTAMPTZ NULL          -- NULL=未処理
  dispatch_attempts SMALLINT NOT NULL DEFAULT 0
  last_error       TEXT NULL                 -- 直近失敗理由（運用可視性）
  locked_at        TIMESTAMPTZ NULL          -- 処理中ロック取得時刻（クラッシュ回収用）
  locked_by        VARCHAR(64) NULL          -- 処理中の worker識別子
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now()

  INDEX ix_events_undispatched (created_at) WHERE dispatched_at IS NULL   -- 部分Index=キュー
  INDEX ix_events_entity (entity_type, entity_id, created_at DESC)
  INDEX ix_events_visibility (visibility, type, created_at DESC)
  UNIQUE ix_events_idem (idempotency_key) WHERE idempotency_key IS NOT NULL
```

### 取得ループ（既存 worker 内）
```
loop every 2s:
  rows = SELECT * FROM domain_events
         WHERE dispatched_at IS NULL
           AND (locked_at IS NULL OR locked_at < now()-INTERVAL '5 min')   -- stale回収
         ORDER BY created_at
         FOR UPDATE SKIP LOCKED                       -- 同時実行安全
         LIMIT 100
  mark rows: locked_at=now(), locked_by=<worker_id>
  for e in rows:
     try:
        dispatcher.dispatch(EventEnvelope.from_row(e))   # 冪等
        e.dispatched_at = now(); e.locked_at = NULL
     except Exception as ex:
        e.dispatch_attempts += 1; e.last_error = str(ex)[:500]; e.locked_at = NULL
        # attempts が閾値超で「要調査」フラグ（DLQ相当は将来）
```
- **`FOR UPDATE SKIP LOCKED`** で複数worker同時でも二重処理しない。
- **`locked_at/locked_by`** はクラッシュ時の stale ロック回収と運用可視化（「今どのworkerが何を処理中か」）。
- **`dispatch_attempts/last_error`** で失敗の可視化・再試行制御。閾値超は Sentry 通知（将来 DLQ）。
- 数百人規模では 2秒間隔・LIMIT 100 で十分。滞留増はスケールトリガーで対処。

---

## 6. Event Dispatcher設計

```python
# app/events/dispatcher.py
class EventDispatcher(Protocol):
    async def dispatch(self, envelope: EventEnvelope) -> None: ...

class InProcessDispatcher:              # ← 現在はこれだけ実装
    def __init__(self, consumers: list[EventConsumer]): ...
    async def dispatch(self, e):
        for c in self._consumers:
            if c.handles(e.type):
                await c.handle(e)       # 冪等・失敗は隔離してlog（1consumer失敗が全体を止めない）

# 将来（interfaceのみ・実装しない）:
#   SqsDispatcher / RedisStreamDispatcher / KafkaDispatcher
#   → OutboxRelay は EventDispatcher に依存するだけ。差し替えで呼び出し側無変更。

class EventConsumer(Protocol):
    def handles(self, event_type: str) -> bool: ...
    async def handle(self, envelope: EventEnvelope) -> None: ...   # 冪等必須
```
- 現在の consumers: `NotificationConsumer`, `ReportConsumer`。register で追加。
- 差し替え点は `EventDispatcher` interface **1箇所のみ**。SQS化はここの実装追加とRelayの向き先変更だけ。

---

## 7. Notification基盤

```
EventDispatcher → NotificationConsumer（冪等）
  1. RoutingRules: どの event.type を誰に、どの category で通知するか（コードtable）
  2. Recipient解決（対象user群）
  3. PreferenceResolver（優先順位を明文化）
        global channel OFF > per-entity mute > category OFF > default ON
  4. ChannelRegistry へ fan-out
        ChannelProvider(Protocol): name; async send(recipient, message) -> DeliveryResult
        現在: BrowserChannel(in-app) / EmailChannel / DiscordChannel
        将来(interfaceのみ): WebhookChannel / PushChannel / LineChannel  ← register で追加
  5. notification_deliveries に結果記録（status/error）→ Dashboard・可観測性
```
- **Redis Stream / Kafka は使わない**。Outbox→既存worker の InProcess fan-out で十分。
- Preference は JSONB（`{channels:{...}, categories:{...}}`）→ 種別追加でマイグレーション不要。
- **冪等**: `notification_deliveries` の UNIQUE(`event_id`,`user_id`,`channel`)。
- 新チャネル追加 = ChannelProvider 1実装 + register 1行（core 無改修）。

---

## 8. Search基盤

```python
class SearchProvider(Protocol):
    name: str          # "team" | "player" | "tournament" | "match"
    weight: float      # スコア正規化の重み
    async def search(self, q: str, limit: int) -> list[SearchHit]: ...
    # SearchHit(score: float[0..1], label, sub, image_url, url, type)

registry = SearchRegistry()
registry.register(TeamSearchProvider())
registry.register(PlayerSearchProvider())
registry.register(TournamentSearchProvider())
registry.register(MatchSearchProvider())

class SearchService:
    async def search(self, q, types, limit) -> SearchResults:
        providers = registry.enabled(types)
        results = await asyncio.gather(*[p.search(q, limit) for p in providers])
        return group_by_type(results)   # {players, teams, tournaments, matches}
```
- 実装は今は **pg_trgm similarity + ILIKE**（provider内に隠蔽）。
- **LFP / LFT / News / Analytics 追加 = Provider 1ファイル + register 1行**（core・API・フロント契約 無改修）。
- 各 provider が **公開エンティティのみ返す**責務（横断漏洩防止）+ **score を 0–1 正規化**（異種混在の比較可能性）。
- 将来 **PGroonga** は provider 実装差し替えのみ（Strategy）。検索履歴/最近見た項目は Zustand persist（サーバー不要）。

---

## 9. Report基盤

```
Service: tournament.status → completed（同一Tx）
   └→ EventService.emit(Ev.TOURNAMENT_COMPLETED, ...)      # domain_events(未dispatch)
OutboxRelay → EventDispatcher → ReportConsumer
   → ReportGenerator.generate(tournament_id)               # interface
        現在: TournamentReportGenerator
        将来(interfaceのみ): PlayerReportGenerator / SeasonReportGenerator
   → tournament_reports UPSERT（version++、data JSONB + markdown）
API: GET /tournaments/{id}/report → 生成済みを読むだけ（未生成404 / 生成中202）
     POST /report/generate → 手動再生成も同じ emit を発火（同期生成はしない）
```
```python
class ReportGenerator(Protocol):
    kind: str                      # "tournament" | "player" | "season"
    async def generate(self, target_id: UUID) -> ReportResult: ...
```
- **同期生成禁止**（ベストマッチ等は O(試合数) 以上）。必ず worker。
- **冪等 + version**: 再生成で上書き、schema 進化に耐える。
- **キャッシュ不要**: `tournament_reports` 自体が materialized（生成済みは不変）。
- **data JSONB を安定契約**にし、将来 PlayerReport/SeasonReport や AXELIA Analytics / PDF は read-only 参照（Report生成に依存させない）。
- 生成 > 5秒（スケールトリガー）で worker 分散を検討。

---

## 10. スケールトリガー一覧（判断基準）

| メトリクス | 閾値 | アクション（到達後に着手） |
|---|---|---|
| domain_events 行数 | **> 100万** | audit_logs / activity_feed へ物理分離 + 月次パーティション + BRIN |
| API p95 応答 | **> 200ms** | 該当APIに Redis キャッシュ |
| 集計API(実績/レポート) | **> 500ms** | 事前集計（部分CQRS投影） |
| 検索 p95 / 日本語精度 | **> 300ms** or ヒット不良 | PGroonga / tsvector(bigram) |
| 同時 WebSocket 接続 | **> 500** | Redis Pub/Sub アダプタ + 複数インスタンス |
| Outbox 未処理滞留 | **> 1000 or 5分** | Relay 並列度↑ → SQS Dispatcher へ差し替え |
| Report 生成時間 | **> 5秒** | Worker 分散 / 生成分割 |
| Postgres 接続数 | **> max_connections 70%** | PgBouncer(transaction pooling) |
| DB サイズ / EBS IOPS | 逼迫 | RDS / Aurora 移行（Multi-AZ + PITR + Read Replica） |
| worker 処理ラグ | 投入 > 処理 | worker スケールアウト（別コンテナ/Fargate） |

各トリガーは Sentry + ログ + 簡易メトリクスで監視。**到達して初めて**該当の将来実装に着手する（先回り禁止）。

---

## 11. 採用しないもの（Interfaceのみ・実装禁止）／将来導入する機能一覧

| 項目 | 今用意するシーム（契約/責務分離） | 導入トリガー |
|---|---|---|
| CQRS 投影 | Dispatcher に Projector consumer を register 可能 | 集計API 200/500ms超 |
| Kafka / Event Bus | `EventDispatcher` interface（InProcess→差替） | 数万人・外部連携・WS500超 |
| Redis Stream | 同上（Dispatcher差替） | Outbox滞留・fan-out増 |
| audit_logs 物理分離 | `visibility` 列 + `list_audit()` Repository分離 | events 100万超 |
| activity_feed 物理分離 | `visibility='public'` + `list_activity()` | events 100万超 / 活動read増 |
| PGroonga / ElasticSearch | `SearchProvider` が検索実装を隠蔽 | 検索300ms超・日本語精度 |
| Read Replica | Repository のセッション取得を一点集約 | 読み負荷でCPU/IO逼迫 |
| WS 水平化 (Redis pub/sub) | WSハンドラを pub/sub 差替可能に | 同時接続500超 |
| Microservice | bounded context（producer）境界の明示のみ | 複数チーム開発・独立スケール |
| RDS/Aurora | Docker Postgres 維持・接続を抽象化 | データ耐久/HA要件・DB逼迫 |

**原則**: これらは「作らない」が「作れるように契約だけ整える」。Growth Policy に従い、スケールトリガー到達まで着手しない。

---

## 12. 実装優先順位（P0再設計）

> `trace_id` は Envelope が保持する＝**Envelope と同時に trace_id 基盤（request middleware）を入れるのが綺麗**。Sentry は trace_id 確立後に接続。

| 順 | 実装 | 内容 / 理由 |
|---|---|---|
| **P0-1** | **Backup** | pg_dump → S3 夜次 cron（+ 世代保持）。データ全損リスクを即消す。数十行 |
| **P0-2** | **Event Envelope + trace_id 基盤** | Envelope 定義 + request middleware（trace_id/correlation_id 生成・伝播）。以降の全イベントが trace を持つ |
| **P0-3** | **EventService.emit + Event Registry** | 唯一の書き込み口 + 型カタログ検証。domain_events(Envelope列)追加 |
| **P0-4** | **Transactional Outbox** | domain_events に Outbox列追加 + OutboxRelay（既存worker） |
| **P0-5** | **Event Dispatcher（InProcess）** | Dispatcher interface + consumer registry。実配線 |
| **P0-6** | **Sentry** | FE/BE 例外収集。trace_id を紐付け（P0-2で確立済み） |
| **P1-1** | 既存処理へ **emit() 差し込み**（status変更/承認/公開/メンバー操作…） | 基盤の実利用・監査開始（後方互換） |
| **P1-2** | **NotificationConsumer + ChannelProvider**（既存通知を移行） | 配信の信頼性・冪等 |
| **P1-3** | **Report 非同期化**（completed→worker, ReportGenerator interface） | 同期集計の除去 |
| **P2-1** | **Search Provider 化**（4実装） | 拡張性 |
| **P2-2** | 通知設定(Preference) UI + per-entity mute | UX |
| **P2-3** | 監査/活動 閲覧UI（domain_events を visibility で出す） | ①② 価値化 |
| **P3** | Dashboard(events+template+todo) / Tag / Sponsor / Rules(MD) / Team実績カード | 基盤上に薄く載る |

P0 = 公開前必須の生存＋基盤。P1 で基盤を実利用。P2以降は基盤の上に薄く載る機能。

---

## 13. 採用理由（なぜこの選択か）

| 判断 | 理由 |
|---|---|
| domain_events **1テーブル + Outbox列** | 数百人規模でイベント数少。別テーブル/別MWは保守負債。`visibility`/`dispatched_at` で論理分離済み＝後から物理分離可能 |
| **InProcess Dispatcher** | 現規模で SQS/Redis Stream は過剰。interface 化で差し替え自由 |
| **Event Registry（コード）** | DB化は過剰。定数+Specで十分・型安全・タイポ排除 |
| **Envelope に trace/correlation/idempotency/version** | 後入れは全イベント改修。今なら列追加のみ。運用・冪等・進化の前提 |
| **locked_at/locked_by/attempts/last_error** | 単一worker前提でもクラッシュ回収と失敗可視化に必須。DLQは将来 |
| **Notification/Search/Report を Provider・Generator 化** | 追加＝1ファイル+register。core 無改修。世界レベルへの拡張点 |
| **Report 非同期** | 同期集計はタイムアウト源。worker隔離が正 |
| **Docker Postgres 維持 + backup追加** | RDS化はコスト増。今の要件は「全損させない」＝backupで達成 |
| **可観測性は log + trace_id + Sentry のみ** | OTel/Prometheus/Grafana は運用者1人には過剰。障害可視性の最低ラインを確保 |
| **CQRS/Kafka/ES/分離を interfaceのみ** | Growth Policy: メトリクスが正当化するまで複雑性を入れない |

---

## 14. 将来導入する機能一覧（トリガー付き・再掲まとめ）

- **audit_logs / activity_feed 物理分離** … domain_events 100万件超
- **CQRS 投影** … 集計API 200/500ms超
- **PGroonga / tsvector(bigram)** … 検索 300ms超・日本語精度不足
- **Redis Pub/Sub（WS水平化）** … 同時接続 500超
- **SQS/Redis Stream Dispatcher（Event Bus化）** … Outbox滞留・外部連携・WS500超
- **Webhook / Push / LINE チャネル** … 事業要件発生時（ChannelProvider register）
- **PlayerReport / SeasonReport** … 機能要件発生時（ReportGenerator register）
- **Read Replica** … 読み負荷逼迫
- **PgBouncer** … Postgres接続 70%超
- **RDS/Aurora（Multi-AZ/PITR）** … データ耐久/HA要件・DB逼迫
- **Microservice 分割** … 複数チーム開発・独立スケール

すべて **Growth Policy** に従い、**スケールトリガー到達を判断基準**として着手する。契約（Envelope / Provider / Dispatcher / Generator interface）は現時点で整備済みのため、実体の差し替えは局所的で済む。

---

### 設計哲学の芯
> **「世界レベルのシステムを最初から作る」のではなく、「世界レベルまで無停止で成長できる契約を今固める」。**
> 契約（Envelope / Registry / Dispatcher / Provider / Generator interface）さえ正しければ、実体（InProcess→SQS、pg_trgm→PGroonga、1テーブル→物理分離、EC2→RDS）は後から差し替えられる。判断は常に「今必要か？」と「スケールトリガーに達したか？」で行う。
