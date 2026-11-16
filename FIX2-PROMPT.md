Perbaiki cacat scene/dialogue hasil verifikasi independen fix round 1 (smoke live 18/19; UUID 500 sudah beres, JANGAN diutak-atik lagi).

## CACAT (1 akar, 2 file)

Verifikasi independen menemukan `TypeError: Scene() got multiple values for keyword argument 'episode_id'` → HTTP 500 saat POST /api/scenes/{episode_id}. Dialogue 404 hanya efek berantai (scene tidak pernah terbentuk).

Penyebab: di `backend/app/api/scenes.py` baris ~63:
```python
scene = Scene(
    episode_id=episode_uuid,
    **scene_dict,
)
```
`scene_dict` berasal dari `scene_data.model_dump(exclude={"characters"})` dan MASIH berisi `episode_id` (field `SceneCreate.episode_id: uuid.UUID`), jadi keyword `episode_id` terisi dua kali.

Pola SAMA di `backend/app/api/dialogues.py` baris ~51:
```python
dialogue = Dialogue(
    scene_id=scene_uuid,
    **dialogue_data.model_dump(),
)
```
`DialogueCreate` juga berisi `scene_id` → akan 500 begitu scene ada.

## PERBAIKAN (bedah, hanya yang diperlukan)

1. `scenes.py`: buang `episode_id` dari dict sebelum di-unpack, mis. `scene_dict = scene_data.model_dump(exclude={"characters", "episode_id"})`. JANGAN ubah field lain, JANGAN ubah skema.
2. `dialogues.py`: sama — `dialogue_data.model_dump(exclude={"scene_id"})`.
3. Audit SEMUA router di `backend/app/api/` untuk pola yang sama (`<Model>(<fk>_uuid, **<data>.model_dump())` di mana dict masih berisi fk itu). Perbaiki bila ada. Episodes.py AMAN (project_id hanya ada di EpisodeRead, bukan EpisodeCreate) — jangan disentuh bila tidak ada pola yang sama.
4. JANGAN ubah: story engine (tetap template/mock), Google OAuth (tetap mock), struktur API/route/skema respons, dan semua perbaikan UUID dari fix round 1.

## KERJA

- Hanya di direktori `/home/hatch/workspace/micro-drama-saas/claude/`. DILARANG membuka/membaca/menyalin `../hermes/` dan `../opencode/`.
- Buktikan dengan tes sendiri: jalankan backend di SQLite terpisah + buat proyek → episode → scene (harus 201) → dialogue (harus 201), lalu `pytest tests/ -q` (32/32) dan `npm run build` di frontend (exit 0).

## PENERIMAAN

- POST scene → 201, POST dialogue → 201
- `pytest tests/ -q` → 32 passed, proses keluar sendiri
- `npm run build` (frontend) → exit 0
- Tulis `FIX2-REPORT.md` di `claude/` yang mendeskripsikan HANYA file di `claude/` (file yang diubah + hasil tes). Lalu BERHENTI.
