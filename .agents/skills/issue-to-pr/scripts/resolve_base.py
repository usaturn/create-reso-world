"""Resolve an exact origin heads ref to a verified commit without changing local branches.

Only objects are fetched. No branch, index, worktree, remote-tracking ref or
FETCH_HEAD is updated. A captured SHA can be checked again before later writes.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

from resolve_issue import ORIGIN_URL, git_environment, require_tracked_cwd, supported, validate_branch

SHA = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})")


def git(checkout: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=checkout, env=git_environment(),
        capture_output=True, text=True, timeout=60,
    )
    if result.returncode:
        # A transport error may contain credentials even when get-url was safe.
        raise ValueError(f"git {args[0]} に失敗しました（詳細は認証情報保護のため省略）")
    return result.stdout.strip()


def require_origin(checkout: Path, repo: str) -> None:
    for options in (("--all",), ("--push", "--all")):
        urls = git(checkout, "remote", "get-url", *options, "origin").splitlines()
        if not urls or any(
            (match := ORIGIN_URL.fullmatch(url)) is None or match[1].casefold() != repo for url in urls
        ):
            raise ValueError("origin の fetch/push URL が指定した repository と一致しません")


def remote_sha(checkout: Path, ref: str) -> str:
    response = git(checkout, "ls-remote", "--exit-code", "--refs", "origin", ref)
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
    branch = validate_branch(base if base is not None else "main", checkout)
    for required in required_bases:
        validate_branch(required, checkout)
        if base is None or branch != required:
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
    git(checkout, "fetch", "--no-tags", "--no-write-fetch-head", "--refmap=", "origin", ref)
    if remote_sha(checkout, ref) != sha:
        raise ValueError("origin の base が取得中に移動しました")
    if git(checkout, "cat-file", "-t", sha) != "commit":
        raise ValueError("origin の base は commit ではありません")
    return {"repo": repo, "remote": "origin", "branch": branch, "ref": ref, "sha": sha}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", required=True, type=Path)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--base")
    parser.add_argument("--required-base", action="append", default=[])
    parser.add_argument("--expected-sha")
    args = parser.parse_args(argv)
    try:
        payload = resolve_base(args.checkout, args.repo, args.base, args.required_base, args.expected_sha)
    except (ValueError, OSError, subprocess.TimeoutExpired) as exc:
        # OSError/TimeoutExpired may contain command arguments; do not echo them.
        message = str(exc) if isinstance(exc, ValueError) else "Git または checkout の読み取りに失敗しました"
        print(f"issue-to-pr base: {message}", file=sys.stderr)
        return 2
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
