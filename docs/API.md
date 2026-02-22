# GestureEngine API Documentation

## Server

Start the server:

```bash
gesture-engine serve --host 0.0.0.0 --port 8765
# or
uvicorn gesture_engine.server:app --host 0.0.0.0 --port 8765
```

Base URL: `http://localhost:8765`

---

## REST Endpoints

### `GET /`
Serves the main web demo page.

### `GET /canvas`
Serves the finger painting canvas page.

### `GET /api/status`
Server status and statistics.

**Response:**
```json
{
  "running": true,
  "clients": 3,
  "canvas_clients": 1,
  "fps": 29.8,
  "latency_ms": 4.7,
  "total_gestures": 142,
  "last_gesture": {
    "type": "gesture",
    "gesture": "peace",
    "confidence": 0.95,
    "hand_index": 0,
    "timestamp": 1708000000.0,
    "latency_ms": 4.7
  },
  "plugins": ["event_logger"]
}
```

### `GET /api/gestures`
List all registered gesture definitions.

**Response:**
```json
{
  "gestures": [
    {
      "name": "open_hand",
      "fingers": {
        "thumb": "extended",
        "index": "extended",
        "middle": "extended",
        "ring": "extended",
        "pinky": "extended"
      },
      "min_confidence": 0.6,
      "constraints": []
    }
  ]
}
```

### `GET /api/heatmap`
Gesture frequency counts for heatmap visualization.

**Response:**
```json
{
  "heatmap": {
    "fist": 45,
    "open_hand": 32,
    "peace": 18,
    "traj:swipe_right": 5,
    "bi:pinch_zoom": 3
  }
}
```

### `GET /api/trajectories`
List registered trajectory templates.

**Response:**
```json
{
  "trajectories": [
    {
      "name": "swipe_right",
      "min_score": 0.6,
      "description": "Horizontal swipe from left to right",
      "points": 21
    }
  ]
}
```

### `GET /api/plugins`
List loaded plugins.

**Response:**
```json
{
  "plugins": [
    {
      "name": "event_logger",
      "version": "1.0.0",
      "description": "Logs all gesture events to a JSON-lines file with counts"
    }
  ]
}
```

### `GET /metrics`
Prometheus metrics endpoint.

**Response:** `text/plain` in Prometheus exposition format.

```
# HELP gesture_engine_gestures_total Total gesture detections by name
# TYPE gesture_engine_gestures_total counter
gesture_engine_gestures_total{gesture="fist"} 45
gesture_engine_gestures_total{gesture="open_hand"} 32

# HELP gesture_engine_frame_latency_seconds Frame processing latency in seconds
# TYPE gesture_engine_frame_latency_seconds histogram
gesture_engine_frame_latency_seconds_bucket{le="0.005"} 1200
gesture_engine_frame_latency_seconds_bucket{le="0.01"} 1450
gesture_engine_frame_latency_seconds_bucket{le="+Inf"} 1500
gesture_engine_frame_latency_seconds_sum 7.234
gesture_engine_frame_latency_seconds_count 1500

# HELP gesture_engine_active_connections Current WebSocket connections
# TYPE gesture_engine_active_connections gauge
gesture_engine_active_connections 3
```

---

## WebSocket Endpoints

### `ws://host:port/ws` — Gesture Events

Main event stream for gesture detection results.

#### Server → Client Messages

**`connected`** — Sent on connection:
```json
{
  "type": "connected",
  "gestures": ["open_hand", "fist", "peace", "..."],
  "trajectories": ["swipe_right", "swipe_left", "circle_cw", "..."]
}
```

**`gesture`** — Single-hand gesture detected:
```json
{
  "type": "gesture",
  "gesture": "thumbs_up",
  "confidence": 0.95,
  "hand_index": 0,
  "timestamp": 1708000000.123,
  "latency_ms": 4.7
}
```

**`sequence`** — Multi-gesture sequence completed:
```json
{
  "type": "sequence",
  "sequence": "release",
  "gestures": ["fist", "open_hand"],
  "duration": 0.832,
  "timestamp": 1708000000.456
}
```

**`trajectory`** — Spatial trajectory matched:
```json
{
  "type": "trajectory",
  "name": "swipe_right",
  "score": 0.82,
  "hand_id": 0,
  "duration": 0.654,
  "timestamp": 1708000000.789
}
```

**`bimanual`** — Two-hand gesture detected:
```json
{
  "type": "bimanual",
  "gesture": "pinch_zoom",
  "value": 1.35,
  "confidence": 0.88,
  "timestamp": 1708000001.0
}
```

Bimanual `value` semantics:
- `pinch_zoom`: zoom factor (>1 = hands apart, <1 = hands together)
- `clap`: convergence velocity
- `frame`: inter-hand width
- `conduct_up/down`: average vertical velocity

**`stats`** — Periodic performance update (every ~10 frames):
```json
{
  "type": "stats",
  "fps": 29.8,
  "latency_ms": 4.7,
  "hands_detected": 2
}
```

**`heatmap`** — Response to `get_heatmap` request:
```json
{
  "type": "heatmap",
  "data": {"fist": 45, "peace": 18}
}
```

**`ping`** — Server keepalive (every 30s of inactivity):
```json
{"type": "ping"}
```

#### Client → Server Messages

**`ping`** — Keepalive response:
```json
{"type": "ping"}
```

**`get_heatmap`** — Request gesture frequency data:
```json
{"type": "get_heatmap"}
```

---

### `ws://host:port/ws/canvas` — Drawing Canvas

Real-time finger painting canvas stream.

#### Server → Client Messages

**`canvas_sync`** — Full state on connect (replay all commands):
```json
{
  "type": "canvas_sync",
  "commands": [
    {"type": "clear"},
    {"type": "line", "x1": 0.1, "y1": 0.2, "x2": 0.15, "y2": 0.22, "color": "#ffffff", "width": 3},
    {"type": "erase", "x": 0.5, "y": 0.5, "radius": 25}
  ]
}
```

**`canvas_commands`** — Incremental drawing updates:
```json
{
  "type": "canvas_commands",
  "commands": [
    {"type": "line", "x1": 0.3, "y1": 0.4, "x2": 0.32, "y2": 0.41, "color": "#22c55e", "width": 3}
  ]
}
```

Command types:
- `line`: Draw line segment. Coordinates are normalized [0,1].
- `erase`: Circular eraser at position with radius.
- `clear`: Clear entire canvas.
- `color`: Color change notification.

#### Client → Server Messages

**`clear`** — Request canvas clear:
```json
{"type": "clear"}
```

**`ping`** — Keepalive:
```json
{"type": "ping"}
```

---

## Python API

### Quick Start

```python
from gesture_engine import GesturePipeline, HandDetector, GestureClassifier
import cv2

pipeline = GesturePipeline()

def on_gesture(event):
    print(f"{event.gesture} ({event.confidence:.0%}) hand={event.hand_id}")

pipeline.on_gesture(on_gesture)

cap = cv2.VideoCapture(0)
while True:
    ret, frame = cap.read()
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    events = pipeline.process_frame(frame_rgb)
```

### Trajectory Tracking

```python
from gesture_engine import TrajectoryTracker

tracker = TrajectoryTracker.with_defaults()

# Custom template
tracker.start_recording("heart")
# ... feed landmarks ...
template = tracker.stop_recording()

# In frame loop
events = tracker.update(hand_id=0, landmarks=lm, timestamp=now)
```

### Two-Hand Gestures

```python
from gesture_engine import BimanualDetector

detector = BimanualDetector()
events = detector.update(hands=[(0, lm0), (1, lm1)], timestamp=now)
for event in events:
    if event.gesture == "pinch_zoom":
        print(f"Zoom: {event.value:.2f}x")
```

### Plugins

```python
from gesture_engine import GesturePlugin, PluginManager

class MyPlugin(GesturePlugin):
    name = "my_plugin"

    def on_gesture(self, event):
        if event.name == "thumbs_up":
            print("Approved!")

manager = PluginManager()
manager.register(MyPlugin())
manager.startup({})
```

### Action Mapping

```yaml
# actions.yml
mappings:
  - trigger: thumbs_up
    actions:
      - type: keyboard
        params: { keys: "space" }
  - trigger: swipe_right
    actions:
      - type: shell
        params: { command: "playerctl next" }
  - trigger: pinch_zoom
    actions:
      - type: webhook
        params: { url: "http://localhost:3000/zoom" }
```

```python
from gesture_engine import ActionMapper
mapper = ActionMapper.from_yaml("actions.yml")
await mapper.on_gesture("thumbs_up", confidence=0.95)
```
