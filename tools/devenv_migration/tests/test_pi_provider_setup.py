"""Execute provider setup against synthetic state; catch wrong targets and secret exposure."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[3]
SETUPS = {"setup_pi.zsh": "deepinfra", "setup_pi_commandcode_goat.zsh": "commandcode",
          "setup_pi_opencode_go.zsh": "opencode-go"}


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
        pi = self.bin / "pi"
        pi.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$CALL_LOG"\n'
                      'case "$1" in\n--list-models) printf "opencode-go %s 1000\\n" "$2";;\n'
                      'update) [ "$2" = --models ] || exit 99;;\n*) exit 99;;\nesac\n')
        pi.chmod(0o755)

    def run(self, *, directory: str | None = None, source: Path = ROOT,
            api_key: str | None = "SYNTHETIC_NEW_KEY") -> subprocess.CompletedProcess[str]:
        env = {"HOME": str(self.home), "PATH": f"{self.bin}:/usr/bin:/bin",
               "DEEPINFRA_TOKEN": "SYNTHETIC_TOKEN", "CALL_LOG": str(self.root / "calls")}
        if api_key is not None:
            env["OPENCODE_API_KEY"] = api_key
        if directory is not None:
            env["PI_CODING_AGENT_DIR"] = directory
        return subprocess.run([
            "bwrap", "--die-with-parent", "--unshare-net", "--unshare-pid",
            "--ro-bind", "/", "/", "--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp",
            "--bind", str(self.root), str(self.root), "--ro-bind", str(source), str(source),
            "--chdir", str(self.cwd), "--", "zsh", str(source / "scripts" / self.script),
        ], env=env, text=True, capture_output=True, timeout=20, umask=0o022)


@pytest.mark.parametrize("script", SETUPS)
@pytest.mark.parametrize("directory", [None, "", "absolute", "relative agent", "~", "~/.pi/agent"])
def test_setup_targets_the_same_agent_directory_as_pi(tmp_path: Path, script: str, directory: str | None) -> None:
    # Break: quoted ~/ written literally, or relative paths resolved after a cwd change.
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


@pytest.mark.parametrize("script", SETUPS)
@pytest.mark.parametrize("encoding", ["utf-8", "utf-8-sig"])
def test_update_preserves_other_providers_permissions_and_bom_input(tmp_path: Path, script: str, encoding: str) -> None:
    # Break: plain UTF-8 reads reject BOM; write_text(tmp)+replace broadens private data.
    h = Harness(tmp_path, script)
    before_models = h.models.read_bytes()
    h.models.write_text(before_models.decode(), encoding=encoding)
    h.auth.write_text(h.auth.read_text(), encoding=encoding)
    result = h.run()
    assert result.returncode == 0, result.stdout + result.stderr
    models = json.loads(h.models.read_text(encoding="utf-8-sig"))["providers"]
    assert models["keep"] == h.other
    provider = SETUPS[script]
    assert models[provider] == json.loads((ROOT / ".devcontainer/pi-models.json").read_text())["providers"][provider]
    assert stat.S_IMODE(h.models.stat().st_mode) == 0o600
    assert json.loads(h.auth.read_text(encoding="utf-8-sig"))["keep"]["key"] == "SYNTHETIC_AUTH"
    assert stat.S_IMODE(h.auth.stat().st_mode) == 0o600
    for backup in h.agent.glob("models.json.bak.*"):
        assert stat.S_IMODE(backup.stat().st_mode) == 0o600
        assert json.loads(backup.read_text(encoding="utf-8-sig"))["providers"]["keep"] == h.other
    first_models, first_auth = h.models.read_bytes(), h.auth.read_bytes()
    backups = {p.name: p.read_bytes() for p in h.agent.glob("models.json.bak.*")}
    again = h.run()
    assert again.returncode == 0, again.stdout + again.stderr
    assert (h.models.read_bytes(), h.auth.read_bytes()) == (first_models, first_auth)
    assert {p.name: p.read_bytes() for p in h.agent.glob("models.json.bak.*")} == backups
    assert not list(h.agent.glob(".*.tmp"))


@pytest.mark.parametrize("script", SETUPS)
def test_new_models_are_private_even_under_public_umask(tmp_path: Path, script: str) -> None:
    h = Harness(tmp_path, script)
    h.models.unlink()
    result = h.run()
    assert result.returncode == 0, result.stdout + result.stderr
    assert stat.S_IMODE(h.models.stat().st_mode) == 0o600


@pytest.mark.parametrize("script", SETUPS)
@pytest.mark.parametrize("invalid", ["syntax", "object", "providers", "symlink", "dangling", "hardlink", "directory", "fifo"])
def test_rejected_models_change_no_managed_state(tmp_path: Path, script: str, invalid: str) -> None:
    # Break: a guard after auth/backup/mkdir or pi refresh leaves unrelated state changed.
    h = Harness(tmp_path, script)
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


@pytest.mark.parametrize("invalid", ["syntax", "object", "symlink", "dangling", "hardlink", "directory", "fifo"])
def test_rejected_auth_changes_neither_models_nor_other_state(tmp_path: Path, invalid: str) -> None:
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


@pytest.mark.parametrize("script", SETUPS)
@pytest.mark.parametrize("content", ["{broken", "[]", '{"providers": []}', '{"providers": {}}'])
def test_invalid_source_is_rejected_before_any_side_effect(tmp_path: Path, script: str, content: str) -> None:
    h = Harness(tmp_path, script)
    repo = tmp_path / "source"
    (repo / "scripts").mkdir(parents=True)
    (repo / ".devcontainer").mkdir()
    shutil.copyfile(ROOT / "scripts" / script, repo / "scripts" / script)
    shutil.copyfile(ROOT / ".devcontainer/pi-provider-setup.py", repo / ".devcontainer/pi-provider-setup.py")
    for launcher in ("pigo", "pigod", "piccg", "piccd"):
        shutil.copyfile(ROOT / ".devcontainer" / launcher, repo / ".devcontainer" / launcher)
    (repo / ".devcontainer/pi-models.json").write_text(content)
    before = snapshot(tmp_path)
    result = h.run(source=repo)
    assert result.returncode != 0
    assert "pi-models.json" in result.stderr
    assert snapshot(tmp_path) == before


def test_missing_opencode_key_is_rejected_before_models_change(tmp_path: Path) -> None:
    h = Harness(tmp_path, "setup_pi_opencode_go.zsh")
    before = snapshot(tmp_path)
    result = h.run(api_key=None)
    assert result.returncode != 0
    assert "API key" in result.stderr
    assert snapshot(tmp_path) == before


def test_existing_opencode_key_is_preserved_without_environment_key(tmp_path: Path) -> None:
    h = Harness(tmp_path, "setup_pi_opencode_go.zsh")
    auth = json.loads(h.auth.read_text())
    auth["opencode-go"] = {"type": "api_key", "key": "SYNTHETIC_SAVED_KEY"}
    h.auth.write_text(json.dumps(auth))
    before = h.auth.read_bytes()
    result = h.run(api_key=None)
    assert result.returncode == 0, result.stdout + result.stderr
    assert h.auth.read_bytes() == before
    assert "SYNTHETIC_SAVED_KEY" not in result.stdout + result.stderr


@pytest.mark.parametrize("script", SETUPS)
def test_existing_fixed_name_tmp_and_its_shared_target_are_untouched(tmp_path: Path, script: str) -> None:
    h = Harness(tmp_path, script)
    shared = h.home / "user-data"
    shared.write_text("do not overwrite")
    temporary = h.agent / "models.json.tmp"
    temporary.symlink_to(shared)
    before = (shared.read_bytes(), shared.stat().st_mode, os.readlink(temporary))
    result = h.run()
    assert result.returncode == 0, result.stdout + result.stderr
    assert (shared.read_bytes(), shared.stat().st_mode, os.readlink(temporary)) == before


@pytest.mark.parametrize("failure", ["fsync", "replace-model", "replace-auth"])
def test_io_failure_never_truncates_files_and_cleans_unused_staging(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                                                   failure: str) -> None:
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
