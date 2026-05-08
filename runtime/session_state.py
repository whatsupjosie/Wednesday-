"""Canonical runtime session state.

This is the boring truth store. It does not render, infer, animate, or decide;
it records enough shared state that rooms, avatars, engines, AI agents, and UI
bridges stop inventing parallel realities.
"""
from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class AvatarRuntimeState:
    avatar_id: str
    asset_id: Optional[str] = None
    room_id: str = "waiting_room"
    pose: str = "idle"
    animation: str = "idle"
    mocap_active: bool = False
    position: Dict[str, float] = field(default_factory=lambda: {"x": 0.0, "y": 0.0, "z": 0.0})
    updated_at: float = field(default_factory=time.time)


@dataclass
class EngineRuntimeState:
    name: str
    mode: str = "offline"
    active: bool = False
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AIRuntimeState:
    name: str
    role: str
    mode: str = "offline"
    owns_execution: bool = False
    details: Dict[str, Any] = field(default_factory=dict)


class SessionState:
    def __init__(self) -> None:
        self.session_id: str = "local"
        self.current_room: str = "waiting_room"
        self.avatars: Dict[str, AvatarRuntimeState] = {}
        self.engines: Dict[str, EngineRuntimeState] = {}
        self.ai_agents: Dict[str, AIRuntimeState] = {}
        self.flags: Dict[str, Any] = {}
        self.created_at = time.time()
        self.updated_at = self.created_at

    def touch(self) -> None:
        self.updated_at = time.time()

    def set_room(self, room_id: str) -> None:
        self.current_room = room_id
        self.touch()

    def register_avatar(self, avatar_id: str, *, asset_id: Optional[str] = None, room_id: Optional[str] = None) -> AvatarRuntimeState:
        state = self.avatars.get(avatar_id) or AvatarRuntimeState(avatar_id=avatar_id)
        if asset_id is not None:
            state.asset_id = asset_id
        if room_id is not None:
            state.room_id = room_id
        state.updated_at = time.time()
        self.avatars[avatar_id] = state
        self.touch()
        return state

    def register_engine(self, name: str, *, mode: str = "offline", active: bool = False, **details: Any) -> EngineRuntimeState:
        state = EngineRuntimeState(name=name, mode=mode, active=active, details=details)
        self.engines[name] = state
        self.touch()
        return state

    def register_ai_agent(self, name: str, *, role: str, mode: str = "offline", owns_execution: bool = False, **details: Any) -> AIRuntimeState:
        state = AIRuntimeState(name=name, role=role, mode=mode, owns_execution=owns_execution, details=details)
        self.ai_agents[name] = state
        self.touch()
        return state

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "current_room": self.current_room,
            "avatars": {k: asdict(v) for k, v in sorted(self.avatars.items())},
            "engines": {k: asdict(v) for k, v in sorted(self.engines.items())},
            "ai_agents": {k: asdict(v) for k, v in sorted(self.ai_agents.items())},
            "flags": dict(self.flags),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
