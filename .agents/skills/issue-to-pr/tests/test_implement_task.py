"""Exercise implement_task.py: configuration checks on temporary TOML files and the request/result models."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from tools.test_support.texts import FINDING_CONTENT

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "implement_task.py"
REAL_TEMPLATE = Path(__file__).resolve().parents[4] / ".devcontainer" / "agent-runner.toml"

AGENTS = """
schema_version = 1

[agents.claude-opus]
runtime = "claude-code"
command = ["fake-claude"]
model = "claude-model"

[agents.codex]
runtime = "codex"
command = ["fake-codex"]
model = "codex-model"

[agents.pi-deepseek]
runtime = "pi"
command = ["fake-pi"]
model = "pi-model"
"""

IMPLEMENT_ROLE = """
[roles.implement]
writes = true
deadline_seconds = 60
result_shape = "json"
"""


def template(tmp_path: Path, assignment: str, *, role: str = IMPLEMENT_ROLE) -> Path:
    path = tmp_path / "agent-runner.toml"
    path.write_text(AGENTS + role + assignment, encoding="utf-8")
    return path


def check(tmp_path: Path, template_path: Path, *args: str, personal: Path | None = None) -> tuple[int, Any]:
    """helper を実際に起動する。個人設定は一時パスに向け、利用者の設定を読まない。"""
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "check", "--template", str(template_path), *args],
        capture_output=True,
        text=True,
        env={**os.environ, "AGENT_RUNNER_CONFIG": str(personal or tmp_path / "no-personal.toml")},
    )
    return result.returncode, json.loads(result.stdout) if result.stdout else result.stderr


SELF = '\n[workflows.issue.assignments.implement]\nagents = ["self"]\n'


def test_check_implement_replaces_primary(tmp_path: Path) -> None:
    path = template(
        tmp_path, '\n[workflows.issue.assignments.implement]\nagents = ["codex"]\nfallback = ["pi-deepseek"]\n'
    )

    code, payload = check(tmp_path, path, "--implement", "claude-opus")
    assert code == 0, payload
    assert payload["assignment"]["agents"] == ["claude-opus"]
    assert payload["self"] is False


@pytest.mark.parametrize(
    ("assignment", "role", "personal", "args"),
    [
        pytest.param(
            SELF,
            IMPLEMENT_ROLE,
            '[workflows.issue.assignments.implement]\nagents = ["codex", "claude-opus"]\n',
            [],
            id="two-primaries",
        ),
    ],
)
def test_check_rejects_invalid_assignment(
    tmp_path: Path, assignment: str, role: str, personal: str | None, args: list[str]
) -> None:
    personal_path = None
    if personal is not None:
        personal_path = tmp_path / "personal.toml"
        personal_path.write_text(personal, encoding="utf-8")

    code, payload = check(tmp_path, template(tmp_path, assignment, role=role), *args, personal=personal_path)

    assert code == 2
    assert payload["status"] == "error"
    assert payload["reason"]


def test_check_reads_the_real_template(tmp_path: Path) -> None:
    """雛形の既定が self であることで、--implement も個人設定の担当も無い run は runner の担当を起動しない。

    issue-to-pr の --implement の無い run を今までと同じにする（#157 の受け入れ条件）。雛形の既定を
    変えるときは、このテストと受け入れ条件を一緒に見直す。
    """
    code, payload = check(tmp_path, REAL_TEMPLATE)

    assert code == 0, payload
    assert payload["self"] is True


# --- 依頼・結果の JSON の形 -----------------------------------------------------------------------------------------

SPEC = importlib.util.spec_from_file_location("issue_implement_task", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
mod: Any = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = mod
SPEC.loader.exec_module(mod)

SHA = "0123456789abcdef0123456789abcdef01234567"


def request(**overrides: object) -> dict[str, object]:
    return {
        "repository": "/abs/feature",
        "revision": SHA,
        "task": "Task 2: 取り込みの前の確認",
        "allowed_files": ["src/a.py", "tests/"],
        "commit_message": "feat: 実装する\n\nCo-Authored-By: Fixture <fixture@example.invalid>",
        "prompt": FINDING_CONTENT,
        **overrides,
    }


@pytest.mark.parametrize(
    "overrides",
    [
        {"allowed_files": ["/abs/a.py"]},
        {"allowed_files": ["../a.py"]},
        {"allowed_files": ["src/a.py\nother.py"]},
    ],
)
def test_task_request_rejects_invalid_fields(overrides: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        mod.TaskRequest.model_validate(request(**overrides))


def test_directory_entry_matches_by_path_segment() -> None:
    assert mod.allowed("tests/a.py", ["tests/"])
    assert mod.allowed("tests/sub/b.py", ["tests/"])
    assert not mod.allowed("tests_other/x", ["tests/"])
    assert not mod.allowed("tests", ["tests/"])
    assert mod.allowed("a.py", ["a.py"])
    assert not mod.allowed("a.pyc", ["a.py"])
    assert not mod.allowed("src/a.py/x", ["src/a.py"])


def test_exit_code_for_verdicts() -> None:
    assert [mod.exit_code_for(verdict) for verdict in ("importable", "no_changes")] == [0, 0]
    assert [mod.exit_code_for(verdict) for verdict in ("retry", "rejected", "failed")] == [1, 1, 1]
