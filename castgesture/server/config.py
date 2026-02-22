"""CastGesture configuration management."""

import os
import json
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional

CONFIG_DIR = Path(__file__).parent.parent / "config"
DATA_DIR = Path(__file__).parent.parent / "data"


@dataclass
class ServerConfig:
    host: str = "0.0.0.0"
    port: int = 7555
    camera_index: int = 0
    camera_width: int = 640
    camera_height: int = 480
    fps: int = 30
    gesture_confidence_threshold: float = 0.7
    mappings_file: str = str(CONFIG_DIR / "default_mappings.yml")
    sounds_dir: str = str(CONFIG_DIR / "sounds")
    obs_ws_url: str = "ws://localhost:4455"
    obs_ws_password: str = ""
    twitch_enabled: bool = False
    twitch_channel: str = ""
    twitch_oauth_token: str = ""
    twitch_bot_name: str = "CastGestureBot"
    overlay_show_skeleton: bool = False
    debug: bool = False


_config: Optional[ServerConfig] = None
_config_path = DATA_DIR / "config.json"


def get_config() -> ServerConfig:
    global _config
    if _config is None:
        _config = load_config()
    return _config


def load_config() -> ServerConfig:
    if _config_path.exists():
        try:
            data = json.loads(_config_path.read_text())
            return ServerConfig(**{k: v for k, v in data.items() if hasattr(ServerConfig, k)})
        except Exception:
            pass
    return ServerConfig()


def save_config(config: ServerConfig):
    global _config
    _config = config
    _config_path.parent.mkdir(parents=True, exist_ok=True)
    _config_path.write_text(json.dumps(asdict(config), indent=2))


def update_config(**kwargs) -> ServerConfig:
    config = get_config()
    for k, v in kwargs.items():
        if hasattr(config, k):
            setattr(config, k, v)
    save_config(config)
    return config
