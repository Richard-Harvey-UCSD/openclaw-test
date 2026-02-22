"""Model export to ONNX and TFLite for edge deployment.

Supports:
- ONNX export with opset 17
- TFLite conversion via ONNX → TF → TFLite
- INT8 quantization for Pi-level hardware
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger("gesture_engine.export")


class ModelExporter:
    """Export trained GestureClassifier MLP to edge formats."""

    def __init__(self, classifier):
        """
        Args:
            classifier: A GestureClassifier with a loaded/trained model.
        """
        self.classifier = classifier
        if classifier._model is None:
            raise ValueError("Classifier has no trained model to export")

    def to_onnx(
        self,
        output_path: str | Path,
        opset_version: int = 17,
    ) -> Path:
        """Export model to ONNX format.

        Args:
            output_path: Destination .onnx file.
            opset_version: ONNX opset version.

        Returns:
            Path to the exported file.
        """
        import torch

        output_path = Path(output_path).with_suffix(".onnx")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        model = self.classifier._model
        model.eval()

        feature_dim = self.classifier._feature_dim or 81
        dummy_input = torch.randn(1, feature_dim)

        torch.onnx.export(
            model,
            dummy_input,
            str(output_path),
            export_params=True,
            opset_version=opset_version,
            do_constant_folding=True,
            input_names=["landmarks_features"],
            output_names=["gesture_logits"],
            dynamic_axes={
                "landmarks_features": {0: "batch_size"},
                "gesture_logits": {0: "batch_size"},
            },
        )

        # Validate
        import onnx
        onnx_model = onnx.load(str(output_path))
        onnx.checker.check_model(onnx_model)

        # Save label map alongside
        self._save_label_map(output_path.with_suffix(".labels.json"))

        logger.info("ONNX model exported to %s (%.1f KB)", output_path, output_path.stat().st_size / 1024)
        return output_path

    def to_tflite(
        self,
        output_path: str | Path,
        quantize: bool = False,
        quantize_int8: bool = False,
        representative_data: Optional[np.ndarray] = None,
    ) -> Path:
        """Export model to TFLite format via ONNX → TF → TFLite.

        Args:
            output_path: Destination .tflite file.
            quantize: Apply dynamic range quantization (float16).
            quantize_int8: Apply full INT8 quantization (needs representative_data).
            representative_data: Sample feature vectors for INT8 calibration, shape (N, feature_dim).

        Returns:
            Path to the exported file.
        """
        import tempfile

        output_path = Path(output_path).with_suffix(".tflite")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Step 1: Export to ONNX first
        with tempfile.NamedTemporaryFile(suffix=".onnx", delete=False) as tmp:
            onnx_path = self.to_onnx(tmp.name)

        # Step 2: ONNX → TF SavedModel
        try:
            import onnx2tf
            import tensorflow as tf

            with tempfile.TemporaryDirectory() as tf_dir:
                onnx2tf.convert(
                    input_onnx_file_path=str(onnx_path),
                    output_folder_path=tf_dir,
                    non_verbose=True,
                )

                # Step 3: TF → TFLite
                converter = tf.lite.TFLiteConverter.from_saved_model(tf_dir)

                if quantize_int8 and representative_data is not None:
                    def representative_dataset():
                        for i in range(min(len(representative_data), 200)):
                            yield [representative_data[i:i+1].astype(np.float32)]

                    converter.optimizations = [tf.lite.Optimize.DEFAULT]
                    converter.representative_dataset = representative_dataset
                    converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
                    converter.inference_input_type = tf.int8
                    converter.inference_output_type = tf.int8
                    logger.info("Applying INT8 quantization")
                elif quantize:
                    converter.optimizations = [tf.lite.Optimize.DEFAULT]
                    logger.info("Applying dynamic range quantization")

                tflite_model = converter.convert()

        except ImportError:
            # Fallback: use onnxruntime to verify ONNX, then try direct tflite conversion
            logger.warning("onnx2tf/tensorflow not available; using ONNX-only export")
            raise ImportError(
                "TFLite export requires: pip install tensorflow onnx2tf\n"
                "For ONNX-only export, use to_onnx() instead."
            )
        finally:
            Path(onnx_path).unlink(missing_ok=True)

        output_path.write_bytes(tflite_model)
        self._save_label_map(output_path.with_suffix(".labels.json"))

        logger.info(
            "TFLite model exported to %s (%.1f KB%s)",
            output_path,
            output_path.stat().st_size / 1024,
            ", INT8 quantized" if quantize_int8 else (", quantized" if quantize else ""),
        )
        return output_path

    def validate_onnx(self, onnx_path: str | Path) -> dict:
        """Validate ONNX model and compare outputs with PyTorch.

        Returns dict with validation results.
        """
        import onnxruntime as ort
        import torch

        onnx_path = Path(onnx_path)

        # Run PyTorch
        feature_dim = self.classifier._feature_dim or 81
        test_input = np.random.randn(1, feature_dim).astype(np.float32)

        model = self.classifier._model
        model.eval()
        with torch.no_grad():
            torch_out = model(torch.FloatTensor(test_input)).numpy()

        # Run ONNX
        session = ort.InferenceSession(str(onnx_path))
        onnx_out = session.run(None, {"landmarks_features": test_input})[0]

        # Compare
        max_diff = float(np.max(np.abs(torch_out - onnx_out)))
        matches = max_diff < 1e-4

        return {
            "valid": matches,
            "max_difference": max_diff,
            "pytorch_output": torch_out.tolist(),
            "onnx_output": onnx_out.tolist(),
        }

    def _save_label_map(self, path: Path):
        """Save label map as JSON for inference."""
        import json
        with open(path, "w") as f:
            json.dump(self.classifier._label_map, f, indent=2)
