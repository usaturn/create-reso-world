#!/bin/bash
# .devcontainer にワークスペースの絶対パスを書いていないことを検査する。
# 固定したパスを使うと、worktree や別名の checkout から実行しても親の checkout を操作する（エラーにならない）ため、
# このパスは固定値で禁止する（F∩S）
set -euo pipefail
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if git grep -nF '/workspaces/reso-world' -- .devcontainer ':!.devcontainer/test-readme.bash'; then
  printf 'FAIL: .devcontainer hard-codes the workspace path\n' >&2
  exit 1
fi
printf 'PASS: no hard-coded workspace path\n'
