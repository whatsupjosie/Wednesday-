"""PubCast runtime event bus.

This is the cross-system handshake layer: avatars, rooms, AI agents, engines,
and UI bridges should communicate by events instead of tight direct imports.
"""
from __future__ import annotations

import inspect
import time
from collections import defaultdict, deque
from dataclasses import asdict, dataclass, field
from typing import Any, Awaitable, Callable, Deque, Dict, List, MutableMapping, Optional

Handler = Callable[["RuntimeEvent"], Any]


@dataclass
class RuntimeEvent:
    type: str
    payload: Dict[str, Any] = field(default_factory=dict)
    source: str = "system"
    ts: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class EventBus:
    def __init__(self, *, history_limit: int = 250) -> None:
        self._subscribers: MutableMapping[str, List[Handler]] = defaultdict(list)
        self._history: Deque[RuntimeEvent] = deque(maxlen=history_limit)

    def subscribe(self, event_type: str, handler: Handler) -> None:
        if handler not in self._subscribers[event_type]:
            self._subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: Handler) -> None:
        if handler in self._subscribers.get(event_type, []):
            self._subscribers[event_type].remove(handler)

    async def emit(self, event_type: str, payload: Optional[Dict[str, Any]] = None, *, source: str = "system") -> RuntimeEvent:
        event = RuntimeEvent(type=event_type, payload=payload or {}, source=source)
        self._history.append(event)
        handlers = list(self._subscribers.get(event_type, [])) + list(self._subscribers.get("*", []))
        for handler in handlers:
            result = handler(event)
            if inspect.isawaitable(result):
                await result
        return event

    def history(self, *, limit: int = 50) -> List[Dict[str, Any]]:
        return [event.to_dict() for event in list(self._history)[-limit:]]

    def subscriber_counts(self) -> Dict[str, int]:
        return {event_type: len(handlers) for event_type, handlers in sorted(self._subscribers.items())}
