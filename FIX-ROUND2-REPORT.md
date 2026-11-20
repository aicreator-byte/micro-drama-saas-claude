# FIX-ROUND2-REPORT — kaki Claude

**Tanggal:** 20 Nov 2026
**Laporan audit:** `audit-3way-round2-claude/AUDIT-REPORT.md` (Part 4 + Part 8, temuan kaki Claude)
**Scope:** hanya `~/workspace/micro-drama-saas/claude/`. Tanpa push GitHub.

## Ringkasan

| Item | Status |
|---|---|
| P1-1 endpoint `GET /google-accounts/{id}/tokens` (plaintext) | **NOT FIXED — menunggu keputusan Di** (sengaja tidak diubah) |
| P1-2 login Google asli + submit Flow | **NOT FIXED — butuh browser Di** (tidak bisa dari VM) |
| Rate limiter per-proses → dukung Redis | **FIXED** |
| Race nano-detik create simultan | **FIXED** (diperkecil ke jendela antar-SELECT; loser 409 + row dihapus) |
| "Open Project" → 404 | **FIXED** (halaman detail proyek baru) |
| Password Google tes lama tak bisa di-decrypt | **FIXED** (2 field dibersihkan di DB live) |
| Server smoke dibiarkan jalan | **FIXED** (PID 1790 + 4262 dimatikan, port bebas) |

**Verifikasi:** pytest **142 passed** (135 ronde 2 + 7 tes baru), `tsc` 0, `npm run build` OK (18 route, termasuk `/dashboard/projects/[id]` baru).

---

## 1. NOT FIXED — P1-1: endpoint `/tokens` plaintext

`GET /google-accounts/{id}/tokens` (`backend/app/api/google_accounts.py:648-651`)
mengembalikan access_token + refresh_token + password Google hasil dekripsi.
**Sengaja TIDAK dihapus/diubah** — perintah tugas: menunggu keputusan Di.
Tidak ada file yang menyentuh endpoint ini.

## 2. NOT FIXED — P1-2: login Google asli + submit Flow

Keputusan sadar ronde 2 (lihat `FUTURE-DEV-ROUND2-REPORT.md`): probe Playwright
via relay sampai ke halaman sign-in Google asli, tapi kredensial TIDAK dimasukkan
(butuh `--ignore-certificate-errors` + proxy MITM TLS; bukti 19 Nov Google
men-challenge login otomatis dari VM; nilai Secure Vault tak bisa diekstrak
sebagai teks untuk Playwright). Submit Flow ikut NOT VERIFIED. Butuh browser
asli Di atau browser task. Tidak ada yang bisa diperbaiki dari VM untuk ini.

---

## 3. FIXED — Rate limiter dukung Redis (`backend/app/core/middleware.py`, `backend/app/core/config.py`)

**Sebelumnya:** limiter in-memory per proses; tiap worker uvicorn punya budget
sendiri. `REDIS_URL` ada di settings tapi tidak dipakai.

**Perbaikan:**
- Setting baru `RATE_LIMIT_USE_REDIS: bool = False` (default off — perilaku lama
  tidak berubah bila tidak dikonfigurasi).
- `RedisRateLimiter`: sliding window via satu script Lua atomik
  (`ZREMRANGEBYSCORE` + `ZCARD` + `ZADD` + `EXPIRE`), key `ratelimit:<ip>:<path>`,
  mengembalikan `[allowed, retry_after]`.
- `_allow()`: bila `RATE_LIMIT_USE_REDIS` True, coba Redis dulu; **kegagalan
  Redis apa pun → fallback ke limiter in-memory** (log warning), tidak pernah 500
  dan tidak pernah tanpa limit. Client Redis dibuat lazy dari `REDIS_URL`
  (`redis.asyncio`, timeout 0,5 dtk); `reset_rate_limit_redis()` untuk tes.
- `redis==5.0.7` sudah ada di `requirements.txt` + terinstal di venv — tanpa
  dependensi baru.

**Tes baru (`tests/test_security_round2.py`, 3 tes):**
- `test_redis_rate_limit_enforced` — fake Redis: login ke-3 → 429, `Retry-After: 7`.
- `test_redis_failure_falls_back_to_memory` — fake Redis raise ConnectionError:
  request tidak 500, limiter in-memory tetap menegakkan 429.
- `test_redis_live_roundtrip` — redis-server asli di port scratch 6390
  (dinyalakan + dimatikan di dalam tes): 2 login lolos, ke-3 429, key
  `ratelimit:*` terbukti ada di Redis. Skip bila `redis-server` tidak ada.

## 4. FIXED — Race create simultan (`backend/app/api/auto_generate.py`)

**Sebelumnya:** create hanya mengandalkan pre-check SELECT (`live_other` dengan
`lease_expires_at > now`); dua request bersamaan bisa sama-sama lolos, sama-sama
insert job RUNNING, dan yang kalah baru gagal belakangan di background runner
(meninggalkan job FAILED).

**Perbaikan:**
- Create mengklaim lock **di dalam request**, sebelum return 201, via
  `claim_job` yang atomik. Yang kalah → **409 + row job-nya dihapus**
  (steps ikut terhapus via cascade `delete-orphan`), jadi tidak ada job
  RUNNING ganda dan tidak ada sisa FAILED.
- Lock create memakai owner placeholder `"create:<job_id>"`, BUKAN id worker:
  runner job itu boleh mengambil alih placeholder tersebut, sementara
  duplicate runner (task ganda di proses yang sama) tetap terblokir —
  re-claim oleh worker id yang sama dengan lease hidup tetap DITOLAK
  (percobaan pertama saya — izinkan re-claim owner — memecahkan 2 tes
  `test_double_runner_executes_once` / `test_concurrent_retry_runs_once`;
  diperbaiki ke skema placeholder, kedua tes hijau lagi).
- Sisa window yang didokumentasikan: di antara pre-check SELECT kedua request —
  kedua row sempat ter-insert, tapi hanya satu yang bisa memegang lock atau
  jalan, dan yang kalah dihapus sebelum respons. Tidak ada lagi window di
  mana dua job RUNNING terlihat oleh klien.

**Tes baru (`tests/test_job_locking.py`, 2 tes):**
- `test_claim_create_lock_takeover` — placeholder bisa diambil alih runner
  job itu; re-claim owner sama dan worker lain ditolak.
- `test_simultaneous_create_one_wins` — dua POST bersamaan via
  `asyncio.gather`: status `{201, 409}`, tepat 1 row job di DB, pemenang
  COMPLETED normal.

## 5. FIXED — "Open Project" → 404 (`frontend/src/app/dashboard/projects/[id]/page.tsx`, baru)

**Sebelumnya:** tautan "Open Project" di dashboard + halaman projects menuju
`/dashboard/projects/${id}`, tapi rute itu tidak ada (hanya `page.tsx` list) —
setiap klik 404. Bug pre-existing sejak Fase 2.

**Perbaikan:** halaman detail proyek baru — fetch `projectApi.get(id)`, set
sebagai `currentProject` di store (supaya sub-halaman yang mengandalkan
currentProject jalan), tampilkan judul/deskripsi/genre/status + tombol
Auto-Generate (modal yang sama) + grid 12 kartu menuju sub-halaman yang sudah
ada (series-bible, characters, locations, episodes, scenes, dialogues,
prompts, story, flow, assets, google-accounts, settings) + halaman "not found"
yang rapi bila proyek tidak ada/tidak dapat diakses.

**Verifikasi:** `tsc --noEmit` 0 error; `npm run build` OK — rute
`ƒ /dashboard/projects/[id]` muncul di daftar (18 route, sebelumnya 17).
Klik manual di browser nyata belum dilakukan (di luar scope subagent ini).

## 6. FIXED — Password Google tes lama tak bisa di-decrypt (data live)

**Temuan:** 2 akun tes di `claude/backend/micro_drama.db` (dari uji fallback
19 Nov: `tes-fallback-a-20261119@gmail.com`, `tes-fallback-b-20261119@gmail.com`)
menyimpan `password_encrypted` hasil derivasi kunci lama (truncate 32 char);
setelah perbaikan Fernet ronde 2 (key dipakai verbatim), keduanya gagal
`decrypt_data` → `InvalidToken`. Semua user di DB ini adalah akun tes
(`fallback-test@`, `r2-*`, `smoke-*`, `test*`); tidak ada akun asli Di di DB ini.

**Perbaikan:**
- `cleanup_undecryptable_credentials(db)` baru di
  `app/services/google_account_service.py`: coba dekripsi tiap field
  (`password`/`access_token`/`refresh_token`) semua akun; yang gagal
  di-set NULL; yang bagus disentuh pun tidak. Commit hanya bila ada
  yang dibersihkan; kembalikan hitungan per tipe.
- Skrip one-off `backend/scripts/cleanup_undecryptable_credentials.py`
  (aman di-run ulang) — **sudah dijalankan ke DB live**: cleared
  `{'password': 2, 'access_token': 0, 'refresh_token': 0}`; kedua akun
  kini `password_encrypted: None`, akun tetap ada dan bisa dipakai ulang
  (password diisi ulang / akun di-link ulang bila perlu).
- Backup DB sebelum cleanup: `backend/micro_drama.db.bak-20261120-fix-round2`
  (hanya ciphertext, bukan plaintext).

**Tes baru (`tests/test_fix_round2.py`, 2 tes):**
- `test_clears_bad_ciphertext_keeps_good` — row ciphertext rusak dibersihkan,
  row bagus (password + access token terenkripsi benar) utuh.
- `test_cleanup_noop_when_nothing_broken` — tanpa data rusak, hasil nol semua.

## 7. FIXED — Server smoke sisa ronde 2 dimatikan

Server smoke ronde 2 masih jalan sejak 19 Nov: uvicorn PID 1790 (port 8003)
+ next-server PID 4262 (port 3000). Dimatikan via `kill` PID eksplisit
(tanpa `pkill -f`, menghindari self-match); terverifikasi `ss`:
port 8003/3000 bebas. Tidak ada server yang saya nyalakan selama perbaikan
ini yang tertinggal (tes memakai TestClient in-process; tes Redis live
mematikan redis-server scratch port 6390 di `finally` — terverifikasi tidak
ada proses `uvicorn`/`next-server`/`redis-server` tersisa).

---

## Verifikasi akhir

- `venv/bin/python -m pytest tests/ -q -p no:cacheprovider` → **142 passed**
  (135 ronde 2 + 7 baru: 2 locking + 3 security/Redis + 2 cleanup), 0 failed.
- `npx tsc --noEmit` → 0 error.
- `npm run build` (setelah `rm -rf .next`) → OK, 18 route.
- Scan: tidak ada nilai key/password yang dicetak/ditulis di laporan ini;
  `.env` tidak disentuh; endpoint `/tokens` tidak disentuh; kaki lain
  tidak disentuh; tanpa push GitHub.

## Sisa / menunggu Di

- P1-1 endpoint `/tokens`: hapus atau biarkan — keputusan Di.
- P1-2 login Google asli + submit Flow: butuh browser asli Di / browser task.
- Rate limiter Redis: aktif hanya bila `RATE_LIMIT_USE_REDIS=true` + `REDIS_URL`
  menunjuk Redis yang jalan; default tetap in-memory (per proses).
- Race create: jendela antar-SELECT didokumentasikan di atas (tidak bisa nol
  tanpa lock DB global; yang dijamin: tidak pernah dua job RUNNING, loser
  selalu 409 + row dihapus).


---

## Tambahan 20 Nov 2026 — P1-1 SELESAI: endpoint `GET /google-accounts/{id}/tokens` DIHAPUS

Perintah Di 20 Nov 08:38: hapus endpoint ini.

### Yang dihapus

- `backend/app/api/google_accounts.py` — fungsi `get_account_tokens` utuh (route `@router.get("/{account_id}/tokens")`, dulu baris 628–652), yang mengembalikan `access_token` + `refresh_token` + `password` plaintext. File kini 625 baris, berakhir di endpoint `browser-session`.
- Import `decrypt_data` di file yang sama dihapus (hanya dipakai endpoint itu; tidak ada pemakaian lain di file).
- `backend/app/services/google_account_service.py` — docstring diperbarui: dulu menyebut endpoint "intentionally left untouched (separate Di decision)", kini menyatakan endpoint sudah dihapus atas perintah Di 20 Nov 2026.

### Pengecekan referensi (sebelum hapus)

- `grep get_account_tokens` / `/tokens` di `backend/` + `frontend/`: **tidak ada pemanggil** — tidak ada tes, tidak ada kode frontend, tidak ada pemakaian internal yang memakai endpoint ini. Frontend hanya menyebut "tokens" untuk JWT auth-store (`access_token`/`refresh_token` login) dan `tokens_used` — keduanya endpoint auth yang sah dan TIDAK disentuh.
- Endpoint auth lain yang sah tetap ada: `POST /api/auth/refresh`, `POST /api/auth/revoke` (terlihat di `/openapi.json` server smoke), JWT `jti` + tabel `revoked_tokens` tidak disentuh.
- Laporan lama (`FIX-REPORT.md`, `PHASE2-REPORT.md`, `GOOGLE-FALLBACK-REPORT.md`, `BROWSER-LOGIN-REPORT.md`, `FUTURE-DEV-ROUND2-REPORT.md`) menyebut endpoint ini sebagai catatan historis — TIDAK diubah.

### Verifikasi

- `venv/bin/python -m pytest tests/ -q -p no:cacheprovider` → **141 passed, 1 skipped, 0 failed** (161 dtk). Skip satu-satunya: `tests/test_security_round2.py:338` — "redis-server not installed" (binary redis-server tidak ada di container ini; tidak terkait perubahan — sebelumnya 142 passed saat redis-server tersedia).
- `npx tsc --noEmit` → 0 error.
- Smoke live server scratch (port 8141, DB scratch `/tmp/tokens-smoke.db`, dimatikan + file dihapus sesudahnya): `/health` 200; `/openapi.json` tidak lagi memuat route `/google-accounts/{id}/tokens` (hanya `/api/auth/refresh` + `/api/auth/revoke` yang mengandung kata "token"); `GET /api/google-accounts/<uuid>/tokens` tanpa auth → **404** (kontrol: `GET .../browser-session` tanpa auth → 401, membuktikan server hidup dan route tetangga masih ada).
- Tidak sentuh kaki lain, tidak push GitHub, tidak ada nilai key/password dicetak, tidak pakai akun Google asli.

### Sisa

- P1-2 login Google asli + submit Flow: tetap NOT VERIFIED (butuh browser asli Di / browser task).
