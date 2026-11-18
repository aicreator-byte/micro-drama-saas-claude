MARKER: PHASE2-CLAUDE
# Phase 2 — Kaki Claude: LLM nyata + OAuth Google nyata + migrasi nyata

Baca dulu `../PHASE2-PROMPT.md` (spec bersama + desain settings/env + larangan) —
itu mengikat. Prompt ini hanya tugas spesifik kaki Claude.

KONTEKS (terverifikasi dari kode + audit, jangan diperdebatkan):
- Kerja HANYA di `/home/hatch/workspace/micro-drama-saas/claude/`. Jangan sentuh
  kaki lain atau file di luar direktori ini.
- Backend: `backend/app/` — router di `backend/app/api/` (`story_engine.py`,
  `google_accounts.py`, `auth.py`, `projects.py`, `series_bible.py`,
  `characters.py`, `locations.py`, `episodes.py`, `scenes.py`, `dialogues.py`,
  `prompts.py`, `flow_bridge.py`, `assets.py`); prefix `/api`
  (`backend/app/main.py`); config `backend/app/core/config.py`; enkripsi di
  `backend/app/core/` (pakai modul enkripsi yang sudah ada di kaki ini).
- Migrasi: `backend/alembic/versions/027a9ef8737e_initial.py` KOSONG — skema DB
  dibuat via `Base.metadata.create_all` saja. Itu bagian tugas.
- Frontend: Next.js di `frontend/src/app/` (login, register, dashboard: projects,
  series-bible, characters, locations, episodes, scenes, dialogues, prompts,
  assets, flow, google-accounts, settings). Halaman Settings SUDAH ADA —
  kembangkan itu, jangan buat baru.
- Baseline: pytest 32/32, smoke 20/20, build 19/19 halaman. Jangan turunkan.
- PERINGATAN: temuan auditor Claude soal "scene create gagal" SALAH — scene
  create terverifikasi 201 (fix3). JANGAN ubah `SceneCreate` / `scenes.py` /
  `dialogues.py` dari fix2–fix3. JANGAN ubah skema `SceneCreate` (field
  `episode_id` tetap seperti sekarang).

TUGAS (hanya ini):
1. **LLM nyata ganti mock Story Engine** (`backend/app/api/story_engine.py`):
   generate memakai template dict + `tokens_used = 500` mock (baris ~44–95).
   Buat satu modul klien AI kecil (mis. `backend/app/services/ai_client.py`,
   pakai `httpx` yang sudah terpasang): baca daftar provider + urutan fallback
   dari setting (lihat spec bersama), kunci dari env var, panggil chat
   completions, fallback ke provider berikut bila gagal/kuota/kosong. Ganti
   SEMUA template mock dengan panggilan LLM nyata. Provider terverifikasi
   jalan: Nvidia NIM ultra-550b — jadikan entri pertama/aktif. Jangan klaim
   provider lain jalan.
2. **Settings API + model** (baru, ikuti pola router/model yang ada):
   tabel/model `AppSettings` (satu baris): `ai_providers` (JSON, lihat spec),
   `google_oauth_client_id` + `google_oauth_client_secret` (enkripsi pakai
   modul enkripsi kaki ini). Endpoint `GET /api/settings` (tanpa nilai
   rahasia — hanya flag `configured`) dan `PATCH /api/settings` (ubah urutan/
   enabled provider, isi kredensial OAuth). Kunci AI tetap env var, tidak
   disimpan di DB. Kembangkan halaman Settings yang sudah ada untuk mengedit
   ini (daftar provider + urutan fallback + kredensial OAuth sebagai field
   password yang tidak pernah tampil nilainya).
3. **OAuth Google nyata** (`backend/app/api/google_accounts.py`): ganti mock
   total — authorize URL mock (baris ~186, `client_id` mock di ~197) dan akun
   mock + token mock (~219–242) dihapus. Implementasikan authorize URL Google
   asli (state acak per request, simpan + validasi di callback), callback tukar
   `code` → token (httpx POST ke token endpoint Google), simpan token
   terenkripsi, refresh saat kedaluwarsa. Tambah field `password_encrypted`
   pada record akun Google (enkripsi yang sama) untuk Flow Bridge.
   BATAS: kredensial OAuth client asli dari Di belum ada — verifikasi alur
   + URL + callback + refresh; login end-to-end = NOT VERIFIED di laporan.
4. **Migrasi Alembic nyata**: generate migrasi asli dari model saat ini
   (`alembic revision --autogenerate`, ganti file initial yang kosong) dan
   alihkan lifespan startup ke `alembic upgrade head` (jangan lagi
   `create_all`). Migrasi harus bisa naik-turun bersih di DB segar.
5. **Paritas + koreksi kecil** (sekunder): tambah model `Shot` + `SceneEngine`
   minimal (ikuti pola model/skema yang ada, lewat migrasi tugas 4) — OpenCode
   punya keduanya, Claude belum. Validasi `location_id` di Scenes API harus
   milik proyek yang sama (tolak 400 bila tidak). Tambah tes pytest untuk
   router yang belum dites (episodes, scenes, dialogues, prompts, assets,
   google_accounts, flow_bridge, story_engine) — minimal 1 tes per router.
   JANGAN ubah `SceneCreate` (lihat PERINGATAN di atas).

JANGAN UBAH: route/prefix `/api`/skema respons yang ada (TIDAK ada prefix
`/api/v1` — jangan tambah); `SECRET_KEY`, auth/JWT, enkripsi yang ada;
perbaikan fix round 1–3; batas karakter (maks 6 TIDAK ditegakkan).

SEBELUM menyatakan selesai, jalankan sendiri tes live (uvicorn + SQLite segar):
register + login + proyek + series-bible + 6 karakter + lokasi + story
generate LLM nyata (konten BUKAN template mock — buktikan dengan potongan
respons) + episode + scene 201 + dialogue 201 + auth URL Google terbentuk
(awal `https://accounts.google.com/o/oauth2/v2/auth`, berisi `state`) + callback
menolak `state` salah + migrasi naik-turun bersih di DB segar + Settings PATCH
tersimpan + `GET /settings` tidak membocorkan rahasia + pytest tidak turun
dari 32 + `npm run build` exit 0. Tulis `PHASE2-REPORT.md` (apa yang diubah +
hasil tes live per endpoint + NOT VERIFIED: login Google end-to-end).
