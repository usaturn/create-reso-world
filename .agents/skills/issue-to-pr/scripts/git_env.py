"""The inherited-Git-environment rule shared by the issue-to-pr helpers and the SKILL.md shell blocks.

Running this file prints, one per line, the inherited GIT_* names a shell block unsets. The shell
blocks talk to origin (base fetch, scan, push, gh), so the transport authentication names stay.
"""

from __future__ import annotations

import os
import re

# Git の認証に使う transport の設定。ローカルの Git ディレクトリ・worktree・設定の選択を変えないので、
# remote と通信するときだけ残す（.agents/scripts/review_target.py の git_environment(transport_auth=True) と同じ）
TRANSPORT_AUTH = frozenset({"GIT_ASKPASS", "GIT_SSH", "GIT_SSH_COMMAND", "GIT_TERMINAL_PROMPT"})
# シェルが変数として持てる名前（unset できる名前）
SHELL_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def git_environment(*, transport_auth: bool = False) -> dict[str, str]:
    """Inherited Git directory/config overrides must not redirect a verified checkout."""
    allowed = TRANSPORT_AUTH if transport_auth else frozenset()
    return {name: value for name, value in os.environ.items() if not name.startswith("GIT_") or name in allowed}


def shell_unset_names() -> list[str]:
    kept = git_environment(transport_auth=True)
    return sorted(name for name in os.environ if name not in kept and SHELL_NAME.fullmatch(name))


def main() -> int:
    for name in shell_unset_names():
        print(name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
