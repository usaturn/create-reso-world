#!/bin/bash
# copy-resonite-managed-data.bash が、既存の版のフォルダ・共有先の外へ書かず、照合できないコピーを成功と報告しないことを検査する（#326）。
# どれも壊れてもエラーにならず、利用者がコピーした DLL の上書き、範囲外への書き込み、壊れた DLL の採用が気付かれないまま残る（S）。
# HOME は `env HOME=...` のワンショットで一時ディレクトリに差し替え、偽の DLL は実行時に作る
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
script="$root/.devcontainer/copy-resonite-managed-data.bash"
tmp="$(mktemp -d)"
trap 'rm -rf -- "${tmp:?}"' EXIT
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
real_cp="$(command -v cp)"
version=2025.11.3.1234
share=.local/share/create-reso-world/resonite-managed-data

# 偽の Windows のコピー元。空白・括弧・日本語を含み、直下の DLL のほかに DLL 以外のファイルとサブフォルダの DLL がある
src="$tmp/win/Program Files (x86)/Steam/steamapps/common/リゾナイト テスト"
mkdir -p "$src/sub"
for n in FrooxEngine ProtoFlux.Core 'Elements Core'; do
  printf 'fake %s %s\n' "$n" "$(date +%s%N)" > "$src/$n.dll"
done
printf 'not a dll\n' > "$src/readme.txt"
printf 'nested\n' > "$src/sub/Nested.dll"

# ディレクトリの中身（名前・種類・リンク先・内容）の一覧。前後で比べて、変えていないことを確かめる
snapshot() {
  (cd "$1" && find . -printf '%p %y %l\n' | LC_ALL=C sort && find . -type f -exec sha256sum -- {} + | LC_ALL=C sort)
}
src_before="$(snapshot "$tmp/win")"

# run <HOME> [PATH の先頭に足すディレクトリ] -- <引数...>。出力を $out、終了コードを $rc に入れる
run() {
  local home="$1" prefix="$2"; shift 2
  rc=0
  out="$(env HOME="$home" PATH="${prefix:+$prefix:}$PATH" bash "$script" "$@" 2>&1)" || rc=$?
}
expect_refused() {
  [ "$rc" -ne 0 ] || fail "$1: exited 0
$out"
  case "$out" in *'copied and verified'*) fail "$1: reported success
$out" ;; esac
}

# 1. 正常例: 直下の *.dll だけが同じ内容でコピーされ、照合の一覧が残り、コピー元は変わらない
h="$tmp/h1"; mkdir "$h"
run "$h" '' --source "$src" --version "$version"
[ "$rc" -eq 0 ] || fail "normal copy failed ($rc):
$out"
case "$out" in *'copied and verified'*) ;; *) fail "normal copy did not report success:
$out" ;; esac
dest="$h/$share/$version"
actual="$(cd "$dest" && find . -mindepth 1 -printf '%P\n' | LC_ALL=C sort)"
[ "$actual" = "$(printf '%s\n' 'Elements Core.dll' FrooxEngine.dll ProtoFlux.Core.dll SHA256SUMS)" ] || fail "unexpected files in $dest:
$actual"
for n in FrooxEngine.dll ProtoFlux.Core.dll 'Elements Core.dll'; do
  cmp -s -- "$src/$n" "$dest/$n" || fail "content differs: $n"
done
(cd "$dest" && sha256sum --quiet -c SHA256SUMS) || fail "SHA256SUMS does not verify"
[ "$(snapshot "$tmp/win")" = "$src_before" ] || fail "source changed"

# 2. 既にある版のフォルダは変えずに拒否する
h="$tmp/h2"; mkdir -p "$h/$share/$version"
printf 'user data\n' > "$h/$share/$version/FrooxEngine.dll"
before="$(snapshot "$h")"
run "$h" '' --source "$src" --version "$version"
expect_refused "existing version folder"
[ "$(snapshot "$h")" = "$before" ] || fail "existing version folder was modified"

# 3. 版の文字列でパスを脱出しない。何も作らない
h="$tmp/h3"; mkdir "$h"
for v in '../escape' 'a/b' '..' '.' '' '-x' '.hidden'; do
  run "$h" '' --source "$src" --version "$v"
  expect_refused "version '$v'"
done
[ -z "$(find "$h" -mindepth 1 -print -quit)" ] || fail "invalid versions created files: $(find "$h" -mindepth 1)"

# 4. 共有先が symlink なら拒否し、リンク先に書かない
h="$tmp/h4"; mkdir -p "$h/${share%/*}" "$tmp/outside4"
ln -s "$tmp/outside4" "$h/$share"
run "$h" '' --source "$src" --version "$version"
expect_refused "shared folder symlink"
[ -z "$(find "$tmp/outside4" -mindepth 1 -print -quit)" ] || fail "wrote through the shared folder symlink"

# 5. 版のフォルダが壊れた symlink なら拒否し、リンク先を作らない
h="$tmp/h5"; mkdir -p "$h/$share" "$tmp/outside5"
ln -s "$tmp/outside5/target" "$h/$share/$version"
run "$h" '' --source "$src" --version "$version"
expect_refused "dangling version symlink"
[ ! -e "$tmp/outside5/target" ] || fail "created the symlink target"

# 6. コピーで内容が壊れる・1 件が欠ける・コピー中にコピー元が変わると、成功と報告せず、照合の一覧を置かず、
#    作った版のフォルダを消さずに残したパスを示す
fake_cp() {  # fake_cp <名前> <cp の後に実行する処理（$dst はコピー先、$src_file はコピー元）>
  mkdir -p "$tmp/bin-$1"
  # shellcheck disable=SC2016 # 偽の cp の本文。展開は偽の cp の実行時に行う
  printf '#!/bin/bash\nsrc_file="${@: -2:1}"; dst="${@: -1}"\n%s\n' "$2" > "$tmp/bin-$1/cp"
  chmod +x "$tmp/bin-$1/cp"
}
fake_cp corrupt "\"$real_cp\" \"\$@\" || exit; case \"\$dst\" in */FrooxEngine.dll) printf x >> \"\$dst\" ;; esac"
fake_cp missing "case \"\$dst\" in */ProtoFlux.Core.dll) exit 0 ;; esac; exec \"$real_cp\" \"\$@\""
fake_cp changed "\"$real_cp\" \"\$@\" || exit; case \"\$src_file\" in */FrooxEngine.dll) printf x >> \"\$src_file\" ;; esac"
for kind in corrupt missing changed; do
  [ "$kind" != changed ] || { cp -a -- "$tmp/win" "$tmp/win-changed"; }
  s="$src"; [ "$kind" != changed ] || s="$tmp/win-changed/${src#"$tmp/win/"}"
  h="$tmp/h6-$kind"; mkdir "$h"
  run "$h" "$tmp/bin-$kind" --source "$s" --version "$version"
  expect_refused "$kind copy"
  [ -d "$h/$share/$version" ] || fail "$kind copy: removed the version folder"
  [ ! -e "$h/$share/$version/SHA256SUMS" ] || fail "$kind copy: left SHA256SUMS in an unverified folder"
  case "$out" in *"$h/$share/$version"*) ;; *) fail "$kind copy: did not show the folder left in place:
$out" ;; esac
done

printf 'PASS: copy-resonite-managed-data refuses unsafe targets and unverified copies\n'
