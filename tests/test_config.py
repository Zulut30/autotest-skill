import copy
import pytest
from pydantic import ValidationError
from autotest_skill.config import Config

BASE = {"project": "test", "allowed_origins": ["http://127.0.0.1:8765"], "checks": [{
    "id": "health", "kind": "http", "requirement": "readiness", "oracle": "Service returns its ready state",
    "spec": {"base_url": "http://127.0.0.1:8765", "path": "/health"}}]}


def test_unknown_options_and_targets_are_rejected():
    for mutate in (lambda c: c.update(unknown=True),
                   lambda c: c["checks"][0]["spec"].update(base_url="https://other.example"),
                   lambda c: c["checks"][0]["spec"].update(path="//other.example")):
        config = copy.deepcopy(BASE)
        mutate(config)
        with pytest.raises(ValidationError):
            Config.model_validate(config)


def test_mutation_requires_both_declarations():
    config = copy.deepcopy(BASE)
    config["checks"][0]["spec"]["method"] = "POST"
    with pytest.raises(ValidationError):
        Config.model_validate(config)
    config["checks"][0]["mutating"] = True
    with pytest.raises(ValidationError):
        Config.model_validate(config)
    config["allow_mutations"] = True
    assert Config.model_validate(config).checks[0].mutating


def test_duplicate_ids_and_dependency_cycles_are_rejected():
    config = copy.deepcopy(BASE)
    config["checks"].append(copy.deepcopy(config["checks"][0]))
    with pytest.raises(ValidationError):
        Config.model_validate(config)
    config["checks"][1]["id"] = "other"
    config["checks"][0]["depends_on"] = ["other"]
    config["checks"][1]["depends_on"] = ["health"]
    with pytest.raises(ValidationError):
        Config.model_validate(config)
