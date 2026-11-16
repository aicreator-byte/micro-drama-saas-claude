Perbaiki cacat hasil verifikasi independen kaki Claude (Micro Drama SaaS). Kerja HANYA di /home/hatch/workspace/micro-drama-saas/claude/ — DILARANG buka/baca/salin ../hermes/ dan ../opencode/. Jangan mulai dari nol; perbaiki kode yang ada.

## Cacat: HTTP 500 di endpoint project-scoped (satu akar masalah)

`get_current_user_id` (app/api/auth.py) mengembalikan `sub` JWT sebagai STRING. Beberapa router membandingkan kolom UUID langsung dengan string mentah (path param / user_id) tanpa konversi `uuid.UUID(...)`. Bind processor SQLAlchemy Uuid memanggil `.hex` pada string → `AttributeError: 'str' object has no attribute 'hex'` → HTTP 500. Terverifikasi live 16 Nov (48x error ini di log server): series-bible, episodes, prompts, google-accounts semua 500.

Yang harus diperbaiki (audit SEMUA router, jangan hanya yang disebut):
1. `app/api/series_bible.py` — punya `_verify_project_access` LOKAL sendiri yang salah: `Project.id == project_id` (string). Samakan dengan versi benar di `app/api/projects.py` (konversi `uuid.UUID(project_id)` DAN `uuid.UUID(user_id)`), atau hapus duplikatnya dan import dari projects. Juga `SeriesBible.project_id == project_id` dan insert `SeriesBible(project_id=project_id)` — konversi ke UUID.
2. `app/api/episodes.py` — `Episode.project_id == project_id` (string) di banyak tempat + insert `project_id=project_id` (string). Konversi semua ke UUID.
3. `app/api/prompts.py` — list/prompts 500, kemungkinan pola sama (`project_id` string). Periksa + konversi.
4. `app/api/google_accounts.py` — baris 28: count query `GoogleAccount.user_id == user_id` (string) → akun PERTAMA saja sudah 500, jadi batas 20 akun tidak pernah teruji live. Konversi ke UUID. Penerimaan: 20 akun bisa dibuat, ke-21 ditolak 400.
5. Periksa juga `assets.py`, `scenes.py`, `dialogues.py`, `flow_bridge.py`, `story_engine.py` untuk pola yang sama (UUID dibanding string) dan perbaiki bila ada.

## Yang JANGAN diubah
- Story Engine tetap template/mock (sudah diketahui, sama seperti kaki lain) — jangan pura-pura jadi LLM asli.
- Google OAuth tetap mock/placeholder — jangan pura-pura jadi OAuth asli.
- Jangan ubah struktur API, nama route, atau skema respons.

## Penerimaan (WAJIB lolos semua sebelum selesai)
- Series bible create → 201; episode create → 201; scene + dialogue create → 201; prompts list → 200.
- 20 akun Google → 201 semua; akun ke-21 → 400.
- `pytest tests/ -q` → 32 passed, proses keluar sendiri.
- `npm run build` di frontend → exit 0.
- Tulis FIX-REPORT.md di claude/ — daftar file yang diubah + hasil tes di atas.
