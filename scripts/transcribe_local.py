"""Offline Whisper transcription with a content-checked video-use word cache."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
import tempfile


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("video", type=Path)
    ap.add_argument("--edit-dir", type=Path, required=True)
    ap.add_argument("--model", choices=["tiny", "base", "small", "medium", "large-v1", "large-v2", "large-v3", "large-v3-turbo"], default="small")
    ap.add_argument("--language", default="zh")
    ap.add_argument("--audio-track", type=int, default=0)
    ap.add_argument("--threads", type=int, default=6)
    args = ap.parse_args()
    if args.audio_track < 0 or args.threads < 1:
        ap.error("audio-track must be nonnegative and threads must be positive")
    source = args.video.resolve(strict=True)
    with source.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    model_path = Path.home() / ".cache" / "whisper" / f"{args.model}.pt"
    if not model_path.is_file():
        ap.error(f"Cached model missing: {model_path}. Install the model before running offline.")
    with model_path.open("rb") as stream:
        model_digest = hashlib.file_digest(stream, "sha256").hexdigest()
    fingerprint = {
        "source_sha256": digest, "audio_track": args.audio_track,
        "model": args.model, "model_sha256": model_digest,
        "language": args.language, "engine": "openai-whisper",
        "engine_version": importlib.metadata.version("openai-whisper"),
        "word_timestamps": True, "condition_on_previous_text": False,
    }
    suffix = f".track{args.audio_track}" if args.audio_track else ""
    dest = args.edit_dir.resolve() / "transcripts" / f"{source.stem}{suffix}.json"
    if dest.exists():
        cached = json.loads(dest.read_text(encoding="utf-8"))
        if cached.get("provenance") == fingerprint:
            print(f"cached: {dest}")
            return
        ap.error(f"Cache differs from the source or settings; use a new edit-dir: {dest}")
    import torch
    import whisper

    torch.set_num_threads(args.threads)
    # Loading a verified local path prevents an implicit model download.
    model = whisper.load_model(str(model_path), device="cpu")
    print("Transcribing locally on CPU; no audio upload", flush=True)
    with tempfile.TemporaryDirectory(prefix="video-use-asr-") as tmp:
        audio = Path(tmp) / "audio.wav"
        subprocess.run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-i", str(source), "-map", f"0:a:{args.audio_track}",
            "-vn", "-ac", "1", "-ar", "16000", str(audio),
        ], check=True)
        result = model.transcribe(
            str(audio), language=args.language, fp16=False,
            word_timestamps=True, condition_on_previous_text=False,
        )
    result["provenance"] = fingerprint
    result["words"] = [
        {"text": word["word"], "start": word["start"], "end": word["end"],
         "type": "word", "probability": word.get("probability")}
        for segment in result["segments"] for word in segment.get("words", [])
    ]
    # Speaker diarization and audio-event recognition are intentionally absent.
    dest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=dest.parent,
                                     suffix=".tmp", delete=False) as stream:
        temporary = Path(stream.name)
        json.dump(result, stream, ensure_ascii=False, indent=2)
    temporary.replace(dest)
    print(dest)


if __name__ == "__main__":
    main()
