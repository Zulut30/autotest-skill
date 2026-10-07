"""Locate installed executables without downloading or executing project content."""

import os
import shutil
from pathlib import Path
from .errors import Blocked


def binary(name):
    configured = os.environ.get('AUTOTEST_' + name.upper() + '_BINARY')
    candidate = configured or shutil.which(name)
    if not candidate:
        local = Path('/workspace/.autotest-tools/bin') / name
        if local.is_file():
            candidate = str(local)
    if not candidate or not Path(candidate).is_file() or not os.access(candidate, os.X_OK):
        raise Blocked(f'{name} is unavailable; install it or set AUTOTEST_{name.upper()}_BINARY')
    return str(Path(candidate).resolve())
