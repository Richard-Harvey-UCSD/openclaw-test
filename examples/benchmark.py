#!/usr/bin/env python3
"""GestureEngine Benchmark — inference latency, throughput, and memory usage.

Measures performance on the current hardware using synthetic hand landmarks.
No camera required.

Usage:
    python examples/benchmark.py
    python examples/benchmark.py --iterations 5000 --hands 2
"""

from __future__ import annotations

import argparse
import gc
import os
import sys
import time
from pathlib import Path

import numpy as np

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from gesture_engine.classifier import GestureClassifier
from gesture_engine.gestures import GestureRegistry, GestureDefinition, FingerState
from gesture_engine.sequences import SequenceDetector


def get_memory_mb() -> float:
    """Get current process RSS in MB."""
    try:
        import resource
        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024  # Linux: KB → MB
    except ImportError:
        return 0.0


def generate_synthetic_landmarks(n: int, gesture_type: str = "random") -> list[np.ndarray]:
    """Generate synthetic normalized hand landmarks for benchmarking."""
    landmarks_list = []

    for _ in range(n):
        if gesture_type == "open_hand":
            # Fingers extended: tips far from wrist
            lm = np.random.randn(21, 3).astype(np.float32) * 0.1
            lm[0] = [0, 0, 0]  # wrist at origin
            for tip in [4, 8, 12, 16, 20]:
                lm[tip] = np.array([0.3 + np.random.rand() * 0.2, -0.5 - np.random.rand() * 0.2, 0])
            for pip in [3, 6, 10, 14, 18]:
                lm[pip] = np.array([0.2 + np.random.rand() * 0.1, -0.3, 0])
        elif gesture_type == "fist":
            lm = np.random.randn(21, 3).astype(np.float32) * 0.1
            lm[0] = [0, 0, 0]
            for tip in [4, 8, 12, 16, 20]:
                lm[tip] = np.array([0.1, -0.1, 0]) + np.random.randn(3) * 0.02
            for pip in [3, 6, 10, 14, 18]:
                lm[pip] = np.array([0.15, -0.2, 0])
        else:
            lm = np.random.randn(21, 3).astype(np.float32) * 0.3
            lm[0] = [0, 0, 0]

        # Normalize
        scale = np.max(np.linalg.norm(lm, axis=1)) + 1e-8
        landmarks_list.append(lm / scale)

    return landmarks_list


def benchmark_classification(classifier: GestureClassifier, landmarks: list[np.ndarray]) -> dict:
    """Benchmark rule-based classification."""
    # Warmup
    for lm in landmarks[:10]:
        classifier.classify_rule_based(lm)

    gc.collect()
    times = []

    for lm in landmarks:
        t0 = time.perf_counter()
        classifier.classify_rule_based(lm)
        times.append(time.perf_counter() - t0)

    times_ms = np.array(times) * 1000
    return {
        "mean_ms": float(np.mean(times_ms)),
        "median_ms": float(np.median(times_ms)),
        "p95_ms": float(np.percentile(times_ms, 95)),
        "p99_ms": float(np.percentile(times_ms, 99)),
        "min_ms": float(np.min(times_ms)),
        "max_ms": float(np.max(times_ms)),
        "throughput_fps": 1000.0 / float(np.mean(times_ms)),
    }


def benchmark_features(classifier: GestureClassifier, landmarks: list[np.ndarray]) -> dict:
    """Benchmark feature extraction."""
    for lm in landmarks[:10]:
        classifier.extract_features(lm)

    gc.collect()
    times = []

    for lm in landmarks:
        t0 = time.perf_counter()
        classifier.extract_features(lm)
        times.append(time.perf_counter() - t0)

    times_ms = np.array(times) * 1000
    return {
        "mean_ms": float(np.mean(times_ms)),
        "throughput_fps": 1000.0 / float(np.mean(times_ms)),
    }


def benchmark_sequences(detector: SequenceDetector, n: int) -> dict:
    """Benchmark sequence detection."""
    gestures = ["fist", "open_hand", "peace", "pointing", "thumbs_up", "ok_sign"]

    # Warmup
    for i in range(100):
        detector.feed(gestures[i % len(gestures)], timestamp=float(i) * 0.1)
    detector.reset()

    gc.collect()
    times = []

    for i in range(n):
        g = gestures[i % len(gestures)]
        t0 = time.perf_counter()
        detector.feed(g, timestamp=float(i) * 0.1)
        times.append(time.perf_counter() - t0)

    times_ms = np.array(times) * 1000
    return {
        "mean_ms": float(np.mean(times_ms)),
        "throughput_fps": 1000.0 / float(np.mean(times_ms)),
    }


def print_table(title: str, rows: list[tuple[str, str]]):
    """Print a formatted table."""
    max_key = max(len(r[0]) for r in rows)
    max_val = max(len(r[1]) for r in rows)
    width = max_key + max_val + 7

    print()
    print(f"  ╭{'─' * width}╮")
    print(f"  │ {title:<{width-2}} │")
    print(f"  ├{'─' * width}┤")
    for key, val in rows:
        print(f"  │ {key:<{max_key}}   {val:>{max_val}} │")
    print(f"  ╰{'─' * width}╯")


def main():
    parser = argparse.ArgumentParser(description="GestureEngine Benchmark")
    parser.add_argument("-n", "--iterations", type=int, default=2000, help="Number of iterations")
    parser.add_argument("--hands", type=int, default=1, help="Simulated hands per frame")
    args = parser.parse_args()

    n = args.iterations

    print()
    print("  ┌─────────────────────────────────────┐")
    print("  │   GestureEngine Benchmark Suite 🚀   │")
    print("  └─────────────────────────────────────┘")
    print()

    # Setup
    mem_before = get_memory_mb()
    registry = GestureRegistry.with_defaults()
    classifier = GestureClassifier(registry=registry)
    seq_detector = SequenceDetector.with_defaults()

    # Generate test data
    print(f"  Generating {n} synthetic landmark frames...")
    landmarks_random = generate_synthetic_landmarks(n, "random")
    landmarks_open = generate_synthetic_landmarks(n // 4, "open_hand")
    landmarks_fist = generate_synthetic_landmarks(n // 4, "fist")
    all_landmarks = landmarks_random + landmarks_open + landmarks_fist
    np.random.shuffle(all_landmarks)
    test_data = all_landmarks[:n]

    mem_after = get_memory_mb()

    # Run benchmarks
    print("  Running classification benchmark...")
    classify_results = benchmark_classification(classifier, test_data)

    print("  Running feature extraction benchmark...")
    feature_results = benchmark_features(classifier, test_data)

    print("  Running sequence detection benchmark...")
    seq_results = benchmark_sequences(seq_detector, n)

    # Results
    print_table("Rule-Based Classification", [
        ("Mean latency", f"{classify_results['mean_ms']:.3f} ms"),
        ("Median latency", f"{classify_results['median_ms']:.3f} ms"),
        ("P95 latency", f"{classify_results['p95_ms']:.3f} ms"),
        ("P99 latency", f"{classify_results['p99_ms']:.3f} ms"),
        ("Min / Max", f"{classify_results['min_ms']:.3f} / {classify_results['max_ms']:.3f} ms"),
        ("Throughput", f"{classify_results['throughput_fps']:.0f} classifications/sec"),
    ])

    print_table("Feature Extraction (81-dim)", [
        ("Mean latency", f"{feature_results['mean_ms']:.3f} ms"),
        ("Throughput", f"{feature_results['throughput_fps']:.0f} extractions/sec"),
    ])

    print_table("Sequence Detection", [
        ("Mean latency", f"{seq_results['mean_ms']:.4f} ms"),
        ("Throughput", f"{seq_results['throughput_fps']:.0f} checks/sec"),
    ])

    print_table("System", [
        ("Iterations", f"{n:,}"),
        ("Gestures registered", f"{len(registry)}"),
        ("Sequences registered", f"{len(seq_detector._sequences)}"),
        ("Memory (data)", f"{mem_after - mem_before:.1f} MB"),
        ("Memory (total RSS)", f"{get_memory_mb():.1f} MB"),
        ("Platform", f"{sys.platform} / {os.uname().machine}"),
        ("Python", f"{sys.version.split()[0]}"),
        ("NumPy", f"{np.__version__}"),
    ])

    # Summary
    total_throughput = classify_results['throughput_fps']
    hands = args.hands
    effective_fps = total_throughput / hands

    print()
    print(f"  ⚡ Effective pipeline throughput: {effective_fps:.0f} FPS ({hands} hand{'s' if hands > 1 else ''})")
    print(f"  ⚡ End-to-end latency budget: {classify_results['mean_ms'] + feature_results['mean_ms']:.2f} ms (classify + features)")
    print(f"  ⚡ Sequence detection overhead: {seq_results['mean_ms']:.4f} ms (negligible)")
    print()


if __name__ == "__main__":
    main()
