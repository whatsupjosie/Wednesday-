# Animation / Mocap / Avatar World Handoff

Date: 2026-05-06

Purpose: focused starting point for the next PubCast pass after security and control-room distractions were cleared.

## Current Safe State

- Security spine / Oubliette / Iteration Wallet work is present but intentionally dormant.
- Control room polish from Claude is imported:
  - runtime page: `static/control_room.html`
  - calibrator: `static/control_room_calibrate.html`
  - reference images: `docs/ui/control_room_references_20260506/`
- Previous control-room file and import sources were preserved under:
  - `rubish/pre_control_room_polish_20260506_013208/`
- Dependency-capable Python is still missing in this environment. Blender Python is available, but it does not have `pytest`, `fastapi`, or `uvicorn`.

## Motion Work Already Added

- `modules/mocap_integration.py`
  - Added `MocapIntegration` app-facing facade.
  - Added manual frame ingestion via `ingest_frame(...)`.
  - Added canonical avatar bone mapping:
    - `hips -> Pelvis`
    - `spine -> Spine_01`
    - `left_wrist -> Hand_L`
    - `right_ankle -> Foot_R`
  - Sends mapped poses to bridge as `MOTION_UPDATE` when a bridge is available.
  - Broadcasts `mocap_frame` and `avatar_pose` events through the hub.
- `main.py`
  - MoCap now initializes as `MocapIntegration(hub=hub, bridge=voxel_bridge)`.
  - Added `POST /api/mocap/frame` for manual mocap frame ingestion.
- `tests/test_mocap_integration.py`
  - Covers manual mocap start/stop.
  - Covers frame-to-canonical-bone mapping.
  - Covers `MOTION_UPDATE` bridge payload.
  - Covers hub broadcasts.

## Validation Already Run

With Blender Python and `PYTHONDONTWRITEBYTECODE=1`:

- In-memory compile passed for:
  - `main.py`
  - `modules/mocap_integration.py`
  - `tests/test_mocap_integration.py`
  - `modules/security_spine_service.py`
  - `modules/security_orchestrator.py`
- Direct no-pytest mocap tests passed:
  - `test_manual_start_and_stop_updates_status`
  - `test_frame_ingest_maps_to_canonical_avatar_bones_and_bridge`
  - `test_frame_ingest_broadcasts_raw_frame_and_mapped_pose`
- Node checks passed:
  - inline scripts in `static/control_room.html`
  - inline scripts in `static/control_room_calibrate.html`
  - `static/bots.js`
  - `static/control_stations.js`

## Main Problem To Solve Next

Build the basic avatar functioning layer, not a giant animation engine first.

The next goal should be:

1. Manny/Sheila can receive a motion pose.
2. The pose can be represented as canonical skeleton data.
3. The world/control-room/frontend can see whether motion is live.
4. Choreography actions, mocap frames, and avatar object interactions use one shared motion contract.
5. Only after that, build richer animation sampling/blending.

## Recommended Next Pass

### 1. Prove The Motion Contract End To End

Add or update a tiny frontend/debug surface that can:

- call `/api/mocap/start`;
- post a sample `/api/mocap/frame`;
- show latest `avatar_pose`;
- show bridge send status;
- show which avatar is targeted.

Candidate locations:

- `static/control_room.html` if adding a small station/status panel.
- `static/avatar_walk_test.html` if turning it into the avatar motion test surface.
- A new focused `static/avatar_motion_lab.html` if keeping it isolated.

Best choice: create `static/avatar_motion_lab.html` first, then fold the useful part into control room later.

### 2. Connect Choreography To Mocap Vocabulary

Current relevant files:

- `modules/choreography_controller.py`
- `modules/choreography_runtime.py`
- `modules/mocap_integration.py`
- `main.py`
- `static/control_room.html`

Needed:

- Define a small shared action-to-pose/status payload.
- Keep actions like `walk`, `sit_desk`, `hold_coffee`, `work_console`, `film_camera` as cues.
- Do not pretend full skeletal animation exists until pose changes visibly move something.

### 3. Add Avatar Object Interaction Contract

Start with data, not visuals.

Suggested contract:

```json
{
  "avatar_id": "manny",
  "action": "hold_coffee",
  "object_id": "coffee_mug_01",
  "attach_to": "Hand_R",
  "duration": 2.0,
  "state": "active"
}
```

Likely endpoint:

- `POST /api/avatar/interaction`

Likely event:

- `avatar_object_interaction`

### 4. Then Build Animation Runtime

Only after the contract moves data end to end:

- keyframe sampling;
- crossfade state machine;
- animation layers;
- mocap base plus procedural/action overlay;
- Manny/Sheila-specific variants.

## Files To Open First

- `modules/mocap_integration.py`
- `tests/test_mocap_integration.py`
- `modules/choreography_controller.py`
- `modules/choreography_runtime.py`
- `static/avatar_walk_test.html`
- `static/js/avatar_glb_walk.js`
- `data/avatars/manifest.json`
- `rust_crate/src/skeleton.rs`
- `main.py`

## Important Cautions

- Do not hook security gating into asset intake yet.
- Do not replace the control room again unless a runtime issue is proven.
- Do not claim Manny/Sheila skeletal animation is working until a browser or renderer proof shows visible pose/animation changes.
- Keep any new animation/mocap work narrowly testable.
- Keep backups in `rubish/` before replacing existing runtime files.

## Suggested First Concrete Task

Create `static/avatar_motion_lab.html` and a tiny JS companion that:

1. starts mocap manually;
2. sends a canned frame for Manny;
3. sends a canned frame for Sheila;
4. displays mapped bones and hub/bridge status;
5. has buttons for choreography cues like `walk`, `hold_coffee`, and `work_console`.

Then add a focused backend test for any new endpoint or event contract before making the visuals fancy.

## 2026-05-06 Motion Lab Pass

Added the first isolated avatar motion proof surface:

- `static/avatar_motion_lab.html`
- `static/js/avatar_motion_lab.js`
- route: `GET /avatar-motion-lab`

The lab can:

- start manual mocap for Manny or Sheila;
- send canned Manny and Sheila mocap frames;
- display mapped canonical bones from the latest `avatar_pose`;
- show mocap status, active avatar, rig, frame count, and bridge send status;
- trigger choreography cues: `walk`, `hold_coffee`, `work_console`;
- prepare an avatar-object interaction contract without activating security gating.

Added shared backend motion vocabulary/contract helpers:

- `modules/avatar_motion_contract.py`
- route: `GET /api/avatar/motion-lab`
- route: `POST /api/avatar/interaction`
- event: `avatar_object_interaction`

Contract example:

```json
{
  "avatar_id": "manny",
  "action": "hold_coffee",
  "object_id": "coffee_mug_01",
  "attach_to": "Hand_R",
  "duration": 2.0,
  "state": "active",
  "contract": "avatar_object_interaction.v1"
}
```

Validation run with Blender Python and Node:

- compiled `main.py`;
- compiled `modules/avatar_motion_contract.py`;
- compiled `tests/test_avatar_motion_contract.py`;
- direct no-pytest avatar motion contract tests passed;
- direct no-pytest mocap integration tests still passed;
- `node --check static/js/avatar_motion_lab.js` passed.

Runtime caveat:

- This environment still lacks `fastapi`, `uvicorn`, and `pytest`, so the app server and full pytest suite were not run here.

Next best pass:

1. Run the app in a dependency-capable Python environment and open `/avatar-motion-lab`.
2. Verify button calls against the live FastAPI app and WebSocket event feed.
3. Add a renderer-visible pose proof only after the data path is confirmed in browser.
4. Then fold the useful lab status bits into `static/control_room.html`.

## 2026-05-06 Runtime / Cue Contract Follow-up

Runtime progress:

- A local `.venv` was created outside Codex's direct executable access.
- PubCast booted successfully with Uvicorn after installing `jinja2`.
- `requirements.txt` now includes `jinja2>=3.1.0,<4.0` because `main.py` uses `Jinja2Templates`.
- The app reached ready state and served health/control-room routes in the user's PowerShell.

Known runtime warnings observed:

- `PUBCAST_JWT_SECRET` is unset; acceptable for local dev, not production.
- `numpy`, `opencv-python`, and `Pillow` are optional/missing; related subsystems degrade.
- Voxel bridge is in emergency/file-system mode because the twin engine TCP target refused connection.
- `data/bots/sir_purfluous_waiting_room.json` is not shaped like `BotConfig`; app continues with 3 valid bots.

Motion contract update:

- `ChoreoController.cue_action(...)` now adds `object_interaction` to interaction cues when possible.
- Example: `hold_coffee` now carries `coffee_mug_01 -> Hand_R` using `avatar_object_interaction.v1`.
- `static/js/avatar_motion_lab.js` displays object interaction details from cue payloads.
- `.venv/` is now ignored in `.gitignore`.

Validation after this follow-up:

- compiled `modules/choreography_controller.py`;
- compiled `modules/avatar_motion_contract.py`;
- direct no-pytest choreography tests passed;
- direct no-pytest avatar motion contract tests passed;
- `node --check static/js/avatar_motion_lab.js` passed;
- `node --check static/js/pubcast_typing_space_guard.js` passed;
- `node --check static/control_stations.js` passed.
