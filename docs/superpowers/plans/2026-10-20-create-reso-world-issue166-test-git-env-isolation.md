# Issue #166 テストの git の `GIT_*` の隔離 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

- 状態: draft
- 対象 Issue: https://github.com/usaturn/create-reso-world/issues/166

**Goal:** テストの git が、外から渡された `GIT_*`（linked worktree の `git rebase --exec` が export する `GIT_DIR` など）を引き継がず、実リポジトリを書き換えないようにする。

**Architecture:** pytest のテスト全体はルートの `conftest.py` の autouse fixture で、unittest の 2 本は `self.env` の作り方で、bash のテストは `.devcontainer/run-tests.bash` で `GIT_*` を除く。pytest と bash は、`GIT_DIR` を渡して別のプロセスで起動する回帰テストで守る。

**Tech Stack:** Python 3.14・pytest 9.1.1（`uv run`）、unittest、bash、git

**Spec:** `docs/superpowers/specs/2026-10-20-create-reso-world-issue166-test-git-env-isolation-design.md`

## Global Constraints

- 除くのは `GIT_` で始まる環境変数だけ。HOME・`XDG_CONFIG_HOME`・git の全体設定は変えない（Spec の D-166-3）
- 既存の個別の fixture（`isolated_git_environment`・`isolated_git` など）は変えない（D-166-4）。ルートの fixture の名前はそれらと別にする
- `tools/agent_runner/` などの本体は変えない（Spec の「範囲外」）
- Python は `uv run` で実行する。`python3` コマンドを使わない
- 一時ファイル・使い捨ての clone は `mktemp -d` の一意のディレクトリか、`/workspaces/reso-world/tmp/agents/issue-166.713wwe8b/`（ログ）に置く。worktree の中に作らない

## Review Focus

1. 既存の fixture が足す `GIT_CONFIG_GLOBAL=/dev/null` などを、ルートの fixture が後から消す順序になっていないか → Task 4 で `--setup-plan` を確かめる
2. ルートの `conftest.py` がワールドのプロジェクト・`external/` の pytest に効いてしまわないか → Spec の「確認した事実」で確認済み（pytest 9.1.1）。Task 4 で再確認しない
3. テストの本体が `monkeypatch.setenv("GIT_DIR", ...)` する既存のテスト（`test_runner.py`・`test_workspace.py`）が、ルートの fixture の後でも意図どおり動くか → Task 4 の全体テスト
4. `GIT_EDITOR` などを除いたことで、エディタを起動する git（`-m` の無い commit など）が止まらないか → Task 4 の全体テストが終わること（`-m` の無い commit が無いことは調査済み）
5. `compgen` の無い bash では `run-tests.bash` が動かない → Dev Container の bash（Ubuntu 26.04 の bash 5.x、progcomp 付き）で動くことを Task 3 で確かめる

## 共有する条件と統合担当

Task 1〜3 は別のファイルを変え、共有する入力は「外の環境の `GIT_*`」だけである。条件ごとの担当と検証:

| Spec の受け入れ条件 | 担当 Task | 観測する結果 | 検証方法 |
| --- | --- | --- | --- |
| 1. 入口のテスト全体で元のリポジトリが変わらない | Task 4（統合） | 共有の設定・HEAD・index・status の前後が同じ | 使い捨ての clone の linked worktree の `GIT_DIR` を export して 3 つの入口を実行 |
| 2. Issue の再現が止まらずに終わる | Task 4 | rebase が成功、`user.name=Test` が書かれない | 使い捨ての clone で `git rebase --exec` |
| 3. 回帰テストが修正の前に失敗し、後に通る | Task 1・3 | 赤 → 緑 | 各 Task の Step 2・4 |
| 4. 既存の fixture の設定が消えない | Task 4 | ルートの fixture が先に準備される | `--setup-plan` |
| 5. 入口のテストが基準と同じ | Task 4 | 基準と同じ（件数は新しいテストの分だけ増える） | 基準: `tmp/agents/issue-166.713wwe8b/baseline-pytest.log` |

## 実行方式

inline（`superpowers:executing-plans`）。Spec の D-166-8 のとおり、`check` の `self` が true で、Task はどれも数行の変更であり、子に文脈を渡す手間が実装より大きい。最後にブランチ全体のレビューを別の担当（`superpowers:requesting-code-review`）に依頼する。

## 実行予算

- 全体の能動時間: 180 分（Task 4 つ、変更は小さいが、統合確認で全体のテストを 3 回ほど実行する）。ledger は `/workspaces/reso-world/tmp/agents/issue-166.713wwe8b/budget.jsonl`
- phase の目安: 準備・Spec・Plan 〜50 分、Task 1〜3 〜40 分、Task 4 〜50 分、レビュー・PR 〜40 分
- worker の期限: 読み合わせ・レビューのサブエージェントは各 20 分。全体テストは止めない（検証コマンドは打ち切りの対象外）
- 再試行の上限: 同じ失敗の再試行は 1 回まで
- checkpoint: Task 3 の後、Task 4 の後、予算の 50%・100%
- 縮小・切り出し・方法変更の候補: 統合確認の全体テストが環境の要因で落ちたら、基準と同じ失敗かを比べ、同じなら変更と無関係として記録する。bash のテストの対応（Task 3）が既存のテストを壊して直せなければ、Task 3 を外して持ち越し候補として PR 本文に書く

## Contingency

- 回帰テストが修正の前に失敗しなければ（赤にならなければ）、再現の形（`GIT_DIR` の値、内側の pytest の cwd）を Issue の再現と比べて直す。それでも赤にならなければ止まる
- 全体テストで基準に無い失敗が出たら `superpowers:systematic-debugging` で調べる。ルートの fixture が原因で、既存のテストの前提（外の `GIT_*` を読む）を変える必要があれば止まる

---

### Task 1: ルートの `conftest.py` と pytest の回帰テスト

テストの要否: 書く。実際に起きた不具合（共有の設定・ブランチの書き換え）の再発を防ぐ。

**Files:**
- Create: `conftest.py`（リポジトリのルート）
- Create: `tools/agent_runner/tests/test_git_isolation.py`

**Interfaces:**
- Produces: autouse fixture `drop_inherited_git_environment(monkeypatch) -> None`（名前は既存の `isolated_git_environment` と別）

- [ ] **Step 1: 回帰テストを書く**

`tools/agent_runner/tests/test_git_isolation.py` に次の 2 つ:

- `test_fixture_git_stays_in_its_temporary_repository(tmp_path)`: `tmp_path / "fixture"` で `git -C <dir> init -q`・`config user.name Test`・`config user.email test@example.invalid`・ファイルを `add`・`commit -qm initial` し、`Path(git(dir, "rev-parse", "--absolute-git-dir")) == dir / ".git"` を確かめる
- `test_inherited_git_dir_of_a_linked_worktree_does_not_reach_fixture_git(tmp_path)`: `tmp_path / "main"`（branch `main`、1 commit）と linked worktree `tmp_path / "linked"`（branch `work`）を作り、`snapshot()` =（`main/.git/config` のバイト列、linked の `symbolic-ref HEAD`、`rev-parse HEAD`、linked の管理領域の `index` のバイト列、`status --porcelain --untracked-files=all`）を取る。`dict(os.environ, GIT_DIR=<linked の rev-parse --absolute-git-dir>)` の環境で、cwd をリポジトリのルートにして `sys.executable -m pytest -q --basetemp <tmp_path/inner> <このファイル>::test_fixture_git_stays_in_its_temporary_repository` を実行し（timeout 120 秒）、`returncode == 0`（失敗なら stdout・stderr を表示）と `snapshot()` が前と同じことを確かめる

- [ ] **Step 2: 修正の前に失敗することを確かめる**

Run: `uv run --locked pytest -q tools/agent_runner/tests/test_git_isolation.py`
Expected: `test_inherited_git_dir_...` が FAIL（内側の pytest が失敗し、`snapshot()` も変わる）。もう 1 つは PASS

- [ ] **Step 3: ルートの `conftest.py` に `drop_inherited_git_environment` を書く**

`@pytest.fixture(autouse=True)` で、`tuple(os.environ)` のうち `GIT_` で始まる名前を `monkeypatch.delenv` する。docstring に理由（`git rebase --exec` が `GIT_DIR` を export する・#166）と、既存の fixture より先に準備されること

- [ ] **Step 4: 通ることを確かめる**

Run: `uv run --locked pytest -q tools/agent_runner/tests/test_git_isolation.py`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add conftest.py tools/agent_runner/tests/test_git_isolation.py
git commit -m "test: drop inherited GIT_* before every pytest test (#166)"
```

### Task 2: unittest の 2 本の `self.env`

テストの要否: 書かない。守る挙動は git を起動する辞書から `GIT_*` を除く 1 行で、Task 1 と同じ仕組みの検査を重ねるだけになる（Spec の D-166-6）。代わりに Task 4 で `GIT_DIR` を export して実行する。

**Files:**
- Modify: `tests/scripts/test_superpowers_context.py:35`
- Modify: `tests/scripts/test_superpowers_review_copy.py:68`

- [ ] **Step 1: `self.env` を `{k: v for k, v in os.environ.items() if not k.startswith("GIT_")} | {"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null"}` の形にし、理由を 1 行のコメントで書く**

- [ ] **Step 2: 通ることを確かめる**

Run: `bash tests/scripts/test-superpowers-python.bash`
Expected: `OK`（終了コード 0）

- [ ] **Step 3: Commit**

```bash
git add tests/scripts/test_superpowers_context.py tests/scripts/test_superpowers_review_copy.py
git commit -m "test: keep inherited GIT_* out of the superpowers unittest git (#166)"
```

### Task 3: `run-tests.bash` と bash の回帰テスト

テストの要否: 書く。入口の bash のテストが、実リポジトリを書き換える不具合の再発を防ぐ。

**Files:**
- Modify: `.devcontainer/run-tests.bash`（テストを順に実行する `for` の前）
- Modify: `.devcontainer/test-run-tests.bash`（3 番目の場合の後に 4 番目を足す）

- [ ] **Step 1: 4 番目の場合を書く**

`git init -q "$tmp/victim"` で一時リポジトリを作り、`.git/config` を `$tmp/victim-config` に写す。偽のテスト `$tmp/git.bash` は `git init -q "$tmp/fixture"` と `git -C "$tmp/fixture" config user.name Test` を行う。`GIT_DIR="$tmp/victim/.git" bash "$runner" "$tmp/git.bash"` が 0 を返し、`cmp -s` で `victim/.git/config` が変わらず、`$tmp/fixture/.git` が存在することを確かめる。失敗の文は既存の `fail` を使う

- [ ] **Step 2: 修正の前に失敗することを確かめる**

Run: `bash .devcontainer/test-run-tests.bash`
Expected: FAIL（`victim/.git/config` が変わる、または `fixture/.git` が無い）

- [ ] **Step 3: `run-tests.bash` で `GIT_*` を除く**

テストの `for` の前で `while IFS= read -r name; do unset "$name"; done < <(compgen -e -X '!GIT_*')`。理由を 2 行のコメントで書く

- [ ] **Step 4: 通ることを確かめる**

Run: `bash .devcontainer/test-run-tests.bash`
Expected: `PASS: run-tests.bash runs every test and reports failures`

- [ ] **Step 5: Commit**

```bash
git add .devcontainer/run-tests.bash .devcontainer/test-run-tests.bash
git commit -m "test: drop inherited GIT_* in run-tests.bash (#166)"
```

### Task 4: 統合確認

テストの要否: 書かない（確認だけ）。結果は Plan の「実行の記録」と PR 本文に書く。

- [ ] **Step 1: fixture の準備の順序（受け入れ条件 4）**

Run: `uv run --locked pytest --setup-plan -q .agents/skills/issue-to-pr/tests/test_implement_task_run.py .agents/scripts/tests/test_review_target.py | grep -E 'SETUP +F (drop_inherited|isolated)' | head`
Expected: 各テストで `drop_inherited_git_environment` が `isolated_git_environment`・`isolated_git` より先

- [ ] **Step 2: 入口のテスト（受け入れ条件 5）**

worktree のルートで `uv run --locked pytest -q tests/skills .agents/skills .agents/scripts tools`・`bash .devcontainer/run-tests.bash`・`bash scripts/check-layout.sh` を実行し、基準と比べる

- [ ] **Step 3: `GIT_DIR` を export した入口のテスト（受け入れ条件 1）**

`mktemp -d` の一意のディレクトリに、この branch の HEAD を `git clone` し、linked worktree（branch `work`）を作る。その worktree の管理領域を `GIT_DIR` に export し、worktree を cwd にして 3 つの入口（pytest 全体・`run-tests.bash`・`uv run --no-project python -m unittest discover -s tests/scripts -p 'test_*.py'`）を実行する。前後で、clone の `.git/config`・worktree の `symbolic-ref HEAD`・`rev-parse HEAD`・index の `sha256sum`・`status --porcelain` が同じことを確かめる

- [ ] **Step 4: Issue の再現（受け入れ条件 2）**

同じ clone の linked worktree で、`git rebase --exec 'uv run --locked pytest -q tools/agent_runner/tests/test_workspace.py::test_resolve_revision_pins_commit_not_branch' HEAD~1` が成功し、`git config --get user.name` が `Test` にならないことを確かめる。比較のため、`origin/main` の `8f5074a` の clone でも同じ操作を行い、再現すること（`user.name=Test` が書かれる）を確かめる

- [ ] **Step 5: 使い捨ての clone を消す**

`rm -rf -- "${CLONE_ROOT:?}"`

## 実行の記録

（実行の後に書く）
