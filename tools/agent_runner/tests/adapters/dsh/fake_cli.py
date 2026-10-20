"""Headless-shaped fake CLI; validates managed flags, writes private artifacts."""

import json
import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[5]))
from tools.test_support.dsh import write_session


def _home_cache(home: Path) -> None:
    # Shapes tools leave in HOME: uv cache links (to a file, a sibling and a
    # directory outside HOME), a FIFO, and Go's read-only module cache.
    entry = home / ".cache" / "uv" / "archive-v0" / "entry"
    (entry / "lib").mkdir(parents=True)
    (entry / "bin").mkdir()
    (entry / "bin" / "python").symlink_to(sys.executable)
    (entry / "lib64").symlink_to("lib")
    (home / ".cache" / "checkout").symlink_to(Path.cwd())
    os.mkfifo(home / "agent.fifo")
    module = home / "go" / "pkg" / "mod" / "example.com" / "m@v1"
    module.mkdir(parents=True)
    (module / "go.mod").write_text("module example.com/m\n")
    (module / "go.mod").chmod(0o444)
    module.chmod(0o555)
    module.parent.chmod(0o555)


_PYTEST_CASE = '''"""Synthetic passing test; no credentials or external files are read."""

import os
from pathlib import Path


def test_tmp_path(tmp_path: Path) -> None:
    (tmp_path / "clean.txt").write_text("synthetic clean fixture\\n")
    if os.environ["FAKE_PYTEST_FIXTURES"] == "1":
        # Like the repository's safety fixtures: links out of tmp_path, a FIFO and a hard link pair.
        outside = Path(os.environ["FAKE_OUTSIDE"])
        (tmp_path / "outside-file").symlink_to(outside / "README.md")
        (tmp_path / "outside-dir").symlink_to(outside)
        os.mkfifo(tmp_path / "fixture.fifo")
        (tmp_path / "original.json").write_text("synthetic linked fixture\\n")
        os.link(tmp_path / "original.json", tmp_path / "linked.json")
    assert (tmp_path / "clean.txt").is_file()
'''


def _run_pytest(fixtures: bool) -> dict[str, object]:
    # Real pytest with its default retention: pytest-current and <test>current links stay in TMPDIR.
    case = Path(tempfile.mkdtemp(prefix="pytest-input-"))
    (case / "pytest.ini").write_text("[pytest]\n")
    (case / "probe_case.py").write_text(_PYTEST_CASE)
    if fixtures:
        (Path.cwd() / "sentinel-link").symlink_to(Path.cwd() / "README.md")
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "-c",
            str(case / "pytest.ini"),
            "-p",
            "no:cacheprovider",
            str(case / "probe_case.py"),
        ],
        env={
            **os.environ,
            "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
            "FAKE_PYTEST_FIXTURES": "1" if fixtures else "0",
            "FAKE_OUTSIDE": str(Path.cwd()),
        },
        capture_output=True,
        text=True,
        check=False,
    )
    return {"exit": completed.returncode, "summary": completed.stdout.strip().splitlines()[-1:]}


def main() -> int:
    mode = sys.argv[1]
    args = sys.argv[2:]
    assert args[:2] == ["--profile", "headless"]
    assert args[-2:] == ["--json", "-"]
    prompt = sys.stdin.read()
    patch = json.loads(Path(args[args.index("--patch") + 1]).read_text())
    rows = {row["id"]: row for row in patch}
    route = next(iter(rows["llm-pi-ai"]["config"]["providers"].values()))
    key = os.environ.get(route["apiKeyEnv"], "")
    state = Path(os.environ["DSH_HOME"])
    home = Path(os.environ["HOME"])
    capture: dict[str, object] = {
        "prompt": prompt,
        "home": str(home),
        "dsh_home": str(state),
        "tmpdir": os.environ.get("TMPDIR"),
        "telemetry": os.environ["DSH_TELEMETRY_MODE"],
        "depth": os.environ["AGENT_RUNNER_DEPTH"],
        "parent_model": os.environ.get("PI_MODEL"),
        "key_present": bool(key),
    }
    if mode == "parent-input":
        from tools.agent_runner.dsh_sandbox import BASE

        parameters = json.loads(prompt.rsplit("```json\n", 1)[1].split("\n```", 1)[0])
        snapshot = Path(parameters["parent_pr_data"]["path"])
        bundle = snapshot.with_name("objects.bundle")
        capture["parent_visible"] = snapshot.is_file() and bundle.is_file()
        if capture["parent_visible"]:
            document = json.loads(snapshot.read_text())
            capture["bundle"] = bundle.read_text()
            denied = []
            for path in (snapshot, bundle, Path(document["target"]["parent_root"]) / ".gitignore"):
                try:
                    path.write_text("changed")
                    denied.append(False)
                except OSError:
                    denied.append(True)
            capture["parent_writes_denied"] = denied
            neighbor = Path(parameters["probe_neighbor"])
            try:
                neighbor.write_text("native shadow")
            except OSError:
                pass
            target_script = Path(parameters["probe_helper"])
            program = (
                "from pathlib import Path; import importlib.util; "
                f"s = importlib.util.spec_from_file_location('parent_root_probe', {str(target_script)!r}); "
                "m = importlib.util.module_from_spec(s); s.loader.exec_module(m); "
                f"assert m.require_parent_root(Path({document['target']['parent_root']!r})); "
                f"assert Path({str(snapshot)!r}).is_file(); "
                f"assert Path({str(bundle)!r}).read_text() == 'fixture bundle'; "
                f"Path({str(neighbor)!r}).write_text('helper shadow')"
            )
            readonly_probe = (
                "for value in " + repr([str(snapshot), str(bundle), str(Path(document["target"]["parent_root"]) / ".gitignore")])
                + ":\n try:\n  Path(value).write_text('changed')\n"
                + " except OSError:\n  continue\n raise AssertionError('parent input was writable')\n"
            )
            program += "; exec(" + repr(readonly_probe) + ")"
            work = str(Path.cwd())
            helper = subprocess.run(
                [*rows["sandbox"]["config"]["runnerCommand"], *BASE, "--tmpfs", "/tmp", "--bind", work, work,
                 "--", sys.executable, "-c", program], capture_output=True, text=True, check=False,
            )
            capture["helper_exit"] = helper.returncode
            capture["helper_error"] = helper.stderr
    if mode == "native-fence":
        attempt = state.parent.parent
        denied: dict[str, bool] = {}
        for path in (attempt / "request.json", attempt / "receipt.json", Path(args[args.index("--patch") + 1])):
            try:
                path.write_text("forged")
                denied[path.name] = False
            except OSError:
                denied[path.name] = True
        target = Path(os.environ["FAKE_HOST_TARGET"])
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            target.write_text("changed")
        except OSError:
            pass
        for name, path in (("scratch", attempt / "review-scratch"), ("exports", state.parent / "tmp" / "exports")):
            (path / "native.txt").write_text("native output")
            capture[name] = str(path)
        try:
            os.link(Path(args[args.index("--patch") + 1]), state.parent / "tmp" / "patch-link")
            capture["hardlink_denied"] = False
        except OSError:
            capture["hardlink_denied"] = True
        capture["denied"] = denied
        host_proc = Path("/proc") / os.environ["FAKE_HOST_PID"]
        capture["host_proc_visible"] = (host_proc / "root").exists()
        from tools.agent_runner.dsh_sandbox import BASE

        work = str(Path.cwd())
        profile = [*BASE, "--tmpfs", "/tmp", "--bind", work, work, "--"]
        program = (
            "from pathlib import Path; import subprocess; "
            f"assert Path({str(attempt / 'request.json')!r}).is_file(); "
            f"Path({str(attempt / 'review-scratch' / 'helper.txt')!r}).write_text('helper output'); "
            "subprocess.run(['git','status','--porcelain'],check=True,capture_output=True)"
        )
        helper = subprocess.run(
            [*rows["sandbox"]["config"]["runnerCommand"], *profile, sys.executable, "-c", program],
            capture_output=True, text=True, check=False,
        )
        capture["helper_exit"] = helper.returncode
        capture["helper_error"] = helper.stderr
    if mode in {"spill", "hang"}:
        # Like DSH's subprocess-local spill of >64 KB command output under tmpdir().
        spill = Path(tempfile.mkdtemp(prefix="dsh-subprocess-")) / "output.log"
        spill.write_text("env dump\n" + "x" * 70000 + f"\nAPI_KEY={key}\n")
        capture["spill"] = str(spill)
    if mode in {"pytest", "pytest-fixtures"}:
        capture["pytest"] = _run_pytest(mode == "pytest-fixtures")
    (state / "capture.json").write_text(json.dumps(capture, ensure_ascii=False))
    if mode == "home-link":
        home.rmdir()
        home.symlink_to(Path.cwd())
    else:
        (home / ".netrc").write_text(f"password {key}\n")
    if mode == "home-cache":
        _home_cache(home)
    if mode == "symlink":
        (state / "foreign-link").symlink_to(Path.cwd() / "README.md")
    elif mode == "fifo":
        os.mkfifo(state / "session.fifo")
    elif mode == "hardlink":
        original = state / "original.json"
        original.write_text("synthetic content")
        os.link(original, original.with_name("linked.json"))
    elif mode == "tmp-symlink":
        (Path(os.environ["TMPDIR"]) / "foreign-link").symlink_to(Path.cwd() / "README.md")
    elif mode == "tmp-fifo":
        os.mkfifo(Path(os.environ["TMPDIR"]) / "spill.fifo")
    elif mode == "tmp-hardlink":
        # Like pytest fixtures left in TMPDIR: a pair in one directory and a name in a child directory.
        scratch = Path(os.environ["TMPDIR"])
        original = scratch / "original.json"
        original.write_text(f"synthetic content {key}\n")
        os.link(original, scratch / "linked.json")
        (scratch / "nested").mkdir()
        os.link(original, scratch / "nested" / "shared.json")
    elif mode == "tmp-link":
        # TMPDIR itself now resolves into the checkout, which holds a link of its own.
        scratch = Path(os.environ["TMPDIR"])
        target = Path.cwd() / "scratch"
        target.mkdir()
        (target / "keep-link").symlink_to(Path.cwd() / "README.md")
        scratch.rmdir()
        scratch.symlink_to(target)
    elif mode == "root-link":
        # The whole runtime root now resolves into the checkout, which has its own home/ and tmp/.
        (Path.cwd() / "home").mkdir()
        (Path.cwd() / "home" / "keep.txt").write_text("keep\n")
        (Path.cwd() / "tmp").mkdir()
        (Path.cwd() / "tmp" / "keep-link").symlink_to(Path.cwd() / "README.md")
        home.parent.rename(home.parent.with_name("dsh-moved"))
        home.parent.symlink_to(Path.cwd())
    else:
        (state / "session.jsonl").write_text(json.dumps({"tool": key}) + "\n")
    if mode in {"hang", "descendant"}:
        child = subprocess.Popen(
            [
                sys.executable, "-c",
                "import signal,time;signal.signal(signal.SIGTERM,signal.SIG_IGN);time.sleep(600)",
                str(Path.cwd() / "child.pid"),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        (Path.cwd() / "child.pid").write_text(str(child.pid))
        if mode == "hang":
            signal.signal(signal.SIGTERM, signal.SIG_IGN)
            time.sleep(600)
    if mode != "missing-session":
        selection = rows["agent-default-model"]["config"]
        session = write_session(
            state, Path.cwd(), session_id="fake-observed", provider=selection["provider"],
            model=selection["model"], effort=selection.get("reasoningEffort"),
        )
        if mode == "mismatched-session":
            records = [json.loads(line) for line in session.read_text().splitlines()]
            records[-1]["data"]["message"]["source"]["model"] = "different-model"
            session.write_text("".join(json.dumps(row) + "\n" for row in records))
    reason: dict[str, object] = {"kind": "completed"}
    text = json.dumps({"ok": True, "prompt": prompt, "secret": key})
    if mode == "github-token":
        token = os.environ.get("GH_TOKEN")
        text = json.dumps({"github_token": token, "unlisted": os.environ.get("UNLISTED_SECRET")})
        (state / "session.jsonl").write_text(json.dumps({"tool": token}) + "\n")
    if mode == "auth":
        reason = {"kind": "error", "error": {"code": "MISSING_CREDENTIAL", "message": "missing"}}
        text = ""
    events: list[dict[str, object]] = [
        {"type": "session", "sessionId": "fake-observed", "cwd": str(Path.cwd())},
        {"type": "status", "phase": "turn_start", "turn": 1},
    ]
    if mode.startswith("ptc-"):
        # Actual fixed-version producer output; only disposable stack paths normalized.
        cases = json.loads(Path(__file__).with_name("ptc_tool_results.json").read_text())
        events.append(cases[mode.removeprefix("ptc-")])
    denials = {
        "approval": 'Error: the user rejected tool "bash"',
        "approval-program": (
            'Error: the user rejected escalating this program to "danger-full-access"; '
            "it stays denied, so stop and explain instead of working around it"
        ),
    }
    if mode in denials:
        events.append({"type": "tool_result", "callId": "call", "status": "error", "result": denials[mode]})
    read_errors = {
        "read-402-lines": 'Error: offset 2001 is out of range for "x.py" (402 lines)',
        "read-401-lines": 'Error: offset 2001 is out of range for "x.py" (401 lines)',
        "read-403-lines": 'Error: offset 2001 is out of range for "x.py" (403 lines)',
        "read-401-filename": 'Error: ENOENT: no such file or directory, open "401.py"',
        "read-403-filename": 'Error: ENOENT: no such file or directory, open "403.py"',
        "read-approval-cancelled": 'Error: offset 2001 is out of range for "approval-cancelled.md" (402 lines)',
        "read-approval-unavailable": 'Error: ENOENT: no such file or directory, open "approval-unavailable.txt"',
        "read-approval-rejected": 'Error: ENOENT: no such file or directory, open "approval-rejected.md"',
        "read-requires-approval": 'Error: ENOENT: no such file or directory, open "notes/requires approval.md"',
        "read-approvals-path": 'Error: ENOENT: no such file or directory, open "/approvals/cancelled.json"',
    }
    if mode in read_errors:
        events.extend(
            [
                {"type": "tool_call", "callId": "read-1", "tool": "read", "input": {}},
                {"type": "tool_result", "callId": "read-1", "status": "error", "result": read_errors[mode]},
            ]
        )
    events.extend(
        [
            {"type": "status", "phase": "turn_end", "turn": 1, "reason": reason},
            {"type": "final", "text": text},
        ]
    )
    for event in events:
        print(json.dumps(event, ensure_ascii=False), flush=True)
    if mode == "malformed":
        print("broken {")
    return 1 if mode in {"auth", "nonzero"} else 0


if __name__ == "__main__":
    sys.exit(main())
