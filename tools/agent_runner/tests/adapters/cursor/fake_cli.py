"""Fake `cursor-agent`: reads stdin, emits stream-json init/result, honors --fail-* and --echo-argv."""

import json
import sys

SESSION = "a6b41ff6-5660-4000-8000-000000000002"


def main() -> int:
    prompt = sys.stdin.read()
    assert prompt and prompt not in sys.argv
    assert "-p" in sys.argv and "--trust" in sys.argv
    assert sys.argv[sys.argv.index("--output-format") + 1] == "stream-json"
    # A fallback must use another model than its primary (duplicate_model)
    assert sys.argv[sys.argv.index("--model") + 1] in {"requested-model", "fallback-model"}
    if "--fail-auth" in sys.argv:
        print("Error: not logged in. Run 'agent login' first.", file=sys.stderr)
        return 1
    if "--fail-trust" in sys.argv:
        print("Workspace Trust Required: run interactively to decide.")
        return 0
    print(json.dumps({"type": "system", "subtype": "init", "session_id": SESSION, "model": "Fake Model X"}))
    if "--fail-bad" in sys.argv:
        print(json.dumps({"type": "result", "subtype": "success", "is_error": True, "session_id": SESSION}))
        return 0
    answer: dict[str, object] = {"answer": 42}
    if "--echo-argv" in sys.argv:
        answer["argv"] = sys.argv[1:]
    result = json.dumps(answer)
    print(
        json.dumps(
            {
                "type": "result",
                "subtype": "success",
                "duration_ms": 1,
                "is_error": False,
                "result": result,
                "session_id": SESSION,
            }
        )
    )
    if "--truncate" in sys.argv:
        print('{"type":"result","result":')
    if "--late-auth" in sys.argv:
        print("Error: not logged in", file=sys.stderr)
    if "--late-trust" in sys.argv:
        print("Workspace Trust Required", file=sys.stderr)
    return 9 if "--nonzero" in sys.argv else 0


if __name__ == "__main__":
    sys.exit(main())
