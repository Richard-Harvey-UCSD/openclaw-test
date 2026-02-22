"""Sound effect triggers for CastGesture."""

from pathlib import Path
from typing import Optional

BUILTIN_SOUNDS: dict[str, str] = {
    "pop": "https://cdn.freesound.org/previews/662/662006_11523868-lq.mp3",
    "whoosh": "https://cdn.freesound.org/previews/607/607409_5674468-lq.mp3",
    "explosion": "https://cdn.freesound.org/previews/587/587194_7862006-lq.mp3",
    "ding": "https://cdn.freesound.org/previews/536/536420_11943129-lq.mp3",
    "applause": "https://cdn.freesound.org/previews/462/462162_8711341-lq.mp3",
    "tada": "https://cdn.freesound.org/previews/397/397354_4284968-lq.mp3",
}

# Maps effect types to default sounds
EFFECT_SOUNDS: dict[str, str] = {
    "confetti": "pop",
    "fire": "whoosh",
    "screen_shake": "explosion",
    "flash": "ding",
    "text_pop": "tada",
    "emoji_rain": "pop",
}

_custom_sounds: dict[str, str] = {}


def get_sound_url(sound_name: str, sounds_dir: Optional[str] = None) -> Optional[str]:
    """Get URL or local path for a sound."""
    if sound_name in _custom_sounds:
        return _custom_sounds[sound_name]
    if sounds_dir:
        local = Path(sounds_dir) / f"{sound_name}.mp3"
        if local.exists():
            return f"/sounds/{sound_name}.mp3"
    return BUILTIN_SOUNDS.get(sound_name)


def get_sound_for_effect(effect_type: str, sounds_dir: Optional[str] = None) -> Optional[str]:
    """Get the sound URL for a given effect type."""
    sound_name = EFFECT_SOUNDS.get(effect_type)
    if sound_name:
        return get_sound_url(sound_name, sounds_dir)
    return None


def register_custom_sound(name: str, url: str):
    _custom_sounds[name] = url


def list_sounds(sounds_dir: Optional[str] = None) -> dict[str, str]:
    result = dict(BUILTIN_SOUNDS)
    result.update(_custom_sounds)
    if sounds_dir:
        for f in Path(sounds_dir).glob("*.mp3"):
            result[f.stem] = f"/sounds/{f.name}"
    return result
