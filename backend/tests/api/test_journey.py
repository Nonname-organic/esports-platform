"""主要ユーザーフローを HTTP 経由で最初から最後まで通す統合テスト（ブラウザは使わない）。

主催者: 登録 → ログイン → 大会作成 → 受付開始 → 申請の承認 → 受付終了 → ブラケット生成
        → 試合開始・スコア・結果確定 → 大会終了
チーム: 登録 → ログイン → チーム作成 → 大会検索・詳細 → 参加申請 → 申請状況 → 対戦カード → 結果確認
権限  : 参加者や他の主催者による運営操作・他人の大会データの閲覧を拒否する
"""
import random

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app

PASSWORD = "Passw0rd1"


@pytest_asyncio.fixture
async def journey_client(client: AsyncClient):
    """登録・ログインは IP ごとに窓あたり 5 回・10 回までに絞られている。

    他のテストと同じ IP から叩くと全体実行で 429 になるため、テストごとに別の
    IP から送る（依存の差し替えは client フィクスチャが app に設定済み）。
    """
    ip = "10." + ".".join(str(random.randint(1, 254)) for _ in range(3))
    async with AsyncClient(
        transport=ASGITransport(app=app, client=(ip, 50000)), base_url="http://localhost"
    ) as c:
        yield c


async def _signup(client: AsyncClient, name: str, role: str = "player") -> dict:
    email = f"{name}@example.com"  # .test は予約名としてメール検証で弾かれる
    res = await client.post("/api/v1/auth/register", json={
        "email": email, "username": name, "password": PASSWORD, "role": role,
    })
    assert res.status_code == 201, res.text
    res = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


async def _create_team(client: AsyncClient, headers: dict, name: str, tag: str) -> str:
    # RC4: 選手のプロフィールを先に作ると、チームの作成者自身の所属（self）ができる
    res = await client.post("/api/v1/players", headers=headers,
                            json={"game": "VALORANT", "riot_id": f"{tag}cap#JP1"})
    assert res.status_code == 201, res.text
    res = await client.post("/api/v1/teams", headers=headers,
                            json={"name": name, "tag": tag, "game": "VALORANT"})
    assert res.status_code == 201, res.text
    return res.json()["data"]["id"]


async def _set_status(client: AsyncClient, headers: dict, tid: str, status: str):
    return await client.patch(f"/api/v1/tournaments/{tid}/status", headers=headers,
                              json={"status": status})


@pytest.mark.asyncio
async def test_主催者とチームの一連の流れ(journey_client: AsyncClient):
    client = journey_client
    org = await _signup(client, "journey_org", "organizer")
    rival = await _signup(client, "journey_rival", "organizer")
    cap_a = await _signup(client, "journey_cap_a")
    cap_b = await _signup(client, "journey_cap_b")

    team_a = await _create_team(client, cap_a, "Journey Alpha", "JRA")
    team_b = await _create_team(client, cap_b, "Journey Bravo", "JRB")

    # ── 大会作成（下書きは一覧に出ない） ──────────────────────────────
    res = await client.post("/api/v1/tournaments", headers=org, json={
        "name": "Journey Cup", "game": "VALORANT", "format": "single_elimination", "max_teams": 4,
        "lineup_size": 1, "roster_max": 2,
    })
    assert res.status_code == 201, res.text
    tid = res.json()["data"]["id"]
    assert res.json()["data"]["status"] == "draft"
    listed = {t["id"] for t in (await client.get("/api/v1/tournaments")).json()["data"]}
    assert tid not in listed

    assert (await _set_status(client, rival, tid, "registration_open")).status_code == 403
    assert (await _set_status(client, org, tid, "registration_open")).status_code == 200

    # ── チーム側: 検索・詳細・申請 ─────────────────────────────────────
    res = await client.get("/api/v1/search", params={"q": "Journey Cup", "types": "tournament"})
    assert tid in {h["id"] for h in res.json()["data"]["tournaments"]}
    assert (await client.get(f"/api/v1/tournaments/{tid}")).status_code == 200

    # 他人のチームでは申請できない
    res = await client.post(f"/api/v1/tournaments/{tid}/register", headers=cap_a,
                            json={"team_id": team_b})
    assert res.status_code == 403, res.text
    for headers, team in ((cap_a, team_a), (cap_b, team_b)):
        res = await client.post(f"/api/v1/tournaments/{tid}/register", headers=headers,
                                json={"team_id": team})
        assert res.status_code == 201, res.text
        assert res.json()["data"]["status"] == "pending"

    mine = (await client.get(f"/api/v1/tournaments/{tid}/my-registration", headers=cap_a)).json()
    assert mine["data"]["registered"] is True and mine["data"]["status"] == "pending"

    # ── 主催者側: 審査（参加者・他の主催者は見られない） ─────────────────
    assert (await client.get(f"/api/v1/tournaments/{tid}/registrations",
                             headers=cap_a)).status_code == 403
    assert (await client.get(f"/api/v1/tournaments/{tid}/registrations",
                             headers=rival)).status_code == 403
    regs = (await client.get(f"/api/v1/tournaments/{tid}/registrations", headers=org)).json()["data"]
    assert {r["team_id"] for r in regs} == {team_a, team_b}

    res = await client.patch(f"/api/v1/tournaments/{tid}/registrations/{regs[0]['id']}",
                             params={"status": "approved"}, headers=rival)
    assert res.status_code == 403
    for r in regs:
        res = await client.patch(f"/api/v1/tournaments/{tid}/registrations/{r['id']}",
                                 params={"status": "approved"}, headers=org)
        assert res.status_code == 200, res.text
        assert res.json()["data"]["status"] == "approved"

    # ── RC4: 名簿（キャプテンが自分を載せ、本人が参加を承認する） ─────────────
    for r in regs:
        headers = cap_a if r["team_id"] == team_a else cap_b
        me = (await client.get(f"/api/v1/teams/{r['team_id']}/members")).json()["data"][0]
        assert me["consent"] == "self"
        res = await client.post(f"/api/v1/tournaments/{tid}/registrations/{r['id']}/roster", headers=headers,
                                json={"player_id": me["player_id"]})
        assert res.status_code == 201, res.text
        assert res.json()["data"]["status"] == "invited"
        res = await client.post(f"/api/v1/roster-entries/{res.json()['data']['id']}/accept", headers=headers)
        assert res.status_code == 200 and res.json()["data"]["status"] == "accepted", res.text

    # ── 受付終了 → ブラケット生成 ──────────────────────────────────────
    assert (await _set_status(client, org, tid, "registration_closed")).status_code == 200
    for headers in (cap_a, rival):
        assert (await client.post(f"/api/v1/tournaments/{tid}/bracket",
                                  headers=headers)).status_code == 403
    assert (await client.post(f"/api/v1/tournaments/{tid}/bracket", headers=org)).status_code == 201
    assert (await _set_status(client, org, tid, "ongoing")).status_code == 200

    # ── 対戦カード（参加者も見られる） → 試合進行 ─────────────────────────
    matches = (await client.get("/api/v1/matches", params={"tournament_id": tid},
                                headers=cap_b)).json()["data"]
    match = next(m for m in matches if m["team1"] and m["team2"])
    mid = match["id"]
    assert {match["team1"]["id"], match["team2"]["id"]} == {team_a, team_b}

    assert (await client.patch(f"/api/v1/matches/{mid}/start", headers=rival)).status_code == 403
    assert (await client.patch(f"/api/v1/matches/{mid}/start", headers=org)).status_code == 204
    res = await client.post(f"/api/v1/matches/{mid}/games/1/score", headers=org,
                            json={"team1_score": 13, "team2_score": 9})
    assert res.status_code == 204, res.text
    assert (await client.post(f"/api/v1/matches/{mid}/result", headers=cap_a,
                              json={"winner_id": team_a})).status_code == 403
    assert (await client.post(f"/api/v1/matches/{mid}/result", headers=org,
                              json={"winner_id": team_a})).status_code == 204

    # ── 結果確認（参加チーム側から） ────────────────────────────────────
    detail = (await client.get(f"/api/v1/matches/{mid}", headers=cap_b)).json()["data"]
    assert detail["status"] == "completed"
    assert detail["winner_id"] == team_a

    # ── 大会終了（他の主催者は終了できず、監査ログも見られない） ─────────────
    assert (await _set_status(client, rival, tid, "completed")).status_code == 403
    assert (await client.get(f"/api/v1/tournaments/{tid}/audit", headers=rival)).status_code == 403
    assert (await _set_status(client, org, tid, "completed")).status_code == 200
    final = (await client.get(f"/api/v1/tournaments/{tid}")).json()["data"]
    assert final["status"] == "completed"


@pytest.mark.asyncio
async def test_作成画面で非公開を選んだ大会は一覧に出ない(journey_client: AsyncClient):
    client = journey_client
    org = await _signup(client, "journey_private_org", "organizer")
    res = await client.post("/api/v1/tournaments", headers=org, json={
        "name": "Hidden Journey Cup", "game": "VALORANT", "format": "single_elimination",
        "rules": {"visibility": "private"},
    })
    assert res.status_code == 201, res.text
    tid = res.json()["data"]["id"]
    assert res.json()["data"]["visibility"] == "private"
    assert (await _set_status(client, org, tid, "registration_open")).status_code == 200

    listed = {t["id"] for t in (await client.get("/api/v1/tournaments")).json()["data"]}
    assert tid not in listed
    # URL を知っている人は開ける
    assert (await client.get(f"/api/v1/tournaments/{tid}")).status_code == 200
