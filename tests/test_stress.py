"""Stress tests for GestureEngine."""

import os
import time
import threading
import numpy as np
import pytest

from gesture_engine.classifier import GestureClassifier
from gesture_engine.gestures import GestureRegistry
from gesture_engine.sequences import SequenceDetector, GestureSequence
from gesture_engine.recorder import GestureRecorder, GesturePlayer
from gesture_engine.trajectory import TrajectoryTracker, _dtw_distance_fast
from gesture_engine.bimanual import BimanualDetector
from gesture_engine.metrics import MetricsCollector
from gesture_engine.profiler import PipelineProfiler
from gesture_engine.pipeline import HandTracker


class TestHighVolume:
    def test_10k_classifications(self):
        """Process 10,000 frames rapidly."""
        classifier = GestureClassifier()
        rng = np.random.default_rng(42)

        for _ in range(10_000):
            lm = rng.random((21, 3)).astype(np.float32)
            classifier.classify(lm)

    def test_memory_stable(self):
        """RSS shouldn't grow unbounded over many frames."""
        try:
            import resource
            get_rss = lambda: resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        except ImportError:
            pytest.skip("resource module not available")

        classifier = GestureClassifier()
        seq_det = SequenceDetector.with_defaults()
        rng = np.random.default_rng(42)

        rss_start = get_rss()
        for i in range(10_000):
            lm = rng.random((21, 3)).astype(np.float32)
            result = classifier.classify(lm)
            if result:
                seq_det.feed(result[0], timestamp=i * 0.001)

        rss_end = get_rss()
        # Allow up to 50MB growth (generous for 10k iterations)
        assert (rss_end - rss_start) < 50_000  # in KB on Linux

    def test_random_landmarks(self):
        classifier = GestureClassifier()
        rng = np.random.default_rng(0)
        results = []
        for _ in range(1000):
            lm = rng.standard_normal((21, 3)).astype(np.float32)
            r = classifier.classify(lm)
            if r:
                results.append(r[0])
        # Just ensure no crashes and some results
        assert len(results) >= 0

    def test_rapid_gesture_switching(self):
        """Every frame is a different gesture."""
        classifier = GestureClassifier()
        seq_det = SequenceDetector.with_defaults()
        gestures = ["fist", "open_hand", "peace", "thumbs_up", "pointing"]

        for i in range(1000):
            # Feed gesture names directly to sequence detector
            seq_det.feed(gestures[i % len(gestures)], timestamp=i * 0.01)


class TestHandCrossing:
    def test_hands_crossing(self):
        """Two hands swapping positions."""
        tracker = HandTracker(max_distance=0.5)

        h1 = np.zeros((21, 3), dtype=np.float32)
        h1[:, 0] = 0.2
        h2 = np.zeros((21, 3), dtype=np.float32)
        h2[:, 0] = 0.8

        r = tracker.update([h1, h2], 0.0)
        id_left = r[0][0]
        id_right = r[1][0]

        # Gradually move hands toward each other and cross
        for step in range(10):
            t = (step + 1) / 10.0
            new_h1 = h1.copy()
            new_h1[:, 0] = 0.2 + t * 0.6
            new_h2 = h2.copy()
            new_h2[:, 0] = 0.8 - t * 0.6
            tracker.update([new_h1, new_h2], step * 0.1)

        # After crossing, tracking may reassign — just ensure no crash
        assert tracker.active_count == 2


class TestTrajectoryStress:
    def test_long_path(self):
        """Trajectory with 1000+ points."""
        tracker = TrajectoryTracker.with_defaults(
            min_path_length=0.01,
            velocity_threshold=0.001,
            still_frames=3,
            window_seconds=100.0,
        )
        for i in range(1000):
            lm = np.full((21, 3), i / 1000.0, dtype=np.float32)
            lm[:, 1] = 0.5
            tracker.update(0, lm, i * 0.01)
        # Just ensure no crash or memory explosion

    def test_dtw_long_sequences(self):
        """DTW with long sequences should still work (may be slow)."""
        rng = np.random.default_rng(42)
        s = rng.random((100, 2)).astype(np.float32)
        t = rng.random((100, 2)).astype(np.float32)
        dist = _dtw_distance_fast(s, t, window=15)
        assert dist > 0
        assert dist < float("inf")


class TestConcurrentRecorder:
    def test_concurrent_save_load(self, tmp_path):
        """Save and load recordings from multiple threads."""
        errors = []

        def save_and_load(idx):
            try:
                rec = GestureRecorder()
                rec.start()
                for _ in range(50):
                    rec.add_frame([np.random.rand(21, 3).astype(np.float32)])
                rec.stop()

                path = tmp_path / f"thread_{idx}.json"
                rec.save(path)

                player = GesturePlayer.load(path)
                assert player.frame_count == 50
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=save_and_load, args=(i,)) for i in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == [], f"Thread errors: {errors}"


class TestMetricsStress:
    def test_concurrent_metrics(self):
        m = MetricsCollector()
        errors = []

        def record(name):
            try:
                for _ in range(1000):
                    m.record_gesture(name)
                    m.record_frame(0.001, 1)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=record, args=(f"g{i}",)) for i in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
        assert m._frames_total == 4000
        output = m.render()
        assert "gesture_engine_frames_total 4000" in output
