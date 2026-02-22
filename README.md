# GestureEngine 🤚

**Real-time hand gesture recognition for edge devices.** No cloud. No latency. Just hands.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-green.svg)](https://python.org)
[![Tests](https://github.com/yourorg/gesture-engine/actions/workflows/test.yml/badge.svg)](https://github.com/yourorg/gesture-engine/actions)

GestureEngine turns any RGB camera into a gesture input device. It runs on a Raspberry Pi, ships with a WebSocket streaming API, and recognizes gestures, spatial movements, two-hand interactions, and even lets you finger-paint in the air — all in under 5ms per frame.

---

## ⚡ Quick Start

```bash
git clone https://github.com/yourorg/gesture-engine.git
cd gesture-engine
pip install -e ".[all,cli]"

# Start the WebSocket server + web demo
gesture-engine serve --port 8765

# Open http://localhost:8765 in your browser
```

### Docker (one command)

```bash
docker-compose up --build
# Open http://localhost:8765
```

## 🎯 Features

| Feature | Description |
|---------|-------------|
| **7 built-in gestures** | open_hand, fist, thumbs_up, peace, pointing, rock_on, ok_sign |
| **6 gesture sequences** | release, grab, wave, peace_out, pinch_release, point_and_click |
| **8 spatial trajectories** | swipe L/R/U/D, circle CW/CCW, Z-pattern, wave — via DTW matching |
| **4 two-hand gestures** | pinch-to-zoom, clap, frame, conducting |
| **Air drawing canvas** | Finger painting with gesture-based color switching and erasing |
| **Plugin system** | Drop a .py file in plugins/ — auto-loads and receives all events |
| **Prometheus metrics** | `/metrics` endpoint with latency histograms, gesture counters |
| **Action mapping** | Map gestures to keyboard shortcuts, shell commands, webhooks, OSC |
| **CLI toolchain** | `serve`, `train`, `record`, `replay`, `benchmark`, `define`, `export` |
| **ONNX/TFLite export** | Edge deployment with INT8 quantization for Pi hardware |
| **Hand tracking** | Stable hand IDs across frames for multi-hand use |
| **Adaptive thresholds** | Auto-adjusting confidence per gesture based on confusion rates |
| **Performance profiler** | Per-stage timing (detection, classification, sequences) |
| **WebSocket streaming** | Real-time events pushed to any client |
| **Browser demo** | Dark-themed live UI with gesture heatmap and air canvas |
| **Recording & replay** | Capture sessions for testing without a camera |
| **Docker support** | One-command demo with webcam passthrough |
| **CI/CD** | GitHub Actions with pytest on Python 3.10-3.12 |

## 🏗 Architecture

```
Camera → HandDetector → HandTracker → GestureClassifier → Temporal Smoothing
                                                               │
                          ┌────────────────────────────────────┤
                          │              │           │         │
                   SequenceDetector  TrajectoryTracker  BimanualDetector
                          │              │           │         │
                          └──────────┬───┘           │    DrawingCanvas
                                     │               │         │
                              ActionMapper    PluginManager  WebSocket
                                     │               │      Broadcast
                                  Execute        Dispatch       │
                            (keyboard/shell/     to all      Browser
                             webhook/OSC)       plugins       Demo
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full technical deep-dive.

## 📡 API

### WebSocket Events

Connect to `ws://host:port/ws` for real-time gesture events:

```json
{"type": "gesture", "gesture": "peace", "confidence": 0.95, "hand_index": 0}
{"type": "sequence", "sequence": "release", "gestures": ["fist", "open_hand"]}
{"type": "trajectory", "name": "swipe_right", "score": 0.82}
{"type": "bimanual", "gesture": "pinch_zoom", "value": 1.35}
```

Connect to `ws://host:port/ws/canvas` for finger painting canvas events.

### REST API

| Endpoint | Description |
|----------|-------------|
| `GET /api/status` | Server status, FPS, latency, client count |
| `GET /api/gestures` | List gesture definitions |
| `GET /api/heatmap` | Gesture frequency data |
| `GET /api/trajectories` | Registered trajectory templates |
| `GET /api/plugins` | Loaded plugins |
| `GET /metrics` | Prometheus metrics |

See [docs/API.md](docs/API.md) for full documentation.

## 🎨 Air Drawing

Point your index finger to draw. Change colors with gestures:

| Gesture | Action |
|---------|--------|
| ☝️ Point | Draw (white) |
| ✌️ Peace | Draw (green) |
| 🤘 Rock on | Draw (red) |
| 👌 OK sign | Draw (blue) |
| ✊ Fist | Erase |
| 🖐 Open hand shake | Clear canvas |

Visit `http://localhost:8765/canvas` for the live canvas demo.

## 🔌 Plugins

Create `plugins/my_plugin.py`:

```python
from gesture_engine.plugins import GesturePlugin, PluginEvent

class MyPlugin(GesturePlugin):
    name = "my_plugin"

    def on_gesture(self, event: PluginEvent):
        if event.name == "thumbs_up":
            print("Approved!")

    def on_trajectory(self, event: PluginEvent):
        if event.name == "swipe_right":
            print("Next slide!")
```

Plugins auto-load on server start. See `plugins/example_logger.py` for a full example.

## ↗️ Spatial Gestures

Track hand movement through space using Dynamic Time Warping:

```python
from gesture_engine import TrajectoryTracker

tracker = TrajectoryTracker.with_defaults()

# Built-in: swipe_right, swipe_left, swipe_up, swipe_down,
#           circle_cw, circle_ccw, z_pattern, wave

# Record custom trajectories:
tracker.start_recording("heart")
# ... feed frames ...
tracker.stop_recording()
```

## 🤝 Two-Hand Gestures

```python
from gesture_engine import BimanualDetector

detector = BimanualDetector()
events = detector.update(hands=[(0, left_lm), (1, right_lm)])

# Detects: pinch_zoom, clap, frame, conduct_up, conduct_down
```

## 📊 Monitoring

Prometheus-compatible metrics at `/metrics`:

```
gesture_engine_gestures_total{gesture="peace"} 142
gesture_engine_frame_latency_seconds_bucket{le="0.005"} 1200
gesture_engine_active_connections 3
```

## ⚡ Performance

Benchmarked on desktop (i7-12700K) and Raspberry Pi 4:

| Stage | Desktop | RPi 4 |
|-------|---------|-------|
| Hand detection | 3-5ms | 15-20ms |
| Classification | <0.1ms | 0.3ms |
| Full pipeline | 4-6ms | 18-25ms |
| Throughput | 180+ FPS | 40-55 FPS |

```bash
gesture-engine benchmark --iterations 1000
```

## 🛠 CLI

```bash
gesture-engine serve       # Start WebSocket server + web demo
gesture-engine train       # Train MLP from collected data
gesture-engine record      # Record landmark data from camera
gesture-engine replay      # Replay a recorded session
gesture-engine benchmark   # Run performance benchmarks
gesture-engine define      # Interactive gesture definition
gesture-engine export      # Export model to ONNX/TFLite
```

## 📦 Installation

```bash
# Minimal (classification only, no camera)
pip install -e .

# With camera support
pip install -e ".[camera]"

# Full stack
pip install -e ".[all,cli,dev]"
```

## 🧪 Testing

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

## 🎮 Unity SDK

GestureEngine includes a full Unity SDK for XR/game developers.

### Installation (Unity Package Manager)

1. Open **Window → Package Manager** → **+** → **Add package from git URL**
2. Enter: `https://github.com/yourorg/gesture-engine.git?path=unity/com.gestureengine.sdk`

### Quick Start

```csharp
using GestureEngine;

public class MyGame : MonoBehaviour
{
    void Start()
    {
        GestureManager.Instance.OnGesture.AddListener(evt =>
        {
            Debug.Log($"Detected: {evt.gesture} ({evt.confidence:P0})");
        });
    }
}
```

### Features

- **WebSocket client** — connects to GestureEngine server, auto-reconnect, main-thread marshaling
- **GestureManager** — singleton MonoBehaviour with UnityEvents for all event types
- **GestureBinding** — map gestures to actions in the Inspector (with confidence thresholds and cooldowns)
- **Hand visualization** — 21-landmark spheres + bone lines in Scene and Game view
- **Native C# classifier** — run gesture recognition without the Python server
- **Cross-platform definitions** — same JSON gesture format works in Python and C#

See [Unity SDK docs](unity/com.gestureengine.sdk/README.md) and [Protocol docs](docs/PROTOCOL.md) for details.

## 📄 License

MIT
