"""Canonical immutable semantic state for the EVO runtime.

All agents observe the same snapshot. State changes are produced by arbitration,
never by mutating a snapshot in place.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from threading import RLock
from time import time
from typing import Any, Mapping


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, float(value)))


@dataclass(frozen=True, slots=True)
class EmotionState:
    valence: float = 0.0
    intensity: float = 0.0
    stability: float = 1.0

    def normalized(self) -> "EmotionState":
        return replace(
            self,
            valence=_clamp(self.valence, -1.0, 1.0),
            intensity=_clamp(self.intensity, 0.0, 1.0),
            stability=_clamp(self.stability, 0.0, 1.0),
        )


@dataclass(frozen=True, slots=True)
class AudienceState:
    engagement: float = 0.5
    confusion: float = 0.0
    attention: float = 0.5

    def normalized(self) -> "AudienceState":
        return replace(
            self,
            engagement=_clamp(self.engagement, 0.0, 1.0),
            confusion=_clamp(self.confusion, 0.0, 1.0),
            attention=_clamp(self.attention, 0.0, 1.0),
        )


@dataclass(frozen=True, slots=True)
class SceneState:
    pacing: float = 0.5
    tension: float = 0.0
    momentum: float = 0.5

    def normalized(self) -> "SceneState":
        return replace(
            self,
            pacing=_clamp(self.pacing, 0.0, 1.0),
            tension=_clamp(self.tension, 0.0, 1.0),
            momentum=_clamp(self.momentum, 0.0, 1.0),
        )


@dataclass(frozen=True, slots=True)
class SafetyState:
    flags: Mapping[str, bool] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SemanticField:
    emotion: EmotionState = field(default_factory=EmotionState)
    audience: AudienceState = field(default_factory=AudienceState)
    scene: SceneState = field(default_factory=SceneState)
    safety: SafetyState = field(default_factory=SafetyState)
    revision: int = 0
    timestamp: float = field(default_factory=time)

    def normalized(self) -> "SemanticField":
        return replace(
            self,
            emotion=self.emotion.normalized(),
            audience=self.audience.normalized(),
            scene=self.scene.normalized(),
        )

    def snapshot(self) -> dict[str, Any]:
        return asdict(self)


class SemanticStore:
    """Thread-safe holder for the current immutable semantic snapshot."""

    def __init__(self, initial: SemanticField | None = None) -> None:
        self._state = (initial or SemanticField()).normalized()
        self._lock = RLock()

    def read(self) -> SemanticField:
        with self._lock:
            return self._state

    def commit(self, new_state: SemanticField, *, expected_revision: int | None = None) -> SemanticField:
        """Atomically publish a new state.

        expected_revision provides optimistic-concurrency protection for callers
        that need compare-and-swap semantics.
        """
        with self._lock:
            if expected_revision is not None and self._state.revision != expected_revision:
                raise RuntimeError(
                    f"semantic state revision conflict: expected {expected_revision}, "
                    f"found {self._state.revision}"
                )
            committed = replace(
                new_state.normalized(),
                revision=self._state.revision + 1,
                timestamp=time(),
            )
            self._state = committed
            return committed
