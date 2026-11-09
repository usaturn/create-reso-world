"""S: retire residual PR-review refs only after ownership and use are proven.

Deleting a ref just because its PR number is closed in the cleanup target can
destroy another repository's review pin, an open PR's fetched head, or a
retained session's object. A ref changed after inventory must stay at its new
value. The closed-PR case keeps a predicate that refuses every ref from passing.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import sys

import pytest

SKILL = Path(__file__).resolve().parents[1] / "SKILL.md"
TITLE = "残存 pinned ref を整理する"
PR_REPO = "usaturn/create-reso-world"


def section_bash(index: int = 0) -> str:
    section = re.search(
        rf"^### {re.escape(TITLE)}\n(.*?)(?=^### |^## |\Z)",
        SKILL.read_text(encoding="utf-8"),
        re.M | re.S,
    )
    assert section, f"cleanup has no {TITLE} section"
    blocks = re.findall(r"```bash\n(.*?)```", section.group(1), re.S)
    assert len(blocks) > index, f"{TITLE} has no bash block {index}"
    return blocks[index]


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, timeout=20
    )
    assert result.returncode == 0, (args, result.stdout, result.stderr)
    return result.stdout.strip()


def git_result(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, timeout=20
    )


@pytest.fixture(autouse=True)
def isolated_git_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Inherited selectors, shell startup files and fixture variables must not
    # redirect the temporary repositories or the fake API.
    for name in tuple(os.environ):
        if name.startswith("GIT_") or name in {
            "BASH_ENV", "ENV", "REF_CHECKOUT", "REF_REPOS", "REF_SESSION_ROOT",
            "REF_INVENTORY", "PR_REPO", "PR_NUMBER", "BASE_REF", "REMOTE",
        }:
            monkeypatch.delenv(name)
    home = tmp_path / "home"
    home.mkdir()
    scratch = tmp_path / "scratch tmp"
    scratch.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("TMPDIR", str(scratch))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(home / "config"))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_AUTHOR_NAME", "Cleanup test")
    monkeypatch.setenv("GIT_AUTHOR_EMAIL", "cleanup@example.invalid")
    monkeypatch.setenv("GIT_COMMITTER_NAME", "Cleanup test")
    monkeypatch.setenv("GIT_COMMITTER_EMAIL", "cleanup@example.invalid")
    monkeypatch.setenv("LC_ALL", "C")


@pytest.fixture()
def work(tmp_path: Path) -> Path:
    remote = tmp_path / "remote.git"
    remote.mkdir()
    git(remote, "init", "-q", "--bare", "-b", "main")
    publisher = tmp_path / "publisher"
    publisher.mkdir()
    git(publisher, "init", "-q", "-b", "main")
    (publisher / "base.txt").write_text("base\n", encoding="utf-8")
    (publisher / "内容.txt").write_text("行1\n行2\n", encoding="utf-8")
    git(publisher, "add", ".")
    git(publisher, "commit", "-qm", "base")
    git(publisher, "remote", "add", "origin", str(remote))
    git(publisher, "push", "-q", "origin", "main")
    checkout = tmp_path / "work tree"
    git(tmp_path, "clone", "-q", str(remote), str(checkout))
    commit_file(checkout, "second.txt", "second\n")
    return checkout


def commit_file(work: Path, name: str, content: str) -> str:
    (work / name).write_text(content, encoding="utf-8")
    git(work, "add", name)
    git(work, "commit", "-qm", f"add {name}")
    return git(work, "rev-parse", "HEAD")


FAKE_GH_SOURCE = f'''#!{sys.executable}
import json, os, sys
args = sys.argv[1:]
fields = "number,state,headRefOid"
if (len(args) != 7 or args[:2] != ["pr", "view"]
        or args[3:5] != ["--repo", args[4]]
        or args[5:] != ["--json", fields]):
    print("unexpected view argv: " + repr(args), file=sys.stderr)
    sys.exit(91)
with open(os.environ["FAKE_GH_PRS_FILE"], encoding="utf-8") as stream:
    prs = json.load(stream)
pr = prs.get(f"{{args[4]}}#{{args[2]}}")
if pr is None:
    print("not found", file=sys.stderr)
    sys.exit(1)
print(json.dumps(pr))
'''


@pytest.fixture()
def fake_gh(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    tools = tmp_path / "fake gh"
    tools.mkdir()
    script = tools / "gh"
    script.write_text(FAKE_GH_SOURCE, encoding="utf-8")
    script.chmod(0o755)
    monkeypatch.setenv("PATH", f"{tools}{os.pathsep}{os.environ['PATH']}")

    def configure(prs: dict[str, dict[str, object]]) -> None:
        path = tmp_path / "pr states.json"
        path.write_text(json.dumps(prs), encoding="utf-8")
        monkeypatch.setenv("FAKE_GH_PRS_FILE", str(path))

    return configure


def pr_state(number: int, state: str, head: str) -> dict[str, object]:
    return {"number": number, "state": state, "headRefOid": head}


def add_ref(work: Path, ref: str, oid: str) -> None:
    git(work, "update-ref", ref, oid)


def run_inventory(work: Path) -> subprocess.CompletedProcess[str]:
    commands = section_bash(0) + '\ncleanup_residual_ref_inventory "$@"\n'
    return subprocess.run(
        ["bash", "--noprofile", "--norc", "-c", commands, "cleanup", str(work)],
        cwd=work, env=dict(os.environ), capture_output=True, text=True, timeout=20,
    )


def run_retire(
    work: Path, ref: str, oid: str, repos: list[str], session_root: Path,
) -> subprocess.CompletedProcess[str]:
    commands = section_bash(0) + '\ncleanup_residual_ref_retire "$@"\n'
    env = {
        **os.environ,
        "REF_REPOS": "\n".join(repos),
        "REF_SESSION_ROOT": str(session_root),
    }
    return subprocess.run(
        ["bash", "--noprofile", "--norc", "-c", commands, "cleanup", str(work), ref, oid],
        cwd=work, env=env, capture_output=True, text=True, timeout=20,
    )


def run_listing_block(
    work: Path, inventory: Path, repos: list[str],
) -> subprocess.CompletedProcess[str]:
    commands = section_bash(0) + "\n" + section_bash(1)
    env = {
        **os.environ,
        "REF_CHECKOUT": str(work),
        "REF_REPOS": "\n".join(repos),
        "REF_INVENTORY": str(inventory),
    }
    return subprocess.run(
        ["bash", "--noprofile", "--norc", "-c", commands, "cleanup"],
        cwd=work, env=env, capture_output=True, text=True, timeout=20,
    )


def run_delete_block(
    work: Path, inventory: Path, repos: list[str], session_root: Path,
) -> subprocess.CompletedProcess[str]:
    commands = section_bash(0) + "\n" + section_bash(2)
    env = {
        **os.environ,
        "REF_CHECKOUT": str(work),
        "REF_REPOS": "\n".join(repos),
        "REF_INVENTORY": str(inventory),
        "REF_SESSION_ROOT": str(session_root),
    }
    return subprocess.run(
        ["bash", "--noprofile", "--norc", "-c", commands, "cleanup"],
        cwd=work, env=env, capture_output=True, text=True, timeout=20,
    )


def test_residual_ref_inventory_only_lists_refs(work: Path, tmp_path: Path) -> None:
    tip = git(work, "rev-parse", "HEAD")
    base = git(work, "rev-parse", "HEAD^")
    refs = {
        f"refs/pr-review/repos/{PR_REPO}/42": tip,
        "refs/pr-review/42": base,
    }
    for ref, oid in refs.items():
        add_ref(work, ref, oid)

    result = run_inventory(work)

    assert result.returncode == 0, (result.stdout, result.stderr)
    listed = result.stdout.splitlines()
    for ref, oid in refs.items():
        assert f"{ref} {oid}" in listed
        assert git(work, "rev-parse", "--verify", ref) == oid


def test_residual_ref_is_deleted_after_its_pr_closed(
    work: Path, fake_gh, tmp_path: Path,
) -> None:
    oid = git(work, "rev-parse", "HEAD")
    ref = f"refs/pr-review/repos/{PR_REPO}/42"
    add_ref(work, ref, oid)
    fake_gh({f"{PR_REPO}#42": pr_state(42, "CLOSED", oid)})
    sessions = tmp_path / "empty sessions"
    sessions.mkdir()

    result = run_retire(work, ref, oid, [PR_REPO], sessions)

    assert result.returncode == 0, (result.stdout, result.stderr)
    assert "削除:" in result.stdout
    assert git_result(work, "show-ref", "--verify", "--quiet", ref).returncode != 0


def test_residual_ref_keeps_an_open_pr_from_its_own_repository(
    work: Path, fake_gh, tmp_path: Path,
) -> None:
    # The cleanup target's PR #7 is closed. Only the ref path identifies the
    # other repository, whose PR #7 is still open. Looking up the target repo
    # would delete the ref of the open PR.
    oid = git(work, "rev-parse", "HEAD")
    ref_repo = "other/repository"
    ref = f"refs/pr-review/repos/{ref_repo}/7"
    add_ref(work, ref, oid)
    fake_gh({
        f"{PR_REPO}#7": pr_state(7, "CLOSED", oid),
        f"{ref_repo}#7": pr_state(7, "OPEN", oid),
    })
    sessions = tmp_path / "empty sessions"
    sessions.mkdir()

    result = run_retire(work, ref, oid, [PR_REPO], sessions)

    assert result.returncode != 0, (result.stdout, result.stderr)
    assert "保持:" in result.stderr
    assert git(work, "rev-parse", "--verify", ref) == oid


def test_residual_ref_keeps_a_retained_version7_session(
    work: Path, fake_gh, tmp_path: Path,
) -> None:
    oid = git(work, "rev-parse", "HEAD")
    ref = f"refs/pr-review/repos/{PR_REPO}/42"
    add_ref(work, ref, oid)
    fake_gh({f"{PR_REPO}#42": pr_state(42, "MERGED", oid)})
    sessions = tmp_path / "session root"
    session = sessions / "pr-review-42-abcdefgh"
    session.mkdir(parents=True)
    (session / "session.json").write_text(json.dumps({
        "version": 7,
        "main_root": str(work),
        "pr_repository": PR_REPO,
        "pr_number": 42,
    }), encoding="utf-8")

    result = run_retire(work, ref, oid, [PR_REPO], sessions)

    assert result.returncode != 0, (result.stdout, result.stderr)
    assert "session" in result.stderr
    assert git(work, "rev-parse", "--verify", ref) == oid


def test_legacy_ref_keeps_an_ambiguous_fork_or_upstream_owner(
    work: Path, fake_gh, tmp_path: Path,
) -> None:
    oid = git(work, "rev-parse", "HEAD")
    ref = "refs/pr-review/42"
    add_ref(work, ref, oid)
    fake_gh({
        "usaturn/resoloop#42": pr_state(42, "CLOSED", oid),
        "orange3134/resoloop#42": pr_state(42, "MERGED", oid),
    })
    sessions = tmp_path / "empty sessions"
    sessions.mkdir()

    result = run_retire(
        work, ref, oid, ["usaturn/resoloop", "orange3134/resoloop"], sessions,
    )

    assert result.returncode != 0, (result.stdout, result.stderr)
    assert "所属" in result.stderr
    assert git(work, "rev-parse", "--verify", ref) == oid


def test_residual_ref_changed_after_inventory_is_kept_at_the_new_value(
    work: Path, fake_gh, tmp_path: Path,
) -> None:
    old_oid = git(work, "rev-parse", "HEAD^")
    new_oid = git(work, "rev-parse", "HEAD")
    ref = f"refs/pr-review/repos/{PR_REPO}/42"
    add_ref(work, ref, old_oid)
    fake_gh({f"{PR_REPO}#42": pr_state(42, "CLOSED", old_oid)})
    sessions = tmp_path / "empty sessions"
    sessions.mkdir()
    # A concurrent fetch repins the ref after the inventory read.
    add_ref(work, ref, new_oid)

    result = run_retire(work, ref, old_oid, [PR_REPO], sessions)

    assert result.returncode != 0, (result.stdout, result.stderr)
    assert "保持:" in result.stderr
    assert git(work, "rev-parse", "--verify", ref) == new_oid


def test_delete_uses_the_displayed_inventory_value(
    work: Path, fake_gh, tmp_path: Path,
) -> None:
    old_oid = git(work, "rev-parse", "HEAD^")
    new_oid = git(work, "rev-parse", "HEAD")
    ref = f"refs/pr-review/repos/{PR_REPO}/42"
    add_ref(work, ref, old_oid)
    fake_gh({f"{PR_REPO}#42": pr_state(42, "CLOSED", old_oid)})
    sessions = tmp_path / "empty sessions"
    sessions.mkdir()
    inventory = tmp_path / "saved inventory.txt"

    listed = run_listing_block(work, inventory, [PR_REPO])
    assert listed.returncode == 0, (listed.stdout, listed.stderr)
    assert f"{ref} {old_oid}" in listed.stdout.splitlines()
    add_ref(work, ref, new_oid)

    result = run_delete_block(work, inventory, [PR_REPO], sessions)

    assert result.returncode == 0, (result.stdout, result.stderr)
    assert "削除:" not in result.stdout
    assert "読み取り後に ref の値が変わった" in result.stderr
    assert git(work, "rev-parse", "--verify", ref) == new_oid


def test_symbolic_ref_cannot_delete_its_target_branch(
    work: Path, fake_gh, tmp_path: Path,
) -> None:
    target = "refs/heads/main"
    target_oid = git(work, "rev-parse", target)
    ref = f"refs/pr-review/repos/{PR_REPO}/42"
    git(work, "symbolic-ref", ref, target)
    fake_gh({f"{PR_REPO}#42": pr_state(42, "CLOSED", target_oid)})
    sessions = tmp_path / "empty sessions"
    sessions.mkdir()

    listed = run_inventory(work)
    result = run_retire(work, ref, target_oid, [PR_REPO], sessions)

    assert listed.returncode == 0, (listed.stdout, listed.stderr)
    assert ref not in [line.split(" ", 1)[0] for line in listed.stdout.splitlines()]
    assert "symbolic" in listed.stderr
    assert result.returncode != 0, (result.stdout, result.stderr)
    assert "symbolic" in result.stderr
    assert git(work, "rev-parse", "--verify", target) == target_oid
    assert git(work, "symbolic-ref", "-q", ref) == target


def test_malformed_session_ownership_keeps_the_ref(
    work: Path, fake_gh, tmp_path: Path,
) -> None:
    oid = git(work, "rev-parse", "HEAD")
    ref = f"refs/pr-review/repos/{PR_REPO}/42"
    add_ref(work, ref, oid)
    fake_gh({f"{PR_REPO}#42": pr_state(42, "CLOSED", oid)})
    sessions = tmp_path / "session root"
    session = sessions / "pr-review-42-malformed"
    session.mkdir(parents=True)
    (session / "session.json").write_text(json.dumps({
        "version": 7,
        "main_root": str(work),
        "pr_repository": [],
        "pr_number": 42,
    }), encoding="utf-8")

    result = run_retire(work, ref, oid, [PR_REPO], sessions)

    assert result.returncode != 0, (result.stdout, result.stderr)
    assert "保持:" in result.stderr
    assert "所属" in result.stderr
    assert git(work, "rev-parse", "--verify", ref) == oid
