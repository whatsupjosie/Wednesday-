# PubCast AI Real Program Audit

Date: 2026-05-05
Repo: whatsupjosie/Wednesday-

This repository is being treated as the real PubCast AI program, not a loose archive.

Confirmed spine:

- main.py is the FastAPI application entrypoint.
- requirements.txt is the Python dependency manifest.
- start_pubcast.sh is the shell startup path.
- modules/timeline_routes.py provides timeline automation routes.
- modules/structured_log_routes.py provides production log routes.
- modules/recording_pipeline_routes.py provides recording export routes.
- modules/governance_waiting_room.py provides the waiting room and airlock routes.

Current stabilization notes:

- README describes a v5.5 package.
- main.py also contains v5.6-era startup language and systems.
- Treat this as a v5.5/v5.6 stabilization snapshot until version metadata is normalized.
- The repo should boot even when optional local services, models, avatars, or cloud keys are absent.

Definition of real for this branch:

1. Dependencies install from requirements.txt.
2. main.py compiles.
3. Startup files and README point to files that actually exist.
4. A smoke test exists and can verify the program spine without requiring paid APIs or local model servers.
5. Missing optional systems degrade gracefully instead of hiding fatal entrypoint errors.

Next hardening targets:

- Add Windows PowerShell startup/check script.
- Add CI for compile and smoke checks.
- Normalize version labels across README, startup scripts, and main.py.
- Audit main.py imports against files present in modules/.
- Promote this branch only after local runtime evidence confirms /health and core pages respond.
