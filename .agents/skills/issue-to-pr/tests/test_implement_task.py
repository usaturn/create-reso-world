"""Exercise implement_task.py: configuration checks on temporary TOML files and the request/result models."""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from tools.agent_runner.models import Attempt, BatchResult, Result
from tools.test_support.texts import FINDING_CONTENT

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "implement_task.py"

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


def test_project_refuses_a_write_enabled_review_role(tmp_path: Path) -> None:
    """S: a review role that can write could modify the work it reviews, so projection must refuse to run it."""
    assignments = (
        '\n[workflows.issue.assignments.implement]\nagents = ["codex"]\n'
        '\n[workflows.issue.assignments.spec-review]\nagents = ["claude-opus"]\n'
    )

    def config_for(name: str, writes: bool) -> Any:
        root = tmp_path / name
        root.mkdir()
        role = (
            IMPLEMENT_ROLE
            + f'\n[roles.spec-review]\nwrites = {str(writes).lower()}\n'
            'deadline_seconds = 60\nresult_shape = "json"\n'
        )
        return mod.load_config(template(root, assignments, role=role), workflow="issue")

    selected = mod.project(config_for("read-only", False), "spec-review", writes=False)
    assert set(selected.workflows["issue"].assignments) == {"spec-review"}
    assert selected.roles["spec-review"].writes is False

    with pytest.raises(mod.ConfigError):
        mod.project(config_for("writable", True), "spec-review", writes=False)


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


# --- 試行の worktree の状態分類と回収 ---------------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def isolated_git_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """一時 Git に外の GIT_* と利用者の設定を届けない。"""
    for name in list(os.environ):
        if name.startswith("GIT_"):
            monkeypatch.delenv(name)
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


class Repo:
    """共有の状態分類を確かめるための、main checkout と登録 worktree。"""

    def __init__(self, tmp_path: Path) -> None:
        self.tmp = tmp_path
        self.main = tmp_path / "repo"
        self.main.mkdir(parents=True)
        git(self.main, "init", "-q", "-b", "main")
        git(self.main, "config", "user.name", "Fixture")
        git(self.main, "config", "user.email", "fixture@example.invalid")
        (self.main / "src.py").write_text("value = 1\n", encoding="utf-8")
        git(self.main, "add", "-A")
        git(self.main, "commit", "-qm", "base")
        self.revision = git(self.main, "rev-parse", "HEAD")

    def worktree(self, name: str) -> Path:
        path = self.tmp / name
        git(self.main, "worktree", "add", "--detach", str(path), self.revision)
        return path

    def registered(self) -> str:
        return git(self.main, "worktree", "list", "--porcelain")


def batch_for(*attempts: Attempt) -> BatchResult:
    return BatchResult(
        run_id="run-1",
        state="success",
        assignments={"implement": ["worker"]},
        results=[
            Result(
                request_id="request-1",
                role="implement",
                requested_agent="worker",
                actual_agent="worker",
                state="success",
                attempts=list(attempts),
            )
        ],
        outside_changes=[],
        elapsed_seconds=0.1,
        artifact_dir=Path("/tmp/artifact"),
    )


def attempt(work_dir: Path | None, **overrides: object) -> Attempt:
    fields: dict[str, object] = {
        "agent_id": "worker",
        "state": "success",
        "elapsed_seconds": 0.1,
        "stop_confirmed": True,
        "work_dir": work_dir,
        "payload": {"status": "DONE"},
    }
    fields.update(overrides)
    return Attempt(**fields)


def test_cleanup_retains_a_worktree_below_a_symlinked_directory(tmp_path: Path) -> None:
    """S: 祖先の symlink をたどると、登録文字列が同じでも参照先の clean checkout を失う。"""
    repo = Repo(tmp_path)
    parent = tmp_path / "parent"
    parent.mkdir()
    work = parent / "reviewer"
    git(repo.main, "worktree", "add", "--detach", str(work), repo.revision)
    target = tmp_path / "target"
    parent.rename(target)
    parent.symlink_to(target, target_is_directory=True)
    assert work.exists()
    assert str(work) in repo.registered()
    target_bytes = (target / "reviewer" / "src.py").read_bytes()
    target_mode = stat.S_IMODE((target / "reviewer" / "src.py").stat().st_mode)
    registered = repo.registered()

    removed, retained = mod.remove_attempts(repo.main, batch_for(attempt(work)))

    assert removed == []
    assert [(item["path"], item["reason"]) for item in retained] == [(str(work), "contains a symlink")]
    assert work.is_dir()
    assert (target / "reviewer").is_dir()
    assert (target / "reviewer" / "src.py").read_bytes() == target_bytes
    assert stat.S_IMODE((target / "reviewer" / "src.py").stat().st_mode) == target_mode
    assert repo.registered() == registered


def test_cleanup_retains_a_clean_checkout_of_another_repository(tmp_path: Path) -> None:
    """S: 未登録の clean checkout を削除すると、レビュー対象でない作業を失う。"""
    repo = Repo(tmp_path)
    foreign = tmp_path / "foreign"
    subprocess.run(["git", "clone", "-q", str(repo.main), str(foreign)], check=True)
    registered = repo.registered()

    removed, retained = mod.remove_attempts(repo.main, batch_for(attempt(foreign)))

    assert removed == []
    assert [(item["path"], item["reason"]) for item in retained] == [
        (str(foreign), "is not a registered worktree of the repository")
    ]
    assert foreign.is_dir()
    assert repo.registered() == registered


def test_cleanup_retains_a_registered_path_replaced_by_another_repository(tmp_path: Path) -> None:
    """S: 同じ path を別 common-dir の checkout に置き換えると、登録文字列だけで実体を信用してしまう。"""
    repo = Repo(tmp_path)
    reviewer = repo.worktree("reviewer")
    shutil.rmtree(reviewer)
    foreign = Repo(tmp_path / "foreign")
    subprocess.run(["git", "clone", "-q", str(foreign.main), str(reviewer)], check=True)
    assert reviewer.is_dir()
    assert str(reviewer) in repo.registered()

    removed, retained = mod.remove_attempts(repo.main, batch_for(attempt(reviewer)))

    assert removed == []
    assert [(item["path"], item["reason"]) for item in retained] == [
        (str(reviewer), "uses a different git common directory than the repository")
    ]
    assert (reviewer / "src.py").is_file()
    assert str(reviewer) in repo.registered()


def test_cleanup_retains_an_unexpectedly_missing_successful_worktree(tmp_path: Path) -> None:
    """S: 成功した試行の worktree が無いのに回収済みと扱うと、監査できない結果を片付けたことにする。"""
    repo = Repo(tmp_path)
    reviewer = repo.worktree("reviewer")
    git(repo.main, "worktree", "remove", "--", str(reviewer))

    removed, retained = mod.remove_attempts(repo.main, batch_for(attempt(reviewer)))

    assert removed == []
    assert [(item["path"], item["reason"]) for item in retained] == [(str(reviewer), "is missing")]


def test_cleanup_ignores_an_attempt_that_ended_before_preparation(tmp_path: Path) -> None:
    """S: 準備前に終わった試行を消失として残すと、正常な fallback の後片付けが終わらない。"""
    repo = Repo(tmp_path)

    removed, retained = mod.remove_attempts(
        repo.main, batch_for(attempt(tmp_path / "never-created", payload=None, state="response_failed"))
    )

    assert removed == []
    assert retained == []


def test_cleanup_removes_a_registered_clean_worktree(tmp_path: Path) -> None:
    """S: 正常な clean worktree まで保持すると、片付けが終わらず runner 出力が残る。"""
    repo = Repo(tmp_path)
    reviewer = repo.worktree("reviewer")

    removed, retained = mod.remove_attempts(repo.main, batch_for(attempt(reviewer)))

    assert removed == [str(reviewer)]
    assert retained == []
    assert not reviewer.exists()
    assert str(reviewer) not in repo.registered()


def test_cleanup_does_not_touch_a_collected_path_but_keeps_it_when_it_reappears(tmp_path: Path) -> None:
    """S: 回収済みの path を再び消すと別の対象を失い、再出現を無視すると新しい作業を消す。"""
    repo = Repo(tmp_path)
    reviewer = repo.worktree("reviewer")
    git(repo.main, "worktree", "remove", "--", str(reviewer))

    removed, retained = mod.remove_attempts(
        repo.main, batch_for(attempt(reviewer)), collected={str(reviewer)}
    )
    assert removed == []
    assert retained == []

    reviewer.mkdir()
    (reviewer / "new.txt").write_text("new\n", encoding="utf-8")

    removed, retained = mod.remove_attempts(
        repo.main, batch_for(attempt(reviewer)), collected={str(reviewer)}
    )

    assert removed == []
    assert [(item["path"], item["reason"]) for item in retained] == [
        (str(reviewer), "reappeared after an earlier cleanup")
    ]
    assert (reviewer / "new.txt").read_text(encoding="utf-8") == "new\n"


@pytest.mark.parametrize(
    "overrides",
    [
        pytest.param({"stop_confirmed": False}, id="unstopped"),
        pytest.param({"sensitive_paths": [Path("/tmp/secret")]}, id="sensitive"),
    ],
)
def test_cleanup_retains_an_absent_area_when_stop_or_secrets_are_unconfirmed(
    tmp_path: Path, overrides: dict[str, object]
) -> None:
    """S: path が無いことを根拠に、停止未確認・機密の領域を安全扱いしない。"""
    repo = Repo(tmp_path)
    missing = tmp_path / "missing"

    removed, retained = mod.remove_attempts(repo.main, batch_for(attempt(missing, **overrides)))

    assert removed == []
    assert len(retained) == 1
    assert retained[0]["path"] == str(missing.parent)
    assert retained[0]["reason"]


def test_cleanup_retains_a_worktree_when_registration_cannot_be_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """S: 登録の読取失敗を不在と扱うと、登録済みの worktree を消すか回収済みと報告する。"""
    repo = Repo(tmp_path)
    reviewer = repo.worktree("reviewer")

    def broken(_: Path) -> set[str]:
        raise OSError("unreadable")

    monkeypatch.setattr(mod, "_registered", broken)

    removed, retained = mod.remove_attempts(repo.main, batch_for(attempt(reviewer)))

    assert removed == []
    assert [(item["path"], item["reason"]) for item in retained] == [
        (str(reviewer), "cannot be read with git")
    ]
    assert reviewer.is_dir()
