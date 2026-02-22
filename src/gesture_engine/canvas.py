"""Finger painting / air drawing module.

Tracks index fingertip position to draw on a virtual canvas.
Gesture-based controls:
- Index finger extended → draw (default: white)
- Peace sign → draw in green
- Rock on → draw in red
- OK sign → draw in blue
- Fist → erase (large eraser circle)
- Open hand shake → clear canvas

Canvas state is streamable over WebSocket as compressed drawing commands.

Usage:
    canvas = DrawingCanvas(width=640, height=480)
    # In frame loop:
    commands = canvas.update(landmarks, gesture_name, timestamp)
    # Send commands to clients
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Optional

import numpy as np


@dataclass
class DrawCommand:
    """A single drawing command to send to clients."""
    type: str  # "line", "erase", "clear", "color"
    x: float = 0.0
    y: float = 0.0
    x2: float = 0.0
    y2: float = 0.0
    color: str = "#ffffff"
    width: float = 3.0
    radius: float = 20.0
    timestamp: float = 0.0

    def to_dict(self) -> dict:
        if self.type == "line":
            return {
                "type": "line",
                "x1": round(self.x, 1),
                "y1": round(self.y, 1),
                "x2": round(self.x2, 1),
                "y2": round(self.y2, 1),
                "color": self.color,
                "width": self.width,
            }
        elif self.type == "erase":
            return {
                "type": "erase",
                "x": round(self.x, 1),
                "y": round(self.y, 1),
                "radius": self.radius,
            }
        elif self.type == "clear":
            return {"type": "clear"}
        elif self.type == "color":
            return {"type": "color", "color": self.color}
        return {"type": self.type}


# Gesture → drawing color mapping
GESTURE_COLORS = {
    "pointing": "#ffffff",   # white (default draw)
    "peace": "#22c55e",      # green
    "rock_on": "#ef4444",    # red
    "ok_sign": "#3b82f6",    # blue
    "thumbs_up": "#eab308",  # yellow
}

# Gestures that trigger drawing
DRAW_GESTURES = set(GESTURE_COLORS.keys())


class DrawingCanvas:
    """Virtual canvas that tracks finger position and generates draw commands.

    The canvas maintains a command history that can be replayed for new clients.
    Coordinates are normalized to [0, 1] so clients can scale to any resolution.
    """

    def __init__(
        self,
        width: int = 640,
        height: int = 480,
        line_width: float = 3.0,
        erase_radius: float = 25.0,
        max_history: int = 10000,
        smoothing: int = 3,
    ):
        self.width = width
        self.height = height
        self.line_width = line_width
        self.erase_radius = erase_radius
        self.smoothing = smoothing

        self._history: list[DrawCommand] = []
        self._max_history = max_history
        self._current_color = "#ffffff"
        self._last_point: Optional[tuple[float, float]] = None
        self._drawing = False
        self._point_buffer: deque = deque(maxlen=smoothing)

        # Clear detection
        self._shake_positions: deque = deque(maxlen=15)
        self._shake_cooldown = 0.0

    def update(
        self,
        landmarks: np.ndarray,
        gesture: Optional[str],
        timestamp: Optional[float] = None,
    ) -> list[DrawCommand]:
        """Process a frame and return drawing commands.

        Args:
            landmarks: Normalized hand landmarks, shape (21, 3).
                       Uses raw (non-wrist-centered) for position tracking.
            gesture: Current classified gesture name, or None.
            timestamp: Current time.

        Returns:
            List of DrawCommand objects to send to clients.
        """
        now = timestamp or time.monotonic()
        commands: list[DrawCommand] = []

        # Index fingertip position (landmark 8), using x and y
        tip = landmarks[8]
        tip_x, tip_y = float(tip[0]), float(tip[1])

        if gesture == "fist":
            # Erase mode
            self._drawing = False
            self._last_point = None
            cmd = DrawCommand(
                type="erase", x=tip_x, y=tip_y,
                radius=self.erase_radius, timestamp=now,
            )
            commands.append(cmd)
            self._history.append(cmd)

        elif gesture == "open_hand":
            # Detect shake for clear
            self._shake_positions.append((tip_x, now))
            self._drawing = False
            self._last_point = None

            if self._detect_shake(now):
                cmd = DrawCommand(type="clear", timestamp=now)
                commands.append(cmd)
                self._history = [cmd]  # Reset history to just clear
                self._shake_positions.clear()
                self._shake_cooldown = now + 2.0

        elif gesture in DRAW_GESTURES:
            # Drawing mode
            new_color = GESTURE_COLORS.get(gesture, "#ffffff")
            if new_color != self._current_color:
                self._current_color = new_color
                commands.append(DrawCommand(type="color", color=new_color, timestamp=now))

            # Smooth the point
            self._point_buffer.append((tip_x, tip_y))
            if len(self._point_buffer) >= 2:
                smooth_x = sum(p[0] for p in self._point_buffer) / len(self._point_buffer)
                smooth_y = sum(p[1] for p in self._point_buffer) / len(self._point_buffer)
            else:
                smooth_x, smooth_y = tip_x, tip_y

            if self._last_point is not None:
                lx, ly = self._last_point
                # Only draw if moved enough (avoid dots from jitter)
                dist = ((smooth_x - lx) ** 2 + (smooth_y - ly) ** 2) ** 0.5
                if dist > 0.003:
                    cmd = DrawCommand(
                        type="line",
                        x=lx, y=ly,
                        x2=smooth_x, y2=smooth_y,
                        color=self._current_color,
                        width=self.line_width,
                        timestamp=now,
                    )
                    commands.append(cmd)
                    self._history.append(cmd)
                    self._last_point = (smooth_x, smooth_y)
            else:
                self._last_point = (smooth_x, smooth_y)

            self._drawing = True
        else:
            # No recognized drawing gesture — stop drawing
            self._drawing = False
            self._last_point = None
            self._point_buffer.clear()

        # Trim history
        if len(self._history) > self._max_history:
            # Keep a clear at the start + recent commands
            self._history = [DrawCommand(type="clear")] + self._history[-self._max_history // 2:]

        return commands

    def _detect_shake(self, now: float) -> bool:
        """Detect rapid horizontal shaking (open hand shake = clear)."""
        if now < self._shake_cooldown:
            return False
        if len(self._shake_positions) < 8:
            return False

        positions = list(self._shake_positions)
        # Count direction changes
        changes = 0
        for i in range(2, len(positions)):
            dx1 = positions[i - 1][0] - positions[i - 2][0]
            dx2 = positions[i][0] - positions[i - 1][0]
            if dx1 * dx2 < 0:  # direction changed
                changes += 1

        # Need several direction changes in short time
        time_span = positions[-1][1] - positions[0][1]
        if changes >= 4 and time_span < 1.5:
            return True
        return False

    def get_full_state(self) -> list[dict]:
        """Get complete drawing history for new client sync."""
        return [cmd.to_dict() for cmd in self._history]

    def clear(self):
        """Programmatically clear the canvas."""
        self._history = [DrawCommand(type="clear")]
        self._last_point = None
        self._point_buffer.clear()

    @property
    def command_count(self) -> int:
        return len(self._history)

    @property
    def is_drawing(self) -> bool:
        return self._drawing

    @property
    def current_color(self) -> str:
        return self._current_color
