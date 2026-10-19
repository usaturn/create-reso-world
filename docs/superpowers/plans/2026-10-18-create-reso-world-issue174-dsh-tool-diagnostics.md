# DSH Tool Diagnostics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 回復済みツールエラーの 401/403 で完成した DSH 回答を捨てず、不必要な fallback を起動しない。

**Architecture:** `tool_result` は任意のツール本文なので API 認証判定に使わず、既存の承認診断だけを維持する。top-level error、turn_end、stderr と runner の終了・identity 検証は変更しない。

**Tech Stack:** Python 3.14、uv、pytest、既存の DSH 偽 CLI/session v4 fixture。

**Spec:** `docs/superpowers/specs/2026-10-18-create-reso-world-issue174-dsh-tool-diagnostics-design.md`

## 管理・実行許可

- 状態: draft。文書・対象リポジトリ: usaturn/create-reso-world。
- Issue: https://github.com/usaturn/create-reso-world/issues/174
- 基準 HEAD: `1335f410e624355cd558029bdcdad65eaa944ed8`。
- 利用者の明示した issue-to-pr #174 により、通常判断・検証・commit・push・PR 作成を実行する。内容承認・マージ許可ではない。
- 実行方式: inline（executing-plans）。1 つの挙動修正で同じ test fixture と adapter を順に編集するため。調査と最終レビューは同期ロールに委譲する。
- ログと ledger は親の `/workspaces/reso-world/tmp/agents/issue-174.znhd_slh/` に置く。worktree 内に scratch を作る upstream helper は使わず、同じ task-start/done と review-package の情報をこのディレクトリで記録する（AGENTS.md 優先）。

## Global Constraints

- 実モデル・課金 API を一切使用しない。
- ツール結果では既存の承認拒否を成功にしない。
- 真の API 認証失敗・非ゼロ終了・identity 欠落や不一致を成功にしない。
- runner 全体、他 adapter、sandbox、DSH 版、認証設定、rebuild、O-M1/G-M1 の診断ラベル問題は対象外。
- 新しい文書テスト・固定文言照合テストは作らない。
- 公開前に親 checkout の scan-before-push を使う。main を base に PR を作り、マージしない。

## Review Focus

1. 行数 401/403 とファイル名 401/403 を各々単独で含む read エラー（Task 1 の collector と実プロセステスト）。
2. 認証風の文字列を含む一般ツール本文は API 診断にしない（Task 1 の collector テスト）。
3. 承認拒否と数値 403 の混在では awaiting_approval（Task 1 の既存承認テスト拡張）。
4. 真の top-level 認証エラーが completed/final より優先する（Task 1 の認証回帰）。
5. fallback の有無が primary の成功を変えず、fallback を余分に起動しない（Task 1 の実プロセステスト）。

## 実行予算

- 全体 60 分（準備・Spec/Plan 15、TDD 実装 15、環境回帰・レビュー 20、公開 10）。ledger は上記の `budget.jsonl`。
- 同期 recon/builder check/最終レビューは各 5 分を目安に成果を要求し、停止手段のないロールを期限で強制終了しない。予約枠は末尾 1 分、途中監視不可のため再試行はしない。
- 検証と実装は foreground で終了まで待ち、timeout による打ち切りはしない。実モデル評価の予算は 0 回。
- 信頼性の同じ失敗は再試行 1 回まで。安全の失敗・権限拒否・秘密検査失敗は停止する。
- checkpoint は準備後、Task 完了時、検証・レビュー後、50%・100%、worker の失敗後。100% で停止して報告する。
- contingency: fixture が複雑化したら既存 stream/session helper に戻す。広い認証正規表現や runner 全体の再設計へ拡大せず、範囲外候補として記録する。必要ツール失敗や解消できない検証失敗では公開せず停止する。

### Task 1: ツール認証診断を分離し、batch/fallback まで回帰を守る

**Files:**
- Modify: `tools/agent_runner/adapters/dsh.py:_classify`
- Test/Modify: `tools/agent_runner/tests/adapters/dsh/test_adapter.py`
- Test/Modify: `tools/agent_runner/tests/adapters/dsh/fake_cli.py`
- Test/Modify: `tools/agent_runner/tests/adapters/dsh/test_runner.py`

**Interfaces:**
- Consumes: `_classify(events: list[dict[str, object]], shape: str) -> tuple[ReceiptStatus, Payload]`、既存 `_stream` / `_collect`、`run_workflow`、`Config` / `Assignment`。
- Produces: 同じインターフェース。回復済み read エラーでも成功・payload を保持し、fallback が設定済みでも primary の 1 試行だけとなる。

**テストの要否:** 必要。認証判定の分岐と、実際の subprocess が返す回答・fallback の発生を確認する。文書は diff と参照先の検査で代える。

- [x] **Step 1: task-start を記録し、回帰テストと偽 CLI mode を追加する**
  - collector に 402 行、401 行、403 行、`401.py`/`403.py`、認証風文字列のツールエラーを挿入し、`status == "success"` と `payload == {"ok": True}` を確認する。
  - 既存承認テストへ 403 を含む拒否を追加し、`awaiting_approval` を確認する。
  - top-level error の `UNAUTHORIZED`/401/403 が completed/final 後も `awaiting_authentication`、payload None となることを確認する。
  - 偽 CLI に上記 5 つの read エラー用 mode を追加し、tool_call/result → completed/final と有効な session を出す。
  - 実プロセステストは 5 mode × fallback 有無。batch/role/primary が success、primary payload の ok が true、exit 0、stop_confirmed、観測 provider/model が一致、attempts は agent a の 1 件だけとする。fallback は別 id の既存偽 CLI success agent を明示登録する。
- [x] **Step 2: RED を確認する**
  - Run: `uv run --locked pytest tools/agent_runner/tests/adapters/dsh/test_adapter.py tools/agent_runner/tests/adapters/dsh/test_runner.py -q`
  - Expected: 402 行の対照・真の認証診断は成功。401/403 の回帰は誤った認証待ちや batch failed、不要な fallback で失敗する。
- [x] **Step 3: 最小修正を入れる**
  - `_classify` の tool_result 分岐で `_diagnostic` を呼ばず、`_APPROVAL.search(result)` に一致した場合のみ `("awaiting_approval", None)` を返す。本文が API の認証状態を表さない理由をコメントに書く。
- [x] **Step 4: GREEN を確認する**
  - Run: `uv run --locked pytest tools/agent_runner/tests/adapters/dsh -q`
  - Expected: 新規ケースと既存の真の認証・承認・非ゼロ終了・identity 検証を含め全件成功、終了コード 0。
- [x] **Step 5: 検証して commit、task-done を記録する**
  - Run: `git diff --check`、明示した 4 パスのみ stage し、`fix(agent-runner): keep recovered DSH tool errors out of API auth checks` で commit。
  - Expected: 終了コード 0。記録に BASE/HEAD、RED/GREEN の結果とログ、所要時間を残す。

## 最終検証・公開

- [x] README の入口（ワールド以外）を同期実行: `bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`uv run --locked pytest tests/skills .agents/skills .agents/scripts tools`。終了コード・実ログを確認。
- [x] branch 全体を fresh の sp-review に読み取り専用で依頼。Spec/Plan、基準 SHA、HEAD、Review Focus、ledger を渡す。重要な指摘は 1 回の RED→GREEN 修正で対応し、回帰を再実行する。
- [x] Issue の open 状態・コメント・競合 PR/claim/branch を再確認する。自分の worktree と他者のものを区別する。
- [x] Plan の完了記録を更新（状態 draft のまま）して commit。親の秘密検査が成功した SHA のみを push し、明示 head/base main で PR を作成する。
- [x] PR に Closes #174、決定理由、実行方式、検証・所要時間を記載。private の停止済み CI は対象外。ログの要点を文書/PR に転記後 ledger を end にしてセッション scratch を回収する。worktree/branch は PR のため残す。

## 実行記録

- 基準の DSH テスト: 124 passed（終了コード 0）。
- RED: 最初の実行で fallback の同一 model が設定検証に拒否されたため、偽 fallback に独立した model を指定した。再実行で 15 failed / 109 passed（終了コード 1）。行数・ファイル名による payload 破棄と不要な fallback を確認した。
- GREEN: DSH 全体 147 passed（終了コード 0）。実装修正 commit: `4a41d95`。
- README の検証: Dev Container/スクリプト 33 passed、check-layout PASS、全 Python 回帰 2591 passed / 1 skipped（598.10 秒）。すべて終了コード 0。
- ブランチ全体の独立レビュー（`1335f41..f82cae6`）: Critical / Important / Minor ともに 0。実モデル未検証のみ評価対象外。指示に従うため追加の実 API 検証はしない（想定と実 CLI の差は未検証の制約として報告）。
- 公開直前の再確認: Issue OPEN、コメント・依存・同 Issue の PR/claim に競合なし。PR #170 は main に MERGED。自分の worktree/branch のみ使用する。
- 実行方式の scratch 配置は AGENTS.md に従った。設計上の変更・持ち越す軽微指摘はない。実モデル使用は 0 回。
- 時間: 2026-10-18 21:34 UTC 着手。準備・設計・Plan 約 6 分、実装・TDD 約 3 分、全体回帰・結果記録 約 17 分、独立レビュー・公開準備 約 2 分。予算 ledger の記録開始は 21:37 UTC（準備途中）で、公開準備時点の記録対象能動時間は約 25 分、60 分の予算内。安全の失敗 0、fixture の信頼性失敗 1 回（修正後解消）。
- 文書は承認されていないため状態 draft のまま。実装・検証・レビュー・PR 作成は完了。
- 公開先: https://github.com/usaturn/create-reso-world/pull/180 （OPEN、base main、Closes #174 を確認）。マージは未実施。
- 公開前の Gitleaks: 5 commits を検査し検出なし。検査した `d387fe6210af7ac493df16518fe68c9b229190a9` をそのまま push した。本完了記録も同じ検査経路で公開する。
- budget 終了時の記録対象能動時間は 1608.81 秒（約 26 分 49 秒）、安全の失敗 0、再試行上限到達なし。開始前の準備約 3 分を含め、全体所要時間は約 30 分。worker の強制停止は 0 回、監視 watcher の作成も 0 回。
- `/workspaces/reso-world/tmp/agents/issue-174.znhd_slh/` のログと ledger は、結果を本 Plan と PR に転記し、同期処理の終了と watcher 不在を確認して回収済み。残した scratch/log はない。
- worktree `/workspaces/reso-world/.worktrees/issue-174-dsh-tool-diagnostics` と branch `fix/issue-174-dsh-tool-diagnostics` は PR の作業用に保持する。
