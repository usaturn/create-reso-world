#!/bin/bash
# .devcontainer/resoloop.lock を読むための関数集。source して使い、単体では何もしない。
# 仕様: docs/superpowers/specs/2026-09-26-create-reso-world-redesign-design.md 6.1・6.2・9.1 節
# ロックは source せず、1 行ずつ書式を検証してから読む（値にコマンドが紛れ込んでも実行しない）。

RESOLOOP_LOCK_KEYS=(RESOLOOP_MODE RESOLOOP_NUGET_VERSION RESOLOOP_FORK_ORIGIN RESOLOOP_FORK_UPSTREAM
  RESOLOOP_FORK_REF RESOLOOP_FORK_COMMIT RESOLOOP_FORK_PACKAGE_VERSION RESOLOOP_FORK_PR RESOLOOP_FORK_SDK)

# resoloop_lock_load FILE
# ロックを検証し、RESOLOOP_LOCK_KEYS の各変数と RESOLOOP_EXPECTED_VERSION を設定する。
# 不正なら理由を標準エラーに 1 件 1 行で出して 1 を返し、変数は設定しない。
resoloop_lock_load() {
  local file="$1" line key value n=0 k
  local blank_re='^[[:space:]]*(#.*)?$' kv_re='^([A-Z][A-Z0-9_]*)=([A-Za-z0-9._:/@+-]+)$'
  local -a errors=()
  local -A seen=()
  if [ ! -f "$file" ]; then
    printf 'resoloop.lock: %s not found\n' "$file" >&2
    return 1
  fi
  while IFS= read -r line || [ -n "$line" ]; do
    n=$((n + 1))
    [[ "$line" =~ $blank_re ]] && continue
    if [[ ! "$line" =~ $kv_re ]]; then
      errors+=("line $n is not KEY=VALUE (the value may use only letters, digits and ._:/@+-)")
      continue
    fi
    key="${BASH_REMATCH[1]}" value="${BASH_REMATCH[2]}"
    if [[ " ${RESOLOOP_LOCK_KEYS[*]} " != *" $key "* ]]; then
      errors+=("line $n: unknown key $key")
    elif [ -n "${seen[$key]+x}" ]; then
      errors+=("line $n: duplicate key $key")
    else
      seen["$key"]="$value"
    fi
  done < "$file"
  for k in "${RESOLOOP_LOCK_KEYS[@]}"; do
    [ -n "${seen[$k]+x}" ] || errors+=("missing key $k")
  done
  case "${seen[RESOLOOP_MODE]-nuget}" in
    nuget|fork) ;;
    *) errors+=("RESOLOOP_MODE must be nuget or fork, not ${seen[RESOLOOP_MODE]}") ;;
  esac
  if [ -n "${seen[RESOLOOP_FORK_COMMIT]+x}" ] && [[ ! "${seen[RESOLOOP_FORK_COMMIT]}" =~ ^[0-9a-f]{40}$ ]]; then
    errors+=("RESOLOOP_FORK_COMMIT must be a full 40-character commit id")
  fi
  if [ -n "${seen[RESOLOOP_FORK_SDK]+x}" ] && [[ ! "${seen[RESOLOOP_FORK_SDK]}" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    errors+=("RESOLOOP_FORK_SDK must be an exact SDK version such as 10.0.201")
  fi
  if [ ${#errors[@]} -gt 0 ]; then
    printf 'resoloop.lock: %s\n' "${errors[@]}" >&2
    return 1
  fi
  for k in "${RESOLOOP_LOCK_KEYS[@]}"; do
    printf -v "$k" '%s' "${seen[$k]}"
  done
  if [ "$RESOLOOP_MODE" = fork ]; then
    RESOLOOP_EXPECTED_VERSION="$RESOLOOP_FORK_PACKAGE_VERSION"
  else
    RESOLOOP_EXPECTED_VERSION="$RESOLOOP_NUGET_VERSION"
  fi
}

# resoloop_lock_sdk_declared DEVCONTAINER_JSON SDK
# devcontainer.json の "additionalVersions"（カンマ区切り）のどれかに SDK があれば 0 を返す。
# // で始まるコメント行は読まない。
resoloop_lock_sdk_declared() {
  local json="$1" sdk="$2" list v
  local -a versions=()
  [ -f "$json" ] || return 1
  while IFS= read -r list; do
    IFS=',' read -r -a versions <<<"$list"
    for v in "${versions[@]}"; do
      [ "${v//[[:space:]]/}" = "$sdk" ] && return 0
    done
  done < <(sed -n -e '/^[[:space:]]*\/\//d' -e 's/.*"additionalVersions"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$json")
  return 1
}

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
