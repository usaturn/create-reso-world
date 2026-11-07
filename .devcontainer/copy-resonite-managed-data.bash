#!/bin/bash
# Windows の Resonite の managed DLL を、WSL 側の版ごとのフォルダへコピーして SHA-256 で照合する（#326）。
# コンテナの外の WSL で、利用者が初回と Resonite の更新時に手動で実行する。手順は .devcontainer/README.md の
# 「Resonite の managed data（ProtoFlux、任意）」。コピー元は find-resonite-managed-data.ps1 が表示する。
#
# 使い方: bash .devcontainer/copy-resonite-managed-data.bash --source <DLL のフォルダ（WSL のパス）> --version <Resonite の版>
#         bash .devcontainer/copy-resonite-managed-data.bash --relink-latest --version <コピー済みの版>
#
# - コピー元の直下の *.dll だけを、~/.local/share/create-reso-world/resonite-managed-data/<版>/ へコピーする
# - 版のフォルダは新しく作る。既にあれば（リンクを含む）止まり、上書き・削除しない
# - コピー元で作った SHA-256 の一覧でコピー先を照合し、通ったときだけ一覧を SHA256SUMS として置き、成功を表示する
# - 失敗したら版のフォルダを残し、そのパスと再試行の前に確かめることを表示する。自動で消さない
# - 照合が通った後、その版が照合済みの版（SHA256SUMS のある版のフォルダ）のうち sort -V で最も新しいときだけ、
#   共有先の直下の latest を相対リンク（latest -> <版>）に付け替える（#331）。一時名のリンクを mv -T で置き換えるので、
#   latest は常に前の版か新しい版のどちらかを指す。latest がリンク以外なら上書きせずに止まる。版の名前に latest は使えない
# - --relink-latest は、既にコピーした版のフォルダを SHA256SUMS で照合し直し、通ったら同じ規則で latest だけを付け替える
# - 設定ファイル・シェルの設定・RESONITE_MANAGED_DATA_PATH は変えない（コンテナの devcontainer.json が latest を指す）
# 終了コード: 0 成功（照合は通ったが、より新しい版があって latest を変えなかったときを含む）、1 失敗、2 引数の誤り
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: copy-resonite-managed-data.bash --source DIR --version VERSION
       copy-resonite-managed-data.bash --relink-latest --version VERSION

Copy the *.dll files directly under DIR (the folder that holds FrooxEngine.dll)
into ~/.local/share/create-reso-world/resonite-managed-data/VERSION/ and verify
them with SHA-256. Run it in WSL, outside the Dev Container.

  --source DIR       WSL path of the folder, e.g. "$(wslpath -u 'C:\...\Resonite')"
  --version VERSION  the Resonite version you confirmed (letters, digits, . _ + -;
                     'latest' is reserved)
  --relink-latest    do not copy; re-verify the existing VERSION folder with its
                     SHA256SUMS and only update the latest link

After a verified copy, the 'latest' link in the shared folder is pointed at
VERSION if it is the newest verified version (sort -V). Older versions never
move it back. An existing VERSION folder is never overwritten. On failure the
folder is left in place for you to inspect and remove.
EOF
}

die() { printf 'copy-resonite-managed-data: %s\n' "$1" >&2; exit "${2:-1}"; }

source_dir=''
version=''
have_source=false
have_version=false
relink=false
while [ $# -gt 0 ]; do
  case "$1" in
    --source) [ $# -ge 2 ] || die 'missing value for --source' 2; source_dir="$2"; have_source=true; shift 2 ;;
    --version) [ $# -ge 2 ] || die 'missing value for --version' 2; version="$2"; have_version=true; shift 2 ;;
    --relink-latest) relink=true; shift ;;
    -h | --help) usage; exit 0 ;;
    *) usage >&2; die "unknown argument: $1" 2 ;;
  esac
done
if "$relink"; then
  if "$have_source" || ! "$have_version"; then
    usage >&2
    die '--relink-latest takes --version and no --source' 2
  fi
elif ! "$have_source" || ! "$have_version"; then
  usage >&2
  die 'both --source and --version are required' 2
fi
# 版はフォルダの名前になる。/ や .. でのパスの脱出と、オプションに見える名前を拒否する
[[ "$version" =~ ^[0-9A-Za-z][0-9A-Za-z._+-]{0,63}$ ]] ||
  die "invalid version '$version': use 1-64 letters, digits, '.', '_', '+' or '-', starting with a letter or digit" 2
# latest は最新の版へのリンクの名前なので、版の名前にしない
[ "${version,,}" != latest ] || die "invalid version '$version': 'latest' is reserved for the link to the newest verified version" 2

root="${HOME:?}/.local/share/create-reso-world/resonite-managed-data"
dest="$root/$version"
latest="$root/latest"
container_root=/home/vscode/.local/share/create-reso-world/resonite-managed-data
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

latest_not_link() { printf '%s is not a symlink, so it was not replaced. Remove or rename it yourself (latest is reserved for the link)' "$latest"; }
# latest が無いか、リンク（壊れたリンクを含む）なら付け替えてよい。実ディレクトリ・ファイルは利用者のものとして触らない
latest_replaceable() { [ -L "$latest" ] || [ ! -e "$latest" ]; }
# 共有先の直下の照合済みの版（リンクでない版のフォルダに、リンクでない SHA256SUMS がある）
is_verified() {
  [[ "$1" =~ ^[0-9A-Za-z][0-9A-Za-z._+-]{0,63}$ ]] && [ "${1,,}" != latest ] &&
    [ -d "$root/$1" ] && [ ! -L "$root/$1" ] && [ -f "$root/$1/SHA256SUMS" ] && [ ! -L "$root/$1/SHA256SUMS" ]
}
# 今の版と照合済みの版のうち、sort -V で最も新しい名前
newest_verified() {
  local p
  {
    printf '%s\n' "$version"
    for p in "$root"/*; do
      if is_verified "${p##*/}"; then printf '%s\n' "${p##*/}"; fi
    done
  } | LC_ALL=C sort -V | tail -n 1
}
# 今の版が最も新しい照合済みの版なら、一時名のリンクを mv -T で latest に置き換える（rename なので途中の状態が無い）
update_latest() {
  local newest tmp_link
  newest="$(newest_verified)" || die "cannot list the versions in $root; latest was not changed"
  if [ "$newest" != "$version" ]; then
    printf 'latest was not changed: %s is newer than %s (latest -> %s)\n' "$newest" "$version" "$(readlink -- "$latest" || printf '<none>')"
    return 0
  fi
  latest_replaceable || die "the copy of $version is verified, but $(latest_not_link)"
  tmp_link="$root/.latest.$$.$RANDOM"
  ln -s -- "$version" "$tmp_link" || die "cannot create $tmp_link; latest was not changed"
  if ! mv -T -- "$tmp_link" "$latest"; then
    rm -f -- "${tmp_link:?}"
    die "cannot replace $latest; it was not changed"
  fi
  printf 'latest -> %s\n' "$version"
}
show_paths() {
  printf 'In the Dev Container, RESONITE_MANAGED_DATA_PATH=%s points at the newest verified version.\n' "$container_root/latest"
  printf '  To use this version only: resoloop doctor --library-path %q\n' "$container_root/$version"
  printf 'This only checks the copy. Confirm the SDK with resoloop doctor and flux check/build (see .devcontainer/README.md).\n'
}

# 既にコピーした版を照合し直して、latest だけを付け替える。版のフォルダの中身は変えない
if "$relink"; then
  if [ -L "$root" ] || [ ! -d "$root" ]; then
    die "$root must be a real directory, not a link or a file"
  fi
  if [ -L "$dest" ] || [ ! -d "$dest" ]; then
    die "$dest is not a version folder"
  fi
  if [ -L "$dest/SHA256SUMS" ] || [ ! -f "$dest/SHA256SUMS" ]; then
    die "$dest has no SHA256SUMS, so it was never verified; copy the version again"
  fi
  latest_replaceable || die "$(latest_not_link)"
  (cd -- "$dest" && sha256sum --quiet --strict -c -- SHA256SUMS) || die "hash check failed in $dest; latest was not changed"
  # 一覧の DLL と SHA256SUMS のほかにファイルが無く、どれもリンクでない通常のファイルであること
  [ -z "$(find "$dest" -mindepth 1 -maxdepth 1 ! -type f -print -quit)" ] || die "$dest has entries that are not regular files; latest was not changed"
  expected="$({ sed -E 's/^[0-9a-f]{64} [ *]//' -- "$dest/SHA256SUMS"; printf '%s\n' SHA256SUMS; } | LC_ALL=C sort)"
  actual="$(cd -- "$dest" && find . -mindepth 1 -maxdepth 1 -printf '%P\n' | LC_ALL=C sort)"
  [ "$actual" = "$expected" ] || die "the files in $dest do not match its SHA256SUMS; latest was not changed"
  update_latest
  printf 'verified again: %s\n' "$dest"
  show_paths
  exit 0
fi

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

# latest を付け替えられないなら、版のフォルダを作る前に止まる（何も変えない）
latest_replaceable || die "$(latest_not_link)"

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
# 照合が通った後にだけ latest を付け替える。失敗したら、照合済みのコピーを残して終了コード 1 で止まる
update_latest
printf 'copied and verified: %d DLL file(s) -> %s\n' "${#names[@]}" "$dest"
show_paths
