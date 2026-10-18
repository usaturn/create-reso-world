"""Fake `codex exec`: reads stdin, emits JSONL events, honors --fail-auth/--fail-bad."""

import json
import os
import sys
from pathlib import Path

SESSION = "f0f0f0f0-5660-4000-8000-000000000001"


def _write_rollout() -> None:
    """Write a session rollout into the runtime home this process inherited."""
    home = os.environ.get("CODEX_HOME")
    if not home:
        return
    directory = Path(home) / "sessions" / "2026" / "10" / "07"
    directory.mkdir(parents=True, exist_ok=True)
    record = {
        "type": "turn_context",
        "payload": {
            "cli_version": "observed-cli",
            "model_provider": "observed-provider",
            "model": "observed-model",
            "effort": "observed-effort",
        },
    }
    name = f"rollout-2026-10-07T00-00-00-{SESSION}.jsonl"
    (directory / name).write_text(json.dumps(record) + "\n", encoding="utf-8")


def main() -> int:
    sys.stdin.read()
    if "--fail-auth" in sys.argv:
        print("Error: not logged in. Run 'codex login' first.", file=sys.stderr)
        return 1
    print(json.dumps({"type": "thread.started", "thread_id": SESSION}))
    _write_rollout()
    if "--fail-bad" in sys.argv:
        print(json.dumps({"type": "error", "message": "turn failed"}))
        return 0
    reconnect = next((arg.removeprefix("--reconnect=") for arg in sys.argv if arg.startswith("--reconnect=")), None)
    if reconnect is not None:
        # A prior success must not survive a terminal reconnect error.
        print(json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": '{"stale":true}'}}))
        print(json.dumps({"type": "turn.completed"}))
        print(json.dumps({"type": "error", "message": "Reconnecting: temporary stream interruption"}))
        if reconnect == "terminal":
            return 0
        if reconnect == "no-message":
            print(json.dumps({"type": "turn.completed"}))
            return 0
        if reconnect == "turn-failed":
            print(json.dumps({"type": "turn.failed", "error": {"message": "terminal failure"}}))
    text = json.dumps({"answer": 42})
    print(json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": text}}))
    if reconnect == "no-completion":
        return 0
    print(json.dumps({"type": "turn.completed"}))
    if "--nonzero" in sys.argv:
        return 7
    if "--fail-approval" in sys.argv:
        print("Error: approval required for command", file=sys.stderr)
        return 1
    if "--truncate" in sys.argv:
        print('{"type":"item.completed","item":')
    return 0


if __name__ == "__main__":
    sys.exit(main())
