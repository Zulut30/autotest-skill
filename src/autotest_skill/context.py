"""Per-run state is isolated from persisted configuration."""

import time
from dataclasses import dataclass, field
from pathlib import Path
from .results import CheckResult
from .secrets import Redactor


@dataclass
class Context:
    config: object
    root: Path
    folder: Path
    redactor: Redactor = field(default_factory=Redactor)
    variables: dict = field(default_factory=dict)
    started: float = field(default_factory=time.monotonic)

    def remaining(self):
        return max(0.001, self.config.budgets.seconds - (time.monotonic() - self.started))

    def result(self, check, status, **details):
        return CheckResult(id=check.id, kind=check.kind, status=status, oracle=check.oracle,
                           requirement=check.requirement, severity=check.severity, **details)
