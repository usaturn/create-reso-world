#!/usr/bin/env zsh
set -e
PROVIDERS=("deepinfra")

# PI_CODING_AGENT_DIR が設定されている場合も考慮
PI_DIR="${PI_CODING_AGENT_DIR:-${HOME}/.pi/agent}"
if [[ "$PI_DIR" == '~' || "$PI_DIR" == '~/'* ]]; then
  PI_DIR="${HOME}${PI_DIR#\~}"
fi
MODELS_JSON="${PI_DIR}/models.json"

# モデル定義の正は .devcontainer/pi-models.json とする。
# ここに定義を埋め込むと install_beforehand.bash が配置する内容とずれる。
MODELS_SOURCE="${0:A:h}/pi-models.json"

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

#
# 2. Pi config directory
#
mkdir -p "${PI_DIR}"

echo "Pi config dir: ${PI_DIR}"

# 入力とリンクをバックアップや変更の前に検査する。symlink・hard link を置き換えると
# 共有先が更新されなくなる。不正な JSON をバックアップの後で検出すると、不要なバックアップが残る。
python3 - "${MODELS_SOURCE}" "${MODELS_JSON}" <<'PY'
import sys
from pathlib import Path

source, models, *others = map(Path, sys.argv[1:])
sys.path.insert(0, str(source.resolve().parent))
from pi_json import load_models, load_object, require_plain_file

try:
    load_models(source)
    for path in (models, *others):
        require_plain_file(path)
        if path.exists():
            (load_models if path == models else load_object)(path)
except ValueError as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)
PY

#
# 3. Backup
#
if [[ -f "${MODELS_JSON}" ]]; then
  BACKUP="$(mktemp "${MODELS_JSON}.bak.$(date +%Y%m%d-%H%M%S).XXXXXX")"
  cp -p "${MODELS_JSON}" "${BACKUP}" || {
    code=$?
    rm -f -- "${BACKUP}"
    exit "$code"
  }
  echo "Backup: ${BACKUP}"
fi

#
# 4. Add/update the DeepInfra provider
#
# 定義は .devcontainer/pi-models.json から読み取る。
# deepinfra 以外のプロバイダはそのまま保持する。
#
python3 - "${MODELS_JSON}" "${MODELS_SOURCE}" "${PROVIDERS[@]}" <<'PY'
import sys
from pathlib import Path

path = Path(sys.argv[1])
source = Path(sys.argv[2])
requested = sys.argv[3:]
sys.path.insert(0, str(source.resolve().parent))
from pi_json import load_models, write_object

try:
    source_providers = load_models(source).get("providers", {})
except ValueError as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)

definitions = {}
for provider in requested:
    definition = source_providers.get(provider)
    if definition is None:
        print(
            f"ERROR: Provider {provider!r} is not defined in {source}",
            file=sys.stderr,
        )
        sys.exit(1)
    definitions[provider] = definition

if path.exists():
    try:
        data = load_models(path)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
else:
    data = {}

providers = data.setdefault("providers", {})

for provider, definition in definitions.items():
    providers[provider] = definition

write_object(path, data)

print(f"Updated: {path}")
PY

#
# 5. Validate JSON
#
python3 -m json.tool "${MODELS_JSON}" >/dev/null

echo "models.json JSON validation: OK"

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
