"""Immutable values shared by external-tool preflight and operations."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal


class ExternalToolsError(ValueError):
    """A safe reason code and explanation, never raw Git output or credentials."""

    def __init__(self, reason_code: str, explanation: str) -> None:
        self.reason_code = reason_code
        super().__init__(explanation)


@dataclass(frozen=True)
class ToolSpec:
    key: str
    repository: str
    relative_path: str
    base_branch: str
    ci: Literal["required", "disabled"]


@dataclass(frozen=True)
class Registry:
    parent_root: Path
    commit: str
    entries: tuple[ToolSpec, ...]

    def find_repository(self, repository: str) -> ToolSpec | None:
        normalized = repository.lower()
        return next((entry for entry in self.entries if entry.repository == normalized), None)


@dataclass(frozen=True)
class ManagedTarget:
    spec: ToolSpec
    checkout: Path
    common_dir: Path
    base_remote: str
    registry_commit: str


@dataclass(frozen=True)
class CheckResult:
    status: Literal["ready", "missing", "mismatch", "blocked"]
    path: Path
    common_dir: Path | None
    reason_code: str | None
    registry_commit: str


@dataclass(frozen=True)
class CloneResult:
    status: Literal["cloned", "present", "blocked", "failed"]
    path: Path
    staging: Path | None
    reason_code: str | None
    registry_commit: str
