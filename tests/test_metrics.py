"""Tests for Prometheus metrics."""

import pytest

from gesture_engine.metrics import MetricsCollector


class TestMetricsCollector:
    def test_record_gesture(self):
        m = MetricsCollector()
        m.record_gesture("fist")
        m.record_gesture("fist")
        m.record_gesture("peace")
        assert m.gesture_counts == {"fist": 2, "peace": 1}

    def test_record_frame(self):
        m = MetricsCollector()
        m.record_frame(0.005, 2)
        m.record_frame(0.010, 1)
        assert m._frames_total == 2
        assert m._hands_total == 3

    def test_render_prometheus_format(self):
        m = MetricsCollector()
        m.record_gesture("thumbs_up")
        m.record_frame(0.005, 1)
        m.set_connections(3)

        output = m.render()
        assert "gesture_engine_gestures_total" in output
        assert 'gesture="thumbs_up"' in output
        assert "gesture_engine_frames_total 1" in output
        assert "gesture_engine_active_connections 3" in output
        assert "# HELP" in output
        assert "# TYPE" in output

    def test_histogram_buckets(self):
        m = MetricsCollector()
        for _ in range(10):
            m.record_frame(0.003, 1)
        output = m.render()
        assert "gesture_engine_frame_latency_seconds_bucket" in output
        assert "gesture_engine_frame_latency_seconds_sum" in output
        assert "gesture_engine_frame_latency_seconds_count 10" in output
