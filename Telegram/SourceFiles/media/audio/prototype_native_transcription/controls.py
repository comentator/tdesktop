#!/usr/bin/env python3
"""Additional real native controls; signal injection is not physical OS pressure."""
import argparse
import json
from pathlib import Path
import signal
import subprocess
import time
from run import Helper, PROFILE


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--assets", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--ggml", type=Path, required=True)
    parser.add_argument("--ct2", type=Path, required=True)
    parser.add_argument("--parakeet", type=Path, required=True)
    parser.add_argument("--legacy-cpu", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    matrix = [("whisper_helper", args.ggml, "metal"), ("whisper_helper", args.ggml, "cpu"),
              ("ct2_helper", args.ct2, "float32"), ("sherpa_helper", args.parakeet, "cpu"),
              ("sherpa_helper", args.parakeet, "coreml")]
    report = []
    for name, model, backend in matrix:
        binary = args.build / "bin" / name
        row = {"engine": name, "backend_requested": backend}
        helper = None
        try:
            helper = Helper(binary, model, backend, args.output / f"{name}-{backend}-long.log")
            row["long_input"] = helper.transcribe(args.assets / "long-voice-like.ogg", "auto")
            try:
                row["oversized_request"] = helper.command("RUN auto 480001")
            except RuntimeError as error:
                row["oversized_request"] = {"failure": str(error)}
            row["oversized_exit"] = helper.process.wait(timeout=5)
        except Exception as error:
            row["long_error"] = str(error)
        finally:
            if helper:
                helper.close()
        helper = None
        try:
            helper = Helper(binary, model, backend, args.output / f"{name}-{backend}-idle-pressure.log")
            helper.process.send_signal(signal.SIGUSR1)
            row["injected_idle_pressure_exit"] = helper.process.wait(timeout=5)
        except Exception as error:
            row["idle_pressure_error"] = str(error)
        finally:
            if helper:
                helper.close()
        helper = None
        try:
            helper = Helper(binary, model, backend, args.output / f"{name}-{backend}-recovery-crash.log")
            row["fresh_load_after_pressure"] = helper.ready
            helper.process.stdin.write(b"CRASH\n")
            helper.process.stdin.flush()
            row["injected_crash_exit"] = helper.process.wait(timeout=10)
        except Exception as error:
            row["crash_error"] = str(error)
        finally:
            if helper:
                helper.close()
        helper = None
        try:
            helper = Helper(binary, model, backend, args.output / f"{name}-{backend}-recovery-run.log")
            row["fresh_run_after_crash"] = helper.transcribe(args.assets / "de.wav", "auto")
        except Exception as error:
            row["recovery_error"] = str(error)
        finally:
            if helper:
                helper.close()
        missing = subprocess.run(["/usr/bin/sandbox-exec", "-f", str(PROFILE), str(binary),
                                  str(args.output / "nonexistent-model"), backend],
                                 capture_output=True, text=True, timeout=30)
        row["missing_model"] = {"exit": missing.returncode, "stdout": missing.stdout,
                                "stderr": missing.stderr}
        report.append(row)
        (args.output / "controls.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
        print(json.dumps(row, ensure_ascii=False), flush=True)
    helper = None
    try:
        helper = Helper(args.legacy_cpu, args.ggml, "cpu", args.output / "legacy-arm11-cpu.log")
        legacy = {"load": helper.ready,
                  "forced_de": helper.transcribe(args.assets / "de.wav", "de"),
                  "actual_host": "M5/macOS27, not macOS11", "binary": str(args.legacy_cpu)}
        (args.output / "legacy-cpu-smoke.json").write_text(json.dumps(legacy, ensure_ascii=False, indent=2))
        print(json.dumps(legacy, ensure_ascii=False), flush=True)
    finally:
        if helper:
            helper.close()


if __name__ == "__main__":
    main()
