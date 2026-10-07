"""Run explicitly authorized repository commands with real test outcomes."""

import os
import signal
import subprocess
import tempfile
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from ..artifacts import safe_file, write_json
from ..errors import Blocked


def terminate(process):
    if process.poll() is None:
        if os.name == "posix":
            os.killpg(process.pid, signal.SIGKILL)
        else:
            process.kill()
        process.wait()


def parse_junit(path, started):
    source = Path(path)
    if not source.is_file() or source.stat().st_mtime < started - 1:
        raise ValueError("Missing or stale JUnit output")
    data = source.read_bytes()
    if len(data) > 5_000_000 or b"<!DOCTYPE" in data.upper() or b"<!ENTITY" in data.upper():
        raise ValueError("Unsafe or oversized JUnit output")
    root = ET.fromstring(data)
    counts = {"passed": 0, "failed": 0, "error": 0, "skipped": 0, "expected_failure": 0, "disabled": 0}
    for case in root.iter("testcase"):
        if case.find("failure") is not None:
            counts["failed"] += 1
        elif case.find("error") is not None:
            counts["error"] += 1
        elif (skip := case.find("skipped")) is not None:
            key = "expected_failure" if "xfail" in str(skip.attrib).lower() else "skipped"
            counts[key] += 1
        elif case.attrib.get("status") == "disabled":
            counts["disabled"] += 1
        else:
            counts["passed"] += 1
    return counts


def run(check, context):
    spec = check.spec
    if not context.config.allow_project_commands:
        raise Blocked("Repository commands are not authorized")
    argv = [value.replace("{run_dir}", str(context.folder)) for value in spec.argv]
    result_file = spec.result_file or f"{check.id}.junit.xml"
    if spec.runner == "pytest":
        argv.append(f"--junitxml={safe_file(context.folder, result_file)}")
    started = time.time()
    with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
        try:
            process = subprocess.Popen(argv, cwd=context.root, stdout=stdout, stderr=stderr,
                                       start_new_session=os.name == "posix")
        except FileNotFoundError as exc:
            raise Blocked("Required command executable is unavailable") from exc
        try:
            process.wait(timeout=min(spec.timeout, context.remaining()))
        except (subprocess.TimeoutExpired, KeyboardInterrupt):
            terminate(process)
            raise
        stdout.seek(0)
        stderr.seek(0)
        output = stdout.read(1_000_000).decode(errors="replace")
        error_output = stderr.read(1_000_000).decode(errors="replace")
    counts = {}
    reason = ""
    status = "passed" if process.returncode == spec.expected_exit else "failed"
    if spec.expected_stdout is not None and spec.expected_stdout not in output:
        status = "failed"
        reason = "Expected command output was absent"
    if spec.runner in {"pytest", "junit"}:
        if spec.runner == "pytest" and process.returncode == 5:
            status, reason = "blocked", "Pytest collected zero tests"
        else:
            counts = parse_junit(safe_file(context.folder, result_file), started)
            if not counts["passed"] and not counts["failed"] and not counts["error"]:
                status, reason = "blocked", "No ordinary test outcomes were evaluated"
            elif counts["failed"] or counts["error"]:
                status, reason = "failed", "Repository tests failed"
    artifact = f"{check.id}.command.json"
    write_json(context.folder, artifact, {"exit_code": process.returncode, "stdout": output,
               "stderr": error_output, "test_counts": counts}, context.redactor)
    return context.result(check, status, expected={"exit_code": spec.expected_exit},
                          actual={"exit_code": process.returncode}, test_counts=counts,
                          reason=reason, evidence=[artifact])
