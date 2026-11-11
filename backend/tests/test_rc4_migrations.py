"""RC4 のマイグレーション（031・032）を、030 の形のデータを入れた別の DB で上げ下げして確かめる。

- 判定 3（D23）: 開催中の大会があると止まり、031 もまとめて戻って版は 030 のまま
- 031: 出どころの判定（self / unconfirmed）・現役の重複の退避・期間の CHECK（違反があれば NOT VALID）
- 032: 既存の大会は legacy・新しい大会の既定は roster・トリガー（Q02）
- 030 への戻し: 退避した重複の行が現役に戻り、追加の列が消える。もう一度上げられる
"""
import asyncio
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

from tests.conftest import BACKEND_DIR, TEST_DB_URL

NOW = datetime.now(timezone.utc)


def _in_thread(fn, *args):
    """別のスレッドで実行する。asyncio.run（alembic の env.py も呼ぶ）は、呼んだスレッドの
    イベントループを外すので、テストの main スレッドで呼ぶと後に続く非同期のテストが落ちる。"""
    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(fn, *args).result()


def _sql(url, sql: str, **params):
    """1 文を実行して行を返す（テストのループと別に、毎回の接続で行う）。"""
    async def run():
        engine = create_async_engine(url)
        try:
            async with engine.begin() as conn:
                res = await conn.execute(text(sql), params)
                return res.all() if res.returns_rows else None
        finally:
            await engine.dispose()
    return _in_thread(asyncio.run, run())


def _tx(url, statements: list[str], **params) -> None:
    """複数の文を 1 つのトランザクションで実行する（切り戻しの手順書の SQL と同じ形）。"""
    async def run():
        engine = create_async_engine(url)
        try:
            async with engine.begin() as conn:
                for sql in statements:
                    await conn.execute(text(sql), params)
        finally:
            await engine.dispose()
    _in_thread(asyncio.run, run())


# RC4_ROLLBACK_RUNBOOK.md の 5 章（Q30）: 完了した roster の大会を、理由を記録して legacy に戻す 1 回だけの作業
Q30_REVERT = [
    "ALTER TABLE tournaments DISABLE TRIGGER trg_tournaments_roster_mode_guard",
    "INSERT INTO admin_corrections (id, kind, tournament_id, reason, before, after) "
    "SELECT gen_random_uuid(), 'roster_mode_change', t.id, :reason, "
    "jsonb_build_object('roster_mode', t.roster_mode), jsonb_build_object('roster_mode', 'legacy') "
    "FROM tournaments t WHERE t.id = :id AND t.roster_mode = 'roster' AND t.status = 'completed'",
    "UPDATE tournaments SET roster_mode = 'legacy' WHERE id = :id AND roster_mode = 'roster' AND status = 'completed'",
    "ALTER TABLE tournaments ENABLE TRIGGER trg_tournaments_roster_mode_guard",
]


def _admin(sql: str) -> None:
    async def run():
        engine = create_async_engine(make_url(TEST_DB_URL).set(database="postgres"), isolation_level="AUTOCOMMIT")
        try:
            async with engine.connect() as conn:
                await conn.execute(text(sql))
        finally:
            await engine.dispose()
    _in_thread(asyncio.run, run())


def _alembic(db_name: str, action: str, rev: str) -> None:
    from app.core.config import settings
    before = settings.DB_NAME
    settings.DB_NAME = db_name
    try:
        config = Config(str(BACKEND_DIR / "alembic.ini"))
        config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
        _in_thread(getattr(command, action), config, rev)
    finally:
        settings.DB_NAME = before


def _seed_030(url) -> dict:
    ids = {k: uuid.uuid4() for k in (
        "owner_u", "self_u", "other_u", "owner_p", "self_p", "other_p", "dup_p", "inv_p", "team",
        "m_owner", "m_self", "m_other", "m_dup_old", "m_dup_new", "m_inverted", "t_done", "t_live", "match")}
    for key in ("owner_u", "self_u", "other_u"):
        _sql(url, "INSERT INTO users (id, email, username, hashed_password, role) "
                  "VALUES (:id, :email, :name, 'x', 'player')",
             id=ids[key], email=f"{key}-{ids[key].hex[:6]}@test.com", name=f"{key}_{ids[key].hex[:6]}")
    for key, user in (("owner_p", "owner_u"), ("self_p", "self_u"), ("other_p", "other_u"),
                      ("dup_p", None), ("inv_p", None)):
        _sql(url, "INSERT INTO players (id, user_id, in_game_name, game) VALUES (:id, :uid, :ign, 'VALORANT')",
             id=ids[key], uid=ids[user] if user else None, ign=key)
    _sql(url, "INSERT INTO teams (id, name, tag, game, owner_id) VALUES (:id, 'Mig Team', 'MIG', 'VALORANT', :o)",
         id=ids["team"], o=ids["owner_u"])
    rows = (("m_owner", "owner_p", 30, None), ("m_self", "self_p", 20, None), ("m_other", "other_p", 20, None),
            ("m_dup_old", "dup_p", 40, None), ("m_dup_new", "dup_p", 10, None),
            ("m_inverted", "inv_p", 5, 8))  # 脱退が加入より前（古いデータの不整合）
    for key, player, joined_days, left_days in rows:
        _sql(url, "INSERT INTO team_members (id, team_id, player_id, role, joined_at, left_at) "
                  "VALUES (:id, :team, :p, 'player', :joined, :left)",
             id=ids[key], team=ids["team"], p=ids[player], joined=NOW - timedelta(days=joined_days),
             left=NOW - timedelta(days=left_days) if left_days else None)
    # 本人が自分を加えたイベント（self の証拠）
    _sql(url, "INSERT INTO domain_events (id, type, occurred_at, actor_id, entity_type, entity_id, after) "
              "VALUES (:id, 'team.member.added', :at, :actor, 'team', :team, CAST(:after AS jsonb))",
         id=uuid.uuid4(), at=NOW, actor=ids["self_u"], team=ids["team"],
         after=f'{{"player_id": "{ids["self_p"]}"}}')
    for key, status in (("t_done", "completed"), ("t_live", "ongoing")):
        _sql(url, "INSERT INTO tournaments (id, name, slug, game, format, organizer_id, status) "
                  "VALUES (:id, :name, :slug, 'VALORANT', 'single_elimination', :org, CAST(:status AS tournament_status))",
             id=ids[key], name=key, slug=f"{key}-{ids[key].hex[:6]}", org=ids["owner_u"], status=status)
    _sql(url, "INSERT INTO matches (id, tournament_id, status) VALUES (:id, :t, 'completed')",
         id=ids["match"], t=ids["t_done"])
    return ids


def _version(url) -> str:
    return _sql(url, "SELECT version_num FROM alembic_version")[0][0]


def _has_column(url, table: str, column: str) -> bool:
    return bool(_sql(url, "SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' "
                          "AND table_name = :t AND column_name = :c", t=table, c=column))


@pytest.fixture
def mig_db():
    name = f"{make_url(TEST_DB_URL).database}_rc4mig"
    _admin(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
    _admin(f'CREATE DATABASE "{name}"')
    try:
        yield name, make_url(TEST_DB_URL).set(database=name)
    finally:
        _admin(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')


def test_031_032_の上げ下げと開催中の大会での停止(mig_db):
    name, url = mig_db
    _alembic(name, "upgrade", "030")
    ids = _seed_030(url)

    # 判定 3: 開催中の大会があると止まる。031 もまとめて戻り、030 のまま
    with pytest.raises(RuntimeError, match="D23"):
        _alembic(name, "upgrade", "head")
    assert _version(url) == "030"
    assert not _has_column(url, "team_members", "consent")
    assert not _has_column(url, "tournaments", "roster_mode")

    _sql(url, "UPDATE tournaments SET status = 'completed' WHERE id = :id", id=ids["t_live"])
    _alembic(name, "upgrade", "head")
    assert _version(url) == "032"

    # 031: 証拠のある所属だけ self。ほかは本人未確認
    consent = dict(_sql(url, "SELECT id, consent FROM team_members"))
    assert consent[ids["m_owner"]] == "self"
    assert consent[ids["m_self"]] == "self"
    assert consent[ids["m_other"]] == "unconfirmed"
    # 現役の重複: 古い行を残し、新しい行を退避してから脱退にする（行は消さない）
    left = dict(_sql(url, "SELECT id, left_at FROM team_members WHERE player_id = :p", p=ids["dup_p"]))
    assert left[ids["m_dup_old"]] is None and left[ids["m_dup_new"]] is not None
    assert [r[0] for r in _sql(url, "SELECT id FROM rc4_membership_dedup_backup")] == [ids["m_dup_new"]]
    # 期間の違反が残っているので、CHECK は NOT VALID のまま（新しい行には効く）
    assert _sql(url, "SELECT convalidated FROM pg_constraint WHERE conname = 'ck_team_members_period'")[0][0] is False
    assert _sql(url, "SELECT grace_days FROM membership_migration_state WHERE id = 1")[0][0] == 60

    # 032: 既存の大会は legacy、新しい大会の既定は roster
    modes = dict(_sql(url, "SELECT id, roster_mode FROM tournaments"))
    assert modes == {ids["t_done"]: "legacy", ids["t_live"]: "legacy"}
    new_id = uuid.uuid4()
    _sql(url, "INSERT INTO tournaments (id, name, slug, game, format, organizer_id) "
              "VALUES (:id, 'new', :slug, 'VALORANT', 'single_elimination', :org)",
         id=new_id, slug=f"new-{new_id.hex[:6]}", org=ids["owner_u"])
    assert _sql(url, "SELECT roster_mode FROM tournaments WHERE id = :id", id=new_id)[0][0] == "roster"

    # トリガー（Q02）: legacy の新しい行と roster → legacy を断る。既存の legacy の行のほかの更新は通す
    with pytest.raises(Exception, match="legacy"):
        _sql(url, "INSERT INTO tournaments (id, name, slug, game, format, organizer_id, roster_mode) "
                  "VALUES (:id, 'bad', :slug, 'VALORANT', 'single_elimination', :org, 'legacy')",
             id=uuid.uuid4(), slug=f"bad-{uuid.uuid4().hex[:6]}", org=ids["owner_u"])
    with pytest.raises(Exception, match="legacy"):
        _sql(url, "UPDATE tournaments SET roster_mode = 'legacy' WHERE id = :id", id=new_id)
    _sql(url, "UPDATE tournaments SET name = 'renamed', status = 'cancelled' WHERE id = :id", id=ids["t_done"])
    _sql(url, "UPDATE tournaments SET roster_mode = 'roster' WHERE id = :id", id=ids["t_live"])

    # 切り戻しの間に旧コードが作って完了した大会（既定で roster）を、手順書の作業で legacy に戻す
    done = uuid.uuid4()
    _sql(url, "INSERT INTO tournaments (id, name, slug, game, format, organizer_id, status) "
              "VALUES (:id, 'done', :slug, 'VALORANT', 'single_elimination', :org, 'completed')",
         id=done, slug=f"done-{done.hex[:6]}", org=ids["owner_u"])
    _tx(url, Q30_REVERT, id=done, reason="切り戻しの間に旧コードで完了した大会")
    assert _sql(url, "SELECT roster_mode FROM tournaments WHERE id = :id", id=done)[0][0] == "legacy"
    assert _sql(url, "SELECT kind, reason FROM admin_corrections WHERE tournament_id = :id", id=done) == [
        ("roster_mode_change", "切り戻しの間に旧コードで完了した大会")]
    assert _sql(url, "SELECT tgenabled::text FROM pg_trigger WHERE tgname = 'trg_tournaments_roster_mode_guard'")[0][0] == "O"
    with pytest.raises(Exception, match="legacy"):  # 作業の後もトリガーは効いている
        _sql(url, "UPDATE tournaments SET roster_mode = 'legacy' WHERE id = :id", id=new_id)

    # 030 へ戻す: 退避した重複は現役に戻り、追加の列・表が消える
    _sql(url, "DELETE FROM tournaments WHERE id = :id", id=new_id)
    _alembic(name, "downgrade", "030")
    assert _version(url) == "030"
    left = dict(_sql(url, "SELECT id, left_at FROM team_members WHERE player_id = :p", p=ids["dup_p"]))
    assert left == {ids["m_dup_old"]: None, ids["m_dup_new"]: None}
    assert not _has_column(url, "team_members", "consent")
    assert not _has_column(url, "tournaments", "roster_mode")
    assert not _sql(url, "SELECT 1 FROM pg_proc WHERE proname = 'rc4_guard_roster_mode'")

    # 戻した後に、もう一度上げられる
    _alembic(name, "upgrade", "head")
    assert _version(url) == "032"
