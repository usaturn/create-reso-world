# PR #194（Issue #166）のレビュー修正の選別（1 回目）

- 文書管理・対象: `usaturn/create-reso-world`、PR #194（`fix/issue-166-test-git-env-isolation`）、Issue #166
- 状態: `completed`
- 実行許可: 利用者の `/review-fix-planning #194`（2026-10-20 JST）。「計画だけ」などの指定が無いので、完遂（結論の三択のどれかを完了させる）で実行した。完遂の依頼は、この PR の承認済み実装修正と、結論 2 のマージ・関連 Issue の更新の実行許可として扱う（review-fix-planning の「依頼の種類と結論」）。内容の承認ではない
- 現行 HEAD: `6cf7096aaaa61b3a02bf65e448022ef37eb7deea`（PR の head）。PR の分岐点（merge-base）は `8f5074ac14b43803b334f8256e4273b97a40a0f3`。base `origin/main` はその後 `b65ef0caf0f8d93dff6bb897fa14008256b8e835` まで進んでいる（PR #190〜#193 のマージ）
- レビューディレクトリ: `/workspaces/reso-world/reviews/usaturn/create-reso-world/#194-fix-issue-166-test-git-env-isolation/`
- planner: claude-opus-5-5（Claude Code 2.1.304）。サイクル: 1。review-fix-planning は親の main checkout（`b65ef0c`）の版を使った
- 確認済みの一覧: 同じディレクトリの `verified/6cf7096aaaa6.json`・`.md`（review-verify、mode cycle）。工程の記録: `verified/6cf7096aaaa6.planning.json`
- 修正用の worktree: `/workspaces/reso-world/.worktrees/issue-166-test-git-env-isolation`（PR の head ブランチを checkout 済みで、未コミットの変更が無く HEAD が PR の head と同じだったので、そのまま使った。作ったのはこのセッションではないので片付けない）
- 関連: 実装の Spec `docs/superpowers/specs/2026-10-20-create-reso-world-issue166-test-git-env-isolation-design.md`、Plan `docs/superpowers/plans/2026-10-20-create-reso-world-issue166-test-git-env-isolation.md`

## レビュアーの構成

4 名が、現行 HEAD を対象にレビューした（2026-10-19 17:42Z に並行で開始、どれも Initial）。

| レビューファイル | モデル（ランタイム） | レビュー HEAD | Mode | 再実行 | Merge recommendation |
| --- | --- | --- | --- | --- | --- |
| `claude-opus-5-5.md` | claude-opus-5-5（claude-code） | `6cf7096aaaa6` | Initial | はい | Approve |
| `gpt-6.1-sol.md` | gpt-6.1-sol（pi） | `6cf7096aaaa6` | Initial | はい | Approve |
| `Grok-4.7.md` | Grok 4.7（cursor） | `6cf7096aaaa6` | Initial | はい | Approve |
| `SWE-2-Max.md` | SWE-2 Max（devin） | `6cf7096aaaa6` | Initial | はい | Approve |

- 入力から外したファイルは無い。`findings/`（候補一覧）・`runs/`（実行記録）はレビュアーではない。4 件の候補一覧は `review_findings.py validate` と、レビューファイルとの `check-pair` に通った
- 前のサイクルの判断の記録は無い（1 回目。PR のコメントは 0 件）

## 全指摘と分類

分類: 解消済み 0 / 対応する 0 / 対応しない 0（指摘は 0 件）

- 4 名とも、Critical〜Info の指摘も Unverified candidates も 0 件だった。判断の記録の `decisions` は空になる
- PR が持ち込んだ致命的な欠陥は、確認の中でも見つからなかった（自己確認の指摘なし）

## 確認の範囲

- PR の全体差分（`8f5074a..6cf7096`、8 ファイル・追加 438 行・削除 2 行）と、変更ファイルの全文（実装の Spec・Plan を含む）。PR 本文、Issue #166 の本文とコメント 2 件
- ルートの `conftest.py` の autouse fixture が効く範囲: `pyproject.toml` の pytest の設定（`testpaths`・`addopts`）、リポジトリの全 `conftest.py` と `tools/test_support/plugin.py`（autouse にしない）、scope の広い fixture（`review-verify/tests/test_dispatch.py:444`・`tests/scripts/test_meshy_conversion.py:36,47` の module scope。どれも git を使わない）、pytest の hook（無い）。`os.environ` に `GIT_` で始まる変数を書くテストのコードは無い（`FAKE_GIT_*` は `GIT_` で始まらないので除かれない）
- base の進み（`8f5074a..b65ef0c`、37 ファイル）で増えたテスト（`.agents/skills/pr-review-fix-loop/tests/` など）も、`GIT_*` の扱いを確かめた。新しい conftest の fixture はどれも function scope で、`GIT_` で始まる変数を `os.environ` に置かない。合わせた結果は下の merge したツリーの pytest 全体で確かめた
- unittest の 2 本: すべての `subprocess` の呼び出しが `env=self.env` を渡す。`tests/scripts` で git を使う unittest はこの 2 本だけ
- bash: `run-tests.bash` は `set -uo pipefail`（`-e` 無し）で、`compgen` の結果をプロセス置換で読むので、`GIT_*` が 1 つも無くても止まらない。`scripts/check-layout.sh` の git は `rev-parse`・`ls-files`・`hash-object`（`-w` 無し）の読み取りだけで、#166 の書き換えの経路ではない
- レビュアーが確かめなかった範囲は、確認済みの一覧の `coverage` で閉じた（下の「実行した検証と結果」）
- 確かめた上で指摘にしなかった点（PR の既知の制限に書いてあり、レビュアーも同じ判断）:
  - bash のテストを 1 本ずつ直接実行すると `GIT_*` を除かない。入口の `run-tests.bash` からは除く（実装の Spec D-166-5。`.devcontainer/README.md` も 1 本だけの実行をランナー経由で案内している）
  - ルートの fixture は function scope なので、scope の広い fixture と収集時のコードには効かない。今は git を使うものが無い（merge したツリーでも同じ）
  - `compgen` は progcomp 付きの bash を前提にする。Dev Container の bash で動く

## 結論

結論 2（修正不要としてマージ）。

- 検証: 下の「実行した検証と結果」
- base: `origin/main`（`b65ef0c`）は PR の分岐点より先に進んでいるので、head に base を merge した一時的なツリー（競合なし）でも同じ検証を通した。この merge は push しない
- CI: create-reso-world は private で CI を止めているため確かめない（`AGENTS.md`）
- マージしてよい範囲: `usaturn/create-reso-world` の open で draft でない PR
- 自己レビュー: 修正が無いので行わない
- PR の説明の既知の制限: 「対応しない」の指摘が無いので書き足さない
- 最終化: この Spec だけの commit を PR の head に載せ、状況コメント（判断の記録 `no_fix_needed`）を投稿してから push し、`finalize.py --spec-commit` でマージと closing Issue（#166）の更新を行う

## 実行した検証と結果

- 修正用の worktree（PR の head `6cf7096aaaa61b3a02bf65e448022ef37eb7deea`。2026-10-20 01:24:32–01:30:08Z）
  - `bash .devcontainer/run-tests.bash`: 33 本 PASS（終了コード 0）
  - `bash scripts/check-layout.sh`: PASS（0）
  - `uv run --locked pytest -q tools/agent_runner/tests/test_git_isolation.py tools/agent_runner/tests/test_workspace.py .agents/scripts/tests/test_agent_tmp.py`: 70 passed（0）
  - 検証の後も worktree に未コミットの変更は無く、PR の head は `6cf7096` のまま（OPEN・draft でない・MERGEABLE）
- head に最新の base を merge した一時的なツリー（`6cf7096` に `b65ef0c` を merge した commit `23faa02`。競合なし。`tmp/agents/` のセッションの中に `mktemp` で作った隔離 worktree で、`/tmp` の DSH の隔離の影響を避けた。push していない。検証の後に外して消した）
  - `uv run --locked pytest -q tests/skills .agents/skills .agents/scripts tools`: 3396 passed・失敗 0（終了コード 0、01:24:28–01:46:27Z）。ルートの `conftest.py` の autouse fixture は全テストに効くので、base で増えたテスト（`pr-review-fix-loop` など）との組み合わせもこれで確かめた
  - `bash .devcontainer/run-tests.bash`: 33 本 PASS（0、01:30:20–01:37:52Z）
  - `bash scripts/check-layout.sh`: PASS（0）
- ガードを外した対照: `6cf7096` を `git archive` で展開した写しからルートの `conftest.py` だけを消すと、`tools/agent_runner/tests/test_git_isolation.py` が 1 failed（内側の pytest が失敗）、戻すと 2 passed。写しは確認後に消した
- PR head だけの pytest 全体は再実行していない。PR 本文の記録（3216 passed）を使った。その後の commit（`016bd3c`・`6cf7096`）は `test-run-tests.bash` と文書だけの変更で、pytest の結果に影響しない。マージする組み合わせ（head ＋最新の base）は上で全体を実行した
- 実行していない検証: bash のテストの 1 本ずつの直接実行・`worlds/` と `external/` の pytest・progcomp の無い bash は、PR の既知の制限か実装の Spec の範囲外（確認済みの一覧の `coverage.remaining`）
- この Spec だけの commit は、上の検証の後に PR の head に載せる（検証した head の直接の子で、変更はこの 1 ファイルだけ）

## 作業時間（この Spec の commit まで）

| 工程 | 時刻（2026-10-20 UTC） | 時間 |
| --- | --- | --- |
| 入力・判断の記録・PR の head の固定・修正用の worktree の確認（開始の時刻は記録していない） | 〜01:24 | 計測なし |
| 確認済みの一覧（review-verify。変更ファイルと関連する処理の精読、ガードを外した対照を含む）と結論 2 の検証（並行） | 01:24:11–01:47:00 | 約 23 分 |
| Spec の仕上げと commit | 01:47– | 約 3 分 |

投稿・push・最終化（マージと #166 の close）の結果は、状況コメントと完了の報告に書く。
