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


ACCEPTED_BODY = (
    "日本語の説明\n複数行の本文\nCloses #42\nother/repo#333333 は別リポジトリの裸参照\n"
)
ISSUE_42 = {"body": "受け入れ条件\n第二行", "comments": [{"body": "承認済み"}]}


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
        "binding",
        "reviewer",
        "coverage",
        "destination",
        "head",
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
    if failure == "binding":
        request = json.loads(prepared["request_path"].read_text(encoding="utf-8"))
        request["request_id"] = "another-request"
        prepared["request_path"].write_text(json.dumps(request), encoding="utf-8")
    elif failure in {"reviewer", "coverage"}:
        findings = Path(result["findings_draft"])
        document = json.loads(findings.read_text(encoding="utf-8"))
        if failure == "reviewer":
            document["reviewer"]["provenance"]["agent_id"] = "another-agent"
        else:
            document["coverage"]["read"] = []
        findings.write_text(json.dumps(document), encoding="utf-8")
    elif failure == "destination":
        destination = prepared["parent"] / result["destination"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text("another review", encoding="utf-8")
    else:

        def moved(_repository: str, _number: int) -> str:
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
    record = only_record(prepared["parent"])
    assert (record["status"], record["failed_at"], record["reason"]) == (
        "failed", "cleanup", "cleanup refused",
    )
    assert record["outputs"]["review_sha256"] == sha256(Path(completed["review_file"]))


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


@pytest.mark.parametrize("kind", ["regular", "fifo"])
def test_fail_request_returns_without_blocking_and_preserves_failure_record(
    prepared: dict[str, Any], tmp_path: Path, kind: str,
) -> None:
    # Refusing a new request must preserve the prepared session's binding and
    # record; a valid request must still record the review failure.
    session = review_run.prepare(prepared["args"])
    assert session["status"] == "prepared", session
    argv = [sys.executable, str(SCRIPT), "fail", "--reason", "review stopped"]
    argv.extend(["--state", session["state_file"]])
    before = run_records(prepared["parent"])
    saved = {path: path.read_bytes() for path in before}
    # Keep deliberately unsafe fixtures out of retained pytest scratch, even
    # when a regression forces subprocess.run to kill and reap its child.
    with tempfile.TemporaryDirectory(dir=tmp_path, prefix="fail-request-") as area:
        target = Path(area) / "request.json"
        if kind == "fifo":
            os.mkfifo(target)
        else:
            target.write_bytes(prepared["request_path"].read_bytes())
        argv.extend(["--request", os.path.relpath(target, prepared["caller"])])
        completed = subprocess.run(
            argv, check=False, cwd=prepared["caller"], capture_output=True, text=True, timeout=5,
        )
    assert completed.returncode == 1, completed.stdout
    result = json.loads(completed.stdout)
    assert result["status"] == "failed" and result["reason"]
    assert result["request_id"] == "request-7"
    if kind == "regular":
        assert result["reason"] == "review stopped"
        failure = only_record(prepared["parent"])
        assert (failure["status"], failure["failed_at"], failure["reason"]) == (
            "failed", "review", "review stopped",
        )
    else:
        assert {path: path.read_bytes() for path in before} == saved


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


def _granted(lines: tuple[str, ...], path: object) -> int:
    """``path`` で始まる行（``<path>: <説明>`` か ``<path> and ...``）の数。"""
    return sum(line.startswith((f"{path}:", f"{path} ")) for line in lines)


@pytest.mark.parametrize("separate", [False, True])
@pytest.mark.parametrize("shallow", [False, True])
def test_helper_write_exceptions_grant_git_data_only_where_the_helper_writes_it(
    tmp_path: Path, separate: bool, shallow: bool
) -> None:
    """--source-root が親と別の repository なら、親の Git ディレクトリには保存ロックだけを許可する（#658）。

    浅い checkout では helper が履歴をセッション内の所有 Git に取得し、その checkout の Git には書かない。親と同じ
    Git でも別でも、その Git を worktree のデータの書き込み先として許可すると、writes=false の担当が利用者の Git を
    書いてよいと読む（PR #249）。
    """
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
        source_shallow=shallow,
    )
    expected = [
        tool_root,
        review_dir,
        f"{parent}/tmp/agents/pr-review-scratch-7.*",
        tool_root / ".venv",
    ]
    if shallow:
        expected.append(parent_git / "pr-review-save.lock")
    else:
        expected += [parent_git / "pr-review-save.lock", source_git] if separate else [parent_git]
    assert [_granted(lines, path) for path in expected] == [1] * len(expected)
    assert sum(line.startswith("/") for line in lines) == len(expected)
    if separate or shallow:
        assert _granted(lines, parent_git) == 0
    if shallow:
        assert _granted(lines, source_git) == 0
    same = review_run.helper_write_exceptions(
        tool_root=tool_root,
        parent=parent,
        parent_git=parent_git,
        review_dir=review_dir,
        number=7,
        source_git=parent_git,
        source_shallow=shallow,
    )
    assert same == review_run.helper_write_exceptions(
        tool_root=tool_root,
        parent=parent,
        parent_git=parent_git,
        review_dir=review_dir,
        number=7,
        source_shallow=shallow,
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


def test_upstream_runner_uses_validated_upstream_remote(
    prepared: dict[str, Any],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
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
    result = review_run.prepare(prepared["args"])
    assert result["status"] == "prepared", result
    assert result["repository"] == repository
    assert result["base"] == git(source, "rev-parse", "main")
    assert (
        json.loads(Path(result["state_file"]).read_text())["base_remote"] == "upstream"
    )
    mark_reviewed(result)
    completed = review_run.complete(argparse.Namespace(state=result["state_file"]))
    assert isinstance(completed, dict) and completed["status"] == "success", completed
    assert Path(str(completed["review_file"])).is_relative_to(
        prepared["parent"] / "reviews/orange3134/resoloop"
    )
    assert shared_refs(source) == before
    assert (source / ".git/FETCH_HEAD").read_text() == "unchanged fetch head\n"


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


@pytest.mark.parametrize("explicit_commit", ["head", "unpushed"])
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
