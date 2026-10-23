"""Machine CLI behavior without invoking any installed agent runtime."""

import json
import signal
import subprocess
import sys
import threading
from pathlib import Path
from types import ModuleType
from typing import cast

import pytest

from tools.agent_runner import cli, hooks, runner
from tools.agent_runner.adapters import (
    AdapterContext,
    AdapterOutcome,
    Capabilities,
    LaunchSpec,
)
from tools.agent_runner.models import BatchResult, BatchState, Config, Result

pytest_plugins = ("tools.test_support.plugin",)
# Only fake agents are launched here; drop AGENT_RUNNER_DEPTH inside each test so a runner agent can run them
pytestmark = pytest.mark.usefixtures("outside_runner")

# run_echo runs the real workflow (worktree checkout and a Python child) under this role
# deadline. Like the defaults in test_runner.py, it only bounds a run that hangs (#218).
_TEMPLATE = """schema_version = 1
[agents.a]
runtime = "pi"
command = ["never-invoke-this-command"]
model = "model-a"
[agents.b]
runtime = "codex"
command = ["never-invoke-this-command"]
model = "model-b"
[roles.inspect]
writes = false
deadline_seconds = 30
result_shape = "json"
[workflows.audit.assignments.inspect]
agents = ["a"]
fallback = ["b"]
"""


@pytest.fixture
def template(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("AGENT_RUNNER_CONFIG", str(tmp_path / "absent-personal.toml"))
    path = tmp_path / "template.toml"
    path.write_text(_TEMPLATE)
    return path


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True, capture_output=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.invalid",
            "commit",
            "--allow-empty",
            "-qm",
            "fixture",
        ],
        check=True,
        capture_output=True,
    )
    return repo


def document(output: str) -> dict[str, object]:
    return cast(dict[str, object], json.loads(output))


def test_explicit_missing_and_auto_broken_personal_are_errors(
    template: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli.main(["--template", str(template), "--config", str(tmp_path / "missing"), "check"]) == 2
    assert document(capsys.readouterr().out)["error"] == "config_io"
    broken = tmp_path / "broken"
    broken.symlink_to(tmp_path / "missing")
    monkeypatch.setenv("AGENT_RUNNER_CONFIG", str(broken))
    assert cli.main(["--template", str(template), "list"]) == 2
    assert document(capsys.readouterr().out)["error"] == "config_io"


@pytest.mark.parametrize(("state", "status"), [("success", 0), ("partial_success", 1)])
def test_run_exit_codes_and_atomic_result(
    template: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    state: BatchState,
    status: int,
) -> None:
    prompt = tmp_path / "prompt.txt"
    prompt.write_text('line 1\n"line 2"\n')
    artifact = tmp_path / "new-run"

    def fake_run(config: Config, workflow: str, text: str, repository: Path, **kwargs: object) -> BatchResult:
        assert text == 'line 1\n"line 2"\n'
        assert workflow == "audit" and repository == tmp_path
        assert kwargs["revision"] == "HEAD" and kwargs["concurrency"] == 3
        assert kwargs["output_dir"] == artifact
        artifact.mkdir()
        return BatchResult(
            run_id="test-run",
            state=state,
            assignments={"inspect": ["a"]},
            results=[],
            outside_changes=[],
            elapsed_seconds=0.0,
            artifact_dir=artifact,
        )

    monkeypatch.setattr(cli, "run_workflow", fake_run)
    code = cli.main(
        [
            "--template",
            str(template),
            "run",
            "--workflow",
            "audit",
            "--repository",
            str(tmp_path),
            "--prompt-file",
            str(prompt),
            "--concurrency",
            "3",
            "--output-dir",
            str(artifact),
        ]
    )
    assert code == status
    summary = document(capsys.readouterr().out)
    saved = document((artifact / "result.json").read_text())
    assert saved["state"] == state and summary["state"] == state
    assert summary["result_path"] == str(artifact / "result.json")
    assert not list(artifact.glob("*.tmp"))
    assert "line 1" not in json.dumps(summary) + json.dumps(saved)


def test_cli_overlay_assignment_priority_preserves_fallback(
    template: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    personal = tmp_path / "personal.toml"
    personal.write_text('[workflows.audit.assignments.inspect]\nagents = ["b"]\nfallback = ["a"]\n')
    prompt = tmp_path / "prompt"
    prompt.write_text("task")
    seen: list[list[str]] = []

    def fake_run(config: Config, workflow: str, text: str, repository: Path, **kwargs: object) -> BatchResult:
        assignment = config.workflows[workflow].assignments["inspect"]
        seen.append(assignment.agents)
        assert assignment.fallback == ["a"]
        artifact = tmp_path / f"run-{len(seen)}"
        artifact.mkdir()
        return BatchResult(
            run_id=f"run-{len(seen)}",
            state="self",
            assignments={"inspect": assignment.agents},
            results=[],
            outside_changes=[],
            elapsed_seconds=0.0,
            artifact_dir=artifact,
        )

    monkeypatch.setattr(cli, "run_workflow", fake_run)
    base = [
        "--template",
        str(template),
        "--config",
        str(personal),
        "run",
        "--workflow",
        "audit",
        "--repository",
        str(tmp_path),
        "--prompt-file",
        str(prompt),
    ]
    assert cli.main(base) == 0
    assert cli.main([*base, "--assign", "inspect=self"]) == 0
    assert seen == [["b"], ["self"]]
    assert len(capsys.readouterr().out.splitlines()) == 2


def test_sigint_saves_interrupted_batch_and_restores_handler(
    template: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    prompt = tmp_path / "prompt"
    prompt.write_text("task")
    previous = signal.getsignal(signal.SIGINT)
    artifact = tmp_path / "interrupted"

    def fake_run(config: Config, workflow: str, text: str, repository: Path, **kwargs: object) -> BatchResult:
        event = cast(threading.Event, kwargs["cancel"])
        handler = signal.getsignal(signal.SIGINT)
        assert callable(handler)
        handler(signal.SIGINT, None)
        assert event.is_set()
        artifact.mkdir()
        return BatchResult(
            run_id="interrupt-run",
            state="failed",
            assignments={"inspect": ["a"]},
            results=[
                Result(
                    request_id="request",
                    role="inspect",
                    requested_agent="a",
                    actual_agent="a",
                    state="interrupted",
                    attempts=[],
                )
            ],
            outside_changes=[],
            elapsed_seconds=0.0,
            artifact_dir=artifact,
        )

    monkeypatch.setattr(cli, "run_workflow", fake_run)
    assert (
        cli.main(
            [
                "--template",
                str(template),
                "run",
                "--workflow",
                "audit",
                "--repository",
                str(tmp_path),
                "--prompt-file",
                str(prompt),
            ]
        )
        == 130
    )
    assert signal.getsignal(signal.SIGINT) == previous
    saved = document((artifact / "result.json").read_text())
    assert cast(list[dict[str, object]], saved["results"])[0]["state"] == "interrupted"
    assert document(capsys.readouterr().out)["state"] == "failed"


# --- after_run（agent-workspace#601） ---------------------------------------------------------------------------------------

_HOOK = (
    "import json, os, sys; "
    "json.dump({'argv': sys.argv[1:], 'cwd': os.getcwd(), 'depth': os.environ.get('AGENT_RUNNER_DEPTH')}, "
    "open(sys.argv[2], 'w')); sys.exit(int(sys.argv[3]))"
)


def add_after_run(template: Path, *commands: list[str]) -> None:
    template.write_text(template.read_text() + "[workflows.audit]\nafter_run = " + json.dumps(list(commands)) + "\n")


def run_audit(template: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[int, Path]:
    prompt = tmp_path / "prompt.txt"
    prompt.write_text("task")
    artifact = tmp_path / "new-run"

    def fake_run(config: Config, workflow: str, text: str, repository: Path, **kwargs: object) -> BatchResult:
        artifact.mkdir()
        return BatchResult(
            run_id="test-run",
            state="success",
            assignments={"inspect": ["a"]},
            results=[],
            outside_changes=[],
            elapsed_seconds=0.0,
            artifact_dir=artifact,
        )

    monkeypatch.setattr(cli, "run_workflow", fake_run)
    argv = ["--template", str(template), "run", "--workflow", "audit", "--repository", str(tmp_path)]
    code = cli.main([*argv, "--prompt-file", str(prompt), "--output-dir", str(artifact)])
    return code, artifact


@pytest.mark.parametrize(("hook_exit", "state"), [(0, "success"), (3, "failed")])
def test_after_run_gets_the_result_path_and_never_changes_the_exit_code(
    template: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    hook_exit: int,
    state: str,
) -> None:
    marker = tmp_path / "hook.json"
    add_after_run(template, [sys.executable, "-c", _HOOK, "{result}", str(marker), str(hook_exit)])
    code, artifact = run_audit(template, tmp_path, monkeypatch)
    assert code == 0
    summary = document(capsys.readouterr().out)
    seen = json.loads(marker.read_text())
    assert seen["argv"][0] == summary["result_path"] == str(artifact / "result.json")
    assert seen["depth"] == "1"
    assert Path(seen["cwd"]) == Path(cli.__file__).resolve().parents[2]
    reports = cast(list[dict[str, object]], summary["after_run"])
    assert reports == [
        {
            "index": 0,
            "state": state,
            "exit_code": hook_exit,
            "stop_confirmed": True,
            "stdout_path": str(artifact / "after-run-0.stdout.log"),
            "stderr_path": str(artifact / "after-run-0.stderr.log"),
        }
    ]
    assert _HOOK not in json.dumps(summary)
    assert document((artifact / "result.json").read_text())["state"] == "success"


def test_after_run_internal_error_is_reported_without_changing_the_exit_code(
    template: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    async def broken(*_args: object, **_kwargs: object) -> object:
        raise RuntimeError("supervisor unavailable")

    monkeypatch.setattr(hooks, "execute", broken)
    add_after_run(template, ["never-invoke-this-command"])
    code, _artifact = run_audit(template, tmp_path, monkeypatch)
    assert code == 0
    report = cast(list[dict[str, object]], document(capsys.readouterr().out)["after_run"])[0]
    assert (report["state"], report["exit_code"], report["stop_confirmed"]) == ("response_failed", None, False)


# --- write_exceptions（agent-workspace#656） --------------------------------------------------------------------------------

_BODY = "review the change"
# 受け取った依頼の prompt を receipt の payload に写す。実際のエージェントの CLI は起動しない
_ECHO = (
    "import json, pathlib, sys; request = json.loads(sys.stdin.read()); "
    "receipt = {key: request[key] for key in ('schema_version', 'run_id', 'request_id', 'agent_id', 'role')}; "
    "receipt.update(status='success', payload={'prompt': request['prompt']}); "
    "pathlib.Path(sys.argv[1]).write_text(json.dumps(receipt))"
)


class EchoAdapter:
    capabilities = Capabilities()

    def prepare(self, context: AdapterContext) -> LaunchSpec:
        argv = (sys.executable, "-c", _ECHO, str(context.receipt_path))
        return LaunchSpec(argv, context.request.model_dump_json().encode())

    def collect(self, context: AdapterContext, stdout_path: Path, stderr_path: Path) -> AdapterOutcome:
        return AdapterOutcome()


def run_echo(template: Path, repository: Path, output: Path, monkeypatch: pytest.MonkeyPatch, *options: str) -> int:
    """実際の run_workflow を通し、pi の adapter だけを EchoAdapter に差し替えて CLI の run を実行する。"""
    module = ModuleType("tools.agent_runner.adapters.pi")
    module.__dict__["ADAPTER"] = EchoAdapter()
    monkeypatch.setitem(sys.modules, module.__name__, module)
    prompt = output.with_name(f"{output.name}-prompt.txt")
    prompt.write_text(_BODY)
    argv = ["--template", str(template), "run", "--workflow", "audit", "--repository", str(repository)]
    return cli.main([*argv, "--prompt-file", str(prompt), "--output-dir", str(output), *options])


def prompt_lines(output: Path) -> list[str]:
    """最後の試行が受け取った prompt を、実行ごとに違う work_dir を置き換えて行に分ける。"""
    results = cast(list[dict[str, object]], document((output / "result.json").read_text())["results"])
    attempt = cast(list[dict[str, object]], results[0]["attempts"])[-1]
    prompt = cast(dict[str, str], attempt["payload"])["prompt"]
    return prompt.replace(cast(str, attempt["work_dir"]), "<work_dir>").split("\n")


def test_write_exceptions_follow_the_work_scope_lines_in_order(
    template: Path,
    repository: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    values = ["/x/#7-feat-日本語\u3000名前: run records", "-x/notes", "uv cache with spaces"]
    plain_code = run_echo(template, repository, tmp_path / "plain", monkeypatch)
    capsys.readouterr()
    granted_code = run_echo(
        template,
        repository,
        tmp_path / "granted",
        monkeypatch,
        "--write-exception",
        values[0],
        f"--write-exception={values[1]}",
        "--write-exception",
        values[2],
    )
    captured = capsys.readouterr()
    summary = json.dumps(document(captured.out), ensure_ascii=False)
    assert plain_code == granted_code == 0
    assert captured.err == ""
    plain, granted = prompt_lines(tmp_path / "plain"), prompt_lines(tmp_path / "granted")
    # --write-exception を付けない呼び出しの指示は、作業範囲の 2 行と空行のまま
    assert runner.EXCEPTIONS_HEADING not in plain
    assert [line.split(":", 1)[0].split("=", 1)[0] for line in plain[:2]] == ["Work in this worktree only", "writes"]
    assert plain[2:] == ["", _BODY]
    assert granted == [*plain[:2], runner.EXCEPTIONS_HEADING, *(f"- {value}" for value in values), *plain[2:]]
    assert not any(value in summary for value in values)


@pytest.mark.parametrize(
    ("value", "code"),
    [
        pytest.param("notes may change", 0, id="valid"),
        # 別の引数に書いた -x は argparse がオプションと読む。値は --write-exception=-x と書く
        pytest.param("-x", 2, id="dash-separate-token"),
    ],
)
def test_invalid_write_exceptions_are_rejected_before_any_output(
    template: Path,
    repository: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    value: str,
    code: int,
) -> None:
    output = tmp_path / "output"
    assert run_echo(template, repository, output, monkeypatch, "--write-exception", value) == code
    captured = capsys.readouterr()
    # 正しい値なら同じ呼び出しが成功するので、拒否は値によるもので引数の未定義によるものではない
    assert output.exists() is (code == 0)
    assert captured.err == ""
    if code == 2:
        assert captured.out == json.dumps({"error": "invalid_input"}) + "\n"
