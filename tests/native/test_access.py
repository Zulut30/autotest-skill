import pytest

from autotest_skill.demo import start_demo

from . import helpers
from .test_auth_forms import click, scroll, status

pytestmark = helpers.pytestmark


@pytest.mark.parametrize("guard", ["role", "ownership"])
@pytest.mark.parametrize("defects", [False, True], ids=["clean", "broken"])
def test_native_role_and_ownership_guards_detect_seeded_backend_bypass(guard, defects):
    mode = "broken" if defects else "clean"
    with start_demo(defects=defects, port=8765) as (_, state):
        button, expected = (
            ("Check admin access", "Admin denied")
            if guard == "role"
            else ("Inspect foreign item", "Foreign item denied")
        )
        actions = [{"action": "expect_text", "text": "Autotest Demo"}, click("Sign in")] + status(
            "Signed in as alice"
        )
        actions += [scroll(button), click(button)] + status(expected)
        helpers.execute_native(
            f"77-{guard}-{mode}",
            actions,
            expected_status="failed" if defects else "passed",
            apk=".autotest/android-build/autotest-demo.apk",
            fixture_defects=False,
            wait_timeout=5,
        )
        assert len(state.items) == 2
