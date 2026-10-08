import json
import os
from pathlib import Path

import pytest

from autotest_skill.config import Config
from autotest_skill.runner import run_config

ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.skipif(
    os.environ.get("AUTOTEST_RUN_ANDROID") != "1",
    reason="Actual emulator/Appium required; enable AUTOTEST_RUN_ANDROID=1",
)


def native_case(step, actions, **options):
    return Config.model_validate(
        {
            "project": f"native-step-{step}",
            "allow_mutations": True,
            "allow_device_controls": True,
            "allowed_origins": ["http://127.0.0.1:4723"],
            "budgets": {"seconds": 900, "max_requests": 1000, "retries": 0},
            "checks": [
                {
                    "id": f"native.step-{step}",
                    "kind": "android",
                    "mutating": True,
                    "requirement": f"APP-STEP-{step}",
                    "oracle": "Native actions end in explicitly asserted state and backend effect",
                    "spec": {
                        "udid": "emulator-5554",
                        "package": "com.autotest.demo",
                        "activity": ".MainActivity",
                        "reuse_runtime": True,
                        "reset": True,
                        "timeout": 300,
                        "wait_timeout": 20,
                        "actions": actions,
                        **options,
                    },
                }
            ],
        }
    )


def execute_native(step, actions, **options):
    report, folder = run_config(
        native_case(step, actions, **options), ROOT, ROOT / ".autotest/native-runs"
    )
    assert report.exit_code() == 0, (
        report.results[0].reason,
        report.results[0].actual,
        str(folder),
    )
    (ROOT / f"docs/evidence/native-step-{step}.json").write_text(
        json.dumps(
            {
                "run_id": report.run_id,
                "target_revision": report.target_revision,
                "target_dirty": report.target_dirty,
                "status": report.results[0].status,
                "actual": report.results[0].actual,
                "directory": str(folder),
            },
            indent=2,
        )
        + "\n"
    )
    return report, folder
