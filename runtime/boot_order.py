"""Uniform PubCast spine boot order.

This is the adjustable rail. Future changes to startup order should happen here
instead of being scattered through main.py, AI agents, engine modules, or routes.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from .spine_manifest import BOOT_PHASES


BOOT_ORDER_VERSION = "2026-05-08.pub-manager-1"


@dataclass(frozen=True)
class BootUnit:
    """A declared system in the canonical spine order."""

    system_id: str
    phase: str
    required: bool = False
    depends_on: List[str] = field(default_factory=list)
    provides: List[str] = field(default_factory=list)
    late_bound: bool = False
    rationale: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class BootPlan:
    """Resolved boot order plus validation findings."""

    version: str
    phases: List[Tuple[str, str]]
    units: List[BootUnit]
    problems: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.problems

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "version": self.version,
            "phases": [{"id": phase, "description": desc} for phase, desc in self.phases],
            "units": [unit.to_dict() for unit in self.units],
            "problems": list(self.problems),
            "warnings": list(self.warnings),
        }


DEFAULT_BOOT_UNITS: List[BootUnit] = [
    BootUnit("settings", "00_config", True, provides=["settings"], rationale="Load paths and feature flags before anything else."),
    BootUnit("registry", "01_kernel", True, depends_on=["settings"], provides=["service_lookup"], rationale="Every subsystem needs one address book."),
    BootUnit("event_bus", "01_kernel", True, depends_on=["registry"], provides=["event_pubsub", "event_history"], rationale="Cross-system talk goes through events, not random imports."),
    BootUnit("session_state", "01_kernel", True, depends_on=["registry", "event_bus"], provides=["runtime_truth"], rationale="One boring source of current room/avatar/engine/AI truth."),
    BootUnit("state_authority", "01_kernel", True, depends_on=["registry", "event_bus", "session_state"], provides=["runtime_state_authority", "transactional_truth"], rationale="Events and services do not become truth; runtime mutations go through one authority."),
    BootUnit("lifecycle", "01_kernel", True, depends_on=["registry"], provides=["lifecycle_state"], rationale="Known/active/degraded/failed must be uniform."),
    BootUnit("capabilities", "01_kernel", True, depends_on=["registry"], provides=["capability_lookup"], rationale="Engines and AIs register what they can do rather than owning startup."),
    BootUnit("jeeves", "01_kernel", True, depends_on=["registry", "event_bus", "session_state", "state_authority", "lifecycle", "capabilities"], provides=["resource_lifecycle_governance"], rationale="System-level hold/hibernate/off policy keeps CPU/RAM focused on current work."),
    BootUnit("pub_manager", "01_kernel", True, depends_on=["registry", "event_bus", "state_authority", "jeeves", "capabilities"], provides=["establishment_policy"], rationale="Pub Manager declares establishment-wide operating mode while Jeeves and local directors execute through the spine."),
    BootUnit("spine_contracts", "01_kernel", True, depends_on=["registry", "lifecycle"], provides=["contract_truth"], rationale="Systems must declare needs/provides before being crowned."),
    BootUnit("boot_order", "01_kernel", True, depends_on=["spine_contracts"], provides=["canonical_order"], rationale="The adjustable rail for future reordering."),
    BootUnit("spine_governor", "01_kernel", True, depends_on=["boot_order"], provides=["spine_policy_enforcement"], rationale="Keeps future systems from quietly growing alternate startup spines."),
    BootUnit("preflight", "02_diagnostics", True, depends_on=["settings", "boot_order"], provides=["launch_gate"], rationale="Fail honestly before optional systems hide the real problem."),
    BootUnit("asset_manifest", "03_assets", True, depends_on=["preflight"], provides=["avatar_asset_truth"], rationale="Manny/Sheila GLB truth before avatar runtime."),
    BootUnit("avatar_system", "04_avatars", False, depends_on=["asset_manifest", "state_authority", "event_bus"], provides=["avatar_runtime_state"], late_bound=True, rationale="Skeleton/avatar state plugs into the spine after asset truth."),
    BootUnit("world_system", "05_world", False, depends_on=["state_authority", "event_bus"], provides=["room_truth", "hotspots"], late_bound=True, rationale="Rooms update through state authority and emit events after truth changes."),
    BootUnit("bridge_system", "06_bridge", False, depends_on=["event_bus", "session_state"], provides=["websocket_bridge"], late_bound=True, rationale="Client/WebSocket bridges connect after truth stores exist."),
    BootUnit("motion_system", "06_bridge", False, depends_on=["avatar_system", "world_system", "event_bus", "session_state"], provides=["performer_motion_state", "mocap_input_hook"], late_bound=True, rationale="Walking/pose/interact truth reacts to avatar/world events; live mocap providers plug in later."),
    BootUnit("engine_runtime", "07_engines", False, depends_on=["event_bus", "session_state", "capabilities"], provides=["engine_capabilities"], late_bound=True, rationale="Multiple engines are capability providers, not the spine."),
    BootUnit("ai_router", "08_ai", False, depends_on=["event_bus", "session_state", "capabilities"], provides=["two_brain_routing"], late_bound=True, rationale="Persona and engine brains route through the spine; neither gets direct runtime control."),
    BootUnit("studio_brain", "08_ai", False, depends_on=["ai_router"], provides=["fast_director_advice"], late_bound=True, rationale="Fast brain advises/directs but does not own runtime truth."),
    BootUnit("architect_brain", "08_ai", False, depends_on=["ai_router"], provides=["slow_planning_advice"], late_bound=True, rationale="Slow planning/code brain stays optional and late-bound."),
    BootUnit("persistence", "09_persistence", False, depends_on=["session_state", "event_bus"], provides=["save_log_credit_records"], late_bound=True, rationale="Persistence records the run after truth/events exist."),
    BootUnit("legacy_containment", "10_legacy", False, depends_on=["registry"], provides=["startup_path_inventory"], late_bound=True, rationale="Old startup paths are inventoried non-destructively after canonical services exist."),
]


def phase_index_map(phases: Sequence[Tuple[str, str]] = BOOT_PHASES) -> Dict[str, int]:
    return {phase: index for index, (phase, _desc) in enumerate(phases)}


def validate_boot_units(units: Iterable[BootUnit], *, phases: Sequence[Tuple[str, str]] = BOOT_PHASES) -> List[str]:
    phase_index = phase_index_map(phases)
    seen: Dict[str, BootUnit] = {}
    problems: List[str] = []
    for unit in units:
        if not unit.system_id:
            problems.append("Boot unit has empty system_id")
            continue
        if unit.system_id in seen:
            problems.append(f"Duplicate boot unit: {unit.system_id}")
        seen[unit.system_id] = unit
        if unit.phase not in phase_index:
            problems.append(f"{unit.system_id} uses unknown phase: {unit.phase}")

    for unit in seen.values():
        for dependency in unit.depends_on:
            dep_unit = seen.get(dependency)
            if dep_unit is None:
                problems.append(f"{unit.system_id} depends on unknown boot unit: {dependency}")
                continue
            if phase_index.get(dep_unit.phase, 999) > phase_index.get(unit.phase, 999):
                problems.append(
                    f"{unit.system_id} in {unit.phase} depends on later-phase {dependency} in {dep_unit.phase}"
                )
    return problems


def resolve_boot_plan(units: Optional[Iterable[BootUnit]] = None) -> BootPlan:
    """Resolve units into a deterministic phase/dependency order."""

    source_units = list(units or DEFAULT_BOOT_UNITS)
    problems = validate_boot_units(source_units)
    phase_index = phase_index_map()
    units_by_id = {unit.system_id: unit for unit in source_units}
    remaining = dict(units_by_id)
    resolved: List[BootUnit] = []
    warnings: List[str] = []

    while remaining:
        ready = [
            unit for unit in remaining.values()
            if all(dep in {resolved_unit.system_id for resolved_unit in resolved} for dep in unit.depends_on)
        ]
        if not ready:
            problems.append("Boot order contains a dependency cycle or unsatisfied dependency cluster: " + ", ".join(sorted(remaining)))
            break
        ready.sort(key=lambda unit: (phase_index.get(unit.phase, 999), unit.system_id))
        chosen = ready[0]
        resolved.append(chosen)
        remaining.pop(chosen.system_id, None)

    # Policy warnings: useful, not fatal.
    for ai_id in ("studio_brain", "architect_brain"):
        unit = units_by_id.get(ai_id)
        if unit and not unit.late_bound:
            warnings.append(f"{ai_id} should remain late_bound so AI never owns spine startup")
    engine = units_by_id.get("engine_runtime")
    if engine and not engine.late_bound:
        warnings.append("engine_runtime should remain late_bound so no engine becomes the spine")

    return BootPlan(version=BOOT_ORDER_VERSION, phases=list(BOOT_PHASES), units=resolved, problems=problems, warnings=warnings)


def default_boot_plan_dict() -> Dict[str, Any]:
    return resolve_boot_plan().to_dict()
