#!/usr/bin/env python3
"""Throwaway local Seatbelt boundary experiment; all native material stays private."""
import argparse
from contextlib import contextmanager
import errno
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time
import traceback

sys.dont_write_bytecode = True
import run as driver

MODEL_BYTES = 3095033483
MODEL_SHA256 = "64d182b440b98d5203c4f9bd541544d84c605196c4f7b845dfa11fb23594d1e2"
ZERO_PCM = bytes(16000 * 4)
LIMITATIONS = {
    "ad_hoc_hardened_seatbelt_not_shipping_app_sandbox_certification": True,
    "profile_is_allow_default_with_scoped_file_and_network_denials": True,
    "no_developer_id_or_notarization_qualification": True,
    "no_older_host_execution": True,
    "passive_observation_not_critical_notification_or_reclamation_proof": True,
    "model_boundary_and_decoding_only_not_product_scheduling_or_account_integration": True,
    "gpu_retry_is_explicit_driver_control_not_automatic_telegram_recovery": True,
    "count_guard_before_resize_and_payload_read_not_before_existing_bounded_reserve": True,
    "no_native_model_or_working_memory_cap_proven": True,
    "network_result_covers_only_the_attempted_loopback_tcp_connect": True,
    "child_core_files_disabled_but_local_os_crash_diagnostics_may_still_occur": True,
    "cpu_build_flags_and_linkage_require_parent_inspection_not_runtime_backend_selection": True,
}


def within(path, root):
    return path == root or root in path.parents


def checkout_root():
    for parent in Path(__file__).resolve().parents:
        if (parent / ".git").exists():
            return parent
    raise RuntimeError("cannot identify prototype checkout boundary")


def prepare(args):
    root = checkout_root()
    git_dir = root / ".git"
    if git_dir.is_file():
        entry = git_dir.read_text().strip()
        if not entry.startswith("gitdir: "):
            raise RuntimeError("cannot identify originating checkout boundary")
        git_dir = (root / entry.removeprefix("gitdir: ")).resolve()
    original_root = next((path.parent for path in (git_dir, *git_dir.parents)
                          if path.name == ".git"), root)
    for name in ("helper", "cpu_helper", "probe", "model"):
        value = getattr(args, name).resolve(strict=True)
        if not value.is_file():
            raise RuntimeError("required explicit input is not a regular file")
        setattr(args, name, value)
    if args.helper == args.cpu_helper:
        raise RuntimeError("Metal and CPU-only controls require distinct executables")
    for binary in (args.helper, args.cpu_helper, args.probe):
        if within(binary, root) or within(binary, original_root):
            raise RuntimeError("native executables must be outside both checkouts")
        if not os.access(binary, os.X_OK):
            raise RuntimeError("native executable is not executable")
    args.output = args.output.resolve()
    if within(args.output, root) or within(args.output, original_root):
        raise RuntimeError("output must be outside both checkouts")
    if args.output.exists():
        if not args.output.is_dir() or any(args.output.iterdir()):
            raise RuntimeError("output must be an empty private directory")
        info = args.output.stat()
        if info.st_uid != os.getuid() or (info.st_mode & 0o777) != 0o700:
            raise RuntimeError("existing output must be owned by this user and mode 0700")
    else:
        args.output.mkdir(mode=0o700, parents=True)
    if any(within(path, args.output) for path in
           (args.model, args.helper, args.cpu_helper, args.probe)):
        raise RuntimeError("empty output cannot contain input files")


def profile(args, managed, deny_gpu):
    runtime = (
        "/System/Library", "/usr/lib", "/usr/share/icu", "/usr/share/zoneinfo",
        "/private/var/db/dyld", "/private/var/db/timezone",
    )
    literals = (args.helper, args.cpu_helper, args.probe, args.model, managed,
                Path("/dev/null"), Path("/dev/urandom"), Path("/dev/random"))
    lines = ["(version 1)", "(allow default)", "(deny network*)",
             "(deny file-read*)", "(deny file-write*)"]
    lines.append('(allow file-read-data (literal "/"))')
    for path in runtime:
        lines.append(f"(allow file-read* (subpath {json.dumps(path)}))")
    for path in literals:
        lines.append(f"(allow file-read* (literal {json.dumps(str(path))}))")
    metadata = {str(parent) for path in literals for parent in path.parents}
    for path in sorted(metadata):
        lines.append(f"(allow file-read-metadata (literal {json.dumps(path)}))")
    lines.append('(allow file-write* (literal "/dev/null"))')
    if deny_gpu:
        lines.append("(deny iokit-open)")
    return "\n".join(lines) + "\n"


def disable_child_core():
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


@contextmanager
def selected_profile(path):
    previous = driver.PROFILE
    original_popen = driver.subprocess.Popen

    def owned_popen(*args, **kwargs):
        kwargs["preexec_fn"] = disable_child_core
        return original_popen(*args, **kwargs)

    driver.subprocess.Popen = owned_popen
    driver.PROFILE = path
    try:
        yield
    finally:
        driver.PROFILE = previous
        driver.subprocess.Popen = original_popen


class TrackedHelper(driver.Helper):
    def __init__(self, owner, label, backend, policy):
        self.owner = owner
        self.label = label
        self.closed = False
        self.pid_recorded = False
        self.exit_code = None
        binary = owner.args.helper if backend == "metal" else owner.args.cpu_helper
        owner.private({"case": label, "requested_backend": backend,
                       "executable_path": str(binary), "model_path": str(owner.args.model)})
        with selected_profile(policy):
            super().__init__(binary, owner.args.model, backend,
                             owner.args.output / (label + ".stderr.log"))

    def response(self, timeout=None):
        if not self.pid_recorded:
            self.owner.private({"case": self.label, "pid": self.process.pid})
            self.pid_recorded = True
        result = super().response(self.owner.args.helper_timeout if timeout is None else timeout)
        self.owner.private({"case": self.label, "native_response": result})
        return result

    def close(self):
        if self.closed:
            return
        process = getattr(self, "process", None)
        if process is not None:
            if process.poll() is None:
                try:
                    if not process.stdin.closed:
                        process.stdin.write(b"QUIT\n")
                        process.stdin.flush()
                    process.wait(timeout=5)
                except (OSError, ValueError, subprocess.TimeoutExpired):
                    process.kill()
                    process.wait(timeout=5)
            self.exit_code = process.returncode
            for stream in (process.stdin, process.stdout):
                if stream is not None:
                    stream.close()
            self.owner.private({"case": self.label, "exit_code": self.exit_code})
        log = getattr(self, "log", None)
        if log is not None:
            log.close()
        self.closed = True


class Qualification:
    def __init__(self, args):
        self.args = args
        self.events = (args.output / "private-native-events.jsonl").open("w")
        self.errors = (args.output / "private-exceptions.log").open("w")
        self.children = []
        self.report = {"schema": 1, "cases": {}, "limitations": LIMITATIONS,
                       "approved_model_verified": False, "unexpected_contract_failures": 0}
        self.strict = args.output / "strict-local.sb"
        self.no_gpu = args.output / "strict-local-no-gpu.sb"

    def private(self, value):
        self.events.write(json.dumps(value, ensure_ascii=False) + "\n")
        self.events.flush()

    def exception(self):
        traceback.print_exc(file=self.errors)
        self.errors.flush()

    def record(self, label, passed, **safe):
        self.report["cases"][label] = {"passed": bool(passed), **safe}
        if not passed:
            self.report["unexpected_contract_failures"] += 1

    def launch(self, label, backend="cpu", policy=None):
        helper = TrackedHelper.__new__(TrackedHelper)
        self.children.append(helper)
        try:
            helper.__init__(self, label, backend, policy or self.strict)
            return helper, True
        except Exception:
            self.exception()
            return helper, False

    def numeric_response(self, response):
        return {key: response[key] for key in
                ("seconds", "calls", "samples", "resident_bytes", "peak_resident_bytes")
                if type(response.get(key)) in (int, float)}

    def run_zero(self, helper):
        helper.submit(ZERO_PCM, "en")
        return helper.response()

    def native_probe(self, label, arguments, timeout):
        with (self.args.output / (label + ".stdout.log")).open("wb") as stdout, \
             (self.args.output / (label + ".stderr.log")).open("wb") as stderr:
            child = subprocess.Popen(["/usr/bin/sandbox-exec", "-f", str(self.strict),
                                      str(self.args.probe), *map(str, arguments)],
                                     stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
                                     preexec_fn=disable_child_core)
            self.private({"case": label, "probe_pid": child.pid})
            try:
                status = child.wait(timeout=timeout)
            except BaseException:
                child.kill()
                child.wait(timeout=5)
                raise
        raw = (self.args.output / (label + ".stdout.log")).read_text()
        self.private({"case": label, "probe_exit_code": status})
        return status, json.loads(raw)

    def boundary(self, label, denied, managed, write):
        try:
            status, data = self.native_probe(label, ["--files", self.args.model, managed, denied, write], 20)
            allowed = all(data[key].get("opened") is True and data[key].get("read") is True
                          for key in ("model", "managed"))
            denied_read = data["denied"].get("opened") is False and data["denied"].get("open_errno") in (errno.EPERM, errno.EACCES)
            denied_write = data["write"].get("opened") is False and data["write"].get("open_errno") in (errno.EPERM, errno.EACCES)
            self.record(label, status == 0 and allowed and denied_read and denied_write,
                        exit_code=status, model_read=data["model"].get("read") is True,
                        managed_read=data["managed"].get("read") is True,
                        denied_read=denied_read, denied_write=denied_write)
        except Exception:
            self.exception()
            self.record(label, False)

    def lifecycle(self):
        helper, loaded = self.launch("cpu-lifecycle")
        try:
            self.record("cpu_load", loaded)
            if not loaded:
                return
            result = self.run_zero(helper)
            self.record("cpu_run", result.get("status") == "ok", **self.numeric_response(result))
            unloaded = helper.command("UNLOAD")
            self.record("unload", unloaded.get("state") == "unloaded", **self.numeric_response(unloaded))
            rejected = self.run_zero(helper)
            self.record("unloaded_rejection", rejected.get("status") == "error"
                        and rejected.get("message") == "model is unloaded")
            ready = helper.command("LOAD")
            self.record("explicit_reload", ready.get("state") == "ready", **self.numeric_response(ready))
            result = self.run_zero(helper)
            self.record("run_after_reload", result.get("status") == "ok", **self.numeric_response(result))
        except Exception:
            self.exception()
            self.record("cpu_lifecycle_exception", False)
        finally:
            helper.close()

    def metal_strict(self):
        helper, loaded = self.launch("metal-strict", "metal", self.strict)
        try:
            self.record("metal_strict_load", loaded)
            if not loaded:
                self.record("metal_strict_run", False, skipped_due_to_failed_load=True)
                return
            result = self.run_zero(helper)
            self.record("metal_strict_run", result.get("status") == "ok",
                        **self.numeric_response(result))
        except Exception:
            self.exception()
            self.record("metal_strict_run", False)
        finally:
            helper.close()

    def malformed(self, label, truncated):
        helper, loaded = self.launch(label)
        try:
            if not loaded:
                self.record(label, False, loaded=False, exit_code=helper.exit_code)
                return
            helper.write_all(b"RUN en 16000\n\0\0\0\0" if truncated else b"RUN en 480001\n")
            helper.process.stdin.flush()
            if truncated:
                helper.process.stdin.close()
            status = helper.process.wait(timeout=20)
            marker = "truncated PCM request" if truncated else "invalid or oversized PCM request"
            stderr = (self.args.output / (label + ".stderr.log")).read_text(errors="replace")
            self.record(label, status == 2 and marker in stderr, exit_code=status,
                        payload_bytes_sent=4 if truncated else 0,
                        guard_before_oversized_resize_and_payload_read=not truncated)
        except Exception:
            self.exception()
            self.record(label, False)
        finally:
            helper.close()

    def crash(self):
        helper, loaded = self.launch("native-crash")
        before = len(self.children)
        try:
            if not loaded:
                self.record("native_crash_containment", False, loaded=False, exit_code=helper.exit_code)
                return
            helper.write_all(b"CRASH\n")
            helper.process.stdin.flush()
            status = helper.process.wait(timeout=20)
            time.sleep(0.2)
            self.record("native_crash_containment", status == -signal.SIGSEGV
                        and len(self.children) == before, exit_code=status,
                        supervisor_survived=True, automatic_restart_launches=len(self.children) - before,
                        intentional_native_fault=True)
        except Exception:
            self.exception()
            self.record("native_crash_containment", False)
        finally:
            helper.close()

    def denied_gpu(self):
        before = len(self.children)
        helper, loaded = self.launch("gpu-denied", "metal", self.no_gpu)
        failure = not loaded
        try:
            if loaded:
                response = self.run_zero(helper)
                failure = response.get("status") != "ok"
        except Exception:
            self.exception()
            failure = True
        finally:
            helper.close()
        stderr = (self.args.output / "gpu-denied.stderr.log").read_text(errors="replace").lower()
        gpu_terms = ("metal", "iokit", "gpu")
        failure_terms = ("failed", "error", "denied", "abort", "assert", "cannot", "unable")
        gpu_marker = any(token in stderr for token in gpu_terms)
        failure_marker = any(any(token in line for token in gpu_terms)
                             and any(token in line for token in failure_terms)
                             for line in stderr.splitlines())
        observed = failure and failure_marker
        self.record("gpu_denied_native_failure", observed, loaded_before_failure=loaded,
                    exit_code=helper.exit_code, expected_abort_observed=helper.exit_code == -signal.SIGABRT,
                    gpu_diagnostic_marker_observed=gpu_marker, failure_diagnostic_marker_observed=failure_marker,
                    retry_launched_automatically=False)
        time.sleep(0.2)
        intervening = len(self.children) - before - 1
        exited = getattr(helper, "process", None) is not None and helper.process.poll() is not None
        self.record("no_retry_before_explicit_call", helper.closed and exited and intervening == 0,
                    intervening_launches=intervening)
        if observed:
            self.explicit_cpu_retry()
        else:
            self.record("explicit_same_model_cpu_retry", False, skipped_due_to_failed_gpu_control=True)

    def explicit_cpu_retry(self):
        helper, loaded = self.launch("explicit-cpu-retry", "cpu", self.no_gpu)
        try:
            if not loaded:
                self.record("explicit_same_model_cpu_retry", False, loaded=False, exit_code=helper.exit_code)
                return
            result = self.run_zero(helper)
            self.record("explicit_same_model_cpu_retry", result.get("status") == "ok",
                        loaded=True, same_model=True, separate_explicit_driver_call=True,
                        **self.numeric_response(result))
        except Exception:
            self.exception()
            self.record("explicit_same_model_cpu_retry", False)
        finally:
            helper.close()

    def pressure(self):
        try:
            status, data = self.native_probe("passive-pressure", ["--pressure", self.args.pressure_seconds], self.args.pressure_seconds + 20)
            safe = {key: data[key] for key in
                    ("registered", "registration_seconds", "observation_seconds", "callbacks", "event_bits",
                     "normal_observed", "warn_observed", "critical_observed", "critical_reclamation_proven")
                    if type(data.get(key)) in (int, float, bool)}
            self.record("passive_pressure", status == 0 and data.get("registered") is True,
                        exit_code=status, **safe)
        except Exception:
            self.exception()
            self.record("passive_pressure", False)

    def execute(self):
        digest = hashlib.sha256()
        size = self.args.model.stat().st_size
        if size == MODEL_BYTES:
            with self.args.model.open("rb") as model:
                for chunk in iter(lambda: model.read(4 * 1024 * 1024), b""):
                    digest.update(chunk)
        verified = size == MODEL_BYTES and digest.hexdigest() == MODEL_SHA256
        self.report["approved_model_verified"] = verified
        self.record("approved_full_model", verified, expected_bytes=MODEL_BYTES)
        if not verified:
            return
        fixtures = self.args.output / "fixtures"
        fixtures.mkdir(mode=0o700)
        original = fixtures / "selected-original.generated"
        sibling = fixtures / "denied-sibling.generated"
        managed = fixtures / "managed-copy.generated"
        original.write_bytes(b"approved synthetic import sentinel\n")
        sibling.write_bytes(b"nonsensitive denied sibling sentinel\n")
        selected = original.read_bytes()
        managed.write_bytes(selected)
        self.record("parent_managed_import", managed.read_bytes() == selected,
                    copied_bytes=len(selected), model_copied=False, before_child_launch=len(self.children) == 0)
        self.strict.write_text(profile(self.args, managed, False))
        self.no_gpu.write_text(profile(self.args, managed, True))
        self.boundary("file_boundary_sibling", sibling, managed, fixtures / "denied-write-a.generated")
        self.boundary("file_boundary_import_original", original, managed, fixtures / "denied-write-b.generated")
        try:
            status, data = self.native_probe("network", ["--network-probe"], 20)
            self.record("network_denied", status == 0 and data.get("connect_result") == -1
                        and data.get("errno") == errno.EPERM, exit_code=status,
                        connect_result=data.get("connect_result") if type(data.get("connect_result")) is int else None,
                        errno=data.get("errno") if type(data.get("errno")) is int else None)
        except Exception:
            self.exception()
            self.record("network_denied", False)
        self.lifecycle()
        self.malformed("oversized-count", False)
        self.malformed("truncated-eof", True)
        self.crash()
        self.metal_strict()
        try:
            self.denied_gpu()
        except Exception:
            self.exception()
            self.record("gpu_control_exception", False)
        self.pressure()
        if self.args.inject_termination:
            self.termination()

    def termination(self):
        helper, loaded = self.launch("optional-termination")
        try:
            if not loaded:
                self.record("optional_termination", False, loaded=False)
                return
            helper.submit(ZERO_PCM, "en")
            started = time.monotonic()
            helper.process.send_signal(signal.SIGTERM)
            status = helper.process.wait(timeout=20)
            self.record("optional_termination", status == -signal.SIGTERM, exit_code=status,
                        seconds=time.monotonic() - started, unrelated_to_actual_os_pressure=True)
        except Exception:
            self.exception()
            self.record("optional_termination", False)
        finally:
            helper.close()

    def finish(self):
        for helper in self.children:
            if hasattr(helper, "closed"):
                try:
                    helper.close()
                except Exception:
                    self.exception()
                    self.record("owned_child_cleanup", False)
        self.report["helper_launch_attempts"] = len(self.children)
        self.report["all_owned_helpers_exited"] = all(
            getattr(helper, "process", None) is None or helper.process.poll() is not None
            for helper in self.children)
        self.report["passed"] = self.report["unexpected_contract_failures"] == 0 and self.report["all_owned_helpers_exited"]
        (self.args.output / "safe-aggregate.json").write_text(json.dumps(self.report, indent=2) + "\n")
        self.events.close()
        self.errors.close()
        print(json.dumps({"passed": self.report["passed"],
                          "approved_model_verified": self.report["approved_model_verified"],
                          "unexpected_contract_failures": self.report["unexpected_contract_failures"],
                          "helper_launch_attempts": self.report["helper_launch_attempts"],
                          "cases": {name: row["passed"] for name, row in self.report["cases"].items()}}, separators=(",", ":")))
        return 0 if self.report["passed"] else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("helper", "cpu-helper", "probe", "model", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--pressure-seconds", type=int, default=5, choices=range(1, 121))
    parser.add_argument("--helper-timeout", type=int, default=600, choices=range(1, 1801))
    parser.add_argument("--inject-termination", action="store_true",
                        help="optional SIGTERM control, unrelated to actual OS pressure")
    args = parser.parse_args()
    os.umask(0o077)
    try:
        prepare(args)
    except Exception:
        print('{"passed":false,"precondition_failure":true}')
        return 2
    qualification = Qualification(args)
    try:
        qualification.execute()
    except BaseException:
        qualification.exception()
        qualification.record("driver_exception", False)
    finally:
        status = qualification.finish()
    return status


if __name__ == "__main__":
    raise SystemExit(main())
