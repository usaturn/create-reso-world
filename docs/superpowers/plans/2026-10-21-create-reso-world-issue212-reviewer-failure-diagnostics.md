# Issue #212 失敗したレビュアーの診断 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** PR 修正ループの `review` が runner の出力を回収する前に、失敗した担当ごとの構造化した診断（上書き前の state・原因の分類・取得できなかった情報を含む）を run の記録に保存する。

**Architecture:** runner（`tools/agent_runner`）は、adapter が出力から分類した状態を上書きの前に `Attempt.reported_state` に残す（DSH は `AdapterOutcome.reported_state` で渡す）。loop（`loop.py`）は、`keep_rejected_request` の直後に、却下・失敗した `Result` ごとに試行のログ（stdout・stderr）の末尾を安全な条件でだけ読み、失敗の経路の文を既知のパターンと照合した分類名だけを `cycle-<n>/diagnostics/<request_id>.json` に書く。保存できなければ理由を記録し、出力を消さずに残す。

**Tech Stack:** Python 3.14、pydantic、pytest（`uv run`）。新しい依存は足さない。

**Spec:** `docs/superpowers/specs/2026-10-21-create-reso-world-issue212-reviewer-failure-diagnostics-design.md`

- 文書管理・コード対象: `usaturn/create-reso-world`。対象 Issue: #212
- 状態: draft
- 検証したコードの HEAD: `7d44355`（Spec の commit `2ba2836`）
- DOC_ROOT・CODE_ROOT: `/workspaces/reso-world/.worktrees/issue-212-reviewer-failure-diagnostics`（branch `fix/issue-212-reviewer-failure-diagnostics`）
- セッションディレクトリ: `/workspaces/reso-world/tmp/agents/issue-212.28g3rn4w`（ledger `budget.jsonl`、基準の検証 `baseline/`）

## Global Constraints

- 診断に入れるのは、列挙値（state・分類・取得できなかった理由）・数値・識別子（設定の agent 名、runner の request ID）だけ。ログの文字列・照合した文字列・パス・例外の文は入れない（Spec 設計 2・3・5）
- 生の stdout・stderr・session を run の記録に写さない（D-212-1）
- 停止を確認できない試行・`sensitive_paths`・このレビューの出力ディレクトリ（`cycle-<n>-review`）の外・symlink・特殊ファイルのログは読まない（Spec 設計 4）
- 各ログは末尾から 1 MiB（`1 << 20` バイト）までを読む
- 分類の語彙と優先順位: `authentication`・`approval`・`rate_limit`・`sandbox`・`timeout`・`connection`・`runtime_error`・`response_extraction`・`unknown`（Spec 設計 3 の表の順）
- 取得できなかった情報のキーは `stdout`・`stderr`・`exit_code`・`reported_state`、理由は `not_recorded`・`not_stopped`・`sensitive`・`outside_output`・`missing`・`not_regular_file`・`unreadable`・`partial`・`not_observed`
- `state` の決め方・fallback・再実行の条件・レビュアーの採否・終了コードは変えない
- テストは偽の CLI・偽の gh・一時 Git だけを使い、本物の担当（モデル）を起動しない。テスト用の偽の秘密の値は実行時に組み立てる（`AGENTS.md`「push の前の秘密情報の検査」）
- テストは `AGENTS.md`「テストの採用基準」に従う（コードを実行して確かめる挙動だけ。文書の文言のテストは書かない）

## Review Focus

- 失敗の原因の文が stdout のモデルの本文・ツールの出力にだけあるとき: 分類に使わない（`unknown`）。レビュー対象のコードが「401」「timeout」を含んでも誤って分類しない → Task 2 の `test_cause_uses_only_failure_channels`
- Traceback の `line 401` や設定の値の数字: HTTP の状態コードと取り違えない → Task 2 の同じテスト
- 1 MiB を超えるログで、原因が頭にだけあるとき: `partial` を記録し、頭は読まない（末尾の原因だけを使う） → Task 2 の `test_large_log_is_read_from_the_tail`
- 診断を書けないとき（ディレクトリが作れない・書けない）: `review` を止めず、理由を返し、ログを消さない → Task 3 の `test_unsaved_diagnostic_keeps_the_output_and_tells_the_controller`
- 中断の後の再開と再実行（`rerun`）: 診断が request ID ごとに残り、1 回目の記録（`replaced`）からも参照できる → Task 3 の `test_rerun_keeps_a_diagnostic_for_each_request`

## 要件照合（`convergence.md` 1）

| Spec の条件 | 担当 Task | 観測する結果 | 検証 |
| --- | --- | --- | --- |
| 受け入れ 1（回収の前に診断を保存、司令塔が後で調べられる） | Task 3 | `review` の後に出力ディレクトリとログが消え、`cycle-1/diagnostics/<request_id>.json` が残り、`ReviewerEntry` からパスと SHA-256 で引ける | `test_different_failures_leave_distinct_causes_after_cleanup` |
| 受け入れ 2（観測できなければ unknown と理由） | Task 2 | 読まない・読めないログは `unavailable` に理由、分類は `unknown` | `test_logs_are_read_only_when_safe`・`test_unobserved_values_are_listed` |
| 受け入れ 3（生ログを写さない、保存できなければ理由と残す） | Task 2・3 | 保存したファイルに偽の CLI の文字列・偽の秘密が無い。保存できないと `diagnostic_error` と `retained` | `test_secret_in_logs_never_reaches_the_records`・`test_unsaved_diagnostic_keeps_the_output_and_tells_the_controller` |
| 受け入れ 4（読まない・消さない条件、再実行と採否を変えない） | Task 2・3・統合 | 停止未確認・sensitive・出力の外を読まない。既存の loop と runner のテストが通る | Task 2 のテスト、Task 5 の pytest 全体 |
| 受け入れ 5（異なる既知の失敗、秘密の対照、保存の失敗） | Task 3 | `connection`・`runtime_error` が区別され、秘密が残らず、保存の失敗が扱われる | Task 3 の 3 つのテスト |
| 受け入れ 6（`reported_state` と DSH の 401） | Task 1 | runner が上書きの前の値を残す。DSH の 401 の上書きで `awaiting_authentication` | `test_reported_state_*`・`test_unreadable_identity_keeps_the_classified_state` |
| 受け入れ 7（README の入口） | Task 5 | 3 つの入口が終了コード 0（基準と比べて新しい失敗が無い） | Task 5 |

共有する前提: `Attempt.reported_state`（Task 1 が作り、Task 2 の分類と診断が読む）、`ReviewerEntry` の 3 項目と `keep_diagnostic` の戻り値（Task 2 が作り、Task 3 が使う）。統合担当は自分（inline）で、Task 3 の統合テストと Task 5 の全体の検証で確かめる。

## 実行方式

`superpowers:executing-plans`（inline）。`implement_task.py check` の `self` が true。Task 2〜4 は `loop.py` とその文書を順に変え、Task 間の名前（`reported_state`、`ReviewerEntry` の項目、`keep_diagnostic`）が密に結び付く。設計の細部はこのセッションの文脈にあり、子に渡しきるより自分で進める方が取り違えが少ない。最後に、ブランチ全体を新しいサブエージェントに 1 回レビューさせる（`superpowers:requesting-code-review`）。

## 実行予算

- Issue 全体の能動時間の予算: 360 分（ledger: `/workspaces/reso-world/tmp/agents/issue-212.28g3rn4w/budget.jsonl`）。根拠は #221（300 分。loop と文書の変更）より範囲が広い（runner・DSH・loop・文書）こと
- phase の目安: 準備・調査・Spec・Plan 70 分（済）、Task 1 40 分、Task 2 50 分、Task 3 50 分、Task 4 20 分、Task 5（検証・最後のレビュー）40 分、PR 10 分、PR 修正ループは残り（最大 3 サイクル ×（レビューの期限 45 分＋計画・修正 15 分）のうち予算に収まる範囲）
- worker: 実装は inline。最後のレビューのサブエージェントを 1 回だけ起動する。長時間の実行（`run-tests.bash`・pytest 全体）はバックグラウンドで実行し、終了コードで確かめる。1 回の期限は 30 分。README の入口は並行させず順に実行する
- 再試行の上限: 同じ signature の信頼性の失敗（テストの時間切れ・環境の I/O の停止）は 1 回まで。安全の失敗（実際の GitHub への書き込み、実リポジトリの書き換えの疑い、本物の担当の起動）は再試行せず止まる
- checkpoint: Task 1 の後、Task 3 の後、Task 5 の後、ループの各サイクルの後、予算の 50%・100%（100% では停止して報告する）
- 縮小・方法変更の候補: (1) 受け付けたレビュアーの失敗した fallback の診断（D-212-3）を、却下したレビュアーだけに縮める、(2) 分類の `sandbox`・`approval` を外す、(3) 保存できないときの残し方（D-212-10）を、理由の記録だけに縮める（この場合は Spec の決定記録に変更として書く）。runner の `reported_state`（D-212-5）は利用者の決定なので縮めない

## 基準の検証

`/workspaces/reso-world/tmp/agents/issue-212.28g3rn4w/baseline/`（`run-checks.sh` で README の 3 つの入口を順に実行）。結果は Task 5 で比べる。

---

### Task 1: runner が上書きの前の状態を `Attempt.reported_state` に残す

**Files:**
- Modify: `tools/agent_runner/models.py`（`Attempt`）
- Modify: `tools/agent_runner/adapters/__init__.py`（`AdapterOutcome`）
- Modify: `tools/agent_runner/runner.py`（`_collect`、`attempt` の `Attempt` の組み立て）
- Modify: `tools/agent_runner/adapters/dsh.py`（`Dsh.collect`）
- Modify: `tools/agent_runner/interfaces.rst`（`AdapterOutcome`・`Attempt` の節）
- Test: `tools/agent_runner/tests/test_runner.py`、`tools/agent_runner/tests/adapters/dsh/test_adapter.py`

**Interfaces:**
- Produces: `Attempt.reported_state: State | None = None`（`state` の次）、`AdapterOutcome.reported_state: State | None = None`（4 番目の項目。位置引数の既存の呼び出しはそのまま）
- `_collect(...) -> tuple[State, Identity, Payload, State | None]`（4 番目が reported）

テストの要否: 要る（runner の状態の記録と DSH の分類の分岐を実行して確かめる）。

- [ ] **Step 1: 失敗するテストを書く（runner）**

`FakeAdapter.__init__` に `reported_state: object = None` を足し、`collect` が `AdapterOutcome(receipt, self.identity, self.outcome_state, cast(State | None, self.reported_state))` を返すようにする。

```python
def test_reported_state_keeps_the_adapter_state_before_the_exit_code_override(repository: Path) -> None:
    batch = run_workflow(configuration(), "audit", "work", repository,
                         adapter_loader=lambda _: FakeAdapter({"a": {"exit": 1}}))
    attempt = batch.results[0].attempts[0]
    assert (attempt.state, attempt.reported_state) == ("response_failed", "success")


@pytest.mark.parametrize("reported,expected", [("awaiting_authentication", "awaiting_authentication"), ("bogus", "response_failed")])
def test_adapter_reported_state_is_recorded(repository: Path, reported: str, expected: str) -> None:
    adapter = FakeAdapter(outcome_state="response_failed", reported_state=reported)
    batch = run_workflow(configuration(), "audit", "work", repository, adapter_loader=lambda _: adapter)
    attempt = batch.results[0].attempts[0]
    assert (attempt.state, attempt.reported_state) == ("response_failed", expected)
```

既存の `test_unconfirmed_stop_blocks_success_and_fallback` と `test_launch_failed_is_safe` に、各試行の `reported_state is None` の assert を足す（収集しない経路は null）。

- [ ] **Step 2: 失敗するテストを書く（DSH）**

```python
@pytest.mark.parametrize(
    "reason,reported",
    [({"kind": "error", "error": {"code": "AUTH", "message": "401: rejected"}}, "awaiting_authentication"), (None, "success")],
)
def test_unreadable_identity_keeps_the_classified_state(context: AdapterContext, reason: dict[str, object] | None, reported: str) -> None:
    # assistant の応答が無い session（DSH session has no observed assistant route）。Issue #212 のコメントの 401 の事例
    path = write_session(context.receipt_path.parent / "dsh" / "state", context.work_dir, session_id="observed-session")
    path.write_text("".join(line + "\n" for line in path.read_text().splitlines()[:-1]))
    outcome = _collect(context, _stream(reason=reason))
    assert outcome.receipt is not None and outcome.receipt.status == "response_failed"
    assert outcome.reported_state == reported


def test_readable_identity_reports_no_override(context: AdapterContext) -> None:
    outcome = _collect(context, _stream())
    assert outcome.receipt is not None and outcome.receipt.status == "success"
    assert outcome.reported_state is None
```

- [ ] **Step 3: テストが失敗することを確かめる**

Run: `uv run pytest tools/agent_runner/tests/test_runner.py tools/agent_runner/tests/adapters/dsh/test_adapter.py -k "reported or identity_keeps or no_override or unconfirmed_stop_blocks or launch_failed_is_safe" -q`
Expected: 新しいテストが `reported_state` の不在（TypeError・AttributeError）で FAIL

- [ ] **Step 4: 実装する**

- `models.py`: `Attempt.reported_state: State | None = None`
- `adapters/__init__.py`: `AdapterOutcome.reported_state: State | None = None`
- `runner.py`: `_STATES = frozenset(get_args(State))`。`_collect` は `collect` の後、`outcome.state` が許された値と確かめた後に、Spec 設計 1 の順（`outcome.reported_state` が `_STATES` の文字列なら採る → 成功以外の `outcome.state` → receipt（ファイル、無ければ adapter のもの）の `status` → `outcome.state`）で reported を決め、それ以降のすべての戻り値の 4 番目に入れる。その前の戻り値（DSH の receipt ファイル、許されない `outcome.state`、例外）は null。`attempt` は `reported: State | None = None` を初期化し、`_collect` を呼んだときだけ受け取り、`Attempt(..., reported_state=reported)` に入れる
- `dsh.py`: `collect` の識別の検査で `status` を置き換える 2 か所で、置き換える前の `status` を `reported` に入れ、`AdapterOutcome(..., reported_state=reported)` で返す
- `interfaces.rst`: `AdapterOutcome(...)` の見出しに `reported_state=None` を足し、意味（adapter 自身の後段の検査で置き換える前の状態。記録だけに使い、状態の判定に使わない）を書く。`Attempt` の項目の列に `reported_state` を足し、意味と null のときを書く

- [ ] **Step 5: テストが通ることを確かめる**

Run: `uv run pytest tools/agent_runner -q`
Expected: PASS（基準の失敗があれば、それと同じものだけ）

- [ ] **Step 6: commit**

```bash
git add tools/agent_runner/models.py tools/agent_runner/adapters/__init__.py tools/agent_runner/runner.py \
  tools/agent_runner/adapters/dsh.py tools/agent_runner/interfaces.rst \
  tools/agent_runner/tests/test_runner.py tools/agent_runner/tests/adapters/dsh/test_adapter.py
git commit -m "feat(agent-runner): record the state the adapter classified before overrides (#212)"
```

### Task 2: loop の診断の部品（ログの読み取り・分類・保存）

**Files:**
- Modify: `.agents/skills/pr-review-fix-loop/scripts/loop.py`（`ReviewerEntry` の項目、新しい節「失敗の診断」を `keep_rejected_request` の後に置く）
- Create: `.agents/skills/pr-review-fix-loop/tests/test_loop_diagnostics.py`

**Interfaces:**
- Consumes: `Attempt.reported_state`（Task 1）
- Produces（`loop.py`）:
  - `DIAGNOSTIC_READ_BYTES = 1 << 20`
  - `Cause`・`Unavailable`・`DiagnosticItem`（Literal。値は Global Constraints）
  - `class AttemptDiagnostic(StrictModel)`: `agent_id: str`、`state: str`、`reported_state: str | None`、`exit_code: int | None`、`stop_confirmed: bool`、`elapsed_seconds: float`、`cause: Cause`、`unavailable: dict[DiagnosticItem, Unavailable]`
  - `class ReviewerDiagnostic(StrictModel)`: `schema`（`pr-review-fix-loop/v1`）、`kind: Literal["diagnostic"]`、`request_id`・`role`・`requested_agent`・`actual_agent: str`、`verdict: Literal["accepted", "rejected"]`、`stage: RejectedStage | None`、`state: str`、`attempts: list[AttemptDiagnostic]`
  - `ReviewerEntry` に `diagnostic_file: str | None = None`・`diagnostic_sha256: str | None = None`・`diagnostic_error: str | None = None`
  - `read_log_tail(path: Path | None, attempt: Attempt, output_dir: Path) -> tuple[str | None, Unavailable | None]`
  - `diagnostic_text(stdout: str | None, stderr: str | None) -> str`
  - `classify_cause(text: str, attempt: Attempt) -> Cause`
  - `diagnose_attempt(attempt: Attempt, output_dir: Path) -> AttemptDiagnostic`
  - `keep_diagnostic(result: Result, entry: ReviewerEntry, directory: Path, output_dir: Path) -> bool`（保存したか不要なら True、保存できなければ `entry.diagnostic_error` を書いて False）

テストの要否: 要る（読む条件・分類・保存の分岐を実行して確かめる）。

- [ ] **Step 1: 失敗するテストを書く**

`test_loop_diagnostics.py` に、`Attempt` を直接組み立てて `loop.diagnose_attempt` を呼ぶ単体のテストを書く（出力ディレクトリは `tmp_path / "out"`）。

- `test_logs_are_read_only_when_safe`（parametrize）: stderr に `Error: invalid api key` を書いたログで、`case` ごとに `unavailable["stderr"]` と分類を確かめる。`readable` は `authentication` で `stderr` の理由なし（対照）。`not_recorded`（パス None）、`not_stopped`（`stop_confirmed=False`）、`sensitive`（`sensitive_paths=[log]`）、`outside_output`（出力の外のファイル）、`missing`、`not_regular_file`（出力の中の symlink、FIFO）は、どれも分類が `unknown`
- `test_large_log_is_read_from_the_tail`: `monkeypatch.setattr(loop, "DIAGNOSTIC_READ_BYTES", 64)`。末尾に `Error: read ECONNRESET` → `partial`・`connection`。頭にだけ `Error: invalid api key` → `partial`・`unknown`
- `test_cause_uses_only_failure_channels`（parametrize、`exit_code=1`・`state="response_failed"`）

  | stdout | stderr | 分類 |
  | --- | --- | --- |
  | `{"type":"tool_result","status":"completed","result":"HTTP 401 Unauthorized"}` | 空 | `unknown` |
  | `The handler returns 429 when rate limited.`（JSON でない本文） | 空 | `unknown` |
  | `{"type":"error","message":"invalid api key"}` | 空 | `authentication` |
  | DSH の `turn_end`（`reason` が `{"kind":"error","error":{"code":"AUTH","message":"401: x"}}`） | 空 | `authentication` |
  | `Error: fetch failed` | 空 | `connection` |
  | 空 | `Traceback (most recent call last):` / `  File "run.py", line 401, in main` / `RuntimeError: boom` | `runtime_error` |
  | 空 | `HTTP 401 Unauthorized` と `connection reset by peer` | `authentication` |
  | 空 | `HTTP 429 Too Many Requests` | `rate_limit` |
  | 空 | `dsh-sandbox: cannot bind` | `sandbox` |
  | 空 | `Request timed out` | `timeout` |

- `test_response_extraction_is_decided_from_the_end_state`（parametrize、ログは空）: `(0, "response_failed", None, [], True)`→`response_extraction`、`(0, "missing_result", "success", [], True)`→`unknown`、`(1, "response_failed", None, [], True)`→`unknown`、`(0, "response_failed", None, [<path>], True)`→`unknown`、`(0, "response_failed", None, [], False)`→`unknown`（引数は exit_code・state・reported_state・sensitive_paths・stop_confirmed）
- `test_unobserved_values_are_listed`: `exit_code=None`・`reported_state=None` → `unavailable` に `{"exit_code": "not_observed", "reported_state": "not_observed"}` が入る
- `test_keep_diagnostic_skips_accepted_reviewers_without_failures`: 受け付けた・全試行 success の `Result` は書かず True、`diagnostic_file` は None

- [ ] **Step 2: テストが失敗することを確かめる**

Run: `uv run pytest .agents/skills/pr-review-fix-loop/tests/test_loop_diagnostics.py -q`
Expected: FAIL（`diagnose_attempt` などが無い）

- [ ] **Step 3: 実装する**

- 分類のパターンは `(Cause, re.Pattern[str])` の tuple の並び（優先順位の順）にし、大文字小文字を区別しない。HTTP の状態コードは `HTTP`・`status`・`status code`・`error code` に続くときだけ数える。DSH の `AUTH` は大文字のときだけ。各分類の語は Spec 設計 3 の表の例を含める
- `diagnostic_text`: stderr の全体と、stdout の各行のうち、JSON の object として読めて失敗のイベント（`type` に `error`・`fail` を含む、`is_error` が true、`subtype` が `error` で始まる、`error` が空でない、`reason.kind` が `error`）のもの、JSON として読めず診断の行（行頭が `error`・`fatal`・`panic`・`critical`・`Traceback`、`<名前>Error:`・`<名前>Exception:`、`dsh:`・`dsh-sandbox:`・`bwrap:`）のものを、改行でつなぐ
- `read_log_tail`: Spec 設計 4 の順（記録なし → 停止未確認 → sensitive → 出力の外（`resolve` で比べる）→ `os.open(O_RDONLY | O_NOFOLLOW | O_NONBLOCK)`（`FileNotFoundError` は `missing`、`ELOOP` は `not_regular_file`、ほかの `OSError` は `unreadable`）→ `fstat` で通常のファイルか → 大きさが上限を超えたら末尾へ seek して `partial`）。UTF-8 で読み、壊れたバイトは置き換える
- `classify_cause`: パターンの照合、当たらなければ Spec 設計 3 の `response_extraction` の条件、どれでもなければ `unknown`
- `keep_diagnostic`: 対象（Spec 設計 2: `entry.verdict == "rejected"` か、`success` 以外の試行がある）でなければ何も書かずに True。`ReviewerDiagnostic` を組み立て、`directory.mkdir(parents=True, exist_ok=True)`、`write_json(directory / f"{request_id}.json", ...)`、`sha256_file`。`OSError`・`ValueError` は `entry.diagnostic_error = f"診断を保存できない（{名前}）"`（名前は `errno.errorcode` の名前、無ければ例外の型の名前）にして False。request ID がファイル名でなければ `ValueError` と同じ扱い

- [ ] **Step 4: テストが通ることを確かめる**

Run: `uv run pytest .agents/skills/pr-review-fix-loop/tests/test_loop_diagnostics.py -q`
Expected: PASS

- [ ] **Step 5: commit**

```bash
git add .agents/skills/pr-review-fix-loop/scripts/loop.py .agents/skills/pr-review-fix-loop/tests/test_loop_diagnostics.py
git commit -m "feat(pr-review-fix-loop): build structured diagnostics for failed reviewers (#212)"
```

### Task 3: 回収の前に診断を保存し、保存できなければ出力を残す

**Files:**
- Modify: `.agents/skills/pr-review-fix-loop/scripts/loop.py`（`cleanup_output`、`_review_batch`、`_reviewer_summary`）
- Test: `.agents/skills/pr-review-fix-loop/tests/test_loop_diagnostics.py`

**Interfaces:**
- Consumes: `keep_diagnostic`・`ReviewerEntry.diagnostic_*`（Task 2）
- Produces: `cleanup_output(tool_root, resource, batch, *, force=False, reason=None, keep: str | None = None) -> list[str]`（`keep` があれば、停止を確認できたときに worktree の登録は外し、出力ディレクトリは消さずに `retained` にして、`keep` を理由にする）。`review` の出力の各レビュアーに `diagnostic_file`・`diagnostic_error`

テストの要否: 要る（`review` の全体の経路で、回収の後に診断が残ること、秘密が残らないこと、保存の失敗の扱いを実行して確かめる）。

- [ ] **Step 1: 失敗するテストを書く**

テストの adapter（同じファイル）: 成功させる担当は `env.reviewers({...})` の偽のレビュアーに任せ、失敗させる担当は `sys.executable -c <program> <JSON>` で stdout・stderr を書いて指定の終了コードで終わる。失敗させる担当の `collect` は `AdapterOutcome(identity=Identity(model=...), state="response_failed", reported_state=<指定>)` を返す。偽の秘密は `"sk-" + hashlib.sha256(b"issue-212").hexdigest()[:40]` のように実行時に作る。保存したファイルの検査は、run のディレクトリの下の全ファイルを読む補助 `saved_text(run_dir) -> str` で行う。

- `test_different_failures_leave_distinct_causes_after_cleanup`: alpha は stderr に `Error: read ECONNRESET (<目印 A>)`、beta は Traceback（`File "<目印 B>.py", line 401` と `RuntimeError: boom`）、どちらも終了コード 1。`review` は `LoopError`（6, `review`）。サイクルの記録の 2 人の `diagnostic_file` が存在し、SHA-256 が一致し、`ReviewerDiagnostic` として読め、`stage` が `runner`、試行の `cause` が `connection`・`runtime_error`、`exit_code` が 1、`stop_confirmed` が true、`unavailable` が空。run の資源は `removed`、元の stderr のログは無い。`saved_text` に目印 A・B が無い
- `test_secret_in_logs_never_reaches_the_records`: alpha は成功、beta は stderr に `HTTP 401 Unauthorized: token <偽の秘密> was rejected`、`reported_state="awaiting_authentication"`。`review` は計画に進む（`next` が `cycle-end`）。`rejected[0]["diagnostic_file"]` があり、試行の `cause` が `authentication`、`reported_state` が `awaiting_authentication`。alpha の `diagnostic_file` は None。`saved_text(run_dir)` と `json.dumps(review の出力)` に偽の秘密が無い
- `test_unsaved_diagnostic_keeps_the_output_and_tells_the_controller`: `cycle_begin` の後に `cycle-1/diagnostics` を通常のファイルとして作る。alpha は成功、beta は終了コード 1。`review` は計画に進み、`rejected[0]["diagnostic_error"]` が `診断を保存できない（EEXIST）`、`diagnostic_file` は None。資源は `retained`（理由に「診断を保存できなかった」）、出力ディレクトリと beta の stderr のログが残り、出力の `retained` にその完全パスが入り、worktree の登録は親だけ。`finish --abort`（`github=env.github`）の `retained` にも入る
- `test_rerun_keeps_a_diagnostic_for_each_request`: alpha は成功、beta は 2 回とも `failed`（偽のレビュアーの payload の失敗）。2 回の `review` の後、`cycle-1/diagnostics` に 2 ファイル、`rerun.replaced[0].diagnostic_file` と、置き換えた後の beta の `diagnostic_file` が別で、どちらも `stage` が `payload`

- [ ] **Step 2: テストが失敗することを確かめる**

Run: `uv run pytest .agents/skills/pr-review-fix-loop/tests/test_loop_diagnostics.py -q`
Expected: 新しい 4 つが FAIL（診断のファイルが無い・`diagnostic_error` が無い）

- [ ] **Step 3: 実装する**

- `_review_batch`: `keep_rejected_request` の同じ loop で `keep_diagnostic(item, entry, work / "diagnostics", output_dir)` を呼び、1 つでも False なら `keep` に「失敗した担当の診断を保存できなかったので、ログを含む出力を消さずに残す」を入れて `cleanup_output` に渡す。コメントは「回収で出力が消える前に、却下した試行に渡した指示と、失敗した担当の診断を残す」にする
- `cleanup_output`: `keep` のとき、worktree を外した後、出力ディレクトリのパスを `retained` に足し、理由を `keep` にする（停止を確認できないときの早い戻りと、親ディレクトリの不在の扱いは変えない）
- `_reviewer_summary`: `diagnostic_file`・`diagnostic_error` を足す

- [ ] **Step 4: テストが通ることを確かめる**

Run: `uv run pytest .agents/skills/pr-review-fix-loop/tests -q`
Expected: PASS（既存の loop のテストを含む）

- [ ] **Step 5: commit**

```bash
git add .agents/skills/pr-review-fix-loop/scripts/loop.py .agents/skills/pr-review-fix-loop/tests/test_loop_diagnostics.py
git commit -m "feat(pr-review-fix-loop): save reviewer diagnostics before removing the runner output (#212)"
```

### Task 4: 文書（records.md・SKILL.md）

**Files:**
- Modify: `.agents/skills/pr-review-fix-loop/references/records.md`
- Modify: `.agents/skills/pr-review-fix-loop/SKILL.md`

テストの要否: 要らない（文書だけ）。代わりに、記述した項目名・値が `loop.py` のモデルと一致することを `git diff` と目視で照合し、`bash scripts/check-layout.sh` を通す。

- [ ] **Step 1: records.md を直す**

1 章の置き場所の木に `diagnostics/<request_id>.json`（失敗した担当がいるレビュアーの試行ごとの構造化した診断。分類だけを残し、ログは写さない）。3 章の `resources` の `retained` に、診断を保存できなかったときの理由。4 章の `review.reviewers[]` に `diagnostic_file`・`diagnostic_sha256`・`diagnostic_error`。4 章の後に「4.1 失敗した担当の診断」の節（対象、時点、形の表、分類の表、`unavailable` の表、保存できないとき、ログを読む条件）。4 章の最後の段落の「秘密が残りうる stdout・stderr は写さない」に、診断は分類名だけを残すことを足す。`review` の出力の項目（`diagnostic_file`・`diagnostic_error`）も書く

- [ ] **Step 2: SKILL.md を直す**

サイクルの 2（`review`）に 1 項を足す: 失敗したレビュアーの原因は `diagnostic_file` の診断（試行ごとの `cause`・`reported_state`・`unavailable`。形式は records.md）で調べる。ログは回収で消える。`diagnostic_error` があれば診断を保存できなかったので、理由と残したパス（`retained`）を利用者に伝える。最終報告に、失敗したレビュアーの診断のパスと原因の分類、保存できなかった理由を足す

- [ ] **Step 3: 確かめる**

Run: `git diff -- .agents/skills/pr-review-fix-loop/references/records.md .agents/skills/pr-review-fix-loop/SKILL.md` と `bash scripts/check-layout.sh`
Expected: 項目名・値がモデルと一致し、check-layout が終了コード 0（基準と同じ）

- [ ] **Step 4: commit**

```bash
git add .agents/skills/pr-review-fix-loop/references/records.md .agents/skills/pr-review-fix-loop/SKILL.md
git commit -m "docs(pr-review-fix-loop): document reviewer failure diagnostics (#212)"
```

### Task 5: 全体の検証・最後のレビュー・記録

テストの要否: 新しいテストは書かない（検証の実行と記録）。

- [ ] **Step 1: README の「テスト」の入口を順に実行する**

Run: `bash /workspaces/reso-world/tmp/agents/issue-212.28g3rn4w/run-checks.sh <worktree> /workspaces/reso-world/tmp/agents/issue-212.28g3rn4w/verify-1`（バックグラウンド、終了の通知で待つ）
Expected: 3 つとも終了コード 0。失敗があれば `baseline/` と比べ、基準からの新しい失敗だけを `systematic-debugging` で調べる

- [ ] **Step 2: 要件照合の表の各行の証拠を確かめる**（テスト名と実行結果、HEAD）

- [ ] **Step 3: ブランチ全体のレビュー**（`superpowers:requesting-code-review`。新しいサブエージェント 1 回。致命的な指摘だけを直し、直したら Step 1 からやり直す）

- [ ] **Step 4: 検証の記録を作る**（`--merge` のため。最後の commit の後の HEAD、`git status --porcelain` が空、各コマンドの argv と終了コード、ログの完全パス。`finalize.py` の `--checks-file` の形 `{"head", "base", "commands": [{"argv", "exit_code"}]}` のファイル `checks.json` も作る）

- [ ] **Step 5: Plan の「完了」に結果を書いて commit**（Spec・Plan は draft のまま）

## 完了

（Task 5 で書く）
