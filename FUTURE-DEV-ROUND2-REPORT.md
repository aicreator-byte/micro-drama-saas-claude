# Future Dev — Round 2 Report (kaki Claude)

Tanggal: 20 November 2026 (23:27–23:55 WIB).
Ruang lingkup: `~/workspace/micro-drama-saas/claude/` SAJA. Tidak ada push ke GitHub.
Dasar: `FUTURE-DEV-REPORT.md` (ronde 1) + `AUTO-GENERATE-SPEC.md` — tidak ada pekerjaan ronde 1 yang diulang.

## Ringkasan

| Item | Status | Bukti |
|---|---|---|
| 1a. Job live 30 episode (LLM nyata) | **SELESAI** | Job `e7944f19…` COMPLETED, 1 bible / 5 karakter / 4 lokasi / 30 episode / 30 prompt |
| 1b. Login Google asli + submit Flow end-to-end | **NOT VERIFIED** | Sampai halaman sign-in Google asli (screenshot), kredensial TIDAK dimasukkan — alasan di bawah |
| 2. Click-through browser Auto-Generate + dashboard | **SELESAI, 13/14 langkah** (1 temuan → diperbaiki, re-check 4/4) | 14 screenshot + `steps.json` di `FUTURE-DEV-ROUND2-evidence-clickthrough/` |
| 3. Security hardening | **SELESAI** | Prod tolak start dengan secret lemah (exit 3); header keamanan live |
| 4. Multi-worker safe job execution | **SELESAI** | Migrasi teraplikasi; 8 tes locking hijau |

Tes: **pytest 135 passed (311,67 dtk)** · `tsc --noEmit` **0 error** (2x, sebelum & sesudah perbaikan layout) · `npm run build` **OK, 17 route** (2x).

---

## 1. Job live 30 episode + login Google asli

### 1a. Job 30 episode — SELESAI

- Job `e7944f19-a421-4b5c-9cd5-ec91bcf2227b`, proyek `299d161b-be7d-460a-aa5b-c769c482cec8` ("Dendam Sang Pewaris", genre drama), user smoke `r2-30ep-5df677df@example.com`.
- **COMPLETED dalam 181,3 detik** (23:27:34–23:30:35 WIB 20 Nov), LLM nyata via key trial Nvidia di `.env` lokal (nilai tidak pernah dicetak).
- Hitungan diverifikasi 2x (via API saat berjalan + via SQLite pasca VM swap): **series bible 1, karakter 5, lokasi 4, episode 30, prompt 30**.
- POST create kembali 0,08 dtk (status running); progres per langkah terlihat di polling: bible ~40 dtk, characters ~40 dtk, locations ~20 dtk, episodes cepat (reuse plan bible), prompts ~80 dtk (3 batch).
- Catatan teknis: UUID tersimpan di SQLite TANPA hyphen (32-char hex) — query DB harus pakai bentuk tanpa hyphen.
- Satu job FAILED lama di DB (`7a35c872…`, 06:32 WIB): "Step characters failed: LLM call failed: All AI providers failed" — error LLM transien, bukan bug locking.

### 1b. Login Google asli + submit Flow — NOT VERIFIED (keputusan sadar)

Yang dicoba, dengan bukti:

- Egress VM kini tembus ke Google: `curl https://accounts.google.com/` → **302** ke `ServiceLogin` (bukan 502/503 seperti 19 Nov). `myaccount.google.com` juga 302.
- Probe Playwright via relay CONNECT lokal buatan sendiri (chaining ke egress proxy dari env `HTTPS_PROXY`; token proxy TIDAK pernah dicetak): Chromium sampai ke **halaman sign-in Google asli, HTTP 200**, URL `accounts.google.com/v3/signin/identifier?...flowName=WebLiteSignIn...`, title "Sign in - Google Accounts", form "Email or phone" + tombol Next ter-render.
- Bukti: `FUTURE-DEV-ROUND2-evidence-google-signin.png` (30.157 B).

Kredensial asli **TIDAK dimasukkan** (email pun tidak), tiga lapis alasan:

1. Gate tugas sendiri — "hanya bila jalurnya aman": jalur ini butuh `--ignore-certificate-errors` + proxy egress yang MITM TLS, jadi password akan transit di infrastruktur yang terminasi TLS.
2. Bukti 19 Nov (kaki Hermes, akun palsu): Google men-challenge login otomatis dari VM ini (`browser_challenge` — minta verifikasi tambahan); hampir pasti sama untuk akun asli dan bisa menandai akun Di.
3. Secara teknis, nilai login Secure Vault tidak bisa diekstrak sebagai teks untuk disuntik ke skrip Playwright (by design — hanya bisa dipakai via browser task dengan referensi, yang tidak dimiliki subagent).

Akibatnya **submit Flow end-to-end juga NOT VERIFIED** (bergantung pada login). Video Flow tetap tidak di-generate (sesuai larangan tugas; video tetap manual di Google Flow).

Yang dibutuhkan agar item ini bisa selesai: login dilakukan Di sendiri di browser asli / mesin yang mencapai Google tanpa MITM, atau jalur browser task dengan kredensial Secure Vault. Bukan dari VM ini.

---

## 2. Click-through browser (Playwright) — SELESAI, 13/14 + 1 temuan diperbaiki

Server: backend `127.0.0.1:8003`, frontend `http://localhost:3000` (port 3000 WAJIB — `CORS_ORIGINS` default hanya `localhost:3000`; percobaan di port 3002 gagal preflight 400, bukan bug produk).

Jalur klik: `/register` → dashboard → `/dashboard/projects` → "New Project" → kartu proyek → tombol Sparkles "Auto-Generate" → modal → validasi judul spasi → Episodes=3 → Start → overlay-click saat running → tunggu selesai → Done → dashboard → Characters → Episodes.

| # | Langkah | Hasil |
|---|---|---|
| 1 | Register via UI → redirect dashboard | OK |
| 2 | Dashboard stats user baru | OK |
| 3 | Create project via UI ("Clickthrough Test") | OK |
| 4 | Buka modal Auto-Generate | OK |
| 5 | Judul hanya-spasi → hint "Title cannot be blank." + Start disabled | OK |
| 6 | Judul dipulihkan | OK |
| 7 | Start → tampilan job muncul | OK |
| 8 | Klik overlay saat running TIDAK menutup modal | OK |
| 9 | Job selesai di modal ("All 5 steps completed.") | OK |
| 10 | Ringkasan per langkah tampil | OK (bible: "Planned 3 episodes"; characters 5; locations 4; episodes 3; prompts 3) |
| 11 | Done menutup modal | OK |
| 12 | Dashboard stats sesudah job | OK — Projects 1, Characters 5, Locations 4, Episodes 3 (screenshot 12) |
| 13 | Halaman Characters menampilkan cast | **FAIL → temuan, diperbaiki (lihat bawah)** |
| 14 | Halaman Episodes menampilkan episode | OK di log awal — **KOREKSI: hasil palsu** (lihat bawah) |

Bukti: `FUTURE-DEV-ROUND2-evidence-clickthrough/` — `01-register-filled.png` … `14-episodes-page.png` + `steps.json` (user `r2-ct-6470e49a@example.com`, job 3 episode `16c5f756…` COMPLETED; job percobaan pertama yang skripnya mati di tengah jalan, `7e476b8d…`, juga COMPLETED sendiri di server).

### Temuan: halaman hasil menampilkan "No projects yet" saat load langsung

Screenshot 13 (Characters) dan 14 (Episodes) sama-sama menampilkan **"No projects yet / Create a project first…"** padahal proyek + data ada (dashboard stats membuktikannya). Akar masalah (dari kode):

- Halaman Characters/Episodes/Locations/dll. membaca daftar proyek dari Zustand store tapi **tidak pernah memanggil `fetchProjects()` sendiri**.
- Store di-persist ke localStorage (`project-storage`) tapi `partialize` hanya menyimpan `currentProject` — daftar `projects` HILANG saat full page load / refresh / kunjungan URL langsung → `projects.length === 0` → blok "No projects yet".
- Jalur yang berfungsi selama ini hanya navigasi client-side (dari Dashboard/Projects, store masih berisi daftar). Tautan "Results are ready" di modal adalah `<Link>` client-side, jadi dari modal tetap berfungsi — yang rusak hanya refresh / URL langsung / bookmark.

Koreksi atas log awal: langkah 14 tercatat OK karena asersi skrip (`"episode" in body.lower()`) lolos dari teks salinan halaman ("Manage your 20-episode series"), bukan dari baris episode. Kedua halaman sama-sama rusak; asersi itu salah, bukan produknya.

### Perbaikan (tambahan dari temuan click-through)

`frontend/src/components/layout/DashboardLayout.tsx` — layout ini membungkus SEMUA halaman dashboard, jadi satu tempat memperbaiki semua halaman hasil:

- `fetchProjects()` dipanggil di `useEffect` saat layout mount (aksi store stabil, tidak loop). Daftar selalu segar dari API, tanpa risiko data basi dari persist.
- `tsc --noEmit` 0 error + `npm run build` OK sesudah perbaikan; frontend di-restart ke build baru.

### Re-check sesudah perbaikan — 4/4 OK

Skrip `/tmp/r2-recheck.py` (tidak disimpan di workspace — skrip sekali pakai): login sebagai user click-through, lalu `page.goto` LANGSUNG ke `/dashboard/characters` dan `/dashboard/episodes` (full load):

- Characters: nama karakter pertama dari API (`Raka Pratama`) tampil di halaman, "No projects yet" hilang.
- Episodes: judul episode pertama dari API (`Topeng Pertama`) tampil, "No projects yet" hilang.
- Bukti: `FUTURE-DEV-ROUND2-evidence-clickthrough/recheck-fix/` (`characters-direct.png`, `episodes-direct.png`, `steps.json`).

Catatan lama yang tetap berlaku: kaki Claude TIDAK punya halaman detail proyek (tautan "Open Project" → 404) — sudah diketahui sejak ronde 1, bukan temuan baru.

---

## 3. Security hardening — SELESAI

Semua di `claude/backend/`.

### File baru / diubah

- `app/core/middleware.py` (baru): `RateLimiter` sliding-window in-memory per IP+endpoint — hanya `/api/auth/login|register|refresh` (limit dibaca dari settings per request agar bisa di-monkeypatch tes); `RateLimitMiddleware` (429 + header `Retry-After`); `SecurityHeadersMiddleware` (X-Content-Type-Options nosniff, X-Frame-Options DENY, CSP `default-src 'none'; frame-ancestors 'none'; base-uri 'none'`, Referrer-Policy, Permissions-Policy; HSTS hanya bila `ENVIRONMENT=production`).
- `app/core/secrets.py` (baru): `validate_secrets()` — production MENOLAK start bila SECRET_KEY <32 karakter / placeholder / ENCRYPTION_KEY bukan Fernet key valid (RuntimeError); development hanya warning. `is_valid_fernet_key()`.
- `app/core/config.py`: `RATE_LIMIT_ENABLED`, `RATE_LIMIT_WINDOW_SECONDS=60`, `RATE_LIMIT_LOGIN_PER_MINUTE=60`, `RATE_LIMIT_REGISTER_PER_MINUTE=60`, `RATE_LIMIT_REFRESH_PER_MINUTE=120`.
- `app/core/security.py`: JWT kini bawa `jti` (uuid4) di access+refresh; `get_encryption_key()` diperbaiki — Fernet key asli dipakai verbatim (kode lama memotong ke 32 karakter lalu re-encode, diam-diam menghasilkan key BERBEDA); fallback derivasi lama dipertahankan untuk kompatibilitas dev; `is_token_revoked()` + `revoke_token()` (return bool, hapus baris kedaluwarsa oportunistik).
- `app/models/revoked_token.py` (baru) + export di `app/models/__init__.py`.
- `app/api/auth.py`: `get_current_user_id` + `/auth/refresh` menolak token ter-revoke (401 "Token has been revoked"); endpoint baru `POST /api/auth/logout` (revoke access dari header + refresh dari body, idempotent, return `{"detail": "Logged out", "revoked": N}`).
- `app/main.py`: lifespan memanggil `validate_secrets()` sebelum `init_db()`; middleware terdaftar (RateLimit lalu SecurityHeaders agar 429 pun dapat header).

### Verifikasi live

- `ENVIRONMENT=production` + `.env` lama (placeholder) → startup **GAGAL, exit 3**, pesan: "Refusing to start with weak secrets in production: SECRET_KEY is a known placeholder value; ENCRYPTION_KEY is missing or not a valid Fernet key…".
- Secret kuat dipasang ke `backend/.env` (SECRET_KEY 64 karakter, ENCRYPTION_KEY 44 karakter Fernet valid — nilai TIDAK pernah dicetak, hanya panjang diverifikasi; `.env` mode 600, 3 baris: NVIDIA_API_KEY + 2 secret baru).
- Production + secret kuat → `/health` 200 + header HSTS + X-Frame-Options + nosniff. Cek ulang pasca VM swap (mode development): header nosniff / DENY / CSP / Referrer-Policy / Permissions-Policy hadir di `/health` (HSTS absen — benar, hanya production).
- **Konsekuensi:** password Google terenkripsi lama di `micro_drama.db` (akun tes palsu saja) kini tidak bisa di-decrypt karena ENCRYPTION_KEY berubah — akun tes itu harus dibuat ulang bila dipakai lagi.

### Sisa isu keamanan (sengaja tidak diubah)

- Endpoint `GET /google-accounts/{id}/tokens` masih mengembalikan token+password plaintext (frontend tidak pakai). **SENGAJA TIDAK dihapus** — Di belum memutuskan. Keputusan menunggu Di.
- Rate limiter per-proses (in-memory); multi-worker butuh Redis (`REDIS_URL` sudah ada di settings) — didokumentasikan di kode.

---

## 4. Multi-worker safe job execution — SELESAI

Semua di `claude/backend/`.

### Perubahan

- `app/models/auto_generate.py`: kolom baru `locked_by` (String 64), `locked_at`, `lease_expires_at` (index) di `AutoGenerateJob`.
- `alembic/versions/c41d8e2a90f7_revoked_tokens_and_job_locks.py` (baru, down_revision `a7c3e9f1b824` = head lama): tabel `revoked_tokens` + 3 kolom lock. **Migrasi sudah teraplikasi ke live DB** (`alembic_version` = `c41d8e2a90f7`, terverifikasi pasca VM swap).
- `app/api/auto_generate.py`:
  - `WORKER_ID` per proses (uuid hex); `LEASE_SECONDS=600` (harus melebihi langkah terpanjang ~1–2 mnt karena SQLite single-writer — renewal antar-langkah, bukan mid-step).
  - `claim_job()`: satu UPDATE atomik — job RUNNING + lease kedaluwarsa/belum ada + NOT EXISTS job lain proyek sama pegang lock live. Pola ini diuji dulu di SQLite mentah: claim kedua = 0 baris, setelah expiry = 1.
  - `renew_lease()` (hanya owner), `release_job()` (hanya owner).
  - `_run_from()` terima `worker_id`, renew lease sebelum tiap langkah.
  - `_run_job_in_background()` claim dulu — bila kalah claim: (a) job ini sendiri sudah di-lock live → diam (runner lain yang punya); (b) job lain proyek sama pegang lock → job ini FAILED dengan pesan "Another auto-generate job is already running for this project — retry after it finishes" (tidak stuck RUNNING); job terminal tidak pernah di-clobber.
  - `_mark_interrupted_jobs_failed()` kini hanya fail job RUNNING yang lease-nya kedaluwarsa/belum ada (live lease dibiarkan — aman multi-worker).
  - Endpoint create: **409** bila ada job RUNNING lain untuk proyek sama dengan live lease. Retry: double-retry aman via claim (satu menang).
  - Helper `_aware()` untuk banding datetime naive dari SQLite.
- Sisa race yang jujur didokumentasikan: dua POST create yang benar-benar simultan (milidetik yang sama, sebelum commit) masih bisa lolos guard — claim atomik tetap mencegah eksekusi ganda, tapi job yang kalah di-FAILED (bukan duplikasi data). Episode sudah dilindungi unique index `(project_id, episode_number)`; karakter/lokasi tanpa unique index nama (sengaja TIDAK ditambah — risiko migrasi gagal bila data lama ada duplikat).

### Tes baru

- `tests/test_security_round2.py` (14 tes): validasi secret prod/dev, Fernet verbatim, rate limit login/register/disable, logout revoke kedua token + idempotent + access-only, token tanpa jti tetap jalan, security headers.
- `tests/test_job_locking.py` (8 tes): claim/release/renew unit, takeover pasca-expiry, eksklusif per proyek, double-runner 1x eksekusi (= 4 LLM call), concurrent retry 1x (= 5 call total), create 409, loser job FAILED bersih, sweep hanya fail stale.
- Pola mock LLM diambil dari `tests/test_auto_generate.py` (`_fake_llm_ok` dkk.; endpoint episodes/prompts paginasi `["total"]`, characters/locations list polos).

---

## Hasil tes

```text
venv/bin/python -m pytest tests/test_auth.py tests/test_auto_generate.py \
  tests/test_browser_login.py tests/test_characters_locations.py tests/test_config.py \
  tests/test_dashboard_stats.py tests/test_fix_round2.py tests/test_google_fallback.py \
  tests/test_new_routers.py tests/test_projects.py tests/test_security_round2.py \
  tests/test_job_locking.py -q -p no:warnings
→ 135 passed dalam 311,67 dtk (12 file tes, termasuk 2 file baru)
```

Frontend (2x — sebelum & sesudah perbaikan `DashboardLayout`):

```text
npx tsc --noEmit          → 0 error
NEXT_PUBLIC_API_URL=http://localhost:8003 npm run build → OK, 17 route
```

Catatan: pytest terakhir dijalankan SEBELUM perbaikan layout; perbaikan itu hanya menyentuh frontend (1 file), dan sesudahnya tsc + build diulang 0 error / OK + re-check Playwright 4/4.

---

## File diubah (ronde 2)

Backend (`claude/backend/`): `app/core/middleware.py` (baru), `app/core/secrets.py` (baru),
`app/core/config.py`, `app/core/security.py`, `app/models/revoked_token.py` (baru),
`app/models/__init__.py`, `app/models/auto_generate.py`, `app/api/auth.py`,
`app/api/auto_generate.py`, `app/main.py`,
`alembic/versions/c41d8e2a90f7_revoked_tokens_and_job_locks.py` (baru),
`tests/test_security_round2.py` (baru), `tests/test_job_locking.py` (baru).

Frontend (`claude/frontend/`): `src/components/layout/DashboardLayout.tsx` (fetch proyek saat mount — temuan click-through).

Tidak diubah: `.env` TIDAK di-commit (ter-ignore git); tidak ada push GitHub.

## Insiden selama ronde 2

- VM/container diganti 20 Nov ~23:35 WIB di tengah verifikasi: semua proses mati, `/tmp` terhapus total (skrip smoke/relay/probe/click-through, log, screenshot `/tmp` hilang). Yang selamat: semua file workspace (kode, `.env`, `micro_drama.db`, screenshot bukti Google). Server di-restart pasca-swap: backend 8003 (`PORT=8003 bash backend/start.sh`, CWD-independen) + frontend 3000 (`npx next start -p 3000`); `/health` 200.
- Skrip click-through pertama mati karena bug skrip sendiri (`get_by_text(..., timeout=...)` tidak valid — diperbaiki jadi `.wait_for(timeout=...)`); job-nya tetap selesai di server (COMPLETED). Skrip di `/tmp` ditulis ulang 2x karena swap.
- `pkill -f 'next-server'` sempat membunuh shell sendiri (self-match — pola ada di command). Restart frontend akhirnya via kill PID eksplisit (1810).

## NOT VERIFIED + keputusan menunggu Di

1. **Login Google asli + submit Flow end-to-end** — butuh browser asli / mesin tanpa MITM, atau browser task dengan kredensial Secure Vault. Bukan dari VM ini.
2. **Klik manual UI oleh manusia** — click-through di sini dilakukan Playwright (headless Chromium), bukan tangan Di. Fungsional sama, tapi "klik manual Di" tetap belum.
3. **Endpoint `GET /google-accounts/{id}/tokens` (plaintext)** — hapus atau pertahankan? Menunggu keputusan Di.
4. **Key trial Nvidia** (di `.env` lokal ketiga kaki) — Di bilang akan hapus/cabut sendiri; belum ada konfirmasi. Ingatkan lagi.
5. **Rate limiter per-proses** — bila benar-benar multi-worker, perlu Redis. Bukan blocker untuk single-worker saat ini.
6. Sisa dari ronde sebelumnya (tetap): job 30 episode live kini SELESAI; keamanan inti selesai; yang masih terbuka: login Google asli, video Flow asli, job 30 episode via UI (job 30 episode di sini via API, bukan via klik modal — modal diuji dengan 3 episode).

## Server smoke yang masih jalan

Backend `127.0.0.1:8003` + frontend `localhost:3000` (build baru, sudah termasuk perbaikan layout). Dibiarkan jalan — mati sendiri saat VM swap berikutnya; matikan manual bila tidak diperlukan.
