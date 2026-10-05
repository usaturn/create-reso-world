#!/usr/bin/env python3
"""Create, verify, save and retire disposable PR-review worktrees."""

from __future__ import annotations

import argparse
import base64
import fcntl
import hashlib
import json
import os
import re
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from collections.abc import Generator, Mapping
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any, cast


class WorkspaceError(RuntimeError):
    """Report a safety invariant violation without changing repository state."""


class CreateInterrupted(BaseException):
    """Stop create on a termination signal so its journal records how it ended."""

    def __init__(self, signum: int) -> None:
        super().__init__(f"create interrupted by {signal.Signals(signum).name}")
        self.signum = signum


MODEL_FILENAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
# Path separators, Windows-illegal name chars, and C0 controls.
UNSAFE_DIRECTORY_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')

MODEL_SOURCE_CODEX = "codex-rollout"
MODEL_SOURCE_EXPLICIT = "explicit"
MODEL_SOURCES = {MODEL_SOURCE_CODEX, MODEL_SOURCE_EXPLICIT}

ATTEMPT_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")
JOURNAL_NAME = "create-journal.jsonl"
TERMINAL_PHASES = ("completed", "failed", "interrupted")
# Tool timeouts and closing terminals send these before any SIGKILL.
INTERRUPT_SIGNALS = (signal.SIGTERM, signal.SIGHUP)


def _json_object(value: object) -> dict[str, object] | None:
    if not isinstance(value, dict):
        return None
    return cast(dict[str, object], value)


def validate_model_name(value: str) -> str:
    # Provider-style identifiers (e.g. opencode/deepseek-v4-flash-free) are
    # common; map `/` to `-` the same way head branches become review dirs.
    # Runtime display names may contain whitespace (e.g. `Cursor Grok 4.6`);
    # map each whitespace run to `-` so the agent proposal is deterministic.
    # Edge whitespace would survive as a leading/trailing `-` and silently
    # move the artifact path, so reject it before the substitution runs.
    if value != value.strip():
        raise WorkspaceError("model identifier is not a safe filename")
    sanitized = value.replace("/", "-")
    sanitized = re.sub(r"\s+", "-", sanitized)
    if MODEL_FILENAME.fullmatch(sanitized) is None:
        raise WorkspaceError("model identifier is not a safe filename")
    return sanitized


def resolve_codex_model_name(environ: Mapping[str, str] | None = None) -> str:
    environment = os.environ if environ is None else environ
    thread_id = environment.get("CODEX_THREAD_ID", "")
    try:
        uuid.UUID(thread_id)
    except ValueError as error:
        raise WorkspaceError("CODEX_THREAD_ID is missing or invalid") from error

    codex_home = (Path(environment["CODEX_HOME"]) if "CODEX_HOME" in environment else Path.home() / ".codex").resolve()
    matches = sorted((codex_home / "sessions").rglob(f"*{thread_id}.jsonl"))
    if len(matches) != 1:
        raise WorkspaceError(f"expected exactly one Codex rollout for {thread_id}, found {len(matches)}")

    model_name: str | None = None
    with matches[0].open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            try:
                parsed: object = json.loads(line)
            except json.JSONDecodeError as error:
                if not line.endswith("\n"):
                    continue
                raise WorkspaceError(f"invalid rollout JSON at line {line_number}") from error
            record = _json_object(parsed)
            if record is None or record.get("type") != "turn_context":
                continue
            payload = _json_object(record.get("payload"))
            if payload is None:
                continue
            candidate = payload.get("model")
            if isinstance(candidate, str) and candidate:
                model_name = candidate

    if model_name is None:
        raise WorkspaceError("Codex rollout has no turn_context model")
    return validate_model_name(model_name)


def resolve_runtime_model_name(
    explicit_model_name: str | None,
    environ: Mapping[str, str] | None = None,
) -> tuple[str, str]:
    environment = os.environ if environ is None else environ
    if environment.get("CODEX_THREAD_ID"):
        runtime_model = resolve_codex_model_name(environment)
        if explicit_model_name is not None and (validate_model_name(explicit_model_name) != runtime_model):
            raise WorkspaceError("explicit model does not match Codex runtime model")
        return runtime_model, MODEL_SOURCE_CODEX
    if explicit_model_name is None:
        raise WorkspaceError("model name is required outside Codex")
    return validate_model_name(explicit_model_name), MODEL_SOURCE_EXPLICIT


def normalize_head_branch(value: str) -> str:
    if not value or value.startswith("/") or value.endswith("/") or value in {".", ".."}:
        raise WorkspaceError("head branch cannot produce a safe review directory")
    normalized = UNSAFE_DIRECTORY_CHARS.sub("-", value).rstrip(" .")
    if not normalized or normalized in {".", ".."}:
        raise WorkspaceError("head branch cannot produce a safe review directory")
    return normalized


def review_directory_name(pr_number: int, head_branch: str) -> str:
    if type(pr_number) is not int or pr_number < 1:
        raise WorkspaceError("PR number cannot produce a safe review directory")
    return f"#{pr_number}-{normalize_head_branch(head_branch)}"


def review_artifact_paths(
    backup_dir: Path,
    head_branch: str,
    model_name: str,
    *,
    pr_number: int,
) -> tuple[Path, str]:
    if MODEL_FILENAME.fullmatch(model_name) is None:
        raise WorkspaceError("Codex model identifier is not a safe filename")
    directory = review_directory_name(pr_number, head_branch)
    filename = f"{model_name}.md"
    return backup_dir / filename, f"reviews/{directory}/{filename}"


def git(repo: Path, *args: str, binary: bool = False, pass_fds: tuple[int, ...] = ()) -> str | bytes:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        capture_output=True,
        pass_fds=pass_fds,
    )
    if result.returncode:
        message = result.stderr.decode("utf-8", errors="replace").strip()
        raise WorkspaceError(f"git {' '.join(args)} failed: {message}")
    if binary:
        return result.stdout
    return result.stdout.decode("utf-8", errors="strict").strip()


def git_path(repo: Path, argument: str) -> Path:
    value = Path(str(git(repo, "rev-parse", argument)))
    if not value.is_absolute():
        value = repo / value
    return value.resolve(strict=True)


def require_main_checkout(repo_value: str) -> Path:
    repo = Path(repo_value).resolve(strict=True)
    top_level = Path(str(git(repo, "rev-parse", "--show-toplevel"))).resolve(strict=True)
    if top_level != repo:
        raise WorkspaceError(f"repo must name the exact repository root: {repo}")
    if git_path(repo, "--git-dir") != git_path(repo, "--git-common-dir"):
        raise WorkspaceError("repo must be the main checkout, not a linked worktree")
    return repo


def snapshot(repo: Path) -> dict[str, Any]:
    # Keep main-checkout inspection read-only during concurrent reviews.
    status = git(
        repo,
        "--no-optional-locks",
        "status",
        "--porcelain=v1",
        "--untracked-files=normal",
        "-z",
        "--",
        ".",
        ":(exclude)reviews",
        ":(exclude)reviews/**",
        binary=True,
    )
    assert isinstance(status, bytes)
    return {
        "branch": str(git(repo, "branch", "--show-current")),
        "head": str(git(repo, "rev-parse", "HEAD")),
        "status": base64.b64encode(status).decode("ascii"),
    }


def file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def destination_fingerprint(path: Path) -> dict[str, str]:
    fingerprint = {"path": str(path)}
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return {**fingerprint, "kind": "missing"}
    if stat.S_ISLNK(metadata.st_mode):
        target = os.readlink(path).encode("utf-8", errors="surrogateescape")
        return {
            **fingerprint,
            "kind": "symlink",
            "sha256": hashlib.sha256(target).hexdigest(),
        }
    if stat.S_ISREG(metadata.st_mode):
        return {**fingerprint, "kind": "file", "sha256": file_digest(path)}
    if stat.S_ISDIR(metadata.st_mode):
        return {**fingerprint, "kind": "directory"}
    return {**fingerprint, "kind": "other"}


def snapshot_existing_review(
    destination: Path,
    backup_dir: Path,
) -> tuple[dict[str, str], Path | None]:
    before = destination_fingerprint(destination)
    if before["kind"] == "missing":
        return before, None
    if before["kind"] != "file":
        raise WorkspaceError("existing review destination must be a regular file")

    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        source_fd = os.open(destination, flags)
    except OSError as error:
        raise WorkspaceError("existing review changed while snapshotting") from error

    previous = backup_dir / "previous-review.md"
    handle, temporary = tempfile.mkstemp(prefix=".previous-review.md.", dir=backup_dir)
    digest = hashlib.sha256()
    try:
        with os.fdopen(source_fd, "rb") as source, os.fdopen(handle, "wb") as output:
            if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
                raise WorkspaceError("existing review destination must be a regular file")
            # Session files need no fsync: os.replace publishes all or nothing,
            # and after an OS crash the review session cannot continue anyway.
            for block in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(block)
                output.write(block)
        after = destination_fingerprint(destination)
        if after != before or digest.hexdigest() != before.get("sha256"):
            raise WorkspaceError("existing review changed while snapshotting")
        os.replace(temporary, previous)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        previous.unlink(missing_ok=True)
        raise
    return before, previous


def require_destination_parent(destination: Path) -> None:
    current = destination.parent
    while True:
        if current.exists():
            if not current.is_dir():
                raise WorkspaceError(f"review destination parent is not a directory: {current}")
            return
        if current.is_symlink():
            raise WorkspaceError(f"review destination parent is not a directory: {current}")
        current = current.parent


def verify_state(state: dict[str, Any], destination: Path) -> None:
    require_destination_parent(destination)
    if destination_fingerprint(destination) != state["destination_fingerprint"]:
        raise WorkspaceError("review destination changed during PR review; stop without saving or cleanup")


@contextmanager
def review_save_lock(repo: Path) -> Generator[None]:
    lock_path = git_path(repo, "--git-common-dir") / "pr-review-save.lock"
    with lock_path.open("a+b") as stream:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


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


def load_state(state_value: str) -> tuple[Path, dict[str, Any]]:
    state_file = Path(state_value).resolve(strict=True)
    with state_file.open(encoding="utf-8") as stream:
        state = json.load(stream)
    required = {
        "backup_dir",
        "commit",
        "destination",
        "destination_fingerprint",
        "draft",
        "head_branch",
        "pr_number",
        "main_root",
        "model_name",
        "model_source",
        "previous_review",
        "worktree",
    }
    if state.get("version") != 6 or not required.issubset(state) or state.get("model_source") not in MODEL_SOURCES:
        raise WorkspaceError("invalid PR-review session state")
    if state_file.name != "session.json":
        raise WorkspaceError("invalid PR-review session state")
    session_dir = state_file.parent
    if not session_dir.name.startswith("pr-review-"):
        raise WorkspaceError("session state is outside a PR-review session directory")

    repo = require_main_checkout(str(state.get("main_root", "")))
    backup_dir = Path(str(state.get("backup_dir", ""))).resolve(strict=True)
    worktree = Path(str(state.get("worktree", ""))).resolve(strict=True)
    if backup_dir != (session_dir / "review-backup").resolve(strict=True):
        raise WorkspaceError("session backup directory does not match its state file")
    if worktree != (session_dir / "worktree").resolve(strict=True):
        raise WorkspaceError("session worktree does not match its state file")
    previous_value = state["previous_review"]
    if previous_value is not None:
        try:
            previous = Path(str(previous_value)).resolve(strict=True)
        except OSError as error:
            raise WorkspaceError("previous review snapshot does not match its session") from error
        expected = (backup_dir / "previous-review.md").resolve()
        if previous != expected or not previous.is_file():
            raise WorkspaceError("previous review snapshot does not match its session")
    return repo, state


def verify(args: argparse.Namespace) -> dict[str, str]:
    repo, state = load_state(args.state)
    destination = safe_destination(repo, state["destination"])
    with review_save_lock(repo):
        verify_state(state, destination)
    return {"main_root": str(repo), "status": "unchanged"}


def is_within(path: Path, directory: Path) -> bool:
    try:
        path.relative_to(directory)
    except ValueError:
        return False
    return True


def safe_destination(repo: Path, destination_value: str) -> Path:
    relative = PurePosixPath(destination_value)
    if relative.is_absolute() or len(relative.parts) < 3:
        raise WorkspaceError("destination must be below reviews/<directory>/")
    if relative.parts[0] != "reviews" or any(part in {"", ".", ".."} for part in relative.parts):
        raise WorkspaceError("destination must be a normalized path below reviews/")
    if relative.suffix != ".md":
        raise WorkspaceError("review destination must end in .md")

    destination = repo / Path(*relative.parts)
    resolved_destination = destination.resolve(strict=False)
    allowed_root = repo / "reviews"
    if not is_within(resolved_destination, allowed_root):
        raise WorkspaceError("destination escapes the main repository reviews/ directory")
    return destination


def atomic_copy(source: Path, destination: Path) -> None:
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
    except (FileExistsError, NotADirectoryError) as error:
        raise WorkspaceError(f"review destination parent is not a directory: {destination.parent}") from error
    handle, temporary = tempfile.mkstemp(prefix=f".{destination.name}.", dir=destination.parent)
    try:
        with source.open("rb") as input_stream, os.fdopen(handle, "wb") as output_stream:
            shutil.copyfileobj(input_stream, output_stream)
            output_stream.flush()
            os.fsync(output_stream.fileno())
        os.replace(temporary, destination)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


def save(args: argparse.Namespace) -> dict[str, str]:
    repo, state = load_state(args.state)

    with review_save_lock(repo):
        if state["model_source"] == MODEL_SOURCE_CODEX:
            runtime_model = resolve_codex_model_name()
            if runtime_model != state["model_name"]:
                raise WorkspaceError("runtime model changed during PR review; stop without saving")
        else:
            runtime_model = state["model_name"]

        backup_dir = Path(state["backup_dir"]).resolve(strict=True)
        expected_draft, expected_destination = review_artifact_paths(
            backup_dir,
            state["head_branch"],
            runtime_model,
            pr_number=state["pr_number"],
        )
        if str(expected_draft) != state["draft"]:
            raise WorkspaceError("draft does not match the pinned review path")
        if expected_destination != state["destination"]:
            raise WorkspaceError("destination does not match the pinned review path")

        draft = expected_draft.resolve(strict=False)
        if not draft.is_file() or not is_within(draft, backup_dir):
            raise WorkspaceError("pinned draft must be a regular file inside the session backup directory")
        destination = safe_destination(repo, expected_destination)
        verify_state(state, destination)
        atomic_copy(draft, destination)
    return {"backup": str(draft), "destination": str(destination)}


def require_session_worktree(worktree: Path, repo: Path) -> None:
    """Refuse to delete anything but this session's linked worktree of repo."""
    try:
        top_level = Path(str(git(worktree, "rev-parse", "--show-toplevel"))).resolve(strict=True)
    except (WorkspaceError, OSError) as error:
        raise WorkspaceError(f"session path is not a linked worktree: {worktree}") from error
    if top_level != worktree:
        raise WorkspaceError(f"session path is not a linked worktree: {worktree}")
    if git_path(worktree, "--git-dir") == git_path(worktree, "--git-common-dir"):
        raise WorkspaceError(f"session path is not a linked worktree: {worktree}")
    if git_path(worktree, "--git-common-dir") != git_path(repo, "--git-common-dir"):
        raise WorkspaceError(f"session path is not a linked worktree of the pinned repository: {worktree}")


def require_saved_review(draft: Path, destination: Path) -> None:
    """Keep the session when the destination does not hold the finished draft."""
    if not draft.is_file():
        raise WorkspaceError("review draft is missing; the review is not saved")
    fingerprint = destination_fingerprint(destination)
    if fingerprint["kind"] != "file" or fingerprint.get("sha256") != file_digest(draft):
        raise WorkspaceError(
            "review destination does not hold the pinned draft; the review is not saved, so the session is kept"
        )


def cleanup(args: argparse.Namespace) -> dict[str, str]:
    repo, state = load_state(args.state)
    session_dir = Path(args.state).resolve(strict=True).parent
    worktree = Path(state["worktree"]).resolve(strict=True)
    draft = Path(state["draft"]).resolve(strict=False)
    destination = safe_destination(repo, state["destination"])

    with review_save_lock(repo):
        require_saved_review(draft, destination)
        require_session_worktree(worktree, repo)
        git(repo, "worktree", "remove", "--force", str(worktree))
        if worktree.exists():
            raise WorkspaceError(f"git did not remove the review worktree: {worktree}")
        shutil.rmtree(session_dir)
    return {
        "destination": str(destination),
        "session_dir": str(session_dir),
        "worktree": str(worktree),
    }


def positive_integer(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return number


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)

    create_parser = commands.add_parser("create", help="create a unique detached review worktree")
    create_parser.add_argument("--repo", required=True)
    create_parser.add_argument("--pr-number", required=True, type=positive_integer)
    create_parser.add_argument("--commit", required=True)
    create_parser.add_argument("--head-branch", required=True)
    create_parser.add_argument("--model-name")
    create_parser.add_argument("--temp-root")
    create_parser.add_argument("--attempt-id", required=True)
    create_parser.set_defaults(handler=create)

    verify_parser = commands.add_parser("verify", help="verify that the main checkout is unchanged")
    verify_parser.add_argument("--state", required=True)
    verify_parser.set_defaults(handler=verify)

    save_parser = commands.add_parser("save", help="atomically save the pinned review draft")
    save_parser.add_argument("--state", required=True)
    save_parser.set_defaults(handler=save)

    cleanup_parser = commands.add_parser("cleanup", help="remove the session worktree once the review is saved")
    cleanup_parser.add_argument("--state", required=True)
    cleanup_parser.set_defaults(handler=cleanup)
    return root


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


if __name__ == "__main__":
    raise SystemExit(main())
