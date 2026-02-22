# GestureEngine 🤚

**Real-time hand gesture recognition for edge devices.** No cloud. No latency. Just hands.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-green.svg)](https://python.org)
[![Tests](https://github.com/yourorg/gesture-engine/actions/workflows/test.yml/badge.svg)](https://github.com/yourorg/gesture-engine/actions)

GestureEngine turns any RGB camera into a gesture input device. It runs on a Raspberry Pi, ships with a WebSocket streaming API, and recognizes both individual gestures and multi-gesture sequences — all in under 5ms per frame.

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
| **Action mapping** | Map gestures to keyboard shortcuts, shell commands, webhooks, OSC |
| **CLI toolchain** | `serve`, `train`, `record`, `replay`, `benchmark`, `define`, `export` |
| **ONNX/TFLite export** | Edge deployment with INT8 quantization for Pi hardware |
| **Hand tracking** | Stable hand IDs across frames for multi-hand use |
| **Adaptive thresholds** | Auto-adjusting confidence per gesture based on confusion rates |
| **Performance profiler** | Per-stage timing (detection, classification, sequences) |
| **WebSocket streaming** | Real-time events pushed to any client |
| **Browser demo** | Dark-themed live UI with confidence meters and timeline |
| **Recording & replay** | Capture sessions for testing without a camera |
| **Docker support** | One-command demo with webcam passthrough |
| **CI/CD** | GitHub Actions with pytest on Python 3.10-3.12 |

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
┌─────────────┐
│ HandTracker  │  ← Stable hand IDs via centroid matching
└──────┬──────┘
       │
       ▼
┌──────────────────┐
│ GestureClassifier │  ← Rule-based OR trained MLP (81-dim features)
└──────┬───────────┘
       │
       ▼
┌────────────────────┐
│ AdaptiveThresholds  │  ← Per-gesture confidence auto-tuning
└──────┬─────────────┘
       │
  ┌────┴────┐
  ▼         ▼
Gesture   Sequence     →  ActionMapper  →  Keyboard / Shell / Webhook / OSC
Events    Detection
```

## 🖥 CLI Reference

```bash
# Start the server with action mappings
gesture-engine serve --port 8765 --actions config/actions.example.yml

# Record gesture data from camera
gesture-engine record -o session.json --duration 30

# Train MLP classifier from recordings
gesture-engine train ./recordings/ --output model.pt --epochs 200

# Replay a recorded session
gesture-engine replay session.json --speed 2.0

# Run benchmarks
gesture-engine benchmark --iterations 5000

# Define a gesture interactively
gesture-engine define

# Export model for edge deployment
gesture-engine export model.pt --format onnx --output gesture_model
gesture-engine export model.pt --format tflite --int8
```

## ⚡ Action Mapping

Map gestures to real actions via YAML config:

```yaml
# config/actions.yml
mappings:
  - trigger: thumbs_up
    min_confidence: 0.8
    actions:
      - type: keyboard
        params: { keys: "space" }
        description: "Play/pause media"
        cooldown: 1.0

  - trigger: pointing
    actions:
      - type: keyboard
        params: { keys: "Right" }
        cooldown: 1.5

  - trigger: grab  # sequence trigger
    actions:
      - type: webhook
        params:
          url: "http://localhost:8080/api/grab"
        cooldown: 2.0

  - trigger: fist
    actions:
      - type: osc
        params:
          address: "/gesture/fist"
          port: 9000
```

Action types: `keyboard` (xdotool), `shell`, `webhook` (HTTP POST), `osc`, `log`.

## 📦 Model Export

Export trained models for edge deployment:

```python
from gesture_engine.classifier import GestureClassifier
from gesture_engine.export import ModelExporter

classifier = GestureClassifier(model_path="model.pt")
exporter = ModelExporter(classifier)

# ONNX (universal)
exporter.to_onnx("gesture_model.onnx")

# TFLite with INT8 quantization (Raspberry Pi)
exporter.to_tflite("gesture_model.tflite", quantize_int8=True, representative_data=X)
```

## 📊 Performance Profiling

Every pipeline stage is instrumented:

```python
pipeline = GesturePipeline(enable_profiling=True)
# ... process frames ...

stats = pipeline.stats
print(stats.profiler_summary)
# {'detection': {'avg_ms': 2.1, 'p95_ms': 3.4, ...},
#  'classification': {'avg_ms': 0.3, 'p95_ms': 0.5, ...}, ...}
```

## 🔧 Installation

```bash
# Core (detection + classification)
pip install -e .

# With server
pip install -e ".[server,cli]"

# Everything
pip install -e ".[all,cli,export]"

# Development
pip install -e ".[dev]"
```

## 🧪 Testing

```bash
pytest tests/ -v
```

## 🐳 Docker

```bash
# Build and run with webcam
docker-compose up --build

# Or standalone
docker build -t gesture-engine .
docker run -p 8765:8765 --device /dev/video0 gesture-engine
```

## 📄 License

MIT
