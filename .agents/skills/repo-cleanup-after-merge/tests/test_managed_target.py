"""S: execute the cleanup skill so same-origin clones/foreign worktrees survive.

Removing the managed resolver/common-dir gate would delete the foreign candidate;
removing the base ancestry gate would delete the unmerged worktree. The positive
case prevents an implementation which refuses every cleanup from passing.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import sys

import pytest

from tools.external_tools.tests.conftest import (
    Workspace,
    git,
    isolated_git,
    workspace,
)

SKILL = Path(__file__).resolve().parents[1] / "SKILL.md"
TOOL_ROOT = SKILL.parents[3]


def section_bash(title: str) -> str:
    section = re.search(
        rf"^### {re.escape(title)}\n(.*?)(?=^### |^## |\Z)",
        SKILL.read_text(encoding="utf-8"), re.M | re.S,
    )
    assert section, f"cleanup has no executable {title} gate"
    blocks = re.findall(r"```bash\n(.*?)```", section.group(1), re.S)
    assert len(blocks) == 1
    return blocks[0]


def test_managed_cleanup_resolves_only_registered_common_dir(
    workspace: Workspace, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Every candidate is a real local Git worktree; only the PR API is fake.
    for name in ("BASH_ENV", "ENV", "CODE_ROOT"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    tools = tmp_path / "fake cli"
    tools.mkdir()
    gh = tools / "gh"
    gh.write_text(
        f"#!{sys.executable}\n"
        "import json, os, sys\n"
        "expected = ['pr', 'view', '7', '--repo', os.environ['PR_REPO'], "
        "'--json', 'state,headRefName,headRefOid,mergeCommit,isCrossRepository']\n"
        "if sys.argv[1:] != expected: sys.exit(91)\n"
        "print(os.environ['FIXTURE_PR'])\n",
        encoding="utf-8",
    )
    gh.chmod(0o755)
    monkeypatch.setenv("PATH", f"{tools}{os.pathsep}{os.environ['PATH']}")

    registered_checkout = workspace.registered
    # A squash merge is not an ancestor of the candidate branch. The shared
    # predicate must still accept the managed worktree through PR evidence.
    (workspace.linked / "tool-change.txt").write_text("材質の変更\n", encoding="utf-8")
    git(workspace.linked, "add", "tool-change.txt")
    git(workspace.linked, "commit", "-m", "tool change")
    linked_head = git(workspace.linked, "rev-parse", "HEAD")
    (registered_checkout / "tool-change.txt").write_text("材質の変更\n", encoding="utf-8")
    git(registered_checkout, "add", "tool-change.txt")
    git(registered_checkout, "commit", "-m", "squash tool change")
    squash_commit = git(registered_checkout, "rev-parse", "HEAD")
    git(registered_checkout, "update-ref", "refs/remotes/origin/main", squash_commit)
    assert subprocess.run(
        ["git", "-C", str(registered_checkout), "merge-base", "--is-ancestor",
         linked_head, squash_commit], capture_output=True, text=True,
    ).returncode == 1, "the fixture must exercise the PR (squash) path, not ancestry"
    unrelated_worktree = tmp_path / "unrelated merged worktree"
    git(workspace.other_clone, "worktree", "add", "-b", "other-merged", str(unrelated_worktree))
    git(workspace.other_clone, "update-ref", "refs/remotes/origin/main", "HEAD")
    parent_worktree = workspace.candidate
    unmerged = tmp_path / "unmerged worktree"
    git(registered_checkout, "worktree", "add", "-b", "unmerged", str(unmerged))
    (unmerged / "change.txt").write_text("材質の変更\n元値を保持する\n", encoding="utf-8")
    git(unmerged, "add", "change.txt")
    git(unmerged, "commit", "-m", "unmerged work")
    parent_before = git(workspace.parent, "worktree", "list", "--porcelain")
    other_before = git(workspace.other_clone, "worktree", "list", "--porcelain")
    registered_head = git(registered_checkout, "rev-parse", "HEAD")

    # Execute real selection, ancestry and PR gates, then the existing step 5
    # removal command (later cleanliness/ownership gates are satisfied fixtures).
    removal = section_bash("5. worktree を削除する").replace('<path>', '"$CLEANUP_CANDIDATE"')
    commands = (
        section_bash("branch の取り込み判定")
        + section_bash("通常ツールの対象照合")
        + '\nprintf "TARGET=%s\\n" "$CLEANUP_ROOT"\n'
        + section_bash("通常ツールの削除候補の照合")
        + '\ncd -- "$CLEANUP_ROOT"\n' + removal
    )

    def run(candidate: Path, code_root: Path | None = None,
            integrated: bool = True) -> subprocess.CompletedProcess[str]:
        branch = git(candidate, "branch", "--show-current")
        candidate_head = git(candidate, "rev-parse", "HEAD")
        env = dict(os.environ, TOOL_ROOT=str(TOOL_ROOT), PARENT_ROOT=str(workspace.parent),
                   PR_REPO=workspace.repository, PR_NUMBER="7", CLEANUP_CANDIDATE=str(candidate),
                   FIXTURE_PR=json.dumps({"state": "MERGED", "headRefName": branch,
                                          "headRefOid": candidate_head,
                                          "mergeCommit": {"oid": squash_commit if integrated
                                                          else candidate_head},
                                          "isCrossRepository": False}))
        if code_root:
            env["CODE_ROOT"] = str(code_root)
        return subprocess.run(["bash", "--noprofile", "--norc", "-c", commands],
                              cwd=workspace.parent, env=env, capture_output=True, text=True)

    refused_clone = run(unrelated_worktree, workspace.other_clone)
    assert refused_clone.returncode != 0, refused_clone.stdout + refused_clone.stderr
    assert "common_dir_mismatch" in refused_clone.stderr
    refused_parent = run(parent_worktree)
    assert refused_parent.returncode != 0, refused_parent.stdout + refused_parent.stderr
    refused_unmerged = run(unmerged, integrated=False)
    assert refused_unmerged.returncode != 0, refused_unmerged.stdout + refused_unmerged.stderr

    accepted = run(workspace.linked)
    assert accepted.returncode == 0, accepted.stdout + accepted.stderr
    cleanup_target = Path(next(line.removeprefix("TARGET=") for line in accepted.stdout.splitlines()
                               if line.startswith("TARGET=")))
    assert cleanup_target == registered_checkout
    assert not workspace.linked.exists(), "the merged, owned tool worktree must be removable"
    assert unrelated_worktree.exists()
    assert parent_worktree.exists()
    assert unmerged.exists()
    unmerged_branch_still_exists = "refs/heads/unmerged" in git(
        registered_checkout, "for-each-ref", "--format=%(refname)", "refs/heads")
    assert unmerged_branch_still_exists
    assert git(workspace.parent, "worktree", "list", "--porcelain") == parent_before
    assert git(workspace.other_clone, "worktree", "list", "--porcelain") == other_before
    assert git(registered_checkout, "rev-parse", "HEAD") == registered_head
