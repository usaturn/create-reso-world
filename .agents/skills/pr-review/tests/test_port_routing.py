"""Real-Git regressions for target routing, pinned identity and pair publication.

These tests catch origin-only routing, repository-less paths, truncated input,
unsafe reuse of a moving PR, and cleanup of refs owned by another session.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

SCRIPT = Path(__file__).parents[1] / "scripts/pr_review_workspace.py"
SPEC = importlib.util.spec_from_file_location("routing_workspace", SCRIPT)
assert SPEC and SPEC.loader
workspace = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(workspace)


def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True).stdout.strip()


def init(root: Path, repository: str) -> str:
    root.mkdir(parents=True)
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.name", "Fixture")
    git(root, "config", "user.email", "fixture@example.test")
    (root / ".gitignore").write_text("/reviews/\n")
    git(root, "add", ".gitignore")
    git(root, "commit", "-qm", "base")
    git(root, "remote", "add", "origin", f"https://github.com/{repository}.git")
    return git(root, "rev-parse", "HEAD")


@pytest.fixture
def fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    parent = tmp_path / "parent"
    init(parent, "usaturn/create-reso-world")
    checkout = parent / "external/resoloop"
    base = init(checkout, "usaturn/resoloop")
    git(
        checkout,
        "remote",
        "add",
        "upstream",
        "https://github.com/orange3134/resoloop.git",
    )
    for n in range(301):
        (checkout / f"file-{n:03}.txt").write_text(f"change {n}\n")
    git(checkout, "add", ".")
    git(checkout, "commit", "-qm", "301 files")
    head = git(checkout, "rev-parse", "HEAD")
    remote = tmp_path / "remote.git"
    git(checkout, "init", "--bare", "-q", str(remote))
    git(checkout, "push", "-q", str(remote), "main", "HEAD:refs/pull/3/head")
    api = tmp_path / "api.json"
    api.write_text(json.dumps({"head": head}))
    binary = tmp_path / "bin"
    binary.mkdir()
    # Rewrite only fetch transport, leaving remote identity inspection real.
    real_git = subprocess.run(["which", "git"], check=True, capture_output=True, text=True).stdout.strip()
    wrapper = binary / "git"
    wrapper.write_text(
        f"#!{sys.executable}\n"
        + f"REAL_GIT = {real_git!r}\n"
        + """import os, sys
args = sys.argv[1:]
if 'fetch' in args:
    args = [os.environ['FAKE_GIT_REMOTE'] if value in ('origin', 'upstream') else value for value in args]
os.execv(REAL_GIT, [REAL_GIT, *args])
"""
    )
    wrapper.chmod(0o755)
    monkeypatch.setenv("FAKE_GIT_REMOTE", str(remote))
    gh = binary / "gh"
    gh.write_text(
        f"#!{sys.executable}\n"
        + """import json, os, sys
assert sys.argv[1:3] == ['api', '-i']
parts = sys.argv[3].split('/')
assert len(parts) == 5 and parts[0] == 'repos' and parts[3:] == ['pulls', '3']
repo = '/'.join(parts[1:3])
head = json.load(open(os.environ['FAKE_PR_API']))['head']
print('HTTP/2.0 200 OK\\n')
print(json.dumps({'number': 3, 'html_url': f'https://github.com/{repo}/pull/3',
 'head': {'ref': 'feature/large', 'sha': head, 'repo': {'full_name': 'fork/resoloop'}},
 'base': {'ref': 'main', 'repo': {'full_name': repo, 'clone_url': f'https://github.com/{repo}.git'}},
 'state': 'open'}))
"""
    )
    gh.chmod(0o755)
    monkeypatch.setenv("FAKE_PR_API", str(api))
    monkeypatch.setenv("PATH", f"{binary}:{os.environ['PATH']}")
    return {
        "parent": parent,
        "checkout": checkout,
        "remote": remote,
        "head": head,
        "base": base,
        "api": api,
        "tmp": tmp_path,
    }


def target(f: dict[str, Any], repository: str = "orange3134/resoloop", **kwargs: Any) -> dict[str, Any]:
    return workspace._target_call(
        "resolve",
        f"https://github.com/{repository}/pull/3",
        parent_root=f["parent"],
        **kwargs,
    )


def create(f: dict[str, Any], resolved: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    return workspace.create(
        argparse.Namespace(
            target=json.dumps(resolved),
            model_name="fixture-model",
            temp_root=str(f["tmp"] / "sessions"),
            **kwargs,
        )
    )


def pair(result: dict[str, Any], repository: str, head: str, base: str) -> None:
    Path(result["draft"]).write_text("## Findings\n\nNo findings.\n")
    Path(result["findings_draft"]).write_text(
        json.dumps(
            {
                "schema": "review-findings/v1",
                "kind": "candidates",
                "source": "reviewer",
                "pr": {"repository": repository, "number": 3},
                "reviewed_head": head,
                "base": base,
                "reviewer": {
                    "model": "fixture-model",
                    "runtime": "pi",
                    "review_file": result["review_file"],
                },
                "skill": {
                    "path": ".agents/skills/pr-review/SKILL.md",
                    "sha256": "0" * 64,
                },
                "timing": {
                    "started_at": "2026-10-05T01:00:00Z",
                    "finished_at": "2026-10-05T01:01:00Z",
                    "seconds": 60,
                },
                "coverage": {
                    "read": ["301-file full diff"],
                    "checks": [],
                    "declined": [],
                },
                "findings": [],
                "unverified_candidates": [],
            }
        )
    )


def test_upstream_full_diff_pair_save_cleanup_preserves_shared_refs(
    fixture: dict[str, Any],
) -> None:
    f = fixture
    t = target(f)
    before = workspace.snapshot(f["checkout"])
    refs = git(f["checkout"], "show-ref")
    fetch_head = f["checkout"] / ".git/FETCH_HEAD"
    fetch_head.write_text("sentinel\n")
    result = create(f, t)
    state = json.loads(Path(result["state_file"]).read_text())
    assert state["base_remote"] == "upstream"
    assert state["version"] == 8
    worktree = Path(result["worktree"])
    assert len(git(worktree, "diff", "--name-only", f["base"], "HEAD").splitlines()) == 301
    diff = git(worktree, "diff", f["base"], "HEAD")
    assert "change 0" in diff and "change 300" in diff
    assert workspace.snapshot(f["checkout"]) == before
    assert fetch_head.read_text() == "sentinel\n"
    pair(result, "orange3134/resoloop", f["head"], f["base"])
    saved = workspace.save(argparse.Namespace(state=result["state_file"], findings=True))
    assert Path(saved["destination"]) == f["parent"] / "reviews/orange3134/resoloop/#3-feature-large/fixture-model.md"
    assert Path(saved["findings_destination"]).read_bytes() == Path(result["findings_draft"]).read_bytes()
    workspace.cleanup(argparse.Namespace(state=result["state_file"]))
    assert not worktree.parent.exists()
    assert git(f["checkout"], "show-ref") == refs


def test_moving_live_head_keeps_drafts_then_fresh_session_continues(
    fixture: dict[str, Any],
) -> None:
    f = fixture
    result = create(f, target(f))
    pair(result, "orange3134/resoloop", f["head"], f["base"])
    (f["checkout"] / "moved.txt").write_text("moved\n")
    git(f["checkout"], "add", "moved.txt")
    git(f["checkout"], "commit", "-qm", "moved")
    moved = git(f["checkout"], "rev-parse", "HEAD")
    git(f["checkout"], "push", "-q", str(f["remote"]), "HEAD:refs/pull/3/head")
    f["api"].write_text(json.dumps({"head": moved}))
    with pytest.raises(workspace.WorkspaceError, match="PR head changed"):
        workspace.save(argparse.Namespace(state=result["state_file"], findings=True))
    assert Path(result["draft"]).is_file() and Path(result["findings_draft"]).is_file()
    assert not (f["parent"] / result["destination"]).exists()
    fresh = create(f, target(f))
    pair(fresh, "orange3134/resoloop", moved, f["base"])
    workspace.save(argparse.Namespace(state=fresh["state_file"], findings=True))
    workspace.cleanup(argparse.Namespace(state=fresh["state_file"]))
    assert Path(result["state_file"]).exists()


def test_external_checkout_requires_explicit_source_and_matching_remote(
    fixture: dict[str, Any],
) -> None:
    f = fixture
    external = f["tmp"] / "external"
    init(external, "someone/tool")
    t = target(f, "someone/tool", code_root=external)
    result = create(f, t, source_root=str(external))
    pair(result, "someone/tool", f["head"], f["base"])
    saved = workspace.save(argparse.Namespace(state=result["state_file"], findings=True))
    assert Path(saved["destination"]).is_relative_to(f["parent"])
    workspace.cleanup(argparse.Namespace(state=result["state_file"]))
    with pytest.raises(workspace.WorkspaceError):
        create(f, t, source_root=str(f["checkout"]))


@pytest.mark.parametrize("change", ["remote", "sha", "number", "url", "repository"])
def test_target_rejects_unvalidated_input_without_creating_session(fixture: dict[str, Any], change: str) -> None:
    f = fixture
    t = target(f)
    if change == "remote":
        t["base_remote"] = "origin"
    elif change == "sha":
        t["head_sha"] = "HEAD"
    elif change == "number":
        t["number"] = True
    elif change == "url":
        t["url"] = "https://github.com/other/repo/pull/3"
    else:
        t["repository"] = "../escape"
    with pytest.raises(workspace.WorkspaceError):
        create(f, t)
    assert not (f["tmp"] / "sessions").exists()


def test_explicit_commit_has_separate_pair_and_validates_worktree_head(
    fixture: dict[str, Any],
) -> None:
    f = fixture
    result = create(f, target(f), review_commit=f["base"])
    assert result["review_file"] == f"fixture-model-commit-{f['base']}.md"
    pair(result, "orange3134/resoloop", f["base"], f["base"])
    git(Path(result["worktree"]), "reset", "--hard", f["head"])
    with pytest.raises(workspace.WorkspaceError, match="pinned commit"):
        workspace.save(argparse.Namespace(state=result["state_file"], findings=True))
    assert Path(result["draft"]).exists()


def test_ref_delete_failure_keeps_a_retryable_session(fixture: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    f = fixture
    result = create(f, target(f))
    pair(result, "orange3134/resoloop", f["head"], f["base"])
    workspace.save(argparse.Namespace(state=result["state_file"], findings=True))
    real_git = workspace.git

    def failing_git(root: Path, *args: str, **kwargs: Any) -> Any:
        if args[:2] == ("update-ref", "-d"):
            raise workspace.WorkspaceError("delete failed")
        return real_git(root, *args, **kwargs)

    monkeypatch.setattr(workspace, "git", failing_git)
    with pytest.raises(workspace.WorkspaceError, match="delete failed"):
        workspace.cleanup(argparse.Namespace(state=result["state_file"]))
    assert Path(result["worktree"]).is_dir()
    workspace.load_state(result["state_file"])


def make_checkout_shallow(f: dict[str, Any]) -> None:
    source = f["checkout"]
    full = f["tmp"] / "full-history"
    source.rename(full)
    git(f["parent"], "clone", "--quiet", "--depth=1", full.as_uri(), str(source))
    git(source, "remote", "set-url", "origin", "https://github.com/usaturn/resoloop.git")
    git(source, "remote", "add", "upstream", "https://github.com/orange3134/resoloop.git")


def recovery_args(session: Path) -> argparse.Namespace:
    return argparse.Namespace(
        repo=str(session / "repo"), temp_root=str(session.parent),
        pr_repo="orange3134/resoloop", pr_number=3, attempt_id="history-recovery", wait=0,
    )


def test_failed_shallow_create_can_be_inspected_then_abandoned(
    fixture: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    # Rejecting all repo/ entries strands helper-owned Git after create fails.
    f = fixture
    make_checkout_shallow(f)
    t = target(f)
    real_verify = workspace.require_created_worktree

    def fail_verify(path: Path, commit: str) -> None:
        real_verify(path, commit)
        raise workspace.WorkspaceError("injected verification failure")

    monkeypatch.setattr(workspace, "require_created_worktree", fail_verify)
    with pytest.raises(workspace.WorkspaceError, match="injected verification failure"):
        create(f, t, attempt_id="history-recovery")
    (session,) = (f["tmp"] / "sessions").iterdir()
    args = recovery_args(session)
    before = workspace.snapshot(f["checkout"])
    report = workspace.inspect_attempt(args)
    assert report["status"] == "failed"
    assert report["worktree_registered"] is True
    removed = workspace.abandon_attempt(args)
    assert removed["status"] == "failed"
    assert removed["worktree_removed"] is True
    assert not session.exists()
    assert workspace.snapshot(f["checkout"]) == before


@pytest.mark.parametrize(
    ("violation", "message"),
    [
        ("journal-kind", "create journal does not identify"),
        ("journal-worktree", "create journal does not identify"),
        ("journal-parent", "create journal has no owned-history repository parent"),
        ("journal-owner", "not this attempt's owned Git"),
        ("git-replacement", "not this attempt's owned Git"),
        ("git-symlink", "unowned Git or user data"),
        ("foreign-worktree", "owns another worktree"),
        ("repo-notes", "unowned Git or user data"),
    ],
)
def test_shallow_recovery_refuses_unowned_git_or_user_data(
    fixture: dict[str, Any], violation: str, message: str
) -> None:
    # A repo/ allowlist alone must not authorize substituted Git or other worktrees.
    f = fixture
    make_checkout_shallow(f)
    result = create(f, target(f), attempt_id="history-recovery")
    session = Path(result["state_file"]).parent
    repo = session / "repo"
    if violation.startswith("journal-"):
        journal = session / "create-journal.jsonl"
        records = [json.loads(line) for line in journal.read_text().splitlines()]
        if violation == "journal-kind":
            records[0]["target_kind"] = "checkout"
        elif violation == "journal-worktree":
            records[0]["worktree"] = str(f["checkout"])
        elif violation == "journal-parent":
            records[0]["parent_root"] = None
        else:
            (created,) = [record for record in records if record["phase"] == "owned-history-created"]
            created["inode"] = -1
        journal.write_text("".join(json.dumps(record) + "\n" for record in records))
    elif violation in {"git-replacement", "git-symlink"}:
        outside = f["tmp"] / "original-git"
        (repo / ".git").rename(outside)
        if violation == "git-symlink":
            (repo / ".git").symlink_to(outside, target_is_directory=True)
        else:
            git(repo, "init", "-q")
    elif violation == "foreign-worktree":
        git(repo, "worktree", "add", "--detach", str(f["tmp"] / "user-worktree"), f["head"])
    else:
        (repo / "notes.txt").write_text("user data\n")
    before = git(repo, "worktree", "list", "--porcelain")
    with pytest.raises(workspace.WorkspaceError, match=message):
        workspace.abandon_attempt(recovery_args(session))
    assert session.is_dir()
    assert git(repo, "worktree", "list", "--porcelain") == before
