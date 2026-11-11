"""Execute provider setup against synthetic state; catch wrong targets and secret exposure."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[3]
SETUPS = {"setup_pi.zsh": "deepinfra", "setup_pi_commandcode_goat.zsh": "commandcode",
          "setup_pi_opencode_go.zsh": "opencode-go", "setup_pi_alibaba.zsh": "alibaba"}


def snapshot(root: Path) -> dict:
    """Include all managed files, backups, links, directories and external-call audit."""
    result = {}
    for path in sorted(root.rglob("*")):
        info = path.lstat()
        kind = stat.S_IFMT(info.st_mode)
        content = os.readlink(path) if path.is_symlink() else path.read_bytes() if path.is_file() else None
        result[str(path.relative_to(root))] = (kind, stat.S_IMODE(info.st_mode), info.st_nlink, content)
    return result


class Harness:
    def __init__(self, tmp: Path, script: str):
        self.root, self.script = tmp, script
        self.home, self.cwd, self.bin = (tmp / p for p in ("home", "cwd", "bin"))
        for path in (self.home, self.cwd, self.bin):
            path.mkdir()
        self.agent = self.home / ".pi/agent"
        self.agent.mkdir(parents=True)
        self.models = self.agent / "models.json"
        self.auth = self.agent / "auth.json"
        self.other = {"apiKey": "SYNTHETIC_OTHER_KEY", "models": []}
        self.models.write_text(json.dumps({"providers": {"keep": self.other}}))
        self.models.chmod(0o600)
        self.auth.write_text(json.dumps({"keep": {"type": "api_key", "key": "SYNTHETIC_AUTH"}}))
        self.auth.chmod(0o600)
        provider = SETUPS[script]
        pi = self.bin / "pi"
        # --list-models の 1 列目は、引数の setup が書く provider。環境変数が無ければその provider を出す。
        pi.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$CALL_LOG"\n'
                      'case "$1" in\n--list-models)\n'
                      '  provider="${FAKE_PI_PROVIDER:-' + provider + '}"\n'
                      '  printf "%s %s 1000\\n" "$provider" "$2";;\n'
                      'update) [ "$2" = --models ] || exit 99;;\n*) exit 99;;\nesac\n')
        pi.chmod(0o755)

    def run(self, *, directory: str | None = None,
            api_key: str | None = "SYNTHETIC_NEW_KEY") -> subprocess.CompletedProcess[str]:
        env = {"HOME": str(self.home), "PATH": f"{self.bin}:/usr/bin:/bin",
               "DEEPINFRA_TOKEN": "SYNTHETIC_TOKEN", "CALL_LOG": str(self.root / "calls"),
               "FAKE_PI_PROVIDER": SETUPS[self.script]}
        if api_key is not None:
            env["OPENCODE_API_KEY"] = api_key
        if directory is not None:
            env["PI_CODING_AGENT_DIR"] = directory
        return subprocess.run([
            "bwrap", "--die-with-parent", "--unshare-net", "--unshare-pid",
            "--ro-bind", "/", "/", "--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp",
            "--bind", str(self.root), str(self.root), "--ro-bind", str(ROOT), str(ROOT),
            "--chdir", str(self.cwd), "--", "zsh", str(ROOT / "scripts" / self.script),
        ], env=env, text=True, capture_output=True, timeout=20, umask=0o022)


@pytest.mark.parametrize("directory", [None, "relative agent", "~", "~/.pi/agent"])
def test_setup_targets_the_same_agent_directory_as_pi(tmp_path: Path, directory: str | None) -> None:
    # Break: quoted ~/ written literally, or relative paths resolved after a cwd change
    # (models.json / auth.json of the wrong directory are written; the three scripts share --agent-dir).
    script = "setup_pi_opencode_go.zsh"
    h = Harness(tmp_path, script)
    supplied = str(h.agent) if directory == "absolute" else directory
    target = h.home if directory == "~" else h.cwd / directory if directory == "relative agent" else h.agent
    result = h.run(directory=supplied)
    assert result.returncode == 0, result.stdout + result.stderr
    assert (target / "models.json").is_file()
    assert not (h.cwd / "~").exists()
    if script == "setup_pi_opencode_go.zsh":
        assert json.loads((target / "auth.json").read_text())["opencode-go"]["key"] == "SYNTHETIC_NEW_KEY"
    assert "SYNTHETIC_NEW_KEY" not in result.stdout + result.stderr


@pytest.mark.parametrize("script", ["setup_pi_opencode_go.zsh", "setup_pi_alibaba.zsh"])
def test_update_preserves_other_providers_and_private_permissions(tmp_path: Path, script: str) -> None:
    # Break: replacing providers drops other providers' keys; write_text(tmp)+replace broadens private data.
    # 防ぐ損害: 新しい setup がほかの provider を消す・退避しないと、データが失われてもエラーにならない。
    # 退避が 0 件だと for は成功するので、更新前の models.json が残っていることを失敗にする。
    encoding = "utf-8"
    h = Harness(tmp_path, script)
    before_models = h.models.read_bytes()
    h.models.write_text(before_models.decode(), encoding=encoding)
    h.auth.write_text(h.auth.read_text(), encoding=encoding)
    pre_update = h.models.read_bytes()
    result = h.run()
    assert result.returncode == 0, result.stdout + result.stderr
    models = json.loads(h.models.read_text(encoding="utf-8-sig"))["providers"]
    assert models["keep"] == h.other
    provider = SETUPS[script]
    assert models[provider] == json.loads((ROOT / ".devcontainer/pi-models.json").read_text())["providers"][provider]
    assert stat.S_IMODE(h.models.stat().st_mode) == 0o600
    if script == "setup_pi_opencode_go.zsh":
        assert json.loads(h.auth.read_text(encoding="utf-8-sig"))["keep"]["key"] == "SYNTHETIC_AUTH"
        assert stat.S_IMODE(h.auth.stat().st_mode) == 0o600
    backups_found = list(h.agent.glob("models.json.bak.*"))
    assert pre_update in {backup.read_bytes() for backup in backups_found}, (
        "退避が無いと、更新前の models.json が失われてもエラーにならない"
    )
    for backup in backups_found:
        assert stat.S_IMODE(backup.stat().st_mode) == 0o600
        assert json.loads(backup.read_text(encoding="utf-8-sig"))["providers"]["keep"] == h.other
    first_models, first_auth = h.models.read_bytes(), h.auth.read_bytes()
    backups = {p.name: p.read_bytes() for p in backups_found}
    again = h.run()
    assert again.returncode == 0, again.stdout + again.stderr
    assert (h.models.read_bytes(), h.auth.read_bytes()) == (first_models, first_auth)
    assert {p.name: p.read_bytes() for p in h.agent.glob("models.json.bak.*")} == backups
    assert not list(h.agent.glob(".*.tmp"))


def test_new_models_are_private_even_under_public_umask(tmp_path: Path) -> None:
    # Break: a new models.json (holding API keys) is created world-readable under umask 022.
    h = Harness(tmp_path, "setup_pi_opencode_go.zsh")
    h.models.unlink()
    result = h.run()
    assert result.returncode == 0, result.stdout + result.stderr
    assert stat.S_IMODE(h.models.stat().st_mode) == 0o600


@pytest.mark.parametrize("invalid", ["syntax", "symlink"])
def test_rejected_models_change_no_managed_state(tmp_path: Path, invalid: str) -> None:
    # Break: a guard after auth/backup/mkdir or pi refresh leaves unrelated state changed,
    # or a symlinked/shared models.json is written through (silently detaches the shared file).
    h = Harness(tmp_path, "setup_pi_opencode_go.zsh")
    if invalid in ("syntax", "object", "providers"):
        h.models.write_text({"syntax": "{broken", "object": "[]", "providers": '{"providers": []}'}[invalid])
    else:
        h.models.unlink()
        shared = h.home / "shared-models"
        shared.write_text('{"providers": {"keep": {"apiKey": "SYNTHETIC_SHARED"}}}')
        shared.chmod(0o600)
        if invalid == "symlink": h.models.symlink_to(shared)
        elif invalid == "dangling": h.models.symlink_to(h.home / "missing")
        elif invalid == "hardlink": os.link(shared, h.models)
        elif invalid == "directory": h.models.mkdir()
        elif invalid == "fifo": os.mkfifo(h.models)
    before = snapshot(tmp_path)
    result = h.run()
    assert result.returncode != 0
    assert "models.json" in result.stderr
    assert "setup complete" not in result.stdout.lower()
    assert "validation: OK" not in result.stdout
    assert snapshot(tmp_path) == before


def test_rejected_auth_changes_neither_models_nor_other_state(tmp_path: Path) -> None:
    # Break: a symlinked auth.json (shared, holds credentials) is replaced, or models.json changes before the guard.
    invalid = "symlink"
    h = Harness(tmp_path, "setup_pi_opencode_go.zsh")
    if invalid in ("syntax", "object"):
        h.auth.write_text("{broken" if invalid == "syntax" else "[]")
    else:
        shared = h.home / "shared-auth"
        h.auth.rename(shared)
        if invalid == "symlink": h.auth.symlink_to(shared)
        elif invalid == "dangling": h.auth.symlink_to(h.home / "missing")
        elif invalid == "hardlink": os.link(shared, h.auth)
        elif invalid == "directory": h.auth.mkdir()
        elif invalid == "fifo": os.mkfifo(h.auth)
    before = snapshot(tmp_path)
    result = h.run()
    assert result.returncode != 0
    assert "auth.json" in result.stderr
    assert snapshot(tmp_path) == before


def test_existing_opencode_key_is_preserved_without_environment_key(tmp_path: Path) -> None:
    # Break: a missing OPENCODE_API_KEY erases the saved key, or the key is printed.
    h = Harness(tmp_path, "setup_pi_opencode_go.zsh")
    auth = json.loads(h.auth.read_text())
    auth["opencode-go"] = {"type": "api_key", "key": "SYNTHETIC_SAVED_KEY"}
    h.auth.write_text(json.dumps(auth))
    before = h.auth.read_bytes()
    result = h.run(api_key=None)
    assert result.returncode == 0, result.stdout + result.stderr
    assert h.auth.read_bytes() == before
    assert "SYNTHETIC_SAVED_KEY" not in result.stdout + result.stderr


def test_existing_fixed_name_tmp_and_its_shared_target_are_untouched(tmp_path: Path) -> None:
    # Break: staging through a fixed models.json.tmp follows a user's symlink and overwrites their file.
    h = Harness(tmp_path, "setup_pi_opencode_go.zsh")
    shared = h.home / "user-data"
    shared.write_text("do not overwrite")
    temporary = h.agent / "models.json.tmp"
    temporary.symlink_to(shared)
    before = (shared.read_bytes(), shared.stat().st_mode, os.readlink(temporary))
    result = h.run()
    assert result.returncode == 0, result.stdout + result.stderr
    assert (shared.read_bytes(), shared.stat().st_mode, os.readlink(temporary)) == before


@pytest.mark.parametrize("failure", ["fsync", "replace-auth"])
def test_io_failure_never_truncates_files_and_cleans_unused_staging(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                                                   failure: str) -> None:
    # Break: an I/O failure mid-update truncates models.json / auth.json (credentials lost) or leaves staging files.
    h = Harness(tmp_path, "setup_pi_opencode_go.zsh")
    spec = importlib.util.spec_from_file_location("provider_setup", ROOT / ".devcontainer/pi-provider-setup.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setenv("OPENCODE_API_KEY", "SYNTHETIC_NEW_KEY")
    before = snapshot(tmp_path)
    auth_before = h.auth.read_bytes()
    replace = os.replace
    calls = 0

    def fail_replace(src: Path, dest: Path) -> None:
        nonlocal calls
        calls += 1
        if calls == (1 if failure == "replace-model" else 2):
            raise OSError("injected replacement failure")
        replace(src, dest)

    def fail_fsync(fd: int) -> None:
        raise OSError("injected fsync failure")

    if failure == "fsync":
        monkeypatch.setattr(module.os, "fsync", fail_fsync)
    else:
        monkeypatch.setattr(module.os, "replace", fail_replace)
    with pytest.raises(OSError, match="injected"):
        module.setup(h.agent, ROOT / ".devcontainer/pi-models.json", "opencode-go")
    assert h.auth.read_bytes() == auth_before
    assert stat.S_IMODE(h.auth.stat().st_mode) == 0o600
    assert not list(h.agent.glob(".*.tmp"))
    backups = list(h.agent.glob("models.json.bak.*"))
    if failure == "fsync":
        assert snapshot(tmp_path) == before
    else:
        assert len(backups) == 1
        assert backups[0].read_bytes() == before["home/.pi/agent/models.json"][3]
        assert stat.S_IMODE(backups[0].stat().st_mode) == 0o600
        models = json.loads(h.models.read_text())["providers"]
        assert models["keep"] == h.other
        assert ("opencode-go" in models) == (failure == "replace-auth")
        assert not (tmp_path / "calls").exists()
        after = snapshot(tmp_path)
        del after[str(backups[0].relative_to(tmp_path))]
        if failure == "replace-auth":
            after["home/.pi/agent/models.json"] = before["home/.pi/agent/models.json"]
        assert after == before


def isolated_command(root: Path, command: list[str]) -> list[str]:
    """Run with only `root` writable, so a broken resolver cannot touch a real HOME."""
    return ["bwrap", "--die-with-parent", "--unshare-net", "--unshare-pid",
            "--ro-bind", "/", "/", "--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp",
            "--ro-bind", str(ROOT), str(ROOT), "--bind", str(root), str(root),
            "--chdir", str(root), "--", *command]


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
    (decoy / "settings.json").write_text("{}")
    return decoy


@pytest.mark.parametrize("kind", ["unset", "tilde", "relative", "symlink-parent"])
def test_agent_dir_matches_the_directory_pi_selects(tmp_path: Path, kind: str) -> None:
    # Break: reinterpreting ~ or following an alias before collapsing .. selects a different directory
    # than native Pi, so models/auth/settings of an unrelated directory get read and written.
    home = tmp_path / "home"
    home.mkdir()
    if kind == "symlink-parent":
        _symlink_parent(tmp_path)
    raw = {"unset": None, "tilde": "~/custom agent", "relative": "relative agent",
           "symlink-parent": "alias/../agent"}[kind]
    env = {**os.environ, "HOME": str(home)}
    env.pop("PI_CODING_AGENT_DIR", None)
    if raw is not None:
        env["PI_CODING_AGENT_DIR"] = raw
    before = snapshot(tmp_path)
    resolved = subprocess.run(
        isolated_command(tmp_path, [sys.executable, str(ROOT / ".devcontainer/pi-provider-setup.py"), "--agent-dir"]),
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=15)
    assert resolved.returncode == 0, resolved.stderr
    assert resolved.stdout.removesuffix("\n") == _native_agent_directory(tmp_path, env)
    assert snapshot(tmp_path) == before


def test_provider_setup_uses_lexical_path_before_validation_or_writes(tmp_path: Path) -> None:
    # Break: raw alias/.. bypasses a real target guard and writes a different auth/models.
    h = Harness(tmp_path, "setup_pi_opencode_go.zsh")
    decoy = _symlink_parent(h.cwd)
    agent = h.cwd / "agent"
    agent.mkdir()
    shutil.copyfile(h.models, agent / "models.json")
    shutil.copyfile(h.auth, agent / "auth.json")
    for path in agent.iterdir():
        path.chmod(0o600)
    decoy_before, default_before = snapshot(decoy), snapshot(h.agent)
    result = h.run(directory="alias/../agent")
    assert result.returncode == 0, result.stdout + result.stderr
    assert snapshot(decoy) == decoy_before
    assert snapshot(h.agent) == default_before
    assert json.loads((agent / "models.json").read_text())["providers"]["keep"] == h.other
    assert json.loads((agent / "auth.json").read_text())["opencode-go"]["key"] == "SYNTHETIC_NEW_KEY"


def test_setup_pins_resolved_directory_for_its_followup_pi_commands(tmp_path: Path) -> None:
    # Break: a later Pi consumer reinterprets a raw relative path after join/chdir and updates another directory.
    h = Harness(tmp_path, "setup_pi_opencode_go.zsh")
    _symlink_parent(h.cwd)
    (h.cwd / "agent").mkdir()
    env = {"HOME": str(h.home), "PATH": f"{h.bin}:/usr/bin:/bin", "PI_CODING_AGENT_DIR": "alias/../agent",
           "DEEPINFRA_TOKEN": "SYNTHETIC_TOKEN", "OPENCODE_API_KEY": "SYNTHETIC_KEY",
           "CALL_LOG": str(tmp_path / "calls")}
    result = subprocess.run(isolated_command(tmp_path, ["zsh", "-c",
        'cd -- "$2"; source "$1"; print -rn -- "PINNED:$PI_CODING_AGENT_DIR"',
        "_", str(ROOT / "scripts/setup_pi_opencode_go.zsh"), str(h.cwd)]),
        cwd=h.cwd, env=env, capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.rsplit("PINNED:", 1)[-1] == str(h.cwd / "agent")


def test_launcher_pins_same_directory_before_executing_pi(tmp_path: Path) -> None:
    # Break: prechecks normalize a path but the process tree still receives its raw spelling.
    _symlink_parent(tmp_path)
    home = tmp_path / "home"
    config = home / ".pi/agent/extensions/subagent.d/create-reso-world/pigo/config.json"
    config.parent.mkdir(parents=True)
    # ヘルパは起動前に cheap / balanced / max の model がそろっているかを確かめる（#307）。
    # 子 Pi の model の照合の拡張を挙げ、そのファイルも置く（#310）。
    guard = home / ".pi/agent/extensions/subagent.d/pi-superagents-model-guard.ts"
    guard.write_text("// model guard placeholder\n")
    config.write_text(json.dumps({"superagents": {"extensions": [str(guard)],
        "modelTiers": {t: f"test/{t}" for t in ("cheap", "balanced", "max")}}}))
    (tmp_path / "agent").mkdir()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    pi = bin_dir / "pi"
    pi.write_text('#!/bin/sh\nprintf "%s\\n" "$PI_CODING_AGENT_DIR"\n')
    pi.chmod(0o755)
    env = {**os.environ, "HOME": str(home), "PATH": f"{bin_dir}:{os.environ['PATH']}",
           "PI_CODING_AGENT_DIR": "alias/../agent", "PI_SUPERAGENTS_LAUNCHER_DRY_RUN": "0"}
    result = subprocess.run(isolated_command(tmp_path, ["zsh", "-c",
        'source "$1"; pi_superagents_exec pigo', "_", str(ROOT / ".devcontainer/pi-superagents-exec.zsh")]),
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stderr
    assert result.stdout.removesuffix("\n") == str(tmp_path / "agent")
