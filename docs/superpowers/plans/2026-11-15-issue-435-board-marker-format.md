# Issue #435 ボードマーカー形式の統一 実装計画

> **For agentic workers:** この Plan は issue-to-pr の run で、Task 1・2 を agent-runner の担当（`claude-code_sonnet_xhigh`）に 1 つずつ依頼して実行する（subagent-driven-development の形）。Task 3 は controller が行う。Steps use checkbox (`- [ ]`) syntax for tracking.

- 状態: `draft`
- 実行許可: Spec の「管理・実行許可」のとおり（issue-to-pr の委任。内容の承認ではない）
- 対象: usaturn/create-reso-world#435、base `main` `273ace19215430fa05042a512d63dc19e4e3a058`

**Goal:** `board-ledger` 形式（#349 の形）のボードを `reshape_issue.py` で整形でき、管理対象をバイト単位で保つ。マーカーの構文を `.agents/issue-format.md` に定義し、両スキルの references・helper を合わせる。

**Architecture:** 構文の定義は `.agents/issue-format.md` の 1 つの小節。`reshape_issue.py` の `_managed_ranges` が `board-ledger` 形式を 1 つの管理対象（kind `ledger`、name `legacy-ledger:<key>`）として厳密に読み、壊れた形を拒否する。`issue_format.py` の `_excluded_numbers` と `publish_issue.py` の `KNOWN_COMMENT` は同じ小節に合わせる。

**Tech Stack:** Python 3.14（uv）、pytest。リポジトリは ruff・mypy を依存に持たないので、静的検査は `uv run --locked python -m py_compile` と pytest の import で代える。

**Spec:** `docs/superpowers/specs/2026-11-15-issue-435-board-marker-format-design.md`

## Global Constraints

- 用語: マーカーの形は「`:board:` 形式」「`board-ledger` 形式」と呼ぶ。archive の「旧形式」「新形式」と混ぜない
- `board-ledger` 形式の構文（Spec D3）: ボード行 `<!-- planning-parallel-issues board: <key> -->`（`board:` の後に半角空白 1 個、`<key>` は `\S+`、行全体が一致）→ 直後の行 `<!-- board-ledger:start -->`（行全体が一致）→ その後の最初の `<!-- board-ledger:end -->`（行全体が一致）。範囲全体を kind `ledger`、name `legacy-ledger:<key>` の 1 つの管理対象にする
- 拒否の対象の行: `^ {0,3}<!-- planning-parallel-issues`（読めた正規の行を除く）と `^ {0,3}<!-- board-ledger:`（読めた開始・終わりを除く）。コードブロック・HTML コメントの中は無視する
- 範囲の中の子マーカー行は `:board:` 形式と同じく無視する（拒否しない）
- GitHub へ書き込まない。テストは偽の本文だけを使う
- テストは AGENTS.md の「テストの採用基準」に従う。文書の文言を写すテスト（F）は足さない
- エラーメッセージは既存と同じく英語の 1 文。文書は AGENTS.md の「日本語表現」に従う（`planning-parallel-issues` の references は英語の文書なので英語で書く）

## 受け入れ基準

（Spec の「受け入れ基準」の本文。実装担当・レビュー担当の brief に同じ本文を渡す）

- 動作環境: Dev Container・uv。テストは偽の本文・ローカルファイルだけを使い、実 GitHub へ書き込まない
- 実入力: #349 の形の本文（`## Publication ledger` の下にボード行・ledger の開始・日本語の説明文と表・ledger の終わり。実際の #349 は LF。CRLF は同じ本文の変換で確かめる）
- `board-ledger` 形式のボードで prepare が終了コード 0 で成功し、build で管理対象がバイト単位で保たれる（`preservation.ok`）。#349 の snapshot でも同じ
- `:board:` 形式のボードと子マーカーの整形が引き続き成功する（既存テストが通る）
- 防御範囲: 対象は `:board:` 形式・`board-ledger` 形式のボードマーカーと子マーカー。対象外の反例は次の 3 つに分けて扱う
  - (a) 管理対象にしない（今の挙動どおり。拒否しない）: 任意の HTML コメント、コードの囲み（閉じていない囲みを含む）・HTML コメントの中のマーカー
  - (b) `reshape_issue.py` が拒否する（終了コード 2）: 終わりの無い開始マーカー（`:board:` 形式・`board-ledger` 形式とも）、壊れた `board-ledger` 形式の範囲、ボード行の無い `board-ledger` 行、本当に未知の `planning-parallel-issues` 行
  - (c) `issue_format.py` の節の検査の除外: 終わりの無い開始を範囲にしないだけで、拒否しない
  - Issue の「閉じていない囲み…は引き続き拒否する」は、(a) の閉じていないコードの囲みについては「管理対象にしない」と読み替える（今の helper も拒否せず、`reshaping.md` の手順で人が止まる）。終わりの無いマーカーの範囲は (b) のとおり拒否する
- マーカーの構文の定義が `.agents/issue-format.md` の 1 か所にあり、同じファイルの他の記述、`issue-authoring` の `references/reshaping.md`、`planning-parallel-issues` の references はそこを参照する
- マージ後に確かめる項目: #349 の本文を共有書式に組み直すときの `draft update` → `verify` の成功（D6）

## Review Focus

1. `board-ledger` 形式の範囲の直後が本文の末尾（末尾の改行なし）: archive の `pad` の経路を通っても保存検査が ok になる。→ Task 1 のテスト 1 に、末尾の改行の無い変種を parametrize で足す
2. ボード行の `<key>` が別の値（`agent-workspace-port-2026-11-08` のような `-` と数字を含む値）: name が `legacy-ledger:<key>` になり archive の位置マーカーに使える。→ テスト 1 の本文の key をこの形にする
3. 同じ本文に `:board:` 形式の範囲と `board-ledger` 形式の範囲が両方ある: 2 つの管理対象として順序どおりに保たれる。→ テスト 1 に変種として足す
4. 既に整形済み（archive あり）の `board-ledger` 形式の本文をもう一度 prepare → build: archive の位置マーカー `ledger:legacy-ledger:<key>` が live の管理対象と対応し、archive が再利用される。→ テスト 1 の中で `build` の出力にもう一度 prepare → build をかける
5. コードブロックの中の `<!-- board-ledger:start -->`: 拒否されず、管理対象にもならない（防御範囲 (a)）。→ テスト 1 の本文のスロットに囲みの中の行を置く

## 要件・Task・検証の対応

| Spec の条件 | Task | 検証 |
| --- | --- | --- |
| `board-ledger` 形式で prepare→build 成功・バイト保存 | Task 1 | テスト 1、#349 の snapshot（Task 3） |
| 子マーカーの認識の退行なし・範囲の中の子マーカーを無視 | Task 1 | テスト 2 |
| 壊れた形・未知行の拒否（陽性対照付き） | Task 1 | テスト 3、陽性対照はテスト 1・2 |
| `:board:` 形式の退行なし | Task 1 | 既存テスト 2 件 |
| 節の検査・警告の整合（D4） | Task 2 | 一時的な確認（コミットしない）、構文の確認 |
| 定義元 1 か所・各文書の参照・既存ボードの保守規則（D2） | Task 2 | `git diff` の確認 |
| #349 で prepare・build 成功（D6） | Task 3（統合） | 終了コードと `preservation.ok` |

共有する前提: `board-ledger` 形式の構文（Spec D3、上の Global Constraints）を Task 1（`reshape_issue.py`）と Task 2（`issue_format.py`・`publish_issue.py`・文書）が同じ意味で使う。統合の確認は Task 3 の controller が行う。Task 2 のレビューで、文書の構文と Task 1 の正規表現を突き合わせる。

---

### Task 1: `reshape_issue.py` が `board-ledger` 形式を読む

**Files:**
- Modify: `.agents/skills/issue-authoring/scripts/reshape_issue.py`（46〜52 行目付近の正規表現の定数、338〜379 行目付近の `_managed_ranges`）
- Test: `.agents/skills/issue-authoring/tests/test_reshape_issue.py`

**Interfaces:**
- Consumes: 既存の `prepare_body(body) -> PreparedBody`、`build_body(original, segments) -> str`、`verify_body(original, built) -> Preservation`（`.ok`）、`ReshapeError`、`PreparedBody.managed_ranges[].{kind,name,text}`・`.segments`・`.archive_body`・`.archive`
- Produces: 定数 `_LEGACY_BOARD`（`re.Pattern`、group `key`）、`_LEGACY_LEDGER_START = "<!-- board-ledger:start -->"`、`_LEGACY_LEDGER_END = "<!-- board-ledger:end -->"`、`_LEGACY_LEDGER_LINE = re.compile(r"^ {0,3}<!-- board-ledger:")`。Task 2 はこの構文を文書に書き、`issue_format.py` に同じ条件を写す

**テストの要否:** 要る（S）。保存が壊れると ledger が黙って失われる。拒否が壊れると壊れたマーカーが編集可能なスロットに入り、黙って消える。子マーカーの保護が外れても気付けない。

- [ ] **Step 1: 失敗するテストを書く**

既存の 2 件と同じ読み込み方を、小さな関数 `_load() -> Any` に共通化してよい（既存 2 件もそれを使う形に直してよい）。足すテストは次の 3 つ。

`test_board_ledger_form_survives_reshape(newline: str, variant: str)`（`newline` は `"\n"`・`"\r\n"`、`variant` は `"plain"`・`"no-final-newline"`・`"with-board-range"`）:
- 本文: `## 概要` / 非 ASCII の文 / コードブロック（` ```text ` の中に `<!-- board-ledger:start -->` を 1 行）/ `## Publication ledger` / ボード行 `<!-- planning-parallel-issues board: agent-workspace-port-2026-11-08 -->` / `<!-- board-ledger:start -->` / `子 Issue の作成後に実際の値を記録した。` / 空行 / `| key | issue |` / `|---|---|` / `` | `alpha` | #1 | `` / `<!-- board-ledger:end -->` / 空行 / `## 対象外` / `なし。`。`with-board-range` は末尾に既存テストと同じ `:board:` 形式の範囲を足す。`no-final-newline` は ledger の終わりで本文を終える（最後の改行なし）
- `prepare_body` の `managed_ranges` の kind・name に `("ledger", "legacy-ledger:agent-workspace-port-2026-11-08")` がちょうど 1 つあり、その `text` がボード行から `<!-- board-ledger:end -->` までのバイト列（`_line_span` の範囲。行末の改行の有無は既存と同じ扱い）
- コードブロックの中の行は管理対象に含まれない（`with-board-range` 以外では管理対象は 1 つ）
- どの `segments` にも ledger の表の行が無い
- `built = build_body(original, list(prepared.segments))` で `verify_body(original, built).ok`、`prepare_body(built).archive_body == original`、管理対象の `text` の列が一致
- もう一度 `build_body(built, list(prepare_body(built).segments))` しても `verify_body(built, rebuilt).ok` で、`archive_body == original`
- `` | `alpha` | #1 | `` を `#2` に変えた本文では `verify_body(original, ...).ok` が偽

`test_child_marker_is_kept(body_kind: str)`（`"child"`・`"child-in-ledger"`）:
- `child`: 1 行目 `<!-- planning-parallel-issues board:demo child:alpha parent:349 -->`、続けて `## 概要` などの本文。prepare → build で `verify_body` が ok、`prepare_body(built)` の `segments[0] == ""`、`built` の 1 行目が子マーカー
- `child-in-ledger`: `board-ledger` 形式の範囲の中（表の後）に子マーカー行を 1 行含む本文。拒否されず、範囲全体（子マーカー行を含む）が 1 つの管理対象として保たれ、`verify_body` が ok

`test_broken_or_unknown_board_markers_are_rejected(lines: list[str])`（3 ケース）:
- ボード行と `<!-- board-ledger:start -->` はあるが `<!-- board-ledger:end -->` が無い
- ボード行の無い `<!-- board-ledger:start -->` / `x` / `<!-- board-ledger:end -->`
- `<!-- planning-parallel-issues unknown -->`
- `## 概要` / `本文。` / 空行 / `*lines` / 空行 / `## 対象外` / `なし。` を `"\n"` で連結した本文で、`prepare_body` が `ReshapeError` を投げる

- [ ] **Step 2: 失敗を確かめる**

Run: `uv run --locked pytest .agents/skills/issue-authoring/tests/test_reshape_issue.py -q`
Expected: テスト 1 は `ReshapeError`（unknown planning-parallel-issues marker）で FAIL。テスト 2 の `child-in-ledger` と、テスト 3 の「ボード行の無い ledger」は FAIL。ほかは PASS でもよい

- [ ] **Step 3: `_managed_ranges` に `board-ledger` 形式を足す**

`_managed_ranges(body, lines) -> tuple[list[tuple[ManagedKind, str, _Span]], str | None]` のシグネチャは変えない。Global Constraints の構文と拒否の規則のとおりに走査を足す。`stack` が空のときだけボード行を範囲の開始として読み、範囲の中は終わりまで進めて `ranges.append(("ledger", f"legacy-ledger:{key}", _line_span(body, lines, board_index, end_index)))` とする。範囲の中の子マーカー行は無視し、それ以外の `_PLANNING_LINE`・`_LEGACY_LEDGER_LINE` の行は拒否する。`stack` が空でないときのボード行・`board-ledger` 行は拒否する。囲み・コメントの中（`line.in_fence`・`covered`）の行は今と同じく飛ばす。docstring に `board-ledger` 形式を 1 行足す

- [ ] **Step 4: テストを通す**

Run: `uv run --locked pytest .agents/skills/issue-authoring/tests/ -q`
Expected: 全件 PASS（既存 2 件を含む）

- [ ] **Step 5: 構文の確認**

Run: `uv run --locked python -m py_compile .agents/skills/issue-authoring/scripts/reshape_issue.py`
Expected: 出力なし・終了コード 0

- [ ] **Step 6: Commit**

```bash
git add .agents/skills/issue-authoring/scripts/reshape_issue.py .agents/skills/issue-authoring/tests/test_reshape_issue.py
git commit -m "fix: reshape helper reads board-ledger form board markers (#435)"
```

### Task 2: 定義元の文書と他の helper を合わせる

**Files:**
- Modify: `.agents/issue-format.md`（54 行目付近の「ほかのスキルの管理対象の節」、487 行目付近の「節の検査で読まない範囲」の (3)。新しい小節を足す）
- Modify: `.agents/skills/issue-authoring/references/reshaping.md`（21・64・91 行目付近）
- Modify: `.agents/skills/planning-parallel-issues/references/issue-board.md`（17 行目の Publication ledger の項）
- Modify: `.agents/skills/planning-parallel-issues/references/github-operations.md`（24 行目の段落）
- Modify: `.agents/scripts/issue_format.py`（`_excluded_numbers`、937〜948 行目付近）
- Modify: `.agents/skills/issue-authoring/scripts/publish_issue.py`（51 行目の `KNOWN_COMMENT`、612 行目の docstring）
- 書き換えない: `.agents/skills/issue-authoring/evals/reshape-validation.md`（移植元の過去の評価記録）

**Interfaces:**
- Consumes: Task 1 の Global Constraints の構文と定数名
- Produces: `.agents/issue-format.md` の小節（見出しの案: `### planning-parallel-issues のマーカー`）。他の文書はこの見出しを参照する

**テストの要否:** 要らない。文書は F。`_excluded_numbers` と `KNOWN_COMMENT` は、壊れても節の検査の問題・警告として表に出る（L）。代わりに Step 5 の一時的な確認と構文の確認を行う。

- [ ] **Step 1: `.agents/issue-format.md` に小節を書く**

小節に次を書く: 用語（`:board:` 形式・`board-ledger` 形式。archive の旧形式・新形式とは別）、`:board:` 形式の構造（`board:<key>` の範囲の中の `ledger` の範囲と、`ledger` の単独）と新しいボードの推奨（Spec D2 の例をそのまま写す。`## Publication ledger` の見出しは範囲の外）、`board-ledger` 形式の構文（新しく書かない。既存ボードの読み取りのため）、子マーカー、拒否する形と管理対象にしない形（受け入れ基準の (a)〜(c)）、既存ボードの保守の規則（Spec D2: マーカーを保って中身だけを更新する。形の書き換えは整形済みボードでは行わず、別の依頼にする）、この小節に従う helper（`reshape_issue.py`・`issue_format.py`・`publish_issue.py`）。54 行目付近の項と 487 行目付近の (3) は、この小節を参照する短い文に直す

- [ ] **Step 2: `reshaping.md` を合わせる**

64 行目付近の「未知の `planning-parallel-issues` の行」を、小節の拒否する形への参照に直す。21・91 行目付近の「`issue-board.md` の形」を、ボードの内容の形（`planning-parallel-issues` の `references/issue-board.md`）とマーカーの構文（`.agents/issue-format.md` の小節）の両方を指す形に直す。リンクの相対パスは既存の書き方に合わせ、実在を確かめる

- [ ] **Step 3: `planning-parallel-issues` の references から参照する**

`issue-board.md` の Publication ledger の項に英語で 2 文程度足す: マーカーの構文は `.agents/issue-format.md` の小節に定義されている。新しいボードは `:board:` form（`<!-- planning-parallel-issues:board:<key>:start -->` と、その中の `<!-- planning-parallel-issues:ledger:start -->`）で書き、既存のボードはマーカーの形を変えずに中身だけを更新する。`github-operations.md` の 24 行目の段落に、同じ小節への参照を 1 文足す。相対パスは `../../../issue-format.md`（実在を確かめる）

- [ ] **Step 4: `issue_format.py` と `publish_issue.py`**

`_excluded_numbers(lines, fences) -> set[int]` に、`board-ledger` 形式の範囲（囲みの外のボード行で、直後の行が `<!-- board-ledger:start -->`、その後の最初の囲みの外の `<!-- board-ledger:end -->` まで）を足す。終わりが無ければ範囲にしない（拒否しない）。docstring の箇条を更新する。`KNOWN_COMMENT` を `^ {0,3}<!-- (?:issue-format:|planning-parallel-issues(?::| board:)|board-ledger:(?:start|end) -->)` にし、docstring を合わせる

- [ ] **Step 5: 一時的な確認（コミットしない）**

`mktemp -d` のディレクトリに確認用のスクリプトを置き、`uv run --locked python <スクリプト>` で次を確かめて結果を報告する: `board-ledger` 形式の範囲の中に `## 受け入れ条件` の行を含む本文で、`issue_format._excluded_numbers` がその行を除く。直後の行が開始でないボード行では除かない。`publish_issue._warnings` が `<!-- board-ledger:start -->`・`:end -->` の行を警告しない。確認後にディレクトリを消す

- [ ] **Step 6: 構文の確認とテスト**

Run: `uv run --locked python -m py_compile .agents/scripts/issue_format.py .agents/skills/issue-authoring/scripts/publish_issue.py && uv run --locked pytest .agents/scripts/tests/test_issue_format.py .agents/skills/issue-authoring/tests -q`
Expected: エラーなし・全件 PASS

- [ ] **Step 7: Commit**

```bash
git add .agents/issue-format.md .agents/skills/issue-authoring/references/reshaping.md .agents/skills/planning-parallel-issues/references/issue-board.md .agents/skills/planning-parallel-issues/references/github-operations.md .agents/scripts/issue_format.py .agents/skills/issue-authoring/scripts/publish_issue.py
git commit -m "docs: define planning-parallel-issues marker syntax in issue-format (#435)"
```

### Task 3（統合・controller）: #349 の snapshot での確認と全体検証

- [ ] `gh api repos/usaturn/create-reso-world/issues/349 > "$SESSION/issue-349.json"`（読み取りだけ）
- [ ] `uv run --locked python .agents/skills/issue-authoring/scripts/reshape_issue.py prepare --repo usaturn/create-reso-world --issue 349 --read-json "$SESSION/issue-349.json" --out-dir <空のディレクトリ>` → 終了コード 0・`status: prepared`、管理対象 1 件（`ledger` / `legacy-ledger:agent-workspace-port-2026-11-08`）
- [ ] prepare の `segments.json` を変えずに `build --segments-file` → 終了コード 0・`preservation.ok` が true
- [ ] 必須検証コマンド（`verify-cmds.json` に固定）: `bash scripts/check-layout.sh`、`uv run --locked pytest tests/skills .agents/skills .agents/scripts tools -q`（README の「テスト」。`.devcontainer/run-tests.bash` は Dev Container とスクリプトのテストで、この変更が触らないので実行しない）
- `draft update` → `verify` は #349 で実行できない（Spec D6）。マージ後の項目として PR 本文と Issue に書く

## 実行方式

`implement_task.py check` の `self` が false（`--implement claude-code_sonnet_xhigh`）なので、Task 1・2 を runner の担当に 1 つずつ順に依頼する（issue-to-pr 4 章の「Task の実装を runner の担当に依頼する」）。Task 2 は Task 1 の定数名・構文に合わせるので Task 1 の後。Task ごとのレビューは controller が行う。`--merge` が適用されるので、最終のブランチ全体レビューはループの 1 サイクル目で代える（4 章 8）。

## 実行予算

- Issue 全体の能動時間: 360 分（Issue の見積り 2〜6 時間の上限。設計・Spec のレビューとループ 3 サイクルを含む）
- phase の目安: 設計・Spec・レビュー 90 分（済み）、Task 1 60 分、Task 2 45 分、Task 3・検証 20 分、PR・ループ 最大 3 ×（レビュー 45 分＋計画・修正 20 分）
- worker: 実装担当の期限は runner の `implement` の 90 分。無進捗の打ち切りは runner の既定
- 再試行の上限: 同じ失敗（同じ signature）の再試行は 1 回まで。`retry`・`rejected` は Task ごとに 1 回まで
- checkpoint: 各 Task の後、予算の 50%・100%、担当の失敗の直後
- 縮小・切り出し・方法変更の候補: Task 2 の `issue_format.py`・`publish_issue.py` の変更を別 Issue に切り出す（文書と reshape だけで #349 の整形は可能になる）。runner の担当が上限まで失敗したら止まって報告する（self で引き取らない）

## contingency（代替策）

- 最初の RED で `managed_ranges[].text` の改行の扱いが Plan の想定と違うときは、テストの比較を `_line_span` の実際の範囲に合わせる最小修正にし、ledger に記録して続ける（意味は変えない）
- `no-final-newline` の変種で `pad` の経路が既存の制限（`reshaping.md` 78 行目の、末尾 LF なしの管理対象の停止）に当たるときは、その変種を既存の挙動の確認（`build` の失敗ではなく成功を期待する形を保てるか）として調べ、既存の `:board:` 形式でも同じなら変種を外して ledger に理由を記録する
- #349 の snapshot で、`board-ledger` 形式以外の理由（別の未知の行・archive・metadata）で prepare が止まったときは、原因が Spec の範囲なら Task 1 の修正の依頼として出す。範囲外なら止まって報告する
