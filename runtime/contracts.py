"""PubCast spine contracts.

These contracts are deliberately tiny. They make future systems prove what they
are, what they need, and what they provide before they are treated as part of
the canonical runtime spine.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Optional, Protocol


class SpinePlugin(Protocol):
    """Optional protocol for systems that want to register with the spine."""

    contract: "SystemContract"

    def register(self, registry: Any) -> Any:
        """Register the system with the AppRegistry."""


@dataclass(frozen=True)
class SystemContract:
    """Declaration of a PubCast system's spine-facing responsibilities."""

    system_id: str
    phase: str
    kind: str
    required: bool = False
    depends_on: List[str] = field(default_factory=list)
    provides: List[str] = field(default_factory=list)
    consumes_events: List[str] = field(default_factory=list)
    emits_events: List[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def validate_contract(contract: SystemContract, known_services: Iterable[str]) -> List[str]:
    """Return human-readable dependency problems for a contract."""

    known = set(known_services)
    problems: List[str] = []
    for dependency in contract.depends_on:
        if dependency not in known:
            problems.append(f"{contract.system_id} depends on unregistered service: {dependency}")
    if not contract.system_id:
        problems.append("Contract has empty system_id")
    if not contract.phase:
        problems.append(f"{contract.system_id} has empty phase")
    if not contract.kind:
        problems.append(f"{contract.system_id} has empty kind")
    return problems


def default_spine_contracts() -> List[SystemContract]:
    """The first permanent spine law: known core services and late-bound systems."""

    return [
        SystemContract("settings", "00_config", "config", True, provides=["settings"]),
        SystemContract("registry", "01_kernel", "kernel", True, provides=["service_lookup"]),
        SystemContract("event_bus", "01_kernel", "kernel", True, provides=["pubsub", "event_history"]),
        SystemContract("session_state", "01_kernel", "kernel", True, provides=["runtime_truth"]),
        SystemContract("state_authority", "01_kernel", "kernel", True, depends_on=["registry", "event_bus", "session_state"], provides=["runtime_state_authority", "transactional_truth"], emits_events=["state.transaction.committed"], notes="Canonical runtime truth gate; events and services do not become truth by themselves."),
        SystemContract("lifecycle", "01_kernel", "kernel", True, depends_on=["registry"], provides=["lifecycle_state"]),
        SystemContract("capabilities", "01_kernel", "kernel", True, depends_on=["registry"], provides=["capability_lookup"]),
        SystemContract("jeeves", "01_kernel", "kernel", True, depends_on=["registry", "event_bus", "session_state", "state_authority", "lifecycle", "capabilities"], provides=["resource_lifecycle_governance"], consumes_events=["*"], emits_events=["jeeves.policy.evaluated"], notes="System-level Jeeves owns active/holding/hibernated/off policy; engines only adapt it."),
        SystemContract("pub_manager", "01_kernel", "kernel", True, depends_on=["registry", "event_bus", "state_authority", "jeeves", "capabilities"], provides=["establishment_policy"], consumes_events=["*"], emits_events=["pub_manager.mode.evaluated"], notes="Pub Manager owns establishment-wide continuity policy and does not bypass State Authority, Jeeves, Pete, or the spine."),
        SystemContract("spine_contracts", "01_kernel", "kernel", True, depends_on=["registry", "lifecycle"], provides=["contract_truth"]),
        SystemContract("boot_order", "01_kernel", "kernel", True, depends_on=["spine_contracts"], provides=["canonical_order"]),
        SystemContract("spine_governor", "01_kernel", "kernel", True, depends_on=["boot_order"], provides=["spine_policy_enforcement"]),
        SystemContract("preflight", "02_diagnostics", "diagnostic", True, depends_on=["settings"], provides=["launch_gate"]),
        SystemContract("asset_manifest", "03_assets", "asset_truth", True, depends_on=["preflight"], provides=["avatar_asset_truth"]),
        SystemContract("avatar_system", "04_avatars", "avatar", True, depends_on=["asset_manifest", "state_authority", "event_bus"], provides=["avatar_asset_truth", "avatar_runtime_state"], consumes_events=["mocap.frame", "avatar.move_requested"], emits_events=["avatar.state_changed"], notes="Manny and Sheila GLBs are spine-owned; missing assets fail honestly instead of substituting sprites."),
        SystemContract("world_system", "05_world", "world", False, depends_on=["state_authority", "event_bus"], provides=["room_truth", "hotspots"], consumes_events=["avatar.move_requested"], emits_events=["room.changed", "interaction.available"]),
        SystemContract("bridge_system", "06_bridge", "bridge", False, depends_on=["event_bus", "session_state"], provides=["websocket_bridge"], consumes_events=["*"], emits_events=["client.connected", "client.disconnected", "client.command"]),
        SystemContract("motion_system", "06_bridge", "motion", False, depends_on=["avatar_system", "world_system", "event_bus", "session_state"], provides=["performer_motion_state", "mocap_input_hook"], consumes_events=["avatar.moved", "mocap.frame"], emits_events=["motion.state_changed"]),
        SystemContract("engine_runtime", "07_engines", "engine", False, depends_on=["event_bus", "session_state"], provides=["engine_capabilities"], consumes_events=["engine.request"], emits_events=["engine.status"]),
        SystemContract("ai_router", "08_ai", "ai_router", False, depends_on=["event_bus", "session_state"], provides=["two_brain_routing"], consumes_events=["director.request", "architect.request"], emits_events=["ai.request.routed"], notes="Persona AI and engine AI are separated; neither owns runtime truth."),
        SystemContract("studio_brain", "08_ai", "ai", False, depends_on=["ai_router"], provides=["fast_director_advice"], consumes_events=["director.request"], emits_events=["director.suggestion"], notes="Fast online/offline conversational brain; must not own runtime truth."),
        SystemContract("architect_brain", "08_ai", "ai", False, depends_on=["ai_router"], provides=["slow_planning_advice"], consumes_events=["architect.request"], emits_events=["architect.plan"], notes="Slower planning/code/design brain; late-bound and optional."),
        SystemContract("persistence", "09_persistence", "persistence", False, depends_on=["session_state", "event_bus"], provides=["save_log_credit_records"], consumes_events=["*"], emits_events=["session.snapshot.saved"]),
        SystemContract("legacy_containment", "10_legacy", "legacy", False, depends_on=["registry"], provides=["startup_path_inventory"], notes="Non-destructive inventory only; no deletions or moves."),
    ]
