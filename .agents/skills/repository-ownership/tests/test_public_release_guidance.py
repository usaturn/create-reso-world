from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
CLAUDE_SKILL = REPO_ROOT / ".claude/skills/version-export/SKILL.md"
AGENTS_SKILL_DIR = REPO_ROOT / ".agents/skills/version-export"
PI_SETTINGS = REPO_ROOT / ".pi/settings.json"
PUBLIC_REPO = "usaturn/maatlog"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def bash_blocks(content: str) -> list[str]:
    return re.findall(r"```bash\n(.*?)\n?```", content, re.DOTALL)


def extract_block(skill_text: str, marker: str) -> str:
    """Extract the fenced bash block whose first line is the marker comment."""
    pattern = re.compile(r"```bash\n(" + re.escape(marker) + r"\n.*?)\n```", re.DOTALL)
    match = pattern.search(skill_text)
    assert match is not None, f"{marker!r} bash block not found in skill"
    return match.group(1) + "\n"


def _git(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-c", "user.email=test@example.com", "-c", "user.name=test", *args],
        cwd=cwd,
        check=check,
        text=True,
        capture_output=True,
    )


def build_public_clone(tmp_path: Path) -> Path:
    """A parent dir whose public/ is a clone of a local bare remote."""
    seed = tmp_path / "seed"
    seed.mkdir()
    _git(seed, "init", "-b", "main")
    (seed / "pyproject.toml").write_text('[project]\nname = "maatlog"\nversion = "1.0.0"\n', encoding="utf-8")
    _git(seed, "add", "pyproject.toml")
    _git(seed, "commit", "-m", "init public")
    remote = tmp_path / "public-remote.git"
    _git(seed, "init", "--bare", str(remote))
    _git(seed, "remote", "add", "origin", str(remote))
    _git(seed, "push", "-u", "origin", "main")

    parent = tmp_path / "parent"
    parent.mkdir()
    subprocess.run(
        ["git", "clone", str(remote), str(parent / "public")],
        check=True,
        text=True,
        capture_output=True,
    )
    return parent


def run_guard(parent: Path, snippet: str, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", "-c", f"set -uo pipefail\n{snippet}"],
        cwd=parent,
        env={**os.environ, **env},
        text=True,
        capture_output=True,
        check=False,
    )


def test_release_procedure_order() -> None:
    """The active procedure is: public bump → public PR → full → CI gate →
    merge SHA → tag → GitHub Release → PyPI, in that order."""
    content = read(CLAUDE_SKILL)
    tokens = [
        "バージョン bump",
        "verify.sh full",
        "gh pr create --repo usaturn/maatlog",
        "full/minimum/latest",
        "secret scan",
        "merge SHA",
        "git -C public tag -a",
        "gh release create",
        "PyPI",
    ]
    pos = -1
    for token in tokens:
        nxt = content.find(token, pos + 1)
        assert nxt > pos, f"{token!r} missing or out of order"
        pos = nxt


def test_no_legacy_export_commands() -> None:
    """The rewritten skill drops public_sync, parent bump/gitlink PRs, and
    blanket staging; every gh call is pinned to the public repository."""
    content = read(CLAUDE_SKILL)
    for forbidden in (
        "tools.public_sync",
        "public_sync status",
        "public_sync export",
        "public_sync import",
        "public_sync ack",
        "git add -A",
        "git add public",
        "--repo usaturn/maatlog-poc",
        "gitlink",
    ):
        assert forbidden not in content, forbidden
    for block in bash_blocks(content):
        assert re.search(r"\back\b", block) is None, block
        assert "--merge" not in block, block
        for line in block.splitlines():
            if re.search(r"\bgh (pr|release|run|api)\b", line):
                assert f"--repo {PUBLIC_REPO}" in line, line


def test_public_ci_gate_uses_public_repo(tmp_path: Path) -> None:
    """A stub gh records every call; the CI gate must query the public repo
    and must never substitute the parent CI waiver for public green."""
    content = read(CLAUDE_SKILL)
    snippet = extract_block(content, "# version-export public CI gate")

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "gh.log"
    stub = bin_dir / "gh"
    stub.write_text(f'#!/bin/sh\nprintf \'%s\\n\' "$*" >> "{log}"\nexit 0\n', encoding="utf-8")
    stub.chmod(0o755)
    env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}", "PR_NUMBER": "12"}
    result = subprocess.run(
        ["bash", "-c", f"set -uo pipefail\n{snippet}"],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    calls = log.read_text(encoding="utf-8").splitlines()
    assert calls, "CI gate must call gh"
    for call in calls:
        assert f"--repo {PUBLIC_REPO}" in call, call
    assert any("checks" in call and "--watch" in call for call in calls)

    # The parent-side CI waiver must not leak into the public release gate.
    for line in content.splitlines():
        if PUBLIC_REPO in line:
            assert "待たなくてよい" not in line, line
            assert "待たない" not in line, line
    assert "green" in content


def test_tag_guard_stops_on_existing_tag(tmp_path: Path) -> None:
    content = read(CLAUDE_SKILL)
    snippet = extract_block(content, "# version-export tag guard")
    parent = build_public_clone(tmp_path)
    sha = _git(parent / "public", "rev-parse", "origin/main").stdout.strip()

    ok = run_guard(parent, snippet, {"VERSION": "9.9.9", "RELEASE_SHA": sha})
    assert ok.returncode == 0, ok.stderr

    remote = tmp_path / "public-remote.git"
    _git(remote, "tag", "v9.9.9", "main")
    blocked = run_guard(parent, snippet, {"VERSION": "9.9.9", "RELEASE_SHA": sha})
    assert blocked.returncode != 0
    assert "already exists" in blocked.stderr


def test_tag_guard_stops_when_main_moved(tmp_path: Path) -> None:
    content = read(CLAUDE_SKILL)
    snippet = extract_block(content, "# version-export tag guard")
    parent = build_public_clone(tmp_path)
    sha = _git(parent / "public", "rev-parse", "origin/main").stdout.strip()

    # Advance public main after the merge SHA was recorded.
    seed = tmp_path / "seed"
    (seed / "pyproject.toml").write_text('[project]\nname = "maatlog"\nversion = "1.0.1"\n', encoding="utf-8")
    _git(seed, "add", "pyproject.toml")
    _git(seed, "commit", "-m", "move main")
    _git(seed, "push", "origin", "main")

    blocked = run_guard(parent, snippet, {"VERSION": "9.9.9", "RELEASE_SHA": sha})
    assert blocked.returncode != 0
    assert "moved" in blocked.stderr


def test_agents_version_export_is_symlink_to_claude_skill() -> None:
    assert CLAUDE_SKILL.is_file()
    assert AGENTS_SKILL_DIR.is_symlink()
    assert AGENTS_SKILL_DIR.resolve() == CLAUDE_SKILL.parent.resolve()


def test_pi_settings_still_resolve_version_export() -> None:
    content = read(PI_SETTINGS)
    assert ".claude/skills/version-export" in content
    assert CLAUDE_SKILL.is_file()
