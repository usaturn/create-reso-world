# Issue #83 Legacy Reference Guard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 由来コメントを誤検出する文言ガードを撤去し、実際の操作先と mount の安全検査を維持する。

**Architecture:** 不要な追跡ファイル検査と専用の正規表現テストを同じファイルごと削除する。既存 resolver/context と mount の実行検査を変更せずに検証する。

**Tech Stack:** Python / uv / pytest、Bash、Git。

**Spec:** `docs/superpowers/specs/2026-10-11-create-reso-world-issue83-legacy-reference-guard-design.md`

- 文書管理・対象リポジトリ: `usaturn/create-reso-world`、Issue #83
- 基準コード HEAD: `8f7594a85636c26c719abe51eb932e8516abf398`
- 状態: draft
- 実行許可: Spec の「実行許可」に記載。推奨案での継続指示による実行であり、個別の文書承認ではない。
- 公開状態: 公開未実施。push・PR 作成・マージ・Issue close はしない。

## Global Constraints

- 変更対象は `tests/skills/test_legacy_references.py` の削除と、本 Issue の Spec・Plan だけ。
- `.devcontainer/test-initialize-mounts.bash` の由来コメント・mount 一覧・実行検査は変更しない。
- resolver/context の実装・実行テスト、`AGENTS.md`、既存の履歴文書、ローカルワールドは変更しない。
- 文書の文言・削除済みファイルの不在だけを照合する代替テスト、allowlist、文章分類器は追加しない。
- Python の実行には `uv` を使う。公開操作は行わない。親 checkout は `origin/main` のまま維持する。

## Review Focus

新しい入力解析・実行ロジックはないため、新規テストは不要。以下は既存検査と差分確認で検証する。

- 由来コメントと操作指示の混同: 正しい由来コメントを保持し、誤った操作指示はレビューで確認する。
- 誤った root・remote: 既存の resolver/context 実行テストを維持し実行する。
- 秘密情報の mount 範囲: 既存の mount 実行検査を維持し実行する。
- 過去の #51 や #68 の記録: 履歴文書を書き換えず、今回の判断は本 Spec に残す。
- テストの採用基準: 文言検査やファイル不在検査を代替として追加しない。

## File Structure / Scheduling

削除対象ファイルの責務は移行元参照の文字列検査だけで、他の実装から利用されていない。Spec は判断、Plan は手順と検証記録を持つ。
独立したレビュー面がないため Task は 1 件。並列設定でも分割せず、隔離 worktree 内の単一 implementer で実行する。調査子・実装子・レビュー子は同期で直列 dispatch する。

---

### Task 1: 不適切な文言ガードを撤去して既存の安全検査を検証する

**Files:**
- Delete: `tests/skills/test_legacy_references.py`
- Preserve: `.devcontainer/test-initialize-mounts.bash`
- Preserve: `tests/scripts/test_superpowers_context.py`
- Preserve: `.agents/skills/pr-review/tests/test_pr_review_skill_contract.py`
- Preserve: `.agents/skills/review-fix-planning/tests/test_review_fix_planning_skill_contract.py`

**Interfaces:**
- Consumes: 既存 pytest と Shell のテストコマンド。
- Produces: 文言ガードを外したテストスイート。新しい API・ヘルパー・テストは作らない。

**テスト要否:** 新規テスト不要。削除済み参照の不在だけを確かめる検査の撤去であり、実装ロジックは変更しない。失敗の再現と、残す検査の実行・差分確認で代える。

- [ ] **Step 1: 修正前の失敗を再現する**

Run: `uv run pytest -q tests/skills/test_legacy_references.py`
Expected: mount の由来コメントを指した 1 failed / 8 passed。基準全体の結果は controller が記録済み。

- [ ] **Step 2: 専用のテストファイルを削除する**

`git rm tests/skills/test_legacy_references.py`。コメントを変更せず、pytest の除外設定や skip へ逃がさず、代替テストも追加しない。

- [ ] **Step 3: 維持する境界検査と mount 検査を実行する**

Run: `uv run pytest -q tests/scripts/test_superpowers_context.py .agents/skills/pr-review/tests/test_pr_review_skill_contract.py .agents/skills/review-fix-planning/tests/test_review_fix_planning_skill_contract.py`
Run: `bash .devcontainer/test-initialize-mounts.bash`
Expected: 全件成功。テストは実際の resolver/context を実行し、誤った作業先・remote を拒否する。

- [ ] **Step 4: 全体と配置・差分を検証する**

Run: `uv run pytest -q -rs`
Run: `bash .devcontainer/run-tests.bash`
Run: `bash scripts/check-layout.sh`
Run: `git diff --check; git diff --cached --check; git diff HEAD --stat`
Expected: pytest 失敗なし、skip があれば理由を記録。Shell 全件成功、配置成功、差分は削除対象だけ。worktree にはローカルワールドがないことを記録。環境起因の警告は分離して記録する。

- [ ] **Step 5: 自己レビューしてコミット・報告する**

`git commit -m "test: remove migration-source wording guard"`
詳細報告は指定 report ファイルに書く。変更、再現・検証のコマンドと結果、skip・警告、所要時間と Task 内訳を記録する。Spec・Plan の完了チェックと更新は controller が行う。
