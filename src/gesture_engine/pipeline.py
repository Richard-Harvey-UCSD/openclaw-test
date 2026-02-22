"""Real-time gesture recognition pipeline."""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np

from gesture_engine.classifier import GestureClassifier
from gesture_engine.detector import HandDetector
from gesture_engine.gestures import GestureRegistry


@dataclass
class GestureEvent:
    """A detected gesture event with metadata."""
    gesture: str
    confidence: float
    hand_index: int
    landmarks: np.ndarray
    timestamp: float


@dataclass
class PipelineStats:
    """Runtime performance statistics."""
    fps: float
    avg_latency_ms: float
    total_frames: int
    total_gestures: int


class GesturePipeline:
    """End-to-end pipeline: frame → detection → classification → events.

    Features:
    - Temporal smoothing to reduce jitter (configurable window)
    - Cooldown to prevent gesture spamming
    - Callback system for gesture events
    - Performance monitoring
    """

    def __init__(
        self,
        detector: Optional[HandDetector] = None,
        classifier: Optional[GestureClassifier] = None,
        smoothing_window: int = 5,
        cooldown_seconds: float = 0.5,
        min_confidence: float = 0.6,
    ):
        self.detector = detector or HandDetector()
        self.classifier = classifier or GestureClassifier()
        self.smoothing_window = smoothing_window
        self.cooldown_seconds = cooldown_seconds
        self.min_confidence = min_confidence

        self._callbacks: list[Callable[[GestureEvent], None]] = []
        self._history: dict[int, deque] = {}  # hand_index → recent gestures
        self._last_triggered: dict[int, tuple[str, float]] = {}  # cooldown tracking
        self._frame_times: deque = deque(maxlen=60)
        self._total_frames = 0
        self._total_gestures = 0

    def on_gesture(self, callback: Callable[[GestureEvent], None]):
        """Register a callback for gesture events."""
        self._callbacks.append(callback)

    def process_frame(self, frame_rgb: np.ndarray) -> list[GestureEvent]:
        """Process a single frame and return detected gesture events.

        Args:
            frame_rgb: RGB image, shape (H, W, 3), uint8.

        Returns:
            List of gesture events (may be empty).
        """
        t_start = time.monotonic()
        self._total_frames += 1

        # Detect hands
        hands = self.detector.detect_normalized(frame_rgb)

        events = []

        for hand_idx, landmarks in enumerate(hands):
            # Classify
            result = self.classifier.classify(landmarks)
            if result is None:
                continue

            gesture_name, confidence = result

            if confidence < self.min_confidence:
                continue

            # Temporal smoothing
            if hand_idx not in self._history:
                self._history[hand_idx] = deque(maxlen=self.smoothing_window)

            self._history[hand_idx].append(gesture_name)

            # Check if gesture is stable (majority in window)
            smoothed = self._get_smoothed_gesture(hand_idx)
            if smoothed is None:
                continue

            # Cooldown check
            now = time.monotonic()
            last = self._last_triggered.get(hand_idx)
            if last and last[0] == smoothed and (now - last[1]) < self.cooldown_seconds:
                continue

            # Fire event
            event = GestureEvent(
                gesture=smoothed,
                confidence=confidence,
                hand_index=hand_idx,
                landmarks=landmarks,
                timestamp=now,
            )

            self._last_triggered[hand_idx] = (smoothed, now)
            self._total_gestures += 1
            events.append(event)

            for cb in self._callbacks:
                cb(event)

        t_end = time.monotonic()
        self._frame_times.append(t_end - t_start)

        return events

    def _get_smoothed_gesture(self, hand_idx: int) -> Optional[str]:
        """Return the majority gesture in the smoothing window, or None."""
        history = self._history.get(hand_idx)
        if not history or len(history) < max(1, self.smoothing_window // 2):
            return None

        # Simple majority vote
        counts: dict[str, int] = {}
        for g in history:
            counts[g] = counts.get(g, 0) + 1

        best = max(counts, key=counts.get)  # type: ignore
        if counts[best] > len(history) // 2:
            return best
        return None

    @property
    def stats(self) -> PipelineStats:
        """Get current performance statistics."""
        if self._frame_times:
            avg_latency = sum(self._frame_times) / len(self._frame_times)
            fps = 1.0 / avg_latency if avg_latency > 0 else 0
        else:
            avg_latency = 0
            fps = 0

        return PipelineStats(
            fps=fps,
            avg_latency_ms=avg_latency * 1000,
            total_frames=self._total_frames,
            total_gestures=self._total_gestures,
        )

    def reset(self):
        """Clear all state (history, cooldowns, stats)."""
        self._history.clear()
        self._last_triggered.clear()
        self._frame_times.clear()
        self._total_frames = 0
        self._total_gestures = 0

    def close(self):
        """Release resources."""
        self.detector.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
