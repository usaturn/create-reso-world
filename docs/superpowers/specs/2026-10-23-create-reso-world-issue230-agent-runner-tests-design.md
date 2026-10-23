# Issue #230: tools/agent_runner のテストを、新しい採用基準で減らす

## 管理・実行許可

- 文書管理・コード対象: `usaturn/create-reso-world`。対象 Issue: https://github.com/usaturn/create-reso-world/issues/230（親 #228、ボード `test-reduction-board`、子のキー `agent-runner-tests`。先行 #229 は completed、PR #240 は `main` にマージ済み）
- 状態: draft
- 関連 Plan: `docs/superpowers/plans/2026-10-23-create-reso-world-issue230-agent-runner-tests.md`
- DOC_ROOT・CODE_ROOT: `/workspaces/reso-world/.worktrees/issue-230-agent-runner-tests`（branch `feat/issue-230-agent-runner-tests`）。PARENT_ROOT: `/workspaces/reso-world`
- 実行許可: 2026-10-23（UTC 08:00 ごろ）、利用者の指示を写した司令塔（Herdr ペイン w1:pD）が、このセッションに次のとおり送った

  ```text
  /issue-to-pr https://github.com/usaturn/create-reso-world/issues/230 --merge --assign implement=self 利用者の決定を /workspaces/reso-world/tmp/agents/commander-230-231-233-236.z9emizj5/decisions/issue-230.md に置いた。読んで Spec の決定記録に引用せよ
  ```

  issue-to-pr の委任により、通常の設計判断を推奨案で決め、Spec・Plan の commit、実装、検証、push の前の検査、push、PR の作成（`Closes #230`）まで行い、`--merge` により PR 修正ループ（pr-review-fix-loop）を回して、修正不要と確かめられたらループの `finalize.py` がマージと関連 Issue の更新を行う。Issue の「マージは利用者が行う（利用者が明示した指示がある場合を除く）」は、この `--merge` を明示の指示として扱う
  - 方針は #228 の「利用者の決定（2026-10-21）」と「削除と採用の基準」に従い、議論し直さない。ほかの判断は、利用者に確認を取らずに決めたエージェントの判断であり、内容の承認（`approved`）ではない
- 利用者の決定（#230）: 下の「利用者の決定の写し」に全文を引用した（決定記録の D-230-U1〜U9 として扱う）
- ループのオプション（`loop.py check-options` の出力）: `max_cycles = 3`（既定の適用）、`assign = {implement: ["self"]}`（利用者の指定 `--assign implement=self`）、`template = .devcontainer/agent-runner.toml`・`config = null`（既定の適用）。割り当ては、レビュー（`inspect`）が `pi-gpt`・`devin-swe`・`pi-deepseek`・`cursor-grok47`（設定のとおり）、修正（`implement`）が `self`（利用者の指定）、自己レビュー（`self-review`）・修正の確認（`fix-check`）が `self`（設定のとおり）。いずれも `fallback` なし
- 実装の担当: `implement_task.py check` は `assignment.agents = ["self"]`・`fallback = []`・`self: true`（雛形 `.devcontainer/agent-runner.toml` の `[workflows.issue.assignments.implement]` の既定の適用。個人設定 `/home/vscode/.config/agent-runner/config.toml` の該当の節は注釈だけで、利用者の指定ではない）
- 予約: `refs/heads/agent-claims/issue-230` = `3fd22c42dc7d4fee9e627f548756b9798501bf22`（https://github.com/usaturn/create-reso-world/issues/230#issuecomment-6360363809）
- 基準: `origin/main` の `7a8e4b7`（PR #245 のマージ）

### 利用者の決定の写し

出どころ: `/workspaces/reso-world/tmp/agents/commander-230-231-233-236.z9emizj5/decisions/issue-230.md`（SHA-256 `316342a79b2bda74d78dbecece7a309a404aa25a4c2e5ef3cbf831c1bc2afc70`。司令塔が利用者の指示（2026-10-23）から写したもの。#230 固有の節は無く、共通の節だけが当たる）

> ### 共通（#230・#231・#233）
> - #228 の「利用者の決定」と「削除と採用の基準」は議論し直さない
> - F・L・D として消す前に、守る処理の条件の各部分・設定の値を 1 つずつ外した変異（単一行の if、複合条件の各条件、文、一覧の要素の削除）を、mktemp -d で作った使い捨てのコピーに当てる。base のテストが検出し、削減後のテストが検出しない変異があれば、その守りの代表を残す。理由の文だけで D・L と決めない（#232・#235 では、S の最後の代表を消したという指摘がサイクルごとに続いた）
> - 変異の走査には、tmp/agents/pr-review-scratch-246.xol_okfd/ の道具を自分の領域に写して使ってよい（元は変えない）
> - 迷ったものは消さずに、棚卸しの表に「迷い」の印を付ける。行数が 1/3 に届かなくても S は消さない（#236 の一覧を見て利用者が決める）
> - pytest の --basetemp は作業ツリーの外に置く
> - 撤去する経路の呼び出し元は、リポジトリの中と external/resoloop・external/resoloop-meshy の checkout で確かめる（読むだけ）。確かめられない場所は Spec に書く
> - 実行予算の 100% では、今の規則どおり止まって報告する。司令塔から延長の指示が来たら、利用者の事前の許可による 1 回の延長として Spec の決定記録に書いて続ける
> - #236 への申し送りは、自分の子 Issue の完了コメントに「#236 への申し送り」の見出しで書く
> - PR #245（#235）、その worktree・/tmp/pr-review-245-*、ペイン w1:pB には触らない

## 意図

`tools/agent_runner` のテスト（`tools/agent_runner/tests/` のテスト本体・`conftest.py`・偽の CLI・launcher・`ptc_tool_results.json`）を、`AGENTS.md` の「テストの採用基準」（#229、PR #240）の分類で 1 つずつ見直し、S（F∩S を含む）と D の代表だけにする。消すのは、F（F∩S を除く）・L・D の余りと、それだけが使っていた fixture・偽の CLI・補助である。消す前に、守りのコードを 1 か所ずつ外した変異で、消す側のテストだけが検出していた守りが無いことを確かめる（利用者の決定の 2 つ目）。

## 範囲

- 変える: `tools/agent_runner/tests/` の全て、この子の Spec・Plan。`tools/agent_runner/` のコードと `interfaces.rst`・`README.md`・`.devcontainer/README.md`・`docs/` は、使われなくなった経路を撤去するときだけ（下の「撤去」）
- 変えない: Issue の「変えないもの」のとおり（`tools/test_support/`・ルートの `conftest.py`・`pyproject.toml`・`.devcontainer/run-tests.bash`・`README.md` の「テスト」・`.devcontainer/agent-runner.toml`・`.devcontainer/agent-runner-personal.toml`・ほかの領域のテストとコード・`AGENTS.md`）
- `tools.agent_runner` の公開の API は変えない（撤去の経路の呼び出し元が無いと確かめた場合を除く）

## 計測

<!-- 計測の表（後で書く） -->

## 決定記録

利用者の決定（「利用者の決定の写し」）は、上から順に D-230-U1〜U9 と呼ぶ。下の表は、利用者に確認を取らずに決めたエージェントの判断である。

| ID | 選択した案 | 検討した別案 | 選択理由 | 委任指示または停止条件 |
| --- | --- | --- | --- | --- |
| D-230-1 | 分類の単位は関数、parametrize はケース。棚卸しは、テストのファイルの組ごとに 6 つのサブエージェントが読むだけで分類し、controller が結合して、基準の 1,064 件がちょうど 1 回ずつ分類されたことを確かめた | controller が全て読む | 10,404 行を並行で読み、判断の確かさは監査（D-230-3）で確かめる | issue-to-pr の委任（推奨案で進める） |
| D-230-2 | D の代表は、守りを実装するモジュールのテストに置く。別の担当が消したテストを代表に挙げていた D は、同じ関数の残るケースに代表を付け替え、残るケースが無いものは監査の結果（その守りの変異を検出した残すテスト）で付け替えた | 代表を挙げ直さない | #228 の「層をまたぐ重複」。#232・#235 で、消したテストを代表にした D がレビューで指摘された | #228 の基準 |
| D-230-3 | 消す前に、守りのコードの変異（条件・複合条件の各項・文・一覧の要素・定数）を使い捨てのコピーに当て、基準が検出し残すテストが検出しない変異（lost）を全て判定した（下の「変異の監査」） | #232 の道具のまま単一行の if だけ | D-230-U2（条件の各部分・文・一覧の要素） | D-230-U2・U3 |
| D-230-4 | lost の判定の原則: 基準が失敗・拒否・停止とする場面で、エラーにならずに成功・受理・続行させる変異、記録（identity・skill_versions・監査・sensitive_paths・stop_confirmed・payload）を黙って誤らせる変異、秘密情報を残す変異は S とし、検出していた消す側のテストを戻す。例外・失敗の状態・メッセージ付きの非 0 の終了で見えるもの、失敗の種類だけが変わるもの、成功が失敗になる向きのものは L とし、見える経路をコードの行で書く。決められないものは迷いとして戻す | L も戻す／棚卸しの分類に合わせる | `AGENTS.md` の L のただし書きと D-230-U2・U4。判定は変異ごとに行い、棚卸しの L・D の判断の誤りを見つけることを目的にした | D-230-U2・U4 |
| D-230-5 | 変異のテストは PID 名前空間の中で実行する | 危険な変異（`_Tree` の 4 つ）を除く | 除くと演算子の網羅が欠け、ほかの経路の見落としも防げない。名前空間なら、変異がどう広がってもテストの外のプロセスに届かないことを見張りで確かめられる | 安全（`.agents/execution-budget.md` の安全の失敗を起こさない） |
| D-230-6 | 名前空間の中で変異なしでも失敗する `test_native_process_has_private_tmp_and_readonly_attempt_metadata` は監査の実行から外し、S として残す | 名前空間を使わない | D-230-5 を優先した。この 1 件は棚卸しで S（DSH の柵）なので残す | — |
| D-230-7 | `tools/agent_runner/adapters/__init__.py` の `runtime_supported` を撤去する（下の「撤去」） | 残す | #228 の決定 5。呼び出し元が無いと確かめた | #228 の決定 5 |
| D-230-8 | `workspace.py` の `changed_checkouts` と、`audit_checkouts` の素の dict の受け付けは撤去しない | 撤去して、残すテストの判定を `audit_checkouts` に書き換える | 呼び出し元は残す S のテスト（`test_workspace.py` の 15 か所。checkout の監査の守り）で、撤去すると残す S のテストを書き換える。撤去で減るのは 3 行 | #228 の決定 6（子は基準に当てはまるテストを消すだけ） |
| D-230-9 | 新しいテストは書かない。残すテストの中身は変えず、消したテストだけが使っていた import・補助・fixture・偽の CLI の場面・`ptc_tool_results.json` の項目を消す。parametrize のケースを減らすときは値の一覧から外し、重ねた parametrize は残すケースだけの 1 つの parametrize（元の node ID を `ids` に写す）に書き換える | 重ねた parametrize のケースは全て残す | 残すケースの値・ID を変えずに、消すケースだけを外せる | #228 の決定 6 |
| D-230-10 | fixture の params（`supervisor_bootstrap` の posix_spawn・popen）で分かれるケースは、片方だけを残せないので、残すケースの両方の起動の経路を残す（2 件増える）。fixture の引数 `startup`（消したテストだけが使っていた）は、残すテストの型注釈まで変わるので整理しない | fixture を書き換える | 残すテストの形を変えない | — |
| D-230-11 | 行数のための fixture の共通化（git の repository の写し、Devin の export のよく似たテスト）はこの子では行わず、#236 に申し送る | この子で共通化する | #228 の決定 6（子は基準に当てはまるテストを消すだけ）。共通化は残す S のテストの準備を変える | #228 の決定 6 |
| D-230-12 | 監査の走査は 3 回方法を変えた（記録は ledger）: (1) 基準の順の事前の走査が遅いので、速い順・完了順の書き込みにした、(2) 安全のため PID 名前空間に変えた（D-230-5）、(3) 止まるテストに 1 件 30 秒の上限（SIGALRM。止まったテストが検出したと数える）を付けた | 同じ方法で続ける | 予算（`.agents/execution-budget.md` の方法変更）。(3) は変異なしの全件の実行で誤検出が無いことを確かめた | 実行予算 |
| D-230-13 | 実行予算の 100% では止まって報告する。延長は、利用者（司令塔は 10:12Z に終了し、このペインは利用者が管理する）の指示がある場合の 1 回だけとし、そのときはこの表に記録する | 自分で延長する | D-230-U7 | D-230-U7 |

## 変異の監査（利用者の決定の 2 つ目）

テストを消す前に、守りのコードを 1 か所ずつ外した変異で、基準のテスト（`7a8e4b7` の 1,064 件）が検出し、残すテスト（棚卸しの「残す」）が検出しない変異（lost）を洗い出した。道具と記録は `/workspaces/reso-world/tmp/agents/issue-230.fuotebjq/audit/`（コミットしない。#232 の `tmp/agents/pr-review-scratch-246.xol_okfd/` の道具を写して作り直した。元は変えていない）。

### 方法

- 対象: `tools/agent_runner/` のコード 24 ファイル（`tests/` と `__main__.py` を除く）
- 変異の演算子: if・while・三項の条件を `False`（`cond_false`）、内包の条件と assert を `True`（`comp_if_true`・`assert_true`）、and・or の項を 1 つずつ外す（`boolop_drop`）、関数の中の文を `pass` にする（`stmt_del`。定義・import・docstring を除く）、リスト・タプル・集合の要素と定数のキーの dict の要素を 1 つずつ外す（`elt_del`）、モジュール・クラスの定数を変える（`const_mod`）。AST の位置で元のソースの 1 か所だけを置き換え、コメントとほかの行は変えない。構文の誤りになるものは除いた
- 生成した 3,421 個から、結果の変わらない 18 個（`tools/agent_runner/__init__.py` の `__all__` の要素。`import *` はリポジトリと external の 2 つの checkout に無い）と、`else` の無い `if` の文の削除 387 個（条件を `False` にする変異と同じ）を除いた 3,016 個を実行した
- テストの選び方: 基準の木で coverage 7.17.0（一時の環境、`core = ctrace`）を動かし、テストごとに実行した行を記録した。`python -m tools.agent_runner` などの子の Python も、`sitecustomize.py` と `COVERAGE_PROCESS_START` で同じテストの名前を付けて計測した。読み込み時に評価される行（モジュール・クラスの定数、関数の既定値）は、その名前を読む行のテストを使い、クラスの本文などは全てのテストを使った。環境を差し替えた子のプロセスで動くため計測できない 7 件のうち、agent_runner のコードを動かす 6 件（`test_review_regressions.py` の literal env の 4 件、`adapters/dsh/test_sandbox.py` の 2 件）は、対象のモジュールの全ての変異に足した。`_supervisor.py`（`-I -S` で起動される）の変異には、`process.py` の起動の行を通るテストを使った
- 判定: 変異ごとに、使い捨てのコピー（`/tmp` に `tempfile.mkdtemp`）を作り、通るテストを「残すテスト（速い順）→ 消すテスト（速い順）」の順に `pytest -x` で実行した。最初に失敗したテストが残す側なら「残すテストが検出」、消す側なら lost（残すテストは全て通った）、どれも失敗しなければ基準も検出しない変異である。事前の走査（同じテストを速い順に実行）で基準が検出しないと分かった 339 個は、本走査から除いた
- 安全: `process.py` の `_Tree` の変異（例 m02748: 子孫の判定から `entry.parent in parents` を外す）は、テストが利用者の全てのプロセスに SIGTERM・SIGKILL を送り得る（棚卸しの担当の指摘。事前の走査では実行前に止めた）。そのため、変異のテストは PID 名前空間（`unshare --user --map-current-user --pid --fork --kill-child --mount-proc`）の中で実行し、テストから見える・届くプロセスをその中だけにした。外に置いた見張りのプロセス（`sleep`）が m02748 の実行の後も生きていることを確かめた。名前空間の中では、DSH の `test_native_process_has_private_tmp_and_readonly_attempt_metadata` だけが変異なしでも失敗する（`/proc` の見え方の違い。PID を 3,000 まで進めても同じ）ので、この 1 件は監査の実行から外し、棚卸しでは S として残した
- 並列: 6〜7 本。並列の負荷で変異なしのテストが落ちないことを、変異なしの全件の実行 6 本の同時実行（各 1,064 件通過）と、名前空間の中の変異なしの実行（1,063 件通過）で確かめた

### 限界

- 変異の演算子は上のものに限る（定数の値の書き換えは、モジュール・クラスの定数だけ）。pydantic の `Field(min_length=1)` のようなキーワード引数の値は外していない
- 同じ変異を検出するテストのうち、最初に失敗した 1 件だけを記録した。lost の変異に戻すテストは、その 1 件（消す側で最も速いもの）である

## 撤去（#228 の決定 5）

| 撤去したもの | 使われていないと判断した根拠 |
| --- | --- |
| `tools/agent_runner/adapters/__init__.py` の `runtime_supported`（check・list の補助として #149 で入れた関数） | worktree の `git grep -n runtime_supported` で、コードからの呼び出し元が無い（CLI の check・list は `cli.py` の `_inventory` で `load_adapter` を直接呼ぶ）。参照は消したテスト 3 か所（`test_cli.py`・`test_config.py`・`adapters/dsh/test_adapter.py`、どれも L）と、#149 の過去の Spec・Plan（`docs/superpowers/specs/2026-10-18-create-reso-world-issue149-agent-runner-core-design.md:35`、`docs/superpowers/plans/2026-10-18-create-reso-world-issue149-agent-runner-core.md:88`。完了した記録なので変えない）だけ。`tools/agent_runner/__init__.py` の `__all__` と `interfaces.rst` に無い。`external/resoloop`（`39db994`）・`external/resoloop-meshy`（`1b64663`）の `git grep -n 'agent_runner\|agent-runner'` は 0 件 |

撤去しなかったもの（D-230-8）: `workspace.py` の `changed_checkouts`（呼び出し元は残す S のテストだけ）と、`audit_checkouts` の素の dict の受け付け。どちらも撤去すると残す S のテストを書き換える。`interfaces.rst`・`README.md`・`.devcontainer/README.md`・`docs/` には `runtime_supported` を説明する行が無いので、変えていない。
