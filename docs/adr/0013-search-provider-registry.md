# ADR-0013: Search Provider Registry

- **Status**: Accepted
- **Date**: 2026-07-05
- **Deciders**: Solo developer

## Context
グローバル検索（機能④）を実装する。現在の検索対象は Team / Player / Tournament / Match の4種だが、今後 LFP / LFT / News / Analytics 等が増える。固定 if 分岐で実装すると、対象追加のたびに SearchService（core）を改修し、変更量が線形に増える。
また各エンティティの検索結果は形（名前・サブ情報・画像・遷移先）が異なるため、返却形式を統一しないとフロントが対象ごとに分岐する。

本ADRは、検索の拡張構造と返却契約を確定する（PHASED §8, ADR-0005 を前提）。

## Decision

### 1. SearchProvider へ委譲・SearchService は束ねるだけ
- 各エンティティ固有の検索ロジックは **SearchProvider** に閉じ込める（`name`, `search(q, limit) -> list[SearchHit]`）。
- **SearchService は Provider を束ねる（orchestrate）だけ**:
  - `SearchRegistry.enabled(types)` で対象 Provider を取得。
  - `asyncio.gather` で**並列実行**。
  - 結果を**カテゴリ別に集約**して返す。
  - SearchService はエンティティ固有の SQL / テーブルを知らない。
- 新対象追加 = **Provider 1ファイル + `registry.register(...)` 1行**（SearchService・API・フロント契約 無改修）。

### 2. 返却形式は共通 SearchResultDTO に統一
- 各 Provider は共通の **`SearchHit`** を返す:
  `type / id / label / sub / image_url / url / score(0..1)`。
- 集約結果は **`SearchResultDTO`**:
  `{ players: [SearchHit], teams: [...], tournaments: [...], matches: [...] }`（type 別グルーピング）。
- score は各 Provider が **0..1 に正規化**（異種混在でも比較・並び替え可能）。
- フロントは型に依存せず SearchHit を描画（対象追加時も UI 契約不変）。

### 3. 実装は Provider 内に隠蔽（差し替え可能）
- 現フェーズの検索実装は **pg_trgm similarity / ILIKE**（Provider 内に隠蔽）。
- 将来 PGroonga / tsvector へ変える場合も **Provider 実装の差し替えのみ**（Strategy / ADR-0005・スケールトリガーで判断）。
- 各 Provider は「**公開エンティティのみ返す**」責務を自身に持つ（横断で非公開が漏れない）。

### 4. API / 権限 / パフォーマンス
- `GET /api/v1/search?q=&types=&limit=` — `types` は Provider 名の動的許可（省略時は全 Provider）。
- `q` は最小長（2文字）・上限長で DoS 抑制。1 Provider の失敗は隔離しログに残す（全体を止めない）。
- N+1回避: 各 Provider は必要情報を1クエリで取得（JOIN 等）。
- 検索履歴・最近見た項目は **クライアント（Zustand persist）** で保持（サーバー不要 / PHASED §11）。

## Consequences
- (+) 検索対象追加が O(1)（Provider + register のみ）。SearchService は不変。
- (+) 返却が SearchResultDTO / SearchHit に統一され、フロントが対象非依存。
- (+) 検索実装（pg_trgm→PGroonga 等）が Provider 内に閉じ、差し替えが局所化。
- (−) 間接層（Provider/Registry）が増える。拡張性の対価として許容。
- (−) score 正規化は各 Provider の責務（実装の一貫性はレビューで担保）。

## Alternatives considered
- SearchService に全エンティティの検索を直書き: 追加のたび core 改修・肥大。→ 却下。
- エンティティごとに別 API（/search/teams など）: フロントが対象ごとに分岐・横断検索が組めない。→ 却下。
- 最初から全文検索エンジン（ES/PGroonga）: premature（PHASED / スケールトリガー未達）。→ 却下（Provider 差し替えで将来対応）。
