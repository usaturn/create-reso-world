# Issue #382 Claude Bash timeout cap 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development（issue-to-pr の委任により、実装 Task は agent-runner の担当に `implement_task.py` で 1 件ずつ依頼する。Task レビュー・最終全体レビューは読み取り専用のサブエージェント）。Steps は checkbox（`- [ ]`）で追跡する。

**Goal:** 非対話 claude-code 担当の前景 Bash 上限を role の残り時間から導出し、既定 10 分を超える正常な検証（実測約 14 分）を role 期限内で完走できるようにする。

**Architecture:** `ClaudeCode.prepare` が `context.request.deadline_seconds`（runner が渡す残り時間）から `BASH_MAX_TIMEOUT_MS = max(600000, int((残り - 120秒) * 1000))` を計算して `LaunchSpec.env` に追加する。既定 `BASH_DEFAULT_TIMEOUT_MS=600000` と背景化無効は維持し、プロンプトに実上限を伝える 1 行を足す。runner の外側の期限・停止確認・`_classify` は変更しない。

**Tech Stack:** Python 3（uv 管理）、pytest、agent-runner（tools/agent_runner）。検証プローブは Node vm（native 計算抽出）と bash の fake CLI。

**Spec:** `docs/superpowers/specs/2026-11-12-issue-382-claude-bash-timeout-cap-design.md`

## Global Constraints

- env の 3 値: `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS="1"`、`BASH_DEFAULT_TIMEOUT_MS="600000"`、`BASH_MAX_TIMEOUT_MS=str(max(600000, int((context.request.deadline_seconds - 120.0) * 1000)))`。
- 変更してよいファイル: `tools/agent_runner/adapters/claude_code.py`（prepare のみ）と `tools/agent_runner/tests/adapters/claude_code/test_adapter.py`（テスト 1 件の追加）。
- 変更しない: `_classify`・`collect`、`runner.py`・`process.py`、他 adapter、`.devcontainer/agent-runner.toml`、runtime 文書（`tools/agent_runner/runtimes/*.rst`・`.devcontainer/README.md`）、対話用 `.claude/settings.json`、既存テスト、個人設定・共有 HOME。
- Python は uv 必須。`python3` コマンドを使わない。リポジトリの Python ツールも `uv run` で実行する。
- テストは AGENTS.md の採用基準で S の 1 件だけ。F（固定値照合）・L（気付ける）・D（重複）のテストは追加しない。
- プロンプトの案内行は英語 1 行で、result_shape の行の後に置く。env の上限と同じ値を伝える。
- commit メッセージは `Co-Authored-By: Claude Code <noreply@anthropic.com>` で終える。
- 作業は feature worktree（`CODE_ROOT`）の中だけ。runner 担当は `AGENT_RUNNER_DEPTH=1` で入れ子起動できない。

## Review Focus

テスト以外で reviewer が注意すべき入力・条件（Spec が含意するが Task のテストが直接確かめないもの）:

1. 小数の残り時間（例 1800.5 秒）: `int()` の切り捨ては予約 120 秒を侵食しない方向（切り上げない）であること。→ Task 1 のテストに `1800.5 → 1680500` のパラメータで固定。
2. プロンプト案内の上限値と env の上限値が同じであること（乖離すると担当が誤った timeout を要求する）。→ Task 1 のテストが stdin に `str(cap)` が含まれることを確認。
3. 残り時間が短い role（60 秒）でも下限 600000 を割り込まないこと（現行挙動の維持）。→ Task 1 のテストに `60.0 → 600000`。
4. 既定 timeout（600000）は margin を引かれず、変わるのは MAX だけであること。→ Task 1 のテストが全パラメータで `BASH_DEFAULT_TIMEOUT_MS == "600000"` を確認。
5. 差分のスコープ: prepare と新テスト以外に変更がないこと（`_classify`・collect の判定を緩めていない）。→ テストではなく diff の照合（Task レビュー・最終レビュー・controller の検証）。

## 受け入れ基準

Spec の「受け入れ基準」をそのまま適用する（実装担当・Task レビュー担当の双方の brief に写す）:

- 動作環境: Dev Container の uv / Python、非対話 agent-runner の claude-code adapter。導入済み Claude Code CLI 2.1.322（timeout 計算のプローブはこの版で取り直す）。
- 実入力: `request.deadline_seconds` = 5400 / 2700 / 1800 / 720 / 60 秒。日本語・改行を含む prompt（例「確認する\n結果を返す」）で argv・stdin の既存仕様を保つ。
- 防御範囲: runner の当該 CLI 子プロセスの env だけに適用する。親環境・対話設定・共有設定は書き換えない。対象外の反例: 対話の claude（env 変更なし）、他 runtime の adapter（変更なし）、親環境の `BASH_MAX_TIMEOUT_MS`（allowlist に無く継承されない）、個人設定の短い期限（外側の runner 期限が優先）。
- 条件:
  1. 背景化無効のまま、既定 10 分を超え role の残り期限内に収まる正常な検証を完走できる上限になること（現行最短 1800 秒で導出上限 1680000ms > 実測 833.97 秒）。既定 600000 と背景化無効は維持。
  2. 上限は `max(600000, int((残り秒数 - 120) * 1000))` であること。残り時間が 720 秒以上のときは残り時間から 120 秒の予約を引いた値を超えず、常に下限 600000 を下回らない（短い role では下限が優先し、runner の外側の期限が引き続き優先する）。runner の期限・停止確認は変更しない。
  3. `_classify` の最後の result・後続イベント・permission_denials の判定を緩めない（差分が prepare とテストに限定され、既存分類の回帰が通ること）。
  4. 短い通常コマンドと、既定上限を超えるが role 期限内の長いコマンドを対照にして確認すること。fake/一時プローブを使い、有料モデルの反復は行わない。
  5. 親の対話セッション・共有設定を変更しないこと。

## 実行方式と理由

- 実装: `superpowers:subagent-driven-development` の形で、Task を agent-runner の `pi_alibaba_qwen4-max_max` に `implement_task.py` で 1 件ずつ依頼する（`implement_task.py check`: self=false、agents=[pi_alibaba_qwen4-max_max]、fallback=[]。利用者の `--implement` 明示）。並行しない。
- runner 起動には `MAAS_ANTHROPIC_TOKEN="${ANTHROPIC_AUTH_TOKEN:?}"` をワンショット前置する（利用者の追加指示。piaq の allowlist 経由で子に届く。値はログ・文書に出さない）。
- Task レビュー: 読み取り専用サブエージェント 1 名（Agent tool、model: sonnet。小さな機械的 diff のため mid-tier）。brief・report・review package の 3 パスと Global Constraints・受け入れ基準を渡す。
- 最終全体レビュー: 読み取り専用サブエージェント 1 名（Agent tool、model: fable。SDD の Model Selection で利用可能な最上位）。merge base から HEAD の package を渡す。
- controller の検証: native 計算プローブ・fake CLI 対照プローブ（実装前/後）・README の 3 入口。プローブはコミットせず SESSION に置く。
- PR 作成後: `--merge` のレビュー修正ループ（最大 3 サイクルは既定の適用。inspect=pi_alibaba_qwen4-max_max,claude-code_sonnet_xhigh、implement=pi_alibaba_qwen4-max_max は利用者指定。self-review/fix-check は既定 self）。

## Task 1: adapter の上限導出とテスト（runner 担当）

**Files:**
- Modify: `tools/agent_runner/adapters/claude_code.py`（`prepare` とモジュール定数）
- Test: `tools/agent_runner/tests/adapters/claude_code/test_adapter.py`（テスト 1 件追加）

**Interfaces:**
- Consumes: `AdapterContext.request.deadline_seconds`（float、残り秒。runner.py が worktree 準備後に設定）、`LaunchSpec(argv, stdin, env)`。
- Produces: `prepare` が返す `LaunchSpec.env` に `BASH_MAX_TIMEOUT_MS`（文字列のミリ秒）。プロンプト stdin に上限値を含む案内行。後続 Task はない。

**テストの要否:** 要（S）。誤った上限はエラーにならず、必要な検証の silent な打ち切り（未検証の成果・有料実行枠の損失）や、role 期限全体の消費による最終 result の損失につながる。入力→出力の単体テストなので F ではない。env 配送は `test_workflow_preserves_literal_environment` がガード済み（D のため追加しない）。分類の回帰は既存テストが担保（D）。

- [ ] **Step 1: 失敗するテストを書く**

`tools/agent_runner/tests/adapters/claude_code/test_adapter.py` の末尾に追加する:

```python
@pytest.mark.parametrize(
    ("deadline_seconds", "expected_cap_ms"),
    [
        pytest.param(5400.0, 5280000, id="implement"),
        pytest.param(2700.0, 2580000, id="inspect"),
        pytest.param(1800.0, 1680000, id="fix-check-shortened"),
        pytest.param(1800.5, 1680500, id="fractional-remaining"),
        pytest.param(720.0, 600000, id="floor-boundary"),
        pytest.param(60.0, 600000, id="short-role-floor"),
    ],
)
def test_prepare_caps_bash_timeout_by_request_deadline(
    context: AdapterContext, deadline_seconds: float, expected_cap_ms: int
) -> None:
    # S: a wrong cap silently truncates required verification, or lets one
    # command spend the whole role deadline and lose the final result.
    context.request.deadline_seconds = deadline_seconds
    spec = ADAPTER.prepare(context)
    assert spec.env["BASH_MAX_TIMEOUT_MS"] == str(expected_cap_ms)
    assert spec.env["BASH_DEFAULT_TIMEOUT_MS"] == "600000"
    assert spec.env["CLAUDE_CODE_DISABLE_BACKGROUND_TASKS"] == "1"
    assert str(expected_cap_ms) in spec.stdin.decode()
```

- [ ] **Step 2: テストが失敗することを確認する**

Run: `uv run --locked pytest tools/agent_runner/tests/adapters/claude_code/test_adapter.py::test_prepare_caps_bash_timeout_by_request_deadline -q`（cwd は feature worktree の root）
Expected: FAIL（`KeyError: 'BASH_MAX_TIMEOUT_MS'`）。

- [ ] **Step 3: prepare を実装する**

`tools/agent_runner/adapters/claude_code.py` のモジュール定数（`_FENCE` の後）に追加:

```python
_DEFAULT_BASH_TIMEOUT_MS = 600_000
_BASH_TIMEOUT_MARGIN_SECONDS = 120.0
```

`prepare` の `lines = [context.request.prompt]` から `return` までを次に置き換える（argv の構築は変更しない）:

```python
        lines = [context.request.prompt]
        lines.extend(prompt_lines(context.work_dir, agent.skill_sources, context.role.skills))
        if context.role.result_shape == "json":
            lines.append("Return your final answer as a JSON object.")
        # Keep this noninteractive child's work in the foreground so it finishes
        # before the result. Bash keeps its 10-minute default; a long verification
        # may request up to the role's remaining time minus a reserve for the
        # final result. The runner's outer deadline still applies.
        cap_ms = max(
            _DEFAULT_BASH_TIMEOUT_MS,
            int((context.request.deadline_seconds - _BASH_TIMEOUT_MARGIN_SECONDS) * 1000),
        )
        lines.append(
            "Bash commands time out after 10 minutes by default. For a command "
            f"expected to take longer, pass an explicit timeout of up to {cap_ms} ms."
        )
        env = {
            "CLAUDE_CODE_DISABLE_BACKGROUND_TASKS": "1",
            "BASH_DEFAULT_TIMEOUT_MS": str(_DEFAULT_BASH_TIMEOUT_MS),
            "BASH_MAX_TIMEOUT_MS": str(cap_ms),
        }
        return LaunchSpec(argv=tuple(argv), stdin="\n\n".join(lines).encode("utf-8"), env=env)
```

- [ ] **Step 4: 対象テストが通ることを確認する**

Run: `uv run --locked pytest tools/agent_runner/tests -q`
Expected: PASS（295 passed。ベースライン 289 + 新パラメータ 6）。

- [ ] **Step 5: コミットする**

```bash
git add tools/agent_runner/adapters/claude_code.py tools/agent_runner/tests/adapters/claude_code/test_adapter.py
git commit -m "fix: derive claude-code bash max timeout from role remaining time (#382)

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

## controller の検証と統合確認（Task 1 の取り込み後）

実装担当の依頼には含めない。controller が feature worktree で実行する:

1. 対象テストの再実行: `uv run --locked pytest tools/agent_runner/tests -q` → exit 0。
2. fake CLI 対照プローブ（実装後）: `bash "$SESSION/probes/run-contrast.sh" long after` と `short after`。期待: long は inspect role（cap 2580000）が success、short role（cap 600000 の下限）が response_failed。short は両 role success。fake の記録に `default_ms=600000`・`background_disabled="1"`、親環境の 999999999 が漏れていないこと。実装前の記録（`run-*-before`）と対照する。
3. native 計算プローブ: `uv run --no-project python "$SESSION/probes/probe_native_timeout.py"`（実装前に実行済み・合格。版が変わらなければ再実行不要）。
4. README の 3 入口（最終 HEAD で）:
   - `bash .devcontainer/run-tests.bash`
   - `bash scripts/check-layout.sh`
   - `uv run --locked pytest tests/skills .agents/skills .agents/scripts tools -q`（約 14 分。バックグラウンド実行と monitoring-long-tasks）
5. 差分のスコープ確認: `git diff <base>...HEAD --stat` が claude_code.py・test_adapter.py・Spec・Plan のみであること。`_classify`・collect に差分がないこと。
6. 要件・原因・検証の対応（convergence.md の「3. 検証と閉じ方」）で Spec の条件 1〜5 を実行証拠と照合する。統合担当は controller。
7. 検証の記録（`--merge` 用）: 検証した HEAD・`git status --porcelain` が空・各コマンドの argv と終了コード・ログの完全パス・base（`CODE_BASE_SHA`）を SESSION に記録し、`finalize.py` の `--checks-file` の形（review-fix-planning の references/execution.md の 3 章）のファイルを作る。

## 実行予算

- Issue 全体の能動時間: **420 分（7 時間）**。根拠: #363 の実績（約 46 分、ループ 1 サイクル・レビューなし）に、設計レビュー（実測 74 秒）+ Spec レビュー（期限 30 分）+ ループ最大 3 サイクル ×（レビュー 45 分 + 計画・修正 30 分）≈ 225 分を加えた目安。ledger: `$SESSION/budget.jsonl`（issue_budget.py）。
- phase の目安: Spec・レビュー 40 分 / Plan 15 分 / 実装 90 分（role 期限 5400 秒、依頼 1 回 + 再試行 2 回まで）/ controller 検証 30 分（全体 pytest 約 14 分を含む）/ PR 5 分 / ループ最大 225 分。
- worker の期限（runner が強制）: implement 5400 秒、spec-review / design-review 1800 秒、inspect / self-review 2700 秒、fix-check 1800 秒（呼び出し側短縮）。controller の検証コマンドは task_watch の宣言対象にしない（monitoring-long-tasks の対象外）。
- 再試行の上限: implement の依頼は Task ごとに合計 3 回（初回 + retry/rejected 2 回）まで。同じ失敗の再試行は 1 回まで（budget ledger の既定）。`failed`（停止未確認・期限切れ・認証待ち・fallback 尽き）は即停止。レビューの失敗（state: failed / status: incomplete）は成功扱いせず停止。ループは 3 サイクルまで。
- checkpoint: Spec レビュー採否後 / Task 1 取り込み後 / 全体検証後 / 各ループサイクル後 / 予算 50%・100%。`budget show` で数えて判断を 1 行記録する。
- 縮小・切り出し・方法変更の候補: 予算不足時はループを上限サイクルで打ち切り `fixes_pushed` として報告（続きは `/pr-review-fix-loop`）。piaq が prose 前置で `response_failed` を繰り返す場合は、担当変更を勝手にせず停止して利用者に選択肢を報告（メモリの既知事象）。プローブはこれ以上縮小しない（受け入れ条件 4 の最小構成）。

## contingency（代替策）

- 最初の RED で API の前提が異なると判明した場合（例: Request が不変で `deadline_seconds` を代入できない）: 仕様の意味を保つ最小修正（テストで `model_copy(update=...)` を使う等）を ledger に残して継続する。上限導出の意味（残り時間 − 120 秒、下限 600000）が変わる場合は利用者の裁定を待つ。
- native プローブの marker が導入済み CLI で見つからない・計算が公式と違う場合: 版を記録して停止する（値を黙って置き換えない）。関数の再特定は読み取りだけで行い、計算の意味が変わるなら設計の再検討が必要。
- fake CLI プローブで runner が起動しない（nested_invocation・checkout_audit 等）: 原因を ledger に記録し、監査対象の登録は自分で prune せず停止報告する。
- base（origin/main）が前進した場合: 停止せず、旧 base JSON を保全して新 SHA を捕捉し、merge で取り込んで再検証・再 scan して続行する（Spec D8。rebase・force push はしない）。競合が所有や仕様の意味を変える場合は停止。
- gitleaks の検出: AGENTS.md の 3 条件を満たす場合だけ該当 commit を直して再検査。満たさなければ停止。

## 完了の条件

- Task 1 が取り込まれ、Task レビューと最終全体レビューが clean（または裁定付き parked）。
- controller の検証 1〜7 がすべて exit 0 / 照合済み。検証記録と checks-file が SESSION にある。
- PR が作成され（`Closes #382`）、`--merge` のループが `no_fix_needed` で finalize のマージまで完了する。マージ後の Issue state を観測して報告する。
- ループが上限・停止で終わった場合は、その区分（`fixes_pushed` / `stopped`）と再開方法を報告する。