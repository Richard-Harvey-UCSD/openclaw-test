"""GestureEngine - Real-time on-device hand gesture recognition."""

__version__ = "0.4.0"

from gesture_engine.detector import HandDetector
from gesture_engine.classifier import GestureClassifier
from gesture_engine.pipeline import GesturePipeline, GestureEvent
from gesture_engine.gestures import GestureDefinition, GestureRegistry
from gesture_engine.sequences import SequenceDetector, GestureSequence, SequenceEvent
from gesture_engine.recorder import GestureRecorder, GesturePlayer
from gesture_engine.profiler import PipelineProfiler
from gesture_engine.actions import ActionMapper, Action, ActionType
from gesture_engine.trajectory import TrajectoryTracker, TrajectoryTemplate, TrajectoryEvent
from gesture_engine.bimanual import BimanualDetector, BimanualEvent
from gesture_engine.canvas import DrawingCanvas, DrawCommand
from gesture_engine.plugins import GesturePlugin, PluginManager, PluginEvent
from gesture_engine.metrics import MetricsCollector
