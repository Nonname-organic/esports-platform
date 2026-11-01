"""readiness の応答に例外の詳細を出さない。

`/health/ready` は未認証で到達する。DB・Redis の例外文字列には接続先や
ユーザー名が載るため、これを応答に入れると第三者が読めてしまう。
応答に出すのは "ok" / "error" だけにし、原因の切り分けは運用手順どおり
Neon / Upstash のダッシュボードで行う。

`readiness()` は `Depends` を使わず関数内で遅延 import しているため、
`app.dependency_overrides` では差し替えられない。import 先のモジュール属性を
monkeypatch する。

このファイルのテストは DB も Redis も使わない（すべてモック）。ただし
conftest.py の `schema` fixture が session-scoped autouse なので、
pytest を動かす時点でテスト用 Postgres が必要になる。
"""
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

# 例外メッセージに混ぜる目印。応答に出ていないことを確認するために使う。
# 実際の接続文字列はテストに書かない。
SENTINEL = "SENTINEL-DSN-MARKER"


class _FakeSession:
    async def execute(self, *_args, **_kwargs):
        return None


class _SessionCM:
    """AsyncSessionLocal() が返す async context manager の代わり。"""

    def __init__(self, session, raise_on_enter=False):
        self._session = session
        self._raise_on_enter = raise_on_enter

    async def __aenter__(self):
        if self._raise_on_enter:
            raise RuntimeError(f"connection refused {SENTINEL}")
        return self._session

    async def __aexit__(self, *_exc):
        return False


def _ok_session_local():
    return _SessionCM(_FakeSession())


def _failing_session_local():
    return _SessionCM(None, raise_on_enter=True)


class _FakeRedis:
    async def ping(self):
        return True


async def _ok_get_redis():
    return _FakeRedis()


async def _failing_get_redis():
    raise RuntimeError(f"connection refused {SENTINEL}")


@pytest.fixture
def readiness(monkeypatch):
    """DB / Redis の健全性を指定して /health/ready を叩く。"""

    async def _call(*, db_ok: bool, cache_ok: bool):
        monkeypatch.setattr(
            "app.core.database.AsyncSessionLocal",
            _ok_session_local if db_ok else _failing_session_local,
        )
        monkeypatch.setattr(
            "app.core.redis.get_redis",
            _ok_get_redis if cache_ok else _failing_get_redis,
        )
        # Host は TrustedHostMiddleware の許可リストに載っている localhost を使う
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://localhost"
        ) as client:
            return await client.get("/health/ready")

    return _call


@pytest.mark.asyncio
async def test_両方正常なら200でreadyを返す(readiness):
    res = await readiness(db_ok=True, cache_ok=True)
    assert res.status_code == 200
    assert res.json() == {"status": "ready", "checks": {"database": "ok", "cache": "ok"}}


@pytest.mark.asyncio
async def test_db障害時は503でdatabaseだけerrorになる(readiness):
    res = await readiness(db_ok=False, cache_ok=True)
    assert res.status_code == 503
    body = res.json()
    assert body["status"] == "degraded"
    # 完全一致。"error: ..." のような詳細付きを許さない
    assert body["checks"]["database"] == "error"
    assert body["checks"]["cache"] == "ok"


@pytest.mark.asyncio
async def test_redis障害時は503でcacheだけerrorになる(readiness):
    res = await readiness(db_ok=True, cache_ok=False)
    assert res.status_code == 503
    body = res.json()
    assert body["status"] == "degraded"
    assert body["checks"]["cache"] == "error"
    assert body["checks"]["database"] == "ok"


@pytest.mark.asyncio
async def test_両方障害なら503で両方errorになる(readiness):
    res = await readiness(db_ok=False, cache_ok=False)
    assert res.status_code == 503
    assert res.json() == {
        "status": "degraded",
        "checks": {"database": "error", "cache": "error"},
    }


@pytest.mark.security
@pytest.mark.asyncio
async def test_例外メッセージが応答本文に混ざらない(readiness):
    """これが B-1 の回帰テスト本体。

    例外に埋めた目印が応答のどこにも出ないことを、本文全体に対して見る。
    キーごとに assert すると、別のキーへ漏れた場合に気づけない。
    """
    for db_ok, cache_ok in ((False, True), (True, False), (False, False)):
        res = await readiness(db_ok=db_ok, cache_ok=cache_ok)
        assert SENTINEL not in res.text
        assert "connection refused" not in res.text
        assert "RuntimeError" not in res.text


@pytest.mark.asyncio
async def test_応答のキー構造を変えない(readiness):
    """status と checks.database / checks.cache という形を固定する。"""
    res = await readiness(db_ok=False, cache_ok=True)
    body = res.json()
    assert set(body) == {"status", "checks"}
    assert set(body["checks"]) == {"database", "cache"}
