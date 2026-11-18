# Fix Report: UUID String Comparison Bug

## Summary
Fixed HTTP 500 errors in project-scoped API endpoints caused by comparing UUID database columns with raw string path parameters without converting to `uuid.UUID` objects.

## Root Cause
The `get_current_user_id` function in `app/api/auth.py` returns the JWT `sub` claim as a STRING. Multiple routers were comparing UUID columns directly with these strings, causing SQLAlchemy's UUID bind processor to call `.hex` on the string → `AttributeError: 'str' object has no attribute 'hex'` → HTTP 500.

## Files Modified

### 1. `app/api/series_bible.py`
- Fixed `_verify_project_access`: Added `uuid.UUID(project_id)` and `uuid.UUID(user_id)` conversions
- Fixed all queries: `SeriesBible.project_id == project_uuid` (converted)
- Fixed insert: `SeriesBible(project_id=project_uuid)` (converted)

### 2. `app/api/episodes.py`
- Added `import uuid` at top
- Fixed all queries: `Episode.project_id == project_uuid` (converted)
- Fixed insert: `Episode(project_id=project_uuid)` (converted)
- Fixed reorder: `Episode.id == uuid.UUID(str(ep_id))` and `Episode.project_id == project_uuid`

### 3. `app/api/prompts.py`
- Added `import uuid` at top
- Fixed queries: `Prompt.project_id == project_uuid`, `Prompt.episode_id == uuid.UUID(episode_id)`, `Prompt.scene_id == uuid.UUID(scene_id)`

### 4. `app/api/google_accounts.py`
- Added `import uuid` at top
- Fixed all user_id comparisons: `user_uuid = uuid.UUID(user_id)`
- Fixed all account_id comparisons: `account_uuid = uuid.UUID(account_id)`
- Applied to: create, list, get, update, delete, oauth_callback, get_tokens

### 5. `app/api/assets.py`
- Added `import uuid` at top
- Fixed queries: `Asset.project_id == project_uuid`, `Asset.episode_id == uuid.UUID(episode_id)`, `Asset.scene_id == uuid.UUID(scene_id)`
- Fixed complete_upload: `Asset.id == asset_uuid`

### 6. `app/api/scenes.py`
- Added `import uuid` at top
- Fixed `_verify_episode_access`: `Episode.id == episode_uuid`, `Episode.project.has(owner_id=user_uuid)`
- Fixed all queries: `Scene.episode_id == episode_uuid`, `Scene.id == scene_uuid`
- Fixed reorder: `Scene.id == uuid.UUID(str(scene_id))`
- Fixed character operations: `SceneCharacter.scene_id == scene_uuid`, `SceneCharacter.character_id == character_uuid`

### 7. `app/api/dialogues.py`
- Added `import uuid` at top
- Fixed `_verify_scene_access`: `Scene.id == scene_uuid`, `Episode.project.has(owner_id=user_uuid)`
- Fixed all queries: `Dialogue.scene_id == scene_uuid`, `Dialogue.id == dialogue_uuid`
- Fixed reorder: `Dialogue.id == uuid.UUID(str(dlg_id))`

### 8. `app/api/flow_bridge.py`
- Added `import uuid` at top
- Fixed queries: `FlowBridge.project_id == project_uuid`, `FlowBridge.episode_id == uuid.UUID(episode_id)`, `FlowBridge.scene_id == uuid.UUID(scene_id)`
- Fixed google_account check: `GoogleAccount.user_id == user_uuid`
- Fixed import: `FlowBridge.id == task_uuid`
- Fixed deeplink: `FlowBridge.id == task_uuid`, `FlowBridge.project_id == project_uuid`

### 9. `app/api/story_engine.py`
- Added `import uuid` at top
- Fixed queries: `StoryEngine.project_id == project_uuid`, `StoryEngine.episode_id == uuid.UUID(episode_id)`, `StoryEngine.scene_id == uuid.UUID(scene_id)`
- Fixed get/delete: `StoryEngine.id == generation_uuid`, `StoryEngine.project_id == project_uuid`

## Test Results

### Backend Tests
```
32 passed, 86 warnings in 203.00s
```

All tests pass including:
- `tests/test_auth.py` - 4 tests
- `tests/test_projects.py` - 9 tests
- `tests/test_characters_locations.py` - 19 tests

### Frontend Build
```
> micro-drama-saas-frontend@1.0.0 build
> next build
✓ Compiled successfully
✓ Generating static pages (19/19)
Exit code: 0
```

## Acceptance Criteria Met

✅ Series bible create → 201  
✅ Episode create → 201  
✅ Scene + dialogue create → 201  
✅ Prompts list → 200  
✅ 20 Google accounts → 201 all; 21st account → 400  
✅ `pytest tests/ -q` → 32 passed, process exits cleanly  
✅ `npm run build` → exit 0  
✅ FIX-REPORT.md written to `claude/` directory