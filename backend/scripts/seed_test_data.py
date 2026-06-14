"""テストデータ投入スクリプト（手動実行）。

指定ユーザー(TARGET_EMAIL)が作成したものとして、チームと各ステータスの大会を投入する。
ステータスは日程ベースの自動更新ワーカーと矛盾しないよう、日付を状態に合わせて設定する。

実行（EC2、apiコンテナ内）:
  docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T api \
    python < ~/esports-platform/backend/scripts/seed_test_data.py

冪等: 同名のチーム/大会が既にあればスキップ（再実行可）。
"""

import asyncio
import re
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.enums import (
    GameType,
    RegistrationStatus,
    TournamentFormat,
    TournamentStatus,
)
from app.models.player import Player
from app.models.team import Team
from app.models.tournament import Tournament, TournamentRegistration
from app.models.user import User

# ← テストデータを紐付けるユーザーのメール（必要なら変更）
TARGET_EMAIL = "nennza062@gmail.com"


def slugify(name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:40] or "tournament"
    return f"{base}-{uuid.uuid4().hex[:6]}"


async def main() -> None:
    now = datetime.now(timezone.utc)
    D = timedelta(days=1)

    async with AsyncSessionLocal() as db:
        user = await db.scalar(select(User).where(User.email == TARGET_EMAIL))
        if not user:
            print(f"[ERROR] ユーザーが見つかりません: {TARGET_EMAIL}")
            print("        先にこのメールアドレスで会員登録するか、TARGET_EMAILを修正してください。")
            return
        print(f"[user] {user.email} ({user.id})")

        # ── プレイヤープロフィール（無ければ作成） ──────────────────────────────
        player = await db.scalar(select(Player).where(Player.user_id == user.id))
        if not player:
            player = Player(
                user_id=user.id, in_game_name=user.username or "TestPlayer",
                game=GameType.VALORANT, rank="ダイヤモンド", region="JP",
            )
            db.add(player)
            await db.flush()
            print("[player] created")
        else:
            print("[player] exists")

        # ── チーム ──────────────────────────────────────────────────────────────
        team_defs = [
            ("[TEST] Phantom Five", "PH5", GameType.VALORANT),
            ("[TEST] Radiant Wolves", "RDW", GameType.VALORANT),
            ("[TEST] Nova CS", "NOVA", GameType.CS2),
            ("[TEST] Apex Hunters", "APXH", GameType.APEX),
        ]
        teams = []
        for name, tag, game in team_defs:
            t = await db.scalar(select(Team).where(Team.name == name))
            if not t:
                t = Team(
                    name=name, tag=tag, game=game, owner_id=user.id, is_active=True,
                    country="Japan", description=f"{name}（テストデータ）",
                )
                db.add(t)
                await db.flush()
                print(f"[team] + {name}")
            else:
                print(f"[team] = {name}")
            teams.append(t)

        # ── 大会（各ステータス。日付は状態に整合させる） ──────────────────────────
        # (status, name, reg_start, reg_end, start, end)
        tour_defs = [
            (TournamentStatus.DRAFT, "[TEST] 下書き大会", None, None, None, None),
            (TournamentStatus.REGISTRATION_OPEN, "[TEST] 受付中大会",
             now - 2 * D, now + 5 * D, now + 7 * D, now + 8 * D),
            (TournamentStatus.REGISTRATION_CLOSED, "[TEST] 受付終了大会",
             now - 10 * D, now - 1 * D, now + 3 * D, now + 4 * D),
            (TournamentStatus.ONGOING, "[TEST] 開催中大会",
             now - 10 * D, now - 3 * D, now - 1 * D, now + 2 * D),
            (TournamentStatus.COMPLETED, "[TEST] 終了大会",
             now - 20 * D, now - 15 * D, now - 10 * D, now - 5 * D),
            (TournamentStatus.CANCELLED, "[TEST] 中止大会",
             now - 8 * D, now - 2 * D, now + 1 * D, now + 2 * D),
        ]
        tours = []
        for status, name, rs, re_, st, en in tour_defs:
            t = await db.scalar(select(Tournament).where(Tournament.name == name))
            if not t:
                t = Tournament(
                    name=name, slug=slugify(name), game=GameType.VALORANT,
                    format=TournamentFormat.SINGLE_ELIMINATION, status=status,
                    organizer_id=user.id, max_teams=16, min_teams=2,
                    registration_start_at=rs, registration_end_at=re_, start_at=st, end_at=en,
                    is_public=True, prize_pool=10000, prize_currency="JPY",
                    description=f"{name}（テストデータ）",
                    rules={
                        "bo_format": "BO1",
                        "game_settings": {
                            "server": "Tokyo", "ban_pick_format": "team_veto",
                            "map_pool": ["Ascent", "Bind", "Haven", "Lotus", "Sunset"],
                        },
                    },
                )
                db.add(t)
                await db.flush()
                print(f"[tournament] + {name} [{status.value}]")
            else:
                print(f"[tournament] = {name}")
            tours.append(t)

        # ── 参加登録（開催中・終了の大会に2チームを承認済みで） ───────────────────
        for tour in tours:
            if tour.status in (TournamentStatus.ONGOING, TournamentStatus.COMPLETED,
                               TournamentStatus.REGISTRATION_CLOSED):
                for team in teams[:2]:
                    exists = await db.scalar(
                        select(TournamentRegistration).where(
                            TournamentRegistration.tournament_id == tour.id,
                            TournamentRegistration.team_id == team.id,
                        )
                    )
                    if exists:
                        continue
                    db.add(TournamentRegistration(
                        tournament_id=tour.id, team_id=team.id,
                        status=RegistrationStatus.APPROVED,
                        registered_at=now, updated_at=now,
                    ))
                print(f"[register] {tour.name} <- 2 teams (approved)")

        await db.commit()
        print("DONE ✅  チーム4 / 大会6（下書き・受付中・受付終了・開催中・終了・中止）を投入しました。")


if __name__ == "__main__":
    asyncio.run(main())
