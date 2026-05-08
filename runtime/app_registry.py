"""Canonical PubCast runtime service registry.

The registry is the permanent spine's address book. Systems register here;
other systems discover shared services through this object rather than importing
random globals from unrelated modules.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Optional

from .service_status import ServiceStatus


@dataclass
class RegisteredService:
    name: str
    instance: Any = None
    status: ServiceStatus = field(default_factory=lambda: ServiceStatus(name="unknown"))

    def to_dict(self) -> Dict[str, Any]:
        data = self.status.to_dict()
        data["registered"] = self.instance is not None
        data["type"] = type(self.instance).__name__ if self.instance is not None else None
        return data


class AppRegistry:
    """Small service registry with explicit status and boot-phase metadata."""

    def __init__(self, *, settings: Any = None) -> None:
        self.settings = settings
        self._services: Dict[str, RegisteredService] = {}
        if settings is not None:
            self.register("settings", settings, phase="00_config", required=True, message="Settings loaded")

    def register(
        self,
        name: str,
        instance: Any = None,
        *,
        phase: str = "unassigned",
        required: bool = False,
        state: str = "ready",
        message: str = "",
        details: Optional[Dict[str, Any]] = None,
    ) -> Any:
        self._services[name] = RegisteredService(
            name=name,
            instance=instance,
            status=ServiceStatus(
                name=name,
                state=state,  # type: ignore[arg-type]
                phase=phase,
                required=required,
                message=message,
                details=details or {},
            ),
        )
        return instance

    def mark(
        self,
        name: str,
        *,
        state: str,
        phase: str = "unassigned",
        required: bool = False,
        message: str = "",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        current = self._services.get(name)
        instance = current.instance if current else None
        self.register(
            name,
            instance,
            phase=phase,
            required=required,
            state=state,
            message=message,
            details=details,
        )

    def get(self, name: str, default: Any = None) -> Any:
        service = self._services.get(name)
        return service.instance if service is not None else default

    def require(self, name: str) -> Any:
        if name not in self._services or self._services[name].instance is None:
            raise KeyError(f"Required PubCast service is not registered: {name}")
        return self._services[name].instance

    def names(self) -> Iterable[str]:
        return self._services.keys()

    def to_dict(self) -> Dict[str, Any]:
        return {name: service.to_dict() for name, service in sorted(self._services.items())}

    def summary(self) -> Dict[str, Any]:
        services = self.to_dict()
        required_failures = [
            name for name, status in services.items()
            if status.get("required") and status.get("state") == "failed"
        ]
        return {
            "service_count": len(services),
            "required_failures": required_failures,
            "ready": [name for name, status in services.items() if status.get("state") == "ready"],
            "failed": [name for name, status in services.items() if status.get("state") == "failed"],
            "services": services,
        }
