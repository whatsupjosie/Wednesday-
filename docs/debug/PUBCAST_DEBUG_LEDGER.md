# PubCast Debug Ledger

Last updated: 2026-05-08

This ledger is the holding table for whole-program stabilization. It separates
environment blockers, confirmed bugs, suspected risks, and disposal candidates.
Do not delete files while working this list. Useful carried material and backups
belong under `baggage/`; obsolete disposal candidates should move into
`rubish/disposal_review_YYYYMMDD/` only after review, with a short note.

## Current Validation State

- `scripts/pubcast_runtime_preflight.ps1`: PASS, 112 pass, 0 warn, 0 fail.
- Python validation: REPAIRED for repo work through
  `.\.venv\Scripts\python.exe`. The venv was rebuilt from
  `C:\Users\hardc\OneDrive\Documents\Playground\Python312\python.exe`.
  `pytest` is still unavailable because network/package install is blocked, so
  current validation uses `unittest`, `py_compile`, direct spine tests, and the
  PowerShell preflight.
- Working tree: DIRTY before this ledger. Treat existing changes as user work.
- Runtime spine: APPLIED. The live repo now has runtime registry, event bus,
  session state, lifecycle, capabilities, governance/boot order, Jeeves, Pub
  Manager, bridge, motion, AI router, persistence, doctor, legacy containment,
  and state authority layers.

## Priority Ledger

| ID | Area | Status | Priority | Evidence | Planned Fix |
| --- | --- | --- | --- | --- | --- |
| DBG-001 | Python environment | fixed | P0 | `.\.venv\Scripts\python.exe tests\test_pubcast.py` runs 36 tests OK; direct spine tests run 12/12; `py_compile` works on touched runtime files. | Keep using explicit venv Python. Install `pytest` later when package access is available, then restore collect-only and pytest groups. |
| DBG-002 | Runtime spine | fixed | P0 | `runtime/` package is present; `scripts/pubcast_runtime_preflight.ps1` reports 112 pass, 0 warn, 0 fail. | Continue adding new systems only through spine registration, contracts, capability declaration, status, and tests. |
| DBG-003 | Shutdown coverage | fixed | P0 | `main.py` now uses an ordered shutdown helper covering mocap, timeline, Studio Control, VoxelBridge, Unity bridge, conversation orchestrator, EVO, avatar studio, Alex bridge/core, memory, security, surface manager, choreo, vault, and cricket. | Later move this list into a spine lifecycle registry so services declare their shutdown adapter instead of living in `main.py`. |
| DBG-004 | Background task ownership | confirmed | P0 | `asyncio.create_task`, `while True`, threads, and watcher loops appear across Hub/WebSockets, LLM warmup, Bridge, MoCap, EVO, room conductor, timeline, logging, vault, recording pipeline, and Studio Control. | Create service ownership map. Every long-running task gets registry owner, lifecycle state, cancellation path, and status endpoint. |
| DBG-005 | Hub room cleanup | fixed | P1 | Regression tests cover disconnect and broadcast pruning for empty room sets. | Keep tests in `tests/test_pubcast.py` as guard rails. |
| DBG-006 | WebSocket production updates | suspected | P1 | `Hub.handle_message()` accepts `production_state` messages over room WebSocket and updates production state outside the normal route auth dependency. | Decide policy: either disable production mutation over public room WS, require authenticated/mod WS identity, or route through a protected control-room channel only. |
| DBG-007 | Dual AI resource policy | fixed | P1 | Gentle Saver disables Studio warmup, sets short Studio keepalive, and keeps Architect cold at startup instead of loading the second brain. | Later expose this in the doctor dashboard as an explicit dual-AI resource posture. |
| DBG-008 | Timeline route ownership | fixed | P1 | `timeline_routes` now uses the `TimelinePlayer` async contract and has a focused route contract test. | Later classify the older `create_timeline_router()` surface as legacy/pending only after route collision review. |
| DBG-009 | Recording route overlap | suspected | P1 | `production_routes.py` exposes `/api/recording/...`; `recording_pipeline_routes.py` also uses prefix `/api/recording`. | Keep production camera/recording session routes canonical in `production_routes.py`; keep pipeline export routes only where they do not shadow production routes. Add route collision test. |
| DBG-010 | Demo/example tails | suspected | P2 | Studio/Voxel/Pete/avatar modules contain embedded example/demo blocks and integration snippets. | Move executable demos to tests or docs only if they affect import/runtime behavior. Otherwise leave as low-risk documentation debt. |
| DBG-011 | Frontend/static route drift | suspected | P1 | Static pages reference many `/api` and `/ws` routes. Python is repaired, but pytest is not installed yet. | Run frontend route-reference tests once pytest is available, then browser-smoke primary pages. |
| DBG-012 | Disposal candidates | confirmed | P2 | Root reports, hotfix scripts, `.bak` files, `dist/`, logs, and generated data are present. | Create dated disposal review folder later. Move only reviewed files, never delete. Keep a manifest for every move. |
| DBG-013 | Resource governor/Jeeves | fixed | P1 | System-level Jeeves is registered as a required kernel service and exposes active/holding/hibernated/off/protected policy. | Next step is engine adapter enforcement and background task lifecycle ownership. |
| DBG-014 | Validation command drift | fixed | P0 | `python` command may still be unreliable, but explicit `.\.venv\Scripts\python.exe` works. | Keep runbook commands pinned to the venv interpreter. |
| DBG-015 | State authority | fixed | P0 | `runtime/state_authority.py` owns transactional truth, canonical event namespaces, runtime state classes, status/snapshot routes, and world movement transactions. | Extend more mutating systems through state authority without letting events or services become truth. |
| DBG-016 | VoxelBridge eager startup | fixed | P1 | Gentle Saver now creates the bridge as present/holding without autoconnect; `/api/voxel/status` reports `bridge_lifecycle: holding`; cold bridge commands are refused instead of queued. | Later add explicit Jeeves restore/warm commands for live renderer moments. |
| DBG-017 | Pub Manager placement | fixed | P0 | `runtime/pub_manager.py` is registered as a required kernel service with establishment modes, `/api/spine/pub-manager/status`, `/api/spine/pub-manager/evaluate`, capability, contract, preflight guard, and doctor section. | Keep Pub Manager declarative. It protects continuity but must not replace State Authority, Jeeves, Pete, or E-Pete. |

## System Risk Map

### Startup And Spine
- `main.py` remains the central app shell and route registry.
- Runtime spine is attached and exposes status, contracts, lifecycle,
  capabilities, boot order, governance, events, Jeeves, Pub Manager, state
  authority, world, bridge, motion, AI, session, persistence, doctor, and legacy
  containment.
- Next success condition is moving shutdown ownership from `main.py` into the
  spine lifecycle registry.

### Auth And Security
- Auth enforcement is environment-gated through `PUBCAST_ENFORCE_AUTH`.
- Many mutating routes already use `require_role("mod")` or `current_identity`.
- Risk remains around WebSocket mutation paths and route modules that may expose
  convenience actions in relaxed mode.

### AI And Inference
- `InferenceManager` is a facade over `LLMOrchestrator`.
- Studio warmup currently starts as a background task without lifecycle owner.
- Architect is mostly resource-conservative already, but the policy should live
  in performance profiles and later Jeeves.

### Memory, Alex, Jeremy
- Alex and Alex/Jeremy bridge have shutdown/snapshot concepts.
- `main.py` now calls Alex bridge/core shutdown; spine lifecycle registration is
  still the cleaner long-term owner.
- This is the model for hibernation/off semantics later.

### Hub And WebSockets
- Hub room cleanup has a confirmed set/list bug.
- Public room WebSocket can update production state.
- ThinkingContext and room watcher tasks should become owned lifecycle tasks.

### Avatars, MoCap, EVO
- Preflight says GLB and sprite guards are currently healthy.
- MoCap, avatar performer, EVO, bridge, and camera managers contain long-running
  loops that need ownership and cancellation review.

### Studio, Recording, Timeline
- Studio Control has live autosave task behavior.
- Recording pipeline has a flush thread.
- Timeline has task-based playback and overlapping route surfaces.

### PubWorld, Voxel, Bridges
- Voxel bridge can start heartbeat, command, and health monitor tasks.
- Bridge shutdown exists and is now called from `main.py`.
- PubWorld has a separate router plus direct `main.py` WebSocket.

### Frontend And Static
- Static route preflight is green for avatar/motion lab contracts.
- Browser-level layout and missing-route tests still need pytest/browser
  coverage once package access is available.

### Data And Files
- Many generated runtime directories are untracked.
- Disposal review must classify files first, then move to `rubish`.

## Status Key

- `confirmed`: directly observed in files or command output.
- `suspected`: evidence exists, but requires tests/runtime confirmation.
- `planned`: known implementation step, not a bug by itself.
- `fixed`: repaired and validated.
- `deferred`: intentionally left for later.
- `disposal_candidate`: safe to review for move-to-rubish, never direct delete.
