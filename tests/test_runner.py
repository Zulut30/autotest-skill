import sys

from autotest_skill.config import Config
from autotest_skill.runner import run_config


def test_missing_command_blocks_only_its_dependents(tmp_path):
    checks = []
    for identifier, argv, deps in (
        ("missing", ["autotest-unavailable-executable-9573"], []),
        ("dependent", [sys.executable, "-c", "print('must not run')"], ["missing"]),
        ("independent", [sys.executable, "-c", "print('ready')"], []),
    ):
        checks.append(
            {
                "id": identifier,
                "kind": "command",
                "requirement": "runner independence",
                "oracle": "Explicit command returns its expected result",
                "depends_on": deps,
                "spec": {"argv": argv},
            }
        )
    config = Config.model_validate(
        {"project": "test", "allow_project_commands": True, "checks": checks}
    )
    report, folder = run_config(config, tmp_path, tmp_path / "runs")
    assert [r.status for r in report.results] == ["blocked", "blocked", "passed"]
    assert report.exit_code() == 2
    assert (folder / "result.json").exists()
    assert report.finished_at


def test_empty_profile_remains_zero_execution(tmp_path):
    config = Config.model_validate(
        {
            "project": "test",
            "allow_project_commands": True,
            "checks": [
                {
                    "id": "only",
                    "kind": "command",
                    "requirement": "profile",
                    "oracle": "Command completes successfully",
                    "profiles": ["release"],
                    "spec": {"argv": [sys.executable, "-c", "print('ready')"]},
                }
            ],
        }
    )
    report, _ = run_config(config, tmp_path, tmp_path / "runs", profile="smoke")
    assert report.exit_code() == 2
    assert report.counts() == {"skipped": 1}
