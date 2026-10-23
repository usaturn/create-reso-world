"""The literal exec environment helper."""

import os
from pathlib import Path

import pytest

from tools.agent_runner import environ


def test_literal_environ_parses_proc_and_skips_malformed_entries(monkeypatch: pytest.MonkeyPatch) -> None:
    def proc_bytes(_self: Path) -> bytes:
        return b"A=1\0NOEQUALS\0B=x=y\0EMPTY=\0RAW=\xff\xfe\0"

    monkeypatch.setattr(environ, "_literal", None)
    monkeypatch.setattr(Path, "read_bytes", proc_bytes)
    assert environ.literal_environ() == {
        "A": "1",
        "B": "x=y",
        "EMPTY": "",
        "RAW": os.fsdecode(b"\xff\xfe"),
    }
