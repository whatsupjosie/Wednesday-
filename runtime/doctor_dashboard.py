"""Unified doctor report over every spine-owned layer."""
from __future__ import annotations

import time
from typing import Any


def build_spine_doctor_report(registry: Any):
    services = registry.to_dict()

    def stat(name):
        svc = registry.get(name)
        if svc is not None and hasattr(svc, "status"):
            try:
                return svc.status()
            except Exception as exc:
                return {"ok": False, "message": f"{name}.status() failed: {exc}"}
        return services.get(name, {})

    life = registry.get("lifecycle")
    caps = registry.get("capabilities")
    bus = registry.get("event_bus")
    summary = registry.summary()
    return {
        "ok": not summary.get("required_failures"),
        "message": "PubCast spine doctor report",
        "canonical_startup": "main.py -> runtime.boot_sequence.attach_spine(app) -> registered systems",
        "required_failures": summary.get("required_failures", []),
        "registered_systems": sorted(registry.names()),
        "failed_systems": summary.get("failed", []),
        "boot_order": registry.get("boot_order"),
        "governance": registry.get("spine_governance"),
        "preflight": registry.get("preflight"),
        "state_authority": stat("state_authority"),
        "pub_manager": stat("pub_manager"),
        "avatar_truth": stat("avatar_system"),
        "world_truth": stat("world_system"),
        "bridge_status": stat("bridge_system"),
        "jeeves_status": stat("jeeves"),
        "motion_status": stat("motion_system"),
        "ai_status": stat("ai_router"),
        "session_status": registry.require("session_state").to_dict(),
        "persistence_status": stat("persistence"),
        "legacy_containment": stat("legacy_containment"),
        "lifecycle": life.summary() if life else {},
        "capabilities": caps.to_dict() if caps else {},
        "event_history": bus.history(limit=50) if bus else [],
        "services": services,
    }


class SpineDoctorDashboardService:
    def __init__(self, registry: Any):
        self.registry = registry
        self.started_at = time.time()

    def status(self):
        report = build_spine_doctor_report(self.registry)
        return {
            "ok": report.get("ok", False),
            "service": "spine_doctor_dashboard",
            "started_at": self.started_at,
            "registered_systems": len(report.get("registered_systems", [])),
            "failed_systems": report.get("failed_systems", []),
            "sections": [
                "registered_systems",
                "failed_systems",
                "preflight",
                "state_authority",
                "pub_manager",
                "avatar_truth",
                "world_truth",
                "bridge_status",
                "jeeves_status",
                "motion_status",
                "ai_status",
                "session_status",
                "persistence_status",
                "legacy_containment",
                "lifecycle",
                "capabilities",
                "event_history",
            ],
        }

    def report(self):
        return build_spine_doctor_report(self.registry)


def register_doctor_dashboard_service(registry: Any) -> SpineDoctorDashboardService:
    svc = SpineDoctorDashboardService(registry)
    caps = registry.get("capabilities")
    if caps is not None:
        from .capabilities import Capability

        caps.register(Capability("spine_doctor_report", "doctor_dashboard", "02_diagnostics", available=True, required=False, priority=0))
    life = registry.get("lifecycle")
    if life is not None:
        life.set_state("doctor_dashboard", "active", message="Unified spine doctor report is available")
    registry.register(
        "doctor_dashboard",
        svc,
        phase="02_diagnostics",
        required=False,
        state="ready",
        message="Doctor dashboard unifies spine-owned status reports",
        details={"sections": svc.status()["sections"]},
    )
    return svc
