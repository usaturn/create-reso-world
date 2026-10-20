# Issue #198: DSH の adapter のテストを checkout の場所に依らず通す Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `tools/agent_runner/tests/adapters/dsh/test_adapter.py` の 2 件が、checkout が `/tmp` の下でも `/workspaces` の下でも、skip されずに通るようにする。

**Architecture:** 1 件目は担当のコマンドを実体の interpreter（`Path(sys.executable).resolve()`）にする。2 件目は `parent_review` fixture が `.agents/scripts/review_target.py` を attempt に写して依頼のパラメータ `probe_helper` で渡し、`fake_cli.py` はそれを読む。adapter の本体は変えない。

**Tech Stack:** Python 3.14、pytest、bubblewrap

**Spec:** `docs/superpowers/specs/2026-10-20-create-reso-world-issue198-dsh-test-tmp-checkout-design.md`

## 管理

- 状態: draft
- 対象 Issue: https://github.com/usaturn/create-reso-world/issues/198
- DOC_ROOT・CODE_ROOT: `/workspaces/reso-world/.worktrees/issue-198-dsh-test-tmp-checkout`（branch `fix/issue-198-dsh-test-tmp-checkout`）。PARENT_ROOT: `/workspaces/reso-world`
- 実行許可: Spec の「管理・実行許可」と同じ（`/issue-to-pr #198 --merge`。PR の作成後に PR 修正ループを回し、修正不要ならループの `finalize.py` がマージする）
- 実行方式: inline（`superpowers:executing-plans`）。`implement_task.py check` の `self` が true で、2 つの Task が同じテストファイルを順に変えるので、委譲しても並行できず、文脈を渡す手間が上回る
- 検証のログ: `/workspaces/reso-world/tmp/agents/issue-198.f428uvx6/`（commit しない）
- `/tmp` の下の検証用 worktree: `/tmp/issue-198-repro.PrSkoY/wt`（`git worktree add --detach` で作った使い捨て。検証が済んだら `git worktree remove` で外す）

## Global Constraints

- 変えるのは `tools/agent_runner/tests/adapters/dsh/test_adapter.py` と `tools/agent_runner/tests/adapters/dsh/fake_cli.py` だけ（Spec の 3）
- skip を使わない（受け入れ条件 3）
- テストを足さない（Spec の D-198-4）
- 依頼のパラメータの名前は `probe_helper`、helper の写しの置き場所は `context.receipt_path.parent / "review_target.py"`

## Review Focus

- 1 件目: 実体の interpreter で起動しても、`/tmp` の下の起動スクリプトと `sys.prefix` の共有の環境が見え、書き込めないことを確かめ続けていること（`marker` の読み取りと書き込みの拒否）
- 2 件目: helper の写しが、外側・内側の両方のサンドボックスから見えること。写しの置き場所（attempt）は読み取り専用で戻るので、helper が書き込める場所に置いていないこと
- 2 件目: `probe_helper` を足しても、adapter の `parent_review_read_paths` が受け付けること（`parent_pr_data` 以外の鍵は見ない）と、`test_invalid_parent_review_input_is_rejected_before_launch` の 12 件が同じ fixture で通ること
- pr-review と同じ使い方（親の `.venv`、`PYTHONPATH` を worktree）でも、worktree 自身の `.venv` でも通ること
- 同じディレクトリのほかの DSH のテスト（`test_runner.py` など）が `/tmp` の下で通ること

## 要件と Task・検証の対応

| Spec の受け入れ条件 | 担当 Task | 観測する結果 | 検証方法 |
| --- | --- | --- | --- |
| 1. `/tmp` の下で、自前の `.venv` でも pr-review の使い方でも通る | Task 1・Task 2（統合は Task 3） | `tools/agent_runner/tests/adapters/dsh` が 0 failed・0 skipped | Task 3 の手順 1・2 |
| 2. `/workspaces` の下で通る | Task 3 | 同じディレクトリが 0 failed・0 skipped | Task 3 の手順 3 |
| 3. skip されず、検査の対象を減らさない | Task 1・Task 2 | 2 件が passed として数えられる。assert を消していない | `-rA` の出力と `git diff` |
| 4. adapter の本体と手順は変えない | Task 3 | 差分が上の 2 ファイルと Spec・Plan だけ | Task 3 の手順 4（`git diff --stat origin/main`） |
| 5. README の「テスト」の入口で、この変更による失敗が無い | Task 3 | 3 つの入口の終了コード。失敗があれば基準（`f2350a4`）と比べる | Task 3 の手順 8（最後の commit の上） |

共有する前提: 2 件はどちらも「`/tmp` の下で adapter が戻すのは決まったパスだけ」という同じ adapter の挙動（`tools/agent_runner/adapters/dsh.py:248-266`）に頼る。両方の Task の後に、Task 3 で同じ checkout の 2 つの場所・2 つの使い方で確かめる。

## 実行予算

- Issue 全体の能動時間の予算: 240 分（ledger: `/workspaces/reso-world/tmp/agents/issue-198.f428uvx6/budget.jsonl`）。目安は Spec・Plan 20 分、Task 1・2 15 分、Task 3 40 分（テストの実行の待ちが大半）、PR 10 分、PR 修正ループ最大 3 サイクル ×（レビューの期限 45 分＋計画・修正 15 分）＝ 180 分のうちの残り。ループが 1 サイクルで修正不要なら合計 2 時間ほど
- worker は使わない（inline）。長時間の実行（`run-tests.bash`・pytest 全体）はバックグラウンドで実行し、終了コードで確かめる。1 回の期限は 30 分
- 再試行の上限: 同じ signature の信頼性の失敗（テストの時間切れ・環境の I/O の停止）は 1 回まで。安全の失敗（実リポジトリ・親の `.venv` の書き換えの疑い）は再試行せず止まる
- checkpoint: Task 2 の後、Task 3 の後、ループの各サイクルの後、予算の 50%・100%
- 縮小・方法変更の候補: README の入口が環境の要因で落ちたら、基準（`f2350a4`）の同じ実行と比べて差分だけを判定する。`/tmp` の worktree が使えなければ、`/tmp` の下の使い捨ての clone で代える

## Task 1: 1 件目の担当のコマンドを実体の interpreter にする

**Files:**
- Modify: `tools/agent_runner/tests/adapters/dsh/test_adapter.py:158`（`test_tmp_launch_script_and_shared_environment_are_visible_readonly`）

**テストの要否:** 既存のテストを直す変更で、新しいテストは書かない（D-198-4）。修正の前の失敗は `/tmp` の検証用 worktree で再現済み（下の「検証の記録」）。

- [x] **Step 1:** `context.agent.command = [sys.executable, str(script)]` の `sys.executable` を `str(Path(sys.executable).resolve())` に変え、直前に `test_adapter_cache_paths_are_writable_with_its_scoped_runner` の 102 行と同じ趣旨のコメント（profile は `/tmp` を隠すので、`/tmp` の checkout の venv は見えないが、それが指す interpreter は見える）を 1 行置く
- [x] **Step 2:** feature worktree で `uv run pytest tools/agent_runner/tests/adapters/dsh/test_adapter.py -q -k tmp_launch_script` が passed
- [x] **Step 3:** commit（`fix(agent_runner): run the dsh tmp launch test with the real interpreter`）

## Task 2: 2 件目の helper を attempt に写して渡す

**Files:**
- Modify: `tools/agent_runner/tests/adapters/dsh/test_adapter.py:171-198`（`parent_review` fixture）
- Modify: `tools/agent_runner/tests/adapters/dsh/fake_cli.py:129`（`parent-input` モードの `target_script`）

**Interfaces:**
- Produces: 依頼のパラメータ `probe_helper: str`（attempt に写した `review_target.py` の絶対パス）。`fake_cli.py` の `parent-input` モードだけが読む

**テストの要否:** Task 1 と同じ。

- [x] **Step 1:** `parent_review` fixture で、`Path(__file__).resolve().parents[5] / ".agents/scripts/review_target.py"` を `context.receipt_path.parent / "review_target.py"` に `shutil.copyfile` で写し、`parameters` に `"probe_helper": str(<写し>)` を足す。写す理由（profile は `/tmp` を隠し、checkout の `tools/` だけを戻すので、`/tmp` の checkout の `.agents/` は見えない。attempt は両方のサンドボックスで読み取り専用で戻る）をコメント 1〜2 行で書く。返す dict に `"helper"` を足す必要は無い
- [x] **Step 2:** `fake_cli.py` の `target_script = Path(__file__).resolve().parents[5] / ".agents/scripts/review_target.py"` を `target_script = Path(parameters["probe_helper"])` にする
- [x] **Step 3:** feature worktree で `uv run pytest tools/agent_runner/tests/adapters/dsh/test_adapter.py -q` が全件 passed（`test_invalid_parent_review_input_is_rejected_before_launch` の 12 件を含む）
- [x] **Step 4:** commit（`fix(agent_runner): give the dsh parent-input probe a sandbox-visible helper`）

## Task 3: 統合確認

**テストの要否:** 確認だけで、コードを変えない。

- [x] **Step 1:** `/tmp` の検証用 worktree を Task 2 の commit に合わせ（`git -C /tmp/issue-198-repro.PrSkoY/wt checkout --detach <SHA>`）、worktree 自身の `.venv` で `uv run --locked pytest tools/agent_runner/tests/adapters/dsh -q -rs -p no:cacheprovider`。期待: 0 failed・0 skipped
- [x] **Step 2:** 同じ worktree で、pr-review と同じ使い方 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$WT" uv run --project /workspaces/reso-world --locked python -m pytest tools/agent_runner/tests/adapters/dsh -q -rs -p no:cacheprovider`。期待: 0 failed・0 skipped
- [x] **Step 3:** feature worktree（`/workspaces` の下）で `uv run pytest tools/agent_runner/tests/adapters/dsh -q -rs`。期待: 0 failed・0 skipped
- [x] **Step 4:** `git diff --stat origin/main` が、2 つのテストのファイルと Spec・Plan だけであること
- [x] **Step 5:** `/tmp` の検証用 worktree を `git worktree remove` で外し、`mktemp` のディレクトリを `rmdir` で消す
- [x] **Step 6:** ブランチ全体のレビュー（新しいコンテキストのサブエージェント）を受け、致命的な指摘があれば直す（直したら Step 1〜3 をやり直す）
- [x] **Step 7:** 手順 1〜3 と 6 の記録をこの Plan に書き、commit（これが最後の commit）
- [ ] **Step 8:** 最後の commit の上で、`git status --porcelain` が空であることを確かめてから、README の「テスト」の入口（`bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`uv run pytest tests/skills .agents/skills .agents/scripts tools`）を実行する。失敗があれば、基準（`f2350a4`）の同じ実行と比べ、この変更によるものでないことを確かめる。検証した HEAD・argv・終了コード・ログのパスと、`finalize.py` の `--checks-file` の形のファイルをログの置き場所に作る（issue-to-pr の 5 章）。結果は Plan に書かず（HEAD が変わるので）、PR 本文に書く

## 検証の記録

### 修正の前（`f2350a4`、`/tmp/issue-198-repro.PrSkoY/wt`）

| 使い方 | 結果 | ログ |
| --- | --- | --- |
| worktree 自身の `.venv`（`uv run --locked pytest tools/agent_runner/tests/adapters/dsh`） | 2 failed・281 passed（1 件目は `bwrap: execvp /tmp/.../wt/.venv/bin/python: No such file or directory`、2 件目は `FileNotFoundError: /tmp/.../wt/.agents/scripts/review_target.py`） | `baseline-tmp-own-venv.log` |
| pr-review と同じ使い方（親の `.venv`、`PYTHONPATH` を worktree） | 1 failed（2 件目）・282 passed | `baseline-tmp-parent-venv.log` |

### 修正の後

ログはどれも `/workspaces/reso-world/tmp/agents/issue-198.f428uvx6/` にある。`-rs` で skip の理由を出す指定にし、skip は 0 件。

| commit | 場所・使い方 | 結果 | ログ |
| --- | --- | --- | --- |
| `bdbb008`（Task 1） | `/tmp` の worktree 自身の `.venv`、`-k tmp_launch_script` | 1 passed | ― |
| `9da5d1a`（Task 2） | `/tmp` の worktree 自身の `.venv` | 283 passed | `after-tmp-own-venv.log` |
| `9da5d1a` | `/tmp` の worktree、pr-review と同じ使い方 | 283 passed | `after-tmp-parent-venv.log` |
| `9da5d1a` | `/workspaces` の feature worktree | 283 passed | `after-workspaces.log` |
| `59e878a`（レビューの指摘でコメントを直した後） | `/tmp` の worktree 自身の `.venv` | 283 passed | `r2-tmp-own-venv.log` |
| `59e878a` | `/tmp` の worktree、pr-review と同じ使い方 | 283 passed | `r2-tmp-parent-venv.log` |
| `59e878a` | `/workspaces` の feature worktree | 283 passed | `r2-workspaces.log` |

`git diff --stat origin/main...59e878a` は、`fake_cli.py`（1 行）と `test_adapter.py` と Spec・Plan だけ（受け入れ条件 4）。`/tmp` の検証用 worktree は `git worktree remove` で外し、`mktemp` のディレクトリも消した。

### 最終レビュー（opus、新しいコンテキスト）

- 判定: Approve。Critical・Important は無し。`/tmp` の使い捨て clone で adapter をわざと壊し（`sys.prefix`・コマンドのファイル・親の入力を戻さない）、2 件のテストが気付くこと、helper の写しへの書き込みが外側・内側の両方で拒否されることを確かめた
- Minor 1（1 件目のコメントが、venv が戻らない理由を adapter の性質のように書いている。実際は `sys.prefix` を差し替えているため）: 境界の説明を誤るので Important に上げ、`59e878a` で直した。コメントだけの変更なので、テストの再実行（上の表の `59e878a` の行）で確かめた
- Minor 2（helper の写しは `review_target.py` が単独で import できることを前提にする）: 見送り。将来その前提が崩れても、2 件目は失敗する方向に倒れ、誤って通らない
- 判断を保留した 5 件（README の入口は Step 8 で実行、内側の復元が `--bind` に変わっても気付かないのは既存の性質、interpreter の実体が `/tmp` の下の環境は今の環境で起きない、tool root を `/tmp` に置く運用は D-198-5、Plan の記録は Step 7）は、どれも範囲外か手順の途中なので、そのままにした

### 所要時間（Step 7 の時点）

着手 2026-10-20 14:27Z ごろ、Step 7 は 14:58Z ごろ（約 31 分）。内訳: 入力・競合の確認と再現 8 分、Spec・Plan 8 分、Task 1・2 5 分、Task 3 の Step 1〜6（テストの待ちとレビュー 10 分を含む）10 分。
