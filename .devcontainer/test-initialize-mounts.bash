#!/bin/bash
# devcontainer.json の mounts・initialize.bash・postCreate の書き込み可能化が一致することを検査する。仕様 7.1・7.2・9.1 節
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
config="$root/.devcontainer/devcontainer.json"
init="$root/.devcontainer/initialize.bash"
installer="$root/.devcontainer/install_beforehand.bash"
tmp="$(mktemp -d)"
trap 'rm -rf -- "$tmp"' EXIT
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
# shellcheck source=mounts.bash
source "$root/.devcontainer/mounts.bash"

# 1. mounts のソースと initialize.bash が作るパスは同じ集合（仕様 7.2・9.1）
if ! out="$(mounts_compare "$config" "$init")"; then fail "mounts and initialize.bash differ:
$out"; fi

# 2. mounts は仕様 7.1 の表の 14 個（既存 13 ＋秘密情報）から、撤去した dsh の ~/.dsh を除いた 13 個
expected='.claude
.claude.json
.codex
.config/create-reso-world
.config/devin
.config/gcloud
.config/gh
.config/glab-cli
.cursor
.grok
.local/share/cursor-agent
.local/share/devin
.pi'
actual="$(mounts_from_devcontainer "$config" | cut -f1 | LC_ALL=C sort)"
[ "$actual" = "$expected" ] || fail "unexpected mounts:
$actual"

# 3. initialize.bash は一時 HOME にすべてのソースを作り、2 回目も成功する。~/.claude.json は通常ファイルで、
#    既存の中身を消さない。秘密情報のディレクトリは本人だけが読める
home="$tmp/home"
mkdir -p "$home"
HOME="$home" bash "$init"
printf '{"keep": true}\n' > "$home/.claude.json"
HOME="$home" bash "$init"
while IFS= read -r rel; do
  if [ "$rel" = .claude.json ]; then
    [ -f "$home/$rel" ] || fail "initialize.bash did not create the file ~/$rel"
  else
    [ -d "$home/$rel" ] || fail "initialize.bash did not create the directory ~/$rel"
  fi
done <<<"$expected"
[ "$(cat "$home/.claude.json")" = '{"keep": true}' ] || fail 'initialize.bash changed ~/.claude.json'
[ "$(stat -c %a "$home/.config/create-reso-world")" = 700 ] || fail '~/.config/create-reso-world must be mode 700'

# 3b. ~/.claude.json が (Docker が先に作った) ディレクトリだと initialize.bash はエラーで終了する
dirhome="$tmp/dirhome"
mkdir -p "$dirhome/.claude.json"
if out="$(HOME="$dirhome" bash "$init" 2>&1)"; then
  fail "initialize.bash succeeded although ~/.claude.json is a directory: $out"
fi
grep -qF '.claude.json is a directory' <<<"$out" || fail "initialize.bash did not report the directory conflict: $out"

# 4. postCreate はディレクトリの mount をすべて書き込み可能にする（ファイルの ~/.claude.json は除く）
writable="$(sed -n '/^step "Ensuring user-writable directories under ~"$/,/; do$/p' "$installer")"
while IFS= read -r rel; do
  [ "$rel" = .claude.json ] && continue
  grep -qF "\"\${HOME}/$rel\"" <<<"$writable" || fail "install_beforehand.bash does not make ~/$rel writable"
done <<<"$expected"

# 5. コンテナ名と、ユーザ単位のツールの PATH（仕様 7.2）
grep -qF '"name": "create-reso-world",' "$config" || fail 'devcontainer.json name must be create-reso-world'
grep -qF '"PATH": "${containerEnv:PATH}:/home/vscode/.local/bin:/home/vscode/bin:/home/vscode/.dotnet/tools"' "$config" \
  || fail 'remoteEnv.PATH must add ~/.local/bin, ~/bin and ~/.dotnet/tools'

# 6. 食い違いの検出: 片方にしか無いパスと、target が違う mount を報告して 1 を返す
cp "$config" "$tmp/extra.json"
sed -i 's|^\(\t\t"source=${localEnv:HOME}/.pi,target=/home/vscode/.pi,type=bind,consistency=cached",\)$|\1\n\t\t"source=${localEnv:HOME}/.extra,target=/home/vscode/.extra,type=bind,consistency=cached",|' "$tmp/extra.json"
if out="$(mounts_compare "$tmp/extra.json" "$init")"; then fail 'accepted a mount that initialize.bash does not create'; fi
grep -qxF 'mounts: ~/.extra is mounted by devcontainer.json but not created by initialize.bash' <<<"$out" || fail "unexpected report: $out"
sed 's|^  "${HOME}/.grok" \\$|  "${HOME}/.grok" \\\n  "${HOME}/.unmounted" \\|' "$init" > "$tmp/extra-init.bash"
if out="$(mounts_compare "$config" "$tmp/extra-init.bash")"; then fail 'accepted a path that is not mounted'; fi
grep -qxF 'mounts: ~/.unmounted is created by initialize.bash but not mounted by devcontainer.json' <<<"$out" || fail "unexpected report: $out"
sed 's|target=/home/vscode/.pi,|target=/root/.pi,|' "$config" > "$tmp/target.json"
if out="$(mounts_compare "$tmp/target.json" "$init")"; then fail 'accepted a mount with an unexpected target'; fi
grep -qxF 'mounts: ~/.pi is mounted at /root/.pi, expected /home/vscode/.pi' <<<"$out" || fail "unexpected report: $out"
# // でコメントアウトした mount と、パス以外も書いた行（chmod など）は数えない
sed 's|^\t\t"source=${localEnv:HOME}/.codex,|\t\t// "source=${localEnv:HOME}/.codex,|' "$config" > "$tmp/commented.json"
if out="$(mounts_compare "$tmp/commented.json" "$init")"; then fail 'counted a commented-out mount'; fi
grep -qxF 'mounts: ~/.codex is created by initialize.bash but not mounted by devcontainer.json' <<<"$out" || fail "unexpected report: $out"
printf 'chmod 700 "${HOME}/.chmod-only"\n' | cat "$init" - > "$tmp/chmod-init.bash"
mounts_compare "$config" "$tmp/chmod-init.bash" >/dev/null || fail 'counted a path on a chmod line'
if out="$(mounts_compare "$tmp/missing.json" "$init")"; then fail 'accepted a missing devcontainer.json'; fi

printf 'PASS: mounts, initialize.bash and postCreate agree\n'
