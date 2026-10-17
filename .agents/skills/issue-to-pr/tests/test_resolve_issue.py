"""Exercise the read-only Issue resolver against real Git checkouts and a gh boundary double.

The supported repositories are fixed values on purpose: they bound which repositories
issue-to-pr may create branches and PRs in (AGENTS.md「リポジトリ境界」).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "resolve_issue.py"


@pytest.fixture
def checkout(tmp_path: Path) -> Path:
    root = tmp_path / "checkout"
    subprocess.run(["git", "init", "--quiet", str(root)], check=True)
    subprocess.run(
        ["git", "-C", str(root), "remote", "add", "origin", "https://github.com/usaturn/create-reso-world.git"],
        check=True,
    )
    return root


@pytest.fixture
def gh_stub(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Put a fake gh first on PATH. It records that it ran, so rejections can prove no lookup happened."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    marker = tmp_path / "gh-called"
    gh = bin_dir / "gh"
    gh.write_text(
        f"#!{sys.executable}\n"
        "import os, pathlib, sys\n"
        "pathlib.Path(os.environ['GH_CALLED']).touch()\n"
        "args = sys.argv[1:]\n"
        "if args[:3] != ['issue', 'view', '42'] or '--repo' not in args:\n"
        "    sys.exit(64)\n"
        "if args[args.index('--repo') + 1] != os.environ['EXPECTED_REPO']:\n"
        "    sys.exit(65)\n"
        "if os.environ.get('GH_FAIL'):\n"
        "    print('HTTP 404: Not Found', file=sys.stderr)\n"
        "    sys.exit(1)\n"
        "print(os.environ['GH_RESPONSE'])\n",
        encoding="utf-8",
    )
    gh.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("GH_CALLED", str(marker))
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))
    set_response(monkeypatch, "usaturn/create-reso-world")
    return marker


def set_response(
    monkeypatch: pytest.MonkeyPatch,
    repo: str,
    *,
    state: str = "OPEN",
    number: object = 42,
    url: str | None = None,
) -> None:
    monkeypatch.setenv("EXPECTED_REPO", repo)
    monkeypatch.setenv(
        "GH_RESPONSE",
        json.dumps(
            {
                "number": number,
                "title": "Fix a regression",
                "body": "Keep unrelated work intact.",
                "state": state,
                "url": url if url is not None else f"https://github.com/{repo}/issues/42",
            }
        ),
    )


def resolve(cwd: Path, argument: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--", argument], cwd=cwd, capture_output=True, text=True
    )


def assert_rejected(result: subprocess.CompletedProcess[str]) -> None:
    assert result.returncode == 2, result.stdout
    assert result.stdout == ""
    assert result.stderr.startswith("issue-to-pr:")


@pytest.mark.parametrize(
    ("argument", "origin", "repo"),
    [
        ("https://github.com/usaturn/resoloop/issues/42", None, "usaturn/resoloop"),
        ("https://github.com/Usaturn/Create-Reso-World/issues/42", None, "usaturn/create-reso-world"),
        ("usaturn/resoloop-meshy#42", None, "usaturn/resoloop-meshy"),
        ("Usaturn/Create-Reso-World#42", None, "usaturn/create-reso-world"),
        ("#42", None, "usaturn/create-reso-world"),
        ("#42", "git@github.com:usaturn/resoloop.git", "usaturn/resoloop"),
        ("#42", "ssh://git@github.com/usaturn/resoloop-meshy", "usaturn/resoloop-meshy"),
        ("#42", "https://github.com/Usaturn/Resoloop-Meshy/", "usaturn/resoloop-meshy"),
        ("  #42 \n", None, "usaturn/create-reso-world"),
    ],
)
def test_resolves_supported_forms_without_changing_git(
    checkout: Path,
    gh_stub: Path,
    monkeypatch: pytest.MonkeyPatch,
    argument: str,
    origin: str | None,
    repo: str,
) -> None:
    if origin:
        subprocess.run(["git", "remote", "set-url", "origin", origin], cwd=checkout, check=True)
    set_response(monkeypatch, repo)
    before = subprocess.check_output(["git", "status", "--porcelain"], cwd=checkout)
    result = resolve(checkout, argument)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {
        "repo": repo,
        "number": 42,
        "url": f"https://github.com/{repo}/issues/42",
        "title": "Fix a regression",
        "body": "Keep unrelated work intact.",
    }
    assert subprocess.check_output(["git", "status", "--porcelain"], cwd=checkout) == before
    assert subprocess.check_output(["git", "for-each-ref"], cwd=checkout) == b""


def test_accepts_repo_casing_only_in_response_url(
    checkout: Path, gh_stub: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    url = "https://github.com/USATURN/Create-Reso-World/issues/42"
    set_response(monkeypatch, "usaturn/create-reso-world", url=url)
    result = resolve(checkout, "#42")
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["url"] == url


@pytest.mark.parametrize(
    "argument",
    [
        "https://github.com/usaturn/create-reso-world/pull/42",
        "https://github.com/other/repo/issues/42",
        "https://github.com/orange3134/resoloop/issues/42",
        "other/repo#42",
        "orange3134/resoloop#42",
        "resoloop#42",
        "42",
        "#0",
        "#042",
        "#-42",
        "#42; touch injected",
        "#42 #43",
        "#42 推奨案で",
        "",
        "https://github.com/usaturn/resoloop/issues/42?x=1",
        "https://github.com/usaturn/resoloop/issues/42#issuecomment-1",
        "https://github.com.evil.test/usaturn/resoloop/issues/42",
        "usaturn/resoloop#42#43",
        "'#42",
    ],
)
def test_rejects_input_before_looking_up_issue(checkout: Path, gh_stub: Path, argument: str) -> None:
    result = resolve(checkout, argument)
    assert_rejected(result)
    assert not gh_stub.exists()
    assert not (checkout / "injected").exists()


@pytest.mark.parametrize(
    "argument",
    [
        "#42 --merge",
        "#42 --merge=1",
        "--implement self #42",
        "#42 --implement=self",
        "#42 --merge --max-cycles 2",
        "#42 --hold-action skip",
        "#42 --assign implement=codex",
        "#42 --template x.toml",
        "#42 --config x.toml",
        "#42 --fresh-review",
    ],
)
def test_rejects_options_with_reason(checkout: Path, gh_stub: Path, argument: str) -> None:
    result = resolve(checkout, argument)
    assert_rejected(result)
    assert "#116" in result.stderr
    assert not gh_stub.exists()


@pytest.mark.parametrize("argument", ["#42 --foo", "#42 -m", "--dry-run #42"])
def test_rejects_unknown_options(checkout: Path, gh_stub: Path, argument: str) -> None:
    result = resolve(checkout, argument)
    assert_rejected(result)
    assert "未知のオプション" in result.stderr
    assert "#116" not in result.stderr
    assert not gh_stub.exists()


@pytest.mark.parametrize(
    "origin",
    [
        "https://github.com/other/repo.git",
        "https://github.com/orange3134/resoloop.git",
        "https://gitlab.com/usaturn/create-reso-world.git",
        "https://github.com/usaturn/create-reso-world.git?x=1",
        None,
    ],
)
def test_number_with_unusable_origin_stops(checkout: Path, gh_stub: Path, origin: str | None) -> None:
    if origin is None:
        subprocess.run(["git", "remote", "rename", "origin", "upstream"], cwd=checkout, check=True)
    else:
        subprocess.run(["git", "remote", "set-url", "origin", origin], cwd=checkout, check=True)
    result = resolve(checkout, "#42")
    assert_rejected(result)
    assert not gh_stub.exists()


@pytest.mark.parametrize(
    "origin",
    [
        "https://user:s3cr3t-token@github.com/usaturn/create-reso-world.git",
        "https://s3cr3t-token@gitlab.com/usaturn/create-reso-world.git",
    ],
)
def test_origin_with_credentials_stops_without_printing_them(
    checkout: Path, gh_stub: Path, origin: str
) -> None:
    subprocess.run(["git", "remote", "set-url", "origin", origin], cwd=checkout, check=True)
    result = resolve(checkout, "#42")
    assert_rejected(result)
    assert "s3cr3t-token" not in result.stderr
    assert not gh_stub.exists()


def test_number_outside_a_checkout_stops(tmp_path: Path, gh_stub: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    result = resolve(outside, "#42")
    assert_rejected(result)
    assert not gh_stub.exists()


@pytest.mark.parametrize(
    ("state", "number", "url"),
    [
        ("CLOSED", 42, None),
        ("MERGED", 42, "https://github.com/usaturn/create-reso-world/pull/42"),
        ("OPEN", 42, "https://github.com/usaturn/create-reso-world/pull/42"),
        ("OPEN", 99, None),
        ("OPEN", 42, "https://github.com/usaturn/create-reso-world/issues/43"),
        ("OPEN", 42, "https://github.com/usaturn/resoloop/issues/42"),
        ("OPEN", 42, "http://github.com/usaturn/create-reso-world/issues/42"),
        ("OPEN", 42, "https://GITHUB.COM/usaturn/create-reso-world/issues/42"),
        ("OPEN", 42, "https://github.com.evil.test/usaturn/create-reso-world/issues/42"),
        ("OPEN", 42, "https://github.com/usaturn/create-reso-world/issues/42/"),
        ("OPEN", 42, "https://github.com/usaturn/create-reso-world/issues/42?x=1"),
        ("OPEN", 42, "https://github.com/usaturn/create-reso-world/issues/42#c"),
        ("OPEN", 42, "https://github.com/usaturn/create-reso-world/issues/042"),
    ],
)
def test_rejects_mismatched_or_closed_response(
    checkout: Path, gh_stub: Path, monkeypatch: pytest.MonkeyPatch, state: str, number: int, url: str | None
) -> None:
    set_response(monkeypatch, "usaturn/create-reso-world", state=state, number=number, url=url)
    assert_rejected(resolve(checkout, "#42"))


@pytest.mark.parametrize(
    "response",
    [
        "not JSON",
        "[]",
        "{}",
        '{"number": "42", "title": "t", "body": "b", "state": "OPEN", '
        '"url": "https://github.com/usaturn/create-reso-world/issues/42"}',
        '{"number": true, "title": "t", "body": "b", "state": "OPEN", '
        '"url": "https://github.com/usaturn/create-reso-world/issues/42"}',
        '{"number": 42, "title": null, "body": "b", "state": "OPEN", '
        '"url": "https://github.com/usaturn/create-reso-world/issues/42"}',
        '{"number": 42, "title": "t", "body": "b", "state": "open", '
        '"url": "https://github.com/usaturn/create-reso-world/issues/42"}',
    ],
)
def test_rejects_malformed_response(
    checkout: Path, gh_stub: Path, monkeypatch: pytest.MonkeyPatch, response: str
) -> None:
    monkeypatch.setenv("GH_RESPONSE", response)
    assert_rejected(resolve(checkout, "#42"))


def test_reports_gh_failure_without_trying_another_repository(
    checkout: Path, gh_stub: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GH_FAIL", "1")
    result = resolve(checkout, "#42")
    assert_rejected(result)
    assert "404" in result.stderr
