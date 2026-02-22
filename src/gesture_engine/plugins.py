"""Plugin system for GestureEngine.

Drop a .py file in the plugins/ directory and it auto-loads on startup.
Plugins receive gesture events and can register custom actions.

Plugin interface:
    class MyPlugin(GesturePlugin):
        name = "my_plugin"

        def on_gesture(self, event):
            print(f"Got gesture: {event.gesture}")

        def on_sequence(self, event):
            pass

        def on_startup(self, engine):
            pass

        def on_shutdown(self):
            pass

Or use the decorator API:
    plugin = GesturePlugin(name="simple")

    @plugin.handler("thumbs_up")
    def on_thumbs_up(event):
        print("Thumbs up!")
"""

from __future__ import annotations

import importlib.util
import logging
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

logger = logging.getLogger("gesture_engine.plugins")


@dataclass
class PluginEvent:
    """Event passed to plugin handlers."""
    type: str  # "gesture", "sequence", "trajectory", "bimanual", "canvas"
    name: str  # gesture/sequence name
    data: dict = field(default_factory=dict)
    timestamp: float = 0.0


class GesturePlugin:
    """Base class for GestureEngine plugins.

    Subclass this and implement the methods you care about.
    Place the file in the plugins/ directory for auto-loading.
    """

    name: str = "unnamed"
    version: str = "1.0.0"
    description: str = ""

    def __init__(self, name: Optional[str] = None, **kwargs):
        if name:
            self.name = name
        self._handlers: dict[str, list[Callable]] = {}

    def on_gesture(self, event: PluginEvent):
        """Called when a gesture is detected."""
        # Dispatch to registered handlers
        handlers = self._handlers.get(event.name, []) + self._handlers.get("*", [])
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error("Plugin %s handler error: %s", self.name, e)

    def on_sequence(self, event: PluginEvent):
        """Called when a gesture sequence is detected."""
        pass

    def on_trajectory(self, event: PluginEvent):
        """Called when a spatial trajectory is matched."""
        pass

    def on_bimanual(self, event: PluginEvent):
        """Called when a two-hand gesture is detected."""
        pass

    def on_canvas(self, event: PluginEvent):
        """Called when a canvas drawing command is generated."""
        pass

    def on_startup(self, context: dict):
        """Called when the engine starts. Context contains engine references."""
        pass

    def on_shutdown(self):
        """Called when the engine stops."""
        pass

    def handler(self, gesture_name: str = "*"):
        """Decorator to register a handler for a specific gesture."""
        def decorator(fn: Callable):
            if gesture_name not in self._handlers:
                self._handlers[gesture_name] = []
            self._handlers[gesture_name].append(fn)
            return fn
        return decorator


class PluginManager:
    """Discovers, loads, and dispatches events to plugins.

    Usage:
        manager = PluginManager()
        manager.load_directory("plugins/")
        manager.startup({"pipeline": pipeline})

        # In frame loop:
        manager.dispatch("gesture", PluginEvent(type="gesture", name="thumbs_up"))

        # Cleanup:
        manager.shutdown()
    """

    def __init__(self):
        self._plugins: dict[str, GesturePlugin] = {}

    def register(self, plugin: GesturePlugin):
        """Register a plugin instance."""
        if plugin.name in self._plugins:
            logger.warning("Plugin '%s' already registered, replacing", plugin.name)
        self._plugins[plugin.name] = plugin
        logger.info("Registered plugin: %s v%s", plugin.name, plugin.version)

    def unregister(self, name: str):
        """Remove a plugin."""
        plugin = self._plugins.pop(name, None)
        if plugin:
            try:
                plugin.on_shutdown()
            except Exception as e:
                logger.error("Plugin %s shutdown error: %s", name, e)

    def load_directory(self, path: str | Path) -> int:
        """Load all .py plugin files from a directory.

        Each file should define a class that subclasses GesturePlugin,
        or a module-level `plugin` variable that is a GesturePlugin instance.

        Returns number of plugins loaded.
        """
        path = Path(path)
        if not path.exists():
            logger.debug("Plugin directory %s does not exist", path)
            return 0

        loaded = 0
        for py_file in sorted(path.glob("*.py")):
            if py_file.name.startswith("_"):
                continue
            try:
                plugin = self._load_plugin_file(py_file)
                if plugin:
                    self.register(plugin)
                    loaded += 1
            except Exception as e:
                logger.error("Failed to load plugin %s: %s", py_file.name, e)

        return loaded

    def _load_plugin_file(self, path: Path) -> Optional[GesturePlugin]:
        """Load a single plugin file."""
        module_name = f"gesture_plugin_{path.stem}"

        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            return None

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        # Strategy 1: Module-level `plugin` variable
        if hasattr(module, "plugin") and isinstance(module.plugin, GesturePlugin):
            return module.plugin

        # Strategy 2: Find GesturePlugin subclass
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (
                isinstance(attr, type)
                and issubclass(attr, GesturePlugin)
                and attr is not GesturePlugin
            ):
                return attr()

        logger.warning("No GesturePlugin found in %s", path.name)
        return None

    def startup(self, context: dict):
        """Initialize all plugins."""
        for plugin in self._plugins.values():
            try:
                plugin.on_startup(context)
            except Exception as e:
                logger.error("Plugin %s startup error: %s", plugin.name, e)

    def shutdown(self):
        """Shut down all plugins."""
        for plugin in self._plugins.values():
            try:
                plugin.on_shutdown()
            except Exception as e:
                logger.error("Plugin %s shutdown error: %s", plugin.name, e)

    def dispatch(self, event_type: str, event: PluginEvent):
        """Send an event to all plugins.

        Args:
            event_type: One of "gesture", "sequence", "trajectory", "bimanual", "canvas"
            event: The event to dispatch.
        """
        method_name = f"on_{event_type}"
        for plugin in self._plugins.values():
            handler = getattr(plugin, method_name, None)
            if handler:
                try:
                    handler(event)
                except Exception as e:
                    logger.error(
                        "Plugin %s %s error: %s", plugin.name, method_name, e
                    )

    @property
    def plugins(self) -> dict[str, GesturePlugin]:
        return dict(self._plugins)

    @property
    def plugin_names(self) -> list[str]:
        return list(self._plugins.keys())
