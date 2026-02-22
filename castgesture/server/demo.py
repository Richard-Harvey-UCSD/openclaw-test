"""Demo mode — generate fake gesture events without a camera.

Usage:
    python -m castgesture.server.demo              # auto mode
    python -m castgesture.server.demo --interactive # just start server, use overlay ?demo=interactive
    python -m castgesture.server.demo --timeline timeline.json

Timeline JSON format:
    [
        {"t": 0.0, "gesture": "open_hand", "x": 0.5, "y": 0.5},
        {"t": 2.0, "gesture": "fist"},
        {"t": 4.0, "gesture": "peace", "x": 0.3, "y": 0.7}
    ]
"""

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger("castgesture.demo")

# Default demo timeline — cycles through all gestures
DEFAULT_TIMELINE = [
    {"t": 0.0, "gesture": "open_hand", "x": 0.5, "y": 0.4},
    {"t": 3.0, "gesture": "fist", "x": 0.5, "y": 0.5},
    {"t": 6.0, "gesture": "peace", "x": 0.4, "y": 0.3},
    {"t": 9.0, "gesture": "thumbs_up", "x": 0.6, "y": 0.4},
    {"t": 12.0, "gesture": "rock_on", "x": 0.5, "y": 0.5},
    {"t": 15.0, "gesture": "ok_sign", "x": 0.5, "y": 0.5},
    {"t": 18.0, "gesture": "pointing", "x": 0.3, "y": 0.3},
    # Sequence: fist → open_hand
    {"t": 21.0, "gesture": "fist", "x": 0.5, "y": 0.5},
    {"t": 21.8, "gesture": "open_hand", "x": 0.5, "y": 0.5},
]

DEMO_LOOP_DURATION = 24.0  # seconds before restarting


async def run_demo_timeline(
    broadcast_fn,
    mapping_engine,
    timeline: Optional[list] = None,
    loop: bool = True,
    get_sound_fn=None,
    sounds_dir: Optional[str] = None,
):
    """Run a scripted timeline of gesture events.

    Args:
        broadcast_fn: async callable to send events to overlay clients
        mapping_engine: MappingEngine instance for gesture→effect resolution
        timeline: list of {t, gesture, x?, y?} dicts, or None for default
        loop: whether to loop the timeline
        get_sound_fn: optional function(effect_type, sounds_dir) → sound_url
        sounds_dir: path to sounds directory
    """
    if timeline is None:
        timeline = DEFAULT_TIMELINE

    # Sort by time
    timeline = sorted(timeline, key=lambda e: e["t"])

    while True:
        start = time.monotonic()
        for entry in timeline:
            # Wait until it's time
            elapsed = time.monotonic() - start
            wait = entry["t"] - elapsed
            if wait > 0:
                await asyncio.sleep(wait)

            gesture = entry["gesture"]
            x = entry.get("x", 0.5)
            y = entry.get("y", 0.5)

            logger.info(f"Demo gesture: {gesture} at ({x:.1f}, {y:.1f})")

            # Process through mapping engine
            events = mapping_engine.process_gesture(gesture, x, y)
            for event in events:
                if get_sound_fn:
                    sound = get_sound_fn(event["effect"], sounds_dir)
                    if sound:
                        event["sound"] = sound
                await broadcast_fn(event)

            # Also broadcast raw gesture event for panel
            await broadcast_fn({
                "type": "gesture",
                "gesture": gesture,
                "x": x,
                "y": y,
                "landmarks": None,
            })

        if not loop:
            break

        # Wait remaining time before looping
        elapsed = time.monotonic() - start
        remaining = DEMO_LOOP_DURATION - elapsed
        if remaining > 0:
            await asyncio.sleep(remaining)


def main():
    """CLI entry point for demo mode."""
    import argparse
    parser = argparse.ArgumentParser(description="CastGesture Demo Mode")
    parser.add_argument("--interactive", action="store_true",
                        help="Start server only (use overlay ?demo=interactive)")
    parser.add_argument("--timeline", type=str, default=None,
                        help="Path to timeline JSON file")
    parser.add_argument("--no-loop", action="store_true",
                        help="Run timeline once instead of looping")
    parser.add_argument("--port", type=int, default=7555)
    parser.add_argument("--host", type=str, default="0.0.0.0")
    args = parser.parse_args()

    import os
    os.environ["CASTGESTURE_DEMO"] = "1"
    if args.interactive:
        os.environ["CASTGESTURE_DEMO_MODE"] = "interactive"
    else:
        os.environ["CASTGESTURE_DEMO_MODE"] = "auto"

    if args.timeline:
        os.environ["CASTGESTURE_DEMO_TIMELINE"] = args.timeline

    if args.no_loop:
        os.environ["CASTGESTURE_DEMO_NO_LOOP"] = "1"

    print(r"""
   ____          _    ____           _
  / ___|__ _ ___| |_ / ___| ___  ___| |_ _   _ _ __ ___
 | |   / _` / __| __| |  _ / _ \/ __| __| | | | '__/ _ \
 | |__| (_| \__ \ |_| |_| |  __/\__ \ |_| |_| | | |  __/
  \____\__,_|___/\__|\____|\___|_|___/\__|\__,_|_|  \___|
                                    🎭 DEMO MODE — No camera needed!
    """)

    if args.interactive:
        print(f"  🎮 Open overlay with interactive buttons:")
        print(f"     http://localhost:{args.port}/overlay/?demo=interactive")
    else:
        print(f"  🤖 Auto-cycling through all effects every 3s")
        print(f"     http://localhost:{args.port}/overlay/?demo=auto")

    print(f"  🎮 Control Panel: http://localhost:{args.port}/panel/")
    print()

    import uvicorn
    uvicorn.run(
        "castgesture.server.app:app",
        host=args.host,
        port=args.port,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
