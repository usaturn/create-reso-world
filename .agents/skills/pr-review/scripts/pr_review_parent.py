"""Immutable, credential-free PR inputs prepared by the authenticated controller."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
from pathlib import Path
from types import ModuleType
from typing import Any, cast

SHA = re.compile(r"[0-9a-f]{40}")
DIGEST = re.compile(r"[0-9a-f]{64}")


def regular_bytes(path: Path, *, limit: int = 512 * 1024 * 1024) -> bytes:
    """Read once through anchored directory descriptors; never follow links or block on a FIFO."""
    if not path.is_absolute() or any(p in {".", ".."} for p in path.parts):
        raise ValueError("parent review input must be a canonical regular file")
    directory = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in path.parts[1:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
            os.close(directory)
            directory = child
        descriptor = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        with os.fdopen(descriptor, "rb") as stream:
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > limit:
                raise ValueError("parent review input must be a bounded, singly linked regular file")
            raw = stream.read(limit + 1)
            after = os.fstat(stream.fileno())
            if len(raw) > limit or (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (after.st_size, after.st_mtime_ns, after.st_ctime_ns):
                raise ValueError("parent review input changed while reading")
            return raw
    finally:
        os.close(directory)


def digest(path: Path) -> str:
    return hashlib.sha256(regular_bytes(path)).hexdigest()


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate parent review input key")
        result[key] = value
    return result


def object_value(value: Any, label: str) -> dict[str, Any]:
    """Reject malformed child-owned JSON before accessing nested fields."""
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value


def parameters_from_prompt(prompt: str) -> dict[str, Any]:
    try:
        parameters = json.loads(
            prompt.rsplit("```json\n", 1)[1].split("\n```", 1)[0],
            object_pairs_hook=unique_object,
        )
        if not isinstance(parameters, dict):
            raise ValueError("Request parameters must be a JSON object")
        return cast(dict[str, Any], parameters)
    except IndexError as error:
        raise ValueError(
            "DSH review requires parent parameters in Request.prompt"
        ) from error


def descriptor_from_prompt(prompt: str) -> dict[str, str]:
    try:
        descriptor = parameters_from_prompt(prompt)["parent_pr_data"]
        if set(descriptor) != {"path", "sha256"} or not all(
            isinstance(v, str) for v in descriptor.values()
        ):
            raise ValueError("invalid parent review descriptor")
        if DIGEST.fullmatch(descriptor["sha256"]) is None:
            raise ValueError("invalid parent review digest")
        return descriptor
    except (KeyError, IndexError, TypeError) as error:
        raise ValueError(
            "DSH review requires trusted parent_pr_data in Request.prompt"
        ) from error


def load(workspace: ModuleType, descriptor: dict[str, str], pr: str) -> dict[str, Any]:
    path = Path(descriptor["path"])
    raw = regular_bytes(path)
    if hashlib.sha256(raw).hexdigest() != descriptor["sha256"]:
        raise ValueError("parent PR snapshot changed")
    loaded = json.loads(raw, object_pairs_hook=unique_object)
    if not isinstance(loaded, dict):
        raise ValueError("invalid parent PR snapshot")
    document = cast(dict[str, Any], loaded)
    if (
        set(document)
        != {
            "schema",
            "target",
            "base",
            "review_commit",
            "comments",
            "bundle_sha256",
            "requirements",
        }
        or document["schema"] != "pr-review-parent/v1"
    ):
        raise ValueError("invalid parent PR snapshot")
    target = workspace.parse_target(json.dumps(document["target"]))
    with workspace.target_errors() as helper:
        pull = helper.PullRequest(
            **{key: target[key] for key in helper.PullRequest._fields}
        )
        parsed = helper.parse_pull_request_argument(pr)
        if parsed.number != pull.number or (
            parsed.repository is not None
            and not helper.same_repository(parsed.repository, pull.repository)
        ):
            raise ValueError("parent snapshot belongs to another PR")
        helper.require_parent_root(Path(target["parent_root"]))
    if SHA.fullmatch(str(document["base"])) is None or not target.get("base_ref"):
        raise ValueError("invalid parent PR base")
    commit = document["review_commit"]
    if commit is not None and (
        not isinstance(commit, str) or SHA.fullmatch(commit) is None
    ):
        raise ValueError("invalid parent review commit")
    bundle = path.with_name("objects.bundle")
    if digest(bundle) != document["bundle_sha256"]:
        raise ValueError("parent PR bundle changed")
    return {
        **document,
        "target": target,
        "bundle": str(bundle),
        "descriptor": descriptor,
    }


def prepare(
    workspace: ModuleType, args: Any, comments: Any, requirements: Any
) -> dict[str, str]:
    parent_value = getattr(args, "parent_root", None)
    parent = (
        Path(parent_value)
        if parent_value
        else workspace._target_call("default_parent_root")
    )
    api_runner = getattr(args, "api_runner", None)
    api_args = {"runner": api_runner} if api_runner is not None else {}
    target = workspace._target_call(
        "resolve",
        args.pr,
        parent_root=parent,
        code_root=Path(args.source_root) if args.source_root else None,
        **api_args,
    )
    workspace.artifact_model("parent-input", args.review_commit)
    directory = Path(args.output_dir).absolute()
    if directory.resolve(strict=False) != directory:
        raise ValueError("parent input directory must be canonical")
    # An existing directory is never ours to replace; refuse it before creating anything.
    directory.mkdir(mode=0o700)
    try:
        return _populate(
            workspace, args, target, directory, comments, requirements, api_args
        )
    except BaseException:
        # Only this call created the directory; leave nothing that blocks a retry of the same cycle.
        shutil.rmtree(directory, ignore_errors=True)
        raise


def _populate(
    workspace: ModuleType,
    args: Any,
    target: dict[str, Any],
    directory: Path,
    comments: Any,
    requirements: Any,
    api_args: dict[str, Any],
) -> dict[str, str]:
    source = directory / "repo"
    checkout = workspace.require_target_checkout(
        Path(args.source_root or target["target_root"]),
        target["repository"],
        Path(target["parent_root"]),
    )
    resolved = workspace._target_call(
        "target_checkout",
        Path(target["parent_root"]),
        target["repository"],
        code_root=checkout,
    )
    if resolved.remote != target["base_remote"]:
        raise ValueError("target base remote changed during parent preparation")
    # Start with an empty owned Git repository. Fetch from the validated remote,
    # not the user's potentially shallow checkout; never unshallow their Git data.
    workspace.git(directory, "init", "--quiet", str(source))
    remote = target["base_remote"]
    remote_url = workspace.git(checkout, "config", "--get", f"remote.{remote}.url")
    workspace.git(source, "remote", "add", remote, remote_url)
    with workspace.target_errors() as helper:
        head_ref = helper.fetch_pull_head(
            source,
            target["repository"],
            target["number"],
            target["head_sha"],
            remote=remote,
        )
    base_ref = "refs/pr-review-parent/base"
    workspace.git(
        source,
        "fetch",
        "--quiet",
        "--no-write-fetch-head",
        "--no-tags",
        "--refmap=",
        remote,
        f"+refs/heads/{target['base_ref']}:{base_ref}",
    )
    commit = args.review_commit or target["head_sha"]
    if args.review_commit:
        workspace.git(
            source,
            "fetch",
            "--quiet",
            "--no-write-fetch-head",
            "--no-tags",
            "--refmap=",
            str(checkout),
            commit,
        )
    workspace.require_review_commit(source, commit)
    commit_ref = "refs/pr-review-parent/commit"
    workspace.git(source, "update-ref", commit_ref, commit)
    base = workspace.git(source, "merge-base", base_ref, commit)
    current = workspace._target_call(
        "fetch_pull_request", target["repository"], target["number"], **api_args
    )
    if current.head_sha != target["head_sha"]:
        raise ValueError("PR head changed during parent preparation")
    bundle = directory / "objects.bundle"
    workspace.git(
        source, "bundle", "create", str(bundle), head_ref, base_ref, commit_ref
    )
    validation = directory / "bundle-check"
    workspace.git(source, "init", "--quiet", str(validation))
    workspace.git(
        validation,
        "fetch",
        "--quiet",
        "--no-write-fetch-head",
        str(bundle),
        f"+{head_ref}:{head_ref}",
        f"+{base_ref}:{base_ref}",
        f"+{commit_ref}:{commit_ref}",
    )
    shutil.rmtree(validation)
    document = {
        "schema": "pr-review-parent/v1",
        "target": target,
        "base": base,
        "review_commit": args.review_commit,
        "comments": comments,
        "bundle_sha256": digest(bundle),
        "requirements": requirements,
    }
    snapshot = directory / "snapshot.json"
    snapshot.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    shutil.rmtree(source)
    bundle.chmod(0o444)
    snapshot.chmod(0o444)
    return {"path": str(snapshot), "sha256": digest(snapshot)}
