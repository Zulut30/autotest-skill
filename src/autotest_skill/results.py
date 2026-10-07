"""Versioned results and conservative completion semantics."""

from collections import Counter
from typing import Any, Literal
from pydantic import Field
from .config import StrictModel

Status = Literal["passed", "failed", "blocked", "skipped", "error", "observation"]


class CheckResult(StrictModel):
    id: str
    kind: str
    status: Status
    oracle: str
    requirement: str
    severity: str = "medium"
    elapsed_ms: float = 0
    expected: Any = None
    actual: Any = None
    reason: str = ""
    evidence: list[str] = Field(default_factory=list)
    attempts: list[dict[str, Any]] = Field(default_factory=list)
    flaky: bool = False
    test_counts: dict[str, int] = Field(default_factory=dict)


class RunReport(StrictModel):
    schema_version: Literal[1] = 1
    run_id: str
    project: str
    profile: str
    tool_version: str
    started_at: str
    finished_at: str | None = None
    target_revision: str | None = None
    config_digest: str
    results: list[CheckResult] = Field(default_factory=list)
    interrupted: bool = False

    def counts(self):
        return dict(Counter(result.status for result in self.results))

    def exit_code(self):
        counts = self.counts()
        if self.interrupted:
            return 130
        if counts.get("error"):
            return 3
        if counts.get("failed") or any(result.flaky for result in self.results):
            return 1
        if counts.get("blocked") or not counts.get("passed"):
            return 2
        return 0
