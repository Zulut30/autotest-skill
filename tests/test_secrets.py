import json
import pytest
from autotest_skill.secrets import Redactor
from autotest_skill.errors import Blocked


def test_secret_is_removed_before_serialization(monkeypatch):
    secret = "test-only-credential-9573"
    monkeypatch.setenv("AUTOTEST_TEST_TOKEN", secret)
    redact = Redactor()
    data = {"nested": {"password": "other-value"}, "message": f"request used {secret}",
            "header": "Bearer synthetic-token"}
    encoded = json.dumps(redact.clean(data))
    assert secret not in encoded
    assert "other-value" not in encoded
    assert "synthetic-token" not in encoded
    assert "[REDACTED]" in encoded


def test_missing_binding_is_blocked_not_empty(monkeypatch):
    monkeypatch.delenv("AUTOTEST_ABSENT_TOKEN", raising=False)
    with pytest.raises(Blocked):
        Redactor().binding("AUTOTEST_ABSENT_TOKEN")
