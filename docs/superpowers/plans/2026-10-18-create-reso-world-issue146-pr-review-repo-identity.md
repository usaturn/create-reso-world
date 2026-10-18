# Issue #146 pr-review の PR 識別に所属リポジトリを含める Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

- 状態: draft（内容の承認は無い。実行許可は Spec の「管理・実行許可」のとおり）
- Spec: `docs/superpowers/specs/2026-10-18-create-reso-world-issue146-pr-review-repo-identity-design.md`（`46e0d56`）
- 作業場所: `/workspaces/reso-world/.worktrees/issue-146-pr-review-repo-identity`、branch `fix/issue-146-pr-review-repo-identity`（`origin/main` `2deb900` から作成）
- セッションディレクトリ: `/workspaces/reso-world/tmp/agents/issue-146.zw5ywlyu`（ledger・ログ・行動比較の場面。コミットしない）

**Goal:** pr-review の session・保存先・取得 ref・片付けの判断を、owner/repo と PR 番号の組で区別する。

**Architecture:** helper に `--pr-repo` を通して session を version 7 にし、保存先を `reviews/<owner>/<repo>/#<N>-<branch>/` にする。読み取り専用の `sessions` サブコマンドが片付けの候補を判断し、SKILL.md（pr-review・repo-cleanup-after-merge・review-fix-planning）と AGENTS.md はそれを使う形に合わせる。

**Tech Stack:** Python 3（uv、標準ライブラリだけ）、pytest、bash/zsh（SKILL.md のブロック）、gh CLI（テストでは偽の gh）

## Global Constraints

- 正規形は小文字の `owner/repo`。owner は `[a-z0-9](?:[a-z0-9-]*[a-z0-9])?`、repo は `[a-z0-9_.-]+` で `.`・`..` を除く
- 保存先は `reviews/<owner>/<repo>/#<N>-<branch>/<model>.md`、取得 ref は `refs/pr-review/repos/<owner>/<repo>/<N>`、session は `version: 7` と `pr_repository`
- 旧形式のレビュー・session・ref を移動・上書き・削除しない。version 6 の session は保存・削除を拒否する
- `sessions` は何も変更しない。`removable: true` は同じ番号の `MERGED`・`CLOSED` だけ
- session ディレクトリ名（`pr-review-<N>-*`）、`--temp-root /tmp`、pr-review の `allowed-tools` は変えない
- SKILL.md の文面を照合するテストは作らない（AGENTS.md「テストの採用基準」）。pr-review の共通 context のブロックは、`--operation review-workspace` を含むブロックが 1 つだけであること（既存のテストが抜き出す）
- 実在する `/tmp/pr-review-*`・`reviews/`・`external/resoloop` を変更しない。テストは `tmp_path` の中だけで行う
- Python は `uv run` で実行する

## Review Focus

1. 大文字を含む `--pr-repo`（`Usaturn/ResoLoop`）が小文字の保存先と同じになること → Task 1 `test_create_normalizes_pr_repository_case`
2. 旧形式の保存先に自モデルのレビューがあるとき、読まず・書き換えず、`legacy_review` で返すこと → Task 1 `test_create_reports_legacy_review_without_adopting_it`
3. version 6 の session に `cleanup` を実行しても何も消えないこと → Task 1 `test_version6_session_is_kept_by_verify_save_and_cleanup`
4. gh が無い・失敗したとき、`sessions` が残す側に倒れること → Task 3 `test_sessions_keep_when_gh_fails`
5. 上流を保存した後に fork を再レビューすると、`previous_review` が fork の本文になること → Task 1 `test_fork_and_upstream_reviews_are_saved_and_rereviewed_independently`

---

### Task 1: create・state・save に所属リポジトリを通す

**Files:**
- Modify: `.agents/skills/pr-review/scripts/pr_review_workspace.py`（`review_artifact_paths`・`create`・`create_session`・`load_state`・`save`・`parser`）
- Test: `.agents/skills/pr-review/tests/test_pr_review_workspace.py`

**Interfaces:**
- Produces: `normalize_pr_repository(value: str) -> str`（不正なら `WorkspaceError("PR repository must be a GitHub owner/repo")`）
- Produces: `review_artifact_paths(backup_dir, head_branch, model_name, *, pr_number, pr_repository) -> tuple[Path, str]`、`legacy_review_destination(head_branch, model_name, *, pr_number) -> str`
- Produces: `create` の `--pr-repo`（argparse の `pr_repo`）。結果の JSON に `pr_repository` と `legacy_review`（相対パスか `None`）
- Produces: state の `version: 7`・`pr_repository`、journal の `started` の `pr_repository`

**テストの要否:** 必要。保存先の計算・入力の検証・拒否の分岐を実行で確かめる。

- [ ] **Step 1: 既存テストを新しい入力に合わせる**

`argparse.Namespace(... create ...)` と `explicit_create_args`・`create_session`・`start_create`（`--pr-repo` を足す）に `pr_repo="usaturn/create-reso-world"` を足す（定数 `PR_REPO`）。期待する保存先を `reviews/usaturn/create-reso-world/#…` にする。`make_repo` の追跡するレビューを `reviews/usaturn/create-reso-world/#4-fix-herdr-session-cwd/gpt-5.md` に移す。`test_create_parser_*` の引数に `--pr-repo` を足す。

- [ ] **Step 2: 新しいテストを書く**

```python
def test_fork_and_upstream_reviews_are_saved_and_rereviewed_independently(...):
    # 同じ repo・PR 11・branch fix/shared・commit・model で fork と上流を create→draft→save
    assert fork["destination"] == "reviews/usaturn/resoloop/#11-fix-shared/opus-5.md"
    assert upstream["destination"] == "reviews/orange3134/resoloop/#11-fix-shared/opus-5.md"
    # 両方の本文が残る。fork を再 create すると previous_review が fork の本文、保存後も上流の本文は不変

@pytest.mark.parametrize("bad", ["", "usaturn", "usaturn/resoloop/extra", "../resoloop", "usaturn/..",
                                 "-bad/resoloop", "usaturn/res oloop", "https://github.com/usaturn/resoloop"])
def test_create_rejects_invalid_pr_repository(...):  # WorkspaceError("PR repository"), temp_root を作らない

def test_create_normalizes_pr_repository_case(...):  # "Usaturn/ResoLoop" → state と destination が小文字

def test_create_reports_legacy_review_without_adopting_it(...):
    # reviews/#4-fix-herdr-session-cwd/opus-5.md を置く → legacy_review がそのパス、previous_review は None、save 後も旧ファイル不変

def test_version6_session_is_kept_by_verify_save_and_cleanup(...):
    # state を version 6・pr_repository 無しに書き換え → verify/save/cleanup が WorkspaceError("no PR repository")
    # 保存先・snapshot・worktree の登録が変わらない

@pytest.mark.parametrize("value", ["Usaturn/resoloop", "usaturn", 7, None])
def test_load_state_rejects_non_canonical_pr_repository(...):  # "invalid PR-review session state"

def test_save_rejects_rewritten_pr_repository(...):
    # state の pr_repository だけを orange3134/resoloop に → "destination does not match"、どちらの保存先にも書かない
```

- [ ] **Step 3: 失敗を確かめる**

Run: `uv run pytest .agents/skills/pr-review/tests/test_pr_review_workspace.py -q -x`
Expected: FAIL（`pr_repo` の属性が無い、保存先の不一致）

- [ ] **Step 4: 実装する**

`create` は attempt ID の検証の直後に `normalize_pr_repository(args.pr_repo)` を呼ぶ（副作用の前）。`load_state` は `version == 6` のとき `WorkspaceError("PR-review session state has no PR repository (version 6); keep the session and confirm which PR it belongs to")`、ほかの版と非正規の `pr_repository` は従来の `invalid PR-review session state`。`save` は `pr_repository` を渡して保存先を計算し直す。`legacy_review` は `os.path.lexists(repo / legacy)` のときだけ返し、中身を読まない。

- [ ] **Step 5: 通ることを確かめる**

Run: `uv run pytest .agents/skills/pr-review/tests/test_pr_review_workspace.py -q`
Expected: 全件 PASS

- [ ] **Step 6: Commit**（`fix(pr-review): pin the PR repository in review sessions`）

### Task 2: inspect・abandon を所属で照合する

**Files:**
- Modify: `.agents/skills/pr-review/scripts/pr_review_workspace.py`（`locate_attempt`・`inspect_attempt`・`abandon_attempt`・`add_attempt_arguments`）
- Test: `.agents/skills/pr-review/tests/test_pr_review_workspace.py`

**Interfaces:**
- Consumes: Task 1 の `normalize_pr_repository`、journal の `pr_repository`
- Produces: `inspect`・`abandon` の必須 `--pr-repo`（argparse の `pr_repo`）。`locate_attempt(repo, temp_root_value, pr_repository, pr_number, attempt_id)`

**テストの要否:** 必要。照合の分岐を実行で確かめる。

- [ ] **Step 1: 既存の `attempt_args` に `pr_repo=PR_REPO` を足し、テストを書く**

```python
def test_inspect_and_abandon_refuse_another_pr_repository(...):
    # PR_REPO で作った試行を pr_repo="orange3134/resoloop" で inspect/abandon → "does not match"、session と worktree は残る

def test_abandon_keeps_a_journal_without_pr_repository(...):
    # journal の started から pr_repository を消す → abandon が "does not match"、session は残る
```

- [ ] **Step 2: 失敗を確かめる** — Run: `uv run pytest .agents/skills/pr-review/tests/test_pr_review_workspace.py -q -k "inspect or abandon"` / Expected: FAIL
- [ ] **Step 3: 実装する**（ヘッダーの照合に `pr_repository` を足す。エラー文は `create journal does not match this repository, PR and session directory` を保つ）
- [ ] **Step 4: 通ることを確かめる** — Run: 同じファイル全体 / Expected: 全件 PASS
- [ ] **Step 5: Commit**（`fix(pr-review): match create attempts by PR repository`）

### Task 3: 読み取り専用の sessions サブコマンド

**Files:**
- Modify: `.agents/skills/pr-review/scripts/pr_review_workspace.py`（`sessions` と parser）
- Test: `.agents/skills/pr-review/tests/test_pr_review_workspace.py`

**Interfaces:**
- Consumes: Task 1 の `load_state`、既存の `require_main_checkout`
- Produces: `sessions --repo <path>` → `{"main_root": str, "sessions": [{"session_dir", "worktree", "pr_repository", "pr_number", "head_branch", "commit", "pr_state", "removable", "reason"}]}`。対象は `git worktree list --porcelain -z` の登録のうち、basename が `worktree` で親の名前が `pr-review-` で始まるもの。gh は `gh pr view <N> --repo <owner/repo> --json number,state`（同じ組は 1 回だけ呼ぶ）

**テストの要否:** 必要。片付けの候補の判断を実行で確かめる。偽の gh は `tmp_path/bin/gh` に置き、`FAKE_GH_STATES`（`{"owner/repo#N": "STATE"}` の JSON ファイル）を読む。無い組は終了コード 1。

- [ ] **Step 1: テストを書く**

```python
@pytest.mark.parametrize(("fork_state", "upstream_state"), [("MERGED", "OPEN"), ("OPEN", "MERGED")])
def test_sessions_keep_the_open_pr_when_fork_and_upstream_share_number_branch_and_head(...):
    # 同じ repo に usaturn/resoloop#11 と orange3134/resoloop#11（同じ branch・commit）の session
    # OPEN 側は removable False・reason に "open"、MERGED 側だけ True。実行前後で worktree list とファイルが同じ

def test_sessions_keep_a_version6_session(...)           # removable False、reason に "no PR repository"
def test_sessions_keep_when_gh_fails(...)                # 状態の無い組と gh の無い PATH → False
def test_sessions_keep_when_gh_reports_another_number(...)
def test_sessions_keep_a_session_without_state(...)      # session.json を消す → False
def test_sessions_keep_a_locked_worktree(...)            # git worktree lock → False
```

- [ ] **Step 2: 失敗を確かめる** — Run: `uv run pytest .agents/skills/pr-review/tests/test_pr_review_workspace.py -q -k sessions` / Expected: FAIL（サブコマンドが無い）
- [ ] **Step 3: 実装する**（`load_state` の例外は reason にして残す。state の `main_root` と worktree が登録と一致することも確かめる）
- [ ] **Step 4: 通ることを確かめる** — Run: 同じファイル全体 / Expected: 全件 PASS
- [ ] **Step 5: Commit**（`feat(pr-review): report which review sessions belong to ended PRs`）

### Task 4: pr-review の SKILL.md

**Files:**
- Modify: `.agents/skills/pr-review/SKILL.md`（description、規約の 56・84・85 行目付近、手順 2 の共通 context・ref・create・inspect・abandon・結果の取得、手順 9 の報告、セルフチェック）
- Test: `.agents/skills/pr-review/tests/test_pr_review_skill_contract.py`

**Interfaces:**
- Consumes: Task 1〜2 の CLI（`--pr-repo`、結果の `legacy_review`）
- Produces: シェル変数 `PR_REPOSITORY`（共通 context のブロック）、`PR_REF`・`PR_HEAD`（`+pull/$PR_NUMBER/head:` を含む fetch のブロック。1 つだけ）、`LEGACY_REVIEW`

**テストの要否:** fetch のブロックは必要（実行して ref が分かれることを確かめる）。文面の変更には作らない。

- [ ] **Step 1: テストを書く**

```python
def test_fork_and_upstream_fetches_keep_separate_refs(tmp_path):
    # build_parent_with_fork の fork に、fork 用と上流用の bare repo を用意し、両方に refs/pull/11/head（別の commit）を置く
    # 共通 context のブロック → fetch のブロックを fork の URL で実行し、続けて上流の URL で実行
    # fetch のハーネスだけ GIT_CONFIG_COUNT の url.<bare>.insteadOf で GitHub の URL を bare に向ける
    assert fork_ref == "refs/pr-review/repos/usaturn/resoloop/11"
    assert upstream_ref == "refs/pr-review/repos/orange3134/resoloop/11"
    # 2 回目の後も fork_ref は fork の commit、各 PR_HEAD は各 bare の commit
```

- [ ] **Step 2: 失敗を確かめる** — Run: `uv run pytest .agents/skills/pr-review/tests/test_pr_review_skill_contract.py -q -k separate_refs` / Expected: FAIL（fetch のブロックが無い）
- [ ] **Step 3: SKILL.md を Spec の「取得 ref」のとおりに変える**（fetch のブロックは `|| exit 1` で止める）
- [ ] **Step 4: 確かめる** — Run: `uv run pytest .agents/skills/pr-review -q` / Expected: 全件 PASS
- [ ] **Step 5: Commit**（`fix(pr-review): fetch and save reviews per PR repository`）

### Task 5: 片付け・review-fix-planning・AGENTS.md

**Files:**
- Modify: `.agents/skills/repo-cleanup-after-merge/SKILL.md`（frontmatter、手順 1・5・6・11）
- Modify: `.agents/skills/repo-cleanup-after-merge/evals/evals.json`（id を 1 つ足す）
- Modify: `.agents/skills/review-fix-planning/SKILL.md`（「第1引数の解決」）、`.agents/skills/review-fix-planning/evals/evals.json`（`#300` の eval の期待値）
- Modify: `AGENTS.md`（「コミットしないファイルの置き場所」の PR レビュー結果の行）

**テストの要否:** 不要。SKILL.md・eval・AGENTS.md の文面の変更。判断はTask 3 のテストと、下の行動比較で確かめる。

- [ ] **Step 1: RED** — 変更前の repo-cleanup-after-merge の SKILL.md を `tmp/agents/issue-146.zw5ywlyu/red-SKILL.md` に写し、場面（fork の root で、fork の PR #9 が MERGED・上流の PR #6 が OPEN、両方の `/tmp/pr-review-*` が同じ branch・head、version 6 の session も 1 つ）を `scenario.md` に書く。新しいサブエージェント 1 体に、コマンドを実行しない机上の判断として、各 worktree を消すか残すかを答えさせる
- [ ] **Step 2: 文面を変える**（Spec の「片付け」「その他の参照」のとおり）
- [ ] **Step 3: GREEN** — 変更後の SKILL.md と、場面に合わせた `sessions` の出力を渡し、同じ指示で新しいサブエージェント 1 体に解かせる。Expected: 上流 OPEN と version 6 の worktree を残し、理由を報告する。fork の MERGED だけを候補にする
- [ ] **Step 4: 確かめる** — Run: `uv run pytest .agents/skills/repo-cleanup-after-merge .agents/skills/review-fix-planning -q && git diff --check` / Expected: 全件 PASS、出力なし
- [ ] **Step 5: Commit**（`fix(repo-cleanup-after-merge): retire review sessions by their PR repository`）

### Task 6: 全体の検証とレビュー

- [ ] **Step 1:** README の「テスト」のワールド以外の 3 コマンドを実行する（`bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`uv run pytest tests/skills .agents/skills .agents/scripts`）。Expected: 終了コード 0。失敗したら基準版と比べ、新しい失敗だけを systematic-debugging で調べる
- [ ] **Step 2:** ブランチ全体のレビューを新しいサブエージェントに依頼する（Spec・Plan・`git diff origin/main...HEAD`・Global Constraints を渡す）。致命的な指摘だけを直す
- [ ] **Step 3:** Spec の「調査・実行記録」と Plan の「完了」に結果を書き、commit

### Task 7: 公開

- [ ] **Step 1:** Issue の状態と競合（同じ Issue の open PR・予約 ref・branch）を調べ直す
- [ ] **Step 2:** `SHA="$(bash /workspaces/reso-world/scripts/scan-before-push.sh -C <worktree>)" && [ -n "$SHA" ] && git -C <worktree> push origin "${SHA:?}:refs/heads/fix/issue-146-pr-review-repo-identity"`
- [ ] **Step 3:** `gh pr create --repo usaturn/create-reso-world --base main --head fix/issue-146-pr-review-repo-identity`（本文に `Closes #146`、決定と理由、実行方式と理由、検証と結果、作業時間）。CI は private で停止しているので確かめない

## 実行方式

`superpowers:executing-plans`（inline）。Task 1〜3 は同じ helper とテストのファイルへの逐次の変更で、Task 4〜5 はその CLI を前提にする。行動比較（Task 5）とブランチ全体のレビュー（Task 6）だけを、新しい文脈のサブエージェントに任せる。

## 実行予算

- Issue 全体の能動時間: 240 分（05:40Z に ledger を開始。Task 7 つ、helper の変更 3 つと SKILL.md 3 本。#121・#128 の実績は 15〜90 分だが、今回は helper のロジックと複数スキルにまたがる）
- phase の目安: 準備・設計 30 分（済み）、Task 1〜3 で 90 分、Task 4〜5 で 60 分、検証・レビュー 40 分、公開・記録 20 分
- worker: 行動比較とレビューのサブエージェントは読み取り専用。Claude Code の Agent ツールは task_watch で起動できないので、事前宣言した打ち切りは使わず完了通知を待つ。1 体の目安は 5 分、15 分を超えたら stall として報告する
- 再試行: 同じ失敗の再試行は 1 回まで（信頼性の失敗）。安全の失敗は全体停止
- checkpoint: phase の境界、予算の 50%（120 分）・100%（240 分）、worker の失敗の直後。100% は停止して報告する
- 縮小・方法変更の候補: 行動比較を GREEN の 1 体だけにする。review-fix-planning の変更を `#番号` の解決だけに絞る。`sessions` の gh 呼び出しが不安定なら、gh の結果を入力で受け取る形に変える

## Contingency

- 既存のテストが失敗したら: 基準版（302 件成功、`tmp/agents/issue-146.zw5ywlyu/baseline-skills.log`）と比べ、新しい失敗だけを調べる。#128 の不安定なテストは既知
- 行動比較の GREEN で誤りが残ったら: 文面を直して 1 回だけ再実行し、なお残れば停止して報告する
- 競合（同じ Issue の PR・予約）が見つかったら: push・PR をせずに停止する
