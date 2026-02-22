"""Tests for effect registry, triggering, and config loading."""
import pytest
from castgesture.server.effects import (
    build_effect_event, EFFECT_DEFAULTS, EffectType, EffectParams,
)


class TestEffectDefaults:
    def test_all_effect_types_have_defaults(self):
        for et in EffectType:
            assert et.value in EFFECT_DEFAULTS, f"Missing defaults for {et.value}"

    def test_defaults_have_duration(self):
        for name, params in EFFECT_DEFAULTS.items():
            assert "duration" in params, f"{name} missing duration"

    def test_defaults_have_intensity_or_text(self):
        for name, params in EFFECT_DEFAULTS.items():
            assert "intensity" in params or "text" in params or "emoji" in params, (
                f"{name} missing intensity/text/emoji"
            )


class TestBuildEffectEvent:
    def test_basic_build(self):
        event = build_effect_event("confetti")
        assert event["type"] == "effect"
        assert event["effect"] == "confetti"
        assert "params" in event

    def test_merge_params(self):
        event = build_effect_event("confetti", {"intensity": 2.0, "custom": True})
        assert event["params"]["intensity"] == 2.0
        assert event["params"]["custom"] is True
        # Should still have defaults merged in
        assert "particle_count" in event["params"]

    def test_unknown_effect(self):
        event = build_effect_event("nonexistent", {"foo": "bar"})
        assert event["effect"] == "nonexistent"
        assert event["params"]["foo"] == "bar"

    def test_no_params(self):
        event = build_effect_event("fire")
        assert event["params"]["duration"] == 3.0

    def test_override_default(self):
        event = build_effect_event("fire", {"duration": 10.0})
        assert event["params"]["duration"] == 10.0


class TestEffectParams:
    def test_default_values(self):
        p = EffectParams()
        assert p.duration == 2.0
        assert p.intensity == 1.0
        assert len(p.colors) == 5

    def test_custom_values(self):
        p = EffectParams(duration=5.0, text="GG!")
        assert p.duration == 5.0
        assert p.text == "GG!"
