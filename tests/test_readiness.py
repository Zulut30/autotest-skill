import pytest

from autotest_skill.demo import start_demo
from autotest_skill.errors import Blocked
from autotest_skill.readiness import wait_http


def test_readiness_checks_health_body_and_application_content():
    with start_demo() as (base, _):
        assert wait_http(base, {"ready": True}, "Autotest demo")["status"] == "passed"
        with pytest.raises(Blocked):
            wait_http(base, {"ready": False}, timeout=0.15)
