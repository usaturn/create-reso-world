# create-reso-world 再設計 フェーズ 3（ResoLoop の版管理と fork 運用）実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 導入する ResoLoop の版を `.devcontainer/resoloop.lock` で固定し、fork（Blender 5 の UV 修正入り）の取得・ビルド・導入を `scripts/resoloop-fork.sh` で再現できるようにする。あわせて、フェーズ 2 から持ち越したスクリプトの小修正（N-9・N-10・N-15・N-16）を片付ける。

**Architecture:** ロックは `KEY=VALUE` のテキストで、`.devcontainer/resoloop-lock.bash` の `resoloop_lock_load` が 1 行ずつ検証して読む（source しない）。導入（`install_resoloop.bash`）・確認（`verify-resonite-tooling.bash`）・fork の操作（`scripts/resoloop-fork.sh`）・レイアウト検査（`scripts/check-layout.sh`）は、すべてこの読み込み関数を使う。fork は `external/resoloop` に clone し、ロックのコミットを detached で取り出してから `dotnet pack` した nupkg をローカルのパッケージソースとして `dotnet tool install|update` する。

**Tech Stack:** bash（`set -euo pipefail`、既存の `tests/scripts/*.bash` と `.devcontainer/test-*.bash` と同じ書き方）、git、.NET SDK 10（`dotnet tool` / `build` / `pack` / `test`）、Dev Container の dotnet Feature（`additionalVersions`）、uv / pytest（既存の回帰確認だけに使う）

**Spec:** `docs/superpowers/specs/2026-09-26-create-reso-world-redesign-design.md`（6 章、7.2 節のうち ResoLoop に関わる項目、9.1 節のロック検査、10 章のフェーズ 3）。前フェーズの計画は `docs/superpowers/plans/2026-09-26-redesign-phase2-instructions-and-skills.md`。

## 判断事項（2026-09-27 にユーザ承認済み）

計画の作成時に、scratchpad に作業用 worktree を複製し、全 Task のコードとテストを実行して通した。各テストが対象の修正を実際に検出することは、実装をわざと壊すミューテーションで確かめた。実環境では、読み取りだけの確認として実物の resoloop に対する `status`、GitHub の fork に対する `clone` と `checkout`（ロックのコミットが fork にあることを確認済み）、`verify-resonite-tooling.bash` を実行した。仕様が決めていない点は次のとおりとし、本計画はこの内容で書いてある。2026-09-27 にユーザが計画全体と D-3〜D-8 を承認した（実行は同じセッションで Subagent-driven）。

| ID | 事項 | 本計画の内容 | 理由 |
| --- | --- | --- | --- |
| D-3 | ロックの読み方 | source せず、`resoloop_lock_load` が 1 行ずつ `KEY=VALUE`（値は英数字と `._:/@+-`）を検証して読む。9 個のキーはモードにかかわらず必須とし、未知のキー・重複・CRLF・空の値は拒否する | 値に `$(...)` が紛れ込んでも実行しない。書式は仕様 6.1 のとおり source できる形のまま |
| D-4 | 同じ版の再導入 | 導入済みの版が期待版と同じなら、fork の `install` もビルドし直さない。コミットを差し替えるときは `RESOLOOP_FORK_PACKAGE_VERSION` も変えるという規則を、ロックの注記、`install` の表示、運用文書に書く | 仕様 6.2 の「導入済み版 == 期待版なら何もしない」をそのまま適用する。dotnet tool も同じ版への更新は行わない |
| D-5 | `resoloop-fork.sh` の安全側の既定 | `checkout` は追跡ファイルに未コミットの変更があれば止まる（`install` と postCreate も同じ）。`sync` は fork の `main` に上流に無いコミットがあれば push しない。`install` は `nuget` モードでは止まる。remote の URL が食い違っていても直さずに止まる | 手元の修正やリモートの状態を黙って書き換えない |
| D-6 | check-layout の読み取り元（N-15） | mode に加えて、symlink の行き先・ファイルの中身・空かどうかも index から読む（`git cat-file`）。追跡中の symlink が解決できるか（検査 2）だけは作業ツリーで確かめる | 作業ツリーの未ステージの変更が index の問題を隠さない。core.symlinks=false の checkout でも同じ結果になる |
| D-7 | リンクが要るディレクトリの定義（N-10） | new-world.sh を check-layout の定義（追跡ファイルを 1 つ以上持つ `.agents/skills` 直下のディレクトリ）に合わせる。ファイルシステムでは「ファイルを 1 つ以上持つディレクトリ（隠しディレクトリを含む）」とする | ルートの `references/` のように、SKILL.md を持たない共有ディレクトリにもリンクが要る |
| D-8 | フェーズ 3 で触る `.devcontainer/` の範囲 | 仕様 7.2 のうち ResoLoop に関わる項目だけ: `devcontainer.json` の dotnet Feature の `additionalVersions`、`install_resoloop.bash`・`verify-resonite-tooling.bash` とそのテスト、`test-resoloop-lock.bash`、`install_beforehand.bash` の ResoLoop の手順名 1 行、`.devcontainer/README.md` の「Resonite ワールド開発ツール」節の導入方法の段落と確認コマンド。7.2 のそれ以外の項目はフェーズ 4 | このフェーズで導入の挙動が変わる箇所の説明を、同じフェーズで正しくする |

仕様 10 章のフェーズ 3 の完了条件（`test-install-resoloop.bash` と `test-resoloop-lock.bash` の通過、`resoloop-fork.sh status`）は Task 8 で確認する。コンテナには `RESOLOOP_FORK_SDK`（10.0.201）が無いため、fork の実ビルドと実導入はこのフェーズでは行わない。Rebuild 後の実機確認（仕様 9.3、ユーザが実施）に委ねる（持ち越し N-18）。

## Global Constraints

- 変数: `M=/workspaces/reso-world`（メイン作業ツリー。ブランチ feat/slum02-slum で、別セッションが slum02 を編集中）、`W=/workspaces/reso-world/.worktrees/repo-redesign`（作業用 worktree。ブランチ chore/repo-redesign）。各ステップのコマンドは `export M=/workspaces/reso-world W=/workspaces/reso-world/.worktrees/repo-redesign` を実行してから、特記が無ければ `cd "$W"` で実行する。
- メイン作業ツリー `$M` では読み取りだけを行う。追跡ファイルの編集、`git add` / `commit` / `checkout` / `stash` / `reset` / `clean` / `fetch`、ファイルの移動・削除をしない。
- 変更のコミットはすべて `$W` で行う。コミットメッセージの末尾に、コミットするエージェント自身のモデル名の trailer を付ける（例: `Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>`）。
- `git add` には明示したパスだけを渡す。`$W` で `git add -A` / `git add .` を使わない（テストが作る一時リポジトリの中は除く）。
- `git push --force` 系を使わない。push は Task 8 で controller が `git push origin chore/repo-redesign`（fast-forward を確認してから）だけ行う。`main`・`feat/*`・`wip/*` を push・rebase・削除しない。PR を開かない。
- Python は uv で実行する（`uv run ...`、`uv run --no-project ...`）。`python3` を直接呼ばない。
- 説明・文書・コミットの日本語で「契約」「原子的」「製品」「着地」を使わない。
- 触らないもの: TRPG 本文（`private/trpg/`、`tmp/` の `ATS.txt`・`BTD.txt`・`TNX.txt`）、`MyResoniteProject/.resoloop/tokyo-nova/pipeline.json`、`.pi/APPEND_SYSTEM.md` の `## Response Persona` 以降、`.git/info/exclude`、`.claude/settings.json`、`.mcp.json`、`.devcontainer/` のうち判断事項 D-8 に挙げていないファイルと行。
- **実環境を変えるコマンドを実行しない。** `dotnet tool install` / `update` / `uninstall`、モックを使わない `bash .devcontainer/install_resoloop.bash`、`install_beforehand.bash`、実ロックに対する `scripts/resoloop-fork.sh sync|build|test|install`（`sync` は usaturn/resoloop へ push し、`install` はグローバルツールを置き換える）は実行しない。実ロックに対して実行してよいのは `scripts/resoloop-fork.sh status` と `bash .devcontainer/verify-resonite-tooling.bash`（読み取りだけ）で、Task 8 では controller だけが `clone` と `checkout` を `$W/external/resoloop` に対して実行する（取得だけ）。テストは必ず、一時ディレクトリの `HOME`、モックの `dotnet`、ローカルの bare リポジトリで行う。
- 既存プロジェクトのディレクトリの中で `resoloop init` や `resoloop skills sync --update` を実行しない。`resoloop skills sync` は `--check` だけ使う。
- テストの書き方: `コマンド | grep -q` は、出力の最終行を照合するときにだけ使う。途中の行を照合するときは、出力をファイルか変数に取ってから `grep` する（`pipefail` の下では `grep -q` が早く終わると上流のコマンドが SIGPIPE で終了コード 141 になり、テストが不安定になる）。
- ルートの pytest の既知の失敗: `pi-model-name/tests/test_pi_model_name_contract.py` の 27 件と `repository-ownership/tests/test_public_release_guidance.py` の 7 件の計 34 件（どちらもフェーズ 5 で扱う）。各 Task の最後に次を実行し、何も表示されないことを確認する。

```bash
cd "$W" && uv run pytest -q -rf 2>&1 | grep '^FAILED' \
  | grep -v -e 'pi-model-name/tests/test_pi_model_name_contract.py' \
            -e 'repository-ownership/tests/test_public_release_guidance.py' || true
```

- 各 Task の後に次も通る: `for t in tests/scripts/*.bash; do bash "$t" >/dev/null 2>&1 && echo "PASS $t" || echo "FAIL $t"; done`（すべて PASS）、`for t in .devcontainer/test-*.bash; do ...; done`（`test-herdr-migration.bash` だけが既知の FAIL。フェーズ 4 で扱う）、`bash scripts/check-layout.sh`（最終行が `PASS: check-layout`）、`git ls-files -i -c --exclude-standard`（`MyResoniteProject/.resoloop/tokyo-nova/pipeline.json` の 1 行だけ）。
- フェーズ 3 の範囲外（持ち越し節を参照）に手を出さない。特に、`.devcontainer/` のフェーズ 4 の項目（`name`、`remoteEnv.PATH`、mounts、Codex の導入、`zshrc.txt`、`run-tests.bash`、`test-herdr-migration.bash` など）、スキル本文の書き直し（フェーズ 5）、ルート README（フェーズ 6）。

## Review Focus

- `external/resoloop` が想定外の状態のまま `install`（postCreate を含む）が走る: 外側のリポジトリの中にある git の checkout でないディレクトリ、remote の URL の違いや欠落、追跡ファイルの未コミットの変更、`origin` に無いコミット、ネットワークの失敗による clone の中断。どれも直すべき点を示すメッセージを出して止まり（1 または 4）、clone し直したり外側のリポジトリの remote を読んだり、半端な checkout を残したりしない（Task 2 のケース 5・6・7・9・10）。
- 人が手で編集したロック: 必須キーの欠落、未知のキー、重複、値に書いたコマンド、CRLF、空の値は拒否し、何も実行しない。最終行の改行が無いだけなら読める。コミットを差し替えて版を据え置いた場合、`install` は再ビルドせずに「版を上げる」ことを表示する（Task 1 のケース 3〜5、Task 2 のケース 18）。
- ロックの SDK が無いコンテナ（Rebuild していない、Feature が効いていない）: `build`・`test`・`install` は `dotnet build` を呼ぶ前に、`additionalVersions` を示して終了コード 3 で止まる（Task 2 のケース 14）。
- `resoloop --version` の出力の揺れ（前後の空白、`+` 以降のビルドメタデータ、空行）と、導入済みの CLI の版の食い違い: 正規化してから比べ、食い違えば両方の版を示して失敗する。対象は install、fork の install、verify の 3 か所（Task 1 のケース 7、Task 2 のケース 20、Task 3 のケース 2・5 と verify のテスト）。
- 作業ツリーが index と食い違う状態での check-layout: 未ステージの変更、作業ツリーだけで消したファイル、core.symlinks=false の checkout。結果は index の内容だけで決まる（Task 4 のケース 41・42、Task 5 のケース 47）。

## 実行前の準備（controller）

- [x] 1. 計画作成時点で worktree はクリーンで、HEAD は `ebec0cc` だった。
- [x] 2. 承認後に本計画書をコミットする（`docs: add redesign phase 3 implementation plan`）。実行開始時は `git -C "$W" status --short | wc -l` が 0 で、`git -C "$W" log -1 --format=%s` がこのメッセージであることを確認する。
- [ ] 3. SDD の作業ディレクトリと台帳を作る（`bash <sdd-skill>/scripts/sdd-workspace <この計画のパス>`）。
- [ ] 4. フェーズ 2 の SDD 作業ディレクトリ `$W/.superpowers/sdd/2026-09-26-redesign-phase2-instructions-and-skills/` を削除する。保留事項は本計画の「持ち越し」節に転記済み（前回の引き継ぎ書の指示）。

---

### Task 1: ロックファイルと読み込み関数（仕様 6.1・6.3）

ResoLoop の版の正本 `.devcontainer/resoloop.lock` と、それを検証して読む関数集 `.devcontainer/resoloop-lock.bash` を作る。fork の `global.json` が要求する SDK を、dotnet Feature の `additionalVersions` で追加する。

**Files:**
- Create: `.devcontainer/resoloop.lock`
- Create: `.devcontainer/resoloop-lock.bash`（source して使う関数集。mode 100755）
- Create: `.devcontainer/test-resoloop-lock.bash`（mode 100755）
- Modify: `.devcontainer/devcontainer.json`（dotnet Feature の 1 か所だけ）

**Interfaces:**
- Produces（Task 2〜5 が使う。`source "$root/.devcontainer/resoloop-lock.bash"` で読み込む）:
  - `resoloop_lock_load FILE` — 成功すると `RESOLOOP_MODE`、`RESOLOOP_NUGET_VERSION`、`RESOLOOP_FORK_ORIGIN`、`RESOLOOP_FORK_UPSTREAM`、`RESOLOOP_FORK_REF`、`RESOLOOP_FORK_COMMIT`、`RESOLOOP_FORK_PACKAGE_VERSION`、`RESOLOOP_FORK_PR`、`RESOLOOP_FORK_SDK` と `RESOLOOP_EXPECTED_VERSION`（fork なら `RESOLOOP_FORK_PACKAGE_VERSION`、nuget なら `RESOLOOP_NUGET_VERSION`）を設定して 0。不正なら `resoloop.lock: <理由>` を 1 件 1 行で標準エラーに出して 1（変数は設定しない）。理由の文言: `<file> not found`、`line N is not KEY=VALUE (...)`、`line N: unknown key K`、`line N: duplicate key K`、`missing key K`、`RESOLOOP_MODE must be nuget or fork, not X`、`RESOLOOP_FORK_COMMIT must be a full 40-character commit id`、`RESOLOOP_FORK_SDK must be an exact SDK version such as 10.0.201`
  - `resoloop_lock_sdk_declared DEVCONTAINER_JSON SDK` — `"additionalVersions"` のカンマ区切りの中に SDK があれば 0（`//` のコメント行は数えない）
  - `resoloop_installed_version` — `dotnet tool list --global` から ResoLoop の版を出力（未導入なら空）。一覧を取れなければ 1
  - `resoloop_version_of TEXT` — `resoloop --version` の出力から版を取り出す（最初の空でない行、前後の空白と `+` 以降を除く）。空なら 1

- [ ] **Step 1: 失敗するテストを書く**

`.devcontainer/test-resoloop-lock.bash` を次の内容で作り、`chmod +x` する。

```bash
#!/bin/bash
# .devcontainer/resoloop.lock と読み込み関数（.devcontainer/resoloop-lock.bash）を検査する。仕様 6.1・6.3・9.1 節
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
tmp="$(mktemp -d)"
trap 'rm -rf -- "$tmp"' EXIT
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
# shellcheck source=resoloop-lock.bash
source "$root/.devcontainer/resoloop-lock.bash"

# 1. リポジトリのロックは読めて、RESOLOOP_FORK_SDK が devcontainer.json の additionalVersions にある
resoloop_lock_load "$root/.devcontainer/resoloop.lock" || fail 'the repository lock is invalid'
[ -n "$RESOLOOP_EXPECTED_VERSION" ] || fail 'no expected version'
resoloop_lock_sdk_declared "$root/.devcontainer/devcontainer.json" "$RESOLOOP_FORK_SDK" \
  || fail "RESOLOOP_FORK_SDK $RESOLOOP_FORK_SDK is not in additionalVersions of devcontainer.json"

# 以降は一時ファイルのロックで検査する。write_lock MODE [追加の行...]
write_lock() {
  local mode="$1"; shift
  {
    printf '# comment\n\n'
    printf 'RESOLOOP_MODE=%s\n' "$mode"
    printf 'RESOLOOP_NUGET_VERSION=1.2.3-preview.4\n'
    printf 'RESOLOOP_FORK_ORIGIN=https://example.com/fork/resoloop.git\n'
    printf 'RESOLOOP_FORK_UPSTREAM=https://example.com/upstream/resoloop.git\n'
    printf 'RESOLOOP_FORK_REF=fix/x\n'
    printf 'RESOLOOP_FORK_COMMIT=%s\n' 0123456789abcdef0123456789abcdef01234567
    printf 'RESOLOOP_FORK_PACKAGE_VERSION=1.2.3-preview.4.pr1.20260101\n'
    printf 'RESOLOOP_FORK_PR=https://example.com/upstream/resoloop/pull/9\n'
    printf 'RESOLOOP_FORK_SDK=10.0.201\n'
    [ $# -eq 0 ] || printf '%s\n' "$@"
  } > "$tmp/lock"
}
# expect_invalid NEEDLE: ロックの読み込みが失敗し、標準エラーに NEEDLE が出ることを確かめる
expect_invalid() {
  local out
  if out="$( (resoloop_lock_load "$tmp/lock") 2>&1 )"; then fail "accepted an invalid lock (expected: $1)"; fi
  grep -qF -- "$1" <<<"$out" || fail "expected '$1' in: $out"
}

# 2. fork モードの期待版は RESOLOOP_FORK_PACKAGE_VERSION、nuget モードは RESOLOOP_NUGET_VERSION
write_lock fork
( resoloop_lock_load "$tmp/lock" && [ "$RESOLOOP_EXPECTED_VERSION" = 1.2.3-preview.4.pr1.20260101 ] ) || fail 'fork expected version'
write_lock nuget
( resoloop_lock_load "$tmp/lock" && [ "$RESOLOOP_EXPECTED_VERSION" = 1.2.3-preview.4 ] ) || fail 'nuget expected version'

# 3. 必須キーの欠落、未知のキー、重複、不正なモード、短いコミット ID、SDK の書式
write_lock fork && sed -i '/^RESOLOOP_FORK_SDK=/d' "$tmp/lock"
expect_invalid 'missing key RESOLOOP_FORK_SDK'
write_lock fork 'RESOLOOP_FORK_CHECKOUT=/tmp/x'
expect_invalid 'unknown key RESOLOOP_FORK_CHECKOUT'
write_lock fork 'RESOLOOP_MODE=nuget'
expect_invalid 'duplicate key RESOLOOP_MODE'
write_lock source
expect_invalid 'RESOLOOP_MODE must be nuget or fork, not source'
write_lock fork && sed -i 's/^RESOLOOP_FORK_COMMIT=.*/RESOLOOP_FORK_COMMIT=1ef4d18/' "$tmp/lock"
expect_invalid 'RESOLOOP_FORK_COMMIT must be a full 40-character commit id'
write_lock fork && sed -i 's/^RESOLOOP_FORK_SDK=.*/RESOLOOP_FORK_SDK=10.0/' "$tmp/lock"
expect_invalid 'RESOLOOP_FORK_SDK must be an exact SDK version'

# 4. 値にコマンドを書いても実行せずに拒否する。空の値、CRLF の行も拒否する
write_lock fork "RESOLOOP_FORK_PR=\$(touch $tmp/executed)"
expect_invalid 'is not KEY=VALUE'
[ ! -e "$tmp/executed" ] || fail 'the lock was executed'
write_lock fork && sed -i 's/^RESOLOOP_FORK_PR=.*/RESOLOOP_FORK_PR=/' "$tmp/lock"
expect_invalid 'is not KEY=VALUE'
write_lock fork && sed -i 's/^RESOLOOP_FORK_REF=fix\/x$/RESOLOOP_FORK_REF=fix\/x\r/' "$tmp/lock"
expect_invalid 'is not KEY=VALUE'

# 5. 失敗したときは変数を設定しない。最終行に改行が無くても読める。ファイルが無ければ失敗する
write_lock fork && sed -i '/^RESOLOOP_FORK_SDK=/d' "$tmp/lock"
( unset RESOLOOP_MODE; resoloop_lock_load "$tmp/lock" 2>/dev/null; [ -z "${RESOLOOP_MODE+x}" ] ) || fail 'set variables from an invalid lock'
write_lock fork && printf 'RESOLOOP_FORK_SDK=10.0.201' > "$tmp/last" && sed -i '/^RESOLOOP_FORK_SDK=/d' "$tmp/lock" && cat "$tmp/last" >> "$tmp/lock"
( resoloop_lock_load "$tmp/lock" && [ "$RESOLOOP_FORK_SDK" = 10.0.201 ] ) || fail 'last line without a newline'
if (resoloop_lock_load "$tmp/missing") 2>/dev/null; then fail 'accepted a missing lock'; fi

# 6. additionalVersions はカンマ区切りの中から探し、// のコメント行は数えない
printf '{\n  "a": { "additionalVersions": "8.0.100, 10.0.201" }\n}\n' > "$tmp/list.json"
resoloop_lock_sdk_declared "$tmp/list.json" 10.0.201 || fail 'SDK in a comma list'
printf '{\n  // "additionalVersions": "10.0.201"\n  "a": { "version": "10.0" }\n}\n' > "$tmp/comment.json"
if resoloop_lock_sdk_declared "$tmp/comment.json" 10.0.201; then fail 'counted a commented-out line'; fi
if resoloop_lock_sdk_declared "$tmp/list.json" 10.0.2; then fail 'matched a version prefix'; fi
if resoloop_lock_sdk_declared "$tmp/none.json" 10.0.201; then fail 'accepted a missing devcontainer.json'; fi

# 7. resoloop --version の出力から版を取り出す
[ "$(resoloop_version_of $'0.1.0-preview.14\n')" = 0.1.0-preview.14 ] || fail 'plain version'
[ "$(resoloop_version_of $'  1.2.3+abc123  \n')" = 1.2.3 ] || fail 'whitespace and build metadata'
[ "$(resoloop_version_of $'\n\n2.0.0\nextra\n')" = 2.0.0 ] || fail 'first non-empty line'
if resoloop_version_of $'\n  \n' >/dev/null; then fail 'accepted empty output'; fi

# 8. dotnet tool list --global から導入済み版を読む（モックの dotnet）
mkdir -p "$tmp/bin"
cat > "$tmp/bin/dotnet" <<'EOF'
#!/bin/bash
[ "$*" = 'tool list --global' ] || exit 64
[ "${MOCK_LIST_FAIL:-0}" = 0 ] || exit 1
printf 'Package Id      Version      Commands\n-------------------------------------\n'
[ -z "${MOCK_LIST_LINE:-}" ] || printf '%s\n' "$MOCK_LIST_LINE"
EOF
chmod +x "$tmp/bin/dotnet"
[ "$(PATH="$tmp/bin:$PATH" MOCK_LIST_LINE='resoloop  0.1.0-preview.14.pr1.20260925  resoloop' resoloop_installed_version)" = 0.1.0-preview.14.pr1.20260925 ] \
  || fail 'installed version'
[ "$(PATH="$tmp/bin:$PATH" MOCK_LIST_LINE='ResoLoop 1.0.0 resoloop' resoloop_installed_version)" = 1.0.0 ] || fail 'package id is case-insensitive'
[ -z "$(PATH="$tmp/bin:$PATH" MOCK_LIST_LINE='my-resoloop-plugin 1.0.0 other' resoloop_installed_version)" ] || fail 'matched a different package'
[ -z "$(PATH="$tmp/bin:$PATH" resoloop_installed_version)" ] || fail 'reported a version when nothing is installed'
if PATH="$tmp/bin:$PATH" MOCK_LIST_FAIL=1 resoloop_installed_version >/dev/null; then fail 'ignored a failing dotnet tool list'; fi

printf 'PASS: resoloop lock and its reader behave as specified\n'
```

- [ ] **Step 2: テストが失敗することを確かめる**

Run: `bash .devcontainer/test-resoloop-lock.bash`
Expected: 終了コード 1。`.devcontainer/resoloop-lock.bash: No such file or directory`

- [ ] **Step 3: ロックと読み込み関数を作り、SDK を追加する**

`.devcontainer/resoloop.lock`（値は仕様 6.1 のとおり）:

```text
# ResoLoop の版を固定するロックファイル。仕様: docs/superpowers/specs/2026-09-26-create-reso-world-redesign-design.md 6.1 節
# 書式は KEY=VALUE の 1 行 1 項目（値に空白・引用符・$ を使わない）。bash で source できる書式だが、
# スクリプトは .devcontainer/resoloop-lock.bash の resoloop_lock_load で検証してから読む。
# 期待版は RESOLOOP_MODE=nuget なら RESOLOOP_NUGET_VERSION、fork なら RESOLOOP_FORK_PACKAGE_VERSION。
# RESOLOOP_FORK_COMMIT を差し替えるときは RESOLOOP_FORK_PACKAGE_VERSION も変える（同じ版は導入済みとみなされ、再導入されない）。
RESOLOOP_MODE=fork
RESOLOOP_NUGET_VERSION=0.1.0-preview.14
RESOLOOP_FORK_ORIGIN=https://github.com/usaturn/resoloop.git
RESOLOOP_FORK_UPSTREAM=https://github.com/orange3134/resoloop.git
RESOLOOP_FORK_REF=fix/blender5-uv-export
RESOLOOP_FORK_COMMIT=1ef4d18ca4010b2d5740b36af9c0c7a67785a1ca
RESOLOOP_FORK_PACKAGE_VERSION=0.1.0-preview.14.pr1.20260925
RESOLOOP_FORK_PR=https://github.com/orange3134/resoloop/pull/2
RESOLOOP_FORK_SDK=10.0.201
```

`.devcontainer/resoloop-lock.bash`（作成後に `chmod +x`）:

```bash
#!/bin/bash
# .devcontainer/resoloop.lock を読むための関数集。source して使い、単体では何もしない。
# 仕様: docs/superpowers/specs/2026-09-26-create-reso-world-redesign-design.md 6.1・6.2・9.1 節
# ロックは source せず、1 行ずつ書式を検証してから読む（値にコマンドが紛れ込んでも実行しない）。

RESOLOOP_LOCK_KEYS=(RESOLOOP_MODE RESOLOOP_NUGET_VERSION RESOLOOP_FORK_ORIGIN RESOLOOP_FORK_UPSTREAM
  RESOLOOP_FORK_REF RESOLOOP_FORK_COMMIT RESOLOOP_FORK_PACKAGE_VERSION RESOLOOP_FORK_PR RESOLOOP_FORK_SDK)

# resoloop_lock_load FILE
# ロックを検証し、RESOLOOP_LOCK_KEYS の各変数と RESOLOOP_EXPECTED_VERSION を設定する。
# 不正なら理由を標準エラーに 1 件 1 行で出して 1 を返し、変数は設定しない。
resoloop_lock_load() {
  local file="$1" line key value n=0 k
  local blank_re='^[[:space:]]*(#.*)?$' kv_re='^([A-Z][A-Z0-9_]*)=([A-Za-z0-9._:/@+-]+)$'
  local -a errors=()
  local -A seen=()
  if [ ! -f "$file" ]; then
    printf 'resoloop.lock: %s not found\n' "$file" >&2
    return 1
  fi
  while IFS= read -r line || [ -n "$line" ]; do
    n=$((n + 1))
    [[ "$line" =~ $blank_re ]] && continue
    if [[ ! "$line" =~ $kv_re ]]; then
      errors+=("line $n is not KEY=VALUE (the value may use only letters, digits and ._:/@+-)")
      continue
    fi
    key="${BASH_REMATCH[1]}" value="${BASH_REMATCH[2]}"
    if [[ " ${RESOLOOP_LOCK_KEYS[*]} " != *" $key "* ]]; then
      errors+=("line $n: unknown key $key")
    elif [ -n "${seen[$key]+x}" ]; then
      errors+=("line $n: duplicate key $key")
    else
      seen["$key"]="$value"
    fi
  done < "$file"
  for k in "${RESOLOOP_LOCK_KEYS[@]}"; do
    [ -n "${seen[$k]+x}" ] || errors+=("missing key $k")
  done
  case "${seen[RESOLOOP_MODE]-nuget}" in
    nuget|fork) ;;
    *) errors+=("RESOLOOP_MODE must be nuget or fork, not ${seen[RESOLOOP_MODE]}") ;;
  esac
  if [ -n "${seen[RESOLOOP_FORK_COMMIT]+x}" ] && [[ ! "${seen[RESOLOOP_FORK_COMMIT]}" =~ ^[0-9a-f]{40}$ ]]; then
    errors+=("RESOLOOP_FORK_COMMIT must be a full 40-character commit id")
  fi
  if [ -n "${seen[RESOLOOP_FORK_SDK]+x}" ] && [[ ! "${seen[RESOLOOP_FORK_SDK]}" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    errors+=("RESOLOOP_FORK_SDK must be an exact SDK version such as 10.0.201")
  fi
  if [ ${#errors[@]} -gt 0 ]; then
    printf 'resoloop.lock: %s\n' "${errors[@]}" >&2
    return 1
  fi
  for k in "${RESOLOOP_LOCK_KEYS[@]}"; do
    printf -v "$k" '%s' "${seen[$k]}"
  done
  if [ "$RESOLOOP_MODE" = fork ]; then
    RESOLOOP_EXPECTED_VERSION="$RESOLOOP_FORK_PACKAGE_VERSION"
  else
    RESOLOOP_EXPECTED_VERSION="$RESOLOOP_NUGET_VERSION"
  fi
}

# resoloop_lock_sdk_declared DEVCONTAINER_JSON SDK
# devcontainer.json の "additionalVersions"（カンマ区切り）のどれかに SDK があれば 0 を返す。
# // で始まるコメント行は読まない。
resoloop_lock_sdk_declared() {
  local json="$1" sdk="$2" list v
  local -a versions=()
  [ -f "$json" ] || return 1
  while IFS= read -r list; do
    IFS=',' read -r -a versions <<<"$list"
    for v in "${versions[@]}"; do
      [ "${v//[[:space:]]/}" = "$sdk" ] && return 0
    done
  done < <(sed -n -e '/^[[:space:]]*\/\//d' -e 's/.*"additionalVersions"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$json")
  return 1
}

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
```

`.devcontainer/devcontainer.json` は dotnet Feature だけを次のとおり変える（インデントはタブ。`test-resonite-feature.bash` が `"version": "10.0"` を Feature の次の行で探すので、`version` を先に置く）。

```diff
--- a/.devcontainer/devcontainer.json
+++ b/.devcontainer/devcontainer.json
@@ -43,7 +43,9 @@
   "features": {
 		"ghcr.io/devcontainers/features/github-cli:1": {},
 		"ghcr.io/devcontainers/features/dotnet:2": {
-			"version": "10.0"
+			"version": "10.0",
+			// resoloop fork の global.json が要求する SDK。.devcontainer/resoloop.lock の RESOLOOP_FORK_SDK と揃える
+			"additionalVersions": "10.0.201"
 		},
 		"ghcr.io/devcontainers/features/node:2": {
 		"nodeGypDependencies": true,
```

- [ ] **Step 4: テストが通ることを確かめる**

Run: `bash .devcontainer/test-resoloop-lock.bash && bash .devcontainer/test-resonite-feature.bash`
Expected: `PASS: resoloop lock and its reader behave as specified` と `PASS: .NET 10 Feature and Blender package configured`

Global Constraints の回帰確認（pytest の FAILED フィルタ、`tests/scripts`、`.devcontainer/test-*.bash`、check-layout）も実行する。

- [ ] **Step 5: コミット**

```bash
git add .devcontainer/resoloop.lock .devcontainer/resoloop-lock.bash .devcontainer/test-resoloop-lock.bash .devcontainer/devcontainer.json
git ls-files -s .devcontainer/resoloop-lock.bash .devcontainer/test-resoloop-lock.bash   # どちらも 100755
git commit -m "feat(resoloop): pin the ResoLoop version in .devcontainer/resoloop.lock"
```

---

### Task 2: `scripts/resoloop-fork.sh`（仕様 6.3）

fork の checkout（既定 `external/resoloop`）に対する `clone`・`sync`・`checkout`・`build`・`test`・`install`・`status` を 1 本のスクリプトにまとめる。テストはローカルの bare リポジトリとモックの `dotnet` だけを使い、ネットワークと実 SDK には触れない。

**Files:**
- Create: `scripts/resoloop-fork.sh`（mode 100755）
- Create: `tests/scripts/test-resoloop-fork.bash`（mode 100755）

**Interfaces:**
- Consumes: Task 1 の `resoloop_lock_load`、`resoloop_installed_version`、`resoloop_version_of`（`<リポジトリ>/.devcontainer/resoloop-lock.bash`。リポジトリはスクリプトの位置の 1 つ上）
- Produces:
  - `scripts/resoloop-fork.sh <clone|sync|checkout|build|test|install|status>`。終了コード 0 成功、1 状態の食い違い、2 使い方の誤り、3 前提不足、4 外部コマンドの失敗（詳細はスクリプト冒頭の注記）
  - 環境変数 `RESOLOOP_LOCK_FILE`（ロックファイル）と `RESOLOOP_FORK_CHECKOUT`（checkout の位置）で既定を差し替えられる。Task 3 の `install_resoloop.bash` は `RESOLOOP_LOCK_FILE` をそのまま引き継いで `install` を呼ぶ
  - `install` の最後の行は `ok: resoloop --version is <版>`、`status` は `lock:`、`mode:`、`expected version:`、`installed version:`、`lock commit:`、`checkout:`、`remotes:` の各行を出す（Task 7 の運用文書が説明する）

- [ ] **Step 1: 失敗するテストを書く**

`tests/scripts/test-resoloop-fork.bash` を次の内容で作り、`chmod +x` する。

```bash
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

printf 'PASS: resoloop-fork script behaves as specified\n'
```

- [ ] **Step 2: テストが失敗することを確かめる**

Run: `bash tests/scripts/test-resoloop-fork.bash`
Expected: 終了コード 1。`FAIL: expected exit 2, got 127:`（スクリプトが無い）

- [ ] **Step 3: スクリプトを書く**

`scripts/resoloop-fork.sh` を次の内容で作り、`chmod +x` する。

```bash
#!/bin/bash
# ResoLoop の fork を取得・追従・checkout・ビルド・導入する。
# 仕様: docs/superpowers/specs/2026-09-26-create-reso-world-redesign-design.md 6.3 節。運用手順: docs/resoloop-fork-workflow.md
# 使い方: scripts/resoloop-fork.sh <clone|sync|checkout|build|test|install|status>
# 環境変数（テストと特殊な運用向け）:
#   RESOLOOP_LOCK_FILE      ロックファイル（既定: <リポジトリ>/.devcontainer/resoloop.lock）
#   RESOLOOP_FORK_CHECKOUT  fork の checkout 先（既定: <リポジトリ>/external/resoloop）
# 終了コード:
#   0 成功
#   1 状態が期待と違う（git の checkout でない、remote の URL、未コミットの変更、コミットが origin に無い、
#     fork の main が上流から分岐、nuget モードでの install、導入後の版の不一致）
#   2 使い方の誤り
#   3 前提不足（ロックの欠落・不正、git / dotnet が無い、必要な SDK が無い、checkout が無い）
#   4 外部コマンドの失敗（git clone / fetch / push / checkout、dotnet build / pack / test / tool）
set -euo pipefail

usage() {
  printf 'usage: %s <clone|sync|checkout|build|test|install|status>\n' "${BASH_SOURCE[0]}" >&2
  exit 2
}
die() { printf 'ERROR: %s\n' "$2" >&2; exit "$1"; }
run() {  # $1=失敗時に表示する名前、残り=コマンド。失敗したら終了コード 4
  local what="$1"
  shift
  "$@" || die 4 "$what failed"
}

[ $# -eq 1 ] || usage
cmd="$1"
case "$cmd" in
  clone|sync|checkout|build|test|install|status) ;;
  *) usage ;;
esac

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
lock="${RESOLOOP_LOCK_FILE:-$root/.devcontainer/resoloop.lock}"
dir="${RESOLOOP_FORK_CHECKOUT:-$root/external/resoloop}"
# shellcheck source=../.devcontainer/resoloop-lock.bash
source "$root/.devcontainer/resoloop-lock.bash"
resoloop_lock_load "$lock" || die 3 "fix $lock first"
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

require_checkout() {
  [ -e "$dir" ] || [ -L "$dir" ] || die 3 "$dir is missing; run scripts/resoloop-fork.sh clone"
  is_checkout || die 1 "$dir exists but is not a git checkout of its own"
}

check_remotes() {  # origin と upstream をロックと比べ、食い違いを 1 件 1 行で出力する。食い違いがあれば 1
  local name want got bad=0
  for name in origin upstream; do
    if [ "$name" = origin ]; then want="$RESOLOOP_FORK_ORIGIN"; else want="$RESOLOOP_FORK_UPSTREAM"; fi
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
    is_checkout || die 1 "$dir exists but is not a git checkout of its own"
    require_remotes
    printf 'ok: %s is already cloned (origin and upstream match the lock)\n' "$dir"
    return
  fi
  run 'git clone' git clone --quiet --origin origin -- "$RESOLOOP_FORK_ORIGIN" "$dir"
  run 'git remote add upstream' git -C "$dir" remote add upstream "$RESOLOOP_FORK_UPSTREAM"
  run 'git fetch upstream' git -C "$dir" fetch --quiet upstream
  printf 'cloned: %s (origin %s, upstream %s)\n' "$dir" "$RESOLOOP_FORK_ORIGIN" "$RESOLOOP_FORK_UPSTREAM"
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
    run 'git merge --ff-only' git -C "$dir" merge --quiet --ff-only "$up"
  else
    run 'git branch -f main' git -C "$dir" branch --quiet -f main "$up"
  fi
  printf 'updated: local main -> %s\n' "$up"
}

do_checkout() {
  local commit="$RESOLOOP_FORK_COMMIT"
  require_checkout
  require_remotes
  dirty && die 1 "$dir has uncommitted changes to tracked files; commit or stash them before checking out $commit"
  if ! git -C "$dir" cat-file -e "$commit^{commit}" 2>/dev/null; then
    run 'git fetch origin' git -C "$dir" fetch --quiet origin
    git -C "$dir" cat-file -e "$commit^{commit}" 2>/dev/null \
      || die 1 "commit $commit is not on origin ($RESOLOOP_FORK_ORIGIN); push it to the fork first"
  fi
  if [ "$(git -C "$dir" rev-parse HEAD)" = "$commit" ] && ! git -C "$dir" symbolic-ref -q HEAD >/dev/null; then
    printf 'ok: %s is already at %s (detached)\n' "$dir" "$commit"
    return
  fi
  run 'git checkout' git -C "$dir" checkout --quiet --detach "$commit"
  printf 'checked out: %s at %s (detached)\n' "$dir" "$commit"
}

require_sdk() {  # fork の global.json が要求する SDK（RESOLOOP_FORK_SDK）があることを確かめる
  local sdks
  command -v dotnet >/dev/null 2>&1 || die 3 "dotnet not found"
  sdks="$(dotnet --list-sdks </dev/null)" || die 4 "dotnet --list-sdks failed"
  awk -v want="$RESOLOOP_FORK_SDK" '$1 == want { found = 1 } END { exit !found }' <<<"$sdks" \
    || die 3 ".NET SDK $RESOLOOP_FORK_SDK is not installed; it comes from additionalVersions of the dotnet feature in .devcontainer/devcontainer.json (rebuild the container)"
}

# dotnet は global.json をカレントディレクトリから探すため、ビルドとテストは checkout に cd して実行する
do_build() {
  local version="$RESOLOOP_FORK_PACKAGE_VERSION"
  require_checkout
  require_sdk
  (cd "$dir" && run 'dotnet build' dotnet build ResoLoop.slnx -c Release --nologo </dev/null)
  (cd "$dir" && run 'dotnet pack' dotnet pack src/RLoop.Cli/RLoop.Cli.csproj -c Release --nologo \
    -o artifacts/fork "-p:PackageVersion=$version" "-p:Version=$version" </dev/null)
  [ -f "$dir/artifacts/fork/ResoLoop.$version.nupkg" ] \
    || die 4 "dotnet pack did not produce artifacts/fork/ResoLoop.$version.nupkg"
  printf 'built: %s/artifacts/fork/ResoLoop.%s.nupkg\n' "$dir" "$version"
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
  [ "$actual" = "$1" ] || die 1 "resoloop --version reports $actual, but the lock expects $1"
  printf 'ok: resoloop --version is %s\n' "$actual"
}

do_install() {
  local want="$RESOLOOP_FORK_PACKAGE_VERSION" installed verb=install
  [ "$RESOLOOP_MODE" = fork ] \
    || die 1 "RESOLOOP_MODE is $RESOLOOP_MODE; run bash .devcontainer/install_resoloop.bash to install the NuGet release"
  command -v dotnet >/dev/null 2>&1 || die 3 "dotnet not found"
  installed="$(resoloop_installed_version)" || die 4 "dotnet tool list --global failed"
  if [ "$installed" = "$want" ]; then
    printf 'ok: ResoLoop %s is already installed (to install a rebuilt package, raise RESOLOOP_FORK_PACKAGE_VERSION in the lock)\n' "$want"
  else
    do_clone
    do_checkout
    do_build
    [ -z "$installed" ] || verb=update
    (cd "$root" && run "dotnet tool $verb" dotnet tool "$verb" --global ResoLoop \
      --add-source "$dir/artifacts/fork" --version "$want" --allow-downgrade </dev/null)
    printf 'installed: ResoLoop %s from %s/artifacts/fork\n' "$want" "$dir"
  fi
  verify_installed "$want"
}

do_status() {
  local installed head branch state problems
  printf 'lock: %s\n' "$lock"
  printf 'mode: %s\n' "$RESOLOOP_MODE"
  printf 'expected version: %s\n' "$RESOLOOP_EXPECTED_VERSION"
  if ! command -v dotnet >/dev/null 2>&1; then
    printf 'installed version: unknown (dotnet not found)\n'
  elif ! installed="$(resoloop_installed_version)"; then
    printf 'installed version: unknown (dotnet tool list --global failed)\n'
  elif [ -z "$installed" ]; then
    printf 'installed version: none\n'
  elif [ "$installed" = "$RESOLOOP_EXPECTED_VERSION" ]; then
    printf 'installed version: %s (matches the lock)\n' "$installed"
  else
    printf 'installed version: %s (DIFFERS from the lock)\n' "$installed"
  fi
  printf 'lock commit: %s (%s)\n' "$RESOLOOP_FORK_COMMIT" "$RESOLOOP_FORK_REF"
  if [ ! -e "$dir" ] && [ ! -L "$dir" ]; then
    printf 'checkout: %s is missing (run scripts/resoloop-fork.sh clone)\n' "$dir"
    return
  fi
  if ! is_checkout; then
    printf 'checkout: %s exists but is not a git checkout of its own\n' "$dir"
    return
  fi
  head="$(git -C "$dir" rev-parse -q --verify HEAD || printf 'none')"
  branch="$(git -C "$dir" symbolic-ref -q --short HEAD || printf 'detached')"
  if dirty; then state='uncommitted changes'; else state='clean'; fi
  if [ "$head" = "$RESOLOOP_FORK_COMMIT" ]; then
    printf 'checkout: %s at %s (%s, %s, matches the lock)\n' "$dir" "$head" "$branch" "$state"
  else
    printf 'checkout: %s at %s (%s, %s, DIFFERS from the lock)\n' "$dir" "$head" "$branch" "$state"
  fi
  if problems="$(check_remotes)"; then
    printf 'remotes: origin and upstream match the lock\n'
  else
    printf 'remotes: %s\n' "${problems//$'\n'/; }"
  fi
}

"do_$cmd"
```

- [ ] **Step 4: テストが通ることを確かめる**

Run: `bash tests/scripts/test-resoloop-fork.bash`
Expected: `PASS: resoloop-fork script behaves as specified`

実ロックに対しては `status` だけを実行してよい: `bash scripts/resoloop-fork.sh status` は `installed version: 0.1.0-preview.14.pr1.20260925 (matches the lock)` と `checkout: .../external/resoloop is missing (run scripts/resoloop-fork.sh clone)` を表示して終了コード 0。Global Constraints の回帰確認も実行する。

- [ ] **Step 5: コミット**

```bash
git add scripts/resoloop-fork.sh tests/scripts/test-resoloop-fork.bash
git ls-files -s scripts/resoloop-fork.sh tests/scripts/test-resoloop-fork.bash   # どちらも 100755
git commit -m "feat(resoloop): add resoloop-fork.sh to clone, sync, build and install the fork"
```

---

### Task 3: ロックに従う導入と確認（仕様 6.2）

`install_resoloop.bash` を、ロックの期待版を導入する形に書き換える（nuget モードは `dotnet tool install|update --version`、fork モードは `scripts/resoloop-fork.sh install` に任せる）。`verify-resonite-tooling.bash` は `resoloop --version` がロックと一致することも確かめる。postCreate の手順名と `.devcontainer/README.md` の該当段落を、変わった挙動に合わせる（判断事項 D-8）。

**Files:**
- Modify（全体を置き換え）: `.devcontainer/install_resoloop.bash`、`.devcontainer/test-install-resoloop.bash`、`.devcontainer/verify-resonite-tooling.bash`、`.devcontainer/test-verify-resonite-tooling.bash`
- Modify: `.devcontainer/install_beforehand.bash`（ResoLoop の手順名の 1 行だけ）、`.devcontainer/README.md`（「Resonite ワールド開発ツール」節の 2 か所だけ）

**Interfaces:**
- Consumes: Task 1 の関数、Task 2 の `scripts/resoloop-fork.sh install` と環境変数 `RESOLOOP_LOCK_FILE`
- Produces: `install_resoloop.bash` と `verify-resonite-tooling.bash` は `RESOLOOP_LOCK_FILE` でロックを差し替えられる（テスト用）。postCreate の手順名は `Installing the ResoLoop version pinned in .devcontainer/resoloop.lock`

- [ ] **Step 1: 失敗するテストを書く**

`.devcontainer/test-install-resoloop.bash` を次の内容に置き換える（mode は 100755 のまま）。

```bash
#!/bin/bash
# .devcontainer/install_resoloop.bash が仕様 6.2 節の表どおりに動くことを、モックの dotnet と一時ロックで検査する
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
tmp="$(mktemp -d)"
trap 'rm -rf -- "$tmp"' EXIT
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }

# モックの dotnet: 呼び出しを DOTNET_CALLS に記録する。tool install/update は MOCK_STATE に版を書き、
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
  'tool install --global ResoLoop --version '*|'tool update --global ResoLoop --version '*)
    printf '%s\n' "$*" >> "$DOTNET_CALLS"
    [ "${DOTNET_INSTALL_FAIL:-0}" = 0 ] || exit 16
    ver="$6"
    printf '%s\n' "$ver" > "$MOCK_STATE"
    printf '#!/bin/bash\nprintf "%%s\\n" %q\n' "${MOCK_SHIM_VERSION:-$ver}" > "$HOME/.dotnet/tools/resoloop"
    chmod +x "$HOME/.dotnet/tools/resoloop" ;;
  *) printf 'Unexpected dotnet invocation: %s\n' "$*" >&2; exit 17 ;;
esac
MOCK
chmod +x "$tmp/bin/dotnet"
export HOME="$tmp/home" PATH="$tmp/bin:$PATH" DOTNET_CALLS="$tmp/calls" MOCK_STATE="$tmp/installed"

write_lock() {  # $1=モード。nuget の期待版は 1.2.3-preview.4、fork の期待版は 1.2.3-preview.4.pr1.test
  cat > "$tmp/resoloop.lock" <<EOF
RESOLOOP_MODE=$1
RESOLOOP_NUGET_VERSION=1.2.3-preview.4
RESOLOOP_FORK_ORIGIN=https://example.com/fork/resoloop.git
RESOLOOP_FORK_UPSTREAM=https://example.com/upstream/resoloop.git
RESOLOOP_FORK_REF=fix/x
RESOLOOP_FORK_COMMIT=0123456789abcdef0123456789abcdef01234567
RESOLOOP_FORK_PACKAGE_VERSION=1.2.3-preview.4.pr1.test
RESOLOOP_FORK_PR=https://example.com/upstream/resoloop/pull/1
RESOLOOP_FORK_SDK=10.0.201
EOF
}
export RESOLOOP_LOCK_FILE="$tmp/resoloop.lock"
reset() {  # 未導入の状態に戻す
  : > "$DOTNET_CALLS"
  : > "$MOCK_STATE"
  rm -f "$HOME/.dotnet/tools/resoloop"
}
installer="$root/.devcontainer/install_resoloop.bash"
expect_fail() {  # $1=出力に含まれるべき文字列、残り=環境変数の代入（env に渡す）
  local needle="$1" out
  shift
  if out="$(env "$@" bash "$installer" 2>&1)"; then fail "installer succeeded (expected: $needle)"; fi
  grep -qF -- "$needle" <<<"$out" || fail "expected '$needle' in: $out"
}
expect_ok() {  # $1=出力に含まれるべき文字列、残り=環境変数の代入（env に渡す）
  local needle="$1" out
  shift
  out="$(env "$@" bash "$installer" 2>&1)" || fail "installer failed (expected: $needle): $out"
  grep -qF -- "$needle" <<<"$out" || fail "expected '$needle' in: $out"
}

# 1. nuget モード・未導入: ロックの版を --version で指定して install する
write_lock nuget
reset
expect_ok 'resoloop 1.2.3-preview.4 matches the lock'
grep -qx 'tool install --global ResoLoop --version 1.2.3-preview.4' "$DOTNET_CALLS" || fail 'nuget install call'

# 2. nuget モード・同じ版を導入済み: 何もせず、--version の照合だけ行う
: > "$DOTNET_CALLS"
expect_ok '1.2.3-preview.4 is already installed'
[ ! -s "$DOTNET_CALLS" ] || fail 'reinstalled an installed version'
printf '#!/bin/bash\nprintf "0.0.1\\n"\n' > "$HOME/.dotnet/tools/resoloop"
expect_fail 'resoloop --version reports 0.0.1, but'

# 3. nuget モード・別の版を導入済み: --allow-downgrade 付きで update する（ダウングレードも含む）
reset
printf '9.0.0\n' > "$MOCK_STATE"
expect_ok 'matches the lock'
grep -qx 'tool update --global ResoLoop --version 1.2.3-preview.4 --allow-downgrade' "$DOTNET_CALLS" || fail 'nuget update call'

# 4. 名前の一部だけが一致するパッケージは未導入として扱う
reset
expect_ok 'matches the lock' DOTNET_LIST_LINE='my-resoloop-plugin 1.0.0 other'
grep -qx 'tool install --global ResoLoop --version 1.2.3-preview.4' "$DOTNET_CALLS" || fail 'partial match treated as installed'

# 5. 導入後の --version がロックと違えば失敗する
reset
expect_fail 'resoloop --version reports 0.0.2, but' MOCK_SHIM_VERSION=0.0.2

# 6. 失敗の伝達: 一覧取得の失敗（何も導入しない）、install / update の失敗、SDK が無い・一覧が取れない、shim が無い、ロックが不正
reset
expect_fail 'cannot list global .NET tools' DOTNET_LIST_FAIL=1
[ ! -s "$DOTNET_CALLS" ] || fail 'installed although the tool list failed'
expect_fail 'installing the global tool 1.2.3-preview.4 failed' DOTNET_INSTALL_FAIL=1
reset
printf '9.0.0\n' > "$MOCK_STATE"
expect_fail 'updating the global tool from 9.0.0 to 1.2.3-preview.4 failed' DOTNET_INSTALL_FAIL=1
reset
expect_fail '.NET 10 SDK is not installed' 'DOTNET_SDKS=8.0.100 [/usr/share/dotnet/sdk]'
expect_fail 'cannot list .NET SDKs' DOTNET_SDK_FAIL=1
printf '1.2.3-preview.4\n' > "$MOCK_STATE"
expect_fail 'installed CLI cannot run on this container'
sed -i '/^RESOLOOP_FORK_SDK=/d' "$tmp/resoloop.lock"
expect_fail 'cannot read'

# 7. fork モード: 導入済みの版が違えば scripts/resoloop-fork.sh install に任せ、同じなら呼ばない
#    （install_resoloop.bash は自分の位置からリポジトリを決めるので、一時リポジトリへ写して実行する）
mkdir -p "$tmp/repo/.devcontainer" "$tmp/repo/scripts"
cp "$installer" "$root/.devcontainer/resoloop-lock.bash" "$tmp/repo/.devcontainer/"
cat > "$tmp/repo/scripts/resoloop-fork.sh" <<'MOCK'
#!/bin/bash
printf 'fork %s lock=%s\n' "$*" "$RESOLOOP_LOCK_FILE" >> "$DOTNET_CALLS"
[ "${FORK_FAIL:-0}" = 0 ] || exit 4
printf '1.2.3-preview.4.pr1.test\n' > "$MOCK_STATE"
printf '#!/bin/bash\nprintf "1.2.3-preview.4.pr1.test\\n"\n' > "$HOME/.dotnet/tools/resoloop"
chmod +x "$HOME/.dotnet/tools/resoloop"
MOCK
installer="$tmp/repo/.devcontainer/install_resoloop.bash"
write_lock fork
reset
printf '1.2.3-preview.4\n' > "$MOCK_STATE"
expect_ok 'resoloop 1.2.3-preview.4.pr1.test matches the lock'
grep -qx "fork install lock=$tmp/resoloop.lock" "$DOTNET_CALLS" || fail 'fork mode did not delegate to resoloop-fork.sh install'
if grep -q '^tool ' "$DOTNET_CALLS"; then fail 'fork mode ran dotnet tool itself'; fi
: > "$DOTNET_CALLS"
expect_ok '1.2.3-preview.4.pr1.test is already installed'
[ ! -s "$DOTNET_CALLS" ] || fail 'fork mode rebuilt an installed version'
reset
expect_fail 'building and installing the fork failed' FORK_FAIL=1

printf 'PASS: ResoLoop install follows the lock (nuget and fork modes, failures)\n'
```

`.devcontainer/test-verify-resonite-tooling.bash` を次の内容に置き換える。

```bash
#!/bin/bash
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
tmp="$(mktemp -d)"
trap 'rm -rf -- "$tmp"' EXIT
# shellcheck source=resoloop-lock.bash
source "$root/.devcontainer/resoloop-lock.bash"
resoloop_lock_load "$root/.devcontainer/resoloop.lock"
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
export PATH="$tmp/bin:$PATH" MOCK_RESOLOOP_VERSION="$RESOLOOP_EXPECTED_VERSION"
bash "$root/.devcontainer/verify-resonite-tooling.bash"
if RESOLOOP_FAIL=1 bash "$root/.devcontainer/verify-resonite-tooling.bash"; then exit 1; fi
if BLENDER_FAIL=1 bash "$root/.devcontainer/verify-resonite-tooling.bash"; then exit 1; fi
# resoloop の版がロックの期待版と違えば失敗し、両方の版を表示する
if out="$(MOCK_RESOLOOP_VERSION=0.0.1 bash "$root/.devcontainer/verify-resonite-tooling.bash" 2>&1)"; then exit 1; fi
grep -qF "resoloop reports 0.0.1, but $root/.devcontainer/resoloop.lock expects $RESOLOOP_EXPECTED_VERSION" <<<"$out"
# ロックが読めなければ失敗する
if RESOLOOP_LOCK_FILE="$tmp/missing.lock" bash "$root/.devcontainer/verify-resonite-tooling.bash" 2>/dev/null; then exit 1; fi
installer="$root/.devcontainer/install_beforehand.bash"
grep -qF 'bash .devcontainer/install_resoloop.bash' "$installer"
grep -qF 'bash .devcontainer/verify-resonite-tooling.bash' "$installer"
grep -qF 'step "Installing the ResoLoop version pinned in .devcontainer/resoloop.lock"' "$installer"
declared_steps="$(sed -n 's/^readonly STEP_TOTAL=//p' "$installer")"
actual_steps="$(grep -c '^step "' "$installer")"
[ "$declared_steps" -eq "$actual_steps" ]
grep -qF 'PATH="$HOME/.dotnet/tools:$PATH"' "$root/.devcontainer/zshrc.txt"
printf 'PASS: toolchain smoke test and postCreate integration\n'
```

- [ ] **Step 2: テストが失敗することを確かめる**

Run: `bash .devcontainer/test-install-resoloop.bash; bash .devcontainer/test-verify-resonite-tooling.bash`
Expected: 1 本目は `FAIL: installer failed (expected: resoloop 1.2.3-preview.4 matches the lock): Unexpected dotnet invocation: tool install --global ResoLoop --prerelease`。2 本目は終了コード 1（旧 verify は版を比べないので、版の食い違いのケースで止まる）

- [ ] **Step 3: 導入と確認のスクリプトを書き換える**

`.devcontainer/install_resoloop.bash` を次の内容に置き換える。

```bash
#!/bin/bash
# .devcontainer/resoloop.lock が指定する版の ResoLoop を導入する。
# 仕様: docs/superpowers/specs/2026-09-26-create-reso-world-redesign-design.md 6.2 節
# 環境変数 RESOLOOP_LOCK_FILE でロックファイルを差し替えられる（テスト用。fork モードでは scripts/resoloop-fork.sh にも引き継がれる）
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
lock="${RESOLOOP_LOCK_FILE:-$root/.devcontainer/resoloop.lock}"
fail() { printf 'ResoLoop setup: %s\n' "$1" >&2; exit 1; }
# shellcheck source=resoloop-lock.bash
source "$root/.devcontainer/resoloop-lock.bash"
resoloop_lock_load "$lock" || fail "cannot read $lock."
expected="$RESOLOOP_EXPECTED_VERSION"

command -v dotnet >/dev/null 2>&1 || fail 'dotnet is not available.'
sdks="$(dotnet --list-sdks </dev/null)" || fail 'cannot list .NET SDKs.'
grep -qE '^10\.' <<<"$sdks" || fail '.NET 10 SDK is not installed.'
installed="$(resoloop_installed_version)" || fail 'cannot list global .NET tools.'

if [ "$installed" = "$expected" ]; then
    printf 'ResoLoop setup: %s is already installed.\n' "$expected"
elif [ "$RESOLOOP_MODE" = fork ]; then
    bash "$root/scripts/resoloop-fork.sh" install </dev/null \
        || fail 'building and installing the fork failed (check with bash scripts/resoloop-fork.sh status).'
elif [ -n "$installed" ]; then
    dotnet tool update --global ResoLoop --version "$expected" --allow-downgrade </dev/null \
        || fail "updating the global tool from $installed to $expected failed."
else
    dotnet tool install --global ResoLoop --version "$expected" </dev/null \
        || fail "installing the global tool $expected failed."
fi

# PATH 上の別の resoloop で誤って通らないよう、グローバルツールの配置先を直接呼ぶ
out="$("$HOME/.dotnet/tools/resoloop" --version </dev/null)" || fail 'installed CLI cannot run on this container.'
actual="$(resoloop_version_of "$out")" || fail 'resoloop --version printed nothing.'
[ "$actual" = "$expected" ] || fail "resoloop --version reports $actual, but $lock expects $expected."
printf 'ResoLoop setup: resoloop %s matches the lock.\n' "$actual"
```

`.devcontainer/verify-resonite-tooling.bash` を次の内容に置き換える。

```bash
#!/bin/bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
lock="${RESOLOOP_LOCK_FILE:-$root/.devcontainer/resoloop.lock}"
# shellcheck source=resoloop-lock.bash
source "$root/.devcontainer/resoloop-lock.bash"

if ! dotnet --list-sdks | grep -qE '^10\.'; then
    echo 'Toolchain verification: .NET 10 SDK is unavailable.' >&2
    exit 1
fi
if ! resoloop_lock_load "$lock"; then
    echo "Toolchain verification: cannot read $lock." >&2
    exit 1
fi
if ! version_output="$(resoloop --version </dev/null)"; then
    echo 'Toolchain verification: resoloop cannot run.' >&2
    exit 1
fi
actual="$(resoloop_version_of "$version_output" || true)"
if [ "$actual" != "$RESOLOOP_EXPECTED_VERSION" ]; then
    echo "Toolchain verification: resoloop reports ${actual:-nothing}, but $lock expects $RESOLOOP_EXPECTED_VERSION." >&2
    exit 1
fi
if ! blender --background --factory-startup --python-exit-code 1 \
    --python-expr 'import bpy; assert bpy.app.background' </dev/null; then
    echo 'Toolchain verification: Blender cannot run headlessly.' >&2
    exit 1
fi
```

`.devcontainer/install_beforehand.bash` は手順名の 1 行だけを変える（`STEP_TOTAL` と手順の数は変わらない）。

```diff
--- a/.devcontainer/install_beforehand.bash
+++ b/.devcontainer/install_beforehand.bash
@@ -90,7 +90,7 @@ if ! sudo apt install -y vim tig ripgrep fzf bubblewrap libglib2.0-0t64 blender;
     fail "apt install of the base packages failed."
 fi
 
-step "Installing or updating the latest ResoLoop tool"
+step "Installing the ResoLoop version pinned in .devcontainer/resoloop.lock"
 export PATH="${HOME}/.dotnet/tools:${PATH}"
 if ! bash .devcontainer/install_resoloop.bash; then
     fail "ResoLoop installation or update failed."
```

`.devcontainer/README.md` は「Resonite ワールド開発ツール」節の 2 か所だけを変える。節のそれ以外と、ファイルの他の節はフェーズ 4 で扱う。

````diff
--- a/.devcontainer/README.md
+++ b/.devcontainer/README.md
@@ -17,7 +17,9 @@ Herdr の復元手順は `.devcontainer/docs/herdr-session-cwd-restore.md` を
 ## Resonite ワールド開発ツール
 
 Dev Container の作成時に .NET 10 SDK と Blender を導入し、ResoLoop を
-プレビュー版を含む利用可能な最新版へインストールまたは更新する。
+`.devcontainer/resoloop.lock` が指定する版で導入する。既定の fork モードでは
+`scripts/resoloop-fork.sh install` が fork を `external/resoloop` に取得してビルドするため、
+ネットワークと数分の時間を要する。版の変え方と fork の運用は `docs/resoloop-fork-workflow.md` を参照する。
 Blender は画面を開かずに実行する。Resonite 本体と ResoniteLink は
 Windows ホスト側で準備する。接続確認の `resoloop doctor`、
 Blender の GUI、ホスト側のネットワーク設定はこのセットアップの対象外とする。
@@ -28,6 +30,7 @@ Blender の GUI、ホスト側のネットワーク設定はこのセットア
 dotnet --list-sdks
 resoloop --version
 bash .devcontainer/verify-resonite-tooling.bash
+bash scripts/resoloop-fork.sh status
 ```
 
 ResoLoop の公式要件には Windows 10/11 が記載されている。Linux で
````

- [ ] **Step 4: テストが通ることを確かめる**

Run: `bash .devcontainer/test-install-resoloop.bash && bash .devcontainer/test-verify-resonite-tooling.bash`
Expected: `PASS: ResoLoop install follows the lock (nuget and fork modes, failures)` と `PASS: toolchain smoke test and postCreate integration`（2 本目の途中に、失敗ケースが出す `Toolchain verification: ...` の行が混ざるのは想定どおり）

実環境の確認（読み取りだけ）: `bash .devcontainer/verify-resonite-tooling.bash; echo $?` が 0（導入済みの resoloop がロックの期待版と一致し、Blender が画面なしで動く）。`install_resoloop.bash` はモック無しでは実行しない。Global Constraints の回帰確認も実行する。

- [ ] **Step 5: コミット**

```bash
git add .devcontainer/install_resoloop.bash .devcontainer/test-install-resoloop.bash \
  .devcontainer/verify-resonite-tooling.bash .devcontainer/test-verify-resonite-tooling.bash \
  .devcontainer/install_beforehand.bash .devcontainer/README.md
git commit -m "feat(devcontainer): install and verify the ResoLoop version from the lock"
```

---

### Task 4: check-layout を index の内容で判定し、resoloop の出力を中継する（持ち越し N-15、N-9 の 3 点目、N-10）

check-layout の内容の読み取りを index に揃え（判断事項 D-6）、フェーズ 2 のレビューで持ち越した細かい不具合を直す。`resoloop skills sync --check` が失敗したときは、その出力を字下げして示す。リンクが要るディレクトリの定義をコメントに書く（N-10。new-world.sh 側は Task 6）。

**Files:**
- Modify（全体を置き換え）: `scripts/check-layout.sh`
- Modify: `tests/scripts/test-check-layout.bash`（`project_repo` の引数、モックの resoloop、ケース 23 の追記、ケース 33〜42 の追加）

**Interfaces:**
- Produces（Task 5 が使う）: `index_entry PATH` — index にパスと完全に一致するエントリがあれば `"<mode> <oid>"` を出力して 0、無ければ 1。グローバル変数 `tmp_list`（NUL 区切りの一覧を受け渡す一時ファイル）
- テストの `project_repo DIR [NAME]` は第 2 引数でプロジェクト名を変えられる（既定 `demo`）

- [ ] **Step 1: 失敗するテストを書く**

`tests/scripts/test-check-layout.bash` を次の差分のとおりに変える（`git apply` を使ってもよい）。

```diff
--- a/tests/scripts/test-check-layout.bash
+++ b/tests/scripts/test-check-layout.bash
@@ -167,9 +167,10 @@
 printf '[core]\n\texcludesFile = %s\n' "$tmp/global-ignore" > "$tmp/global-gitconfig"
 GIT_CONFIG_COUNT=0 GIT_CONFIG_GLOBAL="$tmp/global-gitconfig" bash "$checker" --root "$tmp/clean" | grep -qF 'PASS: check-layout'
 
-# 仕様 4.2 を満たすプロジェクト demo を 1 つ持つリポジトリを作る
+# 仕様 4.2 を満たすプロジェクトを 1 つ持つリポジトリを作る。$2 はプロジェクト名（既定: demo）
 project_repo() {
-  local r="$1" p="$1/demo"
+  local r="$1" n="${2:-demo}"
+  local p="$r/$n"
   new_repo "$r"
   mkdir -p "$r/.claude" "$r/.pi" "$r/.agents" "$p/.agents/skills/resonite-build" "$p/.claude/skills" "$p/.resoloop" "$p/flux"
   printf '{}\n' > "$r/.claude/settings.json"
@@ -179,7 +180,7 @@
   printf '@AGENTS.md\n' > "$p/CLAUDE.md"
   printf '{}\n' > "$p/.resoloop.json"
   printf 'state/\nflux-state/\ncache/\n' > "$p/.resoloop/.gitignore"
-  printf '[project]\nname = "demo"\n' > "$p/pyproject.toml"
+  printf '[project]\nname = "%s"\n' "$n" > "$p/pyproject.toml"
   printf 'version = 1\n' > "$p/uv.lock"
   printf '{}\n' > "$p/.agents/skills/.resoloop-bundled.json"
   printf -- '---\nname: resonite-build\ndescription: d\n---\n' > "$p/.agents/skills/resonite-build/SKILL.md"
@@ -188,14 +189,16 @@
   ln -s ../../.claude/settings.json "$p/.claude/settings.json"
   ln -s ../.pi "$p/.pi"
   ln -s ../../.agents/sp-implementer.md "$p/.agents/sp-implementer.md"
-  commit_paths "$r" .claude .pi .agents demo
+  commit_paths "$r" .claude .pi .agents "$n"
 }
 
-# モックの resoloop: MOCK_RESOLOOP_FAIL と同名のプロジェクトだけ skills sync --check に失敗する
+# モックの resoloop: MOCK_RESOLOOP_FAIL と同名のプロジェクトだけ skills sync --check に失敗する。
+# 実物と同じく、- で始まるプロジェクト引数はオプションと解釈して拒む
 mkdir -p "$tmp/mockbin"
 cat > "$tmp/mockbin/resoloop" <<'EOF'
 #!/bin/bash
 [ "$1 $2 $4" = 'skills sync --check' ] || exit 64
+case "$3" in -*) echo "unknown option $3" >&2; exit 64 ;; esac
 case "$3" in "${MOCK_RESOLOOP_FAIL:-__none__}"|*/"${MOCK_RESOLOOP_FAIL:-__none__}") echo 'SKILL_SYNC_REQUIRED' >&2; exit 6 ;; esac
 exit 0
 EOF
@@ -219,6 +222,7 @@
 
 # 23. resoloop 同梱スキルの同期ずれは失敗する
 PATH="$mock_path" MOCK_RESOLOOP_FAIL=demo expect_fail_with "$tmp/proj-ok" 'resoloop skills sync --check failed for demo'
+grep -qxF '    SKILL_SYNC_REQUIRED' "$tmp/out.txt" || { cat "$tmp/out.txt" >&2; printf 'FAIL: resoloop output was not relayed\n' >&2; exit 1; }
 
 # 24〜30. 標準レイアウトからの逸脱は失敗する（以降は mock の resoloop で実行する）
 export PATH="$mock_path"
@@ -255,4 +259,82 @@
 grep -qF 'ok: project demo layout' "$tmp/p32.out"
 grep -qF 'PASS: check-layout' "$tmp/p32.out"
 
+# 33. .agents/skills 直下のファイルはリンクの対象外
+skill_repo "$tmp/direct-file"
+ln -s ../../.agents/skills/foo "$tmp/direct-file/.claude/skills/foo"
+printf '# index\n' > "$tmp/direct-file/.agents/skills/README.md"
+commit_paths "$tmp/direct-file" .agents .claude
+bash "$checker" --root "$tmp/direct-file" | grep -qF 'PASS: check-layout'
+
+# 34. .claude/skills/<name> が通常ファイル（mode 100644）なら失敗する
+skill_repo "$tmp/regular-file"
+printf '../../.agents/skills/foo\n' > "$tmp/regular-file/.claude/skills/foo"
+commit_paths "$tmp/regular-file" .agents .claude
+expect_fail_with "$tmp/regular-file" '.claude/skills/foo is not a symlink'
+
+# 35. .claude/skills 自体が symlink なら、そのことを失敗として示す
+skill_repo "$tmp/skills-dir-link"
+rmdir "$tmp/skills-dir-link/.claude/skills"
+ln -s ../.agents/skills "$tmp/skills-dir-link/.claude/skills"
+commit_paths "$tmp/skills-dir-link" .agents .claude
+expect_fail_with "$tmp/skills-dir-link" '.claude/skills must be a directory, not a symlink'
+if grep -qF '.claude/skills/.claude' "$tmp/out.txt"; then printf 'FAIL: misleading message for a symlinked .claude/skills\n' >&2; exit 1; fi
+
+# 36. 足りないリンクは名前順に報告する
+skill_repo "$tmp/order"
+for s in zeta alpha mid beta omega kappa delta; do   # bash の連想配列の列挙順が名前順にならない組
+  mkdir -p "$tmp/order/.agents/skills/$s" && printf -- '---\nname: %s\n---\n' "$s" > "$tmp/order/.agents/skills/$s/SKILL.md"
+done
+commit_paths "$tmp/order" .agents
+expect_fail_with "$tmp/order" 'missing link alpha'
+[ "$(grep -o 'missing link [a-z]*' "$tmp/out.txt" | sed 's/^missing link //' | tr '\n' ' ')" = 'alpha beta delta foo kappa mid omega zeta ' ] \
+  || { cat "$tmp/out.txt" >&2; printf 'FAIL: missing links are not sorted\n' >&2; exit 1; }
+
+# 37. プロジェクトの .claude/skills でも、余分・向き違い・実ディレクトリを検出する
+project_repo "$tmp/p37a"
+mkdir -p "$tmp/p37a/elsewhere/extra" && printf 'x\n' > "$tmp/p37a/elsewhere/extra/SKILL.md"
+ln -s ../../../elsewhere/extra "$tmp/p37a/demo/.claude/skills/extra"
+commit_paths "$tmp/p37a" elsewhere demo
+expect_fail_with "$tmp/p37a" 'demo/.claude/skills/extra has no matching demo/.agents/skills/extra'
+project_repo "$tmp/p37b"
+rm "$tmp/p37b/demo/.claude/skills/resonite-build" && ln -s ../../../.agents/skills/resonite-build "$tmp/p37b/demo/.claude/skills/resonite-build"
+commit_paths "$tmp/p37b" demo
+expect_fail_with "$tmp/p37b" 'demo/.claude/skills/resonite-build has unexpected target ../../../.agents/skills/resonite-build'
+project_repo "$tmp/p37c"
+rm "$tmp/p37c/demo/.claude/skills/resonite-build" && mkdir "$tmp/p37c/demo/.claude/skills/resonite-build"
+cp "$tmp/p37c/demo/.agents/skills/resonite-build/SKILL.md" "$tmp/p37c/demo/.claude/skills/resonite-build/SKILL.md"
+commit_paths "$tmp/p37c" demo
+expect_fail_with "$tmp/p37c" 'demo/.claude/skills/resonite-build is not a symlink'
+
+# 38. CLAUDE.md は @AGENTS.md の 1 行だけ（末尾の空行も認めない）
+project_repo "$tmp/p38" && printf '@AGENTS.md\n\n\n' > "$tmp/p38/demo/CLAUDE.md" && commit_paths "$tmp/p38" demo
+expect_fail_with "$tmp/p38" 'demo: CLAUDE.md must be exactly @AGENTS.md'
+
+# 39. 必須ファイルと同名のディレクトリ（demo/uv.lock/x）は必須ファイルとして数えない
+project_repo "$tmp/p39" && git -C "$tmp/p39" rm -q demo/uv.lock
+mkdir -p "$tmp/p39/demo/uv.lock" && printf 'x\n' > "$tmp/p39/demo/uv.lock/x" && commit_paths "$tmp/p39" demo
+expect_fail_with "$tmp/p39" 'demo: missing tracked file uv.lock'
+
+# 40. - で始まるプロジェクト名も検査でき、resoloop には ./ 付きで渡す
+project_repo "$tmp/p40" -dash
+bash "$checker" --root "$tmp/p40" > "$tmp/p40.out"
+grep -qF 'ok: project -dash layout' "$tmp/p40.out"
+grep -qF 'ok: resoloop skills sync --check (-dash)' "$tmp/p40.out"
+
+# 41. 作業ツリーだけの変更は結果を変えない（index の内容で判定する）
+project_repo "$tmp/p41a" && printf 'other\n' > "$tmp/p41a/demo/CLAUDE.md" && commit_paths "$tmp/p41a" demo
+printf '@AGENTS.md\n' > "$tmp/p41a/demo/CLAUDE.md"
+expect_fail_with "$tmp/p41a" 'demo: CLAUDE.md must be exactly @AGENTS.md'
+skill_repo "$tmp/p41b"
+ln -s ../../.agents/skills/foo "$tmp/p41b/.claude/skills/foo"
+commit_paths "$tmp/p41b" .agents .claude
+rm "$tmp/p41b/.agents/skills/foo/SKILL.md"
+bash "$checker" --root "$tmp/p41b" > "$tmp/p41b.out" 2>&1 || true
+if grep -qF 'empty tracked file:' "$tmp/p41b.out"; then printf 'FAIL: a file deleted only from the worktree was reported as empty\n' >&2; exit 1; fi
+
+# 42. core.symlinks=false の checkout（symlink が通常ファイルになる）でも通過する
+git clone -q -c core.symlinks=false "$tmp/proj-ok" "$tmp/nosymlinks"
+[ -f "$tmp/nosymlinks/demo/.pi" ] && [ ! -L "$tmp/nosymlinks/demo/.pi" ] || { printf 'FAIL: core.symlinks=false did not take effect\n' >&2; exit 1; }
+bash "$checker" --root "$tmp/nosymlinks" | grep -qF 'PASS: check-layout'
+
 printf 'PASS: check-layout script behaves as specified\n'
```

- [ ] **Step 2: テストが失敗することを確かめる**

Run: `bash tests/scripts/test-check-layout.bash`
Expected: 終了コード 1。`FAIL: resoloop output was not relayed`（ケース 23。旧スクリプトは resoloop の出力を捨てる）

- [ ] **Step 3: check-layout を書き換える**

`scripts/check-layout.sh` を次の内容に置き換える。変更点は、冒頭の注記、`empty_blob` と `index_entry` の追加、検査 4 の `.claude/skills` 自体が symlink の場合の扱い・行き先の読み取り（`git cat-file blob`）・足りないリンクの名前順・定義のコメント、検査 5 の空ファイル判定（空 blob の oid との比較）、検査 6 の必須ファイル（完全一致と mode）・CLAUDE.md の比較（末尾の改行まで）・AGENTS.md と `.resoloop/.gitignore` の読み取り（index から変数へ）・symlink の行き先、検査 7 の `./` 付きの引数と出力の中継。

```bash
#!/bin/bash
# リポジトリのレイアウト検査。仕様: docs/superpowers/specs/2026-09-26-create-reso-world-redesign-design.md 9.1 節
# 使い方: scripts/check-layout.sh [--root DIR]
# 追跡の有無と mode、symlink の行き先、ファイルの中身はすべて git の index から読む。作業ツリーの未ステージの変更は
# 結果を変えず、core.symlinks=false の checkout（symlink が通常ファイルになる）でも同じ結果になる。
# 例外として、追跡中の symlink が解決できるか（検査 2）だけは作業ツリーで確かめる。
set -euo pipefail

usage() {
  printf 'usage: %s [--root DIR]\n' "${BASH_SOURCE[0]}" >&2
  exit 64
}

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
root=""
root_given=0
while [ $# -gt 0 ]; do
  case "$1" in
    --root)
      [ $# -ge 2 ] || usage
      root="$(git -C "$2" rev-parse --show-toplevel)" || usage
      root_given=1
      shift 2
      ;;
    *) usage ;;
  esac
done
# --root が無い場合だけ、スクリプト自身の位置からデフォルトのルートを求める。
# 引数解析より前に求めると、リポジトリの外にコピーしたスクリプトが --root 付きでも動かない。
if [ "$root_given" -eq 0 ]; then
  root="$(git -C "$script_dir" rev-parse --show-toplevel)"
fi
cd "$root"

failures=0
fail() { failures=$((failures + 1)); printf 'FAIL: %s\n' "$1" >&2; }
ok() { printf 'ok: %s\n' "$1"; }

# git ls-files の出力を NUL 区切りで受け渡す一時ファイル。各 check 関数が使い捨てる
tmp_list="$(mktemp)"
trap 'rm -f "$tmp_list"' EXIT
empty_blob="$(git hash-object -t blob --stdin </dev/null)"

# index（ステージ 0）にあるパスと完全に一致するエントリを "mode oid" で出力する。無ければ 1。
# パスはワイルドカードとして解釈しない。git ls-files はディレクトリの前方一致でも列挙するので、パスの一致を確かめる
index_entry() {
  local want="$1" record meta fields
  while IFS= read -r -d '' record; do
    [ "${record#*$'\t'}" = "$want" ] || continue
    meta="${record%%$'\t'*}"
    fields="${meta#* }"
    printf '%s %s\n' "${meta%% *}" "${fields%% *}"
    return 0
  done < <(git ls-files -s -z -- ":(literal)$want")
  return 1
}

# 1. 追跡してはいけないファイル（仕様 9.1）
check_forbidden_tracked() {
  local pattern='(^|/)(ATS|BTD|TNX)\.txt$|(^|/)\.claude/settings\.local\.json$|\.blend1$|\.blend2$|\.orig$|\.rej$|(^|/)__pycache__/|(^|/)\.venv/'
  if ! git ls-files -z > "$tmp_list"; then
    fail "git ls-files failed"
    return
  fi
  local hits=() path
  while IFS= read -r -d '' path; do
    [[ "$path" =~ $pattern ]] && hits+=("$path")
  done < "$tmp_list"
  if [ ${#hits[@]} -gt 0 ]; then
    fail "forbidden tracked files: ${hits[*]}"
  else
    ok "no forbidden tracked files"
  fi
}

# 2. 追跡中の symlink がすべて解決できる（作業ツリーで確かめる）
check_symlinks_resolve() {
  if ! git ls-files -s -z > "$tmp_list"; then
    fail "git ls-files -s failed"
    return
  fi
  local broken=() record meta path mode
  while IFS= read -r -d '' record; do
    meta="${record%%$'\t'*}"
    path="${record#*$'\t'}"
    mode="${meta%% *}"
    [ "$mode" = 120000 ] || continue
    [ -e "$path" ] || broken+=("$path")
  done < "$tmp_list"
  if [ ${#broken[@]} -gt 0 ]; then
    fail "dangling tracked symlinks: ${broken[*]}"
  else
    ok "tracked symlinks resolve"
  fi
}

# 3. 追跡中かつ ignore 対象は既知の例外だけ
check_tracked_ignored() {
  local allow='MyResoniteProject/.resoloop/tokyo-nova/pipeline.json'
  if ! git -c core.excludesFile=/dev/null ls-files -z -i -c --exclude-standard > "$tmp_list"; then
    fail "git ls-files -i failed"
    return
  fi
  local hits=() path
  while IFS= read -r -d '' path; do
    [ "$path" = "$allow" ] && continue
    hits+=("$path")
  done < "$tmp_list"
  if [ ${#hits[@]} -gt 0 ]; then
    fail "tracked but ignored: ${hits[*]}"
  else
    ok "no unexpected tracked-but-ignored files"
  fi
}

# 4. <prefix>.claude/skills の各エントリが <prefix>.agents/skills の同名ディレクトリへの symlink で、1:1 に対応する（仕様 4.2・8.1・9.1）
# 引数: 接頭辞。ルートは ""、プロジェクトは "slum02/" のように末尾に / を付ける
# リンクが要るのは、追跡ファイルを 1 つ以上持つ .agents/skills 直下のディレクトリ。SKILL.md の有無は問わない
# （ルートの references/ のように、SKILL.md を持たない共有ディレクトリにもリンクが要る）。
# scripts/new-world.sh も、ファイルを 1 つ以上持つディレクトリという同じ定義でリンクを張る。
check_skill_links() {
  local prefix="$1"
  local agents="${prefix}.agents/skills/" claude="${prefix}.claude/skills/"
  local -A dirs=() links=()
  local problems=() names=() path record meta fields mode oid rest name target
  if ! git ls-files -z -- "${prefix}.agents/skills" > "$tmp_list"; then
    fail "git ls-files failed for ${agents}"
    return
  fi
  while IFS= read -r -d '' path; do
    rest="${path#"$agents"}"
    [ "$rest" != "${rest#*/}" ] || continue   # 直下のファイル（.resoloop-bundled.json など）は対象外
    dirs["${rest%%/*}"]=1
  done < "$tmp_list"
  if ! git ls-files -s -z -- "${prefix}.claude/skills" > "$tmp_list"; then
    fail "git ls-files -s failed for ${claude}"
    return
  fi
  while IFS= read -r -d '' record; do
    meta="${record%%$'\t'*}"
    path="${record#*$'\t'}"
    mode="${meta%% *}"
    fields="${meta#* }"
    oid="${fields%% *}"
    if [ "$path" = "${claude%/}" ]; then
      problems+=("${claude%/} must be a directory, not a symlink")
      continue
    fi
    rest="${path#"$claude"}"
    name="${rest%%/*}"
    [ -z "${links[$name]+x}" ] || continue
    links["$name"]=1
    if [ "$mode" != 120000 ] || [ "$rest" != "$name" ]; then
      problems+=("${claude}${name} is not a symlink")
      continue
    fi
    target="$(git cat-file blob "$oid")"
    [ "$target" = "../../.agents/skills/$name" ] || problems+=("${claude}${name} has unexpected target ${target:-<none>}")
    [ -n "${dirs[$name]+x}" ] || problems+=("${claude}${name} has no matching ${agents}${name}")
  done < "$tmp_list"
  if [ ${#dirs[@]} -gt 0 ]; then
    mapfile -t names < <(printf '%s\n' "${!dirs[@]}" | LC_ALL=C sort)
  fi
  for name in ${names[@]+"${names[@]}"}; do
    [ -n "${links[$name]+x}" ] || problems+=("${claude%/}: missing link ${name}")
  done
  if [ ${#problems[@]} -gt 0 ]; then
    local p
    for p in "${problems[@]}"; do fail "$p"; done
  else
    ok "${claude%/} links are 1:1 with ${agents%/}"
  fi
}

# 5. 旧 .devin/skills を追跡していない。スキル配下に 0 バイトの追跡ファイルが無い（仕様 5.5・8.1・11 章）
check_skill_hygiene() {
  local hits=() record meta fields path mode re='(^|/)\.(agents|claude)/skills/'
  if ! git ls-files -z -- .devin/skills > "$tmp_list"; then
    fail "git ls-files failed for .devin/skills"
    return
  fi
  [ ! -s "$tmp_list" ] || hits+=(".devin/skills is still tracked")
  if ! git ls-files -s -z > "$tmp_list"; then
    fail "git ls-files -s failed"
    return
  fi
  while IFS= read -r -d '' record; do
    meta="${record%%$'\t'*}"
    path="${record#*$'\t'}"
    mode="${meta%% *}"
    fields="${meta#* }"
    [ "$mode" != 120000 ] || continue
    [[ "$path" =~ $re ]] || continue
    [ "${fields%% *}" != "$empty_blob" ] || hits+=("empty tracked file: $path")
  done < "$tmp_list"
  if [ ${#hits[@]} -gt 0 ]; then
    local h
    for h in "${hits[@]}"; do fail "$h"; done
  else
    ok "skill trees hold no retired or empty tracked files"
  fi
}

# 6. 各プロジェクト（.resoloop.json を追跡している直下のディレクトリ）が仕様 4.2 の標準レイアウトを満たす
projects=()
collect_projects() {
  local path
  if ! git ls-files -z -- '*/.resoloop.json' > "$tmp_list"; then
    fail "git ls-files failed for */.resoloop.json"
    return
  fi
  while IFS= read -r -d '' path; do
    [[ "$path" =~ ^[^/]+/\.resoloop\.json$ ]] || continue
    projects+=("${path%%/*}")
  done < "$tmp_list"
}

check_project() {
  local p="$1" problems=() f link target sp entry content
  for f in AGENTS.md CLAUDE.md .resoloop.json .resoloop/.gitignore pyproject.toml uv.lock \
           .agents/skills/.resoloop-bundled.json flux/resoloop.flux.json; do
    if ! entry="$(index_entry "$p/$f")"; then
      problems+=("missing tracked file $f")
    elif [ "${entry%% *}" != 100644 ] && [ "${entry%% *}" != 100755 ]; then
      problems+=("$f must be a regular file (index mode ${entry%% *})")
    fi
  done
  # 比較と検索は変数に取り込んでから行う（pipefail の下で grep -q が上流を SIGPIPE で落とすのを避ける）
  content="$(git cat-file blob ":$p/CLAUDE.md" 2>/dev/null; printf x)"
  [ "$content" = $'@AGENTS.md\nx' ] || problems+=("CLAUDE.md must be exactly @AGENTS.md")
  content="$(git cat-file blob ":$p/AGENTS.md" 2>/dev/null || true)"
  grep -qxF '## このプロジェクト固有' <<<"$content" || problems+=("AGENTS.md lacks ## このプロジェクト固有")
  content="$(git cat-file blob ":$p/.resoloop/.gitignore" 2>/dev/null || true)"
  grep -qxF 'cache/' <<<"$content" || problems+=(".resoloop/.gitignore lacks cache/")
  local links=(".claude/settings.json|../../.claude/settings.json" ".pi|../.pi")
  if ! git ls-files -z -- '.agents/sp-*.md' > "$tmp_list"; then
    fail "git ls-files failed for .agents/sp-*.md"
    return
  fi
  while IFS= read -r -d '' sp; do
    links+=(".agents/${sp##*/}|../../.agents/${sp##*/}")
  done < "$tmp_list"
  for link in "${links[@]}"; do
    f="${link%%|*}" target="${link#*|}"
    entry="$(index_entry "$p/$f" || true)"
    if [ "${entry%% *}" != 120000 ] || [ "$(git cat-file blob "${entry#* }")" != "$target" ]; then
      problems+=("$f must be a symlink to $target")
    fi
  done
  if [ ${#problems[@]} -gt 0 ]; then
    local q
    for q in "${problems[@]}"; do fail "$p: $q"; done
  else
    ok "project $p layout"
  fi
  check_skill_links "$p/"
}

# 7. resoloop が使える環境では resoloop skills sync --check が各プロジェクトで成功する。失敗したら resoloop の出力を字下げして示す
check_resoloop_skills() {
  local p out
  if ! command -v resoloop >/dev/null 2>&1; then
    printf 'skip: resoloop not found (skills sync check)\n'
    return
  fi
  for p in ${projects[@]+"${projects[@]}"}; do
    # ./ を付けて、- で始まるプロジェクト名をオプションとして読ませない
    if out="$(resoloop skills sync "./$p" --check 2>&1)"; then
      ok "resoloop skills sync --check ($p)"
    else
      fail "resoloop skills sync --check failed for $p"
      [ -z "$out" ] || printf '%s\n' "$out" | sed 's/^/    /' >&2
    fi
  done
}

check_forbidden_tracked
check_symlinks_resolve
check_tracked_ignored
check_skill_links ""
check_skill_hygiene
collect_projects
for p in ${projects[@]+"${projects[@]}"}; do check_project "$p"; done
check_resoloop_skills

if [ "$failures" -gt 0 ]; then
  printf 'FAIL: check-layout (%d failure(s))\n' "$failures" >&2
  exit 1
fi
printf 'PASS: check-layout\n'
```

- [ ] **Step 4: テストが通ることを確かめる**

Run: `bash tests/scripts/test-check-layout.bash && bash scripts/check-layout.sh | tail -n 1`
Expected: `PASS: check-layout script behaves as specified` と `PASS: check-layout`

Global Constraints の回帰確認も実行する。

- [ ] **Step 5: コミット**

```bash
git add scripts/check-layout.sh tests/scripts/test-check-layout.bash
git commit -m "fix(layout): read check-layout contents from the index and relay resoloop output"
```

---

### Task 5: check-layout にロックの検査を足す（仕様 9.1、持ち越し N-7）

`.devcontainer/devcontainer.json` を追跡しているリポジトリでは、ロックの必須キーと、`RESOLOOP_FORK_SDK` が `additionalVersions` に含まれることを検査する。ロック・読み込み関数・devcontainer.json は index から取り出し、Task 1 の読み込み関数をサブシェルで使う。

**Files:**
- Modify: `scripts/check-layout.sh`（一時ファイルを一時ディレクトリに変更、検査 8 の追加、呼び出しの追加）
- Modify: `tests/scripts/test-check-layout.bash`（`lock_repo` とケース 43〜48 の追加）

**Interfaces:**
- Consumes: Task 1 の `resoloop_lock_load` と `resoloop_lock_sdk_declared`（検査対象のリポジトリの index にある `.devcontainer/resoloop-lock.bash`）、Task 4 の `index_entry`
- Produces: 出力 `ok: resoloop lock (mode <mode>, expects <期待版>)`、`skip: .devcontainer/devcontainer.json is not tracked (resoloop lock check)`、失敗時は `missing tracked file .devcontainer/<file>` またはロックの読み込み関数の理由（`resoloop.lock: ...`）

- [ ] **Step 1: 失敗するテストを書く**

`tests/scripts/test-check-layout.bash` の末尾（最後の `printf 'PASS: ...'` の前）に、次の差分のとおりケースを足す。

```diff
--- a/tests/scripts/test-check-layout.bash
+++ b/tests/scripts/test-check-layout.bash
@@ -337,4 +337,59 @@
 [ -f "$tmp/nosymlinks/demo/.pi" ] && [ ! -L "$tmp/nosymlinks/demo/.pi" ] || { printf 'FAIL: core.symlinks=false did not take effect\n' >&2; exit 1; }
 bash "$checker" --root "$tmp/nosymlinks" | grep -qF 'PASS: check-layout'
 
+# .devcontainer に devcontainer.json・ロック・読み込み関数を持つ一時リポジトリを作る。ロックの SDK は 10.0.201
+lock_repo() {
+  local r="$1"
+  new_repo "$r"
+  mkdir -p "$r/.devcontainer"
+  cp "$root/.devcontainer/resoloop-lock.bash" "$r/.devcontainer/resoloop-lock.bash"
+  printf '{\n\t"features": {\n\t\t"ghcr.io/devcontainers/features/dotnet:2": {\n\t\t\t"version": "10.0",\n\t\t\t"additionalVersions": "10.0.201"\n\t\t}\n\t}\n}\n' \
+    > "$r/.devcontainer/devcontainer.json"
+  cat > "$r/.devcontainer/resoloop.lock" <<'EOF'
+RESOLOOP_MODE=fork
+RESOLOOP_NUGET_VERSION=1.2.3-preview.4
+RESOLOOP_FORK_ORIGIN=https://example.com/fork/resoloop.git
+RESOLOOP_FORK_UPSTREAM=https://example.com/upstream/resoloop.git
+RESOLOOP_FORK_REF=fix/x
+RESOLOOP_FORK_COMMIT=0123456789abcdef0123456789abcdef01234567
+RESOLOOP_FORK_PACKAGE_VERSION=1.2.3-preview.4.pr1.test
+RESOLOOP_FORK_PR=https://example.com/upstream/resoloop/pull/1
+RESOLOOP_FORK_SDK=10.0.201
+EOF
+  commit_paths "$r" .devcontainer
+}
+
+# 43. 正しいロックは ok を表示して通過する。devcontainer.json を追跡していないリポジトリでは skip を表示する
+lock_repo "$tmp/lock-ok"
+bash "$checker" --root "$tmp/lock-ok" > "$tmp/lock-ok.out"
+grep -qF 'ok: resoloop lock (mode fork, expects 1.2.3-preview.4.pr1.test)' "$tmp/lock-ok.out"
+grep -qF 'PASS: check-layout' "$tmp/lock-ok.out"
+bash "$checker" --root "$tmp/clean" > "$tmp/lock-skip.out"
+grep -qF 'skip: .devcontainer/devcontainer.json is not tracked (resoloop lock check)' "$tmp/lock-skip.out"
+
+# 44. devcontainer.json があるのにロックか読み込み関数が無ければ失敗する
+lock_repo "$tmp/lock-missing" && git -C "$tmp/lock-missing" rm -q .devcontainer/resoloop.lock && git -C "$tmp/lock-missing" commit -q -m rm
+expect_fail_with "$tmp/lock-missing" 'missing tracked file .devcontainer/resoloop.lock'
+lock_repo "$tmp/lock-nolib" && git -C "$tmp/lock-nolib" rm -q .devcontainer/resoloop-lock.bash && git -C "$tmp/lock-nolib" commit -q -m rm
+expect_fail_with "$tmp/lock-nolib" 'missing tracked file .devcontainer/resoloop-lock.bash'
+
+# 45. 必須キーの欠落は失敗する
+lock_repo "$tmp/lock-key" && sed -i '/^RESOLOOP_FORK_SDK=/d' "$tmp/lock-key/.devcontainer/resoloop.lock" && commit_paths "$tmp/lock-key" .devcontainer
+expect_fail_with "$tmp/lock-key" 'resoloop.lock: missing key RESOLOOP_FORK_SDK'
+
+# 46. RESOLOOP_FORK_SDK が additionalVersions に無ければ失敗する
+lock_repo "$tmp/lock-sdk" && sed -i 's/"additionalVersions": "10.0.201"/"additionalVersions": "10.0.100"/' "$tmp/lock-sdk/.devcontainer/devcontainer.json" \
+  && commit_paths "$tmp/lock-sdk" .devcontainer
+expect_fail_with "$tmp/lock-sdk" 'RESOLOOP_FORK_SDK 10.0.201 is not in additionalVersions of .devcontainer/devcontainer.json'
+
+# 47. ロックも index の内容で判定する（作業ツリーだけ壊れていても通過する）
+lock_repo "$tmp/lock-worktree"
+printf 'broken\n' > "$tmp/lock-worktree/.devcontainer/resoloop.lock"
+bash "$checker" --root "$tmp/lock-worktree" > "$tmp/lock-worktree.out"
+grep -qF 'ok: resoloop lock (' "$tmp/lock-worktree.out"
+
+# 48. このリポジトリのロックも検査される
+bash "$checker" > "$tmp/self.out"
+grep -qF 'ok: resoloop lock (' "$tmp/self.out"
+
 printf 'PASS: check-layout script behaves as specified\n'
```

- [ ] **Step 2: テストが失敗することを確かめる**

Run: `bash tests/scripts/test-check-layout.bash; echo "exit=$?"`
Expected: `exit=1`（ケース 43 の `grep -qF 'ok: resoloop lock ...'` で止まる。メッセージは出ない）

- [ ] **Step 3: 検査を足す**

`scripts/check-layout.sh` を次の差分のとおりに変える。

```diff
--- a/scripts/check-layout.sh
+++ b/scripts/check-layout.sh
@@ -36,9 +36,10 @@
 fail() { failures=$((failures + 1)); printf 'FAIL: %s\n' "$1" >&2; }
 ok() { printf 'ok: %s\n' "$1"; }
 
-# git ls-files の出力を NUL 区切りで受け渡す一時ファイル。各 check 関数が使い捨てる
-tmp_list="$(mktemp)"
-trap 'rm -f "$tmp_list"' EXIT
+# 一時ディレクトリ。list は git ls-files の出力を NUL 区切りで受け渡すファイルで、各 check 関数が使い捨てる
+tmp_dir="$(mktemp -d)"
+trap 'rm -rf "$tmp_dir"' EXIT
+tmp_list="$tmp_dir/list"
 empty_blob="$(git hash-object -t blob --stdin </dev/null)"
 
 # index（ステージ 0）にあるパスと完全に一致するエントリを "mode oid" で出力する。無ければ 1。
@@ -274,6 +275,43 @@
   done
 }
 
+# 8. ResoLoop のロック（仕様 6.1・9.1）。.devcontainer/devcontainer.json を追跡しているリポジトリだけが対象。
+# ロック・読み込み関数・devcontainer.json を index から取り出し、読み込み関数（.devcontainer/resoloop-lock.bash）で検証する
+check_resoloop_lock() {
+  local f out d="$tmp_dir/lock"
+  if ! index_entry .devcontainer/devcontainer.json >/dev/null; then
+    printf 'skip: .devcontainer/devcontainer.json is not tracked (resoloop lock check)\n'
+    return
+  fi
+  for f in resoloop.lock resoloop-lock.bash; do
+    if ! index_entry ".devcontainer/$f" >/dev/null; then
+      fail "missing tracked file .devcontainer/$f"
+      return
+    fi
+  done
+  mkdir -p "$d"
+  for f in resoloop.lock resoloop-lock.bash devcontainer.json; do
+    git cat-file blob ":.devcontainer/$f" > "$d/$f"
+  done
+  if out="$(validate_lock "$d" 2>&1)"; then
+    ok "resoloop lock ($out)"
+  else
+    while IFS= read -r f; do fail "$f"; done <<<"$out"
+  fi
+}
+
+# 検証はサブシェルで行い、読み込み関数が設定する変数を check-layout に持ち込まない
+validate_lock() (
+  # shellcheck source=/dev/null
+  source "$1/resoloop-lock.bash"
+  resoloop_lock_load "$1/resoloop.lock" || exit 1
+  if ! resoloop_lock_sdk_declared "$1/devcontainer.json" "$RESOLOOP_FORK_SDK"; then
+    printf 'resoloop.lock: RESOLOOP_FORK_SDK %s is not in additionalVersions of .devcontainer/devcontainer.json\n' "$RESOLOOP_FORK_SDK"
+    exit 1
+  fi
+  printf 'mode %s, expects %s' "$RESOLOOP_MODE" "$RESOLOOP_EXPECTED_VERSION"
+)
+
 check_forbidden_tracked
 check_symlinks_resolve
 check_tracked_ignored
@@ -282,6 +320,7 @@
 collect_projects
 for p in ${projects[@]+"${projects[@]}"}; do check_project "$p"; done
 check_resoloop_skills
+check_resoloop_lock
 
 if [ "$failures" -gt 0 ]; then
   printf 'FAIL: check-layout (%d failure(s))\n' "$failures" >&2
```

- [ ] **Step 4: テストが通ることを確かめる**

Run: `bash tests/scripts/test-check-layout.bash && bash scripts/check-layout.sh | tail -n 2`
Expected: `PASS: check-layout script behaves as specified`、`ok: resoloop lock (mode fork, expects 0.1.0-preview.14.pr1.20260925)`、`PASS: check-layout`

Global Constraints の回帰確認も実行する。

- [ ] **Step 5: コミット**

```bash
git add scripts/check-layout.sh tests/scripts/test-check-layout.bash
git commit -m "feat(layout): check the ResoLoop lock and the SDK in devcontainer.json"
```

---

### Task 6: new-world.sh の小修正（持ち越し N-9 の 1・2 点目、N-10、N-16）

git に無視される名前を拒み、改行で終わらない `AGENTS.md` への追記を直す。リンクが要るディレクトリの定義を check-layout に合わせる（判断事項 D-7）。途中のディレクトリが通常ファイルや symlink の場合、`.claude/skills` の隠しエントリ、symlink の `AGENTS.md`、`|` を含む名前を扱う。

**Files:**
- Modify（全体を置き換え）: `scripts/new-world.sh`
- Modify: `tests/scripts/test-new-world.bash`（ケース 7・8 の無変更確認、ケース 19〜29 の追加）

**Interfaces:**
- Produces: 終了コードの意味は変えない（2 に「git に無視される名前」が加わる）。新しいメッセージ: `'<name>' is ignored by git in <root> (...)`、`CONFLICT: <path> is not a directory`、`CONFLICT: AGENTS.md is a symlink; refusing to append to its target`

- [ ] **Step 1: 失敗するテストを書く**

`tests/scripts/test-new-world.bash` を次の差分のとおりに変える。

```diff
--- a/tests/scripts/test-new-world.bash
+++ b/tests/scripts/test-new-world.bash
@@ -104,17 +104,21 @@ before="$(snapshot "$tmp/r6/demo")"
 expect_exit 1 'CONFLICT: .pi exists and is not a symlink' "$tmp/r6" --apply --no-sync demo
 [ "$before" = "$(snapshot "$tmp/r6/demo")" ] || fail 'conflicting --apply changed files'
 
-# 7. CLAUDE.md が雛形と違えば 1
+# 7. CLAUDE.md が雛形と違えば 1 を返し、何も変更しない
 new_root "$tmp/r7"
 run "$tmp/r7" --no-sync demo >/dev/null
 printf 'other\n' > "$tmp/r7/demo/CLAUDE.md"
+before="$(snapshot "$tmp/r7/demo")"
 expect_exit 1 'CONFLICT: CLAUDE.md differs from templates/world-project/CLAUDE.md' "$tmp/r7" --apply --no-sync demo
+[ "$before" = "$(snapshot "$tmp/r7/demo")" ] || fail 'case 7 changed files'
 
-# 8. 対応する .agents/skills の無い .claude/skills のリンクは 1
+# 8. 対応する .agents/skills の無い .claude/skills のリンクは 1 を返し、何も変更しない
 new_root "$tmp/r8"
 run "$tmp/r8" --no-sync demo >/dev/null
 ln -s ../../.agents/skills/stale "$tmp/r8/demo/.claude/skills/stale"
+before="$(snapshot "$tmp/r8/demo")"
 expect_exit 1 'CONFLICT: .claude/skills/stale has no matching .agents/skills/stale' "$tmp/r8" --apply --no-sync demo
+[ "$before" = "$(snapshot "$tmp/r8/demo")" ] || fail 'case 8 changed files'
 
 # 9. resoloop プロジェクトでないディレクトリへの --apply は 3
 new_root "$tmp/r9"
@@ -197,4 +201,91 @@ if grep -qF 'no changes were made' "$tmp/out.txt"; then fail 'claimed no changes
 [ "$(cat "$tmp/r18/demo/CLAUDE.md")" = 'other' ] || fail 'changed CLAUDE.md after the conflict'
 if [ -e "$tmp/r18/demo/.pi" ] || [ -L "$tmp/r18/demo/.pi" ]; then fail 'applied links after the conflict'; fi
 
+# 19. ルートの .gitignore で無視される名前は、resoloop を呼ばず何も作らずに 2（N-9）
+new_root "$tmp/r19"
+printf 'tmp/\n/private/\n' > "$tmp/r19/.gitignore"
+: > "$MOCK_LOG"
+expect_exit 2 "'tmp' is ignored by git" "$tmp/r19" --no-sync tmp
+expect_exit 2 "'private' is ignored by git" "$tmp/r19" --no-sync private
+[ ! -e "$tmp/r19/tmp" ] && [ ! -e "$tmp/r19/private" ] || fail 'created an ignored project'
+[ ! -s "$MOCK_LOG" ] || fail 'ran resoloop for an ignored name'
+
+# 20. 改行で終わらない AGENTS.md には、改行と空行を挟んでから固有節を追記する（N-9）
+new_root "$tmp/r20"
+run "$tmp/r20" --no-sync demo >/dev/null
+printf '# guide' > "$tmp/r20/demo/AGENTS.md"
+expect_exit 0 'appended: AGENTS.md' "$tmp/r20" --apply --no-sync demo
+[ "$(sed -n '1p' "$tmp/r20/demo/AGENTS.md")" = '# guide' ] || fail 'the last line of AGENTS.md was changed'
+[ -z "$(sed -n '2p' "$tmp/r20/demo/AGENTS.md")" ] || fail 'no blank line before the section'
+[ "$(sed -n '3p' "$tmp/r20/demo/AGENTS.md")" = '## このプロジェクト固有' ] || fail 'the section does not start on its own line'
+
+# 21. SKILL.md の無いディレクトリ（隠しディレクトリを含む）でも、ファイルがあればリンクを張る（check-layout と同じ定義、N-10）
+new_root "$tmp/r21"
+run "$tmp/r21" --no-sync demo >/dev/null
+mkdir -p "$tmp/r21/demo/.agents/skills/shared-refs" && printf 'notes\n' > "$tmp/r21/demo/.agents/skills/shared-refs/notes.md"
+mkdir -p "$tmp/r21/demo/.agents/skills/.hidden-refs" && printf 'notes\n' > "$tmp/r21/demo/.agents/skills/.hidden-refs/notes.md"
+expect_exit 0 'linked: .claude/skills/shared-refs -> ../../.agents/skills/shared-refs' "$tmp/r21" --apply --no-sync demo
+grep -qF 'linked: .claude/skills/.hidden-refs -> ../../.agents/skills/.hidden-refs' "$tmp/out.txt" || fail 'hidden directory was not linked'
+expect_exit 0 'DONE: demo' "$tmp/r21" --apply --no-sync demo
+
+# 22. 途中のディレクトリが通常ファイルなら 1 を返し、何も変更しない（N-16）
+new_root "$tmp/r22"
+run "$tmp/r22" --no-sync demo >/dev/null
+rm -rf "$tmp/r22/demo/.claude" && printf 'x\n' > "$tmp/r22/demo/.claude"
+before="$(snapshot "$tmp/r22/demo")"
+expect_exit 1 'CONFLICT: .claude is not a directory' "$tmp/r22" --apply --no-sync demo
+[ "$(grep -c 'is not a directory' "$tmp/out.txt")" -eq 1 ] || fail 'reported the same parent more than once'
+[ "$before" = "$(snapshot "$tmp/r22/demo")" ] || fail 'case 22 changed files'
+
+# 23. .claude/skills の隠しエントリも、対応するディレクトリが無ければ 1（N-16）
+new_root "$tmp/r23"
+run "$tmp/r23" --no-sync demo >/dev/null
+ln -s ../../.agents/skills/.old "$tmp/r23/demo/.claude/skills/.old"
+expect_exit 1 'CONFLICT: .claude/skills/.old has no matching .agents/skills/.old' "$tmp/r23" --apply --no-sync demo
+
+# 24. AGENTS.md が symlink なら追記せずに 1（リンク先を書き換えない、N-16）
+new_root "$tmp/r24"
+run "$tmp/r24" --no-sync demo >/dev/null
+printf '# shared guide\n' > "$tmp/r24/shared-agents.md"
+rm "$tmp/r24/demo/AGENTS.md" && ln -s ../shared-agents.md "$tmp/r24/demo/AGENTS.md"
+expect_exit 1 'CONFLICT: AGENTS.md is a symlink' "$tmp/r24" --apply --no-sync demo
+[ "$(cat "$tmp/r24/shared-agents.md")" = '# shared guide' ] || fail 'wrote through the AGENTS.md symlink'
+
+# 25. 食い違いが複数あればすべて報告し、何も変更しない（N-16）
+new_root "$tmp/r25"
+run "$tmp/r25" --no-sync demo >/dev/null
+rm "$tmp/r25/demo/.pi" && mkdir "$tmp/r25/demo/.pi"
+printf 'other\n' > "$tmp/r25/demo/CLAUDE.md"
+before="$(snapshot "$tmp/r25/demo")"
+expect_exit 1 'CONFLICT: .pi exists and is not a symlink' "$tmp/r25" --apply --no-sync demo
+grep -qF 'CONFLICT: CLAUDE.md differs from templates/world-project/CLAUDE.md' "$tmp/out.txt" || fail 'did not report every conflict'
+[ "$before" = "$(snapshot "$tmp/r25/demo")" ] || fail 'case 25 changed files'
+
+# 26. 行き先の違う symlink は 1（N-16）
+new_root "$tmp/r26"
+run "$tmp/r26" --no-sync demo >/dev/null
+rm "$tmp/r26/demo/.pi" && ln -s ../other "$tmp/r26/demo/.pi"
+expect_exit 1 'CONFLICT: .pi points to ../other, expected ../.pi' "$tmp/r26" --apply --no-sync demo
+
+# 27. 行き先が存在しないことになる symlink は 1（N-16）
+new_root "$tmp/r27"
+run "$tmp/r27" --no-sync demo >/dev/null
+rm "$tmp/r27/demo/.claude/settings.json" "$tmp/r27/.claude/settings.json"
+expect_exit 1 'CONFLICT: .claude/settings.json would point to missing ../../.claude/settings.json' "$tmp/r27" --apply --no-sync demo
+
+# 28. ルートの .claude/settings.json が無ければ、新規作成は resoloop init を呼ばず何も作らずに 3（N-16）
+new_root "$tmp/r28"
+rm "$tmp/r28/.claude/settings.json"
+: > "$MOCK_LOG"
+expect_exit 3 '.claude/settings.json is missing at the repository root' "$tmp/r28" --no-sync demo
+[ ! -e "$tmp/r28/demo" ] || fail 'created the project although the root .claude/settings.json is missing'
+[ ! -s "$MOCK_LOG" ] || fail 'ran resoloop init although the root .claude/settings.json is missing'
+
+# 29. 名前に | を含むスキルディレクトリにも正しくリンクを張る（N-16）
+new_root "$tmp/r29"
+run "$tmp/r29" --no-sync demo >/dev/null
+mkdir -p "$tmp/r29/demo/.agents/skills/a|b" && printf -- '---\nname: ab\n---\n' > "$tmp/r29/demo/.agents/skills/a|b/SKILL.md"
+expect_exit 0 'DONE: demo' "$tmp/r29" --apply --no-sync demo
+[ "$(readlink "$tmp/r29/demo/.claude/skills/a|b")" = '../../.agents/skills/a|b' ] || fail 'link for a name containing |'
+
 printf 'PASS: new-world script behaves as specified\n'
```

- [ ] **Step 2: テストが失敗することを確かめる**

Run: `bash tests/scripts/test-new-world.bash`
Expected: 終了コード 1。`FAIL: expected exit 2, got 0: .../r19 --no-sync tmp`（ケース 19。旧スクリプトは無視される名前でも作ってしまう）

- [ ] **Step 3: new-world.sh を書き換える**

`scripts/new-world.sh` を次の内容に置き換える。変更点は、終了コード 2 の注記、`check-ignore` による名前の検査、`has_files`（リンクの要否）、`parent_ok`（途中のディレクトリの検査）、計画を平行配列（`plan_file_rel` / `plan_file_src`、`plan_link_rel` / `plan_link_target`）で持つこと、`AGENTS.md` の symlink の検査、リンクの 2 つのループの `dotglob`、改行で終わらない `AGENTS.md` への追記。

```bash
#!/bin/bash
# ワールドのプロジェクトを作る、または既存プロジェクトに雛形の不足分を適用する。
# 仕様: docs/superpowers/specs/2026-09-26-create-reso-world-redesign-design.md 4.2・4.3 節
# 使い方: scripts/new-world.sh [--apply] [--no-sync] [--root DIR] <name>
# 終了コード:
#   0 成功
#   1 既存ファイルとの食い違いあり。雛形の変更は何もしない（新規作成では resoloop init が作ったディレクトリだけが残り、その旨を表示する）
#   2 使い方の誤り（git に無視される名前を含む）。何も変更しない
#   3 前提不足。uv（同期ありのとき）・resoloop・ルートの共有物（.claude/settings.json、.pi）の欠落は何かを作る前に検出する。
#     resoloop init の失敗や init 後の生成物の不足では init が作ったものが残る。uv sync の失敗では雛形の適用は済んでおり、その旨を表示する
set -euo pipefail

usage() {
  printf 'usage: %s [--apply] [--no-sync] [--root DIR] <name>\n' "${BASH_SOURCE[0]}" >&2
  exit 2
}
die() { printf 'ERROR: %s\n' "$2" >&2; exit "$1"; }

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
apply=0 sync=1 root="" name="" name_given=0
while [ $# -gt 0 ]; do
  case "$1" in
    --apply) apply=1; shift ;;
    --no-sync) sync=0; shift ;;
    --root)
      [ $# -ge 2 ] || usage
      root="$(git -C "$2" rev-parse --show-toplevel 2>/dev/null)" || usage
      shift 2
      ;;
    -*) usage ;;
    *) [ "$name_given" -eq 0 ] || usage; name="$1"; name_given=1; shift ;;
  esac
done
[ "$name_given" -eq 1 ] || usage
name_re='^[A-Za-z0-9]([A-Za-z0-9_-]*[A-Za-z0-9])?$'
[[ "$name" =~ $name_re ]] || die 2 "invalid project name '$name' (use letters, digits, '-' and '_'; start and end with a letter or digit)"
[ -n "$root" ] || root="$(git -C "$script_dir" rev-parse --show-toplevel)"
# ルートの .gitignore（や利用者の除外設定）で無視される名前のプロジェクトは、git からも check-layout からも見えない
if git -C "$root" check-ignore -q -- "$name/.resoloop.json" 2>/dev/null; then
  die 2 "'$name' is ignored by git in $root (root .gitignore or your excludes); choose another name"
fi
tmpl="$root/templates/world-project"
[ -d "$tmpl" ] || die 3 "template directory not found: $tmpl"
proj="$root/$name"

if [ -e "$proj" ] || [ -L "$proj" ]; then
  [ "$apply" -eq 1 ] || die 2 "$name already exists; use --apply to add the missing scaffold"
else
  [ "$apply" -eq 0 ] || die 2 "$name does not exist; drop --apply to create it"
fi
# 何かを作る前に前提を確かめる
if [ "$sync" -eq 1 ]; then
  command -v uv >/dev/null 2>&1 || die 3 "uv not found; install it or pass --no-sync"
fi
initialized=0
if [ "$apply" -eq 0 ]; then
  command -v resoloop >/dev/null 2>&1 || die 3 "resoloop not found; install it before creating a project"
  for shared in .claude/settings.json .pi; do
    [ -e "$root/$shared" ] || die 3 "$shared is missing at the repository root ($root/$shared); the new project links to it"
  done
  resoloop init "$proj" --json >/dev/null || die 3 "resoloop init failed for $name"
  initialized=1
fi
[ -f "$proj/.resoloop.json" ] || die 3 "$name is not a resoloop project (.resoloop.json is missing)"
[ -f "$proj/AGENTS.md" ] || die 3 "$name/AGENTS.md is missing; run resoloop init first"

render() { sed -e "s/{{name}}/$name/g" "$1"; }
# リンクが要る .agents/skills 直下のディレクトリ: ファイルを 1 つ以上持つもの（SKILL.md の有無は問わない）。
# scripts/check-layout.sh の定義（追跡ファイルを 1 つ以上持つディレクトリ）と揃えている
has_files() { [ -d "$1" ] && [ -n "$(find "$1" -type f -print -quit 2>/dev/null)" ]; }

# 1 周目: 作るもの・追記するものを集め、既存ファイルとの食い違いを集める。食い違いがあれば何も変更しない
conflicts=() plan_file_rel=() plan_file_src=() plan_link_rel=() plan_link_target=() append_section=0 append_cache=0
declare -A reported_parent=()

parent_ok() {  # $1=相対パス。途中のディレクトリが symlink や通常ファイルなら食い違いに加え（1 回だけ）、1 を返す
  local parent result=0
  parent="$(dirname -- "$1")"
  while [ "$parent" != . ]; do
    if [ -L "$proj/$parent" ] || { [ -e "$proj/$parent" ] && [ ! -d "$proj/$parent" ]; }; then
      if [ -z "${reported_parent[$parent]+x}" ]; then
        conflicts+=("$parent is not a directory")
        reported_parent["$parent"]=1
      fi
      result=1
    fi
    parent="$(dirname -- "$parent")"
  done
  return "$result"
}

want_file() {  # $1=相対パス、$2=雛形、$3=既存と比べるなら 1
  local rel="$1" src="$2" compare="$3"
  parent_ok "$rel" || return 0
  if [ -L "$proj/$rel" ] || { [ -e "$proj/$rel" ] && [ ! -f "$proj/$rel" ]; }; then
    conflicts+=("$rel is not a regular file")
  elif [ -f "$proj/$rel" ]; then
    if [ "$compare" -eq 1 ] && ! diff -q <(render "$src") "$proj/$rel" >/dev/null; then
      conflicts+=("$rel differs from templates/world-project/$(basename "$src")")
    fi
  else
    plan_file_rel+=("$rel")
    plan_file_src+=("$src")
  fi
}

want_link() {  # $1=相対パス、$2=期待する行き先
  local rel="$1" target="$2" current
  parent_ok "$rel" || return 0
  if [ -L "$proj/$rel" ]; then
    current="$(readlink "$proj/$rel")"
    [ "$current" = "$target" ] || conflicts+=("$rel points to $current, expected $target")
  elif [ -e "$proj/$rel" ]; then
    conflicts+=("$rel exists and is not a symlink")
  elif [ ! -e "$(realpath -m "$(dirname "$proj/$rel")/$target")" ]; then
    conflicts+=("$rel would point to missing $target")
  else
    plan_link_rel+=("$rel")
    plan_link_target+=("$target")
  fi
}

want_file CLAUDE.md "$tmpl/CLAUDE.md" 1
want_file pyproject.toml "$tmpl/pyproject.toml" 0
if [ -L "$proj/AGENTS.md" ]; then
  conflicts+=("AGENTS.md is a symlink; refusing to append to its target")
elif ! grep -qxF '## このプロジェクト固有' "$proj/AGENTS.md"; then
  append_section=1
fi
if parent_ok .resoloop/.gitignore; then
  if [ -f "$proj/.resoloop/.gitignore" ] && [ ! -L "$proj/.resoloop/.gitignore" ]; then
    grep -qxF 'cache/' "$proj/.resoloop/.gitignore" || append_cache=1
  else
    want_file .resoloop/.gitignore "$tmpl/resoloop-gitignore" 0
  fi
fi
want_link .claude/settings.json ../../.claude/settings.json
want_link .pi ../.pi
for sp in "$root"/.agents/sp-*.md; do
  [ -f "$sp" ] || continue
  want_link ".agents/$(basename "$sp")" "../../.agents/$(basename "$sp")"
done
# 隠しエントリ（.old など）も含めて、リンクが要るディレクトリと、対応するディレクトリの無いリンクを探す
shopt -s dotglob
for d in "$proj"/.agents/skills/*/; do
  d="${d%/}"
  has_files "$d" || continue
  n="$(basename "$d")"
  want_link ".claude/skills/$n" "../../.agents/skills/$n"
done
for l in "$proj"/.claude/skills/*; do
  [ -e "$l" ] || [ -L "$l" ] || continue
  n="$(basename "$l")"
  has_files "$proj/.agents/skills/$n" || conflicts+=(".claude/skills/$n has no matching .agents/skills/$n")
done
shopt -u dotglob

if [ ${#conflicts[@]} -gt 0 ]; then
  printf 'CONFLICT: %s\n' "${conflicts[@]}" >&2
  if [ "$initialized" -eq 1 ]; then
    printf '%s was created by resoloop init and remains; no scaffold changes were applied to it\n' "$name" >&2
  else
    printf 'no changes were made to %s\n' "$name" >&2
  fi
  exit 1
fi

# 2 周目: 適用する
for i in "${!plan_file_rel[@]}"; do
  rel="${plan_file_rel[$i]}" src="${plan_file_src[$i]}"
  mkdir -p "$(dirname "$proj/$rel")"
  render "$src" > "$proj/$rel"
  printf 'created: %s\n' "$rel"
done
if [ "$append_section" -eq 1 ]; then
  # 改行で終わっていない AGENTS.md には、先に改行を足してから空行と固有節を追記する
  { [ -z "$(tail -c 1 "$proj/AGENTS.md")" ] || printf '\n'; printf '\n'; render "$tmpl/AGENTS.local.md"; } >> "$proj/AGENTS.md"
  printf 'appended: AGENTS.md (## このプロジェクト固有)\n'
fi
if [ "$append_cache" -eq 1 ]; then
  printf 'cache/\n' >> "$proj/.resoloop/.gitignore"
  printf 'appended: .resoloop/.gitignore (cache/)\n'
fi
for i in "${!plan_link_rel[@]}"; do
  rel="${plan_link_rel[$i]}" target="${plan_link_target[$i]}"
  mkdir -p "$(dirname "$proj/$rel")"
  ln -s "$target" "$proj/$rel"
  printf 'linked: %s -> %s\n' "$rel" "$target"
done

if [ "$sync" -eq 1 ]; then
  (cd "$proj" && uv sync) \
    || die 3 "uv sync failed in $name; the scaffold changes were already applied and only the sync failed (fix the cause, then run 'uv sync' in $name)"
  if ! command -v resoloop >/dev/null 2>&1; then
    printf 'skip: resoloop not found (skills sync check)\n'
  elif resoloop skills sync "$proj" --check; then
    printf 'ok: resoloop skills sync --check\n'
  else
    printf 'WARN: resoloop skills sync --check failed for %s; review the report, then run resoloop skills sync %s --update\n' "$name" "$name" >&2
  fi
fi
printf 'DONE: %s\n' "$name"
```

- [ ] **Step 4: テストが通り、既存プロジェクトに影響が無いことを確かめる**

Run:

```bash
bash tests/scripts/test-new-world.bash
for p in MyResoniteProject akichi slum02; do bash scripts/new-world.sh --apply --no-sync "$p" | tail -n 1; done
git status --short -- MyResoniteProject akichi slum02 | wc -l
```

Expected: `PASS: new-world script behaves as specified`、`DONE: MyResoniteProject` / `DONE: akichi` / `DONE: slum02`、`0`（既存 3 プロジェクトへの `--apply` は何も変えない）

Global Constraints の回帰確認も実行する。

- [ ] **Step 5: コミット**

```bash
git add scripts/new-world.sh tests/scripts/test-new-world.bash
git commit -m "fix(new-world): reject ignored names and harden the scaffold checks"
```

---

### Task 7: 運用文書と参照の整理（仕様 6.4、持ち越し N-5）

`docs/resoloop-fork-workflow.md` を作り、旧 spec に後継の注記を足し、統合手順に Rebuild 時の fork の扱いを追記する。ルート `AGENTS.md` が参照するファイルが実在することをテストで固定する（N-5）。

**Files:**
- Create: `docs/resoloop-fork-workflow.md`
- Modify: `docs/superpowers/specs/2026-09-24-resonite-devcontainer-tooling-design.md`（冒頭に注記を 1 段落）
- Modify: `docs/integration.md`（「マージ後にユーザが行うこと」に 8・9 を追記）
- Modify: `tests/scripts/test-instructions.bash`（参照先の実在の検査）

**Interfaces:**
- Consumes: Task 1〜3 のファイル名・サブコマンド・終了コード・`status` の行の見出し・環境変数（文書はこれらを説明する）

- [ ] **Step 1: 失敗するテストを書く**

`tests/scripts/test-instructions.bash` を次の差分のとおりに変える。

```diff
--- a/tests/scripts/test-instructions.bash
+++ b/tests/scripts/test-instructions.bash
@@ -37,6 +37,11 @@ for s in 'オブジェクトごとに、1つのメッシュにする' '長大な
   'monitoring-long-tasks' '.agents/monitoring-runtimes.md' 'find-docs' '3 回まで'; do
   has AGENTS.md "$s"
 done
+# AGENTS.md が参照するファイルが実在する（ResoLoop の版管理の 3 件はフェーズ 3 で作成、持ち越し N-5）
+for f in .devcontainer/resoloop.lock scripts/resoloop-fork.sh docs/resoloop-fork-workflow.md \
+  scripts/new-world.sh scripts/check-layout.sh .agents/monitoring-runtimes.md; do
+  [ -e "$f" ] || fail "AGENTS.md refers to missing $f"
+done
 # 旧リポジトリ由来の記述とツール固有の記述を持ち込まない
 for s in 'reStructuredText' 'Gitleaks' 'contingency' 'verify.sh' 'verify-devenv' 'AskUserQuestion' 'TaskOutput' 'npx ctx7'; do
   lacks AGENTS.md "$s"
```

- [ ] **Step 2: テストが失敗することを確かめる**

Run: `bash tests/scripts/test-instructions.bash`
Expected: 終了コード 1。`FAIL: AGENTS.md refers to missing docs/resoloop-fork-workflow.md`

- [ ] **Step 3: 文書を書く**

`docs/resoloop-fork-workflow.md`:

````markdown
# ResoLoop の版管理と fork の運用

仕様: `docs/superpowers/specs/2026-09-26-create-reso-world-redesign-design.md` 6 章。この文書は、`.devcontainer/resoloop.lock` と `scripts/resoloop-fork.sh` を使う日々の手順をまとめる。

## 仕組み

- 導入する ResoLoop の版は `.devcontainer/resoloop.lock` を正とする。手元で `dotnet tool update` などを実行して導入だけを変えない。
- Dev Container の postCreate（`.devcontainer/install_beforehand.bash`）は `.devcontainer/install_resoloop.bash` を実行する。導入済みの版がロックの期待版と同じなら何もしない。違えば、`nuget` モードでは NuGet の公開版を `dotnet tool install` / `update --allow-downgrade` で導入し、`fork` モードでは `scripts/resoloop-fork.sh install` に任せる。最後に `resoloop --version` が期待版と一致することを確かめ、一致しなければ postCreate を失敗させる。
- `.devcontainer/verify-resonite-tooling.bash` と `scripts/check-layout.sh` もロックを読む。check-layout はロックの必須キーと、`RESOLOOP_FORK_SDK` が `devcontainer.json` の dotnet Feature の `additionalVersions` に含まれることを検査する。

### ロックのキー

| キー | 意味 |
| --- | --- |
| `RESOLOOP_MODE` | `fork`（fork をビルドして導入する）または `nuget`（NuGet の公開版を導入する） |
| `RESOLOOP_NUGET_VERSION` | `nuget` モードの期待版 |
| `RESOLOOP_FORK_ORIGIN` | fork（usaturn/resoloop）の URL。checkout の `origin` |
| `RESOLOOP_FORK_UPSTREAM` | 上流（orange3134/resoloop）の URL。checkout の `upstream` |
| `RESOLOOP_FORK_REF` | 導入するコミットを含む fork のブランチ（記録用） |
| `RESOLOOP_FORK_COMMIT` | 導入するコミット（40 桁） |
| `RESOLOOP_FORK_PACKAGE_VERSION` | `fork` モードの期待版。`dotnet pack` にこの版を渡す |
| `RESOLOOP_FORK_PR` | 修正を上流へ出した PR の URL（記録用） |
| `RESOLOOP_FORK_SDK` | fork の `global.json` が要求する .NET SDK。`devcontainer.json` の `additionalVersions` と揃える |

書式は `KEY=VALUE` の 1 行 1 項目で、値には英数字と `._:/@+-` だけを使う。9 個のキーはモードにかかわらずすべて必須。

**`RESOLOOP_FORK_COMMIT` を変えるときは `RESOLOOP_FORK_PACKAGE_VERSION` も必ず変える。** 導入済みの版が期待版と同じなら、`install` はビルドし直さずに終わる。版を据え置くと、新しいコミットは導入されない。

## checkout の位置と remote 構成

fork の checkout は `external/resoloop`（ルートの `.gitignore` で無視する）に置く。remote は次の 2 つで、`scripts/resoloop-fork.sh` はロックの URL と比べて食い違いがあれば止まる（末尾の `/` と `.git` の違いは同じ URL とみなす）。

- `origin`: https://github.com/usaturn/resoloop.git（fork）
- `upstream`: https://github.com/orange3134/resoloop.git（上流）

`/workspaces` 直下には置かない。`/workspaces` はコンテナ内の root 所有のディレクトリで、ホストと共有されるのはリポジトリ（`/workspaces/<repo>`）だけなので、直下に置いた checkout はコンテナを作り直すと消える。`external/` はリポジトリの中にあるので Rebuild 後も残り、次の postCreate は clone を省いて checkout とビルドだけを行う。

## `scripts/resoloop-fork.sh` のサブコマンド

| サブコマンド | 動作 | ネットワーク |
| --- | --- | --- |
| `clone` | `external/resoloop` に `origin` と `upstream` を持つ checkout を作る。既にあれば remote の URL を確かめるだけ | 取得のみ |
| `sync` | `upstream` と `origin` を fetch し、fork の `main` を `upstream/main` へ fast-forward で push する。ローカルの `main` も追従させる。fork の `main` に上流に無いコミットがあれば何も push せずに止まる | **fork へ push する** |
| `checkout` | ロックの `RESOLOOP_FORK_COMMIT` を detached で取り出す（手元に無ければ `origin` から fetch）。追跡ファイルに未コミットの変更があれば止まる | 必要なときだけ取得 |
| `build` | `RESOLOOP_FORK_SDK` があることを確かめ、`dotnet build ResoLoop.slnx -c Release` と `dotnet pack`（`artifacts/fork` に `ResoLoop.<期待版>.nupkg`）を実行する | NuGet の復元 |
| `test` | `dotnet test ResoLoop.slnx` を実行する。postCreate では実行しない | NuGet の復元 |
| `install` | 導入済みの版が期待版と違えば `clone` → `checkout` → `build` → `dotnet tool install` / `update --allow-downgrade` を実行する。最後に `resoloop --version` を照合する。`nuget` モードでは止まる | 取得のみ |
| `status` | ロックの期待版、導入済みの版、checkout の HEAD と状態、remote の構成を表示する。何も変更しない | なし |

`build`・`test` と `install` のビルドは `external/resoloop` に `cd` して実行する（dotnet は `global.json` をカレントディレクトリから探すため）。

終了コード: 0 成功、1 状態が期待と違う（git の checkout でない、remote の食い違い、未コミットの変更、コミットが `origin` に無い、fork の `main` が上流から分岐、導入後の版の不一致など）、2 使い方の誤り、3 前提不足（ロックの欠落・不正、git / dotnet が無い、SDK が無い、checkout が無い）、4 git や dotnet のコマンドの失敗。

環境変数 `RESOLOOP_LOCK_FILE`（ロックファイル）と `RESOLOOP_FORK_CHECKOUT`（checkout の位置）で既定の場所を差し替えられる。主にテスト用。

## 状態を確かめる

```bash
bash scripts/resoloop-fork.sh status
```

`installed version` が `matches the lock` で、`checkout` が `matches the lock` かつ `clean`、`remotes` がロックと一致していれば、手元はロックどおりである。`DIFFERS from the lock` が出たら、ロックを正として `bash .devcontainer/install_resoloop.bash`（または `bash scripts/resoloop-fork.sh install`）で導入し直す。

## 修正の流れ

1. `bash scripts/resoloop-fork.sh sync` で fork の `main` を上流に追従させる（fork へ push する）。
2. `git -C external/resoloop switch -c fix/<topic> upstream/main` で作業ブランチを作る。
3. 修正してコミットする。
4. `bash scripts/resoloop-fork.sh test` でテストを通す。
5. `git -C external/resoloop push -u origin fix/<topic>` で fork へ push する。ロックを変える前に push しておくと、別の環境の postCreate も `origin` からコミットを取得できる。
6. ロックを更新する。`RESOLOOP_FORK_REF=fix/<topic>`、`RESOLOOP_FORK_COMMIT` は `git -C external/resoloop rev-parse HEAD` の 40 桁、`RESOLOOP_FORK_PACKAGE_VERSION` は新しい版（例: `0.1.0-preview.14.pr2.20261001`）にする。
7. `bash scripts/resoloop-fork.sh install` でビルドして導入する。checkout は detached になるので、作業を続けるときは `git -C external/resoloop switch fix/<topic>` で戻る。
8. `bash scripts/check-layout.sh` が通ることを確かめ、ロックの変更をこのリポジトリにコミットする。
9. 上流へ PR を出したら、その URL を `RESOLOOP_FORK_PR` に記録する（例: `gh pr create --repo orange3134/resoloop --head usaturn:fix/<topic>`）。

`external/resoloop` の追跡ファイルに未コミットの変更があると、`install`（postCreate からの実行を含む）は `checkout` の段階で止まる。コミットするか stash してから `bash .devcontainer/install_resoloop.bash` を実行し直す。

## fork 内の PR と、上流のリリース後の切り替え

- fork 内の PR（usaturn/resoloop#1）はレビュー用であり、マージしない。
- 修正が上流にマージされてリリースされたら、ロックの `RESOLOOP_MODE=nuget` と `RESOLOOP_NUGET_VERSION=<リリース版>` を更新し、`bash .devcontainer/install_resoloop.bash` を実行する。fork 用のキーは記録として残す（どのモードでも必須）。

## 上流への PR 候補

- `resoloop init` が作る `.resoloop/.gitignore` に `cache/` が無い（このリポジトリでは `scripts/new-world.sh` が追記している）。
- `global.json` の `rollForward` が `latestPatch` なので、SDK の feature band（10.0.2xx と 10.0.4xx など）を跨げない。このため `devcontainer.json` の `additionalVersions` で 10.0.201 を追加している。

## `tmp/` にある旧 checkout の整理

再設計の前に手作業で作った checkout と作業記録が `tmp/` に残っている。削除は必要な内容を確かめてから手で行う（自動では消さない）。

| ディレクトリ | 中身 | 扱い |
| --- | --- | --- |
| `tmp/resoloop-blender5-uv-20260925` | remote はロックと同じで、HEAD はロックのコミット（ブランチ `fix/blender5-uv-export`）。未追跡の `reviews/` がある | `external/resoloop` がまだ無ければ、`reviews/` を必要に応じて退避してから `mv tmp/resoloop-blender5-uv-20260925 external/resoloop` で移し、`bash scripts/resoloop-fork.sh status` で確かめる。clone を省ける |
| `tmp/usaturn-resoloop-pr1` | fork 内 PR #1 のレビュー用 checkout。未追跡の `reviews/` がある | `reviews/` を必要に応じて退避してから削除する |
| `tmp/resoloop-uv0-fix-20260924` | 上流 v0.1.0-preview.13 の shallow checkout に、未コミットの草稿（4 ファイル）がある | `git -C tmp/resoloop-uv0-fix-20260924 diff > ~/resoloop-uv0-fix-draft.patch` で草稿を保存してから削除する |
| `tmp/resoloop-skills-20260924-1526` | git の checkout ではない作業記録（レビューと差分の Markdown など） | 必要なものを退避してから削除する |

## 対象外

flux-sdk の導入はこの運用の対象外とする。
````

旧 spec の冒頭:

```diff
--- a/docs/superpowers/specs/2026-09-24-resonite-devcontainer-tooling-design.md
+++ b/docs/superpowers/specs/2026-09-24-resonite-devcontainer-tooling-design.md
@@ -1,5 +1,7 @@
 # Dev Container による Resonite 開発ツールのセットアップ
 
+> **後継:** ResoLoop の版の方針（最新のプレビュー版を導入し、版を固定しない）は、`docs/superpowers/specs/2026-09-26-create-reso-world-redesign-design.md` 6 章（`.devcontainer/resoloop.lock` による固定と fork 運用）で置き換えた。現在の手順は `docs/resoloop-fork-workflow.md` を参照する。本書の ResoLoop 以外の記述（.NET 10 SDK と Blender の導入、失敗時の扱い）は引き続き有効である。
+
 ## 目的と対象範囲
 
 Ubuntu 26.04 の Dev Container を作成すると、ResoLoop と Blender を用いた Resonite ワールド開発に必要なコマンドラインツールが揃うようにする。開発者とコーディングエージェントが .NET 10 SDK、プレビュー版を含む最新版の ResoLoop、GUI を使わずに実行できる Blender を利用できる状態を目指す。
```

`docs/integration.md`:

```diff
--- a/docs/integration.md
+++ b/docs/integration.md
@@ -68,3 +68,5 @@
 5. 不要になった未追跡物を削除する。`akichi/.agents/skills/` の Blender 系 10 スキルと `references/`・`tests/`（ルートの `.agents/skills/` に移ったため）、`akichi/.claude/skills/` と `MyResoniteProject/.claude/skills/` の Blender 系 symlink、ルート `.claude/skills/` の `resonite-*` の未追跡 symlink（resonite-* はプロジェクト側で読む）、`MyResoniteProject/.agents/sp-*.md` のうち `sp-implementer.md` 以外の 8 件（pi-superagents の組み込み定義と同一のため）。
 6. `MyResoniteProject/` で `uv sync` を実行し、`uv run pytest` が通ることを確認する（プロジェクト専用の環境になった）。
 7. `bash scripts/check-layout.sh` がすべて `ok` で `PASS: check-layout` になることを確認する。
+8. （任意）Rebuild の前に `tmp/resoloop-blender5-uv-20260925` を `external/resoloop` へ移すと、postCreate の clone を省ける。手順は `docs/resoloop-fork-workflow.md` の「`tmp/` にある旧 checkout の整理」にある。
+9. Rebuild の postCreate は `.devcontainer/resoloop.lock` の fork をビルドして導入する（ネットワークと数分を要する）。終わったら `bash scripts/resoloop-fork.sh status` で、導入済みの版と checkout がロックと一致することを確認する。`tmp/` の残りの旧 checkout は同じ節の手順で整理する。
```

- [ ] **Step 4: テストと文面を確かめる**

Run:

```bash
bash tests/scripts/test-instructions.bash
grep -nE '契約|原子的|製品|着地' docs/resoloop-fork-workflow.md docs/integration.md \
  docs/superpowers/specs/2026-09-24-resonite-devcontainer-tooling-design.md || echo 'wording ok'
```

Expected: `PASS: root instruction files follow spec 5.2 and 5.3` と `wording ok`。文書に書いたサブコマンド・終了コード・`status` の見出しが `scripts/resoloop-fork.sh` と一致することを目で確かめる。Global Constraints の回帰確認も実行する。

- [ ] **Step 5: コミット**

```bash
git add docs/resoloop-fork-workflow.md docs/superpowers/specs/2026-09-24-resonite-devcontainer-tooling-design.md \
  docs/integration.md tests/scripts/test-instructions.bash
git commit -m "docs(resoloop): add the fork workflow and point the old spec to it"
```

---

### Task 8: フェーズ 3 の一括検証と push（controller が実行）

コード変更は無い。controller が実行し、結果を台帳に記録する。

- [ ] **Step 1: 一括検証**

```bash
cd "$W"
git status --short | wc -l                                                     # 0
for t in tests/scripts/*.bash; do bash "$t" >/dev/null 2>&1 && echo "PASS $t" || echo "FAIL $t"; done
                                                                               # 6 件とも PASS（resoloop-fork が増えた）
bash scripts/check-layout.sh | tail -n 2                                       # ok: resoloop lock (mode fork, expects 0.1.0-preview.14.pr1.20260925) と PASS: check-layout
git ls-files -i -c --exclude-standard                                          # MyResoniteProject/.resoloop/tokyo-nova/pipeline.json だけ
for t in .devcontainer/test-*.bash; do bash "$t" >/dev/null 2>&1 && echo "PASS $t" || echo "FAIL $t"; done
                                                                               # 9 PASS（test-resoloop-lock が増えた）、test-herdr-migration だけ FAIL（既知、フェーズ 4）
uv run pytest -q 2>&1 | tail -n 1                                              # 34 failed, 192 passed, 1 skipped
for P in MyResoniteProject akichi slum02; do (cd "$P" && uv run pytest -q 2>&1 | tail -n 1); done
                                                                               # 52 passed / 66 passed / 215 passed
bash .devcontainer/verify-resonite-tooling.bash; echo "verify=$?"              # verify=0
git log --oneline main..HEAD | wc -l                                           # 41（フェーズ 2 までの 33 ＋計画書 1 ＋Task 1〜7 の 7）
git -C "$M" status --short | grep -c '^?? private/'                             # 0
```

Expected は各行のコメントのとおり。`main..HEAD` の件数は fix round のコミットがあれば増える（台帳に記録する）。

- [ ] **Step 2: 実物の fork で clone・checkout・status を確かめる（取得だけ。push・ビルド・導入はしない）**

```bash
cd "$W"
bash scripts/resoloop-fork.sh status      # installed version: ... (matches the lock)、checkout: ... is missing
bash scripts/resoloop-fork.sh clone       # cloned: $W/external/resoloop (origin https://github.com/usaturn/resoloop.git, upstream https://github.com/orange3134/resoloop.git)
bash scripts/resoloop-fork.sh checkout    # checked out: ... at 1ef4d18ca4010b2d5740b36af9c0c7a67785a1ca (detached)
bash scripts/resoloop-fork.sh status      # checkout: ... (detached, clean, matches the lock)、remotes: origin and upstream match the lock
git status --short | wc -l                # 0（external/ は ignore 対象）
```

`$W/external/resoloop` は残してよい（ignore 対象。worktree の削除とともに消える）。

- [ ] **Step 3: push**

```bash
git -C "$W" fetch origin
git -C "$W" merge-base --is-ancestor origin/chore/repo-redesign HEAD && git -C "$W" push origin chore/repo-redesign
git -C "$M" ls-remote --heads origin                                            # 5 本、chore/repo-redesign が HEAD と一致
```

- [ ] **Step 4: ブランチ全体の最終レビューと handoff**

最上位モデルのレビュアーに `MERGE_BASE..HEAD`（`MERGE_BASE` は `ebec0cc`）のレビューを依頼し、指摘は fix wave で直す。完了後、台帳の最後に `PHASE 3 COMPLETE.` を書き、区切りとして agent-handoff で引き継ぎ書を作る。

---

## 持ち越し（フェーズ 4〜6）

前回までの引き継ぎ書と本計画で見つかった保留事項。本計画では着手しない。フェーズ 3 の項目（N-5、N-7、N-9、N-10、N-15、N-16）は本計画の Task 1〜7 で扱う。

| ID | フェーズ | 内容 |
| --- | --- | --- |
| P-4 | 4 | テストの git 設定の隔離で `safe.directory` も外れる。CI では `GIT_CONFIG_COUNT=2`、`GIT_CONFIG_KEY_1=safe.directory`、`GIT_CONFIG_VALUE_1="$root"` を足す。`test-new-world.bash` と本計画の `test-resoloop-fork.bash` も同じ隔離を使う |
| N-1 | 4 | CI で `tests/scripts/*.bash`（test-gitignore、test-check-layout、test-instructions、test-agent-config、test-new-world、test-resoloop-fork）も実行する |
| N-6 | 4 | `.claude/settings.json` のプラグイン一覧を Dev Container の導入一覧と合わせる（仕様 7.1） |
| N-8 | 4 | check-layout に仕様 9.1 のマウント検査（`initialize.bash` の mkdir 集合と `devcontainer.json` の mounts 集合の一致）を足す |
| N-11 | 4 | CI に載せる前に、`test-instructions.bash` のペルソナ節の sha256 固定の扱いを決める。縮小 PATH（`/usr/local/bin:/usr/bin:/bin` に resoloop / uv が無い前提。`test-new-world.bash` のケース 10・15、`test-check-layout.bash` のケース 22）を、モック用ディレクトリだけの PATH に変える（N-1・P-4 と一緒に） |
| N-2 | 5 | 統合したスキルに残る maatlog・`public/`・`verify.sh`・`docs_draft/superpowers/` の記述の書き直し（仕様 8.2）。repository-ownership の削除（スキル、テスト、`.cursor/rules/repository-ownership.mdc`、`.claude/skills/repository-ownership` の symlink）。pi-model-name の 27 件の失敗 |
| N-13 | 5 | `AGENTS.md` の冒頭に「本文のパスはリポジトリルート基準」を 1 文足す |
| N-14 | 5 | スキル書き直し（N-2）で個別に直す項目: pr-review の手順 5 のメインエージェント向けの追跡指示（呼び出し元・呼び出し先、依存関係ファイル、既存テストを辿る）、「短縮・一般化しない」、手順 1 の「未指定」の重複表現、contract テストの固定強化（`--model-name` の `create` 行、委譲制限、allowed-tools）。agent-handoff の概要の文言と evals の q2。repo-cleanup の gitignore ディレクトリの削除規則と allowed-tools（`python3` を `uv run` に置き換えるときに合わせる）。simplify-in-subagent の Examples（`/simplify-in-subagent` の名前と「question tool 不要」の補足） |
| N-3 | 6 | README に書くこと: Codex は信頼済みのときだけ `.codex/config.toml` を読む、cursor-agent は初回に MCP の承認が要る、Devin は symlink 経由の同名スキルを 1 回だけ表示する（`.devin/config.json` は不要）、Cursor と dsh のスキル可視性の制約、pi-superagents の組み込み定義は追跡しない（判断事項 D-1） |
| N-4 | 6 | マージ直前に統合手順の衝突一覧を再実行し、`docs/integration.md` の件数を最新にする |
| N-12 | 6 | `docs/integration.md`（N-4・P-1 と同時に）: 項目 3 に sp-implementer.md（ブランチでは symlink なので、退避した実ファイルはルートの `.agents/sp-implementer.md` と比べる）の補足、項目 2 の 3 ブロックは同じシェルで実行すると明記、項目 3・5 の根拠への参照 |
| N-17 | 6 | 仕様 9.3 の実機確認に、Devin で simplify-in-subagent を呼んだときにサブエージェントが edit / exec を持つかを含める |
| N-18 | 6 | 仕様 9.3 の実機確認に、Rebuild の postCreate で fork のビルドと導入が通ること（`dotnet --list-sdks` に 10.0.201、`dotnet build` / `dotnet pack` の引数、`resoloop --version` の出力がロックの期待版と一致）を含める。コンテナに SDK 10.0.201 が無いため、フェーズ 3 ではモックでしか確かめていない |
| P-1 | 6 | `docs/integration.md` と仕様 10.1 の退避手順に `git checkout -- .claude/settings.local.json` を足し、CLAUDE.md / APPEND_SYSTEM.md の破棄を「マージ前」節へ移す |
| P-2 | 6 | `.git/info/exclude` の `/private/` の行は、tokyo-nova 系ブランチを新しい main に rebase した後に消す |
| P-3 | 6 | フェーズ 0・1 の計画書の 380 行目の注記の誤りと、830 行目の integration.md ひな形の古い文面を直す |
| P-7 | 6 | 仕様 4.4 の `/tmp/`・`**/tmp/`・`/docs_draft/`・`**/docs_draft/` の表記を、実際の `tmp/`・`docs_draft/` に揃える |
| M-5 | 6 | main の再 fast-forward は `git fetch . feat/slum02-slum:main` で行う |
