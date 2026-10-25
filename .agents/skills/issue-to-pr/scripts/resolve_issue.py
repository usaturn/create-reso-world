"""Resolve an open GitHub Issue and the issue-to-pr options (--implement, --merge and the loop options) without modifying Git or GitHub state.

Refuses to start from a directory Git does not track, such as a world project under worlds/.
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path
from typing import NamedTuple

# AGENTS.md の「リポジトリ境界」の表のうち、issue-to-pr が branch と PR を作ってよいリポジトリ。
# 上流の orange3134/resoloop は docs/resoloop-fork-workflow.md の流れで扱うので含めない
SUPPORTED_REPOSITORIES = ("usaturn/create-reso-world", "usaturn/resoloop", "usaturn/resoloop-meshy")
# ループ用のオプション。名前・値・意味は pr-review-fix-loop の start と同じで、--merge と一緒のときだけ受け付ける。
# 範囲・役割の名前・担当の存在などは、loop.py check-options が start と同じ関数で確かめる
LOOP_OPTIONS = frozenset({"--max-cycles", "--assign", "--template", "--config"})
# 起動したときの cwd を基準に絶対パスにするループ用のオプション（loop.py は別の cwd で起動しうる）
PATH_OPTIONS = frozenset({"--template", "--config"})
# 受け付けないオプションと、その理由
REFUSED_OPTIONS = {
    "--hold-action": "このリポジトリの review-fix-planning には判断保留が無く、ループも受け付けません",
    "--fresh-review": "作ったばかりの PR には、再利用するレビューがありません",
}
# --implement の値は、そのまま implement_task.py check の引数になる。runner の agent 名
# （tools/agent_runner/models.py の識別子）と同じ形に限り、シェルの特殊文字を含む値を通さない
IMPLEMENT_VALUE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*")
# ループ用のオプションの値も loop.py の引数になるので、同じ理由で形を限る（パスは制御文字だけを拒む）
MAX_CYCLES_VALUE = re.compile(r"[0-9]+")
ASSIGN_VALUE = re.compile(rf"[a-z][a-z-]*={IMPLEMENT_VALUE.pattern}(?:,{IMPLEMENT_VALUE.pattern})*")
CONTROL_CHARACTER = re.compile(r"[\x00-\x1f\x7f]")
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


def require_tracked_cwd(cwd: Path) -> None:
    """cwd が git の追跡しないディレクトリ（ワールドのプロジェクトなど）の中なら止める。

    ワールドのプロジェクトは worktree に実体が無く、進むと Spec・Plan だけの PR の Closes #N で、
    ワールドの作業が済まないまま Issue が閉じる（#137）。確かめられないときも止める。
    """
    result = subprocess.run(("git", "check-ignore", "-q", "."), cwd=cwd, capture_output=True, text=True, timeout=60)
    if result.returncode == 1:
        return
    if result.returncode == 0:
        raise ValueError(
            f"cwd（{cwd}）は git が追跡しないディレクトリ（ワールドのプロジェクトなど）の中にあります。"
            "ワールドの作業は、そのプロジェクトで branch・PR を使わずに進めます（AGENTS.md の「プロジェクト運用」）。"
            "リポジトリのファイルを変える作業は、checkout のルートで起動し直してください"
        )
    raise ValueError(f"cwd（{cwd}）を git が追跡するかを確かめられません: {result.stderr.strip()}")


class ParsedInput(NamedTuple):
    reference: str
    loop_args: list[str] | None
    implement: str | None


def loop_value(name: str, value: str, cwd: Path) -> str:
    """ループ用のオプションの値の形を確かめ、パスは起動したときの cwd を基準に絶対パスにする。"""
    if name == "--max-cycles":
        valid = MAX_CYCLES_VALUE.fullmatch(value) is not None
    elif name == "--assign":
        valid = ASSIGN_VALUE.fullmatch(value) is not None
    else:
        valid = CONTROL_CHARACTER.search(value) is None
    if not valid:
        raise ValueError(f"{name} の値の形が正しくありません: {value!r}")
    if name not in PATH_OPTIONS:
        return value
    try:
        return str((cwd / Path(value).expanduser()).resolve())
    except RuntimeError as exc:  # ~user のホームディレクトリを決められない
        raise ValueError(f"{name} のパスを展開できません（{exc}）: {value!r}") from exc


def parse_input(text: str, cwd: Path) -> ParsedInput:
    """利用者が書いた引数の文字列を、Issue の参照・ループ用のオプションの列・--implement の値に分ける。

    --implement と --merge は Issue の参照の前でも後でもよく、1 回だけ書ける。値は次の語か --opt=value の形で書く。
    ループ用のオプションは --merge と一緒のときだけ受け付け、書いた順のまま返す（--opt=value は 2 語に分け、
    パスは cwd を基準に絶対パスにする）。--merge が無ければ loop_args は None。
    """
    try:
        words = shlex.split(text)
    except ValueError as exc:
        raise ValueError(f"引数を語に分けられません（{exc}）") from exc
    references: list[str] = []
    merge = 0
    loop_args: list[str] = []
    implement: list[str] = []
    index = 0
    while index < len(words):
        word = words[index]
        index += 1
        if not word.startswith("-"):
            references.append(word)
            continue
        name, separator, value = word.partition("=")
        if name in REFUSED_OPTIONS:
            raise ValueError(f"{name} は使えません（{REFUSED_OPTIONS[name]}）")
        if name == "--merge":
            if separator:
                raise ValueError(f"--merge は値を取りません: {word}")
            merge += 1
            continue
        if name != "--implement" and name not in LOOP_OPTIONS:
            raise ValueError(f"未知のオプションです: {word}")
        if not separator:
            if index == len(words) or words[index].startswith("-"):
                raise ValueError(f"{name} の値がありません")
            value = words[index]
            index += 1
        if name == "--implement":
            if IMPLEMENT_VALUE.fullmatch(value) is None:
                raise ValueError(
                    f"--implement の値は agent 名の形（英数字で始まり、英数字・_・.・- だけ）にしてください: {value!r}"
                )
            implement.append(value)
            continue
        if not value:
            raise ValueError(f"{name} の値が空です")
        loop_args += [name, loop_value(name, value, cwd)]
    if merge > 1:
        raise ValueError("--merge は 1 回だけ指定してください")
    if len(implement) > 1:
        raise ValueError("--implement は 1 回だけ指定してください")
    if loop_args and not merge:
        raise ValueError(f"{loop_args[0]} などのループ用のオプションは、--merge と一緒のときだけ指定できます")
    if len(references) != 1:
        raise ValueError(f"Issue を 1 つだけ指定してください（指定された語: {references or 'なし'}）")
    return ParsedInput(references[0], loop_args if merge else None, implement[0] if implement else None)


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
        "文字列（後ろに続く自然文は含めない）。オプションは --implement AGENT、--merge と、--merge と一緒のときの"
        "ループ用のオプション（--max-cycles・--assign・--template・--config）。"
        "- で始まりうるので、前に -- を置いて渡す",
    )
    args = parser.parse_args(argv)
    try:
        require_tracked_cwd(Path.cwd())
        parsed = parse_input(args.input, Path.cwd())
        payload = {
            **fetch_issue(*resolve_target(parsed.reference, Path.cwd())),
            "merge": None if parsed.loop_args is None else {"loop_args": parsed.loop_args},
            "implement": parsed.implement,
        }
    except (ValueError, OSError, subprocess.TimeoutExpired) as exc:
        print(f"issue-to-pr: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
