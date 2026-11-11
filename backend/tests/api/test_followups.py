"""監査で見つかった既存不具合の回帰テスト（スキーマとタグ）。"""
import pytest
from httpx import AsyncClient

from app.core.security import issue_tokens
from app.services.tag_service import TagService
from tests import factories as f
from tests.conftest import auth_headers


@pytest.mark.asyncio
async def test_選手からの募集_player_seeksを掲載できる(client: AsyncClient, db):
    user = await f.make_user(db)
    player = await f.make_player(db, user=user, in_game_name="Seeker")
    res = await client.post(
        "/api/v1/scout/recruitment",
        headers=auth_headers(issue_tokens(user)[0]),
        json={"post_type": "player_seeks", "player_id": str(player.id), "game": "VALORANT",
              "title": "チームを探しています"},
    )
    assert res.status_code == 201, res.text  # 以前は列が varchar(10) で必ず 500 だった


@pytest.mark.asyncio
async def test_重複入力があっても新しいタグのラベルがずれない(db):
    owner = await f.make_user(db)
    team = await f.make_team(db, owner=owner, name="Tag Team", tag="TAGT")
    tags = await TagService(db).set_tags("team", team.id, ["Ranked", "ranked", "Scrim"])
    assert [(t["slug"], t["label"]) for t in tags] == [("ranked", "Ranked"), ("scrim", "Scrim")]
