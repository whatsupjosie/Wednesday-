"""
tests/test_pubcast.py — PubCast AI Full Test Suite
═══════════════════════════════════════════════════
Run: python -m pytest tests/test_pubcast.py -v

Rear View Foresight LLC — Feic Mo Chroí — 2026-03-24
"""
import asyncio
import json
import shutil
import tempfile
import time
import unittest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestHub(unittest.TestCase):
    def setUp(self):
        self.td = Path(tempfile.mkdtemp())
        from modules.hub import Hub
        self.hub = Hub(self.td)

    def tearDown(self):
        shutil.rmtree(self.td, ignore_errors=True)

    def test_initial_state(self):
        self.assertEqual(len(self.hub.rooms), 0)
        self.assertIsNone(self.hub.on_chat_callback)

    def test_post_and_get_history(self):
        async def run():
            await self.hub.post_chat_message("main", "user1", "Hello")
            history = await self.hub.get_recent_history("main", 10)
            self.assertEqual(len(history), 1)
            self.assertEqual(history[0]["text"], "Hello")
        asyncio.run(run())

    def test_production_state(self):
        state = self.hub.get_production_state()
        self.assertIn("mode", state)
        updated = self.hub.update_production_state({"on_air": True})
        self.assertTrue(updated["on_air"])

    def test_disconnect_removes_empty_room(self):
        from starlette.websockets import WebSocketState

        class FakeWebSocket:
            application_state = WebSocketState.DISCONNECTED

        ws = FakeWebSocket()
        self.hub.rooms["main"] = {ws}

        asyncio.run(self.hub.disconnect(ws, "main"))

        self.assertNotIn("main", self.hub.rooms)

    def test_broadcast_removes_empty_room_after_dead_socket_prune(self):
        from starlette.websockets import WebSocketState

        class FakeWebSocket:
            application_state = WebSocketState.DISCONNECTED

        ws = FakeWebSocket()
        self.hub.rooms["main"] = {ws}

        asyncio.run(self.hub._broadcast("main", {"type": "presence", "payload": {}}))

        self.assertNotIn("main", self.hub.rooms)

    def test_room_websocket_cannot_mutate_production_state(self):
        class FakeWebSocket:
            def __init__(self):
                self.sent = []

            async def send_text(self, text):
                self.sent.append(json.loads(text))

        ws = FakeWebSocket()

        asyncio.run(self.hub.handle_message(ws, "main", json.dumps({
            "type": "production_state",
            "payload": {"on_air": True},
        })))

        self.assertFalse(self.hub.get_production_state().get("on_air", False))
        self.assertEqual(ws.sent[0]["type"], "error")


class TestBotManager(unittest.TestCase):
    def setUp(self):
        self.td = Path(tempfile.mkdtemp())
        from modules.hub import Hub
        from modules.bots import BotManager
        self.hub = Hub(self.td)
        self.bm = BotManager(data_dir=self.td, hub=self.hub)

    def tearDown(self):
        shutil.rmtree(self.td, ignore_errors=True)

    def test_has_ollama(self):
        self.assertTrue(hasattr(self.bm, '_call_ollama'))

    def test_callback_wiring(self):
        self.hub.on_chat_callback = self.bm.on_chat_message
        self.assertTrue(callable(self.hub.on_chat_callback))

    def test_nudge_empty(self):
        async def run():
            result = await self.bm.nudge("main", "test hint")
            self.assertFalse(result)  # No bots loaded
        asyncio.run(run())


class TestCameras(unittest.TestCase):
    def test_default_cameras(self):
        from modules.cameras import create_default_cameras
        cm = create_default_cameras()
        self.assertEqual(len(cm.list_sources()), 6)
        self.assertEqual(cm.get_program_source().source_id, "wide_shot")

    def test_switch(self):
        from modules.cameras import create_default_cameras
        cm = create_default_cameras()
        cm.set_program_source("close_up")
        self.assertEqual(cm.get_program_source().source_id, "close_up")

    def test_reject_unknown(self):
        from modules.cameras import create_default_cameras
        cm = create_default_cameras()
        self.assertFalse(cm.set_program_source("nonexistent"))


class TestStudioControl(unittest.TestCase):
    def setUp(self):
        self.td = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.td, ignore_errors=True)

    def test_studio_control_broadcast_sends_json_and_prunes_dead_clients(self):
        from modules.studio_control import StudioControl

        class JsonClient:
            def __init__(self):
                self.messages = []

            async def send_json(self, message):
                self.messages.append(message)

        class DeadClient:
            async def send_json(self, message):
                raise RuntimeError("gone")

        async def run():
            control = StudioControl(hub=None, pete=None, data_dir=self.td)
            live = JsonClient()
            dead = DeadClient()
            control.register_ws_client(live)
            control.register_ws_client(live)
            control.register_ws_client(dead)

            await control._broadcast({"type": "state_update", "state": "IDLE"})

            self.assertEqual(live.messages, [{"type": "state_update", "state": "IDLE"}])
            self.assertEqual(control._ws_clients, [live])

        asyncio.run(run())


class TestRecording(unittest.TestCase):
    def setUp(self):
        self.td = Path(tempfile.mkdtemp())
        from modules.cameras import create_default_cameras
        from modules.recording import create_recording_service
        self.cm = create_default_cameras()
        self.rs = create_recording_service(self.td, self.cm)

    def tearDown(self):
        shutil.rmtree(self.td, ignore_errors=True)

    def test_profiles(self):
        self.assertEqual(len(self.rs.list_profiles()), 4)

    def test_lifecycle(self):
        from modules.recording import RecordingState
        s = self.rs.start_session("t1", ["wide_shot"], profile_id="broadcast_mp4",
                                   operator="test", countdown_seconds=0)
        self.assertEqual(s.state, RecordingState.ACTIVE)
        self.rs.mark_moment("t1", "test marker")
        self.rs.stop_session("t1")
        s = self.rs.get_session("t1")
        self.assertEqual(s.state, RecordingState.STOPPED)
        self.assertEqual(len(s.markers), 1)

    def test_privacy(self):
        self.assertEqual(self.rs.room_policy("dressing")["recording"], "never")


class TestGovernance(unittest.TestCase):
    def setUp(self):
        self.td = Path(tempfile.mkdtemp())
        from modules.governance import GovernanceEngine
        self.gov = GovernanceEngine(self.td)

    def tearDown(self):
        shutil.rmtree(self.td, ignore_errors=True)

    def test_ban_unban(self):
        self.gov.ban_user("u1", "test", "host")
        self.assertTrue(self.gov.is_banned("u1")[0])
        self.gov.unban_user("u1", "host")
        self.assertFalse(self.gov.is_banned("u1")[0])

    def test_freeze(self):
        self.gov.freeze_avatar("u1", "host", "disruptive")
        frozen, state = self.gov.is_frozen("u1")
        self.assertTrue(frozen)
        self.gov.unfreeze_avatar("u1", "host")
        self.assertFalse(self.gov.is_frozen("u1")[0])

    def test_consent_flow(self):
        from modules.governance import ConsentType
        missing = self.gov.get_missing_consents("u1")
        self.assertIn(ConsentType.TERMS_OF_SERVICE, missing)
        self.gov.record_consent("u1", ConsentType.TERMS_OF_SERVICE, True)
        self.gov.record_consent("u1", ConsentType.AI_DISCLOSURE, True)
        self.assertEqual(len(self.gov.get_missing_consents("u1")), 0)

    def test_waiting_room(self):
        from modules.governance import EntryStatus
        entry = self.gov.request_entry("u1", "Alice", "studio")
        self.assertEqual(entry.status, EntryStatus.WAITING)
        self.gov.approve_entry(entry.entry_id, "host")
        self.assertEqual(len(self.gov.list_waiting()), 0)

    def test_audit_hash_chain(self):
        import hashlib
        self.gov.ban_user("u1", "r1", "host")
        self.gov.unban_user("u1", "host")
        log = self.gov.get_audit_log(10)
        if len(log) >= 2:
            e1, e2 = log[-1], log[-2]
            chain = f"{e1['log_id']}:{e1['timestamp']}:{e1['details']}"
            expected = hashlib.sha256(chain.encode()).hexdigest()[:16]
            self.assertEqual(e2["prev_hash"], expected)


class TestVault(unittest.TestCase):
    def setUp(self):
        self.td = Path(tempfile.mkdtemp())
        self.vdir = self.td / "vault"
        from modules.vault_engine_hardened import VaultEngine
        self.vault = VaultEngine(str(self.vdir))
        self.test_file = self.td / "test.txt"
        self.test_file.write_text("protected content")

    def tearDown(self):
        self.vault.stop_watcher()
        shutil.rmtree(self.td, ignore_errors=True)

    def test_add_and_integrity(self):
        self.vault.create_cradle("P1", str(self.td))
        ok, _ = self.vault.add_file_to_vault(str(self.test_file), "P1")
        self.assertTrue(ok)
        r = self.vault.get_integrity_report()
        self.assertTrue(r["healthy"])
        self.assertEqual(r["shadow_intact"], 1)

    def test_open_requires_command(self):
        ok, _ = self.vault.open_vault("no-session")
        self.assertFalse(ok)

    def test_full_sequence(self):
        self.vault.create_cradle("P1", str(self.td))
        self.vault.add_file_to_vault(str(self.test_file), "P1")
        files = self.vault.list_vault_files("P1")
        fid = files[0]["file_id"]
        # OPEN
        sid = "s1"
        self.vault.enforcer.start_session(sid)
        for c in "OPEN":
            time.sleep(0.06)
            self.vault.enforcer.record_keystroke(sid, c)
        self.vault.open_vault(sid)
        # REMOVE
        sid = "s2"
        self.vault.enforcer.start_session(sid)
        for c in "REMOVE":
            time.sleep(0.06)
            self.vault.enforcer.record_keystroke(sid, c)
        ok, _ = self.vault.remove_file_from_vault(fid, sid)
        self.assertTrue(ok)
        # DELETE
        sid = "s3"
        self.vault.enforcer.start_session(sid)
        for c in "DELETE":
            time.sleep(0.06)
            self.vault.enforcer.record_keystroke(sid, c)
        ok, _ = self.vault.delete_file(fid, sid)
        self.assertTrue(ok)
        self.assertEqual(len(self.vault.list_vault_files("P1")), 0)


class TestModeResolver(unittest.TestCase):
    def test_modes(self):
        from modules.mode_resolver import ModeResolver, ShowMode
        mr = ModeResolver()
        p = mr.resolve({"on_air": True})
        self.assertEqual(p.mode, ShowMode.LIVE)
        p = mr.resolve({"on_air": False, "mode": "REPLAY"})
        self.assertEqual(p.mode, ShowMode.POST_SHOW)

    def test_override(self):
        from modules.mode_resolver import ModeResolver, ShowMode
        mr = ModeResolver()
        mr.set_override(ShowMode.REHEARSAL)
        self.assertEqual(mr.current_mode, ShowMode.REHEARSAL)
        mr.clear_override()


class TestVoxelBridgePolicy(unittest.TestCase):
    def setUp(self):
        self.td = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.td, ignore_errors=True)

    def test_holding_bridge_refuses_commands_without_background_queue(self):
        from modules.bridge_bulletproof import VoxelBridge

        bridge = VoxelBridge(self.td)
        try:
            self.assertFalse(bridge.send_command("LOAD_SCENE", {"scene": "unit"}))
            self.assertEqual(bridge.get_metrics()["queue_depth"], 0)
        finally:
            bridge.close()

    def test_low_profile_keeps_voxel_bridge_cold(self):
        from modules.performance_manager import DEFAULT_POLICY

        low = DEFAULT_POLICY["profiles"]["low"]
        high = DEFAULT_POLICY["profiles"]["high"]
        self.assertFalse(low["voxel_bridge_autoconnect"])
        self.assertFalse(low["voxel_bridge_allow_emergency_fallback"])
        self.assertTrue(high["voxel_bridge_autoconnect"])


class TestAIResourcePolicy(unittest.TestCase):
    def setUp(self):
        self.td = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.td, ignore_errors=True)

    def test_low_profile_keeps_architect_cold_at_startup(self):
        from modules.performance_manager import init_performance_manager
        import modules.llm_orchestrator as orchestrator_module

        mgr = init_performance_manager(data_dir=self.td, policy_path=Path("missing-policy.json"))
        mgr.active_profile = "low"

        class MockResponse:
            status_code = 503

        class MockClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return None

            async def get(self, *args, **kwargs):
                return MockResponse()

        old_loader = orchestrator_module._load_architect
        old_client = orchestrator_module.httpx.AsyncClient
        orchestrator_module._load_architect = lambda: (_ for _ in ()).throw(AssertionError("architect should stay cold"))
        orchestrator_module.httpx.AsyncClient = lambda **kwargs: MockClient()
        try:
            orchestrator = orchestrator_module.LLMOrchestrator()
            asyncio.run(orchestrator.startup())
            self.assertFalse(orchestrator._architect_enabled)
            self.assertFalse(orchestrator._arch_ok)
        finally:
            orchestrator_module._load_architect = old_loader
            orchestrator_module.httpx.AsyncClient = old_client


class TestTimelineRoutes(unittest.TestCase):
    def setUp(self):
        self.td = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.td, ignore_errors=True)

    def test_routes_use_timeline_player_contract(self):
        from modules import timeline_routes
        from modules.timeline import EventType, TimelineDefinition, TimelineEvent

        timeline_routes.init_timeline_system(self.td)
        timeline = TimelineDefinition(
            name="unit_timeline",
            duration=1.0,
            events=[TimelineEvent(t=0.1, event_type=EventType.CUSTOM, params={"ok": True})],
        )
        timeline.save(self.td / "timelines" / "unit_timeline.json")

        async def run():
            loaded = await timeline_routes.load_timeline(
                timeline_routes.TimelineLoadRequest(name="unit_timeline"),
                identity={},
            )
            self.assertEqual(loaded["loaded"], "unit_timeline")

            playing = await timeline_routes.play(identity={})
            self.assertEqual(playing["state"], "running")

            seeked = await timeline_routes.seek(0.2, identity={})
            self.assertEqual(seeked["seeked_to"], 0.2)

            paused = await timeline_routes.pause(identity={})
            self.assertGreaterEqual(paused["elapsed"], 0.0)

            resumed = await timeline_routes.resume(identity={})
            self.assertEqual(resumed["state"], "running")

            stopped = await timeline_routes.stop(identity={})
            self.assertEqual(stopped["action"], "stopped")

        asyncio.run(run())


class TestCharacterEngine(unittest.TestCase):
    def test_speaking_slot(self):
        from modules.character_engine import SpeakingSlotEnforcer
        enforcer = SpeakingSlotEnforcer(min_gap=0.1)
        async def run():
            got = await enforcer.acquire_slot("bot-pete", timeout=2)
            self.assertTrue(got)
            await enforcer.record_spoke("bot-pete")
            enforcer.release_slot("bot-pete")
        asyncio.run(run())

    def test_thought_logger(self):
        from modules.character_engine import ThoughtLogger
        td = Path(tempfile.mkdtemp())
        tl = ThoughtLogger(td)
        tid = tl.log_thought("pete", "ollama", "mistral", "prompt", "response", 150.0)
        self.assertGreater(tid, 0)
        stats = tl.stats()
        self.assertEqual(stats["total_thoughts"], 1)
        shutil.rmtree(td, ignore_errors=True)

    def test_nudge_calibration(self):
        from modules.character_engine import NudgeCalibration
        nc = NudgeCalibration()
        should, score = nc.should_nudge(60.0, 0.0, 5)
        self.assertTrue(should)
        should, score = nc.should_nudge(10.0, 0.0, 5)
        self.assertFalse(should)

    def test_prompt_templates(self):
        from modules.character_engine import get_prompt_template
        for bot in ["pete", "purfluous", "jeremy"]:
            t = get_prompt_template(bot)
            self.assertIn("system", t)
            self.assertIn("voice_markers", t)
            self.assertGreater(len(t["system"]), 100)


class TestEtherealAvatars(unittest.TestCase):
    def setUp(self):
        self.td = Path(tempfile.mkdtemp())
        from modules.ethereal_avatars import EtherealAvatarManager
        self.mgr = EtherealAvatarManager(self.td)

    def tearDown(self):
        shutil.rmtree(self.td, ignore_errors=True)

    def test_create_and_persist(self):
        skin = self.mgr.create_skin("u1", neon_color="pink")
        self.assertEqual(skin.hex_color, "#FF4DC8")
        self.mgr.remove_skin("u1")
        loaded = self.mgr.get_skin("u1")
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.neon_color, "pink")

    def test_color_change(self):
        self.mgr.create_skin("u1")
        self.assertTrue(self.mgr.set_neon_color("u1", "purple"))
        self.assertEqual(self.mgr.get_skin("u1").hex_color, "#C84DFF")


if __name__ == "__main__":
    unittest.main(verbosity=2)
