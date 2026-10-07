"""Bounded functional readiness, not a PID or open-port check."""

import time
import httpx
from .errors import Blocked
from .adapters.http import subset


def wait_http(base_url, expected_json=None, expected_text=None, timeout=10):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            response = httpx.get(base_url + '/health', timeout=min(1, deadline-time.monotonic()))
            ready = response.status_code == 200
            if expected_json is not None:
                ready = ready and subset(expected_json, response.json())
            if expected_text is not None:
                page = httpx.get(base_url + '/', timeout=min(1, max(.001,deadline-time.monotonic())))
                ready = ready and page.status_code == 200 and expected_text in page.text
            if ready:
                return {'status':'passed','health_status':response.status_code}
        except (httpx.HTTPError, ValueError):
            pass
        time.sleep(min(.05,max(0,deadline-time.monotonic())))
    raise Blocked('Service did not satisfy the functional readiness oracle before the deadline')
