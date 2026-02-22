# GestureEngine Unity SDK

Real-time hand gesture recognition for Unity. Connect to the GestureEngine Python server via WebSocket, or run gesture classification natively in C#.

## Installation

### Via Unity Package Manager (Git URL)

1. Open **Window → Package Manager**
2. Click **+** → **Add package from git URL**
3. Enter: `https://github.com/yourorg/gesture-engine.git?path=unity/com.gestureengine.sdk`

### Local Development

Clone the repo and add as a local package:
```
Window → Package Manager → + → Add package from disk → select package.json
```

## Quick Start

1. **Start the GestureEngine server:**
   ```bash
   pip install gesture-engine[all,cli]
   gesture-engine serve --port 8765
   ```

2. **Add GestureManager to your scene:**
   - Create an empty GameObject
   - Add `GestureEngine → GestureManager` component
   - Set Server URL to `ws://your-server:8765/ws`
   - Enable Auto Connect

3. **React to gestures (code):**
   ```csharp
   using GestureEngine;

   public class MyScript : MonoBehaviour
   {
       void Start()
       {
           GestureManager.Instance.OnGesture.AddListener(evt =>
           {
               Debug.Log($"Detected: {evt.gesture} ({evt.confidence:P0})");
           });

           GestureManager.Instance.RegisterGesture("thumbs_up", evt =>
           {
               Debug.Log("👍 Thumbs up!");
           });
       }
   }
   ```

4. **React to gestures (Inspector):**
   - Add a `GestureBinding` component to any GameObject
   - Add bindings: pick gesture name, set confidence threshold, wire up UnityEvents

## Native Classification (No Server)

For standalone builds without a Python server:

```csharp
using GestureEngine.NativeClassifier;

var classifier = new NativeGestureClassifier();

// Classify from 21 landmarks
if (classifier.Classify(landmarks, out string gesture, out float confidence))
{
    Debug.Log($"Native: {gesture} ({confidence:P0})");
}
```

Load custom gesture definitions (same JSON format as Python):
```csharp
classifier.LoadDefinitions(jsonString);
```

## Features

| Feature | Description |
|---------|-------------|
| WebSocket Client | Background thread, auto-reconnect, main-thread marshaling |
| GestureManager | Singleton, UnityEvents, per-gesture callbacks |
| GestureBinding | Inspector-driven gesture → action mapping with cooldowns |
| Hand Visualization | 21-landmark spheres + bone lines, Scene + Game view |
| Native Classifier | Pure C# rule-based classification, no server needed |
| Feature Extraction | 81-dim vector, compatible with Python ML pipeline |

## Supported Events

- **Gestures:** open_hand, fist, thumbs_up, peace, pointing, rock_on, ok_sign
- **Sequences:** release, grab, wave, peace_out, pinch_release, point_and_click
- **Trajectories:** swipe_left/right/up/down, circle_cw/ccw, z_pattern, wave
- **Bimanual:** pinch_zoom, clap, frame, conduct_up/down

## Requirements

- Unity 2020.3+
- .NET Standard 2.1 or .NET 4.x
- GestureEngine Python server (for WebSocket mode)

## Documentation

See [Documentation~/manual.md](Documentation~/manual.md) and [Protocol Documentation](../../docs/PROTOCOL.md).
