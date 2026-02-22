"""Tests for YAML mapping load, gesture→effect resolution."""
import pytest
import tempfile
import os
from pathlib import Path
from castgesture.server.mappings import MappingEngine, GestureMapping, SequenceMapping


FIXTURES_DIR = Path(__file__).parent.parent / "config"
DEFAULT_MAPPINGS = str(FIXTURES_DIR / "default_mappings.yml")


class TestMappingLoad:
    def test_load_default_mappings(self):
        engine = MappingEngine(DEFAULT_MAPPINGS)
        assert len(engine.mappings) > 0

    def test_all_default_gestures_present(self):
        engine = MappingEngine(DEFAULT_MAPPINGS)
        expected = {"open_hand", "fist", "peace", "thumbs_up", "pointing", "rock_on", "ok_sign"}
        assert set(engine.mappings.keys()) == expected

    def test_sequences_loaded(self):
        engine = MappingEngine(DEFAULT_MAPPINGS)
        assert len(engine.sequences) == 2
        assert engine.sequences[0].gestures == ["fist", "open_hand"]

    def test_mapping_fields(self):
        engine = MappingEngine(DEFAULT_MAPPINGS)
        m = engine.mappings["open_hand"]
        assert m.effect == "confetti"
        assert m.cooldown == 1.0
        assert m.sound == "pop"
        assert "intensity" in m.params


class TestGestureResolution:
    def setup_method(self):
        self.engine = MappingEngine(DEFAULT_MAPPINGS)

    def test_single_gesture(self):
        events = self.engine.process_gesture("open_hand", 0.5, 0.5)
        assert len(events) == 1
        assert events[0]["effect"] == "confetti"
        assert events[0]["params"]["x"] == 0.5

    def test_unknown_gesture(self):
        events = self.engine.process_gesture("unknown_gesture")
        assert events == []

    def test_cooldown(self):
        events1 = self.engine.process_gesture("fist")
        assert len(events1) == 1
        # Immediate second call should be blocked by cooldown
        events2 = self.engine.process_gesture("fist")
        assert events2 == []

    def test_different_gestures_no_cooldown_conflict(self):
        events1 = self.engine.process_gesture("fist")
        events2 = self.engine.process_gesture("peace")
        assert len(events1) == 1
        assert len(events2) == 1


class TestMappingCRUD:
    def test_update_mapping(self):
        engine = MappingEngine()
        engine.update_mapping("wave", "confetti", {"intensity": 2.0})
        assert "wave" in engine.mappings
        assert engine.mappings["wave"].effect == "confetti"

    def test_remove_mapping(self):
        engine = MappingEngine(DEFAULT_MAPPINGS)
        engine.remove_mapping("fist")
        assert "fist" not in engine.mappings

    def test_remove_nonexistent(self):
        engine = MappingEngine()
        engine.remove_mapping("nonexistent")  # Should not raise

    def test_get_mappings_dict(self):
        engine = MappingEngine(DEFAULT_MAPPINGS)
        d = engine.get_mappings_dict()
        assert "mappings" in d
        assert "sequences" in d
        assert "open_hand" in d["mappings"]


class TestSaveLoad:
    def test_roundtrip(self):
        engine = MappingEngine(DEFAULT_MAPPINGS)
        with tempfile.NamedTemporaryFile(suffix=".yml", delete=False, mode="w") as f:
            tmp = f.name
        try:
            engine.save(tmp)
            engine2 = MappingEngine(tmp)
            assert set(engine2.mappings.keys()) == set(engine.mappings.keys())
            assert len(engine2.sequences) == len(engine.sequences)
        finally:
            os.unlink(tmp)
