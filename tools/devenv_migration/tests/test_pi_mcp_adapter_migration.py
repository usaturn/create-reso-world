"""組み込み MCP への移行で起きた読み込み・事後確認・探索先の不具合を固定する。"""

from __future__ import annotations

import importlib.util
import json
import os
import stat
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
INSTALL_SCRIPT = ROOT / ".devcontainer/install_beforehand.bash"
AGENT_DIR_KINDS = ("unset", "empty", "custom", "tilde")
MANIFEST_NAMES = ("package.json", "package-lock.json")

# 実 pi のネットワーク・npm 操作だけを置き換える。設定とマニフェストは実ファイルを使う。
FAKE_PI = """\
#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

root = Path(os.environ["FAKE_ROOT"])
with (root / "calls").open("a") as audit:
    audit.write(repr(sys.argv[1:]) + "\\n")
agent = Path(os.environ["FAKE_AGENT_DIR"])
settings = agent / "settings.json"
removed = root / "removed"
data = json.loads(settings.read_text(encoding="utf-8-sig"))
packages = data.get("packages", [])
if sys.argv[1:] == ["list"]:
    if removed.exists() and os.environ.get("FAKE_FAIL_RELIST") == "1":
        print("injected pi list failure", file=sys.stderr)
        sys.exit(7)
    print("\\n".join(packages))
    sys.exit(0)
if sys.argv[1:] == ["remove", "npm:pi-mcp-adapter"]:
    removed.touch()
    registered = "npm:pi-mcp-adapter" in packages
    if os.environ.get("FAKE_KEEP_MANIFEST") != "1":
        for name in ("package.json", "package-lock.json"):
            manifest = agent / "npm" / name
            if manifest.exists():
                manifest.write_text("{}\\n")
    if os.environ.get("FAKE_KEEP_REGISTRATION") == "1":
        sys.exit(1)
    data["packages"] = [entry for entry in packages if entry != "npm:pi-mcp-adapter"]
    settings.write_text(json.dumps(data))
    sys.exit(0 if registered else 1)
print("unexpected pi arguments: " + repr(sys.argv[1:]), file=sys.stderr)
sys.exit(99)
"""


@dataclass(frozen=True)
class MigrationHarness:
    root: Path
    home: Path
    agent_dir: Path
    agent_setting: str | None

    @property
    def settings(self) -> Path:
        return self.agent_dir / "settings.json"

    def seed_settings(self, *, registered: bool = False, encoding: str = "utf-8") -> None:
        self.agent_dir.mkdir(parents=True, exist_ok=True)
        packages = ["keep-package"]
        if registered:
            packages.append("npm:pi-mcp-adapter")
        self.settings.write_text(
            json.dumps(
                {
                    "packages": packages,
                    "extensions": ["-builtin:mcp", "keep-local", "-builtin:mcp"],
                    "theme": "dark",
                }
            ),
            encoding=encoding,
        )
        self.settings.chmod(0o600)

    def seed_manifest(self, name: str) -> Path:
        manifest = self.agent_dir / "npm" / name
        manifest.parent.mkdir(parents=True, exist_ok=True)
        content = (
            '{"dependencies":{"pi-mcp-adapter":"5.0.0"}}'
            if name == "package.json"
            else '{"packages":{"node_modules/pi-mcp-adapter":{"version":"5.0.0"}}}'
        )
        manifest.write_text(content)
        return manifest

    def prepare(self, *, entry: str = "migration") -> Path:
        text = INSTALL_SCRIPT.read_text()
        if entry == "migration":
            start = text.index("remove_pi_mcp_adapter() {\n")
            end = text.index("\nremove_pi_mcp_adapter\n", start)
            body = text[start:end] + "\nremove_pi_mcp_adapter\n"
        else:
            start = text.index('step "Installing pi"\n')
            end = text.index('step "Replacing npm:pi-subagents', start)
            body = text[start:end]
        fragment = self.root / "fragment.bash"
        fragment.write_text('step() { :; }\nfail() { echo "$1" >&2; exit 1; }\n'
                            'ensure_user_writable_dir() { return 0; }\n' + body)
        return fragment

    def run(self, *, entry: str = "migration", **flags: str) -> subprocess.CompletedProcess[str]:
        fragment = self.prepare(entry=entry)
        env = dict(os.environ)
        env.pop("PI_CODING_AGENT_DIR", None)
        if self.agent_setting is not None:
            env["PI_CODING_AGENT_DIR"] = self.agent_setting
        env.update(
            HOME=str(self.home),
            WORKSPACE_ROOT=str(ROOT),
            PATH=f"{self.root / 'bin'}:{os.environ['PATH']}",
            FAKE_ROOT=str(self.root),
            FAKE_AGENT_DIR=str(self.agent_dir),
            FAKE_FAIL_RELIST="0",
            FAKE_KEEP_MANIFEST="0",
            FAKE_KEEP_REGISTRATION="0",
        )
        env.update(flags)
        return subprocess.run(["bash", str(fragment)], cwd=ROOT, env=env, text=True, capture_output=True, timeout=15)


def _harness(tmp_path: Path, kind: str = "unset") -> MigrationHarness:
    home = tmp_path / "home"
    home.mkdir()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake = bin_dir / "pi"
    fake.write_text(FAKE_PI)
    fake.chmod(0o755)
    if kind == "unset":
        agent_dir, setting = home / ".pi/agent", None
    elif kind == "empty":
        agent_dir, setting = home / ".pi/agent", ""
    elif kind == "custom":
        agent_dir = tmp_path / "custom agent"
        setting = str(agent_dir)
    elif kind == "tilde":
        agent_dir, setting = home / "custom-agent", "~/custom-agent"
    else:
        raise ValueError(kind)
    return MigrationHarness(tmp_path, home, agent_dir, setting)


@pytest.mark.parametrize("encoding", ["utf-8", "utf-8-sig"])
def test_cleanup_accepts_bom_and_preserves_other_settings(tmp_path: Path, encoding: str) -> None:
    # F1: utf-8 読み込みへ戻すと BOM 付きケースだけが失敗する。
    harness = _harness(tmp_path)
    harness.seed_settings(encoding=encoding)

    result = harness.run()

    assert result.returncode == 0, result.stderr
    assert json.loads(harness.settings.read_text()) == {
        "packages": ["keep-package"],
        "extensions": ["keep-local"],
        "theme": "dark",
    }
    assert harness.settings.stat().st_mode & 0o777 == 0o600
    assert list(harness.agent_dir.glob(".settings-*.tmp")) == []
    before = harness.settings.read_bytes()
    again = harness.run()
    assert again.returncode == 0, again.stderr
    assert harness.settings.read_bytes() == before


def test_relist_failure_stops_before_settings_cleanup(tmp_path: Path) -> None:
    # F2: pi list の非ゼロを grep の不一致と混同すると成功扱いになる。
    harness = _harness(tmp_path)
    harness.seed_settings(registered=True)
    manifest = harness.seed_manifest("package.json")
    before = harness.settings.read_bytes()

    result = harness.run(FAKE_FAIL_RELIST="1", FAKE_KEEP_REGISTRATION="1")

    assert result.returncode != 0
    assert "pi list" in result.stderr
    assert "pi-mcp-adapter" not in manifest.read_text()
    assert harness.settings.read_bytes() == before


@pytest.mark.parametrize("kind", AGENT_DIR_KINDS)
@pytest.mark.parametrize("manifest_name", MANIFEST_NAMES)
def test_manifest_only_removal_uses_selected_agent_dir(tmp_path: Path, kind: str, manifest_name: str) -> None:
    # F3: 固定 HOME を探索すると custom / ~/ の manifest-only 残存を見逃す。
    harness = _harness(tmp_path, kind)
    harness.seed_settings()
    manifest = harness.seed_manifest(manifest_name)

    result = harness.run()

    assert result.returncode == 0, result.stderr
    assert "pi-mcp-adapter" not in manifest.read_text()
    assert json.loads(harness.settings.read_text())["extensions"] == ["keep-local"]


@pytest.mark.parametrize("kind", AGENT_DIR_KINDS)
@pytest.mark.parametrize("manifest_name", MANIFEST_NAMES)
def test_manifest_left_after_removal_is_rejected(tmp_path: Path, kind: str, manifest_name: str) -> None:
    # F3: 事後検査が別ディレクトリを見ると残存した manifest を成功扱いする。
    harness = _harness(tmp_path, kind)
    harness.seed_settings(registered=True)
    harness.seed_manifest(manifest_name)

    result = harness.run(FAKE_KEEP_MANIFEST="1")

    assert result.returncode != 0
    assert str(harness.agent_dir / "npm") in result.stderr
    assert json.loads(harness.settings.read_text())["extensions"] == [
        "-builtin:mcp",
        "keep-local",
        "-builtin:mcp",
    ]


@pytest.mark.parametrize("kind", AGENT_DIR_KINDS)
def test_successful_removal_preserves_unrelated_settings(tmp_path: Path, kind: str) -> None:
    harness = _harness(tmp_path, kind)
    harness.seed_settings(registered=True)
    manifests = [harness.seed_manifest(name) for name in MANIFEST_NAMES]

    result = harness.run()

    assert result.returncode == 0, result.stderr
    assert all("pi-mcp-adapter" not in manifest.read_text() for manifest in manifests)
    assert json.loads(harness.settings.read_text()) == {
        "packages": ["keep-package"],
        "extensions": ["keep-local"],
        "theme": "dark",
    }
    assert harness.settings.stat().st_mode & 0o777 == 0o600


def _snapshot(root: Path) -> dict:
    # Break: rejecting after pi remove or following a shared link changes other state.
    state = {}
    for path in sorted(root.rglob("*")):
        info = path.lstat()
        content = os.readlink(path) if path.is_symlink() else path.read_bytes() if path.is_file() else None
        state[str(path.relative_to(root))] = (stat.S_IFMT(info.st_mode), stat.S_IMODE(info.st_mode),
                                             info.st_nlink, content)
    return state


def _invalid_settings(harness: MigrationHarness, invalid: str) -> None:
    if invalid in ("syntax", "object", "extensions", "packages"):
        content = {"syntax": '{"secret":"SYNTHETIC_SECRET", broken', "object": "[]",
                   "extensions": '{"extensions":{}}', "packages": '{"packages":{}}'}[invalid]
        harness.settings.write_text(content)
        return
    shared = harness.root / "shared-settings"
    harness.settings.rename(shared)
    if invalid == "symlink": harness.settings.symlink_to(shared)
    elif invalid == "dangling": harness.settings.symlink_to(harness.root / "missing-settings")
    elif invalid == "hardlink": os.link(shared, harness.settings)
    elif invalid == "directory": harness.settings.mkdir()
    elif invalid == "fifo": os.mkfifo(harness.settings)
    else: raise ValueError(invalid)


@pytest.mark.parametrize("registered", [False, True])
@pytest.mark.parametrize("invalid", ["symlink", "dangling", "hardlink", "directory", "fifo",
                                    "syntax", "object", "extensions", "packages"])
def test_invalid_settings_rejects_before_any_managed_change(tmp_path: Path, invalid: str, registered: bool) -> None:
    # Removing preflight, weakening lstat/nlink, or validating only after pi remove must fail.
    h = _harness(tmp_path)
    h.seed_settings(registered=registered)
    for name in MANIFEST_NAMES:
        h.seed_manifest(name)
    _invalid_settings(h, invalid)
    h.prepare()
    before = _snapshot(tmp_path)
    result = h.run()
    assert result.returncode != 0
    assert "settings.json" in result.stderr
    assert "SYNTHETIC_SECRET" not in result.stdout + result.stderr
    assert _snapshot(tmp_path) == before


@pytest.mark.parametrize("invalid", ["symlink", "dangling", "hardlink", "syntax"])
def test_pi_installation_preflight_precedes_external_mutations(tmp_path: Path, invalid: str) -> None:
    # A guard only inside the later MCP function misses earlier pi extension installation.
    h = _harness(tmp_path)
    h.seed_settings(registered=True)
    _invalid_settings(h, invalid)
    npm = tmp_path / "bin/npm"
    npm.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$FAKE_ROOT/npm-calls"\n')
    npm.chmod(0o755)
    h.prepare(entry="install")
    before = _snapshot(tmp_path)
    result = h.run(entry="install")
    assert result.returncode != 0
    assert "settings.json" in result.stderr
    assert _snapshot(tmp_path) == before


@pytest.mark.parametrize("failure", ["fsync", "replace"])
def test_settings_io_failure_leaves_no_partial_or_staged_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                                              failure: str) -> None:
    # An inline temp+replace without finally leaves settings fragments on I/O failure.
    h = _harness(tmp_path)
    h.seed_settings()
    spec = importlib.util.spec_from_file_location("pi_update", ROOT / ".devcontainer/pi-provider-setup.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    before = _snapshot(tmp_path)

    def fail(*args: object) -> None:
        raise OSError("injected settings I/O failure")

    monkeypatch.setattr(module.os, failure, fail)
    with pytest.raises(OSError, match="injected settings I/O failure"):
        module.settings_update(h.agent_dir)
    assert _snapshot(tmp_path) == before


@pytest.mark.parametrize("content", [None, '{}', '{"extensions":["keep-local"],"theme":"dark"}'])
def test_settings_noop_creates_or_changes_nothing(tmp_path: Path, content: str | None) -> None:
    # Missing settings and no -builtin:mcp are no-op, not newly created/rewritten files.
    helper = ROOT / ".devcontainer/pi-provider-setup.py"
    agent = tmp_path / "agent"
    if content is not None:
        agent.mkdir()
        (agent / "settings.json").write_text(content)
    before = _snapshot(tmp_path)
    for mode in ("--settings-check", "--settings-clean"):
        result = subprocess.run(["uv", "run", "--no-project", "python", str(helper), mode, str(agent)],
                                text=True, capture_output=True, timeout=15)
        assert result.returncode == 0, result.stderr
        assert _snapshot(tmp_path) == before
