from __future__ import annotations

import time
from typing import Any, Dict, Optional


DEFAULT_ACTION_OBJECTS: Dict[str, Dict[str, Any]] = {
    "hold_coffee": {
        "object_id": "coffee_mug_01",
        "attach_to": "Hand_R",
        "duration": 2.0,
    },
    "work_console": {
        "object_id": "console_01",
        "attach_to": "Hand_R",
        "duration": 3.2,
    },
    "film_camera": {
        "object_id": "cinema_camera_01",
        "attach_to": "Hand_R",
        "duration": 3.2,
    },
}

CHOREOGRAPHY_LAB_ACTIONS = ["walk", "hold_coffee", "work_console"]

VISUAL_ASSET_STATUS: Dict[str, Dict[str, str]] = {
    "manny": {
        "status": "glb_present",
        "url": "/assets/avatar/manny.glb",
    },
    "sheila": {
        "status": "glb_present",
        "url": "/assets/avatar/sheila.glb",
    },
    "baby_humphrey": {
        "status": "reference_image_present",
        "url": "/assets/avatar/baby_humphrey_reference.webp",
        "glb_status": "not_available",
    },
}

CANNED_MOCAP_FRAMES: Dict[str, Dict[str, Any]] = {
    "manny": {
        "rigId": "rig-manny-lab",
        "frameNumber": 101,
        "joints": {
            "hips": {"x": 0.0, "y": 1.02, "z": 0.0, "confidence": 0.99},
            "spine": {"x": 0.0, "y": 1.38, "z": 0.02, "confidence": 0.98},
            "chest": {"x": 0.0, "y": 1.62, "z": 0.04, "confidence": 0.96},
            "head": {"x": 0.0, "y": 1.88, "z": 0.03, "confidence": 0.95},
            "left_wrist": {"x": -0.48, "y": 1.32, "z": 0.16, "confidence": 0.94},
            "right_wrist": {"x": 0.38, "y": 1.26, "z": 0.28, "confidence": 0.92},
            "left_ankle": {"x": -0.16, "y": 0.1, "z": 0.05, "confidence": 0.93},
            "right_ankle": {"x": 0.24, "y": 0.11, "z": -0.08, "confidence": 0.93},
        },
    },
    "sheila": {
        "rigId": "rig-sheila-lab",
        "frameNumber": 202,
        "joints": {
            "hips": {"x": 0.08, "y": 1.0, "z": 0.0, "confidence": 0.99},
            "spine": {"x": 0.05, "y": 1.34, "z": -0.03, "confidence": 0.98},
            "chest": {"x": 0.03, "y": 1.58, "z": -0.05, "confidence": 0.97},
            "head": {"x": 0.02, "y": 1.84, "z": -0.02, "confidence": 0.96},
            "left_wrist": {"x": -0.34, "y": 1.2, "z": 0.24, "confidence": 0.93},
            "right_wrist": {"x": 0.52, "y": 1.42, "z": 0.1, "confidence": 0.94},
            "left_ankle": {"x": -0.22, "y": 0.09, "z": -0.06, "confidence": 0.92},
            "right_ankle": {"x": 0.19, "y": 0.1, "z": 0.08, "confidence": 0.92},
        },
    },
    "baby_humphrey": {
        "rigId": "rig-baby-humphrey-lab",
        "frameNumber": 303,
        "joints": {
            "hips": {"x": -0.04, "y": 1.01, "z": 0.0, "confidence": 0.99},
            "spine": {"x": -0.02, "y": 1.36, "z": 0.01, "confidence": 0.98},
            "chest": {"x": 0.0, "y": 1.6, "z": 0.03, "confidence": 0.97},
            "head": {"x": 0.01, "y": 1.86, "z": 0.02, "confidence": 0.96},
            "left_wrist": {"x": -0.44, "y": 1.28, "z": 0.12, "confidence": 0.94},
            "right_wrist": {"x": 0.44, "y": 1.34, "z": 0.16, "confidence": 0.94},
            "left_ankle": {"x": -0.2, "y": 0.1, "z": 0.02, "confidence": 0.93},
            "right_ankle": {"x": 0.2, "y": 0.1, "z": -0.02, "confidence": 0.93},
        },
    },
}

VALID_INTERACTION_STATES = {"queued", "active", "complete", "cancelled"}


def _clean_text(value: Any, fallback: str = "") -> str:
    text = str(value or "").strip()
    return text or fallback


def _clean_duration(value: Any, fallback: float) -> float:
    try:
        duration = float(value)
    except (TypeError, ValueError):
        return fallback
    return max(0.0, min(duration, 120.0))


def build_avatar_object_interaction(
    payload: Dict[str, Any],
    *,
    now: Optional[float] = None,
) -> Dict[str, Any]:
    """Normalize the avatar-object interaction contract for lab/runtime use."""
    if not isinstance(payload, dict):
        raise ValueError("interaction payload must be a JSON object")

    avatar_id = _clean_text(payload.get("avatar_id"))
    action = _clean_text(payload.get("action")).lower()
    if not avatar_id:
        raise ValueError("avatar_id is required")
    if not action:
        raise ValueError("action is required")

    defaults = DEFAULT_ACTION_OBJECTS.get(action, {})
    object_id = _clean_text(payload.get("object_id"), defaults.get("object_id", ""))
    attach_to = _clean_text(payload.get("attach_to"), defaults.get("attach_to", "Hand_R"))
    duration = _clean_duration(payload.get("duration"), float(defaults.get("duration", 2.0)))
    state = _clean_text(payload.get("state"), "active").lower()
    if state not in VALID_INTERACTION_STATES:
        state = "active"

    return {
        "avatar_id": avatar_id,
        "action": action,
        "object_id": object_id,
        "attach_to": attach_to,
        "duration": duration,
        "state": state,
        "sent_at": now if now is not None else time.time(),
        "contract": "avatar_object_interaction.v1",
    }


def build_canned_mocap_frame(avatar_id: str, *, ts: Optional[int] = None) -> Dict[str, Any]:
    """Return a copy of a canned lab mocap frame with an avatar target."""
    target = _clean_text(avatar_id, "manny").lower()
    if target not in CANNED_MOCAP_FRAMES:
        raise ValueError(f"unknown canned avatar frame: {avatar_id!r}")
    source = CANNED_MOCAP_FRAMES[target]
    frame = {
        "avatar_id": target,
        "rigId": source["rigId"],
        "frameNumber": source["frameNumber"],
        "joints": {
            name: dict(joint)
            for name, joint in source["joints"].items()
        },
    }
    frame["ts"] = ts if ts is not None else int(time.time() * 1000)
    return frame


def build_motion_lab_config(*, now: Optional[float] = None) -> Dict[str, Any]:
    """Shared vocabulary/config for the browser motion proof surface."""
    generated_at = now if now is not None else time.time()
    sample_frames = {
        avatar_id: build_canned_mocap_frame(avatar_id, ts=int(generated_at * 1000))
        for avatar_id in CANNED_MOCAP_FRAMES
    }
    return {
        "contract": "avatar_motion_lab.v1",
        "generated_at": generated_at,
        "avatars": list(CANNED_MOCAP_FRAMES.keys()),
        "visual_assets": {
            avatar_id: dict(VISUAL_ASSET_STATUS.get(avatar_id, {"status": "unknown", "url": ""}))
            for avatar_id in CANNED_MOCAP_FRAMES
        },
        "sample_frames": sample_frames,
        "choreography_cues": list(CHOREOGRAPHY_LAB_ACTIONS),
        "interaction_defaults": {
            action: dict(defaults)
            for action, defaults in DEFAULT_ACTION_OBJECTS.items()
            if action in CHOREOGRAPHY_LAB_ACTIONS
        },
        "security_gating": "not_activated_by_motion_lab",
    }


__all__ = [
    "CANNED_MOCAP_FRAMES",
    "CHOREOGRAPHY_LAB_ACTIONS",
    "DEFAULT_ACTION_OBJECTS",
    "VALID_INTERACTION_STATES",
    "VISUAL_ASSET_STATUS",
    "build_avatar_object_interaction",
    "build_canned_mocap_frame",
    "build_motion_lab_config",
]
