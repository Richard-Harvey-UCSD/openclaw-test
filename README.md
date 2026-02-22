# GestureEngine 🤚

Real-time hand gesture recognition that runs on edge devices. No cloud. No latency. Just hands.

## What This Is

A lightweight gesture recognition pipeline that turns any RGB camera into a gesture input device. Built for on-device inference — runs on a Raspberry Pi, not a datacenter.

**Two modes:**
- **Rule-based** — Define gestures via finger states and geometric constraints. Works immediately, zero training.
- **Learned** — Train a small MLP on collected landmark data. Higher accuracy, custom gestures, still runs on edge.

## Why It Matters

Every AR/VR headset, smart display, and robot needs hand understanding. Current solutions are either:
- Cloud-dependent (latency kills UX)
- Too heavy for edge hardware
- Not customizable (fixed gesture sets)

GestureEngine is none of those things.

## Architecture

```
Camera Frame (RGB)
       │
       ▼
┌─────────────┐
│ HandDetector │  ← MediaPipe Hands (21 3D landmarks)
└──────┬──────┘
       │ Normalized landmarks (wrist-centered, scale-invariant)
       ▼
┌──────────────────┐
│ GestureClassifier │  ← Rule-based OR trained MLP
└──────┬───────────┘
       │
       ▼
┌────────────────┐
│ GesturePipeline │  ← Temporal smoothing, cooldown, callbacks
└──────┬─────────┘
       │
       ▼
   GestureEvent (name, confidence, landmarks, timestamp)
```

### Key Design Decisions

- **Landmark-based, not pixel-based.** We don't classify raw images — we classify hand geometry. This makes the model tiny and position/scale invariant.
- **81-dimensional feature vector** includes fingertip distances, extension ratios, and palm orientation — not just raw coordinates.
- **Temporal smoothing** via majority vote over a sliding window eliminates single-frame jitter.
- **Cooldown system** prevents gesture spamming without losing responsiveness.

## Quick Start

```bash
# Install
pip install -e ".[train]"

# Run live demo
python examples/demo_webcam.py

# Headless mode (no display)
python examples/demo_webcam.py --no-display
```

## Define Custom Gestures

### Option 1: JSON Definition (No Training)

Create a gesture file:

```json
{
  "gestures": [
    {
      "name": "gun",
      "fingers": {
        "thumb": "extended",
        "index": "extended",
        "middle": "curled",
        "ring": "curled",
        "pinky": "curled"
      },
      "constraints": [
        {
          "type": "angle",
          "landmarks": [4, 0, 8],
          "min_angle": 30,
          "max_angle": 90
        }
      ]
    }
  ]
}
```

Finger states: `extended`, `curled`, `any`

Constraint types:
- `distance` — distance between two landmarks (min/max)
- `angle` — angle at vertex B in triangle A-B-C (min_angle/max_angle)

### Option 2: Collect & Train (Higher Accuracy)

```bash
# Collect 50 samples of your custom gesture
python examples/demo_collect.py --gesture my_gesture --samples 50

# Train (in your own script)
from gesture_engine import GestureClassifier
import numpy as np, json

classifier = GestureClassifier()
data = json.load(open("data/gestures/my_gesture.json"))
X = np.array(data)
y = ["my_gesture"] * len(X)

stats = classifier.train(X, y, epochs=100, save_path="model.pt")
print(f"Accuracy: {stats['accuracy']:.1%}")
```

## API

```python
from gesture_engine import GesturePipeline, GestureEvent

def on_gesture(event: GestureEvent):
    print(f"{event.gesture}: {event.confidence:.0%}")

pipeline = GesturePipeline(
    smoothing_window=5,    # Frames for temporal smoothing
    cooldown_seconds=0.5,  # Min time between same gesture events
    min_confidence=0.6,    # Confidence threshold
)
pipeline.on_gesture(on_gesture)

# Process frames from any source
events = pipeline.process_frame(rgb_frame)
print(pipeline.stats)  # FPS, latency, counts
```

## Built-in Gestures

| Gesture | Description |
|---------|-------------|
| `open_hand` | All fingers extended |
| `fist` | All fingers curled |
| `thumbs_up` | Thumb up, rest curled |
| `peace` | Index + middle extended |
| `pointing` | Index finger only |
| `rock_on` | Index + pinky extended |
| `ok_sign` | OK circle (thumb-index close) |

## Performance

| Device | FPS | Latency |
|--------|-----|---------|
| Raspberry Pi 4 | ~12 | ~80ms |
| M1 MacBook | ~30 | ~33ms |
| Desktop GPU | ~60+ | <16ms |

*Benchmarks are for rule-based mode. MLP adds <2ms.*

## Project Structure

```
src/gesture_engine/
├── __init__.py          # Public API
├── detector.py          # MediaPipe hand detection + normalization
├── classifier.py        # Rule-based + MLP classification
├── gestures.py          # Gesture definitions + registry
└── pipeline.py          # Real-time pipeline with smoothing
examples/
├── demo_webcam.py       # Live camera demo
├── demo_collect.py      # Training data collection
└── gestures.json        # Example custom gesture definitions
```

## License

MIT
