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
    ("argument", "repo"),
    [
        ("https://github.com/usaturn/resoloop/issues/42", "usaturn/resoloop"),
        ("usaturn/resoloop-meshy#42", "usaturn/resoloop-meshy"),
        ("#42", "usaturn/create-reso-world"),
    ],
)
def test_resolves_supported_forms_without_changing_git(
    checkout: Path,
    gh_stub: Path,
    monkeypatch: pytest.MonkeyPatch,
    argument: str,
    repo: str,
) -> None:
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
        "merge": None,
        "implement": None,
    }
    assert subprocess.check_output(["git", "status", "--porcelain"], cwd=checkout) == before
    assert subprocess.check_output(["git", "for-each-ref"], cwd=checkout) == b""


@pytest.mark.parametrize(
    "argument",
    [
        "https://github.com/orange3134/resoloop/issues/42",
        "https://github.com.evil.test/usaturn/resoloop/issues/42",
    ],
)
def test_rejects_input_before_looking_up_issue(checkout: Path, gh_stub: Path, argument: str) -> None:
    result = resolve(checkout, argument)
    assert_rejected(result)
    assert not gh_stub.exists()


def unchanged(checkout: Path, before: bytes) -> bool:
    return (
        subprocess.check_output(["git", "status", "--porcelain"], cwd=checkout) == before
        and subprocess.check_output(["git", "for-each-ref"], cwd=checkout) == b""
    )


@pytest.mark.parametrize(
    ("argument", "loop_args"),
    [
        (
            "#42 --merge --max-cycles 2 --assign inspect=claude-opus,devin-swe --assign implement=self",
            ["--max-cycles", "2", "--assign", "inspect=claude-opus,devin-swe", "--assign", "implement=self"],
        ),
        # start の argparse と同じく、繰り返しは書いた順のまま渡す（--max-cycles は後の値が効く）
        ("#42 --merge --max-cycles 2 --max-cycles 3", ["--max-cycles", "2", "--max-cycles", "3"]),
    ],
)
def test_merge_arguments_are_passed_in_the_written_order(
    checkout: Path, gh_stub: Path, argument: str, loop_args: list[str]
) -> None:
    before = subprocess.check_output(["git", "status", "--porcelain"], cwd=checkout)
    result = resolve(checkout, argument)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["number"] == 42
    assert payload["merge"] == {"loop_args": loop_args}
    assert payload["implement"] is None
    assert unchanged(checkout, before)


def test_template_and_config_become_absolute_from_the_starting_directory(
    checkout: Path, gh_stub: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """loop.py は別の cwd で起動しうる。スラッシュコマンドの引数はシェルを通らないので、~ も helper が展開する。"""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    result = resolve(checkout, "#42 --merge --template sub/a.toml --config '~/c d.toml'")
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["merge"]["loop_args"] == [
        "--template",
        str((checkout / "sub" / "a.toml").resolve()),
        "--config",
        str((home / "c d.toml").resolve()),
    ]


# 複数 Issue から一方を黙って選び、別 Issue の作業を始めない。
@pytest.mark.parametrize(
    "argument",
    [
        "#41 #42 --merge",
    ],
)
def test_rejects_malformed_arguments_before_looking_up_issue(
    checkout: Path, gh_stub: Path, argument: str
) -> None:
    before = subprocess.check_output(["git", "status", "--porcelain"], cwd=checkout)
    result = resolve(checkout, argument)
    assert_rejected(result)
    assert not gh_stub.exists()
    assert unchanged(checkout, before)


@pytest.mark.parametrize(
    ("argument", "implement"),
    [
        ("#42 --implement codex", "codex"),
        ("#42 --implement self", "self"),
    ],
)
def test_implement_is_returned_without_changing_git(
    checkout: Path, gh_stub: Path, argument: str, implement: str
) -> None:
    before = subprocess.check_output(["git", "status", "--porcelain"], cwd=checkout)
    result = resolve(checkout, argument)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["implement"] == implement
    assert payload["number"] == 42
    assert subprocess.check_output(["git", "status", "--porcelain"], cwd=checkout) == before


# 二重指定から一方を黙って選び、意図しない担当を起動しない。
@pytest.mark.parametrize(
    "argument",
    [
        "#42 --implement a --implement b",
    ],
)
def test_rejects_malformed_implement_before_looking_up_issue(
    checkout: Path, gh_stub: Path, argument: str
) -> None:
    result = resolve(checkout, argument)
    assert_rejected(result)
    assert not gh_stub.exists()


@pytest.mark.parametrize(
    "origin",
    [
        "https://gitlab.com/usaturn/create-reso-world.git",
    ],
)
def test_number_with_unusable_origin_stops(checkout: Path, gh_stub: Path, origin: str) -> None:
    subprocess.run(["git", "remote", "set-url", "origin", origin], cwd=checkout, check=True)
    result = resolve(checkout, "#42")
    assert_rejected(result)
    assert not gh_stub.exists()


@pytest.mark.parametrize(
    "origin",
    [
        "https://user:s3cr3t-token@github.com/usaturn/create-reso-world.git",
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


@pytest.mark.parametrize(
    ("state", "number", "url"),
    [
        ("CLOSED", 42, None),
        ("OPEN", 99, None),
        ("OPEN", 42, "https://github.com/usaturn/resoloop/issues/42"),
        ("OPEN", 42, "https://github.com.evil.test/usaturn/create-reso-world/issues/42"),
    ],
)
def test_rejects_mismatched_or_closed_response(
    checkout: Path, gh_stub: Path, monkeypatch: pytest.MonkeyPatch, state: str, number: int, url: str | None
) -> None:
    set_response(monkeypatch, "usaturn/create-reso-world", state=state, number=number, url=url)
    assert_rejected(resolve(checkout, "#42"))


def test_reports_gh_failure_without_trying_another_repository(
    checkout: Path, gh_stub: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GH_FAIL", "1")
    result = resolve(checkout, "#42")
    assert_rejected(result)
    assert "404" in result.stderr


@pytest.mark.parametrize(
    ("argument", "implement", "merge"),
    [
        # ループの --assign implement= はレビュー修正の担当で、Plan の Task の担当にはしない
        ("#42 --merge --assign implement=self", None, {"loop_args": ["--assign", "implement=self"]}),
    ],
)
def test_implement_is_returned_separately_from_loop_args(
    checkout: Path, gh_stub: Path, argument: str, implement: str | None, merge: dict[str, list[str]]
) -> None:
    result = resolve(checkout, argument)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["implement"] == implement
    assert payload["merge"] == merge
