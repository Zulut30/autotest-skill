"""Capability discovery without leaking environment values."""

import importlib.util
import os
import shutil
import sys
from pathlib import Path


def browser_path():
    configured = os.environ.get("AUTOTEST_BROWSER_PATH")
    if configured:
        return configured if Path(configured).is_file() else None
    return shutil.which("chromium") or shutil.which("google-chrome")


def diagnose(probe_browser=False):
    packages = {
        name: importlib.util.find_spec(name) is not None
        for name in ("httpx", "pydantic", "yaml", "playwright", "aiogram", "telethon", "appium")
    }
    tools = {
        name: shutil.which(name) is not None
        for name in ("uv", "k6", "semgrep", "gitleaks", "adb", "appium")
    }
    result = {
        "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "core_ready": all(packages[name] for name in ("httpx", "pydantic", "yaml")),
        "packages_installed": packages,
        "tools_installed": tools,
        "system_browser_installed": browser_path() is not None,
        "telegram_bindings_present": {
            name: bool(os.environ.get(name))
            for name in ("TG_BOT_TOKEN", "TG_API_ID", "TG_API_HASH", "TG_SESSION")
        },
        "note": "Installed tools are not proof that a target workflow has been validated.",
    }
    if probe_browser:
        if not packages["playwright"]:
            result["browser_probe"] = {"status": "blocked", "reason": "Install the web extra."}
        else:
            try:
                from playwright.sync_api import sync_playwright

                with sync_playwright() as pw:
                    browser = pw.chromium.launch(executable_path=browser_path(), headless=True)
                    page = browser.new_page()
                    page.set_content("<button>Readiness probe</button>")
                    page.get_by_role("button", name="Readiness probe").click()
                    result["browser_probe"] = {"status": "passed", "version": browser.version}
                    browser.close()
            except Exception as exc:  # noqa: BLE001 - Readiness boundary reports optional tool exception types without secret text.
                result["browser_probe"] = {"status": "blocked", "reason": type(exc).__name__}
    return result
