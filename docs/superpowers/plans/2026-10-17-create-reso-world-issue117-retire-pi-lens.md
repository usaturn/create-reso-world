# Issue #117 pi-lens の導入停止と撤去 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** reso-world の Dev Container が `npm:pi-lens` を導入しなくなり、登録済みの `~/.pi` からはバックアップを取ってから撤去する。

**Architecture:** 既存の廃止拡張の撤去（`.devcontainer/cleanup_pi_mcp.py` の `PACKAGES`）に `pi-lens` を足し、`.devcontainer/install_beforehand.bash` の拡張の一覧から外す。テストは既存の一覧に足して、汎用のテストで確かめる。

**Tech Stack:** bash（postCreate）、Python（uv）、Pi 1.3.0 のパッケージ管理

**Spec:** `docs/superpowers/specs/2026-10-17-create-reso-world-issue117-retire-pi-lens-design.md`

## 管理・実行許可

- 文書管理・コード対象: `usaturn/create-reso-world`、Issue #117
- 基準 HEAD: `eee9434adf017909770d61e9393129d802a332db`（`origin/main`）
- 状態: completed（2026-10-17 JST、利用者の指示（Spec・Plan を completed にする文書 PR の作成とマージ）による。文書の内容に対する利用者の明示承認は記録していない。完了の根拠は末尾の「完了」）
- 実行許可: 2026-10-17（JST）、利用者の「#117 に対応してください。途中で止めずに推奨案で PR まで実行してください」。推奨案での実装、commit、push、PR の作成まで。マージと rebuild は利用者が行う
- 実行方法: Native（このセッションでインライン実行）。利用者に実行方法を選んでもらう段は、止めずに進める指示に従って省いた。サブエージェントは利用者が求めていないので使わず、レビューは自己レビューと PR での利用者の確認で行う
- 作業場所: worktree `.worktrees/issue-117-retire-pi-lens`、ブランチ `feat/issue-117-retire-pi-lens`（完了後に削除済み）

## Global Constraints

- 実機の共有 `~/.pi` に cleanup やインストーラを実行しない（Spec の「範囲外」）。テストは一時 HOME と偽の pi で行う
- `docs/` の過去の記録は変えない（Spec D-6）
- CI は作らない。private の create-reso-world の Actions は確かめない
- PR の本文は `Refs #117`（Spec D-7）

## Review Focus

- インストーラの一覧に `npm:pi-lens` が残る → `FAKE_PI_REQUIRE_CLEAN=1` のプロビジョニングのテストで、pi-lens の登録後の `pi install` が失敗すること
- 撤去の一覧に足し忘れる → 一覧を回すテストで、pi-lens の登録・マニフェスト・実体が残って失敗すること
- 撤去でほかの拡張を巻き添えにする → 既存の `KEPT` の保持のテストが、pi-lens を足した状態でも通ること

---

### Task 1: pi-lens を撤去の対象に足し、導入をやめる

**Files:**
- Modify: `.devcontainer/tests/test_pi_mcp_cleanup.py`（`REMOVED`、`seed_packages` の `npm/package.json`）
- Modify: `.devcontainer/tests/fake_pi_packages.py`（`retired`）
- Modify: `.devcontainer/cleanup_pi_mcp.py`（`PACKAGES`）
- Modify: `.devcontainer/install_beforehand.bash`（拡張の一覧）

**テストの要否:** 必要。cleanup とインストーラの該当部分を実行して、撤去の安全条件と導入の停止を確かめる（Spec D-3）。

- [ ] **Step 1: テストの一覧に足す**

`test_pi_mcp_cleanup.py`:

```python
REMOVED = ("pi-mcp-adapter", "@upstash/context7-pi", "pi-distill",
           "pi-extensions-tool-display", "pi-extensions-i18n", "pi-lens")
```

`seed_packages` の `npm/package.json` の `dependencies` に `"pi-lens": "^4.4"` を足す。`fake_pi_packages.py` の `retired` にも `"pi-lens"` を足す。

- [ ] **Step 2: 失敗を確かめる**

Run: `bash .devcontainer/run-tests.bash .devcontainer/test-pi-mcp-cleanup.bash`
Expected: FAIL。cleanup が pi-lens を撤去せず、プロビジョニングが pi-lens を入れる

- [ ] **Step 3: 実装する**

`cleanup_pi_mcp.py`:

```python
PACKAGES = (
    "pi-mcp-adapter", "@upstash/context7-pi", "pi-distill",
    "pi-extensions-tool-display", "pi-extensions-i18n", "pi-lens",
)
```

`install_beforehand.bash` の拡張の一覧から `npm:pi-lens \` の行を消す。

- [ ] **Step 4: 通ることを確かめる**

Run: `bash .devcontainer/run-tests.bash .devcontainer/test-pi-mcp-cleanup.bash`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add .devcontainer/cleanup_pi_mcp.py .devcontainer/install_beforehand.bash .devcontainer/tests/
git commit -m "feat(devcontainer): retire pi-lens from pi extensions (#117)"
```

### Task 2: README と `.pi-lens.json`

**Files:**
- Modify: `.devcontainer/README.md`（「pi の旧拡張・MCP 設定の移行」）
- Delete: `.pi-lens.json`

**テストの要否:** 不要。文書の変更と、参照の無い設定ファイルの削除で、コードを実行して確かめる挙動が無い。代わりに Step 2 の検証を行う。

- [ ] **Step 1: 変更する**

README の導入しない拡張の一覧に `pi-lens` を足す。同じ節に、撤去は同じ `~/.pi` を使うほかのコンテナの拡張の実体も消すので、rebuild や手動の cleanup の前にほかのコンテナ・ホストの pi を終了する旨を足す（Spec D-4）。`git rm .pi-lens.json`。

- [ ] **Step 2: 検証する**

Run: `rg -n --hidden -g '!.git' -g '!docs' 'pi-lens' .`
Expected: `.devcontainer/` の撤去の一覧・テスト・README だけが出る

Run: `bash .devcontainer/run-tests.bash && bash scripts/check-layout.sh && uv run pytest tests/skills .agents/skills`
Expected: すべて PASS（check-layout の環境要因の失敗は、main でも同じかを確かめて報告する）

- [ ] **Step 3: Commit**

```bash
git add .devcontainer/README.md
git commit -m "docs(devcontainer): document pi-lens retirement and drop .pi-lens.json (#117)"
```

### Task 3: PR

- [ ] push して PR を作る。本文に `Refs #117`、検証の結果、利用者に頼むこと（ほかのコンテナの Pi を止めてから rebuild、`pi list` に `npm:pi-lens` が無いことの確認、agent-workspace#684・xrift-poc#16 と合わせた取り込み）を書く

## 完了

2026-10-17 JST に完了した。

- コード: #118 を 2026-10-16T19:24Z に `main` へマージした（マージコミット `71607d9`、head `dc2d41b`）。4 モデルのレビューは指摘 0 件で、修正不要と判定した。判定の記録は `docs/superpowers/specs/2026-10-17-create-reso-world-pr118-retire-pi-lens-review-fixes-design.md`
- 検証: PR の head `cd81cde` で `bash .devcontainer/run-tests.bash` 30/30 PASS、`bash scripts/check-layout.sh` PASS、`uv run pytest tests/skills .agents/skills` 474 passed
- rebuild の後の確認: 2026-10-17 02:20 UTC 頃に `main` の `71607d9` で作り直した Dev Container で、`pi list`（Pi 1.3.0）に `npm:pi-lens` が無く、`~/.pi/agent/settings.json`・`~/.pi/agent/npm/package.json`・`~/.pi/agent/npm/package-lock.json`・`~/.pi/agent/npm/node_modules/pi-lens` にも残っていない。撤去の前の登録は、バックアップ `~/.pi/agent/migration-backups/pi-retired-2n0w3n0x`（02:14 UTC）にある
- 合わせて取り込む 2 件: usaturn/agent-workspace#684（PR usaturn/agent-workspace#688）と usaturn/xrift-poc#16（PR usaturn/xrift-poc#17）は、どちらもマージ済みで close
- Issue: #117 を 2026-10-17 に completed で close した（記録は #117 の issuecomment-6233535977）
- worktree: `.worktrees/issue-117-retire-pi-lens` とブランチ `feat/issue-117-retire-pi-lens`（ローカル・リモート）は 2026-10-17 に削除した
