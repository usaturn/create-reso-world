"""Offline executable boundary tests: no real Meshy binary, credentials or HTTP.

The fake replaces only the paid/network CLI boundary. The wrapper, filesystem,
locks, subprocesses and state transitions all execute for real.
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
ENTRY = ROOT / "scripts/meshy.py"
KEY = "msy_test_secret_sentinel_123456"
TASK = "01957f00-a111-7777-8888-0123456789ab"

FAKE = r"""#!__PYTHON__
import json, os, pathlib, signal, sys, time
args = sys.argv[1:]
with open(os.environ['FAKE_CALLS'], 'a') as f:
    f.write(json.dumps({'args': args, 'env': {k:v for k,v in os.environ.items() if k.startswith('MESHY_')}}) + '\n')
if 'create' in args:
    oid = args[args.index('--operation-id')+1]
    journal = pathlib.Path(os.environ['MESHY_CONFIG_DIR']) / 'operations'
    journal.mkdir(parents=True, exist_ok=True)
    (journal / (oid + '.json')).write_text(json.dumps({'operation_id':oid, 'state':'started'}))
mode = os.environ.get('FAKE_MODE', '')
if mode == 'sleep':
    time.sleep(3)
if mode == 'interrupt':
    os.kill(os.getppid(), signal.SIGINT)
    time.sleep(3)
if mode == 'malformed':
    print('not JSON ' + os.environ['MESHY_API_KEY'])
    print(os.environ['MESHY_API_KEY'], file=sys.stderr)
    sys.exit(1)
if 'download' in args:
    source = pathlib.Path(args[args.index('--output-dir')+1])
    source.mkdir(exist_ok=True, parents=True)
    (source / 'generated.glb').write_bytes(b'glTF-fixture')
reply = json.loads(pathlib.Path(os.environ['FAKE_REPLY']).read_text())
print(json.dumps(reply))
print(os.environ['MESHY_API_KEY'], file=sys.stderr)
sys.exit(0 if reply.get('ok') else 10)
"""


@pytest.fixture
def world(tmp_path):
    project = tmp_path / "world"
    project.mkdir()
    (project / ".resoloop.json").write_text("{}")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake = bin_dir / "meshy"
    fake.write_text(FAKE.replace("__PYTHON__", sys.executable))
    fake.chmod(0o755)
    reply = tmp_path / "reply.json"
    calls = tmp_path / "calls.jsonl"
    # An ambient credential profile must never enable keyless operations.
    home = tmp_path / "home"
    (home / ".config/meshy").mkdir(parents=True)
    (home / ".config/meshy/credentials.json").write_text(
        '{"api_key":"ambient-saved-key"}'
    )
    env = {k: v for k, v in os.environ.items() if not k.startswith("MESHY_")}
    env.update(
        PATH=str(bin_dir),
        HOME=str(home),
        MESHY_API_KEY=KEY,
        FAKE_REPLY=str(reply),
        FAKE_CALLS=str(calls),
    )
    return Harness(project, env, reply, calls)


class Harness:
    def __init__(self, project, env, reply, calls):
        self.project, self.env, self.reply_file, self.calls_file = (
            project,
            env,
            reply,
            calls,
        )
        self.reply(
            result={"task": {"task_id": TASK, "status": "PENDING", "progress": 0}}
        )

    def reply(self, *, result=None, ok=True, error=None):
        self.reply_file.write_text(
            json.dumps(
                {
                    "schema_version": "meshy.cli/v1",
                    "ok": ok,
                    "result": result or {},
                    "error": error,
                }
            )
        )

    def command(self, *args):
        # Shorten only the subprocess deadline in this isolated interpreter.
        bootstrap = (
            f"import sys; sys.path.insert(0, {str(ROOT / 'scripts')!r}); "
            "import meshy_workflow; meshy_workflow.CLI_TIMEOUT_SECONDS=0.3; "
            "import meshy; raise SystemExit(meshy.main())"
        )
        return [sys.executable, "-c", bootstrap, "--project", str(self.project), *args]

    def run(self, *args, ok=True):
        proc = subprocess.run(
            self.command(*args),
            env=self.env,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if ok:
            assert proc.returncode == 0, proc.stdout + proc.stderr
        else:
            assert proc.returncode != 0, proc.stdout + proc.stderr
        assert KEY not in proc.stdout + proc.stderr
        assert "Traceback" not in proc.stdout + proc.stderr
        return proc

    def plan(self, name="asset", *args):
        self.run(
            "plan", "--operation", name, "--kind", "text", "--prompt", "a stone", *args
        )

    def manifest_path(self, name="asset"):
        return self.project / "content/generated/meshy" / name / "operation.json"

    def manifest(self, name="asset"):
        text = self.manifest_path(name).read_text()
        assert KEY not in text
        return json.loads(text)

    def calls(self):
        if not self.calls_file.exists():
            return []
        return [json.loads(line) for line in self.calls_file.read_text().splitlines()]

    def submit(self, ok=True):
        return self.run("submit", "--operation", "asset", "--confirm-paid", ok=ok)


# Catch accidental authentication/installation prerequisites on offline planning/help.
def test_plan_and_help_need_neither_key_nor_cli(world):
    world.env.pop("MESHY_API_KEY")
    world.env["PATH"] = "/nonexistent"
    world.run("--help")
    world.plan()
    op = world.manifest()
    assert op["stage"] == "planned"
    assert op["task"]["task_id"] is None
    assert op["downloads"] == {"state": "not_requested", "files": []}
    assert world.calls() == []
    before = world.manifest_path().read_bytes()
    world.run(
        "plan",
        "--operation",
        "asset",
        "--kind",
        "text",
        "--prompt",
        "replacement",
        ok=False,
    )
    assert world.manifest_path().read_bytes() == before


# Catch CLI fallback to saved credentials for every API verb.
@pytest.mark.parametrize(
    "key",
    [
        None,
        "",
        "  \n ",
        "YOUR_MESHY_API_KEY_HERE",
        "your_meshy_api_key_here",
        "your-api-key",
        "<MESHY_API_KEY>",
    ],
)
@pytest.mark.parametrize(
    "verb", ["submit", "status", "wait", "download", "list", "attach", "balance"]
)
def test_unusable_key_never_starts_cli(world, key, verb):
    world.plan()
    if key is None:
        world.env.pop("MESHY_API_KEY")
    else:
        world.env["MESHY_API_KEY"] = key
    extra = {
        "submit": ["--confirm-paid"],
        "list": ["--resource", "text-to-3d"],
        "attach": ["--task-id", TASK],
    }.get(verb, [])
    world.run(verb, "--operation", "asset", *extra, ok=False)
    assert world.calls() == []
    assert world.manifest()["stage"] == "planned"


# Catch paid creates without confirmation or accidental raw API defaults.
def test_submit_requires_confirmation_and_explicit_preview_payload(world):
    world.plan()
    world.run("submit", "--operation", "asset", ok=False)
    assert world.calls() == []
    world.submit()
    call = world.calls()[0]
    args = call["args"]
    assert args[:8] == [
        "--output-schema",
        "v1",
        "--format",
        "json",
        "--no-update-check",
        "--workspace",
        str(world.project),
        "text-to-3d",
    ]
    assert args[8] == "create"
    assert "--async" in args
    assert args[args.index("--operation-id") + 1] == world.manifest()["operation_id"]
    payload = json.loads(args[args.index("--data") + 1])
    assert payload == {
        "mode": "preview",
        "prompt": "a stone",
        "ai_model": "latest",
        "target_formats": ["glb"],
    }
    assert KEY not in json.dumps(args)


# Catch loss of accepted IDs in any documented v1 response, including errors.
@pytest.mark.parametrize("shape", ["task", "top", "submission"])
@pytest.mark.parametrize("accepted_error", [False, True])
def test_accepted_task_is_saved_and_submit_never_repeats(world, shape, accepted_error):
    world.plan()
    result = (
        {"task": {"task_id": TASK, "status": "PENDING", "progress": 3}}
        if shape == "task"
        else (
            {"task_id": TASK}
            if shape == "top"
            else {"submission": {"task_id": TASK, "state": "accepted"}}
        )
    )
    world.reply(
        result=result,
        ok=not accepted_error,
        error={"code": "local_io", "message": KEY, "details": {"secret": KEY}},
    )
    world.submit(ok=not accepted_error)
    assert world.manifest()["task"]["task_id"] == TASK
    assert world.manifest()["stage"] == "submitted"
    world.submit()
    assert len(world.calls()) == 1
    journal = (
        world.project
        / ".resoloop/meshy-cli/operations"
        / (world.manifest()["operation_id"] + ".json")
    )
    assert journal.is_file()


# Catch duplicate billing after transport/output/interruption failures.
@pytest.mark.parametrize("mode", ["malformed", "sleep", "interrupt", "unknown"])
def test_unknown_submit_cannot_be_retried(world, mode):
    world.plan()
    world.env["FAKE_MODE"] = mode
    world.reply(ok=False, error={"code": "submission_unknown", "message": KEY})
    world.submit(ok=False)
    op = world.manifest()
    assert op["stage"] == "unknown"
    assert op["task"]["task_id"] is None
    world.env.pop("FAKE_MODE")
    world.submit(ok=False)
    assert len(world.calls()) == 1
    assert (
        world.project
        / ".resoloop/meshy-cli/operations"
        / (op["operation_id"] + ".json")
    ).exists()


def test_spawn_failure_and_stale_submitting_never_retry(world):
    world.plan()
    world.env["PATH"] = "/nonexistent"
    world.submit(ok=False)
    assert world.manifest()["stage"] == "unknown"
    world.submit(ok=False)
    op = world.manifest()
    op["stage"] = "submitting"
    world.manifest_path().write_text(json.dumps(op))
    world.submit(ok=False)
    assert world.manifest()["stage"] == "unknown"
    assert world.calls() == []


# Catch wait failures that lose the ID, turn failure into success, or POST on resumption.
@pytest.mark.parametrize(
    "status,ok", [("IN_PROGRESS", False), ("FAILED", True), ("CANCELED", True)]
)
def test_wait_failure_preserves_task_and_resumes_only_existing_id(world, status, ok):
    world.plan()
    world.submit()
    world.reply(
        result={"task": {"task_id": TASK, "status": status, "progress": 42}},
        ok=ok,
        error={"code": "timed_out", "message": KEY},
    )
    world.run("wait", "--operation", "asset", "--timeout", "0.1", ok=False)
    assert world.manifest()["task"]["task_id"] == TASK
    assert world.manifest()["stage"] != "succeeded"
    world.reply(
        result={"task": {"task_id": TASK, "status": "SUCCEEDED", "progress": 100}}
    )
    world.run("wait", "--operation", "asset", "--timeout", "0.1")
    assert world.manifest()["stage"] == "succeeded"
    assert sum("create" in c["args"] for c in world.calls()) == 1
    assert all(TASK in c["args"] for c in world.calls()[1:])


# Catch unvalidated partial downloads becoming conversion-ready.
def test_partial_download_preserves_files_and_retry_downloads_same_id(world):
    world.plan()
    world.submit()
    world.reply(
        result={"task": {"task_id": TASK, "status": "SUCCEEDED", "progress": 100}}
    )
    world.run("status", "--operation", "asset")
    source = world.manifest_path().parent / "source"
    entry = {
        "key": "model_urls.glb",
        "path": str(source / "generated.glb"),
        "format": "glb",
        "status": "written",
        "bytes": 12,
        "sha256": "unused",
        "error": None,
    }
    world.reply(
        result={"downloads": {"state": "partial", "files": [entry]}},
        ok=False,
        error={"code": "download_failed", "message": KEY},
    )
    world.run("download", "--operation", "asset", ok=False)
    op = world.manifest()
    assert op["downloads"]["state"] == "partial"
    assert len(op["downloads"]["files"]) == 1
    assert op["stage"] != "downloaded"
    assert (source / "generated.glb").exists()
    world.reply(result={"downloads": {"state": "completed", "files": [entry]}})
    world.run("download", "--operation", "asset")
    assert world.manifest()["stage"] == "downloaded"
    for call in world.calls()[-2:]:
        assert call["args"][7] == "download"
        assert "--all" in call["args"] and "--overwrite" in call["args"]
        assert TASK in call["args"]
    assert sum("create" in c["args"] for c in world.calls()) == 1


@pytest.mark.parametrize("bad_path", ["outside", "symlink", "missing", "no_glb"])
def test_completed_download_requires_safe_existing_glb(world, bad_path):
    world.plan()
    world.submit()
    world.reply(result={"task": {"task_id": TASK, "status": "SUCCEEDED"}})
    world.run("status", "--operation", "asset")
    source = world.manifest_path().parent / "source"
    source.mkdir()
    target = source / "generated.glb"
    if bad_path == "outside":
        target = world.project.parent / "outside.glb"
        target.write_bytes(b"fixture")
    elif bad_path == "symlink":
        target = source / "link.glb"
        target.symlink_to(world.project / ".resoloop.json")
    elif bad_path == "missing":
        target = source / "absent.glb"
    else:
        target = source / "texture.png"
        target.write_bytes(b"fixture")
    world.reply(
        result={
            "downloads": {
                "state": "completed",
                "files": [
                    {
                        "path": str(target),
                        "status": "written",
                        "format": "png" if bad_path == "no_glb" else "glb",
                    }
                ],
            }
        }
    )
    world.run("download", "--operation", "asset", ok=False)
    assert world.manifest()["stage"] != "downloaded"
    assert world.manifest()["downloads"]["state"] != "completed"


# Catch image replacement after plan and unexpected API generation knobs.
def test_image_hash_and_explicit_texture_options(world):
    image = world.project / "input.png"
    image.write_bytes(b"first image")
    world.run(
        "plan",
        "--operation",
        "asset",
        "--kind",
        "image",
        "--image",
        str(image),
        "--texture",
        "true",
    )
    image.write_bytes(b"other image")
    world.submit(ok=False)
    assert world.calls() == []
    image.write_bytes(b"first image")
    world.submit()
    args = world.calls()[0]["args"]
    payload = json.loads(args[args.index("--data") + 1])
    assert payload == {
        "ai_model": "latest",
        "should_texture": True,
        "enable_pbr": True,
        "texture_resolution": "2k",
        "remove_lighting": True,
        "image_enhancement": True,
        "ultra_mode": False,
        "target_formats": ["glb"],
    }
    assert args[args.index("--image-url") + 1] == str(image)


def test_refine_checks_successful_preview_before_paid_create(world):
    world.run(
        "plan", "--operation", "asset", "--kind", "refine", "--preview-task-id", TASK
    )
    world.reply(
        result={
            "task": {"task_id": TASK, "status": "FAILED", "type": "text-to-3d-preview"}
        }
    )
    world.submit(ok=False)
    assert world.manifest()["stage"] == "planned"
    assert all("create" not in c["args"] for c in world.calls())
    world.reply(
        result={
            "task": {
                "task_id": TASK,
                "status": "SUCCEEDED",
                "type": "text-to-3d-preview",
                "resource": "text-to-3d",
            }
        }
    )
    world.submit()
    args = world.calls()[-1]["args"]
    assert json.loads(args[args.index("--data") + 1]) == {
        "mode": "refine",
        "preview_task_id": TASK,
        "ai_model": "latest",
        "enable_pbr": True,
        "texture_resolution": "2k",
        "remove_lighting": True,
        "target_formats": ["glb"],
    }


# Catch cross-boundary writes, both user paths and CLI journal ancestors.
@pytest.mark.parametrize("name", ["../escape", "/absolute", "a/b", ".", "..", "a\\b"])
def test_operation_name_rejects_traversal(world, name):
    world.run(
        "plan", "--operation", name, "--kind", "text", "--prompt", "stone", ok=False
    )
    assert world.calls() == []
    assert not (world.project / "content").exists()


@pytest.mark.parametrize(
    "path",
    [
        "content",
        "content/generated",
        "content/generated/meshy",
        "content/generated/meshy/asset/source",
        ".resoloop",
        ".resoloop/meshy-cli",
        ".resoloop/meshy-cli/operations",
        ".resoloop/meshy-cli/operations/locks",
    ],
)
def test_directory_symlinks_rejected_before_cli(world, path):
    world.plan()
    link = world.project / path
    if not link.exists():
        link.parent.mkdir(parents=True, exist_ok=True)
    else:
        # Place the link after planning, without deleting the original tree.
        link.rename(link.with_name(link.name + "-original"))
    elsewhere = world.project.parent / "elsewhere"
    elsewhere.mkdir()
    link.symlink_to(elsewhere, target_is_directory=True)
    world.submit(ok=False)
    assert world.calls() == []
    assert list(elsewhere.iterdir()) == []


def test_input_symlink_and_invalid_project_rejected(world):
    image = world.project / "link.png"
    image.symlink_to(world.project / ".resoloop.json")
    world.run(
        "plan",
        "--operation",
        "asset",
        "--kind",
        "image",
        "--image",
        str(image),
        ok=False,
    )
    (world.project / ".resoloop.json").unlink()
    world.run(
        "plan", "--operation", "asset", "--kind", "text", "--prompt", "stone", ok=False
    )
    assert world.calls() == []


def test_concurrent_submit_cannot_send_twice(world):
    world.plan()
    world.env["FAKE_MODE"] = "sleep"
    proc = subprocess.Popen(
        world.command("submit", "--operation", "asset", "--confirm-paid"),
        env=world.env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        deadline = time.monotonic() + 2
        while not world.calls() and time.monotonic() < deadline:
            time.sleep(0.01)
        assert world.calls(), "first submit never reached CLI"
        world.submit(ok=False)
        out, err = proc.communicate(timeout=5)
        assert proc.returncode != 0
        assert KEY not in out + err
        assert len(world.calls()) == 1
        assert world.manifest()["stage"] == "unknown"
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()


# Catch inheritance of arbitrary Meshy configuration and leaks from nested CLI data.
def test_list_attach_balance_use_only_env_key_and_allowlisted_output(world):
    world.plan()
    world.env.update(
        MESHY_BASE_URL_V1="https://attacker.invalid",
        MESHY_BASE_URL_V2="https://attacker.invalid",
        MESHY_CREDENTIALS_PATH="/tmp/ambient",
        MESHY_CONFIG_DIR="/tmp/ambient",
        MESHY_LOG_LEVEL="debug",
        MESHY_DEBUG=KEY,
        MESHY_OAUTH_AUTHORIZE_URL="https://attacker.invalid",
    )
    world.reply(
        result={
            "items": [
                {
                    "task_id": TASK,
                    "status": "SUCCEEDED",
                    "progress": 100,
                    "raw": {"secret": KEY},
                    "prompt": KEY,
                }
            ],
            "unexpected": KEY,
        }
    )
    out = world.run("list", "--operation", "asset", "--resource", "text-to-3d")
    assert TASK in out.stdout
    assert "raw" not in out.stdout
    world.reply(
        result={
            "task": {
                "task_id": TASK,
                "status": "SUCCEEDED",
                "progress": 100,
                "raw": KEY,
            }
        }
    )
    world.run("attach", "--operation", "asset", "--task-id", TASK)
    assert world.manifest()["task"] == {
        "task_id": TASK,
        "status": "SUCCEEDED",
        "progress": 100,
    }
    world.reply(result={"balance": 100, "secret": KEY, "unexpected": KEY})
    out = world.run("balance", "--operation", "asset")
    assert "100" in out.stdout and "secret" not in out.stdout
    for call in world.calls():
        assert "create" not in call["args"]
        env = call["env"]
        assert env["MESHY_API_KEY"] == KEY
        assert env["MESHY_BASE_URL_V1"] == "https://api.meshy.ai/openapi/v1"
        assert env["MESHY_BASE_URL_V2"] == "https://api.meshy.ai/openapi/v2"
        assert env["MESHY_LOG_LEVEL"] == "silent"
        assert env["MESHY_CONFIG_DIR"] == str(world.project / ".resoloop/meshy-cli")
        assert not Path(env["MESHY_CREDENTIALS_PATH"]).exists()
        assert "MESHY_DEBUG" not in env and "MESHY_OAUTH_AUTHORIZE_URL" not in env


def test_key_contaminated_task_id_and_error_code_are_never_saved(world):
    world.plan()
    world.reply(
        result={"task": {"task_id": KEY, "status": KEY, "progress": 5}},
        ok=False,
        error={"code": KEY, "message": KEY, "details": {"nested": KEY}},
    )
    world.submit(ok=False)
    assert world.manifest()["stage"] == "unknown"
    assert world.manifest()["task"]["task_id"] is None
    world.submit(ok=False)
    assert len(world.calls()) == 1


# Regression: lexical relative project paths must not be appended twice.
def test_relative_project_path_is_resolved_from_cwd(world):
    command = world.command(
        "plan", "--operation", "asset", "--kind", "text", "--prompt", "stone"
    )
    command[command.index("--project") + 1] = "world"
    result = subprocess.run(
        command,
        env=world.env,
        cwd=world.project.parent,
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert world.manifest()["stage"] == "planned"


# Regression: unexpected JSON shapes are output failures, not resumable POSTs.
def test_malformed_nested_task_after_post_is_persisted_as_unknown(world):
    world.plan()
    world.reply(result={"task": {"task_id": None, "status": []}})
    world.submit(ok=False)
    assert world.manifest()["stage"] == "unknown"
    world.submit(ok=False)
    assert len(world.calls()) == 1


# Catch an edited manifest bypassing the wrapper's bounded paid payload surface.
@pytest.mark.parametrize("edit", ["payload", "resource", "image_url"])
def test_edited_manifest_cannot_add_arbitrary_generation_options(world, edit):
    world.plan()
    operation = world.manifest()
    if edit == "resource":
        operation["resource"] = "image-to-3d"
    elif edit == "image_url":
        operation["request"]["payload"]["image_url"] = "https://attacker.invalid/input"
    else:
        operation["request"]["payload"]["enable_animation"] = True
    world.manifest_path().write_text(json.dumps(operation))
    world.submit(ok=False)
    assert world.calls() == []


# Regression: a killed overwrite must not leave an old completed manifest usable.
def test_redownload_invalidates_completion_before_starting_cli(world):
    world.plan()
    world.submit()
    world.reply(result={"task": {"task_id": TASK, "status": "SUCCEEDED"}})
    world.run("status", "--operation", "asset")
    source = world.manifest_path().parent / "source"
    world.reply(
        result={
            "downloads": {
                "state": "completed",
                "files": [
                    {
                        "path": str(source / "generated.glb"),
                        "status": "written",
                        "format": "glb",
                    }
                ],
            }
        }
    )
    world.run("download", "--operation", "asset")
    assert world.manifest()["downloads"]["state"] == "completed"
    previous_calls = len(world.calls())
    world.env["FAKE_MODE"] = "sleep"
    proc = subprocess.Popen(
        world.command("download", "--operation", "asset"),
        env=world.env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        deadline = time.monotonic() + 2
        while len(world.calls()) == previous_calls and time.monotonic() < deadline:
            time.sleep(0.01)
        assert len(world.calls()) > previous_calls
        assert world.manifest()["downloads"]["state"] != "completed"
        assert world.manifest()["stage"] != "downloaded"
    finally:
        proc.communicate(timeout=5)


# A v1 error can include an ID while task itself is null; that is not a preview proof.
def test_refine_null_task_never_crashes_or_creates(world):
    world.run(
        "plan", "--operation", "asset", "--kind", "refine", "--preview-task-id", TASK
    )
    world.reply(result={"task": None, "task_id": TASK})
    world.submit(ok=False)
    assert all("create" not in call["args"] for call in world.calls())
    assert world.manifest()["stage"] == "planned"


# Corrupt local state must not disclose tracebacks or allow paid calls.
def test_nonstring_operation_uuid_is_rejected_cleanly(world):
    world.plan()
    operation = world.manifest()
    operation["operation_id"] = 123
    world.manifest_path().write_text(json.dumps(operation))
    world.submit(ok=False)
    assert world.calls() == []


# Untrusted numeric metadata cannot erase the accepted ID during extraction.
def test_oversized_progress_does_not_lose_accepted_task(world):
    world.plan()
    world.reply(
        result={"task": {"task_id": TASK, "status": "PENDING", "progress": 10**400}}
    )
    world.submit()
    assert world.manifest()["task"]["task_id"] == TASK
    assert world.manifest()["task"]["progress"] is None
    world.submit()
    assert len(world.calls()) == 1
