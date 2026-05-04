"""
modules/runtime_control_routes.py — lightweight runtime control compatibility API.

This router is intentionally thin and non-owning. It exposes the already-existing
PerformanceManager and ChoreoController through stable endpoints expected by the
panoramic/control-room UI. When a subsystem is unavailable, routes return an
explicit unavailable payload rather than accidental 404s.

Mount from main.py only after the app has constructed the managers:
    app.include_router(create_runtime_control_router(
        performance_manager=performance_manager,
        choreo_controller=choreo_controller,
    ))
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request


async def _json_dict(request: Request) -> Dict[str, Any]:
    try:
        body = await request.json()
    except Exception:
        return {}
    return body if isinstance(body, dict) else {}


def _unavailable(name: str) -> Dict[str, Any]:
    return {"status": "unavailable", "available": False, "subsystem": name}


def create_runtime_control_router(
    *,
    performance_manager: Optional[Any] = None,
    choreo_controller: Optional[Any] = None,
) -> APIRouter:
    router = APIRouter(tags=["Runtime Control"])

    @router.get("/api/performance/status")
    async def performance_status():
        if performance_manager is None:
            return _unavailable("performance_manager")
        status = performance_manager.status() if hasattr(performance_manager, "status") else {}
        if isinstance(status, dict):
            return {"status": "ok", "available": True, **status}
        return {"status": "ok", "available": True, "value": status}

    @router.post("/api/performance/profile")
    async def set_performance_profile(request: Request):
        if performance_manager is None:
            return _unavailable("performance_manager")
        body = await _json_dict(request)
        profile = str(body.get("profile") or "").strip().lower()
        if not profile:
            raise HTTPException(status_code=400, detail="profile is required")
        try:
            snapshot = performance_manager.set_profile(profile)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"status": "ok", "available": True, **snapshot}

    @router.get("/api/choreo/status")
    async def choreo_status():
        if choreo_controller is None:
            return _unavailable("choreo_controller")
        status = choreo_controller.status() if hasattr(choreo_controller, "status") else {}
        if isinstance(status, dict):
            return {"status": "ok", "available": True, **status}
        return {"status": "ok", "available": True, "value": status}

    @router.get("/api/choreo/actions")
    async def choreo_actions():
        if choreo_controller is None:
            return _unavailable("choreo_controller")
        actions = choreo_controller.list_actions() if hasattr(choreo_controller, "list_actions") else {}
        return {"status": "ok", "available": True, "actions": actions}

    @router.get("/api/choreo/constraints")
    async def get_choreo_constraints():
        if choreo_controller is None:
            return _unavailable("choreo_controller")
        constraints = choreo_controller.get_constraints() if hasattr(choreo_controller, "get_constraints") else {}
        return {"status": "ok", "available": True, "constraints": constraints}

    @router.post("/api/choreo/constraints")
    async def set_choreo_constraints(request: Request):
        if choreo_controller is None:
            return _unavailable("choreo_controller")
        body = await _json_dict(request)
        patch = body.get("constraints", body)
        if not isinstance(patch, dict):
            raise HTTPException(status_code=400, detail="constraints must be an object")
        constraints = choreo_controller.set_constraints(patch)
        return {"status": "ok", "available": True, "constraints": constraints}

    @router.post("/api/choreo/cue")
    async def cue_choreo_action(request: Request):
        if choreo_controller is None:
            return _unavailable("choreo_controller")
        body = await _json_dict(request)
        try:
            payload = await choreo_controller.cue_action(
                room=str(body.get("room") or "default"),
                avatar_id=str(body.get("avatar_id") or body.get("avatar") or "").strip(),
                action=str(body.get("action") or "").strip(),
                intensity=float(body.get("intensity", 1.0)),
                duration=body.get("duration"),
                props=body.get("props") if isinstance(body.get("props"), dict) else {},
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"status": "ok", "available": True, "cue": payload}

    return router


__all__ = ["create_runtime_control_router"]
