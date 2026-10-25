#!/usr/bin/env python3
"""Prepare and complete one noninteractive PR review using the existing workspace helper."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import stat
import subprocess
import sys
import tempfile
import time
import uuid
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType
from typing import Any, cast

# This CLI can be invoked from a different repository's review worktree.
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from tools.agent_runner.models import Request, Runtime

BINDING_KEYS = ("run_id", "request_id", "agent_id", "role")
SKILL_PATH = ".agents/skills/pr-review/SKILL.md"
EXECUTION_SECTION = "\n## Review timing\n\n<!-- pr-review:execution -->\n"


def _workspace() -> ModuleType:
    path = Path(__file__).with_name("pr_review_workspace.py")
    spec = importlib.util.spec_from_file_location("review_workspace", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


workspace = _workspace()
records = workspace._load_script(
    "review_records", ROOT / ".agents/scripts/review_records.py"
)
record = workspace._load_script(
    "review_run_record", Path(__file__).with_name("review_run_record.py")
)
FAILURES = (
    OSError,
    ValueError,
    RuntimeError,
    TypeError,
    KeyError,
    subprocess.SubprocessError,
)


def regular_bytes(path: Path, *, limit: int = 512 * 1024 * 1024) -> bytes:
    """Read once through anchored directory descriptors; never follow links or block on a FIFO."""
    if not path.is_absolute() or any(p in {".", ".."} for p in path.parts):
        raise ValueError("review artifact must be a canonical regular file")
    directory = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in path.parts[1:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
            os.close(directory)
            directory = child
        descriptor = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        with os.fdopen(descriptor, "rb") as stream:
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > limit:
                raise ValueError("review artifact must be a bounded, singly linked regular file")
            raw = stream.read(limit + 1)
            after = os.fstat(stream.fileno())
            if len(raw) > limit or (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (after.st_size, after.st_mtime_ns, after.st_ctime_ns):
                raise ValueError("review artifact changed while reading")
            return raw
    finally:
        os.close(directory)

def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate review artifact key")
        result[key] = value
    return result


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise workspace.WorkspaceError(f"cannot read JSON {path}: {error}") from error


def command(argv: list[str]) -> str:
    result = subprocess.run(argv, check=False, text=True, capture_output=True)
    if result.returncode:
        raise workspace.WorkspaceError(f"{argv[0]} failed: {result.stderr.strip()}")
    return result.stdout


def read_request(path: str) -> Request:
    """Keep caller path compatibility, but never wait for a FIFO's writer."""
    descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise workspace.WorkspaceError("Request must be a regular file")
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            return Request.model_validate_json(stream.read())
    finally:
        os.close(descriptor)


def request_binding(path: str | None) -> dict[str, str]:
    if path is None:
        return dict.fromkeys(BINDING_KEYS, "unknown")
    request = read_request(path)
    if request.work_dir.resolve(strict=True) != Path.cwd().resolve(strict=True):
        raise workspace.WorkspaceError(
            "request work_dir must match the invocation cwd, not the review worktree"
        )
    if request.result_shape != "json":
        raise workspace.WorkspaceError(
            "noninteractive review requires request result_shape=json"
        )
    return {key: str(getattr(request, key)) for key in BINDING_KEYS}


def request_deadline(path: str) -> float:
    return read_request(path).deadline_seconds


def observed_model(runtime: Runtime, supplied: str | None) -> tuple[str | None, str]:
    if runtime == "codex":
        if supplied is not None:
            raise workspace.WorkspaceError(
                "Codex model must come from the current rollout, not --model-name"
            )
        return None, "unknown"
    if runtime == "pi":
        provider, model = os.environ.get("PI_PROVIDER"), os.environ.get("PI_MODEL")
        if not provider or not model:
            raise workspace.WorkspaceError(
                "PI_PROVIDER and PI_MODEL must both be observed in this runtime"
            )
        if supplied is not None and supplied != model:
            raise workspace.WorkspaceError(
                "--model-name does not match this runtime's PI_MODEL"
            )
        return model, provider
    if not supplied:
        raise workspace.WorkspaceError(
            "exact runtime model is unavailable; fail without asking a question"
        )
    return supplied, "unknown"


def read_records(target: dict[str, Any], comments_path: str | None) -> dict[str, Any]:
    if comments_path is not None:
        payload = read_json(Path(comments_path))
    else:
        endpoint = f"repos/{target['repository']}/issues/{target['number']}/comments"
        text = command(["gh", "api", "--paginate", "--slurp", endpoint])
        try:
            payload = json.loads(text)
        except ValueError as error:
            raise workspace.WorkspaceError(
                "PR comments API did not return JSON"
            ) from error
    comments = records.comments_from_api(payload)
    return dict(
        records.read_state(
            comments,
            expected_pr={
                "repository": target["repository"],
                "number": target["number"],
            },
        )
    )


def utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_record_path(parent: Path, state: Mapping[str, Any] | None) -> Path | None:
    """state に書いた実行記録のパス。記録を持たない state（この変更より前のセッション）なら None。"""
    context = cast(dict[str, Any], (state or {}).get("run_context") or {})
    relative = context.get("run_record")
    if not relative or state is None:
        return None
    return record.safe_record_path(
        parent, str(relative), workspace.session_repository(state)
    )


def locate_record(
    parent: Path, state: Mapping[str, Any]
) -> tuple[Path | None, str | None]:
    """run_record_path の失敗も、レビューの結果を変えない記録の失敗として返す。"""
    try:
        return run_record_path(parent, state), None
    except FAILURES as error:
        return None, f"run record not updated: {error}"


def record_update(parent: Path, path: Path | None, change: Any) -> str | None:
    """実行記録を更新する。失敗してもレビューの結果は変えず、理由を返す（4.1 節）。"""
    if path is None:
        return None
    try:
        record.update(parent, path, change)
    except FAILURES as error:
        return f"run record not updated: {error}"
    return None


def record_fields(path: Path | None, error: str | None) -> dict[str, Any]:
    fields: dict[str, Any] = {"run_record": str(path) if path is not None else None}
    if error is not None:
        fields["run_record_error"] = error
    return fields


def helper_write_exceptions(
    *,
    tool_root: Path,
    parent: Path,
    parent_git: Path,
    review_dir: str,
    number: int,
    source_git: Path | None = None,
    source_shallow: bool,
) -> tuple[str, ...]:
    """この helper が管理する書き込み先。呼び出し側が runner の作業範囲の指示に、許可する例外として載せる。

    writes=False は、レビュー対象・どの checkout の追跡ファイル・他の担当の成果を変えないという意味で、
    ここに挙げる helper の書き込みはそれに当たらない（references/noninteractive.md）。loop の inspect と
    review-fix-planning の self-review が使う。パスを事前に決められるものは、パスを行の先頭に置く。

    review_dir は保存先のディレクトリで、ブランチ名を知らない呼び出し側は ``#<PR>-*`` のパターンを渡す。
    source_git は ``--source-root`` の checkout の Git の共有ディレクトリ。親（parent_git）と違えば、
    helper は review 用の worktree・ref・オブジェクトをそちらに書き、親には保存ロックだけを書く。
    source_shallow はその checkout が浅いか（``pr_review_workspace.uses_owned_history``）。浅ければ helper は
    履歴をセッション内の所有 Git に取得し、その checkout の Git は読むだけなので、親と同じ Git でも保存ロックだけを許可する。
    """
    worktree_data = "the Git objects, refs and worktree registrations that the helper adds and removes for its review worktree"
    save_lock = f"{parent_git / 'pr-review-save.lock'}: the helper's save lock"
    if source_shallow:
        git_data: tuple[str, ...] = (save_lock,)
    elif source_git is None or source_git == parent_git:
        git_data = (
            (
                f"{parent_git}: the helper's save lock (pr-review-save.lock) and {worktree_data} (a submodule's Git data "
                "is here too)"
            ),
        )
    else:
        git_data = (save_lock, f"{source_git}: {worktree_data} in the --source-root checkout")
    session = "its review worktree, backup and state belong to the helper"
    if source_shallow:
        session = (
            "the Git repository it fetches the history into (the checkout is shallow and its Git is only read), "
            "its review worktree, backup and state belong to the helper"
        )
    return (
        (
            f"{tool_root}: the source checkout (tool_root) that holds the pr-review skill, its references and its "
            "helper. Read them and run the helper from there; do not edit it"
        ),
        (
            f"{review_dir}: the run records and the saved review and candidates that the helper writes; "
            "do not edit them by hand"
        ),
        *git_data,
        (
            f"{parent / 'tmp/agents'}/pr-review-scratch-{number}.*: one scratch directory created with "
            "agent_tmp.py mkdir as pr-review allows; remove it when it is no longer needed"
        ),
        (
            f"the session that the helper's prepare creates (pr-review-{number}-* in the temporary directory): "
            f"{session}. Write only the "
            "draft and findings_draft that prepare returns, and leave no files in the review worktree"
        ),
        (
            f"{tool_root / '.venv'} and uv's cache: the environment that "
            "`uv run --project <tool_root> --locked` maintains"
        ),
    )


def prepare(args: argparse.Namespace) -> dict[str, Any]:
    started_at, started_monotonic = utc_now(), time.monotonic()
    request_path = Path(args.request) if args.request else None
    binding = request_binding(args.request)
    model, provider = observed_model(args.runtime, args.model_name)
    model_name, _source = workspace.resolve_runtime_model_name(model)
    parent = workspace._target_call("default_parent_root")
    target = workspace._target_call(
        "resolve", args.pr, parent_root=parent,
        code_root=Path(args.source_root) if args.source_root else None,
    )
    skill = {
        "path": SKILL_PATH,
        "sha256": hashlib.sha256((ROOT / SKILL_PATH).read_bytes()).hexdigest(),
    }
    provenance = {
        **binding,
        "provider": provider,
        "effort": "unknown",
        "session_id": "unknown",
        "cli_version": "unknown",
        "skills": [skill],
    }
    identity = {
        "model": model or model_name,
        "runtime": args.runtime,
        "provenance": provenance,
    }
    review_kind = "commit" if args.review_commit else "pr_head"
    # 記録の reviewed_head は完全なハッシュなので、create と同じ検査を記録より先に行う
    workspace.artifact_model(model_name, args.review_commit)
    # 記録の名前にセッションの接尾辞を使うので、セッションの名前を先に決めて create に渡す
    session_name, suffix = record.new_session_name(int(target["number"]))
    # 試行 ID は呼び出し元だけが知る。残った試行を abandon で指定するときの証拠になる（#134）
    attempt_id = uuid.uuid4().hex
    temp_root = (
        Path(args.temp_root).resolve()
        if args.temp_root
        else Path(tempfile.gettempdir()).resolve()
    )
    try:
        record_path = record.safe_record_path(
            parent,
            record.record_relative(target, started_at, model_name, suffix),
            str(target["repository"]),
        )
        record.create(
            parent,
            record_path,
            record.started_document(
                target=target,
                review_kind=review_kind,
                reviewed_head=args.review_commit or target["head_sha"],
                reviewer=identity,
                started_at=started_at,
            ),
        )
    except FAILURES as error:
        raise workspace.WorkspaceError(f"cannot write run record: {error}") from error

    def failed_prepare(reason: str) -> dict[str, Any]:
        elapsed = time.monotonic() - started_monotonic
        seconds = {"prepare_seconds": elapsed, "total_seconds": elapsed}
        error = record_update(
            parent,
            record_path,
            record.mark_failed(
                "prepare", reason, finished_at=utc_now(), seconds=seconds
            ),
        )
        return record_fields(record_path, error)

    try:
        decision_state = read_records(target, args.records_comments)
        session = workspace.create(
            argparse.Namespace(
                target=json.dumps(target),
                model_name=model,
                review_commit=args.review_commit,
                source_root=args.source_root,
                temp_root=str(temp_root),
                session_dir=str(temp_root / session_name),
                attempt_id=attempt_id,
            )
        )
    except FAILURES as error:
        retained = None
        session_dir = temp_root / session_name
        if session_dir.is_dir():
            draft, _destination = workspace.review_artifact_paths(
                session_dir / "review-backup",
                target["head_ref"],
                model_name,
                pr_number=target["number"],
                repository=target["repository"],
                review_commit=args.review_commit,
            )
            retained = retained_paths(
                {
                    "worktree": str(session_dir / "worktree"),
                    "draft": str(draft),
                    "pr_number": target["number"],
                    "repository": target["repository"],
                }
            )
        return {
            **result_fields(None),
            "pr_head": target["head_sha"],
            "reviewed_head": args.review_commit or target["head_sha"],
            "retained_paths": retained,
            "attempt_id": attempt_id if retained is not None else None,
            **binding,
            "status": "failed",
            "reason": str(error),
            "repository": target["repository"],
            "pr_number": target["number"],
            **failed_prepare(str(error)),
        }
    state_file = Path(session["state_file"])
    state: dict[str, Any] = {}
    try:
        _parent, state = workspace.load_state(str(state_file))
        reviewer = {**identity, "review_file": session["review_file"]}
        context = {
            "binding": binding,
            "request_path": str(request_path.resolve(strict=True))
            if request_path is not None
            else None,
            "request_sha256": workspace.file_digest(request_path)
            if request_path is not None
            else None,
            "started_at": started_at,
            "started_monotonic": started_monotonic,
            "reviewer": reviewer,
            "skill": skill,
            "run_record": record.record_relative(target, started_at, model_name, suffix),
            "attempt_id": attempt_id,
        }
        state["run_context"] = context
        workspace.write_json(state_file, state)
        base_ref = target["base_ref"]
        # Keep the base private to this owned worktree, including during concurrent reviews.
        worktree = Path(session["worktree"])
        ref = "refs/worktree/pr-review-base"
        workspace.git(
            worktree,
            "fetch",
            "--quiet",
            "--no-write-fetch-head",
            "--no-tags",
            "--refmap=",
            target["base_remote"],
            f"+refs/heads/{base_ref}:{ref}",
        )
        base = workspace.git(worktree, "merge-base", ref, state["commit"])
        document: dict[str, Any] = {
            "schema": "review-findings/v2",
            "kind": "candidates",
            "source": "reviewer",
            "pr": {"repository": target["repository"], "number": target["number"]},
            "reviewed_head": state["commit"],
            "base": base,
            "reviewer": reviewer,
            "skill": skill,
            "timing": {
                "started_at": started_at,
                "finished_at": started_at,
                "seconds": None,
                "waiting_seconds": None,
            },
            "coverage": {"read": [], "checks": [], "declined": []},
            "findings": [],
            "unverified_candidates": [],
        }
        context["immutable"] = {
            key: document[key]
            for key in (
                "schema",
                "kind",
                "source",
                "pr",
                "reviewed_head",
                "base",
                "reviewer",
                "skill",
            )
        }
        fingerprint = state["destination_fingerprint"]
        inputs = {
            "request": (
                {
                    "sha256": context["request_sha256"],
                    "deadline_seconds": request_deadline(args.request),
                }
                if args.request
                else None
            ),
            "previous_review": {"sha256": fingerprint["sha256"]}
            if fingerprint["kind"] == "file"
            else None,
            "records": record.records_input(decision_state),
            "diff": record.diff_input(worktree, str(base), state["commit"]),
        }
        findings_draft = Path(session["findings_draft"])
        workspace.write_json(findings_draft, document)
        # abandon は、この digest と同じ雛形だけを helper のものとして消す。digest の前に止まれば雛形を残す
        context["findings_scaffold"] = {
            "name": findings_draft.name,
            "sha256": workspace.file_digest(findings_draft),
        }
        context["prepared_monotonic"] = time.monotonic()
        workspace.write_json(state_file, state)
    except (OSError, ValueError, RuntimeError) as error:
        return {
            **result_fields(state),
            **binding,
            "status": "failed",
            "reason": str(error),
            "repository": target["repository"],
            "pr_number": target["number"],
            "pr_head": session["pr_head"],
            "reviewed_head": session["reviewed_head"],
            "attempt_id": attempt_id,
            "state_file": str(state_file),
            "retained_paths": retained_paths(
                {
                    **session,
                    "pr_number": target["number"],
                    "repository": target["repository"],
                }
            ),
            **failed_prepare(str(error)),
        }
    record_error = record_update(
        parent,
        record_path,
        record.mark_prepared(
            mode="Update" if state["previous_review"] is not None else "Initial",
            base=str(base),
            inputs=inputs,
            prepare_seconds=context["prepared_monotonic"] - started_monotonic,
        ),
    )
    return {
        **session,
        **binding,
        "status": "prepared",
        "attempt_id": attempt_id,
        "repository": target["repository"],
        "pr_number": target["number"],
        "pr_url": target["url"],
        "base": base,
        "started_at": started_at,
        "reviewer": reviewer,
        "records": decision_state,
        "diff_command": [
            "git",
            "-C",
            session["worktree"],
            "diff",
            "--find-renames",
            f"{base}..{state['commit']}",
        ],
        **record_fields(record_path, record_error),
    }


def retained_paths(state: dict[str, Any]) -> dict[str, str]:
    draft = state["draft"]
    return {
        "worktree": state["worktree"],
        "draft": draft,
        "session_dir": str(Path(state["worktree"]).parent),
        "pr_ref": workspace.pinned_review_ref(
            state["pr_number"],
            state.get("pr_repo") or state.get("pr_repository") or state["repository"],
        ),
    }


def result_fields(state: dict[str, Any] | None = None) -> dict[str, Any]:
    context = (state or {}).get("run_context", {})
    return {
        "schema_version": 1,
        **context.get("binding", dict.fromkeys(BINDING_KEYS, "unknown")),
        "repository": workspace.session_repository(state) if state else None,
        "pr_number": (state or {}).get("pr_number"),
        "pr_head": (state or {}).get("pr_head"),
        "reviewed_head": (state or {}).get("commit"),
        "attempt_id": context.get("attempt_id"),
        "review_file": None,
        "findings_file": None,
        "active_findings": None,
        "cleanup": "not_attempted",
        "cleanup_details": None,
        "retained_paths": None,
        "reason": None,
    }


def complete(args: argparse.Namespace) -> dict[str, Any]:
    parent, state = workspace.load_state(args.state)
    context_value = state.get("run_context")
    if not isinstance(context_value, dict) or "immutable" not in context_value:
        raise workspace.WorkspaceError("state is missing the prepared request context")
    context = cast(dict[str, Any], context_value)
    record_path, located = locate_record(parent, state)
    complete_started = time.monotonic()
    prepared = context.get("prepared_monotonic")
    review_seconds = (
        complete_started - prepared if isinstance(prepared, (int, float)) else None
    )
    stage = "complete"
    save_started: float | None = None
    try:
        backup = Path(args.state).parent / "review-backup"
        if str(backup) != state["backup_dir"] or backup.resolve(strict=True) != backup:
            raise workspace.WorkspaceError("backup does not match the pinned session path")
        pinned_draft, pinned_destination = workspace.review_artifact_paths(
            backup, state["head_branch"], state["model_name"],
            pr_number=state["pr_number"], repository=state["pr_repo"],
            review_commit=state.get("review_commit"),
        )
        if str(pinned_draft) != state["draft"] or pinned_destination != state["destination"]:
            raise workspace.WorkspaceError("draft or destination does not match the pinned review path")
        request_path = context["request_path"]
        if request_path is not None and (
            workspace.file_digest(Path(request_path)) != context["request_sha256"]
            or request_binding(request_path) != context["binding"]
        ):
            raise workspace.WorkspaceError("request binding changed during review")
        if (
            hashlib.sha256((ROOT / SKILL_PATH).read_bytes()).hexdigest()
            != context["skill"]["sha256"]
        ):
            raise workspace.WorkspaceError("loaded review skill changed during review")
        draft = pinned_draft
        findings, _destination = workspace.findings_artifact_paths(
            Path(state["backup_dir"]),
            state["head_branch"],
            state["model_name"],
            pr_number=state["pr_number"],
            commit=state["commit"],
            repository=state["pr_repo"],
            review_commit=state.get("review_commit"),
        )
        for output in (draft, findings):
            if output.resolve(strict=False) != output or (output.exists() and output.stat().st_nlink != 1):
                raise workspace.WorkspaceError("session artifact must not be linked outside its fixed path")
        draft_bytes = regular_bytes(draft, limit=16 * 1024 * 1024)
        findings_bytes = regular_bytes(findings, limit=16 * 1024 * 1024)
        markdown = draft_bytes.decode("utf-8")
        document_value = json.loads(findings_bytes, object_pairs_hook=unique_object)
        if not isinstance(document_value, dict):
            raise workspace.WorkspaceError("candidates must be a JSON object")
        document = cast(dict[str, Any], document_value)
        if any(
            document.get(key) != value for key, value in context["immutable"].items()
        ):
            raise workspace.WorkspaceError(
                "candidates do not match the prepared target or reviewer"
            )
        coverage = document.get("coverage")
        if not isinstance(coverage, dict) or not cast(dict[str, Any], coverage).get(
            "read"
        ):
            raise workspace.WorkspaceError(
                "review coverage is missing; an unreviewed scaffold is not zero findings"
            )
        timing = {
            "started_at": context["started_at"],
            "finished_at": utc_now(),
            "seconds": round(time.monotonic() - context["started_monotonic"], 6),
            "waiting_seconds": None,
        }
        document["timing"] = timing
        execution = {
            "reviewer": context["reviewer"],
            "timing": timing,
            "pr_head": state["pr_head"],
            "reviewed_head": state["commit"],
            "review_kind": "commit" if state.get("review_commit") else "pr_head",
        }
        # Repeating a refused completion must not accumulate misleading timing blocks.
        markdown = markdown.split(EXECUTION_SECTION, 1)[0].rstrip() + EXECUTION_SECTION
        markdown += "```json\n" + json.dumps(execution, ensure_ascii=False, indent=2) + "\n```\n"
        review_findings = workspace.load_review_findings()
        try:
            validated = review_findings.validate_document(document)
            review_findings.check_pair(markdown, validated)
        except review_findings.FindingsError as error:
            raise workspace.WorkspaceError("findings draft is invalid: " + "; ".join(error.problems)) from error
        workspace.write_json(findings, document)
        draft.write_text(markdown, encoding="utf-8")
        stage = "save"
        save_started = time.monotonic()
        saved = workspace.save(argparse.Namespace(state=args.state, findings=True))
    except FAILURES as error:
        now = time.monotonic()
        seconds = {
            "review_seconds": review_seconds,
            "save_seconds": now - save_started if save_started is not None else None,
            "total_seconds": now - context["started_monotonic"],
        }
        record_error = record_update(
            parent,
            record_path,
            record.mark_failed(
                stage, str(error), finished_at=utc_now(), seconds=seconds
            ),
        )
        return {
            **result_fields(state),
            "status": "failed",
            "reason": str(error),
            "state_file": args.state,
            "retained_paths": retained_paths(state),
            **record_fields(record_path, record_error or located),
        }
    save_seconds = time.monotonic() - save_started
    # 保存は済んでいる。記録の参照を作れなくても、レビューの結果と後片付けは変えない
    outputs: dict[str, Any] | None = None
    try:
        outputs = record.outputs_document(
            review_path=Path(saved["destination"]),
            findings_path=Path(saved["findings_destination"]),
            document=document,
        )
    except FAILURES as error:
        located = located or f"run record not updated: {error}"
    cleanup_started = time.monotonic()
    result = {
        **result_fields(state),
        "status": "success",
        "review_file": saved["destination"],
        "findings_file": saved["findings_destination"],
        "active_findings": len(document["findings"]),
        "cleanup": "success",
        "reviewer": context["reviewer"],
        "timing": timing,
        "save_seconds": save_seconds,
    }
    try:
        result["cleanup_details"] = workspace.cleanup(
            argparse.Namespace(state=args.state)
        )
    except (OSError, ValueError, RuntimeError) as error:
        result.update(
            status="failed",
            cleanup="failed",
            reason=str(error),
            state_file=args.state,
            retained_paths=retained_paths(state),
        )
    result["cleanup_seconds"] = time.monotonic() - cleanup_started
    result["total_seconds"] = time.monotonic() - context["started_monotonic"]
    seconds = {
        "review_seconds": review_seconds,
        "save_seconds": save_seconds,
        "cleanup_seconds": result["cleanup_seconds"],
        "total_seconds": result["total_seconds"],
    }
    if outputs is None:
        result.update(record_fields(record_path, located))
        return result
    finished_at = utc_now()
    change = (
        record.mark_success(outputs, finished_at=finished_at, seconds=seconds)
        if result["status"] == "success"
        else record.mark_failed(
            "cleanup",
            result["reason"],
            finished_at=finished_at,
            seconds=seconds,
            outputs=outputs,
        )
    )
    result.update(
        record_fields(
            record_path, record_update(parent, record_path, change) or located
        )
    )
    return result


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)
    start = commands.add_parser("prepare")
    start.add_argument("--pr", required=True)
    start.add_argument(
        "--runtime",
        required=True,
        choices=("claude-code", "devin", "pi", "codex", "cursor"),
    )
    start.add_argument("--model-name")
    start.add_argument("--request")
    start.add_argument("--review-commit")
    start.add_argument("--source-root")
    start.add_argument("--records-comments")
    start.add_argument("--temp-root")
    start.set_defaults(handler=prepare)
    finish = commands.add_parser("complete")
    finish.add_argument("--state", required=True)
    finish.set_defaults(handler=complete)
    failure = commands.add_parser("fail")
    failure.add_argument("--state")
    failure.add_argument("--request")
    failure.add_argument("--reason", required=True)
    failure.add_argument(
        "--abandon",
        action="store_true",
        help="記録の後に、未保存の draft が無ければ prepare が作った試行を消す（--state が要る）",
    )
    runner = commands.add_parser(
        "attach-runner", help="ランナーの result.json の観測値を実行記録に結び付ける"
    )
    runner.add_argument("--result", required=True, type=Path)
    return root


def fail_review(parent: Path, state: Mapping[str, Any], reason: str) -> dict[str, Any]:
    """モデルが prepare の後に止めた（failed_at: review）。終わった記録は書き換えない。"""
    path, located = locate_record(parent, state)
    context = cast(dict[str, Any], state.get("run_context") or {})
    now = time.monotonic()
    prepared, started = (
        context.get("prepared_monotonic"),
        context.get("started_monotonic"),
    )
    seconds = {
        "review_seconds": now - prepared
        if isinstance(prepared, (int, float))
        else None,
        "total_seconds": now - started if isinstance(started, (int, float)) else None,
    }
    error = record_update(
        parent,
        path,
        record.mark_failed("review", reason, finished_at=utc_now(), seconds=seconds),
    )
    return record_fields(path, error or located)


def abandon_stopped(state_file: str) -> dict[str, Any]:
    """fail --abandon: 止めた試行を abandon と同じ条件で消す。消せなければ残し、理由を返す（#134）。"""
    try:
        session_dir = Path(state_file).resolve(strict=True).parent
        attempt_id = workspace.journal_attempt(session_dir / workspace.JOURNAL_NAME)
        if attempt_id is None:
            raise workspace.WorkspaceError("create journal names no attempt; keep the session")
        details = workspace.abandon_session_dir(session_dir, attempt_id)
    except FAILURES as error:
        return {"cleanup": "failed", "cleanup_details": {"error": str(error)}}
    return {"cleanup": "success", "cleanup_details": details, "retained_paths": None}


def attach_runner(result_path: Path) -> dict[str, Any]:
    """書き先は親の main worktree の reviews/ の実行記録だけ。worker が返したパスは使わない。"""
    try:
        parent = workspace._target_call("default_parent_root")
        return record.attach_runner(result_path, parent)
    except FAILURES as error:
        return {
            "schema_version": 1,
            "status": "failed",
            "result_file": str(result_path),
            "reason": str(error),
        }


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.command == "attach-runner":
        result = attach_runner(args.result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if result["status"] == "failed" else 0
    parent: Path | None = None
    state: dict[str, Any] | None = None
    try:
        if getattr(args, "state", None):
            parent, state = workspace.load_state(args.state)
        if args.command == "fail":
            if args.abandon and state is None:
                raise workspace.WorkspaceError("fail --abandon requires --state")
            result = {**result_fields(state), "status": "failed", "reason": args.reason}
            if args.request:
                result.update(request_binding(args.request))
            if parent is not None and state is not None:
                result.update(fail_review(parent, state, args.reason))
                if args.abandon:
                    result.update(abandon_stopped(args.state))
        else:
            result = args.handler(args)
    except FAILURES as error:
        result = {**result_fields(state), "status": "failed", "reason": str(error)}
        if getattr(args, "request", None):
            try:
                result.update(request_binding(args.request))
            except OSError, ValueError, RuntimeError:
                pass
        if getattr(args, "state", None):
            result["state_file"] = args.state
        if parent is not None and state is not None:
            result.update(record_fields(*locate_record(parent, state)))
    # fail --abandon で消した試行のパスを、残したものとして返さない
    if result["status"] == "failed" and state is not None and result.get("cleanup") != "success":
        result["retained_paths"] = retained_paths(state)
    result.setdefault("run_record", None)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result["status"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
