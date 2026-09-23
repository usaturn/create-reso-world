# Resonite 開発ツールの Dev Container 導入 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ubuntu 26.04 の Dev Container に .NET 10、最新版の ResoLoop、GUI 不要の Blender を導入し、コンテナ内で利用可能か確認する。

**Architecture:** .NET SDK は Dev Container Feature、Blender は既存の apt 導入手順に追加する。ResoLoop の初回導入・再実行時の更新を専用スクリプトへ分離し、`postCreateCommand` の既存手順に接続する。ネットワークやホスト側の Resonite に依存しない検証と、利用可能な場合のコンテナ再作成後のスモークテストを分ける。

**Tech Stack:** Dev Container JSONC、Bash、.NET 10 SDK／グローバル .NET ツール、Ubuntu 26.04 の Blender、zsh。

**Spec:** `docs/superpowers/specs/2026-09-24-resonite-devcontainer-tooling-design.md`

## Global Constraints

- ベースイメージは `mcr.microsoft.com/devcontainers/base:ubuntu26.04`、.NET SDK は 10 系。既存の Node と GitHub CLI Feature は維持する。
- ResoLoop は `--prerelease` を使い、`--version` を指定しない。公開済みのプレビュー版へ固定しない。
- Blender は GUI を起動しない。Resonite 本体、ResoniteLink、`RESONITE_LINK_URL` は設定しない。`resoloop doctor` は必須の検証に含めない。
- `.devcontainer/install_beforehand.bash` の番号付き進捗と必須処理の失敗時中断を維持する。`STEP_TOTAL` は現在 27。
- リポジトリ内の Python ツールは uv で実行し、`python3` コマンドは使用しない。Blender 組み込みの Python 実行は Blender 自身の CLI で行う。
- `./scripts/ci/verify-devenv.sh`、Docker CLI、Dev Container CLI は現時点の checkout に見当たらない。実行可否を再確認し、無い場合は未検証と明記する。
- Task は 1 件ずつ完結させ、Task ごとに差分とテスト結果を確認する。ユーザーの `.pi/APPEND_SYSTEM.md` の未コミット変更に触れない。

## Review Focus

1. `dotnet tool list --global` が失敗した場合に「未導入」と誤認してインストールを始めず、中断するか（Task 2）。
2. 一覧の別パッケージ名に `resoloop` が含まれても、パッケージ ID が一致しなければ初回導入を選ぶか（Task 2）。
3. 既存のツールがプレビュー版でも、再実行で `--prerelease` を指定して最新版へ更新し、バージョンを固定しないか（Task 2）。
4. ツール導入コマンドが成功しても `resoloop --version` が失敗すれば、中断するか（Task 2 と Task 3）。
5. Blender が存在してもバックグラウンド実行に失敗すれば、コンテナのセットアップを失敗にするか（Task 3）。

## ファイルの担当

- `.devcontainer/devcontainer.json`: .NET 10 Feature とエージェント起動環境の PATH。
- `.devcontainer/install_beforehand.bash`: Blender の apt 導入、ResoLoop 導入とツール確認を既存の進捗手順へ接続。
- `.devcontainer/install_resoloop.bash`（新規）: .NET SDK 確認、ResoLoop の導入／更新、CLI の起動確認。
- `.devcontainer/verify-resonite-tooling.bash`（新規）: .NET 10、ResoLoop、Blender のヘッドレス動作を確認。
- `.devcontainer/zshrc.txt`: 対話的な開発用シェルのグローバル .NET ツール PATH。
- `.devcontainer/test-resonite-feature.bash`（新規）: Dev Container 設定と Blender apt 導入の回帰検証。
- `.devcontainer/test-install-resoloop.bash`（新規）: `dotnet` を差し替えた導入／更新／失敗系テスト。
- `.devcontainer/test-verify-resonite-tooling.bash`（新規）: コマンドを差し替えたツール確認とセットアップ接続の検証。
- `.devcontainer/README.md`: 利用者向けの導入範囲、再作成、確認方法、Linux 未保証の説明。

---

### Task 1: .NET 10 と Blender の導入設定

**Files:**
- Modify: `.devcontainer/devcontainer.json`（`features` と `remoteEnv`）
- Modify: `.devcontainer/install_beforehand.bash`（現在の `sudo apt install -y ...`）
- Test: `.devcontainer/test-resonite-feature.bash`（新規）

**Interfaces:**
- Consumes: Dev Container の Feature と既存の apt 導入手順。
- Produces: `postCreateCommand` の開始時に利用できる `dotnet` と `blender`。PATH には `${containerEnv:PATH}:/home/vscode/.dotnet/tools` を含める。

- [ ] **Step 1: 先に設定検証テストを作る。** 次の内容を `.devcontainer/test-resonite-feature.bash` に置く。現行ファイルにない Feature と `blender` を検査する。

```bash
#!/bin/bash
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
config="$root/.devcontainer/devcontainer.json"
installer="$root/.devcontainer/install_beforehand.bash"
grep -qF '"ghcr.io/devcontainers/features/dotnet:2"' "$config"
grep -A 2 -F '"ghcr.io/devcontainers/features/dotnet:2"' "$config" | grep -qF '"version": "10.0"'
grep -qF '"PATH": "${containerEnv:PATH}:/home/vscode/.dotnet/tools"' "$config"
grep -qE 'sudo apt install -y .*blender' "$installer"
printf 'PASS: .NET 10 Feature and Blender package configured\n'
```

- [ ] **Step 2: RED を確認する。** `bash .devcontainer/test-resonite-feature.bash` を実行し、Feature 不在で非ゼロ終了することを確認する。最初の RED で実際のフォーマットが異なれば後述の contingency に記録する。
- [ ] **Step 3: 最小限の設定変更をする。** 既存 `features` に次のエントリを加え、`remoteEnv` をトップレベルに置く。既存の Node／GitHub CLI は消さない。apt の既存行の末尾へ `blender` を加える。

```jsonc
"ghcr.io/devcontainers/features/dotnet:2": {
  "version": "10.0"
}
```

```jsonc
"remoteEnv": {
  "PATH": "${containerEnv:PATH}:/home/vscode/.dotnet/tools"
}
```

```bash
sudo apt install -y vim tig ripgrep fzf bubblewrap libglib2.0-0t64 blender
```

- [ ] **Step 4: GREEN と静的確認を行う。** `bash .devcontainer/test-resonite-feature.bash` と `bash -n .devcontainer/install_beforehand.bash` が成功することを確認する。`devcontainer.json` は JSONC なので `jq` に直接渡さず、利用可能なら `devcontainer read-configuration --workspace-folder "$PWD"` で設定の解決を確認する。実行できない場合は未検証と記録する。
- [ ] **Step 5: この Task の差分とテスト結果をレビューし、隔離ブランチが用意できていれば対象ファイルだけをコミットする。** `git diff -- .devcontainer/devcontainer.json .devcontainer/install_beforehand.bash` を確認し、`git add .devcontainer/devcontainer.json .devcontainer/install_beforehand.bash .devcontainer/test-resonite-feature.bash && git commit -m "Add .NET 10 and Blender to the Dev Container"`。`public` や既存のユーザー変更は stage しない。

### Task 2: ResoLoop 導入・更新の独立した処理

**Files:**
- Create: `.devcontainer/install_resoloop.bash`
- Test: `.devcontainer/test-install-resoloop.bash`

**Interfaces:**
- Consumes: Feature が用意した `dotnet`、呼び出し元の `$HOME` と `$PATH`。
- Produces: `bash .devcontainer/install_resoloop.bash` の終了コード。成功時に `$HOME/.dotnet/tools/resoloop` が起動でき、失敗時は非ゼロ終了する。Task 3 の `install_beforehand.bash` から呼ぶ。

- [ ] **Step 1: fake `dotnet` によるテストを作る。** `.devcontainer/test-install-resoloop.bash` に隔離 HOME と fake bin を作り、下記の一覧・導入／更新コマンドを記録する。実際の NuGet やホスト HOME には触れない。

```bash
#!/bin/bash
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
tmp="$(mktemp -d)"
trap 'rm -rf -- "$tmp"' EXIT
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
    printf '%s\n' "${DOTNET_LIST_LINE:-}" ;;
  'tool install --global ResoLoop --prerelease'|'tool update --global ResoLoop --prerelease')
    printf '%s\n' "$*" >> "$DOTNET_CALLS"
    [ "${DOTNET_INSTALL_FAIL:-0}" = 0 ] || exit 16 ;;
  *) printf 'Unexpected dotnet invocation: %s\n' "$*" >&2; exit 17 ;;
esac
MOCK
chmod +x "$tmp/bin/dotnet"
cat > "$tmp/home/.dotnet/tools/resoloop" <<'MOCK'
#!/bin/bash
[ "${RESOLOOP_VERSION_FAIL:-0}" = 0 ] || exit 18
[ "$*" = '--version' ] || exit 19
printf 'resoloop test-version\n'
MOCK
chmod +x "$tmp/home/.dotnet/tools/resoloop"
export HOME="$tmp/home" PATH="$tmp/bin:$PATH" DOTNET_CALLS="$tmp/calls"
# 初回導入: 一覧が空でも --prerelease を付け、--version は付けない。
bash "$root/.devcontainer/install_resoloop.bash"
grep -qx 'tool install --global ResoLoop --prerelease' "$DOTNET_CALLS"
# 更新: 一覧の ID が一致したときだけ update する。
: > "$DOTNET_CALLS"
DOTNET_LIST_LINE='ResoLoop 0.1.0-preview.1 resoloop' bash "$root/.devcontainer/install_resoloop.bash"
grep -qx 'tool update --global ResoLoop --prerelease' "$DOTNET_CALLS"
# 無関係の部分一致はインストール扱い。
: > "$DOTNET_CALLS"
DOTNET_LIST_LINE='my-resoloop-plugin 1.0.0 other' bash "$root/.devcontainer/install_resoloop.bash"
grep -qx 'tool install --global ResoLoop --prerelease' "$DOTNET_CALLS"
# 一覧取得失敗時はインストールしない。
: > "$DOTNET_CALLS"
if DOTNET_LIST_FAIL=1 bash "$root/.devcontainer/install_resoloop.bash"; then exit 1; fi
[ ! -s "$DOTNET_CALLS" ]
# インストーラ成功でも CLI 起動失敗なら失敗。
if RESOLOOP_VERSION_FAIL=1 bash "$root/.devcontainer/install_resoloop.bash"; then exit 1; fi
if DOTNET_LIST_LINE='ResoLoop 0.1.0-preview.1 resoloop' DOTNET_INSTALL_FAIL=1 \
    bash "$root/.devcontainer/install_resoloop.bash"; then exit 1; fi
# SDK 不在、SDK 一覧取得失敗、ダウンロード失敗も伝える。
if DOTNET_SDKS='8.0.100 [/usr/share/dotnet/sdk]' bash "$root/.devcontainer/install_resoloop.bash"; then exit 1; fi
if DOTNET_SDK_FAIL=1 bash "$root/.devcontainer/install_resoloop.bash"; then exit 1; fi
if DOTNET_INSTALL_FAIL=1 bash "$root/.devcontainer/install_resoloop.bash"; then exit 1; fi
# shim がない場合も PATH の別位置にあるコマンドで誤って通さない。
rm "$HOME/.dotnet/tools/resoloop"
if bash "$root/.devcontainer/install_resoloop.bash"; then exit 1; fi
printf 'PASS: ResoLoop global tool install/update and failures\n'
```

- [ ] **Step 2: RED を確認する。** `bash .devcontainer/test-install-resoloop.bash` を実行し、専用スクリプト未作成で非ゼロ終了することを確認する。
- [ ] **Step 3: 専用スクリプトを実装する。** `.devcontainer/install_resoloop.bash` の内容。`tool list` の失敗を未導入と誤認せず、一覧の先頭列のパッケージ ID を正確に比較する。更新後の shim を優先して実行する。

```bash
#!/bin/bash
set -euo pipefail
if ! command -v dotnet >/dev/null 2>&1; then
    echo 'ResoLoop setup: dotnet is not available.' >&2
    exit 1
fi
if ! dotnet --list-sdks | grep -qE '^10\.'; then
    echo 'ResoLoop setup: .NET 10 SDK is not installed.' >&2
    exit 1
fi
if ! installed="$(dotnet tool list --global)"; then
    echo 'ResoLoop setup: cannot list global .NET tools.' >&2
    exit 1
fi
if printf '%s\n' "$installed" | awk 'tolower($1)=="resoloop" {found=1} END {exit !found}'; then
    dotnet tool update --global ResoLoop --prerelease </dev/null || {
        echo 'ResoLoop setup: updating the global tool failed.' >&2
        exit 1
    }
else
    dotnet tool install --global ResoLoop --prerelease </dev/null || {
        echo 'ResoLoop setup: installing the global tool failed.' >&2
        exit 1
    }
fi
export PATH="$HOME/.dotnet/tools:$PATH"
if ! "$HOME/.dotnet/tools/resoloop" --version </dev/null; then
    echo 'ResoLoop setup: installed CLI cannot run on this container.' >&2
    exit 1
fi
```

- [ ] **Step 4: GREEN と静的確認を行う。** `bash .devcontainer/test-install-resoloop.bash` と `bash -n .devcontainer/install_resoloop.bash` が成功することを確認する。SDK がない場合・一覧を取得できない場合・shim がない場合も、Step 1 のテストに含めて確認する。
- [ ] **Step 5: この Task の差分とテスト結果をレビューし、隔離ブランチが用意できていれば対象ファイルだけをコミットする。** `git diff --no-index /dev/null .devcontainer/install_resoloop.bash || test "$?" -eq 1` 等で確認し、`git add .devcontainer/install_resoloop.bash .devcontainer/test-install-resoloop.bash && git commit -m "Install or update the latest ResoLoop tool"`。

### Task 3: セットアップ接続・ヘッドレス確認・利用案内

**Files:**
- Modify: `.devcontainer/install_beforehand.bash`（apt 導入の直後で Task 2 を呼ぶ。`STEP_TOTAL` を更新）
- Modify: `.devcontainer/zshrc.txt`（PATH の既存ブロック）
- Create: `.devcontainer/verify-resonite-tooling.bash`
- Test: `.devcontainer/test-verify-resonite-tooling.bash`
- Modify: `.devcontainer/README.md`（利用者向けのセットアップ案内）

**Interfaces:**
- Consumes: Task 1 の .NET 10／Blender、Task 2 の `bash .devcontainer/install_resoloop.bash` とその終了コード。
- Produces: ResoLoop 導入とツール確認を必須の `postCreateCommand` 手順として実行し、必要な PATH を zsh およびエージェントに公開する。

- [ ] **Step 1: 先にセットアップ接続と異常系のテストを作る。** `.devcontainer/test-verify-resonite-tooling.bash` に、専用スクリプトを fake コマンドで動かす検証と、メインスクリプトの接続確認を置く。実際の apt やインストーラは実行しない。

```bash
#!/bin/bash
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
tmp="$(mktemp -d)"
trap 'rm -rf -- "$tmp"' EXIT
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
printf 'resoloop test-version\n'
MOCK
cat > "$tmp/bin/blender" <<'MOCK'
#!/bin/bash
case " $* " in *' --background '*' --python-expr '*) ;; *) exit 13 ;; esac
[ "${BLENDER_FAIL:-0}" = 0 ] || exit 14
MOCK
chmod +x "$tmp/bin/"*
export PATH="$tmp/bin:$PATH"
bash "$root/.devcontainer/verify-resonite-tooling.bash"
if RESOLOOP_FAIL=1 bash "$root/.devcontainer/verify-resonite-tooling.bash"; then exit 1; fi
if BLENDER_FAIL=1 bash "$root/.devcontainer/verify-resonite-tooling.bash"; then exit 1; fi
installer="$root/.devcontainer/install_beforehand.bash"
grep -qF 'bash .devcontainer/install_resoloop.bash' "$installer"
grep -qF 'bash .devcontainer/verify-resonite-tooling.bash' "$installer"
grep -qF 'readonly STEP_TOTAL=29' "$installer"
grep -qF 'PATH="$HOME/.dotnet/tools:$PATH"' "$root/.devcontainer/zshrc.txt"
printf 'PASS: toolchain smoke test and postCreate integration\n'
```

- [ ] **Step 2: RED を確認する。** `bash .devcontainer/test-verify-resonite-tooling.bash` を実行し、ツール確認用スクリプトと接続がないため非ゼロ終了することを確認する。
- [ ] **Step 3: ツール確認用スクリプトを作る。** .NET 10 と ResoLoop を確認し、Blender 組み込みの Python を使ってバックグラウンド実行を確認する。`--python-exit-code` でスクリプトの例外をエラーとして検知する。

```bash
#!/bin/bash
set -euo pipefail
if ! dotnet --list-sdks | grep -qE '^10\.'; then
    echo 'Toolchain verification: .NET 10 SDK is unavailable.' >&2
    exit 1
fi
if ! resoloop --version </dev/null; then
    echo 'Toolchain verification: resoloop cannot run.' >&2
    exit 1
fi
if ! blender --background --factory-startup --python-exit-code 1 \
    --python-expr 'import bpy; assert bpy.app.background' </dev/null; then
    echo 'Toolchain verification: Blender cannot run headlessly.' >&2
    exit 1
fi
```

- [ ] **Step 4: 既存の `postCreateCommand` 手順に接続する。** `STEP_TOTAL=29` に更新し、apt パッケージ導入後、次の 2 手順を追加する。PATH を現在の bash に通してから、導入と確認を行う。`.devcontainer/zshrc.txt` の既存 `~/.local/bin` 設定の下にも同様の PATH 行を追加する。

```bash
step "Installing or updating the latest ResoLoop tool"
export PATH="${HOME}/.dotnet/tools:${PATH}"
if ! bash .devcontainer/install_resoloop.bash; then
    fail "ResoLoop installation or update failed."
fi
step "Verifying the Resonite development toolchain"
if ! bash .devcontainer/verify-resonite-tooling.bash; then
    fail "Resonite development toolchain verification failed."
fi
```

```zsh
if [ -d "$HOME/.dotnet/tools" ] ; then
    PATH="$HOME/.dotnet/tools:$PATH"
fi
export PATH
```

- [ ] **Step 5: `.devcontainer/README.md` に利用案内を追記する。** 既存の案内を残し、次のセクションを追加する。利用者がこの段階の完了条件を誤解しないようにする。

```markdown
## Resonite ワールド開発ツール

Dev Container の作成時に .NET 10 SDK と Blender を導入し、ResoLoop を
プレビュー版を含む利用可能な最新版へインストールまたは更新します。
Blender は画面を開かずに実行します。Resonite 本体と ResoniteLink は
Windows ホスト側で準備してください。接続確認の `resoloop doctor`、
Blender の GUI、ホスト側のネットワーク設定はこのセットアップの対象外です。

導入を確認するにはコンテナ内で次を実行します。

    dotnet --list-sdks
    resoloop --version
    bash .devcontainer/verify-resonite-tooling.bash

ResoLoop の公式要件には Windows 10/11 が記載されています。Linux で
CLI が動作しない場合は `postCreateCommand` を失敗とし、成功扱いにはしません。
```
- [ ] **Step 6: GREEN、既存テスト、構文、実環境確認を行う。** `bash .devcontainer/test-verify-resonite-tooling.bash`、`bash .devcontainer/test-resonite-feature.bash`、`bash .devcontainer/test-install-resoloop.bash`、変更した各 Bash の `bash -n` と `.devcontainer/test-*.bash` を順に実行する。利用できれば Dev Container を再作成して `.devcontainer/verify-resonite-tooling.bash` を実行する。無い場合は Docker／Dev Container CLI 不在で再作成未実施と報告する。`./scripts/ci/verify-devenv.sh` が現れた場合は最終 Task で 1 回だけ実行し、存在しなければ欠落を報告する。
- [ ] **Step 7: この Task の差分とテスト結果をレビューし、隔離ブランチが用意できていれば対象ファイルだけをコミットする。** `git diff -- .devcontainer/install_beforehand.bash .devcontainer/zshrc.txt .devcontainer/README.md` 等を確認し、`git add .devcontainer/install_beforehand.bash .devcontainer/zshrc.txt .devcontainer/verify-resonite-tooling.bash .devcontainer/test-verify-resonite-tooling.bash .devcontainer/README.md && git commit -m "Verify Resonite tools during container setup"`。

## Contingency／判断記録

- 最初の RED で Feature の設定値、`dotnet tool list --global` の一覧形式、Blender の CLI 引数または終了コードが前提と異なる場合は、**目的と合格条件を維持する範囲で**テストと実装を最小限変更し、差異・理由・確認コマンドをここへ追記して続行する。Linux では CLI が実行できない、GUI やホスト接続が必要になる等、合格条件そのものを変える必要があればユーザーの判断を仰ぐ。
- `git remote -v` に `origin` がなく、この checkout は `main` のままである。設計書も未コミット。隔離 worktree と Task ごとのコミットを始める前に正しい対象リポジトリと基点を確定し、ユーザーの `.pi/APPEND_SYSTEM.md` の変更を保護する。正しい `origin/main` がない状態で別リポジトリを推測したり、`main` へ直接コミットしたりしない。
- コンテナの再作成に必要な Docker／Dev Container CLI が使えない場合は、モックテスト成功を実環境の動作保証に言い換えない。ResoLoop の Ubuntu 動作を確認できないことと、公式の Windows 10/11 前提を報告する。

## 全体レビューと引き渡し

各 Task のレビュー後、差分全体を設計書と照合する。ResoniteLink とホスト側の接続設定が増えていないこと、プレビューを含む最新版を選ぶこと、ユーザーの既存変更が含まれないことを確認する。検証に要した時間と Task ごとの所要時間、未実施の実環境確認と残るリスクを作業報告に記す。
