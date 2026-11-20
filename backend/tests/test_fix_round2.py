"""Tests for audit ronde 2 fixes (FIX-REPORT ronde 2):
- add-character-to-scene no longer 500s (MissingGreenlet, F-H1)
- POST /prompts/generate works for all 10 PromptTypes (KeyError 'name')
- Flow import no longer 500s (double-UUID, flow_bridge.py:208)
- Malformed UUID -> 400, not 500 (F-H3)
- OAuth callback: bad state -> 400, transport error -> 502 (F-H2)
- PATCH scene validates location_id (F-M10)
- Refresh token sent as JSON object -> 200 (frontend 422 fix, backend side)
- Shot CRUD router (P1-18)
"""
import pytest
import httpx
from httpx import AsyncClient

from test_new_routers import (
    TEST_PASSWORD,
    get_auth_headers,
    create_project,
    create_character,
    create_location,
    create_episode,
    create_scene,
)


class TestAddCharacterToScene:
    @pytest.mark.anyio
    async def test_add_character_to_scene(self, async_client: AsyncClient):
        """F-H1: POST /scenes/{ep}/.../characters must be 201, not 500"""
        headers = await get_auth_headers(async_client)
        project_id = await create_project(async_client, headers)
        char_id = await create_character(async_client, headers, project_id, "Nadia")
        episode_id = await create_episode(async_client, headers, project_id)
        scene_id = await create_scene(async_client, headers, episode_id)

        response = await async_client.post(
            f"/api/scenes/{episode_id}/{scene_id}/characters",
            json={"character_id": char_id, "role_in_scene": "lead"},
            headers=headers,
        )
        # NOTE: the route has no status_code=201, so a successful add is 200
        assert response.status_code == 200, response.text
        body = response.json()
        assert len(body["characters"]) == 1
        assert body["characters"][0]["character_id"] == char_id

        # Adding the same character twice -> 400, not 500
        dup = await async_client.post(
            f"/api/scenes/{episode_id}/{scene_id}/characters",
            json={"character_id": char_id},
            headers=headers,
        )
        assert dup.status_code == 400

    @pytest.mark.anyio
    async def test_add_character_other_project(self, async_client: AsyncClient):
        """Character from another project -> 400"""
        headers = await get_auth_headers(async_client)
        project_id = await create_project(async_client, headers)
        other_id = await create_project(async_client, headers, "Other Project")
        char_id = await create_character(async_client, headers, other_id, "Stranger")
        episode_id = await create_episode(async_client, headers, project_id)
        scene_id = await create_scene(async_client, headers, episode_id)

        response = await async_client.post(
            f"/api/scenes/{episode_id}/{scene_id}/characters",
            json={"character_id": char_id},
            headers=headers,
        )
        assert response.status_code == 400


class TestPromptGenerate:
    @pytest.mark.anyio
    async def test_generate_all_prompt_types(self, async_client: AsyncClient):
        """KeyError 'name': every PromptType must generate without 500"""
        headers = await get_auth_headers(async_client)
        project_id = await create_project(async_client, headers)
        char_id = await create_character(async_client, headers, project_id, "Nadia")
        loc_id = await create_location(async_client, headers, project_id, "Jakarta Loft")

        for prompt_type in [
            "character_image", "location_image", "scene_image",
            "video_generation", "camera_movement", "character_action",
            "dialogue_audio", "background_music", "sound_effect", "subtitle",
        ]:
            response = await async_client.post(
                "/api/prompts/generate",
                json={
                    "project_id": project_id,
                    "prompt_type": prompt_type,
                    "context": "a rainy night confrontation",
                    "character_id": char_id,
                    "location_id": loc_id,
                },
                headers=headers,
            )
            assert response.status_code == 200, f"{prompt_type}: {response.text}"
            body = response.json()
            # Honest label: template output is status "template", never "completed"
            assert body["status"] == "template", f"{prompt_type}: {body}"
            assert body["prompt_text"]

    @pytest.mark.anyio
    async def test_generate_character_image_uses_character_name(self, async_client: AsyncClient):
        headers = await get_auth_headers(async_client)
        project_id = await create_project(async_client, headers)
        char_id = await create_character(async_client, headers, project_id, "Nadia")

        response = await async_client.post(
            "/api/prompts/generate",
            json={
                "project_id": project_id,
                "prompt_type": "character_image",
                "context": "standing in the rain",
                "character_id": char_id,
            },
            headers=headers,
        )
        assert response.status_code == 200
        assert "Nadia" in response.json()["prompt_text"]


class TestFlowImport:
    @pytest.mark.anyio
    async def test_import_from_flow(self, async_client: AsyncClient):
        """Double-UUID: import must be 200, not 500"""
        headers = await get_auth_headers(async_client)
        project_id = await create_project(async_client, headers)
        create = await async_client.post(
            "/api/flow",
            json={"project_id": project_id, "task_type": "image_generation", "title": "T1",
                  "input_prompts": "[]", "reference_assets": "[]"},
            headers=headers,
        )
        assert create.status_code == 201, create.text
        task_id = create.json()["id"]

        response = await async_client.post(
            "/api/flow/import",
            json={"flow_task_id": task_id,
                  "output_assets": [{"file_path": "/tmp/out.png", "asset_type": "image"}],
                  "notes": "generated in Flow"},
            headers=headers,
        )
        assert response.status_code == 200, response.text
        assert response.json()["status"] == "imported"

    @pytest.mark.anyio
    async def test_import_unknown_task_404(self, async_client: AsyncClient):
        import uuid
        headers = await get_auth_headers(async_client)
        response = await async_client.post(
            "/api/flow/import",
            json={"flow_task_id": str(uuid.uuid4()), "output_assets": []},
            headers=headers,
        )
        assert response.status_code == 404


class TestMalformedUuid:
    @pytest.mark.anyio
    async def test_malformed_uuid_returns_400(self, async_client: AsyncClient):
        """F-H3: malformed UUID in path -> 400, not 500"""
        headers = await get_auth_headers(async_client)
        for url in [
            "/api/projects/not-a-uuid",
            "/api/prompts/not-a-uuid",
            "/api/characters/not-a-uuid",
            "/api/episodes/not-a-uuid",
            "/api/scenes/not-a-uuid",
            "/api/google-accounts/not-a-uuid",
            "/api/flow/not-a-uuid",
        ]:
            response = await async_client.get(url, headers=headers)
            assert response.status_code == 400, f"{url}: {response.status_code} {response.text}"

    @pytest.mark.anyio
    async def test_malformed_uuid_scene_character(self, async_client: AsyncClient):
        headers = await get_auth_headers(async_client)
        response = await async_client.post(
            "/api/scenes/not-a-uuid/also-not-a-uuid/characters",
            json={"character_id": str(__import__("uuid").uuid4())},
            headers=headers,
        )
        assert response.status_code == 400


class TestOAuthCallback:
    @pytest.mark.anyio
    async def test_callback_bad_state_400(self, async_client: AsyncClient):
        """F-H2/F-H5: unknown state -> 400 (never 500)"""
        headers = await get_auth_headers(async_client)
        response = await async_client.post(
            "/api/google-accounts/oauth/callback",
            json={"code": "fake-code", "state": "not-a-real-state"},
            headers=headers,
        )
        assert response.status_code == 400

    @pytest.mark.anyio
    async def test_callback_transport_error_502(self, async_client: AsyncClient, monkeypatch):
        """F-H2: Google unreachable -> 502, not 500.

        Seeds a valid DB-backed state + OAuth credentials in settings,
        then makes httpx raise ConnectError.
        """
        from app.core.database import get_db
        from app.models.settings import AppSettings
        from app.models.oauth_state import OAuthState
        from datetime import datetime, timezone, timedelta
        import uuid as uuid_mod

        headers = await get_auth_headers(async_client)
        # Configure OAuth credentials via Settings API
        settings_resp = await async_client.patch(
            "/api/settings",
            json={"google_oauth_client_id": "test-client-id",
                  "google_oauth_client_secret": "test-secret"},
            headers=headers,
        )
        assert settings_resp.status_code == 200, settings_resp.text

        # Seed a valid state directly in the test DB
        session_gen = override_db_session(async_client)
        async with session_gen as session:
            me = await async_client.get("/api/auth/me", headers=headers)
            user_id = uuid_mod.UUID(me.json()["id"])
            now = datetime.now(timezone.utc)
            session.add(OAuthState(
                state="valid-state-for-test",
                user_id=user_id,
                redirect_uri="http://localhost:8000/api/google-accounts/oauth/callback",
                created_at=now,
                expires_at=now + timedelta(minutes=10),
            ))
            await session.commit()

        class ExplodingClient(httpx.AsyncClient):
            async def post(self, *args, **kwargs):
                raise httpx.ConnectError("boom", request=httpx.Request("POST", "https://example.com"))

        monkeypatch.setattr(httpx, "AsyncClient", ExplodingClient)

        response = await async_client.post(
            "/api/google-accounts/oauth/callback",
            json={"code": "fake-code", "state": "valid-state-for-test"},
            headers=headers,
        )
        assert response.status_code == 502, response.text


def override_db_session(async_client):
    """Get a raw session on the test engine (same DB the app uses in tests)."""
    from conftest import TestAsyncSessionMaker
    return TestAsyncSessionMaker()


class TestScenePatchLocation:
    @pytest.mark.anyio
    async def test_patch_scene_invalid_location_400(self, async_client: AsyncClient):
        """F-M10: PATCH scene with a location from another project -> 400"""
        headers = await get_auth_headers(async_client)
        project_id = await create_project(async_client, headers)
        other_id = await create_project(async_client, headers, "Other Project")
        loc_id = await create_location(async_client, headers, other_id, "Elsewhere")
        episode_id = await create_episode(async_client, headers, project_id)
        scene_id = await create_scene(async_client, headers, episode_id)

        response = await async_client.patch(
            f"/api/scenes/{episode_id}/{scene_id}",
            json={"location_id": loc_id},
            headers=headers,
        )
        assert response.status_code == 400, response.text


class TestRefreshTokenObject:
    @pytest.mark.anyio
    async def test_refresh_with_object_body(self, async_client: AsyncClient):
        """Frontend fix (P0-18): /auth/refresh expects {"refresh_token": ...}"""
        await async_client.post("/api/auth/register", json={
            "email": "refresh@example.com", "username": "refreshuser",
            "password": TEST_PASSWORD,
        })
        login = await async_client.post("/api/auth/login", json={
            "email": "refresh@example.com", "password": TEST_PASSWORD,
        })
        refresh_token = login.json()["refresh_token"]

        response = await async_client.post(
            "/api/auth/refresh", json={"refresh_token": refresh_token}
        )
        assert response.status_code == 200, response.text
        assert response.json()["access_token"]


class TestShotCrud:
    @pytest.mark.anyio
    async def test_shot_crud(self, async_client: AsyncClient):
        """P1-18: Shot router CRUD"""
        headers = await get_auth_headers(async_client)
        project_id = await create_project(async_client, headers)
        episode_id = await create_episode(async_client, headers, project_id)
        scene_id = await create_scene(async_client, headers, episode_id)

        create = await async_client.post(
            f"/api/shots/{scene_id}",
            json={"shot_number": 1, "description": "Wide shot of the loft",
                  "camera_angle": "wide", "duration_seconds": 4},
            headers=headers,
        )
        assert create.status_code == 201, create.text
        shot_id = create.json()["id"]

        listing = await async_client.get(f"/api/shots/{scene_id}", headers=headers)
        assert listing.status_code == 200
        assert len(listing.json()) == 1

        patch = await async_client.patch(
            f"/api/shots/{scene_id}/{shot_id}",
            json={"camera_movement": "slow pan"},
            headers=headers,
        )
        assert patch.status_code == 200
        assert patch.json()["camera_movement"] == "slow pan"

        delete = await async_client.delete(f"/api/shots/{scene_id}/{shot_id}", headers=headers)
        assert delete.status_code == 204

        gone = await async_client.get(f"/api/shots/{scene_id}/{shot_id}", headers=headers)
        assert gone.status_code == 404

    @pytest.mark.anyio
    async def test_shot_other_user_404(self, async_client: AsyncClient):
        """Tenant isolation on shots"""
        headers = await get_auth_headers(async_client)
        project_id = await create_project(async_client, headers)
        episode_id = await create_episode(async_client, headers, project_id)
        scene_id = await create_scene(async_client, headers, episode_id)

        other = await get_auth_headers(async_client, "other@example.com", "otheruser")
        response = await async_client.get(f"/api/shots/{scene_id}", headers=other)
        assert response.status_code == 404


class TestCleanupUndecryptableCredentials:
    """Audit ronde 2 fix: rows encrypted under the old (truncated-key)
    derivation must be cleared, not left to 500 every caller."""

    @pytest.mark.anyio
    async def test_clears_bad_ciphertext_keeps_good(self, async_client: AsyncClient):
        from sqlalchemy import select

        from app.core.security import decrypt_data, encrypt_data
        from app.models import User
        from app.models.google_account import GoogleAccount
        from app.services.google_account_service import (
            cleanup_undecryptable_credentials,
        )
        from conftest import TestAsyncSessionMaker

        headers = await get_auth_headers(async_client, "clean@example.com", "cleanuser")
        async with TestAsyncSessionMaker() as db:
            user = await db.scalar(select(User).where(User.email == "clean@example.com"))
            bad = GoogleAccount(
                user_id=user.id, email="bad@example.com", account_index=0,
                password_encrypted="gAAAAABq_lOJR0XVbwYl-broken-ciphertext",
            )
            good = GoogleAccount(
                user_id=user.id, email="good@example.com", account_index=1,
                password_encrypted=encrypt_data("real-password"),
                access_token_encrypted=encrypt_data("real-token"),
            )
            db.add_all([bad, good])
            await db.commit()

            cleared = await cleanup_undecryptable_credentials(db)
            assert cleared == {"password": 1, "access_token": 0, "refresh_token": 0}

            bad_after = await db.scalar(select(GoogleAccount).where(GoogleAccount.id == bad.id))
            assert bad_after.password_encrypted is None
            good_after = await db.scalar(select(GoogleAccount).where(GoogleAccount.id == good.id))
            assert decrypt_data(good_after.password_encrypted) == "real-password"
            assert decrypt_data(good_after.access_token_encrypted) == "real-token"

    @pytest.mark.anyio
    async def test_cleanup_noop_when_nothing_broken(self, async_client: AsyncClient):
        from app.services.google_account_service import (
            cleanup_undecryptable_credentials,
        )
        from conftest import TestAsyncSessionMaker

        async with TestAsyncSessionMaker() as db:
            assert await cleanup_undecryptable_credentials(db) == {
                "password": 0, "access_token": 0, "refresh_token": 0,
            }
