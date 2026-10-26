# Issue #178 accept の保存の I/O のエラーからの回復 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

- 状態: `draft`。内容の承認は記録しない
- 実行許可: 利用者の 2026-10-25（JST）の指示（`/issue-to-pr #178 --merge --max-cycles 3`。Spec の「実行許可」と同じ範囲）

**Goal:** review-verify の `dispatch.py accept` の保存の途中で `OSError` が起きたとき、accept が置いたものだけを置く前に戻して以前の確認済みの一覧を守り、同じ run を受け取り直せるようにする。

**Architecture:** `accept` の保存を新しい関数 `publish` に移す。`publish` は既存のエントリを一時ディレクトリへ写してから順に置き換え、例外では、置いたときの inode と内容のままのパスだけを写しで戻す（初回は消す）。`accept` は戻した後に保存先全体を dispatch 時の snapshot と照合し、一致すれば終了コード 1、しなければ 3 にする。照合・検査の既存のコードは変えない。

**Tech Stack:** Python 3.14（uv）、pytest、pydantic

**Spec:** `docs/superpowers/specs/2026-10-25-create-reso-world-issue178-accept-io-recovery-design.md`

## Global Constraints

- 変えるのは `.agents/skills/review-verify/scripts/dispatch.py`・`.agents/skills/review-verify/tests/test_dispatch.py`・`.agents/skills/review-verify/references/fix-check.md` だけ（Spec の D-178-7）
- 保存より前の検査（`check_batch`・`require_unchanged_review` の 2 回・PR・skill・inventory・`validate_document`・`check_statement_judgments`）は変えない（A-4）
- 置く順は sidecar（`<to12>.statement-candidates.json`）→ 本体（`<to12>.fix-check.json`）のまま
- 以前のエントリの退避: 一時ディレクトリ（`mkdtemp(prefix=".accept-", dir=verified/)`）に `<名前>.previous` として `shutil.copy2(..., follow_symlinks=False)` で写す。有無は `os.lstat` で判定し、`FileNotFoundError` だけを「無い」とする（D-178-3）
- 戻すのは、置いたパスの `st_dev`・`st_ino` と内容の sha256 が置いたときと同じときだけ（D-178-2）
- 終了コード: 戻した後の `review_changes` が空なら 1、空でない（`<review snapshot unavailable>` を含む）なら 3。stderr は 1 行で、例外の型と errno の名前だけを出し、例外の文は出さない（D-178-4）
- 2 件の JSON は `publish` を呼ぶ前に bytes にする（今の `json.dumps(..., ensure_ascii=False, indent=2) + "\n"` を UTF-8 にしたものと同じ bytes）
- テストは Spec の D-178-6 の T1・T2 だけを足す。それ以外は一時的な確認（コミットしない）で確かめる（`AGENTS.md` の「テストの採用基準」）
- 一時的な確認・ログ・ledger は worktree の外の `/workspaces/reso-world/tmp/agents/issue-178.3y9w1y18/` に置く（`AGENTS.md` の「コミットしないファイルの置き場所」）
- ruff はプロジェクトの環境に無いので `uvx ruff check` で代える。基準（`c1fdc56`）で 2 つのファイルに 11 件の指摘がある（`ruff-baseline.txt`）ので、変更の後に新しい指摘が増えていないことを比べる。`ruff format` は既存の差分が大きいので実行しない

## Review Focus

T1・T2 で確かめない入力・失敗のうち、利用者に効きやすい順。どれも、壊れても戻した後の照合が終了コード 3 とパスの列挙で示す（L）ので、Task 1 の Step 6 の一時的な確認で確かめ、コミットしない。

1. 初回の保存（同じ名前の結果が無く、`verified/` も無い）で本体の置き換えが失敗する → 終了コード 1、`verified/` が無くなり、同じ run の受け取り直しが 0
2. 置き換えの前（sidecar の置き換え自体）で失敗する → 終了コード 1、保存先全体が accept の前と同じ
3. 戻す操作（写しの `os.replace`）も失敗する → 終了コード 3、以前の sidecar の写しが一時ディレクトリに残り、stderr に dispatch 時と違うパスが並ぶ
4. 他者がその場で書き換えたのではなく、別のファイルで置き換えた（inode が違う）→ 戻さず終了コード 3（T2 はその場の書き換えだけを確かめる）
5. 保存の途中で `OSError` 以外の例外（`KeyboardInterrupt` など）が上がる → 戻してから上げ直し、accept は終了コードに変えない（保存先全体は accept の前と同じ）

## 要件と Task の対応（実装前の照合）

| Spec の受け入れ条件 | 担当 Task | 観測する結果 | 検証 |
| --- | --- | --- | --- |
| A-1 以前の組を不整合のまま残さない | Task 1 | T1: 終了コード 1、`managed_state(review_dir)` が accept の前と同じ、A の本体が `validate` を通る | T1 |
| A-2 初回と更新を分けて定義し、同じ run で受け取り直せる | Task 1（経路）・Task 2（定義） | T1 の受け取り直しが 0 で B が `validate` を通る。初回は一時的な確認。fix-check.md に時点ごとの表と回復の仕方 | T1、Task 1 の Step 6、Task 2 の Step 2 |
| A-3 本体・sidecar・一時ファイル・既存の状態の回帰テスト | Task 1 | T1・T2 が状態全体と bytes を確かめる | T1・T2 |
| A-4 照合を弱めない、他者の変更を戻さない | Task 1 | 保存より前のコードの差分が無い、T2 で他者の内容が残る、既存のテストが変えずに通る | `git diff`、T2、`.agents/skills/review-verify` のテスト全体 |
| A-5 保証する範囲と保証しない範囲 | Task 2 | fix-check.md の「保存する結果」に設計 4 の区別 | Task 2 の Step 2 |

共有する条件: 戻した後の照合（`review_changes`）は、dispatch・accept が使う snapshot と同じ観測値（通常ファイルは `mode:sha256`、inode を含まない）に依存する。写しで戻したファイルが同じ観測値になること（D-178-3）を、統合担当（このセッション）が T1 の `managed_state` の一致と Task 3 の Step 1 で確かめる。ほかに共有する入力・状態・順序・外部仕様は無い。

## 実行方式

`superpowers:executing-plans`（このセッションが inline で実装する）。`implement_task.py check` が `self=true` で、変更は同じ 3 つのファイルへの逐次の変更（Spec の D-178-8）。最後に、ブランチ全体のレビューを新しいレビュアー（サブエージェント 1 つ）に依頼する。

## 実行予算

- 全体の能動時間: 345 分（ledger の予算。ledger の開始は 2026-10-25T04:32:23Z で、それより前の準備（Issue・競合の確認、worktree の作成）は含まない）。PR の作成まで 120 分、`--merge` のループの段階 225 分（サイクルの上限 3 ×（レビューの期限 45 分＋計画・修正 約 30 分））。#177（同じ `dispatch.py` の変更とテスト）の実績から見積もった。ledger は `/workspaces/reso-world/tmp/agents/issue-178.3y9w1y18/budget.jsonl`
- phase の目安: Spec・Plan 20 分、Task 1 で 40 分、Task 2 で 15 分、Task 3（照合・最終レビュー・記録・README の入口）で 40 分、PR 5 分、ループ 225 分
- worker: 実装は inline。README の入口はバックグラウンドで実行し、終了の通知で待つ。絶対期限は README の入口の全体で 90 分（基準は数分〜25 分）、ログが 10 分変わらなければ stall を疑う。最終レビューのサブエージェントは 1 回で、期限 30 分。ループの worker の期限は pr-review-fix-loop の SKILL.md のとおり
- 再試行の上限: 同じ失敗の再試行は 1 回まで。T1・T2 が実装の後も落ちたら、再実行で上書きせず `superpowers:systematic-debugging` で調べる
- checkpoint: 各 Task の完了時、PR の作成時、予算の 50%（172 分）・100%、検証の失敗の直後
- 縮小・切り出し・方法変更の候補: (1) 主張の ID を変えた B が validate を通らなければ、B の違いを主張の文（`claim`）に変える（Contingency 1）(2) 一時的な確認の pytest を worktree の外から実行できなければ、同じ確認を `dispatch.py` の関数を直接呼ぶ短いスクリプトで行う (3) README の入口が環境の要因で失敗したら、`origin/main`（親の checkout）で同じコマンドを実行して既存の失敗と切り分ける

## Contingency

1. Task 1 の Step 2 で、B の受け取り（失敗を入れない対照）自体が validate で落ちる・inventory の照合で落ちるなら、主張の ID ではなく主張の文を変えた B にする。Spec の D-178-6 に追記してから続ける
2. 2 回目の dispatch が checkout の監査や出力先で止まるなら、`run_external` の出力先を変える引数を確かめ、runner の `output_dir` が既存でないことを確かめる
3. README の入口でこの変更と関係の無い失敗が出たら、そのテストを単独で 1 回実行し直して切り分け、記録する

---

### Task 1: 保存の失敗で自分の変更を戻し、終了コードを分ける

**Files:**
- Modify: `.agents/skills/review-verify/scripts/dispatch.py`（`import errno` を足す。新しい関数 `placed_here`・`publish` を `accept` の前に置く。`accept` の 557-572 行の保存の部分を置き換える）
- Test: `.agents/skills/review-verify/tests/test_dispatch.py`（`run_external` に出力先の引数を足す。補助 2 つとテスト 2 件を、受け取りのテストの近く（`test_accept_allows_candidates_and_terms_the_verifier_appended` の後）に足す）

**Interfaces:**
- Produces: `placed_here(path: Path, placed: os.stat_result, digest: str) -> bool` — `path` を `O_NOFOLLOW` で開き、`fstat` の `st_dev`・`st_ino` が `placed` と同じで、内容の sha256 が `digest` のときだけ True。`OSError` は False
- Produces: `publish(verified_dir: Path, files: list[tuple[str, bytes]]) -> None` — Spec の設計 1 のとおり。`BaseException` で戻してから上げ直す。成功したら一時ディレクトリを `rmtree(ignore_errors=True)` で消す
- Produces: `accept` は `publish` の `OSError` を `AcceptError` に変える。`review_changes(review_dir, before)` が空なら code 1、空でなければ code 3
- Produces（テスト）: `run_external(..., output: str = "run")`、`claim_renamed(scenario: Scenario, claim_id: str) -> dict[str, Any]`、`fail_replacing(monkeypatch, target: Path, before_failing: Callable[[], None] = ...) -> None`

**テストの要否:** T1・T2 を足す（Spec の D-178-6。T1 は以前に受け取った結果の保護と受け取り直しの経路、T2 は他者の変更を戻して消さないことの代表で、どちらも S）。初回の保存などは Step 6 の一時的な確認（L）。

- [x] **Step 1: 補助とテストを書く**

`run_external` に `output: str = "run"` を足し、`tmp_path / output` を dispatch の出力先にする（既存の呼び出しは変えない）。

```python
def claim_renamed(scenario: Scenario, claim_id: str) -> dict[str, Any]:
    """主張の ID だけを変えた、別の有効な結果。本体と sidecar の両方が変わる。"""
    payload = scenario.payload()
    payload["inventory"]["claims"][0]["id"] = claim_id
    payload["verified"]["fix_evidence"]["claims"][0]["id"] = claim_id
    return payload


def fail_replacing(monkeypatch, target, before_failing=lambda: None) -> None:
    """target への os.replace を 1 回だけ EIO で失敗させる。ほかの呼び出しと 2 回目からは本物を使う。"""
    # monkeypatch.undo() は autouse の Git の環境の隔離も外すので、回数で戻す。


def test_failed_save_keeps_the_previous_pair_and_the_same_run_can_be_accepted_again(
    dispatch, scenario, tmp_path, findings_helpers, managed_state, monkeypatch
) -> None:
    first = run_external(dispatch, scenario, tmp_path, scenario.payload())
    assert accept(dispatch, first) == 0
    body = scenario.review_dir / "verified" / f"{scenario.fix[:12]}.fix-check.json"
    before = managed_state(scenario.review_dir)
    second = run_external(dispatch, scenario, tmp_path, claim_renamed(scenario, "C-2"), output="run-2")
    fail_replacing(monkeypatch, body)
    assert accept(dispatch, second) == 1
    assert managed_state(scenario.review_dir) == before
    assert findings_helpers.review_findings.main(["validate", str(body)]) == 0
    assert accept(dispatch, second) == 0
    assert json.loads(body.read_text(encoding="utf-8"))["fix_evidence"]["claims"][0]["id"] == "C-2"
    assert findings_helpers.review_findings.main(["validate", str(body)]) == 0


def test_failed_save_does_not_restore_over_a_file_another_writer_changed(
    dispatch, scenario, tmp_path, monkeypatch, capsys
) -> None:
    # T1 と同じ A の受け取りと B の dispatch の後、本体の置き換えを失敗させる直前に
    # sidecar.write_bytes(b"another writer\n")（その場の書き換え。inode は同じ）
    assert accept(dispatch, second) == 3
    assert sidecar.read_bytes() == b"another writer\n"
    assert body.read_bytes() == previous_body
    assert [p for p in verified_dir.glob(".accept-*/*") if p.read_bytes() == previous_sidecar] != []（1 件）
    assert f"verified/{stem}.statement-candidates.json" in capsys.readouterr().err
```

docstring は周りのテストに合わせ、守ること（#178）を 1 行で書く。

- [x] **Step 2: 落ちることを確かめる**

Run: `uv run --locked pytest .agents/skills/review-verify/tests/test_dispatch.py -q -k "failed_save"`
Expected: 2 件とも FAIL（今の accept は `OSError` を捕まえないので、`accept()` から `OSError` が上がる）。補助（`claim_renamed` の B、2 回目の dispatch）の誤りで落ちていないこと: 失敗の行が `accept(dispatch, second)` で、例外が注入した `OSError` であることを読む。Contingency 1・2 の判断はここで行う

- [x] **Step 3: `placed_here`・`publish` と accept の変更を実装する**

`dispatch.py` に Interfaces のとおり実装する。`accept` の 2 回目の `require_unchanged_review` の後を、2 件の bytes を作って `publish(review_dir / "verified", [(sidecar の名前, bytes), (本体の名前, bytes)])` を呼ぶ形にし、今のコメント（sidecar を先に置く理由）を残す。`OSError` の理由の文は Spec の設計 2 のとおり（例: `saving failed (OSError EIO); review_dir is back to its state at dispatch, so accept can be retried with the same --run-dir`、`saving failed (OSError EIO); these paths differ from the state at dispatch: [...]`）。`publish` の docstring に、保証しない範囲（突然死・最後の観測の後の競合）を 1 行で書く

- [x] **Step 4: テストを通す**

Run: `uv run --locked pytest .agents/skills/review-verify/tests/test_dispatch.py -q -k "failed_save"` の後、`uv run --locked pytest .agents/skills/review-verify -q`
Expected: 2 passed、その後 68 passed（基準 66 + 2）

- [x] **Step 5: 静的検査**

Run: `uvx ruff check --output-format concise .agents/skills/review-verify/scripts/dispatch.py .agents/skills/review-verify/tests/test_dispatch.py`（出力を基準の `ruff-baseline.txt` と行番号を除いて比べる）、`git diff --check`
Expected: 新しい指摘が無い。`git diff --check` は終了コード 0

- [x] **Step 6: 一時的な確認（コミットしない）**

`/workspaces/reso-world/tmp/agents/issue-178.3y9w1y18/probe_accept_io.py` に、`test_dispatch.py` をパスで読み込んで fixture（`dispatch`・`scenario`・`findings_helpers`・autouse の Git の隔離・`outside_runner`）を使う pytest のファイルを書き、Review Focus の 1〜5 を確かめる。状態は `dispatch.snapshot_review` と bytes で比べる。

Run: `uv run --locked --project /workspaces/reso-world/.worktrees/issue-178-accept-io-recovery pytest -c /workspaces/reso-world/.worktrees/issue-178-accept-io-recovery/pyproject.toml --rootdir /workspaces/reso-world/.worktrees/issue-178-accept-io-recovery /workspaces/reso-world/tmp/agents/issue-178.3y9w1y18/probe_accept_io.py -q`（worktree を cwd にする）
Expected: 5 件とも PASS。ログを `probe-accept-io.log` に残す

- [x] **Step 7: Commit**

```bash
git add .agents/skills/review-verify/scripts/dispatch.py .agents/skills/review-verify/tests/test_dispatch.py
git commit -m "fix(review-verify): restore the previous pair when accept cannot save (#178)"
```

### Task 2: fix-check.md に回復の範囲と終了コードを書く

**Files:**
- Modify: `.agents/skills/review-verify/references/fix-check.md`（53 行の終了コード 1 の項目、54 行の後に終了コード 3 の項目、118 行の「保存する結果」）

**Interfaces:**
- Consumes: Task 1 の終了コード（1・3）、戻し方、写しの名前（`verified/.accept-*/<名前>.previous`）

**テストの要否:** 書かない（文書の文面の一致のテストは F）。差分を読んで、Spec の設計 2・3・4 と Task 1 の実装に一致することを確かめる。

- [x] **Step 1: 文書を直す**
  - 終了コード 1: 保存の途中の `OSError` でも 1 になり、helper は自分が置いたものを置く前に戻し、保存先全体が dispatch 時と同じことを確かめてから終わる。原因を直してから同じ `--run-dir` でやり直せる（外部の担当を起動し直さない）
  - 終了コード 3（新しい項目）: 保存の途中の `OSError` の後、dispatch 時の状態に戻せなかった・確かめられなかった。違うパスをエスケープして列挙する。以前の一覧は不整合なことがあり、以前のファイルの写しは `verified/.accept-*/<名前>.previous` に残る。回復の仕方は Spec の設計 3 の「終了コード 3 のとき」
  - 「保存する結果」: 2 件同時の一括置換を保証しないことは残し、Spec の設計 3 の表（初回の保存と既存の結果の更新）と、設計 4 の保証する範囲・保証しない範囲（突然死・最後の観測の後の他者の変更・切り替えの間の読み手・永続性）を書く。戻すのは置いたときの inode と内容のままのものだけであることも書く
- [x] **Step 2: 照合する**

Run: `git diff -- .agents/skills/review-verify/references/fix-check.md`、`git diff --check`
Expected: 書いた終了コード・戻し方・写しの場所が `dispatch.py` の実装と一致する。ほかの節（照合・停止確認の条件）の文を変えていない

- [x] **Step 3: Commit**

```bash
git add .agents/skills/review-verify/references/fix-check.md
git commit -m "docs(review-verify): describe accept recovery after I/O errors (#178)"
```

### Task 3: 統合の確認と記録

**テストの要否:** 新しいテストは書かない。README の「テスト」の入口と最終レビューで確かめる。

- [x] **Step 1: 条件ごとの照合** — 上の「要件と Task の対応」の各行について、差分・ログの該当箇所を挙げる。写しで戻したファイルの観測値が dispatch 時と同じになること（共有する条件）は、T1 の `managed_state` の一致で確かめたことを書く
- [x] **Step 2: 最終レビュー** — 新しいレビュアー（サブエージェント 1 つ）にブランチ全体（`origin/main...HEAD`）を渡し、Spec・Plan との一致、テストの採用基準、Review Focus、戻す対象の識別（他者の変更を戻さないこと）の正しさを確かめさせる。Critical・Important を直したら、関係する検証をやり直してから Step 1 からやり直す
- [x] **Step 3: 記録** — 下に「完了」の節を足し、所要時間と主要 Task 別の内訳、Task 1 の検証と一時的な確認の結果、レビューの結果を書いて commit する。これを最後の commit にする（`--merge` の検証の記録は最後の commit の後に作る）
- [ ] **Step 4: README の「テスト」** — 最後の commit の後に、worktree のルートで `bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`uv run pytest tests/skills .agents/skills .agents/scripts tools` を実行する。終了コード・ログの完全パス・検証した HEAD・`git status --porcelain` が空だったことを `/workspaces/reso-world/tmp/agents/issue-178.3y9w1y18/` に記録し、`finalize.py` の `--checks-file` の形のファイルも作る。結果は PR の本文に書く（この Plan には書かない。書くと HEAD が変わる）

## 完了

実装・最終レビュー・その修正は完了した。README の「テスト」（Task 3 の Step 4）はこの記録の commit の後に実行し、結果は PR の本文に書く。状態は `draft` のまま（内容の承認は記録しない）。

- 所要時間（2026-10-25 UTC。worktree の作成 04:24:44Z〜この記録 約 05:20Z、約 55 分。それより前の Issue・競合の確認は数分で、時刻は記録していない）
  - 準備（対象のコード・呼び出し側・文書の調査）と Spec（`e4208fb`、〜04:41:15Z）: 約 16 分
  - Plan（`c4da1b1`、〜04:44:12Z）: 約 3 分
  - Task 1（`d688026`、〜04:48:39Z。一時的な確認と変異の確認は〜04:50Z）: 約 6 分
  - Task 2（`2244006`、〜04:50:45Z）: 約 1 分
  - 最終レビュー（opus のサブエージェント 1 回、04:52Z〜05:09Z ごろ）: 約 17 分。待つ間に、PR 修正ループの手順を読み、検証の記録のスクリプトを用意した
  - 最終レビューの修正（`f40dd1d`・`11bd7a0`、〜05:14:01Z）と、変異・一時的な確認のやり直し: 約 6 分
  - 記録: 約 5 分
- 実行方式: inline（`superpowers:executing-plans`）。SDD の ledger は worktree の外の `/workspaces/reso-world/tmp/agents/issue-178.3y9w1y18/sdd/2026-10-25-create-reso-world-issue178-accept-io-recovery/progress.md` に置き、`sdd-workspace`・`task-start`・`task-done` は使わなかった（`AGENTS.md` の SDD 実行運用）
- 条件ごとの照合（Task 3 の Step 1）
  - A-1: T1（`test_failed_save_keeps_the_previous_pair_and_the_same_run_can_be_accepted_again`）が、2 件目の置き換えの EIO の後に終了コード 1、`managed_state(review_dir)` が accept の前と同じ、A の本体の `validate` が 0 であることを確かめる
  - A-2: T1 の受け取り直しが 0 で、B が `validate` を通る。初回の保存は一時的な確認（終了コード 1、`verified/` が無い、受け取り直しで 0）。fix-check.md に、時点ごとの表と、終了コード 1・3 の回復の仕方
  - A-3: T1・T2・T3 が、保存先全体か各ファイルの bytes を確かめる
  - A-4: `git diff origin/main` の `dispatch.py` の削除行は保存の部分だけで、2 回目の `require_unchanged_review` より前は変わらない。既存の 66 件は変えずに通る。T2 で他者の内容が残る。一時的な確認で、同じ内容・別の inode の置き換えも戻さない
  - A-5: fix-check.md の「保存する結果」に、保証する範囲（保存の処理の中の例外）と保証しない範囲（突然死・最後の観測の後の競合・切り替えの間の読み手・永続性）、`OSError` 以外の例外の扱い
  - 共有する条件（写しで戻したファイルの観測値）: T1 の `managed_state` の一致（mode と bytes）で確かめた。最終レビューも、sidecar を 0o440 にして戻した後の snapshot の一致を確かめた
- Task 1 の検証: RED は 2 件とも、accept から注入した `OSError` が上がって落ちた（`task1-red.log`）。GREEN は 2 passed、`.agents/skills/review-verify` は 68 passed。`uvx ruff check`（0.17.2）は基準（`c1fdc56`）と同じ 11 件で、新しい指摘は無い。`git diff --check` は 0
- 最終レビューの修正の後: `.agents/skills/review-verify` は 69 passed（`final-suite-head.log`、HEAD `11bd7a0`）。ruff の新しい指摘は無い
- 変異の確認（コミットしない。`mutations2.log`）: inode-only・drop-kept-copy・always-exit-1・no-post-check は T2、no-lexists-skip は T1、record-after-rename・oserror-only は T3、no-undo は 3 件とも落ちる。確かめた後に `git checkout` で戻し、worktree に差分は残っていない
- 一時的な確認（コミットしない。`probe_accept_io.py`・`probe-accept-io-final.log`）: 8 passed。Review Focus の 1〜5（4 は最終レビューの M-2 を受けて、同じ内容・別の inode の版にした）、本体の rename の後の `OSError`（終了コード 1 で両方戻る）、`review_dir` の中の権限を直すと受け取り直しが拒否されること、成功の後に一時ディレクトリが残らないこと
- 最終レビュー: Ready to merge: With fixes（Critical 0、Important 1、Minor 2）
  - I-1（Important、直した）: rename が済んだ後に届く例外（Ctrl-C のシグナル、成功した後に失敗を返すファイルシステム）では、置いた記録が無いので戻さず、以前の sidecar の唯一の写しも消えた。置く前に記録し、一時ファイルが残っていれば置き換えは起きていないと判断する形にして、T3（`test_an_interrupt_after_a_rename_is_undone`）を足した（RED→GREEN）
  - M-1（Minor を Important に格上げして直した）: `verified/` の権限など `review_dir` の中を変えて原因を直すと、受け取り直しは拒否される。Spec の設計 3 が「権限」を例に挙げていたので、fix-check.md・stderr の文・Spec を条件付きにした。文言なのでテストは足さず、一時的な確認で条件を確かめた
  - M-2（Minor、持ち越し）: `placed_here` の inode の照合を確かめるテストが無い。現行のコードは正しく（同じ内容・別の inode で戻さないことを一時的な確認で確かめた）、守る場面は同じ run の accept の並行（競合の範囲）なので直さない
- エージェントの判断（ledger の `Ruling:` の要点）: 最終レビューが範囲外として挙げた項目（突然死・永続性・最後の観測の後の競合・切り替えの間の読み手・呼び出し側・保存より前の traceback・一時ディレクトリの中への同じ利用者の書き込み・置き換える名前のディレクトリなど・snapshot が観測しない属性・無視できる幅）はどれも直さない。`verified/`・一時ディレクトリを作った直後に届く例外で空のディレクトリが残る幅は、直さずに文書に書いた
