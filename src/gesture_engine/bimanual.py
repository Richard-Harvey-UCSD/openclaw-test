"""Two-hand gesture detection.

Detects gestures requiring both hands: pinch-to-zoom, clap, frame,
and conducting gestures. Tracks relative hand positions and movements.

Usage:
    detector = BimanualDetector()
    events = detector.update(hands=[(id0, lm0), (id1, lm1)], timestamp=now)
    for evt in events:
        print(f"{evt.gesture}: {evt.value:.2f}")
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Optional

import numpy as np


@dataclass
class BimanualEvent:
    """A two-hand gesture event."""
    gesture: str
    value: float  # semantic value (e.g., zoom factor, distance)
    confidence: float
    left_centroid: np.ndarray
    right_centroid: np.ndarray
    timestamp: float


@dataclass
class _HandState:
    """Internal tracking for a single hand in bimanual context."""
    centroid: np.ndarray
    landmarks: np.ndarray
    timestamp: float


class BimanualDetector:
    """Detects two-hand gestures from pairs of hand landmarks.

    Requires exactly two hands. Automatically determines left/right
    by x-coordinate (lower x = left hand in mirrored camera view).

    Supported gestures:
    - pinch_zoom: Hands moving apart (zoom in) or together (zoom out)
    - clap: Hands rapidly converging to near-contact
    - frame: Two L-shapes forming a rectangle (thumb + index on each hand)
    - conduct_up/conduct_down: Synchronized vertical hand movement
    """

    def __init__(
        self,
        history_size: int = 30,
        zoom_threshold: float = 0.03,
        clap_distance: float = 0.12,
        clap_velocity: float = 0.3,
        frame_tolerance: float = 0.15,
    ):
        self.history_size = history_size
        self.zoom_threshold = zoom_threshold
        self.clap_distance = clap_distance
        self.clap_velocity = clap_velocity
        self.frame_tolerance = frame_tolerance

        self._history: deque[tuple[_HandState, _HandState, float]] = deque(
            maxlen=history_size
        )
        self._last_distance: Optional[float] = None
        self._clap_cooldown = 0.0
        self._cooldowns: dict[str, float] = {}

    def update(
        self,
        hands: list[tuple[int, np.ndarray]],
        timestamp: Optional[float] = None,
    ) -> list[BimanualEvent]:
        """Feed hand observations. Expects exactly 2 hands.

        Args:
            hands: List of (hand_id, landmarks) tuples, landmarks shape (21, 3).
            timestamp: Current time (monotonic).

        Returns:
            List of detected bimanual events.
        """
        now = timestamp if timestamp is not None else time.monotonic()

        if len(hands) < 2:
            self._last_distance = None
            return []

        # Take first two hands, sort by x-centroid (left vs right)
        pair = sorted(hands[:2], key=lambda h: h[1].mean(axis=0)[0])
        left_lm, right_lm = pair[0][1], pair[1][1]
        left_c = left_lm.mean(axis=0)
        right_c = right_lm.mean(axis=0)

        left_state = _HandState(centroid=left_c, landmarks=left_lm, timestamp=now)
        right_state = _HandState(centroid=right_c, landmarks=right_lm, timestamp=now)
        self._history.append((left_state, right_state, now))

        events: list[BimanualEvent] = []

        # --- Pinch to zoom ---
        zoom_evt = self._detect_zoom(left_c, right_c, now)
        if zoom_evt:
            events.append(zoom_evt)

        # --- Clap ---
        clap_evt = self._detect_clap(left_c, right_c, now)
        if clap_evt:
            events.append(clap_evt)

        # --- Frame ---
        frame_evt = self._detect_frame(left_lm, right_lm, left_c, right_c, now)
        if frame_evt:
            events.append(frame_evt)

        # --- Conducting ---
        conduct_evt = self._detect_conducting(now)
        if conduct_evt:
            events.append(conduct_evt)

        return events

    def _check_cooldown(self, gesture: str, now: float, cooldown: float = 0.5) -> bool:
        """Returns True if gesture is NOT in cooldown."""
        last = self._cooldowns.get(gesture, 0.0)
        if now - last < cooldown:
            return False
        return True

    def _set_cooldown(self, gesture: str, now: float):
        self._cooldowns[gesture] = now

    def _detect_zoom(
        self, left_c: np.ndarray, right_c: np.ndarray, now: float
    ) -> Optional[BimanualEvent]:
        """Detect pinch-to-zoom by tracking inter-hand distance changes."""
        distance = float(np.linalg.norm(left_c[:2] - right_c[:2]))

        if self._last_distance is not None:
            delta = distance - self._last_distance
            if abs(delta) > self.zoom_threshold and self._check_cooldown("pinch_zoom", now, 0.1):
                zoom_factor = distance / max(self._last_distance, 1e-6)
                self._last_distance = distance
                return BimanualEvent(
                    gesture="pinch_zoom",
                    value=zoom_factor,
                    confidence=min(1.0, abs(delta) / 0.1),
                    left_centroid=left_c,
                    right_centroid=right_c,
                    timestamp=now,
                )

        self._last_distance = distance
        return None

    def _detect_clap(
        self, left_c: np.ndarray, right_c: np.ndarray, now: float
    ) -> Optional[BimanualEvent]:
        """Detect clap: hands rapidly converging to near-contact."""
        if not self._check_cooldown("clap", now, 1.0):
            return None

        distance = float(np.linalg.norm(left_c[:2] - right_c[:2]))
        if distance > self.clap_distance:
            return None

        # Check velocity of convergence
        if len(self._history) < 5:
            return None

        prev_left, prev_right, prev_t = self._history[-5]
        dt = now - prev_t
        if dt < 1e-6:
            return None

        prev_dist = float(np.linalg.norm(prev_left.centroid[:2] - prev_right.centroid[:2]))
        velocity = (prev_dist - distance) / dt

        if velocity > self.clap_velocity:
            self._set_cooldown("clap", now)
            return BimanualEvent(
                gesture="clap",
                value=velocity,
                confidence=min(1.0, velocity / 1.0),
                left_centroid=left_c,
                right_centroid=right_c,
                timestamp=now,
            )
        return None

    def _detect_frame(
        self,
        left_lm: np.ndarray,
        right_lm: np.ndarray,
        left_c: np.ndarray,
        right_c: np.ndarray,
        now: float,
    ) -> Optional[BimanualEvent]:
        """Detect frame gesture: two L-shapes forming a rectangle.

        Each hand should have thumb + index extended forming an L.
        The two Ls should face each other.
        """
        if not self._check_cooldown("frame", now, 1.0):
            return None

        def is_l_shape(lm: np.ndarray) -> bool:
            """Check if thumb and index are extended, others curled."""
            wrist = lm[0]
            # Thumb tip vs IP
            thumb_ext = np.linalg.norm(lm[4] - wrist) > np.linalg.norm(lm[3] - wrist)
            # Index tip vs PIP
            index_ext = np.linalg.norm(lm[8] - wrist) > np.linalg.norm(lm[6] - wrist)
            # Others curled
            middle_curled = np.linalg.norm(lm[12] - wrist) < np.linalg.norm(lm[10] - wrist)
            ring_curled = np.linalg.norm(lm[16] - wrist) < np.linalg.norm(lm[14] - wrist)

            return thumb_ext and index_ext and middle_curled and ring_curled

        if is_l_shape(left_lm) and is_l_shape(right_lm):
            # Check that thumbs point toward each other (y-axis roughly aligned)
            left_thumb_dir = left_lm[4] - left_lm[2]
            right_thumb_dir = right_lm[4] - right_lm[2]

            # Thumbs should point in roughly opposite x-directions
            if left_thumb_dir[0] * right_thumb_dir[0] < 0:
                self._set_cooldown("frame", now)
                width = float(np.linalg.norm(left_c[:2] - right_c[:2]))
                return BimanualEvent(
                    gesture="frame",
                    value=width,
                    confidence=0.85,
                    left_centroid=left_c,
                    right_centroid=right_c,
                    timestamp=now,
                )
        return None

    def _detect_conducting(self, now: float) -> Optional[BimanualEvent]:
        """Detect synchronized vertical hand movement (conducting)."""
        if not self._check_cooldown("conduct", now, 0.3):
            return None
        if len(self._history) < 8:
            return None

        # Get recent vertical velocities for both hands
        recent = list(self._history)[-8:]
        left_ys = [s[0].centroid[1] for s in recent]
        right_ys = [s[1].centroid[1] for s in recent]
        dt = recent[-1][2] - recent[0][2]
        if dt < 0.05:
            return None

        left_vel = (left_ys[-1] - left_ys[0]) / dt
        right_vel = (right_ys[-1] - right_ys[0]) / dt

        # Both hands moving in same vertical direction, significantly
        min_vel = 0.15
        if abs(left_vel) > min_vel and abs(right_vel) > min_vel:
            # Same direction check (correlation)
            if left_vel * right_vel > 0:
                direction = "conduct_down" if left_vel > 0 else "conduct_up"
                avg_vel = (abs(left_vel) + abs(right_vel)) / 2
                self._set_cooldown("conduct", now)
                left_c = recent[-1][0].centroid
                right_c = recent[-1][1].centroid
                return BimanualEvent(
                    gesture=direction,
                    value=avg_vel,
                    confidence=min(1.0, avg_vel / 0.5),
                    left_centroid=left_c,
                    right_centroid=right_c,
                    timestamp=now,
                )
        return None

    def reset(self):
        """Clear all state."""
        self._history.clear()
        self._last_distance = None
        self._cooldowns.clear()
