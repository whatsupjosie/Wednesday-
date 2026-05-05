"""
PubCast AI real-program smoke test.

This file intentionally tests the repository spine without requiring Ollama,
cloud API keys, avatar assets, or a running server.

Run:
    python test_v55_integration.py
"""
from __future__ import annotations

import importlib.util
import py_compile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

REQUIRED_FILES = [
    "main.py",
    "requirements.txt",
    "modules/appconfig.py",
    "modules/timeline_routes.py",
    "modules/structured_log_routes.py",
    "modules/recording_pipeline_routes.py",
    "modules/governance_waiting_room.py",
]

OPTIONAL_BUT_EXPECTED = [
    "README.md",
    "start_pubcast.sh",
    "QUICK_START.md",
    "DEPLOYMENT_CHECKLIST.md",
    "DEBUGGING_REPORT.md",
    "INTEGRATION_COMPLETE.md",
]

IMPORT_PROBES = [
    "modules.appconfig",
    "modules.timeline_routes",
    "modules.structured_log_routes",
    "modules.recording_pipeline_routes",
    "modules.governance_waiting_room",
]


def require_file(path: str) -> None:
    candidate = ROOT / path
    if not candidate.exists():
        raise AssertionError(f"Required file missing: {path}")


def compile_file(path: str) -> None:
    candidate = ROOT / path
    py_compile.compile(str(candidate), doraise=True)


def probe_import(module_name: str) -> None:
    spec = importlib.util.find_spec(module_name)
    if spec is None:
        raise AssertionError(f"Import probe failed, module not found: {module_name}")
    __import__(module_name)


def main() -> int:
    print("PubCast AI real-program smoke test")
    print("Root:", ROOT)

    for path in REQUIRED_FILES:
        require_file(path)
        print("OK required:", path)

    for path in OPTIONAL_BUT_EXPECTED:
        if (ROOT / path).exists():
            print("OK expected:", path)
        else:
            print("WARN expected file missing:", path)

    compile_file("main.py")
    print("OK compile: main.py")

    for module_name in IMPORT_PROBES:
        probe_import(module_name)
        print("OK import:", module_name)

    print("Smoke test complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
