# GestureEngine Unity SDK — Manual

## Architecture

The SDK has two modes of operation:

### 1. Server Mode (WebSocket)
Your Unity app connects to a running GestureEngine Python server via WebSocket. The server handles camera capture, hand detection (MediaPipe), and gesture classification. Events are streamed to Unity in real-time as JSON messages.

**Best for:** Development, prototyping, multi-client setups, using server-side ML models.

### 2. Native Mode (C# Classifier)
The gesture classifier runs entirely within Unity using a pure C# port. You provide hand landmark data (e.g., from an XR hand tracking SDK) and get gesture classifications back.

**Best for:** Production builds, standalone apps, XR headsets, offline use.

## Components

### GestureManager
The main entry point. Singleton MonoBehaviour that persists across scenes.

**Inspector Fields:**
- **Config** — Optional GestureConfig ScriptableObject
- **Server URL** — WebSocket endpoint (default: `ws://localhost:8765/ws`)
- **Auto Connect** — Connect on Start()
- **Auto Reconnect** — Reconnect on disconnect
- **Minimum Confidence** — Global confidence filter
- **Gesture Cooldown** — Minimum seconds between same gesture events
- **Debug Visualization** — Show hand landmarks in 3D

**Events:**
- `OnGesture(GestureEvent)` — Single gesture recognized
- `OnSequence(GestureSequenceEvent)` — Gesture sequence completed
- `OnBimanual(BimanualEvent)` — Two-hand gesture detected
- `OnTrajectory(TrajectoryEvent)` — Spatial trajectory matched
- `OnHandUpdate(HandUpdateEvent)` — Raw hand landmark data
- `OnConnectedEvent` — WebSocket connected
- `OnDisconnectedEvent(string)` — WebSocket disconnected

**API:**
```csharp
GestureManager.Instance.Connect();
GestureManager.Instance.Disconnect();
bool connected = GestureManager.Instance.IsConnected;
GestureManager.Instance.RegisterGesture("thumbs_up", OnThumbsUp);
GestureManager.Instance.UnregisterGesture("thumbs_up", OnThumbsUp);
HandModel hand = GestureManager.Instance.GetHand(0);
```

### GestureBinding
Attach to any GameObject to map gestures to actions via the Inspector.

Each binding has:
- **Event Type** — Gesture, Sequence, Bimanual, or Trajectory
- **Gesture Name** — Which gesture to listen for (dropdown available)
- **Minimum Confidence** — Per-binding confidence threshold
- **Cooldown** — Minimum seconds between triggers
- **On Triggered** — UnityEvent fired when gesture matches
- **On Triggered With Confidence** — UnityEvent<float> with the confidence value

### GestureConfig
ScriptableObject for sharing configuration across scenes. Create via Assets → Create → GestureEngine → Config.

### GestureVisualizer
Renders hand landmarks as colored spheres connected by lines. Automatically added when Debug Visualization is enabled on GestureManager. Also draws Gizmos in Scene view.

### HandModel
Represents a single hand with 21 3D landmarks. Provides:
- Named landmark indices (Wrist, ThumbTip, IndexMCP, etc.)
- Bone connection map for rendering
- `IsFingerExtended(fingerIndex)` helper
- `Centroid` property

## Native Classifier

### NativeGestureClassifier
```csharp
var classifier = new NativeGestureClassifier(); // uses built-in 7 gestures

// Or load custom definitions
classifier.LoadDefinitions(File.ReadAllText("gestures.json"));

// Classify
if (classifier.Classify(landmarks, out string name, out float conf))
    Debug.Log($"{name}: {conf:P0}");

// Extract features for ML
float[] features = classifier.ExtractFeatures(landmarks); // 81-dim
```

### Cross-Platform Gesture Definitions
The JSON format is identical to the Python version:
```json
{
  "gestures": [
    {
      "name": "thumbs_up",
      "fingers": {
        "thumb": "extended",
        "index": "curled",
        "middle": "curled",
        "ring": "curled",
        "pinky": "curled"
      },
      "min_confidence": 0.6,
      "constraints": []
    }
  ]
}
```

## Thread Safety
The WebSocket client runs on a background thread. All events are marshaled to Unity's main thread via a `ConcurrentQueue` that is drained in `Update()`. You can safely access Unity APIs in all event callbacks.

## Performance Tips
- Set appropriate cooldowns to avoid event flooding
- Use confidence thresholds to filter noisy detections
- Disable Debug Visualization in production
- For XR: use Native Classifier mode to avoid network latency
