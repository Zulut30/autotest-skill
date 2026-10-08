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
    if not candidate and name == "semgrep":
        semgrep = Path("/workspace/.autotest-tools/semgrep-venv/bin/semgrep")
        if semgrep.is_file():
            candidate = str(semgrep)
    if not candidate:
        local = Path("/workspace/.autotest-tools/bin") / name
        if local.is_file():
            candidate = str(local)
    if not candidate or not Path(candidate).is_file() or not os.access(candidate, os.X_OK):
        raise Blocked(f"{name} is unavailable; install it or set AUTOTEST_{name.upper()}_BINARY")
    return str(Path(candidate).resolve())
