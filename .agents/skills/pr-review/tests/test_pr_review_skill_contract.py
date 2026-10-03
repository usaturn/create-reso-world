from __future__ import annotations

import json
import os
import re
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
    """Extract the MAIN_ROOT resolver bash block from a skill document."""
    pattern = re.compile(
        r"```bash\n("
        r"[ \t]*PR_URL=\$\(printf '%s' \"\$PR_JSON\" \| jq -r \.url\)\n"
        r"[ \t]*TOPLEVEL=\$\(git rev-parse --show-toplevel\)\n"
        r"[ \t]*github_repository\(\) \{.*?"
        r"[ \t]*fi\n"
        r")[ \t]*```",
        re.DOTALL,
    )
    match = pattern.search(skill_text)
    assert match is not None, "resolver bash block not found in skill"
    block = match.group(1)
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
    ) -> tuple[Path, str]:
        script = extract_resolver_script(read(skill_path))
        pr_json = json.dumps({"url": pr_url})
        # Emit MAIN_ROOT and PR_REMOTE after the skill block for the test harness.
        shell_options = "set -euo pipefail" if nounset else "set -eo pipefail"
        harness = f"""{shell_options}
PR_JSON={json.dumps(pr_json)}
CODE_ROOT={json.dumps(code_root or "")}
{script}
printf '%s\\n' "$MAIN_ROOT" "$PR_REMOTE"
"""
        shell_args = [shell, "-f"] if shell == "zsh" else [shell]
        completed = subprocess.run(
            [*shell_args, "-c", harness],
            cwd=self.toplevel,
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


def assert_review_contract(content: str) -> None:
    # The user-supplied value is kept raw ($PR_ARG) so gh resolves a URL's
    # owner/repo itself; every later gh call is pinned to the canonical
    # $PR_URL so a foreign-repository URL cannot silently review the
    # same-numbered PR of the checkout's repository.
    assert 'gh pr view "$PR_ARG"' in content
    assert 'gh pr view "$PR_URL" --comments' in content
    assert 'gh pr diff "$PR_URL"' in content
    assert 'gh pr view "$PR_NUMBER"' not in content
    assert 'gh pr diff "$PR_NUMBER"' not in content
    # The helper lives in this repository's skill tree, so it must resolve
    # from $TOPLEVEL even when MAIN_ROOT points at external/resoloop.
    assert 'HELPER="$TOPLEVEL/' in content
    assert 'HELPER="$MAIN_ROOT/' not in content
    assert 'git rev-parse --short=12 "$PR_HEAD"' in content
    assert 'date -u +"%Y-%m-%dT%H:%M:%SZ"' in content
    assert "previous_review" in content
    assert "Review history" in content
    assert "Reviewed at (UTC)" in content
    assert "Initial" in content
    assert "Update" in content
    assert "検出時 HEAD" in content
    assert "Resolved findings" in content
    assert "解消確認時 HEAD" in content
    assert "不明（旧形式）" in content
    assert content.count("headRefOid") >= 3
    assert "他モデルのレビュー本文" in content
    assert "PR_URL=$(printf '%s' \"$PR_JSON\" | jq -r .url)" in content
    assert "github_repository()" in content
    assert 'MAIN_ROOT="$TOPLEVEL"' in content
    assert 'FORK_ROOT="$TOPLEVEL/external/resoloop"' in content
    assert 'MAIN_ROOT="$FORK_ROOT"' in content
    assert "usaturn/resoloop" in content
    assert "orange3134/resoloop" in content
    assert 'git -C "$TOPLEVEL" remote get-url origin' in content
    assert 'git -C "$FORK_ROOT" remote get-url upstream' in content
    assert "scripts/resoloop-fork.sh clone" in content
    assert "unsupported PR repository" in content
    assert 'elif [[ -n "$CODE_ROOT" ]]; then' in content
    assert "exit 66" in content
    assert "リポジトリ境界" in content
    assert 'fetch "$PR_REMOTE" "+pull/<PR_NUMBER>/head:$PR_REF"' in content
    assert "external/resoloop/reviews/" in content
    assert "submodule" not in content
    assert "#160-feature-issue-148-fail-fast" in content
    assert "reviews/#" in content
    assert "追跡パス" not in content
    assert "if printf '%s' \"$PR_URL\" | grep -q devenv; then" not in content
    assert 'MAIN_ROOT="$TOPLEVEL/devenv"' not in content
    assert 'MAIN_ROOT="$(pwd)"' not in content


def assert_heavy_verification_is_not_rerun_contract(content: str) -> None:
    # Review does not rerun the bulk suites: the implementation and CI already
    # ran them and repeating them is too slow. Related pytest, single test
    # scripts, REPL and minimal repro scripts remain allowed. helper verify is
    # destination fingerprinting, not a test run.
    assert "重い一括検証を再実行しない" in content
    assert "bash .devcontainer/run-tests.bash" in content
    assert "scripts/resoloop-fork.sh test" in content
    assert "実装時と CI で確認済み" in content
    assert "冗長" in content
    assert "3. **実行検証**" in content
    assert "関連する pytest" in content
    assert "REPL" in content
    assert "最小再現スクリプト" in content
    assert "helper の `verify`" in content
    assert "`AGENTS.md` や他のスキルが求める完了前の検証より優先する" in content
    assert "scripts/ci/" not in content
    assert "動かして確かめることも行わない" not in content
    assert "プロジェクトのテストを実行しない" not in content
    assert "プロジェクトのテストコマンド" not in content
    assert "既存テストファイルは読むが実行しない" not in content
    assert "npm test" not in content


@pytest.mark.parametrize("skill", [AGENTS_SKILL])
def test_pr_review_skills_define_review_update_contract(skill: Path) -> None:
    assert_review_contract(read(skill))


@pytest.mark.parametrize("skill", [AGENTS_SKILL])
def test_pr_review_skills_do_not_rerun_heavy_verification(skill: Path) -> None:
    assert_heavy_verification_is_not_rerun_contract(read(skill))


def assert_cleanup_contract(content: str) -> None:
    assert 'cleanup --state "$STATE_FILE"' in content
    assert "セッションディレクトリ" in content
    assert "レビュー本文の「根拠」に転記" in content
    assert "削除は helper の `cleanup` だけが行う" in content
    # The "no $WT paths in the final response" rule must stay scoped to a
    # successful cleanup; on the stop-unconfirmed branch $WT still exists and
    # its full path must be reported.
    assert "`cleanup` 成功後は `$WT` 配下のパスは既に存在しないため案内に含めない" in content
    # Cleanup must stay gated on a verified save and must never be hand-rolled.
    assert "worktree、session state、外部バックアップを自動削除しない" not in content
    assert "残した worktree の完全パス" not in content
    assert "最終応答後も削除しない" not in content


@pytest.mark.parametrize("skill", [AGENTS_SKILL])
def test_pr_review_skills_require_session_cleanup(skill: Path) -> None:
    assert_cleanup_contract(read(skill))


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
    assert "対象 PR（スキル呼び出しの引数）: $ARGUMENTS" in content
    assert re.search(r"\$[0-9]", content) is None


ALLOWED_TOOLS = (
    "Read, Grep, Glob, Bash(gh *), Bash(git *), Bash(date *), "
    "Bash(uv run --no-project python *pr_review_workspace.py *), "
    "Edit(/tmp/pr-review-*/review-backup/**), Write(/tmp/pr-review-*/review-backup/**), Agent"
)


def test_skill_keeps_claude_code_permissions_consistent() -> None:
    content = read(AGENTS_SKILL)
    head = yaml.safe_load(content.split("---", 2)[1])
    # Claude Code only pre-approves what this line lists; a dropped entry turns
    # the helper, the draft backup or the delegation into a permission prompt.
    assert head["allowed-tools"] == ALLOWED_TOOLS
    assert head["argument-hint"] == "<PR番号またはURL>"
    assert "CODEX_THREAD_ID" in content
    create_lines = [line for line in content.splitlines() if '"$HELPER" create' in line]
    assert len(create_lines) == 2
    for line in create_lines:
        # allowed-tools only permits Edit/Write under /tmp/pr-review-*, so every
        # runtime pins the helper's temp root there.
        assert "--temp-root /tmp" in line, line
    # Codex resolves the model itself; only the other runtimes pass it once.
    with_model = [line for line in create_lines if "--model-name" in line]
    assert len(with_model) == 1
    assert with_model[0].count('--model-name "$MODEL_NAME"') == 1
    codex_block = content.split("Codex では次を実行する", 1)[1].split("```", 2)[1]
    assert '"$HELPER" create' in codex_block
    assert "--model-name" not in codex_block


def test_skill_keeps_runtime_specific_notes() -> None:
    content = read(AGENTS_SKILL)
    assert "## ランタイム別の注意" in content
    for heading in ("### 対象 PR の受け取り", "### Claude Code", "### Codex", "### Devin", "### pi"):
        assert heading in content
    assert "You are powered by" in content
    assert "`~/.local/share/devin/cli/transcripts/`" in content
    assert "pi-model-name" in content
    # Every runtime that passes MODEL_NAME uses the identifier verbatim.
    assert "既存レビューのファイル名から推測・短縮・一般化しない" in content


def test_delegation_limits_stay_in_the_skill_body() -> None:
    content = read(AGENTS_SKILL)
    for rule in (
        "サブエージェントは `$WT` 上のコードと PR 差分（`gh pr diff` の結果）のみ調査する",
        "`reviews/` 全体と `$PREVIOUS_REVIEW` の読解はメインエージェントだけが行う",
        "委譲時は `reviews/` を調査範囲から明示的に除外する",
        "この読解はメインエージェントのみが行い、サブエージェントに委譲しない",
        "指摘の根拠となる精読をサブエージェント任せにしない",
        "反証試行のための追加委譲はしない",
        "サブエージェントの報告のみを根拠に【検証済み】を付けない",
        "既存 review 本文をサブエージェントへ渡していないか",
    ):
        assert rule in content, rule


def test_main_agent_traces_the_change_when_not_delegating() -> None:
    content = read(AGENTS_SKILL)
    step5 = content.split("5. **コンテキスト読解", 1)[1].split("6. **", 1)[0]
    assert "委譲しない場合は、メインエージェントが自分で" in step5
    for target in ("呼び出し元・呼び出し先", "依存関係ファイル", "既存テスト"):
        assert target in step5.split("委譲しない場合は、メインエージェントが自分で", 1)[1], target


def test_pr_argument_fallback_is_stated_once() -> None:
    content = read(AGENTS_SKILL)
    step1 = content.split("1. **PR情報の取得**", 1)[1].split("2. **", 1)[0]
    assert "`PR_ARG` が確定しない場合" in step1
    assert "   - 未指定の場合、" not in step1


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
    assert stopped.value.returncode == 64
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
    assert stopped.value.returncode == 65
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


def test_other_repositories_keep_reviews_out_of_the_document_store() -> None:
    content = read(AGENTS_SKILL)
    assert 'CODE_ROOT="${CODE_ROOT:-}"' in content
    assert "推測で埋めない" in content
    assert "`$CODE_ROOT/reviews/`" in content
    assert "Spec・Plan ではない" in content


@pytest.mark.parametrize("forbidden", ["$TOPLEVEL/devenv", "submodule status -- devenv"])
def test_pr_review_skills_have_no_legacy_path_selection(forbidden: str) -> None:
    for skill in (AGENTS_SKILL,):
        assert forbidden not in skill.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("skill", "relative"),
    [(AGENTS_SKILL, "references/time-budget.md")],
)
def test_review_budget_reference_is_required_and_resolves(skill: Path, relative: str) -> None:
    content = read(skill)
    assert f"[時間予算と委譲規約]({relative})" in content
    assert "最初の PR API 呼び出しより前に全文を読む" in content
    assert (skill.parent / relative).resolve() == BUDGET_REFERENCE.resolve()
    assert BUDGET_REFERENCE.is_file()
    assert "0. **時間予算の開始**" in content


def test_review_budget_has_fixed_deadlines_and_safe_fallback() -> None:
    content = read(BUDGET_REFERENCE)
    for required in (
        "全体 45 分",
        "開始 40 分",
        "予約枠は 5 分",
        "起動時刻 + 10分",
        "実質進捗から 5 分",
        "300 行以下",
        "3 個以下",
        "進捗があっても延長しない",
        "停止確認",
        "再委譲",
        "最大 1 件",
        "停止手段を利用できなければ委譲を省略する",
        "同期起動のみのランタイムでは委譲しない",
        "呼び出し元・呼び出し先",
        "指摘の根拠となる精読をサブエージェント任せにしない",
        "サブエージェントの報告のみを根拠に【検証済み】を付けない",
        "停止確認不能なら cleanup を省略する",
        "未検証",
        "実時間保証ではない",
        "応答本文へ逐次記し",
        "重要な未検証候補",
        "未再検証の過去指摘",
        "差分の実質的な未読箇所",
    ):
        assert required in content
    assert (
        content.index("`Request changes`") < content.index("`Needs manual verification`") < content.index("`Approve`")
    )


@pytest.mark.parametrize("skill", [AGENTS_SKILL])
def test_pr_review_skills_keep_delegation_optional_and_readonly(skill: Path) -> None:
    content = read(skill)
    assert "読み取り専用の補助委譲として" in content
    assert "起動してよい" in content
    assert "並行して起動する" not in content


@pytest.mark.parametrize("skill", [AGENTS_SKILL])
def test_incomplete_reviews_preserve_pending_and_gate_approval(skill: Path) -> None:
    content = read(skill)
    for section in (
        "Review coverage",
        "Unverified candidates",
        "Pending previous findings",
        "Review timing",
    ):
        assert section in content
    for rule in (
        "未再検証の指摘を Resolved にしない",
        "次回更新で Pending previous findings も再検証する",
        "active / pending / resolved 全体で ID の衝突を避ける",
        "確認不足判定は coverage と pending も参照する",
        "停止確認不能なら cleanup を省略する",
        "重要な未検証候補",
        "未再検証の過去指摘",
        "差分の実質的な未読箇所",
    ):
        assert rule in content
    assert (
        content.index("**Request changes**")
        < content.index("**Needs manual verification**")
        < content.index("**Approve**")
    )


def test_timing_separates_observation_from_runtime_measurement() -> None:
    content = read(BUDGET_REFERENCE)
    for required in (
        "turn_duration",
        "durationMs",
        "tool_use",
        "tool_result",
        "モデル応答までの観測間隔",
        "ツール実時間は不明",
        "ターン外時間",
        "和集合",
        "並行した区間を総時間へ加算しない",
        "出力しない",
        "未完の末尾行",
        "save/cleanup",
        "最終応答",
        "600 秒以下",
        "2700 秒以下",
    ):
        assert required in content
