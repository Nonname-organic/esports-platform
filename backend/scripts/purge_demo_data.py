"""外部公開に向けてデモデータを消す。

掲載していた AXELIA CUP / Test2 と、そこで使っていた架空のチーム・選手・
アカウントを消す。公開サイトを実データだけにするための一回限りの道具で、
通常運用で使うものではない。

残すもの:
  - 管理者 (role=admin)。所有チーム・主催大会・選手のいずれも持たないため
    公開画面には出ない。これを消すと /admin に誰も入れなくなる
  - 運用者本人の Gmail アカウントとその所有チーム。実在の人なので
    「要確認」のまま触らない
  - maps / alembic_version などのマスタ

消す順番は外部キーの向きで決まる。teams.owner_id と
tournaments.organizer_id は ON DELETE RESTRICT、match_results の
winner_id/loser_id も teams に対して RESTRICT なので、大会 → 選手 →
チーム → ユーザー の順に落とす必要がある。

ranking_snapshots は entity_id に外部キーが無く連動しないため、最後に
参照先を失った行を明示的に消す。

    docker compose exec -T api python /tmp/purge_demo_data.py          # ドライラン
    docker compose exec -T api python /tmp/purge_demo_data.py --apply  # 実行
"""
from __future__ import annotations

import asyncio
import sys

sys.path.insert(0, "/app")

from sqlalchemy import text  # noqa: E402

from app.core.database import AsyncSessionLocal  # noqa: E402

# 架空データの出所。example.com と .test はどちらも予約済みドメインで、
# 実在のアドレスと衝突しない。
DEMO_DOMAIN = "%@axelia-demo.example.com"
GOLDEN_DOMAIN = "%@golden.test"

TOURNAMENTS = ("AXELIA CUP", "Test2")


async def counts(db) -> dict[str, int]:
    tables = [
        "users", "tournaments", "teams", "players", "team_members",
        "matches", "match_games", "match_results", "player_match_stats",
        "tournament_registrations", "brackets", "rankings",
        "ranking_snapshots", "notifications", "players_lft",
        "riot_profiles", "scout_profiles", "recruitment_posts",
        "discord_links", "notification_preferences", "domain_events",
        "maps",
    ]
    out = {}
    for t in tables:
        out[t] = (await db.execute(text(f"SELECT count(*) FROM {t}"))).scalar() or 0
    return out


async def purge(db, apply: bool) -> None:
    names = ", ".join(f"'{n}'" for n in TOURNAMENTS)

    # 消す対象の id を先に確定させる。削除の途中で条件が変わらないようにする
    # （teams を消した後では「デモ所有のチーム」が引けなくなる）。
    demo_users = f"""
        SELECT id FROM users
         WHERE (email LIKE '{DEMO_DOMAIN}' OR email LIKE '{GOLDEN_DOMAIN}')
           AND role <> 'admin'
    """
    demo_teams = f"SELECT id FROM teams WHERE owner_id IN ({demo_users})"
    # user に紐づかない選手は、所属チームの持ち主で判定する。
    demo_players = f"""
        SELECT p.id FROM players p
         WHERE p.user_id IN ({demo_users})
            OR (p.user_id IS NULL AND EXISTS (
                  SELECT 1 FROM team_members tm
                   WHERE tm.player_id = p.id AND tm.team_id IN ({demo_teams})))
    """

    steps = [
        ("大会（試合・成績・登録・ブラケットが連鎖）",
         f"DELETE FROM tournaments WHERE name IN ({names})"),
        ("デモ選手（team_members・スカウト等が連鎖）",
         f"DELETE FROM players WHERE id IN ({demo_players})"),
        ("デモチーム",
         f"DELETE FROM teams WHERE id IN ({demo_teams})"),
        ("デモ・goldenのユーザー（管理者は除く）",
         f"DELETE FROM users WHERE id IN ({demo_users})"),
        ("参照先を失ったランキングスナップショット",
         """DELETE FROM ranking_snapshots rs
             WHERE NOT EXISTS (SELECT 1 FROM teams   t WHERE t.id = rs.entity_id)
               AND NOT EXISTS (SELECT 1 FROM players p WHERE p.id = rs.entity_id)"""),
    ]

    print("── 削除 " + ("実行" if apply else "ドライラン（ROLLBACK）") + " " + "─" * 30)
    total = 0
    for label, sql in steps:
        result = await db.execute(text(sql))
        n = result.rowcount or 0
        total += n
        print(f"   {label}: {n}行")
    print(f"   直接削除した行の合計: {total}（連鎖分は含まない）")


async def main() -> None:
    apply = "--apply" in sys.argv

    async with AsyncSessionLocal() as db:
        before = await counts(db)

        # 守り: 管理者が消えないことを先に確かめる。ここを踏み外すと
        # 管理画面に誰も入れなくなり、作り直すしかなくなる。
        admins = (await db.execute(text(
            "SELECT count(*) FROM users WHERE role = 'admin'"))).scalar()
        if not admins:
            print("中止: 管理者が0人です。先に管理者を用意してください")
            return

        await purge(db, apply)

        after = await counts(db)
        print("\n── テーブル別の増減 " + "─" * 30)
        for t in before:
            if before[t] != after[t]:
                print(f"   {t:<28} {before[t]:>5} → {after[t]:>5}  ({after[t] - before[t]:+})")

        # 消し終わった状態の健全性を確認する
        print("\n── 削除後の確認 " + "─" * 34)
        checks = {
            "管理者の人数": "SELECT count(*) FROM users WHERE role='admin'",
            "残るユーザー": "SELECT count(*) FROM users",
            "残る大会": "SELECT count(*) FROM tournaments",
            "残るチーム": "SELECT count(*) FROM teams",
            "残る選手": "SELECT count(*) FROM players",
            "マップ（マスタ・残すべき）": "SELECT count(*) FROM maps",
            "孤立したランキング": """
                SELECT count(*) FROM ranking_snapshots rs
                 WHERE NOT EXISTS (SELECT 1 FROM teams   t WHERE t.id = rs.entity_id)
                   AND NOT EXISTS (SELECT 1 FROM players p WHERE p.id = rs.entity_id)""",
            "孤立した所属": """
                SELECT count(*) FROM team_members tm
                 WHERE NOT EXISTS (SELECT 1 FROM teams t WHERE t.id = tm.team_id)
                    OR NOT EXISTS (SELECT 1 FROM players p WHERE p.id = tm.player_id)""",
        }
        for label, sql in checks.items():
            print(f"   {label}: {(await db.execute(text(sql))).scalar()}")

        print("\n── 残るユーザー ─────────────────────────────")
        for r in (await db.execute(text(
            "SELECT username, email, role::text FROM users ORDER BY role::text, username"
        ))).all():
            print("   " + " | ".join(str(x) for x in r))

        print("\n── 残るチーム ───────────────────────────────")
        rows = (await db.execute(text("""
            SELECT te.name, te.tag, split_part(u.email, chr(64), 1)
              FROM teams te LEFT JOIN users u ON u.id = te.owner_id
             ORDER BY te.created_at"""))).all()
        for r in rows:
            print("   " + " | ".join(str(x) for x in r))
        if not rows:
            print("   （なし）")

        if apply:
            await db.commit()
            print("\n>>> COMMIT しました")
        else:
            await db.rollback()
            print("\n>>> ROLLBACK しました（何も変わっていません）")


if __name__ == "__main__":
    asyncio.run(main())
