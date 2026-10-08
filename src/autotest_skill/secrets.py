"""Redaction is applied before evidence is written, not only when rendered."""

import os
import re

from .errors import Blocked

SENSITIVE = re.compile(
    r"password|passwd|token|secret|authorization|cookie|api.?key|api.?hash|session|jwt|credential",
    re.IGNORECASE,
)


class Redactor:
    def __init__(self):
        self.values = set()
        for name in os.environ:
            if SENSITIVE.search(name):
                self.add(os.environ[name])

    def add(self, value):
        if isinstance(value, str) and value:
            self.values.add(value)

    def text(self, value):
        text = str(value)
        for secret in sorted(self.values, key=len, reverse=True):
            if len(secret) >= 4:
                text = text.replace(secret, "[REDACTED]")
            else:
                text = re.sub(r"(?<!\w)" + re.escape(secret) + r"(?!\w)", "[REDACTED]", text)
        text = re.sub(
            r"(?i)([?&](?:password|token|secret|session|api[_-]?key|jwt|credential)=)[^&#\s]+",
            r"\1[REDACTED]",
            text,
        )
        return re.sub(r"(?i)(bearer\s+)[a-z0-9._~+/=-]+", r"\1[REDACTED]", text)

    def clean(self, value):
        if isinstance(value, dict):
            return {
                self.text(key): "[REDACTED]" if SENSITIVE.search(str(key)) else self.clean(item)
                for key, item in value.items()
            }
        if isinstance(value, (list, tuple)):
            return [self.clean(item) for item in value]
        if isinstance(value, str):
            return self.text(value)
        return value

    def binding(self, name):
        value = os.environ.get(name)
        if not value:
            raise Blocked(f"Required environment binding {name} is absent")
        self.add(value)
        return value
