"""Non-destructive legacy/startup-path containment scan."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Optional


STARTUP_HINTS = (
    "FastAPI(",
    "uvicorn.run",
    "if __name__ == '__main__'",
    'if __name__ == "__main__"',
    "attach_spine(",
)

CONTAINED_DIR_NAMES = {
    "baggage",
    "legacy",
    "_legacy",
    "experimental",
    "_experimental",
    "rubish",
    "rubbish",
    "rubbish_bin",
    "_rubbish_bin",
}

SKIP_DIR_NAMES = {".git", "__pycache__", ".venv", "venv", "node_modules"}


class LegacyContainmentService:
    def __init__(self, root: Path):
        self.root = Path(root).resolve()
        self.scanned_files = 0
        self.candidates = []
        self.scan()

    def scan(self):
        self.candidates = []
        self.scanned_files = 0
        for path in self.root.rglob("*.py"):
            rel_parts = [part.lower() for part in path.relative_to(self.root).parts]
            if any(part in SKIP_DIR_NAMES for part in rel_parts):
                continue
            self.scanned_files += 1
            rel = path.relative_to(self.root).as_posix()
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")[:20000]
            except Exception:
                continue
            hints = [hint for hint in STARTUP_HINTS if hint in text]
            if not hints:
                continue
            category = "canonical" if rel == "main.py" or rel.startswith("runtime/") else "legacy_or_experimental_candidate"
            if any(part in CONTAINED_DIR_NAMES for part in rel_parts):
                category = "contained_legacy"
            self.candidates.append({"path": rel, "category": category, "hints": hints})

    def status(self):
        uncontained = [item for item in self.candidates if item["category"] == "legacy_or_experimental_candidate"]
        contained = [item for item in self.candidates if item["category"] == "contained_legacy"]
        return {
            "ok": True,
            "service": "legacy_containment",
            "scanned_files": self.scanned_files,
            "summary": {
                "startup_candidates": len(self.candidates),
                "contained_candidates": len(contained),
                "uncontained_candidates": len(uncontained),
            },
            "canonical_startup": "main.py -> runtime.boot_sequence.attach_spine(app)",
            "candidates": self.candidates[:100],
            "recommendation": "Do not delete candidates. Mark or move stale startup paths into baggage/legacy after manual review.",
        }


def register_legacy_containment_service(registry: Any, *, root: Optional[Path] = None) -> LegacyContainmentService:
    svc = LegacyContainmentService(Path(root or Path.cwd()))
    registry.register(
        "legacy_containment",
        svc,
        phase="10_legacy",
        required=False,
        state="ready",
        message="Legacy startup candidates scanned non-destructively",
        details=svc.status()["summary"],
    )
    caps = registry.get("capabilities")
    if caps is not None:
        from .capabilities import Capability

        caps.register(
            Capability(
                "startup_path_inventory",
                "legacy_containment",
                "10_legacy",
                available=True,
                required=False,
                priority=0,
                details=svc.status()["summary"],
            )
        )
    life = registry.get("lifecycle")
    if life is not None:
        life.set_state("legacy_containment", "active", message="Legacy containment scan complete; no files moved or deleted")
    return svc
