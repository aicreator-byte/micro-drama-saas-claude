# FIX-REPORT — Kaki Claude pasca-Audit 3-Arah Ronde 2

**Tanggal:** 17 November 2026
**Cakupan:** hanya `~/workspace/micro-drama-saas/claude/` (kaki hermes/opencode dan folder audit tidak disentuh).
**Sumber perbaikan:** `audit-3way-round2/SUMMARY.md` (§5.10, 5.11, 5.12, 5.16, 5.18, §6, §7) + Action Plan P0/P1 untuk Claude di PART-9-10-11 ketiga laporan (`audit-3way-round2-{hermes,opencode,claude}/PART-9-10-11.md`).
**Perintah Di yang dipatuhi:** fungsional P0/P1 saja; security DITUNDA; jangan push ke GitHub; jangan kirim data ke layanan luar.
**Catatan file:** laporan ronde 1 yang sebelumnya ada di file ini dipindah ke `FIX-REPORT-ronde1.md` agar tidak hilang.

---

## 1. Yang diperbaiki

### 1.1 Add-character-to-scene 500 — MissingGreenlet (P0, F-H1)
- **File:** `backend/app/api/scenes.py` (`add_character_to_scene`)
- **Penyebab:** `scene.episode.project_id` diakses secara lazy di konteks async → `MissingGreenlet`; lalu `await db.refresh(scene)` + return `scene` tanpa eager-load `characters`.
- **Perbaikan:** pakai `episode.project_id` dari `_verify_episode_access` (sudah ter-load); query scene dengan `selectinload(Scene.episode)`; setelah commit, re-query dengan `selectinload(Scene.characters).selectinload(SceneCharacter.character)` sebelum return (pola sama seperti handler scene lain).
- **Bukti:** pytest `TestAddCharacterToScene` (tambah → 200 + 1 karakter terdaftar; tambah ganda → 400; karakter proyek lain → 400); smoke live: `POST /scenes/{ep}/{scene}/characters` → **200**, scene berisi 1 karakter.

### 1.2 UUID malformed → 400, bukan 500 (P0/P1, F-H3)
- **File:** `backend/app/main.py`
- **Perbaikan:** exception handler global `ValueError → 400` (`{"detail": "Invalid value: ..."}`). Menangkap semua `uuid.UUID(...)` tanpa try/except di seluruh router sekaligus, tanpa mengubah tiap router.
- **Bukti:** pytest `TestMalformedUuid` (7 path + scene-characters → 400); smoke live: `GET /api/projects/not-a-uuid` → **400**, `GET /api/prompts/not-a-uuid` → **400**.

### 1.3 Settings/OAuth UI tersambung ke backend (P0/P1, F-H5/F-H6/F-M11)
- **File:** `frontend/src/app/dashboard/settings/page.tsx` (tulis ulang), `frontend/src/lib/api.ts`
- **Sebelumnya:** halaman Settings mockup — tab profile/security/account menampilkan "sukses" palsu tanpa API call; tidak ada satu pun pemanggilan `/api/settings` dari frontend.
- **Perbaikan:**
  - Tab baru **AI Providers**: `GET /api/settings` saat load; daftar provider (model, enabled, priority, badge `key_configured`/`Key missing`) + `PATCH /api/settings` saat Save.
  - Tab baru **Google OAuth**: form `client_id`/`client_secret` → `PATCH /api/settings`; badge configured/not-configured; catatan kredensial tersimpan terenkripsi dan tidak pernah dikembalikan API.
  - Tab Profile: hanya tampil (read-only) + keterangan jujur bahwa belum ada endpoint update profil.
  - Tab Security: form ganti password **dinonaktifkan** + keterangan jujur belum ada endpoint backend — tidak ada lagi sukses palsu.
  - Tab Account: Delete Account tetap alert jujur (belum ada endpoint).
  - `frontend/src/lib/api.ts`: tambah `settingsApi.get/update`; hapus `getTokens()` (tidak dipakai halaman mana pun).
- **Bukti:** `npm run build` lolos (halaman `/dashboard/settings` ter-generate); halaman serve **200** via `next start`; bundle hasil build mengandung pemanggilan settings + field `google_oauth_client_id`. Klik-through di browser tidak dijalankan dari subagent ini (tidak ada live browser) — verifikasi klik manual masih perlu dari parent/Di.

### 1.4 OAuth callback: state salah → 400, transport error → 502 (P0, F-H2/F-H5)
- **File:** `backend/app/api/google_accounts.py`, `frontend/src/app/dashboard/google-accounts/page.tsx`
- **Backend:** `httpx` di callback dibungkus helper `_http_post_json`/`_http_get_json` → `httpx.HTTPError` jadi **502** ("Could not reach Google"), bukan 500. State diverifikasi dari DB (lihat 1.5) dan `redirect_uri` yang dipakai saat tukar code adalah yang disimpan saat `/oauth/start` (sebelumnya hardcode, bisa beda).
- **Frontend:** `handleStartOAuth` menyimpan `state` dari respons `/oauth/start`; callback memakai form (input authorization code + state terisi otomatis, read-only) — `prompt()` dan `state: user?.id` dihapus.
- **Bukti:** pytest `test_callback_bad_state_400` (→ 400) dan `test_callback_transport_error_502` (httpx di-mock `ConnectError` → 502); smoke live: state salah → **400**; state benar + Google tak terjangkau (proxy VM: `SSL CERTIFICATE_VERIFY_FAILED`) → **502**, dan baris state terhapus dari DB (single-use terverifikasi: `oauth_states` = 0 baris setelah callback).

### 1.5 State OAuth pindah ke DB (P1-19, F-M6)
- **File baru:** `backend/app/models/oauth_state.py`, `backend/alembic/versions/b3f8a1c9d204_oauth_states.py` (revisi baru, `down_revision = 96117fdda23d`); `backend/app/models/__init__.py`; `backend/tests/conftest.py` (impor model agar `create_all` mencakupnya).
- **Perbaikan:** state OAuth tidak lagi di dict in-memory (hilang tiap restart, rusak multi-worker) — kini tabel `oauth_states`: state acak, `user_id`, `redirect_uri`, TTL 10 menit, dihapus saat dipakai (single-use) + bersih-bersih state kedaluwarsa.
- **Bukti:** migrasi jalan di DB segar smoke (`alembic_version = b3f8a1c9d204`, tabel `oauth_states` ada); pytest 68/68 lolos.
- **Catatan:** migrasi ini BARU dan nyata (tabel baru) — bukan migrasi `c758af...` yang diklaim PHASE2-REPORT (lihat §3.3).

### 1.6 POST /prompts/generate → 500 KeyError: 'name' (P0, §6)
- **File:** `backend/app/api/prompts.py`
- **Penyebab:** template `CHARACTER_IMAGE`/`LOCATION_IMAGE` memakai `{name}` tapi `format()` hanya diberi `description`.
- **Perbaikan:** `{name}` di-resolve dari karakter/lokasi bila `character_id`/`location_id` diberikan (fallback = context). Semua 10 `PromptType` kini memanggil `template.format(name=..., description=...)`.
- **Label jujur (P1-16, F-M3):** endpoint ini tetap template (TIDAK memanggil LLM) — baris yang disimpan kini `status="template"`, bukan `"completed"`; UI halaman Prompts diubah: tombol "AI Generate" → "Generate (Template)", submit → "Generate Template", plus catatan bahwa generate mengisi template dan tidak memanggil model AI. Penyambungan ke `ai_client.generate()` TIDAK dilakukan di ronde ini: di lingkungan tes/smoke tidak ada `NVIDIA_API_KEY` valid (conftest memakai key palsu) dan audit mencatat satu tes memanggil Nvidia dengan key palsu menggantung 383 dtk — memanggil LLM dari endpoint ini akan membuat request menggantung/timeout, bukan menjawab.
- **Bukti:** pytest `TestPromptGenerate` (10/10 tipe → 200, status `template`; `character_image` mengandung nama karakter "Nadia"); smoke live: 10/10 tipe → **200**, contoh teks `Character portrait of Nadia, in the rain, high quality, detailed`.

### 1.7 Import Flow → 500 AttributeError double-UUID (P0, §6/F-H8)
- **File:** `backend/app/api/flow_bridge.py` (`import_from_flow`)
- **Penyebab:** `uuid.UUID(import_data.flow_task_id)` padahal `FlowImport.flow_task_id` sudah `uuid.UUID` (Pydantic sudah parse) → `AttributeError`.
- **Perbaikan:** pakai `import_data.flow_task_id` langsung. Plus label jujur (P1-17, F-M4): respons export tambah `"mode": "manual"`; respons deeplink tambah `"verified": false` + catatan format belum terverifikasi terhadap Flow asli; halaman Flow: judul modal → "Manual Export for Google Flow", deeplink unverified menampilkan peringatan sebelum dibuka.
- **Bukti:** pytest `TestFlowImport` (import → 200 `status=imported`; task tak dikenal → 404); smoke live: import → **200**, deeplink → 200 dengan `verified=false`.

### 1.8 Refresh token sebagai objek JSON (P0-18 Hermes, F-H9)
- **File:** `frontend/src/lib/api.ts` (`authApi.refresh`)
- **Penyebab:** frontend mengirim refresh token sebagai raw string → backend (`RefreshTokenRequest`) 422 → sesi mati tiap 30 menit.
- **Perbaikan:** `api.post("/auth/refresh", { refresh_token })`.
- **Bukti:** pytest `TestRefreshTokenObject` (→ 200 + access_token baru); smoke live: refresh objek → **200**.

### 1.9 PATCH scene validasi location_id (P1-09, F-M10)
- **File:** `backend/app/api/scenes.py` (`update_scene`)
- **Perbaikan:** PATCH kini memvalidasi `location_id` ke proyek yang sama (aturan sama seperti saat create) → lokasi proyek lain ditolak 400.
- **Bukti:** pytest `TestScenePatchLocation` (→ 400); smoke live: PATCH lokasi lintas proyek → **400**.

### 1.10 Router Shot CRUD + halaman Story Engine (P1-18, P1-15; F-M5, F-L7)
- **File baru:** `backend/app/api/shots.py`, `backend/app/schemas/shot.py`, `frontend/src/app/dashboard/story/page.tsx`; diubah: `backend/app/main.py` (registrasi router), `frontend/src/components/layout/DashboardLayout.tsx` (link nav "Story Engine").
- **Shot CRUD:** `POST/GET /shots/{scene_id}`, `GET/PATCH/DELETE /shots/{scene_id}/{shot_id}` — model `Shot` sudah ada (tabel `shots`) tapi tanpa API. Akses diverifikasi lewat scene → episode → proyek; `shot_number` unik per scene.
- **Halaman Story Engine:** `/dashboard/story` — pilih proyek + tipe generasi (8 tipe), prompt, generate via `POST /story-engine/generate` (LLM nyata bila key tersedia), riwayat dengan status/error/output + hapus.
- **Bukti:** pytest `TestShotCrud` (CRUD penuh + isolasi tenant 404); build: rute baru `/dashboard/story` ter-generate; serve **200**.

### 1.11 Sudah benar sebelum perbaikan — diverifikasi, tidak diubah
- **Story/Scene task gagal → FAILED (P0-12 Hermes):** `story_engine.py` sudah set `status=FAILED + error_message + completed_at` saat `AIClientError`. Smoke live tanpa key: generate → **201, status=failed**, `error_message="All providers failed: [... API key not found ...]"` — tidak macet `generating`. Tidak ada perubahan kode.

---

## 2. Hasil verifikasi (aktual, bukan kutipan laporan)

### pytest — 68/68 lolos (54 lama + 14 baru)
- Perintah: `cd backend && ./venv/bin/python -m pytest tests/ -q` — **68 passed, 220 warnings (deprecation passlib/bcrypt + `datetime.utcnow`, sudah ada sebelumnya) dalam 113,97 dtk.**
- Tes baru: `backend/tests/test_fix_round2.py` (14 tes: add-character, generate 10 tipe, flow import, UUID 400, OAuth callback 400/502, PATCH scene location, refresh objek, Shot CRUD).
- **Catatan venv:** pytest HARUS dari `backend/venv` (bcrypt 4.1.2). `claude/venv` (bcrypt 5.0.0) merusak passlib 1.7.4 — register gagal (`ValueError: password cannot be longer than 72 bytes`) bahkan sebelum perubahan ini; itu masalah environment venv tersebut, bukan kode. Jangan pakai `claude/venv` untuk tes backend.

### npm run build — 20/20 halaman
- Perintah: `cd frontend && npm run build` — **Compiled successfully, Generating static pages (20/20)**. Rute baru: `/dashboard/story`. (Klaim lama "19/19": 19 halaman sebelum penambahan story page; auditor yang menghitung 17 rute hanya menghitung rute dashboard — total halaman statis memang 19 sebelum ronde ini, 20 sesudahnya.)

### Smoke live — 28/28 lolos
- Backend: DB segar `/tmp/smoke-round2.db`, `DATABASE_URL=sqlite+aiosqlite:////tmp/smoke-round2.db`, uvicorn `127.0.0.1:8103` (server dimatikan lagi setelah smoke). Skrip: `/tmp/smoke-round2.py`.
- Hasil per endpoint (status HTTP aktual): register 201, login 200, refresh objek 200, create project/character/episode/scene 201, add-character-to-scene **200** (bukan 500), prompts/generate 10/10 tipe **200** status `template`, flow import **200** `imported`, deeplink 200 `verified=false`, UUID malformed **400** (×2), GET/PATCH `/settings` **200** tanpa bocor secret, oauth/start **200** + state, callback state salah **400**, callback state benar **502** (transport Google gagal — bukti handler 502 jalan), shot create 201 + list 200, PATCH scene location lintas proyek **400**, story generate 201 `failed` (tanpa key).
- Frontend: `next start -p 3103` — `/dashboard/settings`, `/dashboard/story`, `/dashboard/google-accounts` → **200** (server dimatikan lagi setelah cek).

### NOT VERIFIED (jujur, bukan dikarang)
- **Generasi LLM nyata (story engine / prompts):** `NVIDIA_API_KEY` tidak tersedia di environment ini — story generate mencatat `failed` dengan jujur ("API key not found"). Butuh key valid Di untuk verifikasi end-to-end.
- **Google OAuth end-to-end:** butuh `client_id`/`client_secret` asli Di. Yang terverifikasi: start → URL Google asli + state DB, callback state salah → 400, callback state benar → 502 saat transport gagal (bukan 500).
- **Klik-through UI di browser** (Settings save, OAuth flow lengkap): tidak dijalankan dari subagent ini (tanpa live browser); yang terverifikasi adalah kode + build + serve 200 + bundle mengandung pemanggilan API.

---

## 3. Yang TIDAK diperbaiki + alasan

### 3.1 Security — DITUNDA per perintah Di (dicatat, bukan diperbaiki diam-diam)
- Rate limiting / lockout login, revokasi token (`jti`/deny-list, logout server-side), `SECRET_KEY` + `ENCRYPTION_KEY` (default hardcoded, enkripsi = SHA-256(SECRET_KEY)), token JWT di localStorage (httpOnly cookie), security headers, `verify=False` di AI client, kunci Settings ke superuser (PATCH `/settings` masih bisa dipanggil user biasa mana pun — F-C2).
- Alasan: perintah Di 17 Nov — security ditunda, fungsi jalan dulu. Semua item ini tetap blocker sebelum komersial dan butuh perintah Di tersendiri.

### 3.2 BLOCKER KEAMANAN — `GET /google-accounts/{id}/tokens` mengembalikan kredensial plaintext (F-C1, §5.10)
- **Status: TIDAK DIPERBAIKI, sengaja.** Endpoint `backend/app/api/google_accounts.py:get_account_tokens` masih mengembalikan `access_token` + `refresh_token` + password Google plaintext (live 200) untuk akun milik user yang login. Ini ranah security — sesuai instruksi tugas, tidak diperbaiki diam-diam.
- **Yang dilakukan:** pemakaian dari frontend dihapus (`getTokens` di `api.ts` dibuang — tidak dipakai halaman mana pun), sehingga tidak ada lagi jalur UI yang memanggilnya. Endpoint backendnya sendiri tetap ada dan tetap bocor — **butuh perintah Di untuk menghapus/menguncinya** (sesuai Action Plan P0-16: hapus endpoint, pemakaian token dilakukan server-side).

### 3.3 Migrasi `c758af...` tidak ada di disk (temuan 5.16)
- **Status: hanya dicatat, sesuai instruksi.** File migrasi `c758af9a050c` yang diklaim PHASE2-REPORT Claude memang tidak ada; skema dilipat ke migrasi awal `96117fdda23d` (18 tabel). Ini masalah klaim laporan, bukan bug kode — **tidak dibuat migrasi palsu**. Migrasi baru yang dibuat di ronde ini (`b3f8a1c9d204`, tabel `oauth_states`) adalah migrasi nyata untuk tabel baru, bukan pengganti klaim tersebut.

### 3.4 Item P0/P1 yang belum dikerjakan (di luar ronde ini)
- **Audit logging (P1-20):** belum ada audit log sama sekali di kaki Claude (login, perubahan settings, CRUD akun Google, penghapusan). Butuh desain + endpoint baca superuser — pekerjaan fitur baru, bukan perbaikan bug; ditunda.
- **P1-17 sebagian:** format deeplink Flow asli belum terverifikasi (tidak ada akses Flow/credential untuk membandingkan) — diberi label `verified: false` + peringatan UI, endpoint tidak dihapus.
- **P1-16 sebagian:** `/prompts/generate` belum tersambung ke `ai_client.generate()` (alasan di §1.6: tanpa key valid, panggilan LLM menggantung/timeout). Template diperbaiki + dilabeli jujur; penyambungan LLM adalah follow-up saat key tersedia.
- **P2/P3 (di luar perintah — fungsional P0/P1 saja):** validasi output story engine sebagai JSON (F-M8), duplikat `scene_number` mengabaikan soft-delete (F-L2), upload aset sungguhan multipart (F-M7), `.gitignore` untuk secret/DB, hapus hack stamp `alembic_version` (F-M9), hapus dead code hitung karakter (F-L1), perbaiki `datetime.utcnow()` deprecated, hapus 18 file `test_server_*.py` debug, naikkan React 19.0.0-rc ke stabil, ganti class-based `config` Pydantic → `ConfigDict`, endpoint ganti password, SceneEngine generate endpoint (model ada, API belum — hanya Shot CRUD yang dibuat di ronde ini).
- **Angka smoke builder lama (temuan 5.18):** klaim "25/25" Claude tidak terreproduksi dari repo dan tidak diperbaiki di sini — smoke ronde ini adalah 28 cek baru yang tercatat di §2, bukan validasi angka lama.

---

## 4. File yang diubah/dibuat

**Backend (baru):** `app/models/oauth_state.py`, `app/api/shots.py`, `app/schemas/shot.py`, `alembic/versions/b3f8a1c9d204_oauth_states.py`, `tests/test_fix_round2.py`
**Backend (diubah):** `app/main.py` (handler ValueError→400, registrasi router shots), `app/api/scenes.py` (add-character eager-load, validasi location_id di PATCH), `app/api/prompts.py` (resolve `{name}`, status `template`), `app/api/flow_bridge.py` (import UUID langsung, label manual/unverified), `app/api/google_accounts.py` (state DB, callback 502, redirect_uri konsisten), `app/models/__init__.py` (impor OAuthState), `tests/conftest.py` (impor OAuthState)
**Frontend (baru):** `src/app/dashboard/story/page.tsx`
**Frontend (diubah):** `src/app/dashboard/settings/page.tsx` (tulis ulang: tab AI Providers + Google OAuth ke `/api/settings`, tanpa sukses palsu), `src/app/dashboard/google-accounts/page.tsx` (state dari `oauth/start`, form callback ganti `prompt()`), `src/lib/api.ts` (refresh objek, `settingsApi`, hapus `getTokens`), `src/components/layout/DashboardLayout.tsx` (nav Story Engine + ikon), `src/app/dashboard/prompts/page.tsx` (label template jujur), `src/app/dashboard/flow/page.tsx` (label manual export, peringatan deeplink unverified)

**Tidak di-push ke GitHub** (sesuai instruksi; `claude/` juga gitignored di repo ini). Tidak ada kredensial yang ditulis/dikirim ke layanan luar.
