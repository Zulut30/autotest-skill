# Contributing

Use Linux and Python 3.12. Run `scripts/install.sh`, install/probe Chromium, then `.venv/bin/pytest -q` and `.venv/bin/autotest benchmark`. Run Ruff checks/format checks on changed Python files. A missing optional tool is a recorded skip or blocked prerequisite, not evidence that its workflow passed.

For an escaped bug, describe the requirement, concrete trigger, expected/actual behavior and target/runtime version. Add a clean control and an independently reproducible defect case where possible. Use synthetic data. Review screenshots and reproduction archives before attaching them to a public issue.

Adapters follow [the contract](docs/ADAPTER-CONTRACT.md) and [extension guide](docs/EXTENDING.md). Keep source warnings separate from proven violations. Do not silently update baselines, drop failed corpus cases, hide retries or convert empty/blocked runs into success.

Optional native checks require a dedicated runner and `AUTOTEST_RUN_ANDROID=1`; live Telegram requires secure bindings and its own genuine wire evidence. Describe the actual validated scope in a pull request. The project remains alpha while its mandatory external release gates are open.
