"""Run the pinned video-use helpers with the installed isolated runtime."""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
INSTALL = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))) / "skills" / "video-use"
HELPERS = ROOT / "third_party" / "video-use" / "helpers"
COMMANDS = {"render", "grade", "timeline_view", "transcribe", "transcribe_batch", "pack_transcripts"}


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] in {"-h", "--help"}:
        print("Usage: python scripts/video_use.py <" + "|".join(sorted(COMMANDS | {"doctor", "ffmpeg", "ffprobe", "download"})) + "> [arguments]")
        return 0
    command, *arguments = sys.argv[1:]
    runtime = INSTALL / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    paths = [str(runtime.parent)]
    local_appdata = env.get("LOCALAPPDATA")
    if local_appdata:
        packages = Path(local_appdata) / "Microsoft" / "WinGet" / "Packages"
        paths.extend(str(p.parent) for p in sorted(packages.glob("Gyan.FFmpeg*/*/bin/ffmpeg.exe")))
    paths.extend(str(p.parent) for p in sorted((ROOT / "local" / "tools" / "ffmpeg").glob("**/ffmpeg.exe")))
    env["PATH"] = os.pathsep.join(paths + [env.get("PATH", "")])
    # Read only this known credential file; never print its contents.
    credential_file = INSTALL / ".env"
    if not env.get("ELEVENLABS_API_KEY") and credential_file.exists():
        for line in credential_file.read_text(encoding="utf-8-sig").splitlines():
            key, sep, value = line.strip().partition("=")
            if sep and key == "ELEVENLABS_API_KEY":
                env[key] = value.strip().strip("\"'")
                break
    if command == "doctor":
        ok = runtime.is_file()
        print(f"Python runtime: {'OK' if ok else 'MISSING'}")
        for name in ("ffmpeg", "ffprobe"):
            found = shutil.which(name, path=env["PATH"])
            print(f"{name}: {found or 'MISSING'}")
            ok = ok and bool(found)
        print("ElevenLabs key: " + ("configured (not validated)" if env.get("ELEVENLABS_API_KEY") else "missing; automatic transcription unavailable"))
        if runtime.is_file():
            result = subprocess.run([str(runtime), "-X", "utf8", "-c", "import requests,numpy,PIL,librosa,matplotlib,yt_dlp; print('Python dependencies: OK')"], env=env)
            ok = ok and result.returncode == 0
        return 0 if ok else 1
    if command in {"ffmpeg", "ffprobe"}:
        executable = shutil.which(command, path=env["PATH"])
        if not executable:
            raise SystemExit(f"{command} missing; install Gyan.FFmpeg or add it to PATH")
        return subprocess.run([executable, *arguments], env=env).returncode
    if not runtime.is_file():
        raise SystemExit(f"Missing runtime: {runtime}; see references/video-use.md")
    if command == "download":
        invocation = [str(runtime), "-m", "yt_dlp", *arguments]
    elif command in COMMANDS:
        invocation = [str(runtime), "-X", "utf8", str(HELPERS / f"{command}.py"), *arguments]
    else:
        raise SystemExit(f"Unknown command: {command}")
    return subprocess.run(invocation, env=env).returncode


if __name__ == "__main__":
    raise SystemExit(main())
