Perbaiki cacat Phase 2 kaki Claude yang ditemukan verifikasi independen sesudah PHASE2-REPORT.md ditulis.

KONTEKS (sudah terverifikasi dari kode + tes live, jangan diperdebatkan):
- pytest 54/54 LULUS (terverifikasi independen) dan frontend build selesai 19 halaman tanpa error.
- TAPI server TIDAK BISA START — `init_db()` hanya menjalankan `alembic upgrade head` (tanpa `create_all`), dan rantai migrasi rusak:
  - `027a9ef8737e_initial.py` KOSONG (`upgrade()`/`downgrade()` = `pass`) — tidak membuat tabel apa pun.
  - `c758af9a050c_phase_2_...` mengasumsikan tabel dasar sudah ada: `ALTER TABLE google_accounts ADD COLUMN password_encrypted` + `CREATE TABLE app_settings/shots/scene_engine`.
  - DB SEGAR: migrasi gagal `sqlite3.OperationalError: no such table: google_accounts` → `RuntimeError: Alembic migration failed` → server mati saat startup.
  - DB LAMA (`micro_drama.db`, tabel sudah dibuat `create_all` versi lama, `alembic_version` = `027a9ef8737e`): migrasi gagal `table app_settings already exists` → server mati juga.
- Akibatnya klaim smoke live di PHASE2-REPORT.md (register → story generate LLM nyata → scene/dialogue 201 → OAuth → Settings) TIDAK BISA direproduksi: server tidak pernah jalan dengan kode saat ini. Klaim "Alembic downgrade → upgrade: Clean round-trip di DB segar" SALAH.
- Yang TIDAK rusak: isi Phase 2 (ai_client, story engine LLM, Settings API, OAuth, model Shot/SceneEngine, validasi location_id, 22 tes baru) — pytest membuktikannya. Cacatnya HANYA di jalur migrasi/startup.

TUGAS (hanya ini, kerja HANYA di /home/hatch/workspace/micro-drama-saas/claude/):
1. Perbaiki rantai migrasi/startup supaya server bisa start di KEDUA skenario:
   (a) DB SEGAR (file tidak ada): `alembic upgrade head` berhasil, semua tabel terbentuk, server start.
   (b) DB LAMA (`micro_drama.db` yang sudah punya semua tabel tapi `alembic_version` = `027a9ef8737e`): server start tanpa error migrasi (boleh dengan menandai revisi sudah diterapkan bila tabel sudah sesuai, atau cara lain yang benar).
   Pilih perbaikan terkecil yang benar (Ponytail: jangan tulis ulang sistem migrasi; jangan ubah isi Phase 2; jangan ubah route/skema respons). Bila perlu, regenerasi migrasi initial dari model yang benar, atau buat `init_db` tahan terhadap kedua skenario — putuskan sendiri mana yang paling kecil dan benar, dan tulis alasannya di laporan.
2. JANGAN ubah: ai_client, story_engine (LLM nyata), settings API, OAuth, model, validasi location_id, tes yang sudah ada, SECRET_KEY/auth/JWT/enkripsi. JANGAN sentuh security. JANGAN tambah batas maks karakter. JANGAN sentuh kaki lain.
3. SEBELUM menyatakan selesai, jalankan sendiri tes live DUA skenario dan simpan buktinya:
   (a) DB SEGAR: hapus file DB tes, nyalakan server (uvicorn + kunci Nvidia asli dari env), lalu curl: register + login + proyek + series-bible + 6 karakter + lokasi + story generate (BUKTI LLM nyata: `model_used` ultra-550b, `tokens_used` > 0, `generated_output` berisi kata kunci unik dari prompt — JANGAN pakai test key yang 401) + episode + scene 201 + dialogue 201 + oauth/start 400 + oauth/callback state salah 400 + settings GET 200 (tanpa rahasia) + settings PATCH 200 + GET lagi tanpa bocor.
   (b) DB LAMA: salin `micro_drama.db` ke file tes, nyalakan server dengan DB itu, buktikan `/health` 200 + login + list proyek jalan.
   Tes level model SAJA tidak cukup — cacat ini lolos karena hanya dites di level model + DB lama.

PENERIMAAN: server start di DB segar DAN DB lama; pytest 54/54 (tidak boleh turun); smoke live (a) semua cek lolos dengan bukti LLM nyata; frontend `npm run build` exit 0.
Tulis PHASE2-FIX-REPORT.md (apa yang diubah + hasil tes live kedua skenario per endpoint + bukti LLM nyata).
