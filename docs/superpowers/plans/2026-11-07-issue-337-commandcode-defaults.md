# Command Code 既定経路停止 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Command Code を通常経路から外し、再有効化経路を残す。

**Architecture:** 既存の設定と配置ブロックの最小変更。説明と実行結果を統合担当が照合する。実装担当の既定 self に従い、関連する2 Taskをinlineで直列実行する。

**Tech Stack:** TOML、Bash、zsh、Markdown、uv、既存 agent_runner。

**Spec:** `docs/superpowers/specs/2026-11-07-issue-337-commandcode-defaults-design.md`

状態: `draft`。issue-to-pr により実行許可あり。内容承認を意味しない。

## Global Constraints

- 個人設定・共有 ~/.pi・認証情報を変更しない。秘密値を出力しない。
- Command Code の agent/provider/launcher/tier/setup と既存安全テストを残す。
- Sol/max、OPENCODE_API_KEY、DeepSeek model_keyを変更しない。
- 固定baseはSpec記載SHA。移動時は停止。マージはループのfinalizeだけ。

## 受け入れ基準

- 動作環境: WSL2上のDev Container、uv管理Python、bash/zsh、既存Pi。実Rebuildは未実施として残す。
- 実入力: 実際のTOML雛形と個人設定のoverlay、設定なしの一時HOME、11本を配置する実スクリプトブロック、`pigod --version`（3キーをunset）。日本語READMEの移行手順も読む。
- 防御範囲: 通常割当からCommand Codeを外すが明示agentは受理する。個人overlayに明示された割当は自動変更しない。既存Command Code executableは削除しない。無キーversionはauthの有効性の証明ではない。

## Review Focus

- 個人設定で割当を上書きした環境は利用者の見直しが必要。
- 自動配置の11本と、維持する13本分のtier/ソースを混同しない。
- 再契約後もRebuildで手動ランチャーは消え、setupの再実行が必要。
- #305の履歴表を現在の推奨値として書き換えない。
- envを外したversion確認を認証・課金モデルの応答成功と説明しない。

新規テストはF/Lに当たるため追加せず、各Taskの実行・差分・既存安全テストで確認する。

## Task 1: 既定割当・自動配置の変更

**Files:** `.devcontainer/agent-runner.toml`、`.devcontainer/install_beforehand.bash`

**Interfaces:** TOMLの `workflows.review.assignments.inspect` とpostCreateのランチャー配置。Task2はこれを説明する。共有条件の照合は統合担当selfが行う。

- [x] 変更前の既存 `test-pi-superagents.bash` を実行し基準を確認する。
- [x] inspectの第三担当だけを `pi_opencode-go_deepseek4-flash_max` に置換。自動配置の見出しとpiccg/piccd installブロックだけ除去する。
- [x] 雛形単独・実overlayでcheck/listとload_configの実効割当を確認。隔離HOMEで配置ブロックを実行して通常11本／手動2本不在を確認する。期待: 全コマンド0、commandcode定義は残る。
- [x] `bash -n .devcontainer/install_beforehand.bash` と既存全ランチャーテストを実行。期待: exit 0。
- [x] 明示2ファイルをcommit: `fix: remove commandcode from default review and launcher deployment`

**テスト要否:** 新規はF/Lなので不要。既存のenv隔離・所有設定保護テストを残し実行する。

## Task 2: 文書・コメントの統合と全体検証

**Files:** `.devcontainer/README.md`、`scripts/setup_pi_commandcode_goat.zsh`、`.devcontainer/piccg`、`.devcontainer/piccd`（後3ファイルはコメントだけ）。このPlanのチェックと実行記録。

**Interfaces:** Task1の既定割当・配置、維持する手動setupとtier。

- [x] READMEの通常導入・11本配置・既定レビュアー・DSH推奨先を更新。Command Codeは停止中の手動再有効化として説明し、13本分のtierは維持。#305の履歴表は残す。
- [x] 個人設定の上書きと不要キーexportを利用者が見直す手順、既存shellのunset、秘密値を出さない未設定確認、人間による失効を記す。既存binary削除は任意、共有モデル/authは保持。
- [x] 再契約後の `zsh scripts/setup_pi_commandcode_goat.zsh` とRebuildごとの再実行を説明。setup/ランチャーの古い自動配置コメントを修正。実行処理は変えない。
- [x] OPENCODE_API_KEY/OPENCODE_GO_API_KEY/COMMANDCODE_API_KEYを外してpigodのversion経路を実行。期待: version、exit 0。auth内容は読まない。
- [x] READMEの入口どおり `bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`uv run pytest tests/skills .agents/skills .agents/scripts tools` を同期実行。期待: 全exit 0。実Rebuild/有料APIは行わない。
- [x] 明示ファイルをcommit: `docs: distinguish normal pi launchers from manual commandcode setup`
- [x] 固定baseから全体diffを作りfresh sp-reviewへ読み取り専用レビューを依頼。Critical/Importantは1修正pass、再レビューなし。必要な絞った再現はselfが実行。
- [ ] 最終commit後clean HEADで検証し、argv/exit/log/head/baseをSESSIONへ記録。Gitleaks後SHA指定push、PR作成・base/head照合。`Refs #337`、Rebuild残項目を明記。
- [ ] 指定3人、最大3サイクルのreview-fix-loopへ進む。終了後IssueへPRとRebuild確認をコメントする。

**テスト要否:** 文言・一覧の固定値テストは追加しない。実行と意味・構造の確認、既存安全テストで代える。

## 要件照合

Spec1/2→Task1の設定読込と実配置、Spec3/4→Task2のversionと既存ランチャーテスト、Spec5→Task2のREADME/コメント差分、Spec6→PR/Issueの残項目。Task1/2の共有する配置・割当・保持範囲を統合担当が実結果と照合する。

## 実行予算

全体360分（準備着手からの約45分を含め実質残315分を目安）。準備/実装30分、検証/全体レビュー45分、公開15分、ループ3×（レビュー45分＋修正30分）。ledgerは `/workspaces/reso-world/tmp/agents/issue-337.9hix5vvk/budget.jsonl` と同SESSIONのsdd。workerは同期、既定role期限（inspect45分、implement90分）、ループの監視を使用。sp-reviewは読み取り専用、独自の途中killはしない。各phase境界・50%・100%・失敗時にcheckpoint。同原因の信頼性再試行は1回まで、安全の失敗は再試行せず停止。100%で停止、勝手に範囲を狭めない。

## 実装・全体レビューの記録

2026-11-07: Task1 `c84223c6`、Task2 `c0b6d7f7`。設定単独/実overlayのcheck/list、実効3人の読込、隔離HOMEへの11本配置、3キー無しpigod version 1.5.0、全13ランチャー安全テストはいずれもexit 0。全体はシェル27件PASS、layout PASS、pytest 1309 passed。追加テストなし。sp-reviewの全体レビューは指摘なし（約6分）。最初の依頼はscope指定不足で実行されず、訂正後1回だけ実レビューした。実Rebuild、認証/モデル応答、個人設定/キー実移行は規定の対象外として未実施。準備・実装約47分、全体検証約20分、全体レビュー/記録約6分。公開とループはこの記録時点で未実施。最終commit後にcleanなHEADで再検証しSESSIONへ記録する。

## contingency（代替策）

実API前提の差は既存コード・実出力を調査し、意味を保つ最小の検証方法変更をledgerに残す。課金API・秘密値表示・個人設定変更で回避しない。検証やrunnerの失敗が解消しなければ停止し、残成果と再開方法を保存。base移動時は旧新SHAと再検証の必要性を報告し、捕捉値を置換しない。
