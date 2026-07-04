# ADR-0014: Tagging Model（正規化タグ + ポリモーフィック関連）

- **Status**: Accepted
- **Date**: 2026-07-05
- **Deciders**: Solo developer

## Context
タグ機能（機能⑤）を Team / Tournament / LFP / LFT の**複数エンティティ横断**で実装する。要件は「複数タグ・タグ検索・タグ追加が容易」。
実装の選択肢は主に2つ:
- **(A) JSONB 配列**を各エンティティに持たせる（`teams.tags`, `tournaments.tags`, ...）。
- **(B) 正規化**（`tags` カタログ + `taggables` ポリモーフィック中間表）。

## Decision
**(B) 正規化モデルを採用する。**

### スキーマ
```
tags
  id         UUID PK
  slug       VARCHAR(50) UNIQUE   -- 正規化キー: ^[a-z0-9-]+$（beginner, premier, online ...）
  label      VARCHAR(50)          -- 表示名（自由・多言語余地）
  category   VARCHAR(30) NULL     -- skill | event | region ...（グルーピング）
  color      VARCHAR(20) NULL
  created_at TIMESTAMPTZ

taggables  （ポリモーフィック中間表）
  tag_id      UUID FK tags(id) ON DELETE CASCADE
  entity_type VARCHAR(32)   -- team | tournament | lfp | lft
  entity_id   UUID
  created_at  TIMESTAMPTZ
  PRIMARY KEY (tag_id, entity_type, entity_id)
  INDEX (entity_type, entity_id)   -- エンティティのタグ取得
  INDEX (tag_id, entity_type)      -- タグ検索（横断）
```

### 採用理由（なぜ正規化か）
1. **タグ検索が主要件**: 「このタグが付いた Team 一覧」は JOIN で効率的。JSONB 配列だと横断検索・集計（人気タグ）が非効率で、GIN 前提の複雑クエリになる。
2. **タグ表記の一貫性**: `slug` UNIQUE により表記ゆれ（"Beginner"/"beginner"）を排除。ラベル/色/カテゴリを1箇所で管理でき、名称変更が全エンティティに即反映（JSONB だと各行にコピーが散る）。
3. **横断が自然**: ポリモーフィック `taggables` は entity_type を足すだけで新エンティティ（LFP/LFT/将来 Player 等）に対応。JSONB だと各テーブルに列追加が必要。
4. **参照整合性**: `taggables.tag_id` は FK（CASCADE）。タグ削除で関連が自動除去。JSONB は孤児タグ（存在しないタグ名）を検知できない。

### 割り切り（正規化の代償への対処）
- **entity_id の FK は張らない**（ポリモーフィックのため単一 FK 不可）。孤児（削除されたエンティティの taggables）は、
  各エンティティ削除サービス内で `taggables` も削除する（TagService.clear_entity）か、将来バッチ掃除。現フェーズは
  エンティティ削除時クリアで対応。
- **タグ付与は差分更新（PUT で置き換え）**: エンティティのタグを丸ごと受け取り、追加/削除を算出。
- **未知 slug の扱い**: 既定は **既存タグのみ許可**（カタログから選ぶ）。自由作成を許すかは TagService の方針で切替可能（現フェーズはカタログ+新規作成許可の緩めで開始、正規化 slug 化）。

### 責務（3層・SSOT）
- **TagService**: タグの正規化（slug 生成）・カタログ取得・エンティティへの付与/差し替え・タグ検索の唯一の窓口。
- **TagRepository**: `tags` / `taggables` の永続化。一覧のタグは**親IDリストで一括取得**（Data Loader・N+1回避）。
- 付与権限は**対象エンティティの権限に従う**（Team=owner/captain, Tournament=organizer, LFP/LFT=作成者）。

## Consequences
- (+) タグ検索・人気タグ集計・表記統一・横断対応が効率的。参照整合性（tag側）が担保。
- (+) 新エンティティ対応 = `entity_type` 追加のみ（スキーマ変更不要）。
- (−) entity_id の FK 不在 → 孤児 taggables を削除サービス/バッチで掃除する必要。
- (−) 取得に JOIN/一括ロードが必要（JSONB の即時読みより一手間）。Data Loader で N+1 回避。
- **Scale Trigger**: タグ数・付与数が極端に増えたら `tags.usage_count` 非正規化（人気タグUI高速化）を検討。

## Alternatives considered
- (A) JSONB 配列: 追加は楽だが、横断検索・表記統一・整合性・人気集計で不利。タグ検索が主要件のため不適。→ 却下。
- entity 別中間表（team_tags / tournament_tags ...): エンティティ増でテーブルが増殖。ポリモーフィック1表が簡潔。→ 却下。
