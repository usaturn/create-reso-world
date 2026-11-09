"""Spec レビューの安全なライフサイクル（S: 失敗の成功扱い・取り違え・記録の消失を防ぐ）を確かめる。

外部の担当は注入した run_workflow と fake adapter の設定だけで動かし、実モデル・API・ネットワークを使わない。
"""

from __future__ import annotations

import importlib.util
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from tools.agent_runner import Config
from tools.agent_runner.models import (
    Agent,
    Assignment,
    Attempt,
    BatchResult,
    Identity,
    Result,
    Role,
    Workflow,
)

pytest_plugins = ("tools.test_support.plugin",)
# 偽の担当だけを起動するので、runner の担当の中でもテストの中だけ depth を外す
pytestmark = pytest.mark.usefixtures("outside_runner")


@pytest.fixture(autouse=True)
def isolated_git_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """一時 Git に外の GIT_* と利用者の設定を届けない。"""
    for name in list(os.environ):
        if name.startswith("GIT_"):
            monkeypatch.delenv(name)
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.delenv("SESSION", raising=False)


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "review_spec.py"
SPEC = importlib.util.spec_from_file_location("issue_review_spec", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
mod: Any = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = mod
SPEC.loader.exec_module(mod)


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


class Fixture:
    """コードの checkout と、別の DOC_ROOT にある Spec を一時 Git で作る。"""

    def __init__(self, tmp_path: Path) -> None:
        self.tmp = tmp_path
        self.tmp.mkdir(parents=True, exist_ok=True)
        self.main = tmp_path / "repo"
        self.main.mkdir()
        git(self.main, "init", "-q", "-b", "main")
        git(self.main, "config", "user.name", "Fixture")
        git(self.main, "config", "user.email", "fixture@example.invalid")
        (self.main / "src.py").write_text("value = 1\n", encoding="utf-8")
        git(self.main, "add", "-A")
        git(self.main, "commit", "-qm", "base")
        self.feature = tmp_path / "feature"
        git(self.main, "worktree", "add", "-q", "-b", "feature", str(self.feature))
        self.revision = git(self.feature, "rev-parse", "HEAD")

        self.doc = tmp_path / "docs-root"
        self.doc.mkdir()
        git(self.doc, "init", "-q", "-b", "main")
        git(self.doc, "config", "user.name", "Fixture")
        git(self.doc, "config", "user.email", "fixture@example.invalid")
        self.spec = self.doc / "docs" / "design.md"
        self.spec.parent.mkdir(parents=True)
        self.spec_bytes = "# 設計\r\n\r\n複数行の日本語の Spec。\r\n変更してはいけない版。\r\n".encode()
        self.spec.write_bytes(self.spec_bytes)
        git(self.doc, "add", "-A")
        git(self.doc, "commit", "-qm", "spec")
        self.ledger = tmp_path / "session" / "review-ledger"
        self.runner = tmp_path / "session" / "runner-1"

    def request(self, **overrides: object) -> Any:
        return mod.ReviewRequest.model_validate(
            {
                "spec_path": str(self.spec),
                "repository": str(self.feature),
                "revision": self.revision,
                "issue": {
                    "repo": "usaturn/create-reso-world",
                    "number": 42,
                    "url": "https://github.com/usaturn/create-reso-world/issues/42",
                    "title": "レビューの入口",
                    "body": "複数行の日本語の Issue。\n2 行目。\n",
                },
                "context": "利用者の明示指定。\n前の版のレビューは無い。\n",
                **overrides,
            }
        )

    def config(self, agents: list[str], *, writes: bool = False, role: str = "spec-review") -> Config:
        names = list(agents)
        return Config(
            agents={
                name: Agent(runtime="pi", command=["fake-reviewer"], model=name)
                for name in names
                if name != "self"
            },
            roles={role: Role(writes=writes, deadline_seconds=60.0, result_shape="json")},
            workflows={"issue": Workflow(assignments={role: Assignment(agents=names)})},
        )

    def review(self, **overrides: object) -> dict[str, Any]:
        request = self.request(**overrides)
        return mod.review(self.config(["self"]), request, None, ledger_dir=self.ledger)


@pytest.fixture
def fx(tmp_path: Path) -> Fixture:
    return Fixture(tmp_path)


def result_for(summary: dict[str, Any], **overrides: object) -> dict[str, Any]:
    return {
        "review_id": summary["review_id"],
        "spec_sha256": summary["spec_sha256"],
        "status": "completed",
        "findings": [],
        "incomplete": [],
        **overrides,
    }


def write_json(path: Path, payload: object) -> Path:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


# --- 記録の保存先と版の対応 -----------------------------------------------------------------------------------------


def test_self_review_records_outside_both_worktrees_and_advances(fx: Fixture) -> None:
    """S: 記録を worktree に置くと回収で消える。CRLF の生バイトを結び付け、採否の次工程を誤らせない。"""
    summary = fx.review()

    assert summary["state"] == "self"
    assert summary["spec_sha256"] == hashlib.sha256(fx.spec_bytes).hexdigest()
    review_dir = Path(summary["review_dir"])
    assert review_dir == fx.ledger / "design.spec-review" / "review-1"
    assert (review_dir / "spec.md").read_bytes() == fx.spec_bytes
    assert b"\r\n" in (review_dir / "spec.md").read_bytes()
    assert not (fx.spec.parent / "design.spec-review").exists()
    assert fx.spec.read_bytes() == fx.spec_bytes
    assert not any(path.is_relative_to(fx.feature) for path in review_dir.parents)
    assert not any(path.is_relative_to(fx.doc) for path in review_dir.parents)

    first = write_json(
        fx.tmp / "result-1.json",
        result_for(
            summary,
            findings=[
                {
                    "id": "S1",
                    "section": "設計 2",
                    "problem": "保存先が曖昧",
                    "evidence": "Spec の文",
                    "impact": "記録が消える",
                    "severity": "important",
                    "suggestion": "保存先を明記する",
                }
            ],
        ),
    )
    submitted = mod.submit(review_dir, first)
    assert submitted["state"] == "completed"

    changed = fx.spec_bytes.replace("変更してはいけない版。".encode(), "変更後の版。".encode()) + "追記\r\n".encode()
    fx.spec.write_bytes(changed)
    decisions = write_json(
        fx.tmp / "decisions-1.json",
        {
            "decisions": [
                {"id": "S1", "decision": "adopt", "reason": "採用する", "reflected_in": "設計 2 の保存先"}
            ]
        },
    )

    decided = mod.decide(review_dir, decisions)

    assert decided["next"] == "rereview"
    assert (review_dir / "reflected.md").read_bytes() == changed
    saved = json.loads((review_dir / "decisions.json").read_text(encoding="utf-8"))
    assert saved["reviewed_spec_sha256"] == summary["spec_sha256"]
    assert saved["reflected_spec_sha256"] == decided["reflected_spec_sha256"]

    # 同じ担当による再レビューは 1 回だけ。2 回目は新しい Spec の版を結び付ける
    second = mod.review(fx.config(["self"]), fx.request(), None, ledger_dir=fx.ledger)
    assert second["round"] == 2
    second_result = write_json(
        fx.tmp / "result-2.json",
        result_for(
            second,
            findings=[
                {
                    "id": "S2",
                    "section": "設計 3",
                    "problem": "残る軽微な点",
                    "evidence": "Spec の文",
                    "impact": "小さい",
                    "severity": "minor",
                    "suggestion": "直す",
                }
            ],
        ),
    )
    mod.submit(Path(second["review_dir"]), second_result)
    second_decisions = write_json(
        fx.tmp / "decisions-2.json",
        {"decisions": [{"id": "S2", "decision": "reject", "reason": "今回は対象外", "reflected_in": None}]},
    )
    assert mod.decide(Path(second["review_dir"]), second_decisions)["next"] == "plan"


def test_self_submit_refuses_after_the_code_head_moved(fx: Fixture) -> None:
    """S: コード HEAD が変わった後も self の結果を completed にすると、未レビューの版で次工程へ進む。"""
    summary = fx.review()
    review_dir = Path(summary["review_dir"])
    (fx.feature / "src.py").write_text("value = 2\n", encoding="utf-8")
    git(fx.feature, "add", "-A")
    git(fx.feature, "commit", "-qm", "changed during the review")

    result = write_json(fx.tmp / "result.json", result_for(summary))
    submitted = mod.submit(review_dir, result)

    assert submitted["state"] == "failed", submitted["reasons"]
    assert any("repository" in reason for reason in submitted["reasons"]), submitted["reasons"]
    recorded = json.loads((review_dir / "review.json").read_text(encoding="utf-8"))
    assert recorded["state"] == "failed"
    decisions = write_json(fx.tmp / "decisions.json", {"decisions": []})
    with pytest.raises(mod.ReviewInputError):
        mod.decide(review_dir, decisions)


def test_missing_session_and_worktree_ledgers_are_refused(fx: Fixture, monkeypatch: pytest.MonkeyPatch) -> None:
    """S: 既定の保存先を推測すると、記録がコードや Spec の worktree に入り回収で消える。"""
    with pytest.raises(mod.ReviewInputError):
        mod.review(fx.config(["self"]), fx.request(), None)

    monkeypatch.setenv("SESSION", str(fx.ledger))
    summary = mod.review(fx.config(["self"]), fx.request(), None)
    assert Path(summary["review_dir"]).is_relative_to(fx.ledger)

    for target in (fx.feature / "records", fx.doc / "records"):
        with pytest.raises(mod.ReviewInputError):
            mod.review(fx.config(["self"]), fx.request(), None, ledger_dir=target)
        assert not (target / "design.spec-review").exists()

    link = fx.tmp / "ledger-link"
    link.symlink_to(fx.doc / "records", target_is_directory=True)
    with pytest.raises(mod.ReviewInputError):
        mod.review(fx.config(["self"]), fx.request(), None, ledger_dir=link)
    assert not (fx.doc / "records" / "design.spec-review").exists()


def test_wrong_result_identity_and_invalid_decisions_leave_records_untouched(fx: Fixture) -> None:
    """S: 取り違えた結果や採否を受理すると、別の版を完了扱いするか履歴を上書きする。"""
    summary = fx.review()
    review_dir = Path(summary["review_dir"])
    findings = [
        {
            "id": "S1",
            "section": "設計 1",
            "problem": "問題 1",
            "evidence": "根拠 1",
            "impact": "影響 1",
            "severity": "important",
            "suggestion": "提案 1",
        },
        {
            "id": "S2",
            "section": "設計 2",
            "problem": "問題 2",
            "evidence": "根拠 2",
            "impact": "影響 2",
            "severity": "minor",
            "suggestion": "提案 2",
        },
    ]
    correct = result_for(summary, findings=findings)

    wrong_id = write_json(fx.tmp / "wrong-id.json", {**correct, "review_id": "0" * 32})
    with pytest.raises(mod.ReviewInputError):
        mod.submit(review_dir, wrong_id)
    assert not (review_dir / "review.json").exists()

    wrong_hash = write_json(fx.tmp / "wrong-hash.json", {**correct, "spec_sha256": "0" * 64})
    with pytest.raises(mod.ReviewInputError):
        mod.submit(review_dir, wrong_hash)
    assert not (review_dir / "review.json").exists()

    good = write_json(fx.tmp / "good.json", correct)
    mod.submit(review_dir, good)
    recorded = (review_dir / "review.json").read_bytes()
    with pytest.raises(mod.ReviewInputError):
        mod.submit(review_dir, good)
    assert (review_dir / "review.json").read_bytes() == recorded

    invalid = {
        "missing": {"decisions": [{"id": "S1", "decision": "adopt", "reason": "採用", "reflected_in": "設計 1"}]},
        "duplicate": {
            "decisions": [
                {"id": "S1", "decision": "adopt", "reason": "採用", "reflected_in": "設計 1"},
                {"id": "S1", "decision": "reject", "reason": "不採用", "reflected_in": None},
                {"id": "S2", "decision": "reject", "reason": "不採用", "reflected_in": None},
            ]
        },
        "unreflected": {
            "decisions": [
                {"id": "S1", "decision": "adopt", "reason": "採用", "reflected_in": "設計 1"},
                {"id": "S2", "decision": "reject", "reason": "不採用", "reflected_in": None},
            ]
        },
    }
    for name, payload in invalid.items():
        path = write_json(fx.tmp / f"{name}.json", payload)
        with pytest.raises(mod.ReviewInputError):
            mod.decide(review_dir, path)
        assert not (review_dir / "decisions.json").exists(), name
        assert not (review_dir / "reflected.md").exists(), name

    fx.spec.write_bytes(fx.spec_bytes + b"reflected\r\n")
    accepted = write_json(
        fx.tmp / "accepted.json",
        {
            "decisions": [
                {"id": "S1", "decision": "adopt", "reason": "採用", "reflected_in": "設計 1"},
                {"id": "S2", "decision": "reject", "reason": "不採用", "reflected_in": None},
            ]
        },
    )
    mod.decide(review_dir, accepted)
    decided = (review_dir / "decisions.json").read_bytes()
    with pytest.raises(mod.ReviewInputError):
        mod.decide(review_dir, accepted)
    assert (review_dir / "decisions.json").read_bytes() == decided


# --- 外部実行の結果の検査 -------------------------------------------------------------------------------------------


def batch(
    payload: dict[str, Any],
    *,
    outside: list[str] | None = None,
    unprotected: list[str] | None = None,
    stop: bool = True,
    work_dir: Path | None = None,
) -> BatchResult:
    attempt = Attempt(
        agent_id="reviewer",
        state="success",
        elapsed_seconds=0.1,
        stop_confirmed=stop,
        work_dir=work_dir,
        payload=payload,
        identity=Identity(model="fake"),
    )
    outcome = Result(
        request_id="request-1",
        role="spec-review",
        requested_agent="reviewer",
        actual_agent="reviewer",
        state="success",
        attempts=[attempt],
    )
    return BatchResult(
        run_id="run-1",
        state="success",
        assignments={"spec-review": ["reviewer"]},
        results=[outcome],
        outside_changes=outside or [],
        unprotected_changes=unprotected or [],
        elapsed_seconds=0.1,
        artifact_dir=Path("/tmp/review-artifact"),
    )


def last_request(ledger: Path) -> dict[str, Any]:
    review_dir = mod._reviews(ledger / "design.spec-review")[-1]
    return json.loads((review_dir / "request.json").read_text(encoding="utf-8"))


def external_review(
    fx: Fixture,
    monkeypatch: pytest.MonkeyPatch,
    make: Any,
    *,
    create_runner: bool = True,
) -> dict[str, Any]:
    def fake_run(*args: Any, **kwargs: Any) -> BatchResult:
        if create_runner:
            # 実 runner と同じく親は作らない（SKILL の手順が親を用意する）
            kwargs["output_dir"].mkdir(mode=0o700)
            (kwargs["output_dir"] / "log.txt").write_text("fake\n", encoding="utf-8")
        record = last_request(fx.ledger)
        return make(record["review_id"], record["spec_sha256"])

    monkeypatch.setattr(mod, "run_workflow", fake_run)
    return mod.review(
        fx.config(["reviewer"]), fx.request(), fx.runner, ledger_dir=fx.ledger
    )


def test_external_review_marks_incomplete_mismatch_outside_and_unstopped_as_failed(
    fx: Fixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    """S: 未完了・取り違え・外部書込・停止未確認を completed（指摘 0 件）と読むと、悪い版で次工程へ進む。"""
    cases = {
        "incomplete": (
            lambda review_id, sha: batch(
                {
                    "review_id": review_id,
                    "spec_sha256": sha,
                    "status": "incomplete",
                    "findings": [],
                    "incomplete": ["文脈が足りない"],
                }
            ),
            "incomplete",
        ),
        "mismatch": (
            lambda review_id, sha: batch(
                {
                    "review_id": "0" * 32,
                    "spec_sha256": sha,
                    "status": "completed",
                    "findings": [],
                    "incomplete": [],
                }
            ),
            "does not match",
        ),
        "outside": (
            lambda review_id, sha: batch(
                {
                    "review_id": review_id,
                    "spec_sha256": sha,
                    "status": "completed",
                    "findings": [],
                    "incomplete": [],
                },
                outside=["src.py"],
            ),
            "outside_changes",
        ),
        "unstopped": (
            lambda review_id, sha: batch(
                {
                    "review_id": review_id,
                    "spec_sha256": sha,
                    "status": "completed",
                    "findings": [],
                    "incomplete": [],
                },
                stop=False,
            ),
            "stop_unconfirmed",
        ),
    }
    for name, (make, expected) in cases.items():
        # 各ケースは独立した SESSION・Spec を使う
        case = Fixture(fx.tmp / name)
        summary = external_review(case, monkeypatch, make)
        assert summary["state"] == "failed", name
        assert any(expected in reason for reason in summary["reasons"]), (name, summary["reasons"])


def test_unprotected_changes_are_only_reported(fx: Fixture, monkeypatch: pytest.MonkeyPatch) -> None:
    """S: 保護しない checkout の観測で成功を失敗にすると、無関係な利用者の作業がレビューを止める。"""

    def make(review_id: str, sha: str) -> BatchResult:
        return batch(
            {
                "review_id": review_id,
                "spec_sha256": sha,
                "status": "completed",
                "findings": [],
                "incomplete": [],
            },
            unprotected=["/other/checkout: content_changed"],
        )

    summary = external_review(fx, monkeypatch, make)

    assert summary["state"] == "completed", summary["reasons"]
    assert summary["unprotected_changes"] == ["/other/checkout: content_changed"]
    record = json.loads((Path(summary["review_dir"]) / "review.json").read_text(encoding="utf-8"))
    assert record["unprotected_changes"] == ["/other/checkout: content_changed"]


def test_reviewer_worktree_change_fails_and_cleanup_keeps_it_and_the_ledger(
    fx: Fixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    """S: 読取専用の担当がコードを変えたのに成功扱いすると、レビューした版と実際の版がずれる。"""
    reviewer = fx.tmp / "reviewer-worktree"
    git(fx.main, "worktree", "add", "--detach", str(reviewer), fx.revision)
    (reviewer / "src.py").write_text("changed = 1\n", encoding="utf-8")

    def make(review_id: str, sha: str) -> BatchResult:
        return batch(
            {
                "review_id": review_id,
                "spec_sha256": sha,
                "status": "completed",
                "findings": [],
                "incomplete": [],
            },
            work_dir=reviewer,
        )

    summary = external_review(fx, monkeypatch, make)

    assert summary["state"] == "failed"
    assert any("changed its worktree" in reason for reason in summary["reasons"]), summary["reasons"]
    review_dir = Path(summary["review_dir"])
    cleaned = mod.cleanup(review_dir)
    assert cleaned["removed_worktrees"] == []
    assert any(item["path"] == str(reviewer) for item in cleaned["retained"])
    assert reviewer.is_dir()
    assert fx.runner.is_dir()
    assert review_dir.is_dir()


def test_review_after_a_runner_without_a_result_is_refused(fx: Fixture, monkeypatch: pytest.MonkeyPatch) -> None:
    """S: runner が戻らなかった試行を failed として読み飛ばすと、旧担当が動いたまま次のレビューを始める。"""

    def broken_run(*args: Any, **kwargs: Any) -> BatchResult:
        kwargs["output_dir"].mkdir(mode=0o700)
        (kwargs["output_dir"] / "log.txt").write_text("partial\n", encoding="utf-8")
        raise OSError("the runner did not finish")

    monkeypatch.setattr(mod, "run_workflow", broken_run)
    failed = mod.review(fx.config(["reviewer"]), fx.request(), fx.runner, ledger_dir=fx.ledger)
    assert failed["state"] == "failed"
    review_dir = Path(failed["review_dir"])
    second_runner = fx.tmp / "session" / "runner-2"

    with pytest.raises(mod.ReviewInputError):
        mod.review(fx.config(["reviewer"]), fx.request(), second_runner, ledger_dir=fx.ledger)

    assert mod._reviews(fx.ledger / "design.spec-review") == [review_dir]
    assert not second_runner.exists()


def test_cleanup_removes_only_safe_runner_output_and_keeps_the_ledger(
    fx: Fixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    """S: ledger まで消すとレビュー履歴が失われ、停止不明の runner 出力を消すと証拠が失われる。"""

    def make(review_id: str, sha: str) -> BatchResult:
        return batch(
            {
                "review_id": review_id,
                "spec_sha256": sha,
                "status": "completed",
                "findings": [],
                "incomplete": [],
            }
        )

    summary = external_review(fx, monkeypatch, make)
    review_dir = Path(summary["review_dir"])
    cleaned = mod.cleanup(review_dir)

    assert cleaned == {"removed_worktrees": [], "retained": [], "removed_runner_dir": True}
    assert not fx.runner.exists()
    assert review_dir.is_dir()

    unknown = Fixture(fx.tmp / "unknown")

    def broken_run(*args: Any, **kwargs: Any) -> BatchResult:
        kwargs["output_dir"].mkdir(mode=0o700)
        (kwargs["output_dir"] / "log.txt").write_text("partial\n", encoding="utf-8")
        raise OSError("the runner did not finish")

    monkeypatch.setattr(mod, "run_workflow", broken_run)
    failed = mod.review(unknown.config(["reviewer"]), unknown.request(), unknown.runner, ledger_dir=unknown.ledger)
    assert failed["state"] == "failed"
    assert any("did not finish" in reason for reason in failed["reasons"])
    retained = mod.cleanup(Path(failed["review_dir"]))
    assert retained["removed_runner_dir"] is False
    assert any(item["path"] == str(unknown.runner) for item in retained["retained"])
    assert unknown.runner.is_dir()
    assert Path(failed["review_dir"]).is_dir()
