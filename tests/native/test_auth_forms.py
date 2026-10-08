from autotest_skill.demo import start_demo

from . import helpers

pytestmark = helpers.pytestmark


def scroll(locator):
    return {"action": "scroll_to", "accessibility_id": locator}


def click(locator):
    return {"action": "click", "accessibility_id": locator}


def fill(locator, value):
    return [
        scroll(locator),
        {"action": "fill", "accessibility_id": locator, "value": value},
        {"action": "hide_keyboard"},
    ]


def status(value):
    return [
        scroll("Status"),
        {"action": "expect_text", "accessibility_id": "Status", "value": value},
    ]


def test_native_forms_login_roles_and_revocation():
    with start_demo(port=8765) as (_, state):
        actions = (
            fill("Password", "wrong")
            + [click("Sign in")]
            + status("Sign in failed. Check credentials or network.")
        )
        actions += (
            fill("Password", "demo-password")
            + [scroll("Sign in"), click("Sign in")]
            + status("Signed in as alice")
        )
        actions += [scroll("Check admin access"), click("Check admin access")] + status(
            "Admin denied"
        )
        actions += [scroll("Save"), click("Save")] + status("Name must contain 1 to 100 characters")
        actions += (
            fill("Name", "Invalid native item")
            + fill("Quantity", "0")
            + [scroll("Save"), click("Save")]
            + status("Quantity must be between 1 and 100")
        )
        actions += [scroll("Sign out"), click("Sign out")] + status("Signed out")
        actions += (
            fill("Quantity", "1") + [scroll("Save"), click("Save")] + status("Please sign in")
        )
        actions += (
            fill("User", "admin")
            + [scroll("Sign in"), click("Sign in")]
            + status("Signed in as admin")
        )
        actions += [scroll("Check admin access"), click("Check admin access")] + status(
            "Admin allowed"
        )
        actions += [scroll("Sign out"), click("Sign out")] + status("Signed out")
        helpers.execute_native(67, actions, apk=".autotest/android-build/autotest-demo.apk")
        assert len(state.items) == 2 and not state.sessions


def test_expired_native_session_denies_save():
    with start_demo(port=8765) as (_, state):
        helpers.execute_native("67-login", [click("Sign in")] + status("Signed in as alice"))
        for record in state.sessions.values():
            record["expires"] = 0
        helpers.execute_native(
            "67-expiry",
            fill("Name", "Expired native item")
            + [scroll("Save"), click("Save")]
            + status("Session expired. Sign in again."),
            reset=False,
        )
        assert len(state.items) == 2
