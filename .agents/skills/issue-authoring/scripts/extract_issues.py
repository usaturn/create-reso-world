#!/usr/bin/env python3
"""登録済みリポジトリの Issue とコメントを読み、機械可読ブロックを JSONL で出す。

``gh api`` の GET だけを使い、clone は読まない。全ページを取得してから、1 Issue を 1 行の JSON にする。
Issue 番号の昇順で、本文の metadata・実行記録・評価の抽出結果と、共有の書式による検査結果を出す。
壊れたブロックや未知の版があってもほかの Issue を落とさず、終了コード 1 で知らせる。取得・入力の失敗は
終了コード 2 で、標準出力には何も書かない。
"""

import argparse
import importlib.util
import json
import subprocess
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, TextIO, cast

ROOT = Path(__file__).resolve().parents[4]
FORMAT_MODULE = ROOT / ".agents/scripts/issue_format.py"
TRUSTED_ASSOCIATIONS = frozenset({"OWNER", "MEMBER", "COLLABORATOR"})
BROKEN_STATUSES = frozenset({"broken", "unknown_version"})
REQUEST_TIMEOUT = 120


def _load_format() -> Any:
    """共有 helper を ``sys.modules`` に登録してから実行する（pydantic のモデルが自分のモジュールを引く）。"""
    spec = importlib.util.spec_from_file_location("issue_format", FORMAT_MODULE)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {FORMAT_MODULE}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["issue_format"] = module
    spec.loader.exec_module(module)
    return module


fmt: Any = _load_format()


class Failure(Exception):
    """取得・入力の失敗。``run`` が終了コード 2 にする。"""


class Runner(Protocol):
    def __call__(
        self,
        args: Sequence[str],
        *,
        input_text: str | None = None,
    ) -> subprocess.CompletedProcess[str]: ...


def run_process(args: Sequence[str], *, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    """既定の ``Runner``。シェルを通さず、UTF-8 で標準入出力を扱う。"""
    return subprocess.run(
        list(args),
        input=input_text,
        text=True,
        encoding="utf-8",
        capture_output=True,
        timeout=REQUEST_TIMEOUT,
        check=False,
    )


@dataclass(frozen=True)
class _Issue:
    number: int
    title: str
    body: str
    state: str
    state_reason: str | None
    labels: tuple[str, ...]
    url: str


@dataclass(frozen=True)
class _Comment:
    id: int
    url: str
    created_at: str
    body: str


def _object(value: object, where: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise Failure(f"{where} is not a JSON object.")
    return cast("dict[str, Any]", value)


def _array(value: object, where: str) -> list[Any]:
    if not isinstance(value, list):
        raise Failure(f"{where} is not a JSON array.")
    return cast("list[Any]", value)


def _string(item: Mapping[str, Any], key: str, where: str) -> str:
    value = item.get(key)
    if not isinstance(value, str):
        raise Failure(f"{where}.{key} is not a string.")
    return value


def _optional_string(item: Mapping[str, Any], key: str, where: str) -> str | None:
    value = item.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise Failure(f"{where}.{key} is not a string or null.")
    return value


def _integer(item: Mapping[str, Any], key: str, where: str) -> int:
    value = item.get(key)
    if type(value) is not int:
        raise Failure(f"{where}.{key} is not an integer.")
    return value


def _pages(raw: str, where: str) -> list[list[dict[str, Any]]]:
    """``gh api --paginate --slurp`` の出力（ページの配列）を読む。"""
    try:
        value: object = json.loads(raw)
    except json.JSONDecodeError:
        raise Failure(f"{where} is not JSON.") from None
    pages: list[list[dict[str, Any]]] = []
    for page_index, page in enumerate(_array(value, where)):
        items = _array(page, f"{where}[{page_index}]")
        pages.append([_object(item, f"{where}[{page_index}][{index}]") for index, item in enumerate(items)])
    return pages


def _fetch_pages(endpoint: str, runner: Runner) -> list[list[dict[str, Any]]]:
    # 指定 repo の記録に別ホストの Issue を混ぜない。
    argv = ["gh", "api", "--paginate", "--slurp", endpoint, "--hostname", "github.com"]
    try:
        result = runner(argv, input_text=None)
    except OSError, subprocess.TimeoutExpired, UnicodeError:
        raise Failure(f"cannot run gh api for {endpoint}.") from None
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        suffix = f": {detail[:500]}" if detail else ""
        raise Failure(f"gh api for {endpoint} failed with exit code {result.returncode}{suffix}")
    return _pages(result.stdout, f"the response for {endpoint}")


def _parse_issue(item: Mapping[str, Any]) -> _Issue | None:
    if "pull_request" in item:
        return None
    number = _integer(item, "number", "an issue")
    if number < 1:
        raise Failure(f"an issue has an invalid number: {number}.")
    labels_value = item.get("labels")
    labels: list[str] = []
    for index, label in enumerate(_array(labels_value, f"issue #{number}.labels")):
        name = _string(_object(label, f"issue #{number}.labels[{index}]"), "name", f"issue #{number}.labels[{index}]")
        labels.append(name)
    body = item.get("body")
    if body is None:
        body = ""
    elif not isinstance(body, str):
        raise Failure(f"issue #{number}.body is not a string or null.")
    return _Issue(
        number=number,
        title=_string(item, "title", f"issue #{number}"),
        body=body,
        state=_string(item, "state", f"issue #{number}"),
        state_reason=_optional_string(item, "state_reason", f"issue #{number}"),
        labels=tuple(labels),
        url=_string(item, "html_url", f"issue #{number}"),
    )


def _parse_comments(pages: list[list[dict[str, Any]]], number: int) -> list[_Comment]:
    comments: list[_Comment] = []
    for page in pages:
        for item in page:
            where = f"a comment on issue #{number}"
            if _optional_string(item, "author_association", where) not in TRUSTED_ASSOCIATIONS:
                continue
            body = item.get("body")
            if body is None:
                body = ""
            elif not isinstance(body, str):
                raise Failure(f"{where} has a body that is not a string or null.")
            comments.append(
                _Comment(
                    id=_integer(item, "id", where),
                    url=_string(item, "html_url", where),
                    created_at=_string(item, "created_at", where),
                    body=body,
                )
            )
    return comments


def _target_mismatch(value: Any, repository: str, number: int) -> str | None:
    issue = getattr(value, "issue", None)
    if issue is None:
        return None
    target_repository = getattr(issue, "repository", None)
    target_number = getattr(issue, "number", None)
    if not isinstance(target_repository, str) or type(target_number) is not int:
        return "The block has no valid target issue."
    if target_repository.casefold() != repository.casefold() or target_number != number:
        return f"The block targets {target_repository}#{target_number}, not {repository}#{number}."
    return None


def _extraction_view(
    extracted: Any,
    *,
    repository: str | None = None,
    number: int | None = None,
) -> dict[str, Any]:
    status = extracted.status
    reason = extracted.reason
    value: object = None
    if status == "ok":
        mismatch = (
            _target_mismatch(extracted.value, repository, number)
            if repository is not None and number is not None
            else None
        )
        if mismatch is not None:
            status = "broken"
            reason = mismatch
        elif extracted.value is not None:
            value = extracted.value.model_dump(mode="json")
        else:
            status = "broken"
            reason = "The block has no value."
    return {
        "status": status,
        "version": extracted.version,
        "reason": reason,
        "line": extracted.line,
        "value": value,
    }


def _comment_view(comment: _Comment, extraction: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": comment.id,
        "url": comment.url,
        "created_at": comment.created_at,
        "extraction": extraction,
    }


def _unreadable(run: Any, evaluation: Any) -> bool:
    return (
        run.status == "broken"
        and evaluation.status == "broken"
        and run.version is None
        and evaluation.version is None
        and run.line is not None
        and run.line == evaluation.line
    )


def _diagnostic(number: int, kind: str, view: Mapping[str, Any], comment_id: int | None = None) -> str:
    place = f"comment {comment_id} ({kind})" if comment_id is not None else kind
    reason = view.get("reason") or view.get("status")
    return f"issue #{number} {place}: {reason}"


def _comments(
    repository: str, number: int, comments: Sequence[_Comment]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    run_records: list[dict[str, Any]] = []
    evaluations: list[dict[str, Any]] = []
    unreadable: list[dict[str, Any]] = []
    diagnostics: list[str] = []
    for comment in comments:
        run = fmt.extract_block(comment.body, "run-record")
        evaluation = fmt.extract_block(comment.body, "evaluation")
        if _unreadable(run, evaluation):
            view = _extraction_view(run)
            unreadable.append(_comment_view(comment, view))
            diagnostics.append(_diagnostic(number, "unreadable", view, comment.id))
            continue
        for kind, extracted, destination in (
            ("run-record", run, run_records),
            ("evaluation", evaluation, evaluations),
        ):
            if extracted.status == "missing":
                continue
            view = _extraction_view(extracted, repository=repository, number=number)
            destination.append(_comment_view(comment, view))
            if view["status"] in BROKEN_STATUSES:
                diagnostics.append(_diagnostic(number, kind, view, comment.id))
    return run_records, evaluations, unreadable, diagnostics


def _check_view(result: Any) -> dict[str, Any]:
    return {
        "complete": result.complete,
        "problems": [
            {"code": problem.code, "where": problem.where, "message": problem.message} for problem in result.problems
        ],
        "undetermined": list(result.undetermined),
    }


def _collect(repository: str, rules: Any, runner: Runner) -> tuple[list[dict[str, Any]], list[str]]:
    issue_pages = _fetch_pages(f"repos/{repository}/issues?state=all&per_page=100", runner)
    issues: list[_Issue] = []
    seen: set[int] = set()
    for page in issue_pages:
        for item in page:
            issue = _parse_issue(item)
            if issue is None:
                continue
            if issue.number in seen:
                raise Failure(f"issue #{issue.number} appears more than once in the response.")
            seen.add(issue.number)
            issues.append(issue)
    issues.sort(key=lambda issue: issue.number)

    records: list[dict[str, Any]] = []
    diagnostics: list[str] = []
    for issue in issues:
        comment_pages = _fetch_pages(f"repos/{repository}/issues/{issue.number}/comments", runner)
        comments = _parse_comments(comment_pages, issue.number)
        run_records, evaluations, unreadable, comment_diagnostics = _comments(repository, issue.number, comments)
        metadata = _extraction_view(fmt.extract_block(issue.body, "metadata"))
        if metadata["status"] in BROKEN_STATUSES:
            diagnostics.append(_diagnostic(issue.number, "metadata", metadata))
        diagnostics.extend(comment_diagnostics)
        records.append(
            {
                "repository": repository,
                "number": issue.number,
                "url": issue.url,
                "title": issue.title,
                "state": issue.state,
                "state_reason": issue.state_reason,
                "labels": list(issue.labels),
                "metadata": metadata,
                "check": _check_view(fmt.check_issue(issue.body, issue.labels, rules, title=issue.title)),
                "run_records": run_records,
                "evaluations": evaluations,
                "unreadable_comments": unreadable,
            }
        )
    return records, diagnostics


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="extract_issues.py",
        description="registered repository の Issue とコメントの抽出結果を JSONL で出す。",
    )
    parser.add_argument("--repo", required=True, metavar="OWNER/NAME", help="対象のリポジトリ（owner/repo）")
    return parser


def run(
    argv: Sequence[str] | None = None,
    *,
    runner: Runner = run_process,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    """CLI の本体。取得と抽出をすべて終えるまで標準出力に書かない。"""
    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as error:
        return error.code if isinstance(error.code, int) else 2
    out = stdout if stdout is not None else sys.stdout
    err = stderr if stderr is not None else sys.stderr
    try:
        rules = fmt.load_rules(args.repo)
        records, diagnostics = _collect(args.repo, rules, runner)
    except (Failure, fmt.FormatError, OSError, UnicodeError) as error:
        err.write(f"extract_issues: {error}\n")
        return 2
    out.write("".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records))
    for diagnostic in diagnostics:
        err.write(f"extract_issues: {diagnostic}\n")
    return 1 if diagnostics else 0


def main(argv: list[str] | None = None) -> int:
    """CLI の入口。"""
    return run(argv)


if __name__ == "__main__":
    raise SystemExit(main())
