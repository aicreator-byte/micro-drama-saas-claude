"""Authentication tests"""
import pytest
from httpx import AsyncClient

# Use short passwords (< 72 bytes) to avoid bcrypt issues
TEST_PASSWORD = "testpass123"


@pytest.mark.anyio
async def test_register_user(async_client):
    """Test user registration"""
    response = await async_client.post("/api/auth/register", json={
        "email": "test@example.com",
        "username": "testuser",
        "password": TEST_PASSWORD,
        "full_name": "Test User"
    })
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["username"] == "testuser"
    assert data["full_name"] == "Test User"
    assert "id" in data
    assert "hashed_password" not in data


@pytest.mark.anyio
async def test_register_duplicate_email(async_client):
    """Test duplicate email registration fails"""
    # First registration
    await async_client.post("/api/auth/register", json={
        "email": "duplicate@example.com",
        "username": "user1",
        "password": TEST_PASSWORD,
    })
    # Second registration with same email
    response = await async_client.post("/api/auth/register", json={
        "email": "duplicate@example.com",
        "username": "user2",
        "password": TEST_PASSWORD,
    })
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"]


@pytest.mark.anyio
async def test_register_duplicate_username(async_client):
    """Test duplicate username registration fails"""
    await async_client.post("/api/auth/register", json={
        "email": "user1@example.com",
        "username": "sameuser",
        "password": TEST_PASSWORD,
    })
    response = await async_client.post("/api/auth/register", json={
        "email": "user2@example.com",
        "username": "sameuser",
        "password": TEST_PASSWORD,
    })
    assert response.status_code == 400
    assert "already taken" in response.json()["detail"]


@pytest.mark.anyio
async def test_login_success(async_client):
    """Test successful login"""
    # Register first
    await async_client.post("/api/auth/register", json={
        "email": "login@example.com",
        "username": "loginuser",
        "password": TEST_PASSWORD,
    })
    # Login
    response = await async_client.post("/api/auth/login", json={
        "email": "login@example.com",
        "password": TEST_PASSWORD,
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.anyio
async def test_login_wrong_password(async_client):
    """Test login with wrong password fails"""
    await async_client.post("/api/auth/register", json={
        "email": "wrongpass@example.com",
        "username": "wrongpassuser",
        "password": TEST_PASSWORD,
    })
    response = await async_client.post("/api/auth/login", json={
        "email": "wrongpass@example.com",
        "password": "wrongpassword",
    })
    assert response.status_code == 401
    assert "Invalid credentials" in response.json()["detail"]


@pytest.mark.anyio
async def test_login_nonexistent_user(async_client):
    """Test login with nonexistent user fails"""
    response = await async_client.post("/api/auth/login", json={
        "email": "nonexistent@example.com",
        "password": TEST_PASSWORD,
    })
    assert response.status_code == 401
    assert "Invalid credentials" in response.json()["detail"]


@pytest.mark.anyio
async def test_refresh_token(async_client):
    """Test token refresh"""
    await async_client.post("/api/auth/register", json={
        "email": "refresh@example.com",
        "username": "refreshuser",
        "password": TEST_PASSWORD,
    })
    login_response = await async_client.post("/api/auth/login", json={
        "email": "refresh@example.com",
        "password": TEST_PASSWORD,
    })
    refresh_token = login_response.json()["refresh_token"]

    response = await async_client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.anyio
async def test_invalid_refresh_token(async_client):
    """Test invalid refresh token fails"""
    response = await async_client.post("/api/auth/refresh", json={"refresh_token": "invalid-token"})
    assert response.status_code == 401
    assert "Invalid refresh token" in response.json()["detail"]


@pytest.mark.anyio
async def test_get_me(async_client):
    """Test getting current user info"""
    await async_client.post("/api/auth/register", json={
        "email": "me@example.com",
        "username": "meuser",
        "password": TEST_PASSWORD,
    })
    login_response = await async_client.post("/api/auth/login", json={
        "email": "me@example.com",
        "password": TEST_PASSWORD,
    })
    access_token = login_response.json()["access_token"]

    response = await async_client.get("/api/auth/me", headers={
        "Authorization": f"Bearer {access_token}"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "me@example.com"
    assert data["username"] == "meuser"


@pytest.mark.anyio
async def test_get_me_unauthorized(async_client):
    """Test getting user info without token fails"""
    response = await async_client.get("/api/auth/me")
    assert response.status_code == 401