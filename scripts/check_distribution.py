#!/usr/bin/env python3
"""Inspect built archives without extracting them or importing the source checkout."""

import hashlib
import json
import sys
import tarfile
import tomllib
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]


def inspect(directory):
    version = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    wheel = directory / f"autotest_agent_skill-{version}-py3-none-any.whl"
    source = directory / f"autotest_agent_skill-{version}.tar.gz"
    with zipfile.ZipFile(wheel) as archive:
        wheel_names = set(archive.namelist())
        metadata = archive.read(f"autotest_agent_skill-{version}.dist-info/METADATA").decode()
    with tarfile.open(source) as archive:
        members = archive.getmembers()
        assert all(not m.issym() and not m.islnk() for m in members), "Unexpected archive links"
        source_names = {
            str(PurePosixPath(m.name).relative_to(f"autotest_agent_skill-{version}"))
            for m in members
        }
    required = {
        "autotest_skill/cli.py",
        "autotest_skill/regression.py",
        "autotest_skill/assets/benchmark/catalog.json",
        "autotest_skill/assets/axe.min.js",
        "autotest_skill/assets/AXE-LICENSE.txt",
        "autotest_skill/skill/SKILL.md",
        "autotest_skill/skill/references/android.md",
        "autotest_skill/skill/references/telegram.md",
        "autotest_skill/skill/schemas/result.schema.json",
        "autotest_skill/skill/examples/api.yaml",
        "autotest_skill/skill/docs/QUICKSTART.md",
        "autotest_skill/skill/docs/evidence/auth-guidance-regression.json",
        f"autotest_agent_skill-{version}.dist-info/licenses/LICENSE",
    }
    assert required <= wheel_names, "Required wheel resources missing: " + str(
        required - wheel_names
    )
    assert {
        "SKILL.md",
        "LICENSE",
        "uv.lock",
        "scripts/install.sh",
        "fixtures/android/AndroidManifest.xml",
    } <= source_names
    assert f"Version: {version}" in metadata and "License-Expression: MIT" in metadata
    for name in wheel_names | source_names:
        parts = PurePosixPath(name).parts
        assert not name.startswith("/") and ".." not in parts, "Unsafe archive path"
        assert not any(
            p in {".venv", ".autotest", ".git", "__pycache__", ".pytest_cache"} for p in parts
        ), "Local data included"
        assert not any(
            p.startswith(".env") or p.endswith((".session", ".keystore")) for p in parts
        ), "Credential file included"
    return {
        "version": version,
        "status": "alpha",
        "license": "MIT",
        "archive_checks": "passed",
        "artifacts": [
            {
                "file": p.name,
                "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                "bytes": p.stat().st_size,
            }
            for p in (wheel, source)
        ],
        "excluded": ["Local caches", "Credentials", "Android signing key", "Private runs"],
    }


if __name__ == "__main__":
    print(json.dumps(inspect(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "dist"), indent=2))
