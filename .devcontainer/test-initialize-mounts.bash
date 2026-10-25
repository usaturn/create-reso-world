#!/bin/bash
# devcontainer.json の mounts と initialize.bash が一致することと、initialize.bash が利用者のファイルを壊さないことを検査する。仕様 7.1・7.2・9.1 節
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
config="$root/.devcontainer/devcontainer.json"
init="$root/.devcontainer/initialize.bash"
tmp="$(mktemp -d)"
trap 'rm -rf -- "$tmp"' EXIT
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
# shellcheck source=mounts.bash
source "$root/.devcontainer/mounts.bash"

# 1. mounts のソースと initialize.bash が作るパスは同じ集合（仕様 7.2・9.1）。initialize.bash が作らない mount の対象は
#    Docker が root 所有で作り、以降の書き込みが権限で失敗する
if ! out="$(mounts_compare "$config" "$init")"; then fail "mounts and initialize.bash differ:
$out"; fi

# 2. mounts は認証情報・設定などの永続領域と、任意の Resonite の写真フォルダ（読み取り専用）の 15 個。
#    mount の増減はホストの永続領域と秘密情報の露出に関わるため、固定値で守る。1 の相互比較だけでは、
#    devcontainer.json と initialize.bash を同時に誤って変えたときに検出できない（Issue #36 C1）
expected='.claude
.claude.json
.codex
.config/create-reso-world
.config/cursor
.config/devin
.config/gcloud
.config/gh
.config/glab-cli
.cursor
.gemini/antigravity-cli
.local/share/create-reso-world/resonite-screenshots
.local/share/cursor-agent
.local/share/devin
.pi'
actual="$(mounts_from_devcontainer "$config" | cut -f1 | LC_ALL=C sort)"
[ "$actual" = "$expected" ] || fail "unexpected mounts:
$actual"

# initialize.bash は自分の隣に resonite-screenshots.env を書くので、リポジトリの .devcontainer を書き換えないようにコピーを実行する
mkdir -p "$tmp/devcontainer"
cp "$init" "$tmp/devcontainer/initialize.bash"
run_init="$tmp/devcontainer/initialize.bash"

# 3. initialize.bash は一時 HOME にすべてのソースを作り、2 回目も成功する。~/.claude.json は通常ファイルで、
#    既存の中身を消さない。秘密情報のディレクトリは本人だけが読める
home="$tmp/home"
mkdir -p "$home"
HOME="$home" bash "$run_init"
printf '{"keep": true}\n' > "$home/.claude.json"
HOME="$home" bash "$run_init"
while IFS= read -r rel; do
  if [ "$rel" = .claude.json ]; then
    [ -f "$home/$rel" ] || fail "initialize.bash did not create the file ~/$rel"
  else
    [ -d "$home/$rel" ] || fail "initialize.bash did not create the directory ~/$rel"
  fi
done <<<"$expected"
[ "$(cat "$home/.claude.json")" = '{"keep": true}' ] || fail 'initialize.bash changed ~/.claude.json'
[ "$(stat -c %a "$home/.config/create-reso-world")" = 700 ] || fail '~/.config/create-reso-world must be mode 700'

printf 'PASS: mounts agree with initialize.bash, which keeps ~/.claude.json\n'
