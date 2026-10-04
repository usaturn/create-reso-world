#!/usr/bin/env python3
"""Publish an immutable, non-replacing review copy of a committed document.

Reads the exact blob of a committed Spec/Plan from DOC_ROOT and publishes it in
the parent checkout's ignored `tmp/superpowers-review/` directory.  Publication
never replaces an existing entry: a completed temporary file in the destination
directory is published with `os.link`, which fails when the destination name is
already taken.  An existing regular destination with identical bytes reports
`unchanged`; differing bytes, a directory, a symlink or a special file are left
untouched and rejected with a versioned-name suggestion.  `--replace-from` is
rejected with a migration message before any filesystem access.

使い方:
    scripts/superpowers-review-copy.sh --doc-root DOC_ROOT --parent-root PARENT_ROOT \
        --path docs/superpowers/{specs,plans}/NAME.md --name TOPIC-spec.md [--commit REV]

Root/remote validation is delegated to the adjacent shared module
`superpowers_context.py` (operation `review-copy`).
"""
from __future__ import annotations

import argparse
import errno
import hashlib
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from superpowers_context import ContextError, resolve_context

REVIEW_DIR = "tmp/superpowers-review"
NAME_RE = re.compile(r"^([a-z0-9][a-z0-9.-]*)-(spec|plan)[.]md$")
KINDS = {"specs": "spec", "plans": "plan"}


class CopyError(ValueError):
    """An expected rejection that leaves every destination entry untouched."""


def document_kind(rel: str) -> str | None:
    """Return spec/plan for a canonical committed document path, else None."""
    parts = PurePosixPath(rel).parts
    if len(parts) != 4 or parts[:2] != ("docs", "superpowers") or parts[2] not in KINDS:
        return None
    name = parts[3]
    if name.startswith(".") or not name.endswith(".md"):
        return None
    return KINDS[parts[2]]


def validate_name(name: str, kind: str) -> str:
    match = NAME_RE.fullmatch(name)
    if not match:
        raise CopyError(
            f"--name must be a short lowercase file name ending in -spec.md or -plan.md: {name}")
    if match.group(2) != kind:
        raise CopyError(f"--name ends in -{match.group(2)}.md but --path is a {kind}")
    return name


def git(doc_root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(doc_root), *args], capture_output=True)


def resolve_commit(doc_root: Path, rev: str) -> str:
    result = git(doc_root, "rev-parse", "--verify", "--quiet", f"{rev}^{{commit}}")
    if result.returncode:
        raise CopyError(f"--commit is not a commit in {doc_root}: {rev}")
    return result.stdout.decode().strip()


def committed_blob(doc_root: Path, commit: str, rel: str) -> str:
    result = git(doc_root, "ls-tree", commit, "--", rel)
    lines = result.stdout.decode().splitlines()
    if not lines:
        raise CopyError(f"{rel} is not committed in {commit}")
    fields = lines[0].split(None, 3)
    if fields[0] not in ("100644", "100755") or len(fields) < 3 or fields[1] != "blob":
        raise CopyError(f"{rel} is not a regular file in {commit}")
    return fields[2]


def require_clean_against_commit(doc_root: Path, commit: str, rel: str) -> None:
    for index_flag in ([], ["--cached"]):
        result = git(doc_root, "diff", "--quiet", *index_flag, commit, "--", rel)
        if result.returncode:
            raise CopyError(f"{rel} in {doc_root} differs from {commit}; commit it first")


def read_blob(doc_root: Path, blob: str) -> bytes:
    result = git(doc_root, "cat-file", "blob", blob)
    if result.returncode:
        raise CopyError(f"cannot read the committed blob {blob}: {result.stderr.decode().strip()}")
    return result.stdout


def require_ignored(parent_root: Path, dest_rel: str) -> None:
    result = subprocess.run(["git", "-C", str(parent_root), "check-ignore", "-q", "--", dest_rel])
    if result.returncode:
        raise CopyError(f"{dest_rel} is not ignored in {parent_root}")


def ensure_review_directory(parent_root: Path, dest_rel: str) -> Path:
    """Create the ignored review directory without following symlinks."""
    review = parent_root / REVIEW_DIR
    for path in (parent_root / "tmp", review):
        try:
            info = path.lstat()
        except FileNotFoundError:
            continue
        except OSError as exc:
            raise CopyError(f"cannot inspect {path}: {exc}") from exc
        if stat.S_ISLNK(info.st_mode):
            raise CopyError(f"{path} is a symlink")
        if not stat.S_ISDIR(info.st_mode):
            raise CopyError(f"{path} is not a directory")
    require_ignored(parent_root, dest_rel)
    try:
        review.mkdir(parents=True, exist_ok=True)
        if Path(os.path.realpath(review, strict=True)) != review:
            raise CopyError(f"{review} resolves outside the parent checkout")
    except OSError as exc:
        raise CopyError(f"cannot prepare {review}: {exc}") from exc
    return review


def read_existing(dest: Path, dest_rel: str) -> bytes:
    """Safely read an existing destination without following symlinks or blocking."""
    try:
        fd = os.open(dest, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except OSError as exc:
        if exc.errno in (errno.ELOOP, errno.EMLINK):
            raise CopyError(f"{dest_rel} is a symlink") from exc
        raise CopyError(f"cannot read the existing {dest_rel}: {exc}") from exc
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            if stat.S_ISDIR(info.st_mode):
                kind = "a directory"
            elif stat.S_ISFIFO(info.st_mode):
                kind = "a FIFO"
            else:
                kind = "a special file"
            raise CopyError(
                f"{dest_rel} is not a regular file (it is {kind}); choose another name, "
                "for example a new versioned name ending in -r2-spec.md or -r2-plan.md")
        chunks = []
        while True:
            chunk = os.read(fd, 1 << 20)
            if not chunk:
                return b"".join(chunks)
            chunks.append(chunk)
    finally:
        os.close(fd)


def suggest_versioned(name: str) -> str:
    return re.sub(r"-(spec|plan)[.]md$", r"-r2-\g<1>.md", name)


def publish(staged: Path, dest: Path, dest_rel: str, content: bytes, name: str) -> str:
    """Publish by hard link only; never replace, rename or delete a destination."""
    try:
        os.link(staged, dest)
    except OSError as exc:
        if exc.errno != errno.EEXIST:
            raise CopyError(f"publishing {dest_rel} failed: {exc}") from exc
        existing = read_existing(dest, dest_rel)
        if existing != content:
            raise CopyError(
                f"{dest_rel} already exists with other content; it was never replaced. "
                f"Publish the new version under a versioned name such as {suggest_versioned(name)}; "
                "the existing copy and any annotations stay untouched") from None
        return "unchanged"
    return "created"


def run(args: argparse.Namespace) -> int:
    try:
        context = resolve_context("review-copy", parent_root=args.parent_root, doc_root=args.doc_root)
    except ContextError as exc:
        # Keep this entrypoint's flag-shaped diagnostics for root validation.
        message = str(exc).replace("PARENT_ROOT", "--parent-root").replace("DOC_ROOT", "--doc-root")
        raise CopyError(message) from exc
    parent_root = Path(context["parent_root"])
    doc_root = Path(context["doc_root"])

    kind = document_kind(args.path)
    if not kind:
        raise CopyError(
            f"--path must be docs/superpowers/specs/*.md or docs/superpowers/plans/*.md: {args.path}")
    validate_name(args.name, kind)

    commit = resolve_commit(doc_root, args.commit)
    blob = committed_blob(doc_root, commit, args.path)
    require_clean_against_commit(doc_root, commit, args.path)
    content = read_blob(doc_root, blob)

    dest_rel = f"{REVIEW_DIR}/{args.name}"
    review = ensure_review_directory(parent_root, dest_rel)
    dest = review / args.name

    try:
        fd, staged_name = tempfile.mkstemp(dir=review, prefix=f".{args.name}.")
        staged = Path(staged_name)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(content)
                handle.flush()
                os.fchmod(handle.fileno(), 0o644)
            status = publish(staged, dest, dest_rel, content, args.name)
            if status == "created" and read_existing(dest, dest_rel) != content:
                # Never delete or rewrite the entry: it may belong to another actor.
                raise CopyError(
                    f"{dest_rel} does not match {args.path} at {commit} after copying; "
                    "investigate it without deleting or rewriting the destination")
        finally:
            # Only this invocation's temporary file is removed; never a destination.
            try:
                os.unlink(staged)
            except FileNotFoundError:
                pass
    except OSError as exc:
        raise CopyError(f"cannot publish {dest_rel} in {review}: {exc}") from exc

    print(f"{status}: {dest_rel}")
    print(f"source: {args.path} at {commit}")
    print(f"sha256: {hashlib.sha256(content).hexdigest()}")
    return 0


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Publish an immutable, non-replacing review copy of a committed document")
    parser.add_argument("--doc-root", required=True,
                        help="DOC_ROOT: the create-reso-world checkout that commits the document")
    parser.add_argument("--parent-root", required=True,
                        help="PARENT_ROOT: the create-reso-world main checkout the user reads")
    parser.add_argument("--path", required=True,
                        help="committed document path relative to DOC_ROOT")
    parser.add_argument("--name", required=True,
                        help="review copy file name ending in -spec.md or -plan.md")
    parser.add_argument("--commit", default="HEAD", help="document revision to copy (default: HEAD)")
    parser.add_argument("--replace-from", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.replace_from is not None:
        parser.error(
            "--replace-from was removed: reviewed copies are never replaced. Publish the new "
            "version under a versioned name (for example TOPIC-r2-spec.md); old copies and "
            "annotations stay untouched")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        return run(args)
    except CopyError as exc:
        print(f"superpowers-review-copy: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
