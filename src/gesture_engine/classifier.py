"""Gesture classification using both rule-based and learned approaches."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np

from gesture_engine.gestures import GestureRegistry


class GestureClassifier:
    """Classifies hand gestures from normalized landmarks.

    Supports two modes:
    1. Rule-based: Uses GestureRegistry definitions (zero-shot, no training)
    2. Learned: Lightweight MLP trained on landmark features (higher accuracy)

    The rule-based mode works out of the box. The learned mode requires
    collecting examples and training via the `train()` method.
    """

    def __init__(
        self,
        registry: Optional[GestureRegistry] = None,
        model_path: Optional[str | Path] = None,
    ):
        self._registry = registry or GestureRegistry.with_defaults()
        self._model = None
        self._label_map: dict[int, str] = {}
        self._feature_dim: Optional[int] = None

        if model_path:
            self.load_model(model_path)

    def classify_rule_based(
        self, landmarks: np.ndarray
    ) -> Optional[tuple[str, float]]:
        """Classify gesture using rule-based definitions.

        Args:
            landmarks: Normalized hand landmarks, shape (21, 3).

        Returns:
            (gesture_name, confidence) or None if no match.
        """
        result = self._registry.match(landmarks)
        if result is None:
            return None
        return result[0].name, result[1]

    def extract_features(self, landmarks: np.ndarray) -> np.ndarray:
        """Extract feature vector from landmarks for ML classification.

        Features include:
        - Flattened normalized landmarks (63)
        - Pairwise fingertip distances (10)
        - Finger extension ratios (5)
        - Palm angle features (3)

        Total: 81 features

        Args:
            landmarks: Normalized landmarks, shape (21, 3).

        Returns:
            Feature vector, shape (81,).
        """
        features = []

        # Raw landmark positions (63 features)
        features.extend(landmarks.flatten())

        # Pairwise fingertip distances (10 features)
        tips = [4, 8, 12, 16, 20]
        for i in range(len(tips)):
            for j in range(i + 1, len(tips)):
                dist = np.linalg.norm(landmarks[tips[i]] - landmarks[tips[j]])
                features.append(dist)

        # Finger extension ratios: tip_dist / pip_dist from wrist (5 features)
        pips = [3, 6, 10, 14, 18]
        wrist = landmarks[0]
        for tip, pip in zip(tips, pips):
            tip_dist = np.linalg.norm(landmarks[tip] - wrist)
            pip_dist = np.linalg.norm(landmarks[pip] - wrist) + 1e-8
            features.append(tip_dist / pip_dist)

        # Palm orientation: normal vector of palm triangle (3 features)
        v1 = landmarks[5] - landmarks[0]   # wrist → index_mcp
        v2 = landmarks[17] - landmarks[0]  # wrist → pinky_mcp
        palm_normal = np.cross(v1, v2)
        norm = np.linalg.norm(palm_normal) + 1e-8
        features.extend(palm_normal / norm)

        return np.array(features, dtype=np.float32)

    def classify(self, landmarks: np.ndarray) -> Optional[tuple[str, float]]:
        """Classify gesture using best available method.

        Uses learned model if loaded, otherwise falls back to rule-based.
        """
        if self._model is not None:
            return self._classify_learned(landmarks)
        return self.classify_rule_based(landmarks)

    def _classify_learned(
        self, landmarks: np.ndarray
    ) -> Optional[tuple[str, float]]:
        """Classify using the trained MLP model."""
        try:
            import torch
        except ImportError:
            # Fallback to rule-based if torch unavailable
            return self.classify_rule_based(landmarks)

        features = self.extract_features(landmarks)
        tensor = torch.FloatTensor(features).unsqueeze(0)

        with torch.no_grad():
            logits = self._model(tensor)
            probs = torch.softmax(logits, dim=1)
            confidence, predicted = torch.max(probs, 1)

        label = self._label_map.get(predicted.item(), "unknown")
        return label, confidence.item()

    def train(
        self,
        X: np.ndarray,
        y: list[str],
        epochs: int = 100,
        lr: float = 0.001,
        save_path: Optional[str | Path] = None,
    ) -> dict:
        """Train the MLP classifier on collected gesture examples.

        Args:
            X: Landmark arrays, shape (N, 21, 3).
            y: Gesture labels, length N.
            epochs: Training epochs.
            lr: Learning rate.
            save_path: Optional path to save trained model.

        Returns:
            Training stats dict with final loss and accuracy.
        """
        import torch
        import torch.nn as nn
        from torch.utils.data import DataLoader, TensorDataset

        # Build label mapping
        unique_labels = sorted(set(y))
        label_to_idx = {label: i for i, label in enumerate(unique_labels)}
        self._label_map = {i: label for label, i in label_to_idx.items()}

        # Extract features
        features = np.array([self.extract_features(x) for x in X])
        targets = np.array([label_to_idx[label] for label in y])

        self._feature_dim = features.shape[1]
        num_classes = len(unique_labels)

        # Build MLP
        self._model = nn.Sequential(
            nn.Linear(self._feature_dim, 128),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(64, num_classes),
        )

        # Train
        dataset = TensorDataset(
            torch.FloatTensor(features),
            torch.LongTensor(targets),
        )
        loader = DataLoader(dataset, batch_size=32, shuffle=True)
        optimizer = torch.optim.Adam(self._model.parameters(), lr=lr)
        criterion = nn.CrossEntropyLoss()

        self._model.train()
        final_loss = 0.0

        for epoch in range(epochs):
            epoch_loss = 0.0
            correct = 0
            total = 0

            for batch_x, batch_y in loader:
                optimizer.zero_grad()
                logits = self._model(batch_x)
                loss = criterion(logits, batch_y)
                loss.backward()
                optimizer.step()

                epoch_loss += loss.item()
                _, predicted = torch.max(logits, 1)
                correct += (predicted == batch_y).sum().item()
                total += batch_y.size(0)

            final_loss = epoch_loss / len(loader)

        accuracy = correct / total if total > 0 else 0

        self._model.eval()

        if save_path:
            self.save_model(save_path)

        return {"loss": final_loss, "accuracy": accuracy, "classes": unique_labels}

    def save_model(self, path: str | Path):
        """Save trained model and metadata."""
        import torch

        torch.save({
            "model_state": self._model.state_dict(),
            "label_map": self._label_map,
            "feature_dim": self._feature_dim,
            "architecture": [
                layer for layer in self._model
                if hasattr(layer, "in_features")
            ],
        }, path)

    def load_model(self, path: str | Path):
        """Load a trained model."""
        import torch
        import torch.nn as nn

        checkpoint = torch.load(path, map_location="cpu", weights_only=False)
        self._label_map = checkpoint["label_map"]
        self._feature_dim = checkpoint["feature_dim"]
        num_classes = len(self._label_map)

        self._model = nn.Sequential(
            nn.Linear(self._feature_dim, 128),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(64, num_classes),
        )
        self._model.load_state_dict(checkpoint["model_state"])
        self._model.eval()
