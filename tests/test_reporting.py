from autotest_skill.config import Config
from autotest_skill.demo import start_demo
from autotest_skill.reporting import escape
from autotest_skill.runner import run_config


def test_readable_report_preserves_failed_and_blocked_scope(tmp_path):
    with start_demo() as (base, _):
        config = Config.model_validate(
            {
                "project": "readable",
                "allowed_origins": [base],
                "checks": [
                    {
                        "id": "wrong",
                        "kind": "http",
                        "requirement": "READY",
                        "oracle": "Declared response has expected ready false",
                        "spec": {
                            "base_url": base,
                            "path": "/health",
                            "expected_json": {"ready": False},
                        },
                    },
                    {
                        "id": "dependent",
                        "kind": "http",
                        "depends_on": ["wrong"],
                        "requirement": "READY",
                        "oracle": "Prerequisite must pass reliably",
                        "spec": {"base_url": base, "path": "/health"},
                    },
                ],
            }
        )
        report, folder = run_config(config, tmp_path, tmp_path / "runs")
        text = (folder / "report.md").read_text()
        assert "failed" in text and "blocked" in text and report.exit_code() == 1
        assert "wrong.http.json" in text and "Declared response" in text
        assert "&lt;" in escape("<script>alert(1)</script>")
        assert "\\[" in escape("[override](https://evil.example)")
