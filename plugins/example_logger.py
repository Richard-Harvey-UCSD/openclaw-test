"""Example GestureEngine plugin — gesture event logger.

This plugin logs all gesture events to a file and keeps running counts.
Drop this file in the plugins/ directory to auto-load it.

Demonstrates:
- Subclassing GesturePlugin
- Handling multiple event types
- Using on_startup/on_shutdown lifecycle
- Registering gesture-specific handlers via decorator
"""

from __future__ import annotations

import json
import logging
from collections import Counter
from pathlib import Path

from gesture_engine.plugins import GesturePlugin, PluginEvent

logger = logging.getLogger("gesture_engine.plugins.example_logger")


class EventLoggerPlugin(GesturePlugin):
    """Logs gesture events to a file with running statistics."""

    name = "event_logger"
    version = "1.0.0"
    description = "Logs all gesture events to a JSON-lines file with counts"

    def __init__(self):
        super().__init__()
        self._counts: Counter = Counter()
        self._log_path: Path = Path("gesture_events.jsonl")
        self._log_file = None

        # Register specific gesture handlers via decorator
        @self.handler("thumbs_up")
        def on_thumbs_up(event: PluginEvent):
            logger.info("👍 Thumbs up detected! (total: %d)", self._counts["thumbs_up"])

        @self.handler("peace")
        def on_peace(event: PluginEvent):
            logger.info("✌️ Peace sign! (total: %d)", self._counts["peace"])

    def on_startup(self, context: dict):
        """Open the log file."""
        try:
            self._log_file = open(self._log_path, "a")
            logger.info("EventLogger: writing to %s", self._log_path)
        except OSError as e:
            logger.warning("EventLogger: could not open log file: %s", e)

    def on_shutdown(self):
        """Close log file and print summary."""
        if self._log_file:
            self._log_file.close()
        if self._counts:
            logger.info("EventLogger summary: %s", dict(self._counts))

    def on_gesture(self, event: PluginEvent):
        """Log every gesture event."""
        self._counts[event.name] += 1
        self._write_log(event)
        super().on_gesture(event)  # dispatch to decorator handlers

    def on_sequence(self, event: PluginEvent):
        """Log sequence events."""
        self._counts[f"seq:{event.name}"] += 1
        self._write_log(event)

    def on_trajectory(self, event: PluginEvent):
        """Log trajectory events."""
        self._counts[f"traj:{event.name}"] += 1
        self._write_log(event)

    def on_bimanual(self, event: PluginEvent):
        """Log bimanual events."""
        self._counts[f"bi:{event.name}"] += 1
        self._write_log(event)

    def _write_log(self, event: PluginEvent):
        """Append event to JSONL log file."""
        if not self._log_file:
            return
        try:
            record = {
                "type": event.type,
                "name": event.name,
                "timestamp": event.timestamp,
                "data": {k: v for k, v in event.data.items() if isinstance(v, (str, int, float, bool))},
            }
            self._log_file.write(json.dumps(record) + "\n")
            self._log_file.flush()
        except Exception:
            pass

    @property
    def counts(self) -> dict[str, int]:
        """Get current gesture counts."""
        return dict(self._counts)
