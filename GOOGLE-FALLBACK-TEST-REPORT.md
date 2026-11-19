# Uji Fallback Akun Google — kaki Claude (tes mekanisme)

Tanggal: 19 Nov 2026, ~08:40–08:41 WIB. Perintah parent: uji fallback akun
Google di kaki Claude saja, dengan 2 akun tes buatan sendiri (akun asli Di
TIDAK dipakai — tidak pernah masuk DB: browser cloud tidak bisa membuka
frontend localhost, jadi penambahan akun asli lewat browser gagal sebelum
tes ini).

Scope: tes saja, tidak ada kode produk yang diubah. Tidak ada video
di-generate. Semua langkah via API ke backend live http://127.0.0.1:8003
(prefix /api, tanpa /v1). Skrip tes: /tmp/fb-test-claude.py
(hasil mentah: /tmp/fb-test-claude-out.json).

## Setup tes (terverifikasi via API + DB read-only)

- User tes: fallback-test@example.com (id 023e4c58-ec45-4e14-8b94-89f94c79274d),
  register 201 + login 200 via POST /api/auth/*.
- Proyek tes: FALLBACK-TEST (id 13be8f19-fcf9-4041-86c4-cc9a114d7fa3).
- Akun A: tes-fallback-a-20261119@gmail.com (id d5c534b8-258b-406e-9ed8-435f79225440),
  account_index 0, is_active true, password TERSIMPAN terenkripsi,
  tanpa access token. Email palsu, password salah (nilai tes, tidak dicantumkan).
- Akun B: tes-fallback-b-20261119@gmail.com (id 45819cf4-f2af-4c31-8284-d63d3dfd2bc3),
  account_index 1, is_active true, password TERSIMPAN terenkripsi,
  tanpa access token. Email palsu lain, password salah yang berbeda.
- Verifikasi DB: kedua akun `password_encrypted IS NOT NULL`, `access_token_encrypted IS NULL`.

## Uji 1 — execute-browser (jalur login browser + fallback), task pin ke A

- Task: FB-TEST-BROWSER (id 9ca2df4a-9e56-43ee-adc7-3783aa817661),
  task_type video_generation, input_prompts 1 prompt tes.
- `POST /api/flow/{project}/{task}/execute-browser` → **502 dalam 3,4 dtk**:
  `Could not reach Google Flow: Page.goto: net::ERR_TUNNEL_CONNECTION_FAILED
  at https://flow.google.com/`
- Task sesudahnya: status `failed`, flow_url null,
  error_message `Google unreachable from the browser: Could not reach
  Google Flow: Page.goto: net::ERR_TUNNEL_CONNECTION_FAILED ...`
- fallback_history (1 percobaan saja):
  `[{account_id: d5c534b8..., email: tes-fallback-a-20261119@gmail.com,
  outcome: failed, reason: unreachable, mode: browser,
  detail: "Could not reach Google Flow: Page.goto: net::ERR_TUNNEL_CONNECTION_FAILED ..."}]`
- Akun B TIDAK pernah dicoba — sesuai desain (flow_browser_execution.py:
  reason `unreachable` masuk `_ABORT_REASONS`, run di-abort setelah akun
  pertama karena akun lain akan kena jaringan mati yang sama).

## Uji 2 — /execute (jalur token + fallback), task pin ke A

- Task: FB-TEST-TOKEN (id 8170f1b2-dc5e-4cce-8f51-86a57005b39e).
- `POST /api/flow/{project}/{task}/execute` → **502 dalam 0,1 dtk**:
  `All Google accounts failed — tes-fallback-a-20261119@gmail.com: no_token;
  tes-fallback-b-20261119@gmail.com: no_token`
- Task sesudahnya: status `failed`, error_message sama seperti di atas.
- fallback_history (2 percobaan, urut A lalu B):
  A `reason: no_token, detail: "Account has no access token stored"`,
  B `reason: no_token, detail: "Account has no access token stored"`.
- **Mekanisme pindah-ke-akun-berikut TERVERIFIKASI live**: A gagal →
  B dicoba → B gagal → 502 menyebut kedua akun + alasannya.

## Uji 3 — /execute, task pin ke B (cek aturan pin-dulu)

- Task: FB-TEST-PINNED-B (id e6edabcc-d937-4e0b-95a3-67c7494b0fa7).
- `POST /execute` → **502**:
  `All Google accounts failed — tes-fallback-b-20261119@gmail.com: no_token;
  tes-fallback-a-20261119@gmail.com: no_token`
- fallback_history urut B lalu A → **aturan "akun ter-pin dulu, lalu akun
  lain urut account_index" TERVERIFIKASI live**.

## Kesimpulan

- **Mekanisme fallback jalan sesuai desain** (terverifikasi live):
  urutan kandidat benar (pin dulu, lalu account_index), tiap percobaan
  tercatat di fallback_history dengan alasan, semua-gagal → task FAILED +
  502 menyebut tiap akun, unreachable → abort setelah akun pertama.
- **Login browser ke Google asli dari VM ini TIDAK BISA** (bukan bug
  aplikasi): Chromium backend kena `ERR_TUNNEL_CONNECTION_FAILED` ke
  flow.google.com — egress VM memblokir Google di level tunnel, sama
  seperti smoke 17 Nov. Karena itu jalur browser tidak pernah sampai
  ke form login Google.

## Yang NOT VERIFIED (jujur)

- **Login Google asli (akun Di)**: akun tidak ada di DB kaki Claude
  (GET /api/google-accounts saat tes hanya berisi 2 akun tes). Akun asli
  tidak pernah ditambahkan karena browser cloud tidak menjangkau
  frontend localhost. Tidak ada kredensial asli yang dipakai atau
  disentuh dalam tes ini.
- **Jalur wrong_password → pindah akun (browser path) secara live**:
  browser tidak pernah mencapai form login Google, jadi klasifikasi
  login_failed/captcha dan perpindahan akun pada kegagalan login hanya
  terverifikasi di pytest (tests/test_browser_login.py, runner di-stub),
  bukan live.
- **Submit prompt ke Flow asli / video**: tidak diuji (di luar scope),
  tidak ada video di-generate.

## Data tes yang tertinggal di DB live (micro_drama.db)

User fallback-test@example.com, proyek FALLBACK-TEST, akun A + B,
task FB-TEST-BROWSER / FB-TEST-TOKEN / FB-TEST-PINNED-B (semua status
failed). ID lengkap di atas; hapus bila tidak diperlukan lagi.
Tidak ada file produk yang diubah.
