# Issue #238: loop の `git_unavailable` のテストを、一時ディレクトリの場所に依らず通す

- 状態: draft
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
4. Issue の案（`GIT_CEILING_DIRECTORIES` を tmp_path に設定する）は効かない。`loop.git_output` は `review_target.git_environment()` で `GIT_*` をすべて除いた環境で git を起動するので、テストで設定した値が git に届かない。pytest のプロセス全体に `GIT_CEILING_DIRECTORIES=<basetemp>` を設定しても 1 failed のままだった。前例の `.agents/skills/issue-to-pr/tests/test_resolve_issue.py:56` は、helper（`resolve_issue.py`）が環境をそのまま引き継ぐので効く。`.agents/scripts/tests/test_agent_tmp.py:75` の前例は、#232 の削減（`2f00d4d`）で無くなっている
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

| 経路 | 判定 | 観測する結果 | 確かめる方法 |
| --- | --- | --- | --- |
| 対象のテスト | 修正する | 作業ツリーの中で、変更前は 1 failed、変更後は 1 passed。外では変更前後とも 1 passed | Issue の再現コマンドを、`tmp/agents/` の下と `mktemp -d` の下で実行する |
| 守る性質（Git の照合の失敗で回収済みにしない） | 修正する（保つ） | 変異を入れたコピーで、内・外とも 1 failed | 使い捨てのコピーで、`cleanup_output` の `except LoopError` を「登録なし」に変える |
| 親の checkout | 既に満たす | 実行の前後で HEAD・refs・worktree・status・stash が同じ | 前後の写しを比べる |
| pr-review-fix-loop のほかのテスト | 既に満たす（確かめる） | 外側のリポジトリの中の basetemp で、変更前は対象の 1 件だけが落ち、変更後は全部通る | 使い捨ての外側のリポジトリの中に basetemp を置いて、テスト全体を実行する |
| `loop.py`・`git_environment()`・ほかのスキルのテスト | 対象外 | — | 「対象外」の理由 |
