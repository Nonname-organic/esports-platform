"""Report 基盤（ADR-0009）。

Event(tournament.completed) → OutboxRelay → ReportConsumer
  → Aggregator(集計) → Generator(組み立て/保存)。
Generator は集計しない。集計は Aggregator の責務。
"""
