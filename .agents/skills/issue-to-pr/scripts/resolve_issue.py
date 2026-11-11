"""Resolve an open GitHub Issue and the issue-to-pr options (--base, --implement, --spec-review, --design-review, --merge and the loop options) without modifying Git or GitHub state.

Refuses to start from a directory Git does not track, such as a world project under worlds/.
"""

from __future__ import annotations

import argparse
import functools
import importlib
import importlib.util
import json
import re
import shlex
import subprocess
import sys
import uuid
from pathlib import Path
from typing import NamedTuple

from git_env import git_environment

# 既存の特殊経路。通常ツールは、この固定値でなく採用済み台帳と共通 identity で検証する。
# 上流の orange3134/resoloop は docs/resoloop-fork-workflow.md の流れで扱うので含めない
SUPPORTED_REPOSITORIES = ("usaturn/create-reso-world", "usaturn/resoloop", "usaturn/resoloop-meshy")
# ループ用のオプション。名前・値・意味は pr-review-fix-loop の start と同じで、--merge と一緒のときだけ受け付ける。
# 範囲・役割の名前・担当の存在などは、loop.py check-options が start と同じ関数で確かめる
LOOP_OPTIONS = frozenset({"--max-cycles", "--assign", "--template", "--config"})
# --issue-number・--issue-repository は issue-to-pr の入力オプションではなく、loop.py の start に
# 司令塔が渡す表示用の別引数。loop_args には入れない（ここでは未知のオプションとして終了コード 2 で拒否する）
# 明示した run にだけ有効にするレビューの opt-in。loop.py へは渡さず、--merge の有無に関係なく受け付ける
REVIEW_OPTIONS = frozenset({"--spec-review", "--design-review"})
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
    result = subprocess.run(
        args, cwd=cwd, capture_output=True, text=True, timeout=60,
        env=git_environment() if args[0] == "git" else None,
    )
    if result.returncode:
        # Git transport errors can echo credential-bearing URLs. Never forward them.
        detail = "" if args[0] == "git" else f": {result.stderr.strip()}"
        raise ValueError(f"{args[0]} の読み取りに失敗{detail}")
    return result.stdout.strip()


def require_tracked_cwd(cwd: Path) -> None:
    """cwd が git の追跡しないディレクトリ（ワールドのプロジェクトなど）の中なら止める。

    ワールドのプロジェクトは worktree に実体が無く、進むと Spec・Plan だけの PR の Closes #N で、
    ワールドの作業が済まないまま Issue が閉じる（#137）。確かめられないときも止める。
    """
    result = subprocess.run(
        ("git", "check-ignore", "-q", "."), cwd=cwd, capture_output=True, text=True, timeout=60,
        env=git_environment(),
    )
    if result.returncode == 1:
        return
    if result.returncode == 0:
        raise ValueError(
            f"cwd（{cwd}）は git が追跡しないディレクトリ（ワールドのプロジェクトなど）の中にあります。"
            "ワールドの作業は、そのプロジェクトで branch・PR を使わずに進めます（AGENTS.md の「プロジェクト運用」）。"
            "リポジトリのファイルを変える作業は、checkout のルートで起動し直してください"
        )
    raise ValueError(f"cwd（{cwd}）を git が追跡するかを確かめられません")


def validate_branch(branch: str, cwd: Path) -> str:
    """Check both literal heads-ref and porcelain rules; never expand @{-1}."""
    if not branch or CONTROL_CHARACTER.search(branch):
        raise ValueError("base の branch 名が不正です")
    run_readonly("git", "check-ref-format", f"refs/heads/{branch}", cwd=cwd)
    if run_readonly("git", "check-ref-format", "--branch", branch, cwd=cwd) != branch:
        raise ValueError("base は literal branch 名で指定してください")
    return branch


class ParsedInput(NamedTuple):
    reference: str
    loop_args: list[str] | None
    implement: str | None
    spec_review: str | None
    design_review: str | None
    base: str
    base_explicit: bool


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
    """利用者の引数を Issue・ループ・実装担当・レビュー・base（明示指定の有無を含む）に分ける。

    --base・--implement・--spec-review・--design-review と --merge は Issue の参照の前でも後でもよく、
    1 回だけ書ける。値は次の語か --opt=value の形で書く。レビューは明示されたときだけ値を持ち、
    loop_args には混ぜない。ループ用のオプションは --merge と一緒のときだけ受け付け、書いた順のまま返す
    （--opt=value は 2 語に分け、パスは cwd を基準に絶対パスにする）。--merge が無ければ loop_args は None。
    """
    try:
        words = shlex.split(text)
    except ValueError as exc:
        raise ValueError(f"引数を語に分けられません（{exc}）") from exc
    references: list[str] = []
    merge = 0
    loop_args: list[str] = []
    implement: list[str] = []
    reviews: dict[str, list[str]] = {"--spec-review": [], "--design-review": []}
    bases: list[str] = []
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
        if name not in {"--implement", "--base"} | REVIEW_OPTIONS and name not in LOOP_OPTIONS:
            raise ValueError(f"未知のオプションです: {word}")
        if not separator:
            if index == len(words) or words[index].startswith("-"):
                raise ValueError(f"{name} の値がありません")
            value = words[index]
            index += 1
        if name in REVIEW_OPTIONS:
            if IMPLEMENT_VALUE.fullmatch(value) is None:
                raise ValueError(
                    f"{name} の値は agent 名の形（英数字で始まり、英数字・_・.・- だけ）にしてください: {value!r}"
                )
            reviews[name].append(value)
            continue
        if name == "--base":
            if not value:
                raise ValueError("--base の値が空です")
            bases.append(validate_branch(value, cwd))
            continue
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
    if len(bases) > 1:
        raise ValueError("--base は 1 回だけ指定してください")
    if len(implement) > 1:
        raise ValueError("--implement は 1 回だけ指定してください")
    for name, values in reviews.items():
        if len(values) > 1:
            raise ValueError(f"{name} は 1 回だけ指定してください")
    if loop_args and not merge:
        raise ValueError(f"{loop_args[0]} などのループ用のオプションは、--merge と一緒のときだけ指定できます")
    if len(references) != 1:
        raise ValueError(f"Issue を 1 つだけ指定してください（指定された語: {references or 'なし'}）")
    return ParsedInput(
        references[0], loop_args if merge else None, implement[0] if implement else None,
        reviews["--spec-review"][0] if reviews["--spec-review"] else None,
        reviews["--design-review"][0] if reviews["--design-review"] else None,
        bases[0] if bases else "main", bool(bases),
    )


@functools.cache
def external_tools():
    """Load the adjacent shared package, never a cwd/PYTHONPATH namesake."""
    path = Path(__file__).resolve().parents[4] / "tools/external_tools"
    name = f"_issue_external_tools_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(
        name, path / "__init__.py", submodule_search_locations=[str(path)])
    if spec is None or spec.loader is None:
        raise ValueError("共通 external-tools を読み込めません")
    package = importlib.util.module_from_spec(spec)
    sys.modules[name] = package
    spec.loader.exec_module(package)
    importlib.import_module(f"{name}.registry")
    importlib.import_module(f"{name}.identity")
    return package


def managed_target(repo: str, *, parent_root: Path | None = None, code_root: Path | None = None):
    """Use only the adopted parent and registered common-dir; never discover a nearby repo."""
    tools = external_tools()
    if parent_root is None:
        helper_root = Path(__file__).resolve().parents[4]
        common = run_readonly("git", "rev-parse", "--path-format=absolute", "--git-common-dir", cwd=helper_root)
        parent_root = Path(common).resolve().parent
    registry = tools.registry.load_active_registry(parent_root)
    if registry is None or registry.find_repository(repo.casefold()) is None:
        raise ValueError("issue-to-pr の対象は既存 parent / fork / meshy と採用済み台帳の通常ツールだけです")
    return tools.identity.resolve_managed_target(
        registry, repo, operation="base-read", code_root=code_root)


def supported(repo: str, *, parent_root: Path | None = None) -> str:
    for candidate in SUPPORTED_REPOSITORIES:
        if candidate == repo.casefold():
            return candidate
    return managed_target(repo, parent_root=parent_root).spec.repository


def resolve_target(reference: str, cwd: Path, *, parent_root: Path | None = None) -> tuple[str, int]:
    for pattern in (ISSUE_URL, REPO_REF):
        if match := pattern.fullmatch(reference):
            return supported(match[1], parent_root=parent_root), int(match[2])
    if match := NUMBER.fullmatch(reference):
        try:
            origin = run_readonly("git", "remote", "get-url", "origin", cwd=cwd)
        except (ValueError, OSError) as exc:
            raise ValueError(f"#N を解決する現在の checkout の origin を読めません（{exc}）") from exc
        if (origin_match := ORIGIN_URL.fullmatch(origin)) is None:
            # URL に埋め込まれた認証情報（user:token@）を報告に出さない
            shown = re.sub(r"(?<=://)[^/@]*@", "***@", origin)
            raise ValueError(f"現在の checkout の origin が GitHub のリポジトリではありません: {shown}")
        return supported(origin_match[1], parent_root=parent_root), int(match[1])
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
        "文字列（後ろに続く自然文は含めない）。オプションは --base BRANCH、--implement AGENT、"
        "--spec-review AGENT、--design-review AGENT、--merge と、--merge と一緒のときの"
        "ループ用のオプション（--max-cycles・--assign・--template・--config）。"
        "- で始まりうるので、前に -- を置いて渡す",
    )
    parser.add_argument("--parent-root", type=Path, help="検証する常設 create-reso-world 親 checkout")
    args = parser.parse_args(argv)
    try:
        require_tracked_cwd(Path.cwd())
        parsed = parse_input(args.input, Path.cwd())
        repo, number = resolve_target(parsed.reference, Path.cwd(), parent_root=args.parent_root)
        target = None if repo in SUPPORTED_REPOSITORIES else managed_target(repo, parent_root=args.parent_root)
        if target is not None and parsed.loop_args is not None:
            raise ValueError("登録済み通常ツールは手動マージです。--merge は使えません")
        base = parsed.base if parsed.base_explicit or target is None else target.spec.base_branch
        payload = {
            **fetch_issue(repo, number),
            "merge": None if parsed.loop_args is None else {"loop_args": parsed.loop_args},
            "implement": parsed.implement,
            "spec_review": parsed.spec_review,
            "design_review": parsed.design_review,
            "base": base,
            "base_explicit": parsed.base_explicit,
        }
    except (ValueError, OSError, subprocess.TimeoutExpired) as exc:
        print(f"issue-to-pr: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
