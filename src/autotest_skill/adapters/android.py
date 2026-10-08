"""Native actions on an explicit isolated Appium device with bounded transport."""

import hashlib
import json
import os
from pathlib import Path

import httpx
from urllib3.exceptions import ConnectTimeoutError, ReadTimeoutError

from ..artifacts import safe_file, write_json
from ..errors import Blocked
from ..policy import require_url
from ..secrets import SENSITIVE


def run(check, context):
    from appium import webdriver
    from appium.options.android import UiAutomator2Options
    from appium.webdriver.client_config import AppiumClientConfig
    from appium.webdriver.common.appiumby import AppiumBy
    from selenium.common.exceptions import (
        NoSuchElementException,
        TimeoutException,
        WebDriverException,
    )
    from selenium.webdriver.support.ui import WebDriverWait

    spec = check.spec
    if spec.baseline:
        raise Blocked(
            "Android image baselines are not supported; use explicit native UI assertions"
        )
    require_url(context.config, spec.server_url)
    context.consume("requests")
    try:
        health = httpx.get(spec.server_url + "/status", timeout=min(5, context.remaining()))
        if health.status_code != 200 or not health.json().get("value", {}).get("ready"):
            raise Blocked("Appium server is not ready")
    except (httpx.HTTPError, ValueError) as exc:
        raise Blocked("Appium server is unavailable") from exc
    capabilities = {
        "platformName": "Android",
        "appium:automationName": "UiAutomator2",
        "appium:udid": spec.udid,
        "appium:deviceName": spec.device_name,
        "appium:appPackage": spec.package,
        "appium:appActivity": spec.activity,
        "appium:noReset": not spec.reset,
        "appium:newCommandTimeout": max(10, int(spec.timeout)),
        "appium:androidInstallTimeout": int(min(spec.timeout, context.remaining()) * 1000),
        "appium:adbExecTimeout": int(min(spec.timeout, context.remaining()) * 1000),
        "appium:uiautomator2ServerLaunchTimeout": int(
            min(spec.timeout, context.remaining()) * 1000
        ),
        "appium:disableWindowAnimation": True,
        "appium:settings[waitForIdleTimeout]": 0,
        "appium:settings[waitForSelectorTimeout]": 0,
        "appium:skipLogcatCapture": True,
    }
    if spec.reuse_runtime:
        capabilities["appium:skipDeviceInitialization"] = True
        capabilities["appium:skipServerInstallation"] = True
    if spec.fixture_defects is not None or spec.fixture_delay_ms:
        arguments = []
        if spec.fixture_defects is not None:
            arguments.extend(["--ez", "defects", str(spec.fixture_defects).lower()])
        if spec.fixture_delay_ms:
            arguments.extend(["--ei", "transport_delay_ms", str(spec.fixture_delay_ms)])
        capabilities["appium:optionalIntentArguments"] = " ".join(arguments)
        capabilities["appium:forceAppLaunch"] = True
    apk_sha256 = None
    if spec.apk:
        root = Path(context.root).resolve()
        apk = (root / spec.apk).resolve()
        if root not in apk.parents or not apk.is_file():
            raise Blocked("Configured APK is missing or outside the project")
        capabilities["appium:app"] = str(apk)
        apk_sha256 = hashlib.sha256(apk.read_bytes()).hexdigest()
        capabilities["appium:enforceAppInstall"] = True
    client = AppiumClientConfig(
        remote_server_addr=spec.server_url,
        timeout=min(spec.timeout, context.remaining()),
        init_args_for_pool_manager={"init_args_for_pool_manager": {"retries": 0}},
    )
    driver = None
    original_network = None
    original_orientation = None
    actual = {
        "device": spec.udid,
        "request_budget_scope": "Explicit Appium operations; downstream protocol frames are not counted.",
    }
    if apk_sha256:
        actual["apk_sha256"] = apk_sha256
    else:
        actual["apk_identity"] = "Preinstalled package; binary fingerprint was not supplied"
    evidence = []
    status, reason = "passed", ""

    def call(function, *args, **kwargs):
        context.consume("requests")
        client.timeout = min(
            spec.timeout if driver is None else spec.wait_timeout + 5, context.remaining()
        )
        return function(*args, **kwargs)

    def locate(action):
        if action.accessibility_id:
            kind, value = AppiumBy.ACCESSIBILITY_ID, action.accessibility_id
        elif action.resource_id:
            kind, value = AppiumBy.ID, action.resource_id
        elif action.text:
            kind, value = (
                AppiumBy.ANDROID_UIAUTOMATOR,
                "new UiSelector().text(" + json.dumps(action.text) + ")",
            )
        else:
            raise ValueError("Native action requires a semantic locator")

        def found(_):
            elements = call(driver.find_elements, kind, value)
            if len(elements) > 1:
                raise Blocked("Configured native locator is ambiguous")
            return elements[0] if elements and call(elements[0].is_displayed) else False

        return WebDriverWait(
            driver, min(spec.wait_timeout, context.remaining()), poll_frequency=0.25
        ).until(found)

    try:
        context.consume("actions")
        driver = call(
            webdriver.Remote,
            spec.server_url,
            options=UiAutomator2Options().load_capabilities(capabilities),
            client_config=client,
        )
        actual["platform_version"] = driver.capabilities.get("platformVersion")
        for index, action in enumerate(spec.actions):
            context.consume("actions")
            actual["last_action"] = index
            value = context.redactor.binding(action.value_env) if action.value_env else action.value
            if action.action == "back":
                call(driver.back)
            elif action.action == "background":
                call(driver.background_app, 2)
            elif action.action == "restart":
                call(driver.terminate_app, spec.package)
                call(driver.activate_app, spec.package)
            elif action.action == "set_network":
                if action.enabled is None:
                    raise ValueError("Connectivity action requires enabled")
                if original_network is None:
                    original_network = call(driver.execute_script, "mobile: getConnectivity", {})
                    actual["initial_network"] = original_network
                call(
                    driver.execute_script,
                    "mobile: setConnectivity",
                    {
                        "wifi": action.enabled,
                        "data": action.enabled,
                        "airplaneMode": not action.enabled,
                    },
                )
                actual.setdefault("network_states", []).append(
                    call(driver.execute_script, "mobile: getConnectivity", {})
                )
            elif action.action == "rotate":
                if original_orientation is None:
                    original_orientation = call(lambda: driver.orientation)
                call(setattr, driver, "orientation", action.orientation)
                actual.setdefault("viewports", []).append(
                    {
                        "orientation": call(lambda: driver.orientation),
                        **call(driver.get_window_size),
                    }
                )
                assert actual["viewports"][-1]["orientation"] == action.orientation
            elif action.action == "expect_keyboard":
                WebDriverWait(
                    driver, min(spec.wait_timeout, context.remaining()), poll_frequency=0.25
                ).until(lambda _, enabled=action.enabled: call(driver.is_keyboard_shown) == enabled)
                observed = call(driver.is_keyboard_shown)
                actual.setdefault("keyboard_states", []).append(observed)
                assert observed == action.enabled
            elif action.action == "hide_keyboard":
                if call(driver.is_keyboard_shown):
                    call(driver.hide_keyboard)
            elif action.action == "scroll_to":
                selector = (
                    "new UiSelector().description(" + json.dumps(action.accessibility_id) + ")"
                    if action.accessibility_id
                    else (
                        "new UiSelector().text(" + json.dumps(action.text) + ")"
                        if action.text
                        else "new UiSelector().resourceId(" + json.dumps(action.resource_id) + ")"
                    )
                )
                WebDriverWait(
                    driver, min(spec.wait_timeout, context.remaining()), poll_frequency=0.25
                ).until(
                    lambda _, selector=selector: call(
                        driver.find_element,
                        AppiumBy.ANDROID_UIAUTOMATOR,
                        "new UiScrollable(new UiSelector().scrollable(true)).scrollIntoView("
                        + selector
                        + ")",
                    )
                )
            elif action.action == "screenshot":
                pass
            else:
                element = locate(action)
                if action.action == "click":
                    call(element.click)
                elif action.action == "fill":
                    if SENSITIVE.search(
                        action.accessibility_id or action.resource_id or action.text or ""
                    ):
                        context.redactor.add(value)
                    call(element.clear)
                    call(element.send_keys, value or "")
                elif action.action == "expect_text" and value is not None:
                    assertion = {
                        "locator": action.accessibility_id or action.resource_id or action.text,
                        "expected": value,
                        "observed": None,
                    }
                    actual.setdefault("assertions", []).append(assertion)

                    def matching(_, element=element, value=value, assertion=assertion):
                        assertion["observed"] = call(lambda: element.text)
                        return assertion["observed"] == value

                    WebDriverWait(
                        driver, min(spec.wait_timeout, context.remaining()), poll_frequency=0.25
                    ).until(matching)
                elif action.action == "expect_not_occluded":
                    if not call(driver.is_keyboard_shown):
                        raise Blocked("Keyboard is not open; occlusion was not evaluated")
                    content = call(driver.find_element, AppiumBy.ID, "android:id/content")
                    bounds, content_bounds = (
                        call(lambda element=element: element.rect),
                        call(lambda content=content: content.rect),
                    )
                    actual.setdefault("keyboard_occlusion", []).append(
                        {"element": bounds, "content": content_bounds}
                    )
                    assert bounds["y"] >= content_bounds["y"]
                    assert (
                        bounds["y"] + bounds["height"]
                        <= content_bounds["y"] + content_bounds["height"]
                    )
                    assert bounds["x"] >= content_bounds["x"]
                    assert (
                        bounds["x"] + bounds["width"]
                        <= content_bounds["x"] + content_bounds["width"]
                    )
        actual["package"] = call(lambda: driver.current_package)
        actual["viewport"] = call(driver.get_window_size)
    except Blocked as exc:
        status, reason = "blocked", context.redactor.text(str(exc))
    except (AssertionError, TimeoutException, NoSuchElementException) as exc:
        status, reason = "failed", f"Native UI oracle was not satisfied ({type(exc).__name__})"
        if driver is not None:
            try:
                alerts = call(driver.find_elements, AppiumBy.ID, "android:id/alertTitle")
                if any(
                    call(lambda alert=alert: alert.text) == "System UI has stopped"
                    for alert in alerts
                ):
                    status, reason = "error", "Android System UI crashed during the scenario"
            except (WebDriverException, ReadTimeoutError, ConnectTimeoutError, Blocked):
                actual["infrastructure_diagnostic_unavailable"] = True
    except (ReadTimeoutError, ConnectTimeoutError):
        status, reason = "blocked", "Appium transport exceeded its bounded timeout"
    except WebDriverException as exc:
        actual["runner_error"] = context.redactor.text(str(exc))[:2500]
        status, reason = (
            "blocked" if driver is None else "error",
            f"Native runner operation did not complete ({type(exc).__name__})",
        )
    finally:
        if driver is not None:
            client.timeout = 5
            image = f"{check.id}.png"
            try:
                if any(
                    a.value_env
                    or (
                        a.action == "fill"
                        and SENSITIVE.search(a.accessibility_id or a.resource_id or a.text or "")
                    )
                    for a in spec.actions
                ):
                    raise Blocked("Screenshot withheld because secret-bound actions were used")
                driver.save_screenshot(str(safe_file(context.folder, image)))
                os.chmod(safe_file(context.folder, image), 0o600)
                evidence.append(image)
            except (WebDriverException, ReadTimeoutError, ConnectTimeoutError, OSError, Blocked):
                actual["screenshot_unavailable"] = True

            def restore_network():
                driver.execute_script("mobile: setConnectivity", original_network)
                restored = driver.execute_script("mobile: getConnectivity", {})
                actual["restored_network"] = restored
                if restored != original_network:
                    raise WebDriverException("Connectivity restoration did not match")

            def restore_orientation():
                driver.orientation = original_orientation
                actual["restored_orientation"] = driver.orientation
                if actual["restored_orientation"] != original_orientation:
                    raise WebDriverException("Orientation restoration did not match")

            restorations = []
            if original_network is not None:
                restorations.append(("network", restore_network))
            if original_orientation is not None:
                restorations.append(("orientation", restore_orientation))
            for scope, restore in restorations:
                try:
                    client.timeout = 10
                    restore()
                except (WebDriverException, ReadTimeoutError, ConnectTimeoutError, OSError):
                    actual[scope + "_cleanup_error"] = True
                    status, reason = (
                        "error",
                        "Device controls could not be restored; inspect the isolated runner",
                    )
            client.timeout = 5
            try:
                driver.quit()
            except (WebDriverException, ReadTimeoutError, ConnectTimeoutError, OSError, Blocked):
                actual["session_cleanup_error"] = True
    artifact = f"{check.id}.android.json"
    write_json(context.folder, artifact, actual, context.redactor)
    evidence.append(artifact)
    return context.result(check, status, actual=actual, reason=reason, evidence=evidence)
