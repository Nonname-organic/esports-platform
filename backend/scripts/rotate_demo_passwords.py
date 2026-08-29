"""デモアカウントのパスワードを無効化する（公開前の必須作業）。

デモ用に作成したアカウントはパスワードがリポジトリ既知の値のままで、
公開すると誰でもチーム管理者としてログインできてしまう。各アカウントの
パスワードをランダム値に差し替えてログイン不能にする（データは残るため、
大会・チームの表示には影響しない）。

    docker compose exec api python scripts/rotate_demo_passwords.py [--yes]

--yes を付けない場合は対象を表示するだけ（ドライラン）。
"""
from __future__ import annotations

import asyncio
import secrets
import sys

sys.path.insert(0, "/app")

from sqlalchemy import text  # noqa: E402

from app.core.database import AsyncSessionLocal  # noqa: E402
from app.core.security import hash_password  # noqa: E402

# ローテーション対象: デモ用に一括作成したアカウントのドメイン/アドレス。
# 実際の運用者アカウント（Gmail等）は対象にしない
TARGET_PATTERNS = [
    "%@axelia-demo.example.com",
    "%@golden.test",
]


async def main() -> None:
    apply = "--yes" in sys.argv
    async with AsyncSessionLocal() as db:
        rows = []
        for pattern in TARGET_PATTERNS:
            rows += (await db.execute(text(
                "SELECT id, email FROM users WHERE email LIKE :p ORDER BY email"
            ), {"p": pattern})).all()

        if not rows:
            print("対象アカウントはありません")
            return

        print(f"対象: {len(rows)}件")
        for _id, email in rows:
            print(f"  {email}")

        if not apply:
            print("\nドライランです。実行するには --yes を付けてください")
            return

        for user_id, _email in rows:
            await db.execute(text(
                "UPDATE users SET hashed_password = :pw, updated_at = now()"
                " WHERE id = :id"
            ), {"pw": hash_password(secrets.token_urlsafe(24)), "id": user_id})
        await db.commit()
        print(f"\n{len(rows)}件のパスワードをランダム化しました（ログイン不能）")


asyncio.run(main())
