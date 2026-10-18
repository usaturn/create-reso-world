"""create-reso-world#152（移植元 usaturn/agent-workspace#483）: review_target.py が PR の解決・保存先・
レビューディレクトリ・Git 操作の対象を決める仕様。

移植元の submodule・一時 clone の代わりに、移植先の経路（``scripts/superpowers_context.py``）を実際の Git の
checkout で確かめる。GitHub への照会は偽の ``gh``、PR head の取得はローカルの bare remote で確かめる。
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "review_target.py"
SPEC = importlib.util.spec_from_file_location("review_target", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
target = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(target)

SELF = "usaturn/create-reso-world"
FORK = "usaturn/resoloop"
UPSTREAM = "orange3134/resoloop"
MESHY = "usaturn/resoloop-meshy"


def url(repository: str) -> str:
    return f"https://github.com/{repository}.git"


@pytest.fixture(autouse=True)
def isolated_git(monkeypatch: pytest.MonkeyPatch) -> None:
    """利用者の Git の設定（insteadOf など）と、親プロセスの ``GIT_*`` を読まない。

    linked worktree の ``git rebase --exec`` は ``GIT_DIR`` を export するので、残すと ``git -C <一時ディレクトリ>`` も
    実リポジトリの設定・index・ブランチを書き換える。
    """
    for name in tuple(os.environ):
        if name.startswith("GIT_"):
            monkeypatch.delenv(name)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", "/dev/null")


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True)
    return result.stdout.strip()


def make_repo(path: Path) -> Path:
    path.mkdir(parents=True)
    subprocess.run(["git", "init", "-b", "main", str(path)], check=True, capture_output=True)
    git(path, "config", "user.name", "Test User")
    git(path, "config", "user.email", "test@example.com")
    return path.resolve()


def make_checkout(path: Path, remotes: dict[str, str]) -> Path:
    checkout = make_repo(path)
    (checkout / ".gitignore").write_text("/reviews/\n/external/\n", encoding="utf-8")
    git(checkout, "add", ".gitignore")
    git(checkout, "commit", "-m", "initial")
    for name, value in remotes.items():
        git(checkout, "remote", "add", name, value)
    return checkout


def make_parent(tmp_path: Path, *, origin: str | None = url(SELF)) -> Path:
    """create-reso-world の main checkout（``/reviews/``・``/external/`` を無視する）。"""
    return make_checkout(tmp_path / "parent", {"origin": origin} if origin is not None else {})


def make_fork(parent: Path, *, upstream: str | None = url(UPSTREAM)) -> Path:
    """``external/resoloop``（origin が fork、upstream が上流）。"""
    remotes = {"origin": url(FORK)}
    if upstream is not None:
        remotes["upstream"] = upstream
    return make_checkout(parent / "external" / "resoloop", remotes)


def make_other(tmp_path: Path, name: str = "meshy", origin: str = url(MESHY)) -> Path:
    """``--code-root`` に渡す、既知の経路に無いリポジトリの main checkout。"""
    return make_checkout(tmp_path / name, {"origin": origin})


def make_remote(root: Path, *, number: int, branch: str, content: str = "change\n") -> tuple[Path, str]:
    """bare remote に main と head ブランチを置き、refs/pull/<number>/head を head に向ける。"""
    work = make_repo(root / "work")
    (work / "README.md").write_text("base\n", encoding="utf-8")
    git(work, "add", "README.md")
    git(work, "commit", "-m", "base")
    git(work, "switch", "-c", branch)
    (work / "change.txt").write_text(content, encoding="utf-8")
    git(work, "add", "change.txt")
    git(work, "commit", "-m", "change")
    head = git(work, "rev-parse", "HEAD")
    remote = root / "remote.git"
    subprocess.run(["git", "init", "--bare", "-b", "main", str(remote)], check=True, capture_output=True)
    git(work, "push", "-q", str(remote), "main", branch, f"{branch}:refs/pull/{number}/head")
    return remote.resolve(), head


def http(status: int, body: object | None = None) -> str:
    text = json.dumps(body) if body is not None else ""
    return f"HTTP/2.0 {status} Status\nContent-Type: application/json\n\n{text}"


def pull(
    repository: str,
    number: int,
    head_ref: str,
    head_sha: str = "a" * 40,
    head_repository: str | None = None,
) -> dict[str, Any]:
    return {
        "number": number,
        "html_url": f"https://github.com/{repository}/pull/{number}",
        "state": "open",
        "head": {
            "ref": head_ref,
            "sha": head_sha,
            "repo": {"full_name": head_repository or repository},
        },
        "base": {
            "ref": "main",
            "repo": {"full_name": repository, "clone_url": f"https://github.com/{repository}.git"},
        },
    }


class FakeGh:
    """gh api -i の応答を API のパスごとに返す。呼ばれた argv を calls に残す。"""

    def __init__(self, responses: dict[str, tuple[str, str]]) -> None:
        self.responses = responses
        self.calls: list[list[str]] = []

    def __call__(self, argv: Sequence[str]) -> subprocess.CompletedProcess[str]:
        self.calls.append(list(argv))
        assert list(argv[:3]) == ["gh", "api", "-i"], argv
        stdout, stderr = self.responses.get(argv[3], (http(404, {"message": "Not Found"}), ""))
        status = 0 if stdout.startswith("HTTP/2.0 2") else 1
        return subprocess.CompletedProcess(list(argv), status, stdout, stderr)


def gh_for(*pulls: dict[str, Any]) -> FakeGh:
    responses: dict[str, tuple[str, str]] = {}
    for item in pulls:
        repository = item["base"]["repo"]["full_name"]
        responses[f"repos/{repository}/pulls/{item['number']}"] = (http(200, item), "")
        responses[f"repos/{repository}"] = (http(200, {"full_name": repository}), "")
    return FakeGh(responses)


def error_code(excinfo: pytest.ExceptionInfo[Exception]) -> int:
    error: Any = excinfo.value
    return error.code


def review_dir(root: Path, *parts: str) -> Path:
    directory = root.joinpath("reviews", *parts)
    directory.mkdir(parents=True)
    (directory / "model.md").write_text("review\n", encoding="utf-8")
    return directory


def write_findings(directory: Path, repository: str, number: int, name: str = "m-0123456789ab.json") -> None:
    findings = directory / "findings"
    findings.mkdir(parents=True, exist_ok=True)
    document = {"pr": {"repository": repository, "number": number}}
    (findings / name).write_text(json.dumps(document), encoding="utf-8")


def tree(root: Path) -> list[Path]:
    return sorted(root.rglob("*"))


# 指定の解釈と名前


def test_parse_number_url_and_reject_other() -> None:
    assert target.parse_pull_request_argument("3") == target.PullRequestArgument(None, 3)
    assert target.parse_pull_request_argument(" #3 ") == target.PullRequestArgument(None, 3)
    assert target.parse_pull_request_argument(
        "https://github.com/usaturn/resoloop-meshy/pull/3/files"
    ) == target.PullRequestArgument(MESHY, 3)
    for value in ("owner/repo#3", "https://gitlab.com/a/b/pull/3", "#0", "pull/3", ""):
        with pytest.raises(target.TargetError) as excinfo:
            target.parse_pull_request_argument(value)
        assert error_code(excinfo) == target.EXIT_USAGE


def test_github_repository_reads_https_and_ssh() -> None:
    assert target.github_repository("https://github.com/usaturn/create-reso-world.git") == SELF
    assert target.github_repository("https://github.com/usaturn/resoloop") == FORK
    assert target.github_repository("git@github.com:orange3134/resoloop.git") == UPSTREAM
    assert target.github_repository("ssh://git@github.com/usaturn/resoloop") == FORK
    assert target.github_repository("file:///tmp/remote.git") is None
    assert target.github_repository("https://github.com/usaturn/..") is None


def test_review_directory_uses_lowercase_owner_and_repo_levels(tmp_path: Path) -> None:
    assert target.review_directory(tmp_path, "Usaturn/Resoloop", 3, "feature/x") == (
        tmp_path / "reviews" / "usaturn" / "resoloop" / "#3-feature-x"
    )


@pytest.mark.parametrize("value", ["usaturn/..", "usaturn/.", "../x", "a/b/c", "a", "-a/b", "a/b c"])
def test_validate_repository_rejects_unsafe_names(value: str) -> None:
    with pytest.raises(target.TargetError) as excinfo:
        target.validate_repository(value)
    assert error_code(excinfo) == target.EXIT_USAGE


def test_naming_rules_keep_the_helper_messages() -> None:
    with pytest.raises(target.TargetError, match="head branch cannot produce a safe review directory"):
        target.normalize_head_branch("feature/")
    with pytest.raises(target.TargetError, match="PR number cannot produce a safe review directory"):
        target.review_directory_name(0, "x")
    with pytest.raises(target.TargetError, match="model identifier is not a safe filename"):
        target.validate_model_name(" gpt")
    assert target.validate_model_name("opencode/deepseek v4") == "opencode-deepseek-v4"


# GitHub への照会


def test_fetch_pull_request_success() -> None:
    gh = gh_for(pull(FORK, 12, "feat/x", head_repository="someone/resoloop"))

    pr = target.fetch_pull_request(FORK, 12, runner=gh)

    assert pr.repository == FORK
    assert pr.head_ref == "feat/x"
    assert pr.head_repository == "someone/resoloop"
    assert pr.clone_url == url(FORK)
    assert gh.calls == [["gh", "api", "-i", f"repos/{FORK}/pulls/12"]]


def test_fetch_pull_request_not_found_when_repository_exists() -> None:
    gh = FakeGh({f"repos/{SELF}": (http(200, {}), "")})

    with pytest.raises(target.TargetError) as excinfo:
        target.fetch_pull_request(SELF, 999, runner=gh)

    assert error_code(excinfo) == target.EXIT_PR_NOT_FOUND
    assert "PR URL" in str(excinfo.value)


def test_fetch_pull_request_repository_missing() -> None:
    with pytest.raises(target.TargetError) as excinfo:
        target.fetch_pull_request("usaturn/nothing", 1, runner=FakeGh({}))

    assert error_code(excinfo) == target.EXIT_REPOSITORY_NOT_FOUND


@pytest.mark.parametrize("status", [401, 403])
def test_fetch_pull_request_auth(status: int) -> None:
    gh = FakeGh({f"repos/{FORK}/pulls/1": (http(status, {"message": "Bad credentials"}), "")})

    with pytest.raises(target.TargetError) as excinfo:
        target.fetch_pull_request(FORK, 1, runner=gh)

    assert error_code(excinfo) == target.EXIT_AUTH


def test_fetch_pull_request_without_status_is_api_failure() -> None:
    gh = FakeGh({f"repos/{FORK}/pulls/1": ("", "dial tcp: connection refused")})

    with pytest.raises(target.TargetError) as excinfo:
        target.fetch_pull_request(FORK, 1, runner=gh)

    assert error_code(excinfo) == target.EXIT_API
    assert "connection refused" in str(excinfo.value)


def test_fetch_pull_request_broken_body() -> None:
    broken = pull(FORK, 1, "x")
    del broken["head"]["sha"]
    gh = FakeGh({f"repos/{FORK}/pulls/1": (http(200, broken), "")})

    with pytest.raises(target.TargetError) as excinfo:
        target.fetch_pull_request(FORK, 1, runner=gh)

    assert error_code(excinfo) == target.EXIT_API


def test_fetch_pull_request_uses_the_canonical_name_after_a_rename() -> None:
    # gh は転送を内部で追い、改名後のリポジトリの応答だけを出す
    gh = FakeGh({"repos/usaturn/old/pulls/1": (http(200, pull("usaturn/renamed", 1, "x")), "")})

    assert target.fetch_pull_request("usaturn/old", 1, runner=gh).repository == "usaturn/renamed"


# resolve（pr-review）


def test_resolve_number_uses_parent_origin(tmp_path: Path) -> None:
    parent = make_parent(tmp_path)
    gh = gh_for(pull(SELF, 4, "fix/x"))

    result = target.resolve("#4", parent_root=parent, runner=gh)

    assert gh.calls[0][3] == f"repos/{SELF}/pulls/4"
    assert result["repository"] == SELF
    assert result["review_dir"] == str(parent / "reviews" / "usaturn" / "create-reso-world" / "#4-fix-x")
    assert result["target_root"] == str(parent)
    assert result["base_remote"] == "origin"
    assert result["parent_root"] == str(parent)


def test_resolve_fork_and_upstream_use_separate_directories_and_remotes(tmp_path: Path) -> None:
    parent = make_parent(tmp_path)
    fork = make_fork(parent)
    gh = gh_for(pull(FORK, 11, "x"), pull(UPSTREAM, 11, "x", head_repository=FORK))

    from_fork = target.resolve(f"https://github.com/{FORK}/pull/11", parent_root=parent, runner=gh)
    from_upstream = target.resolve(f"https://github.com/{UPSTREAM}/pull/11", parent_root=parent, runner=gh)

    assert from_fork["review_dir"] == str(parent / "reviews" / "usaturn" / "resoloop" / "#11-x")
    assert from_upstream["review_dir"] == str(parent / "reviews" / "orange3134" / "resoloop" / "#11-x")
    assert from_fork["target_root"] == from_upstream["target_root"] == str(fork)
    assert (from_fork["base_remote"], from_upstream["base_remote"]) == ("origin", "upstream")


def test_resolve_lowercases_review_directory(tmp_path: Path) -> None:
    parent = make_parent(tmp_path)
    make_fork(parent)
    gh = FakeGh({f"repos/{FORK}/pulls/3": (http(200, pull("Usaturn/Resoloop", 3, "feat/x")), "")})

    result = target.resolve(f"https://github.com/{FORK}/pull/3", parent_root=parent, runner=gh)

    assert result["repository"] == "Usaturn/Resoloop"
    assert result["review_dir"] == str(parent / "reviews" / "usaturn" / "resoloop" / "#3-feat-x")


def test_resolve_fork_pr_uses_base_repository(tmp_path: Path) -> None:
    parent = make_parent(tmp_path)
    make_fork(parent)
    gh = gh_for(pull(FORK, 5, "patch", head_repository="someone/resoloop"))

    result = target.resolve(f"https://github.com/{FORK}/pull/5", parent_root=parent, runner=gh)

    assert result["repository"] == FORK
    assert result["head_repository"] == "someone/resoloop"
    assert result["review_dir"] == str(parent / "reviews" / "usaturn" / "resoloop" / "#5-patch")


def test_resolve_stops_without_checkout_and_does_not_clone(tmp_path: Path) -> None:
    parent = make_parent(tmp_path)
    before = tree(tmp_path)

    with pytest.raises(target.TargetError) as excinfo:
        target.resolve(f"https://github.com/{MESHY}/pull/2", parent_root=parent, runner=gh_for(pull(MESHY, 2, "y")))

    assert error_code(excinfo) == target.EXIT_PARENT
    assert "--code-root" in str(excinfo.value)
    assert tree(tmp_path) == before


def test_resolve_uses_explicit_code_root(tmp_path: Path) -> None:
    parent = make_parent(tmp_path)
    other = make_other(tmp_path)

    result = target.resolve(
        f"https://github.com/{MESHY}/pull/2", parent_root=parent, code_root=other, runner=gh_for(pull(MESHY, 2, "y"))
    )

    assert result["target_root"] == str(other)
    assert result["base_remote"] == "origin"
    assert result["review_dir"] == str(parent / "reviews" / "usaturn" / "resoloop-meshy" / "#2-y")


@pytest.mark.parametrize("state", ["missing", "no-upstream"])
def test_resoloop_route_requires_fork_remotes(tmp_path: Path, state: str) -> None:
    parent = make_parent(tmp_path)
    if state == "no-upstream":
        make_fork(parent, upstream=None)
    gh = gh_for(pull(UPSTREAM, 11, "x", head_repository=FORK))

    with pytest.raises(target.TargetError) as excinfo:
        target.resolve(f"https://github.com/{UPSTREAM}/pull/11", parent_root=parent, runner=gh)

    assert error_code(excinfo) == target.EXIT_PARENT
    assert "resoloop-fork.sh clone" in str(excinfo.value)


@pytest.mark.parametrize("kind", ["relative", "linked", "other-remote", "known-route"])
def test_code_root_rejections(tmp_path: Path, kind: str) -> None:
    parent = make_parent(tmp_path)
    other = make_other(tmp_path)
    repository, code_root = MESHY, other
    if kind == "relative":
        code_root = Path("meshy")
    elif kind == "linked":
        code_root = tmp_path / "linked"
        git(other, "worktree", "add", "-q", "--detach", str(code_root))
    elif kind == "other-remote":
        code_root = make_other(tmp_path, "unrelated", url("someone/else"))
    else:
        repository = SELF

    with pytest.raises(target.TargetError) as excinfo:
        target.resolve(
            f"https://github.com/{repository}/pull/2",
            parent_root=parent,
            code_root=code_root,
            runner=gh_for(pull(repository, 2, "y")),
        )

    assert error_code(excinfo) == target.EXIT_PARENT


def test_resolve_stops_without_parent_origin(tmp_path: Path) -> None:
    parent = make_parent(tmp_path, origin=None)
    gh = gh_for(pull(SELF, 4, "x"))

    with pytest.raises(target.TargetError) as excinfo:
        target.resolve("4", parent_root=parent, runner=gh)

    assert error_code(excinfo) == target.EXIT_PARENT
    assert "PR URL" in str(excinfo.value)
    assert gh.calls == []


def test_require_parent_root_needs_ignored_reviews(tmp_path: Path) -> None:
    parent = make_repo(tmp_path / "parent")
    (parent / "README.md").write_text("x\n", encoding="utf-8")
    git(parent, "add", "README.md")
    git(parent, "commit", "-m", "x")

    with pytest.raises(target.TargetError) as excinfo:
        target.require_parent_root(parent)

    assert error_code(excinfo) == target.EXIT_PARENT


def test_require_parent_root_rejects_linked_worktree(tmp_path: Path) -> None:
    parent = make_parent(tmp_path)
    linked = tmp_path / "linked"
    git(parent, "worktree", "add", "-q", "--detach", str(linked))

    with pytest.raises(target.TargetError) as excinfo:
        target.require_parent_root(linked)

    assert error_code(excinfo) == target.EXIT_PARENT


# レビューディレクトリの探索（review-fix-planning・review-verify）


def test_find_review_directory_by_number(tmp_path: Path) -> None:
    parent = make_parent(tmp_path)
    directory = review_dir(parent, "usaturn", "create-reso-world", "#4-feat-x")

    result = target.find_review_directory("#4", parent_root=parent, runner=gh_for(pull(SELF, 4, "feat/x")))

    assert result["review_dir"] == str(directory)
    assert result["target_root"] == str(parent)


def test_find_review_directory_reports_missing_review_and_legacy_dirs(tmp_path: Path) -> None:
    parent = make_parent(tmp_path)
    legacy = review_dir(parent, "#4-feat-x")

    with pytest.raises(target.TargetError) as excinfo:
        target.find_review_directory("4", parent_root=parent, runner=gh_for(pull(SELF, 4, "feat/x")))

    assert error_code(excinfo) == target.EXIT_NO_REVIEW
    assert str(legacy) in str(excinfo.value)

    fork = make_fork(parent)
    old = review_dir(fork, "#11-x")
    per_checkout = review_dir(fork, "usaturn", "resoloop", "#11-x")
    upstream_dir = review_dir(fork, "orange3134", "resoloop", "#11-x")

    with pytest.raises(target.TargetError) as excinfo:
        target.find_review_directory(
            f"https://github.com/{FORK}/pull/11", parent_root=parent, runner=gh_for(pull(FORK, 11, "x"))
        )

    assert error_code(excinfo) == target.EXIT_NO_REVIEW
    message = str(excinfo.value)
    assert str(old) in message and str(per_checkout) in message
    assert str(upstream_dir) not in message


def test_find_review_directory_does_not_cross_repositories(tmp_path: Path) -> None:
    parent = make_parent(tmp_path)
    make_fork(parent)
    review_dir(parent, "usaturn", "resoloop", "#4-feat-x")

    with pytest.raises(target.TargetError) as excinfo:
        target.find_review_directory(
            f"https://github.com/{UPSTREAM}/pull/4", parent_root=parent, runner=gh_for(pull(UPSTREAM, 4, "feat/x"))
        )

    assert error_code(excinfo) == target.EXIT_NO_REVIEW


def test_find_review_directory_lists_multiple_candidates(tmp_path: Path) -> None:
    parent = make_parent(tmp_path)
    first = review_dir(parent, "usaturn", "create-reso-world", "#4-a")
    second = review_dir(parent, "usaturn", "create-reso-world", "#4-b")

    with pytest.raises(target.TargetError) as excinfo:
        target.find_review_directory("#4", parent_root=parent, runner=gh_for(pull(SELF, 4, "b")))

    assert error_code(excinfo) == target.EXIT_AMBIGUOUS
    assert str(first) in str(excinfo.value) and str(second) in str(excinfo.value)


def test_find_review_directory_ignores_symlinks_and_other_names(tmp_path: Path) -> None:
    parent = make_parent(tmp_path)
    reviews = parent / "reviews" / "usaturn" / "create-reso-world"
    real = review_dir(tmp_path, "elsewhere")
    reviews.mkdir(parents=True)
    (reviews / "#4-link").symlink_to(real, target_is_directory=True)
    (reviews / "x4-feat").mkdir()

    with pytest.raises(target.TargetError) as excinfo:
        target.find_review_directory("#4", parent_root=parent, runner=gh_for(pull(SELF, 4, "link")))

    assert error_code(excinfo) == target.EXIT_NO_REVIEW


def test_find_review_directory_accepts_legacy_path(tmp_path: Path) -> None:
    parent = make_parent(tmp_path)
    legacy = review_dir(parent, "#4-feat-x")
    gh = gh_for(pull(SELF, 4, "feat/x"))

    result = target.find_review_directory(str(legacy), parent_root=parent, runner=gh)

    assert result["review_dir"] == str(legacy)
    assert result["target_root"] == str(parent)
    assert gh.calls[0][3] == f"repos/{SELF}/pulls/4"


def test_find_review_directory_accepts_checkout_owner_repo_layout(tmp_path: Path) -> None:
    parent = make_parent(tmp_path)
    fork = make_fork(parent)
    directory = review_dir(fork, "orange3134", "resoloop", "#11-x")

    result = target.find_review_directory(
        str(directory), parent_root=parent, runner=gh_for(pull(UPSTREAM, 11, "x", head_repository=FORK))
    )

    assert result["repository"] == UPSTREAM
    assert result["target_root"] == str(fork)
    assert result["base_remote"] == "upstream"


def test_legacy_fork_checkout_directory_is_ambiguous(tmp_path: Path) -> None:
    parent = make_parent(tmp_path)
    fork = make_fork(parent)
    directory = review_dir(fork, "#11-x")
    gh = FakeGh({})

    with pytest.raises(target.TargetError) as excinfo:
        target.find_review_directory(str(directory), parent_root=parent, runner=gh)

    assert error_code(excinfo) == target.EXIT_PATH
    message = str(excinfo.value)
    assert FORK in message and UPSTREAM in message and "--pr" in message
    assert gh.calls == []


def test_legacy_fork_checkout_directory_uses_findings(tmp_path: Path) -> None:
    parent = make_parent(tmp_path)
    fork = make_fork(parent)
    directory = review_dir(fork, "#11-x")
    write_findings(directory, UPSTREAM, 11)

    result = target.find_review_directory(
        str(directory), parent_root=parent, runner=gh_for(pull(UPSTREAM, 11, "x", head_repository=FORK))
    )

    assert result["repository"] == UPSTREAM
    assert result["base_remote"] == "upstream"

    write_findings(directory, "someone/x", 11)
    with pytest.raises(target.TargetError) as excinfo:
        target.find_review_directory(str(directory), parent_root=parent, runner=FakeGh({}))
    assert error_code(excinfo) == target.EXIT_PATH


def test_legacy_fork_checkout_directory_with_pr(tmp_path: Path) -> None:
    parent = make_parent(tmp_path)
    fork = make_fork(parent)
    directory = review_dir(fork, "#11-x")

    result = target.find_review_directory(
        str(directory),
        parent_root=parent,
        pr_argument=f"https://github.com/{UPSTREAM}/pull/11",
        runner=gh_for(pull(UPSTREAM, 11, "x", head_repository=FORK)),
    )

    assert result["repository"] == UPSTREAM
    assert result["target_root"] == str(fork)
    assert result["base_remote"] == "upstream"

    for wrong in ("https://github.com/someone/x/pull/11", f"https://github.com/{UPSTREAM}/pull/12"):
        gh = FakeGh({})
        with pytest.raises(target.TargetError) as excinfo:
            target.find_review_directory(str(directory), parent_root=parent, pr_argument=wrong, runner=gh)
        assert error_code(excinfo) == target.EXIT_PATH
        assert gh.calls == []


def test_pr_option_must_match_path(tmp_path: Path) -> None:
    parent = make_parent(tmp_path)
    directory = review_dir(parent, "usaturn", "create-reso-world", "#4-feat-x")

    for wrong in ("5", f"https://github.com/{FORK}/pull/4"):
        with pytest.raises(target.TargetError) as excinfo:
            target.find_review_directory(str(directory), parent_root=parent, pr_argument=wrong, runner=FakeGh({}))
        assert error_code(excinfo) == target.EXIT_PATH

    result = target.find_review_directory(
        str(directory), parent_root=parent, pr_argument="#4", runner=gh_for(pull(SELF, 4, "feat/x"))
    )
    assert result["review_dir"] == str(directory)

    with pytest.raises(target.TargetError) as excinfo:
        target.find_review_directory("#4", parent_root=parent, pr_argument="#4", runner=FakeGh({}))
    assert error_code(excinfo) == target.EXIT_USAGE


def test_checkout_layout_must_match_target_root(tmp_path: Path) -> None:
    parent = make_parent(tmp_path)
    first = make_other(tmp_path, "first")
    second = make_other(tmp_path, "second")
    directory = review_dir(first, "usaturn", "resoloop-meshy", "#2-y")

    with pytest.raises(target.TargetError) as excinfo:
        target.find_review_directory(
            str(directory), parent_root=parent, code_root=second, runner=gh_for(pull(MESHY, 2, "y"))
        )
    assert error_code(excinfo) == target.EXIT_PATH

    with pytest.raises(target.TargetError) as excinfo:
        target.find_review_directory(str(directory), parent_root=parent, runner=gh_for(pull(MESHY, 2, "y")))
    assert error_code(excinfo) == target.EXIT_PARENT

    result = target.find_review_directory(
        str(directory), parent_root=parent, code_root=first, runner=gh_for(pull(MESHY, 2, "y"))
    )
    assert result["target_root"] == str(first)


def test_legacy_single_remote_checkout_directory(tmp_path: Path) -> None:
    parent = make_parent(tmp_path)
    other = make_other(tmp_path)
    directory = review_dir(other, "#2-y")

    result = target.find_review_directory(
        str(directory), parent_root=parent, code_root=other, runner=gh_for(pull(MESHY, 2, "y"))
    )

    assert result["repository"] == MESHY
    assert result["review_dir"] == str(directory)


def test_legacy_checkout_without_github_remote(tmp_path: Path) -> None:
    parent = make_parent(tmp_path)
    local = make_checkout(tmp_path / "local", {"origin": "file:///nowhere/repo.git"})
    directory = review_dir(local, "#2-y")

    with pytest.raises(target.TargetError) as excinfo:
        target.find_review_directory(str(directory), parent_root=parent, runner=FakeGh({}))

    assert error_code(excinfo) == target.EXIT_PATH


def test_find_review_directory_rejects_name_mismatch(tmp_path: Path) -> None:
    parent = make_parent(tmp_path)
    directory = review_dir(parent, "usaturn", "create-reso-world", "#4-old-name")

    with pytest.raises(target.TargetError) as excinfo:
        target.find_review_directory(str(directory), parent_root=parent, runner=gh_for(pull(SELF, 4, "feat/x")))

    assert error_code(excinfo) == target.EXIT_PATH


def test_find_review_directory_from_findings_json(tmp_path: Path) -> None:
    parent = make_parent(tmp_path)
    elsewhere = tmp_path / "elsewhere"
    write_findings(elsewhere, SELF, 7)
    gh = gh_for(pull(SELF, 7, "z"))

    result = target.find_review_directory(str(elsewhere), parent_root=parent, runner=gh)

    assert result["review_dir"] == str(elsewhere.resolve())
    assert gh.calls[0][3] == f"repos/{SELF}/pulls/7"


def test_find_review_directory_rejects_findings_for_another_pr(tmp_path: Path) -> None:
    parent = make_parent(tmp_path)
    directory = review_dir(parent, "usaturn", "create-reso-world", "#4-feat-x")
    write_findings(directory, FORK, 4)

    with pytest.raises(target.TargetError) as excinfo:
        target.find_review_directory(str(directory), parent_root=parent, runner=gh_for(pull(SELF, 4, "feat/x")))

    assert error_code(excinfo) == target.EXIT_PATH


def test_find_review_directory_rejects_unidentifiable_path(tmp_path: Path) -> None:
    parent = make_parent(tmp_path)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()

    with pytest.raises(target.TargetError) as excinfo:
        target.find_review_directory(str(elsewhere), parent_root=parent, runner=FakeGh({}))

    assert error_code(excinfo) == target.EXIT_PATH


# PR head の固定


@pytest.mark.parametrize("head_moved", [False, True])
def test_fetch_pull_head_preserves_tracking_refs_tags_and_fetch_head(tmp_path: Path, head_moved: bool) -> None:
    remote, head = make_remote(tmp_path / "remote", number=3, branch="hogehoge")
    checkout = tmp_path / "source"
    subprocess.run(
        ["git", "clone", "--quiet", "--no-checkout", "--no-tags", str(remote), str(checkout)],
        check=True,
        capture_output=True,
    )
    git(checkout, "config", "--add", "remote.origin.fetch", "+refs/pull/*/head:refs/remotes/origin/pr-*")
    git(checkout, "config", "remote.origin.tagOpt", "--tags")
    git(remote, "update-ref", "refs/tags/published-after-clone", head)
    fetch_head = checkout / ".git" / "FETCH_HEAD"
    fetch_head.write_text("preserve caller fetch result\n", encoding="utf-8")
    refs = ("for-each-ref", "--format=%(refname) %(objectname)", "refs/heads", "refs/remotes", "refs/tags")
    before = git(checkout, *refs)
    if head_moved:
        with pytest.raises(target.TargetError):
            target.fetch_pull_head(checkout, FORK, 3, "b" * 40, remote="origin")
    else:
        ref = target.fetch_pull_head(checkout, FORK, 3, head, remote="origin")
        assert ref == "refs/pr-review/repos/usaturn/resoloop/3"
        assert git(checkout, "rev-parse", ref) == head
    assert git(checkout, *refs) == before
    assert fetch_head.read_text(encoding="utf-8") == "preserve caller fetch result\n"


def test_fetch_pull_head_separates_fork_and_upstream(tmp_path: Path) -> None:
    fork_remote, fork_head = make_remote(tmp_path / "fork", number=11, branch="x", content="fork\n")
    upstream_remote, upstream_head = make_remote(tmp_path / "upstream", number=11, branch="x", content="upstream\n")
    checkout = make_checkout(tmp_path / "checkout", {"origin": str(fork_remote), "upstream": str(upstream_remote)})

    fork_ref = target.fetch_pull_head(checkout, FORK, 11, fork_head, remote="origin")
    upstream_ref = target.fetch_pull_head(checkout, "Orange3134/Resoloop", 11, upstream_head, remote="upstream")

    assert fork_ref == "refs/pr-review/repos/usaturn/resoloop/11"
    assert upstream_ref == "refs/pr-review/repos/orange3134/resoloop/11"
    assert git(checkout, "rev-parse", fork_ref) == fork_head
    assert git(checkout, "rev-parse", upstream_ref) == upstream_head


def test_fetch_pull_head_stops_when_head_moved(tmp_path: Path) -> None:
    remote, _head = make_remote(tmp_path / "remote", number=3, branch="hogehoge")
    checkout = make_checkout(tmp_path / "checkout", {"origin": str(remote)})

    with pytest.raises(target.TargetError) as excinfo:
        target.fetch_pull_head(checkout, FORK, 3, "b" * 40, remote="origin")

    assert error_code(excinfo) == target.EXIT_FETCH
    assert "変わりました" in str(excinfo.value)


# CLI


def test_cli_review_dir_for_planning_keeps_the_range(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    parent = make_parent(tmp_path)
    other = make_other(tmp_path, "someone-x", url("someone/x"))
    review_dir(parent, "someone", "x", "#1-y")
    monkeypatch.setattr(target, "default_parent_root", lambda: parent)

    code = target.main(
        ["review-dir", "https://github.com/someone/x/pull/1", "--for-planning", "--code-root", str(other)],
        runner=gh_for(pull("someone/x", 1, "y")),
    )

    assert code == 0


def test_cli_reports_error_code_and_message(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    parent = make_parent(tmp_path)
    monkeypatch.setattr(target, "default_parent_root", lambda: parent)

    code = target.main(["review-dir", f"https://github.com/{MESHY}/pull/2"], runner=gh_for(pull(MESHY, 2, "y")))

    assert code == target.EXIT_PARENT
    assert capsys.readouterr().err.startswith("review_target: ")


def test_cli_resolve_prints_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    parent = make_parent(tmp_path)
    monkeypatch.setattr(target, "default_parent_root", lambda: parent)

    code = target.main(["resolve", "#4"], runner=gh_for(pull(SELF, 4, "fix/x")))

    assert code == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed["review_dir"].endswith("/reviews/usaturn/create-reso-world/#4-fix-x")
    assert printed["base_remote"] == "origin"
