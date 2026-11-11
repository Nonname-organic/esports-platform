"""メール送信のログに宛先アドレス（個人情報）を残さないことの回帰テスト。"""
import logging
import smtplib

import pytest

from app.core import email

ADDRESS = "taro.yamada@example.com"


@pytest.fixture(autouse=True)
def _logger_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    # テスト開始時に同じプロセスで alembic を流しており、その fileConfig が既存ロガーを無効にする
    monkeypatch.setattr(email.logger, "disabled", False)


@pytest.mark.asyncio
async def test_SMTP未設定でも宛先アドレスを記録しない(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    monkeypatch.setattr(email, "is_configured", lambda: False)
    caplog.set_level(logging.INFO, logger=email.logger.name)
    assert await email.send_email(ADDRESS, "パスワード再設定", "本文") is False
    assert "taro.yamada" not in caplog.text
    assert "example.com" in caplog.text


@pytest.mark.asyncio
async def test_送信失敗時も宛先アドレスを記録しない(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    def refuse(*_: object) -> None:
        raise smtplib.SMTPRecipientsRefused({ADDRESS: (550, b"no such user")})

    monkeypatch.setattr(email, "is_configured", lambda: True)
    monkeypatch.setattr(email, "_send_sync", refuse)
    caplog.set_level(logging.INFO, logger=email.logger.name)
    assert await email.send_email(ADDRESS, "パスワード再設定", "本文") is False
    assert "taro.yamada" not in caplog.text
    assert "SMTPRecipientsRefused" in caplog.text
