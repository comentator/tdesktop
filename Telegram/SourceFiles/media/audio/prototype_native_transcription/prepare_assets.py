#!/usr/bin/env python3
"""Explicit synthetic fixture creation, never private-media discovery or downloads."""
import argparse
import json
from pathlib import Path
import subprocess

REFERENCES = {
    "de": "Hallo, ich habe heute keine Zeit. Wir treffen uns um vierzehn Uhr, nein, um vierzig Minuten nach drei.",
    "en": "This is a local speech recognition smoke test. The audio must stay on this computer.",
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    for language, voice in [("de", "Anna"), ("en", "Samantha")]:
        subprocess.run(["say", "-v", voice, "-o", str(args.output / f"{language}.aiff"),
                        REFERENCES[language]], check=True)
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i",
                        str(args.output / f"{language}.aiff"), "-ar", "16000", "-ac", "1",
                        "-c:a", "pcm_s16le", str(args.output / f"{language}.wav")], check=True)
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i",
                    str(args.output / "de.aiff"), "-ac", "1", "-c:a", "libopus", "-b:a", "32000",
                    str(args.output / "voice-like.ogg")], check=True)
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "lavfi", "-i",
                    "color=c=black:s=128x128:r=25", "-i", str(args.output / "de.aiff"),
                    "-shortest", "-c:v", "libx264", "-c:a", "aac",
                    str(args.output / "video-like.mp4")], check=True)
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "lavfi", "-i",
                    "anullsrc=r=16000:cl=mono", "-t", "5", "-c:a", "pcm_s16le",
                    str(args.output / "silence.wav")], check=True)
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-stream_loop", "4", "-i",
                    str(args.output / "voice-like.ogg"), "-c:a", "libopus",
                    str(args.output / "long-voice-like.ogg")], check=True)
    (args.output / "references.json").write_text(json.dumps(REFERENCES, ensure_ascii=False, indent=2))
    print(f"Created synthetic-only inputs in {args.output}; no dialect/fidelity verdict implied.")


if __name__ == "__main__":
    main()
