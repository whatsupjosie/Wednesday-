# PubCast AI Deployment Checklist

Use this before calling a branch a runnable PubCast build.

## Local verification

- [ ] Python 3.10+ is installed.
- [ ] Virtual environment created.
- [ ] `pip install -r requirements.txt` completes.
- [ ] `python test_v55_integration.py` completes.
- [ ] `python -m py_compile main.py` completes.
- [ ] `python main.py` starts the server.
- [ ] `/health` responds.

## Files that should exist

- [ ] `main.py`
- [ ] `requirements.txt`
- [ ] `README.md`
- [ ] `QUICK_START.md`
- [ ] `start_pubcast.sh`
- [ ] `test_v55_integration.py`
- [ ] `modules/appconfig.py`
- [ ] `modules/timeline_routes.py`
- [ ] `modules/structured_log_routes.py`
- [ ] `modules/recording_pipeline_routes.py`
- [ ] `modules/governance_waiting_room.py`

## Optional services

These may be missing during a basic smoke test and should degrade gracefully:

- [ ] Ollama
- [ ] GGUF local runner
- [ ] Cloud API keys
- [ ] DeepFace
- [ ] MediaPipe
- [ ] Avatar assets
- [ ] Renderer/GPU bridge

## Runtime evidence to collect

Save these when doing a real local run:

- [ ] terminal startup log
- [ ] `/health` JSON
- [ ] `/api/timeline/status` JSON
- [ ] `/api/logs/recent` JSON
- [ ] screenshot of stage or waiting-room page

## Release rule

Do not merge a stabilization branch into `main` until the smoke test passes and at least one local server boot has been verified.
