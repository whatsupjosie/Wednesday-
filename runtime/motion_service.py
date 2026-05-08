"""Spine-owned performer/motion state service."""
from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Literal


MotionState = Literal["idle", "walking", "posing", "interacting", "unavailable"]
ALLOWED_MOTION_STATES = ["idle", "walking", "posing", "interacting", "unavailable"]


@dataclass
class PerformerMotionRecord:
    avatar_id: str
    state: MotionState = "idle"
    source: str = "spine"
    details: Dict[str, Any] = field(default_factory=dict)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MotionStateService:
    def __init__(self, registry: Any):
        self.registry = registry
        self.session_state = registry.require("session_state")
        self.event_bus = registry.require("event_bus")
        self.started_at = time.time()
        self.records: Dict[str, PerformerMotionRecord] = {}

        self.event_bus.subscribe("avatar.moved", self._on_avatar_moved)
        for avatar_id in self.session_state.avatars:
            self.set_state(avatar_id, "idle", source="boot")

    async def _on_avatar_moved(self, event: Any) -> None:
        avatar_id = event.payload.get("avatar_id")
        if not avatar_id:
            return

        record = self.set_state(
            str(avatar_id),
            "walking",
            source=event.source,
            from_room=event.payload.get("from_room"),
            to_room=event.payload.get("to_room"),
        )
        await self.event_bus.emit(
            "motion.state_changed",
            record.to_dict(),
            source="motion_system",
        )

    def set_state(
        self,
        avatar_id: str,
        state: MotionState,
        *,
        source: str = "spine",
        **details: Any,
    ) -> PerformerMotionRecord:
        record = self.records.get(avatar_id) or PerformerMotionRecord(
            avatar_id=avatar_id
        )
        record.state = state
        record.source = source
        record.details.update(details)
        record.updated_at = time.time()
        self.records[avatar_id] = record

        avatar = self.session_state.avatars.get(avatar_id)
        if avatar is not None:
            avatar.animation = state
            avatar.pose = "idle" if state == "walking" else state
            avatar.updated_at = time.time()
            self.session_state.touch()

        return record

    def status(self) -> Dict[str, Any]:
        missing = [
            avatar_id
            for avatar_id in self.session_state.avatars
            if avatar_id not in self.records
        ]
        return {
            "ok": True,
            "service": "motion_state",
            "started_at": self.started_at,
            "allowed_states": list(ALLOWED_MOTION_STATES),
            "summary": {
                "tracked_avatars": len(self.records),
                "untracked_session_avatars": len(missing),
            },
            "untracked_session_avatars": missing,
            "records": {
                avatar_id: record.to_dict()
                for avatar_id, record in sorted(self.records.items())
            },
            "webcam_mocap_ready": False,
            "notes": (
                "Owns performer state now; webcam/mocap ingestion remains a later "
                "provider hook."
            ),
        }


def register_motion_service(registry: Any) -> MotionStateService:
    service = MotionStateService(registry)
    capabilities = registry.get("capabilities")

    if capabilities is not None:
        from .capabilities import Capability

        capabilities.register(
            Capability(
                "performer_motion_state",
                "motion_system",
                "06_bridge",
                available=True,
                required=False,
                priority=0,
            )
        )
        capabilities.register(
            Capability(
                "mocap_input",
                "motion_system",
                "06_bridge",
                available=False,
                required=False,
                priority=40,
                details={"reason": "provider hook declared; live webcam/mocap not wired"},
            )
        )

    lifecycle = registry.get("lifecycle")
    if lifecycle is not None:
        lifecycle.set_state(
            "motion_system",
            "active",
            message="Motion state is spine-owned; live mocap provider is pending",
        )

    registry.register(
        "motion_system",
        service,
        phase="06_bridge",
        required=False,
        state="ready",
        message="Motion service owns performer states",
        details=service.status()["summary"],
    )
    return service
