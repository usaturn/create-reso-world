#!/bin/bash
# scripts/resoloop-fork.sh を、ローカルの bare リポジトリとモックの dotnet で検査する（ネットワークと実 SDK を使わない）
# 仕様: docs/superpowers/specs/2026-10-06-issue-41-resoloop-latest-without-lock-design.md D-5〜D-10
set -euo pipefail
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

# fork_version_of PREFIX COMMIT: 仕様 D-5 の版。PREFIX は csproj の <Version> に .fork（プレリリースが無ければ -fork）を付けたもの
fork_version_of() {
  printf '%s.%s.g%s\n' "$1" "$(TZ=UTC git -C "$tmp/seed" log -1 --format=%cd --date=format-local:%Y%m%d "$2")" \
    "$(git -C "$tmp/seed" rev-parse --short=7 "$2")"
}
fix_version="$(fork_version_of 1.2.3-preview.4.fork "$fix_commit")"

# モックの dotnet: 呼び出しを MOCK_LOG に記録する。--version は MOCK_SDK_MISSING なら global.json の SDK が無いとして 155。
# tool update は MOCK_STATE に版を書き、~/.dotnet/tools/resoloop に版（MOCK_SHIM_VERSION があればその値）を返す shim を置く
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
  --version)
    [ "${MOCK_SDK_MISSING:-0}" = 0 ] || { echo 'A compatible .NET SDK was not found.' >&2; exit 155; }
    echo 10.0.201 ;;
  build) [ "${MOCK_BUILD_FAIL:-0}" = 0 ] ;;
  test) [ "${MOCK_TEST_FAIL:-0}" = 0 ] ;;
  pack)
    out="$(arg_after -o "$@")" ver=""
    for a in "$@"; do case "$a" in -p:PackageVersion=*) ver="${a#-p:PackageVersion=}" ;; esac; done
    mkdir -p "$out" && : > "$out/ResoLoop.$ver.nupkg" ;;
  tool)
    case "$2" in
      list)
        [ "${MOCK_LIST_FAIL:-0}" = 0 ] || exit 1
        printf 'Package Id      Version      Commands\n'
        [ ! -s "$MOCK_STATE" ] || printf 'resoloop      %s      resoloop\n' "$(cat "$MOCK_STATE")" ;;
      update)
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
no_dotnet_work() {  # build・pack・tool update を呼んでいないこと
  if grep -qE '^dotnet (build|pack|tool update) ' "$MOCK_LOG"; then fail "$1"; fi
}

# 1. 引数の誤りは 2（checkout と install は ref が要り、- で始まる ref は受け付けない）
expect_exit 2 'usage:'
expect_exit 2 'usage:' bogus
expect_exit 2 'usage:' clone extra
expect_exit 2 'usage:' checkout
expect_exit 2 'usage:' install
expect_exit 2 'usage:' checkout --detach

# 2. clone 前の status は checkout が無いことを示して 0。clone 前の checkout / sync は 3
expect_exit 0 'is missing (run scripts/resoloop-fork.sh clone)' status
grep -qF 'installed version: none' "$tmp/out.txt" || fail 'status lacks the installed version'
expect_exit 3 'run scripts/resoloop-fork.sh clone' checkout fix/x
expect_exit 3 'run scripts/resoloop-fork.sh clone' sync

# 3. clone は origin と upstream を持つ checkout を作り、2 回目は remote を確かめるだけ
expect_exit 0 "cloned: $co" clone
[ "$(git -C "$co" remote get-url origin)" = "$tmp/origin.git" ] || fail 'origin url'
[ "$(git -C "$co" remote get-url upstream)" = "$tmp/upstream.git" ] || fail 'upstream url'
git -C "$co" rev-parse -q --verify refs/remotes/upstream/main >/dev/null || fail 'upstream was not fetched'
expect_exit 0 'is already cloned' clone

# 4. 末尾の / と .git の違いは同じ URL とみなす。違う URL と欠けた remote は 1 で、何も変えない
git -C "$co" remote set-url origin "$tmp/origin.git/"
expect_exit 0 'is already cloned' clone
git -C "$co" remote set-url origin "$tmp/upstream.git"
expect_exit 1 "remote origin is $tmp/upstream.git (expected $tmp/origin.git)" clone
[ "$(git -C "$co" remote get-url origin)" = "$tmp/upstream.git" ] || fail 'clone changed a mismatching remote'
git -C "$co" remote set-url origin "$tmp/origin.git"
git -C "$co" remote remove upstream
expect_exit 1 'remote upstream is missing' checkout fix/x
git -C "$co" remote add upstream "$tmp/upstream.git"

# 5. 外側のリポジトリの中にある、git の checkout でないディレクトリは 1（外側の remote を見ない）
git init -q "$tmp/outer" && mkdir -p "$tmp/outer/external/resoloop"
RESOLOOP_CHECKOUT="$tmp/outer/external/resoloop" expect_exit 1 'is not a git checkout of its own' clone
grep -qF 'rerun scripts/resoloop-fork.sh clone' "$tmp/out.txt" || fail 'clone message lacks the remediation hint'
RESOLOOP_CHECKOUT="$tmp/outer/external/resoloop" expect_exit 0 'is not a git checkout of its own' status

# 6. clone に失敗したら 4 で、checkout を残さない
RESOLOOP_CHECKOUT="$tmp/work/broken" RESOLOOP_ORIGIN_URL="$tmp/no-such-remote.git" expect_exit 4 'git clone failed' clone
[ ! -e "$tmp/work/broken" ] || fail 'a failed clone left a directory'

# 7. checkout は origin のブランチを detached で取り出し、解決した名前を示す。2 回目は何もしない
expect_exit 0 "checked out: $co at $fix_commit (origin/fix/x, detached)" checkout fix/x
[ "$(git -C "$co" rev-parse HEAD)" = "$fix_commit" ] || fail 'HEAD is not the branch on origin'
if git -C "$co" symbolic-ref -q HEAD >/dev/null; then fail 'HEAD is not detached'; fi
expect_exit 0 'is already at' checkout fix/x

# 8. origin のブランチと同じ名前のローカルのブランチより、origin のブランチを使う。origin に無い名前は git がそのまま
#    解決する（コミットの SHA、upstream/main）。解決できなければ 1
git -C "$co" branch fix/x refs/remotes/origin/main
expect_exit 0 'is already at' checkout fix/x
git -C "$co" branch -D -q fix/x
upstream_main="$(git -C "$co" rev-parse refs/remotes/upstream/main)"
expect_exit 0 "checked out: $co at $upstream_main (upstream/main, detached)" checkout upstream/main
expect_exit 0 "checked out: $co at $fix_commit ($fix_commit, detached)" checkout "$fix_commit"
expect_exit 1 'cannot resolve no-such-branch' checkout no-such-branch
# origin/HEAD（origin の既定のブランチを指す symbolic ref）は origin のブランチとして扱わない。push していないコミットを
# 持つローカルのブランチで checkout HEAD を実行しても、今のコミットのまま detached になる
git -C "$co" rev-parse -q --verify refs/remotes/origin/HEAD >/dev/null || fail 'case 8 needs origin/HEAD in the clone'
git -C "$co" switch -q -c local-only
printf 'local only\n' >> "$co/file.txt" && git -C "$co" commit -q -am 'local only'
local_commit="$(git -C "$co" rev-parse HEAD)"
expect_exit 0 "checked out: $co at $local_commit (HEAD, detached)" checkout HEAD
[ "$(git -C "$co" rev-parse HEAD)" = "$local_commit" ] || fail 'checkout HEAD moved away from the current commit'
git -C "$co" branch -D -q local-only

# 9. 追跡ファイルに未コミットの変更があれば 1 で、HEAD を動かさない。未追跡ファイルは妨げない
git -C "$co" checkout -q main
printf 'local edit\n' >> "$co/file.txt"
expect_exit 1 'has uncommitted changes to tracked files' checkout fix/x
[ "$(git -C "$co" symbolic-ref --short HEAD)" = main ] || fail 'checkout moved HEAD despite local changes'
git -C "$co" checkout -q -- file.txt
printf 'notes\n' > "$co/untracked.txt"
expect_exit 0 "checked out: $co at $fix_commit (origin/fix/x, detached)" checkout fix/x
rm -- "${co:?}/untracked.txt"

# 10. status は checkout と remote を表示する
expect_exit 0 "checkout: $co at $fix_commit (detached, clean)" status
grep -qF 'remotes: origin and upstream are as expected' "$tmp/out.txt" || fail 'status remotes'

# 11. sync は上流の main を fork の main（origin）とローカルの main へ fast-forward する
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

# 12. fork の main に上流に無いコミットがあれば 1 で、何も push しない
git -C "$tmp/seed" checkout -q -b stray "$v2"
printf 'stray\n' >> "$tmp/seed/file.txt"
git -C "$tmp/seed" commit -q -am stray
git -C "$tmp/seed" push -q "$tmp/origin.git" stray:main
stray="$(git -C "$tmp/seed" rev-parse HEAD)"
expect_exit 1 'origin/main has commits that upstream/main lacks' sync
[ "$(git -C "$tmp/origin.git" rev-parse main)" = "$stray" ] || fail 'sync changed a diverged origin main'

# 13. global.json が要求する SDK が無ければ build と test は 3 で、checkout で SDK を確かめ、dotnet build / test を呼ばない
: > "$MOCK_LOG"
MOCK_SDK_MISSING=1 expect_exit 3 '.NET SDK 10.0.201 (required by' build
MOCK_SDK_MISSING=1 expect_exit 3 'additionalVersions' test
grep -qxF "dotnet --version (cwd=$co)" "$MOCK_LOG" || fail 'the SDK was not checked in the checkout'
if grep -qE '^dotnet (build|test) ' "$MOCK_LOG"; then fail 'ran dotnet without the required SDK'; fi

# 14. build は HEAD のコミットから版を決め、checkout の中で dotnet build と dotnet pack を実行する
: > "$MOCK_LOG"
expect_exit 0 "built: $co/artifacts/fork/ResoLoop.$fix_version.nupkg" build
grep -qxF "dotnet build ResoLoop.slnx -c Release --nologo (cwd=$co)" "$MOCK_LOG" || fail 'dotnet build call'
grep -qxF "dotnet pack src/RLoop.Cli/RLoop.Cli.csproj -c Release --nologo -o artifacts/fork -p:PackageVersion=$fix_version -p:Version=$fix_version (cwd=$co)" "$MOCK_LOG" \
  || fail 'dotnet pack call'
MOCK_BUILD_FAIL=1 expect_exit 4 'dotnet build failed' build
printf 'local edit\n' >> "$co/file.txt"
expect_exit 1 'has uncommitted changes to tracked files' build
git -C "$co" checkout -q -- file.txt

# 15. csproj の <Version> にプレリリースが無ければ -fork を付ける。<Version> が無ければ 1
git -C "$tmp/seed" checkout -q -b stable "$fix_commit"
sed -i 's|<Version>.*</Version>|<Version>2.0.0</Version>|' "$tmp/seed/src/RLoop.Cli/RLoop.Cli.csproj"
git -C "$tmp/seed" commit -q -am stable
git -C "$tmp/seed" push -q "$tmp/origin.git" stable
stable_version="$(fork_version_of 2.0.0-fork "$(git -C "$tmp/seed" rev-parse HEAD)")"
git -C "$tmp/seed" checkout -q -b noversion "$fix_commit"
sed -i '/<Version>/d' "$tmp/seed/src/RLoop.Cli/RLoop.Cli.csproj"
git -C "$tmp/seed" commit -q -am noversion
git -C "$tmp/seed" push -q "$tmp/origin.git" noversion
bash "$script" checkout stable >/dev/null
expect_exit 0 "built: $co/artifacts/fork/ResoLoop.$stable_version.nupkg" build
bash "$script" checkout noversion >/dev/null
expect_exit 1 'cannot read <Version> from' build
bash "$script" checkout fix/x >/dev/null

# 16. test は checkout の中で dotnet test を実行する
: > "$MOCK_LOG"
expect_exit 0 'ok: dotnet test passed' test
grep -qxF "dotnet test ResoLoop.slnx --nologo (cwd=$co)" "$MOCK_LOG" || fail 'dotnet test call'
MOCK_TEST_FAIL=1 expect_exit 4 'dotnet test failed' test

# 17. install（checkout が無い）: clone・checkout・build の後に tool update し、resoloop --version を照合する。
#     公開版へ戻すコマンドを示す
rm -rf -- "${co:?}"
: > "$MOCK_LOG"
expect_exit 0 "ok: resoloop --version is $fix_version" install fix/x
grep -qF "cloned: $co" "$tmp/out.txt" || fail 'install did not clone'
grep -qF 'bash .devcontainer/install_resoloop.bash' "$tmp/out.txt" || fail 'install did not show how to return to the release'
[ "$(git -C "$co" rev-parse HEAD)" = "$fix_commit" ] || fail 'install did not check out the branch'
grep -qxF "dotnet tool update --global ResoLoop --add-source $co/artifacts/fork --version $fix_version --allow-downgrade (cwd=$repo_root)" "$MOCK_LOG" \
  || fail 'dotnet tool update call'

# 18. install（同じ版を導入済み）: 何も作り直さず、照合だけ行う。SDK が無くても通る
: > "$MOCK_LOG"
MOCK_SDK_MISSING=1 expect_exit 0 "ResoLoop $fix_version is already installed" install fix/x
grep -qF "ok: resoloop --version is $fix_version" "$tmp/out.txt" || fail 'install skipped the version check'
no_dotnet_work 'rebuilt an installed version'

# 19. install（別の版を導入済み）: 同じ tool update で上書きする。SDK が無ければ 3 で、ビルドも導入もしない
printf '0.0.1\n' > "$MOCK_STATE"
: > "$MOCK_LOG"
MOCK_SDK_MISSING=1 expect_exit 3 '.NET SDK 10.0.201 (required by' install fix/x
no_dotnet_work 'install ran dotnet build/pack/tool update without the required SDK'
expect_exit 0 "ok: resoloop --version is $fix_version" install fix/x
grep -qF "dotnet tool update --global ResoLoop --add-source $co/artifacts/fork --version $fix_version --allow-downgrade" "$MOCK_LOG" \
  || fail 'did not use dotnet tool update'

# 20. 導入後の resoloop --version が違えば 1。tool の失敗は 4
printf '0.0.1\n' > "$MOCK_STATE"
MOCK_SHIM_VERSION=9.9.9 expect_exit 1 "resoloop --version reports 9.9.9, but $fix_version was installed" install fix/x
printf '0.0.1\n' > "$MOCK_STATE"
MOCK_TOOL_FAIL=1 expect_exit 4 'dotnet tool update failed' install fix/x

# 21. main を checkout 中で dirty なまま sync すると、origin への push は済ませつつローカル main は動かさず 1 で止まる
# (case 12 は origin/main を upstream から分岐させたままにし、case 17 の install の再 clone で $co のローカル
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
bash "$script" checkout fix/x >/dev/null

# 22. 相対パスの RESOLOOP_CHECKOUT は呼び出し時の cwd を基準に絶対パスにする。install は build と pack を
#     checkout の中で実行し、--add-source にも絶対パスを渡す
printf '0.0.1\n' > "$MOCK_STATE"
: > "$MOCK_LOG"
(cd "$tmp/work" && RESOLOOP_CHECKOUT=external/resoloop expect_exit 0 "ok: resoloop --version is $fix_version" install fix/x)
grep -qxF "dotnet build ResoLoop.slnx -c Release --nologo (cwd=$co)" "$MOCK_LOG" || fail 'install did not build'
grep -qxF "dotnet tool update --global ResoLoop --add-source $co/artifacts/fork --version $fix_version --allow-downgrade (cwd=$repo_root)" "$MOCK_LOG" \
  || fail 'install passed a relative --add-source'
(cd "$tmp/work" && RESOLOOP_CHECKOUT=external/resoloop expect_exit 0 "checkout: $co at $fix_commit (detached, clean, matches the installed fork build)" status)

# 23. status は導入済みの版の種類を示す。fork のビルドなら公開版へ戻すコマンドと、HEAD がそのビルドのコミットかを示す。
#     導入済みの版を読めないときは unknown と表示する
grep -qF "installed version: $fix_version (fork build)" "$tmp/out.txt" || fail 'status did not flag the fork build'
grep -qF 'return to the latest NuGet release: bash .devcontainer/install_resoloop.bash' "$tmp/out.txt" || fail 'status lacks the return command'
git -C "$co" checkout -q main
main_head="$(git -C "$co" rev-parse HEAD)"
expect_exit 0 "checkout: $co at $main_head (main, clean, differs from the installed fork build)" status
printf '1.2.3-preview.4\n' > "$MOCK_STATE"
expect_exit 0 'installed version: 1.2.3-preview.4 (NuGet release)' status
if grep -qF 'return to the latest NuGet release' "$tmp/out.txt"; then fail 'status showed the return command for a release'; fi
MOCK_LIST_FAIL=1 expect_exit 0 'installed version: unknown (dotnet tool list --global failed)' status

# 24. 末尾の .git の有無だけが違う URL も同じとみなす
git -C "$co" remote set-url origin "$tmp/origin"
expect_exit 0 'is already cloned' clone
git -C "$co" remote set-url origin "$tmp/origin.git"

# 25. remote が食い違っていれば、sync は fetch も push もせずに 1
git -C "$co" remote set-url upstream "$tmp/origin.git"
origin_before="$(git -C "$tmp/origin.git" rev-parse main)"
expect_exit 1 'has unexpected remotes' sync
grep -qF "remote upstream is $tmp/origin.git (expected $tmp/upstream.git)" "$tmp/out.txt" || fail 'sync did not name the mismatching remote'
[ "$(git -C "$tmp/origin.git" rev-parse main)" = "$origin_before" ] || fail 'sync pushed despite mismatching remotes'
git -C "$co" remote set-url upstream "$tmp/upstream.git"

# 26. main を checkout 中でも、きれいなローカル main は sync が fast-forward する。上流に無いコミットを持つローカル
#     main は動かさずに 1（origin への push は済ませる）
git -C "$tmp/seed" checkout -q main
printf 'v4\n' >> "$tmp/seed/file.txt"
git -C "$tmp/seed" commit -q -am v4
git -C "$tmp/seed" push -q "$tmp/upstream.git" main
v4="$(git -C "$tmp/seed" rev-parse HEAD)"
expect_exit 0 "updated: local main -> $v4" sync
[ "$(git -C "$co" rev-parse HEAD)" = "$v4" ] && [ "$(git -C "$co" symbolic-ref --short HEAD)" = main ] || fail 'sync did not fast-forward the checked-out main'
[ -z "$(git -C "$co" status --porcelain --untracked-files=no)" ] || fail 'sync left changes to tracked files'
printf 'local\n' >> "$co/file.txt" && git -C "$co" commit -q -am local
local_main="$(git -C "$co" rev-parse main)"
printf 'v5\n' >> "$tmp/seed/file.txt"
git -C "$tmp/seed" commit -q -am v5
git -C "$tmp/seed" push -q "$tmp/upstream.git" main
v5="$(git -C "$tmp/seed" rev-parse HEAD)"
expect_exit 1 'local main has commits that upstream/main lacks' sync
[ "$(git -C "$tmp/origin.git" rev-parse main)" = "$v5" ] || fail 'sync did not push origin main'
[ "$(git -C "$co" rev-parse main)" = "$local_main" ] || fail 'sync moved a diverged local main'

# 27. origin に後から push されたブランチの先端も、checkout は fetch してから取り出す
git -C "$tmp/seed" checkout -q fix/x
printf 'fix2\n' >> "$tmp/seed/file.txt"
git -C "$tmp/seed" commit -q -am fix2
git -C "$tmp/seed" push -q "$tmp/origin.git" fix/x
fix2="$(git -C "$tmp/seed" rev-parse HEAD)"
if git -C "$co" cat-file -e "$fix2^{commit}" 2>/dev/null; then fail 'case 27 needs a commit the checkout has not fetched'; fi
expect_exit 0 "checked out: $co at $fix2 (origin/fix/x, detached)" checkout fix/x

# 28. checkout が無い・自前の checkout でないときも、status は remotes の行を出す。後者は対処も示す
RESOLOOP_CHECKOUT="$tmp/work/none" expect_exit 0 'remotes: unknown (no checkout)' status
RESOLOOP_CHECKOUT="$tmp/outer/external/resoloop" expect_exit 0 'is not a git checkout of its own; remove it (or move a checkout there) and rerun scripts/resoloop-fork.sh clone' status
grep -qF 'remotes: unknown (no checkout)' "$tmp/out.txt" || fail 'status lacks the remotes line for a directory that is not a checkout'

printf 'PASS: resoloop-fork script behaves as specified\n'
