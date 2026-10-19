#!/usr/bin/env python3
"""Prepare and complete one noninteractive PR review using the existing workspace helper."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable, Mapping
from contextlib import ExitStack
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType
from typing import Any, cast

# This CLI can be invoked from a different repository's review worktree.
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from tools.agent_runner.dsh_identity import read_session_identity
from tools.agent_runner.dsh_paths import review_exports, review_scratch
from tools.agent_runner.models import BatchResult, Identity, Request, Runtime

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
parent_data = workspace._load_script(
    "pr_review_parent", Path(__file__).with_name("pr_review_parent.py")
)
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


def request_binding(
    path: str | None, *, work_dir: Path | None = None, request: Request | None = None
) -> dict[str, str]:
    if path is None:
        return dict.fromkeys(BINDING_KEYS, "unknown")
    if request is None:
        request = Request.model_validate_json(Path(path).read_text(encoding="utf-8"))
    if request.work_dir.resolve(strict=True) != (work_dir or Path.cwd()).resolve(
        strict=True
    ):
        raise workspace.WorkspaceError(
            "request work_dir must match the invocation cwd, not the review worktree"
        )
    if request.result_shape != "json":
        raise workspace.WorkspaceError(
            "noninteractive review requires request result_shape=json"
        )
    return {key: str(getattr(request, key)) for key in BINDING_KEYS}


def read_dsh_request(path: str) -> tuple[Path, bytes, Request]:
    canonical = parent_data.canonical_request_path(Path(path))
    raw = parent_data.regular_bytes(canonical)
    return canonical, raw, Request.model_validate_json(raw)


def request_deadline(path: str) -> float:
    return Request.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    ).deadline_seconds


def observed_dsh_identity() -> Identity:
    if (
        os.environ.get("DSH_SHELL") != "1"
        or os.environ.get("DSH_PROFILE") != "headless"
    ):
        raise workspace.WorkspaceError(
            "DSH headless identity must be read inside its own bash tool"
        )
    home, session = os.environ.get("DSH_HOME"), os.environ.get("DSH_SESSION_ID")
    if not home or not session:
        raise workspace.WorkspaceError(
            "DSH_HOME and DSH_SESSION_ID must both be observed"
        )
    return read_session_identity(Path(home), Path.cwd(), session, live=True)


def observed_model(runtime: Runtime, supplied: str | None) -> tuple[str | None, str]:
    if runtime == "dsh":
        identity = observed_dsh_identity()
        if supplied is not None and supplied != identity.model:
            raise workspace.WorkspaceError(
                "--model-name does not match the observed DSH model"
            )
        return identity.model, identity.provider or "unknown"
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
    if context.get("local_record") and state is not None:
        expected = Path(state["worktree"]).parent.parent / "run.json"
        if context["local_record"] != str(expected):
            raise workspace.WorkspaceError("local run record escaped its session scratch")
        return expected
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
        record.update(parent, path, change, local=path.name == "run.json")
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
    runtime: Runtime | None = None,
) -> tuple[str, ...]:
    """この helper が管理する書き込み先。呼び出し側が runner の作業範囲の指示に、許可する例外として載せる。

    writes=False は、レビュー対象・どの checkout の追跡ファイル・他の担当の成果を変えないという意味で、
    ここに挙げる helper の書き込みはそれに当たらない（references/noninteractive.md）。loop の inspect と
    review-fix-planning の self-review が使う。パスを事前に決められるものは、パスを行の先頭に置く。

    runtime="dsh" は共有保存先・保存ロック・共有 Git を含めず、attempt 内の例外だけを返す。
    review_dir は保存先のディレクトリで、ブランチ名を知らない呼び出し側は ``#<PR>-*`` のパターンを渡す。
    source_git は ``--source-root`` の checkout の Git の共有ディレクトリ。親（parent_git）と違えば、
    helper は review 用の worktree・ref・オブジェクトをそちらに書き、親には保存ロックだけを書く
    （DSH は専用 bundle repository に取得するので checkout の Git には書かない。一覧はその分だけ広い）。
    """
    if runtime == "dsh":
        return (
            f"{tool_root}: read the skill and run its helper without editing this checkout",
            "this attempt's review-scratch: only the helper writes its private session, Git repository and local run.json",
            "this attempt's dsh/tmp/exports/review.md and findings.json: use native write/edit only for the draft paths returned by prepare",
            "this attempt's isolated HOME and TMPDIR: uv environment/cache and disposable reproduction inputs; stop on a permission refusal",
        )
    worktree_data = "the Git objects, refs and worktree registrations that the helper adds and removes for its review worktree"
    if source_git is None or source_git == parent_git:
        git_data = (
            (
                f"{parent_git}: the helper's save lock (pr-review-save.lock) and {worktree_data} (a submodule's Git data "
                "is here too; a validated parent bundle uses owned Git inside the helper's session instead)"
            ),
        )
    else:
        git_data = (
            f"{parent_git / 'pr-review-save.lock'}: the helper's save lock",
            f"{source_git}: {worktree_data} in the --source-root checkout",
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
            "its review worktree, backup and state belong to the helper. Write only the "
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
    request_raw: bytes | None = None
    request: Request | None = None
    if args.runtime == "dsh":
        if not args.request:
            raise workspace.WorkspaceError(
                "DSH review requires an authenticated parent's Request"
            )
        request_path, request_raw, request = read_dsh_request(args.request)
    binding = request_binding(args.request, request=request)
    model, provider = observed_model(args.runtime, args.model_name)
    artifact_identity = f"{provider}/{model}" if args.runtime == "dsh" else model
    model_name, _source = workspace.resolve_runtime_model_name(artifact_identity)
    snapshot = None
    if args.runtime == "dsh":
        assert request is not None
        snapshot = parent_data.load(
            workspace, parent_data.descriptor_from_prompt(request.prompt), args.pr
        )
        if snapshot["review_commit"] != args.review_commit:
            raise workspace.WorkspaceError(
                "review commit does not match the parent snapshot"
            )
        target = snapshot["target"]
        requested_head = parent_data.parameters_from_prompt(request.prompt).get(
            "pr_head"
        )
        if requested_head is not None and requested_head != target["head_sha"]:
            raise workspace.WorkspaceError(
                "parent snapshot does not match Request PR HEAD"
            )
        parent = Path(target["parent_root"])
    else:
        parent = workspace._target_call("default_parent_root")
        target = workspace._target_call(
            "resolve",
            args.pr,
            parent_root=parent,
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
    if args.runtime == "dsh":
        observed = observed_dsh_identity()
        provenance.update(
            effort=observed.effort or "unknown",
            session_id=observed.session_id or "unknown",
        )
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
    if snapshot is not None and request_raw is not None:
        suffix = hashlib.sha256(request_raw).hexdigest()[:8]
        session_name = f"pr-review-{target['number']}-{suffix}"
    temp_root = (
        review_scratch(request_path.parent)
        if snapshot is not None and request_path is not None
        else Path(args.temp_root).resolve()
        if args.temp_root
        else Path(tempfile.gettempdir()).resolve()
    )
    local_record = snapshot is not None
    if local_record:
        assert request_path is not None
        temp_root.mkdir(parents=True, exist_ok=True)
        review_exports(request_path.parent).mkdir(parents=True, exist_ok=True)
    try:
        record_path = temp_root / "run.json" if local_record else record.safe_record_path(
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
            local=local_record,
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
        decision_state = (
            dict(
                records.read_state(
                    records.comments_from_api(snapshot["comments"]),
                    expected_pr={
                        "repository": target["repository"],
                        "number": target["number"],
                    },
                )
            )
            if snapshot is not None
            else read_records(target, args.records_comments)
        )
        # Shallow boundaries are shared by linked worktrees. Complete history must
        # be fetched into owned Git, never by unshallowing the user's checkout.
        git_input = snapshot
        with ExitStack() as inputs:
            if (
                snapshot is None
                and workspace.git(
                    Path(target["target_root"]), "rev-parse", "--is-shallow-repository"
                )
                == "true"
            ):
                directory = Path(
                    inputs.enter_context(
                        tempfile.TemporaryDirectory(prefix="pr-review-input-")
                    )
                )
                descriptor = parent_data._populate(
                    workspace, args, target, directory, [], None, {}
                )
                git_input = parent_data.load(workspace, descriptor, args.pr)
            session = workspace.create(
                argparse.Namespace(
                    target=json.dumps(target),
                    model_name=artifact_identity,
                    review_commit=args.review_commit,
                    source_root=args.source_root,
                    private_clone=args.runtime == "dsh",
                    parent_input=git_input,
                    temp_root=str(temp_root),
                    session_dir=str(temp_root / session_name),
                )
            )
            if (
                snapshot is None
                and git_input is not None
                and workspace.current_pr_head(target["repository"], target["number"])
                != target["head_sha"]
            ):
                raise workspace.WorkspaceError(
                    "PR head changed after fetch; resolve again without saving"
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
            "request_path": str(request_path)
            if request_raw is not None
            else str(request_path.resolve(strict=True))
            if request_path is not None
            else None,
            "request_sha256": hashlib.sha256(request_raw).hexdigest()
            if request_raw is not None
            else workspace.file_digest(request_path)
            if request_path is not None
            else None,
            "started_at": started_at,
            "started_monotonic": started_monotonic,
            "reviewer": reviewer,
            "skill": skill,
            "run_record": record.record_relative(target, started_at, model_name, suffix),
            "local_record": str(record_path) if local_record else None,
            "parent_pr_data": snapshot["descriptor"] if snapshot is not None else None,
        }
        state["run_context"] = context
        workspace.write_json(state_file, state)
        base_ref = target["base_ref"]
        # Keep the base private to this owned worktree, including during concurrent reviews.
        worktree = Path(session["worktree"])
        ref = "refs/worktree/pr-review-base"
        if git_input is None:
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
        else:
            workspace.git(worktree, "update-ref", ref, git_input["base"])
        base = workspace.git(worktree, "merge-base", ref, state["commit"])
        if git_input is not None and base != git_input["base"]:
            raise workspace.WorkspaceError("bundle does not match the prepared base")
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
                    "deadline_seconds": request.deadline_seconds
                    if request is not None
                    else request_deadline(args.request),
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
        context["prepared_monotonic"] = time.monotonic()
        workspace.write_json(state_file, state)
        if local_record:
            assert request_path is not None
            outbox = review_exports(request_path.parent)
            session["draft"] = str(outbox / "review.md")
            session["findings_draft"] = str(outbox / "findings.json")
        workspace.write_json(Path(session["findings_draft"]), document)
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
        "repository": target["repository"],
        "pr_number": target["number"],
        "pr_url": target["url"],
        "base": base,
        "started_at": started_at,
        "reviewer": reviewer,
        "records": decision_state,
        "requirements": snapshot["requirements"] if snapshot is not None else None,
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
    context = state.get("run_context", {})
    draft = state["draft"]
    if context.get("parent_pr_data") is not None and context.get("local_record"):
        draft = str(review_exports(Path(context["request_path"]).parent) / "review.md")
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
        "review_file": None,
        "findings_file": None,
        "active_findings": None,
        "cleanup": "not_attempted",
        "cleanup_details": None,
        "retained_paths": None,
        "reason": None,
    }


def complete(
    args: argparse.Namespace,
    *,
    parent_request: Request | None = None,
    parent_identity: Identity | None = None,
    captured_exports: tuple[bytes, bytes] | None = None,
    validate_only: bool = False,
    prepared_state: tuple[Path, dict[str, Any]] | None = None,
    cleanup_child: Callable[[], None] | None = None,
) -> dict[str, Any]:
    if prepared_state is not None:
        if not validate_only or parent_request is None:
            raise workspace.WorkspaceError("unloaded state is only supported for parent preflight")
        parent, state = prepared_state
    else:
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
        if context["reviewer"]["runtime"] == "dsh":
            observed = (
                parent_identity
                if parent_identity is not None
                else observed_dsh_identity()
            )
            previous = context["reviewer"]
            metadata = previous["provenance"]
            if (
                observed.model,
                observed.provider,
                observed.effort or "unknown",
                observed.session_id,
            ) != (
                previous["model"],
                metadata["provider"],
                metadata["effort"],
                metadata["session_id"],
            ):
                raise workspace.WorkspaceError(
                    "observed DSH route changed during review"
                )
        request_path = context["request_path"]
        if request_path is not None and (
            workspace.file_digest(Path(request_path)) != context["request_sha256"]
            or request_binding(
                request_path,
                work_dir=parent_request.work_dir if parent_request else None,
            )
            != context["binding"]
        ):
            raise workspace.WorkspaceError("request binding changed during review")
        if (
            hashlib.sha256((ROOT / SKILL_PATH).read_bytes()).hexdigest()
            != context["skill"]["sha256"]
        ):
            raise workspace.WorkspaceError("loaded review skill changed during review")
        if context.get("parent_pr_data") is not None:
            snapshot = parent_data.load(
                workspace,
                context["parent_pr_data"],
                f"https://github.com/{state['pr_repo']}/pull/{state['pr_number']}",
            )
            if (
                snapshot["target"]["head_sha"],
                snapshot["base"],
                snapshot["review_commit"] or snapshot["target"]["head_sha"],
            ) != (state["pr_head"], context["immutable"]["base"], state["commit"]):
                raise workspace.WorkspaceError("parent snapshot target changed")
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
        if context.get("parent_pr_data") is not None and parent_request is None:
            outbox = review_exports(Path(context["request_path"]).parent)
            draft, findings = outbox / "review.md", outbox / "findings.json"
        draft_bytes, findings_bytes = captured_exports if captured_exports is not None else (
            parent_data.regular_bytes(draft, limit=16 * 1024 * 1024),
            parent_data.regular_bytes(findings, limit=16 * 1024 * 1024),
        )
        markdown = draft_bytes.decode("utf-8")
        document_value = json.loads(findings_bytes, object_pairs_hook=parent_data.unique_object)
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
        staged = context.get("staged")
        if parent_request is not None and (
            staged is None
            or staged["draft_sha256"] != hashlib.sha256(draft_bytes).hexdigest()
            or staged["findings_sha256"] != hashlib.sha256(findings_bytes).hexdigest()
        ):
            raise workspace.WorkspaceError("review drafts changed after staging")
        timing = (
            staged["timing"]
            if staged is not None
            else {
                "started_at": context["started_at"],
                "finished_at": utc_now(),
                "seconds": round(time.monotonic() - context["started_monotonic"], 6),
                "waiting_seconds": None,
            }
        )
        if captured_exports is not None and document.get("timing") != timing:
            raise workspace.WorkspaceError("staged findings timing changed")
        document["timing"] = timing
        execution = {
            "reviewer": context["reviewer"],
            "timing": timing,
            "pr_head": state["pr_head"],
            "reviewed_head": state["commit"],
            "review_kind": "commit" if state.get("review_commit") else "pr_head",
        }
        # Repeating a refused completion must not accumulate misleading timing blocks.
        if captured_exports is not None:
            sections = markdown.split(EXECUTION_SECTION)
            if len(sections) != 2 or not sections[1].startswith("```json\n") or not sections[1].endswith("\n```\n"):
                raise workspace.WorkspaceError("staged review execution block is missing or malformed")
            if json.loads(sections[1][8:-5], object_pairs_hook=parent_data.unique_object) != execution:
                raise workspace.WorkspaceError("staged review execution differs from its candidates")
        else:
            markdown = markdown.split(EXECUTION_SECTION, 1)[0].rstrip() + EXECUTION_SECTION
            markdown += (
                "```json\n"
                + json.dumps(execution, ensure_ascii=False, indent=2)
                + "\n```\n"
            )
        review_findings = workspace.load_review_findings()
        try:
            validated = review_findings.validate_document(document)
            review_findings.check_pair(markdown, validated)
        except review_findings.FindingsError as error:
            raise workspace.WorkspaceError("findings draft is invalid: " + "; ".join(error.problems)) from error
        if validate_only:
            return {"status": "validated"}
        if captured_exports is not None:
            findings.write_bytes(findings_bytes)
            draft.write_bytes(draft_bytes)
        else:
            workspace.write_json(findings, document)
            draft.write_text(markdown, encoding="utf-8")
        if context.get("parent_pr_data") is not None and parent_request is None:
            # Only the authenticated parent can recheck the live HEAD and publish.
            context["staged"] = {
                "timing": timing,
                "draft_sha256": workspace.file_digest(draft),
                "findings_sha256": workspace.file_digest(findings),
            }
            workspace.write_json(Path(args.state), state)
            return {
                **result_fields(state),
                "status": "staged",
                "staged": context["staged"],
                "prepared": context["immutable"],
                "state_file": args.state,
                "reviewer": context["reviewer"],
                "timing": timing,
                "retained_paths": retained_paths(state),
            }
        stage = "save"
        save_started = time.monotonic()
        saved = workspace.save(argparse.Namespace(state=args.state, findings=True))
    except FAILURES as error:
        if validate_only:
            raise
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
        if cleanup_child is not None:
            cleanup_child()
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


def with_text_body(value: Any) -> dict[str, Any] | None:
    """GitHub は空の本文を null で返す。空文字にした object、形が違えば None。"""
    if not isinstance(value, dict):
        return None
    document = cast(dict[str, Any], value)
    if "body" not in document:
        return None
    if document["body"] is None:
        document["body"] = ""
    return document if isinstance(document["body"], str) else None


def referenced_issue(repository: str, number: int) -> dict[str, Any]:
    """PR 本文が参照する Issue。失敗の理由には gh の出力を写さない（秘密値が混ざりうる）。"""
    try:
        workspace._target_call("validate_repository", repository)
        text = command(
            [
                "gh",
                "issue",
                "view",
                str(number),
                "--repo",
                repository,
                "--json",
                "body,comments",
            ]
        )
    except FAILURES as error:
        raise workspace.WorkspaceError(
            "Issue is not readable with gh issue view"
        ) from error
    try:
        issue = with_text_body(json.loads(text))
    except ValueError as error:
        raise workspace.WorkspaceError("Issue response is not JSON") from error
    if issue is None or not isinstance(issue.get("comments"), list):
        raise workspace.WorkspaceError("Issue requirements metadata is incomplete")
    return issue


def parent_requirements(pr: str, repository: str, number: int) -> dict[str, Any]:
    """対象 PR の要件は必須。参照 Issue を読めなければ理由付きの未取得として渡し、レビューは止めない。"""
    document = with_text_body(
        json.loads(
            command(
                [
                    "gh",
                    "pr",
                    "view",
                    pr,
                    "--repo",
                    repository,
                    "--json",
                    "body,closingIssuesReferences",
                ]
            )
        )
    )
    if document is None or not isinstance(
        document.get("closingIssuesReferences"), list
    ):
        raise workspace.WorkspaceError("PR requirements metadata is incomplete")
    references: set[tuple[str, int]] = {
        (repository, int(n))
        for n in re.findall(r"(?<![\w/])#([1-9][0-9]*)", document["body"])
    }
    for entry in document["closingIssuesReferences"]:
        url = (
            cast(dict[str, Any], entry).get("url") if isinstance(entry, dict) else None
        )
        match = re.fullmatch(
            r"https://github.com/([^/]+/[^/]+)/issues/([1-9][0-9]*)",
            url if isinstance(url, str) else "",
        )
        if match is None:
            raise workspace.WorkspaceError("closing Issue URL is invalid")
        references.add((match[1], int(match[2])))
    for match in re.finditer(
        r"https://github.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)/issues/([1-9][0-9]*)",
        document["body"],
    ):
        references.add((match[1], int(match[2])))
    issues: list[dict[str, Any]] = []
    unavailable: list[dict[str, Any]] = []
    for repo, issue_number in sorted(references - {(repository, number)}):
        try:
            issues.append(
                {
                    "repository": repo,
                    "number": issue_number,
                    **referenced_issue(repo, issue_number),
                }
            )
        except workspace.WorkspaceError as error:
            unavailable.append(
                {"repository": repo, "number": issue_number, "reason": str(error)}
            )
    return {"pr": document, "issues": issues, "unavailable": unavailable}


def prepare_parent(args: argparse.Namespace) -> dict[str, str]:
    """Shared parent preparation for ordinary runner calls and the review loop."""
    if args.records_comments:
        comments = read_json(Path(args.records_comments))
    else:
        target = workspace._target_call(
            "resolve",
            args.pr,
            parent_root=workspace._target_call("default_parent_root"),
            code_root=Path(args.source_root) if args.source_root else None,
        )
        comments = json.loads(
            command(
                [
                    "gh",
                    "api",
                    "--paginate",
                    "--slurp",
                    f"repos/{target['repository']}/issues/{target['number']}/comments",
                ]
            )
        )
    records.comments_from_api(comments)
    requirements = getattr(args, "requirements", None)
    if requirements is None:
        parsed = workspace._target_call("parse_pull_request_argument", args.pr)
        repository = parsed.repository or workspace._target_call(
            "parent_repository", workspace._target_call("default_parent_root")
        )
        requirements = parent_requirements(args.pr, repository, parsed.number)
    return parent_data.prepare(workspace, args, comments, requirements)


def finalize_parent_batch(batch: BatchResult) -> None:
    """Revalidate stopped staged attempts; never trust payload paths by themselves."""
    for result in batch.results:
        if not result.attempts:
            continue
        attempt = result.attempts[-1]
        payload = attempt.payload
        if not isinstance(payload, dict) or payload.get("status") != "staged":
            continue
        promotion_session: Path | None = None
        try:
            if (
                result.state != "success"
                or attempt.state != "success"
                or attempt.exit_code != 0
                or not attempt.stop_confirmed
                or attempt.sensitive_paths
            ):
                raise workspace.WorkspaceError(
                    "staged reviewer did not stop successfully with sensitive cleanup"
                )
            if attempt.request_path is None or attempt.work_dir is None:
                raise workspace.WorkspaceError("staged reviewer has no actual Request")
            request_raw = parent_data.regular_bytes(attempt.request_path)
            request = Request.model_validate_json(request_raw)
            from tools.agent_runner.dsh_review_evidence import promotion_refusal
            refusal = promotion_refusal(attempt.request_path.parent)
            if refusal is not None:
                raise workspace.WorkspaceError(refusal)
            binding = {key: str(getattr(request, key)) for key in BINDING_KEYS}
            if (
                (
                    request.run_id,
                    request.request_id,
                    request.agent_id,
                    request.role,
                    request.work_dir,
                )
                != (
                    batch.run_id,
                    result.request_id,
                    result.actual_agent,
                    result.role,
                    attempt.work_dir,
                )
                or attempt.agent_id != request.agent_id
                or any(payload.get(k) != v for k, v in binding.items())
            ):
                raise workspace.WorkspaceError(
                    "staged result does not match actual Request"
                )
            descriptor = parent_data.descriptor_from_prompt(request.prompt)
            state_path = Path(str(payload["state_file"]))
            snapshot = parent_data.load(
                workspace,
                descriptor,
                f"https://github.com/{payload['repository']}/pull/{payload['pr_number']}",
            )
            suffix = hashlib.sha256(request_raw).hexdigest()[:8]
            scratch = review_scratch(attempt.request_path.parent)
            session = scratch / f"pr-review-{snapshot['target']['number']}-{suffix}"
            if state_path != session / "session.json":
                raise workspace.WorkspaceError(
                    "staged session does not match this Request's fixed scratch path"
                )
            state = parent_data.object_value(
                json.loads(parent_data.regular_bytes(state_path, limit=1024 * 1024), object_pairs_hook=parent_data.unique_object),
                "staged session",
            )
            target = snapshot["target"]
            _parent = Path(target["parent_root"])
            identity = attempt.identity
            if identity is None or not identity.model or not identity.provider:
                raise workspace.WorkspaceError("staged reviewer has no observed Identity")
            model = workspace.validate_model_name(f"{identity.provider}/{identity.model}")
            if any(state.get(key) != value for key, value in {
                "parent_root": target["parent_root"],
                "target_root": str(session / "repo"),
                "target_kind": "bundle",
                "worktree": str(session / "worktree"),
                "backup_dir": str(session / "review-backup"),
                "pr_repo": target["repository"],
                "pr_number": target["number"],
                "pr_head": target["head_sha"],
                "review_commit": snapshot["review_commit"],
                "commit": snapshot["review_commit"] or target["head_sha"],
                "head_branch": target["head_ref"],
                "model_name": model,
                "model_source": workspace.MODEL_SOURCE_EXPLICIT,
                "version": workspace.STATE_VERSION_TARGET,
            }.items()):
                raise workspace.WorkspaceError("staged session target or paths changed")
            for owned in (session, session / "repo", session / "worktree", session / "review-backup"):
                if owned.resolve(strict=True) != owned or owned.stat().st_uid != os.getuid():
                    raise workspace.WorkspaceError("staged session paths must not contain symlinks")
            context = parent_data.object_value(state.get("run_context"), "staged run context")
            for key in ("binding", "reviewer", "skill", "immutable", "staged", "parent_pr_data"):
                parent_data.object_value(context.get(key), f"staged run context.{key}")
            parent_data.object_value(context["staged"].get("timing"), "staged timing")
            observed_now = time.monotonic()
            for key in ("started_monotonic", "prepared_monotonic"):
                value = context.get(key)
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= observed_now:
                    raise workspace.WorkspaceError(f"staged {key} must be finite non-negative seconds")
            if context["started_monotonic"] > context["prepared_monotonic"]:
                raise workspace.WorkspaceError("staged monotonic timing is inconsistent")
            expected_reviewer = {
                "model": identity.model, "runtime": "dsh",
                "provenance": {
                    **binding, "provider": identity.provider,
                    "effort": identity.effort or "unknown",
                    "session_id": identity.session_id or "unknown",
                    "cli_version": "unknown", "skills": [context.get("skill")],
                },
                "review_file": f"{workspace.artifact_model(model, snapshot['review_commit'])}.md",
            }
            if (
                context.get("binding") != binding
                or context.get("parent_pr_data") != descriptor
                or payload.get("reviewer") != context.get("reviewer")
                or payload.get("staged") != context.get("staged")
                or payload.get("prepared") != context.get("immutable")
                or context.get("request_path") != str(attempt.request_path)
                or context.get("request_sha256") != hashlib.sha256(request_raw).hexdigest()
                or context.get("local_record") != str(scratch / "run.json")
                or context.get("reviewer") != expected_reviewer
            ):
                raise workspace.WorkspaceError(
                    "staged session does not match its prepared context"
                )
            if any(
                payload.get(key) != value
                for key, value in {
                    "repository": state["pr_repo"],
                    "pr_number": state["pr_number"],
                    "pr_head": state["pr_head"],
                    "reviewed_head": state["commit"],
                }.items()
            ):
                raise workspace.WorkspaceError("staged result target changed")
            if context["reviewer"]["runtime"] != "dsh":
                raise workspace.WorkspaceError(
                    "parent staging is only supported for DSH"
                )
            expected_immutable = {
                "schema": "review-findings/v2", "kind": "candidates", "source": "reviewer",
                "pr": {"repository": target["repository"], "number": target["number"]},
                "reviewed_head": state["commit"], "base": snapshot["base"],
                "reviewer": context["reviewer"], "skill": context["skill"],
            }
            if context.get("immutable") != expected_immutable:
                raise workspace.WorkspaceError("staged immutable target differs from parent snapshot")
            outbox = review_exports(attempt.request_path.parent)
            captured = (
                parent_data.regular_bytes(outbox / "review.md", limit=16 * 1024 * 1024),
                parent_data.regular_bytes(outbox / "findings.json", limit=16 * 1024 * 1024),
            )
            staged = context.get("staged", {})
            if (staged.get("draft_sha256"), staged.get("findings_sha256")) != tuple(hashlib.sha256(raw).hexdigest() for raw in captured):
                raise workspace.WorkspaceError("review drafts changed after staging")
            complete(
                argparse.Namespace(state=str(state_path)), parent_request=request,
                parent_identity=identity, captured_exports=captured, validate_only=True,
                prepared_state=(_parent, state),
            )
            if workspace.current_pr_head(state["pr_repo"], state["pr_number"]) != state["pr_head"]:
                raise workspace.WorkspaceError("PR head changed before parent promotion")
            # Import the child journal only after its Request, Identity and artifacts match.
            local_document = record.findings.validate_document(json.loads(
                parent_data.regular_bytes(scratch / "run.json", limit=1024 * 1024),
                object_pairs_hook=parent_data.unique_object,
            ))
            local_inputs = parent_data.object_value(local_document.get("inputs"), "local run inputs")
            local_request = parent_data.object_value(local_inputs.get("request"), "local run inputs.request")
            local_timing = parent_data.object_value(local_document.get("timing"), "local run timing")
            if (
                local_document.get("reviewer") != {key: context["reviewer"][key] for key in ("model", "runtime", "provenance")}
                or local_document.get("pr") != expected_immutable["pr"]
                or local_document.get("pr_head") != state["pr_head"]
                or local_document.get("reviewed_head") != state["commit"]
                or local_document.get("status") != "started"
                or local_document.get("outputs") is not None
                or local_document.get("base") != snapshot["base"]
                or local_timing.get("started_at") != context["started_at"]
                or local_request.get("sha256") != hashlib.sha256(request_raw).hexdigest()
            ):
                raise workspace.WorkspaceError("local run record differs from the staged session")
            relative = record.record_relative(target, context["started_at"], model, suffix)
            official = record.safe_record_path(_parent, relative, state["pr_repo"])
            # Never run Git against a child-controlled repository in the authenticated
            # parent. Rebuild the save/cleanup session from the trusted parent bundle.
            promotion = attempt.request_path.parent / "review-promotion"
            promotion.mkdir(mode=0o700, exist_ok=True)
            if promotion.resolve(strict=True) != promotion or promotion.stat().st_uid != os.getuid():
                raise workspace.WorkspaceError("parent promotion root is not an owned canonical directory")
            trusted_name, _suffix = record.new_session_name(state["pr_number"])
            promotion_session = promotion / trusted_name
            trusted = workspace.create(argparse.Namespace(
                target=json.dumps(target), model_name=None,
                authenticated_model=f"{identity.provider}/{identity.model}",
                review_commit=snapshot["review_commit"], source_root=None,
                private_clone=True, parent_input=snapshot,
                temp_root=str(promotion), session_dir=str(promotion_session),
            ))
            trusted_path = Path(trusted["state_file"])
            _, trusted_state = workspace.load_state(str(trusted_path))
            for key in ("destination_fingerprint", "findings_fingerprint"):
                if trusted_state[key] != state[key]:
                    raise workspace.WorkspaceError("review destination changed before parent promotion")
            record.create(_parent, official, local_document)
            context["run_record"] = relative
            context["local_record"] = None
            trusted_state["run_context"] = context
            workspace.write_json(trusted_path, trusted_state)
            attempt.payload = complete(
                argparse.Namespace(state=str(trusted_path)),
                parent_request=request,
                parent_identity=attempt.identity,
                captured_exports=captured,
                cleanup_child=lambda: shutil.rmtree(session),
            )
            if attempt.payload.get("status") != "success":
                attempt.payload["child_session_dir"] = str(session)
        except FAILURES as error:
            attempt.payload = {
                **payload,
                "status": "failed",
                "reason": str(error),
                "cleanup": "not_attempted",
            }
            if promotion_session is not None and promotion_session.exists():
                attempt.payload["promotion_session_dir"] = str(promotion_session)


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)
    parent = commands.add_parser(
        "prepare-parent", help="認証済み親で固定PRデータを取得する"
    )
    parent.add_argument("--pr", required=True)
    parent.add_argument("--output-dir", required=True)
    parent.add_argument("--source-root")
    parent.add_argument("--review-commit")
    parent.add_argument("--records-comments")
    parent.set_defaults(handler=prepare_parent)
    finalize = commands.add_parser(
        "finalize-parent", help="停止済みDSHレビューを親で保存する"
    )
    finalize.add_argument("--result", required=True, type=Path)
    start = commands.add_parser("prepare")
    start.add_argument("--pr", required=True)
    start.add_argument(
        "--runtime",
        required=True,
        choices=("claude-code", "devin", "pi", "dsh", "codex", "cursor"),
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
    if args.command == "finalize-parent":
        batch = BatchResult.model_validate_json(args.result.read_text(encoding="utf-8"))
        finalize_parent_batch(batch)
        workspace.write_json(args.result, batch.model_dump(mode="json"))
        # A refused save is a failed review payload, not a failed after_run hook.
        print(json.dumps({"status": "success", "result_file": str(args.result)}))
        return 0
    if args.command == "prepare-parent":
        try:
            print(json.dumps(prepare_parent(args), ensure_ascii=False))
            return 0
        except FAILURES as error:
            print(
                json.dumps(
                    {"status": "failed", "reason": str(error)}, ensure_ascii=False
                )
            )
            return 1
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
            result = {**result_fields(state), "status": "failed", "reason": args.reason}
            if args.request:
                result.update(request_binding(args.request))
            if parent is not None and state is not None:
                result.update(fail_review(parent, state, args.reason))
        else:
            result = args.handler(args)
    except FAILURES as error:
        result = {**result_fields(state), "status": "failed", "reason": str(error)}
        if getattr(args, "request", None):
            try:
                request = None
                if getattr(args, "runtime", None) == "dsh":
                    _path, _raw, request = read_dsh_request(args.request)
                result.update(request_binding(args.request, request=request))
            except OSError, ValueError, RuntimeError:
                pass
        if getattr(args, "state", None):
            result["state_file"] = args.state
        if parent is not None and state is not None:
            result.update(record_fields(*locate_record(parent, state)))
    if result["status"] == "failed" and state is not None:
        result["retained_paths"] = retained_paths(state)
    result.setdefault("run_record", None)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result["status"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
