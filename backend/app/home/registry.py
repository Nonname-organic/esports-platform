"""Home Provider Registry（ADR-0019）。

Provider を追加/差し替えする唯一の場所。HomeAggregator はこの登録を集約するだけ。
AI差し替え = Recommendation/Prediction の実装をここで交換（Consumerは不変）。
"""

from __future__ import annotations

from app.home.base import WidgetProvider
from app.home.providers import (
    ActivityHomeProvider,
    InsightsProvider,
    LiveSummaryProvider,
    RuleBasedPredictionProvider,
    RuleBasedRecommendationProvider,
    TrendingProvider,
)

# 順序 = ホーム上の意味的優先度（おすすめ→予測→トレンド→ライブ→活動→インサイト）
PROVIDERS: list[WidgetProvider] = [
    RuleBasedRecommendationProvider(),
    RuleBasedPredictionProvider(),
    TrendingProvider(),
    LiveSummaryProvider(),
    ActivityHomeProvider(),
    InsightsProvider(),
]

# 例（将来）: NewsProvider / SponsorProvider / CreatorProvider / LFPProvider などを
# ここへ append するだけで拡張可能（HomeAggregator 変更不要）。


def get_provider(key: str) -> WidgetProvider | None:
    return next((p for p in PROVIDERS if p.key == key), None)
