from fastapi.testclient import TestClient
import logging
import main


def test_startup_boots_surface_voxel_and_studio_without_constructor_failures(caplog):
    caplog.set_level(logging.INFO)
    with TestClient(main.app):
        pass
    text = caplog.text
    assert "[14] Surface manager failed" not in text
    assert "[16] Voxel stack failed" not in text
    assert "[17] Voxel bridge not connected" not in text
    assert "[18] Studio Control failed" not in text
    assert "[14] Surface manager ready" in text
    assert "[16] Voxel asset manager ready" in text
    assert "[18] Studio Control ready" in text


def test_studio_and_voxel_endpoints_are_live_after_startup():
    with TestClient(main.app) as client:
        studio = client.get('/api/studio/status')
        assert studio.status_code == 200
        studio_body = studio.json()
        assert studio_body['available'] is True

        voxel = client.get('/api/voxel/status')
        assert voxel.status_code == 200
        voxel_body = voxel.json()
        assert voxel_body['asset_manager'] is True
        assert voxel_body['studio_integration'] is True
        assert voxel_body['bridge'] is True
        assert voxel_body['bridge_status'] is not None


def test_studio_preflight_and_emergency_save_routes_work():
    with TestClient(main.app) as client:
        preflight = client.post('/api/studio/preflight', json={})
        assert preflight.status_code == 200
        preflight_body = preflight.json()
        assert preflight_body['ok'] is True
        assert 'result' in preflight_body
        assert 'checks' in preflight_body['result']

        emergency = client.post('/api/studio/emergency-save', json={})
        assert emergency.status_code == 200
        emergency_body = emergency.json()
        assert emergency_body['ok'] is True
        assert emergency_body['result']['ok'] is True
