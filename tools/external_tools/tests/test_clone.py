"""S: cloning must not overwrite users' data, bypass authority, or report a partial fetch as success."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import importlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from threading import Event

import pytest

from .conftest import OTHER, git
from .test_identity import snapshot


def clone_module():
    return importlib.import_module("tools.external_tools.clone")


def vacate(workspace, tmp_path):
    workspace.registered.rename(tmp_path / "preserved user checkout")


class Transport:
    """Replace only the internal process boundary; init/config/checkout remain real Git.

    Fetch installs objects from a local fixture, never invokes a transport or reads
    credentials. Callbacks interleave filesystem/registry changes at the process
    boundary, without replacing any lock, authority, path or publication checks.
    """

    def __init__(self, module, workspace, monkeypatch):
        self.real = module._run
        self.seed = workspace.other_clone
        self.calls = []
        self.before = lambda args, root: None
        self.after = lambda args, root: None
        self.fail_fetch = False
        monkeypatch.setattr(module, "_run", self.run)

    def run(self, args, *, directory_fd):
        root = Path(os.readlink(f"/proc/self/fd/{directory_fd}"))
        self.before(args, root)
        if args[0] == "fetch":
            self.calls.append(git(root, "remote", "get-url", "origin"))
            if self.fail_fetch:
                (root / "partial evidence").write_bytes(b"retain failed fetch\x00")
                result = subprocess.CompletedProcess(args, 1, b"", b"private remote failure")
            else:
                # Only local fixture objects, no network/clone/fetch subprocess.
                shutil.copytree(self.seed / ".git/objects", root / ".git/objects", dirs_exist_ok=True)
                git(root, "update-ref", args[-1].split(":", 1)[1], git(self.seed, "rev-parse", "HEAD"))
                result = subprocess.CompletedProcess(args, 0, b"", b"")
        else:
            result = self.real(args, directory_fd=directory_fd)
        self.after(args, root)
        return result


def test_existing_target_is_never_changed(workspace, tmp_path, monkeypatch):
    # Removing the existing-target gate would mutate refs/index/config or erase user data.
    module = clone_module()
    transport = Transport(module, workspace, monkeypatch)
    registry = workspace.registry
    before = snapshot(workspace)
    assert module.clone_tool(registry, "emission-editor").status == "present"
    assert snapshot(workspace) == before
    sentinel = workspace.registered / "user bytes"
    sentinel.write_bytes("材質の変更\n元値を保持する".encode())
    before = snapshot(workspace)
    assert module.clone_tool(registry, "emission-editor").status == "blocked"
    assert snapshot(workspace) == before
    git(workspace.registered, "remote", "set-url", "origin", "https://github.com/wrong/target.git")
    before = snapshot(workspace)
    assert module.clone_tool(registry, "emission-editor").status == "blocked"
    assert snapshot(workspace) == before
    vacate(workspace, tmp_path)
    workspace.registered.mkdir()
    sentinel = workspace.registered / "unknown residue"
    sentinel.write_bytes(b"never delete me\x00")
    assert module.clone_tool(registry, "emission-editor").status == "blocked"
    assert sentinel.read_bytes() == b"never delete me\x00"
    assert transport.calls == []


def test_hidden_tracked_change_is_not_reported_present(workspace, monkeypatch, capsys):
    # S: trusting empty status alone silently reports an assume-unchanged edit as
    # present/success. Refusal must preserve the user's file, index flags and refs.
    module = clone_module()
    transport = Transport(module, workspace, monkeypatch)
    from tools.external_tools.cli import main

    args = ["--parent-root", str(workspace.parent), "clone", "emission-editor"]
    assert main(args) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "present"
    tracked = workspace.registered / ".gitignore"
    git(workspace.registered, "update-index", "--assume-unchanged", ".gitignore")
    changed = "材質の変更\n元値を保持する\n".encode("utf-8")
    tracked.write_bytes(changed)
    assert git(workspace.registered, "status", "--porcelain=v1", "--untracked-files=all") == ""
    before = snapshot(workspace)

    code = main(args)
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "blocked"
    assert code != 0 and result["reason_code"] and result["staging"] is None
    assert tracked.read_bytes() == changed
    assert snapshot(workspace) == before
    assert transport.calls == []


def test_concurrent_clone_has_one_publisher(workspace, tmp_path, monkeypatch):
    # Removing nonblocking per-key flock would allow two writers/transports.
    module = clone_module()
    transport = Transport(module, workspace, monkeypatch)
    registry = workspace.registry
    vacate(workspace, tmp_path)
    entered, release = Event(), Event()

    def pause(args, root):
        if args[0] == "fetch":
            entered.set()
            assert release.wait(10), "test did not release the fixture fetch"

    transport.before = pause
    with ThreadPoolExecutor(max_workers=1) as pool:
        first = pool.submit(module.clone_tool, registry, "emission-editor")
        try:
            assert entered.wait(10), "first clone never reached fetch"
            second = module.clone_tool(registry, "emission-editor")
            assert second.status == "blocked" and second.reason_code == "busy"
        finally:
            release.set()
        results = [first.result(), second]
    assert sum(result.status == "cloned" for result in results) == 1
    assert transport.calls == ["https://github.com/usaturn/resonite-emission-editor.git"]
    assert module.clone_tool(registry, "emission-editor").status == "present"


@pytest.mark.parametrize("race", ["new-destination", "ancestor-swap", "staging-swap"])
def test_publish_refuses_new_destination(workspace, tmp_path, monkeypatch, race):
    # Replacing no-replace rename/fd revalidation with ordinary rename or path access
    # overwrites a new destination or follows an ancestor swapped out after inspection.
    module = clone_module()
    transport = Transport(module, workspace, monkeypatch)
    registry = workspace.registry
    vacate(workspace, tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    sentinel = outside / "sentinel"
    sentinel.write_bytes(b"outside data\x00")
    saved = tmp_path / "retained external"

    def race_at_checkout(args, root):
        if args[0] != "checkout":
            return
        if race == "new-destination":
            # Even an empty directory must not be replaced (ordinary rename would).
            workspace.registered.mkdir()
        elif race == "ancestor-swap":
            (workspace.parent / "external").rename(saved)
            (workspace.parent / "external").symlink_to(outside, target_is_directory=True)
        else:
            root.rename(root.with_name("preserved staging"))
            root.symlink_to(outside, target_is_directory=True)

    transport.after = race_at_checkout
    result = module.clone_tool(registry, "emission-editor")
    assert result.status == "blocked" and result.reason_code
    assert result.staging is not None
    assert sentinel.read_bytes() == b"outside data\x00"
    assert sorted(path.name for path in outside.iterdir()) == ["sentinel"]
    if race == "new-destination":
        assert list(workspace.registered.iterdir()) == []
    elif race == "ancestor-swap":
        assert not (saved / "emission-editor").exists()
    else:
        assert not workspace.registered.exists()


def test_failed_fetch_retains_staging_evidence(workspace, tmp_path, monkeypatch):
    # Swallowing a Git failure or cleaning up would report success or lose evidence.
    module = clone_module()
    transport = Transport(module, workspace, monkeypatch)
    transport.fail_fetch = True
    registry = workspace.registry
    vacate(workspace, tmp_path)
    result = module.clone_tool(registry, "emission-editor")
    assert result.status == "failed" and result.reason_code == "git_failed"
    assert result.staging is not None
    assert (result.staging / "partial evidence").read_bytes() == b"retain failed fetch\x00"
    assert not workspace.registered.exists()
    assert "private" not in repr(result)


def test_clone_rechecks_adoption_before_publication(workspace, tmp_path, monkeypatch):
    # A stale registry snapshot must not publish after the parent's adopted HEAD changes.
    module = clone_module()
    transport = Transport(module, workspace, monkeypatch)
    registry = workspace.registry
    vacate(workspace, tmp_path)

    def change_adoption(args, root):
        if args[0] == "checkout":
            git(workspace.parent, "commit", "--allow-empty", "-m", "new adopted commit")
            git(workspace.parent, "update-ref", "refs/remotes/origin/main", "HEAD")

    transport.after = change_adoption
    result = module.clone_tool(registry, "emission-editor")
    assert result.status == "blocked" and result.reason_code == "registry_not_active"
    assert result.staging.is_dir()
    assert not workspace.registered.exists()


def test_candidate_and_rewritten_destination_cannot_fetch(workspace, tmp_path, monkeypatch):
    # Candidate authority or trusting raw origin alone would send the fetch elsewhere.
    module = clone_module()
    transport = Transport(module, workspace, monkeypatch)
    registry = workspace.registry
    vacate(workspace, tmp_path)
    assert module.clone_tool(replace(registry, commit="unadopted"), "emission-editor").status == "blocked"
    assert not (workspace.parent / ".git/external-tools").exists()
    # Target-specific rewrite leaves parent validation valid, exercising the
    # pre-fetch stage destination gate.
    git(workspace.parent, "config", "--global", "url.https://example.invalid/.insteadOf", "https://github.com/usaturn/resonite-emission-editor")
    result = module.clone_tool(registry, "emission-editor")
    assert result.status == "blocked" and result.reason_code == "remote_mismatch"
    assert transport.calls == []
    assert not workspace.registered.exists()


@pytest.mark.parametrize("gate", ["ancestor", "lock-file"])
def test_clone_refuses_symlink_lock_paths(workspace, tmp_path, monkeypatch, gate):
    # Following either lock ancestor or final symlink could write outside .git and
    # split exclusion across different inodes, permitting competing publishers.
    module = clone_module()
    transport = Transport(module, workspace, monkeypatch)
    registry = workspace.registry
    vacate(workspace, tmp_path)
    outside = tmp_path / "outside lock data"
    outside.mkdir()
    sentinel = outside / "sentinel"
    sentinel.write_bytes(b"do not touch")
    lock_root = workspace.parent / ".git/external-tools"
    if gate == "ancestor":
        lock_root.symlink_to(outside, target_is_directory=True)
    else:
        (lock_root / "locks").mkdir(parents=True)
        (lock_root / "locks/emission-editor.lock").symlink_to(sentinel)
    result = module.clone_tool(registry, "emission-editor")
    assert result.status == "blocked"
    assert sentinel.read_bytes() == b"do not touch"
    assert sorted(path.name for path in outside.iterdir()) == ["sentinel"]
    assert transport.calls == []
    assert not workspace.registered.exists()


def test_clone_only_selected_branch_without_hooks_or_inherited_git(workspace, monkeypatch, tmp_path):
    # Dropping key/branch selection, Git isolation, or hooks suppression can fetch
    # the wrong repo or execute user hooks during an otherwise plausible success.
    module = clone_module()
    transport = Transport(module, workspace, monkeypatch)
    (workspace.parent / "external-tools.toml").write_bytes((workspace.parent / "external-tools.toml").read_bytes() + OTHER)
    git(workspace.parent, "add", "external-tools.toml")
    git(workspace.parent, "commit", "-m", "adopt second tool")
    git(workspace.parent, "update-ref", "refs/remotes/origin/main", "HEAD")
    registry = workspace.registry
    issue = "材質の変更\n元値を保持する"
    (workspace.other_clone / "issue.txt").write_text(issue, encoding="utf-8")
    git(workspace.other_clone, "add", "issue.txt")
    git(workspace.other_clone, "commit", "-m", "fixture content")
    hook_root = tmp_path / "user hooks"
    hook_root.mkdir()
    marker = tmp_path / "hook executed"
    hook = hook_root / "post-checkout"
    hook.write_text(f"#!/bin/sh\nprintf bad > '{marker}'\n", encoding="utf-8")
    hook.chmod(0o755)
    git(workspace.parent, "config", "--global", "core.hooksPath", str(hook_root))
    before = snapshot(workspace)
    monkeypatch.setenv("GIT_DIR", str(workspace.other_clone / ".git"))
    monkeypatch.setenv("GIT_WORK_TREE", str(workspace.other_clone))
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "core.hooksPath")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", str(hook_root))
    result = module.clone_tool(registry, "other-tool")
    assert result.status == "cloned" and result.staging is None
    assert result.path == workspace.parent / "external/other-tool"
    assert (result.path / "issue.txt").read_text(encoding="utf-8") == issue
    assert git(result.path, "branch", "--show-current") == ""
    assert git(result.path, "for-each-ref", "--format=%(refname)", "refs/heads") == ""
    assert git(result.path, "rev-parse", "HEAD") == git(workspace.other_clone, "rev-parse", "HEAD")
    assert git(result.path, "rev-parse", "refs/remotes/origin/development") == git(result.path, "rev-parse", "HEAD")
    assert transport.calls == ["https://github.com/sample-owner/other-tool.git"]
    assert not marker.exists()
    # The parent gained only an ignored external checkout, no existing repository changed.
    after = snapshot(workspace)
    assert after[str(workspace.registered)] == before[str(workspace.registered)]
    assert after[str(workspace.other_clone)] == before[str(workspace.other_clone)]


def test_cli_requires_one_target_and_blocks_dirty_without_writes(workspace, monkeypatch, capsys):
    # Missing-target fallback or ignoring clone's blocked status would mutate dirty
    # data or misleadingly claim success. A clean existing checkout remains valid.
    module = clone_module()
    transport = Transport(module, workspace, monkeypatch)
    from tools.external_tools.cli import main

    prefix = ["--parent-root", str(workspace.parent), "clone"]
    before = snapshot(workspace)
    with pytest.raises(SystemExit):
        main(prefix)
    capsys.readouterr()
    assert snapshot(workspace) == before and transport.calls == []
    assert main([*prefix, "emission-editor"]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "present"
    (workspace.registered / "user data").write_bytes(b"keep me")
    before = snapshot(workspace)
    assert main([*prefix, "emission-editor"]) != 0
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "blocked" and result["staging"] is None
    assert snapshot(workspace) == before and transport.calls == []


def test_checkout_cannot_be_redirected_by_configured_worktree(workspace, tmp_path, monkeypatch):
    # Relying on cwd alone lets core.worktree direct checkout writes outside the
    # held staging directory even when all filesystem ancestors are unchanged.
    module = clone_module()
    transport = Transport(module, workspace, monkeypatch)
    registry = workspace.registry
    vacate(workspace, tmp_path)
    outside = tmp_path / "unrelated user directory"
    outside.mkdir()
    (outside / "sentinel").write_bytes(b"keep outside")

    def change_worktree(args, root):
        if args[0] == "fetch":
            git(root, "config", "core.worktree", str(outside))

    transport.after = change_worktree
    result = module.clone_tool(registry, "emission-editor")
    assert result.status == "blocked"
    assert {path.name: path.read_bytes() for path in outside.iterdir()} == {"sentinel": b"keep outside"}
    assert not workspace.registered.exists()
