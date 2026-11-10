"""公開範囲の回帰テスト。

- 詳細スタッツ非公開（stats_public=False）が個人ページ・ランキングで無視されていた。
- 分析ランキングが本名（real_name）を返していた。
- 非公開の LFP/LFT が ID 指定やタグ検索で誰にでも読めた。
- 下書き・非公開の大会が、優勝ハイライト・選手の大会履歴・タグ検索に出ていた。
"""
from datetime import UTC, datetime, timedelta

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


async def _member_since_before(db, team, player):
    """RC4: 既存の大会（legacy）は、所属の期間が大会の期間と重なる選手に帰属する。大会より前から所属させる。"""
    m = await f.add_member(db, team=team, player=player)
    m.joined_at = _now() - timedelta(days=60)
    await db.flush()
    return m


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
    tour = await f.make_legacy_tournament(db, organizer=owner, status=TournamentStatus.COMPLETED, **kw)
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
        await _member_since_before(db, team, player)
        public = await _completed_with_report(db, owner, team)
        await _completed_with_report(db, owner, team, visibility="private")
        await _completed_with_report(db, owner, team, visibility="unlisted")

        res = await client.get("/api/v1/stats/champions?limit=10")
        assert res.status_code == 200, res.text
        assert [c["tournament_id"] for c in res.json()["data"]] == [str(public.id)]

        res = await client.get(f"/api/v1/players/{player.id}/history")
        assert res.status_code == 200, res.text
        assert [h["tournament_id"] for h in res.json()["data"]] == [str(public.id)]


# ── RC3（S7）: 限定公開・非公開の大会を、実績カード・ランキング・通算成績・分析に数えない ──
async def _final(db, owner, teams, player, *, kills, **kw):
    """teams[0] が決勝で teams[1] に勝って優勝した完了大会（4チーム・選手成績つき）。"""
    tour = await f.make_legacy_tournament(db, organizer=owner, status=TournamentStatus.COMPLETED, **kw)
    for t in teams:
        await f.register_team(db, tournament=tour, team=t)
    match = Match(tournament_id=tour.id, round_number=1, match_number=1, status=MatchStatus.COMPLETED,
                  team1_id=teams[0].id, team2_id=teams[1].id, winner_id=teams[0].id, ended_at=_now())
    db.add(match)
    await db.flush()
    game = MatchGame(match_id=match.id, game_number=1, team1_score=13, team2_score=5, winner_id=teams[0].id)
    db.add(game)
    await db.flush()
    db.add(PlayerMatchStats(match_game_id=game.id, player_id=player.id, team_id=teams[0].id,
                            kills=kills, deaths=10, assists=0, created_at=_now()))
    db.add(TournamentReport(tournament_id=tour.id, data={
        "champion": {"team_id": str(teams[0].id), "team_name": teams[0].name},
        "runner_up": {"team_id": str(teams[1].id), "team_name": teams[1].name},
        "standings": [{"team_id": str(t.id), "wins": int(i == 0), "losses": int(i == 1)}
                      for i, t in enumerate(teams)],
    }))
    await db.flush()
    return tour


class TestPrivateTournamentsStayOutOfAggregates:
    @pytest.mark.asyncio
    async def test_実績カード_ランキング_通算成績_分析は公開大会だけを数える(self, client: AsyncClient, db, admin_token):
        owner = await f.make_user(db)
        player = await f.make_player(db, user=owner)

        async def teams(prefix):
            return [await f.make_team(db, owner=owner, name=f"S7 {prefix}{i} {_now().microsecond}") for i in range(4)]

        pub, priv, lim = await teams("pub"), await teams("priv"), await teams("lim")
        star = pub[0]  # 3大会すべてで優勝するチーム
        await _member_since_before(db, star, player)
        public = await _final(db, owner, pub, player, kills=10)
        private = await _final(db, owner, [star, *priv[1:]], player, kills=40, visibility="private")
        limited = await _final(db, owner, [star, *lim[1:]], player, kills=40, visibility="limited")
        hidden_ids = {str(t.id) for t in priv[1:] + lim[1:]}

        card = (await client.get(f"/api/v1/teams/{star.id}/achievement-card")).json()["data"]
        assert [t["tournament_id"] for t in card["recent_titles"]] == [str(public.id)]
        assert (card["championships"], card["tournaments"], card["matches"], card["wins"]) == (1, 1, 1, 1)

        rank = (await client.get(f"/api/v1/teams/{star.id}/rank-card")).json()["data"]
        assert [h["tournament_id"] for h in rank["history"]] == [str(public.id)]
        assert (rank["championships"], rank["tournaments"]) == (1, 1)

        board = (await client.get("/api/v1/rankings/global?limit=100")).json()["data"]
        assert {e["team_id"] for e in board} == {str(t.id) for t in pub}  # 非公開だけの出場チームは載らない
        mine = next(e for e in board if e["team_id"] == str(star.id))
        assert (mine["tournaments"], mine["championships"]) == (1, 1)
        players = (await client.get("/api/v1/rankings/players?limit=100")).json()["data"]
        assert [p["player_id"] for p in players] == [str(player.id)]
        assert players[0]["rp"] == mine["rp"]  # 所属チームの公開大会の RP だけ

        career = (await client.get(f"/api/v1/teams/{star.id}/career")).json()["data"]
        assert (career["total_matches"], career["championships"], career["tournaments_played"]) == (1, 1, 1)
        assert [r["team_id"] for r in career["rivals"]] == [str(pub[1].id)]  # 非公開大会の対戦相手を出さない
        assert not hidden_ids & {r["team_id"] for r in career["rivals"]}
        stats = (await client.get(f"/api/v1/teams/{star.id}/stats")).json()["data"]
        assert (stats["total_matches"], stats["game_wins"], stats["game_losses"], stats["tournaments_played"]) == (1, 1, 0, 1)

        pc = (await client.get(f"/api/v1/players/{player.id}/career")).json()["data"]
        assert (pc["total_matches"], pc["tournaments_played"], pc["avg_kills"]) == (1, 1, 10.0)

        ranking = (await client.get("/api/v1/analytics/players?game=VALORANT")).json()["data"]
        assert [(r["player_id"], r["games"], r["avg_kills"]) for r in ranking] == [(str(player.id), 1, 10.0)]
        overview = (await client.get("/api/v1/analytics/winrate?game=VALORANT")).json()["data"]["overview"]
        assert (overview["total_tournaments"], overview["total_matches"]) == (1, 1)
        stats_url = f"/api/v1/analytics/players/{player.id}/stats?game=VALORANT"
        mine_stats = (await client.get(stats_url)).json()["data"]  # 監査 S7-1: 以前は全大会を数えていた
        assert (mine_stats["games_played"], mine_stats["total_kills"]) == (1, 10)
        one = (await client.get(f"{stats_url}&tournament_id={private.id}")).json()["data"]
        assert (one["games_played"], one["total_kills"]) == (1, 40)

        # 大会を指定した集計と大会の詳細は、これまでどおり大会の ID で見られる（主催者・管理者の画面）
        res = await client.get(f"/api/v1/analytics/players?game=VALORANT&tournament_id={private.id}")
        assert [(r["games"], r["avg_kills"]) for r in res.json()["data"]] == [(1, 40.0)]
        for headers in (auth_headers(_token(owner)), auth_headers(admin_token)):
            for tour in (private, limited):
                res = await client.get(f"/api/v1/tournaments/{tour.id}", headers=headers)
                assert res.status_code == 200, res.text


class _MemoCache:
    """値を覚えるキャッシュ（テストの既定のキャッシュは何も覚えない）。"""

    def __init__(self):
        self.data: dict = {}

    async def get(self, key): return self.data.get(key)
    async def set(self, key, value, ttl=None): self.data[key] = value
    async def delete(self, key): self.data.pop(key, None)


@pytest.mark.asyncio
async def test_大会を指定した選手スタッツのキャッシュを指定しない閲覧者に返さない(db):
    from app.models.enums import GameType, PeriodType
    from app.services.analytics import AnalyticsService

    owner = await f.make_user(db)
    player = await f.make_player(db, user=owner)
    teams = [await f.make_team(db, owner=owner, name=f"S7c {i} {_now().microsecond}") for i in range(4)]
    await f.add_member(db, team=teams[0], player=player)
    await _final(db, owner, teams, player, kills=10)
    private = await _final(db, owner, teams, player, kills=40, visibility="private")
    svc = AnalyticsService(db, _MemoCache())
    first = await svc.get_player_stats(player.id, GameType.VALORANT, PeriodType.ALL_TIME, private.id)
    assert first.total_kills == 40
    later = await svc.get_player_stats(player.id, GameType.VALORANT, PeriodType.ALL_TIME)
    assert later.total_kills == 10  # 非公開大会の値をキャッシュから返さない
