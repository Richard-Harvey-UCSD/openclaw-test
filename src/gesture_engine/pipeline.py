"""Real-time gesture recognition pipeline with hand tracking and adaptive thresholds."""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Callable, Optional

import numpy as np

from gesture_engine.classifier import GestureClassifier
from gesture_engine.detector import HandDetector
from gesture_engine.gestures import GestureRegistry
from gesture_engine.profiler import PipelineProfiler


@dataclass
class GestureEvent:
    """A detected gesture event with metadata."""
    gesture: str
    confidence: float
    hand_index: int
    hand_id: int  # stable tracking ID across frames
    landmarks: np.ndarray
    timestamp: float


@dataclass
class PipelineStats:
    """Runtime performance statistics."""
    fps: float
    avg_latency_ms: float
    total_frames: int
    total_gestures: int
    active_hands: int = 0
    profiler_summary: dict = field(default_factory=dict)
    adaptive_thresholds: dict = field(default_factory=dict)


@dataclass
class TrackedHand:
    """A hand being tracked across frames."""
    hand_id: int
    landmarks: np.ndarray
    last_seen: float
    gesture_history: deque  # recent gestures for smoothing
    frames_tracked: int = 0


class HandTracker:
    """Tracks hands across frames using landmark distance matching.

    Assigns stable IDs to hands so multi-hand gestures work properly.
    Uses centroid distance for matching — simple but effective for ≤4 hands.
    """

    def __init__(self, max_distance: float = 0.3, timeout: float = 0.5):
        self._next_id = 0
        self._tracked: dict[int, TrackedHand] = {}
        self._max_distance = max_distance
        self._timeout = timeout

    def update(self, hands: list[np.ndarray], now: float) -> list[tuple[int, np.ndarray]]:
        """Match detected hands to tracked hands.

        Returns list of (hand_id, landmarks) with stable IDs.
        """
        # Prune stale tracks
        stale = [hid for hid, t in self._tracked.items() if now - t.last_seen > self._timeout]
        for hid in stale:
            del self._tracked[hid]

        if not hands:
            return []

        # Compute centroids for new detections
        new_centroids = [np.mean(h, axis=0) for h in hands]

        # Compute centroids for existing tracks
        tracked_ids = list(self._tracked.keys())
        tracked_centroids = [np.mean(self._tracked[hid].landmarks, axis=0) for hid in tracked_ids]

        # Greedy nearest-neighbor matching
        matched: list[tuple[int, np.ndarray]] = []
        used_tracks = set()
        used_detections = set()

        if tracked_centroids:
            # Build distance matrix
            for det_idx, det_c in enumerate(new_centroids):
                best_dist = float("inf")
                best_track = -1
                for trk_idx, trk_c in enumerate(tracked_centroids):
                    if trk_idx in used_tracks:
                        continue
                    dist = float(np.linalg.norm(det_c - trk_c))
                    if dist < best_dist:
                        best_dist = dist
                        best_track = trk_idx

                if best_track >= 0 and best_dist < self._max_distance:
                    hid = tracked_ids[best_track]
                    self._tracked[hid].landmarks = hands[det_idx]
                    self._tracked[hid].last_seen = now
                    self._tracked[hid].frames_tracked += 1
                    matched.append((hid, hands[det_idx]))
                    used_tracks.add(best_track)
                    used_detections.add(det_idx)

        # Create new tracks for unmatched detections
        for det_idx, lm in enumerate(hands):
            if det_idx not in used_detections:
                hid = self._next_id
                self._next_id += 1
                self._tracked[hid] = TrackedHand(
                    hand_id=hid,
                    landmarks=lm,
                    last_seen=now,
                    gesture_history=deque(maxlen=10),
                )
                matched.append((hid, lm))

        return matched

    @property
    def active_count(self) -> int:
        return len(self._tracked)

    def get_track(self, hand_id: int) -> Optional[TrackedHand]:
        return self._tracked.get(hand_id)


class AdaptiveThresholds:
    """Auto-adjusts per-gesture confidence thresholds based on confusion rates.

    Gestures that get frequently confused with others need higher thresholds.
    """

    def __init__(
        self,
        base_threshold: float = 0.6,
        min_threshold: float = 0.4,
        max_threshold: float = 0.95,
        window_size: int = 100,
        adjustment_rate: float = 0.01,
    ):
        self.base_threshold = base_threshold
        self.min_threshold = min_threshold
        self.max_threshold = max_threshold
        self._window_size = window_size
        self._adjustment_rate = adjustment_rate
        self._thresholds: dict[str, float] = {}
        self._history: dict[str, deque] = {}  # gesture → recent confidences
        self._confusion_counts: dict[str, int] = {}  # rapid switches

    def get_threshold(self, gesture: str) -> float:
        return self._thresholds.get(gesture, self.base_threshold)

    def record(self, gesture: str, confidence: float, was_stable: bool):
        """Record a classification result for threshold adaptation."""
        if gesture not in self._history:
            self._history[gesture] = deque(maxlen=self._window_size)
            self._thresholds[gesture] = self.base_threshold

        self._history[gesture].append(confidence)

        if not was_stable:
            # Gesture was overridden by smoothing → increase threshold
            self._confusion_counts[gesture] = self._confusion_counts.get(gesture, 0) + 1
            self._thresholds[gesture] = min(
                self.max_threshold,
                self._thresholds[gesture] + self._adjustment_rate,
            )
        else:
            # Stable detection → slowly decrease threshold
            self._thresholds[gesture] = max(
                self.min_threshold,
                self._thresholds[gesture] - self._adjustment_rate * 0.1,
            )

    @property
    def current_thresholds(self) -> dict[str, float]:
        return dict(self._thresholds)


class GesturePipeline:
    """End-to-end pipeline: frame → detection → classification → events.

    Features:
    - Temporal smoothing to reduce jitter
    - Hand tracking with stable IDs
    - Adaptive per-gesture confidence thresholds
    - Performance profiling of each stage
    - Cooldown to prevent gesture spamming
    - Callback system for gesture events
    """

    def __init__(
        self,
        detector: Optional[HandDetector] = None,
        classifier: Optional[GestureClassifier] = None,
        smoothing_window: int = 5,
        cooldown_seconds: float = 0.5,
        min_confidence: float = 0.6,
        enable_tracking: bool = True,
        enable_adaptive: bool = True,
        enable_profiling: bool = True,
    ):
        self.detector = detector or HandDetector()
        self.classifier = classifier or GestureClassifier()
        self.smoothing_window = smoothing_window
        self.cooldown_seconds = cooldown_seconds
        self.min_confidence = min_confidence

        self._callbacks: list[Callable[[GestureEvent], None]] = []
        self._history: dict[int, deque] = {}  # hand_id → recent gestures
        self._last_triggered: dict[int, tuple[str, float]] = {}
        self._frame_times: deque = deque(maxlen=60)
        self._total_frames = 0
        self._total_gestures = 0

        # New subsystems
        self._tracker = HandTracker() if enable_tracking else None
        self._adaptive = AdaptiveThresholds(base_threshold=min_confidence) if enable_adaptive else None
        self.profiler = PipelineProfiler() if enable_profiling else PipelineProfiler()
        self.profiler.enabled = enable_profiling

    def on_gesture(self, callback: Callable[[GestureEvent], None]):
        """Register a callback for gesture events."""
        self._callbacks.append(callback)

    def process_frame(self, frame_rgb: np.ndarray) -> list[GestureEvent]:
        """Process a single frame and return detected gesture events."""
        t_start = time.monotonic()
        self._total_frames += 1
        now = time.monotonic()

        # Detect hands
        with self.profiler.stage("detection"):
            hands = self.detector.detect_normalized(frame_rgb)

        # Track hands across frames
        if self._tracker:
            tracked = self._tracker.update(hands, now)
        else:
            tracked = [(i, lm) for i, lm in enumerate(hands)]

        events = []

        for hand_id, landmarks in tracked:
            # Classify
            with self.profiler.stage("classification"):
                result = self.classifier.classify(landmarks)

            if result is None:
                continue

            gesture_name, confidence = result

            # Adaptive threshold
            threshold = self.min_confidence
            if self._adaptive:
                threshold = self._adaptive.get_threshold(gesture_name)

            if confidence < threshold:
                continue

            # Temporal smoothing
            if hand_id not in self._history:
                self._history[hand_id] = deque(maxlen=self.smoothing_window)

            self._history[hand_id].append(gesture_name)
            smoothed = self._get_smoothed_gesture(hand_id)

            was_stable = smoothed == gesture_name
            if self._adaptive:
                self._adaptive.record(gesture_name, confidence, was_stable)

            if smoothed is None:
                continue

            # Cooldown check
            last = self._last_triggered.get(hand_id)
            if last and last[0] == smoothed and (now - last[1]) < self.cooldown_seconds:
                continue

            # Fire event
            event = GestureEvent(
                gesture=smoothed,
                confidence=confidence,
                hand_index=tracked.index((hand_id, landmarks)),
                hand_id=hand_id,
                landmarks=landmarks,
                timestamp=now,
            )

            self._last_triggered[hand_id] = (smoothed, now)
            self._total_gestures += 1
            events.append(event)

            for cb in self._callbacks:
                cb(event)

        t_end = time.monotonic()
        self._frame_times.append(t_end - t_start)

        with self.profiler.stage("total"):
            pass  # Just mark total frame time is tracked above

        return events

    def _get_smoothed_gesture(self, hand_id: int) -> Optional[str]:
        """Return the majority gesture in the smoothing window, or None."""
        history = self._history.get(hand_id)
        if not history or len(history) < max(1, self.smoothing_window // 2):
            return None

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
            active_hands=self._tracker.active_count if self._tracker else 0,
            profiler_summary=self.profiler.summary(),
            adaptive_thresholds=self._adaptive.current_thresholds if self._adaptive else {},
        )

    def reset(self):
        """Clear all state."""
        self._history.clear()
        self._last_triggered.clear()
        self._frame_times.clear()
        self._total_frames = 0
        self._total_gestures = 0
        self.profiler.reset()

    def close(self):
        """Release resources."""
        self.detector.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
