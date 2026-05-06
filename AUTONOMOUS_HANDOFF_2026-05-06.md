# PubCast Autonomous Handoff - 2026-05-06

## Short Version

The avatar motion lab now has a one-command smoke test that starts PubCast, waits for `/health`, runs Manny, Sheila, and Baby Humphrey through the same mocap/action/object-interaction pipeline, then stops the temporary server.

Run from the repo root:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_avatar_motion_lab_probe.ps1
```

Or double-click / run:

```cmd
RUN_AVATAR_MOTION_LAB.cmd
```

## What The Probe Proves

For each configured lab avatar, the probe:

1. Starts mocap for that avatar.
2. Sends a canned mocap frame.
3. Confirms the backend maps it to an avatar pose.
4. Sends a `hold_coffee` choreography cue.
5. Sends an `avatar_object_interaction.v1` contract.
6. Checks mocap status at the end.

Current avatars:

- `manny`: motion lane plus real GLB at `/assets/avatar/manny.glb`
- `sheila`: motion lane plus real GLB at `/assets/avatar/sheila.glb`
- `baby_humphrey`: motion lane plus reference image at `/assets/avatar/baby_humphrey_reference.webp`; no GLB body found in this repo yet

That last point matters. Baby Humphrey now has a visual reference image, but not yet a rigged visible 3D avatar asset.

## Important Files

- `RUN_AVATAR_MOTION_LAB.cmd` - simplest root-level launcher.
- `scripts/run_avatar_motion_lab_probe.ps1` - starts/stops temporary Uvicorn and runs the probe.
- `scripts/probe_avatar_motion_lab.ps1` - actual Manny/Sheila/Baby Humphrey gauntlet.
- `modules/avatar_motion_contract.py` - shared avatar motion lab vocabulary, canned frames, visual asset truth table, interaction defaults.
- `static/avatar_motion_lab.html` and `static/js/avatar_motion_lab.js` - browser motion lab surface.
- `tests/test_avatar_motion_contract.py` - contract tests for the motion lab vocabulary.
- `ANIMATION_MOCAP_HANDOFF.md` - broader animation/mocap project handoff.

## Known Runtime Warnings

These warnings were observed during successful runs:

- `PUBCAST_JWT_SECRET is not set` - local dev warning; set before anything public.
- `numpy`, `opencv-python`, `Pillow` missing - optional features degraded, not blocking the lab.
- `sir_purfluous_waiting_room.json` validation errors - one bot config is malformed; app continues with 3 valid bots.
- `VoxelBridge` TCP refused / Path C file-system fallback - causes repeated `IRM emergency mode - batch reduced to 500`; noisy and slower, but not blocking the avatar motion lab.

## Validation State

Confirmed in this session:

- PowerShell parser accepts `scripts/probe_avatar_motion_lab.ps1`.
- PowerShell parser accepts `scripts/run_avatar_motion_lab_probe.ps1`.
- User successfully ran the one-command wrapper multiple times.
- Successful probe output included `health: ok`, `avatar_motion_lab.v1`, mocap starts, mocap frames, cues, interactions, final status, and temporary server shutdown.

Not confirmed by Codex sandbox:

- Python tests could not be run from this sandbox because the venv launcher points to `C:\Users\hardc\AppData\Local\Programs\Python\Python312\python.exe`, which the sandbox cannot execute. The user's own PowerShell can run the venv.

## Backups Created

Before changing motion-lab scripts/contracts, copies were placed under:

- `rubish/pre_avatar_motion_run_all_20260506/`
- `rubish/pre_baby_humphrey_rename_20260506/`

No files were deleted.

## Next Best Work

The highest-value next steps are:

1. Give Baby Humphrey a real visual body, either by finding an existing asset or creating/importing one.
2. Connect `/avatar-motion-lab` to a visible GLB preview so Manny and Sheila visibly respond to the same pose stream.
3. Retarget mapped mocap bones to the Manny/Sheila GLB skeletons.
4. Add a walking-loop proof that moves the avatar root transform, even before full skeletal retargeting is perfect.
5. Reduce VoxelBridge emergency noise by either starting the twin-engine TCP service or adding a quieter dev fallback mode.

## Zip Snapshot

A source snapshot zip should live under `dist/` after packaging. It intentionally excludes local virtualenvs, logs, caches, and private runtime stores such as user databases/vaults.
