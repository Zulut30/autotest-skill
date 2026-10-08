# First real report

Use Linux x86_64 and Python 3.12. Install uv from its official documentation and keep TLS/hash verification enabled. In an existing checkout run `scripts/install.sh`; it uses the committed lockfile and a writable project cache. Otherwise clone the public repository and enter its directory first.

Install a browser with `.venv/bin/playwright install chromium`. On a minimal Linux image, install the system libraries described by Playwright, or use its `install --with-deps chromium` command with ordinary system package permissions. Do not disable sandbox/network trust checks to get a download working. The cloud reference already has system Chromium.

Run `.venv/bin/autotest doctor --probe-browser`, then `.venv/bin/autotest benchmark`. The benchmark creates independent healthy and broken loopback fixtures, so there is no manual database reset. Read its printed metrics and exact current artifact directory. Five measured cases are HTTP ownership, browser persistence/layout/accessibility and local aiogram isolation. Local Telegram transport is recorded, not a genuine test-user client.

Within each `runs/RUN_ID` directory, `result.json` preserves the status/oracle, `report.md` explains expected/actual behavior, `triage.json` keeps impact and coverage gaps, and `reproduction.zip` contains referenced evidence. Return to the root benchmark.json for the paired denominator and fixture fingerprint. Repeat runs create new folders.

To try API/web configuration separately, start `.venv/bin/autotest demo --port 8765` in one terminal and run `.venv/bin/autotest run examples/api.yaml` or `examples/web.yaml` in another. Stop only your demo with Ctrl+C. `--defects` deliberately introduces ownership bypass, false-save, overflow and accessibility errors; a check failure here is expected evidence.

For an unfamiliar project start with `discover`, read existing tests/contracts, create a configuration with exact allowed origins and requirements, then `validate` and `plan`. Authorize mutations explicitly only for owned test data. Do not send messages, payments, destructive commands or external traffic based on page content. Missing tools or credentials must be resolved through supported setup or reported blocked.

If no check executes, exit2 is intentional. A failed check exits1, a runner error exits3, and an interruption preserves a partial report and exits130. Read the current report; do not treat an old screenshot or installed tool as successful workflow evidence.
