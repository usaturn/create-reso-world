"""Local Pi JSON update boundary (also usable before uv is installed).

Provider models/auth and installer settings share validation and staging. The
historical filename remains for callers. Replacements are not a transaction
across files, external Pi commands or processes; stop Pi/other setup first.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import sys
import tempfile


def agent_directory(value: str | None = None) -> Path:
    """Expand Pi's raw POSIX path once, returning a stable absolute path."""
    raw = value if value is not None else os.environ.get("PI_CODING_AGENT_DIR")
    if not raw:
        raw = str(Path.home() / ".pi" / "agent")
    elif raw == "~":
        raw = str(Path.home())
    elif raw.startswith("~/"):
        # Concatenate rather than join: a second slash must not discard HOME.
        raw = str(Path.home()) + "/" + raw[2:]
    # Path drops leading ./; absolutize before returning so ./~/x cannot become
    # a fresh ~/x input. Keep symlinks and .. for the OS to traverse in order.
    return Path(raw).absolute()


def plain_file(path: Path) -> None:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise ValueError(f"Refusing linked or non-regular storage: {path}")


def load_object(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (ValueError, UnicodeError):
        # Parser diagnostics can contain credentials from the input.
        raise ValueError(f"Invalid JSON object: {path}") from None
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return data


def stage(path: Path, payload: bytes, mode: int, *, prefix: str | None = None, suffix: str = ".tmp") -> Path:
    fd, name = tempfile.mkstemp(dir=path.parent, prefix=prefix or f".{path.name}.", suffix=suffix)
    temporary = Path(name)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.chmod(mode)
        return temporary
    except BaseException:
        temporary.unlink()
        raise


def setup(agent: Path, source: Path, provider: str) -> None:
    models = agent / "models.json"
    plain_file(models)
    data = load_object(models) if models.exists() else {}
    providers = data.setdefault("providers", {})
    if not isinstance(providers, dict):
        raise ValueError(f"Expected providers object: {models}")
    source_providers = load_object(source).get("providers")
    if not isinstance(source_providers, dict) or not isinstance(source_providers.get(provider), dict):
        raise ValueError(f"Provider {provider!r} is not defined as an object: {source}")
    changed = providers.get(provider) != source_providers[provider]
    providers[provider] = source_providers[provider]
    # Serialize even unchanged inputs: unrepresentable values must fail preflight.
    model_payload = (json.dumps(data, ensure_ascii=True, indent=2, allow_nan=False) + "\n").encode()
    writes = []
    if changed:
        mode = stat.S_IMODE(models.stat().st_mode) if models.exists() else 0o600
        writes.append((models, model_payload, mode))

    if provider == "opencode-go":
        auth = agent / "auth.json"
        plain_file(auth)
        auth_data = load_object(auth) if auth.exists() else {}
        existing = auth_data.get(provider)
        key = os.environ.get("OPENCODE_API_KEY") or os.environ.get("OPENCODE_GO_API_KEY")
        if key:
            auth_data[provider] = {"type": "api_key", "key": key}
        elif not (isinstance(existing, dict) and existing.get("type") == "api_key"
                  and isinstance(existing.get("key"), str) and existing["key"]):
            raise ValueError("No OpenCode Go API key is configured; set OPENCODE_API_KEY or OPENCODE_GO_API_KEY.")
        payload = (json.dumps(auth_data, ensure_ascii=True, indent=2, allow_nan=False) + "\n").encode()
        if not auth.exists() or auth_data.get(provider) != existing or stat.S_IMODE(auth.stat().st_mode) != 0o600:
            writes.append((auth, payload, 0o600))

    # No mkdir, backup, auth write or external Pi command precedes this preflight.
    if not writes:
        print("already up to date")
        return
    agent.mkdir(parents=True, exist_ok=True)
    staged = []
    try:
        for path, payload, mode in writes:
            staged.append((path, stage(path, payload, mode)))
        if changed and models.exists():
            # Reserve a unique backup; never follow an existing fixed-name .tmp.
            backup = stage(models, models.read_bytes(), stat.S_IMODE(models.stat().st_mode),
                           prefix="models.json.bak.", suffix="")
            print(f"backup:{backup}")
        for path, temporary in staged:
            os.replace(temporary, path)
        print("updated")
    finally:
        for _, temporary in staged:
            temporary.unlink(missing_ok=True)


def settings_update(agent: Path, *, check_only: bool = False) -> None:
    settings = agent / "settings.json"
    plain_file(settings)
    if not settings.exists():
        return
    data = load_object(settings)
    for field in ("extensions", "packages"):
        if field in data and not isinstance(data[field], list):
            raise ValueError(f"Expected {field} array: {settings}")
    extensions = data.get("extensions", [])
    # Serialize during preflight too, before external Pi may change packages.
    payload = dict(data)
    payload["extensions"] = [entry for entry in extensions if entry != "-builtin:mcp"]
    encoded = (json.dumps(payload, ensure_ascii=True, indent=2, allow_nan=False) + "\n").encode()
    if check_only or "-builtin:mcp" not in extensions:
        return
    temporary = stage(settings, encoded, stat.S_IMODE(settings.stat().st_mode))
    try:
        os.replace(temporary, settings)
    finally:
        temporary.unlink(missing_ok=True)


if __name__ == "__main__":
    try:
        if sys.argv[1] == "--agent-dir":
            print(agent_directory())
        elif sys.argv[1] in ("--settings-check", "--settings-clean"):
            agent = agent_directory(sys.argv[2] if len(sys.argv) > 2 else None)
            settings_update(agent, check_only=sys.argv[1] == "--settings-check")
        else:
            setup(Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3])
    except (OSError, ValueError) as error:
        print(f"ERROR: Pi configuration update: {error}", file=sys.stderr)
        sys.exit(1)
