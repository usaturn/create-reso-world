"""Keep settings validation and manifest cleanup on Pi's selected POSIX path.

All state is synthetic and test-owned. Named tildes are literal relative paths
in Pi, not another user's home; expanding one used to bypass storage preflight.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import pwd
import subprocess
import sys

import pytest

from test_pi_mcp_adapter_migration import (
    INSTALL_SCRIPT, ROOT, MigrationHarness, _harness, _invalid_settings, _snapshot, isolated_command,
)


def test_path_probe_isolation_protects_storage_outside_its_fixture(tmp_path: Path) -> None:
    # Break: an old/mutant resolver must not write outside the test-owned fixture.
    # Outer /mnt is writable so only the inner helper's readonly guard can protect it.
    outside = tmp_path / "outside"
    outside.mkdir()
    protected = outside / "sentinel"
    protected.write_bytes(b"host-owned fixture bytes")
    root = tmp_path / "writable fixture"
    root.mkdir()
    before = _snapshot(outside)
    command = isolated_command(root, ["bash", "-c",
        'if printf changed > /mnt/sentinel 2>/dev/null; then exit 83; fi; '
        'printf allowed > "$1/allowed"', "_", str(root)])
    result = subprocess.run(["bwrap", "--die-with-parent", "--dev-bind", "/", "/",
        "--bind", str(outside), "/mnt", "--", *command], cwd=ROOT,
        capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stdout + result.stderr
    assert _snapshot(outside) == before
    assert (root / "allowed").read_text() == "allowed"


def _named_tilde(tmp_path: Path) -> str:
    return f"~{pwd.getpwuid(os.getuid()).pw_name}/{tmp_path.name}"


@pytest.mark.parametrize("kind", ["unset", "empty", "absolute", "relative", "tilde", "home", "named", "unknown"])
def test_settings_check_and_cleanup_use_the_selected_path(tmp_path: Path, kind: str) -> None:
    # Break: expanduser checks another HOME, or only explicit/default arguments are fixed.
    home = tmp_path / "home"
    home.mkdir()
    raw, agent = {
        "unset": (None, home / ".pi/agent"),
        "empty": ("", home / ".pi/agent"),
        "absolute": (str(tmp_path / "absolute agent"), tmp_path / "absolute agent"),
        "relative": ("relative agent", tmp_path / "relative agent"),
        "tilde": ("~/custom agent", home / "custom agent"),
        "home": ("~", home),
        "named": (_named_tilde(tmp_path), tmp_path / _named_tilde(tmp_path)),
        "unknown": ("~pi-no-such-test-user/agent", tmp_path / "~pi-no-such-test-user/agent"),
    }[kind]
    agent.mkdir(parents=True, exist_ok=True)
    settings = agent / "settings.json"
    settings.write_text('{"extensions":["-builtin:mcp","keep"],"theme":"user-choice"}')
    settings.chmod(0o600)
    env = {**os.environ, "HOME": str(home)}
    env.pop("PI_CODING_AGENT_DIR", None)
    if raw is not None:
        env["PI_CODING_AGENT_DIR"] = raw
    helper = ROOT / ".devcontainer/pi-provider-setup.py"
    before = _snapshot(tmp_path)
    # Test both CLI entry paths, not just the resolver's return string.
    for explicit in ([[], [raw]] if raw else [[]]):
        result = subprocess.run(isolated_command(tmp_path, [sys.executable, str(helper), "--settings-check", *explicit]),
                                cwd=tmp_path, env=env, capture_output=True, text=True, timeout=15)
        assert result.returncode == 0, result.stderr
        assert _snapshot(tmp_path) == before
    result = subprocess.run(isolated_command(tmp_path, [sys.executable, str(helper), "--settings-clean"]), cwd=tmp_path,
                            env=env, capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stderr
    expected = dict(before)
    expected[str(settings.relative_to(tmp_path))] = (
        *before[str(settings.relative_to(tmp_path))][:3],
        (json.dumps({"extensions": ["keep"], "theme": "user-choice"}, indent=2) + "\n").encode(),
    )
    assert _snapshot(tmp_path) == expected


@pytest.mark.parametrize("entry", ["install", "migration"])
@pytest.mark.parametrize("invalid", ["symlink", "hardlink", "syntax"])
def test_named_tilde_preflight_preserves_all_managed_state(tmp_path: Path, entry: str, invalid: str) -> None:
    # Break: inspecting ~user as a home permits Pi to mutate the literal path's shared settings.
    base = _harness(tmp_path)
    raw = _named_tilde(tmp_path)
    h = MigrationHarness(tmp_path, base.home, tmp_path / raw, raw)
    h.seed_settings(registered=True)
    for name in ("package.json", "package-lock.json"):
        h.seed_manifest(name)
    _invalid_settings(h, invalid)
    npm = tmp_path / "bin/npm"
    npm.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$FAKE_ROOT/npm-calls"\n')
    npm.chmod(0o755)
    h.prepare(entry=entry)
    before = _snapshot(tmp_path)
    result = h.run(entry=entry, isolate=True)
    assert result.returncode != 0
    assert "settings.json" in result.stderr
    assert "SYNTHETIC_SECRET" not in result.stdout + result.stderr
    assert _snapshot(tmp_path) == before


@pytest.mark.parametrize("function,package", [
    ("install_pi_extensions", "pi-subagents"),
    ("remove_pi_mcp_adapter", "pi-mcp-adapter"),
    ("remove_pi_distill", "pi-distill"),
    ("remove_pi_lens", "pi-lens"),
])
@pytest.mark.parametrize("kind", ["absolute", "named"])
@pytest.mark.parametrize("keep_manifest", [False, True])
def test_manifest_cleanup_and_postcheck_use_pi_selected_directory(
    tmp_path: Path, function: str, package: str, kind: str, keep_manifest: bool,
) -> None:
    # Break: HOME-fixed or ~user-expanded checks miss manifest-only packages/false success.
    raw = str(tmp_path / "custom agent") if kind == "absolute" else _named_tilde(tmp_path)
    agent = tmp_path / raw
    agent.mkdir(parents=True)
    settings = agent / "settings.json"
    settings.write_text('{"extensions":[],"packages":[]}')
    manifest = agent / "npm/package.json"
    manifest.parent.mkdir()
    manifest.write_text(json.dumps({"dependencies": {package: "synthetic-version"}}))
    before_settings = settings.read_bytes()
    fake = tmp_path / "pi"
    fake.write_text(f'#!{sys.executable}\n' + '''import json, os, sys
from pathlib import Path
args = sys.argv[1:]
if args == ['list']:
    print('npm:@teelicht/pi-superagents')
elif args == ['remove', 'npm:' + os.environ['TEST_PACKAGE']]:
    if os.environ['TEST_KEEP'] != '1':
        Path(os.environ['TEST_MANIFEST']).write_text('{}')
    sys.exit(1)  # Pi still cleans a manifest-only package when no registration exists.
elif args != ['install', '--approve', 'npm:@teelicht/pi-superagents']:
    sys.exit(99)
''')
    fake.chmod(0o755)
    text = INSTALL_SCRIPT.read_text()
    start = text.index(function + "() {\n")
    end = text.index("\n" + function + "\n", start)
    fragment = tmp_path / "fragment.bash"
    fragment.write_text(text[start:end] + "\n" + function + "\n")
    env = {**os.environ, "HOME": str(tmp_path / "home"), "WORKSPACE_ROOT": str(ROOT),
           "PI_CODING_AGENT_DIR": raw, "PATH": f"{tmp_path}:{os.environ['PATH']}",
           "TEST_PACKAGE": package, "TEST_MANIFEST": str(manifest), "TEST_KEEP": str(int(keep_manifest))}
    result = subprocess.run(isolated_command(tmp_path, ["bash", str(fragment)]), cwd=tmp_path, env=env,
                            capture_output=True, text=True, timeout=15)
    assert settings.read_bytes() == before_settings
    if keep_manifest:
        assert result.returncode != 0
        assert str(Path(raw) / "npm") in result.stderr
        assert package in manifest.read_text()
    else:
        assert result.returncode == 0, result.stdout + result.stderr
        assert json.loads(manifest.read_text()) == {}
