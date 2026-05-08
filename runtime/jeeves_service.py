"""System-level Jeeves resource governor.

Jeeves applies the Switchblade principle above individual engines: keep what is
needed close, let recently used systems hold, hibernate quiet systems, and mark
cold systems off without deleting state.
"""
from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Literal, Optional


JeevesState = Literal["active", "holding", "hibernated", "off", "protected"]


@dataclass
class JeevesRecord:
    system_id: str
    state: JeevesState = "off"
    last_touched: float = field(default_factory=time.time)
    protected: bool = False
    reason: str = "registered"
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class JeevesService:
    """Small spine-owned lifecycle policy layer.

    This service does not kill processes yet. It records the canonical decision
    that later adapters use to throttle, hold, hibernate, or fully shut off
    their own workers.
    """

    def __init__(self, registry: Any, *, profile: str = "Gentle Saver") -> None:
        self.registry = registry
        self.event_bus = registry.require("event_bus")
        self.lifecycle = registry.require("lifecycle")
        self.profile = profile
        self.started_at = time.time()
        self.records: Dict[str, JeevesRecord] = {}
        self.holding_seconds = 45
        self.hibernate_seconds = 180
        self.protected_systems = {
            "registry",
            "event_bus",
            "session_state",
            "lifecycle",
            "capabilities",
            "jeeves",
            "preflight",
            "spine_governor",
        }

    def touch(
        self,
        system_id: str,
        *,
        protected: bool = False,
        reason: str = "activity",
        **details: Any,
    ) -> JeevesRecord:
        record = self.records.get(system_id) or JeevesRecord(system_id=system_id)
        record.last_touched = time.time()
        record.protected = protected or system_id in self.protected_systems
        record.reason = reason
        record.details.update(details)
        record.state = "protected" if record.protected else "active"
        self.records[system_id] = record
        self.lifecycle.set_state(
            system_id,
            "active",
            message=f"Jeeves touch: {reason}",
            jeeves_state=record.state,
        )
        return record

    def set_state(
        self,
        system_id: str,
        state: JeevesState,
        *,
        reason: str = "policy",
        **details: Any,
    ) -> JeevesRecord:
        record = self.records.get(system_id) or JeevesRecord(system_id=system_id)
        record.state = state
        record.reason = reason
        record.details.update(details)
        record.protected = state == "protected" or system_id in self.protected_systems
        self.records[system_id] = record

        lifecycle_state = {
            "active": "active",
            "protected": "active",
            "holding": "holding",
            "hibernated": "hibernated",
            "off": "off",
        }[state]
        self.lifecycle.set_state(
            system_id,
            lifecycle_state,
            message=f"Jeeves policy: {reason}",
            jeeves_state=state,
        )
        return record

    async def evaluate(self, *, pressure: Optional[str] = None) -> Dict[str, Any]:
        now = time.time()
        recommendations: Dict[str, str] = {}

        for system_id in self.registry.names():
            record = self.records.get(system_id)
            if record is None:
                record = self.touch(system_id, protected=system_id in self.protected_systems, reason="registry_seen")

            if record.protected:
                recommendations[system_id] = "protect"
                continue

            idle_for = now - record.last_touched
            if pressure in {"high", "critical"} and idle_for > self.holding_seconds:
                self.set_state(system_id, "hibernated", reason=f"{pressure}_pressure_idle")
                recommendations[system_id] = "hibernate"
            elif idle_for > self.hibernate_seconds:
                self.set_state(system_id, "hibernated", reason="idle_timeout")
                recommendations[system_id] = "hibernate"
            elif idle_for > self.holding_seconds:
                self.set_state(system_id, "holding", reason="recently_used")
                recommendations[system_id] = "hold"
            else:
                recommendations[system_id] = "keep_active"

        await self.event_bus.emit(
            "jeeves.policy.evaluated",
            {"profile": self.profile, "pressure": pressure or "normal", "recommendations": recommendations},
            source="jeeves",
        )
        return {"ok": True, "recommendations": recommendations, "status": self.status()}

    def status(self) -> Dict[str, Any]:
        records = {key: value.to_dict() for key, value in sorted(self.records.items())}
        return {
            "ok": True,
            "service": "jeeves",
            "profile": self.profile,
            "started_at": self.started_at,
            "policy": {
                "holding_seconds": self.holding_seconds,
                "hibernate_seconds": self.hibernate_seconds,
                "protected_systems": sorted(self.protected_systems),
                "states": ["active", "holding", "hibernated", "off", "protected"],
                "rule": "Spend compute on what matters right now, not on what merely exists.",
            },
            "records": records,
        }


def register_jeeves_service(registry: Any) -> JeevesService:
    service = JeevesService(registry)

    capabilities = registry.get("capabilities")
    if capabilities is not None:
        from .capabilities import Capability

        capabilities.register(
            Capability(
                "resource_lifecycle_governance",
                "jeeves",
                "01_kernel",
                available=True,
                required=True,
                priority=0,
                details={"profile": service.profile},
            )
        )

    lifecycle = registry.get("lifecycle")
    if lifecycle is not None:
        lifecycle.set_state(
            "jeeves",
            "active",
            message="System-level Jeeves resource lifecycle governor is active",
        )

    registry.register(
        "jeeves",
        service,
        phase="01_kernel",
        required=True,
        state="ready",
        message="Jeeves owns system-level hold/hibernate/off policy",
        details={"profile": service.profile},
    )
    service.touch("jeeves", protected=True, reason="self")
    return service
