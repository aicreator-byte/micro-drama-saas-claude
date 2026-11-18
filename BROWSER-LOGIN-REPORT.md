# Jalur Login Browser + Auto Ganti Akun — Flow Bridge (kaki Claude)

Tanggal: 17 Nov 2026, ~22:23–23:30 WIB. Perintah Di 22:22 WIB: Di menolak
jalur Google Cloud Console ("Hrsnya login biasa. Dengan browser
masing2").
Scope: fungsionalitas saja, security DITUNDA. Hanya kaki Claude; kaki
lain, folder audit, dan GitHub tidak disentuh.

## Yang dibangun

Jalur eksekusi Flow otomatis lewat browser sungguhan (Playwright +
Chromium), tanpa Cloud Console sama sekali: tidak ada client_id/secret,
tidak ada OAuth code exchange di jalur ini. Browser sign-in ke Google
dengan email + password akun (password dibaca TERENKRIPSI dari DB, cara
enkripsi tidak diubah), sesi disimpan di profil browser persisten per
akun — satu akun satu profil, cookie tidak bercampur.

## Cara kerja

### 1. Login browser — `backend/app/services/browser_login.py` (BARU)

- `login_google_account(account, headless=True, login_url=None)`:
  buka profil persisten akun (`data/browser_profiles/user_<id>/
  account_<id>/`, bisa di-override env `BROWSER_PROFILES_DIR`), isi
  `#identifierId` → `#identifierNext` → `input[type=password]` →
  `#passwordNext` di accounts.google.com. Kalau cookie profil masih
  hidup, langsung dianggap login (tidak isi ulang).
- Hasil login diklasifikasi jujur dari URL + isi halaman:
  `logged_in` | `challenge` (captcha/2FA/"Verify it's you"/bot check) |
  `wrong_password` | `still_signin`. Metadata sesi (status + waktu,
  TANPA secret) disimpan di `session.json` di dalam profil.
- `is_session_alive(user_id, account_id)`: buka profil, kunjungi
  myaccount.google.com, True bila Google tidak melempar balik ke
  sign-in.
- `execute_flow_prompt(account, prompt, ...)`: pastikan sesi dulu
  (sesi mati → login ulang sekali), buka flow.google.com, isi prompt
  box dan submit. Return `{"status": "submitted", "flow_url": ...}`.
  "Submitted" artinya prompt sampai ke input Flow — BUKAN jaminan
  video jadi; hasil tetap di-import lewat `/import` seperti jalur
  manual.
- `BrowserLoginError(reason, detail)` — reason: `no_password`,
  `login_failed`, `captcha_or_2fa`, `session_expired`,
  `quota_exceeded`, `flow_blocked`, `unreachable`,
  `browser_unavailable`. Semua kegagalan dilempar sebagai error,
  tidak pernah dipalsukan jadi sukses.

### 2. Auto ganti akun — `backend/app/services/flow_browser_execution.py` (BARU)

Mirror fallback token (`flow_account_fallback.py`): urutan kandidat
sama (akun ter-pin dulu, lalu akun aktif lain milik user yang sama
urut `account_index`; akun nonaktif / akun user lain tidak dicoba).
Per akun: tanpa password → skip (`no_password`); login ditolak /
captcha / kuota habis / Flow memblokir → catat, pindah ke akun
berikut; Google/browsing tidak terjangkau → abort setelah akun
pertama (akun lain akan kena jaringan mati yang sama). Semua percobaan
di-append ke `fallback_history` task (mode `"browser"`, menyambung
riwayat fallback token yang sudah ada).
- Sukses: task diikat ke akun yang jalan, status `IN_PROGRESS`,
  `flow_url` terisi, `last_used_at` dicatat.
- Semua akun gagal: task `FAILED` + `error_message` menyebut tiap
  akun + alasannya, dan menyebut manual export tetap jalan; endpoint
  menjawab 502.

### 3. Endpoint baru

- `POST /api/flow/{project_id}/{task_id}/execute-browser`
  (di `app/api/flow_bridge.py`) — jalankan task via browser dengan
  auto ganti akun. Status yang boleh: PENDING / READY_FOR_FLOW /
  FAILED. Query `headless=true` (default). Task tanpa prompt → 400.
- `POST /api/google-accounts/{account_id}/browser-login`
  (di `app/api/google_accounts.py`) — login browser satu akun, simpan
  sesi. Tanpa password → 400; password ditolak → 401; captcha/2FA →
  400 (dengan penjelasan login manual); Google/browser tidak
  terjangkau → 502.
- `GET /api/google-accounts/{account_id}/browser-session` — status
  sesi tersimpan (baca file, browser tidak diluncurkan);
  `has_session: false` bila akun belum pernah login via browser.

### 4. Lingkungan

- `playwright==1.65.2` ditambah ke `backend/requirements.txt` dan
  terinstal di `backend/venv`.
- Chromium 1255 + headless shell 1255 terunduh ke
  `~/.cache/ms-playwright/` (CDN Playwright ternyata BISA dijangkau —
  bertentangan dengan catatan lama soal CDN terblokir) dan launch
  default-path terverifikasi jalan.
- `backend/.gitignore` (BARU): `data/` — profil browser berisi cookie
  sesi Google, tidak boleh ter-commit.

## Hasil tes (nyata)

Perintah: `cd backend && ./venv/bin/python -m pytest tests/ -q`
(dari `backend/venv`).

- Baseline sebelum perubahan: **79 passed**.
- Setelah perubahan: **92 passed** (79 lama + 13 baru), 0 gagal.
- 13 tes baru (`tests/test_browser_login.py`):
  - Orkestrasi (browser runner di-fake): login akun 1 ditolak → akun 2
    jalan, task `in_progress`, `flow_url` terisi, history mode browser
    mencatat keduanya; semua akun gagal → 502 + task FAILED + error
    menyebut tiap akun + "manual export"; akun tanpa password di-skip
    (`no_password`); task tanpa prompt → 400; Google unreachable →
    abort setelah akun 1; task completed → 400.
  - Bukti tanpa Console: satu tes menambal
    `get_google_oauth_credentials` agar meledak bila dipanggil —
    jalur browser lolos tanpa menyentuhnya.
  - Endpoint: `POST /browser-login` (login fn di-stub) → 200 +
    `session_saved: true`; `GET /browser-session` → false sebelum
    login, record tersimpan setelah save (dan record tidak mengandung
    password); login tanpa password → 400.
  - Mekanik Playwright sungguhan (tanpa Google): cookie persisten di
    profil bertahan melewati relaunch; profil dua akun terpisah (cookie
    akun 1 tidak bocor ke akun 2); `login_google_account()` asli
    melawan halaman sign-in palsu lokal — password benar → `logged_in`
    + `session.json` tersimpan, password salah → `login_failed`.
  - Satu pelajaran saat tes: cookie sesi (tanpa expiry) memang TIDAK
    ditulis Chromium ke disk — cookie auth Google asli selalu punya
    expiry, jadi tes memakai cookie `max-age`.

## Smoke live (server nyata, DB segar)

- `DATABASE_URL="sqlite+aiosqlite:////tmp/smoke-browser.db" alembic
  upgrade head` → head tetap `f4a11c9d205e` (tidak ada migrasi baru —
  sesi browser disimpan di file, bukan kolom DB). Server `:8124` →
  `/docs` 200. Register → 2 akun (password palsu) → task berisi 1
  prompt ter-pin ke akun 1.
- `POST /flow/{project}/{task}/execute-browser` dengan browser
  sungguhan: Chromium launch, navigasi ke flow.google.com, lalu
  **502 jujur** `Could not reach Google Flow: net::ERR_TUNNEL_CONNECTION_FAILED`;
  task `failed`, `fallback_history` mencatat 1 percobaan akun 1
  `reason: unreachable`, `mode: browser` (abort setelah akun pertama,
  sesuai desain).
- `POST /google-accounts/{id}/browser-login` (browser sungguhan):
  **502 jujur** `Could not reach Google: net::ERR_TUNNEL_CONNECTION_FAILED
  at accounts.google.com/signin/v2/identifier`; `GET /browser-session`
  tetap `has_session: false` (login gagal tidak menulis sesi).
- Server dimatikan setelah smoke (PID eksplisit, curl exit 7); file
  smoke di /tmp dibersihkan.

## Yang TIDAK terverifikasi live (jujur)

- **Login Google asli TIDAK BISA diverifikasi dari VM ini**: tidak ada
  kredensial Google asli (Di belum berikan akun/password), dan egress
  VM memblokir Google di level tunnel (`ERR_TUNNEL_CONNECTION_FAILED`
  untuk accounts.google.com maupun flow.google.com — browser tidak
  pernah sampai ke halaman login). Mekanik login terverifikasi hanya
  melawan halaman sign-in palsu lokal (selektor + deteksi hasil yang
  sama). Verifikasi dengan akun asli butuh environment dengan egress
  bersih + akun/password dari Di.
- **Submit prompt ke Flow asli TIDAK terverifikasi**: selektor prompt
  box Flow (`textarea`, `[contenteditable]`) adalah best-effort dan
  belum pernah dicocokkan dengan DOM flow.google.com yang asli. Bila
  tidak cocok, kode melempar `flow_blocked` dan mengarahkan ke manual
  export — tidak pernah mengklaim generasi berjalan.
- **Google bisa memblokir otomasi** (bot detection / captcha / 2FA)
  kapan saja — itu ditangani sebagai `captcha_or_2fa` + pindah akun /
  fallback manual, bukan sebagai kegagalan diam-diam.

## Yang TIDAK dikerjakan (sengaja)

- Endpoint `GET /google-accounts/{id}/tokens` TIDAK disentuh (masih
  mengembalikan token+password plaintext — blocker terpisah, butuh
  perintah Di). Enkripsi, rate limiting, security headers, SECRET_KEY,
  logika OAuth login/callback tidak disentuh.
- Tidak ada migrasi Alembic baru (tidak ada kolom DB baru).
- Tidak ada push ke GitHub.

## File yang diubah / dibuat

- BARU `backend/app/services/browser_login.py` — login browser,
  cek sesi, eksekusi Flow, penyimpanan profil/sesi per akun.
- BARU `backend/app/services/flow_browser_execution.py` — orkestrasi
  auto ganti akun + pencatatan `fallback_history` mode browser.
- `backend/app/api/flow_bridge.py` — endpoint `execute-browser`.
- `backend/app/api/google_accounts.py` — endpoint `browser-login` +
  `browser-session` (endpoint `/tokens` tidak disentuh).
- BARU `backend/tests/test_browser_login.py` — 13 tes.
- `backend/requirements.txt` — `playwright==1.65.2`.
- BARU `backend/.gitignore` — `data/` (profil browser berisi cookie).
