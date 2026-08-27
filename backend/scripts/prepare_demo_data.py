"""
デモ公開用にデータベースを整える。

1. 開発中に作ったテスト痕跡（Golden 各種 / RP検証カップ / Test Team）を削除する
2. デモチームに選手を登録する
3. AXELIA CUP を最後まで進行させ、試合結果と選手成績を作る

3で作るのはサンプルデータであり実在の大会記録ではない。画面上ではデモ告知
バナー（NEXT_PUBLIC_DEMO_MODE）でその旨を明示している。

    docker compose exec api python scripts/prepare_demo_data.py [--yes]

--yes を付けない場合は削除対象を表示するだけで終了する（ドライラン）。
"""
from __future__ import annotations

import asyncio
import random
import sys
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, text

from app.core.database import AsyncSessionLocal
from app.core.redis import RedisCache, get_redis
from app.models.enums import MatchStatus, TournamentStatus
from app.models.match import Match
from app.models.tournament import Tournament
from app.models.user import User
from app.schemas.match import GameStatsCreate, MatchResultCreate, PlayerStatsCreate
from app.services.match import MatchService
from app.services.ranking import RankingService

# 再現性のある結果にする（実行のたびに数字が変わると差分の確認がしづらい）
random.seed(20260828)

TEST_TOURNAMENTS = ("Golden 下書き", "Golden 完了", "Golden キャンセル",
                    "Golden 受付中", "Golden 開催中", "RP検証カップ")
TEST_TEAMS = ("Golden Alpha", "Golden Bravo", "Test Team 3", "Test Team 4")

AGENTS = ["Jett", "Raze", "Reyna", "Phoenix", "Yoru", "Neon", "Iso",
          "Sova", "Breach", "Skye", "KAY/O", "Fade", "Gekko",
          "Brimstone", "Viper", "Omen", "Astra", "Harbor", "Clove",
          "Sage", "Cypher", "Killjoy", "Chamber", "Deadlock", "Vyse"]

# デモ選手名の素材。チームタグと組み合わせて生成する
NAME_PARTS_A = ["Kai", "Ren", "Sora", "Yuki", "Haru", "Rei", "Jin", "Aki",
                "Riku", "Nao", "Shin", "Tama", "Kuro", "Shiro", "Mizu"]
NAME_PARTS_B = ["blade", "storm", "fox", "hawk", "wolf", "drift", "spark",
                "edge", "flare", "frost", "raven", "quake", "veil", "dash"]


def log(message: str) -> None:
    print(message, flush=True)


async def cleanup_test_data(db, apply: bool) -> None:
    log("── テスト痕跡の削除 " + "─" * 44)

    rows = (await db.execute(text(
        "SELECT name FROM tournaments WHERE name = ANY(:names)"
    ), {"names": list(TEST_TOURNAMENTS)})).scalars().all()
    team_rows = (await db.execute(text(
        "SELECT name FROM teams WHERE name = ANY(:names)"
    ), {"names": list(TEST_TEAMS)})).scalars().all()

    log(f"  削除対象の大会: {rows or 'なし'}")
    log(f"  削除対象のチーム: {team_rows or 'なし'}")
    if not apply:
        return

    # 試合→大会の順に消す。外部キーのカスケード設定に依存しないよう明示的に辿る
    await db.execute(text("""
        DELETE FROM player_match_stats WHERE match_game_id IN (
            SELECT mg.id FROM match_games mg JOIN matches m ON m.id = mg.match_id
            JOIN tournaments t ON t.id = m.tournament_id WHERE t.name = ANY(:names))
    """), {"names": list(TEST_TOURNAMENTS)})
    for table, column in (("match_games", "match_id"), ("ban_picks", "match_id"),
                          ("match_results", "match_id")):
        await db.execute(text(f"""
            DELETE FROM {table} WHERE {column} IN (
                SELECT m.id FROM matches m JOIN tournaments t ON t.id = m.tournament_id
                WHERE t.name = ANY(:names))
        """), {"names": list(TEST_TOURNAMENTS)})
    await db.execute(text("""
        DELETE FROM matches WHERE tournament_id IN
            (SELECT id FROM tournaments WHERE name = ANY(:names))
    """), {"names": list(TEST_TOURNAMENTS)})
    await db.execute(text("""
        DELETE FROM tournament_registrations WHERE tournament_id IN
            (SELECT id FROM tournaments WHERE name = ANY(:names))
    """), {"names": list(TEST_TOURNAMENTS)})
    await db.execute(text("""
        DELETE FROM brackets WHERE tournament_id IN
            (SELECT id FROM tournaments WHERE name = ANY(:names))
    """), {"names": list(TEST_TOURNAMENTS)})
    await db.execute(text(
        "DELETE FROM tournaments WHERE name = ANY(:names)"
    ), {"names": list(TEST_TOURNAMENTS)})

    # テストチーム（残った参照ごと）
    await db.execute(text("""
        DELETE FROM team_members WHERE team_id IN
            (SELECT id FROM teams WHERE name = ANY(:names))
    """), {"names": list(TEST_TEAMS)})
    await db.execute(text("""
        DELETE FROM tournament_registrations WHERE team_id IN
            (SELECT id FROM teams WHERE name = ANY(:names))
    """), {"names": list(TEST_TEAMS)})
    await db.execute(text(
        "DELETE FROM teams WHERE name = ANY(:names)"
    ), {"names": list(TEST_TEAMS)})

    await db.commit()
    log("  削除しました")


async def ensure_rosters(db, apply: bool) -> dict[uuid.UUID, list[uuid.UUID]]:
    """各チームに選手5名を用意する。既に居るチームはそのまま。"""
    log("\n── 選手ロスターの整備 " + "─" * 41)

    teams = (await db.execute(text(
        "SELECT id, name, tag FROM teams ORDER BY created_at"
    ))).all()

    rosters: dict[uuid.UUID, list[uuid.UUID]] = {}
    created = 0
    for team_id, team_name, tag in teams:
        existing = (await db.execute(text(
            "SELECT player_id FROM team_members WHERE team_id=:t AND left_at IS NULL"
        ), {"t": team_id})).scalars().all()
        rosters[team_id] = list(existing)

        need = 5 - len(existing)
        if need <= 0 or not apply:
            continue

        for i in range(need):
            ign = f"{random.choice(NAME_PARTS_A)}{random.choice(NAME_PARTS_B)}{random.randint(1, 99)}"
            pid = uuid.uuid4()
            await db.execute(text("""
                INSERT INTO players (id, in_game_name, game, rank, main_role,
                                     region, created_at, updated_at, stats_public)
                VALUES (:id,:n,'VALORANT',:rk,:role,'関東', now(), now(), true)
            """), {"id": pid, "n": ign,
                   "rk": random.choice(["Diamond", "Ascendant", "Immortal"]),
                   "role": random.choice(["Duelist", "Initiator", "Controller", "Sentinel"])})
            await db.execute(text("""
                INSERT INTO team_members (id, team_id, player_id, role, joined_at)
                VALUES (:id,:t,:p,'player', now())
            """), {"id": uuid.uuid4(), "t": team_id, "p": pid})
            rosters[team_id].append(pid)
            created += 1

    if apply:
        await db.commit()
    log(f"  チーム数={len(teams)} 追加した選手={created}名")
    return rosters


def build_game_stats(
    roster_a: list[uuid.UUID], team_a: uuid.UUID,
    roster_b: list[uuid.UUID], team_b: uuid.UUID,
    rounds_a: int, rounds_b: int,
) -> list[PlayerStatsCreate]:
    """
    1マップ分の選手成績を、勝敗と整合する形で生成する。

    片方のキル合計がもう片方のデス合計になるようにし、ACSは勝者側を高めに寄せる。
    スコアボードから取得できる項目（Agent/K/D/A/SCORE/FB）のみを作る。
    """
    total_rounds = rounds_a + rounds_b
    winner_is_a = rounds_a > rounds_b

    def split(total: int, n: int) -> list[int]:
        """total を n 人に、ばらつきを付けて配分する。"""
        weights = [random.uniform(0.6, 1.5) for _ in range(n)]
        scale = total / sum(weights)
        values = [max(0, int(round(w * scale))) for w in weights]
        # 端数を先頭で調整して合計を合わせる
        values[0] += total - sum(values)
        return [max(0, v) for v in values]

    kills_a = int(total_rounds * (0.92 if winner_is_a else 0.72))
    kills_b = int(total_rounds * (0.72 if winner_is_a else 0.92))

    ka, kb = split(kills_a, 5), split(kills_b, 5)
    da, db_ = split(kills_b, 5), split(kills_a, 5)  # 相手のキル = 自分のデス

    agents_a = random.sample(AGENTS, 5)
    agents_b = random.sample(AGENTS, 5)
    fb_a, fb_b = split(max(1, total_rounds // 6), 5), split(max(1, total_rounds // 7), 5)

    stats: list[PlayerStatsCreate] = []
    for side, roster, team_id, kills, deaths, agents, fbs, won in (
        ("a", roster_a, team_a, ka, da, agents_a, fb_a, winner_is_a),
        ("b", roster_b, team_b, kb, db_, agents_b, fb_b, not winner_is_a),
    ):
        for i, player_id in enumerate(roster[:5]):
            acs = random.randint(190, 310) if won else random.randint(120, 235)
            stats.append(PlayerStatsCreate(
                player_id=str(player_id),
                team_id=str(team_id),
                agent=agents[i],
                kills=kills[i],
                deaths=deaths[i],
                assists=random.randint(2, 12),
                # DB上の score は総コンバットスコア。ACS = score / ラウンド数
                score=acs * total_rounds,
                first_bloods=fbs[i],
            ))
    return stats


async def simulate_tournament(db, cache, apply: bool,
                              rosters: dict[uuid.UUID, list[uuid.UUID]]) -> None:
    log("\n── AXELIA CUP の試合結果生成 " + "─" * 34)

    tournament = (await db.execute(
        select(Tournament).where(Tournament.name == "AXELIA CUP")
    )).scalar_one_or_none()
    if tournament is None:
        log("  AXELIA CUP が見つかりません")
        return

    organizer = (await db.execute(
        select(User).where(User.id == tournament.organizer_id)
    )).scalar_one_or_none()
    if organizer is None:
        log("  主催者ユーザーが見つかりません")
        return

    map_ids = (await db.execute(text(
        "SELECT id FROM maps WHERE game='VALORANT' AND is_active LIMIT 9"
    ))).scalars().all()

    service = MatchService(db, cache)
    played = 0
    base_time = datetime.now(timezone.utc) - timedelta(days=3)

    # ラウンド順に処理する。前のラウンドを確定させないと次の対戦カードが埋まらない
    for round_number in range(1, 6):
        matches = (await db.execute(
            select(Match)
            .where(Match.tournament_id == tournament.id,
                   Match.round_number == round_number)
            .order_by(Match.match_number)
        )).scalars().all()
        if not matches:
            break

        for match in matches:
            if match.status == MatchStatus.COMPLETED:
                continue
            if not match.team1_id or not match.team2_id:
                log(f"  R{round_number} 第{match.match_number}試合: 対戦相手未確定のためスキップ")
                continue

            roster_a = rosters.get(match.team1_id, [])
            roster_b = rosters.get(match.team2_id, [])
            if len(roster_a) < 5 or len(roster_b) < 5:
                log(f"  R{round_number} 第{match.match_number}試合: 選手不足のためスキップ")
                continue

            if not apply:
                played += 1
                continue

            loser_rounds = random.choice([5, 7, 8, 9, 10, 11])
            team1_wins = random.random() < 0.5
            rounds_1, rounds_2 = (13, loser_rounds) if team1_wins else (loser_rounds, 13)
            winner_id = match.team1_id if team1_wins else match.team2_id

            await service.start_match(match.id, organizer)
            await service.register_result(
                match.id,
                MatchResultCreate(
                    winner_id=str(winner_id),
                    game_stats=[GameStatsCreate(
                        game_number=1,
                        map_id=str(random.choice(map_ids)),
                        team1_score=rounds_1,
                        team2_score=rounds_2,
                        winner_id=str(winner_id),
                        duration_seconds=random.randint(1900, 3000),
                        player_stats=build_game_stats(
                            roster_a, match.team1_id, roster_b, match.team2_id,
                            rounds_1, rounds_2,
                        ),
                    )],
                ),
                organizer,
            )
            await db.commit()
            played += 1

        # 次のラウンドの対戦カードを読み直すためセッションを更新する
        if apply:
            await db.commit()

    if apply:
        # 進行時刻を過去にずらして「開催済みの大会」に見えるようにする
        # バインド変数は明示的にキャストする。省くと asyncpg が式全体を
        # interval と推論して型不一致になる
        await db.execute(text("""
            UPDATE matches
               SET started_at = CAST(:base AS timestamptz)
                              + make_interval(hours => match_number)
                              + make_interval(hours => (round_number - 1) * 6),
                   ended_at   = CAST(:base AS timestamptz)
                              + make_interval(hours => match_number)
                              + make_interval(hours => (round_number - 1) * 6)
                              + interval '45 minutes'
             WHERE tournament_id = :t AND status = 'completed'
        """), {"base": base_time, "t": tournament.id})
        # 試合を過去日で作ったので、大会の日程も過去に揃える。
        # 11月開催の大会に8月の試合結果がぶら下がる矛盾を避ける
        await db.execute(text("""
            UPDATE tournaments
               SET status = 'completed',
                   registration_start_at = CAST(:base AS timestamptz) - interval '21 days',
                   registration_end_at   = CAST(:base AS timestamptz) - interval '7 days',
                   start_at              = CAST(:base AS timestamptz),
                   end_at                = CAST(:base AS timestamptz) + interval '1 day'
             WHERE id = :t
        """), {"base": base_time, "t": tournament.id})
        await db.commit()

    log(f"  結果を登録した試合: {played}件")


async def rebuild_rankings(db, cache, apply: bool) -> None:
    """
    完了済みの試合から大会ランキングを組み直す。

    通常はイベント経由でWorkerが更新するが、スクリプトから直接試合を作った
    場合は反映されないため、ここで同じサービスを使って集計し直す。
    """
    log("\n── 大会ランキングの集計 " + "─" * 40)

    # マップ単位の勝敗は match_games にしかないので、そこから数え上げる
    matches = (await db.execute(text("""
        SELECT m.id, m.tournament_id, m.winner_id, m.team1_id, m.team2_id,
               COUNT(*) FILTER (WHERE mg.winner_id = m.winner_id) AS winner_games,
               COUNT(*) FILTER (WHERE mg.winner_id IS NOT NULL
                                  AND mg.winner_id <> m.winner_id) AS loser_games
          FROM matches m
          LEFT JOIN match_games mg ON mg.match_id = m.id
         WHERE m.status = 'completed' AND m.winner_id IS NOT NULL
         GROUP BY m.id, m.tournament_id, m.winner_id, m.team1_id, m.team2_id,
                  m.round_number, m.match_number
         ORDER BY m.round_number, m.match_number
    """))).all()

    if not apply:
        log(f"  集計対象の試合: {len(matches)}件")
        return

    # 作り直しなので既存の集計は一度消す
    await db.execute(text("DELETE FROM rankings"))
    await db.commit()

    service = RankingService(db, cache)
    for _mid, tournament_id, winner_id, team1_id, team2_id, winner_games, loser_games in matches:
        loser_id = team2_id if winner_id == team1_id else team1_id
        await service.update_after_match(
            tournament_id=tournament_id,
            winner_id=winner_id,
            loser_id=loser_id,
            winner_game_wins=winner_games or 1,
            loser_game_wins=loser_games or 0,
        )
    await db.commit()

    total = (await db.execute(text("SELECT count(*) FROM rankings"))).scalar()
    log(f"  試合{len(matches)}件から{total}チーム分のランキングを作成しました")


async def ensure_open_tournament(db, apply: bool) -> None:
    """
    受付中の大会を1件用意する。

    完了した大会だけだとエントリーの流れをデモできないため、同じ主催者で
    次回大会を作り、募集中の状態にしておく。
    """
    log("\n── 受付中の大会 " + "─" * 47)

    existing = (await db.execute(text(
        "SELECT name FROM tournaments WHERE status = 'registration_open'"
    ))).scalars().all()
    if existing:
        log(f"  既にあります: {existing}")
        return
    if not apply:
        log("  作成予定: AXELIA CUP vol.2（受付中）")
        return

    source = (await db.execute(text(
        "SELECT id FROM tournaments WHERE name='AXELIA CUP' LIMIT 1"
    ))).scalar_one_or_none()
    if source is None:
        log("  複製元の AXELIA CUP が見つかりません")
        return

    new_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    # 既存行をコピーして日程と状態だけ差し替える。列を手で書き並べると
    # 必須カラムを取りこぼすため、生成列以外を information_schema から集める
    columns = (await db.execute(text("""
        SELECT column_name FROM information_schema.columns
         WHERE table_name = 'tournaments'
           AND is_generated = 'NEVER'
           AND generation_expression IS NULL
         ORDER BY ordinal_position
    """))).scalars().all()

    overrides = {
        "id": ":nid",
        "name": "'AXELIA CUP vol.2'",
        "slug": "'axelia-cup-vol2'",
        "status": "'registration_open'",
        "registration_start_at": "CAST(:now AS timestamptz) - interval '3 days'",
        "registration_end_at": "CAST(:now AS timestamptz) + interval '18 days'",
        "start_at": "CAST(:now AS timestamptz) + interval '25 days'",
        "end_at": "CAST(:now AS timestamptz) + interval '25 days'",
        "created_at": "CAST(:now AS timestamptz)",
        "updated_at": "CAST(:now AS timestamptz)",
    }
    select_list = ", ".join(overrides.get(c, c) for c in columns)
    column_list = ", ".join(columns)

    await db.execute(
        text(f"INSERT INTO tournaments ({column_list}) "
             f"SELECT {select_list} FROM tournaments WHERE id = :src"),
        {"nid": new_id, "now": now, "src": source},
    )
    await db.commit()
    log("  AXELIA CUP vol.2 を受付中で作成しました")


async def main() -> None:
    apply = "--yes" in sys.argv
    if not apply:
        log("※ ドライラン（実際には変更しません）。実行するには --yes を付けてください\n")

    redis = await get_redis()
    cache = RedisCache(redis)

    async with AsyncSessionLocal() as db:
        await cleanup_test_data(db, apply)
        rosters = await ensure_rosters(db, apply)
        await simulate_tournament(db, cache, apply, rosters)
        await rebuild_rankings(db, cache, apply)
        await ensure_open_tournament(db, apply)

        log("\n── 結果 " + "─" * 55)
        for label, sql in (
            ("大会", "SELECT count(*) FROM tournaments"),
            ("チーム", "SELECT count(*) FROM teams"),
            ("選手", "SELECT count(*) FROM players"),
            ("完了試合", "SELECT count(*) FROM matches WHERE status='completed'"),
            ("選手成績", "SELECT count(*) FROM player_match_stats"),
        ):
            count = (await db.execute(text(sql))).scalar()
            log(f"  {label}: {count}")


asyncio.run(main())
