"""Per-run state is isolated from persisted configuration."""

import time
from dataclasses import dataclass, field
from pathlib import Path

from .errors import BudgetExceeded
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

    counters: dict = field(default_factory=lambda: {"checks": 0, "actions": 0, "requests": 0})

    def remaining(self):
        remaining = self.config.budgets.seconds - (time.monotonic() - self.started)
        if remaining <= 0:
            raise BudgetExceeded("Run time budget exhausted")
        return remaining

    def consume(self, resource, amount=1):
        self.remaining()
        maximum = getattr(self.config.budgets, "max_" + resource)
        if self.counters[resource] + amount > maximum:
            raise BudgetExceeded(f"Run {resource} budget exhausted")
        self.counters[resource] += amount

    def result(self, check, status, **details):
        return CheckResult(
            id=check.id,
            kind=check.kind,
            status=status,
            oracle=check.oracle,
            requirement=check.requirement,
            severity=check.severity,
            impact=check.impact,
            **details,
        )
