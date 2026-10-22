# Issue #234: .devcontainer と tools/devenv_migration のテストを減らす Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans（inline）。独立した Task は同期のサブエージェントに任せてよい。Steps は checkbox（`- [ ]`）で追う。

**Goal:** Spec の棚卸しの表のとおり、`.devcontainer` と `tools/devenv_migration` のテストを S（F∩S を含む）と D の代表に絞り、済んだ一度きりの移行（pi の旧拡張の撤去）をコードとテストごと撤去する。

**Architecture:** 担当ファイルが分かれた 4 つの群（Task 1〜4）を順に処理し、Task 5 で参照の掃除、重さが高の守りの確認、計測、全体検証を行う。撤去は `install_beforehand.bash` の pi の節と `pi-provider-setup.py` の settings 経路だけ。

**Tech Stack:** bash、pytest（`tools/devenv_migration`）、bubblewrap（隔離の確認）

**Spec:** `docs/superpowers/specs/2026-10-23-create-reso-world-issue234-devcontainer-tests-design.md`（棚卸しの表、決定記録 D-234-1〜8、撤去の根拠）

## 管理

- 状態: draft
- 対象 Issue: https://github.com/usaturn/create-reso-world/issues/234（親 #228、子のキー `devcontainer-tests`）
- DOC_ROOT・CODE_ROOT: `/workspaces/reso-world/.worktrees/issue-234-devcontainer-tests`（branch `feat/issue-234-devcontainer-tests`）。PARENT_ROOT: `/workspaces/reso-world`
- 実行許可: Spec の「管理・実行許可」と同じ（`/issue-to-pr #234 --merge`）
- 実行方式: inline（`executing-plans`）を基本に、Task 1〜4 は新しい文脈の同期サブエージェントに任せる。`implement_task.py check` の `self` が true。理由: 4 群は担当ファイルが分かれ、棚卸しの分析（`inventory-F1〜F4.md`）が同じ分け方で済んでいる。同じファイルを同時に書かせない
- セッションディレクトリ（ログ・棚卸しの原本・ledger）: `/workspaces/reso-world/tmp/agents/issue-234.w2vv4kg8/`（commit しない）。以下 `$SESSION`
- 基準: `origin/main` の `481a047`

## Global Constraints

- 各 Task は担当ファイルの外を変えない。`pyproject.toml`・ルートの `conftest.py`・`tools/test_support/`・`.devcontainer/run-tests.bash`・`README.md` の「テスト」・`.devcontainer/README.md` の「テストの実行」・`AGENTS.md`・Meshy・mount の定義は変えない
- 残すテストは Spec の棚卸しの表の「処置」のとおり。分類に迷ったら残して「迷い」に書く。F∩S は消さない（mount の一覧、unset する環境変数の一覧、絶対パスの禁止、削除の既定値、資格情報の送り先）
- 残すテストの先頭のコメントに、防ぐ損害と理由（F∩S は特に）を 1〜2 行で書く。消したテストだけが使っていた補助・fixture・偽の CLI は一緒に消す
- ランチャーの名前・引数と、撤去しない postCreate の段は変えない
- 各 Task は担当ファイルのテストだけを実行する。全体のテストを同時に回さない（#218）
- `AGENTS.md` の「日本語表現」で避ける語（契約・原子的・製品・着地・正本・巡・席・実行器）を使わない

## Review Focus

- 気付けない損害を防ぐテスト（S）を、L・D として消していないか → Task 5 の重さが高の守りの確認、最後のレビュー
- 撤去が postCreate を壊さない（`install_pi_extensions` の導入と事後確認、step 数、`bash -n`） → Task 2、Task 5
- 消したファイルへの参照が文書・スクリプト・設定に残っていない → Task 5 の Step 1

## 要件と Task・検証の対応

| Issue #234 の受け入れ | 担当 Task | 観測する結果 | 検証方法 |
| --- | --- | --- | --- |
| Spec に棚卸しの表がある | 済（Spec） | 全テストに分類と理由 | Spec の「棚卸しの表」 |
| F・L・D の余り・撤去した経路のテストと、それだけが使っていた補助が消えている | Task 1〜4 | 処置どおりのファイル・場面が無い | Task 5 の Step 1（`git grep`）と diff の確認 |
| 重さが高の守りの代表を壊して失敗を確かめる | Task 5 | 各壊し方で残したテストが失敗する | Task 5 の Step 2 |
| 残したテストが通る | Task 1〜4、Task 5 | 領域・全体の終了コード 0 | Task 5 の Step 4 |
| 件数・行数の前後を Spec と Issue に書く | Task 5 | 計測の結果 | Task 5 の Step 3 |
| 撤去したので rebuild の後の確認の手順を Spec に書く | 済（Spec）、結果は利用者の rebuild の後 | – | Issue #234 のコメントに記録（PR のマージ後の申し送り） |

共有する前提: `test_pi_agent_paths.py` が兄弟ファイルから import している補助（`isolated_command` ほか）は Task 1 が自分のファイルへ移してから、Task 2 が `test_pi_mcp_adapter_migration.py` を消す。`STEP_TOTAL` は Task 2 が 29 に合わせる。

## 実行予算

- Issue 全体の能動時間の予算: 480 分（ledger: `$SESSION/budget.jsonl`、2026-10-23 に開始）。根拠は #221・#229 の実績（300〜360 分）に、25 ファイル・約 5,800 行の棚卸しと実装・重さが高の守りの確認 9 件以上、PR 修正ループ（最大 3 サイクル）が加わるため
- phase の目安: 準備・棚卸し・Spec・Plan 90 分（済の見込み）、Task 1〜4 計 150 分（Task 1 と 3 と 4 を並行、Task 2 は Task 1 の後）、Task 5 60 分、PR 20 分、PR 修正ループは残り（予算に収まる範囲）
- worker（サブエージェント）の期限: 1 Task 60 分、無進捗 15 分。長時間の実行はバックグラウンドで実行し、終了コードで確かめる。1 回の期限は 30 分
- 再試行の上限: 同じ signature の信頼性の失敗（テストの時間切れ・I/O の停止・負荷による期限切れ #218）は 1 回まで。安全の失敗（親の checkout や実環境の `~/.pi` の書き換え、想定外の外部送信）は再試行せず止まる
- checkpoint: Task 1〜4 の後、Task 5 の後、PR の作成の後、ループの各サイクルの後、予算の 50%・100%（100% では停止して報告する）
- 縮小・方法変更の候補: bwrap が使えない環境で隔離のテストが動かないときは、その場面を「環境により skip」とせず、同じ守りを別の手段で確かめる案を Spec に書いて止まる。行数が 1/3 に届かない分は、Spec の「迷い」と一覧に残して `integration` に渡す（数のために S を消さない）

## Task 1: pi の Python 設定テスト（F1）

**Files:**
- Modify: `tools/devenv_migration/tests/test_pi_provider_setup.py`（agent_paths の残す 7 件を移す。80 件→13 件＋7 件）
- Modify: `tools/devenv_migration/tests/test_pi_vertex_launchers.py`（133 件→18 件）
- Delete: `tools/devenv_migration/tests/test_pi_agent_paths.py`

**テストの要否:** 既存テストの削除と代表化（新しい挙動のテストは書かない）。確認は、領域の pytest と、移した 7 件が兄弟 import なしで通ること。

- [ ] **Step 1:** Spec の F1 の表のとおり処置する。`test_pi_agent_paths.py` の 7 件が使う補助（`ROOT`・`_snapshot`・`isolated_command`・`Harness`・`SETUPS` など）は、`test_pi_provider_setup.py` に持たせ、`test_pi_mcp_adapter_migration` からの import を無くす。`--settings-check`・`--settings-clean` を使う部分は外す（Task 2 が撤去する）
- [ ] **Step 2:** `uv run --locked pytest tools/devenv_migration/tests/test_pi_provider_setup.py tools/devenv_migration/tests/test_pi_vertex_launchers.py` が通る。`git grep -n 'test_pi_agent_paths\|test_pi_mcp_adapter_migration' -- tools .devcontainer/test-pi-migrations.bash` で `test_pi_provider_setup.py` と `test_pi_vertex_launchers.py` からの参照が無い
- [ ] **Step 3:** commit（`test(devenv): reduce the pi provider setup and vertex launcher tests (#234)`）

## Task 2: pi の導入と移行（F2、Task 1 の後）

**Files:**
- Modify: `.devcontainer/install_beforehand.bash`（3 step と置換後片付けと `--settings-check` の撤去、`STEP_TOTAL` 29、step の見出し）
- Modify: `.devcontainer/pi-provider-setup.py`（`settings_update` と `--settings-check`・`--settings-clean` の撤去）
- Modify: `.devcontainer/test-pi-superagents.bash`（46 場面→9 つの関数）、`tools/devenv_migration/tests/test_pi_shared_packages.py`（2→1 件）
- Delete: `tools/devenv_migration/tests/test_pi_mcp_adapter_migration.py`、`test_pi_installer_isolation.py`、`.devcontainer/tests/pi-launcher-install.bash`、`.devcontainer/test-pi-openai-codex.bash`、`.devcontainer/test-pi-migrations.bash`
- Modify: `.devcontainer/README.md`（撤去した経路を説明する行だけ。Spec の F2「文書の変更」）

**テストの要否:** 撤去と削除。残す場面（`test-pi-superagents.bash` の導入の場面と `test_rebuild_preserves_shared_packages`）は撤去後の `install_pi_extensions` と合わせて直す。

- [ ] **Step 1:** 撤去を実装する。`install_pi_extensions` は `pi install --approve npm:@teelicht/pi-superagents` と、導入後の `pi list` に新拡張が在ることの確認だけを残す。`bash -n .devcontainer/install_beforehand.bash`、`STEP_TOTAL` と `grep -c '^step "'` が同じ（29）
- [ ] **Step 2:** テストを処置する（Spec の F2 の表）。`bash .devcontainer/test-pi-superagents.bash` と `uv run --locked pytest tools/devenv_migration` が通る
- [ ] **Step 3:** README の行を直す。`.devcontainer/README.md` に、残っていたら手で `pi remove npm:<名前>` する旨を残す
- [ ] **Step 4:** commit（`refactor(devcontainer): retire the finished pi extension cleanups and their tests (#234)`）

## Task 3: herdr の bash テスト（F3、Task 1 と並行）

**Files:**
- Modify: `.devcontainer/test-herdr-migration.bash`（712 行→約 400〜450 行）
- Delete: `.devcontainer/test-herdr-status.bash`、`.devcontainer/test-herdr-agent-task.bash`

**テストの要否:** 削除と縮小。F∩S（unset の一覧・POLLUTED_・資格情報の送り先）は消さない。

- [ ] **Step 1:** Spec の F3 の表のとおり処置する。`bash .devcontainer/test-herdr-migration.bash` が通る
- [ ] **Step 2:** 消した 2 本への参照（README・docs・スクリプト）を `git grep` で調べ、撤去した経路を説明する行だけを直す
- [ ] **Step 3:** commit（`test(devcontainer): reduce the herdr tests to the guarded behaviors (#234)`）

## Task 4: その他の bash テスト（F4、Task 1 と並行）

**Files:**
- Modify: `.devcontainer/test-cleanup-workspace.bash`、`test-readme.bash`、`test-run-tests.bash`、`test-install-ctx7.bash`、`test-install-gitleaks.bash`、`test-report-resoloop-skills.bash`、`test-install-resoloop.bash`、`test-shell-tools.bash`、`test-initialize-mounts.bash`、`test-install-beforehand.bash`
- Delete: `.devcontainer/test-verify-resonite-tooling.bash`、`.devcontainer/test-resoloop-tool.bash`

**テストの要否:** 削除と縮小。mount の一覧は F∩S として残す。`test-install-beforehand.bash` の pi の step は触らない（Task 2）。

- [ ] **Step 1:** Spec の F4 の表のとおり処置する。変えた各ファイルを `bash .devcontainer/test-*.bash` で個別に実行して通る
- [ ] **Step 2:** 消した 2 本への参照を `git grep` で調べ、撤去した経路を説明する行だけを直す
- [ ] **Step 3:** commit（`test(devcontainer): reduce the shell tests to the guarded behaviors (#234)`）

## Task 5: 統合確認

**Files:**
- Modify: Spec（「迷いの一覧」「計測の結果」）、Plan（チェックと「検証の記録」）

**テストの要否:** 書かない。参照の掃除、重さが高の守りの確認、計測、全体検証で確かめる。

- [ ] **Step 1: 参照の掃除。** 消したファイル名と撤去した名前（`test-pi-migrations`・`test-pi-openai-codex`・`test-herdr-status`・`test-herdr-agent-task`・`test-verify-resonite-tooling`・`test-resoloop-tool`・`test_pi_agent_paths`・`test_pi_mcp_adapter_migration`・`test_pi_installer_isolation`・`pi-launcher-install`・`remove_pi_mcp_adapter`・`remove_pi_distill`・`remove_pi_lens`・`--settings-check`・`--settings-clean`）を `git grep` し、凍結した記録（`docs/maatlog-poc-porting.md`、過去の Spec・Plan）以外に残っていれば撤去した経路の説明だけを直す（`.devcontainer/README.md` の「テストの実行」・`README.md` の「テスト」は `integration` の担当なので、残る参照は #228 にコメントする）
- [ ] **Step 2: 重さが高の守りの確認（D-234-6）。** Spec の各棚卸しの「壊し方案」のうち、重さが高のもの（F1 の 9 件、F2 の bwrap 不在・Vertex の auth overlay・`--if-absent`、F3 の 10 件、F4 の必須 5 件）を、`mktemp -d` で作った `/tmp` の使い捨てのコピーで 1 つずつ壊し、残したテストが失敗することを確かめる。結果（守り・壊し方・失敗したテスト・終了コード）を Spec の「計測の結果」に書き、コピーを `${d:?}` 付きで消す。失敗しないテストは守りになっていないので、テストを直す
- [ ] **Step 3: 計測。** #234 の「検証」の 3 つのコマンドを commit 済みの状態で実行し、前後（437 件・5,778 行→?）を Spec の「計測の結果」に書く。「迷いの一覧」を各棚卸しから集める
- [ ] **Step 4: 検証。** `git status --porcelain` が空であることを確かめ、worktree のルートで `uv run --locked pytest tools/devenv_migration`、`bash .devcontainer/run-tests.bash .devcontainer/test-*.bash`、`uv run pytest tests/skills .agents/skills .agents/scripts tools`、`bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh` を順にバックグラウンドで実行する（並行させない。各 30 分まで）。落ちたら単独で再実行し、基準（`481a047`）の同じテストと比べて判定する。検証した HEAD・argv・終了コード・ログの完全パスを `$SESSION/verify/record.md` に、`finalize.py --checks-file` の形のファイルを `$SESSION/verify/checks.json` に書く
- [ ] **Step 5: ブランチ全体のレビュー**（新しい文脈のサブエージェント 1 回）。Spec・Plan・Issue #234・#228 の基準・`git diff origin/main...HEAD` を渡し、(1) S を消していないか、(2) 撤去が postCreate を壊していないか、(3) F∩S が残っているか、(4) 担当外のファイルを変えていないか、を見てもらう。致命的な指摘だけを直す
- [ ] **Step 6:** Spec・Plan の記録を commit する（これが最後の commit。以降に変えたら Step 3〜4 をやり直す）

## 検証の記録

（実装の後に書く）
