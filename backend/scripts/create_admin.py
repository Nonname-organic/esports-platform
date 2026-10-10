"""管理者アカウントを作る。

管理画面(/admin)は admin ロールでしか開けない。デモ環境には admin が
1人もおらず、ダッシュボードも監査ログも誰も見られない状態だったため、
そこを埋めるための道具。

パスワードはこのファイルにも引数にも書かない。指定が無ければ生成して
標準出力に1回だけ出す。出力はリポジトリに入れず、手元の安全な場所に
控えること（リポジトリは公開されている）。

    docker compose exec api python scripts/create_admin.py \
        --email admin@example.com --username admin

既に同じメールのユーザーが居る場合は、ロールを admin に上げるだけに
留める（パスワードは変えない）。
"""
from __future__ import annotations

import argparse
import asyncio
import secrets
import string
import sys
import uuid

sys.path.insert(0, "/app")

from sqlalchemy import select  # noqa: E402

from app.core.database import AsyncSessionLocal  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.models.enums import UserRole  # noqa: E402
from app.models.user import User  # noqa: E402

# 紛らわしい字（0/O, 1/l/I）を除く。口頭やコピーで取り違えないようにする
_ALPHABET = (
    "".join(c for c in string.ascii_letters + string.digits if c not in "0O1lI")
    + "!@#%+=?"
)


def generate_password(length: int = 24) -> str:
    return "".join(secrets.choice(_ALPHABET) for _ in range(length))


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", required=True)
    parser.add_argument("--username", required=True)
    parser.add_argument(
        "--password",
        help="省略時は生成する。コマンド履歴に残るので通常は省略すること",
    )
    args = parser.parse_args()

    async with AsyncSessionLocal() as db:
        existing = (await db.execute(
            select(User).where(User.email == args.email)
        )).scalar_one_or_none()

        if existing is not None:
            if existing.role == UserRole.ADMIN:
                print(f"既に管理者です: {existing.email}")
                return
            previous = existing.role.value
            existing.role = UserRole.ADMIN
            await db.commit()
            print(f"ロールを変更しました: {existing.email}  {previous} -> admin")
            print("※ パスワードは変更していません")
            return

        password = args.password or generate_password()
        user = User(
            id=uuid.uuid4(),
            email=args.email,
            username=args.username,
            hashed_password=hash_password(password),
            role=UserRole.ADMIN,
            is_active=True,
            is_email_verified=True,
        )
        db.add(user)
        await db.commit()

        print(f"作成しました: {args.email} (username={args.username}) role=admin")
        if not args.password:
            print("PASSWORD=" + password)
            print("※ この値はここにしか出ない。控えたうえで画面から変更すること")


if __name__ == "__main__":
    asyncio.run(main())
