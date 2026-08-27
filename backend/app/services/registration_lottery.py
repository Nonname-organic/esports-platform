"""参加申請の抽選（approval_mode="lottery"）。

先着順(auto)と違い、受付中は当落を決めずに申請を審査中のまま溜め、
受付終了のタイミングで無作為に定員分を当選させる。

手動でのステータス変更（TournamentService.change_status）と、
日程による自動更新（workers.sqs_consumer.tournament_status_loop）の
両方から呼ぶため、サービス層に依存しない関数として切り出している。
"""

from __future__ import annotations

import random

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.events import Ev, EventEnvelope, EventService
from app.models.enums import RegistrationStatus
from app.models.tournament import Tournament, TournamentRegistration

APPROVAL_MODE_LOTTERY = "lottery"


async def run_registration_lottery(db: AsyncSession, tournament: Tournament) -> int:
    """抽選大会の当選チームを決定する。当選数を返す。

    - 対象は審査中(pending)の申請のみ。当選=approved / 落選=waitlisted。
    - 落選を rejected にしないのは、辞退が出た時に主催者が繰り上げできるようにするため。
    - 冪等: 審査中の申請が無ければ何もしない（再実行・二重呼び出しに安全）。
    """
    if tournament.approval_mode != APPROVAL_MODE_LOTTERY:
        return 0

    pending = list((await db.execute(
        select(TournamentRegistration).where(
            TournamentRegistration.tournament_id == tournament.id,
            TournamentRegistration.status == RegistrationStatus.PENDING,
        )
    )).scalars().all())
    if not pending:
        return 0

    approved_count = await db.scalar(
        select(func.count(TournamentRegistration.id)).where(
            TournamentRegistration.tournament_id == tournament.id,
            TournamentRegistration.status == RegistrationStatus.APPROVED,
        )
    ) or 0
    slots = max(tournament.max_teams - approved_count, 0)

    random.shuffle(pending)
    winners, losers = pending[:slots], pending[slots:]

    for reg in winners:
        reg.status = RegistrationStatus.APPROVED
    for reg in losers:
        reg.status = RegistrationStatus.WAITLISTED

    # 当選チームには手動承認時と同じイベントを発火し、通知経路を共通化する
    events = EventService(db)
    for reg in winners:
        await events.emit(EventEnvelope.build(
            type=Ev.TOURNAMENT_REGISTRATION_APPROVED,
            entity_type="tournament",
            entity_id=tournament.id,
            producer="tournament",
            after={"registration_id": str(reg.id), "team_id": str(reg.team_id), "lottery": True},
        ))

    await db.flush()
    return len(winners)
