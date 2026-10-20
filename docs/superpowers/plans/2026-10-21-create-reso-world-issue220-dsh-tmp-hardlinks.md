# Issue #220: DSH の TMPDIR に残るハードリンクを停止後に消す Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** DSH の担当が sandbox の中で pytest を実行して TMPDIR にハードリンクの fixture を残しても、成功した回答が `response_failed` にならないようにする。`tmp/` の外のハードリンクは今どおり成功にしない。

**Architecture:** 停止後の `_prune_scratch` が `<attempt>/dsh/tmp` を辿るときに消す対象（今は symlink・FIFO などの通常ファイルでないもの）に、リンク数 2 以上の通常ファイルを足す。開かず、名前だけを `os.unlink(name, dir_fd=…)` で消す。`_redact_runtime_tree` と state の決め方は変えないので、消せなかったハードリンクや `tmp/` の外のハードリンクは今どおり報告される。

**Tech Stack:** Python 3.14、pytest、bubblewrap（偽の CLI を bwrap の中で動かす runner の実経路のテスト）

**Spec:** `docs/superpowers/specs/2026-10-21-create-reso-world-issue220-dsh-tmp-hardlinks-design.md`

## 管理

- 状態: draft
- 対象 Issue: https://github.com/usaturn/create-reso-world/issues/220
- DOC_ROOT・CODE_ROOT: `/workspaces/reso-world/.worktrees/issue-220-dsh-tmp-hardlinks`（branch `fix/issue-220-dsh-tmp-hardlinks`）。PARENT_ROOT: `/workspaces/reso-world`
- 実行許可: Spec の「管理・実行許可」と同じ（`/issue-to-pr … --merge --assign implement=self`。PR の作成後に PR 修正ループを回し、修正不要ならループの `finalize.py` がマージする）
- 実行方式: inline（`superpowers:executing-plans`）。`implement_task.py check` の `self` が true で、Task 1 は同じファイル群を TDD の順に逐次変更し、Task 2 は Task 1 の結果に依存する統合確認である。委譲しても並行できず、文脈を渡す手間が上回る。独立したレビューは Task 2 の最後のブランチ全体のレビュー（新しいコンテキストのサブエージェント）で受ける
- 検証のログ・実行の記録（ledger `budget.jsonl` を含む）: `/workspaces/reso-world/tmp/agents/issue-220.z5vcohqb/`（commit しない。worktree の中には置かない）
- 基準: `origin/main` の `4d41f1a`（DSH のテスト全体は 283 passed。`baseline-dsh-dir.log`）

## Global Constraints

- 消す対象を広げるのは `_prune_scratch` が辿る `<attempt>/dsh/tmp` の下だけ。`state/`・patch・receipt・HOME の処理、`_redact_runtime_tree`・`redact_file`・state の決め方は変えない（Spec の設計 1・4）
- 消すのは「自分が所有し（`st_uid == os.getuid()`）、runtime root と同じ device（`st_dev`）にある、通常ファイルでないもの、または `st_nlink > 1` の通常ファイル」。ファイルを開かず、読まず、書き換えない。一覧を閉じた後に `os.unlink(name, dir_fd=…)` で消す今の順序を保つ
- 関数名は `_unlink_special_entries` から `_unlink_unredactable_entries` に変える（D-220-3）
- テストの秘密の値は既存の fixture の `private-test-credential`（`config` fixture の `COMMANDCODE_API_KEY`）を使う
- テストは偽の CLI だけを使う。本物の担当（モデル）を起動しない（AGENTS.md「エージェント運用」）

## Review Focus

- 親と子のディレクトリにまたがるハードリンクの組（`test_adapter.py:744` の `credentials` と `worktree/shared-hardlink` の形）: 後に残る名前は redact され、秘密の値が残らない → Task 1 の `test_scratch_hardlinks_are_unlinked_and_the_rest_redacted`（`nested/shared.json`）
- `state/` のハードリンク: 今どおり `response_failed` で、両方の名前が残って報告される → Task 1 の `test_runtime_hardlinks_are_rejected_before_redaction_hides_the_link`
- ハードリンクの unlink の失敗: 黙って成功にせず報告する → Task 1 の `test_scratch_unlink_failure_is_reported_not_success[tmp-hardlink]`
- TMPDIR のリンク数 1 の通常ファイル（pytest の `clean.txt`、DSH の spill）: 消し過ぎず、redact して残す → 既存の `test_real_pytest_scratch_is_accepted`・`test_large_tmpdir_spill_is_kept_in_runtime_tree_and_redacted`（Task 2 の Step 2 の対照検証で、消し過ぎると落ちることを確かめる）
- 実際の pytest が basetemp に残すハードリンク: `success` になる → Task 1 の `test_real_pytest_scratch_is_accepted[pytest-fixtures]` と、Task 2 の Step 3（リポジトリの実際のテストでの再現）

## 要件と Task・検証の対応

| Spec の受け入れ条件 | 担当 Task | 観測する結果 | 検証方法 |
| --- | --- | --- | --- |
| 1. TMPDIR のハードリンクの fixture だけでは `success` が変わらない | Task 1（統合は Task 2） | `tmp-hardlink`・`pytest-fixtures` が `success`・`sensitive_paths == []` | Task 1 の Step 3（修正の前は failed）・Step 5、Task 2 の Step 3（実際のテストの再現の前後） |
| 2. `tmp/` の外は変えない。`state/` のハードリンクは `response_failed` | Task 1 | `hardlink`（`state/`）が `response_failed`、両方の名前が報告され、リンク数 2 のまま | Task 1 の Step 3・Step 5、Task 2 の Step 2（prune を `state` にも広げると落ちる対照） |
| 3. 残す場合と残さない場合の両方を runner の実経路で確かめる | Task 1 | 残す: `tmp-hardlink`・`pytest-fixtures` が `success`。残さない: `success` のモード・`pytest` が `success` | Task 1 の Step 5、Task 2 の Step 1 |
| 4. 秘密の値が redact されずに残る経路を増やさない | Task 1（統合は Task 2） | `tmp-hardlink` の後、`dsh/` の下のどのファイルにも秘密の値が無く、`dsh/tmp` に残る通常ファイルはリンク数 1。unlink の失敗は報告 | Task 1 の Step 5、Task 2 の Step 2（redact のリンク数の検査を `tmp` で外すと落ちる対照） |
| 5. DSH のテスト全体と README の入口で、この変更による失敗が無い | Task 2 | 各入口の終了コード。失敗があれば基準（`4d41f1a`）の同じ実行と比べる | Task 2 の Step 1・Step 7 |

共有する前提: 変えるのは停止後の処理の 1 か所（`_prune_scratch` の判定）で、テストはどれも同じ `run_workflow` の経路を通る。prune → redact の順序と、`tmp/` の外を変えないことは、統合担当の Task 2 が対照検証（Step 2）で確かめる。

## 実行予算

- Issue 全体の能動時間の予算: 240 分（ledger: `/workspaces/reso-world/tmp/agents/issue-220.z5vcohqb/budget.jsonl`）。根拠は #219（同じ種類の DSH のテストまわりの修正。240 分の予算で、PR の作成の前まで約 31 分）。この Issue は runner の判定とテストの変更があるので、PR の作成の前まで 2 時間ほどを見込む
- phase の目安: 準備・調査 25 分（済）、Spec・Plan 20 分、Task 1 25 分、Task 2 40 分（実際のテストの再現・対照検証・最終レビューの待ち・README の入口）、PR 10 分、PR 修正ループは残り（最大 3 サイクル ×（レビューの期限 45 分＋計画・修正 15 分）のうち、予算に収まる範囲）
- worker は使わない（inline）。最終レビューのサブエージェントは 1 回だけ起動する。長時間の実行（`run-tests.bash`・pytest 全体）はバックグラウンドで実行し、終了コードで確かめる。1 回の期限は 30 分。負荷で時間切れのテストが出ないよう、README の入口は並行させず順に実行する
- 再試行の上限: 同じ signature の信頼性の失敗（テストの時間切れ・環境の I/O の停止）は 1 回まで。安全の失敗（実リポジトリ・親の `.venv` の書き換えの疑い、想定外の外部送信、本物の担当の起動）は再試行せず止まる
- checkpoint: Task 1 の後、Task 2 の後、ループの各サイクルの後、予算の 50%・100%（100% では停止して報告する）
- 縮小・方法変更の候補: Task 2 の Step 3 の再現で、リポジトリのテストが sandbox の中で import できないなど再現の形が動かなければ、偽の CLI の結果（Task 1）だけで受け入れ条件 1 を判定し、再現できなかった理由を記録する。README の入口が環境の要因で落ちたら、基準（`4d41f1a`）の同じ実行と比べて差分だけを判定する

## Task 1: `tmp/` のハードリンクも消す（TDD）

**Files:**
- Modify: `tools/agent_runner/tests/adapters/dsh/fake_cli.py:34-49`（`_PYTEST_CASE`）、`:209-220`（モード）
- Modify: `tools/agent_runner/tests/adapters/dsh/test_runner.py:210-218`、`:374-385` の後（新しいテスト）、`:388-409`、`:412-429`
- Modify: `tools/agent_runner/runner.py:145-205`（`_unlink_special_entries`・`_prune_scratch`）、`:488-495`（コメントと呼び出し）
- Modify: `tools/agent_runner/adapters/dsh.py:8-10`（module docstring）
- Modify: `.devcontainer/README.md:596`

**Interfaces:**
- Produces: `_unlink_unredactable_entries(directory: int, owner: int, device: int) -> list[str]`（`runner.py` の private。開いたディレクトリの、自分が所有し同じ device にある「通常ファイルでないもの、または `st_nlink > 1` の通常ファイル」を消し、サブディレクトリの名前を返す）。偽の CLI のモード `tmp-hardlink`（変更）・`hardlink`（新規）

**テストの要否:** 書く。停止後の判定（消す・報告する・成功にする）を変えるので、受け入れる入力（TMPDIR のハードリンク）と拒否し続ける入力（`state/` のハードリンク、unlink の失敗）を対にして、runner の実経路で確かめる（AGENTS.md「テストの採用基準」の「書く」）。

- [x] **Step 1: 偽の CLI を変える**（`fake_cli.py`）

`_PYTEST_CASE` の fixtures の分岐のコメントを「links out of tmp_path, a FIFO and a hard link pair」にし、`os.mkfifo(...)` の後に足す（文字列の中なので `\\n`）:

```python
        (tmp_path / "original.json").write_text("synthetic linked fixture\\n")
        os.link(tmp_path / "original.json", tmp_path / "linked.json")
```

`fifo` の分岐の後に `state/` のモードを足す:

```python
    elif mode == "hardlink":
        original = state / "original.json"
        original.write_text("synthetic content")
        os.link(original, original.with_name("linked.json"))
```

`tmp-hardlink` の分岐を次に置き換える:

```python
    elif mode == "tmp-hardlink":
        # Like pytest fixtures left in TMPDIR: a pair in one directory and a name in a child directory.
        scratch = Path(os.environ["TMPDIR"])
        original = scratch / "original.json"
        original.write_text(f"synthetic content {key}\n")
        os.link(original, scratch / "linked.json")
        (scratch / "nested").mkdir()
        os.link(original, scratch / "nested" / "shared.json")
```

- [x] **Step 2: テストを書く**（`test_runner.py`）

`test_runtime_hardlinks_are_rejected_before_redaction_hides_the_link` の本体を次にする:

```python
    # Retained records keep the strict policy; only TMPDIR scratch hard links are unlinked.
    config.agents["a"].command[-1] = "hardlink"
    result = run_workflow(config, "test", "respond", repository, output_dir=tmp_path / "run")
    attempt = result.results[0].attempts[0]
    assert attempt.state == "response_failed" and attempt.stop_confirmed
    assert attempt.request_path is not None
    state = attempt.request_path.parent / "dsh/state"
    assert {state / "original.json", state / "linked.json"} <= set(attempt.sensitive_paths)
    # Redaction replaced neither name, so the second link is still visible.
    assert (state / "linked.json").stat().st_nlink == 2
```

`test_scratch_links_and_fifos_are_unlinked_not_followed` の後に新しいテストを置く:

```python
def test_scratch_hardlinks_are_unlinked_and_the_rest_redacted(
    config: Config, repository: Path, tmp_path: Path
) -> None:
    config.agents["a"].command[-1] = "tmp-hardlink"
    result = run_workflow(config, "test", "respond", repository, output_dir=tmp_path / "run")
    attempt = result.results[0].attempts[0]
    assert attempt.state == "success" and attempt.stop_confirmed
    assert attempt.sensitive_paths == []
    assert attempt.request_path is not None
    root = attempt.request_path.parent / "dsh"
    assert not os.path.lexists(root / "tmp" / "original.json")
    assert not os.path.lexists(root / "tmp" / "linked.json")
    files = [path for path in root.rglob("*") if path.is_file() and not path.is_symlink()]
    # A name left with a single link is an ordinary scratch file, redacted like the others.
    assert all(path.lstat().st_nlink == 1 for path in files if path.is_relative_to(root / "tmp"))
    assert all(b"private-test-credential" not in path.read_bytes() for path in files)
```

`test_scratch_unlink_failure_is_reported_not_success` をパラメータ化する。`("tmp-fifo", ["spill.fifo"])` と `("tmp-hardlink", ["linked.json", "nested/shared.json", "original.json"])`。差し替える `os.unlink` は、`names` の各要素のファイル名（`Path(name).name`）のどれかが渡されたら `PermissionError` を出し、それ以外は元の `os.unlink` を呼ぶ。最後の assert は次にする:

```python
    scratch = attempt.request_path.parent / "dsh" / "tmp"
    assert sorted(attempt.sensitive_paths) == [scratch / name for name in names]
```

`test_real_pytest_scratch_is_accepted` の `leftovers` の条件に `or (path.is_file() and path.stat().st_nlink > 1)` を足す（symlink は前の条件で先に拾うので、`stat()` はリンクを辿らない）。

- [x] **Step 3: 修正の前に失敗することを確かめる**

Run: `uv run pytest tools/agent_runner/tests/adapters/dsh/test_runner.py -q -rfE -k 'hardlink or real_pytest_scratch or unlink_failure or scratch_links'`
Expected: `test_scratch_hardlinks_are_unlinked_and_the_rest_redacted` と `test_real_pytest_scratch_is_accepted[pytest-fixtures]` の 2 件が FAILED（state が `response_failed`）。`test_runtime_hardlinks_are_rejected_before_redaction_hides_the_link`・`test_scratch_unlink_failure_is_reported_not_success` の 2 件・`[pytest]`・`test_scratch_links_and_fifos_are_unlinked_not_followed` の 2 件は passed（基準でも成り立つ挙動）。ログは `task1-red.log`

- [x] **Step 4: runner を直す**（`runner.py`）

`_unlink_special_entries` を `_unlink_unredactable_entries(directory: int, owner: int, device: int) -> list[str]` に改名し、消す条件を `(not stat.S_ISREG(info.st_mode) or info.st_nlink > 1) and info.st_uid == owner and info.st_dev == device` にする（ローカル変数 `special` も合わせて改名）。docstring に、対象がリンク・特殊ファイル・ほかの名前を持つ通常ファイルであること、ほかの名前を持つファイルは 1 つの名前を redact しても元の内容が別の名前に残ること、を書く。一覧を閉じた後に消す箇所のコメントは「名前だけを消し、参照先や内容には触れない」の意味にする。`_prune_scratch` の呼び出しを新しい名前にし、docstring に、pytest の fixture のハードリンクも消すこと、先に別の名前が消えてリンク数 1 で残った名前はほかの通常ファイルと同じく redact されること、を足す。`run_workflow` の停止後のコメント（488〜492 行）の「links and special files」を「links, special files and hard links」にする。

- [x] **Step 5: テストが通ることを確かめる**

Run: Step 3 と同じコマンド（ログは `task1-green.log`）
Expected: 8 passed、FAILED なし

- [x] **Step 6: 説明を直す**

- `adapters/dsh.py` の module docstring の「links and special files tools leave in TMPDIR are unlinked」を「links, special files and hard links tools leave in TMPDIR are unlinked」にする（行の折り返しは 88 文字前後の今の幅に合わせる）
- `.devcontainer/README.md:596` の文の後に「TMPDIR に残ったシンボリックリンク・特殊ファイル・ハードリンク（pytest の fixture など）は消す。」を足す

- [x] **Step 7: DSH のテスト全体**

Run: `uv run pytest tools/agent_runner/tests/adapters/dsh -q -rfEs`（ログは `task1-dsh-dir.log`）
Expected: 285 passed（基準の 283 に、新しいテスト 1 件とパラメータ 1 件）、FAILED・SKIPPED なし

- [x] **Step 8: commit**

```bash
git add tools/agent_runner/runner.py tools/agent_runner/adapters/dsh.py .devcontainer/README.md \
  tools/agent_runner/tests/adapters/dsh/fake_cli.py tools/agent_runner/tests/adapters/dsh/test_runner.py
git commit -m "fix(agent_runner): unlink hard links left in the DSH TMPDIR after stop (#220)"
```

## Task 2: 統合確認

**テストの要否:** 確認だけで、コードを変えない（Step 2 の一時的な変更は使い捨ての worktree だけで行い、戻す）。

ログはどれも `/workspaces/reso-world/tmp/agents/issue-220.z5vcohqb/`（以下 `S`）に置く。`WT=/workspaces/reso-world/.worktrees/issue-220-dsh-tmp-hardlinks`、`DSH_DIR=tools/agent_runner/tests/adapters/dsh`。

- [x] **Step 1:** feature worktree で `git status --porcelain` が空。Task 1 の Step 7 の結果を使う（Task 1 の commit の後にコードを変えていないこと）
- [x] **Step 2: 対照検証。** `X="$(mktemp -d)"` に `git -C /workspaces/reso-world worktree add --detach "$X/wt" <Task 1 の SHA>` で使い捨ての worktree を作り、次の一時的な変更を 1 つずつ入れて、対象のテストを `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$X/wt" uv run --project "$WT" --locked python -m pytest -p no:cacheprovider <対象> -q -rfE`（cwd は `$X/wt`）で実行し、毎回 `git -C "$X/wt" checkout -- tools/agent_runner/runner.py` で戻して `status --porcelain` が空なことを確かめる
  - (a) 消し過ぎ: 判定の `info.st_nlink > 1` を `True` にする（tmp のすべての通常ファイルを消す）→ `test_real_pytest_scratch_is_accepted` の 2 件と `test_large_tmpdir_spill_is_kept_in_runtime_tree_and_redacted` が FAILED
  - (b) 範囲の拡大: `_prune_scratch` の最初の stack を `[(root, ["tmp", "state"])]` にする → 少なくとも `test_runtime_hardlinks_are_rejected_before_redaction_hides_the_link` が FAILED（`state/` の symlink・FIFO を扱う `test_unsafe_runtime_files_are_reported_not_followed` も落ちうる）
  - (c) redact のリンク数の検査を `tmp` で外す: `_redact_runtime_tree` の `info.st_nlink != 1` を `(info.st_nlink != 1 and not path.is_relative_to(root / "tmp"))` にする → `test_scratch_unlink_failure_is_reported_not_success[tmp-hardlink]` が FAILED
  - 最後に `git -C /workspaces/reso-world worktree remove "$X/wt"` と `rmdir "$X"`。ログは `control-<a|b|c>.log`
- [x] **Step 3: 実際のテストでの再現（基準と修正後）。** `git clone --quiet --shared --no-checkout "$WT" "$S/repro/repo"` で使い捨ての clone を作る。`$S/repro/agent.py`（偽の担当: cwd の attempt の worktree で `python -m pytest -q -p no:cacheprovider tools/agent_runner/tests/adapters/dsh/test_adapter.py::test_approval_classification_does_not_mutate_input_state tools/agent_runner/tests/adapters/dsh/test_review_evidence.py` を stdin なしで実行し、終了コードと要約を `DSH_HOME/repro-pytest.json` に書いてから、同じ worktree の `fake_cli.py` に `success` と受け取った引数で `os.execv` する）と、`$S/repro/verify.py`（`environ._literal` を `{"COMMANDCODE_API_KEY": "private-test-credential", "PATH": os.defpath}` にし、`test_runner.py` の `config` fixture と同じ形の DSH の担当 1 つ（command は `[sys.executable, agent.py]`、期限 600 秒）で `run_workflow` を実行して、attempt の state・exit_code・stop_confirmed・`sensitive_paths`（`dsh/` からの相対パス）・`dsh/tmp` に残るリンク数 2 以上の通常ファイル・`repro-pytest.json` を JSON で出す）を書く。clone を `4d41f1a` と Task 1 の SHA に順に `checkout --detach` し、それぞれ `env PYTHONPATH="$S/repro/repo" uv run --project "$WT" --locked python "$S/repro/verify.py" "$S/repro/repo" "$S/repro/run-<base|fix>" "$S/repro/agent.py"` を実行する
  - Expected: 基準は `response_failed`・`sensitive_paths` に `tmp/pytest-of-*/…/credentials`・`…/worktree/shared-hardlink`・`…/stdout.log` などの組が並ぶ。修正後は `success`・`sensitive_paths` が空・リンク数 2 以上の通常ファイルが残らない。どちらも `stop_confirmed: true`
  - 終わったら `$S/repro` を消す（`rm -rf -- "${S:?}/repro"`）。結果の JSON は `repro-base.json`・`repro-fix.json` として `S` に残す
- [x] **Step 4: ブランチ全体のレビュー**（新しいコンテキストのサブエージェント）を受け、致命的な指摘があれば直す（直したら Task 1 の Step 7 と Task 2 の Step 2・3 をやり直す）
- [x] **Step 5:** feature worktree で `git diff --stat origin/main` が、Spec・Plan・Task 1 の 5 ファイルだけであること
- [x] **Step 6:** Step 1〜5 の記録をこの Plan の「検証の記録」に書き、commit（これが最後の commit）
- [ ] **Step 7:** 最後の commit の上で `git status --porcelain` が空であることを確かめてから、README の「テスト」の入口（`bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`uv run pytest tests/skills .agents/skills .agents/scripts tools`）を順に実行する。失敗があれば、基準（`4d41f1a`）の同じ実行と比べ、この変更によるものでないことを確かめる。検証した HEAD・`git status --porcelain` が空だったこと・argv・終了コード・ログのパスと、`finalize.py` の `--checks-file` の形のファイルを `S` に作る（issue-to-pr の 5 章）。結果は Plan に書かず（HEAD が変わるので）、PR 本文に書く

## 検証の記録

ログはどれも `/workspaces/reso-world/tmp/agents/issue-220.z5vcohqb/` にある（commit しない）。SDD の ledger は同じディレクトリの `sdd/progress.md`。パラメータ化したテストの実際の ID は `test_scratch_unlink_failure_is_reported_not_success[tmp-fifo-names0]`・`[tmp-hardlink-names1]`（上の Task の本文の `[tmp-hardlink]` はこれを指す）。

### 修正の前（`4d41f1a`）

| 対象 | 結果 | ログ |
| --- | --- | --- |
| `tools/agent_runner/tests/adapters/dsh` 全体 | 283 passed・skip なし | `baseline-dsh-dir.log` |
| `test_runner.py` の `-k 'hardlinks_are_rejected or real_pytest_scratch or scratch_links_and_fifos or unlink_failure'` | 6 passed。TMPDIR のハードリンクで `response_failed` になる既存のテスト（Issue の挙動）を含む | `baseline-targeted.log` |

### Task 1（`0ad7746`）

| 手順 | 対象 | 結果 | ログ |
| --- | --- | --- | --- |
| Step 3（テストと偽の CLI だけを変えた状態） | Step 3 の 8 件 | 2 failed（`test_scratch_hardlinks_are_unlinked_and_the_rest_redacted`・`test_real_pytest_scratch_is_accepted[pytest-fixtures]`。どちらも `'response_failed' == 'success'` の assert）・6 passed | `task1-red.log` |
| Step 5 | 同じ 8 件 | 8 passed | `task1-green.log` |
| Step 7 | DSH のテスト全体 | 285 passed・skip なし | `task1-dsh-dir.log` |

### Task 2

- Step 1: feature worktree は clean で、Task 1 の commit の後にコードを変えていない
- Step 2（対照検証）: `0ad7746` の使い捨ての worktree `/tmp/issue-220-control.rTUGku/wt` で 1 つずつ一時的に変え、毎回戻して clean を確かめた。終わった後に `worktree remove` と `rmdir` で片付けた

  | 一時的な変更 | 落ちたテスト（すべて期待した assert） | ログ |
  | --- | --- | --- |
  | (a) 消し過ぎ（判定の `info.st_nlink > 1` を `True`） | `test_real_pytest_scratch_is_accepted[pytest]`・`[pytest-fixtures]`（`clean.txt` が消えた）、`test_large_tmpdir_spill_is_kept_in_runtime_tree_and_redacted`（spill が消えた） | `control-a.log` |
  | (b) 範囲の拡大（prune が `state` も辿る） | `test_runtime_hardlinks_are_rejected_before_redaction_hides_the_link`、`test_unsafe_runtime_files_are_reported_not_followed[symlink]`・`[fifo]`（どれも `success` になった） | `control-b.log` |
  | (c) redact のリンク数の検査を `tmp` で外す | `test_scratch_unlink_failure_is_reported_not_success[tmp-hardlink-names1]`（`success` になった）。`[tmp-fifo-names0]` は passed | `control-c.log` |

- Step 3（実際のテストでの再現）: `--shared` の使い捨ての clone を基準と修正後に切り替え、偽の担当（`repro-scripts/agent.py`）が attempt の worktree で `test_adapter.py::test_approval_classification_does_not_mutate_input_state` と `test_review_evidence.py` を実行してから `fake_cli.py` の `success` を exec する形で、`run_workflow`（`repro-scripts/verify.py`）を実行した。内側の pytest はどちらも 23 passed。clone と runner の出力は消し、結果の JSON だけを残した

  | 版 | state | exit・stop_confirmed・payload | `sensitive_paths` | リンク数 2 以上の通常ファイル | ログ |
  | --- | --- | --- | --- | --- | --- |
  | 基準 `4d41f1a` | `response_failed` | 0・true・dict | 10 件。Issue 本文と同じ `test_approval_classification_d{0..3}/credentials`・`…/worktree/shared-hardlink`、`test_unsafe_log_is_refused_wit3/source`・`stdout.log` | 同じ 10 件 | `repro-base.json` |
  | 修正後 `0ad7746` | `success` | 0・true・dict | なし | なし | `repro-fix.json` |

  修正後は、同じディレクトリの組（`source`・`stdout.log`）は両方消え、親子にまたがる組は親の `credentials` が消えて子の `worktree/shared-hardlink` がリンク数 1（中身は fixture の文字列）で残った（D-220-2 のとおり）
- Step 4（最終レビュー、opus、新しいコンテキスト）: マージしてよい。Critical・Important は無し
  - レビュアーは独立に、使い捨ての worktree（`/tmp/review-220.iUtVoD/wt`。終了時に外して消した）で DSH のテスト 285 passed、`tools/agent_runner` 全体 1058 passed、runner を使う skill のテスト 444 passed、修正前の `runner.py` での新しいテストの 2 failed・6 passed を確かめた。本物の `outer_command` の mount で、`dsh/tmp`（exports を含む）と worktree・`dsh/home`・`dsh/state`・`review-scratch` の間の `link(2)` が EXDEV になることも確かめた
  - Minor 4 件はどれも記述・表記の精度で、秘密の値が残る経路や誤った結果にはつながらないので見送った: (1) Spec の受け入れ条件 4 の「unlink に失敗したら報告する」は、unlink に失敗した名前が、同じ inode の別の名前が後で消えたことでリンク数 1 になった場合は redact されて `success` になることを含まない（その名前は redact されるので秘密の値は残らない。実際に unlink が失敗する原因（ディレクトリに書き込めない）では redact も失敗して報告される）、(2) README の「ハードリンクは消す」に、ディレクトリをまたぐ組で後に残る名前の補足が無い、(3) `runner.py` のコメント「never a target or the content」は、すべての名前が消えると内容も解放される点で不正確（意図は「開かない・書き換えない」）、(4) パラメータ化のテスト ID が Task の本文の表記とずれる（この節の冒頭に実際の ID を書いた）
  - 任意の推奨 2 件（`_prune_scratch` の docstring に EXDEV の前提を書く、1 つの名前だけの unlink の失敗のパラメータを足す）も見送った
  - 判断の対象外とした 10 件（exports の native write/edit の前提、exports と別ディレクトリの組の順序、`dsh/` の外の worktree・review-scratch、所有者・device の条件のテスト、overlayfs の `st_dev`、`st_nlink == 0` のファイルシステム、D-220-2 の別案、README の入口と Plan の記録が Step 6・7 であること、実際の DSH の担当での確認）は、どれもそのままにした（理由は ledger の `Final: Ruling:` の行）
- Step 5: `git diff --stat origin/main...HEAD`（`origin/main` は `4d41f1a` のまま）は、Spec・Plan と Task 1 の 5 ファイル（`runner.py`・`adapters/dsh.py`・`.devcontainer/README.md`・`fake_cli.py`・`test_runner.py`）の 7 ファイルだけ

### 所要時間（Step 6 の時点）

着手 2026-10-20 21:52Z ごろ、Step 6 は 22:41Z ごろ（約 49 分）。内訳: 入力・競合の確認と worktree 3 分、調査（コード・テスト・mount の確認）と基準の実行 7 分、Spec 4 分、Plan 5 分、Task 1 3 分、Task 2 の Step 2・3 4 分、最終レビューの待ち 22 分（その間に PR 修正ループの手順を確認）、Step 6 2 分
