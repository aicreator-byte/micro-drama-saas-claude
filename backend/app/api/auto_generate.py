"""Auto-generate API router (Fase 1, backend only; future-dev: async).

One job, 5 sequential steps: series_bible -> characters -> locations ->
episodes -> prompts. Each step writes its rows directly (no manual Apply).
A failed step stops the pipeline; retry re-runs from the failed step only.
Re-running a job skips rows that already exist (idempotent).

Jobs run ASYNC (future-dev 3a): POST creates the job and returns
immediately with status "running"; the 5 steps run in a background task
and each step's status is persisted, so the client polls
GET /projects/{id}/auto-generate/{job_id} for live per-step progress.
The modal polls every 2s while the job is running.

Multi-worker safety (future-dev round 2): a job is CLAIMED with one
atomic UPDATE before it runs (see claim_job) — the claim is exclusive
per project, so the same job can never run twice (double retry, a
restart sweep racing a live worker) and two jobs for one project can
never run at the same time. The claim is a lease (LEASE_SECONDS) that
the runner renews before every step; a worker that dies stops
renewing, so after the lease expires another worker may take over.
The startup sweep only fails RUNNING jobs whose lease has expired.
SQLite is single-writer, so the lease (600s) must exceed the longest
single step (one LLM call, ~1-2 min in practice) — renewal happens
between steps, never mid-step. Audit ronde 2 fix: the lock is also
claimed inside the create request itself, so two simultaneous creates
cannot both return 201 — the atomic claim arbitrates and the loser
gets 409 with its row deleted (see create_auto_generate_job).

LLM goes through the leg's existing AI client (Nvidia NIM via env key,
never stored in DB). No video is generated here: step 5 only writes
VIDEO_GENERATION prompt rows; the actual video is still made manually in
Google Flow (spec section 8).
"""
import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import aliased

logger = logging.getLogger(__name__)

# Worker identity: one id per process (uvicorn worker). Used as the
# lock owner in claim_job so a lock can be released only by its owner.
WORKER_ID = uuid.uuid4().hex
# Lease length (s). Must exceed the longest single step; renewed before
# every step (see _run_from). A dead worker's lease lapses at most this
# long after it dies before another worker may take over.
LEASE_SECONDS = 600

from app.api.auth import get_current_user_id
from app.api.projects import _verify_project_access
from app.core.database import get_db
from app.models.auto_generate import (
    STEP_ORDER,
    AutoGenerateJob,
    AutoGenerateJobStatus,
    AutoGenerateStep,
    AutoGenerateStepName,
    AutoGenerateStepStatus,
)
from app.models.character import Character
from app.models.episode import Episode, EpisodeStatus
from app.models.location import Location
from app.models.project import Project
from app.models.prompt import Prompt, PromptType
from app.models.series_bible import SeriesBible
from app.schemas.auto_generate import (
    AutoGenerateCreate,
    AutoGenerateJobRead,
    AutoGenerateStepRead,
)
from app.services.ai_client import AIClientError, get_ai_client

router = APIRouter(prefix="/projects", tags=["auto-generate"])

SYSTEM_PROMPT = (
    "You are a professional screenwriter and story developer for vertical "
    "micro-dramas. Always return valid JSON only, no markdown, no commentary."
)
LANGUAGE_NOTE = (
    "Write all content in the same language as the title/premise "
    "(e.g. an English title means English content)."
)
# Genres the LLM may infer from a title (spec section 3). Anything else
# the LLM returns is treated as "no inference" — never silently defaulted.
GENRE_OPTIONS = (
    "drama", "romance", "thriller", "comedy", "horror",
    "sci-fi", "fantasy", "action", "mystery",
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(value: datetime | None) -> datetime | None:
    """SQLite returns stored datetimes naive; treat them as UTC so
    comparisons with _now() never raise TypeError."""
    if value is None:
        return None
    if value.tzinfo is not None:
        return value
    return value.replace(tzinfo=timezone.utc)


def _genre_label(job: AutoGenerateJob) -> str:
    """Genre for LLM prompts. Honest when unknown: never silently 'drama'."""
    genre = (job.genre or "").strip()
    if genre:
        return genre
    return "not specified — choose the genre that best fits the title"


def _parse_json(text: str) -> dict:
    """Parse LLM output as JSON, tolerating ```json fences."""
    cleaned = (text or "").strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`").strip()
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(f"LLM returned invalid JSON: {exc} (first 200 chars: {cleaned[:200]!r})")
    if not isinstance(parsed, dict):
        raise ValueError(f"LLM returned JSON but not an object: {cleaned[:200]!r}")
    return parsed


async def _llm_json(db: AsyncSession, user_prompt: str, max_tokens: int = 4000) -> dict:
    """One LLM call returning a parsed JSON object.

    Separated so tests can monkeypatch this instead of the real provider.
    """
    ai_client = await get_ai_client(db)
    try:
        response = await ai_client.generate(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            max_tokens=max_tokens,
        )
    except AIClientError as exc:
        raise RuntimeError(f"LLM call failed: {exc}") from exc
    return _parse_json(response.content)


async def _infer_genre(db: AsyncSession, job: AutoGenerateJob) -> str | None:
    """Infer the genre from the title via one LLM call (spec section 3).

    Returns None when the LLM cannot classify or the call fails — the
    caller then uses the honest 'not specified' label instead of
    silently defaulting to 'drama'.
    """
    options = ", ".join(GENRE_OPTIONS)
    user_prompt = (
        "Classify the genre of this micro-drama series from its title "
        "and premise.\n"
        f"Title: {job.title}\nPremise: {job.premise or job.title}\n\n"
        "Return JSON with exactly one key:\n"
        f"- genre (string, one of: {options})\n\n"
        "Pick the single best fit. If none fits clearly, return "
        '{"genre": null}.'
    )
    try:
        data = await _llm_json(db, user_prompt)
    except Exception:
        return None
    genre = data.get("genre")
    if not isinstance(genre, str):
        return None
    genre = genre.strip().lower()
    return genre if genre in GENRE_OPTIONS else None


# ---------------------------------------------------------------- steps

async def _step_series_bible(db: AsyncSession, job: AutoGenerateJob, project: Project) -> dict:
    existing = await db.scalar(
        select(SeriesBible).where(SeriesBible.project_id == project.id)
    )
    if existing is not None:
        return {"skipped": True, "reason": "series bible already exists"}

    if not (job.genre or "").strip():
        inferred = await _infer_genre(db, job)
        if inferred:
            job.genre = inferred

    user_prompt = (
        f"Create a series bible for a micro-drama series.\n"
        f"Title: {job.title}\nGenre: {_genre_label(job)}\n"
        f"Premise: {job.premise or job.title}\n"
        f"Total episodes: {job.total_episodes}\n{LANGUAGE_NOTE}\n\n"
        "Return JSON with exactly these keys:\n"
        "- premise (string), main_plot (string)\n"
        "- subplots (array of 3-5 strings)\n"
        "- character_relationships (string), world_settings (string)\n"
        "- tone_and_style (string), visual_style (string), ending_direction (string)\n"
        "- episode_structure (string, short summary of the episode arc)\n"
        f"- episodes (array of exactly {job.total_episodes} objects, each with "
        "number (1-based int), title, synopsis (one sentence))"
    )
    data = await _llm_json(db, user_prompt)
    episodes = data.get("episodes") or []
    if not isinstance(episodes, list) or not episodes:
        raise ValueError("LLM bible output has no episodes list")

    bible = SeriesBible(
        project_id=project.id,
        premise=data.get("premise"),
        main_plot=data.get("main_plot"),
        subplots=json.dumps(data.get("subplots") or []),
        character_relationships=data.get("character_relationships"),
        world_settings=data.get("world_settings"),
        tone_and_style=data.get("tone_and_style"),
        visual_style=data.get("visual_style"),
        ending_direction=data.get("ending_direction"),
        episode_structure=data.get("episode_structure"),
    )
    db.add(bible)
    return {"episodes_planned": len(episodes), "episodes": episodes}


async def _step_characters(db: AsyncSession, job: AutoGenerateJob, project: Project) -> dict:
    existing = await db.scalars(
        select(Character).where(Character.project_id == project.id)
    )
    existing_names = {c.name.strip().lower() for c in existing.all()}
    if len(existing_names) >= 4:
        return {"created": 0, "skipped": len(existing_names), "reason": "enough characters already exist"}

    bible = await db.scalar(select(SeriesBible).where(SeriesBible.project_id == project.id))
    context = ""
    if bible is not None:
        context = f"Premise: {bible.premise or ''}\nMain plot: {bible.main_plot or ''}\n"

    user_prompt = (
        f"Create the main cast for the micro-drama series \"{job.title}\".\n"
        f"Genre: {_genre_label(job)}\n{context}{LANGUAGE_NOTE}\n\n"
        "Return JSON with exactly one key:\n"
        "- characters (array of exactly 5 objects, each with: name, role "
        "(one of: protagonist, antagonist, supporting), physical_appearance, "
        "personality, background, costume)"
    )
    data = await _llm_json(db, user_prompt)
    characters = data.get("characters") or []
    if not isinstance(characters, list) or len(characters) < 4:
        raise ValueError(
            f"LLM returned only {len(characters) if isinstance(characters, list) else 0} "
            "characters, need at least 4"
        )

    created, skipped = 0, 0
    order = len(existing_names)
    for item in characters[:6]:
        name = (item.get("name") or "").strip()
        if not name:
            skipped += 1
            continue
        if name.lower() in existing_names:
            skipped += 1
            continue
        db.add(Character(
            project_id=project.id,
            name=name[:255],
            role=(item.get("role") or "supporting")[:100],
            physical_appearance=item.get("physical_appearance"),
            personality=item.get("personality"),
            background=item.get("background"),
            costume=item.get("costume"),
            display_order=order,
        ))
        existing_names.add(name.lower())
        order += 1
        created += 1
    return {"created": created, "skipped": skipped}


async def _step_locations(db: AsyncSession, job: AutoGenerateJob, project: Project) -> dict:
    existing = await db.scalars(
        select(Location).where(Location.project_id == project.id)
    )
    existing_names = {loc.name.strip().lower() for loc in existing.all()}
    if len(existing_names) >= 3:
        return {"created": 0, "skipped": len(existing_names), "reason": "enough locations already exist"}

    bible = await db.scalar(select(SeriesBible).where(SeriesBible.project_id == project.id))
    context = ""
    if bible is not None:
        context = f"World settings: {bible.world_settings or ''}\n"

    user_prompt = (
        f"Create the shooting locations for the micro-drama series \"{job.title}\".\n"
        f"Genre: {_genre_label(job)}\n{context}{LANGUAGE_NOTE}\n\n"
        "Return JSON with exactly one key:\n"
        "- locations (array of exactly 4 objects, each with: name, description, "
        "environment, lighting, atmosphere)"
    )
    data = await _llm_json(db, user_prompt)
    locations = data.get("locations") or []
    if not isinstance(locations, list) or len(locations) < 3:
        raise ValueError(
            f"LLM returned only {len(locations) if isinstance(locations, list) else 0} "
            "locations, need at least 3"
        )

    created, skipped = 0, 0
    order = len(existing_names)
    for item in locations[:5]:
        name = (item.get("name") or "").strip()
        if not name:
            skipped += 1
            continue
        if name.lower() in existing_names:
            skipped += 1
            continue
        db.add(Location(
            project_id=project.id,
            name=name[:255],
            description=item.get("description"),
            environment=item.get("environment"),
            lighting=item.get("lighting"),
            atmosphere=item.get("atmosphere"),
            display_order=order,
        ))
        existing_names.add(name.lower())
        order += 1
        created += 1
    return {"created": created, "skipped": skipped}


def _plan_covers(plan: list | None, total_episodes: int) -> bool:
    """True when the plan lists every episode number 1..total_episodes."""
    numbers = set()
    for item in plan or []:
        if not isinstance(item, dict):
            continue
        try:
            numbers.add(int(item.get("number")))
        except (TypeError, ValueError):
            continue
    return set(range(1, total_episodes + 1)).issubset(numbers)


def _plan_from_summary(summary: str | None) -> list:
    """Episode list saved in a bible step's result_summary, or []."""
    if not summary:
        return []
    try:
        saved = json.loads(summary)
    except (ValueError, AttributeError):
        return []
    episodes = saved.get("episodes") if isinstance(saved, dict) else None
    return episodes if isinstance(episodes, list) else []


async def _episode_plan(db: AsyncSession, job: AutoGenerateJob, project: Project) -> list:
    """Episode list, reusing prior work before spending an LLM call.

    Order (future-dev 2e — a re-run must not waste an LLM call):
    1. this job's bible-step summary,
    2. the latest earlier job's bible-step summary for the same project,
    3. episodes already stored in the DB (covers 1..N),
    4. one LLM call ("Plan the episodes").

    A saved plan that does not cover all 1..total_episodes is ignored and
    falls through to the next source.
    """
    step = await db.scalar(
        select(AutoGenerateStep).where(
            AutoGenerateStep.job_id == job.id,
            AutoGenerateStep.step == AutoGenerateStepName.SERIES_BIBLE,
        )
    )
    plan = _plan_from_summary(step.result_summary if step else None)
    if _plan_covers(plan, job.total_episodes):
        return plan

    prior = await db.scalar(
        select(AutoGenerateStep)
        .join(AutoGenerateJob, AutoGenerateStep.job_id == AutoGenerateJob.id)
        .where(
            AutoGenerateJob.project_id == project.id,
            AutoGenerateJob.id != job.id,
            AutoGenerateStep.step == AutoGenerateStepName.SERIES_BIBLE,
            AutoGenerateStep.status == AutoGenerateStepStatus.COMPLETED,
        )
        .order_by(AutoGenerateStep.completed_at.desc())
    )
    plan = _plan_from_summary(prior.result_summary if prior else None)
    if _plan_covers(plan, job.total_episodes):
        return plan

    existing = await db.scalars(
        select(Episode)
        .where(Episode.project_id == project.id)
        .order_by(Episode.episode_number)
    )
    rows = existing.all()
    numbers = {ep.episode_number for ep in rows}
    if set(range(1, job.total_episodes + 1)).issubset(numbers):
        return [
            {
                "number": ep.episode_number,
                "title": ep.title or f"Episode {ep.episode_number}",
                "synopsis": ep.synopsis or "",
            }
            for ep in rows
            if ep.episode_number <= job.total_episodes
        ]

    bible = await db.scalar(select(SeriesBible).where(SeriesBible.project_id == project.id))
    context = ""
    if bible is not None:
        context = f"Premise: {bible.premise or ''}\nMain plot: {bible.main_plot or ''}\n"
    user_prompt = (
        f"Plan the episodes for the micro-drama series \"{job.title}\".\n"
        f"Genre: {_genre_label(job)}\n{context}{LANGUAGE_NOTE}\n\n"
        "Return JSON with exactly one key:\n"
        f"- episodes (array of exactly {job.total_episodes} objects, each with "
        "number (1-based int), title, synopsis (one sentence))"
    )
    data = await _llm_json(db, user_prompt)
    episodes = data.get("episodes") or []
    if not isinstance(episodes, list) or not episodes:
        raise ValueError("LLM episode plan is empty")
    return episodes


async def _step_episodes(db: AsyncSession, job: AutoGenerateJob, project: Project) -> dict:
    existing = await db.scalars(
        select(Episode.episode_number).where(Episode.project_id == project.id)
    )
    existing_numbers = set(existing.all())
    episodes = await _episode_plan(db, job, project)

    # Future-dev 2a: the total episode count IS enforced — a plan that
    # does not cover every number 1..total_episodes fails the step
    # (retryable) instead of silently completing with fewer episodes.
    covered = {
        int(item.get("number")) for item in episodes
        if isinstance(item, dict) and str(item.get("number")).isdigit()
    }
    missing_numbers = sorted(set(range(1, job.total_episodes + 1)) - covered)
    if missing_numbers:
        raise ValueError(
            f"Episode plan covers only {len(covered)} of {job.total_episodes} "
            f"episodes; missing episode number(s): {missing_numbers}"
        )

    created, skipped = 0, 0
    for item in episodes:
        try:
            number = int(item.get("number"))
        except (TypeError, ValueError):
            skipped += 1
            continue
        if number in existing_numbers:
            skipped += 1
            continue
        db.add(Episode(
            project_id=project.id,
            episode_number=number,
            title=(item.get("title") or f"Episode {number}")[:255],
            synopsis=item.get("synopsis"),
            status=EpisodeStatus.PLANNED,
        ))
        existing_numbers.add(number)
        created += 1
    if created == 0 and not existing_numbers:
        raise ValueError("No episodes could be created from the episode plan")
    return {"created": created, "skipped": skipped}


async def _prompts_for_batch(
    db: AsyncSession, job: AutoGenerateJob, batch: list[Episode]
) -> dict[int, str]:
    """One LLM call for a batch of episodes + ONE retry for the episodes
    the LLM skipped. Raises ValueError if any episode is still missing a
    prompt after the retry (future-dev P1: no silent partial coverage)."""
    def listing(eps: list[Episode]) -> str:
        return "\n".join(
            f"- Episode {ep.episode_number}: {ep.title or ''} — {ep.synopsis or ''}"
            for ep in eps
        )

    async def call(eps: list[Episode]) -> dict[int, str]:
        user_prompt = (
            f"Write one vertical-video generation prompt per episode for the "
            f"micro-drama series \"{job.title}\" (genre: {_genre_label(job)}). "
            f"Each prompt must describe the key scene cinematically for a 9:16 "
            f"phone video (setting, characters, action, mood, camera).\n"
            f"{LANGUAGE_NOTE}\n\nEpisodes:\n{listing(eps)}\n\n"
            "Return JSON with exactly one key:\n"
            "- prompts (array of objects, each with: episode_number (int), "
            "prompt_text (string, 2-4 sentences))"
        )
        data = await _llm_json(db, user_prompt)
        prompts = data.get("prompts") or []
        if not isinstance(prompts, list):
            raise ValueError("LLM returned prompts in an unexpected format")
        out: dict[int, str] = {}
        for item in prompts:
            if not isinstance(item, dict):
                continue
            try:
                number = int(item.get("episode_number"))
            except (TypeError, ValueError):
                continue
            text = (item.get("prompt_text") or "").strip()
            if text:
                out[number] = text
        return out

    by_number = await call(batch)
    missing = [ep for ep in batch if ep.episode_number not in by_number]
    if missing:
        retry = await call(missing)
        by_number.update(retry)
    still_missing = sorted(
        ep.episode_number for ep in batch if ep.episode_number not in by_number
    )
    if still_missing:
        raise ValueError(
            "LLM did not return prompts for episode(s): "
            f"{still_missing} (after one retry)"
        )
    return by_number


async def _step_prompts(db: AsyncSession, job: AutoGenerateJob, project: Project) -> dict:
    episodes = await db.scalars(
        select(Episode).where(Episode.project_id == project.id).order_by(Episode.episode_number)
    )
    episodes = episodes.all()
    if not episodes:
        raise ValueError("No episodes exist, cannot generate prompts")

    have_prompt = await db.scalars(
        select(Prompt.episode_id).where(
            Prompt.project_id == project.id,
            Prompt.prompt_type == PromptType.VIDEO_GENERATION,
        )
    )
    have_prompt_ids = set(have_prompt.all())

    todo = [ep for ep in episodes if ep.id not in have_prompt_ids]
    if not todo:
        return {"created": 0, "skipped": len(episodes), "reason": "all episodes already have prompts"}

    created = 0
    for i in range(0, len(todo), 10):
        batch = todo[i:i + 10]
        by_number = await _prompts_for_batch(db, job, batch)
        for ep in batch:
            db.add(Prompt(
                project_id=project.id,
                episode_id=ep.id,
                prompt_type=PromptType.VIDEO_GENERATION,
                prompt_text=by_number[ep.episode_number],
                status="completed",
            ))
            created += 1

    # Final coverage check: every episode must have a prompt when the
    # step reports COMPLETED (rows added earlier in this step are
    # already in the session, so they count here).
    have_now = await db.scalars(
        select(Prompt.episode_id).where(
            Prompt.project_id == project.id,
            Prompt.prompt_type == PromptType.VIDEO_GENERATION,
        )
    )
    have_now_ids = set(have_now.all())
    missing_ids = [ep.episode_number for ep in episodes if ep.id not in have_now_ids]
    if missing_ids:
        raise ValueError(
            f"Prompt coverage incomplete: episode(s) {missing_ids} have no prompt"
        )
    return {"created": created, "skipped": len(episodes) - len(todo)}


STEP_RUNNERS = {
    AutoGenerateStepName.SERIES_BIBLE: _step_series_bible,
    AutoGenerateStepName.CHARACTERS: _step_characters,
    AutoGenerateStepName.LOCATIONS: _step_locations,
    AutoGenerateStepName.EPISODES: _step_episodes,
    AutoGenerateStepName.PROMPTS: _step_prompts,
}


# ---------------------------------------------------------------- job locking
# (future-dev round 2 — multi-worker safe execution)

async def claim_job(
    db: AsyncSession,
    job_id: uuid.UUID,
    project_id: uuid.UUID,
    worker_id: str,
    lease_seconds: int = LEASE_SECONDS,
) -> bool:
    """Atomically claim a RUNNING job for `worker_id`.

    One UPDATE wins the lock: the job must be RUNNING with an expired
    (or never-set) lease, AND no other job for the same project may
    hold a live lock. Losers get rowcount 0 and must not run the job.
    One exception: a lock placed by the create endpoint
    (owner "create:<job_id>") may be taken over by the background
    runner of that same job — the create claim only reserves the slot
    until the runner starts. Re-claiming by the SAME worker id is NOT
    allowed: a duplicate runner task in the same process must be
    blocked, or one job would execute twice.
    """
    now = _now()
    other = aliased(AutoGenerateJob)
    conflict = (
        select(1)
        .where(
            other.project_id == project_id,
            other.id != job_id,
            other.locked_by.is_not(None),
            other.lease_expires_at > now,
        )
        .exists()
    )
    result = await db.execute(
        update(AutoGenerateJob)
        .where(
            AutoGenerateJob.id == job_id,
            AutoGenerateJob.status == AutoGenerateJobStatus.RUNNING,
            or_(
                AutoGenerateJob.lease_expires_at.is_(None),
                AutoGenerateJob.lease_expires_at < now,
                # Takeover of the create-time placeholder lock (see
                # create_auto_generate_job): the runner of THIS job may
                # take over the lock the create request placed. Any
                # other live lock — including one held by the same
                # worker id — blocks the claim (duplicate runner guard).
                AutoGenerateJob.locked_by == f"create:{job_id}",
            ),
            ~conflict,
        )
        .values(
            locked_by=worker_id,
            locked_at=now,
            lease_expires_at=now + timedelta(seconds=lease_seconds),
        )
    )
    await db.commit()
    return result.rowcount == 1


async def renew_lease(
    db: AsyncSession,
    job_id: uuid.UUID,
    worker_id: str,
    lease_seconds: int = LEASE_SECONDS,
) -> bool:
    """Extend our own lease. Only the lock owner may renew."""
    result = await db.execute(
        update(AutoGenerateJob)
        .where(
            AutoGenerateJob.id == job_id,
            AutoGenerateJob.locked_by == worker_id,
        )
        .values(lease_expires_at=_now() + timedelta(seconds=lease_seconds))
    )
    await db.commit()
    return result.rowcount == 1


async def release_job(db: AsyncSession, job_id: uuid.UUID, worker_id: str) -> None:
    """Drop our lock (job finished/failed). Only the owner may release."""
    await db.execute(
        update(AutoGenerateJob)
        .where(
            AutoGenerateJob.id == job_id,
            AutoGenerateJob.locked_by == worker_id,
        )
        .values(locked_by=None, locked_at=None, lease_expires_at=None)
    )
    await db.commit()


# ---------------------------------------------------------------- runner

async def _load_steps(db: AsyncSession, job_id: uuid.UUID) -> list[AutoGenerateStep]:
    result = await db.scalars(
        select(AutoGenerateStep)
        .where(AutoGenerateStep.job_id == job_id)
        .order_by(AutoGenerateStep.position)
    )
    return list(result.all())


async def _run_from(
    db: AsyncSession,
    job: AutoGenerateJob,
    project: Project,
    start_position: int,
    worker_id: str | None = None,
) -> None:
    """Run pending steps from start_position; stops at the first failure.

    When `worker_id` is given, the job lease is renewed before every
    step (the runner owns the lock for the whole run).
    """
    steps = await _load_steps(db, job.id)
    for step in steps:
        if step.position < start_position:
            continue
        if step.status == AutoGenerateStepStatus.COMPLETED:
            continue
        if worker_id is not None:
            await renew_lease(db, job.id, worker_id)
        step.status = AutoGenerateStepStatus.RUNNING
        step.error_message = None
        await db.commit()
        try:
            summary = await STEP_RUNNERS[step.step](db, job, project)
            step.status = AutoGenerateStepStatus.COMPLETED
            step.result_summary = json.dumps(summary)
            step.completed_at = _now()
        except Exception as exc:  # noqa: BLE001 - any step error fails the step
            step.status = AutoGenerateStepStatus.FAILED
            step.error_message = str(exc)[:1000]
            step.completed_at = _now()
            job.status = AutoGenerateJobStatus.FAILED
            job.error_message = f"Step {step.step.value} failed: {exc}"
            await db.commit()
            return
        await db.commit()
    job.status = AutoGenerateJobStatus.COMPLETED
    job.error_message = None
    job.completed_at = _now()
    await db.commit()


async def _run_job_in_background(
    job_id: uuid.UUID,
    project_id: uuid.UUID,
    start_position: int,
    sessionmaker: async_sessionmaker,
) -> None:
    """Background task for a job (future-dev 3a, round 2 locking).

    Own session: the request session is closed once the response is sent,
    so the job cannot reuse it. The sessionmaker is built from the
    request session's engine, so tests (which override get_db with an
    in-memory engine) run the background job against the same test DB.

    The job is claimed first: if another worker already owns it (live
    lease) this call returns without doing anything — that is what makes
    double execution impossible.
    """
    async with sessionmaker() as bg_db:
        claimed = await claim_job(bg_db, job_id, project_id, WORKER_ID)
        if not claimed:
            # Two cases, and they need different handling:
            # (a) THIS job already holds a live lock — another runner
            #     (a duplicate task / retry race) owns it. Do nothing;
            #     that runner will finish it.
            # (b) ANOTHER job for the project holds the lock — this job
            #     can never run while that lock is live. Fail it with a
            #     clear message instead of leaving it stuck RUNNING.
            job = await bg_db.scalar(
                select(AutoGenerateJob).where(AutoGenerateJob.id == job_id)
            )
            if job is not None and job.status == AutoGenerateJobStatus.RUNNING:
                lease = _aware(job.lease_expires_at)
                if job.locked_by is not None and lease is not None and lease > _now():
                    logger.info(
                        "auto-generate job %s already owned by another worker; skipping",
                        job_id,
                    )
                    return
                job.status = AutoGenerateJobStatus.FAILED
                job.error_message = (
                    "Another auto-generate job is already running for this "
                    "project — retry after it finishes"
                )
                job.completed_at = _now()
                await bg_db.commit()
            # A job that is no longer RUNNING (already completed/failed
            # by the owning runner) needs nothing: never clobber a
            # terminal state.
            return
        job = await bg_db.scalar(
            select(AutoGenerateJob).where(AutoGenerateJob.id == job_id)
        )
        if job is None:
            return
        project = await bg_db.scalar(
            select(Project).where(Project.id == project_id)
        )
        if project is None:
            return
        try:
            await _run_from(bg_db, job, project, start_position, WORKER_ID)
        except Exception as exc:  # noqa: BLE001 - never leave a job stuck
            await bg_db.rollback()
            job = await bg_db.scalar(
                select(AutoGenerateJob).where(AutoGenerateJob.id == job_id)
            )
            if job is not None:
                job.status = AutoGenerateJobStatus.FAILED
                job.error_message = f"Job runner failed: {exc}"
                job.completed_at = _now()
                await bg_db.commit()
        finally:
            async with sessionmaker() as rel_db:
                await release_job(rel_db, job_id, WORKER_ID)


async def _mark_interrupted_jobs_failed() -> None:
    """Startup sweep: jobs left RUNNING by a server restart are failed.

    Called once from the app lifespan. Only jobs whose lease has
    expired (or was never claimed) are failed — a job with a LIVE
    lease is being run by another worker right now, and failing it
    would be wrong. Multi-worker safe: every worker runs this sweep,
    but the lease condition makes it idempotent. Their FAILED steps
    can be retried normally.
    """
    from app.core.database import async_session_maker

    now = _now()
    async with async_session_maker() as db:
        jobs = list((await db.scalars(
            select(AutoGenerateJob).where(
                AutoGenerateJob.status == AutoGenerateJobStatus.RUNNING,
                or_(
                    AutoGenerateJob.lease_expires_at.is_(None),
                    AutoGenerateJob.lease_expires_at < now,
                ),
            )
        )).all())
        for job in jobs:
            job.status = AutoGenerateJobStatus.FAILED
            job.error_message = (
                "Interrupted by server restart — retry the failed step"
            )
            job.completed_at = _now()
            job.locked_by = None
            job.locked_at = None
            job.lease_expires_at = None
            steps = list((await db.scalars(
                select(AutoGenerateStep).where(
                    AutoGenerateStep.job_id == job.id,
                    AutoGenerateStep.status == AutoGenerateStepStatus.RUNNING,
                )
            )).all())
            for step in steps:
                step.status = AutoGenerateStepStatus.FAILED
                step.error_message = "Interrupted by server restart"
                step.completed_at = _now()
        if jobs:
            await db.commit()


def _to_read(job: AutoGenerateJob, steps: list[AutoGenerateStep]) -> AutoGenerateJobRead:
    return AutoGenerateJobRead(
        id=job.id,
        project_id=job.project_id,
        title=job.title,
        genre=job.genre,
        total_episodes=job.total_episodes,
        premise=job.premise,
        status=job.status,
        error_message=job.error_message,
        steps=[
            AutoGenerateStepRead(
                step=s.step,
                status=s.status,
                error_message=s.error_message,
                result_summary=s.result_summary,
                completed_at=s.completed_at,
            )
            for s in steps
        ],
        created_at=job.created_at,
        completed_at=job.completed_at,
    )


async def _get_job_or_404(
    db: AsyncSession, project_id: str, job_id: str
) -> AutoGenerateJob:
    job = await db.scalar(
        select(AutoGenerateJob).where(
            AutoGenerateJob.id == uuid.UUID(job_id),
            AutoGenerateJob.project_id == uuid.UUID(project_id),
        )
    )
    if job is None:
        raise HTTPException(status_code=404, detail="Auto-generate job not found")
    return job


def _background_sessionmaker(db: AsyncSession) -> async_sessionmaker:
    """Session factory bound to the same engine as the request session."""
    return async_sessionmaker(
        bind=db.bind, class_=AsyncSession, expire_on_commit=False
    )


# ---------------------------------------------------------------- endpoints

@router.post(
    "/{project_id}/auto-generate",
    response_model=AutoGenerateJobRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_auto_generate_job(
    project_id: str,
    body: AutoGenerateCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Create an auto-generate job and run it in the background.

    The title in the body is the series title (the project title is left
    untouched). Returns immediately with status "running"; poll
    GET /projects/{id}/auto-generate/{job_id} for live per-step progress.

    Simultaneous-create race: the pre-check above is advisory only —
    two requests arriving in the same instant can both pass it. The
    atomic UPDATE inside claim_job is the real arbiter, so the lock is
    claimed HERE, in the request, before returning 201. A loser gets
    409 and its just-inserted row is deleted, so a duplicate RUNNING
    job is never visible and no FAILED litter is left behind. The only
    remaining window is between the two requests' pre-check SELECTs —
    both rows are briefly inserted, but only one can ever hold the
    lock or run, and the loser is removed before the response.
    """
    project = await _verify_project_access(project_id, user_id, db)

    # One active job per project (round 2): a second job may not start
    # while another job for this project holds a live lock. A stale
    # RUNNING job (lease expired — its worker died) does not block.
    live_other = await db.scalar(
        select(AutoGenerateJob).where(
            AutoGenerateJob.project_id == project.id,
            AutoGenerateJob.status == AutoGenerateJobStatus.RUNNING,
            AutoGenerateJob.lease_expires_at > _now(),
        )
    )
    if live_other is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Another auto-generate job is already running for this project",
        )

    job = AutoGenerateJob(
        project_id=project.id,
        title=body.title,
        genre=body.genre,
        total_episodes=body.total_episodes,
        premise=body.premise,
        status=AutoGenerateJobStatus.RUNNING,
    )
    db.add(job)
    await db.flush()
    for position, step_name in enumerate(STEP_ORDER):
        db.add(AutoGenerateStep(
            job_id=job.id,
            position=position,
            step=step_name,
            status=AutoGenerateStepStatus.PENDING,
        ))
    await db.commit()
    await db.refresh(job)

    # Claim the lock now: the loser of a simultaneous create is
    # rejected here with 409 instead of returning 201 and failing
    # later in the background runner. The lock is placed under the
    # placeholder owner "create:<job_id>" (NOT this worker's id), so
    # the background runner can take it over via claim_job while a
    # duplicate runner task is still blocked.
    claimed = await claim_job(db, job.id, project.id, f"create:{job.id}")
    if not claimed:
        await db.delete(job)  # steps cascade (delete-orphan)
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Another auto-generate job is already running for this project",
        )

    asyncio.create_task(_run_job_in_background(
        job.id, project.id, 0, _background_sessionmaker(db),
    ))
    return _to_read(job, await _load_steps(db, job.id))


@router.get("/{project_id}/auto-generate/{job_id}", response_model=AutoGenerateJobRead)
async def get_auto_generate_job(
    project_id: str,
    job_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get an auto-generate job with per-step status (poll this)."""
    await _verify_project_access(project_id, user_id, db)
    job = await _get_job_or_404(db, project_id, job_id)
    return _to_read(job, await _load_steps(db, job.id))


@router.post(
    "/{project_id}/auto-generate/{job_id}/retry/{step}",
    response_model=AutoGenerateJobRead,
)
async def retry_auto_generate_step(
    project_id: str,
    job_id: str,
    step: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Retry one failed step in the background, then continue with the
    following steps. Returns immediately with status "running"; poll GET
    for progress.

    Only a FAILED step can be retried, and only when every earlier step
    is COMPLETED. Completed steps are never re-run.
    """
    project = await _verify_project_access(project_id, user_id, db)
    job = await _get_job_or_404(db, project_id, job_id)

    try:
        step_name = AutoGenerateStepName(step)
    except ValueError:
        raise HTTPException(
            status_code=400, detail=f"Unknown step: {step}"
        ) from None

    steps = await _load_steps(db, job.id)
    target = next((s for s in steps if s.step == step_name), None)
    if target is None:
        raise HTTPException(status_code=404, detail="Step not found in this job")
    if target.status != AutoGenerateStepStatus.FAILED:
        raise HTTPException(
            status_code=400,
            detail=f"Only a failed step can be retried (step is {target.status.value})",
        )
    earlier = [s for s in steps if s.position < target.position]
    if any(s.status != AutoGenerateStepStatus.COMPLETED for s in earlier):
        raise HTTPException(
            status_code=400,
            detail="An earlier step has not completed yet; retry that step first",
        )

    job.status = AutoGenerateJobStatus.RUNNING
    job.error_message = None
    job.completed_at = None
    await db.commit()

    asyncio.create_task(_run_job_in_background(
        job.id, project.id, target.position, _background_sessionmaker(db),
    ))
    await db.refresh(job)
    return _to_read(job, await _load_steps(db, job.id))
