"""review-verify の保存点から review-eval の収集へ記録を渡す（Issue #357）。"""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from tools.review_eval import capture, shim
from tools.review_eval.store import Store
from tools.review_eval.tests.support import write_collection_config

ROOT = Path(__file__).resolve().parents[4]
DISPATCH = ROOT / ".agents/skills/review-verify/scripts/dispatch.py"
FINDINGS = ROOT / ".agents/scripts/review_findings.py"
FINDINGS_TESTS = ROOT / ".agents/scripts/tests/test_review_findings.py"
REPOSITORY = "usaturn/create-reso-world"
PR = 900


def _load(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


dispatch = _load("review_verify_collection_dispatch", DISPATCH)
review_findings = _load("review_verify_collection_findings", FINDINGS)


@pytest.fixture(autouse=True)
def isolated_collection_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """利用者の設定・モデル本文を読まず、runner の子の判定もテストごとに決める。"""
    home = tmp_path / "home"
    home.mkdir()
    xdg = tmp_path / "xdg"
    xdg.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))
    monkeypatch.delenv("AGENT_RUNNER_DEPTH", raising=False)


@pytest.fixture(scope="module")
def findings_helpers() -> Any:
    """有効な v2 文書を組み立てる既存テストの helper を流用する。"""
    return _load("review_verify_collection_findings_helpers", FINDINGS_TESTS)


def review_dir(tmp_path: Path) -> Path:
    directory = tmp_path / "reviews" / REPOSITORY / f"#{PR}-feature-demo"
    directory.mkdir(parents=True)
    return directory


def initialized_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Store:
    store = Store.init(tmp_path / "store")
    config = write_collection_config(
        tmp_path / "review-eval.toml",
        store=store.root,
        workspace_root=tmp_path,
        repos=[REPOSITORY],
    )
    monkeypatch.setenv("REVIEW_EVAL_CONFIG", str(config))
    return store


def observed_paths(store: Store) -> list[str]:
    return [observation.path for observation in store.observations(REPOSITORY, PR)]


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args], check=True, capture_output=True, text=True
    ).stdout.strip()


def commit_all(root: Path, files: dict[str, str], message: str) -> str:
    for name, text in files.items():
        (root / name).write_text(text, encoding="utf-8")
    git(root, "add", "-A")
    git(
        root,
        "-c",
        "user.name=test",
        "-c",
        "user.email=test@example.invalid",
        "commit",
        "-qm",
        message,
    )
    return git(root, "rev-parse", "HEAD")


@dataclass
class Scenario:
    root: Path
    review_dir: Path
    base: str
    fix: str
    request: dict[str, Any]
    inventory: dict[str, Any]
    document: dict[str, Any]

    def payload(self) -> dict[str, Any]:
        return {
            "verified": copy.deepcopy(self.document),
            "inventory": copy.deepcopy(self.inventory),
        }


@pytest.fixture
def scenario(tmp_path: Path, findings_helpers: Any) -> Scenario:
    """道具が候補を 1 件出す実際の Git repository と、有効な v2 fix_check の結果。"""
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-q", "-b", "main")
    base = commit_all(
        root, {"tool.py": "a = 1\n", "README.md": "LIMIT_VALUE を守る\n"}, "base"
    )
    fix = commit_all(root, {"tool.py": "a = LIMIT_VALUE\n"}, "fix")
    h = findings_helpers
    original = h.document_v2("verified")
    original["pr"] = {"repository": REPOSITORY, "number": PR}
    verified = tmp_path / "verified.json"
    verified.write_text(json.dumps(original), encoding="utf-8")
    fix_id = f"claude-opus-5-5#H-1@{base[:12]}"
    claims = {
        "fix_ids": [fix_id],
        "claims": [
            {
                "id": "C-1",
                "fix_id": fix_id,
                "claim": "LIMIT_VALUE を使う",
                "source": "Spec Fix F1",
                "kind": "static",
            }
        ],
    }
    inventory = h.review_findings.statement_candidates(
        root, base, fix, generated_at="2026-10-08T00:00:00Z", claims=claims
    )
    assert [c["path"] for c in inventory["candidates"]] == ["README.md:1"]

    document = h.document_v2("verified")
    document["pr"] = {"repository": REPOSITORY, "number": PR}
    shape = h.fix_check()
    for key in (
        "mode",
        "reviewed_head",
        "fix_check",
        "findings",
        "statement_candidates",
    ):
        document[key] = shape[key]
    # 既存 helper の固定値を、実際の repository の値へ置き換える。
    text = json.dumps(document)
    for old, new in ((h.HEAD, base), (h.FIX, fix)):
        text = text.replace(old, new)
    document = json.loads(text)
    document["fix_check"]["fix_ids"] = [fix_id]
    document["statement_candidates"] = {
        "file": f"{fix[:12]}.statement-candidates.json",
        "judgments": [{"ids": ["S-1"], "result": "unrelated", "basis": "別の説明"}],
    }
    document["findings"][0]["statement_sites"] = []
    check = {
        "command": "git show HEAD:tool.py",
        "head": fix,
        "mode": "executed",
        "exit_code": 0,
        "result": "LIMIT_VALUE を使う",
        "artifact": "tool.py",
    }
    document["fix_evidence"] = {
        "claims": [
            {
                "id": "C-1",
                "result": "holds",
                "basis": "読んだ",
                "checks": [check],
                "findings": [],
            }
        ],
        "files": [
            {
                "path": "tool.py",
                "result": "passed",
                "rule": "AGENTS.md: lint",
                "basis": "lint 実行",
                "checks": [check],
                "findings": [],
            }
        ],
    }
    h.review_findings.validate_document(document)
    h.review_findings.check_statement_judgments(document, inventory)
    directory = review_dir(tmp_path)
    request = {
        "repository": str(root),
        "from": base,
        "to": fix,
        "fix_ids": [fix_id],
        "fix_sections": "F1: LIMIT_VALUE を使う。",
        "verified_file": str(verified),
        "review_dir": str(directory),
    }
    return Scenario(root, directory, base, fix, request, inventory, document)


def write_dispatch(scenario: Scenario, run_dir: Path) -> Path:
    """accept が読む、`unprotected_changes` を持たない古い形の dispatch.json を置く。"""
    skill = {
        "path": ".agents/skills/review-verify/SKILL.md",
        "sha256": hashlib.sha256(dispatch.SKILL.read_bytes()).hexdigest(),
    }
    verifier = copy.deepcopy(scenario.document["verifier"])
    verifier["provenance"]["skills"] = [skill]
    payload = scenario.payload()
    payload["verified"]["skill"] = skill
    saved = {
        "batch": {
            "state": "success",
            "results": [{"attempts": [{"stop_confirmed": True, "payload": payload}]}],
            "checkout_audit": [],
            "outside_changes": [],
        },
        "request": scenario.request,
        "verified": json.loads(
            Path(scenario.request["verified_file"]).read_text(encoding="utf-8")
        ),
        "skill": skill,
        "verifier": verifier,
        "review_snapshot": dispatch.snapshot_review(scenario.review_dir),
        "review_changes": [],
    }
    run_dir.mkdir()
    path = run_dir / "dispatch.json"
    path.write_text(json.dumps(saved, ensure_ascii=False), encoding="utf-8")
    return run_dir


def accept(run_dir: Path) -> int:
    return int(dispatch.main(["accept", "--run-dir", str(run_dir)]))


def test_accept_copies_fix_check_when_enabled(
    scenario: Scenario, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = initialized_store(tmp_path, monkeypatch)
    run_dir = write_dispatch(scenario, tmp_path / "run")

    assert accept(run_dir) == 0

    stem = scenario.fix[:12]
    assert set(observed_paths(store)) == {
        f"verified/{stem}.fix-check.json",
        f"verified/{stem}.statement-candidates.json",
    }


def test_accept_disabled_output_unchanged(
    scenario: Scenario,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    store = initialized_store(tmp_path, monkeypatch)
    run_dir = write_dispatch(scenario, tmp_path / "run")
    monkeypatch.setenv("REVIEW_EVAL_CONFIG", "")

    first_code = accept(run_dir)
    first_output = capsys.readouterr().out
    # 同じ dispatch.json のまま、収集だけが例外になる実行と比べる。
    (scenario.review_dir / "verified").rename(tmp_path / "verified-after-first")

    def broken_collect(**_kwargs: Any) -> None:
        raise RuntimeError("収集に失敗した")

    monkeypatch.setattr(capture, "collect", broken_collect)
    second_code = accept(run_dir)
    second_output = capsys.readouterr().out

    assert (first_code, first_output) == (second_code, second_output)
    assert first_code == 0
    assert observed_paths(store) == []


def test_validate_hooks_absolute_review_dir(
    findings_helpers: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    directory = review_dir(tmp_path) / "verified"
    directory.mkdir()
    document = findings_helpers.document_v2("planning")
    document["pr"] = {"repository": REPOSITORY, "number": PR}
    inside = directory / "abcdef123456.planning.json"
    inside.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
    outside = tmp_path / "planning.json"
    outside.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
    invalid = directory / "fedcba654321.planning.json"
    invalid.write_text('{"schema": "unknown"}', encoding="utf-8")
    calls: list[dict[str, Any]] = []

    def fake_run_hook(**kwargs: Any) -> None:
        calls.append(kwargs)

    monkeypatch.setattr(shim, "run_hook", fake_run_hook)
    monkeypatch.chdir(tmp_path)

    assert review_findings.main(["validate", str(inside.relative_to(tmp_path))]) == 0
    assert len(calls) == 1
    assert calls[0]["route"] == "review-verify"
    assert calls[0]["event"] == "validate"
    assert calls[0]["review_dir"] == inside.parent.parent
    assert calls[0]["tool_root"] == ROOT
    assert calls[0]["review_dir"].is_absolute()
    assert calls[0]["tool_root"].is_absolute()

    assert review_findings.main(["validate", str(outside.relative_to(tmp_path))]) == 0
    assert len(calls) == 1
    assert review_findings.main(["validate", str(invalid.relative_to(tmp_path))]) == 65
    assert len(calls) == 1


def test_accept_calls_collect(
    scenario: Scenario, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_dir = write_dispatch(scenario, tmp_path / "run")
    calls: list[dict[str, Any]] = []

    def fake_collect(**kwargs: Any) -> None:
        calls.append(kwargs)

    monkeypatch.setattr(capture, "collect", fake_collect)

    assert accept(run_dir) == 0
    assert len(calls) == 1
    assert calls[0]["route"] == "review-verify"
    assert calls[0]["event"] == "accept"
    assert calls[0]["review_dir"] == scenario.review_dir
