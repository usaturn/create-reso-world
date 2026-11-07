# Issue #322 新しく作ったリポジトリの Spec・Plan の置き場所 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

- 状態: draft
- 実行許可: 利用者の指示 `/issue-to-pr #322 --merge`（Spec の冒頭のとおり。内容の承認ではない）

**Goal:** 宣言のある新しいリポジトリでは Spec・Plan をそのリポジトリにコミットできるよう、補助・issue-to-pr の手順・規約とスキルの本文をそろえる。

**Architecture:** 判定は `scripts/superpowers_context.py` に一元化する（宣言の読み取り、除外、`--doc-repo` の照合、`document_repository` の出力）。`scripts/superpowers_review_copy.py` はその入力を通すだけ。issue-to-pr の手順のシェルは `document_repository` で文書の分離を決める。文書とスキルは同じ規則を書く。

**Tech Stack:** Python 3.14（標準ライブラリ）、Bash、Git、pytest・unittest、uv。

**Spec:** `docs/superpowers/specs/2026-11-07-create-reso-world-issue-322-spec-plan-in-new-repo-design.md`

## Global Constraints

- 宣言の行は、正確に `<!-- superpowers-documents: this-repository -->`（対象のリポジトリの `AGENTS.md`、`HEAD` のコミット済みの blob、前後の空白を除いて比べる）
- 宣言があっても拒否するリポジトリ: `usaturn/resoloop`・`orange3134/resoloop`・`usaturn/resoloop-meshy`
- 新しい引数は `--doc-repo OWNER/REPO`（省略・空は `usaturn/create-reso-world`）。新しい出力は JSON の `document_repository`
- 今の呼び出し方（`--doc-root`・`--parent-root`・`--path`・`--name`・`--commit`）、終了コード（context の 64・65・66、コピーの 1・2）、`FORK_REPOSITORY`・`UPSTREAM_REPOSITORY` の照合を変えない
- 変えないファイル: Spec の「範囲」の「変えないもの」（`README.md`・`tools/external_tools/`・`finalize.py`・`references/execution.md`・ResoLoop と Meshy の手順書とスクリプト・既存の Spec・Plan を含む）
- テストは「テストの採用基準」の S だけ。実在の GitHub に書き込まない
- 文書の日本語は `AGENTS.md` の「日本語表現」に従う（書き直す行では「正本」を使わない）

## Review Focus

- 宣言が `AGENTS.md` の作業ツリーにだけあり未コミット → 宣言なしとして扱う（Task 1 の宣言なしの拒否で、コミットした状態だけを読む実装を使う）
- `AGENTS.md` が無いリポジトリ・`HEAD` が読めない → 例外にせず「宣言なし」（Task 1 の宣言なしのケースは `AGENTS.md` 自体を持たない checkout で確かめる）
- `--doc-repo` を大文字混じりで渡す → 既存の `parse_repository` で小文字にし、小文字の origin と照合する（Task 1 の正常系で大文字混じりを渡す）。`.git` 付きは取り除かれず止まる（全体レビューの M-2、持ち越し）
- issue-to-pr の別シェルの `pr` ブロックで `DOC_REPO` が未定義 → `target.json` から読み戻す（Task 2 のテストは既存の再開の仕組みで `pr` を別シェルで実行する）
- review-fix-planning の nounset（zsh・bash の `set -u`）で `DOC_REPO` が未定義 → `${DOC_REPO:-}` で既定に落ちる（Task 3 の既存の context テストが nounset の zsh で実行する）

## 受け入れ基準

（Spec の「受け入れ基準」と同じ。実装とレビューの brief にこの節を写す。）

- 動作環境: この Dev Container（Python 3.14、uv、Git）。テストは一時の Git リポジトリと偽の remote で行い、実在の GitHub に書き込まない
- 実入力: `AGENTS.md` は日本語を含む複数行の UTF-8 で、宣言はその中の 1 行。origin は `https://github.com/<owner>/<repo>.git`・`git@github.com:<owner>/<repo>.git` の形
- 防御範囲:
  - 拒否（終了コード 66）: `--doc-repo` に usaturn/resoloop・usaturn/resoloop-meshy（宣言があっても）、宣言が無い、origin が無い、origin が `--doc-repo` と違う、`review-fix` で `--doc-repo` が `--repo` と違う、宣言のあるリポジトリのコードに create-reso-world の `DOC_ROOT` を渡した
  - 正常: 宣言のあるリポジトリの checkout を `DOC_ROOT` に `--doc-repo` 付きで渡す（`review-copy`・`review-fix`）。create-reso-world の文書は今の呼び出し方でコピーできる（既存のテスト）
  - issue-to-pr: 宣言のある登録済みの通常ツールでは文書用の worktree と create-reso-world の PR を作らず、PR は対象のリポジトリの 1 つだけ。宣言の無いツール・ResoLoop では今までどおり 2 つ（既存のテスト）
- ResoLoop の fork・上流の照合の既存のテストが、変えずに通る
- 規約・README・外部ツールの文書・4 つのスキルの記述が食い違わない

## 要件と Task の対応

| Spec の条件 | 担当 Task | 観測する結果 | 検証 |
| --- | --- | --- | --- |
| 宣言・除外・origin の照合で止まる | Task 1 | 終了コード 66、stdout 空、Git の状態が変わらない | `test_superpowers_context.py` の新しいテスト |
| `document_repository` の出力と一致の要求 | Task 1 | JSON の値、不一致で 66 | 同上 |
| 確認用コピーが `--doc-repo` を通す | Task 1 | 一時のリポジトリでコピーが `created` | コミットしない確かめ（Task 1 の Step 6） |
| issue-to-pr で文書を分けない | Task 2（統合担当） | worktree・scan・PR が対象の 1 つだけ | `test_base_workflow.py` の新しいテストと既存のテスト |
| review-fix-planning の経路 | Task 3 | context のブロックが `--doc-repo` を渡しても既存のテストが通る | `.agents/skills/review-fix-planning/tests` |
| 規約・文書・スキルの記述がそろう | Task 4 | 旧規則の記述が範囲内に残らない | `grep` による照合（Task 4 の Step 2）、`check-layout.sh` |

共有する条件: 宣言の文字列・除外の一覧・`--doc-repo` の名前・`document_repository` の名前は Task 1 で決め、Task 2〜4 はそれを使う。照合は Task 5 で、Spec の条件ごとに行う（統合担当は controller）。

## 実行方式

inline（`superpowers:executing-plans`）。Task 2〜4 が Task 1 のインターフェースに順に依存し、同じ規則の文書を続けて書き換えるため。agent-runner の割り当ては `self`（雛形の既定の適用）。最後にブランチ全体のレビューを、新しいサブエージェント 1 つに依頼する。

## 実行予算

- 全体の能動時間: 420 分（PR 修正ループの最大 3 サイクルを含む）。根拠: 実装 4 Task と、似た規模の #262・#267 の実績（ループ 1 サイクルで約 1 時間）
- phase の目安: Spec・Plan 40 分、Task 1 50 分、Task 2 50 分、Task 3 25 分、Task 4 40 分、Task 5（検証・全体レビュー）40 分、PR とループ 3 サイクル ×（レビューの期限 45 分＋計画・修正 30 分）= 最大 225 分
- worker: 全体レビューのサブエージェントは期限 30 分、無進捗 15 分で打ち切る。テストの実行は同期で、`run-tests.bash` は期限 20 分
- 再試行の上限: 同じ失敗（同じ signature）の再試行は 1 回まで。安全の失敗（別のリポジトリへの書き込み、実在の GitHub への想定外の送信）は再試行しない
- checkpoint: 各 Task の終わり、予算の 50%・100%、worker の失敗の直後
- 縮小・切り出しの候補: (1) review-fix-planning は context のブロックの `--doc-repo` と配置の記述だけにし、結論 3 の細部は持ち越す。(2) agent-handoff・planning-parallel-issues の英文の書き直しを 1 文ずつに絞る

## contingency（代替策）

- 最初の RED で、`git cat-file` の出力や既存のテストの前提（JSON のキーの集合など）が想定と違うと分かったら、意味を保つ最小の修正（例: キーの集合に `document_repository` を足す）を ledger に残して続ける
- issue-to-pr の手順のテストの fixture で、通常ツールの seed に `AGENTS.md` を足すと既存のケースが変わるなら、宣言のある variant を別の fixture の引数にする
- 既存のテストが Task 1 の変更で落ち、原因が出力のキーの追加なら、テストの期待のキーを足す。拒否の挙動が変わったなら、変更を戻して設計を見直す（Spec の意味が変わるなら止まる）
- `run-tests.bash` が環境のせいで落ちる（memory の「隔離した検証の落とし穴」）ときは、落ちたテストを単独で再実行して原因を分け、この変更と無関係なら結果をそのまま報告する

---

### Task 1: 補助の判定と `--doc-repo`

**Files:**
- Modify: `scripts/superpowers_context.py`（定数、`resolve_context`、`main`）
- Modify: `scripts/superpowers_review_copy.py`（`run`・`parse_args`・docstring）
- Modify: `scripts/superpowers-review-copy.sh`（使い方のコメント）
- Test: `tests/scripts/test_superpowers_context.py`

**Interfaces:**
- Produces:
  - `DOCUMENTS_MARKER = "<!-- superpowers-documents: this-repository -->"`
  - `SHARED_DOCUMENT_REPOSITORIES = (FORK_REPOSITORY, UPSTREAM_REPOSITORY, "usaturn/resoloop-meshy")`（宣言があっても create-reso-world に置く）
  - `declares_own_documents(checkout: Checkout) -> bool`（`HEAD:AGENTS.md` の blob を読む。読めなければ False）
  - `resolve_context(..., doc_repo: str | None = None)`、CLI の `--doc-repo`
  - 出力の `document_repository: str`
  - `superpowers_review_copy.py` の `--doc-repo`（`resolve_context("review-copy", ..., doc_repo=args.doc_repo)` に渡す）

- [ ] **Step 1: 失敗するテストを書く**

`ContextTests` に `own_documents(self, name, origin, *, declared=True)` の補助を足す（`checkout` で作り、`declared` なら日本語を含む複数行の `AGENTS.md` に宣言の行を入れてコミットする。`declared=False` は `AGENTS.md` を作らない）。`good()` のキーの集合に `document_repository` を足す。新しいテスト `test_own_documents_route_requires_declaration_origin_and_matching_code` を足す:

```python
# S: 補助が誤った checkout を通すと、Spec・Plan を別のリポジトリにコミットし、気付かないまま PR に載せる
tool = self.own_documents("parent/external/new-tool", "https://github.com/usaturn/new-tool.git")
value = self.good(operation="review-copy", doc_root=tool, doc_repo="Usaturn/New-Tool")
self.assertEqual((value["doc_root"], value["document_repository"]), (str(tool), "usaturn/new-tool"))
value = self.good(operation="review-fix", repo="usaturn/new-tool", code_root=tool,
                  doc_root=tool, doc_repo="usaturn/new-tool")
self.assertEqual(value["document_repository"], "usaturn/new-tool")
self.assertEqual(self.good(repo="usaturn/new-tool", code_root=tool)["document_repository"], "usaturn/new-tool")
self.assertEqual(self.good()["document_repository"], SELF)
```

拒否は subTest で、それぞれ `self.bad(<診断の語>, ...)`（終了コード 66）:

- 宣言なし: `own_documents(..., declared=False)` の checkout を `review-copy` に `doc_repo` 付きで渡す
- origin なし: 宣言はあるが remote を持たない checkout
- origin の食い違い: 宣言のある `usaturn/new-tool` の checkout を `doc_repo="usaturn/other-tool"` で渡す
- 除外: 宣言をコミットした `self.fork` を `doc_repo="usaturn/resoloop"` で、宣言のある `usaturn/resoloop-meshy` の checkout を `doc_repo="usaturn/resoloop-meshy"` で渡す
- コードとの不一致: `review-fix`・`repo="usaturn/new-tool"`・`code_root=tool` に、create-reso-world の docs の linked worktree を `doc_repo` なしで渡す。別の宣言のあるリポジトリの checkout を `doc_repo` 付きで渡す
- `doc_repo` だけ: `self.bad("DOC_ROOT", code=64, operation="review-workspace", doc_repo="usaturn/new-tool")`

- [ ] **Step 2: 失敗を確かめる**

Run: `uv run --no-project python -m unittest tests.scripts.test_superpowers_context -v`（cwd はリポジトリのルート。動かなければ `tests/scripts` を `-s` にした discover）
Expected: 新しいテストと `good()` を使う既存のテストが、`--doc-repo` の未知の引数（argparse の終了コード 2）と `document_repository` の欠落で FAIL

- [ ] **Step 3: `scripts/superpowers_context.py` を実装する**

- `_committed_agents(root: Path) -> str | None`: `git -C root cat-file blob HEAD:AGENTS.md` を、`_git` と同じく `GIT_*` を除いた環境で実行し、失敗なら None、成功なら UTF-8（`errors="replace"`）で返す
- `declares_own_documents`: 上の結果の行のどれかが `strip()` で `DOCUMENTS_MARKER` と一致
- `resolve_context`: `doc_repo` を `parse_repository` で正規化（空・None は `DOCUMENT_REPOSITORY`）。`doc_root` があれば、create-reso-world なら今の `_require_origin`、それ以外は除外の一覧・origin の一致・宣言の順に照合する。`doc_repo` が非空で `doc_root` が無ければ `InputError`。`review-copy` の `document_repository` は照合した値。ほかの operation では、`repository` が create-reso-world でも除外の一覧でもなく `declares_own_documents(code)` なら `repository`、それ以外は `DOCUMENT_REPOSITORY`。`doc_root` があって照合した値と違えば `ContextError`（診断に両方のリポジトリ名を書く）
- `main`: `--doc-repo` を足す（既定 None）。`--operation` の未指定の診断は変えない
- 診断の文は英語で、既存と同じく `DOC_ROOT` の語を含める（`superpowers_review_copy.py` が `--doc-root` に置き換える）

- [ ] **Step 4: `superpowers_review_copy.py`・`superpowers-review-copy.sh` に `--doc-repo` を通す**

`parse_args` に `--doc-repo`（help: 「DOC_ROOT のリポジトリ。省略時は usaturn/create-reso-world」に当たる英文）、`run` で `resolve_context` に渡す。docstring と `.sh` のコメントの使い方に `[--doc-repo OWNER/REPO]` を足し、`--doc-root` の説明を「Spec・Plan をコミットした checkout（create-reso-world か、宣言のあるリポジトリ）」にする。

- [ ] **Step 5: テストが通ることを確かめる**

Run: `bash tests/scripts/test-superpowers-python.bash`
Expected: すべて OK（既存の `test_known_routes_*`・`test_fork_requires_both_expected_remotes` を含む）

- [ ] **Step 6: 確認用コピーを実行して確かめる（コミットしない）**

`mktemp -d` の一時ディレクトリに、origin が create-reso-world の main checkout（`tmp/` を ignore）と、宣言のある `usaturn/new-tool` の checkout（`docs/superpowers/specs/x-design.md` をコミット）を作り、`bash scripts/superpowers-review-copy.sh --doc-root <tool> --parent-root <parent> --doc-repo usaturn/new-tool --path docs/superpowers/specs/x-design.md --name new-tool-x-spec.md` が `created:` を出して終了コード 0、`--doc-repo` を外すと終了コード 1 で `--doc-root origin` の診断を出すことを確かめる。結果を ledger に書き、一時ディレクトリを消す。

- [ ] **Step 7: Commit**

```bash
git add scripts/superpowers_context.py scripts/superpowers_review_copy.py scripts/superpowers-review-copy.sh tests/scripts/test_superpowers_context.py
git commit -m "feat: let declared repositories keep their own Spec/Plan in the context helper (#322)"
```

テストの要否: 要る（S。誤った checkout を通すと別のリポジトリに文書を置き、エラーにならない）。

### Task 2: issue-to-pr の文書の分離を `document_repository` で決める（統合担当）

**Files:**
- Modify: `.agents/skills/issue-to-pr/SKILL.md`（2 章の 5 の説明と target ブロック、2 章の 6 の capture ブロック、3 章の説明と worktree ブロック、4 章の 2・3、5 章の diff・publish・pr ブロックと文書用 PR の説明、ループの節の冒頭）
- Test: `.agents/skills/issue-to-pr/tests/test_base_workflow.py`

**Interfaces:**
- Consumes: Task 1 の `document_repository`（`$SESSION/target.json`）
- Produces: シェル変数 `DOC_REPO`。文書を分ける条件 `[ "$DOC_REPO" != "$TARGET_REPO" ]`

- [ ] **Step 1: 失敗するテストを書く**

fixture の `external` の値に `"managed-own-docs"` を足す（`managed` と同じ通常ツールで、code の seed の最初のコミットに、宣言の行を含む `AGENTS.md` を入れる。`workflow.docs` は `code`）。`Workflow.run` の再開の条件 `if [ "$TARGET_REPO" != usaturn/create-reso-world ]; then` を `if [ "$DOC_REPO" != "$TARGET_REPO" ]; then` にする。新しいテスト:

```python
@pytest.mark.parametrize("workflow", ["managed-own-docs"], indirect=True)
def test_declared_tool_keeps_documents_in_its_own_pr(workflow: Workflow) -> None:
    """S: 文書を分けると、宣言したリポジトリの Spec・Plan が create-reso-world の PR に黙って載る。"""
    result = workflow.run("#42")
    assert result.returncode == 0, result.stderr
    assert json.loads((workflow.session / "target.json").read_text())["document_repository"] == "sample-owner/other-tool"
    calls = [json.loads(line) for line in (workflow.session / "gh.jsonl").read_text().splitlines()]
    creates = [call for call in calls if call[:2] == ["pr", "create"]]
    assert [call[call.index("--repo") + 1] for call in creates] == ["sample-owner/other-tool"]
    assert not (workflow.parent / ".worktrees/issue-42-change").exists()
    scans = [json.loads(line) for line in (workflow.session / "scans.jsonl").read_text().splitlines()]
    assert [scan["cwd"] for scan in scans] == [str(workflow.code)]
    assert not (workflow.session / "docs-pr.json").exists()
```

- [ ] **Step 2: 失敗を確かめる**

Run: `uv run --project . --locked pytest .agents/skills/issue-to-pr/tests/test_base_workflow.py -q`
Expected: 新しいテストが FAIL（PR が 2 つ、または `DOC_REPO` が空で文書を分ける）

- [ ] **Step 3: SKILL.md の手順のブロックを直す**

- target ブロック: `TARGET_ROOT` の後に `DOC_REPO="$(jq -er .document_repository "$SESSION/target.json")" || exit 2`
- capture・`recheck_bases`・worktree・diff・publish の各ブロック: `[ "$TARGET_REPO" != usaturn/create-reso-world ]` を `[ "$DOC_REPO" != "$TARGET_REPO" ]` にする
- pr ブロック: 先頭の `CODE_SHA` の読み込みの前に `DOC_REPO="$(jq -er .document_repository "$SESSION/target.json")" || exit 2` を足し、条件を同じく置き換える
- 説明の文: 2 章の 5 の「Spec・Plan は常に create-reso-world の `DOC_ROOT` に保存し」を、`document_repository` で決まることと、宣言のある通常ツールでは対象のリポジトリの `DOC_ROOT`（= `CODE_ROOT`）に置き文書専用の PR を出さないことに書き換える。3 章の「`TARGET_REPO` が create-reso-world でなければ」と 218 行目の `DOC_ROOT` の定義、4 章の 2・3、5 章の「上の文書用 PR は」とループの節の冒頭の条件も `DOC_REPO` で書く

- [ ] **Step 4: テストが通ることを確かめる**

Run: `uv run --project . --locked pytest .agents/skills/issue-to-pr -q`
Expected: すべて PASS（既存の resoloop・通常ツールのケースは PR が 2 つのまま）

- [ ] **Step 5: Commit**

```bash
git add .agents/skills/issue-to-pr/SKILL.md .agents/skills/issue-to-pr/tests/test_base_workflow.py
git commit -m "feat: keep declared repositories' Spec/Plan in their own PR in issue-to-pr (#322)"
```

テストの要否: 要る（S。分岐が壊れると、文書を別のリポジトリの PR に黙って出す）。

### Task 3: review-fix-planning の Spec の置き場所

**Files:**
- Modify: `.agents/skills/review-fix-planning/SKILL.md`（110・115 行目付近、共通 context の 2 つのブロック、154 行目、結論 2 の手順 6 の最後、結論 3 の「書き始めた Spec の扱い」、「Spec のコミットと確認用コピー」、417 行目付近の報告、491 行目の配置）

**Interfaces:**
- Consumes: Task 1 の `--doc-repo`・`document_repository`

- [ ] **Step 1: 共通 context のブロックを直す**

最初のブロックの helper の呼び出しに `--doc-repo "${DOC_REPO:-}"` を足し、出力の読み取りに `DOC_REPO=$(printf '%s' "$CONTEXT_JSON" | jq -r .document_repository)` を足す。状況の投稿のブロック（424 行目付近）の呼び出しにも `--doc-repo "${DOC_REPO:-}"` を足す。

- [ ] **Step 2: 説明の文を直す**

「PR が create-reso-world のもの」で Spec を head に載せると書いた箇所を、「`DOC_REPO` が `PR_REPO`（create-reso-world と、宣言のあるリポジトリ）」に書き換える。`finalize.py` の `--spec-commit` と結論 2 の手順 6 は、マージしてよい範囲（create-reso-world と usaturn/resoloop）にだけ関係することを 1 文で明記する（宣言のあるリポジトリは結論 2 に進まない）。確認用コピーのコマンドに `--doc-repo "$DOC_REPO"` を足す。配置（491 行目）は「`DOC_REPO` の checkout の `docs/superpowers/specs/`」にする。

- [ ] **Step 3: テストを実行する**

Run: `uv run --project . --locked pytest .agents/skills/review-fix-planning -q`
Expected: すべて PASS（context のブロックを bash・zsh・nounset の zsh で実行する既存のテストを含む）

- [ ] **Step 4: Commit**

```bash
git add .agents/skills/review-fix-planning/SKILL.md
git commit -m "docs: place review-fix Specs by document_repository (#322)"
```

テストの要否: 新しいテストは要らない（ブロックの実行は既存のテストが確かめ、文の変更は F）。代わりに既存のテストの実行と、Task 4 の Step 2 の照合で確かめる。

### Task 4: 規約・文書・ほかのスキルの記述

**Files:**
- Modify: `AGENTS.md`（「Spec・Plan の保存と公開」の節だけ）
- Modify: `docs/superpowers/README.md`（「保存先」「確認用コピー」「公開」）
- Modify: `docs/external-tools-workflow.md`（9 行目の 1 文だけ）
- Modify: `.agents/skills/agent-handoff/SKILL.md`（28 行目）、`.agents/skills/agent-handoff/references/handoff-schema.md`（`doc_root` の説明）
- Modify: `.agents/skills/planning-parallel-issues/SKILL.md`（「Target repository」の節）、`.agents/skills/planning-parallel-issues/references/session-workflow.md`（42 行目）

- [ ] **Step 1: 記述を書き換える**

- `AGENTS.md`: 最初の項目を、原則（create-reso-world）と例外（宣言のあるリポジトリはそのリポジトリ、文書専用の PR を出さない、既存の 4 つに宣言を足さない、ResoLoop 本体と Meshy は宣言があっても補助が拒否する）に分ける。`DOC_ROOT` の定義、確認用コピーの項目（宣言のあるリポジトリは `--doc-repo`）、issue-to-pr の項目、「公開」の項目をそれに合わせる。「コミットしないファイルの置き場所」の表は変えない（「`DOC_ROOT` の `docs/superpowers/`」のままで正しい）
- `docs/superpowers/README.md`: 「保存先」に、例外の条件、宣言の行、対象のリポジトリの `AGENTS.md` に置く例（宣言の行と、`https://github.com/usaturn/create-reso-world/blob/main/docs/superpowers/README.md` へのリンクの 1 文）、拒否するリポジトリ、`document_repository` を書く。「確認用コピー」に `--doc-repo` の例。「公開」に、宣言のあるリポジトリはコードと同じ PR
- `docs/external-tools-workflow.md`: 9 行目を「Spec・Plan は、宣言のあるリポジトリ（新しく作ったもの）ではそのリポジトリに、それ以外は create-reso-world の `docs/superpowers/` にコミットする（`docs/superpowers/README.md`）」に当たる 1 文にする
- agent-handoff・planning-parallel-issues: Spec の設計の「planning-parallel-issues・agent-handoff」の節のとおり

- [ ] **Step 2: 旧規則の記述が範囲内に残っていないことを確かめる**

Run: `grep -n -E '対象のリポジトリにかかわらず|どのリポジトリの作業でも|for every repository|whatever repository|外部 repo へ移さず|常に create-reso-world|常にこのリポジトリ側' AGENTS.md docs/superpowers/README.md docs/external-tools-workflow.md .agents/skills/{issue-to-pr,review-fix-planning,agent-handoff,planning-parallel-issues}/SKILL.md .agents/skills/agent-handoff/references/handoff-schema.md .agents/skills/planning-parallel-issues/references/session-workflow.md`
Expected: 出力なし（範囲外の `README.md` の 246 行目は対象に含めない）

- [ ] **Step 3: 構造を確かめる**

Run: `bash scripts/check-layout.sh && git diff --check`
Expected: PASS、出力なし

- [ ] **Step 4: Commit**

```bash
git add AGENTS.md docs/superpowers/README.md docs/external-tools-workflow.md .agents/skills/agent-handoff .agents/skills/planning-parallel-issues
git commit -m "docs: store Spec/Plan in declared new repositories (#322)"
```

テストの要否: 要らない（文書の文言は F）。代わりに Step 2 の照合と Step 3 の構造の検査。

### Task 5: 統合の確認・全体の検証・全体レビュー

**Files:**
- Modify: この Plan（「完了」の節）と Spec（「実装の確認」の節）

- [ ] **Step 1: 全体の検証を実行する**

Run（それぞれ終了コードを記録する）:
- `bash tests/scripts/test-superpowers-python.bash`
- `uv run --project . --locked pytest tests/skills .agents/skills .agents/scripts tools -q`
- `bash .devcontainer/run-tests.bash`
- `bash scripts/check-layout.sh`
- `git diff --check afa86e0967ec71135a37365fd15933e819acf6e1...HEAD`
Expected: すべて終了コード 0

- [ ] **Step 2: 条件ごとに照合する**

「要件と Task の対応」の各行について、観測した結果とコマンドを Spec の「実装の確認」に書く。変更したファイルが Spec の「範囲」の中だけであることを `git diff --name-only afa86e09...HEAD` で確かめる。

- [ ] **Step 3: ブランチ全体のレビューを依頼する**

新しいサブエージェント 1 つに、Spec・Plan の受け入れ基準と、`git diff afa86e09...HEAD` を渡して、致命的な問題とテストの採用基準の違反（書きすぎ・不足）を探させる。指摘は controller が採否を裁定し、ledger に記録する。

- [ ] **Step 4: 範囲外の食い違いを親に伝える**

#320 に、`README.md` の「変更の流れ」の 246 行目（「対象のリポジトリにかかわらず `docs/superpowers/` に置く」）が改めた規則と食い違うこと（担当は #321・#325）をコメントする。

- [ ] **Step 5: Commit**

```bash
git add docs/superpowers/specs/2026-11-07-create-reso-world-issue-322-spec-plan-in-new-repo-design.md docs/superpowers/plans/2026-11-07-create-reso-world-issue-322-spec-plan-in-new-repo.md
git commit -m "docs: record issue 322 verification"
```

テストの要否: 要らない（検証の実行と記録）。

## 完了

- Task 1〜4 は ledger のとおり完了した。Task 3 は Task 2 のテストの実行中に検証が終わったので、先にコミットした
- 全体レビューの後の修正で、Plan と違う形になったもの（Spec の「実装の確認」に理由）:
  - Task 1: `--doc-repo` を `--doc-root` なしで渡したときは無視する（終了コード 64 の確認は L なので除いた）。拒否のケースは、重複を除いて「作業ツリーにだけある宣言」「origin の食い違い」「usaturn/resoloop-meshy」「create-reso-world の `DOC_ROOT`」の 4 つにした
  - Task 2: 条件は `DOC_REPO` でなく、context の正規化した名前を比べた `DOCS_SEPARATE` にした。テストの `TARGET_REPO` は `Sample-Owner/Other-Tool`
- push の前に `main` が `163717cd`（#332・#333）に進んだので、いったん止まり、利用者の指示で rebase した。重なるファイルは `AGENTS.md` だけで節が別のため、競合は無かった。全体の検証は rebase 後の HEAD でやり直した
- 全体の検証の結果は PR の本文に書く
