"""HTTP assertions, ephemeral captures and safe current-run evidence."""

import httpx
from ..artifacts import write_json
from ..errors import Blocked
from ..policy import request_url


def subset(expected, actual):
    if isinstance(expected, dict):
        return isinstance(actual, dict) and all(key in actual and subset(value, actual[key]) for key, value in expected.items())
    if isinstance(expected, list):
        return isinstance(actual, list) and len(expected) == len(actual) and all(subset(a, b) for a, b in zip(expected, actual))
    return type(expected) is type(actual) and expected == actual


def extract(value, path):
    for part in path.split("."):
        value = value[int(part)] if isinstance(value, list) else value[part]
    return value


def run(check, context):
    spec = check.spec
    url = request_url(context.config, spec.base_url, spec.path)
    headers = dict(spec.headers)
    headers.update({key: context.redactor.binding(name) for key, name in spec.headers_env.items()})
    for key, name in spec.headers_from.items():
        if name not in context.variables:
            raise Blocked(f"Required prior capture {name} is unavailable")
        headers[key] = str(context.variables[name])
    body = dict(spec.json_body or {}) if spec.json_body is not None or spec.json_env else None
    for key, name in spec.json_env.items():
        body[key] = context.redactor.binding(name)
    context.consume("requests")
    try:
        with httpx.Client(timeout=min(spec.timeout, context.remaining()), follow_redirects=False) as client:
            with client.stream(spec.method, url, json=body, headers=headers) as response:
                chunks, size = [], 0
                for chunk in response.iter_bytes():
                    context.remaining()
                    size += len(chunk)
                    if size > 1_000_000:
                        raise Blocked("HTTP response exceeds the evidence size limit")
                    chunks.append(chunk)
                content = b"".join(chunks)
                import json
                try:
                    payload = json.loads(content)
                except (ValueError, UnicodeDecodeError):
                    payload = None
                text = content.decode(errors="replace")
                status_code = response.status_code
                observed_headers = dict(response.headers)
    except (httpx.ConnectError, httpx.TimeoutException) as exc:
        raise Blocked(f"Target unavailable: {type(exc).__name__}") from exc
    matches = status_code == spec.expected_status and all(observed_headers.get(key.lower()) == value for key,value in spec.expected_headers.items())
    if spec.expected_json is not None:
        matches = matches and subset(spec.expected_json, payload)
    if spec.expected_text is not None:
        matches = matches and spec.expected_text in text
    contract_errors = []
    if spec.openapi_file:
        from ..contracts import response_errors
        contract_errors = response_errors(context.root, spec.openapi_file, spec.path, spec.method, status_code, payload)
        matches = matches and not contract_errors
    if matches:
        for name, path in spec.capture.items():
            try:
                value = extract(payload, path)
            except (KeyError, IndexError, TypeError, ValueError):
                matches = False
                break
            context.variables[name] = value
            context.redactor.add(value)
    actual = {"status": status_code, "json": payload} if payload is not None else {"status": status_code, "text": text[:20000]}
    actual["headers"] = {key:observed_headers.get(key.lower()) for key in spec.expected_headers}
    expected = {"headers":spec.expected_headers,"status": spec.expected_status, "json": spec.expected_json, "text": spec.expected_text}
    artifact = f"{check.id}.http.json"
    write_json(context.folder, artifact, {"url": url, "method": spec.method, "expected": expected,
               "actual": actual, "contract_errors": contract_errors}, context.redactor)
    return context.result(check, "passed" if matches else "failed", expected=expected, actual=actual,
                          reason="" if matches else "HTTP response does not satisfy the declared oracle", evidence=[artifact])
