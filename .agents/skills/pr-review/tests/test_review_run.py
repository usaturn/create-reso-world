from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import pytest

from tools.agent_runner.models import Attempt, BatchResult, Identity, Request, Result
from tools.test_support.dsh import write_session

SCRIPT = Path(__file__).parents[1] / "scripts" / "review_run.py"
ROOT = Path(__file__).resolve().parents[4]
SPEC = importlib.util.spec_from_file_location("review_run", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
review_run = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(review_run)
REPOSITORY = "example/syncer"


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args], check=True, capture_output=True, text=True
    ).stdout.strip()


@pytest.fixture
def prepared(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    monkeypatch.delenv("CODEX_THREAD_ID", raising=False)
    parent, source, remote, caller = (
        tmp_path / name for name in ("parent", "source", "remote.git", "caller")
    )
    for checkout in (parent, source):
        subprocess.run(
            ["git", "init", "-b", "main", str(checkout)],
            check=True,
            capture_output=True,
        )
        git(checkout, "config", "user.name", "Test")
        git(checkout, "config", "user.email", "test@example.com")
        (checkout / ".gitignore").write_text("/reviews/\n", encoding="utf-8")
        git(checkout, "add", ".gitignore")
        git(checkout, "commit", "-m", "base")
    git(
        parent,
        "remote",
        "add",
        "origin",
        "https://github.com/usaturn/create-reso-world.git",
    )
    git(source, "switch", "-c", "feature")
    (source / "README.md").write_text("a harmless fixture\n", encoding="utf-8")
    git(source, "add", "README.md")
    git(source, "commit", "-m", "PR change")
    head = git(source, "rev-parse", "HEAD")
    subprocess.run(
        ["git", "init", "--bare", str(remote)], check=True, capture_output=True
    )
    git(source, "push", str(remote), "main", "feature", "feature:refs/pull/7/head")
    git(source, "remote", "add", "origin", f"https://github.com/{REPOSITORY}.git")
    # Redirect fetch transport only; remote identity checks must see the real URL.
    real_git = subprocess.run(
        ["which", "git"], check=True, capture_output=True, text=True
    ).stdout.strip()
    binary = tmp_path / "transport-bin"
    binary.mkdir()
    wrapper = binary / "git"
    wrapper.write_text(
        f"#!{sys.executable}\n"
        + f"REAL_GIT = {real_git!r}\n"
        + """import os, sys
args = sys.argv[1:]
if 'fetch' in args:
    args = [os.environ.get('FAKE_GIT_ORIGIN_REMOTE', os.environ['FAKE_GIT_REMOTE']) if value == 'origin'
        else os.environ['FAKE_GIT_REMOTE'] if value == 'upstream' or value == os.environ['FAKE_GIT_URL']
        else value for value in args]
os.execv(REAL_GIT, [REAL_GIT, *args])
"""
    )
    wrapper.chmod(0o755)
    monkeypatch.setenv("FAKE_GIT_REMOTE", str(remote))
    monkeypatch.setenv("FAKE_GIT_URL", f"https://github.com/{REPOSITORY}.git")
    monkeypatch.setenv("PATH", f"{binary}:{os.environ['PATH']}")
    target = review_run.workspace.load_review_target()

    def live_pr(repository: str, number: int, *, runner: Any = None) -> Any:
        assert (repository, number) == (REPOSITORY, 7)
        return target.PullRequest(
            repository,
            number,
            f"https://github.com/{repository}/pull/{number}",
            "feature",
            head,
            repository,
            "main",
            "open",
            f"https://github.com/{repository}.git",
        )

    def parent_root() -> Path:
        return parent

    monkeypatch.setattr(target, "fetch_pull_request", live_pr)
    monkeypatch.setattr(target, "default_parent_root", parent_root)
    caller.mkdir()
    monkeypatch.chdir(caller)
    request = Request(
        run_id="run-568",
        request_id="request-7",
        agent_id="fixture-reviewer",
        role="inspect",
        work_dir=caller,
        prompt="review",
        deadline_seconds=600.0,
        result_shape="json",
    )
    request_path = tmp_path / "request.json"
    request_path.write_text(request.model_dump_json(), encoding="utf-8")
    comments = tmp_path / "comments.json"
    comments.write_text("[]", encoding="utf-8")
    argv = [
        "prepare",
        "--pr",
        f"https://github.com/{REPOSITORY}/pull/7",
        "--runtime",
        "claude-code",
        "--model-name",
        "observed-model",
        "--request",
        str(request_path),
        "--source-root",
        str(source),
        "--records-comments",
        str(comments),
        "--temp-root",
        str(tmp_path / "sessions"),
    ]
    args = review_run.parser().parse_args(argv)
    return {
        "args": args,
        "argv": argv,
        "parent": parent,
        "source": source,
        "remote": remote,
        "head": head,
        "request_path": request_path,
        "comments": comments,
        "caller": caller,
    }


def parent_input(
    prepared: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> dict[str, Any]:
    args = review_run.parser().parse_args(
        [
            "prepare-parent",
            "--pr",
            prepared["args"].pr,
            "--source-root",
            str(prepared["source"]),
            "--records-comments",
            str(prepared["comments"]),
            "--output-dir",
            str(tmp_path / "parent-input"),
        ]
    )
    args.requirements = {
        "pr": {"body": "日本語のPR本文\n", "closingIssuesReferences": []},
        "issues": [],
    }
    descriptor = review_run.prepare_parent(args)
    request = Request.model_validate_json(prepared["request_path"].read_text())
    request.prompt = (
        "日本語の依頼\n```json\n"
        + json.dumps({"parent_pr_data": descriptor})
        + "\n```\n"
    )
    prepared["request_path"].write_text(request.model_dump_json())
    prepared["args"].runtime = "dsh"
    prepared["args"].model_name = None
    prepared["args"].temp_root = str(prepared["request_path"].parent / "dsh" / "tmp")
    home = tmp_path / "identity"
    write_session(
        home, prepared["caller"], provider="commandcode", model="actual/model"
    )
    for key, value in {
        "DSH_HOME": str(home),
        "DSH_SESSION_ID": "session-test",
        "DSH_SHELL": "1",
        "DSH_PROFILE": "headless",
    }.items():
        monkeypatch.setenv(key, value)
    for key in ("GH_TOKEN", "GITHUB_TOKEN"):
        monkeypatch.delenv(key, raising=False)
    return descriptor


def staged_batch(prepared: dict[str, Any], staged: dict[str, Any]) -> BatchResult:
    request = Request.model_validate_json(prepared["request_path"].read_text())
    events = [
        {"type": "session", "sessionId": "session-test", "cwd": str(prepared["caller"])},
        {"type": "status", "phase": "turn_start", "turn": 1},
    ]
    exports = prepared["request_path"].parent / "dsh/tmp/exports"
    for index, name in enumerate(("review.md", "findings.json")):
        events.extend([
            {"type": "tool_call", "callId": f"export-{index}", "tool": "write", "input": {"file_path": str(exports / name)}},
            {"type": "tool_result", "callId": f"export-{index}", "status": "completed", "result": "written"},
        ])
    events.extend([
        {"type": "status", "phase": "turn_end", "turn": 1, "reason": {"kind": "completed"}},
        {"type": "final", "text": json.dumps(staged)},
    ])
    (prepared["request_path"].parent / "stdout.log").write_text("".join(json.dumps(event) + "\n" for event in events))
    return BatchResult(
        run_id=request.run_id,
        state="success",
        assignments={"inspect": [request.agent_id]},
        results=[
            Result(
                request_id=request.request_id,
                role="inspect",
                requested_agent=request.agent_id,
                actual_agent=request.agent_id,
                state="success",
                attempts=[
                    Attempt(
                        agent_id=request.agent_id,
                        state="success",
                        identity=Identity(
                            provider="commandcode",
                            model="actual/model",
                            effort="high",
                            session_id="session-test",
                        ),
                        exit_code=0,
                        elapsed_seconds=1.0,
                        stop_confirmed=True,
                        work_dir=prepared["caller"],
                        request_path=prepared["request_path"],
                        payload=staged,
                    )
                ],
            )
        ],
        outside_changes=[],
        elapsed_seconds=1.0,
        artifact_dir=prepared["request_path"].parent,
    )


def test_parent_bundle_child_needs_no_github_and_parent_saves(
    prepared: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    parent_input(prepared, tmp_path, monkeypatch)
    target = review_run.workspace.load_review_target()
    live = target.fetch_pull_request

    def unavailable(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("child must not query GitHub")

    monkeypatch.setattr(target, "fetch_pull_request", unavailable)
    monkeypatch.setattr(review_run, "command", unavailable)
    # Even removing the PR's remote ref must not break the local bundled input.
    git(prepared["remote"], "update-ref", "-d", "refs/pull/7/head")
    result = review_run.prepare(prepared["args"])
    assert result["status"] == "prepared", result.get("reason")
    assert result["base"] == git(prepared["source"], "rev-parse", "main")
    mark_reviewed(result)
    staged = review_run.complete(argparse.Namespace(state=result["state_file"]))
    assert staged["status"] == "staged", staged
    assert not Path(result["destination"]).exists()
    assert Path(result["worktree"]).exists()
    monkeypatch.setattr(target, "fetch_pull_request", live)
    batch = staged_batch(prepared, staged)
    review_run.finalize_parent_batch(batch)
    completed = batch.results[0].attempts[0].payload
    assert isinstance(completed, dict) and completed["status"] == "success", completed.get("reason")
    assert completed["cleanup"] == "success"
    assert Path(str(completed["review_file"])).is_file()
    assert Path(str(completed["findings_file"])).is_file()
    assert not Path(result["worktree"]).exists()


@pytest.mark.parametrize("notation", ["absolute", "relative", "absolute_dotdot"])
def test_dsh_request_path_notation_preserves_parent_save(
    prepared: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str], notation: str,
) -> None:
    # Regression: a valid relative Request must use the same outbox and binding
    # as its absolute spelling, through the actual CLI and parent promotion.
    parent_input(prepared, tmp_path, monkeypatch)
    request_path = prepared["request_path"]
    value = {
        "absolute": str(request_path),
        "relative": "../request.json",
        "absolute_dotdot": str(prepared["caller"] / ".." / "request.json"),
    }[notation]
    code = review_run.main([
        "prepare", "--pr", prepared["args"].pr, "--runtime", "dsh", "--request", value,
    ])
    result = json.loads(capsys.readouterr().out)
    assert code == 0 and result["status"] == "prepared", result
    state = json.loads(Path(result["state_file"]).read_text())
    assert state["run_context"]["request_path"] == str(request_path)
    assert Path(result["draft"]).parent == tmp_path / "dsh/tmp/exports"
    mark_reviewed(result)
    staged = review_run.complete(argparse.Namespace(state=result["state_file"]))
    assert staged["status"] == "staged", staged
    batch = staged_batch(prepared, staged)
    review_run.finalize_parent_batch(batch)
    completed = batch.results[0].attempts[0].payload
    assert isinstance(completed, dict) and completed["status"] == "success", completed
    assert completed["cleanup"] == "success"
    assert Path(completed["review_file"]).is_file()
    assert Path(completed["findings_file"]).is_file()
    assert not Path(result["worktree"]).exists()


@pytest.mark.parametrize("kind", [
    "symlink", "hardlink", "fifo", "directory_symlink", "symlink_dotdot",
    "missing_dotdot", "file_dotdot",
])
def test_dsh_request_rejects_unsafe_paths_before_creating_artifacts(
    prepared: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    kind: str,
) -> None:
    # Normalization must not conceal an unsafe component, and neither the
    # initial read nor the error-response binding read may block on a FIFO.
    parent_input(prepared, tmp_path, monkeypatch)
    original = prepared["request_path"]
    candidate = tmp_path / "unsafe-request.json"
    if kind == "symlink":
        candidate.symlink_to(original)
    elif kind == "hardlink":
        os.link(original, candidate)
    elif kind == "fifo":
        os.mkfifo(candidate)
    else:
        component = tmp_path / "component"
        if kind in {"directory_symlink", "symlink_dotdot"}:
            component.symlink_to(prepared["caller"], target_is_directory=True)
        elif kind == "file_dotdot":
            component.write_text("not a directory")
        candidate = component / ".." / "request.json"
        if kind == "directory_symlink":
            (prepared["caller"] / "request.json").write_bytes(original.read_bytes())
            candidate = component / "request.json"
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "prepare", "--pr", prepared["args"].pr,
         "--runtime", "dsh", "--request", str(candidate)],
        cwd=prepared["caller"], capture_output=True, text=True, timeout=5,
    )
    assert result.returncode == 1, result.stdout
    outcome = json.loads(result.stdout)
    assert outcome["status"] == "failed" and outcome["run_record"] is None
    assert not (tmp_path / "dsh").exists()
    assert not (prepared["parent"] / "reviews").exists()


@pytest.mark.parametrize("linked", [False, True], ids=["relative", "symlink"])
def test_other_runtime_request_path_acceptance_is_unchanged(
    prepared: dict[str, Any], capsys: pytest.CaptureFixture[str], linked: bool,
) -> None:
    # DSH's stricter input boundary must not change other runtimes' existing
    # handling of a relative Request or a caller-owned symbolic link to one.
    value = "../request.json"
    if linked:
        (prepared["caller"] / "request-link.json").symlink_to(prepared["request_path"])
        value = "request-link.json"
    argv = prepared["argv"].copy()
    argv[argv.index("--request") + 1] = value
    code = review_run.main(argv)
    result = json.loads(capsys.readouterr().out)
    assert code == 0 and result["status"] == "prepared", result
    mark_reviewed(result)
    completed = review_run.complete(argparse.Namespace(state=result["state_file"]))
    assert completed["status"] == "success" and completed["cleanup"] == "success", completed
    assert Path(completed["review_file"]).is_file()
    assert Path(completed["findings_file"]).is_file()


def test_parent_bundle_from_shallow_checkout_is_complete(
    prepared: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = prepared["source"]
    for index in range(2):
        (source / "README.md").write_text(f"change {index}\n")
        git(source, "add", "README.md")
        git(source, "commit", "-m", f"change {index}")
    prepared["head"] = git(source, "rev-parse", "HEAD")
    git(
        source,
        "push",
        str(prepared["remote"]),
        "+feature:feature",
        "+feature:refs/pull/7/head",
    )
    target = review_run.workspace.load_review_target()
    original = target.fetch_pull_request

    def current_pr(repository: str, number: int, **kwargs: Any) -> Any:
        return original(repository, number, **kwargs)._replace(
            head_sha=prepared["head"]
        )

    monkeypatch.setattr(target, "fetch_pull_request", current_pr)
    shallow = tmp_path / "shallow-source"
    subprocess.run(
        [
            "git",
            "clone",
            "--quiet",
            "--depth=1",
            "--no-single-branch",
            source.as_uri(),
            str(shallow),
        ],
        check=True,
    )
    git(shallow, "remote", "set-url", "origin", f"https://github.com/{REPOSITORY}.git")
    before = (shallow / ".git" / "shallow").read_bytes()
    prepared["source"] = shallow
    parent_input(prepared, tmp_path, monkeypatch)
    result = review_run.prepare(prepared["args"])
    assert result["status"] == "prepared", result.get("reason")
    assert (shallow / ".git" / "shallow").read_bytes() == before
    mark_reviewed(result)
    staged = review_run.complete(argparse.Namespace(state=result["state_file"]))
    batch = staged_batch(prepared, staged)
    review_run.finalize_parent_batch(batch)
    payload = batch.results[0].attempts[0].payload
    assert isinstance(payload, dict) and payload["status"] == "success", payload


def test_parent_preparation_collects_pr_and_referenced_issues(
    prepared: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def github(argv: list[str]) -> str:
        if argv[:3] == ["gh", "pr", "view"]:
            return json.dumps(
                {
                    "body": "Closes #42\n日本語\n背景色は `#999999` にする",
                    "closingIssuesReferences": [
                        {
                            "number": 42,
                            "url": f"https://github.com/{REPOSITORY}/issues/42",
                        }
                    ],
                }
            )
        if argv[:4] == ["gh", "issue", "view", "42"]:
            return json.dumps(
                {"body": "実入力の条件\n第二行", "comments": [{"body": "承認済み"}]}
            )
        if argv[:4] == ["gh", "issue", "view", "999999"]:
            raise review_run.workspace.WorkspaceError(
                "gh failed: GraphQL: Could not resolve to an issue"
            )
        raise AssertionError(argv)

    monkeypatch.setattr(review_run, "command", github)
    args = review_run.parser().parse_args(
        [
            "prepare-parent",
            "--pr",
            prepared["args"].pr,
            "--source-root",
            str(prepared["source"]),
            "--records-comments",
            str(prepared["comments"]),
            "--output-dir",
            str(tmp_path / "requirements"),
        ]
    )
    descriptor = review_run.prepare_parent(args)
    snapshot = json.loads(Path(descriptor["path"]).read_text())
    assert (
        snapshot["requirements"]["pr"]["body"]
        == "Closes #42\n日本語\n背景色は `#999999` にする"
    )
    assert snapshot["requirements"]["issues"][0]["body"] == "実入力の条件\n第二行"
    assert snapshot["requirements"]["issues"][0]["repository"] == REPOSITORY
    # 色の #数字 は Issue として読めない。親準備は止めず、理由付きの未取得として子へ渡す
    assert [
        (item["repository"], item["number"])
        for item in snapshot["requirements"]["unavailable"]
    ] == [(REPOSITORY, 999999)]


def fake_requirements_gh(
    pr: Any, issues: dict[tuple[str, str], Any]
) -> tuple[Any, list[list[str]]]:
    """parent_requirements の gh。値が例外なら送出し、文字列ならそのまま、それ以外は JSON にして返す。"""
    calls: list[list[str]] = []

    def answer(value: Any) -> str:
        if isinstance(value, Exception):
            raise value
        return value if isinstance(value, str) else json.dumps(value)

    def github(argv: list[str]) -> str:
        calls.append(argv)
        if argv[:3] == ["gh", "pr", "view"]:
            return answer(pr)
        if argv[:3] == ["gh", "issue", "view"]:
            return answer(issues[(argv[argv.index("--repo") + 1], argv[3])])
        raise AssertionError(argv)

    return github, calls


ACCEPTED_BODY = (
    "日本語の説明\n複数行の本文\nCloses #42\nother/repo#333333 は別リポジトリの裸参照\n"
)
ISSUE_42 = {"body": "受け入れ条件\n第二行", "comments": [{"body": "承認済み"}]}


@pytest.mark.parametrize(
    ("addition", "failing", "answer"),
    [
        (
            "背景色は `#333333` にする\n",
            (REPOSITORY, "333333"),
            review_run.workspace.WorkspaceError(
                "gh failed: GraphQL: Could not resolve (token ghp_secretvalue)"
            ),
        ),
        (
            "参照: https://github.com/usaturn/private-nonexistent-repo/issues/1\n",
            ("usaturn/private-nonexistent-repo", "1"),
            review_run.workspace.WorkspaceError(
                "gh failed: GraphQL: Could not resolve to a Repository"
            ),
        ),
        ("関連 #77\n", (REPOSITORY, "77"), "not JSON"),
        ("関連 #77\n", (REPOSITORY, "77"), {"body": 5, "comments": []}),
        ("関連 #77\n", (REPOSITORY, "77"), {"body": "本文だけ"}),
        ("関連 #77\n", (REPOSITORY, "77"), {"comments": []}),
        ("関連 #77\n", (REPOSITORY, "77"), ["not", "an", "object"]),
    ],
    ids=[
        "color",
        "inaccessible-url",
        "not-json",
        "body-type",
        "comments-missing",
        "body-missing",
        "not-object",
    ],
)
def test_parent_requirements_unavailable_issue_does_not_abort(
    monkeypatch: pytest.MonkeyPatch,
    addition: str,
    failing: tuple[str, str],
    answer: Any,
) -> None:
    github, calls = fake_requirements_gh(
        {"body": ACCEPTED_BODY + addition, "closingIssuesReferences": []},
        {(REPOSITORY, "42"): ISSUE_42, failing: answer},
    )
    monkeypatch.setattr(review_run, "command", github)
    requirements = review_run.parent_requirements(
        f"https://github.com/{REPOSITORY}/pull/7", REPOSITORY, 7
    )
    assert requirements["pr"]["body"] == ACCEPTED_BODY + addition
    assert requirements["issues"] == [
        {"repository": REPOSITORY, "number": 42, **ISSUE_42}
    ]
    [unavailable] = requirements["unavailable"]
    assert (unavailable["repository"], str(unavailable["number"])) == failing
    assert isinstance(unavailable["reason"], str) and unavailable["reason"]
    # gh の出力は理由に写さない（秘密値が混ざりうる）
    assert "ghp_secretvalue" not in json.dumps(requirements)
    # 別リポジトリの裸参照 owner/repo#N は取得しない
    assert sorted(
        call[3] for call in calls if call[:3] == ["gh", "issue", "view"]
    ) == sorted(["42", failing[1]])


def test_parent_requirements_empty_nullable_bodies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    closing = [{"number": 42, "url": f"https://github.com/{REPOSITORY}/issues/42"}]
    github, _calls = fake_requirements_gh(
        {"body": None, "closingIssuesReferences": closing},
        {(REPOSITORY, "42"): {"body": None, "comments": [{"body": "コメント"}]}},
    )
    monkeypatch.setattr(review_run, "command", github)
    requirements = review_run.parent_requirements(
        f"https://github.com/{REPOSITORY}/pull/7", REPOSITORY, 7
    )
    assert requirements["pr"] == {"body": "", "closingIssuesReferences": closing}
    assert requirements["issues"] == [
        {
            "repository": REPOSITORY,
            "number": 42,
            "body": "",
            "comments": [{"body": "コメント"}],
        }
    ]
    assert requirements["unavailable"] == []


@pytest.mark.parametrize(
    "pr",
    [
        review_run.workspace.WorkspaceError("gh failed: API unavailable"),
        "not JSON",
        ["not", "an", "object"],
        {"body": 5, "closingIssuesReferences": []},
        {"closingIssuesReferences": []},
        {"body": "本文"},
        {
            "body": "本文",
            "closingIssuesReferences": [{"url": "https://example.com/issues/1"}],
        },
        {"body": "本文", "closingIssuesReferences": ["not an object"]},
    ],
    ids=[
        "api",
        "not-json",
        "not-object",
        "body-type",
        "body-missing",
        "closing-missing",
        "closing-url",
        "closing-entry",
    ],
)
def test_parent_requirements_required_pr_failure_still_aborts(
    monkeypatch: pytest.MonkeyPatch, pr: Any
) -> None:
    github, _calls = fake_requirements_gh(pr, {})
    monkeypatch.setattr(review_run, "command", github)
    with pytest.raises(review_run.FAILURES):
        review_run.parent_requirements(
            f"https://github.com/{REPOSITORY}/pull/7", REPOSITORY, 7
        )


def test_staged_git_tree_does_not_pollute_runtime_sensitive_cleanup(
    prepared: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from tools.agent_runner.runner import _redact_runtime_tree  # pyright: ignore[reportPrivateUsage]

    source = prepared["source"]
    (source / "readme-link").symlink_to("README.md")
    git(source, "add", "readme-link")
    git(source, "commit", "-m", "tracked symbolic link")
    prepared["head"] = git(source, "rev-parse", "HEAD")
    git(
        source,
        "push",
        str(prepared["remote"]),
        "+feature:feature",
        "+feature:refs/pull/7/head",
    )
    target = review_run.workspace.load_review_target()
    original = target.fetch_pull_request

    def current_pr(repository: str, number: int, **kwargs: Any) -> Any:
        return original(repository, number, **kwargs)._replace(
            head_sha=prepared["head"]
        )

    monkeypatch.setattr(target, "fetch_pull_request", current_pr)
    parent_input(prepared, tmp_path, monkeypatch)
    result = review_run.prepare(prepared["args"])
    assert result["status"] == "prepared", result.get("reason")
    mark_reviewed(result)
    staged = review_run.complete(argparse.Namespace(state=result["state_file"]))
    assert staged["status"] == "staged"
    assert _redact_runtime_tree(prepared["request_path"].parent / "dsh", ()) == []
    batch = staged_batch(prepared, staged)
    review_run.finalize_parent_batch(batch)
    payload = batch.results[0].attempts[0].payload
    assert isinstance(payload, dict) and payload["status"] == "success", payload


@pytest.mark.parametrize(
    "changed",
    [
        "snapshot",
        "bundle",
        "request_pr",
        "request_head",
        "snapshot_symlink",
        "descriptor_missing",
    ],
)
def test_parent_input_rejects_unbound_or_changed_data(
    prepared: dict[str, Any],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    changed: str,
) -> None:
    descriptor = parent_input(prepared, tmp_path, monkeypatch)
    snapshot = Path(descriptor["path"])
    if changed == "snapshot":
        snapshot.chmod(0o600)
        snapshot.write_text("{}")
    elif changed == "bundle":
        bundle = snapshot.with_name("objects.bundle")
        bundle.chmod(0o600)
        bundle.write_bytes(b"broken bundle")
    elif changed == "request_pr":
        prepared["args"].pr = f"https://github.com/{REPOSITORY}/pull/8"
    elif changed == "request_head":
        request = Request.model_validate_json(prepared["request_path"].read_text())
        request.prompt = (
            "```json\n"
            + json.dumps({"parent_pr_data": descriptor, "pr_head": "0" * 40})
            + "\n```\n"
        )
        prepared["request_path"].write_text(request.model_dump_json())
    elif changed == "snapshot_symlink":
        other = snapshot.with_name("other.json")
        other.write_bytes(snapshot.read_bytes())
        snapshot.unlink()
        snapshot.symlink_to(other)
    else:
        request = Request.model_validate_json(prepared["request_path"].read_text())
        request.prompt = "review without parent input"
        prepared["request_path"].write_text(request.model_dump_json())
    with pytest.raises((RuntimeError, ValueError, OSError)):
        review_run.prepare(prepared["args"])
    assert not list(prepared["parent"].glob("reviews/**/*.md"))


@pytest.mark.parametrize(
    "changed",
    ["head", "draft", "stage_metadata", "request", "stop", "sensitive", "identity"],
)
def test_parent_finalize_refuses_stale_or_untrusted_staging(
    prepared: dict[str, Any],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    changed: str,
) -> None:
    parent_input(prepared, tmp_path, monkeypatch)
    result = review_run.prepare(prepared["args"])
    assert result["status"] == "prepared", result.get("reason")
    mark_reviewed(result)
    staged = review_run.complete(argparse.Namespace(state=result["state_file"]))
    assert staged["status"] == "staged"
    batch = staged_batch(prepared, staged)
    if changed == "head":

        def changed_head(*args: Any) -> str:
            return "0" * 40

        monkeypatch.setattr(review_run.workspace, "current_pr_head", changed_head)
    elif changed == "draft":
        Path(result["draft"]).write_text("changed after staging")
    elif changed == "stage_metadata":
        draft = Path(result["draft"])
        draft.write_text(draft.read_text() + "\n追記\n")
        state_file = Path(result["state_file"])
        state = json.loads(state_file.read_text())
        state["run_context"]["staged"]["draft_sha256"] = hashlib.sha256(
            draft.read_bytes()
        ).hexdigest()
        state_file.write_text(json.dumps(state))
    elif changed == "request":
        request = Request.model_validate_json(prepared["request_path"].read_text())
        request.request_id = "other-request"
        prepared["request_path"].write_text(request.model_dump_json())
    elif changed == "stop":
        batch.results[0].attempts[0].stop_confirmed = False
    elif changed == "sensitive":
        batch.results[0].attempts[0].sensitive_paths = [
            tmp_path / "uncleaned-sensitive.json"
        ]
    else:
        batch.results[0].attempts[0].identity.model = "other-model"
    review_run.finalize_parent_batch(batch)
    payload = batch.results[0].attempts[0].payload
    assert isinstance(payload, dict) and payload["status"] == "failed", payload
    assert not Path(result["destination"]).exists()
    assert Path(result["worktree"]).exists()


def mark_reviewed(result: dict[str, Any]) -> None:
    draft = Path(result["draft"])
    draft.write_text(
        f"- 対象: PR #7 / head {result['reviewed_head'][:12]} / 2026-10-08\n"
        "- レビュアー: observed-model（ランタイム: claude-code）\n\n"
        "## Review history\n\n| Reviewed at (UTC) | HEAD | Mode |\n|---|---|---|\n"
        f"| 2026-10-08T00:00:00Z | `{result['reviewed_head'][:12]}` | Initial |\n\n"
        "## Summary\n\n全体差分を確認。activeな指摘なし。\n",
        encoding="utf-8",
    )
    findings = Path(result["findings_draft"])
    document = json.loads(findings.read_text(encoding="utf-8"))
    document["coverage"]["read"] = ["PR全体差分とREADME.md全文"]
    findings.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")


def test_dsh_child_uses_fixed_outbox_without_shared_writes(
    prepared: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    parent_input(prepared, tmp_path, monkeypatch)

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("child must not acquire the shared save lock")

    monkeypatch.setattr(review_run.workspace, "review_save_lock", forbidden)
    monkeypatch.setattr(review_run.record.workspace, "review_save_lock", forbidden)
    result = review_run.prepare(prepared["args"])
    assert result["status"] == "prepared", result
    attempt = prepared["request_path"].parent
    assert Path(result["draft"]) == attempt / "dsh/tmp/exports/review.md"
    assert Path(result["findings_draft"]) == attempt / "dsh/tmp/exports/findings.json"
    assert Path(result["run_record"]) == attempt / "review-scratch/run.json"
    assert not list((prepared["parent"] / "reviews").rglob("runs/*.json"))
    mark_reviewed(result)
    staged = review_run.complete(argparse.Namespace(state=result["state_file"]))
    assert staged["status"] == "staged", staged


def test_complete_rejects_changed_draft_before_writing_anywhere(
    prepared: dict[str, Any], tmp_path: Path
) -> None:
    result = review_run.prepare(prepared["args"])
    mark_reviewed(result)
    protected = tmp_path / "protected.md"
    protected.write_text("user-owned bytes\n")
    state_path = Path(result["state_file"])
    state = json.loads(state_path.read_text())
    state["draft"] = str(protected)
    state_path.write_text(json.dumps(state))
    candidates = Path(result["findings_draft"]).read_bytes()
    completed = review_run.complete(argparse.Namespace(state=str(state_path)))
    assert completed["status"] == "failed"
    assert protected.read_bytes() == b"user-owned bytes\n"
    assert Path(result["findings_draft"]).read_bytes() == candidates


@pytest.mark.parametrize("changed", ["state_path", "draft_path", "destination", "symlink", "hardlink", "fifo", "parent_symlink", "oversize", "invalid_candidates", "native_denial", "missing_native"])
def test_parent_outbox_refusal_preserves_all_files(
    prepared: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch, changed: str
) -> None:
    parent_input(prepared, tmp_path, monkeypatch)
    result = review_run.prepare(prepared["args"])
    mark_reviewed(result)
    staged = review_run.complete(argparse.Namespace(state=result["state_file"]))
    batch = staged_batch(prepared, staged)
    protected = tmp_path / "protected.md"
    protected.write_text("unrelated user-owned bytes\n")
    state_path = Path(result["state_file"])
    draft = Path(result["draft"])
    state = json.loads(state_path.read_text())
    if changed in {"native_denial", "missing_native"}:
        log = prepared["request_path"].parent / "stdout.log"
        events = [json.loads(line) for line in log.read_text().splitlines()]
        if changed == "native_denial":
            events[2:2] = [
                {"type": "tool_call", "callId": "denied", "tool": "write", "input": {}},
                {"type": "tool_result", "callId": "denied", "status": "error", "result": 'Error: the user rejected tool "write"'},
            ]
        else:
            events = [event for event in events if event["type"] not in {"tool_call", "tool_result"}]
        log.write_text("".join(json.dumps(event) + "\n" for event in events))
    elif changed == "state_path":
        batch.results[0].attempts[0].payload["state_file"] = str(protected)
    elif changed == "draft_path":
        state["draft"] = str(protected)
        state_path.write_text(json.dumps(state))
    elif changed == "destination":
        state["destination"] = "reviews/example/syncer/#7-feature/another-reviewer.md"
        state_path.write_text(json.dumps(state))
    elif changed == "parent_symlink":
        draft.parent.rename(draft.parent.with_name("export-target"))
        draft.parent.symlink_to(draft.parent.with_name("export-target"), target_is_directory=True)
    elif changed == "invalid_candidates":
        findings = Path(result["findings_draft"])
        document = json.loads(findings.read_text())
        document["findings"] = [{}]
        findings.write_text(json.dumps(document))
        state["run_context"]["staged"]["findings_sha256"] = hashlib.sha256(findings.read_bytes()).hexdigest()
        state_path.write_text(json.dumps(state))
        batch.results[0].attempts[0].payload["staged"] = state["run_context"]["staged"]
    else:
        if changed in {"hardlink", "symlink"}:
            # Keep valid staged bytes: only the link should cause refusal.
            protected.write_bytes(draft.read_bytes())
        draft.unlink()
        if changed == "symlink":
            draft.symlink_to(protected)
        elif changed == "hardlink":
            os.link(protected, draft)
        elif changed == "fifo":
            os.mkfifo(draft)
        else:
            with draft.open("wb") as stream:
                stream.truncate(16 * 1024 * 1024 + 1)
    protected_before = protected.read_bytes()
    state_before = state_path.read_bytes()
    local = prepared["request_path"].parent / "review-scratch/run.json"
    record_before = local.read_bytes()
    review_run.finalize_parent_batch(batch)
    completed = batch.results[0].attempts[0].payload
    assert completed["status"] == "failed", completed
    assert protected.read_bytes() == protected_before
    assert state_path.read_bytes() == state_before
    assert local.read_bytes() == record_before
    assert not list((prepared["parent"] / "reviews").rglob("*"))


def test_parent_uses_captured_export_bytes_without_reopening(
    prepared: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    parent_input(prepared, tmp_path, monkeypatch)
    result = review_run.prepare(prepared["args"])
    mark_reviewed(result)
    staged = review_run.complete(argparse.Namespace(state=result["state_file"]))
    batch = staged_batch(prepared, staged)
    original = review_run.parent_data.regular_bytes
    counts: dict[Path, int] = {}
    exports = {Path(result["draft"]), Path(result["findings_draft"])}
    expected = {path: path.read_bytes() for path in exports}

    def captured(path: Path, **kwargs: Any) -> bytes:
        raw = original(path, **kwargs)
        if path in exports:
            counts[path] = counts.get(path, 0) + 1
            path.write_bytes(b"replaced after verified read")
        return raw

    monkeypatch.setattr(review_run.parent_data, "regular_bytes", captured)
    review_run.finalize_parent_batch(batch)
    completed = batch.results[0].attempts[0].payload
    assert completed["status"] == "success", completed
    assert counts == {path: 1 for path in exports}
    assert Path(completed["review_file"]).read_bytes() == expected[Path(result["draft"])]
    assert Path(completed["findings_file"]).read_bytes() == expected[Path(result["findings_draft"])]


@pytest.mark.parametrize("poison", ["hook", "config", "git-pointer"])
def test_parent_never_executes_git_in_child_owned_session(
    prepared: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch, poison: str
) -> None:
    parent_input(prepared, tmp_path, monkeypatch)
    result = review_run.prepare(prepared["args"])
    mark_reviewed(result)
    staged = review_run.complete(argparse.Namespace(state=result["state_file"]))
    batch = staged_batch(prepared, staged)
    child = Path(result["state_file"]).parent
    protected = tmp_path / "protected"
    protected.write_text("user-owned bytes\n")
    if poison == "hook":
        hook = child / "repo/.git/hooks/reference-transaction"
        hook.write_text(f"#!/bin/sh\nprintf compromised > '{protected}'\n")
        hook.chmod(0o755)
    elif poison == "config":
        with (child / "repo/.git/config").open("a") as stream:
            stream.write(f"\n[core]\nfsmonitor = touch '{protected}'\n")
    else:
        (child / "worktree/.git").write_text(f"gitdir: {prepared['source'] / '.git'}\n")
    original = review_run.workspace.git

    def trusted_only(root: Path, *args: Any, **kwargs: Any) -> Any:
        assert not Path(root).is_relative_to(child), "parent must not run child-owned Git"
        return original(root, *args, **kwargs)

    monkeypatch.setattr(review_run.workspace, "git", trusted_only)
    review_run.finalize_parent_batch(batch)
    completed = batch.results[0].attempts[0].payload
    assert completed["status"] == "success", completed.get("reason")
    assert protected.read_bytes() == b"user-owned bytes\n"
    assert not child.exists()


def test_parent_child_cleanup_failure_keeps_saved_artifacts_in_result(
    prepared: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    parent_input(prepared, tmp_path, monkeypatch)
    result = review_run.prepare(prepared["args"])
    mark_reviewed(result)
    staged = review_run.complete(argparse.Namespace(state=result["state_file"]))
    batch = staged_batch(prepared, staged)
    child = Path(result["state_file"]).parent
    original = review_run.shutil.rmtree

    def fail_child(path: Any, *args: Any, **kwargs: Any) -> Any:
        if Path(path) == child:
            raise OSError("child cleanup refused")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(review_run.shutil, "rmtree", fail_child)
    review_run.finalize_parent_batch(batch)
    completed = batch.results[0].attempts[0].payload
    assert completed["status"] == "failed" and completed["cleanup"] == "failed"
    assert completed["child_session_dir"] == str(child) and child.is_dir()
    assert Path(completed["review_file"]).is_file()
    assert Path(completed["findings_file"]).is_file()
    document = json.loads(Path(completed["run_record"]).read_text())
    assert document["status"] == "failed" and document["failed_at"] == "cleanup"


@pytest.mark.parametrize("malformed", ["valid", "state", "context-list", "context-null", "staged", "inputs-null", "inputs-list", "request-list", "request-null", "monotonic"])
def test_parent_invalid_first_result_does_not_block_valid_second(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, malformed: str
) -> None:
    # Both independent checkouts represent the same remote PR and fixed commit.
    monkeypatch.setenv("GIT_AUTHOR_DATE", "2026-10-19T00:00:00Z")
    monkeypatch.setenv("GIT_COMMITTER_DATE", "2026-10-19T00:00:00Z")
    first_root = tmp_path / "first"
    first_root.mkdir()
    prepared = globals()["prepared"].__wrapped__(first_root, monkeypatch)
    parent_input(prepared, first_root, monkeypatch)
    first = review_run.prepare(prepared["args"])
    mark_reviewed(first)
    staged = review_run.complete(argparse.Namespace(state=first["state_file"]))
    batch = staged_batch(prepared, staged)
    first_parent = prepared["parent"]
    state_path = Path(first["state_file"])
    local = prepared["request_path"].parent / "review-scratch/run.json"
    state = json.loads(state_path.read_text())
    journal = json.loads(local.read_text())
    if malformed == "state":
        state = []
    elif malformed == "context-list":
        state["run_context"] = []
    elif malformed == "context-null":
        state["run_context"] = None
    elif malformed == "staged":
        state["run_context"]["staged"] = []
        batch.results[0].attempts[0].payload["staged"] = []
    elif malformed.startswith("inputs-"):
        journal["inputs"] = None if malformed == "inputs-null" else []
    elif malformed == "request-list":
        journal["inputs"]["request"] = []
    elif malformed == "request-null":
        journal["inputs"]["request"] = None
    elif malformed == "monotonic":
        state["run_context"]["started_monotonic"] = {}
    state_path.write_text(json.dumps(state))
    local.write_text(json.dumps(journal))
    state_before, journal_before = state_path.read_bytes(), local.read_bytes()
    second_root = tmp_path / "second"
    second_root.mkdir()
    second_prepared = globals()["prepared"].__wrapped__(second_root, monkeypatch)
    parent_input(second_prepared, second_root, monkeypatch)
    second = review_run.prepare(second_prepared["args"])
    mark_reviewed(second)
    second_staged = review_run.complete(argparse.Namespace(state=second["state_file"]))
    batch.results.append(staged_batch(second_prepared, second_staged).results[0])
    review_run.finalize_parent_batch(batch)
    first_done, second_done = [result.attempts[0].payload for result in batch.results]
    assert second_done["status"] == "success", second_done.get("reason")
    if malformed == "valid":
        assert first_done["status"] == "success", first_done.get("reason")
    else:
        assert first_done["status"] == "failed", first_done
        assert state_path.read_bytes() == state_before and local.read_bytes() == journal_before
        assert not list((first_parent / "reviews").rglob("*"))


def test_parent_codex_rollout_does_not_replace_authenticated_child_model(
    prepared: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    parent_input(prepared, tmp_path, monkeypatch)
    result = review_run.prepare(prepared["args"])
    mark_reviewed(result)
    staged = review_run.complete(argparse.Namespace(state=result["state_file"]))
    batch = staged_batch(prepared, staged)
    thread = "019fd23a-4723-7e02-83d9-58f32849f5ab"
    home = tmp_path / "codex-parent"
    rollout = home / "sessions" / f"rollout-{thread}.jsonl"
    rollout.parent.mkdir(parents=True)
    rollout.write_text(json.dumps({"type": "turn_context", "payload": {"model": "parent-codex-model"}}) + "\n")
    monkeypatch.setenv("CODEX_HOME", str(home))
    monkeypatch.setenv("CODEX_THREAD_ID", thread)
    assert review_run.workspace.resolve_codex_model_name() == "parent-codex-model"
    # Ordinary interactive creates still compare an explicit model to the live Codex model.
    with pytest.raises(review_run.workspace.WorkspaceError, match="does not match Codex"):
        review_run.workspace.resolve_runtime_model_name("commandcode/actual/model")
    review_run.finalize_parent_batch(batch)
    completed = batch.results[0].attempts[0].payload
    assert completed["status"] == "success", completed.get("reason")
    findings = json.loads(Path(completed["findings_file"]).read_text())
    assert findings["reviewer"]["model"] == "actual/model"
    assert findings["reviewer"]["provenance"]["provider"] == "commandcode"
    assert Path(completed["review_file"]).name == "commandcode-actual-model.md"
    assert os.environ["CODEX_HOME"] == str(home) and os.environ["CODEX_THREAD_ID"] == thread


@pytest.mark.parametrize("provider", ["commandcode", "opencode-go"])
def test_dsh_prepare_complete_records_live_identity(
    prepared: dict[str, Any],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    provider: str,
) -> None:
    parent_input(prepared, tmp_path, monkeypatch)
    home = tmp_path / "dsh"
    write_session(home, prepared["caller"], provider=provider, model="actual/model")
    for key, value in {
        "DSH_HOME": str(home),
        "DSH_SESSION_ID": "session-test",
        "DSH_PROFILE": "headless",
        "DSH_SHELL": "1",
        "PI_PROVIDER": "parent",
        "PI_MODEL": "wrong-parent",
    }.items():
        monkeypatch.setenv(key, value)
    prepared["args"].runtime = "dsh"
    prepared["args"].model_name = None
    result = review_run.prepare(prepared["args"])
    assert result["status"] == "prepared"
    # A sandboxed reviewer must not mutate the shared source's Git directory.
    state = json.loads(Path(result["state_file"]).read_text())
    assert state["target_kind"] == "bundle"
    assert Path(state["target_root"]).is_relative_to(Path(result["state_file"]).parent)
    reviewer = result["reviewer"]
    assert reviewer["model"] == "actual/model"
    assert reviewer["runtime"] == "dsh"
    assert reviewer["provenance"]["provider"] == provider
    assert reviewer["provenance"]["effort"] == "high"
    assert reviewer["provenance"]["session_id"] == "session-test"
    assert reviewer["review_file"] == f"{provider}-actual-model.md"
    mark_reviewed(result)
    staged = review_run.complete(argparse.Namespace(state=result["state_file"]))
    assert staged["status"] == "staged", staged
    batch = staged_batch(prepared, staged)
    batch.results[0].attempts[0].identity.provider = provider
    review_run.finalize_parent_batch(batch)
    completed = batch.results[0].attempts[0].payload
    assert isinstance(completed, dict) and completed["status"] == "success", completed
    assert completed["cleanup"] == "success"
    document = json.loads(Path(str(completed["findings_file"])).read_text())
    assert document["reviewer"] == reviewer
    execution_record = json.loads(Path(str(completed["run_record"])).read_text())
    assert execution_record["reviewer"]["model"] == "actual/model"


def test_dsh_complete_refuses_a_changed_live_route(
    prepared: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    parent_input(prepared, tmp_path, monkeypatch)
    home = tmp_path / "dsh"
    write_session(home, prepared["caller"])
    for key, value in {
        "DSH_HOME": str(home),
        "DSH_SESSION_ID": "session-test",
        "DSH_PROFILE": "headless",
        "DSH_SHELL": "1",
    }.items():
        monkeypatch.setenv(key, value)
    prepared["args"].runtime = "dsh"
    prepared["args"].model_name = None
    result = review_run.prepare(prepared["args"])
    mark_reviewed(result)
    write_session(home, prepared["caller"], model="changed-model")
    completed = review_run.complete(argparse.Namespace(state=result["state_file"]))
    assert completed["status"] == "failed"
    assert completed["cleanup"] == "not_attempted"
    assert not Path(result["destination"]).exists()


def test_prepare_binds_request_and_local_records(prepared: dict[str, Any]) -> None:
    result = review_run.prepare(prepared["args"])
    assert result["status"] == "prepared"
    assert (
        result["run_id"],
        result["request_id"],
        result["agent_id"],
        result["role"],
    ) == (
        "run-568",
        "request-7",
        "fixture-reviewer",
        "inspect",
    )
    assert result["pr_head"] == result["reviewed_head"] == prepared["head"]
    assert result["records"]["decisions"] == []
    assert result["base"] == git(prepared["source"], "rev-parse", "main")
    assert result["diff_command"][-1] == f"{result['base']}..{prepared['head']}"


def configure_base_fetch(
    prepared: dict[str, Any],
    tmp_path: Path,
    *,
    relation: str,
    local_commit: bool,
) -> tuple[Path, str, str]:
    source, remote = prepared["source"], prepared["remote"]
    base = git(source, "rev-parse", "main")
    if relation != "ahead":
        git(source, "switch", "-c", "remote-base", "main")
        (source / "base.txt").write_text("remote base advanced\n", encoding="utf-8")
        git(source, "add", "base.txt")
        git(source, "commit", "-m", "advance remote base")
        git(source, "push", str(remote), "HEAD:main")
        git(source, "tag", "remote-base-only")
        git(source, "push", str(remote), "refs/tags/remote-base-only")
        git(source, "tag", "-d", "remote-base-only")
        git(source, "switch", "feature")
    remote_base = git(remote, "rev-parse", "refs/heads/main")
    if relation != "missing":
        tracked = {
            "ahead": prepared["head"],
            "behind": base,
            "diverged": prepared["head"],
            "equal": remote_base,
        }
        git(source, "update-ref", "refs/remotes/origin/main", tracked[relation])
    if local_commit:
        (source / "local.txt").write_text("not pushed\n", encoding="utf-8")
        git(source, "add", "local.txt")
        git(source, "commit", "-m", "local review target")
        prepared["args"].review_commit = git(source, "rev-parse", "HEAD")
        absent = subprocess.run(
            [
                "git",
                "-C",
                str(remote),
                "cat-file",
                "-e",
                prepared["args"].review_commit,
            ],
            check=False,
            capture_output=True,
        )
        assert absent.returncode != 0
    sibling = tmp_path / "sibling worktree"
    git(source, "worktree", "add", "--detach", str(sibling), prepared["head"])
    git(source, "update-ref", "refs/worktree/pr-review-base", prepared["head"])
    git(sibling, "update-ref", "refs/worktree/pr-review-base", prepared["head"])
    return sibling, base, remote_base


def shared_refs(root: Path) -> str:
    return git(
        root,
        "for-each-ref",
        "--format=%(refname) %(objectname)",
        "refs/heads",
        "refs/remotes",
        "refs/tags",
    )


@pytest.mark.parametrize(
    "relation", ["ahead", "behind", "diverged", "equal", "missing"]
)
@pytest.mark.parametrize(
    "local_commit", [False, True], ids=["pr-head", "unpushed-commit"]
)
def test_prepare_preserves_shared_refs_and_other_worktree_base_refs(
    prepared: dict[str, Any],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    relation: str,
    local_commit: bool,
) -> None:
    sibling, base, remote_base = configure_base_fetch(
        prepared, tmp_path, relation=relation, local_commit=local_commit
    )
    source = prepared["source"]
    before = shared_refs(source)
    snapshot = review_run.workspace.snapshot(source)
    result = review_run.prepare(prepared["args"])
    assert result["status"] == "prepared"
    assert shared_refs(source) == shared_refs(sibling) == before
    assert review_run.workspace.snapshot(source) == snapshot
    assert result["base"] == base
    assert (
        git(Path(result["worktree"]), "rev-parse", "refs/worktree/pr-review-base")
        == remote_base
    )
    for checkout in (source, sibling):
        assert (
            git(checkout, "rev-parse", "refs/worktree/pr-review-base")
            == prepared["head"]
        )
    expected = {"README.md", "local.txt"} if local_commit else {"README.md"}
    assert (
        set(
            git(
                Path(result["worktree"]),
                "diff",
                "--name-only",
                f"{base}..{result['reviewed_head']}",
            ).splitlines()
        )
        == expected
    )
    mark_reviewed(result)
    completed = review_run.complete(argparse.Namespace(state=result["state_file"]))
    assert completed["status"] == "success" and completed["cleanup"] == "success"
    assert shared_refs(source) == shared_refs(sibling) == before
    assert not Path(result["state_file"]).parent.exists()


def test_prepare_failure_after_base_fetch_keeps_shared_refs_unchanged(
    prepared: dict[str, Any],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sibling, _base, _remote_base = configure_base_fetch(
        prepared, tmp_path, relation="diverged", local_commit=True
    )
    before = shared_refs(prepared["source"])
    original = review_run.workspace.git

    def fail_merge_base(root: Path, *args: str, **kwargs: Any) -> Any:
        if args[0] == "merge-base":
            raise review_run.workspace.WorkspaceError("merge-base refused")
        return original(root, *args, **kwargs)

    monkeypatch.setattr(review_run.workspace, "git", fail_merge_base)
    result = review_run.prepare(prepared["args"])
    assert result["status"] == "failed" and result["reason"] == "merge-base refused"
    assert shared_refs(prepared["source"]) == shared_refs(sibling) == before
    assert Path(result["state_file"]).is_file()


def test_prepare_refuses_external_pr_without_explicit_checkout(
    prepared: dict[str, Any],
) -> None:
    # Missing explicit external checkout must not trigger checkout search or clone.
    prepared["args"].source_root = None
    with pytest.raises(review_run.workspace.WorkspaceError, match="checkout|code-root"):
        review_run.prepare(prepared["args"])
    assert run_records(prepared["parent"]) == []


def test_prepare_parallel_sessions_pin_their_own_base(prepared: dict[str, Any]) -> None:
    first = review_run.prepare(prepared["args"])
    source, remote = prepared["source"], prepared["remote"]
    git(source, "push", str(remote), "feature:main")
    second = review_run.prepare(prepared["args"])
    assert first["status"] == second["status"] == "prepared"
    assert first["base"] != second["base"]
    assert (
        git(Path(first["worktree"]), "rev-parse", "refs/worktree/pr-review-base")
        == first["base"]
    )
    assert (
        git(Path(second["worktree"]), "rev-parse", "refs/worktree/pr-review-base")
        == second["base"]
    )
    mark_reviewed(first)
    assert (
        review_run.complete(argparse.Namespace(state=first["state_file"]))["cleanup"]
        == "success"
    )
    assert Path(second["state_file"]).exists()
    assert (
        git(Path(second["worktree"]), "rev-parse", "refs/worktree/pr-review-base")
        == second["base"]
    )


def test_complete_saves_zero_findings_with_provenance(prepared: dict[str, Any]) -> None:
    result = review_run.prepare(prepared["args"])
    mark_reviewed(result)
    completed = review_run.complete(argparse.Namespace(state=result["state_file"]))
    assert completed["status"] == "success"
    assert completed["active_findings"] == 0
    assert completed["request_id"] == "request-7"
    assert completed["cleanup"] == "success"
    assert completed["cleanup_details"]["pr_ref_status"] == "deleted"
    document = json.loads(Path(completed["findings_file"]).read_text(encoding="utf-8"))
    assert document["schema"] == "review-findings/v2"
    assert document["reviewer"]["provenance"]["agent_id"] == "fixture-reviewer"
    assert document["reviewer"]["provenance"]["provider"] == "unknown"
    assert document["reviewer"]["provenance"]["run_id"] == "run-568"
    assert document["timing"]["waiting_seconds"] is None
    assert document["timing"]["seconds"] > 0
    markdown = Path(completed["review_file"]).read_text(encoding="utf-8")
    execution = json.loads(
        markdown.split("<!-- pr-review:execution -->\n```json\n", 1)[1].split(
            "\n```", 1
        )[0]
    )
    assert execution["timing"] == document["timing"]
    assert execution["reviewer"] == document["reviewer"]
    assert not Path(result["state_file"]).parent.exists()


@pytest.mark.parametrize(
    "failure",
    [
        "missing",
        "invalid",
        "binding",
        "reviewer",
        "coverage",
        "coverage_kind",
        "destination",
        "head",
        "api",
    ],
)
def test_complete_preserves_failure_as_failed_result(
    prepared: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
) -> None:
    result = review_run.prepare(prepared["args"])
    mark_reviewed(result)
    if failure == "missing":
        Path(result["draft"]).unlink()
    elif failure == "invalid":
        Path(result["findings_draft"]).write_text("invalid JSON", encoding="utf-8")
    elif failure == "binding":
        request = json.loads(prepared["request_path"].read_text(encoding="utf-8"))
        request["request_id"] = "another-request"
        prepared["request_path"].write_text(json.dumps(request), encoding="utf-8")
    elif failure in {"reviewer", "coverage", "coverage_kind"}:
        findings = Path(result["findings_draft"])
        document = json.loads(findings.read_text(encoding="utf-8"))
        if failure == "reviewer":
            document["reviewer"]["provenance"]["agent_id"] = "another-agent"
        elif failure == "coverage_kind":
            document["coverage"] = ["README.md"]
        else:
            document["coverage"]["read"] = []
        findings.write_text(json.dumps(document), encoding="utf-8")
    elif failure == "destination":
        destination = prepared["parent"] / result["destination"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text("another review", encoding="utf-8")
    else:

        def moved(_repository: str, _number: int) -> str:
            if failure == "api":
                raise review_run.workspace.WorkspaceError("API unavailable")
            return "f" * 40

        monkeypatch.setattr(review_run.workspace, "current_pr_head", moved)
    assert review_run.main(["complete", "--state", result["state_file"]]) != 0
    failed = json.loads(capsys.readouterr().out)
    assert failed["status"] == "failed"
    assert failed["request_id"] == "request-7"
    assert failed["active_findings"] is None
    assert failed["reason"]
    assert failed["retained_paths"]["worktree"] == result["worktree"]
    assert failed["retained_paths"]["draft"] == result["draft"]
    assert Path(result["state_file"]).exists()


@pytest.mark.parametrize("field", ["work_dir", "result_shape"])
def test_prepare_rejects_wrong_request_workdir_and_shape(
    prepared: dict[str, Any], field: str
) -> None:
    value = json.loads(prepared["request_path"].read_text(encoding="utf-8"))
    value[field] = str(prepared["source"]) if field == "work_dir" else "text"
    prepared["request_path"].write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(
        review_run.workspace.WorkspaceError, match="work_dir|result_shape"
    ):
        review_run.prepare(prepared["args"])


def test_prepare_nonrunner_marks_unobserved_identity_unknown(
    prepared: dict[str, Any],
) -> None:
    prepared["args"].request = None
    result = review_run.prepare(prepared["args"])
    assert (
        result["run_id"]
        == result["request_id"]
        == result["agent_id"]
        == result["role"]
        == "unknown"
    )
    document = json.loads(Path(result["findings_draft"]).read_text(encoding="utf-8"))
    provenance = document["reviewer"]["provenance"]
    assert (
        provenance["provider"]
        == provenance["effort"]
        == provenance["cli_version"]
        == "unknown"
    )


def test_complete_reports_saved_but_uncleaned_result_as_failure(
    prepared: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = review_run.prepare(prepared["args"])
    mark_reviewed(result)

    def cleanup_failure(_args: argparse.Namespace) -> None:
        raise review_run.workspace.WorkspaceError("cleanup refused")

    monkeypatch.setattr(review_run.workspace, "cleanup", cleanup_failure)
    completed = review_run.complete(argparse.Namespace(state=result["state_file"]))
    assert completed["status"] == "failed"
    assert completed["cleanup"] == "failed"
    assert completed["reason"] == "cleanup refused"
    assert completed["retained_paths"]["worktree"] == result["worktree"]
    assert Path(completed["review_file"]).is_file()
    assert Path(completed["findings_file"]).is_file()
    assert Path(result["state_file"]).exists()


def test_prepare_base_fetch_failure_returns_correlated_retained_paths(
    prepared: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    original = review_run.workspace.git

    def fail_base_fetch(root: Path, *args: str, **kwargs: Any) -> Any:
        if args[:2] == ("fetch", "--quiet") and "--no-write-fetch-head" in args:
            raise review_run.workspace.WorkspaceError("base fetch failed")
        return original(root, *args, **kwargs)

    monkeypatch.setattr(review_run.workspace, "git", fail_base_fetch)
    assert review_run.main(prepared["argv"]) == 1
    failed = json.loads(capsys.readouterr().out)
    assert failed["status"] == "failed" and failed["request_id"] == "request-7"
    assert failed["repository"] == REPOSITORY and failed["pr_head"] == prepared["head"]
    assert failed["active_findings"] is None and failed["reason"] == "base fetch failed"
    assert Path(failed["state_file"]).is_file()
    assert Path(failed["retained_paths"]["worktree"]).is_dir()


def test_prepare_fails_without_observed_model(prepared: dict[str, Any]) -> None:
    prepared["args"].model_name = None
    with pytest.raises(review_run.workspace.WorkspaceError, match="model"):
        review_run.prepare(prepared["args"])


def test_prepare_pi_requires_both_current_environment_identifiers(
    prepared: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared["args"].runtime = "pi"
    monkeypatch.setenv("PI_MODEL", "observed-model")
    monkeypatch.delenv("PI_PROVIDER", raising=False)
    with pytest.raises(review_run.workspace.WorkspaceError, match="PI_PROVIDER"):
        review_run.prepare(prepared["args"])


# --- 実行記録（Issue #601） ---------------------------------------------------------------------------------------


def run_records(parent: Path) -> list[Path]:
    return sorted((parent / "reviews").glob("*/*/#*/runs/*.json"))


def only_record(parent: Path) -> dict[str, Any]:
    paths = run_records(parent)
    assert len(paths) == 1, paths
    return review_run.record.findings.validate_document(
        json.loads(paths[0].read_text(encoding="utf-8"))
    )


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_success_record_matches_saved_outputs_and_candidates(
    prepared: dict[str, Any],
) -> None:
    result = review_run.prepare(prepared["args"])
    assert Path(result["run_record"]) == run_records(prepared["parent"])[0]
    assert only_record(prepared["parent"])["status"] == "started"
    mark_reviewed(result)
    completed = review_run.complete(argparse.Namespace(state=result["state_file"]))
    assert (
        completed["status"] == "success"
        and completed["run_record"] == result["run_record"]
    )
    record = only_record(prepared["parent"])
    candidates = json.loads(
        Path(completed["findings_file"]).read_text(encoding="utf-8")
    )
    assert (
        record["status"] == "success"
        and record["mode"] == "Initial"
        and record["review_kind"] == "pr_head"
    )
    assert record["reviewer"] == {
        key: candidates["reviewer"][key] for key in ("model", "runtime", "provenance")
    }
    assert record["timing"]["started_at"] == candidates["timing"]["started_at"]
    assert (
        record["base"] == candidates["base"]
        and record["reviewed_head"] == candidates["reviewed_head"]
    )
    assert record["outputs"] == {
        "review_file": Path(completed["review_file"]).name,
        "review_sha256": sha256(Path(completed["review_file"])),
        "findings_file": "findings/" + Path(completed["findings_file"]).name,
        "findings_sha256": sha256(Path(completed["findings_file"])),
        "active_findings": 0,
        "by_severity": {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0},
        "unverified": 0,
    }
    assert record["inputs"]["request"] == {
        "sha256": sha256(prepared["request_path"]),
        "deadline_seconds": 600.0,
    }
    assert record["inputs"]["previous_review"] is None
    assert record["inputs"]["records"]["decisions"] == {}
    assert record["inputs"]["diff"] == {
        "files": 1,
        "added": 1,
        "deleted": 0,
        "binary": 0,
    }
    assert all(
        record["timing"][key] is not None
        for key in review_run.record.findings.RUN_STAGE_SECONDS
    )
    suffix = Path(result["state_file"]).parent.name.rsplit("-", 1)[1]
    assert Path(result["run_record"]).name.endswith(f"-observed-model-{suffix}.json")


def test_second_review_records_update_mode_and_previous_digest(
    prepared: dict[str, Any],
) -> None:
    first = review_run.prepare(prepared["args"])
    mark_reviewed(first)
    saved = review_run.complete(argparse.Namespace(state=first["state_file"]))
    second = review_run.prepare(prepared["args"])
    document = json.loads(Path(second["run_record"]).read_text(encoding="utf-8"))
    assert document["mode"] == "Update"
    assert document["inputs"]["previous_review"] == {
        "sha256": sha256(Path(saved["review_file"]))
    }
    assert len(run_records(prepared["parent"])) == 2


def test_prepare_without_request_records_null_request(prepared: dict[str, Any]) -> None:
    prepared["args"].request = None
    result = review_run.prepare(prepared["args"])
    document = json.loads(Path(result["run_record"]).read_text(encoding="utf-8"))
    assert document["inputs"]["request"] is None
    assert document["reviewer"]["provenance"]["run_id"] == "unknown"


def test_prepare_alone_leaves_started_record_like_a_killed_run(
    prepared: dict[str, Any],
) -> None:
    review_run.prepare(prepared["args"])
    record = only_record(prepared["parent"])
    assert record["status"] == "started" and record["inputs"] is not None
    assert record["timing"]["prepare_seconds"] is not None
    assert (
        record["timing"]["finished_at"] is None
        and record["timing"]["total_seconds"] is None
    )


def test_prepare_failure_before_resolve_writes_no_record(
    prepared: dict[str, Any],
) -> None:
    prepared["args"].model_name = None
    with pytest.raises(review_run.workspace.WorkspaceError, match="model"):
        review_run.prepare(prepared["args"])
    assert run_records(prepared["parent"]) == []


def test_prepare_failure_after_resolve_records_prepare(
    prepared: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def unavailable(_target: dict[str, Any], _comments: str | None) -> dict[str, Any]:
        raise review_run.workspace.WorkspaceError("comments unavailable")

    monkeypatch.setattr(review_run, "read_records", unavailable)
    assert review_run.main(prepared["argv"]) == 1
    failed = json.loads(capsys.readouterr().out)
    assert failed["status"] == "failed" and failed["reason"] == "comments unavailable"
    assert failed["repository"] == REPOSITORY and failed["request_id"] == "request-7"
    record = only_record(prepared["parent"])
    assert failed["run_record"] == str(run_records(prepared["parent"])[0])
    assert (record["status"], record["failed_at"], record["reason"]) == (
        "failed",
        "prepare",
        "comments unavailable",
    )
    assert record["inputs"] is None and record["timing"]["prepare_seconds"] is not None


def test_prepare_failure_is_kept_when_the_model_later_calls_fail(
    prepared: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    original = review_run.workspace.git

    def fail_base_fetch(root: Path, *args: str, **kwargs: Any) -> Any:
        if args[:2] == ("fetch", "--quiet") and "--no-write-fetch-head" in args:
            raise review_run.workspace.WorkspaceError("base fetch failed")
        return original(root, *args, **kwargs)

    monkeypatch.setattr(review_run.workspace, "git", fail_base_fetch)
    assert review_run.main(prepared["argv"]) == 1
    failed = json.loads(capsys.readouterr().out)
    assert failed["run_record"] == str(run_records(prepared["parent"])[0])
    assert (
        review_run.main(["fail", "--state", failed["state_file"], "--reason", "止めた"])
        == 1
    )
    capsys.readouterr()
    record = only_record(prepared["parent"])
    assert (record["status"], record["failed_at"], record["reason"]) == (
        "failed",
        "prepare",
        "base fetch failed",
    )


@pytest.mark.parametrize("state_kind", ["absent", "prepared", "missing"])
@pytest.mark.parametrize("kind", ["regular", "symlink", "fifo", "fifo_symlink"])
def test_fail_request_returns_without_blocking_and_preserves_failure_record(
    prepared: dict[str, Any], tmp_path: Path, state_kind: str, kind: str,
) -> None:
    # fail has no runtime flag: both its first binding read and the diagnostic
    # retry after an invalid state/input must reject FIFOs without waiting.
    argv = [sys.executable, str(SCRIPT), "fail", "--reason", "review stopped"]
    if state_kind == "prepared":
        session = review_run.prepare(prepared["args"])
        assert session["status"] == "prepared", session
        argv.extend(["--state", session["state_file"]])
    elif state_kind == "missing":
        argv.extend(["--state", str(tmp_path / "missing-session.json")])
    before = run_records(prepared["parent"])
    saved = {path: path.read_bytes() for path in before}
    # Keep deliberately unsafe fixtures out of retained pytest scratch, even
    # when a regression forces subprocess.run to kill and reap its child.
    with tempfile.TemporaryDirectory(dir=tmp_path, prefix="fail-request-") as area:
        target = Path(area) / "request.json"
        if kind in {"fifo", "fifo_symlink"}:
            os.mkfifo(target)
        else:
            target.write_bytes(prepared["request_path"].read_bytes())
        candidate = target
        if kind in {"symlink", "fifo_symlink"}:
            candidate = Path(area) / "request-link.json"
            candidate.symlink_to(target)
        argv.extend(["--request", os.path.relpath(candidate, prepared["caller"])])
        completed = subprocess.run(
            argv, cwd=prepared["caller"], capture_output=True, text=True, timeout=5,
        )
    assert completed.returncode == 1, completed.stdout
    result = json.loads(completed.stdout)
    assert result["status"] == "failed" and result["reason"]
    if kind in {"regular", "symlink"}:
        assert result["request_id"] == "request-7"
        if state_kind != "missing":
            assert result["reason"] == "review stopped"
        if state_kind == "prepared":
            failure = only_record(prepared["parent"])
            assert (failure["status"], failure["failed_at"], failure["reason"]) == (
                "failed", "review", "review stopped",
            )
    else:
        if state_kind == "prepared":
            # The previously validated session binding is still available;
            # refusing the new input must not erase it from the diagnostic.
            assert result["request_id"] == "request-7"
        else:
            assert result.get("request_id") in {None, "unknown"}
        assert {path: path.read_bytes() for path in before} == saved
    if state_kind != "prepared":
        assert run_records(prepared["parent"]) == []


def test_model_fail_records_review(
    prepared: dict[str, Any], capsys: pytest.CaptureFixture[str]
) -> None:
    result = review_run.prepare(prepared["args"])
    assert (
        review_run.main(
            [
                "fail",
                "--state",
                result["state_file"],
                "--reason",
                "レビューを続けられない",
            ]
        )
        == 1
    )
    failed = json.loads(capsys.readouterr().out)
    assert failed["run_record"] == result["run_record"]
    record = only_record(prepared["parent"])
    assert (record["status"], record["failed_at"], record["reason"]) == (
        "failed",
        "review",
        "レビューを続けられない",
    )
    assert record["outputs"] is None
    assert (
        record["timing"]["review_seconds"] is not None
        and record["timing"]["total_seconds"] is not None
    )


def test_refused_complete_records_complete_and_a_retry_succeeds(
    prepared: dict[str, Any],
) -> None:
    result = review_run.prepare(prepared["args"])
    mark_reviewed(result)
    findings = Path(result["findings_draft"])
    document = json.loads(findings.read_text(encoding="utf-8"))
    document["coverage"]["read"] = []
    findings.write_text(json.dumps(document), encoding="utf-8")
    refused = review_run.complete(argparse.Namespace(state=result["state_file"]))
    assert (
        refused["status"] == "failed" and refused["run_record"] == result["run_record"]
    )
    record = only_record(prepared["parent"])
    assert (record["status"], record["failed_at"]) == ("failed", "complete")
    mark_reviewed(result)
    assert (
        review_run.complete(argparse.Namespace(state=result["state_file"]))["status"]
        == "success"
    )
    record = only_record(prepared["parent"])
    assert (record["status"], record["failed_at"], record["reason"]) == (
        "success",
        None,
        None,
    )


def test_save_failure_records_save(
    prepared: dict[str, Any], capsys: pytest.CaptureFixture[str]
) -> None:
    result = review_run.prepare(prepared["args"])
    mark_reviewed(result)
    destination = prepared["parent"] / result["destination"]
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("another review", encoding="utf-8")
    assert review_run.main(["complete", "--state", result["state_file"]]) == 1
    failed = json.loads(capsys.readouterr().out)
    assert failed["run_record"] == result["run_record"]
    record = only_record(prepared["parent"])
    assert (record["status"], record["failed_at"]) == ("failed", "save")
    assert record["outputs"] is None and record["timing"]["save_seconds"] is not None


def test_cleanup_failure_records_cleanup_with_saved_outputs(
    prepared: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = review_run.prepare(prepared["args"])
    mark_reviewed(result)

    def cleanup_failure(_args: argparse.Namespace) -> None:
        raise review_run.workspace.WorkspaceError("cleanup refused")

    monkeypatch.setattr(review_run.workspace, "cleanup", cleanup_failure)
    completed = review_run.complete(argparse.Namespace(state=result["state_file"]))
    record = only_record(prepared["parent"])
    assert (record["status"], record["failed_at"], record["reason"]) == (
        "failed",
        "cleanup",
        "cleanup refused",
    )
    assert record["outputs"]["review_sha256"] == sha256(Path(completed["review_file"]))


def test_record_update_failure_does_not_change_the_review_result(
    prepared: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = review_run.prepare(prepared["args"])
    mark_reviewed(result)

    def broken(*_args: Any, **_kwargs: Any) -> bool:
        raise OSError("disk full")

    monkeypatch.setattr(review_run.record, "update", broken)
    completed = review_run.complete(argparse.Namespace(state=result["state_file"]))
    assert (
        completed["status"] == "success"
        and "disk full" in completed["run_record_error"]
    )
    assert only_record(prepared["parent"])["status"] == "started"


def test_symlinked_review_directory_refuses_to_start(
    prepared: dict[str, Any], tmp_path: Path
) -> None:
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    reviews = prepared["parent"] / "reviews" / "example" / "syncer"
    reviews.mkdir(parents=True)
    (reviews / "#7-feature").symlink_to(elsewhere, target_is_directory=True)
    with pytest.raises(review_run.workspace.WorkspaceError, match="run record"):
        review_run.prepare(prepared["args"])
    assert list(elsewhere.iterdir()) == []
    assert (
        not (tmp_path / "sessions").exists()
        or list((tmp_path / "sessions").iterdir()) == []
    )


# --- ランナーの観測値（attach-runner） ------------------------------------------------------------------------------


def batch_result(
    path: Path,
    *,
    agent_id: str = "fixture-reviewer",
    request_id: str = "request-7",
    state: Any = "success",
    effort: str | None = "high",
) -> Path:
    attempt = Attempt(
        agent_id=agent_id,
        state=state,
        identity=Identity(
            model="observed-model",
            effort=effort,
            session_id="session-1",
            cli_version="9.9.9",
        ),
        exit_code=0,
        elapsed_seconds=12.5,
        stop_confirmed=True,
    )
    batch = BatchResult(
        run_id="run-568",
        state="success",
        assignments={"inspect": [agent_id]},
        results=[
            Result(
                request_id=request_id,
                role="inspect",
                requested_agent=agent_id,
                actual_agent=agent_id,
                state=state,
                attempts=[attempt],
            )
        ],
        outside_changes=[],
        elapsed_seconds=13.0,
        artifact_dir=path.parent,
    )
    path.write_text(batch.model_dump_json(), encoding="utf-8")
    return path


def attach(
    source: Path, capsys: pytest.CaptureFixture[str]
) -> tuple[int, dict[str, Any]]:
    code = review_run.main(["attach-runner", "--result", str(source)])
    return code, json.loads(capsys.readouterr().out)


def completed_review(prepared: dict[str, Any]) -> dict[str, Any]:
    result = review_run.prepare(prepared["args"])
    mark_reviewed(result)
    assert (
        review_run.complete(argparse.Namespace(state=result["state_file"]))["status"]
        == "success"
    )
    return result


def test_attach_runner_writes_the_runner_block_once_and_keeps_provenance(
    prepared: dict[str, Any], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    result = completed_review(prepared)
    before = only_record(prepared["parent"])
    source = batch_result(tmp_path / "result.json", effort=None)
    code, first = attach(source, capsys)
    assert code == 0 and first["status"] == "success"
    assert first["attached"] == [result["run_record"]] and first["unmatched_count"] == 0
    after = only_record(prepared["parent"])
    assert after["runner"] == {
        "identity": {
            "model": "observed-model",
            "provider": "unknown",
            "effort": "unknown",
            "session_id": "session-1",
            "cli_version": "9.9.9",
        },
        "attempt": {
            "state": "success",
            "exit_code": 0,
            "elapsed_seconds": 12.5,
            "stop_confirmed": True,
        },
    }
    assert after["reviewer"] == before["reviewer"]
    assert {key: value for key, value in after.items() if key != "runner"} == {
        key: value for key, value in before.items() if key != "runner"
    }
    code, second = attach(source, capsys)
    assert (
        code == 0
        and second["attached"] == []
        and second["unchanged"] == [result["run_record"]]
    )


def test_attach_runner_rejects_conflicting_values_without_writing(
    prepared: dict[str, Any], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    completed_review(prepared)
    assert attach(batch_result(tmp_path / "first.json", effort=None), capsys)[0] == 0
    written = only_record(prepared["parent"])
    code, payload = attach(
        batch_result(tmp_path / "second.json", effort="high"), capsys
    )
    assert (
        code == 1
        and payload["status"] == "failed"
        and payload["conflicts"]
        and payload["reason"]
    )
    assert payload["attached"] == []
    assert only_record(prepared["parent"]) == written


def test_attach_runner_reports_attempts_without_a_record(
    prepared: dict[str, Any], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    completed_review(prepared)
    before = only_record(prepared["parent"])
    code, payload = attach(
        batch_result(tmp_path / "result.json", agent_id="other-reviewer"), capsys
    )
    assert code == 0 and payload["attached"] == [] and payload["unmatched_count"] == 1
    assert payload["unmatched"] == [
        {
            "run_id": "run-568",
            "request_id": "request-7",
            "agent_id": "other-reviewer",
            "role": "inspect",
            "state": "success",
        }
    ]
    assert only_record(prepared["parent"]) == before


def test_attach_runner_marks_a_timed_out_attempt_on_the_started_record(
    prepared: dict[str, Any], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    review_run.prepare(prepared["args"])
    code, payload = attach(
        batch_result(tmp_path / "result.json", state="timed_out"), capsys
    )
    assert code == 0 and len(payload["attached"]) == 1
    record = only_record(prepared["parent"])
    assert (
        record["status"] == "started"
        and record["runner"]["attempt"]["state"] == "timed_out"
    )


def test_attach_runner_skips_files_outside_the_record_layout(
    prepared: dict[str, Any], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    completed_review(prepared)
    original = run_records(prepared["parent"])[0]
    content = original.read_bytes()
    original.unlink()
    # symlink の階層の下・形式の違う JSON・ディレクトリと PR 番号の合わない記録は、どれも書き先にしない
    linked = prepared["parent"] / "reviews" / "example" / "linked"
    linked.mkdir(parents=True)
    (linked / original.parent.parent.name).symlink_to(
        original.parent.parent, target_is_directory=True
    )
    (original.parent / "notes.json").write_text(
        json.dumps({"kind": "planning"}), encoding="utf-8"
    )
    other_runs = linked.parent / "syncer" / "#8-other" / "runs"
    other_runs.mkdir(parents=True)
    (other_runs / original.name).write_bytes(content)
    code, payload = attach(batch_result(tmp_path / "result.json"), capsys)
    assert code == 0 and payload["attached"] == [] and payload["skipped"] == 3
    assert (
        json.loads((other_runs / original.name).read_text(encoding="utf-8"))["runner"]
        is None
    )


def test_attach_runner_rejects_an_invalid_result_file(
    prepared: dict[str, Any], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "result.json"
    source.write_text(json.dumps({"unknown": 1}), encoding="utf-8")
    code, payload = attach(source, capsys)
    assert code == 1 and payload["status"] == "failed" and payload["reason"]
    assert payload["result_file"] == str(source)


def test_record_outputs_failure_after_save_keeps_the_review_result(
    prepared: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = review_run.prepare(prepared["args"])
    mark_reviewed(result)

    def broken(**_kwargs: Any) -> dict[str, Any]:
        raise OSError("saved file vanished")

    monkeypatch.setattr(review_run.record, "outputs_document", broken)
    completed = review_run.complete(argparse.Namespace(state=result["state_file"]))
    assert completed["status"] == "success" and completed["cleanup"] == "success"
    assert "saved file vanished" in completed["run_record_error"]
    assert only_record(prepared["parent"])["status"] == "started"


def test_payloads_without_a_record_still_name_the_run_record_key(
    prepared: dict[str, Any], capsys: pytest.CaptureFixture[str]
) -> None:
    assert review_run.main(["fail", "--reason", "PR が分からない"]) == 1
    assert json.loads(capsys.readouterr().out)["run_record"] is None
    argv = [
        argument
        for argument in prepared["argv"]
        if argument not in {"--model-name", "observed-model"}
    ]
    assert review_run.main(argv) == 1
    failed = json.loads(capsys.readouterr().out)
    assert failed["status"] == "failed" and failed["run_record"] is None


def _granted(lines: tuple[str, ...], path: object) -> int:
    """``path`` で始まる行（``<path>: <説明>`` か ``<path> and ...``）の数。"""
    return sum(line.startswith((f"{path}:", f"{path} ")) for line in lines)


@pytest.mark.parametrize("separate", [False, True])
def test_helper_write_exceptions_grant_git_data_only_where_the_helper_writes_it(
    tmp_path: Path, separate: bool
) -> None:
    """--source-root が親と別の repository なら、親の Git ディレクトリには保存ロックだけを許可する（#658）。"""
    from tools.agent_runner.runner import _single_line  # pyright: ignore[reportPrivateUsage]

    tool_root, parent = tmp_path / "tool", tmp_path / "parent"
    parent_git, source_git = parent / ".git", tmp_path / "project" / ".git"
    review_dir = f"{parent}/reviews/example/syncer/#7-*"
    lines = review_run.helper_write_exceptions(
        tool_root=tool_root,
        parent=parent,
        parent_git=parent_git,
        review_dir=review_dir,
        number=7,
        source_git=source_git if separate else None,
    )
    expected = [
        tool_root,
        review_dir,
        f"{parent}/tmp/agents/pr-review-scratch-7.*",
        tool_root / ".venv",
    ]
    expected += (
        [parent_git / "pr-review-save.lock", source_git] if separate else [parent_git]
    )
    assert [_granted(lines, path) for path in expected] == [1] * len(expected)
    assert sum(line.startswith("/") for line in lines) == len(expected)
    if separate:
        assert _granted(lines, parent_git) == 0
    same = review_run.helper_write_exceptions(
        tool_root=tool_root,
        parent=parent,
        parent_git=parent_git,
        review_dir=review_dir,
        number=7,
        source_git=parent_git,
    )
    assert same == review_run.helper_write_exceptions(
        tool_root=tool_root,
        parent=parent,
        parent_git=parent_git,
        review_dir=review_dir,
        number=7,
    )
    assert all(_single_line(line) for line in lines)


@pytest.mark.parametrize("status", ["deleted", "missing", "repinned"])
def test_complete_returns_actual_compare_and_delete_outcome(
    prepared: dict[str, Any], status: str
) -> None:
    # Reporting a pre-cleanup guess would lie about refs another session repinned.
    result = review_run.prepare(prepared["args"])
    mark_reviewed(result)
    ref = "refs/pr-review/repos/example/syncer/7"
    if status == "missing":
        git(prepared["source"], "update-ref", "-d", ref)
    elif status == "repinned":
        git(
            prepared["source"],
            "update-ref",
            ref,
            git(prepared["source"], "rev-parse", "main"),
        )
    completed = review_run.complete(argparse.Namespace(state=result["state_file"]))
    assert completed["status"] == "success", completed
    assert completed["cleanup_details"]["pr_ref"] == ref
    assert completed["cleanup_details"]["pr_ref_status"] == status
    remaining = git(prepared["source"], "for-each-ref", "--format=%(objectname)", ref)
    assert remaining == (
        git(prepared["source"], "rev-parse", "main") if status == "repinned" else ""
    )


def test_prepare_returns_skip_decisions_through_ordinary_comments(
    prepared: dict[str, Any],
) -> None:
    # Bypassing the shared parser would silently discard previously accepted skip decisions.
    head = prepared["head"]
    decisions = []
    for finding, state in (("H-1", "fix"), ("M-1", "skip")):
        reference = f"observed-model#{finding}@{head[:12]}"
        decision = {
            "id": reference,
            "sources": [reference],
            "summary": finding,
            "locations": ["README.md:1"],
            "state": state,
            "change": "new",
            "severity": "Medium",
            "pr_relation": "introduced",
            "reason": "確認済み",
        }
        if state == "skip":
            decision["revisit_when"] = "新しい再現条件が見つかったとき"
        decisions.append(decision)
    record = {
        "schema": "review-records/v1",
        "pr": {"repository": REPOSITORY, "number": 7},
        "round": 1,
        "reviewed_head": head,
        "recorded_at": "2026-10-01T01:40:13Z",
        "planner": {
            "model": "planner-model",
            "runtime": "pi",
            "agent_id": "planner-model",
        },
        "seats": [
            {
                "review_file": "observed-model",
                "model": "observed-model",
                "runtime": "claude-code",
                "file_head": head[:12],
                "mode": "Initial",
                "rerun": True,
                "merge_recommendation": "Request changes",
            }
        ],
        "decisions": decisions,
        "outcome": "awaiting_approval",
    }
    body = (
        f"<!-- review-fix-planning:agent:planner-model -->\n"
        f"<!-- review-fix-planning:round:1:{head} -->\n"
        + review_run.records.render_block(record)
    )
    prepared["comments"].write_text(
        json.dumps(
            [
                [
                    {
                        "id": 42,
                        "body": body,
                        "user": {"login": "owner"},
                        "author_association": "OWNER",
                    }
                ]
            ]
        )
    )
    result = review_run.prepare(prepared["args"])
    assert result["status"] == "prepared", result
    assert {item["state"] for item in result["records"]["decisions"]} == {"fix", "skip"}
    assert result["records"]["pr"] == {"repository": REPOSITORY, "number": 7}


@pytest.mark.parametrize("bundled", [False, True], ids=["checkout", "parent-bundle"])
def test_upstream_runner_uses_validated_upstream_remote(
    prepared: dict[str, Any],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    bundled: bool,
) -> None:
    # Hardcoding origin must fail: only upstream contains this PR and its base.
    source = prepared["parent"] / "external/resoloop"
    source.parent.mkdir()
    prepared["source"].rename(source)
    prepared["source"] = source
    prepared["args"].source_root = str(source)
    repository = "orange3134/resoloop"
    git(
        source, "remote", "set-url", "origin", "https://github.com/usaturn/resoloop.git"
    )
    git(source, "remote", "add", "upstream", f"https://github.com/{repository}.git")
    monkeypatch.setenv(
        "FAKE_GIT_ORIGIN_REMOTE", str(tmp_path / "wrong-origin-does-not-exist.git")
    )
    monkeypatch.setenv("FAKE_GIT_URL", f"https://github.com/{repository}.git")
    prepared["args"].pr = f"https://github.com/{repository}/pull/7"
    target = review_run.workspace.load_review_target()

    def upstream_pr(repo: str, number: int, **kwargs: Any) -> Any:
        assert (repo, number) == (repository, 7)
        return target.PullRequest(
            repo,
            number,
            prepared["args"].pr,
            "feature",
            prepared["head"],
            "contributor/resoloop",
            "main",
            "open",
            f"https://github.com/{repo}.git",
        )

    monkeypatch.setattr(target, "fetch_pull_request", upstream_pr)
    before = shared_refs(source)
    (source / ".git/FETCH_HEAD").write_text("unchanged fetch head\n")
    if bundled:
        parent_input(prepared, tmp_path, monkeypatch)
    result = review_run.prepare(prepared["args"])
    assert result["status"] == "prepared", result
    assert result["repository"] == repository
    assert result["base"] == git(source, "rev-parse", "main")
    assert (
        json.loads(Path(result["state_file"]).read_text())["base_remote"] == "upstream"
    )
    mark_reviewed(result)
    completed = review_run.complete(argparse.Namespace(state=result["state_file"]))
    if bundled:
        assert completed["status"] == "staged", completed
        batch = staged_batch(prepared, completed)
        review_run.finalize_parent_batch(batch)
        completed = batch.results[0].attempts[0].payload
    assert isinstance(completed, dict) and completed["status"] == "success", completed
    assert Path(str(completed["review_file"])).is_relative_to(
        prepared["parent"] / "reviews/orange3134/resoloop"
    )
    assert shared_refs(source) == before
    assert (source / ".git/FETCH_HEAD").read_text() == "unchanged fetch head\n"


def test_dsh_bundle_load_and_finalize_do_not_need_original_external_checkout(
    prepared: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A live target_checkout call in the child would fail once the original source is inaccessible.
    parent_input(prepared, tmp_path, monkeypatch)
    prepared["source"].rename(tmp_path / "inaccessible-source")
    target = review_run.workspace.load_review_target()
    live = target.fetch_pull_request

    def unavailable(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("bundle child must not resolve checkout or query GitHub")

    monkeypatch.setattr(target, "target_checkout", unavailable)
    monkeypatch.setattr(target, "fetch_pull_request", unavailable)
    result = review_run.prepare(prepared["args"])
    assert result["status"] == "prepared", result
    parent, state = review_run.workspace.load_state(result["state_file"])
    assert parent == prepared["parent"] and state["target_kind"] == "bundle"
    mark_reviewed(result)
    staged = review_run.complete(argparse.Namespace(state=result["state_file"]))
    assert staged["status"] == "staged", staged
    monkeypatch.setattr(target, "fetch_pull_request", live)
    batch = staged_batch(prepared, staged)
    review_run.finalize_parent_batch(batch)
    completed = batch.results[0].attempts[0].payload
    assert isinstance(completed, dict) and completed["status"] == "success", completed
    assert not Path(result["state_file"]).parent.exists()


def test_complete_refuses_skill_changed_after_prepare(
    prepared: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Dropping the skill digest check would publish a review made under changed instructions.
    tool_root = tmp_path / "skill-source"
    skill = tool_root / ".agents/skills/pr-review/SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("fixture review instructions\n")
    monkeypatch.setattr(review_run, "ROOT", tool_root)
    result = review_run.prepare(prepared["args"])
    mark_reviewed(result)
    skill.write_text("different review instructions\n")
    completed = review_run.complete(argparse.Namespace(state=result["state_file"]))
    assert completed["status"] == "failed" and completed["cleanup"] == "not_attempted"
    assert "skill changed" in completed["reason"]
    assert not (prepared["parent"] / result["destination"]).exists()
    assert Path(result["draft"]).exists() and Path(result["worktree"]).exists()


def test_prepare_create_failure_reports_owned_session_retained_paths(
    prepared: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    # A failure before session.json exists must not hide the already registered worktree.
    original = review_run.workspace.require_created_worktree

    def fail_after_creation(worktree: Path, commit: str) -> None:
        original(worktree, commit)
        raise review_run.workspace.WorkspaceError(
            "created worktree verification failed"
        )

    monkeypatch.setattr(
        review_run.workspace, "require_created_worktree", fail_after_creation
    )
    result = review_run.prepare(prepared["args"])
    assert result["status"] == "failed"
    assert result["reason"].startswith("created worktree verification failed")
    retained = result["retained_paths"]
    assert isinstance(retained, dict), result
    session = Path(retained["session_dir"])
    assert session.is_relative_to(Path(prepared["args"].temp_root))
    assert Path(retained["worktree"]) == session / "worktree"
    assert Path(retained["worktree"]).is_dir()
    assert Path(retained["draft"]) == session / "review-backup/observed-model.md"
    assert retained["pr_ref"] == "refs/pr-review/repos/example/syncer/7"
    assert result["pr_head"] == result["reviewed_head"] == prepared["head"]


@pytest.mark.parametrize("explicit_commit", ["head", "explicit", "unpushed"])
def test_ordinary_depth_one_checkout_reviews_whole_pr_without_shared_history_changes(
    prepared: dict[str, Any], tmp_path: Path, explicit_commit: str
) -> None:
    # A linked worktree shares shallow boundaries: fetching base alone cannot recover ancestry.
    base = git(prepared["source"], "rev-parse", "main")
    shallow = tmp_path / "ordinary-shallow"
    subprocess.run(
        [
            "git",
            "clone",
            "--quiet",
            "--depth=1",
            "--branch=feature",
            prepared["source"].as_uri(),
            str(shallow),
        ],
        check=True,
    )
    git(shallow, "remote", "set-url", "origin", f"https://github.com/{REPOSITORY}.git")
    prepared["args"].source_root = str(shallow)
    reviewed = prepared["head"]
    if explicit_commit == "unpushed":
        git(shallow, "config", "user.name", "Fixture")
        git(shallow, "config", "user.email", "fixture@example.test")
        (shallow / "local.txt").write_text("unpushed review input\n")
        git(shallow, "add", "local.txt")
        git(shallow, "commit", "-qm", "local review input")
        reviewed = git(shallow, "rev-parse", "HEAD")
    if explicit_commit != "head":
        prepared["args"].review_commit = reviewed
    boundary = (shallow / ".git/shallow").read_bytes()
    refs = shared_refs(shallow)
    fetch_head = shallow / ".git/FETCH_HEAD"
    fetch_head.write_text("user-owned fetch head\n")
    worktrees = git(shallow, "worktree", "list", "--porcelain")
    result = review_run.prepare(prepared["args"])
    assert result["status"] == "prepared", result.get("reason")
    assert result["base"] == base and result["reviewed_head"] == reviewed
    diff = git(Path(result["worktree"]), "diff", f"{base}..{reviewed}")
    assert "+a harmless fixture" in diff
    if explicit_commit == "unpushed":
        assert "+unpushed review input" in diff
    state = json.loads(Path(result["state_file"]).read_text())
    assert state["run_context"]["parent_pr_data"] is None
    assert state["target_kind"] == "bundle"
    assert (shallow / ".git/shallow").read_bytes() == boundary
    assert shared_refs(shallow) == refs
    assert fetch_head.read_text() == "user-owned fetch head\n"
    assert git(shallow, "worktree", "list", "--porcelain") == worktrees
    mark_reviewed(result)
    completed = review_run.complete(argparse.Namespace(state=result["state_file"]))
    assert completed["status"] == "success" and completed["cleanup"] == "success", (
        completed
    )
    assert (
        Path(completed["review_file"]).is_file()
        and Path(completed["findings_file"]).is_file()
    )
    assert not Path(result["state_file"]).parent.exists()
    assert (shallow / ".git/shallow").read_bytes() == boundary
    assert (
        shared_refs(shallow) == refs
        and fetch_head.read_text() == "user-owned fetch head\n"
    )


def test_dsh_reproduction_in_declared_isolated_temp_saves_evidence_before_cleanup(
    prepared: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Scratch may disappear: the saved body, not a sandbox-external path, must keep the evidence.
    parent_input(prepared, tmp_path, monkeypatch)
    isolated_temp = tmp_path / "dsh/tmp"
    isolated_temp.mkdir(parents=True)
    monkeypatch.setenv("TMPDIR", str(isolated_temp))
    result = review_run.prepare(prepared["args"])
    assert result["status"] == "prepared", result
    with tempfile.TemporaryDirectory(
        prefix="pr-review-scratch-7-", dir=os.environ["TMPDIR"]
    ) as temporary:
        scratch = Path(temporary)
        tree = scratch / "tree"
        tree.mkdir()
        archive = subprocess.run(
            ["git", "-C", result["worktree"], "archive", "HEAD"],
            check=True,
            capture_output=True,
        ).stdout
        subprocess.run(["tar", "-x", "-C", str(tree)], input=archive, check=True)
        (scratch / "input.csv").write_text("\ufefftitle\nexample\n", encoding="utf-8")
        reproduction = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "import csv; from pathlib import Path; "
                    "rows = list(csv.DictReader(Path('input.csv').open(encoding='utf-8-sig'))); "
                    "assert rows == [{'title': 'example'}]; "
                    "assert Path('tree/README.md').is_file(); print('CSV rows=1; archive readable')"
                ),
            ],
            cwd=scratch,
            check=False,
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        assert (
            reproduction.returncode == 0
            and reproduction.stdout.strip() == "CSV rows=1; archive readable"
        )
        mark_reviewed(result)
        draft = Path(result["draft"])
        draft.write_text(
            draft.read_text() + f"\n## Reproduction\n\n場所: {scratch}（隔離TMPDIR）\n"
            f"条件: BOM付きCSVと固定HEADのarchive\n結果: exit 0; {reproduction.stdout}"
        )
        staged = review_run.complete(argparse.Namespace(state=result["state_file"]))
        assert staged["status"] == "staged", staged
    assert not scratch.exists()
    batch = staged_batch(prepared, staged)
    review_run.finalize_parent_batch(batch)
    completed = batch.results[0].attempts[0].payload
    assert isinstance(completed, dict) and completed["status"] == "success", completed
    assert (
        "CSV rows=1; archive readable"
        in Path(str(completed["review_file"])).read_text()
    )
    assert not Path(result["state_file"]).parent.exists()
