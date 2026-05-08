# PubCast Stabilization Runbook

Last updated: 2026-05-08

Use this runbook to stabilize PubCast without diving too deep or deleting
anything. Each system gets five rounds. Stop after the cleanup plan if the
change would be broad or risky.

## Ground Rules

- Do not delete files.
- Back up useful carried material into `baggage/backups <timestamp>/`.
- Move disposal candidates into `rubish/disposal_review_YYYYMMDD/` only after review.
- Treat the dirty worktree as user work.
- Fix only the current system's scoped bugs.
- Record deferred or wider issues in `docs/debug/PUBCAST_DEBUG_LEDGER.md`.

## Validation Ladder

Run in this order. Use the repo venv interpreter explicitly:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\pubcast_runtime_preflight.ps1
.\.venv\Scripts\python.exe -m py_compile main.py modules\*.py
.\.venv\Scripts\python.exe tests\test_pubcast.py
@'
import tests.test_spine_continuous_job as t
for name in sorted(n for n in dir(t) if n.startswith("test_")):
    getattr(t, name)()
    print("PASS", name)
'@ | .\.venv\Scripts\python.exe -
```

When `pytest` becomes available, add:

```powershell
.\.venv\Scripts\python.exe -m pytest --collect-only -q
.\.venv\Scripts\python.exe -m pytest tests\test_boring_guards.py -q
.\.venv\Scripts\python.exe -m pytest tests\test_frontend_contract_compat.py tests\test_frontend_startup_contracts.py -q
```

If `.venv\Scripts\python.exe` fails, do not continue code fixes. Repair the
environment first.

## Five Debug Rounds

For every system:

1. **Inventory**
   - Identify owner files, routes, background tasks, data files, and tests.
   - Record what owns startup and shutdown.

2. **Static Checks**
   - Compile/import if Python works.
   - Search for `create_task`, `while True`, threads, broad `except`, file writes,
     route duplication, and direct globals.

3. **Focused Tests**
   - Run only the tests for that system.
   - If tests are missing, record one focused test to add before refactoring.

4. **Runtime Smoke**
   - Use `TestClient` or a dev server route smoke.
   - For frontend systems, use route-reference tests before browser screenshots.

5. **Cleanup Plan**
   - Mark fixes as `fixed`, `deferred`, or `disposal_candidate`.
   - Move obsolete files only after review, into `rubish/disposal_review_YYYYMMDD/`.

## System Order

1. **Environment And Tooling**
   - Keep `.venv` pinned to the working local interpreter.
   - Lock Python command path.
   - Confirm preflight, collect-only, compile, and focused tests.

2. **Runtime Spine**
   - Keep registry, event bus, session state, lifecycle, capabilities, contracts,
     boot order, spine governor, Jeeves, Pub Manager, and state authority as the canonical rail.
   - Register new systems through the spine; do not move routes without tests.

3. **Startup And Shutdown**
   - Add lifecycle-owned startup/shutdown.
   - Confirm all background workers have owners and cancellation.

4. **Auth And Security**
   - Confirm mutating REST routes have role policy.
   - Decide WebSocket mutation policy.

5. **AI And Inference**
   - Make Studio warmup and keepalive performance-policy controlled.
   - Keep Architect cold/off by default on Gentle Saver.

6. **Memory, Alex, Jeremy**
   - Use snapshot/resurrection as hibernation model.
   - Ensure shutdown is called from app lifecycle.

7. **Hub And WebSockets**
   - Fix room cleanup.
   - Add tests for room cleanup and production-state mutation policy.

8. **Avatars, MoCap, EVO**
   - Preserve current GLB/sprite guard.
   - Add lifecycle ownership for MoCap, avatar performer, EVO, and bridge loops.

9. **Studio, Recording, Timeline**
   - Resolve route ownership.
   - Ensure recording flush/dead-man/timeline tasks stop safely.

10. **PubWorld, Voxel, Bridges**
    - Register bridge capability and lifecycle.
    - Call bridge close/disconnect during shutdown.

11. **Frontend And Static**
    - Run static route-reference tests.
    - Browser-smoke primary pages after backend is stable.

12. **Data And Disposal**
    - Classify untracked reports, backups, logs, runtime data, and generated
      artifacts.
    - Move reviewed clutter into `rubish`, with a manifest.

## First Fix Batch After Environment Repair

1. Add lifecycle shutdown calls for systems that already expose stop/close/shutdown.
2. Add explicit Jeeves restore/warm commands for VoxelBridge live renderer moments.
3. Add route collision tests for recording and remaining timeline surfaces.
4. Expose dual-AI and bridge resource posture through Pub Manager/doctor status.
5. Move more mutating systems through state authority transactions.

## Blockers

- `pytest` is not installed yet; use the explicit venv Python with `unittest`,
  direct spine tests, `py_compile`, and PowerShell preflight until package access
  is available.
- Existing dirty files should not be reverted or overwritten.
- Generated/untracked data should be reviewed, not removed.
