# PubCast Rebuild From Here 5826-337 AM

Created: May 8, 2026, 3:37 AM  
Repo root: `C:\Users\hardc\OneDrive\Documents\Playground\Pubcast codex run`

This document is the recovery map for rebuilding PubCast from the current working point if the repo, machine, branch, zip, or future push goes sideways.

The rule is simple:

> Do not rebuild PubCast by guessing. Rebuild it from the spine outward.

## Current Known Good State

This point includes the permanent runtime spine plus the new Pub Manager correction.

Validated locally:

```powershell
.\.venv\Scripts\python.exe tests\test_pubcast.py
# 36 tests OK

# direct spine test runner
# 12/12 passed

powershell -NoProfile -ExecutionPolicy Bypass -File scripts\pubcast_runtime_preflight.ps1
# Summary: 112 pass, 0 warn, 0 fail
```

Also smoke-tested:

```text
/api/spine/pub-manager/status works
/api/spine/pub-manager/evaluate works
/api/voxel/status reports bridge_lifecycle = holding under Gentle Saver
startup/shutdown smoke passes
```

Known startup warnings that are not rebuild blockers:

- `PUBCAST_JWT_SECRET` is not set, so dev fallback is used.
- CORS is still broad in dev mode.
- `numpy`, Pillow, and OpenCV are missing for optional features.
- `data/bots/sir_purfluous_waiting_room.json` logs Pydantic validation errors.
- `pytest` is not installed; current reliable test lane uses `unittest`, direct spine tests, `py_compile`, and PowerShell preflight.

## The Current Architecture Split

Do not blur these roles again:

- **State Authority**: owns runtime truth and transactions.
- **Pub Manager**: owns establishment-wide operating mode and continuity policy.
- **Jeeves**: owns active/holding/hibernated/off/protected resource housekeeping policy.
- **Pete**: owns local room/show/floor direction.
- **E-Pete/Switchblade**: owns engine/render/inference moment-level judgment.
- **Spine**: owns registration, lifecycle, capabilities, contracts, routes, status, and permission rail.

The key sentence:

> Pub Manager protects continuity, but Pub Manager does not replace State Authority, Jeeves, Pete, E-Pete, or the spine.

## Design Breakthroughs To Preserve

This section is the heart of the rebuild. These are not ordinary features. These are the design moves that made PubCast start turning from a pile of systems into an operating environment.

If PubCast has to be rebuilt, preserve these breakthroughs first.

## How PubCast Works Now, In Plain English

PubCast should be rebuilt as a small operating environment, not as one giant app.

Think of it like this:

```text
Spine = the building wiring
State Authority = the official truth desk
Pub Manager = the establishment manager
Jeeves = the table cleaner / resource governor
Pete = the local show director
E-Pete / Switchblade = the engine/render judgment layer
AI Router = the traffic sign for the two brains
Doctor = the inspector
Legacy Containment = the back room label maker
```

The normal flow:

```text
User/UI/API asks for something
-> spine route receives it
-> State Authority changes truth if truth must change
-> events announce the change
-> world/motion/bridge/AI/session services react
-> doctor/preflight can report what happened
```

The resource flow:

```text
System exists
-> Pub Manager decides establishment mode
-> Jeeves decides active/holding/hibernated/off/protected
-> engines/bridges/AIs adapt
```

The rule:

```text
known by the spine does not mean running
available does not mean warmed
holding does not mean dead
off does not mean deleted
```

That is the whole hibernation/off idea in code.

## One-To-Two Session Rebuild Path

This is the fast practical path. If PubCast goes belly up, follow this before doing any polish.

### Session 1 Goal

Get the spine booting and prove the system still knows who owns what.

Do not fix UI, styling, or optional engine issues in Session 1.

### Session 1 Steps

1. **Copy the damaged/current folder first.**

   Put the copy under `baggage/backups <timestamp>/`.

2. **Confirm Python.**

   Run:

   ```powershell
   .\.venv\Scripts\python.exe --version
   ```

   If that fails, rebuild `.venv` from:

   ```text
   C:\Users\hardc\OneDrive\Documents\Playground\Python312\python.exe
   ```

3. **Restore or verify these folders/files exist.**

   ```text
   main.py
   modules/
   runtime/
   scripts/pubcast_runtime_preflight.ps1
   tests/test_pubcast.py
   tests/test_spine_continuous_job.py
   assets/avatar/
   data/avatars/manifest.json
   docs/recovery/
   ```

4. **Check spine attachment in `main.py`.**

   Required:

   ```python
   SPINE_REGISTRY = attach_spine(app, root=Path(__file__).resolve().parent)
   install_spine_routes(app)
   ```

5. **Run compile.**

   ```powershell
   .\.venv\Scripts\python.exe -m py_compile main.py runtime\pub_manager.py runtime\state_authority.py runtime\boot_sequence.py runtime\contracts.py runtime\boot_order.py runtime\capabilities.py runtime\doctor_dashboard.py
   ```

6. **Run the spine tests.**

   ```powershell
   @'
   import tests.test_spine_continuous_job as t
   for name in sorted(n for n in dir(t) if n.startswith("test_")):
       getattr(t, name)()
       print("PASS", name)
   '@ | .\.venv\Scripts\python.exe -
   ```

   Expected:

   ```text
   12 spine tests pass
   ```

7. **Run preflight.**

   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\pubcast_runtime_preflight.ps1
   ```

   Expected:

   ```text
   Summary: 112 pass, 0 warn, 0 fail
   ```

Session 1 is done when:

```text
runtime spine attaches
State Authority exists
Pub Manager exists
Jeeves exists
doctor/preflight passes
VoxelBridge stays holding under Gentle Saver
AI direct control is denied
```

If only Session 1 succeeds, PubCast is not fully polished, but the rebuild is alive.

### Session 2 Goal

Prove the app shell, resource behavior, shutdown, and main workflows still behave.

### Session 2 Steps

1. **Run the broader unittest suite.**

   ```powershell
   .\.venv\Scripts\python.exe tests\test_pubcast.py
   ```

   Expected:

   ```text
   36 tests OK
   ```

2. **Smoke the app without a browser.**

   ```powershell
   @'
   from fastapi.testclient import TestClient
   import main

   with TestClient(main.app) as client:
       assert client.get("/api/spine/pub-manager/status").status_code == 200
       result = client.post("/api/spine/pub-manager/evaluate", json={"mode": "quiet"})
       assert result.status_code == 200
       assert result.json()["decision"]["mode"] == "quiet"
       voxel = client.get("/api/voxel/status").json()
       assert voxel["bridge_lifecycle"] == "holding"
   print("startup/pub-manager/voxel smoke ok")
   '@ | .\.venv\Scripts\python.exe -
   ```

3. **Check the key status routes manually if needed.**

   ```text
   /api/spine/status
   /api/spine/state/status
   /api/spine/pub-manager/status
   /api/spine/jeeves/status
   /api/spine/ai/status
   /api/spine/doctor
   /api/voxel/status
   ```

4. **Only after those pass, test UI pages.**

   ```text
   /static/doctor.html
   /static/stage.html
   /static/studio_control_room.html
   /static/avatar_motion_lab.html
   /static/avatar_walk_test.html
   ```

Session 2 is done when:

```text
tests pass
startup smoke passes
shutdown smoke passes
doctor route reports spine sections
VoxelBridge is holding, not looping
Architect is cold on Gentle Saver
```

Only then start polish or push work.

## Quick Mental Model For Future Codex/Claude/Gemini

If another AI is helping rebuild, give it this rule:

```text
Do not invent a new center.
Recover the existing center.
The center is the runtime spine.
```

Then tell it:

```text
State Authority is truth.
Pub Manager is establishment policy.
Jeeves is resource housekeeping.
AI Router separates persona and engine advice.
No AI gets direct control.
VoxelBridge is allowed to be present but holding.
Doctor/preflight proves the rebuild.
```

If the assistant starts by redesigning everything, stop it. The rebuild is not a brainstorming session. It is a spine restoration.

## Fast Rebuild Checklist

Use this as the short version.

```text
[ ] Backup folder into baggage
[ ] Confirm .venv Python
[ ] Restore runtime/
[ ] Restore main.py spine attach
[ ] Restore scripts/pubcast_runtime_preflight.ps1
[ ] Restore tests/test_spine_continuous_job.py
[ ] Restore tests/test_pubcast.py
[ ] Compile core Python files
[ ] Run spine tests: expect 12/12
[ ] Run preflight: expect 112 pass
[ ] Run test_pubcast.py: expect 36 OK
[ ] Smoke Pub Manager route
[ ] Smoke Voxel status: expect holding
[ ] Confirm Architect disabled under low profile
[ ] Confirm AI router direct_control_granted is false
[ ] Only then do UI/browser polish
```

## If A Step Fails

Use this triage:

```text
Python fails
-> repair .venv first

runtime import fails
-> restore runtime/ package before touching UI

spine routes missing
-> check runtime/boot_sequence.py and main.py attach/install calls

State Authority missing
-> restore runtime/state_authority.py before world/avatar changes

Pub Manager missing
-> restore runtime/pub_manager.py and boot_sequence registration

preflight fails
-> read the failed check name; do not guess

VoxelBridge starts loops on low profile
-> check modules/performance_manager.py and main.py bridge_autoconnect logic

Architect loads on low profile
-> check modules/llm_orchestrator.py and architect_enabled profile logic

AI direct control becomes true
-> stop; restore runtime/ai_router_service.py policy
```

### Breakthrough 1: PubCast Became A Runtime Nervous System

Old shape:

```text
many systems
many globals
many routes
many local assumptions
```

New shape:

```text
spine
-> registered systems
-> declared contracts
-> lifecycle states
-> capabilities
-> canonical status
-> doctor/preflight
```

Why this matters:

PubCast is no longer just a FastAPI app with modules attached. It now has a runtime nervous system where subsystems must announce what they are, what they provide, and how they report health.

What to preserve:

```text
runtime/app_registry.py
runtime/boot_sequence.py
runtime/contracts.py
runtime/boot_order.py
runtime/capabilities.py
runtime/lifecycle.py
runtime/doctor_dashboard.py
```

Do not rebuild by adding new globals directly to `main.py` unless they also register into the spine.

Failure sign:

```text
"It works, but only because main.py knows every secret."
```

That means the spine design has been lost.

### Breakthrough 2: State Authority Separates Truth From Noise

This is one of the most important design decisions.

Bad pattern:

```text
events become truth
websockets become truth
frontend state becomes truth
service side effects become truth
```

PubCast pattern:

```text
State Authority owns truth.
Events announce truth changes.
Services react to truth changes.
```

The special part is not just having state. The special part is declaring that events are not truth.

What to preserve:

```text
runtime/state_authority.py
```

Core idea:

```text
begin transaction
-> mutate canonical session state
-> emit canonical events
-> commit
-> increment revision
-> state.transaction.committed
```

Why this matters:

This prevents future weirdness like:

- avatar moved but room did not update
- UI thinks a thing happened but persistence missed it
- AI acts on stale world state
- replay/save cannot reconstruct what happened
- services disagree about which room is real

Failure sign:

```text
"The websocket said it happened, so it happened."
```

That is wrong. The state authority says whether it happened.

### Breakthrough 3: Pub Manager Is A New Role, Not A Rename

Pub Manager is not State Authority. Pub Manager is not Jeeves. Pub Manager is not Pete.

The breakthrough is the separation:

```text
State Authority protects truth.
Pub Manager protects continuity.
Jeeves protects order/resources.
Pete protects local flow.
E-Pete/Switchblade protects engine judgment.
```

Pub Manager exists because PubCast is becoming an establishment, not just a room.

Pub Manager answers questions like:

```text
Should the establishment admit more load?
Should background systems quiet down?
Are we open, quiet, busy, crowded, recovering, or in emergency?
Should new engine work be deferred?
Should Jeeves hibernate idle systems?
```

What to preserve:

```text
runtime/pub_manager.py
```

Current modes:

```text
open
quiet
busy
crowded
maintenance
recovery
emergency
```

Why this matters:

Without Pub Manager, Pete becomes overloaded and turns into the whole building manager, front desk, safety inspector, resource governor, and show director. That would eventually make Pete brittle.

Failure sign:

```text
"Pete decides all global resource and admission policy."
```

That is the old trap. Pete should be powerful locally, not responsible for the whole establishment.

### Breakthrough 4: Present Is Not Active

This is the small sentence that protects the old machine.

Bad pattern:

```text
registered = active
available = running
installed = warmed
```

PubCast pattern:

```text
present
available
holding
active
hibernated
off
```

This is why VoxelBridge can exist without starting renderer loops. This is why Architect can exist without loading at startup. This is why future systems can be known by the spine without eating CPU/RAM.

What to preserve:

```text
runtime/jeeves_service.py
modules/performance_manager.py
modules/bridge_bulletproof.py
modules/llm_orchestrator.py
main.py /api/voxel/status bridge_lifecycle
```

Current proof:

```json
{
  "bridge": true,
  "bridge_status": "disconnected",
  "bridge_lifecycle": "holding",
  "bridge_autoconnect": false
}
```

Why this matters:

This is the code version of the hibernation/off distinction Joshua kept pushing for. A system may be nearby and remembered without being awake and burning resources.

Failure sign:

```text
"The bridge exists, so start its loops."
```

That is wrong under Gentle Saver.

### Breakthrough 5: Jeeves Became A System-Level Resource Governor

Jeeves is not just cleanup.

Jeeves is the table-cleaner and shelf-keeper for runtime resources.

Jeeves states:

```text
active
holding
hibernated
off
protected
```

The breakthrough is applying the Switchblade principle system-wide:

```text
Spend compute on what matters right now, not on what merely exists.
```

Switchblade handles moment-level engine judgment.

Jeeves handles seconds/minutes-level whole-system resource posture.

What to preserve:

```text
runtime/jeeves_service.py
```

Why this matters:

PubCast is being built for an older machine and a complex multi-system future. Without Jeeves, background systems slowly become permanent drag.

Failure sign:

```text
"Everything stays on standby forever just in case."
```

That is exactly what this architecture was designed to avoid.

### Breakthrough 6: Dual AI Became Governed, Not Just Available

The special part is not that PubCast has two AIs.

The special part is that the two AIs are separated by role, capability, lifecycle, and permission.

Studio:

```text
persona
speech
character
guest interaction
user-facing expression
```

Architect / Engine Brain:

```text
planning
resource advice
scene advice
code/design thinking
engine recommendations
```

Neither gets direct control.

The spine router returns:

```json
{
  "direct_control_granted": false
}
```

What to preserve:

```text
runtime/ai_router_service.py
modules/inference.py
modules/llm_orchestrator.py
modules/performance_manager.py
```

Why this matters:

This prevents the AI systems from becoming secret engine controllers or hidden state mutators. They advise through the spine.

Failure sign:

```text
"Architect says move the avatar, so the engine moves it directly."
```

Wrong. Architect may recommend. The spine decides. State Authority mutates truth. Services execute through declared paths.

### Breakthrough 7: Gentle Saver Is A First-Class Architecture Choice

Gentle Saver is not just a performance setting. It is a product philosophy.

It means PubCast can boot on weaker hardware without waking everything.

Current low profile:

```text
studio_warmup_enabled = false
studio_keep_alive = 30s
architect_enabled = false
architect_keep_alive = 0
voxel_bridge_autoconnect = false
voxel_bridge_allow_emergency_fallback = false
```

What to preserve:

```text
modules/performance_manager.py
```

Why this matters:

This machine-aware design is what keeps PubCast from becoming a beautiful program that cannot actually run on Joshua's computer.

Failure sign:

```text
"Boot should warm every smart system so it feels ready."
```

That is wrong for this build. Readiness is not the same as resource consumption.

### Breakthrough 8: Legacy Containment Without Destruction

PubCast has old paths, experiments, patches, examples, and baggage. The breakthrough was not deleting them. The breakthrough was making them stop pretending to be canonical.

Pattern:

```text
canonical
late_bound
legacy
experimental
contained
disposal_candidate
```

What to preserve:

```text
runtime/legacy_containment.py
baggage/
rubish/
docs/debug/PUBCAST_DEBUG_LEDGER.md
```

Why this matters:

This lets the project keep useful history without letting old startup paths quietly take authority again.

Failure sign:

```text
"This old file still starts something important, maybe."
```

That means legacy containment failed.

### Breakthrough 9: Doctor/Preflight Became The Project Memory

The doctor/preflight system is not merely testing. It is the project remembering what must remain true.

Current preflight checks:

```text
spine files exist
routes exist
contracts exist
Pub Manager exists
State Authority exists
Jeeves exists
AI direct control is denied
VoxelBridge stays cold under Gentle Saver
Manny/Sheila GLB sprite guard remains intact
shutdown coverage remains visible
```

What to preserve:

```text
scripts/pubcast_runtime_preflight.ps1
runtime/doctor_dashboard.py
static/doctor.html
modules/doctor.py
```

Why this matters:

Every time the system gets bigger, the doctor becomes the lantern. It tells future Joshua, Codex, Claude, or Gemini what cannot silently regress.

Failure sign:

```text
"The app starts, so it is probably fine."
```

No. Run the doctor/preflight.

### Breakthrough 10: The App Can Grow Without Flattening The Multi-Engine Design

The architecture deliberately avoids turning everything into one god object.

Do not flatten:

```text
Pub Manager
Pete
E-Pete
Switchblade
Jeeves
State Authority
AI Router
VoxelBridge
Unity Bridge
Motion
World
Persistence
```

Each has a different job.

Why this matters:

PubCast is heading toward a multi-room, multi-engine, AI-assisted production environment. Flattening the architecture would feel simpler for one week and then become impossible to debug.

Failure sign:

```text
"Let's just have one manager call everything directly."
```

That is how the project collapses back into a monolith.

## Dual AI / Two-Brain Rebuild Detail

This system does not merely "have two AIs." It has two different AI roles with different permissions.

### Brain 1: Studio / Persona Brain

Spine name:

```text
studio_brain
```

Role:

```text
persona
```

Purpose:

- speech
- character interaction
- guest experience
- hosting tone
- fast conversational response
- user-facing language

Current implementation path:

```text
modules/inference.py
-> modules/llm_orchestrator.py
-> Ollama Studio model
```

Default model:

```text
ministral-pubcast:3b
```

Relevant environment variables:

```text
OLLAMA_HOST
OLLAMA_MODEL
STUDIO_MODEL
OLLAMA_KEEP_ALIVE
OLLAMA_TIMEOUT
```

Important rule:

> Studio may speak and advise, but Studio does not own runtime truth, engine execution, room movement, or save state.

### Brain 2: Architect / Engine Brain

Spine name:

```text
engine_brain
architect_brain
```

Why both names appear:

- `engine_brain` is the spine router identity in `runtime/ai_router_service.py`.
- `architect_brain` is the capability/contract identity for the slower planning brain.

Role:

```text
engine
```

Purpose:

- resource advice
- render/engine advice
- scene planning
- code planning
- structured problem solving
- second-pass analysis

Current implementation path:

```text
modules/inference.py
-> modules/llm_orchestrator.py
-> Architect route
```

Architect may run through either:

```text
Ollama model: gemma4-compute-q5:e2b
```

or a local GGUF path:

```text
PUBCAST_ARCHITECT_MODEL
```

Relevant environment variables:

```text
ARCHITECT_MODEL
ARCHITECT_KEEPALIVE
ARCHITECT_TIMEOUT_S
PUBCAST_ARCHITECT_MODEL
PUBCAST_ARCHITECT_CTX
PUBCAST_ARCHITECT_THREADS
PUBCAST_ARCHITECT_GPU_LAYERS
```

Important rule:

> Architect may plan and advise, but Architect does not directly control engines, mutate State Authority, or bypass Pub Manager/Jeeves.

### AI Router Truth

The spine-owned AI router lives here:

```text
runtime/ai_router_service.py
```

It declares:

```text
studio_brain -> persona
engine_brain -> engine
```

The router returns:

```json
{
  "direct_control_granted": false
}
```

That field matters. If a rebuild ever returns `true` there, the rebuild is wrong.

AI routing event:

```text
ai.request.routed
```

The router rule:

> Persona AI and engine AI may advise/request; neither owns runtime truth or direct engine execution outside the spine.

### Inference Route Names

`modules/inference.py` accepts these route names:

```text
studio
architect
architect_then_studio
auto
dual
two_pass
plan
express
character
```

Canonical mapping:

```text
auto                  -> studio
studio                -> studio
architect             -> architect
architect_then_studio -> architect_then_studio
dual                  -> architect_then_studio
two_pass              -> architect_then_studio
plan                  -> architect
express               -> studio
character             -> studio
```

Complex task hints may bump ambiguous requests to:

```text
architect_then_studio
```

Complex hints include:

```text
analysis
planning
structured_data
troubleshoot
explain
recommend
escalation
```

### Two-Pass Behavior

For:

```text
architect_then_studio
dual
two_pass
```

The intended pattern is:

```text
Architect drafts/plans
-> Studio voices/translates for the user/show
```

This is not the same as letting Architect run the show. Architect produces advice. Studio produces user-facing expression. The spine remains the rail.

### Performance Profiles For Dual AI

The profile source is:

```text
modules/performance_manager.py
```

Current default:

```text
low
```

Low / Gentle Saver:

```text
studio_warmup_enabled = false
studio_keep_alive = 30s
architect_enabled = false
architect_keep_alive = 0
architect_max_concurrency = 1
architect_timeout_s = 6
```

Meaning:

- Studio can be used if available, but it is not warmed at boot.
- Architect is not loaded at boot.
- Requests for Architect fall back to Studio with:

```text
fallback_reason = profile_architect_disabled
```

Medium:

```text
studio_warmup_enabled = false
studio_keep_alive = 2m
architect_enabled = true
architect_keep_alive = 0
architect_max_concurrency = 1
architect_timeout_s = 12
```

High:

```text
studio_warmup_enabled = true
studio_keep_alive = 10m
architect_enabled = true
architect_keep_alive = 0
architect_max_concurrency = 1
architect_timeout_s = 16
```

Meaning:

- Medium permits Architect but keeps Studio warmup off.
- High permits Architect and allows Studio warmup.
- Architect keepalive remains `0` so it does not sit around consuming memory after use.

### Pub Manager And Dual AI

Pub Manager owns establishment posture:

```text
open
quiet
busy
crowded
maintenance
recovery
emergency
```

Pub Manager should eventually influence AI policy like this:

```text
open        -> normal routing
quiet       -> prefer Studio, defer nonessential Architect work
busy        -> restrict Architect to essential planning
crowded     -> Studio only unless recovery/safety requires Architect
maintenance -> Architect allowed for diagnostics, no guest-facing show flow
recovery    -> Architect allowed for recovery planning only
emergency   -> critical safety/recovery advice only
```

Current state:

- Pub Manager is installed and can declare mode.
- The AI router is installed and declares the two-brain policy.
- Performance profiles already enforce the low-machine behavior.
- Pub Manager does not yet dynamically throttle actual LLM calls by mode. That is a next-step integration.

### Jeeves And Dual AI

Jeeves owns resource states:

```text
active
holding
hibernated
off
protected
```

The intended AI mapping:

```text
Studio recently used -> holding
Studio speaking now -> active
Architect disabled by Gentle Saver -> off
Architect may be used soon -> holding
Architect after response -> off or hibernated
```

This is the same principle as the VoxelBridge fix:

> Present does not mean active.

### Dual AI Rebuild Tests

The current regression coverage is in:

```text
tests/test_pubcast.py
tests/test_spine_continuous_job.py
```

Important test expectations:

```text
Low profile keeps Architect cold at startup.
AI router separates persona and engine roles.
Neither AI receives direct control.
Architect-disabled requests fall back to Studio.
```

If rebuilding, confirm:

```powershell
.\.venv\Scripts\python.exe tests\test_pubcast.py
```

and:

```powershell
@'
import tests.test_spine_continuous_job as t
for name in sorted(n for n in dir(t) if n.startswith("test_")):
    getattr(t, name)()
    print("PASS", name)
'@ | .\.venv\Scripts\python.exe -
```

### Dual AI Failure Signs

The rebuild is wrong if:

- Architect loads on startup while the active profile is `low`.
- Studio warmup runs on startup while the active profile is `low`.
- `direct_control_granted` ever returns `true`.
- AI mutates room/avatar/session state without State Authority.
- AI talks directly to VoxelBridge, EVO, Unity, or recording controls.
- Pub Manager becomes an AI persona.
- Pete becomes responsible for all global AI/resource policy.
- Architect responses are treated as commands instead of advice.

## Files That Matter Most

If rebuilding from a partial copy, recover these first.

### Runtime Spine

```text
runtime/app_registry.py
runtime/event_bus.py
runtime/session_state.py
runtime/state_authority.py
runtime/lifecycle.py
runtime/capabilities.py
runtime/contracts.py
runtime/boot_order.py
runtime/spine_governor.py
runtime/jeeves_service.py
runtime/pub_manager.py
runtime/avatar_service.py
runtime/world_service.py
runtime/bridge_service.py
runtime/motion_service.py
runtime/ai_router_service.py
runtime/persistence_service.py
runtime/doctor_dashboard.py
runtime/legacy_containment.py
runtime/boot_sequence.py
runtime/spine_manifest.py
runtime/service_status.py
```

### Main App Wiring

```text
main.py
```

Required spine wiring in `main.py`:

```python
from runtime.boot_sequence import attach_spine, install_spine_routes

SPINE_REGISTRY = attach_spine(app, root=Path(__file__).resolve().parent)
install_spine_routes(app)
```

The current `main.py` also includes:

- ordered shutdown helper
- Voxel bridge holding/cold-start policy
- `/api/voxel/status` with `bridge_lifecycle`
- session/avatar event emission hooks

### Resource Policy

```text
modules/performance_manager.py
modules/llm_orchestrator.py
modules/bridge_bulletproof.py
modules/inference.py
runtime/ai_router_service.py
runtime/pub_manager.py
```

Important behavior:

- Gentle Saver profile is `low`.
- Gentle Saver disables Studio warmup.
- Gentle Saver keeps Architect disabled/cold.
- Gentle Saver keeps VoxelBridge present but holding.
- Cold VoxelBridge refuses queue work instead of pretending a renderer loop exists.

### Core Regression Tests

```text
tests/test_pubcast.py
tests/test_spine_continuous_job.py
scripts/pubcast_runtime_preflight.ps1
```

### Recovery Docs

```text
docs/PUBCAST_CONTINUOUS_SPINE_JOB.md
docs/debug/PUBCAST_DEBUG_LEDGER.md
docs/debug/STABILIZATION_RUNBOOK.md
docs/recovery/PubCast Rebuild From Here 5826-337 AM.md
```

## Backup Rules

Never use destructive cleanup as a recovery step.

Do not run:

```powershell
git reset --hard
git clean -fd
Remove-Item -Recurse
```

Unless Joshua explicitly asks for that exact destructive operation.

Use these folders:

```text
baggage/
```

For useful carried material:

- backups
- patches
- downloads to install
- handoffs
- context packs
- zip archives
- immediate program backups

```text
rubish/
```

Only for disposal candidates Joshua will review later.

Never put important backups in `rubish` unless Joshua explicitly says to.

## If Everything Goes Belly Up

### Step 1: Freeze The Current Folder

Before rebuilding, make a folder-level copy of:

```text
C:\Users\hardc\OneDrive\Documents\Playground\Pubcast codex run
```

Put the copy under:

```text
C:\Users\hardc\OneDrive\Documents\Playground\Pubcast codex run\baggage\backups <timestamp>\
```

Use title-first timestamps, for example:

```text
PubCast Full Folder Backup 5826-337 AM
```

### Step 2: Confirm Python

The current working Python is:

```text
C:\Users\hardc\OneDrive\Documents\Playground\Python312\python.exe
```

The repo venv should be:

```text
C:\Users\hardc\OneDrive\Documents\Playground\Pubcast codex run\.venv\Scripts\python.exe
```

Check:

```powershell
.\.venv\Scripts\python.exe --version
```

If `.venv` is broken, rebuild it from the working Python:

```powershell
C:\Users\hardc\OneDrive\Documents\Playground\Python312\python.exe -m venv .venv
.\.venv\Scripts\python.exe -m pip --version
```

If package install is blocked, do not panic. The current validation path does not require `pytest`.

### Step 3: Run The Minimal Validation Ladder

Run these from repo root:

```powershell
.\.venv\Scripts\python.exe -m py_compile main.py modules\performance_manager.py modules\bridge_bulletproof.py modules\llm_orchestrator.py runtime\pub_manager.py runtime\boot_sequence.py runtime\contracts.py runtime\boot_order.py runtime\capabilities.py runtime\doctor_dashboard.py tests\test_pubcast.py tests\test_spine_continuous_job.py
```

```powershell
.\.venv\Scripts\python.exe tests\test_pubcast.py
```

```powershell
@'
import traceback
import tests.test_spine_continuous_job as t

tests = [name for name in dir(t) if name.startswith("test_")]
failures = []
for name in tests:
    try:
        getattr(t, name)()
        print(f"PASS {name}")
    except Exception as exc:
        print(f"FAIL {name}: {exc}")
        traceback.print_exc()
        failures.append(name)
print(f"{len(tests)-len(failures)}/{len(tests)} passed")
raise SystemExit(1 if failures else 0)
'@ | .\.venv\Scripts\python.exe -
```

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\pubcast_runtime_preflight.ps1
```

Expected results at this recovery point:

```text
test_pubcast.py: 36 tests OK
test_spine_continuous_job: 12/12 passed
preflight: 112 pass, 0 warn, 0 fail
```

### Step 4: Smoke The App Without A Browser

Use `TestClient`:

```powershell
@'
from fastapi.testclient import TestClient
import main

with TestClient(main.app) as client:
    assert client.get("/api/spine/pub-manager/status").status_code == 200
    result = client.post("/api/spine/pub-manager/evaluate", json={"mode": "quiet"})
    assert result.status_code == 200
    assert result.json()["decision"]["mode"] == "quiet"
    voxel = client.get("/api/voxel/status").json()
    assert voxel["bridge_lifecycle"] == "holding"
print("startup/pub-manager/voxel smoke ok")
'@ | .\.venv\Scripts\python.exe -
```

Expected:

```text
startup/pub-manager/voxel smoke ok
```

## Rebuild Order From Blank Or Partial Repo

If starting from a damaged copy, do not start with UI polish. Rebuild in this order.

### Phase 1: Restore The Old App Shell

Recover:

```text
main.py
requirements.txt
modules/
static/
assets/
data/avatars/manifest.json
doctor/
config/
```

The app does not need every optional dependency to boot, but it does need the shape of those folders.

### Phase 2: Restore The Runtime Spine

Restore the `runtime/` package.

Minimum boot order:

```text
settings
registry
event_bus
session_state
state_authority
lifecycle
capabilities
jeeves
pub_manager
spine_contracts
boot_order
spine_governor
preflight
doctor_dashboard
asset_manifest
avatar_system
world_system
bridge_system
motion_system
ai_router
persistence
legacy_containment
ai_policy
engine_policy
spine_governance
```

The actual boot order lives in:

```text
runtime/boot_order.py
```

### Phase 3: Wire Routes Through `runtime/boot_sequence.py`

At minimum, the rebuilt app should expose:

```text
/api/spine/status
/api/spine/preflight
/api/spine/contracts
/api/spine/lifecycle
/api/spine/capabilities
/api/spine/state/status
/api/spine/state/snapshot
/api/spine/jeeves/status
/api/spine/jeeves/touch
/api/spine/jeeves/evaluate
/api/spine/pub-manager/status
/api/spine/pub-manager/evaluate
/api/spine/avatars/status
/api/spine/world/status
/api/spine/world/move-avatar
/api/spine/bridge/status
/api/spine/motion/status
/api/spine/ai/status
/api/spine/ai/route
/api/spine/session/status
/api/spine/session/save
/api/spine/doctor
/api/spine/legacy/status
/api/spine/boot-order
/api/spine/governance
/api/spine/events
```

### Phase 4: Restore State Authority Before Pub Manager

State Authority must exist before Pub Manager.

State Authority does:

- canonical event namespace validation
- runtime state class declaration
- transactions
- avatar registration/movement mutation
- current room mutation
- state revision tracking
- `state.transaction.committed`

Pub Manager does:

- establishment mode
- establishment policy
- continuity posture
- mode evaluation event
- no direct engine control

Do not merge those two roles.

### Phase 5: Restore Jeeves

Jeeves must expose:

```text
active
holding
hibernated
off
protected
```

Jeeves owns resource posture, not truth.

### Phase 6: Restore World Movement Transaction Path

Avatar movement should go through:

```text
world_service.move_avatar()
-> state_authority.begin_transaction()
-> transaction.move_avatar()
-> transaction.emit(room.left)
-> transaction.emit(room.entered)
-> transaction.emit(avatar.moved)
-> transaction.emit(world.state.changed)
-> commit()
-> state.transaction.committed
```

If movement bypasses State Authority, the rebuild is wrong.

### Phase 7: Restore Resource-Saver Startup

Gentle Saver must not eagerly wake expensive systems.

Expected low profile behavior:

```text
studio_warmup_enabled = False
studio_keep_alive = 30s
architect_enabled = False
voxel_bridge_autoconnect = False
voxel_bridge_allow_emergency_fallback = False
```

VoxelBridge should exist but report:

```json
{
  "bridge": true,
  "bridge_status": "disconnected",
  "bridge_lifecycle": "holding",
  "bridge_autoconnect": false
}
```

### Phase 8: Restore Shutdown

Shutdown should include an ordered helper in `main.py` until this moves into the spine lifecycle registry.

Current covered systems:

```text
mocap
timeline_player
studio_control
voxel_bridge
unity_bridge
conversation_orchestrator
evo_orchestrator
avatar_studio
alex_bridge
alex_core
universal_memory
memory_ingestor
security_spine
surface_manager
choreo_controller
vault
cricket_keeper
```

Long-term improvement:

Move shutdown adapters into the lifecycle registry so this list does not stay hand-built in `main.py`.

## What To Fix Next After Rebuild

Do these after the rebuild is passing validation:

1. Fix `data/bots/sir_purfluous_waiting_room.json` schema errors.
2. Add explicit Jeeves warm/restore endpoint for VoxelBridge live renderer moments.
3. Move shutdown ownership from `main.py` into spine lifecycle service.
4. Expose dual-AI and bridge resource posture in Pub Manager/doctor status.
5. Add route collision tests for recording and old timeline surfaces.
6. Install/restore `pytest` once package access works.
7. Browser-smoke key pages only after backend validation is green.

## What Not To Do

Do not:

- replace Manny or Sheila GLB with sprites
- let AI directly control engines
- let Pub Manager mutate runtime truth directly
- let events become truth
- let VoxelBridge start background loops under Gentle Saver
- flatten Pete/E-Pete/Jeeves/Pub Manager into one boss object
- delete old files
- force-push until a new repo remote is confirmed

## New Repo / Force Push Preparation

Before pushing to a new repo:

1. Create the update zip first.
2. Confirm the new remote URL.
3. Create a fresh branch or clean repo target.
4. Review what is intentionally included.
5. Exclude environment/runtime debris:

```text
.venv/
.codex_python_temp/
.codex_test_scratch/
__pycache__/
*.pyc
data/users.db
data/logs/
data/emergency_bridge/
```

6. Include source/docs/tests/spine files.
7. Only then commit/push.

Do not force-push over an existing repo unless Joshua explicitly says the target repo is disposable.

## Recovery Mantra

If confused, rebuild this order:

```text
Python
-> main app shell
-> runtime spine
-> State Authority
-> Jeeves
-> Pub Manager
-> world/avatar movement
-> bridge/motion/AI/session/persistence
-> doctor/preflight
-> validation
-> UI polish
```

The spine is the rail. Everything else plugs into it.
