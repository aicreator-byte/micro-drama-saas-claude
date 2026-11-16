Perbaiki cacat kaki Claude yang ditemukan verifikasi independen sesudah fix round 2.

KONTEKS (sudah terverifikasi dari kode + tes live, jangan diperdebatkan):
- Fix round 2 SUDAH benar: `scenes.py` memakai `model_dump(exclude={"characters", "episode_id"})`,
  `dialogues.py` memakai `model_dump(exclude={"scene_id"})`. Duplicate-kwarg BERES.
- TAPI smoke test live (server uvicorn + SQLite segar, 19 cek) menemukan scene create MASIH 500.
  Akar baru, dari log server: `ResponseValidationError` saat serialisasi respons —
  `SceneRead.characters` memicu lazy-load relasi `Scene.characters` DI LUAR greenlet async
  (`MissingGreenlet: greenlet_spawn has not been called`). Scene-nya SUDAH tersimpan di DB;
  yang gagal adalah pengembalian respons. Handler GET di file yang sama SUDAH benar
  (pakai `selectinload`), handler create/patch TIDAK.
- `DialogueRead.character` punya pola sama (relasi di skema respons) — create dialogue
  kemungkinan 500 juga (belum sempat dites karena smoke berhenti di scene).
- Batas karakter: PROMPT hanya mensyaratkan "at least six characters per project" (tanpa
  batas atas) — karakter ke-7 diterima (201) BUKAN cacat. JANGAN tambah batas maks 6.

TUGAS (hanya ini, kerja HANYA di /home/hatch/workspace/micro-drama-saas/claude/):
1. `backend/app/api/scenes.py` — `create_scene`: sesudah commit, query ulang scene dengan
   `selectinload(Scene.characters).selectinload(SceneCharacter.character)` (cermin `get_scene`)
   lalu kembalikan hasil query itu. Perbaiki juga `update_scene` (PATCH) bila mengembalikan
   objek tanpa eager-load yang sama.
2. `backend/app/api/dialogues.py` — `create_dialogue`: sesudah commit, query ulang dengan
   `selectinload(Dialogue.character)` lalu kembalikan itu. Perbaiki juga `update_dialogue`
   (PATCH) bila polanya sama.
3. Audit SEMUA router lain untuk pola yang sama: handler yang mengembalikan Read schema
   berisi field relasi (daftar: `SceneRead.characters`, `DialogueRead.character`) WAJIB
   eager-load relasi itu sebelum return. `EpisodeRead`, `CharacterRead`, `LocationRead`,
   `SeriesBibleRead`, `PromptRead` hanya berisi field skalar — jangan ubah tanpa bukti.
4. SEBELUM menyatakan selesai, jalankan sendiri tes live: nyalakan backend (uvicorn + SQLite
   segar), lalu curl: register + login + buat proyek + series-bible + 6 karakter + lokasi +
   story generate + episode + scene 201 + dialogue 201 + prompts list + 20 akun Google +
   ke-21 ditolak 400. Tes level model SAJA tidak cukup — cacat round 2 lolos karena hanya
   dites di level model.

JANGAN UBAH: story engine tetap template/mock, OAuth tetap mock, struktur API/route/skema
respons tidak berubah, perbaikan UUID round 1 + duplicate-kwarg round 2 jangan disentuh.

PENERIMAAN: POST scene 201 + dialogue 201 (live, bukan klaim), pytest 32/32 dan proses
keluar sendiri, frontend `npm run build` exit 0.
Tulis FIX3-REPORT.md (apa yang diubah + hasil tes live per endpoint).
