# Project Status

**Last Updated:** 2026-02-22
**Version:** 0.5.0
**Codebase:** ~15,300 lines across Python, C#, HTML/JS, YAML, Markdown
**Tests:** 214 test cases (167 core engine + 34 CastGesture + 13 skipped optional deps)

---

## Architecture Overview

```
openclaw-test/
├── src/gesture_engine/       # Core Python engine (v0.5.0)
├── castgesture/              # CastGesture product (OBS + Chrome extension)
│   ├── server/               # FastAPI WebSocket server
│   ├── overlay/              # OBS browser source overlay (effects)
│   ├── panel/                # Streamer control panel
│   ├── extension/            # Chrome extension (MV3)
│   ├── landing/              # Marketing landing page
│   ├── config/               # Default mappings
│   └── tests/                # CastGesture-specific tests
├── unity/com.gestureengine.sdk/  # Unity SDK (UPM package)
├── examples/                 # Demos, benchmarks, data collection
├── tests/                    # Core engine tests
├── docs/                     # Architecture, API, Protocol docs
└── plugins/                  # Plugin examples
```

## What's Built

### Core Engine (`src/gesture_engine/`)
- [x] Hand detection via MediaPipe with wrist-centered normalization
- [x] Rule-based gesture classifier (7 built-in gestures)
- [x] Trainable MLP classifier with 81-dim feature extraction
- [x] Real-time pipeline with temporal smoothing + cooldown
- [x] Gesture sequence detection (compound gestures)
- [x] 3D trajectory tracking with DTW matching
- [x] Two-hand (bimanual) gesture detection
- [x] Finger painting / air drawing canvas
- [x] Hand tracking persistence (stable IDs across frames)
- [x] Adaptive confidence thresholds
- [x] Per-stage pipeline profiler
- [x] Gesture-to-action mapping (keyboard, shell, webhook, OSC)
- [x] Full CLI (serve, train, record, replay, benchmark, define, export)
- [x] ONNX/TFLite export with INT8 quantization
- [x] Plugin system (auto-loading .py files)
- [x] Prometheus metrics endpoint
- [x] WebSocket streaming server
- [x] Recorder/replay system (JSON + NPZ)
- [x] Benchmark suite

### CastGesture Product (`castgesture/`)
- [x] OBS overlay with 7 visual effects (confetti, fire, emoji rain, shake, flash, text pop, spotlight)
- [x] Control panel for mapping gestures to effects
- [x] OBS WebSocket v5 integration (scene switching, source toggling)
- [x] Twitch IRC chat bot + channel point integration
- [x] Demo mode (auto-cycle + interactive buttons, no camera needed)
- [x] Chrome extension (MV3) — runs MediaPipe in-browser, no Python server needed
- [x] Landing page (professional marketing site)
- [x] Default gesture→effect mappings
- [x] 34 tests

### Unity SDK (`unity/com.gestureengine.sdk/`)
- [x] WebSocket client with auto-reconnect
- [x] GestureManager MonoBehaviour (singleton, UnityEvents)
- [x] Inspector-based gesture→action binding
- [x] 3D hand landmark visualization
- [x] Native C# classifier (no Python server needed for production)
- [x] Custom editor inspectors
- [x] 3 sample projects

### Infrastructure
- [x] GitHub Actions CI (Python 3.10, 3.11, 3.12)
- [x] Docker + docker-compose
- [x] Architecture docs, API docs, Protocol docs

---

## TODO — Next Steps (Priority Order)

### 🔴 Critical (Do These First)
1. **End-to-end integration test with real camera** — verify the full pipeline works on actual hardware (Pi, laptop, desktop)
2. **Record a demo video** — use demo mode to capture a polished screen recording showing all effects. This is what goes on Twitter/landing page
3. **Publish Python package to PyPI** — `pip install gesture-engine` needs to work
4. **Publish Chrome extension** — even as unlisted, get it in the Chrome Web Store

### 🟡 High Value
5. **Replace MediaPipe with custom hand model** — this is the real IP play. Train a lightweight model that's faster/smaller on edge. Start with distillation from MediaPipe's outputs
6. **Landing page deployment** — host on Vercel/Netlify/GitHub Pages, buy a domain (castgesture.com or similar)
7. **OBS plugin packaging** — create an installer (Windows .exe, Mac .dmg) so streamers don't need Python
8. **Twitch/YouTube streamer outreach** — identify 10-20 mid-tier streamers, DM them the extension
9. **Publish Unity SDK to OpenUPM** — discoverability for Unity devs

### 🟢 Nice to Have
10. **More effects** — animated stickers, background swap, face filters
11. **Sound effects library** — bundle royalty-free sounds
12. **Analytics dashboard** — track which gestures users use most
13. **Multi-language support** — i18n for landing page + extension
14. **Discord community** — set up a server for users/developers
15. **Blog post** — "How we built real-time gesture recognition for streamers"
16. **Electron desktop app** — standalone app wrapping the server + overlay

### 🔵 Research / Long-term
17. **Custom hand pose model** — train from scratch, benchmark against MediaPipe
18. **Paper** — publish results if custom model outperforms on edge devices
19. **Sign language module** — extend engine for ASL/BSL translation
20. **Mobile SDK** — iOS/Android native libraries

---

## Known Issues
- GitHub Actions CI workflow needs PAT with `workflow` scope to update
- Chrome extension uses self-contained gesture detection (no MediaPipe JS bundle included yet — needs to be bundled or loaded from CDN)
- Unity SDK not tested in actual Unity project yet
- No Windows/Mac packaging for CastGesture server

## Tech Stack
- **Python 3.10+** — core engine, server
- **MediaPipe** — hand landmark detection (to be replaced)
- **FastAPI + uvicorn** — WebSocket server
- **PyTorch** — MLP training
- **ONNX/TFLite** — model export
- **C#** — Unity SDK
- **Vanilla JS/CSS** — overlay, panel, landing page, extension
- **Docker** — containerized deployment

## Environment
- **Dev machine:** Raspberry Pi (arm64, Linux 6.12)
- **GitHub:** github.com/Richard-Harvey-UCSD/openclaw-test (public)
- **Python venv:** /home/rick/openclaw-test/.venv
