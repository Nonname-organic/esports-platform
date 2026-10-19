"""メール送信（SMTP）。

パスワードリセット等のトランザクションメールを送る最小構成。
SMTP_HOST 未設定の環境（ローカル・デモ）では送信せず、設定漏れとして
警告だけを残す。本文は出さない（リセットURLに使い捨てトークンが
入っているため）。ローカルでリセットフローを試すときは、API の
レスポンスではなく Redis の pwreset:* キーからトークンを取る。

送信は同期の smtplib をスレッドプールへ逃がす。専用ライブラリを増やす
ほどの規模ではない。
"""
from __future__ import annotations

import logging
import smtplib
from email.header import Header
from email.mime.text import MIMEText
from email.utils import formataddr

from starlette.concurrency import run_in_threadpool

from app.core.config import settings

logger = logging.getLogger(__name__)


def is_configured() -> bool:
    return bool(settings.SMTP_HOST)


def _send_sync(to: str, subject: str, body: str) -> None:
    message = MIMEText(body, "plain", "utf-8")
    message["Subject"] = Header(subject, "utf-8")
    message["From"] = formataddr(
        (str(Header(settings.MAIL_FROM_NAME, "utf-8")), settings.MAIL_FROM)
    )
    message["To"] = to

    if settings.SMTP_SSL:
        server: smtplib.SMTP = smtplib.SMTP_SSL(
            settings.SMTP_HOST, settings.SMTP_PORT, timeout=15
        )
    else:
        server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15)
        server.starttls()

    try:
        if settings.SMTP_USER:
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD or "")
        server.sendmail(settings.MAIL_FROM, [to], message.as_string())
    finally:
        server.quit()


async def send_email(to: str, subject: str, body: str) -> bool:
    """メールを1通送る。失敗しても例外は投げず False を返す。

    リセット要求のレスポンスは送信可否に関わらず同じにする必要がある
    （アドレスの存在が推測できてしまうため）ので、呼び出し側が結果で
    分岐しない前提の設計にしている。
    """
    if not is_configured():
        # 本文にはリセットURL（＝30分有効な使い捨てトークン）が入る。
        # ログは収集基盤や端末の履歴に残り、閲覧範囲もメールより広いので
        # 本文は出さない。設定漏れ自体は気づく必要があるため WARNING にする。
        logger.warning(
            "SMTP未設定のためメールは送信されません。宛先=%s 件名=%s",
            to, subject,
        )
        return False
    try:
        await run_in_threadpool(_send_sync, to, subject, body)
        return True
    except Exception:  # noqa: BLE001 - 送信失敗は呼び出し元の処理を止めない
        logger.exception("メール送信に失敗しました: 宛先=%s 件名=%s", to, subject)
        return False
