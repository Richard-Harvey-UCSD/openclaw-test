"""GestureEngine CLI — the main entry point for all operations.

Usage:
    gesture-engine serve       — Start the WebSocket server
    gesture-engine train       — Train MLP from collected data
    gesture-engine record      — Record landmark data from camera
    gesture-engine replay      — Replay a recorded session
    gesture-engine benchmark   — Run performance benchmarks
    gesture-engine define      — Interactive gesture definition
    gesture-engine export      — Export model to ONNX/TFLite
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

try:
    import typer
except ImportError:
    raise ImportError("typer is required for CLI. Install with: pip install typer")
from typing import Optional

app = typer.Typer(
    name="gesture-engine",
    help="🤚 Real-time hand gesture recognition for edge devices.",
    add_completion=False,
)


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", help="Bind address"),
    port: int = typer.Option(8765, help="Port"),
    actions_config: Optional[str] = typer.Option(None, "--actions", help="Path to actions YAML config"),
    model: Optional[str] = typer.Option(None, help="Path to trained model file"),
    log_level: str = typer.Option("info", help="Log level"),
):
    """Start the WebSocket gesture streaming server."""
    import uvicorn
    from gesture_engine.server import app as fastapi_app, state

    if model:
        from gesture_engine.classifier import GestureClassifier
        state.classifier = GestureClassifier(model_path=model)
        typer.echo(f"📦 Loaded model: {model}")

    if actions_config:
        import asyncio
        from gesture_engine.actions import ActionMapper
        state.action_mapper = ActionMapper.from_yaml(actions_config)
        typer.echo(f"⚡ Loaded action mappings: {actions_config}")

    typer.echo(f"🚀 Starting GestureEngine server on {host}:{port}")
    typer.echo(f"   Open http://{host}:{port} for the web demo")
    uvicorn.run(fastapi_app, host=host, port=port, log_level=log_level)


@app.command()
def train(
    data_dir: str = typer.Argument(..., help="Directory with recorded .json/.npz files"),
    output: str = typer.Option("model.pt", help="Output model path"),
    epochs: int = typer.Option(100, help="Training epochs"),
    lr: float = typer.Option(0.001, help="Learning rate"),
):
    """Train the MLP gesture classifier from recorded data."""
    import numpy as np
    from gesture_engine.classifier import GestureClassifier
    from gesture_engine.recorder import GesturePlayer

    data_path = Path(data_dir)
    if not data_path.exists():
        typer.echo(f"❌ Data directory not found: {data_dir}", err=True)
        raise typer.Exit(1)

    # Collect training data from recordings
    X_list = []
    y_list = []

    files = list(data_path.glob("*.json")) + list(data_path.glob("*.npz"))
    if not files:
        typer.echo(f"❌ No recording files found in {data_dir}", err=True)
        raise typer.Exit(1)

    typer.echo(f"📂 Loading {len(files)} recording files...")
    for f in files:
        player = GesturePlayer.load(f)
        for frame in player.play():
            for hand in frame.hands:
                for g in frame.gestures:
                    if g.get("name"):
                        X_list.append(np.array(hand, dtype=np.float32))
                        y_list.append(g["name"])

    if not X_list:
        typer.echo("❌ No labeled gesture data found in recordings.", err=True)
        raise typer.Exit(1)

    X = np.array(X_list)
    typer.echo(f"📊 Training data: {len(X)} samples, {len(set(y_list))} classes")
    typer.echo(f"   Classes: {sorted(set(y_list))}")

    classifier = GestureClassifier()
    with typer.progressbar(length=epochs, label="Training") as progress:
        stats = classifier.train(X, y_list, epochs=epochs, lr=lr, save_path=output)
        progress.update(epochs)

    typer.echo(f"\n✅ Training complete!")
    typer.echo(f"   Loss: {stats['loss']:.4f}")
    typer.echo(f"   Accuracy: {stats['accuracy']:.1%}")
    typer.echo(f"   Model saved to: {output}")


@app.command()
def record(
    output: str = typer.Option("recording.json", "-o", help="Output file path"),
    duration: float = typer.Option(0, help="Recording duration in seconds (0 = until Ctrl+C)"),
    compact: bool = typer.Option(False, help="Save in compact .npz format"),
    camera: int = typer.Option(0, help="Camera device index"),
):
    """Record hand landmark data from the camera."""
    import cv2
    from gesture_engine.detector import HandDetector
    from gesture_engine.classifier import GestureClassifier
    from gesture_engine.recorder import GestureRecorder

    cap = cv2.VideoCapture(camera)
    if not cap.isOpened():
        typer.echo(f"❌ Could not open camera {camera}", err=True)
        raise typer.Exit(1)

    detector = HandDetector()
    classifier = GestureClassifier()
    recorder = GestureRecorder()

    typer.echo(f"🎥 Recording from camera {camera}...")
    typer.echo("   Press Ctrl+C to stop")
    recorder.start()

    start = time.monotonic()
    frame_count = 0

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                continue

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            hands = detector.detect_normalized(frame_rgb)

            gestures = []
            for i, lm in enumerate(hands):
                result = classifier.classify(lm)
                if result:
                    gestures.append({"name": result[0], "confidence": result[1], "hand_index": i})

            recorder.add_frame(hands, gestures)
            frame_count += 1

            if frame_count % 30 == 0:
                elapsed = time.monotonic() - start
                typer.echo(f"\r   Frames: {frame_count} | Duration: {elapsed:.1f}s | Hands: {len(hands)}", nl=False)

            if duration > 0 and (time.monotonic() - start) >= duration:
                break

    except KeyboardInterrupt:
        pass
    finally:
        recorder.stop()
        cap.release()
        detector.close()

    typer.echo(f"\n\n📼 Recorded {recorder.frame_count} frames ({recorder.duration:.1f}s)")

    if compact:
        recorder.save_compact(output)
    else:
        recorder.save(output)

    typer.echo(f"💾 Saved to: {output}")


@app.command()
def replay(
    recording: str = typer.Argument(..., help="Path to recording file"),
    speed: float = typer.Option(1.0, help="Playback speed multiplier"),
    realtime: bool = typer.Option(True, help="Play at original timing"),
):
    """Replay a recorded gesture session through the pipeline."""
    from gesture_engine.recorder import GesturePlayer
    from gesture_engine.pipeline import GesturePipeline

    path = Path(recording)
    if not path.exists():
        typer.echo(f"❌ Recording not found: {recording}", err=True)
        raise typer.Exit(1)

    player = GesturePlayer.load(path)
    typer.echo(f"▶️  Replaying {path.name} ({player.frame_count} frames, {player.duration:.1f}s)")

    pipeline = GesturePipeline()
    gesture_count = 0

    def on_gesture(event):
        nonlocal gesture_count
        gesture_count += 1
        typer.echo(f"   🤚 {event.gesture} (confidence: {event.confidence:.2f}, hand: {event.hand_index})")

    pipeline.on_gesture(on_gesture)

    play_fn = player.play_realtime(speed=speed) if realtime else player.play()
    for frame in play_fn:
        for hand in frame.hands:
            # Feed through classifier directly since we have landmarks
            result = pipeline.classifier.classify(hand)
            if result:
                name, conf = result
                typer.echo(f"   → {name}: {conf:.2f}")

    typer.echo(f"\n✅ Replay complete. {gesture_count} gestures detected.")


@app.command()
def benchmark(
    iterations: int = typer.Option(1000, help="Number of iterations"),
    hands: int = typer.Option(1, help="Simulated hands per frame"),
):
    """Run performance benchmarks on the gesture pipeline."""
    import numpy as np
    from gesture_engine.classifier import GestureClassifier
    from gesture_engine.gestures import GestureRegistry
    from gesture_engine.sequences import SequenceDetector
    from gesture_engine.profiler import PipelineProfiler

    typer.echo(f"⚡ Running benchmark: {iterations} iterations, {hands} hand(s)")

    classifier = GestureClassifier()
    seq_detector = SequenceDetector.with_defaults()
    profiler = PipelineProfiler()

    # Generate synthetic landmarks
    rng = np.random.default_rng(42)
    landmarks = [rng.random((21, 3)).astype(np.float32) for _ in range(hands)]

    times = []
    for i in range(iterations):
        t0 = time.perf_counter()

        with profiler.stage("feature_extraction"):
            features = [classifier.extract_features(lm) for lm in landmarks]

        with profiler.stage("classification"):
            results = [classifier.classify(lm) for lm in landmarks]

        with profiler.stage("sequence_detection"):
            for r in results:
                if r:
                    seq_detector.feed(r[0])

        elapsed = time.perf_counter() - t0
        times.append(elapsed)

    avg_ms = sum(times) / len(times) * 1000
    p95_ms = sorted(times)[int(len(times) * 0.95)] * 1000
    fps = 1000 / avg_ms if avg_ms > 0 else 0

    typer.echo(f"\n📊 Results:")
    typer.echo(f"   Average latency: {avg_ms:.2f} ms")
    typer.echo(f"   P95 latency:     {p95_ms:.2f} ms")
    typer.echo(f"   Throughput:      {fps:.0f} FPS")

    typer.echo(f"\n📈 Stage breakdown:")
    for name, stats in profiler.summary().items():
        typer.echo(f"   {name:25s} avg={stats['avg_ms']:.3f}ms  p95={stats['p95_ms']:.3f}ms")


@app.command()
def define():
    """Interactively define a new gesture by specifying finger states."""
    from gesture_engine.gestures import GestureDefinition, FingerState

    typer.echo("🖐  Interactive Gesture Definition\n")

    name = typer.prompt("Gesture name")

    fingers = {}
    for finger in ["thumb", "index", "middle", "ring", "pinky"]:
        choice = typer.prompt(
            f"  {finger.capitalize()} state",
            type=typer.Choice(["extended", "curled", "any"]),
            default="any",
        )
        fingers[finger] = FingerState(choice)

    min_conf = typer.prompt("Minimum confidence", default=0.6, type=float)

    gesture = GestureDefinition(
        name=name,
        thumb=fingers["thumb"],
        index=fingers["index"],
        middle=fingers["middle"],
        ring=fingers["ring"],
        pinky=fingers["pinky"],
        min_confidence=min_conf,
    )

    typer.echo(f"\n✅ Gesture '{name}' defined:")
    typer.echo(f"   {json.dumps(gesture.to_dict(), indent=2)}")

    save_path = typer.prompt("Save to file (or 'skip')", default="skip")
    if save_path != "skip":
        path = Path(save_path)
        existing = {"gestures": []}
        if path.exists():
            with open(path) as f:
                existing = json.load(f)

        existing["gestures"].append(gesture.to_dict())
        with open(path, "w") as f:
            json.dump(existing, f, indent=2)
        typer.echo(f"💾 Saved to {save_path}")


@app.command("export")
def export_model(
    model_path: str = typer.Argument(..., help="Path to trained .pt model"),
    format: str = typer.Option("onnx", help="Export format: onnx, tflite, both"),
    output: str = typer.Option("exported_model", help="Output path (without extension)"),
    quantize: bool = typer.Option(False, help="Apply quantization"),
    int8: bool = typer.Option(False, "--int8", help="Apply INT8 quantization (TFLite)"),
):
    """Export a trained model to ONNX or TFLite for edge deployment."""
    from gesture_engine.classifier import GestureClassifier
    from gesture_engine.export import ModelExporter

    typer.echo(f"📦 Loading model: {model_path}")
    classifier = GestureClassifier(model_path=model_path)
    exporter = ModelExporter(classifier)

    if format in ("onnx", "both"):
        path = exporter.to_onnx(output)
        typer.echo(f"✅ ONNX exported: {path} ({path.stat().st_size / 1024:.1f} KB)")

        validation = exporter.validate_onnx(path)
        status = "✅ PASSED" if validation["valid"] else "❌ FAILED"
        typer.echo(f"   Validation: {status} (max diff: {validation['max_difference']:.2e})")

    if format in ("tflite", "both"):
        try:
            path = exporter.to_tflite(output, quantize=quantize, quantize_int8=int8)
            typer.echo(f"✅ TFLite exported: {path} ({path.stat().st_size / 1024:.1f} KB)")
        except ImportError as e:
            typer.echo(f"⚠️  TFLite export unavailable: {e}", err=True)


def main():
    app()


if __name__ == "__main__":
    main()
