# Issue #351 失敗レビューセッションの退役 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

- 状態: draft（issue-to-pr の run。実行許可は Spec の「管理・実行許可」。内容の承認ではない）
- Issue: https://github.com/usaturn/create-reso-world/issues/351（ボード #349 の子 `review-retire`）

**Goal:** 停止を確認できた失敗レビューセッションを、未保存の成果を失わずに helper で退役させ、定期掃除と repo-cleanup-after-merge をその helper 経由にする。

**Architecture:** `pr_review_workspace.py` に厳密な退役判定（`reap-check`）と、保存ロックの中で判定し直してから消す `cleanup --strict-reap` を足す。失敗の分類と停止の証拠は、`session.json` の `run_context` が指す実行記録から読む。定期掃除と repo-cleanup-after-merge は、自分で消さずにこの 2 つのコマンドを順に呼ぶ。

**Tech Stack:** Python 3.14（標準ライブラリだけ。helper は `python3` でも `uv run --no-project python` でも動く）、bash、git、pytest（`uv run pytest`）。

**Spec:** `docs/superpowers/specs/2026-11-09-issue-351-review-retire-design.md`

## Global Constraints

- 変更してよいファイルは Spec の「範囲と除外」の 6 つだけ。`install_beforehand.bash`・`zshrc.txt`・`test_review_run.py`・`review_run.py`・`review_run_record.py` を変えない
- `--strict-reap` の無い `cleanup`、`inspect`・`abandon`（`--discard-draft` を含む）・`sessions`・`fail --abandon` の挙動を変えない。`cleanup` の返り値にキーを足すのはよい
- 終了コード: 0 = 退役できる／退役した、1 = 退役しない（stdout に `status: "retained"` の JSON）、2 = 引数の誤り・状態を読めない（stderr に `error: ...`）
- 出力の JSON は 1 行、`ensure_ascii=False`・`sort_keys=True`（今の `main` と同じ）
- 許す ignored のキャッシュ名: `.venv`、`.uv-cache`、`.pytest_cache`、`.ruff_cache`、`__pycache__`、`node_modules`
- 定期掃除は `--operator-confirmed-stopped` を使わない。pr-review のディレクトリを自分で `rm -rf`・`git worktree remove` しない
- テストは AGENTS.md の「テストの採用基準」の S だけ。実 PR・実 runner・実 gh を使わない（`gh` は conftest が exit 97 の偽物にしている）

## Review Focus

1. 作成中（journal のロックが取られている）のセッション → 退役しない。Task 1 のテストで確かめる
2. 利用者が `git worktree lock` した worktree → 退役しない。Task 1 のテストで確かめる
3. 日本語の `--operator-confirmed-stopped` の理由 → そのまま `stop_evidence.reason` に入り、出力は壊れない。Task 2 のテストで確かめる
4. セッション直下の未知の項目（`.session.json.*` の書きかけなど） → 退役しない。Task 1 のテストで確かめる
5. `session.json` の無い `pr-review-*` ディレクトリと loose ファイル → 定期掃除が消さずに報告する。Task 3 のテストで確かめる

## 受け入れ基準

- **動作環境:** Dev Container（Ubuntu 26.04、system の `python3` 3.14、uv、git）。helper は `/tmp/pr-review-*` のセッションを、セッションを作った checkout の保存ロックの下で扱う。定期掃除はリポジトリの `.devcontainer/cleanup-workspace.bash` から実行したとき helper を見つける。`~/bin` のコピーからは helper が見つからず、すべて保持する
- **実入力:** セッションは `/tmp/pr-review-7-1a2b3c4d/` の形（`session.json`、`create-journal.jsonl`、`review-backup/<model>.md`・`<model>.findings.json`・`previous-review.md`、`worktree/`、owned-history なら `repo/`）。version 7（`main_root`・`pr_repository`）と version 8（`parent_root`・`target_root`・`target_kind` が `checkout` か `owned-history`・`pr_repo`）。実行記録は `reviews/<owner>/<repo>/#<PR>-<branch>/runs/<開始時刻>-<model>-<接尾辞>.json`（`#` を含むパス）。利用者の理由は日本語の自由記述（例: `ps で担当と子孫のプロセスが無いことを確認した`）
- **防御範囲:** 対象は helper が作った version 7・8 のセッションのうち、保存済みのものと、停止を確認できた未着手の失敗セッション。対象外（保持して理由を返す）: version 6 以前・状態の無いもの・読めないもの、作成中のもの、lock・prunable の worktree、worktree の無いもの、dirty・未追跡・キャッシュ以外の ignored・skip-worktree のある worktree、未知の項目、未保存の本文の draft、雛形から変わった候補、失敗セッションの `previous-review.md`、実行記録と結び付けられないもの、停止の証拠も利用者の理由も無いもの、runner が success で記録が打ち消していないもの。loose な `pr-review-*` ファイルと `review-fix-planning.*` は helper の対象外（前者は保護して報告、後者は今までどおり）

## 要件と Task の対応

| Spec の受け入れ | 担当 Task | 観測する結果 | 検証 |
| --- | --- | --- | --- |
| A1 保存済みの退役 | 1 | `reap-check` 0・`cleanup --strict-reap` 0 でセッションが消え、保存先が残る | Task 1 のテストと既存の cleanup のテスト |
| A2 停止確認済みの失敗の退役 | 2 | `--allow-failed` で 0、実行記録が残る | Task 2 のテスト |
| A3 停止未確認 | 2 | 1 と `stop_confirmation_needed: true`、理由ありで 0 | Task 2 のテスト |
| A4 成果のある失敗の保持 | 2 | 理由があっても 1、ファイルが残る | Task 2 のテスト |
| A5 ロックの中の再判定 | 1 | 判定の後に足したファイルが残る | Task 1 のテスト |
| A6 定期掃除 | 3 | 拒否されたものが残り、保存済みが消え、理由が出る | `test-cleanup-workspace.bash` |
| A7・A8 既存の挙動 | 1・2・4 | 既存のテストが通る | 検証の全体実行 |
| 手順の文書 | 4 | repo-cleanup の手順 5・ゲート A、noninteractive.md | 既存の repo-cleanup のテスト・`check-layout.sh`・差分の確認 |

共有する条件: helper の終了コードと JSON のキー（`status`・`retirement`・`stop_evidence`・`stop_confirmation_needed`・`reason`・`retained_paths`）を、Task 3 のスクリプトと Task 4 の手順が読む。統合担当は controller で、Task 3・4 のレビューと最後の全体レビューで、文書とスクリプトが Task 1・2 の実際の出力（テストの JSON）と一致することを照合する。

---

### Task 1: 保存済みセッションの厳密な退役（`reap-check` と `cleanup --strict-reap`）

テスト: 要（S。誤って消すとデータを失う。Review Focus 1・2・4 を含む）

**Files:**
- Modify: `.agents/skills/pr-review/scripts/pr_review_workspace.py`
- Test: `.agents/skills/pr-review/tests/test_pr_review_workspace.py`

**Interfaces:**
- Produces（Task 2・3・4 が使う）:
  - `class RetirementRefused(WorkspaceError)`: `__init__(self, message: str, *, retirement: str | None = None, stop_confirmation_needed: bool = False)`
  - `REGENERABLE_CACHE_DIRS: frozenset[str]`（Global Constraints の 6 つ）
  - `def retirement_options(args: argparse.Namespace, *, strict: bool) -> tuple[bool, str | None]`: `(allow_failed, operator_reason)`。`--allow-failed` が `strict` でない、`--operator-confirmed-stopped` が `--allow-failed` 無し・空白だけなら `WorkspaceError`（終了コード 2）。`reap-check` は `strict=True` で呼ぶ
  - `def validate_reapable_session(state_value: str, *, allow_failed: bool = False, operator_reason: str | None = None) -> tuple[Path, dict[str, Any], dict[str, Any]]`: `(lock_root, state, {"retirement": ..., "stop_evidence": ...})`。状態を読めなければ `WorkspaceError`、読めた後の拒否は `RetirementRefused`。Task 1 では常に `retirement: "saved"`、`stop_evidence: None`。Task 2 が失敗の分類と停止の証拠を足す（停止の確認は最後）
  - `def check_reap_candidate(args) -> dict[str, Any]`（`reap-check` の handler）: `{"status": "eligible", "retirement", "stop_evidence", "session_dir", "state_file", "worktree", "retained_paths": None}`
  - `cleanup(args)`: `strict_reap` が真なら、ロックの外と中で `validate_reapable_session` を呼んでから今の順で消し、`{"status": "retired", "retirement", "stop_evidence", "retained_paths": None, ...今のキー}` を返す。偽なら今の挙動のまま `retirement: "saved"`・`stop_evidence: None`・`retained_paths: None` を足す
  - `main`: `RetirementRefused` を `WorkspaceError` より先に捕まえ、stdout に `{"status": "retained", "reason", "retirement", "stop_confirmation_needed", "retained_paths": {"state_file", "session_dir", "worktree"}}` を出して 1 を返す（`session_dir` は `--state` の親、`worktree` はその下の `worktree`）
  - CLI: `reap-check --state [--allow-failed] [--operator-confirmed-stopped REASON]`、`cleanup` に `--strict-reap`・`--allow-failed`・`--operator-confirmed-stopped REASON`

検査の内容と順序は Spec の「分類」「共通の検査」「saved の条件」「退役の操作」のとおり。ロックの根は `load_state` が返す `repo`（version 7 は `main_root`、version 8 は `parent_root`）。journal があれば `finished_creator` と同じ非ブロッキングの flock で作成の終了を確かめ、`cleanup --strict-reap` は削除が終わるまで保持する。owned-history は `owned_attempt_repository(session_dir / "repo", session_dir)`。worktree の登録は `worktree_registration` で探し、`locked`・`prunable` があれば拒否する。ignored は `git ls-files --others --ignored --exclude-standard --directory` の各項目の最後の要素が `REGENERABLE_CACHE_DIRS` にあるものだけ許す。skip-worktree・assume-unchanged は `git ls-files -v` の小文字と `S` の印で見つける。submodule は `git submodule foreach --quiet --recursive` で status と ignored を確かめる。

- [ ] **Step 1: 失敗するテストを書く**（既存の `created_session` fixture と `saved_session` を使う。JSON は `capsys` で読む）

```python
def test_strict_reap_retires_a_saved_session(created_session, capsys):
    # saved_session の後
    assert workspace.main(["reap-check", "--state", state_file]) == 0
    checked = json.loads(capsys.readouterr().out)
    assert (checked["status"], checked["retirement"], checked["retained_paths"]) == ("eligible", "saved", None)
    assert workspace.main(["cleanup", "--strict-reap", "--state", state_file]) == 0
    retired = json.loads(capsys.readouterr().out)
    assert retired["status"] == "retired" and retired["stop_evidence"] is None
    assert not session_dir.exists() and worktree not in git(repo, "worktree", "list")
    assert Path(saved["destination"]).read_text(encoding="utf-8") == "review\n"

@pytest.mark.parametrize("kind", ["untracked", "ignored", "locked", "session-entry", "creator-running"])
def test_strict_reap_keeps_a_saved_session_it_cannot_account_for(created_session, capsys, kind):
    # untracked: worktree/notes.txt。ignored: main の .git/info/exclude に "*.log" と "__pycache__/" を書き、
    #   worktree/notes.log と worktree/__pycache__/a.pyc を作る。locked: git worktree lock --reason 利用者 <worktree>。
    #   session-entry: <session_dir>/.session.json.tmp。creator-running: create-journal.jsonl を fcntl.flock(LOCK_EX) で保持
    assert workspace.main(["reap-check", "--state", state_file]) == 1
    kept = json.loads(capsys.readouterr().out)
    assert kept["status"] == "retained" and kept["reason"]
    assert kept["retained_paths"]["session_dir"] == str(session_dir)
    assert workspace.main(["cleanup", "--strict-reap", "--state", state_file]) == 1
    assert session_dir.is_dir() and Path(worktree).is_dir()
    # ignored の場合だけ: notes.log を消すと __pycache__ だけになり reap-check が 0 になる（キャッシュは許す）

def test_strict_cleanup_rechecks_under_the_save_lock(created_session, monkeypatch, capsys):
    # saved_session の後、workspace.review_save_lock を包み、ロックを取った直後に review-backup/late.md を書く
    assert workspace.main(["cleanup", "--strict-reap", "--state", state_file]) == 1
    assert (session_dir / "review-backup" / "late.md").is_file()
```

- [ ] **Step 2: 失敗を確かめる**

Run: `uv run pytest .agents/skills/pr-review/tests/test_pr_review_workspace.py -k "strict" -q`
Expected: FAIL（`reap-check` が無い、`--strict-reap` を argparse が拒否する）

- [ ] **Step 3: Interfaces のとおりに実装する**

- [ ] **Step 4: 通ることと退行が無いことを確かめる**

Run: `uv run pytest .agents/skills/pr-review/tests -q` と `uv run python -m py_compile .agents/skills/pr-review/scripts/pr_review_workspace.py`（このリポジトリに ruff・mypy は入っていない）
Expected: すべて PASS

- [ ] **Step 5: Commit**

```bash
git add .agents/skills/pr-review/scripts/pr_review_workspace.py .agents/skills/pr-review/tests/test_pr_review_workspace.py
git commit -m "feat(pr-review): add strict reap-check and cleanup for saved sessions"
```

### Task 2: 停止確認済みの失敗セッションの退役（`--allow-failed`）

テスト: 要（S。停止していない試行の削除・成果の消失を防ぐ。Review Focus 3 を含む）

**Files:**
- Modify: `.agents/skills/pr-review/scripts/pr_review_workspace.py`
- Test: `.agents/skills/pr-review/tests/test_pr_review_workspace.py`

**Interfaces:**
- Consumes: Task 1 の `validate_reapable_session`・`RetirementRefused`・`main` の拒否出力
- Produces:
  - `def bound_run_record(parent: Path, state: Mapping[str, Any], session_dir: Path) -> dict[str, Any]`: Spec の「分類」3 の照合をして記録を返す。結び付けられなければ `RetirementRefused(retirement=None)`
  - `def failed_stop_evidence(document: Mapping[str, Any], reason: str | None) -> dict[str, Any]`: `{"source": "operator", "reason": reason}` か `{"source": "runner", "run_record_status", "state", "exit_code", "elapsed_seconds", "stop_confirmed": True}`。証拠が無ければ `RetirementRefused(retirement="failed", stop_confirmation_needed=True)`
  - `validate_reapable_session(..., allow_failed=True)` は `run_context` があり、saved の条件を満たさず（満たせば記録にかかわらず `saved`。Task 2 のレビューで Spec を変更）、記録が `success` 以外のとき `retirement: "failed"` の条件（Spec の「failed の条件」）で検査し、停止の証拠を最後に求める。runner が `success` で記録が `started` なら拒否する

テストの土台: `test_review_run.py` は変えずに、`importlib.util.spec_from_file_location` で別名のモジュールとして読み込み、`prepared` fixture をこのファイルの属性に代入して使う（`prepared = _REVIEW_RUN_TESTS.prepared`）。`_REVIEW_RUN_TESTS.review_run.prepare(prepared["args"])` でセッションを作り、`review_run.main(["fail", "--state", ..., "--reason", "止めた"])` で記録を `failed` にし、`_REVIEW_RUN_TESTS.batch_result(tmp_path / "result.json", state="timed_out")` と `review_run.main(["attach-runner", "--result", ...])` で `stop_confirmed: true` を結び付ける。`pyproject.toml` は `--import-mode=importlib` なので、通常の import はしない。

- [ ] **Step 1: 失敗するテストを書く**

```python
def test_allow_failed_retires_a_stopped_failed_session_and_keeps_its_run_record(prepared, tmp_path, capsys):
    # prepare → fail → attach-runner（timed_out, stop_confirmed）
    assert workspace.main(["reap-check", "--state", state_file]) == 1          # --allow-failed 無しでは保存済みでない
    assert workspace.main(["reap-check", "--allow-failed", "--state", state_file]) == 0
    checked = json.loads(capsys.readouterr().out)
    assert checked["retirement"] == "failed"
    assert checked["stop_evidence"]["source"] == "runner" and checked["stop_evidence"]["stop_confirmed"] is True
    assert workspace.main(["cleanup", "--strict-reap", "--allow-failed", "--state", state_file]) == 0
    assert not session_dir.exists() and Path(run_record).is_file()
    assert worktree not in git(source, "worktree", "list")

def test_failed_session_without_stop_evidence_needs_an_operator_reason(prepared, capsys):
    # prepare → fail（attach-runner しない）
    assert workspace.main(["cleanup", "--strict-reap", "--allow-failed", "--state", state_file]) == 1
    kept = json.loads(capsys.readouterr().out)
    assert kept["retirement"] == "failed" and kept["stop_confirmation_needed"] is True and session_dir.is_dir()
    reason = "ps で担当と子孫のプロセスが無いことを確認した"
    assert workspace.main(["cleanup", "--strict-reap", "--allow-failed",
                           "--operator-confirmed-stopped", reason, "--state", state_file]) == 0
    assert json.loads(capsys.readouterr().out)["stop_evidence"] == {"source": "operator", "reason": reason}

@pytest.mark.parametrize("work", ["draft", "candidates", "previous-review", "unknown"])
def test_allow_failed_keeps_a_failed_session_with_work(prepared, capsys, work):
    # draft: 本文の draft を書く。candidates: 候補の draft の coverage.read に 1 件足す。
    # previous-review: 先に _REVIEW_RUN_TESTS.completed_review(prepared) で保存してから 2 回目を prepare する。
    # unknown: review-backup/notes.txt を作る。どれも fail の後、利用者の理由を付けて実行する
    assert workspace.main(["cleanup", "--strict-reap", "--allow-failed",
                           "--operator-confirmed-stopped", "確認済み", "--state", state_file]) == 1
    kept = json.loads(capsys.readouterr().out)
    assert kept["stop_confirmation_needed"] is False and session_dir.is_dir()
```

- [ ] **Step 2: 失敗を確かめる**

Run: `uv run pytest .agents/skills/pr-review/tests/test_pr_review_workspace.py -k "failed" -q`
Expected: FAIL（`--allow-failed` で失敗セッションが `saved` の検査に落ちる）

- [ ] **Step 3: Interfaces のとおりに実装する**

- [ ] **Step 4: 通ることと退行が無いことを確かめる**

Run: `uv run pytest .agents/skills/pr-review/tests -q` と `uv run python -m py_compile .agents/skills/pr-review/scripts/pr_review_workspace.py`
Expected: すべて PASS

- [ ] **Step 5: Commit**

```bash
git add .agents/skills/pr-review/scripts/pr_review_workspace.py .agents/skills/pr-review/tests/test_pr_review_workspace.py
git commit -m "feat(pr-review): retire stopped failed review sessions with --allow-failed"
```

### Task 3: 定期掃除を helper 経由にする

テスト: 要（S。拒否されたセッションと loose ファイルを消さない。保存済みは退役させる＝何でも保持する実装を通さない）

**Files:**
- Modify: `.devcontainer/cleanup-workspace.bash`
- Test: `.devcontainer/test-cleanup-workspace.bash`

**Interfaces:**
- Consumes: Task 1・2 の CLI・終了コード・JSON
- Produces: 環境変数 `WORKSPACE_CLEANUP_PR_REVIEW_HELPER`（既定はスクリプトの実体の 1 つ上の `.agents/skills/pr-review/scripts/pr_review_workspace.py`）。報告の行は Spec の「2. 定期掃除」のとおり（`retired pr-review session: `、`keep (...): `、`dry-run: would retire pr-review session: `、`pr-review cleanup: retired=<数> kept=<数>`、`protected loose pr-review file (unverifiable provenance): `、`orphaned session file cleanup: protected=<数>`）

`cleanup_pr_review_dirs` を helper の 2 段の呼び出しに置き換える（symlink・使用中・年齢の除外は先に残す）。`REMOVED_PR_DIRS`・`_is_removed_pr_dir`・`_contains` と `cleanup_tmp_dirs` の記録用の引数を除き、`cleanup_tmp_dirs` は `review-fix-planning` だけに使う。helper が見つからなければ、各ディレクトリを `keep (pr-review helper unavailable: <path>)` で報告する。冒頭のコメントを新しい挙動に合わせる。

- [ ] **Step 1: 失敗するテストを書く**（`mktemp -d` の中だけを使う。`HOME` は一時ディレクトリ、`GIT_*` は `run-tests.bash` が除く）

1. 一時の main checkout を作り（`git init -b main`、`-c user.name=… -c user.email=…` で commit）、`python3 "$HELPER" create --repo "$R" --pr-repo usaturn/create-reso-world --pr-number 4 --commit "$SHA" --head-branch fix/x --model-name model-a --temp-root "$T" --attempt-id a1` で保存するセッション S1 を作り、draft を書いて `save --state` する。同じく `model-b`・`a2` で draft を書くだけの S2 を作る。`$T/pr-review-42-abandoned/`（`session.json` 無し）と loose ファイル `$T/pr-review-42-diff.patch` を作る
2. dry-run（`WORKSPACE_CLEANUP_DRY_RUN=1`、`MIN_AGE_DAYS=0`）: 出力に `dry-run: would retire pr-review session: <S1>` があり、何も消えていない
3. 実行（dry-run 無し）: S1 が無い。S2 とその draft、`pr-review-42-abandoned/`、loose ファイルが残る。出力に `keep` で始まる S2 の行、`pr-review-42-abandoned` の行、`protected loose pr-review file` の行がある
4. 今のテスト 2（既定値 `/tmp|1|0` の固定値。F∩S）はそのまま残す。今のテスト 1 は 2 に置き換える

- [ ] **Step 2: 失敗を確かめる**

Run: `bash .devcontainer/run-tests.bash .devcontainer/test-cleanup-workspace.bash`
Expected: FAIL（今のスクリプトが S2 と `pr-review-42-abandoned/` を消す）

- [ ] **Step 3: 実装する**

- [ ] **Step 4: 通ることを確かめる**

Run: `bash .devcontainer/run-tests.bash .devcontainer/test-cleanup-workspace.bash` と `bash -n .devcontainer/cleanup-workspace.bash`（`shellcheck` があれば `shellcheck .devcontainer/cleanup-workspace.bash .devcontainer/test-cleanup-workspace.bash`）
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add .devcontainer/cleanup-workspace.bash .devcontainer/test-cleanup-workspace.bash
git commit -m "fix(devcontainer): retire pr-review sessions only through the helper"
```

### Task 4: repo-cleanup-after-merge と noninteractive.md の手順

テスト: 不要（文書の手順。F に当たる。代わりに既存の repo-cleanup のテスト・`check-layout.sh`・差分の確認で、コマンドとキーが Task 1〜3 の実際の出力と一致することを確かめる）

**Files:**
- Modify: `.agents/skills/repo-cleanup-after-merge/SKILL.md`（`allowed-tools`、手順 5、手順 6 ゲート A、手順 11 の報告、Red Flags・ガードレールの該当行）
- Modify: `.agents/skills/pr-review/references/noninteractive.md`（「実行記録」の後）

**Interfaces:**
- Consumes: Task 1〜3 の CLI・終了コード・JSON のキー・定期掃除の挙動

内容は Spec の「3. repo-cleanup-after-merge」「4. noninteractive.md」のとおり。手順 5 のコマンドは今の `sessions` と同じくリポジトリのルートで `uv run --no-project python .agents/skills/pr-review/scripts/pr_review_workspace.py reap-check --allow-failed --state "$STATE_FILE"`、成功したら `... cleanup --strict-reap --allow-failed --state "$STATE_FILE"` と書く。`allowed-tools` に `Bash(uv run --no-project python *pr_review_workspace.py reap-check *)` と `Bash(uv run --no-project python *pr_review_workspace.py cleanup *)` を足す。version 7 の照合の規則、`sessions` の読み取り専用の報告、`--force` を付けない規則は変えない。手順 4・7〜10 と「通常ツールの対象照合」には触れない（#354 の範囲）。

- [ ] **Step 1: 手順を書き換える**
- [ ] **Step 2: 確かめる**

Run: `uv run pytest .agents/skills/repo-cleanup-after-merge/tests -q` と `bash scripts/check-layout.sh`、`git diff` で手順のキー（`status`・`retirement`・`stop_confirmation_needed`・`retained_paths`）と終了コードが Task 1〜3 と一致することを読む
Expected: PASS、食い違い無し

- [ ] **Step 3: Commit**

```bash
git add .agents/skills/repo-cleanup-after-merge/SKILL.md .agents/skills/pr-review/references/noninteractive.md
git commit -m "docs: retire pr-review sessions through the helper in repo cleanup"
```

## 検証（統合）

最後の commit の後に、`CODE_ROOT` で次を実行し、終了コードとログを `SESSION` に記録する。

1. `uv run pytest .agents/skills/pr-review/tests/test_pr_review_workspace.py`
2. `uv run pytest .agents/skills/pr-review/tests`
3. `bash .devcontainer/run-tests.bash .devcontainer/test-cleanup-workspace.bash`
4. `uv run pytest .agents/skills/repo-cleanup-after-merge/tests`
5. `bash scripts/check-layout.sh`
6. `uv run python -m py_compile .agents/skills/pr-review/scripts/pr_review_workspace.py` と `bash -n .devcontainer/cleanup-workspace.bash`
7. 手動（Issue の「検証」）: `mktemp -d` に偽の main checkout とセッションを作り、保存済み・失敗（停止確認済み）・停止未確認・未保存の draft の 4 つで `reap-check` と `cleanup --strict-reap --allow-failed` の結果を確かめる。`HOME` はワンショットの一時ディレクトリ、`GIT_*` は除く。消すときは `rm -rf -- "${VAR:?}"`

ボードの規則のとおり、`uv run pytest` の全体実行は並行する子の検証と重ねない。`run-tests.bash` は #351 の検証中にほかの子が実行しない（ボードの取り決め）。

## 実行方式

`implement_task.py check` の `self: false`（`--implement claude-code_sonnet_default`）なので、issue-to-pr の 4 章の「Task の実装を runner の担当に依頼する」で、Task 1→2→3→4 を 1 つずつ依頼する（同じファイルを続けて変えるので並行しない）。各 Task の後に controller が関連テストを実行して SDD の Task のレビューを行い、最後に全体のレビューを行う。作業領域は `SESSION/sdd/2026-11-09-issue-351-review-retire/`。

## 実行予算

- 全体: 能動時間 420 分（ledger `tmp/agents/issue-351.naa05k3c/budget.jsonl`、2026-11-08T16:45Z 開始。予約と Spec の 15 分は ledger の前）。根拠: 4 Task（helper の 2 Task が大きい）と、PR 修正ループの最大 3 サイクル
- phase の目安: Spec・Plan 60 分、実装 4 Task 計 150 分（1 Task 30〜50 分）、統合の検証・PR 30 分、ループ 1 サイクル 75 分（レビュー 45 分＋計画・修正 30 分）×最大 3
- worker: runner の `implement` の期限 90 分（runner の既定）。無進捗の打ち切りは runner に任せる
- 再試行の上限: 同じ失敗（signature）は 1 回まで。`retry`（BLOCKED・NEEDS_CONTEXT）・`rejected`（`outside_changes`）とも 1 回
- checkpoint: 各 Task の取り込み後、PR の作成後、ループの各サイクルの後、予算の 50%・100%、worker の失敗の直後
- 縮小・切り出し・方法変更の候補: (1) Task 2 の土台が組めなければ、失敗の判定のテストを Task 1 の version 7 の偽セッションに `run_context` と記録を手で書く形に変える。(2) 予算が足りなければ Task 4 の文書を最小（手順 5 の追記とゲート A の 1 段落）にする。(3) 定期掃除の helper の場所の問題は Spec の既知の制約のまま持ち越す

## contingency（代替策）

- runner の依頼が `rejected`（`outside_changes`）: 並行する #350 の runner・commit が原因のことがある。`tools.agent_runner.workspace.snapshot_checkouts` の指紋が 2 分変わらなくなってから 1 回だけ依頼し直す。また拒否されたら止まる
- runner の依頼が `failed`: その Task で止まり、self に切り替えない
- 最初の RED で前提（関数名・fixture・出力）が違うと分かった: 意味を保つ最小の修正を ledger に書いて続ける。終了コード・JSON のキー・保持の条件の意味が変わるなら止まって利用者の裁定を待つ
- `test_review_run.py` の fixture を読み込めない（`--import-mode=importlib` のせいなど）: 縮小の候補 (1) に切り替え、ledger に書く
- `python3` で helper が動かない: 定期掃除の Python を変えずに止まり、原因を報告する（ブートストラップの例外の判断は利用者に返す）
- push の前の検査（Gitleaks）の検出: AGENTS.md の条件で直せるものだけ直す

## 完了

（実行後に、Task ごとの依頼の回数・所要時間・検証の結果を書く）
