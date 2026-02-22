"""WebSocket streaming server for real-time gesture events.

Captures from the server's webcam and pushes gesture events
to all connected WebSocket clients as JSON messages.

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
    from fastapi.responses import FileResponse, HTMLResponse
    from fastapi.staticfiles import StaticFiles
except ImportError:
    raise ImportError("FastAPI required. Install with: pip install fastapi uvicorn")

try:
    import cv2
except ImportError:
    cv2 = None

from gesture_engine.classifier import GestureClassifier
from gesture_engine.detector import HandDetector
from gesture_engine.gestures import GestureRegistry
from gesture_engine.sequences import SequenceDetector

logger = logging.getLogger("gesture_engine.server")

app = FastAPI(title="GestureEngine", version="0.1.0")

# --- State ---

class ServerState:
    def __init__(self):
        self.clients: set[WebSocket] = set()
        self.detector: Optional[HandDetector] = None
        self.classifier: Optional[GestureClassifier] = None
        self.sequence_detector: Optional[SequenceDetector] = None
        self.capture: Optional[object] = None  # cv2.VideoCapture
        self.running = False
        self.fps = 0.0
        self.latency_ms = 0.0
        self.total_gestures = 0
        self.last_gesture: Optional[dict] = None

state = ServerState()


# --- Web demo serving ---

WEB_DEMO_DIR = Path(__file__).parent.parent.parent / "examples" / "web_demo"


@app.get("/")
async def index():
    index_path = WEB_DEMO_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return HTMLResponse("<h1>GestureEngine Server</h1><p>Web demo not found. Place index.html in examples/web_demo/</p>")


@app.get("/demo/{filename}")
async def demo_files(filename: str):
    file_path = WEB_DEMO_DIR / filename
    if file_path.exists() and file_path.is_file():
        return FileResponse(file_path)
    return HTMLResponse("Not found", status_code=404)


# --- API endpoints ---

@app.get("/api/status")
async def status():
    return {
        "running": state.running,
        "clients": len(state.clients),
        "fps": round(state.fps, 1),
        "latency_ms": round(state.latency_ms, 1),
        "total_gestures": state.total_gestures,
        "last_gesture": state.last_gesture,
    }


@app.get("/api/gestures")
async def list_gestures():
    if state.classifier:
        registry = state.classifier._registry
        return {"gestures": [g.to_dict() for g in registry]}
    return {"gestures": []}


# --- WebSocket ---

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    state.clients.add(ws)
    logger.info(f"Client connected ({len(state.clients)} total)")

    try:
        # Send initial state
        await ws.send_json({
            "type": "connected",
            "gestures": [g.name for g in state.classifier._registry] if state.classifier else [],
        })

        # Keep connection alive, listen for client messages
        while True:
            try:
                msg = await asyncio.wait_for(ws.receive_text(), timeout=30)
                # Client can send pings or config changes
                data = json.loads(msg)
                if data.get("type") == "ping":
                    await ws.send_json({"type": "pong", "server_time": time.time()})
            except asyncio.TimeoutError:
                # Send keepalive
                await ws.send_json({"type": "ping"})
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.debug(f"WebSocket error: {e}")
    finally:
        state.clients.discard(ws)
        logger.info(f"Client disconnected ({len(state.clients)} total)")


async def broadcast(message: dict):
    """Send message to all connected clients."""
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
    state.running = True

    frame_times = []
    last_gestures: dict[int, tuple[str, float]] = {}  # hand_idx → (gesture, time)
    cooldown = 0.3

    try:
        while state.running:
            t_start = time.monotonic()

            ret, frame = state.capture.read()
            if not ret:
                await asyncio.sleep(0.01)
                continue

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            hands = state.detector.detect_normalized(frame_rgb)

            now = time.monotonic()

            for hand_idx, landmarks in enumerate(hands):
                result = state.classifier.classify(landmarks)
                if result is None:
                    continue

                gesture_name, confidence = result

                # Cooldown per hand
                last = last_gestures.get(hand_idx)
                if last and last[0] == gesture_name and (now - last[1]) < cooldown:
                    continue

                last_gestures[hand_idx] = (gesture_name, now)
                state.total_gestures += 1

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

                # Check sequences
                seq_events = state.sequence_detector.feed(gesture_name, hand_idx, now)
                for se in seq_events:
                    seq_msg = {
                        "type": "sequence",
                        "sequence": se.sequence_name,
                        "gestures": se.gestures,
                        "duration": round(se.duration, 3),
                        "timestamp": time.time(),
                    }
                    await broadcast(seq_msg)

            t_end = time.monotonic()
            frame_times.append(t_end - t_start)
            if len(frame_times) > 30:
                frame_times = frame_times[-30:]

            avg = sum(frame_times) / len(frame_times)
            state.fps = 1.0 / avg if avg > 0 else 0
            state.latency_ms = avg * 1000

            # Broadcast stats periodically
            if len(frame_times) % 10 == 0:
                await broadcast({
                    "type": "stats",
                    "fps": round(state.fps, 1),
                    "latency_ms": round(state.latency_ms, 1),
                    "hands_detected": len(hands),
                })

            # Yield to event loop
            await asyncio.sleep(0.001)

    finally:
        state.running = False
        if state.capture:
            state.capture.release()
        if state.detector:
            state.detector.close()
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
