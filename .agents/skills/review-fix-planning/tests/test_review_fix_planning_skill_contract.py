from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
AGENTS_SKILL = REPO_ROOT / ".agents/skills/review-fix-planning/SKILL.md"
AGENTS_HELPER = REPO_ROOT / ".agents/skills/review-fix-planning/scripts/upsert_pr_comment.py"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def assert_status_comment_snippet(content: str) -> None:
    """The posting snippet is run verbatim, so it must survive an unquoted heredoc."""
    # Bare backticks inside <<EOF would run the branch name as a command.
    assert "\\`$HEAD_BRANCH\\`" in content
    assert "\\`$HEAD_SHA\\`" in content
    # The repository is passed explicitly; a PR number alone is ambiguous.
    assert '--repo "$PR_REPO"' in content


def extract_status_script(content: str) -> str:
    blocks = [block for block in re.findall(r"```bash\n(.*?)```", content, re.DOTALL)
              if '--pr "$PR_NUMBER"' in block]
    assert len(blocks) == 1, "skill must have one unambiguous status posting block"
    return blocks[0]


def test_status_comment_snippet_escapes_heredoc_and_pins_repository() -> None:
    assert_status_comment_snippet(extract_status_script(read(AGENTS_SKILL)))


@pytest.fixture(params=["bash", "zsh", "zsh-nounset"])
def context_shell(request):
    shell = "zsh" if request.param.startswith("zsh") else "bash"
    if shutil.which(shell) is None:
        pytest.skip(f"{shell} is not installed; skipping only its context cases")
    return shell, request.param != "zsh"


@pytest.fixture
def bash_shell():
    """シェルごとの差は外部 cwd の正常系だけで確かめ、停止の各条件は bash で確かめる（D）。"""
    if shutil.which("bash") is None:
        pytest.skip("bash is not installed")
    return "bash", True


@pytest.fixture
def git_context(tmp_path):
    # Fixture diagnostics must never print the agent's inherited credentials;
    # Git selectors/config and the real user HOME must not reach temporary repos.
    home = tmp_path / "isolated home"
    home.mkdir()
    env = {"PATH": os.environ["PATH"], "HOME": str(home),
           "XDG_CONFIG_HOME": str(home / ".config"), "UV_OFFLINE": "1",
           "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null"}
    def git(path, *args):
        return subprocess.run(["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", *args],
                              cwd=path, env=env, check=True, text=True, capture_output=True).stdout.strip()
    def repo(name, remotes):
        path = tmp_path / name
        path.mkdir(parents=True)
        git(path, "init", "-b", "main")
        git(path, "commit", "--allow-empty", "-m", "initial")
        for remote, url in remotes.items():
            git(path, "remote", "add", remote, url)
        return path
    parent = repo("parent", {"origin": "https://github.com/usaturn/create-reso-world.git"})
    helper = REPO_ROOT / "scripts/superpowers_context.py"
    (parent / "scripts").mkdir()
    shutil.copy2(helper, parent / "scripts/superpowers_context.py")
    shutil.copytree(REPO_ROOT / "tools/external_tools", parent / "tools/external_tools",
                    ignore=shutil.ignore_patterns("tests", "__pycache__"))
    code = repo("code", {"base": "git@github.com:other/repository.git",
                         "origin": "ssh://git@github.com/contributor/repository.git"})
    doc = tmp_path / "docs"
    git(parent, "worktree", "add", "-b", "docs/topic", str(doc))
    return parent, code, doc, git, env


def run_fix_context(git_context, context_shell, *, cwd=None, **variables):
    parent, code, doc, git, env = git_context
    # The real instruction block is the resolver; no test-side URL/root logic.
    blocks = re.findall(r"```bash\n(.*?)```", read(AGENTS_SKILL), re.DOTALL)
    matches = [block for block in blocks if "CONTEXT_PARENT=" in block
               and '--pr "$PR_NUMBER"' not in block]
    assert len(matches) == 1, "skill must have one unambiguous context preflight block"
    script = matches[0]
    values = {"PARENT_ROOT": str(parent), "CODE_ROOT": str(code), "DOC_ROOT": str(doc),
              "DOC_BRANCH": "docs/topic", "PR_REPO": "other/repository", "HEAD_REPO": "",
              "HEAD_BRANCH": ""}
    values.update(variables)
    before = {str(p): [git(p, *args) for args in (("rev-parse", "HEAD"), ("status", "--porcelain"),
                                                ("remote", "-v"), ("show-ref",))] for p in (parent, code, doc)}
    marker = parent.parent / "later-mutation-reached"
    harness = ("set -euo pipefail\n" if context_shell[1] else "set -eo pipefail\n")
    harness += "\n".join(f"{key}={shlex.quote(value)}" for key, value in values.items()) + "\n"
    harness += script + f"\ntouch {shlex.quote(str(marker))}\nprintf '%s\\n' \"$CONTEXT_JSON\"\n"
    shell = context_shell[0]
    result = subprocess.run([shell, *(["-f"] if shell == "zsh" else []), "-c", harness],
                            cwd=cwd or parent, env=env, text=True, capture_output=True)
    assert before == {str(p): [git(p, *args) for args in (("rev-parse", "HEAD"), ("status", "--porcelain"),
                                                        ("remote", "-v"), ("show-ref",))] for p in (parent, code, doc)}
    if result.returncode:
        assert not marker.exists(), "preflight did not stop a later mutation"
        assert result.returncode == 66, result.stderr
        assert result.stdout == ""
        assert result.stderr
    else:
        assert marker.exists()
        assert result.stderr == ""
    return result


def test_fix_context_uses_real_parent_helper_from_external_cwd(git_context, context_shell):
    parent, code, doc, *_ = git_context
    result = run_fix_context(git_context, context_shell, cwd=code, HEAD_REPO="contributor/repository", HEAD_BRANCH="main")
    assert result.returncode == 0, result.stderr
    value = json.loads(result.stdout)
    assert (value["tool_root"], value["doc_root"], value["code_root"]) == (str(parent), str(doc), str(code))
    assert (value["base_remote"], value["head_remote"]) == ("base", "origin")


@pytest.mark.parametrize("case", ["parent-omitted", "duplicate-base", "doc-branch", "head-ambiguous", "helper-missing"])
def test_fix_context_stops_before_later_mutation(git_context, bash_shell, case):
    parent, code, doc, git, _ = git_context
    values = {}
    cwd = parent
    if case == "parent-omitted":
        values["PARENT_ROOT"] = ""
        cwd = code
    elif case == "duplicate-base":
        git(code, "remote", "add", "mirror", "https://github.com/other/repository.git")
    elif case == "doc-branch":
        values["DOC_BRANCH"] = "wrong"
    elif case.startswith("head-"):
        values.update(HEAD_REPO="contributor/repository", HEAD_BRANCH="main")
        git(code, "remote", "add", "mirror", "https://github.com/contributor/repository.git")
    else:
        helper = parent / "scripts/superpowers_context.py"
        if helper.exists():
            helper.unlink()
    result = run_fix_context(git_context, bash_shell, cwd=cwd, **values)
    assert result.returncode == 66, result.stdout


@pytest.mark.parametrize("case", ["valid", "same-url-clone", "conflict"])
def test_fix_context_verifies_known_repository_worktree_membership(git_context, bash_shell, case):
    parent, code, doc, git, _ = git_context
    if case == "same-url-clone":
        git(code, "remote", "set-url", "base", "https://github.com/usaturn/create-reso-world.git")
        git(code, "remote", "set-url", "origin", "https://github.com/usaturn/create-reso-world.git")
    root = doc if case == "valid" else code
    result = run_fix_context(git_context, bash_shell, PR_REPO="usaturn/create-reso-world", CODE_ROOT=str(root))
    assert result.returncode == (0 if case == "valid" else 66), result.stderr
    if case == "valid":
        assert json.loads(result.stdout)["code_root"] == str(doc)


@pytest.mark.parametrize("case", ["missing-context-helper", "wrong-doc-branch"])
def test_status_snippet_revalidates_before_comment_mutation(git_context, bash_shell, case):
    parent, code, doc, git, env = git_context
    comment_helper = parent / ".agents/skills/review-fix-planning/scripts/upsert_pr_comment.py"
    comment_helper.parent.mkdir(parents=True)
    shutil.copy2(AGENTS_HELPER, comment_helper)
    # GitHub is the external boundary. An accidental call fails, never networks.
    bin_dir = parent.parent / "bin"
    bin_dir.mkdir()
    gh = bin_dir / "gh"
    gh.write_text("#!/bin/bash\nprintf 'unexpected external operation' >&2\nexit 1\n", encoding="utf-8")
    gh.chmod(0o755)
    env["PATH"] = str(bin_dir) + os.pathsep + env["PATH"]
    needle = "PARENT_ROOT origin"
    if case == "missing-context-helper":
        (parent / "scripts/superpowers_context.py").unlink()
        needle = "superpowers_context.py"
    else:
        needle = "DOC_ROOT branch"
    values = {"PARENT_ROOT": str(parent), "TOPLEVEL": str(parent), "CODE_ROOT": str(code), "DOC_ROOT": str(doc),
              "DOC_BRANCH": "wrong" if case == "wrong-doc-branch" else "docs/topic", "PR_REPO": "other/repository",
              "PR_NUMBER": "3", "HEAD_BRANCH": "main", "HEAD_REPO": "contributor/repository", "HEAD_SHA": "1234",
              "MODEL_NAME": "Test-model"}
    script = extract_status_script(read(AGENTS_SKILL))
    harness = ("set -euo pipefail\n" if bash_shell[1] else "set -eo pipefail\n")
    harness += "\n".join(f"{key}={shlex.quote(value)}" for key, value in values.items()) + "\n" + script
    shell = bash_shell[0]
    result = subprocess.run([shell, *(["-f"] if shell == "zsh" else []), "-c", harness],
                            cwd=code, env=env, text=True, capture_output=True)
    assert result.returncode == 66, result.stderr
    assert needle in result.stderr
    assert result.stdout == ""


def test_fix_initial_planning_does_not_confuse_pr_branch_metadata_with_head_validation(git_context, bash_shell):
    result = run_fix_context(git_context, bash_shell, HEAD_BRANCH="pr/topic", HEAD_REPO="")
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["head_remote"] is None


@pytest.mark.parametrize("case", ["split", "wrong-single", "fallback"])
def test_fix_context_validates_effective_push_destinations(git_context, bash_shell, case):
    # A fetch-matching remote with an unsafe pushurl must stop before mutation.
    _, code, _, git, _ = git_context
    if case == "split":
        git(code, "remote", "set-url", "--push", "base", "https://github.com/contributor/repository.git")
        git(code, "remote", "set-url", "--push", "origin", "https://github.com/wrong/repository.git")
    elif case == "wrong-single":
        git(code, "remote", "set-url", "--push", "origin", "https://github.com/wrong/repository.git")
    result = run_fix_context(git_context, bash_shell, cwd=code, HEAD_REPO="contributor/repository", HEAD_BRANCH="main")
    if case in ("split", "fallback"):
        assert result.returncode == 0, result.stderr
        value = json.loads(result.stdout)
        assert value["base_remote"] == "base"
        assert value["head_remote"] == ("base" if case == "split" else "origin")
    else:
        assert result.returncode == 66, result.stdout
        assert "effective push URLs" in result.stderr
