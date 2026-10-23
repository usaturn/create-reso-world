#!/usr/bin/env python3
"""レビュー対象の PR と、レビュー成果物の保存先・Git 操作の対象を解決する。

移植元は usaturn/agent-workspace の同名の helper（usaturn/agent-workspace#483）。create-reso-world#152 で、
Git 操作の対象を ``scripts/superpowers_context.py`` の経路（``AGENTS.md`` の「リポジトリ境界」）で決める形にした。

サブコマンド:

- ``resolve <PR> [--code-root <パス>]``: PR を GitHub に照会し、保存先と Git 操作の対象を JSON で出す（pr-review が使う）
- ``review-dir <PR|パス> [--for-planning] [--code-root <パス>] [--pr <PR>]``: 保存済みのレビューディレクトリを探す
  （review-fix-planning・review-verify）

PR の指定は、番号（``3``・``#3``。親の origin、つまり create-reso-world の PR）か PR の URL（そのリポジトリの PR）。
保存先は親の main checkout（``agent_tmp.py root`` と同じ）の
``reviews/<owner>/<repo>/#<PR 番号>-<変換後の head ブランチ名>/`` である。``owner/repo`` は PR が存在する側
（base）のリポジトリを小文字にしたもので、fork の head 側は使わない。旧配置（親の ``reviews/#<N>-*``、各 checkout の
``reviews/#<N>-*`` と ``reviews/<owner>/<repo>/#<N>-*``）は、明示したパスでだけ読む。fork と上流の両方の PR を
含みうる checkout の ``reviews/#<N>-*`` は、``--pr`` で PR を添えたときだけ読む。

Git 操作の対象（``target_root``）は、``superpowers_context.resolve_context`` の ``review-workspace`` で決める。
create-reso-world は親の checkout、usaturn/resoloop・orange3134/resoloop は ``external/resoloop``、それ以外は
``--code-root`` で明示した main checkout。checkout を探したり clone したりせず、決まらなければ止まる。
``--for-planning`` は移植元の呼び出しとの互換のために受け付け、範囲は変えない。

終了コード: 0 成功、2 引数の誤り、3 PR が存在しない、4 リポジトリが存在しないかアクセス権が無い、
5 認証・権限の問題、6 通信・API の失敗、7 親の main checkout・origin、または Git 操作の対象の checkout を使えない、
8 PR はあるが保存済みレビューが無い、9 候補が複数、11 パスから PR を決められない・食い違う、12 fetch の失敗。
10 は使わない（移植元の owner の制限は持ち込まない）。

標準ライブラリだけで書く（``agent_tmp.py``・``superpowers_context.py``・``review_records.py`` と同じく、
スキルの外にある依存として扱う）。
"""

from __future__ import annotations

import argparse
import functools
import importlib.util
import json
import os
import re
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from types import ModuleType
from typing import Any, NamedTuple, cast

EXIT_USAGE = 2
EXIT_PR_NOT_FOUND = 3
EXIT_REPOSITORY_NOT_FOUND = 4
EXIT_AUTH = 5
EXIT_API = 6
EXIT_PARENT = 7
EXIT_NO_REVIEW = 8
EXIT_AMBIGUOUS = 9
EXIT_PATH = 11
EXIT_FETCH = 12

REVIEWS_DIR = "reviews"

_OWNER = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]*")
_REPO = re.compile(r"[A-Za-z0-9._-]+")
_MODEL_FILENAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
# Path separators, Windows-illegal name chars, and C0 controls.
_UNSAFE_DIRECTORY_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_SHA = re.compile(r"[0-9a-f]{40}")
_NUMBER = r"(?P<number>[1-9][0-9]*)"
_BARE = re.compile(rf"#?{_NUMBER}")
_PULL_URL = re.compile(rf"https://github\.com/(?P<owner>[^/?#\s]+)/(?P<repo>[^/?#\s]+)/pull/{_NUMBER}(?:[/?#]\S*)?")
_REMOTE_URLS = (
    re.compile(r"https://github\.com/(?P<owner>[^/\s]+)/(?P<repo>[^/\s]+?)(?:\.git)?/?"),
    re.compile(r"(?:ssh://)?git@github\.com[:/](?P<owner>[^/\s]+)/(?P<repo>[^/\s]+?)(?:\.git)?/?"),
)
_STATUS_LINE = re.compile(r"HTTP/[0-9.]+ (?P<status>[0-9]{3})\b")
_REVIEW_DIR_NAME = re.compile(rf"#{_NUMBER}-.+")


class TargetError(Exception):
    """解決できない。``code`` は終了コード。"""

    def __init__(self, code: int, message: str) -> None:
        super().__init__(message)
        self.code = code


Runner = Callable[[Sequence[str]], "subprocess.CompletedProcess[str]"]


def _run(argv: Sequence[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(list(argv), check=False, capture_output=True, text=True)


def git_environment(*, transport_auth: bool = False) -> dict[str, str]:
    """``-C`` で指定した checkout の Git を見る環境。

    ``GIT_DIR``・``GIT_COMMON_DIR`` など（linked worktree の ``git rebase --exec``・フックが export）が残ると、
    ``git -C <checkout>`` も別の Git を読み書きする。runner はレビュアーの子の環境から ``GIT_*`` を除くので、
    呼び出し側（loop・review-fix-planning）の checkout の解決・浅い checkout の判定も、子の helper と同じ Git を見る。
    pr-review の helper（``pr_review_workspace.git``）と loop の ``git_output`` もここを使う。
    helper の直接起動では Git の認証に必要な transport 設定だけを残す。これらはローカルの
    Git ディレクトリや worktree の選択を変えない。runner の子は従来どおり全 ``GIT_*`` を除く。
    """
    allowed = {"GIT_ASKPASS", "GIT_SSH", "GIT_SSH_COMMAND", "GIT_TERMINAL_PROMPT"} if transport_auth else set()
    return {key: value for key, value in os.environ.items() if not key.startswith("GIT_") or key in allowed}


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(cwd), *args], check=False, capture_output=True, text=True, env=git_environment()
    )


# 名前の規則（pr-review の helper もここを使う）


def validate_repository(value: str) -> str:
    """``owner/repo`` を GitHub の名前に使える文字だけに限る。"""
    owner, separator, name = value.partition("/")
    if not separator or _OWNER.fullmatch(owner) is None or _REPO.fullmatch(name) is None or name in {".", ".."}:
        raise TargetError(EXIT_USAGE, f"GitHub の owner/repo として使えない名前です: {value!r}")
    return value


def same_repository(left: str | None, right: str | None) -> bool:
    """GitHub の名前は大文字小文字を区別しない。"""
    return left is not None and right is not None and left.lower() == right.lower()


def normalize_head_branch(value: str) -> str:
    if not value or value.startswith("/") or value.endswith("/") or value in {".", ".."}:
        raise TargetError(EXIT_USAGE, "head branch cannot produce a safe review directory")
    normalized = _UNSAFE_DIRECTORY_CHARS.sub("-", value).rstrip(" .")
    if not normalized or normalized in {".", ".."}:
        raise TargetError(EXIT_USAGE, "head branch cannot produce a safe review directory")
    return normalized


def review_directory_name(pr_number: int, head_branch: str) -> str:
    if type(pr_number) is not int or pr_number < 1:
        raise TargetError(EXIT_USAGE, "PR number cannot produce a safe review directory")
    return f"#{pr_number}-{normalize_head_branch(head_branch)}"


def validate_model_name(value: str) -> str:
    """モデル識別子をファイル名にする。``/`` と空白の並びは ``-`` にし、端の空白は拒否する。"""
    if value != value.strip():
        raise TargetError(EXIT_USAGE, "model identifier is not a safe filename")
    sanitized = re.sub(r"\s+", "-", value.replace("/", "-"))
    if _MODEL_FILENAME.fullmatch(sanitized) is None:
        raise TargetError(EXIT_USAGE, "model identifier is not a safe filename")
    return sanitized


def _lower_parts(repository: str) -> tuple[str, str]:
    owner, name = validate_repository(repository).lower().split("/")
    return owner, name


def repository_reviews_root(parent_root: Path, repository: str) -> Path:
    """``<親>/reviews/<owner>/<repo>``。移植先の pr-review と ``superpowers_context.py`` に合わせて小文字にする。"""
    owner, name = _lower_parts(repository)
    return parent_root / REVIEWS_DIR / owner / name


def review_directory(parent_root: Path, repository: str, pr_number: int, head_branch: str) -> Path:
    return repository_reviews_root(parent_root, repository) / review_directory_name(pr_number, head_branch)


# 親の main checkout と、Git 操作の対象の checkout


def _load(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise TargetError(EXIT_PARENT, f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    # dataclass の型注釈の解決は sys.modules を引くので、読み込む前に登録する。
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _load_agent_tmp() -> ModuleType:
    return _load("_review_target_agent_tmp", Path(__file__).resolve().parent / "agent_tmp.py")


@functools.cache
def _load_superpowers_context() -> ModuleType:
    """同じ checkout の ``scripts/superpowers_context.py``（経路の規則の定義元）。"""
    path = Path(__file__).resolve().parents[2] / "scripts" / "superpowers_context.py"
    return _load("_review_target_superpowers_context", path)


def require_parent_root(path: Path) -> Path:
    """親の main checkout（linked worktree・submodule でない）で、``reviews/`` が git に無視されていること。"""
    root = path.resolve()
    toplevel = _git(root, "rev-parse", "--show-toplevel")
    common = _git(root, "rev-parse", "--path-format=absolute", "--git-common-dir")
    if toplevel.returncode or common.returncode or Path(toplevel.stdout.strip()).resolve() != root:
        raise TargetError(EXIT_PARENT, f"親の main checkout ではありません: {root}")
    if Path(common.stdout.strip()).resolve() != (root / ".git").resolve():
        raise TargetError(EXIT_PARENT, f"親の main checkout ではありません（linked worktree か submodule）: {root}")
    if _git(root, "check-ignore", "-q", f"{REVIEWS_DIR}/.review-target-probe").returncode != 0:
        raise TargetError(EXIT_PARENT, f"{root} では {REVIEWS_DIR}/ が git に無視されていません")
    return root


def default_parent_root() -> Path:
    """このスクリプトの置き場所から親の main checkout を決める（``agent_tmp.py root`` と同じ規則）。"""
    agent_tmp = _load_agent_tmp()
    try:
        root = cast(Path, agent_tmp.resolve_main_root(Path(__file__).resolve().parent))
    except agent_tmp.AgentTmpError as error:
        raise TargetError(EXIT_PARENT, f"親の main checkout を解決できません: {error}") from error
    return require_parent_root(root)


def github_repository(url: str) -> str | None:
    """GitHub の remote URL（https・ssh）から ``owner/repo`` を読む。それ以外は None。"""
    for pattern in _REMOTE_URLS:
        match = pattern.fullmatch(url.strip())
        if match is None:
            continue
        try:
            return validate_repository(f"{match['owner']}/{match['repo']}")
        except TargetError:
            return None
    return None


def origin_repository(checkout: Path) -> str | None:
    """origin の URL の設定値から読む。``git remote get-url`` は insteadOf を展開するので使わない。"""
    result = _git(checkout, "config", "--get", "remote.origin.url")
    return github_repository(result.stdout.strip()) if result.returncode == 0 else None


def remote_repositories(checkout: Path) -> list[str]:
    """全ての remote の URL の設定値にある GitHub のリポジトリ（小文字、重複なし、名前順）。"""
    result = _git(checkout, "config", "--get-regexp", r"^remote\..*\.url$")
    if result.returncode not in (0, 1):
        raise TargetError(EXIT_PATH, f"{checkout} の remote を読めません: {result.stderr.strip()}")
    found = {
        repository.lower()
        for line in result.stdout.splitlines()
        if (repository := github_repository(line.partition(" ")[2])) is not None
    }
    return sorted(found)


def parent_repository(parent_root: Path) -> str:
    repository = origin_repository(parent_root)
    if repository is None:
        raise TargetError(
            EXIT_PARENT,
            f"親リポジトリ {parent_root} の origin を GitHub のリポジトリとして解決できません。"
            "PR URL を指定してください",
        )
    return repository


def _toplevel(path: Path) -> Path | None:
    result = _git(path, "rev-parse", "--show-toplevel")
    return Path(result.stdout.strip()).resolve() if result.returncode == 0 else None


class TargetCheckout(NamedTuple):
    """Git 操作の対象にする main checkout と、PR を取得する remote。"""

    root: Path
    remote: str


def target_checkout(parent_root: Path, repository: str, code_root: Path | None = None) -> TargetCheckout:
    """``superpowers_context.resolve_context`` の ``review-workspace`` で、Git 操作の対象を決める。

    create-reso-world は親、usaturn/resoloop・orange3134/resoloop は ``external/resoloop``（上流の PR の remote は
    ``upstream``）、それ以外は ``code_root``（明示した main checkout で、remote 1 件が PR のリポジトリと一致する）。
    checkout を探したり clone したりせず、決まらなければ止まる。
    """
    context = _load_superpowers_context()
    try:
        resolved = context.resolve_context(
            "review-workspace", parent_root=parent_root, code_root=code_root, repo=repository
        )
    except (context.ContextError, OSError) as error:
        hint = (
            "。--code-root <main checkout の絶対パス> で指定してください"
            if isinstance(error, context.InputError)
            else ""
        )
        raise TargetError(
            EXIT_PARENT,
            f"{repository} の Git 操作の対象の checkout を決められません（clone も checkout の探索もしません）: "
            f"{error}{hint}",
        ) from error
    return TargetCheckout(Path(resolved["code_root"]), str(resolved["base_remote"]))


# PR の指定と GitHub への照会


class PullRequestArgument(NamedTuple):
    repository: str | None
    number: int


def parse_pull_request_argument(text: str) -> PullRequestArgument:
    value = text.strip()
    bare = _BARE.fullmatch(value)
    if bare is not None:
        return PullRequestArgument(None, int(bare["number"]))
    url = _PULL_URL.fullmatch(value)
    if url is not None:
        return PullRequestArgument(validate_repository(f"{url['owner']}/{url['repo']}"), int(url["number"]))
    raise TargetError(EXIT_USAGE, f"PR の指定を解釈できません（番号、#番号、PR の URL で指定してください）: {text!r}")


class PullRequest(NamedTuple):
    repository: str
    number: int
    url: str
    head_ref: str
    head_sha: str
    head_repository: str | None
    base_ref: str
    state: str
    clone_url: str


def _api(runner: Runner, path: str) -> tuple[int | None, str, str]:
    """``gh api -i`` を呼び、最後の応答のステータス・本文と、標準エラーを返す（リダイレクトのヘッダは読み飛ばす）。"""
    result = runner(["gh", "api", "-i", path])
    text = (result.stdout or "").replace("\r\n", "\n")
    status: int | None = None
    while (match := _STATUS_LINE.match(text)) is not None:
        status = int(match["status"])
        text = text.partition("\n\n")[2]
    return status, text, (result.stderr or "").strip()


def _object(value: object) -> dict[str, Any] | None:
    return cast(dict[str, Any], value) if isinstance(value, dict) else None


def _parse_pull_request(body: str, repository: str, number: int) -> PullRequest:
    def broken(what: str) -> TargetError:
        return TargetError(EXIT_API, f"GitHub の応答を読めません（{repository} の PR #{number}: {what}）")

    try:
        data = _object(json.loads(body))
    except json.JSONDecodeError as error:
        raise broken("JSON ではありません") from error
    base = _object(data.get("base")) if data else None
    head = _object(data.get("head")) if data else None
    base_repo = _object(base.get("repo")) if base else None
    if data is None or base is None or head is None or base_repo is None:
        raise broken("base・head・base.repo がありません")

    def text(mapping: Mapping[str, Any], key: str, where: str) -> str:
        value = mapping.get(key)
        if not isinstance(value, str) or not value:
            raise broken(where)
        return value

    pr_number = data.get("number")
    if type(pr_number) is not int or pr_number != number:
        raise broken("number")
    head_sha = text(head, "sha", "head.sha")
    if _SHA.fullmatch(head_sha) is None:
        raise broken("head.sha")
    head_repo = _object(head.get("repo"))
    head_repository = head_repo.get("full_name") if head_repo else None
    try:
        canonical = validate_repository(text(base_repo, "full_name", "base.repo.full_name"))
    except TargetError as error:
        raise broken("base.repo.full_name") from error
    return PullRequest(
        repository=canonical,
        number=number,
        url=text(data, "html_url", "html_url"),
        head_ref=text(head, "ref", "head.ref"),
        head_sha=head_sha,
        head_repository=head_repository if isinstance(head_repository, str) else None,
        base_ref=text(base, "ref", "base.ref"),
        state=text(data, "state", "state"),
        clone_url=text(base_repo, "clone_url", "base.repo.clone_url"),
    )


def fetch_pull_request(repository: str, number: int, *, runner: Runner = _run) -> PullRequest:
    """PR を照会する。不存在・リポジトリの不在・認証・通信の失敗を区別する。"""
    status, body, detail = _api(runner, f"repos/{repository}/pulls/{number}")
    if status == 200:
        return _parse_pull_request(body, repository, number)
    if status == 404:
        status, _, detail = _api(runner, f"repos/{repository}")
        if status == 200:
            raise TargetError(
                EXIT_PR_NOT_FOUND,
                f"{repository} に PR #{number} は存在しません。"
                "別リポジトリの PR を指定する場合は、PR URL を指定してください",
            )
        if status == 404:
            raise TargetError(
                EXIT_REPOSITORY_NOT_FOUND,
                f"{repository} が存在しないか、アクセス権がありません（PR #{number} を確認できません）",
            )
    if status in {401, 403}:
        raise TargetError(
            EXIT_AUTH,
            f"GitHub の認証・権限の問題で {repository} の PR #{number} を確認できません（HTTP {status}）。"
            "gh auth status を確認してください",
        )
    reason = f"HTTP {status}" if status is not None else (detail or "応答がありません")
    raise TargetError(
        EXIT_API, f"GitHub への照会に失敗したため、{repository} の PR #{number} を確認できません（{reason}）"
    )


def describe(parent_root: Path, pr: PullRequest, review_dir: Path, checkout: TargetCheckout) -> dict[str, Any]:
    return {
        "parent_root": str(parent_root),
        **pr._asdict(),
        "review_dir": str(review_dir),
        "target_root": str(checkout.root),
        "base_remote": checkout.remote,
    }


def resolve(
    argument: str, *, parent_root: Path, code_root: Path | None = None, runner: Runner = _run
) -> dict[str, Any]:
    """pr-review 用。PR を照会し、保存先（存在しなくてよい）と Git 操作の対象を返す。"""
    parsed = parse_pull_request_argument(argument)
    repository = parsed.repository or parent_repository(parent_root)
    pr = fetch_pull_request(repository, parsed.number, runner=runner)
    checkout = target_checkout(parent_root, pr.repository, code_root)
    return describe(parent_root, pr, review_directory(parent_root, pr.repository, pr.number, pr.head_ref), checkout)


# レビューディレクトリの探索


def numbered_directories(root: Path, number: int) -> list[Path]:
    """``root`` の直下で ``#<number>-`` で始まるディレクトリ（symlink を除く）。"""
    prefix = f"#{number}-"
    try:
        entries = sorted(root.iterdir())
    except (FileNotFoundError, NotADirectoryError):
        return []
    return [entry for entry in entries if entry.name.startswith(prefix) and entry.is_dir() and not entry.is_symlink()]


def legacy_review_directories(
    parent_root: Path, repository: str, number: int, checkout: TargetCheckout
) -> list[Path]:
    """旧配置にある同じ PR のディレクトリ。番号・URL で探したときにエラーの文に並べるだけで、選ばない。

    親の checkout の PR は親の ``reviews/#<N>-*``。ほかの checkout の PR は、その checkout の ``reviews/#<N>-*`` と、
    checkout ごとに保存していたときの ``reviews/<owner>/<repo>/#<N>-*``。
    """
    if checkout.root == parent_root.resolve():
        roots = [parent_root / REVIEWS_DIR]
    else:
        roots = [checkout.root / REVIEWS_DIR, repository_reviews_root(checkout.root, repository)]
    return [directory for root in roots for directory in numbered_directories(root, number)]


class DirectoryIdentity(NamedTuple):
    repository: str
    number: int
    check_name: bool
    # 親以外の checkout の reviews/ にあるときの、その checkout（Git 操作の対象と一致することを確かめる）
    checkout: Path | None = None


def _path_repository(directory: Path) -> str | None:
    """``…/reviews/<owner>/<repo>/#<N>-*`` の ``<owner>/<repo>``。名前に使えなければ None。"""
    try:
        return validate_repository(f"{directory.parent.parent.name}/{directory.parent.name}")
    except TargetError:
        return None


def _checkout_root(path: Path, parent_root: Path) -> Path | None:
    """``path`` が親以外の Git の checkout のルートなら、そのパス。"""
    if path == parent_root.resolve() or not path.is_dir():
        return None
    return path if _toplevel(path) == path else None


def _identity_from_layout(
    parent_root: Path,
    directory: Path,
    from_findings: tuple[str, int] | None,
    expected: tuple[str, int] | None,
) -> DirectoryIdentity | None:
    """パスの形から PR を決める。決められない形なら None。"""
    match = _REVIEW_DIR_NAME.fullmatch(directory.name)
    if match is None:
        return None
    number = int(match["number"])
    reviews = (parent_root / REVIEWS_DIR).resolve()
    parents = directory.parents
    if len(parents) > 2 and parents[2] == reviews:
        repository = _path_repository(directory)
        return DirectoryIdentity(repository, number, check_name=True) if repository is not None else None
    if directory.parent == reviews:
        return DirectoryIdentity(parent_repository(parent_root), number, check_name=True)
    if len(parents) > 3 and parents[2].name == REVIEWS_DIR:
        # checkout ごとに保存していたときの配置（<checkout>/reviews/<owner>/<repo>/#<N>-*）
        checkout = _checkout_root(parents[3], parent_root)
        repository = _path_repository(directory)
        if checkout is not None and repository is not None and repository.lower() in remote_repositories(checkout):
            return DirectoryIdentity(repository, number, check_name=True, checkout=checkout)
    if directory.parent.name != REVIEWS_DIR:
        return None
    # 各 checkout の旧形式（<checkout>/reviews/#<N>-*）
    checkout = _checkout_root(parents[1], parent_root)
    candidates = remote_repositories(checkout) if checkout is not None else []
    if checkout is None or not candidates:
        return None
    if len(candidates) == 1:
        return DirectoryIdentity(candidates[0], number, check_name=True, checkout=checkout)
    listed = "、".join(candidates)
    if expected is not None:
        if expected[0].lower() not in candidates:
            raise TargetError(
                EXIT_PATH, f"--pr の {expected[0]} は、{checkout} の remote のリポジトリ（{listed}）のどれでもありません"
            )
        return DirectoryIdentity(expected[0], number, check_name=True, checkout=checkout)
    if from_findings is not None:
        if from_findings[0].lower() not in candidates or from_findings[1] != number:
            raise TargetError(
                EXIT_PATH,
                f"{directory} の findings/ は {from_findings[0]} の PR #{from_findings[1]} を指していて、"
                f"{checkout} の remote のリポジトリ（{listed}）の PR #{number} と食い違います",
            )
        return DirectoryIdentity(from_findings[0], number, check_name=False, checkout=checkout)
    raise TargetError(
        EXIT_PATH,
        f"{directory} は {checkout} の旧形式のレビューディレクトリで、remote が複数のリポジトリ（{listed}）を"
        "指すため、どの PR のレビューか決められません。--pr <PR の URL> を添えてください"
        "（ディレクトリ名との一致では決めません）",
    )


def _identity_from_findings(directory: Path) -> tuple[str, int] | None:
    """``findings/*.json`` の ``pr``（全ファイルで同じこと）。候補一覧が無ければ None。"""
    findings = directory / "findings"
    if not findings.is_dir():
        return None
    seen: dict[tuple[str, int], str] = {}
    for path in sorted(findings.glob("*.json")):
        if path.name.startswith("."):
            continue
        try:
            document = _object(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise TargetError(EXIT_PATH, f"{path} を読めません: {error}") from error
        pr = _object(document.get("pr")) if document else None
        repository = pr.get("repository") if pr else None
        number = pr.get("number") if pr else None
        if not isinstance(repository, str) or type(number) is not int:
            raise TargetError(EXIT_PATH, f"{path} に pr.repository・pr.number がありません")
        seen[(repository.lower(), number)] = repository
    if not seen:
        return None
    if len(seen) > 1:
        raise TargetError(EXIT_PATH, f"{findings} の候補一覧が複数の PR を指しています")
    ((_, number), repository) = next(iter(seen.items()))
    return validate_repository(repository), number


def identify_review_directory(
    parent_root: Path, directory: Path, expected: tuple[str, int] | None = None
) -> DirectoryIdentity:
    """パスの形（新しい配置・旧配置）か ``findings/`` の ``pr`` から、対象の PR を決める。

    ``expected``（``--pr`` の PR）があれば、決めた PR とディレクトリ名の番号が一致することを確かめる。
    """
    from_findings = _identity_from_findings(directory)
    identity = _identity_from_layout(parent_root, directory, from_findings, expected)
    if identity is None:
        if from_findings is not None:
            identity = DirectoryIdentity(from_findings[0], from_findings[1], check_name=False)
        elif expected is not None and _REVIEW_DIR_NAME.fullmatch(directory.name) is not None:
            identity = DirectoryIdentity(expected[0], expected[1], check_name=True)
        else:
            raise TargetError(
                EXIT_PATH,
                f"{directory} から対象の PR を決められません"
                "（reviews/<owner>/<repo>/#<N>-*・旧配置・findings/ のどれでもない）",
            )
    elif from_findings is not None and (
        not same_repository(from_findings[0], identity.repository) or from_findings[1] != identity.number
    ):
        raise TargetError(
            EXIT_PATH,
            f"{directory} の findings/ は {from_findings[0]} の PR #{from_findings[1]} を指していて、"
            f"ディレクトリの場所（{identity.repository} の PR #{identity.number}）と食い違います",
        )
    if expected is not None:
        named = _REVIEW_DIR_NAME.fullmatch(directory.name)
        if (
            not same_repository(identity.repository, expected[0])
            or identity.number != expected[1]
            or (named is not None and int(named["number"]) != expected[1])
        ):
            raise TargetError(
                EXIT_PATH,
                f"--pr の {expected[0]} の PR #{expected[1]} は、{directory}"
                f"（{identity.repository} の PR #{identity.number}）と食い違います",
            )
    return identity


def _from_path(
    argument: str, *, parent_root: Path, code_root: Path | None, pr_argument: str | None, runner: Runner
) -> dict[str, Any]:
    path = Path(argument)
    if not path.is_dir():
        raise TargetError(
            EXIT_USAGE, f"PR の指定（番号、#番号、PR の URL）でも、存在するディレクトリでもありません: {argument!r}"
        )
    directory = path.resolve()
    expected: tuple[str, int] | None = None
    if pr_argument is not None:
        parsed = parse_pull_request_argument(pr_argument)
        expected = (parsed.repository or parent_repository(parent_root), parsed.number)
    identity = identify_review_directory(parent_root, directory, expected)
    pr = fetch_pull_request(identity.repository, identity.number, runner=runner)
    if identity.check_name and directory.name != review_directory_name(pr.number, pr.head_ref):
        raise TargetError(
            EXIT_PATH,
            f"ディレクトリ名 {directory.name} が {pr.repository} の PR #{pr.number}"
            f"（head ブランチ {pr.head_ref}）と一致しません",
        )
    checkout = target_checkout(parent_root, pr.repository, code_root)
    if identity.checkout is not None and identity.checkout != checkout.root:
        raise TargetError(
            EXIT_PATH,
            f"{directory} は {identity.checkout} のレビューディレクトリで、Git 操作の対象の checkout"
            f"（{checkout.root}）と違います。既知の経路に無いリポジトリなら、--code-root に同じ checkout を指定してください",
        )
    return describe(parent_root, pr, directory, checkout)


def find_review_directory(
    argument: str,
    *,
    parent_root: Path,
    code_root: Path | None = None,
    pr_argument: str | None = None,
    runner: Runner = _run,
) -> dict[str, Any]:
    """review-fix-planning・review-verify 用。番号・URL・パスから保存済みのレビューディレクトリを決める。

    番号・URL は新しい配置だけを見る。旧配置は、パス（``pr_argument`` で PR を添えてもよい）でだけ読む。
    """
    try:
        parsed = parse_pull_request_argument(argument)
    except TargetError:
        return _from_path(
            argument, parent_root=parent_root, code_root=code_root, pr_argument=pr_argument, runner=runner
        )
    if pr_argument is not None:
        raise TargetError(EXIT_USAGE, "--pr は、レビューディレクトリのパスを指定したときだけ使えます")
    repository = parsed.repository or parent_repository(parent_root)
    pr = fetch_pull_request(repository, parsed.number, runner=runner)
    checkout = target_checkout(parent_root, pr.repository, code_root)
    root = repository_reviews_root(parent_root, pr.repository)
    candidates = numbered_directories(root, pr.number)
    if not candidates:
        legacy = legacy_review_directories(parent_root, pr.repository, pr.number, checkout)
        hint = (
            "。旧配置に同じ PR のディレクトリがあります（使う場合はパスで指定してください）: "
            + ", ".join(map(str, legacy))
            if legacy
            else ""
        )
        raise TargetError(
            EXIT_NO_REVIEW,
            f"{pr.repository} の PR #{pr.number} は存在しますが、{root} に保存済みのレビューがありません{hint}",
        )
    if len(candidates) > 1:
        raise TargetError(
            EXIT_AMBIGUOUS,
            "候補が複数あります。レビューディレクトリのパスを指定してください: " + ", ".join(map(str, candidates)),
        )
    return describe(parent_root, pr, candidates[0], checkout)


# PR head の固定


def _review_ref(repository: str, number: int) -> str:
    """移植先の pr-review と同じ、所属リポジトリと PR 番号の組ごとの ref（fork と上流で衝突しない）。"""
    owner, name = _lower_parts(repository)
    return f"refs/pr-review/repos/{owner}/{name}/{number}"


def fetch_pull_head(checkout: Path, repository: str, number: int, head_sha: str, *, remote: str) -> str:
    """``remote`` の ``pull/<N>/head`` を ``refs/pr-review/repos/<owner>/<repo>/<N>`` に固定し、``head_sha`` と一致することを確かめる。

    ``remote`` は ``target_checkout`` の ``remote``（上流の PR は ``upstream``）。追跡 ref・タグ・``FETCH_HEAD`` は変えない。
    他のセッションの cleanup が ref を消した場合に限り、1 回だけ fetch し直す。
    """
    ref = _review_ref(repository, number)
    current: subprocess.CompletedProcess[str] | None = None
    for _attempt in range(2):
        fetched = _git(
            checkout,
            "fetch",
            "--quiet",
            "--no-write-fetch-head",
            "--no-tags",
            "--refmap=",
            remote,
            f"+pull/{number}/head:{ref}",
        )
        if fetched.returncode:
            raise TargetError(
                EXIT_FETCH, f"PR #{number} の head を fetch できません（{checkout}）: {fetched.stderr.strip()}"
            )
        current = _git(checkout, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")
        if current.returncode == 0:
            break
    if current is None or current.returncode:
        raise TargetError(EXIT_FETCH, f"fetch し直しても {ref} がありません（{checkout}）")
    fetched_sha = current.stdout.strip()
    if fetched_sha != head_sha:
        raise TargetError(
            EXIT_FETCH,
            f"PR #{number} の head が解決時の {head_sha[:12]} から {fetched_sha[:12]} に変わりました。"
            "解決からやり直してください",
        )
    return ref


# CLI


def main(argv: Sequence[str] | None = None, *, runner: Runner = _run) -> int:
    parser = argparse.ArgumentParser(
        prog="review_target.py", description="Resolve review targets and review directories (create-reso-world#152)."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    code_root_help = "main checkout of a PR repository outside the known routes (absolute path)"
    resolve_parser = commands.add_parser("resolve", help="resolve a PR for pr-review")
    resolve_parser.add_argument("pr", help="PR number (3, #3) or PR URL")
    resolve_parser.add_argument("--code-root", type=Path, help=code_root_help)
    review_dir_parser = commands.add_parser("review-dir", help="find the saved review directory")
    review_dir_parser.add_argument("target", help="PR number, PR URL, or review directory path")
    review_dir_parser.add_argument(
        "--for-planning",
        action="store_true",
        help="accepted for compatibility with the source callers; it does not narrow the PR range",
    )
    review_dir_parser.add_argument("--code-root", type=Path, help=code_root_help)
    review_dir_parser.add_argument("--pr", help="PR number or URL that a review directory path must match")
    args = parser.parse_args(argv)
    try:
        if args.command == "resolve":
            result = resolve(args.pr, parent_root=default_parent_root(), code_root=args.code_root, runner=runner)
        else:
            result = find_review_directory(
                args.target,
                parent_root=default_parent_root(),
                code_root=args.code_root,
                pr_argument=args.pr,
                runner=runner,
            )
    except TargetError as error:
        print(f"review_target: {error}", file=sys.stderr)
        return error.code
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
