"""Real browser checks with origin boundaries, budgets and masked screenshots."""

import os
import sys
from urllib.parse import urlsplit
from ..artifacts import safe_file, write_json
from ..doctor import browser_path
from ..errors import Blocked
from ..policy import require_url, request_url
from ..secrets import SENSITIVE


def locate(page, action):
    if action.role:
        return page.get_by_role(action.role, name=action.name, exact=True)
    if action.label:
        return page.get_by_label(action.label, exact=True)
    if action.test_id:
        return page.get_by_test_id(action.test_id)
    if action.text:
        return page.get_by_text(action.text, exact=True)
    raise ValueError("Action requires a semantic locator")


def run(check, context):
    from playwright.sync_api import sync_playwright, expect, TimeoutError as BrowserTimeout
    spec = check.spec
    url = request_url(context.config, spec.base_url, spec.path)
    errors, denied, http_errors, expected_http_errors, evidence = [], [], [], [], []
    actual = {}
    console_records = []
    def unexpected_console():
        return [record for record in console_records if not (
            record["text"].startswith("Failed to load resource:") and
            any(item["url"] == record["url"] for item in expected_http_errors))]
    status, reason = "passed", ""
    def route_request(route):
        try:
            require_url(context.config, route.request.url)
            context.consume("requests")
            route.continue_()
        except (Blocked, ValueError) as exc:
            denied.append(context.redactor.text(str(exc)))
            route.abort()
    def on_response(response):
        if response.status >= 400:
            collection = expected_http_errors if response.status in spec.allowed_http_errors.get(urlsplit(response.url).path, []) else http_errors
            collection.append({"url": response.url, "status": response.status})
        if "/api/login" in response.url and response.status == 200:
            try:
                for key, value in response.json().items():
                    if SENSITIVE.search(key):
                        context.redactor.add(value)
            except Exception:
                pass
    with sync_playwright() as pw:
        try:
            browser = pw.chromium.launch(executable_path=browser_path(), headless=True,
                args=["--force-webrtc-ip-handling-policy=disable_non_proxied_udp"])
        except Exception as exc:
            raise Blocked("Chromium is unavailable; install a Playwright browser or set AUTOTEST_BROWSER_PATH") from exc
        session = browser.new_context(viewport={"width": spec.viewport[0], "height": spec.viewport[1]},
                                      service_workers="block", locale="en-US", color_scheme="light", device_scale_factor=1)
        session.route("**/*", route_request)
        page = session.new_page()
        page.on("pageerror", lambda error: errors.append(context.redactor.text(str(error))))
        page.on("response", on_response)
        page.on("console", lambda message: console_records.append({"text": context.redactor.text(message.text),
                "url": message.location.get("url", "")}) if message.type == "error" else None)
        page.set_default_timeout(min(spec.timeout, context.remaining()) * 1000)
        try:
            context.consume("actions")
            response = page.goto(url, wait_until="domcontentloaded", timeout=min(spec.timeout, context.remaining()) * 1000)
            actual["navigation_status"] = response.status if response else None
            for index, action in enumerate(spec.actions):
                context.consume("actions")
                page.set_default_timeout(min(spec.timeout, context.remaining()) * 1000)
                actual["last_action"] = index
                value = context.redactor.binding(action.value_env) if action.value_env else action.value
                if action.action == "goto":
                    page.goto(request_url(context.config, spec.base_url, action.path or "/"), wait_until="domcontentloaded")
                elif action.action == "reload":
                    page.reload(wait_until="domcontentloaded")
                elif action.action == "expect_url":
                    page.wait_for_url(request_url(context.config, spec.base_url, action.path or "/"))
                elif action.action == "screenshot":
                    pass
                else:
                    target = locate(page, action)
                    if target.count() > 1:
                        raise Blocked("Configured semantic locator is ambiguous")
                    if action.action == "click": target.click()
                    elif action.action == "double_click":
                        context.consume("actions")
                        target.dblclick()
                    elif action.action == "fill": target.fill(value or "")
                    elif action.action == "press": target.press(value or "Enter")
                    elif action.action == "expect_text":
                        expect(target).to_be_visible()
                        if value is not None: expect(target).to_have_text(value)
                    elif action.action == "expect_visible": expect(target).to_be_visible()
            for text in spec.expected_text:
                expect(page.get_by_text(text, exact=True)).to_be_visible(timeout=min(spec.timeout, context.remaining()) * 1000)
            if spec.accessibility:
                from ..accessibility import inspect
                actual["accessibility"] = inspect(page)
                if actual["accessibility"]["violations"]:
                    status, reason = "failed", "Automated accessibility violations were found"
            if spec.check_layout:
                actual["layout"] = page.evaluate('() => ({viewport:innerWidth,document:document.documentElement.scrollWidth})')
                if actual["layout"]["document"] > actual["layout"]["viewport"]:
                    status, reason = "failed", "Document overflows the configured viewport"
            if spec.explore:
                from ..web_inspection import inspect_page
                actual["interface_map"] = inspect_page(page, context)
            if spec.check_console and (errors or http_errors or unexpected_console()):
                status, reason = "failed", "Page errors or unexpected HTTP failures were observed"
        except (AssertionError, BrowserTimeout) as exc:
            status, reason = "failed", f"Browser oracle was not satisfied ({type(exc).__name__})"
        except Blocked as exc:
            status, reason = "blocked", context.redactor.text(str(exc))
        finally:
            if denied:
                status, reason = "blocked", "Browser requests exceeded configured target or resource boundaries"
            if spec.check_console and status == "passed" and (errors or http_errors or unexpected_console()):
                status, reason = "failed", "Page errors or unexpected HTTP failures were observed"
            actual.update({"url": page.url, "page_errors": errors, "console_errors": unexpected_console(), "http_errors": http_errors, "expected_http_errors": expected_http_errors, "denied": denied,
                           "browser_version": browser.version, "viewport": spec.viewport})
            image = f"{check.id}.png"
            try:
                path = safe_file(context.folder, image)
                page.screenshot(path=str(path), mask=[page.locator('input[type="password"], [data-autotest-sensitive]')], timeout=3000)
                os.chmod(path, 0o600)
                evidence.append(image)
                actual["visual_conditions"] = {"browser_version": browser.version, "viewport": spec.viewport,
                    "platform": sys.platform, "device_scale_factor": 1, "color_scheme": "light"}
                if spec.baseline:
                    from ..visual import compare
                    actual["visual"] = compare(context.root, spec.baseline, path, actual["visual_conditions"])
                    if actual["visual"]["difference_ratio"] > spec.visual_threshold:
                        status, reason = "failed", "Screenshot differs from its approved baseline"
            except Blocked as exc:
                status, reason = "blocked", context.redactor.text(str(exc))
            except Exception:
                actual["screenshot_unavailable"] = True
                if spec.baseline:
                    status, reason = "error", "Visual comparison could not execute"
            browser.close()
    artifact = f"{check.id}.web.json"
    write_json(context.folder, artifact, actual, context.redactor)
    evidence.append(artifact)
    return context.result(check, status, expected={"text": spec.expected_text}, actual=actual, reason=reason, evidence=evidence)
