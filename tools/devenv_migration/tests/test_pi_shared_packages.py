"""Rebuilding either container must not remove packages shared through ~/.pi.

Damage guarded (#162): a rebuild silently removing other repositories' registrations
(context7-pi) or the user's packages/extensions/theme. The install still succeeds, so
the other repositories' Pi notices only later. Execute the actual installer section
twice, replacing only network/package-manager operations and the separately tested
tier setup.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
# Packages this repository's setup registers in the shared ~/.pi.
INSTALLED_PACKAGES = ("npm:@plannotator/pi-extension",)
# This repository no longer installs context7-pi and stops loading it through
# .pi/settings.json (#162). Other repositories sharing ~/.pi still install and
# use it, so a rebuild here must keep their registration.
KEPT_PACKAGE = "npm:@upstash/context7-pi"

FAKE_PI = r'''
import json, os, sys
from pathlib import Path
agent = Path(os.environ["PI_CODING_AGENT_DIR"])
settings = agent / "settings.json"
data = json.loads(settings.read_text())
packages = data["packages"]
args = [arg for arg in sys.argv[1:] if arg not in ("--approve", "--no-approve")]
if args == ["list"]:
    print("\n".join(packages))
elif len(args) == 2 and args[0] in ("install", "remove"):
    command, package = args
    if command == "remove":
        data["packages"] = [entry for entry in packages if entry != package]
        with Path(os.environ["TEST_REMOVALS"]).open("a") as log:
            log.write(package + "\n")
    elif package not in packages:
        packages.append(package)
    settings.write_text(json.dumps(data))
else:
    sys.exit("unexpected pi invocation: " + repr(args))
'''


def test_rebuild_preserves_shared_packages(tmp_path: Path) -> None:
    home = tmp_path / "home"
    agent = home / ".pi/agent"
    agent.mkdir(parents=True)
    settings = agent / "settings.json"
    settings.write_text(json.dumps({
        "packages": ["npm:unrelated-user-package", *INSTALLED_PACKAGES, KEPT_PACKAGE],
        "extensions": ["-builtin:mcp", "user-local-extension"],
        "theme": "user-choice",
    }))
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    pi = bin_dir / "pi"
    pi.write_text(f"#!{sys.executable}\n" + FAKE_PI)
    pi.chmod(0o755)
    for command in ("npm", "zsh"):
        fake = bin_dir / command
        fake.write_text("#!/bin/sh\nexit 0\n")
        fake.chmod(0o755)
    installer = (ROOT / ".devcontainer/install_beforehand.bash").read_text()
    start = installer.index('step "Installing pi"\n')
    end = installer.index('step "Installing the shared skills (herdr / find-skills)"\n', start)
    fragment = tmp_path / "pi-installer.bash"
    fragment.write_text(
        'set -eu\nstep() { :; }\nfail() { printf "%s\\n" "$*" >&2; exit 1; }\n'
        'ensure_user_writable_dir() { mkdir -p "$1"; }\n' + installer[start:end]
    )
    removals = tmp_path / "removals"
    env = {
        **os.environ,
        "HOME": str(home),
        "WORKSPACE_ROOT": str(ROOT),
        "PI_CODING_AGENT_DIR": str(agent),
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
        "TEST_REMOVALS": str(removals),
    }
    for _ in range(2):
        result = subprocess.run(
            ["bash", str(fragment)], cwd=ROOT, env=env,
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        actual = json.loads(settings.read_text())
        for package in INSTALLED_PACKAGES:
            assert actual["packages"].count(package) == 1, package
        assert actual["packages"].count(KEPT_PACKAGE) == 1
        assert "npm:unrelated-user-package" in actual["packages"]
        assert actual["extensions"] == ["-builtin:mcp", "user-local-extension"]
        assert actual["theme"] == "user-choice"
    removed = removals.read_text().splitlines() if removals.exists() else []
    assert not {*INSTALLED_PACKAGES, KEPT_PACKAGE}.intersection(removed), removed
