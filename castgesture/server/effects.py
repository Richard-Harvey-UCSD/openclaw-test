"""Effect definitions for CastGesture overlay."""

from dataclasses import dataclass, field, asdict
from typing import Optional
from enum import Enum


class EffectType(str, Enum):
    CONFETTI = "confetti"
    EMOJI_RAIN = "emoji_rain"
    FIRE = "fire"
    SCREEN_SHAKE = "screen_shake"
    FLASH = "flash"
    TEXT_POP = "text_pop"
    SPOTLIGHT = "spotlight"
    SCREEN_GRAB = "screen_grab"


@dataclass
class EffectParams:
    duration: float = 2.0          # seconds
    intensity: float = 1.0         # 0.0 - 2.0
    colors: list[str] = field(default_factory=lambda: ["#a855f7", "#06b6d4", "#f43f5e", "#facc15", "#22c55e"])
    emoji: str = "✌️"
    text: str = "NICE!"
    x: float = 0.5                 # normalized hand position
    y: float = 0.5
    particle_count: int = 150
    font_size: int = 120


EFFECT_DEFAULTS: dict[str, dict] = {
    "confetti": {"duration": 3.0, "intensity": 1.0, "particle_count": 150},
    "emoji_rain": {"duration": 3.0, "emoji": "✌️", "particle_count": 40},
    "fire": {"duration": 3.0, "intensity": 1.0},
    "screen_shake": {"duration": 0.5, "intensity": 1.0},
    "flash": {"duration": 0.3, "intensity": 1.0, "colors": ["#ffffff"]},
    "text_pop": {"duration": 2.0, "text": "NICE!", "font_size": 120},
    "spotlight": {"duration": 0.0, "intensity": 1.0},  # 0 = continuous
    "screen_grab": {"duration": 1.5, "intensity": 1.0},
}


def build_effect_event(effect_type: str, params: Optional[dict] = None) -> dict:
    """Build a WebSocket event payload for an effect."""
    defaults = EFFECT_DEFAULTS.get(effect_type, {})
    merged = {**defaults, **(params or {})}
    return {
        "type": "effect",
        "effect": effect_type,
        "params": merged,
    }
