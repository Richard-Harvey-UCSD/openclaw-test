"""Tests for model export functionality."""

import numpy as np
import pytest

from gesture_engine.classifier import GestureClassifier


class TestExportMissingDeps:
    def test_export_without_model(self):
        from gesture_engine.export import ModelExporter
        classifier = GestureClassifier()
        # No model loaded
        with pytest.raises(ValueError, match="no trained model"):
            ModelExporter(classifier)


# Only run full export tests if torch is available
try:
    import torch
    _HAS_TORCH = True
except ImportError:
    _HAS_TORCH = False

try:
    import onnx
    import onnxruntime
    _HAS_ONNX = True
except ImportError:
    _HAS_ONNX = False


@pytest.fixture
def trained_classifier():
    """Create a simple trained classifier."""
    classifier = GestureClassifier()
    rng = np.random.default_rng(42)
    X = rng.random((60, 21, 3)).astype(np.float32)
    y = ["fist"] * 20 + ["open_hand"] * 20 + ["peace"] * 20
    classifier.train(X, y, epochs=5)
    return classifier


@pytest.mark.skipif(not _HAS_TORCH, reason="torch not installed")
class TestTraining:
    def test_train_and_classify(self, trained_classifier):
        lm = np.random.default_rng(0).random((21, 3)).astype(np.float32)
        result = trained_classifier.classify(lm)
        assert result is not None
        name, conf = result
        assert isinstance(name, str)
        assert 0 <= conf <= 1

    def test_save_load_model(self, trained_classifier, tmp_path):
        path = tmp_path / "model.pt"
        trained_classifier.save_model(path)
        assert path.exists()

        loaded = GestureClassifier(model_path=path)
        lm = np.random.default_rng(0).random((21, 3)).astype(np.float32)
        r1 = trained_classifier.classify(lm)
        r2 = loaded.classify(lm)
        assert r1[0] == r2[0]
        assert abs(r1[1] - r2[1]) < 1e-5


@pytest.mark.skipif(not (_HAS_TORCH and _HAS_ONNX), reason="torch+onnx required")
class TestONNXExport:
    def test_export_onnx(self, trained_classifier, tmp_path):
        from gesture_engine.export import ModelExporter
        exporter = ModelExporter(trained_classifier)
        path = exporter.to_onnx(tmp_path / "model")
        assert path.exists()
        assert path.suffix == ".onnx"
        assert path.stat().st_size > 0

    def test_validate_onnx(self, trained_classifier, tmp_path):
        from gesture_engine.export import ModelExporter
        exporter = ModelExporter(trained_classifier)
        onnx_path = exporter.to_onnx(tmp_path / "model")
        result = exporter.validate_onnx(onnx_path)
        assert result["valid"] is True
        assert result["max_difference"] < 1e-4

    def test_onnx_inference_matches_pytorch(self, trained_classifier, tmp_path):
        from gesture_engine.export import ModelExporter
        import onnxruntime as ort

        exporter = ModelExporter(trained_classifier)
        onnx_path = exporter.to_onnx(tmp_path / "model")

        # Multiple test inputs
        rng = np.random.default_rng(123)
        for _ in range(5):
            lm = rng.random((21, 3)).astype(np.float32)
            features = trained_classifier.extract_features(lm).reshape(1, -1)

            # PyTorch
            with torch.no_grad():
                pt_out = trained_classifier._model(torch.FloatTensor(features)).numpy()

            # ONNX
            sess = ort.InferenceSession(str(onnx_path))
            onnx_out = sess.run(None, {"landmarks_features": features})[0]

            np.testing.assert_allclose(pt_out, onnx_out, atol=1e-5)

    def test_label_map_saved(self, trained_classifier, tmp_path):
        from gesture_engine.export import ModelExporter
        import json
        exporter = ModelExporter(trained_classifier)
        exporter.to_onnx(tmp_path / "model")
        labels_path = tmp_path / "model.labels.json"
        assert labels_path.exists()
        labels = json.loads(labels_path.read_text())
        assert len(labels) == 3  # fist, open_hand, peace
