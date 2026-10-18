"""Keep settings validation and manifest cleanup on Pi's selected POSIX path.

All state is synthetic and test-owned. Named tildes are literal relative paths
in Pi, not another user's home; expanding one used to bypass storage preflight.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import pwd
import shutil
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


def _native_agent_directory(root: Path, env: dict[str, str]) -> str:
    # Independent consumer oracle: do not derive the expectation with our resolver.
    pi = shutil.which("pi")
    assert pi is not None
    package = Path(pi).resolve().parents[2]
    script = """import {pathToFileURL} from 'node:url';
import {join, dirname} from 'node:path';
const load = file => import(pathToFileURL(join(process.argv[1], file)).href);
const {getAgentDir} = await load('dist/config.js');
const {FileSettingsStorage} = await load('dist/core/settings-manager.js');
console.log(dirname(new FileSettingsStorage(process.cwd(), getAgentDir()).globalSettingsPath));
"""
    result = subprocess.run(isolated_command(root, ["node", "--input-type=module", "-e", script, str(package)]),
                            cwd=root, env=env, capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stderr
    return result.stdout.removesuffix("\n")


def _symlink_parent(root: Path) -> Path:
    (root / "real/nested").mkdir(parents=True)
    (root / "alias").symlink_to(root / "real/nested", target_is_directory=True)
    decoy = root / "real/agent"
    decoy.mkdir()
    (decoy / "settings.json").write_text('{"extensions":["-builtin:mcp","decoy"]}')
    return decoy


@pytest.mark.parametrize("roundtrip", [False, True])
@pytest.mark.parametrize("kind", ["unset", "empty", "absolute", "relative", "tilde", "home", "named", "unknown",
                                  "dot-tilde", "dot-tilde-root", "symlink-parent", "trailing-newline"])
def test_settings_check_and_cleanup_use_the_selected_path(tmp_path: Path, kind: str, roundtrip: bool) -> None:
    # Break: reinterpreting ./~/ or following alias before collapsing .. changes
    # an unrelated file instead of the one native Pi's settings storage selects.
    home = tmp_path / "home"
    home.mkdir()
    if kind == "symlink-parent":
        (tmp_path / "real/nested").mkdir(parents=True)
        (tmp_path / "alias").symlink_to(tmp_path / "real/nested", target_is_directory=True)
    raw, agent = {
        "unset": (None, home / ".pi/agent"),
        "empty": ("", home / ".pi/agent"),
        "absolute": (str(tmp_path / "absolute agent"), tmp_path / "absolute agent"),
        "relative": ("relative agent", tmp_path / "relative agent"),
        "tilde": ("~/custom agent", home / "custom agent"),
        "home": ("~", home),
        "named": (_named_tilde(tmp_path), tmp_path / _named_tilde(tmp_path)),
        "unknown": ("~pi-no-such-test-user/agent", tmp_path / "~pi-no-such-test-user/agent"),
        "dot-tilde": ("./~/custom agent", tmp_path / "~/custom agent"),
        "dot-tilde-root": ("./~", tmp_path / "~"),
        "symlink-parent": ("alias/../agent", tmp_path / "agent"),
        "trailing-newline": (str(tmp_path / "agent\n\n"), tmp_path / "agent\n\n"),
    }[kind]
    decoy = {"dot-tilde": home / "custom agent/settings.json", "dot-tilde-root": home / "settings.json",
             "symlink-parent": tmp_path / "real/agent/settings.json",
             "trailing-newline": tmp_path / "agent/settings.json"}.get(kind)
    if decoy is not None:
        decoy.parent.mkdir(parents=True, exist_ok=True)
        decoy.write_text('{"extensions":["-builtin:mcp","not-selected"],"secret":"SYNTHETIC_DECOY"}')
        decoy.chmod(0o640)
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
    resolved = subprocess.run(isolated_command(tmp_path, [sys.executable, str(helper), "--agent-dir"]),
                              cwd=tmp_path, env=env, capture_output=True, text=True, timeout=15)
    assert resolved.returncode == 0, resolved.stderr
    assert _snapshot(tmp_path) == before
    selected = resolved.stdout.removesuffix("\n")
    assert selected == _native_agent_directory(tmp_path, env)
    assert _snapshot(tmp_path) == before
    # Exercise the emitted path as the next CLI input, as the MCP installer does.
    for explicit in ([[], [raw], [selected]] if raw else [[], [selected]]):
        result = subprocess.run(isolated_command(tmp_path, [sys.executable, str(helper), "--settings-check", *explicit]),
                                cwd=tmp_path, env=env, capture_output=True, text=True, timeout=15)
        assert result.returncode == 0, result.stderr
        assert _snapshot(tmp_path) == before
    result = subprocess.run(isolated_command(tmp_path, [sys.executable, str(helper), "--settings-clean",
                                                           *([selected] if roundtrip else [])]), cwd=tmp_path,
                            env=env, capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stderr
    expected = dict(before)
    expected[str(settings.relative_to(tmp_path))] = (
        *before[str(settings.relative_to(tmp_path))][:3],
        (json.dumps({"extensions": ["keep"], "theme": "user-choice"}, indent=2) + "\n").encode(),
    )
    assert _snapshot(tmp_path) == expected


@pytest.mark.parametrize("kind", ["named", "dot-tilde", "symlink-parent", "trailing-newline"])
@pytest.mark.parametrize("entry", ["install", "migration"])
@pytest.mark.parametrize("invalid", ["symlink", "hardlink", "syntax"])
def test_relative_tilde_preflight_preserves_all_managed_state(
    tmp_path: Path, entry: str, invalid: str, kind: str,
) -> None:
    # Break: wrong expansion/normalization checks a decoy before external mutation.
    base = _harness(tmp_path)
    if kind == "symlink-parent":
        _symlink_parent(tmp_path)
    raw = {"named": _named_tilde(tmp_path), "dot-tilde": "./~/selected agent",
           "symlink-parent": "alias/../agent", "trailing-newline": str(tmp_path / "agent\n\n")}[kind]
    if kind == "trailing-newline":
        decoy = tmp_path / "agent"
        decoy.mkdir()
        (decoy / "settings.json").write_text('{}')
    agent = tmp_path / "agent" if kind == "symlink-parent" else tmp_path / raw
    h = MigrationHarness(tmp_path, base.home, agent, raw)
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
    assert _snapshot(tmp_path) == before
    assert result.returncode != 0
    assert "settings.json" in result.stderr
    assert "SYNTHETIC_SECRET" not in result.stdout + result.stderr


@pytest.mark.parametrize("function,package", [
    ("install_pi_extensions", "pi-subagents"),
    ("remove_pi_mcp_adapter", "pi-mcp-adapter"),
    ("remove_pi_distill", "pi-distill"),
    ("remove_pi_lens", "pi-lens"),
])
@pytest.mark.parametrize("kind", ["absolute", "named", "dot-tilde", "symlink-parent", "trailing-newline"])
@pytest.mark.parametrize("keep_manifest", [False, True])
def test_manifest_cleanup_and_postcheck_use_pi_selected_directory(
    tmp_path: Path, function: str, package: str, kind: str, keep_manifest: bool,
) -> None:
    # Break: inspecting the OS-side alias/.. instead of Pi's lexical path misses residue.
    decoy = _symlink_parent(tmp_path) if kind == "symlink-parent" else None
    if kind == "trailing-newline":
        decoy = tmp_path / "agent"
        decoy.mkdir()
        (decoy / "settings.json").write_text('{}')
    decoy_before = _snapshot(decoy) if decoy is not None else None
    raw = {"absolute": str(tmp_path / "custom agent"), "named": _named_tilde(tmp_path),
           "dot-tilde": "./~/selected agent", "symlink-parent": "alias/../agent",
           "trailing-newline": str(tmp_path / "agent\n\n")}[kind]
    agent = tmp_path / "agent" if kind == "symlink-parent" else tmp_path / raw
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
    if decoy is not None:
        assert _snapshot(decoy) == decoy_before
    if keep_manifest:
        assert result.returncode != 0
        assert str(agent / "npm") in result.stderr
        assert package in manifest.read_text()
    else:
        assert result.returncode == 0, result.stdout + result.stderr
        assert json.loads(manifest.read_text()) == {}


@pytest.mark.parametrize("script,field", [
    ("setup_pi.zsh", "models.json"),
    ("setup_pi_commandcode_goat.zsh", "models.json"),
    ("setup_pi_opencode_go.zsh", "models.json"),
    ("setup_pi_opencode_go.zsh", "auth.json"),
])
@pytest.mark.parametrize("invalid", [None, "symlink", "hardlink", "syntax"])
@pytest.mark.parametrize("raw", ["alias/../agent", "agent\n\n"])
def test_provider_setup_uses_lexical_path_before_validation_or_writes(
    tmp_path: Path, script: str, field: str, invalid: str | None, raw: str,
) -> None:
    # Break: raw alias/.. bypasses a real target guard and writes a different auth/models.
    from test_pi_provider_setup import Harness, SETUPS

    h = Harness(tmp_path, script)
    decoy = _symlink_parent(h.cwd)
    agent = h.cwd / ("agent" if raw == "alias/../agent" else raw)
    agent.mkdir()
    shutil.copyfile(h.models, agent / "models.json")
    shutil.copyfile(h.auth, agent / "auth.json")
    for path in agent.iterdir():
        path.chmod(0o600)
    target = agent / field
    if invalid == "syntax":
        target.write_text('{"secret":"SYNTHETIC_SECRET", broken')
    elif invalid is not None:
        shared = h.cwd / "shared-json"
        target.rename(shared)
        if invalid == "symlink":
            target.symlink_to(shared)
        else:
            os.link(shared, target)
    before = _snapshot(tmp_path)
    decoy_before = _snapshot(decoy)
    default_before = _snapshot(h.agent)
    result = h.run(directory=raw)
    if invalid is not None:
        assert _snapshot(tmp_path) == before
        assert result.returncode != 0
        assert field in result.stderr
        assert "SYNTHETIC_SECRET" not in result.stdout + result.stderr
    else:
        assert result.returncode == 0, result.stdout + result.stderr
        assert _snapshot(decoy) == decoy_before
        assert _snapshot(h.agent) == default_before
        providers = json.loads((agent / "models.json").read_text())["providers"]
        assert providers["keep"] == h.other
        assert providers[SETUPS[script]] == json.loads(
            (ROOT / ".devcontainer/pi-models.json").read_text())["providers"][SETUPS[script]]
        if SETUPS[script] == "opencode-go":
            assert json.loads((agent / "auth.json").read_text())["opencode-go"]["key"] == "SYNTHETIC_NEW_KEY"
        assert "SYNTHETIC_NEW_KEY" not in result.stdout + result.stderr


@pytest.mark.parametrize("function,provider", [
    ("pi_openai_codex_require_oauth", "openai-codex"), ("pi_xai_require_oauth", "xai"),
])
@pytest.mark.parametrize("valid", [False, True])
def test_oauth_precheck_reads_pi_selected_auth_not_symlink_parent_decoy(
    tmp_path: Path, function: str, provider: str, valid: bool,
) -> None:
    # Break: a valid decoy accepts invalid real auth, or a missing decoy blocks valid Pi auth.
    decoy = _symlink_parent(tmp_path)
    agent = tmp_path / "agent"
    agent.mkdir()
    oauth = {provider: {"type": "oauth", "access": "synthetic-access",
                        "refresh": "synthetic-refresh", "expires": 4102444800000}}
    (agent / "auth.json").write_text(json.dumps(oauth if valid else {}))
    (decoy / "auth.json").write_text(json.dumps({} if valid else oauth))
    env = {**os.environ, "HOME": str(tmp_path / "home"), "PI_CODING_AGENT_DIR": "alias/../agent"}
    before = _snapshot(tmp_path)
    result = subprocess.run(isolated_command(tmp_path, ["zsh", "-c", 'source "$1"; "$2"', "_",
        str(ROOT / ".devcontainer/pi-superagents-exec.zsh"), function]),
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=15)
    assert result.returncode == (0 if valid else 1), result.stderr
    assert _snapshot(tmp_path) == before
    assert "synthetic-access" not in result.stdout + result.stderr


@pytest.mark.parametrize("launcher", ["piccg", "piccd"])
@pytest.mark.parametrize("valid", [False, True])
def test_commandcode_precheck_reads_pi_selected_models_not_decoy(
    tmp_path: Path, launcher: str, valid: bool,
) -> None:
    # Break: a decoy without/with commandcode wrongly blocks/permits the actual Pi models.
    decoy = _symlink_parent(tmp_path)
    agent = tmp_path / "agent"
    agent.mkdir()
    models = (ROOT / ".devcontainer/pi-models.json").read_text()
    (agent / "models.json").write_text(models if valid else '{"providers":{}}')
    (decoy / "models.json").write_text('{"providers":{}}' if valid else models)
    home = tmp_path / "home"
    config = home / f".pi/agent/extensions/subagent.d/{launcher}/config.json"
    config.parent.mkdir(parents=True)
    config.write_text('{}')
    env = {**os.environ, "HOME": str(home), "PI_CODING_AGENT_DIR": "alias/../agent",
           "COMMANDCODE_API_KEY": "SYNTHETIC_KEY", "PI_SUPERAGENTS_LAUNCHER_DRY_RUN": "1"}
    before = _snapshot(tmp_path)
    result = subprocess.run(isolated_command(tmp_path, ["zsh", str(ROOT / ".devcontainer" / launcher)]),
                            cwd=tmp_path, env=env, capture_output=True, text=True, timeout=15)
    assert result.returncode == (0 if valid else 1), result.stderr
    assert _snapshot(tmp_path) == before


def test_vertex_mount_uses_lexical_directory_before_resolving_auth_link(tmp_path: Path) -> None:
    # Break: realpath before collapsing alias/.. overlays auth in the wrong directory.
    _symlink_parent(tmp_path)
    agent = tmp_path / "agent"
    agent.mkdir()
    shared = tmp_path / "shared-auth"
    shared.write_text('{}')
    (agent / "auth.json").symlink_to(shared)
    home = tmp_path / "home"
    config = home / ".pi/agent/extensions/subagent.d/pigemf/config.json"
    config.parent.mkdir(parents=True)
    config.write_text('{}')
    env = {**os.environ, "HOME": str(home), "PI_CODING_AGENT_DIR": "alias/../agent",
           "PI_SUPERAGENTS_LAUNCHER_DRY_RUN": "1"}
    before = _snapshot(tmp_path)
    result = subprocess.run(isolated_command(tmp_path, ["zsh", str(ROOT / ".devcontainer/pigemf")]),
                            cwd=tmp_path, env=env, capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stderr
    args = result.stdout.splitlines()
    assert args[args.index("--ro-bind-data") + 2] == str(shared)
    assert _snapshot(tmp_path) == before


@pytest.mark.parametrize("script", ["setup_pi.zsh", "setup_pi_commandcode_goat.zsh", "setup_pi_opencode_go.zsh"])
@pytest.mark.parametrize("raw,name", [("alias/../agent", "agent"), ("./~/agent", "~/agent"), ("agent\n\n", "agent\n\n")])
def test_setup_pins_resolved_directory_for_its_followup_pi_commands(
    tmp_path: Path, script: str, raw: str, name: str,
) -> None:
    # Break: a later Pi consumer reinterprets a raw relative/tilde path after join/chdir.
    from test_pi_provider_setup import Harness

    h = Harness(tmp_path, script)
    _symlink_parent(h.cwd)
    (h.cwd / name).mkdir(parents=True)
    env = {"HOME": str(h.home), "PATH": f"{h.bin}:/usr/bin:/bin", "PI_CODING_AGENT_DIR": raw,
           "DEEPINFRA_TOKEN": "SYNTHETIC_TOKEN", "OPENCODE_API_KEY": "SYNTHETIC_KEY",
           "CALL_LOG": str(tmp_path / "calls")}
    result = subprocess.run(isolated_command(tmp_path, ["zsh", "-c",
        'cd -- "$2"; source "$1"; print -rn -- "PINNED:$PI_CODING_AGENT_DIR"',
        "_", str(ROOT / "scripts" / script), str(h.cwd)]),
        cwd=h.cwd, env=env, capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.rsplit("PINNED:", 1)[-1] == str(h.cwd / name)


@pytest.mark.parametrize("raw,name", [("alias/../agent", "agent"), ("./~/agent", "~/agent"), ("agent\n\n", "agent\n\n")])
def test_launcher_pins_same_directory_before_executing_pi(tmp_path: Path, raw: str, name: str) -> None:
    # Break: prechecks normalize a path but the process tree still receives its raw spelling.
    _symlink_parent(tmp_path)
    home = tmp_path / "home"
    config = home / ".pi/agent/extensions/subagent.d/pigo/config.json"
    config.parent.mkdir(parents=True)
    config.write_text('{}')
    (tmp_path / name).mkdir(parents=True)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    pi = bin_dir / "pi"
    pi.write_text('#!/bin/sh\nprintf "%s\\n" "$PI_CODING_AGENT_DIR"\n')
    pi.chmod(0o755)
    env = {**os.environ, "HOME": str(home), "PATH": f"{bin_dir}:{os.environ['PATH']}",
           "PI_CODING_AGENT_DIR": raw, "PI_SUPERAGENTS_LAUNCHER_DRY_RUN": "0"}
    result = subprocess.run(isolated_command(tmp_path, ["zsh", "-c",
        'source "$1"; pi_superagents_exec pigo', "_", str(ROOT / ".devcontainer/pi-superagents-exec.zsh")]),
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stderr
    assert result.stdout.removesuffix("\n") == str(tmp_path / name)


@pytest.mark.parametrize("script,launcher", [
    ("setup_pi_commandcode_goat.zsh", "piccg"), ("setup_pi_commandcode_goat.zsh", "piccd"),
    ("setup_pi_opencode_go.zsh", "pigo"), ("setup_pi_opencode_go.zsh", "pigod"),
])
def test_provider_only_update_keeps_installed_launcher_and_helper_compatible(
    tmp_path: Path, script: str, launcher: str,
) -> None:
    # Break: provider setup installs new launchers but leaves an incompatible old helper API.
    from test_pi_provider_setup import Harness

    h = Harness(tmp_path, script)
    installed = h.home / ".local/bin"
    installed.mkdir(parents=True)
    # Minimal previous public API, deliberately without pi_agent_directory.
    (installed / "pi-superagents-exec.zsh").write_text(
        'pi_superagents_exec() { print -r -- "legacy helper"; }\n')
    shared = h.home / ".pi/agent/extensions/subagent"
    shared.mkdir(parents=True)
    config = h.home / f".pi/agent/extensions/subagent.d/{launcher}/config.json"
    config.parent.mkdir(parents=True)
    config.write_text('{}')
    result = h.run()
    assert result.returncode == 0, result.stdout + result.stderr
    # Replace only the final TUI/API process; use the actual installed launcher/helper/bwrap.
    pi = h.bin / "pi"
    pi.write_text('#!/bin/sh\nprintf "Pi reached\\n"\n')
    pi.chmod(0o755)
    before = _snapshot(tmp_path)
    env = {**os.environ, "HOME": str(h.home), "PATH": f"{h.bin}:{os.environ['PATH']}",
           "PI_CODING_AGENT_DIR": str(h.agent), "COMMANDCODE_API_KEY": "SYNTHETIC_KEY",
           "PI_SUPERAGENTS_LAUNCHER_DRY_RUN": "0"}
    result = subprocess.run(isolated_command(tmp_path, ["zsh", str(installed / launcher)]),
                            cwd=h.cwd, env=env, capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stderr
    assert result.stdout == "Pi reached\n"
    assert _snapshot(tmp_path) == before
