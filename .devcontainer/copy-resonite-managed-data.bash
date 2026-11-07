#!/bin/bash
# Windows の Resonite の managed DLL を、WSL 側の版ごとのフォルダへコピーして SHA-256 で照合する（#326）。
# コンテナの外の WSL で、利用者が初回と Resonite の更新時に手動で実行する。手順は .devcontainer/README.md の
# 「Resonite の managed data（ProtoFlux、任意）」。コピー元は find-resonite-managed-data.ps1 が表示する。
#
# 使い方: bash .devcontainer/copy-resonite-managed-data.bash --source <DLL のフォルダ（WSL のパス）> --version <Resonite の版>
#
# - コピー元の直下の *.dll だけを、~/.local/share/create-reso-world/resonite-managed-data/<版>/ へコピーする
# - 版のフォルダは新しく作る。既にあれば（リンクを含む）止まり、上書き・削除しない
# - コピー元で作った SHA-256 の一覧でコピー先を照合し、通ったときだけ一覧を SHA256SUMS として置き、成功を表示する
# - 失敗したら版のフォルダを残し、そのパスと再試行の前に確かめることを表示する。自動で消さない
# - 設定ファイル・シェルの設定・RESONITE_MANAGED_DATA_PATH は変えない
# 終了コード: 0 成功、1 失敗、2 引数の誤り
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: copy-resonite-managed-data.bash --source DIR --version VERSION

Copy the *.dll files directly under DIR (the folder that holds FrooxEngine.dll)
into ~/.local/share/create-reso-world/resonite-managed-data/VERSION/ and verify
them with SHA-256. Run it in WSL, outside the Dev Container.

  --source DIR       WSL path of the folder, e.g. "$(wslpath -u 'C:\...\Resonite')"
  --version VERSION  the Resonite version you confirmed (letters, digits, . _ + -)

An existing VERSION folder is never overwritten. On failure the folder is left
in place for you to inspect and remove.
EOF
}

die() { printf 'copy-resonite-managed-data: %s\n' "$1" >&2; exit "${2:-1}"; }

source_dir=''
version=''
have_source=false
have_version=false
while [ $# -gt 0 ]; do
  case "$1" in
    --source) [ $# -ge 2 ] || die 'missing value for --source' 2; source_dir="$2"; have_source=true; shift 2 ;;
    --version) [ $# -ge 2 ] || die 'missing value for --version' 2; version="$2"; have_version=true; shift 2 ;;
    -h | --help) usage; exit 0 ;;
    *) usage >&2; die "unknown argument: $1" 2 ;;
  esac
done
if ! "$have_source" || ! "$have_version"; then
  usage >&2
  die 'both --source and --version are required' 2
fi
# 版はフォルダの名前になる。/ や .. でのパスの脱出と、オプションに見える名前を拒否する
[[ "$version" =~ ^[0-9A-Za-z][0-9A-Za-z._+-]{0,63}$ ]] ||
  die "invalid version '$version': use 1-64 letters, digits, '.', '_', '+' or '-', starting with a letter or digit" 2

root="${HOME:?}/.local/share/create-reso-world/resonite-managed-data"
dest="$root/$version"
work="$(mktemp -d)"
dest_created=false
succeeded=false
on_exit() {
  rm -rf -- "${work:?}"
  if "$dest_created" && ! "$succeeded"; then
    printf 'copy-resonite-managed-data: NOT verified. The folder is left in place: %s\n' "$dest" >&2
    printf '  Before retrying: make sure Resonite is not running an update, check that --source is the folder\n' >&2
    printf '  that holds FrooxEngine.dll, then inspect and remove the folder yourself (rm -r -- %q).\n' "$dest" >&2
  fi
}
trap on_exit EXIT

[ -d "$source_dir" ] || die "source is not a folder: $source_dir"
if [ -L "$source_dir/FrooxEngine.dll" ] || [ ! -f "$source_dir/FrooxEngine.dll" ]; then
  die "FrooxEngine.dll is not a regular file directly under the source: $source_dir"
fi

# 共有先は initialize.bash と同じく実ディレクトリに限る（リンクだと、リンク先へ書き込む）
if [ -L "$root" ] || { [ -e "$root" ] && [ ! -d "$root" ]; }; then
  die "$root must be a real directory, not a link or a file"
fi
mkdir -p -- "$root" || die "cannot create $root"
real_root="$(realpath -e -- "$root")" || die "cannot resolve $root"
real_src="$(realpath -e -- "$source_dir")" || die "cannot resolve $source_dir"
case "$real_src/" in
  "$real_root"/*) die "the source must not be inside $root" ;;
esac

# コピー元の直下の *.dll。通常のファイルでないもの（リンク・フォルダ）や、照合の一覧に書けない名前があれば止まる
names=()
while IFS= read -r -d '' path; do
  name="${path##*/}"
  [ -f "$path" ] && [ ! -L "$path" ] || die "not a regular file: $path"
  case "$name" in *$'\n'* | *\\*) die "unsupported file name: $path" ;; esac
  names+=("$name")
done < <(find "$real_src" -mindepth 1 -maxdepth 1 -name '*.dll' -print0 | LC_ALL=C sort -z)
[ "${#names[@]}" -gt 0 ] || die "no *.dll directly under $real_src"

# コピー元の直下の *.dll の名前の一覧。コピーの後に作り直して、追加・削除を見つける
list_names() { find "$real_src" -mindepth 1 -maxdepth 1 -name '*.dll' -printf '%f\0' | LC_ALL=C sort -z; }
printf '%s\0' "${names[@]}" > "$work/names-before"

list_hashes() { (cd -- "$real_src" && sha256sum -- "${names[@]}"); }
list_hashes > "$work/before" || die "cannot read the DLLs in $real_src"

# -p を付けない mkdir は、既にある（リンク・壊れたリンクを含む）と失敗する。既存の版へは書かない
mkdir -- "$dest" 2> "$work/mkdir.err" ||
  die "cannot create $dest ($(cat "$work/mkdir.err")). Existing version folders are never overwritten; use a new version or remove it yourself"
dest_created=true
if [ -L "$dest" ] || [ ! -d "$dest" ] || [ "$(realpath -e -- "$dest")" != "$real_root/$version" ]; then
  die "$dest is not a new folder directly under $real_root"
fi

for name in "${names[@]}"; do
  cp -p -- "$real_src/$name" "$dest/$name" || die "copy failed: $name"
done

# コピーの間にコピー元の DLL の名前の集合と内容が変わっていないこと（Resonite の更新中など）
list_names > "$work/names-after" || die "cannot list the DLLs in $real_src after copying"
cmp -s -- "$work/names-before" "$work/names-after" ||
  die 'DLLs were added to or removed from the source while copying (is Resonite updating?)'
list_hashes > "$work/after" || die "cannot read the DLLs in $real_src after copying"
cmp -s -- "$work/before" "$work/after" || die 'the source changed while copying (is Resonite updating?)'
# コピー先の内容がコピー元の一覧と一致し、一覧に無いファイルも欠けたファイルも無いこと
(cd -- "$dest" && sha256sum --quiet --strict -c -- "$work/before") || die "hash check failed in $dest"
expected="$(printf '%s\n' "${names[@]}")"
actual="$(cd -- "$dest" && find . -mindepth 1 -maxdepth 1 -printf '%P\n' | LC_ALL=C sort)"
[ "$actual" = "$expected" ] || die "the files in $dest do not match the source list"

cat -- "$work/before" > "$dest/SHA256SUMS" || die "cannot write $dest/SHA256SUMS"
succeeded=true
container_path="/home/vscode/.local/share/create-reso-world/resonite-managed-data/$version"
printf 'copied and verified: %d DLL file(s) -> %s\n' "${#names[@]}" "$dest"
printf 'In the Dev Container, point flux-sdk at: %s\n' "$container_path"
printf '  e.g. resoloop doctor --library-path %q, or RESONITE_MANAGED_DATA_PATH=%q\n' "$container_path" "$container_path"
printf 'This only checks the copy. Confirm the SDK with resoloop doctor and flux check/build (see .devcontainer/README.md).\n'
