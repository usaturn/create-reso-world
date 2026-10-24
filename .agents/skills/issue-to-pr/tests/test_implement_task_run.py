"""Run implement_task.py's runner path against real Git worktrees with a scripted fake agent."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from tools.agent_runner import Config
from tools.agent_runner.adapters import AdapterContext, AdapterOutcome, Capabilities, LaunchSpec
from tools.agent_runner.models import Agent, Assignment, BatchResult, Identity, Receipt, Role, Workflow
from tools.test_support.texts import FINDING_CONTENT

pytest_plugins = ("tools.test_support.plugin",)
# 偽の担当（PROGRAM）だけを起動するので、runner の担当（AGENT_RUNNER_DEPTH=1）の中でもテストの中だけ depth を外す
pytestmark = pytest.mark.usefixtures("outside_runner")


@pytest.fixture(autouse=True)
def isolated_git_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """fixture の git に、外から渡された GIT_* と利用者の git の設定を届けない。

    linked worktree の `git rebase --exec` は GIT_DIR を export するので、引き継ぐと
    `git -C <一時ディレクトリ>` でも実リポジトリの設定・branch・index が書き換わる（#166）。
    """
    for name in list(os.environ):
        if name.startswith("GIT_"):
            monkeypatch.delenv(name)
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "implement_task.py"
SPEC = importlib.util.spec_from_file_location("issue_implement_task_run", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
mod: Any = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = mod
SPEC.loader.exec_module(mod)

# 偽の担当。runner の worktree でシナリオの手順を実行し、TaskResult を receipt の payload にする。
# commit の "HEAD" は、手順の後の worktree の HEAD に置き換える
PROGRAM = """
import json, pathlib, subprocess, sys
request = json.load(sys.stdin)
scenario = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding='utf-8'))
work = pathlib.Path(request['work_dir'])
def git(*args):
    return subprocess.run(['git', '-C', str(work), *args], check=True, capture_output=True, text=True).stdout.strip()
pathlib.Path(sys.argv[1] + '.prompt').write_text(request['prompt'], encoding='utf-8')
for step in scenario.get('steps', []):
    kind = step['kind']
    if kind == 'write':
        path = work / step['path']
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(step.get('content', 'changed\\n'), encoding='utf-8')
    elif kind == 'delete':
        (work / step['path']).unlink()
    elif kind == 'move':
        (work / step['to']).parent.mkdir(parents=True, exist_ok=True)
        git('mv', step['from'], step['to'])
    elif kind == 'commit':
        git('add', '-A')
        git('-c', 'user.name=Fake', '-c', 'user.email=fake@example.invalid', 'commit', '-qm', 'fake')
    elif kind == 'reset':
        git('reset', '-q', '--hard', step['to'])
    elif kind == 'git':
        git(*step['args'])
    elif kind == 'outside':
        pathlib.Path(step['path']).write_text('outside\\n', encoding='utf-8')
if scenario.get('no_receipt'):
    sys.exit(3)
payload = dict(scenario['payload'])
if payload.get('commit') == 'HEAD':
    payload['commit'] = git('rev-parse', 'HEAD')
receipt = {key: request[key] for key in ('schema_version', 'run_id', 'request_id', 'agent_id', 'role')}
receipt.update(status='success', payload=payload)
pathlib.Path(sys.argv[2]).write_text(json.dumps(receipt), encoding='utf-8')
"""


class FakeAdapter:
    capabilities = Capabilities()

    def __call__(self, runtime: str) -> FakeAdapter:
        return self

    def prepare(self, context: AdapterContext) -> LaunchSpec:
        return LaunchSpec(
            argv=(*context.agent.command, str(context.receipt_path)),
            stdin=context.request.model_dump_json().encode(),
        )

    def collect(self, context: AdapterContext, stdout_path: Path, stderr_path: Path) -> AdapterOutcome:
        if not context.receipt_path.exists():
            return AdapterOutcome(None, Identity(), "response_failed")
        return AdapterOutcome(
            Receipt.model_validate_json(context.receipt_path.read_bytes()),
            Identity(model=context.agent.model, session_id=f"session-{context.agent.model}"),
        )


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


class Fixture:
    def __init__(self, tmp_path: Path) -> None:
        self.tmp = tmp_path
        self.main = tmp_path / "repo"
        self.main.mkdir()
        git(self.main, "init", "-q", "-b", "main")
        git(self.main, "config", "user.name", "Fixture")
        git(self.main, "config", "user.email", "fixture@example.invalid")
        for name, content in {
            ".gitignore": "ignored/\n",
            "src/a.py": "a = 1\n",
            "src/b.py": "b = 1\n",
            "docs/x.md": "x\n",
        }.items():
            path = self.main / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        git(self.main, "add", "-A")
        git(self.main, "commit", "-qm", "base")
        self.feature = tmp_path / "feature"
        git(self.main, "worktree", "add", "-q", "-b", "feature", str(self.feature))
        self.revision = git(self.feature, "rev-parse", "HEAD")
        self.output = tmp_path / "output"

    def scenario(self, name: str, payload: dict[str, object] | None = None, **fields: object) -> Path:
        path = self.tmp / f"{name}.json"
        path.write_text(json.dumps({"payload": payload, **fields}), encoding="utf-8")
        return path

    def config(self, *agents: tuple[str, Path], fallback: int = 0) -> Config:
        """agents の先頭が一次担当、後ろの fallback 個が代わりの候補。"""
        names = [name for name, _ in agents]
        return Config(
            agents={
                name: Agent(runtime="pi", command=[sys.executable, "-c", PROGRAM, str(path)], model=name, env=["PATH"])
                for name, path in agents
            },
            roles={"implement": Role(writes=True, deadline_seconds=60.0, result_shape="json")},
            workflows={
                "issue": Workflow(
                    assignments={"implement": Assignment(agents=[names[0]], fallback=names[1 : 1 + fallback])}
                )
            },
        )

    def request(self, **overrides: object) -> Any:
        return mod.TaskRequest.model_validate(
            {
                "repository": str(self.feature),
                "revision": self.revision,
                "task": "Task 1: src を直す",
                "allowed_files": ["src/a.py", "src/new/", "文書/"],
                "commit_message": "feat: src を直す\n\nCo-Authored-By: Fixture <fixture@example.invalid>",
                "prompt": "src/a.py を直す。\n関連テスト: pytest\n",
                **overrides,
            }
        )

    def run(self, config: Config, request: Any = None) -> dict[str, Any]:
        return mod.run(config, request or self.request(), self.output, adapter_loader=FakeAdapter())


def done(commit: str | None = "HEAD", files: list[str] | None = None, status: str = "DONE") -> dict[str, object]:
    return {
        "status": status,
        "commit": commit,
        "changed_files": files if files is not None else ["src/a.py"],
        "commands": [{"argv": ["pytest", "-q"], "exit_code": 0}],
        "concerns": [],
        "incomplete": [],
        "retained_paths": [],
    }


WRITE_A = {"kind": "write", "path": "src/a.py", "content": "a = 2\n"}
COMMIT = {"kind": "commit"}


@pytest.fixture
def fx(tmp_path: Path) -> Fixture:
    return Fixture(tmp_path)


@pytest.mark.parametrize(
    ("steps", "reported"),
    [
        pytest.param([WRITE_A, {"kind": "write", "path": "src/new/c.py"}], ["src/a.py"], id="unreported-change"),
    ],
)
def test_uncommitted_report_mismatch_is_rejected(fx: Fixture, steps: list[object], reported: list[str]) -> None:
    agent = fx.scenario("a", done(None, reported), steps=steps)

    summary = fx.run(fx.config(("a", agent)))

    assert summary["verdict"] == "rejected"
    assert any("changed_files" in reason for reason in summary["reasons"])


def test_commit_with_leftover_changes_is_rejected(fx: Fixture) -> None:
    agent = fx.scenario("a", done(), steps=[WRITE_A, COMMIT, {"kind": "write", "path": "src/new/left.py"}])

    summary = fx.run(fx.config(("a", agent)))

    assert summary["verdict"] == "rejected"
    assert any("src/new/left.py" in reason for reason in summary["reasons"])


def test_change_outside_allowed_files_is_rejected(fx: Fixture) -> None:
    agent = fx.scenario(
        "a", done(files=["src/a.py", "docs/x.md"]), steps=[WRITE_A, {"kind": "write", "path": "docs/x.md"}, COMMIT]
    )

    summary = fx.run(fx.config(("a", agent)))

    assert summary["verdict"] == "rejected"
    assert any("docs/x.md" in reason for reason in summary["reasons"])


# 担当ファイルの外を途中の commit で変え、次の commit で戻す。最終 tree には残らないが、--ff-only で履歴に残る
REVERTED_OUTSIDE = {
    "new-file": [
        {"kind": "write", "path": "docs/secret.txt", "content": "SECRET-VALUE\n"},
        COMMIT,
        {"kind": "delete", "path": "docs/secret.txt"},
        WRITE_A,
        COMMIT,
    ],
}
REVERTED_PATHS = {"new-file": "docs/secret.txt"}


@pytest.mark.parametrize("case", sorted(REVERTED_OUTSIDE))
def test_intermediate_commit_outside_allowed_files_is_rejected(fx: Fixture, case: str) -> None:
    agent = fx.scenario("a", done(), steps=REVERTED_OUTSIDE[case])

    summary = fx.run(fx.config(("a", agent)))

    assert summary["verdict"] == "rejected"
    assert any(REVERTED_PATHS[case] in reason for reason in summary["reasons"]), summary["reasons"]
    # 要約の changed_files は最終 tree の差分のまま
    assert summary["changed_files"] == ["src/a.py"]


def test_merge_commit_in_range_is_rejected(fx: Fixture) -> None:
    # revision の子の commit を feature で作ってから戻し、担当にその commit を merge させる（どちらも担当ファイルの中）
    (fx.feature / "src/new").mkdir(parents=True)
    (fx.feature / "src/new/side.py").write_text("side\n", encoding="utf-8")
    git(fx.feature, "add", "-A")
    git(fx.feature, "commit", "-qm", "side")
    side = git(fx.feature, "rev-parse", "HEAD")
    git(fx.feature, "reset", "-q", "--hard", fx.revision)
    identity = ["-c", "user.name=Fake", "-c", "user.email=fake@example.invalid"]
    merge = {"kind": "git", "args": [*identity, "merge", "-q", "--no-ff", "--no-edit", side]}
    agent = fx.scenario("a", done(files=["src/a.py", "src/new/side.py"]), steps=[WRITE_A, COMMIT, merge])

    summary = fx.run(fx.config(("a", agent)))

    assert summary["verdict"] == "rejected"
    head = git(Path(summary["work_dir"]), "rev-parse", "HEAD")
    assert git(Path(summary["work_dir"]), "rev-list", "--parents", "-n", "1", head).count(" ") == 2
    assert any("merge" in reason and head in reason for reason in summary["reasons"]), summary["reasons"]


def test_commit_not_descending_from_revision_is_rejected(fx: Fixture) -> None:
    # 元の履歴から外れた commit（revision の親を基にした commit）
    git(fx.main, "commit", "-q", "--allow-empty", "-m", "second")
    git(fx.feature, "merge", "-q", "--ff-only", "main")
    parent = fx.revision
    fx.revision = git(fx.feature, "rev-parse", "HEAD")
    agent = fx.scenario("a", done(), steps=[{"kind": "reset", "to": parent}, WRITE_A, COMMIT])

    summary = fx.run(fx.config(("a", agent)))

    assert summary["verdict"] == "rejected"
    assert any("descend" in reason for reason in summary["reasons"])


def test_reported_commit_other_than_head_is_rejected(fx: Fixture) -> None:
    agent = fx.scenario("a", done(commit=fx.revision), steps=[WRITE_A, COMMIT])

    summary = fx.run(fx.config(("a", agent)))

    assert summary["verdict"] == "rejected"
    assert any("HEAD" in reason for reason in summary["reasons"])


def test_outside_change_is_rejected(fx: Fixture) -> None:
    agent = fx.scenario(
        "a", done(), steps=[WRITE_A, COMMIT, {"kind": "outside", "path": str(fx.feature / "stray.txt")}]
    )

    summary = fx.run(fx.config(("a", agent)))

    assert summary["verdict"] == "rejected"
    assert str(fx.feature) in summary["outside_changes"]


def test_blocked_asks_for_retry(fx: Fixture) -> None:
    agent = fx.scenario("a", done(None, [], status="BLOCKED"))

    summary = fx.run(fx.config(("a", agent)))

    assert summary["verdict"] == "retry"
    assert summary["result"]["status"] == "BLOCKED"


def test_recorded_invalid_payload_is_rejected_on_reassessment(fx: Fixture) -> None:
    # accept は記録を読み直して判定をやり直す。runner の検査の後でも、記録の payload が合わなければ取り込まない
    fx.run(fx.config(("a", fx.scenario("a", done(), steps=[WRITE_A, COMMIT]))))
    record = json.loads((fx.output / "task.json").read_text(encoding="utf-8"))
    batch = BatchResult.model_validate_json(json.dumps(record["batch"]))
    batch.results[0].attempts[0].payload = {**done(), "extra": "x"}

    assessment = mod.assess(fx.request(), batch)

    assert assessment.verdict == "rejected"
    assert assessment.result is None


def test_fallback_success_is_assessed_on_its_own_attempt(fx: Fixture) -> None:
    broken = fx.scenario("a", None, steps=[{"kind": "write", "path": "docs/x.md"}], no_receipt=True)
    backup = fx.scenario("b", done(), steps=[WRITE_A, COMMIT])

    summary = fx.run(fx.config(("a", broken), ("b", backup), fallback=1))

    assert summary["verdict"] == "importable", summary["reasons"]
    assert summary["requested_agent"] == "a"
    assert summary["actual_agent"] == "b"
    assert [attempt["agent_id"] for attempt in summary["attempts"]] == ["a", "b"]


def test_unconfirmed_stop_fails(fx: Fixture) -> None:
    agent = fx.scenario("a", done(), steps=[WRITE_A, COMMIT])
    fx.run(fx.config(("a", agent)))
    record = json.loads((fx.output / "task.json").read_text(encoding="utf-8"))
    batch = BatchResult.model_validate_json(json.dumps(record["batch"]))
    batch.results[0].attempts[0].stop_confirmed = False

    assessment = mod.assess(fx.request(), batch)

    assert assessment.verdict == "failed"


def test_run_refuses_main_checkout(fx: Fixture) -> None:
    with pytest.raises(mod.TaskInputError):
        fx.run(fx.config(("a", fx.scenario("a", done()))), fx.request(repository=str(fx.main)))


def test_non_ascii_paths_and_prompt_round_trip(fx: Fixture) -> None:
    agent = fx.scenario(
        "a", done(None, ["文書/説明 ファイル.md"]), steps=[{"kind": "write", "path": "文書/説明 ファイル.md"}]
    )

    summary = fx.run(fx.config(("a", agent)), fx.request(prompt=FINDING_CONTENT))

    assert summary["verdict"] == "importable", summary["reasons"]
    assert summary["changed_files"] == ["文書/説明 ファイル.md"]
    sent = Path(f"{agent}.prompt").read_text(encoding="utf-8", newline="")
    assert FINDING_CONTENT in sent
    assert '"文書/"' in sent


@pytest.mark.parametrize(
    ("target", "verdict"), [("src/new/a.py", "importable"), ("docs/a.py", "rejected")], ids=["inside", "outside"]
)
def test_rename_counts_both_paths(fx: Fixture, target: str, verdict: str) -> None:
    agent = fx.scenario(
        "a", done(None, ["src/a.py", target]), steps=[{"kind": "move", "from": "src/a.py", "to": target}]
    )

    summary = fx.run(fx.config(("a", agent)))

    assert summary["verdict"] == verdict, summary["reasons"]
    assert set(summary["changed_files"]) == {"src/a.py", target}


# --- accept と cleanup ----------------------------------------------------------------------------------------------


def registered(repo: Path) -> list[str]:
    output = git(repo, "worktree", "list", "--porcelain")
    return [line.removeprefix("worktree ") for line in output.splitlines() if line.startswith("worktree ")]


def test_accept_fast_forwards_agent_commit(fx: Fixture) -> None:
    summary = fx.run(fx.config(("a", fx.scenario("a", done(), steps=[WRITE_A, COMMIT]))))

    # run は feature を動かさず、accept が監査した commit だけを取り込む。
    assert git(fx.feature, "rev-parse", "HEAD") == fx.revision
    accepted = mod.accept(fx.output)

    assert accepted["state"] == "accepted"
    assert accepted["commit"] == summary["commit"]
    assert accepted["helper_commit"] is False
    assert git(fx.feature, "rev-parse", "HEAD") == summary["commit"]
    assert (fx.feature / "src/a.py").read_text(encoding="utf-8") == "a = 2\n"
    assert (fx.output / "accept.json").is_file()


def test_accept_commits_uncommitted_changes_with_message(fx: Fixture) -> None:
    message = "feat: src を直す\n\n# 行頭の # も残す\nCo-Authored-By: Fixture <fixture@example.invalid>"
    agent = fx.scenario(
        "a", done(None, ["src/a.py", "src/new/c.py"]), steps=[WRITE_A, {"kind": "write", "path": "src/new/c.py"}]
    )
    fx.run(fx.config(("a", agent)), fx.request(commit_message=message))

    accepted = mod.accept(fx.output)

    assert accepted["helper_commit"] is True
    assert git(fx.feature, "rev-parse", "HEAD") == accepted["commit"]
    assert git(fx.feature, "log", "-1", "--format=%B") == message
    assert git(fx.feature, "rev-parse", "HEAD~1") == fx.revision
    changed = git(fx.feature, "diff", "--name-only", fx.revision, "HEAD").splitlines()
    assert sorted(changed) == ["src/a.py", "src/new/c.py"]


def test_accept_reassesses_current_state(fx: Fixture) -> None:
    summary = fx.run(fx.config(("a", fx.scenario("a", done(), steps=[WRITE_A, COMMIT]))))
    (Path(summary["work_dir"]) / "docs/x.md").write_text("late\n", encoding="utf-8")

    with pytest.raises(mod.AcceptRefused):
        mod.accept(fx.output)

    assert git(fx.feature, "rev-parse", "HEAD") == fx.revision


@pytest.mark.parametrize("change", ["moved", "untracked"])
def test_accept_refuses_moved_or_dirty_feature(fx: Fixture, change: str) -> None:
    fx.run(fx.config(("a", fx.scenario("a", done(), steps=[WRITE_A, COMMIT]))))
    if change == "moved":
        git(fx.feature, "commit", "-q", "--allow-empty", "-m", "moved")
    else:
        (fx.feature / "stray.txt").write_text("x\n", encoding="utf-8")
    before = git(fx.feature, "rev-parse", "HEAD")

    with pytest.raises(mod.AcceptRefused):
        mod.accept(fx.output)

    assert git(fx.feature, "rev-parse", "HEAD") == before


def test_cleanup_removes_worktree_and_run_dir(fx: Fixture) -> None:
    summary = fx.run(fx.config(("a", fx.scenario("a", done(), steps=[WRITE_A, COMMIT]))))
    mod.accept(fx.output)

    cleaned = mod.cleanup(fx.output)

    assert cleaned["retained"] == []
    assert cleaned["removed_worktrees"] == [summary["work_dir"]]
    assert cleaned["removed_run_dir"] is True
    assert not fx.output.exists()
    assert summary["work_dir"] not in registered(fx.main)
    # 取り込んだ commit は feature の branch に残る
    assert git(fx.feature, "rev-parse", "HEAD") == summary["commit"]


def test_cleanup_retains_dirty_worktree(fx: Fixture) -> None:
    agent = fx.scenario("a", done(), steps=[WRITE_A, COMMIT, {"kind": "write", "path": "src/new/left.py"}])
    summary = fx.run(fx.config(("a", agent)))

    cleaned = mod.cleanup(fx.output)

    assert [item["path"] for item in cleaned["retained"]] == [summary["work_dir"]]
    assert cleaned["retained"][0]["reason"]
    assert cleaned["removed_run_dir"] is False
    assert fx.output.is_dir()
    assert summary["work_dir"] in registered(fx.main)


@pytest.mark.parametrize("field", ["stop_confirmed", "sensitive_paths"])
def test_cleanup_retains_unstopped_or_sensitive_attempt(fx: Fixture, field: str) -> None:
    summary = fx.run(fx.config(("a", fx.scenario("a", done(), steps=[WRITE_A, COMMIT]))))
    task = fx.output / "task.json"
    record = json.loads(task.read_text(encoding="utf-8"))
    attempt = record["batch"]["results"][0]["attempts"][0]
    if field == "stop_confirmed":
        attempt["stop_confirmed"] = False
    else:
        attempt["sensitive_paths"] = [str(Path(summary["work_dir"]).parent / "receipt.json")]
    task.write_text(json.dumps(record), encoding="utf-8")

    cleaned = mod.cleanup(fx.output)

    assert len(cleaned["retained"]) == 1
    assert cleaned["removed_worktrees"] == []
    assert fx.output.is_dir()
    assert summary["work_dir"] in registered(fx.main)


def test_cli_accept_and_cleanup_exit_codes(fx: Fixture, capsys: pytest.CaptureFixture[str]) -> None:
    agent = fx.scenario("a", done(files=["docs/x.md"]), steps=[{"kind": "write", "path": "docs/x.md"}, COMMIT])
    fx.run(fx.config(("a", agent)))

    assert mod.main(["accept", "--run-dir", str(fx.output)]) == 1
    assert json.loads(capsys.readouterr().out)["status"] == "refused"
    # 担当ファイルの外を commit した worktree は clean なので外せる。run_dir は自分のものなので消える
    assert mod.main(["cleanup", "--run-dir", str(fx.output)]) == 0
    assert json.loads(capsys.readouterr().out)["removed_run_dir"] is True
