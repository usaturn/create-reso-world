"""Resolve an open GitHub Issue for issue-to-pr without modifying Git or GitHub state."""

from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path

# AGENTS.md の「リポジトリ境界」の表のうち、issue-to-pr が branch と PR を作ってよいリポジトリ。
# 上流の orange3134/resoloop は docs/resoloop-fork-workflow.md の流れで扱うので含めない
SUPPORTED_REPOSITORIES = ("usaturn/create-reso-world", "usaturn/resoloop", "usaturn/resoloop-meshy")
# 移植元の issue-to-pr にあり、この版では受け付けないオプション（#116 で入れる）
FUTURE_OPTIONS = frozenset(
    {"--merge", "--implement", "--max-cycles", "--hold-action", "--assign", "--template", "--config", "--fresh-review"}
)
STATES = ("OPEN", "CLOSED", "MERGED")

ISSUE_URL = re.compile(r"https://github\.com/([A-Za-z0-9-]+/[A-Za-z0-9._-]+)/issues/([1-9][0-9]*)/?")
REPO_REF = re.compile(r"([A-Za-z0-9-]+/[A-Za-z0-9._-]+)#([1-9][0-9]*)")
NUMBER = re.compile(r"#([1-9][0-9]*)")
ORIGIN_URL = re.compile(
    r"(?:https://github\.com/|git@github\.com:|ssh://git@github\.com/)([A-Za-z0-9-]+/[A-Za-z0-9._-]+?)(?:\.git)?/?"
)


def run_readonly(*args: str, cwd: Path | None = None) -> str:
    result = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=60)
    if result.returncode:
        raise ValueError(f"{args[0]} の読み取りに失敗: {result.stderr.strip()}")
    return result.stdout.strip()


def parse_input(text: str) -> str:
    """利用者が書いた引数の文字列から、Issue の参照を 1 つ取り出す。オプションはどれも受け付けない。"""
    try:
        words = shlex.split(text)
    except ValueError as exc:
        raise ValueError(f"引数を語に分けられません（{exc}）") from exc
    for word in words:
        if not word.startswith("-"):
            continue
        name = word.partition("=")[0]
        if name in FUTURE_OPTIONS:
            raise ValueError(f"{name} はこの版では使えません（#116 で入れる予定）")
        raise ValueError(f"未知のオプションです: {word}")
    if len(words) != 1:
        raise ValueError(f"Issue を 1 つだけ指定してください（指定された語: {words or 'なし'}）")
    return words[0]


def supported(repo: str) -> str:
    for candidate in SUPPORTED_REPOSITORIES:
        if candidate == repo.casefold():
            return candidate
    raise ValueError(
        f"{repo} は issue-to-pr の対象外です（対象は {'、'.join(SUPPORTED_REPOSITORIES)}。AGENTS.md の「リポジトリ境界」）"
    )


def resolve_target(reference: str, cwd: Path) -> tuple[str, int]:
    for pattern in (ISSUE_URL, REPO_REF):
        if match := pattern.fullmatch(reference):
            return supported(match[1]), int(match[2])
    if match := NUMBER.fullmatch(reference):
        try:
            origin = run_readonly("git", "remote", "get-url", "origin", cwd=cwd)
        except (ValueError, OSError) as exc:
            raise ValueError(f"#N を解決する現在の checkout の origin を読めません（{exc}）") from exc
        if (origin_match := ORIGIN_URL.fullmatch(origin)) is None:
            # URL に埋め込まれた認証情報（user:token@）を報告に出さない
            shown = re.sub(r"(?<=://)[^/@]*@", "***@", origin)
            raise ValueError(f"現在の checkout の origin が GitHub のリポジトリではありません: {shown}")
        return supported(origin_match[1]), int(match[1])
    raise ValueError(
        "https://github.com/<owner>/<repo>/issues/N、<owner>/<repo>#N、現在の checkout の #N の"
        "いずれかを指定してください（PR は対象外）"
    )


def fetch_issue(repo: str, number: int) -> dict[str, str | int]:
    response = run_readonly("gh", "issue", "view", str(number), "--repo", repo, "--json", "number,title,body,state,url")
    try:
        issue = json.loads(response)
    except json.JSONDecodeError as exc:
        raise ValueError("GitHub 応答が JSON ではありません") from exc
    if (
        not isinstance(issue, dict)
        or type(issue.get("number")) is not int
        or not all(isinstance(issue.get(key), str) for key in ("title", "body", "state", "url"))
        or issue["state"] not in STATES
    ):
        raise ValueError("GitHub 応答の形式が不正です")
    url_match = ISSUE_URL.fullmatch(issue["url"])
    # owner/repo の大文字小文字だけを許し、URL のほかの部分は完全に一致させる
    if (
        issue["number"] != number
        or url_match is None
        or url_match[1].casefold() != repo
        or issue["url"] != f"https://github.com/{url_match[1]}/issues/{number}"
    ):
        raise ValueError("応答は指定した Issue ではありません（PR または URL・番号の不一致）")
    if issue["state"] != "OPEN":
        raise ValueError(f"Issue は closed です: {issue['url']}")
    return {"repo": repo, "number": number, "url": issue["url"], "title": issue["title"], "body": issue["body"]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "input",
        help="利用者が書いた引数の先頭から、Issue の参照とオプションのうち最後のものまでを書かれたまま切り出した"
        "文字列（後ろに続く自然文は含めない）。- で始まりうるので、前に -- を置いて渡す",
    )
    args = parser.parse_args(argv)
    try:
        payload = fetch_issue(*resolve_target(parse_input(args.input), Path.cwd()))
    except (ValueError, OSError, subprocess.TimeoutExpired) as exc:
        print(f"issue-to-pr: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
