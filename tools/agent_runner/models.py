"""Strict configuration and wire models for the noninteractive runner."""

import math
import re
from pathlib import Path
from typing import Annotated, Literal, cast

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

Runtime = Literal["claude-code", "devin", "pi", "codex", "cursor"]
ResultShape = Literal["json", "text"]
State = Literal[
    "success",
    "self",
    "unsupported",
    "launch_failed",
    "awaiting_authentication",
    "awaiting_approval",
    "response_failed",
    "missing_result",
    "invalid_result",
    "timed_out",
    "interrupted",
]
ReceiptStatus = Literal["success", "awaiting_authentication", "awaiting_approval", "response_failed", "interrupted"]
BatchState = Literal["success", "self", "partial_success", "failed"]
Payload = dict[str, object] | str | None


def _identifier(value: object) -> object:
    if isinstance(value, str) and not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", value):
        raise ValueError("invalid identifier")
    return value


def _nonblank(value: object) -> object:
    if isinstance(value, str) and (not value.strip() or "\x00" in value):
        raise ValueError("text must be nonblank and contain no NUL")
    return value


def _argument(value: object) -> object:
    if isinstance(value, str) and "\x00" in value:
        raise ValueError("argument must contain no NUL")
    return value


Identifier = Annotated[str, BeforeValidator(_identifier)]
Nonblank = Annotated[str, BeforeValidator(_nonblank)]
Argument = Annotated[str, BeforeValidator(_argument)]
PositiveSeconds = Annotated[float, Field(gt=0)]
Command = Annotated[list[Argument], Field(min_length=1)]
ElapsedSeconds = Annotated[float, Field(ge=0)]


class StrictModel(BaseModel):
    """Reject extra keys, coercion, and nonfinite numbers at every boundary."""

    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)

    @field_validator("schema_version", mode="before", check_fields=False)
    @classmethod
    def _schema_version(cls, value: object) -> object:
        # Literal[1] alone accepts True because bool is an int subclass.
        if type(value) is not int or value != 1:
            raise ValueError("unsupported schema version")
        return value

    @field_validator("payload", mode="before", check_fields=False)
    @classmethod
    def _payload(cls, value: object) -> object:
        """Accept only JSON values, including within an otherwise arbitrary object map."""
        active: set[int] = set()

        def visit(item: object) -> None:
            if item is None or type(item) in (str, bool, int):
                return
            if type(item) is float and math.isfinite(item):
                return
            item_id = id(item)
            if isinstance(item, (dict, list)):
                if item_id in active:
                    raise ValueError("payload must not contain cycles")
                active.add(item_id)
                if isinstance(item, dict):
                    for key, child in cast(dict[object, object], item).items():
                        if type(key) is not str:
                            raise ValueError("payload keys must be strings")
                        visit(child)
                else:
                    for child in cast(list[object], item):
                        visit(child)
                active.remove(item_id)
                return
            raise ValueError("payload must contain only JSON values")

        visit(value)
        return value


class Agent(StrictModel):
    runtime: Runtime
    command: list[Argument] = Field(min_length=1)
    model: Nonblank
    model_key: Nonblank | None = None
    provider: Nonblank | None = None
    effort: Nonblank | None = None
    approval: Literal["noninteractive"] = "noninteractive"
    skill_sources: list[Nonblank] = Field(default_factory=list)
    args: list[Argument] = Field(default_factory=list)
    env: list[str] = Field(default_factory=list)

    @field_validator("command")
    @classmethod
    def _executable(cls, value: list[str]) -> list[str]:
        _nonblank(value[0])
        return value

    @field_validator("env")
    @classmethod
    def _environment_names(cls, value: list[str]) -> list[str]:
        if any(not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name) for name in value):
            raise ValueError("environment entries must be variable names")
        return value


class Role(StrictModel):
    skills: list[Nonblank] = Field(default_factory=list)
    writes: bool
    deadline_seconds: PositiveSeconds
    result_shape: ResultShape


class Assignment(StrictModel):
    agents: list[Identifier] = Field(min_length=1)
    fallback: list[Identifier] = Field(default_factory=list)

    @field_validator("agents")
    @classmethod
    def _self_alone(cls, value: list[str]) -> list[str]:
        if "self" in value and value != ["self"]:
            raise ValueError("self must be the only assigned agent")
        return value

    @field_validator("fallback")
    @classmethod
    def _no_self_fallback(cls, value: list[str]) -> list[str]:
        if "self" in value:
            raise ValueError("self is not a fallback agent")
        return value


class Workflow(StrictModel):
    assignments: dict[Identifier, Assignment] = Field(min_length=1)
    exclude_same_model_as: dict[Identifier, Identifier] = Field(default_factory=dict)
    # CLI が result.json を保存した後に順に起動する argv（hooks.py）。結果の状態は変えない
    after_run: list[Command] = Field(default_factory=list[list[str]])

    @field_validator("after_run")
    @classmethod
    def _executables(cls, value: list[list[str]]) -> list[list[str]]:
        for command in value:
            _nonblank(command[0])
        return value


class Config(StrictModel):
    schema_version: Literal[1] = 1
    agents: dict[Identifier, Agent] = Field(default_factory=dict)
    roles: dict[Identifier, Role] = Field(default_factory=dict)
    workflows: dict[Identifier, Workflow] = Field(default_factory=dict)

    @field_validator("agents")
    @classmethod
    def _reserve_self(cls, value: dict[str, Agent]) -> dict[str, Agent]:
        if "self" in value:
            raise ValueError("self is reserved")
        return value


class Request(StrictModel):
    schema_version: Literal[1] = 1
    run_id: Identifier
    request_id: Identifier
    agent_id: Identifier
    role: Identifier
    work_dir: Path
    prompt: str
    deadline_seconds: PositiveSeconds
    result_shape: ResultShape


class Receipt(StrictModel):
    schema_version: Literal[1] = 1
    run_id: Identifier
    request_id: Identifier
    agent_id: Identifier
    role: Identifier
    status: ReceiptStatus
    payload: Payload = None


class Identity(StrictModel):
    model: str | None = None
    provider: str | None = None
    effort: str | None = None
    session_id: str | None = None
    cli_version: str | None = None
    skill_versions: dict[str, str] = Field(default_factory=dict)


class Attempt(StrictModel):
    agent_id: Identifier
    state: State
    # What the adapter classified from the output before the adapter's later checks or the runner
    # replaced it; null when nothing was classified. A diagnostic only: never used to decide state.
    reported_state: State | None = None
    identity: Identity = Field(default_factory=Identity)
    exit_code: int | None = None
    elapsed_seconds: ElapsedSeconds
    stop_confirmed: bool
    work_dir: Path | None = None
    stdout_path: Path | None = None
    stderr_path: Path | None = None
    request_path: Path | None = None
    sensitive_paths: list[Path] = Field(default_factory=list[Path])
    payload: Payload = None


class Result(StrictModel):
    request_id: Identifier
    role: Identifier
    requested_agent: Identifier
    actual_agent: Identifier
    state: State
    attempts: list[Attempt]
    fallback_exhausted: bool = False


AuditReason = Literal[
    "checkout_missing",
    "not_directory",
    "git_unavailable",
    "filesystem_unavailable",
    "audit_unavailable",
    "content_changed",
]


class CheckoutAudit(StrictModel):
    """Observations only: fixed reasons, no Git stderr or attribution to a worker.

    ``removed`` is a checkout that was unreadable after the run and is no longer registered.
    ``protected`` marks the requested checkout (every registration when it cannot be
    identified); the main worktree is not protected unless it is the requested one. Records
    saved before this field existed are read as protected, so they are never accepted by mistake.
    """

    path: str
    kind: Literal["unavailable_before", "unavailable_after", "content_changed", "removed"]
    reason: AuditReason
    locked: bool = False
    prunable: bool = False
    protected: bool = True


class BatchResult(StrictModel):
    """``outside_changes`` lists the protected checkout's observations and blocks acceptance.

    ``unprotected_changes`` reports every observation (``content_changed``, ``removed``,
    ``unavailable_*``) of unprotected checkouts, the main worktree included, and does not
    block acceptance. Records saved without it are read as ``[]``.
    """

    schema_version: Literal[1] = 1
    run_id: Identifier
    state: BatchState
    assignments: dict[Identifier, list[Identifier]]
    results: list[Result]
    outside_changes: list[str]
    unprotected_changes: list[str] = Field(default_factory=list[str])
    checkout_audit: list[CheckoutAudit] = Field(default_factory=list[CheckoutAudit])
    elapsed_seconds: ElapsedSeconds
    artifact_dir: Path

    @model_validator(mode="before")
    @classmethod
    def _legacy_unrelated_audit(cls, value: object) -> object:
        """Read results saved before #243, which always wrote ``unrelated_checkout_audit``.

        Only an empty list is dropped, so saved runs can be resumed and their stopped resources
        reclaimed. A recorded observation still fails as an extra field rather than being lost.
        """
        if isinstance(value, dict):
            data = cast(dict[str, object], value)
            legacy = data.get("unrelated_checkout_audit")
            if type(legacy) is list and not legacy:
                return {key: item for key, item in data.items() if key != "unrelated_checkout_audit"}
        return value
