"""スカウトのなりすましと、入力で 500 になっていた箇所の回帰テスト。

- 募集掲載・応募で、他人のチームや選手の ID を指定してなりすませた。
- UUID 文字列・列長超過・日付の不正値・大量タグが 500 になっていた（422 にする）。
"""
import pytest
from httpx import AsyncClient

from app.core.security import create_access_token
from app.models.enums import MemberRole
from tests import factories as f
from tests.conftest import auth_headers


def _h(user) -> dict:
    return auth_headers(create_access_token(str(user.id), {"role": user.role.value}))


def _post(**kw) -> dict:
    return {"post_type": "team_seeks", "game": "VALORANT", "title": "募集です"} | kw


class TestRecruitmentImpersonation:
    @pytest.mark.asyncio
    async def test_チームとして掲載できるのはオーナーとキャプテンだけ(self, client: AsyncClient, db):
        owner = await f.make_user(db)
        team = await f.make_team(db, owner=owner)
        captain, member, stranger = [await f.make_user(db) for _ in range(3)]
        await f.add_member(db, team=team, player=await f.make_player(db, user=captain), role=MemberRole.CAPTAIN)
        await f.add_member(db, team=team, player=await f.make_player(db, user=member), role=MemberRole.PLAYER)
        body = _post(team_id=str(team.id))

        for user in (stranger, member):
            res = await client.post("/api/v1/scout/recruitment", json=body, headers=_h(user))
            assert res.status_code == 403, res.text
        for user in (owner, captain):
            res = await client.post("/api/v1/scout/recruitment", json=body, headers=_h(user))
            assert res.status_code == 201, res.text

    @pytest.mark.asyncio
    async def test_選手として掲載できるのは本人だけ(self, client: AsyncClient, db):
        owner, stranger = await f.make_user(db), await f.make_user(db)
        player = await f.make_player(db, user=owner)
        # post_type=player_seeks は列長(varchar(10))超過で別途 500 になる既存不具合があるため team_seeks で確かめる
        body = _post(player_id=str(player.id))
        assert (await client.post("/api/v1/scout/recruitment", json=body, headers=_h(stranger))).status_code == 403
        assert (await client.post("/api/v1/scout/recruitment", json=body, headers=_h(owner))).status_code == 201

    @pytest.mark.asyncio
    async def test_他人の選手やチームとして応募できない(self, client: AsyncClient, db):
        author = await f.make_user(db)
        post = (await client.post("/api/v1/scout/recruitment", json=_post(), headers=_h(author))).json()["data"]
        victim, applicant = await f.make_user(db), await f.make_user(db)
        victim_player = await f.make_player(db, user=victim)
        victim_team = await f.make_team(db, owner=victim)
        own_player = await f.make_player(db, user=applicant)

        for extra in ({"player_id": str(victim_player.id)}, {"team_id": str(victim_team.id)}):
            res = await client.post("/api/v1/scout/recruitment/apply", json={"post_id": post["id"], **extra},
                                    headers=_h(applicant))
            assert res.status_code == 403, res.text
        res = await client.post("/api/v1/scout/recruitment/apply",
                                json={"post_id": post["id"], "player_id": str(own_player.id)}, headers=_h(applicant))
        assert res.status_code == 201, res.text


class TestInputValidation:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("url,body", [
        ("/api/v1/scout/recruitment", _post(team_id="not-a-uuid")),
        ("/api/v1/scout/recruitment", _post(player_id="1")),
        ("/api/v1/scout/recruitment", _post(game="V" * 21)),
        ("/api/v1/scout/recruitment", _post(min_rank="R" * 51)),
        ("/api/v1/scout/recruitment/apply", {"post_id": "not-a-uuid"}),
        ("/api/v1/lfp", {"team_id": "not-a-uuid", "title": "t", "roles": ["Duelist"], "headcount": 1,
                         "min_rank": "Gold", "region": "JP"}),
        ("/api/v1/lft", {"roles": ["Duelist"], "current_rank": "Gold", "peak_rank": "Gold", "region": "JP",
                         "experience": "E" * 31}),
        ("/api/v1/lft", {"roles": ["Duelist"], "current_rank": "Gold", "peak_rank": "Gold", "region": "JP",
                         "premier": "P" * 21}),
        ("/api/v1/lft", {"roles": ["Duelist"], "current_rank": "Gold", "peak_rank": "Gold", "region": "JP",
                         "deadline": "next friday"}),
    ])
    async def test_不正な入力は500ではなく422(self, client: AsyncClient, db, url, body):
        user = await f.make_user(db)
        await f.make_player(db, user=user)
        res = await client.post(url, json=body, headers=_h(user))
        assert res.status_code == 422, res.text

    @pytest.mark.asyncio
    async def test_LFPの作成と更新で列長と日付を検証する(self, client: AsyncClient, db):
        owner = await f.make_user(db)
        team = await f.make_team(db, owner=owner)
        base = {"team_id": str(team.id), "title": "t", "roles": ["Duelist"], "headcount": 1,
                "min_rank": "Gold", "region": "JP"}
        for bad in ({"activity_level": "A" * 31}, {"age_requirement": "A" * 31}, {"deadline": "2026-13-40"}):
            assert (await client.post("/api/v1/lfp", json=base | bad, headers=_h(owner))).status_code == 422

        res = await client.post("/api/v1/lfp", json=base | {"deadline": "2026-12-24"}, headers=_h(owner))
        assert res.status_code == 201, res.text
        lfp = res.json()["data"]
        assert lfp["deadline"] == "2026-12-24"

        url = f"/api/v1/lfp/{lfp['id']}"
        for bad in ({"min_rank": "R" * 51}, {"region": "R" * 51}, {"min_rank": ""}, {"deadline": "x"}):
            assert (await client.patch(url, json=bad, headers=_h(owner))).status_code == 422
        res = await client.patch(url, json={"deadline": "2027-01-05", "min_rank": "Diamond"}, headers=_h(owner))
        assert res.status_code == 200, res.text
        assert res.json()["data"]["deadline"] == "2027-01-05"

    @pytest.mark.asyncio
    async def test_LFTの更新で列長を検証する(self, client: AsyncClient, db):
        user = await f.make_user(db)
        await f.make_player(db, user=user)
        res = await client.post("/api/v1/lft", headers=_h(user), json={
            "roles": ["Duelist"], "current_rank": "Gold", "peak_rank": "Gold", "region": "JP",
            "deadline": "2026-12-24"})
        assert res.status_code == 201, res.text
        for bad in ({"current_rank": "R" * 51}, {"peak_rank": "R" * 51}, {"region": "R" * 51},
                    {"experience": "E" * 31}, {"premier": "P" * 21}):
            assert (await client.patch("/api/v1/lft/me", json=bad, headers=_h(user))).status_code == 422

    @pytest.mark.asyncio
    async def test_タグは1回20個まで各50文字まで(self, client: AsyncClient, db):
        owner = await f.make_user(db)
        team = await f.make_team(db, owner=owner)
        url = f"/api/v1/tags/of/team/{team.id}"
        too_many = {"tags": [f"tag{i}" for i in range(21)]}
        too_long = {"tags": ["x" * 51]}
        assert (await client.put(url, json=too_many, headers=_h(owner))).status_code == 422
        assert (await client.put(url, json=too_long, headers=_h(owner))).status_code == 422
        res = await client.put(url, json={"tags": [f"tag{i}" for i in range(20)]}, headers=_h(owner))
        assert res.status_code == 200, res.text
        assert len(res.json()["data"]) == 20
