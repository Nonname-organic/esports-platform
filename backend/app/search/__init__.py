"""グローバル検索（機能④ / ADR-0013）。

SearchService は Provider を束ねるだけ。各エンティティ固有の検索は Provider へ委譲。
返却は共通 SearchHit / SearchResultDTO に統一。
"""
