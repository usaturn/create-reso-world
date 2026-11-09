"""S: the shared predicate must prove both the PR and the selected base.

An ancestor-only rule retains squash/rebase branches; trusting `git branch -d`
alone can delete a branch whose upstream points at itself although the selected
base never received it. The positive ancestor/squash/rebase cases keep a
predicate that simply refuses every branch from passing.
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
PR_REPO = "usaturn/create-reso-world"
EVIDENCE_TITLE = "branch の取り込み判定"
GATE_B_TITLE = "9. ゲート B: リモート branch の削除はユーザー確認を得る"


def section_bash(title: str, index: int = 0) -> str:
    section = re.search(
        rf"^### {re.escape(title)}\n(.*?)(?=^### |^## |\Z)",
        SKILL.read_text(encoding="utf-8"),
        re.M | re.S,
    )
    assert section, f"cleanup has no executable {title} block"
    blocks = re.findall(r"```bash\n(.*?)```", section.group(1), re.S)
    assert len(blocks) > index, f"cleanup has no executable {title} block {index}"
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


def is_ancestor(repo: Path, ref: str, base: str) -> bool:
    return git_result(repo, "merge-base", "--is-ancestor", ref, base).returncode == 0


@pytest.fixture(autouse=True)
def isolated_git_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Inherited selectors, shell startup files and fixture variables must not
    # redirect the temporary repositories or the fake API.
    for name in tuple(os.environ):
        if name.startswith("GIT_") or name in {
            "BASH_ENV", "ENV", "CHECKOUT", "PR_REPO", "PR_NUMBER", "BASE_REF", "REMOTE",
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
def work(tmp_path: Path) -> Path:
    remote = tmp_path / "remote.git"
    remote.mkdir()
    git(remote, "init", "-q", "--bare", "-b", "main")
    publisher = tmp_path / "publisher"
    publisher.mkdir()
    git(publisher, "init", "-q", "-b", "main")
    (publisher / "base.txt").write_text("base\n", encoding="utf-8")
    git(publisher, "add", ".")
    git(publisher, "commit", "-qm", "base")
    git(publisher, "remote", "add", "origin", str(remote))
    git(publisher, "push", "-q", "origin", "main")
    checkout = tmp_path / "work tree"
    git(tmp_path, "clone", "-q", str(remote), str(checkout))
    return checkout


FAKE_GH_SOURCE = f'''#!{sys.executable}
import json, os, sys
args = sys.argv[1:]
fields = "state,headRefName,headRefOid,mergeCommit,isCrossRepository,headRepository,headRepositoryOwner"
repo = os.environ["FAKE_GH_REPO"]
with open(os.environ["FAKE_GH_PRS_FILE"], encoding="utf-8") as stream:
    prs = json.load(stream)
if args[:2] == ["pr", "view"]:
    if len(args) != 7 or args[3:5] != ["--repo", repo] or args[5:] != ["--json", fields]:
        print("unexpected view argv: " + repr(args), file=sys.stderr)
        sys.exit(91)
    pr = prs.get(args[2])
    if pr is None:
        print("not found", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(pr))
elif args[:2] == ["pr", "list"]:
    expected = ["pr", "list", "--state", "all", "--head",
                args[5] if len(args) > 5 else "", "--repo", repo,
                "--json", "number,headRefName,headRefOid", "--limit", "100"]
    if args != expected:
        print("unexpected list argv: " + repr(args), file=sys.stderr)
        sys.exit(91)
    branch = args[5]
    matched = [dict(number=pr["number"], headRefName=pr["headRefName"],
                    headRefOid=pr["headRefOid"])
               for pr in prs.values() if pr.get("headRefName") == branch]
    print(json.dumps(matched))
else:
    print("unexpected argv: " + repr(args), file=sys.stderr)
    sys.exit(92)
'''


@pytest.fixture()
def fake_gh(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    tools = tmp_path / "fake gh"
    tools.mkdir()
    script = tools / "gh"
    script.write_text(FAKE_GH_SOURCE, encoding="utf-8")
    script.chmod(0o755)
    monkeypatch.setenv("PATH", f"{tools}{os.pathsep}{os.environ['PATH']}")

    def configure(prs: dict[str, dict[str, object]], repo: str = PR_REPO) -> None:
        path = tmp_path / "prs.json"
        path.write_text(json.dumps(prs), encoding="utf-8")
        monkeypatch.setenv("FAKE_GH_PRS_FILE", str(path))
        monkeypatch.setenv("FAKE_GH_REPO", repo)

    return configure


def pr_payload(
    number: int, branch: str, head: str, *, state: str = "MERGED",
    merge: str | None = None, cross: bool = False, head_repo: str = PR_REPO,
) -> dict[str, object]:
    owner, name = head_repo.split("/")
    return {
        "number": number,
        "state": state,
        "headRefName": branch,
        "headRefOid": head,
        "mergeCommit": None if merge is None else {"oid": merge},
        "isCrossRepository": cross,
        "headRepository": {"id": "R_fixture", "name": name},
        "headRepositoryOwner": {"id": "U_fixture", "login": owner},
    }


def commit_file(work: Path, name: str, content: str) -> str:
    (work / name).write_text(content, encoding="utf-8")
    git(work, "add", name)
    git(work, "commit", "-qm", f"add {name}")
    return git(work, "rev-parse", "HEAD")


def make_squash(work: Path, branch: str) -> tuple[str, str]:
    git(work, "checkout", "-q", "-b", branch, "main")
    head = commit_file(work, f"{branch} file.txt", f"{branch} content\n")
    git(work, "checkout", "-q", "main")
    git(work, "merge", "--squash", branch)
    git(work, "commit", "-qm", f"squash {branch}")
    squash = git(work, "rev-parse", "HEAD")
    assert not is_ancestor(work, head, "main"), "fixture must not be an ancestor merge"
    return head, squash


def make_rebased(work: Path, branch: str) -> tuple[str, str]:
    git(work, "checkout", "-q", "-b", branch, "main")
    commit_file(work, f"{branch} first.txt", "first\n")
    original = commit_file(work, f"{branch} second.txt", "second\n")
    git(work, "checkout", "-q", "main")
    commit_file(work, "advance base.txt", "advance\n")
    git(work, "checkout", "-q", branch)
    git(work, "rebase", "-q", "main")
    rebased = git(work, "rev-parse", "HEAD")
    assert rebased != original
    git(work, "checkout", "-q", "main")
    git(work, "merge", "-q", "--ff-only", branch)
    git(work, "branch", "-f", branch, original)
    assert git(work, "rev-parse", "main") == rebased
    assert not is_ancestor(work, original, "main")
    assert is_ancestor(work, rebased, "main")
    return original, rebased


def run_evidence(work: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    commands = section_bash(EVIDENCE_TITLE) + '\ncleanup_branch_evidence "$@"\n'
    return subprocess.run(
        ["bash", "--noprofile", "--norc", "-c", commands, "cleanup", *args],
        cwd=work, env=dict(os.environ), capture_output=True, text=True, timeout=20,
    )


def test_branch_evidence_accepts_an_ancestor_with_a_matching_merged_pr(
    work: Path, fake_gh,
) -> None:
    base = git(work, "rev-parse", "main")
    git(work, "branch", "ancestor", base)
    fake_gh({"1": pr_payload(1, "ancestor", base, merge=base)})

    result = run_evidence(
        work, [str(work), PR_REPO, "1", "ancestor", "refs/heads/ancestor", "refs/heads/main"]
    )

    assert result.returncode == 0, (result.stdout, result.stderr)
    assert result.stdout.strip() == "ancestor"


def test_branch_evidence_retains_an_ancestor_without_a_merged_pr(
    work: Path, fake_gh,
) -> None:
    base = git(work, "rev-parse", "main")
    git(work, "branch", "ancestor", base)
    fake_gh({"1": pr_payload(1, "ancestor", base, state="OPEN", merge=base)})

    result = run_evidence(
        work, [str(work), PR_REPO, "1", "ancestor", "refs/heads/ancestor", "refs/heads/main"]
    )

    assert result.returncode != 0, (result.stdout, result.stderr)
    assert result.stdout == ""


def test_branch_evidence_accepts_a_squash_merge_from_the_pr_merge_commit(
    work: Path, fake_gh,
) -> None:
    head, squash = make_squash(work, "squashed")
    fake_gh({"2": pr_payload(2, "squashed", head, merge=squash)})

    result = run_evidence(
        work, [str(work), PR_REPO, "2", "squashed", "refs/heads/squashed", "refs/heads/main"]
    )

    assert result.returncode == 0, (result.stdout, result.stderr)
    assert result.stdout.strip() == "pr"


def test_branch_evidence_accepts_a_rebase_merge_from_the_pr_merge_commit(
    work: Path, fake_gh,
) -> None:
    head, rebased = make_rebased(work, "rebased")
    fake_gh({"3": pr_payload(3, "rebased", head, merge=rebased)})

    result = run_evidence(
        work, [str(work), PR_REPO, "3", "rebased", "refs/heads/rebased", "refs/heads/main"]
    )

    assert result.returncode == 0, (result.stdout, result.stderr)
    assert result.stdout.strip() == "pr"


@pytest.mark.parametrize(
    "mutation",
    ["head-mismatch", "cross-repository", "missing-merge-commit", "missing-state",
     "unknown-pr"],
)
def test_branch_evidence_retains_unproven_pr_evidence(
    work: Path, fake_gh, mutation: str,
) -> None:
    head, squash = make_squash(work, "squashed")
    payload = pr_payload(4, "squashed", head, merge=squash)
    prs: dict[str, dict[str, object]] = {"4": payload}
    if mutation == "head-mismatch":
        payload["headRefOid"] = squash
    elif mutation == "cross-repository":
        payload["isCrossRepository"] = True
    elif mutation == "missing-merge-commit":
        del payload["mergeCommit"]
    elif mutation == "missing-state":
        del payload["state"]
    elif mutation == "unknown-pr":
        prs = {}
    fake_gh(prs)

    result = run_evidence(
        work, [str(work), PR_REPO, "4", "squashed", "refs/heads/squashed", "refs/heads/main"]
    )

    assert result.returncode != 0, (mutation, result.stdout, result.stderr)
    assert result.stdout == ""


UPSTREAM_REPO = "orange3134/resoloop"
FORK_REPO = "usaturn/resoloop"


def make_no_ff(work: Path, branch: str) -> str:
    git(work, "checkout", "-q", "-b", branch, "main")
    head = commit_file(work, f"{branch} file.txt", "fork change\n")
    git(work, "checkout", "-q", "main")
    git(work, "merge", "-q", "--no-ff", "-m", f"merge {branch}", branch)
    return head


@pytest.mark.parametrize("merge_style", ["no-ff", "squash"])
def test_branch_evidence_accepts_an_upstream_pr_only_from_the_verified_fork(
    work: Path, fake_gh, merge_style: str,
) -> None:
    # Upstream PRs from the fork are always cross-repository. They are integrated
    # only when the PR head repository is the verified fork (case-insensitive);
    # another fork that reuses the branch name and head must stay retained.
    if merge_style == "no-ff":
        head = make_no_ff(work, "fork-feature")
        merge, expected = git(work, "rev-parse", "main"), "ancestor"
    else:
        head, merge = make_squash(work, "fork-feature")
        expected = "pr"
    args = [str(work), UPSTREAM_REPO, "7", "fork-feature", "refs/heads/fork-feature",
            "refs/heads/main"]

    def evidence(head_repo: str | None, expected_repo: str | None):
        payload = pr_payload(7, "fork-feature", head, merge=merge, cross=True,
                             head_repo=head_repo or FORK_REPO)
        if head_repo is None:
            del payload["headRepository"]
        fake_gh({"7": payload}, repo=UPSTREAM_REPO)
        return run_evidence(work, args if expected_repo is None else [*args, expected_repo])

    accepted = evidence("UsaTurn/ResoLoop", "usaturn/RESOLOOP")
    assert accepted.returncode == 0, (accepted.stdout, accepted.stderr)
    assert accepted.stdout.strip() == expected

    for head_repo, expected_repo in (
        ("someone/resoloop", FORK_REPO),  # unrelated fork
        (None, FORK_REPO),                # head repository unknown
        (FORK_REPO, ""),                  # route did not verify a fork
        (FORK_REPO, None),                # six-argument caller
    ):
        refused = evidence(head_repo, expected_repo)
        assert refused.returncode != 0, (head_repo, expected_repo, refused.stdout)
        assert refused.stdout == "", (head_repo, expected_repo)


def test_branch_evidence_retains_a_pr_merged_into_another_base(
    work: Path, fake_gh,
) -> None:
    git(work, "checkout", "-q", "-b", "feature", "main")
    feature_head = commit_file(work, "feature.txt", "feature\n")
    git(work, "checkout", "-q", "-b", "release", "main")
    git(work, "merge", "--squash", "feature")
    git(work, "commit", "-qm", "squash into release")
    release_head = git(work, "rev-parse", "HEAD")
    git(work, "checkout", "-q", "main")
    assert not is_ancestor(work, feature_head, "main")
    assert not is_ancestor(work, release_head, "main")
    fake_gh({"5": pr_payload(5, "feature", feature_head, merge=release_head)})
    args = [str(work), PR_REPO, "5", "feature", "refs/heads/feature"]

    refused = run_evidence(work, [*args, "refs/heads/main"])
    accepted = run_evidence(work, [*args, "refs/heads/release"])

    assert refused.returncode != 0, (refused.stdout, refused.stderr)
    assert refused.stdout == ""
    assert accepted.returncode == 0, (accepted.stdout, accepted.stderr)
    assert accepted.stdout.strip() == "pr"


def test_branch_pr_number_requires_exactly_one_matching_head(
    work: Path, fake_gh,
) -> None:
    # Two PRs sharing the branch and head are ambiguous; picking either could
    # let one merged PR hide an open PR that still uses the branch.
    base = git(work, "rev-parse", "main")
    git(work, "branch", "ambiguous", base)
    fake_gh({
        "21": pr_payload(21, "ambiguous", base, state="MERGED", merge=base),
        "22": pr_payload(22, "ambiguous", base, state="OPEN"),
    })
    commands = section_bash(EVIDENCE_TITLE) + '\ncleanup_branch_pr_number "$@"\n'

    result = subprocess.run(
        ["bash", "--noprofile", "--norc", "-c", commands, "cleanup",
         str(work), PR_REPO, "ambiguous", "refs/heads/ambiguous"],
        cwd=work, env=dict(os.environ), capture_output=True, text=True, timeout=20,
    )

    assert result.returncode != 0, (result.stdout, result.stderr)
    assert result.stdout == ""


def test_branch_pr_number_retains_when_the_list_reaches_the_limit(
    work: Path, fake_gh,
) -> None:
    # A full page cannot prove uniqueness: another matching PR may be on the
    # next page. Treat the single match in the page as unknown, not unique.
    base = git(work, "rev-parse", "main")
    git(work, "branch", "limit-branch", base)
    prs: dict[str, dict[str, object]] = {}
    for index in range(100):
        head = base if index == 0 else f"{index:040x}"
        prs[str(1000 + index)] = pr_payload(1000 + index, "limit-branch", head)
    fake_gh(prs)
    commands = section_bash(EVIDENCE_TITLE) + '\ncleanup_branch_pr_number "$@"\n'

    result = subprocess.run(
        ["bash", "--noprofile", "--norc", "-c", commands, "cleanup",
         str(work), PR_REPO, "limit-branch", "refs/heads/limit-branch"],
        cwd=work, env=dict(os.environ), capture_output=True, text=True, timeout=20,
    )

    assert result.returncode != 0, (result.stdout, result.stderr)
    assert "取得上限" in result.stderr
    assert result.stdout == ""


def test_gate_b_presents_pr_merged_branches_that_are_not_ancestors(
    work: Path, fake_gh,
) -> None:
    git(work, "checkout", "-q", "-b", "squashed", "main")
    squashed_head = commit_file(work, "remote squash.txt", "squashed\n")
    git(work, "push", "-q", "origin", "squashed")
    git(work, "checkout", "-q", "-b", "unmerged", "main")
    unmerged_head = commit_file(work, "remote unmerged.txt", "unmerged\n")
    git(work, "push", "-q", "origin", "unmerged")
    git(work, "checkout", "-q", "main")
    git(work, "merge", "--squash", "squashed")
    git(work, "commit", "-qm", "squash on main")
    main_head = git(work, "rev-parse", "HEAD")
    git(work, "push", "-q", "origin", "main")
    git(work, "fetch", "-q", "origin", "--prune")
    fake_gh({
        "11": pr_payload(11, "squashed", squashed_head, merge=main_head),
        "12": pr_payload(12, "unmerged", unmerged_head, merge=unmerged_head),
    })
    commands = section_bash(EVIDENCE_TITLE) + "\n" + section_bash(GATE_B_TITLE)
    env = {
        **os.environ,
        "CHECKOUT": str(work),
        "PR_REPO": PR_REPO,
        "REMOTE": "origin",
        "BASE_REF": "refs/remotes/origin/main",
    }

    result = subprocess.run(
        ["bash", "--noprofile", "--norc", "-c", commands],
        cwd=work, env=env, capture_output=True, text=True, timeout=20,
    )

    assert result.returncode == 0, (result.stdout, result.stderr)
    candidates = [line for line in result.stdout.splitlines() if line.startswith("候補:")]
    assert any("squashed" in line and "pr" in line and "#11" in line for line in candidates), (
        result.stdout
    )
    assert not any("unmerged" in line for line in candidates), result.stdout
    remote_refs = git(work, "for-each-ref", "--format=%(refname)", "refs/remotes/origin")
    assert "refs/remotes/origin/squashed" in remote_refs
    assert "refs/remotes/origin/unmerged" in remote_refs


def test_gate_b_excludes_the_documented_short_base_reference(
    work: Path, fake_gh,
) -> None:
    # `origin/main` is the documented BASE_REF form in step 3. The remote ref
    # enumerated below is `refs/remotes/origin/main`, so comparing the raw
    # strings lets a MERGED main PR turn the base branch into a candidate.
    main_head = git(work, "rev-parse", "main")
    fake_gh({"31": pr_payload(31, "main", main_head, merge=main_head)})
    commands = section_bash(EVIDENCE_TITLE) + "\n" + section_bash(GATE_B_TITLE)
    env = {
        **os.environ,
        "CHECKOUT": str(work),
        "PR_REPO": PR_REPO,
        "REMOTE": "origin",
        "BASE_REF": "origin/main",
    }

    result = subprocess.run(
        ["bash", "--noprofile", "--norc", "-c", commands],
        cwd=work, env=env, capture_output=True, text=True, timeout=20,
    )

    assert result.returncode == 0, (result.stdout, result.stderr)
    decisions = [
        line for line in result.stdout.splitlines()
        if line.startswith(("候補:", "保持:"))
    ]
    assert not any("main" in line for line in decisions), result.stdout
