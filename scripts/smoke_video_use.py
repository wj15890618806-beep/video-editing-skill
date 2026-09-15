"""Offline integration test for the pinned Windows video-use pipeline."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
ENTRY = ROOT / "scripts" / "video_use.py"


def call(command, *args):
    result = subprocess.run([sys.executable, "-X", "utf8", str(ENTRY), command, *map(str, args)], capture_output=True, encoding="utf-8", errors="replace")
    if result.returncode:
        raise RuntimeError(f"{command} failed:\n{result.stdout}\n{result.stderr}")
    return result.stdout


def main():
    root = ROOT / "local" / "tests"
    root.mkdir(parents=True, exist_ok=True)
    case = Path(tempfile.mkdtemp(prefix="中文 初剪-", dir=root))
    source = case / "素材 test.mp4"
    call("ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc2=size=320x180:rate=30:duration=4", "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=4", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", source)
    (case / "master.srt").write_text("1\n00:00:00,100 --> 00:00:01,000\n中文初剪测试\n\n2\n00:00:01,400 --> 00:00:02,300\n第二段字幕\n", encoding="utf-8")
    edl = {"version": 1, "sources": {"test": source.as_posix()}, "ranges": [{"source": "test", "start": 0.2, "end": 1.4}, {"source": "test", "start": 2.0, "end": 3.2}], "grade": "none", "overlays": [], "subtitles": "master.srt", "total_duration_s": 2.4}
    edl_path = case / "edl.json"
    edl_path.write_text(json.dumps(edl, ensure_ascii=False), encoding="utf-8")
    output = case / "draft.mp4"
    call("render", edl_path, "-o", output, "--draft")
    data = json.loads(call("ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", output))
    duration = float(data["format"]["duration"])
    assert abs(duration - 2.4) < 0.15, duration
    video = next(s for s in data["streams"] if s["codec_type"] == "video")
    assert (video["width"], video["height"]) == (1280, 720), video
    assert any(s["codec_type"] == "audio" for s in data["streams"])
    call("ffmpeg", "-v", "error", "-xerror", "-i", output, "-f", "null", "-")
    call("timeline_view", output, 0.2, 2.2, "--n-frames", 4, "-o", case / "verify.png")
    call("grade", "--analyze", source)
    transcripts = case / "transcripts"
    transcripts.mkdir()
    (transcripts / "test.json").write_text(json.dumps({"words": [{"type": "word", "text": "测试", "start": 0.2, "end": 0.8, "speaker_id": "speaker_0"}]}, ensure_ascii=False), encoding="utf-8")
    call("pack_transcripts", "--edit-dir", case)
    assert "测试" in (case / "takes_packed.md").read_text(encoding="utf-8")
    print(f"PASS: render + subtitles + decode + duration + timeline + grade + transcript pack\nArtifacts: {case}")


if __name__ == "__main__":
    main()
