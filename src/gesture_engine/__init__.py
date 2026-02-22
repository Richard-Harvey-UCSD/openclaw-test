"""GestureEngine - Real-time on-device hand gesture recognition."""

__version__ = "0.2.0"

from gesture_engine.detector import HandDetector
from gesture_engine.classifier import GestureClassifier
from gesture_engine.pipeline import GesturePipeline
from gesture_engine.gestures import GestureDefinition, GestureRegistry
from gesture_engine.sequences import SequenceDetector, GestureSequence, SequenceEvent
from gesture_engine.recorder import GestureRecorder, GesturePlayer
