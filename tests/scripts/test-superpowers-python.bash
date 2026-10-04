#!/bin/bash
# Run standard-library Superpowers helper acceptance tests through the CI runner.
set -euo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$root"
exec uv run --no-project python -m unittest discover -s tests/scripts -p 'test_superpowers_*.py'
