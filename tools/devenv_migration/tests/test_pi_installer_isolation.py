"""Catch installer-tail execution and enforce test-only filesystem/network isolation.

Run the actual Codex suite with external operations denied, never by executing
an unbounded installer on the host. All payloads and credentials are synthetic.
"""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
HELPER = ROOT / ".devcontainer/tests/pi-launcher-install.bash"
START = 'step "Placing the launchers (fixture)"\n'
END = 'step "Installing the shared skills (herdr / find-skills)"\n'


def _sandbox(tmp_path: Path, command: list[str], *, network: bool = True) -> subprocess.CompletedProcess[str]:
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    env = {**os.environ, "HOME": str(home), "PI_OFFLINE": "1", "PI_CODEX_LIVE_CHECK": "0"}
    return subprocess.run(
        [shutil.which("bwrap") or "bwrap", "--die-with-parent", *(["--unshare-net"] if network else []),
         "--ro-bind", "/", "/", "--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp",
         "--bind", str(tmp_path), str(tmp_path), "--", *command],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=45,
    )


def test_actual_codex_suite_never_calls_external_installers(tmp_path: Path) -> None:
    # Break: a missing end marker used to execute npx/curl and real cleanup.
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    audit = tmp_path / "forbidden-calls"
    for name in ("npx", "npm", "curl", "wget", "sudo"):
        shim = bin_dir / name
        shim.write_text('#!/bin/sh\nprintf "%s\\n" "$0" >> "$AUDIT_LOG"\nexit 97\n')
        shim.chmod(0o755)
    pi = bin_dir / "pi"
    pi.write_text('#!/bin/sh\n[ "$1" = list ] || exit 98\nprintf "%s\\n" npm:@teelicht/pi-superagents\n')
    pi.chmod(0o755)
    result = _sandbox(tmp_path, [
        "env", f"PATH={bin_dir}:{os.environ['PATH']}", f"AUDIT_LOG={audit}",
        "bash", str(ROOT / ".devcontainer/test-pi-openai-codex.bash"),
    ])
    assert result.returncode == 0, result.stdout + result.stderr
    assert not audit.exists(), audit.read_text()


@pytest.mark.parametrize("text", [
    "printf unsafe\n" + END,
    START + "printf unsafe\n",
    END + START + "printf unsafe\n",
    START + START + "printf unsafe\n" + END,
    START + "printf unsafe\n" + END + END,
])
def test_invalid_boundaries_emit_nothing_and_execute_nothing(tmp_path: Path, text: str) -> None:
    installer = tmp_path / "invalid.bash"
    installer.write_text(text)
    result = _sandbox(tmp_path, ["bash", "-c", 'source "$1"; pi_launcher_install_fragment "$2"',
                                 "_", str(HELPER), str(installer)])
    assert result.returncode != 0
    assert result.stdout == ""


def test_only_launcher_section_runs(tmp_path: Path) -> None:
    installer = tmp_path / "fixture.bash"
    installer.write_text('exit 81\n' + START + 'printf allowed\n' + END + 'exit 82\n')
    result = _sandbox(tmp_path, ["bash", "-c", 'source "$1"; pi_run_launcher_install "$2" "$3"',
                                 "_", str(HELPER), str(installer), str(tmp_path / "home")])
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout == "allowed"


def test_fragment_cannot_modify_repository_or_access_host_network(tmp_path: Path) -> None:
    # Private /tmp is writable, but its writes must not reach the host /tmp.
    # The repository is readonly and the host's test listener is unreachable.
    installer = tmp_path / "isolation.bash"
    protected = tmp_path / "outside-home"
    protected.write_text("host-original")
    readonly = ROOT / "should-never-be-written-by-installer-test"
    assert not readonly.exists()
    with socket.create_server(("127.0.0.1", 0)) as server:
        port = server.getsockname()[1]
        probe = """printf kept > "$HOME/allowed"
printf private > "$PROTECTED_PATH"
if touch "$READONLY_PATH" 2>/dev/null; then exit 83; fi
node -e 'const net=require("node:net"); const c=net.connect(Number(process.env.TEST_PORT),"127.0.0.1"); c.on("connect",()=>process.exit(84)); c.on("error",()=>process.exit(0));'
"""
        installer.write_text(START + probe + END)
        # This fixture shares the parent's network so only the helper's own
        # network namespace can prevent access to this test-owned listener.
        result = _sandbox(tmp_path, [
            "env", f"PROTECTED_PATH={protected}", f"READONLY_PATH={readonly}", f"TEST_PORT={port}", "bash", "-c",
            'source "$1"; pi_run_launcher_install "$2" "$3"',
            "_", str(HELPER), str(installer), str(tmp_path / "home"),
        ], network=False)
    assert result.returncode == 0, result.stdout + result.stderr
    assert (tmp_path / "home/allowed").read_text() == "kept"
    assert protected.read_text() == "host-original"
    assert not readonly.exists()
