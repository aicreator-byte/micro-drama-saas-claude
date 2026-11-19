"""Dashboard stats tests (future-dev 2f): real counts from the DB."""
import pytest
from httpx import AsyncClient

TEST_PASSWORD = "TestPass123!"


async def _auth_headers(async_client: AsyncClient, email: str, username: str) -> dict:
    await async_client.post("/api/auth/register", json={
        "email": email, "username": username, "password": TEST_PASSWORD,
    })
    login = await async_client.post("/api/auth/login", json={
        "email": email, "password": TEST_PASSWORD,
    })
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


async def _make_project(async_client: AsyncClient, headers: dict) -> str:
    res = await async_client.post("/api/projects", json={"title": "P"}, headers=headers)
    assert res.status_code == 201
    return res.json()["id"]


@pytest.mark.anyio
async def test_dashboard_stats_counts_real_data(async_client: AsyncClient):
    """Counts reflect what is actually in the DB — no hardcoded 0."""
    headers = await _auth_headers(async_client, "stats@example.com", "statsuser")
    project_id = await _make_project(async_client, headers)

    res = await async_client.get("/api/dashboard/stats", headers=headers)
    assert res.status_code == 200
    assert res.json() == {
        "projects": 1, "characters": 0, "locations": 0, "episodes": 0,
    }

    for name in ("Ana", "Budi"):
        res = await async_client.post(
            f"/api/characters/{project_id}", json={"name": name}, headers=headers
        )
        assert res.status_code == 201
    res = await async_client.post(
        f"/api/locations/{project_id}", json={"name": "Penthouse"}, headers=headers
    )
    assert res.status_code == 201
    for number in (1, 2):
        res = await async_client.post(
            f"/api/episodes/{project_id}",
            json={"episode_number": number, "title": f"Ep {number}"},
            headers=headers,
        )
        assert res.status_code == 201

    res = await async_client.get("/api/dashboard/stats", headers=headers)
    assert res.status_code == 200
    assert res.json() == {
        "projects": 1, "characters": 2, "locations": 1, "episodes": 2,
    }

    # A second project bumps only the project count.
    await _make_project(async_client, headers)
    res = await async_client.get("/api/dashboard/stats", headers=headers)
    assert res.json()["projects"] == 2
    assert res.json()["characters"] == 2


@pytest.mark.anyio
async def test_dashboard_stats_is_user_scoped(async_client: AsyncClient):
    """Another user's content must not leak into my stats."""
    headers_a = await _auth_headers(async_client, "a@example.com", "usera")
    project_a = await _make_project(async_client, headers_a)
    await async_client.post(
        f"/api/characters/{project_a}", json={"name": "Ana"}, headers=headers_a
    )

    headers_b = await _auth_headers(async_client, "b@example.com", "userb")
    res = await async_client.get("/api/dashboard/stats", headers=headers_b)
    assert res.status_code == 200
    assert res.json() == {
        "projects": 0, "characters": 0, "locations": 0, "episodes": 0,
    }


@pytest.mark.anyio
async def test_dashboard_stats_requires_auth(async_client: AsyncClient):
    res = await async_client.get("/api/dashboard/stats")
    assert res.status_code == 401
