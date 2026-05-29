import pytest
from httpx import AsyncClient

from app.models.user import User


@pytest.mark.asyncio
async def test_create_tournament_success(
    client: AsyncClient, organizer_token: str
):
    response = await client.post(
        "/api/v1/tournaments",
        json={
            "name": "VALORANT Japan Open 2024",
            "game": "VALORANT",
            "format": "single_elimination",
            "max_teams": 8,
        },
        headers={"Authorization": f"Bearer {organizer_token}"},
    )
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["name"] == "VALORANT Japan Open 2024"
    assert data["game"] == "VALORANT"
    assert data["status"] == "draft"


@pytest.mark.asyncio
async def test_create_tournament_unauthorized(client: AsyncClient):
    response = await client.post(
        "/api/v1/tournaments",
        json={
            "name": "Test Tournament",
            "game": "VALORANT",
            "format": "single_elimination",
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_tournaments(client: AsyncClient, organizer_token: str):
    # 作成
    await client.post(
        "/api/v1/tournaments",
        json={
            "name": "Tournament 1",
            "game": "VALORANT",
            "format": "single_elimination",
        },
        headers={"Authorization": f"Bearer {organizer_token}"},
    )

    response = await client.get("/api/v1/tournaments")
    assert response.status_code == 200
    body = response.json()
    assert "data" in body
    assert "meta" in body


@pytest.mark.asyncio
async def test_get_tournament_not_found(client: AsyncClient):
    import uuid
    response = await client.get(f"/api/v1/tournaments/{uuid.uuid4()}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_registration_closed_raises_error(
    client: AsyncClient, organizer_token: str
):
    create_resp = await client.post(
        "/api/v1/tournaments",
        json={
            "name": "Closed Tournament",
            "game": "VALORANT",
            "format": "single_elimination",
            "status": "completed",
        },
        headers={"Authorization": f"Bearer {organizer_token}"},
    )
    tournament_id = create_resp.json()["data"]["id"]

    import uuid
    register_resp = await client.post(
        f"/api/v1/tournaments/{tournament_id}/register",
        json={"team_id": str(uuid.uuid4())},
        headers={"Authorization": f"Bearer {organizer_token}"},
    )
    # draft状態なので申請不可
    assert register_resp.status_code == 400
