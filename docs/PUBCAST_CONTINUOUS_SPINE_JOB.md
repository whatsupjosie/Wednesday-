# PubCast Continuous Spine Job Patch

Continues the permanent spine foundation without destructively rewriting the legacy app.

## Added spine-owned layers

1. **State authority** (`runtime/state_authority.py`): canonical runtime truth, transactional mutations, canonical event namespaces, and runtime state classes.
2. **World/Room truth** (`runtime/world_service.py`): canonical room list, avatar movement through state authority, and `room.left`, `room.entered`, `avatar.moved`, `world.state.changed` events.
3. **Pub Manager** (`runtime/pub_manager.py`): owns establishment-wide operating mode and continuity policy without replacing State Authority, Jeeves, Pete, E-Pete, or the spine.
4. **Event/WebSocket bridge hooks** (`runtime/bridge_service.py`): captures all spine events and defines canonical runtime event names without rewriting every UI page.
5. **Motion state** (`runtime/motion_service.py`): tracks `idle`, `walking`, `posing`, `interacting`, `unavailable`; live mocap remains a provider hook, not a fake implementation.
6. **Two-brain AI router** (`runtime/ai_router_service.py`): separates persona AI from engine/architect AI; neither gets direct runtime control.
7. **Session persistence skeleton** (`runtime/persistence_service.py`): exports/saves spine snapshots; restore/import is intentionally disabled.
8. **Doctor dashboard** (`runtime/doctor_dashboard.py`): unifies preflight, avatar, world, state authority, Pub Manager, bridge, motion, AI, session, persistence, lifecycle, capabilities, and legacy inventory.
9. **Legacy containment scan** (`runtime/legacy_containment.py`): inventories startup-path candidates without moving, deleting, or renaming files.
10. **System-level Jeeves** (`runtime/jeeves_service.py`): owns the spine-wide `active`, `holding`, `hibernated`, `off`, and `protected` policy so CPU/RAM decisions happen above individual engines while engines remain adapters.

## New routes

- `/api/spine/status`
- `/api/spine/preflight`
- `/api/spine/contracts`
- `/api/spine/lifecycle`
- `/api/spine/capabilities`
- `/api/spine/state/status`
- `/api/spine/state/snapshot`
- `/api/spine/jeeves/status`
- `/api/spine/jeeves/touch`
- `/api/spine/jeeves/evaluate`
- `/api/spine/pub-manager/status`
- `/api/spine/pub-manager/evaluate`
- `/api/spine/avatars/status`
- `/api/spine/world/status`
- `/api/spine/world/move-avatar`
- `/api/spine/bridge/status`
- `/api/spine/motion/status`
- `/api/spine/ai/status`
- `/api/spine/ai/route`
- `/api/spine/session/status`
- `/api/spine/session/save`
- `/api/spine/doctor`
- `/api/spine/legacy/status`
- `/api/spine/boot-order`
- `/api/spine/governance`
- `/api/spine/events`

## Validation

The PowerShell runtime preflight now includes spine checks for:

- spine package/service files
- `main.py` spine attachment and route installation
- bridge, motion, AI, session, doctor, and legacy status routes
- state authority status route, contract, committed transaction event, and canonical namespaces
- Pub Manager service, contract, status/evaluate routes, establishment modes, event, and doctor section
- canonical bridge events
- canonical motion state declaration
- AI direct-control denial
- snapshot import/export policy
- snapshot label sanitization
- baggage classification as contained legacy material
- session/avatar event emission hooks
- system-level Jeeves boot, contract, status routes, and policy events
- Gentle Saver cold-start policy for Voxel bridge and Architect
- legacy room WebSocket client lifecycle/command events
- Studio Control WebSocket broadcasting
- Hub empty-room cleanup

Latest local result:

```text
Summary: 112 pass, 0 warn, 0 fail
```

Python validation now works through the repo venv interpreter. Current local results:

```text
.\.venv\Scripts\python.exe tests\test_pubcast.py
Ran 36 tests in 12.855s
OK

direct tests.test_spine_continuous_job run
12/12 passed
```

Startup smoke confirms `/api/voxel/status` reports the renderer bridge as
present but `holding` under Gentle Saver instead of starting background bridge
loops at boot. Shutdown smoke confirms the ordered shutdown helper closes
currently available lifecycle-capable systems including VoxelBridge and
Alex/Jeremy bridge.

`pytest` itself is still unavailable because package/network install is blocked, so the current reliable lane is `unittest`, `py_compile`, direct spine test calls, and the PowerShell preflight.

## Preserved rules

- Manny and Sheila stay GLB/manifest-owned.
- No sprite fallback was added.
- No legacy files were deleted.
- AI and engines remain late-bound capability providers, not the spine.
- Pub Manager owns establishment-wide policy, not runtime truth or engine execution.
- Jeeves owns system lifecycle policy; engines adapt to it instead of replacing it.
- Ordering is adjusted uniformly through `runtime/boot_order.py` and `runtime/spine_manifest.py`.
