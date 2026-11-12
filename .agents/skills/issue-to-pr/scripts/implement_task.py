"""issue-to-pr の Plan の Task を、agent-runner の workflow issue の implement に割り当てた担当に依頼する。

check は設定（雛形 < 個人設定 < --implement）だけを検査し、worktree・runner・GitHub に触れない。
run は Task 1 つを runner で依頼し、停止の確認の後に取り込めるかを git で確かめて判定する（取り込みはしない）。
accept は判定を今の状態でやり直してから --ff-only で取り込み、cleanup は runner の worktree と出力先を片付ける。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import unicodedata
from collections.abc import Callable, Collection, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.agent_runner import (  # noqa: E402
    Config,
    ConfigError,
    RunnerError,
    Workflow,
    load_config,
    resolve_config_path,
    run_workflow,
)
from tools.agent_runner.adapters import Adapter, load_adapter  # noqa: E402
from tools.agent_runner.checkout_policy import require_auditable_workflow  # noqa: E402
from tools.agent_runner.config import validate_config  # noqa: E402
from tools.agent_runner.environ import literal_environ  # noqa: E402
from tools.agent_runner.models import Assignment, Attempt, BatchResult  # noqa: E402
from tools.agent_runner.workspace import CheckoutAuditError  # noqa: E402

DEFAULT_TEMPLATE = ROOT / ".devcontainer/agent-runner.toml"
WORKFLOW = "issue"
ROLE = "implement"
SHA = re.compile(r"[0-9a-f]{40}|[0-9a-f]{64}")
RETRY_STATUSES = frozenset({"BLOCKED", "NEEDS_CONTEXT"})

Status = Literal["DONE", "DONE_WITH_CONCERNS", "BLOCKED", "NEEDS_CONTEXT"]
Verdict = Literal["importable", "no_changes", "retry", "rejected", "failed"]


class TaskInputError(ValueError):
    """implement_task 自身の入力の誤り。文は値・パスを含まない固定の文で、そのまま出す。"""


# --- 設定 ---------------------------------------------------------------------------------------------------------


def project(config: Config, role_name: str = ROLE, *, writes: bool = True) -> Config:
    """workflow issue の選択した role だけを残す。投影の外への依存（同モデルの除外）を黙って捨てない。

    writes はその role に期待する書込権限。read-only のレビュー role には False を渡し、
    設定が書き込みを許していれば runner を起動しない。
    """
    config = validate_config(config, WORKFLOW)
    workflow = config.workflows[WORKFLOW]
    role = config.roles.get(role_name)
    assignment = workflow.assignments.get(role_name)
    if role is None or assignment is None:
        raise ConfigError("invalid_reference")
    if role.writes is not writes or role.result_shape != "json" or len(assignment.agents) != 1:
        raise ConfigError("invalid_config")
    constraints = {name: other for name, other in workflow.exclude_same_model_as.items() if name == role_name}
    if any(other != role_name for other in constraints.values()):
        raise ConfigError("invalid_reference")
    selected = config.model_copy(deep=True)
    selected.workflows = {
        WORKFLOW: Workflow(assignments={role_name: assignment}, exclude_same_model_as=constraints)
    }
    return validate_config(selected, WORKFLOW)


def personal_config(config: Path | None) -> Path | None:
    if config is not None:
        return config
    candidate = resolve_config_path()
    return candidate if candidate.exists() else None


def load(template: Path, config: Path | None, implement: str | None) -> Config:
    """雛形 < 個人設定 < --implement で読み込み、投影する。--implement は agents を置き換え、fallback を保つ。"""
    assignments = {ROLE: [implement]} if implement is not None else None
    return project(load_config(template, personal_config(config), assignments=assignments, workflow=WORKFLOW))


def assignment_of(config: Config) -> Assignment:
    return config.workflows[WORKFLOW].assignments[ROLE]


def check(template: Path, config: Path | None, implement: str | None) -> dict[str, Any]:
    assignment = assignment_of(load(template, config, implement))
    personal = personal_config(config)
    return {
        "status": "ok",
        "assignment": assignment.model_dump(mode="json"),
        "self": assignment.agents == ["self"],
        "template": str(template),
        "config": str(personal) if personal is not None else None,
    }


# --- 依頼と結果の形 -----------------------------------------------------------------------------------------------


def _single_line(value: str) -> bool:
    """runner の write_exceptions と同じ条件: 空でない・前後に空白が無い・1 行・制御文字が無い。"""
    return (
        value != ""
        and value == value.strip()
        and value.splitlines() == [value]
        and not any(unicodedata.category(character) == "Cc" for character in value)
    )


def _nonblank(value: str) -> str:
    if not value.strip() or "\x00" in value:
        raise ValueError("must be nonblank text without NUL")
    return value


def _sha(value: str) -> str:
    if SHA.fullmatch(value) is None:
        raise ValueError("must be a full lowercase commit hash")
    return value


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class TaskRequest(_Strict):
    """司令塔が作る依頼の JSON。prompt は Plan のその Task の全文などを入れた、それだけで作業できる依頼。"""

    repository: str
    revision: str
    task: str
    allowed_files: list[str] = Field(min_length=1)
    commit_message: str
    prompt: str

    @field_validator("repository")
    @classmethod
    def _absolute(cls, value: str) -> str:
        if not Path(value).is_absolute():
            raise ValueError("repository must be absolute")
        return value

    @field_validator("revision")
    @classmethod
    def _revision(cls, value: str) -> str:
        return _sha(value)

    @field_validator("task")
    @classmethod
    def _task(cls, value: str) -> str:
        if not _single_line(value):
            raise ValueError("task must be one trimmed line")
        return value

    @field_validator("allowed_files")
    @classmethod
    def _allowed_files(cls, value: list[str]) -> list[str]:
        for entry in value:
            parts = entry.removesuffix("/").split("/")
            if not _single_line(entry) or entry.startswith("/") or any(part in {"", ".", ".."} for part in parts):
                raise ValueError("allowed_files entries must be normalized relative paths")
        return value

    @field_validator("commit_message", "prompt")
    @classmethod
    def _text(cls, value: str) -> str:
        return _nonblank(value)


class Command(_Strict):
    argv: list[str] = Field(min_length=1)
    exit_code: int


class TaskResult(_Strict):
    """担当が返す JSON（runner の receipt の payload）。"""

    status: Status
    commit: str | None
    changed_files: list[str]
    commands: list[Command]
    concerns: list[str]
    incomplete: list[str]
    retained_paths: list[str]

    @field_validator("commit")
    @classmethod
    def _commit(cls, value: str | None) -> str | None:
        return value if value is None else _sha(value)


def is_task_result(payload: object) -> bool:
    """runner の payload_check。TaskResult に合わない結果は invalid_result になり、fallback の次の候補を試す。"""
    try:
        TaskResult.model_validate(payload)
    except ValidationError:
        return False
    return True


class Assessment(_Strict):
    verdict: Verdict
    reasons: list[str]
    work_dir: str | None = None
    commit: str | None = None
    helper_commit: bool = False
    changed_files: list[str] = Field(default_factory=list[str])
    result: TaskResult | None = None


def allowed(path: str, entries: Sequence[str]) -> bool:
    """完全一致、または / で終わる要素（ディレクトリ）の下。"""
    return any(path == entry or (entry.endswith("/") and path.startswith(entry)) for entry in entries)


def exit_code_for(verdict: str) -> int:
    return 0 if verdict in {"importable", "no_changes"} else 1


RESULT_SHAPE = json.dumps(
    {
        "status": "DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT",
        "commit": "<full SHA of HEAD after your last commit> | null",
        "changed_files": ["<path>"],
        "commands": [{"argv": ["<program>", "<argument>"], "exit_code": 0}],
        "concerns": ["<text>"],
        "incomplete": ["<text>"],
        "retained_paths": ["<absolute path you left behind>"],
    },
    ensure_ascii=False,
)


def compose_prompt(request: TaskRequest) -> str:
    """担当への依頼文。runner はこの前に作業範囲の指示（Work in this worktree only・writes=True）を付ける。"""
    return "\n".join(
        [
            "Implement exactly ONE Task of an implementation plan in this runner worktree. Do not rely on any skill "
            "or memory being available: everything you need is in this request.",
            "",
            "Files you may change (paths relative to the worktree root; an entry ending with '/' is a directory and "
            "everything below it). Do not create, modify, delete or rename anything else:",
            json.dumps(request.allowed_files, ensure_ascii=False),
            "",
            "Commits: you may commit in this worktree (detached HEAD). If you commit, make only linear commits on top "
            "of the current HEAD and never create a merge commit; every commit is checked against the list above, so "
            "do not touch other files even in a commit you later revert. If git refuses to stage or commit (for "
            'example because a sandbox makes .git read-only), leave your changes uncommitted and return "commit": '
            "null; the caller commits them after checking. If you commit, leave nothing uncommitted.",
            "",
            "Never: push, create or edit pull requests or issues, write to GitHub, start another agent (runner or "
            "subagent), or use any other worktree or checkout.",
            "",
            "Run the related tests and static checks the Task names, and report each command's argv and exit code.",
            "",
            "Return exactly one JSON object with exactly these keys:",
            RESULT_SHAPE,
            "status: DONE (finished), DONE_WITH_CONCERNS (finished, but list your doubts in concerns), BLOCKED (you "
            "cannot finish; say why in concerns), NEEDS_CONTEXT (information is missing; say what in incomplete). "
            "changed_files: every path you added, changed or deleted, with both names for a rename, relative to the "
            "worktree root.",
            "",
            f"Task: {request.task}",
            "",
            request.prompt,
        ]
    )


# --- git ----------------------------------------------------------------------------------------------------------


def _git(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    """GIT_* の経路指定を除いた環境で git を呼ぶ（tools.agent_runner.workspace と同じ）。"""
    return subprocess.run(
        ["git", "-C", str(cwd), *args],
        capture_output=True,
        check=check,
        timeout=60,
        env={key: value for key, value in literal_environ().items() if not key.startswith("GIT_")},
    )


def _text(output: bytes) -> str:
    return os.fsdecode(output.rstrip(b"\n"))


def head(cwd: Path) -> str:
    return _text(_git(cwd, "rev-parse", "--verify", "HEAD").stdout)


def status_paths(cwd: Path) -> list[str]:
    """未 commit の変更（untracked を含み、ignored を除く）。リネームは元と先の 2 件に分ける。"""
    output = _git(cwd, "status", "--porcelain=v1", "-z", "--untracked-files=all", "--no-renames").stdout
    return sorted(os.fsdecode(entry[3:]) for entry in output.split(b"\x00") if entry)


def diff_paths(cwd: Path, base: str, commit: str) -> list[str]:
    output = _git(cwd, "diff", "--name-only", "-z", "--no-renames", base, commit, "--").stdout
    return sorted(os.fsdecode(entry) for entry in output.split(b"\x00") if entry)


def range_paths(cwd: Path, base: str, commit: str) -> list[str]:
    """base..commit の各 commit が追加・変更・削除したパスの和集合。後の commit で戻した変更も残る。"""
    output = _git(
        cwd, "log", "--format=", "--no-show-signature", "--name-only", "--no-renames", "-z", f"{base}..{commit}", "--"
    ).stdout
    return sorted({os.fsdecode(entry) for entry in output.split(b"\x00") if entry})


def merge_commits(cwd: Path, base: str, commit: str) -> list[str]:
    return _text(_git(cwd, "rev-list", "--merges", f"{base}..{commit}", "--").stdout).split()


def is_ancestor(cwd: Path, ancestor: str, commit: str) -> bool:
    result = _git(cwd, "merge-base", "--is-ancestor", ancestor, commit, check=False)
    if result.returncode not in {0, 1}:
        raise subprocess.CalledProcessError(result.returncode, "git merge-base")
    return result.returncode == 0


def check_feature(repository: Path, revision: str) -> None:
    """取り込み先の feature worktree: linked worktree の root で、HEAD が revision、未 commit の変更が無い。"""
    try:
        top = Path(_text(_git(repository, "rev-parse", "--show-toplevel").stdout)).resolve()
        git_dir = _text(_git(repository, "rev-parse", "--path-format=absolute", "--git-dir").stdout)
        common = _text(_git(repository, "rev-parse", "--path-format=absolute", "--git-common-dir").stdout)
        current = head(repository)
        dirty = status_paths(repository)
    except subprocess.SubprocessError, OSError:
        raise TaskInputError("repository is not a readable git checkout") from None
    if top != repository.resolve() or Path(git_dir).resolve() == Path(common).resolve():
        raise TaskInputError("repository must be the root of a linked feature worktree")
    if current != revision:
        raise TaskInputError("revision must be the current HEAD of the feature worktree")
    if dirty:
        raise TaskInputError("the feature worktree has uncommitted changes")


# --- 判定 ---------------------------------------------------------------------------------------------------------


def _inspect(request: TaskRequest, result: TaskResult, work: Path) -> Assessment:
    """取り込みの前の確認。runner の worktree を git で読み、報告を信用しない。

    担当の commit は --ff-only で範囲ごと履歴に入るので、最終 tree の差分ではなく範囲のどの commit も照合する。
    merge commit の差分は親の取り方で担当の変更と base 側の変更が混ざるので、直線の範囲だけを受け付ける。
    """
    reasons: list[str] = []
    current = head(work)
    leftovers = status_paths(work)
    changed: list[str] = []
    touched: list[str] = []
    if result.commit is not None:
        if current != result.commit:
            reasons.append(f"commit {result.commit} is not the runner worktree HEAD {current}")
        elif result.commit == request.revision:
            reasons.append("commit equals revision: nothing was committed")
        elif not is_ancestor(work, request.revision, result.commit):
            reasons.append(f"commit does not descend from revision {request.revision}")
        else:
            changed = diff_paths(work, request.revision, result.commit)
            merges = merge_commits(work, request.revision, result.commit)
            if merges:
                reasons.append(f"merge commits between revision and commit (only linear commits): {', '.join(merges)}")
            else:
                touched = range_paths(work, request.revision, result.commit)
        if leftovers:
            reasons.append(f"uncommitted changes remain after the commit: {', '.join(leftovers)}")
    elif current != request.revision:
        reasons.append(f"HEAD moved to {current} but commit is null")
    elif not leftovers:
        return Assessment(verdict="no_changes", reasons=[], work_dir=str(work), result=result)
    else:
        changed = touched = leftovers
        unreported = sorted(set(changed) - set(result.changed_files))
        missing = sorted(set(result.changed_files) - set(changed))
        if unreported or missing:
            reasons.append(
                f"changed_files does not match the uncommitted changes (unreported: {unreported}, missing: {missing})"
            )
    outside = [path for path in touched if not allowed(path, request.allowed_files)]
    if outside:
        reasons.append(f"changes outside allowed_files: {', '.join(outside)}")
    return Assessment(
        verdict="rejected" if reasons else "importable",
        reasons=reasons,
        work_dir=str(work),
        commit=result.commit,
        helper_commit=result.commit is None,
        changed_files=changed,
        result=result,
    )


def assess(request: TaskRequest, batch: BatchResult) -> Assessment:
    """runner の結果と、成功した試行の worktree の今の状態から、取り込めるかを決める。"""
    attempts = [attempt for outcome in batch.results for attempt in outcome.attempts]
    unstopped = [attempt.agent_id for attempt in attempts if not attempt.stop_confirmed]
    if unstopped:
        return Assessment(
            verdict="failed",
            reasons=[f"stop_unconfirmed: attempts of {', '.join(unstopped)}; their areas are retained"],
        )
    sensitive = [attempt.agent_id for attempt in attempts if attempt.sensitive_paths]
    if sensitive:
        return Assessment(
            verdict="failed",
            reasons=[f"sensitive_paths: attempts of {', '.join(sensitive)}; their areas are retained"],
        )
    if len(batch.results) != 1:
        return Assessment(verdict="failed", reasons=["runner returned an unexpected number of results"])
    outcome = batch.results[0]
    if outcome.state != "success" or not outcome.attempts:
        exhausted = "; fallback exhausted" if outcome.fallback_exhausted else ""
        return Assessment(verdict="failed", reasons=[f"runner: {outcome.state}{exhausted}"])
    attempt = outcome.attempts[-1]
    work_dir = str(attempt.work_dir) if attempt.work_dir is not None else None
    # run では runner が is_task_result で検査済み。accept が記録を読み直してやり直すときの防御として残す
    try:
        result = TaskResult.model_validate(attempt.payload)
    except ValidationError as error:
        return Assessment(verdict="rejected", reasons=[f"invalid_result: {_fields(error)}"], work_dir=work_dir)
    if batch.outside_changes:
        return Assessment(
            verdict="rejected",
            reasons=[f"outside_changes: {', '.join(batch.outside_changes)}"],
            work_dir=work_dir,
            result=result,
        )
    if result.status in RETRY_STATUSES:
        return Assessment(verdict="retry", reasons=[f"status: {result.status}"], work_dir=work_dir, result=result)
    if attempt.work_dir is None:
        return Assessment(verdict="rejected", reasons=["the successful attempt has no worktree"], result=result)
    status = classify_attempt_worktree(Path(request.repository), attempt)
    if status.kind != "registered":
        return Assessment(
            verdict="rejected",
            reasons=[f"the runner worktree {status.reason}"],
            work_dir=work_dir,
            result=result,
        )
    try:
        return _inspect(request, result, attempt.work_dir)
    except subprocess.SubprocessError, OSError:
        return Assessment(
            verdict="rejected",
            reasons=["the runner worktree cannot be read with git"],
            work_dir=work_dir,
            result=result,
        )


def summarize(assignment: Assignment, batch: BatchResult, assessment: Assessment) -> dict[str, Any]:
    outcome = batch.results[0] if len(batch.results) == 1 else None
    attempts = outcome.attempts if outcome is not None else []
    return {
        "verdict": assessment.verdict,
        "reasons": assessment.reasons,
        "assignment": assignment.model_dump(mode="json"),
        "requested_agent": outcome.requested_agent if outcome is not None else None,
        "actual_agent": outcome.actual_agent if outcome is not None else None,
        "identity": attempts[-1].identity.model_dump(mode="json") if attempts else None,
        "attempts": [
            {
                "agent_id": attempt.agent_id,
                "state": attempt.state,
                "elapsed_seconds": attempt.elapsed_seconds,
                "stop_confirmed": attempt.stop_confirmed,
                "exit_code": attempt.exit_code,
                "work_dir": str(attempt.work_dir) if attempt.work_dir is not None else None,
            }
            for attempt in attempts
        ],
        "work_dir": assessment.work_dir,
        "commit": assessment.commit,
        "helper_commit": assessment.helper_commit,
        "changed_files": assessment.changed_files,
        "result": assessment.result.model_dump(mode="json") if assessment.result is not None else None,
        "outside_changes": batch.outside_changes,
        # 保護しない checkout の観測は報告だけにする。accept を止めるかは outside_changes だけで決める
        "unprotected_changes": batch.unprotected_changes,
        "elapsed_seconds": batch.elapsed_seconds,
        "artifact_dir": str(batch.artifact_dir),
    }


def run(
    config: Config,
    request: TaskRequest,
    output_dir: Path,
    *,
    adapter_loader: Callable[[str], Adapter] = load_adapter,
) -> dict[str, Any]:
    """Task 1 つを runner で依頼し（concurrency 1）、判定と記録を output_dir/task.json に残す。"""
    selected = project(config)
    assignment = assignment_of(selected)
    if assignment.agents == ["self"]:
        raise TaskInputError("issue.implement is self: the controller implements the Task itself (no runner launch)")
    repository = Path(request.repository)
    check_feature(repository, request.revision)
    # 起動後の classify_attempt_worktree と同じ条件で、担当を起動する前に出力先を拒否する。
    if not _canonical_absolute(output_dir):
        raise TaskInputError("output directory must be a normalized absolute path")
    symlink = _symlink_component(output_dir)
    if symlink is None:
        raise TaskInputError("output directory cannot be inspected")
    if symlink:
        raise TaskInputError("output directory must not contain a symlink")
    if output_dir.exists() or output_dir.is_symlink():
        raise TaskInputError("output directory must be new")
    require_auditable_workflow(selected, WORKFLOW, repository, adapter_loader=adapter_loader)
    batch = run_workflow(
        selected,
        WORKFLOW,
        compose_prompt(request),
        repository,
        revision=request.revision,
        concurrency=1,
        output_dir=output_dir,
        adapter_loader=adapter_loader,
        payload_check=is_task_result,
    )
    assessment = assess(request, batch)
    record = {
        "request": request.model_dump(mode="json"),
        "assignment": assignment.model_dump(mode="json"),
        "batch": batch.model_dump(mode="json"),
        "assessment": assessment.model_dump(mode="json"),
    }
    (batch.artifact_dir / "task.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return summarize(assignment, batch, assessment)


def _fields(error: ValidationError) -> str:
    """検査に失敗した項目の位置だけ（値は出さない）。"""
    locations = {
        ".".join(str(part) for part in detail["loc"]) or "(root)"
        for detail in error.errors(include_url=False, include_input=False)
    }
    return ", ".join(sorted(locations))


def read_request(path: Path) -> TaskRequest:
    try:
        return TaskRequest.model_validate_json(path.read_bytes())
    except ValidationError as error:
        raise TaskInputError(f"invalid request: {_fields(error)}") from None


# --- 取り込みと後片付け -------------------------------------------------------------------------------------------


class AcceptRefused(TaskInputError):
    """取り込みの前の確認に反したので取り込まない（終了コード 1）。feature worktree は動かしていない。"""


def load_record(run_dir: Path) -> tuple[TaskRequest, BatchResult]:
    path = run_dir / "task.json"
    if run_dir.is_symlink() or not run_dir.is_dir() or path.is_symlink() or not path.is_file():
        raise TaskInputError("run directory must be a real directory with task.json written by run")
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
        request = TaskRequest.model_validate_json(json.dumps(record["request"]))
        batch = BatchResult.model_validate_json(json.dumps(record["batch"]))
    except ValueError, KeyError, TypeError:
        raise TaskInputError("task.json is not a record written by run") from None
    return request, batch


def accept(run_dir: Path) -> dict[str, Any]:
    """今の状態で判定をやり直し、importable なら（必要なら helper が commit して）--ff-only で取り込む。"""
    request, batch = load_record(run_dir)
    assessment = assess(request, batch)
    if assessment.verdict != "importable" or assessment.work_dir is None:
        raise AcceptRefused(f"not importable ({assessment.verdict}): {'; '.join(assessment.reasons)}")
    repository = Path(request.repository)
    try:
        check_feature(repository, request.revision)
    except TaskInputError as error:
        raise AcceptRefused(str(error)) from None
    work = Path(assessment.work_dir)
    commit = assessment.commit
    try:
        if assessment.helper_commit:
            _git(work, "add", "-A")
            staged = _git(work, "diff", "--cached", "--name-only", "-z", "--no-renames").stdout
            if sorted(os.fsdecode(entry) for entry in staged.split(b"\x00") if entry) != assessment.changed_files:
                raise AcceptRefused("the staged paths differ from the checked changes")
            # hook は迂回しない。行頭の # を残すため、メッセージは空白の整理だけにする
            _git(work, "commit", "-q", "--cleanup=whitespace", "-m", request.commit_message)
            commit = head(work)
            if diff_paths(work, request.revision, commit) != assessment.changed_files:
                raise AcceptRefused("the helper commit differs from the checked changes")
        assert commit is not None
        _git(repository, "merge", "--ff-only", "-q", commit)
        if head(repository) != commit:
            raise AcceptRefused("the feature worktree HEAD is not the imported commit after the merge")
    except subprocess.CalledProcessError as error:
        raise AcceptRefused(f"git {error.cmd[3] if len(error.cmd) > 3 else ''} failed".strip()) from None
    accepted = {
        "state": "accepted",
        "commit": commit,
        "helper_commit": assessment.helper_commit,
        "changed_files": assessment.changed_files,
    }
    (run_dir / "accept.json").write_text(json.dumps(accepted, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return accepted


def _registered(repository: Path) -> set[str]:
    output = _git(repository, "worktree", "list", "--porcelain", "-z").stdout
    return {
        os.fsdecode(field[len(b"worktree ") :]) for field in output.split(b"\x00") if field.startswith(b"worktree ")
    }


WORKTREE_SYMLINK = "contains a symlink"
WORKTREE_UNREGISTERED = "is not a registered worktree of the repository"
WORKTREE_COMMON_DIR = "uses a different git common directory than the repository"
WORKTREE_UNREADABLE = "cannot be read with git"
WORKTREE_NOT_ABSOLUTE = "is not a normalized absolute path"
WORKTREE_NOT_DIRECTORY = "is not a directory"
WORKTREE_MISSING = "is missing"
WORKTREE_REAPPEARED = "reappeared after an earlier cleanup"
WORKTREE_COLLECTED = "was collected by an earlier cleanup"

WorktreeKind = Literal[
    "registered",
    "prepare-failed",
    "missing",
    "improper",
    "unknown",
    "collected",
    "reappeared",
    "unconfirmed",
]


@dataclass(frozen=True)
class WorktreeStatus:
    """試行の worktree を、監査と回収が同じ事実で分類した結果。"""

    kind: WorktreeKind
    reason: str = ""


def _lexists(path: Path) -> bool | None:
    try:
        os.lstat(path)
    except FileNotFoundError:
        return False
    except (OSError, ValueError):
        return None
    return True


def _symlink_component(path: Path) -> bool | None:
    """パスのどの構成要素（最終要素を含む）が symlink か。参照先はたどらない。"""
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current = current / part
        try:
            info = os.lstat(current)
        except FileNotFoundError:
            return False
        except (OSError, ValueError):
            return None
        if stat.S_ISLNK(info.st_mode):
            return True
    return False


def _canonical_absolute(path: Path) -> bool:
    try:
        text = str(path)
    except (OSError, ValueError):
        return False
    return path.is_absolute() and os.path.normpath(text) == text


def _attempt_record_exists(attempt: Attempt) -> bool | None:
    if attempt.state == "success" or attempt.payload is not None:
        return True
    if attempt.request_path is None:
        return False
    return _lexists(attempt.request_path)


def classify_attempt_worktree(
    repository: Path,
    attempt: Attempt,
    *,
    collected: Collection[str] = (),
) -> WorktreeStatus:
    """停止確認済みの試行の worktree を、監査と回収で共有する状態に分類する。

    準備前に終わった試行（結果も依頼記録も無い）だけを対象外にし、成功した試行を準備前と推測しない。
    symlink を含むパス、登録されていないパス、common-dir が違うパス、読めないパスは実体として扱わない。
    collected は同じレビューの回収記録にあるパスで、不在なら回収済み、再出現なら保持の根拠にする。
    """
    if not attempt.stop_confirmed:
        return WorktreeStatus("unconfirmed", "stop not confirmed")
    if attempt.sensitive_paths:
        return WorktreeStatus("unconfirmed", "sensitive paths may hold secrets")
    work = attempt.work_dir
    if work is None:
        record = _attempt_record_exists(attempt)
        if record is None:
            return WorktreeStatus("unknown", WORKTREE_UNREADABLE)
        if record:
            return WorktreeStatus("missing", WORKTREE_MISSING)
        return WorktreeStatus("prepare-failed", "ended before preparation")
    if not _canonical_absolute(work):
        return WorktreeStatus("improper", WORKTREE_NOT_ABSOLUTE)
    symlink = _symlink_component(work)
    if symlink is None:
        return WorktreeStatus("unknown", WORKTREE_UNREADABLE)
    if symlink:
        return WorktreeStatus("improper", WORKTREE_SYMLINK)
    exists = _lexists(work)
    if exists is None:
        return WorktreeStatus("unknown", WORKTREE_UNREADABLE)
    path = Path(os.path.abspath(work))
    try:
        registered = {Path(entry) for entry in _registered(repository)}
    except (subprocess.SubprocessError, OSError):
        return WorktreeStatus("unknown", WORKTREE_UNREADABLE)
    is_registered = path in registered
    if not exists:
        if str(path) in collected:
            if is_registered:
                return WorktreeStatus("reappeared", WORKTREE_REAPPEARED)
            return WorktreeStatus("collected", WORKTREE_COLLECTED)
        if is_registered:
            return WorktreeStatus("missing", WORKTREE_MISSING)
        record = _attempt_record_exists(attempt)
        if record is None:
            return WorktreeStatus("unknown", WORKTREE_UNREADABLE)
        if not record:
            return WorktreeStatus("prepare-failed", "ended before preparation")
        return WorktreeStatus("missing", WORKTREE_MISSING)
    if str(path) in collected:
        return WorktreeStatus("reappeared", WORKTREE_REAPPEARED)
    if not is_registered:
        return WorktreeStatus("improper", WORKTREE_UNREGISTERED)
    try:
        info = os.lstat(path)
    except (OSError, ValueError):
        return WorktreeStatus("unknown", WORKTREE_UNREADABLE)
    if not stat.S_ISDIR(info.st_mode):
        return WorktreeStatus("improper", WORKTREE_NOT_DIRECTORY)
    try:
        common = Path(_text(_git(repository, "rev-parse", "--path-format=absolute", "--git-common-dir").stdout))
        other = Path(_text(_git(path, "rev-parse", "--path-format=absolute", "--git-common-dir").stdout))
    except (subprocess.SubprocessError, OSError):
        return WorktreeStatus("unknown", WORKTREE_UNREADABLE)
    if os.path.realpath(common) != os.path.realpath(other):
        return WorktreeStatus("improper", WORKTREE_COMMON_DIR)
    try:
        _git(path, "rev-parse", "--verify", "HEAD")
    except (subprocess.SubprocessError, OSError):
        return WorktreeStatus("unknown", WORKTREE_UNREADABLE)
    return WorktreeStatus("registered")


def retained_path(attempt: Attempt, batch: BatchResult, *, parent: bool = False) -> str:
    """保持を報告するパス。worktree が無い試行は依頼記録か runner 出力の場所を返す。"""
    if attempt.work_dir is not None:
        return str(attempt.work_dir.parent if parent else attempt.work_dir)
    if attempt.request_path is not None:
        return str(attempt.request_path.parent)
    return str(batch.artifact_dir)


def remove_attempts(
    repository: Path,
    batch: BatchResult,
    *,
    collected: Collection[str] = (),
    on_removed: Callable[[Path], None] | None = None,
) -> tuple[list[str], list[dict[str, str]]]:
    """停止を確認した試行の worktree の登録を外す（force しない）。消せなかったものは理由付きで返す。

    classify_attempt_worktree と同じ分類を使い、symlink を含むパス、未登録・common-dir 違いのパス、
    読めないパス、予期しない不在は git worktree remove に渡さず保持する。回収記録がある不在は no-op、
    再出現は保持する。on_removed は 1 件の回収が成功するたびに呼び、失敗したらそこで止めて保持する。
    """
    removed: list[str] = []
    retained: list[dict[str, str]] = []
    stopped = False
    for attempt in (attempt for outcome in batch.results for attempt in outcome.attempts):
        if stopped:
            # 記録の失敗で中断した後は削除せず、残りの試行をすべて報告する
            retained.append(
                {
                    "path": retained_path(attempt, batch),
                    "reason": "not processed because an earlier cleanup record could not be written; check it by hand",
                }
            )
            continue
        status = classify_attempt_worktree(repository, attempt, collected=collected)
        if status.kind in {"prepare-failed", "collected"}:
            continue
        if status.kind == "unconfirmed":
            retained.append({"path": retained_path(attempt, batch, parent=True), "reason": status.reason})
            continue
        if status.kind != "registered":
            retained.append({"path": retained_path(attempt, batch), "reason": status.reason})
            continue
        assert attempt.work_dir is not None
        work = Path(os.path.abspath(attempt.work_dir))
        # 分類と削除の間に置き換えられていないことを、副作用の直前にもう一度確かめる
        again = classify_attempt_worktree(repository, attempt, collected=collected)
        if again.kind != "registered":
            retained.append({"path": str(work), "reason": again.reason})
            continue
        if _git(repository, "worktree", "remove", "--", str(work), check=False).returncode != 0:
            retained.append(
                {"path": str(work), "reason": "git worktree remove refused (uncommitted or untracked files)"}
            )
            continue
        removed.append(str(work))
        if on_removed is not None:
            try:
                on_removed(work)
            except Exception as error:
                stage = getattr(error, "cleanup_stage", None)
                detail = (
                    "its cleanup success evidence could not be saved"
                    if stage == "evidence"
                    else "its cleanup receipt could not be written"
                )
                retained.append(
                    {
                        "path": str(work),
                        "reason": f"the worktree was removed but {detail}; check it by hand",
                    }
                )
                stopped = True
    return removed, retained


def cleanup(run_dir: Path) -> dict[str, Any]:
    """停止を確認した試行の worktree の登録を外し、何も残らなければ run_dir を消す。"""
    request, batch = load_record(run_dir)
    removed, retained = remove_attempts(Path(request.repository), batch)
    record_failed = any(
        "cleanup receipt could not be written" in item["reason"]
        or "cleanup success evidence could not be saved" in item["reason"]
        for item in retained
    )
    if record_failed and not any(item["path"] == str(run_dir) for item in retained):
        retained.append(
            {
                "path": str(run_dir),
                "reason": "the run directory was not removed because the cleanup stopped after a record failure; check it by hand",
            }
        )
    removed_run_dir = not retained
    if removed_run_dir:
        shutil.rmtree(run_dir)
    return {"removed_worktrees": removed, "retained": retained, "removed_run_dir": removed_run_dir}


# --- CLI ----------------------------------------------------------------------------------------------------------


def failure_reason(error: Exception) -> str:
    if isinstance(error, TaskInputError):
        return str(error)
    if isinstance(error, ConfigError):
        return f"config: {error.category}"
    if isinstance(error, RunnerError):
        return f"runner: {error.category}"
    return type(error).__name__


def _add_config_arguments(parser: argparse.ArgumentParser) -> None:
    """check と run が同じ定義で受け付ける設定の引数。"""
    parser.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE)
    parser.add_argument(
        "--config", type=Path, help="個人設定（既定は AGENT_RUNNER_CONFIG・XDG_CONFIG_HOME・~/.config）"
    )
    parser.add_argument("--implement", metavar="AGENT", help="その回だけ issue.implement の一次担当を置き換える")


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="implement_task.py", description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)
    _add_config_arguments(commands.add_parser("check", help="設定だけを検査する（worktree・runner に触れない）"))
    launch = commands.add_parser("run", help="Task 1 つを runner で依頼し、取り込めるかを判定する")
    launch.add_argument("--request", type=Path, required=True, help="TaskRequest の JSON")
    launch.add_argument("--output-dir", type=Path, required=True, help="runner の出力先（存在しないパス）")
    _add_config_arguments(launch)
    for name, help_text in (
        ("accept", "判定をやり直し、importable なら --ff-only で feature worktree に取り込む"),
        ("cleanup", "runner の worktree の登録を外し、何も残らなければ出力先を消す"),
    ):
        commands.add_parser(name, help=help_text).add_argument("--run-dir", type=Path, required=True)
    return root


def _error(reason: str, **extra: object) -> int:
    print(json.dumps({"status": "error", "reason": reason, **extra}, ensure_ascii=False))
    return 2


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command in {"accept", "cleanup"}:
            run_dir = args.run_dir.absolute()
            payload = accept(run_dir) if args.command == "accept" else cleanup(run_dir)
            code = 1 if payload.get("retained") else 0
        else:
            template = args.template.resolve()
            config = args.config.resolve() if args.config else None
            if args.command == "check":
                payload = check(template, config, args.implement)
                code = 0
            else:
                request = read_request(args.request)
                payload = run(load(template, config, args.implement), request, args.output_dir.absolute())
                code = exit_code_for(payload["verdict"])
    except AcceptRefused as error:
        print(json.dumps({"status": "refused", "reason": str(error)}, ensure_ascii=False))
        return 1
    except CheckoutAuditError as error:
        return _error(
            "checkout_audit: registered checkouts cannot be audited before launch",
            checkout_audit=[finding.model_dump(mode="json") for finding in error.findings],
        )
    except (ConfigError, TaskInputError, RunnerError, OSError, subprocess.SubprocessError) as error:
        return _error(failure_reason(error))
    print(json.dumps(payload, ensure_ascii=False))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
