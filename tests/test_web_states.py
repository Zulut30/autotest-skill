import json
from pathlib import Path

import pytest
from playwright.sync_api import expect, sync_playwright

from autotest_skill.config import Config
from autotest_skill.demo import start_demo
from autotest_skill.doctor import browser_path
from autotest_skill.runner import run_config


def state_config(base, actions, **spec):
    return Config.model_validate(
        {
            "project": "web-state-regression",
            "allowed_origins": [base],
            "allow_mutations": True,
            "budgets": {"seconds": 60, "retries": 0},
            "checks": [
                {
                    "id": "web.states",
                    "kind": "web",
                    "mutating": True,
                    "requirement": "WEB-AUTH-GUIDANCE",
                    "oracle": "Saving controls and guidance agree with the authenticated state",
                    "spec": {"base_url": base, "actions": actions, "timeout": 2, **spec},
                }
            ],
        }
    )


def button(action, name):
    return {"action": action, "role": "button", "name": name}


def guidance(value):
    return {"action": "expect_text", "test_id": "save-help", "value": value}


def test_auth_guidance_tracks_login_reload_validation_save_and_logout(tmp_path):
    actions = [
        button("expect_disabled", "Save"),
        button("expect_hidden", "Sign out"),
        guidance("Sign in before saving items."),
        button("click", "Sign in"),
        {"action": "expect_text", "text": "Signed in as alice"},
        button("expect_enabled", "Save"),
        button("expect_visible", "Sign out"),
        guidance("Ready to save items."),
        {"action": "reload"},
        {"action": "expect_text", "text": "Signed in as alice"},
        button("expect_enabled", "Save"),
        guidance("Ready to save items."),
        button("click", "Save"),
        {"action": "expect_text", "text": "Name is required."},
        button("expect_enabled", "Save"),
        guidance("Ready to save items."),
        {"action": "fill", "label": "Name", "value": "State verified work"},
        button("click", "Save"),
        {"action": "expect_text", "text": "Saved"},
        button("expect_enabled", "Save"),
        guidance("Ready to save items."),
        button("click", "Sign out"),
        {"action": "expect_text", "text": "Signed out. Please sign in."},
        button("expect_disabled", "Save"),
        button("expect_hidden", "Sign out"),
        guidance("Sign in before saving items."),
        {"action": "reload"},
        button("expect_disabled", "Save"),
        button("expect_hidden", "Sign out"),
        guidance("Sign in before saving items."),
    ]
    with start_demo() as (base, state):
        report, folder = run_config(state_config(base, actions), tmp_path, tmp_path / "runs")
        assert report.exit_code() == 0, report.results[0].reason
        assert not state.sessions
        assert [i["name"] for i in state.items.values()].count("State verified work") == 1
        assertions = json.loads((folder / "web.states.web.json").read_text())["assertions"]
        assert all(a["status"] == "passed" for a in assertions)
        assert any(a["actual"].get("text") == "Ready to save items." for a in assertions)


def test_state_failure_reports_expected_and_observed_disabled_control(tmp_path):
    with start_demo() as (base, _):
        report, _ = run_config(
            state_config(base, [button("expect_enabled", "Save")], timeout=0.2),
            tmp_path,
            tmp_path / "runs",
        )
    assert report.results[0].status == "failed"
    assertion = report.results[0].actual["assertions"][0]
    assert assertion["expected"]["enabled"] is True
    assert assertion["actual"]["enabled"] is False
    assert assertion["status"] == "failed"


@pytest.mark.parametrize("trigger", ["refresh", "save", "reload"])
def test_expired_session_clears_items_and_never_reenables_save(trigger):
    with start_demo() as (base, state), sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=browser_path(), headless=True)
        try:
            page = browser.new_page()
            page.goto(base)
            page.get_by_role("button", name="Sign in", exact=True).click()
            expect(page.get_by_text("Signed in as alice", exact=True)).to_be_visible()
            expect(page.get_by_text("Alice item × 1", exact=True)).to_be_visible()
            with state.lock:
                for record in state.sessions.values():
                    record["expires"] = 0
            if trigger == "refresh":
                page.get_by_role("button", name="Reload items", exact=True).click()
            elif trigger == "save":
                page.get_by_label("Name", exact=True).fill("Expired session must not save")
                page.get_by_role("button", name="Save", exact=True).click()
            else:
                page.reload()
            expect(page.get_by_text("Session expired. Please sign in.", exact=True)).to_be_visible()
            expect(page.get_by_role("button", name="Save", exact=True)).to_be_disabled()
            expect(page.get_by_test_id("save-help")).to_have_text("Sign in before saving items.")
            expect(page.locator("#items li")).to_have_count(0)
            assert page.evaluate("localStorage.getItem('demo-authorization')") is None
            assert len(state.items) == 2
        finally:
            browser.close()


def test_assertion_evidence_withholds_sensitive_text(tmp_path):
    from autotest_skill import demo

    with start_demo() as (base, state):
        state.html_override = (
            (Path(demo.__file__).parent / "assets/demo.html")
            .read_text()
            .replace(
                "<main>",
                '<main><p data-testid="private-note" data-autotest-sensitive>private-fixture-note</p>',
            )
        )
        report, folder = run_config(
            state_config(
                base,
                [{"action": "expect_text", "test_id": "private-note", "value": "Public copy"}],
                timeout=0.2,
            ),
            tmp_path,
            tmp_path / "runs",
        )
        assert report.results[0].status == "failed"
        assert report.results[0].actual["assertions"][0]["actual"]["text"] == "[WITHHELD]"
        assert "private-fixture-note" not in "".join(p.read_text() for p in folder.glob("*.json"))


@pytest.mark.parametrize(
    "expected_text,baseline,status",
    [
        ("Ready to save items.", None, "passed"),
        ("Missing expected guidance", None, "failed"),
        ("Ready to save items.", "approved.png", "blocked"),
    ],
)
def test_secret_bound_actions_keep_functional_result_without_screenshot(
    tmp_path, monkeypatch, expected_text, baseline, status
):
    monkeypatch.setenv("TEST_FIXTURE_PASSWORD", "demo-password")
    with start_demo() as (base, _):
        report, folder = run_config(
            state_config(
                base,
                [
                    {"action": "fill", "label": "Password", "value_env": "TEST_FIXTURE_PASSWORD"},
                    button("click", "Sign in"),
                    guidance(expected_text),
                ],
                timeout=0.2,
                baseline=baseline,
            ),
            tmp_path,
            tmp_path / "runs",
        )
        assert report.results[0].status == status
        assert report.results[0].actual["screenshot_withheld"]
        assert not list(folder.glob("*.png"))
        assert "demo-password" not in "".join(p.read_text() for p in folder.glob("*.json"))
