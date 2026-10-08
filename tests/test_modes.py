import json

from autotest_skill.config import Config
from autotest_skill.planner import select
from autotest_skill.runner import run_config


def modes_config():
    return Config.model_validate(
        {
            "project": "modes",
            "allowed_origins": ["http://localhost:8000"],
            "checks": [
                {
                    "id": "smoke",
                    "kind": "http",
                    "profiles": ["smoke", "release"],
                    "covers": ["src/core.py"],
                    "requirement": "READY",
                    "oracle": "Ready responds as declared",
                    "spec": {"base_url": "http://localhost:8000"},
                },
                {
                    "id": "deep",
                    "kind": "http",
                    "profiles": ["changed", "release"],
                    "covers": ["src/payment.py"],
                    "requirement": "DOMAIN",
                    "oracle": "Domain state matches the contract",
                    "spec": {"base_url": "http://localhost:8000"},
                },
            ],
        }
    )


def test_profiles_select_known_changes_and_record_interrupt(tmp_path):
    config = modes_config()
    assert [c.id for c in select(config, "smoke", ())] == ["smoke"]
    assert [c.id for c in select(config, "changed", ["src/payment.py"])] == ["deep"]
    assert [c.id for c in select(config, "changed", ["unknown.py"])] == ["smoke"]
    assert [c.id for c in select(config, "release", ())] == ["smoke", "deep"]
    calls = []

    def adapter(check, context):
        calls.append(check.id)
        if len(calls) == 2:
            raise KeyboardInterrupt
        return context.result(check, "passed", actual={"ready": True})

    report, folder = run_config(
        config, tmp_path, tmp_path / "runs", profile="release", resolver=lambda _: adapter
    )
    assert report.exit_code() == 130 and report.interrupted
    assert report.results[0].status == "passed" and report.results[1].status == "skipped"
    persisted = json.loads((folder / "result.json").read_text())
    assert persisted["interrupted"] and "Interrupted" in persisted["results"][1]["reason"]
    assert (folder / "reproduction.zip").is_file() and (folder / "report.md").is_file()
