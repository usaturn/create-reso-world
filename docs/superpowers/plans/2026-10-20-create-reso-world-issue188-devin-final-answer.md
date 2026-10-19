# Issue #188 devin adapter の回答の取り出し Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** devin の担当がツールを使って成功した実行を、`collect` が `success` と payload で返すようにする。

**Architecture:** export（ATIF）の最後の agent の発話を回答とし、stdout はその回答で終わる（後ろは改行で区切った通常の進捗行だけ）ことを確かめる。payload は回答から取り出す。診断の優先と最後の step の検査は変えない。

**Tech Stack:** Python 3.14、pytest、偽の devin CLI（`tools/agent_runner/tests/adapters/devin/fake_cli.py`、変更なし）

**Spec:** `docs/superpowers/specs/2026-10-20-create-reso-world-issue188-devin-final-answer-design.md`

- 状態: draft
- 実行方式: `superpowers:executing-plans`（このセッションが inline で実装する）。理由: `implement_task.py check` の `self` が true で、Task 1 は同じ 2 ファイルの逐次の変更、Task 2 は Task 1 の規則を書き写す文書、Task 3 は統合確認で、子に分ける利点が無い。最後のブランチ全体のレビューは省かない

## Global Constraints

- Python は `uv` で実行する（`python3` を使わない）。テストは偽の CLI だけを使い、devin・他の担当を起動しない
- 変更するのは `tools/agent_runner/adapters/devin.py`・`tools/agent_runner/tests/adapters/devin/test_adapter.py`・`tools/agent_runner/runtimes/devin.rst` だけ（Spec の除外範囲）
- 診断の優先（stderr、stdout と最後の発話の診断行、export の error の step）と `_final_agent_message` の検査は変えない（D-188-4）
- 実際の #185・#186 の出力はテストに写さない（D-188-5）

## Review Focus

1. 回答が stdout に 2 回以上現れる（途中の発話で同じ JSON を下書きした）: 最後に現れた位置で判定する → Task 1 の `test_tool_run_answer_repeated_earlier_succeeds`
2. 回答の前後の空白が stdout と export で違う（export の発話の末尾に改行が無い・ある）: 前後の空白を除いて比べる → Task 1 の C1 の正例（stdout は回答 + 改行、export の発話は改行なし）
3. text の役割の payload が stdout 全体から最後の発話に変わる: Task 1 で `test_collect_success_text_shape` を最後の発話の値で確かめる
4. 秘匿値を含む回答: stdout と export の両方で同じ値に置き換わり、成功のまま置き換えた値を返す → Task 1 で `test_retained_export_with_secrets_is_redacted_before_collection` を揃える
5. 既存の負例が、stdout と最後の発話の文字列の違い（`{"ok":true}` と `{"ok": true}`）だけで失敗し、本来の検査をしなくなる: Task 1 の Step 1 で両方を揃える

## 要件の照合

| Spec の条件 | 担当 Task | 観測する結果 | 検証 |
| --- | --- | --- | --- |
| C1 | Task 1 | `success`、payload が回答の object | `test_tool_run_stdout_ending_with_final_answer_succeeds`、`test_end_to_end_tool_run_collects_final_answer` |
| C2 | Task 1 | `response_failed`、payload が null | `test_tool_run_with_truncated_final_answer_fails` |
| C3 | Task 1 | `response_failed`、payload が null | `test_tool_run_stdout_not_ending_with_final_answer_fails`（4 例） |
| C4 | Task 1 | `success` でない | `test_tool_run_final_step_calling_tool_fails` |
| C5 | Task 1 | 既存のテストが、揃えた入力で通る | devin のテストの全体 |
| C6 | Task 3 | 終了コード 0 | README の「テスト」の入口 |
| C7 | Task 3 | 2 件とも `success`、payload が最後の発話の JSON と一致 | scratchpad の確認スクリプト |
| C8 | Task 2・Task 3 | rst と docstring が規則と一致 | rstcheck、`git diff` の読み合わせ |

共有する前提: Task 1 のコードの規則（回答の取り出し元、後ろの行の規則、payload の取り出し元）を、Task 1 の docstring と Task 2 の rst が同じ言葉で書く。統合担当（Task 3、このセッション）が `git diff` で 3 か所を突き合わせる。

---

### Task 1: `collect` の回答の判定とテスト

**Files:**
- Modify: `tools/agent_runner/adapters/devin.py`（docstring 1–8 行、`_json_object` の 79–82 行、`collect` の 233–243 行）
- Test: `tools/agent_runner/tests/adapters/devin/test_adapter.py`

**テストの要否:** 書く。出力の解析で、実際に起きた不具合（#185・#186 の `response_failed`）の再発を防ぐ（AGENTS.md の「テストの採用基準」）。

**Interfaces:**
- Produces: `_plain_tail(tail: str) -> bool`（`_json_object` と `_ends_with` が使う後ろの行の規則）、`_ends_with(stdout: str, answer: str) -> bool`

- [ ] **Step 1: 既存のテストの入力を揃える**

  - ファイルの中の `{"ok":true}` を、すべて `{"ok": true}`（既定の `_export()` の最後の発話と同じ文字列）にする
  - `test_collect_success_text_shape`: `_collect(context, "plain answer\n", export=_export(message="plain answer"))`、`payload == "plain answer"`
  - `test_non_object_stdout_fails_json_shape`: `export=_export(message="plain text")` を足す
  - `test_success_payload_can_discuss_authentication`: stdout と同じ文字列を `export=_export(message=...)` に渡す
  - `test_invalid_final_json_does_not_return_nested_fragment`: `export=_export(message=stdout)` を足す
  - `test_late_diagnostic_or_truncation_after_answer_is_failure`: `export=_export(message=prefix)` を足す
  - `test_fenced_json_answer`: `export=_export(message='```json\n{"ok": true}\n```')` を足す
  - `test_retained_export_with_secrets_is_redacted_before_collection`: `out` を `json.dumps({"final_answer": secret}) + "\n"` にし、`attempt.payload == {"final_answer": "[REDACTED]"}`
  - `test_secret_free_multiline_export_is_retained_unchanged`: `out` を最後の発話（`json.dumps({"answer": "回答\n日本語"}, ensure_ascii=False)`）+ `"\n"` にし、`attempt.payload == {"answer": "回答\n日本語"}`

- [ ] **Step 2: 実際の形の helper と C1〜C4 のテストを足す**

```python
_PROGRESS = (
    "Python 3.14 allows unparenthesized `except A, B` — not a bug. Now checking the tests.",
    "Running the new tests.",
)
_FENCED = '```json\n{\n  "status": "success",\n  "review_file": "SWE-2-Max.md"\n}\n```'
_FENCED_PAYLOAD = {"status": "success", "review_file": "SWE-2-Max.md"}

def _tool_run_export(final: str = _FENCED, *, final_tool_calls: list[dict[str, object]] | None = None) -> dict[str, object]:
    # devin 3000.11.92: agent steps call tools (ATIF tool_call_id/function_name/arguments) before the final answer
    ...  # _export(message=None) に、_PROGRESS の各発話を tool_calls と observation 付きの agent の step で足し、最後に final の step を足す

def _tool_run_stdout(final: str = _FENCED) -> str:
    return "".join(_PROGRESS) + final + "\n"   # devin -p は区切りなしで全発話を連結する
```

```python
@pytest.mark.parametrize("final,payload", [(_FENCED, _FENCED_PAYLOAD), ('{"ok": true}', {"ok": True})])
def test_tool_run_stdout_ending_with_final_answer_succeeds(context, final, payload):
    outcome = _collect(context, _tool_run_stdout(final), export=_tool_run_export(final))
    assert outcome.receipt is not None and outcome.receipt.status == "success"
    assert outcome.receipt.payload == payload

def test_tool_run_answer_repeated_earlier_succeeds(context):
    stdout = "".join(_PROGRESS) + _FENCED + "Double-checking." + _FENCED + "\n"
    outcome = _collect(context, stdout, export=_tool_run_export())
    assert outcome.receipt is not None and outcome.receipt.payload == _FENCED_PAYLOAD

def test_tool_run_with_truncated_final_answer_fails(context):
    final = _FENCED[: _FENCED.index('"review_file"')]
    outcome = _collect(context, _tool_run_stdout(final), export=_tool_run_export(final))
    assert outcome.receipt is not None and outcome.receipt.status == "response_failed"
    assert outcome.receipt.payload is None

@pytest.mark.parametrize("final,stdout", [
    (_FENCED, "".join(_PROGRESS) + _FENCED[:-8]),                 # stdout が回答の途中で切れている
    (_FENCED, _tool_run_stdout() + '{"event":'),                  # 回答の後ろに別の JSON の行
    ('{"ok": true}', "".join(_PROGRESS) + '{"ok": true}, "x": 1}\n'),  # 回答と同じ行に続く文字
    (_FENCED, "".join(_PROGRESS) + "\n"),                         # 回答が stdout に無い
])
def test_tool_run_stdout_not_ending_with_final_answer_fails(context, final, stdout):
    outcome = _collect(context, stdout, export=_tool_run_export(final))
    assert outcome.receipt is not None and outcome.receipt.status == "response_failed"
    assert outcome.receipt.payload is None

def test_tool_run_final_step_calling_tool_fails(context):
    export = _tool_run_export(final_tool_calls=[{"tool_call_id": "call-9", "function_name": "exec", "arguments": {}}])
    outcome = _collect(context, _tool_run_stdout(), export=export)
    assert outcome.receipt is not None and outcome.receipt.status != "success"

def test_end_to_end_tool_run_collects_final_answer(repository, tmp_path):
    # fake_cli に --fake-export（_tool_run_export()）と --fake-stdout（_tool_run_stdout()）を渡し、run_workflow を通す
    assert batch.state == "success"
    assert batch.results[0].attempts[0].payload == _FENCED_PAYLOAD
```

- [ ] **Step 3: テストを実行して、変更前の失敗を確かめる**

Run: `uv run pytest tools/agent_runner/tests/adapters/devin -q`
Expected: FAIL。`test_tool_run_stdout_ending_with_final_answer_succeeds`（2 例とも）・`test_tool_run_answer_repeated_earlier_succeeds`・`test_end_to_end_tool_run_collects_final_answer` と、payload の期待を最後の発話に変えた `test_collect_success_text_shape` が失敗する。秘匿値の 2 件は stdout と最後の発話が同じ文字列なので変更前から通る。C2〜C4 の負例も変更前から通る（回帰の防止）

- [ ] **Step 4: `devin.py` を変える**

  - `_plain_tail(tail: str) -> bool`: `_json_object` の 79–82 行の規則（`_failure_status(tail)` が None で、`{`・`[`・```` ``` ```` で始まる行が無い）を関数にし、`_json_object` もこれを使う
  - `_ends_with(stdout: str, answer: str) -> bool`: `answer.strip()` が `stdout` に最後に現れる位置（`rfind`）を探し、無ければ False。その後ろを最初の改行で分け、同じ行の残りが空白だけで、残りが `_plain_tail` を満たすときだけ True
  - `collect` の成功の分岐: `final is not None and _ends_with(stdout, final)` のとき `_payload(final, context.role.result_shape)` の結果を返す。それ以外は今の `else`（`_failure_status(stdout) or "response_failed"`）。コメントは「最後の ATIF の発話が回答で、stdout はそれで終わる必要がある。途中で切れた stdout や壊れた最後の発話は成功にしない」の意図を残す
  - docstring: 「The run's stdout is the final answer」を、「`devin -p` は全 agent の発話を区切りなしで stdout に出す。export の最後の agent の発話が回答で、stdout はそれで終わる必要がある」に直す

- [ ] **Step 5: テストを実行して通ることを確かめる**

Run: `uv run pytest tools/agent_runner/tests/adapters/devin -q`
Expected: PASS（失敗 0）

- [ ] **Step 6: Commit**

```bash
git add tools/agent_runner/adapters/devin.py tools/agent_runner/tests/adapters/devin/test_adapter.py
git commit -m "fix(agent_runner): take devin's final ATIF message as the answer (#188)"
```

### Task 2: `runtimes/devin.rst` の記述

**Files:**
- Modify: `tools/agent_runner/runtimes/devin.rst`（概要の 11 行、「観測する情報と完了条件」の 33–39 行、「検証と制約」の 50–53 行）

**テストの要否:** 書かない。文書だけの変更（テストの採用基準の「書かない」）。代わりに rstcheck と `git diff` の読み合わせで確かめる。

**Interfaces:**
- Consumes: Task 1 の規則（回答 = 最後の ATIF の応答、stdout はそれで終わる、後ろは通常の進捗行だけ、payload は回答から）

- [ ] **Step 1: rst-writer スキルを読み、3 か所を直す**

  - 概要: 標準出力と `export.json` を解析し、回答は export の最後の agent 応答とする
  - 完了条件: `devin -p` の標準出力には全 agent 応答が区切りなしで連結される。標準出力が回答で終わることを確かめ、後ろには改行で区切った通常の進捗行だけを許す。JSON 形式の役割は最後の応答が空でない JSON object であることを求め、payload は最後の応答から取り出す。途中の応答の診断行も検査の対象になる（Spec の D-188-4）
  - 検証と制約: 3000.11.92 の実際の出力（#185・#186、2026-10-19）で、連結の形と最後の step の形を確かめた。テストは偽の CLI だけを使い、実 CLI・モデル・API を起動しない

- [ ] **Step 2: rstcheck を実行する**

Run: `uv run --no-project --with docutils --with rstcheck rstcheck --report-level warning tools/agent_runner/runtimes/devin.rst`
Expected: `Success! No issues detected.`

- [ ] **Step 3: Commit**

```bash
git add tools/agent_runner/runtimes/devin.rst
git commit -m "docs(agent_runner): describe devin's concatenated stdout (#188)"
```

### Task 3: 統合確認（このセッション）

**Files:** なし（確認だけ。スクリプトは scratchpad に置く）

**テストの要否:** 書かない。Task 1 のテストと、既存の入口の実行で確かめる。

- [ ] **Step 1: C7 — 実際の 2 件に新しい `collect` を当てる**

  scratchpad のスクリプトで、`/workspaces/reso-world/tmp/agents/issue-155.8zy2dh0_/loop/cycle1/runner/4c8509e10b9f42d2a9261ab934ca53fe/attempt-1/` と `/workspaces/reso-world/tmp/agents/issue-157.e6surmvx/review/cycle-1/runner/6d5531268ba24ba58823abd9e3555fc8/attempt-1/` を、元のファイルを変えずに一時ディレクトリへ複写し、JSON の役割の `AdapterContext` で `ADAPTER.collect` を呼ぶ。
  Expected: 2 件とも `status == "success"`、payload が最後の発話を `_json_object` で読んだ値と一致する

- [ ] **Step 2: C6 — README の「テスト」の入口（ワールドの行を除く）**

Run: `bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`uv run pytest tests/skills .agents/skills .agents/scripts tools`
Expected: どれも終了コード 0。環境の要因で失敗したら、変更と無関係であることを `origin/main` の同じ結果と比べて示す

- [ ] **Step 3: C8 — `git diff origin/main` を読み、docstring・rst・コードの規則が一致し、除外範囲のファイルに変更が無いことを確かめる**

- [ ] **Step 4: ブランチ全体のレビュー**（executing-plans の手順に従う）

## 実行予算

- Issue 全体の能動時間: 150 分（Task 3 つ、似た規模の #179・#180 の 1 サイクル分の実績から）。ledger: `/workspaces/reso-world/tmp/agents/issue-188.enxvpyw6/budget.jsonl`
- phase の目安: 準備・Spec・Plan 40 分、Task 1 35 分、Task 2 15 分、Task 3・全体レビュー 35 分、push・PR 15 分、予備 10 分
- worker: 子の実装担当は使わない。長いコマンドは `uv run pytest tests/skills .agents/skills .agents/scripts tools`（期限 20 分、無進捗 10 分で打ち切り）と、全体レビューのサブエージェント（期限 30 分）
- 再試行の上限: 同じ失敗（同じ signature）の再試行は 1 回まで。安全の失敗（範囲外の変更・秘匿値の露出）は再試行しない
- checkpoint: phase の境界、予算の 50%（75 分）・100%、失敗の直後
- 縮小・切り出し・方法変更の候補: runner を通すテスト（`test_end_to_end_tool_run_collects_final_answer`）を省き単体のテストに絞る。rst の観測の記述を最小にする。C7 で文字列の一致が成り立たない形が見つかったら、(a) の判定をやめて止まり、Issue に観測を書く（(b)・(c) への切り替えは推奨案の範囲を超えるので、自分で決めない）

## Contingency

- `check-layout.sh` が環境の要因（resoloop のスキルの同期など）で失敗したら、`origin/main` の checkout（`PARENT_ROOT`）で同じ結果になることを示し、PR に書く
- 既存のテストが、揃えた入力でも別の理由で失敗したら、`superpowers:systematic-debugging` で原因を調べ、規則の変更が既存の負例の意図を壊していないかを先に確かめる

## 完了

（実装後に記録する）
