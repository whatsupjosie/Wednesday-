from __future__ import annotations
import asyncio
from pathlib import Path
from fastapi import FastAPI
from runtime.boot_sequence import attach_spine, install_spine_routes

def make_app_and_registry():
    app = FastAPI(); registry = attach_spine(app, root=Path.cwd()); install_spine_routes(app); return app, registry

def test_continuous_spine_services_register_cleanly():
    _app, registry = make_app_and_registry()
    for name in ["state_authority","jeeves","pub_manager","world_system","bridge_system","motion_system","ai_router","persistence","doctor_dashboard","legacy_containment"]:
        assert registry.get(name) is not None, name
    assert registry.summary()["required_failures"] == []

def test_spine_routes_expose_continuous_job_layers():
    app, _registry = make_app_and_registry(); paths = {route.path for route in app.routes}
    expected = {"/api/spine/state/status","/api/spine/state/snapshot","/api/spine/jeeves/status","/api/spine/jeeves/touch","/api/spine/jeeves/evaluate","/api/spine/pub-manager/status","/api/spine/pub-manager/evaluate","/api/spine/world/status","/api/spine/world/move-avatar","/api/spine/bridge/status","/api/spine/motion/status","/api/spine/ai/status","/api/spine/ai/route","/api/spine/session/status","/api/spine/session/save","/api/spine/doctor","/api/spine/legacy/status"}
    assert expected.issubset(paths)

def test_state_authority_declares_truth_and_transactions():
    _app, registry = make_app_and_registry(); authority = registry.require("state_authority")
    status = authority.status()
    assert status["service"] == "state_authority"
    assert "avatar" in status["canonical_event_namespaces"]
    assert "hibernated" in status["runtime_state_classes"]
    assert registry.require("capabilities").best("runtime_state_authority") is not None
    try:
        authority.begin_transaction(source="test").emit("bad_event")
    except ValueError:
        pass
    else:
        raise AssertionError("State authority accepted a non-canonical event name")

def test_jeeves_declares_system_level_hold_hibernate_off_policy():
    _app, registry = make_app_and_registry(); jeeves = registry.require("jeeves")
    status = jeeves.status()
    assert status["profile"] == "Gentle Saver"
    assert {"active","holding","hibernated","off","protected"}.issubset(set(status["policy"]["states"]))
    assert registry.require("capabilities").best("resource_lifecycle_governance") is not None

def test_pub_manager_declares_establishment_policy_without_direct_control():
    _app, registry = make_app_and_registry(); manager = registry.require("pub_manager")
    status = manager.status()
    assert status["service"] == "pub_manager"
    assert status["mode"] == "open"
    assert {"open","quiet","busy","crowded","maintenance","recovery","emergency"}.issubset(set(status["available_modes"]))
    assert "does_not_control_engines_directly" in status["boundaries"]
    assert registry.require("capabilities").best("establishment_policy") is not None
    result = asyncio.run(manager.evaluate(requested_mode="busy", source="test"))
    assert result["decision"]["mode"] == "busy"
    assert registry.require("event_bus").history(limit=1)[0]["type"] == "pub_manager.mode.evaluated"

def test_world_move_emits_bridge_events_and_updates_motion():
    _app, registry = make_app_and_registry(); world = registry.require("world_system")
    result = asyncio.run(world.move_avatar("manny", "stage", source="test"))
    assert result["ok"] is True
    assert result["state_revision"] >= 1
    assert result["transaction_id"]
    assert registry.require("session_state").avatars["manny"].room_id == "stage"
    event_types = [event["type"] for event in registry.require("event_bus").history(limit=10)]
    for item in ["room.left","room.entered","avatar.moved","motion.state_changed","world.state.changed","state.transaction.committed"]: assert item in event_types
    assert registry.require("motion_system").status()["records"]["manny"]["state"] == "walking"
    assert registry.require("bridge_system").status()["recent_broadcasts"]
    assert "session.participant_registered" in registry.require("bridge_system").status()["canonical_events"]

def test_unknown_room_fails_honestly_without_moving_avatar():
    _app, registry = make_app_and_registry(); world = registry.require("world_system"); before = registry.require("session_state").avatars["sheila"].room_id
    result = asyncio.run(world.move_avatar("sheila", "fake_void", source="test"))
    assert result["ok"] is False
    assert registry.require("session_state").avatars["sheila"].room_id == before
    assert registry.require("event_bus").history(limit=1)[0]["type"] == "world.move_rejected"

def test_ai_router_separates_persona_and_engine_without_direct_control():
    _app, registry = make_app_and_registry(); router = registry.require("ai_router")
    persona = asyncio.run(router.route_request("welcome guest to waiting room")); engine = asyncio.run(router.route_request("engine resource advice for render load"))
    assert persona["role"] == "persona"; assert engine["role"] == "engine"
    assert persona["direct_control_granted"] is False and engine["direct_control_granted"] is False
    assert router.status()["direct_control_violations"] == []

def test_persistence_snapshot_is_export_only():
    _app, registry = make_app_and_registry(); persistence = registry.require("persistence"); snapshot = persistence.make_snapshot()
    assert snapshot["ok"] is True and "session" in snapshot and "event_history" in snapshot
    assert persistence.status()["import_supported"] is False

def test_persistence_sanitizes_snapshot_labels():
    from runtime.persistence_service import _safe_snapshot_label

    assert _safe_snapshot_label("../bad label") == "bad_label"
    assert _safe_snapshot_label("   ") == "manual"

def test_legacy_containment_treats_baggage_as_contained():
    _app, registry = make_app_and_registry(); legacy = registry.require("legacy_containment")
    status = legacy.status()
    assert status["ok"] is True
    for item in status["candidates"]:
        if item["path"].startswith("baggage/"):
            assert item["category"] == "contained_legacy"

def test_doctor_report_unifies_spine_layers():
    _app, registry = make_app_and_registry(); from runtime.doctor_dashboard import build_spine_doctor_report
    report = build_spine_doctor_report(registry)
    assert report["ok"] is True
    for key in ["avatar_truth","world_truth","state_authority","pub_manager","bridge_status","jeeves_status","motion_status","ai_status","session_status","persistence_status","legacy_containment"]: assert key in report
