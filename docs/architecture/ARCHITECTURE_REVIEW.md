# Architecture Review — Tournament OS（Principal レビュー・履歴）

> **位置づけ**: これは特定時点（初回フル設計 `FEATURE_EXPANSION_DESIGN.md` に対する）Principalレビューの**記録**。
> このレビュー結果を「そのまま採用」ではなく、現フェーズ（1人開発・公開前・数百人）向けに縮約した結論が `PHASED_ARCHITECTURE.md`（実装の正）。
> 本書は「なぜその判断に至ったか」の履歴として残す。

評価基準: 5年運用・世界レベルの Tournament Platform を想定。技術スタックは固定（Next.js / FastAPI / SQLAlchemy async / Postgres / Redis / EC2+Docker / CloudFront / S3 / nginx）。

---

## 1. 良い設計（正しく効いている判断）
- 3層 + Repository/Service/Router の一貫性・命名・`Response`/`ListResponse` 規約 → 認知負荷が低く長期運用に有利。
- JSONB を拡張点に使う判断（rules / attachments / prefs）→ DDLロック無しの機能追加。
- add-only マイグレーション徹底 + `server_default`（`status_locked` が模範）→ 本番無停止・後方互換。
- S3 presigned URL の read-time 再署名（key を正とする）→ 失効・公開バケット化の両方を回避。
- 統一 `emit()` 経路の着想 → イベント書き込みの一点集約（方向性は正しい）。
- Dashboard を固定フローにしない判断 → 大会規模・ゲーム差への耐性。

## 2. 問題点（設計ミス・将来ボトルネック）
**致命度: 高**
1. `domain_events` への過剰統合 — 監査/活動/運営タイムラインはアクセスパターン・保持・機密区分・Index要件が異なる。1テーブルは premature。特に `visibility` フィルタ漏れで内部 before/after(PII) が公開に漏れるリスク。
2. 同期 emit + 同一Txでの副作用ファンアウト — Transactional Outbox 欠落による dual-write 問題（通知が飛ばない/二重送信）。
3. 運用成熟度が app 層より低い（最大リスク）— 単一 EC2 + コンテナPostgres（backup/HA/PITR 無し）、可観測性ゼロ、WS 単一インスタンス前提。

**致命度: 中**
4. `action` フリー文字列・Registry無し・`event_version` 無し。
5. 相関ID/冪等キーの欠落。
6. 日本語全文検索に無防備（pg_trgm は日本語弱い）。
7. read-time 集計のキャッシュ無効化戦略 未定義。
8. Report 同期生成（タイムアウト源）。
9. taggables に参照整合性なし。
10. Alembic 連番のリビジョン衝突（多人数時）。

## 3〜11. 改善提案（要旨）
- **Event**: Envelope標準化（version/trace/correlation/idempotency/metadata/producer/service/occurred_at）、Registry管理、Transactional Outbox、Dispatcher interface。
- **DB**: 監査/活動の物理分離（将来）、Outbox、PII分離、BRIN+パーティション（将来）、pg_trgm→PGroonga（将来）。
- **API**: バージョニング方針、検索の per-type cursor、監査/活動の別リソース化、Idempotency-Key、エラー契約に code+trace_id。
- **Search**: Provider/Registry（LFP/LFT/News/Analytics を register で追加）、score 正規化、JP対応は provider 内に隠蔽。
- **Notification**: Event→Dispatcher→Channel Provider、precedence明文化、digest、配信ログ。
- **Dashboard**: Signals(イベント駆動read-model) + 自由Todo + Checklist Template + Timeline、push化。
- **Report**: Outbox→worker→冪等 upsert→versioned、materialized。

## 12〜14. 保守性・パフォーマンス・スケーラビリティ（要旨）
- 5年負債候補: domain_events肥大、インライン`__import__`、`model_dump(exclude_none)`、巨大ページ(大会作成1031行)、Alembic連番、JSONB暗黙契約、可観測性負債、`.env`平文秘密、テスト空白。
- 性能: read-time集計→投影(将来)、N+1回避(selectinload/Data Loader)、検索GIN+並列、polling→push、PgBouncer。
- スケール: 単一EC2が最大制約。RDS/Aurora(Multi-AZ/PITR/replica)、WS Redis pub/sub、worker独立スケール。

## 15. 実装優先順位（レビュー時点の提案）
- P0: backup/PITR、Secrets→SSM、Sentry、Transactional Outbox + Envelope。
- P1: 監査/活動分離、Event Registry、Notification Pipeline。
- P2: Search Provider + JP、Report非同期、Dashboard push。

## 16. 総合評価
- 設計ドキュメントとして **82/100**（思想の一貫性・後方互換・JSONB拡張・可読性は90点級。減点は物理過剰統合/Outbox欠落/イベントversion欠落/JP検索/集計キャッシュ）。
- 稼働インフラ込みのプロダクト成熟度は **65/100**（単一EC2+コンテナPostgres+可観測性ゼロ）。
- 世界レベルへの差分は *新機能* ではなく **(a)信頼性/運用 (b)イベント基盤の契約化 (c)読み取りの投影化** の3点。

---

## このレビューが `PHASED_ARCHITECTURE.md` にどう反映されたか（現フェーズ判断）
| レビュー指摘 | 現フェーズの結論（PHASED） |
|---|---|
| domain_events 物理分離すべき | **今は1テーブル維持** + `visibility`列で論理分離（分離は将来トリガーで） |
| Transactional Outbox 必須 | **採用**（別テーブルではなく domain_events の Outbox列で最小実装） |
| Event Bus(SQS/Kafka) | **InProcess Dispatcher のみ**（interfaceで将来差替） |
| 監査 PII 分離 / WORM | before/after に PII 非格納の方針のみ（物理WORMは将来） |
| RDS/HA/PITR | **Docker Postgres 維持 + pg_dump→S3**（RDS化は将来トリガー） |
| 可観測性フル(OTel/Prom/Grafana) | **log + trace_id + Sentry のみ**（残りは将来） |
| PGroonga(JP検索) | **pg_trgm**（PGroonga は SearchProvider 差替で将来） |
| CQRS投影 | **read-time集計 + Redis**（投影は集計200/500ms超で） |

**結論**: レビューは「世界レベルの到達点」を示す。現フェーズは Growth Policy に従い、**契約（Envelope/Provider/Dispatcher/Generator interface）だけを今固め、実体はスケールトリガー到達後に差し替える**。
