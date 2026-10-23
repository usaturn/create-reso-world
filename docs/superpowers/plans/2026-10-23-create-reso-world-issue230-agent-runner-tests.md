# Issue #230 tools/agent_runner のテスト削減 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Spec の棚卸しの表のとおりに `tools/agent_runner/tests/` のテストを消し、変異の監査で守りの検出が残ることを確かめて、PR（`Closes #230`）を作りマージする。

**Architecture:** 削除は、棚卸しで決めた「残す node ID」の一覧（Spec の棚卸しの表と同じもの）から、スクラッチの `apply_plan.py` で関数・parametrize のケースを機械的に消し、機械で消せないもの（fixture の parametrize、複数の軸、使われなくなった補助・偽の CLI の場面）を手で直す。検証は、領域の pytest、一時環境の ruff（未使用の import・名前）、削減後の木での変異の確認、全体の入口で行う。

**Tech Stack:** Python 3.14、pytest、uv。監査だけに coverage 7.17.0・ruff 0.17.2 を `uv run --with` の一時環境で使う（リポジトリの設定・依存は変えない）。

**Spec:** `docs/superpowers/specs/2026-10-23-create-reso-world-issue230-agent-runner-tests-design.md`

## Global Constraints

- 状態は draft。実行許可は Spec の「管理・実行許可」（`/issue-to-pr … --merge --assign implement=self`）。内容の承認（approved）ではない
- 変えてよいのは `tools/agent_runner/tests/` と、撤去する `tools/agent_runner/adapters/__init__.py` の `runtime_supported`（Spec の「撤去」）、この子の Spec・Plan だけ。`tools/test_support/`・ルートの `conftest.py`・`pyproject.toml`・`.devcontainer/`・`AGENTS.md`・ほかの領域は変えない
- 新しいテストは書かない。残すテストの中身は変えない（消したテストだけが使っていた import・補助・fixture・偽の CLI の場面を消すことを除く）
- pytest の `--basetemp` は worktree の外（`/tmp` の `mktemp -d`）に置く
- 変異のコピーは `/tmp` に `tempfile.mkdtemp` で作り、PID 名前空間（`unshare --user --map-current-user --pid --fork --kill-child --mount-proc`）の中で実行する（Spec の D-230-5）
- 監査の道具と記録は `/workspaces/reso-world/tmp/agents/issue-230.fuotebjq/audit/` に置き、コミットしない

## Review Focus

1. サブプロセスだけで動くコード（`_supervisor.py`、`python -m tools.agent_runner`、`dsh_sandbox.py`）の守りを、消したテストだけが検出していないか（監査の coverage は子のプロセスも計測し、計測できない 7 件は明示的に足した）
2. ほかのテストのファイルが import する補助（`test_runner.py` の `FakeAdapter`・`configuration`・`repository`・`set_when`・`written`、`test_workspace.py` の `git`、`test_process.py` の `alive`）を消していないか
3. parametrize のケースを減らしたときに、残すケースの値・ID が変わっていないか（`collect-only` の前後の照合）
4. 読み込み時に評価される一覧（環境変数の許可リスト、権限のフラグ）の要素を外した変異を、残したテストが検出するか（監査の「名前を使う行」の選択）
5. 期限・時刻に頼る遅いテストが、並列の負荷で誤って失敗し、監査で「残したテストが検出した」と誤って数えていないか（削減後の木での再確認）

---

### Task 1: 棚卸しどおりにテストと、それだけが使っていた補助を消す

**Files:**
- Modify: `tools/agent_runner/tests/**/*.py`（棚卸しの表で「消す」「n 件を残す」の行）、偽の CLI（`adapters/codex/fake_cli.py`・`adapters/devin/fake_cli.py`・`adapters/dsh/fake_cli.py`）の消したテストだけが使っていた場面、`adapters/claude_code/conftest.py`・`adapters/pi/conftest.py` の e2e だけの fixture、`adapters/dsh/ptc_tool_results.json` の消したテストだけが読む項目
- Delete: 全てのテストが消えるファイル（`adapters/cursor/test_integration.py`・`adapters/test_skills.py`）と、使う側が無くなった偽の CLI（`adapters/claude_code/fake_cli.py`・`adapters/pi/fake_launcher.py`・`adapters/cursor/fake_cli.py`）

**Interfaces:**
- Consumes: Spec の棚卸しの表（残す node ID は `retained-final.txt` と同じ集合）
- Produces: 収集される node ID が `retained-final.txt` と一致する木

テストの要否: 新しいテストは書かない（削除だけ）。代わりの検証は Step 2〜4。

- [ ] **Step 1:** `uv run --no-project python <AUDIT>/bin/apply_plan.py <WT> <AUDIT>/collect-base.json <AUDIT>/retained-final.txt` を実行し、`manual` に出た関数を手で直す（fixture の parametrize は関数ごと残すか消すかを棚卸しの表に合わせる）
- [ ] **Step 2:** `uv run --locked pytest --collect-only -q -p no:cacheprovider tools/agent_runner | grep '::'` が `retained-final.txt` と、parametrize の ID の付け直し（Spec の表に書く）を除いて一致することを確かめる
- [ ] **Step 3:** `uv run --no-project --with ruff==0.17.2 ruff check --select F401,F811,F841,F821 --no-cache tools/agent_runner/tests` が終了コード 0
- [ ] **Step 4:** `uv run --locked pytest tools/agent_runner -q -p no:cacheprovider --basetemp "$(mktemp -d /tmp/issue-230-verify.XXXXXX)/bt"` が全件通過
- [ ] **Step 5:** 消したテストだけが使っていた補助（関数・クラス・fixture・偽の CLI の場面・`ptc_tool_results.json` の項目）を消し、モジュールの名前の参照の走査（AST で名前・属性・引数を数える）で参照の無い補助が残らないことを確かめてから、Step 3・4 をやり直す
- [ ] **Step 6:** commit（`test(agent_runner): delete F, L and surplus D tests and their helpers by the #230 inventory`）

### Task 2: 使われなくなったコードの経路（`runtime_supported`）を撤去する

**Files:**
- Modify: `tools/agent_runner/adapters/__init__.py`（`runtime_supported` の撤去）

**Interfaces:**
- Consumes: Task 1 の木（`runtime_supported` を呼ぶテストが無い）
- Produces: `tools.agent_runner.adapters` から `runtime_supported` が無くなる（呼び出し元が無いことは Spec の「撤去」）

テストの要否: 書かない。代わりの検証は Step 2〜3。

- [ ] **Step 1:** `runtime_supported` を消す
- [ ] **Step 2:** `git grep -n runtime_supported -- . ':!docs/superpowers'` が 0 件
- [ ] **Step 3:** Task 1 の Step 3・4 をやり直して通る
- [ ] **Step 4:** commit（`refactor(agent_runner): remove the unused runtime_supported helper`）

### Task 3: 削減後の木で変異の検出を確かめる

**Files:** なし（スクラッチの監査だけ）

テストの要否: 書かない。検証そのもの。

- [ ] **Step 1:** 削減後の木（HEAD の `git archive`）で、基準で検出された変異（本走査の `killed_retained` と戻した分）を `run_audit.py --retained` なしで実行し、全てが検出されることを確かめる。検出されないものは Spec の「変異の監査」の表に理由（L）を書くか、テストを戻して Task 1 の Step 4 をやり直す
- [ ] **Step 2:** 重さが高の守りで代表に絞ったものについて、壊したコピーで残したテストが失敗した記録（変異の ID・失敗したテスト）を Spec の「守りの確認」に書く

### Task 4: 計測と Spec の仕上げ・全体の検証・PR

**Files:**
- Modify: `docs/superpowers/specs/2026-10-23-create-reso-world-issue230-agent-runner-tests-design.md`（計測・棚卸しの表・監査・申し送り）、この Plan（完了の記録）

テストの要否: 書かない。検証は Step 2。

- [ ] **Step 1:** commit 後に Issue の計測（`uv run --locked pytest --collect-only -q tools/agent_runner | tail -n 1`、`git ls-files -z -- tools/agent_runner/tests | xargs -0 cat | wc -l`）を取り、Spec に書いて commit
- [ ] **Step 2:** 全体の入口（`uv run pytest tests/skills .agents/skills .agents/scripts tools`、`bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`）を実行し、argv・終了コード・ログを `tmp/agents/issue-230.fuotebjq/verify/` に記録する（`--merge` の検証の記録と `--checks-file`）
- [ ] **Step 3:** `scripts/scan-before-push.sh` → push → `gh pr create --repo usaturn/create-reso-world --base main --head feat/issue-230-agent-runner-tests`（`Closes #230`）
- [ ] **Step 4:** PR 修正ループ（`loop.py start <PR の URL> --controller-model claude-opus-5-5 --controller-runtime claude-code --assign implement=self`）

## 実行方式

`superpowers:executing-plans`（inline）。Task は同じファイル群への順の変更で、削除はスクリプトで当てるため、サブエージェントに分ける利点が無い（issue-to-pr の表: `self` が true で、同じファイルの逐次変更）。

## 実行予算

`.agents/execution-budget.md` に従う。ledger は `/workspaces/reso-world/tmp/agents/issue-230.fuotebjq/budget.jsonl`（2026-10-23T08:03:59Z 開始）。

- 全体の能動時間: 450 分。根拠: 同じボードの #235（75 件）は 300 分で足りずに延長し、#232（1,056 件）はループが 3 サイクルだった。この子は 1,064 件・10,404 行で、変異の監査（約 3,000 個）が加わる。司令塔の監視の期限（子の起動から 8 時間）に収まるようにした
- phase の目安: 準備 20 分、棚卸しと事前走査 60 分、本走査と判定・戻し 80 分、削除の適用・検証・Spec と Plan 60 分、PR と PR 修正ループ 200 分（3 サイクル ×（レビュー 45 分＋計画・修正 20 分））、余り 30 分
- worker の期限: 走査（`run_audit.py`）は task_watch の宣言（絶対期限 5,400 秒、`--stop INT`、停止確認 30 秒）で起動する。変異 1 個の pytest は 420 秒で SIGKILL。棚卸しのサブエージェント 6 つは読むだけで、結果の通知で待つ。ループのレビュアーの期限はループの設定のとおり（45 分）
- 再試行の上限: 同じ失敗の再試行は 1 回（ledger の `retry_limit` 1）
- checkpoint: phase の境界、予算の 50%（225 分、11:48Z ごろ）、100%（15:33Z ごろ）、worker が失敗した直後
- 縮小・切り出し・方法変更の候補: (1) 走査が予算に収まらなければ、変異の演算子を守りの文（`raise`・`return`・状態の代入）と条件に絞る。(2) lost が多すぎて判定が予算に収まらなければ、消す側のテストを戻す（S とみなす）既定にして、L と判定する群を限る。(3) PR 修正ループがサイクルの上限に達したら、未対応の指摘を PR と Spec に残して止まる（延長は司令塔の指示による 1 回だけ。利用者の決定の 7 つ目）。(4) fixture の共通化など、行数のための追加の削減はこの子では行わず #236 に申し送る

## 完了

（2026-10-23 の実行の記録。PR の作成より前に書いた分）

- Task 1: commit `4c4a964`。棚卸しの残す 347 件に、監査で戻した 19 件と fixture の起動の経路の 2 件を足した 368 件を残した（Task 3 の確認で 3 件の戻しを取り消し、365 件。commit `c13ea67`）。`apply_plan.py` で関数 187・ケース 311 を消し、手で直したもの 5 件（値が変数の parametrize 3 件、fixture の params の 2 件）。補助の削除と ruff（F401 の 40 件）。収集の照合は関数ごとの件数で一致、領域の 368 件（`c13ea67` で 365 件）が通った
- Task 2: commit `c1d8755`。`git grep -n runtime_supported -- . ':!docs/superpowers'` は 0 件
- Task 3: 縮めた木での確認 1,962 個（1,957 個を検出。検出しない 4 個と戻したテストを確かめ直し、検出しない戻し 3 件を取り消し、lost を 2 個足した。Spec の「縮めた木での確認」）と、重さが高の守りの確認 32 項目（Spec の「守りの確認」）
- Task 4: 計測は 1,064 件・10,404 行 → 365 件・7,125 行（Spec の「計測」）。全体の入口・push・PR・PR 修正ループは、この記録の後に行う（結果は PR の本文と #230 の完了のコメント）
- 所要時間（能動時間、ledger）: 準備 20 分、棚卸しと事前の走査 50 分、本走査と lost の判定 75 分、削除の適用・補助の整理・コミット 15 分、Spec・Plan と縮めた木での確認・確かめ直し 35 分（PR の作成までの見込み 約 205 分）
- 方法の変更（ledger の checkpoint）: 事前の走査の順と書き込み、PID 名前空間（安全）、テスト 1 件 30 秒の上限（Spec の D-230-12）
