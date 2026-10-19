"""Fixed DSH review paths and verified parent inputs exposed read-only."""

import hashlib
import json
import os
import re
import stat
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import cast

from tools.agent_runner.dsh_sandbox import grant_path


def review_scratch(attempt_dir: Path) -> Path:
    """Helper-owned staging, outside the redacted DSH runtime tree."""
    return attempt_dir / "review-scratch"


def review_exports(attempt_dir: Path) -> Path:
    """Native-tool review output, imported only after the runtime has stopped."""
    return attempt_dir / "dsh" / "tmp" / "exports"


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate parent input key")
        result[key] = value
    return result


def _constant(_value: str) -> object:
    raise ValueError("nonfinite parent input")


def _regular_bytes(path: Path) -> bytes:
    """Match the parent's bounded single-link input rule without following links."""
    grant_path(str(path))
    directory = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in path.parts[1:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
            os.close(directory)
            directory = child
        descriptor = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        with os.fdopen(descriptor, "rb") as stream:
            before = os.fstat(stream.fileno())
            limit = 512 * 1024 * 1024
            if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > limit:
                raise ValueError("invalid parent input file")
            raw = stream.read(limit + 1)
            after = os.fstat(stream.fileno())
            if len(raw) > limit or (
                before.st_size, before.st_mtime_ns, before.st_ctime_ns
            ) != (after.st_size, after.st_mtime_ns, after.st_ctime_ns):
                raise ValueError("parent input changed while reading")
            return raw
    finally:
        os.close(directory)


def _parent_checkout(path: Path, environment: Mapping[str, str]) -> None:
    grant_path(str(path))
    if path in {Path("/"), Path("/tmp")} or not path.is_dir():
        raise ValueError("invalid parent checkout")
    env = {name: value for name, value in environment.items() if not name.startswith("GIT_")}
    check = subprocess.run(
        ["git", "--no-optional-locks", "-C", str(path), "rev-parse", "--path-format=absolute",
         "--show-toplevel", "--git-common-dir"],
        env=env, capture_output=True, check=False, timeout=10,
    )
    if check.returncode or check.stdout.decode().splitlines() != [str(path), str(path / ".git")]:
        raise ValueError("parent input requires a main checkout")
    ignored = subprocess.run(
        ["git", "--no-optional-locks", "-C", str(path), "check-ignore", "-q", "reviews/.review-target-probe"],
        env=env, capture_output=True, check=False, timeout=10,
    )
    if ignored.returncode:
        raise ValueError("parent checkout must ignore reviews")


def parent_review_read_paths(prompt: str, environment: Mapping[str, str]) -> tuple[Path, ...]:
    """Verify the Request-bound snapshot/bundle before exposing their fixed paths.

    Ordinary DSH requests need no review descriptor. A parsed final parameter
    object's top-level parent_pr_data selects this check; invalid descriptors or
    changed inputs refuse launch. The parent checkout is needed by the helper's
    require_parent_root check, never for writes.
    """
    if "```json\n" not in prompt:
        return ()
    try:
        raw_parameters = prompt.rsplit("```json\n", 1)[1].split("\n```", 1)[0]
        try:
            parameters = json.loads(raw_parameters, object_pairs_hook=_unique_object, parse_constant=_constant)
        except ValueError:
            return ()
        if not isinstance(parameters, dict) or "parent_pr_data" not in parameters:
            return ()
        descriptor = parameters["parent_pr_data"]
        if (
            not isinstance(descriptor, dict) or set(descriptor) != {"path", "sha256"}
            or not isinstance(descriptor["path"], str) or not isinstance(descriptor["sha256"], str)
            or re.fullmatch(r"[0-9a-f]{64}", descriptor["sha256"]) is None
        ):
            raise ValueError("invalid parent input descriptor")
        snapshot = Path(descriptor["path"])
        if snapshot.name != "snapshot.json":
            raise ValueError("invalid parent input filename")
        raw = _regular_bytes(snapshot)
        if hashlib.sha256(raw).hexdigest() != descriptor["sha256"]:
            raise ValueError("parent snapshot digest changed")
        document = json.loads(raw, object_pairs_hook=_unique_object, parse_constant=_constant)
        if (
            not isinstance(document, dict)
            or set(document) != {"schema", "target", "base", "review_commit", "comments", "bundle_sha256", "requirements"}
            or document["schema"] != "pr-review-parent/v1" or not isinstance(document["target"], dict)
            or not isinstance(document["target"].get("parent_root"), str)
            or not isinstance(document["bundle_sha256"], str)
            or re.fullmatch(r"[0-9a-f]{64}", document["bundle_sha256"]) is None
        ):
            raise ValueError("invalid parent snapshot")
        target = cast(dict[str, object], document["target"])
        parent = Path(cast(str, target["parent_root"]))
        _parent_checkout(parent, environment)
        bundle = snapshot.with_name("objects.bundle")
        if hashlib.sha256(_regular_bytes(bundle)).hexdigest() != document["bundle_sha256"]:
            raise ValueError("parent bundle digest changed")
        return snapshot, bundle, parent
    except (IndexError, KeyError, TypeError, OSError, UnicodeError, subprocess.SubprocessError) as error:
        raise ValueError("invalid parent review inputs") from error
