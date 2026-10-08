"""Generated proposal: inspect the requirement/oracle before adopting in a project."""

import json
import os
from pathlib import Path

from autotest_skill.benchmark import case_config
from autotest_skill.demo import start_demo
from autotest_skill.runner import run_config

CASE = json.loads(
    '{"id": "api-idor", "check": "api.foreign-object", "target": "loopback API", "severity": "critical", "requirement": "API-OWNERSHIP", "oracle": "Alice gets 403 for Bob\'s item", "defect": "Ownership guard bypassed", "impact": "Disclosure of another user\'s object"}'
)


def test_declared_regression(tmp_path):
    defects = os.environ.get("AUTOTEST_REGRESSION_DEFECTS") == "1"
    with start_demo(defects=defects) as (base, _):
        config = case_config(CASE, base, defects)
        report, folder = run_config(config, Path.cwd(), tmp_path / "runs")
        result = next(r for r in report.results if r.id == CASE["check"])
        assert result.status == "passed", (result.reason, str(folder))
