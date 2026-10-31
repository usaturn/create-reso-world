#!/usr/bin/env zsh
set -euo pipefail

PROVIDERS=("deepinfra")

# PI_CODING_AGENT_DIR が設定されている場合も考慮
# Keep path-owned trailing newlines; remove only the CLI delimiter and sentinel.
PI_DIR="$(python3 "${0:A:h}/../.devcontainer/pi-provider-setup.py" --agent-dir && printf .)"
PI_DIR="${PI_DIR%$'\n'.}"
readonly PI_DIR
# Follow-up Pi commands must reuse this interpretation, even after joining paths.
export PI_CODING_AGENT_DIR="${PI_DIR}"
MODELS_JSON="${PI_DIR}/models.json"

# モデル定義の正は .devcontainer/pi-models.json とする。
# ここに定義を埋め込むと install_beforehand.bash が配置する内容とずれる。
MODELS_SOURCE="${0:A:h}/../.devcontainer/pi-models.json"

echo "=== Pi + DeepInfra setup ==="

#
# 1. API token check
#
if [[ -z "${DEEPINFRA_TOKEN:-}" ]]; then
  echo "ERROR: DEEPINFRA_TOKEN is not set."
  echo
  echo 'Run:'
  echo '  export DEEPINFRA_TOKEN="your-token"'
  exit 1
fi

echo "DEEPINFRA_TOKEN: SET"

if [[ ! -f "${MODELS_SOURCE}" ]]; then
  echo "ERROR: Model definition source not found: ${MODELS_SOURCE}"
  exit 1
fi

echo "Model source: ${MODELS_SOURCE}"

# Validate all inputs before mkdir/backup/update. The helper is bootstrap-safe.
python3 "${0:A:h}/../.devcontainer/pi-provider-setup.py" \
    "${PI_DIR}" "${MODELS_SOURCE}" deepinfra

echo "models.json JSON validation: OK"

# Launchers live outside the shared ~/.pi mount. Refresh the launcher/helper,
# but keep every user-owned tier config, including explicit pidid edits.
mkdir -p "${HOME}/.local/bin"
install -m 0755 "${0:A:h}/../.devcontainer/pidid" "${HOME}/.local/bin/pidid"
zsh "${0:A:h}/setup_pi_superagents.zsh" --if-absent

#
# 6. Result
#
echo
echo "=== Setup complete ==="
echo "Providers: ${PROVIDERS[*]}"
echo "Config   : ${MODELS_JSON}"
echo
echo "Verify with:"
echo "  pi --list-models deepinfra"
