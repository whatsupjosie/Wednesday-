"""Spine-owned session snapshot/persistence skeleton."""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any, Optional


_SAFE_LABEL = re.compile(r"[^A-Za-z0-9_.-]+")


def _safe_snapshot_label(label: str) -> str:
    cleaned = _SAFE_LABEL.sub("_", (label or "manual").strip()).strip("._-")
    return cleaned[:80] or "manual"


class SpinePersistenceService:
    def __init__(self, registry: Any, *, root: Optional[Path] = None):
        self.registry = registry
        self.session_state = registry.require("session_state")
        self.event_bus = registry.require("event_bus")
        self.root = Path(root or Path.cwd()).resolve()
        self.snapshot_dir = self.root / "data" / "spine_snapshots"
        self.started_at = time.time()
        self.last_snapshot = None
        self.problems = []

    def make_snapshot(self):
        summary = self.registry.summary()
        return {
            "ok": True,
            "created_at": time.time(),
            "session": self.session_state.to_dict(),
            "registered_services": sorted(self.registry.names()),
            "required_failures": summary.get("required_failures", []),
            "event_history": self.registry.require("event_bus").history(limit=100),
        }

    async def save_snapshot(self, *, label: str = "manual"):
        safe_label = _safe_snapshot_label(label)
        snap = self.make_snapshot()
        snap["label"] = label
        snap["safe_label"] = safe_label
        self.last_snapshot = snap
        try:
            self.snapshot_dir.mkdir(parents=True, exist_ok=True)
            path = self.snapshot_dir / f"spine_snapshot_{int(snap['created_at'])}_{safe_label}.json"
            path.write_text(json.dumps(snap, indent=2, sort_keys=True), encoding="utf-8")
            snap["path"] = path.as_posix()
            await self.event_bus.emit(
                "session.snapshot.saved",
                {"path": path.as_posix(), "label": label, "safe_label": safe_label},
                source="persistence",
            )
            return {"ok": True, "path": path.as_posix(), "snapshot": snap}
        except Exception as exc:
            self.problems.append(str(exc))
            return {"ok": False, "message": f"Could not save spine snapshot: {exc}", "snapshot": snap}

    def status(self):
        return {
            "ok": not self.problems,
            "service": "spine_persistence",
            "started_at": self.started_at,
            "snapshot_dir": self.snapshot_dir.as_posix(),
            "last_snapshot_at": self.last_snapshot.get("created_at") if self.last_snapshot else None,
            "problems": list(self.problems),
            "tracks": [
                "session_state",
                "avatars",
                "rooms",
                "ai_agents",
                "engines",
                "events",
                "registered_services",
                "required_failures",
            ],
            "import_supported": False,
            "notes": "Export/save skeleton is present; destructive restore/import is intentionally disabled.",
        }


def register_persistence_service(registry: Any, *, root: Optional[Path] = None) -> SpinePersistenceService:
    svc = SpinePersistenceService(registry, root=root)
    caps = registry.get("capabilities")
    if caps is not None:
        from .capabilities import Capability

        caps.register(Capability("save_log_credit_records", "persistence", "09_persistence", available=True, required=False, priority=0))
        caps.register(Capability("session_snapshot_export", "persistence", "09_persistence", available=True, required=False, priority=0))
        caps.register(
            Capability(
                "session_snapshot_import",
                "persistence",
                "09_persistence",
                available=False,
                required=False,
                priority=80,
                details={"reason": "Destructive restore/import is intentionally disabled until reviewed."},
            )
        )
    life = registry.get("lifecycle")
    if life is not None:
        life.set_state("persistence", "active", message="Spine session snapshot export is available; import remains disabled")
    registry.register(
        "persistence",
        svc,
        phase="09_persistence",
        required=False,
        state="ready",
        message="Persistence service can snapshot spine session truth",
        details={"snapshot_dir": svc.snapshot_dir.as_posix(), "import_supported": False},
    )
    return svc
