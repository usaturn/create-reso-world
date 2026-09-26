#!/bin/bash
# ホスト側で、devcontainer.json の mounts のソースを先に作る（initializeCommand）。
# 無いソースは Docker が root 所有のディレクトリとして作るため、ファイルの mount（~/.claude.json）が
# ディレクトリになったり、コンテナから書き込めなくなったりする。
# 一覧は devcontainer.json の mounts と 1 対 1 にする（.devcontainer/test-initialize-mounts.bash と
# scripts/check-layout.sh が .devcontainer/mounts.bash で突き合わせる）。1 行に 1 つ "${HOME}/<パス>" と書く。
set -e

mkdir -p \
  "${HOME}/.codex" \
  "${HOME}/.claude" \
  "${HOME}/.grok" \
  "${HOME}/.pi" \
  "${HOME}/.dsh" \
  "${HOME}/.local/share/devin" \
  "${HOME}/.config/devin" \
  "${HOME}/.local/share/cursor-agent" \
  "${HOME}/.config/gh" \
  "${HOME}/.cursor" \
  "${HOME}/.config/glab-cli" \
  "${HOME}/.config/gcloud" \
  "${HOME}/.config/create-reso-world"

if [ -d "${HOME}/.claude.json" ]; then
  echo "initialize: ~/.claude.json is a directory; remove it (Docker created it because the file did not exist) and rebuild" >&2
  exit 1
fi

touch \
  "${HOME}/.claude.json"

# 秘密情報（env）を置くディレクトリは本人だけが読めるようにする
chmod 700 "${HOME}/.config/create-reso-world"
