"""Tests for pipeline v2 features: hand tracking and adaptive thresholds."""

import numpy as np
import pytest

from gesture_engine.pipeline import HandTracker, AdaptiveThresholds


class TestHandTracker:
    def test_assign_new_ids(self):
        tracker = HandTracker()
        hands = [np.random.rand(21, 3).astype(np.float32)]
        result = tracker.update(hands, 0.0)
        assert len(result) == 1
        assert result[0][0] == 0  # first ID is 0

    def test_stable_tracking(self):
        tracker = HandTracker(max_distance=0.5)
        hand = np.random.rand(21, 3).astype(np.float32)

        r1 = tracker.update([hand], 0.0)
        id1 = r1[0][0]

        # Slightly shifted hand should keep same ID
        hand2 = hand + 0.01
        r2 = tracker.update([hand2], 0.1)
        id2 = r2[0][0]

        assert id1 == id2

    def test_new_id_for_distant_hand(self):
        tracker = HandTracker(max_distance=0.1)
        hand1 = np.zeros((21, 3), dtype=np.float32)
        hand2 = np.ones((21, 3), dtype=np.float32)

        r1 = tracker.update([hand1], 0.0)
        r2 = tracker.update([hand2], 0.1)

        assert r1[0][0] != r2[0][0]

    def test_timeout_removes_tracks(self):
        tracker = HandTracker(timeout=0.5)
        hand = np.random.rand(21, 3).astype(np.float32)

        tracker.update([hand], 0.0)
        assert tracker.active_count == 1

        tracker.update([], 1.0)  # past timeout
        assert tracker.active_count == 0

    def test_multi_hand(self):
        tracker = HandTracker()
        h1 = np.zeros((21, 3), dtype=np.float32)
        h2 = np.ones((21, 3), dtype=np.float32) * 0.5

        result = tracker.update([h1, h2], 0.0)
        assert len(result) == 2
        ids = {r[0] for r in result}
        assert len(ids) == 2  # unique IDs


class TestAdaptiveThresholds:
    def test_default_threshold(self):
        at = AdaptiveThresholds(base_threshold=0.6)
        assert at.get_threshold("unknown_gesture") == 0.6

    def test_threshold_increases_on_instability(self):
        at = AdaptiveThresholds(base_threshold=0.6, adjustment_rate=0.05)
        initial = at.get_threshold("peace")

        for _ in range(10):
            at.record("peace", 0.7, was_stable=False)

        assert at.get_threshold("peace") > initial

    def test_threshold_decreases_on_stability(self):
        at = AdaptiveThresholds(base_threshold=0.7, adjustment_rate=0.1)
        # First increase it
        for _ in range(10):
            at.record("fist", 0.8, was_stable=False)
        high = at.get_threshold("fist")

        # Now stabilize
        for _ in range(100):
            at.record("fist", 0.9, was_stable=True)

        assert at.get_threshold("fist") < high

    def test_threshold_bounds(self):
        at = AdaptiveThresholds(min_threshold=0.3, max_threshold=0.95, adjustment_rate=0.1)

        for _ in range(200):
            at.record("test", 0.5, was_stable=False)
        assert at.get_threshold("test") <= 0.95

        for _ in range(2000):
            at.record("test", 0.9, was_stable=True)
        assert at.get_threshold("test") >= 0.3
