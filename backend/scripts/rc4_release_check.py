"""RC4 の公開の確認（Q29 (a)・Q31・Q32）。件数だけを出し、条件を満たさなければ終了コード 1 で終わる。

Deploy の workflow が、マイグレーションの開始の時刻を --since に渡して、入れ替えと readiness の後に
API のコンテナの中で実行する:

    python scripts/rc4_release_check.py --since 2026-11-11T10:00:00Z

止める条件（1 件でもあれば失敗。切り戻しの手順へ進む）:
  - DB の版が 032 でない
  - --since の後に開始された、名簿の無い旧方式（legacy）の大会の試合（旧コードが動いていた間に始まったもの）
  - 進行中の legacy の大会の試合・開催中の legacy の大会
  - --since の後に作られた legacy の大会（トリガーが効いていない）

個人を特定する値と接続先は出さない（Q32）。
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # コンテナでは /app

from sqlalchemy import text  # noqa: E402

EXPECTED_REVISION = "032"

# (名前, SQL, 止める条件か)
CHECKS = (
    ("legacy_matches_started_since",
     "SELECT count(*) FROM matches m JOIN tournaments t ON t.id = m.tournament_id "
     "WHERE t.roster_mode = 'legacy' AND m.started_at >= :since", True),
    ("legacy_matches_ongoing",
     "SELECT count(*) FROM matches m JOIN tournaments t ON t.id = m.tournament_id "
     "WHERE t.roster_mode = 'legacy' AND m.status = 'ongoing'", True),
    ("legacy_tournaments_ongoing",
     "SELECT count(*) FROM tournaments WHERE roster_mode = 'legacy' AND status = 'ongoing'", True),
    ("legacy_tournaments_created_since",
     "SELECT count(*) FROM tournaments WHERE roster_mode = 'legacy' AND created_at >= :since", True),
    # 参考（止めない）: 主催者に切り替えを案内する未開始の legacy の大会、確認待ちの所属、閉じた重複
    ("legacy_tournaments_not_started",
     "SELECT count(*) FROM tournaments WHERE roster_mode = 'legacy' "
     "AND status IN ('draft', 'registration_open', 'registration_closed', 'check_in')", False),
    ("memberships_unconfirmed_active",
     "SELECT count(*) FROM team_members WHERE consent = 'unconfirmed' AND left_at IS NULL", False),
    ("membership_duplicates_closed", "SELECT count(*) FROM rc4_membership_dedup_backup", False),
)


async def run_checks(db, since: datetime) -> tuple[dict, list[str]]:
    """({名前: 値}, [止める理由])。db は AsyncSession か AsyncConnection。"""
    revision = (await db.execute(text("SELECT version_num FROM alembic_version"))).scalar()
    values: dict = {"db_revision": revision}
    problems = [] if revision == EXPECTED_REVISION else [f"db_revision={revision}"]
    for name, sql, blocking in CHECKS:
        n = int((await db.execute(text(sql), {"since": since})).scalar() or 0)
        values[name] = n
        if blocking and n:
            problems.append(f"{name}={n}")
    return values, problems


def parse_since(value: str) -> datetime:
    since = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    return since if since.tzinfo else since.replace(tzinfo=timezone.utc)


async def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--since", required=True, help="マイグレーションを始めた時刻（ISO 8601。UTC）")
    args = parser.parse_args(argv)
    from app.core.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        values, problems = await run_checks(db, parse_since(args.since))
    for name, value in values.items():
        print(f"rc4_release_check {name}={value}")
    if problems:
        print("rc4_release_check RESULT=FAIL " + " ".join(problems))
        return 1
    print("rc4_release_check RESULT=PASS")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
