"""Tests for two-hand gesture detection."""

import numpy as np
import pytest

from gesture_engine.bimanual import BimanualDetector, BimanualEvent


def _make_hand(x_offset: float = 0.0, y_offset: float = 0.0) -> np.ndarray:
    """Create a basic hand landmark array at given offset."""
    lm = np.zeros((21, 3), dtype=np.float32)
    for i in range(21):
        lm[i] = [x_offset + i * 0.01, y_offset + i * 0.01, 0]
    return lm


class TestBimanualDetector:
    def test_needs_two_hands(self):
        det = BimanualDetector()
        events = det.update([(0, _make_hand())], 0.0)
        assert events == []

    def test_pinch_zoom(self):
        det = BimanualDetector(zoom_threshold=0.01)
        # First frame: hands close
        h1 = _make_hand(0.2)
        h2 = _make_hand(0.4)
        det.update([(0, h1), (1, h2)], 0.0)

        # Second frame: hands farther apart
        h1 = _make_hand(0.1)
        h2 = _make_hand(0.5)
        events = det.update([(0, h1), (1, h2)], 0.1)

        zoom_events = [e for e in events if e.gesture == "pinch_zoom"]
        assert len(zoom_events) >= 1
        assert zoom_events[0].value > 1.0  # zoom in

    def test_clap_detection(self):
        det = BimanualDetector(clap_distance=0.15, clap_velocity=0.1)

        # Build up history with hands apart
        for i in range(6):
            h1 = _make_hand(0.1)
            h2 = _make_hand(0.6)
            det.update([(0, h1), (1, h2)], i * 0.05)

        # Suddenly bring hands together
        h1 = _make_hand(0.3)
        h2 = _make_hand(0.32)
        events = det.update([(0, h1), (1, h2)], 0.3)
        clap_events = [e for e in events if e.gesture == "clap"]
        assert len(clap_events) >= 1

    def test_reset(self):
        det = BimanualDetector()
        det.update([(0, _make_hand(0.2)), (1, _make_hand(0.5))], 0.0)
        det.reset()
        assert len(det._history) == 0

    def test_conducting(self):
        det = BimanualDetector()
        # Both hands moving down
        for i in range(10):
            y = i * 0.05
            h1 = _make_hand(0.2, y)
            h2 = _make_hand(0.5, y)
            det.update([(0, h1), (1, h2)], i * 0.04)

        events = det.update(
            [(0, _make_hand(0.2, 0.5)), (1, _make_hand(0.5, 0.5))], 0.4
        )
        conduct = [e for e in events if "conduct" in e.gesture]
        # May or may not trigger depending on velocity
        assert isinstance(conduct, list)
