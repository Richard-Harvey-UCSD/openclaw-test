"""Multi-gesture sequence detection.

Detects ordered gesture transitions like fist→open_hand ("release")
or peace→fist ("grab"). Sequences are time-bounded — all gestures
in the sequence must occur within a configurable window.
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class GestureSequence:
    """A named sequence of gestures that triggers a compound event."""
    name: str
    gestures: list[str]  # ordered list of gesture names
    max_duration: float = 2.0  # max seconds for full sequence
    description: str = ""


@dataclass
class SequenceEvent:
    """Fired when a complete gesture sequence is detected."""
    sequence_name: str
    gestures: list[str]
    duration: float  # how long the sequence took
    timestamp: float


class SequenceDetector:
    """Detects multi-gesture sequences from a stream of gesture names.

    Maintains a rolling buffer of recent gestures per hand and checks
    for registered sequence patterns.
    """

    def __init__(self, max_history: int = 20):
        self._sequences: list[GestureSequence] = []
        self._history: dict[int, deque] = {}  # hand_index → (gesture, time)
        self._max_history = max_history
        self._last_triggered: dict[tuple[int, str], float] = {}
        self._cooldown = 1.0  # seconds between same sequence triggers

    def register(self, sequence: GestureSequence):
        """Add a sequence to watch for."""
        self._sequences.append(sequence)

    def feed(self, gesture: str, hand_index: int = 0, timestamp: Optional[float] = None) -> list[SequenceEvent]:
        """Feed a new gesture observation and check for completed sequences.

        Only feeds when the gesture *changes* from the last observed gesture
        for that hand (ignores repeated same-gesture events).

        Returns:
            List of triggered sequence events (usually 0 or 1).
        """
        now = timestamp if timestamp is not None else time.monotonic()

        if hand_index not in self._history:
            self._history[hand_index] = deque(maxlen=self._max_history)

        history = self._history[hand_index]

        # Only record transitions (ignore repeated same gesture)
        if history and history[-1][0] == gesture:
            return []

        history.append((gesture, now))

        # Check sequences
        events = []
        for seq in self._sequences:
            if self._check_sequence(seq, history, hand_index, now):
                event = SequenceEvent(
                    sequence_name=seq.name,
                    gestures=list(seq.gestures),
                    duration=self._last_match_duration,
                    timestamp=now,
                )
                events.append(event)

        return events

    def _check_sequence(self, seq: GestureSequence, history: deque, hand_index: int, now: float) -> bool:
        """Check if the tail of history matches a sequence pattern."""
        pattern = seq.gestures
        if len(history) < len(pattern):
            return False

        # Cooldown
        key = (hand_index, seq.name)
        if key in self._last_triggered:
            last = self._last_triggered[key]
            if now - last < self._cooldown:
                return False

        # Check last N entries match pattern
        tail = list(history)[-len(pattern):]
        for (gesture, _ts), expected in zip(tail, pattern):
            if gesture != expected:
                return False

        # Check duration constraint
        duration = tail[-1][1] - tail[0][1]
        if duration > seq.max_duration:
            return False

        self._last_match_duration = duration
        self._last_triggered[key] = now
        return True

    def reset(self, hand_index: Optional[int] = None):
        """Clear history for one or all hands."""
        if hand_index is not None:
            self._history.pop(hand_index, None)
        else:
            self._history.clear()
            self._last_triggered.clear()

    @classmethod
    def with_defaults(cls) -> SequenceDetector:
        """Create detector with built-in gesture sequences."""
        detector = cls()

        detector.register(GestureSequence(
            name="release",
            gestures=["fist", "open_hand"],
            max_duration=1.5,
            description="Open hand from fist — release/drop action",
        ))

        detector.register(GestureSequence(
            name="grab",
            gestures=["open_hand", "fist"],
            max_duration=1.5,
            description="Close hand — grab/pick up action",
        ))

        detector.register(GestureSequence(
            name="pinch_release",
            gestures=["ok_sign", "open_hand"],
            max_duration=1.5,
            description="Release from pinch grip",
        ))

        detector.register(GestureSequence(
            name="peace_out",
            gestures=["peace", "fist"],
            max_duration=2.0,
            description="Peace sign then close — dismiss/exit",
        ))

        detector.register(GestureSequence(
            name="wave",
            gestures=["open_hand", "fist", "open_hand"],
            max_duration=2.0,
            description="Quick open-close-open — wave gesture",
        ))

        detector.register(GestureSequence(
            name="point_and_click",
            gestures=["pointing", "fist"],
            max_duration=1.5,
            description="Point then click — selection action",
        ))

        return detector
