"""Explicit adapter registry; target content cannot load executable plugins."""

import importlib
from typing import Protocol
from .context import Context
from .config import Check
from .results import CheckResult
from .errors import Blocked


class Adapter(Protocol):
    def __call__(self, check: Check, context: Context) -> CheckResult: ...


ADAPTERS = {"http": "http", "command": "command", "web": "web", "telegram": "telegram",
            "android": "android", "performance": "performance", "security": "security"}


def resolve(kind):
    if kind not in ADAPTERS:
        raise Blocked("Unsupported adapter")
    module_name = f"autotest_skill.adapters.{ADAPTERS[kind]}"
    try:
        return importlib.import_module(module_name).run
    except ModuleNotFoundError as exc:
        if exc.name == module_name or exc.name in {"playwright", "aiogram", "telethon", "appium"}:
            raise Blocked(f"Required {kind} adapter or optional dependency is unavailable") from exc
        raise
