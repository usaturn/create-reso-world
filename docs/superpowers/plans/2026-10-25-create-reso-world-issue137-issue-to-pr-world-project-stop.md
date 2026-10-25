# Issue #137 issue-to-pr をワールドのプロジェクトの作業で止める Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** issue-to-pr を、ワールドのプロジェクトを cwd にしたときとワールドの作業の Issue で使わず、使われても worktree を作る前に止まるようにする。

**Architecture:** `resolve_issue.py` が入力を読む前に cwd で `git check-ignore -q .` を実行し、git が追跡しないディレクトリの中なら終了コード 2 で止まる。`SKILL.md` は description の「使わない」と、2 章の停止条件・止まった後の扱いを足す。振る舞いは sonnet のサブエージェントの行動比較で確かめ、`evals/` に記録する。

**Tech Stack:** Python 3.14（uv）、pytest、git、Markdown、Claude Code の Agent ツール（model `sonnet`）。

**Spec:** `docs/superpowers/specs/2026-10-25-create-reso-world-issue137-issue-to-pr-world-project-stop-design.md`

状態: draft。実行許可は利用者の `/issue-to-pr #137 --merge --max-cycles 3`。内容の承認を意味しない。

## Global Constraints

- 変えるのは `.agents/skills/issue-to-pr/`（`scripts/resolve_issue.py`、`tests/test_resolve_issue.py`、`SKILL.md`、`evals/scenarios.json`、`evals/validation.md`）と、この Spec・Plan だけ（Spec の「対象外」）
- 停止は、`git check-ignore -q .` の終了コード 0 と、0・1 以外（確かめられない）。1 だけが続ける（Spec D1・D2）
- 追加するテストは 1 件だけ（Spec D6）。文言・frontmatter の照合テストは書かない
- 本物のモデルを起動するのは Task 3 の 9 回だけ（Spec D7）
- 変更は `/workspaces/reso-world/.worktrees/issue-137-world-project-stop`（branch `fix/issue-137-world-project-stop`）で行う。ログ・ledger・評価の材料は `/workspaces/reso-world/tmp/agents/issue-137.p0ogh8cd/` に置く
- 指示文は簡潔に書く

## Review Focus

| 観点 | Task と検証 |
| --- | --- |
| ワールドのプロジェクトの下の階層（`worlds/slum02/tests` など）を cwd にしても止まる | Task 1 のテストは下の階層から起動する |
| ルート・linked worktree・`external/resoloop` からは今までどおり解決する | 既存のテスト（ルートの checkout から解決）と Task 4 の Step 1 の実測 |
| ワールドの雛形・ツールの Issue（追跡するファイルの変更）を、ワールドの作業として止めない | Task 2 の 2 章の 4 の例と、Task 3 の (d) の回帰 |
| 明示の `/issue-to-pr` で、止まった後にワールドの作業へ黙って進まない | Task 3 の (wb) |
| `--merge` 付きでも、helper の停止がループ・worktree より前に来る | Task 1 のテストの入力に `--merge` を含める |

## 実行方式

`implement_task.py check` の結果は `agents: [self]`、`fallback: []`、`self: true`（Spec D9）。Task は 4 つで、Task 3 は Task 2 の `SKILL.md` に、Task 4 は全部に依存する。どれも短く、子に渡す文脈が作業そのものより大きいので、issue-to-pr の 4 章の表のとおり `superpowers:executing-plans` で、このセッションが順に実装する。Task 3 のサブエージェントは評価の方法（Spec D7）で、実装の委譲ではない。最後に、新しいサブエージェント（Claude Code の既定のモデル）にブランチ全体をレビューさせる。

## 実装前の要件照合

| Spec の条件 | 担当 Task | 観測する結果 | 検証 |
| --- | --- | --- | --- |
| 受け入れ条件 1（cwd がワールドの自然文の依頼で、作業を作らずにワールドの作業として進める） | Task 2（description・停止・扱い）、Task 3（評価） | 比較の版で (wa) が 3/3 | Task 3 の Step 3 |
| 受け入れ条件 2（(a)〜(j) が変わらない） | Task 2、Task 3 | 比較の版で (a)〜(j) が今の期待どおり 3/3 | Task 3 の Step 4 |
| 受け入れ条件 3（helper が `gh` の前に止まり Git を変えない、追跡するディレクトリでは解決） | Task 1 | 追加のテストと既存のテストが通る。追加のテストは guard を外すと失敗する | Task 1 の Step 2・4、Task 4 の Step 1 |
| 変更の内容 3 の明示の起動（伝えて終える） | Task 2、Task 3 | 比較の版で (wb) が 3/3 | Task 3 の Step 3 |

共有する条件は、helper の停止の意味（`git check-ignore -q .` が 0 なら止まる）と、止まった後の扱いである。Task 1 の stderr の案内と Task 2 の `SKILL.md` の「ワールドの作業で止まったとき」が同じ進め方（そのプロジェクトで branch・PR を使わずに進める。リポジトリのファイルの変更はルートで起動し直す）を指すかを、統合担当（このセッション）が Task 4 の Step 2 で確かめる。

## 実行予算

1. 全体の能動時間: 330 分。根拠: helper の数行・テスト 1 件・`SKILL.md` の追記と、9 回の行動比較で 2 時間ほど。`--merge` のループはサイクルの上限 3 ×（レビューの期限 45 分＋計画・修正 20 分）で最大 195 分
2. phase の目安: 準備・Spec・Plan 35 分、実装 25 分、評価 35 分、検証・全体レビュー 30 分、PR 10 分、ループ 195 分
3. worker: `bash .devcontainer/run-tests.bash` と `uv run pytest tests/skills .agents/skills .agents/scripts tools` は、それぞれ絶対期限 20 分、無進捗の打ち切りは出力が 10 分増えないとき。評価のサブエージェントは 1 回 20 分を期限とする（出力ファイルは完了まで進捗にならないので、無進捗では打ち切らない）。ループは pr-review-fix-loop の期限に従う
4. 再試行: 同じ失敗の再試行は 1 回まで（既定）。評価のサブエージェントがツールの制限を破った回は、その回を捨てて 1 回だけ取り直す
5. checkpoint: phase の境界、予算の 50%（165 分）・100%、worker の失敗の直後
6. 縮小・切り出し・方法変更の候補: 比較の版で (wa)・(wb) が 3/3 に届かなければ、`SKILL.md` の文面を直して比較だけを 1 回取り直す（方法変更）。それでも届かなければ、結果をそのまま記録し、PR に未達として書く。(a)〜(j) で回帰が出たら、原因の文面を直して (a)〜(j) だけを取り直す

ledger は `/workspaces/reso-world/tmp/agents/issue-137.p0ogh8cd/budget.jsonl`。

---

### Task 1: `resolve_issue.py` で、git が追跡しないディレクトリからの起動を止める

**Files:**
- Modify: `.agents/skills/issue-to-pr/scripts/resolve_issue.py`（`main` の `try` の先頭と、新しい関数）
- Test: `.agents/skills/issue-to-pr/tests/test_resolve_issue.py`

**Interfaces:**
- Produces: `require_tracked_cwd(cwd: Path) -> None`。止めるときは `ValueError` を投げ、`main` が `issue-to-pr: <理由>` を stderr に出して終了コード 2 を返す（既存の経路）

**テスト:** 1 件書く（Spec D6。停止が壊れると、エラーにならずに Spec・Plan だけの PR ができ、マージで Issue が閉じる）。

- [ ] **Step 1: 失敗するテストを書く**

既存の `checkout`・`gh_stub` の fixture を使う。docstring に防ぐ損害（#137）を書く。

```python
def test_refuses_to_start_from_a_directory_git_does_not_track(checkout: Path, gh_stub: Path) -> None:
    (checkout / ".gitignore").write_text("worlds/\n", encoding="utf-8")
    below_world = checkout / "worlds" / "slum02" / "tests"
    below_world.mkdir(parents=True)
    before = subprocess.check_output(["git", "status", "--porcelain"], cwd=checkout)
    result = resolve(below_world, "#42 --merge")
    assert_rejected(result)
    assert not gh_stub.exists()
    assert unchanged(checkout, before)
```

- [ ] **Step 2: 失敗を確かめる**

Run: `uv run pytest .agents/skills/issue-to-pr/tests/test_resolve_issue.py::test_refuses_to_start_from_a_directory_git_does_not_track -q`
Expected: FAIL（終了コード 0 で解決し、`gh` が呼ばれる）

- [ ] **Step 3: `require_tracked_cwd(cwd: Path) -> None` を実装し、`main` の `try` の先頭で `Path.cwd()` を渡して呼ぶ**

`subprocess.run(("git", "check-ignore", "-q", "."), cwd=cwd, capture_output=True, text=True, timeout=60)`。終了コード 1 なら戻る。0 なら次の理由で `ValueError`:

```text
cwd（<cwd>）は git が追跡しないディレクトリ（ワールドのプロジェクトなど）の中にあります。ワールドの作業は、そのプロジェクトで branch・PR を使わずに進めます（AGENTS.md の「プロジェクト運用」）。リポジトリのファイルを変える作業は、checkout のルートで起動し直してください
```

それ以外は `cwd（<cwd>）を git が追跡するかを確かめられません: <stderr>` で `ValueError`。`OSError`・`TimeoutExpired` は `main` の既存の `except` に任せる。関数の docstring に、止める理由（ワールドのプロジェクトは worktree に実体が無く、`Closes #N` で Issue が閉じる。#137）を 1〜2 行で書き、モジュールの docstring にもこの拒否を足す。

- [ ] **Step 4: テストが通ることと、既存のテストが通ることを確かめる**

Run: `uv run pytest .agents/skills/issue-to-pr/tests -q`
Expected: すべて PASS

- [ ] **Step 5: commit する**

```bash
git add .agents/skills/issue-to-pr/scripts/resolve_issue.py .agents/skills/issue-to-pr/tests/test_resolve_issue.py
git commit -m "fix: stop issue-to-pr from directories git does not track (#137)"
```

### Task 2: `SKILL.md` に、ワールドの作業での使い分けと停止を書く

**Files:**
- Modify: `.agents/skills/issue-to-pr/SKILL.md`（frontmatter の description、2 章の 3・4、2 章の末尾の新しい節「ワールドの作業で止まったとき」、「停止時の報告」の停止条件）

**Interfaces:**
- Consumes: Task 1 の停止（helper の終了コード 2 と stderr の案内）
- Produces: 節名「ワールドの作業で止まったとき」。Task 3 の評価がこの版を読む

**テスト:** 書かない（Spec D6。文面は F）。Task 3 の行動比較で確かめる。

- [ ] **Step 1: 文面を足す**

Spec の「変更の内容」2〜4 のとおり。

- description: 今の「…ボードの親 Issue からの子の選択には使わない。」の後に、「ワールドのプロジェクト（`worlds/<name>/` と従来位置）を cwd にしているときや、Issue がワールドの作業のときも使わない（そのプロジェクトで branch・PR を使わずに進める）。」を足す
- 2 章の 3: helper の失敗の項の後に、cwd が git で追跡しないディレクトリ（ワールドのプロジェクトなど）の中だと helper が入力を読む前に終了コード 2 で止まり、「ワールドの作業で止まったとき」に従うことを 1 項目で書く
- 2 章の 4: Issue がワールドのプロジェクトの中身を変える作業を含むときも止まり、「ワールドの作業で止まったとき」に従う。雛形（`templates/world-project/`）や `scripts/new-world.sh` など、追跡するファイルの変更は当たらない
- 2 章の末尾（`gh issue`・`gh pr` の段落の前）に「### ワールドの作業で止まったとき」: 作らないもの、進め方（`AGENTS.md` の「プロジェクト運用」）、明示の起動とモデルが選んだ run の扱い（Spec の変更の内容 3）
- 「停止時の報告」の停止条件の列に、この 2 つを足す

- [ ] **Step 2: 差分を読む**

Run: `git diff -- .agents/skills/issue-to-pr/SKILL.md`
Expected: 上の 5 か所の追加だけ。既存の手順・停止条件の文が変わっていない

- [ ] **Step 3: commit する**

```bash
git add .agents/skills/issue-to-pr/SKILL.md
git commit -m "docs: route world project work away from issue-to-pr (#137)"
```

### Task 3: 行動比較と評価の記録

**Files:**
- Modify: `.agents/skills/issue-to-pr/evals/scenarios.json`（(wa)・(wb) の追加）、`.agents/skills/issue-to-pr/evals/validation.md`（#137 の節の追加）
- 評価の材料と回答: `/workspaces/reso-world/tmp/agents/issue-137.p0ogh8cd/eval/`（コミットしない）

**Interfaces:**
- Consumes: Task 2 の `SKILL.md`（比較）、`origin/main` の `115f7c3` の `SKILL.md`（対照）

**テスト:** 書かない。行動比較そのものが検証。

- [ ] **Step 1: 材料を作る**

`eval/` の下に、意味の無い名前の 2 つのディレクトリを作り、それぞれに `issue-to-pr/SKILL.md`（対照は `git show 115f7c3:.agents/skills/issue-to-pr/SKILL.md`、比較は Task 2 の版）と、その版の description を入れたスキルの一覧を置く。一覧には、ワールドのプロジェクトで Claude Code に見えるスキル（`worlds/slum02/.claude/skills/` の resonite-*・meshy-resoloop）と、ルートの pr-review・review-fix-planning・planning-parallel-issues・superpowers:brainstorming を、それぞれの frontmatter の description のまま並べる。ルートの `AGENTS.md`（worktree の版）と `worlds/slum02/AGENTS.md` の写しも置く。

- [ ] **Step 2: (wa)・(wb) を scenarios.json に足す**

共通の状況: ランタイムは Claude Code。cwd は `/workspaces/reso-world/worlds/slum02`（ワールドのプロジェクト。独自の `.git` は無く、create-reso-world の main checkout の中で gitignore されていて、`git check-ignore -q .` は成功する。`#N` は create-reso-world の origin で解決できる）。読み込まれる指示はルートの `CLAUDE.md`→`AGENTS.md` と `worlds/slum02/CLAUDE.md`→`AGENTS.md`。#209 は create-reso-world の open の Issue で、本文は「slum02 の広場に屋台を 3 軒足す」。承認の要求・先行 Issue・予約・同じ Issue の PR・worktree・branch は無い。

- (wa) `wa-world-cwd-natural-language`: 利用者が自然文で「#209 に着手して。推奨案で進めて」。期待: issue-to-pr の流れ（worktree・branch・Spec・Plan・PR）に進まない。`worlds/slum02` で、プロジェクトの `AGENTS.md` に従ってワールドの作業として進める
- (wb) `wb-world-cwd-slash-command`: 利用者が `/issue-to-pr #209`。期待: helper が終了コード 2 で止まり、worktree・branch・PR を作らない。ワールドの作業はこのプロジェクトで branch・PR を使わずに進めると伝えて終え、ワールドの作業には進まない

- [ ] **Step 3: (wa)・(wb) を対照・比較で各 3 回取る**

Agent ツールで新しいサブエージェント（model `sonnet`）を 1 回の起動で 1 回答、6 回起動する。指示文の先頭に、コマンドを実行しないこと、Read は示したファイルだけ（`AGENTS.md` の 2 つとスキルの一覧。issue-to-pr を使うと決めたときだけその `SKILL.md`）を書く。問いは、使うスキル（使わないならその理由）、次に行う操作の順、作るもの・作らないもの、利用者への報告。回答を `eval/` に保存し、全回答を読んで判定する。文言の一致では採点しない。
Expected: 比較で (wa)・(wb) とも 3/3

- [ ] **Step 4: (a)〜(j) を比較の版で 3 回取る**

scenarios.json の context と (a)〜(j) の prompt・今の期待で、1 つの指示文にする。共通の状況に、このセッションのモデル ID（`claude-opus-5-5`）、`PARENT_ROOT`・cwd・`SKILL_DIR`、`PARENT_ROOT` に pr-review-fix-loop と review-fix-planning があること、agent-runner の雛形の `workflows.issue` の `implement` が `self` で個人設定に workflows の節が無いことを足す。ルートの `AGENTS.md` と比較の `SKILL.md` を Read で 1 回ずつ読ませ、3 回起動する。
Expected: (a)〜(j) とも今の期待どおり 3/3

- [ ] **Step 5: validation.md に #137 の節を足し、commit する**

評価方法と範囲、結果の表（(wa)・(wb) の対照と比較、(a)〜(j) の比較）、REFACTOR があればその内容、実行した検証、行っていない確認を書く。

```bash
git add .agents/skills/issue-to-pr/evals/scenarios.json .agents/skills/issue-to-pr/evals/validation.md
git commit -m "docs: record issue-to-pr world project evaluation (#137)"
```

### Task 4: 統合の確認

**Files:** 変更しない（ログは `/workspaces/reso-world/tmp/agents/issue-137.p0ogh8cd/` に置く）

**テスト:** 書かない。下の実行で確かめる。

- [ ] **Step 1: 実際の配置で helper を実行する**

Run: worktree の helper を、`/workspaces/reso-world/worlds/slum02`・`/workspaces/reso-world/worlds/slum02/tests`・`/workspaces/reso-world`・この worktree の 4 か所を cwd にして `-- "#137"` で実行する
Expected: ワールドの 2 か所は終了コード 2 で、stderr が Task 1 の案内。ルートと worktree は終了コード 0 で #137 を返す

- [ ] **Step 2: 差分全体を読む**

Run: `git diff origin/main -- .agents/skills/issue-to-pr`
Expected: Task 1〜3 の変更だけ。helper の stderr の案内と `SKILL.md` の「ワールドの作業で止まったとき」が同じ進め方を指す。既存の停止条件・手順の文が変わっていない

- [ ] **Step 3: README の「テスト」を実行する**

Run: `bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`uv run pytest tests/skills .agents/skills .agents/scripts tools`
Expected: どれも終了コード 0（着手時のベースラインと同じ結果）

- [ ] **Step 4: ブランチ全体のレビュー**

新しいサブエージェントに、Spec・Plan と `git diff origin/main` をレビューさせる。指摘は致命的なものだけを直し、直したら該当の検証をやり直す。
