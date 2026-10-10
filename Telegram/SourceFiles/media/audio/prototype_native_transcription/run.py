#!/usr/bin/env python3
"""Throwaway native qualification; approved synthetic inputs only, no model fetches."""
import argparse
import json
import os
from pathlib import Path
import select
import signal
import subprocess
import time

MAX_BYTES = 30 * 16000 * 4
PROFILE = Path(__file__).with_name("offline.sb")


class Helper:
    def __init__(self, binary, model, backend, log):
        self.log = log.open("wb")
        self.process = subprocess.Popen(
            ["/usr/bin/sandbox-exec", "-f", str(PROFILE),
             str(binary), str(model), backend],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=self.log, bufsize=0)
        self.pending = bytearray()
        try:
            self.ready = self.response()
            if self.ready.get("state") != "ready":
                raise RuntimeError(f"helper did not load: {self.ready}")
        except Exception:
            self.close()
            raise

    def response(self, timeout=180):
        deadline = time.monotonic() + timeout
        while True:
            while b"\n" in self.pending:
                line, _, rest = self.pending.partition(b"\n")
                self.pending = bytearray(rest)
                try:
                    return json.loads(line)
                except (ValueError, UnicodeDecodeError):
                    self.log.write(b"stdout diagnostic: " + line + b"\n")
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("native helper timed out")
            readable, _, _ = select.select([self.process.stdout], [], [], remaining)
            if not readable:
                raise TimeoutError("native helper timed out")
            data = os.read(self.process.stdout.fileno(), 8192)
            if not data:
                raise RuntimeError(f"helper EOF; exit={self.process.wait()}")
            self.pending.extend(data)

    def command(self, command):
        self.process.stdin.write((command + "\n").encode())
        self.process.stdin.flush()
        return self.response()

    def write_all(self, payload):
        remaining = memoryview(payload)
        while remaining:
            written = self.process.stdin.write(remaining)
            if not written:
                raise BrokenPipeError("native helper stdin closed")
            remaining = remaining[written:]

    def submit(self, pcm, language):
        self.write_all(f"RUN {language} {len(pcm) // 4}\n".encode())
        self.write_all(pcm)
        self.process.stdin.flush()

    def transcribe(self, filename, language):
        decoder = subprocess.Popen(
            ["ffmpeg", "-nostdin", "-v", "error", "-protocol_whitelist", "file,pipe",
             "-i", str(filename), "-vn", "-ar", "16000", "-ac", "1",
             "-f", "f32le", "pipe:1"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        results = []
        try:
            while True:
                pcm = decoder.stdout.read(MAX_BYTES)
                if not pcm:
                    break
                if len(pcm) % 4:
                    raise RuntimeError("decoder returned incomplete float sample")
                self.submit(pcm, language)
                results.append(self.response())
            error = decoder.stderr.read().decode()
            if decoder.wait() != 0:
                raise RuntimeError(f"local audio decode failed: {error}")
            return results
        finally:
            if decoder.poll() is None:
                decoder.kill()
                decoder.wait()

    def close(self):
        if self.process.poll() is None:
            try:
                self.process.stdin.write(b"QUIT\n")
                self.process.stdin.flush()
                self.process.wait(timeout=5)
            except (BrokenPipeError, subprocess.TimeoutExpired):
                self.process.kill()
                self.process.wait()
        self.log.close()


def decode_short(path):
    decoded = subprocess.run(
        ["ffmpeg", "-nostdin", "-v", "error", "-protocol_whitelist", "file,pipe",
         "-i", str(path), "-vn", "-ar", "16000", "-ac", "1", "-f", "f32le", "pipe:1"],
        capture_output=True, check=True).stdout
    if not decoded or len(decoded) > MAX_BYTES or len(decoded) % 4:
        raise RuntimeError("control fixture must be nonempty and <=30 seconds")
    return decoded


def qualify(binary, model, backend, assets, output):
    record = {"engine": binary.name, "backend_requested": backend,
              "model": str(model), "cases": [], "limitations": []}
    helper = None
    try:
        helper = Helper(binary, model, backend, output / f"{binary.name}-{backend}.log")
        record["load"] = helper.ready
        for filename, language in [("de.wav", "auto"), ("de.wav", "de"),
                                   ("en.wav", "auto"), ("en.wav", "en"),
                                   ("voice-like.ogg", "auto"),
                                   ("video-like.mp4", "auto"), ("silence.wav", "auto")]:
            record["cases"].append({"input": filename, "requested_language": language,
                                    "results": helper.transcribe(assets / filename, language)})
        time.sleep(2)
        record["warm_after_idle"] = helper.transcribe(assets / "de.wav", "auto")
        record["unload"] = helper.command("UNLOAD")
        record["rejected_while_unloaded"] = helper.transcribe(assets / "de.wav", "auto")
        record["reload"] = helper.command("LOAD")
        record["after_reload"] = helper.transcribe(assets / "de.wav", "auto")
    except Exception as error:
        record["error"] = str(error)
    finally:
        if helper:
            helper.close()
    probe = subprocess.run(
        ["/usr/bin/sandbox-exec", "-f", str(PROFILE), str(binary), "--network-probe"],
        capture_output=True, text=True, timeout=10)
    record["network_probe"] = {"exit": probe.returncode,
                               "stdout": probe.stdout.strip(), "stderr": probe.stderr.strip()}
    for scenario, signum in [("inflight_cancel", signal.SIGTERM),
                             ("injected_inflight_pressure", signal.SIGUSR1)]:
        helper = None
        try:
            helper = Helper(binary, model, backend, output / f"{binary.name}-{backend}-{scenario}.log")
            helper.submit(decode_short(assets / "de.wav"), "auto")
            time.sleep(0.1)
            started = time.monotonic()
            helper.process.send_signal(signum)
            status = helper.process.wait(timeout=5)
            record[scenario] = {"exit": status, "termination_seconds": time.monotonic() - started,
                                "note": "explicit process signal, not induced OS memory pressure"}
        except Exception as error:
            record[scenario] = {"error": str(error)}
        finally:
            if helper:
                helper.close()
    helper = None
    try:
        helper = Helper(binary, model, backend, output / f"{binary.name}-{backend}-crash.log")
        helper.process.stdin.write(b"CRASH\n")
        helper.process.stdin.flush()
        status = helper.process.wait(timeout=10)
        record["native_fault"] = {"exit": status, "supervisor_survived": True,
                                  "note": "intentional native SIGSEGV, not a spontaneous model failure"}
    except Exception as error:
        record["native_fault"] = {"error": str(error)}
    finally:
        if helper:
            helper.close()
    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--assets", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--ggml", type=Path, required=True)
    parser.add_argument("--ct2", type=Path, required=True)
    parser.add_argument("--parakeet", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    matrix = [("whisper_helper", args.ggml, "metal"),
              ("whisper_helper", args.ggml, "cpu"),
              ("ct2_helper", args.ct2, "float32"),
              ("sherpa_helper", args.parakeet, "cpu"),
              ("sherpa_helper", args.parakeet, "coreml")]
    report = []
    for name, model, backend in matrix:
        record = qualify(args.build / "bin" / name, model, backend, args.assets, args.output)
        report.append(record)
        (args.output / "results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
        print(json.dumps(record, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
