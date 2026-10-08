#!/usr/bin/env bash
set -eu
cd "$(dirname "$0")/.."
root="${AUTOTEST_TOOLS_DIR:-$PWD/.autotest/tools}"
export UV_CACHE_DIR="${UV_CACHE_DIR:-$PWD/.autotest/uv-cache}"
mkdir -p "$root"
if [ ! -x "$root/semgrep-venv/bin/python" ]; then
 uv venv --python 3.12 "$root/semgrep-venv"
fi
uv pip sync --python "$root/semgrep-venv/bin/python" scripts/security-tools.lock
printf 'Set AUTOTEST_SEMGREP_BINARY=%s/semgrep-venv/bin/semgrep\n' "$root"
