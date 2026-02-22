# GestureEngine Architecture

> Technical architecture document for engineers evaluating the system.

## Overview

GestureEngine is a real-time hand gesture recognition pipeline that transforms RGB camera frames into structured gesture events in under 5ms. It runs entirely on-device with no cloud dependencies.

```
Camera Frame (RGB)
       │
       ▼
┌─────────────┐
│ HandDetector │  MediaPipe Hands → 21 3D landmarks per hand
└──────┬──────┘
       │ list[ndarray(21,3)]
       ▼
┌──────────────┐
│ HandTracker  │  Stable IDs via centroid matching (Hungarian-lite)
└──────┬───────┘
       │ list[(hand_id, landmarks)]
       ▼
┌───────────────────┐
│ GestureClassifier │  Rule-based (zero-shot) or MLP (trained)
└──────┬────────────┘
       │ (gesture_name, confidence)
       ▼
┌──────────────────────┐
│ Temporal Smoothing   │  Majority vote over sliding window
│ + Adaptive Threshold │  Per-gesture confidence tuning
└──────┬───────────────┘
       │ GestureEvent
       ├──────► SequenceDetector   → SequenceEvent (multi-gesture combos)
       ├──────► TrajectoryTracker  → TrajectoryEvent (spatial gestures via DTW)
       ├──────► BimanualDetector   → BimanualEvent (two-hand gestures)
       ├──────► DrawingCanvas      → DrawCommand (finger painting)
       ├──────► ActionMapper       → Execute keyboard/shell/webhook/OSC
       ├──────► PluginManager      → Dispatch to loaded plugins
       └──────► MetricsCollector   → Prometheus /metrics
                    │
                    ▼
            WebSocket Broadcast → Browser Demo / Any Client
```

## Pipeline Stages

### 1. Hand Detection (`detector.py`)

**Input:** RGB frame (H×W×3, uint8)
**Output:** List of landmark arrays, each shape (21, 3)

Uses MediaPipe Hands for real-time hand detection. Returns up to N hands (configurable, default 2). Provides both raw and wrist-normalized landmarks.

**Normalization:** Translates landmarks so wrist = origin, scales so max distance = 1.0. This makes features invariant to hand position and camera distance.

**Latency budget:** ~3-8ms on desktop, ~15-25ms on Raspberry Pi 4.

### 2. Hand Tracking (`pipeline.py → HandTracker`)

**Input:** List of landmark arrays + timestamp
**Output:** List of (hand_id, landmarks) with stable IDs

Greedy nearest-neighbor matching using centroid distance. Handles:
- Persistent IDs across frames (no ID flickering)
- Timeout-based track cleanup (500ms default)
- New track creation for unmatched detections

**Design decision:** Centroid-based matching is simpler than Hungarian algorithm but sufficient for ≤4 hands. The 0.3 normalized-unit threshold handles typical hand movement between frames.

### 3. Gesture Classification (`classifier.py`)

Two modes:

#### Rule-Based (Zero-Shot)
Each gesture is defined by finger extension states (extended/curled/any) plus optional geometric constraints (distances, angles between landmarks). The registry matches all definitions and returns the best match.

**Pros:** Works immediately, no training data needed, fully interpretable.
**Cons:** Limited to gestures expressible as finger states + geometry.

#### Learned (MLP)
81-feature vector extracted from landmarks:
- 63: Flattened normalized coordinates
- 10: Pairwise fingertip distances
- 5: Finger extension ratios
- 3: Palm normal vector

Architecture: Linear(81→128) → ReLU → Dropout(0.3) → Linear(128→64) → ReLU → Dropout(0.2) → Linear(64→N_classes)

**Latency:** <0.1ms per classification (CPU).

### 4. Temporal Smoothing (`pipeline.py`)

Majority-vote filter over a sliding window (default 5 frames). A gesture must be the majority classification to be emitted. Prevents jitter from single-frame misclassifications.

**Combined with adaptive thresholds:** Gestures that frequently get confused with others automatically get higher confidence thresholds. Thresholds drift slowly down for stable gestures.

### 5. Sequence Detection (`sequences.py`)

Finite state matching on gesture transition history. Sequences are defined as ordered lists of gestures with a max duration constraint.

Example: `["fist", "open_hand"]` within 1.5s → "release" event.

Per-hand history buffers ensure multi-hand sequences don't cross-contaminate.

### 6. Trajectory Tracking (`trajectory.py`)

Tracks hand centroid movement through 2D/3D space over time.

**Algorithm:**
1. Accumulate centroid positions in a rolling window (2s default)
2. When hand velocity drops below threshold → path complete
3. Resample path to 32 evenly-spaced points
4. Normalize to unit bounding box, centered at origin
5. Match against templates using Dynamic Time Warping (DTW)
6. DTW with Sakoe-Chiba band constraint for O(N×W) instead of O(N²)

**Built-in templates:** swipe_right, swipe_left, swipe_up, swipe_down, circle_cw, circle_ccw, z_pattern, wave.

Users can record custom templates at runtime.

### 7. Two-Hand Gestures (`bimanual.py`)

Requires exactly 2 hands. Automatically assigns left/right by x-coordinate.

**Detected gestures:**
- **pinch_zoom:** Inter-hand distance delta exceeds threshold → zoom factor
- **clap:** Rapid convergence to near-contact (velocity-based)
- **frame:** Both hands in L-shape (thumb + index extended), facing each other
- **conduct_up/down:** Synchronized vertical movement of both hands

### 8. Finger Painting (`canvas.py`)

Tracks index fingertip (landmark 8) to draw on a virtual canvas:
- **Drawing:** Index finger extended → line from previous position
- **Colors:** Different gestures map to colors (peace=green, rock_on=red, etc.)
- **Erase:** Fist gesture → circular eraser
- **Clear:** Open hand shake detection (direction change counting)

Canvas state is a command stream (line/erase/clear) that clients replay. New clients receive full state sync.

### 9. Action Mapping (`actions.py`)

Maps gesture/sequence names to actions via YAML configuration:
- **Keyboard:** xdotool key simulation
- **Shell:** Arbitrary commands with timeout
- **Webhook:** HTTP POST with gesture context
- **OSC:** Open Sound Control messages for DAW/VJ integration

Per-action cooldowns prevent spam.

### 10. Plugin System (`plugins.py`)

Auto-discovers .py files in the `plugins/` directory. Each file defines a `GesturePlugin` subclass or module-level `plugin` instance.

Plugins receive events via typed methods: `on_gesture`, `on_sequence`, `on_trajectory`, `on_bimanual`, `on_canvas`. Lifecycle hooks: `on_startup(context)`, `on_shutdown()`.

Decorator API for per-gesture handlers: `@plugin.handler("thumbs_up")`.

### 11. Metrics (`metrics.py`)

Prometheus-compatible `/metrics` endpoint. No external dependencies — generates text exposition format directly.

Tracked:
- `gesture_engine_gestures_total{gesture="..."}` — counter per gesture
- `gesture_engine_frame_latency_seconds` — histogram with ms-level buckets
- `gesture_engine_hand_detection_rate` — EMA gauge
- `gesture_engine_active_connections` — WebSocket connection gauge

## Data Flow

### Frame Processing (Hot Path)

```
Frame → detect(3-8ms) → track(0.1ms) → classify(0.1ms) → smooth(0.01ms)
     → sequence(0.01ms) → trajectory(0.05ms) → bimanual(0.02ms)
     → canvas(0.01ms) → broadcast(0.1ms)
```

**Total hot path:** 4-9ms on desktop, 16-30ms on RPi4.

### WebSocket Protocol

All messages are JSON. Server → Client:
- `{"type": "gesture", "gesture": "...", "confidence": 0.95, ...}`
- `{"type": "sequence", "sequence": "...", "gestures": [...], ...}`
- `{"type": "trajectory", "name": "...", "score": 0.8, ...}`
- `{"type": "bimanual", "gesture": "...", "value": 1.2, ...}`
- `{"type": "stats", "fps": 30, "latency_ms": 5.2, ...}`
- `{"type": "canvas_commands", "commands": [...]}`

Client → Server:
- `{"type": "ping"}` — keepalive
- `{"type": "get_heatmap"}` — request gesture frequency data
- `{"type": "clear"}` — clear canvas (canvas WS only)

## Deployment

### Edge (Raspberry Pi)
- MediaPipe Lite model
- ONNX or TFLite exported classifier
- INT8 quantization for ~2x speedup
- Docker with webcam passthrough

### Server
- FastAPI + Uvicorn
- Multiple WebSocket clients
- Prometheus scraping via `/metrics`

## Design Decisions

1. **MediaPipe over custom detection:** MediaPipe provides production-quality hand tracking with minimal integration effort. The value-add of GestureEngine is everything downstream.

2. **Rule-based default:** Zero-shot gesture definitions mean users get value immediately without collecting training data. The MLP is available for higher accuracy.

3. **DTW for trajectories:** DTW handles variable-speed execution naturally. Sakoe-Chiba band keeps it fast enough for real-time.

4. **No deep learning for trajectories:** Template matching with DTW is more interpretable, requires zero training data, and works with single examples.

5. **Command-based canvas:** Streaming draw commands instead of pixel buffers keeps bandwidth low and allows resolution-independent rendering on clients.

6. **Prometheus text format natively:** No dependency on prometheus_client. The text exposition format is simple enough to generate directly.

7. **Plugin auto-discovery:** Convention over configuration. Drop a file, it loads. No registration boilerplate.
