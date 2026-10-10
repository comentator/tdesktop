#!/usr/bin/env python3
"""Synthetic-input frontend comparison only. No model inference/downloads."""
import argparse
import json
from pathlib import Path
import subprocess
import numpy as np


def reference(pcm):
    audio = np.frombuffer(pcm, dtype="<f4")
    padded = np.pad(audio, (0, 480000 - len(audio)))
    centered = np.pad(padded, (200, 200), mode="reflect")
    frames = np.lib.stride_tricks.sliding_window_view(centered, 400)[::160][:-1]
    window = (0.5 - 0.5 * np.cos(2 * np.pi * np.arange(400) / 400)).astype(np.float32)
    transformed = np.fft.rfft(frames * window, axis=-1)
    power = (transformed.real ** 2 + transformed.imag ** 2).astype(np.float32).T
    mels = np.linspace(0, 45.245640471924965, 130)
    hz = np.where(mels < 15, mels * (200 / 3),
                  1000 * np.exp((mels - 15) * np.log(6.4) / 27))
    fft_hz = np.arange(201) * 16000 / 400
    differences = np.diff(hz)
    ramps = hz[:, None] - fft_hz[None, :]
    filters = np.maximum(0, np.minimum(-ramps[:-2] / differences[:-1, None],
                                      ramps[2:] / differences[1:, None]))
    filters *= (2 / (hz[2:] - hz[:-2]))[:, None]
    energies = np.einsum("mb,bf->mf", filters.astype(np.float32),
                         power.astype(np.float64), optimize=False)
    logs = np.log10(np.maximum(energies, np.float32(1e-10)))
    return (np.maximum(logs, logs.max() - 8) + 4) / 4


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--helper", type=Path, required=True)
    parser.add_argument("--assets", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = {"reference": "NumPy centered-reflect periodic-Hann Slaney128; waveform padded30sec",
              "not_established": ["OpenAI torch/librosa bit identity", "faster-whisper short-input padding parity",
                                  "tokenizer decoder parity", "German recognition quality"], "cases": []}
    profile = Path(__file__).with_name("offline.sb")
    for name in ["de.wav", "en.wav", "silence.wav"]:
        pcm = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", str(args.assets / name),
                              "-vn", "-ar", "16000", "-ac", "1", "-f", "f32le", "pipe:1"],
                             capture_output=True, check=True).stdout
        if not pcm or len(pcm) > 480000 * 4:
            raise RuntimeError("requires nonempty approved fixture <=30sec")
        native = subprocess.run(["/usr/bin/sandbox-exec", "-f", str(profile), str(args.helper),
                                 "--frontend-dump"],
                                input=f"RUN auto {len(pcm)//4}\n".encode() + pcm,
                                capture_output=True, timeout=30)
        if native.returncode:
            raise RuntimeError(f"native frontend failed ({native.returncode}): "
                               f"{native.stderr.decode(errors='replace')} "
                               f"{native.stdout.decode(errors='replace')}")
        actual = np.frombuffer(native.stdout, dtype="<f4").reshape(128, 3000)
        expected = reference(pcm)
        difference = np.abs(actual - expected)
        report["cases"].append({"input": name, "maximum_absolute_difference": float(difference.max()),
                                "mean_absolute_difference": float(difference.mean()),
                                "all_finite": bool(np.isfinite(actual).all()),
                                "within_1e_minus4": bool(np.all(difference <= 1e-4))})
    args.output.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    if not all(row["all_finite"] and row["within_1e_minus4"] for row in report["cases"]):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
