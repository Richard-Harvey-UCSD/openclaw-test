"""Integration tests — full pipeline flows across multiple components."""

import asyncio
import numpy as np
import pytest

from gesture_engine.gestures import GestureDefinition, GestureRegistry, FingerState
from gesture_engine.classifier import GestureClassifier
from gesture_engine.sequences import SequenceDetector, GestureSequence
from gesture_engine.recorder import GestureRecorder, GesturePlayer
from gesture_engine.actions import ActionMapper, Action, ActionType, GestureMapping
from gesture_engine.plugins import GesturePlugin, PluginManager, PluginEvent
from gesture_engine.profiler import PipelineProfiler
from gesture_engine.metrics import MetricsCollector
from gesture_engine.bimanual import BimanualDetector
from gesture_engine.canvas import DrawingCanvas
from gesture_engine.trajectory import TrajectoryTracker


def make_open_hand():
    lm = np.zeros((21, 3), dtype=np.float32)
    lm[0] = [0, 0, 0]
    for pip in [3, 6, 10, 14, 18]:
        lm[pip] = [0.2, -0.3, 0]
    for i, tip in enumerate([4, 8, 12, 16, 20]):
        lm[tip] = [0.1 + i * 0.05, -0.6, 0]
    return lm


def make_fist():
    lm = np.zeros((21, 3), dtype=np.float32)
    lm[0] = [0, 0, 0]
    for pip in [3, 6, 10, 14, 18]:
        lm[pip] = [0.15, -0.25, 0]
    for tip in [4, 8, 12, 16, 20]:
        lm[tip] = [0.05, -0.1, 0]
    return lm


class TestClassifierToSequence:
    """Classify landmarks → feed to sequence detector."""

    def test_classify_then_sequence(self):
        classifier = GestureClassifier()
        seq_det = SequenceDetector()
        seq_det.register(GestureSequence(name="release", gestures=["fist", "open_hand"]))

        # Classify fist
        result1 = classifier.classify(make_fist())
        assert result1 is not None
        name1, _ = result1
        seq_det.feed(name1, timestamp=0.0)

        # Classify open hand
        result2 = classifier.classify(make_open_hand())
        assert result2 is not None
        name2, _ = result2
        events = seq_det.feed(name2, timestamp=0.5)

        assert len(events) == 1
        assert events[0].sequence_name == "release"

    def test_full_default_pipeline(self):
        """Use default registry + default sequences."""
        classifier = GestureClassifier()
        seq_det = SequenceDetector.with_defaults()

        r = classifier.classify(make_open_hand())
        assert r is not None
        seq_det.feed(r[0], timestamp=0.0)

        r = classifier.classify(make_fist())
        assert r is not None
        events = seq_det.feed(r[0], timestamp=0.5)
        grab_events = [e for e in events if e.sequence_name == "grab"]
        assert len(grab_events) == 1


class TestRecorderReplayRoundtrip:
    """Record → save → load → replay through classifier."""

    def test_roundtrip(self, tmp_path):
        # Record
        rec = GestureRecorder()
        rec.start()
        fist_lm = make_fist()
        open_lm = make_open_hand()
        rec.add_frame([fist_lm], [{"name": "fist", "confidence": 0.95, "hand_index": 0}])
        rec.add_frame([open_lm], [{"name": "open_hand", "confidence": 0.92, "hand_index": 0}])
        rec.stop()

        path = tmp_path / "roundtrip.json"
        rec.save(path)

        # Replay
        player = GesturePlayer.load(path)
        classifier = GestureClassifier()
        results = []

        for frame in player.play():
            for hand in frame.hands:
                r = classifier.classify(hand)
                if r:
                    results.append(r[0])

        assert "fist" in results
        assert "open_hand" in results

    def test_npz_roundtrip(self, tmp_path):
        rec = GestureRecorder()
        rec.start()
        for i in range(10):
            rec.add_frame([make_fist() if i % 2 == 0 else make_open_hand()])
        rec.stop()

        path = tmp_path / "test.npz"
        rec.save_compact(path)

        player = GesturePlayer.load(path)
        assert player.frame_count == 10
        frames = list(player.play())
        assert all(len(f.hands) == 1 for f in frames)


class TestActionMapperIntegration:
    def test_gesture_to_action(self):
        mapper = ActionMapper()
        mapper.add_mapping(GestureMapping(
            trigger="fist",
            actions=[Action(type=ActionType.LOG, params={"message": "fist detected"})],
            min_confidence=0.5,
        ))

        loop = asyncio.new_event_loop()
        results = loop.run_until_complete(mapper.on_gesture("fist", confidence=0.9))
        loop.close()
        assert results == [True]

    def test_sequence_to_action(self):
        mapper = ActionMapper()
        mapper.add_mapping(GestureMapping(
            trigger="release",
            actions=[Action(type=ActionType.LOG, params={"message": "released"})],
        ))

        loop = asyncio.new_event_loop()
        results = loop.run_until_complete(mapper.on_sequence("release"))
        loop.close()
        assert results == [True]


class TestPluginIntegration:
    def test_plugin_receives_events(self):
        received = []

        class CollectorPlugin(GesturePlugin):
            name = "collector"

            def on_gesture(self, event):
                received.append(event.name)

            def on_sequence(self, event):
                received.append(f"seq:{event.name}")

        mgr = PluginManager()
        mgr.register(CollectorPlugin())

        mgr.dispatch("gesture", PluginEvent(type="gesture", name="fist"))
        mgr.dispatch("gesture", PluginEvent(type="gesture", name="peace"))
        mgr.dispatch("sequence", PluginEvent(type="sequence", name="release"))

        assert received == ["fist", "peace", "seq:release"]


class TestProfilerIntegration:
    def test_profiler_with_classification(self):
        profiler = PipelineProfiler()
        classifier = GestureClassifier()

        for _ in range(20):
            with profiler.stage("classification"):
                classifier.classify(make_fist())

        summary = profiler.summary()
        assert "classification" in summary
        assert summary["classification"]["calls"] == 20
        assert summary["classification"]["avg_ms"] >= 0


class TestMetricsIntegration:
    def test_metrics_after_processing(self):
        metrics = MetricsCollector()
        classifier = GestureClassifier()

        for i in range(10):
            lm = make_fist() if i % 2 == 0 else make_open_hand()
            result = classifier.classify(lm)
            if result:
                metrics.record_gesture(result[0])
            metrics.record_frame(0.005, 1)

        output = metrics.render()
        assert "gesture_engine_frames_total 10" in output
        assert metrics._frames_total == 10
        counts = metrics.gesture_counts
        assert sum(counts.values()) == 10


class TestCanvasIntegration:
    def test_draw_erase_clear(self):
        canvas = DrawingCanvas(smoothing=1)

        # Draw
        lm = np.zeros((21, 3), dtype=np.float32)
        lm[8] = [0.1, 0.5, 0]
        canvas.update(lm, "pointing", 0.0)
        lm[8] = [0.5, 0.5, 0]
        cmds = canvas.update(lm, "pointing", 0.1)
        assert any(c.type == "line" for c in cmds)

        # Erase
        cmds = canvas.update(lm, "fist", 0.2)
        assert any(c.type == "erase" for c in cmds)

        # Clear
        canvas.clear()
        state = canvas.get_full_state()
        assert state[0]["type"] == "clear"


class TestBimanualIntegration:
    def test_zoom_with_classifier(self):
        classifier = GestureClassifier()
        bi_det = BimanualDetector(zoom_threshold=0.01)

        left = make_open_hand()
        left += np.array([0.1, 0, 0])
        right = make_open_hand()
        right += np.array([0.5, 0, 0])

        # Both classified
        r1 = classifier.classify(left)
        r2 = classifier.classify(right)

        bi_det.update([(0, left), (1, right)], 0.0)

        # Move apart
        left2 = left - np.array([0.1, 0, 0])
        right2 = right + np.array([0.1, 0, 0])
        events = bi_det.update([(0, left2), (1, right2)], 0.1)
        zoom_events = [e for e in events if e.gesture == "pinch_zoom"]
        assert len(zoom_events) >= 1
