#!/bin/bash
# Exercise pi package migration and Vertex launcher behavior offline.
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"
uv run --no-project --with pytest python -m pytest -q \
    tools/devenv_migration/tests/test_pi_mcp_adapter_migration.py \
    tools/devenv_migration/tests/test_pi_vertex_launchers.py \
    tools/devenv_migration/tests/test_pi_shared_packages.py \
    tools/devenv_migration/tests/test_pi_installer_isolation.py \
    tools/devenv_migration/tests/test_pi_provider_setup.py
