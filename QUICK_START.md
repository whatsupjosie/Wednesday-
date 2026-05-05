# PubCast AI Quick Start

This repo is intended to run as the real PubCast AI application.

## Requirements

- Python 3.10 or newer
- pip
- Optional: Ollama or local GGUF tooling for local model backends
- Optional: cloud API keys for cloud LLM providers

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

On Windows PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Verify the program spine

```bash
python test_v55_integration.py
```

This smoke test checks the entrypoint, required route modules, and Python compilation without requiring paid APIs, local model servers, or avatar assets.

## Start

Linux/macOS:

```bash
./start_pubcast.sh
```

Manual:

```bash
python main.py
```

Alternative:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Local URLs

- Main server: http://localhost:8000
- Health: http://localhost:8000/health
- Airlock/waiting room: http://localhost:8000/airlock
- Static stage, if present: http://localhost:8000/static/stage.html

## Key API surfaces

- `/api/timeline/*` — timeline automation
- `/api/logs/*` — production logs
- `/api/hotspots/*` — hotspot interactions
- `/api/recording/*` — recording pipeline exports
- `/api/governance/waiting-room/*` — airlock entry flow

## Environment variables

Common variables are defined in `modules/appconfig.py`, including:

- `PUBCAST_HOST`
- `PUBCAST_PORT`
- `PUBCAST_DEBUG`
- `PUBCAST_DATA_DIR`
- `PUBCAST_ASSETS_DIR`
- `PUBCAST_STATIC_DIR`
- `STUDIO_MODEL`
- `ARCHITECT_MODEL`

## Notes

This branch treats missing model backends, missing cloud keys, and absent optional avatar/rendering services as optional conditions. They should not prevent the core server spine from being inspected or smoke-tested.
