"""Gesture recording and replay — capture landmark sequences to disk.

Record real gesture sessions for:
- Reproducible testing without a camera
- CI pipelines on headless machines
- Demo recordings that play back deterministically
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterator, Optional

import numpy as np


@dataclass
class RecordedFrame:
    """A single frame in a recording."""
    timestamp: float  # seconds from recording start
    hands: list[list[list[float]]]  # list of (21, 3) landmarks as nested lists
    gestures: list[dict]  # [{name, confidence, hand_index}, ...]


class GestureRecorder:
    """Records landmark data and gesture events to a file.

    Usage:
        recorder = GestureRecorder()
        recorder.start()
        # In your frame loop:
        recorder.add_frame(hands, gestures)
        # When done:
        recorder.save("session.json")
    """

    def __init__(self):
        self._frames: list[RecordedFrame] = []
        self._start_time: Optional[float] = None
        self._recording = False

    def start(self):
        """Begin a new recording session."""
        self._frames = []
        self._start_time = time.monotonic()
        self._recording = True

    def stop(self) -> int:
        """Stop recording. Returns number of frames captured."""
        self._recording = False
        return len(self._frames)

    @property
    def is_recording(self) -> bool:
        return self._recording

    @property
    def frame_count(self) -> int:
        return len(self._frames)

    @property
    def duration(self) -> float:
        """Duration of recording in seconds."""
        if not self._frames:
            return 0.0
        return self._frames[-1].timestamp

    def add_frame(
        self,
        hands: list[np.ndarray],
        gestures: Optional[list[dict]] = None,
    ):
        """Add a frame to the recording.

        Args:
            hands: List of landmark arrays, each shape (21, 3).
            gestures: Optional list of gesture dicts with name/confidence/hand_index.
        """
        if not self._recording:
            return

        timestamp = time.monotonic() - self._start_time
        hands_list = [h.tolist() for h in hands]

        self._frames.append(RecordedFrame(
            timestamp=timestamp,
            hands=hands_list,
            gestures=gestures or [],
        ))

    def save(self, path: str | Path):
        """Save recording to JSON file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "version": 1,
            "frame_count": len(self._frames),
            "duration": self.duration,
            "frames": [asdict(f) for f in self._frames],
        }

        with open(path, "w") as f:
            json.dump(data, f)

    def save_compact(self, path: str | Path):
        """Save in compact binary format (numpy npz) for smaller files."""
        path = Path(path).with_suffix(".npz")
        path.parent.mkdir(parents=True, exist_ok=True)

        timestamps = np.array([f.timestamp for f in self._frames], dtype=np.float32)
        # Store gesture info as JSON string
        gesture_data = json.dumps([f.gestures for f in self._frames])
        # Flatten hands per frame (variable number of hands, pad to max)
        max_hands = max((len(f.hands) for f in self._frames), default=0)
        if max_hands == 0:
            hands_array = np.zeros((len(self._frames), 1, 21, 3), dtype=np.float32)
            hand_counts = np.zeros(len(self._frames), dtype=np.int32)
        else:
            hands_array = np.zeros((len(self._frames), max_hands, 21, 3), dtype=np.float32)
            hand_counts = np.array([len(f.hands) for f in self._frames], dtype=np.int32)
            for i, f in enumerate(self._frames):
                for j, h in enumerate(f.hands):
                    hands_array[i, j] = np.array(h, dtype=np.float32)

        np.savez_compressed(
            path,
            timestamps=timestamps,
            hands=hands_array,
            hand_counts=hand_counts,
            gesture_data=np.array([gesture_data]),
        )


class GesturePlayer:
    """Replays a recorded gesture session.

    Usage:
        player = GesturePlayer.load("session.json")
        for frame in player.play():
            # frame.hands is list of np arrays
            pipeline.process_landmarks(frame.hands)

        # Or replay at original speed:
        for frame in player.play_realtime():
            ...
    """

    def __init__(self, frames: list[RecordedFrame]):
        self._frames = frames

    @classmethod
    def load(cls, path: str | Path) -> GesturePlayer:
        """Load recording from JSON file."""
        path = Path(path)

        if path.suffix == ".npz":
            return cls._load_compact(path)

        with open(path) as f:
            data = json.load(f)

        frames = [
            RecordedFrame(
                timestamp=f["timestamp"],
                hands=f["hands"],
                gestures=f.get("gestures", []),
            )
            for f in data["frames"]
        ]
        return cls(frames)

    @classmethod
    def _load_compact(cls, path: Path) -> GesturePlayer:
        """Load from compact npz format."""
        data = np.load(path, allow_pickle=False)
        timestamps = data["timestamps"]
        hands_array = data["hands"]
        hand_counts = data["hand_counts"]
        gesture_data = json.loads(str(data["gesture_data"][0]))

        frames = []
        for i in range(len(timestamps)):
            n_hands = int(hand_counts[i])
            hands = [hands_array[i, j].tolist() for j in range(n_hands)]
            frames.append(RecordedFrame(
                timestamp=float(timestamps[i]),
                hands=hands,
                gestures=gesture_data[i] if i < len(gesture_data) else [],
            ))
        return cls(frames)

    @property
    def frame_count(self) -> int:
        return len(self._frames)

    @property
    def duration(self) -> float:
        if not self._frames:
            return 0.0
        return self._frames[-1].timestamp

    def play(self) -> Iterator[RecordedFrame]:
        """Iterate through all frames instantly (no timing)."""
        for frame in self._frames:
            # Convert hands back to numpy
            frame_copy = RecordedFrame(
                timestamp=frame.timestamp,
                hands=[np.array(h, dtype=np.float32) for h in frame.hands] if frame.hands else [],
                gestures=frame.gestures,
            )
            yield frame_copy

    def play_realtime(self, speed: float = 1.0) -> Iterator[RecordedFrame]:
        """Replay at original timing (or scaled by speed factor).

        Args:
            speed: Playback speed multiplier (2.0 = double speed).
        """
        if not self._frames:
            return

        start = time.monotonic()

        for frame in self.play():
            target_time = frame.timestamp / speed
            elapsed = time.monotonic() - start
            if target_time > elapsed:
                time.sleep(target_time - elapsed)
            yield frame

    def get_frame(self, index: int) -> Optional[RecordedFrame]:
        """Get a specific frame by index."""
        if 0 <= index < len(self._frames):
            f = self._frames[index]
            return RecordedFrame(
                timestamp=f.timestamp,
                hands=[np.array(h, dtype=np.float32) for h in f.hands] if f.hands else [],
                gestures=f.gestures,
            )
        return None
