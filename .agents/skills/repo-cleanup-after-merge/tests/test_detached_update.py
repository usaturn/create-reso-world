"""Execute cleanup update, deletion and status against disposable Git repositories.

These regressions catch attaching/creating/moving local main, targeting the
caller's linked worktree, deleting against its stale HEAD, proceeding after a
failed cleanliness/checkout gate,
and Git's default overwrite of ignored user files. Expected Git state comes
from the fixtures, not from the skill's wording or eval lists.
"""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

import pytest

SKILL = Path(__file__).resolve().parents[1] / "SKILL.md"


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
        if name.startswith("GIT_") or name in {"BASH_ENV", "ENV", "MAIN_ROOT"}:
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


def run_bash(commands: str, *, cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", "--noprofile", "--norc", "-c", commands],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
    )


def run_step7(
    work: Path, *, cwd: Path | None = None, following_delete: bool = False
) -> subprocess.CompletedProcess[str]:
    commands = step_bash(7)
    if following_delete:
        # Execute the actual step 8 in the same shell. Step 7 must stop it
        # itself on failure; the harness deliberately does not add -e or -C.
        commands += "\n" + step_bash(8).replace("<branch>", "merged-feature")
    return subprocess.run(
        ["bash", "--noprofile", "--norc", "-c", commands],
        cwd=cwd or work,
        env={**os.environ, "MAIN_ROOT": str(work)},
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


def test_repeated_cleanup_follows_remote_advancement_without_creating_main(checkout: Path) -> None:
    base = git(checkout, "rev-parse", "origin/main")
    for filename in (None, None, "incoming.txt"):
        target = base if filename is None else advance_remote(checkout, filename)
        result = run_step7(checkout)
        assert result.returncode == 0, (result.stdout, result.stderr)
        assert_detached_at(checkout, target)
        assert local_refs(checkout) == "", "cleanup must never create local main"


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


@pytest.mark.parametrize("upstream_state", ["unset", "pruned"])
def test_branch_deletion_from_linked_project_uses_updated_main_head(
    checkout: Path, upstream_state: str
) -> None:
    # Using the caller's stale HEAD rejects a branch already in origin/main
    # when there is no usable upstream. Only the deletion candidate may go.
    git(checkout, "branch", "main")
    linked = checkout.parent / "linked feature"
    git(checkout, "worktree", "add", "-qb", "active-feature", str(linked))
    project = linked / "project"
    project.mkdir()
    caller_head = git(linked, "rev-parse", "HEAD")
    caller_reflog = git(linked, "reflog", "show", "HEAD")
    main_reflog = git(checkout, "reflog", "show", "main")
    target = advance_remote(checkout)
    git(checkout, "branch", "merged-feature", target)
    if upstream_state == "pruned":
        git(checkout, "push", "-qu", "origin", "merged-feature")
        git(checkout.parent / "publisher", "push", "-q", "origin", "--delete", "merged-feature")
        git(checkout, "fetch", "-q", "--prune")
    assert git(checkout, "log", "--oneline", "origin/main..merged-feature") == ""
    assert git(linked, "log", "--oneline", "HEAD..merged-feature") != ""
    retained_refs = "\n".join(
        line for line in local_refs(checkout).splitlines()
        if not line.startswith("refs/heads/merged-feature ")
    )

    result = run_step7(checkout, cwd=project, following_delete=True)

    assert result.returncode == 0, result.stderr
    assert local_refs(checkout) == retained_refs, "only the candidate may be deleted"
    assert git(checkout, "reflog", "show", "main") == main_reflog
    assert git(linked, "symbolic-ref", "--short", "HEAD") == "active-feature"
    assert git(linked, "rev-parse", "HEAD") == caller_head
    assert git(linked, "reflog", "show", "HEAD") == caller_reflog
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
    assert "not fully merged" in result.stderr
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


def test_dirty_main_tree_is_rechecked_even_when_callers_linked_tree_is_clean(checkout: Path) -> None:
    linked = checkout.parent / "linked feature"
    git(checkout, "worktree", "add", "-qb", "active-feature", str(linked))
    git(checkout, "branch", "merged-feature")
    advance_remote(checkout)
    (checkout / "base.txt").write_text("main worktree edit\n", encoding="utf-8")
    head_before = git(checkout, "rev-parse", "HEAD")
    caller_head = git(linked, "rev-parse", "HEAD")
    refs_before = local_refs(checkout)
    assert git(linked, "status", "--short") == ""

    result = run_step7(checkout, cwd=linked, following_delete=True)

    assert result.returncode != 0, (result.stdout, result.stderr)
    assert git(checkout, "rev-parse", "HEAD") == head_before
    assert git(linked, "symbolic-ref", "--short", "HEAD") == "active-feature"
    assert git(linked, "rev-parse", "HEAD") == caller_head
    assert local_refs(checkout) == refs_before
    assert (checkout / "base.txt").read_text(encoding="utf-8") == "main worktree edit\n"


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


def test_step11_reports_main_root_even_when_called_from_another_repo(
    checkout: Path,
) -> None:
    foreign = checkout.parent / "foreign repo"
    foreign.mkdir()
    git(foreign, "init", "-q", "-b", "trunk")
    (foreign / "f.txt").write_text("foreign\n", encoding="utf-8")
    git(foreign, "add", ".")
    git(foreign, "commit", "-qm", "foreign commit")

    env = {**os.environ, "MAIN_ROOT": str(checkout)}
    expected = [
        git(checkout, "status"),
        git(checkout, "worktree", "list"),
        git(checkout, "branch", "-a"),
    ]
    for line, want in zip(step_bash(11).splitlines(), expected, strict=True):
        result = run_bash(line, cwd=foreign, env=env)
        assert result.returncode == 0, (line, result.stderr)
        assert result.stdout.strip() == want


def test_step8_recheck_for_not_fully_merged_discriminates_merge_state(
    checkout: Path,
) -> None:
    # Fork-like target: HEAD is a detached commit that predates the merge and
    # must not move, so -d refuses a branch that IS merged into the base. The
    # `not fully merged` arm must re-check with merge-base before concluding,
    # and only then may -D delete the verified branch.
    recheck = re.search(
        r"`(git -C external/resoloop merge-base --is-ancestor [^`]*)`",
        step_text(8),
    )
    assert recheck, (
        "step 8 must prescribe a merge-base re-check for `not fully merged`"
    )
    stale = git(checkout, "rev-parse", "HEAD")
    target = advance_remote(checkout)
    git(checkout, "checkout", "-q", "--detach", stale)
    git(checkout, "branch", "--no-track", "merged-feature", target)
    git(checkout, "checkout", "-qb", "unmerged-feature", stale)
    (checkout / "unmerged.txt").write_text("local only\n", encoding="utf-8")
    git(checkout, "add", "unmerged.txt")
    git(checkout, "commit", "-qm", "unmerged work")
    git(checkout, "checkout", "-q", "--detach", stale)

    refused = subprocess.run(
        ["git", "-C", str(checkout), "branch", "-d", "merged-feature"],
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert refused.returncode != 0
    assert "not fully merged" in refused.stderr

    def recheck_for(branch: str) -> subprocess.CompletedProcess[str]:
        command = (
            recheck.group(1)
            .replace("external/resoloop", f'"{checkout}"')
            .replace("<branch>", branch)
            .replace("<基準>", "origin/main")
        )
        return run_bash(command, cwd=checkout, env=dict(os.environ))

    assert recheck_for("merged-feature").returncode == 0
    assert recheck_for("unmerged-feature").returncode != 0
    git(checkout, "branch", "-D", "merged-feature")
    assert "refs/heads/merged-feature" not in local_refs(checkout)
    assert "refs/heads/unmerged-feature" in local_refs(checkout)


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
