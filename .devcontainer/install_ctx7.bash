#!/bin/bash
# find-docs スキルが使う Context7 CLI（ctx7）を、固定した版で npm のグローバルに入れ、PATH 上の ctx7 の版を確かめる。
# 版はここにだけ書く。更新の手順は .devcontainer/README.md の「Context7 CLI（ctx7）」にあり、rebuild せずに入れ替えるときも
# このスクリプトを実行する。ctx7 setup は実行しない（共有の ~/.claude・~/.claude.json・~/.codex などへ MCP 設定や
# スキルを書き込み、find-docs とも重複する）
set -euo pipefail
# 2026-10-18 に npm の latest で確かめた版（engines.node は >=22.13.0）
readonly CTX7_CLI_VERSION="0.8.0"
fail() { printf '[install_ctx7] ERROR: %s\n' "$1" >&2; exit 1; }

npm install -g "ctx7@${CTX7_CLI_VERSION}" || fail "npm install -g ctx7@${CTX7_CLI_VERSION} failed."
ctx7_path="$(command -v ctx7)" || fail 'ctx7 is not on PATH after the install.'
installed="$(ctx7 --version)" || fail "${ctx7_path} --version failed."
installed="${installed//[[:space:]]/}"
[ "$installed" = "$CTX7_CLI_VERSION" ] ||
    fail "${ctx7_path} is version ${installed}, not ${CTX7_CLI_VERSION}. Another ctx7 may come first on PATH."
printf '[install_ctx7] Context7 CLI %s installed at %s.\n' "$CTX7_CLI_VERSION" "$ctx7_path"
