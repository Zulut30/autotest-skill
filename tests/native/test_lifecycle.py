from autotest_skill.demo import start_demo

from . import helpers
from .test_auth_forms import click, fill, scroll, status

pytestmark = helpers.pytestmark


def test_denied_permission_background_and_restart_preserve_scenario():
    with start_demo(port=8765) as (_, state):
        actions = [
            {"action": "expect_text", "text": "Autotest Demo"},
            scroll("Request microphone"),
            click("Request microphone"),
            {
                "action": "click",
                "resource_id": "com.android.packageinstaller:id/permission_deny_button",
            },
        ]
        actions += status("Permission denied. Basic features still work.")
        actions += [scroll("Sign in"), click("Sign in")] + status("Signed in as alice")
        actions += [{"action": "background"}, scroll("Status")] + status("Signed in as alice")
        actions += [{"action": "restart"}] + status("Session restored")
        actions += (
            fill("Name", "Lifecycle native item")
            + [scroll("Save"), click("Save")]
            + status("Saved")
        )
        actions += [
            scroll("View items"),
            click("View items"),
            {
                "action": "expect_text",
                "accessibility_id": "Items",
                "value": "Alice item × 1\nLifecycle native item × 1",
            },
        ]
        helpers.execute_native(68, actions)
        assert len([i for i in state.items.values() if i["name"] == "Lifecycle native item"]) == 1
