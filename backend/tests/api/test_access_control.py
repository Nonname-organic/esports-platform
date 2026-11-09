"""他人の大会への操作と、非公開大会の露出の回帰テスト。

- organizer ロールは誰でも自分で付けられる。ロールだけで通していた試合操作
  （開始・スコア・成績・結果・Ban/Pick・OCR）は、他人の大会でも実行できた。
- 公開設定（限定公開・非公開）と下書きは、一覧・検索・ホームで無視されていた。
"""
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.security import create_access_token
from app.models.enums import GameType, MatchStatus, TournamentStatus, UserRole
from app.models.match import Map, Match, MatchResult
from app.services.tournament import TournamentService
from tests import factories as f
from tests.conftest import auth_headers


class _Cache:
    async def get(self, *a, **k): return None
    async def set(self, *a, **k): pass
    async def delete(self, *a, **k): pass
    async def delete_pattern(self, *a, **k): return 0


def _token(user) -> str:
    return create_access_token(str(user.id), {"role": user.role.value})


async def _ongoing_match(db):
    """主催者A の大会（開催中・2チーム）と、その1回戦の試合を作る。"""
    owner = await f.make_user(db, role=UserRole.ORGANIZER)
    tour = await f.make_tournament(db, organizer=owner, status=TournamentStatus.ONGOING)
    for i in range(2):
        team = await f.make_team(db, owner=owner, name=f"AC Team {i}", tag=f"AC{i}")
        await f.register_team(db, tournament=tour, team=team)
    await TournamentService(db, _Cache()).generate_bracket(tour.id, owner)
    match = (await db.execute(
        select(Match).where(Match.tournament_id == tour.id, Match.team1_id.is_not(None),
                            Match.team2_id.is_not(None))
    )).scalars().first()
    return owner, tour, match


class TestScoreboardOcrSizeLimit:
    # nginx の上限は添付ファイル（10MB）に合わせて上げたため、OCR は API 側で 5MB に止める
    @pytest.mark.asyncio
    async def test_5MBを超えるスクリーンショットは解析しない(self, client: AsyncClient, db):
        owner, _, match = await _ongoing_match(db)
        big = b"\x89PNG" + b"\0" * (5 * 1024 * 1024)
        res = await client.post(f"/api/v1/matches/{match.id}/scoreboard-ocr", headers=auth_headers(_token(owner)),
                                files={"file": ("s.png", big, "image/png")})
        assert res.status_code == 422, res.text


class TestMatchOperationsRequireTournamentOwner:
    @pytest.mark.asyncio
    async def test_他の主催者は試合を操作できない(self, client: AsyncClient, db):
        owner, _, match = await _ongoing_match(db)
        other = _token(await f.make_user(db, role=UserRole.ORGANIZER))
        mid = match.id

        res = await client.patch(f"/api/v1/matches/{mid}/start", headers=auth_headers(other))
        assert res.status_code == 403, res.text

        # 正規の主催者が開始した後でも、他の主催者はスコア・結果を触れない
        res = await client.patch(f"/api/v1/matches/{mid}/start", headers=auth_headers(_token(owner)))
        assert res.status_code == 204, res.text

        res = await client.post(f"/api/v1/matches/{mid}/games/1/score", headers=auth_headers(other),
                                json={"team1_score": 13, "team2_score": 2})
        assert res.status_code == 403, res.text

        res = await client.post(f"/api/v1/matches/{mid}/games/1/player-stats", headers=auth_headers(other),
                                json={"team1_score": 13, "team2_score": 2, "player_stats": []})
        assert res.status_code == 403, res.text

        res = await client.post(f"/api/v1/matches/{mid}/result", headers=auth_headers(other),
                                json={"winner_id": str(match.team1_id)})
        assert res.status_code == 403, res.text

        res = await client.post(f"/api/v1/matches/{mid}/scoreboard-ocr", headers=auth_headers(other),
                                files={"file": ("s.png", b"\x89PNG", "image/png")})
        assert res.status_code == 403, res.text

        await db.refresh(match)
        assert match.status == MatchStatus.ONGOING
        assert match.winner_id is None

    @pytest.mark.asyncio
    async def test_主催者本人と管理者は結果を確定できる(self, client: AsyncClient, db):
        owner, _, match = await _ongoing_match(db)
        admin = _token(await f.make_user(db, role=UserRole.ADMIN))
        mid = match.id

        assert (await client.patch(f"/api/v1/matches/{mid}/start",
                                   headers=auth_headers(_token(owner)))).status_code == 204
        res = await client.post(f"/api/v1/matches/{mid}/games/1/score", headers=auth_headers(admin),
                                json={"team1_score": 13, "team2_score": 7})
        assert res.status_code == 204, res.text
        res = await client.post(f"/api/v1/matches/{mid}/result", headers=auth_headers(_token(owner)),
                                json={"winner_id": str(match.team1_id)})
        assert res.status_code == 204, res.text

        await db.refresh(match)
        assert match.status == MatchStatus.COMPLETED
        assert match.winner_id == match.team1_id

    @pytest.mark.asyncio
    async def test_結果のマップ取得数は同じリクエストで送ったゲームも数える(
        self, client: AsyncClient, db
    ):
        owner, _, match = await _ongoing_match(db)
        token = _token(owner)
        mid = match.id
        assert (await client.patch(f"/api/v1/matches/{mid}/start",
                                   headers=auth_headers(token))).status_code == 204
        t1, t2 = str(match.team1_id), str(match.team2_id)
        # マイグレーションの初期データは前のテストの後始末で消えているので作る
        db.add(Map(game=GameType.VALORANT, internal_name="ac-map", display_name="AC Map"))
        await db.flush()

        def game(n, s1, s2, winner):
            return {"game_number": n, "map_id": "ac-map", "team1_score": s1,
                    "team2_score": s2, "winner_id": winner, "player_stats": []}

        res = await client.post(f"/api/v1/matches/{mid}/result", headers=auth_headers(token), json={
            "winner_id": t1,
            "game_stats": [game(1, 13, 5, t1), game(2, 9, 13, t2), game(3, 13, 11, t1)],
        })
        assert res.status_code == 204, res.text
        result = (await db.execute(
            select(MatchResult).where(MatchResult.match_id == mid)
        )).scalar_one()
        assert (result.winner_score, result.loser_score) == (2, 1)

    @pytest.mark.asyncio
    async def test_ゲームの勝者は参加チームに限る(self, client: AsyncClient, db):
        owner, _, match = await _ongoing_match(db)
        outsider = await f.make_team(db, owner=owner, name="Outsider", tag="OUT")
        token = _token(owner)
        mid = match.id
        assert (await client.patch(f"/api/v1/matches/{mid}/start",
                                   headers=auth_headers(token))).status_code == 204
        res = await client.post(f"/api/v1/matches/{mid}/result", headers=auth_headers(token), json={
            "winner_id": str(match.team1_id),
            "game_stats": [{"game_number": 1, "map_id": "ascent", "team1_score": 13,
                            "team2_score": 5, "winner_id": str(outsider.id), "player_stats": []}],
        })
        assert res.status_code == 400, res.text
        await db.refresh(match)
        assert match.status == MatchStatus.ONGOING

    @pytest.mark.asyncio
    async def test_BanPickは主催者以外は登録できない(self, client: AsyncClient, db):
        _owner, _, match = await _ongoing_match(db)
        player = _token(await f.make_user(db, role=UserRole.PLAYER))
        other = _token(await f.make_user(db, role=UserRole.ORGANIZER))
        body = {"team_id": str(match.team1_id), "action": "ban", "map_id": "ascent", "order": 1}

        for token in (player, other):
            res = await client.post(f"/api/v1/matches/{match.id}/banpick",
                                    headers=auth_headers(token), json=body)
            assert res.status_code == 403, res.text

    @pytest.mark.asyncio
    async def test_BanPickのチームは参加チームに限る(self, client: AsyncClient, db):
        owner, _, match = await _ongoing_match(db)
        outsider = await f.make_team(db, owner=owner, name="Outsider BP", tag="OBP")
        res = await client.post(
            f"/api/v1/matches/{match.id}/banpick", headers=auth_headers(_token(owner)),
            json={"team_id": str(outsider.id), "action": "ban", "map_id": "ascent", "order": 1},
        )
        assert res.status_code == 400, res.text


class TestAdminUserManagement:
    @pytest.mark.asyncio
    async def test_管理者以外はユーザー管理を使えない(self, client: AsyncClient, db):
        org = _token(await f.make_user(db, role=UserRole.ORGANIZER))
        target = await f.make_user(db)
        assert (await client.get("/api/v1/admin/users", headers=auth_headers(org))).status_code == 403
        res = await client.patch(f"/api/v1/admin/users/{target.id}", headers=auth_headers(org),
                                 json={"is_active": False})
        assert res.status_code == 403

    @pytest.mark.asyncio
    async def test_停止したユーザーは以後認証を通らず操作は監査に残る(self, client: AsyncClient, db):
        admin = await f.make_user(db, role=UserRole.ADMIN)
        target = await f.make_user(db, username="suspend_me")
        target_token = _token(target)
        assert (await client.get("/api/v1/auth/me", headers=auth_headers(target_token))).status_code == 200

        found = (await client.get("/api/v1/admin/users", params={"q": "suspend_me"},
                                  headers=auth_headers(_token(admin)))).json()["data"]
        assert [u["id"] for u in found] == [str(target.id)]

        res = await client.patch(f"/api/v1/admin/users/{target.id}", headers=auth_headers(_token(admin)),
                                 json={"is_active": False, "role": "organizer"})
        assert res.status_code == 200, res.text
        assert (res.json()["data"]["is_active"], res.json()["data"]["role"]) == (False, "organizer")
        assert (await client.get("/api/v1/auth/me", headers=auth_headers(target_token))).status_code == 401

        audit = (await client.get("/api/v1/admin/audit", params={"entity_type": "user"},
                                  headers=auth_headers(_token(admin)))).json()["data"]
        assert len(audit) == 2

    @pytest.mark.asyncio
    async def test_自分自身は変更できない(self, client: AsyncClient, db):
        admin = await f.make_user(db, role=UserRole.ADMIN)
        res = await client.patch(f"/api/v1/admin/users/{admin.id}", headers=auth_headers(_token(admin)),
                                 json={"role": "player"})
        assert res.status_code == 400


class TestTournamentVisibility:
    @pytest.mark.asyncio
    async def test_一覧と検索には公開中の大会だけが出る(self, client: AsyncClient, db):
        org = await f.make_user(db, role=UserRole.ORGANIZER)
        shown = await f.make_tournament(db, organizer=org, name="Visible Cup")
        hidden = [
            await f.make_tournament(db, organizer=org, name="Visible Private", visibility="private"),
            await f.make_tournament(db, organizer=org, name="Visible Limited", visibility="limited"),
            await f.make_tournament(db, organizer=org, name="Visible Draft",
                                    status=TournamentStatus.DRAFT),
        ]

        listed = {t["id"] for t in (await client.get("/api/v1/tournaments")).json()["data"]}
        assert str(shown.id) in listed
        assert not listed & {str(t.id) for t in hidden}

        res = await client.get("/api/v1/search", params={"q": "Visible", "types": "tournament"})
        assert res.status_code == 200, res.text
        found = {h["id"] for h in res.json()["data"]["tournaments"]}
        assert found == {str(shown.id)}

        trending = (await client.get("/api/v1/home/trending")).json()["data"]
        trending_ids = {t["id"] for t in trending.get("tournaments", [])}
        assert not trending_ids & {str(t.id) for t in hidden}

    @pytest.mark.asyncio
    async def test_限定公開と非公開はURLで直接開ける(self, client: AsyncClient, db):
        org = await f.make_user(db, role=UserRole.ORGANIZER)
        for visibility in ("limited", "private"):
            t = await f.make_tournament(db, organizer=org, visibility=visibility)
            res = await client.get(f"/api/v1/tournaments/{t.id}")
            assert res.status_code == 200, res.text
