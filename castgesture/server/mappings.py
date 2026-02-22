"""Gesture-to-effect mapping system with YAML config."""

import yaml
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field
import time


@dataclass
class GestureMapping:
    gesture: str
    effect: str
    params: dict = field(default_factory=dict)
    sound: Optional[str] = None
    cooldown: float = 0.5  # seconds


@dataclass
class SequenceMapping:
    gestures: list[str]       # ordered gesture sequence
    effect: str
    params: dict = field(default_factory=dict)
    sound: Optional[str] = None
    timeout: float = 1.0     # max time between gestures
    cooldown: float = 1.0


class MappingEngine:
    def __init__(self, config_path: Optional[str] = None):
        self.mappings: dict[str, GestureMapping] = {}
        self.sequences: list[SequenceMapping] = []
        self._sequence_state: list[tuple[str, float]] = []
        self._last_triggered: dict[str, float] = {}

        if config_path:
            self.load(config_path)

    def load(self, path: str):
        data = yaml.safe_load(Path(path).read_text())
        self.mappings.clear()
        self.sequences.clear()

        for item in data.get("mappings", []):
            m = GestureMapping(
                gesture=item["gesture"],
                effect=item["effect"],
                params=item.get("params", {}),
                sound=item.get("sound"),
                cooldown=item.get("cooldown", 0.5),
            )
            self.mappings[m.gesture] = m

        for item in data.get("sequences", []):
            s = SequenceMapping(
                gestures=item["gestures"],
                effect=item["effect"],
                params=item.get("params", {}),
                sound=item.get("sound"),
                timeout=item.get("timeout", 1.0),
                cooldown=item.get("cooldown", 1.0),
            )
            self.sequences.append(s)

    def save(self, path: str):
        data = {
            "mappings": [
                {"gesture": m.gesture, "effect": m.effect, "params": m.params, "sound": m.sound, "cooldown": m.cooldown}
                for m in self.mappings.values()
            ],
            "sequences": [
                {"gestures": s.gestures, "effect": s.effect, "params": s.params, "sound": s.sound, "timeout": s.timeout, "cooldown": s.cooldown}
                for s in self.sequences
            ],
        }
        Path(path).write_text(yaml.dump(data, default_flow_style=False))

    def process_gesture(self, gesture: str, hand_x: float = 0.5, hand_y: float = 0.5) -> list[dict]:
        """Process a detected gesture, return list of effect events to fire."""
        now = time.time()
        events = []

        # Check sequences first
        self._sequence_state.append((gesture, now))
        # Prune old entries
        self._sequence_state = [(g, t) for g, t in self._sequence_state if now - t < 3.0]

        for seq in self.sequences:
            recent = [g for g, t in self._sequence_state[-len(seq.gestures):]]
            if recent == seq.gestures:
                key = f"seq_{'_'.join(seq.gestures)}"
                if now - self._last_triggered.get(key, 0) >= seq.cooldown:
                    self._last_triggered[key] = now
                    params = {**seq.params, "x": hand_x, "y": hand_y}
                    events.append({"type": "effect", "effect": seq.effect, "params": params, "sound": seq.sound})
                    self._sequence_state.clear()
                    return events

        # Check single gesture mappings
        if gesture in self.mappings:
            m = self.mappings[gesture]
            if now - self._last_triggered.get(gesture, 0) >= m.cooldown:
                self._last_triggered[gesture] = now
                params = {**m.params, "x": hand_x, "y": hand_y}
                events.append({"type": "effect", "effect": m.effect, "params": params, "sound": m.sound})

        return events

    def get_mappings_dict(self) -> dict:
        return {
            "mappings": {k: {"effect": v.effect, "params": v.params, "sound": v.sound, "cooldown": v.cooldown}
                         for k, v in self.mappings.items()},
            "sequences": [{"gestures": s.gestures, "effect": s.effect, "params": s.params} for s in self.sequences],
        }

    def update_mapping(self, gesture: str, effect: str, params: dict = None, sound: str = None):
        self.mappings[gesture] = GestureMapping(gesture=gesture, effect=effect, params=params or {}, sound=sound)

    def remove_mapping(self, gesture: str):
        self.mappings.pop(gesture, None)
