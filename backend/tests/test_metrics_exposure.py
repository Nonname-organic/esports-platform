"""`/metrics` は既定で公開しない。

未認証で到達すると、パス別のリクエスト数・エラー率・レイテンシと、
`esports_app` の version（稼働中のイメージタグ）が読める。デモを
インターネットに出す構成では運用情報を晒すことになるので、
`EXPOSE_API_DOCS` と同じように既定で無効にしてある。

テスト上の制約: `app` はモジュールトップレベルで生成されるシングルトンで、
ルートは import 時に登録される。したがってテストの中で
`settings.EXPOSE_METRICS` を書き換えても、すでに登録済みのルート構成は
変わらない。ここで検証できるのは「いま動いているアプリの構成」だけである。

そのため skip では逃げず、`settings.EXPOSE_METRICS` の値ごとに期待値を
分岐させてある。どちらの環境でも必ず何かを検証するので、CI に
`EXPOSE_METRICS=true` が入っても検査が無音で消えることはない。
ただし有効化側は、その設定を入れた実行でしか通らない。
"""
import pytest
from httpx import ASGITransport, AsyncClient
from prometheus_client import CONTENT_TYPE_LATEST

from app.core.config import Settings, settings
from app.main import app

METRICS_PATH = "/metrics"


def _settings(**over) -> Settings:
    """`.env` を読まずに Settings を作る。実行環境の値に左右されないため。"""
    return Settings(_env_file=None, **over)


def _content_type_parts(value: str) -> tuple[str, set[str]]:
    """content-type を「メディアタイプ」と「charset 以外のパラメータ」に分ける。

    Starlette は media_type が `text/` で始まり `charset=` を含まないときだけ
    `; charset=utf-8` を足す（`starlette/responses.py` の `init_headers`）。
    `CONTENT_TYPE_LATEST` が charset を含むかはライブラリ側の都合なので、
    その1点だけ吸収して、メディアタイプと version は定数と一致を求める。

    文字列の前方一致で見ると `text/plaintext` も通ってしまうため、
    メディアタイプは区切り文字で切り出して丸ごと比較する。
    """
    media_type, *params = (p.strip().lower() for p in value.split(";"))
    return media_type, {p for p in params if p and not p.startswith("charset=")}


# ── 設定値 ────────────────────────────────────────────────────────────────────
# 証明するのは Settings クラスの既定値と型変換だけ。app には触れない。


def test_設定の既定値は無効():
    assert _settings().EXPOSE_METRICS is False


def test_設定として有効化できる():
    assert _settings(EXPOSE_METRICS=True).EXPOSE_METRICS is True


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("true", True), ("false", False), ("True", True), ("False", False)],
)
def test_設定の文字列はboolへ変換される(raw, expected):
    """環境変数は文字列で来る。"false" が True に化けないことを見る。"""
    assert _settings(EXPOSE_METRICS=raw).EXPOSE_METRICS is expected


# ── ルート登録 ────────────────────────────────────────────────────────────────
# 証明するのは「いまの app にルートが在るか無いか」。HTTP は介さない。


def _registered_paths() -> set[str]:
    """app に登録されたパス。Mount など path を持たないものは飛ばす。"""
    return {p for p in (getattr(r, "path", None) for r in app.routes) if p}


def test_ルート登録が設定と一致する():
    """設定が無効ならルートが無く、有効ならある。

    HTTP 応答のテストとは別に置いてある。404 はミドルウェアの変更など
    別の原因でも起こるので、登録の有無はここで直接見る。
    """
    if settings.EXPOSE_METRICS:
        assert METRICS_PATH in _registered_paths()
    else:
        assert METRICS_PATH not in _registered_paths()


# ── HTTP 応答 ─────────────────────────────────────────────────────────────────
# 証明するのは、ミドルウェアを通した実際の応答。


@pytest.fixture
def bare_client():
    """DB を使わないクライアントのファクトリ。

    毎回新しいものを作る。1つのテストで複数回使っても、閉じたクライアントを
    掴まない。Host は許可リストに載っている localhost を使う。
    """
    return lambda: AsyncClient(
        transport=ASGITransport(app=app), base_url="http://localhost"
    )


@pytest.mark.security
@pytest.mark.asyncio
async def test_metrics_の応答が設定と一致する(bare_client):
    """無効なら 404 で本文も漏らさない。有効なら Prometheus 形式を返す。

    skip しないので、どちらの環境でも必ず検証が走る。
    """
    async with bare_client() as c:
        res = await c.get(METRICS_PATH)

    if settings.EXPOSE_METRICS:
        assert res.status_code == 200
        # charset の有無だけ許容し、メディアタイプと version は定数と一致を求める
        expected_type, expected_params = _content_type_parts(CONTENT_TYPE_LATEST)
        actual_type, actual_params = _content_type_parts(res.headers["content-type"])
        assert actual_type == expected_type
        assert actual_params == expected_params
        # Prometheus のテキスト形式。HELP 行と、このアプリ固有の指標名を見る
        assert "# HELP" in res.text
        assert "http_requests_total" in res.text
    else:
        assert res.status_code == 404
        # 404 でも本文は見る。別経路から中身が漏れていないこと
        assert "http_requests_total" not in res.text
        assert "esports_app" not in res.text
        assert "# HELP" not in res.text


@pytest.mark.asyncio
async def test_ヘルスチェックに影響しない(bare_client):
    """/metrics の登録を切り替えても他のルートは変わらない。"""
    async with bare_client() as c:
        live = await c.get("/health/live")
    async with bare_client() as c:
        health = await c.get("/health")

    assert live.status_code == 200
    assert live.json() == {"status": "ok"}
    assert health.status_code == 200
    assert health.json()["status"] == "ok"
