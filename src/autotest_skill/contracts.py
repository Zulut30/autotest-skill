"""Local OpenAPI response validation with no remote reference resolution."""

import copy
import json
import re
from pathlib import Path

from jsonschema import Draft202012Validator

from .errors import Blocked


def local_file(root, name):
    base = Path(root).resolve()
    path = (base / name).resolve()
    if base not in path.parents or not path.is_file() or path.stat().st_size > 1_000_000:
        raise Blocked("Contract file is unavailable or outside the project")
    return path


def normalize(value):
    if isinstance(value, list):
        return [normalize(item) for item in value]
    if not isinstance(value, dict):
        return value
    if "$ref" in value and not value["$ref"].startswith("#/"):
        raise Blocked("Remote contract references are not supported")
    result = {key: normalize(item) for key, item in value.items() if key != "nullable"}
    if value.get("nullable") and isinstance(result.get("type"), str):
        result["type"] = [result["type"], "null"]
    return result


def response_errors(root, name, path, method, status, payload):
    document = normalize(json.loads(local_file(root, name).read_text()))
    if not str(document.get("openapi", "")).startswith(("3.0.", "3.1.")):
        raise Blocked("Supported contracts use OpenAPI 3.0 or 3.1")
    request_path = path.split("?", 1)[0]
    matching = [
        key
        for key in document.get("paths", {})
        if re.fullmatch(
            re.sub(r"\{[^/{}]+\}", "[^/]+", re.escape(key).replace(r"\{", "{").replace(r"\}", "}")),
            request_path,
        )
    ]
    if not matching:
        raise Blocked("No contract operation matches the check")
    operation = document["paths"][matching[0]].get(method.lower())
    if operation is None:
        raise Blocked("No contract operation matches the HTTP method")
    responses = operation.get("responses", {})
    response = responses.get(str(status), responses.get("default"))
    if response is None:
        return ["Response status is not declared in the contract"]
    schema = response.get("content", {}).get("application/json", {}).get("schema")
    if schema is None:
        raise Blocked("The operation has no JSON response schema")
    schema = copy.deepcopy(schema)
    schema["components"] = document.get("components", {})
    return [
        ".".join(map(str, error.path)) + ": " + error.validator
        for error in Draft202012Validator(schema).iter_errors(payload)
    ]
