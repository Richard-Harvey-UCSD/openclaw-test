"""Tests for the gesture-to-action mapping system."""

import asyncio
import tempfile
from pathlib import Path

import pytest
import yaml

from gesture_engine.actions import (
    Action,
    ActionExecutor,
    ActionMapper,
    ActionType,
    GestureMapping,
)


class TestAction:
    def test_from_dict(self):
        data = {"type": "log", "params": {"message": "hello"}, "cooldown": 1.0}
        action = Action.from_dict(data)
        assert action.type == ActionType.LOG
        assert action.params["message"] == "hello"
        assert action.cooldown == 1.0

    def test_roundtrip(self):
        action = Action(type=ActionType.SHELL, params={"command": "echo hi"})
        restored = Action.from_dict(action.to_dict())
        assert restored.type == action.type
        assert restored.params == action.params


class TestActionExecutor:
    def test_log_action(self):
        executor = ActionExecutor()
        action = Action(type=ActionType.LOG, params={"message": "test"})
        result = asyncio.get_event_loop().run_until_complete(
            executor.execute(action, {"gesture": "thumbs_up"})
        )
        assert result is True

    def test_cooldown(self):
        executor = ActionExecutor()
        action = Action(type=ActionType.LOG, params={"message": "test"}, cooldown=10.0)

        loop = asyncio.get_event_loop()
        r1 = loop.run_until_complete(executor.execute(action))
        r2 = loop.run_until_complete(executor.execute(action))
        assert r1 is True
        assert r2 is False  # blocked by cooldown


class TestActionMapper:
    def test_yaml_roundtrip(self):
        mapper = ActionMapper()
        mapper.add_mapping(GestureMapping(
            trigger="thumbs_up",
            actions=[Action(type=ActionType.LOG, params={"message": "nice"})],
            min_confidence=0.8,
        ))

        with tempfile.NamedTemporaryFile(suffix=".yml", mode="w", delete=False) as f:
            mapper.to_yaml(f.name)
            loaded = ActionMapper.from_yaml(f.name)

        assert "thumbs_up" in loaded.triggers

    def test_on_gesture(self):
        mapper = ActionMapper()
        mapper.add_mapping(GestureMapping(
            trigger="peace",
            actions=[Action(type=ActionType.LOG, params={"message": "peace"})],
            min_confidence=0.5,
        ))

        loop = asyncio.get_event_loop()
        results = loop.run_until_complete(mapper.on_gesture("peace", confidence=0.9))
        assert len(results) == 1
        assert results[0] is True

    def test_below_confidence(self):
        mapper = ActionMapper()
        mapper.add_mapping(GestureMapping(
            trigger="peace",
            actions=[Action(type=ActionType.LOG, params={"message": "peace"})],
            min_confidence=0.9,
        ))

        loop = asyncio.get_event_loop()
        results = loop.run_until_complete(mapper.on_gesture("peace", confidence=0.5))
        assert results == []

    def test_disabled_mapping(self):
        mapper = ActionMapper()
        mapper.add_mapping(GestureMapping(
            trigger="fist",
            actions=[Action(type=ActionType.LOG, params={})],
            enabled=False,
        ))

        loop = asyncio.get_event_loop()
        results = loop.run_until_complete(mapper.on_gesture("fist", confidence=1.0))
        assert results == []
