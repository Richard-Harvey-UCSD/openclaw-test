"""Tests for gesture definition matching and registry."""

import numpy as np
import pytest

from gesture_engine.gestures import GestureDefinition, GestureRegistry, FingerState


def make_open_hand():
    """Landmarks with all fingers extended (tips far from wrist)."""
    lm = np.zeros((21, 3), dtype=np.float32)
    lm[0] = [0, 0, 0]  # wrist
    # PIPs at moderate distance
    for pip in [3, 6, 10, 14, 18]:
        lm[pip] = [0.2, -0.3, 0]
    # Tips farther out (extended)
    for i, tip in enumerate([4, 8, 12, 16, 20]):
        lm[tip] = [0.1 + i * 0.05, -0.6, 0]
    return lm


def make_fist():
    """Landmarks with all fingers curled (tips close to wrist)."""
    lm = np.zeros((21, 3), dtype=np.float32)
    lm[0] = [0, 0, 0]
    # PIPs farther than tips
    for pip in [3, 6, 10, 14, 18]:
        lm[pip] = [0.15, -0.25, 0]
    for tip in [4, 8, 12, 16, 20]:
        lm[tip] = [0.05, -0.1, 0]
    return lm


def make_peace():
    """Index + middle extended, rest curled."""
    lm = make_fist()
    # Extend index and middle
    lm[8] = [0.15, -0.6, 0]   # index tip
    lm[12] = [0.2, -0.6, 0]   # middle tip
    return lm


class TestGestureDefinition:
    def test_open_hand_matches(self):
        gesture = GestureDefinition(
            name="open_hand",
            thumb=FingerState.EXTENDED, index=FingerState.EXTENDED,
            middle=FingerState.EXTENDED, ring=FingerState.EXTENDED,
            pinky=FingerState.EXTENDED,
        )
        matched, conf = gesture.match(make_open_hand())
        assert matched
        assert conf >= 0.8

    def test_fist_matches(self):
        gesture = GestureDefinition(
            name="fist",
            thumb=FingerState.CURLED, index=FingerState.CURLED,
            middle=FingerState.CURLED, ring=FingerState.CURLED,
            pinky=FingerState.CURLED,
        )
        matched, conf = gesture.match(make_fist())
        assert matched
        assert conf >= 0.8

    def test_fist_rejects_open_hand(self):
        gesture = GestureDefinition(
            name="fist",
            thumb=FingerState.CURLED, index=FingerState.CURLED,
            middle=FingerState.CURLED, ring=FingerState.CURLED,
            pinky=FingerState.CURLED,
        )
        matched, conf = gesture.match(make_open_hand())
        assert not matched

    def test_any_state_ignored(self):
        gesture = GestureDefinition(
            name="test",
            thumb=FingerState.ANY, index=FingerState.EXTENDED,
            middle=FingerState.ANY, ring=FingerState.ANY,
            pinky=FingerState.ANY,
        )
        lm = make_open_hand()
        matched, conf = gesture.match(lm)
        assert matched

    def test_distance_constraint(self):
        gesture = GestureDefinition(
            name="ok_sign",
            thumb=FingerState.EXTENDED, index=FingerState.EXTENDED,
            middle=FingerState.EXTENDED, ring=FingerState.EXTENDED,
            pinky=FingerState.EXTENDED,
            constraints=[{"type": "distance", "landmarks": [4, 8], "min": 0, "max": 0.1}],
        )
        lm = make_open_hand()
        # Put thumb tip and index tip close together
        lm[4] = [0.15, -0.5, 0]
        lm[8] = [0.16, -0.5, 0]
        matched, conf = gesture.match(lm)
        assert matched

    def test_serialization_roundtrip(self):
        gesture = GestureDefinition(
            name="test", thumb=FingerState.EXTENDED, index=FingerState.CURLED,
            min_confidence=0.7,
            constraints=[{"type": "distance", "landmarks": [4, 8], "min": 0, "max": 0.2}],
        )
        data = gesture.to_dict()
        restored = GestureDefinition.from_dict(data)
        assert restored.name == "test"
        assert restored.thumb == FingerState.EXTENDED
        assert restored.index == FingerState.CURLED
        assert restored.min_confidence == 0.7
        assert len(restored.constraints) == 1


class TestGestureRegistry:
    def test_default_registry_has_gestures(self):
        reg = GestureRegistry.with_defaults()
        assert len(reg) >= 6

    def test_match_open_hand(self):
        reg = GestureRegistry.with_defaults()
        result = reg.match(make_open_hand())
        assert result is not None
        assert result[0].name == "open_hand"

    def test_match_fist(self):
        reg = GestureRegistry.with_defaults()
        result = reg.match(make_fist())
        assert result is not None
        assert result[0].name == "fist"

    def test_match_peace(self):
        reg = GestureRegistry.with_defaults()
        result = reg.match(make_peace())
        assert result is not None
        assert result[0].name == "peace"

    def test_register_custom(self):
        reg = GestureRegistry()
        reg.register(GestureDefinition(name="custom", thumb=FingerState.EXTENDED))
        assert len(reg) == 1

    def test_save_load_roundtrip(self, tmp_path):
        reg = GestureRegistry.with_defaults()
        path = tmp_path / "gestures.json"
        reg.save_to_file(path)

        reg2 = GestureRegistry()
        reg2.load_from_file(path)
        assert len(reg2) == len(reg)
