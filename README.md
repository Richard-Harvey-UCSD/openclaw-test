# GestureEngine 🤚

**Real-time hand gesture recognition for edge devices.** No cloud. No latency. Just hands.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-green.svg)](https://python.org)

GestureEngine turns any RGB camera into a gesture input device. It runs on a Raspberry Pi, ships with a WebSocket streaming API, and recognizes both individual gestures and multi-gesture sequences — all in under 5ms per frame.

---

## ⚡ Quick Start

```bash
git clone https://github.com/yourorg/gesture-engine.git
cd gesture-engine
pip install -e ".[server]"

# Start the WebSocket server + web demo
python -m gesture_engine --port 8765

# Open http://localhost:8765 in your browser
```

## 🎯 What It Does

| Feature | Description |
|---------|-------------|
| **7 built-in gestures** | open_hand, fist, thumbs_up, peace, pointing, rock_on, ok_sign |
| **6 gesture sequences** | release, grab, wave, peace_out, pinch_release, point_and_click |
| **WebSocket streaming** | Real-time gesture events pushed to any client |
| **Browser demo** | Dark-themed live UI with confidence meters and timeline |
| **Recording & replay** | Capture sessions for testing without a camera |
| **Benchmark suite** | Measure latency and throughput on your hardware |
| **Custom gestures** | Define via JSON or train an MLP classifier |

## 🏗 Architecture

```
Camera Frame (RGB)
       │
       ▼
┌─────────────┐
│ HandDetector │  ← MediaPipe (21 3D landmarks)
└──────┬──────┘
       │ Normalized landmarks (wrist-centered, scale-invariant)
       ▼
┌──────────────────┐
│ GestureClassifier │  ← Rule-based OR trained MLP (81-dim features)
└──────┬───────────┘
       │
       ├──▶ GesturePipeline  ← Temporal smoothing, cooldown, callbacks
       │
       └──▶ SequenceDetector ← Multi-gesture pattern matching
              │
              ▼
         WebSocket Server  ← FastAPI/uvicorn → Browser clients
```

### Design Decisions

- **Landmark-based, not pixel-based.** Classify hand geometry, not images. Makes the model tiny and position/scale invariant.
- **81-dimensional feature vector** — fingertip distances, extension ratios, palm orientation. Not just raw coordinates.
- **Temporal smoothing** via majority vote eliminates single-frame jitter.
- **Sequence detection** watches for gesture transitions within time windows (e.g., fist→open_hand = "release").

## 🖥 WebSocket Streaming Server

The server captures from the webcam and pushes gesture events to all connected WebSocket clients:

```bash
# Start server
python -m gesture_engine --host 0.0.0.0 --port 8765

# Or via uvicorn directly
uvicorn gesture_engine.server:app --host 0.0.0.0 --port 8765
```

**Endpoints:**
- `GET /` — Web demo UI
- `GET /api/status` — Server stats (FPS, latency, clients)
- `GET /api/gestures` — Registered gesture definitions
- `WS /ws` — Real-time gesture event stream

**WebSocket message types:**
```json
{"type": "gesture", "gesture": "peace", "confidence": 0.95, "hand_index": 0, "timestamp": 1708000000.0}
{"type": "sequence", "sequence": "grab", "gestures": ["open_hand", "fist"], "duration": 0.8}
{"type": "stats", "fps": 28.5, "latency_ms": 35.1, "hands_detected": 1}
```

## 🌐 Browser Demo

Open `http://localhost:8765` after starting the server. Features:

- **Live gesture display** with emoji and confidence meter
- **Gesture sequence detection** highlighted in gold
- **Event timeline** with timestamps
- **Real-time metrics** — FPS, latency, hand count
- Dark theme, no JavaScript frameworks, pure CSS

## 🎬 Recording & Replay

Record gesture sessions for reproducible testing:

```python
from gesture_engine import GestureRecorder, GesturePlayer

# Record
recorder = GestureRecorder()
recorder.start()
recorder.add_frame(hand_landmarks, [{"name": "peace", "confidence": 0.9}])
recorder.stop()
recorder.save("session.json")           # JSON format
recorder.save_compact("session.npz")    # Compact binary

# Replay
player = GesturePlayer.load("session.json")
for frame in player.play():             # Instant playback
    process(frame.hands)

for frame in player.play_realtime(speed=2.0):  # 2x speed
    process(frame.hands)
```

Useful for:
- CI pipelines on headless machines
- Demo recordings without camera access
- Regression testing

## 🔗 Gesture Sequences

Detect compound gestures — ordered transitions within a time window:

```python
from gesture_engine import SequenceDetector, GestureSequence

detector = SequenceDetector.with_defaults()

# Built-in sequences:
# fist → open_hand    = "release"
# open_hand → fist    = "grab"
# peace → fist        = "peace_out"
# pointing → fist     = "point_and_click"
# ok_sign → open_hand = "pinch_release"
# open_hand → fist → open_hand = "wave"

# Custom sequences:
detector.register(GestureSequence(
    name="swipe_right",
    gestures=["pointing", "open_hand"],
    max_duration=1.0,
))

# Feed gesture observations
events = detector.feed("fist")
events = detector.feed("open_hand")  # → triggers "release"
```

## 📊 Benchmarks

```bash
python examples/benchmark.py
python examples/benchmark.py --iterations 5000 --hands 2
```

Sample output (Raspberry Pi 4):

```
  ╭──────────────────────────────────────────────────╮
  │ Rule-Based Classification                        │
  ├──────────────────────────────────────────────────┤
  │ Mean latency         0.042 ms                    │
  │ P95 latency          0.055 ms                    │
  │ Throughput       23,809 classifications/sec      │
  ╰──────────────────────────────────────────────────╯
```

## 🎨 Custom Gestures

### JSON (Zero-Shot)

```json
{
  "gestures": [{
    "name": "gun",
    "fingers": { "thumb": "extended", "index": "extended", "middle": "curled", "ring": "curled", "pinky": "curled" },
    "constraints": [{ "type": "angle", "landmarks": [4, 0, 8], "min_angle": 30, "max_angle": 90 }]
  }]
}
```

### Train MLP (Higher Accuracy)

```python
from gesture_engine import GestureClassifier
classifier = GestureClassifier()
stats = classifier.train(X_landmarks, y_labels, epochs=100, save_path="model.pt")
```

## 📁 Project Structure

```
src/gesture_engine/
├── __init__.py        # Public API
├── detector.py        # MediaPipe hand detection + normalization
├── classifier.py      # Rule-based + MLP classification
├── gestures.py        # Gesture definitions + registry
├── pipeline.py        # Real-time pipeline with smoothing
├── sequences.py       # Multi-gesture sequence detection
├── recorder.py        # Record & replay gesture sessions
└── server.py          # WebSocket streaming server (FastAPI)
examples/
├── web_demo/          # Browser-based live demo
│   └── index.html
├── benchmark.py       # Performance measurement suite
├── demo_webcam.py     # Live camera demo
└── demo_collect.py    # Training data collection
tests/                 # pytest test suite
```

## 🛠 Installation

```bash
# Core (detection + classification)
pip install -e .

# With WebSocket server
pip install -e ".[server]"

# With ML training
pip install -e ".[train]"

# Everything
pip install -e ".[all]"
```

**Requirements:** Python 3.10+, a webcam (optional — use recordings for testing)

## API Reference

```python
from gesture_engine import (
    GesturePipeline,     # End-to-end: frame → events
    HandDetector,        # MediaPipe landmark extraction
    GestureClassifier,   # Rule-based + MLP classification
    GestureRegistry,     # Gesture definition management
    SequenceDetector,    # Multi-gesture sequences
    GestureRecorder,     # Session recording
    GesturePlayer,       # Session replay
)
```

## License

[MIT](LICENSE)
