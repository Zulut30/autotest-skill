"""Bounded orchestration with checkpointed evidence and prerequisite propagation."""

import hashlib
import json
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path

from . import __version__
from .artifacts import create_run, write_json
from .config import load_config
from .context import Context
from .errors import Blocked
from .planner import select
from .registry import resolve
from .results import RunReport


def now():
    return datetime.now(UTC).isoformat()


def run_config(
    config,
    root,
    output,
    profile="smoke",
    changed_files=(),
    config_digest="in-memory",
    resolver=resolve,
):
    identifier, folder = create_run(output)
    context = Context(config, Path(root), folder)
    revision = subprocess.run(
        ["git", "rev-parse", "--verify", "HEAD^{commit}"],
        cwd=root,
        capture_output=True,
        check=False,
        text=True,
    )
    report = RunReport(
        run_id=identifier,
        project=config.project,
        profile=profile,
        tool_version=__version__,
        started_at=now(),
        config_digest=config_digest,
        target_revision=revision.stdout.strip() if revision.returncode == 0 else None,
    )
    if report.target_revision:
        dirty = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=root,
            capture_output=True,
            check=False,
            text=True,
            timeout=5,
        )
        report.target_dirty = bool(dirty.stdout.strip()) if dirty.returncode == 0 else None
    checks = select(config, profile, changed_files)
    selected_ids = {check.id for check in checks}
    completed = {}
    try:
        for check in checks:
            started = time.monotonic()
            if any(
                completed[dep].status != "passed" or completed[dep].flaky
                for dep in check.depends_on
            ):
                result = context.result(
                    check, "blocked", reason="A prerequisite did not pass reliably"
                )
            else:
                attempts = []
                result = None
                for attempt in range(config.budgets.retries + 1):
                    prefix = ""
                    if attempt:
                        prefix = f"attempts/{check.id}/{attempt + 1}/"
                        context.folder = folder / prefix
                        context.folder.mkdir(parents=True, mode=0o700)
                    try:
                        context.consume("checks")
                        result = resolver(check.kind)(check, context)
                        if result.id != check.id or result.kind != check.kind:
                            raise ValueError("Adapter returned a mismatched result")
                    except Blocked as exc:
                        result = context.result(
                            check, "blocked", reason=context.redactor.text(str(exc))
                        )
                    except subprocess.TimeoutExpired:
                        result = context.result(
                            check, "blocked", reason="Command exceeded its time limit"
                        )
                    except Exception as exc:  # noqa: BLE001 - Adapter boundary preserves unknown tool errors as error status.
                        result = context.result(
                            check, "error", reason=f"Adapter execution error: {type(exc).__name__}"
                        )
                    finally:
                        context.folder = folder
                    result.evidence = [prefix + name for name in result.evidence]
                    attempts.append(
                        {
                            "attempt": attempt + 1,
                            "status": result.status,
                            "reason": result.reason,
                            "actual": result.actual,
                            "expected": result.expected,
                            "evidence": list(result.evidence),
                        }
                    )
                    if result.status != "failed" or check.mutating:
                        break
                result.attempts = attempts
                result.flaky = result.flaky or (
                    result.status == "passed" and any(a["status"] == "failed" for a in attempts)
                )
            result.elapsed_ms = (time.monotonic() - started) * 1000
            report.results.append(result)
            completed[check.id] = result
            write_json(folder, "result.json", report.model_dump(), context.redactor)
    except KeyboardInterrupt:
        report.interrupted = True
    finally:
        for check in config.checks:
            if check.id not in completed:
                reason = (
                    "Interrupted before execution"
                    if report.interrupted and check.id in selected_ids
                    else "Excluded by profile/change selection"
                )
                report.results.append(context.result(check, "skipped", reason=reason))
        report.finished_at = now()
        write_json(folder, "result.json", report.model_dump(), context.redactor)
        write_json(
            folder,
            "summary.json",
            {
                "counts": report.counts(),
                "exit_code": report.exit_code(),
                "budget_used": context.counters,
            },
            context.redactor,
        )
        from .reproduction import collect

        collect(config, report, Path(root), folder, context.redactor)
        from .reporting import render

        render(report, folder)
    return report, folder


def execute(args):
    config, root = load_config(args.config)
    digest = hashlib.sha256(Path(args.config).read_bytes()).hexdigest()
    report, folder = run_config(config, root, args.output, args.profile, args.changed_file, digest)
    print(
        json.dumps(
            {
                "run_id": report.run_id,
                "directory": str(folder),
                "counts": report.counts(),
                "exit_code": report.exit_code(),
            },
            indent=2,
        )
    )
    return report.exit_code()
