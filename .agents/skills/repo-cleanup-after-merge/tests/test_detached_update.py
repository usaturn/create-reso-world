"""Execute cleanup update, deletion and status against disposable Git repositories.

These regressions catch attaching/creating/moving local main, targeting the
caller's linked worktree, deleting against its stale HEAD, proceeding after a
failed cleanliness/checkout gate,
Git's default overwrite of ignored user files, and clean tracked world deletions.
Expected Git state comes
from the fixtures, not from the skill's wording or eval lists.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SKILL = Path(__file__).resolve().parents[1] / "SKILL.md"
EVIDENCE_TITLE = "branch の取り込み判定"
PR_REPO = "usaturn/create-reso-world"


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
        timeout=20,
    )
    return result.stdout.strip()


@pytest.fixture(autouse=True)
def isolated_git_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Hooks, signing, config overrides, repository selectors and shell startup
    # files from the agent's environment must not reach these temporary repos.
    for name in tuple(os.environ):
        if name.startswith("GIT_") or name in {
            "BASH_ENV", "ENV", "MAIN_ROOT", "TARGET_ROOT", "PR_REPO", "PR_NUMBER",
            "BASE_REF",
        }:
            monkeypatch.delenv(name)
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(home / "config"))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_AUTHOR_NAME", "Cleanup test")
    monkeypatch.setenv("GIT_AUTHOR_EMAIL", "cleanup@example.invalid")
    monkeypatch.setenv("GIT_COMMITTER_NAME", "Cleanup test")
    monkeypatch.setenv("GIT_COMMITTER_EMAIL", "cleanup@example.invalid")
    monkeypatch.setenv("LC_ALL", "C")


@pytest.fixture()
def checkout(tmp_path: Path) -> Path:
    remote = tmp_path / "remote.git"
    remote.mkdir()
    git(remote, "init", "-q", "--bare", "-b", "main")
    publisher = tmp_path / "publisher"
    publisher.mkdir()
    git(publisher, "init", "-q", "-b", "main")
    (publisher / "base.txt").write_text("base\n", encoding="utf-8")
    (publisher / ".gitignore").write_text("private.txt\n", encoding="utf-8")
    git(publisher, "add", ".")
    git(publisher, "commit", "-qm", "base")
    git(publisher, "remote", "add", "origin", str(remote))
    git(publisher, "push", "-q", "origin", "main")
    work = tmp_path / "main worktree"
    git(tmp_path, "clone", "-q", str(remote), str(work))
    git(work, "checkout", "-q", "--detach", "origin/main")
    git(work, "branch", "-d", "main")
    return work


def advance_remote(work: Path, filename: str = "incoming.txt") -> str:
    publisher = work.parent / "publisher"
    (publisher / filename).write_text("remote content\n", encoding="utf-8")
    git(publisher, "add", "-f", filename)
    git(publisher, "commit", "-qm", f"add {filename}")
    git(publisher, "push", "-q", "origin", "main")
    git(work, "fetch", "-q", "--all", "--prune")
    return git(publisher, "rev-parse", "HEAD")


def local_refs(work: Path) -> str:
    return git(work, "for-each-ref", "--format=%(refname) %(objectname)", "refs/heads")


def step_text(step: int) -> str:
    section = re.search(
        rf"^### {step}\.[^\n]*\n(.*?)(?=^### \d+\.|\Z)",
        SKILL.read_text(encoding="utf-8"),
        re.M | re.S,
    )
    assert section, f"cleanup step {step} is missing"
    return section.group(1)


def step_bash(step: int) -> str:
    blocks = re.findall(r"```bash\n(.*?)```", step_text(step), re.S)
    assert len(blocks) == 1, f"step {step} must have one runnable bash block"
    return blocks[0]


def section_bash(title: str) -> str:
    section = re.search(
        rf"^### {re.escape(title)}\n(.*?)(?=^### |^## |\Z)",
        SKILL.read_text(encoding="utf-8"),
        re.M | re.S,
    )
    assert section, f"cleanup has no executable {title} block"
    blocks = re.findall(r"```bash\n(.*?)```", section.group(1), re.S)
    assert len(blocks) == 1, f"{title} must have one runnable bash block"
    return blocks[0]


def run_bash(commands: str, *, cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", "--noprofile", "--norc", "-c", commands],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
    )


FAKE_GH_SOURCE = f'''#!{sys.executable}
import json, os, sys
args = sys.argv[1:]
fields = "state,headRefName,headRefOid,mergeCommit,isCrossRepository"
if (len(args) != 7 or args[:2] != ["pr", "view"]
        or args[3:5] != ["--repo", os.environ["PR_REPO"]]
        or args[5:] != ["--json", fields]):
    print("unexpected gh argv: " + repr(args), file=sys.stderr)
    sys.exit(91)
with open(os.environ["FAKE_GH_PRS_FILE"], encoding="utf-8") as stream:
    prs = json.load(stream)
pr = prs.get(args[2])
if pr is None:
    sys.exit(1)
print(json.dumps(pr))
'''


def fake_gh_environment(
    work: Path, prs: dict[str, dict[str, object]],
) -> dict[str, str]:
    tools = work.parent / "cleanup fake gh"
    tools.mkdir(exist_ok=True)
    script = tools / "gh"
    script.write_text(FAKE_GH_SOURCE, encoding="utf-8")
    script.chmod(0o755)
    prs_file = tools / "prs.json"
    prs_file.write_text(json.dumps(prs), encoding="utf-8")
    return {
        "PATH": f"{tools}{os.pathsep}{os.environ['PATH']}",
        "FAKE_GH_PRS_FILE": str(prs_file),
        "PR_REPO": PR_REPO,
    }


def pr_payload(
    branch: str, head: str, *, number: int = 7, merge: str | None = None,
    state: str = "MERGED",
) -> dict[str, object]:
    return {
        "number": number,
        "state": state,
        "headRefName": branch,
        "headRefOid": head,
        "mergeCommit": None if merge is None else {"oid": merge},
        "isCrossRepository": False,
    }


def run_step8(
    work: Path, branch: str, prs: dict[str, dict[str, object]], *,
    number: str = "7", base_ref: str = "refs/remotes/origin/main",
) -> subprocess.CompletedProcess[str]:
    commands = section_bash(EVIDENCE_TITLE) + "\n" + step_bash(8).replace("<branch>", branch)
    env = {
        **os.environ,
        **fake_gh_environment(work, prs),
        "MAIN_ROOT": str(work),
        "PR_NUMBER": number,
        "BASE_REF": base_ref,
    }
    return run_bash(commands, cwd=work, env=env)


def run_step7(
    work: Path, *, cwd: Path | None = None, following_delete: bool = False,
    prs: dict[str, dict[str, object]] | None = None,
) -> subprocess.CompletedProcess[str]:
    commands = step_bash(7)
    env = {**os.environ, "MAIN_ROOT": str(work)}
    if following_delete:
        env.update(fake_gh_environment(work, prs or {}))
        env.update({"PR_NUMBER": "7", "BASE_REF": "refs/remotes/origin/main"})
        # Execute the actual step 8 in the same shell. Step 7 must stop it
        # itself on failure; the harness deliberately does not add -e or -C.
        commands += (
            "\n" + section_bash(EVIDENCE_TITLE) + "\n"
            + step_bash(8).replace("<branch>", "merged-feature")
        )
    return subprocess.run(
        ["bash", "--noprofile", "--norc", "-c", commands],
        cwd=cwd or work,
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
    )


def assert_detached_at(work: Path, oid: str) -> None:
    result = subprocess.run(
        ["git", "-C", str(work), "symbolic-ref", "-q", "HEAD"],
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 1, f"HEAD is attached: {result.stdout}{result.stderr}"
    assert git(work, "rev-parse", "HEAD") == oid
    assert git(work, "status", "--short") == ""


@pytest.mark.parametrize("starting_head", ["detached", "main", "merged-feature"])
def test_updates_to_detached_origin_main_without_changing_local_refs(
    checkout: Path, starting_head: str
) -> None:
    if starting_head != "detached":
        git(checkout, "checkout", "-qb", starting_head)
    target = advance_remote(checkout)
    refs_before = local_refs(checkout)

    result = run_step7(checkout)

    assert result.returncode == 0, (result.stdout, result.stderr)
    assert local_refs(checkout) == refs_before, "cleanup created or moved a local branch"
    assert_detached_at(checkout, target)
    assert (checkout / "incoming.txt").read_text(encoding="utf-8") == "remote content\n"


@pytest.mark.parametrize("main_state", ["stale", "divergent"])
def test_existing_main_is_retained_without_ref_or_reflog_updates(
    checkout: Path, main_state: str
) -> None:
    git(checkout, "checkout", "-qb", "main")
    if main_state == "divergent":
        (checkout / "local-only.txt").write_text("keep local commit\n", encoding="utf-8")
        git(checkout, "add", "local-only.txt")
        git(checkout, "commit", "-qm", "local-only main commit")
    git(checkout, "checkout", "-q", "--detach", "origin/main")
    target = advance_remote(checkout)
    refs_before = local_refs(checkout)
    reflog_before = git(checkout, "reflog", "show", "main")

    result = run_step7(checkout)

    assert result.returncode == 0, (result.stdout, result.stderr)
    assert local_refs(checkout) == refs_before, "existing main was moved"
    assert git(checkout, "reflog", "show", "main") == reflog_before
    assert_detached_at(checkout, target)


def test_main_held_by_another_worktree_does_not_block_or_mutate_that_tree(checkout: Path) -> None:
    other = checkout.parent / "main holder"
    git(checkout, "worktree", "add", "-qb", "main", str(other))
    (other / "base.txt").write_text("other worktree edit\n", encoding="utf-8")
    (other / "private.txt").write_text("other private draft\n", encoding="utf-8")
    other_head = git(other, "rev-parse", "HEAD")
    other_status = git(other, "status", "--short", "--ignored")
    target = advance_remote(checkout)
    refs_before = local_refs(checkout)
    trees_before = git(checkout, "worktree", "list", "--porcelain")

    result = run_step7(checkout)

    assert result.returncode == 0, (result.stdout, result.stderr)
    assert_detached_at(checkout, target)
    assert local_refs(checkout) == refs_before
    # Only the main worktree's HEAD may change in the worktree listing.
    assert git(checkout, "worktree", "list", "--porcelain") == trees_before.replace(
        f"HEAD {other_head}\ndetached", f"HEAD {target}\ndetached", 1
    )
    assert git(other, "symbolic-ref", "--short", "HEAD") == "main"
    assert git(other, "rev-parse", "HEAD") == other_head
    assert git(other, "status", "--short", "--ignored") == other_status
    assert (other / "base.txt").read_text(encoding="utf-8") == "other worktree edit\n"
    assert (other / "private.txt").read_text(encoding="utf-8") == "other private draft\n"


def test_invocation_from_linked_project_targets_main_root_not_callers_feature(checkout: Path) -> None:
    linked = checkout.parent / "linked feature"
    git(checkout, "worktree", "add", "-qb", "active-feature", str(linked))
    project = linked / "project"
    project.mkdir()
    caller_head = git(linked, "rev-parse", "HEAD")
    target = advance_remote(checkout)
    refs_before = local_refs(checkout)

    result = run_step7(checkout, cwd=project)

    assert result.returncode == 0, (result.stdout, result.stderr)
    assert git(linked, "symbolic-ref", "--short", "HEAD") == "active-feature"
    assert git(linked, "rev-parse", "HEAD") == caller_head
    assert local_refs(checkout) == refs_before
    assert_detached_at(checkout, target)


def test_branch_deletion_refuses_a_branch_not_merged_into_origin_main(checkout: Path) -> None:
    # Replacing -d with -D would discard this genuinely unmerged candidate.
    git(checkout, "checkout", "-qb", "merged-feature")
    (checkout / "feature-only.txt").write_text("unmerged work\n", encoding="utf-8")
    git(checkout, "add", "feature-only.txt")
    git(checkout, "commit", "-qm", "unmerged feature")
    git(checkout, "checkout", "-q", "--detach", "origin/main")
    target = advance_remote(checkout)
    refs_before = local_refs(checkout)
    assert git(checkout, "log", "--oneline", "origin/main..merged-feature") != ""

    result = run_step7(checkout, following_delete=True)

    assert result.returncode != 0, (result.stdout, result.stderr)
    assert "取り込みを確認できない" in result.stderr
    assert local_refs(checkout) == refs_before
    assert_detached_at(checkout, target)


def test_final_status_from_linked_project_reports_main_not_dirty_caller(checkout: Path) -> None:
    # A cwd-based status reports the caller's edit instead of the updated tree.
    linked = checkout.parent / "linked feature"
    git(checkout, "worktree", "add", "-qb", "active-feature", str(linked))
    project = linked / "project"
    project.mkdir()
    (linked / "base.txt").write_text("caller edit\n", encoding="utf-8")
    caller_head = git(linked, "rev-parse", "HEAD")
    caller_status = git(linked, "status")
    target = advance_remote(checkout)
    update = run_step7(checkout, cwd=project)
    assert update.returncode == 0, (update.stdout, update.stderr)
    assert_detached_at(checkout, target)

    result = subprocess.run(
        ["bash", "--noprofile", "--norc", "-c", step_bash(11).splitlines()[0]],
        cwd=project,
        env={**os.environ, "MAIN_ROOT": str(checkout)},
        capture_output=True,
        text=True,
        timeout=20,
    )

    assert result.returncode == 0, (result.stdout, result.stderr)
    assert result.stdout.strip() == git(checkout, "status")
    assert result.stdout.strip() != caller_status
    assert git(linked, "status") == caller_status
    assert git(linked, "symbolic-ref", "--short", "HEAD") == "active-feature"
    assert git(linked, "rev-parse", "HEAD") == caller_head


@pytest.mark.parametrize("dirty_kind", ["tracked", "untracked", "failed-status"])
def test_unclean_or_unreadable_main_tree_stops_before_checkout_and_branch_deletion(
    checkout: Path, dirty_kind: str
) -> None:
    git(checkout, "branch", "merged-feature")
    advance_remote(checkout)
    protected = {
        "tracked": checkout / "base.txt",
        "untracked": checkout / "untracked draft.txt",
        "failed-status": checkout / ".git" / "index",
    }[dirty_kind]
    protected.write_bytes(b"unsaved data\n")
    refs_before = local_refs(checkout)
    head_before = git(checkout, "rev-parse", "HEAD")

    result = run_step7(checkout, following_delete=True)

    assert result.returncode != 0, (result.stdout, result.stderr)
    assert protected.read_bytes() == b"unsaved data\n"
    assert local_refs(checkout) == refs_before, "cleanup proceeded to branch deletion"
    assert git(checkout, "rev-parse", "HEAD") == head_before
    assert git(checkout, "rev-parse", "--abbrev-ref", "HEAD") == "HEAD"


def test_ignored_file_collision_aborts_without_losing_data_or_branch_refs(checkout: Path) -> None:
    git(checkout, "branch", "merged-feature")
    (checkout / "private.txt").write_bytes(b"private unsaved draft\n")
    advance_remote(checkout, "private.txt")
    assert git(checkout, "status", "--short") == "", "fixture must be ignored, not dirty"
    refs_before = local_refs(checkout)
    head_before = git(checkout, "rev-parse", "HEAD")

    result = run_step7(checkout, following_delete=True)

    assert (checkout / "private.txt").read_bytes() == b"private unsaved draft\n"
    assert result.returncode != 0, (result.stdout, result.stderr)
    assert local_refs(checkout) == refs_before
    assert_detached_at(checkout, head_before)


def test_steps_8_and_11_stop_when_main_root_is_unset_instead_of_using_callers_repo(
    checkout: Path,
) -> None:
    # Tool calls can run in a fresh shell where MAIN_ROOT is unset. `git -C ""`
    # then silently targets the caller's repo: a stale linked HEAD makes -d
    # reject a merged branch, and a foreign cwd can even delete its own refs.
    # Every MAIN_ROOT command must fail fast instead of falling back.
    linked = checkout.parent / "linked feature"
    git(checkout, "worktree", "add", "-qb", "active-feature", str(linked))
    project = linked / "project"
    project.mkdir()
    foreign = checkout.parent / "foreign repo"
    foreign.mkdir()
    git(foreign, "init", "-q", "-b", "trunk")
    (foreign / "f.txt").write_text("foreign\n", encoding="utf-8")
    git(foreign, "add", ".")
    git(foreign, "commit", "-qm", "foreign commit")
    git(foreign, "branch", "merged-feature")  # merged into foreign's HEAD: -d would delete it
    target = advance_remote(checkout)
    git(checkout, "branch", "merged-feature", target)  # merged into origin/main but not linked HEAD
    env = {k: v for k, v in os.environ.items() if k != "MAIN_ROOT"}
    refs_checkout = local_refs(checkout)
    refs_foreign = local_refs(foreign)

    for cwd in (project, foreign):
        delete = run_bash(
            step_bash(8).replace("<branch>", "merged-feature"), cwd=cwd, env=env
        )
        assert delete.returncode != 0
        assert "MAIN_ROOT" in delete.stderr
        assert "not fully merged" not in delete.stderr
        for line in step_bash(11).splitlines():
            report = run_bash(line, cwd=cwd, env=env)
            assert report.returncode != 0, line
            assert "MAIN_ROOT" in report.stderr
            assert report.stdout == ""

    assert local_refs(checkout) == refs_checkout
    assert local_refs(foreign) == refs_foreign
    assert git(linked, "symbolic-ref", "--short", "HEAD") == "active-feature"


def test_step8_uses_the_route_specific_root(checkout: Path) -> None:
    # A stale TARGET_ROOT from another clone must not override the MAIN_ROOT
    # whose clean detached checkout step 7 verified. The fork path may still
    # use TARGET_ROOT when MAIN_ROOT is absent.
    remote = checkout.parent / "remote.git"
    foreign = checkout.parent / "foreign clone"
    git(checkout.parent, "clone", "-q", str(remote), str(foreign))
    target = git(checkout, "rev-parse", "origin/main")
    git(checkout, "branch", "merged-feature", target)
    git(foreign, "branch", "merged-feature", target)
    prs = {"7": pr_payload("merged-feature", target, merge=target)}
    commands = section_bash(EVIDENCE_TITLE) + "\n" + step_bash(8).replace(
        "<branch>", "merged-feature"
    )
    env = {
        **os.environ,
        **fake_gh_environment(checkout, prs),
        "MAIN_ROOT": str(checkout),
        "TARGET_ROOT": str(foreign),
        "PR_NUMBER": "7",
        "BASE_REF": "refs/remotes/origin/main",
    }

    conflicting = run_bash(commands, cwd=checkout, env=env)

    assert conflicting.returncode != 0, (conflicting.stdout, conflicting.stderr)
    assert "TARGET_ROOT" in conflicting.stderr
    assert "refs/heads/merged-feature " in local_refs(checkout)
    assert "refs/heads/merged-feature " in local_refs(foreign)

    fork_env = {key: value for key, value in env.items() if key != "MAIN_ROOT"}
    fork_env["TARGET_ROOT"] = str(checkout)
    accepted = run_bash(commands, cwd=checkout, env=fork_env)

    assert accepted.returncode == 0, (accepted.stdout, accepted.stderr)
    assert "refs/heads/merged-feature " not in local_refs(checkout)
    assert "refs/heads/merged-feature " in local_refs(foreign)


def test_step8_gates_dash_d_on_selected_base_and_rechecks_before_dash_D(
    checkout: Path,
) -> None:
    # Fork-like target: HEAD is a detached commit that predates the merge and
    # must not move, so -d refuses a branch that IS merged into the base. The
    # `not fully merged` arm must re-check the same PR/base evidence before -D.
    # The unmerged branch has an upstream pointing at itself, which would let
    # -d succeed; the pre-check must keep it because the selected base lacks it.
    stale = git(checkout, "rev-parse", "HEAD")
    target = advance_remote(checkout)
    git(checkout, "checkout", "-q", "--detach", stale)
    git(checkout, "branch", "--no-track", "merged-feature", target)
    git(checkout, "checkout", "-qb", "unmerged-feature", stale)
    (checkout / "unmerged.txt").write_text("local only\n", encoding="utf-8")
    git(checkout, "add", "unmerged.txt")
    git(checkout, "commit", "-qm", "unmerged work")
    unmerged_head = git(checkout, "rev-parse", "HEAD")
    git(checkout, "checkout", "-q", "--detach", stale)
    git(checkout, "update-ref", "refs/remotes/origin/unmerged-feature", unmerged_head)
    git(checkout, "branch", "--set-upstream-to=origin/unmerged-feature", "unmerged-feature")
    prs = {
        "7": pr_payload("merged-feature", target, merge=target),
        "8": pr_payload("unmerged-feature", unmerged_head, merge=unmerged_head),
    }

    merged = run_step8(checkout, "merged-feature", prs, number="7")

    assert merged.returncode == 0, (merged.stdout, merged.stderr)
    assert "not fully merged" in merged.stderr
    assert "refs/heads/merged-feature " not in local_refs(checkout)

    unmerged = run_step8(checkout, "unmerged-feature", prs, number="8")

    assert unmerged.returncode != 0, (unmerged.stdout, unmerged.stderr)
    assert "取り込みを確認できない" in unmerged.stderr
    assert "refs/heads/unmerged-feature " in local_refs(checkout)


def test_cleanup_keeps_the_forks_local_main_out_of_deletion_candidates() -> None:
    # The fork's local `main` is the base ref that resoloop-fork.sh sync
    # maintains. A synced main has an empty `upstream/main..main` log, so it
    # would appear as a merged candidate and step 8's -d would delete the
    # user's base ref. Pin the exclusion's existence: a fixed wording check is
    # allowed here because the guard protects a user-owned base ref.
    for step in (3, 8):
        assert re.search(r"external/resoloop[^\n]*`main`", step_text(step)), (
            f"step {step} must exclude the fork's local main from deletion"
        )


def test_checkout_lock_failure_stops_before_subsequent_branch_deletion(checkout: Path) -> None:
    git(checkout, "branch", "merged-feature")
    advance_remote(checkout)
    lock = checkout / ".git" / "index.lock"
    lock.write_bytes(b"do not remove a lock\n")
    refs_before = local_refs(checkout)
    head_before = git(checkout, "rev-parse", "HEAD")

    result = run_step7(checkout, following_delete=True)

    assert result.returncode != 0, (result.stdout, result.stderr)
    assert local_refs(checkout) == refs_before
    assert lock.read_bytes() == b"do not remove a lock\n"
    assert_detached_at(checkout, head_before)


# These five roots are user-owned safety boundaries. Omitting any one from the
# deletion guard can remove clean tracked world data during checkout.
PROTECTED_WORLD_ROOTS = ["MyResoniteProject", "akichi", "slum02", "slum03", "worlds"]


def snapshot_paths(*roots: Path) -> dict[str, tuple[object, ...]]:
    """Read only fixture paths, never follow symlinks outside the scratch repo.

    Include Git's index, refs, HEAD and raw reflogs as well as file bytes,
    modes and inode/link identity. Access times are excluded because reading
    the snapshot itself can update them.
    """
    state = {}
    for number, root in enumerate(roots):
        paths = [root, *sorted(root.rglob("*"))] if root.is_dir() else [root]
        for path in paths:
            info = path.lstat()
            payload = (
                os.readlink(path) if path.is_symlink()
                else path.read_bytes() if path.is_file()
                else None
            )
            relative = path.relative_to(root)
            # status may replace a byte-identical index via index.lock. Cache
            # inode/timestamps (and the containing directory's timestamps) are
            # not Git state; retain the index bytes/mode in the comparison.
            if relative in (Path(".git"), Path(".git/index")):
                state[f"{number}/{relative}"] = (info.st_mode, payload)
            else:
                state[f"{number}/{relative}"] = (
                    info.st_mode, info.st_dev, info.st_ino, info.st_nlink,
                    info.st_size, info.st_mtime_ns, info.st_ctime_ns, payload,
                )
    return state


def publish_world_changes(work: Path) -> str:
    publisher = work.parent / "publisher"
    git(publisher, "push", "-q", "origin", "main")
    git(work, "fetch", "-q", "--all", "--prune")
    return git(publisher, "rev-parse", "HEAD")


def tracked_world_fixture(work: Path, region: str) -> tuple[str, Path]:
    publisher = work.parent / "publisher"
    world = publisher / region
    world.mkdir()
    source = f"{region}/source.py"
    (publisher / source).write_bytes(b"#!/usr/bin/env python\nprint('world source')\n")
    (publisher / source).chmod(0o755)
    (world / "source-link").symlink_to("source.py")
    git(publisher, "add", region)
    git(publisher, "commit", "-qm", "tracked world source and link")
    publish_world_changes(work)
    git(work, "checkout", "-q", "--detach", "origin/main")
    git(work, "branch", "main")
    git(work, "branch", "merged-feature")

    # Local cache/excludes and a hardlink peer outside the worktree must not be
    # touched by a refusal. Every path remains under pytest's temporary root.
    cache = work / region / ".uv-cache" / "cache.bin"
    cache.parent.mkdir()
    cache.write_bytes(b"ignored cached world data\x00\xff")
    cache.chmod(0o640)
    with (work / ".git" / "info" / "exclude").open("a", encoding="utf-8") as stream:
        stream.write(f"\n/{region}/.uv-cache/\n")
    files = work.parent / "files"
    files.mkdir()
    peer = files / "shared source.py"
    os.link(work / source, peer)
    assert git(work, "status", "--short", "--untracked-files=all") == ""
    return source, peer


@pytest.mark.parametrize("region", PROTECTED_WORLD_ROOTS)
def test_tracked_world_deletion_stops_without_mutating_any_local_state(
    checkout: Path, region: str
) -> None:
    # A clean index and --no-overwrite-ignore do not protect tracked deletions.
    # Removing this guard would delete the source and advance HEAD/branch cleanup.
    source, peer = tracked_world_fixture(checkout, region)
    publisher = checkout.parent / "publisher"
    git(publisher, "rm", source)
    git(publisher, "commit", "-qm", "untrack one world source")
    publish_world_changes(checkout)
    assert git(checkout, "status", "--short", "--untracked-files=all") == ""
    assert git(checkout, "diff", "--no-renames", "--name-only", "--diff-filter=D",
               "HEAD", "origin/main") == source
    before = snapshot_paths(checkout, peer)

    result = run_step7(checkout, following_delete=True)

    assert snapshot_paths(checkout, peer) == before
    assert result.returncode != 0, (result.stdout, result.stderr)
    assert source in result.stdout, "the refused deletion must be listed to the user"
    assert "README" in result.stderr, "the user needs the preservation procedure"


def test_world_source_rename_outside_protected_roots_is_treated_as_deletion(checkout: Path) -> None:
    # A rename does not exempt the original protected path from the deletion
    # gate, even when an unrestricted diff identifies the move as R100.
    source, peer = tracked_world_fixture(checkout, "worlds")
    publisher = checkout.parent / "publisher"
    git(publisher, "mv", source, "moved-source.py")
    git(publisher, "commit", "-qm", "move world source outside protected roots")
    publish_world_changes(checkout)
    assert git(checkout, "status", "--short", "--untracked-files=all") == ""
    assert git(checkout, "diff", "--name-status", "-M", "HEAD", "origin/main") == (
        f"R100\t{source}\tmoved-source.py"
    )
    before = snapshot_paths(checkout, peer)

    result = run_step7(checkout, following_delete=True)

    assert snapshot_paths(checkout, peer) == before
    assert result.returncode != 0, (result.stdout, result.stderr)
    assert source in result.stdout


def test_deleted_path_diff_error_stops_before_checkout_or_branch_deletion(
    checkout: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Only diff fails: origin/main, status and every real checkout prerequisite
    # are valid. Ignoring a failed deletion query must not advance the tree.
    _, peer = tracked_world_fixture(checkout, "worlds")
    advance_remote(checkout)
    assert git(checkout, "status", "--short", "--untracked-files=all") == ""
    real_git = shutil.which("git")
    assert real_git
    tools = checkout.parent / "tools"
    tools.mkdir()
    wrapper = tools / "git"
    wrapper.write_text(
        '#!/bin/bash\n'
        'printf "%s\\0" "$@" >> "$GIT_CALL_LOG"\n'
        'printf "\\n" >> "$GIT_CALL_LOG"\n'
        'if [ "$1" = -C ] && [ "$3" = diff ]; then\n'
        '    printf "%s\\n" "injected diff read failure" >&2\n'
        '    exit 73\n'
        'fi\n'
        'exec "$REAL_GIT" "$@"\n',
        encoding="utf-8",
    )
    wrapper.chmod(0o755)
    log = tools / "git-calls.log"
    log.write_bytes(b"")
    monkeypatch.setenv("PATH", f"{tools}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("REAL_GIT", real_git)
    monkeypatch.setenv("GIT_CALL_LOG", str(log))
    before = snapshot_paths(checkout, peer)
    calls_before = log.read_bytes()

    result = run_step7(checkout, following_delete=True)

    assert snapshot_paths(checkout, peer) == before
    assert result.returncode != 0, (result.stdout, result.stderr)
    calls = log.read_bytes()[len(calls_before):].splitlines()
    assert [line.decode().split("\x00")[:-1] for line in calls] == [
        ["-C", str(checkout), "status", "--short", "--untracked-files=all"],
        ["-C", str(checkout), "diff", "--no-renames", "--name-only", "--diff-filter=D",
         "HEAD", "origin/main", "--", *PROTECTED_WORLD_ROOTS],
    ], "only the read-only status/diff queries may run; checkout must not be called"


def test_protected_world_update_from_linked_project_deletes_only_merged_branch(
    checkout: Path,
) -> None:
    # Normal counterpart of the refusal tests above: refusing every world
    # change, or running step 8 against the caller's stale linked HEAD or not
    # at all, still passes them. Only the merged candidate may be deleted.
    source, peer = tracked_world_fixture(checkout, "worlds")
    linked = checkout.parent / "linked feature"
    git(checkout, "worktree", "add", "-qb", "active-feature", str(linked))
    project = linked / "project"
    project.mkdir()
    caller_head = git(linked, "rev-parse", "HEAD")
    publisher = checkout.parent / "publisher"
    (publisher / source).write_bytes(b"updated world source\n")
    git(publisher, "add", source)
    git(publisher, "commit", "-qm", "update world source without deletion")
    target = publish_world_changes(checkout)
    git(checkout, "branch", "-f", "merged-feature", target)
    assert git(checkout, "diff", "--no-renames", "--name-only", "HEAD", "origin/main") == source
    assert git(checkout, "diff", "--no-renames", "--name-only", "--diff-filter=D",
               "HEAD", "origin/main") == ""
    assert git(checkout, "log", "--oneline", "origin/main..merged-feature") == ""
    assert git(linked, "log", "--oneline", "HEAD..merged-feature") != ""
    retained_refs = "\n".join(
        line for line in local_refs(checkout).splitlines()
        if not line.startswith("refs/heads/merged-feature ")
    )
    cache_before = snapshot_paths(checkout / "worlds" / ".uv-cache")
    # Checkout unlinks the worktree path, so the peer's link count and ctime
    # change; its own inode and bytes must not.
    peer_before = (peer.lstat().st_ino, peer.read_bytes())

    result = run_step7(
        checkout, cwd=project, following_delete=True,
        prs={"7": pr_payload("merged-feature", target, merge=target)},
    )

    assert result.returncode == 0, (result.stdout, result.stderr)
    assert_detached_at(checkout, target)
    assert (checkout / source).read_bytes() == b"updated world source\n"
    assert local_refs(checkout) == retained_refs, "only the merged candidate may be deleted"
    assert git(linked, "symbolic-ref", "--short", "HEAD") == "active-feature"
    assert git(linked, "rev-parse", "HEAD") == caller_head
    assert snapshot_paths(checkout / "worlds" / ".uv-cache") == cache_before
    assert (peer.lstat().st_ino, peer.read_bytes()) == peer_before
