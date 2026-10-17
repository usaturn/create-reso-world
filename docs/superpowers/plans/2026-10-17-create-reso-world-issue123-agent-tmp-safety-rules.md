# Issue #123 コミットしないファイルの置き場所・作業の安全規則 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

- 文書管理・コード対象: `usaturn/create-reso-world`、Issue #123
- 基準 HEAD: `cd602e63e04e51616cd5043dd46b0cbefd8fc60e`（`origin/main`）
- 状態: draft（文書の内容に対する利用者の明示承認は無い）
- 実行許可: Spec の「管理・実行許可」のとおり（推奨案で PR の作成まで。マージは利用者）
- 実行方法: superpowers:executing-plans（controller が自分で実装する。利用者の「途中で止めずに」の指示による、エージェントの判断）
- 作業場所: `/workspaces/reso-world/.worktrees/issue-123-agent-tmp-safety-rules`（ブランチ `feat/issue-123-agent-tmp-safety-rules`）

**Goal:** `agent_tmp.py` とそのテストを移植し、`AGENTS.md` に置き場所の表・作業の安全規則・日本語表現の規則を足す。

**Architecture:** `agent_tmp.py` は標準ライブラリだけの CLI で、スクリプト自身の置き場所から親の checkout を求める。判定のロジックは移植元 `d3f4151` のまま。規則は `AGENTS.md` に 1 か所で書き、`CLAUDE.md` の重複を消す。

**Tech Stack:** Python 3.12 以上（`uv run --no-project python`）、pytest、git

**Spec:** `docs/superpowers/specs/2026-10-17-create-reso-world-issue123-agent-tmp-safety-rules-design.md`

## Global Constraints

- 実行のコマンドは `uv run --no-project python .agents/scripts/agent_tmp.py root|mkdir <topic>`
- topic の形は `[a-z0-9][a-z0-9._-]{0,63}`、作るディレクトリは `<PARENT_ROOT>/tmp/agents/<topic>.XXXXXX`
- `testpaths = ["tests/skills", ".agents/skills", ".agents/scripts"]`（#115 のブランチと同じ行）
- `.devcontainer/` と #115 のファイルは変えない
- 文書は `AGENTS.md` の「日本語表現」に従う（「正本」「着地」を使わない、など）

## Review Focus

1. ワールドを cwd にしたエージェント（ワールドが自分の `.git` を持つ場合を含む）が `root` を呼ぶ — ワールドではなく親の checkout を返す（Task 1 の `test_cli_root_from_every_cwd`）
2. worktree の写しから `mkdir` を呼ぶ — worktree の中ではなく親の `tmp/agents/` に作る（Task 1 の `test_cli_mkdir_from_worktree_copy_writes_parent_tmp`）
3. 不正な topic で CLI を呼ぶ — stdout に何も出さず、`tmp/agents` も作らない（Task 1 の `test_cli_rejects_invalid_topic_without_creating`）
4. 「編集前の確認」を読んだワールドのエージェント — ワールドの作業を worktree に移そうとしない（Task 2 の読み合わせ）
5. 規則を読んだエージェントが `tmp/` の既存の entry を片付けようとする — `tmp/agents/` 以外は触らない（Task 2 の文面）

---

### Task 1: `agent_tmp.py` とテスト

テスト: 要る。CLI を実際に実行して、親の checkout の解決・ディレクトリの作成・不正な入力の拒否（安全条件）を確かめる（「テストの採用基準」の「書く」）。

**Files:**
- Create: `.agents/scripts/agent_tmp.py`
- Create: `.agents/scripts/tests/test_agent_tmp.py`
- Modify: `pyproject.toml`（`testpaths`）、`README.md`（「テスト」の節のコマンド）、`.github/workflows/ci.yml`（`skill-tests` のコマンド）

**Interfaces:**
- Produces: `resolve_main_root(anchor: Path) -> Path`、`make_session_dir(main_root: Path, topic: str) -> Path`、`main(argv: Sequence[str] | None = None) -> int`、`AgentTmpError`、`TOPIC_PATTERN`、`AGENTS_DIR`（移植元と同じ名前）

- [ ] **Step 1: テストを書く**

移植元の `test_agent_tmp.py` の単体テスト（`make_repo` を使う 10 件）をそのまま写す。`make_repo` の commit は `-c commit.gpgsign=false` を付ける。次を変える・足す。

- `test_resolve_main_root_rejects_submodule_checkout`: テストの中で `sub`（1 commit の repository）を作り、`make_repo` の親で `git -c protocol.file.allow=always submodule add <sub> public` して commit し、`resolve_main_root(parent / "public")` が `match="common dir"` で失敗することを確かめる
- fixture `parent_checkout(tmp_path) -> Layout`（`Layout` は `parent`・`worktree`・`meshy`・`meshy_worktree`・`world`・`outside` の `Path` を持つ dataclass）: bare の origin に、実際の `.gitignore`（`SCRIPT.parents[2] / ".gitignore"`）と `SCRIPT` の写しを `.agents/scripts/agent_tmp.py` として commit する。`git clone` の後 `git checkout --detach origin/main` と `git branch -D main` で親を detached にする。`git worktree add -b feat/x .worktrees/x origin/main`。`external/resoloop-meshy` は別の bare origin の clone で、`.worktrees/y` の worktree を持つ。`worlds/w` は `git init` した独立の repository で、`worlds/w/sub` を作る
- `test_cli_root_from_every_cwd`: 親と worktree の写しのそれぞれを、`parent`・`worktree`・`meshy`・`meshy_worktree`・`world`・`world/sub`・`outside` の各 cwd から `sys.executable <copy> root` で実行し、終了コード 0、stdout が `f"{parent}\n"`
- `test_cli_mkdir_from_worktree_copy_writes_parent_tmp`: worktree の写しを `meshy_worktree` から `mkdir issue-123` で実行し、出力のパスが `parent / "tmp/agents"` 直下の `issue-123.` で始まるディレクトリで、モードが `0o700`、`git status --porcelain` が親・worktree とも空
- `test_cli_rejects_invalid_topic_without_creating`: 親の写しで `mkdir bad/topic` を実行し、終了コード 1、stdout が空、stderr が `agent_tmp: ` で始まり、`parent / "tmp"` が存在しない
- 移植元の `test_cli_rejects_invalid_topic_without_stdout`・`test_cli_root_is_independent_of_cwd`（実際の checkout で実行する 2 件）は、上の 3 件に置き換えて持ち込まない

- [ ] **Step 2: 失敗を確かめる**

Run: `uv run pytest .agents/scripts -q`
Expected: `agent_tmp.py` が無いため収集で失敗する

- [ ] **Step 3: `agent_tmp.py` を移植する**

移植元 `d3f4151` の本文を写し、Spec の D-2 のとおり docstring だけを変える（`usaturn/agent-workspace#333` からの移植、`create-reso-world#123`、移植先の呼び出し元の例）。

- [ ] **Step 4: テストを通す**

Run: `uv run pytest .agents/scripts -q`
Expected: すべて PASS

- [ ] **Step 5: テストの範囲を足す**

`pyproject.toml` の `testpaths` を Global Constraints の行にする。`README.md` の「テスト」の節と `.github/workflows/ci.yml` の `uv run pytest tests/skills .agents/skills` に ` .agents/scripts` を足す。

Run: `uv run pytest -q`
Expected: `.agents/scripts` のテストを含めて PASS

- [ ] **Step 6: Commit**

```bash
git add .agents/scripts pyproject.toml README.md .github/workflows/ci.yml
git commit -m "feat: add agent_tmp.py from agent-workspace (#123)"
```

### Task 2: `AGENTS.md`・`CLAUDE.md` の規則

テスト: 要らない。文書だけの変更（「テストの採用基準」の「書かない」）。代わりに `bash tests/scripts/test-instructions.bash`（参照の実在と `CLAUDE.md` の 1 行目）、`git diff` の確認、「プロジェクト運用」との読み合わせを行う。

**Files:**
- Modify: `AGENTS.md`（「日本語表現」「ファイルとドラフト」「Spec・Plan の保存と公開」、新しい「作業の安全」）
- Modify: `CLAUDE.md`（「一時ファイル・ディレクトリの削除」を消す）

**Interfaces:**
- Consumes: Task 1 の `.agents/scripts/agent_tmp.py`（`test-docs.bash --refs` が実在を確かめる）

- [ ] **Step 1: 「日本語表現」に Spec の D-8 の 2 件を足す**
- [ ] **Step 2: 「ファイルとドラフト」に「コミットしないファイルの置き場所」の小節を足す**（Spec の D-1 の表と規則）
- [ ] **Step 3: `PARENT_ROOT` の定義に `agent_tmp.py root` の出力であることを足す**（Spec の D-3）
- [ ] **Step 4: 「作業の安全」の節を「ファイルとドラフト」の次に作る**（Spec の D-6 の 4 項目）
- [ ] **Step 5: `CLAUDE.md` の「一時ファイル・ディレクトリの削除」を消す**（Spec の D-7）
- [ ] **Step 6: 確かめる**

Run: `bash tests/scripts/test-instructions.bash`
Expected: `PASS: root instruction imports, references and persona SHA`

読み合わせ: 「作業の安全」の書き分けの箇条と「プロジェクト運用」の 1・3 番目の箇条を並べ、ワールドの作業に worktree・branch を求める読み方が無いことを確かめる。`git diff` で「正本」「着地」などの語を足していないことを確かめる。

- [ ] **Step 7: Commit**

```bash
git add AGENTS.md CLAUDE.md
git commit -m "docs: add uncommitted file locations and work safety rules (#123)"
```

### Task 3: 全体の検証と PR

テスト: 新しく書かない。README の「テスト」の全項目を実行する。

- [ ] **Step 1: 検証を実行する**

Run: `bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`uv run pytest tests/skills .agents/skills .agents/scripts`
Expected: すべて終了コード 0。`check-layout.sh` の `warn:`（同梱スキルの更新など、環境に依存する表示）は結果に書く

- [ ] **Step 2: Spec・Plan の「完了」を書き、確認用のコピーを作る**

Plan の末尾に「完了」の節（各検証の結果、所要時間と Task 別の内訳）を書いて commit する。`scripts/superpowers-review-copy.sh` で `tmp/superpowers-review/` に `create-reso-world-issue123-agent-tmp-safety-rules-spec.md`・`...-plan.md` をコピーする。

- [ ] **Step 3: push と PR**

`git push -u origin feat/issue-123-agent-tmp-safety-rules`、`gh pr create --base main`。本文は `Closes #123`、変更の要約、検証の結果、持ち越し（`.devcontainer/README.md` のテストのコマンド、`repo-cleanup-after-merge` の固定名、#115 の入口）を書く。
