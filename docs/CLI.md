# CLI contract

Commands: `doctor [--probe-browser]`, `discover [path]`, `validate CONFIG`, `plan CONFIG`, `run CONFIG`, `report RUN_DIRECTORY`, `benchmark`, `demo [--defects]`.

Plans and runs accept `--profile smoke|changed|release` and repeated `--changed-file PATH`. Runs accept `--output DIRECTORY`. Each command supports `--help`. Paths are resolved from the documented working directory; configuration-relative project roots are explicit.

Run exit codes: 0 = evaluated checks pass; 1 = confirmed failed checks; 2 = blocked prerequisites, invalid configuration or zero evaluated checks; 3 = executor error; 130 = interruption. Diagnostic and planning success is not a claim that application checks ran.

During development an unavailable handler exits 2 rather than reporting a fake pass. Configuration errors show field locations and error types, not submitted secret values.
