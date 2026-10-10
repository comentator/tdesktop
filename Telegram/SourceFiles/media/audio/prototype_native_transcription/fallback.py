#!/usr/bin/env python3
"""Process-scoped IOKit denial, not a fabricated GPU error or global GPU change."""
import argparse
import json
from pathlib import Path
import run as driver


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--helper", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--assets", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    original_profile = driver.PROFILE
    row = {"model": str(args.model), "scope": "IOKit denial in this helper only, not physical GPU failure"}
    helper = None
    try:
        driver.PROFILE = Path(__file__).with_name("no_gpu.sb")
        helper = driver.Helper(args.helper, args.model, "metal", args.output / "gpu-denied.log")
        row["gpu_denied_load"] = helper.ready
        row["gpu_denied_run"] = helper.transcribe(args.assets / "de.wav", "auto")
    except Exception as error:
        row["gpu_denied_error"] = str(error)
    finally:
        if helper:
            helper.close()
        driver.PROFILE = original_profile
    helper = None
    try:
        helper = driver.Helper(args.helper, args.model, "cpu", args.output / "fallback-same-model-cpu.log")
        row["same_model_cpu_load"] = helper.ready
        row["same_model_cpu_run"] = helper.transcribe(args.assets / "de.wav", "auto")
    except Exception as error:
        row["cpu_error"] = str(error)
    finally:
        if helper:
            helper.close()
    row["not_proven"] = ["physical GPU fault recovery", "automatic Telegram supervisor fallback policy",
                         "older OS/Intel runtime", "same full-system memory footprint"]
    (args.output / "fallback.json").write_text(json.dumps(row, ensure_ascii=False, indent=2))
    print(json.dumps(row, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
