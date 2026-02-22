"""Tests for multi-gesture sequence detection."""

import pytest

from gesture_engine.sequences import SequenceDetector, GestureSequence


class TestSequenceDetector:
    def test_simple_two_gesture_sequence(self):
        det = SequenceDetector()
        det.register(GestureSequence(name="release", gestures=["fist", "open_hand"]))

        events = det.feed("fist", timestamp=0.0)
        assert len(events) == 0

        events = det.feed("open_hand", timestamp=0.5)
        assert len(events) == 1
        assert events[0].sequence_name == "release"

    def test_three_gesture_sequence(self):
        det = SequenceDetector()
        det.register(GestureSequence(name="wave", gestures=["open_hand", "fist", "open_hand"]))

        det.feed("open_hand", timestamp=0.0)
        det.feed("fist", timestamp=0.5)
        events = det.feed("open_hand", timestamp=1.0)
        assert len(events) == 1
        assert events[0].sequence_name == "wave"

    def test_timeout_rejects_slow_sequence(self):
        det = SequenceDetector()
        det.register(GestureSequence(name="release", gestures=["fist", "open_hand"], max_duration=1.0))

        det.feed("fist", timestamp=0.0)
        events = det.feed("open_hand", timestamp=5.0)  # too slow
        assert len(events) == 0

    def test_ignores_repeated_same_gesture(self):
        det = SequenceDetector()
        det.register(GestureSequence(name="release", gestures=["fist", "open_hand"]))

        det.feed("fist", timestamp=0.0)
        events = det.feed("fist", timestamp=0.2)  # same gesture, ignored
        assert len(events) == 0

        events = det.feed("open_hand", timestamp=0.5)
        assert len(events) == 1

    def test_cooldown_prevents_rapid_retrigger(self):
        det = SequenceDetector()
        det._cooldown = 1.0
        det.register(GestureSequence(name="release", gestures=["fist", "open_hand"]))

        det.feed("fist", timestamp=0.0)
        det.feed("open_hand", timestamp=0.5)

        # Try again immediately
        det.feed("fist", timestamp=0.6)
        events = det.feed("open_hand", timestamp=0.8)
        assert len(events) == 0  # cooldown

    def test_multiple_sequences(self):
        det = SequenceDetector()
        det.register(GestureSequence(name="release", gestures=["fist", "open_hand"]))
        det.register(GestureSequence(name="grab", gestures=["open_hand", "fist"]))

        det.feed("open_hand", timestamp=0.0)
        events = det.feed("fist", timestamp=0.5)
        assert any(e.sequence_name == "grab" for e in events)

    def test_per_hand_tracking(self):
        det = SequenceDetector()
        det.register(GestureSequence(name="release", gestures=["fist", "open_hand"]))

        det.feed("fist", hand_index=0, timestamp=0.0)
        det.feed("fist", hand_index=1, timestamp=0.1)

        # Only hand 0 completes the sequence
        events = det.feed("open_hand", hand_index=0, timestamp=0.5)
        assert len(events) == 1

    def test_reset_clears_history(self):
        det = SequenceDetector()
        det.register(GestureSequence(name="release", gestures=["fist", "open_hand"]))

        det.feed("fist", timestamp=0.0)
        det.reset()
        events = det.feed("open_hand", timestamp=0.5)
        assert len(events) == 0

    def test_default_sequences(self):
        det = SequenceDetector.with_defaults()
        assert len(det._sequences) >= 5

    def test_duration_reported(self):
        det = SequenceDetector()
        det.register(GestureSequence(name="release", gestures=["fist", "open_hand"]))

        det.feed("fist", timestamp=1.0)
        events = det.feed("open_hand", timestamp=1.7)
        assert len(events) == 1
        assert abs(events[0].duration - 0.7) < 0.01
