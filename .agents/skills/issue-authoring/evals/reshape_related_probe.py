#!/usr/bin/env python3
"""Historical usaturn/agent-workspace fixture from commit 6e71fae4d25f217b23ce2409517cf602437a3cbf.

Offline, observable gh fixture for related-issue authoring evaluations; it is
not a result or a ready-to-run create-reso-world scenario.

This is not a security sandbox: execute only trusted commands through `exec` and
never use an absolute path to the real gh or a different network client. Each
case requires its own fresh state directory. No actual GitHub access is needed.
"""

import argparse
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any, cast
from urllib.parse import parse_qs, unquote, urlsplit

REPO = "usaturn/agent-workspace"
LABELS = ["type: improvement", "area: issue-workflow", "priority: P2", "size: S", "source: planned", "duplicate"]


def dump(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def issue(number: int, title: str, requirement: str, state: str = "open") -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "filed_on": "2026-11-09",
        "bases": [{"repository": REPO, "branch": "main", "sha": "0" * 40}],
        "estimate": {"hours_low": 1, "hours_high": 2, "confidence": "high", "uncertainties": []},
        "baselines": [],
        "targets": [],
        "discovery": {"links": [], "note": "架空の利用記録から確認"},
    }
    body = (
        "## 概要\n\n架空の作業の確認を改善する。\n\n"
        "## 問題と影響\n\n手作業で確認する担当者が見落とす。\n\n"
        "## 改善前の状態（基準値）\n\n該当なし（評価用の架空事例）。\n\n"
        "## 目標値と評価方法\n\n該当なし（評価用の架空事例）。\n\n"
        f"## 受け入れ条件\n\n{requirement}\n\n"
        "## 対象外\n\n該当なし（他の作業は変更しない）。\n\n"
        "## 関連 Issue・依存関係\n\n該当なし（未調査）。\n\n"
        "## 決定済みの事項\n\n該当なし（まだ決定していない）。\n\n"
        "## エージェントに任せる事項\n\n実装方法を検討する。\n\n"
        "## 未決事項\n\nなし\n\n"
        "<details><summary>整形前の本文（2026-11-09 に issue-authoring が保存）</summary>\n\n"
        "```issue-format-original\n架空の過去の要望。\n```\n\n</details>\n\n"
        f"<!-- issue-format:metadata:v1\n{json.dumps(metadata, ensure_ascii=False, indent=2)}\n-->\n"
    )
    return {
        "number": number,
        "id": 900000 + number,
        "title": title,
        "body": body,
        "state": state,
        "state_reason": None,
        "duplicate_of": None,
        "labels": [{"name": name} for name in LABELS[:-1]],
        "created_at": "2026-11-09T00:00:00Z",
        "updated_at": "2026-11-09T00:00:00Z",
        "html_url": f"https://github.com/{REPO}/issues/{number}",
        "comments": [],
    }


def init(out: Path, case: str, search: str) -> None:
    if not out.is_absolute():
        raise ValueError("--out-dir must be absolute")
    out.mkdir(parents=True, exist_ok=True)
    if any(out.iterdir()):
        raise ValueError("--out-dir must be empty")
    if case == "partial":
        requirements = (
            "共通 X: 日本語の確認結果を一覧に表示する。\n固有 Y: 表示結果を CSV で保存する。",
            "共通 X: 日本語の確認結果を一覧に表示する。\n固有 Z: 保存せず端末に警告する。",
        )
    else:
        requirements = (
            "共通: 日本語の確認結果を一覧に表示する。\n確認対象を複数行で表示する。",
            "共通: 日本語の確認結果を一覧に表示する。\n表示の対象には非 ASCII を含む。",
        )
    issues = [
        issue(101, "確認結果を一覧で見られるようにする", requirements[0]),
        issue(102, "確認結果の表示を改善する", requirements[1]),
        issue(103, "以前の確認結果を一覧表示する", "以前の案。\nこの Issue は完了済み。", "closed"),
    ]
    state = {"repository": REPO, "case": case, "search": search, "labels": LABELS, "issues": issues}
    dump(out / "state.json", state)
    (out / "history.jsonl").touch()
    (out / "config").mkdir()
    (out / "bin").mkdir()
    wrapper = out / "bin" / "gh"
    wrapper.write_text(
        f'#!/bin/sh\nexec {shlex.quote(sys.executable)} {shlex.quote(str(Path(__file__).resolve()))} _gh -- "$@"\n',
        encoding="utf-8",
    )
    wrapper.chmod(0o755)
    print(
        json.dumps(
            {
                "state": str(out / "state.json"),
                "history": str(out / "history.jsonl"),
                "repo": REPO,
                "issues": [101, 102, 103],
            },
            ensure_ascii=False,
        )
    )


def parse_api(args: list[str]) -> tuple[str, str, dict[str, Any], bool, bool, str | None]:
    method = "GET"
    explicit_method = False
    endpoint = ""
    payload: dict[str, Any] = {}
    paginate = False
    slurp = False
    jq: str | None = None
    i = 0
    while i < len(args):
        arg = args[i]
        if arg in ("--method", "-X", "--input", "-F", "-f", "--field", "--raw-field", "--jq", "-q"):
            if i + 1 >= len(args):
                raise ValueError(f"missing value for {arg}")
            value = args[i + 1]
            i += 2
            if arg in ("--method", "-X"):
                method = value.upper()
                explicit_method = True
            elif arg == "--input":
                if value != "-":
                    raise ValueError("only --input - is supported")
                obj: Any = json.load(sys.stdin)
                if not isinstance(obj, dict):
                    raise ValueError("expected JSON object")
                payload.update(cast("dict[str, Any]", obj))
            elif arg in ("--jq", "-q"):
                jq = value
            else:
                key, sep, val = value.partition("=")
                if not sep:
                    raise ValueError("invalid field")
                if key.endswith("[]"):
                    payload.setdefault(key[:-2], []).append(val)
                else:
                    payload[key] = val
            continue
        if arg == "--paginate":
            paginate = True
        elif arg == "--slurp":
            slurp = True
        elif not arg.startswith("-") and not endpoint:
            endpoint = arg
        else:
            raise ValueError(f"unsupported api argument: {arg}")
        i += 1
    if not endpoint or (slurp and not paginate):
        raise ValueError("missing endpoint or invalid pagination")
    if payload and method == "GET":
        if explicit_method:
            from urllib.parse import urlencode

            endpoint += ("&" if "?" in endpoint else "?") + urlencode(payload, doseq=True)
            payload = {}
        else:
            method = "POST"
    return method, endpoint, payload, paginate, slurp, jq


def api(state: dict[str, Any], method: str, endpoint: str, payload: dict[str, Any]) -> Any:
    parsed = urlsplit(endpoint)
    path = parsed.path.strip("/")
    query = parse_qs(parsed.query)
    issues: list[dict[str, Any]] = state["issues"]
    base = f"repos/{REPO}/"
    if method == "GET" and path == "search/issues":
        if state["search"] == "failure":
            raise ValueError("fixture search failure")
        q = " ".join(query.get("q", []))
        if f"repo:{REPO}" not in q:
            raise ValueError("search must target the fixture repository")
        open_only = "state:open" in q or "is:open" in q
        found = [] if state["search"] == "empty" else [x for x in issues if not open_only or x["state"] == "open"]
        return {"total_count": len(found), "incomplete_results": False, "items": found}
    if not path.startswith(base):
        raise ValueError("unsupported repository or endpoint")
    tail = path[len(base) :].split("/")
    if tail == ["labels"]:
        if method == "GET":
            return [{"name": name} for name in state["labels"]]
        if (
            method == "POST"
            and set(payload) <= {"name", "color", "description"}
            and isinstance(payload.get("name"), str)
        ):
            state["labels"].append(payload["name"])
            return {"name": payload["name"]}
    if tail == ["issues"]:
        if method == "GET":
            wanted = query.get("state", ["open"])[0]
            return [x for x in issues if wanted == "all" or x["state"] == wanted]
        if method == "POST" and set(payload) <= {"title", "body", "labels"} and isinstance(payload.get("title"), str):
            number = max(x["number"] for x in issues) + 1
            created = issue(number, payload["title"], "")
            created["body"] = payload.get("body", "")
            created["labels"] = [{"name": name} for name in payload.get("labels", [])]
            issues.append(created)
            return created
    if len(tail) < 2 or tail[0] != "issues" or not tail[1].isdigit():
        raise ValueError("unsupported endpoint")
    item = next((x for x in issues if x["number"] == int(tail[1])), None)
    if item is None:
        raise ValueError("issue not found")
    if len(tail) == 2:
        if method == "GET":
            return item
        if method == "PATCH" and payload and set(payload) <= {"title", "body", "state", "state_reason"}:
            if "body" in payload and state["case"] == "update-failure":
                raise ValueError("fixture body update failure")
            item.update(payload)
            return item
    if (
        tail[2:] == ["labels"]
        and method == "POST"
        and set(payload) == {"labels"}
        and isinstance(payload["labels"], list)
    ):
        names = cast("list[Any]", payload["labels"])
        for name in names:
            if name not in state["labels"]:
                raise ValueError("unknown label")
        for name in names:
            if name not in [x["name"] for x in item["labels"]]:
                item["labels"].append({"name": name})
        return item["labels"]
    if len(tail) == 4 and tail[2] == "labels" and method == "DELETE":
        name = unquote(tail[3])
        if name not in [x["name"] for x in item["labels"]]:
            raise ValueError("label not found")
        item["labels"] = [x for x in item["labels"] if x["name"] != name]
        return item["labels"]
    if tail[2:] == ["comments"]:
        if method == "GET":
            return item["comments"]
        if method == "POST" and set(payload) == {"body"} and isinstance(payload["body"], str):
            comment = {
                "id": len(item["comments"]) + 1,
                "body": payload["body"],
                "html_url": item["html_url"] + f"#issuecomment-{len(item['comments']) + 1}",
            }
            item["comments"].append(comment)
            return comment
    raise ValueError("unsupported operation")


def issue_command(state: dict[str, Any], args: list[str]) -> dict[str, Any]:
    if len(args) != 6 or args[0] not in ("edit", "close") or not args[1].isdigit():
        raise ValueError("unsupported issue command")
    options = dict(zip(args[2::2], args[3::2], strict=True))
    option = "--add-label" if args[0] == "edit" else "--duplicate-of"
    if set(options) != {"--repo", option} or options["--repo"] != REPO:
        raise ValueError("unsupported issue options or repository")
    issues: list[dict[str, Any]] = state["issues"]
    item = next((x for x in issues if x["number"] == int(args[1])), None)
    if item is None:
        raise ValueError("issue not found")
    if args[0] == "edit":
        name = options[option]
        if name != "duplicate" or name not in state["labels"]:
            raise ValueError("unsupported or unknown label")
        if name not in [x["name"] for x in item["labels"]]:
            item["labels"].append({"name": name})
    else:
        target = options[option]
        if not target.isdigit() or not any(x["number"] == int(target) for x in issues):
            raise ValueError("duplicate target not found")
        item["duplicate_of"] = int(target)
        item["state"] = "closed"
        item["state_reason"] = "duplicate"
    return item


def gh(args: list[str], directory: Path) -> int:
    state_path = directory / "state.json"
    state: dict[str, Any] = json.loads(state_path.read_text(encoding="utf-8"))
    method = "UNKNOWN"
    endpoint = ""
    payload: dict[str, Any] = {}
    code = 1
    try:
        if len(args) >= 2 and args[0] == "issue" and args[1] in ("edit", "close"):
            method = f"ISSUE_{args[1].upper()}"
            result = issue_command(state, args[1:])
            dump(state_path, state)
            print(result["html_url"])
            code = 0
            return code
        if not args or args[0] != "api":
            raise ValueError("unsupported gh command")
        method, endpoint, payload, _paginate, slurp, jq = parse_api(args[1:])
        # Reject unsupported output transformations before any write.
        if jq not in (None, ".[].name") or (jq is not None and method != "GET"):
            raise ValueError("unsupported jq expression")
        result = api(state, method, endpoint, payload)
        if method != "GET":
            dump(state_path, state)
        if jq is not None:
            if not isinstance(result, list):
                raise ValueError("jq requires an array")
            rows = cast("list[dict[str, str]]", result)
            print("\n".join(x["name"] for x in rows))
        else:
            print(json.dumps([result] if slurp else result, ensure_ascii=False))
        code = 0
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"fake gh: {exc}", file=sys.stderr)
    finally:
        with (directory / "history.jsonl").open("a", encoding="utf-8") as log:
            log.write(
                json.dumps(
                    {
                        "argv": args,
                        "method": method,
                        "endpoint": endpoint,
                        "payload": payload,
                        "write": method not in ("GET", "UNKNOWN"),
                        "exit_code": code,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
    return code


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    p_init = sub.add_parser("init")
    p_init.add_argument("--out-dir", type=Path, required=True)
    p_init.add_argument("--case", choices=("merge", "partial", "update-failure", "noninteractive"), required=True)
    p_init.add_argument("--search", choices=("normal", "empty", "failure"), default="normal")
    p_exec = sub.add_parser("exec")
    p_exec.add_argument("--state-dir", type=Path, required=True)
    p_exec.add_argument("command", nargs=argparse.REMAINDER)
    p_gh = sub.add_parser("_gh")
    p_gh.add_argument("args", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    try:
        if args.action == "init":
            init(args.out_dir, args.case, args.search)
            return 0
        if args.action == "_gh":
            gh_args: list[str] = args.args
            if gh_args and gh_args[0] == "--":
                gh_args = gh_args[1:]
            return gh(gh_args, Path(os.environ["RESHAPE_PROBE_STATE"]))
        directory: Path = args.state_dir
        if not directory.is_absolute() or not (directory / "state.json").is_file():
            raise ValueError("--state-dir must be an initialized absolute directory")
        command: list[str] = args.command
        if command and command[0] == "--":
            command = command[1:]
        if not command:
            raise ValueError("missing command")
        env = {k: v for k, v in os.environ.items() if not k.upper().startswith(("GH_", "GITHUB_"))}
        env["GH_CONFIG_DIR"] = str(directory / "config")
        env["RESHAPE_PROBE_STATE"] = str(directory)
        env["PATH"] = str(directory / "bin") + os.pathsep + env.get("PATH", "")
        state: dict[str, Any] = json.loads((directory / "state.json").read_text(encoding="utf-8"))
        for key in ("CI", "AGENT_RUNNER_DEPTH", "CLAUDE_CODE_SESSION_ATTENDED", "CLAUDE_CODE_ENTRYPOINT"):
            env.pop(key, None)
        if state["case"] == "noninteractive":
            env["CI"] = "1"
        return subprocess.run(command, env=env, check=False).returncode
    except (OSError, ValueError, KeyError) as exc:
        print(f"probe: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
