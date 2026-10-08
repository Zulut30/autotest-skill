import subprocess

from autotest_skill.demo import start_demo
from autotest_skill.tooling import binary

from . import helpers
from .test_auth_forms import click, fill, scroll, status

pytestmark = helpers.pytestmark


def test_network_failure_recovery_rotation_and_keyboard_visibility():
    adb = [binary("adb"), "-s", "emulator-5554", "shell", "settings"]
    previous = subprocess.run(
        adb + ["get", "secure", "show_ime_with_hard_keyboard"],
        capture_output=True,
        text=True,
        timeout=10,
        check=True,
    ).stdout.strip()
    subprocess.run(
        adb + ["put", "secure", "show_ime_with_hard_keyboard", "1"], timeout=10, check=True
    )
    try:
        with start_demo(port=8765) as (_, state):
            actions = [{"action": "expect_text", "text": "Autotest Demo"}, click("Sign in")]
            actions += status("Signed in as alice") + fill("Name", "Network native item")
            actions += fill("API URL", "http://10.0.2.2:1") + [scroll("Save"), click("Save")]
            actions += status("Saving")
            actions += status("Could not save. Check network and try again.")
            actions += fill("API URL", "http://10.0.2.2:8765") + [scroll("Save"), click("Save")]
            actions += status("Saving")
            actions += status("Saved")
            actions += [
                {"action": "rotate", "orientation": "LANDSCAPE"},
                {"action": "scroll_to", "text": "Autotest Demo"},
                {"action": "expect_text", "text": "Autotest Demo"},
                {"action": "rotate", "orientation": "PORTRAIT"},
                scroll("Name"),
                click("Name"),
                {"action": "expect_keyboard", "enabled": True},
                {"action": "expect_not_occluded", "accessibility_id": "Name"},
                {"action": "hide_keyboard"},
                {"action": "expect_keyboard", "enabled": False},
                scroll("View items"),
                click("View items"),
                {
                    "action": "expect_text",
                    "accessibility_id": "Items",
                    "value": "Alice item × 1\nNetwork native item × 1",
                },
            ]
            report, _ = helpers.execute_native(
                69, actions, apk=".autotest/android-build/autotest-demo.apk", fixture_delay_ms=4000
            )
            actual = report.results[0].actual
            assert actual["restored_orientation"] == "PORTRAIT"
            assert actual["viewports"][0]["width"] > actual["viewports"][0]["height"]
            assert actual["viewports"][1]["height"] > actual["viewports"][1]["width"]
            assert len([i for i in state.items.values() if i["name"] == "Network native item"]) == 1
    finally:
        restore = (
            ["delete", "secure", "show_ime_with_hard_keyboard"]
            if previous == "null"
            else ["put", "secure", "show_ime_with_hard_keyboard", previous]
        )
        subprocess.run(adb + restore, timeout=10, check=True)
