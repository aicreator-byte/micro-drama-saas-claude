"""Auto-generate (Fase 1) tests — job runs 5 steps in order.

The LLM seam is app.api.auto_generate._llm_json, monkeypatched here with
canned JSON so no real provider is called.
"""
import uuid

import pytest
from httpx import AsyncClient

import app.api.auto_generate as auto_generate_mod

TEST_PASSWORD = "TestPass123!"


async def get_auth_headers(async_client: AsyncClient, email: str = "autogen@example.com",
                           username: str = "autogenuser") -> dict:
    await async_client.post("/api/auth/register", json={
        "email": email,
        "username": username,
        "password": TEST_PASSWORD,
    })
    login_response = await async_client.post("/api/auth/login", json={
        "email": email,
        "password": TEST_PASSWORD,
    })
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def make_project(async_client: AsyncClient, headers: dict) -> str:
    response = await async_client.post("/api/projects", json={
        "title": "Test Project",
        "genre": "drama",
    }, headers=headers)
    assert response.status_code == 201
    return response.json()["id"]


def _bible_payload(n_episodes: int = 3) -> dict:
    return {
        "premise": "A struggling singer marries a cold CEO to save her family.",
        "main_plot": "Contract marriage turns into real love.",
        "subplots": ["Rival returns", "Corporate war", "Family secret"],
        "character_relationships": "Emma married to Alexander by contract.",
        "world_settings": "Modern New York, luxury penthouses.",
        "tone_and_style": "Cinematic, romantic, suspenseful.",
        "visual_style": "High-end Hollywood style.",
        "ending_direction": "Love wins after the truth comes out.",
        "episode_structure": "30 short episodes, 1-2 minutes each.",
        "episodes": [
            {"number": i + 1, "title": f"Episode {i + 1}",
             "synopsis": f"Something dramatic happens in episode {i + 1}."}
            for i in range(n_episodes)
        ],
    }


def _characters_payload() -> dict:
    return {"characters": [
        {"name": "Emma Carter", "role": "protagonist",
         "physical_appearance": "Young woman, brown hair",
         "personality": "Kind but strong-willed", "background": "Struggling singer",
         "costume": "Simple dresses"},
        {"name": "Alexander Blackwood", "role": "protagonist",
         "physical_appearance": "Tall, sharp suit",
         "personality": "Cold, ruthless in business", "background": "Billionaire CEO",
         "costume": "Tailored suits"},
        {"name": "Victoria", "role": "antagonist",
         "physical_appearance": "Elegant blonde",
         "personality": "Manipulative", "background": "Alexander's ex",
         "costume": "Designer gowns"},
        {"name": "Daniel", "role": "antagonist",
         "physical_appearance": "Slick businessman",
         "personality": "Ambitious, scheming", "background": "Rival executive",
         "costume": "Dark suits"},
        {"name": "Maya", "role": "supporting",
         "physical_appearance": "Cheerful young woman",
         "personality": "Loyal friend", "background": "Emma's best friend",
         "costume": "Casual chic"},
    ]}


def _locations_payload() -> dict:
    return {"locations": [
        {"name": "Blackwood Penthouse", "description": "Luxury penthouse",
         "environment": "Modern high-rise", "lighting": "Warm evening light",
         "atmosphere": "Opulent, tense"},
        {"name": "Emma's Apartment", "description": "Small cozy flat",
         "environment": "Old building", "lighting": "Soft daylight",
         "atmosphere": "Humble, warm"},
        {"name": "Blackwood Tower Office", "description": "Glass corporate office",
         "environment": "Skyscraper", "lighting": "Cold fluorescent",
         "atmosphere": "Powerful, intimidating"},
        {"name": "Rooftop Garden", "description": "Garden on a rooftop",
         "environment": "Outdoors at night", "lighting": "City lights",
         "atmosphere": "Romantic, quiet"},
    ]}


def _prompts_payload(n_episodes: int = 3) -> dict:
    return {"prompts": [
        {"episode_number": i + 1,
         "prompt_text": f"Cinematic vertical video, episode {i + 1}: a dramatic "
                        f"confrontation in a luxury penthouse, 9:16, moody lighting."}
        for i in range(n_episodes)
    ]}


async def _fake_llm_ok(db, user_prompt: str, max_tokens: int = 4000) -> dict:
    if "series bible" in user_prompt:
        return _bible_payload()
    if "main cast" in user_prompt:
        return _characters_payload()
    if "shooting locations" in user_prompt:
        return _locations_payload()
    if "Plan the episodes" in user_prompt:
        return {"episodes": _bible_payload()["episodes"]}
    if "video generation prompt" in user_prompt:
        return _prompts_payload()
    raise AssertionError(f"unexpected LLM prompt: {user_prompt[:120]!r}")


async def _fake_llm_fail_characters(db, user_prompt: str, max_tokens: int = 4000) -> dict:
    if "main cast" in user_prompt:
        raise RuntimeError("simulated LLM outage")
    return await _fake_llm_ok(db, user_prompt, max_tokens)


def _post_job(client, project_id, headers, total_episodes=3):
    return client.post(f"/api/projects/{project_id}/auto-generate", json={
        "title": "THE BILLIONAIRE CEO",
        "genre": "Romance",
        "total_episodes": total_episodes,
        "premise": "A struggling singer marries a cold CEO.",
    }, headers=headers)


@pytest.mark.anyio
async def test_auto_generate_full_run(async_client: AsyncClient, monkeypatch):
    """Happy path: one POST fills bible + characters + locations + episodes + prompts."""
    monkeypatch.setattr(auto_generate_mod, "_llm_json", _fake_llm_ok)
    headers = await get_auth_headers(async_client)
    project_id = await make_project(async_client, headers)

    response = await _post_job(async_client, project_id, headers)
    assert response.status_code == 201
    job = response.json()
    assert job["status"] == "completed"
    assert [s["step"] for s in job["steps"]] == [
        "series_bible", "characters", "locations", "episodes", "prompts",
    ]
    assert all(s["status"] == "completed" for s in job["steps"])

    bible = await async_client.get(f"/api/series-bible/{project_id}", headers=headers)
    assert bible.status_code == 200
    assert "struggling singer" in (bible.json()["premise"] or "")

    chars = await async_client.get(f"/api/characters/{project_id}", headers=headers)
    assert chars.status_code == 200
    assert len(chars.json()) == 5

    locs = await async_client.get(f"/api/locations/{project_id}", headers=headers)
    assert locs.status_code == 200
    assert len(locs.json()) == 4

    eps = await async_client.get(f"/api/episodes/{project_id}", headers=headers)
    assert eps.status_code == 200
    assert eps.json()["total"] == 3
    assert [e["episode_number"] for e in eps.json()["items"]] == [1, 2, 3]

    prompts = await async_client.get(f"/api/prompts/{project_id}", headers=headers)
    assert prompts.status_code == 200
    assert prompts.json()["total"] == 3
    assert all(p["prompt_type"] == "video_generation" for p in prompts.json()["items"])


@pytest.mark.anyio
async def test_step_failure_stops_pipeline(async_client: AsyncClient, monkeypatch):
    """Characters step fails -> job failed, later steps stay pending, nothing half-written."""
    monkeypatch.setattr(auto_generate_mod, "_llm_json", _fake_llm_fail_characters)
    headers = await get_auth_headers(async_client)
    project_id = await make_project(async_client, headers)

    response = await _post_job(async_client, project_id, headers)
    assert response.status_code == 201
    job = response.json()
    assert job["status"] == "failed"
    by_step = {s["step"]: s["status"] for s in job["steps"]}
    assert by_step == {
        "series_bible": "completed",
        "characters": "failed",
        "locations": "pending",
        "episodes": "pending",
        "prompts": "pending",
    }
    assert "simulated LLM outage" in (job["error_message"] or "")

    chars = await async_client.get(f"/api/characters/{project_id}", headers=headers)
    assert len(chars.json()) == 0


@pytest.mark.anyio
async def test_retry_failed_step(async_client: AsyncClient, monkeypatch):
    """Retry only the failed step; earlier results are kept, later steps continue."""
    monkeypatch.setattr(auto_generate_mod, "_llm_json", _fake_llm_fail_characters)
    headers = await get_auth_headers(async_client)
    project_id = await make_project(async_client, headers)

    response = await _post_job(async_client, project_id, headers)
    job = response.json()
    assert job["status"] == "failed"
    job_id = job["id"]

    monkeypatch.setattr(auto_generate_mod, "_llm_json", _fake_llm_ok)
    retry = await async_client.post(
        f"/api/projects/{project_id}/auto-generate/{job_id}/retry/characters",
        headers=headers,
    )
    assert retry.status_code == 200
    job = retry.json()
    assert job["status"] == "completed"
    assert all(s["status"] == "completed" for s in job["steps"])

    chars = await async_client.get(f"/api/characters/{project_id}", headers=headers)
    assert len(chars.json()) == 5

    # Retrying a completed step is rejected.
    again = await async_client.post(
        f"/api/projects/{project_id}/auto-generate/{job_id}/retry/characters",
        headers=headers,
    )
    assert again.status_code == 400


@pytest.mark.anyio
async def test_rerun_is_idempotent(async_client: AsyncClient, monkeypatch):
    """A second job on the same project must not duplicate rows."""
    monkeypatch.setattr(auto_generate_mod, "_llm_json", _fake_llm_ok)
    headers = await get_auth_headers(async_client)
    project_id = await make_project(async_client, headers)

    first = await _post_job(async_client, project_id, headers)
    assert first.json()["status"] == "completed"
    second = await _post_job(async_client, project_id, headers)
    assert second.status_code == 201
    assert second.json()["status"] == "completed"

    chars = await async_client.get(f"/api/characters/{project_id}", headers=headers)
    assert len(chars.json()) == 5
    locs = await async_client.get(f"/api/locations/{project_id}", headers=headers)
    assert len(locs.json()) == 4
    eps = await async_client.get(f"/api/episodes/{project_id}", headers=headers)
    assert eps.json()["total"] == 3
    prompts = await async_client.get(f"/api/prompts/{project_id}", headers=headers)
    assert prompts.json()["total"] == 3


@pytest.mark.anyio
async def test_get_job(async_client: AsyncClient, monkeypatch):
    """GET returns the job with steps in order."""
    monkeypatch.setattr(auto_generate_mod, "_llm_json", _fake_llm_ok)
    headers = await get_auth_headers(async_client)
    project_id = await make_project(async_client, headers)

    created = await _post_job(async_client, project_id, headers)
    job_id = created.json()["id"]

    got = await async_client.get(
        f"/api/projects/{project_id}/auto-generate/{job_id}", headers=headers
    )
    assert got.status_code == 200
    assert got.json()["id"] == job_id
    assert len(got.json()["steps"]) == 5


@pytest.mark.anyio
async def test_auto_generate_requires_auth(async_client: AsyncClient):
    """No token -> 401."""
    response = await async_client.post(
        f"/api/projects/{uuid.uuid4()}/auto-generate",
        json={"title": "X"},
    )
    assert response.status_code == 401


@pytest.mark.anyio
async def test_auto_generate_project_not_found(async_client: AsyncClient):
    """Unknown project -> 404."""
    headers = await get_auth_headers(async_client)
    response = await async_client.post(
        f"/api/projects/{uuid.uuid4()}/auto-generate",
        json={"title": "X"},
        headers=headers,
    )
    assert response.status_code == 404


@pytest.mark.anyio
async def test_retry_unknown_step(async_client: AsyncClient, monkeypatch):
    """Retry with an unknown step name -> 400."""
    monkeypatch.setattr(auto_generate_mod, "_llm_json", _fake_llm_fail_characters)
    headers = await get_auth_headers(async_client)
    project_id = await make_project(async_client, headers)

    created = await _post_job(async_client, project_id, headers)
    job_id = created.json()["id"]

    response = await async_client.post(
        f"/api/projects/{project_id}/auto-generate/{job_id}/retry/not_a_step",
        headers=headers,
    )
    assert response.status_code == 400
