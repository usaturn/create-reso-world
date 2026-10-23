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

Issue の「検証」の計測のコマンド（`uv run --locked pytest --collect-only -q tools/agent_runner | tail -n 1`、`git ls-files -z -- tools/agent_runner/tests | xargs -0 cat | wc -l`）を、コミット済みの状態で実行した。

| 指標 | 前（`7a8e4b7`） | 後（PR #247 のサイクル 1 の修正の後） | 比 |
| --- | --- | --- | --- |
| 件数（pytest の収集数） | 1,064 | 371 | 34.9% |
| 行数（`tools/agent_runner/tests` の追跡ファイル） | 10,404 | 7,171 | 68.9% |
| ファイル数 | 34 | 29 | — |

- 残す 371 件の内訳: 棚卸しで残す 347 件（S・F∩S・迷い）、監査で戻した 16 件（D-230-4。縮めた木での確認で、変異を検出しないと分かった 3 件の戻しは取り消した）、fixture の起動の経路だけが違うので一緒に残す 2 件（D-230-10）、PR #247 のサイクル 1 のレビュー修正で戻した 6 件（D-230-14）
- PR の作成の時点（`c13ea67`）は 365 件・7,125 行（34.3%・68.5%）だった
- Issue の「手がかり」の基準値（`5a6b096`、1,058 件・10,351 行）は、その後の main で 6 件・53 行増えていた。比は `7a8e4b7` を基準にした
- 件数は #228 の目標の 1/3 にほぼ届く（34.9%）が、行数は 68.9% で届かない。残る行は、実際のプロセス・git・bubblewrap を動かす S の長いシナリオと、その準備の fixture である（決定 6 のとおり `integration` の一覧で扱う）

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
| D-230-14 | PR #247 のサイクル 1 のレビュー（gpt-6.1-sol の M-1・M-2）と修正後の自己レビュー（L-2）を受けて 6 件を戻す。(1) 中断の分類（`test_abort_maps_to_interrupted`）と、同じ「担当が報告した中断は fallback を始めない」性質に頼る 2 つの経路（`dsh_identity.py:57-58` の v4 のログが無いときの分類の保持: `test_missing_identity_preserves_known_failure` の MISSING_CREDENTIAL のケース、`runner.py:557` の保持物があるときの success だけの置き換え: `test_nonregular_receipt_is_rejected_before_adapter_reads_it` と `FifoAdapter`）。(2) 厳密な判定の緩和（`runner.py:290` の `is True`: `[returns-false]`、`dsh.py:140` の `truncated` の `is True`: `test_invalid_intermediate_event_is_not_ignored` の tool_call のケース）。(3) D の代表が別の層にあり、消したテストの守りを通らない（自己レビューの L-2: `hooks.py:49-56` が後処理に run の cancel を渡す守りの `test_after_run_is_not_started_after_an_interrupted_run`） | 指摘の 2 件だけを戻す | 原因が 2 つあり、同じ原因に頼る経路を同じ PR で直す（review-fix-planning の「守る条件と影響経路」）。(1) lost の判定で「失敗の種類だけが変わる」を L とした判定が、その種類が `runner.py:604` の fallback の続行・停止を決める場合を見落とした。L の判定の理由を全て読み直し、停止の状態（interrupted）を続行の状態に変える変異を拾った。(2) 変異の演算子に値の緩和が無かった。比較の緩和・状態の差し替えの 191 個を足して流した。(3) の形（受け渡しの引数の差し替え）は、停止の event・期限・環境・cwd・伏せ字・パスの安全を運ぶキーワード引数の値の差し替え 57 個を足して流した（「サイクル 1 のレビューを受けた確認」） | 実行許可（`--merge` の PR 修正ループ）の中の review-fix-planning の完遂 |

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

### 結果

| 段 | 変異の数 | 結果 |
| --- | --- | --- |
| 生成 | 3,421 | 除外 405（`__all__` の要素 18、`else` の無い `if` の文の削除 387） |
| 事前の走査（基準のテストを速い順） | 1,315 | 基準が検出 975、検出しない 283、通るテスト無し 57。このうち 2 個（m00019・m00030）は、最初の走査の後に除いた `else` の無い `if` の文の削除。本走査では、実行する 3,016 個のうち検出しない 282 個と通るテスト無し 57 個の計 339 個を除いた |
| 本走査（残す → 消す） | 2,677 | 残すテストが検出 1,931（止まった 3 を含む）、lost 252（止まった 1 を含む）、基準も検出しない 457、通るテスト無し 36、止まったときに走っていたテストが残す側の異常終了 1（m01678）。縮めた木での確認で、残すテストの検出のうち 2 個（m00046・m02596）は誤りで lost と分かった |
| lost の判定 | 254 | S 18・迷い 9（どちらも検出していた消す側のテストを戻した。戻したテストは 16 件）、L 221（PR #247 のサイクル 1 で 7 個を S・1 個を迷いに改めた。D-230-14）、撤去 3（`runtime_supported`）、縮めた木での確認で lost ではないと分かったもの 3（基準も検出しない 2、残すテストが検出 1） |
| 縮めた木での確認 | 1,962 | 下の「縮めた木での確認」 |

lost の判定は、変異のある箇所ごとに controller と 3 つのサブエージェント（読むだけ。DSH 系、pi・cli・config 系、models・hooks・sandbox 系）が D-230-4 の原則で行い、controller が確かめた。pi 系の担当の指摘で、controller が L としていた `claude_code.py:75` の m00101 を S に直した（同じ経路の `pi.py:76` の m01301 と合わせた）。

### lost の判定

| 箇所 | 変異 | 判定 | 理由（S は防ぐ損害、L は見える経路） | 戻したテスト |
| --- | --- | --- | --- | --- |
| adapters/claude_code.py: _json_object（75 行、raw_decode の失敗で次の候補へ進む continue を外す） | m00101 | S（中） | 最初の候補で失敗したときは value が未束縛の UnboundLocalError で invalid_result になるが、前の fence が raw_decode に成功して閉じ fence の検査に落ちた後に次の fence で失敗すると、前の value・end のまま次の候補を照合し… | `adapters/test_parser_regressions.py::test_invalid_fence_cannot_salvage_inner_json[```json\n{"outer":{"ok":true},\n```-claude-code]` |
| adapters/codex.py: _event（42 行、type が文字列でないイベントを受け付ける） | m00452 | S（中） | type が文字列でない行を有効なイベントとして扱うと、壊れた出力（_malformed_events）として失敗にせず、type の壊れた turn.failed・error を見落として success を返し得る（失敗を成功と報告する）。base で検出していた test_invalid_event_type_is_response_failed_with_identity を戻す | `adapters/codex/test_codex.py::test_invalid_event_type_is_response_failed_with_identity[False-bad_type0]` |
| adapters/cursor.py: _prompt（21 行、依頼文を stdin から外す） | m00671 | S（中） | 依頼文（作業範囲の指示と依頼）を stdin から外しても起動は成功し、担当は依頼の無いまま JSON の回答（空の指摘など）を返せる。もっともらしい誤った成功として残る。base で検出していた test_prepare_reads_prompt_from_stdin_and_trusts_worktree を戻す | `adapters/cursor/test_cursor.py::test_prepare_reads_prompt_from_stdin_and_trusts_worktree` |
| adapters/pi.py: _json_object（76 行） | m01301 | S（中） | fence の raw_decode の失敗で次の候補へ進む continue を外す変異。最初の候補で失敗したときは value が未束縛で UnboundLocalError になり runner が invalid_result にする（runner.py:299-301）が… | `adapters/test_parser_regressions.py::test_invalid_fence_cannot_salvage_inner_json[```json\n{"outer":{"ok":true},\n```-pi]` |
| config.py: _validate_references（126・127 行） | m01871・m01803 | S（中） | 最終形の割り当てで未定義の role を拒否する検査。外すと、個人設定の役割名の誤記（例: [workflows.issue.assignments.implemnt] で implement の担当を選び直すつもり）が黙って通る。run_roles.py:326・implement_task.py:491・dispatch.py:295 は既知の役割だけを投影する（run_roles.py:131、implement_task.py:75… | `test_config.py::test_references_must_resolve[[workflows.audit.assignments.unknown]\nagents = ["first"]\n]` |
| models.py: StrictModel._payload の visit（78・85・89・95・97 行） | m02443・m02391・m02445・m02394・m02398・m02399 | S（中） | 担当の JSON の回答に NaN・Infinity・-Infinity（または 1e400 のように float で inf になる数）があると、adapter は json.loads・raw_decode でそのまま読み（claude_code.py:64・73、codex・cursor・devin・pi も同じ。DSH の _decode も parse_constant は NaN の語だけを拒み、1e400 は inf にする）… | `test_config.py::test_receipt_rejects_non_json_payloads[payload1]`・`test_config.py::test_receipt_rejects_non_json_payloads[payload2]` |
| process.py: redact_file の通常ファイルの確認（208・209 行） | m02698・m02544 | S（中） | FIFO などの特殊ファイルを伏せ字にできたとして True を返し、置き換えた空・部分の内容を収集に回し、sensitive_paths にも載せない（安全に伏せ字にできない保持物を収集に使わない、の守りが外れる）。base で検出していた test_unsafe_devin_export_is_retained_reported_and_never_collected の fifo のケースを戻す | `test_runner.py::test_unsafe_devin_export_is_retained_reported_and_never_collected[fifo]` |
| runner.py: _scrub の他の型（69 行） | m02790 | S（中） | 文字列・dict・list 以外の値（数・真偽値・null）を None にするので、成功の payload と identity の数・真偽値が伏せ字の処理で黙って null に変わる（記録の取り違え・データの消失）。base で検出していた codex の test_integration の success のケースを戻す | `adapters/codex/test_integration.py::test_reconnect_requires_fresh_completion_and_clean_process_exit[success-0-True]` |
| runner.py: 準備の失敗で起動しない（434 行） | m02933・m03101 | S（中） | worktree の準備が失敗した・停止を確かめられないときも担当を起動し、不完全な checkout で動いた結果を返し得る（未検証の状態での実行）。base で検出していた test_checkout_preparation_is_supervised の late_cancel のケースを戻す | `test_runner.py::test_checkout_preparation_is_supervised[late_cancel]` |
| workspace.py: snapshot_checkouts の locked の判定（206 行、理由つきの「locked <理由>」を外す） | m03407 | S（中） | 理由を付けてロックした worktree（git worktree lock --reason）を locked=false として記録する。監査の記録（checkout_audit の locked）は、止まったときに人が登録を prune・削除してよいかを判断する材料で… | `test_workspace.py::test_audit_diagnoses_unavailable_baseline[locked-checkout_missing-True-False]` |
| adapters/cursor.py: prepare（155 行、effort が無いときも [effort=None] を付ける） | m00709 | 迷い | model に [effort=None] が付いた値を CLI が拒否するか黙って既定で動くかを確かめていない（cursor は effort を観測しないので記録に残らない）。m00671 で戻す test_prepare_reads_prompt_from_stdin_and_trusts_worktree が検出する | `adapters/cursor/test_cursor.py::test_prepare_reads_prompt_from_stdin_and_trusts_worktree` |
| adapters/dsh.py: _intermediate_event_valid の tool_result の result の型（142 行） | m01120 | 迷い | status が completed・error で result が文字列でない tool_result を受け付ける。導入済みの DSH 0.2.1-rc.2 の投影は result を常に文字列で書く（json-stream:252 の resultText。長すぎる行でも scalar の result は残り、type と truncated だけの形は callId が無く dsh.py:134-135 で落ちる）ので… | `adapters/dsh/test_adapter.py::test_invalid_intermediate_event_is_not_ignored[event7]` |
| adapters/skills.py: configured_skill_paths（33・34 行） | m01610・m01572 | 迷い | is_file の検査を外すと、最初の source にある存在しない <source>/<name>/SKILL.md を採用し… | `adapters/cursor/test_cursor.py::test_prepare_keeps_native_fallback_when_no_configured_source_exists` |
| process.py: _finish の最初の _stop（270 行）・stdin の close（284 行） | m02569 | 迷い | 270 行: anchor を残したまま group の仲間を止める段を飛ばすと、anchor の解放の後に観測していない group の仲間を見つけられなくなる恐れがあるが、2 回目の _stop で止まる場面との違いを確かめていない。284 行: 終了時に stdin を閉じないと、大きな依頼文の書き込みの途中で期限になったときに transport が残り得るが、影響を確かめていない。どちらも base で検出していたテストを戻す | `test_process.py::test_deadline_kills_term_resistant_leader[False]` |
| runner.py: DSH の出力先の正規化の拒否（367 行） | m02900・m03096・m03154 | 迷い | DSH の出力先に symlink の祖先があると、柵の bind と prompt の書き込みの例外は正規化していないパスを使う。sandbox の書き込みの範囲がずれるかを確かめていない。base で検出していた test_dsh_output_ancestor_symlink_is_rejected を戻す | `adapters/dsh/test_runner.py::test_dsh_output_ancestor_symlink_is_rejected` |
| runner.py: 作業範囲の行と依頼文の間の空行（457 行） | m02946 | 迷い | 空行が無いと、依頼文の先頭の行が呼び出し側の許可した例外の一覧の続きに見える（依頼文が「- <パス>: …」で始まると、担当には許可された書き込みの例外として読める）。依頼文は呼び出し側のスキルが組み立てるので実際の損害は確かめていない。base で検出していた test_write_exceptions_follow_the_work_scope_lines_in_order を戻す | `test_cli.py::test_write_exceptions_follow_the_work_scope_lines_in_order` |
| adapters/__init__.py: runtime_supported（105・107・108 行） | m00069・m00070・m00071 | 撤去 | runtime_supported はコードからの呼び出し元が無く（参照は消すテスト 3 か所と #149 の過去の Spec・Plan だけ、external の 2 つの checkout にも無い）、撤去する |  |
| process.py: _Tree.live の子孫の探索（94 行の while True を False） | m02658 | 残すテストが検出 | 子孫を探さないと止めていない子孫が残り、後のテストが失敗する形で検出される。基準の木でも縮めた木でも、全体を流すと毎回検出するが、検出するテストは毎回違い（test_checkout_preparation_is_supervised・test_coroutine_cancellation_stops_leader_and_escaped_descendant など）… |  |
| process.py: _Tree.live の anchored（77 行）・_finish の stdin の close（284 行） | m02745・m02574 | 基準も検出しない | 本走査では消す側のテスト（test_immediate_exit_before_ownership_observation_stops_children[0-False-shell]、test_checkout_preparation_is_supervised[none]）だけが検出したが、その検出は負荷の下の誤りだった。戻したテストを変異を当てたコピーで単独で流すと 3 回とも通り… |  |
| _supervisor.py: main の except（60 行、IndexError を外す）・process.py: execute の tree の初期化（347 行） | m00046・m02596 | L | 本走査では残すテストが検出したが、縮めた木の確認で検出せず、基準の木では消す側の test_invalid_launch_arguments_return_safe_failure が 2 回とも検出した（本走査の残すテストの検出は誤り）。60 行: 空の argv の IndexError を捕まえないと supervisor が状態を送らずに終わり… |  |
| _supervisor.py: main の except（60 行） | m00044 | L | 起動できない argv（NUL を含む）の ValueError を捕まえないと supervisor が状態を送らずに終わり、controller は launch_failed ではなく response_failed を返す。どちらも失敗で、区別だけが変わる |  |
| adapters/__init__.py: module_name・load_adapter（58・78・79・91・96・98 行） | m00059・m00066・m00067・m00072・m00076・m00078・m00079 | L | 未知の runtime は設定の読み込み（models.Runtime の Literal）で拒否され、raise を外しても固定の接頭辞の名前（tools.agent_runner.adapters.None）の import が失敗して UnsupportedRuntime になる。形の誤った ADAPTER を返しても、runner は capabilities の参照の例外を unsupported に… |  |
| adapters/claude_code.py: _identity・_classify（132・151 行） | m00205・m00185 | L | 132 行: model が文字列でない assistant の message を観測すると Identity の検証（strict）か KeyError の例外で invalid_result になる。151 行: 成功の result まで診断に入れると、成功の回答が認証・承認の語を含むときに awaiting_authentication などの失敗になる（成功が失敗として見える向き） |  |
| adapters/claude_code.py: _json_object・_payload（75・78・79・84・85 行） | m00177・m00103・m00164・m00106・m00199・m00222・m00223・m00224・m00225 | L | fence の中の JSON・text の回答の取り出しを壊すと、正しい回答が response_failed（失敗）になるか、タプルの分解の例外で invalid_result になる。どれも成功が失敗として見える向きで、失敗を成功にしない。 |  |
| adapters/codex.py: _prompt・_diagnostics・_rollout・_rollout_fields（30・128・141・187 行） | m00247・m00304・m00311・m00339 | L | 30 行: JSON の形の指示が無いと、担当が JSON 以外で答えたときに response_failed として見える。128 行: 失敗のイベントを診断の文から外すと、認証待ちが response_failed になる（どちらも失敗で区別だけ）。141 行: session id が None のとき re.escape の TypeError で invalid_result になる。文字列の不正な id は… |  |
| adapters/codex.py: _prompt（29 行）・_json_object（62 行）・_rollout_fields（186 行）・collect（220・241・251・252・258・289 行） | m00413・m00480・m00479・m00442・m00495・m00370・m00498・m00379・m00523・m00409 | L | 29 行: JSON の形の指示が無いと、JSON 以外の回答が response_failed として見える。62 行: 空の object や配列を payload にしても… |  |
| adapters/cursor.py: _prompt（22 行）・_read_evidence（83・86・90・100 行）・_diagnostics（135・138 行）・collect（197・219 行） | m00659・m00663・m00664・m00665・m00679・m00668・m00692・m00705・m00706・m00722・m00721・m00744・m00655 | L | 22 行: JSON の形の指示の欠落は JSON 以外の回答の response_failed として見える。83〜100 行: dict でない read・result・success・readRange を読み進めると None.get の AttributeError で invalid_result（shell などの読み取り以外の tool_call が来るだけで失敗する）。90 行で error と success の両方がある読み取りを証拠… |  |
| adapters/cursor.py: _prompt（23 行）・_read_evidence（84・87・91・101 行）・_diagnostics（142 行） | m00534・m00565・m00568・m00572・m00582・m00605 | L | 23 行: JSON の形の指示の欠落は、JSON 以外の回答の response_failed として見える。84〜101 行: 形の違う tool_call・read・result・path を読み進めると .get・fullmatch の AttributeError・TypeError で invalid_result になる。142 行: stdout の診断の行を外しても、失敗は errored と result の検査で決まり… |  |
| adapters/devin.py: _ends_with（71 行）・_json_object（100 行）・最後の回答（156 行）・診断の行（244 行） | m00750・m00864・m00872・m00889 | L | 71 行: 回答を strip しないと、stdout の末尾との照合が外れて成功が response_failed になる（失敗を成功にはしない）。100 行: 空の object は runner の形の確認で invalid_result。156 行: message が None のとき .strip() の AttributeError で invalid_result。244 行: 全ての行を診断の行として扱うと… |  |
| adapters/dsh.py: _classify の aborted（161・162 行） | m01127・m00954・m01223・m01224 | S（PR #247 のサイクル 1 で L から改めた） | 中断が別の失敗の種類になると、`runner.py:604` が fallback の担当を起動して成功を返す。当初の判定は、PR #170 の既知の制限（応答の前のログで診断が上書きされる場合だけの話）を一般の中断に当てはめて L とした誤り（D-230-14） | `test_abort_maps_to_interrupted` |
| adapters/dsh.py: _classify の completed の tool_result（151 行）・text の形（196・197 行） | m01122・m01079・m00985・m01139・m01140 | L | 成功が失敗になる向き。151 行: completed の tool の結果が拒否の文の形をしていると awaiting_approval になり（dsh.py:154-155）、正しい回答を捨てる。196・197 行: text の役割の回答を JSON として取り出し、JSON でなければ response_failed（dsh.py:198-199）… |  |
| adapters/dsh.py: _classify の長さ・先頭・末尾の検査（165・166 行） | m01075・m01088・m00958 | L | 空の stream は dsh.py:165・167 の events[0] の IndexError が collect の except（dsh.py:348）を抜け、runner が invalid_result にする（runner.py:299-301）。それ以外の短い・先頭が session でない・末尾が final でない stream は… |  |
| adapters/dsh.py: _diagnostic（113・114 行）・_classify の top-level の error（149・150 行）・collect の stderr の診断（350・352 行） | m01070・m00926・m01085・m00944・m01106・m01056 | L | 失敗の種類だけが変わる。113・114 行: _diagnostic が awaiting_approval を返さず response_failed になる。呼び出し元（dsh.py:150・164・352）はどれも既に失敗の経路で、tool の拒否は _diagnostic を通らず dsh.py:154-155 が awaiting_approval にする。149・150 行: top-level の error を先に分類しなくても… |  |
| adapters/dsh.py: _intermediate_event_valid の step の turn・型（127 行）・tool_call の input（138 行） | m01112・m01113 | L | 損害が無い。受け付けるようになる形（今の turn と違う step、int でない step、（m01167 は下の行））は、導入済みの DSH 0.2.1-rc.2 の投影では出ない（step は同じ session の turn・step をそのまま書く: json-stream:183・192-199・214-228。tool_call は常に input を書き… |  |
| adapters/dsh.py: _intermediate_event_valid の tool_call の input（138 行） | m01167 | 迷い（PR #247 のサイクル 1 で L から改めた） | input も truncated も無い tool_call を受け付ける。導入済みの DSH の投影では出ないが、同じ形を値の変異 v0070 でも見つけたので、不正な中間イベントを黙って受け入れる向きとして迷いにした（D-230-14） | `test_invalid_intermediate_event_is_not_ignored` の tool_call のケース |
| adapters/dsh.py: _intermediate_event_valid の text・thinking（122・123 行）・step の代入（125 行）・truncated の tool_call（140 行） | m01072・m01109・m00932・m00934・m01216 | L | 成功が失敗になる向きで、普段の利用で現れる。122・123 行: DSH の投影は応答の reasoning・text を thinking・text のイベントにする（導入済みの dsh-headless の lib/json-stream-BA-F3lfb.js:203-212）ので… |  |
| adapters/dsh.py: _json_payload（106 行） | m01164 | L | 空の object を payload として返しても、collect は success と {} の Receipt を返し、runner の形の確認（runner.py:279-285… |  |
| adapters/dsh.py: collect の object でないイベント（344・345 行）と TypeError の捕捉（348 行） | m01205・m01051・m01209 | L | object でない行をイベントに入れると、_classify の event.get（dsh.py:149）の AttributeError が collect の except（dsh.py:348）を抜ける。TypeError を捕まえないと、dsh.py:345 の TypeError と… |  |
| adapters/dsh.py: prepare の command の /tmp のファイルの読み取り（252・253 行）と内側の bash の HOME の grant（274 行） | m01156・m01021・m01276 | L | どれも見える範囲・書ける範囲を狭める向きで、柵は広がらない。252・253 行: command の絶対パスのファイルを戻さないと、/tmp の下の CLI が --tmpfs /tmp に隠れて exec に失敗し、DSH が起動しないので stdout が空になり response_failed（dsh.py:165-166… |  |
| adapters/dsh.py: prepare の provider・args の検査（207・208 行） | m01099・m01145・m01146・m00990 | L | provider が None・未知: 検査が無くても _KEYS[provider] の KeyError（dsh.py:229）で prepare が失敗し、runner が launch_failed にする（runner.py:485・495-496）。args: prepare は agent.args を 207 行の検査のほかで使わないので、args は CLI に渡らず… |  |
| adapters/dsh.py: prepare の sandbox_write_paths の拒否（209・210 行） | m01100・m00992 | L | prepare は sandbox_write_paths を 209 行の検査のほかで使わず、どこにも bind しないので、柵は広がらない（書けるのは outer_command の workspace と所有の HOME・state・tmp・scratch だけ: dsh_sandbox.py:35-41）。呼び出し側が書かせたかった場所への書き込みは、--ro-bind / / の下で Read-only file system になるか… |  |
| adapters/pi.py: _classify（195・204 行） | m01480・m01551 | L | どちらも失敗の経路（diagnostics と failed）を広げるか、失敗の種類を変える向きだけ。195 行: 形の壊れた行をすべて診断に入れて failed にすると、agent_end より前に壊れた行（type が文字列でない行など）があるだけで pi.py:210-211 の response_failed… |  |
| adapters/skills.py: verified_versions（84・85 行） | m01612・m01595 | L | 84 行: except から OSError を外すと、読んだ後に消えた・読めない SKILL.md の OSError が adapter の collect から出る（呼び出し元の pi.py:238・codex.py:116・cursor.py:124 は吸収しない）。FileNotFoundError は runner.py:297-298 で missing_result… |  |
| cli.py: _inventory（77・78・82・83・84・87・88・89・91・95 行） | m01656・m01657・m01659・m01660・m01661・m01662・m01719・m01720・m01663・m01729・m01730・m01664・m01708・m01709・m01735 | L | check・list の出力だけを変える（#230 の L の例）。77・78・87 行の文の削除（m01656・m01657・m01662）は try の外の NameError・KeyError で cli.py:190-192 の runner_failed（終了コード 2）になり… |  |
| cli.py: main（170・185・186 行） | m01725・m01699・m01700 | L | 170 行: --template が無いと template が None になり… |  |
| config.py: _CATEGORIES（14 行）・_validation_category（113・114・117・118 行） | m01845・m01847・m01849・m01852・m01839・m01881・m01795・m01841・m01874・m01799 | L | ConfigError の category の名前だけが変わる（config.py:33 で invalid_config に丸まる、または _validation_category が別の分類を返す）。ConfigError を送出する箇所と条件は変わらず（_validation_category を使う config.py:176-177 も含む）、CLI は cli.py:187-189 の終了コード 2 で… |  |
| config.py: _override（86・92 行） | m01836・m01860・m01777 | L | --assign の workflow と role の検査を外しても、workflow が None・未知なら config.py:94 の workflows[workflow] の KeyError で cli.py:190-192 の runner_failed（終了コード 2）になる。未知の role は新しい割り当てとして足されるが… |  |
| config.py: _read（65・66 行） | m01867・m01868・m01766 | L | 65 行: TOMLDecodeError・UnicodeDecodeError の片方を except から外すと、その例外がそのまま出る。CLI は cli.py:190-192 の runner_failed（終了コード 2）、run_roles.py:507・dispatch.py:616 は ValueError として型の名前だけを出し… |  |
| config.py: _validate_references（133・134・140・141 行） | m01877・m01809・m01872・m01879・m01880・m01815 | L | 133・134 行: 未定義の agent の拒否を外しても、config.py:135 の agent.model が None の AttributeError で止まる。CLI は cli.py:190-192 の runner_failed（終了コード 2）、呼び出し側のスクリプトは AttributeError を捕まえずにトレースバックで止まる（run_roles.py:507、implement_task.py:702… |  |
| config.py: check_depth（56 行） | m01762 | L | 整数でない AGENT_RUNNER_DEPTH で raise を外しても、config.py:57 の if nested: で nested が未束縛の UnboundLocalError になる。CLI は cli.py:190-192 の runner_failed（終了コード 2）… |  |
| config.py: validate_config（152・153 行） | m01842・m01821 | L | 未知の workflow を validate_config が通しても… |  |
| dsh_identity.py: _read_session のログが無いとき（57・58 行） | m01951・m01901 | S（PR #247 のサイクル 1 で L から改めた） | v4 のログが無いと ValueError（ambiguous）になり、collect（dsh.py:369-372）が中断（interrupted）も response_failed に置き換えて、fallback の担当が起動する（変異を当てた写しで確かめた）。当初の判定は認証待ちの種類の違いだけを見た（D-230-14） | `test_missing_identity_preserves_known_failure` の MISSING_CREDENTIAL のケース |
| dsh_identity.py: _read_session の改行の無い末尾（79・80 行） | m01972・m01920 | L | 棚卸しの理由（json.loads が止める）は誤りで、この 2 つは break を残すので、停止後のログでも改行の無い末尾を黙って捨て、完全な前半の記録から identity を返す。それでも損害は無い。DSH の JSONL の永続化は同じプロセスの worker_threads で動き… |  |
| dsh_paths.py: _regular_bytes の通常ファイル・単一リンク・大きさ（52・53 行）・parent_review_read_paths の snapshot の形（118・125 行）と bundle の digest（130・131 行） | m02075・m02102・m02016・m02073・m02087・m02051・m02074・m02057 | L | 後段が同じ条件で必ず止める。DSH の review は、sandbox の中の helper の prepare（pr-review の review_run.py:329-330）・complete（787 行）と、停止の後の親の finalize（1191 行）が parent_data.load（pr_review_parent.py:112-158）で、単一リンクの通常ファイル（pr_review_parent.py:50）… |  |
| dsh_paths.py: parent_review_read_paths の parent_pr_data の無い依頼文（100・101・102 行） | m02037・m02069・m02079・m02039 | L | json の fence があって parent_pr_data の無い依頼文で prepare が失敗し… |  |
| dsh_review_evidence.py: promotion_refusal の input の dict の検査（83・95 行） | m02218・m02226 | L | input が dict でない tool_call（DSH の truncated の call は input を持たない、dsh.py:140）で .get の AttributeError になる（83 行は tool_call の段… |  |
| dsh_review_evidence.py: promotion_refusal の native の書き込みの一覧（95 行の {"write", "edit"}） | m02235 | L | edit を native の書き込みから外すと、edit で書いた固定の出力が written に入らず、107-108 行で理由付きで拒否され、finalize_parent_batch が payload を failed にする（review_run.py:1361-1367）。一覧を狭めるだけで、成功が拒否になる向きだけ |  |
| dsh_review_evidence.py: promotion_refusal の対応する call の無い result（87・88 行） | m02220・m02163 | L | call の無い tool_result（status・result は _classify が検査済み、dsh.py:142）は、completed なら 94 行の call.get の AttributeError で、上の group と同じく finalize が例外で止まる（review_run.py:1455-1461・loop.py:2171）。error なら… |  |
| dsh_sandbox.py: main の except（74 行の (OSError, ValueError)） | m02296 | L | OSError を捕まえないと、無い・読めない grant（grant_path の resolve(strict=True)・lstat、dsh_sandbox.py:17-19）や execv の失敗がtraceback で終了コード 1 になる（dsh_sandbox.py:80-81）。どれも execv の前か execv そのものの失敗で、コマンドは走らない。DSH には runner の失敗の署名（dsh-sandbox:・bwrap:… |  |
| dsh_sandbox.py: main の profile・command の検査（62・63 行） | m02290・m02293・m02263 | L | DSH が渡す profile は比べるだけで mount に使わない。mount は固定の BASE・writable から作り（dsh_sandbox.py:67-72）、writable と一致しない profile は読み取り専用の [*BASE, *reads] になるので… |  |
| environ.py: literal_environ の os.environ への fallback（25 行） | m02317 | L | /proc/self/environ を読めないときの代入を外すと、dict(None) の TypeError になる。run_workflow の最初の呼び出しは resolve_revision の_git（workspace.py:48-60 の except に TypeError は無い）で… |  |
| hooks.py: _state（23・25 行の失敗の種類） | m02351・m02353 | L | 23 行の state の項を外すと、終了コードのある timed_out・interrupted が failed になる。25 行を "failed" にすると、timed_out・interrupted・launch_failed がすべて failed になる。どちらも後処理の失敗の種類が変わるだけで、success（21 行）にはならない。loop.py:2199 は success 以外を LoopError にし… |  |
| hooks.py: _state（25 行の return を外す） | m02331 | L | 25 行を外すと、timed_out・interrupted・launch_failed と、終了コードの無い response_failed の報告の state が null になる（interfaces.rst「後処理」の一覧に無い値）。success にはならず、ループは success 以外を LoopError にし（loop.py:2199）… |  |
| models.py: Agent._environment_names（121・122 行） | m02427・m02404 | L | 名前でない要素（"TOP_SECRET=value"・空白付きの名前など）が許可リストに入っても、引き継ぎは起動時の環境の名前との完全一致だけ（runner.py:475 の name in ambient、dsh.py:230 の key_name in agent.env）で… |  |
| models.py: Assignment._no_self_fallback（147・148 行） | m02429・m02410 | L | fallback の self は、一次担当が失敗して fallback に進んだときだけ attempt に入る。期限・中断の確認（runner.py:395-398 でtimed_out・interrupted）の後の config.agents["self"]（runner.py:399、try の外）で KeyError になり… |  |
| models.py: Assignment._self_alone（140・141 行） | m02428・m02407 | L | agents に self と担当が混ざっても、runner は self の Result（attempts 無し）と担当の Result を別々に返すだけ（runner.py:583-591）。担当が失敗すれば batch は partial_success で CLI は 1（runner.py:636-641・cli.py:160）。利用側は… |  |
| models.py: StrictModel._payload の循環の検出（82・83 行） | m02444・m02389 | L | 循環の検出を外すと visit が無限に再帰して RecursionError になる。adapter の Receipt の組み立て（例: claude_code.py:100-108）で漏れ、runner の _collect の except Exception（runner.py:299-301）が基準と同じ invalid_result にする。payload は JSON の解析（receipts.py:25… |  |
| models.py: StrictModel._schema_version（65・66 行） | m02426・m02433・m02379 | L | _schema_version を外しても 2・"1" は Literal[1]（strict）が拒否し、新たに通るのは true だけで v1 として読まれる。Config・Request・Receipt・BatchResult とも v1 しか無いので、別の版の設定・receipt を取り違える相手が無い（損害なし） |  |
| models.py: _identifier（31・32 行） | m02417・m02370 | L | 識別子の書式の検査を外しても、損害の経路が無い。設定の名前（agent・role・workflow のキー、assignments の agents・fallback）はdict の引き当てと一致の比較にだけ使い（runner.py:399-400・577-628、config.py:122-143、checkout_policy.py:28-41）… |  |
| models.py: _nonblank の isinstance の項（37 行） | m02422 | L | isinstance の項を外すと、文字列でない値（model = 123… |  |
| models.py: _nonblank・_argument・Agent._executable・Workflow._executables（37・38・43・44・115・162 行） | m02418・m02431・m02373・m02419・m02376・m02401・m02412 | L | 空・空白・NUL の値が通っても、どれも失敗として見えるか損害が無い。command・args・after_run の要素の NUL は argv に入り、create_subprocess_exec の ValueError で launch_failed（process.py:418-419。後処理では hooks の報告が launch_failed で… |  |
| process.py: _stop の stopped（137 行）・_command_outcome（164・165 行）・execute の変数の初期化と状態（346・349・400・419・432 行） | m02497・m02651・m02517・m02595・m02598・m02620・m02757・m02674 | L | 137 行: preserve のある停止の判定が常に偽になり、SIGTERM・SIGKILL の猶予を最後まで待つだけ（信号を送る対象は同じ観測した PID で、anchor は preserve で除かれる）。遅くなるだけで、止まらなければ目に見えて止まる。164・165 行: 不正な状態の行で matched が None のまま int(matched[1]) の TypeError になり… |  |
| runner.py: _single_line の型（102 行）・adapter が返してよい状態の集合（253 行）・DSH の依頼文の例外（447 行） | m03043・m03130・m03131・m03104 | L | 102 行: 文字列でない write_exceptions の要素で value.strip() の AttributeError が run_workflow から出る（CLI は runner_failed の終了コード 2）。253 行: awaiting_authentication・awaiting_approval を許す状態から外すと… |  |
| runner.py: adapter の読み込みの失敗（408 行）・DSH の所有の書き込みの例外（448 行） | m02922・m02943 | L | 408 行: adapter が未束縛のまま後の prepare の NameError を runner.py:495-496 が launch_failed にする（unsupported との区別だけ）。448 行: DSH の依頼文の書き込みの例外が呼び出し側のものになっても、柵（bubblewrap）は変わらず、担当が所有の領域に書けずに失敗する（成功が失敗になる向き） |  |
| runner.py: 伏せ字にできない保持物の扱い（557 行、state == "success" を外す） | m03231 | S（PR #247 のサイクル 1 で L から改めた） | sensitive_paths があると、担当が報告した中断も response_failed になり、fallback の担当が起動する（自己レビューの fix-check が実行で確かめた）。中断だけを置き換える変更は基準のテストも検出しない（申し送り）（D-230-14） | `test_nonregular_receipt_is_rejected_before_adapter_reads_it` |
| runner.py: 準備の失敗の状態（433 行）・DSH の所有の書き込みの例外の要素（448 行） | m03199・m03201・m03202 | L | 433 行: 準備の timed_out・interrupted が response_failed になっても、次の候補の試行は期限（runner.py:397）・取り消し（runner.py:395）で同じ状態で終わり、失敗の種類と試行の記録が 1 つ増えるだけ。448 行: DSH の依頼文から所有の書き込みの例外の行を 1 つ外しても柵（bubblewrap）は変わらず、担当がその領域に書かずに失敗するか、書いて成功する（成果は柵の中だけ） |  |
| workspace.py: _fingerprint のディレクトリの確認（151・152 行）・symlink の祖先の扱い（164〜174 行）・require_auditable_checkouts の事前の失敗（246 行） | m03367・m03288・m03298・m03300・m03397・m03304・m03307・m03345・m03388 | L | 151・152 行: ディレクトリでない checkout は、続く git -C の失敗で WorkspaceError（git_unavailable）になり、同じく監査できない checkout として記録される（理由の名前だけが変わる）。164〜174 行: symlink の祖先をたどると、外の referent の内容を指紋に入れるので、外の変化を checkout の変更（content_changed）として誤って報告するか… |  |

### 縮めた木での確認

コミット `c1d8755` の木で、本走査で残すテストが検出した変異 1,931 個、戻したテストの変異 30 個、異常終了の 1 個の計 1,962 個を、縮めた木のテスト（coverage を関数ごとに新しい node ID に写して選んだ）だけで実行した（`res/pass2.jsonl`）。

- 1,957 個を検出した。検出されなかったのは 4 個、1 個は止まったときに走っていたテストが残す側の異常終了（m01678、SIGINT のテスト）
- 検出されなかった 4 個と、戻したテストの全て（変異を当てたコピーで、戻したテストだけを 2〜3 回）を確かめ直した
  - m02745（`process.py:77`）・m02574（`process.py:284`）: 戻したテストは単独で毎回通り、基準の木で通るテストを全て流しても 2 回とも検出しない。本走査の lost は負荷の下の誤った失敗だった。lost から外し、戻した 2 件を外した（commit `c13ea67`）
  - m02658（`process.py:94`）: 戻した `[9-True]` は単独で通るが、基準の木でも縮めた木でも、全体を流すと前のテストが残した子孫のプロセスで後のテストが失敗する形で毎回検出する（失敗するテストは毎回違う）。残すテストが検出するので lost から外し、`[9-True]` を外した（`c13ea67`）
  - m00046（`_supervisor.py:60`）・m02596（`process.py:347`）: 本走査の残すテストの検出は誤りで、基準の木では消す側の `test_invalid_launch_arguments_return_safe_failure` が 2 回とも検出する（lost）。どちらも L（「lost の判定」）
  - 残りの戻したテスト 16 件は、それぞれの変異を単独で 2 回とも検出した
- 外した 3 件が縮めた木の確認で最初に検出した変異は m02633 だけで、最終の木（`c13ea67`）でも残すテストが 2 回とも検出した

### サイクル 1 のレビューを受けた確認（D-230-14）

PR #247 のサイクル 1 で、gpt-6.1-sol が S の最後の代表を消した 2 件（DSH の中断の分類、payload_check の False の戻り値）を見つけた（レビュー修正の Spec: `docs/superpowers/specs/2026-10-23-create-reso-world-pr247-issue230-review-fixes-design.md`）。原因は 2 つで、それぞれ同じ原因に頼る経路を確かめた。記録は `/workspaces/reso-world/tmp/agents/issue-230.fuotebjq/audit/c1/`（コミットしない）。

- 判定の誤り: 中断の分類の変異 m01127・m00954・m01223・m01224 は lost として見つかっていたが、「失敗の種類だけが変わる」として L にしていた（`triage-t1-dsh.json`。根拠に挙げた PR #170 の既知の制限は、応答の前のログで診断が上書きされる場合だけの話だった）。`runner.py:604` は success・interrupted・timed_out と停止未確認だけで fallback を止めるので、担当が報告した中断が別の失敗になると次の担当が起動する。L の判定の理由を全て読み直し、停止の状態を続行の状態に変える変異を探した。見つかった経路は 2 つで、m01951・m01901（`dsh_identity.py:57-58`。v4 のログが無いと中断も response_failed にする。変異を当てた写しで確かめた）と m03231（`runner.py:557`。保持物があると中断も response_failed にする。コードを読んだ判断なので迷い）である。ほかの「失敗の種類」の L（認証・承認待ちと response_failed・invalid_result の区別、後処理の状態、準備の中断）は、どちらの状態でも fallback を続けるか、runner 自身の取り消し・期限で同じ状態に終わるので L のままにした
- 演算子の不足: 監査の演算子（条件・複合条件の項・文・一覧の要素・定数）に値の緩和が無く、`runner.py:290` の `is True` を緩める変異を作っていなかった。守りのコード 24 ファイルに、比較の緩和（`True`・`False`・`None` との `is`・`is not` の比較を、緩い比較か真偽値にする）と状態の差し替え（返す・代入する状態の interrupted・timed_out を response_failed に、失敗の状態を success にする）の 219 個を作り（`bin/gen_value_ops.py`）、消すテストが覆う 191 個を、縮めた木（`c899bd4` のテスト。coverage を関数ごとに写した対応表）と基準の木で流した（PID 名前空間、テスト 1 件 30 秒の上限）
  - 縮めた木: 39 個を検出し、144 個は検出せず、8 個は覆うテストが無い
  - 基準の木（縮めた木で検出しなかった 152 個）: 15 個を消すテストが検出し、137 個は基準も検出しない
  - 15 個のうち、v0083（`dsh.py:162`）と v0195（`runner.py:290`）は指摘の 2 件と同じ守り。v0070（`dsh.py:140`。input も truncated も無い tool_call を受け付ける）は不正な中間イベントを黙って受け入れる向きなので、迷いとして戻した。残りの 12 個は L: 失敗の状態を success にしても payload が null なので runner の形の確認（`runner.py:279-285`）で invalid_result になる（v0013・v0076・v0077・v0080・v0085）、`process.py:400・419` は runner の取り消しの確認と `runner.py:553-560` で失敗のままになる（v0172・v0170）、`cli.py:83-84` は `check`・`list` の表示だけを変える（v0117〜v0120）、`codex.py:226` は runner が常に PATH を含む環境を渡すので空の環境に届かない（v0025）
- 代表が別の層にある D（修正後の自己レビューの L-2）: `test_after_run_is_not_started_after_an_interrupted_run` は D（代表 `test_process.py::test_already_cancelled_does_not_spawn`）として消していたが、代表は `process.execute` に取り消し済みの event を直接渡すだけで、`hooks.run_after_run` が後処理の `execute` に run の cancel を渡すこと（`hooks.py:49-56`）を通らない。cancel を新しい event に差し替えると、SIGINT で中断した run でも後処理が起動する（interfaces.rst「後処理」の保証が破れる）。同じ形（受け渡しの引数の差し替え）を、停止の event・期限・環境・cwd・伏せ字・パスの安全を運ぶキーワード引数（`cancel`・`deadline_seconds`・`timeout`・`env`・`cwd`・`dir_fd`・`secrets`・`preserve`・`required_paths`・`follow_symlinks`・`strict`・`check`・`stop_confirmed`）の値の差し替え 58 個（消すテストが覆う 57 個）で流した（`bin/gen_kwarg_ops.py`、縮めた木は修正の commit の木）
  - 縮めた木: 39 個を検出し、18 個は検出しない
  - 基準の木（18 個）: 2 個を消すテストが検出し、16 個は基準も検出しない。2 個のうち k0024（`hooks.py:49` の cancel）は S として `test_after_run_is_not_started_after_an_interrupted_run` を戻した。k0023（`hooks.py:49` の期限を 1e9）は、止まらない後処理で CLI が戻らず目に見えて止まるので L
  - 基準も検出しない 16 個には、`hooks.py:49` の `secrets=()`（後処理のログを伏せ字にしない）、`runner.py:126` の `follow_symlinks=True`、`cli.py:144` の cancel（CLI から後処理への受け渡し）がある（#236 への申し送り）

## 撤去（#228 の決定 5）

| 撤去したもの | 使われていないと判断した根拠 |
| --- | --- |
| `tools/agent_runner/adapters/__init__.py` の `runtime_supported`（check・list の補助として #149 で入れた関数） | worktree の `git grep -n runtime_supported` で、コードからの呼び出し元が無い（CLI の check・list は `cli.py` の `_inventory` で `load_adapter` を直接呼ぶ）。参照は消したテスト 3 か所（`test_cli.py`・`test_config.py`・`adapters/dsh/test_adapter.py`、どれも L）と、#149 の過去の Spec・Plan（`docs/superpowers/specs/2026-10-18-create-reso-world-issue149-agent-runner-core-design.md:35`、`docs/superpowers/plans/2026-10-18-create-reso-world-issue149-agent-runner-core.md:88`。完了した記録なので変えない）だけ。`tools/agent_runner/__init__.py` の `__all__` と `interfaces.rst` に無い。`external/resoloop`（`39db994`）・`external/resoloop-meshy`（`1b64663`）の `git grep -n 'agent_runner\|agent-runner'` は 0 件 |

撤去しなかったもの（D-230-8）: `workspace.py` の `changed_checkouts`（呼び出し元は残す S のテストだけ）と、`audit_checkouts` の素の dict の受け付け。どちらも撤去すると残す S のテストを書き換える。`interfaces.rst`・`README.md`・`.devcontainer/README.md`・`docs/` には `runtime_supported` を説明する行が無いので、変えていない。

## 守りの確認（重さが高の守りで代表に絞ったもの）

Issue の受け入れ（守る処理を一時的に壊した使い捨てのコピーで、残したテストが失敗することを 1 回ずつ確かめる）の記録。棚卸しで重さが高の S のうち、ケース・同じ守りの別のテストを消して代表に絞ったもの 32 項目について、その守りの行（棚卸しの guard）の変異を縮めた木（`c1d8755`）の確認で当てたとき、最初に失敗した残すテストを挙げる。最終の木（`c13ea67`）で外した 3 件は、表の「失敗した残すテスト」に含まない。変異のコピーは `/tmp` に `tempfile.mkdtemp` で作り、実行の後に消した。

| 守り（棚卸しの guard） | 残したテスト | 変異（壊した箇所） | 失敗した残すテスト |
| --- | --- | --- | --- |
| runner.py:378-379, runner.py:474-475, runner.py:490-494, runner.py:631-635 | `test_only_allowlisted_environment_and_redacted_results` | m02906 stmt_del runner.py:378 | `test_role_deadline_covers_fallback_attempts[4.0]` |
| runner.py:420-434, workspace.py:89-135 | `test_checkout_preparation_is_supervised` | m02933 stmt_del runner.py:434 | `test_checkout_preparation_is_supervised[late_cancel]` |
| runner.py:514, runner.py:532-533 | `test_devin_retained_export_is_redacted_after_nonzero_exit` | m03109 cond_false runner.py:514 | `test_devin_retained_export_is_redacted_after_nonzero_exit` |
| runner.py:542-543, process.py:170-233 | `test_retained_receipts_are_scrubbed_even_when_invalid` | m03114 cond_false runner.py:542 | `test_retained_receipts_are_scrubbed_even_when_invalid[True]` |
| dsh_sandbox.py:36-41, adapters/dsh.py:219 | `test_tmp_parent_review_inputs_are_readonly_in_native_and_inner_bash` | m02245 stmt_del dsh_sandbox.py:36 | `test_prepare_isolates_state_and_passes_config_not_credentials[commandcode-COMMANDCODE_API_KEY]` |
| dsh_paths.py:113-115, dsh_sandbox.py:15-22 | `test_invalid_parent_review_input_is_rejected_before_launch` | m02046 stmt_del dsh_paths.py:113 | `test_invalid_parent_review_input_is_rejected_before_launch[hash]` |
| adapters/dsh.py:337-382 | `test_approval_classification_does_not_mutate_input_state` | m01046 stmt_del adapters/dsh.py:338 | `test_dsh_disk_receipt_cannot_override_failed_jsonl` |
| dsh_review_evidence.py:27-50 | `test_unsafe_log_is_refused_without_touching_its_target` | m02131 stmt_del dsh_review_evidence.py:46 | `test_unsafe_log_is_refused_without_touching_its_target[hardlink]` |
| dsh_sandbox.py:12, adapters/dsh.py:315-318 | `test_native_process_has_private_tmp_and_readonly_attempt_metadata` | m02275 elt_del dsh_sandbox.py:12 | `test_explicit_grants_preserve_neighboring_host_files` |
| adapters/dsh.py:254-267, dsh_sandbox.py:39 | `test_scoped_dsh_cannot_modify_protected_or_unrelated_host_paths` | m01022 stmt_del adapters/dsh.py:254 | `test_prepare_isolates_state_and_passes_config_not_credentials[commandcode-COMMANDCODE_API_KEY]` |
| runner.py:72-89 | `test_runtime_hardlinks_are_rejected_before_redaction_hides_the_link` | m02791 stmt_del runner.py:74 | `test_runtime_hardlinks_are_rejected_before_redaction_hides_the_link` |
| runner.py:378-379 | `test_explicit_auth_environment_is_allowlisted_and_redacted` | m02906 stmt_del runner.py:378 | `test_role_deadline_covers_fallback_attempts[4.0]` |
| runner.py:145-174 | `test_scratch_links_and_fifos_are_unlinked_not_followed` | m03240 boolop_drop runner.py:161 | `test_scratch_links_and_fifos_are_unlinked_not_followed[tmp-symlink-foreign-link]` |
| runner.py:177-216 | `test_scratch_hardlinks_are_unlinked_and_the_rest_redacted` | m02842 stmt_del runner.py:211 | `test_scratch_hardlinks_are_unlinked_and_the_rest_redacted` |
| runner.py:177-216 | `test_real_pytest_scratch_is_accepted` | m02839 stmt_del runner.py:208 | `test_real_pytest_scratch_is_accepted[pytest-fixtures]` |
| runner.py:517-528 | `test_timeout_and_cancellation_stop_descendants` | m02975 stmt_del runner.py:517 | `test_role_deadline_covers_fallback_attempts[4.0]` |
| dsh_sandbox.py:15-22 | `test_unsafe_grants_or_profile_never_run_the_command` | m02237 stmt_del dsh_sandbox.py:16 | `test_prepare_isolates_state_and_passes_config_not_credentials[commandcode-COMMANDCODE_API_KEY]` |
| process.py:73-93, process.py:408-415 | `test_immediate_exit_before_ownership_observation_stops_children` | m02471 stmt_del process.py:73 | `test_reused_leader_group_is_not_signaled` |
| process.py:94-109, process.py:133-147 | `test_leader_exit_stops_observed_descendants` | m02482 stmt_del process.py:95 | `test_reused_leader_group_is_not_signaled` |
| process.py:43-48 | `test_non_utf8_descendant_name_does_not_escape_tracking` | m02453 stmt_del process.py:45 | `test_control_eof_never_uses_successful_helper_exit` |
| workspace.py:138-195, workspace.py:198-223 | `test_audit_detects_existing_dirty_content_edits` | m03313 stmt_del workspace.py:182 | `test_audit_detects_existing_dirty_content_edits[tracked]` |
| workspace.py:153-158, workspace.py:181 | `test_audit_detects_checkout_mutations` | m03289 stmt_del workspace.py:153 | `test_audit_detects_checkout_mutations[head]` |
| workspace.py:198-258, workspace.py:261-276 | `test_audit_diagnoses_unavailable_baseline` | m03333 stmt_del workspace.py:216 | `test_audit_diagnoses_unavailable_baseline[missing-checkout_missing-False-True]` |
| workspace.py:261-300 | `test_audit_distinguishes_changes_from_unavailability` | m03360 stmt_del workspace.py:280 | `test_audit_distinguishes_changes_from_unavailability[disappear]` |
| workspace.py:198-200 | `test_registration_list_failure_still_stops_snapshot` | m03321 stmt_del workspace.py:200 | `test_registration_list_failure_still_stops_snapshot` |
| checkout_policy.py:28-31 | `test_self_override_does_not_use_retained_fallback_as_confinement_evidence` | m01616 stmt_del checkout_policy.py:31 | `test_self_override_does_not_use_retained_fallback_as_confinement_evidence[fallback0]` |
| workspace.py:226-236, runner.py:643, runner.py:651 | `test_confined_batch_still_blocks_protected_edits` | m03335 stmt_del workspace.py:228 | `test_dsh_output_ancestor_symlink_is_rejected` |
| checkout_policy.py:48-59, workspace.py:239-258, runner.py:351-357, runner.py:642-651 | `test_confined_preflight_retains_unrelated_missing_registration` | m01622 stmt_del checkout_policy.py:54 | `test_unproven_configuration_keeps_unavailable_registration_blocking[nonconfined]` |
| checkout_policy.py:32-45 | `test_unproven_configuration_keeps_unavailable_registration_blocking` | m01620 stmt_del checkout_policy.py:44 | `test_unproven_configuration_keeps_unavailable_registration_blocking[unavailable]` |
| checkout_policy.py:39-41 | `test_unproven_configuration_keeps_unavailable_registration_blocking` | m01619 stmt_del checkout_policy.py:41 | `test_role_deadline_covers_fallback_attempts[4.0]` |
| checkout_policy.py:48-59, workspace.py:226-257 | `test_confined_preflight_rejects_protected_audit_failure` | m01622 stmt_del checkout_policy.py:54 | `test_unproven_configuration_keeps_unavailable_registration_blocking[nonconfined]` |
| runner.py:512-536, adapters/devin.py:49, adapters/devin.py:217-218 | `test_retained_export_with_secrets_is_redacted_before_collection` | m03169 boolop_drop runner.py:534 | `test_retained_export_with_secrets_is_redacted_before_collection` |

## 迷いの一覧

`integration`（#236）の一覧で先頭に並べる（#228 の「迷うもの」）。どれも残した。

- 棚卸しの迷い（12 件）: `test_runner.py` の `test_unproven_capability_is_unsupported`、`adapters/dsh/test_adapter.py` の `test_unallowlisted_key_is_not_inherited`・`test_skill_source_is_used_in_stdin`、`adapters/dsh/test_identity.py` の `test_rejects_unbound_or_invalid_records` の symlink・directory_link（2 件）、`test_workspace.py` の `test_git_common_dir_of_a_linked_worktree_is_the_main_git_directory`、`test_checkout_policy.py` の `test_unproven_configuration_keeps_unavailable_registration_blocking[truthy]`、`test_config.py` の `test_self_cannot_be_mixed_or_used_as_fallback` の空の agents のケース、`adapters/cursor/test_cursor.py` の `test_prepare_read_only_role_allows_shell_without_cursor_sandbox`・`test_prepare_rejects_ambiguous_second_model_override`、`adapters/devin/test_adapter.py` の `test_export_error_fields_override_answer`（2 件。`_export_failure` を外しても結果が response_failed のままで、守りを検出しない。直すかは #236 で決める）
- 監査の迷い（変異 9 個、戻したテスト 6 件。うち 1 件は S の m00671 と同じテスト）: 上の「lost の判定」の迷いの行（`cursor.py:155`、`skills.py:33-34`、`dsh.py:142`、`process.py:270`、`runner.py:367・457`）
- PR #247 のサイクル 1 の迷い（1 件、D-230-14）: `adapters/dsh/test_adapter.py` の `test_invalid_intermediate_event_is_not_ignored` の tool_call のケース（v0070・m01167）

## 申し送り（`integration`（#236）へ）

- 行数は 68.9% で 1/3 に届かない。行数のための fixture の共通化（git の repository の写し: `test_runner.py`・`test_review_regressions.py`・`adapters/*/conftest.py` など、Devin の export のよく似たテスト）はこの子では行っていない（D-230-11）
- `tools/agent_runner/tests/conftest.py` の `supervisor_bootstrap` が返す `configure(startup)` の `startup` は、消したテスト（`test_supervisor_rejects_unreadable_original_environment`）だけが使っていた。残すテストの型注釈（`Callable[[str], None]`）まで変わるので整理していない（D-230-10）
- 重さが高の守りで、基準にも決定的なテストが無いもの: `process.py:77`（anchored の条件。数値の PGID を識別にしない。m02745 は基準のテストの全体でも検出しない）、`process.py:94`（子孫の探索。m02658 は、前のテストが残したプロセスで後のテストが失敗する形でしか検出しない）。`process.py:284`（終了時の stdin の close、m02574）も基準が検出しない
- 基準のテストも検出しない変異が 457 個ある（守りの穴の候補。この子の範囲外。一覧は監査の記録 `res/main-v1.jsonl` の `survived`）。PR #247 のサイクル 1 で足した値の緩和・状態の差し替えでも 137 個（`c1/res/phaseB.jsonl` の `survived`）、キーワード引数の値の差し替えでも 16 個（`c1/res/kwargB.jsonl`。`hooks.py:49` の `secrets=()`、`runner.py:126` の `follow_symlinks=True` など）。うち `runner.py:604` の停止の集合から interrupted を外す変異（m03253）と `runner.py:555`（m03117・m03172・m03173）は、担当が報告した中断で fallback を始めないことを runner の層で確かめるテストが基準にも無いことを示す
- 監査の道具（PID 名前空間での実行、子の Python も含めたテストごとの coverage、テスト 1 件 30 秒の上限、残す → 消すの順の 1 回の走査）は `/workspaces/reso-world/tmp/agents/issue-230.fuotebjq/audit/bin/` にある。#231・#233・#236 でも使える
- `test_checkout_policy.py` の ruff の F811（`test_runner.py` から import した fixture の `repository` を引数の名前で使う形）は基準からある（基準 10 件、今は 8 件）

## 検証

- 領域: `uv run --locked pytest tools/agent_runner`（`--basetemp` は `/tmp` の `mktemp -d`）。`c13ea67` で 365 件が通った（34 秒）。PR #247 のサイクル 1 の修正の commit で 371 件が通った（戻した 5 件の検出は、レビュー修正の Spec の「実行した検証と結果」）
- 未使用の名前: `uv run --no-project --with ruff==0.17.2 ruff check --no-cache --isolated --select F401,F841,F821,F823 tools/agent_runner` が通る（F811 は基準からある形。「申し送り」）
- 収集の照合: 計画の残す node ID（`retained-final.txt`）と収集の node ID は、関数ごとの件数とパラメータの無いテストで一致した
- 全体の入口（`README.md` の「テスト」）は、最後のコミットの後に実行し、argv・終了コード・ログを PR の本文と検証の記録（`/workspaces/reso-world/tmp/agents/issue-230.fuotebjq/verify/`）に書く

## 受け入れ条件との対応

| Issue の受け入れ | 対応 |
| --- | --- |
| Spec に棚卸しの表がある | 「棚卸しの表」 |
| F（F∩S を除く）・L・D の余り・撤去した経路のテストと、それだけが使っていた fixture・偽の CLI が消えている | commit `4c4a964`（テストと補助）・`c1d8755`（`runtime_supported`）・`c13ea67`（検出しない戻しの取り消し）。PR #247 のサイクル 1 で、S・迷いの 6 件を戻した（D-230-14）。消した補助は「補助・偽の CLI」 |
| 重さが高の守りで代表に絞ったものを、壊したコピーで確かめた | 「守りの確認」（32 項目）と「縮めた木での確認」 |
| 残したテストが通る | 「検証」（PR #247 のサイクル 1 の修正の後は 371 件） |
| 前後の件数・行数を Spec と Issue に書く | 「計測」。Issue には完了のコメントで書く |

## 補助・偽の CLI

| 消したもの | 理由 |
| --- | --- |
| `adapters/claude_code/fake_cli.py`・`adapters/pi/fake_launcher.py`、両方の `conftest.py` の `repository`・`outside_runner` の fixture と `test_adapter.py` の `pytestmark` | 起動するのは消した e2e（`test_end_to_end_launch_and_collection`）だけ。`context` の fixture の `command` は、単体のテストが起動しないので `["unused"]` にした（残すテストは `spec.argv` の先頭が `command` と一致することだけを確かめる） |
| `adapters/cursor/test_integration.py`・`adapters/cursor/fake_cli.py` | 全てのテストを消した（e2e の代表は codex の `test_integration.py` に残す） |
| `adapters/test_skills.py` | 唯一のテストが L |
| `adapters/codex/fake_cli.py` の `--fail-auth`・`--fail-bad`・`--nonzero`・`--fail-approval`・`--truncate` と reconnect の terminal・no-message・no-completion | 残す 2 ケース（success・turn-failed）は使わない |
| `adapters/devin/fake_cli.py` の `--fake-stderr`・`--fake-exit` | 残すテストは `--fake-capture`・`--fake-export`・`--fake-stdout` だけを使う |
| `adapters/dsh/fake_cli.py` の場面（auth・nonzero・malformed・missing-session・mismatched-session・descendant・approval・approval-program・read の 10 件・ptc の全て・spill・pytest（fixture なし）・fifo・tmp-fifo・home-link・tmp-link・root-link） | 残すテストが使う場面は success・native-fence・hardlink・github-token・home-cache・symlink・tmp-symlink・tmp-hardlink・pytest-fixtures・hang・parent-input だけ |
| `adapters/dsh/ptc_tool_results.json` の cancelled・unavailable・tool_approval・read・read_403・caught_rejection | 残すテストが読むのは rejected・captured_only だけ（残す 2 項目は元の内容のまま） |
| `test_review_regressions.py` の `ImmediateExitAdapter`・`HugeReceipt`（`FifoAdapter` は PR #247 のサイクル 1 で戻した）、`test_cli.py` の `ListingAdapter`・`command`、`test_config.py` の `request_data`、`test_parser_regressions.py` の `_JSONL`、`test_checkout_policy.py` の all-self の分岐 | 消したテスト・ケースだけが使っていた（モジュールの名前の参照の走査で参照 0 件） |
| 未使用になった import 40 件 | ruff 0.17.2（一時の環境、`--select F401`）で消した |

## 棚卸しの表

分類は F・F∩S・L・S・D・撤去・迷い、重さ（S）は高・中・低（#228 の「守りの重さ」）。理由は棚卸しの記録（6 つの担当の分類の要点。L は気付ける経路、S は防ぐ損害、D は代表）で、全文は監査の記録 `final-inventory.json`（コミットしない）にある。「監査で戻した」は、変異の監査で lost の S・迷いを検出していたので戻したテスト（棚卸しの分類を付けて、戻した理由を書いた）。自動で付く ID（値の位置から付く `events12` など）は、ケースを減らすと番号が詰まる（関数ごとの件数は、計画と収集で一致することを確かめた）。

#### `adapters/claude_code/test_adapter.py`（40 件 → 22 件）

| テスト（群） | 分類 | 理由・防ぐ損害（重さ） | 扱い |
| --- | --- | --- | --- |
| `test_prepare_builds_stream_json_launch` | S（中） | ClaudeCode.prepare の argv と stdin を確かめる。`--model` に設定のモデルを渡すこと（外れると Claude Code の既定のモデルで黙って動く: 中）と、JSON の役割の指示を stdin に足すことを含む | 残す |
| `test_prepare_maps_effort_and_appends_agent_args` | S（中） | effort を `--effort` に渡すことと、`agent.args` を末尾に付けることを確かめる。effort が落ちると既定の推論の強さで黙って動き、args が落ちると利用者が足した引数（`--add-dir` など）が黙って効かない（中） | 残す |
| `test_collect_success_extracts_identity_and_json_payload` | S（中） | 成功の収集の正しく通る例（拒否の群に残す正例）。取り違えると記録が実際と違う（中: 記録の取り違え） | 残す |
| `test_assistant_model_overrides_init_model` | S（低） | init の model（別名）より後の assistant の message.model（実際のモデル）を identity にすることを確かめる。壊れると記録のモデル名が別名のままになる（低: 記録の精度） | 残す |
| `test_collect_success_text_shape` | L | text の役割の正例。text の分岐（claude_code.py:84-85）が壊れると、text の役割の実行がすべて response_failed か例外… | 消す |
| `test_non_object_answer_fails_json_shape` | L | JSON の役割で object でない回答を response_failed にする | 消す |
| `test_json_fence_answer_parses` | L | 前置きの文の後の JSON のコードフェンスを受け付ける正例。壊れるとフェンスの回答が response_failed になり、偽の失敗として現れる | 消す |
| `test_permission_denials_report_awaiting_approval` | S（中） | result に permission_denials があれば、subtype が success でも awaiting_approval にすることを確かめる。外れると、拒否されて必要な操作をできなかった実行を成功と報告する（中: 誤った結果の報告） | 残す |
| `test_error_subtype_reports_response_failed`（`[True]`） | D | 代表: `test_error_subtype_reports_response_failed`。is_error も true のケース | 消す |
| `test_error_subtype_reports_response_failed`（`[False]`） | S（中） | subtype が error なら is_error が false でも失敗にすることを確かめる… | 残す |
| `test_auth_error_text_reports_awaiting_authentication` | S（低） | 失敗した result（is_error）の本文を診断に足し、ログインを求める文を awaiting_authentication にすることを確かめる | 残す |
| `test_missing_result_with_auth_stderr_reports_authentication` | D | 代表: `test_stderr_failure_dominates_plausible_result`。stderr を診断にする同じ経路と同じ `_AUTH` の語（401・Unauthorized・invalid api key）を… | 消す |
| `test_missing_result_reports_response_failed` | S（中） | result イベントの無いストリームを成功にしないことを確かめる（終了コード 0 を成功としない） | 残す |
| `test_garbled_and_non_json_lines_are_skipped` | L | OSC の通知や JSON でない行を無視する正例。壊れて通知の行を壊れたイベントとして扱うと、result の後の行で response_failed になり、偽の失敗として現れる | 消す |
| `test_skill_invocation_alone_does_not_prove_file_read` | S（中） | Skill ツールの呼び出しだけでは skill の版を記録しないことを確かめる（Clau… | 残す |
| `test_init_skill_listing_is_not_load_evidence` | D | 代表: `test_skill_invocation_alone_does_not_prove_file_read`。Claude Code の adapter は skill_versions を一切記録しない（claude_code.py:138-139）ので… | 消す |
| `test_end_to_end_launch_and_collection`（`[0-success]`） | L | 本物の adapter・runner・偽の CLI で成功の一連を通す。壊れると Claude Code の実行がすべて失敗し、初回の利用で明らかに動かない | 消す |
| `test_end_to_end_launch_and_collection`（`[7-response_failed]`） | D | 代表: `test_exit_zero_is_not_a_substitute_for_valid_receipt`。非ゼロ終了を失敗にする runner の判定（runner.py:557-561）の上の層の重なり | 消す |
| `test_prepare_resolves_role_skills_against_work_dir` | S（中） | role.skills と、work_dir 基準で解決した設定の source の SKILL.md の絶対パスを stdin のプロンプトに足すことを確かめる。設定しただけでは版を記録しないことも確かめる | 残す |
| `test_missing_identity_is_not_filled_from_agent_settings` | S（中） | init が無いとき identity を要求の provider・effort で埋めず、session_id・cli_version も null にすることを確かめる。壊れると、観測していない値を実測として記録する（中: 記録の取り違え） | 残す |
| `test_stderr_failure_dominates_plausible_result`（2 件） | S（中） | もっともらしい成功の result があっても、stderr の認証（401・invalid api key）・承認…。外れると、認証・承認で止まった実行を成功と報告する（中） | 残す |
| `test_error_event_dominates_plausible_result`（`[Not logged in-awaiting_authentication]`） | D | 代表: `test_error_event_dominates_plausible_result`。error イベントを診断にする経路は [Internal execution error… | 消す |
| `test_error_event_dominates_plausible_result`（`[Requires approval-awaiting_approval]`） | D | 代表: `test_stderr_failure_dominates_plausible_result`。`_APPROVAL` の語は test_stderr_failure_dominates_plausible_result[Workspace trust ...] が… | 消す |
| `test_error_event_dominates_plausible_result`（`[Internal execution error-response_failed]`） | S（中） | result の前の error イベントは、認証・承認の語が無くても失敗にすることを確かめる | 残す |
| `test_successful_answer_discussing_authentication_is_valid` | L | 成功の result の本文の認証の語を診断にしない正例。壊れると偽の失敗（awaiting_authentication）として現れる | 消す |
| `test_interrupted_result_is_not_success`（3 件） | S（中） | 中断を示す subtype（interrupted・aborted・cancelled）を interrupted にすることを確かめる。interrupted は runner が fallback を始めない状態で、response_failed に取り違えると… | 残す |
| `test_is_error_overrides_success_subtype` | S（中） | subtype が success でも is_error が true なら失敗にすることを確かめる | 残す |
| `test_empty_text_result_fails` | L | text の役割で空白だけの回答を失敗にする | 消す |
| `test_malformed_result_does_not_complete_stream` | D | 代表: `test_missing_result_reports_response_failed`。途中で切れた result の行は壊れたイベントになり、result が無い扱いになる | 消す |
| `test_incomplete_assistant_prose_is_not_auth_diagnostic` | S（低） | result の無いストリームの assistant の文に認証の語があっても awaiting_authentication にしない… | 残す |
| `test_failed_skill_invocation_does_not_record_hash` | D | 代表: `test_skill_invocation_alone_does_not_prove_file_read`。Claude Code の adapter は skill_versions を記録しないので… | 消す |
| `test_explicit_assistant_error_is_auth_diagnostic` | S（中） | error の項目を持つ assistant のイベントを失敗の経路（診断）にすることを確かめる | 残す |
| `test_later_unfinished_turn_invalidates_earlier_success` | S（中） | 成功の result の後に assistant のイベント（次の未完了のターン）が続けば失敗にすることを確かめる | 残す |
| `test_truncated_event_after_success_invalidates_completion`（2 件） | D | 代表: `test_truncated_event_after_success_invalidates_completion`。切れた行が壊れたイベントになって成功を無効にする同じ経路を [  {] が確かめる（strip の後に同じ `{` の行になる） | 消す |
| `test_truncated_event_after_success_invalidates_completion`（`[  {]`） | S（中） | 成功の result の後の途中で切れた行（先頭に空白のある `{`）を壊れたイベントとして残し、成功を無効にすることを確かめる | 残す |
| `test_malformed_event_before_final_completion_does_not_reuse_stale_result` | L | 壊れたイベントの後に新しい完全な result が来れば、それで成功にする正例（回復）。壊れると偽の失敗として現れる | 消す |

#### `adapters/codex/test_codex.py`（80 件 → 26 件）

| テスト（群） | 分類 | 理由・防ぐ損害（重さ） | 扱い |
| --- | --- | --- | --- |
| `test_prepare_passes_prompt_over_stdin_with_read_only_sandbox` | F∩S（高） | 読み取りのロール（writes=false）を `-s read-only` で起動する権限のフラグ（#230 の F∩S の候補） | 残す |
| `test_prepare_write_role_uses_workspace_write_effort_and_args` | F∩S（高） | 書き込みのロールの sandbox を `workspace-write`（worktree と /tmp だけに書ける）に固定する権限のフラグ | 残す |
| `test_prepare_appends_json_shape_and_skill_instruction` | D | 代表: `test_prepare_tells_model_to_read_configured_skill_source_paths`。skill を codex の参照の形（`$名前`）で prompt に入れる文は、残す … | 消す |
| `test_collect_success_builds_receipt_and_identity` | S（中） | 成功の経路の代表で、残す拒否の群（後の失敗・壊れた行・thread の検査・診断）の正しく通る例（何でも拒否する実装を通さない）。項目の欠落・取り違えはエラーにならない記録の取り違え | 残す |
| `test_collect_text_shape_returns_raw_text` | L | text 形の正しく通る例。壊れると text 形のロールが毎回 response_failed になり、初回の利用で明らかに動かない | 消す |
| `test_collect_turn_failed_is_response_failed` | D | 代表: `test_failure_diagnostics_override_prior_message`。agent_message が無いので、turn.failed の扱いを外しても完了・本文の検査で失敗になり、この場面は turn.failed の守りを単独では確かめていない… | 消す |
| `test_collect_authentication_message_is_awaiting_authentication` | L | stdout が空なので、認証の検出を外しても response_failed になり、違うのは失敗の分類… | 消す |
| `test_collect_missing_agent_message_is_response_failed` | L | agent_message が無いと text が None のままで、本文の検査（cod… | 消す |
| `test_collect_non_dict_json_shape_is_response_failed` | L | JSON でない本文を拒否する検査（codex.py:282-285）を外すと payload が None や文字列の receipt になるが… | 消す |
| `test_collect_embedded_json_object_is_extracted` | D | 代表: `test_collect_nested_json_object_returns_outer_object`。散文に埋めた JSON object を取り出す正しく通る例 | 消す |
| `test_collect_nested_json_object_returns_outer_object` | S（中） | 散文・コードフェンスに包んだ JSON の外側の object を返す正しく通る例 | 残す |
| `test_collect_authentication_words_in_output_do_not_fail` | L | ツールの出力・成功の本文にある認証の語では失敗にしない（過剰な拒否を防ぐ）正しく通る例 | 消す |
| `test_collect_identity_fields_stay_null_without_rollout` | D | 代表: `test_untrusted_thread_id_cannot_select_rollout`。観測できない identity を要求の設定から補わず null にする | 消す |
| `test_collect_skill_versions_hash_successfully_read_skill_files` | S（中） | skill の版の記録の正しく通る例（`/bin/bash -lc 'cat …'` の展開を含む） | 残す |
| `test_collect_skill_path_mentioned_in_message_is_not_recorded` | D | 代表: `test_collect_skill_version_stays_unknown_when_observed_content_differs`。本文の言及は command_execution の出力を持たないので、_read_evidence を緩めても… | 消す |
| `test_collect_unproven_cat_reads_are_not_recorded`（4 件） | D | 代表: `test_collect_skill_version_stays_unknown_when_observed_content_differs`。どの場面も aggregated_output が空で現在のファイルの内容と一致しないので、status・exit_code の検査… | 消す |
| `test_collect_commands_without_unambiguous_read_evidence_are_not_recorded`（2 件） | D | 代表: `test_collect_skill_version_stays_unknown_when_observed_content_differs`。出力がパスの文字列で内容と一致しないので、単純な cat だけを証拠にする検査（codex.py:90-100）を外しても記録されない（検出した変異は例外と偽の失敗だけ） | 消す |
| `test_collect_rollout_without_successful_execution_is_not_read_evidence`（3 件） | D | 代表: `test_collect_skill_version_stays_unknown_when_observed_content_differs`。rollout の prompt の写し・ツールの呼び出し・parsed_cmd は it… | 消す |
| `test_collect_skill_version_stays_unknown_when_observed_content_differs` | S（中） | 読み込みで観測した内容が現在の SKILL.md と違えば版を記録しない（skills.p… | 残す |
| `test_collect_skill_version_stays_unknown_when_file_deleted_after_read` | L | 読んだ後に消えたファイルは verified_versions の OSError の分岐で unknown になる。この分岐を壊すと UnboundLocalError・OSError が collect から出て、runner の _collect が invalid_result にする… | 消す |
| `test_collect_skill_version_stays_unknown_when_observed_content_is_truncated` | D | 代表: `test_collect_skill_version_stays_unknown_when_observed_content_differs`。途中までの出力も `observed != content` の同じ分岐で拒否する | 消す |
| `test_prepare_tells_model_to_read_configured_skill_source_paths` | S（低） | role.skills を codex の参照の形（`$alpha`）と、設定した source の絶対パスの読み込みの指示で prompt に入れる… | 残す |
| `test_failure_diagnostics_override_prior_message`（`[stderr-Not logged in-awaiting_authent…]`） | S（中） | 成功らしい stream（agent_message と turn.completed、終了コード 0）でも、stderr の認証の診断… | 残す |
| `test_failure_diagnostics_override_prior_message`（`[stderr-Approval required-awaiting_app…]`） | S（中） | 成功らしい stream でも stderr の承認の診断（正規表現の選択肢 `approval (?:required\|needed\|pending)`）があれば成功にしない | 残す |
| `test_failure_diagnostics_override_prior_message`（`[stderr-waiting for approval-awaiting_…]`） | S（中） | 承認の正規表現の別の選択肢 `(?:waiting\|awaiting) (?:for )?approval` を、成功を覆す場面で確かめるのはこれだけ… | 残す |
| `test_failure_diagnostics_override_prior_message`（`[stderr-command failed-response_failed]`） | L | 一般的な stderr の出力では失敗にしない正しく通る例（終了コードは runner が見る） | 消す |
| `test_failure_diagnostics_override_prior_message`（3 件） | D | 代表: `test_failure_diagnostics_override_prior_message`。error イベントで成功を無効にする分岐は [error-command failed-response_failed] が確かめる | 消す |
| `test_failure_diagnostics_override_prior_message`（`[error-command failed-response_failed]`） | S（中） | 成功の後の error イベントが先行する本文と完了を無効にする | 残す |
| `test_failure_diagnostics_override_prior_message`（3 件） | D | 代表: `test_failure_diagnostics_override_prior_message`。turn.failed で成功を無効にする分岐は [turn.failed-command failed-response_failed] が確かめる | 消す |
| `test_failure_diagnostics_override_prior_message`（`[turn.failed-command failed-response_f…]`） | S（中） | 成功の後の turn.failed が先行する本文と完了を無効にする | 残す |
| `test_truncated_later_event_does_not_reuse_success`（`[{"type":"item.completed",]`） | S（中） | 成功の後の壊れた JSON らしい行（「{」で始まる）で成功を再利用しない | 残す |
| `test_truncated_later_event_does_not_reuse_success`（`[[{"type":]`） | S（中） | 「[」で始まる壊れた行 | 残す |
| `test_truncated_later_event_does_not_reuse_success`（`[{broken json}]`） | D | 代表: `test_truncated_later_event_does_not_reuse_success`。「{」で始まる壊れた行の同じ分岐 | 消す |
| `test_plain_progress_does_not_invalidate_completion` | L | JSON でない進捗の行では成功を無効にしない正しく通る例。壊れると進捗を出す実行が毎回失敗する（「{」の項を外すと末尾の空行でも全実行が失敗する）ので気付ける | 消す |
| `test_missing_or_unfinished_final_turn_is_failure`（`[]`） | S（中） | turn.completed の無い最後の message を成功にしない。終了コード 0 でも完了の証拠を求める（exit 0 を成功としない） | 残す |
| `test_missing_or_unfinished_final_turn_is_failure`（`[{"type":"turn.started"}\n]`） | D | 代表: `test_latest_turn_cannot_reuse_an_earlier_message`。後続の turn.started が完了を取り消す分岐は代表の tail0 も検出する | 消す |
| `test_untrusted_thread_id_cannot_select_rollout`（`[../foreign]`） | S（中） | CLI の出力の thread_id にパス区切りやワイルドカードがあれば失敗にし、その ID で rollout を探さない。外すと不正な出力を成功にし、session_id を取り違える | 残す |
| `test_untrusted_thread_id_cannot_select_rollout`（5 件） | D | 代表: `test_untrusted_thread_id_cannot_select_rollout`。同じ _THREAD_ID.fullmatch の分岐（検出した変異も [../foreign] と同じ） | 消す |
| `test_rollout_uses_effective_child_environment`（`[CODEX_HOME]`） | S（中） | rollout を子に渡した環境（context.environment）の CODEX_HOME から読み、親の os.environ から読まない。外すと別の CODEX_HOME にある同じ thread の記録から identity を写す（記録の取り違え） | 残す |
| `test_rollout_uses_effective_child_environment`（`[HOME]`） | S（低） | CODEX_HOME が無いときに HOME/.codex から rollout を読む（codex.py:138-139）。雛形の codex の担当は env = ["HOME", "PATH"] でこの経路を通るので、壊れると全ての実行の identity… | 残す |
| `test_rollout_uses_effective_child_environment`（`[empty]`） | D | 代表: `test_rollout_uses_effective_child_environment`。同じ m00469（親の環境を使う）を [CODEX_HOME] も検出する | 消す |
| `test_rollout_cannot_borrow_identity_from_another_session`（`[suffix-collision]`） | D | 代表: `test_rollout_cannot_borrow_identity_from_another_session`。接尾辞が衝突する rollout は session_meta の id も違うので、ファイル名の検査… | 消す |
| `test_rollout_cannot_borrow_identity_from_another_session`（`[metadata-mismatch]`） | S（中） | ファイル名が一致しても session_meta の id・session_id が違う rollout から identity を写さない。外すと別のセッションの model などを記録する（記録の取り違え） | 残す |
| `test_rollout_cannot_borrow_identity_from_another_session`（`[symlink-escape]`） | D | 代表: `test_rollout_cannot_borrow_identity_from_another_session`。同じ resolve の境界の分岐（検出した変異も同じ） | 消す |
| `test_rollout_cannot_borrow_identity_from_another_session`（`[symlink-within-home]`） | S（中） | sessions の外を指す symlink の rollout を読まない。CODEX_HOME の中でも sessions の外なら拒否することを確かめるので、境界を広げる誤りも検出する | 残す |
| `test_latest_turn_cannot_reuse_an_earlier_message`（`[tail0]`） | S（中） | 後続の turn.started が先行の本文を消す | 残す |
| `test_latest_turn_cannot_reuse_an_earlier_message`（`[tail1]`） | D | 代表: `test_latest_turn_cannot_reuse_an_earlier_message`。同じ codex.py:267 の文の None の場合 | 消す |
| `test_latest_turn_cannot_reuse_an_earlier_message`（`[tail2]`） | S（中） | 後続の空の agent_message が古い本文を置き換え、空なので失敗にする（codex.py:262-268）。生成した変異では古い本文は戻らないが、空・文字列でない message を読み飛ばす変更をすると、黙って古い payload で成功する… | 残す |
| `test_configured_source_read_can_prove_version_without_native_directory_name` | L | skills という名前のディレクトリの外にある設定 source でも版を記録できる正しく通る例。壊れても版が unknown になるだけで（検出した変異は例外と記録の欠落）、雛形の codex の source… | 消す |
| `test_invalid_or_ambiguous_thread_event_is_failure`（2 件） | D | 代表: `test_untrusted_thread_id_cannot_select_rollout`。None・数値の thread_id は codex.py:220-221 の同じ分岐で、… | 消す |
| `test_invalid_or_ambiguous_thread_event_is_failure`（`[thread_ids2]`） | S（中） | 異なる 2 つの thread_id を曖昧として失敗にする。外すと最後の ID を session_id にして成功し、記録を取り違える | 残す |
| `test_rollout_sessions_directory_cannot_escape_runtime_home` | S（中） | sessions ディレクトリ自体が CODEX_HOME の外を指すときは rollout を読まない。外すと別の場所の記録から identity を写す | 残す |
| `test_invalid_final_object_cannot_return_a_nested_fragment`（3 件） | L | 空の list・空の dict・list を payload にする変異は、runner … | 消す |
| `test_invalid_final_object_cannot_return_a_nested_fragment`（`[{"outer":{"nested":true},]`） | D | 代表: `test_invalid_final_object_cannot_return_a_nested_fragment`。裸の壊れた JSON は codex.py:59-60 とループの最初の復号の失敗の両方で拒否する（どちらを外しても None） | 消す |
| `test_invalid_final_object_cannot_return_a_nested_fragment`（`[prefix\n{"outer":{"nested":true},]`） | S（中） | 散文の後の壊れた外側の JSON から内側の object を取り出さない（codex.py:63-73 のループの return None）。生成した変異では内側は取り出せない（runner の形の検査で止まる形だけ）が、復号に失敗した後も次の「{」を探す変更をすると… | 残す |
| `test_invalid_event_type_is_response_failed_with_identity`（`[False-bad_type0]`） | S（中） | 監査で戻した: type が文字列でない行を有効なイベントとして扱うと、壊れた出力（_malformed_events）として失敗にせず、type の壊れた turn.failed・error を見落として success を返し得る（失敗を成功と報告する）（m00452） | 残す |
| `test_invalid_event_type_is_response_failed_with_identity`（`[False-bad_type1]`） | L | 成功の前に壊れた行があるだけで本文が無いので、検査を外しても失敗になる（検出した変異は例外と値の欠落） | 消す |
| `test_invalid_event_type_is_response_failed_with_identity`（2 件） | D | 代表: `test_truncated_later_event_does_not_reuse_success`。成功の後の type が文字列でない行を壊れた行として失敗にする分岐（codex.py:42・176・274）は、残す truncated の場面が同じ変異を検出する | 消す |
| `test_invalid_type_preserves_failure_diagnostic_precedence`（4 件） | L | type が不正な行と認証・承認の診断が両方あるときの分類の優先を確かめる。どちらの分類でも失敗で、違うのは分類だけ（#150 の Spec の GPT-M2 と同じ判断） | 消す |

#### `adapters/codex/test_integration.py`（12 件 → 2 件）

| テスト（群） | 分類 | 理由・防ぐ損害（重さ） | 扱い |
| --- | --- | --- | --- |
| `test_success_with_real_adapter_and_fake_cli` | D | 代表: `test_reconnect_requires_fresh_completion_and_clean_process_exit`。runner が子の環境（CODEX_HOME）を AdapterContext.environment で adapter に渡し（runner.py:476-484）… | 消す |
| `test_authentication_failure_maps_to_awaiting_authentication` | L | 偽の CLI が stderr に認証の誤りを出し、終了コード 1 で終わる | 消す |
| `test_event_error_maps_to_response_failed` | L | error イベントだけで agent_message が無いので、どの検査を外しても成功にならない… | 消す |
| `test_plausible_response_does_not_hide_failure`（`[args0-response_failed]`） | D | 代表: `test_exit_zero_is_not_a_substitute_for_valid_receipt`。成功らしい stream で終了コード 7（--nonzero） | 消す |
| `test_plausible_response_does_not_hide_failure`（`[args1-awaiting_approval]`） | L | --fail-approval は終了コード 1 なので runner が成功にしない | 消す |
| `test_plausible_response_does_not_hide_failure`（`[args2-response_failed]`） | D | 代表: `test_truncated_later_event_does_not_reuse_success`。--truncate: 成功の後の壊れた行（codex.py:274 の _malformed_events(stdout)） | 消す |
| `test_reconnect_requires_fresh_completion_and_clean_process_exit`（`[success-0-True]`） | S（中） | 監査で戻した: 文字列・dict・list 以外の値（数・真偽値・null）を None にするので、成功の payload と identity の数・真偽値が伏せ字の処理で黙って null に変わる（記録の取り違え・データの消失）（m02790） | 残す |
| `test_reconnect_requires_fresh_completion_and_clean_process_exit`（`[terminal-0-False]`） | D | 代表: `test_failure_diagnostics_override_prior_message`。成功の後の error で終わる（codex.py:247 の "error"） | 消す |
| `test_reconnect_requires_fresh_completion_and_clean_process_exit`（`[no-completion-0-False]`） | D | 代表: `test_missing_or_unfinished_final_turn_is_failure`。新しい message の後に turn.completed が無い | 消す |
| `test_reconnect_requires_fresh_completion_and_clean_process_exit`（`[no-message-0-False]`） | D | 代表: `test_latest_turn_cannot_reuse_an_earlier_message`。error の後に新しい message が無いまま turn.completed | 消す |
| `test_reconnect_requires_fresh_completion_and_clean_process_exit`（`[turn-failed-0-False]`） | S（中） | 再接続の error の後に turn.failed があれば、新しい message と turn.completed が来ても成功にしない | 残す |
| `test_reconnect_requires_fresh_completion_and_clean_process_exit`（`[success-7-False]`） | D | 代表: `test_exit_zero_is_not_a_substitute_for_valid_receipt`。終了コード 7 で成功にしない runner の分岐（runner.py:559-561） | 消す |

#### `adapters/cursor/test_cursor.py`（51 件 → 24 件）

| テスト（群） | 分類 | 理由・防ぐ損害（重さ） | 扱い |
| --- | --- | --- | --- |
| `test_prepare_reads_prompt_from_stdin_and_trusts_worktree` | S（中） | 監査で戻した: 依頼文（作業範囲の指示と依頼）を stdin から外しても起動は成功し、担当は依頼の無いまま JSON の回答（空の指摘など）を返せる。もっともらしい誤った成功として残る（m00671・m00709） | 残す |
| `test_prepare_read_only_role_allows_shell_without_cursor_sandbox` | 迷い（中） | #230 の F∩S の候補（cursor の `--sandbox disabled`、#201）。権限を決める固定値として F∩S か、気付けるので L か決められないので残す | 残す |
| `test_prepare_write_role_forces_and_effort_uses_bracket` | F∩S（高） | 書き込みのロール（writes=true）には `--sandbox` を付けず、利用者の sandbox.mode に従わせる（#201） | 残す |
| `test_prepare_appends_json_shape_and_skill_instruction` | D | 代表: `test_prepare_tells_model_to_read_configured_skill_source_paths`。skill の名前を prompt に入れる文は、残す test_prepare_tell… | 消す |
| `test_collect_success_builds_receipt_and_identity` | S（中） | 成功の経路の代表で、残す拒否の群（後の壊れた行・失敗の result・error・後の応答・診断）の正しく通る例 | 残す |
| `test_collect_result_is_error_is_response_failed` | D | 代表: `test_collect_later_corruption_or_failure_cannot_reuse_success`。is_error が true で subtype も失敗なので、cursor.py:206 の条件の 1 項を外しても他の項で失敗になる（この場面は項を単独では確かめない） | 消す |
| `test_collect_trust_required_is_awaiting_approval` | L | result が無いので、承認の検出を外しても response_failed になり、違うのは分類だけ | 消す |
| `test_collect_authentication_is_awaiting_authentication` | L | stdout が空なので、認証の検出を外しても response_failed になり、違うのは分類だけ | 消す |
| `test_collect_auth_words_in_prompt_echo_and_result_do_not_fail` | L | prompt の写し・成功の result にある認証の語では失敗にしない（過剰な拒否を防ぐ）正しく通る例 | 消す |
| `test_collect_nested_json_result_returns_outer_object` | S（中） | 散文に包んだ JSON の外側の object を返す正しく通る例 | 残す |
| `test_collect_missing_result_event_is_response_failed` | L | result が無いとき、検査（cursor.py:210）を外すと _json_object(None) が AttributeError を投げ… | 消す |
| `test_collect_non_dict_json_shape_is_response_failed` | L | JSON でない result を拒否する検査（cursor.py:212-215）を外すと payload が None や文字列になるが… | 消す |
| `test_collect_text_shape_returns_raw_text` | L | text 形の正しく通る例。壊れると text 形のロールが毎回失敗する（payload の代入を外すと NameError） | 消す |
| `test_collect_skill_versions_from_successful_read_completion` | S（中） | readToolCall の完了から版を記録する正しく通る例 | 残す |
| `test_collect_skill_path_mentioned_in_text_is_not_recorded` | D | 代表: `test_collect_skill_version_stays_unknown_when_observed_content_differs`。user・assistant の本文の言及は tool_call の結果の content を持たないので… | 消す |
| `test_collect_incomplete_or_failed_reads_are_not_recorded`（2 件） | D | 代表: `test_collect_skill_version_stays_unknown_when_observed_content_differs`。開始だけ（subtype が started）・失敗（error のある result）の読み込みは… | 消す |
| `test_collect_incomplete_or_failed_reads_are_not_recorded`（2 件） | L | result・success の dict の検査（cursor.py:86-91）を外すと None.get の AttributeError が collect から出て… | 消す |
| `test_collect_shell_path_mention_is_not_recorded` | L | readToolCall の検査（cursor.py:82-84）を外すと None.get の AttributeError で invalid_result になる | 消す |
| `test_collect_structured_prompt_echo_is_not_read_evidence` | D | 代表: `test_collect_skill_version_stays_unknown_when_observed_content_differs`。prompt の写しは tool_call ではなく内容も持たないので、どの検査を外しても記録されない | 消す |
| `test_collect_reading_skill_backup_does_not_record_unread_skill` | S（中） | 読んだファイルが `**/skills/**/SKILL.md` でなければ（SKILL.md.bak）、親のディレクトリの名前の skill の版として記録しない | 残す |
| `test_collect_skill_version_stays_unknown_when_read_range_is_partial` | D | 代表: `test_collect_skill_version_stays_unknown_when_read_limit_is_exceeded`。部分の読み込みは記録しない | 消す |
| `test_collect_skill_version_stays_unknown_when_read_limit_is_exceeded` | S（中） | CLI が上限超過（exceededLimit）を報告した読み込みは、返った内容が現在のファイルと一致しても版を記録しない | 残す |
| `test_collect_skill_version_stays_unknown_when_content_is_missing` | D | 代表: `test_collect_skill_version_stays_unknown_when_observed_content_differs`。content が無ければ verified_versions に比べる内容が無く、型の検査（cursor.py:95）を外しても記録されない | 消す |
| `test_collect_skill_version_stays_unknown_when_range_evidence_is_missing` | L | readRange の dict の検査（cursor.py:100-101）を外すと None.get の AttributeError で invalid_result になる | 消す |
| `test_prepare_tells_model_to_read_configured_skill_source_paths` | S（低） | role.skills と、設定した source の絶対パスの読み込みの指示を prompt に入れる… | 残す |
| `test_prepare_keeps_native_fallback_when_no_configured_source_exists` | 迷い | 監査で戻した: is_file の検査を外すと、最初の source にある存在しない <source>/<name>/SKILL.md を採用し、prompt_lines…（m01610・m01572） | 残す |
| `test_collect_unobserved_identity_is_not_copied_from_settings` | S（中） | init の無い出力では identity を要求の設定（model・effort）から補わず、全て null にする（interfaces.rst・cursor.rst の規則）。生成した変異では壊れないが、補う変更はエラーにならない記録の取り違え（要求したモデルが動いたと記録する） | 残す |
| `test_collect_later_corruption_or_failure_cannot_reuse_success`（6 件） | S（中） | 成功の result の後の行で、先行の成功を再利用しない。6 つの場面はそれぞれ別の条件の部分を確かめる: 「{」で始まる壊れた行、「[」で始まる壊れた行（startswith の要素「[」）、result の文字列が無い result… | 残す |
| `test_collect_plain_progress_after_success_is_ignored` | L | JSON でない進捗の行では成功を無効にしない正しく通る例。壊れると進捗を出す実行が毎回失敗するので気付ける | 消す |
| `test_collect_invalid_outer_json_cannot_be_replaced_by_nested_object`（`[{"outer": {"ok": true}]`） | S（中） | 壊れた外側の JSON から内側の object を取り出さない（cursor.py:53-55 とループの return None）。生成した変異では内側は取り出せないが、復号に失敗した後も次の「{」を探す変更をすると、空でない dict として runner の検査も通り… | 残す |
| `test_collect_invalid_outer_json_cannot_be_replaced_by_nested_object`（`[[{"ok": true}]]`） | D | 代表: `test_collect_invalid_outer_json_cannot_be_replaced_by_nested_object`。list の全体は cursor.py:50-52 で None にし、その文を外しても cursor.py:54-55 が「[」で始まる値を拒否する（二重の検査） | 消す |
| `test_collect_invalid_outer_json_cannot_be_replaced_by_nested_object`（`[]`） | L | 空の result は _json_object が None にし、検査を外しても pa… | 消す |
| `test_collect_failure_diagnostics_override_plausible_result`（2 件） | S（中） | 成功の result（終了コード 0）でも、stderr の認証の診断（`not logged in`）・trust の診断…。2 つの場面は別の分岐と正規表現の選択肢を確かめる | 残す |
| `test_prepare_rejects_ambiguous_second_model_override` | 迷い（低） | ブラケットつきの model と別の effort を一緒に指定すると起動の準備で拒否する（ValueError → runner の launch_failed）。CLI の挙動を確かめていないので S か L か決められない | 残す |
| `test_collect_skill_version_requires_exact_current_read_content`（2 件） | D | 代表: `test_collect_skill_version_stays_unknown_when_observed_content_differs`。返った内容が現在のファイルと違えば記録しない（skills.py の verified_versions の `observed != content`） | 消す |
| `test_collect_failed_result_subtype_supplies_diagnostic`（2 件） | L | 失敗の result の本文を診断に入れて認証・承認に分類する | 消す |
| `test_later_response_requires_its_own_result`（`[False-later0]`） | S（中） | 成功の result の後に assistant の応答が出たら、新しい result が出るまで成功にしない。外すと古い payload で黙って成功する | 残す |
| `test_later_response_requires_its_own_result`（`[False-later1]`） | S（中） | 成功の result の後に新しい system/init（新しいセッション）が出たら、その応答の result を求める（cursor.py:196-197 の init の項） | 残す |
| `test_later_response_requires_its_own_result`（`[True-later0]`） | D | 代表: `test_later_response_requires_its_own_result`。新しい応答の後の新しい result を採用する正しく通る例の重複 | 消す |
| `test_later_response_requires_its_own_result`（`[True-later1]`） | S（中） | 新しい init の後に新しい result が出れば、その payload と最後の init の identity を採用する正しく通る例 | 残す |
| `test_notification_after_result_is_harmless` | L | init でない system の通知・進捗の行では成功を無効にしない正しく通る例。init の項を外して全ての system の event で result を消すと偽の失敗になるので気付ける | 消す |

#### `adapters/cursor/test_integration.py`（9 件 → 0 件）

| テスト（群） | 分類 | 理由・防ぐ損害（重さ） | 扱い |
| --- | --- | --- | --- |
| `test_success_with_real_adapter_and_fake_cli` | L | 本物の adapter と偽の CLI の成功の経路。偽の CLI は `-p`・`--trust`・stream-json・stdin の prompt を assert するので… | 消す |
| `test_authentication_failure_maps_to_awaiting_authentication` | L | 偽の CLI が stderr に認証の誤りを出し、終了コード 1 で終わる | 消す |
| `test_workspace_trust_maps_to_awaiting_approval` | L | result が無いので、trust の検出が壊れても response_failed になり、違うのは分類だけ | 消す |
| `test_error_result_maps_to_response_failed` | D | 代表: `test_collect_later_corruption_or_failure_cannot_reuse_success`。is_error が true で result の文字列も無い result | 消す |
| `test_read_only_roles_launch_any_cursor_agent_with_shell_and_without_sandbox` | D | 代表: `test_prepare_read_only_role_allows_shell_without_cursor_sandbox`。#201 の読み取りのロールの起動のフラグを、任意の名前・fallback の担当で runner を通して確かめる | 消す |
| `test_success_shaped_output_does_not_hide_failure`（`[args0-response_failed]`） | D | 代表: `test_exit_zero_is_not_a_substitute_for_valid_receipt`。--nonzero: 成功の result で終了コード 9 | 消す |
| `test_success_shaped_output_does_not_hide_failure`（`[args1-response_failed]`） | D | 代表: `test_collect_later_corruption_or_failure_cannot_reuse_success`。--truncate: 成功の後の壊れた行（cursor.py:190） | 消す |
| `test_success_shaped_output_does_not_hide_failure`（`[args2-awaiting_authentication]`） | D | 代表: `test_collect_failure_diagnostics_override_plausible_result`。--late-auth: 成功の result と stderr の認証の診断（終了コード 0） | 消す |
| `test_success_shaped_output_does_not_hide_failure`（`[args3-awaiting_approval]`） | D | 代表: `test_collect_failure_diagnostics_override_plausible_result`。--late-trust: 成功の result と stderr の trust の診断（終了コード 0） | 消す |

#### `adapters/devin/test_adapter.py`（81 件 → 30 件）

| テスト（群） | 分類 | 理由・防ぐ損害（重さ） | 扱い |
| --- | --- | --- | --- |
| `test_prepare_writes_prompt_file_and_maps_flags` | S（高） | Devin.prepare が `--export` に attempt の `export.json`（runner が収集の前に伏せ字にする場所と同じ名前）を渡すこと…。export の場所がずれると、継いだ秘密を含む ATIF の export が伏せ字にされないまま attempt に残り、エラーにならない（高: 秘密情報の漏れ） | 残す |
| `test_prepare_appends_agent_args` | S（中） | `agent.args` が argv の末尾に付くことを確かめる。落ちたり前に回ったりすると、設定した制限が黙って効かず、エラーにならない（中: 設定が黙って無視され、権限が広がりうる） | 残す |
| `test_collect_success_extracts_identity` | S（中） | 成功の収集の正しく通る例（下の拒否の群に残す正例）。取り違えると、レビューの記録が実際と違うモデル名を持つ（中: 記録の取り違え） | 残す |
| `test_collect_success_text_shape` | S（中） | text の役割の正しく通る例 | 残す |
| `test_blank_stdout_fails_even_with_export` | S（中） | export に正しい最終メッセージがあっても、stdout が空なら成功にしないことを確かめる（stdout はその回答で終わらなければならない）。壊れると、出力の途切れた実行を成功と報告する（中: 誤った結果の報告） | 残す |
| `test_missing_export_fails` | S（中） | export が無ければ、stdout にもっともらしい JSON があっても成功にせず、identity も観測しないことを確かめる…。壊れて stdout から回答を拾うと、全メッセージの連結のうち最終でないものを成功として返しうる（中: 誤った結果の報告） | 残す |
| `test_malformed_export_fails` | D | 代表: `test_truncated_later_export_cannot_reuse_completion`。解析できない export を None にする同じ分岐（_export の `except OSError, ValueError`）を… | 消す |
| `test_export_without_agent_message_fails` | D | 代表: `test_incomplete_or_failed_export_does_not_reuse_prior_answer`。export の最後の step が agent でなければ最終メッセージにしない同じ条件… | 消す |
| `test_auth_stderr_reports_awaiting_authentication` | D | 代表: `test_diagnostics_override_plausible_success`。stderr を _failure_status に渡して認証待ちにする同じ経路と同じ `_AUTH` の語（not logged in）を… | 消す |
| `test_workspace_trust_stderr_reports_awaiting_approval` | D | 代表: `test_diagnostics_override_plausible_success`。stderr の承認待ちの分類（`_APPROVAL` の分岐）を、もっともらしい成功の前… | 消す |
| `test_non_object_stdout_fails_json_shape` | L | JSON の役割で、最終メッセージが JSON object でなければ response_failed にする | 消す |
| `test_skill_tool_call_path_alone_does_not_prove_read` | S（中） | ATIF の tool call の引数に SKILL.md のパスがあるだけでは skill の版を記録しないことを確かめる… | 残す |
| `test_end_to_end_launch_and_collection` | L | 本物の Devin adapter・runner・偽の CLI で成功の一連を通す。壊れると Devin の実行がすべて失敗し、初回の利用で明らかに動かない | 消す |
| `test_retained_export_with_secrets_is_redacted_before_collection` | S（高） | 継いだ秘密が最終回答・履歴・tool の引数に入った export を、runner が収集の前に attempt の `export.json` で伏せ字にし… | 残す |
| `test_missing_retained_export_keeps_response_failed` | D | 代表: `test_missing_export_fails`。export の無い実行を response_failed にする adapter の分岐は test_missing_export_fails と同じ | 消す |
| `test_secret_free_multiline_export_is_retained_unchanged` | D | 代表: `test_retained_export_with_secrets_is_redacted_before_collection`。秘密を含まない export を伏せ字の処理が書き換えないことを確かめる | 消す |
| `test_prepare_includes_requested_skills_and_configured_source` | S（中） | role.skills と、設定した source の SKILL.md の絶対パスを、プロンプトのファイルに書くことを確かめる（argv には書かない）。落ちると、担当が指定の skill を使わないか、native の探索で別の版を読んだまま、もっともらしい回答を返す（中: 誤った結果） | 残す |
| `test_identity_never_copies_requested_configuration` | S（中） | export に agent・session_id が無いとき、identity を要求の provider・effort・model で埋めないことを確かめる…。壊れると、観測していない値を実測として記録する（中: 記録の取り違え） | 残す |
| `test_diagnostics_override_plausible_success`（3 件） | S（中） | stdout と export にもっともらしい成功があっても、stderr の認証・承認の診断を優先し、payload を返さないことを確かめる（成功の後の失敗の優先）。[Not logged in] は `_AUTH`、[Approval required]… | 残す |
| `test_stdout_diagnostic_without_answer_is_not_success`（`[Error: not logged in]`） | D | 代表: `test_text_diagnostic_with_valid_export_is_not_success`。export が無く stdout に診断（Error: not logged in）だけがある場面 | 消す |
| `test_stdout_diagnostic_without_answer_is_not_success`（`[Approval required]`） | D | 代表: `test_text_diagnostic_with_valid_export_is_not_success`。export が無く stdout に診断（Approval required）だけがある場面 | 消す |
| `test_success_payload_can_discuss_authentication` | L | 成功した JSON の回答の中の「Authentication」「approval required」を診断にしない（診断は行の先頭の形だけ）ことを確かめる正例。壊れると、正しい回答が awaiting_authentication などの失敗になり、偽の失敗として現れる | 消す |
| `test_truncated_later_stdout_cannot_reuse_completion`（2 件） | S（中） | 回答の後に JSON らしい行（完全でも途中で切れていても）が続く stdout を成功にしないことを確かめる（_plain_tail の startswith の要素）。外れると、後に続く別のイベントや切れた記録を無視して前の回答で成功にする（中: 誤った結果の報告） | 残す |
| `test_truncated_later_stdout_cannot_reuse_completion`（`[{broken json}]`） | D | 代表: `test_truncated_later_stdout_cannot_reuse_completion`。`{` で始まる行という同じ要素を [{"event":] が確かめる | 消す |
| `test_plain_progress_after_json_does_not_invalidate_completion` | S（中） | 回答の後の普通の進捗の行は許すことを確かめる | 残す |
| `test_truncated_later_export_cannot_reuse_completion` | S（中） | 完全な ATIF の JSON の後に切れた記録が続く export を、json.loads で丸ごと拒否して成功にしないことを確かめる | 残す |
| `test_latest_empty_agent_message_cannot_reuse_earlier_answer`（`[]`） | S（中） | 最後の agent の step のメッセージが空なら、前の step の回答を使わないことを確かめる（最後の step だけを最終メッセージにする） | 残す |
| `test_latest_empty_agent_message_cannot_reuse_earlier_answer`（`[ ]`） | D | 代表: `test_latest_empty_agent_message_cannot_reuse_earlier_answer`。空白だけのメッセージは、空の [] と同じ `message.strip()` の条件と同じ経路 | 消す |
| `test_latest_empty_agent_message_cannot_reuse_earlier_answer`（2 件） | L | 文字列でないメッセージ（None・17）。`isinstance(message, str)` が外れると `.strip()` で AttributeError になり… | 消す |
| `test_incomplete_or_failed_export_does_not_reuse_prior_answer`（`[tail0]`） | S（中） | 前に回答の step がある export の最後に user の step が続くとき、前の回答を使わないことを確かめる… | 残す |
| `test_incomplete_or_failed_export_does_not_reuse_prior_answer`（`[tail1]`） | D | 代表: `test_tool_run_final_step_calling_tool_fails`。最後の step が tool call を続けている場合の `step.get("tool_calls")` の条件は… | 消す |
| `test_incomplete_or_failed_export_does_not_reuse_prior_answer`（`[tail2]`） | D | 代表: `test_incomplete_or_failed_export_does_not_reuse_prior_answer`。error の step で終わる場合も、最後の step が agent でない同じ条件（[tail0]）で成功にならない | 消す |
| `test_invalid_final_json_does_not_return_nested_fragment`（2 件） | L | 空の配列・空の object。adapter の検査が外れても、runner が JSON の役割の payload を空でない object に限る… | 消す |
| `test_invalid_final_json_does_not_return_nested_fragment`（2 件） | S（中） | 最終の回答が配列や途中で切れた object のとき、中の入れ子の object を拾って成功にしないことを確かめる（先頭から 1 つの object として読む | 残す |
| `test_nonzero_cli_exit_cannot_succeed_with_valid_artifacts` | D | 代表: `test_exit_zero_is_not_a_substitute_for_valid_receipt`。非ゼロ終了なら正しい成果物があっても失敗にする判定は runner.py:557-561 の 1 か所にあり、adapter は終了コードを見ない | 消す |
| `test_late_diagnostic_or_truncation_after_answer_is_failure`（`[\nError: not logged in-awaiting_authe…]`） | D | 代表: `test_text_diagnostic_with_valid_export_is_not_success`。回答の後の診断の行は、stdout の診断行の走査（同じ _DIAGNOSTIC_LINE の語）で失敗になる | 消す |
| `test_late_diagnostic_or_truncation_after_answer_is_failure`（`[\nError: not logged in-awaiting_authe…]`） | D | 代表: `test_text_diagnostic_with_valid_export_is_not_success`。回答の後の診断の行は、stdout の診断行の走査（同じ _DIAGNOSTIC_LINE の語）で失敗になる | 消す |
| `test_late_diagnostic_or_truncation_after_answer_is_failure`（`[\nApproval required-awaiting_approval…]`） | D | 代表: `test_text_diagnostic_with_valid_export_is_not_success`。回答の後の診断の行は、stdout の診断行の走査（同じ _DIAGNOSTIC_LINE の語）で失敗になる | 消す |
| `test_late_diagnostic_or_truncation_after_answer_is_failure`（`[\nApproval required-awaiting_approval…]`） | D | 代表: `test_text_diagnostic_with_valid_export_is_not_success`。回答の後の診断の行は、stdout の診断行の走査（同じ _DIAGNOSTIC_LINE の語）で失敗になる | 消す |
| `test_late_diagnostic_or_truncation_after_answer_is_failure`（2 件） | D | 代表: `test_truncated_later_stdout_cannot_reuse_completion`。回答の後に `{` で始まる行が続く場面 | 消す |
| `test_fenced_json_answer`（2 件） | L | JSON のコードフェンスで囲んだ回答を受け付ける正例。壊れるとフェンスの回答が response_failed になり、偽の失敗として現れる | 消す |
| `test_text_diagnostic_with_valid_export_is_not_success`（2 件） | S（中） | stdout が最終の回答で終わり export も正しいとき、その前の診断の行（Error: Not logged in・Approval required）だけが成功を止める。stdout の診断行の走査（devin.py:238-245）を外すか、_DIAGNOS… | 残す |
| `test_text_diagnostic_with_valid_export_is_not_success`（`[json-{"ok": true}-Error: Not logged i…]`） | D | 代表: `test_text_diagnostic_with_valid_export_is_not_success`。役割の形は診断の走査より後でしか使わないので、json のケースは同じ診断の text のケースと同じ経路 | 消す |
| `test_text_diagnostic_with_valid_export_is_not_success`（`[json-{"ok": true}-Approval required-a…]`） | D | 代表: `test_text_diagnostic_with_valid_export_is_not_success`。役割の形は診断の走査より後でしか使わないので、json のケースは同じ診断の text のケースと同じ経路 | 消す |
| `test_export_error_fields_override_answer`（2 件） | 迷い（中） | export の step の `error`・`is_error`（_export_failure、devin.py:159-177）が回答より優先することを意図するテスト。守りは S（エラーの step を含む export を成功にしない）だが、このテストは確かめていない | 残す |
| `test_prepare_does_not_invent_provider_or_effort_flags` | L | provider・effort を Devin の CLI に無い引数として渡さないことを確かめる。作った引数を渡せば、CLI が未知の引数で止まるか無視するかで、黙って損害が残る経路は無い | 消す |
| `test_final_atif_diagnostic_overrides_successful_stdout`（2 件） | S（中） | export の最終メッセージそのものが診断のとき、認証・承認待ちにし payload を返さないことを確かめる | 残す |
| `test_final_atif_diagnostic_overrides_successful_stdout`（`[json-Error: Not logged in-awaiting_au…]`） | D | 代表: `test_text_diagnostic_with_valid_export_is_not_success`。error: の語は stdout の回答の前で確かめる test_text_diagno… | 消す |
| `test_final_atif_diagnostic_overrides_successful_stdout`（`[json-Approval required-awaiting_approval]`） | D | 代表: `test_text_diagnostic_with_valid_export_is_not_success`。approval required の語は test_text_diagnostic_wi… | 消す |
| `test_final_atif_diagnostic_overrides_successful_stdout`（2 件） | D | 代表: `test_final_atif_diagnostic_overrides_successful_stdout`。役割の形は診断の走査に関係しない | 消す |
| `test_final_atif_diagnostic_overrides_successful_stdout`（2 件） | D | 代表: `test_final_atif_diagnostic_overrides_successful_stdout`。役割の形は診断の走査に関係しない | 消す |
| `test_json_role_requires_complete_final_atif_object`（`[{"unfinished":]`） | D | 代表: `test_invalid_final_json_does_not_return_nested_fragment`。途中で切れた object を先頭から読めずに拒否する同じ raw_decode の分岐（devin.py:88-91）を… | 消す |
| `test_json_role_requires_complete_final_atif_object`（3 件） | L | 空の配列・空の object は test_invalid_final_json_does_not_return_nested_fragment の同じ入力と重なり… | 消す |
| `test_final_atif_authentication_topic_is_ordinary_data`（2 件） | L | test_success_payload_can_discuss_authentication と同じ正例（json は入力も同じ）。壊れると偽の失敗として現れる | 消す |
| `test_tool_run_stdout_ending_with_final_answer_succeeds`（`[```json\n{\n  "status": "success",\n …]`） | S（中） | #185・#186 の実際の形（tool を使う途中のメッセージが区切り無しで連結され、最後がフェンスの回答）の stdout と export で成功にする正例 | 残す |
| `test_tool_run_stdout_ending_with_final_answer_succeeds`（`[{"ok": true}-payload1]`） | L | 同じ経路をフェンスの無い回答で通す正例。壊れると偽の失敗として現れる | 消す |
| `test_tool_run_answer_repeated_earlier_succeeds` | L | 同じ回答が前にも出る stdout で、最後の出現（rfind）を回答とする正例。壊れると偽の失敗として現れる | 消す |
| `test_tool_run_with_truncated_final_answer_fails` | D | 代表: `test_invalid_final_json_does_not_return_nested_fragment`。フェンスの中で途中で切れた最終の回答を、先頭から 1 つの object として読めずに拒否する同じ raw_decode の分岐（devin.py:88-91） | 消す |
| `test_tool_run_stdout_not_ending_with_final_answer_fails`（2 件） | D | 代表: `test_blank_stdout_fails_even_with_export`。回答が stdout に揃っていない（途中で切れる・届かない）ので rfind が見つけない `index < 0` の条件 | 消す |
| `test_tool_run_stdout_not_ending_with_final_answer_fails`（`[```json\n{\n  "status": "success",\n …]`） | D | 代表: `test_truncated_later_stdout_cannot_reuse_completion`。回答の後に `{` で始まる行が続く、test_truncated_later_stdout_cannot_reuse_completion[{"event":] と同じ要素 | 消す |
| `test_tool_run_stdout_not_ending_with_final_answer_fails`（`[{"ok": true}-Python 3.14 allows unpar…]`） | S（中） | 回答の行の後ろに文字が続く（stdout の最後の JSON が回答そのものでない）とき成功にしないことを確かめる。外れると、回答に続けて別の内容を出した stdout を成功にする（中） | 残す |
| `test_tool_run_final_step_calling_tool_fails` | S（中） | 最後の agent の step がまだ tool call を続けているなら、そのメッセージを最終の回答にしないことを確かめる | 残す |
| `test_end_to_end_tool_run_collects_final_answer` | L | #188 の形を runner と偽の CLI で通す成功の一連。解析は単体の tool run のテストが確かめ、壊れると偽の失敗（response_failed）として現れる | 消す |
| `test_tool_run_answer_whitespace_differs_from_stdout` | L | export の最終メッセージの前後の空行を除いて stdout と比べる正例。壊れると、空行の付いた回答が response_failed になり、偽の失敗として現れる | 消す |

#### `adapters/dsh/test_adapter.py`（170 件 → 48 件）

| テスト（群） | 分類 | 理由・防ぐ損害（重さ） | 扱い |
| --- | --- | --- | --- |
| `test_adapter_cache_paths_are_writable_with_its_scoped_runner` | L | 壊れると内側の bash の sandbox で HOME（uv の cache・venv）への書き込みが Read-only file system になり… | 消す |
| `test_runtime_is_registered` | L | dsh が登録から外れると、DSH の試行がすべて unsupported になり、初回の利用で明らかに動かない | 消す |
| `test_arbitrary_write_grants_are_rejected_before_launch_state` | L | 誤った入力で ValueError を投げることだけを確かめる。検査が壊れても adapter は sandbox_write_paths をどこにも mount しないので柵は広がらず… | 消す |
| `test_dsh_disk_receipt_cannot_override_failed_jsonl` | S（中） | DSH の試行に receipt.json があれば invalid_result にする。壊れると、JSONL が失敗した試行でも書かれた receipt の success と偽の payload をそのまま採る（失敗を成功と報告する） | 残す |
| `test_tmp_launch_script_and_shared_environment_are_visible_readonly` | D | 代表: `test_tmp_parent_review_inputs_are_readonly_in_native_and_inner_bash`。/tmp に隠れた CLI と sys.prefix を読み取り専用で戻すこと | 消す |
| `test_tmp_parent_review_inputs_are_readonly_in_native_and_inner_bash` | S（高） | 親が作った PR の snapshot・bundle と親の checkout の .gitignore を…。壊れると担当が親の入力や親の checkout を書き換えられる（sandbox の境界、誤った対象への書き込み） | 残す |
| `test_ordinary_prompt_without_parent_descriptor_is_unchanged`（5 件） | L | parent_pr_data の無い依頼文はレビューの入力として扱わないこと。壊れると普通の依頼文で parent_review_read_paths が ValueError… | 消す |
| `test_invalid_parent_review_input_is_rejected_before_launch`（4 件） | S（高） | 検査を通らない親の入力では起動前に止める | 残す |
| `test_invalid_parent_review_input_is_rejected_before_launch`（8 件） | L | 壊れても後段が必ず止める。bundle: bundle は検証した snapshot の隣の固定のパスで、変わった中身は load の digest の検査… | 消す |
| `test_prepare_isolates_state_and_passes_config_not_credentials`（2 件） | S（高） | 資格情報を argv と patch のファイルに出さない、apiKeyEnv を元の名前と別の参照にして project の .env・共有の資格情報へ戻らない… | 残す |
| `test_missing_bwrap_prevents_launch_state` | S（高） | #230 の残す S の例（bwrap が無いときに止まる） | 残す |
| `test_unallowlisted_key_is_not_inherited` | 迷い（高） | 許可リストに無い COMMANDCODE_API_KEY を担当に渡さない（環境変数の許可リスト）。壊れても本番では runner の許可リストが同じ値を落とすので、S（防御の重ね）か重複かを決められない | 残す |
| `test_skill_source_is_used_in_stdin` | 迷い（低） | 設定したスキルの指示を stdin の依頼文に付けること。一方、今の雛形の役割はすべて skills = [] で DSH に skill_sources も無く、今の設定では影響が出ないので L との間で決められない | 残す |
| `test_unsupported_launch_options_are_rejected`（3 件） | L | 誤った入力で ValueError を投げることだけを確かめる。provider が None・未知: 検査が壊れても _KEYS[provider] の KeyError で prepare が失敗し launch_failed になる | 消す |
| `test_collector_binds_stdout_session_to_observed_model` | D | 代表: `test_success_payload_and_observed_identity_only`。stdout の sessionId で試行の session log を読み、要求した値ではなく観測した provider・model・effort を identity にする | 消す |
| `test_missing_identity_discards_success_payload` | S（中） | session log が無いときは success と payload を捨てる。壊れると、観測したモデルの分からない成功を採る（誤った結果・記録の欠落） | 残す |
| `test_missing_identity_preserves_known_failure`（`[MISSING_CREDENTIAL-awaiting_authentication]`） | S | PR #247 のサイクル 1 で戻した（D-230-14）: log が無いときに分類を置き換えない守り（`dsh_identity.py:57-58`）の代表。壊れると担当が報告した中断も response_failed になり、fallback の担当が起動する（m01951・m01901） | 残す |
| `test_missing_identity_preserves_known_failure`（`[APPROVAL_REQUIRED-awaiting_approval]`） | D | 代表: 同じ関数の MISSING_CREDENTIAL のケース（同じ分岐の値違い） | 消す |
| `test_unreadable_identity_keeps_the_classified_state`（`[reason0-awaiting_authentication]`） | D | 代表: `test_unreadable_identity_keeps_the_classified_state`。分類した状態が awaiting_authentication のケース | 消す |
| `test_unreadable_identity_keeps_the_classified_state`（`[None-success]`） | S（低） | 読めない identity で状態を response_failed に置き換えたとき、分類した状態（success）を reported_state に残す（#212）。壊れても失敗の判定は変わらず、診断の記録が欠けるだけ（統計・表示の誤り） | 残す |
| `test_readable_identity_reports_no_replaced_state` | L | 置き換えないときは reported_state が None。初期化の文が壊れると NameError で collect が落ち、runner が invalid_result にする（すべての試行で明らかに失敗する） | 消す |
| `test_mismatched_identity_discards_success_payload` | S（中） | session の assistant の model が request header の route と違うとき、success と payload を捨てる。壊れると、どのモデルの回答か確かめられない結果を成功として採る（記録の取り違え） | 残す |
| `test_changed_route_with_matching_response_discards_payload`（2 件） | S（中） | 1 つの session の中で provider・reasoningEffort が変わった（応答は header と一致）ときに捨てる。壊れると、途中で経路が変わった実行を最後の経路だけに帰属させる（記録の取り違え） | 残す |
| `test_changed_route_with_matching_response_discards_payload`（`[model]`） | D | 代表: `test_rejects_unbound_or_invalid_records`。model の要素 | 消す |
| `test_success_payload_and_observed_identity_only`（2 件） | S（中） | [json-{"ok":true}]: 成功の payload と、観測した identity（session_id・provider・model・effort…。要求した値を identity に写すと記録の取り違え | 残す |
| `test_success_payload_and_observed_identity_only`（7 件） | L | フェンス・前置き・後書き・text の形の成功の取り出し。壊れると payload が取れず response_failed（json）になるか、text の形で dict を返して runner の text の検査… | 消す |
| `test_missing_malformed_or_inconsistent_stream_is_not_success`（14 件） | L | 壊れても必ず失敗になる | 消す |
| `test_missing_malformed_or_inconsistent_stream_is_not_success`（6 件） | S（中） | 壊れた・食い違う stream を成功にしない | 残す |
| `test_missing_malformed_or_inconsistent_stream_is_not_success`（`[events17]`） | D | 代表: `test_missing_malformed_or_inconsistent_stream_is_not_success`。フェンスの中の重複した鍵 | 消す |
| `test_missing_malformed_or_inconsistent_stream_is_not_success`（`[events18]`） | D | 代表: `test_missing_malformed_or_inconsistent_stream_is_not_success`。フェンスの中の NaN | 消す |
| `test_missing_malformed_or_inconsistent_stream_is_not_success`（`[events20]`） | D | 代表: `test_error_reason_overrides_even_nonempty_final`。completed でない turn_end の reason（unknown） | 消す |
| `test_error_reason_overrides_even_nonempty_final`（`[MISSING_CREDENTIAL-awaiting_authentic…]`） | S（中） | turn_end の reason が error なら、空でない final があっても成功にしない。壊れると失敗した turn を成功と報告する | 残す |
| `test_error_reason_overrides_even_nonempty_final`（4 件） | D | 代表: `test_error_reason_overrides_even_nonempty_final`。成功にしない部分は代表（[MISSING_CREDENTIAL]）と同じ dsh.py:163-164 | 消す |
| `test_empty_final_with_missing_credential_is_authentication` | L | 空の final は元から成功にならない。確かめるのは失敗の種類（awaiting_authentication）だけで、壊れても失敗のまま表示が変わるだけ | 消す |
| `test_abort_maps_to_interrupted` | S | PR #247 のサイクル 1 で戻した（D-230-14）: aborted を interrupted にする（`dsh.py:161-162`）。別の失敗になると `runner.py:604` が fallback の担当を起動し、成功として返す | 残す |
| `test_recovered_tool_error_preserves_final_payload`（12 件） | L | #230 の L の例（recovered-tool-error）。回復した読み取りエラーの成功を保つこと | 消す |
| `test_recovered_tool_error_preserves_final_payload`（`[Error: ENOENT: no such file, open 'th…]`） | S（中） | 拒否の群（test_approval_error_in_tool_result_is_not_success など）に残す、正しく通る例（AGENTS.md の D の規則） | 残す |
| `test_api_auth_error_overrides_completed_final`（5 件） | D | 代表: `test_error_events_cannot_be_hidden_by_completed_final`。top-level の error の event は completed の final より優先する | 消す |
| `test_approval_error_in_tool_result_is_not_success`（10 件） | S（中） | DSH の固定版が出す本物の拒否・承認待ちの文を、直接の形で awaiting_approval・payload None にする。壊れると、拒否されて作業できなかった試行を成功として採る（失敗を成功と報告する） | 残す |
| `test_approval_error_in_tool_result_is_not_success`（`[False-Error: the user rejected tool "…]`） | D | 代表: `test_approval_error_in_tool_result_is_not_success`。直接の形で、正規表現の同じ分岐を代表が確かめる | 消す |
| `test_approval_error_in_tool_result_is_not_success`（2 件） | D | 代表: `test_approval_error_in_tool_result_is_not_success`。escalating this command・operation | 消す |
| `test_approval_error_in_tool_result_is_not_success`（13 件） | D | 代表: `test_ptc_producer_output`。PTC で包んだ 13 件（直接の文に固定の接頭辞とスタックを付けたもの） | 消す |
| `test_control_diagnostics_keep_generic_matching`（2 件） | D | 代表: `test_error_events_cannot_be_hidden_by_completed_final`。top-level の error の event（message が APPROVAL_REQUIRED・401） | 消す |
| `test_control_diagnostics_keep_generic_matching`（2 件） | D | 代表: `test_error_reason_overrides_even_nonempty_final`。turn_end の reason の message | 消す |
| `test_control_diagnostics_keep_generic_matching`（2 件） | L | 失敗した stream のときだけ stderr で失敗の種類を決めること | 消す |
| `test_real_denial_is_not_hidden_by_later_recovery`（7 件） | D | 代表: `test_real_denial_is_not_hidden_by_later_recovery`。拒否と回復の順・同じ turn か別の turn か・直接か PTC かの組み合わせ | 消す |
| `test_real_denial_is_not_hidden_by_later_recovery`（`[True-True-False]`） | S（中） | 回復した読み取りエラーと completed の turn_end の後の、別の turn の本物の拒否（PTC の実際の生成物）も awaiting_approval にする | 残す |
| `test_completed_tool_output_is_not_control_diagnostic` | L | completed の tool の結果の中の拒否の文はデータ | 消す |
| `test_approval_classification_does_not_mutate_input_state`（3 件） | D | 代表: `test_approval_classification_does_not_mutate_input_state`。直接・PTC、拒否・回復の残りの組み合わせ | 消す |
| `test_approval_classification_does_not_mutate_input_state`（`[False-True]`） | S（高） | collect は入力（作業の checkout、共有のリンク先の資格情報・backup・cache・tmp の sentinel…。壊れてリンクをたどって書き換えると、利用者のファイルの消失・誤った対象への書き込みが気付かれずに残る | 残す |
| `test_startup_error_without_final_is_classified` | L | final の無い stream は元から成功にならない。確かめるのは失敗の種類（awaiting_authentication）だけ | 消す |
| `test_error_events_cannot_be_hidden_by_completed_final` | S（中） | top-level の error の event があれば、後の completed の final があっても成功にしない。壊れると失敗した実行を成功と報告する | 残す |
| `test_unicode_line_separator_inside_json_string_is_preserved` | L | JSON の文字列の中の U+2028 を行の区切りにしない（split("\n")）。壊れると行が JSON の途中で切れて decode が失敗し、response_failed になる（失敗の向き） | 消す |
| `test_invalid_event_type_does_not_escape_collector`（3 件） | L | unhashable な type・phase と object でない event。壊れると TypeError・AttributeError が collect から漏れ、runner の _collect が invalid_result にする… | 消す |
| `test_invalid_intermediate_event_is_not_ignored`（4 件） | L | event0・1（text・thinking の text が文字列でない）、event3・4（step の turn・step の型） | 消す |
| `test_invalid_intermediate_event_is_not_ignored`（event5、tool_call） | 迷い | PR #247 のサイクル 1 で戻した（D-230-14）: input も truncated も無い tool_call を受け付けない（`dsh.py:140` の `is True` を緩める v0070 を検出する） | 残す |
| `test_invalid_intermediate_event_is_not_ignored`（2 件） | S（中） | event2（未知の status の phase）・event6（未知の tool_result の status）: 知らない形の制御の event を無視しない。壊れると、DSH が新しい phase・status で伝える拒否や中断を読み飛ばして成功にする（失敗を成功と報告する） | 残す |
| `test_invalid_intermediate_event_is_not_ignored`（`[event7]`） | 迷い | 監査で戻した: status が completed・error で result が文字列でない tool_result を受け付ける（m01120） | 残す |
| `test_documented_truncated_tool_input_and_reasoning_are_accepted` | L | 文書にある truncated の形を受け入れる。壊れると DSH が大きな入力を切り詰めた実行がすべて response_failed になる（成功が失敗になる向き） | 消す |
| `test_ptc_producer_output`（2 件） | S（中） | [rejected]: DSH 0.2.0-rc.2 の実際の生成物の PTC の拒否を awaiting_approval にし、collect が拒否を覚えない… | 残す |
| `test_ptc_producer_output`（3 件） | D | 代表: `test_ptc_producer_output`。[cancelled]・[unavailable]・[tool_approval]: PTC の包み方は代表（[rejected]）と同じ dsh.py:70-72… | 消す |
| `test_ptc_producer_output`（3 件） | L | [read]・[read_403]・[caught_rejection]: 回復した PTC の読み取りエラー・捕捉した例外の成功を保つ | 消す |
| `test_ptc_refusal_survives_truncated_captured_output` | S（中） | Captured output が長く切り詰められた（truncated=true の）PTC の拒否も awaiting_approval にする | 残す |
| `test_ptc_refusal_preserves_first_control_failure`（2 件） | L | 認証の error と PTC の拒否のどちらが先かで、最初の制御の失敗の種類を保つ | 消す |

#### `adapters/dsh/test_identity.py`（17 件 → 13 件）

| テスト（群） | 分類 | 理由・防ぐ損害（重さ） | 扱い |
| --- | --- | --- | --- |
| `test_reads_observed_route_not_requested_or_parent` | S（中） | identity を要求した値や親の PI_* ではなく、試行の v4 log の request header と assistant の source から読む代表…。壊れると記録の取り違え | 残す |
| `test_accepts_repeated_responses_from_the_same_route` | S（中） | 同じ経路の request と応答の繰り返しは受け入れる | 残す |
| `test_rejects_unbound_or_invalid_records`（9 件） | S（中） | この試行に結び付かない・食い違う log から identity を作らない。cwd・id: 別のプロジェクト・別の session の log を採る | 残す |
| `test_rejects_unbound_or_invalid_records`（`[route_changed]`） | D | 代表: `test_rejects_unbound_or_invalid_records`。[route_changed]: 変わった後に応答が無いので、dsh_identity.py:103-107 が壊れても最後の照合（:126-131）が拒む | 消す |
| `test_rejects_unbound_or_invalid_records`（3 件） | L | malformed（壊れた行）・torn（改行の無い末尾）: json.loads が ValueError を投げ、ここに例外を握る経路は無い… | 消す |
| `test_rejects_unbound_or_invalid_records`（2 件） | 迷い（中） | symlink（log が symlink）・directory_link（session のディレクトリが symlink）: host 側の読み取りがリンクをたどらないこと…。ただし、たどって読めるのは header の cwd・session id がこの試行と一致する v4 log だけで、担当は state のディレクトリに直接書けるので… | 残す |

#### `adapters/dsh/test_review_evidence.py`（19 件 → 9 件）

| テスト（群） | 分類 | 理由・防ぐ損害（重さ） | 扱い |
| --- | --- | --- | --- |
| `test_native_pair_and_recovered_read_error_are_accepted` | S（中） | 2 つの固定の出力を native の write で書き、回復した読み取りエラーがある正常な log は昇格を認める | 残す |
| `test_missing_or_uncorrelated_native_success_is_refused`（4 件） | S（中） | shell（bash で書いた）・foreign-path（固定の出力でないパス）・failed（write が失敗）・duplicate… | 残す |
| `test_missing_or_uncorrelated_native_success_is_refused`（2 件） | L | unmatched（対応する call の無い result）: dsh_review_e… | 消す |
| `test_refusal_is_not_erased_by_later_native_success`（`[Error: [sandbox: file access denied u…]`） | S（中） | [DENIAL]: ファイルの読み書きの sandbox の拒否（workspace-write の固定の文とヒント）の後に native の書き込みが成功しても昇格させない | 残す |
| `test_refusal_is_not_erased_by_later_native_success`（`[Error: the user rejected escalating t…]`） | D | 代表: `test_approval_error_in_tool_result_is_not_success`。[escalation]（直接の昇格の拒否）: この文は先に _classify が awaiting_approval にして :69 で拒む | 消す |
| `test_refusal_is_not_erased_by_later_native_success`（`[Error: code run failed (exception): T…]`） | D | 代表: `test_ptc_producer_output`。[run_code の PTC の拒否]: 先に _classify が awaiting_approval にして :69 で拒む | 消す |
| `test_denial_marker_in_ordinary_tool_output_is_data` | L | bash のエラーの Captured output の中の拒否の文はデータ | 消す |
| `test_escalation_request_is_refused_even_if_result_claims_success` | S（高） | sandbox_permissions（昇格）を求めた tool の呼び出しがあれば、結果が completed でも昇格させない。壊れると、柵を広げて書いたかもしれないレビューを保存する（sandbox の境界） | 残す |
| `test_unsafe_log_is_refused_without_touching_its_target`（2 件） | L | missing（log が無い）・malformed（JSON でない）: OSError・ValueError の拒否を確かめるだけ | 消す |
| `test_unsafe_log_is_refused_without_touching_its_target`（2 件） | S（高） | symlink・hardlink の stdout.log は読まずに拒む。壊れると、リンク先・別の名前で差し替えた偽の log を証拠にしてレビューを昇格させる（未検証の結果の採用） | 残す |
| `test_unsafe_log_is_refused_without_touching_its_target`（`[duplicate-json-key]`） | D | 代表: `test_missing_malformed_or_inconsistent_stream_is_not_success`。[duplicate-json-key]: 重複した鍵を拒む _decode の _object（adapters/dsh.py:87-88）を代表が確かめる | 消す |
| `test_edit_of_both_fixed_exports_counts_as_native_success` | L | edit も native の書き込みに数える。壊れると edit で書いたレビューの昇格が理由付きで拒まれる（成功が失敗になる向き） | 消す |
| `test_unicode_line_separator_in_tool_content_is_not_a_jsonl_boundary` | L | tool の内容の U+2028・U+2029 で行を切らない。壊れると decode が失敗し、昇格が拒まれる（失敗の向き） | 消す |

#### `adapters/dsh/test_runner.py`（76 件 → 15 件）

| テスト（群） | 分類 | 理由・防ぐ損害（重さ） | 扱い |
| --- | --- | --- | --- |
| `test_real_process_state_and_stdin`（`[success-success-0]`） | S（中） | [success]: 偽の CLI の実プロセスで DSH を runner から動かす e2e の代表（e2e は adapter ごとに 1 件、#230 の D の例） | 残す |
| `test_real_process_state_and_stdin`（3 件） | L | [auth]・[malformed]・[descendant]: auth は失敗の種類（awaiting_authentication）だけ… | 消す |
| `test_real_process_state_and_stdin`（`[approval-awaiting_approval-0]`） | D | 代表: `test_approval_error_in_tool_result_is_not_success`。[approval]: 直接の拒否を成功にしない守りは adapter の代表が確かめる（上の層の重複） | 消す |
| `test_real_process_state_and_stdin`（`[approval-program-awaiting_approval-0]`） | D | 代表: `test_approval_error_in_tool_result_is_not_success`。[approval-program]: program の昇格の拒否（#174 の SR-C1）の e2e | 消す |
| `test_real_process_state_and_stdin`（`[nonzero-response_failed-1]`） | D | 代表: `test_exit_zero_is_not_a_substitute_for_valid_receipt`。[nonzero]: 非 0 の終了の success を response_failed にする守りは runner.py:559-561 にあり… | 消す |
| `test_real_process_state_and_stdin`（`[missing-session-response_failed-0]`） | D | 代表: `test_missing_identity_discards_success_payload`。[missing-session]: log の無い success を捨てる守りは adapter の代表が確かめる | 消す |
| `test_real_process_state_and_stdin`（`[mismatched-session-response_failed-0]`） | D | 代表: `test_mismatched_identity_discards_success_payload`。[mismatched-session]: 食い違う identity の success を捨てる守りは adapter の代表が確かめる | 消す |
| `test_native_process_has_private_tmp_and_readonly_attempt_metadata` | S（高） | #230 の残す S の例（DSH の書き込みの柵） | 残す |
| `test_scoped_dsh_cannot_modify_protected_or_unrelated_host_paths`（4 件） | D | 代表: `test_native_process_has_private_tmp_and_readonly_attempt_metadata`。[main]・[feature]・[neighbor]・[host-tmp]: どれも tmp_path（/tmp）の中にあり、守るのは --tmpfs /tmp で隠すこと | 消す |
| `test_scoped_dsh_cannot_modify_protected_or_unrelated_host_paths`（`[git]`） | S（高） | [git]: 親のリポジトリの共通の git ディレクトリ（.git/config）は、w… | 残す |
| `test_real_dsh_keeps_parallel_edit_as_observation` | D | 代表: `test_confined_batch_reports_parallel_edit_without_blocking`。confined_writes の adapter だけの batch では、別のセッションの隣の worktree の編集を観測… | 消す |
| `test_dsh_output_ancestor_symlink_is_rejected` | 迷い | 監査で戻した: DSH の出力先に symlink の祖先があると、柵の bind と prompt の書き込みの例外は正規化していないパスを使う（m02900・m03096・m03154） | 残す |
| `test_runtime_hardlinks_are_rejected_before_redaction_hides_the_link` | S（高） | 保持する state の hard link は伏せ字にせず sensitive_paths に出し、試行を失敗にする | 残す |
| `test_dsh_prompt_uses_only_its_owned_write_exceptions` | L | DSH には呼び出し側の write_exceptions を渡さず、試行の review-scratch・exports などだけを例外として書く | 消す |
| `test_recovered_read_error_keeps_primary_result`（28 件） | L | #230 の L の例（recovered-read-error の 28 件）。回復した読み取りエラーで primary の成功を保ち、fallback を使わない | 消す |
| `test_explicit_provider_key_is_used_without_ambient_credentials` | S（高） | run_workflow の environment で渡した資格情報だけで起動でき、その値を結果（payload・BatchResult の JSON）から伏せる。壊れると明示した資格情報が結果に残る（秘密情報の漏れ） | 残す |
| `test_explicit_auth_environment_is_allowlisted_and_redacted` | S（高） | environment で渡した値のうち許可リストの GH_TOKEN だけを担当に渡し（UNLISTED_SECRET は渡さない）…。壊れると許可していない値を担当に渡すか、保持する記録に秘密情報が残る | 残す |
| `test_private_session_artifacts_are_redacted` | D | 代表: `test_explicit_auth_environment_is_allowlisted_and_redacted`。dsh/state/session.jsonl の秘密情報を伏せる | 消す |
| `test_home_tool_caches_are_disposed_without_following_links` | S（高） | 使い捨ての HOME を、uv の cache のリンク（interpreter・checkout を指す）・FIFO・読み取り専用の Go の module ごと… | 残す |
| `test_large_tmpdir_spill_is_kept_in_runtime_tree_and_redacted` | D | 代表: `test_scratch_hardlinks_are_unlinked_and_the_rest_redacted`。TMPDIR の大きな spill を runtime の木に残して伏せ、許可リストの ambient の TMPDIR を使わない | 消す |
| `test_unsafe_runtime_files_are_reported_not_followed`（`[symlink]`） | S（中） | [symlink]: 保持する state の symlink はたどらず、消さず、sensitive_paths に出して試行を失敗にする。壊れると、外を指すリンクを含む記録を安全として成功にする（後で読む側がリンクをたどる） | 残す |
| `test_unsafe_runtime_files_are_reported_not_followed`（`[fifo]`） | D | 代表: `test_unsafe_runtime_files_are_reported_not_followed`。[fifo]: 代表と同じ runner.py:83 の not S_ISREG で報告する | 消す |
| `test_scratch_links_and_fifos_are_unlinked_not_followed`（`[tmp-symlink-foreign-link]`） | S（高） | [tmp-symlink]: TMPDIR の中の checkout の README を指すリンクは名前だけを外し、リンク先を消さない | 残す |
| `test_scratch_links_and_fifos_are_unlinked_not_followed`（`[tmp-fifo-spill.fifo]`） | L | [tmp-fifo]: TMPDIR の FIFO を外して成功にする。壊れると FIFO が残り、伏せ字の段（runner.py:83）が sensitive に出して response_failed になる（成功が失敗になる向き） | 消す |
| `test_scratch_hardlinks_are_unlinked_and_the_rest_redacted` | S（高） | TMPDIR の hard link の組は名前を外し、最後に 1 つの名前で残った nested/shared.json を伏せ字にして…。壊れると、hard link の別の名前に資格情報の入った内容が残る（秘密情報の漏れ） | 残す |
| `test_real_pytest_scratch_is_accepted`（`[pytest]`） | D | 代表: `test_real_pytest_scratch_is_accepted`。[pytest]: pytest の pytest-current などのリンクを外して成功にし、通常のファイルを残す | 消す |
| `test_real_pytest_scratch_is_accepted`（`[pytest-fixtures]`） | S（高） | [pytest-fixtures]: 本物の pytest が TMPDIR に残すリンク・FIFO・hard link を外し、checkout を指すディレクトリのリンク…。通常のファイルを消すと診断の記録を失う | 残す |
| `test_scratch_unlink_failure_is_reported_not_success`（`[tmp-fifo-names0]`） | D | 代表: `test_unsafe_runtime_files_are_reported_not_followed`。[tmp-fifo]: unlink の失敗は握られ、残った FIFO を伏せ字の段の not S_ISREG（runner.py:83）が報告する | 消す |
| `test_scratch_unlink_failure_is_reported_not_success`（`[tmp-hardlink-names1]`） | D | 代表: `test_runtime_hardlinks_are_rejected_before_redaction_hides_the_link`。[tmp-hardlink]: unlink の失敗で残った hard link を伏せ字の段の st_nlink（runner.py:83）が報告する | 消す |
| `test_kernel_rejects_replacing_runtime_mounts_and_keeps_target`（3 件） | L | dsh/home・dsh・dsh/tmp は mount point なので担当はリンクに置き換えられず、偽の CLI が例外で終わる | 消す |
| `test_home_removal_failure_is_reported_not_success` | S（高） | HOME を消せないときは sensitive_paths に出して失敗にし、残った HOME（.netrc）も伏せ字にする。壊れて消す前提で伏せ字から外すと、消せなかったときに資格情報が残る（秘密情報の漏れ） | 残す |
| `test_timeout_and_cancellation_stop_descendants`（`[False]`） | S（高） | [False]（期限切れ）: SIGTERM を無視する CLI と子を期限で止めた後も、session.jsonl と spill を伏せ字にし、HOME を消す。状態を見て伏せ字を飛ばす変更をすると秘密情報が残る | 残す |
| `test_timeout_and_cancellation_stop_descendants`（`[True]`） | D | 代表: `test_timeout_and_cancellation_stop_descendants`。[True]（取り消し）: 伏せ字・HOME の片付けは期限切れと同じ runner.py:517-528 で、代表（[False]）が確かめる | 消す |
| `test_unconfirmed_stop_reports_runtime_root` | S（高） | 停止を確かめられないときは dsh/ を sensitive_paths に出し、HOME・TMPDIR を消さず読まない（生きている書き手と競合しない） | 残す |
| `test_ptc_refusal_keeps_primary_failed`（8 件） | D | 代表: `test_ptc_producer_output`。PTC の拒否で primary を awaiting_approval・payload None にし、fallback があれば次へ進む e2e | 消す |

#### `adapters/dsh/test_sandbox.py`（6 件 → 4 件）

| テスト（群） | 分類 | 理由・防ぐ損害（重さ） | 扱い |
| --- | --- | --- | --- |
| `test_missing_bwrap_never_executes_command` | S（高） | #230 の残す S の例（bwrap が無いときに止まる） | 残す |
| `test_explicit_grants_preserve_neighboring_host_files` | S（高） | #230 の残す S の例（DSH の書き込みの柵） | 残す |
| `test_readonly_does_not_apply_additional_grants` | S（中） | 読み取り専用の profile では grant を足さない | 残す |
| `test_unsafe_grants_or_profile_never_run_the_command`（`[symlink]`） | S（高） | [symlink]: symlink の grant ではコマンドを実行しない。壊れると、内側の bwrap がリンク先を書き込みで bind し、外側の読み取り専用の root の下のファイルにも書ける mount を作りうる（sandbox の境界） | 残す |
| `test_unsafe_grants_or_profile_never_run_the_command`（2 件） | L | [missing]: 無い grant は resolve(strict=True) の OSError で 127 になり、壊れても例外で止まってコマンドは走らない | 消す |

#### `adapters/pi/test_adapter.py`（38 件 → 26 件）

| テスト（群） | 分類 | 理由・防ぐ損害（重さ） | 扱い |
| --- | --- | --- | --- |
| `test_prepare_builds_launcher_argv` | F∩S（高） | Pi.prepare の argv の固定の引数と対応を確かめる。`--no-approve`（Pi 1.3.0: trust-gated のプロジェクトローカルの設定・資源を読まない）が外れると… | 残す |
| `test_prepare_maps_skill_sources_and_args` | S（中） | agent.skill_sources を順に `--skill` に渡すことと、agent.args を末尾に付けることを確かめる。落ちると、設定した skill の source や利用者の引数（例の `--offline` など）が黙って効かない（中） | 残す |
| `test_collect_success_extracts_identity_and_payload` | S（中） | 成功の収集の正しく通る例（拒否の群に残す正例）。identity を最後の agent_end の assistant の model・provider・thinkingLevel と session の id から取り… | 残す |
| `test_exit_zero_without_agent_end_is_response_failed` | S（中） | agent_end の無いストリームを成功にしないことを確かめる（Pi は失敗でも終了コード 0 を返すことがある。#230 の S の例「exit 0 を成功としない」） | 残す |
| `test_missing_agent_settled_is_response_failed` | D | 代表: `test_final_lifecycle_dominates_earlier_turn`。最後の agent_end の後に agent_settled が無ければ失敗にする同じ条件（pi.py:212-217 の `settled is None`）を… | 消す |
| `test_aborted_stop_reason_is_interrupted` | S（中） | stopReason の aborted を interrupted にすることを確かめる（pi.py:224-225 の語の組の "abort"）。response_failed に取り違えると、取り消された担当の後に fallback の有料の実行が始まる（中: 取り消しで fallback しない） | 残す |
| `test_unknown_stop_reason_is_response_failed` | S（中） | 正常でない stopReason（length など、切れた回答）を成功にしないことを確かめる（_STOP_OK） | 残す |
| `test_auth_stderr_reports_awaiting_authentication` | D | 代表: `test_diagnostics_override_plausible_answer`。stderr を診断にする同じ経路（pi.py:191）と `_AUTH` の語を、もっと… | 消す |
| `test_non_json_lines_and_osc_sequences_are_skipped` | L | OSC の通知・進捗の行・`{` で始まらない行を無視する正例。壊れると完了の後の行で response_failed になり、偽の失敗として現れる | 消す |
| `test_text_shape_returns_concatenated_text` | S（中） | text の役割で、最後の assistant の text の部分をすべてつなぎ（thinking を除く）payload にすることを確かめる。つなぎ方が壊れて一部だけを返すと、もっともらしいが欠けた回答を成功として返す（中） | 残す |
| `test_non_object_answer_fails_json_shape` | L | JSON の役割で object でない回答を response_failed にする | 消す |
| `test_only_completed_matching_full_read_is_hashed`（`[configured]`） | D | 代表: `test_only_completed_matching_full_read_is_hashed`。read のイベントが無いので、完了の無い [mentioned] と同じく証拠が出ない経路 | 消す |
| `test_only_completed_matching_full_read_is_hashed`（5 件） | S（中） | skill の版は、同じ toolCallId の read の開始と成功した完了が対になり、範囲指定が無く、読んだ全文が今のファイルと一致するときだけ記録することを確かめる | 残す |
| `test_prepare_applies_role_skills` | S（中） | role.skills と、work_dir 基準で解決した設定の source の SKILL.md の絶対パスを stdin のプロンプトに足すことを確かめる。落ちると、担当が指定の skill を使わないか別の版で、もっともらしい回答を返す（中） | 残す |
| `test_final_lifecycle_dominates_earlier_turn`（4 件） | S（中） | 最後の agent_end とその後の settlement だけが完了を決めることを確かめる | 残す |
| `test_final_lifecycle_dominates_earlier_turn`（`[events4-success]`） | L | 前の agent_end が失敗でも、最後の完全な agent_end で成功にする正例（回復） | 消す |
| `test_diagnostics_override_plausible_answer`（2 件） | S（中） | もっともらしい回答があっても、stderr と error イベントの認証・承認の診断を優先することを確かめる（1 つのテストで 2 つの経路）。外れると、認証・承認で止まった実行を成功と報告する（中） | 残す |
| `test_auth_words_in_successful_answer_are_harmless` | L | 成功の回答の本文の認証・承認の語を診断にしない正例。壊れると偽の失敗（awaiting_authentication など）として現れる | 消す |
| `test_missing_identity_is_not_filled_from_config` | S（中） | assistant に model・provider・thinkingLevel が無く session も無いとき、identity を要求の設定で埋めないことを確かめる。壊れると観測していない値を実測として記録する（中: 記録の取り違え） | 残す |
| `test_end_to_end_launch_and_collection`（`[0-success]`） | L | 本物の adapter・runner・偽の launcher で成功の一連を通す。壊れると Pi の実行がすべて失敗し、初回の利用で明らかに動かない | 消す |
| `test_end_to_end_launch_and_collection`（`[7-response_failed]`） | D | 代表: `test_exit_zero_is_not_a_substitute_for_valid_receipt`。非ゼロ終了を失敗にする runner の判定（runner.py:557-561）の上の層の重なり | 消す |
| `test_malformed_event_types_do_not_crash_collection` | L | type が文字列でないイベントで止まらない正例 | 消す |
| `test_empty_skill_requires_observed_text_content` | S（中） | read の完了の result に text の content が無ければ、空の SKILL.md でも版を記録しないことを確かめる… | 残す |
| `test_trailing_broken_event_cannot_reuse_success`（3 件） | S（中） | 完了の後の壊れた行で前の回答を使わないことを確かめる | 残す |
| `test_trailing_broken_event_cannot_reuse_success`（`[{"type":{}}-response_failed]`） | D | 代表: `test_trailing_broken_event_cannot_reuse_success`。type が object の場合も [{"type":[]}] と同じ `isinstance(value.get("type"), str)` の条件 | 消す |
| `test_broken_event_before_fresh_completion_can_recover` | L | 壊れた行の後に新しい session・完全な agent_end・agent_settled が来れば、その新しい回答と identity で成功にする正例（pi.rst の回復）。壊れると偽の失敗として現れる | 消す |
| `test_plain_progress_after_completion_is_harmless` | S（中） | 完了の後の普通の進捗の行は許す正例 | 残す |
| `test_new_session_without_completion_cannot_reuse_old_payload` | S（中） | 完了の後に新しい session が始まり完了していなければ、前の回答を使わずに失敗にし、session の id は新しいものにすることを確かめる…。外れると、別のセッションの前の回答で成功にする（中） | 残す |

#### `adapters/test_parser_regressions.py`（104 件 → 11 件）

| テスト（群） | 分類 | 理由・防ぐ損害（重さ） | 扱い |
| --- | --- | --- | --- |
| `test_literal_unicode_preserves_payload_and_observed_identity`（12 件） | L | JSONL を LF だけで分けること（633ab42 で直した、splitlines が U+2028・U+2029・U+0085 で記録を切る不具合の再発防止）。壊れても、JSON の文字列の中の引用符は必ずエスケープされるので、切れた断片が正しい記録として読まれることは無く、正しい回答が response_failed… | 消す |
| `test_literal_unicode_full_skill_read_is_hashed`（9 件） | L | skill の読み込みの証拠を LF だけで分けること。壊れても、証拠を失って skill_versions が不明になるか（verified_versions は今のファイルの bytes と一致するときだけ記録するので… | 消す |
| `test_codex_rollout_unicode_skill_evidence_survives_reparsing`（3 件） | L | codex の rollout の skill の証拠（codex.py:107-116）を LF だけで分けること | 消す |
| `test_codex_unicode_session_metadata_cannot_hide_mismatch`（`[\u2028]`） | S（中） | rollout の session_meta の照合（codex.py:158-166）も LF だけで分けること。この走査だけが splitlines に戻ると、区切り文字を含む session_meta が切れて照合から漏れ、別の session の rollout が受け入れられ… | 残す |
| `test_codex_unicode_session_metadata_cannot_hide_mismatch`（2 件） | D | 代表: `test_codex_unicode_session_metadata_cannot_hide_mismatch`。str.splitlines は U+2028・U+2029・U+0085 をどれも区切りにするので、同じ走査… | 消す |
| `test_unicode_in_failure_event_keeps_diagnostic_classification`（2 件） | D | 代表: `test_error_event_dominates_plausible_result`。代表を残すケースに付け替えた（棚卸しで挙げた代表は別の担当が消した） | 消す |
| `test_unicode_in_failure_event_keeps_diagnostic_classification`（2 件） | D | 代表: `test_diagnostics_override_plausible_answer`。成功の後の失敗の優先（#230 の D の例） | 消す |
| `test_unicode_in_failure_event_keeps_diagnostic_classification`（2 件） | D | 代表: `test_failure_diagnostics_override_prior_message`。代表を残すケースに付け替えた（棚卸しで挙げた代表は別の担当が消した） | 消す |
| `test_unicode_in_failure_event_keeps_diagnostic_classification`（2 件） | L | cursor の _diagnostics が error イベントを診断に含めること（cursor.py:136）。この条件を外しても error イベントは errored（cursor.py:201-202… | 消す |
| `test_unicode_success_cannot_hide_corrupt_lf_record`（`[claude-code]`） | D | 代表: `test_truncated_event_after_success_invalidates_completion`。代表を残すケースに付け替えた（棚卸しで挙げた代表は別の担当が消した） | 消す |
| `test_unicode_success_cannot_hide_corrupt_lf_record`（`[pi]`） | D | 代表: `test_trailing_broken_event_cannot_reuse_success`。成功の後の破損した記録を成功にしない（#230 の D の例） | 消す |
| `test_unicode_success_cannot_hide_corrupt_lf_record`（`[codex]`） | D | 代表: `test_truncated_later_event_does_not_reuse_success`。成功の後の破損した記録を成功にしない（#230 の D の例） | 消す |
| `test_unicode_success_cannot_hide_corrupt_lf_record`（`[cursor]`） | D | 代表: `test_collect_later_corruption_or_failure_cannot_reuse_success`。成功の後の破損した記録を成功にしない（#230 の D の例） | 消す |
| `test_fenced_json_with_nested_code_backticks_is_data`（`[claude-code]`） | L | JSON の文字列の中のバッククォートを閉じ fence と誤ると、回答を取り出せずに response_failed（成功が失敗として見える向き）になる | 消す |
| `test_fenced_json_with_nested_code_backticks_is_data`（`[pi]`） | S（中） | pi のフェンスの JSON の解析（pi.py:63-81）の正しく通る例 | 残す |
| `test_fenced_json_with_nested_code_backticks_is_data`（`[codex]`） | L | JSON の文字列の中のバッククォートを閉じ fence と誤ると、回答を取り出せずに response_failed（成功が失敗として見える向き）になる | 消す |
| `test_fenced_json_with_nested_code_backticks_is_data`（`[cursor]`） | L | JSON の文字列の中のバッククォートを閉じ fence と誤ると、回答を取り出せずに response_failed（成功が失敗として見える向き）になる | 消す |
| `test_fenced_json_with_nested_code_backticks_is_data`（`[devin]`） | L | JSON の文字列の中のバッククォートを閉じ fence と誤ると、回答を取り出せずに response_failed（成功が失敗として見える向き）になる | 消す |
| `test_invalid_fence_cannot_salvage_inner_json`（2 件） | S（中） | 閉じフェンスの無い回答を成功にしない（claude_code.py:78、pi.py:79 の candidate[end:].lstrip().startswith("```")。claude と pi は別の関数） | 残す |
| `test_invalid_fence_cannot_salvage_inner_json`（`[```json\n{"outer":{"ok":true},\n```-c…]`） | S（中） | 監査で戻した: 最初の候補で失敗したときは value が未束縛の UnboundLocalError で invalid_result になるが、前の fence が raw_decode に成功して閉じ fence の検査に落ちた後に次の fence で失敗すると…（m00101） | 残す |
| `test_invalid_fence_cannot_salvage_inner_json`（`[```json\n{"outer":{"ok":true},\n```-pi]`） | S（中） | 監査で戻した: fence の raw_decode の失敗で次の候補へ進む continue を外す変異（m01301） | 残す |
| `test_devin_fence_failure_in_either_channel_is_read_only`（5 件） | D | 代表: `test_truncated_later_stdout_cannot_reuse_completion`・`test_tool_run_stdout_not_ending_with_final_answer_fails`。代表を、監査で devin の回答の後の行の検査（devin.py:59-76 の _plain_tail・_ends_with）の変異を検出した残すテストに付け替えた… | 消す |
| `test_devin_fence_failure_in_either_channel_is_read_only`（`[```json\n{"ok":true}-response_failed-…]`） | S（中） | 最終の ATIF の回答が閉じフェンスを欠くとき成功にしない。stdout の末尾に残る ``` の行を _plain_tail が拒み（devin.py:59-64・67-76）… | 残す |
| `test_devin_fence_failure_in_either_channel_is_read_only`（`[```json\n{"ok":true}\n```\nError: not…]`） | D | 代表: `test_truncated_later_stdout_cannot_reuse_completion`・`test_tool_run_stdout_not_ending_with_final_answer_fails`。代表を、監査で devin の回答の後の行の検査（devin.py:59-76 の _plain_tail・_ends_with）の変異を検出した残すテストに付け替えた… | 消す |
| `test_devin_fence_failure_in_either_channel_is_read_only`（`[```json\n{"ok":true}\n```\nError: not…]`） | D | 代表: `test_truncated_later_stdout_cannot_reuse_completion`・`test_tool_run_stdout_not_ending_with_final_answer_fails`。代表を、監査で devin の回答の後の行の検査（devin.py:59-76 の _plain_tail・_ends_with）の変異を検出した残すテストに付け替えた… | 消す |
| `test_devin_fence_failure_in_either_channel_is_read_only`（`[```json\n{"ok":true}\n```\nApproval r…]`） | D | 代表: `test_truncated_later_stdout_cannot_reuse_completion`・`test_tool_run_stdout_not_ending_with_final_answer_fails`。代表を、監査で devin の回答の後の行の検査（devin.py:59-76 の _plain_tail・_ends_with）の変異を検出した残すテストに付け替えた… | 消す |
| `test_devin_fence_failure_in_either_channel_is_read_only`（`[```json\n{"ok":true}\n```\nApproval r…]`） | D | 代表: `test_truncated_later_stdout_cannot_reuse_completion`・`test_tool_run_stdout_not_ending_with_final_answer_fails`。代表を、監査で devin の回答の後の行の検査（devin.py:59-76 の _plain_tail・_ends_with）の変異を検出した残すテストに付け替えた… | 消す |
| `test_devin_fence_failure_in_either_channel_is_read_only`（2 件） | D | 代表: `test_truncated_later_stdout_cannot_reuse_completion`・`test_tool_run_stdout_not_ending_with_final_answer_fails`。代表を、監査で devin の回答の後の行の検査（devin.py:59-76 の _plain_tail・_ends_with）の変異を検出した残すテストに付け替えた… | 消す |
| `test_codex_fresh_completed_message_recovers_error`（5 件） | D | 代表: `test_codex_fresh_completed_message_recovers_error`。transport・approval の文言と、error の後の turn.started の有無は、どれも codex.py:247-261 の同じ回復の分岐を通る | 消す |
| `test_codex_fresh_completed_message_recovers_error`（`[False-authentication required]`） | S（中） | codex の再試行の回復（codex.py:256-261 の pending_errors.clear()、633ab42 の GPT-H1）の正しく通る例 | 残す |
| `test_codex_recovery_requires_new_complete_message_and_terminal_success`（2 件） | D | 代表: `test_failure_diagnostics_override_prior_message`。完了した message の後の error が未回復のまま残れば response_failed（codex.py:247-252・276） | 消す |
| `test_codex_recovery_requires_new_complete_message_and_terminal_success`（`[tail1]`） | D | 代表: `test_latest_turn_cannot_reuse_an_earlier_message`。error で古い message を無効にする代入（codex.py:249 の text = None）は turn.started と共通の文で… | 消す |
| `test_codex_recovery_requires_new_complete_message_and_terminal_success`（2 件） | D | 代表: `test_missing_or_unfinished_final_turn_is_failure`。最後の message に turn.completed が無ければ response_failed（codex.py:268・278） | 消す |
| `test_codex_recovery_requires_new_complete_message_and_terminal_success`（`[tail4]`） | D | 代表: `test_latest_turn_cannot_reuse_an_earlier_message`。代表を残すケースに付け替えた（棚卸しで挙げた代表は別の担当が消した） | 消す |
| `test_codex_recovery_requires_new_complete_message_and_terminal_success`（`[tail5]`） | D | 代表: `test_latest_turn_cannot_reuse_an_earlier_message`。空の message は回復にも成功にもならない（codex.py:258・282-285） | 消す |
| `test_codex_recovery_requires_new_complete_message_and_terminal_success`（`[tail6]`） | D | 代表: `test_invalid_final_object_cannot_return_a_nested_fragment`。代表を残すケースに付け替えた（棚卸しで挙げた代表は別の担当が消した） | 消す |
| `test_codex_recovery_requires_new_complete_message_and_terminal_success`（`[tail7]`） | D | 代表: `test_missing_or_unfinished_final_turn_is_failure`。代表を残すケースに付け替えた（棚卸しで挙げた代表は別の担当が消した） | 消す |
| `test_codex_recovery_requires_new_complete_message_and_terminal_success`（`[tail9]`） | S（中） | turn.failed の後に新しい message と turn.completed が来ても失敗のままにする… | 残す |
| `test_codex_recovery_does_not_clear_other_diagnostic_channels`（`[authentication required-awaiting_auth…]`） | D | 代表: `test_failure_diagnostics_override_prior_message`。stderr は回復と無関係に診断に入る（codex.py:121） | 消す |
| `test_codex_recovery_does_not_clear_other_diagnostic_channels`（`[authentication required-awaiting_auth…]`） | S（中） | 回復しても、stdout の JSON でない行の認証・承認の診断を消さない（codex.py:119-129 の _diagnostics の 126-127） | 残す |
| `test_codex_recovery_does_not_clear_other_diagnostic_channels`（`[approval required-awaiting_approval-s…]`） | D | 代表: `test_failure_diagnostics_override_prior_message`。stderr は回復と無関係に診断に入る（codex.py:121） | 消す |
| `test_codex_recovery_does_not_clear_other_diagnostic_channels`（`[approval required-awaiting_approval-n…]`） | D | 代表: `test_codex_recovery_does_not_clear_other_diagnostic_channels`。同じ codex.py:126-127 の分岐で、当てる正規表現が _APPROVAL に変わるだけ | 消す |
| `test_codex_corrupt_event_cannot_be_recovered_by_success` | D | 代表: `test_truncated_later_event_does_not_reuse_success`。stdout の破損した記録は位置によらず _malformed_events（codex.py:174-176・274）で response_failed にする | 消す |
| `test_codex_unicode_rollout_cannot_hide_corrupt_lf_record`（`[\u2028]`） | S（中） | rollout の破損した記録で失敗にする（codex.py:274 の `or _malformed_events(rollout_text)`） | 残す |
| `test_codex_unicode_rollout_cannot_hide_corrupt_lf_record`（`[\u2029]`） | D | 代表: `test_codex_unicode_rollout_cannot_hide_corrupt_lf_record`。U+2029 は U+2028 と同じ走査（codex.py:176・181）の同じ退行で、破損の検査は同じ条件 | 消す |
| `test_codex_unverified_recovery_keeps_pending_diagnostic`（6 件） | L | 回復が完成しない（turn.completed が無い・message が無い・JSON が未完成）とき、先の認証・承認の診断を残す（codex.py:256-261）。壊れても回復の条件の残りか完了の検査（codex.py:276-285）で失敗のままで、awaiting_* が response_failed に変わるだけ（成功にはならない） | 消す |
| `test_devin_unicode_diagnostic_inside_json_remains_data`（12 件） | L | devin の stdout・最終の ATIF の診断の走査を LF だけで分けること（devin.py:238-245、633ab42 の SR1）。splitlines に戻ると、JSON の文字列の中の区切り文字の後の "Error: not logged in"・"Approval required" が診断の行になり… | 消す |
| `test_devin_export_unicode_remains_json_data`（3 件） | D | 代表: `test_collect_success_extracts_identity`。export の JSON は json.loads で読むので区切り文字は値のまま（devin.py:134-139） | 消す |

#### `adapters/test_skills.py`（1 件 → 0 件）

| テスト（群） | 分類 | 理由・防ぐ損害（重さ） | 扱い |
| --- | --- | --- | --- |
| `test_replaced_skill_fifo_is_unknown_without_blocking` | L | SKILL.md が FIFO に置き換えられたとき、O_NONBLOCK で開いて普通のファイルでなければ読まない（skills.py:288-292）。O_NONBLOCK が無いと collect が書き手を待って止まり、runner 全体が戻らない（見て分かる） | 消す |

#### `test_checkout_policy.py`（17 件 → 11 件）

| テスト（群） | 分類 | 理由・防ぐ損害（重さ） | 扱い |
| --- | --- | --- | --- |
| `test_self_override_does_not_use_retained_fallback_as_confinement_evidence`（`[fallback0]`） | S（高） | --assign self で一次担当が全て self のとき、雛形に残る fallback（起動しない）の confined_writes を隔離の証拠にせず、全登録を必須にする | 残す |
| `test_self_override_does_not_use_retained_fallback_as_confinement_evidence`（`[fallback1]`） | D | 代表: `test_self_override_does_not_use_retained_fallback_as_confinement_evidence`。[fallback1]（fallback 2 件）は、同じ分岐（29 行）を fallback の数だけ変えて確かめる | 消す |
| `test_confined_primary_keeps_targeted_scope_with_a_retained_fallback` | D | 代表: `test_confined_preflight_retains_unrelated_missing_registration`。全担当が隔離の保証を持つときに限定の監査（main と依頼元）を返す、正しく通る例 | 消す |
| `test_confined_batch_reports_parallel_edit_without_blocking` | S（中） | 隔離された担当の run で、無関係な checkout の並行の変更を unrelated_checkout_audit に内容の変化として残し…。無関係な変更の記録を落とす変更も検出する | 残す |
| `test_confined_batch_still_blocks_protected_edits`（`[main]`） | D | 代表: `test_confined_batch_still_blocks_protected_edits`。[main] は守る集合の main の要素 | 消す |
| `test_confined_batch_still_blocks_protected_edits`（`[feature]`） | S（高） | 隔離された担当の run でも、守る checkout（依頼元 | 残す |
| `test_nonconfined_batch_preserves_strict_parallel_edit_audit` | D | 代表: `test_unproven_configuration_keeps_unavailable_registration_blocking`。隔離の保証の無い担当では全登録を必須にする（checkout_policy.py:40-41） | 消す |
| `test_confined_preflight_retains_unrelated_missing_registration` | S（高） | 隔離された構成の起動前の監査は、無関係な登録の消失で止まらず（正しく通る例）、run は … | 残す |
| `test_unproven_configuration_keeps_unavailable_registration_blocking`（3 件） | S（高） | 保証を確かめられない構成では全登録を必須にし、無関係な登録の消失でも起動前に止める。それぞれ別の条件: 保証の無い一次担当（40-41）、保証の無い fallback（35 の *assignment.fallback の要素）、adapter を読めない… | 残す |
| `test_unproven_configuration_keeps_unavailable_registration_blocking`（`[all-self]`） | D | 代表: `test_self_override_does_not_use_retained_fallback_as_confinement_evidence`。一次担当が全て self（fallback なし）で全登録を必須にする分岐（29-31）は… | 消す |
| `test_unproven_configuration_keeps_unavailable_registration_blocking`（`[truthy]`） | 迷い（高） | confined_writes が True でない真の値（"yes"）を保証とみなさない（is not True）。trusted adapter の bool の欄に文字列が入る経路は今は無く、S か L か決められない | 残す |
| `test_confined_preflight_rejects_protected_audit_failure`（`[main]`） | S（高） | 隔離された構成でも、守る checkout（main）の指紋が取れなければ起動前に止める（require_auditable_checkouts の必須のパスの失敗… | 残す |
| `test_confined_preflight_rejects_protected_audit_failure`（`[feature]`） | D | 代表: `test_confined_preflight_rejects_protected_audit_failure`。[feature] は守る集合の show-toplevel の要素 | 消す |
| `test_required_path_missing_from_snapshot_is_not_success` | S（高） | 必須のパスが登録の一覧に無いときも、失敗の記録が無いことを成功にせず、audit_unavailable の finding で止める… | 残す |
| `test_changed_adapter_guarantee_never_launches_nonconfined_attempt` | S（高） | 範囲を決めた後に adapter の保証が変わったら、起動の直前の再確認で unsupported にし、限定の監査のまま保証の無い担当を起動しない…。外すと、保証の無い担当の書き込みを unrelated に回して見逃す | 残す |

#### `test_cli.py`（39 件 → 12 件）

| テスト（群） | 分類 | 理由・防ぐ損害（重さ） | 扱い |
| --- | --- | --- | --- |
| `test_check_list_report_support_state_without_configuration_values`（2 件） | L | check・list の出力（#230 の L の例）。supported の値を誤っても、run の段で runner が adapter の読み込みと capability を確かめ直して unsupported にする… | 消す |
| `test_invalid_arguments_are_sanitized`（6 件） | L | argparse の整形（#230 の L の例）。_Parser.error の上書き（cli.py:23-26）を外しても、argparse の既定が usage と誤りを stderr に出して終了コード 2 で止まり… | 消す |
| `test_invalid_config_never_prints_raw_values` | L | CLI は ConfigError の category だけを出す（cli.py:187-189）。ConfigError は固定の category と定型文しか持たず元の例外を from None で切る（config.py:29-34・177）ので… | 消す |
| `test_explicit_missing_and_auto_broken_personal_are_errors` | S（中） | 自動で探した個人設定の場所が壊れた symlink のとき config_io（終了コード 2）にする…。この条件が無いと個人設定が黙って無視され、雛形だけの設定（別の agent・model・割り当て）で run が進む | 残す |
| `test_run_exit_codes_and_atomic_result`（`[success-0]`） | S（中） | [partial_success-1] の拒否の正しく通る例（何でも 1 にする実装で通らないように） | 残す |
| `test_run_exit_codes_and_atomic_result`（`[self-0]`） | L | self を成功の集合（cli.py:160）から外すと self の run が終了コード 1 になり、呼び出し側には失敗として現れる | 消す |
| `test_run_exit_codes_and_atomic_result`（`[partial_success-1]`） | S（中） | 成功していない batch（partial_success・failed）を終了コード 0 にしない（cli.py:160）。0 になると、呼び出し側が一部失敗・失敗の run を成功として扱う | 残す |
| `test_run_exit_codes_and_atomic_result`（`[failed-1]`） | D | 代表: `test_run_exit_codes_and_atomic_result`。failed は partial_success と同じ cli.py:160 の else の分岐で 1 になる | 消す |
| `test_cli_overlay_assignment_priority_preserves_fallback` | S（中） | --config の個人設定と --assign を load_config に渡す配線（cli.py:171・176-182…。--assign が無視されると、利用者が選んだ担当（self など）ではなく個人設定・雛形の担当が黙って起動する（有料の担当が動く、別のモデルになる） | 残す |
| `test_sigint_saves_interrupted_batch_and_restores_handler` | S（中） | SIGINT のハンドラが共有の cancel を立て（cli.py:126-130）、結果を保存して終了コード 130 を返し、元のハンドラに戻す（cli.py:158-162）。ハンドラが無い・cancel を立てないと、Ctrl-C で担当のプロセスが止まらず（監督プロセスは別の session で動く… | 残す |
| `test_unsupported_run_persists_result` | L | adapter を読めないときの unsupported（runner.py:407-408。except の return が無いと、試行は worktree を作った後 adapt… | 消す |
| `test_shipped_template_passes_check`（2 件） | L | 雛形 .devcontainer/agent-runner.toml と postCreate が置く個人設定（agent-runner-personal.toml）が読めること…。壊れると、どの利用者の check・run も初回から設定の誤り（終了コード 2）か unsupported（終了コード 1）で止まる（初回の利用で明らかに動かない） | 消す |
| `test_default_template_resolves_relative_to_module_not_cwd` | L | 既定の雛形を cli.py の位置から探す（cli.py:20・170）。cwd 基準に壊れると、別の cwd からの実行は config_io（終了コード 2）で止まる | 消す |
| `test_list_requires_installed_guaranteed_capabilities`（3 件） | L | list の supported の判定（cli.py:83-87。誤っても run の段で runner.py:403-404 が保証の無い adapter を unsupported にするので、終了コード 1 と state で現れる | 消す |
| `test_after_run_gets_the_result_path_and_never_changes_the_exit_code`（2 件） | S（中） | 後処理に {result} を置き換えた result.json のパスを渡し（hooks.py:44）…。壊れると、雛形の review の後処理（review_run.py の finalize-parent・attach-runner）が失敗しても成功と報告され… | 残す |
| `test_after_run_timeout_is_reported_without_changing_the_exit_code` | L | 後処理の期限切れ（#230 の L の例の期限切れの kill） | 消す |
| `test_summary_lists_no_after_run_when_unset` | L | 後処理が無いときに summary の after_run が空であること（表示）。壊れて after_run が欠けると、summary を読む呼び出し側が KeyError で失敗する | 消す |
| `test_after_run_is_not_started_after_an_interrupted_run` | S | PR #247 のサイクル 1 で戻した（D-230-14）: SIGINT で中断した run では後処理を起動しない（interfaces.rst「後処理」、`hooks.py:56` が run の cancel を渡す）。当初の代表 `test_already_cancelled_does_not_spawn` は hooks を通らず、cancel を新しい event に差し替える変異（k0024）を検出しない | 残す |
| `test_after_run_internal_error_is_reported_without_changing_the_exit_code` | S（中） | 監督の例外を、終了コードを変えずに response_failed・停止未確認で報告する（hooks.py:65-67 | 残す |
| `test_write_exceptions_follow_the_work_scope_lines_in_order` | 迷い | 監査で戻した: 空行が無いと、依頼文の先頭の行が呼び出し側の許可した例外の一覧の続きに見える（依頼文が「- <パス>: …」で始まると、担当には許可された書き込みの例外として読める）（m02946） | 残す |
| `test_invalid_write_exceptions_are_rejected_before_any_output`（`[valid]`） | S（中） | [dash-separate-token] の拒否の正しく通る例 | 残す |
| `test_invalid_write_exceptions_are_rejected_before_any_output`（`[empty]`） | D | 代表: `test_invalid_write_exceptions_are_rejected_before_any_output`。値の検査は runner にだけある（runner.py:96-107 の _single_line と 337-344 | 消す |
| `test_invalid_write_exceptions_are_rejected_before_any_output`（`[leading-space]`） | D | 代表: `test_invalid_write_exceptions_are_rejected_before_any_output`。値の検査は runner にだけある（runner.py:96-107 の _single_line と 337-344 | 消す |
| `test_invalid_write_exceptions_are_rejected_before_any_output`（`[trailing-space]`） | D | 代表: `test_invalid_write_exceptions_are_rejected_before_any_output`。値の検査は runner にだけある（runner.py:96-107 の _single_line と 337-344 | 消す |
| `test_invalid_write_exceptions_are_rejected_before_any_output`（`[leading-ideographic]`） | D | 代表: `test_invalid_write_exceptions_are_rejected_before_any_output`。値の検査は runner にだけある（runner.py:96-107 の _single_line と 337-344 | 消す |
| `test_invalid_write_exceptions_are_rejected_before_any_output`（`[trailing-nbsp]`） | D | 代表: `test_invalid_write_exceptions_are_rejected_before_any_output`。値の検査は runner にだけある（runner.py:96-107 の _single_line と 337-344 | 消す |
| `test_invalid_write_exceptions_are_rejected_before_any_output`（`[newline]`） | D | 代表: `test_invalid_write_exceptions_are_rejected_before_any_output`。値の検査は runner にだけある（runner.py:96-107 の _single_line と 337-344 | 消す |
| `test_invalid_write_exceptions_are_rejected_before_any_output`（`[tab]`） | D | 代表: `test_invalid_write_exceptions_are_rejected_before_any_output`。値の検査は runner にだけある（runner.py:96-107 の _single_line と 337-344 | 消す |
| `test_invalid_write_exceptions_are_rejected_before_any_output`（`[dash-separate-token]`） | S（中） | argparse の誤り（別の引数に書いた -x）で CLI が止まり、出力先を作らないこと… | 残す |

#### `test_config.py`（86 件 → 18 件）

| テスト（群） | 分類 | 理由・防ぐ損害（重さ） | 扱い |
| --- | --- | --- | --- |
| `test_recursive_overlay_replaces_arrays_and_preserves_other_fields` | S（中） | 個人設定を table は再帰的に統合し配列は置き換える（config.py:71-79）。再帰や置き換えが壊れると、個人設定の command・env・deadline・agents・fallback が黙って無視され（または雛形の値が残り）… | 残す |
| `test_assignment_override_is_last_and_keeps_explicit_fallback` | S（中） | --assign の割り当てが個人設定の後に効き、agents だけを置き換えて明示の fallback を残す（config.py:102-108）。置き換えの代入が無いと --assign が黙って無視され、個人設定の担当が起動する | 残す |
| `test_assignment_override_can_add_a_defined_role` | L | workflow に無いが定義済みの role を --assign で足せること（config.py:98-108）。壊れると、足す呼び出しが ConfigError（invalid_type・invalid_reference、終了コード 2）か NameError（runner_failed… | 消す |
| `test_empty_template_can_be_completed_by_personal_config` | D | 代表: `test_recursive_overlay_replaces_arrays_and_preserves_other_fields`。空の table の雛形に個人設定を重ねる | 消す |
| `test_config_errors_are_categorized_without_input_or_traceback_leaks`（3 件） | L | 版の検査（models.py:61-67 の _schema_version と Literal[1]）。_schema_version を外しても 2・"1" は Literal[1] が拒否し、通るのは true だけで v1 の設定として読まれるだけ | 消す |
| `test_config_errors_are_categorized_without_input_or_traceback_leaks`（`[TOP_SECRET_unknown = "TOP_SECRET_valu…]`） | S（中） | 未知のキーを拒否する（models.py:59 の extra="forbid"。拒否が無いと、綴りを誤ったキー（例: 最上位の [workflow.review]、ski… | 残す |
| `test_config_errors_are_categorized_without_input_or_traceback_leaks`（4 件） | D | 代表: `test_config_errors_are_categorized_without_input_or_traceback_leaks`。agent・role・workflow・assignment の未知のキーも、同じ StrictModel の extra="forbid"… | 消す |
| `test_config_errors_are_categorized_without_input_or_traceback_leaks`（6 件） | L | strict の型の検査（models.py:59 の strict=True）。緩めても "false"・"60" は正しい値に変換され、文字列の command・dict の env・数の model は pydantic の検証が拒否し… | 消す |
| `test_config_errors_are_categorized_without_input_or_traceback_leaks`（11 件） | L | 値の検査。期限の 0・負・inf（Field(gt=0)・allow_inf_nan=False）は、壊れると即時の期限切れか止まらない担当（見て分かる）になる | 消す |
| `test_read_errors_are_sanitized` | L | 読めない個人設定を config_io にする（config.py:67-68）。except を外すと OSError が CLI の except Exception で runner_failed（終了コード 2）になり… | 消す |
| `test_parse_errors_are_sanitized`（2 件） | L | TOML の誤り・UTF-8 でない内容を invalid_toml にする（config.py:65-66）。except を外すと TOMLDecodeError・UnicodeDecodeError が CLI の except Exception で runner_failed… | 消す |
| `test_references_must_resolve`（4 件） | L | 参照の検査（config.py:122-143）。壊れても、未知の agent は agent.model の AttributeError（config.py:135）… | 消す |
| `test_references_must_resolve`（`[[workflows.audit.assignments.unknown]…]`） | S（中） | 監査で戻した: 最終形の割り当てで未定義の role を拒否する検査。外すと、個人設定の役割名の誤記（例: [workflows.issue.assignments.implemnt] で implement の担当を選び直すつもり）が黙って通る（m01871・m01803） | 残す |
| `test_assignment_overrides_require_existing_workflow_and_role`（3 件） | L | --assign の workflow と role の存在の検査（config.py:85-92）。壊れても、workflow が None・未知なら workflows[...] の KeyError で止まり、未知の role は _validate_references… | 消す |
| `test_self_cannot_be_mixed_or_used_as_fallback`（`[[workflows.audit.assignments.inspect]…]`） | 迷い（低） | 空の agents の拒否（models.py:134 の Field(min_length=1) | 残す |
| `test_self_cannot_be_mixed_or_used_as_fallback`（`[[workflows.audit.assignments.inspect]…]`） | L | self と担当の混在の拒否（models.py:137-142） | 消す |
| `test_self_cannot_be_mixed_or_used_as_fallback`（`[[workflows.audit.assignments.inspect]…]`） | L | fallback の self の拒否（models.py:144-149） | 消す |
| `test_reserved_self_cannot_hide_a_real_agent_definition` | S（低） | self を agent の名前に使わせない（models.py:172-177） | 残す |
| `test_self_assignment_is_preserved_without_an_agent_definition` | L | self を agent の定義無しで受け付ける（config.py:130-131）。壊れると self の割り当てが invalid_reference（終了コード 2）で止まる | 消す |
| `test_duplicate_models_are_rejected_across_all_candidates`（`[[agents.second]\nmodel = "model-one"\…]`） | S（中） | 同じ role の agents と fallback の全候補でモデルの重複を拒否する（config.py:128-137。fallback の候補を含めて見ること、別の agent でも同じモデルなら重複とすること（agent の名前の比較への退行も検出する）も確かめる | 残す |
| `test_duplicate_models_are_rejected_across_all_candidates`（3 件） | D | 代表: `test_duplicate_models_are_rejected_across_all_candidates`。agents どうし・primary と fallback・fallback どうしの重複は、どれも config.py:129-137 の同じ集合への追加と同じ判定で拒否する | 消す |
| `test_same_model_is_allowed_in_different_roles_without_constraint` | D | 代表: `test_recursive_overlay_replaces_arrays_and_preserves_other_fields`。role が違えば同じモデルを許す（モデルの集合を role ごとに作る、config.py:128）重複の拒否の正しく通る例 | 消す |
| `test_diversity_constraint_checks_fallback_candidates` | S（中） | exclude_same_model_as で指定した 2 つの role の候補（fallback を含む）に同じモデルがあれば拒否する（config.py:139-143。拒否が無いと、明示した役割間のモデルの制約（例: 実装とレビューを別のモデルにする）が黙って破られる | 残す |
| `test_diversity_constraint_accepts_disjoint_candidates` | S（中） | test_diversity_constraint_checks_fallback_candidates の拒否の正しく通る例 | 残す |
| `test_after_run_is_empty_unless_configured` | L | after_run の既定が空であること（models.py:156 の default_factory）。壊れて必須になると、after_run を書かないすべての設定が invalid_type（終了コード 2）で止まる | 消す |
| `test_after_run_requires_nonempty_argv_lists`（3 件） | L | after_run の各要素が空でない argv の配列であること（models.py:52・156-163）。壊れても、空の argv・空白の先頭は後処理の起動の失敗として summary の after_run に報告され、配列でない値は pydantic の検証が拒否する | 消す |
| `test_personal_config_replaces_after_run` | D | 代表: `test_recursive_overlay_replaces_arrays_and_preserves_other_fields`。個人設定の after_run = [] で雛形の後処理を止める | 消す |
| `test_personal_path_precedence`（5 件） | S（中） | 個人設定の場所の優先順（AGENT_RUNNER_CONFIG と ~ の展開、絶対パスの XDG_CONFIG_HOME、~/.config。ケースごとに別の分岐（明示、~ の展開、XDG、相対の XDG を無視、既定の場所）を確かめる | 残す |
| `test_nested_or_malformed_depth_is_rejected`（`[1]`） | S（中） | runner の担当（AGENT_RUNNER_DEPTH=1）からの入れ子の run を nested_invocation で拒否する（config.py:53-58） | 残す |
| `test_nested_or_malformed_depth_is_rejected`（2 件） | D | 代表: `test_nested_or_malformed_depth_is_rejected`。0 でない整数は代表と同じ config.py:54・57-58 の分岐で拒否する | 消す |
| `test_nested_or_malformed_depth_is_rejected`（`[TOP_SECRET_invalid]`） | L | 整数でない深さ（config.py:55-56）。変異で except の raise を外しても nested が未定義のまま UnboundLocalError で止まり（CLI は runner_failed… | 消す |
| `test_top_level_depth_is_allowed`（`[None]`） | S（中） | 入れ子の拒否（test_nested_or_malformed_depth_is_rejected[1]）の正しく通る例 | 残す |
| `test_top_level_depth_is_allowed`（`[0]`） | L | 0 を最上位として通すこと（config.py:54・57）。壊れると AGENT_RUNNER_DEPTH=0 のすべての run が nested_invocation か UnboundLocalError（終了コード 2）で止まり… | 消す |
| `test_top_level_depth_is_allowed`（`[]`） | D | 代表: `test_top_level_depth_is_allowed`。空文字は未設定と同じ config.py:51-52 の分岐で通る | 消す |
| `test_request_rejects_invalid_wire_data`（2 件） | L | 識別子の書式（models.py:30-33 の _identifier）。今の経路で識別子がパスの一部になるのは runner が uuid4().hex で作る request_id だけで（runner.py:372・409・580）… | 消す |
| `test_receipt_rejects_non_json_payloads`（3 件） | L | payload を JSON の値に限る（models.py:69-98）。adapter が作る payload に入ると、result.json の保存（cli.py:109）で直列化の誤り（runner_failed、終了コード 2）になるか… | 消す |
| `test_receipt_rejects_non_json_payloads`（`[payload1]`） | S（中） | 監査で戻した: 担当の JSON の回答に NaN・Infinity・-Infinity（または 1e400 のように float で inf になる数）があると、adapter は json.loads・raw_decode でそのまま読み（claude_code.py:64・73…（m02391・m02445・m02394・m02398…） | 残す |
| `test_receipt_rejects_non_json_payloads`（`[payload2]`） | S（中） | 監査で戻した: 担当の JSON の回答に NaN・Infinity・-Infinity（または 1e400 のように float で inf になる数）があると、adapter は json.loads・raw_decode でそのまま読み（claude_code.py:64・73…（m02443） | 残す |
| `test_receipt_rejects_cyclic_payload` | L | 循環の拒否（models.py:80-84） | 消す |
| `test_absent_adapters_are_unsupported_without_import_error_leaks`（7 件） | L | 固定名の adapter の読み込み（adapters/__init__.py:178-211）。Runtime の値に対応表（_MODULES、adapters/__init__.py:161-168）の項目が欠けると… | 消す |
| `test_unknown_runtime_cannot_select_an_arbitrary_module` | L | 未知の runtime を import のパスにしない（adapters/__init__.py:178-183）。runtime は設定の Literal で決まり、raise を外しても固定の接頭辞の名前… | 消す |
| `test_invalid_adapter_is_unsupported` | L | ADAPTER が Adapter の形でないとき unsupported にする（adapters/__init__.py:193-199）。壊れても runner が capabilities の AttributeError を unsupported にし（runner.py:401-408）… | 消す |

#### `test_environ.py`（4 件 → 1 件）

| テスト（群） | 分類 | 理由・防ぐ損害（重さ） | 扱い |
| --- | --- | --- | --- |
| `test_literal_environ_parses_proc_and_skips_malformed_entries` | S（低） | literal_environ は os.environ（起動時の locale の強制・起動後の変更を含む）でなく… | 残す |
| `test_literal_environ_falls_back_to_os_environ` | L | /proc を読めないときの os.environ への fallback。fallback の代入（25 行、covmap.json でこのテストだけが覆う）を外す変異は、その環境で dict(None) の TypeError で止まる | 消す |
| `test_literal_environ_caches_and_returns_copies` | L | キャッシュと写しを返すこと。キャッシュの条件・戻り値の文を外す変異は TypeError で止まる | 消す |
| `test_literal_environ_matches_proc_self_environ` | D | 代表: `test_literal_environ_parses_proc_and_skips_malformed_entries`。実際の /proc/self/environ との比較で、テストの中に同じ内包表記を写している | 消す |

#### `test_git_isolation.py`（2 件 → 2 件）

| テスト（群） | 分類 | 理由・防ぐ損害（重さ） | 扱い |
| --- | --- | --- | --- |
| `test_fixture_git_stays_in_its_temporary_repository` | S（高） | #166 の回帰（#230 の S の例「GIT_DIR の無視（#166 の test_git_isolation.py）」）の内側のテスト。単体では一時リポジトリを作るだけだが、下のテストが GIT_DIR を export した別の pytest でこの node ID を実行する | 残す |
| `test_inherited_git_dir_of_a_linked_worktree_does_not_reach_fixture_git` | S（高） | linked worktree の git rebase --exec が export する GIT_DIR を受け継いでも… | 残す |

#### `test_process.py`（63 件 → 24 件）

| テスト（群） | 分類 | 理由・防ぐ損害（重さ） | 扱い |
| --- | --- | --- | --- |
| `test_stdin_quotes_multiline_cwd_and_environment_are_literal` | S（高） | 引用符・$HOME・$()・改行を含むプロンプトを加工せずに stdin で渡して EOF まで閉じ、cwd と env をそのまま渡す。cwd が外れると担当は runner の cwd（親の checkout）で作業して書き込み、シェルを通すとプロンプトが黙って変わる… | 残す |
| `test_process_has_independent_session` | S（高） | #230 の S の例（setsid） | 残す |
| `test_large_parallel_output_is_streamed_to_files` | L | #230 の手がかりの L（大きな出力の流し込み）。2 つの pipe を並行に読まない実装は、子が満杯の pipe で止まり期限切れ（timed_out）として現れる | 消す |
| `test_secrets_split_across_reads_are_redacted_on_both_pipes` | S（高） | #230 の S の例（分割された秘密情報）。pipe の読み取りごとに伏せ字にすると、読み取りの境界をまたいだ秘密がログに残る | 残す |
| `test_abnormal_exit_returns_response_failed`（2 件） | S（中） | 元の CLI の非 0 の終了（SystemExit(7)）と signal による終了（SIGTERM → -15）を、response_failed と実測の終了コードで返す。2 件は別の条件（signal による終了を 0 にしない waitstatus_to_exitcode と、負の数を受け取る exit (-?\d+)） | 残す |
| `test_launch_oserror_is_safe_result` | L | 存在しないコマンドを launch_failed で返す | 消す |
| `test_invalid_control_outcome_is_safe_failure`（`[]`） | D | 代表: `test_control_eof_never_uses_successful_helper_exit`。報告の無い EOF を ValueError にする分岐（process.py:155-156）の単体の確認 | 消す |
| `test_invalid_control_outcome_is_safe_failure`（4 件） | L | 形式違い・余分な bytes・64 bytes 以上の報告を ValueError にする。これらの分岐（process.py:158-159・164-165、covmap.json でこのテストだけが覆う）を外す変異は、TypeError… | 消す |
| `test_control_eof_never_uses_successful_helper_exit` | S（中） | #230 の S の例（exit 0 を成功としない）の process の層 | 残す |
| `test_buffered_original_exit_survives_anchor_reap` | S（低） | 期限切れと同時に CLI が終わり、監督プロセスを回収した後に届く元の終了コードを捨てない（interfaces.rst「終了コードは監督プロセスではなく元の CLI の実測値」）。外すと timed_out のまま記録の exit_code が null になる（記録を失う） | 残す |
| `test_supervisor_preserves_literal_environment`（2 件） | S（低） | 監督プロセスは、Python の起動時の locale の強制（C・POSIX の loc…。起動の 2 つの分岐（posix_spawnp と、POSIX_SPAWN_CLOSEFROM の無い build の Popen）は別の文なので 1 件ずつ残す | 残す |
| `test_supervisor_preserves_literal_environment`（7 件） | D | 代表: `test_supervisor_preserves_literal_environment`。posix_spawn の locale1〜7 は、同じ /proc からの作り直し（_s… | 消す |
| `test_supervisor_preserves_literal_environment`（7 件） | D | 代表: `test_supervisor_preserves_literal_environment`。popen の locale1〜7 は、同じ /proc からの作り直し（_supervi… | 消す |
| `test_supervisor_rejects_unreadable_original_environment`（2 件） | L | /proc/self/environ が読めないとき、os.environ に頼らず CLI を起動しない。読み取りの失敗は通常の Linux では起きない（読めなければ /proc に頼るプロセスの木の追跡も動かない） | 消す |
| `test_supervisor_launch_paths_preserve_stdin_and_exit`（`[posix_spawn]`） | D | 代表: `test_abnormal_exit_returns_response_failed`。既定の起動（posix_spawnp）は conftest の差し込みの有無で同じ動き | 残す |
| `test_supervisor_launch_paths_preserve_stdin_and_exit`（`[popen]`） | S（中） | Popen の起動の分岐（POSIX_SPAWN_CLOSEFROM の無い build、_supervisor.py:44-49）で、stdin がそのまま CLI に届き…。壊れると、その build で失敗した CLI を成功と報告しうる | 残す |
| `test_command_does_not_inherit_private_control_socket` | S（中） | #230 の S の例（制御ソケットの漏れ） | 残す |
| `test_already_cancelled_does_not_spawn` | S（中） | 取り消し済みの event では何も起動しない。外すと、後処理（記録の保存など）が起動し、直後に止められるまで途中まで実行される | 残す |
| `test_immediate_exit_before_ownership_observation_stops_children`（`[0-False-python]`） | S（高） | #230 の S の例（孤児）。元の CLI が _Tree を作る前に終わって回収されても、監督プロセスを識別の anchor にして同じ group の孤児を見つけて止める | 残す |
| `test_immediate_exit_before_ownership_observation_stops_children`（7 件） | D | 代表: `test_immediate_exit_before_ownership_observation_stops_children`。同じ group の孤児の発見と停止を、終了コード（0/7）・pipe を閉じる子・shell の起動で組み合わせたもの | 消す |
| `test_leader_exit_stops_observed_descendants`（3 件） | D | 代表: `test_leader_exit_stops_observed_descendants`。escaped=False は同じ group に残る子で、group による発見は te… | 消す |
| `test_leader_exit_stops_observed_descendants`（`[0-True]`） | S（高） | leader が正常に終わっても、観測済みの子孫（setsid で group を離れ、SIGTERM を無視する子）を識別で追い続け、TERM → KILL で止める | 残す |
| `test_deadline_kills_term_resistant_leader`（`[False]`） | 迷い | 監査で戻した: 270 行: anchor を残したまま group の仲間を止める段を飛ばすと、anchor の解放の後に観測していない group の仲間を見つけられなくなる恐れがあるが、2 回目の _stop で止まる場面との違いを確かめていない。284 行: 終了時に stdin を閉じないと、大きな依頼文の書き込みの途中で期限になったときに transport が残り得るが、影響を確かめていない（m02569） | 残す |
| `test_deadline_kills_term_resistant_leader`（`[True]`） | L | #230 の手がかりの L（期限切れの kill。止まらなければ見て分かる） | 消す |
| `test_thread_event_cancels_running_process` | L | 実行中の取り消しで interrupted を返して止める。止める分岐（process.py:399-401）を外すと、Ctrl-C の後も担当が期限まで動いて CLI が戻らないので気付ける | 消す |
| `test_coroutine_cancellation_stops_leader_and_escaped_descendant` | S（高） | coroutine が取り消されても finally の停止を飛ばさず、leader と setsid で離れた子孫を止める…。外すと、結果を返さないまま担当の process が残り、停止の確認の記録も残らない | 残す |
| `test_unconfirmed_stop_is_reported` | S（高） | #230 の手がかりの「未確認の停止」の process の層の代表 | 残す |
| `test_repeated_cancellation_during_launch_still_stops_process` | S（高） | create_subprocess_exec の完了の途中で 2 回取り消されても PID を失わず、起動した process を止める…。外すと、起動した担当が誰にも管理されずに残る | 残す |
| `test_invalid_launch_arguments_return_safe_failure`（3 件） | L | adapter の誤った argv（空・空文字・NUL）を launch_failed で返す | 消す |
| `test_non_utf8_descendant_name_does_not_escape_tracking`（`[0.0]`） | S（高） | /proc/<pid>/stat の comm は任意の bytes で ')' も含みうる | 残す |
| `test_non_utf8_descendant_name_does_not_escape_tracking`（`[0.6]`） | D | 代表: `test_non_utf8_descendant_name_does_not_escape_tracking`。[0.6] は子の初期化を遅らせ、名前を変える前に一度観測される場合 | 消す |
| `test_reused_leader_group_is_not_signaled` | S（高） | #230 の S の例（PID の再利用）。leader の PID・PGID が別の process（starttime 違い）に再利用されたら、その group を自分のものとみなさず、signal を送らず… | 残す |
| `test_reused_descendant_identity_is_not_overwritten` | S（高） | 本物の group の中でも、記録した子孫の PID が再利用されたら（starttime 違い）、記録した識別を上書きせず、その子も取り込まず、停止を未確認とする | 残す |
| `test_group_after_leader_exit_requires_identity_anchor`（2 件） | S（高） | leader が終わった後は、観測済みの group member（識別が一致）が anchor のときだけ新しい孤児を取り込む（[True]、取り込みの正しく通る例）。2 件は anchored の真偽の別の分岐 | 残す |

#### `test_review_regressions.py`（15 件 → 6 件）

| テスト（群） | 分類 | 理由・防ぐ損害（重さ） | 扱い |
| --- | --- | --- | --- |
| `test_one_fallback_cannot_fill_two_parallel_role_slots`（`[1]`） | D | 代表: `test_one_fallback_cannot_fill_two_parallel_role_slots`。concurrency=1 で順に実行する場合 | 消す |
| `test_one_fallback_cannot_fill_two_parallel_role_slots`（`[2]`） | S（中） | 1 つの fallback は役割の 1 つの枠しか埋めない（runner.py:595-601 の claimed_fallbacks。防ぐ損害は、同じ担当（同じモデル）が同じ役割で 2 回使われて独立したレビューの数を偽ること（誤った結果の報告）と、fallback_exhausted を誤ること | 残す |
| `test_retained_receipts_are_scrubbed_even_when_invalid`（`[False]`） | D | 代表: `test_retained_receipts_are_scrubbed_even_when_invalid`。正しい JSON の受領 | 消す |
| `test_retained_receipts_are_scrubbed_even_when_invalid`（`[True]`） | S（高） | 停止を確認した試行の receipt.json を、受領として正しくなくても（壊れた JSON でも）伏せ字にする（runner.py:542-543。防ぐ損害は、保持する受領への秘密情報の漏れ | 残す |
| `test_abnormal_exit_without_receipt_is_response_failure` | D | 代表: `test_exit_zero_is_not_a_substitute_for_valid_receipt`。受領が無く終了コードが 7 なら response_failed | 消す |
| `test_success_receipt_survives_cli_immediate_exit_with_child`（`[False]`） | D | 代表: `test_immediate_exit_before_ownership_observation_stops_children`。CLI が受領を書いてすぐ終わり、パイプを持った子が残る場合 | 消す |
| `test_success_receipt_survives_cli_immediate_exit_with_child`（`[True]`） | D | 代表: `test_immediate_exit_before_ownership_observation_stops_children`。代表を残すケースに付け替えた（棚卸しで挙げた代表は別の担当が消した） | 消す |
| `test_nonregular_receipt_is_rejected_before_adapter_reads_it` | S | PR #247 のサイクル 1 で戻した（D-230-14）: `runner.py:557` の `state == "success"` の項を外す変異（m03231）の唯一の検出。その変異では保持物のある中断も response_failed になり、fallback の担当が起動する。中断だけを置き換える変更は、このテストも基準の全体も検出しない（申し送り） | 残す |
| `test_unconfirmed_stop_does_not_read_or_rewrite_live_receipt` | S（高） | 担当の停止を確認できないときは受領を読まず書き換えず（collect を呼ばない）、sensitive_paths に出し、fallback も起動しない…。防ぐ損害は、生きた書き手が FIFO・差し替えで受領を操作している間に読んで秘密を結果に写すこと・伏せ字にしたつもりで残すこと（秘密情報の漏れ） | 残す |
| `test_oversized_receipt_rejected_before_unbounded_collection` | L | 16 MiB を超える受領を adapter に渡さない（receipts.py:20 の st_size と 22-24 の読む量の 2 つの検査）。2 つの検査が重なっていて、どちらか 1 つを外しても他方が拒否するので結果は変わらない | 消す |
| `test_allowlisted_environment_is_the_literal_exec_environment`（`[exec_env0-C]`） | S（低） | runner を LC_CTYPE=C で起動した新しいインタープリタ（Python が os.environ の LC_CTYPE を C.UTF-8 に強制する）でも…。防ぐ損害は、利用者が設定していない値に書き換えた環境で担当を実行すること（環境の隔離） | 残す |
| `test_allowlisted_environment_is_the_literal_exec_environment`（3 件） | D | 代表: `test_allowlisted_environment_is_the_literal_exec_environment`。POSIX・LANG=C（強制で LC_CTYPE が足される）・LC_ALL=C の場合 | 消す |
| `test_exec_only_secrets_are_scrubbed_from_command_output` | S（高） | 起動時の環境（literal_environ）にだけあり os.environ に無い秘密の名前の値も、許可して子に渡したら stdout から伏せる…。防ぐ損害は、保持するログへの秘密情報の漏れ | 残す |

#### `test_runner.py`（87 件 → 49 件）

| テスト（群） | 分類 | 理由・防ぐ損害（重さ） | 扱い |
| --- | --- | --- | --- |
| `test_unavailable_registered_checkout_does_not_prevent_cli_run` | D | 代表: `test_audit_diagnoses_unavailable_baseline`。代表を残すケースに付け替えた（棚卸しで挙げた代表は別の担当が消した） | 消す |
| `test_success_has_verified_receipt_paths_and_observed_identity` | D | 代表: `test_only_allowlisted_environment_and_redacted_results`。正しい受領で success になる経路の確かめ | 消す |
| `test_exit_zero_is_not_a_substitute_for_valid_receipt`（`[options0-missing_result]`） | D | 代表: `test_partial_success_and_independent_worktrees`。受領が無い試行は missing_result（runner.py:262-267 の receipt が None の分岐） | 消す |
| `test_exit_zero_is_not_a_substitute_for_valid_receipt`（`[options1-invalid_result]`） | L | 壊れた JSON の受領は receipts.py:25 の Receipt.model_validate_json が必ず例外を投げ、成功にはなり得ない | 消す |
| `test_exit_zero_is_not_a_substitute_for_valid_receipt`（5 件） | S（中） | exit 0 を成功の代わりにしない（#230 の残す S の例）。防ぐ損害は、CLI が正しい結果を出していないのに success と報告すること（誤った結果の報告） | 残す |
| `test_exit_zero_is_not_a_substitute_for_valid_receipt`（3 件） | D | 代表: `test_exit_zero_is_not_a_substitute_for_valid_receipt`。request_id・agent_id・role が違う受領の拒否 | 消す |
| `test_exit_zero_is_not_a_substitute_for_valid_receipt`（`[options6-invalid_result]`） | D | 代表: `test_config_errors_are_categorized_without_input_or_traceback_leaks`。代表を残すケースに付け替えた（棚卸しで挙げた代表は別の担当が消した） | 消す |
| `test_exit_zero_is_not_a_substitute_for_valid_receipt`（`[options7-invalid_result]`） | D | 代表: `test_config_errors_are_categorized_without_input_or_traceback_leaks`。未知のキーを持つ受領の拒否は、全モデルに共通の models.py:59 の StrictModel の extra="forbid" にあり… | 消す |
| `test_exit_zero_is_not_a_substitute_for_valid_receipt`（2 件） | D | 代表: `test_exit_zero_is_not_a_substitute_for_valid_receipt`。json の役割の payload が list・None のときの拒否 | 消す |
| `test_exit_zero_is_not_a_substitute_for_valid_receipt`（2 件） | D | 代表: `test_exit_zero_is_not_a_substitute_for_valid_receipt`。終了コード 0 の受領の状態（awaiting_authentication・response_failed）をそのまま使う runner.py:295 | 消す |
| `test_exit_zero_is_not_a_substitute_for_valid_receipt`（2 件） | S（低） | 終了コードが 0 以外でも受領の awaiting_authentication・awaiting_approval を残す（runner.py:560 の集合の要素） | 残す |
| `test_exit_zero_is_not_a_substitute_for_valid_receipt`（`[options15-awaiting_approval]`） | D | 代表: `test_exit_zero_is_not_a_substitute_for_valid_receipt`。終了コード 0 の awaiting_approval | 消す |
| `test_exit_zero_is_not_a_substitute_for_valid_receipt`（`[options18-response_failed]`） | D | 代表: `test_exit_zero_is_not_a_substitute_for_valid_receipt`。受領が response_failed で終了コードが 0 以外 | 消す |
| `test_exit_zero_is_not_a_substitute_for_valid_receipt`（`[options20-invalid_result]`） | D | 代表: `test_exit_zero_is_not_a_substitute_for_valid_receipt`。受領が timed_out を名乗る場合 | 消す |
| `test_text_receipt_requires_nonblank_text`（2 件） | S（中） | text の役割の受領の形の検査（runner.py:279-285）。[ \n -invalid_result] は空白だけの文を成功にしない bool(payload.strip())（防ぐ損害: 空の回答を成功と報告する） | 残す |
| `test_text_receipt_requires_nonblank_text`（`[payload2-invalid_result]`） | L | text の役割で object の payload。isinstance(payload, str) を外しても dict に .strip() が無く AttributeError になり… | 消す |
| `test_adapter_success_cannot_bypass_missing_receipt` | S（中） | adapter が success と分類しても受領が無ければ missing_result（runner.py:266 の failure == "success" の条件）。防ぐ損害は、受領の無い試行を payload 無しの success と報告すること（誤った結果の報告） | 残す |
| `test_reported_state_keeps_the_adapter_state_before_the_exit_code_override` | S（低） | reported_state（adapter が出力から分類した状態 | 残す |
| `test_adapter_reported_state_is_recorded`（2 件） | S（低） | _reported の 1 つ目の分岐（adapter が渡した以前の状態を残す、runner.py:228-229）と 2 つ目の分岐（State でない値は無視し…。[awaiting_authentication] と [bogus] はそれぞれ別の分岐だけが守る | 残す |
| `test_partial_success_and_independent_worktrees` | S（中） | 同じ役割の担当の一部だけが成功したら batch は partial_success（runner.py:636-641）で… | 残す |
| `test_only_explicit_fallback_is_tried_in_order` | S（中） | 明示した fallback だけを書いた順に試し、fallback の無い役割では primary だけ（runner.py:594-608）。防ぐ損害は、別の担当・別の順で実行して誤った担当の結果を返すこと（#230 の残す S の例「fallback の順」） | 残す |
| `test_payload_check_refusal_is_invalid_result_and_tries_fallback`（`[returns-false]`） | S | PR #247 のサイクル 1 で戻した（D-230-14）: payload_check の False の戻り値を拒否する（`runner.py:290` の `is True`。例外の扱いとは別の守り）。緩めると拒否した payload を成功として返す | 残す |
| `test_payload_check_refusal_is_invalid_result_and_tries_fallback`（`[raises]`） | S（中） | 呼び出し側の payload の検査（payload_check）が例外を出したら invalid_result にして次の fallback へ進み…。防ぐ損害は、検査に通らない結果を success と報告することと、検査の例外の文（payload の内容を含み得る）が結果に漏れること | 残す |
| `test_self_has_no_process_or_worktree` | S（中） | self の担当は process・worktree を作らず、全てが self の batch は success ではなく self…。防ぐ損害は、self の batch を success と報告すること | 残す |
| `test_launch_failed_is_safe` | S（低） | 起動できない command は launch_failed（runner.py:553-554 の集合の要素）で、prompt を結果に出さない | 残す |
| `test_role_deadline_covers_fallback_attempts`（`[4.0]`） | S（中） | 役割の期限が worktree の準備と全ての fallback に共通で、残りの時間だけを各試行に渡す（runner.py:592・426・499-501）。防ぐ損害は、fallback ごとに期限が延びて役割の期限を超えて実行し続けること（#230 の残す S の例「共有の期限」） | 残す |
| `test_role_deadline_covers_fallback_attempts`（`[8.0]`） | D | 代表: `test_role_deadline_covers_fallback_attempts`。期限の値を変えただけの同じ確かめ | 消す |
| `test_workflow_preserves_literal_environment`（`[posix_spawn-default]`） | D | 代表: `test_only_allowlisted_environment_and_redacted_results`。許可リストが空なら PATH と AGENT_RUNNER_DEPTH だけが子に渡る（runner.py:474-475） | 消す |
| `test_workflow_preserves_literal_environment`（`[posix_spawn-allowlist]`） | D | 代表: `test_allowlisted_environment_is_the_literal_exec_environment`。許可した変数の値を os.environ ではなく起動時の環境（literal_environ）から取る（runner.py:378・475） | 消す |
| `test_workflow_preserves_literal_environment`（`[posix_spawn-adapter]`） | S（中） | adapter が LaunchSpec.env で足す値（空の値・改行を含む値を含む）が実行の環境に入る（runner.py:490。足されないと、認証が通る構成では DSH がホストの HOME に書き telemetry を送る（環境の隔離・サンドボックスの境界） | 残す |
| `test_workflow_preserves_literal_environment`（3 件） | D | 代表: `test_supervisor_preserves_literal_environment`。代表を残すケースに付け替えた（棚卸しで挙げた代表は別の担当が消した） | 1 件を残す |
| `test_cancel_during_run_prevents_fallback` | S（中） | 実行中に取り消したら interrupted にして fallback を起動しない（runner.py:555-556・604-605）。防ぐ損害は、利用者が止めた後に別の担当を起動すること（#230 の残す S の例「取り消しで fallback しない」） | 残す |
| `test_preexisting_cancel_launches_nothing` | S（中） | 実行前に取り消し済みなら何も起動せず worktree も作らない（runner.py:395-396）。防ぐ損害は、取り消した後の起動（費用と副作用） | 残す |
| `test_unconfirmed_stop_blocks_success_and_fallback` | S（中） | process._stop_confirmed を偽にするので、worktree の準備（git worktree add と hook）の停止を確認できない経路を確かめる。防ぐ損害は、生き残った処理が worktree に書き続ける間に成功と報告し、別の担当を並行して起動すること… | 残す |
| `test_concurrency_bounds_whole_assignments` | S（中） | concurrency が担当（fallback を含む）単位の同時実行の上限になる（runner.py:576・581 の semaphore）。防ぐ損害は、上限を超えた同時起動（#230 の残す S の例「並行の上限」） | 残す |
| `test_outside_change_to_already_dirty_file_is_warning_only` | S（中） | 担当が元の checkout の既に dirty なファイルを変えたら outside_changes に出す（runner.py:642-650 の配線。防ぐ損害は、作業範囲の外の変更を報告しないこと（checkout の監査） | 残す |
| `test_only_allowlisted_environment_and_redacted_results` | S（高） | 許可リストの変数だけを子に渡し（GIT_* は除く、runner.py:474-475）、adapter の AGENT_RUNNER_DEPTH を 1 に上書きし…。防ぐ損害は、許可していない資格情報が担当の CLI に渡ることと、保持する成果物に秘密の値が残ること（秘密情報の漏れ） | 残す |
| `test_invalid_direct_config_is_rejected_before_execution` | D | 代表: `test_duplicate_models_are_rejected_across_all_candidates`。代表を残すケースに付け替えた（棚卸しで挙げた代表は別の担当が消した） | 消す |
| `test_nested_invocation_and_invalid_inputs_fail_closed` | S（中） | AGENT_RUNNER_DEPTH=1 の中からの run_workflow を nested_invocation で拒否する…。防ぐ損害は、runner の担当の中から runner が担当を入れ子に起動すること（AGENTS.md の運用） | 残す |
| `test_write_exceptions_follow_the_work_scope_lines` | S（低） | write_exceptions を作業範囲の 2 行の後に見出しと 1 行ずつで並べ、渡さない呼び出しでは 2 行のまま（runner.py:446-457）。防ぐ損害は、許可した書き込み先が担当に伝わらないこと・許可していない見出しが付くこと（担当への指示の誤り） | 残す |
| `test_write_exceptions_keep_non_ascii_spaces_inside_a_line` | L | 全角空白・NBSP・Cf/Co/Cn を行の途中に含む値を受け付ける（拒否しすぎない） | 消す |
| `test_invalid_write_exceptions_are_rejected_before_any_output`（3 件） | D | 代表: `test_invalid_write_exceptions_are_rejected_before_any_output`。改行・CR・NEL は splitlines と Cc の両方の条件が拒否するので、条件を 1 つ外す変異ではこれらのケースの結果は変わらない | 消す |
| `test_invalid_write_exceptions_are_rejected_before_any_output`（2 件） | S（中） | write_exceptions の 1 行の検査（runner.py:96-107 の _single_line）を出力の前に行う。防ぐ損害は、改行・制御文字を含む値で作業範囲の行を増やし、担当への指示を書き換えること（prompt への注入） | 残す |
| `test_invalid_write_exceptions_are_rejected_before_any_output`（`[a\tb]`） | D | 代表: `test_invalid_write_exceptions_are_rejected_before_any_output`。タブは Cc の条件（runner.py:106）だけが拒否する | 消す |
| `test_invalid_write_exceptions_are_rejected_before_any_output`（`[ a]`） | S（低） | 前後の空白を拒否する value == value.strip()（runner.py:104）を外す変異を検出する代表。防ぐ損害は、字下げで作業範囲の行の形を変える値を受け付けること | 残す |
| `test_invalid_write_exceptions_are_rejected_before_any_output`（5 件） | D | 代表: `test_invalid_write_exceptions_are_rejected_before_any_output`。前後の空白（ASCII・全角・NBSP）は同じ value == value.strip() の条件が拒否する（str.strip は Unicode の空白を除く） | 消す |
| `test_invalid_write_exceptions_are_rejected_before_any_output`（`[]`） | D | 代表: `test_invalid_write_exceptions_are_rejected_before_any_output`。空文字は value != "" と splitlines（"".splitlines() は [] で [""] と違う）の両方が拒否するので、条件を 1 つ外しても拒否のまま | 消す |
| `test_invalid_write_exceptions_are_rejected_before_any_output`（`[1]`） | L | str でない値。type(value) is str（runner.py:102）を外す変異を検出するのはこのケースだけだが、外すと 1.strip() が AttributeError を投げ… | 消す |
| `test_a_bare_string_is_not_split_into_exceptions` | S（低） | write_exceptions に str を 1 つ渡すと RunnerError（runner.py:336・341）。壊れると例外が黙って捨てられ（runner.py:336 で空になる）、許可したはずの書き込み先が担当に伝わらない | 残す |
| `test_existing_or_symlink_output_is_never_reused` | S（中） | output_dir が既にある・壊れた symlink のときは再利用せず RunnerError（runner.py:369 の exist_ok なしの mkdir）。防ぐ損害は、前の実行の成果物（receipt.json・CLI の result.json）を上書き・混在させること（記録の上書き） | 残す |
| `test_default_artifact_directory_is_unique` | F∩S（中） | 既定の成果物の置き場所が /tmp の create-reso-world-agent-runner- 接頭辞の一意のディレクトリであること（runner.py:362）。防ぐ損害は、伏せ字にできなかった成果物（sensitive_paths）を含む保持物がリポジトリ・worktree の中など一時領域の外に置かれること… | 残す |
| `test_invalid_mutated_config_does_not_emit_serializer_values` | S（中） | 不正に書き換えた設定の再検証で pydantic の serializer の警告を出さない（config.py:149 の model_dump(warnings=False)）。警告は不正な値をそのまま stderr に出すので、防ぐ損害は設定の値の漏れ | 残す |
| `test_invalid_observed_identity_does_not_emit_serializer_values` | S（中） | adapter が観測した identity が不正な型でも serializer の警告を出さず invalid_result にする…。防ぐ損害は、CLI の出力から得た値（秘密を含み得る）が警告として stderr に出ること | 残す |
| `test_missing_receipt_file_is_missing_not_a_parse_failure` | S（低） | adapter が受領を読もうとして FileNotFoundError を出したら invalid_result ではなく missing_result… | 残す |
| `test_receipt_created_before_launch_is_never_reused` | S（中） | 起動前（adapter.prepare の中）に作られた受領は使わず invalid_result（runner.py:486-487）。防ぐ損害は、古い・前もって置かれた受領を今回の結果として success と報告すること（#230 の残す S の例「起動前の受領の拒否」） | 残す |
| `test_unproven_capability_is_unsupported` | 迷い（中） | adapter の noninteractive・stdin が True と保証されていない（真に見える文字列）なら起動せず unsupported…。保証の無い adapter を足したときに起動すると、対話の待ちで期限切れ（見て分かる）になるのか、無人で対話の操作を進める（気付けない）のかを決められない | 残す |
| `test_checkout_preparation_is_supervised`（`[none]`） | D | 代表: `test_checkout_preparation_is_supervised`。期限切れで準備を止める場合（[none]）と、期限切れの後に取り消した場合（[late_cancel]） | 消す |
| `test_checkout_preparation_is_supervised`（`[cancel]`） | S（高） | worktree の準備（post-checkout hook と、setsid して SIGTERM を無視する子）を監督する。防ぐ損害は、準備のログへの秘密情報の漏れ（runner.py:430 の secrets を確かめるのはこのテストだけ）と、準備が終わらないまま担当を起動すること | 残す |
| `test_checkout_preparation_is_supervised`（`[late_cancel]`） | S（中） | 監査で戻した: worktree の準備が失敗した・停止を確かめられないときも担当を起動し、不完全な checkout で動いた結果を返し得る（未検証の状態での実行）（m02933・m03101） | 残す |
| `test_cancel_at_preparation_completion_retains_log_paths` | S（中） | 準備が終わった時点で取り消されたら、担当を起動せず、結果のログのパスを準備のログ（worktree.*.log）のままにする…。防ぐ損害は、起動していない担当のログのパス（存在しない stdout.log）を結果に記録して準備のログに辿れなくすること（記録の取り違え | 残す |
| `test_devin_retained_export_is_redacted_after_nonzero_exit` | S（高） | Devin が attempt に残す export.json（ATIF の記録 | 残す |
| `test_devin_retained_export_is_redacted_after_timeout` | D | 代表: `test_devin_retained_export_is_redacted_after_nonzero_exit`。期限切れで止めた後の export.json の伏せ字 | 消す |
| `test_devin_retained_export_is_redacted_after_interruption` | D | 代表: `test_devin_retained_export_is_redacted_after_nonzero_exit`。取り消し（interrupted）で止めた後の export.json の伏せ字 | 消す |
| `test_unconfirmed_stop_never_reads_or_rewrites_devin_export` | S（高） | 停止を確認できない試行では、生きた書き手が差し替え得る export.json と receipt.json を読まず書き換えず、sensitive_paths に出し…。防ぐ損害は、書き手が残っている間に伏せ字にしたつもりで秘密の値を残すことと、その path を報告しないこと（秘密情報の漏れ） | 残す |
| `test_unsafe_devin_export_is_retained_reported_and_never_collected`（`[symlink]`） | S（高） | export.json が symlink なら辿らず書き換えず、sensitive_paths に出して collect しない…。防ぐ損害は、伏せ字の書き換えで attempt の外のファイル（sentinel）を上書きすること（誤った対象の上書き）と、伏せ字にできない記録を報告しないこと | 残す |
| `test_unsafe_devin_export_is_retained_reported_and_never_collected`（`[fifo]`） | S（中） | 監査で戻した: FIFO などの特殊ファイルを伏せ字にできたとして True を返し、置き換えた空・部分の内容を収集に回し、sensitive_paths にも載せない（安全に伏せ字にできない保持物を収集に使わない、の守りが外れる）（m02698・m02544） | 残す |
| `test_devin_export_redaction_fault_never_reaches_collection` | S（高） | export.json を伏せ字にできなかったら（redact_file が False）…。防ぐ損害は、秘密の残る記録を collector が読んで payload・identity に写すことと、その記録を報告しないこと | 残す |

#### `test_workspace.py`（47 件 → 18 件）

| テスト（群） | 分類 | 理由・防ぐ損害（重さ） | 扱い |
| --- | --- | --- | --- |
| `test_resolve_revision_pins_commit_not_branch` | S（中） | 指定の revision（HEAD・HEAD~1）を変わらない commit ID に解決する。revision を無視する・別の commit を返す変更は、担当が別の base で作業した結果をもっともらしく返す | 残す |
| `test_revision_errors_are_safe`（5 件） | L | option（--help・-q）・存在しない revision・commit でない blob・NUL を WorkspaceError にし、git の診断を出さない。事前の検査（workspace.py:65-66、covmap.json でこれらのテストだけが覆う 66 行）を外しても… | 消す |
| `test_repository_must_exist_and_be_git` | L | 存在しない・git でないディレクトリの拒否 | 消す |
| `test_worktree_is_fresh_detached_and_preserves_dirty_original` | L | create_worktree は runner が使わない同期の作成で、呼び出し元はテストだけ（git grep）。壊れれば、create_worktree を fixture に使うテストがエラーで止まる | 消す |
| `test_worktree_never_overwrites_existing_directory` | L | create_worktree（テスト用）の既存のディレクトリの拒否 | 消す |
| `test_audit_detects_existing_dirty_content_edits`（2 件） | S（高） | #230 の S の例（checkout の監査）。untracked の symlink は参照先の文字列で検出する（[symlink]、別の分岐） | 残す |
| `test_audit_detects_existing_dirty_content_edits`（2 件） | D | 代表: `test_audit_detects_existing_dirty_content_edits`。[staged] は index の dirty な blob と作業ツリーの変更で、内容のハッシュ（184-190）は [tracked] と同じ分岐 | 消す |
| `test_audit_detects_checkout_mutations`（`[delete]`） | D | 代表: `test_audit_detects_existing_dirty_content_edits`。削除した追跡ファイルは、内容と mode の入力が無くなって必ず指紋が変わる | 消す |
| `test_audit_detects_checkout_mutations`（4 件） | S（高） | 指紋の入力を 1 つずつ確かめる: untracked の一覧（[add]、157-158）、mode（[chmod]、181）、index の blob（[index]…。どれも別の文で、外すとその種類の変更（新しいファイル・権限・staged の内容・commit）を黙って見逃す | 残す |
| `test_audit_ignores_new_checkouts_and_gitignored_resources` | L | 誤って変化と報告する側（誤検知）の確認。ignored の資源や snapshot の後に作った checkout を変化とすると… | 消す |
| `test_audit_reports_disappeared_checkout` | D | 代表: `test_audit_distinguishes_changes_from_unavailability`。snapshot の後に消えた（移動した）checkout の報告 | 消す |
| `test_repair_of_moved_main_and_linked_worktree_preserves_all_resources` | S（高） | 監査は観察だけで、消えた登録を自動で回収（prune・repair・remove）しない（モジュールの docstring… | 残す |
| `test_audit_does_not_follow_untracked_symlink` | L | symlink の参照先は監査の範囲外（interfaces.rst）。受け取りの入口が拒否して気付ける） | 消す |
| `test_audit_does_not_follow_symlink_ancestors` | L | symlink に置き換えた追跡ディレクトリの先を読まない（164-174）。この分岐の変異（parent /= part・linked_parent・continue など、covmap.json でこのテストだけが覆う）は… | 消す |
| `test_audit_detects_submodule_dirty_content` | S（高） | 初期化済みの submodule の作業ファイルの変更を、親の checkout の監査で検出する（191-192 の再帰） | 残す |
| `test_unavailable_registered_checkout_is_a_warning`（5 件） | D | 代表: `test_audit_diagnoses_unavailable_baseline`。監査できない登録（prunable・locked・gitdir の破損・通常ファイル・読めない）を None にし、main の指紋を続けて取り、その登録を報告する | 消す |
| `test_checkout_recovered_after_snapshot_still_warns` | D | 代表: `test_audit_distinguishes_changes_from_unavailability`。snapshot の時に監査できず、後で直った checkout を報告し続ける | 消す |
| `test_audit_diagnoses_unavailable_baseline`（`[missing-checkout_missing-False-True]`） | S（高） | 開始前に監査できない登録を unavailable_before の finding（理由・locked・prunable）として返し… | 残す |
| `test_audit_diagnoses_unavailable_baseline`（`[locked-checkout_missing-True-False]`） | S（中） | 監査で戻した: 理由を付けてロックした worktree（git worktree lock --reason）を locked=false として記録する（m03407） | 残す |
| `test_audit_diagnoses_unavailable_baseline`（2 件） | D | 代表: `test_audit_diagnoses_unavailable_baseline`。gitdir の破損・読めないディレクトリは、_git の失敗（git_unavailable… | 消す |
| `test_audit_diagnoses_unavailable_baseline`（`[file-not_directory-False-True]`） | L | [locked] は lock の理由付きの locked の読み取り（206 の startswith）、[file] は not_directory の分岐…。外しても finding と起動前の拒否は変わらず、理由が git_unavailable に、locked が false になるだけ | 消す |
| `test_audit_distinguishes_changes_from_unavailability`（`[change]`） | D | 代表: `test_audit_detects_existing_dirty_content_edits`。内容の変更を content_changed として報告する | 消す |
| `test_audit_distinguishes_changes_from_unavailability`（2 件） | S（高） | [disappear]: snapshot の後に消えた checkout を unavailable_after（checkout_missing）として報告する… | 残す |
| `test_preflight_registration_failure_is_environment_diagnostic` | D | 代表: `test_registration_list_failure_still_stops_snapshot`。登録の一覧が読めないとき、空の snapshot で起動前の監査を通さない守りは test… | 消す |
| `test_unavailable_fingerprint_is_attempted_once` | L | 監査できなかった基準の checkout の指紋を、監査の時に取り直さない（276 の continue） | 消す |
| `test_registration_list_failure_still_stops_snapshot` | S（高） | worktree の登録の一覧が読めないとき、snapshot_checkouts は空の基準を返さず WorkspaceError で止める。空の基準を返す変更は、その後の監査が何も報告せず（全ての checkout の変化を黙って通す）、起動前の監査も通してしまう | 残す |
| `test_git_helper_timeout_has_safe_diagnostics` | L | git の補助の期限（10 秒）が無いと、止まった git で起動前の監査が止まったままになり、見て分かる | 消す |
| `test_async_preparation_uses_pinned_commit_and_safe_environment` | S（高） | #230 の S の例（GIT_* の無視）の準備の経路。_git の 57 行とは別の文） | 残す |
| `test_git_preparation_stops_term_resistant_child_of_exited_hook` | S（高） | checkout の hook（post-checkout）が残した SIGTERM を無視する子を、準備の監督が止める | 残す |
| `test_git_common_dir_of_a_linked_worktree_is_the_main_git_directory` | 迷い（低） | linked worktree から共有の Git のディレクトリ（main の .git）を返す。誤ると指示の書き込み先が黙って変わるが、指示は強制されず担当の git は実際の共有のディレクトリに書くので損害は小さく、S か L か決められない | 残す |
| `test_git_common_dir_ignores_ambient_git_routing` | S（高） | #230 の S の例（GIT_DIR の無視）の _git の代表。外から渡された GIT_DIR が別のリポジトリを指しても、_git は GIT_* を除いた起動時の環境で動き、指定の checkout の値を返す | 残す |
| `test_git_common_dir_of_a_non_repository_is_a_workspace_error` | L | git でないディレクトリは git rev-parse が失敗して WorkspaceError で止まる（エラーで止まる経路） | 消す |

