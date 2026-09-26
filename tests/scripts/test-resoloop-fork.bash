#!/bin/bash
# scripts/resoloop-fork.sh を、ローカルの bare リポジトリとモックの dotnet で検査する（ネットワークと実 SDK を使わない）
set -euo pipefail
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null
export GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=core.excludesFile GIT_CONFIG_VALUE_0=/dev/null
export GIT_AUTHOR_NAME=test GIT_AUTHOR_EMAIL=test@example.com GIT_COMMITTER_NAME=test GIT_COMMITTER_EMAIL=test@example.com
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
script="$repo_root/scripts/resoloop-fork.sh"
tmp="$(cd "$(mktemp -d)" && pwd -P)"
trap 'rm -rf "$tmp"' EXIT
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }

# 上流（upstream.git）と fork（origin.git）。fork には修正ブランチ fix/x がある
git init -q -b main "$tmp/seed"
printf 'v1\n' > "$tmp/seed/file.txt"
git -C "$tmp/seed" add file.txt && git -C "$tmp/seed" commit -q -m v1
git clone -q --bare "$tmp/seed" "$tmp/upstream.git"
git clone -q --bare "$tmp/seed" "$tmp/origin.git"
git -C "$tmp/seed" checkout -q -b fix/x
printf 'fix\n' >> "$tmp/seed/file.txt"
git -C "$tmp/seed" commit -q -am fix
git -C "$tmp/seed" push -q "$tmp/origin.git" fix/x
fix_commit="$(git -C "$tmp/seed" rev-parse HEAD)"

write_lock() {  # $1=モード、$2=コミット（省略時は fix/x の先端）
  cat > "$tmp/resoloop.lock" <<EOF
RESOLOOP_MODE=$1
RESOLOOP_NUGET_VERSION=0.1.0-preview.14
RESOLOOP_FORK_ORIGIN=$tmp/origin.git
RESOLOOP_FORK_UPSTREAM=$tmp/upstream.git
RESOLOOP_FORK_REF=fix/x
RESOLOOP_FORK_COMMIT=${2:-$fix_commit}
RESOLOOP_FORK_PACKAGE_VERSION=0.1.0-preview.14.pr1.test
RESOLOOP_FORK_PR=https://example.com/upstream/resoloop/pull/1
RESOLOOP_FORK_SDK=10.0.201
EOF
}
write_lock fork
export RESOLOOP_LOCK_FILE="$tmp/resoloop.lock" RESOLOOP_FORK_CHECKOUT="$tmp/work/external/resoloop"
co="$RESOLOOP_FORK_CHECKOUT"

# モックの dotnet: 呼び出しを MOCK_LOG に記録する。tool install/update は MOCK_STATE に版を書き、
# ~/.dotnet/tools/resoloop に版（MOCK_SHIM_VERSION があればその値）を返す shim を置く
mkdir -p "$tmp/mockbin" "$tmp/home/.dotnet/tools"
cat > "$tmp/mockbin/dotnet" <<'EOF'
#!/bin/bash
printf 'dotnet %s (cwd=%s)\n' "$*" "$PWD" >> "$MOCK_LOG"
arg_after() {  # $1=オプション名。その次の引数を出力する
  local want="$1"
  shift
  while [ $# -gt 0 ]; do
    if [ "$1" = "$want" ]; then printf '%s\n' "$2"; return; fi
    shift
  done
}
case "$1" in
  --list-sdks) printf '%s\n' "${MOCK_SDKS:-10.0.201 [/usr/share/dotnet/sdk]}" ;;
  build) [ "${MOCK_BUILD_FAIL:-0}" = 0 ] ;;
  test) [ "${MOCK_TEST_FAIL:-0}" = 0 ] ;;
  pack)
    out="$(arg_after -o "$@")" ver=""
    for a in "$@"; do case "$a" in -p:PackageVersion=*) ver="${a#-p:PackageVersion=}" ;; esac; done
    mkdir -p "$out" && : > "$out/ResoLoop.$ver.nupkg" ;;
  tool)
    case "$2" in
      list)
        printf 'Package Id      Version      Commands\n'
        [ ! -s "$MOCK_STATE" ] || printf 'resoloop      %s      resoloop\n' "$(cat "$MOCK_STATE")" ;;
      install|update)
        [ "${MOCK_TOOL_FAIL:-0}" = 0 ] || exit 1
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
export HOME="$tmp/home" PATH="$tmp/mockbin:$PATH" MOCK_LOG="$tmp/dotnet.log" MOCK_STATE="$tmp/installed"
: > "$MOCK_LOG"
: > "$MOCK_STATE"

expect_exit() {  # $1=期待する終了コード、$2=出力に含まれるべき文字列、残り=resoloop-fork.sh の引数
  local want="$1" needle="$2" got=0
  shift 2
  bash "$script" "$@" > "$tmp/out.txt" 2>&1 || got=$?
  [ "$got" -eq "$want" ] || { cat "$tmp/out.txt" >&2; fail "expected exit $want, got $got: $*"; }
  grep -qF -- "$needle" "$tmp/out.txt" || { cat "$tmp/out.txt" >&2; fail "expected output '$needle': $*"; }
}

# 1. 引数の誤りは 2
expect_exit 2 'usage:'
expect_exit 2 'usage:' bogus
expect_exit 2 'usage:' clone extra

# 2. ロックが不正なら 3
sed -i '/^RESOLOOP_FORK_SDK=/d' "$tmp/resoloop.lock"
expect_exit 3 'missing key RESOLOOP_FORK_SDK' status
write_lock fork

# 3. clone 前の status は checkout が無いことを示して 0。clone 前の checkout / sync は 3
expect_exit 0 'is missing (run scripts/resoloop-fork.sh clone)' status
grep -qF 'expected version: 0.1.0-preview.14.pr1.test' "$tmp/out.txt" || fail 'status lacks the expected version'
grep -qF 'installed version: none' "$tmp/out.txt" || fail 'status lacks the installed version'
expect_exit 3 'run scripts/resoloop-fork.sh clone' checkout
expect_exit 3 'run scripts/resoloop-fork.sh clone' sync

# 4. clone は origin と upstream を持つ checkout を作り、2 回目は remote を確かめるだけ
expect_exit 0 "cloned: $co" clone
[ "$(git -C "$co" remote get-url origin)" = "$tmp/origin.git" ] || fail 'origin url'
[ "$(git -C "$co" remote get-url upstream)" = "$tmp/upstream.git" ] || fail 'upstream url'
git -C "$co" rev-parse -q --verify refs/remotes/upstream/main >/dev/null || fail 'upstream was not fetched'
expect_exit 0 'is already cloned' clone

# 5. 末尾の / と .git の違いは同じ URL とみなす。違う URL と欠けた remote は 1 で、何も変えない
git -C "$co" remote set-url origin "$tmp/origin.git/"
expect_exit 0 'is already cloned' clone
git -C "$co" remote set-url origin "$tmp/upstream.git"
expect_exit 1 "remote origin is $tmp/upstream.git (expected $tmp/origin.git)" clone
[ "$(git -C "$co" remote get-url origin)" = "$tmp/upstream.git" ] || fail 'clone changed a mismatching remote'
git -C "$co" remote set-url origin "$tmp/origin.git"
git -C "$co" remote remove upstream
expect_exit 1 'remote upstream is missing' checkout
git -C "$co" remote add upstream "$tmp/upstream.git"

# 6. 外側のリポジトリの中にある、git の checkout でないディレクトリは 1（外側の remote を見ない）
git init -q "$tmp/outer" && mkdir -p "$tmp/outer/external/resoloop"
RESOLOOP_FORK_CHECKOUT="$tmp/outer/external/resoloop" expect_exit 1 'is not a git checkout of its own' clone
grep -qF 'rerun scripts/resoloop-fork.sh clone' "$tmp/out.txt" || fail 'clone message lacks the remediation hint'
RESOLOOP_FORK_CHECKOUT="$tmp/outer/external/resoloop" expect_exit 0 'is not a git checkout of its own' status

# 7. clone に失敗したら 4 で、checkout を残さない
RESOLOOP_FORK_CHECKOUT="$tmp/work/broken" expect_exit 0 'is missing' status
sed -i "s|^RESOLOOP_FORK_ORIGIN=.*|RESOLOOP_FORK_ORIGIN=$tmp/no-such-remote.git|" "$tmp/resoloop.lock"
RESOLOOP_FORK_CHECKOUT="$tmp/work/broken" expect_exit 4 'git clone failed' clone
[ ! -e "$tmp/work/broken" ] || fail 'a failed clone left a directory'
write_lock fork

# 8. checkout はロックのコミットを detached で取り出し、2 回目は何もしない
expect_exit 0 "checked out: $co at $fix_commit" checkout
[ "$(git -C "$co" rev-parse HEAD)" = "$fix_commit" ] || fail 'HEAD is not the lock commit'
if git -C "$co" symbolic-ref -q HEAD >/dev/null; then fail 'HEAD is not detached'; fi
expect_exit 0 'is already at' checkout

# 9. 追跡ファイルに未コミットの変更があれば 1 で、HEAD を動かさない。未追跡ファイルは妨げない
git -C "$co" checkout -q main
printf 'local edit\n' >> "$co/file.txt"
expect_exit 1 'has uncommitted changes to tracked files' checkout
[ "$(git -C "$co" symbolic-ref --short HEAD)" = main ] || fail 'checkout moved HEAD despite local changes'
git -C "$co" checkout -q -- file.txt
printf 'notes\n' > "$co/untracked.txt"
expect_exit 0 "checked out: $co at $fix_commit" checkout
rm "$co/untracked.txt"

# 10. origin に無いコミットは fetch してから 1
write_lock fork 0123456789abcdef0123456789abcdef01234567
expect_exit 1 'is not on origin' checkout
write_lock fork

# 11. status は checkout・remote・導入済み版をロックと比べて表示する
expect_exit 0 "checkout: $co at $fix_commit (detached, clean, matches the lock)" status
grep -qF 'remotes: origin and upstream match the lock' "$tmp/out.txt" || fail 'status remotes'

# 12. sync は上流の main を fork の main（origin）とローカルの main へ fast-forward する
git -C "$tmp/seed" checkout -q main
printf 'v2\n' >> "$tmp/seed/file.txt"
git -C "$tmp/seed" commit -q -am v2
git -C "$tmp/seed" push -q "$tmp/upstream.git" main
v2="$(git -C "$tmp/seed" rev-parse HEAD)"
expect_exit 0 "pushed: origin/main" sync
[ "$(git -C "$tmp/origin.git" rev-parse main)" = "$v2" ] || fail 'origin main was not fast-forwarded'
[ "$(git -C "$co" rev-parse main)" = "$v2" ] || fail 'local main was not fast-forwarded'
[ "$(git -C "$co" rev-parse HEAD)" = "$fix_commit" ] || fail 'sync moved the detached HEAD'
expect_exit 0 'already matches upstream/main' sync

# 13. fork の main に上流に無いコミットがあれば 1 で、何も push しない
git -C "$tmp/seed" checkout -q -b stray "$v2"
printf 'stray\n' >> "$tmp/seed/file.txt"
git -C "$tmp/seed" commit -q -am stray
git -C "$tmp/seed" push -q "$tmp/origin.git" stray:main
stray="$(git -C "$tmp/seed" rev-parse HEAD)"
expect_exit 1 'origin/main has commits that upstream/main lacks' sync
[ "$(git -C "$tmp/origin.git" rev-parse main)" = "$stray" ] || fail 'sync changed a diverged origin main'

# 14. ロックの SDK が無ければ build と test は 3 で、dotnet build / test を呼ばない
: > "$MOCK_LOG"
MOCK_SDKS='10.0.401 [/usr/share/dotnet/sdk]' expect_exit 3 '.NET SDK 10.0.201 is not installed' build
MOCK_SDKS='10.0.401 [/usr/share/dotnet/sdk]' expect_exit 3 '.NET SDK 10.0.201 is not installed' test
if grep -qE '^dotnet (build|test) ' "$MOCK_LOG"; then fail 'ran dotnet without the required SDK'; fi

# 15. build は checkout の中で dotnet build と dotnet pack を実行し、ロックの版の nupkg を作る
: > "$MOCK_LOG"
expect_exit 0 "built: $co/artifacts/fork/ResoLoop.0.1.0-preview.14.pr1.test.nupkg" build
grep -qxF "dotnet build ResoLoop.slnx -c Release --nologo (cwd=$co)" "$MOCK_LOG" || fail 'dotnet build call'
grep -qxF "dotnet pack src/RLoop.Cli/RLoop.Cli.csproj -c Release --nologo -o artifacts/fork -p:PackageVersion=0.1.0-preview.14.pr1.test -p:Version=0.1.0-preview.14.pr1.test (cwd=$co)" "$MOCK_LOG" \
  || fail 'dotnet pack call'
MOCK_BUILD_FAIL=1 expect_exit 4 'dotnet build failed' build

# 16. test は checkout の中で dotnet test を実行する
: > "$MOCK_LOG"
expect_exit 0 'ok: dotnet test passed' test
grep -qxF "dotnet test ResoLoop.slnx --nologo (cwd=$co)" "$MOCK_LOG" || fail 'dotnet test call'
MOCK_TEST_FAIL=1 expect_exit 4 'dotnet test failed' test

# 17. install（未導入）: clone・checkout・build の後に tool install し、resoloop --version を照合する
rm -rf "$co"
: > "$MOCK_LOG"
expect_exit 0 'ok: resoloop --version is 0.1.0-preview.14.pr1.test' install
grep -qF "cloned: $co" "$tmp/out.txt" || fail 'install did not clone'
[ "$(git -C "$co" rev-parse HEAD)" = "$fix_commit" ] || fail 'install did not check out the lock commit'
grep -qxF "dotnet tool install --global ResoLoop --add-source $co/artifacts/fork --version 0.1.0-preview.14.pr1.test --allow-downgrade (cwd=$repo_root)" "$MOCK_LOG" \
  || fail 'dotnet tool install call'

# 18. install（導入済みが同じ版）: 何も作り直さず、照合だけ行う
: > "$MOCK_LOG"
expect_exit 0 'is already installed (to install a rebuilt package, raise RESOLOOP_FORK_PACKAGE_VERSION' install
grep -qF 'ok: resoloop --version is 0.1.0-preview.14.pr1.test' "$tmp/out.txt" || fail 'install skipped the version check'
if grep -qE '^dotnet (build|pack|tool install|tool update) ' "$MOCK_LOG"; then fail 'rebuilt an installed version'; fi

# 19. install（別の版を導入済み）: tool update を使う
printf '0.0.1\n' > "$MOCK_STATE"
: > "$MOCK_LOG"
expect_exit 0 'ok: resoloop --version is 0.1.0-preview.14.pr1.test' install
grep -qF 'dotnet tool update --global ResoLoop --add-source' "$MOCK_LOG" || fail 'did not use dotnet tool update'

# 20. 導入後の resoloop --version がロックと違えば 1。tool の失敗は 4。nuget モードの install は 1
printf '0.0.1\n' > "$MOCK_STATE"
MOCK_SHIM_VERSION=9.9.9 expect_exit 1 'resoloop --version reports 9.9.9, but the lock expects 0.1.0-preview.14.pr1.test' install
printf '0.0.1\n' > "$MOCK_STATE"
MOCK_TOOL_FAIL=1 expect_exit 4 'dotnet tool update failed' install
write_lock nuget
expect_exit 1 'RESOLOOP_MODE is nuget' install
write_lock fork

# 21. main を checkout 中で dirty なまま sync すると、origin への push は済ませつつローカル main は動かさず 1 で止まる
# (case 13 は origin/main を upstream から分岐させたままにし、case 17 以降の install の再 clone で $co のローカル
# main も stray まで進んでいるので、ここでは seed から origin.git の main を upstream の先端 v2 まで戻し、
# $co のローカル main も v2 まで戻してから使う)
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
bash "$script" checkout >/dev/null

# 22. install は SDK をビルドが要るときだけ確かめる: 導入済みが期待版と違えば SDK 不足で 3 になり、
# clone も dotnet build/pack/tool install/update も行わない。導入済みが期待版と同じなら SDK 不足でも成功する
rm -rf "$co"
printf '0.0.1\n' > "$MOCK_STATE"
: > "$MOCK_LOG"
MOCK_SDKS='10.0.401 [/usr/share/dotnet/sdk]' expect_exit 3 '.NET SDK 10.0.201 is not installed' install
[ ! -e "$co" ] || fail 'install cloned despite the missing SDK'
if grep -qE '^dotnet (build|pack|tool install|tool update) ' "$MOCK_LOG"; then
  fail 'install ran dotnet build/pack/tool install/update without the required SDK'
fi
printf '#!/bin/bash\nprintf "%%s\\n" %q\n' 0.1.0-preview.14.pr1.test > "$HOME/.dotnet/tools/resoloop"
chmod +x "$HOME/.dotnet/tools/resoloop"
printf '0.1.0-preview.14.pr1.test\n' > "$MOCK_STATE"
MOCK_SDKS='10.0.401 [/usr/share/dotnet/sdk]' expect_exit 0 'is already installed' install

printf 'PASS: resoloop-fork script behaves as specified\n'
