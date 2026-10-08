"""Explicit safe scanners with conservative scope and sanitized findings."""

import json
import re
from pathlib import Path

import httpx

from ..artifacts import safe_file, write_json
from ..errors import Blocked
from ..policy import request_url
from ..security_scan import dependency_findings, run_tool, scan
from ..tooling import binary


def run(check, context):
    spec = check.spec
    if spec.tool == "web_headers":
        if not spec.base_url:
            raise Blocked("Web header checks require an explicit allowed origin")
        url = request_url(context.config, spec.base_url, spec.path)
        context.consume("requests")
        try:
            with (
                httpx.Client(
                    timeout=min(spec.timeout, context.remaining()), follow_redirects=False
                ) as client,
                client.stream("GET", url) as response,
            ):
                headers = dict(response.headers)
                code = response.status_code
        except httpx.HTTPError as exc:
            raise Blocked("Web header target is unavailable") from exc
        if code != 200:
            raise Blocked("Header check requires a successful target response")
        findings = [
            {
                "rule": "required-response-header",
                "header": key,
                "expected": value,
                "actual": headers.get(key.lower()),
                "classification": "potential_issue",
                "applicability": "Configured response header differs; assess deployment and threat model.",
            }
            for key, value in spec.required_headers.items()
            if headers.get(key.lower()) != value
        ]
        actual = {
            "tool": spec.tool,
            "findings": findings,
            "scope": "Declared response headers only; injection and session exploitation not inferred",
            "not_evaluated": ["All routes", "Third-party services", "Undeclared response headers"],
        }
        artifact = f"{check.id}.security.json"
        write_json(context.folder, artifact, actual, context.redactor)
        return context.result(
            check,
            "failed" if findings else "passed",
            actual=actual,
            evidence=[artifact],
            reason="Response header policy differs" if findings else "",
        )
    target = context.root.resolve() if spec.path == "." else safe_file(context.root, spec.path)
    if not target.exists():
        raise Blocked("Configured scan target does not exist")
    if spec.tool == "secrets":
        actual = scan(context.root, target, context.redactor)
    elif spec.tool == "dependencies":
        if not target.is_file() or target.stat().st_size > 100_000:
            raise Blocked("Dependency audit needs a small file of explicit name==version pins")
        lines = [
            line.strip()
            for line in target.read_text().splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        if not lines or any(
            not re.fullmatch(r"[A-Za-z0-9_.-]+==[A-Za-z0-9_.+!-]+", line) for line in lines
        ):
            raise Blocked(
                "Dependency audit only accepts explicit pins, without URLs, commands or implicit resolution"
            )
        context.consume("requests", len(lines))
        code, payload = run_tool(
            [
                binary("pip-audit"),
                "-r",
                str(target),
                "--disable-pip",
                "--no-deps",
                "--strict",
                "-f",
                "json",
                "--progress-spinner",
                "off",
                "--timeout",
                "10",
                "--cache-dir",
                str(context.folder / "audit-cache"),
            ],
            context,
            spec.timeout,
        )
        if code not in {0, 1}:
            raise Blocked(f"Dependency advisory audit could not finish (exit {code})")
        try:
            actual = dependency_findings(json.loads(payload))
        except (ValueError, KeyError, TypeError) as exc:
            raise Blocked("Dependency audit returned an invalid result") from exc
        if actual["skipped_packages"] or not actual["audited_dependencies"]:
            raise Blocked("Some pinned dependencies could not be audited")
    elif spec.tool == "semgrep":
        rules = Path(__file__).parents[1] / "assets" / "security" / "python.yaml"
        code, payload = run_tool(
            [
                binary("semgrep"),
                "scan",
                "--config",
                str(rules),
                "--json",
                "--error",
                "--metrics",
                "off",
                "--disable-version-check",
                "--no-git-ignore",
                "--jobs",
                "2",
                str(target),
            ],
            context,
            spec.timeout,
            env_extra={
                "SEMGREP_SETTINGS_FILE": str(context.folder / "semgrep-settings.yml"),
                "SEMGREP_LOG_FILE": str(context.folder / "semgrep.log"),
            },
        )
        if code not in {0, 1}:
            raise Blocked(f"Semgrep did not finish (exit {code})")
        data = json.loads(payload)
        if data.get("errors"):
            raise Blocked("Semgrep reported scan errors; source scope is incomplete")
        scanned = data.get("paths", {}).get("scanned", [])
        if not scanned:
            raise Blocked("No supported Python source was scanned")
        findings = [
            {
                "rule": f["check_id"],
                "file": str(Path(f["path"]).resolve().relative_to(context.root.resolve())),
                "line": f["start"]["line"],
                "classification": "potential_issue",
                "applicability": f["extra"]["message"],
            }
            for f in data["results"]
        ]
        actual = {
            "findings": findings,
            "scanned_files": len(scanned),
            "scope": "Two local Python rules; metrics and registry access disabled",
        }
    elif spec.tool == "gitleaks":
        raw = safe_file(context.folder, f"{check.id}.gitleaks-raw.json")
        code, _ = run_tool(
            [
                binary("gitleaks"),
                "dir",
                str(target),
                "--no-banner",
                "--redact=100",
                "--report-format",
                "json",
                "--report-path",
                str(raw),
            ],
            context,
            spec.timeout,
        )
        if code not in {0, 1} or not raw.is_file():
            raise Blocked(f"Gitleaks did not finish (exit {code})")
        data = json.loads(raw.read_text())
        raw.unlink()
        findings = [
            {
                "rule": f["RuleID"],
                "file": f["File"],
                "line": f["StartLine"],
                "classification": "potential_issue",
                "applicability": "Credential pattern in working tree; verify active use. Value withheld.",
            }
            for f in data
        ]
        actual = {
            "findings": findings,
            "scope": "Working tree patterns; excludes Git history and active credential validation",
        }
    else:
        raise Blocked("Requested security tool is not implemented yet")
    actual["tool"] = spec.tool
    artifact = f"{check.id}.security.json"
    write_json(context.folder, artifact, actual, context.redactor)
    return context.result(
        check,
        "failed" if actual["findings"] else "passed",
        actual=actual,
        expected={"findings": 0},
        reason="Potential security issues require applicability review"
        if actual["findings"]
        else "",
        evidence=[artifact],
    )
