"""Tests for hand detector normalization logic."""

import numpy as np
import pytest


def make_landmarks(seed=42):
    """Generate realistic-ish hand landmarks."""
    rng = np.random.RandomState(seed)
    lm = rng.randn(21, 3).astype(np.float32) * 0.1
    lm[0] = [0.5, 0.5, 0.0]  # wrist in center
    # Spread fingers out from wrist
    for i, tip in enumerate([4, 8, 12, 16, 20]):
        angle = -0.3 + i * 0.15
        lm[tip] = lm[0] + np.array([angle, -0.3, 0.0])
    return lm


def normalize_landmarks(landmarks):
    """Reproduce detector normalization without MediaPipe."""
    centered = landmarks - landmarks[0]
    scale = np.max(np.linalg.norm(centered, axis=1)) + 1e-8
    return centered / scale


class TestNormalization:
    def test_wrist_at_origin(self):
        lm = make_landmarks()
        norm = normalize_landmarks(lm)
        np.testing.assert_allclose(norm[0], [0, 0, 0], atol=1e-6)

    def test_max_distance_is_one(self):
        lm = make_landmarks()
        norm = normalize_landmarks(lm)
        dists = np.linalg.norm(norm, axis=1)
        assert pytest.approx(np.max(dists), abs=1e-5) == 1.0

    def test_translation_invariance(self):
        lm = make_landmarks()
        lm_shifted = lm + np.array([10.0, -5.0, 3.0])
        norm1 = normalize_landmarks(lm)
        norm2 = normalize_landmarks(lm_shifted)
        np.testing.assert_allclose(norm1, norm2, atol=1e-5)

    def test_scale_invariance(self):
        lm = make_landmarks()
        lm_scaled = lm * 3.5
        norm1 = normalize_landmarks(lm)
        norm2 = normalize_landmarks(lm_scaled)
        np.testing.assert_allclose(norm1, norm2, atol=1e-5)

    def test_shape_preserved(self):
        lm = make_landmarks()
        norm = normalize_landmarks(lm)
        assert norm.shape == (21, 3)
        assert norm.dtype == np.float32 or norm.dtype == np.float64
