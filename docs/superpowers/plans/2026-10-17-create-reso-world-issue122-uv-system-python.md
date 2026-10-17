# Issue #122 uv の Python をシステムの Python に固定する Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dev Container 内の uv が、uv 管理の古い Python よりシステムの Python（3.14）を選び、無い版を自動でダウンロードしないようにする。

**Architecture:** `.devcontainer/devcontainer.json` の `containerEnv` に `UV_PYTHON_PREFERENCE=system` と `UV_PYTHON_DOWNLOADS=manual` を足し、`.devcontainer/README.md` に設定の意味・影響・既存コンテナの移行を書く。コードとテストは変えない。

**Tech Stack:** Dev Container（`containerEnv`）、uv 0.13.1、システムの Python 3.14.4

**Spec:** `docs/superpowers/specs/2026-10-17-create-reso-world-issue122-uv-system-python-design.md`

## 管理・実行許可

- 文書管理・コード対象: `usaturn/create-reso-world`、Issue #122
- 基準 HEAD: `cd602e63e04e51616cd5043dd46b0cbefd8fc60e`（`origin/main`）
- 状態: draft
- 実行許可: 2026-10-17（JST）、利用者の「#122 に着手せよ。専用 worktree を作成し、途中で止めずに推奨案で PR を出せ」。推奨案での実装、commit、push、PR の作成まで。マージと rebuild は利用者が行う
- 実行方法: Native（このセッションでインライン実行）。利用者に実行方法を選んでもらう段は、止めずに進める指示に従って省いた。サブエージェントは利用者が求めていないので使わず、レビューは自己レビューと PR での利用者の確認で行う
- 作業場所: worktree `.worktrees/issue-122-uv-python-system`、ブランチ `feat/issue-122-uv-python-system`

## Global Constraints

- 設定は `containerEnv` の 1 か所だけに置く。`uv.toml`・`install_beforehand.bash`・`zshrc.txt`・`pyproject.toml` に重複して置かない（Spec D-1）
- `requires-python` は変えない（Spec D-3）
- ローカルのワールドの `.venv` に `uv run` を実行しない。検証は一時ディレクトリで、`UV_PYTHON_INSTALL_DIR`・`UV_CACHE_DIR` を一時ディレクトリに向けて行う（Spec「範囲外」）
- `.devcontainer` にワークスペースの絶対パスを書かない（`.devcontainer/test-readme.bash` の検査）
- CI は作らない。PR の本文は `Refs #122`（Spec D-6）

## Review Focus

- `devcontainer.json`（JSONC）の構文を壊す → `mounts.bash` が読む mount の一覧と、コメントを除いた JSON の `containerEnv` を確かめる（Task 1 Step 2）
- README の確認の手順が、この環境でそのまま動かない → 手順のシェルの block を、2 つの設定を渡した子シェルで実行する（Task 1 Step 3）
- README の旧版の確認手順が、共有の `~/.local/share/uv`・`~/.local/bin` に interpreter を残す → 手順を実行した後に、`uv python list --only-installed` がシステムの 3.14 だけで、`~/.local/bin/python3.12` が無いことを確かめる（Task 1 Step 3）

---

### Task 1: `containerEnv` の設定と README

**Files:**
- Modify: `.devcontainer/devcontainer.json`（`containerEnv`）
- Modify: `.devcontainer/README.md`（「テストの実行」と「Resonite ワールド開発ツール」の間に「uv の Python 実行環境」の節）

**テストの要否:** 不要。設定値と文書だけの変更で、コードを実行して確かめる挙動が無い（Spec D-5）。代わりに Step 2・3 の検証を行う。

- [ ] **Step 1: 変更する**

`containerEnv` に `"UV_PYTHON_PREFERENCE": "system"` と `"UV_PYTHON_DOWNLOADS": "manual"` を足し、上に 1 行のコメント（目的と README の節名）を付ける。

README の節の小見出しは「既存コンテナの移行」と「旧版で互換性を確かめる場合」。書くことは Spec D-4 のとおり。確認の手順は、移植元の受け入れ block に `bash .devcontainer/verify-resonite-tooling.bash` とワールドの `uv run pytest` を加えたもの。旧版の確認は移植元の隔離の手順（`--no-bin`、`UV_PYTHON_INSTALL_DIR`・`UV_CACHE_DIR` を一時ディレクトリ、`trap` で削除）。

- [ ] **Step 2: 設定を検証する**

Run: `sed 's|^[[:space:]]*//.*||' .devcontainer/devcontainer.json | jq -e '.containerEnv'`
Expected: `SHELL`・`UV_PYTHON_PREFERENCE`（`system`）・`UV_PYTHON_DOWNLOADS`（`manual`）の 3 つ

Run: `bash .devcontainer/run-tests.bash && bash scripts/check-layout.sh && uv run pytest tests/skills .agents/skills`
Expected: すべて PASS（check-layout の環境要因の失敗は、`main` でも同じかを確かめて報告する）

- [ ] **Step 3: README の手順を子シェルで実行する**

Run: README の確認の block と旧版の確認の block を、`UV_PYTHON_PREFERENCE=system UV_PYTHON_DOWNLOADS=manual` を渡した子シェルで実行する
Expected: 通常実行が 3.14.4、未導入の 3.12 の明示指定が `No interpreter found` で失敗、旧版の確認は 3.12 を表示して一時ディレクトリを消す。その後 `uv python list --only-installed` はシステムの 3.14 だけで、`~/.local/bin/python3.12` は無い

- [ ] **Step 4: Commit**

```bash
git add .devcontainer/devcontainer.json .devcontainer/README.md
git commit -m "feat(devcontainer): prefer system Python for uv and disable automatic downloads (#122)"
```

### Task 2: PR

- [ ] push して PR を作る。本文に `Refs #122`、Spec の判断（D-2・D-3）、隔離した検証と Task 1 の検証の結果、利用者に頼むこと（rebuild、README の確認の手順の実行、`.venv` が uv 管理の 3.12 を指すワールドの扱い、#125 との衝突）を書く
