"""CastGesture — Main FastAPI server."""

import asyncio
import json
import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .config import get_config, update_config, save_config, ServerConfig
from .effects import build_effect_event, EFFECT_DEFAULTS
from .sounds import get_sound_for_effect, list_sounds, register_custom_sound
from .mappings import MappingEngine
from .obs_integration import OBSController
from .twitch_integration import TwitchBot

logger = logging.getLogger("castgesture")

# --- Globals ---
clients: set[WebSocket] = set()
mapping_engine: Optional[MappingEngine] = None
obs: Optional[OBSController] = None
twitch: Optional[TwitchBot] = None
gesture_pipeline = None  # GestureEngine pipeline (lazy init)
camera_task: Optional[asyncio.Task] = None


ROOT = Path(__file__).parent.parent
OVERLAY_DIR = ROOT / "overlay"
PANEL_DIR = ROOT / "panel"
LANDING_DIR = ROOT / "landing"


async def broadcast(event: dict):
    """Send event to all connected overlay clients."""
    data = json.dumps(event)
    dead = set()
    for ws in clients:
        try:
            await ws.send_text(data)
        except Exception:
            dead.add(ws)
    clients.difference_update(dead)


async def camera_loop():
    """Capture webcam frames and run gesture detection."""
    config = get_config()
    try:
        import cv2
        cap = cv2.VideoCapture(config.camera_index)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.camera_width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.camera_height)

        # Try to import GestureEngine
        try:
            from gesture_engine import GesturePipeline
            pipeline = GesturePipeline()
        except ImportError:
            logger.warning("GestureEngine not installed — using mock gesture detection")
            pipeline = None

        while True:
            ret, frame = cap.read()
            if not ret:
                await asyncio.sleep(0.1)
                continue

            gesture = None
            hand_x, hand_y = 0.5, 0.5
            landmarks = None

            if pipeline:
                result = pipeline.process(frame)
                if result and result.gesture:
                    gesture = result.gesture
                    hand_x = result.hand_center_x if hasattr(result, 'hand_center_x') else 0.5
                    hand_y = result.hand_center_y if hasattr(result, 'hand_center_y') else 0.5
                    landmarks = result.landmarks if hasattr(result, 'landmarks') else None

            if gesture and mapping_engine:
                events = mapping_engine.process_gesture(gesture, hand_x, hand_y)
                for event in events:
                    sound_url = get_sound_for_effect(event["effect"], config.sounds_dir)
                    if sound_url:
                        event["sound"] = sound_url
                    await broadcast(event)

                # Broadcast gesture detection event (for panel live preview)
                await broadcast({
                    "type": "gesture",
                    "gesture": gesture,
                    "x": hand_x,
                    "y": hand_y,
                    "landmarks": landmarks,
                })

            await asyncio.sleep(1.0 / config.fps)

    except ImportError:
        logger.warning("OpenCV not installed — camera loop disabled. Install with: pip install opencv-python")
    except Exception as e:
        logger.error(f"Camera loop error: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global mapping_engine, obs, twitch, camera_task
    config = get_config()

    # Load mappings
    mapping_engine = MappingEngine(config.mappings_file)
    logger.info(f"Loaded {len(mapping_engine.mappings)} gesture mappings")

    # Start camera loop or demo mode
    import os
    if os.environ.get("CASTGESTURE_DEMO") == "1" and os.environ.get("CASTGESTURE_DEMO_MODE") != "interactive":
        from .demo import run_demo_timeline, DEFAULT_TIMELINE
        import json
        timeline = DEFAULT_TIMELINE
        timeline_path = os.environ.get("CASTGESTURE_DEMO_TIMELINE")
        if timeline_path:
            timeline = json.loads(Path(timeline_path).read_text())
        loop = os.environ.get("CASTGESTURE_DEMO_NO_LOOP") != "1"
        camera_task = asyncio.create_task(
            run_demo_timeline(broadcast, mapping_engine, timeline, loop=loop,
                              get_sound_fn=get_sound_for_effect, sounds_dir=config.sounds_dir)
        )
        logger.info("Demo mode active — broadcasting scripted gestures")
    else:
        camera_task = asyncio.create_task(camera_loop())

    # Connect to OBS if configured
    if config.obs_ws_url:
        obs = OBSController(config.obs_ws_url, config.obs_ws_password)
        try:
            await obs.connect()
            logger.info("Connected to OBS")
        except Exception as e:
            logger.warning(f"OBS connection failed: {e}")

    # Start Twitch bot if configured
    if config.twitch_enabled and config.twitch_oauth_token:
        twitch = TwitchBot(config.twitch_channel, config.twitch_oauth_token, config.twitch_bot_name)

        async def on_twitch_command(user, cmd):
            if cmd in EFFECT_DEFAULTS:
                event = build_effect_event(cmd)
                event["triggered_by"] = f"twitch:{user}"
                await broadcast(event)

        twitch.on_command(on_twitch_command)
        asyncio.create_task(twitch.run())
        logger.info(f"Twitch bot joining #{config.twitch_channel}")

    yield

    # Cleanup
    if camera_task:
        camera_task.cancel()
    if obs and obs.connected:
        await obs.disconnect()
    if twitch:
        await twitch.disconnect()


app = FastAPI(title="CastGesture", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# --- Static files ---
app.mount("/overlay", StaticFiles(directory=str(OVERLAY_DIR), html=True), name="overlay")
app.mount("/panel", StaticFiles(directory=str(PANEL_DIR), html=True), name="panel")
app.mount("/landing", StaticFiles(directory=str(LANDING_DIR), html=True), name="landing")


# --- WebSocket ---
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    clients.add(ws)
    try:
        while True:
            data = await ws.receive_text()
            msg = json.loads(data)
            # Handle client messages (e.g., test effects from panel)
            if msg.get("type") == "test_effect":
                event = build_effect_event(msg["effect"], msg.get("params"))
                sound = get_sound_for_effect(msg["effect"], get_config().sounds_dir)
                if sound:
                    event["sound"] = sound
                await broadcast(event)
            elif msg.get("type") == "trigger_effect":
                await broadcast(msg)
    except WebSocketDisconnect:
        pass
    finally:
        clients.discard(ws)


# --- REST API ---
class MappingUpdate(BaseModel):
    gesture: str
    effect: str
    params: dict = {}
    sound: Optional[str] = None


class ConfigUpdate(BaseModel):
    class Config:
        extra = "allow"


@app.get("/")
async def root():
    return FileResponse(str(PANEL_DIR / "index.html"))


@app.get("/api/config")
async def get_api_config():
    config = get_config()
    return {
        "host": config.host, "port": config.port,
        "camera_index": config.camera_index,
        "obs_ws_url": config.obs_ws_url,
        "twitch_enabled": config.twitch_enabled,
        "twitch_channel": config.twitch_channel,
        "overlay_show_skeleton": config.overlay_show_skeleton,
        "debug": config.debug,
    }


@app.post("/api/config")
async def update_api_config(data: dict):
    config = update_config(**data)
    return {"status": "ok"}


@app.get("/api/mappings")
async def get_mappings():
    if mapping_engine:
        return mapping_engine.get_mappings_dict()
    return {"mappings": {}, "sequences": []}


@app.post("/api/mappings")
async def update_mapping(m: MappingUpdate):
    if mapping_engine:
        mapping_engine.update_mapping(m.gesture, m.effect, m.params, m.sound)
        return {"status": "ok"}
    return {"error": "no mapping engine"}


@app.delete("/api/mappings/{gesture}")
async def delete_mapping(gesture: str):
    if mapping_engine:
        mapping_engine.remove_mapping(gesture)
        return {"status": "ok"}
    return {"error": "not found"}


@app.post("/api/mappings/save")
async def save_mappings():
    if mapping_engine:
        mapping_engine.save(get_config().mappings_file)
        return {"status": "saved"}
    return {"error": "no engine"}


@app.get("/api/effects")
async def get_effects():
    return EFFECT_DEFAULTS


@app.get("/api/sounds")
async def get_sounds():
    return list_sounds(get_config().sounds_dir)


@app.post("/api/test/{effect_type}")
async def test_effect(effect_type: str, params: Optional[dict] = None):
    event = build_effect_event(effect_type, params)
    sound = get_sound_for_effect(effect_type, get_config().sounds_dir)
    if sound:
        event["sound"] = sound
    await broadcast(event)
    return {"status": "triggered", "effect": effect_type}


@app.get("/api/obs/scenes")
async def get_obs_scenes():
    if obs and obs.connected:
        scenes = await obs.get_scenes()
        return {"scenes": scenes}
    return {"error": "OBS not connected", "scenes": []}


@app.post("/api/obs/scene/{scene_name}")
async def switch_obs_scene(scene_name: str):
    if obs and obs.connected:
        await obs.switch_scene(scene_name)
        return {"status": "switched"}
    return {"error": "OBS not connected"}


@app.get("/api/status")
async def status():
    return {
        "server": "running",
        "clients": len(clients),
        "obs_connected": obs.connected if obs else False,
        "twitch_connected": twitch._running if twitch else False,
        "mappings_loaded": len(mapping_engine.mappings) if mapping_engine else 0,
    }


def main():
    import uvicorn
    config = get_config()
    uvicorn.run(app, host=config.host, port=config.port)


if __name__ == "__main__":
    main()
