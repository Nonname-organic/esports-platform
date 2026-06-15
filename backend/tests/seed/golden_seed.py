"""Golden Dataset — 決定論的・冪等。全ロール/全状態を1本で（最少データ最大カバレッジ）。

E2E / Visual / Load / 手動QA で共通利用する。固定UUID + ドメイン golden.test。
共通パスワード: Passw0rd!

実行（テストDB or デモDB を指す環境で）:
  python -m tests.seed.golden_seed
  （CIは DATABASE 環境変数で TEST DB を指してから実行）

冪等: 固定IDで存在チェック。再実行しても重複しない。
"""

import asyncio
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models.enums import (
    BOFormat,
    GameType,
    MatchStatus,
    MemberRole,
    NotificationChannel,
    NotificationType,
    RegistrationStatus,
    TournamentFormat,
    TournamentStatus,
    UserRole,
)
from app.models.discord import DiscordLink
from app.models.match import Match
from app.models.player import Player
from app.models.riot import RiotProfile
from app.models.scout import RecruitmentPost, ScoutProfile
from app.models.team import Team, TeamMember
from app.models.tournament import Notification, Tournament, TournamentRegistration
from app.models.user import User

PW = hash_password("Passw0rd!")
NOW = datetime(2026, 6, 15, 0, 0, tzinfo=timezone.utc)
D = timedelta(days=1)


def gid(suffix: str) -> uuid.UUID:
    """決定論UUID: 末尾suffix(<=12hex)で固定。"""
    return uuid.UUID(f"00000000-0000-0000-0000-{suffix:>012}")


async def _get(db, model, pk):
    return await db.get(model, pk)


async def seed() -> None:
    async with AsyncSessionLocal() as db:
        # ── Users / Roles ────────────────────────────────────────────────────
        users = {
            "admin": (gid("a1"), "admin@golden.test", "g_admin", UserRole.ADMIN),
            "organizer": (gid("a2"), "organizer@golden.test", "g_organizer", UserRole.ORGANIZER),
            "captain": (gid("a3"), "captain@golden.test", "g_captain", UserRole.PLAYER),
            "player": (gid("a4"), "player@golden.test", "g_player", UserRole.PLAYER),
            "retiree": (gid("a5"), "retiree@golden.test", "g_retiree", UserRole.PLAYER),
        }
        for _k, (uid, email, uname, role) in users.items():
            if not await _get(db, User, uid):
                db.add(User(id=uid, email=email, username=uname, hashed_password=PW,
                            role=role, is_active=True))
        await db.flush()

        # ── Players: 高レート / 新人 / 引退 ────────────────────────────────────
        players = {
            "captain": (gid("b1"), users["captain"][0], "GoldCaptain", "レディアント"),
            "player": (gid("b2"), users["player"][0], "GoldPlayer", "ダイヤモンド"),
            "rookie": (gid("b3"), None, "Rookie", "アイアン"),
            "retiree": (gid("b4"), users["retiree"][0], "Legend", "イモータル"),
        }
        for _k, (pid, owner_uid, ign, rank) in players.items():
            if not await _get(db, Player, pid):
                db.add(Player(id=pid, user_id=owner_uid, in_game_name=ign,
                              game=GameType.VALORANT, rank=rank))
        await db.flush()

        # ── Teams ─────────────────────────────────────────────────────────────
        teams = {
            "alpha": (gid("c1"), users["captain"][0], "Golden Alpha", "GA"),
            "bravo": (gid("c2"), users["organizer"][0], "Golden Bravo", "GB"),
        }
        for _k, (tid, owner_uid, name, tag) in teams.items():
            if not await _get(db, Team, tid):
                db.add(Team(id=tid, name=name, tag=tag, game=GameType.VALORANT,
                            owner_id=owner_uid, is_active=True))
        await db.flush()

        # captain を alpha のキャプテンに
        cm_id = gid("d1")
        if not await _get(db, TeamMember, cm_id):
            db.add(TeamMember(id=cm_id, team_id=teams["alpha"][0],
                              player_id=players["captain"][0], role=MemberRole.CAPTAIN,
                              joined_at=NOW))
        await db.flush()

        # ── Tournaments: 全ステータス ──────────────────────────────────────────
        tdefs = [
            ("e1", TournamentStatus.DRAFT, "Golden 下書き", None, None, None, None),
            ("e2", TournamentStatus.REGISTRATION_OPEN, "Golden 受付中", -2, 5, 7, 8),
            ("e3", TournamentStatus.ONGOING, "Golden 開催中", -10, -3, -1, 2),
            ("e4", TournamentStatus.COMPLETED, "Golden 完了", -20, -15, -10, -5),
            ("e5", TournamentStatus.CANCELLED, "Golden キャンセル", -8, -2, 1, 2),
        ]
        tour_ids = {}
        for suf, status, name, rs, re_, st, en in tdefs:
            tid = gid(suf)
            tour_ids[status] = tid
            if not await _get(db, Tournament, tid):
                db.add(Tournament(
                    id=tid, name=name, slug=f"golden-{suf}", game=GameType.VALORANT,
                    format=TournamentFormat.SINGLE_ELIMINATION, status=status,
                    organizer_id=users["organizer"][0], max_teams=8, min_teams=2,
                    is_public=True, prize_pool=10000, prize_currency="JPY",
                    registration_start_at=NOW + rs * D if rs is not None else None,
                    registration_end_at=NOW + re_ * D if re_ is not None else None,
                    start_at=NOW + st * D if st is not None else None,
                    end_at=NOW + en * D if en is not None else None,
                    rules={"bo_format": "BO1", "game_settings": {"server": "Tokyo"}},
                ))
        await db.flush()

        # 参加登録（開催中・完了に2チーム承認済み）
        reg_n = 0
        for status in (TournamentStatus.ONGOING, TournamentStatus.COMPLETED):
            for team_key in ("alpha", "bravo"):
                rid = gid(f"f{reg_n:x}")
                reg_n += 1
                if not await _get(db, TournamentRegistration, rid):
                    db.add(TournamentRegistration(
                        id=rid, tournament_id=tour_ids[status], team_id=teams[team_key][0],
                        status=RegistrationStatus.APPROVED, registered_at=NOW, updated_at=NOW))
        await db.flush()

        # ── Matches: 未開始/進行中/完了/棄権 ──────────────────────────────────
        mdefs = [
            ("90", MatchStatus.SCHEDULED, None),
            ("91", MatchStatus.ONGOING, None),
            ("92", MatchStatus.COMPLETED, teams["alpha"][0]),
            ("93", MatchStatus.FORFEIT, teams["bravo"][0]),
        ]
        for i, (suf, status, winner) in enumerate(mdefs):
            mid = gid(suf)
            if not await _get(db, Match, mid):
                db.add(Match(
                    id=mid, tournament_id=tour_ids[TournamentStatus.ONGOING],
                    team1_id=teams["alpha"][0], team2_id=teams["bravo"][0],
                    winner_id=winner, status=status, round_number=1, match_number=i + 1,
                    format=BOFormat.BO1,
                    started_at=NOW - 1 * D if status != MatchStatus.SCHEDULED else None,
                    ended_at=NOW if status in (MatchStatus.COMPLETED, MatchStatus.FORFEIT) else None,
                ))
        await db.flush()

        # ── Notifications: 未読/既読 ───────────────────────────────────────────
        for suf, read in (("a0", False), ("a1", False), ("a2", True)):
            nid = gid(f"7{suf}")
            if not await _get(db, Notification, nid):
                db.add(Notification(
                    id=nid, user_id=users["player"][0], type=NotificationType.GENERAL,
                    channel=NotificationChannel.IN_APP, title=f"通知 {suf}", body="golden",
                    is_read=read, created_at=NOW))
        await db.flush()

        # ── Scout: profile(募集中) + 募集post ─────────────────────────────────
        sp_id = gid("80")
        if not await _get(db, ScoutProfile, sp_id):
            db.add(ScoutProfile(id=sp_id, player_id=players["player"][0], type="player",
                                is_looking=True, created_at=NOW, updated_at=NOW))
        rp_id = gid("81")
        if not await _get(db, RecruitmentPost, rp_id):
            db.add(RecruitmentPost(
                id=rp_id, author_id=users["captain"][0], post_type="team_seeks",
                team_id=teams["alpha"][0], game=GameType.VALORANT.value,
                title="[GOLDEN] メンバー募集", description="golden recruitment",
                is_open=True, created_at=NOW, updated_at=NOW))
        await db.flush()

        # ── Discord: 接続済 ────────────────────────────────────────────────────
        dl_id = gid("82")
        if not await _get(db, DiscordLink, dl_id):
            db.add(DiscordLink(id=dl_id, user_id=users["captain"][0],
                               discord_user_id="111122223333", discord_username="golden#0001",
                               linked_at=NOW))
        await db.flush()

        # ── Riot: 同期済 / 未同期 ──────────────────────────────────────────────
        rp1 = gid("83")
        if not await _get(db, RiotProfile, rp1):
            db.add(RiotProfile(id=rp1, player_id=players["captain"][0], game_name="GoldCaptain",
                               tag_line="JP1", puuid="golden-puuid-synced", region="ap",
                               synced_at=NOW, created_at=NOW))
        rp2 = gid("84")
        if not await _get(db, RiotProfile, rp2):
            db.add(RiotProfile(id=rp2, player_id=players["player"][0], game_name="GoldPlayer",
                               tag_line="JP2", puuid=None, region="ap", created_at=NOW))

        await db.commit()
        print("GOLDEN SEED DONE ✅  users5/players4/teams2/tours5/matches4/notif3/scout/discord/riot")


if __name__ == "__main__":
    asyncio.run(seed())
