# AUTO-GENERATE Fase 2 — Frontend Report (kaki Claude)

**Tanggal:** 19 Nov 2026. **Spek:** `~/workspace/micro-drama-saas/AUTO-GENERATE-SPEC.md` §6.
**Kontrak backend (Fase 1, TIDAK diubah):** `AUTO-GENERATE-F1-REPORT.md` — `POST /api/projects/{id}/auto-generate`
(TANPA `/v1`; body `title` wajib, `genre`, `total_episodes` 1–100 default 30, `premise`),
`GET .../auto-generate/{job_id}`, `POST .../retry/{step}`.
**Ruang lingkup:** frontend saja. Backend TIDAK disentuh, kaki lain TIDAK disentuh, TIDAK push GitHub.

## Yang dibangun

Satu modal Auto-Generate (form + progres + retry), dipakai di 2 tempat.

### File baru

- `frontend/src/components/auto-generate/AutoGenerateModal.tsx` — modal + progres:
  - Form: judul (terisi judul proyek), genre (default "Auto (from title)"),
    jumlah episode (number, 1–100, default 30), premis (terisi deskripsi proyek).
  - Submit → `POST .../auto-generate` → tampilkan 5 langkah berurutan
    (Series Bible → Characters → Locations → Episodes → Prompts) dengan status
    tiap langkah (pending/running/completed/failed) + pesan error.
  - Tombol **Retry** di langkah yang gagal (endpoint retry Fase 1); langkah sukses
    dipertahankan. Job completed → daftar tautan hasil (Series Bible, Characters,
    Locations, Episodes, Prompts) + store di-refresh (bible/karakter/lokasi/
    episode/prompt di-fetch ulang) sehingga halaman hasil langsung menampilkan
    data baru tanpa refresh manual.
  - Polling `GET .../auto-generate/{job_id}` tiap 2 dtk HANYA bila job masih
    `running` (backend Fase 1 jalan sinkron — respons POST biasanya sudah
    terminal; polling ini pengaman bila backend suatu saat jadi async).

### File diubah

- `frontend/src/lib/api.ts` — tambah `autoGenerateApi` (create/get/retry).
- `frontend/src/types/api.ts` — tambah tipe `AutoGenerateCreate`,
  `AutoGenerateJobRead`, `AutoGenerateStepRead`, `AutoGenerateStepName`,
  `AutoGenerateStepStatus`, `AutoGenerateJobStatus`.
- `frontend/src/app/dashboard/story/page.tsx` — kartu baru **Auto-Generate** di
  atas kartu Generate (halaman Story Engine = hub AI kaki ini; pemilih proyek
  sudah ada di halaman itu). Tombol nonaktif bila belum ada proyek.
- `frontend/src/app/dashboard/projects/page.tsx` — tombol Sparkles
  (Auto-Generate) di tiap kartu proyek, membuka modal yang sama.

### Keputusan desain (terverifikasi dari kode)

- **Tidak ada halaman detail proyek di kaki ini.** Route
  `/dashboard/projects/[id]` TIDAK ADA (hanya `projects/page.tsx`); tautan
  "Open Project" di dashboard + daftar proyek mengarah ke route yang tidak
  ada (bug lama, di luar scope Fase 2). Karena itu tombol ditaruh di 2 tempat
  yang ADA dan masuk akal — kartu proyek + halaman Story Engine — bukan dengan
  membangun halaman detail baru.
- **§7.2 counter/badge "Active": TIDAK BERLAKU di kaki ini.** Grep `Active` di
  `frontend/src/` hanya menemukan: status akun Google (active/inactive),
  state tab Settings, dan state nav aktif. TIDAK ADA counter "Active Projects"
  dan TIDAK ADA badge "Active" untuk proyek di kaki Claude — jadi tidak ada
  definisi yang perlu disamakan. Tidak ada yang diubah.
  - Observasi (tidak diperbaiki, di luar scope): kartu statistik dashboard
    menampilkan Characters/Locations/Episodes = 0 hardcode
    (`dashboard/page.tsx`), bukan angka nyata.

### §7.1 akun demo "Test"

Tidak berubah dari temuan Fase 1: tidak ada seed akun Test di kaki ini.

## Cara pakai (langkah klik)

1. Login → **Story Engine** (sidebar) atau **Projects**.
2. Pilih proyek (Story) atau klik ikon Sparkles di kartu proyek (Projects).
3. Modal Auto-Generate: isi/ubah judul, genre, jumlah episode, premis → **Start Auto-Generate**.
4. Progres 5 langkah tampil; bila satu langkah gagal, klik **Retry** di langkah itu.
5. Selesai → klik tautan hasil (mis. Characters) — data baru langsung tampil.

## Hasil verifikasi

- `npx tsc --noEmit`: **0 error** (exit 0).
- `npm run build` (`next build`): **exit 0** — 17 route ter-build, termasuk
  `/dashboard/story` dan `/dashboard/projects` (First Load JS 145 kB).
- `npm run lint`: **TIDAK BISA DIJALANKAN — bukan karena kode ini.** Repo ini
  tidak punya konfigurasi ESLint sama sekali (tidak ada `.eslintrc*`); `next lint`
  malah menampilkan prompt interaktif "How would you like to configure ESLint?".
  Kondisi ini sudah ada sebelum Fase 2 (pre-existing); mengonfigurasi ESLint di
  luar scope brief, jadi tidak dilakukan.

## TIDAK dikerjakan (sesuai larangan)

Backend/API, auth/security, fallback akun Google, Flow Bridge, CRUD manual
(selain menambah tombol/modal), kaki lain, push GitHub, hapus file.

## NOT VERIFIED

- **Uji klik manual di browser** (Fase 3): alur di atas baru terverifikasi via
  typecheck + build, belum diklik end-to-end di server berjalan.
- **Generasi LLM nyata:** backend Fase 1 memakai mock di tes; kualitas konten
  dan perilaku job sinkron yang lama (LLM lambat → request HTTP lama) belum
  teruji live.
- **Jalur polling:** belum teruji live karena backend sinkron selalu
  mengembalikan job terminal dari POST; polling hanya berjalan bila job
  `running` — belum pernah terjadi di tes.
