"""Prometheus-compatible metrics endpoint for GestureEngine.

Exposes /metrics in Prometheus text exposition format.
No external dependencies — generates the text format directly.

Tracked metrics:
- gesture_engine_gestures_total (counter, by gesture name)
- gesture_engine_sequences_total (counter, by sequence name)
- gesture_engine_trajectories_total (counter, by trajectory name)
- gesture_engine_bimanual_total (counter, by gesture name)
- gesture_engine_frame_latency_seconds (histogram)
- gesture_engine_hand_detection_rate (gauge)
- gesture_engine_active_connections (gauge)
- gesture_engine_frames_total (counter)
- gesture_engine_hands_detected_total (counter)
"""

from __future__ import annotations

import time
import threading
from collections import Counter
from typing import Optional


class _Histogram:
    """Simple histogram with configurable buckets."""

    def __init__(self, buckets: list[float]):
        self.buckets = sorted(buckets)
        self.bucket_counts = [0] * len(self.buckets)
        self.count = 0
        self.sum = 0.0
        self._lock = threading.Lock()

    def observe(self, value: float):
        with self._lock:
            self.count += 1
            self.sum += value
            for i, b in enumerate(self.buckets):
                if value <= b:
                    self.bucket_counts[i] += 1

    def render(self, name: str, help_text: str) -> str:
        lines = [
            f"# HELP {name} {help_text}",
            f"# TYPE {name} histogram",
        ]
        with self._lock:
            cumulative = 0
            for i, b in enumerate(self.buckets):
                cumulative += self.bucket_counts[i]
                lines.append(f'{name}_bucket{{le="{b}"}} {cumulative}')
            lines.append(f'{name}_bucket{{le="+Inf"}} {self.count}')
            lines.append(f"{name}_sum {self.sum:.6f}")
            lines.append(f"{name}_count {self.count}")
        return "\n".join(lines)


class MetricsCollector:
    """Collects and exposes Prometheus metrics for GestureEngine."""

    def __init__(self):
        self._gesture_counts: Counter = Counter()
        self._sequence_counts: Counter = Counter()
        self._trajectory_counts: Counter = Counter()
        self._bimanual_counts: Counter = Counter()
        self._frames_total = 0
        self._hands_total = 0
        self._active_connections = 0
        self._hand_detection_rate = 0.0
        self._lock = threading.Lock()

        # Latency histogram: buckets from 1ms to 100ms
        self._latency = _Histogram(
            [0.001, 0.002, 0.005, 0.010, 0.020, 0.033, 0.050, 0.100]
        )

        self._start_time = time.time()

    def record_gesture(self, name: str):
        with self._lock:
            self._gesture_counts[name] += 1

    def record_sequence(self, name: str):
        with self._lock:
            self._sequence_counts[name] += 1

    def record_trajectory(self, name: str):
        with self._lock:
            self._trajectory_counts[name] += 1

    def record_bimanual(self, name: str):
        with self._lock:
            self._bimanual_counts[name] += 1

    def record_frame(self, latency_seconds: float, hands_detected: int):
        with self._lock:
            self._frames_total += 1
            self._hands_total += hands_detected
        self._latency.observe(latency_seconds)

        # Update detection rate (exponential moving average)
        rate = 1.0 if hands_detected > 0 else 0.0
        self._hand_detection_rate = 0.95 * self._hand_detection_rate + 0.05 * rate

    def set_connections(self, count: int):
        self._active_connections = count

    def render(self) -> str:
        """Render all metrics in Prometheus text exposition format."""
        lines: list[str] = []

        # Uptime
        uptime = time.time() - self._start_time
        lines.append("# HELP gesture_engine_uptime_seconds Time since server start")
        lines.append("# TYPE gesture_engine_uptime_seconds gauge")
        lines.append(f"gesture_engine_uptime_seconds {uptime:.1f}")
        lines.append("")

        # Gesture counts
        lines.append("# HELP gesture_engine_gestures_total Total gesture detections by name")
        lines.append("# TYPE gesture_engine_gestures_total counter")
        with self._lock:
            for name, count in sorted(self._gesture_counts.items()):
                lines.append(f'gesture_engine_gestures_total{{gesture="{name}"}} {count}')
        lines.append("")

        # Sequence counts
        lines.append("# HELP gesture_engine_sequences_total Total sequence detections")
        lines.append("# TYPE gesture_engine_sequences_total counter")
        with self._lock:
            for name, count in sorted(self._sequence_counts.items()):
                lines.append(f'gesture_engine_sequences_total{{sequence="{name}"}} {count}')
        lines.append("")

        # Trajectory counts
        lines.append("# HELP gesture_engine_trajectories_total Total trajectory matches")
        lines.append("# TYPE gesture_engine_trajectories_total counter")
        with self._lock:
            for name, count in sorted(self._trajectory_counts.items()):
                lines.append(f'gesture_engine_trajectories_total{{trajectory="{name}"}} {count}')
        lines.append("")

        # Bimanual counts
        lines.append("# HELP gesture_engine_bimanual_total Total bimanual gesture detections")
        lines.append("# TYPE gesture_engine_bimanual_total counter")
        with self._lock:
            for name, count in sorted(self._bimanual_counts.items()):
                lines.append(f'gesture_engine_bimanual_total{{gesture="{name}"}} {count}')
        lines.append("")

        # Frame latency histogram
        lines.append(self._latency.render(
            "gesture_engine_frame_latency_seconds",
            "Frame processing latency in seconds"
        ))
        lines.append("")

        # Frames total
        lines.append("# HELP gesture_engine_frames_total Total frames processed")
        lines.append("# TYPE gesture_engine_frames_total counter")
        lines.append(f"gesture_engine_frames_total {self._frames_total}")
        lines.append("")

        # Hands detected
        lines.append("# HELP gesture_engine_hands_detected_total Total hands detected across all frames")
        lines.append("# TYPE gesture_engine_hands_detected_total counter")
        lines.append(f"gesture_engine_hands_detected_total {self._hands_total}")
        lines.append("")

        # Hand detection rate
        lines.append("# HELP gesture_engine_hand_detection_rate Exponential moving average of hand detection")
        lines.append("# TYPE gesture_engine_hand_detection_rate gauge")
        lines.append(f"gesture_engine_hand_detection_rate {self._hand_detection_rate:.4f}")
        lines.append("")

        # Active connections
        lines.append("# HELP gesture_engine_active_connections Current WebSocket connections")
        lines.append("# TYPE gesture_engine_active_connections gauge")
        lines.append(f"gesture_engine_active_connections {self._active_connections}")
        lines.append("")

        return "\n".join(lines) + "\n"

    @property
    def gesture_counts(self) -> dict[str, int]:
        with self._lock:
            return dict(self._gesture_counts)
