# Micro Drama SaaS — Claude Leg

A full-stack SaaS platform for creating vertical micro-drama series from a
single title to production-ready video prompts, using AI. This is the
**Claude leg** of a three-leg build challenge (Hermes, OpenCode, Claude) —
three independent implementations of the same spec, kept in separate repos.

## Highlights

- **Auto-Generate**: type a series title → AI fills in everything in 5
  steps — series bible, characters, locations, episodes, video prompts.
  Jobs run **async**: POST returns immediately, the frontend polls live
  per-step progress, and each step can be retried on its own. Re-running
  reuses completed work instead of spending more LLM calls.
- **Genre auto-detect**: leave genre empty and the AI infers it from the
  title in step 1 (romance, thriller, comedy, …). If it cannot classify,
  the genre stays unset — never silently defaulted to "drama".
- **Project Studio**: create and manage multiple drama projects.
- **Series Bible**: premise, plot, subplots, world, tone, visual style.
- **Character / Location Studio**: detailed profiles and shooting locations.
- **Story Engine**: AI-powered episode generation and breakdowns.
- **Prompt Studio**: structured prompts for image, video and audio.
- **Google Accounts + Flow Bridge**: connect up to 20 Google accounts per
  user; log in with a normal browser login (no Cloud Console); automatic
  fallback to the next account when one fails; export prompts for Google
  Flow and import the results. Video itself is still produced manually in
  Google Flow.
- **Dashboard stats**: real counts from the database (projects, characters,
  locations, episodes).

## Tech Stack

- **Frontend**: Next.js 15, React 19, TypeScript, Tailwind CSS, Zustand
- **Backend**: FastAPI 0.115, Python 3.12, SQLAlchemy 2.0, Alembic,
  Playwright (browser login)
- **Database**: SQLite by default, PostgreSQL via `DATABASE_URL`
- **Auth**: JWT tokens with bcrypt password hashing
- **AI**: Nvidia NIM (`nvidia/nemotron-3-ultra-550b-a55b`) via
  `NVIDIA_API_KEY` — no card needed for the free tier
- **Containerization**: Docker, Docker Compose (Postgres + Redis)

## Quick Start

### Prerequisites

- Docker and Docker Compose, **or** for local development:
- Node.js 20+ and Python 3.12+

### Using Docker Compose

```bash
cd micro-drama-saas-claude
cp backend/.env.example backend/.env
# Edit backend/.env — set SECRET_KEY, ENCRYPTION_KEY, NVIDIA_API_KEY
docker compose up -d
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API docs: http://localhost:8000/docs

### Local Development

#### Backend

```bash
cd backend

python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env — at minimum NVIDIA_API_KEY (auto-generate LLM),
# SECRET_KEY and ENCRYPTION_KEY

alembic upgrade head

# Start from ANY directory — the script cds into backend/ itself,
# so .env is always found:
./start.sh
# or: PORT=8003 ./start.sh
```

#### Frontend

```bash
cd frontend
npm install

# Point at the backend (default http://localhost:8000):
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
# or: npm run build && npm start   (production, port 3000)
```

## Project Structure

```
micro-drama-saas-claude/
├── backend/
│   ├── app/
│   │   ├── api/           # API routes (incl. auto_generate, dashboard)
│   │   ├── core/          # Config, security, database
│   │   ├── models/        # SQLAlchemy models
│   │   ├── schemas/       # Pydantic schemas
│   │   ├── services/      # AI client, browser login, account fallback
│   │   └── utils/         # Encryption helpers
│   ├── alembic/           # Database migrations
│   ├── tests/             # Pytest tests (113 tests)
│   ├── start.sh           # Start the backend from any directory
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── app/           # Next.js App Router pages
│   │   ├── components/    # React components (incl. auto-generate modal)
│   │   ├── lib/           # API client, stores
│   │   └── types/         # TypeScript types
│   └── package.json
├── docker-compose.yml
└── README.md
```

## Auto-Generate (how it works)

`POST /api/projects/{project_id}/auto-generate` with:

```json
{
  "title": "THE BILLIONAIRE CEO",
  "genre": null,
  "total_episodes": 5,
  "premise": "A struggling singer marries a cold CEO."
}
```

- `title` is required and may not be blank/whitespace-only (422).
- `genre` is optional — when omitted the AI infers it from the title.
- `total_episodes` is 1–100 (default 30).

The endpoint returns `201` immediately with the job in status `running`.
The 5 steps (series_bible → characters → locations → episodes →
prompts) run in a background task; each step's status and result summary
are stored in the database. Poll
`GET /api/projects/{project_id}/auto-generate/{job_id}` (the frontend
modal polls every 2 s) for live progress.

Rules the backend enforces:

- **Episode count**: the plan must cover every number 1..N, otherwise the
  episodes step fails (retryable) instead of completing short.
- **Prompt coverage**: every episode must end up with a video prompt. If
  the LLM skips an episode, the step retries just the missing ones once;
  if still missing, the step fails naming the episode.
- **Idempotent re-run**: a second job on the same project reuses the
  bible plan, stored episodes and existing prompts — zero extra LLM calls.
- **Retry**: `POST /api/projects/{id}/auto-generate/{job_id}/retry/{step}`
  re-runs one failed step (and the steps after it) in the background.
- **Restart safety**: jobs left `running` by a server restart are marked
  failed at startup so their steps can be retried. Single-worker
  assumption — do not run multiple uvicorn workers against one database.

## API Endpoints

All routes are under `/api` (no `/v1` prefix on this leg).

### Authentication

- `POST /api/auth/register` — Register a user
- `POST /api/auth/login` — Login (form data), returns JWT
- `GET /api/auth/me` — Current user

### Dashboard

- `GET /api/dashboard/stats` — Real counts: projects, characters,
  locations, episodes (current user)

### Projects

- `POST /api/projects` — Create project
- `GET /api/projects` — List projects (paginated)
- `GET /api/projects/{id}` — Get project
- `PATCH /api/projects/{id}` — Update project
- `DELETE /api/projects/{id}` — Delete project

### Auto-Generate

- `POST /api/projects/{id}/auto-generate` — Start a job (async, 201)
- `GET /api/projects/{id}/auto-generate/{job_id}` — Job + per-step status
- `POST /api/projects/{id}/auto-generate/{job_id}/retry/{step}` — Retry a
  failed step (async)

### Series Bible / Characters / Locations / Episodes / Scenes / Dialogues / Prompts / Shots

- `POST /api/series-bible/{project_id}` — Create series bible
- `GET /api/series-bible/{project_id}` — Get series bible
- `POST /api/characters/{project_id}` — Create character
- `GET /api/characters/{project_id}` — List characters
- `POST /api/locations/{project_id}` — Create location
- `GET /api/locations/{project_id}` — List locations
- `POST /api/episodes/{project_id}` — Create episode
- `GET /api/episodes/{project_id}` — List episodes (paginated)
- `POST /api/prompts/{project_id}` — Create prompt
- `GET /api/prompts/{project_id}` — List prompts
- Scenes, dialogues and shots follow the same per-project pattern.

### Google Accounts & Flow Bridge

- `POST /api/google-accounts` — Connect a Google account (max 20/user)
- `GET /api/google-accounts` — List accounts
- `PATCH /api/google-accounts/{id}` — Update account
- `DELETE /api/google-accounts/{id}` — Disconnect account
- `POST /api/google-accounts/{id}/password` — Store browser-login password
  (encrypted)
- `POST /api/flow/{project_id}/tasks` — Create a Flow task
- `GET /api/flow/{project_id}/tasks` — List Flow tasks
- `POST /api/flow/{project_id}/export-prompts` — Export prompts for Flow
- `POST /api/flow/{project_id}/import-results` — Import Flow results

### Other

- `GET /api/story-engine/{project_id}` — Story engine generations
- `GET /api/settings` — App settings
- `POST /api/assets/{project_id}/upload` — Upload an asset
- `GET /health` — Health check

## Google Login & Fallback (how it works)

Login uses a **normal browser login** (email + password, Playwright +
Chromium, persistent profile per account) — no Google Cloud Console.
Passwords are stored encrypted in the database; sessions are reused until
they expire. When an account fails (wrong password, challenge, session
expired, Flow blocked, quota), execution automatically falls back to the
next connected account of the same user, and every attempt is recorded in
the task's `fallback_history`.

## Testing

```bash
cd backend
source venv/bin/activate
# Run the suite by explicit file list — bare `pytest` currently crashes
# during collection (pytest-asyncio 0.23.3 tooling issue, pre-existing).
venv/bin/python -m pytest tests/test_auth.py tests/test_auto_generate.py \
  tests/test_browser_login.py tests/test_characters_locations.py \
  tests/test_config.py tests/test_dashboard_stats.py tests/test_fix_round2.py \
  tests/test_google_fallback.py tests/test_new_routers.py tests/test_projects.py -q
```

113 tests, all passing. Auto-generate tests use a fake LLM
(monkeypatched `_llm_json`), so no provider is called and no key is
needed. Frontend: `npx tsc --noEmit` (0 errors) and `npm run build`.

## Deployment

1. **Set `SECRET_KEY` and `ENCRYPTION_KEY`** — the shipped defaults are
   placeholders. Generate the encryption key with:
   `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
2. **Set `NVIDIA_API_KEY`** for auto-generate (free tier, no card).
3. **Use PostgreSQL** — set `DATABASE_URL` to
   `postgresql+asyncpg://…` (asyncpg is already a dependency).
4. **Set `DEBUG=false`** and restrict `CORS_ORIGINS` to your domain.
5. **Use HTTPS** behind a reverse proxy.
6. **Run a single uvicorn worker** — background auto-generate jobs and
   the restart sweep assume one worker per database.

## Known Limitations (honest)

- **Real Google login has never been verified live from this VM**: the
  browser path reaches Google's sign-in form via relay, but Google asks
  for extra verification (bot detection) and the VM's egress cannot
  complete a real login. Login with a real account, a real Flow prompt
  submission, and real Flow video remain unverified.
- **Video is manual**: auto-generate writes video prompts only. The video
  itself is made in Google Flow (manually or via the Flow Bridge's
  export/import).
- **30-episode jobs** have not been run live yet (smoke tests used 3–5
  episodes); prompts are generated in batches of 10 per LLM call.
- **Manual UI clicks** in a browser have not been verified (only API +
  build checks).
- **Security hardening is deferred** by design decision: placeholder
  secrets, no rate limiting, no token revocation. Do not expose the
  backend publicly without hardening it first.
- **Test quirk**: bare `pytest` crashes during collection
  (pytest-asyncio); run the suite via the explicit file list above.
- **Passlib/bcrypt warning**: `passlib` logs a trapped
  `AttributeError: module 'bcrypt' has no attribute '__about__'` on
  first use with bcrypt ≥ 4.1 — harmless (password hashing still works),
  fixed by pinning bcrypt < 4.1 if it bothers you.

## Future Improvements

- Verify a real Google login + Flow submission end-to-end from a machine
  that reaches Google, and a 30-episode live job.
- Manual browser click-through of the Auto-Generate modal and dashboard.
- Security hardening: strong secrets, rate limiting, token revocation,
  security headers.
- Multi-worker safe job execution (job locking / a task queue).

## License

Proprietary — All rights reserved.
