# Google Account Fallback — Flow Bridge (kaki Claude)

Tanggal: 17 Nov 2026, ~21:03–22:30 WIB. Perintah Di 21:03 WIB (gap audit ronde 2:
fallback LLM sudah jalan, fallback akun Google belum ada).
Scope: fungsionalitas saja, security DITUNDA. Hanya kaki Claude; kaki lain, folder
audit, dan GitHub tidak disentuh.

## Temuan arsitektur (penting)

- **Tidak ada eksekusi Flow otomatis di kaki ini** — sama seperti kaki Hermes
  (`hermes/backend/app/api/flow_bridge.py`, dibaca sebagai referensi): bridge-nya
  manual, export → Flow manual di flow.google.com → import. Jadi tidak ada titik
  eksekusi yang bisa di-retry; fallback diterapkan di titik akun benar-benar
  dipakai: **resolusi akun + validasi token** sebelum task ditandai siap Flow.
- Sebelumnya: task terikat ke satu `google_account_id` yang dipilih saat buat
  task; kalau akun itu kuotanya habis / token invalid / refresh gagal, task gagal
  tanpa alternatif.

## Cara kerja fallback

- `POST /api/flow/{project_id}/{task_id}/execute` — resolve akun lalu tandai task
  `ready_for_flow`. `POST /api/flow/{project_id}/{task_id}/retry` — retry manual
  untuk task FAILED/PENDING (menghapus error lama, resolve ulang).
- Urutan kandidat (mirip fallback LLM di `app/services/ai_client.py`: coba
  berurutan berdasar prioritas, pindah saat gagal): akun yang di-pin di task
  dulu, lalu akun aktif lain milik user yang sama diurutkan `account_index`.
  Akun nonaktif dan akun user lain tidak pernah dicoba.
- Per akun: (1) token kedaluwarsa (< 5 menit) → refresh via refresh token;
  (2) token (hasil refresh) diverifikasi ke Google tokeninfo. Akun dilewati bila:
  `no_token`, `token_expired` (tanpa refresh token), `refresh_failed`,
  `token_invalid`, `quota_exceeded` (429). Akun pertama yang lolos dipakai,
  `google_account_id` task diikat ke akun itu, `last_used_at` dicatat.
- **Semua akun gagal → error jujur, bukan diam-diam gagal:** task disimpan
  `FAILED` dengan `error_message` yang menyebut tiap akun + alasannya, dan
  endpoint menjawab **502** dengan detail yang sama.
- **Google tidak terjangkau** (network/proxy) → run di-abort setelah akun
  pertama (akun lain akan kena jaringan mati yang sama), task FAILED dengan
  alasan `unreachable`.
- Jejak audit: field baru `fallback_history` (JSON Text) di task, berisi tiap
  percobaan `{"account_id","email","outcome","reason","detail"}` — akun mana
  dipakai + alasan pindah tercatat di task itu sendiri.
- Token dibaca **terenkripsi langsung dari DB di backend**; endpoint
  `GET /google-accounts/{id}/tokens` TIDAK dipakai dan TIDAK diubah.
- Completed/imported/in-progress task tidak bisa di-execute/retry (400) —
  task selesai tidak pernah diikat ulang ke akun lain.

## File yang diubah / dibuat

- BARU `backend/app/services/google_account_service.py` — `refresh_access_token`,
  `verify_access_token`, `get_google_oauth_credentials`, `GoogleAccountError`
  (reason: `no_token`/`token_expired`/`refresh_failed`/`token_invalid`/
  `quota_exceeded`/`unreachable`).
- BARU `backend/app/services/flow_account_fallback.py` — `get_candidate_accounts`,
  `resolve_account_for_task`, `run_fallback_for_task`, `AllGoogleAccountsFailed`,
  `GoogleUnreachable`.
- `backend/app/models/flow_bridge.py` — field baru `fallback_history` (Text, nullable).
- `backend/app/schemas/flow_bridge.py` — `fallback_history` di `FlowBridgeRead`.
- `backend/app/api/flow_bridge.py` — endpoint `POST .../execute` dan `POST .../retry`.
- `backend/app/api/google_accounts.py` — endpoint `/refresh` dan blok refresh di
  `/verify` kini memakai service yang sama (respons tidak berubah; logika OAuth
  login/callback tidak disentuh). Helper kredensial dipindah ke service.
- BARU `backend/alembic/versions/f4a11c9d205e_flow_fallback_history.py`
  (revises `b3f8a1c9d204`) — tambah kolom `fallback_history`.
- BARU `backend/tests/test_google_fallback.py` — 11 tes (lihat bawah).

## Hasil tes (nyata, bukan kutip)

Perintah: `cd backend && ./venv/bin/python -m pytest tests/ -q`
(dari `backend/venv` — `claude/venv` tidak dipakai, sesuai catatan bcrypt/passlib).

- Baseline sebelum perubahan: **68 passed**.
- Setelah perubahan: **79 passed** (68 lama + 11 baru), 0 gagal.
- 11 tes baru (`tests/test_google_fallback.py`, Google di-stub di seam service):
  akun pertama kuota 429 → pindah ke akun kedua → berhasil; semua akun gagal →
  502 + task FAILED + error menyebut tiap akun; retry setelah gagal → berhasil;
  tanpa akun → 502 + "No enabled Google accounts"; token kedaluwarsa + refresh
  jalan → akun sama dipakai; refresh gagal → fallback ke akun berikut; akun
  nonaktif tidak dicoba; tanpa akun ter-pin → urutan `account_index`;
  execute/retry pada task completed → 400; Google unreachable → abort setelah
  akun pertama.

## Smoke live (server nyata, DB segar)

- `DATABASE_URL="sqlite+aiosqlite:////tmp/smoke-fallback.db" ./venv/bin/python -m alembic upgrade head`
  → migrasi jalan bersih: `96117fdda23d → b3f8a1c9d204 → f4a11c9d205e`, kolom
  `fallback_history` ada di `flow_bridge`, head = `f4a11c9d205e`.
- Server `uvicorn app.main:app --host 127.0.0.1 --port 8123` → `/docs` 200.
  Register (201) → login → buat project → 2 akun Google (token palsu) → buat
  task ter-pin ke akun 1 → `POST /flow/{project}/{task}/execute`.
- Hasil aktual: **502 `{"detail":"Google could not be reached"}`**; GET task →
  `status: failed`, `error_message: "Google unreachable: ..."`,
  `fallback_history` mencatat 1 percobaan akun 1 `reason: unreachable`,
  detail `Could not reach Google: [SSL: CERTIFICATE_VERIFY_FAILED] ...`.
  `POST .../retry` → 502 yang sama. Server dimatikan setelah smoke
  (curl exit 7, tidak ada uvicorn tersisa).

## Yang TIDAK terverifikasi live (jujur)

- **Jalur sukses end-to-end dengan akun Google asli TIDAK bisa di-smoke dari VM
  ini**: tokeninfo Google gagal di level TLS — proxy egress VM meng-intercept
  (`SSL: CERTIFICATE_VERIFY_FAILED, self-signed certificate in chain`), jadi
  verifikasi token terhadap Google nyata tidak pernah sampai. Ini perilaku
  environment yang sudah ada (kode refresh/verify lama juga pakai `verify=True`),
  bukan akibat perubahan ini. Jalur sukses (akun 1 gagal → akun 2 dipakai)
  terverifikasi di pytest dengan Google di-stub; verifikasi dengan akun asli
  butuh environment dengan egress bersih (HP/laptop atau VM tanpa intercept TLS).
- **Tidak diubah (sengaja):** endpoint `GET /google-accounts/{id}/tokens` masih
  mengembalikan access/refresh token + password plaintext — blocker terpisah,
  butuh perintah Di. Enkripsi, rate limiting, security headers, SECRET_KEY,
  logika OAuth login/callback tidak disentuh.

## Catatan

- `verify_access_token` sengaja TIDAK memakai `verify=False` seperti panggilan
  Nvidia di `ai_client.py` — menonaktifkan verifikasi TLS adalah keputusan
  security, di luar scope tugas ini (security ditunda).
- Satu insiden saat smoke: `pkill -f` dengan pola yang sama dengan command
  shell membunuh shell sendiri (pola sudah dikenal, AGENTS.md); server akhirnya
  dimatikan dan dikonfirmasi mati via `curl` (exit 7) + `ps`.
