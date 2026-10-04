"""Small strict JSON/storage boundary shared by pi migration and provider setup."""
import json
import math
from datetime import datetime
import os
from pathlib import Path
import stat
import shutil
import tempfile


def load_object(path: Path) -> dict:
    """Read a JSON object that pi/npm can represent as finite JavaScript Numbers."""
    def reject_constant(token):
        raise ValueError(f"Invalid JSON constant: {token}")

    def finite_number(token):
        value = float(token)
        if not math.isfinite(value):
            raise ValueError("JSON number is outside the finite JavaScript Number range")
        return value

    def finite_integer(token):
        finite_number(token)
        return int(token)  # Preserve accepted integers, including those beyond 2**53.

    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"),
                          parse_constant=reject_constant,
                          parse_float=finite_number, parse_int=finite_integer)
        if not isinstance(data, dict):
            raise ValueError("Expected JSON object")
    except ValueError as error:
        raise ValueError(f"Invalid JSON in {path}: {error}") from error
    return data


def write_object(path: Path, data: dict) -> None:
    """Serialize completely before staging a same-directory, mode-preserving replacement."""
    serialized = json.dumps(data, ensure_ascii=True, indent=2, allow_nan=False) + "\n"
    mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o600
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(serialized)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def backup_file(path: Path) -> Path:
    """Reserve a unique same-directory backup and preserve original bytes and mode."""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    descriptor, name = tempfile.mkstemp(prefix=f"{path.name}.bak.{timestamp}.", dir=path.parent)
    os.close(descriptor)
    backup = Path(name)
    try:
        shutil.copy2(path, backup)
    except OSError:
        backup.unlink()
        raise
    return backup
