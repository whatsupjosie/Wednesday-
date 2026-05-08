"""
modules/timeline_routes.py — Timeline Automation System Routes
Rear View Foresight LLC — Feic Mo Chroí — 2026-04-18
"""
from __future__ import annotations
import asyncio, logging
from pathlib import Path
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from .timeline import TimelinePlayer, TimelineDefinition, EventType, TimelineState
from .route_security import require_role

logger = logging.getLogger("pubcast.timeline_routes")

# ═══════════════════════════════════════════════════════════════════════════
# MODELS
# ═══════════════════════════════════════════════════════════════════════════

class TimelineLoadRequest(BaseModel):
    name: str

class TimelineStatus(BaseModel):
    state: str
    elapsed: float
    progress: float
    timeline_name: Optional[str] = None
    duration: Optional[float] = None

# ═══════════════════════════════════════════════════════════════════════════
# ROUTER & PLAYER SINGLETON
# ═══════════════════════════════════════════════════════════════════════════

router = APIRouter(prefix="/api/timeline", tags=["Timeline"])
player = TimelinePlayer()

# Data directory (set during init)
TIMELINES_DIR: Optional[Path] = None

def init_timeline_system(data_dir: Path):
    """Initialize timeline system with data directory."""
    global TIMELINES_DIR
    TIMELINES_DIR = data_dir / "timelines"
    TIMELINES_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"Timeline system initialized: {TIMELINES_DIR}")

# ═══════════════════════════════════════════════════════════════════════════
# EVENT HANDLER REGISTRY
# ═══════════════════════════════════════════════════════════════════════════

# External systems register handlers here
_event_handlers: Dict[EventType, list] = {}

def register_timeline_handler(event_type: EventType, handler):
    """
    Register a handler for timeline events.
    
    Example:
        async def handle_camera(params):
            await camera_manager.switch_to(params['to'])
        
        register_timeline_handler(EventType.CAMERA, handle_camera)
    """
    if event_type not in _event_handlers:
        _event_handlers[event_type] = []
    _event_handlers[event_type].append(handler)
    logger.info(f"Registered handler for {event_type.value}")

async def _dispatch_event(event_type: EventType, params: dict):
    """Internal: dispatch event to registered handlers."""
    handlers = _event_handlers.get(event_type, [])
    for handler in handlers:
        try:
            if asyncio.iscoroutinefunction(handler):
                await handler(params)
            else:
                handler(params)
        except Exception as e:
            logger.error(f"Handler error for {event_type.value}: {e}")

def _dispatching_handler(event_type: EventType):
    async def handler(event):
        await _dispatch_event(event_type, event.params)
    return handler

# Wire player to dispatcher.
player.register_handler(EventType.CAMERA, _dispatching_handler(EventType.CAMERA))
player.register_handler(EventType.LIGHTING, _dispatching_handler(EventType.LIGHTING))
player.register_handler(EventType.CHAT, _dispatching_handler(EventType.CHAT))
player.register_handler(EventType.RECORD, _dispatching_handler(EventType.RECORD))
player.register_handler(EventType.ENTRANCE, _dispatching_handler(EventType.ENTRANCE))
player.register_handler(EventType.ENVIRONMENT, _dispatching_handler(EventType.ENVIRONMENT))
player.register_handler(EventType.WALK, _dispatching_handler(EventType.WALK))
player.register_handler(EventType.AUDIO, _dispatching_handler(EventType.AUDIO))
player.register_handler(EventType.CUSTOM, _dispatching_handler(EventType.CUSTOM))

# ═══════════════════════════════════════════════════════════════════════════
# API ROUTES
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/status", response_model=TimelineStatus)
async def get_status():
    """Get current timeline playback status."""
    timeline_name = player._timeline.name if player._timeline else None
    duration = player._timeline.duration if player._timeline else None
    
    return TimelineStatus(
        state=player.state.value,
        elapsed=player.elapsed,
        progress=player.progress,
        timeline_name=timeline_name,
        duration=duration,
    )

@router.get("/list")
async def list_timelines():
    """List all available timelines."""
    if not TIMELINES_DIR:
        raise HTTPException(500, "Timeline system not initialized")
    
    timelines = []
    for path in TIMELINES_DIR.glob("*.json"):
        try:
            tl = TimelineDefinition.load(path)
            timelines.append({
                "name": tl.name,
                "filename": path.stem,
                "description": tl.description,
                "duration": tl.duration,
                "event_count": len(tl.events),
                "loop": tl.loop,
            })
        except Exception as e:
            logger.warning(f"Failed to load timeline {path.name}: {e}")
    
    return {"timelines": timelines}

@router.post("/load")
async def load_timeline(req: TimelineLoadRequest, identity: Dict[str, Any] = Depends(require_role("mod"))):
    """Load a timeline by name."""
    if not TIMELINES_DIR:
        raise HTTPException(500, "Timeline system not initialized")
    
    path = TIMELINES_DIR / f"{req.name}.json"
    if not path.exists():
        raise HTTPException(404, f"Timeline '{req.name}' not found")
    
    try:
        timeline = TimelineDefinition.load(path)
        issues = timeline.validate()
        if issues:
            raise HTTPException(400, f"Timeline validation failed: {issues}")
        
        player.load_timeline(timeline)
        logger.info(f"Loaded timeline: {timeline.name}")
        
        return {
            "loaded": timeline.name,
            "duration": timeline.duration,
            "events": len(timeline.events),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to load timeline {req.name}: {e}")
        raise HTTPException(500, f"Failed to load timeline: {str(e)}")

@router.post("/play")
async def play(identity: Dict[str, Any] = Depends(require_role("mod"))):
    """Start timeline playback."""
    if not player._timeline:
        raise HTTPException(400, "No timeline loaded")
    
    ok = await player.start()
    if not ok:
        raise HTTPException(400, "Timeline is already running or cannot start")
    logger.info("Timeline playback started")
    return {"action": "playing", "state": player.state.value}

@router.post("/pause")
async def pause(identity: Dict[str, Any] = Depends(require_role("mod"))):
    """Pause timeline playback."""
    if player.state != TimelineState.RUNNING:
        raise HTTPException(400, "Timeline not running")
    
    await player.pause()
    logger.info("Timeline playback paused")
    return {"action": "paused", "elapsed": player.elapsed}

@router.post("/resume")
async def resume(identity: Dict[str, Any] = Depends(require_role("mod"))):
    """Resume paused timeline."""
    if player.state != TimelineState.PAUSED:
        raise HTTPException(400, "Timeline not paused")
    
    await player.resume()
    logger.info("Timeline playback resumed")
    return {"action": "resumed", "state": player.state.value}

@router.post("/stop")
async def stop(identity: Dict[str, Any] = Depends(require_role("mod"))):
    """Stop timeline playback."""
    await player.stop()
    logger.info("Timeline playback stopped")
    return {"action": "stopped"}

@router.post("/seek")
async def seek(time: float, identity: Dict[str, Any] = Depends(require_role("mod"))):
    """Seek to specific time in timeline."""
    if not player._timeline:
        raise HTTPException(400, "No timeline loaded")
    
    if time < 0 or time > player._timeline.duration:
        raise HTTPException(400, f"Time must be 0-{player._timeline.duration}")
    
    if not player.seek(time):
        raise HTTPException(400, "Unable to seek timeline")
    logger.info(f"Seeked to {time}s")
    return {"seeked_to": time, "elapsed": player.elapsed}

# ═══════════════════════════════════════════════════════════════════════════
# WEBSOCKET REAL-TIME STATUS
# ═══════════════════════════════════════════════════════════════════════════

@router.websocket("/ws")
async def timeline_websocket(websocket: WebSocket):
    """Real-time timeline status updates."""
    await websocket.accept()
    logger.info("Timeline WebSocket client connected")
    
    try:
        while True:
            status = {
                "state": player.state.value,
                "elapsed": player.elapsed,
                "progress": player.progress,
            }
            
            if player._timeline:
                status["timeline"] = player._timeline.name
                status["duration"] = player._timeline.duration
            
            await websocket.send_json(status)
            await asyncio.sleep(0.1)  # 10Hz updates
    except WebSocketDisconnect:
        logger.info("Timeline WebSocket client disconnected")
