"""Spine-owned room/world truth for PubCast."""
from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterable, List, Optional


@dataclass(frozen=True)
class RoomRecord:
    room_id: str
    display_name: str
    kind: str = "room"
    canonical: bool = True
    allows_avatar_entry: bool = True
    description: str = ""
    exits: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


CANONICAL_ROOMS = [
    RoomRecord(
        "waiting_room",
        "Waiting Room",
        "liminal",
        True,
        True,
        "Guest landing zone before host admission.",
        ["dressing_room", "stage"],
    ),
    RoomRecord(
        "dressing_room",
        "Dressing Room",
        "private_runtime",
        True,
        True,
        "Per-user avatar/dressing room state.",
        ["waiting_room", "stage"],
    ),
    RoomRecord(
        "stage",
        "Stage",
        "production",
        True,
        True,
        "Primary performance/capture space.",
        ["dressing_room", "control_room", "world"],
    ),
    RoomRecord(
        "world",
        "World",
        "exploration",
        True,
        True,
        "General 3D world container.",
        ["stage", "map"],
    ),
    RoomRecord(
        "control_room",
        "Control Room",
        "operator",
        True,
        True,
        "Human/operator production controls.",
        ["stage", "broadcast_control"],
    ),
    RoomRecord(
        "broadcast_control",
        "Broadcast Control",
        "operator",
        True,
        True,
        "VTR/chyron/stream output controls.",
        ["control_room"],
    ),
    RoomRecord(
        "engine_room",
        "Engine Room",
        "technical",
        True,
        False,
        "Diagnostics and engine status space.",
        ["control_room"],
    ),
    RoomRecord(
        "map",
        "Map",
        "navigation",
        True,
        True,
        "Spatial navigation overview.",
        ["world", "stage"],
    ),
]


class WorldTruthService:
    def __init__(
        self,
        registry: Any,
        rooms: Optional[Iterable[RoomRecord]] = None,
    ) -> None:
        self.registry = registry
        self.session_state = registry.require("session_state")
        self.state_authority = registry.require("state_authority")
        self.event_bus = registry.require("event_bus")
        self.rooms = {room.room_id: room for room in (rooms or CANONICAL_ROOMS)}
        self.started_at = time.time()
        self.problems: List[str] = []
        self.warnings: List[str] = []
        self._validate()

    def _validate(self) -> None:
        self.problems = []
        self.warnings = []

        if "waiting_room" not in self.rooms:
            self.problems.append("Canonical world is missing waiting_room")

        for room in self.rooms.values():
            for exit_room in room.exits:
                if exit_room not in self.rooms:
                    self.warnings.append(
                        f"Room {room.room_id} exits to unknown room: {exit_room}"
                    )

    @property
    def ok(self) -> bool:
        return not self.problems

    def occupants(self) -> Dict[str, List[str]]:
        occupants = {room_id: [] for room_id in self.rooms}
        for avatar_id, avatar in self.session_state.avatars.items():
            occupants.setdefault(avatar.room_id, []).append(avatar_id)
        return {room_id: sorted(items) for room_id, items in sorted(occupants.items())}

    async def move_avatar(
        self,
        avatar_id: str,
        room_id: str,
        *,
        source: str = "world_system",
        reason: str = "requested",
    ) -> Dict[str, Any]:
        if room_id not in self.rooms:
            await self.event_bus.emit(
                "world.move_rejected",
                {
                    "avatar_id": avatar_id,
                    "room_id": room_id,
                    "reason": "unknown_room",
                },
                source=source,
            )
            return {
                "ok": False,
                "message": f"Unknown room: {room_id}",
                "avatar_id": avatar_id,
                "room_id": room_id,
            }

        room = self.rooms[room_id]
        if not room.allows_avatar_entry:
            await self.event_bus.emit(
                "world.move_rejected",
                {
                    "avatar_id": avatar_id,
                    "room_id": room_id,
                    "reason": "room_blocks_avatar_entry",
                },
                source=source,
            )
            return {
                "ok": False,
                "message": f"Room does not allow avatar entry: {room_id}",
                "avatar_id": avatar_id,
                "room_id": room_id,
            }

        avatar = self.session_state.avatars.get(avatar_id)
        previous_room_id = avatar.room_id if avatar is not None else "waiting_room"
        asset_id = avatar.asset_id if avatar is not None else None
        payload = {
            "avatar_id": avatar_id,
            "from_room": previous_room_id,
            "to_room": room_id,
            "reason": reason,
        }

        transaction = self.state_authority.begin_transaction(
            source=source,
            reason=f"move_avatar:{reason}",
        ).move_avatar(
            avatar_id,
            room_id,
            asset_id=asset_id,
        )

        if previous_room_id != room_id:
            transaction.emit(
                "room.left",
                {
                    "avatar_id": avatar_id,
                    "room_id": previous_room_id,
                    "to_room": room_id,
                },
                source=source,
            )
            transaction.emit(
                "room.entered",
                {
                    "avatar_id": avatar_id,
                    "room_id": room_id,
                    "from_room": previous_room_id,
                },
                source=source,
            )

        transaction.emit("avatar.moved", payload, source=source)
        transaction.emit(
            "world.state.changed",
            {"change": "avatar_room", **payload},
            source=source,
        )
        transaction_result = await transaction.commit()
        return {
            "ok": True,
            "avatar_id": avatar_id,
            "from_room": previous_room_id,
            "to_room": room_id,
            "room": room.to_dict(),
            "state_revision": transaction_result["revision"],
            "transaction_id": transaction_result["transaction"]["transaction_id"],
        }

    def status(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "service": "world_truth",
            "started_at": self.started_at,
            "state_revision": self.state_authority.revision,
            "summary": {
                "room_count": len(self.rooms),
                "problems": len(self.problems),
                "warnings": len(self.warnings),
            },
            "problems": list(self.problems),
            "warnings": list(self.warnings),
            "rooms": {room_id: room.to_dict() for room_id, room in sorted(self.rooms.items())},
            "occupants": self.occupants(),
        }


def register_world_service(registry: Any) -> WorldTruthService:
    service = WorldTruthService(registry)
    status = service.status()
    capabilities = registry.get("capabilities")

    if capabilities is not None:
        from .capabilities import Capability

        capabilities.register(
            Capability(
                "room_truth",
                "world_system",
                "05_world",
                available=service.ok,
                required=False,
                priority=0,
                details=status["summary"],
            )
        )

    lifecycle = registry.get("lifecycle")
    if lifecycle is not None:
        lifecycle.set_state(
            "world_system",
            "active" if service.ok else "failed",
            message=(
                "World/room truth is spine-owned"
                if service.ok
                else "World/room truth has problems"
            ),
            problems=status["problems"],
        )

    details = dict(status["summary"])
    details["problems"] = status["problems"]
    registry.register(
        "world_system",
        service,
        phase="05_world",
        required=False,
        state="ready" if service.ok else "failed",
        message="World service owns canonical room truth",
        details=details,
    )
    return service
