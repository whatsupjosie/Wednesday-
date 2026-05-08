"""Canonical boot-phase ordering for PubCast.

Research-informed rule: boot the smallest stable kernel first, then register
plugins/engines/agents by dependency, not by excitement. AI and render engines
are late-bound providers; they must not own startup truth.
"""
from __future__ import annotations

BOOT_PHASES = [
    ("00_config", "Configuration, paths, feature flags"),
    ("01_kernel", "Registry, event bus, session state"),
    ("02_diagnostics", "Doctor/preflight and honest launch gate"),
    ("03_assets", "Asset manifests and source-of-truth checks"),
    ("04_avatars", "Skeleton authority, GLB avatar availability, animation state"),
    ("05_world", "Rooms, pubworld, hotspots, surfaces"),
    ("06_bridge", "Websocket/event bridge, studio/unity/mocap connectors"),
    ("07_engines", "Render/voxel/recording/performance engines"),
    ("08_ai", "Two-AI orchestration: studio brain and architect brain"),
    ("09_persistence", "Save files, logs, memory, credits"),
    ("10_legacy", "Non-destructive legacy containment and migration notes"),
]

REQUIRED_CORE_SERVICES = ["settings", "registry", "event_bus", "session_state", "preflight"]

AI_POLICY = {
    "studio_brain": "fast conversational/director brain; may be online/offline without blocking core boot",
    "architect_brain": "slower planning/code/design brain; must be late-bound and optional",
    "rule": "AI agents advise or route work; session_state and registry own runtime truth.",
}

ENGINE_POLICY = {
    "rule": "Engines register capabilities and health; they do not import each other directly or become the boot spine.",
    "preferred_order": ["performance", "recording", "voxel", "render", "mocap", "unity_bridge"],
}
