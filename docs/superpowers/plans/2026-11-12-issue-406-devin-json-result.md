# Issue #406 devin json_result 移植 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** devin の最後の発話が「文章 → JSON」の形でも完了した作業を受け取れるように、agent-workspace の `json_result.py` を移植して devin adapter の回答読み取りに使う。

**Architecture:** `tools/agent_runner/adapters/json_result.py` を byte 一致で移植し、devin の `_payload` だけを `json_object()` に置き換える。#188 の隔離（最後の発話だけ読む・stdout が回答で終わる確認）と認証・承認の診断はそのまま保つ。

**Tech Stack:** Python 3.14 / uv / pytest（偽 CLI のみ。実 CLI・モデル・API は起動しない）

**Spec:** `docs/superpowers/specs/2026-11-12-issue-406-devin-json-result-design.md`

## Global Constraints

- 移植元: usaturn/agent-workspace @ `f65dd6a23f1d8b9bdaa3b68d9cfbe607c25ec822` の `tools/agent_runner/adapters/json_result.py`（345 行・sha256 `a636a027b87cdfa095e838f30a0d4ba1ad49c22a4ba33225428c3f4368495bac`）。スキャナを書き直さない
- 編集してよいファイルは Task 1 の Files の 5 つだけ。他 adapter（claude_code・codex・cursor・pi）・runner 本体・設定・helper は変更しない
- `collect` の `_final_agent_message`・`_ends_with`・`_plain_tail`・`_failure_status`・`_export_failure` と `prepare` のプロンプト指示（`Return the final answer as one nonempty JSON object, without surrounding prose.`）は変更しない
- Python は uv 必須（`python3` コマンドを使わない）。CI は作らない・有効にしない
- テストは AGENTS.md の「テストの採用基準」: S の代表 1 件ずつ。守りはそれを実装しているモジュールのテストに置く。同じ守りの層またぎ重複は代表 1 件（D）。拒否のテストには正しく通る例を 1 件残す
- 日本語表現の規則（AGENTS.md）: 「正本」「着地」「契約」「原子的」などを使わない

## Review Focus

- 最後の発話が文章だけで途中の発話に JSON があるとき、古い JSON を拾って success にしない（隔離の維持。T1）
- 壊れた object 候補（閉じた fence 内の壊れた wrapper・fence をインラインスパンが横切る壊れた訂正）から内部・直前の有効 JSON を救済しない（U1・U2）
- 途切れた JSON を前の有効 JSON にフォールバックさせない（U3）
- 訂正の形で古い JSON でなく最後の有効 JSON を payload にする（T2 の correction ケース）
- stdout が回答で終わる確認と認証・承認の診断の優先が変わらない（既存テスト 40 件で回帰確認）

## 受け入れ基準（Spec と同じ本文・実装担当とレビュー担当の双方に渡す）

### 動作環境

- Dev Container（Ubuntu 26.04 LTS、Python 3.14、uv）。devin CLI 3000.12.x の出力の形
- テストは偽の CLI（`tools/agent_runner/tests/adapters/devin/fake_cli.py`）と手元に残る実際の出力だけ。実 CLI・モデル・API は起動しない

### 実入力

1. 本文の形: 最後の発話が複数行の文章（日本語・英語混在、backtick を含む）→ 空行 → JSON object（`All done — the setup script is tracked as 100644, ...` + `{"status": "DONE", "commit": "d747b6f3...", ...}`）
2. コメントの形: 文章の後に ```` ```json ```` fence 付きの JSON
3. 訂正の形: 古い fence 付き JSON → 文章（日本語）→ 新しい fence 付き JSON

### 防御範囲（対象）

- 上の 3 形で `success`、payload は最後の有効な JSON object と一致（訂正では新しい JSON）
- JSON の後ろに文章が続く形・インデントされた JSON も受け付ける（コミットする陽性対照は上の 3 形）
- 散文中の `{name}` は object 候補にしない

### 防御範囲（対象にしない反例）

- 最後の発話が文章だけ → `response_failed`（途中の発話の JSON を拾わない）
- JSON が途中で切れている・壊れた object 候補がある → `response_failed`（前の有効な JSON にフォールバックしない）
- stdout が回答で終わる確認と認証・承認の診断の扱いは変えない
- 他 adapter への展開は別 Issue（ここでは変更しない）

## 要件照合（実装前・convergence.md「1. 実装前の要件照合」）

| Spec の条件 | 担当 | 観測する結果 | 検証方法 |
| --- | --- | --- | --- |
| 受け入れ 3 形で success・payload は最後の有効 JSON（防御範囲・対象） | Task 1 | T2 の 3 ケースが RED→GREEN | 偽 CLI 端到端。入力は #402・#401 の実記録の形から独立に構成 |
| 文章だけの最終発話は response_failed・途中の JSON を拾わない（反例） | Task 1 | T1 が移植前後で green | devin adapter テスト（#188 の隔離） |
| 途切れ・壊れた候補は response_failed・フォールバックしない（反例） | Task 1 | U1〜U3 が green | json_result 単体テスト |
| 散文中の `{name}` は候補にしない | Task 1 | U4 が green | json_result 単体テスト（拒否テストの陽性対照を兼ねる） |
| `_ends_with`・認証/承認の診断は不変 | Task 1 | 既存 40 件が green | devin + parser_regressions の回帰 |
| 他 adapter へ展開しない | Task 1 | 差分は Files の 5 ファイルのみ | `git diff --stat` |
| 移植は byte 一致 | Task 1 | sha256 が固定値と一致 | `sha256sum` |
| ドキュメントが挙動と一致 | Task 1 | rst が移植後の挙動を記述 | diff の確認 |
| リポジトリ全体の回帰 | 統合検証（controller） | 全体 pytest・run-tests.bash・check-layout.sh が pass | 実行ログ（SESSION に記録） |
| 実 evidence の救済 | 統合検証（controller） | evidence stdout の最後の発話が success・payload 一致 | SESSION の再生スクリプト |

共有条件: Task は 1 つで、複数 Task 間の共有入力・状態・順序は無い。外部仕様（devin CLI の出力形）は実記録（#402 の stdout・#401 のコメント）を根拠にし、fixture は実装の仮定からでなく実記録の形から構成する。移植の正は外部リポジトリの固定 revision の sha256 で独立に照合する。

## Task 1: json_result の移植と devin への組み込み（TDD）

**Files:**
- Create: `tools/agent_runner/adapters/json_result.py`
- Create: `tools/agent_runner/tests/adapters/test_json_result.py`
- Modify: `tools/agent_runner/adapters/devin.py`（`_json_object` 削除・import 追加・`_payload` 置換・docstring 追記）
- Modify: `tools/agent_runner/runtimes/devin.rst`（「観測する情報と完了条件」の JSON の行）
- Test: `tools/agent_runner/tests/adapters/devin/test_adapter.py`

**Interfaces:**
- Consumes: 移植元 `json_result.json_object(text: str) -> dict[str, object] | None`（最後の有効 object。壊れた候補は None）
- Produces: devin `_payload(text, shape)` が `json_object` を使う。他ファイルから見た devin の公開インターフェース（`ADAPTER.prepare` / `ADAPTER.collect`）は変わらない

**テストの要否:** 必要（S）。誤った payload・壊れた回答を成功として受け取らない守り（U1〜U3・T1）と、完了した作業が捨てられる本 Issue の損害の再発防止（T2 の陽性対照）。U4 は拒否テストに伴う「正しく通る例」（AGENTS.md の要件）。配置の理由は Spec D5（設計レビュー concern D1 の採用）。

- [ ] **Step 1: devin の失敗するテストを書く（T1・T2）**

`tools/agent_runner/tests/adapters/devin/test_adapter.py` の末尾に次を追加する。既存の `_export`・`_collect`・`_tool_run_export`・`_devin_config`・`_runtime_agent`・`_PROGRESS` はそのまま使う。

````python
# #406: the final agent message may start with prose and end with the JSON
# result. The shapes below are the real failures from #402 (implement) and
# #401 (spec review), exercised through the fake CLI and the runner path.
_PROSE_BODY = (
    "All done — the setup script is tracked as 100644, matching the other "
    "`setup_pi*.zsh` scripts (they're invoked as `zsh scripts/…`). "
    "Tree is clean after the linear commit on `03fb4c29`.\n"
    "セットアップは完了しました。"
)
_BODY_PAYLOAD = {"status": "DONE", "commit": "d747b6f3"}
_REVIEW_PAYLOAD = {"status": "completed", "findings": []}
_CORRECTED_PAYLOAD = {"commands": ["validation completed"], "details": {"note": "訂正後"}}
_CORRECTION_FINAL = (
    '```json\n{"commands": []}\n```\n'
    "先ほどの報告は誤りです。訂正します。\n"
    "```json\n" + json.dumps(_CORRECTED_PAYLOAD, ensure_ascii=False) + "\n```"
)


def test_prose_only_final_does_not_borrow_earlier_json(
    context: AdapterContext,
) -> None:
    # The isolation of #188: only the final agent message is the answer. An
    # earlier agent step's JSON must not rescue a prose-only final message.
    final = "All done — no JSON in this message."
    export = _tool_run_export(final)
    cast(list[object], export["steps"]).insert(
        -1,
        {
            "source": "agent",
            "message": '{"status": "DONE"}',
            "tool_calls": [
                {"tool_call_id": "call-j", "function_name": "read", "arguments": {}}
            ],
        },
    )
    stdout = "".join(_PROGRESS) + '{"status": "DONE"}' + final + "\n"
    outcome = _collect(context, stdout, export=export)
    assert outcome.receipt is not None
    assert outcome.receipt.status == "response_failed"
    assert outcome.receipt.payload is None


@pytest.mark.parametrize(
    "final,payload",
    [
        (_PROSE_BODY + "\n\n" + json.dumps(_BODY_PAYLOAD), _BODY_PAYLOAD),
        (
            "I've completed a thorough review of the spec.\n\n```json\n"
            + json.dumps(_REVIEW_PAYLOAD)
            + "\n```",
            _REVIEW_PAYLOAD,
        ),
        (_CORRECTION_FINAL, _CORRECTED_PAYLOAD),
    ],
    ids=["prose-then-json", "prose-then-fenced-json", "correction"],
)
def test_fake_cli_prose_then_json_payload_is_received(
    repository: Path, tmp_path: Path, final: str, payload: dict[str, object]
) -> None:
    fixture = tmp_path / "export.json"
    fixture.write_text(json.dumps(_export(message=final)), encoding="utf-8")
    out = tmp_path / "out.txt"
    out.write_text(final + "\n", encoding="utf-8")
    config = _devin_config(
        _runtime_agent(
            tmp_path, "--fake-export", str(fixture), "--fake-stdout", str(out)
        )
    )
    batch = run_workflow(
        config, "audit", "PROMPT", repository, output_dir=tmp_path / "run"
    )
    assert batch.state == "success"
    attempt = batch.results[0].attempts[0]
    assert attempt.state == "success"
    assert attempt.payload == payload
````

- [ ] **Step 2: RED を確認する**

Run: `uv run pytest tools/agent_runner/tests/adapters/devin/test_adapter.py -q`
Expected: T2 の 3 ケース（prose-then-json・prose-then-fenced-json・correction）が FAIL（現行 `_json_object` は文章で始まる回答を読めない）。T1 と既存テストは PASS。FAIL がこれら以外（T1 の FAIL・既存テストの FAIL）なら、前提が違うので実装を進めずに報告する。

- [ ] **Step 3: json_result.py を移植する**

依頼プロンプトにインラインで渡す移植元ソース（usaturn/agent-workspace @ `f65dd6a23f1d8b9bdaa3b68d9cfbe607c25ec822`・345 行）を、そのまま `tools/agent_runner/adapters/json_result.py` に書く。書き写し・簡略化・再フォーマットをしない。

Run: `sha256sum tools/agent_runner/adapters/json_result.py`
Expected: `a636a027b87cdfa095e838f30a0d4ba1ad49c22a4ba33225428c3f4368495bac`

- [ ] **Step 4: json_result の単体テストを書く（U1〜U4）**

`tools/agent_runner/tests/adapters/test_json_result.py` を新設する:

````python
"""json_result: rejection boundaries of the ported parser (#406).

The guards live here because json_result implements them (AGENTS.md: put a
guard in the tests of the module that implements it). The acceptance shapes
through the runner path are covered by the devin fake-CLI tests.
"""

import json

from tools.agent_runner.adapters.json_result import json_object


def test_malformed_wrapper_rejects_complete_inner_object() -> None:
    inner: dict[str, object] = {"status": "DONE", "commit": None}
    text = "```json\n" + '{"result": ' + json.dumps(inner) + ', "note": invalid}\n```'
    assert json_object(text) is None


def test_broken_correction_inside_fence_crossed_by_inline_span() -> None:
    done: dict[str, object] = {"status": "DONE", "commit": None}
    text = (
        "```json\n" + json.dumps(done) + "\n```\n"
        'Fix `name is required:\n```json\n{"status": 123\n```\n'
        "Then `pytest` later."
    )
    assert json_object(text) is None


def test_truncated_candidate_does_not_fall_back_to_earlier_object() -> None:
    text = '{"ok": true}\nDone.\n{"status": "DONE",'
    assert json_object(text) is None


def test_prose_before_object_is_a_passing_candidate() -> None:
    # The passing example required alongside the rejection guards: prose does
    # not hide a valid object, and a prose brace is not a candidate.
    assert json_object('Use {name} here.\nDone.\n{"ok": true}') == {"ok": True}
````

Run: `uv run pytest tools/agent_runner/tests/adapters/test_json_result.py -q`
Expected: 4 件 PASS（移植したパーサの拒否境界と陽性対照。移植が byte 一致で正しければそのまま通る）

- [ ] **Step 5: devin.py を組み替える**

- `from tools.agent_runner.adapters.json_result import json_object` を追加（`from tools.agent_runner.adapters.skills import prompt_lines` の前）
- `_payload` の `parsed = _json_object(text)` を `parsed = json_object(text)` に置換
- `_json_object` 関数（`def _json_object` から `return cast(...) ...` まで）を削除
- モジュール docstring の `Only local parsing happens here; this module never starts a process.` の前に、回答の読み取りが `json_result.json_object`（文章の後の JSON を受け付け、最後の有効 object を採用）である旨の 1 文を追加
- それ以外（`_ends_with`・`_plain_tail`・`_final_agent_message`・`_failure_status`・`_export_failure`・`prepare`・`collect` の構造）は変更しない

- [ ] **Step 6: GREEN を確認する**

Run: `uv run pytest tools/agent_runner/tests/adapters/devin tools/agent_runner/tests/adapters/test_json_result.py tools/agent_runner/tests/adapters/test_parser_regressions.py -q`
Expected: 全て PASS（既存 40 件 + 単体 4 件 + devin 新規 4 件 = 48 件）

- [ ] **Step 7: devin.rst を更新する**

「観測する情報と完了条件」の 39 行目付近:

```
JSON 形式の役割では最終 ATIF 応答が空でない JSON object であることを求め、payload は最終 ATIF 応答から取り出す。
```

を次に置き換える:

```
JSON 形式の役割では、最終 ATIF 応答を ``json_result.json_object`` で読み、payload は最後にデコードできた JSON object とする。
文章の後に JSON が続く形（fence 付きを含む）を受け付け、訂正では最後の有効な object を採用する。
壊れた object 候補がある場合は応答全体を拒否し、前の有効な JSON にフォールバックしない。
閉じたインラインコード span・閉じた非 JSON fence の中の壊れた候補は拒否に使わない（移植元の既知の限界は ``json_result`` の docstring に従う）。
最後の発話だけを読み、途中の発話や stdout から JSON を探さない隔離は変わらない。
```

- [ ] **Step 8: tools 全体で回帰を確認する**

Run: `uv run pytest tools -q`
Expected: 全て PASS

- [ ] **Step 9: commit する**

```bash
git add tools/agent_runner/adapters/json_result.py tools/agent_runner/tests/adapters/test_json_result.py tools/agent_runner/adapters/devin.py tools/agent_runner/runtimes/devin.rst tools/agent_runner/tests/adapters/devin/test_adapter.py
git commit -m "fix: accept prose before JSON in devin final answer via json_result port (#406)"
```

## 統合検証（controller が実行・runner の担当には依頼しない）

1. `uv run pytest tests/skills .agents/skills .agents/scripts tools`（リポジトリ全体の Python テスト）
2. `bash .devcontainer/run-tests.bash`
3. `bash scripts/check-layout.sh`
4. 実 evidence の再生: `tmp/agents/issue-402.ht7fd2ih/task-2-failed-evidence/stdout.log` の最後の発話を移植後の collect に通し、success と payload の一致を確認（SESSION の一時スクリプトで実行）
5. Spec→Plan→Task→実行証拠の条件単位の照合（review-fix-planning の convergence.md「3. 検証と閉じ方」）
6. 検証の記録（HEAD・status が空・argv と終了コード・ログの完全パス）を SESSION に保存し、`finalize.py` の `--checks-file` の形でも保存

## 実行方式と理由

- SDD 形。Task 1 は `implement_task.py run --implement pi_alibaba_qwen4-max_max` で runner の担当に依頼する（`--implement` 明示・check の `self: false`）。並行しない
- Task のレビューは controller が review package を作って別 context のレビュアーに依頼する（同じ受け入れ基準の本文を渡す）
- 統合検証と最後の全体レビューは controller の責任。全体レビューは別 context のレビュアーに依頼する
- 理由: 変更は 5 ファイルに凝集し、TDD の RED/GREEN を 1 Task で完結できる。担当は利用者の明示指定

## 実行予算

- Issue 全体の能動時間: 360 分（ledger: `tmp/agents/issue-406.95mq71g7/budget.jsonl`）。根拠: 実装は 1 Task の小さな移植（#402 の実 Task は 502〜1197 秒の実績）、レビュー 2 回（各期限 30 分）、ループは最大 3 サイクル
- phase の目安: 準備 40 分（完了）/ 設計レビュー ≤30 分 / Spec レビュー ≤30 分（再レビュー ≤30 分）/ Plan 20 分 / 実装 ≤90 分 / Task レビュー 15 分 / 統合検証 20 分 / PR 10 分 / ループ ≤3 ×（レビュー 45 分 + 計画・修正 45 分）
- worker の期限: runner の役割の期限に従う（implement 5400 秒・design-review / spec-review 1800 秒・inspect 2700 秒）。runner が期限と停止確認を管理する。controller は完了通知を待ち、約 10 分ごとに attempt のログの mtime・末尾で進捗を確認する
- 再試行の上限: 同じ失敗の再試行は 1 回まで（budget の既定）。Task の `retry`（BLOCKED・NEEDS_CONTEXT）は新しい依頼で 2 回まで。`rejected` は 1 回まで依頼し直す。レビューの失敗（state: failed・status: incomplete）は issue-to-pr の停止条件に従い止まる
- checkpoint: phase の境界・予算の 50%（180 分）・100%（360 分）・worker 失敗の直後。`issue_budget.py show` で数えて判断を ledger に残す
- 縮小・切り出し・方法変更の候補: 実装の再試行が尽きたら停止して報告（controller が self で引き取らない）。ループがサイクル上限に達したら修正 push 済みで未完了報告。担当の認証・モデルの失敗が続く場合は停止して利用者の裁定（担当変更）を待つ。持ち越し候補は Spec の「持ち越し候補」のとおり

## contingency（代替策）

- 最初の RED で実出力・API の前提が異なると判明した場合: 仕様の意味を保つ最小修正を ledger に残して継続する。意味が変わる場合は停止して利用者の裁定を待つ
- 移植ソースの sha256 が一致しない: 固定 revision から再取得して照合し直す。それでも一致しなければ停止（書き写しの誤りを推測で直さない）
- runner の認証失敗（MAAS_ANTHROPIC_TOKEN）: 起動時に `ANTHROPIC_AUTH_TOKEN` の値をワンショットで渡していることを確認し、env の有無を確かめる。資格情報を推測・探索しない。解消しなければ停止
- main が進んだ場合: Spec D9 の追随手順（fast-forward に限り再捕捉 → rebase → 再検証）。祖先でなくなったら停止
- gitleaks の検出: AGENTS.md の「push の前の秘密情報の検査」の 3 条件を満たす場合だけその commit を直して検査・検証をやり直す。満たさなければ停止
- 検証の失敗: systematic-debugging で調べ、解消できなければ停止