import json

from autotest_skill.artifacts import write_json
from autotest_skill.config import Config
from autotest_skill.runner import run_config


def test_flaky_retry_keeps_both_artifacts_and_blocks_dependents(tmp_path):
    config = Config.model_validate(
        {
            "project": "retry",
            "checks": [
                {
                    "id": "sometimes",
                    "kind": "http",
                    "requirement": "RELIABILITY",
                    "oracle": "Declared value is present on every attempt",
                    "spec": {"base_url": "http://localhost:8000"},
                },
                {
                    "id": "dependent",
                    "kind": "http",
                    "depends_on": ["sometimes"],
                    "requirement": "RELIABILITY",
                    "oracle": "Prerequisite passes consistently first",
                    "spec": {"base_url": "http://localhost:8000"},
                },
            ],
            "allowed_origins": ["http://localhost:8000"],
        }
    )
    calls = []

    def adapter(check, context):
        calls.append(check.id)
        number = len(calls)
        write_json(context.folder, "actual.json", {"attempt_number": number}, context.redactor)
        return context.result(
            check,
            "failed" if number == 1 else "passed",
            actual={"attempt_number": number},
            evidence=["actual.json"],
        )

    report, folder = run_config(config, tmp_path, tmp_path / "runs", resolver=lambda _: adapter)
    result = report.results[0]
    assert result.flaky and report.exit_code() == 1
    assert report.results[1].status == "blocked" and calls == ["sometimes", "sometimes"]
    assert result.attempts[0]["actual"]["attempt_number"] == 1
    assert (
        json.loads((folder / result.attempts[0]["evidence"][0]).read_text())["attempt_number"] == 1
    )
    assert (
        json.loads((folder / result.attempts[1]["evidence"][0]).read_text())["attempt_number"] == 2
    )
