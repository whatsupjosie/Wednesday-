"""Spine governor: policy checks that keep PubCast from growing new spines."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from .boot_order import BootPlan, resolve_boot_plan


@dataclass
class SpineDecision:
    ok: bool
    decision: str
    message: str
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SpineGovernor:
    """Central place for permanent spine laws.

    This intentionally stays small. It does not run engines or AI. It only says
    whether the runtime still obeys the declared spine policy.
    """

    def __init__(self, *, boot_plan: Optional[BootPlan] = None) -> None:
        self.boot_plan = boot_plan or resolve_boot_plan()
        self.decisions: List[SpineDecision] = []

    def evaluate(self, registry: Any) -> SpineDecision:
        service_names = set(registry.names()) if registry is not None else set()
        required_units = [unit.system_id for unit in self.boot_plan.units if unit.required]
        missing = [system_id for system_id in required_units if system_id not in service_names]
        required_failures = []
        if registry is not None:
            summary = registry.summary()
            required_failures = list(summary.get("required_failures", []))

        ok = self.boot_plan.ok and not missing and not required_failures
        decision = SpineDecision(
            ok=ok,
            decision="spine_governed" if ok else "spine_attention_required",
            message="Canonical spine is attached and required services are present" if ok else "Canonical spine needs attention",
            details={
                "boot_plan_ok": self.boot_plan.ok,
                "missing_required_units": missing,
                "required_failures": required_failures,
                "boot_plan_problems": list(self.boot_plan.problems),
                "boot_plan_warnings": list(self.boot_plan.warnings),
            },
        )
        self.decisions.append(decision)
        return decision

    def to_dict(self) -> Dict[str, Any]:
        return {
            "boot_plan": self.boot_plan.to_dict(),
            "latest_decision": self.decisions[-1].to_dict() if self.decisions else None,
            "decisions": [decision.to_dict() for decision in self.decisions[-25:]],
        }
