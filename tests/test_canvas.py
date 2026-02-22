"""Tests for finger painting / air drawing canvas."""

import numpy as np
import pytest

from gesture_engine.canvas import DrawingCanvas, DrawCommand, GESTURE_COLORS


def _make_landmarks(tip_x: float = 0.5, tip_y: float = 0.5) -> np.ndarray:
    """Create landmarks with index fingertip at given position."""
    lm = np.zeros((21, 3), dtype=np.float32)
    lm[8] = [tip_x, tip_y, 0]  # index fingertip
    return lm


class TestDrawCommand:
    def test_line_to_dict(self):
        cmd = DrawCommand(type="line", x=0.1, y=0.2, x2=0.3, y2=0.4, color="#fff", width=2)
        d = cmd.to_dict()
        assert d["type"] == "line"
        assert d["x1"] == 0.1
        assert d["color"] == "#fff"

    def test_clear_to_dict(self):
        cmd = DrawCommand(type="clear")
        assert cmd.to_dict() == {"type": "clear"}

    def test_erase_to_dict(self):
        cmd = DrawCommand(type="erase", x=0.5, y=0.5, radius=20)
        d = cmd.to_dict()
        assert d["type"] == "erase"
        assert d["radius"] == 20


class TestDrawingCanvas:
    def test_draw_line(self):
        canvas = DrawingCanvas(smoothing=1)
        lm1 = _make_landmarks(0.1, 0.5)
        lm2 = _make_landmarks(0.5, 0.5)

        # First frame: sets start point
        cmds1 = canvas.update(lm1, "pointing", 0.0)
        # Second frame: draws line
        cmds2 = canvas.update(lm2, "pointing", 0.1)
        line_cmds = [c for c in cmds2 if c.type == "line"]
        assert len(line_cmds) >= 1

    def test_erase_on_fist(self):
        canvas = DrawingCanvas()
        lm = _make_landmarks(0.5, 0.5)
        cmds = canvas.update(lm, "fist", 0.0)
        erase_cmds = [c for c in cmds if c.type == "erase"]
        assert len(erase_cmds) == 1

    def test_color_change(self):
        canvas = DrawingCanvas(smoothing=1)
        lm = _make_landmarks(0.3, 0.3)
        cmds = canvas.update(lm, "peace", 0.0)
        color_cmds = [c for c in cmds if c.type == "color"]
        assert len(color_cmds) >= 1
        assert color_cmds[0].color == "#22c55e"

    def test_clear(self):
        canvas = DrawingCanvas()
        canvas.update(_make_landmarks(), "pointing", 0.0)
        canvas.clear()
        state = canvas.get_full_state()
        assert any(c["type"] == "clear" for c in state)

    def test_no_draw_on_unknown_gesture(self):
        canvas = DrawingCanvas()
        cmds = canvas.update(_make_landmarks(), "open_hand", 0.0)
        line_cmds = [c for c in cmds if c.type == "line"]
        assert len(line_cmds) == 0

    def test_full_state(self):
        canvas = DrawingCanvas(smoothing=1)
        canvas.update(_make_landmarks(0.1, 0.1), "pointing", 0.0)
        canvas.update(_make_landmarks(0.5, 0.5), "pointing", 0.1)
        state = canvas.get_full_state()
        assert isinstance(state, list)
