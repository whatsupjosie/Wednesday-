"""PubCast spine lifecycle controller.

Lifecycle is separate from service registration so the app can tell the
difference between "known", "registered", "healthy", "active", "degraded", and
"stopped" without inventing one-off flags in every subsystem.
"""
from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Literal, Optional

LifecycleState = Literal[
    "declared",
    "registered",
    "starting",
    "active",
    "holding",
    "hibernated",
    "off",
    "degraded",
    "stopping",
    "stopped",
    "failed",
    "disabled",
]


@dataclass
class LifecycleRecord:
    system_id: str
    state: LifecycleState = "declared"
    message: str = ""
    updated_at: float = field(default_factory=time.time)
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class LifecycleController:
    def __init__(self) -> None:
        self._records: Dict[str, LifecycleRecord] = {}

    def declare(self, system_id: str, *, message: str = "Declared by spine", **details: Any) -> LifecycleRecord:
        return self.set_state(system_id, "declared", message=message, **details)

    def set_state(self, system_id: str, state: LifecycleState, *, message: str = "", **details: Any) -> LifecycleRecord:
        record = self._records.get(system_id) or LifecycleRecord(system_id=system_id)
        record.state = state
        record.message = message
        record.details.update(details)
        record.updated_at = time.time()
        self._records[system_id] = record
        return record

    def get(self, system_id: str) -> Optional[LifecycleRecord]:
        return self._records.get(system_id)

    def to_dict(self) -> Dict[str, Any]:
        return {key: value.to_dict() for key, value in sorted(self._records.items())}

    def summary(self) -> Dict[str, Any]:
        data = self.to_dict()
        return {
            "system_count": len(data),
            "active": [k for k, v in data.items() if v.get("state") == "active"],
            "holding": [k for k, v in data.items() if v.get("state") == "holding"],
            "hibernated": [k for k, v in data.items() if v.get("state") == "hibernated"],
            "off": [k for k, v in data.items() if v.get("state") == "off"],
            "failed": [k for k, v in data.items() if v.get("state") == "failed"],
            "degraded": [k for k, v in data.items() if v.get("state") == "degraded"],
            "systems": data,
        }
