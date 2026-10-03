#!/bin/bash
# Isolated pi-only migration and real provisioning extension selection.
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec uv run --no-project python "$root/.devcontainer/tests/test_pi_mcp_cleanup.py" "$@"
