"""Tests for gesture recording and replay."""

import numpy as np
import pytest

from gesture_engine.recorder import GestureRecorder, GesturePlayer, RecordedFrame


def make_hands(n=1):
    return [np.random.randn(21, 3).astype(np.float32) for _ in range(n)]


class TestRecorder:
    def test_record_and_count(self):
        rec = GestureRecorder()
        rec.start()
        for _ in range(10):
            rec.add_frame(make_hands())
        count = rec.stop()
        assert count == 10

    def test_not_recording_ignores_frames(self):
        rec = GestureRecorder()
        rec.add_frame(make_hands())
        assert rec.frame_count == 0

    def test_save_and_load_json(self, tmp_path):
        rec = GestureRecorder()
        rec.start()
        hands = make_hands(2)
        rec.add_frame(hands, [{"name": "fist", "confidence": 0.9, "hand_index": 0}])
        rec.add_frame(make_hands())
        rec.stop()

        path = tmp_path / "test.json"
        rec.save(path)

        player = GesturePlayer.load(path)
        assert player.frame_count == 2

    def test_save_and_load_npz(self, tmp_path):
        rec = GestureRecorder()
        rec.start()
        for _ in range(5):
            rec.add_frame(make_hands())
        rec.stop()

        path = tmp_path / "test.npz"
        rec.save_compact(path)

        player = GesturePlayer.load(path)
        assert player.frame_count == 5

    def test_play_yields_numpy(self, tmp_path):
        rec = GestureRecorder()
        rec.start()
        rec.add_frame(make_hands())
        rec.stop()

        path = tmp_path / "test.json"
        rec.save(path)

        player = GesturePlayer.load(path)
        frames = list(player.play())
        assert len(frames) == 1
        assert isinstance(frames[0].hands[0], np.ndarray)
        assert frames[0].hands[0].shape == (21, 3)

    def test_get_frame(self, tmp_path):
        rec = GestureRecorder()
        rec.start()
        rec.add_frame(make_hands())
        rec.add_frame(make_hands())
        rec.stop()

        path = tmp_path / "test.json"
        rec.save(path)
        player = GesturePlayer.load(path)

        assert player.get_frame(0) is not None
        assert player.get_frame(1) is not None
        assert player.get_frame(5) is None
