import json

import pytest

from autotest_skill.demo import start_demo

from . import helpers
from .test_auth_forms import click, fill, scroll, status

pytestmark = helpers.pytestmark


@pytest.mark.parametrize("defects", [False, True], ids=["clean", "broken"])
def test_saved_work_reopens_and_matches_backend_with_seeded_false_save(defects):
    mode = "broken" if defects else "clean"
    with start_demo(port=8765) as (_, state):
        actions = [{"action": "expect_text", "text": "Autotest Demo"}, click("Sign in")]
        actions += (
            status("Signed in as alice") + fill("Name", "Native E2E work") + fill("Quantity", "2")
        )
        actions += [scroll("Save"), click("Save")] + status("Saved")
        actions += [
            scroll("View items"),
            click("View items"),
            {
                "action": "expect_text",
                "accessibility_id": "Items",
                "value": "Alice item × 1\nNative E2E work × 2",
            },
        ]
        report, _ = helpers.execute_native(
            f"70-{mode}",
            actions,
            expected_status="failed" if defects else "passed",
            apk=".autotest/android-build/autotest-demo.apk",
            fixture_defects=defects,
            wait_timeout=5,
        )
        items = [i for i in state.items.values() if i["name"] == "Native E2E work"]
        assert len(items) == (0 if defects else 1)
        if items:
            assert items[0]["owner"] == "alice" and items[0]["quantity"] == 2
        path = helpers.ROOT / f"docs/evidence/native-step-70-{mode}.json"
        evidence = json.loads(path.read_text())
        evidence["backend_items"] = items
        evidence["false_saved_feedback_observed"] = any(
            a["observed"] == "Saved" for a in report.results[0].actual["assertions"]
        )
        path.write_text(json.dumps(evidence, indent=2) + "\n")
