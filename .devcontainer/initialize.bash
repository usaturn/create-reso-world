#!/bin/bash
# ホスト側で、devcontainer.json の mounts のソースを先に作る（initializeCommand）。
# 無いソースは Docker が root 所有のディレクトリとして作るため、ファイルの mount（~/.claude.json）が
# ディレクトリになったり、コンテナから書き込めなくなったりする。
# 一覧は devcontainer.json の mounts と 1 対 1 にする（.devcontainer/test-initialize-mounts.bash と
# scripts/check-layout.sh が .devcontainer/mounts.bash で突き合わせる）。1 行に 1 つ "${HOME}/<パス>" と書く。
set -e

# Resonite の写真フォルダ（任意、usaturn/resoloop#13）。WSL で Windows の Pictures/Resonite へのリンクにすると、
# コンテナから読み取り専用で読める。リンク先が無いと Docker の mount が分かりにくいエラーで失敗するので、先に止める
screenshots="${HOME}/.local/share/create-reso-world/resonite-screenshots"
if [ -L "$screenshots" ] && [ ! -d "$screenshots" ]; then
  echo "initialize: ${screenshots} links to a missing folder ($(readlink "$screenshots")); check that the Windows drive is visible (ls /mnt/c) and that Resonite has saved a photo, or remove the link" >&2
  exit 1
fi

mkdir -p \
  "${HOME}/.codex" \
  "${HOME}/.claude" \
  "${HOME}/.pi" \
  "${HOME}/.local/share/devin" \
  "${HOME}/.config/devin" \
  "${HOME}/.local/share/cursor-agent" \
  "${HOME}/.config/gh" \
  "${HOME}/.cursor" \
  "${HOME}/.config/cursor" \
  "${HOME}/.config/glab-cli" \
  "${HOME}/.config/gcloud" \
  "${HOME}/.gemini/antigravity-cli" \
  "${HOME}/.config/create-reso-world" \
  "${HOME}/.local/share/create-reso-world/resonite-screenshots"

if [ -d "${HOME}/.claude.json" ]; then
  echo "initialize: ~/.claude.json is a directory; remove it (Docker created it because the file did not exist) and rebuild" >&2
  exit 1
fi

touch \
  "${HOME}/.claude.json"

# 秘密情報（env）を置くディレクトリは本人だけが読めるようにする
chmod 700 "${HOME}/.config/create-reso-world"

# コンテナの環境変数を、devcontainer.json の runArgs の --env-file が読むファイルに書く。mount と同じくコンテナの作成時に決まる
# - 写真フォルダがリンクのときだけ、その場所を RESOLOOP_SCREENSHOTS_DIR で渡す。リンクを作った・消した後は rebuild が要る
# - RESOLOOP_TEXTURE_TRANSFER=data を常に渡す。対応する ResoLoop は画像を画素で送り、Resonite がコンテナのパスを開く必要をなくす
#   （usaturn/resoloop#22）。公開版の対応確認と fork の導入方法は README を参照
env_file="$(dirname -- "${BASH_SOURCE[0]}")/resonite-screenshots.env"
: > "$env_file"
if [ -L "$screenshots" ]; then
  printf 'RESOLOOP_SCREENSHOTS_DIR=/home/vscode/.local/share/create-reso-world/resonite-screenshots\n' >> "$env_file"
fi
printf 'RESOLOOP_TEXTURE_TRANSFER=data\n' >> "$env_file"
