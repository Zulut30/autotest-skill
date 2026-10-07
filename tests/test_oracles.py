import pytest
from pydantic import ValidationError
from autotest_skill.config import Config


def test_checks_cannot_omit_requirement_or_oracle():
    base = {"project": "x", "allowed_origins": ["http://localhost"], "checks": [{
        "id": "health", "kind": "http", "spec": {"base_url": "http://localhost"}}]}
    with pytest.raises(ValidationError):
        Config.model_validate(base)
