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

## Task 6: PR #249 レビュー修正サイクル 1

**担当:** `review-fix-planning` の既定 `claude-opus`。`run_roles.py --phase implement` の隔離 worktree で実装・commit し、controller が差分と停止を確かめて既存の feature branch に取り込む。TDD は行わない。

- [x] `BatchResult` の入力境界で、旧結果の空 `unrelated_checkout_audit` だけを受け入れる。現行の出力からは除外し、空以外や未知欄は引き続き拒否する。対象は `tools/agent_runner/models.py` と、その守りを実装するモジュールの安全性テスト。読取側4入口を独立に実行して確認する。
- [x] `helper_write_exceptions` と loop / run_roles の呼出元で、checkout の浅さと実際の Git 書き込み先を一致させる。shallow では元 Git の書き込みを許可せず、通常 checkout では必要な許可を残す。対象は `.agents/skills/pr-review/scripts/review_run.py`、`.agents/skills/pr-review-fix-loop/scripts/loop.py`、`.agents/skills/review-fix-planning/scripts/run_roles.py` と既存の安全性テスト。変更した共通の許可範囲の説明も実装と一致させる。別の既存 Cursor 解説の不一致は fix-check の V-1 として記録する。
- [x] `STEP_TOTAL` の表示ずれは実在を記録し、今回の致命的な修正に含めない。該当するコード・テスト・文書を編集しない。
- [x] 変更した入口の局所検証、`bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`uv run pytest tests/skills .agents/skills`、関連する `tools/agent_runner` のテストと静的解析を通す。必要な一時入力・ログは session に置く。controller が最後の変更後に検証と Gitleaks の検査を確認する。
- [x] 保存済みの確認済み一覧を使って、既定の1回の自己レビューと fix-check を行う。自己レビューは指摘0件、fix-check は9主張・8ファイル・181文書候補を確認し、致命的な指摘は無い。Spec の経路表を実測結果へ更新する。
- [x] `completed` の Spec を1回 commit し、検査済みの SHA `ed1c1bbb9e683ce88f30a810c95b24de7d7563d3` を既存 PR へ push して状況コメントを記録した。ループへ結果を返し、第2サイクルへ進んだ。

**テスト要否:** 2つの安全条件は S。旧結果の誤った未確認扱いと書き込み許可の過大化は、失敗が目立たないまま停止状態や利用者の Git に影響するため、守りを実装するモジュールに代表テストを置く。DSH を廃止した事実を照合するテストは書かず、TDD も行わない。読取入口や文書の固定値を重複して写すテストは作らず、実行・構造確認で確かめる。

## Task 7: PR #249 レビュー修正サイクル 2

**担当:** `review-fix-planning` の既定 `claude-opus`。前サイクルと同じ安全条件の2回目かつ `f12c400` が作った判定の回帰なので、Spec の「守る条件の設計」と影響経路の表を先に確認する。担当は `run_roles.py --phase implement` の隔離 worktree で実装・commit し、controller が差分・停止・検証を確認して取り込む。TDD は行わない。

- [x] 現行 HEAD `ed1c1bbb9e683ce88f30a810c95b24de7d7563d3` の M-2 を隔離 worktree で再現し、`verified/ed1c1bbb9e68.json` に confirmed 1件・未確認0件を保存した。ほか3件のレビューの active 指摘と、前回の判断を照合した。
- [x] 明示した checkout の Git 操作が、`GIT_DIR`・`GIT_COMMON_DIR` を含む外部の `GIT_*` に向かわないよう、`review_target._git`、`pr_review_workspace.git`、`loop.git_output` の環境を共通の方法で扱った。親・対象の前段にある `agent_tmp._git` と `superpowers_context._git` にも同じ除去を適用した。runner の子と同じ対象を `uses_owned_history` が判定し、浅い元 Git への過大な許可を出さず、通常 checkout で必要な権限を保つ。
- [x] 実装の後で、`test_run_roles.py` に S の代表テストを1件加えた。浅い／通常と汚染なし／`GIT_DIR` を対照し、ガードを外した一時変異では1件失敗。DSH 廃止を確認するテストは作らず、TDD は行っていない。
- [x] resolver、prepare・save・cleanup、loop の許可文、外部 self-review の許可文を隔離実行で照合した。担当は関連587件、`run-tests.bash` 23件、`check-layout.sh`、全 Python 1726件を成功させ、旧版との lint・型検査比較で新規指摘0件。controller は同一ツリー ID、代表テスト4件、`git diff --check`、Gitleaks 15 commit 検出0件を確認した。
- [x] 確認済み一覧を入力に既定1回の自己レビューと fix-check を行った。自己レビューは `172bc8f` の全体差分で指摘0件。fix-check の V-1 は直接 pr-review helper の認証変数が消える機能停止として確認し、`93bf88f` で transport 認証だけ戻した。自己レビューは繰り返さず、偽 transport の from/to/修正後、関連98件、全 Python 1726件、`run-tests.bash` 23件、`check-layout.sh` で再検証した。Spec の設計表と実測を更新した。
- [x] Gitleaks が検査した最終 SHA `4ded95313c51c98b857769edf64ce0c934fbacf2` だけを既存 PR に push し、判断の記録と状況コメントを投稿してループへ結果を返した。

**テスト要否:** 書き込み許可が不要な元 Git を含むと、失敗が表示されず利用者の Git を変更し得るため S。1件の代表テストで正常と環境汚染の両側を確かめる。廃止の事実、文言、ファイル一覧を写すテストは F/L に当たり不要。代わりに現行 code の静的確認・実コマンド・差分を確認する。

## Task 8: PR #249 レビュー修正サイクル 3

**担当:** `review-fix-planning` の既定の修正担当。同じ transport 認証条件の適用漏れなので、Spec の「守る条件の設計」と Git 呼出元の表を先に確認する。隔離 worktree で実装・commit し、controller が差分、担当の停止、現行 HEAD の検証を確かめて取り込む。TDD は行わない。

- [x] 4 レビュアーの同一指摘を現行 HEAD で独立に確認し、`verified/4ded95313c51.json` に保存した。前サイクルの `fix`・`skip` 判断を引き継いだ。
- [x] `review_target.fetch_pull_head` の remote fetch にだけ認証用4変数を渡した。ローカル Git の解決と ref 確認では `GIT_*` の除去を維持し、base/historical fetch と書き込み許可の経路を照合した。
- [x] SSH・HTTPS の偽 transport で、直接 `prepare` から HEAD fetch まで、認証なし／ありと汚染された `GIT_DIR` の両側を実行した。関連テスト、`run-tests.bash`、`check-layout.sh`、全 Python テスト、差分・構文を確認した。最終 SHA の Gitleaks 検査は push 直前に行う。
- [x] 規定の1回の自己レビューと fix-check を実施した。自己レビューの active 指摘0件、コードの fix-check 主張9件成立。前サイクルの誤った検証記録を Spec で訂正した。自己レビュー後のコード変更はない。
- [ ] ループへ結果を返し、返された終了条件に従う。マージできた場合にだけ #175・#211 の not planned クローズ、#116 のコメント、#243 の状態確認へ進む。

**テスト要否:** 今回の直接 fetch の欠陥は明示的な非0終了で気付ける L。恒久テストは追加しない。DSH 廃止の有無を固定するテストも利用者の指示に従って作らない。修正後の一時的な偽 transport 実行と、既存の S テスト・構造検査で確かめる。
