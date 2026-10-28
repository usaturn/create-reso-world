#!/bin/bash
# find-docs スキルが使う Context7 CLI（ctx7）を、npm の最新版でグローバルに入れ、PATH 上の ctx7 が npm のグローバルの
# ctx7 であることを確かめる。版は固定しない（#290）。postCreate と、rebuild せずに最新へ上げるときに実行する。
# 手順は .devcontainer/README.md の「Context7 CLI（ctx7）」にある。ctx7 setup は実行しない（共有の ~/.claude・
# ~/.claude.json・~/.codex などへ MCP 設定やスキルを書き込み、find-docs とも重複する）。ctx7 upgrade も実行しない
set -euo pipefail
fail() { printf '[install_ctx7] ERROR: %s\n' "$1" >&2; exit 1; }

npm install -g ctx7@latest || fail 'npm install -g ctx7@latest failed.'
npm_root="$(npm root -g)" && [ -n "$npm_root" ] || fail 'npm root -g failed.'
ctx7_path="$(command -v ctx7)" || fail 'ctx7 is not on PATH after the install.'
# 版ではなく実体の場所で判定し、PATH の前のほうにある別の ctx7 は実行しない。パッケージの中のファイル名は仮定しない
root_real="$(readlink -f -- "$npm_root")" || fail "cannot resolve ${npm_root}."
ctx7_real="$(readlink -f -- "$ctx7_path")" || fail "cannot resolve ${ctx7_path}."
case "$ctx7_real" in
    "$root_real"/ctx7/*) ;;
    *) fail "${ctx7_path} (${ctx7_real}) is not the npm global ctx7 under ${root_real}/ctx7/. Another ctx7 may come first on PATH." ;;
esac
installed="$("$ctx7_path" --version)" || fail "${ctx7_path} --version failed."
installed="${installed//[[:space:]]/}"
[ -n "$installed" ] || fail "${ctx7_path} --version printed nothing."
printf '[install_ctx7] Context7 CLI %s installed at %s.\n' "$installed" "$ctx7_path"
