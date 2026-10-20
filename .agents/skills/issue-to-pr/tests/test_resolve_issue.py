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
        "merge": None,
        "implement": None,
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


def unchanged(checkout: Path, before: bytes) -> bool:
    return (
        subprocess.check_output(["git", "status", "--porcelain"], cwd=checkout) == before
        and subprocess.check_output(["git", "for-each-ref"], cwd=checkout) == b""
    )


@pytest.mark.parametrize(
    ("argument", "loop_args"),
    [
        ("#42 --merge", []),
        (
            "#42 --merge --max-cycles 2 --assign inspect=claude-opus,devin-swe --assign implement=self",
            ["--max-cycles", "2", "--assign", "inspect=claude-opus,devin-swe", "--assign", "implement=self"],
        ),
        ("--merge #42 --max-cycles=2", ["--max-cycles", "2"]),
        # ループ用のオプションは --merge より前に書いてもよい
        ("#42 --max-cycles 2 --merge", ["--max-cycles", "2"]),
        # start の argparse と同じく、繰り返しは書いた順のまま渡す（--max-cycles は後の値が効く）
        ("#42 --merge --max-cycles 2 --max-cycles 3", ["--max-cycles", "2", "--max-cycles", "3"]),
        # 範囲は check-options が start と同じ関数で確かめる（test_resolve_then_check_options）
        ("#42 --merge --max-cycles 0", ["--max-cycles", "0"]),
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


def test_unresolvable_home_is_rejected(checkout: Path, gh_stub: Path) -> None:
    result = resolve(checkout, "#42 --merge --config ~nosuchuser-158/x.toml")
    assert_rejected(result)
    assert "Traceback" not in result.stderr
    assert not gh_stub.exists()


# 値はそのまま loop.py check-options・start の引数になるので、形の合わない値は Issue を読む前に止める
@pytest.mark.parametrize(
    "argument",
    [
        "#42 --max-cycles 2",
        "#42 --assign implement=self",
        "#42 --template x.toml",
        "#42 --merge --merge",
        "#42 --merge=yes",
        "#42 --merge --max-cycles",
        "#42 --merge --max-cycles x",
        "#42 --merge --max-cycles -1",
        "#42 --merge --max-cycles=٣",
        "#42 --merge --assign inspect",
        "#42 --merge --assign 'inspect=a;touch injected'",
        "#42 --merge --assign =a",
        "#42 --merge --template",
        "#42 --merge --template=",
        "#42 --merge --template --config x",
        "#42 --merge --config 'a\nb'",
        "#42 --merge --foo",
        "#42 --merge -x",
        "#42 extra --merge",
        "#41 #42 --merge",
        "--merge",
        "#42 --merge --template 'a",
    ],
)
def test_rejects_malformed_arguments_before_looking_up_issue(
    checkout: Path, gh_stub: Path, argument: str
) -> None:
    before = subprocess.check_output(["git", "status", "--porcelain"], cwd=checkout)
    result = resolve(checkout, argument)
    assert_rejected(result)
    assert not gh_stub.exists()
    assert not (checkout / "injected").exists()
    assert unchanged(checkout, before)


# このリポジトリの review-fix-planning とループには判断保留が無く（#156 の D-4）、作ったばかりの PR には
# 再利用するレビューが無い。どちらも黙って外さず、名前を挙げて止める
@pytest.mark.parametrize(
    ("argument", "option"),
    [
        ("#42 --merge --hold-action skip", "--hold-action"),
        ("#42 --hold-action fix", "--hold-action"),
        ("#42 --merge --fresh-review", "--fresh-review"),
        ("#42 --fresh-review", "--fresh-review"),
    ],
)
def test_refused_options_name_the_option(checkout: Path, gh_stub: Path, argument: str, option: str) -> None:
    result = resolve(checkout, argument)
    assert_rejected(result)
    assert option in result.stderr
    # 未知のオプションと区別して、理由付きで止める
    assert "未知のオプション" not in result.stderr
    assert not gh_stub.exists()


@pytest.mark.parametrize(
    ("argument", "implement"),
    [
        ("#42 --implement codex", "codex"),
        ("#42 --implement=codex", "codex"),
        ("#42 --implement self", "self"),
        ("--implement codex #42", "codex"),
        ("#42 --implement pi-deepseek", "pi-deepseek"),
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


# 値はそのまま次の implement_task.py check の引数になるので、agent 名の形
# （tools/agent_runner/models.py の識別子）でない値は Issue を読む前に止める
@pytest.mark.parametrize(
    "argument",
    [
        "#42 --implement",
        "#42 --implement=",
        "#42 --implement --merge",
        "#42 --implement -x",
        "#42 --implement a --implement b",
        "#42 --implement=a --implement=b",
        "#42 --implement 'x;touch injected'",
        "#42 --implement ../x",
        "#42 --implement 推奨案",
    ],
)
def test_rejects_malformed_implement_before_looking_up_issue(
    checkout: Path, gh_stub: Path, argument: str
) -> None:
    result = resolve(checkout, argument)
    assert_rejected(result)
    assert not gh_stub.exists()
    assert not (checkout / "injected").exists()


@pytest.mark.parametrize("argument", ["#42 --foo", "#42 -m", "--dry-run #42"])
def test_rejects_unknown_options(checkout: Path, gh_stub: Path, argument: str) -> None:
    result = resolve(checkout, argument)
    assert_rejected(result)
    assert "未知のオプション" in result.stderr
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


IMPLEMENT_SCRIPT = SCRIPT.parent / "implement_task.py"
IMPLEMENT_TEMPLATE = """
schema_version = 1

[agents.codex]
runtime = "codex"
command = ["fake-codex"]
model = "codex-model"

[roles.implement]
writes = true
deadline_seconds = 60
result_shape = "json"

[workflows.issue.assignments.implement]
agents = ["self"]
"""


@pytest.mark.parametrize(
    ("argument", "expected"),
    [
        ("#42", (0, 0, True)),
        ("#42 --implement codex", (0, 0, False)),
        ("#42 --implement self", (0, 0, True)),
        ("#42 --implement self --merge", (0, 0, True)),
        ("#42 --implement nobody", (0, 2, None)),
        ("#42 --implement", (2, None, None)),
    ],
)
def test_resolve_then_implement_check(
    checkout: Path, gh_stub: Path, tmp_path: Path, argument: str, expected: tuple[int, int | None, bool | None]
) -> None:
    """worktree を作る前の 2 段（resolve_issue.py → implement_task.py check）を、本物の 2 つのスクリプトでつなぐ。

    値は（resolve の終了コード、check の終了コード、check の self）。implement が null なら --implement を付けない。
    """
    template = tmp_path / "agent-runner.toml"
    template.write_text(IMPLEMENT_TEMPLATE, encoding="utf-8")
    resolved = resolve(checkout, argument)
    if resolved.returncode != 0:
        assert (resolved.returncode, None, None) == expected
        return
    implement = json.loads(resolved.stdout)["implement"]
    checked = subprocess.run(
        [
            sys.executable,
            str(IMPLEMENT_SCRIPT),
            "check",
            "--template",
            str(template),
            *(["--implement", implement] if implement is not None else []),
        ],
        cwd=checkout,
        capture_output=True,
        text=True,
        env={**os.environ, "AGENT_RUNNER_CONFIG": str(tmp_path / "no-personal.toml")},
    )
    assert (resolved.returncode, checked.returncode, json.loads(checked.stdout).get("self")) == expected


@pytest.mark.parametrize(
    ("argument", "implement", "merge"),
    [
        ("#42 --implement claude-opus --merge --max-cycles 2", "claude-opus", {"loop_args": ["--max-cycles", "2"]}),
        # --merge の後ろに書いても、--implement はループ用のオプションにならない
        ("#42 --merge --max-cycles 2 --implement codex", "codex", {"loop_args": ["--max-cycles", "2"]}),
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


LOOP_SCRIPT = SCRIPT.parents[2] / "pr-review-fix-loop" / "scripts" / "loop.py"
LOOP_TEMPLATE = """
schema_version = 1

[agents.claude-opus]
runtime = "claude-code"
command = ["fake-claude"]
model = "claude-model"

[agents.devin-swe]
runtime = "devin"
command = ["fake-devin"]
model = "devin-model"

[agents.codex]
runtime = "codex"
command = ["fake-codex"]
model = "codex-model"

[roles.inspect]
writes = false
deadline_seconds = 60
result_shape = "json"

[roles.implement]
writes = true
deadline_seconds = 60
result_shape = "json"

[roles.self-review]
writes = false
deadline_seconds = 60
result_shape = "json"

[roles.fix-check]
writes = false
deadline_seconds = 60
result_shape = "json"

[workflows.review.assignments.inspect]
agents = ["claude-opus", "devin-swe"]

[workflows.fix.assignments.implement]
agents = ["claude-opus"]

[workflows.fix.assignments.self-review]
agents = ["self"]

[workflows.fix.assignments.fix-check]
agents = ["self"]
"""


@pytest.mark.parametrize(
    ("argument", "expected"),
    [
        ("#42 --merge", (0, 0)),
        ("#42 --merge --max-cycles 2 --assign inspect=claude-opus,devin-swe --assign implement=self", (0, 0)),
        ("#42 --max-cycles 2", (2, None)),
        ("#42 --merge --hold-action skip", (2, None)),
        ("#42 --merge --max-cycles 0", (0, 2)),
        ("#42 --merge --assign inspect=nobody", (0, 2)),
        ("#42 --merge --assign inspect=codex", (0, 2)),
        # 利用者の --template は、下で先に渡す一時の雛形より後ろに来るので、利用者の値が効く
        ("#42 --merge --template missing.toml", (0, 2)),
    ],
)
def test_resolve_then_check_options(
    checkout: Path, gh_stub: Path, tmp_path: Path, argument: str, expected: tuple[int, int | None]
) -> None:
    """worktree を作る前の 2 段（resolve_issue.py → loop.py check-options）を、本物の 2 つのスクリプトでつなぐ。

    値は（resolve の終了コード、check-options の終了コード）。loop_args の各要素を 1 つの引数として渡す。
    """
    template = tmp_path / "agent-runner.toml"
    template.write_text(LOOP_TEMPLATE, encoding="utf-8")
    resolved = resolve(checkout, argument)
    if resolved.returncode != 0:
        assert (resolved.returncode, None) == expected
        return
    loop_args = json.loads(resolved.stdout)["merge"]["loop_args"]
    checked = subprocess.run(
        [sys.executable, str(LOOP_SCRIPT), "check-options", "--template", str(template), *loop_args],
        cwd=checkout,
        capture_output=True,
        text=True,
        env={**os.environ, "AGENT_RUNNER_CONFIG": str(tmp_path / "no-personal.toml")},
    )
    assert (resolved.returncode, checked.returncode) == expected, checked.stdout + checked.stderr
    if checked.stdout:
        assert json.loads(checked.stdout)["status"] == ("ok" if checked.returncode == 0 else "error")
