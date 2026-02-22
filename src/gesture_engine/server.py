"""WebSocket streaming server for real-time gesture events.

Captures from the server's webcam and pushes gesture events
to all connected WebSocket clients as JSON messages.

Features:
- Real-time gesture detection and streaming
- Spatial trajectory tracking
- Two-hand gesture detection
- Finger painting / air drawing canvas
- Plugin system for extensibility
- Prometheus metrics endpoint
- REST API for status and gesture info

Usage:
    python -m gesture_engine.server
    # or
    uvicorn gesture_engine.server:app --host 0.0.0.0 --port 8765
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Optional

import numpy as np

try:
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect
    from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse
    _HAS_FASTAPI = True
except ImportError:
    _HAS_FASTAPI = False

if not _HAS_FASTAPI:
    raise ImportError("FastAPI required. Install with: pip install fastapi uvicorn")

try:
    import cv2
except ImportError:
    cv2 = None

from gesture_engine.classifier import GestureClassifier
from gesture_engine.detector import HandDetector
from gesture_engine.gestures import GestureRegistry
from gesture_engine.sequences import SequenceDetector
from gesture_engine.trajectory import TrajectoryTracker
from gesture_engine.bimanual import BimanualDetector
from gesture_engine.canvas import DrawingCanvas
from gesture_engine.plugins import PluginManager, PluginEvent
from gesture_engine.metrics import MetricsCollector

logger = logging.getLogger("gesture_engine.server")

app = FastAPI(title="GestureEngine", version="0.4.0")

# --- State ---

class ServerState:
    def __init__(self):
        self.clients: set[WebSocket] = set()
        self.canvas_clients: set[WebSocket] = set()
        self.detector: Optional[HandDetector] = None
        self.classifier: Optional[GestureClassifier] = None
        self.sequence_detector: Optional[SequenceDetector] = None
        self.trajectory_tracker: Optional[TrajectoryTracker] = None
        self.bimanual_detector: Optional[BimanualDetector] = None
        self.drawing_canvas: Optional[DrawingCanvas] = None
        self.plugin_manager: Optional[PluginManager] = None
        self.metrics: MetricsCollector = MetricsCollector()
        self.capture: Optional[object] = None
        self.running = False
        self.fps = 0.0
        self.latency_ms = 0.0
        self.total_gestures = 0
        self.last_gesture: Optional[dict] = None
        self.gesture_heatmap: dict[str, int] = {}

state = ServerState()


# --- Web demo serving ---

WEB_DEMO_DIR = Path(__file__).parent.parent.parent / "examples" / "web_demo"


@app.get("/")
async def index():
    index_path = WEB_DEMO_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return HTMLResponse("<h1>GestureEngine Server</h1><p>Web demo not found.</p>")


@app.get("/canvas")
async def canvas_page():
    path = WEB_DEMO_DIR / "canvas.html"
    if path.exists():
        return FileResponse(path)
    return HTMLResponse("<h1>Canvas not found</h1>", status_code=404)


@app.get("/demo/{filename}")
async def demo_files(filename: str):
    file_path = WEB_DEMO_DIR / filename
    if file_path.exists() and file_path.is_file():
        return FileResponse(file_path)
    return HTMLResponse("Not found", status_code=404)


# --- API endpoints ---

@app.get("/api/status")
async def api_status():
    return {
        "running": state.running,
        "clients": len(state.clients),
        "canvas_clients": len(state.canvas_clients),
        "fps": round(state.fps, 1),
        "latency_ms": round(state.latency_ms, 1),
        "total_gestures": state.total_gestures,
        "last_gesture": state.last_gesture,
        "plugins": state.plugin_manager.plugin_names if state.plugin_manager else [],
    }


@app.get("/api/gestures")
async def list_gestures():
    if state.classifier:
        registry = state.classifier._registry
        return {"gestures": [g.to_dict() for g in registry]}
    return {"gestures": []}


@app.get("/api/heatmap")
async def gesture_heatmap():
    """Get gesture frequency heatmap data."""
    return {"heatmap": state.gesture_heatmap}


@app.get("/api/trajectories")
async def list_trajectories():
    """List registered trajectory templates."""
    if state.trajectory_tracker:
        return {
            "trajectories": [
                {"name": t.name, "min_score": t.min_score, "description": t.description, "points": len(t.points)}
                for t in state.trajectory_tracker.templates
            ]
        }
    return {"trajectories": []}


@app.get("/api/plugins")
async def list_plugins():
    if state.plugin_manager:
        return {
            "plugins": [
                {"name": p.name, "version": p.version, "description": p.description}
                for p in state.plugin_manager.plugins.values()
            ]
        }
    return {"plugins": []}


# --- Prometheus metrics ---

@app.get("/metrics")
async def metrics():
    state.metrics.set_connections(len(state.clients) + len(state.canvas_clients))
    return PlainTextResponse(
        state.metrics.render(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


# --- WebSocket: gestures ---

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    state.clients.add(ws)
    logger.info(f"Client connected ({len(state.clients)} total)")

    try:
        await ws.send_json({
            "type": "connected",
            "gestures": [g.name for g in state.classifier._registry] if state.classifier else [],
            "trajectories": [t.name for t in state.trajectory_tracker.templates] if state.trajectory_tracker else [],
        })

        while True:
            try:
                msg = await asyncio.wait_for(ws.receive_text(), timeout=30)
                data = json.loads(msg)
                if data.get("type") == "ping":
                    await ws.send_json({"type": "pong", "server_time": time.time()})
                elif data.get("type") == "get_heatmap":
                    await ws.send_json({"type": "heatmap", "data": state.gesture_heatmap})
            except asyncio.TimeoutError:
                await ws.send_json({"type": "ping"})
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.debug(f"WebSocket error: {e}")
    finally:
        state.clients.discard(ws)
        logger.info(f"Client disconnected ({len(state.clients)} total)")


# --- WebSocket: canvas ---

@app.websocket("/ws/canvas")
async def canvas_websocket(ws: WebSocket):
    await ws.accept()
    state.canvas_clients.add(ws)
    logger.info(f"Canvas client connected ({len(state.canvas_clients)} total)")

    try:
        # Send full canvas state for sync
        if state.drawing_canvas:
            await ws.send_json({
                "type": "canvas_sync",
                "commands": state.drawing_canvas.get_full_state(),
            })

        while True:
            try:
                msg = await asyncio.wait_for(ws.receive_text(), timeout=30)
                data = json.loads(msg)
                if data.get("type") == "ping":
                    await ws.send_json({"type": "pong"})
                elif data.get("type") == "clear":
                    if state.drawing_canvas:
                        state.drawing_canvas.clear()
                        await broadcast_canvas({"type": "canvas_commands", "commands": [{"type": "clear"}]})
            except asyncio.TimeoutError:
                await ws.send_json({"type": "ping"})
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.debug(f"Canvas WS error: {e}")
    finally:
        state.canvas_clients.discard(ws)


async def broadcast(message: dict):
    """Send message to all gesture clients."""
    if not state.clients:
        return
    dead = set()
    payload = json.dumps(message)
    for ws in state.clients:
        try:
            await ws.send_text(payload)
        except Exception:
            dead.add(ws)
    state.clients -= dead


async def broadcast_canvas(message: dict):
    """Send message to all canvas clients."""
    if not state.canvas_clients:
        return
    dead = set()
    payload = json.dumps(message)
    for ws in state.canvas_clients:
        try:
            await ws.send_text(payload)
        except Exception:
            dead.add(ws)
    state.canvas_clients -= dead


# --- Camera capture loop ---

async def capture_loop():
    """Main loop: capture frames, detect gestures, broadcast events."""
    if cv2 is None:
        logger.error("opencv-python required for camera capture")
        return

    logger.info("Starting camera capture...")
    state.capture = cv2.VideoCapture(0)

    if not state.capture.isOpened():
        logger.error("Could not open camera")
        return

    state.detector = HandDetector(max_hands=2)
    state.classifier = GestureClassifier()
    state.sequence_detector = SequenceDetector.with_defaults()
    state.trajectory_tracker = TrajectoryTracker.with_defaults()
    state.bimanual_detector = BimanualDetector()
    state.drawing_canvas = DrawingCanvas()

    # Load plugins
    state.plugin_manager = PluginManager()
    plugin_dir = Path(__file__).parent.parent.parent / "plugins"
    loaded = state.plugin_manager.load_directory(plugin_dir)
    logger.info(f"Loaded {loaded} plugins from {plugin_dir}")
    state.plugin_manager.startup({
        "classifier": state.classifier,
        "trajectory_tracker": state.trajectory_tracker,
    })

    state.running = True

    frame_times = []
    last_gestures: dict[int, tuple[str, float]] = {}
    cooldown = 0.3

    try:
        while state.running:
            t_start = time.monotonic()

            ret, frame = state.capture.read()
            if not ret:
                await asyncio.sleep(0.01)
                continue

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Detect hands (raw for position tracking, normalized for gesture classification)
            raw_hands = state.detector.detect(frame_rgb)
            hands = state.detector.detect_normalized(frame_rgb)

            now = time.monotonic()
            tracked_pairs: list[tuple[int, np.ndarray]] = []

            for hand_idx, landmarks in enumerate(hands):
                result = state.classifier.classify(landmarks)
                if result is None:
                    continue

                gesture_name, confidence = result
                tracked_pairs.append((hand_idx, landmarks))

                # Cooldown per hand
                last = last_gestures.get(hand_idx)
                if last and last[0] == gesture_name and (now - last[1]) < cooldown:
                    continue

                last_gestures[hand_idx] = (gesture_name, now)
                state.total_gestures += 1
                state.gesture_heatmap[gesture_name] = state.gesture_heatmap.get(gesture_name, 0) + 1
                state.metrics.record_gesture(gesture_name)

                event = {
                    "type": "gesture",
                    "gesture": gesture_name,
                    "confidence": round(confidence, 3),
                    "hand_index": hand_idx,
                    "timestamp": time.time(),
                    "latency_ms": round(state.latency_ms, 1),
                }
                state.last_gesture = event
                await broadcast(event)

                # Plugin dispatch
                if state.plugin_manager:
                    state.plugin_manager.dispatch("gesture", PluginEvent(
                        type="gesture", name=gesture_name,
                        data={"confidence": confidence, "hand_index": hand_idx},
                        timestamp=now,
                    ))

                # Sequences
                seq_events = state.sequence_detector.feed(gesture_name, hand_idx, now)
                for se in seq_events:
                    state.metrics.record_sequence(se.sequence_name)
                    seq_msg = {
                        "type": "sequence",
                        "sequence": se.sequence_name,
                        "gestures": se.gestures,
                        "duration": round(se.duration, 3),
                        "timestamp": time.time(),
                    }
                    await broadcast(seq_msg)
                    if state.plugin_manager:
                        state.plugin_manager.dispatch("sequence", PluginEvent(
                            type="sequence", name=se.sequence_name,
                            data={"gestures": se.gestures, "duration": se.duration},
                            timestamp=now,
                        ))

                # Trajectory tracking
                if state.trajectory_tracker and hand_idx < len(raw_hands):
                    traj_events = state.trajectory_tracker.update(hand_idx, raw_hands[hand_idx], now)
                    for te in traj_events:
                        state.metrics.record_trajectory(te.name)
                        state.gesture_heatmap[f"traj:{te.name}"] = state.gesture_heatmap.get(f"traj:{te.name}", 0) + 1
                        traj_msg = {
                            "type": "trajectory",
                            "name": te.name,
                            "score": round(te.score, 3),
                            "hand_id": te.hand_id,
                            "duration": round(te.duration, 3),
                            "timestamp": time.time(),
                        }
                        await broadcast(traj_msg)

                # Canvas drawing (use raw landmarks for position)
                if state.drawing_canvas and hand_idx < len(raw_hands):
                    draw_cmds = state.drawing_canvas.update(raw_hands[hand_idx], gesture_name, now)
                    if draw_cmds:
                        await broadcast_canvas({
                            "type": "canvas_commands",
                            "commands": [cmd.to_dict() for cmd in draw_cmds],
                        })

            # Bimanual detection
            if state.bimanual_detector and len(tracked_pairs) >= 2:
                bi_events = state.bimanual_detector.update(tracked_pairs, now)
                for be in bi_events:
                    state.metrics.record_bimanual(be.gesture)
                    state.gesture_heatmap[f"bi:{be.gesture}"] = state.gesture_heatmap.get(f"bi:{be.gesture}", 0) + 1
                    bi_msg = {
                        "type": "bimanual",
                        "gesture": be.gesture,
                        "value": round(be.value, 4),
                        "confidence": round(be.confidence, 3),
                        "timestamp": time.time(),
                    }
                    await broadcast(bi_msg)

            t_end = time.monotonic()
            frame_latency = t_end - t_start
            frame_times.append(frame_latency)
            if len(frame_times) > 30:
                frame_times = frame_times[-30:]

            avg = sum(frame_times) / len(frame_times)
            state.fps = 1.0 / avg if avg > 0 else 0
            state.latency_ms = avg * 1000
            state.metrics.record_frame(frame_latency, len(hands))

            # Broadcast stats periodically
            if len(frame_times) % 10 == 0:
                await broadcast({
                    "type": "stats",
                    "fps": round(state.fps, 1),
                    "latency_ms": round(state.latency_ms, 1),
                    "hands_detected": len(hands),
                })

            await asyncio.sleep(0.001)

    finally:
        state.running = False
        if state.capture:
            state.capture.release()
        if state.detector:
            state.detector.close()
        if state.plugin_manager:
            state.plugin_manager.shutdown()
        logger.info("Capture loop stopped")


@app.on_event("startup")
async def startup():
    asyncio.create_task(capture_loop())


@app.on_event("shutdown")
async def shutdown():
    state.running = False


# --- CLI entry point ---

def main():
    import argparse
    import uvicorn

    parser = argparse.ArgumentParser(description="GestureEngine WebSocket Server")
    parser.add_argument("--host", default="0.0.0.0", help="Bind address")
    parser.add_argument("--port", type=int, default=8765, help="Port")
    parser.add_argument("--log-level", default="info")
    args = parser.parse_args()

    uvicorn.run(app, host=args.host, port=args.port, log_level=args.log_level)


if __name__ == "__main__":
    main()
