"""Select bounded checks and include their prerequisite closure."""

import json
import fnmatch
from pathlib import PurePosixPath
from .config import load_config
from .secrets import Redactor


def select(config, profile="smoke", changed_files=()):
    selected = [check for check in config.checks if profile in check.profiles]
    if profile == "changed":
        paths = []
        for value in changed_files:
            path = PurePosixPath(value.replace("\\", "/"))
            if path.is_absolute() or ".." in path.parts:
                raise ValueError("Changed paths must be project-relative")
            paths.append(str(path))
        impacted = [check for check in selected if any(fnmatch.fnmatch(path, pattern)
                    for path in paths for pattern in check.covers)]
        selected = impacted or [check for check in config.checks if "smoke" in check.profiles]
    by_id = {check.id: check for check in config.checks}
    ordered, visited = [], set()
    def include(check):
        if check.id in visited:
            return
        for identifier in check.depends_on:
            include(by_id[identifier])
        visited.add(check.id)
        ordered.append(check)
    for check in selected:
        include(check)
    return ordered


def plan(config, profile="smoke", changed_files=()):
    checks = select(config, profile, changed_files)
    return {"project": config.project, "profile": profile, "execution_order": [c.id for c in checks],
            "checks": [{"id": c.id, "kind": c.kind, "oracle": c.oracle, "requirement": c.requirement,
                        "mutating": c.mutating, "depends_on": c.depends_on} for c in checks],
            "budget": config.budgets.model_dump(), "note": "Planning does not execute checks."}


def execute(args):
    config, _ = load_config(args.config)
    print(json.dumps(Redactor().clean(plan(config, args.profile, args.changed_file)), indent=2))
    return 0
