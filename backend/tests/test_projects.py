"""Projects tests"""
import pytest
from httpx import AsyncClient

TEST_PASSWORD = "testpass123"


async def get_auth_headers(async_client: AsyncClient, email: str = "test@example.com", username: str = "testuser") -> dict:
    """Helper to register, login and get auth headers"""
    await async_client.post("/api/auth/register", json={
        "email": email,
        "username": username,
        "password": TEST_PASSWORD,
    })
    login_response = await async_client.post("/api/auth/login", json={
        "email": email,
        "password": TEST_PASSWORD,
    })
    access_token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {access_token}"}


@pytest.mark.anyio
async def test_create_project(async_client: AsyncClient):
    """Test creating a project"""
    headers = await get_auth_headers(async_client)
    response = await async_client.post("/api/projects", json={
        "title": "My Drama Series",
        "description": "A test drama series",
        "genre": "drama",
        "themes": "redemption,identity",
    }, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "My Drama Series"
    assert data["description"] == "A test drama series"
    assert data["genre"] == "drama"
    assert data["themes"] == "redemption,identity"
    assert data["status"] == "draft"
    assert "id" in data


@pytest.mark.anyio
async def test_list_projects(async_client: AsyncClient):
    """Test listing projects"""
    headers = await get_auth_headers(async_client)
    # Create a few projects
    await async_client.post("/api/projects", json={"title": "Project 1"}, headers=headers)
    await async_client.post("/api/projects", json={"title": "Project 2"}, headers=headers)

    response = await async_client.get("/api/projects", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2
    assert data["page"] == 1


@pytest.mark.anyio
async def test_list_projects_pagination(async_client: AsyncClient):
    """Test project pagination"""
    headers = await get_auth_headers(async_client)
    for i in range(5):
        await async_client.post("/api/projects", json={"title": f"Project {i}"}, headers=headers)

    response = await async_client.get("/api/projects?page=1&page_size=2", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 2
    assert data["total"] == 5
    assert data["total_pages"] == 3


@pytest.mark.anyio
async def test_get_project(async_client: AsyncClient):
    """Test getting a specific project"""
    headers = await get_auth_headers(async_client)
    create_response = await async_client.post("/api/projects", json={"title": "Test Project"}, headers=headers)
    project_id = create_response.json()["id"]

    response = await async_client.get(f"/api/projects/{project_id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == project_id
    assert data["title"] == "Test Project"


@pytest.mark.anyio
async def test_get_nonexistent_project(async_client: AsyncClient):
    """Test getting nonexistent project fails"""
    headers = await get_auth_headers(async_client)
    import uuid
    response = await async_client.get(f"/api/projects/{uuid.uuid4()}", headers=headers)
    assert response.status_code == 404


@pytest.mark.anyio
async def test_update_project(async_client: AsyncClient):
    """Test updating a project"""
    headers = await get_auth_headers(async_client)
    create_response = await async_client.post("/api/projects", json={"title": "Original Title"}, headers=headers)
    project_id = create_response.json()["id"]

    response = await async_client.patch(f"/api/projects/{project_id}", json={
        "title": "Updated Title",
        "genre": "comedy",
        "status": "in_production",
    }, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Title"
    assert data["genre"] == "comedy"
    assert data["status"] == "in_production"


@pytest.mark.anyio
async def test_delete_project(async_client: AsyncClient):
    """Test soft deleting a project"""
    headers = await get_auth_headers(async_client)
    create_response = await async_client.post("/api/projects", json={"title": "To Delete"}, headers=headers)
    project_id = create_response.json()["id"]

    response = await async_client.delete(f"/api/projects/{project_id}", headers=headers)
    assert response.status_code == 204

    # Verify it's gone from list
    list_response = await async_client.get("/api/projects", headers=headers)
    assert list_response.json()["total"] == 0


@pytest.mark.anyio
async def test_tenant_isolation(async_client: AsyncClient):
    """Test that users cannot access each other's projects"""
    # User 1 creates a project
    headers1 = await get_auth_headers(async_client, "user1@example.com", "user1")
    create_response = await async_client.post("/api/projects", json={"title": "User 1 Project"}, headers=headers1)
    project_id = create_response.json()["id"]

    # User 2 tries to access User 1's project
    headers2 = await get_auth_headers(async_client, "user2@example.com", "user2")
    response = await async_client.get(f"/api/projects/{project_id}", headers=headers2)
    assert response.status_code == 404

    # User 2's list should be empty
    list_response = await async_client.get("/api/projects", headers=headers2)
    assert list_response.json()["total"] == 0