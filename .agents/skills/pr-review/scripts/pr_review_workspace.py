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
from contextlib import contextmanager, suppress
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
PR_OWNER = re.compile(r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?")
PR_NAME = re.compile(r"[a-z0-9_.-]+")
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


def normalize_pr_repository(value: str) -> str:
    # GitHub ignores case in owner/repo; one spelling keeps one review path.
    owner, separator, name = value.lower().partition("/")
    if not separator or PR_OWNER.fullmatch(owner) is None or PR_NAME.fullmatch(name) is None or name in {".", ".."}:
        raise WorkspaceError("PR repository must be a GitHub owner/repo")
    return f"{owner}/{name}"


def is_canonical_pr_repository(value: object) -> bool:
    try:
        return isinstance(value, str) and normalize_pr_repository(value) == value
    except WorkspaceError:
        return False


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
    pr_repository: str,
) -> tuple[Path, str]:
    if MODEL_FILENAME.fullmatch(model_name) is None:
        raise WorkspaceError("Codex model identifier is not a safe filename")
    if not is_canonical_pr_repository(pr_repository):
        raise WorkspaceError("PR repository must be a GitHub owner/repo")
    directory = review_directory_name(pr_number, head_branch)
    filename = f"{model_name}.md"
    # A fork and its upstream share one checkout and can reuse a number.
    return backup_dir / filename, f"reviews/{pr_repository}/{directory}/{filename}"


def legacy_review_destination(head_branch: str, model_name: str, *, pr_number: int) -> str:
    """Return where this review went before sessions pinned the PR repository."""
    return f"reviews/{review_directory_name(pr_number, head_branch)}/{model_name}.md"


def git(
    repo: Path,
    *args: str,
    binary: bool = False,
    pass_fds: tuple[int, ...] = (),
    new_session: bool = False,
) -> str | bytes:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        capture_output=True,
        pass_fds=pass_fds,
        start_new_session=new_session,
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
        # The journal is the record. A reader that stopped reading (a closed
        # pipe after a tool timeout) must not turn create into a helper error.
        with suppress(OSError):
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

    interrupted = False

    def interrupt(signum: int, _frame: object) -> None:
        nonlocal interrupted
        # `uv run` forwards the signal the process group already delivered;
        # a second copy must not cut short the journal's end record.
        if interrupted:
            return
        interrupted = True
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
    pr_repository = normalize_pr_repository(args.pr_repo)
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
            pr_repository=pr_repository,
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
                result = create_session(args, repo, commit, model, pr_repository, session_dir, journal)
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
    pr_repository: str,
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
        pr_repository=pr_repository,
    )
    legacy = legacy_review_destination(args.head_branch, model_name, pr_number=args.pr_number)
    destination_path = safe_destination(repo, destination)
    require_destination_parent(destination_path)

    before = snapshot(repo)
    journal.record("worktree-add")
    # A checkout that outlives this process keeps the creator lock held. Its
    # own session keeps a signal sent to this process group away from git:
    # SIGTERM there starts git's own cleanup, which a SIGKILL right after can
    # cut short and leave records git cannot remove. On our signal,
    # subprocess.run stops git with SIGKILL, leaving a worktree that
    # `git worktree remove` still accepts.
    git(
        repo,
        "worktree",
        "add",
        "--detach",
        str(worktree),
        commit,
        pass_fds=(journal.fileno(),),
        new_session=True,
    )

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
        # Reported only: it may be the other repository's review of this number.
        legacy_review = legacy if os.path.lexists(repo / legacy) else None
        state: dict[str, Any] = {
            "version": 7,
            "main_root": str(repo),
            "worktree": str(worktree.resolve(strict=True)),
            "backup_dir": str(backup_dir.resolve(strict=True)),
            "commit": commit,
            "head_branch": args.head_branch,
            "pr_repository": pr_repository,
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
        "legacy_review": legacy_review,
        "model_name": state["model_name"],
        "model_source": state["model_source"],
        "pr_repository": pr_repository,
        "previous_review": state["previous_review"],
        "state_file": str(state_file.resolve(strict=True)),
        "worktree": state["worktree"],
    }


def load_state(state_value: str) -> tuple[Path, dict[str, Any]]:
    state_file = Path(state_value).resolve(strict=True)
    with state_file.open(encoding="utf-8") as stream:
        state = json.load(stream)
    if not isinstance(state, dict):
        raise WorkspaceError("invalid PR-review session state")
    required = {
        "backup_dir",
        "commit",
        "destination",
        "destination_fingerprint",
        "draft",
        "head_branch",
        "pr_number",
        "pr_repository",
        "main_root",
        "model_name",
        "model_source",
        "previous_review",
        "worktree",
    }
    if state.get("version") == 6:
        raise WorkspaceError(
            "PR-review session state has no PR repository (version 6); "
            "keep the session and confirm which PR it belongs to"
        )
    if (
        state.get("version") != 7
        or not required.issubset(state)
        or state.get("model_source") not in MODEL_SOURCES
        or not is_canonical_pr_repository(state["pr_repository"])
    ):
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
            pr_repository=state["pr_repository"],
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


SESSION_FILES = {JOURNAL_NAME, "session.json"}
SESSION_DIRECTORIES = {"review-backup", "worktree"}


def locate_attempt(
    repo: Path, temp_root_value: str | None, pr_repository: str, pr_number: int, attempt_id: str
) -> Path | None:
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
        or header.get("pr_repository") != pr_repository
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


def worktree_registrations(repo: Path) -> list[dict[str, str]]:
    listing = git(repo, "worktree", "list", "--porcelain", "-z", binary=True)
    assert isinstance(listing, bytes)
    entries: list[dict[str, str]] = []
    entry: dict[str, str] = {}
    for field in listing.decode("utf-8", errors="surrogateescape").split("\0"):
        if field:
            key, _, value = field.partition(" ")
            entry[key] = value
            continue
        if "worktree" in entry:
            entries.append(entry)
        entry = {}
    return entries


def worktree_registration(repo: Path, worktree: Path) -> dict[str, str] | None:
    target = os.path.realpath(worktree)
    return next(
        (entry for entry in worktree_registrations(repo) if os.path.realpath(entry["worktree"]) == target),
        None,
    )


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
    pr_repository = normalize_pr_repository(args.pr_repo)
    repo = require_main_checkout(args.repo)
    deadline = time.monotonic() + args.wait
    while True:
        session_dir = locate_attempt(repo, args.temp_root, pr_repository, args.pr_number, attempt_id)
        if session_dir is None:
            return {"attempt_id": attempt_id, "status": "absent", "session_dir": None}
        # Probe before reading so a just-finished attempt shows its end record.
        running = creator_running(session_dir / JOURNAL_NAME)
        report = attempt_report(repo, session_dir, attempt_id, running=running)
        remaining = deadline - time.monotonic()
        if not running or remaining <= 0:
            return report
        time.sleep(min(1.0, remaining))


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


def read_link(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="surrogateescape").strip()


def attempt_admin_dirs(repo: Path, worktree: Path) -> list[Path]:
    """Find this repository's worktree records that belong to the session worktree."""
    admin_root = git_path(repo, "--git-common-dir") / "worktrees"
    own_gitfile = os.path.realpath(worktree / ".git")
    found: set[Path] = set()
    gitfile = worktree / ".git"
    if gitfile.is_symlink() or (gitfile.exists() and not gitfile.is_file()):
        raise WorkspaceError(f"session worktree .git is not a file; keep the session: {worktree}")
    if gitfile.is_file():
        content = read_link(gitfile)
        if not content.startswith("gitdir: "):
            raise WorkspaceError(f"session worktree .git is not a gitdir link; keep the session: {worktree}")
        linked = Path(os.path.realpath(worktree / content.removeprefix("gitdir: ")))
        if linked.parent != admin_root:
            raise WorkspaceError(f"session worktree links outside this repository's worktree records: {linked}")
        if os.path.lexists(admin_root / linked.name):
            found.add(admin_root / linked.name)
    if admin_root.is_dir():
        for admin in admin_root.iterdir():
            backlink = admin / "gitdir"
            if backlink.is_file() and os.path.realpath(read_link(backlink)) == own_gitfile:
                found.add(admin)
    for admin in found:
        if admin.is_symlink() or not admin.is_dir():
            raise WorkspaceError(f"worktree record is not a directory; keep the session: {admin}")
        backlink = admin / "gitdir"
        if os.path.lexists(backlink) and os.path.realpath(read_link(backlink)) != own_gitfile:
            raise WorkspaceError(f"worktree record belongs to another worktree; keep the session: {admin}")
        lock = admin / "locked"
        if os.path.lexists(lock) and read_link(lock) != "initializing":
            raise WorkspaceError(f"worktree record is locked by the user; keep the session: {admin}")
    return sorted(found)


def is_session_worktree(worktree: Path, repo: Path) -> bool:
    try:
        require_session_worktree(worktree.resolve(strict=True), repo)
    except (WorkspaceError, OSError):
        return False
    return True


def remove_attempt_worktree(repo: Path, worktree: Path) -> bool:
    if worktree.is_symlink():
        raise WorkspaceError(f"session worktree path is a symlink; keep the session: {worktree}")
    registration = worktree_registration(repo, worktree)
    lock = None if registration is None else registration.get("locked")
    if lock not in (None, "initializing"):
        raise WorkspaceError(f"worktree is locked ({lock}); keep the session for the user: {worktree}")
    if registration is not None and worktree.is_dir() and is_session_worktree(worktree, repo):
        # `git worktree add` marks its worktree "initializing" until checkout ends.
        force = ("--force", "--force") if lock == "initializing" else ("--force",)
        git(repo, "worktree", "remove", *force, str(worktree))
        removed = True
    else:
        # git's own `worktree add` cleanup was cut short and left records git
        # no longer accepts; remove only the ones that point at this worktree.
        admins = attempt_admin_dirs(repo, worktree)
        if registration is not None and not admins:
            raise WorkspaceError(f"cannot find the worktree record git lists; keep the session: {worktree}")
        removed = bool(admins) or worktree.exists()
        for admin in admins:
            shutil.rmtree(admin)
        if worktree.exists():
            shutil.rmtree(worktree)
    if worktree.exists() or worktree_registration(repo, worktree) is not None:
        raise WorkspaceError(f"the review worktree is still present: {worktree}")
    return removed


def abandon_attempt(args: argparse.Namespace) -> dict[str, Any]:
    attempt_id = validate_attempt_id(args.attempt_id)
    pr_repository = normalize_pr_repository(args.pr_repo)
    repo = require_main_checkout(args.repo)
    with review_save_lock(repo):
        session_dir = locate_attempt(repo, args.temp_root, pr_repository, args.pr_number, attempt_id)
        if session_dir is None:
            raise WorkspaceError(
                f"no create attempt {attempt_id} for PR {pr_repository}#{args.pr_number}; nothing to abandon"
            )
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


PR_STATES = {"OPEN", "CLOSED", "MERGED"}
ENDED_PR_STATES = {"CLOSED", "MERGED"}


def query_pr_state(pr_repository: str, pr_number: int) -> tuple[str | None, str]:
    """Return the PR's GitHub state, or None and why it is unknown."""
    try:
        result = subprocess.run(
            ["gh", "pr", "view", str(pr_number), "--repo", pr_repository, "--json", "number,state"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as error:
        return None, f"cannot run gh: {error}"
    if result.returncode:
        return None, f"gh pr view failed: {result.stderr.strip()}"
    try:
        reported = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None, "gh pr view returned invalid JSON"
    if not isinstance(reported, dict) or reported.get("number") != pr_number or reported.get("state") not in PR_STATES:
        return None, f"gh pr view did not report {pr_repository}#{pr_number}"
    return reported["state"], ""


def session_report(
    repo: Path, registration: dict[str, str], pr_states: dict[tuple[str, int], tuple[str | None, str]]
) -> dict[str, Any]:
    worktree = Path(registration["worktree"])
    report: dict[str, Any] = {
        "session_dir": str(worktree.parent),
        "worktree": str(worktree),
        "pr_repository": None,
        "pr_number": None,
        "head_branch": None,
        "commit": None,
        "pr_state": None,
        "removable": False,
    }
    try:
        state_repo, state = load_state(str(worktree.parent / "session.json"))
    except (WorkspaceError, OSError, ValueError) as error:
        return {**report, "reason": f"session state cannot be used: {error}"}
    pr_repository, pr_number = state["pr_repository"], state["pr_number"]
    report.update(
        pr_repository=pr_repository, pr_number=pr_number, head_branch=state["head_branch"], commit=state["commit"]
    )
    if state_repo != repo:
        return {**report, "reason": f"session belongs to another checkout: {state_repo}"}
    for flag in ("locked", "prunable"):
        if flag in registration:
            detail = f" ({registration[flag]})" if registration[flag] else ""
            return {**report, "reason": f"worktree is {flag}{detail}"}
    if type(pr_number) is not int or pr_number < 1:
        return {**report, "reason": "session state has an invalid PR number"}
    key = (pr_repository, pr_number)
    if key not in pr_states:
        pr_states[key] = query_pr_state(*key)
    pr_state, failure = pr_states[key]
    if pr_state is None:
        return {**report, "reason": f"PR state is unknown: {failure}"}
    report["pr_state"] = pr_state
    if pr_state not in ENDED_PR_STATES:
        return {**report, "reason": f"{pr_repository}#{pr_number} is open"}
    return {**report, "removable": True, "reason": f"{pr_repository}#{pr_number} is {pr_state.lower()}"}


def sessions(args: argparse.Namespace) -> dict[str, Any]:
    """Report each review session of a checkout and whether its own PR has ended."""
    repo = require_main_checkout(args.repo)
    pr_states: dict[tuple[str, int], tuple[str | None, str]] = {}
    reports = [
        session_report(repo, entry, pr_states)
        for entry in worktree_registrations(repo)
        if PurePosixPath(entry["worktree"]).name == "worktree"
        and PurePosixPath(entry["worktree"]).parent.name.startswith("pr-review-")
    ]
    return {"main_root": str(repo), "sessions": reports}


def positive_integer(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return number


def non_negative_integer(value: str) -> int:
    number = int(value)
    if number < 0:
        raise argparse.ArgumentTypeError("must be zero or a positive integer")
    return number


def add_attempt_arguments(command: argparse.ArgumentParser) -> None:
    command.add_argument("--repo", required=True)
    command.add_argument("--pr-repo", required=True)
    command.add_argument("--pr-number", required=True, type=positive_integer)
    command.add_argument("--attempt-id", required=True)
    command.add_argument("--temp-root")


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)

    create_parser = commands.add_parser("create", help="create a unique detached review worktree")
    create_parser.add_argument("--repo", required=True)
    create_parser.add_argument("--pr-repo", required=True)
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

    inspect_parser = commands.add_parser("inspect", help="report how a create attempt ended and what it left")
    add_attempt_arguments(inspect_parser)
    inspect_parser.add_argument("--wait", type=non_negative_integer, default=0)
    inspect_parser.set_defaults(handler=inspect_attempt)

    abandon_parser = commands.add_parser(
        "abandon", help="remove what an interrupted create attempt left when it holds no unsaved review"
    )
    add_attempt_arguments(abandon_parser)
    abandon_parser.set_defaults(handler=abandon_attempt)

    sessions_parser = commands.add_parser(
        "sessions", help="report the review sessions of a checkout and whether each one's PR has ended"
    )
    sessions_parser.add_argument("--repo", required=True)
    sessions_parser.set_defaults(handler=sessions)
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        result = args.handler(args)
    except CreateInterrupted as error:
        # Not "error:": the skill stops on that prefix as a helper error, while
        # an interrupted create is one that inspect and abandon can clear.
        print(f"interrupted: {error}", file=sys.stderr)
        return 128 + error.signum
    except KeyboardInterrupt:
        print(f"interrupted: {args.command} interrupted by SIGINT", file=sys.stderr)
        return 128 + signal.SIGINT
    except (WorkspaceError, OSError, ValueError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
