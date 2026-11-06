"""S: a read-only CLI must not report unadopted or unavailable targets as ready."""
from __future__ import annotations

import json
import shutil

from .conftest import ADOPTED, UNADOPTED, git


def invoke(workspace, capsys, *args):
    from tools.external_tools.cli import main

    code = main(["--parent-root", str(workspace.parent), *args])
    output = capsys.readouterr()
    assert output.err == ""
    return code, json.loads(output.out)


def test_cli_reads_adopted_blob_without_promoting_candidates(workspace, capsys):
    # Reading the worktree file would expose unadopted targets as operational entries.
    (workspace.parent / "external-tools.toml").write_bytes(ADOPTED + UNADOPTED)
    code, listing = invoke(workspace, capsys, "list")
    assert code == 0
    assert [entry["repository"] for entry in listing["tools"]] == [workspace.repository]
    assert listing["registry_commit"] == workspace.adopted_sha
    code, shown = invoke(workspace, capsys, "show", "emission-editor")
    assert code == 0 and shown["repository"] == workspace.repository
    assert shown["path"] == str(workspace.registered)
    code, checked = invoke(workspace, capsys, "check", "unadopted")
    assert code != 0 and checked["status"] == "blocked"


def test_cli_check_never_calls_missing_or_mismatched_checkout_ready(workspace, capsys):
    # A swallowed identity error or parent fallback would advertise a wrong target as ready.
    from .test_identity import snapshot

    before = snapshot(workspace)
    code, checked = invoke(workspace, capsys, "check", "emission-editor")
    assert code == 0 and checked["status"] == "ready"
    assert checked["path"] == str(workspace.registered)
    assert checked["common_dir"] == str(workspace.registered / ".git")
    assert snapshot(workspace) == before
    git(workspace.registered, "remote", "set-url", "origin", "https://github.com/wrong/repository.git")
    before = snapshot(workspace)
    code, checked = invoke(workspace, capsys, "check", "emission-editor")
    assert code != 0 and checked["status"] == "mismatch" and checked["reason_code"]
    assert snapshot(workspace) == before
    # Move, rather than delete, user data; check must neither recreate nor clone it.
    saved = workspace.registered.with_name("saved")
    shutil.move(workspace.registered, saved)
    code, checked = invoke(workspace, capsys, "check", "emission-editor")
    assert code != 0 and checked["status"] == "missing"
    assert not workspace.registered.exists() and saved.is_dir()
