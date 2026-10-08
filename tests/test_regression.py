import ast
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from autotest_skill import demo
from autotest_skill.cli import main
from autotest_skill.config import Config
from autotest_skill.demo import start_demo
from autotest_skill.regression import ProposalError, propose, propose_from_run
from autotest_skill.runner import run_config


def regression_config(base, **spec):
    return Config.model_validate(
        {
            "project": "reported-regression",
            "allowed_origins": [base],
            "allow_mutations": True,
            "budgets": {"retries": 0},
            "checks": [
                {
                    "id": "api.health",
                    "kind": "http",
                    "requirement": "READINESS",
                    "oracle": "The declared test target is functionally ready",
                    "spec": {"base_url": base, "path": "/health", "expected_json": {"ready": True}},
                },
                {
                    "id": "web.guidance",
                    "kind": "web",
                    "mutating": True,
                    "requirement": "WEB-AUTH-GUIDANCE",
                    "oracle": "Saving guidance updates after a successful authenticated transition",
                    "depends_on": ["api.health"],
                    "spec": {
                        "base_url": base,
                        "timeout": 0.2,
                        "actions": [
                            {"action": "click", "role": "button", "name": "Sign in"},
                            {"action": "expect_text", "text": "Signed in as alice"},
                            {"action": "expect_enabled", "role": "button", "name": "Save"},
                            {
                                "action": "expect_text",
                                "test_id": "save-help",
                                "value": "Ready to save items.",
                            },
                        ],
                        **spec,
                    },
                },
                {
                    "id": "api.unrelated",
                    "kind": "http",
                    "requirement": "READINESS",
                    "oracle": "An independent health check remains unrelated to the saved scenario",
                    "spec": {"base_url": base, "path": "/health"},
                },
            ],
        }
    )


@pytest.fixture
def stale_run(tmp_path):
    with start_demo() as (base, state):
        html = (Path(demo.__file__).parent / "assets/demo.html").read_text()
        state.html_override = html.replace(
            "saving?'Saving item…':'Ready to save items.'", "'Sign in before saving items.'"
        )
        assert state.html_override != html
        report, folder = run_config(regression_config(base), tmp_path, tmp_path / "runs")
        assert report.results[1].status == "failed"
        yield base, state, report, folder


def test_report_proposal_replays_real_failure_and_passes_after_fix(
    stale_run, tmp_path, monkeypatch
):
    base, state, _, folder = stale_run
    proposal = tmp_path / "test_reported_guidance.py"
    assert (
        main(
            [
                "regression",
                "--from-run",
                str(folder),
                "--check",
                "web.guidance",
                "--output",
                str(proposal),
            ]
        )
        == 0
    )
    syntax = ast.parse(proposal.read_text())
    payload = next(
        node.value.args[0].value
        for node in syntax.body
        if isinstance(node, ast.Assign) and node.targets[0].id == "CONFIG"
    )
    data = json.loads(payload)
    assert [c["id"] for c in data["checks"]] == ["api.health", "web.guidance"]
    assert data["budgets"]["retries"] == 0
    assert not data["allow_project_commands"] and not data["allow_device_controls"]
    assert proposal.stat().st_mode & 0o777 == 0o600
    monkeypatch.setenv("AUTOTEST_REGRESSION_BASE_URL", base)
    for mode, expected_exit in [("broken", 1), ("fixed", 0)]:
        if mode == "fixed":
            state.html_override = None
        executed = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                str(proposal),
                "-q",
                "--basetemp",
                str(tmp_path / mode),
            ],
            cwd=tmp_path,
            env=os.environ.copy(),
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )
        assert executed.returncode == expected_exit, executed.stdout + executed.stderr
    with pytest.raises(ProposalError, match="overwrite"):
        propose_from_run(folder, proposal)


@pytest.mark.parametrize("status", ["passed", "blocked", "observation", "skipped", "error"])
def test_nonfailed_results_cannot_generate_regressions(stale_run, tmp_path, status):
    _, _, _, folder = stale_run
    source = folder / "result.json"
    report = json.loads(source.read_text())
    report["results"][1]["status"] = status
    source.write_text(json.dumps(report))
    with pytest.raises(ProposalError, match="failed web check"):
        propose_from_run(folder, tmp_path / "proposal.py")
    assert not (tmp_path / "proposal.py").exists()


def test_mismatched_runs_and_unreliable_prerequisites_are_rejected(stale_run, tmp_path):
    _, _, _, folder = stale_run
    source = folder / "result.json"
    original = json.loads(source.read_text())
    for mutate, message in [
        (lambda r: r.update(run_id="another-run"), "same completed"),
        (lambda r: r.update(interrupted=True), "same completed"),
        (lambda r: r["results"][0].update(flaky=True), "prerequisites"),
    ]:
        modified = json.loads(json.dumps(original))
        mutate(modified)
        source.write_text(json.dumps(modified))
        with pytest.raises(ProposalError, match=message):
            propose_from_run(folder, tmp_path / "proposal.py")


def test_redacted_inputs_are_not_replayed_as_credentials(stale_run, tmp_path):
    _, _, _, folder = stale_run
    source = folder / "reproduction.json"
    document = json.loads(source.read_text())
    document["configuration"]["checks"][1]["spec"]["actions"][0]["value"] = "[REDACTED]"
    source.write_text(json.dumps(document))
    with pytest.raises(ProposalError, match="environment bindings"):
        propose_from_run(folder, tmp_path / "proposal.py")
    assert not (tmp_path / "proposal.py").exists()


def test_http_credential_bindings_survive_redaction_and_generated_replay(
    stale_run, tmp_path, monkeypatch
):
    base, state, _, _ = stale_run
    monkeypatch.setenv("TEST_FIXTURE_PASSWORD", "demo-password")
    data = regression_config(base).model_dump()
    data["checks"].insert(
        1,
        {
            "id": "api.login",
            "kind": "http",
            "mutating": True,
            "depends_on": ["api.health"],
            "requirement": "AUTH",
            "oracle": "The isolated account receives an authenticated session",
            "spec": {
                "base_url": base,
                "path": "/api/login",
                "method": "POST",
                "json_body": {"username": "alice"},
                "json_env": {"password": "TEST_FIXTURE_PASSWORD"},
                "capture": {"auth": "authorization"},
            },
        },
    )
    data["checks"].insert(
        2,
        {
            "id": "api.profile",
            "kind": "http",
            "depends_on": ["api.login"],
            "requirement": "AUTH",
            "oracle": "The authenticated profile belongs to Alice",
            "spec": {
                "base_url": base,
                "path": "/api/me",
                "headers_from": {"Authorization": "auth"},
                "expected_json": {"username": "alice"},
            },
        },
    )
    data["checks"][3]["depends_on"] = ["api.profile"]
    report, folder = run_config(Config.model_validate(data), tmp_path, tmp_path / "credential-runs")
    assert report.results[3].status == "failed"
    proposal = propose_from_run(folder, tmp_path / "test_bound_credentials.py")
    assert "demo-password" not in proposal.read_text()
    assert "TEST_FIXTURE_PASSWORD" in proposal.read_text()
    state.html_override = None
    monkeypatch.setenv("AUTOTEST_REGRESSION_BASE_URL", base)
    executed = subprocess.run(
        [sys.executable, "-m", "pytest", str(proposal), "-q"],
        cwd=tmp_path,
        env=os.environ.copy(),
        check=False,
        text=True,
        capture_output=True,
        timeout=30,
    )
    assert executed.returncode == 0, executed.stdout + executed.stderr


def test_inline_sensitive_ui_values_cannot_be_exported(stale_run, tmp_path):
    _, _, _, folder = stale_run
    source = folder / "reproduction.json"
    document = json.loads(source.read_text())
    document["configuration"]["checks"][1]["spec"]["actions"].insert(
        0, {"action": "fill", "label": "Password", "value": "must-not-be-exported"}
    )
    source.write_text(json.dumps(document))
    with pytest.raises(ProposalError, match="Sensitive UI inputs"):
        propose_from_run(folder, tmp_path / "proposal.py")
    assert not (tmp_path / "proposal.py").exists()


def test_secret_bound_ui_failure_can_generate_and_replay(stale_run, tmp_path, monkeypatch):
    base, state, _, _ = stale_run
    monkeypatch.setenv("TEST_FIXTURE_PASSWORD", "demo-password")
    data = regression_config(base).model_dump()
    data["checks"][1]["spec"]["actions"].insert(
        0, {"action": "fill", "label": "Password", "value_env": "TEST_FIXTURE_PASSWORD"}
    )
    report, folder = run_config(Config.model_validate(data), tmp_path, tmp_path / "ui-bound-runs")
    assert report.results[1].status == "failed"
    assert not list(folder.glob("*.png"))
    proposal = propose_from_run(folder, tmp_path / "test_ui_bound.py")
    assert "demo-password" not in proposal.read_text()
    state.html_override = None
    monkeypatch.setenv("AUTOTEST_REGRESSION_BASE_URL", base)
    executed = subprocess.run(
        [sys.executable, "-m", "pytest", str(proposal), "-q"],
        cwd=tmp_path,
        env=os.environ.copy(),
        check=False,
        text=True,
        capture_output=True,
        timeout=30,
    )
    assert executed.returncode == 0, executed.stdout + executed.stderr


def test_report_strings_are_data_in_generated_python(stale_run, tmp_path):
    _, _, _, folder = stale_run
    oracle = "PROVENANCE_JSON CONFIG_JSON {config_json} ''); raise SystemExit('untrusted'); #"
    result_path = folder / "result.json"
    report = json.loads(result_path.read_text())
    report["results"][1]["oracle"] = oracle
    result_path.write_text(json.dumps(report))
    repro_path = folder / "reproduction.json"
    reproduction = json.loads(repro_path.read_text())
    reproduction["configuration"]["checks"][1]["oracle"] = oracle
    repro_path.write_text(json.dumps(reproduction))
    proposal = propose_from_run(folder, tmp_path / "proposal.py")
    syntax = ast.parse(proposal.read_text())
    compile(syntax, str(proposal), "exec")
    payload = next(
        node.value.args[0].value
        for node in syntax.body
        if isinstance(node, ast.Assign) and node.targets[0].id == "SOURCE_REPORT"
    )
    assert json.loads(payload)["oracle"] == oracle
    assert all(
        isinstance(node, (ast.Expr, ast.Import, ast.ImportFrom, ast.Assign, ast.FunctionDef))
        for node in syntax.body
    )


def test_seeded_proposals_still_work_and_refuse_overwrite(tmp_path):
    proposal = propose("api-idor", tmp_path / "test_idor.py")
    compile(proposal.read_text(), str(proposal), "exec")
    with pytest.raises(ProposalError, match="overwrite"):
        propose("api-idor", proposal)
