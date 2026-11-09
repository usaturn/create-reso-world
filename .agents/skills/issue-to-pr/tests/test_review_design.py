"""設計レビュー固有の停止・採否・順序（S: 誤った設計を続行・利用者の判断の取り込み）を確かめる。

共通の保存先・版・停止の検査は test_review_spec.py が代表で確かめる。ここでは設計レビューだけの判断を重複させない。
"""

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
from tools.agent_runner.models import Assignment, Role, Workflow

pytest_plugins = ("tools.test_support.plugin",)
pytestmark = pytest.mark.usefixtures("outside_runner")


@pytest.fixture(autouse=True)
def isolated_git_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in list(os.environ):
        if name.startswith("GIT_"):
            monkeypatch.delenv(name)
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.delenv("SESSION", raising=False)


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "review_design.py"
SPEC = importlib.util.spec_from_file_location("issue_review_design", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
mod: Any = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = mod
SPEC.loader.exec_module(mod)


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


class Fixture:
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
        self.spec_bytes = "# 設計\r\n\r\n複数行の日本語。\r\n".encode()
        self.spec.write_bytes(self.spec_bytes)
        git(self.doc, "add", "-A")
        git(self.doc, "commit", "-qm", "spec")
        self.ledger = tmp_path / "session" / "review-ledger"

    def request(self) -> Any:
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
                "context": "設計レビューは Spec レビューの前。\n",
            }
        )

    def config(self) -> Config:
        return Config(
            roles={"design-review": Role(writes=False, deadline_seconds=60.0, result_shape="json")},
            workflows={"issue": Workflow(assignments={"design-review": Assignment(agents=["self"])})},
        )

    def review(self) -> dict[str, Any]:
        return mod.review(self.config(), self.request(), None, ledger_dir=self.ledger)

    def submitted(self, **result_fields: object) -> tuple[dict[str, Any], Path]:
        summary = self.review()
        payload = {
            "review_id": summary["review_id"],
            "spec_sha256": summary["spec_sha256"],
            "status": "completed",
            "verdict": "sound",
            "assessment": "問題なし",
            "concerns": [],
            "questions_for_user": [],
            "incomplete": [],
            **result_fields,
        }
        path = self.tmp / "result.json"
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        mod.submit(Path(summary["review_dir"]), path)
        return summary, Path(summary["review_dir"])


@pytest.fixture
def fx(tmp_path: Path) -> Fixture:
    return Fixture(tmp_path)


def concern(**overrides: object) -> dict[str, Any]:
    return {
        "id": "D1",
        "decision_ref": "D1",
        "problem": "別案の方が良い",
        "evidence": "Spec の決定記録",
        "alternative": "別案",
        "tradeoffs": "移行の手間",
        "impact": "利用者の操作が変わる",
        "recommendation": "keep",
        "severity": "worth_considering",
        **overrides,
    }


def decide(fx: Fixture, review_dir: Path, decisions: list[dict[str, Any]]) -> dict[str, Any]:
    path = fx.tmp / "decisions.json"
    path.write_text(json.dumps({"decisions": decisions}, ensure_ascii=False), encoding="utf-8")
    return mod.decide(review_dir, path)


def test_sound_design_continues_with_an_empty_decision_set(fx: Fixture) -> None:
    """S: sound な設計を止めると不要な停止が残り、空の採否を書かないと次工程を決められない。"""
    _, review_dir = fx.submitted()

    decided = decide(fx, review_dir, [])

    assert decided["next"] == "continue"
    assert (review_dir / "decisions.json").is_file()
    assert (review_dir / "reflected.md").read_bytes() == fx.spec_bytes


@pytest.mark.parametrize(
    ("result_fields", "decisions", "expected"),
    [
        pytest.param(
            {"verdict": "wrong_approach", "concerns": [concern(recommendation="change")]},
            [{"id": "D1", "decision": "reject", "changes_what_is_built": False, "reason": "採用しない", "reflected_in": None}],
            "wrong_approach",
            id="wrong-approach",
        ),
        pytest.param(
            {"verdict": "concerns", "concerns": [concern(severity="blocking")]},
            [{"id": "D1", "decision": "reject", "changes_what_is_built": False, "reason": "採用しない", "reflected_in": None}],
            "blocking",
            id="blocking",
        ),
        pytest.param(
            {
                "verdict": "concerns",
                "concerns": [concern()],
                "questions_for_user": ["設計を変えるべきか"],
            },
            [{"id": "D1", "decision": "reject", "changes_what_is_built": False, "reason": "採用しない", "reflected_in": None}],
            "questions_for_user",
            id="questions",
        ),
        pytest.param(
            {"verdict": "concerns", "concerns": [concern()]},
            [
                {
                    "id": "D1",
                    "decision": "needs_judgment",
                    "changes_what_is_built": False,
                    "reason": "利用者が決める",
                    "reflected_in": None,
                }
            ],
            "needs_judgment",
            id="needs-judgment",
        ),
    ],
)
def test_design_stops_even_when_every_concern_is_rejected(
    fx: Fixture,
    result_fields: dict[str, object],
    decisions: list[dict[str, Any]],
    expected: str,
) -> None:
    """S: 停止条件を採否で上書きすると、設計の誤り・利用者への問いを無視して Plan へ進む。"""
    _, review_dir = fx.submitted(**result_fields)

    decided = decide(fx, review_dir, decisions)

    assert decided["next"] == "stop"
    assert any(expected in reason for reason in decided["reasons"]), decided["reasons"]
    assert (review_dir / "decisions.json").is_file()


def test_adopting_a_design_change_or_an_ask_user_concern_is_refused(fx: Fixture) -> None:
    """S: 作るものが変わる別案や利用者への問いを adopt 扱いすると、未承認の設計変更が反映済みになる。"""
    _, review_dir = fx.submitted(verdict="concerns", concerns=[concern(recommendation="ask_user")])
    fx.spec.write_bytes(fx.spec_bytes + b"reflected\r\n")

    ask_user = [
        {
            "id": "D1",
            "decision": "adopt",
            "changes_what_is_built": False,
            "reason": "採用する",
            "reflected_in": "設計 3",
        }
    ]
    with pytest.raises(mod.ReviewInputError):
        decide(fx, review_dir, ask_user)
    assert not (review_dir / "decisions.json").exists()
    assert not (review_dir / "reflected.md").exists()

    changes = Fixture(fx.tmp / "changes")
    _, other_dir = changes.submitted(verdict="concerns", concerns=[concern(recommendation="change")])
    changes.spec.write_bytes(changes.spec_bytes + b"reflected\r\n")
    with pytest.raises(mod.ReviewInputError):
        decide(
            changes,
            other_dir,
            [
                {
                    "id": "D1",
                    "decision": "adopt",
                    "changes_what_is_built": True,
                    "reason": "採用する",
                    "reflected_in": "設計 3",
                }
            ],
        )
    assert not (other_dir / "decisions.json").exists()
    assert not (other_dir / "reflected.md").exists()


def test_design_refuses_after_spec_review_started_or_a_second_time(fx: Fixture) -> None:
    """S: 順序を破ると設計レビューが古い Spec を対象にし、2 回目は同じゲートを閉じずに追加の要求を増やす。"""
    spec_review = fx.ledger / "design.spec-review" / "review-1"
    spec_review.mkdir(parents=True)
    with pytest.raises(mod.ReviewInputError):
        fx.review()
    assert not (fx.ledger / "design.design-review").exists()

    spec_review.rmdir()
    spec_review.parent.rmdir()
    summary, review_dir = fx.submitted()
    assert decide(fx, review_dir, [])["next"] == "continue"

    with pytest.raises(mod.ReviewInputError):
        fx.review()
    assert mod.review_spec._reviews(fx.ledger / "design.design-review") == [review_dir]
    assert summary["round"] == 1
