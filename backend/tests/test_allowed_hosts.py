"""Host ヘッダの許可リスト。

Render のヘルスチェックが 400 で弾かれてデプロイが失敗していた。原因は
TrustedHostMiddleware の許可リストを ALLOWED_ORIGINS（CORS の許可先）から
導出していたことで、フロントと違うホスト名で来る呼び出しが通らなかった。

同じ取り違えが戻らないよう、ALLOWED_HOSTS と ALLOWED_ORIGINS が別物である
ことと、設定が無いときに全許可へ倒れないことを固定する。
"""
import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings, settings
from app.main import _allowed_hosts, app

ALWAYS = {"localhost", "127.0.0.1", "api"}


@pytest.fixture
def hosts(monkeypatch):
    """ALLOWED_HOSTS / ALLOWED_ORIGINS を差し替えて _allowed_hosts() を呼ぶ。"""

    def _call(allowed_hosts, allowed_origins):
        monkeypatch.setattr(settings, "ALLOWED_HOSTS", allowed_hosts)
        monkeypatch.setattr(settings, "ALLOWED_ORIGINS", allowed_origins)
        return set(_allowed_hosts())

    return _call


def test_allowed_hosts_が設定されていればそれを使う(hosts):
    got = hosts(["axelia-api.onrender.com"], ["https://front.example.com"])
    assert "axelia-api.onrender.com" in got


def test_cors_の許可先は_host_許可リストに混ざらない(hosts):
    """責務分離。ALLOWED_HOSTS があるとき ALLOWED_ORIGINS は Host に影響しない。"""
    got = hosts(["axelia-api.onrender.com"], ["https://front.example.com"])
    assert "front.example.com" not in got


def test_allowed_origins_を変えても_host_許可リストは変わらない(hosts):
    a = hosts(["axelia-api.onrender.com"], ["https://a.example.com"])
    b = hosts(["axelia-api.onrender.com"], ["https://b.example.com"])
    assert a == b


def test_allowed_hosts_が空なら_allowed_origins_から導出する(hosts):
    """後方互換。未設定の既存環境（VPS・ローカル・CI）の挙動を変えない。"""
    got = hosts([], ["https://app.axelia-esports.jp"])
    assert "app.axelia-esports.jp" in got


def test_空でも全許可にはしない(hosts):
    got = hosts([], ["https://app.axelia-esports.jp"])
    assert "*" not in got
    # 導出元 + 常に許可する3つ、それ以上は増えない
    assert got == {"app.axelia-esports.jp"} | ALWAYS


@pytest.mark.parametrize(
    "allowed_hosts,allowed_origins",
    [
        (["axelia-api.onrender.com"], ["https://front.example.com"]),
        ([], ["https://front.example.com"]),
        ([], []),
    ],
)
def test_内部呼び出し用のホストは常に許可される(hosts, allowed_hosts, allowed_origins):
    """compose の healthcheck は localhost、frontend と worker は api で来る。"""
    assert ALWAYS <= hosts(allowed_hosts, allowed_origins)


def test_アスタリスクは拒否する(hosts):
    with pytest.raises(ValueError):
        hosts(["*"], [])


def test_空文字は無視する(hosts):
    got = hosts(["axelia-api.onrender.com", ""], [])
    assert "" not in got
    assert got == {"axelia-api.onrender.com"} | ALWAYS


def _settings(value):
    """環境変数から渡ってくる形を再現する。_env_file=None で手元の .env を混ぜない。"""
    return Settings(ALLOWED_HOSTS=value, _env_file=None)


def test_カンマ区切りの文字列をリストに分解する():
    """Render は ALLOWED_HOSTS を文字列で渡す。前後の空白は落とす。"""
    s = _settings("axelia-api.onrender.com, example.com")
    assert s.ALLOWED_HOSTS == ["axelia-api.onrender.com", "example.com"]


def test_単一のホスト名もリストになる():
    assert _settings("axelia-api.onrender.com").ALLOWED_HOSTS == ["axelia-api.onrender.com"]


def test_空文字なら空リストになる():
    """未設定と同じ扱いにして、ALLOWED_ORIGINS からの導出へ落とす。"""
    assert _settings("").ALLOWED_HOSTS == []


def test_カンマだけや空白だけの要素は捨てる():
    assert _settings("a.example.com, ,  ,b.example.com").ALLOWED_HOSTS == [
        "a.example.com",
        "b.example.com",
    ]


def test_リストで渡したときはそのまま通る():
    assert _settings(["a.example.com"]).ALLOWED_HOSTS == ["a.example.com"]


@pytest.fixture
def bare_client():
    """DB を使わない素のクライアント。Host 検証はルーティング前に走る。"""
    return lambda host: AsyncClient(
        transport=ASGITransport(app=app), base_url=f"http://{host}"
    )


@pytest.mark.asyncio
async def test_許可された_host_なら_health_が通る(bare_client):
    async with bare_client("localhost") as c:
        res = await c.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_不許可の_host_は_400_で弾かれる(bare_client):
    async with bare_client("evil.example.com") as c:
        res = await c.get("/health")
    assert res.status_code == 400
    assert "Invalid host header" in res.text


@pytest.mark.asyncio
async def test_弾かれるのはパスに依らない(bare_client):
    """`/` にルートは無いので、通れば 404。400 ならミドルウェアが止めている。"""
    async with bare_client("evil.example.com") as c:
        res = await c.head("/")
    assert res.status_code == 400
