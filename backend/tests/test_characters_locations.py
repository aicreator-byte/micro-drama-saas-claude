"""Characters and Locations tests"""
import pytest
from httpx import AsyncClient


async def get_auth_headers(client: AsyncClient, email: str = "test@example.com", username: str = "testuser") -> dict:
    """Helper to register, login and get auth headers"""
    await client.post("/api/auth/register", json={
        "email": email,
        "username": username,
        "password": "password123",
    })
    login_response = await client.post("/api/auth/login", json={
        "email": email,
        "password": "password123",
    })
    access_token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {access_token}"}


async def create_project(client: AsyncClient, headers: dict, title: str = "Test Project") -> str:
    """Helper to create a project and return its ID"""
    response = await client.post("/api/projects", json={"title": title}, headers=headers)
    return response.json()["id"]


# Character tests
@pytest.mark.anyio
async def test_create_character(async_client: AsyncClient):
    """Test creating a character"""
    headers = await get_auth_headers(async_client)
    project_id = await create_project(async_client, headers)

    response = await async_client.post(f"/api/characters/{project_id}", json={
        "name": "John Doe",
        "role": "protagonist",
        "physical_appearance": "Tall, dark hair, blue eyes",
        "personality": "Brave, determined",
        "background": "Former soldier",
        "costume": "Tactical gear",
        "consistency_instructions": "Always show scar on left cheek",
    }, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "John Doe"
    assert data["role"] == "protagonist"
    assert data["display_order"] == 0


@pytest.mark.anyio
async def test_list_characters(async_client: AsyncClient):
    """Test listing characters"""
    headers = await get_auth_headers(async_client)
    project_id = await create_project(async_client, headers)

    await async_client.post(f"/api/characters/{project_id}", json={"name": "Character 1"}, headers=headers)
    await async_client.post(f"/api/characters/{project_id}", json={"name": "Character 2"}, headers=headers)

    response = await async_client.get(f"/api/characters/{project_id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


@pytest.mark.anyio
async def test_get_character(async_client: AsyncClient):
    """Test getting a specific character"""
    headers = await get_auth_headers(async_client)
    project_id = await create_project(async_client, headers)

    create_response = await async_client.post(f"/api/characters/{project_id}", json={"name": "Test Character"}, headers=headers)
    character_id = create_response.json()["id"]

    response = await async_client.get(f"/api/characters/{project_id}/{character_id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == character_id
    assert data["name"] == "Test Character"


@pytest.mark.anyio
async def test_update_character(async_client: AsyncClient):
    """Test updating a character"""
    headers = await get_auth_headers(async_client)
    project_id = await create_project(async_client, headers)

    create_response = await async_client.post(f"/api/characters/{project_id}", json={"name": "Original Name"}, headers=headers)
    character_id = create_response.json()["id"]

    response = await async_client.patch(f"/api/characters/{project_id}/{character_id}", json={
        "name": "Updated Name",
        "role": "antagonist",
    }, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Name"
    assert data["role"] == "antagonist"


@pytest.mark.anyio
async def test_delete_character(async_client: AsyncClient):
    """Test soft deleting a character"""
    headers = await get_auth_headers(async_client)
    project_id = await create_project(async_client, headers)

    create_response = await async_client.post(f"/api/characters/{project_id}", json={"name": "To Delete"}, headers=headers)
    character_id = create_response.json()["id"]

    response = await async_client.delete(f"/api/characters/{project_id}/{character_id}", headers=headers)
    assert response.status_code == 204

    list_response = await async_client.get(f"/api/characters/{project_id}", headers=headers)
    assert len(list_response.json()) == 0


@pytest.mark.anyio
async def test_reorder_characters(async_client: AsyncClient):
    """Test reordering characters"""
    headers = await get_auth_headers(async_client)
    project_id = await create_project(async_client, headers)

    c1 = await async_client.post(f"/api/characters/{project_id}", json={"name": "Char 1"}, headers=headers)
    c2 = await async_client.post(f"/api/characters/{project_id}", json={"name": "Char 2"}, headers=headers)
    c3 = await async_client.post(f"/api/characters/{project_id}", json={"name": "Char 3"}, headers=headers)

    ids = [c1.json()["id"], c2.json()["id"], c3.json()["id"]]

    # Reverse order
    response = await async_client.post(f"/api/characters/{project_id}/reorder", json={
        "character_ids": [ids[2], ids[1], ids[0]]
    }, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data[0]["name"] == "Char 3"
    assert data[1]["name"] == "Char 2"
    assert data[2]["name"] == "Char 1"


@pytest.mark.anyio
async def test_character_tenant_isolation(async_client: AsyncClient):
    """Test character tenant isolation"""
    headers1 = await get_auth_headers(async_client, "user1@example.com", "user1")
    project_id = await create_project(async_client, headers1, "User 1 Project")

    create_response = await async_client.post(f"/api/characters/{project_id}", json={"name": "User 1 Char"}, headers=headers1)
    character_id = create_response.json()["id"]

    headers2 = await get_auth_headers(async_client, "user2@example.com", "user2")
    response = await async_client.get(f"/api/characters/{project_id}/{character_id}", headers=headers2)
    assert response.status_code == 404


# Location tests
@pytest.mark.anyio
async def test_create_location(async_client: AsyncClient):
    """Test creating a location"""
    headers = await get_auth_headers(async_client)
    project_id = await create_project(async_client, headers)

    response = await async_client.post(f"/api/locations/{project_id}", json={
        "name": "Main Street",
        "description": "Busy downtown street",
        "environment": "Urban, outdoor",
        "lighting": "Natural daylight",
        "atmosphere": "Bustling, energetic",
        "consistency_instructions": "Always show the clock tower in background",
    }, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Main Street"
    assert data["environment"] == "Urban, outdoor"
    assert data["display_order"] == 0


@pytest.mark.anyio
async def test_list_locations(async_client: AsyncClient):
    """Test listing locations"""
    headers = await get_auth_headers(async_client)
    project_id = await create_project(async_client, headers)

    await async_client.post(f"/api/locations/{project_id}", json={"name": "Location 1"}, headers=headers)
    await async_client.post(f"/api/locations/{project_id}", json={"name": "Location 2"}, headers=headers)

    response = await async_client.get(f"/api/locations/{project_id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


@pytest.mark.anyio
async def test_get_location(async_client: AsyncClient):
    """Test getting a specific location"""
    headers = await get_auth_headers(async_client)
    project_id = await create_project(async_client, headers)

    create_response = await async_client.post(f"/api/locations/{project_id}", json={"name": "Test Location"}, headers=headers)
    location_id = create_response.json()["id"]

    response = await async_client.get(f"/api/locations/{project_id}/{location_id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == location_id
    assert data["name"] == "Test Location"


@pytest.mark.anyio
async def test_update_location(async_client: AsyncClient):
    """Test updating a location"""
    headers = await get_auth_headers(async_client)
    project_id = await create_project(async_client, headers)

    create_response = await async_client.post(f"/api/locations/{project_id}", json={"name": "Original Location"}, headers=headers)
    location_id = create_response.json()["id"]

    response = await async_client.patch(f"/api/locations/{project_id}/{location_id}", json={
        "name": "Updated Location",
        "atmosphere": "Quiet and peaceful",
    }, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Location"
    assert data["atmosphere"] == "Quiet and peaceful"


@pytest.mark.anyio
async def test_delete_location(async_client: AsyncClient):
    """Test deleting a location"""
    headers = await get_auth_headers(async_client)
    project_id = await create_project(async_client, headers)

    create_response = await async_client.post(f"/api/locations/{project_id}", json={"name": "To Delete"}, headers=headers)
    location_id = create_response.json()["id"]

    response = await async_client.delete(f"/api/locations/{project_id}/{location_id}", headers=headers)
    assert response.status_code == 204

    list_response = await async_client.get(f"/api/locations/{project_id}", headers=headers)
    assert len(list_response.json()) == 0


@pytest.mark.anyio
async def test_reorder_locations(async_client: AsyncClient):
    """Test reordering locations"""
    headers = await get_auth_headers(async_client)
    project_id = await create_project(async_client, headers)

    l1 = await async_client.post(f"/api/locations/{project_id}", json={"name": "Loc 1"}, headers=headers)
    l2 = await async_client.post(f"/api/locations/{project_id}", json={"name": "Loc 2"}, headers=headers)

    ids = [l1.json()["id"], l2.json()["id"]]

    response = await async_client.post(f"/api/locations/{project_id}/reorder", json={
        "location_ids": [ids[1], ids[0]]
    }, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data[0]["name"] == "Loc 2"
    assert data[1]["name"] == "Loc 1"


@pytest.mark.anyio
async def test_location_tenant_isolation(async_client: AsyncClient):
    """Test location tenant isolation"""
    headers1 = await get_auth_headers(async_client, "user1@example.com", "user1")
    project_id = await create_project(async_client, headers1, "User 1 Project")

    create_response = await async_client.post(f"/api/locations/{project_id}", json={"name": "User 1 Location"}, headers=headers1)
    location_id = create_response.json()["id"]

    headers2 = await get_auth_headers(async_client, "user2@example.com", "user2")
    response = await async_client.get(f"/api/locations/{project_id}/{location_id}", headers=headers2)
    assert response.status_code == 404