# Issue #116 のボード作成 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** #116 を、10 件の子 Issue・GitHub の親子関係・13 本の `blocked_by`・開始手順を持つボード `review-automation-board` にする。

**Architecture:** 子の定義（キー、題、担当ファイル、禁止、先行、入力、完了の証拠、受け入れ、検証）を 1 つの生成スクリプトに持ち、子の本文・親の実行マップ・依存の図と表・API への登録をすべてそこから作る。GitHub への書き込みは 1 件ごとに返った ID を台帳に保存し、読み戻して確かめる。

**Tech Stack:** `gh api`（REST: issues、sub_issues、dependencies/blocked_by）、`uv run --no-project python`（生成と照合のスクリプト）

**Spec:** `docs/superpowers/specs/2026-10-18-create-reso-world-issue116-review-automation-board-design.md`（`b2bd038`）

## 管理

- 状態: draft
- 実行許可: Spec の「管理・実行許可」と同じ（利用者の `/issue-to-pr` の指示と「ボード作成まで」の選択）。子の実装とマージは含まない
- 実行方式: `superpowers:executing-plans`（inline）。各 Task が前の Task の返した Issue の番号・ID を使う逐次の GitHub 操作で、同じ生成スクリプトと #116 の本文を書き換えるため、委譲して並行させる部分が無い

## Global Constraints

- 書き込み先は usaturn/create-reso-world だけ。`gh issue`・`gh pr` には `--repo usaturn/create-reso-world`、`gh api` は `repos/usaturn/create-reso-world/...` の完全な endpoint
- Sub Issue と依存の payload は database の `id`（Issue の番号・node_id ではない）
- 一覧の読み取りは `gh api --paginate`
- 本文は `--input` の JSON ファイルで渡す。Issue の本文をシェルの文字列に埋め込まない
- 子の題は `[#116-N] ...`、状態は planning: not-started / implementation: not-started
- #116 の本文の「着手するエージェントへの注意（利用者決定: 2026-10-18）」は 1 文字も変えない
- 日本語は `AGENTS.md` の「日本語表現」に従う（「正本」「着地」「巡」「席」「実行器」を使わない）
- 作業用のファイルは `PARENT_ROOT/tmp/agents/issue-116.t32o1873/`（`SESSION`）に置き、worktree に置かない

## Review Focus

- 書き込みの途中で API が失敗したとき: 作った子・登録した関係が台帳に残り、同じ書き込みを繰り返さずに続きから再開できる（Task 2・3 は書き込みの前に既存を読み、返った ID を即座に保存する）
- 同じ題の子が既にあるとき（再実行）: 重複して作らない（Task 2 の Step 1 で `[#116-` の題の open Issue を全ページ検索する）
- 子の本文の担当ファイルと親の表の担当ファイルの食い違い、同じファイルを 2 つの子が節の指定なしに持つ: 公開の前に止まる（Task 1 の照合）
- 依存の循環・図と API の辺の数の食い違い: Task 1 で循環を、Task 3 で API の辺の集合と生成元の集合の一致を確かめる
- #116 の本文を利用者が同時に編集したとき: Task 4 は書き込みの直前に `updated_at` と本文のハッシュを読み直し、作業開始時の写し（`SESSION/issue116-body-before.md`、sha256 `05c70776...`）と違えば止まる

---

### Task 1: 子の定義と本文の生成・照合

**Files:**
- Create: `SESSION/board.py`（生成と照合。コミットしない）
- Create: `SESSION/out/child-<key>.md`（10 件）、`SESSION/out/parent-sections.md`

**Interfaces:**
- Produces: `board.py render` が `out/` に本文を書く。`board.py check` が照合の結果を出し、問題があれば終了コード 1。`board.py edges` が `(子のキー, 先行のキー)` の一覧を JSON で出す。`board.py parent --ledger SESSION/ledger.json` が台帳の番号・ID を埋めた親の節を出す

- [ ] **Step 1: 子 10 件の定義を書く**（Spec の D-18・D-19・D-12・D-16・D-17 の値をそのまま使う）。各子に `key`・`n`（1〜10）・`title`・`objective`・`owns`（許可する編集）・`forbids`（禁止する編集）・`preds`（直接の先行のキー）・`inputs`・`evidence`・`interface`・`acceptance`・`verify`・`extra_gate`（`pr-review-v2` の #146 など）を持たせる
- [ ] **Step 2: `check` を実装して実行する**

  確かめること: 各子の `owns` と `forbids` に同じパスが無い。2 つ以上の子の `owns` に出るファイルは、節の指定（`ファイル: 節`）が付き、節が重ならない。先行のキーが実在し、循環が無い。辺の数が 13。

  Run: `uv run --no-project python "$SESSION/board.py" check`
  Expected: `ok: 10 children, 13 edges, no cycle, ownership consistent` と終了コード 0

- [ ] **Step 3: 本文を生成し、目で読む**

  Run: `uv run --no-project python "$SESSION/board.py" render && grep -c '' "$SESSION"/out/child-*.md`
  Expected: 10 ファイル。各本文に「親と目的」「範囲と禁止」「依存」「インターフェース」「受け入れ」「検証」「成果物」「状態と反映先」の節、#116 の注意書きへの参照、`AGENTS.md` の禁止語が無い（`grep -n '正本\|着地\|巡\|席\|実行器'` が 0 件）

テスト: 書かない（一時的な生成スクリプトで、守る挙動はこの作業の照合そのもの）。代わりに Step 2 の照合と Step 3 の目視。

### Task 2: 子 Issue の作成

**Files:**
- Create: `SESSION/ledger.json`（台帳の手元の写し）

**Interfaces:**
- Consumes: Task 1 の `out/child-<key>.md`
- Produces: `ledger.json` の `children[key] = {number, id, node_id, html_url}`

- [ ] **Step 1: 既存の子を探す**

  Run: `gh api --paginate 'repos/usaturn/create-reso-world/issues?state=all&per_page=100' --jq '.[] | select(.title | startswith("[#116-")) | .number'`
  Expected: 空。あれば作らずに台帳へ取り込み、本文の差分を確かめる

- [ ] **Step 2: 1 件ずつ作る**: `gh api -X POST repos/usaturn/create-reso-world/issues --input <title と body の JSON>`。返った `number`・`id`・`node_id`・`html_url` を、次の作成の前に `ledger.json` に書く。応答が不明なら、Step 1 の検索で作られたかを確かめてから進む
- [ ] **Step 3: 子の本文の中の、ほかの子への参照（キー）を番号のリンクに置き換えて PATCH する**（作成の時点では番号が無いため）。PATCH の後に GET し、本文が生成したものと一致することを確かめる

テスト: 書かない（GitHub の操作）。代わりに Step 3 の読み戻し。

### Task 3: 親子関係と依存の登録

**Interfaces:**
- Consumes: `ledger.json`、`board.py edges`

- [ ] **Step 1: 登録の前に、#116 の Sub Issue と各子の `blocked_by` を全ページ読み、空であることを確かめる**
- [ ] **Step 2: 子 10 件を #116 の Sub Issue にする**: `POST repos/usaturn/create-reso-world/issues/116/sub_issues`、`{"sub_issue_id": <子の id>}`。子は新しく作ったので親は無い（`replace_parent` を付けない）
- [ ] **Step 3: 依存 13 本を登録する**: 子 N に `POST .../issues/N/dependencies/blocked_by`、`{"issue_id": <先行の id>}`
- [ ] **Step 4: 読み戻して照合する**

  Run: `gh api --paginate repos/usaturn/create-reso-world/issues/116/sub_issues --jq '.[].number'` と、各子の `gh api --paginate .../issues/N/dependencies/blocked_by --jq '.[].number'`
  Expected: Sub Issue の集合が台帳の 10 件と一致、`blocked_by` の (子, 先行) の集合が `board.py edges` の 13 本と一致。余分な関係が無い

テスト: 書かない。代わりに Step 4 の集合の一致。

### Task 4: #116 の本文の更新

**Files:**
- Create: `SESSION/issue116-body-after.md`

- [ ] **Step 1: 新しい本文を組み立てる**。順序は、状態の 1 行 → 「着手するエージェントへの注意」（元のまま）→ 目的と範囲（元の「目的」の箇条を保ち、完了の条件・範囲外・基準・Spec を足す）→ 実行マップ → 公開台帳 → 依存関係と並行の波 → 共有インターフェースと担当 → 運用ルール → 開始手順 → メモの段階の記録（元の「候補の範囲」「`ec13c3e` の後に移植元で入った主な変更」「持ち込まないもの」「着手するときに決めること」を元の文のまま置き、決めたことに Spec の判断の番号を添える）→ 先行 → 状態。実行マップと公開台帳は `<!-- review-automation-board:map:start -->` などの印で囲む
- [ ] **Step 2: 元の本文の各行が、新しい本文に残っていることを確かめる**（変えてよいのは、冒頭の引用の行と末尾の「状態」の行だけ）

  Run: `uv run --no-project python "$SESSION/board.py" preserved --before "$SESSION/issue116-body-before.md" --after "$SESSION/issue116-body-after.md"`
  Expected: 残っていない行が、意図して変えた冒頭の引用の行と「状態」の行だけ（決めたことは、元の節の後ろに新しい行で足し、元の行を書き換えない）

- [ ] **Step 3: 書き込みの直前に #116 を読み直し**、本文の sha256 が `05c707768efb9d4efcaeb5b561bed485162b807ef568df691edeff66cf3a563f` のままなら PATCH する。違えば止まって差分を報告する
- [ ] **Step 4: 読み戻して、本文が `issue116-body-after.md` と一致し、公開台帳の番号・ID が `ledger.json` と一致することを確かめる**

テスト: 書かない。代わりに Step 2 と Step 4。

### Task 5: 公開

- [ ] **Step 1: Plan の「完了」の節に、作った子の番号・依存の照合の結果・本文の更新の結果・所要時間を書き、commit する**（状態は draft のまま）
- [ ] **Step 2: 検証**: `git -C "$DOC_ROOT" diff --stat origin/main` が Spec と Plan の 2 ファイルだけであること、`bash scripts/check-layout.sh` の結果（文書だけの変更なので、`README.md` の「テスト」のうち実行するのはこれだけ。ほかの入口はコードを変えていないので省き、PR に書く）
- [ ] **Step 3: push と PR**

  ```bash
  SCAN="$PARENT_ROOT/scripts/scan-before-push.sh"
  CODE_SHA="$(bash "$SCAN" -C "$DOC_ROOT")" && [ -n "$CODE_SHA" ] \
    && git -C "$DOC_ROOT" push origin "${CODE_SHA:?}:refs/heads/docs/issue-116-review-automation-board"
  gh pr create --repo usaturn/create-reso-world --base main --head docs/issue-116-review-automation-board ...
  ```

  PR の本文は `Refs #116`（親は子が全て終わるまで閉じない）、子の一覧、Spec の判断と理由、実行方式と理由、検証、所要時間
- [ ] **Step 4: #116 に、ボードを公開したことと PR の URL をコメントする**

## 実行予算

- Issue 全体の能動時間: 240 分（ledger は `SESSION/budget.jsonl`、2026-10-18T05:59Z に開始）
- phase の目安: Spec・Plan 60 分、Task 1 60 分、Task 2〜4 60 分、Task 5 30 分
- worker: 使わない（inline）
- 再試行の上限: GitHub API の一時的な失敗（5xx、タイムアウト）は、同じ書き込みについて、既存の確認をしてから 2 回まで。権限・検証の失敗（403、422 の内容の誤り）は再試行せず止まる
- checkpoint: Task 1 の後（照合が通らなければ分割を見直す）、Task 3 の後（関係の照合）
- 縮小の候補: 予算を超えそうなら、子の本文の「インターフェース」を親の表への参照に縮め、詳細は各子の Spec に任せる

## Contingency

- 子の作成の途中で止まったら、台帳に記録した子だけを残し、作っていない子を「未作成」と報告する。作った子を消さない
- `blocked_by` の API が使えない（404 など）ときは、本文の依存の記載だけで代えず、ボードを未完成として報告する
- #116 の本文が作業中に変わっていたら、PATCH せず、変わった行を報告する（利用者の編集を上書きしない）

## 完了

2026-10-18（UTC）に Task 1〜4 を実行した。状態は draft のまま（内容の承認は記録していない）。

- 子 Issue: #149 `runner-core`、#150 `runner-adapters`、#151 `dsh-headless`、#152 `review-helpers`、#153 `pr-review-v2`、#154 `review-verify`、#155 `review-fix-roles`、#156 `fix-loop`、#157 `issue-to-pr-implement`、#158 `issue-to-pr-merge`。どれも planning: not-started / implementation: not-started
- 照合: 生成スクリプトの `check` が「子 10 件、依存 13 本、循環なし、担当の重なりは節で分かれている」で終了コード 0。子の本文は PATCH の後の GET で生成したものと 10 件とも一致
- 関係: #116 の Sub Issue（全ページ）が子 10 件と一致、各子の `blocked_by`（全ページ）が生成元の 13 本と一致し、余分な関係は無い
- #116 の本文: 書き込みの直前の sha256 が作業開始時の写し（`05c70776…`）と一致したので PATCH した。読み戻した本文が生成したものと一致し、公開台帳の番号・id・node_id・URL が台帳と一致。元の本文で変えた行は、冒頭の引用、「目的」の見出し（「目的と範囲」へ）、「状態」の 3 行だけ
- Spec の追記: Task 4 の見直しで、`create_parent_repo` を使う移植元の 3 モジュールの扱いが決まっていなかったので D-8 に足した（`b6f9651`）
- 所要時間: 着手（05:50 頃、推定）から公開の前まで約 25 分。内訳は、入力・競合の確認と範囲の確認 約 5 分、移植元・移植先の調査と Spec 約 13 分、Plan 約 2 分、Task 1 約 5 分、Task 2・3 約 2 分、Task 4 約 3 分（commit と ledger の時刻から）
