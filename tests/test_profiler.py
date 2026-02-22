"""Tests for the performance profiler."""

import time
from gesture_engine.profiler import PipelineProfiler


class TestPipelineProfiler:
    def test_stage_timing(self):
        profiler = PipelineProfiler()
        with profiler.stage("detection"):
            time.sleep(0.001)

        stats = profiler.get_stage_stats("detection")
        assert stats is not None
        assert stats.call_count == 1
        assert stats.avg_ms >= 0.5  # at least ~1ms

    def test_multiple_stages(self):
        profiler = PipelineProfiler()
        for _ in range(10):
            with profiler.stage("classification"):
                pass

        stats = profiler.get_stage_stats("classification")
        assert stats.call_count == 10

    def test_summary(self):
        profiler = PipelineProfiler()
        with profiler.stage("detection"):
            pass
        with profiler.stage("classification"):
            pass

        summary = profiler.summary()
        assert "detection" in summary
        assert "classification" in summary
        assert "avg_ms" in summary["detection"]

    def test_disabled(self):
        profiler = PipelineProfiler()
        profiler.enabled = False
        with profiler.stage("detection"):
            pass

        stats = profiler.get_stage_stats("detection")
        assert stats is None  # no data recorded

    def test_reset(self):
        profiler = PipelineProfiler()
        with profiler.stage("detection"):
            pass
        profiler.reset()
        assert profiler.get_stage_stats("detection") is None or profiler.get_stage_stats("detection").call_count == 0
