"""パスワード再設定まわり。主眼はリセットトークンがログへ漏れないこと。

SMTP 未設定の分岐でメール本文をそのまま INFO ログへ出していた。本文には
30分有効な使い捨てトークン付きの URL が入るため、ログを読める範囲の人が
任意のアカウントのパスワードを再設定できてしまう。本番は SMTP 設定済みで
この分岐に入らないが、設定が外れた環境では成立する。

ここでは「本文が出ないこと」を軸に、既存のリセットフローが壊れていない
ことも併せて見る。
"""
import logging
import re

import pytest
from httpx import AsyncClient

from app.core import email as mailer
from app.core.config import settings
from app.core.dependencies import get_cache
from app.main import app
from app.middleware.rate_limit import RateLimitMiddleware

# 本物と同じ形のトークン。ログに出ていないことを確かめるための目印。
FAKE_TOKEN = "ZZZtestonlytoken0123456789abcdefg"
RESET_URL = f"https://example.test/reset-password?token={FAKE_TOKEN}"
BODY = f"テスト本文\n\n{RESET_URL}\n\nAXELIA"


@pytest.fixture(autouse=True)
def _enable_email_logger():
    """app.core.email のロガーを有効に戻す。

    conftest がスキーマ構築で alembic を呼び、alembic/env.py の
    fileConfig() が disable_existing_loggers=True（既定）で走るため、
    それまでに import 済みのロガーが軒並み disabled になる。
    この副作用があるとログの検証ができない。

    env.py 側で disable_existing_loggers=False にすればこの回避は不要に
    なる。別の修正として分けてあるので、そちらが入ったらここは消す。
    """
    lg = logging.getLogger("app.core.email")
    before = lg.disabled
    lg.disabled = False
    yield
    lg.disabled = before


@pytest.fixture
def smtp_unset(monkeypatch):
    monkeypatch.setattr(settings, "SMTP_HOST", "", raising=False)
    return settings


@pytest.fixture
def smtp_unreachable(monkeypatch):
    # 接続が即座に拒否されるポート。待たされずに失敗経路へ入る。
    monkeypatch.setattr(settings, "SMTP_HOST", "127.0.0.1", raising=False)
    monkeypatch.setattr(settings, "SMTP_PORT", 1, raising=False)
    monkeypatch.setattr(settings, "SMTP_SSL", False, raising=False)
    monkeypatch.setattr(settings, "SMTP_USER", "", raising=False)
    monkeypatch.setattr(settings, "MAIL_FROM", "noreply@example.test", raising=False)
    monkeypatch.setattr(settings, "MAIL_FROM_NAME", "AXELIA", raising=False)
    return settings


class _MemoryCache:
    """中身を保持する最小のキャッシュ。

    conftest の client フィクスチャが挿す FakeRedisCache は get が常に
    None を返すため、トークンを保存して取り出す経路を確かめられない。
    リセットの「一度しか使えない」はまさにその経路の性質なので、
    このテストの間だけ差し替える。
    """

    def __init__(self):
        self.store: dict = {}

    async def get(self, key):
        return self.store.get(key)

    async def set(self, key, value, ttl=None):
        self.store[key] = value

    async def delete(self, key):
        self.store.pop(key, None)

    async def delete_pattern(self, pattern):
        return 0

    async def exists(self, key):
        return key in self.store

    async def increment(self, key, ttl=None):
        return 1


# ── SMTP 未設定の分岐 ────────────────────────────────────────────────────────
class TestUnconfiguredSmtp:
    @pytest.mark.asyncio
    async def test_本文とトークンがログに出ない(self, smtp_unset, caplog):
        with caplog.at_level(logging.DEBUG, logger="app.core.email"):
            await mailer.send_email(to="user@example.test", subject="件名", body=BODY)
        text = caplog.text
        assert FAKE_TOKEN not in text
        assert RESET_URL not in text
        assert "reset-password?token=" not in text
        assert "テスト本文" not in text

    @pytest.mark.asyncio
    async def test_宛先と件名は記録される(self, smtp_unset, caplog):
        with caplog.at_level(logging.DEBUG, logger="app.core.email"):
            await mailer.send_email(to="user@example.test", subject="件名", body=BODY)
        assert "user@example.test" in caplog.text
        assert "件名" in caplog.text

    @pytest.mark.asyncio
    async def test_設定漏れに気づけるようWARNING以上で出す(self, smtp_unset, caplog):
        with caplog.at_level(logging.DEBUG, logger="app.core.email"):
            await mailer.send_email(to="user@example.test", subject="件名", body=BODY)
        levels = [r.levelno for r in caplog.records if r.name == "app.core.email"]
        assert levels, "app.core.email のログが1件も出ていない"
        assert max(levels) >= logging.WARNING

    @pytest.mark.asyncio
    async def test_Falseを返し例外を投げない(self, smtp_unset):
        assert await mailer.send_email(to="user@example.test", subject="件名", body=BODY) is False

    def test_is_configuredがFalse(self, smtp_unset):
        assert mailer.is_configured() is False


# ── 送信失敗の分岐 ──────────────────────────────────────────────────────────
class TestSendFailure:
    @pytest.mark.asyncio
    async def test_失敗してもFalseを返し例外を漏らさない(self, smtp_unreachable):
        assert mailer.is_configured() is True
        assert await mailer.send_email(to="user@example.test", subject="件名", body=BODY) is False

    @pytest.mark.asyncio
    async def test_失敗ログにも本文を載せない(self, smtp_unreachable, caplog):
        with caplog.at_level(logging.DEBUG, logger="app.core.email"):
            await mailer.send_email(to="user@example.test", subject="件名", body=BODY)
        text = caplog.text
        assert FAKE_TOKEN not in text
        assert RESET_URL not in text
        assert "テスト本文" not in text
        # 失敗したことは分かる必要がある
        assert "user@example.test" in text


# ── リセットフローの回帰 ────────────────────────────────────────────────────
class TestResetFlow:
    @pytest.fixture(autouse=True)
    def _no_rate_limit(self, monkeypatch):
        """レート制限を外す。

        /auth/forgot-password は 5回/60秒。ミドルウェアは DI を介さず
        実 Redis を直接見るため、カウントがテスト実行をまたいで残る。
        同じファイルを60秒以内に2回流すと 429 になり、落ちた理由が
        レート制限なのか本来の検証なのか分からなくなる。
        """
        monkeypatch.setattr(RateLimitMiddleware, "COSTLY_SUFFIXES", {}, raising=False)
        monkeypatch.setattr(settings, "RATE_LIMIT_REQUESTS", 10_000, raising=False)

    @pytest.mark.asyncio
    async def test_存在する場合もしない場合も同じ202を返す(
        self, client: AsyncClient, player_user, monkeypatch
    ):
        """アドレスの存在を応答から推測できないこと。"""
        async def _noop(**kwargs):
            return True

        monkeypatch.setattr(mailer, "send_email", _noop)

        known = await client.post(
            "/api/v1/auth/forgot-password", json={"email": player_user.email}
        )
        unknown = await client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "no-such-user@example.com"},
        )
        assert known.status_code == 202
        assert unknown.status_code == 202
        assert known.json() == unknown.json()

    @pytest.mark.asyncio
    async def test_不正なトークンは拒否される(self, client: AsyncClient):
        res = await client.post(
            "/api/v1/auth/reset-password",
            json={"token": "x" * 32, "new_password": "NewPassw0rd!"},
        )
        assert res.status_code == 401

    @pytest.mark.asyncio
    async def test_トークンは一度しか使えない(
        self, client: AsyncClient, player_user, monkeypatch
    ):
        sent: list[str] = []

        async def _capture(*, to: str, subject: str, body: str):
            sent.append(body)
            return True

        monkeypatch.setattr(mailer, "send_email", _capture)
        # 1インスタンスを使い回す。毎回作ると保存が共有されず意味がない。
        cache = _MemoryCache()
        monkeypatch.setitem(app.dependency_overrides, get_cache, lambda: cache)

        res = await client.post(
            "/api/v1/auth/forgot-password", json={"email": player_user.email}
        )
        assert res.status_code == 202
        assert sent, "送信処理が呼ばれていない"

        m = re.search(r"reset-password\?token=([\w\-]+)", sent[0])
        assert m, "本文からトークンを取り出せない"
        token = m.group(1)

        first = await client.post(
            "/api/v1/auth/reset-password",
            json={"token": token, "new_password": "NewPassw0rd!"},
        )
        assert first.status_code == 204

        second = await client.post(
            "/api/v1/auth/reset-password",
            json={"token": token, "new_password": "AnotherPass1!"},
        )
        assert second.status_code == 401, "同じトークンが二度使えてしまう"
