from pathlib import Path

import yaml

from autotest_skill.config import Config
from autotest_skill.demo import start_demo
from autotest_skill.runner import run_config


def demo_config(base):
    data = yaml.safe_load(Path("examples/api.yaml").read_text())
    data["allowed_origins"] = [base]
    for check in data["checks"]:
        check["spec"]["base_url"] = base
    return Config.model_validate(data)


def test_auth_captures_and_access_checks_have_private_evidence(tmp_path):
    with start_demo() as (base, state):
        report, folder = run_config(demo_config(base), tmp_path, tmp_path / "runs")
        assert report.exit_code() == 0
        assert len(report.results) == 4
        artifacts = "".join(p.read_text() for p in folder.glob("*.json"))
        for token in state.sessions:
            assert token not in artifacts
        assert report.results[-1].actual["status"] == 403


def test_seeded_ownership_bug_is_confirmed(tmp_path):
    with start_demo(defects=True) as (base, _):
        report, _ = run_config(demo_config(base), tmp_path, tmp_path / "runs")
        assert report.exit_code() == 1
        assert report.results[-1].id == "api.foreign-object"
        assert report.results[-1].status == "failed"
        assert report.results[-1].actual["status"] == 200
