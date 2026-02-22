"""Spatial gesture recognition via 3D trajectory tracking and DTW matching.

Tracks hand centroid movement through space over time, then matches
trajectories against known templates using Dynamic Time Warping (DTW).
Ships with built-in swipe/circle/wave templates.

Usage:
    tracker = TrajectoryTracker()
    # In frame loop:
    events = tracker.update(hand_id=0, landmarks=lm, timestamp=now)
    for evt in events:
        print(f"Spatial gesture: {evt.name} (score={evt.score:.2f})")

    # Record custom template:
    tracker.start_recording("my_shape")
    # ... feed frames ...
    tracker.stop_recording()
"""

from __future__ import annotations

import math
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Optional

import numpy as np


@dataclass
class TrajectoryEvent:
    """Fired when a spatial trajectory matches a template."""
    name: str
    score: float  # 0–1, higher = better match
    hand_id: int
    duration: float
    path_length: float  # total distance traveled
    timestamp: float


@dataclass
class TrajectoryTemplate:
    """A named trajectory pattern for DTW matching."""
    name: str
    points: np.ndarray  # shape (N, 2) or (N, 3) — normalized path
    min_score: float = 0.65
    description: str = ""

    def normalized(self) -> np.ndarray:
        """Return path normalized to unit bounding box, centered at origin."""
        pts = self.points.copy().astype(np.float64)
        pts -= pts.mean(axis=0)
        span = pts.max(axis=0) - pts.min(axis=0)
        span = np.where(span < 1e-8, 1.0, span)
        return (pts / span).astype(np.float32)


def _dtw_distance(s: np.ndarray, t: np.ndarray) -> float:
    """Compute DTW distance between two sequences of points.

    Uses O(N*M) DP. Sequences are (N, D) and (M, D).
    Returns average per-step cost (lower = better match).
    """
    n, m = len(s), len(t)
    if n == 0 or m == 0:
        return float("inf")

    # Cost matrix
    cost = np.full((n + 1, m + 1), float("inf"), dtype=np.float64)
    cost[0, 0] = 0.0

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            d = float(np.linalg.norm(s[i - 1] - t[j - 1]))
            cost[i, j] = d + min(cost[i - 1, j], cost[i, j - 1], cost[i - 1, j - 1])

    return cost[n, m] / (n + m)


def _dtw_distance_fast(s: np.ndarray, t: np.ndarray, window: int = 10) -> float:
    """DTW with Sakoe-Chiba band constraint for speed."""
    n, m = len(s), len(t)
    if n == 0 or m == 0:
        return float("inf")

    cost = np.full((n + 1, m + 1), float("inf"), dtype=np.float64)
    cost[0, 0] = 0.0

    for i in range(1, n + 1):
        j_start = max(1, i - window)
        j_end = min(m, i + window)
        for j in range(j_start, j_end + 1):
            d = float(np.linalg.norm(s[i - 1] - t[j - 1]))
            cost[i, j] = d + min(cost[i - 1, j], cost[i, j - 1], cost[i - 1, j - 1])

    return cost[n, m] / (n + m)


def _resample_path(points: np.ndarray, n_points: int = 32) -> np.ndarray:
    """Resample a path to a fixed number of evenly-spaced points."""
    if len(points) < 2:
        return points

    # Compute cumulative arc length
    diffs = np.diff(points, axis=0)
    seg_lengths = np.linalg.norm(diffs, axis=1)
    cum_length = np.concatenate([[0], np.cumsum(seg_lengths)])
    total = cum_length[-1]

    if total < 1e-8:
        return np.tile(points[0], (n_points, 1))

    # Interpolate at evenly spaced arc lengths
    target_lengths = np.linspace(0, total, n_points)
    resampled = np.zeros((n_points, points.shape[1]), dtype=np.float32)

    for i, target in enumerate(target_lengths):
        idx = np.searchsorted(cum_length, target, side="right") - 1
        idx = min(idx, len(points) - 2)
        seg_remain = target - cum_length[idx]
        seg_len = seg_lengths[idx] if seg_lengths[idx] > 1e-8 else 1e-8
        t_param = seg_remain / seg_len
        resampled[i] = points[idx] + t_param * diffs[idx]

    return resampled


class TrajectoryTracker:
    """Tracks hand centroids over time and matches against trajectory templates.

    For each tracked hand, maintains a rolling window of centroid positions.
    When the hand stops moving (velocity drops below threshold), the accumulated
    path is matched against registered templates using DTW.
    """

    def __init__(
        self,
        window_seconds: float = 2.0,
        min_path_length: float = 0.08,
        velocity_threshold: float = 0.005,
        still_frames: int = 5,
        resample_points: int = 32,
        use_2d: bool = True,
    ):
        self.window_seconds = window_seconds
        self.min_path_length = min_path_length
        self.velocity_threshold = velocity_threshold
        self.still_frames = still_frames
        self.resample_points = resample_points
        self.use_2d = use_2d

        self._templates: list[TrajectoryTemplate] = []
        self._paths: dict[int, deque] = {}  # hand_id → deque of (time, centroid)
        self._still_counts: dict[int, int] = {}
        self._last_match_time: dict[int, float] = {}
        self._cooldown = 1.0

        # Recording state
        self._recording: Optional[str] = None
        self._recording_points: list[np.ndarray] = []

    def register_template(self, template: TrajectoryTemplate):
        """Add a trajectory template."""
        self._templates.append(template)

    def start_recording(self, name: str):
        """Begin recording a custom trajectory template."""
        self._recording = name
        self._recording_points = []

    def stop_recording(self, min_score: float = 0.65) -> Optional[TrajectoryTemplate]:
        """Stop recording and register the template. Returns the template or None."""
        if not self._recording or len(self._recording_points) < 5:
            self._recording = None
            return None

        pts = np.array(self._recording_points, dtype=np.float32)
        dim = 2 if self.use_2d else 3
        pts = pts[:, :dim]

        template = TrajectoryTemplate(
            name=self._recording,
            points=pts,
            min_score=min_score,
        )
        self._templates.append(template)
        self._recording = None
        self._recording_points = []
        return template

    def update(
        self, hand_id: int, landmarks: np.ndarray, timestamp: float
    ) -> list[TrajectoryEvent]:
        """Feed a new hand observation. Returns any matched trajectory events."""
        # Centroid = mean of all landmarks
        centroid = landmarks.mean(axis=0)
        dim = 2 if self.use_2d else 3
        point = centroid[:dim]

        # Recording mode
        if self._recording is not None:
            self._recording_points.append(point.copy())

        # Track path
        if hand_id not in self._paths:
            self._paths[hand_id] = deque()
            self._still_counts[hand_id] = 0

        path = self._paths[hand_id]

        # Prune old points
        while path and (timestamp - path[0][0]) > self.window_seconds:
            path.popleft()

        path.append((timestamp, point.copy()))

        # Check velocity
        if len(path) >= 2:
            dt = path[-1][0] - path[-2][0]
            if dt > 0:
                velocity = float(np.linalg.norm(path[-1][1] - path[-2][1])) / dt
            else:
                velocity = 0.0
        else:
            velocity = 0.0

        if velocity < self.velocity_threshold:
            self._still_counts[hand_id] = self._still_counts.get(hand_id, 0) + 1
        else:
            self._still_counts[hand_id] = 0

        # If hand has been still long enough, try to match the path
        events = []
        if self._still_counts.get(hand_id, 0) >= self.still_frames and len(path) > 10:
            # Cooldown check
            last = self._last_match_time.get(hand_id, 0)
            if timestamp - last > self._cooldown:
                events = self._match_path(hand_id, path, timestamp)
                if events:
                    self._last_match_time[hand_id] = timestamp
                    path.clear()

        return events

    def _match_path(
        self, hand_id: int, path: deque, timestamp: float
    ) -> list[TrajectoryEvent]:
        """Try to match accumulated path against templates."""
        if not self._templates:
            return []

        # Extract points
        times = [p[0] for p in path]
        points = np.array([p[1] for p in path], dtype=np.float32)

        # Check minimum path length
        total_length = float(np.sum(np.linalg.norm(np.diff(points, axis=0), axis=1)))
        if total_length < self.min_path_length:
            return []

        # Normalize and resample
        resampled = _resample_path(points, self.resample_points)
        resampled -= resampled.mean(axis=0)
        span = resampled.max(axis=0) - resampled.min(axis=0)
        span = np.where(span < 1e-8, 1.0, span)
        resampled /= span

        duration = times[-1] - times[0]

        events = []
        for template in self._templates:
            tmpl_pts = template.normalized()
            # Ensure same dimensionality
            dim = resampled.shape[1]
            tmpl_pts = tmpl_pts[:, :dim] if tmpl_pts.shape[1] >= dim else tmpl_pts

            tmpl_resampled = _resample_path(tmpl_pts, self.resample_points)

            dist = _dtw_distance_fast(resampled, tmpl_resampled)
            # Convert distance to score (0–1)
            score = max(0.0, 1.0 - dist * 2.0)

            if score >= template.min_score:
                events.append(TrajectoryEvent(
                    name=template.name,
                    score=score,
                    hand_id=hand_id,
                    duration=duration,
                    path_length=total_length,
                    timestamp=timestamp,
                ))

        # Return best match only
        if events:
            events.sort(key=lambda e: e.score, reverse=True)
            return [events[0]]
        return []

    def clear(self, hand_id: Optional[int] = None):
        """Clear tracking state."""
        if hand_id is not None:
            self._paths.pop(hand_id, None)
            self._still_counts.pop(hand_id, None)
        else:
            self._paths.clear()
            self._still_counts.clear()

    @property
    def templates(self) -> list[TrajectoryTemplate]:
        return list(self._templates)

    @classmethod
    def with_defaults(cls, **kwargs) -> TrajectoryTracker:
        """Create tracker with built-in swipe/circle/wave templates."""
        tracker = cls(**kwargs)

        # Swipe right: left-to-right horizontal line
        tracker.register_template(TrajectoryTemplate(
            name="swipe_right",
            points=np.array([[i / 20.0, 0.0] for i in range(21)], dtype=np.float32),
            min_score=0.60,
            description="Horizontal swipe from left to right",
        ))

        # Swipe left
        tracker.register_template(TrajectoryTemplate(
            name="swipe_left",
            points=np.array([[1.0 - i / 20.0, 0.0] for i in range(21)], dtype=np.float32),
            min_score=0.60,
            description="Horizontal swipe from right to left",
        ))

        # Swipe up
        tracker.register_template(TrajectoryTemplate(
            name="swipe_up",
            points=np.array([[0.0, 1.0 - i / 20.0] for i in range(21)], dtype=np.float32),
            min_score=0.60,
            description="Vertical swipe upward",
        ))

        # Swipe down
        tracker.register_template(TrajectoryTemplate(
            name="swipe_down",
            points=np.array([[0.0, i / 20.0] for i in range(21)], dtype=np.float32),
            min_score=0.60,
            description="Vertical swipe downward",
        ))

        # Circle (clockwise)
        angles = np.linspace(0, 2 * math.pi, 32, endpoint=False)
        circle_pts = np.column_stack([np.cos(angles), np.sin(angles)])
        tracker.register_template(TrajectoryTemplate(
            name="circle_cw",
            points=circle_pts.astype(np.float32),
            min_score=0.55,
            description="Clockwise circle",
        ))

        # Circle (counter-clockwise)
        tracker.register_template(TrajectoryTemplate(
            name="circle_ccw",
            points=circle_pts[::-1].copy().astype(np.float32),
            min_score=0.55,
            description="Counter-clockwise circle",
        ))

        # Z-pattern
        z_pts = np.array([
            [0, 0], [1, 0],  # top left to right
            [0, 1],           # diagonal down-left
            [1, 1],           # bottom right
        ], dtype=np.float32)
        tracker.register_template(TrajectoryTemplate(
            name="z_pattern",
            points=z_pts,
            min_score=0.55,
            description="Z-shaped pattern",
        ))

        # Wave (horizontal zigzag)
        wave_pts = []
        for i in range(5):
            wave_pts.append([i * 0.25, 0.0])
            wave_pts.append([i * 0.25 + 0.125, 0.3 if i % 2 == 0 else -0.3])
        wave_pts.append([1.0, 0.0])
        tracker.register_template(TrajectoryTemplate(
            name="wave",
            points=np.array(wave_pts, dtype=np.float32),
            min_score=0.50,
            description="Horizontal wave motion",
        ))

        return tracker
