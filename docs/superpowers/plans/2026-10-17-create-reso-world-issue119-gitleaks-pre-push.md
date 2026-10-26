# Issue #119 push の前の Gitleaks の検査 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 承認済みの版の Gitleaks を Dev Container に入れ、push の前に未 push の commit を base の設定で検査し、検査した SHA だけを push する。

**Architecture:** 導入は `.devcontainer/install_gitleaks.bash`（版と SHA-256 はここにだけ書く）、検査は `scripts/scan-before-push.sh`。検査は base の `.gitleaks.toml`（無ければ既定の規則）を一時ファイルで渡し、作業ツリー・環境変数・`.gitleaksignore`・inline の allow で緩められない形で `gitleaks git` を実行する。終了コードに加えて `ERR`・`FTL` の行でも失敗にする。

**Tech Stack:** bash（`set -euo pipefail`、既存のテストと同じ書き方）、git 2.55、Gitleaks 8.30.1、uv / PyYAML（CI 定義の検査）

**Spec:** `docs/superpowers/specs/2026-10-17-create-reso-world-issue119-gitleaks-pre-push-design.md`

## 管理・実行許可

- 文書管理・コード対象: `usaturn/create-reso-world`、Issue #119
- 基準 HEAD: `cd602e63e04e51616cd5043dd46b0cbefd8fc60e`（`origin/main`）
- 状態: completed
- 実行許可: 2026-10-17 21:11 JST、利用者の「#119 に着手せよ。専用 worktree を作成し、途中で止めずに推奨案で PR を出せ。」。推奨案での実装、commit、push、PR の作成まで。マージと rebuild は利用者が行う
- 実行方法: Native（このセッションでインライン実行）。実行方法を選んでもらう段は、止めずに進める指示に従って省いた。サブエージェントは利用者が求めていないので使わず、レビューは自己レビューと PR での利用者の確認で行う
- 作業場所: worktree `.worktrees/issue-119-gitleaks-pre-push`、ブランチ `feat/issue-119-gitleaks-pre-push`

## Global Constraints

- Gitleaks は 8.30.1、`gitleaks_8.30.1_linux_x64.tar.gz` の SHA-256 は `551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb`。値は `install_gitleaks.bash` にだけ書き、CI の `GITLEAKS_VERSION` とは `test-ci.bash` で比べる（Spec D-2）
- 追跡するファイルに、Gitleaks の規則に当たるトークンの形の文字列を書かない。テストの偽のトークンは実行時に作る（Spec D-10）
- `scripts/*.sh`・`.devcontainer/*.bash`・`tests/scripts/*.bash` は index で 100755（`tests/scripts/test-file-modes.bash`）
- 一時ディレクトリの削除は `rm -rf -- "${VAR:?}"` の形（`CLAUDE.md`）
- CI は作らない。private の create-reso-world の Actions は確かめない
- PR の本文は `Refs #119`（Spec D-12）

## Review Focus

- git の失敗で gitleaks が 0 で終わる（Spec F-6）→ Task 2 の壊れた object の場合で、終了コードが 0 以外・標準出力が空
- base に設定が無いリポジトリで、作業ツリーの `.gitleaks.toml` が読まれる（Spec F-2）→ Task 2 の「base に設定が無い」場合の全除外の `.gitleaks.toml`
- 検査の後に HEAD が変わって、検査していない commit を push する → 出力が検査の前に解決した HEAD の SHA であること（Task 2 の成功の場合で `git rev-parse HEAD` と比べる）。push の形は Task 3 の文書で SHA を使う
- 導入の確認に失敗したのに、既にある gitleaks を置き換えている → Task 1 の失敗の各場合で、既存の `~/.local/bin/gitleaks` のバイト列が変わらない
- 引数の誤り（`--base` に `/` が無い、remote が無い）を既定の値で続けてしまう → Task 2 の使い方の誤りの場合

---

### Task 1: Gitleaks の導入

**Files:**
- Create: `.devcontainer/install_gitleaks.bash`、`.devcontainer/test-install-gitleaks.bash`
- Modify: `.devcontainer/install_beforehand.bash`（`STEP_TOTAL` を 28 に、「Installing uv」の後にステップを足す）
- Modify: `.github/workflows/ci.yml`（`devcontainer-tests` に導入のステップ）
- Modify: `tests/scripts/test-ci.bash`（版の比較）

**テストの要否:** 必要。SHA-256 を確かめてから置くこと、失敗のときに既存のものを変えないことは、導入を実行して確かめる安全条件である。

**Interfaces:**
- Produces: `.devcontainer/install_gitleaks.bash` の 1 行 `readonly GITLEAKS_VERSION="8.30.1"`（Task 2 と `test-ci.bash` が読む）。実行すると `~/.local/bin/gitleaks` を置き、終了コード 0。失敗は `[install_gitleaks] ERROR: ...` を標準エラーに出して 1

- [ ] **Step 1: 失敗するテストを書く**

`.devcontainer/test-install-gitleaks.bash`。一時 `HOME`、`PATH="$tmp/bin:/usr/bin:/bin"`。偽の `curl` は `-o <path>` と URL を受け、URL を `$CALLS` に書き、`$FAKE_ARCHIVE` を `<path>` にコピーする（`FAIL_CURL=1` なら 22 で終わる）。fixture の tar.gz には、`version` で `$FAKE_VERSION` を出す偽の `gitleaks` だけを入れる。版は `install_gitleaks.bash` から `sed` で読み、テストに書かない。

1. 本物の `install_gitleaks.bash`（fixture と SHA-256 が合わない）: 失敗し、事前に置いた `~/.local/bin/gitleaks`（sentinel）のバイト列が変わらない
2. `GITLEAKS_ARCHIVE_SHA256` の行を fixture の SHA-256 に差し替えた写し: 成功し、置いた gitleaks が fixture と同じバイト列で mode 755、`$CALLS` の URL が `https://github.com/gitleaks/gitleaks/releases/download/v${ver}/gitleaks_${ver}_linux_x64.tar.gz`
3. 写しで `FAIL_CURL=1`: 失敗し、sentinel が変わらない
4. 写しで、fixture の gitleaks が別の版を出す: 失敗し、sentinel が変わらない

`tests/scripts/test-ci.bash` の Python に、`install_gitleaks.bash` の `readonly GITLEAKS_VERSION="..."` を正規表現で 1 件だけ読み、`leaks["env"]["GITLEAKS_VERSION"]` と等しいことを足す。

- [ ] **Step 2: 失敗を確かめる**

Run: `bash .devcontainer/run-tests.bash .devcontainer/test-install-gitleaks.bash tests/scripts/test-ci.bash`
Expected: 両方 FAIL（`install_gitleaks.bash` が無い）

- [ ] **Step 3: `install_gitleaks.bash` を書く**

一時ディレクトリに取得 → `sha256sum -c` → `tar -xzf <archive> -C <tmp> gitleaks` → 展開した gitleaks の `version` が `GITLEAKS_VERSION` と同じことを確かめる → `install -m 0755` で `~/.local/bin/gitleaks` に置く。置いた後に `gitleaks version` を表示する。`install_beforehand.bash` には `step "Installing the pinned Gitleaks"` で `bash .devcontainer/install_gitleaks.bash` を呼び、失敗は `fail "Gitleaks installation failed."`。`ci.yml` の `devcontainer-tests` には、テストの実行の前に `bash .devcontainer/install_gitleaks.bash` と `echo "$HOME/.local/bin" >> "$GITHUB_PATH"` を足す。

- [ ] **Step 4: 通ることを確かめる**

Run: `bash .devcontainer/run-tests.bash .devcontainer/test-install-gitleaks.bash tests/scripts/test-ci.bash .devcontainer/test-install-beforehand.bash`
Expected: PASS 3 本

- [ ] **Step 5: 今のコンテナに導入する**

Run: `bash .devcontainer/install_gitleaks.bash && command -v gitleaks && gitleaks version`
Expected: `~/.local/bin/gitleaks`、`8.30.1`

- [ ] **Step 6: Commit**

```bash
git add .devcontainer/install_gitleaks.bash .devcontainer/test-install-gitleaks.bash .devcontainer/install_beforehand.bash .github/workflows/ci.yml tests/scripts/test-ci.bash
git commit -m "feat(devcontainer): install the pinned Gitleaks (#119)"
```

### Task 2: push の前の検査

**Files:**
- Create: `scripts/scan-before-push.sh`、`tests/scripts/test-scan-before-push.bash`

**テストの要否:** 必要。検出・緩められないこと・失敗を成功にしないことを、実際の gitleaks で一時リポジトリを検査して確かめる（Issue の「検証」）。

**Interfaces:**
- Consumes: Task 1 の `readonly GITLEAKS_VERSION="..."` の行
- Produces: `bash scripts/scan-before-push.sh [-C <dir>] [--base <remote>/<branch>]`。成功: 終了コード 0、標準出力は検査した HEAD の SHA の 1 行だけ。失敗: 0 以外、標準出力は空。ログはすべて標準エラー。使い方の誤りは 2

- [ ] **Step 1: 失敗するテストを書く**

`tests/scripts/test-scan-before-push.bash`。`GIT_CONFIG_GLOBAL=/dev/null`・`GIT_CONFIG_NOSYSTEM=1` と author / committer を固定する。gitleaks が PATH に無ければ、`bash .devcontainer/install_gitleaks.bash` を案内して失敗する。偽のトークンは `ghp_` と、固定の種の `sha256sum` の先頭 36 文字を実行時につないで作る。各場合は bare の origin を持つ新しい一時リポジトリで作り、`main` を push してから feature branch で commit する。`run_scan` は標準出力と標準エラーを別のファイルに取る。

検出して失敗し、標準出力が空:
- `leak_commit`: 通常の commit にトークン
- `leak_in_merge`: 両方の親に無いファイルを、`git merge --no-ff --no-commit` の後に足してマージ commit にする
- `leak_with_inline_allow`: トークンの行に `# gitleaks:allow`
- `worktree_config_cannot_relax`: base の `.gitleaks.toml`（`useDefault = true` だけ）がある状態で、branch に全パスを除外する `.gitleaks.toml` を commit し、さらに `GITLEAKS_CONFIG`（全除外のファイル）と `GITLEAKS_CONFIG_TOML`（全除外の内容）を渡す
- `no_base_config_cannot_relax`: base に `.gitleaks.toml` が無い状態で、同じ全除外の `.gitleaks.toml` を作業ツリーに置く（未追跡）

止まって失敗し、標準出力が空:
- `gitleaksignore_stops`: 秘密情報の無い commit で、ルートに `.gitleaksignore`（空）
- `broken_base_config`: base の `.gitleaks.toml` が TOML として壊れている
- `corrupt_object`: 範囲内の commit の blob の object ファイルを空にする（gitleaks は 0 で終わる。Spec F-6）
- `missing_base`: `--base origin/nope`、`--base nope/main`、`--base main`（使い方の誤りで 2）
- `wrong_version`: `version` で別の版を出す偽の gitleaks を PATH の先頭に置く
- `gitleaks_fails`: `version` は正しい版を出し、`git` では 3 で終わる偽の gitleaks

成功し、標準出力が `git -C <repo> rev-parse HEAD` と同じ 1 行:
- `clean_commits`: 秘密情報の無い通常の commit とマージ commit
- `base_config_is_used`: base の `.gitleaks.toml` に、そのトークンだけを `regexTarget = "secret"` で除外する allowlist を置き、同じトークンを commit する
- `subdirectory_with_C`: `-C <repo>/sub` で、ルートの検査として成功する

- [ ] **Step 2: 失敗を確かめる**

Run: `bash .devcontainer/run-tests.bash tests/scripts/test-scan-before-push.bash`
Expected: FAIL（`scripts/scan-before-push.sh` が無い）

- [ ] **Step 3: `scripts/scan-before-push.sh` を書く**

順に: 引数の解析 → `GITLEAKS_*` をすべて unset → gitleaks の有無と版（スクリプトの checkout の `.devcontainer/install_gitleaks.bash` から読む）→ `git -C <dir> rev-parse --show-toplevel` に移る → `.gitleaksignore`（`-e` か `-L`）で停止 → `git remote get-url <remote>` → `git fetch --no-tags <remote> +refs/heads/<branch>:refs/remotes/<remote>/<branch>` → base と HEAD を `rev-parse --verify '<ref>^{commit}'` → `git ls-tree --name-only <base> -- .gitleaks.toml` が失敗なら停止、空なら `[extend]\nuseDefault = true` を、そうでなければ `git show <base>:.gitleaks.toml` を一時ファイルに書く → 次を実行し、出力を標準エラーに流しながらファイルにも取る:

```bash
gitleaks git --no-banner --no-color --redact --verbose --ignore-gitleaks-allow \
  --config "$scan_dir/config.toml" --gitleaks-ignore-path "$scan_dir/ignore" \
  --log-opts="--diff-merges=separate $base_sha..$head_sha" .
```

終了コードが 0 以外、または出力に `^[^ ]+ (ERR|FTL) ` の行があれば失敗。成功なら `$head_sha` を出す。メッセージの接頭辞は `scan-before-push:`。

- [ ] **Step 4: 通ることを確かめる**

Run: `bash .devcontainer/run-tests.bash tests/scripts/test-scan-before-push.bash tests/scripts/test-file-modes.bash`
Expected: PASS 2 本

- [ ] **Step 5: Commit**

```bash
git add scripts/scan-before-push.sh tests/scripts/test-scan-before-push.bash
git commit -m "feat(scripts): scan unpushed commits with Gitleaks before push (#119)"
```

### Task 3: 規則・スキル・手順書

**Files:**
- Modify: `AGENTS.md`（「リポジトリ境界」の後に「push の前の秘密情報の検査」の節）
- Modify: `.agents/skills/review-fix-planning/SKILL.md`（「実装後」手順 5、結論 2 の手順 6、例の 2 か所）
- Modify: `docs/resoloop-fork-workflow.md`（手順 5）、`docs/resoloop-meshy-workflow.md`（手順 5）
- Modify: `.devcontainer/README.md`（導入ツール一覧、「テストの実行」の gitleaks の段落）

**テストの要否:** 不要。文書・SKILL.md の文面だけの変更で、コードを実行して確かめる挙動が無い（`AGENTS.md` の「テストの採用基準」）。代わりに Step 2 の検証を行う。

- [ ] **Step 1: 書く**

Spec D-7・D-8 のとおり。push の形は D-7 のブロック。`review-fix-planning` は `--base "$PR_REMOTE/<PR の base>"`、`git -C "$MAIN_ROOT" push "$HEAD_REMOTE" "$SHA:refs/heads/$HEAD_BRANCH"`、スクリプトは `"$TOPLEVEL/scripts/scan-before-push.sh" -C "$MAIN_ROOT"`。README の表の Gitleaks の行は mount・initialize・zshrc・update の列を `—` にする。

- [ ] **Step 2: 検証する**

Run: `rg -n 'push "\$HEAD_REMOTE" HEAD|push -u origin' AGENTS.md .agents docs/resoloop-fork-workflow.md docs/resoloop-meshy-workflow.md`
Expected: 出力なし

Run: `bash .devcontainer/run-tests.bash && bash scripts/check-layout.sh && uv run pytest tests/skills .agents/skills`
Expected: すべて PASS（check-layout の環境要因の失敗は、`main` でも同じかを確かめて報告する）

- [ ] **Step 3: Commit**

```bash
git add AGENTS.md .agents/skills/review-fix-planning/SKILL.md docs/resoloop-fork-workflow.md docs/resoloop-meshy-workflow.md .devcontainer/README.md
git commit -m "docs: require the Gitleaks scan before every push (#119)"
```

### Task 4: 実環境での確認と PR

- [ ] **Step 1: 3 つのリポジトリで検査する**

Run: `bash scripts/scan-before-push.sh`（この worktree）、`bash scripts/scan-before-push.sh -C <PARENT_ROOT>/external/resoloop`、`bash scripts/scan-before-push.sh -C <PARENT_ROOT>/external/resoloop-meshy`
Expected: どれも終了コード 0 で SHA を 1 行出す。resoloop・resoloop-meshy では既定の規則を使った旨を表示する

- [ ] **Step 2: 実行記録を書いて commit する**

検証の結果と所要時間を Plan の末尾の「実行記録」に書く。状態は draft のままにする（completed は、マージと rebuild の後の確認の後で別に記録する）。

- [ ] **Step 3: 検査付きで push して PR を作る**

`SHA="$(bash scripts/scan-before-push.sh)" && [ -n "$SHA" ] && git push origin "$SHA:refs/heads/feat/issue-119-gitleaks-pre-push"`。PR の本文に `Refs #119`、検証の結果、移植元との違い（Spec D-11）、利用者に頼むこと（rebuild の後の `gitleaks version` と、3 つのリポジトリの worktree での検査）を書く

## 実行記録

2026-10-17 JST に、このセッションで Native 実行した。状態は draft のまま（Task 4 Step 2）。

- 所要時間: 21:11（worktree の作成）〜 22:00 頃（PR の作成）の約 50 分。内訳は、調査・gitleaks の実測・Spec 11 分、Plan 1 分、Task 1 3 分、Task 2 5 分、Task 3 8 分（スキルの pytest の 3 分を含む）、Task 4 と最終の自己レビュー・修正・再検証 約 20 分
- commit: Spec `66e904c`、Plan `f9a4761`、Task 1 `457912d`、Task 2 `adac95d`、Task 3 `366a1b4`、自己レビューの修正はこの記録と同じ commit
- テストの検出力: 導入の 4 か所と検査の 15 か所の防御を 1 つずつ外して、テストが失敗することを確かめた。外しても失敗しないのは、`GITLEAKS_*` の unset（`--config` が `GITLEAKS_CONFIG`・`GITLEAKS_CONFIG_TOML` より優先される）と `--no-ext-diff`（`git log -p` は `--ext-diff` が無いと外部 diff を使わない）の 2 つで、どちらも Spec D-5 の念押しとして残した
- 今のコンテナへの導入: `bash .devcontainer/install_gitleaks.bash` が release から取得し、SHA-256 を確かめて `~/.local/bin/gitleaks`（8.30.1）に置いた
- 実環境での検査: この worktree（5 commit、検出なし）。usaturn/resoloop・usaturn/resoloop-meshy は、このセッションの隔離で worktree の外の checkout（`external/`）に git を実行できないため、GitHub から worktree の `tmp/` に浅く clone して試した。どちらも base に `.gitleaks.toml` が無く既定の規則で検査し、未 push の commit が無いとき・秘密情報の無い commit とマージ commit では HEAD の SHA を出し、偽のトークンの commit では終了コード 1・標準出力は空で止まった。`external/` の checkout と、作り直した Dev Container での確認は利用者に頼む
- 最終の自己レビュー（サブエージェントは使っていない）: 利用者の git の設定（`color.ui=always`）と、branch で足した `.gitattributes`（`* -diff`）、textconv で、gitleaks が終了コード 0 のまま見逃すことを見つけた（Spec F-11）。テストを足して RED を確かめてから、`--no-color --no-ext-diff --no-textconv` と `GIT_ATTR_SOURCE=<base>` で直した
- 範囲外の発見: `gitleaks dir` で作業ツリーを走査すると、`main` にある `tests/scripts/test_meshy.py:20`（テスト用の偽の値 `KEY`）が generic-api-key に当たる。push 済みの履歴なので、この検査（未 push の commit だけ）では止まらない。履歴の全体を走査するときにどう扱われるかは確かめていない

## マージ後の完了記録（2026-10-26 UTC）

### 実行許可と完了の範囲

- PR #133 は `8c4463714677685c3dad1921e59c0c8719716aa4` でマージ済み。
- 利用者は残っていた環境確認・文書更新・Issue close の一覧を受けて「残作業を実行してください。」と指示した。今回の継続作業はこの実行許可に基づく。状態の `completed` は実装と残っていた環境確認の完了を表し、`approved` への変更でも、新しい設計承認の推定でもない。
- 当初の rebuild 後の確認に代えて、Issue コメントで明示的に許可された `bash .devcontainer/install_gitleaks.bash` を現在の Dev Container で実行する方法を採用した。以下は controller が実行した記録であり、文書担当はログを確認した。rebuild・bootstrap を試したとは扱わない。

### 現在の Dev Container への導入

- 実行: `bash /workspaces/reso-world/.devcontainer/install_gitleaks.bash`（終了コード 0）。release archive `gitleaks_8.30.1_linux_x64.tar.gz` を取得し、installer に固定された SHA-256 の検証を通して `/home/vscode/.local/bin/gitleaks` に導入した。
- 実行: `gitleaks version`（終了コード 0、標準出力 `8.30.1`）。既存バイナリの版を推測したのではなく、導入後の実測である。

### 3 リポジトリの実 worktree での検査

既存の `origin/main` の履歴から選んだ linked worktree を対象に、`bash /workspaces/reso-world/scripts/scan-before-push.sh -C <対象 worktree>` を実行した。resoloop にのみ `--base upstream/main` を付け、ほかは既定の `origin/main` を使った。3 件とも終了コード 0、標準出力は表の HEAD SHA だけの 1 行で、対象の作業ツリーは clean だった。

| リポジトリ・対象 worktree（絶対パス） | HEAD SHA | base ref / SHA | 検査範囲 |
| --- | --- | --- | --- |
| create-reso-world: `/workspaces/reso-world/.worktrees/issue-119-post-merge` | `ac01ef40a503ab709d19eb1d8d881e936f787467` | `origin/main` / `ac01ef40a503ab709d19eb1d8d881e936f787467` | `ac01ef40a503ab709d19eb1d8d881e936f787467..ac01ef40a503ab709d19eb1d8d881e936f787467` |
| resoloop: `/workspaces/reso-world/external/resoloop/.worktrees/issue-119-post-merge` | `ff77b91d1f17c7dba861416d82f1a6c8929f2805` | `upstream/main` / `a7be2dd4a5e4df9f152c8908e51a853d3af6bb74` | `a7be2dd4a5e4df9f152c8908e51a853d3af6bb74..ff77b91d1f17c7dba861416d82f1a6c8929f2805` |
| resoloop-meshy: `/workspaces/reso-world/external/resoloop-meshy/.worktrees/issue-119-post-merge` | `1b64663595e5cc024dad08acec0cfff5416e1a95` | `origin/main` / `1b64663595e5cc024dad08acec0cfff5416e1a95` | `1b64663595e5cc024dad08acec0cfff5416e1a95..1b64663595e5cc024dad08acec0cfff5416e1a95` |

resoloop・resoloop-meshy は base に `.gitleaks.toml` が無く、既定の規則を使った旨を標準エラーに表示した。3 件とも Gitleaks の実測は `0 commits scanned`・`0 bytes`。resoloop の範囲は `rev-list` ではマージ commit 1 件だが、Gitleaks が 1 件分の差分を走査したとは報告しない。これらは実際の配置・base 選択・終了コード・SHA 出力を確かめた運用経路の確認であり、外部リポジトリの空でない差分に対する新しい検出テストではない。検出動作は別途、既存の `tests/scripts/test-scan-before-push.bash` を実行して確認した。

### 回帰確認と証跡

- 初回の `bash .devcontainer/run-tests.bash .devcontainer/test-install-gitleaks.bash tests/scripts/test-scan-before-push.bash tests/scripts/test-ci.bash` は終了コード 1。導入と scanner の 2 suite は PASS で、唯一の失敗は `tests/scripts/test-ci.bash: No such file or directory`。同ファイルは #235（`da5ee518a56f8bf6bc387b38eb33b1b5b6b5b82c`）で意図して削除済みであり、古い検証対象の指定を訂正した。初回成功とも、今回の実装による回帰とも扱わない。
- 訂正後の現行 Bash suite は `PASS: 23 test(s)`、標準エラーは空。既存の導入・scanner の suite を含む。layout 検査は `PASS: check-layout`。これは controller 提供の現時点の baseline であり、この文書 commit 後の全体検証や、今後の pytest の成功を先取りした記録ではない。
- 証跡ディレクトリ: `/workspaces/reso-world/tmp/agents/issue-119-post-merge.fuw652fp/`。実行 argv・cwd・終了コード・完了時刻・所要秒数・HEAD/base は同ディレクトリの `environment-checks.json`、標準出力・標準エラーは下表に記録されている（ローカルの証跡で、リポジトリには含めない）。

| 確認 | 上記ディレクトリ内のログ |
| --- | --- |
| 実導入 | `install-gitleaks.stdout.log` / `install-gitleaks.stderr.log` |
| 実測の版 | `gitleaks-version.stdout.log` / `gitleaks-version.stderr.log` |
| create-reso-world | `scan-create-reso-world.stdout.log` / `scan-create-reso-world.stderr.log` |
| resoloop | `scan-resoloop.stdout.log` / `scan-resoloop.stderr.log` |
| resoloop-meshy | `scan-resoloop-meshy.stdout.log` / `scan-resoloop-meshy.stderr.log` |
| 初回の古い対象指定 | `baseline-gitleaks.stdout.log` / `baseline-gitleaks.stderr.log` |
| 訂正後の 23 Bash suite | `baseline-current.stdout.log` / `baseline-current.stderr.log` |
| layout | `baseline-layout.log` |

### 文書更新と残る公開手順

ソース・設定・トークンの fixture・外部リポジトリのコードは変更せず、秘密情報・資格情報の値や検査の回避・除外設定も追加していない。文書の固定値の記録は F に当たるため新しい恒久テストは作らず、変更 Markdown・参照先・`git diff --check` を確認する。過去の実行記録と Task のチェックボックスはこの追記では変更しない。

この文書更新はローカル commit の段階で、公開未実施。controller がレビュー後のチェックボックス更新・現行の全体検証・完了記録の PR 作成と利用者指定の `--merge` ループ・Issue #119 の更新と close を担当する。これらの完了や、新しい PR URL はこの記録では主張しない。
