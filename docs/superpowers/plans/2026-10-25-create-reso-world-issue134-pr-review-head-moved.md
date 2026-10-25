# Issue #134: pr-review の保存しなかった試行の片付け Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** pr-review の新しい入口で保存しなかった試行を、未保存の draft を失わずに helper で片付けられるようにし、再レビューの可否・片付け・報告をスキルに書く。

**Architecture:** prepare が試行 ID と候補の雛形の SHA-256 を state に残し、`abandon` は `--session-dir`・`--attempt-id` で試行を指定して、helper が書いたままのものだけを消す。prepare の後に止めるレビュアーは `fail --abandon` で同じ判定を使い、結果の JSON に片付けの結果を載せる。スキルは再レビューをしないこと、片付けの条件、報告の項目を書く。

**Tech Stack:** Python 3.14（uv）、pytest、Git の一時リポジトリの fixture、Markdown のスキル文書

**Spec:** `docs/superpowers/specs/2026-10-25-create-reso-world-issue134-pr-review-head-moved-design.md`

- 状態: draft
- 実行許可: Spec と同じ（`/issue-to-pr #134 --merge --max-cycles 3`）。本 Plan の内容の承認ではない
- 実行方式: `superpowers:executing-plans`（このセッションが自分で実装する）。`implement_task.py check` は `self: true`。Task 1 の helper の変更は 2 つのモジュールにまたがる 1 つのテストの単位で、Task 2 の文書は Task 1 の引数と結果の形を書くので、Task は独立せず順に進める。サブエージェントは builder check、振る舞いの比較、最後のブランチ全体のレビューだけに使う
- 作業領域: `/workspaces/reso-world/tmp/agents/issue-134.zmji0mac/`（実行予算の ledger `budget.jsonl`、基準のテストのログ `baseline/`、振る舞いの比較 `eval/`、executing-plans の ledger `sdd/2026-10-25-create-reso-world-issue134-pr-review-head-moved/progress.md`、一時的な検証 `verify/`）

## Global Constraints

- Python は `uv run` で実行する。リポジトリのテストは worktree のルートで `uv run pytest …` にする
- テストは `AGENTS.md` の「テストの採用基準」の S だけを書く（Spec の D9 の 2 件）。それ以外の分岐は `verify/` の一時スクリプトで確かめ、コミットしない
- worktree の中にコミットしないファイルを作らない。一時スクリプト・ログは作業領域に置く
- `abandon` は、未保存の draft（本文の draft がある、または候補の draft が prepare の雛形から変わった）を `--discard-draft` 無しに消さない。想定外のものは `--discard-draft` があっても消さない
- `abandon --session-dir` は、journal の開始の記録の `attempt_id`・`session_dir`・`worktree`・`pr_number` が指定と合わないと消さない
- HEAD の不一致の理由の文は `PR head changed after fetch (<12 桁> -> <12 桁>); stop without reviewing` と `PR head changed during review (<12 桁> -> <12 桁>); stop without saving`
- 文書は `AGENTS.md` の「日本語表現」に従い、指示文は「何をする／しない」を 1 行ずつ簡潔に書く

## Review Focus

1. 並行する別のレビュアーの試行（同じ PR・同じ checkout・雛形だけ）を、パスの誤りで消さない → Task 1 の `other_attempt`
2. coverage だけを書きかけた候補の draft を、雛形と見なして消さない → Task 1 の `findings`
3. 雛形の SHA-256 が state に無い試行（この変更より前のセッション、prepare の途中の中断）を、雛形と見なして消さない → Task 1 の `no_digest`
4. `--discard-draft` を付けても、review-backup の想定外のファイルを消さない → Task 1 の `discard_extra`
5. `fail --abandon` が、残した試行を報告から落とさない／消した試行を残したと報告しない → Task 1 の `test_fail_abandon_reports_what_it_removed_or_kept`

## 要件の照合

| Spec の受け入れ条件 | 担当 | 観測する結果 | 検証 |
| --- | --- | --- | --- |
| 1 試行ごとの扱い | Task 2 | SKILL.md の「保存しなかったとき」に、prepare の失敗・prepare の後の fail・complete の拒否の扱いと、消す人 | 振る舞いの比較の場面 A・B・C、`git diff` |
| 2 再レビューの可否と上限 | Task 2 | 同じ節と time-budget.md の S15・S24 | 比較の場面 A |
| 3 `abandon` の条件の一致 | Task 1・2 | helper の判定と節の条件が同じ | Task 1 のテスト、Step 6 の 1・5、比較の場面 C |
| 4 報告の項目と 2 つの head | Task 1・2 | 理由の文、節の報告の項目 | Step 6 の 1・3、比較の場面 A |
| 5 旧 3 地点の対応と分岐の実行 | Task 1・2 | 節の照合の地点、Step 6 の 1〜5 | `verify/` のログ |
| 6 `fail --abandon` の結果の一致 | Task 1 | `cleanup`・`retained_paths` | Task 1 のテスト |
| 7 README の「テスト」 | 統合の確認 | 3 つとも終了コード 0 | 作業領域のログ |

共有する条件: `run_context.findings_scaffold`（prepare が書き、`abandon` が読む）と、`abandon` の CLI・`fail --abandon` が使う同じ判定。統合の確認（このセッション）で、prepare から作った試行に両方の入口を当てて確かめる（Task 1 のテストと Step 6）。

## 実行予算

- Issue 全体の能動時間: 360 分（ledger の `--budget-minutes 360`）。内訳は Spec・Plan 30 分（ledger の開始の後）、Task 1 75 分、Task 2 50 分、統合の検証・ブランチ全体のレビュー・PR 45 分、PR 修正ループ 150 分（サイクルの上限 3 × レビュー 45 分＋計画・修正 5〜15 分。修正が無ければ 1 サイクル）。根拠: #39（helper の新しいサブコマンドとスキル）・#265（1 サイクルでマージ）の実績と、Task の数
- ledger の開始は 2026-10-25T04:42:58Z（着手は 04:23Z ごろ。それまでの約 20 分の調査は ledger の外）
- worker: builder check・振る舞いの比較・ブランチ全体のレビューのサブエージェントは、Claude Code の Agent ツールの完了通知で待つ（`task_watch.py` で包めない）。1 回の目安は 15 分。テストなどの検証コマンドは途中で止めない
- 再試行の上限: 同じ signature の失敗は再試行 1 回まで。振る舞いの比較で期待と違う答えが出たら、文書を 1 回だけ直し、変更後の版を 3 回だけ取り直す（本物のモデルの起動は最大 9 回）
- checkpoint: Task の境界、予算の 50%（180 分）・100%、worker の失敗の直後
- 縮小・切り出し・方法変更の候補: (a) `--discard-draft` を持ち越し、未保存の draft の片付けを利用者の手作業とする（Spec の D7 の変更として記録する）。(b) version 8 の保存ロックの変更（Spec の変更の内容 7）を持ち越す。(c) 振る舞いの比較を版ごとに 1 回にする。(d) 固定した ref の削除（変更の内容 6）を持ち越す

---

### Task 1: helper（試行 ID・雛形の SHA-256・`abandon --session-dir`・`fail --abandon`）

**Files:**
- Modify: `.agents/skills/pr-review/scripts/pr_review_workspace.py`（`create_from_target`、`verify_state`、`require_abandonable_entries`、`abandon_attempt`、`parser`、`WorkspaceParser.parse_args`）
- Modify: `.agents/skills/pr-review/scripts/review_run.py`（`prepare`、`result_fields`、`main`、`parser`）
- Test: `.agents/skills/pr-review/tests/test_review_run.py`（末尾に節を足す）

**Interfaces:**
- Produces（`pr_review_workspace.py`）:
  - `abandon_session_dir(session_dir: Path, attempt_id: str, *, discard_draft: bool = False) -> dict[str, Any]`。結果は `attempt_id`・`session_dir`・`status`（journal の状態）・`worktree`・`worktree_removed` と、version 8 の checkout の試行では `pr_ref`・`pr_ref_status`（`deleted`・`missing`・`repinned`・`kept`）。拒否は `WorkspaceError`
  - CLI: `abandon --attempt-id ID (--session-dir DIR | --repo R --pr-repo O/R --pr-number N [--temp-root T]) [--discard-draft]`。`--session-dir` と `--repo`・`--pr-repo`・`--pr-number`・`--temp-root` は一緒に使えない（`WorkspaceParser.parse_args` の `self.error`）。今の指定の経路も同じ判定で消し、`--discard-draft` を受け付ける
  - `require_abandonable_entries(session_dir: Path, *, owned_repo: Path | None = None, scaffold: tuple[str, str] | None = None, drafts: frozenset[str] = frozenset()) -> None`。review-backup では、既存レビューの写し、`scaffold`（名前, SHA-256）と一致するファイル、`drafts` の名前のファイルだけを許す。拒否の文には今と同じく `review backup` と `unexpected entry` を含める
  - version 8 の試行の `abandon` の保存ロックは、journal の `parent_root` の checkout（`require_parent_root` で確かめる）。version 7 は今と同じ
  - `create_from_target` の journal の `started` に `pr_head` を足す
- Produces（`review_run.py`）:
  - `prepare` は `uuid.uuid4().hex` の試行 ID を `workspace.create` の `attempt_id` に渡す。成功の結果と、セッションを残した失敗の結果に `attempt_id` を返す
  - `session.json` の `run_context.attempt_id: str` と `run_context.findings_scaffold: {"name": str, "sha256": str}`。雛形を書いた後に state を書く（中断で SHA-256 が無ければ、`abandon` は雛形を消さない）
  - `result_fields` に `attempt_id`（`run_context` に無ければ null）
  - `fail --abandon`（`--state` が要る。無ければ失敗の結果）。`fail_review` の後に `workspace.abandon_session_dir(<state の親>, <journal の試行 ID>)` を呼び、成功で `cleanup: "success"`・`cleanup_details: <abandon の結果>`・`retained_paths: null`、拒否で `cleanup: "failed"`・`cleanup_details: {"error": <理由>}`・`retained_paths`（今と同じ）。`--discard-draft` は付けない
- Consumes: 既存の `finished_creator`・`owned_attempt_repository`・`remove_attempt_worktree`・`delete_pinned_ref`・`pinned_review_ref`・`findings_artifact_paths`・`read_journal`・`journal_attempt`

テストの要否: 書く（Spec の D9）。壊れると、未保存のレビューや別の試行をエラー無しに消す、または片付けの結果を誤って報告する（S）。

- [ ] **Step 1: 失敗するテストを書く**

`test_review_run.py` の末尾に `# --- 保存しなかった試行の片付け（Issue #134） ---` の節を足す。

```python
@pytest.mark.parametrize(
    "case",
    ["scaffold", "markdown", "findings", "no_digest", "other_attempt", "discard", "discard_extra"],
)
def test_abandon_session_dir_removes_only_what_prepare_left(
    prepared: dict[str, Any], capsys: pytest.CaptureFixture[str], case: str
) -> None:
    # 守りは pr_review_workspace.py の判定。雛形の SHA-256 を書く prepare から試行を作るので、ここに置く
    result = review_run.prepare(prepared["args"])
    session, attempt = Path(result["state_file"]).parent, result["attempt_id"]
    # case ごとの準備: markdown は本文の draft を書く。findings は候補の coverage.read を書く。
    # no_digest は session.json の run_context.findings_scaffold を消す。other_attempt は attempt を "f" * 32 にする。
    # discard・discard_extra は mark_reviewed(result)。discard_extra は review-backup/notes.txt も書く
    argv = ["abandon", "--session-dir", str(session), "--attempt-id", attempt]
    if case.startswith("discard"):
        argv.append("--discard-draft")
    code = review_run.workspace.main(argv)
    worktrees = git(prepared["source"], "worktree", "list", "--porcelain")
    ref = git(prepared["source"], "for-each-ref", "refs/pr-review/repos/example/syncer/7")
    if case in {"scaffold", "discard"}:
        assert code == 0
        assert json.loads(capsys.readouterr().out)["pr_ref_status"] == "deleted"
        assert not session.exists() and str(session / "worktree") not in worktrees and ref == ""
    else:
        assert code == 2
        assert session.is_dir() and str(session / "worktree") in worktrees and ref != ""
        # markdown・findings・discard_extra は、書いたファイルの bytes が変わらないことも確かめる
```

```python
@pytest.mark.parametrize("drafted", [False, True])
def test_fail_abandon_reports_what_it_removed_or_kept(
    prepared: dict[str, Any], capsys: pytest.CaptureFixture[str], drafted: bool
) -> None:
    result = review_run.prepare(prepared["args"])
    session = Path(result["state_file"]).parent
    if drafted:
        Path(result["draft"]).write_text("書きかけのレビュー\n", encoding="utf-8")
    code = review_run.main(
        ["fail", "--state", result["state_file"], "--reason", "PR の HEAD が依頼と違う", "--abandon"]
    )
    payload = json.loads(capsys.readouterr().out)
    assert code == 1 and payload["status"] == "failed"
    assert only_record(prepared["parent"])["failed_at"] == "review"
    if drafted:
        assert payload["cleanup"] == "failed" and payload["cleanup_details"]["error"]
        assert payload["retained_paths"]["session_dir"] == str(session) and session.is_dir()
    else:
        assert payload["cleanup"] == "success" and payload["retained_paths"] is None
        assert payload["cleanup_details"]["session_dir"] == str(session) and not session.exists()
```

- [ ] **Step 2: テストが失敗することを確かめる**

Run: `uv run pytest .agents/skills/pr-review/tests/test_review_run.py -k "abandon_session_dir or fail_abandon" -q`
Expected: FAIL（`KeyError: 'attempt_id'` か、`--session-dir`・`--abandon` の argparse の拒否）

- [ ] **Step 3: `pr_review_workspace.py` を実装する**

Interfaces のとおり。`abandon_session_dir` は、ディレクトリ（symlink でない）と journal の開始の記録を確かめ、`main_root` を `require_main_checkout` で確かめてから、保存ロック（version 8 は `parent_root`）の中で、今の `abandon_attempt` の本体（`finished_creator` → `owned_attempt_repository` → `require_abandonable_entries` → `remove_attempt_worktree` → ref → `shutil.rmtree`）を呼ぶ。今の指定の経路も、試行を探した後に journal から保存ロックの場所を決め、ロックの中で探し直して同じ本体を呼ぶ。`session.json` は JSON として読めるときだけ使い（読めなければ雛形と draft の名前を許さない）、draft の名前は `state["draft"]` の名前と `findings_artifact_paths` の候補の名前、雛形は `run_context.findings_scaffold` の名前が候補の名前と同じで SHA-256 が 64 桁の 16 進のときだけ使う。ref の期待値は state の `pr_head`、無ければ journal の `pr_head`（どちらも 40 桁の 16 進のときだけ）で、無ければ `kept`。HEAD の理由の文は Global Constraints のとおり

- [ ] **Step 4: `review_run.py` を実装する**

Interfaces のとおり。`main` は、`fail --abandon` で消したとき（`cleanup == "success"`）に、最後の `retained_paths(state)` の上書きをしない

- [ ] **Step 5: テストが通ることを確かめる**

Run: `uv run pytest .agents/skills/pr-review/tests -q`
Expected: PASS（既存の abandon・cleanup・moving HEAD のテストを含む）

- [ ] **Step 6: 採用した分岐をローカルの fixture で確かめる（コミットしない）**

`verify/test_issue134_branches.py` を作業領域に作り、`test_review_run.py` の `prepared` と同じ fixture（`gh` を呼ばない偽の PR API と、ローカルの bare リポジトリ）で次を実行して、結果のログを `verify/` に残す。

1. prepare の中の HEAD の不一致（worktree を作った後の API の head を変える）: prepare が `failed`、理由に 2 つの 12 桁、結果に `attempt_id` と `retained_paths.session_dir`。その試行は `abandon --session-dir` で消える（`session.json` が無く、journal の `pr_head` で ref を消す）
2. prepare の中の HEAD の不一致（fetch の前に PR の head を進める）: prepare が `failed`。ref は新しい head を指すので `abandon` の `pr_ref_status` は `repinned`
3. complete の HEAD の不一致: `failed`・理由に 2 つの 12 桁・保存先が無い・draft が残る。`abandon` は拒否し、`--discard-draft` で消える
4. 3 の後、新しい head で新しい prepare → complete が `success`
5. version 7 の試行（`create` の今の指定）を今の指定と `--session-dir` の両方で `abandon` できる

Run: `uv run pytest -c pyproject.toml --rootdir . /workspaces/reso-world/tmp/agents/issue-134.zmji0mac/verify/test_issue134_branches.py -q`（worktree のルートで）
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add .agents/skills/pr-review/scripts/pr_review_workspace.py .agents/skills/pr-review/scripts/review_run.py .agents/skills/pr-review/tests/test_review_run.py
git commit -m "feat(pr-review): 保存しなかった試行を abandon で片付けられるようにする (#134)"
```

### Task 2: スキルの文書と振る舞いの比較

**Files:**
- Modify: `.agents/skills/pr-review/SKILL.md`（実行時の共通規則の削除と helper の項目、手順 5、新しい節「保存しなかったとき」を「手順」の後に置く）
- Modify: `.agents/skills/pr-review/references/noninteractive.md`（fail の節、結果の表の `attempt_id`・`cleanup`・`retained_paths`、停止条件）
- Modify: `.agents/skills/pr-review/references/time-budget.md`（打ち切りの保存拒否の項目、検証シナリオの S15・S23・S24）

**Interfaces:**
- Consumes: Task 1 の CLI（`abandon --session-dir … --attempt-id … [--discard-draft]`、`fail --abandon`）と結果の欄（`attempt_id`・`cleanup`・`cleanup_details`・`retained_paths`）、理由の文

テストの要否: 書かない。文面の照合は F。代わりに振る舞いの比較（Spec の D10）と `git diff` の確認を行う。

- [ ] **Step 1: 変更前の振る舞いを取る**

作業領域の `eval/prompt.md` の問い（場面 A: 対話で complete が HEAD の不一致で失敗、場面 B: 非対話で prepare の reviewed_head が依頼の pr_head と違う、場面 C: 利用者が残った draft のある試行の片付けを指示）を、`eval/before/pr-review/`（`origin/main` `c1fdc56` の SKILL.md と参照文書）に対して、Agent ツールの新しいサブエージェント（model `sonnet`、読み取りだけ）で 3 回答えさせ、`eval/before-<n>.md` に残す

- [ ] **Step 2: 「保存しなかったとき」の節と関係する項目を書く**

節の内容は Spec の D1〜D8 のとおり。照合の地点（prepare の 2 つと complete）と途中の照合が要らない理由、再レビューをしないこと（0 回、prepare を呼び直さない、新しい HEAD のレビューの始め方）、`fail --abandon` を使う場面と条件、prepare の失敗と complete の拒否はレビュアーが消さないこと、利用者の指示での `abandon --session-dir`（と `--discard-draft`）と helper の条件、報告の項目。実行時の共通規則の「削除は cleanup だけ」「旧 create の inspect/abandon は互換 API」と、手順 5 の失敗の扱いは、この節を指す形に直す

- [ ] **Step 3: noninteractive.md と time-budget.md を直す**

noninteractive.md: fail の節に `--abandon`、結果の表に `attempt_id` の行、`cleanup` と `retained_paths` の行に fail の場合、停止条件の moving PR head に「自動でレビューし直さない」。time-budget.md: 打ち切りの保存拒否の項目を「SKILL.md の『保存しなかったとき』のとおり報告し、予算が残っていても再レビューしない」に、S15 を complete の拒否の期待（保存しない・再レビューしない・draft のある試行を残す・2 つの head と draft の完全パスと次の操作を報告）に直し、S23（prepare の後に依頼の HEAD と違う → `fail --abandon`、`cleanup: success`、`retained_paths: null`）と S24（prepare の中の HEAD の不一致 → 再実行しない、試行を残して `attempt_id`・`session_dir` と次の操作を報告）を足す

- [ ] **Step 4: 変更後の振る舞いを取って比べる**

Task 2 の変更を commit してから、その版を `eval/after/pr-review/` に写し、Step 1 と同じ問いで 3 回答えさせ、`eval/after-<n>.md` に残す。期待: 場面 A は helper を呼ばず（prepare・complete・abandon をしない）、報告に 2 つの head・draft の完全パスと有無・試行を残したこと・`attempt_id`・`session_dir`・新しい HEAD のレビューの始め方・`abandon --discard-draft` を含める。場面 B は `fail --state … --reason … --abandon` で、その結果をそのまま返す。場面 C は `abandon --session-dir /tmp/pr-review-300-ab12cd34 --attempt-id … --discard-draft`。3 回のうち 1 回でも外れたら、原因の文を 1 回だけ直して取り直す（実行予算の再試行の上限）

- [ ] **Step 5: Commit**

```bash
git add .agents/skills/pr-review/SKILL.md .agents/skills/pr-review/references/noninteractive.md .agents/skills/pr-review/references/time-budget.md
git commit -m "docs(pr-review): 保存しなかったときの再レビューと片付けを書く (#134)"
```

### 統合の確認と PR

- [ ] 受け入れ条件 1〜7 を、Spec → Task → 実行した確認の順に照合する（`review-fix-planning/references/convergence.md` の「3. 検証と閉じ方」）
- [ ] README の「テスト」の 3 つ（`bash .devcontainer/run-tests.bash`・`bash scripts/check-layout.sh`・`uv run pytest tests/skills .agents/skills .agents/scripts tools`）を最後の commit で実行し、HEAD・`git status --porcelain`・argv・終了コード・ログの完全パスと `finalize.py` の `--checks-file` の形のファイルを作業領域に記録する
- [ ] ブランチ全体のレビューを、新しいサブエージェント（読み取りだけ）に依頼する。致命的な指摘だけ直す
- [ ] Spec・Plan の「完了」の記録を足して commit し、push の前の検査、push、PR の作成、PR 修正ループへ進む（issue-to-pr の 5 章）

## 完了

（実装の後に、所要時間と主要 Task 別の内訳、振る舞いの比較の結果、検証の結果を書く）
