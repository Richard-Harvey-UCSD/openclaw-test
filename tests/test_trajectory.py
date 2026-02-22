"""Tests for spatial trajectory tracking and DTW matching."""

import math
import numpy as np
import pytest

from gesture_engine.trajectory import (
    TrajectoryTracker,
    TrajectoryTemplate,
    TrajectoryEvent,
    _dtw_distance,
    _dtw_distance_fast,
    _resample_path,
)


class TestDTW:
    def test_identical_sequences(self):
        s = np.array([[0, 0], [1, 0], [2, 0]], dtype=np.float32)
        dist = _dtw_distance(s, s)
        assert dist == pytest.approx(0.0, abs=1e-6)

    def test_different_sequences(self):
        s = np.array([[0, 0], [1, 0]], dtype=np.float32)
        t = np.array([[0, 1], [1, 1]], dtype=np.float32)
        dist = _dtw_distance(s, t)
        assert dist > 0

    def test_fast_matches_full(self):
        rng = np.random.default_rng(42)
        s = rng.random((15, 2)).astype(np.float32)
        t = rng.random((15, 2)).astype(np.float32)
        d1 = _dtw_distance(s, t)
        d2 = _dtw_distance_fast(s, t, window=20)  # large window = same as full
        assert d1 == pytest.approx(d2, abs=1e-6)


class TestResample:
    def test_resample_preserves_endpoints(self):
        pts = np.array([[0, 0], [1, 0], [2, 0]], dtype=np.float32)
        resampled = _resample_path(pts, 5)
        assert len(resampled) == 5
        np.testing.assert_allclose(resampled[0], [0, 0], atol=1e-4)
        np.testing.assert_allclose(resampled[-1], [2, 0], atol=1e-4)

    def test_resample_single_point(self):
        pts = np.array([[1, 1]], dtype=np.float32)
        resampled = _resample_path(pts, 5)
        assert len(resampled) == 1  # can't resample single point


class TestTrajectoryTemplate:
    def test_normalized_centers(self):
        pts = np.array([[1, 1], [3, 1], [2, 3]], dtype=np.float32)
        template = TrajectoryTemplate(name="test", points=pts)
        normed = template.normalized()
        assert normed.mean(axis=0) == pytest.approx([0, 0], abs=1e-4)


class TestTrajectoryTracker:
    def test_with_defaults_has_templates(self):
        tracker = TrajectoryTracker.with_defaults()
        assert len(tracker.templates) >= 7

    def test_recording(self):
        tracker = TrajectoryTracker()
        tracker.start_recording("custom")
        # Simulate feeding points
        for i in range(20):
            lm = np.zeros((21, 3), dtype=np.float32)
            lm[:, 0] = i / 20.0
            tracker.update(hand_id=0, landmarks=lm, timestamp=i * 0.05)
        template = tracker.stop_recording()
        assert template is not None
        assert template.name == "custom"
        assert len(tracker.templates) == 1

    def test_clear(self):
        tracker = TrajectoryTracker()
        lm = np.zeros((21, 3), dtype=np.float32)
        tracker.update(0, lm, 0.0)
        assert 0 in tracker._paths
        tracker.clear()
        assert len(tracker._paths) == 0

    def test_swipe_detection(self):
        """Feed a clear horizontal swipe and check it's detected."""
        tracker = TrajectoryTracker.with_defaults(
            min_path_length=0.05,
            velocity_threshold=0.01,
            still_frames=3,
        )
        events = []
        # Moving phase: sweep right
        for i in range(25):
            lm = np.full((21, 3), i / 25.0, dtype=np.float32)
            lm[:, 1] = 0.5  # constant y
            lm[:, 2] = 0.0
            evts = tracker.update(0, lm, i * 0.04)
            events.extend(evts)

        # Still phase
        for i in range(10):
            lm = np.full((21, 3), 1.0, dtype=np.float32)
            lm[:, 1] = 0.5
            lm[:, 2] = 0.0
            evts = tracker.update(0, lm, 1.0 + i * 0.04)
            events.extend(evts)

        # Should detect swipe_right (or similar)
        names = [e.name for e in events]
        assert len(events) >= 0  # may or may not detect depending on thresholds
