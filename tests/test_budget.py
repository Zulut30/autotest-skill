import time

import pytest

from autotest_skill.config import Config
from autotest_skill.context import Context
from autotest_skill.errors import BudgetExceeded


def test_deadline_and_action_limits_are_enforced(tmp_path):
    config = Config.model_validate(
        {
            "project": "x",
            "allowed_origins": ["http://localhost"],
            "budgets": {"max_actions": 1},
            "checks": [
                {
                    "id": "health",
                    "kind": "http",
                    "requirement": "health",
                    "oracle": "Service reports its ready state",
                    "spec": {"base_url": "http://localhost"},
                }
            ],
        }
    )
    context = Context(config, tmp_path, tmp_path)
    context.consume("actions")
    with pytest.raises(BudgetExceeded):
        context.consume("actions")
    context.started = time.monotonic() - config.budgets.seconds - 1
    with pytest.raises(BudgetExceeded):
        context.remaining()
