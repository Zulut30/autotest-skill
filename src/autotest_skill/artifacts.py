"""Private, atomic artifacts scoped to one unique run."""

import json
import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path


def create_run(output):
    base = Path(output).resolve()
    base.mkdir(parents=True, exist_ok=True)
    identifier = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:12]
    folder = base / identifier
    folder.mkdir(mode=0o700)
    return identifier, folder


def safe_file(folder, name):
    root = Path(folder).resolve()
    target = (root / name).resolve()
    if target == root or root not in target.parents:
        raise ValueError("Artifact path escapes the run directory")
    return target


def write_json(folder, name, data, redactor):
    target = safe_file(folder, name)
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(prefix=".artifact-", dir=target.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(redactor.clean(data), stream, indent=2, ensure_ascii=False)
            stream.write("\n")
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return target
