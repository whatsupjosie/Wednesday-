from __future__ import annotations

from modules.avatar_motion_contract import (
    build_avatar_object_interaction,
    build_canned_mocap_frame,
    build_motion_lab_config,
)


def test_avatar_object_interaction_uses_action_defaults():
    contract = build_avatar_object_interaction(
        {"avatar_id": "manny", "action": "hold_coffee"},
        now=123.0,
    )

    assert contract["avatar_id"] == "manny"
    assert contract["action"] == "hold_coffee"
    assert contract["object_id"] == "coffee_mug_01"
    assert contract["attach_to"] == "Hand_R"
    assert contract["duration"] == 2.0
    assert contract["state"] == "active"
    assert contract["sent_at"] == 123.0
    assert contract["contract"] == "avatar_object_interaction.v1"


def test_avatar_object_interaction_allows_explicit_object_contract():
    contract = build_avatar_object_interaction(
        {
            "avatar_id": "sheila",
            "action": "work_console",
            "object_id": "console_keyboard_01",
            "attach_to": "Hand_L",
            "duration": 4.5,
            "state": "queued",
        },
        now=456.0,
    )

    assert contract["avatar_id"] == "sheila"
    assert contract["object_id"] == "console_keyboard_01"
    assert contract["attach_to"] == "Hand_L"
    assert contract["duration"] == 4.5
    assert contract["state"] == "queued"


def test_avatar_object_interaction_rejects_missing_required_fields():
    try:
        build_avatar_object_interaction({"avatar_id": "manny"})
    except ValueError as exc:
        assert "action is required" in str(exc)
    else:
        raise AssertionError("missing action should fail")


def test_canned_mocap_frame_targets_avatar_and_rig():
    frame = build_canned_mocap_frame("sheila", ts=1700000000000)

    assert frame["avatar_id"] == "sheila"
    assert frame["rigId"] == "rig-sheila-lab"
    assert frame["ts"] == 1700000000000
    assert frame["joints"]["right_wrist"]["confidence"] == 0.94


def test_motion_lab_config_shares_frames_cues_and_interaction_defaults():
    config = build_motion_lab_config(now=1700000000.0)

    assert config["contract"] == "avatar_motion_lab.v1"
    assert config["sample_frames"]["manny"]["avatar_id"] == "manny"
    assert config["sample_frames"]["baby_humphrey"]["rigId"] == "rig-baby-humphrey-lab"
    assert config["visual_assets"]["manny"]["status"] == "glb_present"
    assert config["visual_assets"]["baby_humphrey"]["status"] == "reference_image_present"
    assert config["visual_assets"]["baby_humphrey"]["glb_status"] == "not_available"
    assert "walk" in config["choreography_cues"]
    assert config["interaction_defaults"]["hold_coffee"]["attach_to"] == "Hand_R"
    assert config["security_gating"] == "not_activated_by_motion_lab"
