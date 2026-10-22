#!/bin/bash
# scripts/resoloop-fork.sh が他人の checkout・汚れた作業ツリー・分岐した main を壊さないことを、
# ローカルの bare リポジトリとモックの dotnet で検査する（ネットワークと実 SDK を使わない。守りごとに代表の 1 件）
# 仕様: docs/superpowers/specs/2026-10-06-issue-41-resoloop-latest-without-lock-design.md D-5〜D-10
set -euo pipefail
# 外から渡された GIT_* を除く。linked worktree の git rebase --exec は GIT_DIR を export するので、残すと
# 直接実行したときに一時リポジトリの git init・git -C が、そのリポジトリの設定・index・ブランチを書き換える（#200）
while IFS= read -r name; do unset "$name"; done < <(compgen -e -X '!GIT_*')
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# ユーザの git 設定から隔離する（システム・グローバル設定と core.excludesFile を外す）。グローバル設定の
# safe.directory も外れるので、このリポジトリだけは所有者が違っても読めるようにしておく
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null
export GIT_CONFIG_COUNT=2 GIT_CONFIG_KEY_0=core.excludesFile GIT_CONFIG_VALUE_0=/dev/null \
  GIT_CONFIG_KEY_1=safe.directory GIT_CONFIG_VALUE_1="$repo_root"
export GIT_AUTHOR_NAME=test GIT_AUTHOR_EMAIL=test@example.com GIT_COMMITTER_NAME=test GIT_COMMITTER_EMAIL=test@example.com
script="$repo_root/scripts/resoloop-fork.sh"
tmp="$(cd "$(mktemp -d)" && pwd -P)"
trap 'rm -rf -- "${tmp:?}"' EXIT
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }

# 上流（upstream.git）と fork（origin.git）。checkout には global.json と、<Version> を持つ csproj がある。
# fork には修正ブランチ fix/x がある
git init -q -b main "$tmp/seed"
mkdir -p "$tmp/seed/src/RLoop.Cli"
printf '{ "sdk": { "version": "10.0.201", "rollForward": "latestPatch" } }\n' > "$tmp/seed/global.json"
printf '<Project>\n  <PropertyGroup>\n    <Version>1.2.3-preview.4</Version>\n  </PropertyGroup>\n</Project>\n' \
  > "$tmp/seed/src/RLoop.Cli/RLoop.Cli.csproj"
printf 'v1\n' > "$tmp/seed/file.txt"
git -C "$tmp/seed" add . && git -C "$tmp/seed" commit -q -m v1
git clone -q --bare "$tmp/seed" "$tmp/upstream.git"
git clone -q --bare "$tmp/seed" "$tmp/origin.git"
git -C "$tmp/seed" checkout -q -b fix/x
printf 'fix\n' >> "$tmp/seed/file.txt"
git -C "$tmp/seed" commit -q -am fix
git -C "$tmp/seed" push -q "$tmp/origin.git" fix/x
fix_commit="$(git -C "$tmp/seed" rev-parse HEAD)"
export RESOLOOP_ORIGIN_URL="$tmp/origin.git" RESOLOOP_UPSTREAM_URL="$tmp/upstream.git" RESOLOOP_CHECKOUT="$tmp/work/external/resoloop"
co="$RESOLOOP_CHECKOUT"

# 仕様 D-5 の版: csproj の <Version> に .fork を付け、コミットの日付（UTC）と短い SHA を続ける
fork_version_of() {
  printf '%s.%s.g%s\n' 1.2.3-preview.4.fork "$(TZ=UTC git -C "$tmp/seed" log -1 --format=%cd --date=format-local:%Y%m%d "$1")" \
    "$(git -C "$tmp/seed" rev-parse --short=7 "$1")"
}

# モックの dotnet: build・test は成功し、pack は nupkg を作る。tool update は MOCK_STATE に版を書き、
# ~/.dotnet/tools/resoloop に版（MOCK_SHIM_VERSION があればその値）を返す shim を置く
mkdir -p "$tmp/mockbin" "$tmp/home/.dotnet/tools"
cat > "$tmp/mockbin/dotnet" <<'EOF'
#!/bin/bash
arg_after() {  # $1=オプション名。その次の引数を出力する
  local want="$1"
  shift
  while [ $# -gt 0 ]; do
    if [ "$1" = "$want" ]; then printf '%s\n' "$2"; return; fi
    shift
  done
}
case "$1" in
  --version) echo 10.0.201 ;;
  build | test) ;;
  pack)
    out="$(arg_after -o "$@")" ver=""
    for a in "$@"; do case "$a" in -p:PackageVersion=*) ver="${a#-p:PackageVersion=}" ;; esac; done
    mkdir -p "$out" && : > "$out/ResoLoop.$ver.nupkg" ;;
  tool)
    case "$2" in
      list)
        printf 'Package Id      Version      Commands\n'
        [ ! -s "$MOCK_STATE" ] || printf 'resoloop      %s      resoloop\n' "$(cat "$MOCK_STATE")" ;;
      update)
        ver="$(arg_after --version "$@")"
        printf '%s\n' "$ver" > "$MOCK_STATE"
        printf '#!/bin/bash\nprintf "%%s\\n" %q\n' "${MOCK_SHIM_VERSION:-$ver}" > "$HOME/.dotnet/tools/resoloop"
        chmod +x "$HOME/.dotnet/tools/resoloop" ;;
      *) exit 64 ;;
    esac ;;
  *) exit 64 ;;
esac
EOF
chmod +x "$tmp/mockbin/dotnet"
export HOME="$tmp/home" PATH="$tmp/mockbin:$PATH" MOCK_STATE="$tmp/installed"
: > "$MOCK_STATE"

expect_exit() {  # $1=期待する終了コード、$2=出力に含まれるべき文字列、残り=resoloop-fork.sh の引数
  local want="$1" needle="$2" got=0
  shift 2
  bash "$script" "$@" > "$tmp/out.txt" 2>&1 || got=$?
  [ "$got" -eq "$want" ] || { cat "$tmp/out.txt" >&2; fail "expected exit $want, got $got: $*"; }
  grep -qF -- "$needle" "$tmp/out.txt" || { cat "$tmp/out.txt" >&2; fail "expected output '$needle': $*"; }
}

# 1. clone は origin と upstream を持つ checkout を作り、2 回目は remote を確かめるだけ
expect_exit 0 "cloned: $co" clone
[ "$(git -C "$co" remote get-url origin)" = "$tmp/origin.git" ] || fail 'origin url'
[ "$(git -C "$co" remote get-url upstream)" = "$tmp/upstream.git" ] || fail 'upstream url'
expect_exit 0 'is already cloned' clone

# 2. 他の remote を持つ checkout は、clone も checkout も sync も受け付けず、何も変えない
git -C "$co" remote set-url origin "$tmp/upstream.git"
expect_exit 1 "remote origin is $tmp/upstream.git (expected $tmp/origin.git)" clone
[ "$(git -C "$co" remote get-url origin)" = "$tmp/upstream.git" ] || fail 'clone changed a mismatching remote'
git -C "$co" remote set-url origin "$tmp/origin.git"
git -C "$co" remote set-url upstream "$tmp/origin.git"
origin_before="$(git -C "$tmp/origin.git" rev-parse main)"
expect_exit 1 'has unexpected remotes' sync
[ "$(git -C "$tmp/origin.git" rev-parse main)" = "$origin_before" ] || fail 'sync pushed despite mismatching remotes'
git -C "$co" remote set-url upstream "$tmp/upstream.git"

# 3. 外側のリポジトリの中にある、git の checkout でないディレクトリは、外側の remote を見て clone 済みとみなさない
git init -q "$tmp/outer" && mkdir -p "$tmp/outer/external/resoloop"
git -C "$tmp/outer" remote add origin "$tmp/origin.git"
RESOLOOP_CHECKOUT="$tmp/outer/external/resoloop" expect_exit 1 'is not a git checkout of its own' clone

# 4. checkout は origin のブランチを detached で取り出す。origin のブランチと同じ名前のローカルのブランチより、
#    origin のブランチを使う。origin に後から push されたブランチの先端も fetch してから取り出す
expect_exit 0 "checked out: $co at $fix_commit (origin/fix/x, detached)" checkout fix/x
git -C "$co" branch fix/x refs/remotes/origin/main
expect_exit 0 'is already at' checkout fix/x
git -C "$co" branch -D -q fix/x
git -C "$tmp/seed" checkout -q fix/x
printf 'fix2\n' >> "$tmp/seed/file.txt"
git -C "$tmp/seed" commit -q -am fix2
git -C "$tmp/seed" push -q "$tmp/origin.git" fix/x
fix2="$(git -C "$tmp/seed" rev-parse HEAD)"
expect_exit 0 "checked out: $co at $fix2 (origin/fix/x, detached)" checkout fix/x
# origin/HEAD（origin の既定のブランチを指す symbolic ref）は origin のブランチとして扱わない。push していないコミットを
# 持つローカルのブランチで checkout HEAD を実行しても、今のコミットのまま detached になる
git -C "$co" switch -q -c local-only
printf 'local only\n' >> "$co/file.txt" && git -C "$co" commit -q -am 'local only'
local_commit="$(git -C "$co" rev-parse HEAD)"
expect_exit 0 "checked out: $co at $local_commit (HEAD, detached)" checkout HEAD
[ "$(git -C "$co" rev-parse HEAD)" = "$local_commit" ] || fail 'checkout HEAD moved away from the current commit'
git -C "$co" branch -D -q local-only

# 5. 追跡ファイルに未コミットの変更があれば 1 で、HEAD を動かさない。未追跡ファイルは妨げない
git -C "$co" checkout -q main
printf 'local edit\n' >> "$co/file.txt"
expect_exit 1 'has uncommitted changes to tracked files' checkout fix/x
[ "$(git -C "$co" symbolic-ref --short HEAD)" = main ] || fail 'checkout moved HEAD despite local changes'
expect_exit 1 'has uncommitted changes to tracked files' build
git -C "$co" checkout -q -- file.txt
printf 'notes\n' > "$co/untracked.txt"
expect_exit 0 'checked out:' checkout fix/x
rm -- "${co:?}/untracked.txt"

# 6. sync は上流の main を fork の main（origin）とローカルの main へ fast-forward し、detached HEAD を動かさない
git -C "$tmp/seed" checkout -q main
printf 'v2\n' >> "$tmp/seed/file.txt"
git -C "$tmp/seed" commit -q -am v2
git -C "$tmp/seed" push -q "$tmp/upstream.git" main
v2="$(git -C "$tmp/seed" rev-parse HEAD)"
head_before="$(git -C "$co" rev-parse HEAD)"
expect_exit 0 'pushed: origin/main' sync
[ "$(git -C "$tmp/origin.git" rev-parse main)" = "$v2" ] || fail 'origin main was not fast-forwarded'
[ "$(git -C "$co" rev-parse main)" = "$v2" ] || fail 'local main was not fast-forwarded'
[ "$(git -C "$co" rev-parse HEAD)" = "$head_before" ] || fail 'sync moved the detached HEAD'

# 7. fork の main に上流に無いコミットがあれば 1 で、何も push しない
git -C "$tmp/seed" checkout -q -b stray "$v2"
printf 'stray\n' >> "$tmp/seed/file.txt"
git -C "$tmp/seed" commit -q -am stray
git -C "$tmp/seed" push -q "$tmp/origin.git" stray:main
stray="$(git -C "$tmp/seed" rev-parse HEAD)"
expect_exit 1 'origin/main has commits that upstream/main lacks' sync
[ "$(git -C "$tmp/origin.git" rev-parse main)" = "$stray" ] || fail 'sync changed a diverged origin main'

# 8. main を checkout 中で未コミットの変更があるまま sync すると、ローカル main は動かさず 1 で止まる。
#    きれいなローカル main は fast-forward する（detached の 6 とは別の分岐）。上流に無いコミットを持つローカル main は
#    動かさない（止まるときも、先に origin の main を上流の先端へ進める）
git -C "$tmp/seed" push -q -f "$tmp/origin.git" "$v2:refs/heads/main"
git -C "$tmp/seed" checkout -q main
printf 'v3\n' >> "$tmp/seed/file.txt"
git -C "$tmp/seed" commit -q -am v3
git -C "$tmp/seed" push -q "$tmp/upstream.git" main
v3="$(git -C "$tmp/seed" rev-parse HEAD)"
git -C "$co" branch -f main "$v2"
git -C "$co" checkout -q main
printf 'dirty\n' >> "$co/file.txt"
expect_exit 1 'has uncommitted changes on main' sync
[ "$(git -C "$tmp/origin.git" rev-parse main)" = "$v3" ] || fail 'sync did not push origin main forward despite the dirty local main'
[ "$(git -C "$co" rev-parse main)" = "$v2" ] || fail 'sync moved local main despite uncommitted changes on main'
git -C "$co" checkout -q -- file.txt
expect_exit 0 "updated: local main -> $v3" sync
[ "$(git -C "$co" rev-parse HEAD)" = "$v3" ] && [ "$(git -C "$co" symbolic-ref --short HEAD)" = main ] || fail 'sync did not fast-forward the checked-out main'
[ -z "$(git -C "$co" status --porcelain --untracked-files=no)" ] || fail 'sync left changes to tracked files'
printf 'local\n' >> "$co/file.txt" && git -C "$co" commit -q -am local
local_main="$(git -C "$co" rev-parse main)"
printf 'v4\n' >> "$tmp/seed/file.txt"
git -C "$tmp/seed" commit -q -am v4
git -C "$tmp/seed" push -q "$tmp/upstream.git" main
v4="$(git -C "$tmp/seed" rev-parse HEAD)"
expect_exit 1 'local main has commits that upstream/main lacks' sync
[ "$(git -C "$tmp/origin.git" rev-parse main)" = "$v4" ] || fail 'sync did not push origin main'
[ "$(git -C "$co" rev-parse main)" = "$local_main" ] || fail 'sync moved a diverged local main'
bash "$script" checkout fix/x >/dev/null

# 9. install: checkout を build し、tool update の後に resoloop --version を照合する。
#    導入した版と resoloop --version が違えば成功と報告せず 1
fix2_version="$(fork_version_of "$fix2")"
printf '0.0.1\n' > "$MOCK_STATE"
expect_exit 0 "ok: resoloop --version is $fix2_version" install fix/x
printf '0.0.1\n' > "$MOCK_STATE"
MOCK_SHIM_VERSION=9.9.9 expect_exit 1 "resoloop --version reports 9.9.9, but $fix2_version was installed" install fix/x

printf 'PASS: resoloop-fork script protects checkouts, branches and the installed version\n'
