"""Inspect project metadata without reading credential files or executing project code."""

import json
import shutil
import subprocess
import tomllib
from pathlib import Path

MANIFESTS = {"pyproject.toml", "package.json", "go.mod", "Cargo.toml", "pom.xml", "build.gradle", "requirements.txt", "Dockerfile"}
EXCLUDE = {".git", ".venv", "node_modules", "vendor", ".autotest", "__pycache__", "dist", "build"}


def discover(path):
    root = Path(path).resolve()
    if not root.is_dir():
        raise ValueError("Discovery requires a directory")
    warnings = []
    if shutil.which("rg"):
        command = ["rg", "--files", "--hidden", "-g", "!.env*", "-g", "!*.session*"]
        for name in EXCLUDE:
            command.extend(["-g", f"!{name}"])
        proc = subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=20)
        if proc.returncode not in (0, 1):
            raise ValueError("Project traversal failed")
        files = proc.stdout.splitlines()
    else:
        warnings.append("ripgrep unavailable; using a bounded filesystem walk")
        import os
        files = []
        for current, dirs, names in os.walk(root, onerror=lambda error: warnings.append(type(error).__name__)):
            dirs[:] = [name for name in dirs if name not in EXCLUDE]
            for name in names:
                if name.startswith(".env") or ".session" in name:
                    continue
                files.append(str((Path(current) / name).relative_to(root)))
                if len(files) > 10000:
                    raise ValueError("Discovery limit exceeded")
    if len(files) > 10000:
        raise ValueError("Discovery limit exceeded")
    manifests = sorted(name for name in files if Path(name).name in MANIFESTS)
    tests = sorted(name for name in files if Path(name).name.startswith("test_") or ".spec." in name or ".test." in name)
    instructions = sorted(name for name in files if Path(name).name in {"AGENTS.md", "README.md"} or name.startswith(".github/workflows/"))
    commands = []
    if (root / "pyproject.toml").is_file():
        data = tomllib.loads((root / "pyproject.toml").read_text())
        if "pytest" in str(data.get("dependency-groups", {})) or tests:
            commands.append({"argv": ["python", "-m", "pytest"], "source": "Python metadata/tests", "inferred": True})
    if (root / "package.json").is_file():
        data = json.loads((root / "package.json").read_text())
        for name in ("test", "build", "typecheck", "lint"):
            if name in data.get("scripts", {}):
                commands.append({"argv": ["npm", "run", name], "source": "package.json", "inferred": False})
    if "go.mod" in manifests:
        commands.append({"argv": ["go", "test", "./..."], "source": "go.mod", "inferred": True})
    revision = None
    result = subprocess.run(["git", "rev-parse", "--verify", "HEAD^{commit}"], cwd=root, capture_output=True, text=True)
    if result.returncode == 0:
        revision = result.stdout.strip()
    return {"root": str(root), "revision": revision, "manifests": manifests, "test_files": tests,
            "instruction_files": instructions, "candidate_commands": commands, "warnings": warnings,
            "note": "Candidates were discovered, not executed. Read project instructions before using them."}


def execute(args):
    from .secrets import Redactor
    print(json.dumps(Redactor().clean(discover(args.path)), indent=2))
    return 0
