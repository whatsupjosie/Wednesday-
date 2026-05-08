"""Permanent PubCast runtime spine helpers.

The current app still has a large legacy main.py. This module gives that app a
canonical kernel without destructively moving hundreds of routes at once.
Future systems should register through this spine instead of adding new globals.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI

from config.settings import settings
from doctor.preflight import run_spine_preflight
from .app_registry import AppRegistry
from .event_bus import EventBus
from .session_state import SessionState
from .spine_manifest import AI_POLICY, BOOT_PHASES, ENGINE_POLICY
from .contracts import default_spine_contracts, validate_contract
from .state_authority import register_state_authority
from .lifecycle import LifecycleController
from .capabilities import CapabilityRegistry, seed_core_capabilities
from .boot_order import resolve_boot_plan
from .spine_governor import SpineGovernor
from .jeeves_service import register_jeeves_service
from .pub_manager import register_pub_manager_service
from .avatar_service import register_avatar_service
from .world_service import register_world_service
from .bridge_service import register_bridge_service
from .motion_service import register_motion_service
from .ai_router_service import register_ai_router_service
from .persistence_service import register_persistence_service
from .legacy_containment import register_legacy_containment_service
from .doctor_dashboard import build_spine_doctor_report, register_doctor_dashboard_service


def create_kernel_registry(*, root: Optional[Path] = None) -> AppRegistry:
    registry = AppRegistry(settings=settings)
    event_bus = EventBus()
    session_state = SessionState()
    lifecycle = LifecycleController()
    capability_registry = CapabilityRegistry()
    boot_plan = resolve_boot_plan()
    spine_governor = SpineGovernor(boot_plan=boot_plan)
    seed_core_capabilities(capability_registry)
    registry.register("registry", registry, phase="01_kernel", required=True, message="Registry is the service spine")
    registry.register("event_bus", event_bus, phase="01_kernel", required=True, message="Event bus ready")
    registry.register("session_state", session_state, phase="01_kernel", required=True, message="Session truth store ready")
    registry.register("lifecycle", lifecycle, phase="01_kernel", required=True, message="Lifecycle controller ready")
    registry.register("capabilities", capability_registry, phase="01_kernel", required=True, message="Capability registry ready")
    register_state_authority(registry)
    registry.register(
        "boot_order",
        boot_plan.to_dict(),
        phase="01_kernel",
        required=True,
        state="ready" if boot_plan.ok else "failed",
        message="Canonical boot order resolved" if boot_plan.ok else "Canonical boot order has problems",
        details={"problems": boot_plan.problems, "warnings": boot_plan.warnings, "version": boot_plan.version},
    )
    registry.register("spine_governor", spine_governor, phase="01_kernel", required=True, message="Spine governor ready")
    register_jeeves_service(registry)
    register_pub_manager_service(registry)

    for contract in default_spine_contracts():
        lifecycle.declare(contract.system_id, message=f"Declared contract for {contract.kind}", phase=contract.phase, required=contract.required)

    contract_problems = []
    known = set(registry.names()) | {contract.system_id for contract in default_spine_contracts()}
    for contract in default_spine_contracts():
        contract_problems.extend(validate_contract(contract, known))
    registry.register(
        "spine_contracts",
        [contract.to_dict() for contract in default_spine_contracts()],
        phase="01_kernel",
        required=True,
        state="ready" if not contract_problems else "warning",
        message="Spine contracts declared" if not contract_problems else "Spine contract warnings found",
        details={"problems": contract_problems},
    )

    preflight = run_spine_preflight(root or Path.cwd())
    registry.register(
        "preflight",
        preflight,
        phase="02_diagnostics",
        required=True,
        state="ready" if preflight.get("ok") else "failed",
        message="Spine preflight passed" if preflight.get("ok") else "Spine preflight has required failures",
        details=preflight.get("summary", {}),
    )
    register_doctor_dashboard_service(registry)

    checks_by_id = {check.get("check_id"): check for check in preflight.get("checks", []) if isinstance(check, dict)}
    avatar_manifest = checks_by_id.get("avatar_manifest", {})
    registry.register(
        "asset_manifest",
        avatar_manifest,
        phase="03_assets",
        required=True,
        state="ready" if avatar_manifest.get("status") in {"pass", "warn"} else "failed",
        message=avatar_manifest.get("message", "Avatar asset manifest status unknown"),
        details=avatar_manifest.get("details", {}),
    )

    # The first real subsystem owned by the permanent spine: avatar asset truth.
    # This deliberately happens after manifest/preflight and before engines/AI.
    project_root = root or Path.cwd()
    register_avatar_service(registry, root=project_root)

    # Continuous spine layers. These are narrow authority services and hooks, not
    # destructive rewrites of the legacy UI/rendering app.
    register_world_service(registry)
    register_bridge_service(registry)
    register_motion_service(registry)
    register_ai_router_service(registry)
    register_persistence_service(registry, root=project_root)
    register_legacy_containment_service(registry, root=project_root)

    # Declare the two-brain policy and engine policy as first-class services so
    # later implementation can't accidentally let an AI/engine become the spine.
    registry.register("ai_policy", AI_POLICY, phase="08_ai", required=False, state="ready", message="Two-AI policy declared")
    registry.register("engine_policy", ENGINE_POLICY, phase="07_engines", required=False, state="ready", message="Multi-engine policy declared")

    decision = spine_governor.evaluate(registry)
    registry.register(
        "spine_governance",
        decision.to_dict(),
        phase="01_kernel",
        required=True,
        state="ready" if decision.ok else "failed",
        message=decision.message,
        details=decision.details,
    )
    return registry


def attach_spine(application: FastAPI, *, root: Optional[Path] = None) -> AppRegistry:
    registry = create_kernel_registry(root=root)
    application.state.pubcast_spine = registry
    application.state.event_bus = registry.require("event_bus")
    application.state.session_state = registry.require("session_state")
    application.state.state_authority = registry.require("state_authority")
    application.state.lifecycle = registry.require("lifecycle")
    application.state.capabilities = registry.require("capabilities")
    application.state.spine_governor = registry.require("spine_governor")
    application.state.pub_manager = registry.require("pub_manager")
    return registry


def spine_status(application: FastAPI) -> dict[str, Any]:
    registry = getattr(application.state, "pubcast_spine", None)
    if registry is None:
        return {"ok": False, "message": "PubCast spine has not been attached"}
    summary = registry.summary()
    return {
        "ok": not summary["required_failures"],
        "canonical_startup": "main.py -> runtime.boot_sequence.attach_spine(app) -> registered systems",
        "boot_phases": [{"id": phase, "description": desc} for phase, desc in BOOT_PHASES],
        "boot_order": registry.get("boot_order"),
        "governance": registry.get("spine_governance"),
        **summary,
    }


def install_spine_routes(application: FastAPI) -> None:
    @application.get("/api/spine/status")
    async def api_spine_status():
        return spine_status(application)

    @application.get("/api/spine/preflight")
    async def api_spine_preflight():
        registry = getattr(application.state, "pubcast_spine", None)
        if registry is not None:
            return registry.get("preflight")
        return run_spine_preflight(Path.cwd())

    @application.get("/api/spine/contracts")
    async def api_spine_contracts():
        registry = getattr(application.state, "pubcast_spine", None)
        if registry is None:
            return {"ok": False, "contracts": []}
        service = registry.get("spine_contracts", [])
        details = registry.to_dict().get("spine_contracts", {}).get("details", {})
        return {"ok": not details.get("problems"), "contracts": service, "problems": details.get("problems", [])}

    @application.get("/api/spine/lifecycle")
    async def api_spine_lifecycle():
        registry = getattr(application.state, "pubcast_spine", None)
        if registry is None:
            return {"ok": False, "message": "PubCast spine has not been attached"}
        lifecycle = registry.require("lifecycle")
        return {"ok": not lifecycle.summary()["failed"], **lifecycle.summary()}

    @application.get("/api/spine/capabilities")
    async def api_spine_capabilities():
        registry = getattr(application.state, "pubcast_spine", None)
        if registry is None:
            return {"ok": False, "capabilities": {}}
        capabilities = registry.require("capabilities")
        return {"ok": True, "capabilities": capabilities.to_dict()}

    @application.get("/api/spine/state/status")
    async def api_spine_state_status():
        registry = getattr(application.state, "pubcast_spine", None)
        if registry is None:
            return {"ok": False, "message": "PubCast spine has not been attached"}
        service = registry.get("state_authority")
        return service.status() if service is not None else {"ok": False, "message": "State authority is not registered with the spine"}

    @application.get("/api/spine/state/snapshot")
    async def api_spine_state_snapshot():
        registry = getattr(application.state, "pubcast_spine", None)
        if registry is None:
            return {"ok": False, "snapshot": {}}
        service = registry.get("state_authority")
        if service is None:
            return {"ok": False, "snapshot": {}}
        return {"ok": True, "revision": service.revision, "snapshot": service.snapshot()}

    @application.get("/api/spine/jeeves/status")
    async def api_spine_jeeves_status():
        registry = getattr(application.state, "pubcast_spine", None)
        if registry is None:
            return {"ok": False, "message": "PubCast spine has not been attached"}
        service = registry.get("jeeves")
        return service.status() if service is not None else {"ok": False, "message": "Jeeves is not registered with the spine"}

    @application.post("/api/spine/jeeves/touch")
    async def api_spine_jeeves_touch(payload: dict[str, Any]):
        registry = getattr(application.state, "pubcast_spine", None)
        if registry is None:
            return {"ok": False, "message": "PubCast spine has not been attached"}
        service = registry.get("jeeves")
        if service is None:
            return {"ok": False, "message": "Jeeves is not registered with the spine"}
        system_id = str(payload.get("system_id") or "").strip()
        if not system_id:
            return {"ok": False, "message": "system_id is required"}
        record = service.touch(system_id, protected=bool(payload.get("protected")), reason=str(payload.get("reason") or "api"))
        return {"ok": True, "record": record.to_dict(), "status": service.status()}

    @application.post("/api/spine/jeeves/evaluate")
    async def api_spine_jeeves_evaluate(payload: dict[str, Any] | None = None):
        registry = getattr(application.state, "pubcast_spine", None)
        if registry is None:
            return {"ok": False, "message": "PubCast spine has not been attached"}
        service = registry.get("jeeves")
        if service is None:
            return {"ok": False, "message": "Jeeves is not registered with the spine"}
        return await service.evaluate(pressure=str((payload or {}).get("pressure") or "normal"))

    @application.get("/api/spine/pub-manager/status")
    async def api_spine_pub_manager_status():
        registry = getattr(application.state, "pubcast_spine", None)
        if registry is None:
            return {"ok": False, "message": "PubCast spine has not been attached"}
        service = registry.get("pub_manager")
        return service.status() if service is not None else {"ok": False, "message": "Pub Manager is not registered with the spine"}

    @application.post("/api/spine/pub-manager/evaluate")
    async def api_spine_pub_manager_evaluate(payload: dict[str, Any] | None = None):
        registry = getattr(application.state, "pubcast_spine", None)
        if registry is None:
            return {"ok": False, "message": "PubCast spine has not been attached"}
        service = registry.get("pub_manager")
        if service is None:
            return {"ok": False, "message": "Pub Manager is not registered with the spine"}
        return await service.evaluate(requested_mode=(payload or {}).get("mode"), source="api.spine.pub_manager")

    @application.get("/api/spine/avatars/status")
    async def api_spine_avatars_status():
        registry = getattr(application.state, "pubcast_spine", None)
        if registry is None:
            return {"ok": False, "message": "PubCast spine has not been attached"}
        avatar_service = registry.get("avatar_system")
        if avatar_service is None:
            return {"ok": False, "message": "Avatar service is not registered with the spine"}
        return avatar_service.status()


    @application.get("/api/spine/world/status")
    async def api_spine_world_status():
        registry = getattr(application.state, "pubcast_spine", None)
        if registry is None:
            return {"ok": False, "message": "PubCast spine has not been attached"}
        service = registry.get("world_system")
        return service.status() if service is not None else {"ok": False, "message": "World service is not registered with the spine"}

    @application.post("/api/spine/world/move-avatar")
    async def api_spine_world_move_avatar(payload: dict[str, Any]):
        registry = getattr(application.state, "pubcast_spine", None)
        if registry is None:
            return {"ok": False, "message": "PubCast spine has not been attached"}
        service = registry.get("world_system")
        if service is None:
            return {"ok": False, "message": "World service is not registered with the spine"}
        avatar_id = str(payload.get("avatar_id") or "").strip()
        room_id = str(payload.get("room_id") or payload.get("to_room") or "").strip()
        if not avatar_id or not room_id:
            return {"ok": False, "message": "avatar_id and room_id are required"}
        return await service.move_avatar(avatar_id, room_id, source="api.spine.world", reason=str(payload.get("reason") or "api"))

    @application.get("/api/spine/bridge/status")
    async def api_spine_bridge_status():
        registry = getattr(application.state, "pubcast_spine", None)
        if registry is None:
            return {"ok": False, "message": "PubCast spine has not been attached"}
        service = registry.get("bridge_system")
        return service.status() if service is not None else {"ok": False, "message": "Bridge service is not registered with the spine"}

    @application.get("/api/spine/motion/status")
    async def api_spine_motion_status():
        registry = getattr(application.state, "pubcast_spine", None)
        if registry is None:
            return {"ok": False, "message": "PubCast spine has not been attached"}
        service = registry.get("motion_system")
        return service.status() if service is not None else {"ok": False, "message": "Motion service is not registered with the spine"}

    @application.get("/api/spine/ai/status")
    async def api_spine_ai_status():
        registry = getattr(application.state, "pubcast_spine", None)
        if registry is None:
            return {"ok": False, "message": "PubCast spine has not been attached"}
        service = registry.get("ai_router")
        return service.status() if service is not None else {"ok": False, "message": "AI router is not registered with the spine"}

    @application.post("/api/spine/ai/route")
    async def api_spine_ai_route(payload: dict[str, Any]):
        registry = getattr(application.state, "pubcast_spine", None)
        if registry is None:
            return {"ok": False, "message": "PubCast spine has not been attached"}
        service = registry.get("ai_router")
        if service is None:
            return {"ok": False, "message": "AI router is not registered with the spine"}
        return await service.route_request(str(payload.get("intent") or "persona"), payload.get("payload") or {}, source="api.spine.ai")

    @application.get("/api/spine/session/status")
    async def api_spine_session_status():
        registry = getattr(application.state, "pubcast_spine", None)
        if registry is None:
            return {"ok": False, "message": "PubCast spine has not been attached"}
        persistence = registry.get("persistence")
        return {"ok": True, "session": registry.require("session_state").to_dict(), "persistence": persistence.status() if persistence is not None else None}

    @application.post("/api/spine/session/save")
    async def api_spine_session_save(payload: dict[str, Any] | None = None):
        registry = getattr(application.state, "pubcast_spine", None)
        if registry is None:
            return {"ok": False, "message": "PubCast spine has not been attached"}
        service = registry.get("persistence")
        if service is None:
            return {"ok": False, "message": "Persistence service is not registered with the spine"}
        return await service.save_snapshot(label=str((payload or {}).get("label") or "api"))

    @application.get("/api/spine/doctor")
    async def api_spine_doctor():
        registry = getattr(application.state, "pubcast_spine", None)
        if registry is None:
            return {"ok": False, "message": "PubCast spine has not been attached"}
        return build_spine_doctor_report(registry)

    @application.get("/api/spine/legacy/status")
    async def api_spine_legacy_status():
        registry = getattr(application.state, "pubcast_spine", None)
        if registry is None:
            return {"ok": False, "message": "PubCast spine has not been attached"}
        service = registry.get("legacy_containment")
        return service.status() if service is not None else {"ok": False, "message": "Legacy containment service is not registered with the spine"}

    @application.get("/api/spine/boot-order")
    async def api_spine_boot_order():
        registry = getattr(application.state, "pubcast_spine", None)
        if registry is None:
            return {"ok": False, "message": "PubCast spine has not been attached"}
        return registry.get("boot_order")

    @application.get("/api/spine/governance")
    async def api_spine_governance():
        registry = getattr(application.state, "pubcast_spine", None)
        if registry is None:
            return {"ok": False, "message": "PubCast spine has not been attached"}
        governor = registry.require("spine_governor")
        decision = governor.evaluate(registry)
        registry.mark(
            "spine_governance",
            state="ready" if decision.ok else "failed",
            phase="01_kernel",
            required=True,
            message=decision.message,
            details=decision.details,
        )
        return {"ok": decision.ok, "governor": governor.to_dict()}

    @application.get("/api/spine/events")
    async def api_spine_events(limit: int = 50):
        registry = getattr(application.state, "pubcast_spine", None)
        if registry is None:
            return {"ok": False, "events": []}
        event_bus = registry.require("event_bus")
        return {"ok": True, "subscriber_counts": event_bus.subscriber_counts(), "events": event_bus.history(limit=max(1, min(limit, 250)))}
