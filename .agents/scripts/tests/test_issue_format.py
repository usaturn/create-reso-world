"""誤対象、metadata の欠落と壊れたブロックの成功扱いを防ぐ。"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "issue_format.py"
SPEC = importlib.util.spec_from_file_location("issue_format", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
fmt = importlib.util.module_from_spec(SPEC)
sys.modules["issue_format"] = fmt
SPEC.loader.exec_module(fmt)


def _git(root: Path, *args: str) -> None:
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, env=env)


def _checkout(path: Path, remote: str) -> None:
    path.mkdir(parents=True)
    _git(path, "init", "-q")
    _git(path, "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "--allow-empty", "-qm", "initial")
    _git(path, "remote", "add", "origin", f"https://github.com/{remote}.git")


def test_repository_resolution_rejects_unregistered_without_selecting_another_target() -> None:
    # 別 repo の書式として誤って成功しない。実際の親と resolver を使う。
    rules = fmt.load_rules("USATURN/Create-Reso-World")
    assert rules.repository == "usaturn/create-reso-world"
    with pytest.raises(fmt.FormatError):
        fmt.load_rules("example-owner/unregistered")


def test_meshy_only_accepts_fixed_permanent_checkout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # 別 checkout や別 origin への書込みを防ぐ。Git と共通 resolver は実物を通す。
    parent = tmp_path / "parent"
    _checkout(parent, "usaturn/create-reso-world")
    fixed = parent / "external" / "resoloop-meshy"
    _checkout(fixed, "usaturn/resoloop-meshy")
    monkeypatch.setattr(fmt.agent_tmp, "resolve_main_root", lambda anchor: parent)
    assert fmt.load_rules("Usaturn/ResoLoop-Meshy").repository == "usaturn/resoloop-meshy"
    _git(fixed, "remote", "set-url", "origin", "https://github.com/example-owner/other.git")
    with pytest.raises(fmt.FormatError):
        fmt.load_rules("usaturn/resoloop-meshy")
    _git(fixed, "remote", "set-url", "origin", "https://github.com/usaturn/resoloop-meshy.git")
    other = tmp_path / "other"
    _checkout(other, "usaturn/resoloop-meshy")
    moved = parent / "external" / "original"
    fixed.rename(moved)
    fixed.symlink_to(other, target_is_directory=True)
    with pytest.raises(fmt.FormatError):
        fmt.load_rules("usaturn/resoloop-meshy")


def test_write_metadata_round_trips_text_that_would_close_the_comment() -> None:
    tricky = "1 行目\n`<!-- 例 -->` と --> と --!> を含む\n```python\nprint('<b>日本語</b>')\n```\n最後"
    metadata = fmt.IssueMetadata.model_validate_json(
        json.dumps(
            {
                "filed_on": "2026-11-09",
                "bases": [{"repository": "example-owner/example-repo", "branch": "main", "sha": "0" * 40}],
                "estimate": {"hours_low": 1, "hours_high": 2, "confidence": "low", "uncertainties": [tricky]},
                "baselines": [],
                "targets": [],
                "discovery": {"links": [], "note": tricky},
            }
        )
    )
    original = "## 概要\r\n\r\n本文。\r\n```\r\n<!-- 例 -->\r\n```\r\n"
    written = fmt.write_metadata(original, metadata)
    assert written.startswith(original)

    extracted = fmt.extract_block(written, "metadata")
    assert extracted.status == "ok"
    assert extracted.value == metadata
    assert extracted.line is not None and extracted.end_line is not None
    lines = written.split("\n")
    start = sum(len(line) + 1 for line in lines[: extracted.line - 1])
    first_close = written.index("-->", start)
    # ブロックの 1 行目から最初に出る --> が、ブロックの最後の行（-->）であること
    assert written.count("\n", 0, first_close) + 1 == extracted.end_line
    assert written[first_close:].strip() == "-->"


def test_check_issue_does_not_pass_a_block_closed_inside_its_json() -> None:
    rules = fmt.load_rules("usaturn/create-reso-world")
    sections = "\n\n".join(
        f"## {rule.heading}\n\n該当なし（このテストでは指標を扱わない）" for rule in rules.sections if rule.required
    )
    labels = [next(label.name for label in rules.labels if label.family == family) for family in fmt.REQUIRED_FAMILIES]
    metadata = fmt.IssueMetadata.model_validate_json(
        json.dumps(
            {
                "filed_on": "2026-11-09",
                "bases": [{"repository": "usaturn/create-reso-world", "branch": "main", "sha": "0" * 40}],
                "estimate": {"hours_low": 1, "hours_high": 2, "confidence": "high", "uncertainties": []},
                "baselines": [],
                "targets": [],
                "discovery": {"links": [], "note": "メモ"},
            }
        )
    )
    body = fmt.write_metadata(sections, metadata)
    assert fmt.check_issue(body, labels, rules).complete  # 前提: 書式に合う本文は通る

    broken = body.replace('"メモ"', '"メモ -->"')  # 手で編集して、コメントが JSON の途中で閉じた
    result = fmt.check_issue(broken, labels, rules)
    assert not result.complete
    assert result.metadata.status == "broken"
    assert "block_broken" in {problem.code for problem in result.problems}


def test_check_issue_does_not_drop_targets_from_a_populated_section() -> None:
    rules = fmt.load_rules("usaturn/create-reso-world")
    target_rule = next(rule for rule in rules.sections if rule.metadata_key == "targets")
    labels = [next(label.name for label in rules.labels if label.family == family) for family in fmt.REQUIRED_FAMILIES]
    metadata = fmt.IssueMetadata.model_validate_json(
        json.dumps(
            {
                "filed_on": "2026-11-09",
                "bases": [{"repository": "usaturn/create-reso-world", "branch": "main", "sha": "0" * 40}],
                "estimate": {"hours_low": 1, "hours_high": 2, "confidence": "high", "uncertainties": []},
                "baselines": [],
                "targets": [],
                "discovery": {"links": [], "note": "メモ"},
            }
        )
    )

    def body_with(target_section: str) -> str:
        sections = "\n\n".join(
            f"## {rule.heading}\n\n"
            + (target_section if rule == target_rule else "該当なし（このテストでは扱わない）")
            for rule in rules.sections
            if rule.required
        )
        return fmt.write_metadata(sections, metadata)

    populated = body_with("| 指標 | 目標 |\n|---|---|\n| 手作業の時間 | 3 分以内 |")
    result = fmt.check_issue(populated, labels, rules)
    assert not result.complete
    assert any(
        problem.code == "section_metadata_empty" and problem.where == f"section:{target_rule.heading}"
        for problem in result.problems
    )

    referenced = body_with(f"親 #9001 の「{target_rule.heading}」を参照する。この子に固有の指標は無い")
    assert fmt.check_issue(referenced, labels, rules).complete
