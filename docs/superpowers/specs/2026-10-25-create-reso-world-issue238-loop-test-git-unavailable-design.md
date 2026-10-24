# Issue #238: loop の `git_unavailable` のテストを、一時ディレクトリの場所に依らず通す

- 状態: completed（PR #257 のサイクル 1 で修正不要と判断した。末尾の「PR #257 のレビュー修正（サイクル 1）」）
- 文書管理リポジトリ: `usaturn/create-reso-world`（`docs/superpowers/`）
- 対象: `usaturn/create-reso-world` / [Issue #238](https://github.com/usaturn/create-reso-world/issues/238)
- 検証したコードの HEAD: `origin/main` `bdbe02b1bfdc8e884dfb836fc1083cd0cf3ae858`（2026-10-24T15:47Z の着手時）
- 関連 Plan: `docs/superpowers/plans/2026-10-25-create-reso-world-issue238-loop-test-git-unavailable.md`
- 関連: #221・PR #226（発見の経緯）、#231・PR #255（このテストを 1 件に縮約した）、#228（テストの採用基準のボード）
- 実行許可: 利用者の `/issue-to-pr #238 --merge`。通常の設計判断を推奨案で決め、実装・検証・commit・push・PR の作成と、PR 修正ループ、その結論に従う `finalize.py` のマージまでを許可する。本 Spec の内容の承認（`approved`）ではない

## 目的

`.agents/skills/pr-review-fix-loop/tests/test_loop_review.py` の `test_missing_output_checks_fail_closed` を、pytest の一時ディレクトリ（`--basetemp`）が Git の作業ツリーの中にあっても通るようにする。`AGENTS.md` は検証ログの置き場所に `tmp/agents/<topic>.XXXXXX/` を挙げており、担当がそこに basetemp を置くと、このテストが環境のせいで落ちる。PR #226 のループでは、レビュアーが環境の違いと見分けるのに手間をかけた。

テストが守る性質は変えない。記録した出力ディレクトリが無く、Git の登録（`git worktree list`）を照合できないときは、資源を回収済み（`removed`）にせず、停止を確認できない資源として返す（#231 の分類では S・高）。

## 着手時の確認

1. #231（PR #255、`bdbe02b`）が、このテストを Issue 作成時の 6 件から `[git_unavailable-audit]` の 1 件に縮約した。ほかの 5 件は、同じ失敗時停止の重複（D）として消された
2. 着手時の main で再現した。basetemp が `/workspaces/reso-world/tmp/agents/issue-238.webd39ls/t-inside` なら 1 failed（`assert [] == ['…/protected/create-reso-world-pr-loop-owned']`）、`mktemp -d` の下なら 1 passed
3. 原因: テストは fixture の tool root（`env.parent`）の `.git` を改名して、Git を使えない状態を作る。`.git` が無いと git は上の階層をたどるので、tmp_path が外側の作業ツリーの中にあると、外側のリポジトリの `git worktree list` が成功する。`cleanup_output` は登録が無いと判断して `removed` にし、`audit_resources` は空のリストを返す。外側のリポジトリは読むだけで、変更しない
4. Issue の案（`GIT_CEILING_DIRECTORIES` を tmp_path に設定する）は効かない。`loop.git_output` は `review_target.git_environment()` で `GIT_*` をすべて除いた環境で git を起動するので、テストで設定した値が git に届かない。変更前の版のコピーで、テストの中で `monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))` を設定しても、作業ツリーの中の basetemp では 1 failed のままだった。同じコピーで `git_environment()` がこの変数を残すように変えると 1 passed になったので、除いているのはこの関数である。なお、pytest のプロセス全体に設定した `GIT_*` は、ルートの `conftest.py` の autouse fixture（#166）がテストの前に除くので、それだけでは根拠にならない。前例の `.agents/skills/issue-to-pr/tests/test_resolve_issue.py:56` は、helper（`resolve_issue.py`）が環境をそのまま引き継ぐので効く。`.agents/scripts/tests/test_agent_tmp.py:75` の前例は、#232 の削減（`2f00d4d`）で無くなっている
5. git 2.55.0 で、外側のリポジトリの中に置いた一時リポジトリの `.git` を変えて `git worktree list` を実行した。改名（`.git` が無い）と空のディレクトリは、外側のリポジトリを見つけて終了コード 0 になる。`gitdir: <存在しないパス>` の gitfile と、形式の壊れたファイルは、その階層で `fatal: …` を出して終了コード 128 になり、上の階層をたどらない

## 変更の内容

`git_unavailable` の場合に、`.git` を退けた跡へ、存在しないパスを指す gitfile（`gitdir: <tmp_path>/absent-gitdir`）を置く。git はその gitfile で失敗するので、tmp_path の場所に依らず Git を使えない状態になる。後始末（`finally`）では、gitfile を消してから `.git` を戻す。外側のリポジトリをたどること、`GIT_CEILING_DIRECTORIES` が届かないことを、コメントに短く書く。

変えるのは `test_loop_review.py` の `test_missing_output_checks_fail_closed` だけである。

## 対象外

- `loop.py`（`git_output`・`_registered_worktrees`・`cleanup_output`・`audit_resources`）の動作。実際の tool root は自分の `.git` を持つ create-reso-world の checkout で、`.git` が無いまま外側のリポジトリをたどる状況は起きない。Issue の対象は、テストの誤った失敗である
- `review_target.git_environment()`。`GIT_*` を除くのは、呼び出し側の Git の環境変数で別のリポジトリを読み書きしないための隔離（`AGENTS.md` の S の「環境の隔離（`GIT_*`・`HOME`）」）で、テストの都合で緩めない
- #231 が消したパラメータ（`cleanup`・`inaccessible`・`dangling`）の復元。テスト本体に残る `inaccessible`・`dangling` の分岐は #231 の縮約の結果で、今回は触らない
- conftest の fixture と、ほかのテスト。`.git` を操作するほかのテスト（`.agents/skills/pr-review/tests/test_port_routing.py` の `git-replacement`・`git-symlink`）は、退けた直後に `.git` を作り直すので、上の階層をたどらない
- 新しいテスト（決定記録の D3）

## 受け入れ条件

1. `--basetemp` を親の checkout の作業ツリーの中（`tmp/agents/` の下）にしても、`test_missing_output_checks_fail_closed` の全ケースが通る。現行のケースは `[git_unavailable-audit]` の 1 件である（D2）
2. 外側のリポジトリ（親の checkout）を変更しない
3. 作業ツリーの外の basetemp でも、引き続き通る
4. テストが守る性質を保つ。`cleanup_output` が Git の照合の失敗を「登録なし」として扱う変異を入れると、作業ツリーの内・外のどちらの basetemp でも、このテストが落ちる

## 決定記録

| ID | 選択した案 | 検討した別案 | 選択理由 | 委任指示または停止条件 |
| --- | --- | --- | --- | --- |
| D1 | `.git` を退けた跡に、存在しないパスを指す gitfile を置く | (a) Issue の案の `GIT_CEILING_DIRECTORIES`（テスト・fixture・pytest のプロセスのどこで設定しても同じ）。(b) PATH の先頭に、失敗する偽の git を置く。(c) tmp_path に、上の階層の探索を止める壊れた `.git` を置く。(d) `loop.py` で、見つかったリポジトリが tool root かを照合する。(e) `git_environment()` で `GIT_CEILING_DIRECTORIES` を残す | (a) は `git_environment()` が除くので効かない（着手時の確認 4）。(b) は以降の git をすべて偽物にし、tool root の Git が壊れた状態から遠い。(c) は 2 か所を操作するので意図が読みにくい。(d)(e) は実際の動作と共有の環境の隔離を変え、Issue の対象（テストの誤った失敗）を超える。実際の tool root では起きない状況のための変更にもなる。gitfile なら git はその階層で失敗し（着手時の確認 5）、変更が 1 か所に収まる | 委任: `/issue-to-pr #238 --merge` の推奨案での決定 |
| D2 | 受け入れ条件 1 の件数を、Issue の「6 件」から現行の全ケース（1 件）に読み替える。消えた 5 件は戻さない | 6 件を戻して通す | #231 が #228 の基準（D は代表の 1 件にする）で縮約した。戻すと #228・#231 の決定に反する。条件の意図（basetemp の場所に依らず通る）は変わらない | 完了条件の件数の変更（`.agents/execution-budget.md` の「完了条件を変える縮小」）として、ここに記録する。委任: 推奨案での決定 |
| D3 | テストを足さない | basetemp を作業ツリーの中に置く回帰のテストを足す | 今回の不具合は、テストが誤って落ちる形で現れる（`AGENTS.md` の L）。足すと、外側のリポジトリを作る fixture が増える（書きすぎ）。テストが守る性質は、受け入れ条件 4 の変異で確かめる | `AGENTS.md` の「テストの採用基準」 |
| D4 | 親の checkout の作業ツリーの中で実行するのは、対象のテストだけにする。テスト全体を作業ツリーの中で試すときは、使い捨ての外側のリポジトリの中に basetemp を置く | 親の checkout の `tmp/agents/` の下で、テスト全体を実行する | 対象のテストは、外側のリポジトリを読むだけと確かめた（着手時の確認 3）。ほかのテストは、外側のリポジトリをたどったときに書き込まないとは確かめていない | 受け入れ条件 2 |
| D5 | `--merge` のループは `check-options` の結果のままにする。サイクルの上限 3、雛形 `.devcontainer/agent-runner.toml`、`--config` なし。inspect は `pi-gpt`・`devin-swe`・`pi-deepseek`・`cursor-grok47`、修正は `claude-opus`、自己レビューと fix-check は `self` | ループ用のオプションを足す | 利用者が書いたのは `--merge` だけで、ループ用のオプションは無い。どれも雛形と個人設定の既定の適用で、利用者の指定ではない | 委任: `/issue-to-pr #238 --merge`。`check-options` は終了コード 0 |
| D6 | Plan の Task の担当は `self` にする | 別の担当に依頼する | `implement_task.py check` は `agents: [self]`、`fallback: []`、`self: true`。雛形の既定の適用で、利用者は `--implement` を書いていない | 委任: `/issue-to-pr #238 --merge`。`check` は終了コード 0 |

## 経路表

観測した結果は、Task 1 の commit `9e97f11` に対するものである（変更前は `7a72d9e`・`bdbe02b` で、コードは同じ）。

| 経路 | 判定 | 観測した結果 | 確かめた方法 |
| --- | --- | --- | --- |
| 対象のテスト | 修正した | 作業ツリーの中（`tmp/agents/` の下の basetemp）: 変更前は 1 failed（`assert [] == [...]`）、変更後は 1 passed。`mktemp -d` の下: 変更後も 1 passed。後始末の後、fixture の `.git` はディレクトリに戻る | Issue の再現コマンド |
| 守る性質（Git の照合の失敗で回収済みにしない） | 保った | 対照（変更なし）は内・外とも 1 passed。変異（`cleanup_output` の `except LoopError` の本体を `registrations = []` に置き換える）は、内・外とも 1 failed（`assert [] == [...]`） | `9e97f11` を `git archive` で作業ツリーの外の独立したリポジトリに展開したコピー。内は使い捨ての外側のリポジトリの中の basetemp |
| 親の checkout | 既に満たす | 対象のテストを `tmp/agents/` の下の basetemp で実行した前後で、HEAD・refs・worktree・status・stash・`.git/config` の写しに差が無い | 前後の写しの比較 |
| テスト全体（pr-review-fix-loop を含む） | 既に満たす | 使い捨ての外側のリポジトリの中の basetemp で、変更前は 1 failed（対象だけ）・1223 passed、変更後は 1224 passed。外側のリポジトリは、basetemp のディレクトリが増えたほかは変わらない | `uv run --locked pytest --basetemp <外側のリポジトリ>/… tests/skills .agents/skills .agents/scripts tools` |
| `loop.py`・`git_environment()`・ほかのスキルのテスト | 対象外 | — | 「対象外」の理由 |

## PR #257 のレビュー修正（サイクル 1）

- 実行許可: 利用者の `/issue-to-pr #238 --merge`。issue-to-pr の 5 章のとおり PR 修正ループ（run `a79c749924af42999d62ed93389373cd`）を回し、review-fix-planning の完遂で判断した。結論 2 のマージと関連 Issue の更新は `finalize.py` が行う
- planner: `claude-opus-5-5`（claude-code）。サイクル 1（判断の記録の round 1）で、前のサイクルの記録は無い
- 対象: PR の head `2ff7d38b6507cb51ab0b529ecea1a13105401353`。base `main` の先端は、レビューの後に PR #258 と PR #256 のマージで `095961022c8bef74683aff4c8010bb1d73f7dc4f` に進んだ（merge-base は `bdbe02b`）
- 入力: `reviews/usaturn/create-reso-world/#257-fix-issue-238-loop-test-git-unavailable/` の 4 レビューファイルと `findings/*-2ff7d38b6507.json`。候補 JSON は 4 件とも `validate`・`check-pair` を通った
- 確認済みの一覧: `verified/2ff7d38b6507.json`（review-verify の mode cycle。確認担当は planner 自身）。confirmed 0・not_reproduced 0・unverified 0 で、未確認の範囲は無い。工程の記録は `verified/2ff7d38b6507.planning.json`

| レビューファイル | モデル | ランタイム | 担当 | レビュー HEAD | 今回再実行 | Merge recommendation |
| --- | --- | --- | --- | --- | --- | --- |
| `gpt-6.1-sol.md` | gpt-6.1-sol | pi | pi-gpt | `2ff7d38b6507` | はい | Approve |
| `SWE-2-Max.md` | SWE-2 Max | devin | devin-swe | `2ff7d38b6507` | はい | Approve |
| `deepseek-deepseek-v4.1-flash.md` | deepseek/deepseek-v4.1-flash | pi | pi-deepseek | `2ff7d38b6507` | はい | Approve |
| `Grok-4.7.md` | Grok 4.7 | cursor | cursor-grok47 | `2ff7d38b6507` | はい | Approve |

- 指摘の振り分け: 指摘は 0 件（4 レビュアーとも active findings・Unverified candidates が無い）。解消済み 0 / 対応する 0 / 対応しない 0。「対応する」項目が無いので、守る条件と影響経路の表は作らない
- planner の確認: PR の変更ファイルの全文（テストの関数、この Spec、Plan）、関連する処理（`loop.py` の `git_output`・`_registered_worktrees`・`cleanup_output`・`audit_resources`、`review_target.git_environment()`、ルートの `conftest.py` の autouse fixture、loop のテストの `env` fixture）と、正常側の対のテスト（`test_missing_parent_with_no_registration_is_removed`）を読んだ。`2ff7d38` の隔離 worktree で、対象のテストは basetemp が外側の Git リポジトリの中でも作業ツリーの外でも 1 passed、pr-review-fix-loop のテストは 114 passed。PR の欠陥は見つからなかった
- 結論: 2 修正不要としてマージする
- 検証: head `2ff7d38` に base の新しい先端 `0959610` を一時の隔離 worktree で merge したツリー（競合なし。push しない）で、`bash .devcontainer/run-tests.bash` は終了コード 0（23 test(s) PASS）、`bash scripts/check-layout.sh` は 0、`uv run pytest tests/skills .agents/skills .agents/scripts tools` は 0（1224 passed）。検証した base は `095961022c8bef74683aff4c8010bb1d73f7dc4f`。途中の先端 `6b6fd9a`（PR #258 のマージ）を merge したツリーでも 3 つとも 0 だった（pytest は 1223 passed。1 件の差は PR #258 の devin の adapter のテストの減少）。head だけのツリー（未 commit の変更なし）でも 3 つとも 0（pytest は 1224 passed）
- 自己レビュー: 修正が無い（結論 2）ので行っていない。`run_roles.py` も実行していない
- 所要時間: レビュー 16:37Z〜16:56Z（約 19 分）、確認済みの一覧と計画 16:57Z〜17:25Z ごろ（base が 2 回進み、merge したツリーの検証を 2 回行った）
