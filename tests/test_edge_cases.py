"""Edge case tests for GestureEngine."""

import numpy as np
import pytest

from gesture_engine.gestures import GestureDefinition, GestureRegistry, FingerState
from gesture_engine.classifier import GestureClassifier
from gesture_engine.pipeline import GesturePipeline, HandTracker, AdaptiveThresholds
from gesture_engine.sequences import SequenceDetector, GestureSequence
from gesture_engine.recorder import GestureRecorder, GesturePlayer
from gesture_engine.trajectory import (
    TrajectoryTracker, TrajectoryTemplate, _dtw_distance, _dtw_distance_fast, _resample_path,
)
from gesture_engine.bimanual import BimanualDetector
from gesture_engine.canvas import DrawingCanvas
from gesture_engine.profiler import PipelineProfiler
from gesture_engine.metrics import MetricsCollector


class TestLandmarkEdgeCases:
    """Test with malformed/extreme landmark data."""

    def test_nan_landmarks(self):
        classifier = GestureClassifier()
        lm = np.full((21, 3), np.nan, dtype=np.float32)
        # Should not crash, result may be None or a tuple
        result = classifier.classify_rule_based(lm)
        # Just ensure no exception

    def test_inf_landmarks(self):
        classifier = GestureClassifier()
        lm = np.full((21, 3), np.inf, dtype=np.float32)
        result = classifier.classify_rule_based(lm)

    def test_zero_landmarks(self):
        classifier = GestureClassifier()
        lm = np.zeros((21, 3), dtype=np.float32)
        result = classifier.classify_rule_based(lm)
        # All distances zero — should still work

    def test_single_nonzero_landmark(self):
        """Only one landmark has data, rest zero."""
        classifier = GestureClassifier()
        lm = np.zeros((21, 3), dtype=np.float32)
        lm[8] = [0.5, 0.5, 0.0]
        result = classifier.classify_rule_based(lm)

    def test_very_large_values(self):
        classifier = GestureClassifier()
        lm = np.ones((21, 3), dtype=np.float32) * 1e6
        result = classifier.classify_rule_based(lm)

    def test_negative_values(self):
        classifier = GestureClassifier()
        lm = np.ones((21, 3), dtype=np.float32) * -1.0
        lm[0] = [0, 0, 0]
        result = classifier.classify_rule_based(lm)

    def test_feature_extraction_nan(self):
        classifier = GestureClassifier()
        lm = np.full((21, 3), np.nan, dtype=np.float32)
        features = classifier.extract_features(lm)
        assert features.shape == (81,)

    def test_feature_extraction_zero(self):
        classifier = GestureClassifier()
        lm = np.zeros((21, 3), dtype=np.float32)
        features = classifier.extract_features(lm)
        assert features.shape == (81,)


class TestConfidenceEdgeCases:
    def test_very_high_min_confidence(self):
        gesture = GestureDefinition(
            name="impossible",
            thumb=FingerState.EXTENDED,
            min_confidence=1.0,
        )
        lm = np.zeros((21, 3), dtype=np.float32)
        lm[4] = [0, -1, 0]  # thumb extended
        matched, conf = gesture.match(lm)
        assert matched  # confidence should be exactly 1.0

    def test_very_low_min_confidence(self):
        gesture = GestureDefinition(
            name="anything",
            thumb=FingerState.EXTENDED,
            min_confidence=0.0,
        )
        lm = np.zeros((21, 3), dtype=np.float32)
        matched, conf = gesture.match(lm)
        # With min_confidence=0, anything matches

    def test_all_any_fingers(self):
        gesture = GestureDefinition(name="any", min_confidence=0.5)
        lm = np.zeros((21, 3), dtype=np.float32)
        matched, conf = gesture.match(lm)
        assert matched
        assert conf == 1.0


class TestRegistryEdgeCases:
    def test_empty_registry_match(self):
        reg = GestureRegistry()
        lm = np.zeros((21, 3), dtype=np.float32)
        result = reg.match(lm)
        assert result is None

    def test_duplicate_gesture_names(self):
        reg = GestureRegistry()
        g1 = GestureDefinition(name="dup", thumb=FingerState.EXTENDED)
        g2 = GestureDefinition(name="dup", thumb=FingerState.CURLED)
        reg.register(g1)
        reg.register(g2)
        assert len(reg) == 2  # both registered

    def test_registry_iteration(self):
        reg = GestureRegistry()
        reg.register(GestureDefinition(name="a"))
        reg.register(GestureDefinition(name="b"))
        names = [g.name for g in reg]
        assert names == ["a", "b"]


class TestHandTrackerEdgeCases:
    def test_empty_hands(self):
        tracker = HandTracker()
        result = tracker.update([], 0.0)
        assert result == []

    def test_many_hands(self):
        tracker = HandTracker()
        hands = [np.random.rand(21, 3).astype(np.float32) * i for i in range(5)]
        result = tracker.update(hands, 0.0)
        assert len(result) == 5

    def test_get_nonexistent_track(self):
        tracker = HandTracker()
        assert tracker.get_track(999) is None


class TestAdaptiveThresholdEdgeCases:
    def test_many_gestures(self):
        at = AdaptiveThresholds()
        for i in range(100):
            at.record(f"gesture_{i}", 0.8, was_stable=True)
        assert len(at.current_thresholds) == 100


class TestSequenceEdgeCases:
    def test_single_gesture_sequence(self):
        det = SequenceDetector()
        det.register(GestureSequence(name="tap", gestures=["fist"]))
        events = det.feed("fist", timestamp=0.0)
        assert len(events) == 1

    def test_empty_history_reset(self):
        det = SequenceDetector()
        det.reset()  # Should not crash
        det.reset(hand_index=5)


class TestRecorderEdgeCases:
    def test_empty_recording_save_json(self, tmp_path):
        rec = GestureRecorder()
        rec.start()
        rec.stop()
        path = tmp_path / "empty.json"
        rec.save(path)
        player = GesturePlayer.load(path)
        assert player.frame_count == 0

    def test_empty_recording_save_npz(self, tmp_path):
        rec = GestureRecorder()
        rec.start()
        rec.stop()
        path = tmp_path / "empty.npz"
        rec.save_compact(path)
        player = GesturePlayer.load(path)
        assert player.frame_count == 0

    def test_recording_duration_zero_frames(self):
        rec = GestureRecorder()
        assert rec.duration == 0.0

    def test_player_empty_duration(self):
        player = GesturePlayer([])
        assert player.duration == 0.0
        assert player.frame_count == 0

    def test_player_get_frame_negative(self):
        player = GesturePlayer([])
        assert player.get_frame(-1) is None

    def test_play_realtime_empty(self):
        player = GesturePlayer([])
        frames = list(player.play_realtime())
        assert frames == []


class TestCanvasEdgeCases:
    def test_out_of_bounds_coordinates(self):
        canvas = DrawingCanvas(smoothing=1)
        lm = np.zeros((21, 3), dtype=np.float32)
        lm[8] = [-1.0, 2.0, 0]
        cmds = canvas.update(lm, "pointing", 0.0)
        # Should not crash

    def test_rapid_drawing(self):
        canvas = DrawingCanvas(smoothing=1)
        for i in range(100):
            lm = np.zeros((21, 3), dtype=np.float32)
            lm[8] = [i / 100.0, 0.5, 0]
            canvas.update(lm, "pointing", i * 0.01)
        assert canvas.command_count > 0

    def test_multiple_hand_ids(self):
        """Canvas doesn't track hand IDs directly, but shouldn't crash with varied input."""
        canvas = DrawingCanvas(smoothing=1)
        for i in range(10):
            lm = np.zeros((21, 3), dtype=np.float32)
            lm[8] = [i / 10.0, 0.5, 0]
            canvas.update(lm, "pointing", i * 0.1)

    def test_canvas_state_after_clear(self):
        canvas = DrawingCanvas(smoothing=1)
        lm = np.zeros((21, 3), dtype=np.float32)
        lm[8] = [0.1, 0.1, 0]
        canvas.update(lm, "pointing", 0.0)
        lm[8] = [0.5, 0.5, 0]
        canvas.update(lm, "pointing", 0.1)
        canvas.clear()
        state = canvas.get_full_state()
        assert len(state) == 1
        assert state[0]["type"] == "clear"


class TestTrajectoryEdgeCases:
    def test_dtw_empty_sequences(self):
        s = np.array([], dtype=np.float32).reshape(0, 2)
        t = np.array([[1, 0]], dtype=np.float32)
        assert _dtw_distance(s, t) == float("inf")
        assert _dtw_distance(t, s) == float("inf")

    def test_dtw_single_point(self):
        s = np.array([[0, 0]], dtype=np.float32)
        t = np.array([[1, 1]], dtype=np.float32)
        dist = _dtw_distance(s, t)
        assert dist > 0

    def test_dtw_fast_empty(self):
        s = np.array([], dtype=np.float32).reshape(0, 2)
        t = np.array([[1, 0]], dtype=np.float32)
        assert _dtw_distance_fast(s, t) == float("inf")

    def test_resample_two_points(self):
        pts = np.array([[0, 0], [1, 0]], dtype=np.float32)
        resampled = _resample_path(pts, 10)
        assert len(resampled) == 10

    def test_resample_identical_points(self):
        pts = np.array([[1, 1], [1, 1], [1, 1]], dtype=np.float32)
        resampled = _resample_path(pts, 5)
        assert len(resampled) == 5
        np.testing.assert_allclose(resampled, [[1, 1]] * 5, atol=1e-6)

    def test_template_normalized_flat(self):
        """Template with all same points."""
        pts = np.array([[5, 5], [5, 5]], dtype=np.float32)
        tmpl = TrajectoryTemplate(name="flat", points=pts)
        normed = tmpl.normalized()
        # Should handle division by zero gracefully
        assert normed.shape == (2, 2)

    def test_recording_abort(self):
        tracker = TrajectoryTracker()
        tracker.start_recording("test")
        # Only feed 2 points (less than 5 minimum)
        for i in range(2):
            lm = np.zeros((21, 3), dtype=np.float32)
            tracker.update(0, lm, i * 0.1)
        result = tracker.stop_recording()
        assert result is None  # too few points

    def test_clear_specific_hand(self):
        tracker = TrajectoryTracker()
        lm = np.zeros((21, 3), dtype=np.float32)
        tracker.update(0, lm, 0.0)
        tracker.update(1, lm, 0.0)
        tracker.clear(hand_id=0)
        assert 0 not in tracker._paths
        assert 1 in tracker._paths


class TestProfilerEdgeCases:
    def test_unknown_stage(self):
        profiler = PipelineProfiler()
        with profiler.stage("custom_stage"):
            pass
        stats = profiler.get_stage_stats("custom_stage")
        assert stats is not None
        assert stats.call_count == 1

    def test_stats_nonexistent_stage(self):
        profiler = PipelineProfiler()
        assert profiler.get_stage_stats("nope") is None


class TestMetricsEdgeCases:
    def test_empty_render(self):
        m = MetricsCollector()
        output = m.render()
        assert "gesture_engine_frames_total 0" in output

    def test_thread_safety_basic(self):
        import threading
        m = MetricsCollector()

        def record_many():
            for _ in range(100):
                m.record_gesture("test")
                m.record_frame(0.001, 1)

        threads = [threading.Thread(target=record_many) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert m._frames_total == 400
        assert m.gesture_counts["test"] == 400


class TestBimanualEdgeCases:
    def test_single_hand(self):
        det = BimanualDetector()
        lm = np.zeros((21, 3), dtype=np.float32)
        events = det.update([(0, lm)], 0.0)
        assert events == []

    def test_three_hands(self):
        """Should only use first two."""
        det = BimanualDetector()
        hands = [(i, np.random.rand(21, 3).astype(np.float32)) for i in range(3)]
        events = det.update(hands, 0.0)
        # Should not crash
        assert isinstance(events, list)

    def test_identical_hands(self):
        det = BimanualDetector()
        lm = np.zeros((21, 3), dtype=np.float32)
        events = det.update([(0, lm), (1, lm)], 0.0)
        assert isinstance(events, list)
