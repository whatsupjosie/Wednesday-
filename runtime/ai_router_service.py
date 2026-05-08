"""Two-brain AI router declaration for the PubCast spine."""
from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Literal, Optional


AIBrainRole = Literal["persona", "engine"]
ENGINE_INTENT_TERMS = {"resource", "render", "engine", "code", "scene_plan", "boot_order"}


@dataclass(frozen=True)
class AIBrainContract:
    brain_id: str
    role: AIBrainRole
    display_name: str
    owns_execution: bool = False
    allowed_controls: List[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AIRouterService:
    def __init__(self, registry: Any):
        self.registry = registry
        self.session_state = registry.require("session_state")
        self.event_bus = registry.require("event_bus")
        self.started_at = time.time()
        self.brains = {
            "studio_brain": AIBrainContract(
                "studio_brain",
                "persona",
                "Studio / Persona Brain",
                False,
                ["speech", "character_interaction", "guest_experience"],
                "Handles personality/speech/hosting.",
            ),
            "engine_brain": AIBrainContract(
                "engine_brain",
                "engine",
                "Engine / Architect Brain",
                False,
                ["recommendations", "resource_advice", "scene_planning", "code_planning"],
                "Advises engine operations through spine-mediated requests.",
            ),
        }

        for brain in self.brains.values():
            self.session_state.register_ai_agent(
                brain.brain_id,
                role=brain.role,
                mode="declared",
                owns_execution=brain.owns_execution,
                allowed_controls=brain.allowed_controls,
            )

    async def route_request(
        self,
        intent: str,
        payload: Optional[Dict[str, Any]] = None,
        *,
        source: str = "ai_router",
    ) -> Dict[str, Any]:
        payload = payload or {}
        role: AIBrainRole = "engine" if self._is_engine_intent(intent) else "persona"
        brain = next(item for item in self.brains.values() if item.role == role)
        event_payload = {
            "intent": intent,
            "brain_id": brain.brain_id,
            "role": brain.role,
            "payload": payload,
            "direct_control_granted": False,
        }

        await self.event_bus.emit("ai.request.routed", event_payload, source=source)
        return {
            "ok": True,
            **event_payload,
            "message": (
                "Request routed; AI advice must return through spine-controlled "
                "actions."
            ),
        }

    def _is_engine_intent(self, intent: str) -> bool:
        lowered = intent.lower()
        return any(term in lowered for term in ENGINE_INTENT_TERMS)

    def status(self) -> Dict[str, Any]:
        violations = [brain.brain_id for brain in self.brains.values() if brain.owns_execution]
        return {
            "ok": not violations,
            "service": "ai_router",
            "started_at": self.started_at,
            "direct_control_violations": violations,
            "brains": {
                brain_id: brain.to_dict()
                for brain_id, brain in sorted(self.brains.items())
            },
            "rule": (
                "Persona AI and engine AI may advise/request; neither owns runtime "
                "truth or direct engine execution outside the spine."
            ),
        }


def register_ai_router_service(registry: Any) -> AIRouterService:
    service = AIRouterService(registry)
    status = service.status()
    capabilities = registry.get("capabilities")

    if capabilities is not None:
        from .capabilities import Capability

        capabilities.register(
            Capability(
                "studio_brain",
                "ai_router",
                "08_ai",
                available=True,
                required=False,
                priority=0,
                details={"role": "persona"},
            )
        )
        capabilities.register(
            Capability(
                "architect_brain",
                "ai_router",
                "08_ai",
                available=True,
                required=False,
                priority=0,
                details={"role": "engine"},
            )
        )

    lifecycle = registry.get("lifecycle")
    if lifecycle is not None:
        lifecycle.set_state(
            "ai_router",
            "active" if status["ok"] else "failed",
            message="Two-brain routing policy is spine-owned",
            violations=status["direct_control_violations"],
        )

    registry.register(
        "ai_router",
        service,
        phase="08_ai",
        required=False,
        state="ready" if status["ok"] else "failed",
        message="Two-brain AI router declared",
        details={"brains": list(service.brains)},
    )
    return service
