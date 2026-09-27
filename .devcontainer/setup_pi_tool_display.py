#!/usr/bin/env python3
"""Use Pi's built-in Bash while keeping pi-distill and other display settings."""

import json
import os
import stat
import sys
import tempfile
from pathlib import Path
from typing import NoReturn


def _reject_nonstandard_json_constant(value: str) -> NoReturn:
    raise ValueError(f"nonstandard numeric constant {value}")


def main() -> int:
    agent_dir = Path(os.environ.get("PI_CODING_AGENT_DIR") or Path.home() / ".pi" / "agent").expanduser()
    config_path = agent_dir / "extensions" / "pi-tool-display" / "config.json"
    write_path = config_path.resolve() if config_path.is_symlink() else config_path

    try:
        data = (
            json.loads(
                config_path.read_text(encoding="utf-8"),
                parse_constant=_reject_nonstandard_json_constant,
            )
            if config_path.exists()
            else {}
        )
    except (ValueError, UnicodeError) as error:
        print(f"Invalid JSON in {config_path}: {error}", file=sys.stderr)
        return 1
    except OSError as error:
        print(f"Cannot read {config_path}: {error}", file=sys.stderr)
        return 1

    if not isinstance(data, dict):
        print(f"Invalid tool-display config in {config_path}: expected a JSON object", file=sys.stderr)
        return 1
    overrides = data.setdefault("registerToolOverrides", {})
    if not isinstance(overrides, dict):
        print(f"Invalid registerToolOverrides in {config_path}: expected a JSON object", file=sys.stderr)
        return 1
    if overrides.get("bash") is False:
        print(f"Bash override already disabled: {config_path}")
        return 0

    overrides["bash"] = False
    temporary_path: Path | None = None
    try:
        write_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=write_path.parent, prefix=".config-", delete=False
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            json.dump(data, temporary_file, ensure_ascii=False, allow_nan=False, indent=2)
            temporary_file.write("\n")
        if write_path.exists():
            temporary_path.chmod(stat.S_IMODE(write_path.stat().st_mode))
        temporary_path.replace(write_path)
    except (OSError, ValueError, UnicodeError) as error:
        print(f"Cannot update {config_path}: {error}", file=sys.stderr)
        return 1
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)

    print(f"Disabled Bash override: {config_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
