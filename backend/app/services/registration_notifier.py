"""参加承認の通知（手動承認・抽選当選の共通経路）。

承認されたチームのメンバー全員のAXELIAアカウントへ、大会Discordサーバーの
招待リンクを同封した通知を送る。NotificationService 側で

  - アプリ内通知（必ず届く）
  - WebSocket push（オンラインなら即時）
  - Discord連携済みユーザーには bot 経由のDM

まで面倒を見るため、ここでは対象ユーザーの列挙と文面の組み立てだけを行う。
Webhook はチャンネル投稿専用で個人には送れないため、個人への招待の到達は
この経路が担う。
"""
from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.discord_invite import normalize_discord_invite
from app.core.redis import RedisCache
from app.models.player import Player
from app.models.team import Team, TeamMember
from app.models.tournament import Tournament

logger = logging.getLogger(__name__)


async def _team_user_ids(db: AsyncSession, team_id: uuid.UUID) -> set[uuid.UUID]:
    """チームに紐づくAXELIAユーザー（オーナー + 在籍メンバー）を集める。"""
    user_ids: set[uuid.UUID] = set()

    owner_id = await db.scalar(select(Team.owner_id).where(Team.id == team_id))
    if owner_id:
        user_ids.add(owner_id)

    rows = (await db.execute(
        select(Player.user_id)
        .join(TeamMember, TeamMember.player_id == Player.id)
        .where(
            TeamMember.team_id == team_id,
            TeamMember.left_at.is_(None),
            Player.user_id.is_not(None),
        )
    )).scalars().all()
    user_ids.update(rows)
    return user_ids


async def notify_registration_approved(
    db: AsyncSession,
    cache: RedisCache,
    tournament: Tournament,
    team_id: uuid.UUID,
    *,
    by_lottery: bool = False,
) -> int:
    """承認されたチームのメンバーへ通知を送る。送った件数を返す。

    通知の失敗で承認処理を巻き戻さないため、例外はここで握りつぶして
    ログに残すだけにする。
    """
    try:
        from app.services.notification_service import NotificationService

        invite = normalize_discord_invite(
            ((tournament.rules or {}).get("discord") or {}).get("invite_url")
        )

        from app.notifications import templates

        date_text = templates.format_tournament_date(tournament.start_at)
        if invite:
            title, body = templates.approved_with_discord(
                tournament.name, date_text, invite)
        else:
            title, body = templates.approved_without_discord(
                tournament.name, date_text)

        # 開いたときの遷移先は大会ページにする。Discord へは本文を読んだうえで
        # ボタンから明示的に飛ばす（通知を押した瞬間に外部サイトへ送らない）。
        action_url = f"/tournaments/{tournament.id}"

        service = NotificationService(db, cache)
        sent = 0
        for user_id in await _team_user_ids(db, team_id):
            await service.create(
                user_id=user_id,
                ntype="application_approved",
                title=title,
                body=body,
                action_url=action_url,
                metadata={
                    "tournament_id": str(tournament.id),
                    "team_id": str(team_id),
                    "discord_invite": invite or None,
                },
            )
            sent += 1
        return sent
    except Exception:  # noqa: BLE001 - 通知失敗は承認処理を妨げない
        logger.exception(
            "承認通知の送信に失敗しました tournament=%s team=%s",
            tournament.id, team_id,
        )
        return 0


async def notify_registration_waitlisted(
    db: AsyncSession,
    cache: RedisCache,
    tournament: Tournament,
    team_id: uuid.UUID,
) -> int:
    """抽選に外れたチームへ通知を送る。送った件数を返す。

    外れたチームは削除せず補欠として残り、辞退が出れば繰り上げられる。
    結果が分からないまま放置されるのが一番困るので、外れた側にも必ず知らせる。
    """
    try:
        from app.notifications import templates
        from app.services.notification_service import NotificationService

        date_text = templates.format_tournament_date(tournament.start_at)
        title, body = templates.waitlisted(tournament.name, date_text)

        service = NotificationService(db, cache)
        sent = 0
        for user_id in await _team_user_ids(db, team_id):
            await service.create(
                user_id=user_id,
                ntype="application_rejected",
                title=title,
                body=body,
                action_url=f"/tournaments/{tournament.id}",
                metadata={
                    "tournament_id": str(tournament.id),
                    "team_id": str(team_id),
                },
            )
            sent += 1
        return sent
    except Exception:  # noqa: BLE001 - 通知失敗は抽選処理を妨げない
        logger.exception(
            "補欠通知の送信に失敗しました tournament=%s team=%s",
            tournament.id, team_id,
        )
        return 0
