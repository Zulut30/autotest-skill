# CLI contract

Commands: `skill`, `doctor [--probe-browser]`, `discover [path]`, `validate CONFIG`, `plan CONFIG`, `run CONFIG`, `report RUN_DIRECTORY`, `benchmark`, `regression (--case CASE | --from-run RUN_DIRECTORY) [--check CHECK_ID] --output PATH`, `demo [--defects]`.

`skill` locates the installed agent instructions and bundled references. It does not execute product checks or register the skill with an agent host. Source/wheel installation details are in [DISTRIBUTION.md](DISTRIBUTION.md).

Plans and runs accept `--profile smoke|changed|release` and repeated `--changed-file PATH`. Runs accept `--output DIRECTORY`. Each command supports `--help`. Paths are resolved from the documented working directory; configuration-relative project roots are explicit.

Run exit codes: 0 = evaluated checks pass; 1 = confirmed failed checks; 2 = blocked prerequisites, invalid configuration or zero evaluated checks; 3 = executor error; 130 = interruption. Diagnostic and planning success is not a claim that application checks ran.

During development an unavailable handler exits 2 rather than reporting a fake pass. Configuration errors show field locations and error types, not submitted secret values.

## Regression from a saved web failure

```bash
.venv/bin/autotest regression --from-run .autotest/runs/RUN_ID \
  --check web.auth-state --output tests/test_reported_regression.py
```

The command reads matching, completed `result.json` and `reproduction.json`; it does not execute the target or modify application code. The selected web check must have failed its declared oracle. Only reliably passed web/HTTP prerequisites are included. Observations, blocked/skipped/tool-error results, interrupted runs, mismatched metadata and unsupported prerequisite kinds are rejected with exit 2. `--check` is optional only when exactly one failed web check is present. Existing output files are never overwritten; proposals have private file permissions.

Review the proposal, start a fresh authorized test target and restore its test data. Run the generated test from the intended project root. To rebind a single configured origin to a reviewed local target:

```bash
AUTOTEST_REGRESSION_BASE_URL=http://127.0.0.1:8765 \
  .venv/bin/pytest tests/test_reported_regression.py -q
```

Without the override, the saved origins are used. Multi-origin rebinding is unsupported. `AUTOTEST_REGRESSION_ROOT` optionally names the project directory for declared local input files. The proposal retains mutation permission from the reviewed configuration, disables project/device commands and sets retries to zero. A blocked, failed or flaky replay fails pytest; it cannot become a passing regression.

Supply required credentials through the original environment bindings. Reproduction metadata preserves binding names and capture paths without their credential values. Redacted literal credentials cannot be regenerated: convert the original scenario to bindings and record a new run. Sensitive inline UI values are also rejected. This first report-based generator supports failed web scenarios with web/HTTP prerequisites; manual prose reports, arbitrary pytest synthesis and native/bot failures are not supported. The existing seeded `--case` mode remains available.
