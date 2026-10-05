# Issue #39 pr-review の create 中断への対策 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** pr-review の helper の `create` に試行 ID と進捗の記録（journal と creator のロック）を加え、中断した試行を `inspect` で調べて `abandon` で安全に片付けられるようにし、スキルに短いタイムアウトで helper を打ち切らない規約と中断後の手順を書いて、`main` 向けの PR（`Closes #39`）を作る。

**Architecture:** 変更は `pr_review_workspace.py` の 1 ファイルに閉じる。`create` はセッションディレクトリ直後に `create-journal.jsonl` を作って flock を持ち続け、工程ごとに 1 行ずつ追記する。`inspect` は試行 ID で journal を探して状態を返し、`abandon` は共有ロックと creator のロックを取ったうえで、自分の試行の worktree とセッションディレクトリだけを消す。スキル（`SKILL.md`・`references/time-budget.md`）は手順と規約だけを変える。

**Tech Stack:** Python 3（標準ライブラリのみ。`fcntl`・`signal`・`subprocess`）、pytest（`uv run pytest`）、Git 2.55、Markdown

**Spec:** `docs/superpowers/specs/2026-10-05-issue-39-pr-review-create-interruption-design.md`

- 状態: draft（利用者の 2026-10-05 の指示「途中で止めずに推奨案で Spec、Plan を作成し PR まで実施せよ」による実行許可。Plan 自体の明示承認は得ていない）
- 作業場所: worktree `/workspaces/reso-world/.worktrees/issue-39-create-interruption`、ブランチ `fix/issue-39-pr-review-create-interruption`（`origin/main` の `a6e2c41` から作成）
- 実行方式: 利用者の指示どおり止まらずに進めるため、このセッションで executing-plans により実装する（サブエージェントは起動しない）

## Global Constraints

- 編集するのは `.agents/skills/pr-review/scripts/pr_review_workspace.py`、`.agents/skills/pr-review/tests/test_pr_review_workspace.py`、`.agents/skills/pr-review/SKILL.md`、`.agents/skills/pr-review/references/time-budget.md` と、この Plan・Spec だけ
- Python は `uv run` で実行する（`python3` を直接使わない）。テストは worktree のルートで `uv run pytest <パス> -q`
- 試行 ID の形式: 正規表現 `[A-Za-z0-9][A-Za-z0-9._-]{0,63}`。スキルでの生成は `ATTEMPT_ID=$(date -u +%Y%m%dT%H%M%S%NZ)`
- journal のファイル名は `create-journal.jsonl`。phase は `started`・`worktree-add`・`worktree-verify`・`lock-wait`・`state-write`・`completed`・`failed`・`interrupted` の 8 種で、この順に記録する
- `inspect` の `status` は `absent`・`running`・`completed`・`failed`・`interrupted`・`vanished` の 6 種
- `create` がシグナルで中断したときの終了コードは 128＋シグナル番号（SIGTERM なら 143）。helper のエラーは従来どおり 2
- タイムアウトの規約は「指定しないか 600 秒以上」。待機は `inspect --wait 540`。再試行は調査期限まで 10 分以上残っているときの 1 回だけ
- `SKILL.md` の `"$HELPER" create` を含む行は 2 行のまま、両方に `--temp-root /tmp` と `--attempt-id "$ATTEMPT_ID"` を付ける（`test_skill_keeps_claude_code_permissions_consistent`）。文「削除は helper の `cleanup` だけが行う」は残す（`assert_cleanup_contract`）
- 文書の文言を固定値で比べるテストは新しく書かない
- 一時ファイルは scratchpad に置く。削除コマンドの対象にシェル変数を使うときは `${VAR:?}` で空値を防ぎ、パス全体を引用する

## Review Focus

1. `create` の Python だけが強制終了され、`git worktree add` の子（checkout）が生き残る: `inspect` は `running` を返し、`abandon` は何も消さない。子が終わると `vanished` になる（Task 3 の `test_abandon_waits_for_a_checkout_that_outlives_create`）
2. この変更より前に残ったセッション（journal が無い）: `inspect` は `absent` を返し、そのセッションに触れない（Task 2 の `test_inspect_reports_an_unknown_attempt_as_absent`）
3. 書き込みの途中で切れた journal の末尾行: `inspect` は最後の完全な行までを読み、エラーにしない（Task 2 の `test_inspect_ignores_a_cut_off_journal_line`）
4. `abandon` を 2 回続けて実行する: 2 回目は「片付ける試行が無い」で終わり、他のものを消さない（Task 3 の `test_abandon_clears_an_attempt_killed_while_waiting_for_the_lock`）
5. 他のセッションが共有ロックを持っている間の `abandon`: ロックが外れるまで待ってから片付ける（Task 3 の `test_abandon_waits_for_the_repository_review_lock`）

---

### Task 1: `create` の試行 ID・journal・中断の記録と、セッション内ファイルの fsync の削除

**Files:**
- Modify: `.agents/skills/pr-review/scripts/pr_review_workspace.py`（import、定数、`git`、`snapshot_existing_review`、`write_json`、`create`、`main`、`parser`）
- Test: `.agents/skills/pr-review/tests/test_pr_review_workspace.py`

**Interfaces:**
- Produces: `validate_attempt_id(value: str) -> str`、`JOURNAL_NAME = "create-journal.jsonl"`、`TERMINAL_PHASES`、`CreateInterrupted(BaseException)`（属性 `signum: int`）、`CreateJournal`（`record(phase, **fields)`・`fileno()`・`close()`）、`journal_attempt(path: Path) -> str | None`、`read_journal(path: Path) -> list[dict[str, Any]]`、`attempt_sessions(temp_root: Path, pr_number: int, attempt_id: str) -> list[Path]`、`git(repo, *args, binary=False, pass_fds=())`、`create(args)` は `args.attempt_id` を必須とする

- [ ] **Step 1: 既存テストの `create` 呼び出しに試行 ID を足す**

`test_pr_review_workspace.py` の import に `contextlib`・`fcntl`・`shutil`・`signal`・`time`・`uuid` を足し、`THREAD_ID` の下に次を置く。

```python
def attempt_id() -> str:
    return uuid.uuid4().hex
```

`workspace.create(argparse.Namespace(...))` を呼ぶ全 10 箇所（`test_create_requires_explicit_model_outside_codex`、`test_create_pins_slash_model_name_as_hyphenated_filename`、`test_create_destination_uses_hash_pr_number_and_sanitized_branch`、`test_create_destination_replaces_unsafe_directory_characters`、`test_create_pins_explicit_model_outside_codex`、`test_save_uses_pinned_explicit_model_without_codex_metadata`、`test_create_pins_model_and_artifact_paths`、`test_create_pins_existing_review_snapshot`、`create_session`、`test_first_session_wins_same_destination`）の Namespace に `attempt_id=attempt_id(),` を足す。`test_create_parser_accepts_explicit_model_name` の引数リストに `"--attempt-id", "20261005T121530123456789Z",` を足す。

- [ ] **Step 2: 新しいテストを書く**

ファイル末尾に次を足す。

```python
def explicit_create_args(
    repo: Path,
    commit: str,
    temp_root: Path,
    attempt: str,
    *,
    model_name: str = "opus-5",
) -> argparse.Namespace:
    return argparse.Namespace(
        repo=str(repo),
        pr_number=4,
        commit=commit,
        head_branch="fix/herdr-session-cwd",
        model_name=model_name,
        temp_root=str(temp_root),
        attempt_id=attempt,
    )


def journal_records(session_dir: Path) -> list[dict[str, Any]]:
    lines = (session_dir / "create-journal.jsonl").read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines]


def test_create_parser_requires_attempt_id() -> None:
    with pytest.raises(SystemExit):
        workspace.parser().parse_args(
            [
                "create",
                "--repo",
                "/repo",
                "--pr-number",
                "5",
                "--commit",
                "deadbeef",
                "--head-branch",
                "fix/model-name",
                "--model-name",
                "opus-5",
            ]
        )


@pytest.mark.parametrize("bad", ["", "-leading-dash", "../escape", "has space", "x" * 65])
def test_create_rejects_unsafe_attempt_id(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, bad: str) -> None:
    monkeypatch.delenv("CODEX_THREAD_ID", raising=False)
    repo = tmp_path / "repo"
    commit = make_repo(repo)
    temp_root = tmp_path / "sessions"

    with pytest.raises(workspace.WorkspaceError, match="attempt id"):
        workspace.create(explicit_create_args(repo, commit, temp_root, bad))

    assert not temp_root.exists()


def test_create_rejects_reused_attempt_id(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CODEX_THREAD_ID", raising=False)
    repo = tmp_path / "repo"
    commit = make_repo(repo)
    temp_root = tmp_path / "sessions"
    attempt = attempt_id()
    workspace.create(explicit_create_args(repo, commit, temp_root, attempt))
    worktrees = git(repo, "worktree", "list")

    with pytest.raises(workspace.WorkspaceError, match="already used"):
        workspace.create(explicit_create_args(repo, commit, temp_root, attempt))

    assert len(list(temp_root.iterdir())) == 1
    assert git(repo, "worktree", "list") == worktrees


def test_create_records_its_phases_in_the_journal(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CODEX_THREAD_ID", raising=False)
    repo = tmp_path / "repo"
    commit = make_repo(repo)
    attempt = attempt_id()

    result = workspace.create(explicit_create_args(repo, commit, tmp_path / "sessions", attempt))

    session_dir = Path(result["state_file"]).parent
    records = journal_records(session_dir)
    assert [record["phase"] for record in records] == [
        "started",
        "worktree-add",
        "worktree-verify",
        "lock-wait",
        "state-write",
        "completed",
    ]
    assert all(record["at"].endswith("Z") for record in records)
    header = records[0]
    assert header["attempt_id"] == attempt
    assert header["pid"] == os.getpid()
    assert header["pr_number"] == 4
    assert header["commit"] == commit
    assert header["main_root"] == str(repo.resolve())
    assert header["session_dir"] == str(session_dir)
    assert header["worktree"] == result["worktree"]
    assert records[-1]["state_file"] == result["state_file"]


def test_create_does_not_fsync_session_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # fsync here held the shared review lock for minutes behind concurrent checkouts (Issue #39).
    monkeypatch.delenv("CODEX_THREAD_ID", raising=False)
    repo = tmp_path / "repo"
    commit = make_repo(repo)

    def refuse_fsync(fd: int) -> None:
        raise AssertionError("create must not fsync while holding the shared review lock")

    monkeypatch.setattr(workspace.os, "fsync", refuse_fsync)

    result = workspace.create(explicit_create_args(repo, commit, tmp_path / "sessions", attempt_id(), model_name="gpt-5"))

    assert result["previous_review"] is not None
    assert Path(result["state_file"]).is_file()
```

- [ ] **Step 3: テストが失敗することを確かめる**

Run: `uv run pytest .agents/skills/pr-review/tests/test_pr_review_workspace.py -q -k "attempt_id or journal or fsync or parser"`
Expected: FAIL（`--attempt-id` が未定義、journal が無い、fsync が呼ばれる）

- [ ] **Step 4: helper を実装する**

import に `signal`・`threading`・`time` と `from datetime import UTC, datetime` を足す。`MODEL_SOURCES` の下に定数を置く。

```python
ATTEMPT_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")
JOURNAL_NAME = "create-journal.jsonl"
TERMINAL_PHASES = ("completed", "failed", "interrupted")
# Tool timeouts and closing terminals send these before any SIGKILL.
INTERRUPT_SIGNALS = (signal.SIGTERM, signal.SIGHUP)
```

`WorkspaceError` の下に例外を置く。

```python
class CreateInterrupted(BaseException):
    """Stop create on a termination signal so its journal records how it ended."""

    def __init__(self, signum: int) -> None:
        super().__init__(f"create interrupted by {signal.Signals(signum).name}")
        self.signum = signum
```

`git` に `pass_fds` を足す。

```python
def git(repo: Path, *args: str, binary: bool = False, pass_fds: tuple[int, ...] = ()) -> str | bytes:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        capture_output=True,
        pass_fds=pass_fds,
    )
```

`snapshot_existing_review` の `os.fsync(output.fileno())` の行を消し、`output.flush()` の前に次のコメントを置く。

```python
            # Session files need no fsync: os.replace publishes all or nothing,
            # and after an OS crash the review session cannot continue anyway.
```

`write_json` を次にする。

```python
def write_json(path: Path, value: dict[str, Any]) -> None:
    # No fsync: the state lives only as long as the review session, and an
    # fsync under the shared review lock waited minutes on concurrent
    # checkouts (Issue #39). os.replace still publishes all or nothing.
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, sort_keys=True)
            stream.write("\n")
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise
```

`write_json` の下に journal 関係を置く。

```python
def validate_attempt_id(value: str) -> str:
    if ATTEMPT_ID.fullmatch(value) is None:
        raise WorkspaceError("attempt id must be 1-64 letters, digits, '.', '_' or '-', starting with a letter or digit")
    return value


def utc_timestamp() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


class CreateJournal:
    """Append create's phases and hold the creator lock until create ends."""

    def __init__(self, session_dir: Path, attempt_id: str) -> None:
        self.attempt_id = attempt_id
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_APPEND | getattr(os, "O_NOFOLLOW", 0)
        self.stream = os.fdopen(os.open(session_dir / JOURNAL_NAME, flags, 0o600), "a", encoding="utf-8")
        # The kernel drops this lock when every holder exits, so inspect and
        # abandon can tell a finished attempt without trusting a PID.
        fcntl.flock(self.stream.fileno(), fcntl.LOCK_EX)

    def fileno(self) -> int:
        return self.stream.fileno()

    def record(self, phase: str, **fields: object) -> None:
        at = utc_timestamp()
        self.stream.write(json.dumps({"phase": phase, "at": at, **fields}, ensure_ascii=False, sort_keys=True) + "\n")
        self.stream.flush()
        detail = f" session_dir={fields['session_dir']}" if "session_dir" in fields else ""
        print(f"pr-review create {self.attempt_id}: {at} {phase}{detail}", file=sys.stderr, flush=True)

    def record_end(self, phase: str, **fields: object) -> None:
        # Never mask the error that ended create; a missing end reads as vanished.
        try:
            self.record(phase, **fields)
        except (OSError, ValueError):
            pass

    def close(self) -> None:
        self.stream.close()


@contextmanager
def interruption_signals() -> Generator[None]:
    if threading.current_thread() is not threading.main_thread():
        yield
        return

    def interrupt(signum: int, _frame: object) -> None:
        raise CreateInterrupted(signum)

    previous = {signum: signal.signal(signum, interrupt) for signum in INTERRUPT_SIGNALS}
    try:
        yield
    finally:
        for signum, handler in previous.items():
            signal.signal(signum, handler)


def journal_attempt(path: Path) -> str | None:
    """Return the attempt id in a journal's start record, or None if unreadable."""
    if path.is_symlink() or not path.is_file():
        return None
    try:
        with path.open(encoding="utf-8") as stream:
            first = stream.readline()
        header = json.loads(first) if first.endswith("\n") else None
    except (OSError, ValueError):
        return None
    if not isinstance(header, dict) or header.get("phase") != "started":
        return None
    value = header.get("attempt_id")
    return value if isinstance(value, str) else None


def read_journal(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            if not line.endswith("\n"):
                break  # cut off by a kill while appending
            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                raise WorkspaceError(f"create journal is unreadable: {path}") from error
            if not isinstance(record, dict) or not isinstance(record.get("phase"), str):
                raise WorkspaceError(f"create journal is unreadable: {path}")
            records.append(cast(dict[str, Any], record))
    if not records or records[0]["phase"] != "started":
        raise WorkspaceError(f"create journal has no start record: {path}")
    return records


def attempt_sessions(temp_root: Path, pr_number: int, attempt_id: str) -> list[Path]:
    return [
        session_dir
        for session_dir in sorted(temp_root.glob(f"pr-review-{pr_number}-*"))
        if not session_dir.is_symlink()
        and session_dir.is_dir()
        and journal_attempt(session_dir / JOURNAL_NAME) == attempt_id
    ]
```

`create` を次の 2 関数に分ける。

```python
def create(args: argparse.Namespace) -> dict[str, str | None]:
    attempt_id = validate_attempt_id(args.attempt_id)
    model = resolve_runtime_model_name(args.model_name)
    review_directory_name(args.pr_number, args.head_branch)
    repo = require_main_checkout(args.repo)
    commit = str(git(repo, "rev-parse", "--verify", f"{args.commit}^{{commit}}"))
    temp_root = Path(args.temp_root).resolve() if args.temp_root else Path(tempfile.gettempdir()).resolve()
    temp_root.mkdir(parents=True, exist_ok=True)
    if attempt_sessions(temp_root, args.pr_number, attempt_id):
        raise WorkspaceError(f"attempt id {attempt_id} is already used for PR {args.pr_number}; generate a new one")
    session_dir = Path(tempfile.mkdtemp(prefix=f"pr-review-{args.pr_number}-", dir=temp_root))
    journal = CreateJournal(session_dir, attempt_id)
    try:
        journal.record(
            "started",
            attempt_id=attempt_id,
            pid=os.getpid(),
            pr_number=args.pr_number,
            commit=commit,
            head_branch=args.head_branch,
            model_name=model[0],
            main_root=str(repo),
            session_dir=str(session_dir),
            worktree=str(session_dir / "worktree"),
        )
        with interruption_signals():
            try:
                result = create_session(args, repo, commit, model, session_dir, journal)
            except CreateInterrupted as error:
                journal.record_end("interrupted", signal=signal.Signals(error.signum).name)
                raise
            except KeyboardInterrupt:
                journal.record_end("interrupted", signal="SIGINT")
                raise
            except BaseException as error:
                journal.record_end("failed", error=str(error) or type(error).__name__)
                raise
            journal.record("completed", state_file=result["state_file"])
            return result
    finally:
        journal.close()


def create_session(
    args: argparse.Namespace,
    repo: Path,
    commit: str,
    model: tuple[str, str],
    session_dir: Path,
    journal: CreateJournal,
) -> dict[str, str | None]:
    model_name, model_source = model
    worktree = session_dir / "worktree"
    backup_dir = session_dir / "review-backup"
    backup_dir.mkdir()
    draft, destination = review_artifact_paths(
        backup_dir,
        args.head_branch,
        model_name,
        pr_number=args.pr_number,
    )
    destination_path = safe_destination(repo, destination)
    require_destination_parent(destination_path)

    before = snapshot(repo)
    journal.record("worktree-add")
    # A checkout that outlives this process keeps the creator lock held.
    git(repo, "worktree", "add", "--detach", str(worktree), commit, pass_fds=(journal.fileno(),))

    journal.record("worktree-verify")
    actual_top = Path(str(git(worktree, "rev-parse", "--show-toplevel"))).resolve(strict=True)
    if actual_top != worktree.resolve(strict=True):
        raise WorkspaceError("created worktree root does not match the requested unique path")
    if git_path(worktree, "--git-dir") == git_path(worktree, "--git-common-dir"):
        raise WorkspaceError("created review directory is not a linked worktree")
    if git(worktree, "branch", "--show-current"):
        raise WorkspaceError("created review worktree is not detached")
    if git(worktree, "rev-parse", "HEAD") != commit:
        raise WorkspaceError("created review worktree does not point at the requested commit")
    if snapshot(repo) != before:
        raise WorkspaceError("creating the review worktree changed the main working tree")

    state_file = session_dir / "session.json"
    journal.record("lock-wait")
    with review_save_lock(repo):
        journal.record("state-write")
        fingerprint, previous = snapshot_existing_review(destination_path, backup_dir)
        state: dict[str, Any] = {
            "version": 6,
            "main_root": str(repo),
            "worktree": str(worktree.resolve(strict=True)),
            "backup_dir": str(backup_dir.resolve(strict=True)),
            "commit": commit,
            "head_branch": args.head_branch,
            "pr_number": args.pr_number,
            "model_name": model_name,
            "model_source": model_source,
            "draft": str(draft.resolve(strict=False)),
            "previous_review": (str(previous.resolve(strict=True)) if previous is not None else None),
            "destination": destination,
            "destination_fingerprint": fingerprint,
        }
        write_json(state_file, state)
    return {
        "backup_dir": state["backup_dir"],
        "destination": state["destination"],
        "draft": state["draft"],
        "model_name": state["model_name"],
        "model_source": state["model_source"],
        "previous_review": state["previous_review"],
        "state_file": str(state_file.resolve(strict=True)),
        "worktree": state["worktree"],
    }
```

`state` と返却値は既存の `create` と同じ内容で、session の state の形式（version 6）は変えない。

`main` で中断を終了コードに変える。

```python
def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        result = args.handler(args)
    except CreateInterrupted as error:
        print(f"error: {error}", file=sys.stderr)
        return 128 + error.signum
    except KeyboardInterrupt:
        print("error: interrupted by SIGINT", file=sys.stderr)
        return 128 + signal.SIGINT
    except (WorkspaceError, OSError, ValueError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0
```

`parser` の `create_parser` に `create_parser.add_argument("--attempt-id", required=True)` を足す。

- [ ] **Step 5: テストが通ることを確かめる**

Run: `uv run pytest .agents/skills/pr-review/tests/test_pr_review_workspace.py -q`
Expected: PASS（既存のテストを含めて全件）

- [ ] **Step 6: コミット**

```bash
git add .agents/skills/pr-review/scripts/pr_review_workspace.py .agents/skills/pr-review/tests/test_pr_review_workspace.py
git commit -m "feat(pr-review): create に試行 ID と進捗の記録を加え、セッション内の fsync をやめる"
```

### Task 2: `inspect` サブコマンド

**Files:**
- Modify: `.agents/skills/pr-review/scripts/pr_review_workspace.py`（`inspect_attempt` と補助関数、`parser`）
- Test: `.agents/skills/pr-review/tests/test_pr_review_workspace.py`

**Interfaces:**
- Consumes: Task 1 の `JOURNAL_NAME`・`TERMINAL_PHASES`・`validate_attempt_id`・`read_journal`・`attempt_sessions`
- Produces: `inspect_attempt(args) -> dict[str, Any]`（args は `repo`・`pr_number`・`attempt_id`・`temp_root`・`wait`）、`locate_attempt(repo: Path, temp_root_value: str | None, pr_number: int, attempt_id: str) -> Path | None`、`creator_running(journal: Path) -> bool`、`attempt_report(repo: Path, session_dir: Path, attempt_id: str, *, running: bool) -> dict[str, Any]`、`worktree_registration(repo: Path, worktree: Path) -> dict[str, str] | None`

- [ ] **Step 1: テストを書く**

```python
def attempt_args(repo: Path, temp_root: Path, attempt: str, *, wait: int = 0) -> argparse.Namespace:
    return argparse.Namespace(repo=str(repo), pr_number=4, attempt_id=attempt, temp_root=str(temp_root), wait=wait)


def stalling_git_env(tmp_path: Path) -> dict[str, str]:
    """Run git normally, but keep `git worktree add` alive after it finishes."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    real_git = shutil.which("git")
    assert real_git is not None
    wrapper = bin_dir / "git"
    wrapper.write_text(
        f'#!/bin/sh\n"{real_git}" "$@" || exit $?\ncase " $* " in *" worktree add "*) exec sleep 60 ;; esac\n',
        encoding="utf-8",
    )
    wrapper.chmod(0o755)
    env = os.environ.copy()
    env.pop("CODEX_THREAD_ID", None)
    env["PATH"] = f"{bin_dir}{os.pathsep}{env['PATH']}"
    return env


def start_create(env: dict[str, str], repo: Path, commit: str, temp_root: Path, attempt: str) -> subprocess.Popen[str]:
    return subprocess.Popen(
        [
            sys.executable,
            str(SCRIPT),
            "create",
            "--repo",
            str(repo),
            "--pr-number",
            "4",
            "--commit",
            commit,
            "--head-branch",
            "fix/herdr-session-cwd",
            "--model-name",
            "opus-5",
            "--temp-root",
            str(temp_root),
            "--attempt-id",
            attempt,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
        start_new_session=True,
    )


def kill_group(pid: int, signum: int) -> None:
    with contextlib.suppress(ProcessLookupError):
        os.killpg(pid, signum)


def wait_for_phase(repo: Path, temp_root: Path, attempt: str, phase: str) -> dict[str, Any]:
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        report = workspace.inspect_attempt(attempt_args(repo, temp_root, attempt))
        if report.get("last_phase") == phase:
            return report
        time.sleep(0.05)
    raise AssertionError(f"create never reached {phase}")


def test_inspect_reports_a_completed_attempt(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CODEX_THREAD_ID", raising=False)
    repo = tmp_path / "repo"
    commit = make_repo(repo)
    temp_root = tmp_path / "sessions"
    attempt = attempt_id()
    result = workspace.create(explicit_create_args(repo, commit, temp_root, attempt))

    report = workspace.inspect_attempt(attempt_args(repo, temp_root, attempt))

    assert report["status"] == "completed"
    assert report["session_dir"] == str(Path(result["state_file"]).parent)
    assert report["state_file"] == result["state_file"]
    assert report["worktree"] == result["worktree"]
    assert report["worktree_exists"] is True
    assert report["worktree_registered"] is True
    assert report["worktree_lock"] is None
    assert report["last_phase"] == "completed"
    assert {"create-journal.jsonl", "session.json", "worktree/", "review-backup/"} <= set(report["entries"])


def test_killed_create_reports_its_last_phase_and_leftovers(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    commit = make_repo(repo)
    temp_root = tmp_path / "sessions"
    attempt = attempt_id()
    process = start_create(stalling_git_env(tmp_path), repo, commit, temp_root, attempt)
    try:
        running = wait_for_phase(repo, temp_root, attempt, "worktree-add")
    finally:
        kill_group(process.pid, signal.SIGKILL)
        _, stderr = process.communicate(timeout=10)

    report = workspace.inspect_attempt(attempt_args(repo, temp_root, attempt, wait=10))

    assert running["status"] == "running"
    assert process.returncode == -signal.SIGKILL
    assert report["status"] == "vanished"
    assert report["last_phase"] == "worktree-add"
    assert report["state_file"] is None
    assert report["worktree_exists"] is True
    assert report["worktree_registered"] is True
    assert f"session_dir={report['session_dir']}" in stderr
    assert "worktree-add" in stderr


def test_terminated_create_records_the_signal(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    commit = make_repo(repo)
    temp_root = tmp_path / "sessions"
    attempt = attempt_id()
    process = start_create(stalling_git_env(tmp_path), repo, commit, temp_root, attempt)
    try:
        wait_for_phase(repo, temp_root, attempt, "worktree-add")
    finally:
        kill_group(process.pid, signal.SIGTERM)
        process.communicate(timeout=10)

    report = workspace.inspect_attempt(attempt_args(repo, temp_root, attempt, wait=10))

    assert process.returncode == 128 + signal.SIGTERM
    assert report["status"] == "interrupted"
    assert report["signal"] == "SIGTERM"
    assert report["last_phase"] == "interrupted"


def test_inspect_reports_an_unknown_attempt_as_absent(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    make_repo(repo)
    temp_root = tmp_path / "sessions"
    legacy = temp_root / "pr-review-4-legacy"
    legacy.mkdir(parents=True)
    (legacy / ".session.json.kqdd8rsc").write_text("{}\n", encoding="utf-8")

    report = workspace.inspect_attempt(attempt_args(repo, temp_root, attempt_id()))

    assert report == {"attempt_id": report["attempt_id"], "status": "absent", "session_dir": None}
    assert (legacy / ".session.json.kqdd8rsc").is_file()


def test_inspect_ignores_a_cut_off_journal_line(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CODEX_THREAD_ID", raising=False)
    repo = tmp_path / "repo"
    commit = make_repo(repo)
    temp_root = tmp_path / "sessions"
    attempt = attempt_id()
    result = workspace.create(explicit_create_args(repo, commit, temp_root, attempt))
    with (Path(result["state_file"]).parent / "create-journal.jsonl").open("a", encoding="utf-8") as stream:
        stream.write('{"phase": "fail')

    report = workspace.inspect_attempt(attempt_args(repo, temp_root, attempt))

    assert report["status"] == "completed"
    assert report["last_phase"] == "completed"


def test_inspect_refuses_an_attempt_id_shared_by_two_sessions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("CODEX_THREAD_ID", raising=False)
    repo = tmp_path / "repo"
    commit = make_repo(repo)
    temp_root = tmp_path / "sessions"
    attempt = attempt_id()
    result = workspace.create(explicit_create_args(repo, commit, temp_root, attempt))
    duplicate = temp_root / "pr-review-4-duplicate"
    duplicate.mkdir()
    shutil.copy(Path(result["state_file"]).parent / "create-journal.jsonl", duplicate / "create-journal.jsonl")

    with pytest.raises(workspace.WorkspaceError, match="share attempt id"):
        workspace.inspect_attempt(attempt_args(repo, temp_root, attempt))
```

- [ ] **Step 2: テストが失敗することを確かめる**

Run: `uv run pytest .agents/skills/pr-review/tests/test_pr_review_workspace.py -q -k "inspect or killed or terminated"`
Expected: FAIL（`inspect_attempt` が未定義）

- [ ] **Step 3: 実装する**

`cleanup` の下に置く。

```python
SESSION_FILES = {JOURNAL_NAME, "session.json"}
SESSION_DIRECTORIES = {"review-backup", "worktree"}


def locate_attempt(repo: Path, temp_root_value: str | None, pr_number: int, attempt_id: str) -> Path | None:
    temp_root = Path(temp_root_value).resolve() if temp_root_value else Path(tempfile.gettempdir()).resolve()
    if not temp_root.is_dir():
        return None
    matches = attempt_sessions(temp_root, pr_number, attempt_id)
    if not matches:
        return None
    if len(matches) > 1:
        raise WorkspaceError(f"{len(matches)} sessions share attempt id {attempt_id}; keep them for the user")
    session_dir = matches[0]
    header = read_journal(session_dir / JOURNAL_NAME)[0]
    if (
        header.get("main_root") != str(repo)
        or header.get("session_dir") != str(session_dir)
        or header.get("pr_number") != pr_number
    ):
        raise WorkspaceError("create journal does not match this repository, PR and session directory")
    return session_dir


def creator_running(journal: Path) -> bool:
    with journal.open("rb") as stream:
        try:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return True
        fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
    return False


def worktree_registration(repo: Path, worktree: Path) -> dict[str, str] | None:
    listing = git(repo, "worktree", "list", "--porcelain", "-z", binary=True)
    assert isinstance(listing, bytes)
    target = os.path.realpath(worktree)
    entry: dict[str, str] = {}
    for field in listing.decode("utf-8", errors="surrogateescape").split("\0"):
        if field:
            key, _, value = field.partition(" ")
            entry[key] = value
            continue
        if "worktree" in entry and os.path.realpath(entry["worktree"]) == target:
            return entry
        entry = {}
    return None


def entry_name(path: Path, prefix: str = "") -> str:
    return prefix + path.name + ("/" if path.is_dir() and not path.is_symlink() else "")


def session_entries(session_dir: Path) -> list[str]:
    entries: list[str] = []
    for child in sorted(session_dir.iterdir()):
        entries.append(entry_name(child))
        if child.name == "review-backup" and child.is_dir() and not child.is_symlink():
            entries.extend(entry_name(grandchild, "review-backup/") for grandchild in sorted(child.iterdir()))
    return entries


def attempt_report(repo: Path, session_dir: Path, attempt_id: str, *, running: bool) -> dict[str, Any]:
    records = read_journal(session_dir / JOURNAL_NAME)
    last = records[-1]
    ended = last if last["phase"] in TERMINAL_PHASES else {}
    worktree = session_dir / "worktree"
    registration = worktree_registration(repo, worktree)
    state_file = session_dir / "session.json"
    return {
        "attempt_id": attempt_id,
        "status": "running" if running else (last["phase"] if ended else "vanished"),
        "session_dir": str(session_dir),
        "pid": records[0].get("pid"),
        "phases": [{"phase": record["phase"], "at": record.get("at")} for record in records],
        "last_phase": last["phase"],
        "last_phase_at": last.get("at"),
        "error": ended.get("error"),
        "signal": ended.get("signal"),
        "state_file": str(state_file) if state_file.is_file() and not state_file.is_symlink() else None,
        "worktree": str(worktree),
        "worktree_exists": worktree.exists() or worktree.is_symlink(),
        "worktree_registered": registration is not None,
        "worktree_lock": None if registration is None else registration.get("locked"),
        "entries": session_entries(session_dir),
    }


def inspect_attempt(args: argparse.Namespace) -> dict[str, Any]:
    attempt_id = validate_attempt_id(args.attempt_id)
    repo = require_main_checkout(args.repo)
    deadline = time.monotonic() + args.wait
    while True:
        session_dir = locate_attempt(repo, args.temp_root, args.pr_number, attempt_id)
        if session_dir is None:
            return {"attempt_id": attempt_id, "status": "absent", "session_dir": None}
        # Probe before reading so a just-finished attempt shows its end record.
        running = creator_running(session_dir / JOURNAL_NAME)
        report = attempt_report(repo, session_dir, attempt_id, running=running)
        remaining = deadline - time.monotonic()
        if not running or remaining <= 0:
            return report
        time.sleep(min(1.0, remaining))
```

`positive_integer` の下に置く。

```python
def non_negative_integer(value: str) -> int:
    number = int(value)
    if number < 0:
        raise argparse.ArgumentTypeError("must be zero or a positive integer")
    return number


def add_attempt_arguments(command: argparse.ArgumentParser) -> None:
    command.add_argument("--repo", required=True)
    command.add_argument("--pr-number", required=True, type=positive_integer)
    command.add_argument("--attempt-id", required=True)
    command.add_argument("--temp-root")
```

`parser` の `cleanup_parser` の後に置く。

```python
    inspect_parser = commands.add_parser("inspect", help="report how a create attempt ended and what it left")
    add_attempt_arguments(inspect_parser)
    inspect_parser.add_argument("--wait", type=non_negative_integer, default=0)
    inspect_parser.set_defaults(handler=inspect_attempt)
```

- [ ] **Step 4: テストが通ることを確かめる**

Run: `uv run pytest .agents/skills/pr-review/tests/test_pr_review_workspace.py -q`
Expected: PASS

- [ ] **Step 5: コミット**

```bash
git add .agents/skills/pr-review/scripts/pr_review_workspace.py .agents/skills/pr-review/tests/test_pr_review_workspace.py
git commit -m "feat(pr-review): 中断した create の試行を調べる inspect を加える"
```

### Task 3: `abandon` サブコマンド

**Files:**
- Modify: `.agents/skills/pr-review/scripts/pr_review_workspace.py`（`abandon_attempt` と補助関数、`parser`）
- Test: `.agents/skills/pr-review/tests/test_pr_review_workspace.py`

**Interfaces:**
- Consumes: Task 2 の `locate_attempt`・`attempt_report`・`worktree_registration`・`SESSION_FILES`・`SESSION_DIRECTORIES`・`add_attempt_arguments`、既存の `review_save_lock`・`require_session_worktree`
- Produces: `abandon_attempt(args) -> dict[str, Any]`（返却キーは `attempt_id`・`session_dir`・`worktree`・`worktree_removed`・`status`）

- [ ] **Step 1: テストを書く**

```python
def completed_attempt(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    monkeypatch.delenv("CODEX_THREAD_ID", raising=False)
    repo = tmp_path / "repo"
    commit = make_repo(repo)
    temp_root = tmp_path / "sessions"
    attempt = attempt_id()
    result = workspace.create(explicit_create_args(repo, commit, temp_root, attempt))
    return {
        "repo": repo,
        "commit": commit,
        "temp_root": temp_root,
        "attempt": attempt,
        "result": result,
        "session_dir": Path(result["state_file"]).parent,
    }


def test_abandon_clears_an_attempt_killed_while_waiting_for_the_lock(tmp_path: Path) -> None:
    # The Issue #39 state: the worktree exists and session.json was never published.
    repo = tmp_path / "repo"
    commit = make_repo(repo)
    temp_root = tmp_path / "sessions"
    attempt = attempt_id()
    env = os.environ.copy()
    env.pop("CODEX_THREAD_ID", None)
    with workspace.review_save_lock(repo):
        process = start_create(env, repo, commit, temp_root, attempt)
        try:
            waiting = wait_for_phase(repo, temp_root, attempt, "lock-wait")
        finally:
            kill_group(process.pid, signal.SIGKILL)
            process.communicate(timeout=10)
    session_dir = Path(waiting["session_dir"])
    (session_dir / ".session.json.kqdd8rsc").write_text("{}\n", encoding="utf-8")
    before = workspace.snapshot(repo)

    left = workspace.inspect_attempt(attempt_args(repo, temp_root, attempt, wait=10))
    removed = workspace.abandon_attempt(attempt_args(repo, temp_root, attempt))

    assert left["status"] == "vanished"
    assert left["last_phase"] == "lock-wait"
    assert left["state_file"] is None
    assert ".session.json.kqdd8rsc" in left["entries"]
    assert removed["worktree_removed"] is True
    assert removed["status"] == "vanished"
    assert not session_dir.exists()
    assert left["worktree"] not in git(repo, "worktree", "list")
    assert workspace.snapshot(repo) == before
    assert workspace.inspect_attempt(attempt_args(repo, temp_root, attempt))["status"] == "absent"
    with pytest.raises(workspace.WorkspaceError, match="nothing to abandon"):
        workspace.abandon_attempt(attempt_args(repo, temp_root, attempt))


def test_abandon_waits_for_a_checkout_that_outlives_create(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    commit = make_repo(repo)
    temp_root = tmp_path / "sessions"
    attempt = attempt_id()
    process = start_create(stalling_git_env(tmp_path), repo, commit, temp_root, attempt)
    try:
        wait_for_phase(repo, temp_root, attempt, "worktree-add")
        process.kill()  # only create itself; its git child keeps running
        process.communicate(timeout=10)

        orphaned = workspace.inspect_attempt(attempt_args(repo, temp_root, attempt))
        with pytest.raises(workspace.WorkspaceError, match="still running"):
            workspace.abandon_attempt(attempt_args(repo, temp_root, attempt))
        assert Path(orphaned["worktree"]).is_dir()
    finally:
        kill_group(process.pid, signal.SIGKILL)

    assert orphaned["status"] == "running"
    assert workspace.inspect_attempt(attempt_args(repo, temp_root, attempt, wait=10))["status"] == "vanished"
    assert workspace.abandon_attempt(attempt_args(repo, temp_root, attempt))["worktree_removed"] is True


def test_abandon_removes_a_worktree_left_initializing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    attempt = completed_attempt(tmp_path, monkeypatch)
    repo = attempt["repo"]
    worktree = attempt["result"]["worktree"]
    git(repo, "worktree", "lock", "--reason", "initializing", worktree)
    assert workspace.inspect_attempt(attempt_args(repo, attempt["temp_root"], attempt["attempt"]))[
        "worktree_lock"
    ] == "initializing"

    removed = workspace.abandon_attempt(attempt_args(repo, attempt["temp_root"], attempt["attempt"]))

    assert removed["worktree_removed"] is True
    assert removed["status"] == "completed"
    assert not Path(worktree).exists()
    assert worktree not in git(repo, "worktree", "list")
    assert not attempt["session_dir"].exists()


def test_abandon_keeps_a_worktree_locked_for_another_reason(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    attempt = completed_attempt(tmp_path, monkeypatch)
    repo = attempt["repo"]
    worktree = attempt["result"]["worktree"]
    git(repo, "worktree", "lock", "--reason", "kept by the user", worktree)

    with pytest.raises(workspace.WorkspaceError, match="locked"):
        workspace.abandon_attempt(attempt_args(repo, attempt["temp_root"], attempt["attempt"]))

    assert Path(worktree).is_dir()
    assert attempt["session_dir"].is_dir()


def test_abandon_refuses_while_the_attempt_is_running(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    attempt = completed_attempt(tmp_path, monkeypatch)
    args = attempt_args(attempt["repo"], attempt["temp_root"], attempt["attempt"])
    with (attempt["session_dir"] / "create-journal.jsonl").open("rb") as stream:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
        assert workspace.inspect_attempt(args)["status"] == "running"
        with pytest.raises(workspace.WorkspaceError, match="still running"):
            workspace.abandon_attempt(args)

    assert Path(attempt["result"]["worktree"]).is_dir()
    assert attempt["session_dir"].is_dir()


@pytest.mark.parametrize(
    ("extra", "message"),
    [
        ("review-backup/opus-5.md", "review backup"),
        ("review-backup/nested/", "review backup"),
        ("notes.txt", "unexpected entry"),
    ],
)
def test_abandon_keeps_a_session_with_files_it_did_not_create(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, extra: str, message: str
) -> None:
    attempt = completed_attempt(tmp_path, monkeypatch)
    path = attempt["session_dir"] / extra.rstrip("/")
    if extra.endswith("/"):
        path.mkdir()
    else:
        path.write_text("unsaved review\n", encoding="utf-8")

    with pytest.raises(workspace.WorkspaceError, match=message):
        workspace.abandon_attempt(attempt_args(attempt["repo"], attempt["temp_root"], attempt["attempt"]))

    assert path.exists()
    assert attempt["result"]["worktree"] in git(attempt["repo"], "worktree", "list")


def test_abandon_refuses_another_repository(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    attempt = completed_attempt(tmp_path, monkeypatch)
    other = tmp_path / "other"
    make_repo(other)

    with pytest.raises(workspace.WorkspaceError, match="does not match"):
        workspace.abandon_attempt(attempt_args(other, attempt["temp_root"], attempt["attempt"]))

    assert attempt["session_dir"].is_dir()
    assert attempt["result"]["worktree"] in git(attempt["repo"], "worktree", "list")


def test_abandon_touches_only_its_own_attempt(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    mine = completed_attempt(tmp_path, monkeypatch)
    repo = mine["repo"]
    theirs = workspace.create(explicit_create_args(repo, mine["commit"], mine["temp_root"], attempt_id()))
    other_review = repo / "reviews/#4-fix-herdr-session-cwd/gemini-3.6-flash.md"
    other_review.write_text("gemini review\n", encoding="utf-8")
    (repo / "notes.txt").write_text("user notes\n", encoding="utf-8")
    before = workspace.snapshot(repo)

    workspace.abandon_attempt(attempt_args(repo, mine["temp_root"], mine["attempt"]))

    assert not mine["session_dir"].exists()
    assert Path(theirs["worktree"]).is_dir()
    assert theirs["worktree"] in git(repo, "worktree", "list")
    assert Path(theirs["state_file"]).is_file()
    assert other_review.read_text(encoding="utf-8") == "gemini review\n"
    assert workspace.snapshot(repo) == before


def test_abandon_waits_for_the_repository_review_lock(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    attempt = completed_attempt(tmp_path, monkeypatch)
    command = [
        sys.executable,
        str(SCRIPT),
        "abandon",
        "--repo",
        str(attempt["repo"]),
        "--pr-number",
        "4",
        "--attempt-id",
        attempt["attempt"],
        "--temp-root",
        str(attempt["temp_root"]),
    ]

    with workspace.review_save_lock(attempt["repo"]):
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        with pytest.raises(subprocess.TimeoutExpired):
            process.wait(timeout=1)
        assert attempt["session_dir"].is_dir()

    stdout, stderr = process.communicate(timeout=10)
    assert process.returncode == 0, stderr
    assert json.loads(stdout)["session_dir"] == str(attempt["session_dir"])
    assert not attempt["session_dir"].exists()
```

- [ ] **Step 2: テストが失敗することを確かめる**

Run: `uv run pytest .agents/skills/pr-review/tests/test_pr_review_workspace.py -q -k abandon`
Expected: FAIL（`abandon_attempt` が未定義）

- [ ] **Step 3: 実装する**

`inspect_attempt` の下に置く。

```python
@contextmanager
def finished_creator(journal: Path) -> Generator[None]:
    """Hold the creator lock, refusing while create or its checkout still runs."""
    with journal.open("rb") as stream:
        try:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise WorkspaceError(
                "create attempt is still running; wait with inspect --wait before abandoning it"
            ) from error
        yield


def require_abandonable_entries(session_dir: Path) -> None:
    """Keep the session when it holds anything create itself did not write."""
    for child in session_dir.iterdir():
        name = child.name
        if child.is_symlink():
            raise WorkspaceError(f"session holds an unexpected entry; keep it for the user: {child}")
        if name in SESSION_DIRECTORIES and child.is_dir():
            continue
        if (name in SESSION_FILES or name.startswith(".session.json.")) and child.is_file():
            continue
        raise WorkspaceError(f"session holds an unexpected entry; keep it for the user: {child}")
    backup_dir = session_dir / "review-backup"
    if not backup_dir.is_dir():
        return
    for child in backup_dir.iterdir():
        snapshot_file = child.name == "previous-review.md" or child.name.startswith(".previous-review.md.")
        if child.is_symlink() or not child.is_file() or not snapshot_file:
            raise WorkspaceError(
                f"review backup holds a file other than the helper's snapshot; keep the session: {child}"
            )


def remove_attempt_worktree(repo: Path, worktree: Path) -> bool:
    registration = worktree_registration(repo, worktree)
    if worktree.is_symlink():
        raise WorkspaceError(f"session worktree path is a symlink; keep the session: {worktree}")
    if not worktree.exists():
        if registration is not None:
            raise WorkspaceError(f"worktree is registered but its directory is missing; keep the session: {worktree}")
        return False
    if registration is None:
        if any(worktree.iterdir()):
            raise WorkspaceError(f"session worktree directory is not a registered worktree; keep the session: {worktree}")
        return False
    require_session_worktree(worktree.resolve(strict=True), repo)
    # `git worktree add` marks its worktree "initializing" until checkout ends;
    # any other lock reason belongs to the user and git keeps refusing it.
    force = ("--force", "--force") if registration.get("locked") == "initializing" else ("--force",)
    git(repo, "worktree", "remove", *force, str(worktree))
    if worktree.exists() or worktree_registration(repo, worktree) is not None:
        raise WorkspaceError(f"git did not remove the review worktree: {worktree}")
    return True


def abandon_attempt(args: argparse.Namespace) -> dict[str, Any]:
    attempt_id = validate_attempt_id(args.attempt_id)
    repo = require_main_checkout(args.repo)
    with review_save_lock(repo):
        session_dir = locate_attempt(repo, args.temp_root, args.pr_number, attempt_id)
        if session_dir is None:
            raise WorkspaceError(f"no create attempt {attempt_id} for PR {args.pr_number}; nothing to abandon")
        with finished_creator(session_dir / JOURNAL_NAME):
            status = attempt_report(repo, session_dir, attempt_id, running=False)["status"]
            require_abandonable_entries(session_dir)
            worktree = session_dir / "worktree"
            removed = remove_attempt_worktree(repo, worktree)
            shutil.rmtree(session_dir)
    return {
        "attempt_id": attempt_id,
        "session_dir": str(session_dir),
        "status": status,
        "worktree": str(worktree),
        "worktree_removed": removed,
    }
```

`parser` の `inspect_parser` の後に置く。

```python
    abandon_parser = commands.add_parser(
        "abandon", help="remove what an interrupted create attempt left when it holds no unsaved review"
    )
    add_attempt_arguments(abandon_parser)
    abandon_parser.set_defaults(handler=abandon_attempt)
```

- [ ] **Step 4: テストが通ることを確かめる**

Run: `uv run pytest .agents/skills/pr-review/tests/test_pr_review_workspace.py -q`
Expected: PASS

- [ ] **Step 5: コミット**

```bash
git add .agents/skills/pr-review/scripts/pr_review_workspace.py .agents/skills/pr-review/tests/test_pr_review_workspace.py
git commit -m "feat(pr-review): 中断した create の試行を片付ける abandon を加える"
```

### Task 4: スキルと時間予算の規約

**Files:**
- Modify: `.agents/skills/pr-review/SKILL.md`
- Modify: `.agents/skills/pr-review/references/time-budget.md`

**Interfaces:**
- Consumes: Task 1〜3 の CLI（`create --attempt-id`、`inspect --wait`、`abandon`）

- [ ] **Step 1: `SKILL.md` の「ランタイム別の注意」を変える**

`### Claude Code` の箇条の末尾に次を足す。

```markdown
- helper を呼ぶ Bash には `timeout: 600000` を指定する（規約の「helper の呼び出し」）
```

`### pi` の箇条の末尾に次を足す。

```markdown
- bash ツールの `timeout` は秒単位である。helper を呼ぶときは指定しないか 600 以上にする（規約の「helper の呼び出し」）
```

- [ ] **Step 2: `SKILL.md` の「規約」を変える**

「自セッションの worktree の削除は helper の `cleanup` だけが行う。」で始まる箇条を次にする。

```markdown
- 自セッションの worktree の削除は helper の `cleanup` だけが行う。`create` が結果を返さずに中断した試行の残存物は、helper の `abandon` だけが片付ける（手順 2）。`git worktree remove`、`rm -rf` などの削除コマンドを自分で組み立てない。`cleanup`・`abandon` が拒否した場合も手で代行しない
```

「レビュー中は `git clean`」の箇条の前に次を足す。

```markdown
- helper の呼び出し: `pr_review_workspace.py` の各サブコマンドは、fetch・`gh` など所要時間の読めない別の処理と同じツール呼び出しにまとめない（結果の JSON を読む `jq` は同じ呼び出しでよい）。ツール呼び出しにタイムアウトを指定できるランタイムでは、指定しないか 600 秒以上を指定する（上限が 600 秒未満のランタイムではその上限）。`create` は同時のレビューやストレージの書き込み待ちで数分かかることがあり、短いタイムアウトで打ち切ると worktree が残ってレビューを続けられなくなる。時間予算はフェーズの境界で確かめ、helper を打ち切って守らない
```

- [ ] **Step 3: `SKILL.md` の手順 2 を変える**

「`create` を一度だけ実行する。」を「`create` は試行 ID ごとに一度だけ実行する。」に変える。その箇条の後（「Codex では次を実行する。」の前）に次を足す。

````markdown
   - `create` の前に試行 ID を決め、開始時刻と同じく進捗記録に残す。`create` が何も返さずに終わっても、この ID で自分の試行を指せる。helper は同じ PR に同じ ID の試行があれば worktree を作る前に拒否する。

     ```bash
     ATTEMPT_ID=$(date -u +%Y%m%dT%H%M%S%NZ)
     ```
````

2 つの `create` の行の `--temp-root /tmp` の後に ` --attempt-id "$ATTEMPT_ID"` を足す。

「`CODEX_THREAD_ID` が存在するのに」の箇条の後に次を足す。

````markdown
   - `create` は進捗を工程ごとに stderr とセッション内の journal へ記録する。`create` の呼び出しが、結果の JSON も helper のエラー（`error:` で始まる出力）も返さずに終わった場合（ツールのタイムアウト、ランタイムによる中断など）は、`create` をそのまま再実行せず、次の順に扱う。
     1. 次の `inspect` を実行する。`status` が `running` なら `--wait 540` を付けてやり直し、終わるのを待つ。それでも `running` なら、`abandon` も再試行もせず停止して報告する。

        ```bash
        uv run --no-project python "$HELPER" inspect --repo "$MAIN_ROOT" --pr-number "$PR_NUMBER" --attempt-id "$ATTEMPT_ID" --temp-root /tmp
        ```

     2. `status` が `absent` 以外なら、次の `abandon` で試行の残存物を片付ける。`abandon` は、試行が終わっていて、保存前の draft など helper が作った以外のファイルが無く、worktree がこのリポジトリの自セッションのものであるときだけ消す。拒否されたら削除を手で代行せず停止し、`inspect` の出力（工程・状態・残存パス）と拒否の理由を報告する。

        ```bash
        uv run --no-project python "$HELPER" abandon --repo "$MAIN_ROOT" --pr-number "$PR_NUMBER" --attempt-id "$ATTEMPT_ID" --temp-root /tmp
        ```

     3. `abandon` が成功した、または `inspect` が `absent` を返した場合、調査期限まで 10 分以上残っていれば、新しい `ATTEMPT_ID` を決めて `create` を 1 回だけやり直してよい。残っていなければ停止して報告する。
     4. やり直した `create` も結果を返さなければ、同じく 1・2 を行い、再試行せずに停止して報告する。

     `inspect` の出力から `create` の結果（`worktree`・`state_file` など）を組み立てて続行しない。`create` が helper のエラーで終わった場合は従来どおり停止して報告し、残存パスの報告に `inspect` を使ってよいが `abandon` はしない。
````

- [ ] **Step 4: `SKILL.md` の手順 9 と出力前セルフチェックを変える**

手順 9 の「最終応答では save/cleanup の結果、」で始まる箇条の末尾に次の文を足す。

```markdown
`create` をやり直した、または `abandon` を実行した場合は、試行 ID ごとの `inspect`・`abandon` の結果も報告する。
```

出力前セルフチェックの「`create` が返した `model_name`」の項目の前に次の 2 項目を足す。

```markdown
- helper の呼び出しを他の処理とまとめたり、600 秒未満のタイムアウトで打ち切ったりしていないか
- `create` に `--attempt-id "$ATTEMPT_ID"` を渡し、結果を返さなかった試行を `inspect`・`abandon` で扱ったか（拒否されたら手で消さずに停止したか）
```

- [ ] **Step 5: `references/time-budget.md` を変える**

「## 時間予算」の「開始からの目安は次のとおり。」の表の後の段落（「phase 境界、」で始まる箇条）の前に次を足す。

```markdown
- 期限はフェーズの境界で確かめるもので、実行中の helper をツールのタイムアウトで打ち切って守るものではない。準備の `create` は、同時のレビューやストレージの書き込み待ちで数分かかることがある。helper の呼び出し方とタイムアウトはスキル本文の規約「helper の呼び出し」に従う。`create` が結果を返さずに中断したときの再試行は、調査期限まで 10 分以上残っている場合の 1 回だけとする。
```

検証シナリオの表の末尾（S22 の後）に次の行を足す。

```markdown
| S23 | `create` のツール呼び出しがタイムアウトし、JSON もエラーも返らない | `create` をそのまま再実行しない。`inspect` と `abandon` の後、調査期限まで 10 分以上あれば新しい試行 ID で 1 回だけやり直す |
| S24 | `inspect` が `running`、`--wait 540` の後も `running` | `abandon` も再試行もせず停止し、工程と残存パスを報告 |
| S25 | `abandon` が拒否（draft あり、未知のファイル、利用者のロックなど） | 削除を手で代行せず停止し、`inspect` の出力と拒否の理由を報告 |
| S26 | やり直した `create` も結果を返さない | `inspect` と `abandon` の後、再試行せず停止して報告 |
```

- [ ] **Step 6: スキルのテストを実行する**

Run: `uv run pytest .agents/skills/pr-review tests/skills -q`
Expected: PASS。契約テストが失敗したら、変更の意図（Global Constraints の 2 行の `create` と cleanup の文）に照らして文書側を直す。文言を固定値で比べる新しい検査は足さない

- [ ] **Step 7: コミット**

```bash
git add .agents/skills/pr-review/SKILL.md .agents/skills/pr-review/references/time-budget.md
git commit -m "docs(pr-review): helper を短いタイムアウトで打ち切らず、中断した create を inspect と abandon で扱う"
```

### Task 5: 全体の検証、記録、PR

**Files:**
- Modify: `docs/superpowers/specs/2026-10-05-issue-39-pr-review-create-interruption-design.md`（9 章）
- Modify: この Plan（チェックボックス）

- [ ] **Step 1: リポジトリ全体のテストと配置検査**

Run: `uv run pytest -q` と `bash scripts/check-layout.sh` と `bash .devcontainer/run-tests.bash`
Expected: すべて PASS

- [ ] **Step 2: 実環境に近い条件での確認**

scratchpad に `git clone --shared` で作った使い捨ての clone に対して、新しい helper で次を確かめる（利用者の checkout と既存の worktree には触れない）。

- 単独の `create` の stderr に工程が出て、journal の時刻から `worktree-add`・`lock-wait`・`state-write` の所要時間が読めること
- 4 件同時の `create` で、`state-write` から `completed` までが計測前（95 秒）より短いこと
- `create` を `timeout -s TERM 5` で打ち切り、`inspect` が工程と `interrupted` を返し、`abandon` で片付くこと

結果は Spec の 9 章に記録する。確認の後、scratchpad の clone は `rm -rf -- "${S:?}/measure"` の形で消す。

- [ ] **Step 3: Spec に実装の記録を書いてコミット**

9 章に、各 Task のコミット、テストの件数、Step 2 の計測値、範囲外として残したもの（Issue の `/tmp/pr-review-38-wq1dp0rt` は journal が無く `abandon` の対象外）を書く。状態は `draft` のまま（明示承認は得ていない）。

```bash
git add docs/superpowers/specs/2026-10-05-issue-39-pr-review-create-interruption-design.md docs/superpowers/plans/2026-10-05-issue-39-pr-review-create-interruption.md
git commit -m "docs(spec): Issue #39 の実装の記録を残す"
```

- [ ] **Step 4: push と PR**

```bash
git push -u origin fix/issue-39-pr-review-create-interruption
gh pr create --base main --title "fix(pr-review): create の中断を調べて片付けられるようにし、短いタイムアウトで打ち切らない" --body-file <scratchpad の本文>
```

本文には、原因（3 章）、変更の要点、受け入れ条件との対応、検証結果、範囲外、`Closes #39` を書き、末尾に `🤖 Generated with [Claude Code](https://claude.com/claude-code)` を付ける。マージはしない。
