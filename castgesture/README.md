# 🤚 CastGesture

**Gesture-powered streaming effects for OBS.** Trigger confetti, fire, emoji rain, and more — just by making hand gestures on your webcam.

[![Powered by GestureEngine](https://img.shields.io/badge/powered%20by-GestureEngine-a855f7)](https://github.com/yourorg/gesture-engine)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](../LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-green.svg)](https://python.org)

---

## What is CastGesture?

CastGesture turns your webcam into a gesture-powered effects controller for live streaming. Open your hand → confetti explodes. Make a fist → screen shakes. Peace sign → emoji rain. No hotkeys, no stream deck, no controllers — just your hands.

**Two ways to use it:**
1. **OBS Plugin** — Python server + overlay browser source (full control, Twitch integration, OBS control)
2. **Chrome Extension** — Zero-install gesture effects on Google Meet, Zoom, and Teams

---

## ⚡ Quick Start

```bash
# Clone the repo
git clone https://github.com/yourorg/gesture-engine.git
cd gesture-engine/castgesture

# Install dependencies
pip install -r requirements.txt

# Launch CastGesture
python run.py
```

The control panel opens automatically at `http://localhost:7555/panel/`.

---

## 🎭 Demo Mode (No Camera Needed!)

Demo mode lets you try all effects without a webcam. Perfect for:
- Recording demo videos
- Testing effects
- Trade show displays
- Trying CastGesture before setting up a camera

### Auto Demo
Cycles through all effects every 3 seconds:
```bash
# Server-side demo (broadcasts events to overlay)
python -m castgesture.server.demo

# Or just open the overlay directly:
# http://localhost:7555/overlay/?demo=auto
```

### Interactive Demo
On-screen buttons to trigger each effect manually:
```bash
python -m castgesture.server.demo --interactive

# Or open directly:
# http://localhost:7555/overlay/?demo=interactive
```

### Custom Timeline
Create a JSON timeline for scripted demos:
```bash
python -m castgesture.server.demo --timeline my_timeline.json
```

Timeline format:
```json
[
  {"t": 0.0, "gesture": "open_hand", "x": 0.5, "y": 0.4},
  {"t": 3.0, "gesture": "fist"},
  {"t": 6.0, "gesture": "peace", "x": 0.3, "y": 0.7}
]
```

---

## 🎬 Supported Effects

| Gesture | Effect | Description |
|---------|--------|-------------|
| 🖐️ Open Hand | 🎉 Confetti | Particle explosion from hand position |
| ✊ Fist | 📳 Screen Shake | Intense screen shake animation |
| ✌️ Peace | 🌧️ Emoji Rain | Selected emoji falling from the top |
| 👍 Thumbs Up | 💬 Text Pop | "NICE!" text appears and fades |
| 👆 Pointing | 🔦 Spotlight | Circular spotlight follows your hand |
| 🤟 Rock On | 🔥 Fire | Flame effect at bottom of screen |
| 👌 OK Sign | ⚡ Flash | Bright flash then fade |

### Gesture Sequences (Combos!)

| Sequence | Effect |
|----------|--------|
| ✊ Fist → 🖐️ Open Hand | 💥 Big confetti explosion (2x particles!) |
| ✌️ Peace → ✊ Fist | 🫳 Screen grab effect |

---

## 🌐 Chrome Extension (Zero Install!)

Use CastGesture effects directly in video calls — no Python server needed.

### Installation (Developer Mode)

1. Open Chrome and go to `chrome://extensions/`
2. Enable **Developer mode** (toggle in top-right)
3. Click **Load unpacked**
4. Select the `castgesture/extension/` folder
5. The CastGesture icon appears in your toolbar

### Supported Platforms
- **Google Meet** — `meet.google.com`
- **Zoom** — `zoom.us` (web client)
- **Microsoft Teams** — `teams.microsoft.com`

### How It Works
1. Join a video call on any supported platform
2. Click the CastGesture extension icon
3. Toggle effects on/off
4. Configure gesture→effect mappings in the popup
5. Make gestures on camera — effects appear as overlays!

### Extension Architecture
The extension runs entirely in the browser:
- Content script detects your self-view video element
- Gesture classification runs client-side (no server needed)
- Effects render as DOM overlays on top of the video call page
- Settings sync via `chrome.storage`

---

## 🖥️ OBS Setup

1. **Start CastGesture** — `python run.py`
2. **Add Browser Source in OBS:**
   - URL: `http://localhost:7555/overlay/`
   - Width: 1920 (match your canvas)
   - Height: 1080
   - ✅ Check "Shutdown source when not visible"
   - ✅ Check "Refresh browser when scene becomes active"
3. **Position the overlay** — Make it fill your entire canvas (it's transparent)

### OBS WebSocket Integration

CastGesture can control OBS directly via obs-websocket-plugin v5:

1. Install [obs-websocket](https://github.com/obsproject/obs-websocket) (included in OBS 28+)
2. Enable WebSocket server in OBS → Tools → WebSocket Server Settings
3. Enter the URL and password in CastGesture's control panel → OBS tab

---

## 💜 Twitch Integration

Let your viewers trigger effects too!

### Chat Commands
```
!effect confetti
!effect fire
!gesture thumbs_up
```

### Setup
1. Go to **Control Panel → Twitch** tab
2. Enter your channel name and OAuth token
3. Get a token at [twitchtokengenerator.com](https://twitchtokengenerator.com)

---

## 🎨 Custom Mappings

Edit `config/default_mappings.yml`:
```yaml
mappings:
  - gesture: open_hand
    effect: confetti
    params:
      intensity: 1.5
      particle_count: 200
    sound: pop
    cooldown: 1.0

sequences:
  - gestures: [fist, open_hand]
    effect: confetti
    params:
      intensity: 2.0
    timeout: 1.0
```

Or use the visual editor at `http://localhost:7555/panel/`.

---

## 🔊 Custom Sounds

Drop `.mp3` files in `config/sounds/` and reference by name:
```yaml
- gesture: thumbs_up
  sound: airhorn  # → config/sounds/airhorn.mp3
```

Built-in: `pop`, `whoosh`, `explosion`, `ding`, `applause`, `tada`

---

## 🏗️ Architecture

```
castgesture/
├── server/                  # FastAPI + WebSocket server
│   ├── app.py               # Main server, REST API, WebSocket
│   ├── demo.py              # Demo mode (no camera needed)
│   ├── effects.py           # Effect definitions & defaults
│   ├── sounds.py            # Sound effect management
│   ├── mappings.py          # Gesture→effect mapping engine
│   ├── config.py            # Configuration management
│   ├── obs_integration.py   # OBS WebSocket control
│   └── twitch_integration.py # Twitch chat bot
├── overlay/                 # OBS Browser Source overlay
│   └── index.html           # Canvas effects + WebSocket client
│                            #   ?demo=auto — auto cycle effects
│                            #   ?demo=interactive — clickable buttons
├── panel/                   # Streamer control panel
│   └── index.html           # Configuration UI
├── landing/                 # Marketing landing page
│   └── index.html
├── extension/               # Chrome Extension (zero-install!)
│   ├── manifest.json        # Chrome MV3 manifest
│   ├── background.js        # Service worker
│   ├── content.js           # Video detection + gesture classification
│   ├── effects.js           # DOM-based effect renderer
│   ├── popup.html/js        # Extension popup UI
│   ├── styles.css           # Injected overlay styles
│   └── icons/               # Extension icons
├── tests/                   # Test suite
│   ├── test_effects.py      # Effect registry tests
│   ├── test_mappings.py     # Mapping engine tests
│   └── test_server.py       # REST API endpoint tests
├── config/
│   ├── default_mappings.yml # Gesture→effect config
│   └── sounds/              # Custom sound effects
├── run.py                   # One-command launcher
└── requirements.txt

Data Flow (OBS path):
  Webcam → GestureEngine → MappingEngine → WebSocket → Overlay (OBS Browser Source)
                                         → OBS WebSocket (scene switching)
                                         → Twitch Chat (viewer triggers)

Data Flow (Extension path):
  Video Call → Content Script → Gesture Classifier → DOM Effects Overlay
  (all in-browser, no server needed)
```

---

## 🧪 Running Tests

```bash
pip install pytest httpx
python -m pytest castgesture/tests/ -v
```

---

## 🤝 Contributing

CastGesture is part of the [GestureEngine](https://github.com/yourorg/gesture-engine) project. PRs welcome!

---

## License

MIT — Use it, fork it, stream with it.
