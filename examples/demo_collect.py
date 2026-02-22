#!/usr/bin/env python3
"""Collect gesture training data from webcam.

Records landmark data for custom gesture training.

Usage:
    python examples/demo_collect.py --gesture thumbs_up --samples 100
"""

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, "src")
from gesture_engine import HandDetector


def main():
    parser = argparse.ArgumentParser(description="Collect gesture training data")
    parser.add_argument("--gesture", required=True, help="Gesture label name")
    parser.add_argument("--samples", type=int, default=50, help="Number of samples")
    parser.add_argument("--camera", type=int, default=0, help="Camera index")
    parser.add_argument("--output", default="data/gestures", help="Output directory")
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{args.gesture}.json"

    cap = cv2.VideoCapture(args.camera)
    if not cap.isOpened():
        print(f"Error: Cannot open camera {args.camera}")
        sys.exit(1)

    detector = HandDetector(max_hands=1)
    samples = []
    existing = []

    # Load existing samples if file exists
    if output_file.exists():
        with open(output_file) as f:
            existing = json.load(f)
        print(f"Loaded {len(existing)} existing samples")

    print(f"Collecting '{args.gesture}' gesture samples")
    print(f"Show the gesture and press SPACE to capture, 'q' to quit\n")

    while len(samples) < args.samples:
        ret, frame = cap.read()
        if not ret:
            break

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        hands = detector.detect_normalized(frame_rgb)

        status = f"Samples: {len(samples)}/{args.samples}"
        if hands:
            status += " | Hand detected ✓"
        else:
            status += " | No hand"

        cv2.putText(frame, status, (10, 30),
                     cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.imshow(f"Collecting: {args.gesture}", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        elif key == ord(" ") and hands:
            samples.append(hands[0].tolist())
            print(f"  Captured sample {len(samples)}/{args.samples}")

    cap.release()
    cv2.destroyAllWindows()
    detector.close()

    # Save
    all_samples = existing + samples
    with open(output_file, "w") as f:
        json.dump(all_samples, f)

    print(f"\nSaved {len(all_samples)} total samples to {output_file}")


if __name__ == "__main__":
    main()
