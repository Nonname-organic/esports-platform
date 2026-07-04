"""通知基盤（P1-2）。

domain_events → OutboxRelay → NotificationConsumer → PreferenceResolver → ChannelProvider。
配信ルールの SSOT は matrix.py（docs/architecture/NOTIFICATION_EVENT_MATRIX.md と1対1）。
"""
