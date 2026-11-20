"""Multi-worker safe job execution tests (future-dev round 2, item 4).

Covers: atomic claim (exclusive per job AND per project), lease
renew/release, takeover after lease expiry, double-runner execution
(only one runner may run a job), concurrent retry (one run), create
409 while another job runs, the loser job failing cleanly instead of
staying stuck RUNNING, and the startup sweep leaving live-lease jobs
alone while failing stale ones.
"""
import asyncio
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import select

import app.api.auto_generate as auto_generate_mod
from app.models.auto_generate import (
    STEP_ORDER,
    AutoGenerateJob,
    AutoGenerateJobStatus,
    AutoGenerateStep,
    AutoGenerateStepName,
    AutoGenerateStepStatus,
)
from conftest import TestAsyncSessionMaker
from test_auto_generate import (
    _fake_llm_ok,
    _poll_job,
    _post_job,
    get_auth_headers,
    make_project,
)

TEST_PASSWORD = "TestPass123!"


def _now():
    return datetime.now(timezone.utc)


async def _insert_job(session, project_id, status=AutoGenerateJobStatus.RUNNING,
                      locked_by=None, lease_expires_at=None):
    job = AutoGenerateJob(
        project_id=project_id,
        title="LOCK TEST",
        genre="drama",
        total_episodes=3,
        status=status,
        locked_by=locked_by,
        locked_at=_now() if locked_by else None,
        lease_expires_at=lease_expires_at,
    )
    session.add(job)
    await session.flush()
    for position, step_name in enumerate(STEP_ORDER):
        session.add(AutoGenerateStep(
            job_id=job.id,
            position=position,
            step=step_name,
            status=AutoGenerateStepStatus.PENDING,
        ))
    await session.commit()
    return job.id


async def _read_job(job_id):
    async with TestAsyncSessionMaker() as session:
        return await session.scalar(
            select(AutoGenerateJob).where(AutoGenerateJob.id == job_id)
        )


# ---------------------------------------------------------------- claim unit

@pytest.mark.anyio
async def test_claim_release_renew_unit(async_client: AsyncClient):
    headers = await get_auth_headers(async_client, "lock1@example.com", "lock1")
    project_id = await make_project(async_client, headers)
    pid = uuid.UUID(project_id)

    async with TestAsyncSessionMaker() as db:
        job_id = await _insert_job(db, pid)
        # First claim wins.
        assert await auto_generate_mod.claim_job(db, job_id, pid, "w1") is True
        # Second worker cannot claim the same job while the lease is live.
        assert await auto_generate_mod.claim_job(db, job_id, pid, "w2") is False
        # Only the owner may renew; a stranger cannot.
        assert await auto_generate_mod.renew_lease(db, job_id, "w2") is False
        assert await auto_generate_mod.renew_lease(db, job_id, "w1") is True
        # Only the owner may release; a stranger's release is a no-op.
        await auto_generate_mod.release_job(db, job_id, "w2")
        job = await db.scalar(select(AutoGenerateJob).where(AutoGenerateJob.id == job_id))
        assert job.locked_by == "w1"
        await auto_generate_mod.release_job(db, job_id, "w1")
        job = await db.scalar(select(AutoGenerateJob).where(AutoGenerateJob.id == job_id))
        assert job.locked_by is None
        assert job.lease_expires_at is None
        # After release, another worker may claim.
        assert await auto_generate_mod.claim_job(db, job_id, pid, "w2") is True


@pytest.mark.anyio
async def test_claim_takeover_after_lease_expiry(async_client: AsyncClient):
    headers = await get_auth_headers(async_client, "lock2@example.com", "lock2")
    project_id = await make_project(async_client, headers)
    pid = uuid.UUID(project_id)

    async with TestAsyncSessionMaker() as db:
        job_id = await _insert_job(db, pid)
        # w1 claims with an already-expired lease (dead worker).
        assert await auto_generate_mod.claim_job(db, job_id, pid, "w1", lease_seconds=0) is True
        # w2 may take over immediately: the lease is already past.
        assert await auto_generate_mod.claim_job(db, job_id, pid, "w2") is True


@pytest.mark.anyio
async def test_claim_is_exclusive_per_project(async_client: AsyncClient):
    headers = await get_auth_headers(async_client, "lock3@example.com", "lock3")
    project_id = await make_project(async_client, headers)
    pid = uuid.UUID(project_id)

    async with TestAsyncSessionMaker() as db:
        job1 = await _insert_job(db, pid)
        job2 = await _insert_job(db, pid)
        assert await auto_generate_mod.claim_job(db, job1, pid, "w1") is True
        # A different job for the SAME project cannot claim while w1's
        # job holds a live lock.
        assert await auto_generate_mod.claim_job(db, job2, pid, "w2") is False
        await auto_generate_mod.release_job(db, job1, "w1")
        assert await auto_generate_mod.claim_job(db, job2, pid, "w2") is True


# ---------------------------------------------------------------- double execution

@pytest.mark.anyio
async def test_double_runner_executes_once(async_client: AsyncClient, monkeypatch):
    """POST a job, then race a second _run_job_in_background for the
    same job: exactly one run happens (4 LLM calls, not 8)."""
    calls = {"n": 0}

    async def slow_fake(db, user_prompt: str, max_tokens: int = 4000):
        calls["n"] += 1
        await asyncio.sleep(0.3)
        return await _fake_llm_ok(db, user_prompt, max_tokens)

    monkeypatch.setattr(auto_generate_mod, "_llm_json", slow_fake)
    headers = await get_auth_headers(async_client, "lock4@example.com", "lock4")
    project_id = await make_project(async_client, headers)

    res = await _post_job(async_client, project_id, headers)
    assert res.status_code == 201
    job_id = res.json()["id"]

    # Second runner for the SAME job, while the first is still running.
    await auto_generate_mod._run_job_in_background(
        uuid.UUID(job_id), uuid.UUID(project_id), 0, TestAsyncSessionMaker
    )
    job = await _poll_job(async_client, project_id, job_id, headers, timeout=20.0)
    assert job["status"] == "completed"
    assert calls["n"] == 4  # bible + characters + locations + prompts, once
    eps = await async_client.get(f"/api/episodes/{project_id}", headers=headers)
    assert eps.json()["total"] == 3
    chars = await async_client.get(f"/api/characters/{project_id}", headers=headers)
    assert len(chars.json()) == 5


@pytest.mark.anyio
async def test_concurrent_retry_runs_once(async_client: AsyncClient, monkeypatch):
    """Two simultaneous retries of the same failed step: one run."""
    calls = {"n": 0}
    state = {"failed_once": False}

    async def fail_once_then_ok(db, user_prompt: str, max_tokens: int = 4000):
        calls["n"] += 1
        await asyncio.sleep(0.2)
        if "main cast" in user_prompt and not state["failed_once"]:
            state["failed_once"] = True
            raise RuntimeError("simulated LLM outage")
        return await _fake_llm_ok(db, user_prompt, max_tokens)

    monkeypatch.setattr(auto_generate_mod, "_llm_json", fail_once_then_ok)
    headers = await get_auth_headers(async_client, "lock5@example.com", "lock5")
    project_id = await make_project(async_client, headers)

    res = await _post_job(async_client, project_id, headers)
    job_id = res.json()["id"]
    job = await _poll_job(async_client, project_id, job_id, headers)
    assert job["status"] == "failed"
    assert calls["n"] == 2  # bible ok, characters failed

    r1, r2 = await asyncio.gather(
        async_client.post(
            f"/api/projects/{project_id}/auto-generate/{job_id}/retry/characters",
            headers=headers,
        ),
        async_client.post(
            f"/api/projects/{project_id}/auto-generate/{job_id}/retry/characters",
            headers=headers,
        ),
    )
    assert r1.status_code == 200
    assert r2.status_code == 200
    job = await _poll_job(async_client, project_id, job_id, headers, timeout=20.0)
    assert job["status"] == "completed"
    # Retry run = characters + locations + prompts, exactly once.
    assert calls["n"] == 2 + 3
    chars = await async_client.get(f"/api/characters/{project_id}", headers=headers)
    assert len(chars.json()) == 5  # no duplicates from the double retry


@pytest.mark.anyio
async def test_create_second_job_while_running_409(async_client: AsyncClient, monkeypatch):
    async def slow_fake(db, user_prompt: str, max_tokens: int = 4000):
        await asyncio.sleep(0.3)
        return await _fake_llm_ok(db, user_prompt, max_tokens)

    monkeypatch.setattr(auto_generate_mod, "_llm_json", slow_fake)
    headers = await get_auth_headers(async_client, "lock6@example.com", "lock6")
    project_id = await make_project(async_client, headers)

    first = await _post_job(async_client, project_id, headers)
    assert first.status_code == 201
    # Let the background task claim the job (claim happens at task start).
    await asyncio.sleep(0.5)
    second = await _post_job(async_client, project_id, headers)
    assert second.status_code == 409
    assert "already running" in second.json()["detail"]

    job = await _poll_job(async_client, project_id, first.json()["id"], headers, timeout=20.0)
    assert job["status"] == "completed"
    # Once the first job is done, a new job may start.
    third = await _post_job(async_client, project_id, headers)
    assert third.status_code == 201
    job = await _poll_job(async_client, project_id, third.json()["id"], headers, timeout=20.0)
    assert job["status"] == "completed"


@pytest.mark.anyio
async def test_loser_job_fails_cleanly(async_client: AsyncClient, monkeypatch):
    """A job whose claim loses to another job for the same project is
    FAILED with a clear message — never stuck RUNNING."""
    monkeypatch.setattr(auto_generate_mod, "_llm_json", _fake_llm_ok)
    headers = await get_auth_headers(async_client, "lock7@example.com", "lock7")
    project_id = await make_project(async_client, headers)
    pid = uuid.UUID(project_id)

    async with TestAsyncSessionMaker() as db:
        winner = await _insert_job(db, pid)
        loser = await _insert_job(db, pid)
        assert await auto_generate_mod.claim_job(db, winner, pid, "w1") is True

    await auto_generate_mod._run_job_in_background(
        loser, pid, 0, TestAsyncSessionMaker
    )
    job = await _read_job(loser)
    assert job.status == AutoGenerateJobStatus.FAILED
    assert "already running" in (job.error_message or "")

    # The winner is untouched; once its lock is released it can run
    # to completion normally.
    async with TestAsyncSessionMaker() as db:
        await auto_generate_mod.release_job(db, winner, "w1")
    await auto_generate_mod._run_job_in_background(
        winner, pid, 0, TestAsyncSessionMaker
    )
    job = await _read_job(winner)
    assert job.status == AutoGenerateJobStatus.COMPLETED


# ---------------------------------------------------------------- startup sweep

@pytest.mark.anyio
async def test_sweep_fails_only_stale_jobs(async_client: AsyncClient, monkeypatch):
    headers = await get_auth_headers(async_client, "lock8@example.com", "lock8")
    project_id = await make_project(async_client, headers)
    pid = uuid.UUID(project_id)

    async with TestAsyncSessionMaker() as db:
        live = await _insert_job(
            db, pid, locked_by="w1", lease_expires_at=_now() + timedelta(seconds=600)
        )
        stale = await _insert_job(
            db, pid, locked_by="w1", lease_expires_at=_now() - timedelta(seconds=10)
        )
        unclaimed = await _insert_job(db, pid)
        for job_id in (live, stale, unclaimed):
            step = await db.scalar(select(AutoGenerateStep).where(
                AutoGenerateStep.job_id == job_id,
                AutoGenerateStep.step == AutoGenerateStepName.SERIES_BIBLE,
            ))
            step.status = AutoGenerateStepStatus.RUNNING
        await db.commit()

    import app.core.database as database_mod
    monkeypatch.setattr(database_mod, "async_session_maker", TestAsyncSessionMaker)
    await auto_generate_mod._mark_interrupted_jobs_failed()

    live_job = await _read_job(live)
    assert live_job.status == AutoGenerateJobStatus.RUNNING
    assert live_job.locked_by == "w1"  # untouched: another worker runs it
    stale_job = await _read_job(stale)
    assert stale_job.status == AutoGenerateJobStatus.FAILED
    assert stale_job.locked_by is None
    unclaimed_job = await _read_job(unclaimed)
    assert unclaimed_job.status == AutoGenerateJobStatus.FAILED


# ---------------------------------------------------------------- audit ronde 2 fix: claim at create

@pytest.mark.anyio
async def test_claim_create_lock_takeover(async_client: AsyncClient):
    """The create endpoint places a placeholder lock ("create:<job_id>");
    the job's own runner may take it over, but nobody else may — and
    the SAME worker id may NOT re-claim a live lock it already holds
    (that is the duplicate-runner guard: a second runner task in the
    same process must be blocked)."""
    headers = await get_auth_headers(async_client, "lock9@example.com", "lock9")
    project_id = await make_project(async_client, headers)
    pid = uuid.UUID(project_id)

    async with TestAsyncSessionMaker() as db:
        job_id = await _insert_job(db, pid)
        # Create-time placeholder lock, as create_auto_generate_job does.
        assert await auto_generate_mod.claim_job(db, job_id, pid, f"create:{job_id}") is True
        # The job's own runner takes the placeholder over.
        assert await auto_generate_mod.claim_job(db, job_id, pid, "w1") is True
        job = await _read_job(job_id)
        assert job.locked_by == "w1"
        # Same worker id re-claiming its own live lock: blocked.
        assert await auto_generate_mod.claim_job(db, job_id, pid, "w1") is False
        # A different worker: blocked as well.
        assert await auto_generate_mod.claim_job(db, job_id, pid, "w2") is False


@pytest.mark.anyio
async def test_simultaneous_create_one_wins(async_client: AsyncClient, monkeypatch):
    """Two creates fired at the same instant: exactly one 201 and one
    409, and only ONE job row exists afterwards (the loser is deleted,
    not left FAILED). The winner runs to completion normally."""
    monkeypatch.setattr(auto_generate_mod, "_llm_json", _fake_llm_ok)
    headers = await get_auth_headers(async_client, "lock10@example.com", "lock10")
    project_id = await make_project(async_client, headers)

    first, second = await asyncio.gather(
        _post_job(async_client, project_id, headers),
        _post_job(async_client, project_id, headers),
    )
    assert sorted([first.status_code, second.status_code]) == [201, 409]
    winner = first if first.status_code == 201 else second
    loser = second if first.status_code == 201 else first
    assert "already running" in loser.json()["detail"]

    async with TestAsyncSessionMaker() as db:
        jobs = (await db.scalars(
            select(AutoGenerateJob).where(
                AutoGenerateJob.project_id == uuid.UUID(project_id)
            )
        )).all()
    assert len(jobs) == 1
    assert str(jobs[0].id) == winner.json()["id"]

    job = await _poll_job(async_client, project_id, winner.json()["id"], headers, timeout=20.0)
    assert job["status"] == "completed"
