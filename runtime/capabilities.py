"""Capability registry for engines, AI providers, bridges, and optional systems."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Capability:
    name: str
    provider: str
    phase: str
    available: bool = False
    required: bool = False
    priority: int = 100
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class CapabilityRegistry:
    """Answers: what can this runtime do right now, and who provides it?"""

    def __init__(self) -> None:
        self._capabilities: Dict[str, List[Capability]] = {}

    def register(self, capability: Capability) -> Capability:
        providers = self._capabilities.setdefault(capability.name, [])
        providers[:] = [item for item in providers if item.provider != capability.provider]
        providers.append(capability)
        providers.sort(key=lambda item: (not item.available, item.priority, item.provider))
        return capability

    def best(self, name: str) -> Optional[Capability]:
        for capability in self._capabilities.get(name, []):
            if capability.available:
                return capability
        return None

    def providers(self, name: str) -> List[Dict[str, Any]]:
        return [item.to_dict() for item in self._capabilities.get(name, [])]

    def to_dict(self) -> Dict[str, Any]:
        return {name: [item.to_dict() for item in providers] for name, providers in sorted(self._capabilities.items())}


def seed_core_capabilities(registry: CapabilityRegistry) -> None:
    registry.register(Capability("runtime_truth", "session_state", "01_kernel", available=True, required=True, priority=0))
    registry.register(Capability("runtime_state_authority", "state_authority", "01_kernel", available=False, required=True, priority=0))
    registry.register(Capability("establishment_policy", "pub_manager", "01_kernel", available=False, required=True, priority=0))
    registry.register(Capability("event_pubsub", "event_bus", "01_kernel", available=True, required=True, priority=0))
    registry.register(Capability("launch_gate", "preflight", "02_diagnostics", available=True, required=True, priority=0))
    registry.register(Capability("avatar_asset_truth", "avatar_manifest", "03_assets", available=True, required=True, priority=10))
    registry.register(Capability("studio_brain", "late_bound_ai_provider", "08_ai", available=False, required=False, priority=50))
    registry.register(Capability("architect_brain", "late_bound_ai_provider", "08_ai", available=False, required=False, priority=60))
    registry.register(Capability("render_engine", "late_bound_engine_provider", "07_engines", available=False, required=False, priority=50))
    registry.register(Capability("mocap_input", "late_bound_bridge_provider", "06_bridge", available=False, required=False, priority=50))
