# Issue #41 ResoLoop の版のロック廃止 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

- 状態: draft（内容の明示承認はまだ無い）
- 実行許可: Spec と同じ（2026-10-06 の「推奨案で進めて、途中で止めずに PR まで作成せよ」）。実行方式は Native（この会話で自分で実装し、最後にブランチ全体を見直す）。タスク同士がスクリプトのインターフェース（関数名・出力の文言・環境変数）で強く結び付いており、分けて渡すと食い違いの確認が増えるため
- 基準: `main` の `e6edcf8`、Spec のコミット `5d6fbaf`

**Goal:** `.devcontainer/resoloop.lock` を廃止し、postCreate と手動のコマンドで NuGet の最新の公開版の ResoLoop を入れる。fork のビルドはロック無しの一時的な上書きとして使えるようにする。

**Architecture:** 導入は `dotnet tool update --global ResoLoop --prerelease --allow-downgrade` の 1 本にする。fork の上書きは `scripts/resoloop-fork.sh install <ref>` が、コミットから決まる版（`<Version>.fork.<日付>.g<SHA>`）でビルドして入れる。同梱スキルの同期は表示だけにし、postCreate と check-layout を失敗させない（手での編集は check-layout が引き続き検出する）。

**Tech Stack:** bash、git、dotnet 10 の global tool、モックの dotnet・resoloop を使う bash のテスト（`.devcontainer/run-tests.bash` が集める）

**Spec:** `docs/superpowers/specs/2026-10-06-issue-41-resoloop-latest-without-lock-design.md`

## Global Constraints

- 最新の導入のコマンドは `dotnet tool update --global ResoLoop --prerelease --allow-downgrade`（D-1）
- fork の版は `<csproj の Version>.fork.<UTC のコミット日 YYYYMMDD>.g<短い SHA 7 桁>`。Version にプレリリースの部分が無ければ `-fork.`（D-5）
- remote の既定の URL は `https://github.com/usaturn/resoloop.git`（origin）と `https://github.com/orange3134/resoloop.git`（upstream）。環境変数は `RESOLOOP_CHECKOUT`・`RESOLOOP_ORIGIN_URL`・`RESOLOOP_UPSTREAM_URL`（D-7）
- `rg 'resoloop\.lock|resoloop-lock|RESOLOOP_(MODE|NUGET_VERSION|FORK_)'` に一致する名前を新しく作らない
- テストは版番号などの変わり得る値を固定値で検査しない。版はモックが返す値やテストが作る入力だけを使う
- `.devcontainer/*.bash` は index の mode を 100755 にする（`tests/scripts/test-file-modes.bash`）
- Python は使わない（bash だけ）。rm にシェル変数を使うときは `${VAR:?}` を付けて引用する
- README の見出し `## ResoLoop の版` と AGENTS.md の見出し `## ResoLoop の版管理` は変えない（D-16・D-17）

## Review Focus

1. `dotnet tool list --global` の見出しが日本語に訳されている（この環境の実際の出力）→ 版を正しく読む。Task 1 のテストで日本語の見出しを使う
2. NuGet に届かない postCreate で、導入済みの版が無い → 失敗する。ある → 警告して続ける。Task 2 のテスト 4・5
3. origin のブランチと同じ名前のローカルのブランチがある → origin のブランチを使い、解決した名前を表示する。Task 6 のテスト
4. csproj の Version にプレリリースの部分が無い（`2.0.0`）→ `2.0.0-fork.…` という正しい SemVer になる。Task 6 のテスト
5. `-` で始まる名前のプロジェクト → postCreate の表示がオプションと誤解させない（`./` を付ける）。Task 4 のテスト

---

## File Structure

| ファイル | 責務 |
| --- | --- |
| `.devcontainer/resoloop-tool.bash`（新規） | 導入済みの版の取得と、`resoloop --version` の解析（source して使う） |
| `.devcontainer/install_resoloop.bash` | 最新の公開版の導入と照合 |
| `.devcontainer/verify-resonite-tooling.bash` | .NET 10 SDK・resoloop・Blender が動くことの確認 |
| `.devcontainer/report-resoloop-skills.bash`（新規） | 各プロジェクトの `skills sync --check` の表示（常に 0） |
| `.devcontainer/install_beforehand.bash` | postCreate の手順（手順名と、表示の手順の追加） |
| `scripts/check-layout.sh` | 検査 7 の判定の変更、検査 8 の削除 |
| `scripts/resoloop-fork.sh` | fork の取得・追従・checkout・ビルド・テスト・一時的な導入・状態の表示 |
| 文書（`AGENTS.md`・`README.md`・`.devcontainer/README.md`・`docs/resoloop-fork-workflow.md`・`docs/integration.md`・`repo-cleanup-after-merge/SKILL.md`・`devcontainer.json` のコメント） | 新しい仕組みの説明 |

---

### Task 1: 版を読む関数を `.devcontainer/resoloop-tool.bash` に移す

**Files:**
- Create: `.devcontainer/resoloop-tool.bash`（100755）
- Test: `.devcontainer/test-resoloop-tool.bash`（新規、100755）

**Interfaces:**
- Produces: `resoloop_installed_version`（標準出力に導入済みの版、未導入なら空。一覧の取得に失敗したら 1）、`resoloop_version_of TEXT`（最初の空でない行の前後の空白と `+` 以降を除いて出力。無ければ 1）

- [ ] **Step 1: テストを書く**

~~~bash
#!/bin/bash
# .devcontainer/resoloop-tool.bash の関数（導入済みの版の取得と、resoloop --version の解析）を検査する
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
tmp="$(mktemp -d)"
trap 'rm -rf -- "$tmp"' EXIT
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
# shellcheck source=resoloop-tool.bash
source "$root/.devcontainer/resoloop-tool.bash"

# 1. resoloop --version の出力から版を取り出す
[ "$(resoloop_version_of $'0.1.0-preview.14\n')" = 0.1.0-preview.14 ] || fail 'plain version'
[ "$(resoloop_version_of $'  1.2.3+abc123  \n')" = 1.2.3 ] || fail 'whitespace and build metadata'
[ "$(resoloop_version_of $'\n\n2.0.0\nextra\n')" = 2.0.0 ] || fail 'first non-empty line'
if resoloop_version_of $'\n  \n' >/dev/null; then fail 'accepted empty output'; fi

# 2. dotnet tool list --global から導入済み版を読む（モックの dotnet。MOCK_HEADER で見出しを差し替える）
mkdir -p "$tmp/bin"
cat > "$tmp/bin/dotnet" <<'EOF'
#!/bin/bash
[ "$*" = 'tool list --global' ] || exit 64
[ "${MOCK_LIST_FAIL:-0}" = 0 ] || exit 1
printf '%s\n-------------------------------------\n' "${MOCK_HEADER:-Package Id      Version      Commands}"
[ -z "${MOCK_LIST_LINE:-}" ] || printf '%s\n' "$MOCK_LIST_LINE"
EOF
chmod +x "$tmp/bin/dotnet"
[ "$(PATH="$tmp/bin:$PATH" MOCK_LIST_LINE='resoloop  0.1.0-preview.14.fork.20260925.gabc1234  resoloop' resoloop_installed_version)" = 0.1.0-preview.14.fork.20260925.gabc1234 ] \
  || fail 'installed version'
[ "$(PATH="$tmp/bin:$PATH" MOCK_LIST_LINE='ResoLoop 1.0.0 resoloop' resoloop_installed_version)" = 1.0.0 ] || fail 'package id is case-insensitive'
# この環境の dotnet は見出しを日本語で出す
[ "$(PATH="$tmp/bin:$PATH" MOCK_HEADER='パッケージ ID      バージョン      コマンド' MOCK_LIST_LINE='resoloop  1.0.0  resoloop' resoloop_installed_version)" = 1.0.0 ] \
  || fail 'localized header'
[ -z "$(PATH="$tmp/bin:$PATH" MOCK_LIST_LINE='my-resoloop-plugin 1.0.0 other' resoloop_installed_version)" ] || fail 'matched a different package'
[ -z "$(PATH="$tmp/bin:$PATH" resoloop_installed_version)" ] || fail 'reported a version when nothing is installed'
if PATH="$tmp/bin:$PATH" MOCK_LIST_FAIL=1 resoloop_installed_version >/dev/null; then fail 'ignored a failing dotnet tool list'; fi

printf 'PASS: resoloop tool helpers behave as specified\n'
~~~

- [ ] **Step 2: 失敗を確かめる**

Run: `bash .devcontainer/run-tests.bash .devcontainer/test-resoloop-tool.bash`
Expected: FAIL（`resoloop-tool.bash` が無く source できない）

- [ ] **Step 3: 実装する**（`.devcontainer/resoloop-lock.bash` の後ろの 2 つの関数をそのまま移す）

~~~bash
#!/bin/bash
# ResoLoop のグローバルツールの版を読む関数集。source して使い、単体では何もしない。
# 使う側: .devcontainer/install_resoloop.bash、scripts/resoloop-fork.sh
# 仕様: docs/superpowers/specs/2026-10-06-issue-41-resoloop-latest-without-lock-design.md D-11

# resoloop_installed_version
# dotnet tool list --global から ResoLoop の導入済み版を出力する（未導入なら何も出力しない）。
# 一覧を取れなければ 1 を返す。
resoloop_installed_version() {
  local listing
  listing="$(dotnet tool list --global </dev/null)" || return 1
  awk 'tolower($1) == "resoloop" && !found { print $2; found = 1 }' <<<"$listing"
}

# resoloop_version_of TEXT
# resoloop --version の出力から版を取り出す。最初の空でない行の前後の空白と、+ 以降のビルドメタデータを除く。
# 空でない行が無ければ 1 を返す。
resoloop_version_of() {
  local line
  while IFS= read -r line; do
    line="${line#"${line%%[![:space:]]*}"}"
    line="${line%"${line##*[![:space:]]}"}"
    [ -n "$line" ] || continue
    printf '%s\n' "${line%%+*}"
    return 0
  done <<<"$1"
  return 1
}
~~~

`chmod 755` の後、`git add --chmod=+x` で index の mode も 100755 にする。

- [ ] **Step 4: 通ることを確かめる**

Run: `bash .devcontainer/run-tests.bash .devcontainer/test-resoloop-tool.bash`
Expected: `PASS .devcontainer/test-resoloop-tool.bash`

- [ ] **Step 5: コミット**

~~~bash
git add --chmod=+x .devcontainer/resoloop-tool.bash .devcontainer/test-resoloop-tool.bash
git commit -m "feat(devcontainer): ResoLoop の版を読む関数をロックから切り離す"
~~~

### Task 2: `install_resoloop.bash` で最新の公開版を入れる

**Files:**
- Modify: `.devcontainer/install_resoloop.bash`（全体を置き換える）
- Test: `.devcontainer/test-install-resoloop.bash`（全体を置き換える）

**Interfaces:**
- Consumes: Task 1 の `resoloop_installed_version`・`resoloop_version_of`
- Produces: 出力の文言 `ResoLoop setup: installed resoloop <版>.`・`ResoLoop setup: resoloop <版> is installed (unchanged).`・`ResoLoop setup: resoloop <版> is installed (was <前の版>).`・警告 `ResoLoop setup: WARN: updating to the latest release failed (is NuGet reachable?); keeping <版>.`

- [ ] **Step 1: テストを書く**

~~~bash
#!/bin/bash
# .devcontainer/install_resoloop.bash が NuGet の最新の公開版を導入することを、モックの dotnet で検査する
# 仕様: docs/superpowers/specs/2026-10-06-issue-41-resoloop-latest-without-lock-design.md D-1〜D-3
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
tmp="$(mktemp -d)"
trap 'rm -rf -- "$tmp"' EXIT
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }

# モックの dotnet: tool update の呼び出しを DOTNET_CALLS に記録する。update は MOCK_STATE に MOCK_LATEST の版を書き、
# ~/.dotnet/tools/resoloop に版（MOCK_SHIM_VERSION があればその値）を返す shim を置く
mkdir -p "$tmp/home/.dotnet/tools" "$tmp/bin"
cat > "$tmp/bin/dotnet" <<'MOCK'
#!/bin/bash
case "$*" in
  --list-sdks)
    [ "${DOTNET_SDK_FAIL:-0}" = 0 ] || exit 20
    printf '%s\n' "${DOTNET_SDKS:-10.0.100 [/usr/share/dotnet/sdk]}" ;;
  'tool list --global')
    [ "${DOTNET_LIST_FAIL:-0}" = 0 ] || exit 15
    printf 'Package Id Version Commands\n'
    [ -z "${DOTNET_LIST_LINE:-}" ] || printf '%s\n' "$DOTNET_LIST_LINE"
    [ ! -s "$MOCK_STATE" ] || printf 'resoloop %s resoloop\n' "$(cat "$MOCK_STATE")" ;;
  'tool update --global ResoLoop --prerelease --allow-downgrade')
    printf '%s\n' "$*" >> "$DOTNET_CALLS"
    [ "${DOTNET_UPDATE_FAIL:-0}" = 0 ] || exit 16
    printf '%s\n' "$MOCK_LATEST" > "$MOCK_STATE"
    printf '#!/bin/bash\nprintf "%%s\\n" %q\n' "${MOCK_SHIM_VERSION:-$MOCK_LATEST}" > "$HOME/.dotnet/tools/resoloop"
    chmod +x "$HOME/.dotnet/tools/resoloop" ;;
  *) printf 'Unexpected dotnet invocation: %s\n' "$*" >&2; exit 17 ;;
esac
MOCK
chmod +x "$tmp/bin/dotnet"
export HOME="$tmp/home" PATH="$tmp/bin:$PATH" DOTNET_CALLS="$tmp/calls" MOCK_STATE="$tmp/installed" MOCK_LATEST=1.2.3-preview.4
installer="$root/.devcontainer/install_resoloop.bash"

installed_as() {  # $1=導入済みとして扱う版（空なら未導入）。shim もその版を返す
  : > "$DOTNET_CALLS"
  rm -f "$HOME/.dotnet/tools/resoloop"
  if [ -z "$1" ]; then
    : > "$MOCK_STATE"
    return
  fi
  printf '%s\n' "$1" > "$MOCK_STATE"
  printf '#!/bin/bash\nprintf "%%s\\n" %q\n' "$1" > "$HOME/.dotnet/tools/resoloop"
  chmod +x "$HOME/.dotnet/tools/resoloop"
}
expect_fail() {  # $1=出力に含まれるべき文字列、残り=環境変数の代入（env に渡す）
  local needle="$1"
  shift
  if env "$@" bash "$installer" > "$tmp/out.txt" 2>&1; then fail "installer succeeded (expected: $needle)"; fi
  grep -qF -- "$needle" "$tmp/out.txt" || fail "expected '$needle' in: $(cat "$tmp/out.txt")"
}
expect_ok() {  # $1=出力に含まれるべき文字列、残り=環境変数の代入（env に渡す）
  local needle="$1"
  shift
  env "$@" bash "$installer" > "$tmp/out.txt" 2>&1 || fail "installer failed (expected: $needle): $(cat "$tmp/out.txt")"
  grep -qF -- "$needle" "$tmp/out.txt" || fail "expected '$needle' in: $(cat "$tmp/out.txt")"
}
updated_once() {
  [ "$(cat "$DOTNET_CALLS")" = 'tool update --global ResoLoop --prerelease --allow-downgrade' ] \
    || fail "expected one update call, got: $(cat "$DOTNET_CALLS")"
}

# 1. 未導入: --prerelease で最新を導入し、導入した版を表示する
installed_as ''
expect_ok 'installed resoloop 1.2.3-preview.4.'
updated_once

# 2. 最新を導入済み: 同じ update を実行し、版が変わらないことを表示する
installed_as 1.2.3-preview.4
expect_ok 'resoloop 1.2.3-preview.4 is installed (unchanged).'
updated_once

# 3. fork のビルド（公開版より大きい版）を導入済み: --allow-downgrade 付きの update で最新の公開版に戻す
installed_as 1.2.3-preview.4.fork.20261006.gabc1234
expect_ok 'resoloop 1.2.3-preview.4 is installed (was 1.2.3-preview.4.fork.20261006.gabc1234).'
updated_once
[ "$(cat "$MOCK_STATE")" = 1.2.3-preview.4 ] || fail 'the fork build was not replaced'

# 4. update に失敗しても、導入済みの版があれば警告してその版のまま通す
installed_as 9.0.0
expect_ok 'keeping 9.0.0.' DOTNET_UPDATE_FAIL=1
grep -qF 'resoloop 9.0.0 is installed (unchanged).' "$tmp/out.txt" || fail 'the kept version was not reported'

# 5. update に失敗し、導入済みの版が無ければ失敗する（名前の一部だけが一致するパッケージは導入済みとみなさない）
installed_as ''
expect_fail 'installing the latest ResoLoop release from NuGet failed' DOTNET_UPDATE_FAIL=1
expect_fail 'installing the latest ResoLoop release from NuGet failed' DOTNET_UPDATE_FAIL=1 DOTNET_LIST_LINE='my-resoloop-plugin 1.0.0 other'

# 6. 導入後の resoloop --version が dotnet tool list の版と違えば失敗する
installed_as ''
expect_fail 'resoloop --version reports 0.0.2, but dotnet tool list --global reports 1.2.3-preview.4' MOCK_SHIM_VERSION=0.0.2

# 7. 前提の失敗: 一覧が取れない（何も導入しない）、SDK が無い・一覧が取れない、shim が無い
installed_as ''
expect_fail 'cannot list global .NET tools' DOTNET_LIST_FAIL=1
[ ! -s "$DOTNET_CALLS" ] || fail 'updated although the tool list failed'
expect_fail '.NET 10 SDK is not installed' 'DOTNET_SDKS=8.0.100 [/usr/share/dotnet/sdk]'
expect_fail 'cannot list .NET SDKs' DOTNET_SDK_FAIL=1
installed_as 9.0.0
rm -f "$HOME/.dotnet/tools/resoloop"
expect_fail 'installed CLI cannot run on this container' DOTNET_UPDATE_FAIL=1

printf 'PASS: ResoLoop install brings in the latest NuGet release\n'
~~~

- [ ] **Step 2: 失敗を確かめる**

Run: `bash .devcontainer/run-tests.bash .devcontainer/test-install-resoloop.bash`
Expected: FAIL（今のスクリプトはロックを読み、`--version` を指定する）

- [ ] **Step 3: 実装する**

~~~bash
#!/bin/bash
# NuGet の最新の公開版の ResoLoop を導入する。postCreate と、rebuild せずに最新へ上げるときに実行する。
# 仕様: docs/superpowers/specs/2026-10-06-issue-41-resoloop-latest-without-lock-design.md D-1〜D-3
# 公開版は今はプレリリースだけなので --prerelease を付ける。fork のビルド（公開版より大きい版になり得る）からも
# 戻せるよう --allow-downgrade を付ける。update は未導入なら導入する。
# NuGet に届かないなどで更新できなくても、導入済みの版があれば警告してその版のまま続ける。
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fail() { printf 'ResoLoop setup: %s\n' "$1" >&2; exit 1; }
# shellcheck source=resoloop-tool.bash
source "$root/.devcontainer/resoloop-tool.bash"

command -v dotnet >/dev/null 2>&1 || fail 'dotnet is not available.'
sdks="$(dotnet --list-sdks </dev/null)" || fail 'cannot list .NET SDKs.'
grep -qE '^10\.' <<<"$sdks" || fail '.NET 10 SDK is not installed.'
before="$(resoloop_installed_version)" || fail 'cannot list global .NET tools.'

if ! dotnet tool update --global ResoLoop --prerelease --allow-downgrade </dev/null; then
    [ -n "$before" ] || fail 'installing the latest ResoLoop release from NuGet failed.'
    printf 'ResoLoop setup: WARN: updating to the latest release failed (is NuGet reachable?); keeping %s.\n' "$before" >&2
fi

installed="$(resoloop_installed_version)" || fail 'cannot list global .NET tools.'
[ -n "$installed" ] || fail 'ResoLoop is missing from dotnet tool list --global after the update.'
# PATH 上の別の resoloop で誤って通らないよう、グローバルツールの配置先を直接呼ぶ
out="$("$HOME/.dotnet/tools/resoloop" --version </dev/null)" || fail 'installed CLI cannot run on this container.'
actual="$(resoloop_version_of "$out")" || fail 'resoloop --version printed nothing.'
[ "$actual" = "$installed" ] || fail "resoloop --version reports $actual, but dotnet tool list --global reports $installed."
if [ -z "$before" ]; then
    printf 'ResoLoop setup: installed resoloop %s.\n' "$actual"
elif [ "$before" = "$actual" ]; then
    printf 'ResoLoop setup: resoloop %s is installed (unchanged).\n' "$actual"
else
    printf 'ResoLoop setup: resoloop %s is installed (was %s).\n' "$actual" "$before"
fi
~~~

- [ ] **Step 4: 通ることを確かめる**

Run: `bash .devcontainer/run-tests.bash .devcontainer/test-install-resoloop.bash`
Expected: PASS

- [ ] **Step 5: コミット**

~~~bash
git add .devcontainer/install_resoloop.bash .devcontainer/test-install-resoloop.bash
git commit -m "feat(devcontainer): postCreate で NuGet の最新の公開版の ResoLoop を入れる"
~~~

### Task 3: `verify-resonite-tooling.bash` からロックを外す

**Files:**
- Modify: `.devcontainer/verify-resonite-tooling.bash`
- Test: `.devcontainer/test-verify-resonite-tooling.bash`（全体を置き換える）

**Interfaces:**
- Produces: 成功時の出力 `Toolchain verification: resoloop <版>`、失敗時の `Toolchain verification: resoloop --version printed nothing.`

- [ ] **Step 1: テストを書く**（postCreate の手順名の固定文字列の検査は書かない）

~~~bash
#!/bin/bash
# .devcontainer/verify-resonite-tooling.bash（.NET 10 SDK・resoloop・Blender の確認）と、postCreate からの呼び出しを検査する
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
tmp="$(mktemp -d)"
trap 'rm -rf -- "$tmp"' EXIT
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
mkdir -p "$tmp/bin"
cat > "$tmp/bin/dotnet" <<'MOCK'
#!/bin/bash
[ "$*" = '--list-sdks' ] || exit 11
printf '10.0.100 [/usr/share/dotnet/sdk]\n'
MOCK
cat > "$tmp/bin/resoloop" <<'MOCK'
#!/bin/bash
[ "$*" = '--version' ] || exit 12
[ "${RESOLOOP_FAIL:-0}" = 0 ] || exit 15
printf '%s\n' "$MOCK_RESOLOOP_VERSION"
MOCK
cat > "$tmp/bin/blender" <<'MOCK'
#!/bin/bash
case " $* " in *' --background '*' --python-expr '*) ;; *) exit 13 ;; esac
[ "${BLENDER_FAIL:-0}" = 0 ] || exit 14
MOCK
chmod +x "$tmp/bin/"*
export PATH="$tmp/bin:$PATH" MOCK_RESOLOOP_VERSION=1.2.3-preview.4
verify="$root/.devcontainer/verify-resonite-tooling.bash"

# 1. resoloop が版を表示すれば通り、確かめた版を表示する（版の値は比べない）
out="$(bash "$verify" 2>&1)" || fail "verification failed: $out"
grep -qF 'Toolchain verification: resoloop 1.2.3-preview.4' <<<"$out" || fail "the checked version was not shown: $out"
# 2. resoloop が動かない・版を表示しない、Blender が動かないときは失敗する
if RESOLOOP_FAIL=1 bash "$verify" 2>/dev/null; then fail 'passed although resoloop cannot run'; fi
if out="$(MOCK_RESOLOOP_VERSION='' bash "$verify" 2>&1)"; then fail 'passed although resoloop printed no version'; fi
grep -qF 'resoloop --version printed nothing' <<<"$out" || fail "unexpected message: $out"
if BLENDER_FAIL=1 bash "$verify" 2>/dev/null; then fail 'passed although Blender cannot run'; fi

# 3. postCreate が導入と確認を呼び、宣言した手順の数が実際の手順の数と同じ
installer="$root/.devcontainer/install_beforehand.bash"
for s in 'bash .devcontainer/install_resoloop.bash' 'bash .devcontainer/verify-resonite-tooling.bash'; do
  grep -qF -- "$s" "$installer" || fail "install_beforehand.bash does not run: $s"
done
declared_steps="$(sed -n 's/^readonly STEP_TOTAL=//p' "$installer")"
actual_steps="$(grep -c '^step "' "$installer")"
[ "$declared_steps" -eq "$actual_steps" ] || fail "STEP_TOTAL is $declared_steps, but there are $actual_steps steps"
grep -qF 'PATH="$HOME/.dotnet/tools:$PATH"' "$root/.devcontainer/zshrc.txt" || fail 'zshrc.txt does not put ~/.dotnet/tools on PATH'
printf 'PASS: toolchain smoke test and postCreate integration\n'
~~~

- [ ] **Step 2: 失敗を確かめる**

Run: `bash .devcontainer/run-tests.bash .devcontainer/test-verify-resonite-tooling.bash`
Expected: FAIL（今のスクリプトはロックの版 `0.1.0-preview.15` と比べるので `1.2.3-preview.4` で失敗する）

- [ ] **Step 3: 実装する**

~~~bash
#!/bin/bash
# Resonite の開発ツール（.NET 10 SDK・resoloop・Blender）が動くことを確かめる。postCreate の確認と手動の確認に使う。
# ResoLoop は版を固定せず最新を使うので、版の値は比べず、動いて版を表示することだけを確かめる
# （仕様: docs/superpowers/specs/2026-10-06-issue-41-resoloop-latest-without-lock-design.md D-4）
set -euo pipefail

# 一覧を変数に取ってから探す（pipefail の下で grep -q が dotnet を SIGPIPE で止めないように）
if ! sdks="$(dotnet --list-sdks </dev/null)" || ! grep -qE '^10\.' <<<"$sdks"; then
    echo 'Toolchain verification: .NET 10 SDK is unavailable.' >&2
    exit 1
fi
if ! version_output="$(resoloop --version </dev/null)"; then
    echo 'Toolchain verification: resoloop cannot run.' >&2
    exit 1
fi
version="$(sed -n '/[^[:space:]]/{s/^[[:space:]]*//;s/[[:space:]]*$//;p;q;}' <<<"$version_output")"
if [ -z "$version" ]; then
    echo 'Toolchain verification: resoloop --version printed nothing.' >&2
    exit 1
fi
printf 'Toolchain verification: resoloop %s\n' "$version"
if ! blender --background --factory-startup --python-exit-code 1 \
    --python-expr 'import bpy; assert bpy.app.background' </dev/null; then
    echo 'Toolchain verification: Blender cannot run headlessly.' >&2
    exit 1
fi
~~~

- [ ] **Step 4: 通ることを確かめる**

Run: `bash .devcontainer/run-tests.bash .devcontainer/test-verify-resonite-tooling.bash`
Expected: PASS

- [ ] **Step 5: コミット**

~~~bash
git add .devcontainer/verify-resonite-tooling.bash .devcontainer/test-verify-resonite-tooling.bash
git commit -m "feat(devcontainer): ツールの確認で ResoLoop の版をロックと比べない"
~~~

### Task 4: postCreate で各プロジェクトの同梱スキルの状態を表示する

**Files:**
- Create: `.devcontainer/report-resoloop-skills.bash`（100755）
- Modify: `.devcontainer/install_beforehand.bash:3-11`（冒頭のコメントと `STEP_TOTAL`）、`:88-97`（ResoLoop の手順）
- Modify: `.devcontainer/test-verify-resonite-tooling.bash`（配線の検査に 1 件足す）
- Test: `.devcontainer/test-report-resoloop-skills.bash`（新規、100755）

**Interfaces:**
- Produces: 出力 `ResoLoop skills: <p>: up to date`・`ResoLoop skills: <p>: the installed resoloop bundles newer skills. …`・`ResoLoop skills: <p>: the check failed (exit <n>). …`・`ResoLoop skills: resoloop not found; skipped the check.`。終了コードは常に 0

- [ ] **Step 1: テストを書く**

~~~bash
#!/bin/bash
# .devcontainer/report-resoloop-skills.bash が、各プロジェクトの resoloop skills sync --check の結果を表示し、
# 差分や失敗があっても 0 で終わることを、一時リポジトリとモックの resoloop で検査する
# 仕様: docs/superpowers/specs/2026-10-06-issue-41-resoloop-latest-without-lock-design.md D-12
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
tmp="$(cd "$(mktemp -d)" && pwd -P)"
trap 'rm -rf -- "$tmp"' EXIT
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null
export GIT_AUTHOR_NAME=test GIT_AUTHOR_EMAIL=test@example.com GIT_COMMITTER_NAME=test GIT_COMMITTER_EMAIL=test@example.com

# 一時リポジトリ: 直下のプロジェクト ok・stale・edited・-dash と、プロジェクトでないもの（ネストした deep/sub、追跡していない loose）
repo="$tmp/repo"
git init -q "$repo"
mkdir -p "$repo/.devcontainer"
cp "$root/.devcontainer/report-resoloop-skills.bash" "$repo/.devcontainer/"
for p in ok stale edited -dash deep/sub loose; do
  mkdir -p "$repo/$p" && printf '{}\n' > "$repo/$p/.resoloop.json"
done
git -C "$repo" add -- .devcontainer ok stale edited -dash deep
git -C "$repo" commit -q -m init

# モックの resoloop: 呼び出しを MOCK_LOG に記録し、プロジェクトごとに実物と同じ形の結果を返す
mkdir -p "$tmp/bin"
cat > "$tmp/bin/resoloop" <<'EOF'
#!/bin/bash
printf '%s (cwd=%s)\n' "$*" "$PWD" >> "$MOCK_LOG"
[ "$1 $2 $4" = 'skills sync --check' ] || exit 64
case "$3" in
  ./ok|./-dash) exit 0 ;;
  ./stale)
    printf 'SKILL_SYNC_REQUIRED: Bundled skills or their lock need synchronization.\n  next: Review the reported paths, then run resoloop skills sync --update.\n' >&2
    exit 6 ;;
  ./edited)
    printf 'SKILL_SYNC_CONFLICT: Bundled skill sync stopped because one or more installed skills are modified or have no trusted lock.\n' >&2
    exit 6 ;;
  *) printf 'unexpected project %s\n' "$3" >&2; exit 65 ;;
esac
EOF
chmod +x "$tmp/bin/resoloop"
export MOCK_LOG="$tmp/calls"
: > "$MOCK_LOG"
report="$repo/.devcontainer/report-resoloop-skills.bash"

# 1. 別の cwd から実行しても、リポジトリのルートで各プロジェクトを確かめ、結果にかかわらず 0 で終わる
out="$(cd "$tmp" && PATH="$tmp/bin:$PATH" bash "$report" 2>&1)" || fail "the report failed: $out"
for s in 'ResoLoop skills: ok: up to date' 'ResoLoop skills: -dash: up to date' \
  'ResoLoop skills: stale: the installed resoloop bundles newer skills' '    SKILL_SYNC_REQUIRED: Bundled skills' \
  'ResoLoop skills: edited: the check failed (exit 6)' '    SKILL_SYNC_CONFLICT: Bundled skill sync stopped'; do
  grep -qF -- "$s" <<<"$out" || fail "the report lacks '$s': $out"
done
# 2. プロジェクトは .resoloop.json を追跡している直下のディレクトリだけで、resoloop には ./ 付きで渡す
[ "$(cut -d' ' -f3 "$MOCK_LOG" | LC_ALL=C sort | tr '\n' ' ')" = './-dash ./edited ./ok ./stale ' ] \
  || fail "unexpected projects: $(cat "$MOCK_LOG")"
grep -qF "(cwd=$repo)" "$MOCK_LOG" || fail 'resoloop did not run at the repository root'
# 3. resoloop が無ければ、表示して 0 で終わる
if PATH=/usr/bin:/bin command -v resoloop >/dev/null 2>&1; then fail 'resoloop is visible on PATH=/usr/bin:/bin'; fi
out="$(PATH=/usr/bin:/bin bash "$report" 2>&1)" || fail "the report failed without resoloop: $out"
grep -qF 'ResoLoop skills: resoloop not found; skipped the check.' <<<"$out" || fail "unexpected output without resoloop: $out"

printf 'PASS: postCreate reports the bundled skill state of each project without failing\n'
~~~

`test-verify-resonite-tooling.bash` の手順 3 の一覧に `'bash .devcontainer/report-resoloop-skills.bash'` を足す。

- [ ] **Step 2: 失敗を確かめる**

Run: `bash .devcontainer/run-tests.bash .devcontainer/test-report-resoloop-skills.bash .devcontainer/test-verify-resonite-tooling.bash`
Expected: 2 本とも FAIL（スクリプトが無い、postCreate が呼んでいない）

- [ ] **Step 3: 実装する**

`.devcontainer/report-resoloop-skills.bash`:

~~~bash
#!/bin/bash
# 各プロジェクト（.resoloop.json を追跡している直下のディレクトリ。scripts/check-layout.sh の collect_projects と同じ定義）で
# resoloop skills sync --check を実行し、結果を表示する。
# 仕様: docs/superpowers/specs/2026-10-06-issue-41-resoloop-latest-without-lock-design.md D-12
# postCreate から呼ぶ。同梱スキルの同期は手動で行う（AGENTS.md の「プロジェクト運用」）ので、差分や失敗があっても常に 0 で終わる
set -uo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
say() { printf 'ResoLoop skills: %s\n' "$1"; }
relay() { [ -z "$1" ] || printf '%s\n' "$1" | sed 's/^/    /'; }

if ! command -v resoloop >/dev/null 2>&1; then
    say 'resoloop not found; skipped the check.'
    exit 0
fi
if ! cd -- "$root" || ! git rev-parse --git-dir >/dev/null 2>&1; then
    say "cannot list the projects ($root is not a git checkout); skipped the check."
    exit 0
fi
projects=()
while IFS= read -r -d '' path; do
    [[ "$path" =~ ^[^/]+/\.resoloop\.json$ ]] && projects+=("${path%%/*}")
done < <(git ls-files -z -- '*/.resoloop.json')
if [ ${#projects[@]} -eq 0 ]; then
    say 'no projects found.'
    exit 0
fi
for p in "${projects[@]}"; do
    status=0
    # ./ を付けて、- で始まるプロジェクト名をオプションとして読ませない
    out="$(resoloop skills sync "./$p" --check </dev/null 2>&1)" || status=$?
    if [ "$status" -eq 0 ]; then
        say "$p: up to date"
    elif [ "$status" -eq 6 ] && [[ "$out" == SKILL_SYNC_REQUIRED* ]]; then
        say "$p: the installed resoloop bundles newer skills. Review the differences with 'resoloop skills sync --check' in $p, then run 'resoloop skills sync --update'."
        relay "$out"
    else
        say "$p: the check failed (exit $status). Resolve it before running 'resoloop skills sync --update'."
        relay "$out"
    fi
done
exit 0
~~~

`.devcontainer/install_beforehand.bash`:

- 冒頭のコメント「継続してよい処理（workspace cleanup）だけを」を「継続してよい処理（同梱スキルの状態の表示と workspace cleanup）だけを」にする
- `readonly STEP_TOTAL=25` を `26` にする
- ResoLoop の 3 手順を次にする

~~~bash
step "Installing the latest ResoLoop release from NuGet"
export PATH="${HOME}/.dotnet/tools:${PATH}"
if ! bash .devcontainer/install_resoloop.bash; then
    fail "ResoLoop installation or update failed."
fi

step "Verifying the Resonite development toolchain"
if ! bash .devcontainer/verify-resonite-tooling.bash; then
    fail "Resonite development toolchain verification failed."
fi

step "Reporting the bundled ResoLoop skills of each project"
# 同梱スキルの同期は手動で行う（AGENTS.md の「プロジェクト運用」）。結果を表示するだけで、差分があっても続ける
if ! bash .devcontainer/report-resoloop-skills.bash; then
    warn "Reporting the bundled ResoLoop skills failed; continuing."
fi
~~~

- [ ] **Step 4: 通ることを確かめる**

Run: `bash .devcontainer/run-tests.bash .devcontainer/test-report-resoloop-skills.bash .devcontainer/test-verify-resonite-tooling.bash .devcontainer/test-install-beforehand.bash`
Expected: 3 本とも PASS

- [ ] **Step 5: コミット**

~~~bash
git add --chmod=+x .devcontainer/report-resoloop-skills.bash .devcontainer/test-report-resoloop-skills.bash
git add .devcontainer/install_beforehand.bash .devcontainer/test-verify-resonite-tooling.bash
git commit -m "feat(devcontainer): postCreate で各プロジェクトの同梱スキルの状態を表示する"
~~~

### Task 5: `check-layout.sh` の検査 7 を変え、検査 8 を外す

**Files:**
- Modify: `scripts/check-layout.sh:1-7`（冒頭のコメント）、`:265-280`（検査 7）、`:283-331`（検査 8 と検査 9 のコメント）、`:363-367`（呼び出し）
- Test: `tests/scripts/test-check-layout.bash:200-231`（モックと 23）、`:348-...`（43〜54）

**Interfaces:**
- Produces: 出力 `warn: resoloop skills sync --check (<p>): the installed resoloop bundles newer skills; review them, then run resoloop skills sync --update`

- [ ] **Step 1: テストを書き換える**

モックの resoloop に、`MOCK_RESOLOOP_CONFLICT` と同名のプロジェクトだけ `SKILL_SYNC_CONFLICT` で 6 を返す分岐を足す:

~~~bash
case "$3" in "${MOCK_RESOLOOP_CONFLICT:-__none__}"|*/"${MOCK_RESOLOOP_CONFLICT:-__none__}") echo 'SKILL_SYNC_CONFLICT' >&2; exit 6 ;; esac
~~~

23 を次にする:

~~~bash
# 23. 新しい版による同梱スキルの更新（SKILL_SYNC_REQUIRED）は warn を表示して通過し、手で編集した同梱スキル
#     （SKILL_SYNC_CONFLICT）は失敗する。どちらも resoloop の出力を字下げして示す
PATH="$mock_path" MOCK_RESOLOOP_FAIL=demo bash "$checker" --root "$tmp/proj-ok" > "$tmp/proj-drift.out" 2>&1 \
  || { cat "$tmp/proj-drift.out" >&2; printf 'FAIL: an outdated bundled skill failed check-layout\n' >&2; exit 1; }
grep -qF 'warn: resoloop skills sync --check (demo)' "$tmp/proj-drift.out" || { cat "$tmp/proj-drift.out" >&2; printf 'FAIL: no warn line\n' >&2; exit 1; }
grep -qxF '    SKILL_SYNC_REQUIRED' "$tmp/proj-drift.out" || { cat "$tmp/proj-drift.out" >&2; printf 'FAIL: resoloop output was not relayed\n' >&2; exit 1; }
grep -qF 'PASS: check-layout' "$tmp/proj-drift.out"
PATH="$mock_path" MOCK_RESOLOOP_CONFLICT=demo expect_fail_with "$tmp/proj-ok" 'resoloop skills sync --check failed for demo'
grep -qxF '    SKILL_SYNC_CONFLICT' "$tmp/out.txt" || { cat "$tmp/out.txt" >&2; printf 'FAIL: resoloop output was not relayed\n' >&2; exit 1; }
~~~

`lock_repo` を `devcontainer_repo` に改め、`resoloop-lock.bash` のコピーとロックの作成を外す（devcontainer.json の `additionalVersions` と mounts、`mounts.bash`、`initialize.bash` は残す）。43〜52 を次にする（53・54 は `lock_repo` を `devcontainer_repo` に置き換えるだけ）:

~~~bash
# 43. .devcontainer を持つリポジトリは mount を検査して通過する。devcontainer.json を追跡していないリポジトリでは skip を表示する
devcontainer_repo "$tmp/dc-ok"
bash "$checker" --root "$tmp/dc-ok" > "$tmp/dc-ok.out"
grep -qF 'ok: mounts match .devcontainer/initialize.bash' "$tmp/dc-ok.out"
grep -qF 'PASS: check-layout' "$tmp/dc-ok.out"
bash "$checker" --root "$tmp/clean" > "$tmp/dc-skip.out"
grep -qF 'skip: .devcontainer/devcontainer.json is not tracked (mount check)' "$tmp/dc-skip.out"

# 44. このリポジトリの mounts も検査される
bash "$checker" > "$tmp/self.out"
grep -qF 'ok: mounts match .devcontainer/initialize.bash' "$tmp/self.out"

# 45. devcontainer.json が作業ツリーにあっても追跡していなければ skip
devcontainer_repo "$tmp/dc-untracked" && git -C "$tmp/dc-untracked" rm -q --cached .devcontainer/devcontainer.json \
  && git -C "$tmp/dc-untracked" commit -q -m untrack
[ -f "$tmp/dc-untracked/.devcontainer/devcontainer.json" ] || { printf 'FAIL: case 45 lost the untracked file\n' >&2; exit 1; }
bash "$checker" --root "$tmp/dc-untracked" > "$tmp/dc-untracked.out"
grep -qF 'skip: .devcontainer/devcontainer.json is not tracked (mount check)' "$tmp/dc-untracked.out"

# 46. 衝突の解決中（ステージ 0 に無い）の .devcontainer のファイルは、終了コード 1 で解決を促す（128 で止まらない）
devcontainer_repo "$tmp/dc-conflict"
git -C "$tmp/dc-conflict" checkout -q -b other
printf '# other\n' >> "$tmp/dc-conflict/.devcontainer/initialize.bash" && commit_paths "$tmp/dc-conflict" .devcontainer
git -C "$tmp/dc-conflict" checkout -q -
printf '# mine\n' >> "$tmp/dc-conflict/.devcontainer/initialize.bash" && commit_paths "$tmp/dc-conflict" .devcontainer
if git -C "$tmp/dc-conflict" merge -q other >/dev/null 2>&1; then printf 'FAIL: case 46 merged without a conflict\n' >&2; exit 1; fi
expect_fail_with "$tmp/dc-conflict" '.devcontainer/initialize.bash has unresolved merge conflicts'

# 47. index から読めない blob（壊れたオブジェクト）は、終了コード 1 の FAIL として報告する
remove_object() {  # $1=リポジトリ、$2=パス。index にある blob のオブジェクトファイルを消す
  local oid
  oid="$(git -C "$1" rev-parse ":$2")"
  rm -f "$1/.git/objects/${oid:0:2}/${oid:2}"
}
devcontainer_repo "$tmp/dc-corrupt" && remove_object "$tmp/dc-corrupt" .devcontainer/initialize.bash
expect_fail_with "$tmp/dc-corrupt" 'cannot read .devcontainer/initialize.bash from the index'
skill_repo "$tmp/link-corrupt"
ln -s ../../.agents/skills/foo "$tmp/link-corrupt/.claude/skills/foo"
commit_paths "$tmp/link-corrupt" .agents .claude
remove_object "$tmp/link-corrupt" .claude/skills/foo
expect_fail_with "$tmp/link-corrupt" 'cannot read the target of .claude/skills/foo from the index'
~~~

続く mount の 2 件は番号を 48・49 に詰める。

- [ ] **Step 2: 失敗を確かめる**

Run: `bash .devcontainer/run-tests.bash tests/scripts/test-check-layout.bash`
Expected: FAIL（23 で同期ずれが FAIL になる）

- [ ] **Step 3: 実装する**

検査 7 を次にする:

~~~bash
# 7. resoloop が使える環境では、各プロジェクトで resoloop skills sync --check を実行する（resoloop は作業ツリーを読む）。
# 導入済みの resoloop が新しい同梱スキルを持つだけ（SKILL_SYNC_REQUIRED）なら warn を表示して通過する。ResoLoop は常に最新を
# 入れるので、上流のリリースのたびに起きるため（仕様: docs/superpowers/specs/2026-10-06-issue-41-resoloop-latest-without-lock-design.md D-13）。
# 手で編集した同梱スキル（SKILL_SYNC_CONFLICT）などそれ以外の失敗は FAIL にする。どちらも resoloop の出力を字下げして示す
check_resoloop_skills() {
  local p out status
  if ! command -v resoloop >/dev/null 2>&1; then
    printf 'skip: resoloop not found (skills sync check)\n'
    return
  fi
  for p in ${projects[@]+"${projects[@]}"}; do
    status=0
    # ./ を付けて、- で始まるプロジェクト名をオプションとして読ませない
    out="$(resoloop skills sync "./$p" --check 2>&1)" || status=$?
    if [ "$status" -eq 0 ]; then
      ok "resoloop skills sync --check ($p)"
    elif [ "$status" -eq 6 ] && [[ "$out" == SKILL_SYNC_REQUIRED* ]]; then
      printf 'warn: resoloop skills sync --check (%s): the installed resoloop bundles newer skills; review them, then run resoloop skills sync --update\n' "$p"
      printf '%s\n' "$out" | sed 's/^/    /'
    else
      fail "resoloop skills sync --check failed for $p"
      [ -z "$out" ] || printf '%s\n' "$out" | sed 's/^/    /' >&2
    fi
  done
}
~~~

- `check_resoloop_lock` と `validate_lock` を削除し、呼び出しの `check_resoloop_lock` の行も削除する
- 検査 9（mount）の見出しのコメントを `# 8.` にする。`extract_devcontainer_files` のコメント「（検査 8・9 が使う）」を「（検査 8 が使う）」にする
- 冒頭のコメントの「（検査 1・4・5・6・8・9）」を「（検査 1・4・5・6・8）」にする

- [ ] **Step 4: 通ることを確かめる**

Run: `bash .devcontainer/run-tests.bash tests/scripts/test-check-layout.bash`
Expected: PASS

- [ ] **Step 5: コミット**

~~~bash
git add scripts/check-layout.sh tests/scripts/test-check-layout.bash
git commit -m "feat(check-layout): 同梱スキルの更新は warn にし、ロックの検査を外す"
~~~

### Task 6: `resoloop-fork.sh` をロック無しで動かす

**Files:**
- Modify: `scripts/resoloop-fork.sh`（全体を置き換える）
- Test: `tests/scripts/test-resoloop-fork.bash`（全体を置き換える）

**Interfaces:**
- Consumes: Task 1 の関数
- Produces: 使い方 `resoloop-fork.sh <clone|sync|build|test|status>` と `resoloop-fork.sh <checkout|install> <ref>`。出力 `checked out: <dir> at <sha> (<解決した名前>, detached)`、`built: <dir>/artifacts/fork/ResoLoop.<版>.nupkg`、`installed version: <版> (NuGet release|fork build)`、`return to the latest NuGet release: bash .devcontainer/install_resoloop.bash`

- [ ] **Step 1: テストを書く**

~~~bash
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
trap 'rm -rf -- "$tmp"' EXIT
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

# 9. 追跡ファイルに未コミットの変更があれば 1 で、HEAD を動かさない。未追跡ファイルは妨げない
git -C "$co" checkout -q main
printf 'local edit\n' >> "$co/file.txt"
expect_exit 1 'has uncommitted changes to tracked files' checkout fix/x
[ "$(git -C "$co" symbolic-ref --short HEAD)" = main ] || fail 'checkout moved HEAD despite local changes'
git -C "$co" checkout -q -- file.txt
printf 'notes\n' > "$co/untracked.txt"
expect_exit 0 "checked out: $co at $fix_commit (origin/fix/x, detached)" checkout fix/x
rm "$co/untracked.txt"

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
~~~

- [ ] **Step 2: 失敗を確かめる**

Run: `bash .devcontainer/run-tests.bash tests/scripts/test-resoloop-fork.bash`
Expected: FAIL（今のスクリプトはロックが無いと 3 で止まり、`checkout <ref>` を受け付けない）

- [ ] **Step 3: 実装する**

~~~bash
#!/bin/bash
# ResoLoop の fork を取得・追従・checkout・ビルド・テストし、fork のビルドを一時的に導入する。
# 仕様: docs/superpowers/specs/2026-10-06-issue-41-resoloop-latest-without-lock-design.md D-5〜D-10。運用手順: docs/resoloop-fork-workflow.md
# 使い方: scripts/resoloop-fork.sh <clone|sync|build|test|status>
#         scripts/resoloop-fork.sh <checkout|install> <ref>
#   <ref> は fork（origin）のブランチ名。origin に無い名前は、git がそのまま解決できる名前（コミット、タグ、ローカルのブランチ、
#   upstream/main など）として扱う
# fork のビルドの導入は一時的な上書きで、次の rebuild か bash .devcontainer/install_resoloop.bash で最新の公開版に戻る。
# 環境変数（テストと特殊な運用向け）:
#   RESOLOOP_CHECKOUT      fork の checkout 先（既定: <リポジトリ>/external/resoloop）
#   RESOLOOP_ORIGIN_URL    origin の URL（既定: https://github.com/usaturn/resoloop.git）
#   RESOLOOP_UPSTREAM_URL  upstream の URL（既定: https://github.com/orange3134/resoloop.git）
# 終了コード:
#   0 成功
#   1 状態が期待と違う（git の checkout でない、remote の URL、未コミットの変更、ref を解決できない、
#     fork の main が上流から分岐、csproj の版を読めない、導入後の版の不一致）
#   2 使い方の誤り
#   3 前提不足（git / dotnet が無い、global.json が要求する SDK が無い、checkout が無い）
#   4 外部コマンドの失敗（git clone / fetch / push / checkout、dotnet build / pack / test / tool）
set -euo pipefail

usage() {
  printf 'usage: %s <clone|sync|build|test|status>\n       %s <checkout|install> <ref>\n' "${BASH_SOURCE[0]}" "${BASH_SOURCE[0]}" >&2
  exit 2
}
die() { printf 'ERROR: %s\n' "$2" >&2; exit "$1"; }
run() {  # $1=失敗時に表示する名前、残り=コマンド。失敗したら終了コード 4
  local what="$1"
  shift
  "$@" || die 4 "$what failed"
}

[ $# -ge 1 ] || usage
cmd="$1" ref=""
case "$cmd" in
  clone|sync|build|test|status) [ $# -eq 1 ] || usage ;;
  checkout|install)
    [ $# -eq 2 ] && [ -n "$2" ] || usage
    case "$2" in -*) usage ;; esac
    ref="$2" ;;
  *) usage ;;
esac

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# 相対パスの RESOLOOP_CHECKOUT は呼び出し時の cwd を基準に絶対パスにする（install は $root に cd してから
# --add-source を渡すため）。symlink は解決しない
dir="$(realpath -ms -- "${RESOLOOP_CHECKOUT:-$root/external/resoloop}")"
origin_url="${RESOLOOP_ORIGIN_URL:-https://github.com/usaturn/resoloop.git}"
upstream_url="${RESOLOOP_UPSTREAM_URL:-https://github.com/orange3134/resoloop.git}"
# shellcheck source=../.devcontainer/resoloop-tool.bash
source "$root/.devcontainer/resoloop-tool.bash"
command -v git >/dev/null 2>&1 || die 3 "git not found"

same_url() {  # 末尾の / と .git の有無だけが違う URL は同じとみなす
  local a="${1%/}" b="${2%/}"
  [ "${a%.git}" = "${b%.git}" ]
}

is_checkout() {  # $dir がそれ自体 git の checkout のルートなら 0（外側のリポジトリのサブディレクトリは 1）
  local top
  [ -d "$dir" ] || return 1
  top="$(git -C "$dir" rev-parse --show-toplevel 2>/dev/null)" || return 1
  [ "$(cd "$top" && pwd -P)" = "$(cd "$dir" && pwd -P)" ]
}

not_a_checkout="exists but is not a git checkout of its own; remove it (or move a checkout there) and rerun scripts/resoloop-fork.sh clone"

require_checkout() {
  [ -e "$dir" ] || [ -L "$dir" ] || die 3 "$dir is missing; run scripts/resoloop-fork.sh clone"
  is_checkout || die 1 "$dir $not_a_checkout"
}

check_remotes() {  # origin と upstream を期待する URL と比べ、食い違いを 1 件 1 行で出力する。食い違いがあれば 1
  local name want got bad=0
  for name in origin upstream; do
    if [ "$name" = origin ]; then want="$origin_url"; else want="$upstream_url"; fi
    if ! got="$(git -C "$dir" remote get-url "$name" 2>/dev/null)"; then
      printf 'remote %s is missing (expected %s)\n' "$name" "$want"
      bad=1
    elif ! same_url "$got" "$want"; then
      printf 'remote %s is %s (expected %s)\n' "$name" "$got" "$want"
      bad=1
    fi
  done
  return "$bad"
}

require_remotes() {
  local problems
  if ! problems="$(check_remotes)"; then
    printf '%s\n' "$problems" >&2
    die 1 "$dir has unexpected remotes; fix them with git remote add/set-url (see docs/resoloop-fork-workflow.md)"
  fi
}

dirty() {  # 追跡ファイルに未コミットの変更があれば 0（未追跡ファイルは数えない）
  [ -n "$(git -C "$dir" status --porcelain --untracked-files=no)" ]
}

do_clone() {
  if [ -e "$dir" ] || [ -L "$dir" ]; then
    is_checkout || die 1 "$dir $not_a_checkout"
    require_remotes
    printf 'ok: %s is already cloned (origin and upstream are as expected)\n' "$dir"
    return
  fi
  run 'git clone' git clone --quiet --origin origin -- "$origin_url" "$dir"
  run 'git remote add upstream' git -C "$dir" remote add upstream "$upstream_url"
  run 'git fetch upstream' git -C "$dir" fetch --quiet upstream
  printf 'cloned: %s (origin %s, upstream %s)\n' "$dir" "$origin_url" "$upstream_url"
}

do_sync() {
  local up origin_main local_main
  require_checkout
  require_remotes
  run 'git fetch upstream' git -C "$dir" fetch --quiet upstream
  run 'git fetch origin' git -C "$dir" fetch --quiet origin
  up="$(git -C "$dir" rev-parse --verify -q refs/remotes/upstream/main)" || die 1 "upstream has no main branch"
  origin_main="$(git -C "$dir" rev-parse --verify -q refs/remotes/origin/main)" || die 1 "origin has no main branch"
  if [ "$origin_main" = "$up" ]; then
    printf 'ok: origin/main already matches upstream/main (%s)\n' "$up"
  elif git -C "$dir" merge-base --is-ancestor "$origin_main" "$up"; then
    run 'git push origin main' git -C "$dir" push --quiet origin "$up:refs/heads/main"
    printf 'pushed: origin/main %s -> %s\n' "$origin_main" "$up"
  else
    die 1 "origin/main has commits that upstream/main lacks; the fork's main only mirrors upstream, so move those commits to a branch before syncing"
  fi
  # ローカルの main があれば同じく fast-forward する
  local_main="$(git -C "$dir" rev-parse --verify -q refs/heads/main)" || return 0
  [ "$local_main" != "$up" ] || return 0
  git -C "$dir" merge-base --is-ancestor "$local_main" "$up" \
    || die 1 "local main has commits that upstream/main lacks; left it unchanged"
  if [ "$(git -C "$dir" symbolic-ref -q --short HEAD || true)" = main ]; then
    dirty && die 1 "$dir has uncommitted changes on main; local main was left unchanged (origin/main is already synced)"
    run 'git merge --ff-only' git -C "$dir" merge --quiet --ff-only "$up"
  else
    run 'git branch -f main' git -C "$dir" branch --quiet -f main "$up"
  fi
  printf 'updated: local main -> %s\n' "$up"
}

resolved_commit="" resolved_name=""
resolve_ref() {  # origin と upstream を fetch し、$ref を resolved_commit と resolved_name に解決する（origin のブランチを優先）
  run 'git fetch origin' git -C "$dir" fetch --quiet --prune origin
  run 'git fetch upstream' git -C "$dir" fetch --quiet upstream
  if resolved_commit="$(git -C "$dir" rev-parse --verify -q "refs/remotes/origin/$ref^{commit}")"; then
    resolved_name="origin/$ref"
  elif resolved_commit="$(git -C "$dir" rev-parse --verify -q "$ref^{commit}")"; then
    resolved_name="$ref"
  else
    die 1 "cannot resolve $ref: it is neither a branch on origin ($origin_url) nor a name git can resolve in $dir"
  fi
}

do_checkout() {
  require_checkout
  require_remotes
  dirty && die 1 "$dir has uncommitted changes to tracked files; commit or stash them before checking out $ref"
  resolve_ref
  if [ "$(git -C "$dir" rev-parse HEAD)" = "$resolved_commit" ] && ! git -C "$dir" symbolic-ref -q HEAD >/dev/null; then
    printf 'ok: %s is already at %s (%s, detached)\n' "$dir" "$resolved_commit" "$resolved_name"
    return
  fi
  run 'git checkout' git -C "$dir" checkout --quiet --detach "$resolved_commit"
  printf 'checked out: %s at %s (%s, detached)\n' "$dir" "$resolved_commit" "$resolved_name"
}

require_sdk() {  # checkout の global.json が要求する SDK があることを確かめる（rollForward を含む解決は dotnet に任せる）
  local want
  command -v dotnet >/dev/null 2>&1 || die 3 "dotnet not found"
  (cd "$dir" && dotnet --version </dev/null >/dev/null 2>&1) && return 0
  want="$(sed -n '/"version"/{s/.*"version"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p;q;}' "$dir/global.json" 2>/dev/null || true)"
  die 3 ".NET SDK ${want:+$want }(required by $dir/global.json) is not installed; add it to additionalVersions of the dotnet feature in .devcontainer/devcontainer.json and rebuild the container"
}

fork_version() {  # HEAD のコミットから fork のビルドの版を出力する: <csproj の Version>.fork.<UTC のコミット日>.g<短い SHA>
  local csproj="$dir/src/RLoop.Cli/RLoop.Cli.csproj" base date sha
  base="$(sed -n '/<Version>/{s|.*<Version>[[:space:]]*\([^<[:space:]]*\)[[:space:]]*</Version>.*|\1|p;q;}' "$csproj" 2>/dev/null || true)"
  base="${base%%+*}"
  [ -n "$base" ] || die 1 "cannot read <Version> from $csproj"
  date="$(TZ=UTC git -C "$dir" log -1 --format=%cd --date=format-local:%Y%m%d HEAD)" || die 4 'git log failed'
  sha="$(git -C "$dir" rev-parse --short=7 HEAD)" || die 4 'git rev-parse failed'
  # SemVer: プレリリースがあれば識別子を足し、無ければプレリリースとして付ける。SHA の前の g は、数字だけの SHA が
  # 先頭が 0 の数値の識別子（不正）になるのを避ける
  case "$base" in *-*) base="$base.fork" ;; *) base="$base-fork" ;; esac
  printf '%s.%s.g%s\n' "$base" "$date" "$sha"
}

# dotnet は global.json をカレントディレクトリから探すため、ビルドとテストは checkout に cd して実行する
build_package() {  # $1=版
  local version="$1"
  (cd "$dir" && run 'dotnet build' dotnet build ResoLoop.slnx -c Release --nologo </dev/null)
  (cd "$dir" && run 'dotnet pack' dotnet pack src/RLoop.Cli/RLoop.Cli.csproj -c Release --nologo \
    -o artifacts/fork "-p:PackageVersion=$version" "-p:Version=$version" </dev/null)
  [ -f "$dir/artifacts/fork/ResoLoop.$version.nupkg" ] \
    || die 4 "dotnet pack did not produce artifacts/fork/ResoLoop.$version.nupkg"
  printf 'built: %s/artifacts/fork/ResoLoop.%s.nupkg\n' "$dir" "$version"
}

do_build() {
  local version
  require_checkout
  dirty && die 1 "$dir has uncommitted changes to tracked files; commit them first (the package version names the commit)"
  require_sdk
  version="$(fork_version)" || exit "$?"
  build_package "$version"
}

do_test() {
  require_checkout
  require_sdk
  (cd "$dir" && run 'dotnet test' dotnet test ResoLoop.slnx --nologo </dev/null)
  printf 'ok: dotnet test passed\n'
}

verify_installed() {  # $1=期待版。~/.dotnet/tools の resoloop が期待版を返すことを確かめる
  local out actual
  out="$("$HOME/.dotnet/tools/resoloop" --version </dev/null)" \
    || die 1 "the installed resoloop cannot run ($HOME/.dotnet/tools/resoloop --version failed)"
  actual="$(resoloop_version_of "$out")" || die 1 "resoloop --version printed nothing"
  [ "$actual" = "$1" ] || die 1 "resoloop --version reports $actual, but $1 was installed"
  printf 'ok: resoloop --version is %s\n' "$actual"
}

do_install() {
  local want installed
  command -v dotnet >/dev/null 2>&1 || die 3 "dotnet not found"
  do_clone
  do_checkout
  want="$(fork_version)" || exit "$?"
  installed="$(resoloop_installed_version)" || die 4 "dotnet tool list --global failed"
  if [ "$installed" = "$want" ]; then
    printf 'ok: ResoLoop %s is already installed\n' "$want"
  else
    require_sdk
    build_package "$want"
    (cd "$root" && run 'dotnet tool update' dotnet tool update --global ResoLoop \
      --add-source "$dir/artifacts/fork" --version "$want" --allow-downgrade </dev/null)
    printf 'installed: ResoLoop %s from %s/artifacts/fork\n' "$want" "$dir"
  fi
  verify_installed "$want"
  printf 'note: this fork build stays until the next rebuild; return to the latest NuGet release with bash .devcontainer/install_resoloop.bash\n'
}

do_status() {
  local installed="" kind="" head branch state problems match=""
  if ! command -v dotnet >/dev/null 2>&1; then
    printf 'installed version: unknown (dotnet not found)\n'
  elif ! installed="$(resoloop_installed_version)"; then
    installed=""
    printf 'installed version: unknown (dotnet tool list --global failed)\n'
  elif [ -z "$installed" ]; then
    printf 'installed version: none\n'
  else
    case "$installed" in *[.-]fork.*) kind='fork build' ;; *) kind='NuGet release' ;; esac
    printf 'installed version: %s (%s)\n' "$installed" "$kind"
    [ "$kind" != 'fork build' ] || printf 'return to the latest NuGet release: bash .devcontainer/install_resoloop.bash\n'
  fi
  if [ ! -e "$dir" ] && [ ! -L "$dir" ]; then
    printf 'checkout: %s is missing (run scripts/resoloop-fork.sh clone)\n' "$dir"
    printf 'remotes: unknown (no checkout)\n'
    return
  fi
  if ! is_checkout; then
    printf 'checkout: %s %s\n' "$dir" "$not_a_checkout"
    printf 'remotes: unknown (no checkout)\n'
    return
  fi
  head="$(git -C "$dir" rev-parse -q --verify HEAD || printf 'none')"
  branch="$(git -C "$dir" symbolic-ref -q --short HEAD || printf 'detached')"
  if dirty; then state='uncommitted changes'; else state='clean'; fi
  if [ "$kind" = 'fork build' ]; then
    if [[ "$head" == "${installed##*.g}"* ]]; then
      match=', matches the installed fork build'
    else
      match=', differs from the installed fork build'
    fi
  fi
  printf 'checkout: %s at %s (%s, %s%s)\n' "$dir" "$head" "$branch" "$state" "$match"
  if problems="$(check_remotes)"; then
    printf 'remotes: origin and upstream are as expected\n'
  else
    printf 'remotes: %s\n' "${problems//$'\n'/; }"
  fi
}

"do_$cmd"
~~~

- [ ] **Step 4: 通ることを確かめる**

Run: `bash .devcontainer/run-tests.bash tests/scripts/test-resoloop-fork.bash`
Expected: PASS

- [ ] **Step 5: コミット**

~~~bash
git add scripts/resoloop-fork.sh tests/scripts/test-resoloop-fork.bash
git commit -m "feat(resoloop-fork): ロック無しで fork のビルドを一時的に導入する"
~~~

### Task 7: ロックを削除し、文書を新しい仕組みに合わせる

**Files:**
- Delete: `.devcontainer/resoloop.lock`、`.devcontainer/resoloop-lock.bash`、`.devcontainer/test-resoloop-lock.bash`
- Modify: `.devcontainer/devcontainer.json:49`、`AGENTS.md:84-88`、`README.md:23-27,65-71`、`.devcontainer/README.md:117-122`、`docs/resoloop-fork-workflow.md`（全体）、`docs/integration.md:96,103`、`.agents/skills/repo-cleanup-after-merge/SKILL.md:32,36`、`.agents/skills/repo-cleanup-after-merge/tests/test_repo_cleanup_after_merge_contract.py:76-79`（コメントだけ）
- Modify（テスト）: `tests/scripts/test-docs.bash:26`、`tests/scripts/test-instructions.bash:26,40-41`、`.devcontainer/test-readme.bash:44`、`tests/scripts/test-file-modes.bash:9`

- [ ] **Step 1: ロックを削除する**

~~~bash
git rm -q .devcontainer/resoloop.lock .devcontainer/resoloop-lock.bash .devcontainer/test-resoloop-lock.bash
~~~

- [ ] **Step 2: 文書のテストからロックを外す**（一覧から外すだけで、代わりの固定値は足さない）

- `tests/scripts/test-docs.bash:26` の一覧から `.devcontainer/resoloop.lock` を外す
- `tests/scripts/test-instructions.bash:26` の一覧から `'.devcontainer/resoloop.lock'` を外す。`:40` のコメントの「ResoLoop の版管理の 3 件」を「ResoLoop の版管理の 2 件」にし、`:41` の一覧から `.devcontainer/resoloop.lock` を外す
- `.devcontainer/test-readme.bash:44` の一覧から `'.devcontainer/resoloop.lock'` を外す
- `tests/scripts/test-file-modes.bash:9` のコメントの `resoloop-lock.bash` を `resoloop-tool.bash` にする

- [ ] **Step 3: 文書を書き換える**

`.devcontainer/devcontainer.json:49` のコメント:

~~~jsonc
			// fork のビルド（scripts/resoloop-fork.sh）に要る、上流 resoloop の global.json の SDK。rollForward: latestPatch は feature band をまたがないので、上流が変えたら合わせる
~~~

`AGENTS.md` の「ResoLoop の版管理」節の本文:

~~~markdown
- ResoLoop は常に NuGet の最新の公開版を使い、版を固定しない。postCreate が `.devcontainer/install_resoloop.bash` で最新を導入する。rebuild せずに最新へ上げるときも同じスクリプトを実行する。使っている版は `resoloop --version` で確かめる
- 上流に未取り込みの修正を一時的に使うときは、`scripts/resoloop-fork.sh install <fork のブランチかコミット>` で fork のビルドを導入する。次の rebuild か `bash .devcontainer/install_resoloop.bash` で最新の公開版に戻る。fork の取得・ビルド・導入の手順は `docs/resoloop-fork-workflow.md` に従う
- 版が上がると同梱スキル（`resonite-*`）にも更新が出る。postCreate と `scripts/check-layout.sh` は更新の有無を表示するだけなので、「プロジェクト運用」のとおり差分を確認してから `--update` する
~~~

`README.md` の「Dev Container を起動する」の 2 の後半（`ResoLoop は ...` の 2 行）:

~~~markdown
   ResoLoop は NuGet の最新の公開版をネットワークから導入し、続けて各プロジェクトの同梱スキルの状態を表示する。
~~~

`README.md` の「ResoLoop の版」節の本文（見出しは変えない）:

~~~~markdown
ResoLoop は常に NuGet の最新の公開版（上流 orange3134/resoloop のリリース。今はプレリリースだけ）を使い、版を固定しない。
Dev Container を作るとき（postCreate）に最新を導入する。rebuild せずに最新へ上げるときは、次の 1 行を実行する
（中で `dotnet tool update --global ResoLoop --prerelease --allow-downgrade` を実行し、`resoloop --version` を照合する）。

```bash
bash .devcontainer/install_resoloop.bash
```

最新に追従するので、rebuild や上のコマンドのたびに resoloop の挙動が変わり得る。使っている版は `resoloop --version` で確かめる。
版が上がると、各プロジェクトの同梱スキル（`resonite-*`）にも更新が出る。postCreate と `scripts/check-layout.sh` は更新の有無を
表示するだけなので、`resoloop skills sync --check` で差分を見てから `--update` する（`AGENTS.md` の「プロジェクト運用」）。

上流に未取り込みの修正を一時的に使うときは、`bash scripts/resoloop-fork.sh install <fork のブランチ>` で fork（usaturn/resoloop）の
ビルドを導入する。次の rebuild か、上の 1 行で最新の公開版に戻る。fork の checkout は `external/resoloop`（git の追跡対象外）に置く。
fork の使い方と上流への PR の流れは `docs/resoloop-fork-workflow.md` にある。
~~~~

`.devcontainer/README.md` の「Resonite ワールド開発ツール」の冒頭の 5 行（`Dev Container の作成時に` から `参照する。` まで）:

~~~markdown
Dev Container の作成時に .NET 10 SDK と Blender を導入し、ResoLoop は NuGet の最新の公開版を
`.devcontainer/install_resoloop.bash`（`dotnet tool update --global ResoLoop --prerelease --allow-downgrade`）で導入する。
続けて、各プロジェクトの `resoloop skills sync --check` の結果を `.devcontainer/report-resoloop-skills.bash` で表示する
（差分があっても postCreate は失敗しない）。rebuild せずに最新へ上げるときも `bash .devcontainer/install_resoloop.bash` を実行する。
fork のビルドを一時的に使う方法は `docs/resoloop-fork-workflow.md` を参照する。
~~~

`docs/integration.md`:

- 96 行の「postCreate は `.devcontainer/resoloop.lock` の fork をビルドして導入する（ネットワークと数分を要する）。」を「postCreate は NuGet の最新の公開版の ResoLoop を導入する（ネットワークを要する）。」にする
- 103 行を次にする

~~~markdown
2. postCreate の ResoLoop の導入が通っている: `resoloop --version` が NuGet の最新の公開版を返し、`bash scripts/resoloop-fork.sh status` の `installed version` が `NuGet release` である。postCreate の出力に、各プロジェクトの `resoloop skills sync --check` の結果がある。fork へ push する `bash scripts/resoloop-fork.sh sync` を初めて使うときは、GitHub への push の認証が通ることを確かめる。
~~~

`.agents/skills/repo-cleanup-after-merge/SKILL.md`:

- 32 行: 「fork の checkout は `scripts/resoloop-fork.sh checkout` が固定した lock commit へ detached HEAD で置かれており、`build` はこれを動かさない。」を「fork の checkout は、`scripts/resoloop-fork.sh checkout <ref>` や `install <ref>` が取り出したコミットで detached HEAD になっていることが多く、利用者が作業ブランチにいることもある。`build` はこれを動かさない。」にする
- 36 行: 「`external/resoloop` は detached のまま残す。誤って動かしていた場合は `bash scripts/resoloop-fork.sh checkout` で lock commit へ復元する」を「`external/resoloop` の HEAD は、detached でもブランチでもそのまま残す。誤って動かしていた場合は、`git -C external/resoloop reflog` で元の位置を確かめて戻す」にする
- テストの 76〜79 行のコメントの「off its lock commit」を「off the commit it was left at」にする

`docs/resoloop-fork-workflow.md` を次の内容に置き換える:

~~~~markdown
# ResoLoop の版と fork の運用

仕様: `docs/superpowers/specs/2026-10-06-issue-41-resoloop-latest-without-lock-design.md`（版のロックを廃止した設計）。この文書は、最新の公開版の導入と、fork（usaturn/resoloop）のビルドを一時的に使う日々の手順をまとめる。

## 仕組み

- ResoLoop は常に NuGet の最新の公開版を使い、版を固定しない。公開版は今はプレリリース（`0.1.0-preview.N`）だけなので、`--prerelease` を付けて導入する。
- Dev Container の postCreate（`.devcontainer/install_beforehand.bash`）は `.devcontainer/install_resoloop.bash` を実行する。このスクリプトは `dotnet tool update --global ResoLoop --prerelease --allow-downgrade` で最新を導入し（未導入なら導入、導入済みなら更新）、`resoloop --version` が導入した版と一致することを確かめる。NuGet に届かず更新できなくても、導入済みの版があれば警告してその版のまま続ける。導入済みの版が無ければ postCreate を失敗させる。
- コンテナの起動のたび（postStart）には更新しない。rebuild せずに最新へ上げるときは、手で `bash .devcontainer/install_resoloop.bash` を実行する。
- postCreate は続けて `.devcontainer/report-resoloop-skills.bash` で、各プロジェクトの `resoloop skills sync --check` の結果を表示する。差分があっても失敗しない。`scripts/check-layout.sh` も、新しい版による同梱スキルの更新（`SKILL_SYNC_REQUIRED`）は `warn:` の表示にとどめ、手で編集した同梱スキル（`SKILL_SYNC_CONFLICT`）は失敗にする。更新は差分を確かめてから `resoloop skills sync --update` で行う。
- `.devcontainer/verify-resonite-tooling.bash` は、`resoloop --version` が動いて版を表示することだけを確かめる（版の値は比べない）。

## 最新の公開版へ上げる・戻す

```bash
bash .devcontainer/install_resoloop.bash
```

fork のビルドを導入している状態からも、このコマンドで最新の公開版に戻る（fork のビルドの版は公開版より大きくなり得るので、`--allow-downgrade` を付けている）。使っている版は `resoloop --version`、または `bash scripts/resoloop-fork.sh status` の `installed version` で確かめる。

## fork のビルドを一時的に使う

上流に未取り込みの修正を使いたいときは、fork のブランチ（またはコミット）を指定してビルドし、導入する。

```bash
bash scripts/resoloop-fork.sh install fix/<topic>
```

`install` は次の順で進める。

1. `external/resoloop` が無ければ clone する（`origin` が fork、`upstream` が上流）。
2. `origin` と `upstream` を fetch し、`<ref>` を解決して detached で取り出す。`origin` に同じ名前のブランチがあればそれを使い、無ければ git がそのまま解決できる名前（コミット、タグ、ローカルのブランチ、`upstream/main` など）として扱う。push していないローカルのコミットは、コミットの SHA で指定する。
3. 版を決める。`<csproj の Version>.fork.<コミット日（UTC、YYYYMMDD）>.g<短い SHA>`（例: `0.1.0-preview.17.fork.20261006.gabc1234`）。同じコミットからは同じ版になる。
4. その版が導入済みなら、ビルドせずに照合だけ行う。違えば、`global.json` が要求する SDK を確かめ、ビルドして `dotnet tool update --global ResoLoop --add-source <checkout>/artifacts/fork --version <版> --allow-downgrade` で導入する。
5. `resoloop --version` がその版を返すことを確かめる。

この導入は一時的な上書きである。次の rebuild、または `bash .devcontainer/install_resoloop.bash` で最新の公開版に戻る。上流がその修正をリリースしたら、戻すだけでよい。

## checkout の位置と remote 構成

fork の checkout は `external/resoloop`（ルートの `.gitignore` で無視する）に置く。remote は次の 2 つで、`scripts/resoloop-fork.sh` はこの URL と比べて食い違いがあれば止まる（末尾の `/` と `.git` の違いは同じ URL とみなす）。

- `origin`: https://github.com/usaturn/resoloop.git（fork）
- `upstream`: https://github.com/orange3134/resoloop.git（上流）

`/workspaces` 直下には置かない。`/workspaces` はコンテナ内の root 所有のディレクトリで、ホストと共有されるのはリポジトリ（`/workspaces/<repo>`）だけなので、直下に置いた checkout はコンテナを作り直すと消える。`external/` はリポジトリの中にあるので Rebuild 後も残る。

## `scripts/resoloop-fork.sh` のサブコマンド

| サブコマンド | 動作 | ネットワーク |
| --- | --- | --- |
| `clone` | `external/resoloop` に `origin` と `upstream` を持つ checkout を作る。既にあれば remote の URL を確かめるだけ | 取得のみ |
| `sync` | `upstream` と `origin` を fetch し、fork の `main` を `upstream/main` へ fast-forward で push する。ローカルの `main` も追従させる。fork の `main` に上流に無いコミットがあれば何も push せずに止まる | **fork へ push する** |
| `checkout <ref>` | `origin` と `upstream` を fetch し、`<ref>` を解決して detached で取り出す（解決の順は上の「fork のビルドを一時的に使う」の 2）。追跡ファイルに未コミットの変更があれば止まる | 取得のみ |
| `build` | HEAD のコミットから版を決め、`global.json` が要求する SDK を確かめて、`dotnet build ResoLoop.slnx -c Release` と `dotnet pack`（`artifacts/fork` に `ResoLoop.<版>.nupkg`）を実行する。版がコミットを名指すので、追跡ファイルに未コミットの変更があれば止まる | NuGet の復元 |
| `test` | `dotnet test ResoLoop.slnx` を実行する | NuGet の復元 |
| `install <ref>` | `clone` → `checkout <ref>` → 版の決定 →（導入済みの版と違えば）ビルド → `dotnet tool update --allow-downgrade` を実行し、`resoloop --version` を照合する | 取得と NuGet の復元 |
| `status` | 導入済みの版とその種類（`NuGet release` か `fork build`）、checkout の HEAD と状態、remote の構成を表示する。fork のビルドなら、checkout の HEAD がそのビルドのコミットかと、公開版へ戻すコマンドも表示する。何も変更しない | なし |

`build`・`test` と `install` のビルドは `external/resoloop` に `cd` して実行する（dotnet は `global.json` をカレントディレクトリから探すため）。SDK の確認も同じ場所で `dotnet --version` を実行し、`rollForward` を含む解決を dotnet に任せる。上流の `global.json` が要求する SDK は `devcontainer.json` の dotnet Feature の `additionalVersions` で入れている。上流が変えたら `additionalVersions` も合わせる。

終了コード: 0 成功、1 状態が期待と違う（git の checkout でない、remote の食い違い、未コミットの変更、`<ref>` を解決できない、fork の `main` が上流から分岐、csproj の版を読めない、導入後の版の不一致など）、2 使い方の誤り、3 前提不足（git / dotnet が無い、SDK が無い、checkout が無い）、4 git や dotnet のコマンドの失敗。

環境変数 `RESOLOOP_CHECKOUT`（checkout の位置）と `RESOLOOP_ORIGIN_URL`・`RESOLOOP_UPSTREAM_URL`（remote の URL）で既定の値を差し替えられる。テストと特殊な運用向け。

## 状態を確かめる

```bash
bash scripts/resoloop-fork.sh status
```

`installed version` が `NuGet release` なら公開版を使っている。`fork build` なら fork のビルドを使っており、`bash .devcontainer/install_resoloop.bash` で公開版に戻る。`checkout` の行は、HEAD・ブランチ（または `detached`）・未コミットの変更の有無を示す。`remotes` が `as expected` でなければ、`git -C external/resoloop remote set-url` で直す。

## 上流へ PR を出すときの流れ

1. `bash scripts/resoloop-fork.sh sync` で fork の `main` を上流に追従させる（fork へ push する）。
2. `git -C external/resoloop switch -c fix/<topic> upstream/main` で作業ブランチを作る。
3. 修正してコミットする。
4. `bash scripts/resoloop-fork.sh test` でテストを通す。
5. `git -C external/resoloop push -u origin fix/<topic>` で fork へ push する。
6. 手元で試すときは `bash scripts/resoloop-fork.sh install fix/<topic>` でビルドして導入する。checkout は detached になるので、作業を続けるときは `git -C external/resoloop switch fix/<topic>` で戻る。push していないコミットを試すときは、ブランチ名ではなく `git -C external/resoloop rev-parse HEAD` の SHA を渡す。
7. 上流へ PR を出す（例: `gh pr create --repo orange3134/resoloop --head usaturn:fix/<topic>`）。
8. 上流がマージしてリリースしたら、`bash .devcontainer/install_resoloop.bash` で公開版に戻す。

`external/resoloop` の追跡ファイルに未コミットの変更があると、`checkout`・`build`・`install` は止まる。コミットするか stash してから実行し直す。

## fork 内の PR

- fork 内の PR（usaturn/resoloop#1）はレビュー用であり、マージしない。

## 上流への PR 候補

- `resoloop init` が作る `.resoloop/.gitignore` に `cache/` が無い（このリポジトリでは `scripts/new-world.sh` が追記している）。
- `global.json` の `rollForward` が `latestPatch` なので、SDK の feature band（10.0.2xx と 10.0.4xx など）を跨げない。このため `devcontainer.json` の `additionalVersions` で 10.0.201 を追加している。

## `tmp/` にある旧 checkout の整理

再設計の前に手作業で作った checkout と作業記録が `tmp/` に残っている。削除は必要な内容を確かめてから手で行う（自動では消さない）。

| ディレクトリ | 中身 | 扱い |
| --- | --- | --- |
| `tmp/resoloop-blender5-uv-20260925` | remote は fork（`origin`）と上流（`upstream`）で、HEAD はブランチ `fix/blender5-uv-export` のコミット。未追跡の `reviews/` がある | `external/resoloop` がまだ無ければ、`reviews/` を必要に応じて退避してから `mv tmp/resoloop-blender5-uv-20260925 external/resoloop` で移し、`bash scripts/resoloop-fork.sh status` で確かめる。clone を省ける |
| `tmp/usaturn-resoloop-pr1` | fork 内 PR #1 のレビュー用 checkout。未追跡の `reviews/` がある | `reviews/` を必要に応じて退避してから削除する |
| `tmp/resoloop-uv0-fix-20260924` | 上流 v0.1.0-preview.13 の shallow checkout に、未コミットの草稿（4 ファイル）がある | `git -C tmp/resoloop-uv0-fix-20260924 diff > ~/resoloop-uv0-fix-draft.patch` で草稿を保存してから削除する |
| `tmp/resoloop-skills-20260924-1526` | git の checkout ではない作業記録（レビューと差分の Markdown など） | 必要なものを退避してから削除する |

## 対象外

flux-sdk の導入はこの運用の対象外とする。
~~~~

- [ ] **Step 4: 検査する**

Run: `bash .devcontainer/run-tests.bash && bash scripts/check-layout.sh && uv run pytest tests/skills .agents/skills -q`
Expected: すべて PASS

Run: `git grep -n -E 'resoloop\.lock|resoloop-lock|RESOLOOP_(MODE|NUGET_VERSION|FORK_)' -- ':!docs/superpowers/**' ':!docs/maatlog-poc-porting.md' ':!.agents/skills/rst-writer/evals/fixtures/**' ':!scripts/superpowers_context.py'`
Expected: 出力なし（終了コード 1）

- [ ] **Step 5: コミット**

~~~bash
git add -A .devcontainer AGENTS.md README.md docs/resoloop-fork-workflow.md docs/integration.md .agents/skills/repo-cleanup-after-merge tests/scripts
git commit -m "chore: ResoLoop の版のロックを削除し、文書を最新の版を使う運用に合わせる"
~~~

### Task 8: コンテナで実際に確かめる

**Files:** なし（検証だけ。結果は PR の本文に書く）

- [ ] **Step 1: 最新の公開版を入れる**

Run: `bash .devcontainer/install_resoloop.bash && resoloop --version`
Expected: `ResoLoop setup: resoloop <最新> is installed (was 0.1.0-preview.15).`、`resoloop --version` が NuGet の最新（Issue の作成時点では `0.1.0-preview.17`）

- [ ] **Step 2: fork のビルドを一時的に入れる**（利用者の `external/resoloop` を動かさないよう、scratchpad に clone する。時間がかかるのでバックグラウンドで実行し、monitoring-long-tasks に従って待つ）

Run: `RESOLOOP_CHECKOUT=<scratchpad>/resoloop bash scripts/resoloop-fork.sh install main && resoloop --version && RESOLOOP_CHECKOUT=<scratchpad>/resoloop bash scripts/resoloop-fork.sh status`
Expected: `ok: resoloop --version is <Version>.fork.<日付>.g<SHA>`、status が `fork build` と `matches the installed fork build`

- [ ] **Step 3: 公開版に戻す**

Run: `bash .devcontainer/install_resoloop.bash && resoloop --version`
Expected: `(was <fork の版>)` と表示し、最新の公開版に戻る

- [ ] **Step 4: 同梱スキルの表示と全体の検査**

Run: `bash .devcontainer/report-resoloop-skills.bash; echo "exit=$?"`
Expected: 各プロジェクトの結果が出て `exit=0`

Run: `bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`uv run pytest tests/skills .agents/skills -q`、各プロジェクト（MyResoniteProject・akichi・slum02・slum03）で `uv run pytest -q`
Expected: すべて通る。check-layout は 4 プロジェクトについて `warn:` を表示して `PASS: check-layout`
