# Issue #236 テストの計測・共有の補助の整理・残ったテストの一覧 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 使われていない `FINDING_REASON`・古い pytest のパス・古いテストのコマンドを直し、テスト全体を #228 の「計測」で測り、1/3 に届かないので残ったテストの一覧を Spec と #228 に出して、PR（`Closes #236`）を `--merge` のループでマージする。

**Architecture:** コードの変更は Task 1 の 4 ファイルだけ。一覧は、コミット済みの checkout から作る索引（node ID・関数の行の範囲・ファイルの行数）と、6 つの領域ごとに子の Spec から写した分類の JSON を、controller のスクリプトで結合して作る。索引・検査・結合のスクリプトは `PARENT_ROOT/tmp/agents/issue-236.15yls_nc/bin/` に置き、コミットしない。

**Tech Stack:** Python 3.14（`uv run --no-project` の標準ライブラリだけ）、pytest の収集、git、gh。

**Spec:** `docs/superpowers/specs/2026-10-25-create-reso-world-issue236-test-integration-design.md`

## Global Constraints

- 状態は draft。実行許可は Spec の「管理・実行許可」（`/issue-to-pr #236 --merge`）。内容の承認（approved）ではない
- リポジトリで変えてよいのは、`tools/test_support/texts.py`・`tools/test_support/__init__.py`・`pyproject.toml` の `[tool.pytest.ini_options]`・`.devcontainer/README.md` の「テストの実行」の節と、この子の Spec・Plan だけ（Spec の D-236-1〜6）。領域ごとの子のテストとコード（`tools/agent_runner/tests/adapters/dsh/ptc_tool_results.json` を含む）、`AGENTS.md`、Meshy のファイル、`.github/workflows/ci.yml`、`.gitleaks.toml` は変えない
- テストは書かない・消さない（`AGENTS.md` の「テストの採用基準」。この変更に S に当たる挙動は無い）
- 計測は #228 の「計測」の 4 つのコマンドを、コミット済みの状態で、worktree のルートで実行する。一覧の件数・行数の合計は、その値と一致しなければならない
- 一覧の並べ順は、使うテストが無い補助 → 迷い（重さの低い順）→ 低 → 中 → 高。同じ段の中は、領域（`agent-runner-tests`・`pr-review-tests`・`review-helper-tests`・`skill-tests`・`devcontainer-tests`・`script-tests`・`integration`）、ファイルのパス、正しく通る例（`pair_positive`）を後ろ、ファイルの中の位置の順（Spec の D-236-12・D-236-20）
- 子の表が parametrize のケースで分類・重さ・迷いを分けている関数は、ケースの群ごとに行を分ける（Spec の D-236-8）。表の重さに幅があってケースを分けていないものは重い方（D-236-10）
- 重さは #228 の「守りの重さ」: 高（秘密情報の漏れ・データの消失・誤った対象への破壊的な操作・未検証のマージ）、中（誤った結果の報告・記録の取り違え）、低（作業の結果を変えないもの）
- コミットしないファイルは `PARENT_ROOT/tmp/agents/issue-236.15yls_nc/` に置き、worktree の中に作らない（SDD の ledger・依頼・レビューの資料も `…/sdd/` に置く）。pytest の `--basetemp` は worktree の外
- push は `AGENTS.md` の「push の前の秘密情報の検査」の形だけで行う。#228 の本文は変えない

## Review Focus

1. 索引と計測の数え方が食い違う入力: 改行で終わらないファイル、クラスのメソッドのテスト（unittest の `TestCase`）、parametrize の ID に `[`・`::` を含むもの → Task 3 の Step 2 で、一覧の合計を計測の 4 つのコマンドの値と照合する
2. 子の表で「消す」なのに今も残っているテスト（レビュー修正で戻したもの）を、表の分類のまま L・D として一覧に載せる → Task 2 の検査で、残っている L・F・D には理由の `note` を必須にし、レビューで全件を確かめる
3. 子の棚卸しの後に別の PR が足した・変えたテスト（#243 の `5678691`・`a532330`、`f12c400`、`172bc8f`、`d33f01d`）を、表の別のテストの行に誤って当てる → Task 2 の依頼に commit を渡し、表に無いものは `source` を null にして理由を書く。レビューで全件を確かめる
4. 補助のファイルの「使うテスト」を誤って決め、まだ使われている補助を「使うテストが無い補助」として先頭に置く → Task 3 の Step 3 で、先頭に置いた補助ごとに `git grep` の結果を記録する
5. parametrize のケースで分類が分かれる関数を 1 行にまとめ、迷いや軽いケースを重い段に入れる（件数の目標まで 64 件なので、目標に届く位置が動く）→ Task 2 の依頼で `cases` を求め、検査（`validate_classify.py`）がケースの ID の網羅を確かめ、レビューで `cases` の全件を表に照らす

---

### Task 1: 使われていない名前・古い pytest のパス・古いテストのコマンドを直す

**Files:**
- Modify: `tools/test_support/texts.py`（docstring の 1〜6 行、`FINDING_REASON` の 18〜22 行）
- Modify: `tools/test_support/__init__.py`（7〜12 行）
- Modify: `pyproject.toml`（`[tool.pytest.ini_options]` の 2 つ目のコメントの行と `pythonpath`）
- Modify: `.devcontainer/README.md`（「テストの実行」の節の 1 文目とコードブロック）

**Interfaces:**
- Produces: `tools.test_support.FINDING_CONTENT`・`tools.test_support.texts.FINDING_CONTENT`・`tools.test_support.plugin.outside_runner` は今のまま。`FINDING_REASON` は無くなる。pytest の `pythonpath` は `["."]`

テストの要否: 書かない。消す名前は使われていない（壊れれば import のエラーで気付く L）、README は文書（F）。代わりの検証は Step 5〜7。

- [ ] **Step 1:** `texts.py` の `FINDING_REASON` の定義（18〜22 行と、その前の空行）を消し、docstring を次にする

  ```python
  """レビュー指摘の、実環境の形をした自由記述サンプル。

  担当への依頼の `prompt` のような自由記述は、改行・タブ・CRLF・
  非 ASCII 文字を含む複数行の文章になりうる。識別子やパスとして解釈
  できる形ではない（``str.isidentifier()`` が False）。
  """
  ```

- [ ] **Step 2:** `__init__.py` の import を `from tools.test_support.texts import FINDING_CONTENT` に、`__all__` を `["FINDING_CONTENT"]`（今の複数行の書き方のまま 1 項目）にする。docstring は変えない
- [ ] **Step 3:** `pyproject.toml` の `# pythonpath の 2 つ目は、tools/devenv_migration/tests のテストが兄弟のモジュールを名前で import するため` の行を消し、`pythonpath = ["."]` にする。`testpaths`・`addopts`・1 つ目のコメントは変えない
- [ ] **Step 4:** `.devcontainer/README.md` の「テストの実行」の 1 文目を `リポジトリのルートで次を実行する。CI（`.github/workflows/ci.yml`）も同じコマンドを実行する（skill-tests のジョブは pytest の `tools` を除く）。` にし、コードブロックを次にする（コメントの位置は `README.md` の「テスト」と同じ 65 桁目）

  ```bash
  bash .devcontainer/run-tests.bash                                # .devcontainer/test-*.bash と tests/scripts/*.bash（CI の devcontainer-tests）
  bash scripts/check-layout.sh                                     # リポジトリのレイアウト（CI の layout。resoloop が無ければ skills sync の検査を skip）
  uv run pytest tests/skills .agents/skills .agents/scripts tools  # スキル・.agents/scripts・tools のテスト（CI の skill-tests は tools を除く）
  (cd worlds/<name> && uv run pytest)                              # 各ローカルプロジェクトのテスト（追跡対象外なので CI では実行しない）
  ```

- [ ] **Step 5:** 名前の確かめ: `git grep -n FINDING_REASON -- ':!:docs/'` が 0 件。`FINDING_CONTENT`・`outside_runner`・`tools.test_support.plugin`・`tools.test_support.texts` を `git grep -n <名前> -- ':!:tools/test_support/' ':!:docs/'` で 1 つずつ実行し、どれも 1 件以上。結果を `…/verify/names.txt` に保存する
- [ ] **Step 6:** パスの確かめ: `testpaths` の 4 つと `pythonpath` の `.` に `test -d`、`bash .devcontainer/run-tests.bash --list` の全ての行に `test -f`。結果を `…/verify/paths.txt` に保存する
- [ ] **Step 7:** `uv run --locked pytest tools/devenv_migration .agents/skills/issue-to-pr -q -p no:cacheprovider --basetemp "$(mktemp -d /tmp/issue-236-t1.XXXXXX)/bt"` が全件通過。`uv run --locked pytest --collect-only -q | tail -n 1` が `1224 tests collected`
- [ ] **Step 8:** commit（`chore: drop the unused FINDING_REASON, the stale pytest path and the stale test command (#236)`）

### Task 2: 6 つの領域の分類を子の Spec から写す（読むだけ、並行）

**Files:**
- Create（リポジトリの外）: `…/data/classify/<area>.json`（`<area>` は `agent-runner-tests`・`pr-review-tests`・`review-helper-tests`・`skill-tests`・`devcontainer-tests`・`script-tests`）

**Interfaces:**
- Consumes: 索引 `…/data/index-<Spec・Plan の commit>.json`（テストのファイルは `bdbe02b` と同じ）、依頼のファイル `…/data/tasks/<area>.json`（関数の一覧とケースの ID・bash のテスト・読む Spec・棚卸しの後の commit）、検査 `…/bin/validate_classify.py`
- Produces: Spec の「分類（Task 2）」の形の JSON。Task 3 が読む

テストの要否: 書かない（リポジトリを変えない）。代わりの検証は Step 2・3。

- [ ] **Step 1:** 6 つの領域に、読むだけのサブエージェントを 1 つずつ並行で依頼する（依頼の本文は `…/sdd/task-2-brief.md` と、領域ごとの値）
- [ ] **Step 2:** 各領域で `uv run --no-project python …/bin/validate_classify.py …/data/index-<Spec・Plan の commit>.json <area> …/data/classify/<area>.json <worktree>` が `"ok": true`（関数・ケースの ID・bash のテストの網羅、値の形、`source.line` の実在、bash の範囲の重なり）
- [ ] **Step 3:** 領域ごとのレビュー: `weight_basis` が `inferred`、`source.spec` が null、`classification` が L・F・D、`mayoi` が true、`pair_positive` が true、`cases` を使う関数の全件（多ければ 30 件まで）と、ほかから 15 件を、子の Spec とテストのコードに照らす。食い違いは同じ担当に直させ、Step 2 をやり直す

### Task 3: 一覧を作り、Spec の結果の節を書く（統合、controller）

**Files:**
- Modify: Spec の「棚卸しの表の確認」「計測の結果（この PR の後）」「残ったテストの一覧」「持ち越し候補」の節

**Interfaces:**
- Consumes: Task 1 の commit、Task 2 の 6 つの JSON、`…/bin/index_tests.py`・`…/bin/per_area.py`
- Produces: `…/bin/build_list.py <index.json> <classify_dir> <out_dir>` が書く `list.md`（全ての行の表）・`groups.md`（領域 × 段の群の表）・`mayoi.md`（迷いの行）・`summary.json`（合計・段ごとの累計・目標に届く行）。Task 5 の #228 のコメントが使う

テストの要否: 書かない（コミットするのは文書だけ）。代わりの検証は Step 2〜4。

- [ ] **Step 1:** Task 1 の commit（clean）で `index_tests.py` を実行し、`…/data/index-<sha>.json` を作る。関数・ケースの ID・bash のテストの集合が Task 2 の索引と同じで、件数が 1,279、行数が 28,470 から Task 1 で減った行を引いた値であることを確かめる
- [ ] **Step 2:** `build_list.py` を書いて実行する。割り当て・並べ順は Spec の「割り当てと並べ替え」のとおり。スクリプト自身が、行の件数・行数の合計が索引の `count_total`・`lines_total` と一致すること、全ての計測の行がちょうど 1 行に割り当てられたこと、並べ順が Global Constraints のとおりであることを確かめ、食い違えば終了コード 1
- [ ] **Step 3:** 「使うテストが無い補助」として先頭に置いた各ファイルについて、ファイル名の `git grep -n` の結果を `…/verify/unused-support.txt` に保存する（`docs/` の外に参照が無いこと）
- [ ] **Step 4:** #228 の「計測」の 4 つのコマンドを Task 1 の commit で実行し、`summary.json` の合計と一致することを確かめる。結果を `…/verify/measure.txt` に保存する
- [ ] **Step 5:** Spec の 4 つの節を書く。「棚卸しの表の確認」は 6 つの Spec のパスと棚卸しの節の見出し（`grep -n '^#'`）、「計測の結果」は Step 4 の値と子ごとの内訳（`per_area.py`）、「残ったテストの一覧」は `summary.json` の段ごとの累計と `list.md`、「持ち越し候補」は子の申し送り（#230・#232・#234・#235 の完了のコメント・Spec）のうち、この子で行わないもの（Spec の D-236-13・16・17）
- [ ] **Step 6:** commit（`docs: record the #236 measurement and the list of remaining tests`）

### Task 4: ブランチ全体のレビューと最後の検証

**Files:**
- Modify: 指摘があれば Task 1 のファイルと Spec。この Plan の「完了」

テストの要否: 書かない。検証は Step 3。

- [ ] **Step 1:** ブランチ全体のレビューを、最も能力の高いモデルのサブエージェントに依頼する（`review-package` の出力を `…/sdd/` に置く。Spec・Plan・Global Constraints を渡す）
- [ ] **Step 2:** 指摘があれば 1 回だけまとめて直し、範囲を絞った再レビューを 1 回行う
- [ ] **Step 3:** 最後の commit の後、clean な HEAD で `README.md` の「テスト」の入口（`uv run pytest tests/skills .agents/skills .agents/scripts tools`、`bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`）を実行し、argv・終了コード・ログの完全パス・HEAD・`git status --porcelain` が空だったことを `…/verify/` に記録し、`finalize.py` の `--checks-file` の形のファイル（`{"head", "base", "commands"}`）を作る。#228 の「計測」もこの HEAD で実行して一致を確かめる

### Task 5: 公開（push・PR・#228 と #236 へのコメント）

テストの要否: 書かない（外部への書き込みだけ）。確かめは、push の前の検査（Step 2）と、投稿したコメントの読み戻し（Step 4）。

- [ ] **Step 1:** 予約 ref が保存した SHA のままで、#236 が open、#236 の open の PR が無いことを確かめ直す
- [ ] **Step 2:** `SHA="$(bash "$PARENT_ROOT/scripts/scan-before-push.sh" -C <worktree>)" && [ -n "$SHA" ] && git -C <worktree> push origin "${SHA:?}:refs/heads/feat/issue-236-test-integration"`
- [ ] **Step 3:** `gh pr create --repo usaturn/create-reso-world --base main --head feat/issue-236-test-integration`（draft にしない）。本文は `Closes #236`、変更の概要、Spec の決定と理由、実行方式と理由、検証と結果、計測と一覧の要約、持ち越し候補、作業時間と Task ごとの内訳
- [ ] **Step 4:** #228 に、計測の結果・子ごとの内訳・段ごとの累計・`groups.md`・`mayoi.md`・持ち越し候補・Spec の一覧へのリンク（PR の head の commit の blob）をコメントし、読み戻す。#236 に PR と #228 のコメントの URL をコメントする

### Task 6: PR 修正ループ（`--merge`）

テストの要否: 書かない。修正が要るときは review-fix-planning の手順と `AGENTS.md` の「テストの採用基準」に従う。

- [ ] **Step 1:** `herdr-agent-task set "PR #<番号> レビュー・マージ"`。`PARENT_ROOT/.agents/skills/pr-review-fix-loop/SKILL.md` をファイルとして読む
- [ ] **Step 2:** `uv run --project "$PARENT_ROOT" --locked python "$PARENT_ROOT/.agents/skills/pr-review-fix-loop/scripts/loop.py" start "<PR の URL>" --controller-model claude-opus-5-5 --controller-runtime claude-code`（ループ用のオプションは無い）
- [ ] **Step 3:** 以降は pr-review-fix-loop の SKILL.md のとおり。修正で一覧が変わったら、#228 のコメントを直す（Spec の D-236-15）。1 サイクル目で修正不要かつ HEAD が Task 4 の記録と同じなら、その検証の記録を `--checks-file` に使う

### Task 7: 終わり

テストの要否: 書かない。確かめは、`main` での計測（Step 1）と予約の ref が無いこと（Step 2）。

- [ ] **Step 1:** マージされたら、`main` で #228 の「計測」を実行し、値が PR の head と同じことを確かめる（違えば #228 に補足する）。#236 に結果（マージ commit・計測・#228 のコメント・ループの結果）を書く
- [ ] **Step 2:** 予約を `git push --force-with-lease=refs/heads/agent-claims/issue-236:4163db8351cc360b9f18381522e6518b881f072c origin :refs/heads/agent-claims/issue-236` で解放し、ref が無いことを確かめる
- [ ] **Step 3:** 使い捨ての worktree `/tmp/issue236-base.aRDoQX/wt` を `git worktree remove` で外す（force しない）。セッションディレクトリは、一覧の元のデータを利用者の判断に使えるよう残し、完全パスを報告する
- [ ] **Step 4:** Herdr のタスクを completed にし、issue-to-pr の 5 章の項目で報告する

## 実行方式

`superpowers:subagent-driven-development`。Task 2 は 6 つの独立した読むだけの作業（子の Spec は合わせて約 930KB、関数は着手時に 891、載せ直しの後は 892）で、文脈を依頼のファイルで渡しきれる（issue-to-pr の表: `self` が true で、Task が独立し、同期の委譲を使える）。

- Task 1 は実装の担当（sonnet）に依頼し、Task のレビュー（sonnet）を行う
- Task 2 の 6 つは、互いに別のファイル（リポジトリの外）だけを書き、commit も git の書き込みもしないので、並行で依頼する（SDD の「並行で依頼しない」は同じファイルの競合を避けるためで、ここには当たらない。ledger に Ruling として書く）。担当は sonnet、レビューは領域ごとに sonnet
- Task 3 は、6 つの結果と共有の条件（数え方・並べ順）を統合する Task なので controller が行い（`review-fix-planning` の `references/convergence.md` の「共有する条件の確認は統合担当の Task」）、Task のレビューをサブエージェントに依頼する
- ブランチ全体のレビュー（Task 4）は最も能力の高いモデル（opus）
- SDD の ledger・依頼・報告・レビューの資料は、worktree の中ではなく `…/sdd/` に置く（`AGENTS.md` の「worktree の中にコミットしないファイルを作らない」。`task-brief`・`review-package` は出力先の引数で使う）

## 実行予算

`.agents/execution-budget.md` に従う。ledger は `/workspaces/reso-world/tmp/agents/issue-236.15yls_nc/budget.jsonl`（2026-10-24T15:57:32Z 開始。予約は 15:50Z、着手の確認は 15:45Z ごろからで、その約 12 分は ledger に入っていない）。

- 全体の能動時間: 480 分。根拠: 同じボードの #230 は 450 分の予算でループ 2 サイクル、#233 は約 3.5 時間でループ 3 サイクル。この子のコードの変更は小さいが、6 つの領域の分類（関数は着手時に 891）と一覧の結合が加わる
- phase の目安: 準備と設計 70 分、Task 1 20 分、Task 2 60 分（並行）、Task 3 45 分、Task 4 40 分、Task 5 20 分、Task 6 180 分（3 サイクル ×（レビュー 45 分＋計画・修正 15 分））、Task 7 15 分、余り 30 分
- worker の期限: Task 2 の担当は依頼から 75 分。過ぎたら止め、失敗として 1 回だけ依頼し直す。ほかのサブエージェント（レビュー）は 30 分。ループのレビュアーの期限はループの設定のとおり（45 分）
- 再試行の上限: 同じ失敗の再試行は 1 回（ledger の `retry_limit` 1）
- checkpoint: phase の境界、予算の 50%（240 分、2026-10-24T19:57Z ごろ）、100%（23:57Z ごろ）、worker が失敗した直後
- 縮小・切り出し・方法変更の候補: (1) 領域の分類が期限に収まらなければ、その領域の単位をファイル × 重さの群に下げ（子の表のファイルごとの節を使う）、Spec の決定記録に縮小として書く。(2) Task 2 のレビューで食い違いが多い領域は、食い違いの種類ごとにまとめて直させ、全件をやり直さない。(3) PR 修正ループがサイクルの上限に達したら、修正を push した状態で止まって報告する（延長は利用者が決める）

## 完了

（実行の後に記録する）
