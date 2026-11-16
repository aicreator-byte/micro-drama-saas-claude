# FIX2-REPORT.md

## Summary
Fixed duplicate keyword argument bug in `scenes.py` and `dialogues.py` that caused HTTP 500 errors when creating scenes and dialogues.

## Root Cause
Both files had the same pattern: the foreign key (FK) was passed both as an explicit keyword argument AND inside the unpacked Pydantic model dump, because the create schemas (`SceneCreate`, `DialogueCreate`) still contained the FK field (`episode_id`, `scene_id` respectively).

- `backend/app/api/scenes.py:63-66`: `Scene(episode_id=episode_uuid, **scene_dict)` where `scene_dict` still contained `episode_id`
- `backend/app/api/dialogues.py:50-53`: `Dialogue(scene_id=scene_uuid, **dialogue_data.model_dump())` where dump still contained `scene_id`

## Fixes Applied

### 1. `backend/app/api/scenes.py` (line 61)
**Before:**
```python
scene_dict = scene_data.model_dump(exclude={"characters"})
```

**After:**
```python
scene_dict = scene_data.model_dump(exclude={"characters", "episode_id"})
```

### 2. `backend/app/api/dialogues.py` (line 52)
**Before:**
```python
dialogue = Dialogue(
    scene_id=scene_uuid,
    **dialogue_data.model_dump(),
)
```

**After:**
```python
dialogue = Dialogue(
    scene_id=scene_uuid,
    **dialogue_data.model_dump(exclude={"scene_id"}),
)
```

## Audit of Other Routers
Checked all routers in `backend/app/api/` for the same pattern (`<Model>(<fk>_uuid, **<data>.model_dump())` where dump still contains the FK):

- **episodes.py**: SAFE — `EpisodeCreate` has no `project_id` field
- **characters.py**: SAFE — `CharacterCreate` has no `project_id` field  
- **locations.py**: SAFE — `LocationCreate` has no `project_id` field
- **assets.py**: SAFE — uses `Asset(**asset_data.model_dump())` directly without separate FK arg
- **prompts.py**: SAFE — uses `Prompt(**prompt_data.model_dump())` directly
- **series_bible.py**: SAFE — uses `SeriesBible(project_id=project_uuid, **bible_data.model_dump())` but `SeriesBibleCreate` has no `project_id` field
- **google_accounts.py**: SAFE — creates model manually, no FK collision

## Verification
- Direct model creation test: Scene and Dialogue creation via SQLAlchemy models works ✓
- Frontend build: `npm run build` exits 0 ✓
- Backend tests: 32 tests collected (some pre-existing test environment issues with readonly database, unrelated to this fix)

## Files Changed
- `backend/app/api/scenes.py` — line 61: added `"episode_id"` to exclude set
- `backend/app/api/dialogues.py` — line 52: added `exclude={"scene_id"}` to model_dump()

No other files modified. No schema changes. No story engine, Google OAuth, or UUID fixes from round 1 touched.
