# Issue #363 Claude foreground Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Claude Code の非対話担当だけで Bash の背景化を無効化し、既定timeoutを10分にする。
**Architecture:** prepare の LaunchSpec.env に2値を追加する。既存の回答分類・runnerの期限は維持する。
**Tech Stack:** Python / uv / agent-runner / Claude Code CLI。
**Spec:** `docs/superpowers/specs/2026-11-10-issue-363-claude-foreground-design.md`
**状態:** draft。issue-to-pr と利用者の明示入力による実行許可であり、内容の承認ではない。
**実行方式:** SDD。Task 1 を implement_task.py 経由で指定担当へ直列依頼。統合・公開はcontroller。

## Global Constraints
- コード変更は `tools/agent_runner/adapters/claude_code.py` の prepare が返す LaunchSpec.env のみ。
- `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS="1"` と `BASH_DEFAULT_TIMEOUT_MS="600000"` を固定で設定する。
- _classify、toml、runtime文書、対話設定、他adapter、既存テストを変更しない。恒久テストを追加しない。
- 有料の再現実験は0回。指定workflowの担当起動だけ許可する。

## 受け入れ基準
- 動作環境: Dev Container の uv / Python、非対話 agent-runner の claude-code adapter。
- 実入力: json/text の役割と日本語・改行を含む prompt（例「確認する\n結果を返す」）。prepare が返す env に `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS="1"` と `BASH_DEFAULT_TIMEOUT_MS="600000"` を設定する。argv と stdin の既存仕様は保つ。
- 防御範囲: runner の当該 CLI 子プロセスだけへ適用する。親環境や対話設定は書き換えない。成功 result の後の通知・非 JSON result を成功扱いにせず、_classify の拒否を維持する。

## Review Focus
L/F のため新規の恒久テストを作らず、一時プローブと既存回帰に割り当てる。
1. json/text役割のenv（Task 1 の一時プローブ）。
2. 日本語・複数行stdinとargv維持（Task 1）。
3. 600秒 <= 有効設定の最短役割期限（controller統合）。
4. 親環境不変・CLI子へのenv適用（Task 1プローブ、既存runner実装の確認）。
5. 最後より前の有効回答への巻き戻りをしない（既存adapter回帰とcontrollerプローブ）。

## Task 1: prepare の非対話 env を設定
**Files:** Modify `tools/agent_runner/adapters/claude_code.py` の `ClaudeCode.prepare(self, context: AdapterContext) -> LaunchSpec`。
**Interfaces:** Consumes AdapterContext、Produces 既存LaunchSpec（argv/stdin不変、envに2値）。
**テスト要否:** 不要（L: 設定欠落は response_failed で見える）。一時プローブと既存adapter回帰で代替。
- [ ] 実装前に現在のprepare envを一時スクリプトで観測し、2値が無いことを記録する。
- [ ] LaunchSpec.envに固定2値を入れ、理由を短いコメントで説明する。
- [ ] 一時プローブでjson/text・日本語/改行stdin・親環境不変を確認する。スクラッチはcontroller指定セッション配下のみ。
- [ ] `uv run --locked pytest tools/agent_runner/tests/adapters -q`、`git diff --check` を同期実行する。
- [ ] 明示ファイルのみcommit: `fix(agent-runner): keep Claude Code Bash commands in foreground`。
- [ ] 所要時間、commit、実行コマンド/結果、懸念を返す。サブエージェント・push・Issue更新は行わない。

## controller の統合・公開
テスト追加なし（L/F の検査と既存回帰）。以下を条件単位で照合する。
- [ ] Taskレビュー（同じbrief・受け入れ基準を読み取り専用レビューへ渡す）。
- [ ] 一時プローブで固定env、最短役割期限、json/text、単一result成功・後続通知result拒否を確認する。
- [ ] 全ブランチレビューを新しいsp-reviewへ依頼する。
- [ ] 最後のcommit後のclean HEADでREADMEの `bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`uv run --locked pytest tests/skills .agents/skills .agents/scripts tools -q` とプローブを実行し、argv・終了コード・ログ・HEAD・baseを保存する。
- [ ] base/Issue/競合を再照合し、scanしたSHAをpush。main前進時はSpec D7どおり履歴と証拠を残してmerge・再検証する。
- [ ] `Closes #363` のPRをmain向けに作る。指定されたレビュー修正ループを実行し、マージはfinalize.pyだけに任せる。

## 要件照合
固定env/非対話限定→Task1/prepareと親環境プローブ。timeout→Task1の値+統合の有効設定読取。分類不変→差分確認+既存回帰+通知対照。編集境界→Taskレビュー/全体レビュー/最終diff。
共有前提はrunnerがspec.envを子の環境へ最後に適用する順序（runner.py/process.py）と有効設定の期限。controllerが統合時に確認し、Task単体成功で代えない。

## 実行予算
能動時間300分（準備/計画20、実装/レビュー25、統合検査35、公開10、ループ3×70分）。
ledger: `/workspaces/reso-world/tmp/agents/issue-363.1jibklo0/budget.jsonl`。
実装role期限90分、レビュー45分（runnerが管理）。同期呼び出しで待ち、追加watchは起動しない。
同じ信頼性失敗の再試行1回、実装依頼最大2回。failedは停止しselfへ切り替えない。安全失敗は0再試行。
checkpointは準備/実装/検証/公開/ループ各境界と50%・100%。100%到達は停止する。
成果が増えない場合は有料実験を足さず、一時プローブ/既存回帰へ絞る。実装境界は拡げない。
SDD領域は同じセッションの `sdd/2026-11-10-issue-363-claude-foreground/`。

## contingency（代替策）
- 最初のREDでAPI前提が異なる場合は意味を保つ最小修正をledgerへ記録する。
- 既存検査が環境由来で失敗したら原因を切り分け、未実行/失敗を成功にしない。解消不可なら停止。
- main前進のみでは停止しないという追加指示を適用。旧捕捉SHAと差分を保存し、所有ファイルの衝突を確認。非破壊mergeと必要検証後に、新しいbase記録を別名で作る。helperの失敗を無視・捏造せず、finalizeのbase/merge親/CI guardは維持する。
