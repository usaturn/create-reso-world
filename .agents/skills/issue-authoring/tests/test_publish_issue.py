"""publish_issue.py が、取り消せない投稿の前に止まるガード。

実在の GitHub・Gitleaks・ネットワークは使わない。`gh` は偽の Runner、Gitleaks は `tmp_path` に書いた偽のスクリプト。
テストを実行する環境の変数に結果が左右されないよう、非対話の判定に使う環境は `publish` の引数で渡す。
"""

import copy
import hashlib
import importlib.util
import json
import os
import shlex
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "publish_issue.py"
REPO = "usaturn/create-reso-world"
ISSUE = 871
FAKE_VERSION = "0.0.0-test"

# 偽の Gitleaks 本体。検出される形の文字列をソースに書かないよう、見本の目印は実行時に連結して作る
FAKE_GITLEAKS = """
import json
import os
import sys
from pathlib import Path

assert "GITLEAKS_CONFIG" not in os.environ
assert "GITLEAKS_CONFIG_TOML" not in os.environ
args = sys.argv[1:]
if args[:1] == ["version"]:
    print({version!r})
    raise SystemExit(0)
assert "--redact" in args and "--ignore-gitleaks-allow" in args
source = Path(args[1])
report = Path(args[args.index("--report-path") + 1])
silent = {silent!r}
marker = "gh" + "p_"
items = []
if not silent:
    for path in sorted(source.iterdir()):
        if marker in path.read_text(encoding="utf-8"):
            items.append({{"File": str(path.resolve()), "RuleID": "github-pat", "StartLine": 1}})
report.write_text(json.dumps(items), encoding="utf-8")
raise SystemExit(0 if silent else 99)
"""


@pytest.fixture(scope="module")
def pub() -> Any:
    spec = importlib.util.spec_from_file_location("publish_issue", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["publish_issue"] = module
    spec.loader.exec_module(module)
    return module


def fake_gitleaks(pub: Any, directory: Path, *, silent: bool) -> Any:
    """`silent=True` は、見本（canary）を検出せず終了コード 0 で空のレポートを書く偽の Gitleaks。"""
    directory.mkdir(parents=True)
    body = directory / "gitleaks_body.py"
    body.write_text(FAKE_GITLEAKS.format(version=FAKE_VERSION, silent=silent), encoding="utf-8")
    # スキャナーの作業ディレクトリからでも、ルートの lock 済み環境で実行する。
    wrapper = directory / "gitleaks"
    root = Path(__file__).resolve().parents[4]
    wrapper.write_text(
        f'#!/bin/sh\nexec uv run --project {shlex.quote(str(root))} --locked python {shlex.quote(str(body))} "$@"\n',
        encoding="utf-8",
    )
    wrapper.chmod(0o755)
    pin = directory / "install-gitleaks.bash"
    pin.write_text(f'readonly GITLEAKS_VERSION="{FAKE_VERSION}"\n', encoding="utf-8")
    return pub.Scanner(binary=str(wrapper), pin_file=pin)


def issue_json(number: int, *, title: str, body: str | None, labels: Sequence[str] = ()) -> dict[str, Any]:
    return {
        "number": number,
        "id": 900000 + number,
        "title": title,
        "body": body,
        "labels": [{"name": name} for name in labels],
        "updated_at": "2026-11-09T00:00:00Z",
        "html_url": f"https://github.com/{REPO}/issues/{number}",
    }


class FakeGh:
    """`gh api` の呼び出しに答える偽の Runner。書き込み（`GET` 以外）の呼び出しも `calls` に残す。"""

    def __init__(self) -> None:
        self.issues: dict[tuple[str, int], dict[str, Any]] = {}
        self.labels: dict[str, list[str]] = {}
        self.fail_posts_to: set[str] = set()
        self.calls: list[list[str]] = []
        self.write_payloads: list[dict[str, Any]] = []

    def __call__(self, args: Sequence[str], *, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
        argv = list(args)
        self.calls.append(argv)
        assert argv[:3] == ["gh", "api", "--method"], argv
        method = argv[3]
        endpoint = next(arg for arg in argv[4:] if arg.startswith("repos/"))
        parts = endpoint.split("/")
        repo = f"{parts[1]}/{parts[2]}"
        tail = parts[3:]
        if method != "GET":
            if endpoint in self.fail_posts_to:
                return self._reply(argv, 1, "", "gh: Bad Gateway (HTTP 502)")
            return self._write(argv, method, repo, tail, input_text)
        if tail == ["labels"]:
            return self._reply(argv, 0, "\n".join(self.labels.get(repo, [])))
        if len(tail) == 2 and tail[0] == "issues":
            issue = self.issues.get((repo, int(tail[1])))
            if issue is None:
                return self._reply(argv, 1, '{"message": "Not Found"}', "gh: Not Found (HTTP 404)")
            return self._reply(argv, 0, json.dumps(issue))
        if tail[2:] == ["parent"]:
            return self._reply(argv, 1, '{"message": "No parent issue found"}', "gh: Not Found (HTTP 404)")
        if tail[2:] == ["dependencies", "blocked_by"]:
            return self._reply(argv, 0, "")
        return self._reply(argv, 1, "", f"unexpected gh args: {argv}")

    def _write(
        self, argv: list[str], method: str, repo: str, tail: list[str], input_text: str | None
    ) -> subprocess.CompletedProcess[str]:
        payload: dict[str, Any] = json.loads(input_text) if input_text else {}
        self.write_payloads.append(payload)
        if tail[0] == "issues" and tail[2:] == ["comments"]:
            number = int(tail[1])
            url = f"https://github.com/{repo}/issues/{number}#issuecomment-1"
            return self._reply(argv, 0, json.dumps({"id": 1, "html_url": url}))
        if method == "PATCH" and tail[0] == "issues" and len(tail) == 2:
            issue = self.issues[(repo, int(tail[1]))]
            issue.update(payload)
            return self._reply(argv, 0, json.dumps(issue))
        if tail[0] == "issues" and len(tail) >= 3 and tail[2] == "labels":
            issue = self.issues[(repo, int(tail[1]))]
            names = [label["name"] for label in issue["labels"]]
            if method == "POST" and len(tail) == 3:
                names.extend(name for name in payload["labels"] if name.casefold() not in {n.casefold() for n in names})
            elif method == "DELETE" and len(tail) == 4:
                names = [name for name in names if name.casefold() != unquote(tail[3]).casefold()]
            else:
                raise AssertionError(argv)
            issue["labels"] = [{"name": name} for name in names]
        return self._reply(argv, 0, "{}")

    @staticmethod
    def _reply(argv: list[str], code: int, stdout: str, stderr: str = "") -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(argv, code, stdout, stderr)

    def writes(self) -> list[list[str]]:
        return [call for call in self.calls if call[3] != "GET"]

    def writes_to(self, method: str, suffix: str) -> list[list[str]]:
        return [call for call in self.writes() if call[3] == method and call[4].endswith(suffix)]


def saved_comment(pub: Any, tmp_path: Path, fake: FakeGh) -> tuple[Path, str]:
    """動く偽の Gitleaks で `comment` の案を保存し、案のディレクトリと承認する `sha256` を返す。"""
    fake.issues[(REPO, ISSUE)] = issue_json(ISSUE, title="対象の Issue", body="本文")
    out_dir = tmp_path / "draft"
    out_dir.mkdir()
    saved = pub.draft_comment(
        repo=REPO,
        issue=ISSUE,
        body="評価の結果を記録する。",
        out_dir=out_dir,
        runner=fake,
        scanner=fake_gitleaks(pub, tmp_path / "working-scanner", silent=False),
    )
    assert saved["status"] == "draft_saved"
    return out_dir, saved["sha256"]


def conforming_update(pub: Any) -> tuple[list[str], str]:
    """登録規則を満たす、必須の 5 系統のラベルと、必須の節・機械可読ブロックを持つ本文。"""
    fmt = pub.fmt
    rules = fmt.load_rules(REPO)
    labels = [next(label.name for label in rules.labels if label.family == family) for family in fmt.REQUIRED_FAMILIES]
    sections = "\n".join(
        f"## {rule.heading}\n\n該当なし（このテストでは指標を扱わない）\n" for rule in rules.sections if rule.required
    )
    metadata = fmt.IssueMetadata.model_validate_json(
        json.dumps(
            {
                "filed_on": "2026-11-09",
                "bases": [{"repository": REPO, "branch": "main", "sha": "0" * 40}],
                "estimate": {"hours_low": 1, "hours_high": 2, "confidence": "high", "uncertainties": []},
                "baselines": [],
                "targets": [],
                "discovery": {"links": [], "note": "メモ"},
            }
        )
    )
    return labels, fmt.write_metadata(sections, metadata)


def test_publish_stops_when_scanner_finds_nothing(pub: Any, tmp_path: Path) -> None:
    fake = FakeGh()
    out_dir, sha256 = saved_comment(pub, tmp_path, fake)

    result = pub.publish(
        draft_dir=out_dir,
        sha256=sha256,
        runner=fake,
        scanner=fake_gitleaks(pub, tmp_path / "silent-scanner", silent=True),
        env={},
    )

    assert result["status"] == "scan_failed"
    assert fake.writes() == []


def test_publish_does_not_overwrite_body_changed_after_reading(pub: Any, tmp_path: Path) -> None:
    fake = FakeGh()
    labels, new_body = conforming_update(pub)
    fake.labels[REPO] = list(labels)
    fake.issues[(REPO, ISSUE)] = issue_json(ISSUE, title="対象の Issue", body="古い本文", labels=labels)
    out_dir = tmp_path / "draft"
    out_dir.mkdir()
    scanner = fake_gitleaks(pub, tmp_path / "working-scanner", silent=False)
    saved = pub.draft_update(
        repo=REPO,
        issue=ISSUE,
        read_json=json.loads(json.dumps(fake.issues[(REPO, ISSUE)])),
        body=new_body,
        metadata=None,
        title=None,
        add_labels=[],
        remove_labels=[],
        out_dir=out_dir,
        runner=fake,
        scanner=scanner,
    )
    assert saved["status"] == "draft_saved"

    fake.issues[(REPO, ISSUE)]["body"] = "別のセッションが書いた本文"
    result = pub.publish(draft_dir=out_dir, sha256=saved["sha256"], runner=fake, scanner=scanner, env={})

    assert result["status"] == "conflict"
    assert fake.writes() == []


def test_update_resume_rejects_changed_body_and_allows_partial_labels(pub: Any, tmp_path: Path) -> None:
    """途中公開後の外部編集で誤成功・追加書込みしない一方、正当な途中状態は再開できる。"""
    fake = FakeGh()
    labels, body = conforming_update(pub)
    old_label = next(label.name for label in pub.fmt.load_rules(REPO).labels if label.family == "triage")
    initial_labels = labels[1:] + [old_label]
    fake.labels[REPO] = labels + [old_label]
    fake.issues[(REPO, ISSUE)] = issue_json(ISSUE, title="対象の Issue", body="古い本文", labels=initial_labels)
    out_dir = tmp_path / "draft"
    out_dir.mkdir()
    scanner = fake_gitleaks(pub, tmp_path / "working-scanner", silent=False)
    saved = pub.draft_update(
        repo=REPO, issue=ISSUE, read_json=copy.deepcopy(fake.issues[(REPO, ISSUE)]),
        body=body, metadata=None, title=None, add_labels=[labels[0]], remove_labels=[old_label],
        out_dir=out_dir, runner=fake, scanner=scanner,
    )
    assert saved["status"] == "draft_saved"
    endpoint = f"repos/{REPO}/issues/{ISSUE}/labels"
    fake.fail_posts_to.add(endpoint)
    result = pub.publish(draft_dir=out_dir, sha256=saved["sha256"], runner=fake, scanner=scanner, env={})
    assert result["step"] == "add_labels"
    assert fake.issues[(REPO, ISSUE)]["body"] == body

    fake.fail_posts_to.clear()
    fake.issues[(REPO, ISSUE)]["body"] = "別のセッションが書いた本文"
    remote_before = copy.deepcopy((fake.issues, fake.labels))
    files_before = {p.name: (p.read_bytes(), p.stat().st_mode) for p in out_dir.iterdir()}
    writes_before = list(fake.writes())
    result = pub.publish(draft_dir=out_dir, sha256=saved["sha256"], runner=fake, scanner=scanner, env={})
    assert result["status"] == "conflict"
    assert (fake.issues, fake.labels) == remote_before
    assert fake.writes() == writes_before
    assert {p.name: (p.read_bytes(), p.stat().st_mode) for p in out_dir.iterdir()} == files_before

    fake.issues[(REPO, ISSUE)]["body"] = body
    remove_endpoint = f"{endpoint}/{quote(old_label, safe='')}"
    fake.fail_posts_to.add(remove_endpoint)
    result = pub.publish(draft_dir=out_dir, sha256=saved["sha256"], runner=fake, scanner=scanner, env={})
    assert result["step"] == f"remove_label:{old_label}"
    assert labels[0] in [label["name"] for label in fake.issues[(REPO, ISSUE)]["labels"]]
    fake.fail_posts_to.clear()
    writes_before = len(fake.writes())
    result = pub.publish(draft_dir=out_dir, sha256=saved["sha256"], runner=fake, scanner=scanner, env={})
    assert result["status"] == "published"
    assert [call[3] for call in fake.writes()[writes_before:]] == ["DELETE"]
    assert {label["name"] for label in fake.issues[(REPO, ISSUE)]["labels"]} == set(labels)


def test_publish_refuses_non_interactive_run(pub: Any, tmp_path: Path) -> None:
    fake = FakeGh()
    out_dir, sha256 = saved_comment(pub, tmp_path, fake)

    result = pub.publish(
        draft_dir=out_dir,
        sha256=sha256,
        runner=fake,
        scanner=fake_gitleaks(pub, tmp_path / "second-scanner", silent=False),
        env={"CLAUDE_CODE_SESSION_ATTENDED": "0"},
    )

    assert result["status"] == "non_interactive"
    assert fake.writes() == []


def test_publish_refuses_draft_changed_after_approval(pub: Any, tmp_path: Path) -> None:
    fake = FakeGh()
    out_dir, sha256 = saved_comment(pub, tmp_path, fake)
    draft_path = out_dir / "draft.json"
    draft = json.loads(draft_path.read_text(encoding="utf-8"))
    draft["body"] = "承認していない本文"
    draft_path.write_text(json.dumps(draft, ensure_ascii=False, indent=2), encoding="utf-8")

    result = pub.publish(
        draft_dir=out_dir,
        sha256=sha256,
        runner=fake,
        scanner=fake_gitleaks(pub, tmp_path / "second-scanner", silent=False),
        env={},
    )

    assert result["status"] == "draft_changed"
    assert fake.writes() == []


def test_publish_scans_approved_secret_and_writes_nothing(pub: Any, tmp_path: Path) -> None:
    """承認済みでも秘密を送信すると漏洩するため、投稿直前に再検出して止める。"""
    fake = FakeGh()
    out_dir, _ = saved_comment(pub, tmp_path, fake)
    draft_path = out_dir / "draft.json"
    draft = json.loads(draft_path.read_text(encoding="utf-8"))
    secret = "gh" + "p_" + "x" * 36
    draft["body"] = "誤って含まれた値: " + secret
    raw = json.dumps(draft, ensure_ascii=False).encode()
    draft_path.write_bytes(raw)
    result = pub.publish(
        draft_dir=out_dir, sha256=hashlib.sha256(raw).hexdigest(), runner=fake,
        scanner=fake_gitleaks(pub, tmp_path / "second-scanner", silent=False), env={},
    )
    assert result["status"] == "secret_detected"
    assert secret not in json.dumps(result)
    assert fake.writes() == []


def test_publish_approved_comment_once_without_changing_draft(
    pub: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """外部設定で検査を無効化せず、承認内容を一度だけ送って記録の重複を防ぐ。"""
    monkeypatch.setenv("GITLEAKS_CONFIG", "untrusted-config")
    monkeypatch.setenv("GITLEAKS_CONFIG_TOML", "untrusted-config")
    fake = FakeGh()
    out_dir, sha256 = saved_comment(pub, tmp_path, fake)
    raw = (out_dir / "draft.json").read_bytes()
    scanner = fake_gitleaks(pub, tmp_path / "second-scanner", silent=False)
    first = pub.publish(draft_dir=out_dir, sha256=sha256, runner=fake, scanner=scanner, env={})
    second = pub.publish(draft_dir=out_dir, sha256=sha256, runner=fake, scanner=scanner, env={})
    assert first["status"] == "published"
    assert second["status"] == "already_published"
    assert (out_dir / "draft.json").read_bytes() == raw
    assert len(fake.writes_to("POST", "/comments")) == 1
    assert fake.write_payloads == [{"body": "評価の結果を記録する。"}]


def test_host_change_after_draft_does_not_send_to_other_host(
    pub: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """別ホストへの誤投稿と成功記録を防ぐ。draft 後の環境変更も検査する。"""
    fake = FakeGh()
    other_calls: list[list[str]] = []

    def route(args: Sequence[str], *, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
        argv = list(args)
        host = argv[argv.index("--hostname") + 1] if "--hostname" in argv else os.environ["GH_HOST"]
        if host != "github.com":
            other_calls.append(argv)
        return fake(argv, input_text=input_text)

    monkeypatch.setenv("GH_HOST", "draft.invalid")
    fake.issues[(REPO, ISSUE)] = issue_json(ISSUE, title="対象の Issue", body="本文")
    out_dir = tmp_path / "draft"
    out_dir.mkdir()
    saved = pub.draft_comment(
        repo=REPO, issue=ISSUE, body="評価の結果を記録する。", out_dir=out_dir, runner=route,
        scanner=fake_gitleaks(pub, tmp_path / "draft-scanner", silent=False),
    )
    assert saved["status"] == "draft_saved"
    sha256 = saved["sha256"]
    monkeypatch.setenv("GH_HOST", "other.invalid")
    result = pub.publish(
        draft_dir=out_dir, sha256=sha256, runner=route,
        scanner=fake_gitleaks(pub, tmp_path / "publish-scanner", silent=False), env={},
    )
    assert result["status"] == "published"
    assert len(fake.writes_to("POST", "/comments")) == 1
    assert other_calls == []


def test_publish_does_not_resend_comment_after_lost_response(pub: Any, tmp_path: Path) -> None:
    fake = FakeGh()
    out_dir, sha256 = saved_comment(pub, tmp_path, fake)
    scanner = fake_gitleaks(pub, tmp_path / "second-scanner", silent=False)
    fake.fail_posts_to.add(f"repos/{REPO}/issues/{ISSUE}/comments")

    first = pub.publish(draft_dir=out_dir, sha256=sha256, runner=fake, scanner=scanner, env={})
    fake.fail_posts_to.clear()
    second = pub.publish(draft_dir=out_dir, sha256=sha256, runner=fake, scanner=scanner, env={})

    assert first["status"] == "gh_failed"
    assert second["status"] == "uncertain"
    assert len(fake.writes_to("POST", "/comments")) == 1
