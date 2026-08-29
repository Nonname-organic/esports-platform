"""SMTP設定の疎通確認。

.env にSMTP設定を入れたあと、実際にメールが届くかを1通送って確かめる。

    docker compose exec api python scripts/send_test_email.py 宛先アドレス

未設定の場合は、何をどこに設定すればよいかを表示して終了する。
"""
from __future__ import annotations

import asyncio
import sys

sys.path.insert(0, "/app")

from app.core import email as mailer  # noqa: E402
from app.core.config import settings  # noqa: E402


async def main() -> int:
    if len(sys.argv) < 2 or "@" not in sys.argv[1]:
        print("使い方: python scripts/send_test_email.py 宛先アドレス")
        return 1
    to = sys.argv[1]

    print("── 現在の設定 ─────────────────────────────")
    print(f"  SMTP_HOST : {settings.SMTP_HOST or '(未設定)'}")
    print(f"  SMTP_PORT : {settings.SMTP_PORT}")
    print(f"  SMTP_USER : {settings.SMTP_USER or '(未設定)'}")
    print(f"  SMTP_PASS : {'設定済み' if settings.SMTP_PASSWORD else '(未設定)'}")
    print(f"  MAIL_FROM : {settings.MAIL_FROM}")
    print(f"  リンク基点: {settings.FRONTEND_BASE_URL}")
    print()

    if not mailer.is_configured():
        print("SMTP_HOST が未設定です。backend/.env のSMTPブロックに値を入れ、")
        print("docker compose restart api worker で反映してから再実行してください。")
        print("（未設定でもパスワードリセット自体は動き、本文はAPIログに出ます）")
        return 1

    print(f"{to} へテストメールを送信します…")
    ok = await mailer.send_email(
        to=to,
        subject="【AXELIA】メール設定の確認",
        body=(
            "このメールが届いていれば、SMTP設定は正しく機能しています。\n\n"
            f"送信元: {settings.MAIL_FROM}\n"
            f"リセットリンクの基点: {settings.FRONTEND_BASE_URL}\n\n"
            "AXELIA"
        ),
    )
    if ok:
        print("送信に成功しました。受信箱（迷惑メールフォルダも）を確認してください。")
        return 0
    print("送信に失敗しました。上のAPIログ（docker compose logs api）に詳細が出ています。")
    print("よくある原因: パスワード誤り / Gmailでアプリパスワード未発行 / ポート番号違い")
    return 1


sys.exit(asyncio.run(main()))
