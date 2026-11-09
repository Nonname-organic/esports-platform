"""本番設定の検査（REQUIRE_STRONG_SECRETS）と、設定エラーで値を出さないことの回帰テスト。

本番は docker-compose.prod.yml が REQUIRE_STRONG_SECRETS=true を渡す。開発・CI は既定（false）のまま。
"""
import pytest
from pydantic import ValidationError

from app.core import config
from app.core.config import Settings, production_problems

STRONG_KEY = "k" * 16 + "Z9x2" * 6  # 40文字・見本の語を含まない
STRONG_PW = "Rq8vTt2LmZ0pW4yK"
DB_MSG = "DB のパスワードが未設定か既定値です"
KEY_MSG = "SECRET_KEY が見本・テスト用の値です"


def _settings(**kw):
    return Settings(**{"SECRET_KEY": STRONG_KEY, "DB_PASSWORD": STRONG_PW, "DATABASE_URL": None, **kw})


@pytest.mark.parametrize("pw", ["", "esports_pass", "password", "postgres"])
def test_空や既定値のDBパスワードを検出する(pw: str) -> None:
    assert production_problems(_settings(DB_PASSWORD=pw)) == [DB_MSG]


def test_DATABASE_URLの既定パスワードも検出する() -> None:
    s = _settings(DATABASE_URL="postgresql://esports_user:esports_pass@postgres:5432/esports_db")
    assert production_problems(s) == [DB_MSG]


@pytest.mark.parametrize("key", [
    "please-change-this-secret-key-000000000000",
    "ci-test-0000000000000000000000000000000000",
    "your-secret-key-at-least-32-characters-long",
])
def test_見本やテスト用のSECRET_KEYを検出する(key: str) -> None:
    assert production_problems(_settings(SECRET_KEY=key)) == [KEY_MSG]


def test_固有の値なら問題なし() -> None:
    assert production_problems(_settings()) == []


def test_有効なときは起動を拒否し値を出さない(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REQUIRE_STRONG_SECRETS", "true")
    monkeypatch.setenv("DB_PASSWORD", "esports_pass")
    monkeypatch.setenv("SECRET_KEY", "please-change-this-secret-key-000000000000")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(RuntimeError) as e:
        config.enforce_production_settings(Settings())
    msg = str(e.value)
    assert DB_MSG in msg and KEY_MSG in msg
    assert "esports_pass" not in msg and "please-change" not in msg


def test_無効なとき_開発とCI_は既定値でも起動できる(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REQUIRE_STRONG_SECRETS", "false")
    monkeypatch.setenv("DB_PASSWORD", "esports_pass")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    s = Settings()
    config.enforce_production_settings(s)  # 例外にならない
    assert s.DB_PASSWORD == "esports_pass"


def test_設定エラーの文面に入力値を出さない() -> None:
    with pytest.raises(ValidationError) as e:
        Settings(SECRET_KEY="short-secret-value")
    assert "short-secret-value" not in str(e.value)


@pytest.mark.asyncio
async def test_分析の書き出しは画像用バケットへ向かわない(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.workers.handlers import stats_export

    def no_session() -> None:
        raise AssertionError("S3 クライアントを作ってはいけない")

    monkeypatch.setattr(config.settings, "S3_BUCKET_NAME", "images-bucket")
    monkeypatch.setattr(config.settings, "ANALYTICS_EXPORT_BUCKET", "")
    monkeypatch.setattr(stats_export.aioboto3, "Session", no_session)
    assert await stats_export.handle_stats_export(None) == 0
