# Issue #243 DSH 撤去 Implementation Plan

> **For agentic workers:** `superpowers:subagent-driven-development` または `superpowers:executing-plans` で Task ごとに進める。利用者の追加指示により TDD は行わず、廃止確認テストを追加しない。

- 文書管理: `usaturn/create-reso-world`
- 対象: `usaturn/create-reso-world#243`
- 着手時のコード: `7cf60715caf0026f7a4c95c72cdc2527e8075e2c`
- 状態: `draft`。利用者の実行指示は内容の承認ではない
- 実行許可: 「`$issue-to-pr https://github.com/usaturn/create-reso-world/issues/243 --merge`」および「廃止したことについて、テストを書かないこと。TDD で実装しないこと。」

**Goal:** DSH の担当と専用経路を撤去し、残るランタイムの監査・レビュー・設定を維持して PR とレビュー修正ループまで進める。

**Architecture:** agent_runner は全登録 checkout を監査し、旧 DSH 設定を読み込み時点で明示エラーにする。PR レビューは通常の checkout 経路だけに整理し、修正ループと Dev Container から専用分岐を削除する。

**Tech Stack:** Python 3.14 / Pydantic / uv、Bash、TOML、GitHub CLI。

**Spec:** `docs/superpowers/specs/2026-10-23-create-reso-world-issue243-remove-dsh-design.md`

## 全体条件

- 過去の Spec・Plan、個人設定、資格情報、他の adapter の挙動を変更しない。
- 新規の廃止確認テスト、固定文言テスト、TDD 工程を設けない。削除対象の専用テストはコードと一緒に削除する。
- 共通の監査・停止確認・レビュー保存と Codex の拒否規則は弱めない。
- `README.md` の「テスト」の追跡対象向け 3 コマンドを最終 HEAD で実行する。Python コマンドは `uv` で起動する。
- `--merge` は利用者の指定。ループの上限 3 と各担当は設定の既定で、利用者が指定した値とは記録しない。

## Review Focus

1. 個人設定の旧 `runtime = "dsh"` を、秘密の値を出さずに担当の起動前で拒否できるか。正常設定との対照を一時設定で実行する。
2. 消失した無関係の worktree 登録も、runner と各入口で監査の対象になるか。残る安全性テストと実 CLI の対象ケースで確認する。
3. PR レビューの通常経路で HEAD・モデル識別・保存ロック・cleanup が保たれるか。既存の該当テストと実ループで確認する。
4. `after_run` の `attach-runner` は残り、旧 `finalize-parent` だけが外れるか。設定を読み込み、hook と文書を検査する。
5. 現行文書の DSH 参照が残っていないか、履歴・移行案内との区別を `git grep -il dsh` と差分の精読で確認する。

上記は利用者の指示により、新しい廃止確認テストにはしない。既存の安全性テストは、その守りを実装する箇所に 1 件以上残す。

## 実行方式

`implement_task.py check` は `self=true`、一次担当 `["self"]`、fallback なし。Task 1〜4 は担当ファイルを分けられるため、`superpowers:subagent-driven-development` で実装・レビューを行い、統合担当が Task 5 を実施する。各実装担当は担当ファイルだけを編集し、同じファイルを同時に編集しない。サブエージェントが使えない場合は `superpowers:executing-plans` で順に実施する。利用者の禁止に従い TDD の工程は省く。

## Task 1: agent_runner と全登録監査

**担当ファイル:** `tools/agent_runner/models.py`、`config.py`、`cli.py`、`adapters/__init__.py`、`adapters/dsh.py`、`dsh_identity.py`、`dsh_paths.py`、`dsh_review_evidence.py`、`dsh_sandbox.py`、`checkout_policy.py`、`workspace.py`、`runner.py`、`interfaces.rst`、`tools/test_support/dsh.py`、`tools/agent_runner/tests/adapters/dsh/`、関連する `tools/agent_runner/tests/test_*.py`、`.agents/skills/issue-to-pr/tests/test_implement_task_run.py`、`.agents/skills/review-verify/tests/test_dispatch.py`。

- [ ] DSH runtime と adapter・専用モジュールを削除し、個人設定の旧 runtime に専用の安全な設定エラーを返す。CLI でも撤去と必要な設定変更が分かる固定文面を出す。
- [ ] `confined_writes` と限定監査、DSH 専用の書き込み先・receipt 処理を削除する。`require_auditable_workflow` と runner は全登録を監査する。
- [ ] DSH 専用テストと fixture を削除し、共通の安全性テストは全登録監査の現行仕様に合わせて整理する。新規の廃止確認テストは書かない。
- [ ] `uv run pytest tools/agent_runner .agents/skills/issue-to-pr/tests .agents/skills/review-verify/tests`、`uvx ruff check`、一時設定で正常・旧 runtime の読み込みを確認する。

**テスト要否:** 新規テストは不要。廃止の有無を照合するテストは F または L であり利用者も禁止した。既存の安全性テストは全登録監査という S の守りを維持する。

## Task 2: pr-review の DSH 親入力と bundle

**担当ファイル:** `.agents/skills/pr-review/scripts/review_run.py`、`pr_review_parent.py`、`pr_review_workspace.py`、`.agents/skills/pr-review/tests/test_review_run.py`、`test_pr_review_workspace.py`、`test_port_routing.py`、`SKILL.md`、`references/evidence.md`、`references/noninteractive.md`。

- [ ] `prepare-parent`・`finalize-parent`、DSH session identity、staged 親保存の CLI と呼出しを削除する。
- [ ] 親入力 bundle と private clone の専用経路を削除する。浅い checkout は必要な履歴を所有する使い捨て領域へ直接取得し、元 checkout の shallow 境界・ref・FETCH_HEAD を保持する。通常 checkout の保存・cleanup も残す。
- [ ] DSH 専用テストを削除し、共有の HEAD・保存・cleanup テストを維持する。現行スキルの説明を更新する。
- [ ] `uv run pytest .agents/skills/pr-review/tests` と `uvx ruff check .agents/skills/pr-review/scripts` を実行する。

**テスト要否:** 新規テストは不要。削除の固定値テストは F。残す安全性テストは誤った HEAD・保存先・cleanup による S の損害を防ぐ。

## Task 3: PR 修正ループと review-fix-planning

**担当ファイル:** `.agents/skills/pr-review-fix-loop/scripts/loop.py`、`tests/`、`SKILL.md`、`references/records.md`、`.agents/skills/review-fix-planning/scripts/run_roles.py`、`tests/test_run_roles.py`、`SKILL.md`、`references/execution.md`。

- [ ] DSH の親側準備・プロンプト・書き込み例外・成果照合・診断分類を削除し、通常レビュアーの経路を維持する。
- [ ] `run_roles.py` とループの DSH 拒否を削除し、Codex の拒否を維持する。設定・記録の説明を更新する。
- [ ] DSH 専用の既存テストを削除し、一般の protocol・安全性テストを残す。
- [ ] `uv run pytest .agents/skills/pr-review-fix-loop/tests .agents/skills/review-fix-planning/tests` と `uvx ruff check` を実行する。

**テスト要否:** 新規テストは不要。専用経路の撤去は静的検査と実ループで確認する。既存の Codex 拒否と成果照合の安全性テストは維持する。

## Task 4: 雛形・Dev Container・現行文書

**担当ファイル:** `.devcontainer/agent-runner.toml`、`install_beforehand.bash`、`test-install-beforehand.bash`、`README.md`、必要な `.agents/skills/issue-to-pr/` の現行説明、`docs/maatlog-poc-porting.md`。参照の残りに応じて現行文書を追加する。

- [ ] DSH agent 定義を削除し、`review.inspect` の該当枠を `pi-deepseek` にする。`after_run` の `attach-runner` を維持して `finalize-parent` を外す。
- [ ] DSH の導入処理と専用の導入テストを削除する。README の headless 手順を除き、個人設定を手で更新するための短い案内だけを残す。
- [ ] 履歴の Spec・Plan を除く現行文書の DSH 参照を整理する。`bash .devcontainer/run-tests.bash` と `bash scripts/check-layout.sh`、設定の読み込みを実行する。

**テスト要否:** 新規テストは不要。撤去対象の導入テストは削除する。既存の共通の導入・レイアウト検査を実行して確認する。

## Task 5: 統合、公開、レビュー修正ループ

**担当:** このセッション。作業対象は上記の統合修正、Spec・Plan の実行記録、PR・Issue の更新。

- [ ] Spec の条件と Task 1〜4 の現行 HEAD の観測結果を照合する。`git grep -il dsh`、`git diff --check`、構文・参照先・設定を確認し、DSH 以外の adapter と Codex 拒否を精読する。撤去した親側の確定手順を参照していた `repo-cleanup-after-merge/SKILL.md` の旧 session 案内も更新する。
- [ ] `bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`uv run pytest tests/skills .agents/skills .agents/scripts tools` と関連 lint を最終 commit 後に実行し、HEAD・clean status・argv・終了コード・ログの完全パスを session に記録する。
- [ ] push 前に Issue 状態・競合と gitleaks を再確認し、検査した SHA のみを push して PR を作る。PR 本文に実行方式、判断、検証、時間、`Closes #243` を記す。
- [ ] `pr-review-fix-loop` を指定の既定設定で回し、`finalize.py` の結果を確認する。マージ成功後に #175・#211 を理由付きで not planned として閉じ、#116 に撤去をコメントする。PR と #243 の最終状態を確認する。

**テスト要否:** 新規の廃止確認テストは不要。実ループ、設定の対照、既存検査、差分レビューを証拠にする。

## 実行予算

- 能動時間の予算: 420 分。約 5,100 行の撤去と最大 3 サイクルのレビューを含むため。ledger は `/workspaces/reso-world/tmp/agents/issue-243.hzhugcs3/budget.jsonl`。
- phase の目安: 準備・Spec・Plan 35 分、Task 1〜4 とレビュー 150 分、統合・検証 45 分、PR 15 分、ループ最大 165 分、Issue 更新 10 分。
- worker の目安: 実装担当 75 分、レビュー担当 30 分。共有 feature worktree の実装担当と検証コマンドは監視上の強制停止対象にしない。無進捗が 15 分続けば現状を報告し、依存作業を保留して判断する。専用の使い捨て領域で行うループのレビュアーは既存の 45 分の期限と、15 分の結果保存枠を適用する。
- 同じ信頼性の失敗は再試行 1 回まで。安全の失敗は再試行せず全体停止。ループ固有のサイクル上限と停止条件を優先する。
- checkpoint: 各 Task と phase の境界、予算の 50%・100%、worker の失敗直後に `issue_budget.py show` を読み、判断を ledger に記録する。
- 縮小候補は DSH と無関係な説明・整理を別件候補にすること。受け入れ条件は縮小しない。独立の不具合を見つけたらこの PR に無断で加えず記録する。予算を使い切ったら停止して現状を報告する。

## 実装前の照合

- 原因: DSH を外した後も呼び出し元・設定・文書に専用経路が残ると、使えない担当や hook を選べてしまう。Task 1〜4 が設定から実行・保存までの各経路を閉じる。
- 修正する経路: runtime と監査（Task 1）、PR レビューの入力と保存（Task 2）、ループの選択と成果照合（Task 3）、導入と既定割当（Task 4）。Task 5 が共有の設定・HEAD・記録・順序を現行版で確認する。
- 対象外: 過去の Spec・Plan、個人設定の編集、他 repo、他ランタイムの仕様変更。これらに触れる必要が生じたら停止条件を確認する。

## Contingency

検証が失敗した場合は `systematic-debugging` に従って原因を特定し、影響した Task の担当範囲で直す。DSH 以外の既存不具合と確認できた場合は、失敗を成功扱いせず、対象と証拠を報告する。push 前の検査・ループの停止条件は issue-to-pr の規則どおりに扱う。
