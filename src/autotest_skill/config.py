"""Strict, secret-free execution configuration."""

import json
import ipaddress
import re
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlsplit,parse_qsl
import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


def origin(value: str) -> str:
    if any(ord(c)<32 or ord(c)==127 for c in value):
        raise ValueError("URL controls are forbidden")
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Only HTTP(S) origins are supported")
    if parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in {"", "/"}:
        raise ValueError("An origin cannot contain credentials, paths, queries or fragments")
    host = parsed.hostname.lower().encode("idna").decode("ascii")
    if host in {"metadata.google.internal","metadata.aws.internal","100.100.100.200","168.63.129.16","fd00:ec2::254"}:
        raise ValueError("Cloud metadata targets are forbidden")
    try:
        address=ipaddress.ip_address(host)
        if address.is_link_local or (getattr(address,"ipv4_mapped",None) and address.ipv4_mapped.is_link_local):
            raise ValueError("Link-local metadata targets are forbidden")
    except ValueError as exc:
        if 'forbidden' in str(exc):raise
        if not re.fullmatch(r"[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?",host) or '..' in host or re.fullmatch(r"[0-9.]+",host):
            raise ValueError("Invalid or ambiguous host")
    if ":" in host:
        host = f"[{host}]"
    port = parsed.port
    suffix = f":{port}" if port and port != (443 if parsed.scheme == "https" else 80) else ""
    return f"{parsed.scheme}://{host}{suffix}"


class Budgets(StrictModel):
    seconds: float = Field(default=120, gt=0, le=3600)
    max_checks: int = Field(default=100, ge=1, le=1000)
    max_actions: int = Field(default=200, ge=1, le=5000)
    max_requests: int = Field(default=500, ge=1, le=10000)
    retries: int = Field(default=1, ge=0, le=3)


class HttpSpec(StrictModel):
    base_url: str
    path: str = "/"
    method: Literal["GET", "HEAD", "OPTIONS", "POST", "PUT", "PATCH", "DELETE"] = "GET"
    expected_status: int = Field(default=200, ge=100, le=599)
    expected_json: dict[str, Any] | None = None
    expected_text: str | None = None
    expected_headers: dict[str,str] = Field(default_factory=dict)
    headers: dict[str, str] = Field(default_factory=dict)
    headers_env: dict[str, str] = Field(default_factory=dict)
    headers_from: dict[str, str] = Field(default_factory=dict)
    json_body: dict[str, Any] | None = None
    json_env: dict[str, str] = Field(default_factory=dict)
    capture: dict[str, str] = Field(default_factory=dict)
    openapi_file: str | None = None
    timeout: float = Field(default=10, gt=0, le=120)


class CommandSpec(StrictModel):
    argv: list[str] = Field(min_length=1)
    timeout: float = Field(default=60, gt=0, le=3600)
    expected_exit: int = 0
    expected_stdout: str | None = None
    runner: Literal["generic", "pytest", "junit"] = "generic"
    result_file: str | None = None


class WebAction(StrictModel):
    action: Literal["goto", "click", "double_click", "fill", "press", "expect_text", "expect_visible", "expect_url", "reload", "screenshot"]
    role: str | None = None
    name: str | None = None
    label: str | None = None
    test_id: str | None = None
    text: str | None = None
    value: str | None = None
    value_env: str | None = None
    path: str | None = None
    safe_read_only: bool = False


    @model_validator(mode="after")
    def locator_contract(self):
        if self.action in {"click", "double_click", "fill", "press", "expect_text", "expect_visible"}:
            if sum(bool(value) for value in (self.role,self.label,self.test_id,self.text)) != 1:
                raise ValueError("An action needs exactly one semantic locator")
        if self.value is not None and self.value_env is not None:
            raise ValueError("Use one value source")
        return self


class WebSpec(StrictModel):
    base_url: str
    path: str = "/"
    actions: list[WebAction] = Field(default_factory=list)
    expected_text: list[str] = Field(default_factory=list)
    viewport: list[int] = Field(default_factory=lambda: [1280, 800], min_length=2, max_length=2)
    timeout: float = Field(default=15, gt=0, le=120)
    check_console: bool = True
    measure_performance: bool = False
    max_navigation_ms: float | None = Field(default=None,gt=0)
    max_action_ms: float | None = Field(default=None,gt=0)
    allowed_http_errors: dict[str, list[int]] = Field(default_factory=dict)
    accessibility: bool = False
    check_layout: bool = False
    explore: bool = False
    ux: bool = False
    baseline: str | None = None
    visual_threshold: float = Field(default=0.01, ge=0, le=1)


    @model_validator(mode="after")
    def viewport_bounds(self):
        if (self.max_navigation_ms is not None or self.max_action_ms is not None) and not self.measure_performance:
            raise ValueError("Timing thresholds require measurement")
        if not 240 <= self.viewport[0] <= 3840 or not 240 <= self.viewport[1] <= 2160:
            raise ValueError("Viewport is outside supported resource limits")
        return self


class TelegramEvent(StrictModel):
    kind: Literal["message", "callback"] = "message"
    text: str | None = Field(default=None,max_length=1000)
    callback: str | None = Field(default=None,max_length=64)
    user_id: int = Field(default=501,gt=0)
    chat_id: int | None = None
    update_id: int | None = Field(default=None,ge=1)


class TelegramSpec(StrictModel):
    mode: Literal["local", "live"] = "local"
    scenario: Literal["start", "dialog", "invalid", "cancel", "callback", "isolation", "duplicate", "delivery"] = "start"
    bot_username: str | None = None
    factory: str = "autotest_skill.telegram_demo:create_dispatcher"
    events: list[TelegramEvent] = Field(default_factory=list,max_length=100)
    expected_messages: list[str] = Field(default_factory=list)
    defects: bool = False
    serve_fixture: bool = False
    expected_text: str | None = None
    timeout: float = Field(default=20, gt=0, le=120)


class AndroidAction(StrictModel):
    enabled: bool | None = None
    value_env: str | None = None
    action: Literal["click", "fill", "expect_text", "expect_visible", "back", "background", "screenshot", "restart", "set_network", "scroll_to", "hide_keyboard"]
    accessibility_id: str | None = None
    resource_id: str | None = None
    text: str | None = None
    value: str | None = None


    @model_validator(mode="after")
    def locator_contract(self):
        if self.action in {"click","fill","expect_text","expect_visible","scroll_to"} and sum(bool(x) for x in (self.accessibility_id,self.resource_id,self.text))!=1:
            raise ValueError("Native actions need exactly one semantic locator")
        if self.value is not None and self.value_env is not None:raise ValueError("Use one native value source")
        if self.action=='set_network' and self.enabled is None:raise ValueError("Network actions require an explicit enabled value")
        return self


class AndroidSpec(StrictModel):
    server_url: str = "http://127.0.0.1:4723"
    apk: str | None = None
    udid: str = Field(pattern=r"^[A-Za-z0-9_.:-]{1,128}$")
    reset: bool = True
    reuse_runtime: bool = False
    package: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z][A-Za-z0-9_]*)+$")
    activity: str = Field(pattern=r"^[.A-Za-z][.A-Za-z0-9_$]*$")
    actions: list[AndroidAction] = Field(default_factory=list)
    timeout: float = Field(default=30, gt=0, le=300)
    device_name: str = "Android"
    baseline: str | None = None
    visual_threshold: float = Field(default=0.01,ge=0,le=1)


class PerformanceSpec(StrictModel):
    base_url: str
    path: str = "/health"
    engine: Literal["builtin", "k6"] = "builtin"
    requests: int = Field(default=10, ge=1, le=1000)
    concurrency: int = Field(default=1, ge=1, le=20)
    warmup: int = Field(default=2, ge=0, le=20)
    max_p95_ms: float = Field(default=1000, gt=0)
    max_error_rate: float = Field(default=0, ge=0, le=1)
    baseline: str | None = None
    max_regression_ratio: float = Field(default=1.5, gt=1)
    timeout: float = Field(default=10, gt=0, le=120)


class SecuritySpec(StrictModel):
    tool: Literal["secrets", "dependencies", "semgrep", "gitleaks", "web_headers"] = "secrets"
    required_headers: dict[str,str] = Field(default_factory=lambda:{"x-content-type-options":"nosniff"})
    path: str = "."
    base_url: str | None = None
    timeout: float = Field(default=120, gt=0, le=600)


SPECS = {"http": HttpSpec, "command": CommandSpec, "web": WebSpec,
         "telegram": TelegramSpec, "android": AndroidSpec,
         "performance": PerformanceSpec, "security": SecuritySpec}


class Check(StrictModel):
    id: str = Field(pattern=r"^[a-z][a-z0-9_.-]{0,63}$")
    kind: Literal["http", "command", "web", "telegram", "android", "performance", "security"]
    oracle: str = Field(min_length=10)
    requirement: str = Field(min_length=1)
    severity: Literal["critical", "high", "medium", "low", "info"] = "medium"
    profiles: list[Literal["smoke", "changed", "release"]] = Field(default_factory=lambda: ["smoke", "changed", "release"])
    tags: list[str] = Field(default_factory=list)
    covers: list[str] = Field(default_factory=list)
    depends_on: list[str] = Field(default_factory=list)
    mutating: bool = False
    spec: Any

    @model_validator(mode="after")
    def validate_spec(self):
        self.spec = SPECS[self.kind].model_validate(self.spec)
        return self


class Config(StrictModel):
    version: Literal[1] = 1
    project: str = Field(min_length=1)
    project_root: str = "."
    allowed_origins: list[str] = Field(default_factory=list)
    allow_mutations: bool = False
    allow_project_commands: bool = False
    allow_device_controls: bool = False
    budgets: Budgets = Field(default_factory=Budgets)
    checks: list[Check] = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def consistency(self):
        self.allowed_origins = [origin(url) for url in self.allowed_origins]
        by_id = {check.id: check for check in self.checks}
        if len(by_id) != len(self.checks):
            raise ValueError("Check IDs must be unique")
        for check in self.checks:
            spec = check.spec
            if check.mutating and not self.allow_mutations:
                raise ValueError("Mutation requires configuration authorization")
            if check.kind == "command" and not self.allow_project_commands:
                raise ValueError("Project commands require configuration authorization")
            if check.kind == "http" and spec.method not in {"GET", "HEAD", "OPTIONS"} and not check.mutating:
                raise ValueError("Mutating HTTP methods must be declared")
            if check.kind == "web" and any(a.action in {"fill", "click", "double_click", "press"} and not a.safe_read_only for a in spec.actions) and not check.mutating:
                raise ValueError("Interactive browser actions must declare mutation or read-only intent")
            if check.kind=='android':
                if not any(a.action in {'expect_text','expect_visible'} for a in spec.actions):
                    raise ValueError("Native checks need a semantic assertion")
                if (spec.apk or any(a.action in {'click','fill','back','background','restart','set_network'} for a in spec.actions)) and not check.mutating:
                    raise ValueError("Native state changes must declare mutation")
                if any(a.action=='set_network' for a in spec.actions) and not self.allow_device_controls:
                    raise ValueError("Device network controls require separate authorization")
            if check.kind=='telegram' and spec.mode=='live' and not check.mutating:
                raise ValueError("Live Telegram conversations must declare mutation")
            if check.kind == "telegram" and spec.factory != "autotest_skill.telegram_demo:create_dispatcher":
                if not self.allow_project_commands or not spec.events or not spec.expected_messages:
                    raise ValueError("Custom bot imports require command permission, events and expected replies")
            for field in ("base_url", "server_url"):
                value = getattr(spec, field, None)
                if value and origin(value) not in self.allowed_origins:
                    raise ValueError("Target origin is outside the configured allowlist")
            path = getattr(spec, "path", None)
            if check.kind in {"http", "web", "performance"} and (not path.startswith("/") or path.startswith("//") or "\\" in path):
                raise ValueError("Request paths must be relative to the configured origin")
            for candidate in [path,*[a.path for a in getattr(spec,'actions',[]) if getattr(a,'path',None)]]:
                if candidate and (any(ord(c)<32 or ord(c)==127 for c in candidate) or any(re.search(r"password|token|secret|session|api.?key|jwt|credential",key,re.I) for key,_ in parse_qsl(urlsplit(candidate).query))):
                    raise ValueError("Secrets and control characters cannot be placed in URL paths")
            for field in ('apk','baseline','openapi_file'):
                candidate=getattr(spec,field,None)
                if candidate and (Path(candidate).is_absolute() or '..' in Path(candidate).parts):
                    raise ValueError("Input file paths must remain under the project root")
            for action in getattr(spec,'actions',[]):
                if getattr(action,'value_env',None) and not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*",action.value_env):
                    raise ValueError("Invalid action environment binding")
            if check.kind == "http" and any(key.lower() in {"authorization", "cookie", "proxy-authorization"} for key in spec.headers):
                raise ValueError("Credential headers must use environment bindings or captures")
            for field in ("headers_env", "json_env"):
                for name in getattr(spec, field, {}).values():
                    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
                        raise ValueError("Invalid environment binding name")
            if any(dep not in by_id for dep in check.depends_on):
                raise ValueError("Unknown check dependency")
        visiting, visited = set(), set()
        def visit(identifier):
            if identifier in visiting:
                raise ValueError("Check dependencies contain a cycle")
            if identifier in visited:
                return
            visiting.add(identifier)
            for dep in by_id[identifier].depends_on:
                visit(dep)
            visiting.remove(identifier)
            visited.add(identifier)
        for identifier in by_id:
            visit(identifier)
        return self


def load_config(path):
    source = Path(path).resolve()
    if source.stat().st_size > 1_000_000:
        raise ValueError("Configuration exceeds the size limit")
    data = yaml.safe_load(source.read_text())
    config = Config.model_validate(data)
    root = (source.parent / config.project_root).resolve()
    if not root.is_dir():
        raise ValueError("Project root is not a directory")
    return config, root


def execute(args):
    config, root = load_config(args.config)
    print(json.dumps({"valid": True, "project": config.project, "root": str(root), "checks": len(config.checks)}))
    return 0
