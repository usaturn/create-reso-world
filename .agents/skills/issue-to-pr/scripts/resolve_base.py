"""Resolve an exact origin heads ref to a verified commit without changing local branches.

Only objects are fetched. No branch, index, worktree, remote-tracking ref or
FETCH_HEAD is updated. A captured SHA can be checked again before later writes.

The advance modes keep an unpushed feature branch usable when its remote base moves:
they inspect the movement, rebase the worktree, and gate publishing and PR creation on
a fresh verification of the new (base, HEAD) pair.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from git_env import git_environment
from resolve_issue import (
    ORIGIN_URL, SUPPORTED_REPOSITORIES, managed_target, require_tracked_cwd, supported, validate_branch,
)

SHA = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})")
COMMIT = re.compile(r"[0-9a-f]{40}")
SHA256 = re.compile(r"[0-9a-f]{64}")
HEX_TOKEN = re.compile(r"(?<![0-9a-fA-F])[0-9a-fA-F]{7,40}(?![0-9a-fA-F])")
STATE_KEYS = frozenset({"repo", "remote", "branch", "ref", "sha"})
ADVANCE_KEYS = frozenset({
    "target", "repo", "branch", "ref", "old_sha", "new_sha", "phase",
    "old_head", "new_head", "changed_files", "premise_note",
})
DOCUMENT_REPOSITORY = "usaturn/create-reso-world"


def _git_result(checkout: Path, *args: str, transport_auth: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=checkout, env=git_environment(transport_auth=transport_auth),
        capture_output=True, text=True, timeout=60,
    )


def git(checkout: Path, *args: str, transport_auth: bool = False) -> str:
    """Local reads drop every inherited GIT_*; only origin transport keeps its authentication."""
    result = _git_result(checkout, *args, transport_auth=transport_auth)
    if result.returncode:
        # A transport error may contain credentials even when get-url was safe.
        raise ValueError(f"git {args[0]} に失敗しました（詳細は認証情報保護のため省略）")
    return result.stdout.strip()


def git_output(checkout: Path, *args: str, transport_auth: bool = False) -> str:
    result = _git_result(checkout, *args, transport_auth=transport_auth)
    if result.returncode:
        raise ValueError(f"git {args[0]} に失敗しました（詳細は認証情報保護のため省略）")
    return result.stdout


def git_ok(checkout: Path, *args: str) -> bool:
    return _git_result(checkout, *args).returncode == 0


def require_origin(checkout: Path, repo: str) -> None:
    for options in (("--all",), ("--push", "--all")):
        urls = git(checkout, "remote", "get-url", *options, "origin").splitlines()
        if not urls or any(
            (match := ORIGIN_URL.fullmatch(url)) is None or match[1].casefold() != repo for url in urls
        ):
            raise ValueError("origin の fetch/push URL が指定した repository と一致しません")


def remote_sha(checkout: Path, ref: str) -> str:
    response = git(checkout, "ls-remote", "--exit-code", "--refs", "origin", ref, transport_auth=True)
    lines = response.splitlines()
    if len(lines) != 1:
        raise ValueError("origin の base ref を一意に確定できません")
    sha, separator, actual_ref = lines[0].partition("\t")
    if not separator or actual_ref != ref or SHA.fullmatch(sha) is None:
        raise ValueError("origin の応答が指定した完全な heads ref と一致しません")
    return sha


def resolve_base(
    checkout: Path, repo: str, base: str | None, required_bases: list[str], expected_sha: str | None
) -> dict[str, str]:
    repo = supported(repo)
    checkout = checkout.expanduser().resolve(strict=True)
    require_tracked_cwd(checkout)
    if Path(git(checkout, "rev-parse", "--show-toplevel")).resolve() != checkout:
        raise ValueError("--checkout は作業対象の checkout root を指定してください")
    target = None if repo in SUPPORTED_REPOSITORIES else managed_target(repo, code_root=checkout)
    default_base = target.spec.base_branch if target is not None else "main"
    branch = validate_branch(base if base is not None else default_base, checkout)
    for required in required_bases:
        validate_branch(required, checkout)
        # A requirement must match the selected (registered or legacy) default or explicit base.
        if branch != required:
            raise ValueError("要求された base を --base で明示してください（未指定または矛盾）")
    if expected_sha is not None and SHA.fullmatch(expected_sha) is None:
        raise ValueError("--expected-sha は完全な commit SHA を指定してください")
    require_origin(checkout, repo)
    ref = f"refs/heads/{branch}"
    sha = remote_sha(checkout, ref)
    if expected_sha is not None and sha != expected_sha:
        raise ValueError("origin の base が捕捉した SHA から移動しました")
    # Explicit source + empty refmap prevents repository fetch configuration from
    # updating any local head or remote-tracking ref. Do not write FETCH_HEAD.
    git(checkout, "fetch", "--no-tags", "--no-write-fetch-head", "--refmap=", "origin", ref, transport_auth=True)
    if remote_sha(checkout, ref) != sha:
        raise ValueError("origin の base が取得中に移動しました")
    if git(checkout, "cat-file", "-t", sha) != "commit":
        raise ValueError("origin の base は commit ではありません")
    return {"repo": repo, "remote": "origin", "branch": branch, "ref": ref, "sha": sha}


def _regular_file(path: Path, label: str) -> Path:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"{label} は symlink でない通常ファイルである必要があります")
    return path


def _read_bytes(path: Path, label: str) -> bytes:
    return _regular_file(path, label).read_bytes()


def _read_text(path: Path, label: str) -> str:
    try:
        return _read_bytes(path, label).decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{label} は UTF-8 のテキストではありません") from exc


def _read_json_bytes(path: Path, label: str) -> tuple[object, bytes]:
    data = _read_bytes(path, label)
    try:
        return json.loads(data), data
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} が JSON ではありません") from exc


def _read_json(path: Path, label: str) -> object:
    return _read_json_bytes(path, label)[0]


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json_bytes(payload: object) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")


def _write_new(path: Path, payload: object) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(_json_bytes(payload))
    except BaseException:
        try:
            path.unlink()
        except OSError:
            pass
        raise


def _remove_any(path: Path) -> None:
    if path.is_symlink() or path.exists():
        path.unlink()


def _write_state_target(path: Path) -> tuple[Path, Path]:
    path = path.expanduser()
    if path.stem.endswith(".initial"):
        raise ValueError("--write-state には初期固定ファイルではなく base 状態ファイルを指定してください")
    initial = path.with_name(f"{path.stem}.initial{path.suffix}")
    parent = path.parent
    if parent.is_symlink() or not parent.is_dir():
        raise ValueError("--write-state の親ディレクトリが実在する通常ディレクトリではありません")
    for destination in (path, initial):
        if os.path.lexists(destination):
            raise ValueError("--write-state の保存先または初期固定ファイルが既に存在します")
    return path, initial


def _write_state(path: Path, payload: dict[str, str]) -> None:
    path, initial = _write_state_target(path)
    created: list[Path] = []
    try:
        for destination in (path, initial):
            _write_new(destination, payload)
            created.append(destination)
    except BaseException:
        for destination in created:
            try:
                destination.unlink()
            except OSError:
                pass
        raise


def _verify_checkout(root: Path, repo: str) -> tuple[str, Path]:
    root = root.expanduser()
    if root.is_symlink():
        raise ValueError("checkout に symlink は指定できません")
    root = root.resolve(strict=True)
    require_tracked_cwd(root)
    if Path(git(root, "rev-parse", "--show-toplevel")).resolve() != root:
        raise ValueError("checkout は対象リポジトリのルートを指定してください")
    canonical = supported(repo)
    if canonical not in SUPPORTED_REPOSITORIES:
        managed_target(repo, code_root=root)
    require_origin(root, canonical)
    return canonical, root


def _read_state(path: Path, expected_repo: str) -> dict[str, str]:
    payload = _read_json(path, path.name)
    if not isinstance(payload, dict) or set(payload) != STATE_KEYS:
        raise ValueError(f"{path.name} の項目が base 状態の形式と一致しません")
    if not all(isinstance(payload[key], str) and payload[key] for key in ("repo", "remote", "branch", "ref")):
        raise ValueError(f"{path.name} の文字列項目が不正です")
    if supported(payload["repo"]) != expected_repo:
        raise ValueError(f"{path.name} の repo が対象リポジトリと一致しません")
    if payload["remote"] != "origin":
        raise ValueError(f"{path.name} の remote が origin ではありません")
    if payload["ref"] != f"refs/heads/{payload['branch']}":
        raise ValueError(f"{path.name} の ref と branch が一致しません")
    if not isinstance(payload["sha"], str) or COMMIT.fullmatch(payload["sha"]) is None:
        raise ValueError(f"{path.name} の sha が 40 桁の commit SHA ではありません")
    return {key: payload[key] for key in STATE_KEYS}


@dataclass
class Context:
    session: Path
    code_repo: str
    docs_repo: str
    target_root: Path
    parent_root: Path
    docs_separate: bool
    code_state: dict[str, str]
    code_initial: dict[str, str]
    docs_state: dict[str, str] | None
    docs_initial: dict[str, str] | None
    advances: list[dict[str, object]]


def _read_advances(
    path: Path, docs_separate: bool, code_state: dict[str, str], docs_state: dict[str, str] | None,
    code_repo: str,
) -> list[dict[str, object]]:
    if not os.path.lexists(path):
        return []
    data = _read_bytes(path, path.name)
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{path.name} は UTF-8 の JSONL ではありません") from exc
    if not text.strip():
        raise ValueError(f"{path.name} が空です")
    records: list[dict[str, object]] = []
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            raise ValueError(f"{path.name} の {number} 行目が空です")
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path.name} の {number} 行目が JSON ではありません") from exc
        if not isinstance(record, dict) or set(record) != ADVANCE_KEYS:
            raise ValueError(f"{path.name} の {number} 行目の項目が前進記録の形式と一致しません")
        target = record["target"]
        if target not in ("code", "docs"):
            raise ValueError(f"{path.name} の {number} 行目の target が不正です")
        if target == "docs" and not docs_separate:
            raise ValueError(f"{path.name} に文書分離でない run の docs 記録があります")
        state = code_state if target == "code" else docs_state
        expected_repo = code_repo if target == "code" else DOCUMENT_REPOSITORY
        if state is None:
            raise ValueError(f"{path.name} の {number} 行目に対応する base 状態がありません")
        repo = record["repo"]
        if not isinstance(repo, str) or not repo or supported(repo) != expected_repo:
            raise ValueError(f"{path.name} の {number} 行目の repo が対象と一致しません")
        branch = record["branch"]
        if not isinstance(branch, str) or not branch or branch != state["branch"]:
            raise ValueError(f"{path.name} の {number} 行目の branch が base 状態と一致しません")
        if record["ref"] != f"refs/heads/{branch}":
            raise ValueError(f"{path.name} の {number} 行目の ref が branch と一致しません")
        old_sha, new_sha = record["old_sha"], record["new_sha"]
        if (
            not isinstance(old_sha, str) or COMMIT.fullmatch(old_sha) is None
            or not isinstance(new_sha, str) or COMMIT.fullmatch(new_sha) is None
            or old_sha == new_sha
        ):
            raise ValueError(f"{path.name} の {number} 行目の SHA が不正です")
        phase = record["phase"]
        if phase == "pre_worktree":
            if record["old_head"] is not None or record["new_head"] is not None:
                raise ValueError(f"{path.name} の {number} 行目の worktree 前の HEAD が null ではありません")
        elif phase == "worktree":
            for key in ("old_head", "new_head"):
                value = record[key]
                if not isinstance(value, str) or COMMIT.fullmatch(value) is None:
                    raise ValueError(f"{path.name} の {number} 行目の {key} が 40 桁の SHA ではありません")
        else:
            raise ValueError(f"{path.name} の {number} 行目の phase が不正です")
        changed = record["changed_files"]
        if not isinstance(changed, list) or any(not isinstance(item, str) for item in changed):
            raise ValueError(f"{path.name} の {number} 行目の changed_files が文字列配列ではありません")
        premise = record["premise_note"]
        if not isinstance(premise, str) or not premise.strip():
            raise ValueError(f"{path.name} の {number} 行目の前提確認が空です")
        records.append(record)
    return records


def _verify_state_chain(
    advances: list[dict[str, object]], initial: dict[str, str], current: dict[str, str], target: str,
) -> None:
    for key in ("repo", "remote", "branch", "ref"):
        if initial[key] != current[key]:
            raise ValueError(f"{target} の base 状態の {key} が初期値と一致しません")
    records = [record for record in advances if record["target"] == target]
    if not records:
        if initial["sha"] != current["sha"]:
            raise ValueError(f"{target} の base 状態が初期値と一致しません")
        return
    if records[0]["old_sha"] != initial["sha"]:
        raise ValueError(f"{target} の前進記録の先頭が初期 SHA と一致しません")
    for previous, following in zip(records, records[1:]):
        if previous["new_sha"] != following["old_sha"]:
            raise ValueError(f"{target} の前進記録が連続していません")
    if records[-1]["new_sha"] != current["sha"]:
        raise ValueError(f"{target} の前進記録の末尾が現在の SHA と一致しません")


def _context(session_arg: Path) -> Context:
    session = session_arg.expanduser()
    if session.is_symlink() or not session.is_dir():
        raise ValueError("--session は symlink でない実在するディレクトリを指定してください")
    session = session.resolve(strict=True)
    target = _read_json(session / "target.json", "target.json")
    if not isinstance(target, dict):
        raise ValueError("target.json がオブジェクトではありません")
    for key in ("code_root", "parent_root", "repository", "document_repository"):
        value = target.get(key)
        if not isinstance(value, str) or not value:
            raise ValueError(f"target.json の {key} が空または文字列ではありません")
    repository = str(target["repository"])
    document = str(target["document_repository"])
    docs_separate = document.casefold() != repository.casefold()
    if docs_separate and supported(document) != DOCUMENT_REPOSITORY:
        raise ValueError("target.json の document_repository が文書リポジトリと一致しません")
    code_repo, target_root = _verify_checkout(Path(str(target["code_root"])), repository)
    _, parent_root = _verify_checkout(Path(str(target["parent_root"])), DOCUMENT_REPOSITORY)
    code_state = _read_state(session / "code-base.json", code_repo)
    code_initial = _read_state(session / "code-base.initial.json", code_repo)
    docs_state = docs_initial = None
    if docs_separate:
        docs_state = _read_state(session / "docs-base.json", DOCUMENT_REPOSITORY)
        docs_initial = _read_state(session / "docs-base.initial.json", DOCUMENT_REPOSITORY)
    advances = _read_advances(
        session / "base-advances.jsonl", docs_separate, code_state, docs_state, code_repo)
    _verify_state_chain(advances, code_initial, code_state, "code")
    if docs_separate and docs_initial is not None and docs_state is not None:
        _verify_state_chain(advances, docs_initial, docs_state, "docs")
    return Context(
        session, code_repo, DOCUMENT_REPOSITORY, target_root, parent_root,
        docs_separate, code_state, code_initial, docs_state, docs_initial, advances,
    )


def _normalize_owned_path(raw: object) -> str:
    if not isinstance(raw, str) or not raw or "\x00" in raw or "\\" in raw or raw.startswith("/"):
        raise ValueError("所有パスは空でないリポジトリ相対 POSIX パスで指定してください")
    stripped = raw.rstrip("/")
    if stripped in ("", "."):
        raise ValueError("所有パスがリポジトリ全体または空を指しています")
    parts = stripped.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise ValueError("所有パスに空・.・.. の要素があります")
    return stripped


def _paths_overlap(first: str, second: str) -> bool:
    return (
        first == second or first.startswith(second + "/") or second.startswith(first + "/")
    )


def _owned_list(value: object, label: str, *, nonempty: bool) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ValueError(f"owned-paths.json の {label} が文字列配列ではありません")
    if nonempty and not value:
        raise ValueError(f"owned-paths.json の {label} が空です")
    normalized = [_normalize_owned_path(item) for item in value]
    for index, first in enumerate(normalized):
        for second in normalized[index + 1:]:
            if _paths_overlap(first, second):
                raise ValueError(f"owned-paths.json の {label} に重複するパスがあります")
    return normalized


def _load_owned(path: Path, docs_separate: bool) -> tuple[list[str], list[str], str]:
    payload, data = _read_json_bytes(path, "owned-paths.json")
    if not isinstance(payload, dict) or not set(payload).issubset({"code", "docs"}):
        raise ValueError("owned-paths.json の項目が形式と一致しません")
    if "code" not in payload:
        raise ValueError("owned-paths.json に code がありません")
    code = _owned_list(payload["code"], "code", nonempty=True)
    docs_value = payload.get("docs", [])
    if docs_separate:
        if "docs" not in payload:
            raise ValueError("文書分離の run では owned-paths.json の docs が必須です")
        docs = _owned_list(docs_value, "docs", nonempty=True)
    else:
        docs = _owned_list(docs_value, "docs", nonempty=False)
        if docs:
            raise ValueError("文書分離でない run の owned-paths.json に docs のパスがあります")
    return code, docs, _sha256(data)


def _changed_files(checkout: Path, old_sha: str, new_sha: str) -> list[str]:
    output = git_output(
        checkout, "diff", "--no-renames", "--name-only", "-z", old_sha, new_sha)
    return [item for item in output.split("\0") if item]


def _commits(checkout: Path, old_sha: str, new_sha: str) -> list[dict[str, str]]:
    output = git_output(checkout, "log", "--format=%H%x09%s", f"{old_sha}..{new_sha}")
    commits: list[dict[str, str]] = []
    for line in output.splitlines():
        sha, separator, subject = line.partition("\t")
        if not separator or COMMIT.fullmatch(sha) is None:
            raise ValueError("base のコミット一覧を読み取れません")
        commits.append({"sha": sha, "subject": subject})
    return commits


def _overlaps_owned(changed: list[str], owned: list[str]) -> bool:
    return any(_paths_overlap(item, allowed) for item in changed for allowed in owned)


def _verify_worktree(
    path: Path, checkout: Path, expected_branch: str, old_sha: str, new_sha: str,
    advanced: bool, base_changed: list[str],
) -> str:
    path = path.expanduser()
    if path.is_symlink() or not path.is_dir():
        raise ValueError("作業 worktree が実在する通常ディレクトリではありません")
    root = path.resolve(strict=True)
    if root == checkout.expanduser().resolve(strict=True):
        raise ValueError("worktree に常設の checkout は指定できません")
    if Path(git(root, "rev-parse", "--show-toplevel")).resolve() != root:
        raise ValueError("worktree のルートが --code-root / --doc-root と一致しません")
    git_dir = Path(git(root, "rev-parse", "--path-format=absolute", "--git-dir")).resolve()
    common = Path(git(root, "rev-parse", "--path-format=absolute", "--git-common-dir")).resolve()
    if git_dir == common:
        raise ValueError("常設の checkout を worktree として扱えません")
    expected_common = Path(
        git(checkout, "rev-parse", "--path-format=absolute", "--git-common-dir")).resolve()
    if common != expected_common:
        raise ValueError("worktree が対象 checkout と同じ Git ディレクトリに属していません")
    if git(root, "symbolic-ref", "--quiet", "--short", "HEAD") != expected_branch:
        raise ValueError("worktree の現在のブランチが指定した作業ブランチと一致しません")
    if git(root, "status", "--porcelain", "--untracked-files=normal"):
        raise ValueError("worktree に未コミットの変更があります")
    if not git_ok(root, "merge-base", "--is-ancestor", old_sha, "HEAD"):
        raise ValueError("捕捉した base SHA が worktree の HEAD の祖先ではありません")
    if git(root, "rev-list", "--merges", f"{old_sha}..HEAD"):
        raise ValueError("worktree の変更履歴にマージコミットがあります")
    head_sha = git(root, "rev-parse", "--verify", "HEAD^{commit}")
    if COMMIT.fullmatch(head_sha) is None:
        raise ValueError("worktree の HEAD を完全な SHA で確定できません")
    if advanced:
        changed = _changed_files(root, old_sha, head_sha)
        if _overlaps_owned(changed, base_changed):
            raise ValueError("base の変更ファイルが worktree の変更と重複しています")
        if head_sha != old_sha and not git_ok(root, "merge-tree", "--write-tree", head_sha, new_sha):
            raise ValueError("worktree の HEAD と新しい base が衝突します")
    return head_sha


def _verify_worktree_clean(path: Path, checkout: Path, base_sha: str) -> str:
    path = path.expanduser()
    if path.is_symlink() or not path.is_dir():
        raise ValueError("検証対象の worktree が実在する通常ディレクトリではありません")
    root = path.resolve(strict=True)
    if root == checkout.expanduser().resolve(strict=True):
        raise ValueError("検証対象に常設の checkout は指定できません")
    if Path(git(root, "rev-parse", "--show-toplevel")).resolve() != root:
        raise ValueError("検証対象のパスが worktree のルートではありません")
    git_dir = Path(git(root, "rev-parse", "--path-format=absolute", "--git-dir")).resolve()
    common = Path(git(root, "rev-parse", "--path-format=absolute", "--git-common-dir")).resolve()
    if git_dir == common:
        raise ValueError("常設の checkout を検証対象の worktree として扱えません")
    expected_common = Path(
        git(checkout, "rev-parse", "--path-format=absolute", "--git-common-dir")).resolve()
    if common != expected_common:
        raise ValueError("検証対象の worktree が対象 checkout と同じ Git ディレクトリに属していません")
    if _git_result(root, "symbolic-ref", "--quiet", "--short", "HEAD").returncode:
        raise ValueError("検証対象の worktree が detached HEAD です")
    if git(root, "status", "--porcelain", "--untracked-files=normal"):
        raise ValueError("検証対象の worktree に未コミットの変更があります")
    if not git_ok(root, "merge-base", "--is-ancestor", base_sha, "HEAD"):
        raise ValueError("base SHA が worktree の HEAD の祖先ではありません")
    head_sha = git(root, "rev-parse", "--verify", "HEAD^{commit}")
    if COMMIT.fullmatch(head_sha) is None:
        raise ValueError("worktree の HEAD を完全な SHA で確定できません")
    return head_sha


@dataclass
class Inspection:
    context: Context
    phase: str
    payload: dict[str, object]
    code_branch: str
    doc_branch: str
    doc_root: Path


def _path_exists(path: Path) -> bool:
    return path.is_symlink() or path.exists()


def _doc_root(args: argparse.Namespace, context: Context) -> Path:
    code_root = args.code_root.expanduser()
    if not context.docs_separate:
        return code_root
    if args.doc_root is None:
        raise ValueError("文書分離の run では --doc-root が必須です")
    doc_root = args.doc_root.expanduser()
    if doc_root.resolve(strict=False) == code_root.resolve(strict=False):
        raise ValueError("文書分離の run では --doc-root に --code-root と別のパスを指定してください")
    return doc_root


def _inspection(args: argparse.Namespace) -> Inspection:
    if args.max_advances < 1:
        raise ValueError("--max-advances は 1 以上にしてください")
    context = _context(args.session)
    code_branch = validate_branch(args.code_branch, context.target_root)
    doc_branch = ""
    if context.docs_separate:
        if not args.doc_branch:
            raise ValueError("文書分離の run では --doc-branch が必須です")
        doc_branch = validate_branch(args.doc_branch, context.parent_root)
    code_owned, docs_owned, owned_sha = _load_owned(args.owned_paths_file, context.docs_separate)
    if git(context.target_root, "ls-remote", "--refs", "origin", f"refs/heads/{code_branch}",
           transport_auth=True):
        raise ValueError("作業ブランチが既に origin に push 済みのため rebase できません")
    if context.docs_separate and git(
        context.parent_root, "ls-remote", "--refs", "origin", f"refs/heads/{doc_branch}",
        transport_auth=True,
    ):
        raise ValueError("文書ブランチが既に origin に push 済みのため rebase できません")

    code_path = args.code_root.expanduser()
    code_exists = _path_exists(code_path)
    if code_path.is_symlink():
        raise ValueError("--code-root に symlink は指定できません")
    doc_path = _doc_root(args, context)
    if context.docs_separate:
        if doc_path.is_symlink():
            raise ValueError("--doc-root に symlink は指定できません")
        doc_exists = _path_exists(doc_path)
        if code_exists != doc_exists:
            raise ValueError("code と docs の worktree の片方だけが存在します")
        if code_exists and not (code_path.is_dir() and doc_path.is_dir()):
            raise ValueError("--code-root と --doc-root は実在するディレクトリである必要があります")
        phase = "worktree" if code_exists else "pre_worktree"
    else:
        if code_exists and not code_path.is_dir():
            raise ValueError("--code-root が実在するディレクトリではありません")
        phase = "worktree" if code_exists else "pre_worktree"

    code_new = resolve_base(
        context.target_root, context.code_repo, context.code_state["branch"], [], None)["sha"]
    if COMMIT.fullmatch(code_new) is None:
        raise ValueError("origin の code base SHA が 40 桁の commit SHA ではありません")
    docs_new = None
    if context.docs_separate and context.docs_state is not None:
        docs_new = resolve_base(
            context.parent_root, context.docs_repo, context.docs_state["branch"], [], None)["sha"]
        if COMMIT.fullmatch(docs_new) is None:
            raise ValueError("origin の docs base SHA が 40 桁の commit SHA ではありません")
    code_advanced = code_new != context.code_state["sha"]
    docs_advanced = False
    if context.docs_state is not None and docs_new is not None:
        docs_advanced = docs_new != context.docs_state["sha"]
    if not code_advanced and not docs_advanced:
        raise ValueError("origin の base は移動していません")

    targets: dict[str, dict[str, object]] = {}

    def inspect_target(
        target: str, checkout: Path, old_sha: str, new_sha: str, owned: list[str],
        branch: str,
    ) -> dict[str, object]:
        advanced = old_sha != new_sha
        payload: dict[str, object] = {
            "advanced": advanced, "old_sha": old_sha, "new_sha": new_sha,
            "commits": [], "changed_files": [], "branch": branch, "head_sha": None,
        }
        if not advanced:
            return payload
        count = sum(1 for record in context.advances if record["target"] == target)
        if count >= args.max_advances:
            raise ValueError(f"{target} の base 前進が上限（{args.max_advances} 回）に達しています")
        if not git_ok(checkout, "merge-base", "--is-ancestor", old_sha, new_sha):
            raise ValueError(f"{target} の base が fast-forward ではありません")
        changed = _changed_files(checkout, old_sha, new_sha)
        if _overlaps_owned(changed, owned):
            raise ValueError(f"{target} の base 変更ファイルが所有パスと重複しています")
        payload["commits"] = _commits(checkout, old_sha, new_sha)
        payload["changed_files"] = changed
        return payload

    targets["code"] = inspect_target(
        "code", context.target_root, context.code_state["sha"], code_new, code_owned, code_branch)
    if context.docs_separate and context.docs_state is not None and docs_new is not None:
        targets["docs"] = inspect_target(
            "docs", context.parent_root, context.docs_state["sha"], docs_new, docs_owned,
            doc_branch)

    if phase == "worktree":
        code_target = targets["code"]
        code_target["head_sha"] = _verify_worktree(
            code_path, context.target_root, code_branch, context.code_state["sha"],
            str(code_target["new_sha"]), bool(code_target["advanced"]),
            list(code_target["changed_files"]),
        )
        if context.docs_separate and "docs" in targets:
            docs_target = targets["docs"]
            docs_target["head_sha"] = _verify_worktree(
                doc_path, context.parent_root, doc_branch, context.docs_state["sha"],  # type: ignore[union-attr]
                str(docs_target["new_sha"]), bool(docs_target["advanced"]),
                list(docs_target["changed_files"]),
            )

    payload: dict[str, object] = {
        "phase": phase,
        "docs_separate": context.docs_separate,
        "owned_paths_sha256": owned_sha,
        "targets": targets,
    }
    return Inspection(context, phase, payload, code_branch, doc_branch, doc_path)


def _compare_inspection(recorded: object, live: dict[str, object]) -> None:
    if not isinstance(recorded, dict):
        raise ValueError("--inspection がオブジェクトではありません")
    for key in ("phase", "owned_paths_sha256"):
        if recorded.get(key) != live[key]:
            raise ValueError("--inspection が現在の検査結果と一致しません")
    if recorded.get("docs_separate") is not live["docs_separate"]:
        raise ValueError("--inspection が現在の検査結果と一致しません")
    recorded_targets = recorded.get("targets")
    live_targets = live["targets"]
    if not isinstance(recorded_targets, dict) or not isinstance(live_targets, dict):
        raise ValueError("--inspection の targets が不正です")
    if set(recorded_targets) != set(live_targets):
        raise ValueError("--inspection の対象が現在の検査結果と一致しません")
    for target, live_target in live_targets.items():
        recorded_target = recorded_targets.get(target)
        if not isinstance(recorded_target, dict):
            raise ValueError("--inspection の対象が不正です")
        if recorded_target.get("advanced") is not live_target["advanced"]:
            raise ValueError("--inspection が現在の検査結果と一致しません")
        for key in ("old_sha", "new_sha", "branch", "head_sha"):
            if recorded_target.get(key) != live_target[key]:
                raise ValueError("--inspection が現在の検査結果と一致しません")


def _appended_advances(path: Path, records: list[dict[str, object]]) -> bytes:
    existing = _read_bytes(path, path.name) if os.path.lexists(path) else b""
    prefix = b"\n" if existing and not existing.endswith(b"\n") else b""
    return existing + prefix + b"".join(_json_bytes(record) for record in records)


def _replace_files(files: list[tuple[Path, bytes]]) -> None:
    staged: list[tuple[str, Path]] = []
    try:
        for path, data in files:
            descriptor, temporary = tempfile.mkstemp(
                dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(data)
            os.chmod(temporary, 0o600)
            staged.append((temporary, path))
        for temporary, path in staged:
            os.replace(temporary, path)
    except BaseException:
        for temporary, _ in staged:
            try:
                os.unlink(temporary)
            except OSError:
                pass
        raise


def _advance(args: argparse.Namespace) -> dict[str, object]:
    premise = _read_text(args.premise_file, "advance-premise.txt")
    if not premise.strip():
        raise ValueError("advance-premise.txt が空です")
    live = _inspection(args)
    recorded = _read_json(args.inspection, "advance-inspection.json")
    _compare_inspection(recorded, live.payload)
    context = live.context
    records: list[dict[str, object]] = []
    applied: list[tuple[Path, str]] = []
    current: tuple[Path, str] | None = None
    try:
        for target in ("code", "docs"):
            target_payload = live.payload["targets"].get(target)  # type: ignore[union-attr]
            if not isinstance(target_payload, dict) or not target_payload["advanced"]:
                continue
            if live.phase == "worktree":
                path = (args.code_root if target == "code" else live.doc_root).expanduser()
                rebase_root = path.resolve(strict=True)
                old_head = git(rebase_root, "rev-parse", "--verify", "HEAD^{commit}")
                if COMMIT.fullmatch(old_head) is None:
                    raise ValueError("rebase 前の worktree HEAD を確定できません")
                current = (rebase_root, old_head)
                result = _git_result(
                    rebase_root, "rebase", "--onto", str(target_payload["new_sha"]),
                    str(target_payload["old_sha"]))
                if result.returncode:
                    raise ValueError("rebase に失敗したため前進を適用しませんでした")
                applied.append((rebase_root, old_head))
                current = None
                new_head = git(rebase_root, "rev-parse", "--verify", "HEAD^{commit}")
                if COMMIT.fullmatch(new_head) is None:
                    raise ValueError("rebase 後の worktree HEAD を確定できません")
            else:
                old_head = new_head = None
            state = context.code_state if target == "code" else context.docs_state
            if state is None:
                raise ValueError(f"{target} の base 状態がありません")
            records.append({
                "target": target,
                "repo": state["repo"],
                "branch": state["branch"],
                "ref": state["ref"],
                "old_sha": target_payload["old_sha"],
                "new_sha": target_payload["new_sha"],
                "phase": live.phase,
                "old_head": old_head,
                "new_head": new_head,
                "changed_files": target_payload["changed_files"],
                "premise_note": premise,
            })
    except BaseException:
        if current is not None:
            _git_result(current[0], "rebase", "--abort")
            _git_result(current[0], "reset", "--hard", current[1])
        for path, old_head in reversed(applied):
            _git_result(path, "reset", "--hard", old_head)
        raise

    for name in ("reverified.json", "checks.json", "code-sha.txt", "docs-sha.txt"):
        _remove_any(context.session / name)
    new_states: list[tuple[Path, bytes]] = []
    result_states: dict[str, dict[str, str] | None] = {
        "code": dict(context.code_state),
        "docs": dict(context.docs_state) if context.docs_state is not None else None,
    }
    for record in records:
        if record["target"] == "code":
            next_state = dict(context.code_state)
            next_state["sha"] = str(record["new_sha"])
            new_states.append((context.session / "code-base.json", _json_bytes(next_state)))
            result_states["code"] = next_state
        else:
            if context.docs_state is None:
                raise ValueError("docs の base 状態がありません")
            next_state = dict(context.docs_state)
            next_state["sha"] = str(record["new_sha"])
            new_states.append((context.session / "docs-base.json", _json_bytes(next_state)))
            result_states["docs"] = next_state
    _replace_files([
        (context.session / "base-advances.jsonl",
         _appended_advances(context.session / "base-advances.jsonl", records)),
        *new_states,
    ])
    return {
        "records": records,
        "code_base": result_states["code"],
        "docs_base": result_states["docs"],
        "advance_count": len(context.advances) + len(records),
    }


def _normalize_commands(value: object, docs_separate: bool, *, allow_shorthand: bool) -> list[dict[str, object]]:
    if not isinstance(value, list) or not value:
        raise ValueError("検証コマンドは 1 件以上の配列で指定してください")
    normalized: list[dict[str, object]] = []
    for item in value:
        if isinstance(item, list):
            if not allow_shorthand:
                raise ValueError("保存済みの検証コマンドが正規化されたオブジェクトではありません")
            cwd, argv = "code", item
        elif isinstance(item, dict):
            if set(item) != {"cwd", "argv"}:
                raise ValueError("検証コマンドのオブジェクトは cwd と argv だけを持てます")
            cwd, argv = item["cwd"], item["argv"]
        else:
            raise ValueError("検証コマンドの要素が配列またはオブジェクトではありません")
        if cwd not in ("code", "docs", "parent") or (cwd == "docs" and not docs_separate):
            raise ValueError("検証コマンドの cwd が実行できない場所を指しています")
        if not isinstance(argv, list) or not argv:
            raise ValueError("検証コマンドの argv が 1 件以上の配列ではありません")
        if any(not isinstance(argument, str) or "\x00" in argument for argument in argv):
            raise ValueError("検証コマンドの引数が文字列ではありません")
        if not argv[0].strip():
            raise ValueError("検証コマンドの argv[0] が空です")
        normalized.append({"cwd": cwd, "argv": list(argv)})
    return normalized


def _read_required(session: Path, docs_separate: bool) -> tuple[list[dict[str, object]], bytes]:
    payload, data = _read_json_bytes(session / "required-verify-cmds.json", "required-verify-cmds.json")
    normalized = _normalize_commands(payload, docs_separate, allow_shorthand=False)
    if payload != normalized:
        raise ValueError("required-verify-cmds.json が正規化された形ではありません")
    return normalized, data


def _set_verify_cmds(args: argparse.Namespace) -> None:
    context = _context(args.session)
    supplied = _normalize_commands(
        _read_json(args.commands_file, "verify-cmds.json"), context.docs_separate, allow_shorthand=True)
    path = context.session / "required-verify-cmds.json"
    if os.path.lexists(path):
        existing, _ = _read_required(context.session, context.docs_separate)
        if existing != supplied:
            raise ValueError("必須検証コマンドは既に固定されており、内容を変更できません")
        return
    try:
        _write_new(path, supplied)
    except FileExistsError as exc:
        raise ValueError("必須検証コマンドが同時に作成されました") from exc


def _verify_remote_state(context: Context) -> None:
    code_tip = resolve_base(
        context.target_root, context.code_repo, context.code_state["branch"], [], None)["sha"]
    if code_tip != context.code_state["sha"]:
        raise ValueError("origin の code base が捕捉した SHA から移動しました")
    if context.docs_separate and context.docs_state is not None:
        docs_tip = resolve_base(
            context.parent_root, context.docs_repo, context.docs_state["branch"], [], None)["sha"]
        if docs_tip != context.docs_state["sha"]:
            raise ValueError("origin の docs base が捕捉した SHA から移動しました")


def _write_log(path: Path, data: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags, 0o600)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(data)


def _reverify(args: argparse.Namespace) -> dict[str, object]:
    context = _context(args.session)
    doc_root = _doc_root(args, context)
    required, required_bytes = _read_required(context.session, context.docs_separate)
    if args.commands_file is not None:
        supplied = _normalize_commands(
            _read_json(args.commands_file, "verify-cmds.json"), context.docs_separate,
            allow_shorthand=True)
        if supplied != required:
            raise ValueError("--commands-file が固定済みの必須検証コマンドと一致しません")
    if not context.advances:
        raise ValueError("base 前進の記録が無いため再検証できません")
    code_root = args.code_root.expanduser()
    code_head = _verify_worktree_clean(code_root, context.target_root, context.code_state["sha"])
    docs_head = None
    if context.docs_separate:
        if context.docs_state is None:
            raise ValueError("docs の base 状態がありません")
        docs_head = _verify_worktree_clean(
            doc_root, context.parent_root, context.docs_state["sha"])
    _verify_remote_state(context)
    _remove_any(context.session / "reverified.json")
    _remove_any(context.session / "checks.json")
    cwd_map = {"code": code_root, "docs": doc_root, "parent": context.parent_root}
    logs: list[tuple[Path, str]] = []
    try:
        for index, command in enumerate(required, 1):
            log = context.session / f"reverify-{index}.log"
            if log.is_symlink() or (log.exists() and not log.is_file()):
                raise ValueError(f"再検証ログ {log.name} が通常ファイルではありません")
            try:
                completed = subprocess.run(
                    list(command["argv"]), cwd=cwd_map[str(command["cwd"])],
                    env=git_environment(transport_auth=False), capture_output=True, timeout=3600,
                )
            except (OSError, subprocess.TimeoutExpired) as exc:
                raise ValueError(f"再検証コマンド {index} を実行できませんでした") from exc
            output = (completed.stdout or b"") + (completed.stderr or b"")
            _write_log(log, output)
            if completed.returncode:
                raise ValueError(f"再検証コマンド {index} が終了コード {completed.returncode} で失敗しました")
            logs.append((log, _sha256(log.read_bytes())))
        if _read_bytes(context.session / "required-verify-cmds.json",
                       "required-verify-cmds.json") != required_bytes:
            raise ValueError("再検証中に必須検証コマンドが変更されました")
        _verify_remote_state(context)
        if _verify_worktree_clean(code_root, context.target_root, context.code_state["sha"]) != code_head:
            raise ValueError("再検証中に code worktree の HEAD が変化しました")
        if context.docs_separate:
            if context.docs_state is None:
                raise ValueError("docs の base 状態がありません")
            if _verify_worktree_clean(
                doc_root, context.parent_root, context.docs_state["sha"]) != docs_head:
                raise ValueError("再検証中に docs worktree の HEAD が変化しました")
    except BaseException:
        # A command may have written these names itself; a failed run must not leave a passing record.
        for name in ("reverified.json", "checks.json"):
            try:
                _remove_any(context.session / name)
            except OSError:
                pass
        raise
    commands: list[dict[str, object]] = []
    for command, (log, log_sha) in zip(required, logs):
        commands.append({
            "cwd": command["cwd"], "argv": command["argv"], "exit_code": 0,
            "log_path": str(log), "log_sha256": log_sha,
        })
    reverified: dict[str, object] = {
        "docs_separate": context.docs_separate,
        "advance_count": len(context.advances),
        "code_base_sha": context.code_state["sha"],
        "code_head_sha": code_head,
        "doc_base_sha": context.docs_state["sha"] if context.docs_state is not None else None,
        "doc_head_sha": docs_head,
        "required_verify_sha256": _sha256(required_bytes),
        "commands": commands,
    }
    checks = {
        "head": code_head,
        "base": context.code_state["sha"],
        "commands": [{"argv": command["argv"], "exit_code": 0} for command in required],
    }
    _replace_files([
        (context.session / "reverified.json", _json_bytes(reverified)),
        (context.session / "checks.json", _json_bytes(checks)),
    ])
    return reverified


def _unadvanced(context: Context) -> bool:
    if (context.session / "base-advances.jsonl").exists():
        return False
    if context.code_state["sha"] != context.code_initial["sha"]:
        return False
    if context.docs_separate:
        return (
            context.docs_state is not None and context.docs_initial is not None
            and context.docs_state["sha"] == context.docs_initial["sha"]
        )
    return True


def _check_publish(args: argparse.Namespace) -> tuple[Context, dict[str, object], list[dict[str, object]]]:
    context = _context(args.session)
    if _unadvanced(context):
        return context, {}, []
    if not context.advances:
        raise ValueError("base 前進の記録がありません")
    _verify_remote_state(context)
    required, required_bytes = _read_required(context.session, context.docs_separate)
    payload = _read_json(context.session / "reverified.json", "reverified.json")
    if not isinstance(payload, dict):
        raise ValueError("reverified.json がオブジェクトではありません")
    if payload.get("docs_separate") is not context.docs_separate:
        raise ValueError("reverified.json の文書分離設定が現在の設定と一致しません")
    if (
        type(payload.get("advance_count")) is not int
        or payload["advance_count"] != len(context.advances)
    ):
        raise ValueError("reverified.json の前進回数が記録と一致しません")
    if payload.get("required_verify_sha256") != _sha256(required_bytes):
        raise ValueError("reverified.json の必須検証コマンド SHA-256 が一致しません")
    if payload.get("code_base_sha") != context.code_state["sha"]:
        raise ValueError("reverified.json の code base SHA が一致しません")
    commands = payload.get("commands")
    if not isinstance(commands, list) or len(commands) != len(required):
        raise ValueError("reverified.json の検証コマンド一覧が一致しません")
    for item, expected in zip(commands, required):
        if not isinstance(item, dict) or set(item) != {
            "cwd", "argv", "exit_code", "log_path", "log_sha256",
        }:
            raise ValueError("reverified.json の検証コマンドの項目が不正です")
        if item["cwd"] != expected["cwd"] or item["argv"] != expected["argv"]:
            raise ValueError("reverified.json の検証コマンドが固定値と一致しません")
        if type(item["exit_code"]) is not int or item["exit_code"] != 0:
            raise ValueError("reverified.json の検証コマンドが成功していません")
        log_path = item["log_path"]
        log_sha = item["log_sha256"]
        if not isinstance(log_path, str) or not isinstance(log_sha, str) or SHA256.fullmatch(log_sha) is None:
            raise ValueError("reverified.json のログ情報が不正です")
        log = Path(log_path)
        if not log.is_absolute():
            raise ValueError("reverified.json のログが絶対パスではありません")
        if log.is_symlink() or not log.is_file() or log.resolve(strict=True).parent != context.session:
            raise ValueError("reverified.json のログが session 内の通常ファイルではありません")
        if _sha256(log.read_bytes()) != log_sha:
            raise ValueError("reverified.json のログ SHA-256 が一致しません")
    code_head = _verify_worktree_clean(
        args.code_root.expanduser(), context.target_root, context.code_state["sha"])
    if payload.get("code_head_sha") != code_head:
        raise ValueError("reverified.json の code HEAD が現在の worktree と一致しません")
    if context.docs_separate:
        if context.docs_state is None:
            raise ValueError("docs の base 状態がありません")
        docs_head = _verify_worktree_clean(
            _doc_root(args, context), context.parent_root, context.docs_state["sha"])
        if payload.get("doc_base_sha") != context.docs_state["sha"]:
            raise ValueError("reverified.json の docs base SHA が一致しません")
        if payload.get("doc_head_sha") != docs_head:
            raise ValueError("reverified.json の docs HEAD が現在の worktree と一致しません")
    else:
        if (
            "doc_base_sha" not in payload or "doc_head_sha" not in payload
            or payload["doc_base_sha"] is not None or payload["doc_head_sha"] is not None
        ):
            raise ValueError("文書分離でない run の reverified.json に docs の値があります")
    return context, payload, required


def _check_publish_gate(args: argparse.Namespace) -> None:
    _check_publish(args)


def _pr_body(value: str, label: str) -> str:
    """Accept either the body text or a path to it; the shell variables may hold either."""
    if not value:
        return value
    candidate = Path(value).expanduser()
    if candidate.is_symlink():
        raise ValueError(f"{label} が symlink です")
    if "\n" not in value and candidate.is_file():
        return _read_text(candidate, label)
    looks_like_path = (
        "/" in value or "\\" in value or value.startswith((".", "~"))
        or (candidate.suffix.lower() in (".md", ".txt", ".json") and " " not in value)
    )
    if "\n" not in value and looks_like_path:
        raise ValueError(f"{label} のファイルが存在しません")
    return value


def _body_has_sha(body: str, sha: str) -> bool:
    return any(sha.startswith(token) for token in HEX_TOKEN.findall(body))


def _check_pr_gate(args: argparse.Namespace) -> None:
    context, payload, required = _check_publish(args)
    if _unadvanced(context):
        return
    code_sha = _read_text(context.session / "code-sha.txt", "code-sha.txt").strip()
    if code_sha != payload.get("code_head_sha"):
        raise ValueError("code-sha.txt が再検証した HEAD と一致しません")
    if context.docs_separate:
        docs_sha = _read_text(context.session / "docs-sha.txt", "docs-sha.txt").strip()
        if docs_sha != payload.get("doc_head_sha"):
            raise ValueError("docs-sha.txt が再検証した HEAD と一致しません")
    if args.code_pr_body is None:
        raise ValueError("--code-pr-body が必要です")
    if context.docs_separate and not args.doc_pr_body:
        raise ValueError("文書分離の run では --doc-pr-body が必要です")
    code_body = _read_text(args.code_pr_body, "code-pr-body")
    doc_body = _pr_body(args.doc_pr_body, "doc-pr-body")
    if context.docs_separate and not doc_body.strip():
        raise ValueError("--doc-pr-body が空です")
    for record in context.advances:
        body = code_body if record["target"] == "code" else doc_body
        old_sha, new_sha = str(record["old_sha"]), str(record["new_sha"])
        if not _body_has_sha(body, old_sha) or not _body_has_sha(body, new_sha):
            raise ValueError("PR 本文に base 前進の旧/新 SHA の記載がありません")
    for command in required:
        argv = command["argv"]
        if not isinstance(argv, list):
            raise ValueError("必須検証コマンドの形式が不正です")
        if " ".join(str(argument) for argument in argv) not in code_body and shlex.join(
            [str(argument) for argument in argv]
        ) not in code_body:
            raise ValueError("PR 本文に必須検証コマンドの記載がありません")


def _require_argument(value: object, name: str) -> None:
    if value is None or (isinstance(value, str) and not value):
        raise ValueError(f"{name} が必要です")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", type=Path)
    parser.add_argument("--repo")
    parser.add_argument("--base")
    parser.add_argument("--required-base", action="append", default=[])
    parser.add_argument("--expected-sha")
    parser.add_argument("--write-state", type=Path)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--inspect-advance", action="store_true")
    modes.add_argument("--advance", action="store_true")
    modes.add_argument("--set-verify-cmds", action="store_true")
    modes.add_argument("--reverify", action="store_true")
    modes.add_argument("--check-publish-gate", action="store_true")
    modes.add_argument("--check-pr-gate", action="store_true")
    parser.add_argument("--session", type=Path)
    parser.add_argument("--owned-paths-file", type=Path)
    parser.add_argument("--code-root", type=Path)
    parser.add_argument("--code-branch")
    parser.add_argument("--doc-root", type=Path)
    parser.add_argument("--doc-branch", default="")
    parser.add_argument("--max-advances", type=int, default=3)
    parser.add_argument("--inspection", type=Path)
    parser.add_argument("--premise-file", type=Path)
    parser.add_argument("--commands-file", type=Path)
    parser.add_argument("--code-pr-body", type=Path)
    parser.add_argument("--doc-pr-body", default="")
    args = parser.parse_args(argv)
    try:
        mode = any((
            args.inspect_advance, args.advance, args.set_verify_cmds, args.reverify,
            args.check_publish_gate, args.check_pr_gate,
        ))
        if mode:
            if (
                args.write_state is not None or args.checkout is not None or args.repo is not None
                or args.base is not None or args.required_base or args.expected_sha is not None
            ):
                raise ValueError("前進の各モードは base の捕捉引数と同時に指定できません")
            _require_argument(args.session, "--session")
            if args.inspect_advance or args.advance:
                _require_argument(args.owned_paths_file, "--owned-paths-file")
                _require_argument(args.code_root, "--code-root")
                _require_argument(args.code_branch, "--code-branch")
                if args.advance:
                    _require_argument(args.inspection, "--inspection")
                    _require_argument(args.premise_file, "--premise-file")
                payload: object | None = _inspection(args).payload if args.inspect_advance else None
                if args.advance:
                    payload = _advance(args)
            elif args.set_verify_cmds:
                _require_argument(args.commands_file, "--commands-file")
                _set_verify_cmds(args)
                payload = None
            elif args.reverify:
                _require_argument(args.code_root, "--code-root")
                payload = _reverify(args)
            elif args.check_publish_gate:
                _require_argument(args.code_root, "--code-root")
                _check_publish_gate(args)
                payload = None
            else:
                _require_argument(args.code_root, "--code-root")
                _check_pr_gate(args)
                payload = None
        else:
            _require_argument(args.checkout, "--checkout")
            _require_argument(args.repo, "--repo")
            if args.write_state is not None:
                _write_state_target(args.write_state)
            payload = resolve_base(
                args.checkout, args.repo, args.base, args.required_base, args.expected_sha)
            if args.write_state is not None:
                _write_state(args.write_state, payload)
                payload = None
        if payload is not None:
            print(json.dumps(payload, ensure_ascii=False))
        return 0
    except (ValueError, OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
        # OSError/TimeoutExpired may contain command arguments; do not echo them.
        message = str(exc) if isinstance(exc, ValueError) else "Git、checkout、または状態ファイルの読み取りに失敗しました"
        print(f"issue-to-pr base: {message}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
