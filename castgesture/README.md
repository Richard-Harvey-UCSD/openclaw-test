# 🤚 CastGesture

**Gesture-powered streaming effects for OBS.** Trigger confetti, fire, emoji rain, and more — just by making hand gestures on your webcam.

[![Powered by GestureEngine](https://img.shields.io/badge/powered%20by-GestureEngine-a855f7)](https://github.com/yourorg/gesture-engine)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](../LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-green.svg)](https://python.org)

![CastGesture Demo](https://via.placeholder.com/800x400/0a0a12/a855f7?text=CastGesture+Demo+GIF)

---

## What is CastGesture?

CastGesture turns your webcam into a gesture-powered effects controller for live streaming. Open your hand → confetti explodes. Make a fist → screen shakes. Peace sign → emoji rain. No hotkeys, no stream deck, no controllers — just your hands.

**Built for:** Twitch streamers, YouTubers, content creators, anyone who streams with OBS.

**Powered by:** [GestureEngine](https://github.com/yourorg/gesture-engine) — real-time hand gesture recognition with sub-5ms latency.

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

## 🖥️ OBS Setup

1. **Start CastGesture** — `python run.py`
2. **Add Browser Source in OBS:**
   - URL: `http://localhost:7555/overlay/`
   - Width: 1920 (match your canvas)
   - Height: 1080
   - ✅ Check "Shutdown source when not visible"
   - ✅ Check "Refresh browser when scene becomes active"
3. **Position the overlay** — Make it fill your entire canvas (it's transparent, effects render on top of everything)

### OBS WebSocket Integration

CastGesture can control OBS directly via obs-websocket-plugin v5:

1. Install [obs-websocket](https://github.com/obsproject/obs-websocket) (included in OBS 28+)
2. Enable WebSocket server in OBS → Tools → WebSocket Server Settings
3. Enter the URL and password in CastGesture's control panel → OBS tab

---

## 💜 Twitch Integration

Let your viewers trigger effects too!

### Chat Commands

Viewers can type in chat:
```
!effect confetti
!effect fire
!gesture thumbs_up
```

### Setup

1. Go to **Control Panel → Twitch** tab
2. Enter your channel name and OAuth token
3. Get an OAuth token at [twitchtokengenerator.com](https://twitchtokengenerator.com)
4. Enable the bot and save

---

## 🎨 Custom Gestures & Effects

### Edit Mappings (YAML)

Edit `config/default_mappings.yml`:

```yaml
mappings:
  - gesture: open_hand
    effect: confetti
    params:
      intensity: 1.5
      particle_count: 200
      colors: ["#ff0000", "#00ff00", "#0000ff"]
    sound: pop
    cooldown: 1.0
```

### Create Sequences

```yaml
sequences:
  - gestures: [fist, open_hand]
    effect: confetti
    params:
      intensity: 2.0
      particle_count: 300
    timeout: 1.0
```

### Visual Editor

Use the **Control Panel** at `http://localhost:7555/panel/` to edit mappings visually with live preview.

---

## 🔊 Custom Sounds

Drop `.mp3` files in `config/sounds/` and reference them by name:

```yaml
- gesture: thumbs_up
  effect: text_pop
  sound: airhorn  # → config/sounds/airhorn.mp3
```

Built-in sounds: `pop`, `whoosh`, `explosion`, `ding`, `applause`, `tada`

---

## 🏗️ Architecture

```
castgesture/
├── server/          # FastAPI + WebSocket server
│   ├── app.py       # Main server, REST API, WebSocket
│   ├── effects.py   # Effect definitions & defaults
│   ├── sounds.py    # Sound effect management
│   ├── mappings.py  # Gesture-to-effect mapping engine
│   ├── obs_integration.py    # OBS WebSocket control
│   └── twitch_integration.py # Twitch chat bot
├── overlay/         # OBS Browser Source overlay
│   └── index.html   # Canvas effects + WebSocket client
├── panel/           # Streamer control panel
│   └── index.html   # Configuration UI
├── landing/         # Marketing landing page
│   └── index.html
├── config/          # Configuration files
│   ├── default_mappings.yml
│   └── sounds/      # Custom sound effects
├── run.py           # One-command launcher
└── requirements.txt
```

---

## 🤝 Contributing

CastGesture is part of the [GestureEngine](https://github.com/yourorg/gesture-engine) project. PRs welcome!

- 🐛 [Report bugs](https://github.com/yourorg/gesture-engine/issues)
- 💡 [Request features](https://github.com/yourorg/gesture-engine/issues)
- 🎨 [Submit new effects](https://github.com/yourorg/gesture-engine/pulls)

---

## License

MIT — Use it, fork it, stream with it.
