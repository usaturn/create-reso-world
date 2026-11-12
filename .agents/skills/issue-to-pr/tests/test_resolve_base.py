"""Base selection safety: real local Git, with only origin URL discovery replaced.

Each rejection prevents silently selecting another repository/history or modifying
an existing checkout. Normal cases keep the boundary from becoming reject-all.
"""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

from tools.external_tools.tests.conftest import Workspace, isolated_git, workspace  # noqa: F401

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "resolve_base.py"
REPO = "usaturn/create-reso-world"
INTEGRATION = "統合/プラグイン"


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def snapshot(root: Path) -> tuple[str, str, str, bytes, bytes | None]:
    fetch_head = root / ".git" / "FETCH_HEAD"
    return (
        git(root, "for-each-ref"),
        git(root, "status", "--porcelain"),
        git(root, "symbolic-ref", "HEAD"),
        (root / ".git" / "index").read_bytes(),
        fetch_head.read_bytes() if fetch_head.exists() else None,
    )


@dataclass
class Repository:
    root: Path
    seed: Path
    remote: Path
    fetch_log: Path


def resolve(
    repository: Repository, *args: str, checkout: Path | None = None, repo: str = REPO
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--checkout", str(checkout or repository.root), "--repo", repo, *args],
        capture_output=True,
        text=True,
    )


def rejected(result: subprocess.CompletedProcess[str]) -> None:
    assert result.returncode == 2, result.stdout
    assert result.stdout == ""
    assert result.stderr


@pytest.fixture
def repository(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Repository:
    # The root conftest drops inherited GIT_* before this fixture. Use a one-test
    # HOME so the real Git setup also cannot use the developer's global config.
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("GIT_AUTHOR_NAME", "Base test")
    monkeypatch.setenv("GIT_AUTHOR_EMAIL", "base@example.test")
    monkeypatch.setenv("GIT_COMMITTER_NAME", "Base test")
    monkeypatch.setenv("GIT_COMMITTER_EMAIL", "base@example.test")
    remote, seed, root = (tmp_path / name for name in ("remote.git", "seed", "checkout"))
    subprocess.run(["git", "init", "--bare", "--quiet", "--initial-branch=main", str(remote)], check=True)
    subprocess.run(["git", "init", "--quiet", "--initial-branch=main", str(seed)], check=True)
    (seed / "content").write_text("main history\n", encoding="utf-8")
    git(seed, "add", "content")
    git(seed, "commit", "--quiet", "-m", "main")
    git(seed, "switch", "--quiet", "-c", INTEGRATION)
    (seed / "content").write_text("統合の履歴\nsecond line\n", encoding="utf-8")
    git(seed, "commit", "--quiet", "-am", "integration")
    git(seed, "tag", "tag-only")
    git(seed, "remote", "add", "origin", str(remote))
    git(seed, "push", "--quiet", "origin", "--all")
    git(seed, "push", "--quiet", "origin", "--tags")
    subprocess.run(
        ["git", "clone", "--quiet", "--single-branch", "--branch", "main", str(remote), str(root)],
        check=True,
    )
    git(root, "switch", "--quiet", "-c", "feature/local")
    (root / "local").write_text("keep the feature\n", encoding="utf-8")
    git(root, "add", "local")
    git(root, "commit", "--quiet", "-m", "local feature")
    (root / "local").write_text("keep uncommitted edits\n", encoding="utf-8")
    # A configured refmap must not redirect base acquisition into local heads.
    git(root, "config", "remote.origin.fetch", "+refs/heads/*:refs/heads/*")
    real_git = shutil.which("git")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fetch_log = tmp_path / "fetch.log"
    wrapper = bin_dir / "git"
    wrapper.write_text(
        f"#!{sys.executable}\n"
        "import os, pathlib, subprocess, sys\n"
        f"real_git = {real_git!r}\n"
        "args = sys.argv[1:]\n"
        "if args[:2] == ['remote', 'get-url']:\n"
        "    response = subprocess.run([real_git, *args], capture_output=True, text=True)\n"
        "    if response.returncode:\n"
        "        sys.exit(response.returncode)\n"
        "    key = 'BASE_PUSH_URL' if '--push' in args else 'BASE_FETCH_URL'\n"
        "    print(response.stdout.strip().replace(os.environ['BASE_REMOTE'], os.environ[key]))\n"
        "    sys.exit(0)\n"
        "if args and args[0] == 'fetch':\n"
        "    with pathlib.Path(os.environ['BASE_FETCH_LOG']).open('a') as log:\n"
        "        log.write('fetch\\n')\n"
        "    if os.environ.get('BASE_MOVE_ON_FETCH'):\n"
        "        subprocess.run([real_git, '-C', os.environ['BASE_REMOTE'], 'update-ref',\n"
        "                        'refs/heads/main', os.environ['BASE_MOVE_ON_FETCH']], check=True)\n"
        "if args and args[0] == 'ls-remote' and os.environ.get('BASE_REMOTE_ERROR'):\n"
        "    print(os.environ['BASE_REMOTE_ERROR'], file=sys.stderr)\n"
        "    sys.exit(128)\n"
        "os.execv(real_git, [real_git, *args])\n",
        encoding="utf-8",
    )
    wrapper.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("BASE_REMOTE", str(remote))
    monkeypatch.setenv("BASE_FETCH_URL", f"https://github.com/{REPO}.git")
    monkeypatch.setenv("BASE_PUSH_URL", f"git@github.com:{REPO}.git")
    monkeypatch.setenv("BASE_FETCH_LOG", str(fetch_log))
    return Repository(root, seed, remote, fetch_log)


def test_resolve_exact_origin_branch(repository: Repository) -> None:
    """Defaulting all requests to main, or returning a local feature SHA, loses integration work."""
    before = snapshot(repository.root)
    main = git(repository.remote, "rev-parse", "refs/heads/main")
    integration = git(repository.remote, "rev-parse", f"refs/heads/{INTEGRATION}")
    assert main != integration
    for args, branch, sha, content in (
        ([], "main", main, "main history"),
        (["--base", INTEGRATION], INTEGRATION, integration, "統合の履歴\nsecond line"),
    ):
        result = resolve(repository, *args)
        assert result.returncode == 0, result.stderr
        assert json.loads(result.stdout) == {
            "repo": REPO, "remote": "origin", "branch": branch,
            "ref": f"refs/heads/{branch}", "sha": sha,
        }
        assert git(repository.root, "cat-file", "-t", sha) == "commit"
        assert git(repository.root, "show", f"{sha}:content") == content
        assert snapshot(repository.root) == before


def test_rejects_wrong_target_and_required_base(repository: Repository, monkeypatch: pytest.MonkeyPatch) -> None:
    """Wrong fetch/push targets and dropped handoff requirements must stop before acquisition."""
    before = snapshot(repository.root)
    for key in ("BASE_FETCH_URL", "BASE_PUSH_URL"):
        with monkeypatch.context() as patch:
            patch.setenv(key, "https://github.com/usaturn/resoloop.git")
            rejected(resolve(repository))
        assert not repository.fetch_log.exists()
    for args in (
        ["--required-base", INTEGRATION],
        ["--base", "main", "--required-base", INTEGRATION],
        ["--base", INTEGRATION, "--required-base", INTEGRATION, "--required-base", "main"],
    ):
        rejected(resolve(repository, *args))
        assert not repository.fetch_log.exists()
    assert snapshot(repository.root) == before
    result = resolve(repository, "--base", INTEGRATION, "--required-base", INTEGRATION,
                     "--required-base", INTEGRATION)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["sha"] == git(repository.remote, "rev-parse", f"refs/heads/{INTEGRATION}")


def test_rejects_non_root_and_untracked_checkout(repository: Repository) -> None:
    """Accepting an ignored world/subdirectory could create a PR for a different tracked target."""
    (repository.root / ".gitignore").write_text("worlds/\n", encoding="utf-8")
    world = repository.root / "worlds" / "project"
    world.mkdir(parents=True)
    subdirectory = repository.root / "tracked-subdir"
    subdirectory.mkdir()
    before = snapshot(repository.root)
    for path in (world, subdirectory, repository.remote):
        rejected(resolve(repository, checkout=path))
        assert not repository.fetch_log.exists()
    assert snapshot(repository.root) == before
    assert resolve(repository).returncode == 0


def test_base_cannot_select_other_ref_or_revision(repository: Repository) -> None:
    """Revision expansion, tag fallback, and injected refspecs can silently select/overwrite other work."""
    before = snapshot(repository.root)
    for branch in (
        "tag-only", "missing", "@{-1}", "main~1", "refs/tags/tag-only", "refs/heads/main",
        "main:refs/heads/feature/local", "+main", "-main", "HEAD", "main*",
    ):
        rejected(resolve(repository, f"--base={branch}"))
        assert snapshot(repository.root) == before
        assert not repository.fetch_log.exists()
    assert resolve(repository, "--base", "main").returncode == 0


def test_base_movement_rejected(repository: Repository, monkeypatch: pytest.MonkeyPatch) -> None:
    """Rechecking a captured SHA must not silently adopt a moved remote base or reset the feature."""
    before = snapshot(repository.root)
    first = resolve(repository)
    assert first.returncode == 0, first.stderr
    captured = json.loads(first.stdout)["sha"]
    rechecked = resolve(repository, "--expected-sha", captured)
    assert rechecked.returncode == 0, rechecked.stderr
    assert json.loads(rechecked.stdout)["sha"] == captured
    advanced = git(repository.remote, "rev-parse", f"refs/heads/{INTEGRATION}")
    git(repository.remote, "update-ref", "refs/heads/main", advanced)
    rejected(resolve(repository, "--expected-sha", captured))
    assert snapshot(repository.root) == before
    # Also catch a movement between ls-remote and the exact fetch, even when the
    # captured object is already present locally from the previous invocation.
    git(repository.remote, "update-ref", "refs/heads/main", captured)
    monkeypatch.setenv("BASE_MOVE_ON_FETCH", advanced)
    rejected(resolve(repository, "--expected-sha", captured))
    assert snapshot(repository.root) == before


def test_inherited_git_environment_cannot_redirect_checkout(
    repository: Repository, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """GIT_DIR/config injection must not make a validated checkout read another repository's origin/base."""
    expected = git(repository.remote, "rev-parse", "refs/heads/main")
    # ls-remote/fetch keep the transport authentication names; an insteadOf left in
    # that environment would read another history's main while origin still verifies.
    wrong = tmp_path / "wrong.git"
    subprocess.run(["git", "init", "--bare", "--quiet", "--initial-branch=main", str(wrong)], check=True)
    git(repository.seed, "push", "--quiet", str(wrong), f"{INTEGRATION}:refs/heads/main")
    foreign_before = git(repository.seed, "for-each-ref")
    before = snapshot(repository.root)
    with monkeypatch.context() as patch:
        patch.setenv("GIT_DIR", str(repository.seed / ".git"))
        patch.setenv("GIT_WORK_TREE", str(repository.seed))
        patch.setenv("GIT_INDEX_FILE", str(tmp_path / "foreign-index"))
        patch.setenv("GIT_CONFIG_COUNT", "2")
        patch.setenv("GIT_CONFIG_KEY_0", "remote.origin.url")
        patch.setenv("GIT_CONFIG_VALUE_0", str(wrong))
        patch.setenv("GIT_CONFIG_KEY_1", f"url.{wrong}.insteadOf")
        patch.setenv("GIT_CONFIG_VALUE_1", str(repository.remote))
        result = resolve(repository)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["sha"] == expected
    assert snapshot(repository.root) == before
    assert git(repository.seed, "for-each-ref") == foreign_before
    assert not (tmp_path / "foreign-index").exists()


def test_remote_failure_does_not_expose_credentials(repository: Repository, monkeypatch: pytest.MonkeyPatch) -> None:
    """Git may echo credential URLs on transport failure; forwarding stderr leaks them into reports."""
    secret = "-".join(("base", "test", "credential"))
    monkeypatch.setenv("BASE_REMOTE_ERROR", f"fatal: https://user:{secret}@github.com/{REPO}.git failed")
    result = resolve(repository)
    rejected(result)
    assert secret not in result.stderr
    assert not repository.fetch_log.exists()
    monkeypatch.delenv("BASE_REMOTE_ERROR")
    assert resolve(repository).returncode == 0


def test_managed_base_read_requires_registered_common_dir(
    workspace: Workspace, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """S: a same-URL clone must not provide a plausible base from unrelated local history."""
    root = Path(__file__).resolve().parents[4]
    deployed = workspace.parent / ".agents/skills/issue-to-pr/scripts"
    shutil.copytree(SCRIPT.parent, deployed, ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(root / "tools/external_tools", workspace.parent / "tools/external_tools",
                    ignore=shutil.ignore_patterns("tests", "__pycache__"))
    sha = git(workspace.registered, "rev-parse", "HEAD")
    calls = tmp_path / "transport.log"
    bin_dir = tmp_path / "base-bin"
    bin_dir.mkdir()
    real_git = shutil.which("git")
    wrapper = bin_dir / "git"
    wrapper.write_text(
        f"#!{sys.executable}\nimport pathlib, os, sys\n"
        f"real = {real_git!r}\nargs = sys.argv[1:]\n"
        "if any(a in ('ls-remote', 'fetch', 'push') for a in args):\n"
        "    if args[0] not in ('ls-remote', 'fetch'): sys.exit(64)\n"
        f"    with pathlib.Path({str(calls)!r}).open('a') as f: f.write(args[0] + '\\n')\n"
        "    if args[0] == 'ls-remote':\n"
        f"        print({sha!r} + '\\t' + args[-1])\n"
        "    sys.exit(0)\n"
        "os.execv(real, [real, *args])\n")
    wrapper.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")

    def call(checkout: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, str(deployed / "resolve_base.py"),
                               "--checkout", str(checkout), "--repo", workspace.repository],
                              capture_output=True, text=True)

    rejected(call(workspace.other_clone))
    assert not calls.exists()
    result = call(workspace.linked)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["sha"] == sha
    assert calls.read_text().splitlines() == ["ls-remote", "fetch", "ls-remote"]


@dataclass
class AdvanceWorld:
    root: Path
    code_repo: str
    docs_separate: bool
    parent: Path
    parent_seed: Path
    parent_remote: Path
    code: Path
    code_seed: Path
    code_remote: Path


def call_base(*args: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *(str(arg) for arg in args)],
        capture_output=True, text=True, timeout=180,
    )


def install_advance_transport(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Only origin URL discovery is rewritten; all objects and refs stay in real local Git."""
    mapping = tmp_path / "url-map.json"
    mapping.write_text("{}", encoding="utf-8")
    bin_dir = tmp_path / "advance-bin"
    bin_dir.mkdir()
    real_git = shutil.which("git")
    wrapper = bin_dir / "git"
    wrapper.write_text(
        f"#!{sys.executable}\n"
        "import json, os, pathlib, subprocess, sys\n"
        f"real = {real_git!r}\n"
        "args = sys.argv[1:]\n"
        "if args[:2] == ['remote', 'get-url']:\n"
        "    response = subprocess.run([real, *args], capture_output=True, text=True)\n"
        "    if response.returncode:\n"
        "        sys.exit(response.returncode)\n"
        "    urls = json.loads(pathlib.Path(os.environ['BASE_URL_MAP']).read_text())\n"
        "    sys.stdout.write(urls.get(response.stdout.strip(), response.stdout))\n"
        "    sys.exit(0)\n"
        "os.execv(real, [real, *args])\n",
        encoding="utf-8",
    )
    wrapper.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("BASE_URL_MAP", str(mapping))
    return mapping


def make_pair(root: Path, name: str, repository: str, mapping: Path) -> tuple[Path, Path, Path]:
    root.mkdir(parents=True)
    remote, seed, checkout = root / "remote.git", root / "seed", root / "checkout with spaces"
    subprocess.run(["git", "init", "--bare", "--quiet", "--initial-branch=main", str(remote)], check=True)
    subprocess.run(["git", "init", "--quiet", "--initial-branch=main", str(seed)], check=True)
    git(seed, "config", "user.name", "Advance test")
    git(seed, "config", "user.email", "advance@example.test")
    (seed / "content.txt").write_text(f"{name} base\n", encoding="utf-8")
    git(seed, "add", "content.txt")
    git(seed, "commit", "--quiet", "-m", "base")
    git(seed, "remote", "add", "origin", str(remote))
    git(seed, "push", "--quiet", "origin", "--all")
    subprocess.run(
        ["git", "clone", "--quiet", "--single-branch", "--branch", "main", str(remote), str(checkout)],
        check=True,
    )
    git(checkout, "config", "user.name", "Advance test")
    git(checkout, "config", "user.email", "advance@example.test")
    urls = json.loads(mapping.read_text())
    urls[str(remote)] = f"https://github.com/{repository}.git"
    mapping.write_text(json.dumps(urls), encoding="utf-8")
    return remote, seed, checkout


def make_advance_world(
    root: Path, mapping: Path, *, code_repo: str = REPO, docs_separate: bool = False
) -> AdvanceWorld:
    parent_remote, parent_seed, parent = make_pair(root / "parent", "parent", REPO, mapping)
    code_remote, code_seed, code = make_pair(root / "code", "code", code_repo, mapping)
    return AdvanceWorld(root, code_repo, docs_separate, parent, parent_seed, parent_remote,
                        code, code_seed, code_remote)


def start_session(world: AdvanceWorld, name: str) -> Path:
    session = world.root / "sessions" / name
    session.mkdir(parents=True)
    (session / "target.json").write_text(json.dumps({
        "code_root": str(world.code),
        "parent_root": str(world.parent),
        "repository": world.code_repo,
        "document_repository": REPO if world.docs_separate else world.code_repo,
    }, ensure_ascii=False), encoding="utf-8")
    return session


def capture_bases(world: AdvanceWorld, session: Path) -> None:
    result = call_base("--checkout", world.code, "--repo", world.code_repo,
                       "--write-state", session / "code-base.json")
    assert result.returncode == 0, result.stderr
    if world.docs_separate:
        result = call_base("--checkout", world.parent, "--repo", REPO,
                           "--write-state", session / "docs-base.json")
        assert result.returncode == 0, result.stderr


def read_state(session: Path, target: str) -> dict[str, str]:
    return json.loads((session / f"{target}-base.json").read_text())


def write_owned(session: Path, code: list[str], docs: list[str] | None = None) -> Path:
    payload: dict[str, list[str]] = {"code": code}
    payload["docs"] = [] if docs is None else docs
    path = session / "owned-paths.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def write_premise(session: Path, text: str = "前提を確認した\n外部仕様は変わらない\n") -> Path:
    path = session / "advance-premise.txt"
    path.write_text(text, encoding="utf-8")
    return path


def worktree_path(world: AdvanceWorld, session: Path, target: str) -> Path:
    return world.root / "worktrees" / session.name / target


def inspect_advance(
    world: AdvanceWorld, session: Path, code_branch: str, doc_branch: str = "",
    *, owned: Path | None = None, code_root: Path | None = None, doc_root: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    args: list[object] = [
        "--inspect-advance", "--session", session,
        "--owned-paths-file", owned or session / "owned-paths.json",
        "--code-root", code_root or worktree_path(world, session, "code"),
        "--code-branch", code_branch,
    ]
    if world.docs_separate:
        args += ["--doc-root", doc_root or worktree_path(world, session, "docs"),
                 "--doc-branch", doc_branch]
    return call_base(*args)


def advance_base(
    world: AdvanceWorld, session: Path, code_branch: str, doc_branch: str = "",
    *, inspection: Path | None = None, premise: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    args: list[object] = [
        "--advance", "--session", session,
        "--inspection", inspection or session / "advance-inspection.json",
        "--owned-paths-file", session / "owned-paths.json",
        "--premise-file", premise or session / "advance-premise.txt",
        "--code-root", worktree_path(world, session, "code"),
        "--code-branch", code_branch,
    ]
    if world.docs_separate:
        args += ["--doc-root", worktree_path(world, session, "docs"), "--doc-branch", doc_branch]
    return call_base(*args)


def advance_remote(world: AdvanceWorld, target: str, files: dict[str, str], message: str) -> str:
    seed = world.code_seed if target == "code" else world.parent_seed
    git(seed, "switch", "--quiet", "main")
    # Start from the current remote tip so a test-side reset cannot leave a stale
    # parent commit in the next synthetic base advance.
    git(seed, "fetch", "--quiet", "origin", "main")
    git(seed, "reset", "--hard", "FETCH_HEAD")
    for name, content in files.items():
        path = seed / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    git(seed, "add", "-A")
    git(seed, "commit", "--quiet", "-m", message)
    sha = git(seed, "rev-parse", "HEAD")
    git(seed, "push", "--quiet", "origin", "HEAD:refs/heads/main")
    return sha


def advance_remote_rename(
    world: AdvanceWorld, target: str, old_path: str, new_path: str, message: str
) -> str:
    seed = world.code_seed if target == "code" else world.parent_seed
    git(seed, "switch", "--quiet", "main")
    git(seed, "fetch", "--quiet", "origin", "main")
    git(seed, "reset", "--hard", "FETCH_HEAD")
    git(seed, "mv", old_path, new_path)
    git(seed, "commit", "--quiet", "-m", message)
    sha = git(seed, "rev-parse", "HEAD")
    git(seed, "push", "--quiet", "origin", "HEAD:refs/heads/main")
    return sha


def set_remote(world: AdvanceWorld, target: str, sha: str) -> None:
    remote = world.code_remote if target == "code" else world.parent_remote
    git(remote, "update-ref", "refs/heads/main", sha)


def orphan_tip(world: AdvanceWorld, target: str) -> str:
    seed = world.code_seed if target == "code" else world.parent_seed
    git(seed, "checkout", "--quiet", "--orphan", "unrelated-root")
    (seed / "unrelated.txt").write_text("unrelated history\n", encoding="utf-8")
    git(seed, "add", "-A")
    git(seed, "commit", "--quiet", "-m", "unrelated root")
    sha = git(seed, "rev-parse", "HEAD")
    git(seed, "push", "--quiet", "origin", f"{sha}:refs/heads/unrelated-root")
    git(seed, "switch", "--quiet", "main")
    return sha


def add_worktree(world: AdvanceWorld, session: Path, target: str, branch: str, base_sha: str) -> Path:
    checkout = world.code if target == "code" else world.parent
    path = worktree_path(world, session, target)
    path.parent.mkdir(parents=True, exist_ok=True)
    git(checkout, "worktree", "add", "--quiet", "-b", branch, str(path), base_sha)
    return path


def commit_files(path: Path, files: dict[str, str], message: str) -> str:
    for name, content in files.items():
        file = path / name
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(content, encoding="utf-8")
    git(path, "add", "-A")
    git(path, "commit", "--quiet", "-m", message)
    return git(path, "rev-parse", "HEAD")


def advance_records(session: Path) -> list[dict[str, object]]:
    path = session / "base-advances.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def set_verify(session: Path, commands: list[object]) -> subprocess.CompletedProcess[str]:
    (session / "verify-cmds.json").write_text(json.dumps(commands, ensure_ascii=False), encoding="utf-8")
    return call_base("--set-verify-cmds", "--session", session,
                     "--commands-file", session / "verify-cmds.json")


def reverify(
    world: AdvanceWorld, session: Path, *, commands: Path | None = None
) -> subprocess.CompletedProcess[str]:
    args: list[object] = ["--reverify", "--session", session,
                          "--code-root", worktree_path(world, session, "code")]
    if world.docs_separate:
        args += ["--doc-root", worktree_path(world, session, "docs")]
    if commands is not None:
        args += ["--commands-file", commands]
    return call_base(*args)


def publish_gate(world: AdvanceWorld, session: Path) -> subprocess.CompletedProcess[str]:
    args: list[object] = ["--check-publish-gate", "--session", session,
                          "--code-root", worktree_path(world, session, "code")]
    if world.docs_separate:
        args += ["--doc-root", worktree_path(world, session, "docs")]
    return call_base(*args)


def pr_gate(
    world: AdvanceWorld, session: Path, code_body: Path, doc_body: str = ""
) -> subprocess.CompletedProcess[str]:
    args: list[object] = ["--check-pr-gate", "--session", session,
                          "--code-root", worktree_path(world, session, "code"),
                          "--code-pr-body", code_body]
    if world.docs_separate:
        args += ["--doc-root", worktree_path(world, session, "docs"), "--doc-pr-body", doc_body]
    return call_base(*args)


def test_advance_guards_and_state_chain(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """S: unpushed rebase/republish must not proceed with stale, overlapping, or unverified state."""
    mapping = install_advance_transport(tmp_path, monkeypatch)

    # A normal, unadvanced run keeps every existing workflow: both gates answer 0 without
    # owned paths, verification commands, reverified state, or PR text.
    normal = make_advance_world(tmp_path / "normal", mapping)
    plain = start_session(normal, "plain")
    capture_bases(normal, plain)
    initial = read_state(plain, "code")
    doubles = call_base("--checkout", normal.code, "--repo", normal.code_repo,
                        "--write-state", plain / "code-base.json")
    rejected(doubles)
    assert read_state(plain, "code") == initial
    link = plain / "linked-base.json"
    link.symlink_to(plain / "code-base.json")
    rejected(call_base("--checkout", normal.code, "--repo", normal.code_repo,
                       "--write-state", link))
    assert not (plain / "linked-base.initial.json").exists()
    assert call_base("--check-publish-gate", "--session", plain,
                     "--code-root", tmp_path / "not-created").returncode == 0
    assert call_base("--check-pr-gate", "--session", plain,
                     "--code-root", tmp_path / "not-created",
                     "--code-pr-body", tmp_path / "missing.md").returncode == 0

    # Pre-worktree advance: guards, inspection, rollback on a live movement, and the
    # old verification records being invalidated without being reused as commands.
    flow = start_session(normal, "flow")
    capture_bases(normal, flow)
    flow_initial = read_state(flow, "code")
    write_owned(flow, ["src/ours"])
    first_tip = advance_remote(normal, "code", {"incoming.txt": "base change\n"}, "advance one")
    empty = flow / "empty-owned.json"
    empty.write_text(json.dumps({"code": []}), encoding="utf-8")
    rejected(inspect_advance(normal, flow, "feat/flow", owned=empty))
    duplicate = flow / "duplicate-owned.json"
    duplicate.write_text(json.dumps({"code": ["src/ours", "src/ours/file.txt"]}), encoding="utf-8")
    rejected(inspect_advance(normal, flow, "feat/flow", owned=duplicate))
    invalid = flow / "invalid-owned.json"
    for bad_path in ("/absolute", "src/../bad", "src//bad", "src/./bad", "", "src\\bad"):
        invalid.write_text(json.dumps({"code": [bad_path]}), encoding="utf-8")
        rejected(inspect_advance(normal, flow, "feat/flow", owned=invalid))
    docs_in_code = flow / "docs-in-code.json"
    docs_in_code.write_text(json.dumps({"code": ["src/ours"], "docs": ["docs"]}), encoding="utf-8")
    rejected(inspect_advance(normal, flow, "feat/flow", owned=docs_in_code))
    set_remote(normal, "code", flow_initial["sha"])
    advance_remote(normal, "code", {"src/ours/base.txt": "owned overlap\n"}, "owned overlap")
    rejected(inspect_advance(normal, flow, "feat/flow"))
    assert read_state(flow, "code") == flow_initial
    set_remote(normal, "code", first_tip)
    git(normal.code_remote, "update-ref", "refs/heads/feat/flow", flow_initial["sha"])
    rejected(inspect_advance(normal, flow, "feat/flow"))
    git(normal.code_remote, "update-ref", "-d", "refs/heads/feat/flow")
    unrelated = orphan_tip(normal, "code")
    set_remote(normal, "code", unrelated)
    rejected(inspect_advance(normal, flow, "feat/flow"))
    set_remote(normal, "code", first_tip)
    (flow / "checks.json").write_text(json.dumps({
        "head": flow_initial["sha"], "base": flow_initial["sha"],
        "commands": [{"argv": ["old"], "exit_code": 0}],
    }), encoding="utf-8")
    (flow / "reverified.json").write_text("{}\n", encoding="utf-8")
    (flow / "code-sha.txt").write_text(f"{flow_initial['sha']}\n", encoding="utf-8")
    inspection = inspect_advance(normal, flow, "feat/flow")
    assert inspection.returncode == 0, inspection.stderr
    inspected = json.loads(inspection.stdout)
    assert inspected["phase"] == "pre_worktree"
    assert inspected["docs_separate"] is False
    assert inspected["targets"]["code"]["advanced"] is True
    assert inspected["targets"]["code"]["old_sha"] == flow_initial["sha"]
    assert inspected["targets"]["code"]["new_sha"] == first_tip
    assert [commit["sha"] for commit in inspected["targets"]["code"]["commits"]] == [first_tip]
    (flow / "advance-inspection.json").write_text(inspection.stdout, encoding="utf-8")
    assert (flow / "checks.json").exists()
    rejected(advance_base(normal, flow, "feat/flow", premise=write_premise(flow, "\n")))
    assert read_state(flow, "code") == flow_initial
    assert not (flow / "base-advances.jsonl").exists()
    advance_remote(normal, "code", {"second.txt": "live movement\n"}, "advance live")
    rejected(advance_base(normal, flow, "feat/flow"))
    assert read_state(flow, "code") == flow_initial
    assert not (flow / "base-advances.jsonl").exists()
    set_remote(normal, "code", first_tip)
    inspection = inspect_advance(normal, flow, "feat/flow")
    assert inspection.returncode == 0, inspection.stderr
    (flow / "advance-inspection.json").write_text(inspection.stdout, encoding="utf-8")
    write_premise(flow)
    advanced = advance_base(normal, flow, "feat/flow")
    assert advanced.returncode == 0, advanced.stderr
    flow_state = read_state(flow, "code")
    assert flow_state["sha"] == first_tip
    assert json.loads((flow / "code-base.initial.json").read_text())["sha"] == flow_initial["sha"]
    first_record = advance_records(flow)[0]
    assert first_record["phase"] == "pre_worktree"
    assert first_record["old_head"] is None and first_record["new_head"] is None
    assert first_record["old_sha"] == flow_initial["sha"] and first_record["new_sha"] == first_tip
    assert first_record["changed_files"] == ["incoming.txt"]
    assert first_record["premise_note"].strip()
    for stale in ("checks.json", "reverified.json", "code-sha.txt"):
        assert not (flow / stale).exists()
    assert not (flow / "required-verify-cmds.json").exists()

    # A manual state rewrite, a schema violation, and a broken chain are all rejected.
    state_bytes = (flow / "code-base.json").read_bytes()
    rewritten = json.loads(state_bytes)
    rewritten["sha"] = flow_initial["sha"]
    (flow / "code-base.json").write_text(json.dumps(rewritten), encoding="utf-8")
    rejected(publish_gate(normal, flow))
    (flow / "code-base.json").write_bytes(state_bytes)
    advances_bytes = (flow / "base-advances.jsonl").read_bytes()
    bad_record = dict(first_record)
    bad_record["old_head"] = flow_initial["sha"]
    (flow / "base-advances.jsonl").write_text(json.dumps(bad_record) + "\n", encoding="utf-8")
    rejected(publish_gate(normal, flow))
    (flow / "base-advances.jsonl").write_bytes(advances_bytes)
    (flow / "base-advances.jsonl").unlink()
    rejected(publish_gate(normal, flow))
    (flow / "base-advances.jsonl").write_bytes(advances_bytes)
    wrong_target = dict(first_record)
    wrong_target["target"] = "docs"
    (flow / "base-advances.jsonl").write_text(json.dumps(wrong_target) + "\n", encoding="utf-8")
    rejected(publish_gate(normal, flow))
    (flow / "base-advances.jsonl").write_bytes(advances_bytes)

    # A clean linear worktree rejects dirty state, overlapping base files, and a real
    # rename/rename merge conflict without changing HEAD or the captured state.
    code_root = add_worktree(normal, flow, "code", "feat/flow", flow_state["sha"])
    commit_files(code_root, {"src/ours/file.txt": "ours\n", "shared.txt": "work\n"}, "work")
    git(code_root, "mv", "content.txt", "other.txt")
    git(code_root, "commit", "--quiet", "-m", "rename content")
    (code_root / "shared.txt").write_text("dirty\n", encoding="utf-8")
    head_before, state_before = git(code_root, "rev-parse", "HEAD"), state_bytes
    rejected(inspect_advance(normal, flow, "feat/flow"))
    assert git(code_root, "rev-parse", "HEAD") == head_before
    assert (flow / "code-base.json").read_bytes() == state_before
    git(code_root, "checkout", "--quiet", "--", "shared.txt")
    advance_remote(normal, "code", {"shared.txt": "base shared\n"}, "base shared")
    rejected(inspect_advance(normal, flow, "feat/flow"))
    assert git(code_root, "rev-parse", "HEAD") == head_before
    assert (flow / "code-base.json").read_bytes() == state_before
    set_remote(normal, "code", flow_state["sha"])
    advance_remote_rename(normal, "code", "content.txt", "new.txt", "base rename")
    rejected(inspect_advance(normal, flow, "feat/flow"))
    assert git(code_root, "rev-parse", "HEAD") == head_before
    assert (flow / "code-base.json").read_bytes() == state_before
    set_remote(normal, "code", flow_state["sha"])
    conflict_tip = advance_remote(normal, "code", {"incoming2.txt": "base two\n"}, "advance two")
    inspection = inspect_advance(normal, flow, "feat/flow")
    assert inspection.returncode == 0, inspection.stderr
    inspected = json.loads(inspection.stdout)
    assert inspected["phase"] == "worktree"
    assert inspected["targets"]["code"]["new_sha"] == conflict_tip
    (flow / "advance-inspection.json").write_text(inspection.stdout, encoding="utf-8")
    worktree_state_bytes = (flow / "code-base.json").read_bytes()
    (code_root / "shared.txt").write_text("changed after inspection\n", encoding="utf-8")
    rejected(advance_base(normal, flow, "feat/flow"))
    assert git(code_root, "rev-parse", "HEAD") == head_before
    assert (flow / "code-base.json").read_bytes() == worktree_state_bytes
    git(code_root, "checkout", "--quiet", "--", "shared.txt")
    inspection = inspect_advance(normal, flow, "feat/flow")
    assert inspection.returncode == 0, inspection.stderr
    (flow / "advance-inspection.json").write_text(inspection.stdout, encoding="utf-8")
    rebased = advance_base(normal, flow, "feat/flow")
    assert rebased.returncode == 0, rebased.stderr
    second_record = advance_records(flow)[1]
    new_head = git(code_root, "rev-parse", "HEAD")
    assert second_record["phase"] == "worktree"
    assert second_record["old_head"] == head_before
    assert second_record["new_head"] == new_head
    assert second_record["new_sha"] == conflict_tip
    assert read_state(flow, "code")["sha"] == conflict_tip
    assert subprocess.run(["git", "-C", str(code_root), "merge-base", "--is-ancestor",
                           conflict_tip, "HEAD"]).returncode == 0

    # The required command list is fixed, and an incomplete list or a failing command
    # cannot leave a passing verification record.
    commands = [["bash", "-c", "test -f src/ours/file.txt"],
                {"cwd": "code", "argv": ["bash", "-c", "test -f shared.txt"]}]
    assert set_verify(flow, commands).returncode == 0
    assert set_verify(flow, commands).returncode == 0
    required = json.loads((flow / "required-verify-cmds.json").read_text())
    rejected(set_verify(flow, commands[:1]))
    rejected(set_verify(flow, [{"cwd": "code", "argv": commands[0]}]))
    rejected(set_verify(flow, [{"cwd": "docs", "argv": ["bash", "-c", "true"]}]))
    assert json.loads((flow / "required-verify-cmds.json").read_text()) == required
    partial = flow / "partial-cmds.json"
    partial.write_text(json.dumps(commands[:1]), encoding="utf-8")
    rejected(reverify(normal, flow, commands=partial))
    assert not (flow / "reverified.json").exists()
    verified = reverify(normal, flow)
    assert verified.returncode == 0, verified.stderr
    reverified = json.loads((flow / "reverified.json").read_text())
    assert reverified["advance_count"] == 2
    assert reverified["code_base_sha"] == conflict_tip
    assert reverified["code_head_sha"] == new_head
    assert reverified["doc_base_sha"] is None and reverified["doc_head_sha"] is None
    assert [{"cwd": item["cwd"], "argv": item["argv"]} for item in reverified["commands"]] == required
    checks = json.loads((flow / "checks.json").read_text())
    assert checks["head"] == new_head and checks["base"] == conflict_tip
    for item in reverified["commands"]:
        assert Path(item["log_path"]).is_file()
    assert publish_gate(normal, flow).returncode == 0
    first_log = Path(reverified["commands"][0]["log_path"])
    first_log_bytes = first_log.read_bytes()
    first_log.write_text("tampered\n", encoding="utf-8")
    rejected(publish_gate(normal, flow))
    first_log.write_bytes(first_log_bytes)
    assert publish_gate(normal, flow).returncode == 0

    # A failing reverify deletes old passing records and writes no new ones.
    original_required = (flow / "required-verify-cmds.json").read_text()
    (flow / "required-verify-cmds.json").write_text(json.dumps(
        [{"cwd": "code", "argv": ["bash", "-c", "exit 1"]}]), encoding="utf-8")
    rejected(reverify(normal, flow))
    assert not (flow / "reverified.json").exists()
    assert not (flow / "checks.json").exists()
    (flow / "required-verify-cmds.json").unlink()
    assert set_verify(flow, commands).returncode == 0
    assert (flow / "required-verify-cmds.json").read_text() == original_required
    assert reverify(normal, flow).returncode == 0

    # PR text must record every old/new SHA and every required command. A later commit
    # makes the verification stale and blocks publishing again.
    body = flow / "body.md"
    body.write_text("本文\n", encoding="utf-8")
    (flow / "code-sha.txt").write_text("0" * 40 + "\n", encoding="utf-8")
    rejected(pr_gate(normal, flow, body))
    (flow / "code-sha.txt").write_text(f"{new_head}\n", encoding="utf-8")
    rejected(pr_gate(normal, flow, body))
    lines = []
    for record in advance_records(flow):
        lines.append(f"{record['old_sha'][:7]} -> {record['new_sha'][:7]}")
    for command in required:
        lines.append(" ".join(command["argv"]))
        lines.append(shlex.join(command["argv"]))
    body.write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert pr_gate(normal, flow, body).returncode == 0
    commit_files(code_root, {"stale.txt": "later\n"}, "later commit")
    rejected(publish_gate(normal, flow))

    # Three consecutive advances succeed; the fourth is refused with no further state change.
    limits = make_advance_world(tmp_path / "limits", mapping)
    limited = start_session(limits, "limits")
    capture_bases(limits, limited)
    write_owned(limited, ["src/ours"])
    write_premise(limited)
    last_tip = ""
    for number in range(1, 4):
        if number == 2:
            # A valid last line without a newline must not be concatenated with the next record.
            records_path = limited / "base-advances.jsonl"
            records_path.write_bytes(records_path.read_bytes().rstrip(b"\n"))
        last_tip = advance_remote(limits, "code", {
            f"limit-{number}.txt": f"advance {number}\n"}, f"limit {number}")
        inspection = inspect_advance(limits, limited, "feat/limits")
        assert inspection.returncode == 0, inspection.stderr
        (limited / "advance-inspection.json").write_text(inspection.stdout, encoding="utf-8")
        assert advance_base(limits, limited, "feat/limits").returncode == 0
        assert len(advance_records(limited)) == number
    assert read_state(limited, "code")["sha"] == last_tip
    advance_remote(limits, "code", {"limit-4.txt": "too many\n"}, "limit four")
    rejected(inspect_advance(limits, limited, "feat/limits"))
    assert len(advance_records(limited)) == 3
    assert read_state(limited, "code")["sha"] == last_tip

    # Separate documents: both repositories advance and rebase, docs ownership is checked,
    # and a docs-cwd verification command runs in DOC_ROOT.
    separate = make_advance_world(tmp_path / "separate", mapping,
                                  code_repo="usaturn/resoloop", docs_separate=True)
    docs_session = start_session(separate, "separate")
    capture_bases(separate, docs_session)
    code_initial = read_state(docs_session, "code")
    docs_initial = read_state(docs_session, "docs")
    write_owned(docs_session, ["src/ours"], ["docs/superpowers/specs"])
    empty_docs = docs_session / "empty-docs.json"
    empty_docs.write_text(json.dumps({"code": ["src/ours"], "docs": []}), encoding="utf-8")
    rejected(inspect_advance(separate, docs_session, "feat/separate", "docs/separate", owned=empty_docs))
    duplicate_docs = docs_session / "duplicate-docs.json"
    duplicate_docs.write_text(json.dumps({
        "code": ["src/ours"],
        "docs": ["docs/superpowers/specs", "docs/superpowers/specs/spec.md"],
    }), encoding="utf-8")
    rejected(inspect_advance(separate, docs_session, "feat/separate", "docs/separate",
                            owned=duplicate_docs))
    empty_code = docs_session / "empty-code.json"
    empty_code.write_text(json.dumps({"code": [], "docs": ["docs/superpowers/specs"]}), encoding="utf-8")
    rejected(inspect_advance(separate, docs_session, "feat/separate", "docs/separate", owned=empty_code))
    git(separate.parent_remote, "update-ref", "refs/heads/docs/separate", docs_initial["sha"])
    rejected(inspect_advance(separate, docs_session, "feat/separate", "docs/separate"))
    git(separate.parent_remote, "update-ref", "-d", "refs/heads/docs/separate")
    partial_root = worktree_path(separate, docs_session, "code")
    partial_root.mkdir(parents=True)
    rejected(inspect_advance(separate, docs_session, "feat/separate", "docs/separate"))
    partial_root.rmdir()
    code_root = add_worktree(separate, docs_session, "code", "feat/separate", code_initial["sha"])
    doc_root = add_worktree(separate, docs_session, "docs", "docs/separate", docs_initial["sha"])
    commit_files(code_root, {"src/feature.txt": "code work\n"}, "code work")
    commit_files(doc_root, {"docs/superpowers/specs/spec.md": "design\n"}, "docs work")
    code_head_before = git(code_root, "rev-parse", "HEAD")
    doc_head_before = git(doc_root, "rev-parse", "HEAD")
    code_tip = advance_remote(separate, "code", {"incoming-code.txt": "code base\n"}, "code base")
    advance_remote(separate, "docs", {"docs/superpowers/specs/base.md": "docs base\n"}, "docs overlap")
    rejected(inspect_advance(separate, docs_session, "feat/separate", "docs/separate"))
    assert git(code_root, "rev-parse", "HEAD") == code_head_before
    assert git(doc_root, "rev-parse", "HEAD") == doc_head_before
    set_remote(separate, "docs", docs_initial["sha"])
    docs_tip = advance_remote(separate, "docs", {"incoming-docs.txt": "docs base\n"}, "docs base")
    inspection = inspect_advance(separate, docs_session, "feat/separate", "docs/separate")
    assert inspection.returncode == 0, inspection.stderr
    inspected = json.loads(inspection.stdout)
    assert inspected["docs_separate"] is True
    assert inspected["targets"]["code"]["new_sha"] == code_tip
    assert inspected["targets"]["docs"]["new_sha"] == docs_tip
    (docs_session / "advance-inspection.json").write_text(inspection.stdout, encoding="utf-8")
    write_premise(docs_session)
    assert advance_base(separate, docs_session, "feat/separate", "docs/separate").returncode == 0
    assert read_state(docs_session, "code")["sha"] == code_tip
    assert read_state(docs_session, "docs")["sha"] == docs_tip
    records = advance_records(docs_session)
    assert {record["target"] for record in records} == {"code", "docs"}
    assert all(isinstance(record["old_head"], str) and isinstance(record["new_head"], str)
               for record in records)
    assert git(code_root, "rev-parse", "HEAD") != code_head_before
    assert git(doc_root, "rev-parse", "HEAD") != doc_head_before
    commands = [["bash", "-c", "test -f src/feature.txt"],
                {"cwd": "docs", "argv": ["bash", "-c",
                                            "test -f docs/superpowers/specs/spec.md"]},
                {"cwd": "parent", "argv": ["bash", "-c", "test -f content.txt"]}]
    assert set_verify(docs_session, commands).returncode == 0
    verified = reverify(separate, docs_session)
    assert verified.returncode == 0, verified.stderr
    reverified = json.loads((docs_session / "reverified.json").read_text())
    assert reverified["docs_separate"] is True
    assert reverified["advance_count"] == 2
    assert reverified["doc_base_sha"] == docs_tip
    assert {item["cwd"] for item in reverified["commands"]} == {"code", "docs", "parent"}
    assert publish_gate(separate, docs_session).returncode == 0
    (docs_session / "code-sha.txt").write_text(reverified["code_head_sha"] + "\n", encoding="utf-8")
    (docs_session / "docs-sha.txt").write_text(reverified["doc_head_sha"] + "\n", encoding="utf-8")
    required = json.loads((docs_session / "required-verify-cmds.json").read_text())
    code_body = docs_session / "code-body.md"
    code_lines = [f"{record['old_sha'][:7]} -> {record['new_sha'][:7]}" for record in records]
    code_lines += [" ".join(command["argv"]) for command in required]
    code_body.write_text("\n".join(code_lines) + "\n", encoding="utf-8")
    rejected(pr_gate(separate, docs_session, code_body))
    doc_body = "\n".join(
        f"{record['old_sha'][:7]} -> {record['new_sha'][:7]}"
        for record in records if record["target"] == "docs"
    )
    assert pr_gate(separate, docs_session, code_body, doc_body).returncode == 0
