"""Establishment-wide Pub Manager policy service.

State Authority owns truth. Pub Manager owns the establishment posture: open,
quiet, busy, crowded, maintenance, recovery, or emergency. It is declarative,
not operational; Jeeves and local directors perform the work through the spine.
"""
from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Literal


EstablishmentMode = Literal[
    "open",
    "quiet",
    "busy",
    "crowded",
    "maintenance",
    "recovery",
    "emergency",
]


MODE_POLICIES: Dict[EstablishmentMode, Dict[str, Any]] = {
    "open": {
        "admissions": "normal",
        "background_work": "allowed",
        "jeeves_pressure": "normal",
        "engine_posture": "normal",
    },
    "quiet": {
        "admissions": "limited",
        "background_work": "reduced",
        "jeeves_pressure": "normal",
        "engine_posture": "protect_current_work",
    },
    "busy": {
        "admissions": "restricted",
        "background_work": "deferred",
        "jeeves_pressure": "high",
        "engine_posture": "throttle_nonessential",
    },
    "crowded": {
        "admissions": "paused",
        "background_work": "hibernated",
        "jeeves_pressure": "critical",
        "engine_posture": "protect_active_room_only",
    },
    "maintenance": {
        "admissions": "closed",
        "background_work": "diagnostic_only",
        "jeeves_pressure": "high",
        "engine_posture": "disabled_unless_required",
    },
    "recovery": {
        "admissions": "closed",
        "background_work": "recovery_only",
        "jeeves_pressure": "critical",
        "engine_posture": "restore_safely",
    },
    "emergency": {
        "admissions": "closed",
        "background_work": "critical_only",
        "jeeves_pressure": "critical",
        "engine_posture": "suspend_noncritical",
    },
}


@dataclass
class PubManagerDecision:
    mode: EstablishmentMode
    reasons: list[str] = field(default_factory=list)
    policy: Dict[str, Any] = field(default_factory=dict)
    evaluated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PubManagerService:
    """The operational steward of the PubCast establishment."""

    def __init__(self, registry: Any) -> None:
        self.registry = registry
        self.event_bus = registry.require("event_bus")
        self.state_authority = registry.require("state_authority")
        self.jeeves = registry.require("jeeves")
        self.started_at = time.time()
        self.mode: EstablishmentMode = "open"
        self.last_decision = PubManagerDecision(
            mode=self.mode,
            reasons=["initial"],
            policy=dict(MODE_POLICIES[self.mode]),
        )

    def _derive_mode(self, *, requested_mode: str | None = None) -> PubManagerDecision:
        if requested_mode:
            normalized = requested_mode.strip().lower()
            if normalized in MODE_POLICIES:
                mode = normalized  # type: ignore[assignment]
                return PubManagerDecision(
                    mode=mode,
                    reasons=[f"requested:{mode}"],
                    policy=dict(MODE_POLICIES[mode]),
                )

        summary = self.registry.summary()
        session = self.registry.require("session_state")
        jeeves_status = self.jeeves.status()
        reasons: list[str] = []

        required_failures = summary.get("required_failures", [])
        failed = summary.get("failed", [])
        if required_failures:
            reasons.append("required_spine_failure")
            mode: EstablishmentMode = "emergency"
        elif failed:
            reasons.append("nonrequired_service_failure")
            mode = "recovery"
        else:
            active_avatars = len(getattr(session, "avatars", {}) or {})
            hibernated = [
                record for record in jeeves_status.get("records", {}).values()
                if record.get("state") == "hibernated"
            ]
            if active_avatars >= 4:
                reasons.append("multiple_active_avatars")
                mode = "busy"
            elif hibernated:
                reasons.append("systems_already_hibernated")
                mode = "quiet"
            else:
                reasons.append("nominal")
                mode = "open"

        return PubManagerDecision(
            mode=mode,
            reasons=reasons,
            policy=dict(MODE_POLICIES[mode]),
        )

    async def evaluate(self, *, requested_mode: str | None = None, source: str = "pub_manager") -> Dict[str, Any]:
        decision = self._derive_mode(requested_mode=requested_mode)
        changed = decision.mode != self.mode
        self.mode = decision.mode
        self.last_decision = decision

        await self.event_bus.emit(
            "pub_manager.mode.evaluated",
            {"mode": decision.mode, "changed": changed, "reasons": decision.reasons, "policy": decision.policy},
            source=source,
        )
        return {"ok": True, "changed": changed, "decision": decision.to_dict(), "status": self.status()}

    def status(self) -> Dict[str, Any]:
        return {
            "ok": True,
            "service": "pub_manager",
            "started_at": self.started_at,
            "mode": self.mode,
            "last_decision": self.last_decision.to_dict(),
            "available_modes": list(MODE_POLICIES.keys()),
            "rule": "The Pub Manager protects establishment-wide continuity without bypassing the spine.",
            "boundaries": [
                "does_not_replace_state_authority",
                "does_not_replace_pete",
                "does_not_replace_jeeves",
                "does_not_control_engines_directly",
            ],
        }


def register_pub_manager_service(registry: Any) -> PubManagerService:
    service = PubManagerService(registry)

    capabilities = registry.get("capabilities")
    if capabilities is not None:
        from .capabilities import Capability

        capabilities.register(
            Capability(
                "establishment_policy",
                "pub_manager",
                "01_kernel",
                available=True,
                required=True,
                priority=0,
                details={"mode": service.mode},
            )
        )

    lifecycle = registry.get("lifecycle")
    if lifecycle is not None:
        lifecycle.set_state(
            "pub_manager",
            "active",
            message="Pub Manager establishment policy service is active",
        )

    registry.register(
        "pub_manager",
        service,
        phase="01_kernel",
        required=True,
        state="ready",
        message="Pub Manager owns establishment-wide mode and continuity policy",
        details={"mode": service.mode},
    )
    return service
