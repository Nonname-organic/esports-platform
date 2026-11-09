"""公開範囲の回帰テスト。

- 詳細スタッツ非公開（stats_public=False）が個人ページ・ランキングで無視されていた。
- 分析ランキングが本名（real_name）を返していた。
- 非公開の LFP/LFT が ID 指定やタグ検索で誰にでも読めた。
- 下書き・非公開の大会が、優勝ハイライト・選手の大会履歴・タグ検索に出ていた。
"""
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient

from app.core.security import issue_tokens
from app.models.enums import MatchStatus, TournamentStatus
from app.models.match import Match, MatchGame, PlayerMatchStats
from app.models.player_lft import PlayerLFT
from app.models.tag import Tag, Taggable
from app.models.team_recruitment import TeamRecruitment
from app.models.tournament_report import TournamentReport
from tests import factories as f
from tests.conftest import auth_headers


def _now():
    return datetime.now(UTC)


def _token(user) -> str:
    return issue_tokens(user)[0]


class TestPlayerStatsPublic:
    @pytest.mark.asyncio
    async def test_非公開の詳細スタッツは本人と管理者だけが見られる(self, client: AsyncClient, db, admin_token):
        owner = await f.make_user(db)
        player = await f.make_player(db, user=owner, stats_public=False)
        stranger = await f.make_user(db)
        detail = [f"/api/v1/players/{player.id}/{p}" for p in ("career", "stats", "analysis")]

        for headers in ({}, auth_headers(_token(stranger)), {"Authorization": "Bearer garbage"}):
            for url in detail:
                assert (await client.get(url, headers=headers)).status_code == 403, url
            prof = (await client.get(f"/api/v1/players/{player.id}/profile", headers=headers)).json()["data"]
            assert prof["career"] is None and prof["analysis"] is None
            assert prof["basic"]["id"] == str(player.id)  # 第1層（基本情報・大会成績）は残る
            res = await client.get(f"/api/v1/analytics/players/{player.id}/stats?game=VALORANT", headers=headers)
            assert res.status_code == 403

        for token in (_token(owner), admin_token):
            for url in detail:
                assert (await client.get(url, headers=auth_headers(token))).status_code == 200, url
            prof = (await client.get(f"/api/v1/players/{player.id}/profile", headers=auth_headers(token))).json()
            assert prof["data"]["career"] is not None

    @pytest.mark.asyncio
    async def test_公開設定なら誰でも見られる(self, client: AsyncClient, db):
        player = await f.make_player(db, user=await f.make_user(db))
        for p in ("career", "stats", "analysis"):
            assert (await client.get(f"/api/v1/players/{player.id}/{p}")).status_code == 200


async def _completed_match_with_stats(db, players):
    owner = await f.make_user(db)
    tour = await f.make_tournament(db, organizer=owner, status=TournamentStatus.COMPLETED)
    team = await f.make_team(db, owner=owner)
    match = Match(tournament_id=tour.id, team1_id=team.id, status=MatchStatus.COMPLETED, winner_id=team.id)
    db.add(match)
    await db.flush()
    game = MatchGame(match_id=match.id, game_number=1, team1_score=13, team2_score=5, winner_id=team.id)
    db.add(game)
    await db.flush()
    for p in players:
        db.add(PlayerMatchStats(match_game_id=game.id, player_id=p.id, team_id=team.id,
                                kills=20, deaths=10, assists=5, created_at=_now()))
    await db.flush()


class TestAnalyticsPlayerRanking:
    @pytest.mark.asyncio
    async def test_非公開の選手を載せず本名も返さない(self, client: AsyncClient, db):
        public = await f.make_player(db, in_game_name="PublicIGN", real_name="山田 太郎")
        hidden = await f.make_player(db, in_game_name="HiddenIGN", stats_public=False)
        await _completed_match_with_stats(db, [public, hidden])

        res = await client.get("/api/v1/analytics/players?game=VALORANT")
        assert res.status_code == 200, res.text
        rows = res.json()["data"]
        assert [r["player_id"] for r in rows] == [str(public.id)]
        assert rows[0]["player_name"] == "PublicIGN"
        assert "山田" not in res.text


class TestPrivateRecruitments:
    @pytest.mark.asyncio
    async def test_非公開のLFPは作成者と管理者以外には404(self, client: AsyncClient, db, admin_token):
        owner = await f.make_user(db)
        team = await f.make_team(db, owner=owner)
        lfp = TeamRecruitment(team_id=team.id, owner_id=owner.id, title="secret", roles=["Duelist"],
                              headcount=1, min_rank="Gold", region="JP", is_public=False,
                              created_at=_now(), updated_at=_now())
        db.add(lfp)
        await db.flush()
        url = f"/api/v1/lfp/{lfp.id}"
        stranger = await f.make_user(db)
        assert (await client.get(url)).status_code == 404
        assert (await client.get(url, headers=auth_headers(_token(stranger)))).status_code == 404
        assert (await client.get(url, headers=auth_headers(_token(owner)))).status_code == 200
        assert (await client.get(url, headers=auth_headers(admin_token))).status_code == 200

    @pytest.mark.asyncio
    async def test_非公開のLFTは本人と管理者以外には404(self, client: AsyncClient, db, admin_token):
        owner = await f.make_user(db)
        player = await f.make_player(db, user=owner)
        lft = PlayerLFT(player_id=player.id, user_id=owner.id, roles=["Duelist"], current_rank="Gold",
                        peak_rank="Gold", region="JP", is_public=False, created_at=_now(), updated_at=_now())
        db.add(lft)
        await db.flush()
        url = f"/api/v1/lft/{lft.id}"
        stranger = await f.make_user(db)
        assert (await client.get(url)).status_code == 404
        assert (await client.get(url, headers=auth_headers(_token(stranger)))).status_code == 404
        assert (await client.get(url, headers=auth_headers(_token(owner)))).status_code == 200
        assert (await client.get(url, headers=auth_headers(admin_token))).status_code == 200


class TestTagSearch:
    @pytest.mark.asyncio
    async def test_公開されているものだけがタグ検索に出る(self, client: AsyncClient, db):
        owner = await f.make_user(db)
        team = await f.make_team(db, owner=owner)
        player = await f.make_player(db, user=owner)
        tours = {
            "public": await f.make_tournament(db, organizer=owner),
            "private": await f.make_tournament(db, organizer=owner, visibility="private"),
            "unlisted": await f.make_tournament(db, organizer=owner, visibility="unlisted"),
            "draft": await f.make_tournament(db, organizer=owner, status=TournamentStatus.DRAFT),
        }
        lfps, lfts = {}, {}
        for public in (True, False):
            lfps[public] = TeamRecruitment(team_id=team.id, owner_id=owner.id, title="t", roles=["Duelist"],
                                           headcount=1, min_rank="Gold", region="JP", is_public=public,
                                           created_at=_now(), updated_at=_now())
            p = player if public else await f.make_player(db, user=await f.make_user(db))
            lfts[public] = PlayerLFT(player_id=p.id, user_id=p.user_id, roles=["Duelist"], current_rank="Gold",
                                     peak_rank="Gold", region="JP", is_public=public,
                                     created_at=_now(), updated_at=_now())
        db.add_all([*lfps.values(), *lfts.values()])
        tag = Tag(slug="pro", label="Pro")
        db.add(tag)
        await db.flush()
        targets = [("team", team.id)] + [("tournament", t.id) for t in tours.values()] \
            + [("lfp", r.id) for r in lfps.values()] + [("lft", r.id) for r in lfts.values()]
        db.add_all([Taggable(tag_id=tag.id, entity_type=et, entity_id=eid) for et, eid in targets])
        await db.flush()

        res = await client.get("/api/v1/tags/pro/entities")
        assert res.status_code == 200, res.text
        got = {(r["entity_type"], r["entity_id"]) for r in res.json()["data"]}
        assert got == {("team", str(team.id)), ("tournament", str(tours["public"].id)),
                       ("lfp", str(lfps[True].id)), ("lft", str(lfts[True].id))}


async def _completed_with_report(db, owner, team, **kw):
    tour = await f.make_tournament(db, organizer=owner, status=TournamentStatus.COMPLETED, **kw)
    await f.register_team(db, tournament=tour, team=team)
    db.add(TournamentReport(tournament_id=tour.id, data={"champion": {"team_id": str(team.id),
                                                                      "team_name": team.name}}))
    await db.flush()
    return tour


class TestPrivateTournamentsStayOut:
    @pytest.mark.asyncio
    async def test_優勝ハイライトと選手の大会履歴に非公開大会を出さない(self, client: AsyncClient, db):
        owner = await f.make_user(db)
        player = await f.make_player(db, user=owner)
        team = await f.make_team(db, owner=owner)
        await f.add_member(db, team=team, player=player)
        public = await _completed_with_report(db, owner, team)
        await _completed_with_report(db, owner, team, visibility="private")
        await _completed_with_report(db, owner, team, visibility="unlisted")

        res = await client.get("/api/v1/stats/champions?limit=10")
        assert res.status_code == 200, res.text
        assert [c["tournament_id"] for c in res.json()["data"]] == [str(public.id)]

        res = await client.get(f"/api/v1/players/{player.id}/history")
        assert res.status_code == 200, res.text
        assert [h["tournament_id"] for h in res.json()["data"]] == [str(public.id)]
