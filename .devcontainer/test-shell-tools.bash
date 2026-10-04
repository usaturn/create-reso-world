#!/bin/bash
# zshrc.txt の未導入ツールの保護・秘密情報の読み込みと、starship.toml の custom.uv_python を検査する。仕様 7.1・7.2 節
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
# stub NAME: 呼び出しを $tmp/calls に記録するだけのコマンドを置く
stub() {
  printf '#!/bin/bash\nprintf "%%s\\n" "%s $*" >> "$TMP_LOG"\n' "$1" > "$tmp/bin/$1"
  chmod +x "$tmp/bin/$1"
}
mkdir -p "$tmp/home" "$tmp/bin" "$tmp/sys"
for c in cat chmod date dirname ls mkdir mv rm rmdir touch; do   # compinit などが使う基本コマンド
  ln -s "$(command -v "$c")" "$tmp/sys/$c"
done
printf '#!/bin/bash\n' > "$tmp/bin/starship"   # zshrc.txt の eval "$(starship init zsh)" は何もしない
chmod +x "$tmp/bin/starship"
: > "$tmp/calls"

zsh -n "$zshrc"

# 1. どのツールも無くても読み込みは成功し、command not found を出さない
run_zsh 'true' || fail "sourcing zshrc.txt failed: $(cat "$tmp/err")"
if grep -F 'command not found' "$tmp/err"; then fail 'zshrc.txt ran a missing command while loading'; fi

# 2. update() は無いツールを飛ばして 0 を返し、飛ばした項目を表示する
run_zsh 'update' || fail "update failed without any tool: $(cat "$tmp/err")"
for tool in claude npm pi agent devin; do
  grep -qF "update: $tool not found; skipped" "$tmp/err" || fail "update did not report the missing $tool"
done
# 撤去した Grok Build（grok）は update() の対象にしない
if grep -qF 'update: grok' "$tmp/err"; then fail 'update() still updates grok'; fi
if grep -F 'command not found' "$tmp/err"; then fail 'update ran a missing command'; fi

# 3. update() はあるツールだけを更新する
stub claude && stub npm && stub pi
: > "$tmp/calls"
run_zsh 'update' || fail "update failed: $(cat "$tmp/err")"
expected='claude update
npm install -g @openai/codex@latest
pi update
pi update --extensions'
[ "$(cat "$tmp/calls")" = "$expected" ] || fail "update ran: $(cat "$tmp/calls")"
grep -qF 'update: devin not found; skipped: devin plugins update superpowers' "$tmp/err" || fail 'update did not skip devin'
rm "$tmp/bin/claude" "$tmp/bin/npm" "$tmp/bin/pi"

# 4. cod・genv・buni は、ツールが無ければ理由を示して 127 を返す。buni は node_modules を消さない
mkdir -p "$tmp/home/work/node_modules"
for call in 'cod:codex' 'genv:gcloud' 'buni:bun'; do
  fn="${call%%:*}" tool="${call#*:}" code=0
  run_zsh "cd \"\$HOME/work\" && $fn" || code=$?
  [ "$code" -eq 127 ] || fail "$fn returned $code without $tool"
  grep -qxF "$fn: $tool not found" "$tmp/err" || fail "$fn did not report the missing $tool: $(cat "$tmp/err")"
done
[ -d "$tmp/home/work/node_modules" ] || fail 'buni removed node_modules although bun is missing'
stub gcloud
code=0
run_zsh 'genv' || code=$?
[ "$code" -eq 127 ] && grep -qxF 'genv: fzf not found' "$tmp/err" || fail 'genv must also require fzf'
rm "$tmp/bin/gcloud"

# 5. bun の場所は $HOME 基準で、/home/vscode を書かない
run_zsh 'print -r -- "$BUN_INSTALL"' || fail 'BUN_INSTALL'
[ "$(cat "$tmp/out")" = "$tmp/home/.bun" ] || fail "BUN_INSTALL is $(cat "$tmp/out")"
if grep -nF '/home/vscode' "$zshrc"; then fail 'zshrc.txt must not hard-code /home/vscode'; fi

# 6. 秘密情報の env はあるときだけ読み込み、書いた変数を export する
mkdir -p "$tmp/home/.config/create-reso-world"
printf 'EXAMPLE_TOKEN=secret-value\n' > "$tmp/home/.config/create-reso-world/env"
run_zsh '[[ ${(t)EXAMPLE_TOKEN} == *export* ]] && print -r -- "$EXAMPLE_TOKEN"' || fail "the secrets env was not exported: $(cat "$tmp/err")"
[ "$(cat "$tmp/out")" = secret-value ] || fail 'EXAMPLE_TOKEN value'
rm "$tmp/home/.config/create-reso-world/env"
run_zsh 'true' || fail 'loading without the secrets env failed'
[ ! -s "$tmp/err" ] || fail "loading without the secrets env printed: $(cat "$tmp/err")"

# 7. starship の custom.uv_python は、カレントディレクトリから上へ最寄りの .venv/pyvenv.cfg を探す
uv run --no-project python - "$root/.devcontainer/starship.toml" "$tmp" <<'PY'
import pathlib
import sys
import tomllib

module = tomllib.load(open(sys.argv[1], "rb"))["custom"]["uv_python"]
out = pathlib.Path(sys.argv[2])
(out / "uv_python_command.sh").write_text(module["command"] + "\n")
(out / "uv_python_when.sh").write_text(module["when"] + "\n")
PY
mkdir -p "$tmp/ws/proj/.venv" "$tmp/ws/proj/sub/dir" "$tmp/ws/other"
printf 'home = /usr/bin\nversion_info = 3.12.7\n' > "$tmp/ws/proj/.venv/pyvenv.cfg"
for dir in "$tmp/ws/proj" "$tmp/ws/proj/sub/dir"; do
  (cd "$dir" && bash --noprofile --norc "$tmp/uv_python_when.sh") || fail "uv_python hidden in $dir"
  [ "$(cd "$dir" && bash --noprofile --norc "$tmp/uv_python_command.sh")" = 3.12.7 ] || fail "uv_python version in $dir"
done
if (cd "$tmp/ws/other" && bash --noprofile --norc "$tmp/uv_python_when.sh"); then fail 'uv_python shown without a .venv'; fi

printf 'PASS: shell setup guards missing tools and finds the nearest .venv\n'
