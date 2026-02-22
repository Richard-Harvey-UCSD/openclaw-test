"""Performance profiler for pipeline stages.

Instruments each stage of the gesture recognition pipeline with
high-resolution timing. Exposes statistics for monitoring and the web demo.
"""

from __future__ import annotations

import time
from collections import deque
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Iterator


@dataclass
class StageStats:
    """Timing statistics for a single pipeline stage."""
    name: str
    avg_ms: float
    min_ms: float
    max_ms: float
    p95_ms: float
    call_count: int


class PipelineProfiler:
    """Instruments pipeline stages with high-resolution timing.

    Usage:
        profiler = PipelineProfiler()

        with profiler.stage("detection"):
            hands = detector.detect(frame)

        with profiler.stage("classification"):
            result = classifier.classify(landmarks)

        print(profiler.summary())
    """

    STAGES = [
        "detection",
        "normalization",
        "feature_extraction",
        "classification",
        "sequence_detection",
        "action_dispatch",
        "total",
    ]

    def __init__(self, window_size: int = 120):
        self._window_size = window_size
        self._timings: dict[str, deque[float]] = {
            s: deque(maxlen=window_size) for s in self.STAGES
        }
        self._counts: dict[str, int] = {s: 0 for s in self.STAGES}
        self._enabled = True

    @contextmanager
    def stage(self, name: str) -> Iterator[None]:
        """Context manager to time a pipeline stage."""
        if not self._enabled:
            yield
            return

        if name not in self._timings:
            self._timings[name] = deque(maxlen=self._window_size)
            self._counts[name] = 0

        t0 = time.perf_counter()
        yield
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        self._timings[name].append(elapsed_ms)
        self._counts[name] += 1

    def get_stage_stats(self, name: str) -> StageStats | None:
        """Get stats for a specific stage."""
        timings = self._timings.get(name)
        if not timings:
            return None

        sorted_t = sorted(timings)
        n = len(sorted_t)
        return StageStats(
            name=name,
            avg_ms=sum(sorted_t) / n,
            min_ms=sorted_t[0],
            max_ms=sorted_t[-1],
            p95_ms=sorted_t[int(n * 0.95)] if n >= 2 else sorted_t[-1],
            call_count=self._counts.get(name, 0),
        )

    def summary(self) -> dict[str, dict]:
        """Get summary of all stages as a dict."""
        result = {}
        for name in self._timings:
            stats = self.get_stage_stats(name)
            if stats and stats.call_count > 0:
                result[name] = {
                    "avg_ms": round(stats.avg_ms, 3),
                    "min_ms": round(stats.min_ms, 3),
                    "max_ms": round(stats.max_ms, 3),
                    "p95_ms": round(stats.p95_ms, 3),
                    "calls": stats.call_count,
                }
        return result

    def reset(self):
        """Clear all timing data."""
        for d in self._timings.values():
            d.clear()
        for k in self._counts:
            self._counts[k] = 0

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool):
        self._enabled = value
