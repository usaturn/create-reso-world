"""Inspect adopted external tools without network access or checkout mutations."""
from __future__ import annotations

import argparse
from collections.abc import Sequence
from dataclasses import asdict
import json
import os
from pathlib import Path

from .identity import resolve_managed_target
from .models import CheckResult, CloneResult, ExternalToolsError
from .registry import _git, load_active_registry


def _parent_root() -> Path:
    # Anchor to this package's checkout, not cwd or a nearby repository. A linked
    # document worktree uses the permanent parent identified by its common dir.
    checkout = Path(__file__).resolve().parents[2]
    common = os.fsdecode(_git(checkout, "rev-parse", "--path-format=absolute", "--git-common-dir").stdout).strip()
    return Path(common).resolve().parent


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parent-root", type=Path, help="absolute permanent create-reso-world checkout root")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list")
    for command in ("show", "check", "clone"):
        commands.add_parser(command).add_argument("key")
    args = parser.parse_args(argv)
    parent = args.parent_root
    commit = ""
    path = parent
    try:
        if parent is None:
            parent = _parent_root()
        path = parent
        registry = load_active_registry(parent)
        if registry is None:
            raise ExternalToolsError("registry_missing", "Permanent parent has no adopted external-tools registry.")
        commit = registry.commit
        if args.command == "list":
            payload = {"registry_commit": commit, "tools": [asdict(spec) for spec in registry.entries]}
            code = 0
        else:
            spec = next((spec for spec in registry.entries if spec.key == args.key), None)
            if spec is None:
                raise ExternalToolsError("unknown_tool", "Tool key is not registered in the adopted registry.")
            path = parent / spec.relative_path
            if args.command == "show":
                payload = {**asdict(spec), "path": str(path), "registry_commit": commit}
                code = 0
            elif args.command == "clone":
                # Task3 supplies clone_tool. Until then refuse explicitly; never
                # import a missing module eagerly or pretend a clone succeeded.
                payload = asdict(CloneResult("blocked", path, None, "clone_unsupported", commit))
                code = 1
            else:
                try:
                    target = resolve_managed_target(registry, spec.repository, operation="review-workspace")
                except ExternalToolsError as error:
                    status = "missing" if error.reason_code == "checkout_missing" else "mismatch"
                    payload = asdict(CheckResult(status, path, None, error.reason_code, commit))
                    code = 1
                else:
                    payload = asdict(CheckResult("ready", target.checkout, target.common_dir, None, commit))
                    code = 0
    except ExternalToolsError as error:
        payload = asdict(CheckResult("blocked", path or Path(__file__).resolve().parents[2], None, error.reason_code, commit))
        code = 1
    print(json.dumps(payload, default=str, ensure_ascii=False, sort_keys=True))
    return code
