# Issue #322 新しく作ったリポジトリの Spec・Plan をそのリポジトリに置く

- 文書管理リポジトリ: usaturn/create-reso-world（この子の実装の対象も create-reso-world）
- Issue: [#322](https://github.com/usaturn/create-reso-world/issues/322)（ボード [#320](https://github.com/usaturn/create-reso-world/issues/320) `new-dev-procedures-board` の子 `spec-plan-in-new-repo`）
- 基準: `main` の `afa86e0967ec71135a37365fd15933e819acf6e1` で設計・実装した（Issue の調査時点の `4aa1ca04` から、範囲外の #327 だけが進んだ）。push の前に `main` が `163717cd7aa92fe62cd866c37c70a7f6d7d18f1f`（#332・#333）に進んだので、利用者の指示で `163717cd` に rebase した
- 状態: completed（PR #335 の PR 修正ループのサイクル 1 で修正不要と判定。内容の承認（`approved`）は記録していない）
- 実行許可: 利用者の指示 `/issue-to-pr #322 --merge`。issue-to-pr スキルにより、推奨案で Spec・Plan・実装・検証・PR まで進め、PR 修正ループで修正不要と確かめられたらループの `finalize.py` がマージする。これは実行の許可であり、内容の承認（`approved`）ではない。push の前に base が動いて止まった後、利用者の指示「rebase して、そのまま PR を出してください」で、`163717cd` への rebase と、検証のやり直し・PR・ループへの継続を許可された
- 作成: Claude Code（Opus 5.5、`claude-opus-5-5`）。決定はすべてエージェントの判断で、利用者の承認ではない
- Plan: `docs/superpowers/plans/2026-11-07-create-reso-world-issue-322-spec-plan-in-new-repo.md`

## 目的

新規開発の手順・スキル（#323・#324・#325・#328・#329）で新しく作るツール・ワールド・ResoLoop プラグインのリポジトリでは、superpowers の Spec・Plan をそのリポジトリの `docs/superpowers/specs/`・`plans/` にコミットできるようにする。今の「どのリポジトリの作業でも create-reso-world に置く」規則を改め、規約・確認用コピーの補助・スキルの本文をそろえる。

## 守る前提（#320 から写す）

利用者の決定（2026-11-07）のうち、この子に関係するもの。議論し直さない。

- ツール・ワールドの作成のために superpowers で作った Spec・Plan は、新しく作ったそのリポジトリにコミットする（6 点目）
- 新しく作るプラグインのリポジトリでも同じ。既存の usaturn/resoloop-meshy と ResoLoop 本体は、今までどおり create-reso-world に置く（9 点目）
- 既存のリポジトリ（usaturn/resonite-emission-editor・usaturn/reso-world-Halloween・usaturn/reso-world-sensoji・usaturn/reso-workshop・usaturn/resoloop-meshy）は、今までどおり create-reso-world の配下に置き、そのための新しいリポジトリは作らない。独自のリポジトリを持たないワールドも create-reso-world に置く（10 点目）

「ResoLoop の開発との関係」の条件のうち、この子に関係するもの。

- 条件 1: `AGENTS.md` の「リポジトリ境界」「ResoLoop の版管理」、`README.md`、`docs/resoloop-fork-workflow.md`、`docs/resoloop-meshy-workflow.md`、`scripts/resoloop-fork.sh`、`scripts/resoloop-meshy.sh` を変えない
- 条件 6: ResoLoop 本体と既存の usaturn/resoloop-meshy の Spec・Plan は create-reso-world に置く。`scripts/superpowers_context.py` の fork と上流の照合（`FORK_REPOSITORY`・`UPSTREAM_REPOSITORY`）の挙動は変えない

## 範囲

変えるもの（Issue の「変えてよいもの」の中だけ）:

- `AGENTS.md` の「Spec・Plan の保存と公開」
- `docs/superpowers/README.md`
- `docs/external-tools-workflow.md` の冒頭の Spec・Plan の 1 文
- `scripts/superpowers_context.py`・`scripts/superpowers_review_copy.py`・`scripts/superpowers-review-copy.sh` と、`tests/scripts/test_superpowers_context.py`
- `.agents/skills/issue-to-pr/SKILL.md` と、その手順を実行するテスト `.agents/skills/issue-to-pr/tests/test_base_workflow.py`
- `.agents/skills/review-fix-planning/SKILL.md`
- `.agents/skills/agent-handoff/SKILL.md`・`.agents/skills/agent-handoff/references/handoff-schema.md`
- `.agents/skills/planning-parallel-issues/SKILL.md`・`.agents/skills/planning-parallel-issues/references/session-workflow.md`
- この Spec と Plan

変えないもの: Issue の「変えないもの」のすべて（`AGENTS.md` のほかの節、`docs/external-tools-workflow.md` の「新しい通常ツールを追加する」、既存の Spec・Plan、fork と上流の照合、ResoLoop・Meshy の手順書とスクリプト、`external/`・`worlds/`、`README.md`）。`tools/external_tools/` も変えない（決定 D1 で台帳を使わないため）。`.agents/skills/review-fix-planning/scripts/finalize.py` と `references/execution.md` も変えない（決定 D8）。

## 設計

### 対象のリポジトリの見分け方

対象のリポジトリは、自分の `AGENTS.md` に次の 1 行（以下「宣言」）をコミットする。

```markdown
<!-- superpowers-documents: this-repository -->
```

補助（`scripts/superpowers_context.py`）は、checkout の `HEAD` のコミット済みの `AGENTS.md` の blob に、前後の空白を除いてこの文字列と一致する行があるかで判定する。作業ツリーと index の変更は見ない。宣言があっても、次のリポジトリは対象にしない（特別な経路を持つため、補助が固定で拒否する）。

- usaturn/resoloop・orange3134/resoloop（ResoLoop 本体）
- usaturn/resoloop-meshy（既存の Meshy プラグイン）

create-reso-world 自身は、今までどおりの経路（自分の `docs/superpowers/`）で、宣言とは関係しない。既存の 4 つのリポジトリ（usaturn/resonite-emission-editor・usaturn/reso-world-Halloween・usaturn/reso-world-sensoji・usaturn/reso-workshop）は宣言を持たず、規約で宣言を足さないと定める。宣言の無いリポジトリ（この子の用語で「未登録のリポジトリ」）の Spec・Plan は create-reso-world に置く。

### 補助の入力と出力

`scripts/superpowers_context.py` と `scripts/superpowers_review_copy.py`（`scripts/superpowers-review-copy.sh`）に、任意の `--doc-repo OWNER/REPO` を足す。

- 省略時（空も同じ）は `usaturn/create-reso-world`。今の呼び出し方（`--doc-root`・`--parent-root`・`--path`・`--name`）は、そのまま create-reso-world の文書をコピーする
- create-reso-world 以外を指定すると、`DOC_ROOT` に次をすべて求め、どれかが欠ければ終了コード 66 で止まる（文書を別のリポジトリに置かない）
  1. 指定したリポジトリが ResoLoop 本体・usaturn/resoloop-meshy でない
  2. `DOC_ROOT` の `origin` があり、指定したリポジトリを指す
  3. `DOC_ROOT` の `HEAD` の `AGENTS.md` に宣言がある
- `--doc-repo` を `--doc-root` なしで渡したときは、照合するものが無いので無視する（review-fix-planning の context のブロックは、`DOC_ROOT` が決まる前に、前の出力の `document_repository` を渡して再実行するため。全体レビューの I-1）

共通 context の JSON に `document_repository` を足す。Spec・Plan をコミットするリポジトリを表す。

- `review-copy`: 照合した `--doc-repo` の値
- `review-workspace`・`review-fix`: コード側の checkout（`code_root`）の `HEAD` の宣言から決める。対象のリポジトリなら `repository`、それ以外（create-reso-world、ResoLoop 本体、Meshy、宣言の無いリポジトリ）は `usaturn/create-reso-world`。`DOC_ROOT` も渡したときは、照合した `--doc-repo` がこの値と一致しなければ止まる（宣言のあるリポジトリの文書を create-reso-world に置く誤りと、その逆の誤りを止める）

### 作業先の関係

- `PARENT_ROOT` は変えない。確認用コピーは、対象のリポジトリの文書でも `PARENT_ROOT` の `tmp/superpowers-review/` と `docs_draft/superpowers/` に置く。利用者が読む場所を 1 か所に保つ
- `DOC_ROOT` は Spec・Plan をコミットする checkout または worktree。対象のリポジトリでは、そのリポジトリの作業用の worktree で、普通は `CODE_ROOT` と同じ
- `CODE_ROOT` は変えない

### issue-to-pr

- 2 章の 5 の対象の解決で得た context の `document_repository` と `repository`（どちらも helper が小文字にした名前）を比べ、違うかを `DOCS_SEPARATE` にする。文書用の worktree・base・diff・scan・push・PR を作る条件を、`TARGET_REPO` が create-reso-world でないことから、`DOCS_SEPARATE` が `false` でないことに変える。利用者や Issue の本文の綴り（大文字を含む `TARGET_REPO`）では比べない（全体レビューの I-2）
- `DOCS_SEPARATE` が `false`（create-reso-world 自身と、宣言のある登録済みの通常ツール）なら、`DOC_ROOT="$CODE_ROOT"` とし、Spec・Plan をコードと同じ PR に入れる。文書専用の PR を出さない
- 別シェルの `pr` ブロックは、`DOCS_SEPARATE` を `$SESSION/target.json` から決め直す
- issue-to-pr が扱う対象は変えない（宣言のあるワールドのリポジトリは「リポジトリ境界」の未登録の repo なので、今までどおり issue-to-pr の対象外）

### review-fix-planning

- 共通 context の 2 つのブロックに `--doc-repo "${DOC_REPO:-}"` を足し、最初のブロックで `DOC_REPO` を出力の `document_repository` から読む
- Spec を PR の head に載せる条件を、「PR が create-reso-world のもの」から「`DOC_REPO` が `PR_REPO`（create-reso-world と、宣言のあるリポジトリ）」に広げる。それ以外は今までどおり create-reso-world の文書用ブランチに置く
- 宣言のあるリポジトリは「マージしてよい範囲」の外（登録済み通常ツールか未登録の repo）なので、結論 2 には進まず、`finalize.py` の `--spec-commit` も使わない。結論 3 の「書き始めた Spec の扱い」は create-reso-world の PR と同じ規則にする。マージしてよい範囲と `finalize.py` は変えない

### planning-parallel-issues・agent-handoff

- 子のコードの対象が宣言のあるリポジトリなら、その子の Spec・Plan は、利用者か確認済みの引き継ぎが示したそのリポジトリの checkout にコミットする。checkout が示されていなければ、create-reso-world に代わりに置かずに止まる
- handoff の `sources.doc_root` は、Spec・Plan をコミットした checkout（create-reso-world か、宣言のあるリポジトリ）を書く

### 対象のリポジトリに置く説明

規則は create-reso-world の `docs/superpowers/README.md` にだけ定める。対象のリポジトリの `AGENTS.md` には、宣言の行と、その規則へのリンクを書いた 1 文だけを置く。`docs/superpowers/README.md` の「保存先」に、置く文の例を書く（#325・#329 が雛形に写し、#323・#324・#328 が手作業の手順に書く）。

## 決定記録

| # | 決めること | 選択した案 | 検討した別案 | 選択理由 | 委任指示・停止条件 |
| --- | --- | --- | --- | --- | --- |
| D1 | 対象のリポジトリの見分け方 | 対象のリポジトリの `AGENTS.md` の宣言の行 | `external-tools.toml` の項目、create-reso-world に新しい一覧、`docs/superpowers/` の有無 | ワールドのリポジトリは `external/` に無く台帳に入らない。#325 のスキルは create-reso-world を push の対象にできない（#320 の条件 4）ので、create-reso-world 側の一覧はリポジトリごとに別の PR が要る。ディレクトリの有無は意図せず当たる | issue-to-pr の推奨案で決めた |
| D2 | 宣言の形 | `<!-- superpowers-documents: this-repository -->` の 1 行を、`HEAD` のコミット済みの `AGENTS.md` から読む | 作業ツリーの `AGENTS.md`、別の設定ファイル（TOML） | エージェントが読む `AGENTS.md` に人向けの説明と並べて置ける。コミットした状態だけを根拠にする | 同上 |
| D3 | 必ず除くリポジトリ | ResoLoop 本体の 2 つと usaturn/resoloop-meshy を補助で固定して拒否する。既存の 4 つは規約で宣言を足さない | 既存の 4 つも補助で固定する、何も固定しない | 特別な経路（「リポジトリ境界」と各手順書）を持つリポジトリだけを固定する。既存の 4 つは宣言を持たないので既に対象外で、一覧を補助に増やす保守の負担を避ける | 同上 |
| D4 | 補助の入力 | 任意の `--doc-repo`（省略時は create-reso-world） | `DOC_ROOT` の origin から自動で決める | 呼び出す側が文書を置くリポジトリを明示し、別の checkout を渡した誤りを origin の照合で止められる。省略時の挙動が今と同じ | 同上 |
| D5 | 期待する置き場所の出力 | 共通 context の JSON に `document_repository` を足し、`DOC_ROOT` を渡したときは一致を求める | エージェントが `AGENTS.md` を読んで決める | issue-to-pr の手順のシェルが同じ規則で分岐でき、置き場所の取り違えを補助が止める | 同上 |
| D6 | `PARENT_ROOT`・`DOC_ROOT`・`CODE_ROOT` | `PARENT_ROOT` と確認用コピーの置き場所は変えない。`DOC_ROOT` は対象のリポジトリの worktree（普通は `CODE_ROOT`） | 確認用コピーを対象のリポジトリに置く | 利用者が読む場所が 1 か所のまま。対象のリポジトリの作業ツリーにコミットしないファイルを作らない（「コミットしないファイルの置き場所」） | 同上 |
| D7 | issue-to-pr の経路 | context の `document_repository` が `repository` と同じ（`DOCS_SEPARATE` が `false`）なら Spec・Plan をコードの PR に入れ、文書専用の PR を出さない | 宣言のある repo でも create-reso-world に文書専用の PR を出す | 利用者の決定（6 点目）のとおり、そのリポジトリにコミットする | 同上 |
| D8 | review-fix-planning の経路 | Spec を PR の head に載せる条件を `DOC_REPO == PR_REPO` に広げる。マージしてよい範囲・`finalize.py` は変えない | 宣言のある repo の結論 2 で Spec だけを push する経路を新しく作る | 宣言のある repo は手動マージで結論 2 に進まないので、新しい経路は要らない。create-reso-world の PR と同じ規則で足りる | 同上 |
| D9 | 公開・承認・状態の規則 | 対象のリポジトリにもそのまま適用する（`draft` でコミット、承認はコミットの SHA に結び付ける、issue-to-pr では確認用コピーを作らない） | 対象のリポジトリだけ別の規則にする | 同じ規則で、置き場所だけが変わる方が誤りにくい | 同上 |
| D10 | 対象のリポジトリに置く説明 | 宣言の行と、create-reso-world の `docs/superpowers/README.md` へのリンクの 1 文だけ | 同じ説明を対象のリポジトリにも複製する | 複製すると食い違う。create-reso-world は公開なので、リンクは単独の clone からも辿れる | 同上 |
| D11 | PR 本文の Issue の指定 | `Refs #322`（ボードの子） | Issue 本文の「成果物」にある `Closes #322` | issue-to-pr の規則（ボードの子は `Refs #N`、close と親の更新はマージの後に調整役が行う）は変えないと定めている。マージの後に、結果を #322 にコメントする | issue-to-pr の規則に従う |
| D12 | 範囲外の食い違い | `README.md` の「変更の流れ」の「設計と実装計画は、対象のリポジトリにかかわらず `docs/superpowers/` に置く」は直さず、#320 にコメントする | この PR で直す | `README.md` は #321・#325 の担当で、この子は変えない（Issue の「変えないもの」） | 範囲を広げない |
| D13 | テスト | S の守りだけを、実装しているモジュールのテストに足す（補助の拒否と正常系、issue-to-pr の手順の分岐） | 文書の文言の照合、確認用コピーの正常系の追加 | 文言の照合は F。コピーの正常系は、壊れるとエラーで止まる L で、create-reso-world の正常系は既存のテストにある | 「テストの採用基準」に従う |

## インターフェース

- 宣言の行: `<!-- superpowers-documents: this-repository -->`（対象のリポジトリの `AGENTS.md`）
- 補助の引数: `--doc-repo OWNER/REPO`（`scripts/superpowers_context.py`・`scripts/superpowers_review_copy.py`・`scripts/superpowers-review-copy.sh`）
- 補助の出力: 共通 context の JSON の `document_repository`
- 変えない: `--doc-root`・`--parent-root`・`--path`・`--name`・`--commit` の意味、終了コード（64・65・66、コピーの 1・2）、create-reso-world と ResoLoop・Meshy の文書の経路

## 受け入れ基準

- 動作環境: この Dev Container（Python 3.14、uv、Git）。テストは一時の Git リポジトリと偽の remote（URL だけ、または一時の bare リポジトリ）で行い、実在の GitHub に書き込まない
- 実入力: `AGENTS.md` は日本語を含む複数行の UTF-8。宣言はその中の 1 行。リポジトリは `https://github.com/<owner>/<repo>.git`・`git@github.com:<owner>/<repo>.git` の形の origin
- 防御範囲:
  - 拒否（終了コード 66、文書を置かない）: `--doc-repo` に usaturn/resoloop・usaturn/resoloop-meshy を指定した（宣言があっても）、宣言が無い（作業ツリーにだけある宣言を含む）、origin が無い、origin が `--doc-repo` と違う、`review-fix` で `--doc-repo` が `--repo` と違う、宣言のあるリポジトリのコードに create-reso-world の `DOC_ROOT` を渡した
  - 正常（正しく通る例）: 宣言のあるリポジトリの checkout を `DOC_ROOT` に `--doc-repo` 付きで渡す（`review-copy`・`review-fix`）。create-reso-world の文書は、今の呼び出し方でコピーできる（既存のテスト）
  - issue-to-pr: 宣言のある登録済みの通常ツールでは、`TARGET_REPO` の綴りに大文字が混じっていても、文書用の worktree と create-reso-world の PR を作らず、PR は対象のリポジトリの 1 つだけ。宣言の無いツール・ResoLoop では今までどおり 2 つ（既存のテスト）
- ResoLoop の fork・上流の照合の既存のテストが、変えずに通る
- `AGENTS.md`・`docs/superpowers/README.md`・`docs/external-tools-workflow.md`・4 つのスキルの記述が、改めた規則で食い違わない

## 検証

Issue の「検証」のとおり。

- `bash tests/scripts/test-superpowers-python.bash`
- `uv run pytest tests/skills .agents/skills .agents/scripts tools`
- `bash .devcontainer/run-tests.bash`
- `bash scripts/check-layout.sh`
- `git diff --check`
- 確認用コピーの実行（一時のリポジトリで、宣言のあるリポジトリの文書を `--doc-repo` 付きでコピーする）。コミットしない確かめとして行う

## 実装の確認

実装は Plan の Task 1〜4（inline、`superpowers:executing-plans`）。ledger は `tmp/agents/issue-322.8ncdx5jc/sdd/2026-11-07-create-reso-world-issue-322-spec-plan-in-new-repo/progress.md`（`PARENT_ROOT` 基準。コミットしない）。

| 条件 | 観測した結果 | 方法 |
| --- | --- | --- |
| 宣言・除外・origin の照合で止まる | 作業ツリーにだけある宣言、origin の食い違い、usaturn/resoloop-meshy で終了コード 66。宣言のあるリポジトリの checkout は `review-copy`・`review-fix` で通る（大文字を混ぜた `--doc-repo` も通る） | `tests/scripts/test_superpowers_context.py` の `test_own_documents_route_requires_declaration_origin_and_matching_code`。宣言・除外・不一致・origin・`document_repository` の計算・作業ツリーを読む実装の各変異で FAIL を確認 |
| `document_repository` と一致の要求 | 宣言のあるリポジトリのコードに create-reso-world の `DOC_ROOT` を渡すと 66。宣言の無いリポジトリと create-reso-world は `usaturn/create-reso-world` | 同上 |
| 確認用コピー | 一時のリポジトリで、`--doc-repo` 付きは `created` で内容が一致し、外すと終了コード 1（`--doc-root origin`） | コミットしない確かめ（`superpowers-review-copy.sh` を実行） |
| issue-to-pr で文書を分けない | 宣言のある通常ツール（`TARGET_REPO=Sample-Owner/Other-Tool`）で、PR は対象のリポジトリの 1 つだけ、文書用 worktree なし、scan はコードの worktree だけ。宣言の無いツール・ResoLoop は今までどおり 2 つ | `.agents/skills/issue-to-pr/tests/test_base_workflow.py`。大文字の綴りは修正前に RED |
| review-fix-planning の context の再実行 | `DOC_ROOT` が空のまま 2 回実行して、2 回目も終了コード 0 | コミットしない再現（修正前は `DOC_ROOT is required` で 66） |
| 記述がそろう | 範囲内のファイルに旧規則の文言が無い | Plan の Task 4 の Step 2 の `grep`、`bash scripts/check-layout.sh` |

全体レビュー（新しいサブエージェント 1 つ、Opus）の指摘と扱い:

- 対応した: I-1（上の再実行）、I-2（大文字の綴り）、M-4（書き直した `AGENTS.md` の行の「正本」）、M-5（planning-parallel-issues の checkout の扱いを issue-to-pr に合わせた）、M-6（テストの書きすぎ。L の終了コード 64 の確認と、D の重複 3 件を除いた）、M-7（作業ツリーにだけある宣言を拒否する S のケースを足した）
- 持ち越し（壊れても止まるだけ、または起きる見込みが低い）: M-1（issue-to-pr は宣言を常設 checkout の `HEAD` から読み、`CODE_BASE_SHA` からは読まない）、M-2（`--doc-repo` の `.git` は取り除かれず、紛らわしい診断で止まる）、M-3（宣言したリポジトリの `DOC_ROOT` は origin が対象を指す checkout に限る）

全体の検証（Plan の Task 5 の Step 1）は、`163717cd` に rebase して、この記録をコミットした後の HEAD で実行し、コマンド・終了コード・ログのパスを PR の本文と `tmp/agents/issue-322.8ncdx5jc/verify-final/` に残す。

## PR 修正ループ（PR #335、サイクル 1）

- PR: https://github.com/usaturn/create-reso-world/pull/335（head `824766652f4906c4a565dbdbead14012e251cd13`、base `main` の `163717cd7aa92fe62cd866c37c70a7f6d7d18f1f`）
- 実行許可: `/issue-to-pr #322 --merge` と、再開の指示「rebase して、そのまま PR を出してください」。review-fix-planning の完遂として、修正不要ならマージと関連 Issue の更新まで行う
- planner: claude-opus-5-5（Claude Code）。loop の run: `reviews/usaturn/create-reso-world/#335-feat-issue-322-spec-plan-in-new-repo/loop/fe950b9dbee14bf5a97392b5d2092e9e/`
- 結論: 2 修正不要（判断の記録は `no_fix_needed`）。修正と自己レビューは無い

| レビューファイル | モデル | ランタイム | レビュー HEAD | 再実行 | Merge recommendation |
| --- | --- | --- | --- | --- | --- |
| `gpt-6.1-sol` | gpt-6.1-sol | pi | `824766652f49` | はい | Approve |
| `SWE-2-Max` | SWE-2 Max | devin | `824766652f49` | はい | Approve |

- `pi_commandcode_deepseek4-flash_max` は runner の期限切れ（`timed_out`、終了コード -15）で受け付けられなかった。指摘 0 件ではなく失敗として扱い、入力に含めていない
- 指摘: 2 人とも 0 件（`findings/` の候補も 0 件）。確認済みの一覧（`verified/`）は、確かめる候補が無いので作っていない
- 要件との照合: PR の約束は Spec の「受け入れ基準」と同じで、「実装の確認」の表のとおり確かめた。このサイクルで変えたコードは無い
- 検証: issue-to-pr が記録した検証を使った（同じ HEAD `824766652f49`、作業ツリーは clean、base `163717cd` は head の祖先で、サイクル中も先端は変わっていない）。`bash tests/scripts/test-superpowers-python.bash`・`uv run --project . --locked pytest tests/skills .agents/skills .agents/scripts tools -q`（1309 passed）・`bash .devcontainer/run-tests.bash`・`bash scripts/check-layout.sh`・`git diff --check 163717cd...HEAD` がいずれも終了コード 0。ログは `tmp/agents/issue-322.8ncdx5jc/verify-final/`（`PARENT_ROOT` 基準）
- PR 本文: 決定 D11 の説明に書いた自動で閉じるキーワードの文字列を、GitHub が close の指定として読んでいた（`closingIssuesReferences` に #322）。ボードの子は参照だけにする方針なので、その文を言い換えて本文を直し、close の対象が無くなったことを確かめた
