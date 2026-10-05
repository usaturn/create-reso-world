#!/bin/bash
# .devcontainer/resoloop-tool.bash の関数（導入済みの版の取得と、resoloop --version の解析）を検査する
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
tmp="$(mktemp -d)"
trap 'rm -rf -- "${tmp:?}"' EXIT
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
# shellcheck source=resoloop-tool.bash
source "$root/.devcontainer/resoloop-tool.bash"

# 1. resoloop --version の出力から版を取り出す
[ "$(resoloop_version_of $'0.1.0-preview.14\n')" = 0.1.0-preview.14 ] || fail 'plain version'
[ "$(resoloop_version_of $'  1.2.3+abc123  \n')" = 1.2.3 ] || fail 'whitespace and build metadata'
[ "$(resoloop_version_of $'\n\n2.0.0\nextra\n')" = 2.0.0 ] || fail 'first non-empty line'
if resoloop_version_of $'\n  \n' >/dev/null; then fail 'accepted empty output'; fi

# 2. dotnet tool list --global から導入済み版を読む（モックの dotnet。MOCK_HEADER で見出しを差し替える）
mkdir -p "$tmp/bin"
cat > "$tmp/bin/dotnet" <<'EOF'
#!/bin/bash
[ "$*" = 'tool list --global' ] || exit 64
[ "${MOCK_LIST_FAIL:-0}" = 0 ] || exit 1
printf '%s\n-------------------------------------\n' "${MOCK_HEADER:-Package Id      Version      Commands}"
[ -z "${MOCK_LIST_LINE:-}" ] || printf '%s\n' "$MOCK_LIST_LINE"
EOF
chmod +x "$tmp/bin/dotnet"
[ "$(PATH="$tmp/bin:$PATH" MOCK_LIST_LINE='resoloop  0.1.0-preview.14.fork.20260925.gabc1234  resoloop' resoloop_installed_version)" = 0.1.0-preview.14.fork.20260925.gabc1234 ] \
  || fail 'installed version'
[ "$(PATH="$tmp/bin:$PATH" MOCK_LIST_LINE='ResoLoop 1.0.0 resoloop' resoloop_installed_version)" = 1.0.0 ] || fail 'package id is case-insensitive'
# この環境の dotnet は見出しを日本語で出す
[ "$(PATH="$tmp/bin:$PATH" MOCK_HEADER='パッケージ ID      バージョン      コマンド' MOCK_LIST_LINE='resoloop  1.0.0  resoloop' resoloop_installed_version)" = 1.0.0 ] \
  || fail 'localized header'
[ -z "$(PATH="$tmp/bin:$PATH" MOCK_LIST_LINE='my-resoloop-plugin 1.0.0 other' resoloop_installed_version)" ] || fail 'matched a different package'
[ -z "$(PATH="$tmp/bin:$PATH" resoloop_installed_version)" ] || fail 'reported a version when nothing is installed'
if PATH="$tmp/bin:$PATH" MOCK_LIST_FAIL=1 resoloop_installed_version >/dev/null; then fail 'ignored a failing dotnet tool list'; fi

printf 'PASS: resoloop tool helpers behave as specified\n'
