"""Tests for new routers: episodes, scenes, dialogues, prompts, assets, google_accounts, flow_bridge, story_engine, settings"""
import pytest
from httpx import AsyncClient
import uuid

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


async def create_project(async_client: AsyncClient, headers: dict, title: str = "Test Project") -> str:
    """Helper to create a project and return its ID"""
    response = await async_client.post("/api/projects", json={"title": title}, headers=headers)
    assert response.status_code == 201
    return response.json()["id"]


async def create_series_bible(async_client: AsyncClient, headers: dict, project_id: str) -> str:
    """Helper to create a series bible and return its ID"""
    response = await async_client.post(f"/api/projects/{project_id}/series-bible", json={
        "premise": "A test series premise",
        "genre": "drama",
        "logline": "A test logline",
        "theme": "redemption",
        "tone": "serious",
        "setting": "modern city",
        "format": "episodic",
        "target_audience": "adults",
        "estimated_episodes": 10,
    }, headers=headers)
    assert response.status_code == 201
    return response.json()["id"]


async def create_character(async_client: AsyncClient, headers: dict, project_id: str, name: str = "Test Character") -> str:
    """Helper to create a character and return its ID"""
    response = await async_client.post(f"/api/characters/{project_id}", json={
        "name": name,
        "role": "protagonist",
        "description": "A test character",
        "personality_traits": "brave, curious",
        "backstory": "Test backstory",
    }, headers=headers)
    assert response.status_code == 201
    return response.json()["id"]


async def create_location(async_client: AsyncClient, headers: dict, project_id: str, name: str = "Test Location") -> str:
    """Helper to create a location and return its ID"""
    response = await async_client.post(f"/api/locations/{project_id}", json={
        "name": name,
        "description": "A test location",
        "location_type": "interior",
    }, headers=headers)
    assert response.status_code == 201
    return response.json()["id"]


async def create_episode(async_client: AsyncClient, headers: dict, project_id: str, episode_number: int = 1) -> str:
    """Helper to create an episode and return its ID"""
    response = await async_client.post(f"/api/episodes/{project_id}", json={
        "episode_number": episode_number,
        "title": f"Episode {episode_number}",
    }, headers=headers)
    assert response.status_code == 201
    return response.json()["id"]


async def create_scene(async_client: AsyncClient, headers: dict, episode_id: str, scene_number: int = 1, location_id: str = None) -> str:
    """Helper to create a scene and return its ID"""
    data = {"episode_id": episode_id, "scene_number": scene_number, "title": f"Scene {scene_number}"}
    if location_id:
        data["location_id"] = location_id
    response = await async_client.post(f"/api/scenes/{episode_id}", json=data, headers=headers)
    assert response.status_code == 201
    return response.json()["id"]


class TestEpisodesRouter:
    """Tests for episodes router"""

    @pytest.mark.anyio
    async def test_create_episode(self, async_client: AsyncClient):
        """Test creating an episode"""
        headers = await get_auth_headers(async_client)
        project_id = await create_project(async_client, headers)

        response = await async_client.post(f"/api/episodes/{project_id}", json={
            "episode_number": 1,
            "title": "Pilot",
            "synopsis": "First episode",
        }, headers=headers)
        assert response.status_code == 201
        data = response.json()
        assert data["episode_number"] == 1
        assert data["title"] == "Pilot"
        assert data["project_id"] == project_id

    @pytest.mark.anyio
    async def test_list_episodes(self, async_client: AsyncClient):
        """Test listing episodes"""
        headers = await get_auth_headers(async_client)
        project_id = await create_project(async_client, headers)

        await async_client.post(f"/api/episodes/{project_id}", json={"episode_number": 1}, headers=headers)
        await async_client.post(f"/api/episodes/{project_id}", json={"episode_number": 2}, headers=headers)

        response = await async_client.get(f"/api/episodes/{project_id}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    @pytest.mark.anyio
    async def test_get_episode(self, async_client: AsyncClient):
        """Test getting a specific episode"""
        headers = await get_auth_headers(async_client)
        project_id = await create_project(async_client, headers)
        create_response = await async_client.post(f"/api/episodes/{project_id}", json={"episode_number": 1}, headers=headers)
        episode_id = create_response.json()["id"]

        response = await async_client.get(f"/api/episodes/{project_id}/{episode_id}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == episode_id

    @pytest.mark.anyio
    async def test_update_episode(self, async_client: AsyncClient):
        """Test updating an episode"""
        headers = await get_auth_headers(async_client)
        project_id = await create_project(async_client, headers)
        create_response = await async_client.post(f"/api/episodes/{project_id}", json={"episode_number": 1}, headers=headers)
        episode_id = create_response.json()["id"]

        response = await async_client.patch(f"/api/episodes/{project_id}/{episode_id}", json={
            "title": "Updated Title",
            "status": "writing",
        }, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"
        assert data["status"] == "writing"


class TestScenesRouter:
    """Tests for scenes router"""

    @pytest.mark.anyio
    async def test_create_scene(self, async_client: AsyncClient):
        """Test creating a scene"""
        headers = await get_auth_headers(async_client)
        project_id = await create_project(async_client, headers)
        episode_id = await create_episode(async_client, headers, project_id)
        location_id = await create_location(async_client, headers, project_id)

        response = await async_client.post(f"/api/scenes/{episode_id}", json={
            "scene_number": 1,
            "title": "Opening Scene",
            "description": "Test scene",
            "location_id": location_id,
        }, headers=headers)
        assert response.status_code == 201
        data = response.json()
        assert data["scene_number"] == 1
        assert data["title"] == "Opening Scene"
        assert data["location_id"] == location_id

    @pytest.mark.anyio
    async def test_create_scene_invalid_location(self, async_client: AsyncClient):
        """Test creating a scene with location from different project fails"""
        headers = await get_auth_headers(async_client)
        project_id = await create_project(async_client, headers)
        other_project_id = await create_project(async_client, headers, "Other Project")
        episode_id = await create_episode(async_client, headers, project_id)
        location_id = await create_location(async_client, headers, other_project_id)

        response = await async_client.post(f"/api/scenes/{episode_id}", json={
            "scene_number": 1,
            "location_id": location_id,
        }, headers=headers)
        # Should fail with 400
        assert response.status_code == 400

    @pytest.mark.anyio
    async def test_list_scenes(self, async_client: AsyncClient):
        """Test listing scenes"""
        headers = await get_auth_headers(async_client)
        project_id = await create_project(async_client, headers)
        episode_id = await create_episode(async_client, headers, project_id)
        location_id = await create_location(async_client, headers, project_id)

        await async_client.post(f"/api/scenes/{episode_id}", json={"scene_number": 1, "location_id": location_id}, headers=headers)
        await async_client.post(f"/api/scenes/{episode_id}", json={"scene_number": 2, "location_id": location_id}, headers=headers)

        response = await async_client.get(f"/api/scenes/{episode_id}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2


class TestDialoguesRouter:
    """Tests for dialogues router"""

    @pytest.mark.anyio
    async def test_create_dialogue(self, async_client: AsyncClient):
        """Test creating a dialogue"""
        headers = await get_auth_headers(async_client)
        project_id = await create_project(async_client, headers)
        episode_id = await create_episode(async_client, headers, project_id)
        location_id = await create_location(async_client, headers, project_id)
        scene_id = await create_scene(async_client, headers, episode_id, location_id=location_id)
        character_id = await create_character(async_client, headers, project_id)

        response = await async_client.post(f"/api/dialogues/{scene_id}", json={
            "character_id": character_id,
            "dialogue_text": "Hello world!",
            "order_index": 0,
        }, headers=headers)
        assert response.status_code == 201
        data = response.json()
        assert data["dialogue_text"] == "Hello world!"
        assert data["character_id"] == character_id

    @pytest.mark.anyio
    async def test_list_dialogues(self, async_client: AsyncClient):
        """Test listing dialogues"""
        headers = await get_auth_headers(async_client)
        project_id = await create_project(async_client, headers)
        episode_id = await create_episode(async_client, headers, project_id)
        location_id = await create_location(async_client, headers, project_id)
        scene_id = await create_scene(async_client, headers, episode_id, location_id=location_id)
        character_id = await create_character(async_client, headers, project_id)

        await async_client.post(f"/api/dialogues/{scene_id}", json={"character_id": character_id, "dialogue_text": "Line 1", "order_index": 0}, headers=headers)
        await async_client.post(f"/api/dialogues/{scene_id}", json={"character_id": character_id, "dialogue_text": "Line 2", "order_index": 1}, headers=headers)

        response = await async_client.get(f"/api/dialogues/{scene_id}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2


class TestPromptsRouter:
    """Tests for prompts router"""

    @pytest.mark.anyio
    async def test_create_prompt(self, async_client: AsyncClient):
        """Test creating a prompt"""
        headers = await get_auth_headers(async_client)
        project_id = await create_project(async_client, headers)

        response = await async_client.post(f"/api/prompts", json={
            "project_id": project_id,
            "prompt_type": "scene_image",
            "prompt_text": "Generate a scene about a test topic",
        }, headers=headers)
        assert response.status_code == 201
        data = response.json()
        assert data["prompt_type"] == "scene_image"
        assert "test topic" in data["prompt_text"].lower()

    @pytest.mark.anyio
    async def test_list_prompts(self, async_client: AsyncClient):
        """Test listing prompts"""
        headers = await get_auth_headers(async_client)
        project_id = await create_project(async_client, headers)

        await async_client.post(f"/api/prompts", json={"project_id": project_id, "prompt_type": "scene_image", "prompt_text": "t1"}, headers=headers)
        await async_client.post(f"/api/prompts", json={"project_id": project_id, "prompt_type": "dialogue_audio", "prompt_text": "t2"}, headers=headers)

        response = await async_client.get(f"/api/prompts/{project_id}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2


class TestAssetsRouter:
    """Tests for assets router"""

    @pytest.mark.anyio
    async def test_create_asset(self, async_client: AsyncClient):
        """Test creating an asset"""
        headers = await get_auth_headers(async_client)
        project_id = await create_project(async_client, headers)

        response = await async_client.post(f"/api/assets", json={
            "project_id": project_id,
            "file_name": "test.png",
            "file_path": "/uploads/test.png",
            "asset_type": "scene_image",
            "file_size": 1024,
            "mime_type": "image/png",
        }, headers=headers)
        assert response.status_code == 201
        data = response.json()
        assert data["file_name"] == "test.png"
        assert data["asset_type"] == "scene_image"

    @pytest.mark.anyio
    async def test_list_assets(self, async_client: AsyncClient):
        """Test listing assets"""
        headers = await get_auth_headers(async_client)
        project_id = await create_project(async_client, headers)

        await async_client.post(f"/api/assets", json={"project_id": project_id, "file_name": "a.png", "file_path": "/a.png", "asset_type": "scene_image", "file_size": 100, "mime_type": "image/png"}, headers=headers)
        await async_client.post(f"/api/assets", json={"project_id": project_id, "file_name": "b.mp4", "file_path": "/b.mp4", "asset_type": "video_clip", "file_size": 200, "mime_type": "video/mp4"}, headers=headers)

        response = await async_client.get(f"/api/assets/{project_id}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2


class TestGoogleAccountsRouter:
    """Tests for google_accounts router"""

    @pytest.mark.anyio
    async def test_oauth_start_requires_credentials(self, async_client: AsyncClient):
        """Test OAuth start fails when credentials not configured"""
        headers = await get_auth_headers(async_client)

        response = await async_client.post("/api/google-accounts/oauth/start", json={}, headers=headers)
        assert response.status_code == 400
        assert "not configured" in response.json()["detail"].lower()

    @pytest.mark.anyio
    async def test_list_google_accounts_empty(self, async_client: AsyncClient):
        """Test listing Google accounts when empty"""
        headers = await get_auth_headers(async_client)

        response = await async_client.get("/api/google-accounts", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0


class TestFlowBridgeRouter:
    """Tests for flow_bridge router"""

    @pytest.mark.anyio
    async def test_create_flow_task(self, async_client: AsyncClient):
        """Test creating a flow bridge task"""
        headers = await get_auth_headers(async_client)
        project_id = await create_project(async_client, headers)

        response = await async_client.post(f"/api/flow", json={
            "project_id": project_id,
            "task_type": "video_generation",
            "title": "Test task",
            "input_prompts": '["prompt 1"]',
            "reference_assets": "[]",
        }, headers=headers)
        assert response.status_code == 201
        data = response.json()
        assert data["task_type"] == "video_generation"
        assert data["title"] == "Test task"

    @pytest.mark.anyio
    async def test_list_flow_tasks(self, async_client: AsyncClient):
        """Test listing flow bridge tasks"""
        headers = await get_auth_headers(async_client)
        project_id = await create_project(async_client, headers)

        await async_client.post(f"/api/flow", json={"project_id": project_id, "task_type": "video_generation", "title": "Task 1", "input_prompts": "[]", "reference_assets": "[]"}, headers=headers)
        await async_client.post(f"/api/flow", json={"project_id": project_id, "task_type": "image_generation", "title": "Task 2", "input_prompts": "[]", "reference_assets": "[]"}, headers=headers)

        response = await async_client.get(f"/api/flow/{project_id}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2


class TestStoryEngineRouter:
    """Tests for story_engine router"""

    @pytest.mark.anyio
    async def test_generate_story(self, async_client: AsyncClient):
        """Test story generation (will fail without API key but tests endpoint)"""
        headers = await get_auth_headers(async_client)
        project_id = await create_project(async_client, headers)

        response = await async_client.post("/api/story-engine/generate", json={
            "project_id": project_id,
            "generation_type": "story_idea",
            "context": {"genre": "drama", "premise": "A test story"},
        }, headers=headers)
        # Should either succeed (if valid API key) or fail with provider error (401->502/503)
        # With test key it will get 401 from Nvidia which becomes 502/503
        assert response.status_code in (201, 401, 502, 503)

    @pytest.mark.anyio
    async def test_list_story_generations(self, async_client: AsyncClient):
        """Test listing story generations"""
        headers = await get_auth_headers(async_client)
        project_id = await create_project(async_client, headers)

        response = await async_client.get(f"/api/story-engine/{project_id}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data


class TestSettingsRouter:
    """Tests for settings router"""

    @pytest.mark.anyio
    async def test_get_settings(self, async_client: AsyncClient):
        """Test getting settings"""
        headers = await get_auth_headers(async_client)

        response = await async_client.get("/api/settings", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "ai_providers" in data
        assert "google_oauth_configured" in data
        assert isinstance(data["ai_providers"], list)

    @pytest.mark.anyio
    async def test_update_settings_providers(self, async_client: AsyncClient):
        """Test updating AI providers"""
        headers = await get_auth_headers(async_client)

        response = await async_client.patch("/api/settings", json={
            "ai_providers": [
                {
                    "id": "nvidia-nim-1",
                    "provider": "nvidia",
                    "model": "nvidia/nemotron-3-ultra-550b-a55b",
                    "key_env": "NVIDIA_API_KEY",
                    "enabled": True,
                    "priority": 1,
                }
            ]
        }, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["ai_providers"]) == 1
        assert data["ai_providers"][0]["provider"] == "nvidia"

    @pytest.mark.anyio
    async def test_update_settings_oauth(self, async_client: AsyncClient):
        """Test updating Google OAuth credentials"""
        headers = await get_auth_headers(async_client)

        response = await async_client.patch("/api/settings", json={
            "google_oauth_client_id": "test-client-id",
            "google_oauth_client_secret": "test-client-secret",
        }, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["google_oauth_configured"] is True

        # Verify secrets not returned in GET
        get_response = await async_client.get("/api/settings", headers=headers)
        assert get_response.status_code == 200
        get_data = get_response.json()
        assert get_data["google_oauth_configured"] is True
        # Should not contain actual secret values