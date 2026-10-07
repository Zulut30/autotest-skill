#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
command -v uv >/dev/null 2>&1 || { echo 'Install uv from its official distribution first.' >&2; exit 2; }
uv sync --frozen --all-extras --group dev
uv run --frozen --all-extras autotest --version
