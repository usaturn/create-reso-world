#!/bin/bash
# zshrc.txt の buni が bun の無いとき node_modules を消さないことと、固定の HOME を書いていないことを検査する。仕様 7.1・7.2 節
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
zshrc="$root/.devcontainer/zshrc.txt"
tmp="$(mktemp -d)"
trap 'rm -rf -- "$tmp"' EXIT
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }

# 一時 HOME と、スタブ（$tmp/bin）と基本コマンド（$tmp/sys）だけの PATH で zshrc.txt を読み込み、$1 の zsh コードを
# 実行する。標準出力は $tmp/out、標準エラーは $tmp/err に残し、終了コードを返す。スタブを置かなかったツールは
# 「未導入」になる（非 TTY なので herdrstart は何もしない）
run_zsh() {
  local code=0
  env -i HOME="$tmp/home" PATH="$tmp/bin:$tmp/sys" TMP_LOG="$tmp/calls" ZSHRC="$zshrc" \
    /usr/bin/zsh -f -c 'source "$ZSHRC"; '"$1" </dev/null >"$tmp/out" 2>"$tmp/err" || code=$?
  return "$code"
}
mkdir -p "$tmp/home" "$tmp/bin" "$tmp/sys"
for c in cat chmod date dirname ls mkdir mv rm rmdir touch; do   # compinit などが使う基本コマンド
  ln -s "$(command -v "$c")" "$tmp/sys/$c"
done
printf '#!/bin/bash\n' > "$tmp/bin/starship"   # zshrc.txt の eval "$(starship init zsh)" は何もしない
chmod +x "$tmp/bin/starship"

# buni は bun が無いとき node_modules を消さない。bun が無いのに rm だけが走ると、依存を再導入できずに失われる
mkdir -p "$tmp/home/work/node_modules"
code=0
run_zsh 'cd "$HOME/work" && buni' || code=$?
[ "$code" -eq 127 ] || fail "buni returned $code without bun"
[ -d "$tmp/home/work/node_modules" ] || fail 'buni removed node_modules although bun is missing'

# zshrc.txt に /home/vscode を書かない。固定した HOME を書くと、一時 HOME で読み込むテストや別の利用者で実行したときに
# 実際の /home/vscode を操作する（エラーにならない）ため、このパスは固定値で禁止する（F∩S）
if grep -nF '/home/vscode' "$zshrc"; then fail 'zshrc.txt must not hard-code /home/vscode'; fi

printf 'PASS: buni keeps node_modules without bun and zshrc.txt has no hard-coded HOME\n'
