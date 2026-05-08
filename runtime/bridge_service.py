"""Spine-owned bridge between runtime events and future UI/WebSocket clients."""
from __future__ import annotations

import time
from collections import deque
from dataclasses import asdict, dataclass, field
from typing import Any, Deque, Dict, List


CANONICAL_RUNTIME_EVENTS: List[str] = [
    "avatar.registered",
    "avatar.moved",
    "avatar.state_changed",
    "room.entered",
    "room.left",
    "world.state.changed",
    "world.move_rejected",
    "motion.state_changed",
    "ai.request.routed",
    "session.participant_registered",
    "session.snapshot.saved",
    "client.connected",
    "client.disconnected",
    "client.command",
    "jeeves.policy.evaluated",
]


@dataclass
class BridgeMessage:
    event_type: str
    payload: Dict[str, Any]
    source: str
    ts: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SpineBridgeService:
    def __init__(self, registry: Any, *, history_limit: int = 250):
        self.registry = registry
        self.event_bus = registry.require("event_bus")
        self.session_state = registry.require("session_state")
        self.started_at = time.time()
        self.connected_clients = 0
        self.broadcast_history: Deque[BridgeMessage] = deque(maxlen=history_limit)
        self.event_bus.subscribe("*", self._capture_event)

    def _capture_event(self, event: Any) -> None:
        self.broadcast_history.append(
            BridgeMessage(event.type, dict(event.payload), event.source, event.ts)
        )

    def status(self) -> Dict[str, Any]:
        return {
            "ok": True,
            "service": "spine_bridge",
            "started_at": self.started_at,
            "connected_clients": self.connected_clients,
            "canonical_events": list(CANONICAL_RUNTIME_EVENTS),
            "subscriber_counts": self.event_bus.subscriber_counts(),
            "recent_broadcasts": [
                item.to_dict() for item in list(self.broadcast_history)[-25:]
            ],
            "notes": (
                "Bridge hooks are ready; legacy UI pages do not need rewriting in "
                "this patch."
            ),
        }


def register_bridge_service(registry: Any) -> SpineBridgeService:
    service = SpineBridgeService(registry)
    capabilities = registry.get("capabilities")

    if capabilities is not None:
        from .capabilities import Capability

        capabilities.register(
            Capability(
                "websocket_bridge",
                "bridge_system",
                "06_bridge",
                available=True,
                required=False,
                priority=0,
                details={"canonical_events": CANONICAL_RUNTIME_EVENTS},
            )
        )

    lifecycle = registry.get("lifecycle")
    if lifecycle is not None:
        lifecycle.set_state(
            "bridge_system",
            "active",
            message="Event bridge is capturing spine events",
        )

    registry.register(
        "bridge_system",
        service,
        phase="06_bridge",
        required=False,
        state="ready",
        message="Spine bridge captures runtime events",
        details={"canonical_events": CANONICAL_RUNTIME_EVENTS},
    )
    return service
