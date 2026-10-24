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
- 基準: `origin/main` の `bdbe02b`（PR #255 のマージ）

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
| D-236-5 | `.devcontainer/README.md` の「テストの実行」の pytest の行に `tools` を足し、「CI も同じコマンドを実行する」を、CI の skill-tests のジョブが `tools` を含まないことが分かる書き方に直す | (a) 変えない、(b) CI のジョブに `tools` を足す | (a) この行は #123（`38d779f`）の後に直されておらず、#149（`d1000b1`）が `testpaths` に `tools` を足した後も `tools` を含まない。`tools/devenv_migration` のテストを実行していた `.devcontainer/test-pi-migrations.bash` は #234 が消したので、今はこの節のコマンドで `tools` のテスト（`tools/agent_runner`・`tools/devenv_migration`）が 1 つも実行されない。`README.md` の「テスト」と `testpaths` は `tools` を含む。(b) `.github/workflows/ci.yml` はこの子の範囲の外で、`AGENTS.md` の「GitHub Actions」は private の CI を止めている | Issue の受け入れ（README が残ったテストの実行のしかたと合う） |
| D-236-6 | `README.md` の「テスト」、`.devcontainer/run-tests.bash`、`tests/scripts/test-superpowers-python.bash` は変えない | — | どれも消えたディレクトリを指さず、残ったテストの実行のしかたと合っている（確かめたことは「受け入れ条件との対応」） | — |
| D-236-7 | 件数・行数のどちらも 1/3 に届かないので、一覧を作り #228 にコメントする。この子は一覧を出したら completed で close し（PR の `Closes #236` を `finalize.py` が更新する）、#228 は open のまま残す | — | Issue の受け入れ・#228 の決定 6 | Issue の受け入れ |
| D-236-8 | 一覧の単位は、今の `main` に残っているテストの関数（pytest・unittest。parametrize は収集数を件数にした 1 行）と、bash のテストの場面の群（ファイルの中で、重さと「迷い」が同じ場面をまとめる）にする。子の表が 1 つの関数の parametrize のケースで分類・重さ・迷いを分けているとき（例: `test_review_records.py::test_invalid_records_are_rejected` の「S（高・中）」、`test_review_findings.py::test_invalid_documents_name_the_problem` の「S 中 4 / 迷い 2」、`test_process.py::test_supervisor_launch_paths_preserve_stdin_and_exit` の D と S）は、分類・重さ・迷いが同じケースの群ごとに行を分け、件数はその群のケースの数にする | (a) 子の棚卸しの表の行をそのまま使う、(b) ファイルごと、(c) 分けた関数を、いちばん重いケースの段に 1 行で置く、(d) 迷いのケースが 1 つでもあれば関数ごと迷いの段に置く | (a) 表の行の単位は子ごとに違い（関数、parametrize のケース、説明文の群）、#243 などの後の変更で今のテストと合わない行がある。行数を行に割り当てられない。(b) 重さの順に並べられない。(c) は迷いのケースを先頭から外し、(d) は高の守りを先頭に出す。件数の目標まで 64 件しかなく、ケースの段の違いが目標に届く位置を動かすので、表が分けたとおりに分ける（brainstorming の builder check の問い 1 への判断） | Issue の受け入れ（テストまたはテストの群ごとに） |
| D-236-9 | 分類・防ぐ損害・重さ・「迷い」は、6 つの子の Spec の棚卸しの表と、レビュー修正の記録（同じ Spec の後の節と、`pr24x-...-review-fixes-design.md`）から取る。表で「消す」なのに残っているテストは、戻した記録の理由を使う。表に無いテスト（子の後の PR が足した・変えたもの）と、記録が見つからないものは、`AGENTS.md` の「テストの採用基準」で #236 が判定し、一覧で「#236 の判定」と分かるようにする | 全てのテストを #236 が分類し直す | #228 の決定（議論し直さない）。分類の根拠は子の棚卸し。#236 の判定は、子の表で決まらないものに限る | #228 の「利用者の決定」 |
| D-236-10 | 表に重さが書かれていない S・F∩S・迷いは、#228 の「守りの重さ」（高: 秘密情報の漏れ・データの消失・誤った対象への破壊的な操作・未検証のマージ。中: 誤った結果の報告・記録の取り違え。低: 作業の結果を変えないもの）で #236 が決め、「重さは #236 の判定」と分かるようにする。表の重さに幅がある（「中-低」「高・中」）のにケースを分けていないものは、重い方にする | (a) 重さの無い行を別の群にする、(b) 幅は軽い方にする | (a) 並べ替えに重さが要る。定義は #228 にある。(b) 軽い方にすると、重い方の守りを含むテストが先に消える位置に来る。#228 の決定 6（気付けない損害を防ぐテストを数のために消さない）に近い側にした | #228 の「守りの重さ」 |
| D-236-20 | 拒否のテストの対として残した「正しく通る例」（`AGENTS.md` の D: 拒否を確かめるテストには、正しく通る例を少なくとも 1 件残す）は、重さを対の守りのいちばん重いものにそろえ、同じファイル・同じ段の中で、ほかの行の後に置く | (a) 正しく通る例そのものの損害で重さを決める（多くは低）、(b) 対のテストを指す項目を JSON に持たせ、対の最後の行の直後に置く | (a) 上から消すと、正しく通る例が対の拒否のテストより先に消え、D の規則があるので実際にはそこまで消せない。件数の累計が実際に消せる数より多く見える（brainstorming の builder check の問い 2）。(b) 対は同じモジュールの守りなので、同じファイル・同じ段の後ろに置けば足りる。依存の処理を検査と並べ替えに足さずに済む | `AGENTS.md` の「テストの採用基準」の D |
| D-236-11 | 計測の対象の全ての行を、一覧のどれか 1 行にだけ割り当てる（下の「一覧の作り方」の割り当て）。テストの関数の行はその行に（ケースの群に分けた関数は、並べ順でその関数の最後の群に）、ファイルの準備（import・補助・fixture）の行はそのファイルの最後の行に、補助のファイル（`conftest.py`・偽の CLI・fixture のデータ）はそれを使うテストの最後の行に、bash のファイルの 1 件と準備の行はそのファイルの最後の群に付ける。使うテストが無い補助は一覧の先頭に置く | (a) テストの関数の行だけを数え、準備は別に示す、(b) 準備をテストの数で按分する | 上から消したときの累計が、実際にそこまで消したときに消せる行数（準備はそれを使う最後のテストを消したときに消せる）の下限になる。(a) は全てを消しても合計に届かない。(b) は消しても残る準備を消せるように見せる。合計は計測の行数と一致する | Issue の受け入れ（上から消したときの累計） |
| D-236-12 | 並べ順: 使うテストが無い補助 → 「迷い」（重さの低い順） → 低 → 中 → 高。同じ段の中は、領域（#230・#231・#232・#233・#234・#235・`integration` の順）、ファイルのパス、正しく通る例を後ろ（D-236-20）、ファイルの中の位置の順 | 同じ段の中を行数の多い順にする | Issue の並べ順（迷いを先頭に、続けて重さの低い順）。同じ段の中は、ファイルごとにまとまり、利用者がファイルを見ながら選べる順にした | Issue の受け入れ |
| D-236-13 | `tools/agent_runner/tests/adapters/dsh/ptc_tool_results.json`（14 行）は、#243 が DSH のテストを消した後に残った、使われていない fixture である（`git grep ptc_tool_results` は `docs/` だけ）。この子では消さず、一覧の先頭に「使うテストが無い補助」として載せる | この子で消す | `agent-runner-tests` の領域のファイルで、Issue の「変えないもの」に当たる | Issue の「変えないもの」 |
| D-236-14 | 一覧の全体（関数・場面の群ごと）はこの Spec の「残ったテストの一覧」に置き、#228 のコメントには、計測の結果、子ごとの内訳、段ごと（迷い・低・中・高）の累計、領域 × 段の群の一覧（件数・行数・防ぐ損害・重さ・迷い・累計）、「迷い」の行の全て、持ち越し候補、全体の一覧へのリンクを書く | 全体の一覧を #228 のコメント（複数）に写す | 一覧は 900 行ほどで、GitHub のコメントの上限（65,536 字）に収まらない。PR でレビューされる 1 か所に置き、版を Git で追える。#228 のコメントは、群の一覧で判断でき、行ごとの詳細はリンクで読める | Issue の受け入れ（テストまたはテストの群ごとに） |
| D-236-15 | #228 へのコメントは PR を作った後（ループの前）に、PR の head の計測で投稿する。ループの修正で一覧が変わったら、コメントを直す。マージの後に `main` で測り直し、最終の値を #228 と #236 に書く | マージの後にだけ投稿する | Issue は「一覧を出したら completed で close」の順で、`finalize.py` はマージと同時に #236 を閉じる。投稿の後にループの修正があっても、同じコメントを直せば古い一覧が残らない | Issue の受け入れ |
| D-236-16 | 子が申し送った、基準のテストも検出しない守り（#230 の `runner.py:604` など、#232 の `agent_tmp.py:39`、#235 の `new-world.sh:185` など）と、消したままの S の例（#232 のサイクル 3 の 5 件）は、この子ではテストを足さず・戻さず、#228 のコメントに「持ち越し候補（テストを足す・戻す候補）」として書く | この子でテストを足す・戻す | 領域のテストは Issue の「変えないもの」。足すのは新しい要求で、件数も増える。#230 は「テストを足すかは #236 で決める」と申し送ったので、この表で決めた | Issue の「変えないもの」 |
| D-236-17 | 行数のための準備のコードの共通化（#230 の D-230-11: git の repository の写し、Devin の export のよく似たテスト）は、この子では行わず、行数を減らす別の手段として #228 のコメントに書く | この子で共通化する | 領域のテストを変える（Issue の「変えないもの」）。残す S のテストの準備を変えるので、どこまで行うかは利用者が決める | Issue の「変えないもの」 |
| D-236-18 | 分類の取り出しは、6 つの領域ごとに 1 つ、読むだけのサブエージェントが決まった JSON の形で書き、controller が検査のスクリプト（関数・場面の網羅、値の形、Spec の行の実在）で確かめ、各領域から抜き出した行を Spec と照らし合わせる。`integration` の補助は controller が扱う | controller が全て読む | 子の Spec は合わせて約 930KB、残っているテストの関数は 891 ある。領域は互いに独立で、並行で読める。形と網羅は機械で、中身は抜き出しで確かめる | issue-to-pr の委任（推奨案で進める） |
| D-236-19 | 予約は、ループの `finish` の後（ループのエラーで `finish` まで進めないときは止まった時点）に、結果と再開の方法を #236 に書いてから解放する | PR の作成の直後に解放する | issue-to-pr の `--merge` の手順 | issue-to-pr |

## 受け入れ条件との対応

| Issue の受け入れ | 担当（Plan） | 観測する結果 | 確かめ方 |
| --- | --- | --- | --- |
| `tools/test_support/` とルートの `conftest.py` に使われていない名前が無い | Task 1 | `__all__` と各モジュールの名前（`FINDING_CONTENT`・`plugin`・`outside_runner`・`texts`・`drop_inherited_git_environment`）が、`tools/test_support/` の外で使われている。`FINDING_REASON` が無い | `git grep -n <名前> -- ':!:tools/test_support/'` を名前ごとに実行し、結果を記録する。autouse の fixture は効く範囲を書く |
| `pyproject.toml` の `pythonpath`・`testpaths`、`.devcontainer/run-tests.bash` が消えたディレクトリを指していない | Task 1 | 指すパスがすべて実在する | パスごとに `test -d`。`run-tests.bash --list` の全てが実在する |
| `README.md` の「テスト」と `.devcontainer/README.md` の「テストの実行」が、残ったテストの実行のしかたと合っている | Task 1 | 両方の pytest の行が `testpaths` と同じ 4 つを指す。CI の記述が `ci.yml` と食い違わない | `git diff` と、書いたコマンドの実行（Task 5） |
| 6 つの子の Spec に棚卸しの表があることを確かめる | Task 4 | 6 つの Spec のパスと、棚卸しの表の節の見出し | `grep -n '^#' <Spec>` の結果を「棚卸しの表の確認」に書く |
| 「計測」の結果（件数・行数と、子ごとの内訳）を #228 にコメントする | Task 6 | #228 のコメントの URL | `gh api` で読み戻す |
| 届かなければ、一覧を作り #228 にコメントする（領域・件数・行数・防ぐ損害・重さ・迷い、迷いを先頭に重さの低い順、累計） | Task 2・3・4・6 | 一覧の行の合計が計測の件数・行数と一致し、並べ順が D-236-12 のとおり | 一覧の生成のスクリプトの検査（網羅・合計・並べ順）と、領域ごとの抜き出しの照合 |
| `README.md` の「テスト」の入口が通る | Task 5 | 3 つのコマンドが終了コード 0 | `uv run pytest tests/skills .agents/skills .agents/scripts tools`、`bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh` |

共有する条件: 一覧の件数・行数は、計測と同じファイルの集合（#228 の「計測」の pathspec）と同じ数え方（`wc -l` は改行の数）を使う。この条件は Task 2 の索引と Task 4 の生成で同じスクリプトの関数を使い、Task 4 で合計を計測の値と照合する（統合は controller）。

## 一覧の作り方

### 索引（Task 2）

コミット済みの checkout で次を集め、JSON の索引にする（スクリプトは `PARENT_ROOT/tmp/agents/issue-236.*/bin/index_tests.py`。コミットしない）。

- `uv run --locked pytest --collect-only -q` と、`tests/scripts`（Meshy を除く）の収集の node ID。node ID の `[...]` を除いた `パス::関数`（クラスのメソッドは `パス::クラス::メソッド`）ごとに、収集数とケースの ID（`[...]` の中）を記録する
- 計測の pathspec の全てのファイルの改行の数（`wc -l` と同じ）
- テストのモジュール（`test_*.py`）の、`test` で始まる関数とメソッドの行の範囲（デコレータの行から関数の最後の行まで）。範囲の外の行は、そのファイルの準備の行
- bash のテスト（`.devcontainer/test-*.bash`・`tests/scripts/test-*.bash`。Meshy を除く）

全ての node ID が関数に対応し、全ての関数に node ID があることを確かめる（着手時の `bdbe02b` で 1,279 件・28,470 行と一致し、対応しないものは無かった。基準値の `7d44355` でも 3,646 件・45,024 行と一致した）。

### 分類（Task 3）

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

### 割り当てと並べ替え（Task 4）

1. 行は、関数（件数はその収集数）、関数のケースの群（件数はその群のケースの数）、bash の場面の群（件数 0）、使うテストが無い補助（件数 0）である
2. 段と並べ順: 使うテストが無い補助 → 迷い → 低 → 中 → 高（D-236-12）。迷いの中は重さの低い順。同じ段・領域・ファイルの中では、正しく通る例（`pair_positive`）をほかの行の後に置き、その中はファイルの中の位置の順
3. 行数の割り当て（D-236-11）: 関数は自分の行の範囲（ケースの群に分けた関数は、並べ順でその関数の最後の群に付ける）、bash の群は自分の `ranges`。ファイルの準備の行と bash のファイルの 1 件は、並べ順でそのファイルの最後の行に付ける。補助のファイルは、使うテストの最後の行に付ける。使うテストは次で決める
   - `conftest.py`: 同じディレクトリとその下のテストのモジュール（ルートの `conftest.py` は pytest の `testpaths` の全て）
   - 偽の CLI・補助のモジュール・fixture のデータ: 1 つ上のディレクトリとその下のテストのうち、ファイル名（拡張子を除く名前）を含むもの。含むものが無ければ「使うテストが無い補助」
   - `tools/test_support/plugin.py`・`texts.py`: `tools.test_support.plugin`・`tools.test_support.texts` を読み込むテストのモジュール。`__init__.py` はその両方
   - `tests/scripts/test-superpowers-python.bash`: `tests/scripts` の Python のテスト（件数の 1 件も付ける）
4. 累計: 上から順に、件数と行数（付けた分を含む）を足す。合計が計測の件数・行数と一致することを確かめる。残りが目標以下になる最初の行を、件数・行数それぞれに印を付ける
5. 出力: この Spec の「残ったテストの一覧」の表（全ての行）と、#228 のコメントの群の一覧（領域 × 段）

この割り当ては、そこまで消したときに消せる行数の下限である。準備の一部は、それを使うテストだけを消せばもっと早く消せる。

## 棚卸しの表の確認（#228 の完了の条件 4）

（Task 4 で記録する）

## 計測の結果（この PR の後）

（Task 5 で記録する）

## 残ったテストの一覧

（Task 4 で生成して記録する）

## 持ち越し候補（この子の範囲外）

（Task 4 で、子の申し送りから集めて記録する）

## 検証

- `README.md` の「テスト」の入口: `uv run pytest tests/skills .agents/skills .agents/scripts tools`、`bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`（worktree のルート、コミット済みの状態）
- 計測: #228 の「計測」のコマンド（コミット済みの状態）
- 使われていない名前: `git grep -n <名前> -- ':!:tools/test_support/'`
- 一覧: 生成のスクリプトの検査（合計・網羅・並べ順）
