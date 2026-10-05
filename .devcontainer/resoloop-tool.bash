#!/bin/bash
# ResoLoop のグローバルツールの版を読む関数集。source して使い、単体では何もしない。
# 使う側: .devcontainer/install_resoloop.bash、scripts/resoloop-fork.sh
# 仕様: docs/superpowers/specs/2026-10-06-issue-41-resoloop-latest-without-lock-design.md D-11

# resoloop_installed_version
# dotnet tool list --global から ResoLoop の導入済み版を出力する（未導入なら何も出力しない）。
# 一覧を取れなければ 1 を返す。
resoloop_installed_version() {
  local listing
  listing="$(dotnet tool list --global </dev/null)" || return 1
  awk 'tolower($1) == "resoloop" && !found { print $2; found = 1 }' <<<"$listing"
}

# resoloop_version_of TEXT
# resoloop --version の出力から版を取り出す。最初の空でない行の前後の空白と、+ 以降のビルドメタデータを除く。
# 空でない行が無ければ 1 を返す。
resoloop_version_of() {
  local line
  while IFS= read -r line; do
    line="${line#"${line%%[![:space:]]*}"}"
    line="${line%"${line##*[![:space:]]}"}"
    [ -n "$line" ] || continue
    printf '%s\n' "${line%%+*}"
    return 0
  done <<<"$1"
  return 1
}
