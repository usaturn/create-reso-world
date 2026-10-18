"""Execute the documented fixture: inherited Git targets/config must stay untouched."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[4]
VALIDATION = Path(__file__).resolve().parents[1] / "evals/validation.md"


@pytest.mark.parametrize(
    "attack",
    ["clean", "index", "git-dir", "work-tree", "common-dir", "global-hooks", "home-hooks", "xdg-signing",
     "config-injection", "bash-env", "env"],
)
def test_documented_fixture_isolates_subprocesses_from_host_git_state(
    tmp_path: Path, managed_state: Any, attack: str,
) -> None:
    # Removing the fixture env scrub would target another repository/index,
    # enable host hooks/signing, or source a host shell startup file.
    host = tmp_path / "host"
    home = host / "home"
    home.mkdir(parents=True)
    env = {"PATH": os.environ["PATH"], "HOME": str(home), "XDG_CONFIG_HOME": str(home / "config"),
           "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
           "GIT_AUTHOR_NAME": "Fake", "GIT_AUTHOR_EMAIL": "fake@example.invalid",
           "GIT_COMMITTER_NAME": "Fake", "GIT_COMMITTER_EMAIL": "fake@example.invalid"}
    other = host / "other-repository"
    other.mkdir()

    def git(*args: str) -> None:
        subprocess.run(["git", "-C", str(other), *args], env=env, check=True, capture_output=True)

    git("init", "-q", "-b", "other")
    (other / "owned").write_bytes(b"other repository contents\n")
    git("add", "owned")
    git("commit", "-qm", "other base")
    (other / "staged").write_bytes(b"other staged contents\n")
    git("add", "staged")
    (other / "owned").chmod(0o640)
    (host / "link").symlink_to(other / "owned")
    marker = host / "unexpected-command"
    hooks = host / "hooks"
    hooks.mkdir()
    hook = hooks / "pre-commit"
    hook.write_text(f"#!/bin/sh\nprintf called >> '{marker}'\n")
    hook.chmod(0o700)
    signing = host / "signer"
    signing.write_text(f"#!/bin/sh\nprintf called >> '{marker}'\nexit 1\n")
    signing.chmod(0o700)
    hook_config = f"[core]\n\thooksPath = {hooks}\n"
    sign_config = f"[commit]\n\tgpgSign = true\n[gpg]\n\tprogram = {signing}\n"
    if attack == "index":
        env["GIT_INDEX_FILE"] = str(other / ".git/index")
    elif attack == "git-dir":
        env["GIT_DIR"] = str(other / ".git")
    elif attack == "work-tree":
        env["GIT_WORK_TREE"] = str(other)
    elif attack == "common-dir":
        env["GIT_COMMON_DIR"] = str(other / ".git")
    elif attack == "global-hooks":
        config = host / "global-config"
        config.write_text(hook_config)
        env["GIT_CONFIG_GLOBAL"] = str(config)
    elif attack == "home-hooks":
        (home / ".gitconfig").write_text(hook_config)
        del env["GIT_CONFIG_GLOBAL"]
    elif attack == "xdg-signing":
        config = home / "config/git/config"
        config.parent.mkdir(parents=True)
        config.write_text(sign_config)
        del env["GIT_CONFIG_GLOBAL"]
    elif attack == "config-injection":
        env.update(GIT_CONFIG_COUNT="1", GIT_CONFIG_KEY_0="core.hooksPath", GIT_CONFIG_VALUE_0=str(hooks))
    elif attack in {"bash-env", "env"}:
        startup = host / "startup"
        startup.write_text(f"printf called >> '{marker}'\n")
        env["BASH_ENV" if attack == "bash-env" else "ENV"] = str(startup)
        # A fake command boundary observes the env passed to every fixture child.
        # It delegates all Git behavior to the real executable, without services.
        commands = host / "commands"
        commands.mkdir()
        real_git = shutil.which("git")
        assert real_git is not None
        wrapper = commands / "git"
        wrapper.write_text(
            f"#!{sys.executable}\nimport os, pathlib, sys\n"
            f"if os.environ.get({'BASH_ENV' if attack == 'bash-env' else 'ENV'!r}): "
            f"pathlib.Path({str(marker)!r}).write_text('inherited')\n"
            f"os.execv({real_git!r}, [{real_git!r}, *sys.argv[1:]])\n"
        )
        wrapper.chmod(0o700)
        env["PATH"] = f"{commands}:{env['PATH']}"

    # Extract and execute the complete Python block, not a copied env snippet.
    text = VALIDATION.read_text()
    code = text.split("```python\n", 1)[1].split("\n```", 1)[0]
    script = tmp_path / "cycle-fixture.py"
    script.write_text(code)
    session = tmp_path / "session"
    session.mkdir()
    before = managed_state(host)
    result = subprocess.run(
        [sys.executable, "-B", str(script), str(ROOT), str(session)],
        env=env, capture_output=True, text=True, timeout=30,
    )
    assert managed_state(host) == before, f"host state changed under {attack}: {result.stderr}"
    assert not marker.exists()
    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    assert output["counts"] == {"confirmed": 1, "not_reproduced": 1, "unverified": 1}
    document = json.loads(Path(output["verified"]).read_text())
    assert document["reviewed_head"] == output["head"]
    assert [finding["verdict"] for finding in document["findings"]] == [
        "confirmed", "not_reproduced", "unverified",
    ]
    transcript = json.loads((Path(output["area"]) / "execution.json").read_text())
    failures = [command for command in transcript["commands"] if command["exit_code"]]
    assert len(failures) == 1
    assert "fixture_missing_dependency_154" in failures[0]["stderr"]
    assert not (Path(output["area"]) / "worktree").exists()
