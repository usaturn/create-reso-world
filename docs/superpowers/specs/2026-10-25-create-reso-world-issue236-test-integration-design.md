# Issue #236: テストの総数を測り、共有の補助を整理して、1/3 に届いたかを確かめる

## 管理・実行許可

- 文書管理・コード対象: `usaturn/create-reso-world`。対象 Issue: https://github.com/usaturn/create-reso-world/issues/236（親 #228、ボード `test-reduction-board`、子のキー `integration`。先行の #230〜#235 はすべて completed で close し、PR #247・#255・#246・#254・#244・#245 は `main` に含まれる）
- 状態: draft
- 関連 Plan: `docs/superpowers/plans/2026-10-25-create-reso-world-issue236-test-integration.md`
- DOC_ROOT・CODE_ROOT: `/workspaces/reso-world/.worktrees/issue-236-test-integration`（branch `feat/issue-236-test-integration`）。PARENT_ROOT: `/workspaces/reso-world`
- 実行許可: 2026-10-24（UTC 15:45 ごろ）、利用者が Claude Code で次を実行した

  ```text
  /issue-to-pr #236 --merge
  ```

  issue-to-pr の委任により、通常の設計判断を推奨案で決め、Spec・Plan の commit、実装、検証、push の前の検査、push、PR の作成（`Closes #236`）まで行い、`--merge` により PR 修正ループ（pr-review-fix-loop）を回して、修正不要と確かめられたらループの `finalize.py` がマージと関連 Issue の更新を行う。Issue の「マージは利用者が行う（利用者が明示した指示がある場合を除く）」は、この `--merge` を明示の指示として扱う
  - 方針は #228 の「利用者の決定（2026-10-21）」と「削除と採用の基準」に従い、議論し直さない。ほかの判断は、利用者に確認を取らずに決めたエージェントの判断であり、内容の承認（`approved`）ではない
- #236 固有の利用者の決定の写しは無い。2026-10-23 の司令塔の run（`/workspaces/reso-world/tmp/agents/commander-230-231-233-236.z9emizj5/`）は #236 を起動する前に終わり、`decisions/issue-236.md` は作られていない（`commander-state.json` の `commander_ended.not_done`）。この run は利用者の直接の指示で、決定のファイルの指定は無い。司令塔への指示のファイル（`docs_draft/` の下）は、`AGENTS.md` の「`docs_draft/` はタスクで指定された場合だけ読む」に従い読んでいない
- ループのオプション（`loop.py check-options` の出力）: `max_cycles = 3`・`assign = {}`・`template = .devcontainer/agent-runner.toml`・`config = null`（どれも既定の適用）。割り当ては、レビュー（`inspect`）が `pi-gpt`・`devin-swe`・`pi-deepseek`・`cursor-grok47`、修正（`implement`）が `claude-opus`、自己レビュー（`self-review`）・修正の確認（`fix-check`）が `self`（どれも設定のとおり）。いずれも `fallback = []`
- 実装の担当: `implement_task.py check` は `assignment.agents = ["self"]`・`fallback = []`・`self: true`（雛形 `.devcontainer/agent-runner.toml` の既定の適用。利用者の指定ではない）
- 予約: `refs/heads/agent-claims/issue-236` = `4163db8351cc360b9f18381522e6518b881f072c`（https://github.com/usaturn/create-reso-world/issues/236#issuecomment-6386249923）
- 基準: 着手時は `origin/main` の `bdbe02b`（PR #255 のマージ）。作業中に PR #258（`6b6fd9a`）・PR #256（`0959610`）・PR #257（`dcdc0d9`）がマージされたので、push の前の branch を `dcdc0d9` に載せ直した（D-236-21）

## 意図

#228 の最後の子として、6 つの領域の子の後のテスト全体を #228 の「計測」で測り、共有の補助（`tools/test_support/`、ルートの `conftest.py`）と pytest の設定・テストの入口・README の節から、使われなくなったものと古くなった記述を除く。件数・行数がともに 1/3 以下なら、#228 の完了の条件 2 を満たしたと記録する。届かなければ、残ったテストを守りの重さの順に並べた一覧を #228 に出して、どこまで削るかの判断を利用者に渡す（#228 の決定 6）。

この子はテストを消さない。一覧に載せるだけで、どこまで削るかは利用者が決める（Issue の「変えないもの」）。

## 範囲

- 変える: `tools/test_support/`、ルートの `conftest.py`、`pyproject.toml` の `[tool.pytest.ini_options]`、`.devcontainer/run-tests.bash`、`tests/scripts/test-superpowers-python.bash`、`README.md` の「テスト」の節、`.devcontainer/README.md` の「テストの実行」の節、この子の Spec・Plan（Issue の「変えてよいもの」）。実際に変えるのは下の決定記録のとおり
- 変えない: 領域ごとの子のテストとコード（使われていない fixture が残っていても一覧に載せるだけ。D-236-13）、`AGENTS.md`、Meshy のファイル、`.github/workflows/ci.yml`、`.gitleaks.toml`、README のほかの節
- 外部への書き込み: #236 へのコメント（予約・計測・完了）、#228 へのコメント（計測の結果と一覧）、PR。#228 の本文（実行マップ・公開台帳）は調整役の担当なので変えない

## 計測

#228 の「計測」のコマンドを、create-reso-world の checkout のルートで、コミット済みの状態で実行した。件数は pytest の `testpaths` の収集数、`tests/scripts` の Python の収集数（Meshy を除く）、bash のテストの本数（Meshy を除く）の合計、行数は計測の対象のファイルの行数の合計である。

| 指標 | 基準値（`7d44355`） | 着手時（`bdbe02b`） | 比 | 目標（1/3 以下） | 届いたか |
| --- | --- | --- | --- | --- | --- |
| 件数 | 3,646（3,553 + 61 + 32） | 1,279（1,224 + 33 + 22） | 35.1% | 1,215 以下 | 届かない（64 件多い） |
| 行数 | 45,024 | 28,470 | 63.2% | 15,008 以下 | 届かない（13,462 行多い） |

- この PR の後の値は「計測の結果（この PR の後）」に書く（この PR はテストを消さないので、件数は変わらない）
- 基準値は、使い捨ての worktree（`7d44355`）で同じコマンドを実行して、#228 の値を再現した

### 子ごとの内訳

領域の分け方は #228 の「実行マップ」の担当ファイルのとおりで、`tests/scripts/test-superpowers-python.bash`（`integration` の担当）は、#228 の「調査の見積もり」の表に合わせて `script-tests` に数える。件数の括弧は pytest + unittest + bash。

| 子のキー | 基準値（`7d44355`） | 着手時（`bdbe02b`） | 件数の比 | 行数の比 |
| --- | --- | --- | --- | --- |
| `agent-runner-tests`（#230） | 1,058（1,058+0+0）・10,351 行 | 275（275+0+0）・5,430 行 | 26.0% | 52.5% |
| `pr-review-tests`（#231） | 548（548+0+0）・9,626 行 | 288（288+0+0）・7,302 行 | 52.6% | 75.9% |
| `review-helper-tests`（#232） | 1,056（1,056+0+0）・9,919 行 | 427（427+0+0）・7,093 行 | 40.4% | 71.5% |
| `skill-tests`（#233） | 472（472+0+0）・5,923 行 | 195（195+0+0）・4,087 行 | 41.3% | 69.0% |
| `devcontainer-tests`（#234） | 437（419+0+18）・5,778 行 | 51（39+0+12）・2,481 行 | 11.7% | 42.9% |
| `script-tests`（#235） | 75（0+61+14）・3,293 行 | 43（0+33+10）・1,993 行 | 57.3% | 60.5% |
| `integration`（#236。`tools/test_support/`・ルートの `conftest.py`） | 0・134 行 | 0・84 行 | — | 62.7% |
| 合計 | 3,646・45,024 行 | 1,279・28,470 行 | 35.1% | 63.2% |

- 着手時の値には、ボードの子のほかに、子のマージの後の PR の変更も入っている。`agent-runner-tests` は #243（PR #249）の DSH の担当の撤去（`5678691`、DSH の adapter のテストと偽の CLI で約 1,650 行）と `f12c400`（`test_models.py` に 58 行）、`review-helper-tests` は `a532330`・`172bc8f`・`5678691`、`devcontainer-tests` は `d33f01d`。子の Issue に書かれた前後の値は、それぞれの着手時の base と範囲で測ったもので、この表の値とは base が違う
- `integration` の 134 → 84 行は、#243 の撤去（`5678691`）で消えた `tools/test_support/dsh.py`（50 行）による

## 決定記録

下の表は、利用者に確認を取らずに決めたエージェントの判断である。

| ID | 選択した案 | 検討した別案 | 選択理由 | 委任指示または停止条件 |
| --- | --- | --- | --- | --- |
| D-236-1 | `tools/test_support/texts.py` の `FINDING_REASON` と、`__init__.py` のその import・`__all__` の項目を消す。`texts.py` の docstring を、残る `FINDING_CONTENT` だけの説明に直す（今の docstring は、消えた `ReviewFinding.content` と planner の `reason` を挙げている） | `FINDING_REASON` を残す | Issue の受け入れ（`git grep` で使われていない。調査の時点で既に使われていない） | Issue の「インターフェース」（使われていないと確かめたものだけ消す） |
| D-236-2 | `FINDING_CONTENT` と、`__init__.py` のその再 export は残す | 再 export を消し、`__init__.py` を docstring だけにする | Issue の確かめ方（`__all__` と各モジュールの名前を `git grep -n <名前> -- ':!:tools/test_support/'` で 1 つずつ）では、`FINDING_CONTENT` は issue-to-pr の 2 つのテストが使う。パッケージの経路（`from tools.test_support import ...`）で使うものは無いが、名前ごと消せるのは使われていない名前だけ。再 export を外す変更は、使われている名前の公開の場所を変えるので、この子では行わない | Issue の「インターフェース」 |
| D-236-3 | `plugin.py` の `outside_runner`、ルートの `conftest.py` の `drop_inherited_git_environment` は変えない | — | `outside_runner` は 12 のテストのモジュールが `pytestmark` で使う。`drop_inherited_git_environment` は autouse で、名前で呼ぶものは無いが全ての pytest のテストに効く（回帰テスト `tools/agent_runner/tests/test_git_isolation.py` が実在する） | — |
| D-236-4 | `pyproject.toml` の `pythonpath` から 2 つ目の `tools/devenv_migration/tests` と、その理由のコメントの行を消す | 残す | #234 が兄弟ファイルからの import をやめた（#234 の D-234-2、#228 への申し送り）。`git grep` で `tools/devenv_migration/tests` のテストに兄弟のモジュールの import が無いことを確かめた。1 つ目の `.`（`tools.*` の import）、`testpaths` の 4 つ（どれも実在する）、`--import-mode=importlib`（`test_adapter.py` が 3 つのディレクトリにあり、コメントの理由が今も当たる）は残す | Issue の受け入れ |
| D-236-5 | `.devcontainer/README.md` の「テストの実行」の pytest の行に `tools` を足し、「CI も同じコマンドを実行する」を、CI の skill-tests のジョブが `tools` を含まないことが分かる書き方に直す | (a) 変えない、(b) CI のジョブに `tools` を足す | (a) #149 の Spec の C-11（`docs/superpowers/specs/2026-10-18-create-reso-world-issue149-agent-runner-core-design.md`）は、`tools/devenv_migration/tests` を `.devcontainer/test-pi-migrations.bash` と二重に実行しないために、この節と `ci.yml` を変えないと決めた。その `test-pi-migrations.bash` は #234 が消したので前提が無くなり、今はこの節のコマンドで `tools` のテスト（`tools/agent_runner`・`tools/devenv_migration`）が 1 つも実行されない。`README.md` の「テスト」と `testpaths` は `tools` を含む。(b) `.github/workflows/ci.yml` はこの子の範囲の外で、`AGENTS.md` の「GitHub Actions」は private の CI を止めている | Issue の受け入れ（README が残ったテストの実行のしかたと合う） |
| D-236-6 | `README.md` の「テスト」、`.devcontainer/run-tests.bash`、`tests/scripts/test-superpowers-python.bash` は変えない | — | どれも消えたディレクトリを指さず、残ったテストの実行のしかたと合っている（確かめたことは「受け入れ条件との対応」） | — |
| D-236-7 | 件数・行数のどちらも 1/3 に届かないので、一覧を作り #228 にコメントする。この子は一覧を出したら completed で close し（PR の `Closes #236` を `finalize.py` が更新する）、#228 は open のまま残す | — | Issue の受け入れ・#228 の決定 6 | Issue の受け入れ |
| D-236-8 | 一覧の単位は、今の `main` に残っているテストの関数（pytest・unittest。parametrize は収集数を件数にした 1 行）と、bash のテストの場面の群（ファイルの中で、重さと「迷い」が同じ場面をまとめる）にする。子の表が 1 つの関数の parametrize のケースで分類・重さ・迷いを分けているとき（例: `test_review_records.py::test_invalid_records_are_rejected` の「S（高・中）」、`test_review_findings.py::test_invalid_documents_name_the_problem` の「S 中 4 / 迷い 2」、`test_process.py::test_supervisor_launch_paths_preserve_stdin_and_exit` の D と S）は、分類・重さ・迷いが同じケースの群ごとに行を分け、件数はその群のケースの数にする | (a) 子の棚卸しの表の行をそのまま使う、(b) ファイルごと、(c) 分けた関数を、いちばん重いケースの段に 1 行で置く、(d) 迷いのケースが 1 つでもあれば関数ごと迷いの段に置く | (a) 表の行の単位は子ごとに違い（関数、parametrize のケース、説明文の群）、#243 などの後の変更で今のテストと合わない行がある。行数を行に割り当てられない。(b) 重さの順に並べられない。(c) は迷いのケースを先頭から外し、(d) は高の守りを先頭に出す。件数の目標まで 64 件しかなく、ケースの段の違いが目標に届く位置を動かすので、表が分けたとおりに分ける（brainstorming の builder check の問い 1 への判断） | Issue の受け入れ（テストまたはテストの群ごとに） |
| D-236-9 | 分類・防ぐ損害・重さ・「迷い」は、6 つの子の Spec の棚卸しの表と、レビュー修正の記録（同じ Spec の後の節と、`pr24x-...-review-fixes-design.md`）から取る。表で「消す」なのに残っているテストは、戻した記録の理由を使う。表に無いテスト（子の後の PR が足した・変えたもの）と、記録が見つからないものは、`AGENTS.md` の「テストの採用基準」で #236 が判定し、一覧で「#236 の判定」と分かるようにする | 全てのテストを #236 が分類し直す | #228 の決定（議論し直さない）。分類の根拠は子の棚卸し。#236 の判定は、子の表で決まらないものに限る | #228 の「利用者の決定」 |
| D-236-10 | 表に重さが書かれていない S・F∩S・迷いは、#228 の「守りの重さ」（高: 秘密情報の漏れ・データの消失・誤った対象への破壊的な操作・未検証のマージ。中: 誤った結果の報告・記録の取り違え。低: 作業の結果を変えないもの）で #236 が決め、「重さは #236 の判定」と分かるようにする。表の重さに幅がある（「中-低」「高・中」）のにケースを分けていないものは、重い方にする | (a) 重さの無い行を別の群にする、(b) 幅は軽い方にする | (a) 並べ替えに重さが要る。定義は #228 にある。(b) 軽い方にすると、重い方の守りを含むテストが先に消える位置に来る。#228 の決定 6（気付けない損害を防ぐテストを数のために消さない）に近い側にした | #228 の「守りの重さ」 |
| D-236-11 | 計測の対象の全ての行を、一覧のどれか 1 行にだけ割り当てる（下の「一覧の作り方」の割り当て）。テストの関数の行はその行に（ケースの群に分けた関数は、並べ順でその関数の最後の群に）、ファイルの準備（import・補助・fixture）の行はそのファイルの最後の行に（ほかのテストのモジュールが import・パスで取り込むモジュールは、取り込む側も含めた最後の行に）、補助のファイル（`conftest.py`・偽の CLI・fixture のデータ）はそれを使うテストの最後の行に、bash のファイルの 1 件と準備の行はそのファイルの最後の群に付ける。使うテストが無い補助は一覧の先頭に置く | (a) テストの関数の行だけを数え、準備は別に示す、(b) 準備をテストの数で按分する | 上から消したときの累計が、実際にそこまで消したときに消せる行数（準備はそれを使う最後のテストを消したときに消せる）の下限になる。(a) は全てを消しても合計に届かない。(b) は消しても残る準備を消せるように見せる。合計は計測の行数と一致する | Issue の受け入れ（上から消したときの累計） |
| D-236-12 | 並べ順: 使うテストが無い補助 → 「迷い」（重さの低い順） → 低 → 中 → 高。同じ段の中は、領域（#230・#231・#232・#233・#234・#235・`integration` の順）、ファイルのパス、正しく通る例を後ろ（D-236-20）、ファイルの中の位置の順 | 同じ段の中を行数の多い順にする | Issue の並べ順（迷いを先頭に、続けて重さの低い順）。同じ段の中は、ファイルごとにまとまり、利用者がファイルを見ながら選べる順にした | Issue の受け入れ |
| D-236-13 | `tools/agent_runner/tests/adapters/dsh/ptc_tool_results.json`（14 行）は、#243 が DSH のテストを消した後に残った、使われていない fixture である（`git grep ptc_tool_results` は `docs/` だけ）。この子では消さず、一覧の先頭に「使うテストが無い補助」として載せる | この子で消す | `agent-runner-tests` の領域のファイルで、Issue の「変えないもの」に当たる | Issue の「変えないもの」 |
| D-236-14 | 一覧の全体（関数・場面の群ごと）はこの Spec の「残ったテストの一覧」に置き、#228 のコメントには、計測の結果、子ごとの内訳、段ごと（迷い・低・中・高）の累計、領域 × 段の群の一覧（件数・行数・防ぐ損害・重さ・迷い・累計）、「迷い」の行の全て、持ち越し候補、全体の一覧へのリンクを書く | (a) 全体の一覧を #228 のコメント（複数）に写す、(b) 一覧を別のファイルにして commit する | (a) 一覧は約 970 行で、GitHub のコメントの上限（65,536 字）に収まらない。(b) `docs/superpowers/README.md` は、テーマごとに 1 つの Spec を更新する決まりで、Spec の付録のファイルの扱いを決めていない。Spec が大きくなる（約 300KB）が、子の Spec（#230 は約 260KB）と同じ程度である。PR でレビューされる 1 か所に置き、版を Git で追える。#228 のコメントは、群の一覧で判断でき、行ごとの詳細はリンクで読める | Issue の受け入れ（テストまたはテストの群ごとに） |
| D-236-15 | #228 へのコメントは PR を作った後（ループの前）に、PR の head の計測で投稿する。ループの修正で一覧が変わったら、コメントを直す。マージの後に `main` で測り直し、最終の値を #228 と #236 に書く | マージの後にだけ投稿する | Issue は「一覧を出したら completed で close」の順で、`finalize.py` はマージと同時に #236 を閉じる。投稿の後にループの修正があっても、同じコメントを直せば古い一覧が残らない | Issue の受け入れ |
| D-236-16 | 子が申し送った、基準のテストも検出しない守り（#230 の `runner.py:604` など、#232 の `agent_tmp.py:39`、#235 の `new-world.sh:185` など）と、消したままの S の例（#232 のサイクル 3 の 5 件）は、この子ではテストを足さず・戻さず、#228 のコメントに「持ち越し候補（テストを足す・戻す候補）」として書く。子が「直すかは #236 で決める」「#236 が見直す」と任せた、守りを検出しない・弱いテスト（#230 の `test_export_error_fields_override_answer`、#234 の `test_concurrent_launchers_initialize_only_empty_missing_auth`、PR #246 の S1 の `test_statement_candidates_ignores_user_diff_prefix_settings`）も、直さずに持ち越す（一覧では迷いのまま）。#232 が勧めた、残った S の重さを決める前の複合条件・`if` でない文の走査は行わず、重さは子の表から写した（D-236-9） | この子でテストを足す・戻す | 領域のテストは Issue の「変えないもの」。足すのは新しい要求で、件数も増える。#230 は「テストを足すかは #236 で決める」と申し送ったので、この表で決めた | Issue の「変えないもの」 |
| D-236-17 | 行数のための準備のコードの共通化（#230 の D-230-11: git の repository の写し、Devin の export のよく似たテスト）は、この子では行わず、行数を減らす別の手段として #228 のコメントに書く | この子で共通化する | 領域のテストを変える（Issue の「変えないもの」）。残す S のテストの準備を変えるので、どこまで行うかは利用者が決める | Issue の「変えないもの」 |
| D-236-18 | 分類の取り出しは、6 つの領域ごとに 1 つ、読むだけのサブエージェントが決まった JSON の形で書き、controller が検査のスクリプト（関数・場面の網羅、値の形、Spec の行の実在）で確かめ、各領域から抜き出した行を Spec と照らし合わせる。`integration` の補助は controller が扱う | controller が全て読む | 子の Spec は合わせて約 930KB、残っているテストの関数は着手時に 891（載せ直しの後は 892）ある。領域は互いに独立で、並行で読める。形と網羅は機械で、中身は抜き出しで確かめる | issue-to-pr の委任（推奨案で進める） |
| D-236-19 | 予約は、ループの `finish` の後（ループのエラーで `finish` まで進めないときは止まった時点）に、結果と再開の方法を #236 に書いてから解放する | PR の作成の直後に解放する | issue-to-pr の `--merge` の手順 | issue-to-pr |
| D-236-20 | 拒否のテストの対として残した「正しく通る例」（`AGENTS.md` の D: 拒否を確かめるテストには、正しく通る例を少なくとも 1 件残す）は、重さを対の守りのいちばん重いものにそろえ、同じファイル・同じ段の中で、ほかの行の後に置く | (a) 正しく通る例そのものの損害で重さを決める（多くは低）、(b) 対のテストを指す項目を JSON に持たせ、対の最後の行の直後に置く | (a) 上から消すと、正しく通る例が対の拒否のテストより先に消え、D の規則があるので実際にはそこまで消せない。件数の累計が実際に消せる数より多く見える（brainstorming の builder check の問い 2）。(b) 対は同じモジュールの守りなので、同じファイル・同じ段の後ろに置けば足りる。依存の処理を検査と並べ替えに足さずに済む | `AGENTS.md` の「テストの採用基準」の D |
| D-236-21 | 作業中に `main` へマージされた PR #258（`tools/agent_runner/tests/adapters/devin/test_adapter.py` で関数 2 つ（収集 4 件）を消して関数 2 つ（収集 3 件）を足した）と PR #256（`.agents/skills/review-fix-planning/tests/test_finalize.py` で関数 1 つ（収集 1 件）を消して関数 2 つ（収集 2 件）を足した）と PR #257（`.agents/skills/pr-review-fix-loop/tests/test_loop_review.py` の 1 つの関数に 5 行を足した。関数の増減は無い）に合わせて、push の前の branch を `dcdc0d9` に載せ直し、索引を作り直して、増減した 7 つの関数だけを分類し直した（足した 4 つの関数は表に無いので、#239・#241 の Spec を引いて #236 が判定した） | 着手時の `bdbe02b` のまま一覧を出す | 一覧と計測は、マージされる状態の数を示す。消えたテスト（PR #256 の 1 件は #232 の表で消す扱いのまま残っていたもの）を一覧に残さない。commit は push の前で、載せ直しても誰の作業も壊さない | Issue の受け入れ（計測はコミット済みの状態） |

## 受け入れ条件との対応

| Issue の受け入れ | 担当（Plan） | 観測する結果 | 確かめ方 |
| --- | --- | --- | --- |
| `tools/test_support/` とルートの `conftest.py` に使われていない名前が無い | Task 1 | `__all__` と各モジュールの名前（`FINDING_CONTENT`・`plugin`・`outside_runner`・`texts`・`drop_inherited_git_environment`）が、`tools/test_support/` の外で使われている。`FINDING_REASON` が無い | `git grep -n <名前> -- ':!:tools/test_support/'` を名前ごとに実行し、結果を記録する。autouse の fixture は効く範囲を書く |
| `pyproject.toml` の `pythonpath`・`testpaths`、`.devcontainer/run-tests.bash` が消えたディレクトリを指していない | Task 1 | 指すパスがすべて実在する | パスごとに `test -d`。`run-tests.bash --list` の全てが実在する |
| `README.md` の「テスト」と `.devcontainer/README.md` の「テストの実行」が、残ったテストの実行のしかたと合っている | Task 1 | 両方の pytest の行が `testpaths` と同じ 4 つを指す。CI の記述が `ci.yml` と食い違わない | `git diff` と、書いたコマンドの実行（Task 4） |
| 6 つの子の Spec に棚卸しの表があることを確かめる | Task 3 | 6 つの Spec のパスと、棚卸しの表の節の見出し | `grep -n '^#' <Spec>` の結果を「棚卸しの表の確認」に書く |
| 「計測」の結果（件数・行数と、子ごとの内訳）を #228 にコメントする | Task 5 | #228 のコメントの URL | `gh api` で読み戻す |
| 届かなければ、一覧を作り #228 にコメントする（領域・件数・行数・防ぐ損害・重さ・迷い、迷いを先頭に重さの低い順、累計） | Task 2・3・5 | 一覧の行の合計が計測の件数・行数と一致し、並べ順が D-236-12 のとおり | 一覧の生成のスクリプトの検査（網羅・合計・並べ順）と、領域ごとの抜き出しの照合 |
| `README.md` の「テスト」の入口が通る | Task 4 | 3 つのコマンドが終了コード 0 | `uv run pytest tests/skills .agents/skills .agents/scripts tools`、`bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh` |

共有する条件: 一覧の件数・行数は、計測と同じファイルの集合（#228 の「計測」の pathspec）と同じ数え方（`wc -l` は改行の数）を使う。この条件は索引（Task 2 の前と Task 3）と一覧の生成（Task 3）で同じ数え方を使い、Task 3 で合計を計測の値と照合する（統合は controller）。

## 一覧の作り方

### 索引（Task 2 の前と Task 3）

コミット済みの checkout で次を集め、JSON の索引にする。道具と記録は `/workspaces/reso-world/tmp/agents/issue-236.15yls_nc/` に置き、コミットしない（`bin/index_tests.py`・`bin/validate_classify.py`・`bin/build_list.py`・`bin/render_sections.py`、分類の `data/classify/<領域>.json`、索引の `data/index-1823614.json`、検証の記録の `verify/`）。利用者が削る範囲を決めた後に一覧を作り直せるよう、このディレクトリは #236 の後も残す（Plan の Task 7）。

- `uv run --locked pytest --collect-only -q` と、`tests/scripts`（Meshy を除く）の収集の node ID。node ID の `[...]` を除いた `パス::関数`（クラスのメソッドは `パス::クラス::メソッド`）ごとに、収集数とケースの ID（`[...]` の中）を記録する
- 計測の pathspec の全てのファイルの改行の数（`wc -l` と同じ）
- テストのモジュール（`test_*.py`）の、`test` で始まる関数とメソッドの行の範囲（デコレータの行から関数の最後の行まで）。範囲の外の行は、そのファイルの準備の行
- bash のテスト（`.devcontainer/test-*.bash`・`tests/scripts/test-*.bash`。Meshy を除く）

全ての node ID が関数に対応し、全ての関数に node ID があることを確かめる（着手時の `bdbe02b` で 1,279 件・28,470 行と一致し、対応しないものは無かった。基準値の `7d44355` でも 3,646 件・45,024 行と一致した）。

### 分類（Task 2）

領域ごとに、索引のその領域の関数の全てと、bash のファイルの全てについて、次の形の JSON を書く。

```json
{
  "area": "agent-runner-tests",
  "sources_read": ["docs/superpowers/specs/<子の Spec>.md"],
  "tier_summaries": {"迷い": "<段の主な損害>", "低": "...", "中": "...", "高": "..."},
  "functions": [
    {"path": "<ファイル>", "qualname": "<関数 または クラス::メソッド>",
     "classification": "S | F∩S | L | F | D", "mayoi": false, "weight": "高 | 中 | 低",
     "weight_basis": "table | inferred", "pair_positive": false, "damage": "<防ぐ損害（100 字以内）>",
     "source": {"spec": "<Spec のパス または null>", "line": 123}, "note": "<任意>"},
    {"path": "<ファイル>", "qualname": "<parametrize のケースで分類が分かれる関数>",
     "cases": [
       {"ids": ["<node ID の [] の中>"], "classification": "...", "mayoi": false, "weight": "...",
        "weight_basis": "...", "pair_positive": false, "damage": "...", "source": {"spec": "...", "line": 456}, "note": "..."}
     ]}
  ],
  "bash_groups": [
    {"path": "<bash のファイル>", "name": "<場面の群の名前>", "ranges": [[10, 40]],
     "classification": "...", "mayoi": false, "weight": "...", "weight_basis": "...", "damage": "...",
     "source": {"spec": "...", "line": 456}, "note": "..."}
  ],
  "anomalies": ["<表と今のテストの食い違い>"]
}
```

- `classification` は表の分類。D の代表として残したものは、その守りの分類（S か F∩S）にする。残っているのに表で L・F・D のものは `note` に残っている理由（戻した記録など）を書き、見つからなければ `anomalies` に書く
- `mayoi` は、表か「迷いの一覧」で迷いと書かれたもの
- `pair_positive` は、拒否のテストの対として残した正しく通る例（D-236-20）。重さは対の守りのいちばん重いもの
- `cases` は、表が parametrize のケースで分類・重さ・迷いを分けている関数だけに使い、その関数の収集したケースの ID（索引の `ids`）をちょうど 1 回ずつ、どれかの群に入れる（D-236-8）。`cases` を使う関数は、関数の直下に分類の項目を書かない
- `source.line` は、分類を取った Spec の行。表に無いものは `spec`・`line` を null にし、`note` に「表に無い」と理由を書く
- bash の `ranges` は、その群の場面の行（1 始まり、両端を含む）。同じファイルの群の範囲は重ならない。範囲の外の行（shebang・共通の関数・準備）は、そのファイルの準備の行になる
- 検査のスクリプト（`bin/validate_classify.py`）が、網羅（索引の関数と bash のファイルがちょうど 1 回ずつ現れる）、値の形、`source.line` の実在、bash の範囲を確かめる

### 割り当てと並べ替え（Task 3）

1. 行は、関数（件数はその収集数）、関数のケースの群（件数はその群のケースの数）、bash の場面の群（件数 0）、使うテストが無い補助（件数 0）である
2. 段と並べ順: 使うテストが無い補助 → 迷い → 低 → 中 → 高（D-236-12）。迷いの中は重さの低い順。同じ段・領域・ファイルの中では、正しく通る例（`pair_positive`）をほかの行の後に置き、その中はファイルの中の位置の順
3. 行数の割り当て（D-236-11）: 関数は自分の行の範囲（ケースの群に分けた関数は、並べ順でその関数の最後の群に付ける）、bash の群は自分の `ranges`。ファイルの準備の行と bash のファイルの 1 件は、並べ順でそのファイルの最後の行に付ける（ほかのテストのモジュールがコメントでない行の import かファイル名で取り込むモジュールの準備は、取り込む側も含めた最後の行に付ける）。補助のファイルは、使うテストの最後の行に付ける。使うテストは次で決める
   - `conftest.py`: 同じディレクトリとその下のテストのモジュール（ルートの `conftest.py` は pytest の `testpaths` の全て）
   - 偽の CLI・補助のモジュール・fixture のデータ: 同じディレクトリとその下のテストのうち、ファイル名（拡張子を除く名前）を含むもの。無ければ 1 つ上のディレクトリとその下で探す。それでも無ければ「使うテストが無い補助」
   - `tools/test_support/plugin.py`・`texts.py`: `tools.test_support.plugin`・`tools.test_support.texts` を読み込むテストのモジュール。`__init__.py` はその両方
   - `tests/scripts/test-superpowers-python.bash`: `tests/scripts` の Python のテスト（件数の 1 件も付ける）
4. 累計: 上から順に、件数と行数（付けた分を含む）を足す。合計が計測の件数・行数と一致することを確かめる。残りが目標以下になる最初の行を、件数・行数それぞれに印を付ける
5. 出力: この Spec の「残ったテストの一覧」の表（全ての行）と、#228 のコメントの群の一覧（領域 × 段）

この割り当ては、そこまで消したときに消せる行数の下限である。準備の一部は、それを使うテストだけを消せばもっと早く消せる。

## 棚卸しの表の確認（#228 の完了の条件 4）

6 つの子の Spec のすべてに、棚卸しの表（テストごとの分類と理由）がある。見出しの行は `grep -n -E '^#{2,3} .*(棚卸し|迷いの一覧)'` で確かめた（`1823614`。記録は `PARENT_ROOT/tmp/agents/issue-236.15yls_nc/verify/inventory-headings.txt`。6 つの Spec は `bdbe02b` から変わっていない）。

| 子 | Spec | 棚卸しの節（行） | 迷いの一覧 |
| --- | --- | --- | --- |
| #230 `agent-runner-tests` | `docs/superpowers/specs/2026-10-23-create-reso-world-issue230-agent-runner-tests-design.md` | 「棚卸しの表」（318 行） | 「迷いの一覧」（270 行） |
| #231 `pr-review-tests` | `docs/superpowers/specs/2026-10-24-create-reso-world-issue231-pr-review-tests-design.md` | 「棚卸しの表」（42 行） | 表の中 |
| #232 `review-helper-tests` | `docs/superpowers/specs/2026-10-22-create-reso-world-issue232-review-helper-tests-design.md` | 「棚卸し」（96 行）、「Task 5 の棚卸し」（425 行） | 表の中 |
| #233 `skill-tests` | `docs/superpowers/specs/2026-10-24-create-reso-world-issue233-skill-tests-design.md` | 「棚卸しの表」（40 行。45・168・316 行の 3 つの節） | 表の中 |
| #234 `devcontainer-tests` | `docs/superpowers/specs/2026-10-23-create-reso-world-issue234-devcontainer-tests-design.md` | 「棚卸しの表」（105 行。F1〜F4） | 「迷いの一覧」（685 行） |
| #235 `script-tests` | `docs/superpowers/specs/2026-10-23-create-reso-world-issue235-script-tests-design.md` | 「棚卸しの表」（57 行） | 表の中 |

レビュー修正で戻したテストは、#230・#232・#234・#235 では別の Spec（`2026-10-23-create-reso-world-pr247-issue230-review-fixes-design.md`・`…-pr246-issue232-…`・`…-pr244-issue234-…`・`…-pr245-issue235-…`）に、#231・#233 では同じ Spec の後の節にある。

## 計測の結果（この PR の後）

#228 の「計測」の 4 つのコマンドを、`1823614`（`origin/main` の `dcdc0d9` に載せ直した後の、コミット済みの状態。計測の対象のファイルは、この PR でコードを変えた最後の commit `e7e005c` と同じ）で実行した（出力は `PARENT_ROOT/tmp/agents/issue-236.15yls_nc/verify/measure.txt`）。後の commit は Spec・Plan だけで、計測の値は変わらない（最後の head での計測は Plan の「完了」に書く）。

| 指標 | 基準値（`7d44355`） | この PR の後 | 比 | 目標（1/3 以下） | 届いたか |
| --- | --- | --- | --- | --- | --- |
| 件数 | 3,646 | 1,279（1,224 + 33 + 22） | 35.1% | 1,215 以下 | 届かない（64 件多い） |
| 行数 | 45,024 | 28,504 | 63.3% | 15,008 以下 | 届かない（13,496 行多い） |

- 着手時（`bdbe02b`）の 1,279 件・28,470 行との差は、この PR の `tools/test_support/` の 7 行減と、着手の後にマージされた PR #258（`tools/agent_runner/tests/adapters/devin/test_adapter.py` で関数 2 つ（収集 4 件）を消して関数 2 つ（収集 3 件）を足し、+9 行）・PR #256（`.agents/skills/review-fix-planning/tests/test_finalize.py` で関数 1 つ（収集 1 件）を消して関数 2 つ（収集 2 件）を足し、+27 行）・PR #257（`.agents/skills/pr-review-fix-loop/tests/test_loop_review.py` の 1 つの関数に +5 行）による
- この PR は件数を変えない。合計の件数が着手時と同じなのは、PR #258 の 1 件減と PR #256 の 1 件増が打ち消し合うため（領域ごとの増減は下の表）

### 子ごとの内訳（この PR の後）

領域の分け方は「計測」の「子ごとの内訳」と同じ。

| 子のキー | 基準値（`7d44355`） | この PR の後（`e7e005c`） | 件数の比 | 行数の比 |
| --- | --- | --- | --- | --- |
| `agent-runner-tests`（#230） | 1,058（1,058+0+0）・10,351 行 | 274（274+0+0）・5,439 行 | 25.9% | 52.5% |
| `pr-review-tests`（#231） | 548（548+0+0）・9,626 行 | 288（288+0+0）・7,307 行 | 52.6% | 75.9% |
| `review-helper-tests`（#232） | 1,056（1,056+0+0）・9,919 行 | 428（428+0+0）・7,120 行 | 40.5% | 71.8% |
| `skill-tests`（#233） | 472（472+0+0）・5,923 行 | 195（195+0+0）・4,087 行 | 41.3% | 69.0% |
| `devcontainer-tests`（#234） | 437（419+0+18）・5,778 行 | 51（39+0+12）・2,481 行 | 11.7% | 42.9% |
| `script-tests`（#235） | 75（0+61+14）・3,293 行 | 43（0+33+10）・1,993 行 | 57.3% | 60.5% |
| `integration`（#236）。`tools/test_support/`・ルートの `conftest.py` | 0（0+0+0）・134 行 | 0（0+0+0）・77 行 | — | 57.5% |
| 合計 | 3,646・45,024 行 | 1,279・28,504 行 | 35.1% | 63.3% |


## 残ったテストの一覧

「一覧の作り方」のとおり、6 つの子の棚卸しの表（とレビュー修正の記録）から、この PR の head のテストを 967 行に分けた。上から消したときの累計の件数・行数の最後は、計測の値（1,279 件・28,504 行）と一致する。行数の累計は、準備の行と補助のファイルをそれを使う最後の行に付けた下限である（D-236-11。ほかのテストのモジュールが取り込むモジュールの準備は、取り込む側も含めた最後の行に付けた）。

### 段ごとの累計

| 段 | 行の数 | 件数 | 行数 | 累計の件数 | 累計の行数 | 残りの件数 | 残りの行数 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 使うテストが無い補助 | 1 | 0 | 14 | 0 | 14 | 1,279 | 28,490 |
| 迷い | 45 | 55 | 600 | 55 | 614 | 1,224 | 27,890 |
| 低 | 60 | 68 | 827 | 123 | 1,441 | 1,156 | 27,063 |
| 中 | 428 | 570 | 7,757 | 693 | 9,198 | 586 | 19,306 |
| 高 | 433 | 586 | 19,306 | 1,279 | 28,504 | 0 | 0 |

- 件数が目標（1,215 件以下）に届くのは、上から 55 行目（段は「低」）まで消したとき（累計 64 件・678 行、残り 1,215 件・27,826 行）
- 行数が目標（15,008 行以下）に届くのは、上から 614 行目（段は「高」）まで消したとき（累計 799 件・13,543 行、残り 480 件・14,961 行）
- 上の 2 つの位置は、迷いを先頭に並べたこの順で数えた位置である。件数は「低」の段だけで 68 件あるので、迷いを 1 件も消さずに「低」から 64 件を選んでも届く
- 行数は、迷い・低・中（と使うテストが無い補助）を全て消しても 9,198 行で、必要な 13,496 行に 4,298 行足りない。どう選んでも「高」の守りを消すか、準備のコードの共通化（D-236-17）が要る
- 「614 行目」「累計 799 件」は、段の中の並び（領域 → ファイル → 位置）による値で、行数の目標に届くために必要な最小の件数ではない
- 根拠の内訳: 子の表のとおり 850 行、表の分類で重さだけ #236 が決めたもの 106 行、表に無く #236 が判定したもの 10 行、使うテストが無い補助 1 行

- 付けた行（準備 10,844 行、補助のファイル 1,133 行、ケースの群に分けた関数 757 行）は合わせて 12,734 行で、計測の行数の 44.7% を占める。そのうち 11,191 行は「高」の段の行に付いていて（「高」の段の 19,306 行の 58.0%）、「高」の行を消さないと減らない

### 領域 × 段の群

| 順 | 段 | 領域 | 行の数 | 件数 | 行数 | 防ぐ損害（主なもの） | 累計の件数 | 累計の行数 | 残りの件数 | 残りの行数 |
| ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: |
| 1 | 補助 | `agent-runner-tests` | 1 | 0 | 14 | 消しても守りは減らない（`tools/agent_runner/tests/adapters/dsh/ptc_tool_results.json`） | 0 | 14 | 1,279 | 28,490 |
| 2 | 迷い（低） | `agent-runner-tests` | 5 | 5 | 56 | 気付けるか決められない守り（権限のフラグ・入力の検査・skill の指示・孤児が残る恐れ）。外れた影響が未確認で、検出できないテストも含む（この領域の迷い全体の要約） | 5 | 70 | 1,274 | 28,434 |
| 3 | 迷い（低） | `review-helper-tests` | 11 | 11 | 111 | 検査の分岐を外すと誤った記録・抜粋・checkout の判定がエラーなしに通る、L との境が曖昧なもの（書きすぎの可能性を含む）（この領域の迷い全体の要約） | 16 | 181 | 1,263 | 28,323 |
| 4 | 迷い（低） | `devcontainer-tests` | 2 | 0 | 21 | ccdd が子の終了コードを握りつぶす、親シェルの ANTHROPIC_MODEL・DEEPINFRA_TOKEN を消す／config が無いのに tier 無しで起動し、モデル割当が黙って変わる | 16 | 202 | 1,263 | 28,302 |
| 5 | 迷い（中） | `agent-runner-tests` | 3 | 4 | 25 | 読み取りのロールを --sandbox disabled・shell 許可で起動する権限のフラグ（#201）。F∩S か L か未決／export の step の error・is_error を回答より優先する守り（_export_failure）。外しても response_failed のままで検出できない／noninteractive・stdin が True と保証されていなければ起動しない。今の adapter は全て True で普段は変わらず、保証の無い adapter の影響は未決 | 20 | 227 | 1,259 | 28,277 |
| 6 | 迷い（中） | `pr-review-tests` | 3 | 3 | 61 | 旧 create API で、明示したモデル名を固定せず、別名の保存先へ誤ったレビューを保存する。／旧 create API で、save が固定済みの明示モデル名を使わず、別名の保存先へ誤ったレビューを保存する。／旧 create API で、repository 名の大文字小文字を正規化せず、同じ PR のレビューを別の保存先に分ける。 | 23 | 288 | 1,256 | 28,216 |
| 7 | 迷い（中） | `review-helper-tests` | 9 | 17 | 69 | 検査の分岐を外すと誤った記録・抜粋・checkout の判定がエラーなしに通る、L との境が曖昧なもの（書きすぎの可能性を含む）（この領域の迷い全体の要約） | 40 | 357 | 1,239 | 28,147 |
| 8 | 迷い（中） | `devcontainer-tests` | 2 | 0 | 90 | 健全な兄弟 identity の pane が起動中の workspace へ流れ、復元先が静かに取り違えられる／pi install が 0 でも一覧に新拡張が無いまま postCreate が成功扱いで終わる（失敗を成功と報告） | 40 | 447 | 1,239 | 28,057 |
| 9 | 迷い（高） | `agent-runner-tests` | 1 | 1 | 21 | 期限切れで SIGTERM を無視する leader を止める。anchor を残して group の仲間を止める段を飛ばした影響は未確認 | 41 | 468 | 1,238 | 28,036 |
| 10 | 迷い（高） | `review-helper-tests` | 4 | 5 | 37 | 検査の分岐を外すと誤った記録・抜粋・checkout の判定がエラーなしに通る、L との境が曖昧なもの（書きすぎの可能性を含む）（この領域の迷い全体の要約） | 46 | 505 | 1,233 | 27,999 |
| 11 | 迷い（高） | `skill-tests` | 3 | 7 | 84 | 5 領域に追跡ファイルが残る旧 HEAD を更新し、clean なワールドのファイルも削除される／rename 検出が旧パスの削除を隠し、追跡中のワールド source を失う／削除パス照会の失敗を空集合として扱い、保護領域の追跡ファイルを削除する | 53 | 589 | 1,226 | 27,915 |
| 12 | 迷い（高） | `devcontainer-tests` | 1 | 1 | 13 | 同時起動で保存済みの auth を置き換える、不正な JSON・公開権限・staging が残る（先着の上書きは検出できない） | 54 | 602 | 1,225 | 27,902 |
| 13 | 迷い（高） | `script-tests` | 1 | 1 | 12 | 再開判定表の blocked の行が ready に変わり、受け取り側が未承認・無許可の作業を実装する（権限を決める値） | 55 | 614 | 1,224 | 27,890 |
| 14 | 低 | `agent-runner-tests` | 21 | 24 | 204 | 記録のモデル名・環境の書き換え・指示文の形・失敗の種類の分類など、作業の結果を変えない記録や表示の精度 | 79 | 818 | 1,200（件数が目標に届く） | 27,686 |
| 15 | 低 | `review-helper-tests` | 36 | 44 | 605 | 統計・時間枠・抜粋の誤り（採用の帰属、能動時間、実行記録の統計、再試行回数）。作業の結果は変えない | 123 | 1,423 | 1,156 | 27,081 |
| 16 | 低 | `devcontainer-tests` | 1 | 0 | 3 | 固定した版でない ctx7 CLI を受け入れる（動くので気付けないが、作業の結果は変わらない） | 123 | 1,426 | 1,156 | 27,078 |
| 17 | 低 | `script-tests` | 2 | 0 | 15 | uv sync の失敗を成功と報告する、fetch の前の古い upstream/main を黙って取り出す（作業の結果への影響が小さい誤り） | 123 | 1,441 | 1,156 | 27,063 |
| 18 | 中 | `agent-runner-tests` | 148 | 194 | 2,636 | 失敗や途中の応答を成功と報告する、記録を取り違える、取り消し後に fallback を起動するなど誤った結果の報告 | 317 | 4,077 | 962 | 24,427 |
| 19 | 中 | `pr-review-tests` | 55 | 86 | 1,430 | 診断・実行記録・判断記録・候補一覧の誤保存や上書き、誤った原因・状態の報告、回収の手掛かりの喪失。 | 403 | 5,507 | 876 | 22,997 |
| 20 | 中 | `review-helper-tests` | 141 | 204 | 1,646 | 誤った結果の報告・記録の取り違え（別 PR・別 head・別 base の記録、判定漏れ、サイクルの上書き、失敗を成功と報告） | 607 | 7,153 | 672 | 21,351 |
| 21 | 中 | `skill-tests` | 47 | 52 | 664 | モデル名・監視結果の誤帰属や誤報、起動失敗の完了扱い、担当・オプションの取り違え、引き継ぎ記録の欠落、凍結履歴の喪失を防ぐ。 | 659 | 7,817 | 620 | 20,687 |
| 22 | 中 | `devcontainer-tests` | 24 | 25 | 920 | 誤ったディレクトリへの書き込み、tier・設定・session 記録の取り違え、共有登録の消失、失敗の見落とし、スキル同期の誤表示 | 684 | 8,737 | 595 | 19,767 |
| 23 | 中 | `script-tests` | 13 | 9 | 461 | 別の checkout・親の選択、スキルのリンクと .pi の食い違い、前提欠落での途中状態、失敗を成功と報告、指示ファイル・過去文書の改変 | 693 | 9,198 | 586 | 19,306 |
| 24 | 高 | `agent-runner-tests` | 41 | 46 | 2,483 | 秘密情報の漏れ、孤児・別プロセスへの signal、実リポジトリへの git 書き込み、checkout の変更の見逃し、権限の広がり | 739 | 11,681 | 540 | 16,823 |
| 25 | 高 | `pr-review-tests` | 140 | 199 | 5,816 | 利用者ファイル・worktree・共有 Git の誤削除・変更、別 PR・HEAD のレビュー流用による未検証のマージ、秘密の漏れ、ロック競合、権限・書込範囲の拡大。 | 938 | 17,497 | 341 | 11,007（行数が目標に届く） |
| 26 | 高 | `review-helper-tests` | 83 | 147 | 4,652 | 未検証のマージ、別リポジトリや tmp・reviews の外・追跡対象への書き込み、信頼境界・sandbox・環境の隔離の破れ、レビュー結果の消失、トークンの漏れ | 1,085 | 22,149 | 194 | 6,355 |
| 27 | 高 | `skill-tests` | 107 | 136 | 3,397 | 未保存ファイル・ロック・branch の消失、担当外変更や別リポジトリの取り込み、実プロセスの誤停止・誤報、資格情報の漏れを防ぐ。 | 1,221 | 25,546 | 58 | 2,958 |
| 28 | 高 | `devcontainer-tests` | 25 | 25 | 1,453 | 秘密情報・認証の漏れや消失（拒否前の保存済みの鍵の上書きを含む）、誤った対象の削除・操作（削除範囲・GIT_*・HOME・buni・gitleaks の検証）、サンドボックスと権限の境界 | 1,246 | 26,999 | 33 | 1,505 |
| 29 | 高 | `script-tests` | 37 | 33 | 1,505 | 秘密情報の漏れ（資格情報・鍵・gitleaks・ignore）、利用者のファイルの上書き・symlink 先への書き込み、別のリポジトリへの push、確認用コピーの上書き | 1,279 | 28,504 | 0 | 0 |


### 全ての行

段（迷いは重さごと）とファイルの順に並べる。「行数」の括弧は、その行に付けた行数で、「準備」はファイルの準備（bash は場面の外の行。bash のファイルの 1 件は、同じ行の件数の列に足す）、「関数」はケースの群に分けた関数の行（並べ順で最後の群に付けるので、前の群の行数は 0 になり、累計の行数が横ばいになる）、`パス` は補助のファイルである。付けた行は、それを使う全ての行を消したときに初めて減る（1 つの行だけを消しても、その行に付いた準備・補助の行は残る）。補助のファイルは使う側の最後の行に付けるので、領域ごとに行数を足しても「子ごとの内訳」とは一致しない（`integration` の 77 行のうち、`tools/test_support/` の 58 行は使う側の最後の `skill-tests` の行に、ルートの `conftest.py` の 19 行は pytest の最後の `devcontainer-tests` の行に付く）。「根拠」の「表」は子の棚卸しの表（とレビュー修正の記録）、「表・重さは #236」は重さだけを #236 が決めたもの、「#236 の判定」は表に無く #236 が判定したもの。

#### 使うテストが無い補助


`tools/agent_runner/tests/adapters/dsh/ptc_tool_results.json`（`agent-runner-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 1 | （ファイル全体） | 0 | 14 | 消しても守りは減らない | #236 | 0 | 14 |

#### 迷い（重さ: 低）


`tools/agent_runner/tests/adapters/cursor/test_cursor.py`（`agent-runner-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 2 | `test_prepare_keeps_native_fallback_when_no_configured_source_exists` | 1 | 7 | 設定 source に無い SKILL.md のパスを native より優先して渡さない。担当が止まるか黙って続くか未確認（今の役割は skills=[] で届かない） | 表・重さは #236 | 1 | 21 |
| 3 | `test_prepare_rejects_ambiguous_second_model_override` | 1 | 3 | ブラケット付き model と別の effort の同時指定を起動の準備で拒否する。CLI の挙動が未確認で S か L か未決 | 表 | 2 | 24 |

`tools/agent_runner/tests/test_cli.py`（`agent-runner-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 4 | `test_write_exceptions_follow_the_work_scope_lines_in_order` | 1 | 32 | 空行が無いと依頼文の先頭の行が許可した書き込み例外の続きに見える。依頼文は呼び出し側の組み立てで実害は未確認 | 表・重さは #236 | 3 | 56 |

`tools/agent_runner/tests/test_config.py`（`agent-runner-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 5 | `test_self_cannot_be_mixed_or_used_as_fallback` | 1 | 9 | 空の agents の拒否（Field(min_length=1)）。外れた場合の影響は確かめておらず S か L か未決 | 表 | 4 | 65 |

`tools/agent_runner/tests/test_workspace.py`（`agent-runner-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 6 | `test_git_common_dir_of_a_linked_worktree_is_the_main_git_directory` | 1 | 5 | linked worktree から共有の Git ディレクトリ（main の .git）を返す。誤ると指示の書き込み先が黙って変わるが損害は小さい | 表 | 5 | 70 |

`.agents/scripts/tests/test_review_findings.py`（`review-helper-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 7 | `test_invalid_documents_name_the_problem` の `verified-mutate-findings[0].sources: must be a non-empty array` | 1 | 0 | verified の指摘の sources が空で、元レビュアーへの対応を失い採否・統計の帰属が黙って外れる | 表 | 6 | 70 |
| 8 | `test_legacy_findings_cannot_prove_the_actor_of_a_v2_adoption` | 1 | 4 | provenance の無い v1 の一覧から、v2 の採用を実担当に帰属させる | 表 | 7 | 74 |
| 9 | `test_cli_stats_skips_lists_other_than_cycle_even_if_they_lack_newer_sections` | 1 | 11 | 集計しない一覧を読み飛ばさず検査する。外すとメッセージ付きの終了 65 で現れる（L に近い） | 表・重さは #236 | 8 | 85 |
| 10 | `test_statement_candidates_puts_frequent_terms_in_common_terms` | 1 | 10 | 多くの文書に出る語を common_terms に分けず、大量の候補を並べる | 表 | 9 | 95 |
| 11 | `test_statement_candidates_keeps_a_short_line_as_it_is` | 1 | 10 | 短い行をそのまま出す分岐を誤り、抜粋がエラーなしに変わる | 表 | 10 | 105 |
| 12 | `test_statement_candidates_merges_overlapping_excerpts` | 1 | 11 | 重なる抜粋をまとめる分岐を誤り、抜粋がエラーなしに変わる | 表 | 11 | 116 |

`.agents/scripts/tests/test_review_records.py`（`review-helper-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 13 | `test_check_against_keeps_d1_of_an_inherited_fix` | 1 | 10 | 引き継いだ fix の d1（再現の記録）が、エラーなしに消える | 表 | 12 | 126 |
| 14 | `test_collect_records_lists_a_status_comment_with_a_line_added_on_top` | 1 | 5 | 人が先頭に行を足した状況コメントが、記録から黙って外れる | 表 | 13 | 131 |

`.agents/skills/review-verify/tests/test_dispatch.py`（`review-helper-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 15 | `test_self_returns_complete_input_without_launching_implementation` | 1 | 13 | self の割り当てで担当を起動する、または不完全な入力を返す | 表 | 14 | 144 |
| 16 | `test_self_prompt_embeds_the_same_time_limits` | 1 | 7 | self の指示と dispatch.json の時間枠が食い違う | 表 | 15 | 151 |
| 17 | `test_dispatch_does_not_read_the_review_directory_without_stop_confirmation` | 1 | 30 | 停止が未確認の間に、保存先を読む | 表 | 16 | 181 |

`.devcontainer/test-herdr-migration.bash`（`devcontainer-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 18 | ccdd の終了コードと親環境 | 0 | 8 | ccdd が子の終了コードを握りつぶす、親シェルの ANTHROPIC_MODEL・DEEPINFRA_TOKEN を消す | 表 | 16 | 189 |

`.devcontainer/test-pi-superagents.bash`（`devcontainer-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 19 | config が無いとき exit 1（#3） | 0 | 13 | config が無いのに tier 無しで起動し、モデル割当が黙って変わる | 表 | 16 | 202 |

#### 迷い（重さ: 中）


`tools/agent_runner/tests/adapters/cursor/test_cursor.py`（`agent-runner-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 20 | `test_prepare_read_only_role_allows_shell_without_cursor_sandbox` | 1 | 5 | 読み取りのロールを --sandbox disabled・shell 許可で起動する権限のフラグ（#201）。F∩S か L か未決 | 表 | 17 | 207 |

`tools/agent_runner/tests/adapters/devin/test_adapter.py`（`agent-runner-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 21 | `test_export_error_fields_override_answer` | 2 | 14 | export の step の error・is_error を回答より優先する守り（_export_failure）。外しても response_failed のままで検出できない | 表 | 19 | 221 |

`tools/agent_runner/tests/test_runner.py`（`agent-runner-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 22 | `test_unproven_capability_is_unsupported` | 1 | 6 | noninteractive・stdin が True と保証されていなければ起動しない。今の adapter は全て True で普段は変わらず、保証の無い adapter の影響は未決 | 表 | 20 | 227 |

`.agents/skills/pr-review/tests/test_pr_review_workspace.py`（`pr-review-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 23 | `test_create_pins_explicit_model_outside_codex` | 1 | 24 | 旧 create API で、明示したモデル名を固定せず、別名の保存先へ誤ったレビューを保存する。 | 表・重さは #236 | 21 | 251 |
| 24 | `test_save_uses_pinned_explicit_model_without_codex_metadata` | 1 | 25 | 旧 create API で、save が固定済みの明示モデル名を使わず、別名の保存先へ誤ったレビューを保存する。 | 表・重さは #236 | 22 | 276 |
| 25 | `test_create_normalizes_pr_repository_case` | 1 | 12 | 旧 create API で、repository 名の大文字小文字を正規化せず、同じ PR のレビューを別の保存先に分ける。 | 表・重さは #236 | 23 | 288 |

`.agents/scripts/tests/test_agent_tmp.py`（`review-helper-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 26 | `test_resolve_main_root_rejects_submodule_checkout` | 1 | 8 | submodule を親と取り違え、親でない checkout に tmp を作る | 表 | 24 | 296 |

`.agents/scripts/tests/test_review_findings.py`（`review-helper-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 27 | `test_invalid_documents_name_the_problem` の `candidates-mutate-reviewed_head: must be` | 1 | 0 | reviewed_head が完全な commit のハッシュでない記録を通し、どの commit のレビューか特定できない | 表 | 25 | 296 |
| 28 | `test_statement_candidates_ignores_user_diff_prefix_settings` | 1 | 10 | 利用者の diff の prefix 設定で差分の読み取りが変わる。外すと止まる（L に近い） | 表 | 26 | 306 |
| 29 | `test_invalid_statement_candidates_name_the_problem` | 1 | 12 | 候補 ID の重複を通し、判定の照合が片方の候補の判定漏れを見落とす | 表 | 27 | 318 |

`.agents/scripts/tests/test_review_records.py`（`review-helper-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 30 | `test_invalid_records_are_rejected` の `short-reviewed-head`・`repeated-review-file`・`sources-without-decision-id`・`reference-without-head`・`previous-state-equal-to-state`・`null-severity-for-a-finding`・`d1-on-a-preexisting-problem`・`d1-reproduced-by-another-finding`・`awaiting-approval-without-fix-or-hold` | 9 | 0 | 検査が外れると、誤った記録（reviewed_head の形・参照・重大度・d1・承認待ち等）がエラーなしに投稿される | 表・重さは #236 | 36 | 318 |

`.agents/scripts/tests/test_review_target.py`（`review-helper-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 31 | `test_find_review_directory_accepts_checkout_owner_repo_layout` | 1 | 12 | checkout 内の owner/repo 配置で、上流の base_remote を origin と取り違える | 表 | 37 | 330 |

`.agents/skills/review-fix-planning/tests/test_run_roles.py`（`review-helper-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 32 | `test_unresolved_parent_stops_before_reserving_the_review` | 1 | 11 | 親の解決の前に 1 回だけの枠を消費する（再実行は already reserved で止まる） | 表 | 38 | 341 |
| 33 | `test_unusable_fix_check_destination_stops_before_reservation_or_launch` | 1 | 13 | 使えない保存先でも予約・起動の前に止まらず、枠を消費する（#177） | 表 | 39 | 354 |

`.agents/skills/review-fix-planning/tests/test_upsert_pr_comment.py`（`review-helper-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 34 | `test_records_post_rejects_a_different_model_name_before_any_gh_call` | 1 | 3 | 別名義（別のモデル名）の記録を投稿する | 表 | 40 | 357 |

`.devcontainer/test-herdr-migration.bash`（`devcontainer-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 35 | test_session_cwd_repair_multi_workspace ③ | 0 | 27 | 健全な兄弟 identity の pane が起動中の workspace へ流れ、復元先が静かに取り違えられる | 表 | 40 | 384 |

`.devcontainer/test-pi-superagents.bash`（`devcontainer-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 36 | 導入の成功と導入後の検査（#29・#37） | 0 | 63 | pi install が 0 でも一覧に新拡張が無いまま postCreate が成功扱いで終わる（失敗を成功と報告） | 表 | 40 | 447 |

#### 迷い（重さ: 高）


`tools/agent_runner/tests/test_process.py`（`agent-runner-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 37 | `test_deadline_kills_term_resistant_leader` | 1 | 21 | 期限切れで SIGTERM を無視する leader を止める。anchor を残して group の仲間を止める段を飛ばした影響は未確認 | 表・重さは #236 | 41 | 468 |

`.agents/scripts/tests/test_agent_tmp.py`（`review-helper-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 38 | `test_make_session_dir_refuses_symlink_escaping_main_worktree` | 2 | 12 | tmp か tmp/agents の symlink を通って親の worktree の外へ書き込む | 表 | 43 | 480 |

`.agents/scripts/tests/test_review_target.py`（`review-helper-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 39 | `test_resolve_uses_explicit_code_root`（正しく通る例） | 1 | 11 | 対の守り: code_root から target_root・base_remote・保存先を正しく対応させる（拒否側は別リポジトリの選択） | 表・重さは #236 | 44 | 491 |

`.agents/skills/review-fix-planning/tests/test_review_fix_planning_skill_contract.py`（`review-helper-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 40 | `test_status_comment_snippet_escapes_heredoc_and_pins_repository` | 1 | 2 | --repo の固定の欠落で別リポジトリへ投稿し、未エスケープのバッククォートでブランチ名のコマンドを実行する | 表・重さは #236 | 45 | 493 |

`.agents/skills/review-fix-planning/tests/test_run_roles.py`（`review-helper-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 41 | `test_review_directory_tampering_is_not_accepted_or_cleaned` | 1 | 12 | review_dir の改ざんを受け取る、または消す（データの消失）。roles.json の記録を守る | 表 | 46 | 505 |

`.agents/skills/repo-cleanup-after-merge/tests/test_detached_update.py`（`skill-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 42 | `test_tracked_world_deletion_stops_without_mutating_any_local_state` | 5 | 22 | 5 領域に追跡ファイルが残る旧 HEAD を更新し、clean なワールドのファイルも削除される | 表 | 51 | 527 |
| 43 | `test_world_source_rename_outside_protected_roots_is_treated_as_deletion` | 1 | 19 | rename 検出が旧パスの削除を隠し、追跡中のワールド source を失う | 表 | 52 | 546 |
| 44 | `test_deleted_path_diff_error_stops_before_checkout_or_branch_deletion` | 1 | 43 | 削除パス照会の失敗を空集合として扱い、保護領域の追跡ファイルを削除する | 表 | 53 | 589 |

`tools/devenv_migration/tests/test_pi_vertex_launchers.py`（`devcontainer-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 45 | `test_concurrent_launchers_initialize_only_empty_missing_auth` | 1 | 13 | 同時起動で保存済みの auth を置き換える、不正な JSON・公開権限・staging が残る（先着の上書きは検出できない） | 表 | 54 | 602 |

`tests/scripts/test_superpowers_lifecycle.py`（`script-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 46 | `LifecycleInstructionTests::test_continuation_gates_keep_unapproved_or_unauthorized_resumes_blocked` | 1 | 12 | 再開判定表の blocked の行が ready に変わり、受け取り側が未承認・無許可の作業を実装する（権限を決める値） | 表・重さは #236 | 55 | 614 |

#### 低


`tools/agent_runner/tests/adapters/claude_code/test_adapter.py`（`agent-runner-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 47 | `test_assistant_model_overrides_init_model` | 1 | 3 | init の別名より後の assistant の実際のモデルを identity にする。壊れると記録のモデル名が別名のまま | 表 | 56 | 617 |
| 48 | `test_auth_error_text_reports_awaiting_authentication` | 1 | 6 | 失敗した result の本文のログイン要求を awaiting_authentication に分類する（失敗の種類の分類） | 表 | 57 | 623 |
| 49 | `test_incomplete_assistant_prose_is_not_auth_diagnostic` | 1 | 3 | result の無いストリームの assistant の文に認証の語があっても awaiting_authentication にしない。壊れると失敗の種類だけが変わる | 表 | 58 | 626 |

`tools/agent_runner/tests/adapters/codex/test_codex.py`（`agent-runner-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 50 | `test_prepare_tells_model_to_read_configured_skill_source_paths` | 1 | 12 | $名前と設定 source の絶対パスの読み込み指示を prompt に入れる。外れても担当は指定の skill・版を使わず作業する（今の役割は skills=[]） | 表 | 59 | 638 |
| 51 | `test_rollout_uses_effective_child_environment` の `HOME` | 1 | 0 | CODEX_HOME が無いとき HOME/.codex から rollout を読む。壊れると全ての実行の identity が黙って null になる | 表 | 60 | 638 |

`tools/agent_runner/tests/adapters/cursor/test_cursor.py`（`agent-runner-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 52 | `test_prepare_tells_model_to_read_configured_skill_source_paths` | 1 | 10 | skill と設定 source の絶対パスの読み込み指示を prompt に入れる。外れても担当は指定の skill・版を使わず作業する（今の役割は skills=[]） | 表 | 61 | 648 |

`tools/agent_runner/tests/adapters/devin/test_adapter.py`（`agent-runner-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 53 | `test_quoted_diagnostics_in_model_messages_are_answer_data` の `no-answer` | 1 | 0 | 回答の無い実行（最後の step が tool を呼ぶ）を、標準出力の引用の語によらず response_failed にする。外れると awaiting_authentication に誤分類される | #236 の判定 | 62 | 648 |

`tools/agent_runner/tests/test_config.py`（`agent-runner-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 54 | `test_reserved_self_cannot_hide_a_real_agent_definition` | 1 | 8 | self を agent の定義名に使わせない。外れると実在の agent の定義が self に隠れる | 表 | 63 | 656 |

`tools/agent_runner/tests/test_environ.py`（`agent-runner-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 55 | `test_literal_environ_parses_proc_and_skips_malformed_entries` | 1 | 22（準備 10 を含む） | 起動時の環境（/proc/self/environ）を返す。外すと許可した変数に locale の強制の値・起動後の値が黙って渡る | 表 | 64（件数が目標に届く） | 678 |

`tools/agent_runner/tests/test_process.py`（`agent-runner-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 56 | `test_buffered_original_exit_survives_anchor_reap` | 1 | 23 | 期限切れと同時に CLI が終わっても、届いた元の終了コードを捨てない。外すと exit_code が null になる（記録を失う） | 表 | 65 | 701 |
| 57 | `test_supervisor_preserves_literal_environment` | 2 | 32 | 起動時の環境を /proc/self/environ から作り直して CLI に渡す（locale の強制を受けない）。外すと渡す環境が黙って変わる | 表 | 67 | 733 |

`tools/agent_runner/tests/test_review_regressions.py`（`agent-runner-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 58 | `test_allowlisted_environment_is_the_literal_exec_environment` | 1 | 28 | 許可した変数を起動時の環境のまま渡す。locale の強制で書き換えると設定していない値の環境で担当が動く（環境の隔離） | 表 | 68 | 761 |

`tools/agent_runner/tests/test_runner.py`（`agent-runner-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 59 | `test_exit_zero_is_not_a_substitute_for_valid_receipt` の `options4-awaiting_authentication`・`options5-awaiting_approval` | 2 | 0 | 終了コードが 0 以外でも受領の awaiting_authentication・awaiting_approval を残す | 表 | 70 | 761 |
| 60 | `test_reported_state_keeps_the_adapter_state_before_the_exit_code_override` | 1 | 7 | reported_state に adapter が出力から分類した状態を、終了コードによる上書きの前のまま残す | 表 | 71 | 768 |
| 61 | `test_adapter_reported_state_is_recorded` | 2 | 9 | adapter が渡した以前の状態を記録し、State でない値は無視して adapter の失敗の状態を残す。壊れると失敗の診断が誤る | 表 | 73 | 777 |
| 62 | `test_launch_failed_is_safe` | 1 | 8 | 起動できない command を launch_failed にし、prompt を結果に出さない | 表 | 74 | 785 |
| 63 | `test_workflow_preserves_literal_environment` の `popen-adapter` | 1 | 0 | 起動時の環境をそのまま CLI に渡す（popen の起動の経路。代表 test_supervisor_preserves_literal_environment と同じ守り） | 表・重さは #236 | 75 | 785 |
| 64 | `test_write_exceptions_follow_the_work_scope_lines` | 1 | 19 | write_exceptions を作業範囲の 2 行の後に見出しと 1 行ずつで並べる。壊れると許可した書き込み先が担当に伝わらない | 表 | 76 | 804 |
| 65 | `test_invalid_write_exceptions_are_rejected_before_any_output` の ` a` | 1 | 0 | 前後の空白を拒否する（value == value.strip()）。外れると字下げで作業範囲の行の形を変える値を受け付ける | 表 | 77 | 804 |
| 66 | `test_a_bare_string_is_not_split_into_exceptions` | 1 | 5 | write_exceptions に str を 1 つ渡すと RunnerError。壊れると許可した書き込み先が黙って捨てられ担当に伝わらない | 表 | 78 | 809 |
| 67 | `test_missing_receipt_file_is_missing_not_a_parse_failure` | 1 | 9 | 受領の読み取りの FileNotFoundError を invalid_result でなく missing_result にする。壊れると受領が無い失敗が「壊れている」と表示される | 表 | 79 | 818 |

`.agents/scripts/tests/test_issue_budget.py`（`review-helper-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 68 | `test_user_wait_is_excluded_from_active_time` | 1 | 7 | 利用者の待ち時間を能動時間から除かず、能動時間の統計を誤る | 表 | 80 | 825 |
| 69 | `test_open_user_wait_counts_until_now` | 1 | 4 | 終わっていない利用者の待ち（await-user のまま）を現在時刻まで数えず、能動時間を誤る | 表 | 81 | 829 |
| 70 | `test_checkpoint_is_due_after_threshold_until_recorded` | 1 | 11 | checkpoint の到来の判定を誤り、見逃す（記録後の扱いも） | 表 | 82 | 840 |
| 71 | `test_user_wait_delays_checkpoint_due_time` | 1 | 5 | 利用者の待ちを checkpoint の到来時刻に反映せず、判断を誤る | 表 | 83 | 845 |
| 72 | `test_retry_limit_counts_same_reliability_signature` | 1 | 14 | 同じ信頼性の失敗（signature）の回数を数え誤り、再試行の上限を見誤る | 表 | 84 | 859 |
| 73 | `test_single_safety_failure_is_reported` | 1 | 4 | safety の失敗 1 件を safety_failure として報告せず、見落とす | 表 | 85 | 863 |
| 74 | `test_inconsistent_ledger_is_rejected_with_line` | 4 | 65（準備 51 を含む） | 矛盾した台帳をエラーなしに集計し、誤った能動時間・状態を返す | 表 | 89 | 928 |

`.agents/scripts/tests/test_review_findings.py`（`review-helper-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 75 | `test_stats_reports_false_positives_misses_late_detections_and_severity_drift` | 1 | 46 | 精度の統計（誤検出・見逃し・遅れ・severity の差）を誤る | 表 | 90 | 974 |
| 76 | `test_stats_counts_severity_drift_with_either_reference_style` | 2 | 22 | .md 付き・なしの参照で severity の差を数え落とす | 表 | 92 | 996 |
| 77 | `test_provenance_stats_retains_adoption_after_resolution_without_counting_split_sources_twice` | 1 | 7 | 採用の数え方（解消後の保持、分割した出所の二重計上）を誤る | 表 | 93 | 1,003 |
| 78 | `test_provenance_stats_separates_same_model_with_different_observations` | 2 | 21 | 同じモデルでも effort・session が違う観測を 1 つに数える（統計の誤り） | 表 | 95 | 1,024 |
| 79 | `test_provenance_stats_adopts_a_finding_fixed_in_a_later_round` | 1 | 22 | 後のサイクルで直した指摘の採用の帰属を誤る | 表 | 96 | 1,046 |
| 80 | `test_provenance_stats_does_not_credit_a_later_round_from_another_session` | 1 | 23 | 別セッションの後のサイクルの採用を帰属させる | 表 | 97 | 1,069 |
| 81 | `test_provenance_stats_leaves_adoption_unevaluated_when_identifiers_are_unobserved` | 1 | 11 | 識別子が未観測なのに採用を確定させる | 表 | 98 | 1,080 |
| 82 | `test_stats_rejects_malformed_folded_records_without_a_traceback` | 3 | 16 | 壊れた fold の記録（版・severity・history）を集計し、終了 0 で誤った統計を返す | 表 | 101 | 1,096 |
| 83 | `test_stats_names_records_pr_for_a_malformed_pr` | 1 | 6 | records.pr の不正を検査せず、壊れた記録をそのまま集計する | 表 | 102 | 1,102 |
| 84 | `test_provenance_stats_attributes_waiting_and_rework_to_the_actual_actor` | 1 | 35 | 待ち時間・やり直しを実際の担当に帰属させず統計を誤る | 表 | 103 | 1,137 |
| 85 | `test_provenance_stats_uses_planning_time_instead_of_counting_the_same_find_stage_twice` | 1 | 14 | 同じ find 工程の時間を二重に数える | 表 | 104 | 1,151 |
| 86 | `test_provenance_stats_marks_legacy_identity_and_unmeasured_time_unknown` | 1 | 14 | 旧形式の識別子・未計測の時間を不明とせず、確定値として出す | 表 | 105 | 1,165 |
| 87 | `test_cli_stats_reads_cycle_documents_under_verified` | 1 | 7 | verified の cycle 以外の文書を数え、統計を誤る | 表 | 106 | 1,172 |
| 88 | `test_run_stats_counts_completion_failures_timeouts_and_time_per_line` | 1 | 36 | 完走率・失敗・タイムアウトの統計を誤る | 表 | 107 | 1,208 |
| 89 | `test_extract_terms_skips_plain_words_and_excluded_directories` | 1 | 23 | 語の抽出を誤り、普通の語や除外 dir の語を候補にする | 表 | 108 | 1,231 |
| 90 | `test_statement_candidates_reads_code_spans_removed_from_documents` | 1 | 14 | 文書から消えたコードスパンの語を落とす | 表 | 109 | 1,245 |
| 91 | `test_statement_candidates_keeps_the_excerpt_around_a_term_far_into_a_long_line` | 1 | 13 | 長い行の遠くにある語の抜粋から、語が消える | 表 | 110 | 1,258 |
| 92 | `test_statement_candidates_does_not_count_a_term_inside_a_longer_word` | 1 | 11 | 長い語の中の語を数え、誤った候補が出る | 表 | 111 | 1,269 |
| 93 | `test_statement_candidates_finds_terms_containing_regex_characters` | 1 | 20 | 記号入りの語を候補から落とす | 表 | 112 | 1,289 |
| 94 | `test_extract_terms_does_not_mistake_removed_dash_lines_for_headers` | 1 | 12 | 削除行の「---」をヘッダと取り違え、差分の読み取りを誤る | 表 | 113 | 1,301 |
| 95 | `test_extract_terms_places_removed_lines_in_the_old_file` | 1 | 20 | 削除行を旧ファイルの行として扱わず、位置を誤る | 表 | 114 | 1,321 |
| 96 | `test_extract_terms_reads_changed_lines_of_documents` | 1 | 25 | 文書の変更行の語を読み落とす | 表 | 115 | 1,346 |

`.agents/scripts/tests/test_review_records.py`（`review-helper-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 97 | `test_v2_record_keeps_session_through_render_extract_and_fold` | 1 | 8 | fold が provenance（session）を黙って落とす記録の欠落 | 表 | 116 | 1,354 |
| 98 | `test_records_with_unicode_line_separators_round_trip` | 1 | 5 | unicode の行区切りで記録が分割・破損する（実際に起きた不具合の再発防止） | 表 | 117 | 1,359 |

`.agents/skills/review-fix-planning/tests/test_upsert_pr_comment.py`（`review-helper-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 99 | `test_agent_id_comes_from_the_shared_module_whatever_the_cwd` | 1 | 11 | agent id がずれて自分のコメントを見失い、重複投稿する | 表 | 118 | 1,370 |
| 100 | `test_a_malformed_comments_payload_stops_before_any_write` | 1 | 5 | 壊れた応答を空とみなして重複投稿する | 表 | 119 | 1,375 |
| 101 | `test_records_post_rejects_a_closed_pull_request` | 1 | 4 | open でない PR（CLOSED）に記録を投稿する（誤った対象への書き込み） | 表 | 120 | 1,379 |

`.agents/skills/review-verify/tests/test_dispatch.py`（`review-helper-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 102 | `test_prefixed_named_skill_digest_is_not_recorded_as_a_fake_path` | 1 | 15 | 接頭辞付きの skill の digest を偽のパスとして記録する | 表 | 121 | 1,394 |
| 103 | `test_time_limits_follow_the_projected_deadline` | 2 | 29 | 上限 1800 の丸めと短い期限の予約を誤る | 表 | 123 | 1,423 |

`.devcontainer/test-install-ctx7.bash`（`devcontainer-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 104 | 別の版の ctx7 を拒否する | 0 | 3 | PATH の先の別の版の ctx7 を受け入れ、固定した版でない CLI を使う（動くので気付けない） | 表 | 123 | 1,426 |

`tests/scripts/test-new-world.bash`（`script-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 105 | 場面 18（uv sync の失敗） | 0 | 7 | 同期ありの uv sync が失敗しても、成功と報告する（雛形の適用は済んでいる） | 表 | 123 | 1,433 |

`tests/scripts/test-resoloop-fork.bash`（`script-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 106 | 場面 4 の一部（upstream の fetch） | 0 | 8 | checkout の前に upstream を fetch せず、古い upstream/main を黙って取り出す | 表 | 123 | 1,441 |

#### 中


`tools/agent_runner/tests/adapters/claude_code/test_adapter.py`（`agent-runner-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 107 | `test_prepare_builds_stream_json_launch` | 1 | 11 | --model に設定のモデルを渡す。外れると既定のモデルで黙って動く。JSON の指示が stdin から落ちる | 表 | 124 | 1,452 |
| 108 | `test_prepare_maps_effort_and_appends_agent_args` | 1 | 6 | effort が落ちると既定の推論の強さで黙って動く。agent.args が落ちると利用者の追加引数が黙って効かない | 表 | 125 | 1,458 |
| 109 | `test_permission_denials_report_awaiting_approval` | 1 | 4 | permission_denials があれば成功にしない。外れると必要な操作を拒否された実行を成功と報告する | 表 | 126 | 1,462 |
| 110 | `test_error_subtype_reports_response_failed` | 1 | 4 | subtype が error なら is_error が false でも失敗にする。外れると実行中のエラーで終わった result を成功にする | 表 | 127 | 1,466 |
| 111 | `test_missing_result_reports_response_failed` | 1 | 3 | result の無いストリームを、終了コード 0 でも成功にしない。外れると途切れた実行を成功と報告する | 表 | 128 | 1,469 |
| 112 | `test_skill_invocation_alone_does_not_prove_file_read` | 1 | 14 | Skill ツールの呼び出しだけで skill の版を記録しない。外れると読んでいない版が実測として残る | 表 | 129 | 1,483 |
| 113 | `test_prepare_resolves_role_skills_against_work_dir` | 1 | 14 | role.skills と work_dir 基準の SKILL.md の絶対パスを stdin に足す。設定しただけでは版を記録しない | 表 | 130 | 1,497 |
| 114 | `test_missing_identity_is_not_filled_from_agent_settings` | 1 | 6 | init が無いとき identity を要求の provider・effort で埋めない。壊れると観測していない値を実測として記録する | 表 | 131 | 1,503 |
| 115 | `test_stderr_failure_dominates_plausible_result` | 2 | 8 | 成功らしい result があっても stderr の認証・承認の診断を優先する。外れると止まった実行を成功と報告する | 表 | 133 | 1,511 |
| 116 | `test_error_event_dominates_plausible_result` | 1 | 6 | result の前の error イベントを失敗にする。外れると error の後にもっともらしい result があれば成功と報告する | 表 | 134 | 1,517 |
| 117 | `test_interrupted_result_is_not_success` | 3 | 4 | 中断を示す subtype を interrupted にする。response_failed に取り違えると取り消された担当の後に fallback の有料の実行が始まる | 表 | 137 | 1,521 |
| 118 | `test_is_error_overrides_success_subtype` | 1 | 3 | subtype が success でも is_error が true なら失敗にする。外れると is_error の result を成功と報告する | 表 | 138 | 1,524 |
| 119 | `test_explicit_assistant_error_is_auth_diagnostic` | 1 | 5 | error の項目を持つ assistant のイベントを失敗の経路（診断）にし、認証待ちに分類する | 表 | 139 | 1,529 |
| 120 | `test_later_unfinished_turn_invalidates_earlier_success` | 1 | 3 | 成功の result の後に次の未完了のターンが続けば失敗にする。外れると前の成功を再利用して成功と報告する | 表 | 140 | 1,532 |
| 121 | `test_truncated_event_after_success_invalidates_completion` | 1 | 8 | 成功の result の後の途中で切れた行（先頭に空白のある {）を壊れたイベントとして残し成功を無効にする | 表 | 141 | 1,540 |
| 122 | `test_collect_success_extracts_identity_and_json_payload`（正しく通る例） | 1 | 156（`tools/agent_runner/tests/adapters/claude_code/conftest.py` 33・準備 108 を含む） | 失敗・未完了を成功にしない拒否の群の対の正例（何でも失敗にする実装を通さない）。取り違えは記録の取り違え | 表 | 142 | 1,696 |

`tools/agent_runner/tests/adapters/codex/test_codex.py`（`agent-runner-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 123 | `test_collect_skill_version_stays_unknown_when_observed_content_differs` | 1 | 23 | 観測した内容が今の SKILL.md と違えば版を記録しない。外すと review-verify の出所の記録（skills の path/sha256）を黙って取り違える | 表 | 143 | 1,719 |
| 124 | `test_failure_diagnostics_override_prior_message` | 5 | 30 | 成功らしい stream でも stderr の認証・承認の診断、後の error・turn.failed があれば成功にしない。外すと古い payload で偽の成功になる | 表 | 148 | 1,749 |
| 125 | `test_truncated_later_event_does_not_reuse_success` | 2 | 8 | 成功の後の途中で切れた行（{・[ で始まる）で、前の成功を再利用しない | 表 | 150 | 1,757 |
| 126 | `test_missing_or_unfinished_final_turn_is_failure` | 1 | 7 | turn.completed の無い最後の message を成功にしない。終了コード 0 でも完了の証拠を求める | 表 | 151 | 1,764 |
| 127 | `test_untrusted_thread_id_cannot_select_rollout` | 1 | 9 | thread_id にパス区切りやワイルドカードがあれば失敗にし rollout を探さない。外すと session_id を取り違える | 表 | 152 | 1,773 |
| 128 | `test_rollout_uses_effective_child_environment` の `CODEX_HOME` | 1 | 14（関数 14 を含む） | rollout を子に渡した環境の CODEX_HOME から読む。外すと別の CODEX_HOME の記録から identity を写す | 表 | 153 | 1,787 |
| 129 | `test_rollout_cannot_borrow_identity_from_another_session` | 2 | 15 | session_meta の id が違う rollout と、sessions の外を指す symlink の rollout から identity を写さない | 表 | 155 | 1,802 |
| 130 | `test_latest_turn_cannot_reuse_an_earlier_message` | 2 | 12 | 後続の turn.started や空の agent_message が先行の本文を消す。外れると古い payload で黙って成功する | 表 | 157 | 1,814 |
| 131 | `test_invalid_or_ambiguous_thread_event_is_failure` | 1 | 7 | 異なる 2 つの thread_id を曖昧として失敗にする。外すと最後の ID を session_id にして記録を取り違える | 表 | 158 | 1,821 |
| 132 | `test_rollout_sessions_directory_cannot_escape_runtime_home` | 1 | 10 | sessions ディレクトリ自体が CODEX_HOME の外を指すときは rollout を読まない。外すと別の場所の記録から identity を写す | 表 | 159 | 1,831 |
| 133 | `test_invalid_final_object_cannot_return_a_nested_fragment` | 1 | 6 | 壊れた外側の JSON から内側の object を取り出さない。次の「{」を探す変更をすると誤った payload で黙って成功する | 表 | 160 | 1,837 |
| 134 | `test_invalid_event_type_is_response_failed_with_identity` | 1 | 22 | type が文字列でない行を壊れた出力として失敗にする。外すと type の壊れた turn.failed・error を見落として success を返す | 表 | 161 | 1,859 |
| 135 | `test_collect_success_builds_receipt_and_identity`（正しく通る例） | 1 | 41 | 後の失敗・壊れた行・thread・診断で成功にしない拒否の群の対の正例（何でも拒否する実装を通さない） | 表 | 162 | 1,900 |
| 136 | `test_collect_nested_json_object_returns_outer_object`（正しく通る例） | 1 | 10 | 散文・コードフェンスに包んだ JSON の外側の object を返す正例（入れ子の断片を拾う拒否の対） | 表 | 163 | 1,910 |
| 137 | `test_collect_skill_versions_hash_successfully_read_skill_files`（正しく通る例） | 1 | 42 | skill の版の記録の正例。内容の不一致の拒否と組で、何でも unknown にする実装を通さない。壊れると全ての codex の実行で版が unknown になる | 表 | 164 | 1,952 |

`tools/agent_runner/tests/adapters/codex/test_integration.py`（`agent-runner-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 138 | `test_reconnect_requires_fresh_completion_and_clean_process_exit` | 2 | 133（`tools/agent_runner/tests/adapters/codex/fake_cli.py` 50・準備 63 を含む） | 伏せ字処理で成功 payload・identity の数・真偽値が null に変わらない。再接続後の turn.failed を成功にしない | 表 | 166 | 2,085 |

`tools/agent_runner/tests/adapters/cursor/test_cursor.py`（`agent-runner-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 139 | `test_prepare_reads_prompt_from_stdin_and_trusts_worktree` | 1 | 8 | 依頼文を stdin から外しても起動は成功し、担当は依頼の無いまま JSON の回答を返せる（もっともらしい誤った成功） | 表 | 167 | 2,093 |
| 140 | `test_collect_reading_skill_backup_does_not_record_unread_skill` | 1 | 35 | 読んだファイルが SKILL.md でなければ（SKILL.md.bak）、親ディレクトリ名の skill の版として記録しない | 表 | 168 | 2,128 |
| 141 | `test_collect_skill_version_stays_unknown_when_read_limit_is_exceeded` | 1 | 7 | CLI が上限超過を報告した読み込みは、内容が今のファイルと一致しても版を記録しない | 表 | 169 | 2,135 |
| 142 | `test_collect_unobserved_identity_is_not_copied_from_settings` | 1 | 9 | init の無い出力で identity を設定から補わず全て null にする。補うと要求したモデルが動いたと記録する | 表 | 170 | 2,144 |
| 143 | `test_collect_later_corruption_or_failure_cannot_reuse_success` | 6 | 14 | 成功の result の後の壊れた行・失敗の result・error・文字列の is_error で、先行の成功を再利用しない。外すと古い payload で黙って成功する | 表 | 176 | 2,158 |
| 144 | `test_collect_invalid_outer_json_cannot_be_replaced_by_nested_object` | 1 | 5 | 壊れた外側の JSON から内側の object を取り出さない。次の「{」を探す変更をすると誤った payload で黙って成功する | 表 | 177 | 2,163 |
| 145 | `test_collect_failure_diagnostics_override_plausible_result` | 2 | 8 | 成功の result（終了コード 0）でも stderr の認証・trust の診断があれば成功にしない。外すと偽の成功になる | 表 | 179 | 2,171 |
| 146 | `test_later_response_requires_its_own_result` の `False-later0`・`False-later1` | 2 | 0 | 成功の result の後の assistant の応答・新しい init は、新しい result が出るまで成功にしない | 表 | 181 | 2,171 |
| 147 | `test_collect_success_builds_receipt_and_identity`（正しく通る例） | 1 | 31 | 後の壊れた行・失敗の result・error・診断で成功にしない拒否の群の対の正例（何でも拒否する実装を通さない） | 表 | 182 | 2,202 |
| 148 | `test_collect_nested_json_result_returns_outer_object`（正しく通る例） | 1 | 13 | 散文に包んだ JSON の外側の object を返す正例（入れ子の断片を拾う拒否の対） | 表 | 183 | 2,215 |
| 149 | `test_collect_skill_versions_from_successful_read_completion`（正しく通る例） | 1 | 35 | readToolCall の完了から skill の版を記録する正例（版を記録しない拒否の群の対） | 表 | 184 | 2,250 |
| 150 | `test_later_response_requires_its_own_result` の `True-later1`（正しく通る例） | 1 | 30（関数 30 を含む） | 新しい init の後の新しい result なら、その payload と最後の init の identity を採用する正例 | 表 | 185 | 2,280 |

`tools/agent_runner/tests/adapters/devin/test_adapter.py`（`agent-runner-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 151 | `test_quoted_diagnostics_in_model_messages_are_answer_data` の `answer` | 1 | 29（関数 29 を含む） | 引用した診断の形の行が回答の本文や後ろにあっても、正しい回答で終わる出力を success にする。外れると正しいレビューが認証待ちで捨てられる | #236 の判定 | 186 | 2,309 |
| 152 | `test_export_error_step_authentication_overrides_answer` | 1 | 13 | export の error の step の認証の失敗を、標準出力が回答で終わっていても優先して awaiting_authentication にする。外れると失敗を成功と報告する | #236 の判定 | 187 | 2,322 |
| 153 | `test_prepare_appends_agent_args` | 1 | 4 | agent.args が argv の末尾に付く。落ちたり前に回ると設定した制限が黙って効かず権限が広がりうる | 表 | 188 | 2,326 |
| 154 | `test_blank_stdout_fails_even_with_export` | 1 | 3 | export に正しい最終メッセージがあっても stdout が空なら成功にしない。外れると途切れた実行を成功と報告する | 表 | 189 | 2,329 |
| 155 | `test_missing_export_fails` | 1 | 4 | export が無ければ stdout にもっともらしい JSON があっても成功にしない。壊れると最終でないメッセージを成功として返しうる | 表 | 190 | 2,333 |
| 156 | `test_skill_tool_call_path_alone_does_not_prove_read` | 1 | 21 | ATIF の tool call の引数に SKILL.md のパスがあるだけでは skill の版を記録しない | 表 | 191 | 2,354 |
| 157 | `test_prepare_includes_requested_skills_and_configured_source` | 1 | 15 | role.skills と設定 source の SKILL.md の絶対パスをプロンプトのファイルに書く。落ちると指定の skill が使われない | 表 | 192 | 2,369 |
| 158 | `test_identity_never_copies_requested_configuration` | 1 | 11 | export に agent・session_id が無いとき identity を要求の provider・effort・model で埋めない（記録の取り違え） | 表 | 193 | 2,380 |
| 159 | `test_diagnostics_override_plausible_success` | 3 | 14 | stdout と export にもっともらしい成功があっても stderr の認証・承認の診断を優先し payload を返さない。外れると止まった実行を成功と報告する | 表 | 196 | 2,394 |
| 160 | `test_truncated_later_stdout_cannot_reuse_completion` | 2 | 6 | 回答の後に JSON らしい行（完全でも途中で切れていても）が続く stdout を成功にしない。外れると前の回答で成功にする | 表 | 198 | 2,400 |
| 161 | `test_truncated_later_export_cannot_reuse_completion` | 1 | 7 | 完全な ATIF の JSON の後に切れた記録が続く export を json.loads で丸ごと拒否して成功にしない | 表 | 199 | 2,407 |
| 162 | `test_latest_empty_agent_message_cannot_reuse_earlier_answer` | 1 | 8 | 最後の agent の step のメッセージが空なら前の step の回答を使わない（最後の step だけを最終メッセージにする） | 表 | 200 | 2,415 |
| 163 | `test_incomplete_or_failed_export_does_not_reuse_prior_answer` | 1 | 13 | 前に回答の step がある export の最後に user の step が続くとき、前の回答を使わない。外れると終わっていない実行を成功にする | 表 | 201 | 2,428 |
| 164 | `test_invalid_final_json_does_not_return_nested_fragment` | 2 | 8 | 最終の回答が配列や途中で切れた object のとき、中の入れ子の object を拾って成功にしない | 表 | 203 | 2,436 |
| 165 | `test_tool_run_stdout_not_ending_with_final_answer_fails` | 1 | 16 | 回答の行の後ろに文字が続く（stdout の最後の JSON が回答そのものでない）とき成功にしない | 表 | 204 | 2,452 |
| 166 | `test_tool_run_final_step_calling_tool_fails` | 1 | 8 | 最後の agent の step がまだ tool call を続けているなら、そのメッセージを最終の回答にしない | 表 | 205 | 2,460 |
| 167 | `test_collect_success_extracts_identity`（正しく通る例） | 1 | 9 | stdout・export の不整合や診断を成功にしない拒否の群の対の正例（何でも失敗にする実装を通さない） | 表 | 206 | 2,469 |
| 168 | `test_collect_success_text_shape`（正しく通る例） | 1 | 7 | text の役割で成功にする正例。stdout・export の不整合を成功にしない拒否の群の対（何でも失敗にする実装を通さない） | 表 | 207 | 2,476 |
| 169 | `test_plain_progress_after_json_does_not_invalidate_completion`（正しく通る例） | 1 | 6 | 回答の後の普通の進捗の行は許す正例。_plain_tail の拒否の群（後ろに JSON らしい行が続く stdout を成功にしない）の対 | 表 | 208 | 2,482 |
| 170 | `test_tool_run_stdout_ending_with_final_answer_succeeds`（正しく通る例） | 1 | 9 | tool を使う途中のメッセージが連結され最後がフェンスの回答の stdout と export で成功にする正例（#185・#186） | 表 | 209 | 2,491 |

`tools/agent_runner/tests/adapters/pi/test_adapter.py`（`agent-runner-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 171 | `test_prepare_maps_skill_sources_and_args` | 1 | 10 | agent.skill_sources を順に --skill に渡し、agent.args を末尾に付ける。落ちると設定した skill や引数が黙って効かない | 表 | 210 | 2,501 |
| 172 | `test_exit_zero_without_agent_end_is_response_failed` | 1 | 3 | agent_end の無いストリームを成功にしない（Pi は失敗でも終了コード 0 を返すことがある） | 表 | 211 | 2,504 |
| 173 | `test_aborted_stop_reason_is_interrupted` | 1 | 6 | stopReason の aborted を interrupted にする。response_failed に取り違えると取り消し後に fallback の実行が始まる | 表 | 212 | 2,510 |
| 174 | `test_unknown_stop_reason_is_response_failed` | 1 | 6 | 正常でない stopReason（length など切れた回答）を成功にしない | 表 | 213 | 2,516 |
| 175 | `test_text_shape_returns_concatenated_text` | 1 | 6 | text の役割で最後の assistant の text をすべてつなぐ。一部だけ返すと欠けた回答を成功として返す | 表 | 214 | 2,522 |
| 176 | `test_only_completed_matching_full_read_is_hashed` の `mentioned`・`failed`・`partial`・`mismatch` | 4 | 0 | 完了の無い開始・失敗した完了・範囲指定の read・内容の不一致では版を記録しない。外れると読んでいない・一部しか読んでいない版を記録する | 表 | 218 | 2,522 |
| 177 | `test_prepare_applies_role_skills` | 1 | 11 | role.skills と設定 source の SKILL.md の絶対パスを stdin に足す。落ちると指定の skill が使われず別の版を読む | 表 | 219 | 2,533 |
| 178 | `test_final_lifecycle_dominates_earlier_turn` | 4 | 10 | 最後の agent_end とその後の settlement だけが完了を決める（前の成功・先に出た settlement を使わない） | 表 | 223 | 2,543 |
| 179 | `test_diagnostics_override_plausible_answer` | 2 | 8 | もっともらしい回答があっても stderr と error イベントの認証・承認の診断を優先する。外れると止まった実行を成功と報告する | 表 | 225 | 2,551 |
| 180 | `test_missing_identity_is_not_filled_from_config` | 1 | 9 | assistant に model・provider・thinkingLevel と session が無いとき identity を設定で埋めない（記録の取り違え） | 表 | 226 | 2,560 |
| 181 | `test_empty_skill_requires_observed_text_content` | 1 | 12 | read の完了の result に text の content が無ければ、空の SKILL.md でも版を記録しない。外れると未観測の空ファイルの版を記録する | 表 | 227 | 2,572 |
| 182 | `test_trailing_broken_event_cannot_reuse_success` | 3 | 11 | 完了の後の壊れた行で前の回答を使わない | 表 | 230 | 2,583 |
| 183 | `test_new_session_without_completion_cannot_reuse_old_payload` | 1 | 5 | 完了の後に新しい session が始まり完了していなければ前の回答を使わず失敗にする。外れると別のセッションの前の回答で成功にする | 表 | 231 | 2,588 |
| 184 | `test_collect_success_extracts_identity_and_payload`（正しく通る例） | 1 | 10 | 異常なストリームを成功にしない拒否の群の対の正例（何でも失敗にする実装を通さない）。identity を最後の agent_end と session の id から取る | 表 | 232 | 2,598 |
| 185 | `test_only_completed_matching_full_read_is_hashed` の `complete`（正しく通る例） | 1 | 17（関数 17 を含む） | 同じ toolCallId の read の開始と成功した完了が対で、範囲指定が無く全文が今のファイルと一致するときだけ版を記録する正例 | 表 | 233 | 2,615 |
| 186 | `test_plain_progress_after_completion_is_harmless`（正しく通る例） | 1 | 4 | 完了の後の普通の進捗の行は許す正例（壊れた行で前の回答を使わない拒否の対） | 表 | 234 | 2,619 |

`tools/agent_runner/tests/adapters/test_parser_regressions.py`（`agent-runner-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 187 | `test_codex_unicode_session_metadata_cannot_hide_mismatch` | 1 | 8 | session_meta の照合を LF だけで分ける。splitlines に戻ると別の session の rollout を受け入れ、レビューの記録が別のモデルのものになる | 表 | 235 | 2,627 |
| 188 | `test_invalid_fence_cannot_salvage_inner_json` | 4 | 5 | 閉じフェンスの無い回答の最初の object を payload にしない。前の候補の値を使い回すと壊れた最終回答が下書きの値で success になる | 表 | 239 | 2,632 |
| 189 | `test_devin_fence_failure_in_either_channel_is_read_only` | 1 | 40 | 最終の ATIF の回答が閉じフェンスを欠くとき成功にしない。collect がファイルを書き換えず外部コマンドを起動しないことも確かめる | 表 | 240 | 2,672 |
| 190 | `test_codex_recovery_requires_new_complete_message_and_terminal_success` | 1 | 7 | turn.failed の後に新しい message と turn.completed が来ても失敗のままにする。外すと失敗した turn の後の回答が成功になる | 表 | 241 | 2,679 |
| 191 | `test_codex_recovery_does_not_clear_other_diagnostic_channels` | 1 | 15 | 回復しても、stdout の JSON でない行の認証・承認の診断を消さない | 表 | 242 | 2,694 |
| 192 | `test_codex_unicode_rollout_cannot_hide_corrupt_lf_record` | 1 | 10 | rollout の破損した記録で失敗にする（rollout を LF だけで分け、区切り文字で破損を隠さない） | 表 | 243 | 2,704 |
| 193 | `test_fenced_json_with_nested_code_backticks_is_data`（正しく通る例） | 1 | 8 | pi のフェンスの JSON の解析の正例。JSON の文字列中の ``` を閉じ fence と誤らない（閉じ fence の拒否の対） | 表 | 244 | 2,712 |
| 194 | `test_codex_fresh_completed_message_recovers_error`（正しく通る例） | 1 | 121（準備 105 を含む） | codex の再試行の回復（pending_errors.clear()）の正例。新しい完了した message の後は先の error から回復する | 表 | 245 | 2,833 |

`tools/agent_runner/tests/test_checkout_policy.py`（`agent-runner-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 195 | `test_batch_reports_parallel_checkout_edit` | 1 | 18 | 他のセッションが登録済みの checkout に並行して加えた変更を outside_changes・checkout_audit に残す。落とすと見逃す | #236 の判定 | 246 | 2,851 |

`tools/agent_runner/tests/test_cli.py`（`agent-runner-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 196 | `test_explicit_missing_and_auto_broken_personal_are_errors` | 1 | 13 | 自動で探した個人設定の場所が壊れた symlink のとき config_io にする。無いと個人設定が黙って無視され雛形だけで run が進む | 表 | 247 | 2,864 |
| 197 | `test_run_exit_codes_and_atomic_result` の `partial_success-1` | 1 | 0 | 成功していない batch（partial_success・failed）を終了コード 0 にしない。0 だと呼び出し側が失敗を成功として扱う | 表 | 248 | 2,864 |
| 198 | `test_cli_overlay_assignment_priority_preserves_fallback` | 1 | 46 | --assign が無視されると、選んだ担当（self など）でなく個人設定・雛形の担当が黙って起動する（有料の担当が動く） | 表 | 249 | 2,910 |
| 199 | `test_sigint_saves_interrupted_batch_and_restores_handler` | 1 | 58 | SIGINT で共有の cancel を立て結果を保存し終了コード 130 を返す。無いと Ctrl-C で担当が止まらず、利用者は止めたつもりでも動き続ける | 表 | 250 | 2,968 |
| 200 | `test_after_run_gets_the_result_path_and_never_changes_the_exit_code` の `3-failed` | 1 | 0 | 非 0 で終わった後処理を success と報告しない。壊れると review の後処理（finalize-parent・attach-runner）の失敗が成功と報告される | 表 | 251 | 2,968 |
| 201 | `test_after_run_internal_error_is_reported_without_changing_the_exit_code` | 1 | 12 | 後処理の監督で例外が出ても、終了コードを変えず response_failed・停止未確認として報告する | 表 | 252 | 2,980 |
| 202 | `test_after_run_is_not_started_after_an_interrupted_run` | 1 | 11 | SIGINT で中断した run では後処理（finalize-parent・attach-runner）を起動しない。外れると利用者の停止の後にも後処理が走る | 表・重さは #236 | 253 | 2,991 |
| 203 | `test_invalid_write_exceptions_are_rejected_before_any_output` の `dash-separate-token` | 1 | 0 | 別の引数に書いた -x の argparse の誤りで CLI が止まり出力先を作らない。error() が戻ると誤ったオプションを無視して既定値で run が進む | 表 | 254 | 2,991 |
| 204 | `test_run_exit_codes_and_atomic_result` の `success-0`（正しく通る例） | 1 | 54（関数 54 を含む） | [partial_success-1] の拒否の正例（何でも 1 にする実装で通らないように）。成功の run は終了コード 0 | 表 | 255 | 3,045 |
| 205 | `test_after_run_gets_the_result_path_and_never_changes_the_exit_code` の `0-success`（正しく通る例） | 1 | 31（関数 31 を含む） | [3-failed] の失敗の報告の正例。成功した後処理を成功と報告し、終了コードと result.json の state を変えない | 表 | 256 | 3,076 |
| 206 | `test_invalid_write_exceptions_are_rejected_before_any_output` の `valid`（正しく通る例） | 1 | 203（関数 25・準備 178 を含む） | [dash-separate-token] の拒否の正例（正しい値なら同じ呼び出しが成功する） | 表 | 257 | 3,279 |

`tools/agent_runner/tests/test_config.py`（`agent-runner-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 207 | `test_recursive_overlay_replaces_arrays_and_preserves_other_fields` | 1 | 24 | 個人設定の table を再帰的に統合し配列は置き換える。壊れると利用者が選んだのと別の担当・モデル・期限で run が進む | 表 | 258 | 3,303 |
| 208 | `test_assignment_override_is_last_and_keeps_explicit_fallback` | 1 | 10 | --assign が個人設定の後に効き、agents だけ置き換えて明示の fallback を残す。外れると --assign が黙って無視される | 表 | 259 | 3,313 |
| 209 | `test_config_errors_are_categorized_without_input_or_traceback_leaks` | 1 | 18 | 未知のキーを拒否する（extra=forbid）。外れると綴りを誤ったキーが黙って無視され、書いた設定と違う設定で run が進む | 表 | 260 | 3,331 |
| 210 | `test_references_must_resolve` | 1 | 10 | 最終形の割り当てで未定義の role を拒否する。外れると個人設定の役割名の誤記が黙って通る | 表 | 261 | 3,341 |
| 211 | `test_duplicate_models_are_rejected_across_all_candidates` | 1 | 10 | 同じ role の agents と fallback の全候補で同じモデルの重複を拒否する。外れると重複したモデルの設定が黙って通る | 表 | 262 | 3,351 |
| 212 | `test_diversity_constraint_checks_fallback_candidates` | 1 | 5 | exclude_same_model_as の 2 つの role の候補（fallback を含む）に同じモデルがあれば拒否する。外れると制約が黙って破られる | 表 | 263 | 3,356 |
| 213 | `test_personal_path_precedence` | 5 | 22 | 個人設定の場所の優先順（明示・~ の展開・XDG・既定）を分岐ごとに確かめる。誤ると意図と違う個人設定を読む | 表 | 268 | 3,378 |
| 214 | `test_nested_or_malformed_depth_is_rejected` | 1 | 7 | runner の担当（AGENT_RUNNER_DEPTH=1）からの入れ子の run を nested_invocation で拒否する | 表 | 269 | 3,385 |
| 215 | `test_receipt_rejects_non_json_payloads` | 2 | 9 | 担当の回答の NaN・Infinity・1e400 を payload にしない。外れると不正な結果を success と報告し、保存した記録の値が黙って null に変わる | 表 | 271 | 3,394 |
| 216 | `test_diversity_constraint_accepts_disjoint_candidates`（正しく通る例） | 1 | 8 | test_diversity_constraint_checks_fallback_candidates の拒否の正例（重ならない候補は通す） | 表 | 272 | 3,402 |
| 217 | `test_top_level_depth_is_allowed`（正しく通る例） | 1 | 103（準備 97 を含む） | 入れ子の拒否（AGENT_RUNNER_DEPTH=1）の正例。未設定なら最上位として通す | 表 | 273 | 3,505 |

`tools/agent_runner/tests/test_models.py`（`agent-runner-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 218 | `test_saved_v1_result_keeps_its_stop_state_without_dropping_observations` | 2 | 58（準備 38 を含む） | 空の旧欄を拒否すると停止済みの run が結果なしで資源が回収されず、記録のある観測を受け付けると黙って捨てる | #236 の判定 | 275 | 3,563 |

`tools/agent_runner/tests/test_process.py`（`agent-runner-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 219 | `test_abnormal_exit_returns_response_failed` | 2 | 6 | CLI の非 0 の終了と signal による終了を、response_failed と実測の終了コードで返す | 表 | 277 | 3,569 |
| 220 | `test_control_eof_never_uses_successful_helper_exit` | 1 | 12 | 制御の報告が無いまま EOF になったとき、監督プロセスの終了コード 0 を成功にしない（exit 0 を成功としない） | 表 | 278 | 3,581 |
| 221 | `test_supervisor_launch_paths_preserve_stdin_and_exit` の `posix_spawn` | 1 | 0 | 終了コード 7 → response_failed と stdin の受け渡し。既定の起動（posix_spawnp）側は代表 2 件と同じ守り | 表・重さは #236 | 279 | 3,581 |
| 222 | `test_supervisor_launch_paths_preserve_stdin_and_exit` の `popen` | 1 | 9（関数 9 を含む） | Popen の起動の分岐で stdin が届き、非 0 の終了を response_failed と実測の終了コードで返す。壊れるとその build で失敗した CLI を成功と報告しうる | 表 | 280 | 3,590 |
| 223 | `test_command_does_not_inherit_private_control_socket` | 1 | 13 | 担当の CLI に監督プロセスの制御ソケットを継承させない（制御ソケットの漏れ） | 表 | 281 | 3,603 |
| 224 | `test_already_cancelled_does_not_spawn` | 1 | 18 | 取り消し済みの event では何も起動しない。外すと後処理（記録の保存など）が起動し、止められるまで途中まで実行される | 表 | 282 | 3,621 |

`tools/agent_runner/tests/test_review_regressions.py`（`agent-runner-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 225 | `test_one_fallback_cannot_fill_two_parallel_role_slots` | 1 | 15 | 1 つの fallback は役割の 1 つの枠しか埋めない。外れると同じ担当が同じ役割で 2 回使われ独立したレビューの数を偽る | 表 | 283 | 3,636 |
| 226 | `test_nonregular_receipt_is_rejected_before_adapter_reads_it` | 1 | 5 | 保持物があるときの response_failed への置き換えを success だけにする。外れると中断も置き換わり fallback が起動する | 表・重さは #236 | 284 | 3,641 |

`tools/agent_runner/tests/test_runner.py`（`agent-runner-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 227 | `test_exit_zero_is_not_a_substitute_for_valid_receipt` の `options0-invalid_result`・`options1-invalid_result`・`options2-invalid_result`・`options3-response_failed`・`options6-invalid_result` | 5 | 24（関数 24 を含む） | exit 0 を成功の代わりにしない。CLI が正しい結果を出していないのに success と報告する（誤った結果の報告） | 表 | 289 | 3,665 |
| 228 | `test_text_receipt_requires_nonblank_text` の ` \n -invalid_result` | 1 | 0 | text の役割の受領の形の検査。空白だけの文を成功にしない（空の回答を成功と報告する） | 表 | 290 | 3,665 |
| 229 | `test_adapter_success_cannot_bypass_missing_receipt` | 1 | 9 | adapter が success と分類しても受領が無ければ missing_result にする。外れると受領の無い試行を success と報告する | 表 | 291 | 3,674 |
| 230 | `test_partial_success_and_independent_worktrees` | 1 | 13 | 同じ役割の担当の一部だけが成功したら batch を partial_success にする。外れると失敗を含む batch を success・failed と取り違えて報告する | 表 | 292 | 3,687 |
| 231 | `test_only_explicit_fallback_is_tried_in_order` | 1 | 11 | 明示した fallback だけを書いた順に試す。外れると別の担当・別の順で実行した結果を返す | 表 | 293 | 3,698 |
| 232 | `test_payload_check_refusal_is_invalid_result_and_tries_fallback` の `returns-false` | 1 | 0 | payload_check が False を返したら拒否する（True だけを受け入れる厳密な判定）。緩めると拒否した payload を成功として返す | 表・重さは #236 | 294 | 3,698 |
| 233 | `test_payload_check_refusal_is_invalid_result_and_tries_fallback` の `raises` | 1 | 31（関数 31 を含む） | payload_check が例外を出したら invalid_result にして次の fallback へ進み、例外の文と拒否した payload を結果に出さない | 表 | 295 | 3,729 |
| 234 | `test_self_has_no_process_or_worktree` | 1 | 6 | self の担当は process・worktree を作らず、全て self の batch を success でなく self にする。誤ると review-verify の指示が渡らない | 表 | 296 | 3,735 |
| 235 | `test_role_deadline_covers_fallback_attempts` | 1 | 73 | 役割の期限が worktree の準備と全ての fallback に共通で、残りの時間だけを各試行に渡す。外れると期限を超えて実行し続ける | 表 | 297 | 3,808 |
| 236 | `test_workflow_preserves_literal_environment` の `posix_spawn-adapter` | 1 | 51（関数 51 を含む） | adapter が LaunchSpec.env で足す値（空の値・改行を含む値を含む）が実行の環境に入る（環境の隔離） | 表 | 298 | 3,859 |
| 237 | `test_cancel_during_run_prevents_fallback` | 1 | 15 | 実行中に取り消したら interrupted にして fallback を起動しない。外れると利用者が止めた後に別の担当が起動する | 表 | 299 | 3,874 |
| 238 | `test_preexisting_cancel_launches_nothing` | 1 | 13 | 実行前に取り消し済みなら何も起動せず worktree も作らない。外れると取り消した後に起動する（費用と副作用） | 表 | 300 | 3,887 |
| 239 | `test_unconfirmed_stop_blocks_success_and_fallback` | 1 | 16 | 準備の停止を確認できないとき成功と報告せず別の担当も起動しない。外れると生き残った処理が書き続ける間に並行して動く | 表 | 301 | 3,903 |
| 240 | `test_concurrency_bounds_whole_assignments` | 1 | 16 | concurrency が担当（fallback を含む）単位の同時実行の上限になる。外れると上限を超えて同時に起動する | 表 | 302 | 3,919 |
| 241 | `test_outside_change_to_already_dirty_file_is_warning_only` | 1 | 13 | 担当が元の checkout の既に dirty なファイルを変えたら outside_changes に出す。外れると作業範囲の外の変更を報告しない | 表 | 303 | 3,932 |
| 242 | `test_nested_invocation_and_invalid_inputs_fail_closed` | 1 | 9 | AGENT_RUNNER_DEPTH=1 の中からの run_workflow を nested_invocation で拒否する。外れると runner の担当から入れ子に起動する | 表 | 304 | 3,941 |
| 243 | `test_invalid_write_exceptions_are_rejected_before_any_output` の `a\u2028b`・`a\x00b` | 2 | 22（関数 22 を含む） | write_exceptions の 1 行の検査を出力の前に行う。改行・制御文字で作業範囲の行を増やし指示を書き換える注入を防ぐ | 表 | 306 | 3,963 |
| 244 | `test_existing_or_symlink_output_is_never_reused` | 1 | 11 | output_dir が既にある・壊れた symlink のときは再利用せず RunnerError。外れると前の実行の成果物を上書き・混在させる | 表 | 307 | 3,974 |
| 245 | `test_default_artifact_directory_is_unique` | 1 | 8 | 既定の成果物の置き場所が /tmp の一意のディレクトリ。外れると保持物がリポジトリ内など一時領域の外に置かれ、実行どうしで記録が混ざる | 表 | 308 | 3,982 |
| 246 | `test_invalid_mutated_config_does_not_emit_serializer_values` | 1 | 8 | 不正に書き換えた設定の再検証で pydantic の警告（不正な値をそのまま stderr に出す）を出さない。外れると設定の値が漏れる | 表 | 309 | 3,990 |
| 247 | `test_invalid_observed_identity_does_not_emit_serializer_values` | 1 | 10 | adapter が観測した不正な型の identity でも serializer の警告を出さない。外れると CLI の出力の値（秘密を含み得る）が漏れる | 表 | 310 | 4,000 |
| 248 | `test_receipt_created_before_launch_is_never_reused` | 1 | 9 | 起動前に作られた受領は使わず invalid_result にする。外れると古い・前もって置かれた受領を success と報告する | 表 | 311 | 4,009 |
| 249 | `test_checkout_preparation_is_supervised` の `late_cancel` | 1 | 0 | worktree の準備が失敗した・停止を確かめられないときは担当を起動しない。外れると不完全な checkout で動いた結果を返す | 表 | 312 | 4,009 |
| 250 | `test_cancel_at_preparation_completion_retains_log_paths` | 1 | 50 | 準備が終わった時点で取り消されたら担当を起動せず、ログのパスを準備のログのままにする。外れると存在しない stdout.log を記録する | 表 | 313 | 4,059 |
| 251 | `test_unsafe_devin_export_is_retained_reported_and_never_collected` の `fifo` | 1 | 0 | FIFO などの特殊ファイルを伏せ字にできたと見なして収集に回さず、sensitive_paths に載せる | 表 | 314 | 4,059 |
| 252 | `test_text_receipt_requires_nonblank_text` の `answer-success`（正しく通る例） | 1 | 12（関数 12 を含む） | text の形の拒否の群で残す正例。空でない文の回答を success にする（何でも拒否する実装を通さない） | 表 | 315 | 4,071 |

`tools/agent_runner/tests/test_workspace.py`（`agent-runner-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 253 | `test_resolve_revision_pins_commit_not_branch` | 1 | 6 | 指定の revision を変わらない commit ID に解決する。無視する・別の commit を返すと別の base で作業した結果を返す | 表 | 316 | 4,077 |
| 254 | `test_audit_diagnoses_unavailable_baseline` の `locked-checkout_missing-True-False` | 1 | 0 | 理由を付けてロックした worktree を locked=false として記録しない。人が prune・削除してよいかの判断材料を誤る | 表 | 317 | 4,077 |

`.agents/skills/pr-review-fix-loop/tests/test_loop_check_options.py`（`pr-review-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 255 | `test_check_options_reports_the_options_start_would_record` | 1 | 21 | 前検査と start の担当・設定が食い違い、別の担当で気付かず実行する。 | 表 | 318 | 4,098 |

`.agents/skills/pr-review-fix-loop/tests/test_loop_diagnostics.py`（`pr-review-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 256 | `test_cause_uses_only_failure_channels` | 4 | 35 | モデル本文を実際の失敗として分類し、誤った原因を永続診断に保存する。 | 表 | 322 | 4,133 |
| 257 | `test_response_extraction_is_decided_from_the_end_state` | 4 | 31 | runner や adapter の終了状態と食い違う応答抽出失敗を永続診断に保存し、復旧判断を誤らせる。 | 表 | 326 | 4,164 |
| 258 | `test_reported_failures_are_not_response_extraction` | 2 | 27 | pi が報告した提供元の失敗を応答抽出失敗と誤記録する。 | 表 | 328 | 4,191 |
| 259 | `test_recovered_failures_do_not_decide_the_cause` | 4 | 60 | 回復した一時的エラーを最終原因として保存する。 | 表 | 332 | 4,251 |
| 260 | `test_unobservable_logs_are_not_response_extraction` | 1 | 13 | 部分取得のログだけで応答抽出失敗と誤判定し、復旧判断を誤らせる。 | 表 | 333 | 4,264 |
| 261 | `test_final_pi_failure_survives_a_long_history` | 2 | 39 | 長い履歴で最後の失敗を見失い、誤原因を保存する（実発生 #237 の再発）。 | 表 | 335 | 4,303 |
| 262 | `test_model_prose_stdout_never_decides_the_cause` | 4 | 55 | Devin のコード例やモデル本文を実失敗として扱い、誤原因を保存する。 | 表 | 339 | 4,358 |
| 263 | `test_keep_diagnostic_covers_only_reviewers_with_a_failure` | 3 | 49 | 失敗した試行の診断を保存し忘れ、ログ回収後に根拠を失う。 | 表 | 342 | 4,407 |
| 264 | `test_different_failures_leave_distinct_causes_after_cleanup` | 1 | 38 | ログ回収後に別々の失敗を同じ原因として記録する。 | 表 | 343 | 4,445 |
| 265 | `test_review_reads_stdout_by_the_reviewer_runtime` | 1 | 11 | レビュアーの runtime を取り違え、失敗の原因を誤記録する。 | 表 | 344 | 4,456 |
| 266 | `test_rerun_keeps_a_diagnostic_for_each_request` | 1 | 16 | 再実行が最初の失敗記録を上書きして調査履歴を失う。 | 表 | 345 | 4,472 |
| 267 | `test_all_failed_review_returns_the_diagnostics_to_the_controller` | 1 | 34 | 全員失敗時に診断の保存先や保存失敗を司令塔へ返さず、残存資源と原因を見失う。 | 表 | 346 | 4,506 |

`.agents/skills/pr-review-fix-loop/tests/test_loop_review.py`（`pr-review-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 268 | `test_reviewers_receive_the_previous_round_when_the_head_moved` | 1 | 41 | 前回の判断履歴をレビュアーへ渡さず、同じ指摘を取り違える。 | 表 | 347 | 4,547 |
| 269 | `test_cycle_end_reads_the_roles_json_that_run_roles_writes` | 1 | 57 | 実際の担当と違う担当を判断の記録に保存する。 | 表 | 348 | 4,604 |
| 270 | `test_failed_cleanup_paths_are_reported` | 1 | 19 | 回収できなかったパスを報告せず、残存資源を見失う。 | 表 | 349 | 4,623 |
| 271 | `test_reviewer_rejected_after_runner_success_is_rerun_once` | 1 | 30 | 保存に失敗した担当を未実施のまま指摘なし扱いにする。 | 表 | 350 | 4,653 |

`.agents/skills/pr-review-fix-loop/tests/test_loop_state.py`（`pr-review-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 272 | `test_start_accepts_fix_assignments_that_run_roles_accepts` | 2 | 23 | 有効な設定を誤った担当に置き換えて起動する。 | 表 | 352 | 4,676 |
| 273 | `test_start_records_options_and_effective_assignments` | 1 | 25 | CLI が担当指定を渡さず、run.json と計画に別の担当を記録する。 | 表 | 353 | 4,701 |
| 274 | `test_inherited_skip_changed_without_evidence_is_rejected` | 1 | 37 | 引き継いだ判断を根拠なしに変更し、判断履歴を誤記録する。 | 表 | 354 | 4,738 |

`.agents/skills/pr-review/tests/test_port_routing.py`（`pr-review-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 275 | `test_ref_delete_failure_keeps_a_retryable_session` | 1 | 17 | ref の削除に失敗した後、所有 session と回収の手掛かりを失う。 | 表 | 355 | 4,755 |
| 276 | `test_failed_shallow_create_can_be_inspected_then_abandoned` | 1 | 27 | 浅い checkout の create 失敗後に、所有 session と回収の手掛かりを失う。 | 表 | 356 | 4,782 |

`.agents/skills/pr-review/tests/test_pr_review_workspace.py`（`pr-review-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 277 | `test_create_reports_legacy_review_without_adopting_it` | 1 | 18 | 旧配置のレビューを別リポジトリの前回結果として黙って採用・移動する。 | 表 | 357 | 4,800 |
| 278 | `test_save_with_findings_saves_the_review_and_the_candidates` | 1 | 11 | レビューと候補一覧の対の保存が崩れ、不完全なレビュー成果を正式保存する。 | 表 | 358 | 4,811 |
| 279 | `test_save_with_invalid_findings_saves_nothing` | 5 | 24 | 不整合な候補一覧（別 HEAD・別 PR・別 review_file・本文と不一致・Markdown 由来）を正式保存する。 | 表 | 363 | 4,835 |
| 280 | `test_save_with_findings_restores_the_candidates_when_the_review_copy_fails` | 1 | 21 | 本文の保存失敗時に既存の候補一覧を元に戻さず、古い・不完全な成果を正式保存したままにする。 | 表 | 364 | 4,856 |
| 281 | `test_save_with_findings_removes_new_candidates_when_the_review_copy_fails` | 1 | 18 | 本文の保存失敗時に新しく作った候補一覧を消さず、本文の無い候補一覧を正式保存したままにする。 | 表・重さは #236 | 365 | 4,874 |
| 282 | `test_findings_destination_must_stay_under_the_review_findings_directory` | 5 | 16 | 候補一覧の書込先が findings・reviews・該当 repository の外へ出て、別 PR・HEAD の候補一覧などを正式保存する。 | 表 | 370 | 4,890 |
| 283 | `test_save_without_findings_removes_the_stale_candidates_of_the_same_head` | 1 | 18 | 同じ HEAD を本文だけで保存し直したとき、古い候補一覧を残して review-verify に読ませる。 | 表 | 371 | 4,908 |
| 284 | `test_findings_draft_cannot_escape_the_session_via_symlink` | 1 | 11 | 候補一覧の draft が symlink で session 外のファイルを指しても保存し、別の候補一覧を正式保存する。 | 表 | 372 | 4,919 |
| 285 | `test_findings_paths_require_repository_identity` | 2 | 8 | repository を持たない旧配置の候補一覧パスを書込先にし、別 PR・HEAD の候補一覧などを正式保存する。 | 表 | 374 | 4,927 |

`.agents/skills/pr-review/tests/test_review_run.py`（`pr-review-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 286 | `test_complete_saves_zero_findings_with_provenance` | 1 | 25 | 指摘 0 件の完了で、来歴・状態を誤って報告または上書きする。 | 表 | 375 | 4,952 |
| 287 | `test_complete_preserves_failure_as_failed_result` | 5 | 49 | complete の失敗（binding・reviewer・coverage・destination・head）を成功と報告する、または記録を上書きする。 | 表 | 380 | 5,001 |
| 288 | `test_prepare_nonrunner_marks_unobserved_identity_unknown` | 1 | 20 | runner でない起動で、観測していない識別（provider・effort・cli_version）を unknown と記録せず誤報告する。 | 表 | 381 | 5,021 |
| 289 | `test_complete_reports_saved_but_uncleaned_result_as_failure` | 1 | 24 | 保存済みで回収に失敗した結果を成功と報告し、記録を誤る。 | 表 | 382 | 5,045 |
| 290 | `test_prepare_base_fetch_failure_returns_correlated_retained_paths` | 1 | 20 | base fetch 失敗時に、残存パスを要求と対応させて返さず、失敗の状態を誤って報告する。 | 表 | 383 | 5,065 |
| 291 | `test_prepare_pi_requires_both_current_environment_identifiers` | 1 | 9 | pi の環境識別子（PI_MODEL・PI_PROVIDER）の片方だけで、実行記録の識別を誤って記録する。 | 表 | 384 | 5,074 |
| 292 | `test_success_record_matches_saved_outputs_and_candidates` | 1 | 56 | 実行記録の成功が保存した出力・候補と食い違い、識別・状態を誤って報告する。 | 表 | 385 | 5,130 |
| 293 | `test_second_review_records_update_mode_and_previous_digest` | 1 | 13 | 2 回目のレビューの mode と前回レビューの digest を誤記録する。 | 表 | 386 | 5,143 |
| 294 | `test_prepare_without_request_records_null_request` | 1 | 6 | request なしの実行で、存在しない run の来歴（inputs.request・run_id）を誤って記録する。 | 表・重さは #236 | 387 | 5,149 |
| 295 | `test_prepare_alone_leaves_started_record_like_a_killed_run` | 1 | 11 | prepare だけで kill された実行が started の記録を残さず、状態を誤って報告する。 | 表 | 388 | 5,160 |
| 296 | `test_prepare_failure_before_resolve_writes_no_record` | 1 | 7 | model 不明で resolve より前に失敗した実行の、ghost の started 記録を残す。 | 表・重さは #236 | 389 | 5,167 |
| 297 | `test_prepare_failure_after_resolve_records_prepare` | 1 | 21 | resolve 後の prepare 失敗を、失敗段階（prepare）つきで記録せず誤って報告する。 | 表 | 390 | 5,188 |
| 298 | `test_prepare_failure_is_kept_when_the_model_later_calls_fail` | 1 | 27 | prepare で記録済みの失敗原因・段階を、後続の fail が上書きする。 | 表・重さは #236 | 391 | 5,215 |
| 299 | `test_fail_request_returns_without_blocking_and_preserves_failure_record` | 2 | 36 | 不正な request の fail で、準備済みの実行記録や失敗の記録を上書きする。 | 表 | 393 | 5,251 |
| 300 | `test_model_fail_records_review` | 1 | 29 | モデルの fail を review 段階の失敗として記録せず、状態・失敗を誤って報告する。 | 表 | 394 | 5,280 |
| 301 | `test_save_failure_records_save` | 1 | 14 | save 段階の失敗を記録せず、状態・失敗を誤って報告する。 | 表 | 395 | 5,294 |
| 302 | `test_record_update_failure_does_not_change_the_review_result` | 1 | 17 | 実行記録の更新失敗がレビュー結果を失敗に変え、結果を誤って報告する。 | 表 | 396 | 5,311 |
| 303 | `test_attach_runner_writes_the_runner_block_once_and_keeps_provenance` | 1 | 35 | runner の観測値を二重に書く、または来歴を上書きする。 | 表 | 397 | 5,346 |
| 304 | `test_attach_runner_rejects_conflicting_values_without_writing` | 1 | 17 | 矛盾する runner の観測値で、実行記録を上書きして誤る。 | 表 | 398 | 5,363 |
| 305 | `test_attach_runner_reports_attempts_without_a_record` | 1 | 19 | 実行記録の無い試行を報告せず、または別の記録に付ける。 | 表 | 399 | 5,382 |
| 306 | `test_attach_runner_marks_a_timed_out_attempt_on_the_started_record` | 1 | 13 | タイムアウトした試行の状態を started 記録に付けず、状態を誤って報告する。 | 表 | 400 | 5,395 |
| 307 | `test_record_outputs_failure_after_save_keeps_the_review_result` | 1 | 15 | outputs_document の失敗時に、出力を特定できない実行記録を success と誤記録する。 | 表・重さは #236 | 401 | 5,410 |
| 308 | `test_prepare_returns_skip_decisions_through_ordinary_comments` | 1 | 70 | 共有 parser を通さず、以前受理した skip の判断を黙って捨て、記録を取り違える。 | 表 | 402 | 5,480 |
| 309 | `test_prepare_create_failure_reports_owned_session_retained_paths` | 1 | 27 | session.json の作成前に失敗しても、登録済みの worktree を残存パスに報告せず、失敗を誤って報告する。 | 表 | 403 | 5,507 |

`.agents/scripts/tests/test_agent_tmp.py`（`review-helper-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 310 | `test_cli_root_from_every_cwd` | 1 | 17 | cwd によって親と違う場所に記録を残す（別の場所に記録） | 表 | 404 | 5,524 |

`.agents/scripts/tests/test_review_findings.py`（`review-helper-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 311 | `test_v2_input_and_accuracy_cannot_claim_different_sessions` | 1 | 5 | 入力と accuracy が別セッションを名乗る取り違えを黙って通す | 表 | 405 | 5,529 |
| 312 | `test_v2_source_must_resolve_to_an_input_file` | 1 | 5 | 出所の参照先が入力ファイルに解決しない取り違えを黙って通す | 表 | 406 | 5,534 |
| 313 | `test_statement_candidates_section_is_required_only_for_fix_check` | 1 | 7 | fix_check の条件判定の節が無くても通る（判定漏れ） | 表 | 407 | 5,541 |
| 314 | `test_check_statement_judgments_accepts_a_complete_judgment` | 1 | 3 | 判定漏れ・別 head の一覧・不整合の見落としを防ぐ群のうち、完全な判定を通す側 | 表 | 408 | 5,544 |
| 315 | `test_check_statement_judgments_reports_an_unjudged_candidate` | 1 | 6 | 候補の判定漏れを見落として通す | 表 | 409 | 5,550 |
| 316 | `test_check_statement_judgments_reports_unknown_and_repeated_ids` | 1 | 6 | 知らない ID・重複した ID の判定を見落として通す（不整合の見落とし） | 表 | 410 | 5,556 |
| 317 | `test_check_statement_judgments_reports_a_different_to` | 1 | 4 | 別の head（to）で作った候補一覧で判定を通す | 表 | 411 | 5,560 |
| 318 | `test_check_statement_judgments_reports_a_different_from` | 1 | 4 | 別の base（from）で作った候補一覧で判定を通す（別の範囲の一覧との取り違え） | 表 | 412 | 5,564 |
| 319 | `test_check_statement_judgments_requires_inconsistent_sites_in_findings` | 1 | 5 | 条件の不整合の箇所を findings に書かないまま通す（不整合の見落とし） | 表 | 413 | 5,569 |
| 320 | `test_cli_validate_checks_the_fix_check_against_its_candidates` | 1 | 12 | CLI が候補一覧との突き合わせを呼ばず、判定漏れを通す | 表 | 414 | 5,581 |
| 321 | `test_invalid_documents_name_the_problem` の `candidates-mutate-findings[0].failure_scenario: required`・`verified-mutate-findings[0].reproduction: required when verdict is`・`fix_check-mutate-fix_check: required when mode is fix_check`・`fix_check-mutate-fix_check.to: must equal reviewed_head` | 4 | 18（関数 18 を含む） | failure_scenario・reproduction・fix_check の必須欄の欠落、fix_check.to の取り違えを通す | 表 | 418 | 5,599 |
| 322 | `test_unverified_verdict_requires_missing_checks` | 1 | 6 | unverified の理由（missing_checks）の欠落を通す | 表 | 419 | 5,605 |
| 323 | `test_duplicate_ids_are_rejected` | 1 | 4 | 指摘 ID の重複で記録を取り違える | 表 | 420 | 5,609 |
| 324 | `test_control_characters_are_rejected_in_text` | 1 | 4 | 制御文字の混入（偽装）を通す | 表 | 421 | 5,613 |
| 325 | `test_parse_review_markdown_reads_active_findings_and_unverified_candidates` | 1 | 13 | コードブロック内の見出し・決定済みの節を数え、指摘を取り違える | 表 | 422 | 5,626 |
| 326 | `test_candidates_from_markdown_is_a_valid_markdown_source_document` | 1 | 16 | Markdown から作る候補の変換結果を取り違える | 表 | 423 | 5,642 |
| 327 | `test_check_pair_names_each_mismatch` | 5 | 16 | Markdown と JSON の指摘の欠落・余分・severity 差・位置の移動・未確認候補の欠落を見逃す | 表 | 428 | 5,658 |
| 328 | `test_provenance_stats_does_not_apply_other_pr_or_head_decisions` | 1 | 17 | 別の PR・head の採否を適用し、採用を取り違える | 表 | 429 | 5,675 |
| 329 | `test_v2_model_identity_cannot_contain_a_line_break` | 1 | 6 | model への改行で識別子を偽装する | 表 | 430 | 5,681 |
| 330 | `test_cli_from_markdown_and_check_pair` | 1 | 30 | check-pair の不一致が終了コード 65 にならず、取り違えが通る | 表 | 431 | 5,711 |
| 331 | `test_review_run_rejects_inconsistent_fields` | 4 | 16 | success に outputs 無し・started に finished_at・by_severity の合計違い・時刻の逆転の記録を通す | 表 | 435 | 5,727 |
| 332 | `test_from_markdown_refuses_findings_it_cannot_read` | 5 | 24 | 読めない指摘を黙って落とす（最終レビュー I-1 の再発防止） | 表 | 440 | 5,751 |
| 333 | `test_check_pair_refuses_unverified_candidates_it_cannot_read` | 1 | 8 | 読めない未確認候補を取りこぼして通す | 表 | 441 | 5,759 |
| 334 | `test_statement_candidates_lists_documents_naming_the_enclosing_state` | 1 | 21 | 修正で変わった条件を述べる文書を候補から落とす（見落とし） | 表 | 442 | 5,780 |
| 335 | `test_statement_candidates_handles_deleted_files` | 1 | 8 | 削除したファイルの候補を黙って落とす | 表 | 443 | 5,788 |
| 336 | `test_cli_statement_candidates_writes_the_file` | 1 | 16 | 候補の出力ファイルを書かない | 表 | 444 | 5,804 |
| 337 | `test_cli_statement_candidates_rejects_an_unknown_revision` | 1 | 15 | 失敗したとき、既存の出力を上書きする | 表 | 445 | 5,819 |
| 338 | `test_statement_candidates_handles_non_ascii_paths` | 1 | 9 | 日本語パスの候補を黙って落とす、または誤ったパスにする | 表 | 446 | 5,828 |
| 339 | `test_statement_candidates_lists_documents_for_a_template_only_change` | 1 | 21 | テンプレートだけの変更で文書を見落とす（実際に起きた見落とし、Issue #620・#555） | 表 | 447 | 5,849 |
| 340 | `test_statement_candidates_reads_kebab_case_names` | 1 | 23 | kebab-case の名前を語として読まず、文書を見落とす（実際に起きた見落とし、Issue #620・#555） | 表 | 448 | 5,872 |
| 341 | `test_fix_evidence_requires_every_claim_and_changed_file` | 2 | 6 | 主張・変更ファイルの判定漏れを通す | 表 | 450 | 5,878 |
| 342 | `test_fix_evidence_rejects_duplicate_judgments` | 1 | 6 | 同じ主張への判定の重複を通す | 表 | 451 | 5,884 |
| 343 | `test_fix_evidence_rejects_malformed_execution` | 2 | 6 | 別 head の証拠・assumed の実行を証拠として通す | 表 | 453 | 5,890 |
| 344 | `test_artifact_claim_requires_executed_generated_evidence` | 3 | 6 | static・exit_code≠0・artifact なしの証拠で、生成物の主張を holds と記録する | 表 | 456 | 5,896 |
| 345 | `test_unchecked_evidence_requires_remaining_coverage` | 1 | 8 | 未確認の証拠を remaining に書かないまま通す | 表 | 457 | 5,904 |
| 346 | `test_failed_evidence_requires_confirmed_finding` | 1 | 8 | 違反した証拠を confirmed の指摘にしないまま通す | 表 | 458 | 5,912 |
| 347 | `test_evidence_inventory_cannot_omit_a_fix_or_reuse_a_claim_id` | 1 | 9 | fix の主張漏れ・claim ID の再利用を通す | 表 | 459 | 5,921 |
| 348 | `test_v2_fix_check_requires_evidence_without_breaking_legacy` | 1 | 14 | v2 の fix_check で fix_evidence を求めず、証拠なしで通す | 表 | 460 | 5,935 |
| 349 | `test_claim_inventory_lists_all_changed_paths_including_rename_and_deletion` | 1 | 36 | 改名・削除したパスを検査対象から落とす | 表 | 461 | 5,971 |
| 350 | `test_v2_document_accepts_observed_identity_and_real_activities`（正しく通る例） | 3 | 4 | 対の守り: v2 の取り違え・偽装の拒否が、正しい v2 の文書を拒否しない | 表・重さは #236 | 464 | 5,975 |
| 351 | `test_valid_documents_pass`（正しく通る例） | 5 | 4 | 対の守り: 文書の検証が、正しい v1 の文書を拒否しない（拒否側は欠落・取り違え） | 表・重さは #236 | 469 | 5,979 |
| 352 | `test_failure_scenario_is_optional_for_documentation_findings`（正しく通る例） | 1 | 6 | 対の守り: failure_scenario 必須の検査が、文書の指摘まで拒否しない | 表・重さは #236 | 470 | 5,985 |
| 353 | `test_check_pair_accepts_a_matching_pair`（正しく通る例） | 1 | 2 | 対の守り: Markdown と JSON の組の検査が、一致する組を拒否しない | 表・重さは #236 | 471 | 5,987 |
| 354 | `test_review_run_accepts_each_status`（正しく通る例） | 5 | 6 | 対の守り: 実行記録の検査が、正しい状態の記録を拒否しない（拒否側は矛盾した記録） | 表・重さは #236 | 476 | 5,993 |
| 355 | `test_from_markdown_still_reads_coverage_subsections_and_matching_summaries`（正しく通る例） | 1 | 10 | 対の守り: 読めない指摘の拒否が、Coverage の小節・一致する Summary の Markdown まで拒否しない | 表・重さは #236 | 477 | 6,003 |
| 356 | `test_from_markdown_reads_an_unverified_section_that_says_none`（正しく通る例） | 2 | 14 | 対の守り: 読めない未確認候補の拒否が、「なし」と書いた未確認の節を拒否しない | 表・重さは #236 | 479 | 6,017 |
| 357 | `test_fix_evidence_accepts_executed_artifact_and_deleted_file`（正しく通る例） | 1 | 2 | 対の守り: fix の証拠の検査が、実行した生成物・削除したファイルの正しい証拠を拒否しない | 表・重さは #236 | 480 | 6,019 |

`.agents/scripts/tests/test_review_records.py`（`review-helper-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 358 | `test_invalid_records_are_rejected` の `agent-id-not-derived-from-model`・`rerun-disagrees-with-heads`・`changed-without-previous-state`・`reopened-skip-without-new-evidence`・`skip-without-revisit-condition`・`comment-marker-in-text`・`planner-d1-without-reproduction`・`duplicate-decision-id`・`source-shared-across-bases`・`commit-equal-to-reviewed`・`pushed-without-fix`・`no-fix-needed-with-fix` | 12 | 0 | 決定記録の整合（agent_id・rerun と head・skip・changed・d1・重複 ID・source・fix・マーカー）を欠く記録を通す | 表 | 492 | 6,019 |
| 359 | `test_agent_id_for_follows_the_marker_rule` | 2 | 9 | 計画者の同一性（1 サイクル 1 計画者）の基準になる agent_id の導出を誤る | 表 | 494 | 6,028 |
| 360 | `test_fold_keeps_the_latest_state_merged_sources_and_planner_models` | 1 | 30 | 状態の取り違え（最新の状態・source の統合・計画者の履歴） | 表 | 495 | 6,058 |
| 361 | `test_fold_orders_one_round_by_time_and_then_comment_id` | 1 | 11 | 古い記録で新しい状態を上書きする | 表 | 496 | 6,069 |
| 362 | `test_fold_keeps_split_decisions_apart` | 1 | 8 | 分割した decision の判断を取り違える | 表 | 497 | 6,077 |
| 363 | `test_fold_rejects_records_of_another_pull_request` | 1 | 8 | 別の PR の記録を混ぜる | 表 | 498 | 6,085 |
| 364 | `test_check_against_rejects_inconsistent_rounds` | 7 | 6 | 記録済みの new・state 変更・サイクル番号の飛び・別 PR・前の fix の脱落・skip 参照の付け替えを通す | 表 | 505 | 6,091 |
| 365 | `test_check_against_keeps_one_planner_per_round` | 1 | 13 | 1 サイクル 1 計画者を守らず、記録を上書きする | 表 | 506 | 6,104 |
| 366 | `test_check_against_refuses_to_update_a_round_after_a_later_one` | 1 | 6 | 後のサイクルがあるのに古いサイクルの記録を更新し、上書きする | 表 | 507 | 6,110 |
| 367 | `test_check_against_rejects_finishing_with_an_earlier_hold` | 1 | 13 | 前の hold を残したまま完了と報告する | 表 | 508 | 6,123 |
| 368 | `test_check_against_keeps_a_reference_with_the_part_that_holds_it` | 1 | 13 | 分割後の参照を、別の指摘を保つ部分から切り離して付け替える（記録の取り違え） | 表 | 509 | 6,136 |
| 369 | `test_stopped_round_requires_a_concrete_allowed_category` | 6 | 8 | 区分（permission・environment・external）や具体的な理由の無い停止を記録しても気付けない | 表 | 515 | 6,144 |
| 370 | `test_comments_from_api_accepts_slurped_pages_and_flat_arrays` | 1 | 7 | gh の応答の形を読み違え、記録が 0 件になる | 表 | 516 | 6,151 |
| 371 | `test_collect_records_accepts_explicit_trusted_login` | 1 | 7 | CONTRIBUTOR の投稿を読まず、記録が消える（#169） | 表 | 517 | 6,158 |
| 372 | `test_trusted_login_keeps_association_trust` | 1 | 8 | trusted_login を指定すると権限による信頼を保たず、記録を読み落とす | 表 | 518 | 6,166 |
| 373 | `test_collect_records_names_every_broken_comment` | 1 | 12 | 壊れた記録のコメントを黙って飛ばし、記録を失う | 表 | 519 | 6,178 |
| 374 | `test_read_state_lists_ignored_comments_and_checks_the_pull_request` | 1 | 10 | 無視したコメントを一覧に出さず、別の PR の記録を読む | 表 | 520 | 6,188 |
| 375 | `test_updating_the_same_round_excludes_its_own_comment` | 1 | 9 | 更新時に自分のコメントを除かず、「記録済み」と拒否する／重複する | 表 | 521 | 6,197 |
| 376 | `test_cli_fold_prints_the_current_state` | 1 | 15 | CLI の入出力のつなぎを誤り、現在の状態を出さない | 表 | 522 | 6,212 |
| 377 | `test_cli_fold_reports_records_of_another_pull_request` | 1 | 7 | --repo/--pr の配線が切れ、別 PR の記録を混ぜる | 表 | 523 | 6,219 |
| 378 | `test_cli_fold_exits_65_on_a_broken_record` | 1 | 8 | 壊れた記録を成功（終了 0）と報告する | 表 | 524 | 6,227 |
| 379 | `test_cli_fold_uses_explicit_trusted_login` | 2 | 17 | --trusted-login の配線が切れ、信頼する投稿者を取り違える | 表 | 526 | 6,244 |
| 380 | `test_cli_validate_uses_explicit_trusted_login` | 1 | 9 | validate の --trusted-login の配線が切れる | 表 | 527 | 6,253 |
| 381 | `test_cli_validate_checks_the_record_against_earlier_comments` | 1 | 22 | 更新時の前のコメントとの照合と --exclude-comment を誤る | 表 | 528 | 6,275 |
| 382 | `test_check_against_accepts_the_next_round`（正しく通る例） | 1 | 2 | 対の守り: サイクルの整合の検査が、正しい次のサイクルを拒否しない（拒否側は記録の上書き・脱落） | 表・重さは #236 | 529 | 6,277 |

`.agents/scripts/tests/test_review_target.py`（`review-helper-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 383 | `test_resolve_fork_and_upstream_use_separate_directories_and_remotes` | 1 | 12 | fork と上流のディレクトリ・remote を取り違える | 表 | 530 | 6,289 |
| 384 | `test_find_review_directory_does_not_cross_repositories` | 1 | 11 | fork と上流で番号が同じでも、別リポジトリのレビューを選ぶ | 表 | 531 | 6,300 |
| 385 | `test_find_review_directory_lists_multiple_candidates` | 1 | 10 | 複数候補のとき、止まらずに任意の 1 件を選ぶ | 表 | 532 | 6,310 |
| 386 | `test_find_review_directory_ignores_symlinks_and_other_names` | 1 | 12 | symlink 先の別ディレクトリを使う | 表 | 533 | 6,322 |
| 387 | `test_legacy_fork_checkout_directory_is_ambiguous` | 1 | 13 | 旧配置の fork checkout で、fork と上流を推測で選ぶ | 表 | 534 | 6,335 |
| 388 | `test_legacy_fork_checkout_directory_rejects_findings_of_another_repository` | 1 | 9 | 旧配置で別リポジトリの findings を受け入れ、別の PR のレビューを使う | 表 | 535 | 6,344 |
| 389 | `test_pr_option_must_match_path` | 1 | 17 | --pr とパスの不一致を通し、別 PR のレビューを使う（正例つき） | 表 | 536 | 6,361 |
| 390 | `test_checkout_layout_must_match_target_root` | 1 | 20 | 別の checkout を対象にする（正例つき） | 表 | 537 | 6,381 |
| 391 | `test_find_review_directory_rejects_name_mismatch` | 1 | 8 | ディレクトリ名と head branch の不一致を通し、古い branch 名のレビューを使う | 表 | 538 | 6,389 |
| 392 | `test_find_review_directory_rejects_findings_for_another_pr` | 1 | 9 | 別 PR の findings を受け入れる | 表 | 539 | 6,398 |
| 393 | `test_fetch_pull_head_separates_fork_and_upstream` | 1 | 12 | fork と上流の保存先 ref を取り違える | 表 | 540 | 6,410 |
| 394 | `test_find_review_directory_by_number`（正しく通る例） | 1 | 8 | 対の守り: 番号でレビュー dir を探せる（拒否側は別リポジトリ・別 PR・symlink の取り違え） | 表 | 541 | 6,418 |
| 395 | `test_find_review_directory_from_findings_json`（正しく通る例） | 1 | 10 | 対の守り: findings から PR を識別できる（拒否側は別 PR の findings） | 表 | 542 | 6,428 |

`.agents/skills/review-fix-planning/tests/test_finalize.py`（`review-helper-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 396 | `test_public_ci_still_running_waits_and_the_rerun_finalizes` | 1 | 14 | CI が実行中のときの待機と、待機後の再実行での完了を誤る | 表 | 543 | 6,442 |
| 397 | `test_wait_after_post_reruns_by_updating_the_same_comment` | 1 | 15 | 再実行で状況コメントを重複投稿する | 表 | 544 | 6,457 |
| 398 | `test_already_merged_with_this_record_posted_only_resumes_issue_updates` | 1 | 5 | マージ済みの再実行で、Issue 更新を再開しない | 表 | 545 | 6,462 |
| 399 | `test_merged_without_this_no_fix_record_is_stopped_but_merged` | 2 | 16 | この記録なしでマージ済みの PR を、完了または未マージと取り違えて報告する | 表 | 547 | 6,478 |
| 400 | `test_manual_merge_after_a_stop_before_posting_is_not_no_fix_needed` | 1 | 16 | 停止後の手動マージを no_fix_needed の完了と報告する | 表 | 548 | 6,494 |
| 401 | `test_issue_update_failure_is_reported_after_real_merge` | 1 | 6 | マージ後の Issue 更新の失敗を成功と報告する | 表 | 549 | 6,500 |
| 402 | `test_cli_saves_and_reports_actual_result` | 1 | 13 | 結果ファイルと報告が食い違う | 表 | 550 | 6,513 |
| 403 | `test_cli_exits_one_and_saves_the_result_when_stopped` | 1 | 13 | 停止時の終了コード 1 と結果の保存を誤り、停止を成功と扱う | 表 | 551 | 6,526 |
| 404 | `test_post_operation_save_failure_preserves_observed_effects_in_stdout` | 1 | 19 | 結果の保存に失敗したとき、マージ済みの事実を出力に残さない | 表 | 552 | 6,545 |
| 405 | `test_conflict_with_earlier_records_is_environment_and_names_the_decision` | 1 | 11 | 過去の記録と衝突したまま記録を書く | 表 | 553 | 6,556 |
| 406 | `test_login_failure_is_external_and_does_not_post_or_merge` | 2 | 14 | 認証済みの login を取れないまま投稿・マージする | 表 | 555 | 6,570 |
| 407 | `test_merged_with_another_head_keeps_the_merge` | 1 | 17 | 別の head でマージ済みの PR を未マージと報告し、マージ済みの事実を失う | 表 | 556 | 6,587 |
| 408 | `test_manual_merge_with_another_head_after_posting_keeps_the_merge` | 1 | 8 | 投稿後に別の head で手動マージされたのに、マージ済みの事実を失う（#207） | 表 | 557 | 6,595 |
| 409 | `test_manual_merge_before_posting_keeps_the_merge` | 1 | 9 | 投稿前の手動マージを未マージと報告し、マージ済みの事実を失う（#207） | 表 | 558 | 6,604 |
| 410 | `test_failed_confirmation_after_the_merge_is_unconfirmed_and_the_rerun_recovers` | 1 | 13 | マージ後の確認の失敗を未マージと言い、再実行で完了しない | 表 | 559 | 6,617 |
| 411 | `test_failed_merge_request_is_unconfirmed_and_the_rerun_recovers` | 1 | 10 | マージ要求の失敗を未マージと断定し、再実行で完了しない | 表 | 560 | 6,627 |

`.agents/skills/review-fix-planning/tests/test_review_fix_planning_skill_contract.py`（`review-helper-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 412 | `test_fix_initial_planning_does_not_confuse_pr_branch_metadata_with_head_validation` | 1 | 4 | PR の branch の情報と HEAD の検証を取り違える | 表 | 561 | 6,631 |

`.agents/skills/review-fix-planning/tests/test_run_roles.py`（`review-helper-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 413 | `test_single_call_uses_both_review_roles_and_retains_self_instructions` | 2 | 39 | 1 回枠の予約・記録・accept の拒否を誤る | 表 | 563 | 6,670 |
| 414 | `test_verified_input_mismatch_never_consumes_the_only_review` | 2 | 13 | 別 PR・別 HEAD の verified を受けて、1 回だけの枠を消費する | 表 | 565 | 6,683 |
| 415 | `test_second_review_is_refused_even_when_all_assignments_are_self` | 1 | 5 | 1 回枠の再予約を許し、記録を上書きする | 表 | 566 | 6,688 |
| 416 | `test_binding_mismatch_is_rejected_before_reservation` | 1 | 5 | planning と PR の不一致のまま枠を予約する | 表 | 567 | 6,693 |
| 417 | `test_review_assignment_that_cannot_run_the_helpers_stops_before_reserving_the_review` | 1 | 29 | helper を動かせない担当（codex の fallback）で、戻せない 1 回枠を消費する（#731） | 表 | 568 | 6,722 |
| 418 | `test_unconfirmed_stop_blocks_fix_check_accept_and_keeps_budget` | 1 | 16 | 停止未確認のまま fix-check を成功と報告する | 表 | 569 | 6,738 |

`.agents/skills/review-fix-planning/tests/test_upsert_pr_comment.py`（`review-helper-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 419 | `test_record_less_body_rejects_round_markers_and_records_blocks` | 2 | 14 | 記録なしの本文から round マーカー・記録ブロックを偽造できる | 表 | 571 | 6,752 |
| 420 | `test_find_own_comment_ignores_other_agents_and_rejects_duplicates` | 1 | 10 | 別担当のコメントを書き換える | 表 | 572 | 6,762 |
| 421 | `test_find_own_comment_matches_the_marker_as_a_whole_first_line` | 1 | 12 | 引用した marker のコメントを自分のものとして書き換える | 表 | 573 | 6,774 |
| 422 | `test_find_round_comment_matches_both_marker_lines_exactly` | 1 | 14 | 別サイクルの記録のコメントを上書きする | 表 | 574 | 6,788 |
| 423 | `test_comments_are_read_from_every_slurped_page` | 1 | 8 | 全ページを読まず、既存コメントを見落として重複する | 表 | 575 | 6,796 |
| 424 | `test_login_failure_stops_before_any_comment_write` | 2 | 7 | login が不明なままコメントを書き込む | 表 | 577 | 6,803 |
| 425 | `test_records_post_updates_the_same_round_after_the_push` | 1 | 7 | push 後に同じサイクルのコメントを重複させる | 表 | 578 | 6,810 |
| 426 | `test_records_post_reads_prior_round_written_by_own_contributor_login` | 1 | 9 | 自分の login が CONTRIBUTOR で書いた前のサイクルを読まず、履歴を失う（#169） | 表 | 579 | 6,819 |
| 427 | `test_records_post_rejects_a_record_for_another_pull_request` | 1 | 4 | 別 PR の記録を投稿する | 表 | 580 | 6,823 |
| 428 | `test_records_post_requires_the_pull_request_head` | 2 | 9 | 古い HEAD の記録を投稿する | 表 | 582 | 6,832 |
| 429 | `test_records_post_stops_when_a_later_round_exists` | 1 | 4 | 後のサイクルがあるのに、古いサイクルを上書きする | 表 | 583 | 6,836 |
| 430 | `test_records_post_rejects_no_fix_needed_with_pending_decisions` | 1 | 4 | 保留を残したまま no_fix_needed の完了と記録する | 表 | 584 | 6,840 |
| 431 | `test_records_post_stops_on_duplicate_round_comments` | 1 | 4 | サイクルのコメントが重複しているのに、どちらかを書き換える | 表 | 585 | 6,844 |

`.agents/skills/review-verify/tests/test_dispatch.py`（`review-helper-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 432 | `test_external_runs_only_fix_check_and_preserves_observed_identity` | 2 | 23 | 失敗を成功と報告する。観測した identity を記録しない | 表 | 587 | 6,867 |
| 433 | `test_self_fix_check_asks_for_no_write_exceptions` | 1 | 21 | self に書込み例外を与える | 表 | 588 | 6,888 |
| 434 | `test_writing_fix_check_role_is_rejected_before_launch` | 1 | 8 | 書込み可の役割を fix-check に使い、例外なしで書込み担当が走り得る | 表 | 589 | 6,896 |
| 435 | `test_unobserved_identity_is_unknown_not_requested` | 1 | 14 | 要求したモデルを観測値と偽って記録する（記録の取り違え） | 表 | 590 | 6,910 |
| 436 | `test_mutable_revision_is_rejected_before_output` | 1 | 8 | 動く参照（HEAD）を許し、別 commit を検証して成功と報告する | 表 | 591 | 6,918 |
| 437 | `test_explicit_fallback_keeps_the_actual_agent_and_observed_identity` | 1 | 22 | fallback 時に実際の担当を記録しない | 表 | 592 | 6,940 |
| 438 | `test_observed_hash_conflicting_with_the_dispatched_skill_is_unknown` | 1 | 14 | 適用した skill と食い違う観測値を採用する | 表 | 593 | 6,954 |
| 439 | `test_accept_rejects_a_missing_or_malformed_trusted_pr_before_output` | 2 | 20 | 凍結した PR が読めないとき payload へ fallback する、bool を番号と誤認する | 表 | 595 | 6,974 |
| 440 | `test_accept_rejects_a_primary_skill_not_applied_by_dispatch_before_creating_output` | 2 | 26 | 適用していない skill の記録を受理する | 表 | 597 | 7,000 |
| 441 | `test_accept_does_not_attribute_a_disappeared_checkout_to_content_changes` | 1 | 22 | 消えた checkout の監査不能を「内容変更」と取り違える | 表 | 598 | 7,022 |
| 442 | `test_fix_check_environment_preflight_does_not_launch` | 1 | 35 | 移動した checkout で main が environment と報告せず、担当を起動する | 表 | 599 | 7,057 |
| 443 | `test_dispatch_main_exits_1_and_names_outside_changes` | 1 | 11 | 外部書込みで終了コード 0 を返し、汚染された結果を成功と扱う | 表 | 600 | 7,068 |
| 444 | `test_accept_rejects_malformed_checkout_diagnostics` | 1 | 10 | 改ざん・欠落した監査欄を、無変更と読む | 表 | 601 | 7,078 |
| 445 | `test_main_exits_1_for_a_failed_run` | 1 | 8 | 失敗した実行を成功（終了 0）と報告する | 表 | 602 | 7,086 |
| 446 | `test_main_names_the_invalid_request_field_without_its_value` | 1 | 8 | 不正な入力値を stderr に漏らす | 表 | 603 | 7,094 |
| 447 | `test_accept_checks_changes_since_dispatch_even_with_an_invalid_payload` | 1 | 10 | payload が不正なとき、起動後の変更の検出を飛ばす | 表 | 604 | 7,104 |
| 448 | `test_initial_snapshot_cannot_silently_skip_an_unreadable_subdirectory` | 1 | 11 | 読めない subdir を飛ばした不完全な snapshot で、変更を見落とす | 表 | 605 | 7,115 |
| 449 | `test_observed_hash_matching_the_dispatched_skill_is_kept`（正しく通る例） | 1 | 15 | 対の守り: 適用した skill と一致する観測値は残す（拒否側は食い違う観測値の採用） | 表 | 606 | 7,130 |
| 450 | `test_accept_keeps_the_applied_skill_when_identity_was_not_observed`（正しく通る例） | 1 | 23 | 対の守り: 未観測の identity でも適用した skill の記録は受理する（拒否側は適用外の skill） | 表 | 607 | 7,153 |

`.agents/skills/agent-handoff/tests/test_agent_handoff_skill_contract.py`（`skill-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 451 | `test_schema_documents_the_authored_fields` | 1 | 4 | 引き継ぎ schema から decisions・out_of_scope・verification・landing が消え、決定や境界が無言で落ちる | 表 | 608 | 7,157 |
| 452 | `test_schema_maps_review_fix_planning_hold_to_deferred` | 1 | 4 | Hold を Skip 等へ写し、未解決のレビュー指摘が延期記録から黙って消える | 表 | 609 | 7,161 |

`.agents/skills/issue-to-pr/tests/test_implement_task.py`（`skill-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 453 | `test_check_implement_replaces_primary` | 1 | 9 | --implement が別の担当を選び、もっともらしい結果で誤担当の作業を採用する | 表 | 610 | 7,170 |
| 454 | `test_check_rejects_invalid_assignment` | 1 | 25 | 複数の一次担当を受け入れ、意図しない担当を起動・採用する | 表 | 611 | 7,195 |
| 455 | `test_check_reads_the_real_template` | 1 | 10 | 雛形の既定 self が変わり、--implement 無しで有料 runner を黙って起動する | 表 | 612 | 7,205 |
| 456 | `test_exit_code_for_verdicts` | 1 | 3 | rejected・failed・retry を 0 で返し、呼び出し元が失敗を成功として進める | 表 | 613 | 7,208 |

`.agents/skills/issue-to-pr/tests/test_implement_task_run.py`（`skill-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 457 | `test_blocked_asks_for_retry` | 1 | 7 | 作業不能（BLOCKED）の報告を成功・無変更と誤判定して先へ進む | 表 | 614 | 7,215 |
| 458 | `test_non_ascii_paths_and_prompt_round_trip` | 1 | 12 | prompt の内容が静かに欠落・変形し、担当が別の作業をしても許可範囲内なら気付けない | 表 | 615 | 7,227 |
| 459 | `test_cli_accept_and_cleanup_exit_codes` | 1 | 9 | accept が拒否しても CLI が 0 を返し、呼び出し元が取り込み成功として続ける | 表 | 616 | 7,236 |

`.agents/skills/issue-to-pr/tests/test_resolve_issue.py`（`skill-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 460 | `test_merge_arguments_are_passed_in_the_written_order` | 2 | 22 | 値の順序や担当指定を入れ替え、利用者と違う回数・担当でレビュー修正が進む | 表 | 618 | 7,258 |
| 461 | `test_template_and_config_become_absolute_from_the_starting_directory` | 1 | 15 | 後段の cwd で相対パスを解決し、別設定を読んで違う担当を起動する | 表 | 619 | 7,273 |
| 462 | `test_implement_is_returned_without_changing_git` | 2 | 17 | 明示した --implement を別担当・self に取り違え、誤った担当を起動・採用する | 表 | 621 | 7,290 |
| 463 | `test_rejects_malformed_implement_before_looking_up_issue` | 1 | 12 | 二重の --implement から一方を黙って採り、意図しない担当を起動する | 表 | 622 | 7,302 |
| 464 | `test_implement_is_returned_separately_from_loop_args` | 1 | 15 | --assign implement= を Plan Task の担当へ混ぜ、別担当が実装する | 表 | 623 | 7,317 |

`.agents/skills/monitoring-long-tasks/tests/test_task_watch_core.py`（`skill-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 465 | `test_exit_is_completed_only_with_zero_and_declared_result` | 1 | 6 | exit 0 でも宣言済み結果が無い、または非 0 なのに completed と記録し、未完了を成功と報告する | 表 | 624 | 7,323 |
| 466 | `test_safety_failure_precedes_deadline_and_other_reasons` | 1 | 6 | 安全失敗を期限超過などへ置き換え、失敗の種類が最終記録から失われる | 表 | 625 | 7,329 |
| 467 | `test_deadline_stops_even_while_progressing` | 1 | 4 | 進捗があるだけで期限を無視し、宣言した上限を越えて対象が動き続ける | 表 | 626 | 7,333 |
| 468 | `test_repeated_failure_stops_at_the_declared_count` | 1 | 5 | 同じ失敗が所定回数に達しても続行し、失敗を繰り返す対象が期限まで動き続ける | 表 | 627 | 7,338 |
| 469 | `test_no_progress_applies_only_before_research_deadline` | 1 | 8 | 無進捗を見逃して続行するか予約時間に誤って停止し、期限・保存の判断を誤る | 表 | 628 | 7,346 |
| 470 | `test_safety_failure_recorded_before_exit_is_not_completed` | 1 | 6 | 終了コードと結果だけを見て、記録済みの安全失敗を成功と報告する | 表 | 629 | 7,352 |
| 471 | `test_policy_rejects_reserve_that_leaves_no_investigation_time` | 1 | 5 | 予約時間が期限以上の指定を通し、調査不足の成果を completed と記録する | 表 | 630 | 7,357 |
| 472 | `test_progress_reader_counts_only_new_items_and_complete_lines` | 1 | 24 | heartbeat・重複・未完了行を新しい進捗と数え、無進捗の対象を進捗ありとして走らせ続ける | 表 | 631 | 7,381 |
| 473 | `test_failures_are_counted_per_signature_and_first_safety_is_kept` | 1 | 22 | 署名別の失敗回数の混同による誤停止・停止漏れと、安全失敗の先頭記録の喪失 | 表 | 632 | 7,403 |

`.agents/skills/monitoring-long-tasks/tests/test_task_watch_process.py`（`skill-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 474 | `test_heartbeat_only_worker_is_stopped_for_no_progress` | 1 | 10 | heartbeat を実進捗と誤認して worker が走り続ける。停止の確認は実 PID の生存で見る | 表 | 633 | 7,413 |
| 475 | `test_launch_failure_is_reported_as_incomplete` | 1 | 23 | 起動できない CLI を completed と最終報告し、何も実行していないのに成功が残る | 表 | 634 | 7,436 |

`.agents/skills/pi-model-name/tests/test_pi_model_name_contract.py`（`skill-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 476 | `test_strict_fails_closed_without_runtime` | 1 | 5 | runtime 不明なのに履歴から正式なモデル名を推測し、レビュー担当を誤帰属する | 表 | 635 | 7,441 |
| 477 | `test_history_allowed_only_with_flag` | 1 | 15 | 明示 flag なしで履歴を正式なモデル名として返し、古いモデルを現在の担当として記録する | 表 | 636 | 7,456 |
| 478 | `test_history_does_not_fall_back_from_unreadable_explicit_file` | 1 | 8 | 明示したファイルが読めない時に環境側へ無言で fallback し、別 session のモデルを正式に表示する | 表 | 637 | 7,464 |
| 479 | `test_history_invalid_utf8_does_not_supply_a_model` | 1 | 6 | 壊れた session を読み飛ばしてモデルを推測し、誤帰属する | 表 | 638 | 7,470 |
| 480 | `test_runtime_and_selected_conflict_suppresses_text_answer` | 1 | 6 | runtime と選択済みモデルが食い違っても、テキストにモデル名を出して誤った担当を記録する | 表 | 639 | 7,476 |
| 481 | `test_newer_observed_identity_conflicts` | 2 | 11 | 新しい observed の provider/model の不一致を見逃し、実際に応答したモデルを誤帰属する | 表 | 641 | 7,487 |
| 482 | `test_observed_before_model_switch_is_warning` | 1 | 14 | 古い observed を現在のモデルとして採用し、切替後の担当モデルを取り違える | 表 | 642 | 7,501 |
| 483 | `test_crosscheck_ignores_abandoned_branch` | 1 | 14 | 放棄された session 分岐のモデルを採用し、現在の会話と別のモデルを担当として記録する | 表 | 643 | 7,515 |
| 484 | `test_explicit_session_file_precedes_env_sources` | 1 | 9 | 明示ファイルより環境変数を優先し、異なる session のモデルを採用する | 表 | 644 | 7,524 |
| 485 | `test_pi_session_file_precedes_subagent_session` | 1 | 6 | 親 runtime の session より子の session を優先し、子のモデルを親の担当として記録する | 表 | 645 | 7,530 |
| 486 | `test_wrong_session_id_does_not_overrule_runtime_env` | 1 | 14 | session ID が違うファイルを runtime の照合に使い、別実行のモデルで偽の衝突・偽の一致を生む | 表 | 646 | 7,544 |
| 487 | `test_unreadable_session_paths_follow_source_policy` | 1 | 8 | 明示パスが読めないのに暗黙ソースへ fallback し、別 session を照合済みとして扱う | 表 | 647 | 7,552 |
| 488 | `test_crosschecked_text_modes` | 3 | 13 | --model・--provider・--session の値を取り違え、誤った担当を人がそのまま記録する | 表 | 650 | 7,565 |
| 489 | `test_json_without_session_path_reports_unchecked` | 1 | 9 | session が無いのに照合済みのように見せ、未検証のモデルを正式に記録する | 表 | 651 | 7,574 |
| 490 | `test_runtime_env_stays_required_with_explicit_session_file` | 1 | 5 | runtime が無いのに明示 session file の履歴を正式なモデル名として返し、古いモデルを記録する | 表 | 652 | 7,579 |
| 491 | `test_prints_runtime_model`（正しく通る例） | 1 | 4 | fail-closed 拒否の正例。違う provider/model 名を表示するとレビュー記録を誤帰属する | 表 | 653 | 7,583 |
| 492 | `test_history_prefers_explicit_file_over_runtime_file`（正しく通る例） | 1 | 15 | 明示 session と別のファイルから取得し、別の実行のモデルを現在の担当として記録する。fallback 拒否の正例 | 表 | 654 | 7,598 |
| 493 | `test_session_crosscheck_reports_matching_selected_and_observed`（正しく通る例） | 1 | 149（準備 133 を含む） | 照合の衝突判定テスト群の正例。全て conflict と返す実装で、照合済みデータの記録が欠落する | 表 | 655 | 7,747 |

`.agents/skills/repo-cleanup-after-merge/tests/test_detached_update.py`（`skill-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 494 | `test_final_status_from_linked_project_reports_main_not_dirty_caller` | 1 | 29 | caller の dirty 状態を main の状態として報告し、後続の片付け判断を誤る | 表・重さは #236 | 656 | 7,776 |
| 495 | `test_checkout_lock_failure_stops_before_subsequent_branch_deletion` | 1 | 14 | checkout が index.lock で失敗した後、旧 HEAD のまま branch 削除へ進む | 表・重さは #236 | 657 | 7,790 |

`.agents/skills/stale-git-lock-recovery/tests/test_stale_git_lock_recovery_contract.py`（`skill-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 496 | `test_rm_failure_reports_error_without_json` | 1 | 12 | 削除に失敗したのに JSON で成功を返し、残るロックを解消済みと誤報する | 表・重さは #236 | 658 | 7,802 |

`tests/skills/test_skill_packages.py`（`skill-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 497 | `SkillPackageTests::test_provenance_license_and_document_coverage` | 1 | 15 | 凍結した取り込み履歴（出所・改変・出力対応・帰属）が空になっても通常の処理は止まらず、記録を失う | 表・重さは #236 | 659 | 7,817 |

`.devcontainer/test-cleanup-workspace.bash`（`devcontainer-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 498 | 1. dry-run は表示するだけで消さない | 0 | 14 | dry-run が削除してしまい、確認のつもりで /tmp のレビュー用 worktree を消す（誤った対象の削除） | 表 | 659 | 7,831 |

`.devcontainer/test-herdr-migration.bash`（`devcontainer-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 499 | test_session_cwd_repair・multi_workspace ①② | 0 | 118 | session.json の cwd 修復が壊れ、復元先や再開情報が静かに変わる、稼働中の保存と競合する、複数 workspace が収束する | 表 | 659 | 7,949 |

`.devcontainer/test-initialize-mounts.bash`（`devcontainer-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 500 | 1. mounts と initialize.bash が同じ集合 | 0 | 4 | initialize.bash が作らない mount の対象を Docker が root 所有で作り、以降の書き込みが権限で失敗する | 表 | 659 | 7,953 |

`.devcontainer/test-install-beforehand.bash`（`devcontainer-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 501 | agent-runner の個人設定の配置と雛形の変更の反映 | 1 | 47（準備 9 を含む） | 利用者が書いた agent-runner の個人設定を上書きする、雛形の変更が個人設定を置いた後に効かなくなる（#167） | 表 | 660 | 8,000 |

`.devcontainer/test-install-ctx7.bash`（`devcontainer-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 502 | 固定した版の導入と ctx7 を --version だけで呼ぶこと | 1 | 45（準備 42 を含む） | ctx7 setup などを呼び、共有の ~/.claude・~/.codex に MCP 設定とスキルを書く（導入は成功して気付けない） | 表 | 661 | 8,045 |

`.devcontainer/test-install-resoloop.bash`（`devcontainer-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 503 | 2. fork のビルドから最新の公開版へ戻す | 0 | 6 | fork のビルドから最新の公開版へ戻せず、「常に最新」（#45）が黙って崩れる | 表 | 661 | 8,051 |
| 504 | 1. 未導入からの導入（正例）（正しく通る例） | 1 | 60（準備 56 を含む） | 対の守り: fork のビルドが残り「常に最新」が黙って崩れる。導入の基本経路の正例 | 表 | 662 | 8,111 |

`.devcontainer/test-pi-superagents.bash`（`devcontainer-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 505 | bind 先・argv の一致・ランチャーごとの設定・退避世代・settings 不変（#2・#7・#13・#22・#26） | 0 | 186 | tier の bind 先の取り違え、別ランチャーの設定を重ねる、退避世代の上書き、共有 settings.json の書き換え、argv の食い違い | 表 | 662 | 8,297 |

`.devcontainer/test-report-resoloop-skills.bash`（`devcontainer-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 506 | プロジェクトごとのスキル同期の状態の表示 | 1 | 50（準備 12 を含む） | 同梱スキルの更新が必要なことを「最新」と読み違えて表示する、差分や失敗で 0 以外になり postCreate が止まる | 表 | 663 | 8,347 |

`.devcontainer/test-run-tests.bash`（`devcontainer-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 507 | 1. 失敗があれば 1 を返す | 0 | 6 | 失敗した bash テストがあっても 0 を返し、壊れたテストを見逃す（失敗を成功と報告する） | 表 | 663 | 8,353 |
| 508 | 4. 既定の対象は両方の入口を含み lib を含まない | 0 | 6 | tests/scripts か .devcontainer が既定の一覧から落ち、そのテストが 1 本も走らないまま PASS と報告する | 表・重さは #236 | 663 | 8,359 |
| 509 | 2. すべて通れば 0（正例）（正しく通る例） | 0 | 2 | 対の守り: 失敗を成功と報告する。何でも失敗にする実装を防ぐ正例 | 表 | 663 | 8,361 |

`tools/devenv_migration/tests/test_pi_provider_setup.py`（`devcontainer-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 510 | `test_setup_targets_the_same_agent_directory_as_pi` | 4 | 15 | 引用した ~/ をそのまま書く、cwd 変更後に相対パスを解くと、別ディレクトリの models.json・auth.json を書く | 表 | 667 | 8,376 |
| 511 | `test_agent_dir_matches_the_directory_pi_selects` | 4 | 21 | --agent-dir が Pi の選ぶ設定ディレクトリと食い違い、別の settings・models・auth を読み書きする | 表 | 671 | 8,397 |
| 512 | `test_provider_setup_uses_lexical_path_before_validation_or_writes` | 1 | 17 | alias/.. のまま実体の検査をすり抜け、別ディレクトリの models・auth を書く（誤ったディレクトリへの書き込み） | 表 | 672 | 8,414 |
| 513 | `test_setup_pins_resolved_directory_for_its_followup_pi_commands` | 1 | 14 | 後続の Pi 呼び出しが生の相対パスを再解釈し、別ディレクトリを更新する（誤ったディレクトリへの更新） | 表・重さは #236 | 673 | 8,428 |
| 514 | `test_launcher_pins_same_directory_before_executing_pi` | 1 | 20 | ランチャーが正規化前の生のパスを Pi の process tree に渡し、別ディレクトリを使う | 表 | 674 | 8,448 |

`tools/devenv_migration/tests/test_pi_shared_packages.py`（`devcontainer-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 515 | `test_rebuild_preserves_shared_packages` | 1 | 100（準備 49 を含む） | rebuild が共有 ~/.pi の他リポジトリの登録（context7-pi）や利用者の packages・extensions・theme を黙って消す | 表 | 675 | 8,548 |

`tools/devenv_migration/tests/test_pi_vertex_launchers.py`（`devcontainer-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 516 | `test_launch_reaches_pi_without_adc_preserving_args_cwd_environment_and_exit` | 1 | 17 | 引数の引用・cwd・HOME・終了コードが崩れ、Pi に別の入力で届く（黙って別の入力になる） | 表 | 676 | 8,565 |
| 517 | `test_linked_auth_reaches_parent_and_child_without_changing_host_state` | 2 | 42 | symlink・hardlink の auth を正規化せず、共有の auth を書き換える（共有データの破壊） | 表 | 678 | 8,607 |
| 518 | `test_missing_any_used_vertex_model_stops_before_pi_and_auth_reads` | 1 | 16 | catalog に無いモデルで Pi のあいまい一致に落ち、別のモデルで動く（誤った結果） | 表 | 679 | 8,623 |
| 519 | `test_native_vertex_sdk_receives_saved_or_explicit_adc_path` | 3 | 92 | 保存済み・明示の ADC パスを SDK に渡さない、明示の指定を上書きして別の資格情報で動く（誤った結果） | 表 | 682 | 8,715 |
| 520 | `test_relative_agent_dir_stays_fixed_when_a_child_changes_cwd` | 1 | 12 | 相対の agent dir が子の cwd で別の場所に解け、auth の overlay を外れる（秘密・認証の取り違え） | 表 | 683 | 8,727 |
| 521 | `test_catalog_with_only_used_vertex_models_reaches_pi`（正しく通る例） | 1 | 10 | 対の守り: catalog に無いモデルで Pi が別のモデルで動く（誤った結果）。何でも拒否する実装を防ぐ正例 | 表 | 684 | 8,737 |

`tests/scripts/test-blender-system-python.bash`（`script-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 522 | Blender の終了コードの伝搬 | 1 | 19（準備 12 を含む） | wrapper が Blender の終了コードを捨て、Blender の失敗を成功と報告する（resoloop は 0 以外で BLENDER_FAILED） | 表 | 685 | 8,756 |

`tests/scripts/test-check-layout.bash`（`script-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 523 | 場面 3〜8・10〜12（配置の逸脱） | 0 | 155 | 配置の逸脱を通す: 宙吊りの追跡 symlink・追跡中なのに ignore・スキルのリンクの不一致・共有の指示や設定を読まないプロジェクト | 表 | 685 | 8,911 |

`tests/scripts/test-gitignore.bash`（`script-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 524 | 一覧 3（ignore してはならない共通ツール・文書） | 0 | 8 | ignore が広がり、共通ツール・雛形・文書が追跡から漏れて、リポジトリに残らない（gitignore の範囲） | 表・重さは #236 | 685 | 8,919 |

`tests/scripts/test-instructions.bash`（`script-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 525 | CLAUDE.md の読み込み指定とペルソナ節の SHA | 1 | 19（準備 10 を含む） | CLAUDE.md が @AGENTS.md を読み込まず規約・安全ルールが読まれない、利用者所有のペルソナ節が書き換わる | 表・重さは #236 | 686 | 8,938 |

`tests/scripts/test-new-world.bash`（`script-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 526 | 場面 4・5・16・17・19（途中状態・食い違い） | 0 | 34 | --apply の繰り返しでの変更、前提欠落での途中状態、別の指示を読む .pi を残す、AGENTS.md が無いのに成功と報告する | 表 | 686 | 8,972 |

`tests/scripts/test-resoloop-fork.bash`（`script-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 527 | 場面 1 の後半・3・4 の一部・8 の一部・9・10 | 0 | 45 | 外側の repo を checkout と誤認、origin 以外のブランチを選ぶ、失敗（外部コマンド・版の不一致・main が動かない）を成功と報告する | 表 | 686 | 9,017 |

`tests/scripts/test-resoloop-meshy.bash`（`script-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 528 | 場面 1〜3（別のリポジトリを自分の checkout と扱わない） | 1 | 60（準備 40 を含む） | origin の違う checkout や外側のリポジトリの checkout を、自分の checkout として扱う（別のリポジトリを選ぶ） | 表 | 687 | 9,077 |

`tests/scripts/test_superpowers_context.py`（`script-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 529 | `ContextTests::test_missing_unsupported_or_foreign_parent_origin_has_actionable_error` | 1 | 10 | origin が無い・GitHub 以外・別のリポジトリの親を受け入れ、別のリポジトリを PARENT_ROOT に選ぶ | 表 | 688 | 9,087 |
| 530 | `ContextTests::test_linked_parent_requires_explicit_main_parent` | 1 | 7 | linked worktree を暗黙の親に選ぶ（main checkout の明示を求めない） | 表 | 689 | 9,094 |
| 531 | `ContextTests::test_explicit_roots_must_be_absolute_checkout_roots` | 1 | 7 | 相対パスや checkout 内のサブディレクトリを root に選ぶ（checkout の外を選ぶ） | 表 | 690 | 9,101 |
| 532 | `ContextTests::test_invalid_repository_inputs_fail_clearly` | 1 | 4 | github.com.evil など他のホストの URL を GitHub と誤認する | 表 | 691 | 9,105 |

`tests/scripts/test_superpowers_lifecycle.py`（`script-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 533 | `LifecycleInstructionTests::test_imported_documents_are_unchanged_since_import` | 1 | 86（`tests/scripts/fixtures/superpowers-imported-documents.sha256.json` 24・準備 56 を含む） | 取り込んだ過去文書（凍結した履歴）が書き換わっても気付けない（記録の上書き） | 表・重さは #236 | 692 | 9,191 |

`tests/scripts/test_superpowers_review_copy.py`（`script-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 534 | `ReviewCopyTests::test_uncommitted_worktree_or_index_changes_are_rejected` | 1 | 7 | 未コミットの版をコピーして、利用者が確認した版と食い違う | 表 | 693 | 9,198 |

#### 高


`tools/agent_runner/tests/adapters/codex/test_codex.py`（`agent-runner-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 535 | `test_prepare_passes_prompt_over_stdin_with_read_only_sandbox` | 1 | 9 | 読み取りのロールを -s read-only で起動する権限のフラグ。外れると読み取りの担当が書き込める権限で動く | 表 | 694 | 9,207 |
| 536 | `test_prepare_write_role_uses_workspace_write_effort_and_args` | 1 | 110（準備 102 を含む） | 書き込みのロールの sandbox を workspace-write（worktree と /tmp だけに書ける）に固定する権限のフラグ | 表 | 695 | 9,317 |

`tools/agent_runner/tests/adapters/cursor/test_cursor.py`（`agent-runner-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 537 | `test_prepare_write_role_forces_and_effort_uses_bracket` | 1 | 132（準備 126 を含む） | 書き込みのロールに --sandbox を付けず、利用者の sandbox.mode に従わせる権限のフラグ（#201） | 表 | 696 | 9,449 |

`tools/agent_runner/tests/adapters/devin/test_adapter.py`（`agent-runner-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 538 | `test_prepare_writes_prompt_file_and_maps_flags` | 1 | 13 | --export に attempt の export.json（runner が伏せ字にする場所）を渡す。ずれると継いだ秘密を含む export が残る | 表 | 697 | 9,462 |
| 539 | `test_retained_export_with_secrets_is_redacted_before_collection` | 1 | 348（`tools/agent_runner/tests/adapters/devin/conftest.py` 59・`tools/agent_runner/tests/adapters/devin/fake_cli.py` 34・準備 195 を含む） | adapter が export を書かせる場所と runner が伏せ字にする場所の一致。ずれると継いだ秘密を含む export が attempt に残る | 表 | 698 | 9,810 |

`tools/agent_runner/tests/adapters/pi/test_adapter.py`（`agent-runner-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 540 | `test_prepare_builds_launcher_argv` | 1 | 143（`tools/agent_runner/tests/adapters/pi/conftest.py` 35・準備 98 を含む） | --no-approve・--no-session・--provider の固定。外れると設定・拡張の読み込み、伏せ字の無い記録、別の provider への資格情報とプロンプトの送信が黙って起きる | 表 | 699 | 9,953 |

`tools/agent_runner/tests/test_checkout_policy.py`（`agent-runner-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 541 | `test_unavailable_registration_blocks_work_without_launch_or_repair` | 1 | 40（準備 23 を含む） | 起動前に監査できない登録（移動・消失した worktree）があれば担当を起動せず止め、登録を回収（repair・prune）しない | #236 の判定 | 700 | 9,993 |

`tools/agent_runner/tests/test_git_isolation.py`（`agent-runner-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 542 | `test_fixture_git_stays_in_its_temporary_repository` | 1 | 11 | GIT_DIR を受け継いだ別の pytest で動く内側の確認。外れるとテストの git が実リポジトリの設定・index・ブランチを書き換える | 表 | 701 | 10,004 |
| 543 | `test_inherited_git_dir_of_a_linked_worktree_does_not_reach_fixture_git` | 1 | 59（準備 34 を含む） | rebase --exec が export する GIT_DIR を受け継いでも、fixture の git が実リポジトリの設定・index・ブランチを書き換えない（#166） | 表 | 702 | 10,063 |

`tools/agent_runner/tests/test_process.py`（`agent-runner-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 544 | `test_stdin_quotes_multiline_cwd_and_environment_are_literal` | 1 | 24 | cwd が外れると担当が親の checkout で作業して書き込む。シェルを通すとプロンプトが黙って変わる | 表 | 703 | 10,087 |
| 545 | `test_process_has_independent_session` | 1 | 7 | 独立した session で起動しないと、停止の signal が controller の process group に届く | 表 | 704 | 10,094 |
| 546 | `test_secrets_split_across_reads_are_redacted_on_both_pipes` | 1 | 18 | pipe の読み取りごとに伏せ字にすると、読み取りの境界をまたいだ秘密がログに残る（秘密情報の漏れ） | 表 | 705 | 10,112 |
| 547 | `test_immediate_exit_before_ownership_observation_stops_children` | 1 | 55 | CLI が追跡の前に終わって回収されても、監督プロセスを識別の anchor にして同じ group の孤児を見つけて止める | 表 | 706 | 10,167 |
| 548 | `test_leader_exit_stops_observed_descendants` | 1 | 32 | leader が正常に終わっても、観測済みの子孫（setsid で group を離れ SIGTERM を無視する子）を TERM → KILL で止める | 表 | 707 | 10,199 |
| 549 | `test_coroutine_cancellation_stops_leader_and_escaped_descendant` | 1 | 34 | coroutine が取り消されても finally の停止を飛ばさず leader と離れた子孫を止める。外すと担当の process が残る | 表 | 708 | 10,233 |
| 550 | `test_unconfirmed_stop_is_reported` | 1 | 9 | 停止の確認を exit=0 から推測せず、独立した信号で確かめる（未確認の停止の process の層の代表） | 表 | 709 | 10,242 |
| 551 | `test_repeated_cancellation_during_launch_still_stops_process` | 1 | 43 | 起動の完了の途中で 2 回取り消されても PID を失わず、起動した process を止める。外すと起動した担当が管理されず残る | 表 | 710 | 10,285 |
| 552 | `test_non_utf8_descendant_name_does_not_escape_tracking` | 1 | 26 | /proc の comm は任意の bytes で ')' も含みうる。stat 全体を decode すると生きた子孫が追跡から漏れて止まらない | 表 | 711 | 10,311 |
| 553 | `test_reused_leader_group_is_not_signaled` | 1 | 15 | leader の PID・PGID が別の process に再利用されたら、その group を自分のものとみなさず signal を送らない。外すと無関係な process を止める | 表 | 712 | 10,326 |
| 554 | `test_reused_descendant_identity_is_not_overwritten` | 1 | 16 | 本物の group の中でも、記録した子孫の PID が再利用されたら識別を上書きせず、その子も取り込まず停止を未確認とする | 表 | 713 | 10,342 |
| 555 | `test_group_after_leader_exit_requires_identity_anchor` の `False` | 1 | 0 | anchor が無ければ孤児を取り込まず、未知の process の不確かさを停止の確認に残す。外すと無関係な process を止める・確かめられない停止を確認済みと報告する | 表 | 714 | 10,342 |
| 556 | `test_group_after_leader_exit_requires_identity_anchor` の `True`（正しく通る例） | 1 | 21（関数 21 を含む） | 観測済みの group member（識別が一致）が anchor なら、leader の終了後の新しい孤児を取り込む正例（取り込みの正しく通る例） | 表 | 715 | 10,363 |

`tools/agent_runner/tests/test_review_regressions.py`（`agent-runner-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 557 | `test_retained_receipts_are_scrubbed_even_when_invalid` | 1 | 21 | 停止を確認した試行の receipt.json を、壊れた JSON でも伏せ字にする。外れると保持する受領に秘密情報が漏れる | 表 | 716 | 10,384 |
| 558 | `test_unconfirmed_stop_does_not_read_or_rewrite_live_receipt` | 1 | 30 | 停止を確認できないときは受領を読まず書き換えず sensitive_paths に出す。外れると生きた書き手の操作で秘密を結果に写す | 表 | 717 | 10,414 |
| 559 | `test_exec_only_secrets_are_scrubbed_from_command_output` | 1 | 133（準備 121 を含む） | 起動時の環境にだけある秘密の値も、許可して子に渡したら stdout から伏せる。外れると保持するログに秘密が漏れる | 表 | 718 | 10,547 |

`tools/agent_runner/tests/test_runner.py`（`agent-runner-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 560 | `test_only_allowlisted_environment_and_redacted_results` | 1 | 34 | 許可リストの変数だけを子に渡し（GIT_* は除く）、結果・ログから秘密の値を伏せる。外れると資格情報が渡り秘密が残る | 表 | 719 | 10,581 |
| 561 | `test_checkout_preparation_is_supervised` の `cancel` | 1 | 106（関数 106 を含む） | worktree の準備（post-checkout hook と SIGTERM を無視する子）を監督する。外れると準備のログに秘密が漏れ、準備が終わらないまま担当が起動する | 表 | 720 | 10,687 |
| 562 | `test_devin_retained_export_is_redacted_after_nonzero_exit` | 1 | 20 | 非 0 終了の後も、Devin が attempt に残す export.json の継いだ秘密を伏せ字にする。外れると秘密が残る | 表 | 721 | 10,707 |
| 563 | `test_unconfirmed_stop_never_reads_or_rewrites_devin_export` | 1 | 55 | 停止未確認の試行の export.json・receipt.json を読まず書き換えず sensitive_paths に出す。外れると秘密が残る | 表 | 722 | 10,762 |
| 564 | `test_unsafe_devin_export_is_retained_reported_and_never_collected` の `symlink` | 1 | 32（関数 32 を含む） | export.json が symlink なら辿らず書き換えず sensitive_paths に出す。外れると attempt の外のファイルを上書きする | 表 | 723 | 10,794 |
| 565 | `test_devin_export_redaction_fault_never_reaches_collection` | 1 | 533（準備 145・準備 360 を含む） | export.json を伏せ字にできなかったら収集に回さず sensitive_paths に出す。外れると秘密の残る記録が payload・identity に写る | 表 | 724 | 11,327 |

`tools/agent_runner/tests/test_workspace.py`（`agent-runner-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 566 | `test_audit_detects_existing_dirty_content_edits` | 2 | 20 | checkout の監査: 既に dirty なファイルの内容の編集と untracked の symlink の参照先の変更を検出する | 表 | 726 | 11,347 |
| 567 | `test_audit_detects_checkout_mutations` | 4 | 20 | 指紋の入力（untracked の一覧・mode・index の blob・commit）を 1 つずつ確かめる。外れるとその種類の変更を黙って見逃す | 表 | 730 | 11,367 |
| 568 | `test_repair_of_moved_main_and_linked_worktree_preserves_all_resources` | 1 | 30 | 監査は観察だけで、消えた登録を自動で回収（prune・repair・remove）しない。外れると worktree の資源を失う | 表 | 731 | 11,397 |
| 569 | `test_audit_detects_submodule_dirty_content` | 1 | 14 | 初期化済みの submodule の作業ファイルの変更を、親の checkout の監査で検出する | 表 | 732 | 11,411 |
| 570 | `test_audit_diagnoses_unavailable_baseline` の `missing-checkout_missing-False-True` | 1 | 53（関数 53 を含む） | 開始前に監査できない登録を unavailable_before の finding として返し起動前に止める。外すと基準の無い checkout の変化を確かめないまま担当を起動する | 表 | 733 | 11,464 |
| 571 | `test_audit_distinguishes_changes_from_unavailability` | 2 | 36 | 担当が消した checkout を unavailable_after として報告する（外すと変化なしになる）。開始時に監査できなかった基準は後で直っても遡って証明しない | 表 | 735 | 11,500 |
| 572 | `test_registration_list_failure_still_stops_snapshot` | 1 | 7 | worktree の登録の一覧が読めないとき空の基準を返さず WorkspaceError で止める。外れると以後の監査が何も報告しない | 表 | 736 | 11,507 |
| 573 | `test_async_preparation_uses_pinned_commit_and_safe_environment` | 1 | 32 | worktree の準備が固定した commit を使い、外から渡された GIT_DIR を無視する（#230 の S の例 GIT_* の無視） | 表 | 737 | 11,539 |
| 574 | `test_git_preparation_stops_term_resistant_child_of_exited_hook` | 1 | 35 | checkout の hook（post-checkout）が残した SIGTERM を無視する子を、準備の監督が止める。外れると孤児が残る | 表 | 738 | 11,574 |
| 575 | `test_git_common_dir_ignores_ambient_git_routing` | 1 | 107（`tools/agent_runner/tests/conftest.py` 26・準備 72 を含む） | 外から渡された GIT_DIR が別のリポジトリを指しても、指定の checkout の値を返す（#230 の S の例 GIT_DIR の無視） | 表 | 739 | 11,681 |

`.agents/skills/pr-review-fix-loop/tests/test_loop_check_options.py`（`pr-review-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 576 | `test_check_options_has_no_external_side_effects` | 1 | 43（準備 35 を含む） | 設定の事前検査が PR・GitHub・run・ロックへ副作用を残し、後続処理や他 run を妨げる。 | 表 | 740 | 11,724 |

`.agents/skills/pr-review-fix-loop/tests/test_loop_diagnostics.py`（`pr-review-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 577 | `test_logs_are_read_only_when_safe` | 6 | 40 | sensitive・symlink・出力外・生存中のログを読み、秘密や別ファイルに触れる。 | 表 | 746 | 11,764 |
| 578 | `test_secret_in_logs_never_reaches_the_records` | 1 | 28 | ログ中の秘密情報が永続記録や CLI の JSON 出力へ漏れる。 | 表 | 747 | 11,792 |
| 579 | `test_unsaved_diagnostic_keeps_the_output_and_tells_the_controller` | 1 | 214（準備 193 を含む） | 診断の保存失敗時に唯一のログを削除し、原因調査不能にする。 | 表 | 748 | 12,006 |

`.agents/skills/pr-review-fix-loop/tests/test_loop_herdr_pane.py`（`pr-review-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 580 | `test_start_succeeds_when_herdr_hangs` | 1 | 50（準備 32 を含む） | Herdr が応答しないとき start が止まり、レビュー作業を進められない（#231 が hang を S と明記）。 | 表 | 749 | 12,056 |

`.agents/skills/pr-review-fix-loop/tests/test_loop_review.py`（`pr-review-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 581 | `test_verify_reviewer_rejects_each_broken_condition` | 11 | 26 | 失敗した runner、別 run・担当・PR・HEAD の成果、未停止の担当、改ざんされた成果を受理し、計画・マージへ進む。 | 表 | 760 | 12,082 |
| 582 | `test_after_run_result_is_reloaded_before_reviewer_validation` | 1 | 40 | after_run が却下した結果を古い成功値で受け付け、失敗したレビューで計画へ進む。 | 表 | 761 | 12,122 |
| 583 | `test_review_executes_after_run_against_saved_result` | 1 | 19 | 設定された後処理を省き、検査を経ない runner 成果を成功として使う。 | 表 | 762 | 12,141 |
| 584 | `test_reuse_counts_only_pairs_for_the_current_head` | 1 | 18 | 古い HEAD のレビューを現 HEAD に流用して未検証の変更をマージする。 | 表 | 763 | 12,159 |
| 585 | `test_review_refuses_when_the_head_moved_after_cycle_begin` | 1 | 12 | 古い HEAD のレビューを現 HEAD に流用して未検証の変更をマージする。 | 表 | 764 | 12,171 |
| 586 | `test_review_records_partial_failure_and_cleans_owned_worktrees` | 1 | 23 | 失敗したレビュアーを指摘なしとして扱う、または所有 worktree を残す・誤削除する。 | 表 | 765 | 12,194 |
| 587 | `test_review_with_no_accepted_reviewer_fails_with_code_6` | 1 | 18 | 受理したレビューが 0 件でも計画へ進む。 | 表 | 766 | 12,212 |
| 588 | `test_unconfirmed_stop_holds_the_lock_until_operator_recovery` | 1 | 47 | 生存中かもしれないレビュアーの資源を消す、または停止未確認のまま再起動して競合させる。 | 表 | 767 | 12,259 |
| 589 | `test_interrupted_review_without_result_is_not_rerun` | 1 | 32 | 生存中かもしれないレビュアーの資源を消す、または停止未確認のまま再起動して競合させる。 | 表 | 768 | 12,291 |
| 590 | `test_resume_after_review_continues_from_status` | 1 | 14 | 再開時にレビューの保存結果を無視して段階を飛ばす。 | 表 | 769 | 12,305 |
| 591 | `test_next_commands_never_carry_placeholders_and_recover_rejects_them` | 1 | 26 | 書きかけの停止確認を事実として受理し、生存プロセスの資源とロックを解放する。 | 表 | 770 | 12,331 |
| 592 | `test_recover_keeps_files_that_may_hold_secrets` | 1 | 20 | 回収時に秘密情報が残りうる receipt を消し、必要な調査記録を失う。 | 表 | 771 | 12,351 |
| 593 | `test_verify_reviewer_rejects_artifacts_that_do_not_belong_to_this_head` | 2 | 31 | payload が正しくても、本文や候補一覧が別 PR・HEAD のものを採用する。 | 表 | 773 | 12,382 |
| 594 | `test_missing_output_parent_does_not_hide_registered_worktrees` | 1 | 38 | 親ディレクトリが消えても登録済み worktree を見落とし、ロックを解放・誤削除する。 | 表 | 774 | 12,420 |
| 595 | `test_missing_output_checks_fail_closed` | 1 | 45 | git 登録確認が失敗した状態を空とみなして資源を削除する。 | 表 | 775 | 12,465 |
| 596 | `test_cleanup_output_removes_only_its_own_prefix` | 2 | 24 | 別の出力ディレクトリ（loop が作った名前以外）を削除する。 | 表 | 777 | 12,489 |
| 597 | `test_cleanup_without_force_keeps_only_a_written_worktree` | 2 | 33 | レビュアーが書いた worktree の変更を消す。 | 表 | 779 | 12,522 |
| 598 | `test_rerun_is_not_started_while_another_attempt_is_unconfirmed` | 1 | 31 | 未停止の試行と同時に再実行し、同じ成果や資源へ競合書き込みする。 | 表 | 780 | 12,553 |
| 599 | `test_request_is_kept_only_from_a_regular_file` | 1 | 25 | 未停止の書き手や symlink をたどって別のファイルを読み取り、保存対象を誤る。 | 表 | 781 | 12,578 |
| 600 | `test_write_exceptions_name_the_target_checkout_git` | 1 | 26 | runner に別 checkout の Git 書き込み権限を渡す。 | 表 | 782 | 12,604 |
| 601 | `test_unconfirmed_after_run_keeps_outputs_and_lock_until_the_operator_confirms` | 1 | 53 | 生存中かもしれない after_run の出力を消し、ロックを解放する。 | 表 | 783 | 12,657 |
| 602 | `test_review_after_an_interrupted_after_run_holds_the_run` | 1 | 22 | 中断した after_run を再起動し、既存の子プロセスや出力と競合する。 | 表 | 784 | 12,679 |
| 603 | `test_unconfirmed_attempt_holds_the_run_instead_of_planning` | 2 | 78 | レビュアーの停止を確認しないまま計画を始め、資源を消す。 | 表 | 786 | 12,757 |
| 604 | `test_verify_reviewer_accepts_a_complete_payload_and_records_hashes`（正しく通る例） | 1 | 13 | 正例: 正しい成果を拒否する実装を許さない。対の拒否は、別 run・担当・PR・HEAD・未停止・改ざんの成果を受理して計画・マージへ進む損害を防ぐ。 | 表・重さは #236 | 787 | 12,770 |
| 605 | `test_missing_parent_with_no_registration_is_removed`（正しく通る例） | 1 | 337（準備 323 を含む） | 正例: 拒否だけで回収が進まない実装を許さない。対の拒否は、登録確認の失敗を空とみなす誤削除と、登録済み worktree の見落としを防ぐ。 | 表・重さは #236 | 788 | 13,107 |

`.agents/skills/pr-review-fix-loop/tests/test_loop_reviewer_protocol.py`（`pr-review-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 606 | `test_literal_reviewer_completes_the_real_helper_within_the_declared_exceptions` | 1 | 272（準備 242 を含む） | read-only runner の書き込み範囲が広がる、または別 PR・HEAD の成果が混入する（実 helper 経路で検出）。 | 表 | 789 | 13,379 |

`.agents/skills/pr-review-fix-loop/tests/test_loop_state.py`（`pr-review-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 607 | `test_second_start_is_refused_while_the_first_run_holds_the_lock` | 1 | 11 | 同じ PR の同時書き込み、または別 run のロック解放による競合。 | 表 | 790 | 13,390 |
| 608 | `test_out_of_order_calls_are_refused` | 1 | 8 | レビューや判断記録の前にサイクルを完了し、未検証の PR を成功扱いする。 | 表 | 791 | 13,398 |
| 609 | `test_cycle_end_before_the_record_is_posted_keeps_the_cycle_open` | 1 | 20 | レビューや判断記録の前にサイクルを完了し、未検証の PR を成功扱いする。 | 表 | 792 | 13,418 |
| 610 | `test_record_for_another_head_is_not_taken_as_this_cycle` | 1 | 11 | 別 HEAD の判断や push を現サイクルのものとして採用する。 | 表 | 793 | 13,429 |
| 611 | `test_fixes_pushed_requires_the_pr_head_to_be_the_pushed_commit` | 1 | 13 | 別 HEAD の判断や push を現サイクルのものとして採用する。 | 表 | 794 | 13,442 |
| 612 | `test_no_fix_needed_needs_a_merged_finalize_result_at_the_same_head` | 1 | 23 | 未マージまたは別 HEAD のマージを検証済みとして完了報告する。 | 表 | 795 | 13,465 |
| 613 | `test_finalize_stopped_ends_the_run_as_stopped_and_not_merged` | 1 | 24 | finalize の停止をマージ成功として報告する。 | 表 | 796 | 13,489 |
| 614 | `test_finalize_stopped_keeps_the_real_merge` | 3 | 54 | finalize が停止しても、実際のマージを未マージとして誤報告する。 | 表 | 799 | 13,543（行数が目標に届く） |
| 615 | `test_finalize_merged_but_pr_not_merged_is_a_mismatch_when_stopped` | 1 | 18 | 未マージまたは別 HEAD のマージを検証済みとして完了報告する。 | 表 | 800 | 13,561 |
| 616 | `test_cycle_limit_ends_with_fixes_pushed` | 1 | 17 | サイクル上限後に追加レビューなしで次へ進み、未検証のままマージする。 | 表 | 801 | 13,578 |
| 617 | `test_finish_releases_only_its_own_lock` | 1 | 13 | 同じ PR の同時書き込み、または別 run のロック解放による競合。 | 表 | 802 | 13,591 |
| 618 | `test_abort_after_a_finalize_merge_keeps_the_merge` | 1 | 36 | finalize 後に cycle-end が停止しても、abort でマージ済みを false と記録する。 | 表 | 803 | 13,627 |
| 619 | `test_abort_records_the_merge_state_it_observed` | 4 | 39 | PR の実状態、finalize の最後の観測、未確認 null を混同してマージ状態を誤報告する。 | 表 | 807 | 13,666 |
| 620 | `test_finalize_result_is_only_for_abort_and_must_be_a_finalize_result` | 1 | 24 | 不正な finalize 結果で run を上書きし、マージ状態を誤記録する。 | 表 | 808 | 13,690 |
| 621 | `test_cli_finish_abort_passes_the_finalize_result` | 1 | 16 | CLI が --finalize-result を渡さず、PR 不可読時に観測済みのマージを null と記録する。 | 表 | 809 | 13,706 |
| 622 | `test_status_returns_the_next_command_after_a_restart` | 1 | 11 | 再開時に誤った段階へ進み、レビューや判断を飛ばす。 | 表 | 810 | 13,717 |
| 623 | `test_record_from_an_earlier_run_for_the_same_head_is_not_taken` | 1 | 23 | 同じ HEAD の古い run の判断を新 run の判断として流用する。 | 表 | 811 | 13,740 |
| 624 | `test_a_differently_cased_pr_url_shares_the_lock` | 1 | 16 | URL の大文字小文字違いで同じ PR に二重ロックを作り、同時書き込みする。 | 表 | 812 | 13,756 |
| 625 | `test_records_need_the_authenticated_login` | 1 | 26 | login を得られないまま投稿者の絞り込みを緩め、他人の判断記録を採用する。 | 表 | 813 | 13,782 |
| 626 | `test_cycle_end_reads_the_authenticated_users_record` | 1 | 16 | 他人のコメントを認証済み利用者の判断として採用する。 | 表 | 814 | 13,798 |
| 627 | `test_cycle_end_accepts_a_spec_commit_merge` | 1 | 119（準備 92 を含む） | 検証 HEAD の上に Spec commit を載せた PR のマージを、別 commit と誤照合する。 | 表 | 815 | 13,917 |

`.agents/skills/pr-review-fix-loop/tests/test_pr_review_fix_loop_skill_contract.py`（`pr-review-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 628 | `test_loop_skill_runs_only_when_explicitly_invoked` | 1 | 660（`.agents/skills/pr-review-fix-loop/tests/conftest.py` 642・準備 16 を含む） | disable-model-invocation の権限境界が外れ、明示依頼なしに push・マージまで進む。 | 表 | 816 | 14,577 |

`.agents/skills/pr-review/tests/test_port_routing.py`（`pr-review-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 629 | `test_upstream_full_diff_pair_save_cleanup_preserves_shared_refs` | 1 | 26 | upstream PR の全差分レビューで、PR・HEAD・commit・base・保存先を取り違える、または共有 ref を変更する。 | 表 | 817 | 14,603 |
| 630 | `test_moving_live_head_keeps_drafts_then_fresh_session_continues` | 1 | 21 | PR の HEAD が動いたのに保存を通し、PR・HEAD・commit・base・保存先を取り違える、または共有 ref を変更する。 | 表 | 818 | 14,624 |
| 631 | `test_external_checkout_requires_explicit_source_and_matching_remote` | 1 | 14 | 明示指定のない・remote の合わない外部 checkout を対象に、他の Git や利用者所有ファイルを操作・削除する。 | 表 | 819 | 14,638 |
| 632 | `test_target_rejects_unvalidated_input_without_creating_session` | 5 | 17 | 未検証の target 入力（remote・sha・number・url・repository）を通し、PR・HEAD・保存先を取り違える。 | 表 | 824 | 14,655 |
| 633 | `test_explicit_commit_has_separate_pair_and_validates_worktree_head` | 1 | 11 | 指定 commit のレビューを別 pair にせず、または worktree の HEAD 変更後も保存し、commit・保存先を取り違える。 | 表 | 825 | 14,666 |
| 634 | `test_shallow_recovery_refuses_unowned_git_or_user_data` | 8 | 250（準備 199 を含む） | 浅い checkout の回収で、所有していない Git・他の worktree・利用者データを操作・削除する。 | 表 | 833 | 14,916 |

`.agents/skills/pr-review/tests/test_pr_review_workspace.py`（`pr-review-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 635 | `test_resolve_codex_model_name_uses_latest_turn_context` | 1 | 8 | Codex の最新の turn のモデルを取り違え、もっともらしい誤レビューを保存する。 | 表 | 834 | 14,924 |
| 636 | `test_resolve_codex_model_name_fails_closed` | 3 | 32 | Codex のモデル名が不正・非一意・rollout 破損でも受理し、識別を取り違えた誤レビューを保存する。 | 表 | 837 | 14,956 |
| 637 | `test_resolve_codex_model_name_rejects_malformed_completed_record` | 1 | 13 | 完了済みの rollout 行が壊れていても受理し、モデルの識別を取り違えた誤レビューを保存する。 | 表 | 838 | 14,969 |
| 638 | `test_resolve_runtime_model_name_fails_closed_outside_codex` | 2 | 13 | ../ や先頭空白を含むモデル名が通り、別の保存先へ書いて利用者ファイル・別 worktree・共有 Git を変更する。 | 表 | 840 | 14,982 |
| 639 | `test_resolve_runtime_model_name_rejects_codex_override` | 1 | 10 | Codex の実モデルと違う明示名で上書きし、識別を取り違えた誤レビューを保存する。 | 表 | 841 | 14,992 |
| 640 | `test_destination_fingerprint_distinguishes_symlink_entries` | 1 | 16 | 保存先の symlink を実体と区別できず、利用者ファイル・別 worktree・共有 Git を削除または変更する。 | 表 | 842 | 15,008 |
| 641 | `test_snapshot_existing_review_copies_regular_file` | 1 | 12 | 既存レビューの写しが誤り、モデル・PR・HEAD・保存先の識別を取り違えた誤レビューを保存する。 | 表 | 843 | 15,020 |
| 642 | `test_snapshot_existing_review_rejects_non_regular` | 3 | 21 | ディレクトリ・symlink・FIFO の保存先を通常ファイルとして扱い、利用者ファイル・別 worktree・共有 Git を削除または変更する。 | 表 | 846 | 15,041 |
| 643 | `test_snapshot_existing_review_rejects_source_race` | 1 | 25 | 読み取り中に差し替わった既存レビューを受理し、利用者ファイル・別 worktree・共有 Git を削除または変更する。 | 表 | 847 | 15,066 |
| 644 | `test_atomic_copy_replaces_internal_destination_symlink_entry` | 1 | 19 | 保存先 symlink の指す別ファイルを上書きし、利用者ファイル・別 worktree・共有 Git を削除または変更する。 | 表 | 848 | 15,085 |
| 645 | `test_safe_destination_rejects_symlink_escape` | 1 | 10 | symlink 経由で保存先が reviews の外へ出て、利用者ファイル・別 worktree・共有 Git を削除または変更する。 | 表 | 849 | 15,095 |
| 646 | `test_snapshot_does_not_refresh_index` | 1 | 14 | レビュー前後の snapshot が Git の index を更新し、利用者の共有 Git を変更する。 | 表 | 850 | 15,109 |
| 647 | `test_snapshot_preserves_existing_index_lock` | 1 | 10 | レビューの snapshot が利用者の index.lock を変更・削除する。 | 表 | 851 | 15,119 |
| 648 | `test_snapshot_reports_changes_excluding_reviews` | 4 | 35 | checkout の変更を検出する snapshot が欠け、利用者ファイル・別 worktree・共有 Git の変更を見逃す。 | 表 | 855 | 15,154 |
| 649 | `test_save_rejects_unknown_model_source` | 1 | 9 | state の model_source が未知でも save し、モデルの識別を取り違えた誤レビューを保存する。 | 表 | 856 | 15,163 |
| 650 | `test_create_pins_model_and_artifact_paths` | 1 | 36 | create がモデル・PR・HEAD・保存先を固定せず、識別を取り違えた誤レビューを保存する。 | 表 | 857 | 15,199 |
| 651 | `test_create_pins_existing_review_snapshot` | 1 | 29 | 既存レビューの写しを固定せず、モデル・PR・HEAD・保存先の識別を取り違えた誤レビューを保存する。 | 表 | 858 | 15,228 |
| 652 | `test_load_state_rejects_tampered_previous_review` | 1 | 15 | 改ざんされた前回レビューの参照を受理し、識別を取り違えた誤レビューを保存する。 | 表 | 859 | 15,243 |
| 653 | `test_fork_and_upstream_reviews_are_saved_and_rereviewed_independently` | 1 | 34 | fork と upstream の同番号 PR のレビューが同じ保存先・前回レビューに混ざり、一方が他方を上書きする。 | 表・重さは #236 | 860 | 15,277 |
| 654 | `test_create_rejects_invalid_pr_repository` | 2 | 9 | 不正な PR repository（../resoloop・usaturn/..）を受理し、保存先の識別を取り違えた誤レビューを保存する。 | 表 | 862 | 15,286 |
| 655 | `test_version6_session_is_kept_by_verify_save_and_cleanup` | 1 | 23 | 旧 state（repository 不明）を無視して verify・save・cleanup が進み、別 PR の worktree を削除・レビューを上書きする。 | 表 | 863 | 15,309 |
| 656 | `test_load_state_rejects_non_canonical_pr_repository` | 2 | 12 | 正規形でない PR repository の state を受理し、保存先の識別を取り違えた誤レビューを保存する。 | 表 | 865 | 15,321 |
| 657 | `test_save_rejects_rewritten_pr_repository` | 1 | 15 | 書き換えられた PR repository で save し、別 repository の保存先へ誤レビューを保存する。 | 表 | 866 | 15,336 |
| 658 | `test_review_artifact_paths_reject_invalid_branch` | 2 | 4 | 不正な branch 名（先頭 /・正規化後に空）で保存先を作り、誤った branch の保存先へレビューを保存する。 | 表・重さは #236 | 868 | 15,340 |
| 659 | `test_review_artifact_paths_reject_invalid_pr_number` | 2 | 10 | 不正な PR 番号（bool・0）で保存先を作り、誤った PR の保存先へレビューを保存する。 | 表・重さは #236 | 870 | 15,350 |
| 660 | `test_save_uses_only_pinned_paths` | 1 | 9 | save が固定した以外のパスへ書き、識別を取り違えた誤レビューを保存する。 | 表 | 871 | 15,359 |
| 661 | `test_save_rejects_changed_pinned_destination` | 1 | 13 | 固定後に変わった保存先へ save して他者のレビューを上書きし、識別を取り違えた誤レビューを保存する。 | 表 | 872 | 15,372 |
| 662 | `test_first_session_wins_same_destination` | 1 | 27 | 後から始めたセッションが先に保存したレビューを無断で上書きする。 | 表 | 873 | 15,399 |
| 663 | `test_save_rejects_changed_runtime_model` | 1 | 8 | save までにモデルが変わっても受理し、別モデルの名前で誤レビューを保存する。 | 表 | 874 | 15,407 |
| 664 | `test_save_rejects_tampered_destination` | 1 | 9 | 改ざんされた state の保存先で save し、別の保存先に誤レビューを保存する。 | 表 | 875 | 15,416 |
| 665 | `test_save_waits_for_repository_review_lock` | 1 | 24 | save が保存ロックを待たず競合し、利用者ファイル・別 worktree・共有 Git を削除または変更する。 | 表 | 876 | 15,440 |
| 666 | `test_cleanup_removes_session_after_successful_save` | 1 | 15 | 保存済み session の回収が誤り、保存したレビューや利用者ファイル・別 worktree・共有 Git を削除または変更する。 | 表 | 877 | 15,455 |
| 667 | `test_cleanup_refuses_before_save` | 1 | 13 | 保存前の cleanup を通して未保存レビューの worktree を削除し、利用者ファイル・別 worktree・共有 Git を削除または変更する。 | 表 | 878 | 15,468 |
| 668 | `test_cleanup_refuses_when_destination_diverges_from_draft` | 1 | 15 | 保存先が draft と食い違っても session を回収し、手編集のレビューなど利用者ファイル・別 worktree・共有 Git を削除または変更する。 | 表 | 879 | 15,483 |
| 669 | `test_cleanup_keeps_other_worktrees_and_main_checkout` | 1 | 16 | cleanup が他の worktree や本体 checkout に及び、利用者ファイル・別 worktree・共有 Git を削除または変更する。 | 表 | 880 | 15,499 |
| 670 | `test_cleanup_refuses_when_session_path_is_not_its_worktree` | 1 | 16 | session のパスが自分の worktree でないのに削除し、利用者ファイル・別 worktree・共有 Git を削除または変更する。 | 表 | 881 | 15,515 |
| 671 | `test_cleanup_refuses_worktree_of_another_repository` | 1 | 15 | 別 repository の worktree を自分のものとして回収し、利用者ファイル・別 worktree・共有 Git を削除または変更する。 | 表 | 882 | 15,530 |
| 672 | `test_cleanup_waits_for_repository_review_lock` | 1 | 24 | cleanup が保存ロックを待たず競合し、利用者ファイル・別 worktree・共有 Git を削除または変更する。 | 表 | 883 | 15,554 |
| 673 | `test_create_rejects_unsafe_attempt_id` | 1 | 11 | ../ を含む attempt id を受理し、session の外へ書いて利用者ファイル・別 worktree・共有 Git を削除または変更する。 | 表 | 884 | 15,565 |
| 674 | `test_create_rejects_reused_attempt_id` | 1 | 14 | 使用済みの attempt id で create し、既存の session や worktree を巻き込んで利用者ファイル・別 worktree・共有 Git を削除または変更する。 | 表 | 885 | 15,579 |
| 675 | `test_create_records_its_phases_in_the_journal` | 1 | 29 | create の journal が段階を記録せず、未終了の試行を回収可能と誤判定して worktree を削除する。 | 表 | 886 | 15,608 |
| 676 | `test_killed_create_reports_its_last_phase_and_leftovers` | 1 | 29 | kill された create の最終段階と残存物を報告せず、未終了の試行を回収可能と誤判定して worktree を削除する。 | 表 | 887 | 15,637 |
| 677 | `test_terminated_create_records_the_signal` | 1 | 20 | 終了させられた create の記録が無く、未終了の試行を回収可能と誤判定して worktree を削除する。 | 表 | 888 | 15,657 |
| 678 | `test_inspect_refuses_an_attempt_id_shared_by_two_sessions` | 1 | 15 | 同じ attempt id の 2 session を区別せず、未終了の試行を回収可能と誤判定して worktree を削除する。 | 表 | 889 | 15,672 |
| 679 | `test_abandon_clears_an_attempt_killed_while_waiting_for_the_lock` | 1 | 34 | ロック待ちで kill された試行を abandon する際に、利用者ファイル・別 worktree・共有 Git を削除または変更する。 | 表 | 890 | 15,706 |
| 680 | `test_abandon_waits_for_a_checkout_that_outlives_create` | 1 | 23 | create より長く生きる checkout を待たずに abandon し、利用者ファイル・別 worktree・共有 Git を削除または変更する。 | 表 | 891 | 15,729 |
| 681 | `test_abandon_keeps_a_worktree_locked_for_another_reason` | 1 | 11 | 利用者が別の理由で lock した worktree を abandon で削除し、利用者ファイル・別 worktree・共有 Git を削除または変更する。 | 表 | 892 | 15,740 |
| 682 | `test_abandon_refuses_while_the_attempt_is_running` | 1 | 11 | 実行中の試行を abandon で回収し、利用者ファイル・別 worktree・共有 Git を削除または変更する。 | 表 | 893 | 15,751 |
| 683 | `test_abandon_keeps_a_session_with_files_it_did_not_create` | 3 | 23 | helper が作っていないファイル・ディレクトリを含む session を abandon で削除する（利用者ファイル・別 worktree・共有 Git）。 | 表 | 896 | 15,774 |
| 684 | `test_legacy_inspect_reports_but_abandon_preserves_an_unowned_repo_directory` | 1 | 13 | 旧 checkout 方式の attempt で、所有していない repo/ を abandon で削除し、利用者ファイル・別 worktree・共有 Git を削除または変更する。 | 表 | 897 | 15,787 |
| 685 | `test_abandon_refuses_another_repository` | 1 | 10 | 別 repository の試行を abandon し、利用者ファイル・別 worktree・共有 Git を削除または変更する。 | 表 | 898 | 15,797 |
| 686 | `test_inspect_and_abandon_refuse_another_pr_repository` | 1 | 14 | 同じ checkout を共有する別 PR repository（fork・upstream）の試行を abandon し、利用者ファイル・別 worktree・共有 Git を削除または変更する。 | 表 | 899 | 15,811 |
| 687 | `test_abandon_keeps_a_journal_without_pr_repository` | 1 | 13 | 所属 PR が分からない旧 journal の session を推測して削除する。 | 表 | 900 | 15,824 |
| 688 | `test_abandon_touches_only_its_own_attempt` | 1 | 17 | abandon が自分以外の試行・他モデルのレビュー・利用者ファイルに及び、利用者ファイル・別 worktree・共有 Git を削除または変更する。 | 表 | 901 | 15,841 |
| 689 | `test_abandon_waits_for_the_repository_review_lock` | 1 | 28 | abandon が保存ロックを待たず、同時の save・cleanup と削除が競合する。 | 表・重さは #236 | 902 | 15,869 |
| 690 | `test_abandon_clears_records_left_by_an_interrupted_worktree_add` | 1 | 22 | 中断した worktree add の管理レコードの回収が他の worktree に及び、利用者ファイル・別 worktree・共有 Git を削除または変更する。 | 表 | 903 | 15,891 |
| 691 | `test_abandon_refuses_records_of_another_worktree` | 1 | 17 | 別 worktree の管理レコードを自分のものとして abandon で削除し、利用者ファイル・別 worktree・共有 Git を削除または変更する。 | 表 | 904 | 15,908 |
| 692 | `test_a_repeated_signal_does_not_cut_the_end_record` | 1 | 28 | シグナルの重複で終了記録が欠け、未終了の試行を回収可能と誤判定して worktree を削除する。 | 表 | 905 | 15,936 |
| 693 | `test_sessions_keep_the_open_pr_when_fork_and_upstream_share_number_branch_and_head` | 1 | 34 | fork と upstream が同番号・同 branch・同 HEAD のとき、開いている PR の session を回収可能と誤判定して削除する。 | 表 | 906 | 15,970 |
| 694 | `test_sessions_keep_a_version6_session` | 1 | 17 | 旧 state（repository 不明）の session を回収可能とみなし、別 PR の worktree を削除・レビューを上書きする。 | 表 | 907 | 15,987 |
| 695 | `test_sessions_keep_when_gh_fails` | 2 | 21 | gh の失敗（PR 不明・gh なし）で PR の状態が不明な session を、回収可能と誤判定して worktree を削除する。 | 表 | 909 | 16,008 |
| 696 | `test_sessions_keep_when_gh_reports_another_number` | 1 | 11 | gh が別番号の PR を返してもその状態で session を削除可能と誤判定する。 | 表 | 910 | 16,019 |
| 697 | `test_sessions_keep_a_session_without_state` | 2 | 20 | state の無い session を回収可能と誤判定して worktree を削除する。 | 表 | 912 | 16,039 |
| 698 | `test_sessions_keep_a_locked_worktree` | 1 | 12 | lock された worktree を回収可能と誤判定して削除し、利用者ファイル・別 worktree・共有 Git を削除または変更する。 | 表 | 913 | 16,051 |
| 699 | `test_cleanup_keeps_v7_session_when_saved_candidates_are_missing` | 1 | 10 | 保存した候補一覧が無い v7 session を回収し、利用者ファイル・別 worktree・共有 Git を削除または変更する。 | 表 | 914 | 16,061 |
| 700 | `test_save_allows_another_review_destination_to_change`（正しく通る例） | 1 | 585（準備 572 を含む） | 正例: 自分の保存先以外の変化で誤って拒否しない。対の拒否は、保存先の変更・改ざん・先行 session の上書きを見逃す損害を防ぐ。 | 表・重さは #236 | 915 | 16,646 |

`.agents/skills/pr-review/tests/test_review_run.py`（`pr-review-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 701 | `test_complete_rejects_changed_draft_before_writing_anywhere` | 1 | 16 | state の draft を利用者ファイルへ差し替えても complete が書き込み、保護範囲外を変更する。 | 表 | 916 | 16,662 |
| 702 | `test_prepare_binds_request_and_local_records` | 1 | 18 | request・ローカルの判断記録・PR・HEAD・base の結び付けを誤り、誤った対象をレビュー・保存する。 | 表 | 917 | 16,680 |
| 703 | `test_prepare_preserves_shared_refs_and_other_worktree_base_refs` | 2 | 46 | base fetch や prepare・complete が共有 ref・他 worktree の base ref を変更し、利用者の Git ref を変える。 | 表 | 919 | 16,726 |
| 704 | `test_prepare_failure_after_base_fetch_keeps_shared_refs_unchanged` | 1 | 21 | base fetch の後に merge-base が失敗する経路でも共有 ref を変更し、利用者の Git ref を変える。 | 表・重さは #236 | 920 | 16,747 |
| 705 | `test_prepare_refuses_external_pr_without_explicit_checkout` | 1 | 8 | 明示した checkout なしで外部 PR の checkout を探索・clone し、誤った対象をレビュー・保存する。 | 表 | 921 | 16,755 |
| 706 | `test_prepare_parallel_sessions_pin_their_own_base` | 1 | 25 | 並行 session が互いの base を上書きし、誤った base でレビュー・保存する。 | 表 | 922 | 16,780 |
| 707 | `test_prepare_rejects_wrong_request_workdir_and_shape` | 2 | 11 | work_dir や result_shape の誤った request を受理し、誤った対象をレビュー・保存する。 | 表 | 924 | 16,791 |
| 708 | `test_refused_complete_records_complete_and_a_retry_succeeds` | 1 | 26 | 拒否された complete の失敗記録・再試行の成功が崩れ、誤った対象をレビュー・保存する、または利用者の Git ref・ファイルを変える。 | 表 | 925 | 16,817 |
| 709 | `test_symlinked_review_directory_refuses_to_start` | 1 | 15 | symlink の reviews ディレクトリ経由で、保護範囲外へ書く。 | 表 | 926 | 16,832 |
| 710 | `test_attach_runner_skips_files_outside_the_record_layout` | 1 | 25 | symlink 階層・形式違い・別 PR 番号の記録を書き先にし、保護範囲外へ書く。 | 表 | 927 | 16,857 |
| 711 | `test_helper_write_exceptions_grant_git_data_only_where_the_helper_writes_it` | 4 | 59 | 固定した書込許可範囲を広げ、writes=false の担当が利用者 Git を変更できる。 | 表 | 931 | 16,916 |
| 712 | `test_complete_returns_actual_compare_and_delete_outcome` | 3 | 25 | 既に無い ref や他 session が付け替えた ref を、deleted など実際と違う結果でもっともらしく誤報告する。 | 表 | 934 | 16,941 |
| 713 | `test_upstream_runner_uses_validated_upstream_remote` | 1 | 55 | 検証済みの upstream remote でなく origin を使い、誤った対象をレビュー・保存する。 | 表 | 935 | 16,996 |
| 714 | `test_complete_refuses_skill_changed_after_prepare` | 1 | 17 | prepare の後に SKILL.md が変わっても complete が保存し、変更された指示で作ったレビューを公開する。 | 表 | 936 | 17,013 |
| 715 | `test_ordinary_depth_one_checkout_reviews_whole_pr_without_shared_history_changes` | 2 | 484（`.agents/skills/pr-review/tests/conftest.py` 23・準備 399 を含む） | 浅い checkout の共有履歴（shallow 境界・ref・FETCH_HEAD）を変更する、または PR の一部の差分だけをレビューする。 | 表 | 938 | 17,497 |

`.agents/scripts/tests/test_agent_tmp.py`（`review-helper-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 716 | `test_make_session_dir_rejects_invalid_topic` | 3 | 7 | topic で tmp/agents の外（../ や / 入り、隠し dir）に作成してしまう | 表 | 941 | 17,504 |
| 717 | `test_make_session_dir_refuses_when_tmp_is_not_ignored` | 1 | 6 | git の無視の外に作ると、スクラッチの記録が git に入る（記録が git に入る範囲） | 表・重さは #236 | 942 | 17,510 |
| 718 | `test_make_session_dir_refuses_symlink_into_unignored_directory` | 1 | 14 | symlink 先が追跡対象（無視されない）ディレクトリでも、そこへ書き込む | 表 | 943 | 17,524 |
| 719 | `test_make_session_dir_creates_unique_dirs_under_tmp_agents`（正しく通る例） | 1 | 12 | 対の守り: 正しい topic では一意な dir を作れる（拒否側は tmp/agents の外・追跡対象への作成） | 表・重さは #236 | 944 | 17,536 |
| 720 | `test_cli_mkdir_from_worktree_copy_writes_parent_tmp`（正しく通る例） | 1 | 122（準備 107 を含む） | 対の守り: worktree の写しからでも親の tmp に作れる（拒否側は tmp 外・追跡対象への書き込み） | 表・重さは #236 | 945 | 17,658 |

`.agents/scripts/tests/test_review_records.py`（`review-helper-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 721 | `test_invalid_records_are_rejected` の `empty-seats`・`no-rerun-seat` | 2 | 5（関数 5 を含む） | 再レビューしていない記録（空の seats、再実行したレビュアー無し）を通し、未検証のマージに進む | 表 | 947 | 17,663 |
| 722 | `test_collect_records_reads_trusted_round_status_comments_only` | 1 | 32 | 信頼できない投稿者の状況コメントを記録として読み、記録を偽造される（信頼境界） | 表 | 948 | 17,695 |
| 723 | `test_collect_records_does_not_trust_other_or_empty_logins` | 3 | 16 | 他人・author 無し・空同士の一致で信頼し、偽の記録を読む | 表 | 951 | 17,711 |
| 724 | `test_collect_records_rejects_markers_that_disagree_with_the_record` | 1 | 10 | マーカーと記録が食い違うコメントを、別の計画者の記録として読む | 表 | 952 | 17,721 |
| 725 | `test_round_records_pass_validation`（正しく通る例） | 1 | 3 | 対の守り: 記録の検査が正しい 2 つの記録を拒否しない（拒否側は再レビューなしの記録での未検証マージ） | 表・重さは #236 | 953 | 17,724 |
| 726 | `test_stopped_round_preserves_category_and_pending_decisions`（正しく通る例） | 1 | 495（準備 485 を含む） | 対の守り: 停止サイクルの空の seats と具体的な stop_reason を許す（拒否側は再レビューなしの記録） | 表・重さは #236 | 954 | 18,219 |

`.agents/scripts/tests/test_review_target.py`（`review-helper-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 727 | `test_validate_repository_rejects_unsafe_names` | 3 | 5 | owner/repo の名前（.. や ../x、多段）で reviews/ の外へ書き込む | 表 | 957 | 18,224 |
| 728 | `test_resolve_stops_without_checkout_and_does_not_clone` | 1 | 10 | checkout が無いとき勝手に clone し、作業ツリーを変える | 表 | 958 | 18,234 |
| 729 | `test_require_parent_root_needs_ignored_reviews` | 1 | 10 | reviews/ を無視していない親を許し、レビュー結果が git に入る（記録が git に入る範囲） | 表・重さは #236 | 959 | 18,244 |
| 730 | `test_require_parent_root_rejects_linked_worktree` | 1 | 9 | linked worktree を親にし、worktree の削除でレビュー結果を失う | 表 | 960 | 18,253 |
| 731 | `test_fetch_pull_head_preserves_tracking_refs_tags_and_fetch_head` | 2 | 25 | 利用者の ref・tag・FETCH_HEAD を壊す。head が動いたときに拒否しない | 表 | 962 | 18,278 |
| 732 | `test_resolve_number_uses_parent_origin`（正しく通る例） | 1 | 246（準備 234 を含む） | 対の守り: 番号だけの指定で親の origin を使える（拒否側は勝手な clone・別リポジトリの選択） | 表・重さは #236 | 963 | 18,524 |

`.agents/skills/review-fix-planning/tests/test_finalize.py`（`review-helper-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 733 | `test_no_fix_result_requires_post_merge_confirmation_and_issue_update` | 1 | 13 | マージ方式・--match-head-commit・Issue close の順序を誤り、未確認のままマージ・close する | 表 | 964 | 18,537 |
| 734 | `test_missing_or_wrong_verification_stops_before_network` | 4 | 16 | 検証の記録が未検証・コマンド 0 件・失敗・base 不明でも最終化し、未検証のままマージする | 表 | 968 | 18,553 |
| 735 | `test_invalid_pr_state_does_not_post_or_merge` | 2 | 11 | head が動いた PR・draft の PR に投稿・マージする | 表 | 970 | 18,564 |
| 736 | `test_public_ci_failure_or_absence_stops_without_waiting` | 3 | 10 | 公開 PR の CI が失敗・ERROR・不在でも、未検証のままマージする | 表 | 973 | 18,574 |
| 737 | `test_create_reso_world_ci_is_not_required_but_resoloop_ci_is` | 1 | 13 | 公開 PR を CI の確認なしでマージする | 表 | 974 | 18,587 |
| 738 | `test_repository_outside_the_merge_scope_stops_before_network` | 1 | 10 | マージしてよい範囲の外のリポジトリの PR をマージする | 表 | 975 | 18,597 |
| 739 | `test_comment_rejection_cannot_be_bypassed_with_manual_post` | 1 | 6 | 記録を投稿できないまま（手動投稿で迂回して）マージする | 表 | 976 | 18,603 |
| 740 | `test_moving_head_after_post_is_not_merged` | 1 | 5 | 投稿後に動いた別の head をマージする | 表 | 977 | 18,608 |
| 741 | `test_merge_command_success_without_merged_state_is_not_completion` | 1 | 5 | マージのコマンドが成功でも merged 状態が未確認のまま、完了と報告する | 表 | 978 | 18,613 |
| 742 | `test_posted_record_counts_only_from_a_writer_or_the_authenticated_user` | 3 | 15 | 書き込み権限も認証もない投稿者の記録を、投稿済みの記録として採用する | 表 | 981 | 18,628 |
| 743 | `test_gh_failure_detail_is_kept_without_tokens_or_stop_reason` | 1 | 16 | gh の失敗の出力のトークンの形の文字列を伏せない、または stop_reason に gh の出力を入れ、判断の記録に漏らす | #236 の判定 | 982 | 18,644 |
| 744 | `test_unusable_result_path_stops_before_gh` | 1 | 22 | 結果ファイルの symlink で、別セッションの結果を上書きする | 表 | 983 | 18,666 |
| 745 | `test_foreign_or_malformed_closing_issue_is_never_closed` | 1 | 6 | 別リポジトリや不正な形の Issue を close する | 表 | 984 | 18,672 |
| 746 | `test_spec_commit_compare_must_be_one_spec_file_on_the_reviewed_head` | 7 | 7 | 検証した head の上の Spec 1 ファイルでない commit を、Spec の commit として未検証のままマージする | 表 | 991 | 18,679 |
| 747 | `test_spec_commit_compare_failure_after_the_push_waits_and_the_rerun_merges` | 1 | 14 | 比較の失敗でも未検証のままマージする、または待たず停止して、修正不要の PR をマージできない | #236 の判定 | 992 | 18,693 |
| 748 | `test_spec_commit_requires_the_identical_record_already_posted` | 3 | 15 | 同一の記録が投稿されていないのに、Spec の commit をマージする | 表 | 995 | 18,708 |
| 749 | `test_invalid_spec_commit_stops_before_network` | 1 | 13 | 他リポジトリの PR に Spec の commit を使ってマージする | 表 | 996 | 18,721 |
| 750 | `test_spec_commit_merged_with_a_changed_diff_is_not_completed` | 1 | 7 | マージ済みでも diff を確かめず、Spec の commit の変更を完了と報告する | 表 | 997 | 18,728 |
| 751 | `test_base_moved_after_verification_is_not_merged_until_the_new_base_is_verified` | 2 | 18 | 検証後に進んだ base へ、新しい base を検証せずにマージする | 表 | 999 | 18,746 |
| 752 | `test_base_moved_after_posting_is_not_merged_and_the_rerun_updates_the_comment` | 1 | 15 | 投稿後に進んだ base へマージする。再実行でコメントを更新しない | 表 | 1,000 | 18,761 |
| 753 | `test_unreadable_base_tip_stops_without_merging` | 2 | 15 | base の先端を別ブランチの応答で読む、要求失敗のままでも、base を確かめずにマージする | 表 | 1,002 | 18,776 |
| 754 | `test_retargeted_base_is_compared_with_the_new_base_branch` | 1 | 9 | 付け替え後の base ではなく元の base で照合してマージする | 表 | 1,003 | 18,785 |
| 755 | `test_merge_commit_parent_must_be_the_verified_base` | 2 | 21 | 検証した base と違う親で作られたマージ（#206）を、検証済みと報告する | 表 | 1,005 | 18,806 |
| 756 | `test_only_a_record_verified_on_the_merge_commit_completes_the_issue_update` | 1 | 19 | 同じ記録の再実行で、merge commit を検証していないのに Issue を閉じる | 表 | 1,006 | 18,825 |
| 757 | `test_manual_merge_on_a_moved_base_is_merged_but_not_completed` | 1 | 9 | base が進んだ後の手動マージでも Issue を閉じる | 表 | 1,007 | 18,834 |
| 758 | `test_unreadable_merge_commit_is_merged_but_not_completed` | 3 | 21 | merge commit を読めない（欠落・要求失敗・不一致）のに Issue を閉じる | 表 | 1,010 | 18,855 |
| 759 | `test_spec_commit_merges_the_spec_head_after_the_record_was_posted`（正しく通る例） | 1 | 462（準備 449 を含む） | 対の守り: Spec の commit を --match-head-commit にしてマージできる（拒否側は未検証の commit のマージ） | 表 | 1,011 | 19,317 |

`.agents/skills/review-fix-planning/tests/test_review_fix_planning_skill_contract.py`（`review-helper-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 760 | `test_fix_context_stops_before_later_mutation` | 5 | 21 | 親・base・文書 branch・HEAD の曖昧さや helper の欠落のまま進み、誤った対象を破壊する | 表 | 1,016 | 19,338 |
| 761 | `test_fix_context_verifies_known_repository_worktree_membership` | 3 | 11 | 既知リポジトリの worktree の所属を確かめず、別の checkout を対象にする | 表 | 1,019 | 19,349 |
| 762 | `test_status_snippet_revalidates_before_comment_mutation` | 2 | 32 | コメント変更の直前に再検証せず、誤った対象のコメントを変更する | 表 | 1,021 | 19,381 |
| 763 | `test_fix_context_validates_effective_push_destinations` | 3 | 18 | 誤った push 先（分割・単一の取り違え・fallback）を通す | 表 | 1,024 | 19,399 |
| 764 | `test_fix_context_uses_real_parent_helper_from_external_cwd`（正しく通る例） | 3 | 131（準備 124 を含む） | 対の守り: 外部 cwd・3 シェルで親の helper を正しく呼べる（拒否側は誤った対象への破壊操作） | 表 | 1,027 | 19,530 |

`.agents/skills/review-fix-planning/tests/test_run_roles.py`（`review-helper-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 765 | `test_external_review_roles_list_their_write_exceptions_with_the_role` | 1 | 23 | 外部担当への書き込み例外の範囲（sandbox の境界）が過大になる | 表 | 1,028 | 19,553 |
| 766 | `test_only_the_externally_assigned_role_lists_exceptions` | 2 | 9 | self の役割にも書き込み例外を付ける（sandbox の境界） | 表 | 1,030 | 19,562 |
| 767 | `test_self_review_never_grants_a_shallow_checkout_git_under_ambient_git_routing` | 1 | 29 | 環境の GIT_DIR で浅い checkout を完全と誤判定し、writes=false の担当に利用者の Git の書き込みを許可する | #236 の判定 | 1,031 | 19,591 |
| 768 | `test_existing_lock_does_not_start_or_erase_another_call` | 1 | 7 | 他の呼び出しのロックを消す、または競合して起動する（競合の防止） | 表 | 1,032 | 19,598 |
| 769 | `test_invalid_writable_review_role_never_consumes_budget` | 1 | 278（準備 272 を含む） | 書き込み可（writes=true）のレビューの役割を拒否せず、書き込めるレビュアーが起動し得る | 表 | 1,033 | 19,876 |

`.agents/skills/review-fix-planning/tests/test_upsert_pr_comment.py`（`review-helper-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 770 | `test_only_trusted_authors_are_matched` | 6 | 18 | 信頼しない投稿者のコメントを書き換える | 表 | 1,039 | 19,894 |
| 771 | `test_upsert_stops_when_gh_resolves_a_different_repository` | 1 | 14 | gh が別リポジトリの PR を解決しても、そこへコメントを書き込む | 表 | 1,040 | 19,908 |
| 772 | `test_record_less_upsert_updates_own_login_comment_and_ignores_untrusted` | 1 | 22 | 信頼しない同マーカーのコメントを更新する。自分の login のコメントを更新できない（正しく通る例を含む） | 表 | 1,041 | 19,930 |
| 773 | `test_authenticated_login_strips_newline_and_rejects_blank` | 1 | 9 | 信頼する投稿者を gh の認証先で決めず、PR の作者などで別の利用者を信頼する | 表・重さは #236 | 1,042 | 19,939 |
| 774 | `test_records_post_creates_a_new_comment_for_the_next_round` | 1 | 18 | 次のサイクルで前のサイクルの記録を上書きし、記録を失う | 表 | 1,043 | 19,957 |
| 775 | `test_records_post_updates_own_contributor_round_comment_and_ignores_forged_ones` | 1 | 15 | 偽造されたサイクルのコメントを、更新・照合に使う | 表 | 1,044 | 19,972 |
| 776 | `test_records_post_does_not_read_rounds_of_other_contributors` | 1 | 10 | 他人が書いたサイクルの記録を、履歴に使う | 表 | 1,045 | 19,982 |
| 777 | `test_records_post_stops_when_another_agent_recorded_the_round` | 1 | 5 | 他担当が記録したサイクルの記録を上書きする | 表 | 1,046 | 19,987 |
| 778 | `test_records_post_creates_a_round_comment`（正しく通る例） | 1 | 322（準備 309 を含む） | 対の守り: 記録付き投稿の正しい形で投稿できる（拒否側は他担当の記録の上書き・別 PR・古い HEAD） | 表・重さは #236 | 1,047 | 20,309 |

`.agents/skills/review-verify/tests/test_dispatch.py`（`review-helper-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 779 | `test_external_fix_check_request_lists_its_write_exceptions` | 1 | 17 | 外部担当に与える書込み許可の範囲（サンドボックスの境界）が過大になる | 表 | 1,048 | 20,326 |
| 780 | `test_accept_rejects_a_different_pr_without_changing_outputs` | 2 | 23 | 別 PR の結果で保存先を上書きする（記録の上書き） | 表 | 1,050 | 20,349 |
| 781 | `test_accept_uses_the_frozen_pr_after_the_original_verified_file_changes` | 2 | 20 | 可変な元ファイルの書き換えで、対象 PR を差し替えられる | 表 | 1,052 | 20,369 |
| 782 | `test_accept_rejects_a_payload_that_differs_from_the_tool_output` | 6 | 25 | ツール出力と異なる payload（key・terms・candidates・fix_ids・形・判定）を受理する | 表 | 1,058 | 20,394 |
| 783 | `test_accept_rejects_outside_changes_and_dispatch_exits_1_for_them` | 1 | 11 | 呼び出し元 repository への外部書込みを受理する | 表 | 1,059 | 20,405 |
| 784 | `test_accept_rejects_an_unconfirmed_stop` | 1 | 7 | 停止が確認できない実行の結果を受理する | 表 | 1,060 | 20,412 |
| 785 | `test_accept_rejects_a_failed_run` | 1 | 4 | 失敗した実行の結果を受理する | 表 | 1,061 | 20,416 |
| 786 | `test_review_directory_changes_are_rejected_before_publishing` | 5 | 53 | 保存先の改ざん（gitignore 内の作成・外の上書き・削除・chmod・symlink）を、公開前に拒否しない | 表 | 1,066 | 20,469 |
| 787 | `test_symlink_verified_directory_is_rejected_without_writing_referent` | 1 | 10 | verified が symlink のとき、その参照先へ書き込む | 表 | 1,067 | 20,479 |
| 788 | `test_accept_rejects_a_late_verified_directory_symlink` | 1 | 7 | 起動後に verified が symlink になっても、参照先へ書き込む | 表 | 1,068 | 20,486 |
| 789 | `test_unusable_review_directory_is_rejected_before_launch_or_any_state_change` | 2 | 31 | 保存できない保存先で 1800 秒の担当を起動し、状態を変える（#177） | 表 | 1,070 | 20,517 |
| 790 | `test_unavailable_review_audit_never_means_unchanged` | 1 | 26 | 監査不能を無変更と扱い、内容を stderr に出す | 表 | 1,071 | 20,543 |
| 791 | `test_initial_ancestor_symlink_rejects_without_launch_or_any_state_change` | 1 | 16 | 祖先が symlink のまま担当を起動し、状態を変える | 表 | 1,072 | 20,559 |
| 792 | `test_ancestor_replaced_after_dispatch_is_not_unchanged_or_accepted` | 1 | 11 | 起動後に祖先を差し替えても、無変更と扱い受理する | 表 | 1,073 | 20,570 |
| 793 | `test_accept_rechecks_destination_after_validation_before_creating_any_output` | 3 | 37 | 検証中の保存先の差し替え・既存結果の上書きを防がない（記録の上書き） | 表 | 1,076 | 20,607 |
| 794 | `test_accept_saves_the_tool_output_unchanged_with_the_observed_verifier`（正しく通る例） | 1 | 24 | 受理の正例: ツール出力を無改変で保存し、観測した verifier を記録する（対の拒否は別 PR・外部書込み等） | 表 | 1,077 | 20,631 |
| 795 | `test_accept_allows_candidates_and_terms_the_verifier_appended`（正しく通る例） | 1 | 16 | 対の守り: verifier が追記した候補・語は許す（拒否側はツール出力と異なる payload の受理） | 表・重さは #236 | 1,078 | 20,647 |
| 796 | `test_unchanged_existing_results_and_temporary_probe_outputs_are_allowed`（正しく通る例） | 1 | 1,353（準備 837・準備 503 を含む） | 対の守り: 変更なしの既存の結果と一時の probe 出力は許す（拒否側は保存先の改ざん） | 表・重さは #236 | 1,079 | 22,000 |

`.agents/skills/review-verify/tests/test_evaluation.py`（`review-helper-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 797 | `test_documented_fixture_isolates_subprocesses_from_host_git_state` の `git-dir`・`home-hooks`・`xdg-signing`・`bash-env`・`env` | 5 | 0 | ホストの Git の index 書き換え・フック・署名・シェル起動ファイルが評価の子に混入する | 表 | 1,084 | 22,000 |
| 798 | `test_documented_fixture_isolates_subprocesses_from_host_git_state` の `clean`（正しく通る例） | 1 | 149（関数 98・`.agents/skills/review-verify/tests/conftest.py` 33・準備 18 を含む） | 対の守り: 隔離を外さない通常経路が動く（拒否側はホストの Git・フック・署名・シェル起動ファイルの混入） | 表・重さは #236 | 1,085 | 22,149 |

`.agents/skills/agent-handoff/tests/test_agent_handoff_skill_contract.py`（`skill-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 799 | `test_schema_requires_git_branch_head_status_in_json_fields` | 1 | 6 | worktree・branch・head・status を引き継がず、別 checkout の変更を対象として扱う | 表 | 1,086 | 22,155 |
| 800 | `test_documents_and_code_have_separate_schema_fields` | 1 | 39（準備 30 を含む） | 文書とコードの checkout を混同し、別リポジトリへ commit・push する | 表 | 1,087 | 22,194 |

`.agents/skills/issue-to-pr/tests/test_implement_task.py`（`skill-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 801 | `test_task_request_rejects_invalid_fields` | 3 | 11 | allowed_files のパス脱出・偽装で、担当外ファイルを取り込む | 表 | 1,090 | 22,205 |
| 802 | `test_directory_entry_matches_by_path_segment` | 1 | 108（準備 100 を含む） | tests/ が tests_other/ や tests に誤一致し、担当外の変更を許可済みと判定する | 表 | 1,091 | 22,313 |

`.agents/skills/issue-to-pr/tests/test_implement_task_run.py`（`skill-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 803 | `test_uncommitted_report_mismatch_is_rejected` | 1 | 13 | 報告に無いファイルを helper が commit し、未監査の変更を取り込む | 表 | 1,092 | 22,326 |
| 804 | `test_commit_with_leftover_changes_is_rejected` | 1 | 7 | commit 後に残る未報告変更を成功と扱い、取り込みや削除でデータを失う | 表 | 1,093 | 22,333 |
| 805 | `test_change_outside_allowed_files_is_rejected` | 1 | 9 | 最終差分にある担当外ファイルを取り込む | 表 | 1,094 | 22,342 |
| 806 | `test_intermediate_commit_outside_allowed_files_is_rejected` | 1 | 10 | 途中の commit にだけ残る担当外ファイルが、ff 取り込みで履歴に入る | 表 | 1,095 | 22,352 |
| 807 | `test_merge_commit_in_range_is_rejected` | 1 | 18 | merge commit の親の取り方で、未監査の変更が紛れ込む | 表 | 1,096 | 22,370 |
| 808 | `test_commit_not_descending_from_revision_is_rejected` | 1 | 12 | 別の履歴の commit を feature に取り込む | 表 | 1,097 | 22,382 |
| 809 | `test_reported_commit_other_than_head_is_rejected` | 1 | 7 | 報告 SHA と監査した worktree の HEAD が違うまま取り込む | 表 | 1,098 | 22,389 |
| 810 | `test_outside_change_is_rejected` | 1 | 9 | runner worktree の外側に生じた変更を見落として成功と報告する | 表 | 1,099 | 22,398 |
| 811 | `test_recorded_invalid_payload_is_rejected_on_reassessment` | 1 | 11 | 保存済み記録が壊れた後でも、再評価で未検証の payload を取り込む | 表 | 1,100 | 22,409 |
| 812 | `test_fallback_success_is_assessed_on_its_own_attempt` | 1 | 10 | 失敗した一次担当の作業領域を成功した代替担当のものと取り違え、別の変更を採用する | 表 | 1,101 | 22,419 |
| 813 | `test_unconfirmed_stop_fails` | 1 | 10 | 停止未確認でまだ書き込み中の担当を、成功として取り込む | 表 | 1,102 | 22,429 |
| 814 | `test_run_refuses_main_checkout` | 1 | 3 | feature 用の処理を親の main checkout に適用し、main を動かす | 表 | 1,103 | 22,432 |
| 815 | `test_rename_counts_both_paths` | 2 | 12 | rename の移動元か移動先の片方しか監査せず、担当外への移動を許す | 表 | 1,105 | 22,444 |
| 816 | `test_accept_commits_uncommitted_changes_with_message` | 1 | 15 | helper commit が未監査ファイルや別の親を含む、または記録と異なる commit を取り込む | 表 | 1,106 | 22,459 |
| 817 | `test_accept_reassesses_current_state` | 1 | 8 | run 後に worktree が変化しても、古い監査結果のまま取り込む | 表 | 1,107 | 22,467 |
| 818 | `test_accept_refuses_moved_or_dirty_feature` | 2 | 13 | run と accept の間に feature が変わった場合の上書き・別履歴への取り込み | 表 | 1,109 | 22,480 |
| 819 | `test_cleanup_retains_dirty_worktree` | 1 | 11 | 未 commit・未追跡の作業物を cleanup が消してデータを失う | 表 | 1,110 | 22,491 |
| 820 | `test_cleanup_retains_unstopped_or_sensitive_attempt` | 2 | 18 | 停止未確認や秘匿情報のある担当領域を消し、実行中の作業・調査用データを失う | 表 | 1,112 | 22,509 |
| 821 | `test_accept_fast_forwards_agent_commit`（正しく通る例） | 1 | 13 | 監査した SHA だけを ff 取り込みする正常例。拒否テスト群が『何でも拒否』の実装で通るのを防ぐ | 表 | 1,113 | 22,522 |
| 822 | `test_cleanup_removes_worktree_and_run_dir`（正しく通る例） | 1 | 329（準備 258・`tools/test_support/__init__.py` 11・`tools/test_support/plugin.py` 31・`tools/test_support/texts.py` 16 を含む） | cleanup 保持テスト群の正例。無いと『何も消さない』実装で通り、正常な領域の撤去が壊れても気付けない | 表 | 1,114 | 22,851 |

`.agents/skills/issue-to-pr/tests/test_resolve_issue.py`（`skill-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 823 | `test_rejects_input_before_looking_up_issue` | 2 | 11 | 許可外のリポジトリやホストを先に拒否せず、別対象の Issue で作業を進める | 表 | 1,116 | 22,862 |
| 824 | `test_rejects_malformed_arguments_before_looking_up_issue` | 1 | 14 | 複数 Issue の入力から一方を黙って選び、別 Issue の作業・PR を作る | 表 | 1,117 | 22,876 |
| 825 | `test_number_with_unusable_origin_stops` | 1 | 11 | #N の origin が別ホストでも GitHub と誤認し、別リポジトリの Issue を選ぶ | 表 | 1,118 | 22,887 |
| 826 | `test_origin_with_credentials_stops_without_printing_them` | 1 | 14 | origin に入った資格情報をエラーメッセージへ出して漏らす | 表 | 1,119 | 22,901 |
| 827 | `test_rejects_mismatched_or_closed_response` の `CLOSED-42-None`・`OPEN-99-None`・`OPEN-42-https://github.com/usaturn/resoloop/issues/42`・`OPEN-42-https://github.com.evil.test/usaturn/create-reso-world/issues/42` | 4 | 0 | GitHub 応答の状態や対象を信用し、閉じた Issue・別 Issue・別リポジトリで作業を始める | 表 | 1,123 | 22,901 |
| 828 | `test_rejects_mismatched_or_closed_response` の `OPEN-42-https://github.com/usaturn/create-reso-world/pull/42` | 1 | 16（関数 16 を含む） | OPEN の PR 応答を Issue として受け付け、別の対象に branch と PR を作る | 表・重さは #236 | 1,124 | 22,917 |
| 829 | `test_reports_gh_failure_without_trying_another_repository` | 1 | 7 | 404 後に別 repo を推測して再検索し、もっともらしい別 Issue を選ぶ | 表 | 1,125 | 22,924 |
| 830 | `test_resolves_supported_forms_without_changing_git` の `https://github.com/usaturn/resoloop/issues/42-None-usaturn/resoloop`・`usaturn/resoloop-meshy#42-None-usaturn/resoloop-meshy`・`#42-None-usaturn/create-reso-world`（正しく通る例） | 3 | 0 | 許可 owner/repo の固定値と #N の origin 選択が誤り、別リポジトリで branch/PR を作る。拒否群の正例を兼ねる | 表 | 1,128 | 22,924 |
| 831 | `test_resolves_supported_forms_without_changing_git` の `#42-git@github.com:usaturn/resoloop.git-usaturn/resoloop`（正しく通る例） | 1 | 161（関数 35・準備 126 を含む） | #N が origin でなく固定 repo に解決され、別のリポジトリを選ぶ。拒否群の正例を兼ねる | 表・重さは #236 | 1,129 | 23,085 |

`.agents/skills/monitoring-long-tasks/tests/test_task_watch_core.py`（`skill-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 832 | `test_new_investigation_in_reserve_is_stopped` | 1 | 5 | 保存用の予約時間に新たな調査を始め、保存時間を使い切って途中結果を失う | 表 | 1,130 | 23,090 |
| 833 | `test_records_before_the_reserve_offset_are_not_investigation` | 1 | 23 | finalize 要求直後の保存中の記録を新規調査と誤認して停止し、途中結果を失う | 表 | 1,131 | 23,113 |
| 834 | `test_line_longer_than_read_limit_is_skipped_and_later_records_are_read` | 1 | 70（準備 57 を含む） | 長い 1 行で読み取りが止まり、後続の安全失敗を取り込まず見逃して続行する | 表 | 1,132 | 23,183 |

`.agents/skills/monitoring-long-tasks/tests/test_task_watch_process.py`（`skill-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 835 | `test_unstoppable_worker_is_held_and_left_running` | 1 | 12 | TERM を無視する worker を停止済みと誤報し、残留プロセスを見逃して作業を終える | 表 | 1,133 | 23,195 |
| 836 | `test_escalate_kill_confirms_stop_of_term_ignoring_worker` | 1 | 16 | kill へ進めた後、実際は生存しているのに confirmed=true と誤報する | 表 | 1,134 | 23,211 |
| 837 | `test_undeclared_stop_never_signals` | 1 | 8 | 宣言されていない停止 signal を実 worker に送る | 表 | 1,135 | 23,219 |
| 838 | `test_item_written_right_after_finalize_request_is_within_grace` | 1 | 16 | finalize 要求直後の猶予中の記録を違反扱いし、成果保存中の worker を止めて結果を失う | 表 | 1,136 | 23,235 |
| 839 | `test_records_written_by_the_group_after_exit_reach_the_final` | 1 | 8 | leader の exit 0 後に child が記録した安全失敗を読み損ね、失敗を成功と報告する | 表 | 1,137 | 23,243 |
| 840 | `test_processes_left_in_the_group_after_exit_are_held` | 1 | 15 | leader の終了だけで完了扱いし、child が生きたまま controller が作業を終える | 表 | 1,138 | 23,258 |
| 841 | `test_status_sees_the_group_after_the_watcher_is_killed` | 1 | 28 | watcher が SIGKILL された後に child の生存を見落とし、動いている対象を停止済みとして扱う | 表 | 1,139 | 23,286 |
| 842 | `test_stop_refuses_unrelated_and_caller_pids` | 1 | 30 | stale・再利用・caller の PID に signal を送り、無関係のプロセスを破壊する | 表 | 1,140 | 23,316 |
| 843 | `test_relative_state_dir_round_trip` | 1 | 18 | 相対 state path を別の cwd 基準で解決し、別 watch の状態を読んだり対象を止めたりする | 表 | 1,141 | 23,334 |
| 844 | `test_existing_state_is_not_overwritten` | 1 | 9 | 誤った引数が既存の state directory を上書きし、監視記録を失う | 表 | 1,142 | 23,343 |
| 845 | `test_operator_stop_confirms_and_reports_operator`（正しく通る例） | 1 | 222（`.agents/skills/monitoring-long-tasks/tests/fake_worker.py` 91・準備 113 を含む） | PID 検証の拒否テストの正例。operator 停止で watcher の退出を確かめて確認済みと記録し、虚偽の停止確認を防ぐ | 表 | 1,143 | 23,565 |

`.agents/skills/repo-cleanup-after-merge/tests/test_detached_update.py`（`skill-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 846 | `test_updates_to_detached_origin_main_without_changing_local_refs` | 3 | 15 | 更新時にローカル main・作業 branch を作成・移動し、利用者の ref と履歴が変わる | 表 | 1,146 | 23,580 |
| 847 | `test_existing_main_is_retained_without_ref_or_reflog_updates` | 2 | 20 | 既存 main の commit・reflog を動かし、利用者が持つ履歴を失う | 表 | 1,148 | 23,600 |
| 848 | `test_main_held_by_another_worktree_does_not_block_or_mutate_that_tree` | 1 | 25 | 別 worktree の main と未保存・ignored 内容を更新元として扱い、その内容を壊す | 表・重さは #236 | 1,149 | 23,625 |
| 849 | `test_invocation_from_linked_project_targets_main_root_not_callers_feature` | 1 | 16 | linked project からの実行で、呼び出し元 feature の HEAD・refs を動かす | 表・重さは #236 | 1,150 | 23,641 |
| 850 | `test_branch_deletion_refuses_a_branch_not_merged_into_origin_main` | 1 | 17 | 未マージ branch を -D で消し、利用者の commit を失う | 表 | 1,151 | 23,658 |
| 851 | `test_unclean_or_unreadable_main_tree_stops_before_checkout_and_branch_deletion` | 3 | 22 | main の dirty・読取失敗を無視した checkout と branch 削除で、データ・履歴を失う | 表・重さは #236 | 1,154 | 23,680 |
| 852 | `test_ignored_file_collision_aborts_without_losing_data_or_branch_refs` | 1 | 14 | Git の checkout が無警告で上書きし得る ignored な利用者ファイルを失う | 表 | 1,155 | 23,694 |
| 853 | `test_steps_8_and_11_stop_when_main_root_is_unset_instead_of_using_callers_repo` | 1 | 40 | MAIN_ROOT が空のとき、別 repository の branch を削除・誤報する | 表・重さは #236 | 1,156 | 23,734 |
| 854 | `test_step8_recheck_for_not_fully_merged_discriminates_merge_state` | 1 | 47 | branch -d 拒否後の祖先確認を誤り、未マージ commit を -D で消す | 表・重さは #236 | 1,157 | 23,781 |
| 855 | `test_cleanup_keeps_the_forks_local_main_out_of_deletion_candidates` | 1 | 10 | fork のローカル main を削除候補に入れ、利用者所有の基準 branch を消す | 表・重さは #236 | 1,158 | 23,791 |
| 856 | `test_protected_world_update_from_linked_project_deletes_only_merged_branch`（正しく通る例） | 1 | 291（準備 249 を含む） | 保護領域の削除拒否テスト群の正例。無いと『変更を全て拒否』する実装でも群が通る。マージ済み branch だけ消す | 表・重さは #236 | 1,159 | 24,082 |

`.agents/skills/simplify-in-subagent/tests/test_simplify_in_subagent_contract.py`（`skill-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 857 | `test_interpolation_is_limited_to_the_target_line` | 1 | 16（準備 9 を含む） | $ARGUMENTS・$0〜$9 が対象行以外にあり、スキル本文のコードブロックまで展開されて意図外の対象で作業する | 表 | 1,160 | 24,098 |

`.agents/skills/stale-git-lock-recovery/tests/test_ff_merge_keep_untracked.py`（`skill-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 858 | `test_fast_forwards_and_restores_every_conflicting_file` | 1 | 12 | 退避した未追跡ファイル・symlink・mode を ff 後に復元せず、利用者データを失う | 表 | 1,161 | 24,110 |
| 859 | `test_failed_fast_forward_restores_everything_and_keeps_head` | 1 | 21 | merge 失敗時に退避ファイルを戻さず、HEAD とローカル編集を失う | 表 | 1,162 | 24,131 |
| 860 | `test_not_a_fast_forward_changes_nothing` | 1 | 11 | 非 fast-forward を通常 merge や破壊的更新で進める | 表・重さは #236 | 1,163 | 24,142 |
| 861 | `test_backup_failure_changes_nothing` | 1 | 10 | 退避先を作れないまま merge し、未追跡ファイルを失う | 表・重さは #236 | 1,164 | 24,152 |
| 862 | `test_inherited_git_dir_does_not_redirect_the_target` | 1 | 11 | 継承した GIT_DIR・GIT_WORK_TREE により、別 repository を更新する | 表・重さは #236 | 1,165 | 24,163 |
| 863 | `test_force_is_refused_without_changing_files` | 1 | 7 | --force を受け入れて破壊的更新をする | 表・重さは #236 | 1,166 | 24,170 |
| 864 | `test_ignored_file_on_an_added_path_is_kept` | 1 | 12 | Git が無警告で上書きする ignored ファイルの内容を失う | 表 | 1,167 | 24,182 |
| 865 | `test_interrupted_run_restores_files_and_reports_head` | 1 | 29 | シグナル後の後片付け漏れで退避ファイルが消える。HEAD の進みも誤報する | 表 | 1,168 | 24,211 |
| 866 | `test_failure_to_list_candidates_changes_nothing` | 1 | 20 | 衝突候補を列挙できないまま merge し、ignored ファイルを無警告で上書きする | 表 | 1,169 | 24,231 |
| 867 | `test_ignored_content_that_could_not_be_put_back_stops_the_run` | 3 | 40 | 復元先が塞がる ignored ファイル・directory・symlink を、先に merge して失う | 表 | 1,172 | 24,271 |
| 868 | `test_candidates_do_not_depend_on_the_callers_locale` | 1 | 25 | locale 差で候補を落とし、ignored ファイルが Git に無警告で上書きされる | 表・重さは #236 | 1,173 | 24,296 |
| 869 | `test_untracked_nested_repository_that_files_are_added_into_stops_the_run` | 1 | 18 | 未追跡の入れ子 repository 内の作業ファイルが、上流により上書きされる | 表 | 1,174 | 24,314 |
| 870 | `test_ignored_file_where_a_tracked_directory_was_stops_the_run` | 1 | 25 | index 上は directory でも実体が ignored ファイルの場合に、Git が無警告で削除する | 表・重さは #236 | 1,175 | 24,339 |
| 871 | `test_submodule_hidden_by_its_ignore_setting_is_still_seen` | 1 | 28 | .gitmodules の ignore に隠れた gitlink 追加で、ignored ファイルを失う | 表・重さは #236 | 1,176 | 24,367 |
| 872 | `test_ignored_file_in_a_submodule_turned_into_a_directory_stops_the_run` | 1 | 37 | submodule を通常 directory に変える際に、checkout 内の ignored log を上書きする | 表・重さは #236 | 1,177 | 24,404 |
| 873 | `test_ignored_file_on_the_way_inside_a_submodule_turned_into_a_directory_stops_the_run` | 1 | 16 | submodule 内で追加先の途中にある ignored ファイルを削除する | 表・重さは #236 | 1,178 | 24,420 |
| 874 | `test_submodule_turned_into_a_file_stops_the_run_while_its_checkout_has_content` | 2 | 18 | gitlink を file に変えるとき、checkout 全体とその未追跡内容を消す | 表 | 1,180 | 24,438 |
| 875 | `test_submodule_inside_a_directory_replaced_by_a_file_stops_the_run` | 2 | 13 | 親 directory が file へ変わる際に、子 submodule の未追跡内容を消す | 表・重さは #236 | 1,182 | 24,451 |
| 876 | `test_failing_directory_listing_stops_the_run` | 1 | 24 | directory 内の内容を確認できないまま更新を進め、未追跡データを失う | 表・重さは #236 | 1,183 | 24,475 |
| 877 | `test_added_submodule_over_an_existing_clone_still_fast_forwards`（正しく通る例） | 1 | 247（準備 225 を含む） | 停止系テスト群の正例。既存 clone を丸ごと置換せず、その未追跡ファイルを残して ff する | 表・重さは #236 | 1,184 | 24,722 |

`.agents/skills/stale-git-lock-recovery/tests/test_stale_git_lock_recovery_contract.py`（`skill-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 878 | `test_bash_snippets_do_not_run_destructive_git_commands` | 1 | 6 | 実行例が clean・reset --hard・強制 checkout を呼び、利用者の未保存データを失う | 表・重さは #236 | 1,185 | 24,728 |
| 879 | `test_skill_never_removes_the_lock_by_hand` | 1 | 5 | 手作業の rm が保持者検査を迂回して、生きたロックを消す | 表・重さは #236 | 1,186 | 24,733 |
| 880 | `test_live_holder_blocks_check_and_clear` | 1 | 16 | lsof で見える生きた保持者のロックを消し、進行中の Git 操作を壊す | 表 | 1,187 | 24,749 |
| 881 | `test_proc_scan_finds_holder_when_lsof_is_unavailable` | 1 | 14 | lsof 不在時に /proc の fd 保持者を見逃し、使用中のロックを消す | 表 | 1,188 | 24,763 |
| 882 | `test_unlistable_git_process_is_an_unknown_holder` | 1 | 16 | Git プロセスの fd を読めない場合に stale と誤認してロックを消す | 表 | 1,189 | 24,779 |
| 883 | `test_clear_removes_only_the_symlink_lock_not_its_target` | 1 | 16 | symlink の参照先にある利用者ファイルを削除・上書きする | 表 | 1,190 | 24,795 |
| 884 | `test_linked_worktree_lock_is_detected_at_its_own_path` | 1 | 14 | linked worktree のロックを main 側と取り違え、別のロックを操作する | 表・重さは #236 | 1,191 | 24,809 |
| 885 | `test_clear_refuses_force` | 1 | 6 | --force が保持者検査を迂回し、生きたロックを消す | 表・重さは #236 | 1,192 | 24,815 |
| 886 | `test_git_commit_holding_the_lock_without_an_fd_is_not_stale` | 2 | 48 | hook・editor 待ちで fd を閉じた commit の生きたロックを消し、コミットを壊す | 表 | 1,194 | 24,863 |
| 887 | `test_git_process_inside_the_repository_makes_the_holder_unknown` | 1 | 12 | 同一 worktree 内で fd を閉じた Git を見落とし、使用中のロックを消す | 表・重さは #236 | 1,195 | 24,875 |
| 888 | `test_git_process_pointing_at_the_repository_through_its_environment_is_unknown` | 4 | 22 | cwd が外でも GIT_* で対象 index に結び付く Git を見落とし、使用中のロックを消す | 表・重さは #236 | 1,199 | 24,897 |
| 889 | `test_git_process_pointing_at_the_repository_through_its_options_is_unknown` | 2 | 18 | argv の --git-dir・--work-tree で外部 cwd から対象を指す Git を見落とし、ロックを消す | 表・重さは #236 | 1,201 | 24,915 |
| 890 | `test_git_process_with_a_relative_repository_reference_cannot_be_ruled_out` | 1 | 14 | 起動後の cwd から相対 --git-dir を確定できず、保持中のロックを消す | 表・重さは #236 | 1,202 | 24,929 |
| 891 | `test_git_process_with_an_unreadable_cwd_is_unknown` | 1 | 7 | cwd を読めない Git を対象外と断定して、ロックを消す | 表・重さは #236 | 1,203 | 24,936 |
| 892 | `test_repo_inside_the_git_dir_is_refused` | 3 | 15 | .git 内からの指定で worktree の保持者を見落とし、使用中のロックを消す | 表・重さは #236 | 1,206 | 24,951 |
| 893 | `test_union_keeps_unknown_when_lsof_finds_nothing` | 1 | 6 | lsof が空で /proc が不明なのに stale と断定し、使用中のロックを消す | 表 | 1,207 | 24,957 |
| 894 | `test_without_proc_lsof_alone_cannot_prove_a_lock_stale` | 1 | 9 | /proc が使えず lsof が空なのに保持者不在と断定し、使用中のロックを消す | 表 | 1,208 | 24,966 |
| 895 | `test_inherited_git_environment_does_not_redirect_the_target` | 3 | 21 | 呼び出し元の GIT_* で別 repository の index.lock を削除する | 表 | 1,211 | 24,987 |
| 896 | `test_concurrent_clear_waits_for_the_lock_directory` | 1 | 27 | 並列 clear の競合で、検査済みとは別のロックを消す | 表 | 1,212 | 25,014 |
| 897 | `test_clear_without_flock_removes_nothing` | 1 | 12 | 排他ロック取得に失敗した clear が、競合する Git・clear のロックを消す | 表・重さは #236 | 1,213 | 25,026 |
| 898 | `test_clear_keeps_a_lock_replaced_during_the_check` | 1 | 12 | 検査後に差し替えられた新しいロックを消す（TOCTOU のデータ損失） | 表 | 1,214 | 25,038 |
| 899 | `test_paused_commit_in_a_core_worktree_repository_is_not_stale` | 1 | 38 | core.worktree が外を指す配置で、一時停止した commit のロックを消す | 表・重さは #236 | 1,215 | 25,076 |
| 900 | `test_git_started_through_a_symlink_with_another_name_is_detected` | 1 | 37 | 別名 symlink で起動した Git の commit 中ロックを非 Git と誤認して消す | 表・重さは #236 | 1,216 | 25,113 |
| 901 | `test_git_dir_given_as_a_dot_git_file_is_resolved` | 1 | 19 | linked worktree の .git ファイルを解決できず、その worktree の生きたロックを消す | 表・重さは #236 | 1,217 | 25,132 |
| 902 | `test_stale_lock_is_detected_then_cleared`（正しく通る例） | 1 | 301（準備 278 を含む） | 保持者がいない場合だけロックを消せる正常例。保持者拒否を『常に拒否』で満たす退行を防ぐ | 表・重さは #236 | 1,218 | 25,433 |

`tests/skills/test_skill_frontmatter.py`（`skill-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 903 | `test_allowed_tools_preserves_permission_type` | 1 | 27（準備 20 を含む） | allowed-tools の型が変わって実行権限の解釈が黙って変わり、意図外のツールを使う | 表 | 1,219 | 25,460 |

`tests/skills/test_skill_packages.py`（`skill-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 904 | `SkillPackageTests::test_execution_guidance_guards_cover_positive_and_negative_fixtures` | 1 | 8 | 検出器が常に偽を返し、禁止した Blender MCP・他エンジンへの誘導を見逃して外部へ作業を出す | 表 | 1,220 | 25,468 |
| 905 | `SkillPackageTests::test_no_positive_execution_guidance_in_skills_or_shared_references` | 1 | 78（準備 67 を含む） | スキル本文・参照文書に Blender MCP・他エンジンへの誘導が混じり、ResoLoop の操作範囲外へ作業を出す | 表 | 1,221 | 25,546 |

`.devcontainer/test-cleanup-workspace.bash`（`devcontainer-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 906 | 2. 設定の既定値（/tmp・1 日・dry-run なし） | 1 | 24（準備 13 を含む） | 削除の既定値が広がり、使用中の worktree や /tmp 外のディレクトリを消す（誤った対象への破壊的な操作） | 表・重さは #236 | 1,222 | 25,570 |

`.devcontainer/test-herdr-migration.bash`（`devcontainer-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 907 | unset の一覧と送り先・権限フラグ（env_unsets・destination） | 0 | 123 | 親の資格情報・プロバイダ切替を子 claude へ漏らす、送り先を別ホストへ変える、通常名で権限確認が外れる | 表 | 1,222 | 25,693 |
| 908 | POLLUTED_・入力元・起動の対照 | 1 | 159（準備 112 を含む） | ccdd・ccddg・ccdu が親の資格情報（POLLUTED_）や入力元のキーを子 claude へ残す（秘密情報の漏れ） | 表 | 1,223 | 25,852 |

`.devcontainer/test-initialize-mounts.bash`（`devcontainer-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 909 | 2. mount の一覧（14 個） | 0 | 20 | mount の増減でホストの永続領域や秘密情報がコンテナに露出する（固定の 14 個で守る） | 表・重さは #236 | 1,223 | 25,872 |
| 910 | 3. initialize.bash の実行（.claude.json・700） | 1 | 37（準備 16 を含む） | initialize.bash が利用者の ~/.claude.json を消す・壊す、秘密情報のディレクトリが本人以外に読める（700 でない） | 表 | 1,224 | 25,909 |

`.devcontainer/test-install-gitleaks.bash`（`devcontainer-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 911 | SHA-256 の不一致を拒否し、既にある gitleaks を変えない | 0 | 3 | SHA-256 が合わない（改ざんされた）archive を受け入れる、失敗時に既にある gitleaks を壊す | 表 | 1,224 | 25,912 |
| 912 | SHA-256 が一致する archive を置く（正例）（正しく通る例） | 1 | 58（準備 55 を含む） | 対の守り: 改ざんされた gitleaks の archive を受け入れる。何でも拒否する実装を防ぐ正例 | 表 | 1,225 | 25,970 |

`.devcontainer/test-pi-superagents.bash`（`devcontainer-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 913 | bwrap 不在・Vertex の auth overlay・--if-absent（#4・#15・#24） | 1 | 177（準備 110 を含む） | bwrap 不在でサンドボックス無しに起動、Vertex の auth overlay の登録漏れ、rebuild で利用者の tier 編集が消える | 表 | 1,226 | 26,147 |

`.devcontainer/test-readme.bash`（`devcontainer-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 914 | ワークスペースの絶対パスを書かない | 1 | 11（準備 1 を含む） | worktree や別名の checkout から実行しても、固定したパスで親の checkout を操作する | 表・重さは #236 | 1,227 | 26,158 |

`.devcontainer/test-run-tests.bash`（`devcontainer-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 915 | 3. 外から渡された GIT_* をテストに渡さない（#166） | 1 | 24（準備 14 を含む） | 外から渡された GIT_* で、一時リポジトリのつもりのテストが実リポジトリの設定を書き換える | 表 | 1,228 | 26,182 |

`.devcontainer/test-shell-tools.bash`（`devcontainer-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 916 | buni は bun が無いとき node_modules を消さない | 0 | 22 | bun が無いのに buni が node_modules だけを消し、依存を再導入できずに失う（データの消失） | 表 | 1,228 | 26,204 |
| 917 | zshrc.txt に /home/vscode を書かない | 1 | 15（準備 12 を含む） | zshrc.txt に /home/vscode を固定すると、一時 HOME や別の利用者で実際の HOME を操作する | 表・重さは #236 | 1,229 | 26,219 |

`tools/devenv_migration/tests/test_pi_provider_setup.py`（`devcontainer-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 918 | `test_new_models_are_private_even_under_public_umask` | 1 | 7 | 新規の models.json（API キーを含む）が umask 022 で誰でも読める権限で作られる（秘密情報の漏れ） | 表 | 1,230 | 26,226 |
| 919 | `test_rejected_models_change_no_managed_state` の `syntax` | 1 | 0 | models.json の構文エラーを拒否する前に auth.json の保存済みの鍵が上書きされ、退避されないので戻せない（一意名の退避は models.json だけ）。止まる表示では気付けない | #236 の判定 | 1,231 | 26,226 |
| 920 | `test_rejected_models_change_no_managed_state` の `symlink` | 1 | 24（関数 24 を含む） | symlink・hardlink の先へ書いて共有の models.json を置き換え、共有が黙って外れる | 表 | 1,232 | 26,250 |
| 921 | `test_rejected_auth_changes_neither_models_nor_other_state` | 1 | 19 | symlink の auth.json（共有・資格情報）を置き換える、拒否の前に models.json が変わる（秘密を含む共有の消失） | 表 | 1,233 | 26,269 |
| 922 | `test_existing_opencode_key_is_preserved_without_environment_key` | 1 | 11 | 環境変数が無いときに保存済みの OpenCode の鍵を消す、出力に出す（データ消失・秘密の漏れ） | 表 | 1,234 | 26,280 |
| 923 | `test_existing_fixed_name_tmp_and_its_shared_target_are_untouched` | 1 | 11 | 固定名の models.json.tmp が指す symlink 経由で、利用者のファイルを上書きする（誤った対象の破壊） | 表 | 1,235 | 26,291 |
| 924 | `test_io_failure_never_truncates_files_and_cleans_unused_staging` | 2 | 50 | 入出力の失敗で models.json・auth.json を切り詰めて資格情報を失う、バックアップと staging が残る | 表 | 1,237 | 26,341 |
| 925 | `test_update_preserves_other_providers_and_private_permissions`（正しく通る例） | 1 | 150（準備 124 を含む） | 対の守り: symlink 先の共有 auth.json・models.json を置き換える。拒否テストの正例。自身は他の鍵の消失と 0600 も守る | 表 | 1,238 | 26,491 |

`tools/devenv_migration/tests/test_pi_vertex_launchers.py`（`devcontainer-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 926 | `test_cloud_defaults_precedence_and_api_key_removal` | 2 | 34 | GOOGLE_CLOUD_API_KEY が Pi の環境に残る（秘密情報の漏れ）、project・location の優先順位を誤り課金先を取り違える | 表 | 1,240 | 26,525 |
| 927 | `test_real_namespace_masks_auth_for_parent_and_child_preserving_saved_files` | 3 | 66 | 保存済み OAuth を Pi が消費・更新して失う、Vertex の鍵が親子の Pi に渡る、保存済み auth を書き換える | 表 | 1,243 | 26,591 |
| 928 | `test_nonauth_state_and_settings_lock_remain_host_backed` | 1 | 12 | agent dir 全体を隠してセッションや設定が失われる（データ消失） | 表 | 1,244 | 26,603 |
| 929 | `test_invalid_auth_configuration_fails_closed_without_secret_output` | 1 | 12 | 壊れた auth を黙って {} にする、解析エラーに秘密を載せる、Pi を起動する（秘密情報の漏れ） | 表 | 1,245 | 26,615 |
| 930 | `test_native_oauth_refresh_and_request_do_not_consume_saved_tokens` | 1 | 384（`conftest.py` 19・準備 289 を含む） | 読み取り専用 snapshot の OAuth を Pi が更新し、新しいトークンを保存できず失う（認証情報の消失） | 表 | 1,246 | 26,999 |

`tests/scripts/test-agent-config.bash`（`script-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 931 | MCP 設定の header の鍵の直書き | 1 | 21（準備 8 を含む） | 共有する MCP 設定の header に鍵が直書きされたままコミットされる（CI と gitleaks が停止中で、この検査だけが止める） | 表 | 1,247 | 27,020 |

`tests/scripts/test-check-layout.bash`（`script-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 932 | 場面 2・9（追跡禁止ファイル・作業物の再混入） | 0 | 11 | 追跡禁止ファイル（私的なデータ）やワールドの作業物の再混入（git add -f を含む）を見逃してコミットされる | 表 | 1,247 | 27,031 |
| 933 | 場面 1（問題の無いリポジトリの通過）（正しく通る例） | 1 | 127（準備 124 を含む） | 正例（拒否の対）: 問題の無いリポジトリの通過。何でも拒否する実装を通さない。対は追跡禁止ファイルの見逃し防止 | 表・重さは #236 | 1,248 | 27,158 |

`tests/scripts/test-gitignore.bash`（`script-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 934 | 一覧 1・2（ワールドの作業物・秘密情報などの ignore） | 1 | 50（準備 27 を含む） | ignore が外れて、ワールドの作業物・秘密情報・ローカル設定・私的なデータがコミットされる（gitignore の範囲） | 表・重さは #236 | 1,249 | 27,208 |

`tests/scripts/test-new-world.bash`（`script-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 935 | 場面 1・3・6〜15（利用者のファイルを壊さない） | 0 | 133 | 不正な名前、既存のプロジェクト・利用者の設定・wrapper・AGENTS.md の上書き、symlink の先への書き込みで利用者のファイルを壊す | 表 | 1,249 | 27,341 |
| 936 | 場面 2（新規作成の通過）（正しく通る例） | 1 | 101（準備 95 を含む） | 正例（拒否の対）: 新規作成が通ること。何でも拒否する実装を通さない。対は上書き・symlink 先への書き込みの防止 | 表・重さは #236 | 1,250 | 27,442 |

`tests/scripts/test-resoloop-fork.bash`（`script-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 937 | 場面 2・5・7・8（別リポジトリへの push・変更の消失） | 0 | 53 | 他の remote の checkout・分岐した main への push、未コミットの変更の消失、ローカル main の誤った移動 | 表 | 1,250 | 27,495 |
| 938 | 場面 1 の前半・6（clone と sync の通過）（正しく通る例） | 1 | 116（準備 99 を含む） | 正例（拒否の対）: clone と sync の fast-forward が通る。何でも拒否する実装を通さない。対は他リポジトリの checkout・分岐した main への push の防止 | 表・重さは #236 | 1,251 | 27,611 |

`tests/scripts/test-scan-before-push.bash`（`script-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 939 | 検出して止まる・検査できないときは止まる | 0 | 148 | 秘密情報が push される: 緩める経路の見逃し・allowlist の広がり・検査できないのに成功と報告する（fail-closed） | 表 | 1,251 | 27,759 |
| 940 | .gitleaks.toml の除外設定のハッシュの固定 | 0 | 17 | .gitleaks.toml の除外の形が変わり、足した・入れ替えた allowlist が秘密情報を除外して push が通る | 表・重さは #236 | 1,251 | 27,776 |
| 941 | 成功する（秘密情報の無い commit の通過）（正しく通る例） | 1 | 106（準備 100 を含む） | 正例（拒否の対）: 秘密情報の無い commit とマージ commit の通過。何でも拒否する実装を通さない。対は秘密情報の push の検出と fail-closed | 表・重さは #236 | 1,252 | 27,882 |

`tests/scripts/test_superpowers_context.py`（`script-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 942 | `ContextTests::test_parent_origin_rejection_does_not_disclose_url_credentials` | 1 | 9 | 拒否メッセージに親 checkout の origin URL の資格情報が出る（秘密情報の漏れ） | 表 | 1,253 | 27,891 |
| 943 | `ContextTests::test_push_url_rejection_does_not_disclose_credentials_in_any_destination` | 1 | 13 | 拒否メッセージに push 先 URL の資格情報が出る（秘密情報の漏れ） | 表 | 1,254 | 27,904 |
| 944 | `ContextTests::test_repository_input_errors_do_not_echo_credentials_or_url_parts` | 1 | 12 | 入力エラーに repo 引数の資格情報や URL の一部が出る（秘密情報の漏れ） | 表 | 1,255 | 27,916 |
| 945 | `ContextTests::test_external_cwd_cannot_become_implicit_parent` | 1 | 4 | 別のリポジトリの cwd を暗黙の PARENT_ROOT に選ぶ（別のリポジトリを選ぶ） | 表 | 1,256 | 27,920 |
| 946 | `ContextTests::test_explicit_parent_supports_external_cwd_but_code_stays_explicit` | 1 | 4 | コード対象を明示させずに cwd のリポジトリを採用する（別のリポジトリを選ぶ）。通る例を含む | 表 | 1,257 | 27,924 |
| 947 | `ContextTests::test_empty_roots_are_omitted_not_external_defaults` | 1 | 7 | 空の root を外部 cwd の既定に置き換えて採用する（別のリポジトリを選ぶ）。通る例を含む | 表 | 1,258 | 27,931 |
| 948 | `ContextTests::test_external_remote_selection_requires_exactly_one_name` | 1 | 10 | base の remote を 1 つに決められず、別のリポジトリの remote を選ぶ | 表 | 1,259 | 27,941 |
| 949 | `ContextTests::test_known_routes_select_base_and_reject_conflicting_explicit_root` | 1 | 6 | 既知のリポジトリの経路を、明示した別の checkout にすり替えられる | 表 | 1,260 | 27,947 |
| 950 | `ContextTests::test_fork_requires_both_expected_remotes` | 1 | 4 | fork に期待する 2 つの remote が揃わないまま受け付け、別のリポジトリを選ぶ | 表 | 1,261 | 27,951 |
| 951 | `ContextTests::test_workspace_rejects_linked_code_but_fix_accepts_verified_worktrees` | 1 | 9 | linked worktree を作業用のコード対象に受け付け、worktree を既知の checkout と誤認する。通る例を含む | 表 | 1,262 | 27,960 |
| 952 | `ContextTests::test_fix_rejects_known_worktree_effective_fetch_rewrites_without_disclosing_urls` | 1 | 28 | worktree の実効の fetch URL の書き換えを既知の checkout と誤認し、URL を拒否メッセージに出す | 表 | 1,263 | 27,988 |
| 953 | `ContextTests::test_fix_rejects_same_url_clone_and_its_linked_worktree_for_known_routes` | 1 | 8 | 同じ URL の別の clone とその linked worktree を、既知の経路の checkout と誤認する | 表 | 1,264 | 27,996 |
| 954 | `ContextTests::test_document_main_and_linked_roots_verify_requested_branch` | 1 | 10 | DOC_ROOT のブランチの食い違いや別のリポジトリの checkout を受け入れ、別の文書を採用する。通る例を含む | 表 | 1,265 | 28,006 |
| 955 | `ContextTests::test_base_and_head_remote_are_independent_and_head_branch_must_match` | 1 | 15 | push 先の remote を 1 つに決められず、誤った宛先・ブランチへ push する（誤った対象への push）。通る例を含む | 表 | 1,266 | 28,021 |
| 956 | `ContextTests::test_head_remote_rejects_matching_first_pushurl_with_wrong_later_destination` | 1 | 10 | 最初の push URL だけを見て、後ろの push URL の誤った宛先を見逃す（誤った対象への push） | 表 | 1,267 | 28,031 |
| 957 | `ContextTests::test_head_remote_rejects_mixed_fetch_url_fallback_destinations` | 1 | 5 | push URL が無いとき、fetch URL の後ろの誤った宛先を見逃す（誤った対象への push） | 表 | 1,268 | 28,036 |
| 958 | `ContextTests::test_fix_accepts_known_worktree_same_repository_transport_rewrites`（正しく通る例） | 1 | 160（準備 141 を含む） | 正例（拒否の対）: 同じリポジトリ宛ての transport 書き換えの受け入れ。対の守りは fetch URL の書き換えの誤認 | 表 | 1,269 | 28,196 |

`tests/scripts/test_superpowers_review_copy.py`（`script-tests`）

| 順 | テスト | 件数 | 行数 | 防ぐ損害 | 根拠 | 累計の件数 | 累計の行数 |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: |
| 959 | `ReviewCopyTests::test_distinct_concurrent_copies_leave_exactly_one_winner` | 1 | 24 | 同時に別の内容を公開したとき、一方が他方を上書きする（記録の上書き） | 表 | 1,270 | 28,220 |
| 960 | `ReviewCopyTests::test_user_annotation_written_before_a_paused_publish_survives` | 1 | 12 | 公開の直前に利用者が書いた注記を失う（記録を失う） | 表 | 1,271 | 28,232 |
| 961 | `ReviewCopyTests::test_destination_changed_into_a_symlink_before_publish_does_not_follow` | 1 | 14 | 公開の直前に symlink へ差し替えられたとき、リンク先（確認用コピーの外）へ書く | 表 | 1,272 | 28,246 |
| 962 | `ReviewCopyTests::test_injected_link_failure_never_replaces_an_existing_destination` | 1 | 7 | リンクの失敗時に、既存の entry を別の方法（rename・copy）で差し替える | 表 | 1,273 | 28,253 |
| 963 | `ReviewCopyTests::test_name_and_path_outside_the_review_layout_are_rejected` | 1 | 6 | --name のパスの脱出、--path の範囲外を受け入れ、確認用コピーの外へ書く | 表 | 1,274 | 28,259 |
| 964 | `ReviewCopyTests::test_existing_destination_kinds_are_never_replaced` | 1 | 16 | symlink・ディレクトリ・FIFO・注記付きの既存の entry を差し替える | 表 | 1,275 | 28,275 |
| 965 | `ReviewCopyTests::test_empty_required_roots_are_rejected_before_context_fallback` | 1 | 17 | 空の root が cwd の fallback で解決され、別の対象へ公開される | 表 | 1,276 | 28,292 |
| 966 | `ReviewCopyTests::test_destination_must_be_ignored_and_inside_the_parent_checkout` | 1 | 16 | ignore されていない場所や、symlink で親の checkout の外へ公開する | 表 | 1,277 | 28,308 |
| 967 | `ReviewCopyTests::test_creates_exact_committed_bytes_and_reports_metadata`（正しく通る例） | 2 | 196（`tests/scripts/test-superpowers-python.bash` 6・準備 186 を含む） | 正例（拒否の対）: コミット済みの版と同じ内容のコピーを作る。何でも拒否する実装を通さない。対は非置換・symlink 先への書き込みの防止 | 表・重さは #236 | 1,279 | 28,504 |

## 持ち越し候補（この子の範囲外）

子の申し送り（#230・#232・#235 の完了のコメント、#228 のコメントにある #234 の完了の報告 https://github.com/usaturn/create-reso-world/issues/228#issuecomment-6347755362 、各 Spec）のうち、この子で行わないもの。行番号は申し送りの時点のもので、その後の変更（#243 など）で位置が変わっているものがある。#236 では、印を付けたもの（確かめた）のほかは確かめていない。

### テストを足す・戻す候補（D-236-16）

| 出どころ | 内容 |
| --- | --- |
| #230 | `runner.py` の fallback を止める集合から interrupted を外す変異（申し送りの時点の `runner.py:604`）と `runner.py:555` の 3 つ: 担当が報告した中断で fallback を始めないことを runner の層で確かめるテストが、基準のテストにも無い。`runner.py:557` で中断だけを response_failed に置き換える変更も、基準の全体が検出しない |
| #230 | `hooks.py:49` の `secrets=()`（後処理のログを伏せ字にしない）、`runner.py:126` の `follow_symlinks=True`、`cli.py:144` の cancel（CLI から後処理への受け渡し）を、基準のテストも検出しない |
| #230 | `process.py:77`（anchored の条件）・`process.py:94`（子孫の探索）・`process.py:284`（終了時の stdin の close）に、基準にも決定的なテストが無い |
| #230 | 代表が別のファイルにある D の 63 行は、位置引数・戻り値の受け渡しの差し替えなどの形の変異を試していない（未確認） |
| #230 | 上の `runner.py`・`hooks.py`・`process.py` の 3 行は例である。基準のテストも検出しない変異は、初回の監査の `survived` が 457 個、値の変異が 137 個、受け渡しの引数の変異が 16 個ある。記録は `PARENT_ROOT/tmp/agents/issue-230.fuotebjq/audit/` の `res/main-v1.jsonl`・`c1/res/phaseB.jsonl`・`c1/res/kwargB.jsonl`（コミットしない記録で、片付けると失われる） |
| #232 | `review_findings.py` の守りの唯一の例を消したままの 5 件（PR #246 のサイクル 3 の Low。利用者の指示で直さずにマージした）: `test_v2_timing_distinguishes_unknown_zero_and_waiting_overrun`、`test_provenance_stats_separates_skill_revisions`、`test_provenance_stats_keeps_stage_separate_from_generic_runner_role`、`test_statement_candidates_joins_excerpts_of_distant_terms_in_one_long_line`、`test_statement_candidates_ignores_documents_under_excluded_directories` |
| #232 | 変異の走査は単一行の `if`/`elif` と `review_findings.py` の証拠の検査の複合条件だけで、ほかの複合条件と、`if` でない文・式は網羅していない |
| #232 | `agent_tmp.py:39`（申し送りの時点）: cwd が main checkout の `.git` のときだけ、別の検査が拒否しない（基準のテストも検出しない） |
| #234 | `cleanup-workspace.bash` 本体の安全条件を確かめるテストが無い。`herdr-git-status.bash` の `git status` に `--no-optional-locks` が無い（範囲外の観察） |
| #235 | `new-world.sh:185` の symlink の `.resoloop/.gitignore` への追記、`check-layout.sh:364` の world の必須ファイルの symlink、`.gitleaks.toml` の 3 つ目の最初の名前の塊を、基準のテストも確かめていなかった |

### 検出しない・弱いテスト（直す候補。子が #236 に判断を任せたもの、D-236-16）

| 出どころ | テスト（一覧の段） | 内容 |
| --- | --- | --- |
| #230 の Spec の「迷いの一覧」（274 行） | `tools/agent_runner/tests/adapters/devin/test_adapter.py::test_export_error_fields_override_answer`（迷い・中。一覧の 21 行目） | `_export_failure` を外しても結果が response_failed のままで、守りを検出しない。「直すかは #236 で決める」 |
| #234 の Spec の「迷いの一覧」・#228 のコメント（#234 の完了の報告） | `tools/devenv_migration/tests/test_pi_vertex_launchers.py::test_concurrent_launchers_initialize_only_empty_missing_auth`（迷い・高。一覧の 45 行目） | 先着の auth を後着が上書きしない部分は、守りを壊しても失敗しなかった（この変更の前から同じ） |
| PR #246 のレビュー修正の Spec（40 行、S1） | `.agents/scripts/tests/test_review_findings.py::test_statement_candidates_ignores_user_diff_prefix_settings`（迷い・中。一覧の 28 行目） | 外すとエラーで止まる（L に近い）ので書きすぎの可能性がある。「#236 が L の残りを整理するときに見直す」 |

### 行数を減らす別の手段（D-236-17）

| 出どころ | 内容 |
| --- | --- |
| #230 の D-230-11 | 行数のための準備のコードの共通化（git の repository の写し、Devin の export のよく似たテスト）。残す S のテストの準備を変える |
| この子の一覧 | ファイルの準備・補助のファイル・ケースの群に分けた関数の行が 12,734 行（計測の行数の 44.7%）、「高」の段では 11,191 行（58.0%）を占める（「残ったテストの一覧」の「段ごとの累計」の下の注記）。そのうち「高」の段の行に付いた 11,191 行は、「高」の行を消さないと減らない |

### 使われていないもの・古い記述（ほかの子の領域）

| 出どころ | 内容 |
| --- | --- |
| #236（確かめた。`PARENT_ROOT/tmp/agents/issue-236.15yls_nc/verify/unused-support.txt`） | `tools/agent_runner/tests/adapters/dsh/ptc_tool_results.json`（14 行）: #243 が DSH のテストを消した後に残った、使われていない fixture（`git grep ptc_tool_results` は `docs/` だけ）。一覧の 1 行目（D-236-13） |
| #235（確かめた。`PARENT_ROOT/tmp/agents/issue-236.15yls_nc/verify/test-ci-refs.txt`） | `.gitleaks.toml` の 5 行目のコメントと 2 つ目の allowlist の description、`.devcontainer/install_gitleaks.bash:4`、`tests/scripts/test_meshy.py:20` のコメントが、消した `tests/scripts/test-ci.bash` を参照している（説明の文だけ） |
| #230 | `tools/agent_runner/tests/conftest.py` の `supervisor_bootstrap` の引数 `startup` は、消したテストだけが使っていた（D-230-10） |
| #230 | `test_checkout_policy.py` の ruff の F811（`test_runner.py` から import した fixture の `repository` を引数の名前で使う形）は基準からある |
| #230 | #230 の Spec の棚卸しの表の 4 行（811・910・911・912 行）の行番号は実在しない行を指す（`skills.py:79-81`、`adapters/__init__.py:58-66`・`83-93` が正しい） |
| #230 | #230 の Spec の棚卸しの表の理由は 90 字で切ってある（全文は `PARENT_ROOT/tmp/agents/issue-230.fuotebjq/audit/final-inventory.json`。コミットしない）。理由が切れていた 71 項目のうち約 50 項目は、この子の一覧の「防ぐ損害」を全文から直した（残りは表の理由のまま） |
| #236 の分類の担当の観察（確かめていない） | 縮約で消したケース用の分岐が `.agents/skills/pr-review-fix-loop/tests/test_loop_review.py` などに残っている。`test_create_records_its_phases_in_the_journal` は、#231 の表の注記（固定の phase 名・順序の写しは F、残すなら絞る）どおりには絞られていない |

### これから削るときの進め方（子の申し送り）

| 出どころ | 内容 |
| --- | --- |
| #235 | D・L・F と判定する前に、守る条件の部分を 1 つ外した変異と、F とした確認の 1 つずつの見直し（F∩S かどうか）で確かめると、S の最後の代表を消す手戻りを避けられる（#232・#235 では、その指摘がサイクルごとに続いた） |
| #230 | 変異の監査の道具（PID 名前空間での実行、子の Python も含めたテストごとの coverage、テスト 1 件 30 秒の上限）は `PARENT_ROOT/tmp/agents/issue-230.fuotebjq/audit/bin/` にある（コミットしない） |
| #232 | 残った S を一覧にするときは、単一行の `if` のほかの複合条件と、`if` でない文・式を走査してから重さを決めるのがよい。#236 はこの走査を行わず、重さを子の表から写した（D-236-16） |

## 検証

- `README.md` の「テスト」の入口: `uv run pytest tests/skills .agents/skills .agents/scripts tools`、`bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`（worktree のルート、コミット済みの状態）
- 計測: #228 の「計測」のコマンド（コミット済みの状態）
- 使われていない名前: `git grep -n <名前> -- ':!:tools/test_support/'`
- 一覧: 生成のスクリプトの検査（合計・網羅・並べ順）
