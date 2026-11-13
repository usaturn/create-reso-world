"""Spec レビューの安全なライフサイクル（S: 失敗の成功扱い・取り違え・記録の消失を防ぐ）を確かめる。

外部の担当は注入した run_workflow と fake adapter の設定だけで動かし、実モデル・API・ネットワークを使わない。
"""

from __future__ import annotations

import errno
import fcntl
import hashlib
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

from tools.agent_runner import Config
from tools.agent_runner.adapters import AdapterContext, AdapterOutcome, Capabilities, LaunchSpec
from tools.agent_runner.models import (
    Agent,
    Assignment,
    Attempt,
    BatchResult,
    Identity,
    Receipt,
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
        self.reviewer = tmp_path / "reviewer-clean"
        git(self.main, "worktree", "add", "--detach", str(self.reviewer), self.revision)

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
    request_path: Path | None = None,
    previous_attempts: list[Attempt] | None = None,
) -> BatchResult:
    attempt = Attempt(
        agent_id="reviewer",
        state="success",
        elapsed_seconds=0.1,
        stop_confirmed=stop,
        work_dir=work_dir,
        request_path=request_path,
        payload=payload,
        identity=Identity(model="fake"),
    )
    outcome = Result(
        request_id="request-1",
        role="spec-review",
        requested_agent="reviewer",
        actual_agent="reviewer",
        state="success",
        attempts=[*(previous_attempts or []), attempt],
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
            work_dir=fx.reviewer,
        )

    summary = external_review(fx, monkeypatch, make)

    assert summary["state"] == "completed", summary["reasons"]
    assert summary["unprotected_changes"] == ["/other/checkout: content_changed"]
    record = json.loads((Path(summary["review_dir"]) / "review.json").read_text(encoding="utf-8"))
    assert record["unprotected_changes"] == ["/other/checkout: content_changed"]


def test_external_review_fails_when_the_repository_moves_during_the_review(
    fx: Fixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    """S: レビュー中に CODE_ROOT の HEAD が変わったのに completed と記録すると、別の版を採用する。"""

    def make(review_id: str, sha: str) -> BatchResult:
        (fx.feature / "src.py").write_text("value = 2\n", encoding="utf-8")
        git(fx.feature, "commit", "-qam", "move during review")
        return batch(
            {
                "review_id": review_id,
                "spec_sha256": sha,
                "status": "completed",
                "findings": [],
                "incomplete": [],
            },
            work_dir=fx.reviewer,
        )

    summary = external_review(fx, monkeypatch, make)

    assert summary["state"] == "failed"
    assert any("the repository changed during the review" in reason for reason in summary["reasons"]), summary[
        "reasons"
    ]


def test_external_review_accepts_a_fallback_after_preparation_failed(
    fx: Fixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    """S: 準備前に終わった試行の不在 worktree を拒否すると、有効な fallback の結果を失う。"""
    attempt_dir = fx.tmp / "failed-before-preparation" / "attempt-1"
    primary = Attempt(
        agent_id="primary",
        state="response_failed",
        elapsed_seconds=0.1,
        stop_confirmed=True,
        work_dir=attempt_dir / "worktree",
        request_path=attempt_dir / "request.json",
    )

    def make(review_id: str, sha: str) -> BatchResult:
        return batch(
            {
                "review_id": review_id,
                "spec_sha256": sha,
                "status": "completed",
                "findings": [],
                "incomplete": [],
            },
            previous_attempts=[primary],
            work_dir=fx.reviewer,
        )

    summary = external_review(fx, monkeypatch, make)

    assert summary["state"] == "completed", summary["reasons"]
    record = json.loads((Path(summary["review_dir"]) / "review.json").read_text(encoding="utf-8"))
    assert record["state"] == "completed"
    assert record["result"]["review_id"] == summary["review_id"]


def test_external_review_rejects_a_worktree_missing_after_preparation(
    fx: Fixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    """S: 準備後に消えた worktree を黙って受け入れると、読取専用の監査を飛ばして成功扱いする。"""
    attempt_dir = fx.tmp / "missing-after-preparation" / "attempt-1"
    attempt_dir.mkdir(parents=True)
    request_path = attempt_dir / "request.json"
    request_path.write_text("{}", encoding="utf-8")
    primary = Attempt(
        agent_id="primary",
        state="response_failed",
        elapsed_seconds=0.1,
        stop_confirmed=True,
        work_dir=attempt_dir / "worktree",
        request_path=request_path,
    )

    def make(review_id: str, sha: str) -> BatchResult:
        return batch(
            {
                "review_id": review_id,
                "spec_sha256": sha,
                "status": "completed",
                "findings": [],
                "incomplete": [],
            },
            previous_attempts=[primary],
            work_dir=fx.reviewer,
        )

    summary = external_review(fx, monkeypatch, make)

    assert summary["state"] == "failed"
    assert any("the worktree of primary is missing" in reason for reason in summary["reasons"]), summary["reasons"]


def test_external_review_rejects_a_successful_attempt_without_a_worktree(
    fx: Fixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    """S: 成功した試行の worktree が無いのに受理すると、読取専用の監査を飛ばして成功扱いする。"""

    def make(work_dir: Path | None) -> Any:
        def build(review_id: str, sha: str) -> BatchResult:
            return batch(
                {
                    "review_id": review_id,
                    "spec_sha256": sha,
                    "status": "completed",
                    "findings": [],
                    "incomplete": [],
                },
                work_dir=work_dir,
            )

        return build

    # 結果を持つ試行は、worktree のパスが無い場合も、パスはあるが消えている場合も監査できない
    for name, with_path in (("missing-worktree", True), ("no-worktree-path", False)):
        case = Fixture(fx.tmp / name)
        work_dir = case.tmp / "gone-worktree" if with_path else None
        summary = external_review(case, monkeypatch, make(work_dir))
        assert summary["state"] == "failed", name
        assert any("the worktree of reviewer is missing" in reason for reason in summary["reasons"]), (
            name,
            summary["reasons"],
        )


def test_external_review_rejects_a_symlink_worktree(
    fx: Fixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    """S: symlink をたどって clean な参照先を監査すると、担当の変更を見落として成功扱いする。"""
    link = fx.tmp / "reviewer-link"
    link.symlink_to(fx.reviewer, target_is_directory=True)
    # 参照先はレビューした版のまま clean なので、symlink を許す実装では completed になる
    assert git(fx.reviewer, "rev-parse", "HEAD") == fx.revision
    assert git(fx.reviewer, "status", "--porcelain") == ""
    link_target = os.readlink(link)
    target_bytes = (fx.reviewer / "src.py").read_bytes()
    target_mode = stat.S_IMODE((fx.reviewer / "src.py").stat().st_mode)
    registered = git(fx.main, "worktree", "list", "--porcelain")

    def make(review_id: str, sha: str) -> BatchResult:
        return batch(
            {
                "review_id": review_id,
                "spec_sha256": sha,
                "status": "completed",
                "findings": [],
                "incomplete": [],
            },
            work_dir=link,
        )

    summary = external_review(fx, monkeypatch, make)

    assert summary["state"] == "failed"
    assert any(
        "the worktree of reviewer contains a symlink, so its changes cannot be audited" in reason
        for reason in summary["reasons"]
    ), summary["reasons"]
    assert link.is_symlink()
    assert os.readlink(link) == link_target
    assert (fx.reviewer / "src.py").read_bytes() == target_bytes
    assert stat.S_IMODE((fx.reviewer / "src.py").stat().st_mode) == target_mode
    assert git(fx.main, "worktree", "list", "--porcelain") == registered


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
            },
            work_dir=fx.reviewer,
        )

    summary = external_review(fx, monkeypatch, make)
    review_dir = Path(summary["review_dir"])
    cleaned = mod.cleanup(review_dir)

    assert cleaned == {"removed_worktrees": [str(fx.reviewer)], "retained": [], "removed_runner_dir": True}
    assert not fx.reviewer.exists()
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


# --- 回収実績と再実行 -----------------------------------------------------------------------------------------------


def completed(review_id: str, sha: str) -> dict[str, Any]:
    return {
        "review_id": review_id,
        "spec_sha256": sha,
        "status": "completed",
        "findings": [],
        "incomplete": [],
    }


def cleanup_events(review_dir: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in (review_dir / "cleanup.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_cleanup_records_collection_and_a_repeat_is_a_noop(fx: Fixture, monkeypatch: pytest.MonkeyPatch) -> None:
    """S: 回収実績を残さないと再実行で別の対象を消し、記録を上書きすると履歴を失う。"""

    def make(review_id: str, sha: str) -> BatchResult:
        return batch(completed(review_id, sha), work_dir=fx.reviewer)

    summary = external_review(fx, monkeypatch, make)
    review_dir = Path(summary["review_dir"])
    review_bytes = (review_dir / "review.json").read_bytes()

    first = mod.cleanup(review_dir)

    assert first == {"removed_worktrees": [str(fx.reviewer)], "retained": [], "removed_runner_dir": True}
    events = cleanup_events(review_dir)
    assert [event["event"] for event in events] == ["worktree_removed", "runner_dir_removed"]
    assert all(event["review_id"] == summary["review_id"] for event in events)
    assert all(event["spec_sha256"] == summary["spec_sha256"] for event in events)
    assert all(event["run_id"] == "run-1" for event in events)
    assert all(event["runner_dir"] == str(fx.runner) for event in events)
    assert (review_dir / "review.json").read_bytes() == review_bytes

    second = mod.cleanup(review_dir)

    assert second == {"removed_worktrees": [], "retained": [], "removed_runner_dir": False}
    assert not fx.reviewer.exists()
    assert not fx.runner.exists()
    assert (review_dir / "review.json").read_bytes() == review_bytes


def test_cleanup_after_a_partial_collection_leaves_the_collected_worktree_alone(
    fx: Fixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    """S: 部分回収の再実行で回収済みの worktree を別の対象として扱わない。"""
    clean = fx.tmp / "reviewer-clean-2"
    git(fx.main, "worktree", "add", "--detach", str(clean), fx.revision)
    dirty = fx.tmp / "reviewer-dirty"
    git(fx.main, "worktree", "add", "--detach", str(dirty), fx.revision)
    (dirty / "src.py").write_text("changed = 1\n", encoding="utf-8")
    primary = Attempt(
        agent_id="primary",
        state="response_failed",
        elapsed_seconds=0.1,
        stop_confirmed=True,
        work_dir=clean,
    )

    def make(review_id: str, sha: str) -> BatchResult:
        return batch(completed(review_id, sha), previous_attempts=[primary], work_dir=dirty)

    summary = external_review(fx, monkeypatch, make)
    review_dir = Path(summary["review_dir"])

    first = mod.cleanup(review_dir)

    assert first["removed_worktrees"] == [str(clean)]
    assert [item["path"] for item in first["retained"]] == [str(dirty)]
    assert first["removed_runner_dir"] is False
    assert not clean.exists()
    assert dirty.is_dir()
    assert fx.runner.is_dir()

    git(dirty, "checkout", "--", "src.py")
    second = mod.cleanup(review_dir)

    assert second == {"removed_worktrees": [str(dirty)], "retained": [], "removed_runner_dir": True}
    assert not dirty.exists()
    assert not fx.runner.exists()
    events = cleanup_events(review_dir)
    assert [event["path"] for event in events if event["event"] == "worktree_removed"] == [str(clean), str(dirty)]


def test_cleanup_rejects_a_changed_review_parent_before_side_effects(
    fx: Fixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    """S: 親を symlink に差し替えた領域で消すと、記録の外の対象を消して履歴を失う。"""

    def make(review_id: str, sha: str) -> BatchResult:
        return batch(completed(review_id, sha), work_dir=fx.reviewer)

    summary = external_review(fx, monkeypatch, make)
    review_dir = Path(summary["review_dir"])
    parent = review_dir.parent
    moved = fx.tmp / "moved-review-parent"
    parent.rename(moved)
    parent.symlink_to(moved, target_is_directory=True)
    registered = git(fx.main, "worktree", "list", "--porcelain")
    review_bytes = (moved / review_dir.name / "review.json").read_bytes()
    request_bytes = (moved / review_dir.name / "request.json").read_bytes()

    with pytest.raises(mod.CleanupInputError) as raised:
        mod.cleanup(review_dir)

    assert str(review_dir / "request.json") in raised.value.records
    assert fx.reviewer.is_dir()
    assert fx.runner.is_dir()
    assert git(fx.main, "worktree", "list", "--porcelain") == registered
    assert not list(moved.rglob("cleanup-success-*.json"))
    assert not (moved / review_dir.name / "cleanup.jsonl").exists()
    assert (moved / review_dir.name / "review.json").read_bytes() == review_bytes
    assert (moved / review_dir.name / "request.json").read_bytes() == request_bytes
    assert parent.is_symlink()


def test_cleanup_keeps_a_path_and_runner_directory_that_reappear_after_collection(
    fx: Fixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    """S: 回収後に再出現した path を消すと、今回の回収対象でない新しい作業を失う。"""

    def make(review_id: str, sha: str) -> BatchResult:
        return batch(completed(review_id, sha), work_dir=fx.reviewer)

    summary = external_review(fx, monkeypatch, make)
    review_dir = Path(summary["review_dir"])
    mod.cleanup(review_dir)
    assert not fx.reviewer.exists()
    assert not fx.runner.exists()

    fx.reviewer.mkdir()
    (fx.reviewer / "new.txt").write_text("new\n", encoding="utf-8")
    fx.runner.mkdir()
    (fx.runner / "log.txt").write_text("new\n", encoding="utf-8")

    cleaned = mod.cleanup(review_dir)

    assert cleaned["removed_worktrees"] == []
    assert cleaned["removed_runner_dir"] is False
    assert any(item["path"] == str(fx.reviewer) for item in cleaned["retained"])
    assert any(item["path"] == str(fx.runner) for item in cleaned["retained"])
    assert (fx.reviewer / "new.txt").read_text(encoding="utf-8") == "new\n"
    assert (fx.runner / "log.txt").read_text(encoding="utf-8") == "new\n"


@pytest.mark.parametrize("receipt", ["corrupt", "mismatch", "symlink"])
def test_cleanup_refuses_a_bad_receipt_before_side_effects(
    fx: Fixture, monkeypatch: pytest.MonkeyPatch, receipt: str
) -> None:
    """S: 壊れた・対応しない回収記録を信じると、別の対象を消すか履歴を上書きする。"""

    def make(review_id: str, sha: str) -> BatchResult:
        return batch(completed(review_id, sha), work_dir=fx.reviewer)

    summary = external_review(fx, monkeypatch, make)
    review_dir = Path(summary["review_dir"])
    path = review_dir / "cleanup.jsonl"
    if receipt == "corrupt":
        path.write_text("{not json}\n", encoding="utf-8")
    elif receipt == "mismatch":
        path.write_text(
            json.dumps(
                {
                    "event": "worktree_removed",
                    "review_id": "0" * 32,
                    "kind": "spec-review",
                    "spec_sha256": summary["spec_sha256"],
                    "run_id": "run-1",
                    "runner_dir": str(fx.runner),
                    "path": str(fx.reviewer),
                    "removed_at": "2026-11-10T00:00:00+00:00",
                }
            )
            + "\n",
            encoding="utf-8",
        )
    else:
        target = fx.tmp / "receipt-target.json"
        target.write_text("do not read\n", encoding="utf-8")
        path.symlink_to(target)

    with pytest.raises(mod.CleanupInputError) as raised:
        mod.cleanup(review_dir)

    assert any(item["path"] == str(fx.reviewer) for item in raised.value.retained)
    assert any(item["path"] == str(fx.runner) for item in raised.value.retained)
    assert str(path) in raised.value.records
    assert str(review_dir / "request.json") in raised.value.records
    assert fx.reviewer.is_dir()
    assert fx.runner.is_dir()
    assert (review_dir / "review.json").is_file()


def test_cleanup_refuses_a_shared_receipt_before_side_effects(
    fx: Fixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    """S: hardlink された回収記録へ追記すると、ledger の外の利用者ファイルを変更する。"""

    def make(review_id: str, sha: str) -> BatchResult:
        return batch(completed(review_id, sha), work_dir=fx.reviewer)

    summary = external_review(fx, monkeypatch, make)
    review_dir = Path(summary["review_dir"])
    target = fx.tmp / "unrelated.txt"
    target.write_bytes(b"")
    target.chmod(0o640)
    receipt = review_dir / "cleanup.jsonl"
    receipt.hardlink_to(target)
    registered = git(fx.main, "worktree", "list", "--porcelain")
    review_bytes = (review_dir / "review.json").read_bytes()
    request_bytes = (review_dir / "request.json").read_bytes()
    target_bytes = target.read_bytes()
    target_mode = stat.S_IMODE(target.stat().st_mode)
    target_inode = target.stat().st_ino

    with pytest.raises(mod.CleanupInputError) as raised:
        mod.cleanup(review_dir)

    assert any(item["path"] == str(fx.reviewer) for item in raised.value.retained)
    assert any(item["path"] == str(fx.runner) for item in raised.value.retained)
    assert str(receipt) in raised.value.records
    assert str(review_dir / "request.json") in raised.value.records
    assert target.read_bytes() == target_bytes
    assert stat.S_IMODE(target.stat().st_mode) == target_mode
    assert receipt.stat().st_ino == target_inode
    assert receipt.stat().st_nlink == 2
    assert fx.reviewer.is_dir()
    assert fx.runner.is_dir()
    assert git(fx.main, "worktree", "list", "--porcelain") == registered
    assert (review_dir / "review.json").read_bytes() == review_bytes
    assert (review_dir / "request.json").read_bytes() == request_bytes


def test_cleanup_keeps_runner_output_when_a_collection_receipt_cannot_be_written(
    fx: Fixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    """S: 回収の記録に失敗したのに完了扱いすると、再実行で別の対象を消すか証拠を失う。"""

    def make(review_id: str, sha: str) -> BatchResult:
        return batch(completed(review_id, sha), work_dir=fx.reviewer)

    summary = external_review(fx, monkeypatch, make)
    review_dir = Path(summary["review_dir"])

    def broken(review_dir: Path, event: Any) -> None:
        raise mod.ReviewInputError("cannot write")

    monkeypatch.setattr(mod, "_append_cleanup_event", broken)
    cleaned = mod.cleanup(review_dir)

    assert cleaned["removed_worktrees"] == [str(fx.reviewer)]
    assert cleaned["removed_runner_dir"] is False
    assert any(item["path"] == str(fx.reviewer) and "receipt" in item["reason"] for item in cleaned["retained"])
    assert fx.runner.is_dir()
    assert review_dir.is_dir()


def test_cleanup_keeps_the_ledger_when_the_runner_directory_disappears_without_a_record(
    fx: Fixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    """S: 記録なしの runner 領域の消失を回収完了と推測すると、確認できない証拠を片付けたことにする。"""

    def make(review_id: str, sha: str) -> BatchResult:
        return batch(completed(review_id, sha), work_dir=fx.reviewer)

    summary = external_review(fx, monkeypatch, make)
    review_dir = Path(summary["review_dir"])
    shutil.rmtree(fx.runner)

    cleaned = mod.cleanup(review_dir)

    assert cleaned["removed_worktrees"] == [str(fx.reviewer)]
    assert cleaned["removed_runner_dir"] is False
    assert any(item["path"] == str(fx.runner) for item in cleaned["retained"])
    assert review_dir.is_dir()


def success_evidence(
    fx: Fixture, summary: dict[str, Any], *, path: Path | None = None, **overrides: object
) -> tuple[Path, dict[str, Any]]:
    """保存済みレビューと試行に合う成功証拠を組み立てる（安全境界の検査用）。"""
    review_dir = Path(summary["review_dir"])
    target = Path(path or fx.reviewer)
    common_dir = str(Path(git(fx.feature, "rev-parse", "--path-format=absolute", "--git-common-dir")).resolve())
    payload: dict[str, Any] = {
        "version": 1,
        "event": {
            "event": "worktree_removed",
            "review_id": summary["review_id"],
            "kind": "spec-review",
            "spec_sha256": summary["spec_sha256"],
            "run_id": "run-1",
            "runner_dir": str(fx.runner),
            "path": str(target),
            "removed_at": "2026-11-12T00:00:00+00:00",
        },
        "review_sha256": hashlib.sha256((review_dir / "review.json").read_bytes()).hexdigest(),
        "repository": str(fx.feature),
        "common_dir": common_dir,
        "request_id": "request-1",
        "attempt_index": 0,
        "agent_id": "reviewer",
    }
    payload.update(overrides)
    key = hashlib.sha256(f"worktree_removed\n{target}".encode("utf-8")).hexdigest()
    return review_dir / f"cleanup-success-{key}.json", payload


@pytest.mark.parametrize("case", ["wrong-common-dir", "symlink"])
def test_cleanup_rejects_invalid_success_evidence_before_side_effects(
    fx: Fixture, monkeypatch: pytest.MonkeyPatch, case: str
) -> None:
    """S: 別の common-dir や symlink の証拠を信じると、別のレビューの対象を消すか共有ファイルを読む。"""

    def make(review_id: str, sha: str) -> BatchResult:
        return batch(completed(review_id, sha), work_dir=fx.reviewer)

    summary = external_review(fx, monkeypatch, make)
    review_dir = Path(summary["review_dir"])
    evidence_path, payload = success_evidence(fx, summary)
    if case == "wrong-common-dir":
        write_json(evidence_path, {**payload, "common_dir": "/different/common-dir"})
    else:
        target = fx.tmp / "evidence-target.json"
        write_json(target, payload)
        target_bytes = target.read_bytes()
        evidence_path.symlink_to(target)

    with pytest.raises(mod.CleanupInputError) as raised:
        mod.cleanup(review_dir)

    assert any(item["path"] == str(fx.reviewer) for item in raised.value.retained)
    assert any(item["path"] == str(fx.runner) for item in raised.value.retained)
    assert str(evidence_path) in raised.value.records
    assert str(review_dir / "cleanup.jsonl") in raised.value.records
    assert fx.reviewer.is_dir()
    assert fx.runner.is_dir()
    assert not (review_dir / "cleanup.jsonl").exists()
    if case == "symlink":
        assert evidence_path.is_symlink()
        assert target.read_bytes() == target_bytes


def test_cleanup_keeps_an_unrecorded_missing_worktree_with_manual_records(
    fx: Fixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    """S: 成功証拠のない消失を不在だけで回収済みにすると、未確認の変更を失ったことにする。"""

    def make(review_id: str, sha: str) -> BatchResult:
        return batch(completed(review_id, sha), work_dir=fx.reviewer)

    summary = external_review(fx, monkeypatch, make)
    review_dir = Path(summary["review_dir"])
    git(fx.main, "worktree", "remove", "--force", str(fx.reviewer))

    cleaned = mod.cleanup(review_dir)

    assert cleaned["removed_worktrees"] == []
    assert cleaned["removed_runner_dir"] is False
    assert any(item["path"] == str(fx.reviewer) and "missing" in item["reason"] for item in cleaned["retained"])
    assert fx.runner.is_dir()
    records = cleaned["records"]
    for path in (
        review_dir / "request.json",
        review_dir / "review.json",
        review_dir / "cleanup.jsonl",
        fx.runner,
    ):
        assert str(path) in records
    assert len(records) == len(set(records))


def test_cleanup_lock_contention_keeps_targets_and_a_later_run_succeeds(
    fx: Fixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    """S: lock を取れないのに削除すると、同時に動く別の回収と対象を取り違える。"""

    def make(review_id: str, sha: str) -> BatchResult:
        return batch(completed(review_id, sha), work_dir=fx.reviewer)

    summary = external_review(fx, monkeypatch, make)
    review_dir = Path(summary["review_dir"])
    lock_path = review_dir / "cleanup.lock"
    descriptor = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(mod.CleanupInputError) as raised:
            mod.cleanup(review_dir)
        assert any("another cleanup" in str(raised.value) for _ in [0])
        assert any(item["path"] == str(fx.reviewer) for item in raised.value.retained)
        assert any(item["path"] == str(fx.runner) for item in raised.value.retained)
        assert raised.value.records
        assert fx.reviewer.is_dir()
        assert fx.runner.is_dir()
        assert not (review_dir / "cleanup.jsonl").exists()
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)

    cleaned = mod.cleanup(review_dir)

    assert cleaned == {"removed_worktrees": [str(fx.reviewer)], "retained": [], "removed_runner_dir": True}
    assert not fx.reviewer.exists()
    assert not fx.runner.exists()


def test_cleanup_cli_reports_retained_and_records_for_a_precheck_error(
    fx: Fixture, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """S: 事前検査の拒否から照合先を落とすと、利用者が手で回収先を確かめられない。"""

    def make(review_id: str, sha: str) -> BatchResult:
        return batch(completed(review_id, sha), work_dir=fx.reviewer)

    summary = external_review(fx, monkeypatch, make)
    review_dir = Path(summary["review_dir"])
    (review_dir / "cleanup.jsonl").write_text("{not json}\n", encoding="utf-8")

    code = mod.main(["cleanup", "--review-dir", str(review_dir)])
    payload = json.loads(capsys.readouterr().out)

    assert code == 2
    assert payload["status"] == "error"
    assert any(item["path"] == str(fx.reviewer) for item in payload["retained"])
    assert any(item["path"] == str(fx.runner) for item in payload["retained"])
    assert str(review_dir / "request.json") in payload["records"]
    assert str(review_dir / "cleanup.jsonl") in payload["records"]
    assert fx.reviewer.is_dir()
    assert fx.runner.is_dir()


class FakeReviewAdapter:
    """本物の runner を通し、レビューの receipt だけを偽の担当として返す。"""

    capabilities = Capabilities()

    def __init__(self, ledger: Path, *, fail_agents: set[str] | frozenset[str] = frozenset()) -> None:
        self.ledger = ledger
        self.fail_agents = fail_agents

    def __call__(self, runtime: str) -> FakeReviewAdapter:
        return self

    def prepare(self, context: AdapterContext) -> LaunchSpec:
        return LaunchSpec(
            argv=tuple(context.agent.command),
            stdin=context.request.model_dump_json().encode(),
        )

    def collect(
        self, context: AdapterContext, stdout_path: Path, stderr_path: Path
    ) -> AdapterOutcome:
        review_dir = mod._reviews(self.ledger / "design.spec-review")[-1]
        request = json.loads((review_dir / "request.json").read_text(encoding="utf-8"))
        failed = context.request.agent_id in self.fail_agents
        receipt = Receipt(
            schema_version=1,
            run_id=context.request.run_id,
            request_id=context.request.request_id,
            agent_id=context.request.agent_id,
            role=context.request.role,
            status="response_failed" if failed else "success",
            payload=None if failed else completed(request["review_id"], request["spec_sha256"]),
        )
        return AdapterOutcome(receipt, Identity(model=context.agent.model))


def test_cleanup_preserves_targets_until_request_metadata_is_restored(fx: Fixture) -> None:
    """S: 不完全な識別情報で削除すると、証拠が残らず復元後も回収できない。"""
    runner = fx.tmp / "session" / "runner-日本語"
    config = Config(
        agents={
            "reviewer": Agent(
                runtime="pi", command=[sys.executable, "-c", "import sys; sys.stdin.buffer.read()"], model="fake"
            )
        },
        roles={"spec-review": Role(writes=False, deadline_seconds=60.0, result_shape="json")},
        workflows={"issue": Workflow(assignments={"spec-review": Assignment(agents=["reviewer"])})},
    )
    summary = mod.review(
        config, fx.request(), runner, ledger_dir=fx.ledger, adapter_loader=FakeReviewAdapter(fx.ledger)
    )
    assert summary["state"] == "completed", summary["reasons"]
    review_dir = Path(summary["review_dir"])
    request_path = review_dir / "request.json"
    original = request_path.read_bytes()
    request = json.loads(original)
    del request["review_id"]
    write_json(request_path, request)
    record = json.loads((review_dir / "review.json").read_bytes())
    attempts = record["batch"]["results"][0]["attempts"]
    worktrees = [Path(attempt["work_dir"]) for attempt in attempts]
    attempt_requests = [Path(attempt["request_path"]) for attempt in attempts]

    def snapshot(root: Path) -> dict[str, bytes]:
        return {
            str(p.relative_to(root)): p.read_bytes()
            for p in root.rglob("*")
            if p.is_file() and not p.is_symlink()
        }

    before_runner = snapshot(runner)
    before_ledger = snapshot(fx.ledger)
    before_git = git(fx.main, "worktree", "list", "--porcelain")
    before_head = git(fx.feature, "rev-parse", "HEAD")
    before_status = git(fx.feature, "status", "--porcelain")
    before_spec = fx.spec.read_bytes()
    command = [
        "uv", "run", "--project", "/workspaces/reso-world", "--locked", "python",
        str(SCRIPT), "cleanup", "--review-dir", str(review_dir),
    ]
    rejected = subprocess.run(command, capture_output=True, text=True)
    assert rejected.returncode == 2, (rejected.stdout, rejected.stderr)
    payload = json.loads(rejected.stdout)
    assert payload["status"] == "error"
    assert {str(p) for p in [*worktrees, runner]} <= {item["path"] for item in payload["retained"]}
    assert {
        str(p) for p in [request_path, review_dir / "review.json", review_dir / "spec.md", *attempt_requests]
    } <= set(payload["records"])
    assert all(p.is_dir() for p in worktrees)
    assert snapshot(runner) == before_runner
    assert snapshot(fx.ledger) == before_ledger
    assert git(fx.main, "worktree", "list", "--porcelain") == before_git
    assert git(fx.feature, "rev-parse", "HEAD") == before_head
    assert git(fx.feature, "status", "--porcelain") == before_status
    assert fx.spec.read_bytes() == before_spec
    request_path.write_bytes(original)
    recovered = subprocess.run(command, capture_output=True, text=True)
    assert recovered.returncode == 0, (recovered.stdout, recovered.stderr)
    assert json.loads(recovered.stdout) == {
        "removed_worktrees": [str(p) for p in worktrees], "retained": [], "removed_runner_dir": True
    }
    assert all(not p.exists() for p in [*worktrees, runner])
    registered = git(fx.main, "worktree", "list", "--porcelain")
    assert all(str(p) not in registered for p in worktrees)
    noop = subprocess.run(command, capture_output=True, text=True)
    assert noop.returncode == 0, (noop.stdout, noop.stderr)
    assert json.loads(noop.stdout) == {"removed_worktrees": [], "retained": [], "removed_runner_dir": False}


def test_cleanup_rejects_a_completed_review_identity_mismatch(fx: Fixture, monkeypatch: pytest.MonkeyPatch) -> None:
    """S: 別レビューの識別情報で削除証拠を記録しない。"""
    summary = external_review(
        fx, monkeypatch, lambda review_id, sha: batch(completed(review_id, sha), work_dir=fx.reviewer)
    )
    review_dir = Path(summary["review_dir"])
    request_path = review_dir / "request.json"
    original = request_path.read_bytes()
    request = json.loads(original)
    request["review_id"] = "another-review"
    write_json(request_path, request)
    with pytest.raises(mod.CleanupInputError):
        mod.cleanup(review_dir)
    assert fx.reviewer.is_dir() and fx.runner.is_dir()
    assert str(fx.reviewer) in git(fx.main, "worktree", "list", "--porcelain")
    assert not (review_dir / "cleanup.lock").exists()
    request_path.write_bytes(original)
    assert mod.cleanup(review_dir) == {
        "removed_worktrees": [str(fx.reviewer)], "retained": [], "removed_runner_dir": True
    }


def test_cleanup_recovers_a_real_fallback_and_reports_unprocessed_attempts(
    fx: Fixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    """S: 実 runner の複数試行で記録に失敗したとき、後続を消さず、別 CLI の回復で欠落だけを追記する。"""
    runner = fx.tmp / "session" / "runner-一次"
    config = Config(
        agents={
            name: Agent(
                runtime="pi",
                command=[sys.executable, "-c", "import sys; sys.stdin.buffer.read()"],
                model=name,
            )
            for name in ("primary", "reviewer")
        },
        roles={"spec-review": Role(writes=False, deadline_seconds=60.0, result_shape="json")},
        workflows={
            "issue": Workflow(
                assignments={"spec-review": Assignment(agents=["primary"], fallback=["reviewer"])}
            )
        },
    )
    summary = mod.review(
        config,
        fx.request(),
        runner,
        ledger_dir=fx.ledger,
        adapter_loader=FakeReviewAdapter(fx.ledger, fail_agents={"primary"}),
    )
    assert summary["state"] == "completed", summary["reasons"]
    review_dir = Path(summary["review_dir"])
    record = json.loads((review_dir / "review.json").read_text(encoding="utf-8"))
    attempts = record["batch"]["results"][0]["attempts"]
    assert [attempt["agent_id"] for attempt in attempts] == ["primary", "reviewer"]
    assert [attempt["state"] for attempt in attempts] == ["response_failed", "success"]
    first, second = attempts
    first_worktree = Path(first["work_dir"])
    second_worktree = Path(second["work_dir"])
    request_paths = [Path(attempt["request_path"]) for attempt in attempts]
    assert first_worktree.is_dir()
    assert second_worktree.is_dir()
    assert all(path.is_file() for path in request_paths)
    assert all(path.is_relative_to(runner) for path in (first_worktree, second_worktree))

    unrelated = fx.tmp / "unrelated-worktree"
    git(fx.main, "worktree", "add", "--detach", str(unrelated), fx.revision)
    unrelated_head = git(unrelated, "rev-parse", "HEAD")

    def snapshot(root: Path, skip: tuple[Path, ...] = ()) -> dict[str, bytes]:
        return {
            str(path.relative_to(root)): path.read_bytes()
            for path in sorted(root.rglob("*"))
            if path.is_file()
            and not path.is_symlink()
            and not any(path.is_relative_to(item) for item in skip)
        }

    worktrees = (first_worktree, second_worktree)
    runner_before = snapshot(runner, worktrees)
    ledger_before = snapshot(fx.ledger)
    request_bytes = {path: path.read_bytes() for path in request_paths}
    review_bytes = (review_dir / "review.json").read_bytes()
    spec_bytes = fx.spec.read_bytes()
    head = git(fx.feature, "rev-parse", "HEAD")
    status = git(fx.feature, "status", "--porcelain")
    registered_before = git(fx.main, "worktree", "list", "--porcelain")

    receipt = review_dir / "cleanup.jsonl"
    real_write = os.write
    injected = {"done": False}

    def flaky_write(descriptor: int, data: bytes) -> int:
        if not injected["done"]:
            try:
                opened = Path(os.readlink(f"/proc/self/fd/{descriptor}")).resolve(strict=False)
            except OSError:
                opened = None
            if opened == receipt.resolve(strict=False):
                injected["done"] = True
                raise OSError(errno.EIO, "simulated write failure")
        return real_write(descriptor, data)

    monkeypatch.setattr(mod.os, "write", flaky_write)
    interrupted = mod.cleanup(review_dir)

    assert injected["done"]
    assert interrupted["removed_worktrees"] == [str(first_worktree)]
    assert not first_worktree.exists()
    assert second_worktree.is_dir()
    assert runner.is_dir()
    retained = {item["path"]: item["reason"] for item in interrupted["retained"]}
    assert str(first_worktree) in retained
    assert "receipt could not be written" in retained[str(first_worktree)]
    assert str(second_worktree) in retained
    assert "not processed" in retained[str(second_worktree)]
    assert str(runner) in retained
    assert interrupted["removed_runner_dir"] is False
    assert all(str(path) in interrupted["records"] for path in request_paths)
    assert str(runner) in interrupted["records"]
    assert str(receipt) in interrupted["records"]
    assert len(list(review_dir.glob("cleanup-success-*.json"))) == 1

    assert snapshot(runner, worktrees) == runner_before
    assert {path: path.read_bytes() for path in request_paths} == request_bytes
    ledger_after_failure = snapshot(fx.ledger)
    assert {key: ledger_after_failure[key] for key in ledger_after_failure if key in ledger_before} == ledger_before
    assert (review_dir / "review.json").read_bytes() == review_bytes
    assert fx.spec.read_bytes() == spec_bytes
    assert git(fx.feature, "rev-parse", "HEAD") == head
    assert git(fx.feature, "status", "--porcelain") == status
    assert git(unrelated, "rev-parse", "HEAD") == unrelated_head
    assert str(unrelated) in registered_before

    recovered_run = subprocess.run(
        [sys.executable, str(SCRIPT), "cleanup", "--review-dir", str(review_dir)],
        capture_output=True,
        text=True,
    )
    assert recovered_run.returncode == 0, recovered_run.stderr
    assert json.loads(recovered_run.stdout) == {
        "removed_worktrees": [str(second_worktree)],
        "retained": [],
        "removed_runner_dir": True,
    }
    assert not second_worktree.exists()
    assert not runner.exists()
    events = cleanup_events(review_dir)
    assert [event["event"] for event in events] == [
        "worktree_removed",
        "worktree_removed",
        "runner_dir_removed",
    ]
    assert [event["path"] for event in events if event["event"] == "worktree_removed"] == [
        str(first_worktree),
        str(second_worktree),
    ]

    ledger_after_recovery = snapshot(fx.ledger)
    assert {
        key: ledger_after_recovery[key] for key in ledger_after_recovery if key in ledger_before
    } == ledger_before
    assert (review_dir / "review.json").read_bytes() == review_bytes
    assert fx.spec.read_bytes() == spec_bytes
    assert git(fx.feature, "rev-parse", "HEAD") == head
    assert git(fx.feature, "status", "--porcelain") == status
    assert git(unrelated, "rev-parse", "HEAD") == unrelated_head
    assert mod.cleanup(review_dir) == {
        "removed_worktrees": [],
        "retained": [],
        "removed_runner_dir": False,
    }
    registered = git(fx.main, "worktree", "list", "--porcelain")
    assert str(fx.feature) in registered
    assert str(unrelated) in registered
    assert str(first_worktree) not in registered
    assert str(second_worktree) not in registered
