"""Tests for the plugin system."""

import pytest
from pathlib import Path

from gesture_engine.plugins import GesturePlugin, PluginManager, PluginEvent


class TestGesturePlugin:
    def test_handler_decorator(self):
        plugin = GesturePlugin(name="test")
        called = []

        @plugin.handler("thumbs_up")
        def on_thumbs(event):
            called.append(event.name)

        event = PluginEvent(type="gesture", name="thumbs_up")
        plugin.on_gesture(event)
        assert called == ["thumbs_up"]

    def test_wildcard_handler(self):
        plugin = GesturePlugin(name="test")
        called = []

        @plugin.handler("*")
        def on_any(event):
            called.append(event.name)

        plugin.on_gesture(PluginEvent(type="gesture", name="fist"))
        plugin.on_gesture(PluginEvent(type="gesture", name="peace"))
        assert called == ["fist", "peace"]

    def test_handler_error_doesnt_crash(self):
        plugin = GesturePlugin(name="test")

        @plugin.handler("*")
        def bad_handler(event):
            raise ValueError("boom")

        # Should not raise
        plugin.on_gesture(PluginEvent(type="gesture", name="test"))


class TestPluginManager:
    def test_register_and_list(self):
        mgr = PluginManager()
        mgr.register(GesturePlugin(name="a"))
        mgr.register(GesturePlugin(name="b"))
        assert mgr.plugin_names == ["a", "b"]

    def test_unregister(self):
        mgr = PluginManager()
        mgr.register(GesturePlugin(name="a"))
        mgr.unregister("a")
        assert mgr.plugin_names == []

    def test_dispatch(self):
        mgr = PluginManager()
        received = []

        class TestPlugin(GesturePlugin):
            name = "test"
            def on_gesture(self, event):
                received.append(event.name)

        mgr.register(TestPlugin())
        mgr.dispatch("gesture", PluginEvent(type="gesture", name="peace"))
        assert received == ["peace"]

    def test_load_directory_nonexistent(self):
        mgr = PluginManager()
        loaded = mgr.load_directory("/tmp/nonexistent_plugin_dir_12345")
        assert loaded == 0

    def test_load_directory(self, tmp_path):
        # Create a simple plugin file
        plugin_file = tmp_path / "my_plugin.py"
        plugin_file.write_text("""
from gesture_engine.plugins import GesturePlugin

class MyPlugin(GesturePlugin):
    name = "my_plugin"
    version = "1.0.0"
""")

        mgr = PluginManager()
        loaded = mgr.load_directory(tmp_path)
        assert loaded == 1
        assert "my_plugin" in mgr.plugin_names

    def test_startup_shutdown(self):
        mgr = PluginManager()
        state = {"started": False, "stopped": False}

        class LifecyclePlugin(GesturePlugin):
            name = "lifecycle"
            def on_startup(self, context):
                state["started"] = True
            def on_shutdown(self):
                state["stopped"] = True

        mgr.register(LifecyclePlugin())
        mgr.startup({})
        assert state["started"]
        mgr.shutdown()
        assert state["stopped"]
