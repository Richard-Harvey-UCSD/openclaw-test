"""Tests for feature extraction and classification."""

import numpy as np
import pytest

from gesture_engine.classifier import GestureClassifier
from gesture_engine.gestures import GestureRegistry


def make_landmarks(seed=0):
    rng = np.random.RandomState(seed)
    lm = rng.randn(21, 3).astype(np.float32) * 0.3
    lm[0] = [0, 0, 0]
    scale = np.max(np.linalg.norm(lm, axis=1)) + 1e-8
    return lm / scale


class TestFeatureExtraction:
    def test_feature_vector_shape(self):
        classifier = GestureClassifier()
        lm = make_landmarks()
        features = classifier.extract_features(lm)
        assert features.shape == (81,)

    def test_feature_dtype(self):
        classifier = GestureClassifier()
        features = classifier.extract_features(make_landmarks())
        assert features.dtype == np.float32

    def test_features_deterministic(self):
        classifier = GestureClassifier()
        lm = make_landmarks(42)
        f1 = classifier.extract_features(lm)
        f2 = classifier.extract_features(lm)
        np.testing.assert_array_equal(f1, f2)

    def test_features_differ_for_different_hands(self):
        classifier = GestureClassifier()
        f1 = classifier.extract_features(make_landmarks(1))
        f2 = classifier.extract_features(make_landmarks(2))
        assert not np.allclose(f1, f2)

    def test_raw_landmarks_in_features(self):
        classifier = GestureClassifier()
        lm = make_landmarks()
        features = classifier.extract_features(lm)
        # First 63 features should be flattened landmarks
        np.testing.assert_allclose(features[:63], lm.flatten(), atol=1e-6)

    def test_fingertip_distances_positive(self):
        classifier = GestureClassifier()
        features = classifier.extract_features(make_landmarks())
        # Features 63-72 are pairwise fingertip distances (10 values)
        distances = features[63:73]
        assert np.all(distances >= 0)

    def test_extension_ratios_positive(self):
        classifier = GestureClassifier()
        features = classifier.extract_features(make_landmarks())
        # Features 73-77 are extension ratios (5 values)
        ratios = features[73:78]
        assert np.all(ratios >= 0)


class TestClassification:
    def test_classify_returns_tuple_or_none(self):
        classifier = GestureClassifier()
        result = classifier.classify(make_landmarks())
        assert result is None or (isinstance(result, tuple) and len(result) == 2)

    def test_rule_based_fallback(self):
        # Without a model, classify should use rule-based
        classifier = GestureClassifier()
        result = classifier.classify_rule_based(make_landmarks())
        # May or may not match — just check it doesn't crash
        if result is not None:
            name, conf = result
            assert isinstance(name, str)
            assert 0 <= conf <= 1
