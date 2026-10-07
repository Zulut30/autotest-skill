"""Errors whose meaning must survive reporting."""

class Blocked(RuntimeError):
    """A required runtime prerequisite is unavailable."""


class BudgetExceeded(Blocked):
    """The run exhausted an explicitly configured resource budget."""
