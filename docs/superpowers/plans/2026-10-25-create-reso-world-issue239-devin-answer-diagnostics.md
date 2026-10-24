# Issue #239: Devin の adapter が、モデルの発言を CLI の診断とみなさないようにする Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Devin の adapter が、認証・承認待ちを標準エラーと export の error の step だけで判定し、標準出力と最終 ATIF 応答（モデルの発言）の引用で正しい回答を捨てないようにする。

**Architecture:** `Devin.collect` の判定を「標準エラー → export の error の step → 最終 ATIF 応答と標準出力の終わりの照合 → それ以外は `response_failed`」にする。`_plain_tail` は JSON のような行だけを見る。使わなくなる `_DIAGNOSTIC_LINE` を消し、`devin.rst` を同じ判定に書き換える。

**Tech Stack:** Python 3.14、pytest（`uv run --locked`）

**Spec:** `docs/superpowers/specs/2026-10-25-create-reso-world-issue239-devin-answer-diagnostics-design.md`

## 管理

- 状態: draft
- 対象 Issue: https://github.com/usaturn/create-reso-world/issues/239
- DOC_ROOT・CODE_ROOT: `/workspaces/reso-world/.worktrees/issue-239-devin-answer-diagnostics`（branch `fix/issue-239-devin-answer-diagnostics`、基準 `origin/main` の `bdbe02b`）
- 実行許可: Spec の「管理」と同じ（`--merge`）
- 実行方式: inline（`superpowers:executing-plans`）。`implement_task.py check` の `self` が true。Task は 1 つで、実装・テスト・`devin.rst` が同じ判定の規則を書くので、委譲する文脈の手間より同じ文脈で進める方が小さい。最後にブランチ全体のレビューを別のサブエージェントで行う
- セッションディレクトリ: `/workspaces/reso-world/tmp/agents/issue-239.ctc8zcjz`（ledger `budget.jsonl`、一時的な再現 `repro.py` とログ、変異の確認、検証のログ）

## Global Constraints

- 認証・承認待ちの判定は、標準エラー（`_failure_status(stderr)`）と export の error の step（`_export_failure(export)`）だけで行い、回答の確認より先に返す。標準出力と最終 ATIF 応答は `_ends_with`・`_payload` にだけ使う
- 標準エラーと export に失敗が無く、回答も無いときは `response_failed`（標準出力の語を見ない）
- `_plain_tail(tail: str) -> bool` は「どの行も `line.lstrip()` が `{`・`[`・```` ``` ```` で始まらない」だけを返す
- 変えない: `_AUTH`・`_APPROVAL`・`_failure_status`・`_export_failure`・`_final_agent_message`・`_ends_with`・`_json_object`・`_payload`・`prepare`、runner、他の adapter、`interfaces.rst`
- テストは偽の出力だけを使い、実際の devin を起動しない（AGENTS.md）。採用基準の S だけを書く
- コードのコメントは英語（ファイルの既存の書き方）、`devin.rst` は日本語

## Review Focus

1. 本当の未ログイン（標準エラーに実機の `Error: Login canceled`、export なし）は、今までどおり `awaiting_authentication`
2. 回答の無い実行で、発話が login・authentication に触れている: `response_failed`（`awaiting_authentication` にしない）
3. 標準出力の回答の後ろに、認証の語を含む普通の行がある（終了コード 0）: `success`（Spec の D-3。CLI の失敗は標準エラーと非 0 終了で現れ、runner が非 0 終了を `response_failed` にする）
4. text 形式の役割で、最終応答のコードブロックに診断の引用がある: `success` で、全文が payload
5. 承認の語（`Approval required`・`waiting for approval`・`workspace trust`）の引用: `awaiting_approval` にしない

2 は Task 1 の新しいテストで確かめる。1・3・4・5 は、新しいテストと同じ守りの別の組み合わせ（採用基準の D）なのでコミットするテストにせず、Task 1 の Step 7 の一時的な再現で確かめる。

## 実行予算

- Issue 全体の能動時間の予算: 310 分。ledger は 2026-10-24T16:00:04Z に開始した（その前の調査は約 15 分。完了の記録で直した）。Plan を書いた時点で、`--merge` のループの段階を含めるため 240 分から決め直した（ledger の checkpoint に記録）
- phase の目安: 調査・Spec・Plan 45 分、Task 1 20 分、全体の検証 25 分、ブランチ全体のレビュー 15 分、PR の作成 10 分、PR 修正ループ最大 3 サイクル × 約 65 分（レビューの期限 45 分＋計画・修正 20 分）
- worker の期限: ブランチ全体のレビューのサブエージェントは 20 分。ループのレビュアーの期限はループの設定（`inspect` は 2700 秒）
- 再試行の上限: 同じ signature の信頼性の失敗（pytest・`run-tests.bash` の一時的な失敗、gh・GitHub の API の一時的な失敗）は 1 回まで。安全の失敗は再試行せず止まる
- checkpoint: Task 1 の後、全体の検証の後、PR の作成の後、ループの各サイクルの後、予算の 50%・100%
- 縮小・方法変更の候補: export のテスト（Spec の D-5 の 2 つ目）がレビューで書きすぎと判断されたら外す。ループで devin-swe のレビューが捨てられても（Spec の D-8）、残りのレビュアーで続ける

## 要件と Task・検証の対応

| Spec の条件 | Task | 観測する結果 | 検証 |
| --- | --- | --- | --- |
| 受け入れ条件 1（引用があっても正しい回答は `success`） | 1 | `answer` のケースが `success` で payload を持つ | Step 2 で失敗、Step 5 で成功。Step 7 の再現の 1・4・5 |
| 受け入れ条件 2（標準エラー） | 1 | `test_diagnostics_override_plausible_success` が通る | Step 5。Step 7 の再現の 8・9（実機の標準エラー） |
| 受け入れ条件 2（export の error の step） | 1 | export のテストが `awaiting_authentication` | Step 3（確認を外すと失敗する）、Step 5 |
| D-2（回答の無い実行は `response_failed`） | 1 | `no-answer` のケース | Step 2 で失敗、Step 5 で成功。Step 7 の再現の 6・7 |
| D-3（`_plain_tail` は形だけ） | 1 | `answer` のケース（JSON の後ろの引用） | Step 6 の変異 (c) |
| 形の確認（後ろの JSON、回答で終わらない標準出力、tool を呼ぶ最後の step）は残る | 1 | 既存のテストが通る | Step 5。Step 7 の再現の 12・13 |
| 実機の記録 7 件が変わらない | 1 | 修正の前後で `success` と payload が同じ | Step 7 |
| D-6（文書） | 1 | `devin.rst` の文が実装の判定と一致 | Step 8 |

共有する条件: 実装（`collect`・`_plain_tail`）、テスト、`devin.rst` は同じ判定の規則を書く。統合の確認は Step 8 で `devin.rst` の各文を実装と突き合わせ、ブランチ全体のレビューに Spec・Plan・差分を渡して行う（担当: inline の実装者＝このセッション）。

---

### Task 1: 診断を標準エラーと export の error の step に限る

**Files:**
- Modify: `tools/agent_runner/adapters/devin.py`（docstring 1〜9 行、`_DIAGNOSTIC_LINE` 43〜47 行、`_plain_tail` 59〜64 行、`collect` 236〜256 行）
- Modify: `tools/agent_runner/tests/adapters/devin/test_adapter.py`（`test_text_diagnostic_with_valid_export_is_not_success` 389〜409 行と `test_final_atif_diagnostic_overrides_successful_stdout` 428〜445 行を消し、テストを 2 つ足す）
- Modify: `tools/agent_runner/runtimes/devin.rst`（「観測する情報と完了条件」34〜43 行、「検証と制約」）

**Interfaces:**
- Consumes: なし
- Produces: `Devin.collect` の返す状態の型は変わらない。`_plain_tail(tail: str) -> bool`

**テストの要否:** 要る（採用基準の S。Spec の D-5）。新しいテスト 2 つ（3 ケース）、消すテスト 2 つ。

- [x] **Step 1: テストを書く**

  `_tool_run_stdout` の後ろに置く。

  ```python
  # #239: devin -p prints the model's own messages to stdout, so a review can
  # quote a CLI-looking line in a code block or after its JSON answer.
  _QUOTE = "The adapter logs this on a bad key:\n```\nError: invalid api key\n```\n"
  _QUOTED_FINAL = _FENCED + "\nError: invalid api key above is quoted from the diff."


  @pytest.mark.parametrize(
      "final_tool_calls,state,payload",
      [
          (None, "success", _FENCED_PAYLOAD),
          ([{"tool_call_id": "call-9", "function_name": "exec", "arguments": {}}], "response_failed", None),
      ],
      ids=["answer", "no-answer"],
  )
  def test_quoted_diagnostics_in_model_messages_are_answer_data(context, final_tool_calls, state, payload):
      export = _tool_run_export(_QUOTED_FINAL, final_tool_calls=final_tool_calls)
      # 引用する応答も export の途中の step に入れ、標準出力はすべての応答の連結にする
      read = [{"tool_call_id": "call-q", "function_name": "read", "arguments": {}}]
      cast(list[object], export["steps"]).insert(-1, {"source": "agent", "message": _QUOTE, "tool_calls": read})
      stdout = "".join(_PROGRESS) + _QUOTE + _QUOTED_FINAL + "\n"
      outcome = _collect(context, stdout, export=export)
      assert outcome.receipt is not None and outcome.receipt.status == state
      assert outcome.receipt.payload == payload


  def test_export_error_step_authentication_overrides_answer(context):
      export = _tool_run_export()
      # 最終応答の前に error の step を置き、標準出力は最終応答で終わる
      cast(list[object], export["steps"]).insert(-1, {"source": "error", "message": "Error: invalid api key"})
      outcome = _collect(context, _tool_run_stdout(), export=export)
      assert outcome.receipt is not None and outcome.receipt.status == "awaiting_authentication"
      assert outcome.receipt.payload is None
  ```

- [x] **Step 2: 実行して、変更前の失敗を確かめる**

  Run: `uv run --locked pytest tools/agent_runner/tests/adapters/devin/test_adapter.py -q -k "quoted_diagnostics or export_error_step_authentication"`
  Expected: `answer`・`no-answer` の 2 ケースが `awaiting_authentication` で FAIL。export のテストは PASS（今の挙動）

  続けて、`devin.py` が変更前のうちに、`$SESSION/repro.py` へ Review Focus の 3（標準出力の回答の後ろに認証の語の行。終了コード 0 の形）と 5（承認の語の引用）のケースを足して実行し、変更前の結果を `$SESSION/repro-base-bdbe02b.log` に取り直す

- [x] **Step 3: export のテストが確認を守っていることを確かめる（一時的な変異）**

  `devin.py` の `failure = hint or (_export_failure(export) if export is not None else None)` を `failure = hint` に変えて Step 2 と同じコマンドを実行し、export のテストが `success` で FAIL することを確かめる。`git checkout -- tools/agent_runner/adapters/devin.py` で戻し、`git diff --stat` に `devin.py` が無いことを確かめる

- [x] **Step 4: `devin.py` を変える**

  - `_DIAGNOSTIC_LINE` を消す
  - `_plain_tail` から `_failure_status(tail) is None and` を外し、コメントを「後ろに続いてよいのは普通の行で、JSON のような行（完全・途中）は単一の最終応答ではない。語は CLI の診断ではない（#239）」の趣旨にする
  - `collect`: `diagnostics` と `hint` を消し、`failure = _failure_status(stderr) or (_export_failure(export) if export is not None else None)`。直前のコメントは「標準出力と最終 ATIF 応答はモデルの発言で、そこに引用された `Error: invalid api key` は回答のデータ。CLI の失敗を報告するのは標準エラーと export の error の step だけ（#239）」の趣旨。最後の `else` は `status, payload = "response_failed", None`
  - module docstring に「それらの応答はモデルの発言なので、CLI の失敗は標準エラーと export の error の step だけで判定する」の 1 文を足す
  - テストの 2 つ（389〜409 行・428〜445 行）を消す

- [x] **Step 5: テストと静的検査**

  Run: `uv run --locked pytest tools/agent_runner/tests/adapters -q`、`uvx ruff check tools/agent_runner/adapters/devin.py tools/agent_runner/tests/adapters/devin/test_adapter.py`
  Expected: すべて PASS、ruff は終了コード 0

- [x] **Step 6: 変異の確認（一時的。コミットしない）**

  1 つずつ戻して新しいテストを実行し、どれかが FAIL することを確かめる。毎回 `git diff` で `devin.py` を Step 4 の状態に戻す（変異は `$SESSION/mutations/` のパッチで当てて外す）。結果を `$SESSION/mutations.log` に書く
  - (a) 前段の照合に標準出力の行を足す（`_failure_status(stderr, *[行頭が診断の形の stdout の行])`）
  - (b) 前段の照合に最終応答の行を足す
  - (c) `_plain_tail` に `_failure_status(tail) is None and` を戻す
  - (d) 最後の `else` を `_failure_status(stdout) or "response_failed"` に戻す
  - (e) export の確認を外す

  Expected: (a)(b)(c) は `answer`、(d) は `no-answer`、(e) は export のテストが FAIL

- [x] **Step 7: 一時的な再現と実機の記録の再生**

  Step 2 で取った変更前のログと同じスクリプトを、変更後の `devin.py` で実行し、`$SESSION/repro-fix.log` に書いて比べる
  Expected（変更後）: 引用のケース（1・4・5・承認）は `success`、回答の無いケース（6・7）は `response_failed`、実機の標準エラーと export の error の step（8〜10）は `awaiting_authentication`、11〜13 は `response_failed`、回答の後ろの認証の語の行は `success`。実機の記録 7 件は、変更前と同じ `success` と payload のキー

- [x] **Step 8: `devin.rst` を書き換え、実装と突き合わせる**

  - 34〜43 行: 36 行（標準出力と最終 ATIF 応答の診断行を優先する）と 42〜43 行（既知の制限）を消す。39 行の失敗の列挙から「認証・承認の診断」を外す。続けて、認証・承認待ちは標準エラーと export の error の step（`source` が `error`、`is_error` が真、`error` がある step）で判定し成功候補より優先すること、標準出力と最終 ATIF 応答はモデルの発言なので診断に使わないこと、引用があっても正しい回答で終われば成功・回答の無い実行は内容によらず `response_failed` であること（Issue #239）を書く
  - 「検証と制約」: 3000.11.205 で、認証情報の無い一時 HOME の `devin -p` が標準エラーに `Error: Login canceled` を出して終了コード 1 で終わり、標準出力に診断が無く export も作らないことを確かめた（Issue #239。モデルは起動していない）
  - 突き合わせ: `devin.rst` の各文が、Step 4 の `collect` の順（標準エラー → export → 回答 → `response_failed`）と `_plain_tail` の条件に一致すること

- [x] **Step 9: Commit**

  ```bash
  git add tools/agent_runner/adapters/devin.py tools/agent_runner/tests/adapters/devin/test_adapter.py tools/agent_runner/runtimes/devin.rst
  git commit -m "fix(agent_runner): stop treating devin's model messages as CLI diagnostics (#239)"
  ```

## 検証（全体）

- [ ] `bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`uv run pytest tests/skills .agents/skills .agents/scripts tools` の終了コードが 0（README.md の「テスト」。ワールドの行は除く）
- [ ] `git diff --stat origin/main...HEAD` が、Task 1 の 3 ファイルと Spec・Plan だけ
- [ ] 最後の commit の後に検証し、HEAD・`git status --porcelain` が空だったこと・各コマンドの argv と終了コード・ログの完全パスを `$SESSION/verification.md` に、`finalize.py` の `--checks-file` の形のファイルを `$SESSION/checks.json` に置く
- [x] ブランチ全体のレビュー（別のサブエージェント。Spec・Plan・差分を渡す）

## 完了

### 所要時間（PR の作成の前まで。UTC）

- 合計: 約 45 分（着手 15:45 ごろ〜この記録 16:30 ごろ。worktree の作成は 15:49）
- 調査・Spec・Plan: 約 23 分（〜16:08。実機の未ログインの観測、記録 7 件の確認、変更前の再現）
- Task 1: 約 4 分（〜16:12）
- ブランチ全体のレビュー: 約 12 分（16:13〜16:25。サブエージェント、opus）。同じ時間に全体の検証の事前確認を流し、`4590ff4` で 3 つとも終了コード 0（pytest は 1223 passed）

### Plan からの変更（ledger の Ruling）

- SDD の ledger と review package は、worktree の中（`.superpowers/sdd/`）ではなく `$SESSION/sdd/` に置き、`task-start`・`task-done` と同じことを手で行った（AGENTS.md の「コミットしないファイルの置き場所」。#251 の Plan と同じ判断）
- 実行予算の「ledger の開始の前の調査」は約 25 分と書いたが、worktree の作成時刻から数えると約 15 分だった（この記録で直した）

### 検証（Task 1）

| 確認 | 結果 |
| --- | --- |
| RED（変更前の新しいテスト） | `answer`・`no-answer` が `awaiting_authentication` で失敗。export のテストは通過 |
| export の確認を外す変異 | export のテストが `success` で失敗 |
| GREEN | `uv run --locked pytest tools/agent_runner/tests/adapters -q` は 140 passed。`uvx ruff check`（0.17.2）と rstcheck は指摘 0 |
| 変異 (a)〜(e) | (a) は `answer`・`no-answer`、(b)(c) は `answer`、(d) は `no-answer`、(e) は export のテストが失敗（`$SESSION/mutations.log`） |
| 再現と記録の再生 | 変更前 `$SESSION/repro-base-bdbe02b.log`、変更後 `$SESSION/repro-fix.log`。引用のケースは `success`、回答の無いケースは `response_failed`、実機の標準エラーと export の error の step は `awaiting_authentication`、実機の記録 7 件は前後で同じ結果と payload |

### ブランチ全体のレビュー

Critical 0・Important 0・Minor 2（Ready to merge: Yes）。レビュアーは Review Focus の 1〜5 と、D-3 の runner に関する主張を、偽の devin CLI で `run_workflow` を通す確認を含めて独立に確かめた。Minor の 2 件は直さずに持ち越す（executing-plans の規則）。

- `test_diagnostics_override_plausible_success` の値を、実機の `Error: Login canceled` にする（`_AUTH` を狭める変更への備え）
- `devin.rst` の「回答の無い実行は…」に前提（標準エラーと export に失敗が無い）を書き、回答の後ろの CLI の行を使わない理由（D-3）を補う

レビュアーが判断を保留した項目への判断は、ledger（`$SESSION/sdd/progress.md` の `Final: Ruling:`）にある。持ち越しの候補として、既存の `test_export_error_fields_override_answer` が export の確認を守っていないことを、マージの後の再調査で Issue にするか判断する。

### 未確認

- 認証情報が期限切れ・無効のときの devin の出力先（観測したのは、認証情報が無い場合だけ）
- 実際のモデルに引用を含むレビューを出させる確認（Spec の D-7 のとおり行わない）

全体の検証（`run-tests.bash`・`check-layout.sh`・pytest）は、この記録の commit の後に実行し、結果を PR 本文と `$SESSION/verification.md` に書く。
