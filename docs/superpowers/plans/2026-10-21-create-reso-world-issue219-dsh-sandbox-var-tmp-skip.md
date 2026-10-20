# Issue #219: DSH の attempt の中で test_sandbox.py の 5 件を理由付きで skip する Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `tools/agent_runner/tests/adapters/dsh/test_sandbox.py` の `/var/tmp` を使う 5 件が、`/var/tmp` に作業領域を作れない環境（DSH の attempt）では理由付きで skip され、ホストでは今どおり実行されて通るようにする。

**Architecture:** 3 か所の `with tempfile.TemporaryDirectory(dir="/var/tmp")` を、function scope の fixture `root` 1 つにまとめる。fixture は作業領域の作成だけを `try` で囲み、`OSError` なら `pytest.skip` する。テストの本体と adapter の本体は変えない。

**Tech Stack:** Python 3.14、pytest 9.1.1、bubblewrap 0.11.1

**Spec:** `docs/superpowers/specs/2026-10-21-create-reso-world-issue219-dsh-sandbox-var-tmp-skip-design.md`

## 管理

- 状態: draft
- 対象 Issue: https://github.com/usaturn/create-reso-world/issues/219
- DOC_ROOT・CODE_ROOT: `/workspaces/reso-world/.worktrees/issue-219-dsh-sandbox-var-tmp-skip`（branch `fix/issue-219-dsh-sandbox-var-tmp-skip`）。PARENT_ROOT: `/workspaces/reso-world`
- 実行許可: Spec の「管理・実行許可」と同じ（`/issue-to-pr … --merge --assign implement=self`。PR の作成後に PR 修正ループを回し、修正不要ならループの `finalize.py` がマージする）
- 実行方式: inline（`superpowers:executing-plans`）。`implement_task.py check` の `self` が true で、変えるのは 1 ファイルの 1 Task。委譲しても並行できず、文脈を渡す手間が上回る
- 検証のログ: `/workspaces/reso-world/tmp/agents/issue-219.f0wvtucb/`（commit しない）
- `/tmp` の下の検証用 worktree: `/tmp/issue-219-repro.Nr5wNG/wt`（`git worktree add --detach` で作った使い捨て。自前の `.venv` は `uv sync --locked` で作った。Task 2 の最後に `git worktree remove` で外す）

## Global Constraints

- 変えるのは `tools/agent_runner/tests/adapters/dsh/test_sandbox.py` だけ（Spec の設計 2）
- skip するのは `tempfile.TemporaryDirectory(prefix="dsh-sandbox-test-", dir="/var/tmp")` の作成の `OSError` だけ（Spec の受け入れ条件 3）
- テストを足さない（Spec の D-219-4）
- fixture の名前は `root`、scope は function。skip の理由は英語で、`/var/tmp` と例外の文を含める
- mount の形は Spec の「確認した事実」の 2 つ（DSH の形・Issue の形）をそのまま使う

## Review Focus

- 作成の後の失敗（`make_paths`・`invoke`・assert）が skip に変わらず、失敗のまま残ること → Task 2 の Step 7（`dsh_sandbox.py` をわざと壊した対照検証）
- ホストでは 5 件が skip されないこと（`/tmp` の下の checkout を含む）→ Task 2 の Step 2〜4（`-rs` で skipped 0）
- 作業領域が fixture の teardown で消え、`/var/tmp/dsh-sandbox-test-*` が残らないこと → Task 2 の Step 2（実行の前後で数える）
- skip の理由に `/var/tmp` と例外の文（`Read-only file system`）が出ること → Task 2 の Step 5・6
- パラメータ化したテストの 3 件が、それぞれ新しい作業領域を受け取って実行されること → Task 1 の Step 4 と Task 2 の Step 2〜4（6 passed）

## 要件と Task・検証の対応

| Spec の受け入れ条件 | 担当 Task | 観測する結果 | 検証方法 |
| --- | --- | --- | --- |
| 1. ホスト（`/workspaces`・`/tmp` の下）で 5 件が skip されずに通る | Task 1（統合は Task 2） | `tools/agent_runner/tests/adapters/dsh` が 0 failed・0 skipped | Task 2 の Step 2〜4 |
| 2. DSH と同じ形の mount の中で、5 件が理由付きで skip され、失敗しない | Task 1（統合は Task 2） | `test_sandbox.py` が 1 passed・5 skipped・0 failed。理由に `/var/tmp`・`Read-only file system` | Task 2 の Step 5・6 |
| 3. skip は作れないときだけで、作れた後の失敗は失敗のまま | Task 1 | `try` が作業領域の作成だけを囲む。`dsh_sandbox.py` を壊すとホストで failed になる | Task 2 の Step 7 と `git diff` |
| 4. adapter の本体と DSH の grant は変えない | Task 2 | 差分が `test_sandbox.py` と Spec・Plan だけ | Task 2 の Step 8（`git diff --stat origin/main`） |
| 5. DSH のテストと README の入口で、この変更による失敗が無い | Task 2 | 各入口の終了コード。失敗があれば基準（`5a6b096`）の同じ実行と比べる | Task 2 の Step 4・Step 12 |

共有する前提: 5 件はどれも同じ fixture `root` に頼り、変更は 1 ファイルなので、Task の間で共有する入力・状態は無い。ホストと mount の両方の環境での確認は、統合担当の Task 2 で行う。

## 実行予算

- Issue 全体の能動時間の予算: 240 分（ledger: `/workspaces/reso-world/tmp/agents/issue-219.f0wvtucb/budget.jsonl`）。根拠は #198（同じ種類のテストの前提の修正、240 分の予算で Plan の Step 7 まで約 31 分）。目安は準備・再現 15 分、Spec・Plan 20 分、Task 1 10 分、Task 2 40 分（テストの実行の待ちと最終レビューが大半）、PR 10 分、PR 修正ループは最大 3 サイクル ×（レビューの期限 45 分＋計画・修正 15 分）＝ 180 分のうちの残り。ループが 1 サイクルで修正不要なら合計 2 時間ほど
- worker は使わない（inline）。長時間の実行（`run-tests.bash`・pytest 全体）はバックグラウンドで実行し、終了コードで確かめる。1 回の期限は 30 分。負荷で時間切れのテストが出ないよう、README の入口は並行させず順に実行する
- 再試行の上限: 同じ signature の信頼性の失敗（テストの時間切れ・環境の I/O の停止）は 1 回まで。安全の失敗（実リポジトリ・親の `.venv` の書き換えの疑い、想定外の外部送信）は再試行せず止まる
- checkpoint: Task 1 の後、Task 2 の後、ループの各サイクルの後、予算の 50%・100%
- 縮小・方法変更の候補: README の入口が環境の要因で落ちたら、基準（`5a6b096`）の同じ実行と比べて差分だけを判定する。DSH の形の mount で検証の形に由来する失敗（Spec の「確認した事実」の PID の件）が出たら、Issue の形の mount の結果で判定する。`/tmp` の worktree が使えなければ、`/tmp` の下の使い捨ての clone で代える

## Task 1: `/var/tmp` の作業領域を fixture にし、作れないときは skip する

**Files:**
- Modify: `tools/agent_runner/tests/adapters/dsh/test_sandbox.py:3-9`（import）、`:81-115`（3 つのテスト）

**Interfaces:**
- Produces: fixture `root() -> Iterator[Path]`（function scope）。`/var/tmp` の下に作った空のディレクトリを渡し、テストの後に消す。作れなければ skip する

**テストの要否:** 既存のテストの前提を直す変更で、新しいテストは書かない（D-219-4）。修正の前の失敗は Spec の「確認した事実」で再現済み。

- [ ] **Step 1:** `from pathlib import Path` の前に `from collections.abc import Iterator` を足す
- [ ] **Step 2:** `make_paths` の後、`test_missing_bwrap_never_executes_command` の前に fixture を置く。82 行のコメントはここへ移す

```python
@pytest.fixture
def root() -> Iterator[Path]:
    # /var/tmp remains visible read-only; bwrap's per-call /tmp is ephemeral. A DSH
    # attempt mounts / read-only, so there the directory cannot be created at all.
    try:
        directory = tempfile.TemporaryDirectory(prefix="dsh-sandbox-test-", dir="/var/tmp")
    except OSError as error:
        pytest.skip(f"cannot create the host-visible directory under /var/tmp: {error}")
    with directory as path:
        yield Path(path)
```

- [ ] **Step 3:** 3 つのテストに引数 `root: Path` を足し（パラメータ化したものは `(case: str, root: Path)`）、`with tempfile.TemporaryDirectory(...) as directory:` と `root = Path(directory)` の 2 行を消して本体の字下げを 1 段戻す。本体の行（`make_paths`・`invoke`・assert）は変えない
- [ ] **Step 4:** feature worktree で `uv run pytest tools/agent_runner/tests/adapters/dsh/test_sandbox.py -q -rs`。期待: `6 passed`、`SKIPPED` の行が無い
- [ ] **Step 5:** commit（`fix(agent_runner): skip the dsh sandbox tests when /var/tmp cannot be written (#219)`）

## Task 2: 統合確認

**テストの要否:** 確認だけで、コードを変えない（Step 7 の一時的な変更は使い捨ての worktree だけで行い、戻す）。

ログはどれも `/workspaces/reso-world/tmp/agents/issue-219.f0wvtucb/` に置く。`WT2=/tmp/issue-219-repro.Nr5wNG/wt`、`DSH_DIR=tools/agent_runner/tests/adapters/dsh`、`T=$DSH_DIR/test_sandbox.py`。mount の中の Python は `env PYTHONDONTWRITEBYTECODE=1 "$WT2/.venv/bin/python" -m pytest`。

- [ ] **Step 1:** `git -C "$WT2" checkout --detach <Task 1 の SHA>`、`git -C "$WT2" status --porcelain` が空
- [ ] **Step 2:** ホスト・`/tmp` の worktree・自前の `.venv`: `ls -d /var/tmp/dsh-sandbox-test-* 2>/dev/null | wc -l` を数え、`$DSH_DIR` を `-q -rs` で実行し、もう一度数える。期待: 0 failed・0 skipped、前後の数が同じ
- [ ] **Step 3:** ホスト・`/tmp` の worktree・pr-review と同じ使い方: `cd "$WT2" && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$WT2" uv run --project /workspaces/reso-world --locked python -m pytest "$DSH_DIR" -q -rs`。期待: 0 failed・0 skipped
- [ ] **Step 4:** ホスト・feature worktree（`/workspaces` の下）: `uv run pytest "$DSH_DIR" -q -rs`。期待: 0 failed・0 skipped
- [ ] **Step 5:** DSH の形の mount（`bwrap --ro-bind / / --dev /dev --unshare-pid --proc /proc --die-with-parent --cap-drop ALL --tmpfs /tmp --bind "$WT2" "$WT2" --chdir "$WT2" --`）で `$T` を `-q -rs`。期待: 1 passed・5 skipped・0 failed、5 件の理由に `/var/tmp` と `Read-only file system`
- [ ] **Step 6:** Issue の形の mount（`bwrap --ro-bind / / --dev /dev --proc /proc --tmpfs /tmp --bind "$WT2" "$WT2" --chdir "$WT2" --`）で `$T` と `$DSH_DIR` を `-q -rfEs`。期待: `$T` は Step 5 と同じ。`$DSH_DIR` は 278 passed・5 skipped・0 failed（基準は 5 failed・278 passed）
- [ ] **Step 7:** 対照検証: `$WT2` の `tools/agent_runner/dsh_sandbox.py` の `mounts` の writable 側から `*additions` を外し（grant を mount しない）、ホストで `$T` を `-q -rs`。期待: `test_explicit_grants_preserve_neighboring_host_files` が failed（skipped ではない）。`git -C "$WT2" checkout -- tools/agent_runner/dsh_sandbox.py` で戻し、`git -C "$WT2" status --porcelain` が空
- [ ] **Step 8:** feature worktree で `git diff --stat origin/main` が、`test_sandbox.py` と Spec・Plan だけであること
- [ ] **Step 9:** ブランチ全体のレビュー（新しいコンテキストのサブエージェント）を受け、致命的な指摘があれば直す（直したら Step 1〜8 をやり直す）
- [ ] **Step 10:** `/tmp` の検証用 worktree を `git -C /workspaces/reso-world worktree remove "$WT2"` で外し、`/tmp/issue-219-repro.Nr5wNG` を `rmdir` で消す
- [ ] **Step 11:** Step 1〜9 の記録をこの Plan の「検証の記録」に書き、commit（これが最後の commit）
- [ ] **Step 12:** 最後の commit の上で `git status --porcelain` が空であることを確かめてから、README の「テスト」の入口（`bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`uv run pytest tests/skills .agents/skills .agents/scripts tools`）を順に実行する。失敗があれば、基準（`5a6b096`）の同じ実行と比べ、この変更によるものでないことを確かめる。検証した HEAD・`git status --porcelain` が空だったこと・argv・終了コード・ログのパスと、`finalize.py` の `--checks-file` の形のファイルをログの置き場所に作る（issue-to-pr の 5 章）。結果は Plan に書かず（HEAD が変わるので）、PR 本文に書く

## 検証の記録

（Task 2 の Step 11 で書く）
