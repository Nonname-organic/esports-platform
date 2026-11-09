"""プロフィール（パスワード・メール）の更新と、メール・Discord 通知の送信。

外部への送信はすべて差し替え、宛先と内容が正しく組み立てられることだけを見る。
"""
import pytest
from httpx import AsyncClient

from app.api.v1 import auth as auth_api
from app.core import email as mailer
from app.core.security import issue_tokens
from app.workers.handlers import notification as notif
from tests import factories as f
from tests.conftest import auth_headers


def _h(user) -> dict:
    return auth_headers(issue_tokens(user)[0])


class TestProfileUpdate:
    @pytest.mark.asyncio
    async def test_パスワード変更は現パスワードと強度を確かめる(self, client: AsyncClient, db):
        user = await f.make_user(db, email="pw@example.com", password="Passw0rd1")
        url = "/api/v1/auth/password"
        assert (await client.patch(url, headers=_h(user), json={
            "current_password": "wrong", "new_password": "NewPassw0rd"})).status_code == 401
        assert (await client.patch(url, headers=_h(user), json={
            "current_password": "Passw0rd1", "new_password": "weakpassword"})).status_code == 422
        assert (await client.patch(url, headers=_h(user), json={
            "current_password": "Passw0rd1", "new_password": "NewPassw0rd"})).status_code == 204
        login = await client.post("/api/v1/auth/login", json={"email": "pw@example.com", "password": "NewPassw0rd"})
        assert login.status_code == 200, login.text

    @pytest.mark.asyncio
    async def test_メール変更はパスワード確認と重複チェックがある(self, client: AsyncClient, db):
        user = await f.make_user(db, email="old@example.com", password="Passw0rd1")
        await f.make_user(db, email="taken@example.com")
        url = "/api/v1/auth/email"
        assert (await client.patch(url, headers=_h(user), json={
            "password": "wrong", "new_email": "new@example.com"})).status_code == 401
        assert (await client.patch(url, headers=_h(user), json={
            "password": "Passw0rd1", "new_email": "taken@example.com"})).status_code == 400
        res = await client.patch(url, headers=_h(user), json={"password": "Passw0rd1", "new_email": "new@example.com"})
        assert res.status_code == 200 and res.json()["email"] == "new@example.com"


class TestNotificationsDelivery:
    @pytest.mark.asyncio
    async def test_パスワード再設定メールは登録アドレスにだけ送る(self, client: AsyncClient, db, monkeypatch):
        sent = []

        async def fake_send(to, subject, body):
            sent.append((to, subject, body))
            return True

        monkeypatch.setattr(auth_api.mailer, "send_email", fake_send)
        await f.make_user(db, email="reset@example.com")
        res = await client.post("/api/v1/auth/forgot-password", json={"email": "reset@example.com"})
        assert res.status_code == 202
        res = await client.post("/api/v1/auth/forgot-password", json={"email": "nobody@example.com"})
        assert res.status_code == 202  # 未登録でも同じ応答（登録有無を漏らさない）
        assert len(sent) == 1 and sent[0][0] == "reset@example.com"
        assert "/reset-password?token=" in sent[0][2]

    @pytest.mark.asyncio
    async def test_SMTP設定時は送信処理へ宛先と件名が渡る(self, monkeypatch):
        calls = []
        monkeypatch.setattr(mailer.settings, "SMTP_HOST", "smtp.example.invalid")
        monkeypatch.setattr(mailer, "_send_sync", lambda to, subject, body: calls.append((to, subject)))
        assert await mailer.send_email("to@example.com", "件名", "本文") is True
        assert calls == [("to@example.com", "件名")]

    @pytest.mark.asyncio
    async def test_Discord通知はWebhookへ送りそれ以外の宛先には送らない(self, monkeypatch):
        posted = []

        class FakeResponse:
            def raise_for_status(self): pass

        class FakeClient:
            def __init__(self, *a, **k): pass
            async def __aenter__(self): return self
            async def __aexit__(self, *a): return False
            async def post(self, url, json):
                posted.append((url, json))
                return FakeResponse()

        monkeypatch.setattr(notif.httpx, "AsyncClient", FakeClient)
        ok = "https://discord.com/api/webhooks/1/abc"
        await notif.handle_notification({"channel": "discord", "webhook_url": ok, "content": "試合開始"}, None, None)
        await notif.handle_notification(
            {"channel": "discord", "webhook_url": "http://169.254.169.254/latest", "content": "x"}, None, None)
        assert posted == [(ok, {"content": "試合開始"})]
