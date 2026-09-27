#!/bin/bash
# devcontainer.json の mounts と initialize.bash が作るパスを突き合わせる関数集（source して使う）。
# 仕様: docs/superpowers/specs/2026-09-26-create-reso-world-redesign-design.md 7.1・7.2・9.1 節
# 使うのは .devcontainer/test-initialize-mounts.bash と scripts/check-layout.sh。
# 書式の前提（行単位で読む）:
#   devcontainer.json: 1 行に 1 つ "source=${localEnv:HOME}/<rel>,target=/home/vscode/<rel>,type=bind,..."。// で始まる行は読まない
#   initialize.bash:   作るパスを 1 行に 1 つ "${HOME}/<rel>" だけ書く（mkdir -p と touch の引数。行末の \ は可）

# mounts_from_devcontainer DEVCONTAINER_JSON
# mounts を "<rel><TAB><target>" で 1 行ずつ出力する（<rel> はソースの ~/ からの相対パス）。ファイルが無ければ 1
mounts_from_devcontainer() {
  local json="$1" line
  local re='"source=\$\{localEnv:HOME\}/([^,"]+),target=([^,"]+),type=bind[^"]*"'
  [ -f "$json" ] || return 1
  while IFS= read -r line; do
    [[ "$line" =~ ^[[:space:]]*// ]] && continue
    [[ "$line" =~ $re ]] && printf '%s\t%s\n' "${BASH_REMATCH[1]}" "${BASH_REMATCH[2]}"
  done < "$json"
  return 0
}

# mounts_from_initialize INITIALIZE_BASH
# initialize.bash が作るパス（"${HOME}/<rel>" だけを書いた行）を <rel> で 1 行ずつ出力する。ファイルが無ければ 1
mounts_from_initialize() {
  local file="$1" line
  local re='^[[:space:]]*"\$\{HOME\}/([^"]+)"[[:space:]]*\\?$'
  [ -f "$file" ] || return 1
  while IFS= read -r line; do
    [[ "$line" =~ $re ]] && printf '%s\n' "${BASH_REMATCH[1]}"
  done < "$file"
  return 0
}

# mounts_compare DEVCONTAINER_JSON INITIALIZE_BASH
# mounts のソースの集合と initialize.bash が作るパスの集合を比べ、食い違いを 1 件 1 行で出力する。
# target が /home/vscode/<rel> でない mount も食い違いとして出力する。一致すれば何も出力せず 0、それ以外は 1
mounts_compare() {
  local json="$1" init="$2" pairs created rel target bad=0
  pairs="$(mounts_from_devcontainer "$json")" || { printf 'mounts: %s not found\n' "$json"; return 1; }
  created="$(mounts_from_initialize "$init")" || { printf 'mounts: %s not found\n' "$init"; return 1; }
  [ -n "$pairs" ] || { printf 'mounts: no mounts found in %s\n' "$json"; return 1; }
  while IFS=$'\t' read -r rel target; do
    if [ "$target" != "/home/vscode/$rel" ]; then
      printf 'mounts: ~/%s is mounted at %s, expected /home/vscode/%s\n' "$rel" "$target" "$rel"
      bad=1
    fi
    grep -qxF -- "$rel" <<<"$created" && continue
    printf 'mounts: ~/%s is mounted by devcontainer.json but not created by initialize.bash\n' "$rel"
    bad=1
  done <<<"$pairs"
  while IFS= read -r rel; do
    [ -n "$rel" ] || continue
    grep -qxF -- "$rel" <<<"$(cut -f1 <<<"$pairs")" && continue
    printf 'mounts: ~/%s is created by initialize.bash but not mounted by devcontainer.json\n' "$rel"
    bad=1
  done <<<"$created"
  return "$bad"
}
