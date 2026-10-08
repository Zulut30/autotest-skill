import importlib.util
from pathlib import Path

import pytest

from autotest_skill.artifacts import write_json
from autotest_skill.config import Config
from autotest_skill.context import Context
from autotest_skill.errors import Blocked


def test_extension_example_rejects_stale_and_zero_evidence(tmp_path):
    path = Path(__file__).parents[1] / "examples/adapters/status_file.py"
    spec = importlib.util.spec_from_file_location("reviewed_status_example", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    config = Config.model_validate(
        {
            "project": "example",
            "allowed_origins": ["http://localhost:8000"],
            "checks": [
                {
                    "id": "producer",
                    "kind": "http",
                    "requirement": "EXTENSION",
                    "oracle": "Current producer has evaluated passing checks",
                    "spec": {"base_url": "http://localhost:8000"},
                }
            ],
        }
    )
    context = Context(config, tmp_path, tmp_path)
    check = config.checks[0]
    check.spec = module.StatusSpec(artifact="producer.json")
    for run_id, count in [("old-run", 5), (tmp_path.name, 0)]:
        write_json(
            tmp_path,
            "producer.json",
            {"run_id": run_id, "checks_executed": count, "status": "passed"},
            context.redactor,
        )
        with pytest.raises(Blocked):
            module.run(check, context)
    for status in ["passed", "failed", "error"]:
        write_json(
            tmp_path,
            "producer.json",
            {"run_id": tmp_path.name, "checks_executed": 5, "status": status},
            context.redactor,
        )
        assert module.run(check, context).status == status
