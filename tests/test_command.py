import sys
from pathlib import Path
from autotest_skill.config import Config
from autotest_skill.context import Context
from autotest_skill.adapters.command import run
from autotest_skill.artifacts import create_run


def invoke(tmp_path, source):
    (tmp_path / "test_target.py").write_text(source)
    config = Config.model_validate({"project": "command-test", "allow_project_commands": True,
        "checks": [{"id": "suite", "kind": "command", "requirement": "repository tests",
        "oracle": "Selected repository tests execute and pass", "spec": {
            "argv": [sys.executable, "-m", "pytest", "test_target.py", "-q"], "runner": "pytest"}}]})
    _, folder = create_run(tmp_path / "runs")
    result = run(config.checks[0], Context(config, tmp_path, folder))
    return result, folder


def test_failed_passed_and_skipped_outcomes_are_distinct(tmp_path):
    result, _ = invoke(tmp_path, 'import pytest\ndef test_ok(): assert 2 + 2 == 4\ndef test_bad(): assert 1 == 2\n@pytest.mark.skip(reason="control")\ndef test_skip(): pass\n')
    assert result.status == "failed"
    assert result.actual["exit_code"] == 1
    assert result.test_counts["passed"] == 1
    assert result.test_counts["failed"] == 1
    assert result.test_counts["skipped"] == 1


def test_zero_test_run_is_blocked(tmp_path):
    result, _ = invoke(tmp_path, "# no tests\n")
    assert result.status == "blocked"
    assert result.actual["exit_code"] == 5


def test_command_evidence_is_redacted(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTOTEST_COMMAND_TOKEN", "synthetic-command-secret")
    result, folder = invoke(tmp_path, 'import os\ndef test_output(): print(os.environ["AUTOTEST_COMMAND_TOKEN"]); assert True\n')
    assert result.status == "passed"
    assert "synthetic-command-secret" not in (folder / result.evidence[0]).read_text()
