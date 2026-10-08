"""Generate reviewable checks from declared failed oracles; never execute target content."""

import json
import os
import sys
from pathlib import Path

from .artifacts import safe_file
from .benchmark import CATALOG
from .config import Config, origin
from .results import RunReport
from .secrets import SENSITIVE


class ProposalError(ValueError):
    """Fixed, safe diagnostics that contain no submitted target content or credentials."""


def write_proposal(output, source):
    path = Path(output).absolute()
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise ProposalError("Refusing to overwrite an existing regression proposal") from exc
    with os.fdopen(descriptor, "w") as stream:
        stream.write(source)
    return path


def propose(case_id, output):
    catalog = json.loads(CATALOG.read_text())
    case = next((c for c in catalog["measured_cases"] if c["id"] == case_id), None)
    if not case:
        raise ValueError("Unknown confirmed corpus case")
    source = '''"""Generated proposal: inspect the requirement/oracle before adopting in a project."""
import json
import os
from pathlib import Path
from autotest_skill.benchmark import case_config
from autotest_skill.demo import start_demo
from autotest_skill.runner import run_config

CASE = json.loads(CASE_JSON)

def test_declared_regression(tmp_path):
    defects = os.environ.get('AUTOTEST_REGRESSION_DEFECTS') == '1'
    with start_demo(defects=defects) as (base, _):
        config = case_config(CASE, base, defects)
        report, folder = run_config(config, Path.cwd(), tmp_path/'runs')
        result = next(r for r in report.results if r.id == CASE['check'])
        assert result.status == 'passed', (result.reason, str(folder))
'''.replace("CASE_JSON", repr(json.dumps(case)))
    return write_proposal(output, source)


def read_document(folder, name):
    path = safe_file(folder, name)
    if not path.is_file() or path.stat().st_size > 5_000_000:
        raise ProposalError("Saved run input is missing or exceeds the size limit")
    return json.loads(path.read_text())


def has_redactions(value):
    if isinstance(value, dict):
        return any(has_redactions(k) or has_redactions(v) for k, v in value.items())
    if isinstance(value, list):
        return any(has_redactions(v) for v in value)
    return isinstance(value, str) and "[REDACTED]" in value


def restore_bindings(config, metadata):
    checks = {check["id"]: check for check in config["checks"]}
    seen = set()
    for record in metadata:
        if record["check"] not in checks:
            continue
        key = (record["check"], record["field"])
        check = checks[record["check"]]
        if (
            key in seen
            or check["kind"] != "http"
            or record["field"] not in {"headers_env", "headers_from", "json_env", "capture"}
        ):
            raise ProposalError("Replay binding metadata is invalid or inconsistent")
        original = check["spec"][record["field"]]
        restored = {item["name"]: item["binding"] for item in record["entries"]}
        if (
            len(restored) != len(record["entries"])
            or original.keys() != restored.keys()
            or any(original[name] not in {"[REDACTED]", value} for name, value in restored.items())
        ):
            raise ProposalError("Replay binding metadata is invalid or inconsistent")
        check["spec"][record["field"]] = restored
        seen.add(key)


def report_configuration(run_directory, check_id=None):
    """Reduce the saved plan to one failed web oracle and its passed prerequisites."""
    folder = Path(run_directory).resolve()
    try:
        report = RunReport.model_validate(read_document(folder, "result.json"))
        reproduction = read_document(folder, "reproduction.json")
        if (
            reproduction["schema_version"] != 1
            or reproduction["run_id"] != report.run_id
            or reproduction["target_revision"] != report.target_revision
            or reproduction["config_digest"] != report.config_digest
            or reproduction["profile"] != report.profile
            or not report.finished_at
            or report.interrupted
        ):
            raise ProposalError("Inputs must belong to the same completed, uninterrupted run")
        failed = [
            r
            for r in report.results
            if r.kind == "web"
            and r.status == "failed"
            and not r.flaky
            and (check_id is None or r.id == check_id)
        ]
        if len(failed) != 1:
            raise ProposalError("Select exactly one failed web check with --check")
        result = failed[0]
        if len({r.id for r in report.results}) != len(report.results):
            raise ProposalError("Saved report contains duplicate check identifiers")
        data = reproduction["configuration"]
        checks = {check["id"]: check for check in data["checks"]}
        if len(checks) != len(data["checks"]):
            raise ProposalError("Saved configuration contains duplicate check identifiers")
        selected, visiting = [], set()
        results = {r.id: r for r in report.results}

        def include(identifier):
            if identifier in visiting:
                raise ProposalError("Saved configuration contains a dependency cycle")
            if any(c["id"] == identifier for c in selected):
                return
            visiting.add(identifier)
            check = checks[identifier]
            observed = results[identifier]
            if (
                check["kind"] not in {"web", "http"}
                or observed.kind != check["kind"]
                or observed.requirement != check["requirement"]
                or observed.oracle != check["oracle"]
            ):
                raise ProposalError("Only matching web/HTTP scenarios can be replayed from a run")
            if identifier != result.id and (observed.status != "passed" or observed.flaky):
                raise ProposalError("All prerequisites must have passed reliably in the source run")
            for dependency in check.get("depends_on", []):
                include(dependency)
            selected.append({**check, "profiles": ["release"]})
            visiting.remove(identifier)

        include(result.id)
        reduced = {
            **data,
            "project_root": ".",
            "checks": selected,
            "allow_project_commands": False,
            "allow_device_controls": False,
            "budgets": {**data.get("budgets", {}), "retries": 0},
        }
        restore_bindings(reduced, reproduction.get("configuration_bindings", []))
        if has_redactions(reduced):
            raise ProposalError(
                "Replay inputs are redacted. Use environment bindings for credentials in the "
                "original scenario and record a new run; placeholders are not replayable values"
            )
        config = Config.model_validate(reduced)
        for check in config.checks:
            if check.kind == "web" and any(
                action.value is not None
                and action.action in {"fill", "press"}
                and any(
                    SENSITIVE.search(value)
                    for value in (action.label, action.name, action.test_id, action.text)
                    if value
                )
                for action in check.spec.actions
            ):
                raise ProposalError("Sensitive UI inputs must use environment bindings for replay")
        config.allowed_origins = sorted({origin(check.spec.base_url) for check in config.checks})
        config = Config.model_validate(config.model_dump())
        return report, result, config
    except ProposalError:
        raise
    except (KeyError, TypeError, AttributeError, ValueError) as exc:
        raise ProposalError(
            "Saved run metadata or configuration is invalid or inconsistent"
        ) from exc


def propose_from_run(run_directory, output, check_id=None):
    report, result, config = report_configuration(run_directory, check_id)
    provenance = {
        "run_id": report.run_id,
        "check": result.id,
        "requirement": result.requirement,
        "oracle": result.oracle,
        "target_revision": report.target_revision,
    }
    config_json = json.dumps(config.model_dump(), ensure_ascii=False)
    provenance_json = json.dumps(provenance, ensure_ascii=False)
    source = f'''"""Regression proposal from a saved failed web oracle.

Review the declared expectations and start the isolated target before running.
Credentials remain environment bindings. This test does not start or reset the target.
AUTOTEST_REGRESSION_BASE_URL optionally rebinds a single origin to a reviewed test target.
AUTOTEST_REGRESSION_ROOT defaults to the current project directory for input files.
"""
import json
import os
from pathlib import Path

from autotest_skill.config import Config, origin
from autotest_skill.runner import run_config

CONFIG = json.loads({config_json!r})
SOURCE_REPORT = json.loads({provenance_json!r})


def test_reported_regression(tmp_path):
    data = json.loads(json.dumps(CONFIG))
    rebound = os.environ.get("AUTOTEST_REGRESSION_BASE_URL")
    if rebound:
        if len(data["allowed_origins"]) != 1:
            raise ValueError("Rebinding requires exactly one configured origin")
        base = origin(rebound)
        data["allowed_origins"] = [base]
        for check in data["checks"]:
            check["spec"]["base_url"] = base
    root = Path(os.environ.get("AUTOTEST_REGRESSION_ROOT", ".")).resolve()
    config = Config.model_validate(data)
    report, folder = run_config(config, root, tmp_path / "runs", profile="release")
    result = next(r for r in report.results if r.id == SOURCE_REPORT["check"])
    assert report.exit_code() == 0 and result.status == "passed" and not result.flaky, (
        result.status, result.reason, report.counts(), str(folder)
    )
'''
    return write_proposal(output, source)


def execute(args):
    try:
        if args.case:
            if args.check:
                raise ProposalError("--check is only supported with --from-run")
            path = propose(args.case, args.output)
            source = {"case": args.case}
        else:
            path = propose_from_run(args.from_run, args.output, args.check)
            source = {"from_run": args.from_run, "check": args.check}
    except ProposalError as exc:
        print(f"Cannot generate regression: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"proposal": str(path), **source, "application_code_modified": False}))
    return 0
