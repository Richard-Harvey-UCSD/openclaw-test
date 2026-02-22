#!/usr/bin/env python3
"""Live webcam gesture recognition demo.

Usage:
    python examples/demo_webcam.py [--camera 0] [--no-display]
"""

import argparse
import sys
import time

import cv2
import numpy as np

sys.path.insert(0, "src")
from gesture_engine import GesturePipeline, GestureEvent


def draw_overlay(frame, events: list[GestureEvent], stats):
    """Draw gesture labels and stats on frame."""
    # Stats
    cv2.putText(
        frame,
        f"FPS: {stats.fps:.1f} | Latency: {stats.avg_latency_ms:.1f}ms",
        (10, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 255, 0),
        2,
    )

    # Gesture labels
    for event in events:
        label = f"{event.gesture} ({event.confidence:.0%})"
        # Position label near the wrist landmark
        h, w = frame.shape[:2]
        wrist = event.landmarks[0]
        x = int(wrist[0] * w)
        y = int(wrist[1] * h) - 20

        cv2.putText(
            frame, label, (x, y),
            cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2,
        )

    return frame


def main():
    parser = argparse.ArgumentParser(description="GestureEngine Webcam Demo")
    parser.add_argument("--camera", type=int, default=0, help="Camera index")
    parser.add_argument("--no-display", action="store_true", help="Run headless")
    args = parser.parse_args()

    cap = cv2.VideoCapture(args.camera)
    if not cap.isOpened():
        print(f"Error: Cannot open camera {args.camera}")
        sys.exit(1)

    print("Starting GestureEngine...")
    print("Press 'q' to quit\n")

    def on_gesture(event: GestureEvent):
        print(f"  🤚 {event.gesture} (confidence: {event.confidence:.0%})")

    with GesturePipeline(smoothing_window=5, cooldown_seconds=0.8) as pipeline:
        pipeline.on_gesture(on_gesture)

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            events = pipeline.process_frame(frame_rgb)

            if not args.no_display:
                frame = draw_overlay(frame, events, pipeline.stats)
                cv2.imshow("GestureEngine", frame)

                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

    cap.release()
    cv2.destroyAllWindows()

    stats = pipeline.stats
    print(f"\nProcessed {stats.total_frames} frames, {stats.total_gestures} gestures")


if __name__ == "__main__":
    main()
