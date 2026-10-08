"""Locate installed executables without downloading or executing project content."""

import os
import shutil
import sys
from pathlib import Path

from .errors import Blocked


def binary(name):
    configured = os.environ.get("AUTOTEST_" + name.upper() + "_BINARY")
    candidate = configured or shutil.which(name)
    sibling = Path(sys.executable).parent / name
    if not candidate and sibling.is_file():
        candidate = str(sibling)
    roots = [Path.cwd() / ".autotest/tools", Path("/workspace/.autotest-tools")]
    if os.environ.get("AUTOTEST_TOOLS_DIR"):
        roots.insert(0, Path(os.environ["AUTOTEST_TOOLS_DIR"]))
    candidates = []
    if name == "adb" and os.environ.get("ANDROID_HOME"):
        candidates.append(Path(os.environ["ANDROID_HOME"]) / "platform-tools/adb")
    for root in roots:
        candidates.append(root / "bin" / name)
        if name == "semgrep":
            candidates.append(root / "semgrep-venv/bin/semgrep")
        elif name == "adb":
            candidates.append(root / "android/platform-tools/adb")
        elif name == "appium":
            candidates.append(root / "appium/node_modules/.bin/appium")
    if not candidate:
        candidate = next((str(path) for path in candidates if path.is_file()), None)
    if not candidate or not Path(candidate).is_file() or not os.access(candidate, os.X_OK):
        raise Blocked(f"{name} is unavailable; install it or set AUTOTEST_{name.upper()}_BINARY")
    return str(Path(candidate).resolve())
