"""Gesture definition system — define gestures via landmark geometry."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

import numpy as np


class FingerState(Enum):
    """Binary finger state based on landmark positions."""
    EXTENDED = "extended"
    CURLED = "curled"
    ANY = "any"  # don't care


@dataclass
class GestureDefinition:
    """A gesture defined by finger states and optional geometric constraints.

    Finger extension is determined by comparing fingertip distance from wrist
    vs PIP joint distance from wrist (extended fingers have tips farther out).

    Optional constraints allow more precise definitions using angles and
    distances between arbitrary landmarks.
    """

    name: str
    thumb: FingerState = FingerState.ANY
    index: FingerState = FingerState.ANY
    middle: FingerState = FingerState.ANY
    ring: FingerState = FingerState.ANY
    pinky: FingerState = FingerState.ANY
    min_confidence: float = 0.6
    constraints: list[dict] = field(default_factory=list)

    # Landmark indices for fingertip and PIP joints
    _FINGER_TIPS = [4, 8, 12, 16, 20]
    _FINGER_PIPS = [3, 6, 10, 14, 18]  # thumb uses IP instead of PIP
    _WRIST = 0

    def match(self, landmarks: np.ndarray) -> tuple[bool, float]:
        """Check if landmarks match this gesture definition.

        Args:
            landmarks: Normalized landmarks, shape (21, 3).

        Returns:
            (matched, confidence) tuple.
        """
        finger_states = self._get_finger_states(landmarks)
        expected = [self.thumb, self.index, self.middle, self.ring, self.pinky]

        matches = 0
        checked = 0

        for actual, expected_state in zip(finger_states, expected):
            if expected_state == FingerState.ANY:
                continue
            checked += 1
            if actual == expected_state:
                matches += 1

        if checked == 0:
            finger_confidence = 1.0
        else:
            finger_confidence = matches / checked

        # Check geometric constraints
        constraint_score = self._check_constraints(landmarks)

        # Combined confidence
        if self.constraints:
            confidence = 0.7 * finger_confidence + 0.3 * constraint_score
        else:
            confidence = finger_confidence

        matched = confidence >= self.min_confidence
        return matched, confidence

    def _get_finger_states(self, landmarks: np.ndarray) -> list[FingerState]:
        """Determine extension state of each finger."""
        states = []
        wrist = landmarks[self._WRIST]

        for tip_idx, pip_idx in zip(self._FINGER_TIPS, self._FINGER_PIPS):
            tip_dist = np.linalg.norm(landmarks[tip_idx] - wrist)
            pip_dist = np.linalg.norm(landmarks[pip_idx] - wrist)

            if tip_dist > pip_dist:
                states.append(FingerState.EXTENDED)
            else:
                states.append(FingerState.CURLED)

        return states

    def _check_constraints(self, landmarks: np.ndarray) -> float:
        """Evaluate geometric constraints. Returns score in [0, 1]."""
        if not self.constraints:
            return 1.0

        scores = []
        for constraint in self.constraints:
            kind = constraint.get("type")

            if kind == "distance":
                # Distance between two landmarks within a range
                a, b = constraint["landmarks"]
                dist = np.linalg.norm(landmarks[a] - landmarks[b])
                lo, hi = constraint.get("min", 0), constraint.get("max", float("inf"))
                scores.append(1.0 if lo <= dist <= hi else 0.0)

            elif kind == "angle":
                # Angle at vertex B in triangle A-B-C
                a, b, c = constraint["landmarks"]
                ba = landmarks[a] - landmarks[b]
                bc = landmarks[c] - landmarks[b]
                cos_angle = np.dot(ba, bc) / (
                    np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-8
                )
                angle_deg = math.degrees(math.acos(np.clip(cos_angle, -1, 1)))
                lo = constraint.get("min_angle", 0)
                hi = constraint.get("max_angle", 180)
                scores.append(1.0 if lo <= angle_deg <= hi else 0.0)

        return sum(scores) / len(scores) if scores else 1.0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "fingers": {
                "thumb": self.thumb.value,
                "index": self.index.value,
                "middle": self.middle.value,
                "ring": self.ring.value,
                "pinky": self.pinky.value,
            },
            "min_confidence": self.min_confidence,
            "constraints": self.constraints,
        }

    @classmethod
    def from_dict(cls, data: dict) -> GestureDefinition:
        fingers = data.get("fingers", {})
        return cls(
            name=data["name"],
            thumb=FingerState(fingers.get("thumb", "any")),
            index=FingerState(fingers.get("index", "any")),
            middle=FingerState(fingers.get("middle", "any")),
            ring=FingerState(fingers.get("ring", "any")),
            pinky=FingerState(fingers.get("pinky", "any")),
            min_confidence=data.get("min_confidence", 0.6),
            constraints=data.get("constraints", []),
        )


class GestureRegistry:
    """Registry of gesture definitions with matching logic."""

    def __init__(self):
        self._gestures: list[GestureDefinition] = []

    def register(self, gesture: GestureDefinition):
        """Add a gesture definition to the registry."""
        self._gestures.append(gesture)

    def match(
        self, landmarks: np.ndarray
    ) -> Optional[tuple[GestureDefinition, float]]:
        """Find the best matching gesture for given landmarks.

        Returns:
            (gesture, confidence) for the best match, or None if no match.
        """
        best: Optional[tuple[GestureDefinition, float]] = None

        for gesture in self._gestures:
            matched, confidence = gesture.match(landmarks)
            if matched and (best is None or confidence > best[1]):
                best = (gesture, confidence)

        return best

    def load_from_file(self, path: str | Path):
        """Load gesture definitions from a JSON file."""
        with open(path) as f:
            data = json.load(f)

        for entry in data.get("gestures", []):
            self.register(GestureDefinition.from_dict(entry))

    def save_to_file(self, path: str | Path):
        """Save all gesture definitions to a JSON file."""
        data = {"gestures": [g.to_dict() for g in self._gestures]}
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def with_defaults(cls) -> GestureRegistry:
        """Create a registry with common built-in gestures."""
        registry = cls()

        registry.register(GestureDefinition(
            name="open_hand",
            thumb=FingerState.EXTENDED,
            index=FingerState.EXTENDED,
            middle=FingerState.EXTENDED,
            ring=FingerState.EXTENDED,
            pinky=FingerState.EXTENDED,
        ))

        registry.register(GestureDefinition(
            name="fist",
            thumb=FingerState.CURLED,
            index=FingerState.CURLED,
            middle=FingerState.CURLED,
            ring=FingerState.CURLED,
            pinky=FingerState.CURLED,
        ))

        registry.register(GestureDefinition(
            name="thumbs_up",
            thumb=FingerState.EXTENDED,
            index=FingerState.CURLED,
            middle=FingerState.CURLED,
            ring=FingerState.CURLED,
            pinky=FingerState.CURLED,
        ))

        registry.register(GestureDefinition(
            name="peace",
            thumb=FingerState.CURLED,
            index=FingerState.EXTENDED,
            middle=FingerState.EXTENDED,
            ring=FingerState.CURLED,
            pinky=FingerState.CURLED,
        ))

        registry.register(GestureDefinition(
            name="pointing",
            thumb=FingerState.CURLED,
            index=FingerState.EXTENDED,
            middle=FingerState.CURLED,
            ring=FingerState.CURLED,
            pinky=FingerState.CURLED,
        ))

        registry.register(GestureDefinition(
            name="rock_on",
            thumb=FingerState.CURLED,
            index=FingerState.EXTENDED,
            middle=FingerState.CURLED,
            ring=FingerState.CURLED,
            pinky=FingerState.EXTENDED,
        ))

        registry.register(GestureDefinition(
            name="ok_sign",
            thumb=FingerState.EXTENDED,
            index=FingerState.EXTENDED,
            middle=FingerState.EXTENDED,
            ring=FingerState.EXTENDED,
            pinky=FingerState.EXTENDED,
            min_confidence=0.5,
            constraints=[{
                "type": "distance",
                "landmarks": [4, 8],
                "min": 0.0,
                "max": 0.15,
            }],
        ))

        return registry

    def __len__(self) -> int:
        return len(self._gestures)

    def __iter__(self):
        return iter(self._gestures)
