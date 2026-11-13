"""読み取り専用の抽出 CLI が、壊れた metadata でほかの Issue を黙って落とさないことを確かめる。"""

import importlib.util
import io
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "extract_issues.py"
REPO = "usaturn/create-reso-world"


def load_extractor() -> Any:
    spec = importlib.util.spec_from_file_location("extract_issues", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["extract_issues"] = module
    spec.loader.exec_module(module)
    return module


class FakeGh:
    """ページをまたぐ Issue とコメントを返す偽の Runner。"""

    def __init__(self, issues: list[list[dict[str, Any]]], comments: dict[int, list[list[dict[str, Any]]]]) -> None:
        self.issues = issues
        self.comments = comments
        self.calls: list[list[str]] = []

    def __call__(self, args: Any, *, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
        argv = list(args)
        self.calls.append(argv)
        assert argv[:4] == ["gh", "api", "--paginate", "--slurp"], argv
        endpoint = argv[4]
        if endpoint == f"repos/{REPO}/issues?state=all&per_page=100":
            pages = self.issues
        else:
            prefix = f"repos/{REPO}/issues/"
            suffix = "/comments"
            assert endpoint.startswith(prefix) and endpoint.endswith(suffix), endpoint
            number = int(endpoint[len(prefix) : -len(suffix)])
            pages = self.comments[number]
        return subprocess.CompletedProcess(argv, 0, stdout=json.dumps(pages), stderr="")


def issue(number: int, *, body: str | None, **extra: Any) -> dict[str, Any]:
    return {
        "number": number,
        "title": f"Issue {number}",
        "body": body,
        "state": "open",
        "state_reason": None,
        "labels": [{"name": "type: bug"}],
        "html_url": f"https://github.com/{REPO}/issues/{number}",
        **extra,
    }


def comment(number: int, body: str | None, *, association: str = "OWNER", comment_id: int = 1) -> dict[str, Any]:
    return {
        "id": comment_id,
        "body": body,
        "html_url": f"https://github.com/{REPO}/issues/3#issuecomment-{comment_id}",
        "created_at": "2026-01-02T00:00:00Z",
        "author_association": association,
        "issue_url": f"https://api.github.com/repos/{REPO}/issues/{number}",
    }


def test_extract_uses_github_when_environment_selects_another_host(monkeypatch: Any) -> None:
    """別ホストの Issue やコメントを指定 repo の記録として混同しない。"""
    extractor = load_extractor()
    fake = FakeGh([[issue(1, body="first")], [issue(3, body="second")]], {
        1: [[comment(1, "first comment")], [comment(1, "second comment", comment_id=2)]],
        3: [[]],
    })
    other_calls: list[list[str]] = []

    def route(args: Any, *, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
        argv = list(args)
        host = argv[argv.index("--hostname") + 1] if "--hostname" in argv else os.environ["GH_HOST"]
        if host != "github.com":
            other_calls.append(argv)
        return fake(argv, input_text=input_text)

    monkeypatch.setenv("GH_HOST", "other.invalid")
    stdout, stderr = io.StringIO(), io.StringIO()
    code = extractor.run(["--repo", REPO], runner=route, stdout=stdout, stderr=stderr)
    records = [json.loads(line) for line in stdout.getvalue().splitlines()]
    assert code == 0, stderr.getvalue()
    assert [record["number"] for record in records] == [1, 3]
    assert len(fake.calls) == 3
    assert other_calls == []


def test_broken_metadata_is_emitted_without_losing_other_issues() -> None:
    extractor = load_extractor()
    fmt = extractor.fmt
    metadata = fmt.IssueMetadata.model_validate_json(
        json.dumps(
            {
                "filed_on": "2026-01-02",
                "bases": [{"repository": REPO, "branch": "main", "sha": "0" * 40}],
                "estimate": None,
                "baselines": [],
                "targets": [],
                "discovery": {"links": [], "note": None},
                "undetermined": [{"item": "estimate", "reason": "未計測", "how_to_decide": "計測する"}],
            }
        )
    )
    normal = fmt.render_block(metadata)
    run_record = fmt.render_block(
        fmt.RunRecord.model_validate_json(
            json.dumps(
                {
                    "issue": {"repository": REPO, "number": 3},
                    "skill": "issue-authoring",
                    "session": None,
                    "runtime": "test",
                    "model": "test-model",
                    "started_at": "2026-01-02T00:00:00Z",
                    "ended_at": "2026-01-02T00:10:00Z",
                    "outcome": "stopped",
                    "active_minutes": 10,
                    "user_wait_minutes": 0,
                    "tasks": [],
                    "actual_size": "S",
                    "stops": [{"reason": "test", "kind": "expected"}],
                    "resumes": 0,
                    "review_cycles": None,
                    "pr": None,
                }
            )
        )
    )
    evaluation = fmt.render_block(
        fmt.Evaluation.model_validate_json(
            json.dumps(
                {
                    "issue": {"repository": REPO, "number": 3},
                    "evaluated_at": "2026-01-02T00:20:00Z",
                    "runtime": "test",
                    "model": "test-model",
                    "scope": "test",
                    "results": [
                        {
                            "metric": "test",
                            "target": "test",
                            "actual": "test",
                            "achieved": None,
                            "gap": "未計測",
                        }
                    ],
                    "notes": None,
                }
            )
        )
    )
    broken = '本文\n\n<!-- issue-format:metadata:v1\n{"filed_on": \n-->\n'
    issues = [
        [
            issue(2, body=None, pull_request={"url": f"https://api.github.com/repos/{REPO}/pulls/2"}),
            issue(1, body=broken),
        ],
        [issue(5, body="旧書式"), issue(3, body=f"本文\n\n{normal}")],
    ]
    comments: dict[int, list[list[dict[str, Any]]]] = {
        1: [[]],
        3: [
            [comment(3, f"実行記録\n\n{run_record}", comment_id=10)],
            [comment(3, f"評価\n\n{evaluation}", comment_id=11)],
        ],
        5: [[]],
    }
    fake = FakeGh(issues, comments)
    stdout = io.StringIO()
    stderr = io.StringIO()
    code = extractor.run(["--repo", REPO], runner=fake, stdout=stdout, stderr=stderr)

    assert code == 1
    records = [json.loads(line) for line in stdout.getvalue().splitlines()]
    assert [record["number"] for record in records] == [1, 3, 5]
    broken_record = records[0]
    assert broken_record["metadata"]["status"] == "broken"
    assert broken_record["metadata"]["reason"]
    assert "issue #1 metadata:" in stderr.getvalue()
    assert broken_record["metadata"]["reason"] in stderr.getvalue()
    assert records[1]["metadata"]["status"] == "ok"
    assert records[2]["metadata"]["status"] == "missing"
    assert len(records[1]["run_records"]) == 1
    assert len(records[1]["evaluations"]) == 1
    assert all(f"repos/{REPO}/issues/2/comments" not in call[4] for call in fake.calls)
