# Issue #396 monitoring 期限超過テストのハンドシェイク化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `test_undeclared_stop_never_signals` の固定秒数依存を解消し、観測遅延で誤失敗しない決定的テストにする。

**Architecture:** fake worker の `undeclared` モードを、watcher が `hold/deadline` を `events.jsonl` に記録するまで終了しないハンドシェイクに変更する。`task_watch.py` とテスト本体の assertion は変更しない。

**Tech Stack:** Python 3（uv 管理）・pytest・Linux /proc

**Spec:** `docs/superpowers/specs/2026-11-12-issue-396-monitoring-deadline-test-design.md`

## Global Constraints

- 変更してよいファイルは `.agents/skills/monitoring-long-tasks/tests/fake_worker.py` のみ（Task 1）。`task_watch.py`・`SKILL.md`・`test_task_watch_core.py`・`test_task_watch_process.py` は編集禁止
- 新しいコミット対象テストは追加しない（テスト採用基準: 既存テストが S、fake worker の失敗は L で可視化）
- Python は uv 経由（`uv run`）。python3 コマンドは使わない
- 日本語表現規約（AGENTS.md）: 「正本」「着地」「契約」「原子的」等の直訳語を使わない
- 検証はローカル実行。CI（GitHub Actions）は無効・確認不要
- コミットしないファイルは worktree 内に作らない（セッションディレクトリ `tmp/agents/issue-396.z5hf2du1/` を使う）
- 削除コマンドのシェル変数は `${VAR:?}` ガード付き・パス全体を引用
- 実装サブエージェントはテスト・静的チェック・回帰を同期実行し、完了を待ってからターンを終える

## 受け入れ基準

### 動作環境

- Ubuntu 26.04 LTS Dev Container（WSL2 上）。Linux /proc が使えること（task_watch の前提）
- uv とプロジェクトの pytest 環境（`uv run pytest` が worktree のルートで動く）
- 実行 cwd は feature worktree `/workspaces/reso-world/.worktrees/issue-396-flaky-deadline-test`

### 実入力

- watcher CLI: `uv run python .agents/skills/monitoring-long-tasks/scripts/task_watch.py run --state-dir <state> --poll-seconds 0.05 --progress-file <progress.jsonl> --deadline-seconds 0.3 --stop none -- <python> .agents/skills/monitoring-long-tasks/tests/fake_worker.py undeclared <progress.jsonl> <result.json> <state>`
- fake worker の argv: `fake_worker.py undeclared PROGRESS RESULT STATE_DIR`（STATE_DIR は argv[4]）
- `events.jsonl` の行（watcher が追記）: `{"at": "2026-11-12T00:00:00.000000Z", "elapsed_seconds": 0.31, "decision": "hold", "reason": "deadline"}`。書きかけの末尾行（JSON でない）が混在し得る
- 進捗ファイルの項目は非 ASCII（他モードの `確認した挙動 N`）。undeclared モードは進捗を書かない

### 防御範囲

- 対象条件: `--stop none` で deadline 超過かつ worker 生存 → `hold/deadline` が記録され、シグナルは送られない（`got-term` なし）。worker は記録後に正常終了 → `completed`・`deadline_exceeded=true`・`stop=null`
- 対象外の反例（既存仕様を変更しない）:
  - worker が期限前に終了 → `completed`（hold なし）。`decide()` の終了優先は単体テスト `test_exit_is_completed_only_with_zero_and_declared_result` がカバー
  - `--stop TERM/INT` の停止・エスカレーション → 既存テスト（`test_escalate_kill_confirms_stop_of_term_ignoring_worker` 等）がカバー
  - 終了後の安全の失敗 → `exited_incomplete/safety`（`test_records_written_by_the_group_after_exit_reach_the_final`）
  - 終了後の group 残存 → `hold/residual_processes`（`test_processes_left_in_the_group_after_exit_are_held`）
- `task_watch.py` の回収（`_wait_group_empty`）・停止確認（`_wait_stopped`）・識別（Identity）は変更しない

## 要件・原因・検証の対応（実装前の照合）

| Spec の条件 | 担当 Task | 観測する結果 | 検証方法 |
| --- | --- | --- | --- |
| 1. 固定秒数に依存しない「期限後も生存」の確認 | Task 1（ハンドシェイク）+ Task 2（統合確認） | worker は hold/deadline 記録前に終了しない。RED/GREEN ハーネスの summary | Task 2: RED（旧コードで hold なし completed、controller が再現済み）→ GREEN（新コードで hold あり completed）。単体 30 回反復 |
| 2. 終了優先仕様との整合・守りを弱めない | Task 1（task_watch.py 無変更）+ Task 2 | `git diff` で task_watch.py・テスト本体の変更が無い。既存 25 テスト成功 | Task 1: monitoring スイート。Task 2: 全体スイート + diff 確認 |
| 3. 単独・並行での安定性 | Task 2 | 30 回反復全件成功・並行負荷下の全体スイート成功 | Task 2: 反復実行 + `run-tests.bash` との並行実行 |
| 4. #345 との分離・結果の参照可能性 | Task 2（記録）+ PR | PR 本文・Issue コメントに検証結果 | PR 作成時に確認 |

共有条件: worker と watcher の同期は `events.jsonl`（追記専用・完全行のみ解析）と `state` ディレクトリ（argv[4]）。統合担当（Task 2・controller）が条件単位で確認する。

## Review Focus

1. **events.jsonl の書きかけ末尾行**: watcher 追記中の部分行を読んでも worker が例外終了しない（JSON 解析失敗・object でない行は読み飛ばし）。既存テストの失敗で可視化（L）
2. **watcher が hold/deadline を記録しない不具合**: worker が無限待機しない（`signal.alarm(60)` で終了 → テスト失敗で可視化、L）
3. **待機中の SIGTERM（守りの破れ）**: ハンドラーは待機前に取り付け、`got-term` が書かれる → 既存 assertion が失敗（S の守り）
4. **worker が観測前に終了する競合**: ハンドシェイクで構造的に排除。GREEN ハーネスと 30 回反復で確認
5. **他モードへの回帰**: `heartbeat`・`ignore-term`・`finalize-late` 等は変更しない → monitoring スイート全体で確認

（AGENTS.md のテスト採用基準により、これらを確かめる新しいコミット対象テストは追加しない。既存テスト・一時ハーネス・alarm による可視化で代える）

## 実行予算

- **Issue 全体の能動時間: 360 分**。根拠: 準備・Spec 〜40 分 + Spec レビュー 〜30 分 + Plan 〜15 分 + Task 1 実装 〜60 分 + 統合検証 〜25 分 + PR 〜10 分 + ループ ≤ 3 サイクル ×（レビュー 45 分 + 計画・修正 15 分）= 180 分 + 予備
- phase 目安: 準備・Spec 40 / Spec レビュー 30 / Plan 15 / 実装 60 / 検証 25 / PR 10 / ループ 180
- worker の期限（agent-runner の役割設定）: implement 5400 秒（90 分）・spec-review 1800 秒（30 分）・inspect 2700 秒（45 分）。controller は monitoring-long-tasks に従い完了通知で待つ
- 再試行の上限: 同じ失敗（reliability）は 1 回まで。`pi_alibaba_qwen4-max_max` の `response_failed` は事前委任（Spec D8）により `pi_opencode-go_deepseek4-flash_max` へ担当変更（方法変更であり同じ手段の再試行ではない）。変更後も失敗したら停止
- checkpoint: phase の境界・予算 50%（180 分）・100%（360 分）・worker 失敗直後。ledger は `tmp/agents/issue-396.z5hf2du1/budget.jsonl`
- 縮小・切り出し・方法変更の候補: 反復回数の短縮（30 → 10、Spec の決定記録に変更を明記）・ループがサイクル上限で終わったら `/pr-review-fix-loop` で継続（切り出し）・base 移動時は rebase して検証やり直し（Spec D7）

## contingency（代替策）

- 最初の RED で実出力・API の前提が異なると判明した場合: 仕様の意味を保つ最小修正を ledger に残して継続。意味が変わる場合は利用者の裁定を待つ
- ハンドシェイクがデッドロックする場合（worker が event を読めない等）: `finalize-late` モードと同じ state 読み取りパターンに合わせる最小修正。`events.jsonl` の形式が変わる場合は Spec の意味が変わるので停止
- runner が `response_failed` / 起動失敗: 事前委任の担当変更（Spec D8）。それでも失敗したら停止
- 全体スイートの無関係な失敗: 原因を調査し、本変更と無関係なら証拠を記録して判断。解消できなければ停止
- base 移動: Spec D7 の追随手順。rebase 競合が解消できなければ停止

## Task 1: fake worker のハンドシェイク化

**Files:**
- Modify: `.agents/skills/monitoring-long-tasks/tests/fake_worker.py`（`undeclared` モード、52-59 行付近）

**Interfaces:**
- Consumes: watcher が書く `state/events.jsonl`（追記専用 JSONL。`decision`・`reason` キー）。`state` は argv[4]
- Produces: `undeclared` モードの終了タイミング（hold/deadline 記録後）。他モードの挙動は不変

**テストの要否:** 新規コミット対象テストは不要。既存の `test_undeclared_stop_never_signals` が S の守り（停止未宣言の対象へシグナルを送らない）を端到端で確かめ、ハンドシェイク自体の失敗はテスト失敗・alarm で可視化される（L）。代わりの検証: monitoring スイート実行 + Task 2 の RED/GREEN ハーネス

- [ ] **Step 1: 現状の誤失敗の再現を確認する（RED は controller が実行済み）**

controller が `repro_deadline_delay.py`（red モード）で旧コードの誤失敗を再現済み（セッションの `repro-old-2.log`: hold/deadline なし completed）。実装担当はこの記録を参照し、再現ハーネス自体は変更しない

- [ ] **Step 2: `undeclared` モードをハンドシェイクに変更する**

`fake_worker.py` の `case "undeclared":` を次のとおり変更する（`signal.alarm(60)` は main の冒頭のまま。SIGTERM ハンドラーの取り付けもまま）:

```python
case "undeclared":

    def record_term(_signum: int, _frame: FrameType | None) -> None:
        (state.parent / "got-term").write_text("term\n", encoding="utf-8")

    signal.signal(signal.SIGTERM, record_term)
    # watcher が hold/deadline を記録するまで終了しない。固定秒数のスケジューリングに
    # 依存せず「期限後も生存」を保証する（#396）。書きかけの末尾行は読み飛ばす。
    events = state / "events.jsonl"
    while True:
        if events.exists():
            for line in events.read_text(encoding="utf-8").splitlines():
                try:
                    event = json.loads(line)
                except ValueError:
                    continue
                if isinstance(event, dict) and event.get("decision") == "hold" and event.get("reason") == "deadline":
                    return 0
        time.sleep(INTERVAL)
```

- [ ] **Step 3: monitoring スイートを実行する**

Run: `env -u CODEX_THREAD_ID uv run pytest .agents/skills/monitoring-long-tasks -q -p no:cacheprovider`
Expected: 25 passed

- [ ] **Step 4: 変更範囲を確認する**

Run: `git show --name-only HEAD`（コミット後）
Expected: `fake_worker.py` のみ。`task_watch.py`・テスト本体・SKILL.md の変更が無い

- [ ] **Step 5: Commit**

```bash
git add .agents/skills/monitoring-long-tasks/tests/fake_worker.py
git commit -m "fix: wait for hold/deadline event in undeclared fake worker (#396)"
```

## Task 2: 統合確認（controller が実行）

**Files:**
- 変更なし（検証のみ）。ログはセッションディレクトリに保存

**テストの要否:** 新規テスト不要。Spec の条件 1〜4 を実行証拠で確認する

- [ ] **Step 1: GREEN ハーネス**

Run: `uv run python "$SESSION/repro_deadline_delay.py" "$CODE_ROOT" "$SESSION/repro-green" green`
Expected: `hold_deadline_event=true`・`decision=completed`・`deadline_exceeded=true`・`stop=null`・`got_term_exists=false`

- [ ] **Step 2: 単体テスト 30 回反復**

Run: `for i in $(seq 1 30); do env -u CODEX_THREAD_ID uv run pytest .agents/skills/monitoring-long-tasks/tests/test_task_watch_process.py::test_undeclared_stop_never_signals -q -p no:cacheprovider || break; done`
Expected: 30 回全件 passed

- [ ] **Step 3: 並行負荷下の全体スイート**

Run: `bash .devcontainer/run-tests.bash`（バックグラウンド）と同時並行で `env -u CODEX_THREAD_ID uv run pytest tests/skills .agents/skills .agents/scripts tools -q -p no:cacheprovider`
Expected: 両方成功（全体スイートは 1442 passed 前後）

- [ ] **Step 4: レイアウト検査**

Run: `bash scripts/check-layout.sh`
Expected: 終了コード 0

- [ ] **Step 5: 検証の記録**

HEAD・`git status --porcelain`（空）・各コマンドの argv と終了コード・ログの完全パスをセッションディレクトリに記録。`finalize.py --checks-file` 形式（`{"head", "base", "commands"}`）のファイルを作る。base は `CODE_BASE_SHA`（移動時は再捕捉した SHA）

## 実行方式

runner 担当による SDD（`implement_task.py check` の `self=false`）。Task 1 を `pi_alibaba_qwen4-max_max` に依頼（事前委任: 同様の失敗で `pi_opencode-go_deepseek4-flash_max` に変更、Spec D8）。Task 2 は controller（統合担当）が同期実行。Task 1 のレビューは controller が別 context に依頼（brief・report・diff・受け入れ基準を渡す）。最後の全体レビューは別 context で実行

## 完了

- 全 Task 完了・全体レビュー clean・検証記録揃ったら PR 作成（`Closes #396`）。`--merge` のループへ
- PR 本文: 変更概要・Spec の決定と理由・実行方式・検証結果・作業時間・割り当てと runner の観測情報・レビュー記録の SESSION パス
- マージ後: Issue #396 の state を観測して報告。#345 から参照できるよう検証結果を Issue コメントに残す