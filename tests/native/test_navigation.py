from autotest_skill.demo import start_demo

from . import helpers

pytestmark = helpers.pytestmark


def test_native_screens_buttons_and_system_back():
    with start_demo(port=8765):
        helpers.execute_native(
            66,
            [
                {"action": "click", "accessibility_id": "Sign in"},
                {"action": "scroll_to", "accessibility_id": "Status"},
                {
                    "action": "expect_text",
                    "accessibility_id": "Status",
                    "value": "Signed in as alice",
                },
                {"action": "scroll_to", "accessibility_id": "View items"},
                {"action": "click", "accessibility_id": "View items"},
                {"action": "expect_text", "text": "Saved items"},
                {"action": "expect_text", "accessibility_id": "Items", "value": "Alice item × 1"},
                {"action": "click", "accessibility_id": "Back to editor"},
                {"action": "expect_text", "text": "Autotest Demo"},
                {"action": "scroll_to", "accessibility_id": "View items"},
                {"action": "click", "accessibility_id": "View items"},
                {"action": "expect_text", "text": "Saved items"},
                {"action": "back"},
                {"action": "expect_text", "text": "Autotest Demo"},
            ],
        )
