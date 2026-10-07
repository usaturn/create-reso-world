#!/bin/bash
# Run the standard-library Python tests in tests/scripts (test_*.py; the Superpowers helpers) through the CI runner.
set -euo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$root"
exec uv run --no-project python -m unittest discover -s tests/scripts -p 'test_*.py'
