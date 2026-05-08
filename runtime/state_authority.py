"""Canonical runtime state authority for PubCast.

Events describe what happened. Services do the work. This service owns the
official mutation gate for current runtime truth.
"""
from __future__ import annotations

import time
import uuid
from collections import deque
from dataclasses import asdict, dataclass, field
from typing import Any, Deque, Dict, List, Optional


CANONICAL_EVENT_NAMESPACES = (
    "system",
    "spine",
    "state",
    "avatar",
    "world",
    "room",
    "motion",
    "camera",
    "session",
    "recording",
    "ai",
    "client",
    "memory",
    "jeeves",
    "engine",
    "legacy",
)

RUNTIME_STATE_CLASSES = (
    "registered",
    "available",
    "warm",
    "active",
    "holding",
    "hibernated",
    "off",
    "failed",
    "locked",
    "legacy",
)


@dataclass
class StateOperation:
    action: str
    target: str
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class QueuedEvent:
    type: str
    payload: Dict[str, Any] = field(default_factory=dict)
    source: str = "state_authority"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TransactionRecord:
    transaction_id: str
    source: str
    reason: str
    status: str = "pending"
    created_at: float = field(default_factory=time.time)
    committed_at: Optional[float] = None
    operations: List[StateOperation] = field(default_factory=list)
    events: List[QueuedEvent] = field(default_factory=list)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "transaction_id": self.transaction_id,
            "source": self.source,
            "reason": self.reason,
            "status": self.status,
            "created_at": self.created_at,
            "committed_at": self.committed_at,
            "operations": [operation.to_dict() for operation in self.operations],
            "events": [event.to_dict() for event in self.events],
            "error": self.error,
        }


class StateTransaction:
    def __init__(self, authority: "StateAuthority", *, source: str, reason: str) -> None:
        self.authority = authority
        self.record = TransactionRecord(
            transaction_id=uuid.uuid4().hex,
            source=source,
            reason=reason,
        )

    def register_avatar(self, avatar_id: str, *, asset_id: Optional[str] = None, room_id: Optional[str] = None) -> "StateTransaction":
        self.record.operations.append(
            StateOperation(
                "register_avatar",
                avatar_id,
                {"asset_id": asset_id, "room_id": room_id},
            )
        )
        return self

    def move_avatar(self, avatar_id: str, room_id: str, *, asset_id: Optional[str] = None) -> "StateTransaction":
        self.record.operations.append(
            StateOperation(
                "move_avatar",
                avatar_id,
                {"room_id": room_id, "asset_id": asset_id},
            )
        )
        return self

    def set_current_room(self, room_id: str) -> "StateTransaction":
        self.record.operations.append(StateOperation("set_current_room", "session", {"room_id": room_id}))
        return self

    def emit(self, event_type: str, payload: Optional[Dict[str, Any]] = None, *, source: Optional[str] = None) -> "StateTransaction":
        self.authority.validate_event_type(event_type)
        self.record.events.append(QueuedEvent(event_type, payload or {}, source or self.record.source))
        return self

    async def commit(self) -> Dict[str, Any]:
        return await self.authority.commit(self)

    def rollback(self, error: str = "rolled_back") -> Dict[str, Any]:
        self.record.status = "rolled_back"
        self.record.error = error
        self.authority._remember(self.record)
        return self.record.to_dict()


class StateAuthority:
    def __init__(self, registry: Any) -> None:
        self.registry = registry
        self.session_state = registry.require("session_state")
        self.event_bus = registry.require("event_bus")
        self.revision = 0
        self.started_at = time.time()
        self._history: Deque[TransactionRecord] = deque(maxlen=100)

    def begin_transaction(self, *, source: str = "state_authority", reason: str = "runtime_mutation") -> StateTransaction:
        return StateTransaction(self, source=source, reason=reason)

    def validate_event_type(self, event_type: str) -> None:
        namespace = event_type.split(".", 1)[0]
        if "." not in event_type or namespace not in CANONICAL_EVENT_NAMESPACES:
            raise ValueError(f"Event type is outside canonical namespaces: {event_type}")

    async def commit(self, transaction: StateTransaction) -> Dict[str, Any]:
        record = transaction.record
        if record.status != "pending":
            raise RuntimeError(f"Transaction is already {record.status}")
        try:
            for operation in record.operations:
                self._apply_operation(operation)
            self.revision += 1
            record.status = "committed"
            record.committed_at = time.time()
            self._remember(record)
            for event in record.events:
                await self.event_bus.emit(event.type, event.payload, source=event.source)
            await self.event_bus.emit(
                "state.transaction.committed",
                {
                    "transaction_id": record.transaction_id,
                    "revision": self.revision,
                    "operation_count": len(record.operations),
                    "event_count": len(record.events),
                },
                source="state_authority",
            )
            return {"ok": True, "transaction": record.to_dict(), "revision": self.revision}
        except Exception as exc:
            record.status = "failed"
            record.error = str(exc)
            self._remember(record)
            raise

    def _apply_operation(self, operation: StateOperation) -> None:
        if operation.action == "register_avatar":
            self.session_state.register_avatar(
                operation.target,
                asset_id=operation.payload.get("asset_id"),
                room_id=operation.payload.get("room_id"),
            )
            return
        if operation.action == "move_avatar":
            current = self.session_state.avatars.get(operation.target)
            self.session_state.register_avatar(
                operation.target,
                asset_id=operation.payload.get("asset_id") or (current.asset_id if current else None),
                room_id=operation.payload["room_id"],
            )
            return
        if operation.action == "set_current_room":
            self.session_state.set_room(operation.payload["room_id"])
            return
        raise ValueError(f"Unknown state operation: {operation.action}")

    def _remember(self, record: TransactionRecord) -> None:
        self._history.append(record)

    def snapshot(self) -> Dict[str, Any]:
        return self.session_state.to_dict()

    def status(self) -> Dict[str, Any]:
        return {
            "ok": True,
            "service": "state_authority",
            "message": "State authority is canonical runtime truth; events are history, not truth.",
            "revision": self.revision,
            "started_at": self.started_at,
            "canonical_event_namespaces": list(CANONICAL_EVENT_NAMESPACES),
            "runtime_state_classes": list(RUNTIME_STATE_CLASSES),
            "transaction_count": len(self._history),
            "recent_transactions": [record.to_dict() for record in list(self._history)[-10:]],
            "snapshot": self.snapshot(),
        }


def register_state_authority(registry: Any) -> StateAuthority:
    service = StateAuthority(registry)
    capabilities = registry.get("capabilities")
    if capabilities is not None:
        from .capabilities import Capability

        capabilities.register(
            Capability(
                "runtime_state_authority",
                "state_authority",
                "01_kernel",
                available=True,
                required=True,
                priority=0,
                details={
                    "canonical_event_namespaces": list(CANONICAL_EVENT_NAMESPACES),
                    "runtime_state_classes": list(RUNTIME_STATE_CLASSES),
                },
            )
        )
    registry.register(
        "state_authority",
        service,
        phase="01_kernel",
        required=True,
        state="ready",
        message="Runtime state authority ready",
        details={
            "canonical_event_namespaces": list(CANONICAL_EVENT_NAMESPACES),
            "runtime_state_classes": list(RUNTIME_STATE_CLASSES),
        },
    )
    return service
