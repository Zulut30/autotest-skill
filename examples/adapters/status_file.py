"""Example trusted adapter consuming a producer's current-run status artifact."""

from typing import Literal

from pydantic import Field

from autotest_skill.artifacts import safe_file
from autotest_skill.config import StrictModel
from autotest_skill.errors import Blocked


class StatusSpec(StrictModel):
    artifact: str


class ProducerResult(StrictModel):
    run_id: str
    checks_executed: int = Field(ge=0)
    status: Literal["passed", "failed", "error"]


def run(check, context):
    context.remaining()
    path = safe_file(context.folder, check.spec.artifact)
    if not path.is_file() or path.stat().st_size > 100_000:
        raise Blocked("Current producer artifact missing or oversized")
    data = ProducerResult.model_validate_json(path.read_text())
    if data.run_id != context.folder.name:
        raise Blocked("Producer artifact belongs to another run")
    if data.checks_executed == 0:
        raise Blocked("Producer evaluated no checks")
    return context.result(
        check,
        data.status,
        actual=data.model_dump(),
        evidence=[check.spec.artifact],
        reason="" if data.status == "passed" else "Producer did not satisfy the declared oracle",
    )
