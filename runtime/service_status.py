"""PubCast runtime service status records.

These dataclasses are intentionally tiny and dependency-free so the spine can
boot before optional engines, AI providers, renderers, and room plugins exist.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Literal, Optional

ServiceState = Literal["pending", "ready", "optional", "warning", "failed", "disabled"]


@dataclass
class ServiceStatus:
    name: str
    state: ServiceState = "pending"
    phase: str = "unassigned"
    required: bool = False
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.state in {"ready", "optional", "warning", "disabled"}

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
