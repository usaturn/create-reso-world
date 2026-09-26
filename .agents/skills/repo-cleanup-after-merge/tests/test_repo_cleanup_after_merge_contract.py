from __future__ import annotations

import json
import os
import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[4]
SKILL_DIR = REPO_ROOT / ".agents/skills/repo-cleanup-after-merge"
SKILL = SKILL_DIR / "SKILL.md"
EVALS = SKILL_DIR / "evals/evals.json"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def frontmatter() -> dict[str, object]:
    return yaml.safe_load(read(SKILL).split("---", 2)[1])


def test_claude_code_reads_the_same_skill_through_a_symlink() -> None:
    link = REPO_ROOT / ".claude/skills/repo-cleanup-after-merge"
    assert link.is_symlink()
    assert os.readlink(link) == "../../.agents/skills/repo-cleanup-after-merge"


def test_keeps_gh_failure_stop_and_user_confirmation() -> None:
    content = read(SKILL)
    assert "が非0終了した場合、PR の状態は不明である" in content
    assert "AskUserQuestion" in content


def test_allowed_tools_cover_the_commands_the_steps_run() -> None:
    # Claude Code pre-approves only what this line lists.
    tools = frontmatter()["allowed-tools"]
    assert isinstance(tools, str)
    for entry in (
        "AskUserQuestion",
        "Bash(git *)",
        "Bash(gh *)",
        "Bash(diff *)",
        "Bash(cp *)",
        "Bash(rm *)",
        "Bash(uv run --no-project python -c *)",
        "Bash(bash scripts/resoloop-fork.sh sync)",
    ):
        assert entry in tools, entry
    content = read(SKILL)
    assert "python3" not in content
    assert "uv run --no-project python -c" in content


def test_resoloop_prs_are_cleaned_up_in_the_fork_checkout() -> None:
    body = read(SKILL).split("---", 2)[2]
    assert "リポジトリ境界" in body
    assert "git -C external/resoloop" in body
    assert "--repo usaturn/resoloop" in body
    assert "--repo orange3134/resoloop" in body
    assert "scripts/resoloop-fork.sh clone" in body
    assert "```bash\nbash scripts/resoloop-fork.sh sync\n```" in body
    assert "submodule" not in body


def test_local_main_follows_origin_main_by_fast_forward() -> None:
    content = read(SKILL)
    assert "git switch main" in content
    assert "git merge --ff-only origin/main" in content
    assert "`main` branch を作成しない" not in content
    assert "`main` branch は作成しない" not in content


def test_ignored_files_in_a_worktree_are_checked_before_removal() -> None:
    # git worktree remove deletes ignored files without asking.
    content = read(SKILL)
    assert "git -C <worktree の絶対パス> status --short --ignored" in content
    assert "`git worktree remove` は ignore 対象のファイルを確認せずに消す" in content
    for cache in (".venv/", ".pytest_cache/", "__pycache__/"):
        assert cache in content, cache
    assert "gitignore 対象のファイルは、再生成できるキャッシュを除き" in content
    assert "--force" not in content.split("### 5.", 1)[1].split("### 6.", 1)[0].replace("`--force` は付けない", "")


def test_related_skills_exist() -> None:
    related = read(SKILL).split("## 関連スキル", 1)[1]
    names = re.findall(r"^- `([a-z0-9-]+)`", related, re.M)
    assert names
    for name in names:
        assert (REPO_ROOT / ".agents/skills" / name / "SKILL.md").is_file(), name


def test_evals_cover_the_rules_of_this_repository() -> None:
    names = {item["name"] for item in json.loads(read(EVALS))["evals"]}
    assert {
        "remove-only-clean-worktree",
        "fast-forward-local-main",
        "hold-ignored-files-in-worktree",
        "sync-fork-after-upstream-merge",
    } <= names
    assert "stay-detached-without-local-main" not in names
    assert "force-remove-only-clean-worktree" not in names


def test_fork_sync_describes_push_semantics_correctly() -> None:
    # The sync step must correctly describe when fork/main is pushed.
    content = read(SKILL)
    # After the fix: fork's main is pushed when local main is clean,
    # but not when local main has uncommitted changes (though origin/main is synced).
    assert "fork の `main` への push を済ませてから" in content
    assert "origin/main is already synced" in content
    # The old incorrect description must be gone.
    assert "未コミットの変更がある場合、スクリプトは何も push せずに止まる" not in content
    # User confirmation must be requested via AskUserQuestion.
    assert "（Claude Code では AskUserQuestion を使う）" in content
