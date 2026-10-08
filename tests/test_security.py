import secrets

from autotest_skill.config import Config
from autotest_skill.runner import run_config


def security_config(tool, path=".", **options):
    return Config.model_validate(
        {
            "project": "security",
            "budgets": {"retries": 0},
            "checks": [
                {
                    "id": "security.scan",
                    "kind": "security",
                    "requirement": "SEC-SCAN",
                    "oracle": "Configured source scope has no matching unsafe patterns",
                    "spec": {"tool": tool, "path": path, **options},
                }
            ],
        }
    )


def test_credential_control_is_found_without_leaking_value(tmp_path):
    value = secrets.token_hex(20)
    source = tmp_path / "app.py"
    source.write_text('api_key = "' + value + '"\n')
    report, folder = run_config(security_config("secrets", "app.py"), tmp_path, tmp_path / "runs")
    assert report.results[0].status == "failed"
    assert report.results[0].actual["findings"][0]["line"] == 1
    assert value not in (folder / "result.json").read_text()
    assert value not in (folder / "security.scan.security.json").read_text()
    source.write_text('import os\napi_key = os.environ["API_KEY"]\n')
    clean, _ = run_config(security_config("secrets", "app.py"), tmp_path, tmp_path / "runs")
    assert clean.exit_code() == 0


def test_real_pinned_dependency_advisory(tmp_path):
    pins = tmp_path / "requirements.txt"
    pins.write_text("urllib3==1.26.5\n")
    report, _ = run_config(
        security_config("dependencies", "requirements.txt"), tmp_path, tmp_path / "runs"
    )
    assert report.results[0].status == "failed", report.results[0].reason
    actual = report.results[0].actual
    assert actual["audited_dependencies"] == 1 and actual["findings"]
    assert actual["findings"][0]["classification"] == "potential_issue"


def test_dependency_urls_are_not_executed(tmp_path):
    (tmp_path / "requirements.txt").write_text("danger @ https://example.com/file.whl\n")
    report, _ = run_config(
        security_config("dependencies", "requirements.txt"), tmp_path, tmp_path / "runs"
    )
    assert report.results[0].status == "blocked"


def test_real_semgrep_rules_and_clean_control(tmp_path):
    import pytest

    from autotest_skill.errors import Blocked
    from autotest_skill.tooling import binary

    try:
        binary("semgrep")
    except Blocked:
        pytest.skip("Optional Semgrep installation required")
    target = tmp_path / "app.py"
    target.write_text("import subprocess\nsubprocess.run(user_input, shell=True)\n")
    report, _ = run_config(security_config("semgrep", "app.py"), tmp_path, tmp_path / "runs")
    assert report.results[0].status == "failed", report.results[0].reason
    assert report.results[0].actual["findings"][0]["line"] == 2
    target.write_text('import subprocess\nsubprocess.run(["echo", "hello"], check=True)\n')
    clean, _ = run_config(security_config("semgrep", "app.py"), tmp_path, tmp_path / "runs")
    assert clean.exit_code() == 0, clean.results[0].reason


def test_real_gitleaks_redacts_control_and_clean_source_passes(tmp_path):
    import pytest

    from autotest_skill.errors import Blocked
    from autotest_skill.tooling import binary

    try:
        binary("gitleaks")
    except Blocked:
        pytest.skip("Optional Gitleaks installation required")
    source = tmp_path / "source"
    source.mkdir()
    value = "gh" + "p_" + secrets.token_hex(20)
    target = source / "app.py"
    target.write_text('github_token = "' + value + '"\n')
    report, folder = run_config(security_config("gitleaks", "source"), tmp_path, tmp_path / "runs")
    assert report.results[0].status == "failed", report.results[0].reason
    assert value not in (folder / "result.json").read_text()
    target.write_text('import os\ngithub_token = os.environ["GITHUB_TOKEN"]\n')
    clean, _ = run_config(security_config("gitleaks", "source"), tmp_path, tmp_path / "runs")
    assert clean.exit_code() == 0, clean.results[0].reason


def test_bounded_header_policy_checks_control_and_clean_target(tmp_path):
    from autotest_skill.demo import start_demo

    for defects in (False, True):
        with start_demo(defects=defects) as (base, _):
            data = {
                "project": "headers",
                "allowed_origins": [base],
                "budgets": {"retries": 0},
                "checks": [
                    {
                        "id": "headers.policy",
                        "kind": "security",
                        "requirement": "SEC-HEADERS",
                        "oracle": "Response has the declared nosniff header",
                        "spec": {"tool": "web_headers", "base_url": base, "path": "/health"},
                    }
                ],
            }
            report, _ = run_config(Config.model_validate(data), tmp_path, tmp_path / "runs")
            assert report.results[0].status == ("failed" if defects else "passed")
            assert report.results[0].actual["not_evaluated"]
