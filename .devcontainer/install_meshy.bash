#!/bin/bash
# Only install and probe locally; never authenticate or make a paid request here.
set -euo pipefail
fail() { printf '[install_meshy] ERROR: %s\n' "$1" >&2; exit 1; }
if ! env -u MESHY_API_KEY npm install -g meshy-cli@0.4.0; then
    fail 'Meshy npm installation failed.'
fi
command -v meshy >/dev/null 2>&1 || fail 'meshy is not on PATH after installation.'
if ! env -u MESHY_API_KEY meshy --no-update-check --version; then
    fail 'Meshy version verification failed.'
fi
if ! env -u MESHY_API_KEY meshy --no-update-check --help; then
    fail 'Meshy help verification failed.'
fi
printf '[install_meshy] Meshy CLI installed and verified without authentication.\n'
