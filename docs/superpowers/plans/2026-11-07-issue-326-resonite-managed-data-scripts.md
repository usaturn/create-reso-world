# Issue #326 Resonite managed DLL の準備スクリプト 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

- 状態: draft（issue-to-pr の実行許可。内容の承認ではない）
- Spec: `docs/superpowers/specs/2026-11-07-issue-326-resonite-managed-data-scripts-design.md`
- Issue: https://github.com/usaturn/create-reso-world/issues/326

**Goal:** Windows でコピー元を確かめる PowerShell と、WSL で版ごとにコピーして SHA-256 で照合する Bash を `.devcontainer/` に足し、README の手作業を置き換える。

**Architecture:** 2 本は独立して手動で実行する。PowerShell は読むだけで、Bash に渡すコマンドを表示する。Bash は共有先の下に新しい版のフォルダを作り、コピー元の一覧を基準に照合し、全部通ったときだけ `SHA256SUMS` を置いて成功を表示する。

**Tech Stack:** bash 4+・GNU coreutils（`sha256sum`・`realpath`・`cp`・`find`）、Windows PowerShell 5.1 / PowerShell 7。

## Global Constraints

- 版は `^[0-9A-Za-z][0-9A-Za-z._+-]{0,63}$` だけを受け付ける
- 共有先は `$HOME/.local/share/create-reso-world/resonite-managed-data`。リンク・ファイルなら止まる
- 既存の版のフォルダ（リンク・壊れたリンクを含む）は上書き・削除しない。失敗時も版のフォルダを自動で消さない
- 設定ファイル・シェルの設定・`RESONITE_MANAGED_DATA_PATH`・Windows 側は変えない
- PowerShell のメッセージは ASCII（5.1 が BOM 無しの UTF-8 を誤読するため）
- DLL・ハッシュ一覧・生成物をリポジトリに入れない。CI は足さない

## 実行方式

`self`（雛形の既定）。Task は 2 つで、README は両スクリプトの引数・出力に依存し、同じ流れを逐次に変えるので `superpowers:executing-plans` で inline に実行する。ledger は `tmp/agents/issue-326.vpg05uso/sdd/2026-11-07-issue-326-resonite-managed-data-scripts/progress.md`。

## 受け入れ基準

（Spec の「受け入れ基準」と同じ）

- 動作環境: Bash は WSL2 の Linux（コンテナの外）の bash 4 以上と GNU coreutils。テストはこの Dev Container（Ubuntu 26.04）の bash で実行する。PowerShell は Windows 11 の Windows PowerShell 5.1 と PowerShell 7。このコンテナでは Linux 版の pwsh 7 で偽のインストール先に対して確かめ、Windows の実機・実 DLL では確かめない（未検証として報告する）
- 実入力: コピー元 `…/Program Files (x86)/Steam/steamapps/common/リゾナイト テスト/` のような空白・括弧・日本語を含むパス、版 `2025.11.3.1234` のような文字列、`FrooxEngine.dll` を含む複数の `*.dll`、DLL 以外のファイル、サブフォルダの DLL
- 防御範囲: 対象は、版の文字列による脱出（`../x`・`a/b`・`.`・`..`・空）、共有先の symlink、版のフォルダの既存（実ディレクトリ・symlink・壊れた symlink）、コピーの欠落・内容の不一致・コピー中のコピー元の変化、PowerShell の候補 0・複数。対象外は、`$HOME` や `~/.local` 自体が symlink である配置、スクリプトの実行中に他のプロセスが共有先を書き換える競合、Windows の実行ポリシー・署名、実 DLL での SDK の check/build

## 要件・検証の対応

| Spec の条件 | Task | 検証 |
| --- | --- | --- |
| D3 版の脱出・共有先 symlink・既存の版・壊れたリンクの拒否 | 1 | テスト (2)〜(5) |
| D3 欠落・不一致・コピー元の変化を成功と報告しない、版のフォルダを消さない | 1 | テスト (6) |
| D3 正常例（空白・括弧・日本語、直下の `*.dll` だけ、コピー元不変） | 1 | テスト (1) |
| D2 候補 0・複数で止まる、`'` を含むパスの引用 | 2 | 一時 pwsh での実行（コミットしない） |
| D5 README | 2 | `git diff` の確認、README のコマンドを偽の DLL で実行 |

## Task 1: Bash のコピー・照合スクリプトとテスト

**Files:**
- Create: `.devcontainer/test-copy-resonite-managed-data.bash`
- Create: `.devcontainer/copy-resonite-managed-data.bash`

**テストの要否:** 要。上書き防止・操作範囲・誤った成功報告は壊れてもエラーにならない S（AGENTS.md）。引数解析・ヘルプは L で書かない。

**Interfaces:**
- Produces: `bash .devcontainer/copy-resonite-managed-data.bash --source <dir> --version <ver>`。成功時は終了コード 0 と `copied and verified` を含む出力、引数の誤りは 2、それ以外の失敗は 1。失敗の出力に成功の文を含めない。版のフォルダを作った後の失敗では `left in place: <版のフォルダ>` を出す

- [ ] **Step 1:** テストを書く。`env HOME="$tmp/hN"` のワンショットで実行し、偽 DLL は実行時に作る。ケースは Spec D4 の (1)〜(6) と、コピー中にコピー元が変わる偽 `cp`
- [ ] **Step 2:** `bash .devcontainer/test-copy-resonite-managed-data.bash` が、スクリプトが無いことで FAIL することを確かめる
- [ ] **Step 3:** Spec D3 のとおりに実装する（EXIT の trap で一時ファイルを消し、版のフォルダを作った後に成功まで進まなければ残したパスと再試行前の確認を表示する）
- [ ] **Step 4:** テストが PASS し、`uv tool run --from shellcheck-py shellcheck` が 2 ファイルで警告を出さないことを確かめる
- [ ] **Step 5:** commit `feat: add script to copy and verify Resonite managed DLLs (#326)`

## Task 2: PowerShell のスクリプトと README

**Files:**
- Create: `.devcontainer/find-resonite-managed-data.ps1`
- Modify: `.devcontainer/README.md`（「Resonite の managed data（ProtoFlux、任意）」の手順 1・2 と、節の冒頭の説明）

**テストの要否:** PowerShell のテストはコミットしない（このコンテナと CI に pwsh が無く、常に skip するテストは守りにならない）。代わりに一時的に用意した pwsh 7 で、偽のインストール先（候補 1・2・0、`-ManagedPath`、空白・括弧・日本語・`'` を含むパス）に対して実行して確かめ、出力したコマンドを bash に渡してコピーが通ることを確かめる。README は F なのでテストしない

- [ ] **Step 1:** Spec D2 のとおりに実装する
- [ ] **Step 2:** `dotnet tool install PowerShell --tool-path <セッションディレクトリ>/pwsh` で pwsh を一時的に用意し、構文解析（`[System.Management.Automation.Language.Parser]::ParseFile`）と上のケースを実行する。用意できなければ構文検査を未実施として報告する
- [ ] **Step 3:** README の手順 1・2 を置き換える（Spec D5）
- [ ] **Step 4:** `bash .devcontainer/run-tests.bash`・`bash scripts/check-layout.sh` を実行する
- [ ] **Step 5:** commit `docs: document the managed data scripts in the devcontainer README (#326)`

## 実行予算

- 全体の能動時間の予算: 3 時間（Task 1: 60 分、Task 2: 60 分、検証・PR: 20 分、`--merge` のループ: サイクルの上限 3 ×（レビュー 45 分＋計画・修正 15 分）の範囲で、ループの期限に従う）
- 再試行の上限: 同じ検証の失敗は原因を変えた修正で 3 回まで。pwsh の導入の失敗は 1 回で打ち切り、構文検査を未実施として報告する
- checkpoint: Task 1 の commit の後、Task 2 の commit の後
- 縮小の候補: pwsh を用意できないとき、PowerShell の実行確認を省き、未検証として PR に書く

## contingency（代替策）

- `shellcheck-py` を取得できない: `bash -n` だけで代え、shellcheck を未実施と報告する
- pwsh を取得できない: 上の縮小の候補
- `sha256sum --strict` が無い環境だと分かった: `--strict` を外す（意味は同じ照合）。ledger に記録する
