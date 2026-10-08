# Continuous integration

[Checks workflow](../.github/workflows/checks.yml) runs on main pushes and pull requests with read-only repository permission. Actions are pinned to commits resolved from their official release tags. Python/uv install locked dependencies, execute lint, pytest, actual Chromium/HTTP/aiogram corpus checks, build packages and retain synthetic benchmark artifacts even on failure.

The hosted job covers local handlers and browser/API checks. Optional k6, Semgrep and Gitleaks integration tests explicitly skip when those tools are absent; their actual local evidence is recorded separately. Live Telegram credentials and Android devices are not implicit hosted runner capabilities. CI green alone does not close their mandatory release gates.

Tests assert failure, blockage, zero-execution, retries and interruption semantics. Failed or blocked declared checks retain nonzero exit codes. Artifact retention is limited to synthetic demo evidence, not arbitrary production logs. Configure any real credentials only through protected test environments, never workflow source or pull request code from unknown contributors.
