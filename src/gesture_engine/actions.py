"""Gesture-to-action mapping system.

Maps gestures and sequences to arbitrary actions:
- Keyboard shortcuts (via subprocess / xdotool)
- Shell commands
- HTTP webhooks
- OSC messages

Configuration via YAML file.
"""

from __future__ import annotations

import asyncio
import logging
import subprocess
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import yaml

logger = logging.getLogger("gesture_engine.actions")


class ActionType(Enum):
    KEYBOARD = "keyboard"
    SHELL = "shell"
    WEBHOOK = "webhook"
    OSC = "osc"
    LOG = "log"


@dataclass
class Action:
    """A single action to execute when a gesture is detected."""
    type: ActionType
    params: dict[str, Any] = field(default_factory=dict)
    cooldown: float = 0.0  # minimum seconds between triggers
    description: str = ""

    def to_dict(self) -> dict:
        return {
            "type": self.type.value,
            "params": self.params,
            "cooldown": self.cooldown,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Action:
        return cls(
            type=ActionType(data["type"]),
            params=data.get("params", {}),
            cooldown=data.get("cooldown", 0.0),
            description=data.get("description", ""),
        )


@dataclass
class GestureMapping:
    """Maps a gesture or sequence name to one or more actions."""
    trigger: str  # gesture name or sequence name
    actions: list[Action]
    min_confidence: float = 0.7
    enabled: bool = True


class ActionExecutor:
    """Executes actions triggered by gesture events."""

    def __init__(self):
        self._last_triggered: dict[str, float] = {}
        self._http_session = None

    async def execute(self, action: Action, context: dict | None = None) -> bool:
        """Execute a single action. Returns True on success."""
        # Cooldown check
        key = f"{action.type.value}:{id(action)}"
        now = time.monotonic()
        if action.cooldown > 0:
            last = self._last_triggered.get(key, 0)
            if now - last < action.cooldown:
                return False
        self._last_triggered[key] = now

        try:
            if action.type == ActionType.KEYBOARD:
                return await self._exec_keyboard(action.params)
            elif action.type == ActionType.SHELL:
                return await self._exec_shell(action.params)
            elif action.type == ActionType.WEBHOOK:
                return await self._exec_webhook(action.params, context)
            elif action.type == ActionType.OSC:
                return await self._exec_osc(action.params)
            elif action.type == ActionType.LOG:
                logger.info(
                    "Action LOG: %s (context: %s)",
                    action.params.get("message", "gesture triggered"),
                    context,
                )
                return True
        except Exception as e:
            logger.error("Action %s failed: %s", action.type.value, e)
            return False

        return False

    async def _exec_keyboard(self, params: dict) -> bool:
        """Send keyboard shortcut via xdotool."""
        keys = params.get("keys", "")
        if not keys:
            return False

        proc = await asyncio.create_subprocess_exec(
            "xdotool", "key", keys,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            logger.warning("xdotool failed: %s", stderr.decode().strip())
            return False
        return True

    async def _exec_shell(self, params: dict) -> bool:
        """Run a shell command."""
        command = params.get("command", "")
        if not command:
            return False

        timeout = params.get("timeout", 10)
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=timeout
            )
            logger.debug("Shell [%s] → rc=%d", command, proc.returncode)
            return proc.returncode == 0
        except asyncio.TimeoutError:
            proc.kill()
            logger.warning("Shell command timed out: %s", command)
            return False

    async def _exec_webhook(self, params: dict, context: dict | None) -> bool:
        """Send HTTP POST to a webhook URL."""
        url = params.get("url", "")
        if not url:
            return False

        try:
            import aiohttp
        except ImportError:
            # Fallback to synchronous request
            import urllib.request
            import json

            payload = {**(params.get("body", {})), "context": context or {}}
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=5) as resp:
                    return 200 <= resp.status < 300
            except Exception as e:
                logger.warning("Webhook failed: %s", e)
                return False

        if self._http_session is None:
            self._http_session = aiohttp.ClientSession()

        payload = {**(params.get("body", {})), "context": context or {}}
        headers = params.get("headers", {"Content-Type": "application/json"})

        async with self._http_session.post(url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=5)) as resp:
            return 200 <= resp.status < 300

    async def _exec_osc(self, params: dict) -> bool:
        """Send OSC message."""
        address = params.get("address", "/gesture")
        host = params.get("host", "127.0.0.1")
        port = params.get("port", 9000)
        args = params.get("args", [])

        try:
            from pythonosc.udp_client import SimpleUDPClient
            client = SimpleUDPClient(host, port)
            client.send_message(address, args)
            return True
        except ImportError:
            logger.warning("python-osc not installed, skipping OSC action")
            return False
        except Exception as e:
            logger.warning("OSC send failed: %s", e)
            return False

    async def close(self):
        """Clean up resources."""
        if self._http_session:
            await self._http_session.close()
            self._http_session = None


class ActionMapper:
    """Manages gesture-to-action mappings and dispatches events.

    Load mappings from YAML:
        mapper = ActionMapper.from_yaml("actions.yml")

    Dispatch on gesture:
        await mapper.on_gesture("thumbs_up", confidence=0.9)
    """

    def __init__(self):
        self._mappings: dict[str, GestureMapping] = {}
        self._executor = ActionExecutor()

    def add_mapping(self, mapping: GestureMapping):
        """Register a gesture-to-action mapping."""
        self._mappings[mapping.trigger] = mapping

    async def on_gesture(
        self, gesture: str, confidence: float = 1.0, context: dict | None = None
    ) -> list[bool]:
        """Dispatch actions for a gesture event. Returns list of success bools."""
        mapping = self._mappings.get(gesture)
        if not mapping or not mapping.enabled:
            return []

        if confidence < mapping.min_confidence:
            return []

        ctx = {"gesture": gesture, "confidence": confidence, **(context or {})}
        results = []
        for action in mapping.actions:
            ok = await self._executor.execute(action, ctx)
            results.append(ok)
        return results

    async def on_sequence(
        self, sequence_name: str, context: dict | None = None
    ) -> list[bool]:
        """Dispatch actions for a sequence event."""
        return await self.on_gesture(sequence_name, confidence=1.0, context=context)

    @classmethod
    def from_yaml(cls, path: str | Path) -> ActionMapper:
        """Load mappings from a YAML config file."""
        with open(path) as f:
            config = yaml.safe_load(f)

        mapper = cls()
        for entry in config.get("mappings", []):
            actions = [Action.from_dict(a) for a in entry.get("actions", [])]
            mapping = GestureMapping(
                trigger=entry["trigger"],
                actions=actions,
                min_confidence=entry.get("min_confidence", 0.7),
                enabled=entry.get("enabled", True),
            )
            mapper.add_mapping(mapping)

        return mapper

    def to_yaml(self, path: str | Path):
        """Save current mappings to YAML."""
        entries = []
        for mapping in self._mappings.values():
            entries.append({
                "trigger": mapping.trigger,
                "min_confidence": mapping.min_confidence,
                "enabled": mapping.enabled,
                "actions": [a.to_dict() for a in mapping.actions],
            })

        with open(path, "w") as f:
            yaml.dump({"mappings": entries}, f, default_flow_style=False, sort_keys=False)

    async def close(self):
        await self._executor.close()

    @property
    def triggers(self) -> list[str]:
        return list(self._mappings.keys())
