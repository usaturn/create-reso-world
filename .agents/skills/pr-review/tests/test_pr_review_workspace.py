from __future__ import annotations

import argparse
import base64
import contextlib
import fcntl
import importlib.util
import json
import os
import shutil
import signal
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any

import pytest

SCRIPT = Path(__file__).parents[1] / "scripts" / "pr_review_workspace.py"
SPEC = importlib.util.spec_from_file_location("pr_review_workspace", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
workspace = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(workspace)

THREAD_ID = "019fd23a-4723-7e02-83d9-58f32849f5ab"


def attempt_id() -> str:
    return uuid.uuid4().hex


def write_rollout(codex_home: Path, models: list[str], thread_id: str = THREAD_ID) -> Path:
    rollout = codex_home / "sessions" / "2026" / "08" / "05" / f"rollout-{thread_id}.jsonl"
    rollout.parent.mkdir(parents=True, exist_ok=True)
    with rollout.open("w", encoding="utf-8") as stream:
        for model in models:
            record = {
                "type": "turn_context",
                "payload": {"model": model},
            }
            stream.write(json.dumps(record) + "\n")
    return rollout


def write_rollout_text(codex_home: Path, text: str) -> Path:
    rollout = codex_home / "sessions" / "2026" / "08" / "05" / f"rollout-{THREAD_ID}.jsonl"
    rollout.parent.mkdir(parents=True, exist_ok=True)
    rollout.write_text(text, encoding="utf-8")
    return rollout


def test_resolve_codex_model_name_uses_latest_turn_context(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    codex_home = tmp_path / "codex"
    write_rollout(codex_home, ["gpt-5", "gpt-5.6-sol"])
    (codex_home / "config.toml").write_text('model = "gpt-5"\n', encoding="utf-8")
    monkeypatch.setenv("CODEX_HOME", str(codex_home))
    monkeypatch.setenv("CODEX_THREAD_ID", THREAD_ID)

    assert workspace.resolve_codex_model_name() == "gpt-5.6-sol"


@pytest.mark.parametrize(
    ("setup", "message"),
    [
        ("missing-thread", "CODEX_THREAD_ID"),
        ("missing-rollout", "rollout"),
        ("missing-context", "turn_context"),
        ("unsafe-model", "safe filename"),
        ("non-unique-rollout", "exactly one"),
        ("invalid-json", "invalid rollout JSON"),
    ],
)
def test_resolve_codex_model_name_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    setup: str,
    message: str,
) -> None:
    codex_home = tmp_path / "codex"
    monkeypatch.setenv("CODEX_HOME", str(codex_home))
    monkeypatch.delenv("CODEX_THREAD_ID", raising=False)

    if setup != "missing-thread":
        monkeypatch.setenv("CODEX_THREAD_ID", THREAD_ID)
    if setup == "missing-context":
        rollout = write_rollout(codex_home, [])
        rollout.write_text('{"type":"event_msg","payload":{}}\n', encoding="utf-8")
    if setup == "unsafe-model":
        # `:` and other non-filename characters remain rejected after `/` → `-`
        # and whitespace → `-` sanitization.
        write_rollout(codex_home, ["gpt:5.6-sol"])
    if setup == "non-unique-rollout":
        write_rollout(codex_home, ["gpt-5.6-sol"])
        write_rollout(
            codex_home / "sessions" / "2026" / "08" / "05" / "other",
            ["gpt-5.6-sol"],
        )
    if setup == "invalid-json":
        write_rollout(codex_home, ["gpt-5.6-sol"]).write_text("this is not json\n", encoding="utf-8")

    with pytest.raises(workspace.WorkspaceError, match=message):
        workspace.resolve_codex_model_name()


def test_resolve_codex_model_name_replaces_whitespace_with_hyphen(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    codex_home = tmp_path / "codex"
    write_rollout(codex_home, ["Cursor Grok 4.6"])
    monkeypatch.setenv("CODEX_HOME", str(codex_home))
    monkeypatch.setenv("CODEX_THREAD_ID", THREAD_ID)

    assert workspace.resolve_codex_model_name() == "Cursor-Grok-4.6"


def test_resolve_codex_model_name_replaces_slash_with_hyphen(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    codex_home = tmp_path / "codex"
    write_rollout(codex_home, ["opencode/deepseek-v4-flash-free"])
    monkeypatch.setenv("CODEX_HOME", str(codex_home))
    monkeypatch.setenv("CODEX_THREAD_ID", THREAD_ID)

    assert workspace.resolve_codex_model_name() == "opencode-deepseek-v4-flash-free"


def test_resolve_codex_model_name_ignores_unterminated_partial_tail(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    codex_home = tmp_path / "codex"
    complete = json.dumps({"type": "turn_context", "payload": {"model": "gpt-5.6-sol"}})
    write_rollout_text(codex_home, complete + '\n{"type":"event_msg"')
    monkeypatch.setenv("CODEX_HOME", str(codex_home))
    monkeypatch.setenv("CODEX_THREAD_ID", THREAD_ID)

    assert workspace.resolve_codex_model_name() == "gpt-5.6-sol"


@pytest.mark.parametrize(
    "unexpected_record",
    [
        123,
        ["turn_context"],
        {"type": "turn_context", "payload": None},
        {"type": "turn_context", "payload": []},
        {"type": "turn_context", "payload": {"model": None}},
    ],
)
def test_resolve_codex_model_name_skips_records_outside_expected_schema(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    unexpected_record: object,
) -> None:
    codex_home = tmp_path / "codex"
    lines = [
        json.dumps(unexpected_record),
        json.dumps({"type": "turn_context", "payload": {"model": "gpt-5.6-sol"}}),
    ]
    write_rollout_text(codex_home, "\n".join(lines) + "\n")
    monkeypatch.setenv("CODEX_HOME", str(codex_home))
    monkeypatch.setenv("CODEX_THREAD_ID", THREAD_ID)

    assert workspace.resolve_codex_model_name() == "gpt-5.6-sol"


def test_resolve_codex_model_name_rejects_malformed_completed_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    codex_home = tmp_path / "codex"
    write_rollout_text(
        codex_home,
        '{"type":"turn_context","payload":{"model":"gpt-5.6-sol"}}\nnot-json\n',
    )
    monkeypatch.setenv("CODEX_HOME", str(codex_home))
    monkeypatch.setenv("CODEX_THREAD_ID", THREAD_ID)

    with pytest.raises(workspace.WorkspaceError, match="invalid rollout JSON at line 2"):
        workspace.resolve_codex_model_name()


def test_resolve_runtime_model_name_uses_explicit_name_outside_codex() -> None:
    assert workspace.resolve_runtime_model_name("opus-5", {}) == (
        "opus-5",
        "explicit",
    )


def test_resolve_runtime_model_name_replaces_slash_with_hyphen() -> None:
    assert workspace.resolve_runtime_model_name("opencode/deepseek-v4-flash-free", {}) == (
        "opencode-deepseek-v4-flash-free",
        "explicit",
    )


def test_resolve_runtime_model_name_replaces_whitespace_with_hyphen() -> None:
    assert workspace.resolve_runtime_model_name("Cursor Grok 4.6", {}) == (
        "Cursor-Grok-4.6",
        "explicit",
    )


@pytest.mark.parametrize(
    ("model_name", "message"),
    [
        (None, "model name is required outside Codex"),
        ("opus:5", "safe filename"),
        ("../evil", "safe filename"),
        (" Composer", "safe filename"),
        ("Composer ", "safe filename"),
    ],
)
def test_resolve_runtime_model_name_fails_closed_outside_codex(
    model_name: str | None,
    message: str,
) -> None:
    with pytest.raises(workspace.WorkspaceError, match=message):
        workspace.resolve_runtime_model_name(model_name, {})


def test_resolve_runtime_model_name_rejects_codex_override(tmp_path: Path) -> None:
    codex_home = tmp_path / "codex"
    write_rollout(codex_home, ["gpt-5.6-sol"])
    environ = {
        "CODEX_HOME": str(codex_home),
        "CODEX_THREAD_ID": THREAD_ID,
    }

    with pytest.raises(workspace.WorkspaceError, match="does not match Codex runtime"):
        workspace.resolve_runtime_model_name("gpt-5", environ)


def test_resolve_runtime_model_name_accepts_slash_equivalent_explicit_in_codex(
    tmp_path: Path,
) -> None:
    codex_home = tmp_path / "codex"
    write_rollout(codex_home, ["opencode/deepseek-v4-flash-free"])
    environ = {
        "CODEX_HOME": str(codex_home),
        "CODEX_THREAD_ID": THREAD_ID,
    }

    assert workspace.resolve_runtime_model_name("opencode/deepseek-v4-flash-free", environ) == (
        "opencode-deepseek-v4-flash-free",
        "codex-rollout",
    )


def test_review_artifact_paths_preserve_exact_model_name(tmp_path: Path) -> None:
    draft, destination = workspace.review_artifact_paths(
        tmp_path / "review-backup",
        "fix/herdr-session-cwd",
        "gpt-5.6-sol",
        pr_number=4,
    )

    assert draft == tmp_path / "review-backup" / "gpt-5.6-sol.md"
    assert destination == "reviews/#4-fix-herdr-session-cwd/gpt-5.6-sol.md"


def test_destination_fingerprint_distinguishes_symlink_entries(tmp_path: Path) -> None:
    target = tmp_path / "target.md"
    target.write_text("review\n", encoding="utf-8")
    link = tmp_path / "link.md"
    link.symlink_to(target.name)
    dangling = tmp_path / "dangling.md"
    dangling.symlink_to("missing.md")

    target_fingerprint = workspace.destination_fingerprint(target)
    link_fingerprint = workspace.destination_fingerprint(link)
    dangling_fingerprint = workspace.destination_fingerprint(dangling)

    assert target_fingerprint["kind"] == "file"
    assert link_fingerprint["kind"] == "symlink"
    assert dangling_fingerprint["kind"] == "symlink"
    assert link_fingerprint["sha256"] != dangling_fingerprint["sha256"]


def test_snapshot_existing_review_copies_regular_file(tmp_path: Path) -> None:
    backup_dir = tmp_path / "review-backup"
    backup_dir.mkdir()
    destination = tmp_path / "reviews/branch/gpt-5.6-sol.md"
    destination.parent.mkdir(parents=True)
    destination.write_text("existing review\n", encoding="utf-8")

    fingerprint, previous = workspace.snapshot_existing_review(destination, backup_dir)

    assert fingerprint == workspace.destination_fingerprint(destination)
    assert previous == backup_dir / "previous-review.md"
    assert previous.read_text(encoding="utf-8") == "existing review\n"


def test_snapshot_existing_review_reports_missing(tmp_path: Path) -> None:
    backup_dir = tmp_path / "review-backup"
    backup_dir.mkdir()
    destination = tmp_path / "reviews/branch/gpt-5.6-sol.md"

    fingerprint, previous = workspace.snapshot_existing_review(destination, backup_dir)

    assert fingerprint == {"path": str(destination), "kind": "missing"}
    assert previous is None
    assert list(backup_dir.iterdir()) == []


@pytest.mark.parametrize("kind", ["directory", "symlink", "fifo"])
def test_snapshot_existing_review_rejects_non_regular(tmp_path: Path, kind: str) -> None:
    backup_dir = tmp_path / "review-backup"
    backup_dir.mkdir()
    destination = tmp_path / "reviews/branch/gpt-5.6-sol.md"
    destination.parent.mkdir(parents=True)
    if kind == "directory":
        destination.mkdir()
    elif kind == "symlink":
        target = tmp_path / "other-model.md"
        target.write_text("must not be read\n", encoding="utf-8")
        destination.symlink_to(target)
    else:
        os.mkfifo(destination)

    with pytest.raises(
        workspace.WorkspaceError,
        match="existing review destination must be a regular file",
    ):
        workspace.snapshot_existing_review(destination, backup_dir)
    assert list(backup_dir.iterdir()) == []


def test_snapshot_existing_review_rejects_source_race(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    backup_dir = tmp_path / "review-backup"
    backup_dir.mkdir()
    destination = tmp_path / "reviews/branch/gpt-5.6-sol.md"
    destination.parent.mkdir(parents=True)
    destination.write_text("existing review\n", encoding="utf-8")
    original = workspace.destination_fingerprint
    calls = 0

    def changing(path: Path) -> dict[str, str]:
        nonlocal calls
        result = original(path)
        if path == destination:
            calls += 1
            if calls == 2:
                return {**result, "sha256": "0" * 64}
        return result

    monkeypatch.setattr(workspace, "destination_fingerprint", changing)
    with pytest.raises(
        workspace.WorkspaceError,
        match="existing review changed while snapshotting",
    ):
        workspace.snapshot_existing_review(destination, backup_dir)
    assert not (backup_dir / "previous-review.md").exists()


def test_atomic_copy_replaces_internal_destination_symlink_entry(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    branch_dir = repo / "reviews" / "branch"
    branch_dir.mkdir(parents=True)
    target = branch_dir / "actual.md"
    target.write_text("old target\n", encoding="utf-8")
    link = branch_dir / "model.md"
    link.symlink_to(target.name)
    draft = tmp_path / "draft.md"
    draft.write_text("new review\n", encoding="utf-8")

    destination = workspace.safe_destination(repo, "reviews/branch/model.md")
    assert destination == link

    workspace.atomic_copy(draft, destination)

    assert not destination.is_symlink()
    assert destination.read_text(encoding="utf-8") == "new review\n"
    assert target.read_text(encoding="utf-8") == "old target\n"


def test_safe_destination_rejects_symlink_escape(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    reviews = repo / "reviews"
    outside = repo / "outside"
    reviews.mkdir(parents=True)
    outside.mkdir()
    (reviews / "branch").symlink_to(outside, target_is_directory=True)

    with pytest.raises(workspace.WorkspaceError, match="escapes"):
        workspace.safe_destination(repo, "reviews/branch/model.md")


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def make_repo(path: Path, *, tracked_reviews: bool = True) -> str:
    path.mkdir()
    subprocess.run(["git", "init", "-b", "main", str(path)], check=True, capture_output=True)
    git(path, "config", "user.name", "Test User")
    git(path, "config", "user.email", "test@example.com")
    (path / "README.md").write_text("fixture\n", encoding="utf-8")
    git(path, "add", "README.md")
    if tracked_reviews:
        old_review = path / "reviews" / "#4-fix-herdr-session-cwd" / "gpt-5.md"
        old_review.parent.mkdir(parents=True)
        old_review.write_text("existing alias\n", encoding="utf-8")
        git(path, "add", "reviews/#4-fix-herdr-session-cwd/gpt-5.md")
    git(path, "commit", "-m", "fixture")
    return git(path, "rev-parse", "HEAD")


def test_snapshot_does_not_refresh_index(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GIT_OPTIONAL_LOCKS", "1")
    repo = tmp_path / "repo"
    commit = make_repo(repo)
    readme = repo / "README.md"
    stat = readme.stat()
    os.utime(readme, ns=(stat.st_atime_ns, stat.st_mtime_ns + 2_000_000_000))
    index = repo / ".git" / "index"
    before = index.read_bytes(), index.stat().st_mtime_ns

    assert workspace.snapshot(repo) == {"branch": "main", "head": commit, "status": ""}

    assert (index.read_bytes(), index.stat().st_mtime_ns) == before
    assert not (repo / ".git" / "index.lock").exists()


def test_snapshot_preserves_existing_index_lock(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    commit = make_repo(repo)
    lock = repo / ".git" / "index.lock"
    lock.write_bytes(b"another process owns this lock\n")
    before = lock.read_bytes(), lock.stat().st_mtime_ns, lock.stat().st_ino

    assert workspace.snapshot(repo) == {"branch": "main", "head": commit, "status": ""}

    assert (lock.read_bytes(), lock.stat().st_mtime_ns, lock.stat().st_ino) == before


@pytest.mark.parametrize(
    ("change", "expected_status"),
    [
        ("staged", b"M  README.md\0"),
        ("unstaged", b" M README.md\0"),
        ("both", b"MM README.md\0"),
        ("untracked", b"?? notes.txt\0?? scratch/\0"),
    ],
)
def test_snapshot_reports_changes_excluding_reviews(
    tmp_path: Path,
    change: str,
    expected_status: bytes,
) -> None:
    repo = tmp_path / "repo"
    commit = make_repo(repo)
    readme = repo / "README.md"
    if change in {"staged", "both"}:
        readme.write_text("staged change\n", encoding="utf-8")
        git(repo, "add", "README.md")
    if change in {"unstaged", "both"}:
        readme.write_text("unstaged change\n", encoding="utf-8")
    if change == "untracked":
        (repo / "notes.txt").write_text("notes\n", encoding="utf-8")
        (repo / "scratch").mkdir()
        (repo / "scratch" / "notes.txt").write_text("nested notes\n", encoding="utf-8")
    reviews = repo / "reviews" / "#4-fix-herdr-session-cwd"
    (reviews / "gpt-5.md").write_text("changed review\n", encoding="utf-8")
    (reviews / "new-model.md").write_text("new review\n", encoding="utf-8")

    result = workspace.snapshot(repo)

    assert result["branch"] == "main"
    assert result["head"] == commit
    assert base64.b64decode(result["status"]) == expected_status


def test_create_requires_explicit_model_outside_codex(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CODEX_THREAD_ID", raising=False)
    monkeypatch.delenv("CODEX_HOME", raising=False)
    temp_root = tmp_path / "sessions"

    with pytest.raises(workspace.WorkspaceError, match="required outside Codex"):
        workspace.create(
            argparse.Namespace(
                repo=str(tmp_path / "unused-repo"),
                pr_number=5,
                commit="unused-commit",
                head_branch="fix/model-name",
                model_name=None,
                temp_root=str(temp_root),
                attempt_id=attempt_id(),
            )
        )

    assert not temp_root.exists()


def test_create_pins_slash_model_name_as_hyphenated_filename(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CODEX_THREAD_ID", raising=False)
    monkeypatch.delenv("CODEX_HOME", raising=False)
    repo = tmp_path / "repo"
    commit = make_repo(repo)

    result = workspace.create(
        argparse.Namespace(
            repo=str(repo),
            pr_number=42,
            commit=commit,
            head_branch="fix/model-name",
            model_name="opencode/deepseek-v4-flash-free",
            temp_root=str(tmp_path / "sessions"),
            attempt_id=attempt_id(),
        )
    )

    assert result["model_name"] == "opencode-deepseek-v4-flash-free"
    assert result["destination"] == "reviews/#42-fix-model-name/opencode-deepseek-v4-flash-free.md"
    assert result["draft"].endswith("/opencode-deepseek-v4-flash-free.md")


def test_create_destination_uses_hash_pr_number_and_sanitized_branch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("CODEX_THREAD_ID", raising=False)
    monkeypatch.delenv("CODEX_HOME", raising=False)
    repo = tmp_path / "repo"
    commit = make_repo(repo, tracked_reviews=False)

    result = workspace.create(
        argparse.Namespace(
            repo=str(repo),
            pr_number=160,
            commit=commit,
            head_branch="feature/issue-148-fail-fast",
            model_name="grok-4.6",
            temp_root=str(tmp_path / "sessions"),
            attempt_id=attempt_id(),
        )
    )

    assert result["destination"] == "reviews/#160-feature-issue-148-fail-fast/grok-4.6.md"


@pytest.mark.parametrize(
    ("head_branch", "directory"),
    [
        ("feature/foo:bar", "#7-feature-foo-bar"),
        (r"win\path", "#7-win-path"),
        ('a<>:"|?*b', "#7-a-------b"),
        ("ends-with-dot.", "#7-ends-with-dot"),
        ("trailing-space ", "#7-trailing-space"),
        ("has space", "#7-has space"),
        ("foo\nbar", "#7-foo-bar"),
    ],
)
def test_create_destination_replaces_unsafe_directory_characters(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    head_branch: str,
    directory: str,
) -> None:
    monkeypatch.delenv("CODEX_THREAD_ID", raising=False)
    monkeypatch.delenv("CODEX_HOME", raising=False)
    repo = tmp_path / "repo"
    commit = make_repo(repo, tracked_reviews=False)

    result = workspace.create(
        argparse.Namespace(
            repo=str(repo),
            pr_number=7,
            commit=commit,
            head_branch=head_branch,
            model_name="grok-4.6",
            temp_root=str(tmp_path / "sessions"),
            attempt_id=attempt_id(),
        )
    )

    assert result["destination"] == f"reviews/{directory}/grok-4.6.md"


def test_create_pins_explicit_model_outside_codex(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CODEX_THREAD_ID", raising=False)
    monkeypatch.delenv("CODEX_HOME", raising=False)
    repo = tmp_path / "repo"
    commit = make_repo(repo)

    result = workspace.create(
        argparse.Namespace(
            repo=str(repo),
            pr_number=5,
            commit=commit,
            head_branch="fix/model-name",
            model_name="opus-5",
            temp_root=str(tmp_path / "sessions"),
            attempt_id=attempt_id(),
        )
    )

    state = json.loads(Path(result["state_file"]).read_text(encoding="utf-8"))
    assert result["model_name"] == "opus-5"
    assert result["model_source"] == "explicit"
    assert result["destination"] == "reviews/#5-fix-model-name/opus-5.md"
    assert state["model_source"] == "explicit"


def test_save_uses_pinned_explicit_model_without_codex_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("CODEX_THREAD_ID", raising=False)
    monkeypatch.delenv("CODEX_HOME", raising=False)
    repo = tmp_path / "repo-save"
    commit = make_repo(repo)
    result = workspace.create(
        argparse.Namespace(
            repo=str(repo),
            pr_number=5,
            commit=commit,
            head_branch="fix/model-name",
            model_name="opus-5",
            temp_root=str(tmp_path / "save-sessions"),
            attempt_id=attempt_id(),
        )
    )
    Path(result["draft"]).write_text("review\n", encoding="utf-8")

    saved = workspace.save(argparse.Namespace(state=result["state_file"]))

    assert saved["destination"].endswith("/reviews/#5-fix-model-name/opus-5.md")
    assert Path(saved["destination"]).read_text(encoding="utf-8") == "review\n"


def test_save_rejects_unknown_model_source(created_session: dict[str, Any]) -> None:
    result = created_session["result"]
    state_file = Path(result["state_file"])
    state = json.loads(state_file.read_text(encoding="utf-8"))
    state["model_source"] = "unknown"
    state_file.write_text(json.dumps(state) + "\n", encoding="utf-8")

    with pytest.raises(workspace.WorkspaceError, match="invalid PR-review session state"):
        workspace.save(argparse.Namespace(state=str(state_file)))


def test_create_pins_model_and_artifact_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    codex_home = tmp_path / "codex"
    write_rollout(codex_home, ["gpt-5.6-sol"])
    monkeypatch.setenv("CODEX_HOME", str(codex_home))
    monkeypatch.setenv("CODEX_THREAD_ID", THREAD_ID)
    repo = tmp_path / "repo"
    commit = make_repo(repo)

    result = workspace.create(
        argparse.Namespace(
            repo=str(repo),
            pr_number=4,
            commit=commit,
            head_branch="fix/herdr-session-cwd",
            model_name=None,
            temp_root=str(tmp_path / "sessions"),
            attempt_id=attempt_id(),
        )
    )

    assert result["model_name"] == "gpt-5.6-sol"
    assert result["destination"] == "reviews/#4-fix-herdr-session-cwd/gpt-5.6-sol.md"
    assert Path(result["draft"]).name == "gpt-5.6-sol.md"
    assert (repo / "reviews/#4-fix-herdr-session-cwd/gpt-5.md").read_text(encoding="utf-8") == "existing alias\n"
    state = json.loads(Path(result["state_file"]).read_text(encoding="utf-8"))
    assert result["previous_review"] is None
    assert state["previous_review"] is None
    assert state["model_source"] == "codex-rollout"
    assert result["model_source"] == "codex-rollout"
    assert state["head_branch"] == "fix/herdr-session-cwd"
    assert state["model_name"] == "gpt-5.6-sol"
    assert state["draft"] == result["draft"]
    assert state["destination"] == result["destination"]


def test_create_pins_existing_review_snapshot(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    codex_home = tmp_path / "codex"
    write_rollout(codex_home, ["gpt-5.6-sol"])
    monkeypatch.setenv("CODEX_HOME", str(codex_home))
    monkeypatch.setenv("CODEX_THREAD_ID", THREAD_ID)
    repo = tmp_path / "repo"
    commit = make_repo(repo)
    own_review = repo / "reviews/#4-fix-herdr-session-cwd/gpt-5.6-sol.md"
    own_review.write_text("own existing review\n", encoding="utf-8")

    result = workspace.create(
        argparse.Namespace(
            repo=str(repo),
            pr_number=4,
            commit=commit,
            head_branch="fix/herdr-session-cwd",
            model_name=None,
            temp_root=str(tmp_path / "sessions"),
            attempt_id=attempt_id(),
        )
    )

    previous = Path(str(result["previous_review"]))
    state = json.loads(Path(result["state_file"]).read_text(encoding="utf-8"))
    assert previous.name == "previous-review.md"
    assert previous.read_text(encoding="utf-8") == "own existing review\n"
    assert state["previous_review"] == str(previous)
    assert state["destination_fingerprint"] == workspace.destination_fingerprint(own_review)


def test_load_state_rejects_tampered_previous_review(
    created_session: dict[str, Any],
) -> None:
    state_file = Path(created_session["result"]["state_file"])
    state = json.loads(state_file.read_text(encoding="utf-8"))
    outside = state_file.parent.parent / "another-review.md"
    outside.write_text("outside session\n", encoding="utf-8")
    state["previous_review"] = str(outside)
    state_file.write_text(json.dumps(state) + "\n", encoding="utf-8")

    with pytest.raises(
        workspace.WorkspaceError,
        match="previous review snapshot does not match its session",
    ):
        workspace.load_state(str(state_file))


@pytest.mark.parametrize("head_branch", ["", "/", ".", "..", "..."])
def test_review_artifact_paths_reject_invalid_branch(tmp_path: Path, head_branch: str) -> None:
    with pytest.raises(workspace.WorkspaceError, match="head branch"):
        workspace.review_artifact_paths(tmp_path, head_branch, "gpt-5.6-sol", pr_number=1)


@pytest.mark.parametrize("pr_number", [0, -1, True, "160"])
def test_review_artifact_paths_reject_invalid_pr_number(tmp_path: Path, pr_number: object) -> None:
    with pytest.raises(workspace.WorkspaceError, match="PR number"):
        workspace.review_artifact_paths(
            tmp_path,
            "feature/ok",
            "gpt-5.6-sol",
            pr_number=pr_number,  # type: ignore[arg-type]
        )


def test_save_parser_rejects_caller_selected_paths() -> None:
    with pytest.raises(SystemExit):
        workspace.parser().parse_args(
            [
                "save",
                "--state",
                "/tmp/session.json",
                "--draft",
                "/tmp/gpt-5.md",
                "--destination",
                "reviews/branch/gpt-5.md",
            ]
        )


def test_create_parser_accepts_explicit_model_name() -> None:
    args = workspace.parser().parse_args(
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
            "--attempt-id",
            "20261005T121530123456789Z",
        ]
    )

    assert args.model_name == "opus-5"


def create_session(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    tracked_reviews: bool = True,
) -> dict[str, Any]:
    codex_home = tmp_path / "codex"
    write_rollout(codex_home, ["gpt-5.6-sol"])
    monkeypatch.setenv("CODEX_HOME", str(codex_home))
    monkeypatch.setenv("CODEX_THREAD_ID", THREAD_ID)
    repo = tmp_path / "repo"
    commit = make_repo(repo, tracked_reviews=tracked_reviews)
    result = workspace.create(
        argparse.Namespace(
            repo=str(repo),
            pr_number=4,
            commit=commit,
            head_branch="fix/herdr-session-cwd",
            model_name=None,
            temp_root=str(tmp_path / "sessions"),
            attempt_id=attempt_id(),
        )
    )
    return {"result": result, "codex_home": codex_home, "repo": repo}


@pytest.fixture
def created_session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    return create_session(tmp_path, monkeypatch)


def test_save_uses_only_pinned_paths(created_session: dict[str, Any]) -> None:
    result = created_session["result"]
    draft = Path(result["draft"])
    draft.write_text("review\n", encoding="utf-8")

    saved = workspace.save(argparse.Namespace(state=result["state_file"]))

    assert saved["destination"].endswith("/reviews/#4-fix-herdr-session-cwd/gpt-5.6-sol.md")
    assert Path(saved["destination"]).read_text(encoding="utf-8") == "review\n"


def test_save_allows_another_review_destination_to_change(
    created_session: dict[str, Any],
) -> None:
    result = created_session["result"]
    repo = created_session["repo"]
    Path(result["draft"]).write_text("codex review\n", encoding="utf-8")
    other = repo / "reviews/#4-fix-herdr-session-cwd/gemini-3.6-flash.md"
    other.write_text("gemini review\n", encoding="utf-8")

    saved = workspace.save(argparse.Namespace(state=result["state_file"]))

    assert Path(saved["destination"]).read_text(encoding="utf-8") == "codex review\n"
    assert other.read_text(encoding="utf-8") == "gemini review\n"


def test_save_allows_untracked_reviews_directory_to_appear(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    session = create_session(tmp_path, monkeypatch, tracked_reviews=False)
    result = session["result"]
    repo = session["repo"]
    Path(result["draft"]).write_text("codex review\n", encoding="utf-8")
    other = repo / "reviews" / "#4-fix-herdr-session-cwd" / "gemini.md"
    other.parent.mkdir(parents=True)
    other.write_text("gemini review\n", encoding="utf-8")
    assert git(repo, "status", "--porcelain") == "?? reviews/"

    saved = workspace.save(argparse.Namespace(state=result["state_file"]))

    assert Path(saved["destination"]).read_text(encoding="utf-8") == "codex review\n"
    assert other.read_text(encoding="utf-8") == "gemini review\n"


@pytest.mark.parametrize("collision", ["reviews", "branch"])
def test_save_rejects_non_directory_destination_parent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    collision: str,
) -> None:
    session = create_session(tmp_path, monkeypatch, tracked_reviews=False)
    result = session["result"]
    repo = session["repo"]
    Path(result["draft"]).write_text("review\n", encoding="utf-8")
    if collision == "reviews":
        (repo / "reviews").write_text("collision\n", encoding="utf-8")
    else:
        reviews = repo / "reviews"
        reviews.mkdir()
        (reviews / "#4-fix-herdr-session-cwd").write_text("collision\n", encoding="utf-8")

    with pytest.raises(
        workspace.WorkspaceError,
        match="review destination parent is not a directory",
    ):
        workspace.save(argparse.Namespace(state=result["state_file"]))


def test_save_rejects_changed_pinned_destination(
    created_session: dict[str, Any],
) -> None:
    result = created_session["result"]
    repo = created_session["repo"]
    Path(result["draft"]).write_text("new review\n", encoding="utf-8")
    destination = repo / result["destination"]
    destination.write_text("concurrent review\n", encoding="utf-8")

    with pytest.raises(workspace.WorkspaceError, match="review destination changed"):
        workspace.save(argparse.Namespace(state=result["state_file"]))

    assert destination.read_text(encoding="utf-8") == "concurrent review\n"


def test_first_session_wins_same_destination(
    created_session: dict[str, Any],
) -> None:
    first = created_session["result"]
    repo = created_session["repo"]
    commit = git(repo, "rev-parse", "HEAD")
    second = workspace.create(
        argparse.Namespace(
            repo=str(repo),
            pr_number=4,
            commit=commit,
            head_branch="fix/herdr-session-cwd",
            model_name=None,
            temp_root=str(Path(first["state_file"]).parents[1]),
            attempt_id=attempt_id(),
        )
    )
    Path(first["draft"]).write_text("first review\n", encoding="utf-8")
    Path(second["draft"]).write_text("second review\n", encoding="utf-8")

    workspace.save(argparse.Namespace(state=first["state_file"]))
    with pytest.raises(workspace.WorkspaceError, match="review destination changed"):
        workspace.save(argparse.Namespace(state=second["state_file"]))

    destination = repo / first["destination"]
    assert destination.read_text(encoding="utf-8") == "first review\n"


def test_save_allows_unrelated_main_changes(created_session: dict[str, Any]) -> None:
    result = created_session["result"]
    repo = created_session["repo"]
    Path(result["draft"]).write_text("review\n", encoding="utf-8")
    (repo / "README.md").write_text("changed\n", encoding="utf-8")
    scratch = repo / ".pr-review-scratch"
    scratch.mkdir()
    (scratch / "diff.txt").write_text("scratch\n", encoding="utf-8")

    saved = workspace.save(argparse.Namespace(state=result["state_file"]))

    assert Path(saved["destination"]).read_text(encoding="utf-8") == "review\n"


def test_load_state_rejects_previous_version(created_session: dict[str, Any]) -> None:
    state_file = Path(created_session["result"]["state_file"])
    state = json.loads(state_file.read_text(encoding="utf-8"))
    state["version"] = 5
    state_file.write_text(json.dumps(state) + "\n", encoding="utf-8")

    with pytest.raises(workspace.WorkspaceError, match="invalid PR-review session state"):
        workspace.load_state(str(state_file))


def test_save_rejects_changed_runtime_model(created_session: dict[str, Any]) -> None:
    result = created_session["result"]
    codex_home = created_session["codex_home"]
    Path(result["draft"]).write_text("review\n", encoding="utf-8")
    write_rollout(codex_home, ["gpt-5.6-sol", "gpt-5"])

    with pytest.raises(workspace.WorkspaceError, match="runtime model changed"):
        workspace.save(argparse.Namespace(state=result["state_file"]))


def test_save_rejects_tampered_destination(created_session: dict[str, Any]) -> None:
    result = created_session["result"]
    state_file = Path(result["state_file"])
    state = json.loads(state_file.read_text(encoding="utf-8"))
    state["destination"] = "reviews/#4-fix-herdr-session-cwd/gpt-5.md"
    state_file.write_text(json.dumps(state) + "\n", encoding="utf-8")

    with pytest.raises(workspace.WorkspaceError, match="destination does not match"):
        workspace.save(argparse.Namespace(state=str(state_file)))


def test_save_waits_for_repository_review_lock(
    created_session: dict[str, Any],
) -> None:
    result = created_session["result"]
    repo = created_session["repo"]
    Path(result["draft"]).write_text("review\n", encoding="utf-8")
    destination = repo / result["destination"]

    with workspace.review_save_lock(repo):
        process = subprocess.Popen(
            [sys.executable, str(SCRIPT), "save", "--state", result["state_file"]],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=os.environ.copy(),
        )
        with pytest.raises(subprocess.TimeoutExpired):
            process.wait(timeout=1)
        assert not destination.exists()

    stdout, stderr = process.communicate(timeout=5)
    assert process.returncode == 0, stderr
    assert json.loads(stdout)["destination"] == str(destination)
    assert destination.read_text(encoding="utf-8") == "review\n"


def saved_session(session: dict[str, Any], body: str = "review\n") -> dict[str, str]:
    result = session["result"]
    Path(result["draft"]).write_text(body, encoding="utf-8")
    return workspace.save(argparse.Namespace(state=result["state_file"]))


def test_cleanup_removes_session_after_successful_save(
    created_session: dict[str, Any],
) -> None:
    result = created_session["result"]
    repo = created_session["repo"]
    session_dir = Path(result["state_file"]).parent
    saved = saved_session(created_session)

    removed = workspace.cleanup(argparse.Namespace(state=result["state_file"]))

    assert removed["session_dir"] == str(session_dir)
    assert removed["destination"] == saved["destination"]
    assert not session_dir.exists()
    assert result["worktree"] not in git(repo, "worktree", "list")
    assert Path(saved["destination"]).read_text(encoding="utf-8") == "review\n"


def test_cleanup_removes_worktree_holding_verification_artifacts(
    created_session: dict[str, Any],
) -> None:
    result = created_session["result"]
    repo = created_session["repo"]
    worktree = Path(result["worktree"])
    build = worktree / "_build"
    build.mkdir()
    (build / "pytest.log").write_text("verification output\n", encoding="utf-8")
    (worktree / "README.md").write_text("edited during review\n", encoding="utf-8")
    saved_session(created_session)

    workspace.cleanup(argparse.Namespace(state=result["state_file"]))

    assert not worktree.exists()
    assert result["worktree"] not in git(repo, "worktree", "list")


def test_cleanup_refuses_before_save(created_session: dict[str, Any]) -> None:
    result = created_session["result"]
    repo = created_session["repo"]
    session_dir = Path(result["state_file"]).parent
    Path(result["draft"]).write_text("review\n", encoding="utf-8")

    with pytest.raises(workspace.WorkspaceError, match="not saved"):
        workspace.cleanup(argparse.Namespace(state=result["state_file"]))

    assert session_dir.is_dir()
    assert Path(result["worktree"]).is_dir()
    assert result["worktree"] in git(repo, "worktree", "list")
    assert not (repo / result["destination"]).exists()


def test_cleanup_refuses_when_destination_diverges_from_draft(
    created_session: dict[str, Any],
) -> None:
    result = created_session["result"]
    repo = created_session["repo"]
    session_dir = Path(result["state_file"]).parent
    saved = saved_session(created_session)
    Path(saved["destination"]).write_text("hand edited\n", encoding="utf-8")

    with pytest.raises(workspace.WorkspaceError, match="not saved"):
        workspace.cleanup(argparse.Namespace(state=result["state_file"]))

    assert session_dir.is_dir()
    assert result["worktree"] in git(repo, "worktree", "list")
    assert Path(saved["destination"]).read_text(encoding="utf-8") == "hand edited\n"


def test_cleanup_keeps_other_worktrees_and_main_checkout(tmp_path: Path, created_session: dict[str, Any]) -> None:
    result = created_session["result"]
    repo = created_session["repo"]
    other = tmp_path / "unrelated-worktree"
    git(repo, "worktree", "add", "--detach", str(other), "HEAD")
    other_review = repo / "reviews/#4-fix-herdr-session-cwd/gemini-3.6-flash.md"
    other_review.parent.mkdir(parents=True, exist_ok=True)
    other_review.write_text("gemini review\n", encoding="utf-8")
    saved_session(created_session)

    workspace.cleanup(argparse.Namespace(state=result["state_file"]))

    assert other.is_dir()
    assert str(other) in git(repo, "worktree", "list")
    assert (repo / "README.md").read_text(encoding="utf-8") == "fixture\n"
    assert other_review.read_text(encoding="utf-8") == "gemini review\n"


def test_cleanup_refuses_when_session_path_is_not_its_worktree(
    created_session: dict[str, Any],
) -> None:
    result = created_session["result"]
    repo = created_session["repo"]
    worktree = Path(result["worktree"])
    saved_session(created_session)
    git(repo, "worktree", "remove", "--force", str(worktree))
    worktree.mkdir()
    (worktree / "precious.txt").write_text("not a worktree\n", encoding="utf-8")

    with pytest.raises(workspace.WorkspaceError, match="linked worktree"):
        workspace.cleanup(argparse.Namespace(state=result["state_file"]))

    assert (worktree / "precious.txt").is_file()
    assert Path(result["state_file"]).is_file()


def test_cleanup_refuses_worktree_of_another_repository(tmp_path: Path, created_session: dict[str, Any]) -> None:
    result = created_session["result"]
    repo = created_session["repo"]
    worktree = Path(result["worktree"])
    saved_session(created_session)
    git(repo, "worktree", "remove", "--force", str(worktree))
    stranger = tmp_path / "stranger"
    stranger_commit = make_repo(stranger, tracked_reviews=False)
    git(stranger, "worktree", "add", "--detach", str(worktree), stranger_commit)

    with pytest.raises(workspace.WorkspaceError, match="linked worktree"):
        workspace.cleanup(argparse.Namespace(state=result["state_file"]))

    assert worktree.is_dir()
    assert str(worktree) in git(stranger, "worktree", "list")


def test_cleanup_fails_closed_when_rerun(created_session: dict[str, Any]) -> None:
    result = created_session["result"]
    saved = saved_session(created_session)
    workspace.cleanup(argparse.Namespace(state=result["state_file"]))

    with pytest.raises((workspace.WorkspaceError, OSError)):
        workspace.cleanup(argparse.Namespace(state=result["state_file"]))

    assert Path(saved["destination"]).read_text(encoding="utf-8") == "review\n"


def test_cleanup_parser_rejects_caller_selected_paths() -> None:
    with pytest.raises(SystemExit):
        workspace.parser().parse_args(
            [
                "cleanup",
                "--state",
                "/tmp/session.json",
                "--worktree",
                "/tmp/pr-review-4-abcd/worktree",
            ]
        )


def test_cleanup_waits_for_repository_review_lock(
    created_session: dict[str, Any],
) -> None:
    result = created_session["result"]
    repo = created_session["repo"]
    session_dir = Path(result["state_file"]).parent
    saved_session(created_session)

    with workspace.review_save_lock(repo):
        process = subprocess.Popen(
            [sys.executable, str(SCRIPT), "cleanup", "--state", result["state_file"]],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=os.environ.copy(),
        )
        with pytest.raises(subprocess.TimeoutExpired):
            process.wait(timeout=1)
        assert session_dir.is_dir()

    stdout, stderr = process.communicate(timeout=10)
    assert process.returncode == 0, stderr
    assert json.loads(stdout)["session_dir"] == str(session_dir)
    assert not session_dir.exists()


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

    result = workspace.create(
        explicit_create_args(repo, commit, tmp_path / "sessions", attempt_id(), model_name="gpt-5")
    )

    assert result["previous_review"] is not None
    assert Path(result["state_file"]).is_file()


def test_create_outlives_a_reader_that_closed_its_stderr(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # A tool that stops reading after its timeout must not turn the attempt
    # into a helper error, which the skill stops on without abandoning it.
    monkeypatch.delenv("CODEX_THREAD_ID", raising=False)
    repo = tmp_path / "repo"
    commit = make_repo(repo)

    class ClosedPipe:
        def write(self, _text: str) -> int:
            raise BrokenPipeError(32, "Broken pipe")

        def flush(self) -> None:
            raise BrokenPipeError(32, "Broken pipe")

    monkeypatch.setattr(workspace.sys, "stderr", ClosedPipe())

    result = workspace.create(explicit_create_args(repo, commit, tmp_path / "sessions", attempt_id()))

    assert journal_records(Path(result["state_file"]).parent)[-1]["phase"] == "completed"


def attempt_args(repo: Path, temp_root: Path, attempt: str, *, wait: int = 0) -> argparse.Namespace:
    return argparse.Namespace(repo=str(repo), pr_number=4, attempt_id=attempt, temp_root=str(temp_root), wait=wait)


def stalling_git_env(tmp_path: Path) -> dict[str, str]:
    """Run git normally, but keep `git worktree add` alive after it finishes."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    real_git = shutil.which("git")
    assert real_git is not None
    wrapper = bin_dir / "git"
    pid_file = tmp_path / "stalled-git.pid"
    wrapper.write_text(
        f'#!/bin/sh\n"{real_git}" "$@" || exit $?\n'
        f'case " $* " in *" worktree add "*) echo $$ > "{pid_file}"; exec sleep 60 ;; esac\n',
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


def kill_stalled_git(tmp_path: Path) -> None:
    pid_file = tmp_path / "stalled-git.pid"
    if pid_file.is_file():
        with contextlib.suppress(ProcessLookupError):
            os.kill(int(pid_file.read_text(encoding="utf-8")), signal.SIGKILL)


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
        kill_group(process.pid, signal.SIGKILL)
        _, stderr = process.communicate(timeout=10)
        # `git worktree add` runs in its own session, so the group kill spares it.
        checkout_alive = workspace.inspect_attempt(attempt_args(repo, temp_root, attempt))
    finally:
        kill_group(process.pid, signal.SIGKILL)
        kill_stalled_git(tmp_path)

    report = workspace.inspect_attempt(attempt_args(repo, temp_root, attempt, wait=10))

    assert running["status"] == "running"
    assert process.returncode == -signal.SIGKILL
    assert checkout_alive["status"] == "running"
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
        _, stderr = process.communicate(timeout=10)

    report = workspace.inspect_attempt(attempt_args(repo, temp_root, attempt, wait=10))

    assert process.returncode == 128 + signal.SIGTERM
    # The skill reads an `error:` line as a helper error and would not abandon.
    assert not [line for line in stderr.splitlines() if line.startswith("error:")]
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
        kill_stalled_git(tmp_path)

    assert orphaned["status"] == "running"
    assert workspace.inspect_attempt(attempt_args(repo, temp_root, attempt, wait=10))["status"] == "vanished"
    assert workspace.abandon_attempt(attempt_args(repo, temp_root, attempt))["worktree_removed"] is True


def test_abandon_removes_a_worktree_left_initializing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    attempt = completed_attempt(tmp_path, monkeypatch)
    repo = attempt["repo"]
    worktree = attempt["result"]["worktree"]
    git(repo, "worktree", "lock", "--reason", "initializing", worktree)
    assert (
        workspace.inspect_attempt(attempt_args(repo, attempt["temp_root"], attempt["attempt"]))["worktree_lock"]
        == "initializing"
    )

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


def admin_dir_of(worktree: Path) -> Path:
    return Path((worktree / ".git").read_text(encoding="utf-8").strip().removeprefix("gitdir: "))


@pytest.mark.parametrize("cut", ["gitdir", "HEAD", "record"])
def test_abandon_clears_records_left_by_an_interrupted_worktree_add(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, cut: str
) -> None:
    # A SIGTERM that reaches `git worktree add` starts git's own cleanup; a
    # SIGKILL right after cuts it short and leaves records git cannot remove.
    attempt = completed_attempt(tmp_path, monkeypatch)
    repo = attempt["repo"]
    worktree = Path(attempt["result"]["worktree"])
    admin = admin_dir_of(worktree)
    other = tmp_path / "unrelated-worktree"
    git(repo, "worktree", "add", "--detach", str(other), "HEAD")
    (admin / "locked").write_text("initializing\n", encoding="utf-8")
    if cut == "record":
        shutil.rmtree(admin)
    elif cut == "gitdir":
        for name in ("gitdir", "HEAD", "commondir"):
            (admin / name).unlink()
    else:
        (admin / "HEAD").unlink()

    removed = workspace.abandon_attempt(attempt_args(repo, attempt["temp_root"], attempt["attempt"]))

    assert removed["worktree_removed"] is True
    assert not attempt["session_dir"].exists()
    assert not admin.exists()
    assert str(worktree) not in git(repo, "worktree", "list")
    assert other.is_dir()
    assert str(other) in git(repo, "worktree", "list")


def test_abandon_refuses_records_of_another_worktree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    mine = completed_attempt(tmp_path, monkeypatch)
    repo = mine["repo"]
    theirs = workspace.create(explicit_create_args(repo, mine["commit"], mine["temp_root"], attempt_id()))
    their_admin = admin_dir_of(Path(theirs["worktree"]))
    worktree = Path(mine["result"]["worktree"])
    git(repo, "worktree", "remove", "--force", str(worktree))
    worktree.mkdir()
    (worktree / ".git").write_text(f"gitdir: {their_admin}\n", encoding="utf-8")
    (worktree / "README.md").write_text("fixture\n", encoding="utf-8")

    with pytest.raises(workspace.WorkspaceError, match="another worktree"):
        workspace.abandon_attempt(attempt_args(repo, mine["temp_root"], mine["attempt"]))

    assert their_admin.is_dir()
    assert theirs["worktree"] in git(repo, "worktree", "list")
    assert (worktree / "README.md").is_file()


def test_a_repeated_signal_does_not_cut_the_end_record(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # `uv run` forwards SIGTERM to the helper that already got it from the
    # process group, so the second copy lands while create records the first.
    monkeypatch.delenv("CODEX_THREAD_ID", raising=False)
    repo = tmp_path / "repo"
    commit = make_repo(repo)
    temp_root = tmp_path / "sessions"
    attempt = attempt_id()
    snapshot = workspace.snapshot
    record_end = workspace.CreateJournal.record_end

    def terminated_snapshot(path: Path) -> dict[str, Any]:
        os.kill(os.getpid(), signal.SIGTERM)
        return snapshot(path)

    def record_end_after_another_signal(self: Any, phase: str, **fields: object) -> None:
        os.kill(os.getpid(), signal.SIGTERM)
        record_end(self, phase, **fields)

    monkeypatch.setattr(workspace, "snapshot", terminated_snapshot)
    monkeypatch.setattr(workspace.CreateJournal, "record_end", record_end_after_another_signal)

    with pytest.raises(workspace.CreateInterrupted):
        workspace.create(explicit_create_args(repo, commit, temp_root, attempt))

    report = workspace.inspect_attempt(attempt_args(repo, temp_root, attempt))
    assert report["status"] == "interrupted"
    assert report["signal"] == "SIGTERM"
