# AUTO-GENERATE Fase 1 — Backend Report (kaki Claude)

**Tanggal:** 19 Nov 2026. **Spek:** `~/workspace/micro-drama-saas/AUTO-GENERATE-SPEC.md` (Gate 1 disetujui Di 19 Nov 04:04).
**Ruang lingkup:** backend saja. Frontend TIDAK disentuh, kaki lain TIDAK disentuh, TIDAK push GitHub.

## Yang dibangun

Satu job, 5 langkah berurutan, tiap langkah menulis barisnya langsung (tanpa Apply manual).
Langkah gagal → pipeline berhenti; retry hanya langkah gagal; jalan ulang job → skip yang
sudah ada (idempotent).

### Endpoint baru (router `app/api/auto_generate.py`, prefix `/api/projects`)

| Endpoint | Fungsi |
|---|---|
| `POST /{project_id}/auto-generate` (201) | Buat job + 5 langkah, jalankan berurutan sinkron (seperti story-engine generate). Body: `title` (wajib), `genre`, `total_episodes` (default 30, 1–100), `premise`. |
| `GET /{project_id}/auto-generate/{job_id}` | Status job + tiap langkah (terurut). |
| `POST /{project_id}/auto-generate/{job_id}/retry/{step}` | Retry satu langkah FAILED saja; langkah sebelumnya harus COMPLETED; langkah COMPLETED tidak pernah diulang. Step tak dikenal → 400. |

### Langkah (mesin LLM kaki yang sudah ada — `ai_client.generate`, key Nvidia dari env)

| # | Langkah | Cara kerja di kaki Claude |
|---|---|---|
| 1 | Series Bible | LLM `generate` (JSON: premise, main_plot, subplots, relationships, world, tone, visual, ending, episode_structure + daftar episode). Upsert ke `series_bibles` (unik per proyek). Daftar episode disimpan di `result_summary` langkah untuk dipakai langkah 4. |
| 2 | Characters | LLM minta 5 karakter (role protagonist/antagonist/supporting). Tulis ke `characters` (skip nama yang sudah ada). Gagal bila LLM kembalikan <4. Default: skip LLM bila proyek sudah punya ≥4 karakter. |
| 3 | Locations | LLM minta 4 lokasi. Tulis ke `locations` (skip nama yang sudah ada). Gagal bila <3. Skip bila sudah ≥3. |
| 4 | Episodes | Pakai daftar episode dari langkah 1; bila kosong, satu call LLM (gaya FULL_SERIES). Tulis ke `episodes` status `PLANNED`, skip nomor yang sudah ada. |
| 5 | Prompts | Per episode yang belum punya prompt VIDEO_GENERATION: satu call LLM per batch 10 episode → tulis `prompts` (type `VIDEO_GENERATION`, status `completed`). Minimal 1 prompt per episode. |

### Adaptasi ke kaki Claude (beda dari OpenCode — diverifikasi dari kode)

- Kaki Claude TIDAK punya konsep task/apply Story Engine (hanya `POST /story-engine/generate`
  satu tembakan). Jadi job + langkah dibangun baru, bukan reuse apply.
- `EpisodeStatus` kaki ini TIDAK punya `OUTLINED` → episode baru pakai `PLANNED` (status awal
  yang ada di kaki ini).
- Endpoint `/prompts/generate` kaki ini HANYA template (status `template`, tanpa LLM — dicatat
  di kodenya sendiri). Langkah 5 memakai LLM langsung, BUKAN template itu.
- Seam tes: `app.api.auto_generate._llm_json` (satu fungsi LLM → JSON) — tes memonkeypatch ini.

## File diubah / dibuat

**Dibuat:**
- `backend/app/models/auto_generate.py` — `AutoGenerateJob`, `AutoGenerateStep`, enum status/langkah, `STEP_ORDER`.
- `backend/app/schemas/auto_generate.py` — `AutoGenerateCreate`, `AutoGenerateJobRead`, `AutoGenerateStepRead`.
- `backend/app/api/auto_generate.py` — router + 5 runner langkah + runner job + `_llm_json`/`_parse_json`.
- `backend/alembic/versions/a7c3e9f1b824_auto_generate_jobs.py` — migrasi (revisi `f4a11c9d205e`).
- `backend/tests/test_auto_generate.py` — 8 tes baru.
- `AUTO-GENERATE-F1-REPORT.md` (file ini).

**Diubah:**
- `backend/app/models/__init__.py` — export `AutoGenerateJob`, `AutoGenerateStep`.
- `backend/app/main.py` — import + `include_router(auto_generate.router, prefix="/api")`.

**TIDAK diubah:** frontend, auth/security, fallback akun Google, CRUD manual, Flow Bridge.

## §7 — perbaikan keanehan (temuan)

1. **Akun demo "Test" (test@example.com): TIDAK ADA di kaki Claude.** Grep `seed`/`test@example`
   di `app/` + `alembic/` kosong; `main.py` tidak seed user; register/login normal. Yang pakai
   `test@example.com` hanya helper tes (`tests/test_projects.py` register sendiri). → Tidak ada
   yang diperbaiki di backend; bila Di masih melihat akun Test, itu dari kaki lain / data lama.
2. **Counter "Active Projects": TIDAK ADA di backend kaki ini** (grep `active` di `app/api/` hanya
   `active_only` Google Accounts). Counter + badge hidup di frontend → dicatat untuk Fase 2,
   bukan dikerjakan di sini.

## Hasil tes

- Baseline sebelum perubahan: **92 passed** (139 dtk).
- Tes baru `tests/test_auto_generate.py`: **8 passed** (full run, gagal-berhenti, retry,
  idempotent, get job, 401 tanpa auth, 404 proyek tak ada, 400 retry step tak dikenal).
- Full suite setelah perubahan: **100 passed, 0 failed** (136 dtk). Tidak ada regresi.

## Migrasi (terverifikasi)

- `alembic upgrade head` di salinan DB: rantai `96117fdda23d → b3f8a1c9d204 → f4a11c9d205e → a7c3e9f1b824` jalan bersih; `downgrade -1` hapus kedua tabel kembali (terverifikasi di `/tmp`).
- Catatan: perintah verifikasi migrasi sempat menjalankan upgrade pada `micro_drama.db` live
  (env.py menimpa `sqlalchemy.url` dari settings) — hanya penambahan tabel, DB live kini di
  revisi `a7c3e9f1b824` dengan kedua tabel ada. Itu jalur normal (`init_db` menjalankan
  migrasi saat server start). Tidak ada data dihapus/diubah.

## NOT VERIFIED

- **Generasi LLM nyata:** semua tes memakai `_llm_json` palsu (canned JSON). Belum ada panggilan
  nyata ke Nvidia NIM dari endpoint ini (butuh `NVIDIA_API_KEY` + server jalan).
- **Smoke live:** belum dijalankan di server berjalan (hanya pytest + ASGI test client).
- **Perilaku bila provider LLM gagal total:** hanya diuji via fake yang melempar (langkah FAILED
  + job FAILED) — bukan terhadap provider nyata.
- **Frontend Fase 2** (tombol + progres) belum ada — job hanya bisa dipakai via API saat ini.
- **Akun Google / Flow:** tidak disentuh (di luar scope §8).
