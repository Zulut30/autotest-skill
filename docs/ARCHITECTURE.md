# Architecture decision: Python execution core

Python 3.12+ hosts the CLI and adapters. HTTPX handles API requests; Pydantic validates strict configuration and result contracts; PyYAML reads configuration. Optional extras isolate Playwright, aiogram/Telethon and Appium dependencies. Pytest verifies real behavior. uv.lock pins transitive dependencies.

The core runs without an LLM API key. SKILL.md instructs an existing coding agent to discover requirements, invoke deterministic tools and interpret evidence. No hosted AI dependency is hidden in test execution.

Flow: repository discovery → explicit plan and oracles → bounded adapters → current-run artifacts → JSON/Markdown report. The CLI never executes instructions from a target page.

External tools (k6, Semgrep, Gitleaks) are optional adapters with explicit readiness checks. An unavailable required tool produces blocked, not a fabricated pass. Native Android and live Telegram require their real runtime prerequisites.
