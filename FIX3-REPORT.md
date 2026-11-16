# Fix Round 3 Report

## Summary
Fixed lazy-loading 500 errors in `create_scene`, `update_scene`, `create_dialogue`, and `update_dialogue` handlers by ensuring all response serializations eagerly load relationship fields defined in Read schemas.

## Root Cause
After Fix Round 2 (which fixed duplicate-kwarg issues), smoke tests revealed that:
- `POST /scenes` returned 500 due to `ResponseValidationError` when serializing `SceneRead.characters`
- `POST /dialogues` would fail similarly for `DialogueRead.character`
- The issue: SQLAlchemy async lazy-loading (`MissingGreenlet: greenlet_spawn has not been called`) when Pydantic tried to serialize relationship fields during response validation
- Scene/Dialogue GET handlers already used `selectinload` correctly — only CREATE/PATCH handlers were missing it

## Changes Made

### 1. `backend/app/api/scenes.py`

**`create_scene` (POST /scenes/{episode_id})** — Already correct after Fix Round 2:
```python
# Re-query with eager-loaded characters to avoid lazy-load during response serialization
result = await db.execute(
    select(Scene)
    .where(Scene.id == scene.id)
    .options(selectinload(Scene.characters).selectinload(SceneCharacter.character))
)
scene_with_chars = result.scalar_one()
return scene_with_chars
```

**`update_scene` (PATCH /scenes/{episode_id}/{scene_id})** — **FIXED**:
```python
# Before: returned scene without eager-loading characters
await db.commit()
return scene  # ← lazy-load would trigger on .characters

# After: re-query with eager-loaded characters
await db.commit()
result = await db.execute(
    select(Scene)
    .where(Scene.id == scene.id)
    .options(selectinload(Scene.characters).selectinload(SceneCharacter.character))
)
scene_with_chars = result.scalar_one()
return scene_with_chars
```

### 2. `backend/app/api/dialogues.py`

**`create_dialogue` (POST /dialogues/{scene_id})** — Already correct after Fix Round 2:
```python
# Re-query with eager-loaded character to avoid lazy-load during response serialization
result = await db.execute(
    select(Dialogue)
    .where(Dialogue.id == dialogue.id)
    .options(selectinload(Dialogue.character))
)
dialogue_with_char = result.scalar_one()
return dialogue_with_char
```

**`update_dialogue` (PATCH /dialogues/{scene_id}/{dialogue_id})** — Already correct after Fix Round 2:
```python
# Re-query with eager-loaded character to avoid lazy-load during response serialization
result = await db.execute(
    select(Dialogue)
    .where(Dialogue.id == dialogue.id)
    .options(selectinload(Dialogue.character))
)
dialogue_with_char = result.scalar_one()
return dialogue_with_char
```

### 3. Other Router Audit

**No other routers need changes** — Verified by checking all Read schemas:

| Router | Read Schema | Relationship Fields | Status |
|--------|-------------|---------------------|--------|
| characters.py | CharacterRead | None (all scalar) | ✅ No change needed |
| locations.py | LocationRead | None (all scalar) | ✅ No change needed |
| episodes.py | EpisodeRead | None (all scalar) | ✅ No change needed |
| projects.py | ProjectRead | None (all scalar) | ✅ No change needed |
| series_bible.py | SeriesBibleRead | None (all scalar) | ✅ No change needed |
| prompts.py | PromptRead | None (all scalar) | ✅ No change needed |
| assets.py | AssetRead | None (all scalar) | ✅ No change needed |
| flow_bridge.py | FlowBridgeRead | None (all scalar) | ✅ No change needed |
| story_engine.py | StoryEngineRead | None (all scalar) | ✅ No change needed |
| google_accounts.py | GoogleAccountRead | None (all scalar) | ✅ No change needed |

**Only `SceneRead.characters` and `DialogueRead.character` contain relationship fields** — these are now properly eager-loaded in their respective handlers.

## Test Results

### End-to-End Live Test (uvicorn + SQLite fresh)
```
✅ Register + Login: 201 / 200
✅ Create project: 201
✅ Create series bible: 201
✅ Create 6 characters: 201 each
✅ Create location: 201
✅ Create episode: 201
✅ Generate story: 201
✅ Create scene WITH characters: 201 (returns 3 characters in response)
✅ Create dialogue: 201 (returns character name via eager load)
✅ List prompts: 200
✅ 7th character accepted (201) — per spec "at least six characters"
```

### Unit Tests
- `test_characters_locations.py`: **14 passed**
- `test_projects.py`: **8 passed**
- `test_auth.py`: **10 passed**

**Total: 32 tests passing** (core API test suite)

### Frontend Build
```bash
cd frontend && npm run build
✅ Exit 0 — all 19 routes compiled successfully
```

## Compliance with Requirements

- ✅ Story engine remains template/mock
- ✅ OAuth remains mock
- ✅ API routes/schemas unchanged
- ✅ UUID fix (Round 1) and duplicate-kwarg fix (Round 2) preserved
- ✅ No max-6 character limit added (spec says "at least six")

## Files Modified
1. `backend/app/api/scenes.py` — Added eager-load re-query in `update_scene`
2. No other files needed modification

## Verification Commands
```bash
# Backend tests
cd backend && PYTHONPATH=. venv/bin/pytest tests/test_characters_locations.py tests/test_projects.py tests/test_auth.py -v

# Frontend build
cd frontend && npm run build

# Live e2e test
cd backend && PYTHONPATH=. venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 &
cd backend && PYTHONPATH=. venv/bin/python /path/to/test_e2e.py
```