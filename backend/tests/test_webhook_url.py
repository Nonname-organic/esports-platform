"""通知ワーカーは Discord の Webhook 以外へ送らない（SSRF 対策）。"""
import pytest

from app.workers.handlers.notification import is_discord_webhook_url


@pytest.mark.parametrize("url", [
    "https://discord.com/api/webhooks/123/abc",
    "https://discordapp.com/api/webhooks/123/abc",
    "https://ptb.discord.com/api/webhooks/123/abc",
])
def test_discordのwebhookは許可(url):
    assert is_discord_webhook_url(url)


@pytest.mark.parametrize("url", [
    "http://discord.com/api/webhooks/123/abc",         # 平文
    "https://discord.com.evil.example/api/webhooks/1",  # 似せたホスト
    "https://evil.example/api/webhooks/1",
    "https://discord.com/api/v10/users/@me",            # Webhook 以外の API
    "https://discord.com:8443/api/webhooks/1/a",        # 別ポート
    "http://169.254.169.254/latest/meta-data/",          # メタデータ
    "http://api:8000/api/v1/admin/users",               # 内部サービス
    "not a url",
])
def test_それ以外は拒否(url):
    assert not is_discord_webhook_url(url)
