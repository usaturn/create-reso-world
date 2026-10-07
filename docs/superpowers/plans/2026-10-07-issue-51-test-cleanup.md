# Issue #51 不要なテストの削除 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 全テストを採用基準で分類して不要な検査を削除し、採用基準を `AGENTS.md` に一本化して計画・レビューで使う。

**Architecture:** 規則を先に入れ、その基準で領域ごとに棚卸し・削除する。分類表は Spec の付録に領域ごとに書く。最後に規則の前後で行動を比べ、全テストの前後比較を記録して 1 本の PR にする。

**Tech Stack:** Bash、Python（uv / pytest / unittest）、Git、GitHub CLI、Claude Code CLI（行動比較）。

**Spec:** `docs/superpowers/specs/2026-10-07-issue-51-test-cleanup-design.md`

- 文書管理・対象リポジトリ: `usaturn/create-reso-world`、Issue #51、PR #53
- 状態: completed（実装・検証・PR 作成まで完了。内容の明示承認は未取得で、実行許可に基づく。マージは未実施）
- 基準 HEAD: `a94f04eea41fce3fb344dd4a7f10a7a0692512c2`
- 実行方法: subagent-driven-development。Task を直列に実行し、各 Task の後に読み取り専用のレビューを挟む
- 実行許可: 利用者の「その他は途中で止めずに推奨案で進めて、PR まで作成して」。内容の承認とは区別する。マージは含まない

## Global Constraints

- CODE_ROOT / DOC_ROOT: `/workspaces/reso-world/.worktrees/issue-51-test-cleanup`。PARENT_ROOT: `/workspaces/reso-world`（基準 HEAD の detached checkout。編集しない）
- 編集してよいもの: 担当領域のテストと、その fixture・helper・probe・runner・テスト設定、分類表の担当節。Task 1 は `AGENTS.md` と 2 つの `SKILL.md` の指定箇所も
- 新しいテストファイルを作らない。消した検査を別の語句一覧・件数固定・弱い assertion・新しい汎用パーサで置き換えない
- テストを通すために実装・文書・schema・受入条件を変えない
- 保護: `.pi/APPEND_SYSTEM.md`、凍結した Spec・Plan、#12 の証跡・採用 run・manifest・生成物、`MyResoniteProject/.resoloop/tokyo-nova/pipeline.json`、外部配布のスキル、`external/resoloop`。Resonite のライブ操作はしない
- 次は「理由付き固定値として維持」を既定とする（消すなら理由を分類表に書く）: ペルソナ SHA、過去文書の SHA manifest、mount 一覧、unset 環境変数の一覧、gitignore の追跡例外
- Python は uv で実行する。シェル変数を使う `rm` は `${VAR:?}` で守り、パス全体を引用する
- worktree に書く担当は同時に 1 つ。レビュー担当は読み取り専用。担当は自分の領域と分類表の担当節だけをコミットする。Spec・Plan の状態、push、PR は controller が扱う
- 各担当は所要時間を報告する

## 各 Task 共通のテスト要否

全 Task で**テストなし**。理由: 作業がテストの削除・統合・書き換えと文書の変更で、守る実行時の挙動を新しく加えないため。代わりの検証は各 Task の手順に書く。

## Review Focus

1. 消した実行テストだけが持っていた失敗ケース（誤対象の削除、中断時の後始末、認証の隔離）が、残りの検査から消える
2. 消したファイルを runner・pytest 設定・helper が参照し続け、収集エラーになるか、黙って実行されなくなる
3. 理由付き固定値の検査を、文面検査と一緒に消す
4. ワールドの証跡・manifest・生成物を、テストの fixture と誤って消す
5. 書き換えた検査が、同じ現行値から期待値を作る恒真の検査になる

各 Task の検証手順が 1〜5 を確かめる。

---

### Task 1: 採用基準とレビュースキルへの参照

**Files:**
- Modify: `AGENTS.md`（「基本方針」のテスト 3 項目の削除、`## テストの採用基準` の追加）
- Modify: `.agents/skills/pr-review/SKILL.md`（「優先順位」の直後に 1 行）
- Modify: `.agents/skills/review-fix-planning/SKILL.md`（「テストを足すのは、致命的な指摘の修正と検証に要るときだけである」の文に 1 文）
- Create: `docs/superpowers/specs/2026-10-07-issue-51-test-inventory.md`

**テストの要否:** テストなし。文書と規則だけの変更で、守る実行時の挙動が無い。

- [x] **Step 1: `AGENTS.md` を変える**
  Spec 第 2 章のとおり、「基本方針」の 3 項目（「スキル superpowers の TDD で進める場合…」「TDD に限らず…」「安全な操作範囲、schema…」）を削除し、「基本方針」の直後に Spec の節をそのまま入れる。
- [x] **Step 2: 2 つの `SKILL.md` に 1 行ずつ足す**
  Spec 第 3 章の文をそのまま入れる。
- [x] **Step 3: 分類表の骨組みを作る**
  冒頭に Spec と同じ管理情報を書き、`## 前後比較`、`## スキルのテスト`、`## tests/scripts`、`## .devcontainer`、`## MyResoniteProject・akichi`、`## slum02`、`## slum03` の節を置く。各領域の節には列見出し `| 場所 | 検出する不具合 | 判断 | 理由 | 代わりの保証 | 関連 |` を置く。
- [x] **Step 4: 代わりの検証**
  `uv run pytest tests/skills -q`（frontmatter）、`bash tests/scripts/test-instructions.bash`（`CLAUDE.md` の読み込み指定・参照の実在）、`git diff --check`、`git diff` で変更が指定箇所だけであることを確認する。
- [x] **Step 5: コミット**
  `docs: add test adoption criteria (issue 51)`

### Task 2〜7: 領域ごとの棚卸しと削除

| Task | 領域 | 実行する suite |
| --- | --- | --- |
| 2 | `tests/skills/*.py`、`.agents/skills/*/tests/*.py` | `uv run pytest tests/skills .agents/skills -q` |
| 3 | `tests/scripts/`（Python 3、シェル 11）と `test-superpowers-python.bash` の重複実行 | `uv run pytest tests/scripts -q`、`bash .devcontainer/run-tests.bash tests/scripts/*.bash` |
| 4 | `.devcontainer/test-*.bash`、`.devcontainer/tests/` | `bash .devcontainer/run-tests.bash .devcontainer/test-*.bash` |
| 5 | `MyResoniteProject/tests/`、`akichi/tests/` | 各プロジェクトで `uv run pytest -q` |
| 6 | `slum02/tests/` | `(cd slum02 && uv run pytest -q)` |
| 7 | `slum03/tests/` | `(cd slum03 && uv run pytest -q)` |

ワールド（Task 5〜7）は各プロジェクトの `AGENTS.md` にも従う。

**Files（各 Task）:**
- Modify / Delete: 表の領域のテストと、その fixture・helper・runner の参照
- Modify: 分類表の担当節

**テストの要否:** テストなし。テストの削除・統合・書き換えだけで、新しい挙動を加えない。

- [x] **Step 1: 着手前の状態を記録する**
  担当領域のファイル数・行数（Python とシェルを分ける）と、表の suite の収集件数・結果・所要時間を記録する。着手前から失敗するものは記録し、直さない。
- [x] **Step 2: 全ファイルを読んで分類する**
  Spec 第 4 章で、各ファイル（混在なら関数・assertion）を「削除」「統合」「書き換え」「理由付き固定値として維持」「維持」に分け、分類表の担当節に 1 行ずつ書く。実行するコードのテストを消す行には、同じ経路を守る残りの検査を「代わりの保証」に書く。
- [x] **Step 3: 反映する**
  分類どおりに削除・統合・書き換えを行い、参照が無くなった fixture・helper・import・runner の呼出しを消す。保護対象（Global Constraints）には触れない。
- [x] **Step 4: 代わりの検証**
  - 表の suite を実行し、着手前と同じ失敗以外が無いことを確かめる
  - 書き換えた検査は、worktree の外の一時コピーで「許容すべき変更で成功」「検出対象の誤りで失敗」を確かめる。期待値を変異に合わせて直さない
  - 消したファイル名で `git grep` し、参照が残っていないことを確かめる
  - `git diff --stat` で、領域外と保護対象に変更が無いことを確かめる。`git diff --check`
- [x] **Step 5: コミット**
  `test: prune <領域> tests (issue 51)`。報告に、前後のファイル数・行数・収集件数・所要時間、変異検証の結果、未解決の点を書く。

### Task 8: 行動比較

**Files:**
- Modify: 分類表の `## 行動比較` 節（新設）

**テストの要否:** テストなし。エージェントの判断の比較で、`in`／`not in` のテストでは代用できない（Spec 第 5 章）。

- [x] **Step 1: 場面ごとの prompt を作る**
  Spec 第 5 章の場面 1〜5 を、それぞれ短い依頼文にする。場面 1〜4 は「Plan だけを書く。ファイルは編集しない」、場面 5 はレビューする差分を添える。prompt は scratchpad に置く。
- [x] **Step 2: 前後で実行する**
  各場面を PARENT_ROOT と CODE_ROOT を cwd にして、`claude -p --model sonnet --tools Read,Grep,Glob "<prompt>"` で 1 回ずつ実行し、出力を scratchpad に保存する。
- [x] **Step 3: 比べて記録する**
  場面ごとに、Task のテスト要否の記載、作らない型のテストの有無、場面 4 の回帰テストの有無、場面 5 の指摘の有無を表にする。期待と違う結果は、そのまま記録する。

### Task 9: 前後比較・最終確認・PR

**Files:**
- Modify: 分類表の `## 前後比較`、Spec・Plan の状態

**テストの要否:** テストなし。記録と公開だけの作業。

- [x] **Step 1: 全体の検証**
  Spec 第 6 章のコマンドをすべて実行し、終了コードと所要時間を記録する。
- [x] **Step 2: 前後比較を書く**
  領域ごとのファイル数・行数・収集件数・所要時間を、着手前（基準 HEAD）と比べる。着手前の値は、Task 1 の前に controller が同じ worktree で Spec 第 6 章のコマンドを実行した結果を使う。重複実行をやめた分は二重に数えない。失敗・skip・未確認は理由とともに書く。
- [x] **Step 3: 全体のレビュー**
  読み取り専用のレビュー担当に、ブランチ全体と Review Focus 1〜5 を確かめさせる。
- [x] **Step 4: 公開**
  Spec・Plan の状態と記録を更新してコミットし、push して PR を作る。PR 本文に分類表へのリンク・前後比較・行動比較の要約・検証結果を書き、Issue #51 からリンクする。マージはしない。

## 実行結果

- コミット: `2ed0fe4`（Task 1）、`806866f`（Task 2）、`d424504`・`34d6953`（Task 3、修正 1 回）、`6f3b9f9`（Task 4）、`03ce8a9`（Task 5）、`4109346`（Task 6）、`bc1cb12`（Task 7）、`5889490`（Task 8）、`7d56e48`（最終レビューの修正）
- 各 Task の後に読み取り専用のレビューを行い、Critical・Important が残っていないことを確かめた。最終レビュー（ブランチ全体）の指摘は 1 回の修正で直し、再レビューで解消を確かめた
- 前後比較・行動比較・#36 の判断を見直したもの: 分類表 `docs/superpowers/specs/2026-10-07-issue-51-test-inventory.md`
- 実行中の裁定:
  - 実装担当は Task 1 に haiku、Task 2〜7 に opus、Task 8 に sonnet を使った
  - `AGENTS.md` の採用基準で、`SKILL.md` のバッククォートを外した（参照の実在検査が、リポジトリ直下のパスと解釈するため）。Spec 第 2 章も合わせた
  - Task 8 は、データ収集を Task 4 と並行して読み取り専用で行い、記録は Task 7 の後に行った
  - 最終レビューの「採用基準の『書く』に参照実在・定義元比較・schema を足し、型 6 を足す」提案は採らず、利用者が指示したルール 1〜4 の文面のままにした（PR で判断事項として示す）
  - 削除した検査が副次的に守っていた「`.pi/mcp.json` の API キーが環境変数の参照であること」を、`tests/scripts/test-agent-config.bash` に理由付きで戻した
