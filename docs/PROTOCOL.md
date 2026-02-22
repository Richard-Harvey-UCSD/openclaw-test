# GestureEngine WebSocket Protocol

## Connection

Connect via WebSocket to `ws://<host>:<port>/ws` (default: `ws://localhost:8765/ws`).

### Handshake

After connection, the server sends a `connected` message:

```json
{
  "type": "connected",
  "gestures": ["open_hand", "fist", "thumbs_up", "peace", "pointing", "rock_on", "ok_sign"],
  "trajectories": ["swipe_right", "swipe_left", "swipe_up", "swipe_down", "circle_cw", "circle_ccw", "z_pattern", "wave"]
}
```

## Keep-Alive

The server sends `{"type": "ping"}` every 30 seconds of inactivity. Clients should respond with `{"type": "pong"}`.

Clients may also send `{"type": "ping"}` and will receive `{"type": "pong", "server_time": <unix_timestamp>}`.

## Event Messages (Server → Client)

### Gesture Event

```json
{
  "type": "gesture",
  "gesture": "thumbs_up",
  "confidence": 0.923,
  "hand_index": 0,
  "timestamp": 1708617600.123,
  "latency_ms": 3.2
}
```

| Field | Type | Description |
|-------|------|-------------|
| gesture | string | Gesture name |
| confidence | float | 0.0–1.0 |
| hand_index | int | 0 = first hand, 1 = second |
| timestamp | float | Unix timestamp |
| latency_ms | float | Server processing latency |

### Sequence Event

```json
{
  "type": "sequence",
  "sequence": "release",
  "gestures": ["fist", "open_hand"],
  "duration": 0.832,
  "timestamp": 1708617600.456
}
```

| Field | Type | Description |
|-------|------|-------------|
| sequence | string | Sequence name |
| gestures | string[] | Ordered gesture list |
| duration | float | Time span of the sequence (seconds) |

### Bimanual Event

```json
{
  "type": "bimanual",
  "gesture": "pinch_zoom",
  "value": 1.234,
  "confidence": 0.85,
  "timestamp": 1708617600.789
}
```

| Field | Type | Description |
|-------|------|-------------|
| gesture | string | "pinch_zoom", "clap", "frame", "conduct_up", "conduct_down" |
| value | float | Semantic value (zoom factor, velocity, width, etc.) |
| confidence | float | 0.0–1.0 |

### Trajectory Event

```json
{
  "type": "trajectory",
  "name": "swipe_right",
  "score": 0.782,
  "hand_id": 0,
  "duration": 0.654,
  "timestamp": 1708617601.012
}
```

| Field | Type | Description |
|-------|------|-------------|
| name | string | Trajectory template name |
| score | float | DTW match score, 0.0–1.0 |
| hand_id | int | Which hand performed the trajectory |
| duration | float | Duration of the movement (seconds) |

### Stats Event

```json
{
  "type": "stats",
  "fps": 28.5,
  "latency_ms": 4.1,
  "hands_detected": 2
}
```

Sent every 10 frames.

## Client → Server Messages

### Ping

```json
{"type": "ping"}
```

### Get Heatmap

```json
{"type": "get_heatmap"}
```

Response:
```json
{
  "type": "heatmap",
  "data": {"open_hand": 42, "fist": 17, "thumbs_up": 8}
}
```

## Canvas WebSocket

A separate endpoint at `ws://<host>:<port>/ws/canvas` streams drawing canvas events. On connection, the server sends a full canvas sync, then incremental draw commands.

## Error Handling

- If the server is unavailable, the WebSocket connection will fail. Clients should implement reconnection logic.
- Malformed client messages are silently ignored.
- Server errors during processing do not close the connection.

## REST API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/status` | GET | Server status, client count, FPS |
| `/api/gestures` | GET | List gesture definitions |
| `/api/trajectories` | GET | List trajectory templates |
| `/api/heatmap` | GET | Gesture frequency data |
| `/api/plugins` | GET | Loaded plugins |
| `/metrics` | GET | Prometheus metrics |
