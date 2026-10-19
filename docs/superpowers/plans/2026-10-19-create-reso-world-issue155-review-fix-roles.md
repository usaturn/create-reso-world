# Issue #155 review-fix-planning の役割の実行と最終化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

- 状態: `draft`（内容の承認は記録しない）
- 実行許可: Spec の「実行許可」のとおり（`/issue-to-pr #155` と「`/issue-to-pr #155 --merge` 相当で進めて」）

**Goal:** review-fix-planning が `run_roles.py` で修正・自己レビュー・修正の確認を runner で実行し、`finalize.py` で修正不要の最終化を行い、判断の記録を読み書きできるようにする。

**Architecture:** 移植元 `usaturn/agent-workspace@415b366` の `run_roles.py`・`finalize.py`・記録付きの `upsert_pr_comment.py` を、名前と入出力を保って移植先の helper（#149・#152・#153・#154）に接続する。`tools.workspace` の代わりに CI とマージの範囲の固定値を持ち、create-reso-world の PR の結論 2 のために `--spec-commit` を足す。SKILL.md は判断の規則を残し、手段の段だけを差し替え、詳しい手順を `references/` に置く。

**Tech Stack:** Python 3.14（uv、ルートの `pyproject.toml`）、pydantic、pytest、`gh` CLI（テストでは偽物）、git。

**Spec:** `docs/superpowers/specs/2026-10-19-create-reso-world-issue155-review-fix-roles-design.md`

移植元のファイルは `/workspaces/reso-world/tmp/agents/issue-155.8zy2dh0_/src-aw`（checkout の無い clone）から `git -C <そこ> show 415b3669dc06d045fe81fb15be7d82f8864c5cef:<path>` で読む。以下 `SRC=415b3669dc06d045fe81fb15be7d82f8864c5cef` とする。

## Global Constraints

- 変えてよいのは `.agents/skills/review-fix-planning/`（SKILL.md の「第1引数の解決」の節と手順 2 のレビューディレクトリ・`PR_REPO` の決め方を除く）、`.devcontainer/agent-runner.toml` の `[workflows.fix.assignments.*]`、この Plan と Spec だけ
- `.agents/scripts/review_*.py`・`tools/`・`.agents/skills/pr-review/`・`review-verify/`・`pr-review-fix-loop/`・`AGENTS.md`・`.agents/review-records.md`・`review-findings.md` は変えない
- 判断基準（致命的な指摘だけ・3 区分）、三択の結論、修正後の自己レビューは最大 1 回（後の修正は再レビューせずに記録）を変えない（Spec D-1）
- `run_roles.py`・`finalize.py` の名前・引数・出力・終了コードは移植元と同じにする（追加は `finalize.py --spec-commit` と結果の `spec_commit` だけ。`--registry` は無くす）
- `upsert(pr, repo, model_name, markdown, *, runner=None, record=None)` の呼び方を保つ
- Python はリポジトリの方法で動かす: `uv run --project <checkout> --locked python ...`、テストは `uv run pytest ...`。`python3` を直接使わない
- テストは偽の `gh`・偽の adapter・一時の Git だけを使う。実際の PR・ネットワーク・モデルを使わない。`AGENTS.md`「テストの採用基準」の作らない型（文言の照合、運用で変わる値の写し）を書かない
- 文書は日本語。`AGENTS.md`「日本語表現」の言い換え（契約・原子的・製品・着地・正本・巡・席・実行器を使わない）に従う
- commit の末尾に `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` を付ける。stage は明示したパスだけ

## Review Focus

1. 親のリポジトリに、ディレクトリが消えた worktree の登録（prunable）が残っている → `run_roles.py` は checkout の監査で起動前に止まる（終了コード 1、`category: environment`、1 回枠を消費しない）。SKILL.md はこれを結論 3（環境）として、報告されたパスを書くよう案内する（Task 3 の移植するテスト `test_environment_preflight_does_not_launch_or_consume_review` が固定する）
2. `gh api user --jq '.login // empty'` の出力は末尾に改行が付く → 前後の空白を除いた値を login にし、空なら止まる（Task 2 の `test_authenticated_login_strips_newline_and_rejects_blank`）
3. GitHub の比較で、Spec の commit が名前の変更・サブディレクトリ・2 ファイル以上・Markdown 以外・2 commit 以上・親の違い・base より後ろを含む → `finalize.py --spec-commit` はマージせずに `environment:` で止まる（Task 4 の `test_spec_commit_compare_must_be_one_spec_file_on_the_reviewed_head`）
4. 記録付きの投稿を、記録を作り直した（`recorded_at` だけ違う）状態で再実行する → 同じサイクルの自分のコメントを更新し、重複を作らない。`finalize.py --spec-commit` では、投稿済みの記録と食い違えば止まる（Task 2・Task 4 のテスト）
5. 状況の本文が 65,536 文字を超える → helper が投稿せずに拒否する（`review_records.compose_comment` の検査）。SKILL.md は「対応しない」を判断 ID と一行の理由に短くして投稿し直す手順を示す（Task 5 の文書。挙動は既存の `review_records.py` のテストが固定している）

---

## File Structure

| ファイル | 責務 | Task |
| --- | --- | --- |
| `.devcontainer/agent-runner.toml` | `[workflows.fix.assignments.*]` を足す | 1 |
| `.agents/skills/review-fix-planning/scripts/upsert_pr_comment.py` | 状況コメントの投稿（記録付き・記録なし）、認証済みの login | 2 |
| `.agents/skills/review-fix-planning/tests/test_upsert_pr_comment.py` | 上のテスト | 2 |
| `.agents/skills/review-fix-planning/scripts/run_roles.py`（新規） | 役割の実行と 1 回枠の予約 | 3 |
| `.agents/skills/review-fix-planning/tests/test_run_roles.py`（新規） | 上のテスト | 3 |
| `.agents/skills/review-fix-planning/scripts/finalize.py`（新規） | 修正不要の最終化 | 4 |
| `.agents/skills/review-fix-planning/tests/test_finalize.py`（新規） | 上のテスト | 4 |
| `.agents/skills/review-fix-planning/references/execution.md`（新規） | 役割の実行・最終化の手順 | 5 |
| `.agents/skills/review-fix-planning/references/round-records.md`（新規） | 判断の記録の作り方と投稿 | 5 |
| `.agents/skills/review-fix-planning/SKILL.md` | 手順・結論・自己レビュー・投稿の接続 | 6 |
| `.agents/skills/review-fix-planning/evals/`（追加） | 行動の評価の packet・結果、`evals.json` の場面 | 7 |

## 実行方式

- Task 2・3・4（移植のコードとテスト）は `superpowers:subagent-driven-development`。移植元という具体的な基準があり、入出力が下の Interfaces で決まっていて、文脈を子に渡しきれる。Task ごとに実装の担当と、仕様・品質のレビューの担当を分ける。Task 4 は Task 2 の API を使うので、Task 2 の後に行う。Task 3 は Task 2 と別のファイルなので、Task 2 の後に続けて行う（同じ worktree で同時に commit させない）
- Task 1・5・6・7・8 は controller が自分で行う（`superpowers:executing-plans` の作法）。SKILL.md と references は判断の規則との整合が要で、Spec の判断と既存の文面の全体を持つ controller のほうが誤りにくい。Task 7 は新しいコンテキストのサブエージェントを controller が起動して採点する
- 実装の担当はテストを同期で実行し、終わってからターンを終える。controller は担当の完了通知を待ってから次の Task に進む

## 実行予算

- 全体の能動時間の予算: 600 分。根拠: 移植のコード約 1,200 行・テスト約 1,700 行・文書 2 本と SKILL.md の改修・行動の評価、PR の後のサイクル（最大 3 回 ×（レビュー最大 45 分＋計画・修正 60 分））。着手（10:44Z）から ledger の開始（11:11Z）までの約 27 分は ledger に含まれない
- phase の目安: 準備（Spec・Plan）60 分、実装（Task 1〜6）240 分、評価（Task 7）60 分、検証（Task 8）60 分、PR とサイクル 210 分
- worker: 実装の担当は 1 Task 60 分を目安にし、30 分で実質の進捗（コミット・テストの通過）が無ければ controller が状況を確かめる。Claude Code の `Agent` は `task_watch.py` で止められないので、これは目安で、止める宣言ではない。評価の担当は読み取りだけで 1 回 20 分を目安にする。runner のレビュアーは雛形の役割の期限（inspect 2700 秒）に従う
- 再試行: 同じ失敗の再試行は 1 回まで（`issue_budget.py` の既定）。安全の失敗は再試行しない
- checkpoint: phase の境界、予算の 50%（300 分）・100%（600 分）、worker の失敗の直後。ledger は `/workspaces/reso-world/tmp/agents/issue-155.8zy2dh0_/budget.jsonl`
- 縮小・切り出し・方法変更の候補: (1) 行動の評価は、時間が足りなければ 1 packet・各条件 1 回に絞る（Spec に記録）。(2) サイクルが予算を超えそうなら、進行中のサイクルを終えて未マージで報告する。(3) runner のレビュアーが環境の理由で起動できなければ、止まって報告する（レビュアーを勝手に減らさない）

## 検証の入口

- 関連: `uv run pytest .agents/skills/review-fix-planning`、`env AGENT_RUNNER_DEPTH=1 uv run pytest .agents/skills/review-fix-planning`（runner の担当の中でも通ること）
- 全体（`README.md`「テスト」）: `uv run pytest tests/skills .agents/skills .agents/scripts tools`、`bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`
- ベースライン（`8083a85`、2026-10-19）: pytest `2876 passed`、`run-tests.bash` 33 本 PASS、`check-layout.sh` PASS（ログ `/workspaces/reso-world/tmp/agents/issue-155.8zy2dh0_/baseline/`）

---

### Task 1: 雛形の fix の割り当て

**Files:**
- Modify: `.devcontainer/agent-runner.toml`（末尾の `[workflows.review.assignments.inspect]` の後）

**Interfaces:**
- Produces: `workflows.fix.assignments` の `implement`（`["claude-opus"]`）・`self-review`（`["self"]`）・`fix-check`（`["self"]`）。Task 3 の `run_roles.py` の既定の雛形

テスト: 不要（雛形の設定値だけの変更。`AGENTS.md`「テストの採用基準」）。代わりに実際の雛形を読む確認を行う。

- [ ] **Step 1: 3 つの節を足す。** 直前に 1 行のコメント（「review-fix-planning の run_roles.py が使う担当（ボードの D-13）。self は司令塔が実行する」）を置く
- [ ] **Step 2: 雛形を読めることを確かめる**

```bash
EMPTY=$(mktemp -d)/personal.toml && : > "$EMPTY" && \
uv run --project . --locked python -m tools.agent_runner --template .devcontainer/agent-runner.toml --config "$EMPTY" check
```

Expected: 終了コード 0、JSON の一覧が出る（`{"error": ...}` でない）

- [ ] **Step 3: commit**（`feat(agent-runner): add the review-fix workflow assignments (#155)`）

### Task 2: `upsert_pr_comment.py` の記録付きの投稿と認証済みの login

**Files:**
- Modify: `.agents/skills/review-fix-planning/scripts/upsert_pr_comment.py`
- Modify: `.agents/skills/review-fix-planning/tests/test_upsert_pr_comment.py`

**Interfaces:**
- Consumes: `.agents/scripts/review_records.py`（`Path(__file__).resolve().parents[4]` から importlib で読む。`agent_id_for`・`AGENT_MARKER_PREFIX`・`AGENT_MARKER_PATTERN`・`ROUND_MARKER_PATTERN`・`round_marker`・`record_markers_in`・`TRUSTED_ASSOCIATIONS`・`comments_from_api`・`validate_record`・`compose_comment`・`read_state`・`check_against`・`extract_record`・`DECISION_ID`・`RecordError`）
- Produces（Task 4 が使う）:
  - `records`（読み込んだ `review_records` モジュール）、`CommentError`、`GhRunner`、`Runner`（Protocol）、`run_gh(args, *, runner, input_text=None) -> str`、`load_json(text, what) -> object`
  - `authenticated_login(runner: Runner) -> str`: `gh api user --jq '.login // empty'` を実行し、前後の空白を除いた値を返す。終了コードが 0 でない・空なら `CommentError`
  - `view_pr(pr: int, repo: str, runner: Runner, fields: Sequence[str] = ("url", "number")) -> dict[str, object]`
  - `list_comments(repo: str, pr: int, runner: Runner) -> list[dict[str, Any]]`（`records.comments_from_api` で `id`・`body`・`author`・`author_association` に整える）
  - `find_round_comment_id(comments, record, trusted_login: str) -> int | None`
  - `find_own_comment_id(comments, model_name: str, trusted_login: str) -> int | None`
  - `_checked_record(record, model_name: str, markdown: str) -> tuple[dict[str, Any], str]`
  - `_round_target(checked, comments, trusted_login: str) -> int | None`（`records.read_state(..., trusted_login=trusted_login)` と `check_against`）
  - `upsert(pr, repo, model_name, markdown, *, runner=None, record=None) -> dict[str, Any]`（戻り値は今と同じ `action`・`comment_id`・`url` など）
- CLI: 既存の引数に `--records-file <path>` を足す。拒否は標準エラー出力に書いて終了コード 64

移植元 `$SRC:.agents/skills/review-fix-planning/scripts/upsert_pr_comment.py` を基にし、次を足す。

- 信頼の判定 `_trusted(comment, trusted_login)`: `author_association` が `records.TRUSTED_ASSOCIATIONS` にある、または `trusted_login` が空でなく `comment["author"] == trusted_login`
- `upsert` は、記録付き・記録なしのどちらでも、PR の解決の後・コメントの取得の前に `authenticated_login` を呼び、その値を `find_own_comment_id`・`_round_target` に渡す

- [ ] **Step 1: 失敗するテストを書く。** 移植元 `$SRC:.agents/skills/review-fix-planning/tests/test_upsert_pr_comment.py` の記録付きの場面（記録の検査で通信の前に止まる、`planner.model` と `--model-name` の不一致、PR が open でない・head が違う、同じサイクルの更新、別のエージェント・番号の大きいサイクルで止まる、2 件以上で止まる、記録なしの本文にサイクルのマーカーがあれば拒否）を移し、偽の `gh` に `api user` の応答を足す。次の場面を足す

```python
def test_authenticated_login_strips_newline_and_rejects_blank() -> None:
    # gh の --jq の出力の末尾の改行を含めない。空・空白だけ・失敗は止まる
    assert mod.authenticated_login(FakeGh(login="usaturn\n")) == "usaturn"
    for bad in (FakeGh(login=""), FakeGh(login="  \n"), FakeGh(login_fails=True)):
        with pytest.raises(mod.CommentError):
            mod.authenticated_login(bad)

def test_record_less_upsert_updates_own_login_comment_and_ignores_untrusted() -> None:
    # CONTRIBUTOR でも認証済み利用者自身のコメントは更新する。別の CONTRIBUTOR の同じマーカーは更新しない
    ...  # 自分の login の CONTRIBUTOR のコメント → PATCH、他人の CONTRIBUTOR のコメントだけ → POST

def test_records_post_reads_prior_round_written_by_own_contributor_login() -> None:
    # 上流の PR（usaturn が CONTRIBUTOR）で、前のサイクルの自分の記録を照合に使う（#169）
    ...  # 前のサイクルの fix の判断を落とした記録は、照合で拒否される

def test_login_failure_stops_before_any_comment_write() -> None:
    gh = FakeGh(login_fails=True, ...)
    with pytest.raises(mod.CommentError):
        mod.upsert(..., runner=gh)
    assert not [call for call in gh.calls if "--method" in call[0]]
```

既存のテストは、偽の `gh` のコメントに `author_association`（または `user.login`）を足して、更新の対象を明示する。

- [ ] **Step 2: テストが失敗することを確かめる**

Run: `uv run pytest .agents/skills/review-fix-planning/tests/test_upsert_pr_comment.py -q`
Expected: 新しい場面が FAIL（`authenticated_login` が無い、`record` を受け付けない など）

- [ ] **Step 3: 実装する。** 移植元の記録付きの投稿を移し、上の信頼の判定と login の取得を足す。マーカーは行全体の一致で比べる
- [ ] **Step 4: テストが通ることを確かめる**

Run: `uv run pytest .agents/skills/review-fix-planning/tests/test_upsert_pr_comment.py .agents/skills/review-fix-planning/tests/test_review_fix_planning_skill_contract.py -q`
Expected: すべて PASS

- [ ] **Step 5: commit**（`feat(review-fix-planning): post round records and trust the authenticated login (#155)`）

### Task 3: `run_roles.py`

**Files:**
- Create: `.agents/skills/review-fix-planning/scripts/run_roles.py`
- Create: `.agents/skills/review-fix-planning/tests/test_run_roles.py`

**Interfaces:**
- Consumes: `tools.agent_runner`（`Config`・`ConfigError`・`RunnerError`・`Workflow`・`load_config`・`resolve_config_path`・`run_workflow`）、`tools.agent_runner.adapters`（`Adapter`・`load_adapter`）、`tools.agent_runner.config.validate_config`、`tools.agent_runner.models.BatchResult`、`tools.agent_runner.workspace`（`CheckoutAuditError`・`WorkspaceError`・`git_common_dir`・`require_auditable_checkouts`・`resolve_revision`）、review-verify の `scripts/dispatch.py`（`load_review_findings`・`FixInput`・`check_review_directories`・`SKILL`・`time_limits`・`snapshot_review`・`review_changes`・`observed_verifier`・`failure_category`・`assigned_externally`・`fix_check_write_exceptions`）、`.agents/scripts/review_target.py`（`default_parent_root`・`repository_reviews_root`・`TargetError`）、pr-review の `scripts/review_run.py`（`helper_write_exceptions`）、Task 1 の雛形
- Produces（#156 と SKILL.md が使う）: 移植元と同じ `RoleInputError`・`PullRequest`・`RoleInput`・`project(config, phase) -> Config`・`reject_dsh_review_agents(config) -> None`・`reject_codex_review_agents(config, workflow: str, roles: Sequence[str]) -> None`・`reserve_review(path, data) -> None`・`write_exceptions(config, data) -> tuple[str, ...]`・`fix_context(request, data, config) -> dict`・`run(config, phase, request, output_dir, *, planning_file=None, fix_input=None, adapter_loader=load_adapter) -> BatchResult`・`failure_reason(error) -> str`・`main(argv=None) -> int`、CLI の引数・出力・終了コード（Spec の「インターフェース」）。加えて `READ_ONLY_SANDBOX_RUNTIMES = frozenset({"codex"})` と `assigned_read_only_sandbox(config, workflow, role) -> bool`（一次担当と fallback、`self` を除く）

移植元 `$SRC:.agents/skills/review-fix-planning/scripts/run_roles.py` を基にする。適応は次の 3 点だけ。

- `reject_codex_review_agents` は `verifier.assigned_read_only_sandbox` の代わりに、このファイルの `assigned_read_only_sandbox` を使う（移植先の review-verify に無いため。Spec D-2）
- モジュールの説明に、移植元・#731 の判定をここに置いた理由を 1〜2 行で書く
- それ以外の名前・文・順序は移植元のまま（`--template` の既定は `ROOT / ".devcontainer/agent-runner.toml"`）

- [ ] **Step 1: 失敗するテストを書く。** 移植元 `$SRC:.agents/skills/review-fix-planning/tests/test_run_roles.py` を移す。変える点: PR の slug を `usaturn/create-reso-world`（番号 900）にし、`test_external_review_roles_list_their_write_exceptions_with_the_role` の期待するパスを移植先の値（`f"{parent}/reviews/usaturn/create-reso-world/#900-*"`、venv は `mod.ROOT / ".venv"`）にする。期待する行の数え方は `review_run.helper_write_exceptions` の移植先の戻り値に合わせる
- [ ] **Step 2: テストが失敗することを確かめる**

Run: `uv run pytest .agents/skills/review-fix-planning/tests/test_run_roles.py -q`
Expected: 収集の段で FAIL（`run_roles.py` が無い）

- [ ] **Step 3: 実装する**（上の適応だけ）
- [ ] **Step 4: テストが通ることを確かめる**

Run: `uv run pytest .agents/skills/review-fix-planning/tests/test_run_roles.py -q && env AGENT_RUNNER_DEPTH=1 uv run pytest .agents/skills/review-fix-planning/tests/test_run_roles.py -q`
Expected: どちらも PASS

- [ ] **Step 5: 実際の雛形で CLI の入口を確かめる**（テストにしない。費用の無い self の割り当て）: 一時の Git、v2 の工程の記録の仮の版、確認済みの一覧（v1 の最小）、fix-input を作り、`--phase self-review --config <空のファイル>` で実行する。Expected: 終了コード 0、標準出力の `pending_self` が `["self-review", "fix-check"]`、工程の記録に `pre_push_review` が 1 件。同じ入力で 2 回目は終了コード 2、標準エラー出力に `already reserved`。作ったものは確認の後に消す
- [ ] **Step 6: commit**（`feat(review-fix-planning): run the fix roles and reserve the single self-review (#155)`）

### Task 4: `finalize.py`

**Files:**
- Create: `.agents/skills/review-fix-planning/scripts/finalize.py`
- Create: `.agents/skills/review-fix-planning/tests/test_finalize.py`

**Interfaces:**
- Consumes: Task 2 の `upsert_pr_comment.py`（`records`・`CommentError`・`GhRunner`・`run_gh`・`load_json`・`view_pr`・`list_comments`・`authenticated_login`・`_checked_record`・`_round_target`・`upsert`）
- Produces（#156 と SKILL.md が使う）: `finalize(record, markdown, checks, *, runner=None, spec_commit: str | None = None) -> dict[str, Any]`、`main(argv=None) -> int`、CLI（`--record-file`・`--body-file`・`--checks-file`・`--result-file`・`--spec-commit`）、結果の JSON（Spec の「インターフェース」）。定数 `CI_REQUIRED: Mapping[str, bool] = {"usaturn/create-reso-world": False, "usaturn/resoloop-meshy": False, "usaturn/resoloop": True}`、`MERGEABLE_REPOSITORIES = frozenset({"usaturn/create-reso-world", "usaturn/resoloop"})`、`SPEC_REPOSITORY = "usaturn/create-reso-world"`、`SPEC_DIRECTORY = "docs/superpowers/specs/"`

移植元 `$SRC:.agents/skills/review-fix-planning/scripts/finalize.py` を基にし、次を変える。

- `tools.workspace` の import・`registry_path`・`--registry` を無くし、`check_ci(view, repo)` は `CI_REQUIRED.get(repo, True)` が偽なら確かめない
- 入力の検査（記録・本文・検証の記録）の直後、GitHub に問い合わせる前に、`repo not in MERGEABLE_REPOSITORIES` なら `Stop("permission: マージしてよい範囲（usaturn/create-reso-world・usaturn/resoloop）の外の PR")`
- `round_target` の前に `poster.authenticated_login(active)` で login を取り、`poster._round_target(checked, comments, login)` に渡す（取得の失敗は `external:`）
- `spec_commit` があるとき: 完全な SHA で `reviewed_head` と違うこと、`repo == SPEC_REPOSITORY` を、問い合わせの前に確かめる（違えば `environment:`／`permission:`）。PR の head の期待値を `spec_commit` にする。`gh api repos/<repo>/compare/<reviewed_head>...<spec_commit>` を読み、`status == "ahead"`・`ahead_by == 1`・`behind_by == 0`・`commits` が 1 件で `sha == spec_commit`・`parents` の sha が `[reviewed_head]`、`files` が 1 件で `filename` が `SPEC_DIRECTORY` の直下の `*.md`（`/` をそれ以上含まない）・`status` が `added` か `modified`、を確かめる。違えば `Stop("environment: Spec の commit が検証した HEAD の上の Spec 1 ファイルだけの変更ではない")`。投稿はせず、このサイクルの自分のコメントの記録（`posted_record`）が渡した記録と同じことを求める（違えば `environment:`）。マージは `--match-head-commit spec_commit`、マージ後は `headRefOid == spec_commit`。結果に `spec_commit` を入れる

- [ ] **Step 1: 失敗するテストを書く。** 移植元 `$SRC:.agents/skills/review-fix-planning/tests/test_finalize.py` を移す。`tools.test_support.registry`・`tools.workspace` と `fixture_registry` を外す。`REPO` を `usaturn/create-reso-world`、公開の CI を確かめるリポジトリを `usaturn/resoloop` にする。偽の `gh` に `api user`（login）と `api repos/.../compare/...` の応答を足す。移植元の `test_unregistered_repository_requires_ci`・`test_unreadable_registry_stops_before_network` は外し、次を足す

```python
@pytest.mark.parametrize("repo", ["usaturn/resoloop-meshy", "orange3134/resoloop", "other/repo"])
def test_repository_outside_the_merge_scope_stops_before_network(repo: str) -> None:
    gh = FakeGh(repo=repo); value = record(); value["pr"]["repository"] = repo
    result = mod.finalize(value, "状況", checks(), runner=gh)
    assert result["outcome"] == "stopped" and result["stop_reason"].startswith("permission:")
    assert gh.calls == []

def test_create_reso_world_ci_is_not_required_but_resoloop_ci_is() -> None: ...

def test_spec_commit_merges_the_spec_head_after_the_record_was_posted() -> None:
    # 記録は reviewed_head のうちに投稿済み、PR の head は Spec の commit
    ...  # writes は ("pr","merge") と ("issue","close") だけ。merge の --match-head-commit は SPEC_HEAD。result["spec_commit"] == SPEC_HEAD

@pytest.mark.parametrize("mutation", ["two_files", "renamed", "subdirectory", "not_markdown", "two_commits", "wrong_parent", "behind"])
def test_spec_commit_compare_must_be_one_spec_file_on_the_reviewed_head(mutation: str) -> None:
    ...  # outcome stopped、stop_reason は environment:、writes は空

@pytest.mark.parametrize("posted", ["none", "different"])
def test_spec_commit_requires_the_identical_record_already_posted(posted: str) -> None: ...

@pytest.mark.parametrize("bad", ["other_repo", "same_as_reviewed_head", "short_sha"])
def test_invalid_spec_commit_stops_before_network(bad: str) -> None: ...

def test_login_failure_is_external_and_does_not_post_or_merge() -> None: ...
```

- [ ] **Step 2: テストが失敗することを確かめる**

Run: `uv run pytest .agents/skills/review-fix-planning/tests/test_finalize.py -q`
Expected: 収集の段で FAIL（`finalize.py` が無い）

- [ ] **Step 3: 実装する**（上の変更だけ。ほかの順序・文は移植元のまま）
- [ ] **Step 4: テストが通ることを確かめる**

Run: `uv run pytest .agents/skills/review-fix-planning -q`
Expected: すべて PASS

- [ ] **Step 5: commit**（`feat(review-fix-planning): finalize no-fix PRs with fixed CI and merge scopes (#155)`）

### Task 5: references（`execution.md`・`round-records.md`）

**Files:**
- Create: `.agents/skills/review-fix-planning/references/execution.md`
- Create: `.agents/skills/review-fix-planning/references/round-records.md`

テスト: 不要（文書だけ）。代わりに、文書のコードブロックの引数が Task 2〜4 の CLI と一致することと、参照先のファイルの実在を確かめる。

- [ ] **Step 1: `execution.md` を書く。** 移植元 `$SRC:.agents/skills/review-fix-planning/references/execution.md` を基に、移植先に直す: uv は `uv run --project "$TOPLEVEL" --locked python`、パスは移植先のもの、採否の語は 3 区分（H・D1・N・Hold を使わない）、自己レビュー後の必須の修正は「直して検証し、再レビューせずに記録する」（移植元の停止にしない）、fix-check の独立の保存先と `REVIEW_DIR/verified/` への取り込み（Spec D-9）、`finalize.py` の CI とマージの範囲（D-4）と `--spec-commit` の順序（D-5）、DSH・codex の拒否、`checkout_audit` で止まったときの扱い（結論 3）
- [ ] **Step 2: `round-records.md` を書く。** 移植元 `$SRC:.agents/skills/review-fix-planning/references/round-records.md` を基に、認証済みの login の取得（review-records.md 8.1 のブロック）、3 区分から `state` への写し方（Spec D-7）、`seats` の作り方、`outcome` と三択の対応、検査・投稿・本文の上限、書けなかった記録の扱い、後片付け（`agent_tmp.py mkdir review-fix-planning-pr<N>`）を書く
- [ ] **Step 3: 確かめる。** 文書のコマンドの引数を `--help` と照合し（`uv run --project . --locked python .agents/skills/review-fix-planning/scripts/run_roles.py --help` など）、リンク先の実在を `test -f` で確かめる
- [ ] **Step 4: commit**（`docs(review-fix-planning): describe role runs, finalization and round records (#155)`）

### Task 6: SKILL.md の接続

**Files:**
- Modify: `.agents/skills/review-fix-planning/SKILL.md`
- Modify（必要なときだけ）: `.agents/skills/review-fix-planning/tests/test_review_fix_planning_skill_contract.py`

テスト: 新しいテストは書かない（文書の変更）。既存の SKILL.md の手順のテスト（`test_review_fix_planning_skill_contract.py`。投稿ブロックと共通 context の確認ブロックを実行する）が通ることを確かめる。

- [ ] **Step 1: Spec D-8 の箇所を書き換える。** 「第1引数の解決」の節と手順 2 のレビューディレクトリ・`PR_REPO` の決め方は変えない。frontmatter の `allowed-tools` に `Write(tmp/agents/**)`・`Edit(tmp/agents/**)` を足す（記録・依頼の JSON の置き場所）
- [ ] **Step 2: 投稿ブロックに `--records-file "$ROUND_JSON"` を足す。** `--pr "$PR_NUMBER"` を含む bash ブロックは 1 つのまま、共通 context の確認より前に外部への操作を足さない
- [ ] **Step 3: 確かめる**

Run: `uv run pytest .agents/skills/review-fix-planning -q && git diff origin/main -- .agents/skills/review-fix-planning/SKILL.md | grep -c '^[-+]'`
Expected: PASS。差分の行が D-8 の箇所に限られる（「第1引数の解決」の節に差分が無いことを `git diff` で目で確かめる）

- [ ] **Step 4: commit**（`feat(review-fix-planning): connect role runs, finalization and round records (#155)`）

### Task 7: 行動の評価

**Files:**
- Create: `.agents/skills/review-fix-planning/evals/run-roles-decision-packet.md`
- Create: `.agents/skills/review-fix-planning/evals/run-roles-safety-packet.md`
- Create: `.agents/skills/review-fix-planning/evals/2026-10-19-issue155-validation.md`
- Modify: `.agents/skills/review-fix-planning/evals/evals.json`（場面を追加。`id` は 21 から）

テスト: 不要（評価の記録）。`evals.json` の形は既存の `test_repo_cleanup_after_merge_contract.py::test_evals_have_valid_structure_and_existing_files` が確かめる。

- [ ] **Step 1: packet を書く。** 移植元の `decision-packet.md`・`safety-packet.md` の事実を、移植先の基準で答えが決まる形にする（Hold・H・D1 の問いを外し、自己レビューの枠を使った後の必須の修正、`run_roles.py` の 2 回目、create-reso-world の PR の修正不要の最終化（Spec の commit と投稿の順序）、上流 PR の自分の記録（CONTRIBUTOR）を足す）。採点の基準は validation の文書にだけ書き、packet に含めない
- [ ] **Step 2: 3 条件で答えさせる。** 新しいコンテキストのサブエージェントに、同じ packet を、(a) スキル無し、(b) 旧版（`git show origin/main:.agents/skills/review-fix-planning/SKILL.md` の内容）、(c) 新版（この worktree の SKILL.md と references）で答えさせる。モデルは 3 条件で同じにする。ファイルの作成・編集・外部への操作を禁じる
- [ ] **Step 3: 採点して記録する。** 区分（1 件ずつ）・結論・自己レビューの回数・停止の理由を比べ、旧版と新版で判断基準が変わっていないこと、スキル無しとの差を `2026-10-19-issue155-validation.md` に書く。限界（各条件 1 回、同じモデル、回答の上の判断であり実行ではない）も書く
- [ ] **Step 4: 判断が食い違ったら、新版の文面を直し、食い違った場面だけを新版でもう 1 回答えさせる（1 回まで）**
- [ ] **Step 5: commit**（`test(review-fix-planning): record the behavior evaluation (#155)`）

### Task 8: 全体の検証と記録

**Files:**
- Modify: この Plan と Spec（実行の記録）

- [ ] **Step 1: 全体の検証**（`README.md`「テスト」。`monitoring-long-tasks` でバックグラウンドで実行し、終了コードとログで確かめる）

```bash
uv run pytest tests/skills .agents/skills .agents/scripts tools
bash .devcontainer/run-tests.bash
bash scripts/check-layout.sh
env AGENT_RUNNER_DEPTH=1 uv run pytest .agents/skills/review-fix-planning
```

Expected: すべて終了コード 0

- [ ] **Step 2: Spec→Plan→Task→実行の証拠を条件ごとに照合する**（`review-fix-planning/references/convergence.md` の「3. 検証と閉じ方」）
- [ ] **Step 3: Spec と Plan に実行の記録（検証の結果・所要時間・Task 別の内訳）を書いて commit する**

## PR の後（`--merge` 相当。Spec D-13）

1. 「push の前の秘密情報の検査」の形で push し、`gh pr create --repo usaturn/create-reso-world --base main --head feat/issue-155-review-fix-roles`（draft にしない、本文は `Closes #155`）
2. サイクル（最大 3 回）: 親の main checkout の pr-review で、agent-runner の設定の inspect のレビュアーを runner で並行に起動する → 親の main checkout の review-fix-planning を完遂で実行する
3. 結論 2 ならマージと #155 の close を確かめる。結論 1 なら次のサイクル。結論 3 か上限なら止まって報告する
4. #155 に結果を書き、予約を exact-SHA lease で解放する。#116 に Spec D-14 の論点をコメントする

## Contingency

- 移植元のテストが移植先の helper の挙動の違いで落ちる: 移植先の helper（#149・#152〜#154 の担当）は変えない。テストの期待値を移植先の仕様に合わせ、差を Spec に記録する。挙動の違いが致命的なら #116 に報告する
- GitHub の比較の API の形が想定と違う: `finalize.py` は止まる側に倒す（`environment:`）。マージしない
- 全体の pytest で時間に依存するテストが落ちる: 落ちたテストだけを 1 回実行し直し、結果を記録する。2 回目も落ちれば `systematic-debugging` で調べる
- 行動の評価で旧版と新版の判断が食い違う: Task 7 の Step 4
