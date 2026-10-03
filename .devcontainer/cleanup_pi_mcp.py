#!/usr/bin/env python3
"""Remove retired pi-only additions, using pi's package manager for npm state.

Run with: uv run --no-project .devcontainer/cleanup_pi_mcp.py
Only PI_CODING_AGENT_DIR (default ~/.pi/agent) is migrated; project/shared
configuration and ~/.npm caches are not cleanup targets.
"""
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys

PACKAGES = ("pi-mcp-adapter", "@upstash/context7-pi")
# mcp.json and mcp-auth.json are also native MCP storage; never migrate or unlink them.
MCP_FILES = (
    "mcp-cache.json", "mcp-project-approvals.json", "mcp-onboarding.json", "mcp-npx-cache.json",
)
MANIFESTS = (
    "package.json", "package-lock.json", "npm-shrinkwrap.json",
    "node_modules/.package-lock.json",
)


def agent_directory():
    path = Path(os.environ.get("PI_CODING_AGENT_DIR") or Path.home() / ".pi/agent").expanduser()
    # POSIX preserves // lexically even when the OS aliases it to /; do not resolve symlinks.
    if (not path.is_absolute() or path.anchor == "//" or ".." in path.parts
            or path in (Path("/"), Path.home())):
        raise ValueError(f"Unsafe agent directory: {path}")
    return path


def safe_storage(path):
    """Check without resolving links: never let pi mutate linked storage."""
    for item in (*reversed(path.parents), path):
        try:
            mode = item.lstat().st_mode
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(mode):
            raise ValueError(f"Refusing symlinked package/settings storage: {item}")
        if item != path and not stat.S_ISDIR(mode):
            raise ValueError(f"Unsafe storage directory: {item}")


def read_object(path):
    safe_storage(path)
    try:
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode):
            raise ValueError(f"Unsafe non-regular storage file: {path}")
        if info.st_nlink != 1:
            raise ValueError(f"Refusing hard-linked package/settings storage: {path}")
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        return {}
    except (OSError, ValueError) as error:
        raise ValueError(f"Cannot read {path}: {error}") from error
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


def package_sources(settings, path):
    entries = settings.get("packages", [])
    if not isinstance(entries, list):
        raise ValueError(f"Invalid packages declaration in {path}")
    sources = []
    for entry in entries:
        source = entry.get("source") if isinstance(entry, dict) else entry
        if not isinstance(source, str):
            raise ValueError(f"Invalid package source in {path}")
        sources.append(source)
    return sources


def matches(source, name):
    return source == "npm:" + name or source.startswith("npm:" + name + "@")


def manifest_contains(data, name):
    if isinstance(data, dict):
        return any(
            key == name or key == "node_modules/" + name
            or key.endswith("/node_modules/" + name) or manifest_contains(value, name)
            for key, value in data.items()
        )
    if isinstance(data, list):
        return any(manifest_contains(value, name) for value in data)
    return False


def inspect(agent):
    # Preflight every relevant storage path, including the lock pi uses to save settings.
    for relative in ("settings.json.lock", "npm", "npm/node_modules", "npm/node_modules/@upstash"):
        safe_storage(agent / relative)
    settings_path = agent / "settings.json"
    sources = package_sources(read_object(settings_path), settings_path)
    manifests = [(agent / "npm" / relative, read_object(agent / "npm" / relative)) for relative in MANIFESTS]
    result = {}
    for name in PACKAGES:
        installed = agent / "npm/node_modules" / name
        safe_storage(installed)
        try:
            installed.lstat()
            present = True
        except FileNotFoundError:
            present = False
        declared = any(matches(source, name) for source in sources)
        leftovers = [str(path) for path, data in manifests if manifest_contains(data, name)]
        if declared:
            leftovers.append(str(settings_path))
        if present:
            leftovers.append(str(installed))
        result[name] = (declared, leftovers)
    return result


def require_retained_npm_declarations(agent):
    """Refuse unsafe prefixes before npm uninstall can prune unrelated extensions."""
    # pi skips npm uninstall when the prefix is absent and only removes settings entries.
    if not os.path.lexists(agent / "npm"):
        return
    manifest_path = agent / "npm/package.json"
    if not manifest_path.exists():
        raise ValueError(f"Missing {manifest_path}; restore the npm manifest before retrying cleanup")
    manifest = read_object(manifest_path)
    dependencies = set()
    for section in ("dependencies", "devDependencies", "optionalDependencies"):
        entries = manifest.get(section, {})
        if not isinstance(entries, dict) or any(not isinstance(value, str) for value in entries.values()):
            raise ValueError(f"Invalid {section} in {manifest_path}; restore the npm manifest before retrying cleanup")
        dependencies.update(entries)
    settings_path = agent / "settings.json"
    for source in package_sources(read_object(settings_path), settings_path):
        if not source.startswith("npm:") or any(matches(source, name) for name in PACKAGES):
            continue
        if not any(matches(source, name) for name in dependencies):
            raise ValueError(
                f"Retained package {source} is not declared in {manifest_path}; "
                "restore the npm manifest before retrying cleanup"
            )


def cleanup():
    agent = agent_directory()
    safe_storage(agent)
    before = inspect(agent)
    if any(leftovers for _, leftovers in before.values()):
        require_retained_npm_declarations(agent)
    # Validate all state entries before removing packages; no recursive deletion or glob.
    for filename in MCP_FILES:
        path = agent / filename
        try:
            mode = path.lstat().st_mode
        except FileNotFoundError:
            continue
        if not (stat.S_ISREG(mode) or stat.S_ISLNK(mode)):
            raise ValueError(f"Unsafe MCP state file: {path}")

    env = {**os.environ, "PI_CODING_AGENT_DIR": str(agent)}
    for name, (declared, leftovers) in before.items():
        if not leftovers:
            continue
        source = "npm:" + name
        # --no-approve avoids project trust prompts and project-local package configuration.
        removal = subprocess.run(["pi", "remove", source, "--no-approve"], env=env,
                                 text=True, capture_output=True)
        if removal.stdout:
            print(removal.stdout, end="")
        if removal.stderr:
            print(removal.stderr, end="", file=sys.stderr)
        remaining = inspect(agent)[name][1]
        if remaining:
            raise ValueError(f"{source} remains after removal: {', '.join(remaining)}")
        if removal.returncode:
            # pi uninstalls manifest-only packages, then returns 1 because no settings entry
            # matched. npm warnings may accompany the exact diagnostic line; arbitrary
            # removal/read errors without that line must still fail.
            diagnostics = re.sub(r"\x1b\[[0-9;]*m", "", removal.stderr).splitlines()
            if (declared or removal.returncode != 1
                    or f"No matching package found for {source}" not in diagnostics):
                raise ValueError(f"{source} removal failed (exit {removal.returncode})")

    # Verify both package identities again before unlinking pi-only state (also dangling links).
    for name, (_, leftovers) in inspect(agent).items():
        if leftovers:
            raise ValueError(f"npm:{name} remains after cleanup: {', '.join(leftovers)}")
    for filename in MCP_FILES:
        path = agent / filename
        try:
            path.unlink()
            print(f"Removed pi-only state: {path}")
        except FileNotFoundError:
            pass


if __name__ == "__main__":
    try:
        cleanup()
    except (OSError, ValueError) as error:
        print(f"ERROR: pi-only MCP cleanup: {error}", file=sys.stderr)
        sys.exit(1)
