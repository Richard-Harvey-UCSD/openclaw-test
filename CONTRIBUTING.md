# Contributing to GestureEngine / CastGesture

## Project Structure

- `src/gesture_engine/` — Core Python gesture recognition engine
- `castgesture/` — CastGesture product (OBS overlay + Chrome extension)
- `unity/com.gestureengine.sdk/` — Unity SDK
- `tests/` — Core engine tests
- `castgesture/tests/` — CastGesture tests
- `examples/` — Demo scripts, benchmarks
- `docs/` — Architecture, API, protocol documentation

## Setup

```bash
cd /home/rick/openclaw-test
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Running Tests

```bash
# Core engine tests
pytest tests/ -v

# CastGesture tests
pytest castgesture/tests/ -v

# All tests
pytest tests/ castgesture/tests/ -v
```

## Code Style

- Python: ruff (configured in pyproject.toml), line length 88
- Type hints on all public functions
- Docstrings on all public classes and methods
- Guard optional imports (torch, mediapipe, fastapi) with try/except

## Key Design Decisions

1. **Landmark-based, not pixel-based** — classify hand geometry, not raw images
2. **Rule-based first, ML second** — rule-based works zero-shot, MLP for higher accuracy
3. **MediaPipe as current backbone** — planned replacement with custom model
4. **WebSocket for real-time** — gesture events streamed to any client
5. **Browser-first for CastGesture** — Chrome extension runs without Python server

## Adding a New Gesture

1. Add to `GestureRegistry.with_defaults()` in `src/gesture_engine/gestures.py`
2. Add tests in `tests/test_gestures.py`
3. Update `examples/gestures.json`
4. Update default mappings in `castgesture/config/default_mappings.yml`
5. Add effect mapping in `castgesture/server/effects.py` if needed

## Adding a New Effect (CastGesture)

1. Add effect class in `castgesture/server/effects.py`
2. Add JS renderer in `castgesture/overlay/index.html`
3. Add to Chrome extension in `castgesture/extension/effects.js`
4. Add default mapping in `castgesture/config/default_mappings.yml`
5. Add test button in `castgesture/panel/index.html`
