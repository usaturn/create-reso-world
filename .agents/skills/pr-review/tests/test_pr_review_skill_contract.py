from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[4]
AGENTS_SKILL = REPO_ROOT / ".agents/skills/pr-review/SKILL.md"
AGENTS_HELPER = REPO_ROOT / ".agents/skills/pr-review/scripts/pr_review_workspace.py"
CLAUDE_LINK = REPO_ROOT / ".claude/skills/pr-review"
BUDGET_REFERENCE = REPO_ROOT / ".agents/skills/pr-review/references/time-budget.md"


class ResolverStopped(Exception):
    """Raised when the skill resolver exits non-zero (fail-closed)."""

    def __init__(self, returncode: int, stderr: str, stdout: str = "") -> None:
        super().__init__(returncode, stderr)
        self.returncode = returncode
        self.stderr = stderr
        self.stdout = stdout


class _RootPath:
    """Path-like root updated by the fixture; supports / and equality at runtime."""

    __slots__ = ("_parts",)

    def __init__(self, *parts: str) -> None:
        self._parts = parts

    def __truediv__(self, other: str | Path) -> _RootPath:
        return _RootPath(*self._parts, str(other))

    def _absolute(self) -> Path:
        base = _FixtureState.toplevel
        assert base is not None, "resolver_fixture must bind TOPLEVEL before resolve"
        return base.joinpath(*self._parts)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, (Path, _RootPath)):
            return NotImplemented
        left = self._absolute()
        right = other._absolute() if isinstance(other, _RootPath) else other
        return left == right

    def __hash__(self) -> int:
        return hash(self._parts)

    def __repr__(self) -> str:
        return f"TOPLEVEL.joinpath{self._parts!r}"


class _FixtureState:
    toplevel: Path | None = None


TOPLEVEL = _RootPath()


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def extract_resolver_script(skill_text: str) -> str:
    """Extract the resolver by its CLI operation, never its prose heading."""
    blocks = re.findall(r"```bash\n(.*?)```", skill_text, re.DOTALL)
    matches = [block for block in blocks if "--operation review-workspace" in block]
    assert len(matches) == 1, "skill must have one unambiguous review-workspace block"
    block = matches[0]
    # Nested list markdown indents the fence body; strip a common indent.
    lines = block.splitlines()
    indents = [len(line) - len(line.lstrip(" ")) for line in lines if line.strip()]
    common = min(indents) if indents else 0
    return "\n".join(line[common:] if len(line) >= common else line for line in lines) + "\n"


def _git(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-c", "user.email=test@example.com", "-c", "user.name=test", *args],
        cwd=cwd,
        check=check,
        env=dict(os.environ, GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL="/dev/null"),
        text=True,
        capture_output=True,
    )


PARENT_ORIGIN = "https://github.com/usaturn/create-reso-world.git"
FORK_ORIGIN = "https://github.com/usaturn/resoloop.git"
FORK_UPSTREAM = "https://github.com/orange3134/resoloop.git"


def build_parent_with_fork(tmp_path: Path, *, fork: str = "ok") -> Path:
    """Create an isolated parent repo; external/resoloop is the fork checkout.

    fork="ok" builds what scripts/resoloop-fork.sh clone leaves: a repository
    of its own with origin and upstream. "missing" leaves no checkout, "plain"
    leaves an ordinary directory inside the parent, and "wrong-origin" /
    "wrong-upstream" point that remote at another repository.
    """
    parent = tmp_path / "parent"
    parent.mkdir()
    _git(parent, "init")
    (parent / ".gitignore").write_text("/external/\n", encoding="utf-8")
    _git(parent, "add", ".gitignore")
    _git(parent, "commit", "-m", "init parent")
    _git(parent, "remote", "add", "origin", PARENT_ORIGIN)
    helper = REPO_ROOT / "scripts/superpowers_context.py"
    (parent / "scripts").mkdir()
    shutil.copy2(helper, parent / "scripts/superpowers_context.py")
    _git(parent, "add", "scripts/superpowers_context.py")
    _git(parent, "commit", "-m", "install context helper")
    checkout = parent / "external" / "resoloop"
    if fork == "missing":
        return parent.resolve()
    checkout.mkdir(parents=True)
    if fork == "plain":
        return parent.resolve()
    _git(checkout, "init")
    _git(checkout, "commit", "--allow-empty", "-m", "init fork")
    other = "https://github.com/someone/resoloop.git"
    _git(checkout, "remote", "add", "origin", other if fork == "wrong-origin" else FORK_ORIGIN)
    _git(checkout, "remote", "add", "upstream", other if fork == "wrong-upstream" else FORK_UPSTREAM)
    return parent.resolve()


@dataclass
class ResolverFixture:
    toplevel: Path

    def resolve(
        self,
        pr_url: str,
        *,
        skill_path: Path,
        code_root: str | None = None,
        shell: str = "bash",
        nounset: bool = True,
        parent_root: str | None = None,
        cwd: Path | None = None,
    ) -> tuple[Path, str]:
        script = extract_resolver_script(read(skill_path))
        pr_json = json.dumps({"url": pr_url})
        # Emit MAIN_ROOT and PR_REMOTE after the skill block for the test harness.
        shell_options = "set -euo pipefail" if nounset else "set -eo pipefail"
        harness = f"""{shell_options}
PR_JSON={json.dumps(pr_json)}
CODE_ROOT={json.dumps(code_root or "")}
PARENT_ROOT={json.dumps(parent_root or "")}
{script}
printf '%s\\n' "$MAIN_ROOT" "$PR_REMOTE"
"""
        shell_args = [shell, "-f"] if shell == "zsh" else [shell]
        completed = subprocess.run(
            [*shell_args, "-c", harness],
            cwd=cwd or self.toplevel,
            env=dict(os.environ, GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL="/dev/null"),
            text=True,
            capture_output=True,
            check=False,
        )
        if completed.returncode != 0:
            raise ResolverStopped(completed.returncode, completed.stderr, completed.stdout)
        # Preserve the blank remote line: stripping stdout hid zsh's empty result.
        lines = completed.stdout.splitlines()
        assert len(lines) == 2, completed.stdout
        assert completed.stderr == "", completed.stderr
        main_root, pr_remote = lines
        return Path(main_root).resolve(), pr_remote


def make_resolver(tmp_path: Path, fork: str = "ok") -> ResolverFixture:
    toplevel = build_parent_with_fork(tmp_path, fork=fork)
    _FixtureState.toplevel = toplevel
    return ResolverFixture(toplevel=toplevel)


@pytest.fixture
def resolver_fixture(tmp_path: Path) -> ResolverFixture:
    return make_resolver(tmp_path)


def test_helper_has_one_real_copy_shared_through_the_skill_symlink() -> None:
    assert AGENTS_HELPER.is_file() and not AGENTS_HELPER.is_symlink()
    assert AGENTS_HELPER.stat().st_size > 0
    assert CLAUDE_LINK.is_symlink()
    assert os.readlink(CLAUDE_LINK) == "../../.agents/skills/pr-review"
    assert not (REPO_ROOT / ".devin/skills").exists()


def test_skill_interpolation_is_limited_to_the_target_line() -> None:
    content = read(AGENTS_SKILL)
    # Claude Code and Devin replace $ARGUMENTS and $0-$9 in the body with the
    # invocation arguments. Only the target-PR line may carry $ARGUMENTS, and
    # embedded shell code must not use positional parameters.
    assert content.count("$ARGUMENTS") == 1
    assert all("$ARGUMENTS" not in block for block in re.findall(r"```[^\n]*\n(.*?)```", content, re.DOTALL))
    assert re.search(r"\$[0-9]", content) is None


ALLOWED_TOOLS = (
    "Read, Grep, Glob, Bash(gh *), Bash(git *), Bash(date *), "
    "Bash(uv run --no-project python *pr_review_workspace.py *), "
    "Bash(uv run --no-project python *superpowers_context.py *), "
    "Edit(/tmp/pr-review-*/review-backup/**), Write(/tmp/pr-review-*/review-backup/**), Agent"
)


def test_skill_keeps_claude_code_permissions_consistent() -> None:
    content = read(AGENTS_SKILL)
    head = yaml.safe_load(content.split("---", 2)[1])
    # The tool allow-list is a permission boundary, not descriptive prose.
    assert head["allowed-tools"] == ALLOWED_TOOLS
    assert isinstance(head["argument-hint"], str) and head["argument-hint"].strip()
    create_arguments: list[list[str]] = []
    for block in re.findall(r"```bash\n(.*?)```", content, re.DOTALL):
        if "create" not in block:
            continue
        # Join explicit continuations, then tokenize each logical line: shlex
        # consumes the newline ending a comment, which must not merge a later
        # invocation into the preceding command and hide an unsafe temp-root.
        for line in block.replace("\\\n", "").splitlines():
            lexer = shlex.shlex(line, posix=True, punctuation_chars="();&|")
            lexer.whitespace = " \t\r"
            lexer.whitespace_split = True
            command: list[str] = []
            for token in [*lexer, "\n"]:
                if not token.strip("();&|\n"):
                    # Control words precede a simple command without changing
                    # its argv. Unknown execution wrappers must fail closed,
                    # not hide another create call beside the safe examples.
                    while command and command[0] in ("if", "elif", "then", "else", "while", "until", "do", "!", "{", "}"):
                        command.pop(0)
                    # Literal echo/printf data is not an invocation. A
                    # substitution-like payload is ambiguous: reject it rather
                    # than silently treating an executable helper call as data.
                    if command and (
                        command[0] not in ("echo", "printf")
                        or any("`" in arg or "$(" in arg for arg in command)
                    ) and re.search(
                        r"""(?:\$(?:HELPER|\{HELPER\})|(?:[^\s]*/)?pr_review_workspace\.py)["']?\s+(?:\S+\s+)*["']?create["']?(?:\s|$)""",
                        " ".join(command),
                    ):
                        command = ["$HELPER" if arg == "${HELPER}" else arg for arg in command]
                        assert command[:6] == ["uv", "run", "--no-project", "python", "$HELPER", "create"], (
                            f"unparsed helper create invocation: {command}"
                        )
                        create_arguments.append(command[6:])
                    command = []
                else:
                    command.append(token)
    assert create_arguments, "skill has no executable helper create command"
    model_arguments = []
    for args in create_arguments:
        options: dict[str, list[str]] = {"--temp-root": [], "--model-name": []}
        for index, arg in enumerate(args):
            flag, equals, value = arg.partition("=")
            if flag in options:
                values = [value] if equals else args[index + 1:index + 2]
                assert values and values[0], args
                options[flag].extend(values)
        # Count both --flag value and --flag=value; a later override must not
        # move the workspace outside the tool allow-list's /tmp boundary.
        assert options["--temp-root"] == ["/tmp"], args
        assert len(options["--model-name"]) <= 1, args
        model_arguments.append(options["--model-name"])
    # Keep both explicit-model and session-model CLI forms runnable, without
    # selecting them by the preceding runtime paragraph.
    assert ["$MODEL_NAME"] in model_arguments
    assert [] in model_arguments


@pytest.mark.parametrize("skill_path", [AGENTS_SKILL])
@pytest.mark.parametrize(
    ("pr_url", "expected_root", "expected_remote"),
    [
        ("https://github.com/usaturn/create-reso-world/pull/1", TOPLEVEL, "origin"),
        ("https://github.com/usaturn/resoloop/pull/2", TOPLEVEL / "external" / "resoloop", "origin"),
        # An upstream PR's pull/<N>/head lives in the upstream repository.
        ("https://github.com/orange3134/resoloop/pull/3", TOPLEVEL / "external" / "resoloop", "upstream"),
    ],
)
def test_pr_review_resolver_selects_only_registered_repositories(
    skill_path: Path,
    pr_url: str,
    expected_root: Path,
    expected_remote: str,
    resolver_fixture: ResolverFixture,
) -> None:
    main_root, pr_remote = resolver_fixture.resolve(pr_url, skill_path=skill_path)
    assert main_root == expected_root
    assert pr_remote == expected_remote


@pytest.mark.parametrize(
    ("repository", "expected_remote"),
    [("usaturn/create-reso-world", "origin"), ("usaturn/resoloop", "origin"), ("orange3134/resoloop", "upstream")],
)
def test_pr_review_resolver_rejects_a_linked_toplevel_before_fetch(
    tmp_path: Path, repository: str, expected_remote: str
) -> None:
    resolver = make_resolver(tmp_path)
    worktree = tmp_path / "parent-wt"
    _git(resolver.toplevel, "worktree", "add", "--detach", str(worktree))
    pr_url = f"https://github.com/{repository}/pull/16"
    try:
        linked_resolver = ResolverFixture(toplevel=worktree)
        with pytest.raises(ResolverStopped) as stopped:
            linked_resolver.resolve(pr_url, skill_path=AGENTS_SKILL)
        assert stopped.value.returncode == 66
        assert "linked worktree" in stopped.value.stderr
        assert "main checkout" in stopped.value.stderr
        assert "create-reso-world" in stopped.value.stderr
        assert str(worktree) in stopped.value.stderr
        assert "scripts/resoloop-fork.sh clone" not in stopped.value.stderr
        # The resolver stops before returning a root to the following fetch.
        assert stopped.value.stdout == ""
        main_root, pr_remote = resolver.resolve(pr_url, skill_path=AGENTS_SKILL)
        expected_root = (
            resolver.toplevel if repository == "usaturn/create-reso-world" else resolver.toplevel / "external/resoloop"
        )
        assert main_root == expected_root
        assert pr_remote == expected_remote
    finally:
        _git(resolver.toplevel, "worktree", "remove", "--force", str(worktree))


@pytest.mark.parametrize("skill_path", [AGENTS_SKILL])
def test_pr_review_resolver_stops_for_unknown_repository(skill_path: Path, resolver_fixture: ResolverFixture) -> None:
    with pytest.raises(ResolverStopped) as stopped:
        resolver_fixture.resolve(
            "https://github.com/other/repository/pull/3",
            skill_path=skill_path,
        )
    assert stopped.value.returncode == 66
    assert "unsupported PR repository: other/repository" in stopped.value.stderr


@pytest.mark.parametrize(
    ("owner", "fork"),
    [
        ("orange3134", "missing"),
        ("usaturn", "missing"),
        ("orange3134", "plain"),
        ("orange3134", "wrong-origin"),
        ("orange3134", "wrong-upstream"),
    ],
)
def test_pr_review_resolver_stops_without_a_verified_fork_checkout(tmp_path: Path, owner: str, fork: str) -> None:
    # A plain directory under the parent must not resolve to the parent's
    # own checkout, and a checkout with other remotes is not the fork.
    resolver = make_resolver(tmp_path, fork=fork)
    with pytest.raises(ResolverStopped) as stopped:
        resolver.resolve(f"https://github.com/{owner}/resoloop/pull/4", skill_path=AGENTS_SKILL)
    assert stopped.value.returncode == 66
    assert "scripts/resoloop-fork.sh clone" in stopped.value.stderr
    assert stopped.value.stdout == ""


OTHER_URL = "https://github.com/other/repository/pull/3"


def build_checkout(path: Path, remotes: dict[str, str]) -> Path:
    """A checkout of its own outside the parent, with the given remotes."""
    path.mkdir(parents=True)
    _git(path, "init")
    _git(path, "commit", "--allow-empty", "-m", "init")
    for name, url in remotes.items():
        _git(path, "remote", "add", name, url)
    return path.resolve()


@pytest.fixture(params=["bash", "zsh-default", "zsh-nounset"])
def resolver_shell(request: pytest.FixtureRequest) -> tuple[str, bool]:
    shell = "zsh" if request.param.startswith("zsh") else "bash"
    if shell == "zsh" and shutil.which(shell) is None:
        pytest.skip(f"{shell} is not installed; skipping only its resolver cases")
    return shell, request.param != "zsh-default"


@pytest.mark.parametrize(
    ("remotes", "expected_remote"),
    [
        ({"origin": "https://github.com/other/repository.git"}, "origin"),
        # A fork checkout: the PR's pull/<N>/head lives in the base repository.
        (
            {"origin": "https://github.com/someone/repository.git", "upstream": "git@github.com:other/repository.git"},
            "upstream",
        ),
    ],
)
def test_pr_review_resolver_uses_an_explicit_code_root(
    tmp_path: Path, remotes: dict[str, str], expected_remote: str, resolver_shell: tuple[str, bool]
) -> None:
    resolver = make_resolver(tmp_path)
    checkout = build_checkout(tmp_path / "elsewhere" / "repository", remotes)
    shell, nounset = resolver_shell
    main_root, pr_remote = resolver.resolve(
        OTHER_URL, skill_path=AGENTS_SKILL, code_root=str(checkout), shell=shell, nounset=nounset
    )
    assert main_root == checkout
    assert pr_remote == expected_remote


@pytest.mark.parametrize(
    ("remotes", "count"),
    [
        ({"origin": "https://github.com/someone/repository.git"}, 0),
        (
            {"origin": "https://github.com/other/repository.git", "mirror": "git@github.com:other/repository.git"},
            2,
        ),
    ],
)
def test_pr_review_resolver_requires_exactly_one_matching_remote(
    tmp_path: Path, remotes: dict[str, str], count: int, resolver_shell: tuple[str, bool]
) -> None:
    resolver = make_resolver(tmp_path)
    checkout = build_checkout(tmp_path / "elsewhere" / "repository", remotes)
    shell, nounset = resolver_shell
    with pytest.raises(ResolverStopped) as stopped:
        resolver.resolve(OTHER_URL, skill_path=AGENTS_SKILL, code_root=str(checkout), shell=shell, nounset=nounset)
    assert stopped.value.returncode == 66
    assert f"has {count} remotes for other/repository; exactly one is required" in stopped.value.stderr
    assert stopped.value.stdout == ""


@pytest.mark.parametrize(
    "case",
    [
        "relative",
        "git-directory",
        "nested-directory",
        "linked-worktree",
        "missing",
    ],
)
def test_pr_review_resolver_rejects_an_unverified_code_root(tmp_path: Path, case: str) -> None:
    resolver = make_resolver(tmp_path)
    remotes = {"origin": "https://github.com/other/repository.git"}
    checkout = build_checkout(tmp_path / "elsewhere" / "repository", remotes)
    (checkout / "src").mkdir()
    worktree = tmp_path / "elsewhere" / "repository-wt"
    if case == "linked-worktree":
        # The helper only creates review worktrees from the main checkout.
        _git(checkout, "worktree", "add", "--detach", str(worktree))
    code_root = {
        "relative": "elsewhere/repository",
        "git-directory": str(checkout / ".git"),
        # Inside the right checkout but not its root: the review must not start there.
        "nested-directory": str(checkout / "src"),
        "linked-worktree": str(worktree),
        "missing": str(tmp_path / "absent"),
    }.get(case, str(checkout))
    with pytest.raises(ResolverStopped) as stopped:
        resolver.resolve(OTHER_URL, skill_path=AGENTS_SKILL, code_root=code_root)
    assert stopped.value.returncode == 66
    assert "CODE_ROOT" in stopped.value.stderr
    if case == "linked-worktree":
        assert "linked worktree" in stopped.value.stderr


def test_pr_review_resolver_rejects_a_code_root_that_contradicts_a_known_route(tmp_path: Path) -> None:
    resolver = make_resolver(tmp_path)
    checkout = build_checkout(tmp_path / "elsewhere" / "repository", {"origin": PARENT_ORIGIN})
    with pytest.raises(ResolverStopped) as stopped:
        resolver.resolve(
            "https://github.com/usaturn/create-reso-world/pull/1", skill_path=AGENTS_SKILL, code_root=str(checkout)
        )
    assert stopped.value.returncode == 66
    main_root, pr_remote = resolver.resolve(
        "https://github.com/usaturn/create-reso-world/pull/1",
        skill_path=AGENTS_SKILL,
        code_root=str(resolver.toplevel),
    )
    assert (main_root, pr_remote) == (resolver.toplevel, "origin")


@pytest.mark.parametrize(
    "origin_url",
    [
        "git@github.com:usaturn/create-reso-world.git",
        "ssh://git@github.com/usaturn/create-reso-world.git",
        "ssh://git@github.com/usaturn/create-reso-world",
    ],
)
def test_pr_review_resolver_accepts_github_remote_formats_for_toplevel(tmp_path: Path, origin_url: str) -> None:
    resolver = make_resolver(tmp_path)
    _git(resolver.toplevel, "remote", "set-url", "origin", origin_url)
    main_root, pr_remote = resolver.resolve(
        "https://github.com/usaturn/create-reso-world/pull/16", skill_path=AGENTS_SKILL
    )
    assert (main_root, pr_remote) == (resolver.toplevel, "origin")


@pytest.mark.parametrize(("owner", "expected_remote"), [("usaturn", "origin"), ("orange3134", "upstream")])
def test_pr_review_resolver_accepts_ssh_urls_for_fork_remotes(
    tmp_path: Path, owner: str, expected_remote: str
) -> None:
    resolver = make_resolver(tmp_path)
    checkout = resolver.toplevel / "external/resoloop"
    _git(checkout, "remote", "set-url", "origin", "ssh://git@github.com/usaturn/resoloop.git")
    _git(checkout, "remote", "set-url", "upstream", "ssh://git@github.com/orange3134/resoloop")
    main_root, pr_remote = resolver.resolve(f"https://github.com/{owner}/resoloop/pull/16", skill_path=AGENTS_SKILL)
    assert (main_root, pr_remote) == (checkout, expected_remote)


@pytest.mark.parametrize(
    "remote_url", ["ssh://git@github.com/other/repository.git", "ssh://git@github.com/other/repository"]
)
def test_pr_review_resolver_accepts_ssh_urls_for_code_root(tmp_path: Path, remote_url: str) -> None:
    resolver = make_resolver(tmp_path)
    checkout = build_checkout(tmp_path / "elsewhere/repository", {"origin": remote_url})
    main_root, pr_remote = resolver.resolve(OTHER_URL, skill_path=AGENTS_SKILL, code_root=str(checkout))
    assert (main_root, pr_remote) == (checkout, "origin")


@pytest.mark.parametrize(
    "remote_url",
    [
        "https://example.com/other/repository.git",
        "git@example.com:other/repository.git",
        "ssh://git@example.com/other/repository.git",
        "ssh://git@github.com/someone/repository.git",
    ],
)
def test_pr_review_resolver_rejects_mismatched_remote_urls(tmp_path: Path, remote_url: str) -> None:
    resolver = make_resolver(tmp_path)
    checkout = build_checkout(tmp_path / "elsewhere/repository", {"origin": remote_url})
    with pytest.raises(ResolverStopped) as stopped:
        resolver.resolve(OTHER_URL, skill_path=AGENTS_SKILL, code_root=str(checkout))
    assert stopped.value.returncode == 66
    assert "has 0 remotes for other/repository; exactly one is required" in stopped.value.stderr
    assert stopped.value.stdout == ""


@pytest.mark.parametrize("forbidden", ["$TOPLEVEL/devenv", "submodule status -- devenv"])
def test_pr_review_skills_have_no_legacy_path_selection(forbidden: str) -> None:
    for skill in (AGENTS_SKILL,):
        assert forbidden not in skill.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("skill", "relative"),
    [(AGENTS_SKILL, "references/time-budget.md")],
)
def test_review_budget_reference_is_required_and_resolves(skill: Path, relative: str) -> None:
    targets = [target.split("#", 1)[0]
               for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", read(skill))]
    assert relative in targets, "skill lost its budget reference"
    for target in targets:
        if target and not target.startswith(("http:", "https:")):
            assert (skill.parent / target).resolve().is_file(), target
    assert (skill.parent / relative).resolve() == BUDGET_REFERENCE.resolve()


@pytest.mark.parametrize("case", ["implicit", "explicit", "duplicate", "subdirectory"])
def test_external_cwd_does_not_bypass_parent_or_code_preflight(
    tmp_path: Path, case: str, resolver_shell: tuple[str, bool]
) -> None:
    resolver = make_resolver(tmp_path)
    checkout = build_checkout(tmp_path / "other", {"origin": "https://github.com/other/repository.git"})
    if case == "duplicate":
        _git(checkout, "remote", "add", "mirror", "git@github.com:other/repository.git")
    sub = checkout / "src"
    sub.mkdir()
    code = str(sub if case == "subdirectory" else checkout) if case != "implicit" else None
    before = (_git(checkout, "rev-parse", "HEAD").stdout, _git(checkout, "status", "--porcelain").stdout,
              _git(checkout, "remote", "-v").stdout)
    shell, nounset = resolver_shell
    with pytest.raises(ResolverStopped) as stopped:
        resolver.resolve(OTHER_URL, skill_path=AGENTS_SKILL, code_root=code, cwd=checkout,
                         shell=shell, nounset=nounset)
    assert stopped.value.returncode == 66
    assert "PARENT_ROOT" in stopped.value.stderr
    assert stopped.value.stdout == ""
    assert before == (_git(checkout, "rev-parse", "HEAD").stdout, _git(checkout, "status", "--porcelain").stdout,
                      _git(checkout, "remote", "-v").stdout)


@pytest.mark.parametrize("origin", [None, "not-a-url", "https://example.com/usaturn/create-reso-world.git"])
def test_invalid_parent_origin_fails_with_diagnostic_before_using_external_code(
    tmp_path: Path, origin: str | None, resolver_shell: tuple[str, bool]
) -> None:
    resolver = make_resolver(tmp_path)
    if origin is None:
        _git(resolver.toplevel, "remote", "remove", "origin")
    else:
        _git(resolver.toplevel, "remote", "set-url", "origin", origin)
    checkout = build_checkout(tmp_path / "other", {"origin": "https://github.com/other/repository.git"})
    shell, nounset = resolver_shell
    with pytest.raises(ResolverStopped) as stopped:
        resolver.resolve(OTHER_URL, skill_path=AGENTS_SKILL, code_root=str(checkout), shell=shell, nounset=nounset)
    assert stopped.value.returncode == 66
    assert "PARENT_ROOT origin" in stopped.value.stderr
    assert stopped.value.stdout == ""


def test_explicit_parent_keeps_tool_helper_separate_from_external_cwd(tmp_path: Path) -> None:
    resolver = make_resolver(tmp_path)
    checkout = build_checkout(tmp_path / "other", {"base": "https://github.com/other/repository.git"})
    root, remote = resolver.resolve(OTHER_URL, skill_path=AGENTS_SKILL, code_root=str(checkout),
                                    cwd=checkout, parent_root=str(resolver.toplevel))
    assert (root, remote) == (checkout, "base")


def test_missing_context_helper_stops_with_parent_checkout_guidance(tmp_path: Path) -> None:
    resolver = make_resolver(tmp_path)
    helper = resolver.toplevel / "scripts/superpowers_context.py"
    if helper.exists():
        helper.unlink()
    with pytest.raises(ResolverStopped) as stopped:
        resolver.resolve("https://github.com/usaturn/create-reso-world/pull/16", skill_path=AGENTS_SKILL)
    assert stopped.value.returncode == 66
    assert "superpowers_context.py" in stopped.value.stderr
    assert "PARENT_ROOT" in stopped.value.stderr
    assert stopped.value.stdout == ""
