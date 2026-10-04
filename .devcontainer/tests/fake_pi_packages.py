#!/usr/bin/env python3
"""Offline pi double: only the external package-manager boundary is replaced."""
import json
import os
from pathlib import Path
import shutil
import sys

agent = Path(os.environ.get("PI_CODING_AGENT_DIR") or Path.home() / ".pi/agent").expanduser()
settings_path = agent / "settings.json"
settings = json.loads(settings_path.read_text(encoding="utf-8-sig")) if settings_path.exists() else {}
packages = settings.get("packages", [])
args = sys.argv[1:]
command = args.pop(0)
args = [arg for arg in args if arg not in ("--approve", "--no-approve")]
retired = ("pi-mcp-adapter", "@upstash/context7-pi", "pi-distill",
           "pi-extensions-tool-display", "pi-extensions-i18n")
if os.environ.get("FAKE_PI_CALL_LOG"):
    with Path(os.environ["FAKE_PI_CALL_LOG"]).open("a") as log:
        log.write(json.dumps([command, *args]) + "\n")


def source(entry):
    return entry if isinstance(entry, str) else entry["source"]


def identity(spec):
    # pi removes by npm name, including pinned and object-form declarations.
    if not spec.startswith("npm:"):
        return spec
    return spec[4:].split("@", 1)[0] if not spec[4:].startswith("@") else "@" + spec[5:].split("@", 1)[0]


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n")


def prune(value, name):
    if isinstance(value, dict):
        return {
            key: prune(item, name)
            for key, item in value.items()
            if key != name and key != "node_modules/" + name and not key.endswith("/node_modules/" + name)
        }
    if isinstance(value, list):
        return [prune(item, name) for item in value]
    return value


if command == "list":
    print("\n".join(source(entry) for entry in packages))
elif command == "install":
    spec = args[0]
    name = identity(spec)
    if os.environ.get("FAKE_PI_REQUIRE_CLEAN") == "1":
        if any(identity(source(entry)) in retired for entry in packages) or any(
            (agent / filename).exists() for filename in (
                "mcp-cache.json", "mcp-project-approvals.json", "mcp-onboarding.json", "mcp-npx-cache.json",
            )
        ):
            print("Error: unrelated extension installation ran before pi-only cleanup", file=sys.stderr)
            sys.exit(1)
    if not any(identity(source(entry)) == name for entry in packages):
        packages.append(spec)
    settings["packages"] = packages
    save(settings_path, settings)
    if spec.startswith("npm:"):
        manifest = agent / "npm/package.json"
        data = json.loads(manifest.read_text()) if manifest.exists() else {}
        data.setdefault("dependencies", {})[name] = "*"
        save(manifest, data)
        (agent / "npm/node_modules" / name).mkdir(parents=True, exist_ok=True)
elif command == "update" and args == ["--extensions"]:
    # Rebuild from both settings and the npm root manifest, as real pi/npm updates do.
    names = {identity(source(entry)) for entry in packages if source(entry).startswith("npm:")}
    manifest = agent / "npm/package.json"
    if manifest.exists():
        data = json.loads(manifest.read_text())
        for section in ("dependencies", "devDependencies", "optionalDependencies"):
            names.update(data.get(section, {}))
    for name in names:
        save(agent / "npm/node_modules" / name / "package.json", {"name": name})
elif command == "remove":
    spec = args[0]
    name = identity(spec)
    mode = os.environ.get("FAKE_PI_REMOVE", "normal")
    if mode == "fail":
        print("Error: package removal failed", file=sys.stderr)
        sys.exit(1)
    declared = any(identity(source(entry)) == name for entry in packages)
    if mode != "keep-settings" and declared:
        settings["packages"] = [entry for entry in packages if identity(source(entry)) != name]
        save(settings_path, settings)
    if mode != "keep-manifest":
        for relative in ("package.json", "package-lock.json", "npm-shrinkwrap.json", "node_modules/.package-lock.json"):
            manifest = agent / "npm" / relative
            if manifest.exists():
                save(manifest, prune(json.loads(manifest.read_text()), name))
    if mode != "keep-installed":
        installed = agent / "npm/node_modules" / name
        if installed.exists():
            shutil.rmtree(installed)
    if mode == "break-settings":
        settings_path.write_text("{broken")
    if mode == "fail-after-clean":
        print("Error: package removal failed after partial cleanup", file=sys.stderr)
        sys.exit(1)
    if mode == "nonzero-declared":
        print(f"No matching package found for {spec}", file=sys.stderr)
        sys.exit(1)
    if not declared:
        if mode == "noisy-undeclared":
            print("npm notice update available\nnpm warn harmless warning", file=sys.stderr)
            print(f"\x1b[31mNo matching package found for {spec}\x1b[0m", file=sys.stderr)
        elif mode == "wrong-source":
            print("No matching package found for npm:not-the-target", file=sys.stderr)
        elif mode == "partial-diagnostic":
            print(f"Error: No matching package found for {spec} (other failure)", file=sys.stderr)
        else:
            print(f"No matching package found for {spec}", file=sys.stderr)
        sys.exit(2 if mode == "nonzero-undeclared" else 1)
else:
    print(f"Unexpected pi command: {command}", file=sys.stderr)
    sys.exit(64)
