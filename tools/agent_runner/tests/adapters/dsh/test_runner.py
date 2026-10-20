"""Runner/process integration for DSH using real disposable repositories."""

import json
import os
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any

import pytest

from tools.agent_runner import environ, runner
from tools.agent_runner.models import Agent, Assignment, Config, Role, Workflow
from tools.agent_runner.process import ProcessResult
from tools.agent_runner.runner import run_workflow
from tools.agent_runner.tests.test_runner import set_when, written
from tools.agent_runner.tests.test_workspace import git

pytest_plugins = ("tools.test_support.plugin",)
# Only fake agents are launched here; drop AGENT_RUNNER_DEPTH inside each test so a runner agent can run them
pytestmark = pytest.mark.usefixtures("outside_runner")

FAKE = Path(__file__).with_name("fake_cli.py")


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    root = tmp_path / "repository"
    root.mkdir()
    (root / "README.md").write_text("# fixture workspace\n")
    # Prevent an invoking agent's GIT_DIR/GIT_WORK_TREE/config from selecting another checkout.
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    for args in (
        ["init", "-q"],
        ["config", "user.name", "Fixture"],
        ["config", "user.email", "fixture@example.invalid"],
        ["config", "commit.gpgsign", "false"],
        ["add", "README.md"],
        ["commit", "-qm", "fixture"],
    ):
        subprocess.run(["git", "-C", str(root), *args], env=env, check=True, capture_output=True)
    return root


@pytest.fixture
def ambient_tmp(tmp_path: Path) -> Path:
    path = tmp_path / "ambient-tmp"
    path.mkdir()
    return path


@pytest.fixture
def config(monkeypatch: pytest.MonkeyPatch, ambient_tmp: Path) -> Config:
    # An allowlisted ambient TMPDIR must not receive the runtime's temporary files.
    monkeypatch.setattr(
        environ,
        "_literal",
        {"COMMANDCODE_API_KEY": "private-test-credential", "PATH": os.defpath, "TMPDIR": str(ambient_tmp)},
    )
    return Config(
        agents={
            "a": Agent(
                runtime="dsh",
                command=[sys.executable, str(FAKE), "success"],
                model="fixture-model",
                provider="commandcode",
                env=["COMMANDCODE_API_KEY", "TMPDIR"],
            )
        },
        roles={"inspect": Role(writes=False, deadline_seconds=15.0, result_shape="json")},
        workflows={"test": Workflow(assignments={"inspect": Assignment(agents=["a"])})},
    )


@pytest.mark.parametrize(
    "mode,state,exit_code",
    [
        ("success", "success", 0),
        ("auth", "awaiting_authentication", 1),
        ("approval", "awaiting_approval", 0),
        ("approval-program", "awaiting_approval", 0),
        ("nonzero", "response_failed", 1),
        ("malformed", "response_failed", 0),
        ("missing-session", "response_failed", 0),
        ("mismatched-session", "response_failed", 0),
        ("descendant", "success", 0),
    ],
)
def test_real_process_state_and_stdin(
    config: Config, repository: Path, tmp_path: Path, mode: str, state: str, exit_code: int
) -> None:
    config.agents["a"].command[-1] = mode
    prompt = "一行目\n二行目 ☃\n"
    result = run_workflow(config, "test", prompt, repository, output_dir=tmp_path / "run")
    attempt = result.results[0].attempts[0]
    assert attempt.state == state
    assert attempt.exit_code == exit_code
    assert attempt.stop_confirmed
    assert attempt.work_dir is not None
    assert attempt.request_path is not None
    capture = json.loads((attempt.request_path.parent / "dsh" / "state" / "capture.json").read_text())
    assert capture["prompt"].endswith(prompt)
    assert capture["depth"] == "1" and capture["telemetry"] == "DISABLED"
    assert Path(capture["home"]).is_relative_to(attempt.request_path.parent)
    assert Path(capture["tmpdir"]).is_relative_to(attempt.request_path.parent / "dsh")
    assert capture["parent_model"] is None
    if state == "success":
        assert (attempt.identity.provider, attempt.identity.model) == ("commandcode", "fixture-model")
        assert isinstance(attempt.payload, dict)
        assert attempt.payload["secret"] == "[REDACTED]"
    if mode == "descendant":
        # The file contains a PID in the runtime's private namespace; host-side
        # descendant teardown is exercised below using an observed host PID.
        assert int((attempt.work_dir / "child.pid").read_text()) > 0


def test_native_process_has_private_tmp_and_readonly_attempt_metadata(
    config: Config, repository: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "other-attempt" / "receipt.json"
    target.parent.mkdir()
    target.write_text("host original")
    monkeypatch.setitem(environ._literal, "FAKE_HOST_TARGET", str(target))
    monkeypatch.setitem(environ._literal, "FAKE_HOST_PID", str(os.getpid()))
    config.agents["a"].env.extend(("FAKE_HOST_TARGET", "FAKE_HOST_PID"))
    config.agents["a"].command[-1] = "native-fence"
    result = run_workflow(config, "test", "respond", repository, output_dir=tmp_path / "run")
    attempt = result.results[0].attempts[0]
    assert target.read_text() == "host original"
    assert attempt.state == "success" and attempt.stop_confirmed
    assert attempt.request_path is not None
    capture = json.loads((attempt.request_path.parent / "dsh/state/capture.json").read_text())
    assert all(capture["denied"].values())
    assert capture["hardlink_denied"]
    assert not capture["host_proc_visible"]
    assert capture["helper_exit"] == 0, capture["helper_error"]
    assert not (attempt.request_path.parent / "receipt.json").exists()
    assert Path(capture["scratch"]).joinpath("native.txt").read_text() == "native output"
    assert Path(capture["scratch"]).joinpath("helper.txt").read_text() == "helper output"
    assert Path(capture["exports"]).joinpath("native.txt").read_text() == "native output"


@pytest.mark.parametrize("target", ["main", "feature", "neighbor", "git", "host-tmp"])
def test_scoped_dsh_cannot_modify_protected_or_unrelated_host_paths(
    config: Config, repository: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, target: str,
) -> None:
    from tools.agent_runner.workspace import create_worktree

    feature = create_worktree(repository, "HEAD", tmp_path / "feature")
    neighbor = create_worktree(repository, "HEAD", tmp_path / "neighbor")
    host_tmp = tmp_path / "host-tmp.txt"
    host_tmp.write_text("host temporary data")
    protected = {
        "main": repository / "README.md",
        "feature": feature / "README.md",
        "neighbor": neighbor / "README.md",
        "git": repository / ".git" / "config",
        "host-tmp": host_tmp,
    }[target]
    before = protected.read_bytes()
    monkeypatch.setitem(environ._literal, "FAKE_HOST_TARGET", str(protected))
    monkeypatch.setitem(environ._literal, "FAKE_HOST_PID", str(os.getpid()))
    config.agents["a"].env.extend(("FAKE_HOST_TARGET", "FAKE_HOST_PID"))
    config.agents["a"].command[-1] = "native-fence"
    batch = run_workflow(config, "test", "respond", feature, output_dir=tmp_path / "run")
    attempt = batch.results[0].attempts[0]
    assert attempt.state == "success" and attempt.stop_confirmed
    assert protected.read_bytes() == before
    assert batch.outside_changes == [] and batch.unrelated_checkout_audit == []
    assert attempt.work_dir is not None
    assert git(attempt.work_dir, "rev-parse", "HEAD") == git(feature, "rev-parse", "HEAD")


def test_real_dsh_keeps_parallel_edit_as_observation(
    config: Config, repository: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tools.agent_runner.workspace import create_worktree

    neighbor = create_worktree(repository, "HEAD", tmp_path / "neighbor")
    original = runner.snapshot_checkouts

    def snapshot(root: Path) -> Any:
        before = original(root)
        # This is a write by another controller, outside the sandboxed child.
        (neighbor / "README.md").write_text("another session's edit")
        return before

    monkeypatch.setattr(runner, "snapshot_checkouts", snapshot)
    batch = run_workflow(config, "test", "respond", repository, output_dir=tmp_path / "run")
    assert batch.state == "success" and batch.outside_changes == []
    assert [item.path for item in batch.unrelated_checkout_audit] == [str(neighbor)]


def test_dsh_output_ancestor_symlink_is_rejected(
    config: Config, repository: Path, tmp_path: Path,
) -> None:
    from tools.agent_runner.runner import RunnerError

    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "link"
    link.symlink_to(real, target_is_directory=True)
    with pytest.raises(RunnerError):
        run_workflow(config, "test", "respond", repository, output_dir=link / "run")
    assert not (real / "run").exists()


def test_runtime_hardlinks_are_rejected_before_redaction_hides_the_link(
    config: Config, repository: Path, tmp_path: Path,
) -> None:
    # Retained records keep the strict policy; only TMPDIR scratch hard links are unlinked.
    config.agents["a"].command[-1] = "hardlink"
    result = run_workflow(config, "test", "respond", repository, output_dir=tmp_path / "run")
    attempt = result.results[0].attempts[0]
    assert attempt.state == "response_failed" and attempt.stop_confirmed
    assert attempt.request_path is not None
    state = attempt.request_path.parent / "dsh/state"
    assert {state / "original.json", state / "linked.json"} <= set(attempt.sensitive_paths)
    # Redaction replaced neither name, so the second link is still visible.
    assert (state / "linked.json").stat().st_nlink == 2


def test_dsh_prompt_uses_only_its_owned_write_exceptions(
    config: Config, repository: Path, tmp_path: Path,
) -> None:
    shared_exception = "shared/reviews: another runtime may save its review here"
    result = run_workflow(
        config, "test", "respond", repository, output_dir=tmp_path / "run",
        write_exceptions=(shared_exception,),
    )
    attempt = result.results[0].attempts[0]
    assert attempt.state == "success" and attempt.request_path is not None
    request = json.loads(attempt.request_path.read_text())
    assert shared_exception not in request["prompt"]
    assert str(attempt.request_path.parent / "review-scratch") in request["prompt"]
    assert str(attempt.request_path.parent / "dsh/tmp/exports") in request["prompt"]


@pytest.mark.parametrize(
    "mode",
    [
        "read-402-lines", "read-401-lines", "read-403-lines", "read-401-filename", "read-403-filename",
        "read-approval-cancelled", "read-approval-unavailable", "read-approval-rejected",
        "read-requires-approval", "read-approvals-path",
        "ptc-read", "ptc-read_403", "ptc-captured_only", "ptc-caught_rejection",
    ],
)
@pytest.mark.parametrize("with_fallback", [False, True])
def test_recovered_read_error_keeps_primary_result(
    config: Config, repository: Path, tmp_path: Path, mode: str, with_fallback: bool
) -> None:
    config.agents["a"].command[-1] = mode
    if with_fallback:
        fallback = config.agents["a"].model_copy(deep=True)
        fallback.command[-1] = "success"
        fallback.model = "fallback-model"
        config.agents["b"] = fallback
        config.workflows["test"].assignments["inspect"].fallback = ["b"]
    result = run_workflow(config, "test", "recover from a read error", repository, output_dir=tmp_path / "run")
    assert result.state == "success"
    role_result = result.results[0]
    assert role_result.state == "success"
    assert role_result.actual_agent == "a"
    assert len(role_result.attempts) == 1
    attempt = role_result.attempts[0]
    assert attempt.agent_id == "a" and attempt.state == "success"
    assert attempt.exit_code == 0 and attempt.stop_confirmed
    assert isinstance(attempt.payload, dict) and attempt.payload["ok"] is True
    assert (attempt.identity.provider, attempt.identity.model) == ("commandcode", "fixture-model")


def test_explicit_provider_key_is_used_without_ambient_credentials(
    config: Config, repository: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(environ, "_literal", {"PATH": os.defpath})
    result = run_workflow(
        config,
        "test",
        "respond",
        repository,
        output_dir=tmp_path / "run",
        environment={"COMMANDCODE_API_KEY": "explicit-test-credential"},
    )
    assert result.state == "success"
    attempt = result.results[0].attempts[0]
    assert isinstance(attempt.payload, dict) and attempt.payload["secret"] == "[REDACTED]"
    assert "explicit-test-credential" not in result.model_dump_json()


def test_explicit_auth_environment_is_allowlisted_and_redacted(
    config: Config, repository: Path, tmp_path: Path
) -> None:
    config.agents["a"].env.append("GH_TOKEN")
    config.agents["a"].command[-1] = "github-token"
    result = run_workflow(
        config,
        "test",
        "respond",
        repository,
        output_dir=tmp_path / "run",
        environment={"GH_TOKEN": "private-github-token", "UNLISTED_SECRET": "do-not-inherit"},
    )
    attempt = result.results[0].attempts[0]
    assert attempt.state == "success" and attempt.stop_confirmed
    assert attempt.payload == {"github_token": "[REDACTED]", "unlisted": None}
    assert attempt.request_path is not None
    assert "private-github-token" not in result.model_dump_json()
    for name in ("stdout.log", "request.json", "dsh/state/session.jsonl"):
        assert "private-github-token" not in (attempt.request_path.parent / name).read_text()


def test_private_session_artifacts_are_redacted(config: Config, repository: Path, tmp_path: Path) -> None:
    result = run_workflow(config, "test", "respond", repository, output_dir=tmp_path / "run")
    attempt = result.results[0].attempts[0]
    assert attempt.request_path is not None
    session = attempt.request_path.parent / "dsh" / "state" / "session.jsonl"
    assert json.loads(session.read_text())["tool"] == "[REDACTED]"
    assert attempt.sensitive_paths == []
    assert "private-test-credential" not in attempt.model_dump_json()


def test_home_tool_caches_are_disposed_without_following_links(
    config: Config, repository: Path, tmp_path: Path
) -> None:
    config.agents["a"].command[-1] = "home-cache"
    result = run_workflow(config, "test", "respond", repository, output_dir=tmp_path / "run")
    attempt = result.results[0].attempts[0]
    assert attempt.state == "success" and attempt.stop_confirmed
    assert attempt.sensitive_paths == []
    assert attempt.request_path is not None and attempt.work_dir is not None
    root = attempt.request_path.parent / "dsh"
    assert not os.path.lexists(root / "home")  # links, FIFO, secrets and caches are not retained
    assert (root / "state" / "capture.json").is_file()
    assert (attempt.work_dir / "README.md").read_text() == "# fixture workspace\n"
    assert Path(sys.executable).exists()


def test_large_tmpdir_spill_is_kept_in_runtime_tree_and_redacted(
    config: Config, repository: Path, tmp_path: Path, ambient_tmp: Path
) -> None:
    config.agents["a"].command[-1] = "spill"
    result = run_workflow(config, "test", "respond", repository, output_dir=tmp_path / "run")
    attempt = result.results[0].attempts[0]
    assert attempt.state == "success" and attempt.sensitive_paths == []
    assert attempt.request_path is not None
    root = attempt.request_path.parent / "dsh"
    capture = json.loads((root / "state" / "capture.json").read_text())
    spill = Path(capture["spill"])
    assert spill.is_relative_to(root / "tmp")
    content = spill.read_text()
    assert len(content) > 70000
    assert "private-test-credential" not in content and "API_KEY=[REDACTED]" in content
    assert list(ambient_tmp.iterdir()) == []


@pytest.mark.parametrize("mode", ["symlink", "fifo"])
def test_unsafe_runtime_files_are_reported_not_followed(
    config: Config, repository: Path, tmp_path: Path, mode: str
) -> None:
    config.agents["a"].command[-1] = mode
    result = run_workflow(config, "test", "respond", repository, output_dir=tmp_path / "run")
    attempt = result.results[0].attempts[0]
    assert attempt.state == "response_failed"
    assert attempt.stop_confirmed
    assert attempt.sensitive_paths
    assert attempt.work_dir is not None and attempt.request_path is not None
    assert (attempt.work_dir / "README.md").read_text() == "# fixture workspace\n"
    # Retained records keep the strict policy: links and FIFOs are reported, never removed.
    managed = attempt.request_path.parent / "dsh" / "state"
    assert all(path.is_relative_to(managed) for path in attempt.sensitive_paths)
    assert os.path.lexists(attempt.sensitive_paths[0])
    if mode == "symlink":
        assert attempt.sensitive_paths[0].is_symlink()


@pytest.mark.parametrize("mode,name", [("tmp-symlink", "foreign-link"), ("tmp-fifo", "spill.fifo")])
def test_scratch_links_and_fifos_are_unlinked_not_followed(
    config: Config, repository: Path, tmp_path: Path, mode: str, name: str
) -> None:
    config.agents["a"].command[-1] = mode
    result = run_workflow(config, "test", "respond", repository, output_dir=tmp_path / "run")
    attempt = result.results[0].attempts[0]
    assert attempt.state == "success" and attempt.stop_confirmed
    assert attempt.sensitive_paths == []
    assert attempt.work_dir is not None and attempt.request_path is not None
    assert not os.path.lexists(attempt.request_path.parent / "dsh" / "tmp" / name)
    assert (attempt.work_dir / "README.md").read_text() == "# fixture workspace\n"


def test_scratch_hardlinks_are_unlinked_and_the_rest_redacted(
    config: Config, repository: Path, tmp_path: Path
) -> None:
    config.agents["a"].command[-1] = "tmp-hardlink"
    result = run_workflow(config, "test", "respond", repository, output_dir=tmp_path / "run")
    attempt = result.results[0].attempts[0]
    assert attempt.state == "success" and attempt.stop_confirmed
    assert attempt.sensitive_paths == []
    assert attempt.request_path is not None
    root = attempt.request_path.parent / "dsh"
    assert not os.path.lexists(root / "tmp" / "original.json")
    assert not os.path.lexists(root / "tmp" / "linked.json")
    files = [path for path in root.rglob("*") if path.is_file() and not path.is_symlink()]
    # A name left with a single link is an ordinary scratch file, redacted like the others.
    assert all(path.lstat().st_nlink == 1 for path in files if path.is_relative_to(root / "tmp"))
    assert all(b"private-test-credential" not in path.read_bytes() for path in files)


@pytest.mark.parametrize("mode", ["pytest", "pytest-fixtures"])
def test_real_pytest_scratch_is_accepted(config: Config, repository: Path, tmp_path: Path, mode: str) -> None:
    config.agents["a"].command[-1] = mode
    result = run_workflow(config, "test", "respond", repository, output_dir=tmp_path / "run")
    attempt = result.results[0].attempts[0]
    assert attempt.request_path is not None and attempt.work_dir is not None
    root = attempt.request_path.parent / "dsh"
    capture = json.loads((root / "state" / "capture.json").read_text())
    assert capture["pytest"]["exit"] == 0 and "1 passed" in capture["pytest"]["summary"][0]
    assert attempt.state == "success" and attempt.stop_confirmed
    assert attempt.sensitive_paths == []
    assert result.outside_changes == []
    leftovers = [
        path
        for path in (root / "tmp").rglob("*")
        if path.is_symlink() or not (path.is_dir() or path.is_file()) or (path.is_file() and path.stat().st_nlink > 1)
    ]
    assert leftovers == []
    # Regular files written by the test stay for diagnosis.
    assert [path.read_text() for path in (root / "tmp").rglob("clean.txt")] == ["synthetic clean fixture\n"]
    assert (attempt.work_dir / "README.md").read_text() == "# fixture workspace\n"
    if mode == "pytest-fixtures":
        # outside-dir pointed at the checkout; its own link was not reached through it.
        assert (attempt.work_dir / "sentinel-link").is_symlink()


@pytest.mark.parametrize(
    "mode,names",
    [("tmp-fifo", ["spill.fifo"]), ("tmp-hardlink", ["linked.json", "nested/shared.json", "original.json"])],
)
def test_scratch_unlink_failure_is_reported_not_success(
    config: Config, repository: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: str, names: list[str]
) -> None:
    original = os.unlink
    refused = {Path(name).name for name in names}

    def failing(path: Any, *, dir_fd: int | None = None) -> None:
        if path in refused:
            raise PermissionError("injected unlink failure")
        original(path, dir_fd=dir_fd)

    monkeypatch.setattr(os, "unlink", failing)
    config.agents["a"].command[-1] = mode
    result = run_workflow(config, "test", "respond", repository, output_dir=tmp_path / "run")
    attempt = result.results[0].attempts[0]
    assert attempt.state == "response_failed" and attempt.stop_confirmed
    assert attempt.request_path is not None
    scratch = attempt.request_path.parent / "dsh" / "tmp"
    assert sorted(attempt.sensitive_paths) == [scratch / name for name in names]


@pytest.mark.parametrize("mode,replaced", [("home-link", "dsh/home"), ("root-link", "dsh"), ("tmp-link", "dsh/tmp")])
def test_kernel_rejects_replacing_runtime_mounts_and_keeps_target(
    config: Config, repository: Path, tmp_path: Path, mode: str, replaced: str
) -> None:
    config.agents["a"].command[-1] = mode
    result = run_workflow(config, "test", "respond", repository, output_dir=tmp_path / "run")
    attempt = result.results[0].attempts[0]
    assert attempt.state == "response_failed" and attempt.stop_confirmed
    assert attempt.request_path is not None and attempt.work_dir is not None
    link = attempt.request_path.parent / replaced
    assert not link.is_symlink()
    assert attempt.sensitive_paths == []
    assert (attempt.work_dir / "README.md").read_text() == "# fixture workspace\n"
    assert (attempt.work_dir / ".git").exists()
    if mode == "root-link":
        assert (attempt.work_dir / "home" / "keep.txt").read_text() == "keep\n"
    # Links behind a replaced root or TMPDIR are outside the scratch and stay.
    target = {"root-link": "tmp", "tmp-link": "scratch"}.get(mode)
    if target is not None:
        assert (attempt.work_dir / target / "keep-link").is_symlink()


def test_home_removal_failure_is_reported_not_success(
    config: Config, repository: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = shutil.rmtree

    def failing(path: Any, *, dir_fd: int | None = None) -> None:
        if Path(path).name == "home":
            raise PermissionError("injected removal failure")
        original(path, dir_fd=dir_fd)

    monkeypatch.setattr(shutil, "rmtree", failing)
    result = run_workflow(config, "test", "respond", repository, output_dir=tmp_path / "run")
    attempt = result.results[0].attempts[0]
    assert attempt.state == "response_failed" and attempt.stop_confirmed
    assert attempt.request_path is not None
    home = attempt.request_path.parent / "dsh" / "home"
    assert home in attempt.sensitive_paths
    # A HOME that could not be disposed is still strictly redacted, not skipped.
    assert (home / ".netrc").read_text() == "password [REDACTED]\n"


def _assert_stopped(pid: int) -> None:
    path = Path(f"/proc/{pid}/stat")
    if path.exists():
        assert path.read_text().rsplit(")", 1)[1].split()[0] == "Z"


@pytest.mark.parametrize("interrupt", [False, True])
def test_timeout_and_cancellation_stop_descendants(
    config: Config, repository: Path, tmp_path: Path, interrupt: bool
) -> None:
    config.agents["a"].command[-1] = "hang"
    # Cancel once the runtime wrote its last file, not on a clock started before
    # the run; the timeout covers checkout and startup (unloaded 0.17 s) (#694).
    config.roles["inspect"].deadline_seconds = 60.0 if interrupt else 3.0
    cancel = threading.Event()
    observed: set[int] = set()

    def child_running() -> bool:
        markers = list(tmp_path.glob("run/*/attempt-1/worktree/child.pid"))
        if not markers or written(markers) != 1:
            return False
        marker = os.fsencode(markers[0])
        # A private procfs reports namespace PIDs. Observe the exact fake child
        # argv from the controller's procfs before asking the runner to cancel.
        for process_dir in Path("/proc").iterdir():
            if process_dir.name.isdecimal():
                try:
                    if marker in (process_dir / "cmdline").read_bytes().split(b"\0"):
                        observed.add(int(process_dir.name))
                except OSError:
                    pass
        return interrupt and bool(observed)

    with set_when(cancel, child_running):
        result = run_workflow(config, "test", "respond", repository, output_dir=tmp_path / "run", cancel=cancel)
    attempt = result.results[0].attempts[0]
    assert attempt.state == ("interrupted" if interrupt else "timed_out")
    assert attempt.stop_confirmed
    assert attempt.work_dir is not None
    assert observed
    for pid in observed:
        _assert_stopped(pid)
    assert attempt.request_path is not None
    root = attempt.request_path.parent / "dsh"
    session = root / "state" / "session.jsonl"
    assert "private-test-credential" not in session.read_text()
    spill = Path(json.loads((root / "state" / "capture.json").read_text())["spill"])
    assert spill.is_relative_to(root / "tmp")
    assert "private-test-credential" not in spill.read_text()
    assert not os.path.lexists(root / "home")


def test_unconfirmed_stop_reports_runtime_root(
    config: Config, repository: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def unconfirmed(*args: Any, **kwargs: Any) -> ProcessResult:
        (Path(kwargs["env"]["TMPDIR"]) / "live-link").symlink_to(kwargs["cwd"] / "README.md")
        return ProcessResult(None, 0, False, 0.0)

    monkeypatch.setattr(runner, "execute", unconfirmed)
    result = run_workflow(config, "test", "respond", repository, output_dir=tmp_path / "run")
    attempt = result.results[0].attempts[0]
    assert attempt.state == "response_failed" and not attempt.stop_confirmed
    assert attempt.request_path is not None
    root = attempt.request_path.parent / "dsh"
    assert root in attempt.sensitive_paths
    # Without stop evidence a live writer may still use HOME and TMPDIR; neither is removed nor read.
    assert (root / "home").is_dir()
    assert (root / "tmp" / "live-link").is_symlink()


@pytest.mark.parametrize("case", ["rejected", "cancelled", "unavailable", "tool_approval"])
@pytest.mark.parametrize("with_fallback", [False, True])
def test_ptc_refusal_keeps_primary_failed(
    config: Config, repository: Path, tmp_path: Path, case: str, with_fallback: bool
) -> None:
    config.agents["a"].command[-1] = "ptc-" + case
    if with_fallback:
        fallback = config.agents["a"].model_copy(deep=True)
        fallback.command[-1] = "success"
        fallback.model = "fallback-model"
        config.agents["b"] = fallback
        config.workflows["test"].assignments["inspect"].fallback = ["b"]
    result = run_workflow(config, "test", "report the tool result", repository, output_dir=tmp_path / "run")
    assert result.state == ("success" if with_fallback else "failed")
    role = result.results[0]
    assert role.actual_agent == ("b" if with_fallback else "a")
    assert len(role.attempts) == (2 if with_fallback else 1)
    primary = role.attempts[0]
    assert primary.agent_id == "a" and primary.state == "awaiting_approval"
    assert primary.payload is None
    assert primary.exit_code == 0 and primary.stop_confirmed
    assert (primary.identity.provider, primary.identity.model) == ("commandcode", "fixture-model")
    if with_fallback:
        assert role.attempts[1].state == "success"
        assert isinstance(role.attempts[1].payload, dict) and role.attempts[1].payload["ok"] is True
