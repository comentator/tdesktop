#!/usr/bin/env python3
"""Export aggregate observations only; never publish inferred text, audio or raw logs."""
import argparse
import json
from pathlib import Path
import platform


def result(value):
    return {key: value[key] for key in
            ["status", "state", "language", "seconds", "calls", "resident_bytes", "peak_resident_bytes"]
            if key in value} | ({"text_characters": len(value["text"]),
                                "has_text": bool(value["text"].strip())}
                               if "text" in value else {})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    original = json.loads((args.input / "results.json").read_text())
    controls = json.loads((args.input / "controls.json").read_text())
    document = {"host": {"architecture": platform.machine(), "macos": platform.mac_ver()[0]},
                "scope": "synthetic smoke only; Debug helpers; no German-quality or shipping certification",
                "raw_audio_transcripts_and_logs": "retained locally, not exported",
                "cells": [], "controls": []}
    for row in original:
        cell = {"engine": row["engine"], "backend_requested": row["backend_requested"],
                "load": result(row["load"]), "cases": [],
                "warm_after_two_seconds_idle": [result(x) for x in row["warm_after_idle"]],
                "unload": result(row["unload"]), "reload": result(row["reload"]),
                "after_reload": [result(x) for x in row["after_reload"]],
                "while_unloaded": [result(x) for x in row["rejected_while_unloaded"]],
                "network_probe_exit": row["network_probe"]["exit"],
                "network_probe": json.loads(row["network_probe"]["stdout"]),
                "submitted_request_termination": row["inflight_cancel"],
                "injected_pressure_termination": row["injected_inflight_pressure"],
                "in_backend_running_acknowledgement": False,
                "injected_native_fault": row["native_fault"]}
        for case in row["cases"]:
            cell["cases"].append({"input": case["input"], "requested_language": case["requested_language"],
                                   "results": [result(x) for x in case["results"]]})
        document["cells"].append(cell)
    for row in controls:
        document["controls"].append({"engine": row["engine"], "backend_requested": row["backend_requested"],
                                    "long_input": [result(x) for x in row["long_input"]],
                                    "oversized_exit": row["oversized_exit"],
                                    "injected_idle_pressure_exit": row["injected_idle_pressure_exit"],
                                    "fresh_load_after_pressure": result(row["fresh_load_after_pressure"]),
                                    "injected_crash_exit": row["injected_crash_exit"],
                                    "fresh_run_after_crash": [result(x) for x in row["fresh_run_after_crash"]],
                                    "missing_model_exit": row["missing_model"]["exit"]})
    document["frontend_comparison"] = json.loads((args.input / "frontend-parity.json").read_text())
    decoder = json.loads((args.input / "decoder-parity.json").read_text())
    document["decoder_comparison"] = [{"case": x["case"], "equal": x["equal"]} for x in decoder]
    legacy = json.loads((args.input / "legacy-cpu-smoke.json").read_text())
    document["legacy_arm_cpu_on_current_host"] = {"load": result(legacy["load"]),
                                                 "forced_de": [result(x) for x in legacy["forced_de"]],
                                                 "not_old_os_execution": True}
    if (args.input / "fallback.json").exists():
        fallback = json.loads((args.input / "fallback.json").read_text())
        document["gpu_denial_probe"] = {key: fallback[key] for key in ["scope", "not_proven"]}
        for key in ["gpu_denied_load", "same_model_cpu_load"]:
            if key in fallback:
                document["gpu_denial_probe"][key] = result(fallback[key])
        for key in ["gpu_denied_run", "same_model_cpu_run"]:
            if key in fallback:
                document["gpu_denial_probe"][key] = [result(x) for x in fallback[key]]
        if "gpu_denied_error" in fallback:
            document["gpu_denial_probe"]["gpu_denied_failed"] = True
    args.output.write_text(json.dumps(document, ensure_ascii=False, indent=2))
    print(f"Exported aggregate observations to {args.output}; no inferred text or raw logs.")


if __name__ == "__main__":
    main()
