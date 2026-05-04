"""
modules/production_routes.py — Camera + Recording REST API
═══════════════════════════════════════════════════════════
Wires CameraManager and RecordingService into FastAPI.
Also provides WebSocket broadcast helpers so the control room
console receives live updates on camera switches and recording state.

Usage in main.py:
    from modules.cameras import create_default_cameras
    from modules.recording import create_recording_service
    from modules.production_routes import create_production_router

    cameras = create_default_cameras()
    recording = create_recording_service(DATA_DIR, cameras)
    app.include_router(create_production_router(cameras, recording, hub))

Rear View Foresight LLC — Feic Mo Chroí — 2026-03-24T08:00Z
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Query
from fastapi.responses import FileResponse, JSONResponse

from modules.cameras import CameraManager, CameraSource, CameraTransport, create_default_cameras
from modules.recording import (
    RecordingService,
    RecordingSession,
    RecordingState,
    ContainerFormat,
    EncodingProfile,
    create_recording_service,
)

from modules.route_security import bound_actor, require_role
from modules.persistence import sanitize_filename, unique_child_path

logger = logging.getLogger("pubcast.production")


async def _json_dict(request: Request) -> Dict[str, Any]:
    """Parse a request body as a JSON object with clean 400s."""
    try:
        body = await request.json()
    except json.JSONDecodeError as exc:
        raise HTTPException(400, f"Malformed JSON body: {exc.msg}")
    except Exception as exc:
        raise HTTPException(400, f"Invalid JSON body: {exc}")
    if not isinstance(body, dict):
        raise HTTPException(400, "JSON body must be an object")
    return body


def _string_field(body: Dict[str, Any], key: str, *, default: str = "", required: bool = False,
                  max_length: int = 256) -> str:
    value = body.get(key, default)
    if value is None:
        value = default
    if not isinstance(value, str):
        raise HTTPException(400, f"{key} must be a string")
    value = value.strip()
    if required and not value:
        raise HTTPException(400, f"{key} required")
    if len(value) > max_length:
        raise HTTPException(400, f"{key} must be <= {max_length} characters")
    return value


def _bool_field(body: Dict[str, Any], key: str, *, default: bool = False) -> bool:
    value = body.get(key, default)
    if not isinstance(value, bool):
        raise HTTPException(400, f"{key} must be a boolean")
    return value


def _numeric_field(body: Dict[str, Any], key: str, *, default: float | int, minimum: float | None = None) -> float:
    value = body.get(key, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise HTTPException(400, f"{key} must be numeric")
    value = float(value)
    if minimum is not None and value < minimum:
        raise HTTPException(400, f"{key} must be >= {minimum}")
    return value


def _vector3(body: Dict[str, Any], key: str) -> List[float]:
    value = body.get(key, [0.0, 0.0, 0.0])
    if not isinstance(value, list) or len(value) != 3:
        raise HTTPException(400, f"{key} must be a 3-item array")
    try:
        vector = [float(v) for v in value]
    except (TypeError, ValueError):
        raise HTTPException(400, f"{key} must contain only numeric values")
    return vector


def _string_list(body: Dict[str, Any], key: str, *, required: bool = False) -> List[str]:
    value = body.get(key, [])
    if value in (None, ""):
        value = []
    if not isinstance(value, list):
        raise HTTPException(400, f"{key} must be an array")
    cleaned: List[str] = []
    for item in value:
        if not isinstance(item, str):
            raise HTTPException(400, f"{key} items must be strings")
        item = item.strip()
        if not item:
            raise HTTPException(400, f"{key} items must not be blank")
        cleaned.append(item)
    if required and not cleaned:
        raise HTTPException(400, f"{key} must contain at least one value")
    return cleaned


def create_production_router(
    cameras: CameraManager,
    recording: RecordingService,
    hub: Any,
) -> APIRouter:
    """Create the production API router."""
    router = APIRouter(tags=["Production"])

    # ═══════════════════════════════════════════════════════════════════
    # CAMERAS
    # ═══════════════════════════════════════════════════════════════════

    @router.get("/api/cameras")
    async def list_cameras():
        """List all registered camera sources with status."""
        sources = cameras.list_sources()
        statuses = {s.source_id: s for s in cameras.list_status()}
        pgm = cameras.get_program_source()
        pvw = cameras.get_preview_source()

        return {
            "cameras": [
                {
                    "source_id": cam.source_id,
                    "name": cam.name,
                    "location": cam.location,
                    "transport": cam.transport.value,
                    "endpoint": cam.endpoint,
                    "position": cam.position,
                    "rotation": cam.rotation,
                    "fov": cam.fov,
                    "tags": cam.tags,
                    "status": {
                        "online": statuses.get(cam.source_id, None)
                                  and statuses[cam.source_id].online,
                        "latency_ms": getattr(statuses.get(cam.source_id), "latency_ms", None),
                        "frame_rate": getattr(statuses.get(cam.source_id), "frame_rate", None),
                    },
                }
                for cam in sources
            ],
            "program": pgm.source_id if pgm else None,
            "preview": pvw.source_id if pvw else None,
        }

    @router.post("/api/cameras/switch")
    async def switch_camera(request: Request, identity: Dict[str, Any] = Depends(require_role("mod"))):
        """Switch program or preview camera. Broadcasts to all control rooms."""
        body = await _json_dict(request)
        target = _string_field(body, "target", default="program", max_length=32) or "program"
        source_id = _string_field(body, "source_id", required=True, max_length=128)

        if target == "program":
            ok = cameras.set_program_source(source_id)
        elif target == "preview":
            ok = cameras.set_preview_source(source_id)
        else:
            raise HTTPException(400, f"Invalid target '{target}'. Use 'program' or 'preview'.")

        if not ok:
            raise HTTPException(404, f"Camera source '{source_id}' not found.")

        # Broadcast switch to all connected clients
        if hub:
            pgm = cameras.get_program_source()
            pvw = cameras.get_preview_source()
            await hub.broadcast_system_event({
                "type": "camera_switch",
                "payload": {
                    "target": target,
                    "source_id": source_id,
                    "program": pgm.source_id if pgm else None,
                    "preview": pvw.source_id if pvw else None,
                    "timestamp": time.time(),
                },
            })

        return {"ok": True, "target": target, "source_id": source_id}

    @router.post("/api/cameras/cut")
    async def cut_cameras(identity: Dict[str, Any] = Depends(require_role("mod"))):
        """Swap program and preview (standard broadcast CUT transition)."""
        pgm = cameras.get_program_source()
        pvw = cameras.get_preview_source()

        if not pgm or not pvw:
            raise HTTPException(400, "Both program and preview must be set to cut.")

        cameras.set_program_source(pvw.source_id)
        cameras.set_preview_source(pgm.source_id)

        if hub:
            await hub.broadcast_system_event({
                "type": "camera_cut",
                "payload": {
                    "new_program": pvw.source_id,
                    "new_preview": pgm.source_id,
                    "timestamp": time.time(),
                },
            })

        return {"ok": True, "program": pvw.source_id, "preview": pgm.source_id}

    @router.post("/api/cameras/register")
    async def register_camera(request: Request, identity: Dict[str, Any] = Depends(require_role("mod"))):
        """Register a new camera source."""
        body = await _json_dict(request)
        try:
            source = CameraSource(
                source_id=_string_field(body, "source_id", required=True, max_length=128),
                name=_string_field(body, "name", default=_string_field(body, "source_id", required=True, max_length=128), max_length=128),
                location=_string_field(body, "location", default="virtual", max_length=128) or "virtual",
                description=_string_field(body, "description", default="", max_length=512),
                transport=CameraTransport(_string_field(body, "transport", default="virtual", max_length=64) or "virtual"),
                endpoint=_string_field(body, "endpoint", default=f"virtual://{_string_field(body, 'source_id', required=True, max_length=128)}", max_length=512),
                position=_vector3(body, "position"),
                rotation=_vector3(body, "rotation"),
                fov=_numeric_field(body, "fov", default=60.0, minimum=1.0),
                tags=_string_list(body, "tags"),
            )
        except (KeyError, ValueError) as exc:
            raise HTTPException(400, str(exc))

        cameras.register(source)
        return {"ok": True, "source_id": source.source_id}

    # ═══════════════════════════════════════════════════════════════════
    # RECORDING
    # ═══════════════════════════════════════════════════════════════════

    @router.get("/api/recording/profiles")
    async def list_profiles():
        """List available encoding profiles."""
        return [
            {
                "profile_id": p.profile_id,
                "name": p.name,
                "container": p.container.value,
                "video_codec": p.video_codec,
                "audio_codec": p.audio_codec,
                "resolution": p.resolution,
                "description": p.description,
            }
            for p in recording.list_profiles()
        ]

    @router.get("/api/recording/sessions")
    async def list_sessions():
        """List all recording sessions."""
        return [s.to_dict() for s in recording.list_sessions()]

    @router.post("/api/recording/start")
    async def start_recording(request: Request, identity: Dict[str, Any] = Depends(require_role("mod"))):
        """Start a new recording session."""
        body = await _json_dict(request)
        sources = _string_list(body, "sources")
        if not sources:
            # Default: record the current program source
            pgm = cameras.get_program_source()
            if pgm:
                sources = [pgm.source_id]
            else:
                raise HTTPException(400, "No sources specified and no program source set.")

        profile_id = _string_field(body, "profile_id", default="broadcast_mp4", max_length=128) or "broadcast_mp4"
        operator = bound_actor(request=request, identity=identity, explicit_value=body.get("operator"), field_name="operator") or "director"
        session_id = _string_field(body, "session_id", default="", max_length=128) or None
        countdown = int(_numeric_field(body, "countdown_seconds", default=5, minimum=0))
        host_override = _bool_field(body, "host_override", default=False)

        try:
            session = recording.start_session(
                session_id=session_id,
                sources=sources,
                profile_id=profile_id,
                operator=operator,
                countdown_seconds=countdown,
                host_override=host_override,
            )
        except (ValueError, PermissionError, KeyError) as exc:
            raise HTTPException(400, str(exc))

        # Broadcast recording start
        if hub:
            await hub.broadcast_system_event({
                "type": "recording_started",
                "payload": {
                    "session_id": session.session_id,
                    "sources": session.sources,
                    "profile_id": session.profile_id,
                    "state": session.state.value,
                    "countdown": countdown,
                },
            })

        return session.to_dict()

    @router.post("/api/recording/{session_id}/activate")
    async def activate_recording(session_id: str, identity: Dict[str, Any] = Depends(require_role("mod"))):
        """Activate a recording session (transition from countdown to active)."""
        try:
            session = recording.activate_session(session_id)
        except (KeyError, ValueError) as exc:
            raise HTTPException(400, str(exc))

        if hub:
            await hub.broadcast_system_event({
                "type": "recording_active",
                "payload": {"session_id": session_id},
            })

        return session.to_dict()

    @router.post("/api/recording/{session_id}/stop")
    async def stop_recording(session_id: str, identity: Dict[str, Any] = Depends(require_role("mod"))):
        """Stop a recording session."""
        try:
            session = recording.stop_session(session_id)
        except KeyError as exc:
            raise HTTPException(404, str(exc))

        if hub:
            await hub.broadcast_system_event({
                "type": "recording_stopped",
                "payload": {
                    "session_id": session_id,
                    "duration": (session.ended_at or time.time()) - session.started_at,
                },
            })

        return session.to_dict()

    @router.post("/api/recording/{session_id}/pause")
    async def pause_recording(session_id: str, request: Request, identity: Dict[str, Any] = Depends(require_role("mod"))):
        """Pause or resume a recording session."""
        body = await _json_dict(request)
        paused = _bool_field(body, "paused", default=True)
        try:
            session = recording.pause_session(session_id, paused)
        except (KeyError, ValueError) as exc:
            raise HTTPException(400, str(exc))
        return session.to_dict()

    @router.post("/api/recording/{session_id}/marker")
    async def add_marker(session_id: str, request: Request, identity: Dict[str, Any] = Depends(require_role("mod"))):
        """Add a timestamp marker to a recording session."""
        body = await _json_dict(request)
        label = _string_field(body, "label", required=True, max_length=256)
        operator = bound_actor(request=request, identity=identity, explicit_value=body.get("operator"), field_name="operator") if body.get("operator") else identity.get("user_id")
        try:
            marker = recording.mark_moment(session_id, label, operator)
        except KeyError as exc:
            raise HTTPException(404, str(exc))
        return {"ok": True, "timestamp": marker.timestamp, "label": marker.label}

    @router.post("/api/recording/{session_id}/export")
    async def export_recording(session_id: str, request: Request, identity: Dict[str, Any] = Depends(require_role("mod"))):
        """Export a recording session as a zip bundle."""
        body = await _json_dict(request)
        container = _string_field(body, "format", default="mp4", max_length=16) or "mp4"
        try:
            fmt = ContainerFormat(container)
        except ValueError:
            raise HTTPException(400, f"Invalid format '{container}'. Use: mp4, webm, wav, mov")

        try:
            export_path = await asyncio.to_thread(
                recording.export_session, session_id, container=fmt
            )
        except (KeyError, ValueError) as exc:
            raise HTTPException(400, str(exc))

        return FileResponse(
            export_path,
            media_type="application/zip",
            filename=export_path.name,
        )

    @router.post("/api/recording/import")
    async def import_recording(file: UploadFile = File(...), identity: Dict[str, Any] = Depends(require_role("mod"))):
        """Import a recording session from a zip bundle."""
        import_dir = recording.imports_dir
        filename = sanitize_filename(file.filename or "")
        if not filename:
            raise HTTPException(400, "Uploaded file must have a filename")
        if not filename.lower().endswith(".zip"):
            raise HTTPException(400, "Recording import requires a .zip bundle")
        import_path = unique_child_path(import_dir, filename)
        with open(import_path, "wb") as f:
            content = await file.read()
            f.write(content)
        try:
            session = recording.import_session(import_path)
        except (ValueError, FileNotFoundError) as exc:
            raise HTTPException(400, str(exc))
        return session.to_dict()

    @router.get("/api/recording/storage")
    async def storage_status():
        """Get recording storage usage."""
        return recording.storage_status()

    @router.get("/api/recording/privacy")
    async def privacy_matrix():
        """Get recording privacy rules per room."""
        return recording.privacy_matrix()

    # ═══════════════════════════════════════════════════════════════════
    # PANIC / Emergency
    # ═══════════════════════════════════════════════════════════════════

    @router.post("/api/production/panic")
    async def production_panic(identity: Dict[str, Any] = Depends(require_role("mod"))):
        """Emergency: stop all recordings, mute, fade to black."""
        # Stop all active recordings
        stopped = []
        for session in recording.list_sessions():
            if session.state in (RecordingState.ACTIVE, RecordingState.COUNTDOWN):
                recording.stop_session(session.session_id)
                stopped.append(session.session_id)

        # Broadcast panic to all clients
        if hub:
            await hub.broadcast_system_event({
                "type": "production_panic",
                "payload": {
                    "timestamp": time.time(),
                    "sessions_stopped": stopped,
                    "message": "PANIC — all recordings stopped, fade to black",
                },
            })
            # Also update production state
            hub.update_production_state({
                "on_air": False,
                "camera": "black",
                "lower_third": "",
            })

        return {"ok": True, "sessions_stopped": stopped}

    return router
