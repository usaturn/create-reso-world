"""Catch requested/parent identity substitution and cross-session log reads."""

import json
from pathlib import Path

import pytest

from tools.agent_runner import dsh_identity
from tools.test_support.dsh import write_session


def test_reads_observed_route_not_requested_or_parent(tmp_path: Path) -> None:
    cwd = tmp_path / "work"
    cwd.mkdir()
    path = write_session(tmp_path / "state", cwd, model="actual/model")
    # A live append's unfinished tail is not a completed invalid record.
    with path.open("a") as stream:
        stream.write('{"type":')
    identity = dsh_identity.read_session_identity(tmp_path / "state", cwd, "session-test", live=True)
    assert (identity.model, identity.provider, identity.effort, identity.session_id) == (
        "actual/model",
        "observed-provider",
        "high",
        "session-test",
    )
    assert identity.cli_version is None


def test_accepts_repeated_responses_from_the_same_route(tmp_path: Path) -> None:
    cwd = tmp_path / "work"
    cwd.mkdir()
    home = tmp_path / "state"
    path = write_session(home, cwd)
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    header, assistant = json.loads(json.dumps(rows[1:]))
    header["seq"], assistant["seq"] = 2, 3
    rows.extend([header, assistant])
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))
    identity = dsh_identity.read_session_identity(home, cwd, "session-test")
    assert (identity.provider, identity.model) == ("observed-provider", "observed-model")


@pytest.mark.parametrize(
    "case",
    [
        "cwd",
        "id",
        "version",
        "source",
        "header_only",
        "route_changed",
        "route_changed_then_returned",
        "sequence",
        "ambiguous",
        "malformed",
        "duplicate",
        "torn",
        "symlink",
        "directory_link",
        "fifo",
    ],
)
def test_rejects_unbound_or_invalid_records(tmp_path: Path, case: str) -> None:
    cwd = tmp_path / "work"
    cwd.mkdir()
    home = tmp_path / "state"
    path = write_session(home, cwd)
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    if case in {"cwd", "id", "version"}:
        rows[0][case] = {"cwd": str(tmp_path), "id": "foreign-session", "version": 999}[case]
    elif case == "source":
        rows[-1]["data"]["message"]["source"]["model"] = "different-model"
    elif case == "header_only":
        rows.pop()
    elif case == "route_changed":
        changed = json.loads(json.dumps(rows[1]))
        changed["seq"] = 2
        changed["data"]["header"]["config"]["model"] = "different-model"
        rows.append(changed)
    elif case == "route_changed_then_returned":
        changed = json.loads(json.dumps(rows[1]))
        changed["seq"] = 2
        changed["data"]["header"]["config"]["model"] = "temporary-model"
        restored_header, restored_assistant = json.loads(json.dumps(rows[1:]))
        restored_header["seq"], restored_assistant["seq"] = 3, 4
        rows.extend([changed, restored_header, restored_assistant])
    elif case == "sequence":
        rows[-1]["seq"] = 9
    elif case == "ambiguous":
        duplicate = home / "sessions" / "another-project" / "session-test" / "session.v4.jsonl"
        duplicate.parent.mkdir(parents=True)
        duplicate.write_text(path.read_text())
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))
    if case == "torn":
        with path.open("a") as stream:
            stream.write('{"type":')
    elif case == "malformed":
        with path.open("a") as stream:
            stream.write("broken {\n")
    elif case == "duplicate":
        path.write_text(path.read_text().replace('"version": 4', '"version": 4, "version": 4'))
    elif case == "symlink":
        target = tmp_path / "foreign.jsonl"
        path.rename(target)
        path.symlink_to(target)
    elif case == "directory_link":
        target = tmp_path / "foreign"
        path.parent.rename(target)
        path.parent.symlink_to(target, target_is_directory=True)
    elif case == "fifo":
        import os

        path.unlink()
        os.mkfifo(path)
    with pytest.raises((ValueError, OSError)):
        dsh_identity.read_session_identity(home, cwd, "session-test")
