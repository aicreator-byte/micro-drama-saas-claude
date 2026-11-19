# Future Development — Claude Leg — Report

Perintah Di 19 Nov 20:44: kerjakan semua future development kaki Claude +
buat README (repo Claude di GitHub tidak punya README). Tanggal pengerjaan:
19 Nov 2026 (malam). Semua kerja HANYA di
`~/workspace/micro-drama-saas/claude/`.

## Ringkasan

Semua item scope SELESAI dan terverifikasi (tes + smoke live). Tidak ada
item yang gagal.

| Item | Status | Bukti |
|---|---|---|
| 1. README.md | SELESAI | `claude/README.md` (12 KB) |
| 2. P1 prompts coverage penuh | SELESAI | tes baru, 113 passed |
| 2a. Jumlah episode ditegakkan (langkah 4/5) | SELESAI | tes baru, 113 passed |
| 2b. Judul hanya-spasi ditolak (backend+frontend) | SELESAI | tes baru, 113 passed |
| 2c. Genre "Auto (from title)" — inferensi LLM | SELESAI | tes baru + smoke live |
| 2d. Overlay tidak menutup modal saat running | SELESAI | tsc 0 + build OK |
| 2e. Re-run tanpa buang 1 call LLM | SELESAI | tes baru (run ke-2 = 0 call) |
| 2f. Statistik dashboard nyata dari DB | SELESAI | tes baru + smoke live |
| 3a. Progres live — backend ASYNC | SELESAI | tes baru + smoke live (POST 0,12 dtk) |
| 3b. .env CWD-independen + start script | SELESAI | tes baru + server jalan dari /tmp |
| 3c. Genre tidak default "drama" diam-diam | SELESAI | tes baru (unknown → None) |

## Detail per item

### 1. README.md — SELESAI
File baru `claude/README.md`: apa aplikasi, highlight (auto-generate,
genre auto-detect, Google Accounts + fallback, Flow Bridge, dashboard
stats), tech stack (FastAPI 0.115, Next.js 15, React 19, SQLAlchemy 2.0,
Nvidia NIM), quick start Docker + lokal, struktur proyek, cara kerja
auto-generate + aturannya, ringkas API (semua prefix `/api`, tanpa `/v1`),
Google login + fallback, cara tes (113 tes + catatan bare-pytest crash),
deployment, keterbatasan jujur, future improvements.
Acuan gaya: `hermes/README.md` (hanya dibaca, tidak diubah).

### 2. P1 — Prompts WAJIB coverage penuh — SELESAI
`backend/app/api/auto_generate.py`: `_prompts_for_batch()` 1 call LLM per
batch (10 episode) + 1 retry khusus episode yang dilewati; bila masih ada
yang hilang → langkah FAILED menyebut nomor episode.
`_step_prompts` tambah final coverage check: jumlah prompt
VIDEO_GENERATION di DB harus = jumlah episode.
Tes: `test_prompts_coverage_retries_missing_episode` (call pertama lewati
ep 2 → retry → completed, 3 prompt, 2 prompt-calls),
`test_prompts_coverage_fails_when_still_missing` (selalu lewati ep 2 →
langkah prompts FAILED, error menyebut "2").

### 2a. Jumlah total episode ditegakkan — SELESAI
`_plan_covers()` (plan harus memuat 1..N) + `_episode_plan` bertingkat;
`_step_episodes` gagalkan langkah bila plan tidak mencakup 1..N (pesan
"missing episode number(s)"). Berlaku langkah 4 (episodes) dan 5
(prompts memakai plan yang sama).
Tes: `test_episode_count_enforced` (bible+plan hanya 2 episode untuk total
5 → langkah episodes FAILED, "missing episode", 0 episode di DB).

### 2b. Judul hanya-spasi ditolak — SELESAI
Backend: `backend/app/schemas/auto_generate.py` — validator pydantic
`field_validator("title", mode="before")` strip → hanya-spasi jadi "" →
422 (min_length=1); `genre`/`premise` di-strip, kosong → None.
Frontend: `AutoGenerateModal.tsx` — hint merah "Title cannot be blank."
bila judul hanya-spasi.
Tes: `test_whitespace_title_rejected` (422 + judul berpadding disimpan
ter-strip).

### 2c. Genre "Auto (from title)" — inferensi LLM — SELESAI
`_infer_genre()` — 1 call LLM "Classify the genre" di langkah 1 bila genre
kosong; hanya menerima GENRE_OPTIONS (drama, romance, thriller, comedy,
horror, sci-fi, fantasy, action, mystery); bila gagal/tidak dikenal →
None. Semua `or 'drama'` dihapus. Label modal jadi
"Auto-detect (AI infers from title)".
Tes: `test_genre_inferred_from_title` (genre → "romance"),
`test_genre_unknown_stays_unset` (genre "western" dari LLM → job.genre
None).
Smoke live: judul "Istri yang Diremehkan" → genre ter-infer "drama"
(klasifikasi LLM nyata, bukan default).

### 2d. Overlay tidak menutup modal saat running — SELESAI
`AutoGenerateModal.tsx`: `handleOverlayClick` tidak menutup bila job
running; tombol X disabled saat running; tambah `stepSummaryText()`
(ringkasan 1 baris per langkah completed dari `result_summary` JSON).
Verifikasi: `npx tsc --noEmit` 0 error, `npm run build` 17 route OK.
Klik manual UI di browser TIDAK terverifikasi (di luar jangkauan VM).

### 2e. Re-run tanpa buang 1 call LLM — SELESAI
`_episode_plan` pakai ulang bertingkat: summary bible job ini → summary
bible job terdahulu untuk proyek yang sama → episode yang sudah ada di DB
(bila mencakup 1..N) → baru 1 call LLM. Langkah lain (bible/characters/
locations/prompts) sudah memakai ulang hasil COMPLETED sebelumnya.
Tes: `test_rerun_makes_no_llm_calls` (run ke-1 tepat 4 call:
bible+characters+locations+prompts; run ke-2 tepat 0 call).

### 2f. Statistik dashboard nyata dari DB — SELESAI
Backend baru: `backend/app/schemas/dashboard.py` (`DashboardStats`) +
`backend/app/api/dashboard.py` (`GET /api/dashboard/stats`, hitung via
`Project.owner_id == user`, `deleted_at is None`, join
Characters/Locations/Episodes via subquery project_id), didaftarkan di
`main.py` prefix `/api`.
Frontend: `src/lib/api.ts` tambah `dashboardApi.getStats()`;
`src/types/api.ts` tambah `DashboardStats`;
`src/app/dashboard/page.tsx` panggil stats saat mount, pakai hitungan
nyata (fallback projects.length / 0 selagi loading).
Tes: `test_dashboard_stats.py` (counts nyata; user-scoped; tanpa auth →
401). Smoke live: stats `{projects: 1, characters: 5, locations: 4,
episodes: 3}`.

### 3a. Progres live — backend ASYNC — SELESAI
`backend/app/api/auto_generate.py` ditulis ulang: POST create + POST retry
membuat job lalu `asyncio.create_task(_run_job_in_background(...))` dan
langsung return 201/200 status "running"; job jalan di background dengan
session sendiri; GET sudah ada untuk polling.
`_mark_interrupted_jobs_failed()`: sweep startup — job RUNNING → FAILED +
step RUNNING → FAILED ("Interrupted by server restart"), dipanggil dari
lifespan di `main.py` setelah `init_db()`; asumsi single-worker (dicatat
di kode + README).
Frontend modal: polling sudah ada, komentar diperbarui; progres per
langkah kini tampil dari data langkah (bukan hanya "generating").
Tes: `test_post_returns_running_immediately` + semua tes lama diperbarui
untuk async (POST assert "running" lalu poll sampai terminal).
Smoke live: POST kembali 0,12 dtk status running; poll menunjukkan
series_bible running → completed, characters running → completed,
locations, episodes, prompts satu-satu; completed ~121 dtk (3 episode,
LLM nyata).

### 3b. .env CWD-independen + start script — SELESAI
`backend/app/core/config.py`: `env_file` kini
`Path(__file__).resolve().parents[2] / ".env"` (absolut ke `backend/.env`,
bukan CWD).
`backend/start.sh` (baru, chmod +x): cd ke direktori script, aktifkan
`venv` bila ada, `exec python -m uvicorn app.main:app --host
${HOST:-0.0.0.0} --port ${PORT:-8000}`.
Tes: `test_config.py` (env_file absolut = `backend/.env`, independen dari
CWD via monkeypatch chdir).
Verifikasi live: server dijalankan dari `/tmp` dengan
`PORT=8003 bash backend/start.sh`, `/health` 200, smoke auto-generate
jalan (key trial dari `backend/.env` terbaca meski CWD = /tmp).

### 3c. Genre tidak default "drama" diam-diam — SELESAI
Lihat 2c: semua `or 'drama'` dihapus; genre hasil inferensi disimpan di
`job.genre`; bila inferensi gagal/tidak dikenal → None (label tampil
"not specified — choose the genre that best fits the title" di prompt
LLM langkah 1). Tes `test_genre_unknown_stays_unset`.

### .env.example — baru
`backend/.env.example` dibuat (kaki Claude sebelumnya tidak punya):
template tanpa nilai nyata (SECRET_KEY/ENCRYPTION_KEY/NVIDIA_API_KEY
placeholder). `.env` tetap ter-ignore git — nilai key TIDAK pernah
dicetak/ditulis di mana pun.

## Bukti tes

- **Full suite backend: 113 passed dalam 145,49 dtk** (baseline F1:
  100/100 via daftar file eksplisit; +13 tes baru: 8 auto-generate, 3
  dashboard stats, 2 config). Perintah:
  `venv/bin/python -m pytest tests/test_auth.py tests/test_auto_generate.py
  tests/test_browser_login.py tests/test_characters_locations.py
  tests/test_config.py tests/test_dashboard_stats.py tests/test_fix_round2.py
  tests/test_google_fallback.py tests/test_new_routers.py tests/test_projects.py
  -q -p no:warnings` → `113 passed in 145.49s`.
- **Perbaikan saat tes gagal (root cause terverifikasi):** 4 tes gagal awal
  karena DB tes `:memory:` SQLite memakai satu koneksi bersama
  (SingletonThreadPool) — session background + session polling GET
  bertabrakan. Perbaikan: `backend/tests/conftest.py` — DB tes kini file
  temp (`tempfile.mkstemp`, prefix `micro_drama_test_`) + fixture
  session-scoped `_cleanup_test_db` yang menghapus file di akhir sesi.
  Jejak `AttributeError: module 'bcrypt' has no attribute '__about__'`
  di log hanya warning passlib yang terperangkap (pre-existing, tidak
  berbahaya).
- **Frontend: `npx tsc --noEmit` 0 error; `npm run build` OK (17 route).**
- **Smoke live async (LLM nyata, key trial di `.env`):** server baru dari
  `/tmp` via `start.sh` port 8003; POST auto-generate 201 dalam 0,12 dtk
  status running; job 3 episode completed ~121 dtk; progres per langkah
  terlihat di poll; genre ter-infer "drama"; 3 episode + 3 prompt di DB;
  dashboard stats nyata (1/5/4/3). Server smoke sudah dimatikan setelah
  selesai. Akun tes `smoke-async@example.com` + proyek smoke tertinggal
  di `backend/micro_drama.db` (data tes, bukan data Di).

## File yang diubah / dibuat

Backend:
- `backend/app/schemas/auto_generate.py` (ditulis ulang — validator judul)
- `backend/app/core/config.py` (env_file absolut)
- `backend/app/api/auto_generate.py` (ditulis ulang — async, genre
  inferensi, episode count, prompt coverage, re-run idempotent, sweep
  restart)
- `backend/app/schemas/dashboard.py` (baru)
- `backend/app/api/dashboard.py` (baru)
- `backend/app/main.py` (register dashboard router + sweep startup)
- `backend/start.sh` (baru, +x)
- `backend/.env.example` (baru)
- `backend/tests/test_auto_generate.py` (ditulis ulang — async + 8 tes baru)
- `backend/tests/test_dashboard_stats.py` (baru)
- `backend/tests/test_config.py` (baru)
- `backend/tests/conftest.py` (DB tes file temp)

Frontend:
- `frontend/src/types/api.ts` (DashboardStats)
- `frontend/src/lib/api.ts` (dashboardApi.getStats)
- `frontend/src/components/auto-generate/AutoGenerateModal.tsx` (label
  genre, overlay-click, tombol X, hint judul kosong, ringkasan langkah)
- `frontend/src/app/dashboard/page.tsx` (stats nyata)

Lainnya:
- `claude/README.md` (baru)
- `claude/FUTURE-DEV-REPORT.md` (file ini)

Tidak ada file kaki lain yang disentuh. Tidak ada perubahan di luar scope.

## NOT VERIFIED (jujur, di luar jangkauan VM ini)

- Login Google asli akun Di, submit prompt Flow nyata, video Flow.
- Klik manual UI di browser (modal auto-generate + dashboard) — hanya
  tsc/build + API yang terverifikasi.
- Job 30 episode live (smoke 3 episode; Fase 3 dulu 5 episode).
- Keamanan (rate limiting, revokasi token, SECRET_KEY kuat, security
  headers) — tetap ditunda sesuai keputusan Di 17 Nov; README menyebutnya
  sebagai keterbatasan.
