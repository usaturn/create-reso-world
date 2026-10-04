"""Behavior tests for ``scripts/ff_merge_keep_untracked.sh``.

The script fast-forwards a branch whose merge is blocked by untracked files
that the incoming commits would overwrite. It must never lose such a file:
every one is restored (symlinks as symlinks) whether the fast-forward
succeeds or fails, and the target repository is selected by ``--repo`` only.
"""
from __future__ import annotations

import os
import shutil
import signal
import subprocess
import time
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "ff_merge_keep_untracked.sh"


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


@pytest.fixture(autouse=True)
def backups_in_tmp_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Keep the script's backup directories inside the test's tmp_path."""
    backups = tmp_path / "backups"
    backups.mkdir()
    monkeypatch.setenv("TMPDIR", str(backups))
    return backups


def run_script(
    *args: str, cwd: Path | None = None, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        capture_output=True,
        text=True,
        cwd=cwd,
        env=env,
        timeout=60,
    )


def configure(repo: Path) -> None:
    git(repo, "config", "user.email", "test@example.com")
    git(repo, "config", "user.name", "Test")


def status(repo: Path) -> set[str]:
    out = git(repo, "status", "--porcelain=v1", "-z", "--untracked-files=all")
    return {entry for entry in out.split("\0") if entry}


@pytest.fixture()
def behind(tmp_path: Path) -> Path:
    """A clone whose main is one commit behind origin/main.

    origin/main adds ``same.md``, ``differs.md``, ``sub dir/nested.md`` and the
    symlink ``link.md``; the clone has not merged that commit yet.
    """
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "-q", "-b", "main", "--bare", str(remote)], check=True)
    work = tmp_path / "work"
    subprocess.run(["git", "clone", "-q", str(remote), str(work)], check=True, capture_output=True)
    configure(work)
    (work / "base.txt").write_text("base\n", encoding="utf-8")
    git(work, "add", "base.txt")
    git(work, "commit", "-qm", "base")
    git(work, "push", "-q", "origin", "HEAD:main")
    git(work, "branch", "-u", "origin/main")

    upstream = tmp_path / "upstream"
    subprocess.run(["git", "clone", "-q", str(remote), str(upstream)], check=True, capture_output=True)
    configure(upstream)
    (upstream / "same.md").write_text("same\n", encoding="utf-8")
    (upstream / "differs.md").write_text("upstream\n", encoding="utf-8")
    (upstream / "sub dir").mkdir()
    (upstream / "sub dir" / "nested.md").write_text("upstream nested\n", encoding="utf-8")
    (upstream / "link.md").symlink_to("base.txt")
    git(upstream, "add", "-A")
    git(upstream, "commit", "-qm", "upstream")
    git(upstream, "push", "-q", "origin", "HEAD:main")

    git(work, "fetch", "-q", "origin")
    return work


def add_conflicting_untracked_files(work: Path) -> None:
    (work / "same.md").write_text("same\n", encoding="utf-8")
    (work / "differs.md").write_text("local draft\n", encoding="utf-8")
    (work / "differs.md").chmod(0o600)
    (work / "sub dir").mkdir()
    (work / "sub dir" / "nested.md").write_text("local nested\n", encoding="utf-8")
    (work / "link.md").symlink_to("differs.md")


def assert_local_files_kept(work: Path) -> None:
    assert (work / "same.md").read_text(encoding="utf-8") == "same\n"
    assert (work / "differs.md").read_text(encoding="utf-8") == "local draft\n"
    assert (work / "differs.md").stat().st_mode & 0o777 == 0o600
    assert (work / "sub dir" / "nested.md").read_text(encoding="utf-8") == "local nested\n"
    assert (work / "link.md").is_symlink(), "a symlink must be restored as a symlink"
    assert os.readlink(work / "link.md") == "differs.md"


def test_plain_merge_is_blocked_by_the_fixture(behind: Path) -> None:
    add_conflicting_untracked_files(behind)
    result = subprocess.run(
        ["git", "-C", str(behind), "merge", "--ff-only", "origin/main"],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "untracked working tree files would be overwritten" in result.stderr


def test_fast_forwards_and_restores_every_conflicting_file(behind: Path, tmp_path: Path) -> None:
    add_conflicting_untracked_files(behind)
    upstream_head = git(behind, "rev-parse", "origin/main").strip()

    # Run from outside the repository and point --repo at a subdirectory.
    result = run_script("--repo", str(behind / "sub dir"), "--ref", "origin/main", cwd=tmp_path)
    assert result.returncode == 0, (result.stdout, result.stderr)

    assert git(behind, "rev-parse", "HEAD").strip() == upstream_head
    assert_local_files_kept(behind)
    # Identical files become clean; local drafts stay as modifications.
    assert status(behind) == {" M differs.md", " M link.md", " M sub dir/nested.md"}


def test_failed_fast_forward_restores_everything_and_keeps_head(behind: Path) -> None:
    add_conflicting_untracked_files(behind)
    # A tracked file with local changes that origin/main also changes makes
    # `git merge --ff-only` fail after the untracked files were moved away.
    (behind / "base.txt").write_text("local edit\n", encoding="utf-8")
    remote_main = git(behind, "rev-parse", "origin/main").strip()
    upstream = behind.parent / "upstream"
    (upstream / "base.txt").write_text("upstream edit\n", encoding="utf-8")
    git(upstream, "commit", "-qam", "edit base")
    git(upstream, "push", "-q", "origin", "HEAD:main")
    git(behind, "fetch", "-q", "origin")
    assert git(behind, "rev-parse", "origin/main").strip() != remote_main
    head = git(behind, "rev-parse", "HEAD").strip()

    result = run_script("--repo", str(behind), "--ref", "origin/main")
    assert result.returncode == 1, (result.stdout, result.stderr)
    assert "HEAD is unchanged" in result.stderr

    assert git(behind, "rev-parse", "HEAD").strip() == head
    assert_local_files_kept(behind)
    assert (behind / "base.txt").read_text(encoding="utf-8") == "local edit\n"


def test_not_a_fast_forward_changes_nothing(behind: Path) -> None:
    add_conflicting_untracked_files(behind)
    (behind / "base.txt").write_text("diverge\n", encoding="utf-8")
    git(behind, "commit", "-qam", "diverge")
    head = git(behind, "rev-parse", "HEAD").strip()

    result = run_script("--repo", str(behind), "--ref", "origin/main")
    assert result.returncode == 1, (result.stdout, result.stderr)
    assert "not a fast-forward" in result.stderr
    assert git(behind, "rev-parse", "HEAD").strip() == head
    assert_local_files_kept(behind)


def test_backup_failure_changes_nothing(behind: Path, tmp_path: Path) -> None:
    add_conflicting_untracked_files(behind)
    head = git(behind, "rev-parse", "HEAD").strip()
    env = {**os.environ, "TMPDIR": str(tmp_path / "missing")}

    result = run_script("--repo", str(behind), "--ref", "origin/main", env=env)
    assert result.returncode == 1, (result.stdout, result.stderr)
    assert "nothing was changed" in result.stderr
    assert git(behind, "rev-parse", "HEAD").strip() == head
    assert_local_files_kept(behind)


def test_without_conflicts_it_only_fast_forwards(behind: Path) -> None:
    result = run_script("--repo", str(behind), "--ref", "origin/main")
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert git(behind, "rev-parse", "HEAD").strip() == git(behind, "rev-parse", "origin/main").strip()
    assert status(behind) == set()


def test_already_up_to_date_is_a_noop(behind: Path) -> None:
    git(behind, "merge", "-q", "--ff-only", "origin/main")
    result = run_script("--repo", str(behind), "--ref", "origin/main")
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert "already up to date" in result.stdout


def test_inherited_git_dir_does_not_redirect_the_target(behind: Path, tmp_path: Path) -> None:
    other = tmp_path / "other"
    other.mkdir()
    subprocess.run(["git", "init", "-q", str(other)], check=True)
    add_conflicting_untracked_files(behind)
    env = {**os.environ, "GIT_DIR": str(other / ".git"), "GIT_WORK_TREE": str(other)}

    result = run_script("--repo", str(behind), "--ref", "origin/main", env=env)
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert git(behind, "rev-parse", "HEAD").strip() == git(behind, "rev-parse", "origin/main").strip()
    assert_local_files_kept(behind)


@pytest.mark.parametrize(
    "args",
    [
        (),
        ("--ref",),
        ("--ref", "no-such-ref"),
        ("--ref", "origin/main", "--force"),
    ],
)
def test_usage_errors_change_nothing(behind: Path, args: tuple[str, ...]) -> None:
    add_conflicting_untracked_files(behind)
    head = git(behind, "rev-parse", "HEAD").strip()
    result = run_script(*args, cwd=behind)
    assert result.returncode == 2, (result.stdout, result.stderr)
    assert git(behind, "rev-parse", "HEAD").strip() == head
    assert_local_files_kept(behind)


def test_outside_a_work_tree_is_a_usage_error(tmp_path: Path) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()
    result = run_script("--repo", str(plain), "--ref", "HEAD")
    assert result.returncode == 2
    assert "not a git work tree" in result.stderr


def push_upstream(behind: Path, files: dict[str, str]) -> None:
    upstream = behind.parent / "upstream"
    for name, content in files.items():
        (upstream / name).parent.mkdir(parents=True, exist_ok=True)
        (upstream / name).write_text(content, encoding="utf-8")
    git(upstream, "add", "-f", "-A")
    git(upstream, "commit", "-qm", "more upstream")
    git(upstream, "push", "-q", "origin", "HEAD:main")
    git(behind, "fetch", "-q", "origin")


def test_ignored_file_on_an_added_path_is_kept(behind: Path) -> None:
    # git merge overwrites ignored files without asking; the script must not.
    push_upstream(behind, {"secret.env": "upstream\n"})
    with (behind / ".git" / "info" / "exclude").open("a", encoding="utf-8") as exclude:
        exclude.write("*.env\n")
    add_conflicting_untracked_files(behind)
    (behind / "secret.env").write_text("local secret\n", encoding="utf-8")

    result = run_script("--repo", str(behind), "--ref", "origin/main")
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert (behind / "secret.env").read_text(encoding="utf-8") == "local secret\n"
    assert_local_files_kept(behind)


def test_files_under_a_directory_or_a_symlink_named_like_an_added_path_are_left_alone(
    behind: Path, tmp_path: Path
) -> None:
    # origin/main adds the file "plain" and "linked/inner.md". Locally "plain"
    # is a directory and "linked" a symlink to a directory outside the work
    # tree; neither may be backed up, removed or written through.
    push_upstream(behind, {"plain": "upstream\n", "linked/inner.md": "upstream\n"})
    (behind / "plain").mkdir()
    (behind / "plain" / "draft.md").write_text("draft\n", encoding="utf-8")
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "inner.md").write_text("precious\n", encoding="utf-8")
    (behind / "linked").symlink_to(outside)
    head = git(behind, "rev-parse", "HEAD").strip()

    result = run_script("--repo", str(behind), "--ref", "origin/main")
    assert result.returncode == 1, (result.stdout, result.stderr)
    assert git(behind, "rev-parse", "HEAD").strip() == head
    assert (behind / "plain" / "draft.md").read_text(encoding="utf-8") == "draft\n"
    assert (behind / "linked").is_symlink()
    assert (outside / "inner.md").read_text(encoding="utf-8") == "precious\n"


def test_interrupted_run_restores_files_and_reports_head(behind: Path, tmp_path: Path) -> None:
    # A slow smudge filter keeps the fast-forward busy; TERM reaches only the
    # script, which runs its trap once git has finished.
    started = tmp_path / "smudge-started"
    git(behind, "config", "filter.slow.smudge", f': >"{started}"; sleep 3; cat')
    push_upstream(behind, {".gitattributes": "*.slow filter=slow\n", "big.slow": "data\n"})
    add_conflicting_untracked_files(behind)

    script = subprocess.Popen(
        ["bash", str(SCRIPT), "--repo", str(behind), "--ref", "origin/main"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    deadline = time.monotonic() + 30
    while not started.exists():
        assert script.poll() is None, script.communicate()
        assert time.monotonic() < deadline, "the smudge filter never ran"
        time.sleep(0.05)
    script.send_signal(signal.SIGTERM)
    stdout, stderr = script.communicate(timeout=60)

    assert script.returncode == 1, (stdout, stderr)
    assert "interrupted after the fast-forward" in stderr
    assert git(behind, "rev-parse", "HEAD").strip() == git(behind, "rev-parse", "origin/main").strip()
    assert_local_files_kept(behind)


def test_failure_to_list_candidates_changes_nothing(behind: Path, tmp_path: Path) -> None:
    # Without the candidate list a plain merge would overwrite ignored files,
    # so a failing step (here: no `comm`) must stop the run before any change.
    push_upstream(behind, {"secret.env": "upstream\n"})
    with (behind / ".git" / "info" / "exclude").open("a", encoding="utf-8") as exclude:
        exclude.write("*.env\n")
    (behind / "secret.env").write_text("local secret\n", encoding="utf-8")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for tool in ("bash", "cat", "cmp", "cp", "dirname", "git", "mkdir", "mktemp", "readlink", "rm", "sort", "stat", "xargs"):
        target = shutil.which(tool)
        assert target, f"{tool} is required for this test"
        (bin_dir / tool).symlink_to(target)
    head = git(behind, "rev-parse", "HEAD").strip()

    result = run_script("--repo", str(behind), "--ref", "origin/main", env={**os.environ, "PATH": str(bin_dir)})
    assert result.returncode == 1, (result.stdout, result.stderr)
    assert "nothing was changed" in result.stderr
    assert git(behind, "rev-parse", "HEAD").strip() == head
    assert (behind / "secret.env").read_text(encoding="utf-8") == "local secret\n"


@pytest.mark.parametrize(
    ("added", "local_kind"),
    [
        ("build", "ignored directory with files"),
        ("cache/x", "ignored file"),
        ("lnk/f", "ignored symlink"),
    ],
)
def test_ignored_content_that_could_not_be_put_back_stops_the_run(
    behind: Path, tmp_path: Path, added: str, local_kind: str
) -> None:
    # git removes ignored content without asking when origin/main needs its
    # place for a file or a directory, and it could not be restored there.
    push_upstream(behind, {added: "upstream\n"})
    name = added.split("/")[0]
    with (behind / ".git" / "info" / "exclude").open("a", encoding="utf-8") as exclude:
        exclude.write(f"{name}\n")
    outside = tmp_path / "outside"
    outside.mkdir()
    if local_kind == "ignored directory with files":
        (behind / name).mkdir()
        (behind / name / "out.bin").write_text("precious\n", encoding="utf-8")
        kept = behind / name / "out.bin"
    elif local_kind == "ignored file":
        (behind / name).write_text("precious\n", encoding="utf-8")
        kept = behind / name
    else:
        (outside / "f").write_text("precious\n", encoding="utf-8")
        (behind / name).symlink_to(outside)
        kept = outside / "f"
    head = git(behind, "rev-parse", "HEAD").strip()

    result = run_script("--repo", str(behind), "--ref", "origin/main")
    assert result.returncode == 1, (result.stdout, result.stderr)
    assert "nothing was changed" in result.stderr
    assert f"  {name}" in result.stderr
    assert git(behind, "rev-parse", "HEAD").strip() == head
    assert kept.read_text(encoding="utf-8") == "precious\n"
    if local_kind == "ignored symlink":
        assert (behind / name).is_symlink()


def test_tracked_paths_that_change_between_file_and_directory_still_fast_forward(behind: Path) -> None:
    upstream = behind.parent / "upstream"
    # HEAD: "swap/a" (directory) and "flip" (file); origin/main turns them around.
    for tree in (behind, upstream):
        git(tree, "pull", "-q", "--ff-only")
    (behind / "swap").mkdir()
    (behind / "swap" / "a").write_text("a\n", encoding="utf-8")
    (behind / "flip").write_text("flip\n", encoding="utf-8")
    git(behind, "add", "-A")
    git(behind, "commit", "-qm", "dir and file")
    git(behind, "push", "-q", "origin", "HEAD:main")
    git(upstream, "pull", "-q", "--ff-only")
    git(upstream, "rm", "-q", "-r", "swap", "flip")
    (upstream / "swap").write_text("now a file\n", encoding="utf-8")
    (upstream / "flip").mkdir()
    (upstream / "flip" / "inner").write_text("now a dir\n", encoding="utf-8")
    git(upstream, "add", "-A")
    git(upstream, "commit", "-qm", "swap")
    git(upstream, "push", "-q", "origin", "HEAD:main")
    git(behind, "fetch", "-q", "origin")

    result = run_script("--repo", str(behind), "--ref", "origin/main")
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert (behind / "swap").read_text(encoding="utf-8") == "now a file\n"
    assert (behind / "flip" / "inner").read_text(encoding="utf-8") == "now a dir\n"


def available_locale(*names: str) -> str | None:
    listed = subprocess.run(["locale", "-a"], capture_output=True, text=True).stdout.split()
    normalized = {name.lower().replace("-", "") for name in listed}
    for name in names:
        if name.lower().replace("-", "") in normalized:
            return name
    return None


def test_candidates_do_not_depend_on_the_callers_locale(behind: Path, tmp_path: Path) -> None:
    # "B" sorts before "a" in C but after it in en_US; every step that
    # compares sorted lists must use the same collation. GNU sort and comm
    # honor the locale (CI runs them); where they are installed under other
    # names, as in the devcontainer, put them first on PATH.
    locale_name = available_locale("en_US.UTF-8", "en_US.utf8")
    if locale_name is None:
        pytest.skip("en_US.UTF-8 locale is not installed")
    push_upstream(behind, {"B.env": "upstream\n", "a.env": "upstream\n"})
    with (behind / ".git" / "info" / "exclude").open("a", encoding="utf-8") as exclude:
        exclude.write("*.env\n")
    # Only "a.env" exists locally, so the two sorted lists differ.
    (behind / "a.env").write_text("local a\n", encoding="utf-8")
    gnu_bin = tmp_path / "gnu-bin"
    gnu_bin.mkdir()
    for tool in ("comm", "sort"):
        gnu = shutil.which(f"gnu{tool}")
        if gnu:
            (gnu_bin / tool).symlink_to(gnu)
    env = {**os.environ, "LC_ALL": locale_name, "PATH": f"{gnu_bin}:{os.environ['PATH']}"}

    result = run_script("--repo", str(behind), "--ref", "origin/main", env=env)
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert (behind / "a.env").read_text(encoding="utf-8") == "local a\n"
    assert (behind / "B.env").read_text(encoding="utf-8") == "upstream\n"


def test_untracked_nested_repository_that_files_are_added_into_stops_the_run(behind: Path) -> None:
    # origin/main ignores vendor/ but force-adds vendor/lib/x.c. Locally
    # vendor/lib is an untracked repository of its own, which git ls-files
    # does not look into, and git would overwrite x.c inside it.
    upstream = behind.parent / "upstream"
    (upstream / ".gitignore").write_text("vendor/\n", encoding="utf-8")
    push_upstream(behind, {"vendor/lib/x.c": "upstream\n"})
    nested = behind / "vendor" / "lib"
    nested.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(nested)], check=True)
    (nested / "x.c").write_text("local work\n", encoding="utf-8")
    head = git(behind, "rev-parse", "HEAD").strip()

    result = run_script("--repo", str(behind), "--ref", "origin/main")
    assert result.returncode == 1, (result.stdout, result.stderr)
    assert "  vendor/lib/" in result.stderr
    assert git(behind, "rev-parse", "HEAD").strip() == head
    assert (nested / "x.c").read_text(encoding="utf-8") == "local work\n"


def test_added_submodule_over_an_existing_clone_still_fast_forwards(behind: Path, tmp_path: Path) -> None:
    library = tmp_path / "library"
    subprocess.run(["git", "init", "-q", str(library)], check=True)
    configure(library)
    (library / "lib.txt").write_text("lib\n", encoding="utf-8")
    git(library, "add", "lib.txt")
    git(library, "commit", "-qm", "lib")
    upstream = behind.parent / "upstream"
    subprocess.run(
        ["git", "-C", str(upstream), "-c", "protocol.file.allow=always", "submodule", "add", "-q", str(library), "sub"],
        check=True,
        capture_output=True,
    )
    git(upstream, "commit", "-qm", "add submodule")
    git(upstream, "push", "-q", "origin", "HEAD:main")
    git(behind, "fetch", "-q", "origin")
    subprocess.run(["git", "clone", "-q", str(library), str(behind / "sub")], check=True, capture_output=True)
    (behind / "sub" / "untracked.txt").write_text("local\n", encoding="utf-8")

    result = run_script("--repo", str(behind), "--ref", "origin/main")
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert (behind / "sub" / "untracked.txt").read_text(encoding="utf-8") == "local\n"


def test_tracked_symlink_replaced_by_a_directory_still_fast_forwards(behind: Path) -> None:
    upstream = behind.parent / "upstream"
    for tree in (behind, upstream):
        git(tree, "pull", "-q", "--ff-only")
    (behind / "d" / "a").mkdir(parents=True)
    (behind / "d" / "a" / "b").write_text("b\n", encoding="utf-8")
    (behind / "l").symlink_to("d")
    git(behind, "add", "-A")
    git(behind, "commit", "-qm", "symlink to a directory")
    git(behind, "push", "-q", "origin", "HEAD:main")
    git(upstream, "pull", "-q", "--ff-only")
    git(upstream, "rm", "-q", "l")
    (upstream / "l" / "a" / "b").mkdir(parents=True)
    (upstream / "l" / "a" / "b" / "c").write_text("c\n", encoding="utf-8")
    git(upstream, "add", "-A")
    git(upstream, "commit", "-qm", "directory instead of the symlink")
    git(upstream, "push", "-q", "origin", "HEAD:main")
    git(behind, "fetch", "-q", "origin")

    result = run_script("--repo", str(behind), "--ref", "origin/main")
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert (behind / "l" / "a" / "b" / "c").read_text(encoding="utf-8") == "c\n"
    assert not (behind / "l").is_symlink()


def test_ignored_file_where_a_tracked_directory_was_stops_the_run(behind: Path) -> None:
    # HEAD tracks a/x and ignores "a"; origin/main adds a/b. Locally the
    # directory "a" was replaced by an ignored file, which git would remove
    # although the index still has a/x (git ls-files -- a matches a/x).
    upstream = behind.parent / "upstream"
    for tree in (behind, upstream):
        git(tree, "pull", "-q", "--ff-only")
    (behind / "a").mkdir()
    (behind / "a" / "x").write_text("x\n", encoding="utf-8")
    (behind / ".gitignore").write_text("a\n", encoding="utf-8")
    git(behind, "add", "-f", "a/x", ".gitignore")
    git(behind, "commit", "-qm", "tracked a/x")
    git(behind, "push", "-q", "origin", "HEAD:main")
    git(upstream, "pull", "-q", "--ff-only")
    push_upstream(behind, {"a/b": "upstream\n"})
    (behind / "a" / "x").unlink()
    (behind / "a").rmdir()
    (behind / "a").write_text("precious\n", encoding="utf-8")
    head = git(behind, "rev-parse", "HEAD").strip()

    result = run_script("--repo", str(behind), "--ref", "origin/main")
    assert result.returncode == 1, (result.stdout, result.stderr)
    assert "\n  a\n" in result.stderr
    assert git(behind, "rev-parse", "HEAD").strip() == head
    assert (behind / "a").read_text(encoding="utf-8") == "precious\n"


@pytest.mark.parametrize("ignore_setting", [None, "diff.ignoreSubmodules"])
def test_untracked_file_where_a_submodule_is_added_stops_the_run(
    behind: Path, tmp_path: Path, ignore_setting: str | None
) -> None:
    # diff.ignoreSubmodules=all and submodule.<name>.ignore=all hide added
    # submodules from a plain diff; the script must still see them.
    library = tmp_path / "library"
    subprocess.run(["git", "init", "-q", str(library)], check=True)
    configure(library)
    (library / "lib.txt").write_text("lib\n", encoding="utf-8")
    git(library, "add", "lib.txt")
    git(library, "commit", "-qm", "lib")
    upstream = behind.parent / "upstream"
    subprocess.run(
        ["git", "-C", str(upstream), "-c", "protocol.file.allow=always", "submodule", "add", "-q", str(library), "sub"],
        check=True,
        capture_output=True,
    )
    git(upstream, "commit", "-qm", "add submodule")
    git(upstream, "push", "-q", "origin", "HEAD:main")
    git(behind, "fetch", "-q", "origin")
    (behind / "sub").write_text("local\n", encoding="utf-8")
    if ignore_setting:
        git(behind, "config", ignore_setting, "all")
    head = git(behind, "rev-parse", "HEAD").strip()

    result = run_script("--repo", str(behind), "--ref", "origin/main")
    assert result.returncode == 1, (result.stdout, result.stderr)
    assert "nothing was changed" in result.stderr
    assert git(behind, "rev-parse", "HEAD").strip() == head
    assert (behind / "sub").read_text(encoding="utf-8") == "local\n"


def test_unborn_branch_is_refused_with_a_clear_message(tmp_path: Path, behind: Path) -> None:
    fresh = tmp_path / "fresh"
    subprocess.run(["git", "init", "-q", str(fresh)], check=True)
    git(fresh, "remote", "add", "origin", str(behind.parent / "remote.git"))
    git(fresh, "fetch", "-q", "origin")
    (fresh / "same.md").write_text("mine\n", encoding="utf-8")

    result = run_script("--repo", str(fresh), "--ref", "origin/main")
    assert result.returncode == 1, (result.stdout, result.stderr)
    assert "HEAD has no commit yet" in result.stderr
    assert (fresh / "same.md").read_text(encoding="utf-8") == "mine\n"


def test_submodule_hidden_by_its_ignore_setting_is_still_seen(behind: Path, tmp_path: Path) -> None:
    # HEAD already maps "sub" in .gitmodules with ignore = all; origin/main
    # then adds the gitlink. Without --ignore-submodules=none even git
    # diff-tree leaves it out, and git would remove the ignored file "sub".
    upstream = behind.parent / "upstream"
    for tree in (behind, upstream):
        git(tree, "pull", "-q", "--ff-only")
    (behind / ".gitmodules").write_text(
        '[submodule "sub"]\n\tpath = sub\n\turl = ../library\n\tignore = all\n', encoding="utf-8"
    )
    (behind / ".gitignore").write_text("sub\n", encoding="utf-8")
    git(behind, "add", ".gitmodules", ".gitignore")
    git(behind, "commit", "-qm", "map sub")
    git(behind, "push", "-q", "origin", "HEAD:main")
    git(upstream, "pull", "-q", "--ff-only")
    gitlink = git(upstream, "rev-parse", "HEAD").strip()
    git(upstream, "update-index", "--add", "--cacheinfo", f"160000,{gitlink},sub")
    git(upstream, "commit", "-qm", "add the gitlink")
    git(upstream, "push", "-q", "origin", "HEAD:main")
    git(behind, "fetch", "-q", "origin")
    (behind / "sub").write_text("precious\n", encoding="utf-8")
    head = git(behind, "rev-parse", "HEAD").strip()

    result = run_script("--repo", str(behind), "--ref", "origin/main")
    assert result.returncode == 1, (result.stdout, result.stderr)
    assert "\n  sub\n" in result.stderr
    assert git(behind, "rev-parse", "HEAD").strip() == head
    assert (behind / "sub").read_text(encoding="utf-8") == "precious\n"


def test_ignored_file_in_a_submodule_turned_into_a_directory_stops_the_run(
    behind: Path, tmp_path: Path
) -> None:
    # origin/main replaces the submodule vendor/lib with plain files. git
    # leaves the submodule checkout in place and writes into it, so an
    # ignored local file on an added path would be overwritten.
    library = tmp_path / "library"
    subprocess.run(["git", "init", "-q", str(library)], check=True)
    configure(library)
    (library / "code.txt").write_text("lib\n", encoding="utf-8")
    git(library, "add", "code.txt")
    git(library, "commit", "-qm", "lib")
    upstream = behind.parent / "upstream"
    for tree in (behind, upstream):
        git(tree, "pull", "-q", "--ff-only")
    (behind / ".gitignore").write_text("*.log\n", encoding="utf-8")
    git(behind, "add", ".gitignore")
    subprocess.run(
        ["git", "-C", str(behind), "-c", "protocol.file.allow=always", "submodule", "add", "-q", str(library), "vendor/lib"],
        check=True,
        capture_output=True,
    )
    git(behind, "commit", "-qm", "submodule")
    git(behind, "push", "-q", "origin", "HEAD:main")
    git(upstream, "pull", "-q", "--ff-only")
    git(upstream, "rm", "-q", "--cached", "vendor/lib")
    git(upstream, "rm", "-q", ".gitmodules")
    (upstream / "vendor" / "lib").mkdir(parents=True, exist_ok=True)
    push_upstream(behind, {"vendor/lib/code.txt": "upstream\n", "vendor/lib/run.log": "upstream\n"})
    (behind / "vendor" / "lib" / "run.log").write_text("precious local log\n", encoding="utf-8")
    head = git(behind, "rev-parse", "HEAD").strip()

    result = run_script("--repo", str(behind), "--ref", "origin/main")
    assert result.returncode == 1, (result.stdout, result.stderr)
    assert "  vendor/lib/run.log" in result.stderr
    assert git(behind, "rev-parse", "HEAD").strip() == head
    assert (behind / "vendor" / "lib" / "run.log").read_text(encoding="utf-8") == "precious local log\n"


def add_gitlink(work: Path, library: Path, path: str) -> None:
    """Check out ``library`` at ``path`` and record it as a gitlink.

    git submodule add cannot take a path starting with "-", so the gitlink
    is written to the index directly; the script only looks at the index.
    """
    subprocess.run(["git", "clone", "-q", str(library), str(work / path)], check=True, capture_output=True)
    sha = git(library, "rev-parse", "HEAD").strip()
    git(work, "update-index", "--add", "--cacheinfo", f"160000,{sha},{path}")


def submodule_on_both_sides(behind: Path, tmp_path: Path, name: str = "sub") -> Path:
    """Commit a submodule ``name`` with a tracked file "t" and check it out in both clones."""
    library = tmp_path / "library"
    subprocess.run(["git", "init", "-q", str(library)], check=True)
    configure(library)
    (library / "t").write_text("t\n", encoding="utf-8")
    git(library, "add", "t")
    git(library, "commit", "-qm", "lib")
    upstream = behind.parent / "upstream"
    for tree in (behind, upstream):
        git(tree, "pull", "-q", "--ff-only")
    (behind / ".gitignore").write_text("*.log\n", encoding="utf-8")
    git(behind, "add", ".gitignore")
    add_gitlink(behind, library, name)
    git(behind, "commit", "-qm", "submodule")
    git(behind, "push", "-q", "origin", "HEAD:main")
    git(upstream, "pull", "-q", "--ff-only")
    git(upstream, "rm", "-q", "--cached", "--", name)
    return upstream


def test_ignored_file_on_the_way_inside_a_submodule_turned_into_a_directory_stops_the_run(
    behind: Path, tmp_path: Path
) -> None:
    # origin/main drops the submodule and adds sub/x.log/y; locally the
    # checkout has an ignored file sub/x.log, which git would remove.
    upstream = submodule_on_both_sides(behind, tmp_path)
    (upstream / "sub").mkdir(exist_ok=True)
    push_upstream(behind, {"sub/x.log/y": "upstream\n"})
    (behind / "sub" / "x.log").write_text("precious\n", encoding="utf-8")
    head = git(behind, "rev-parse", "HEAD").strip()

    result = run_script("--repo", str(behind), "--ref", "origin/main")
    assert result.returncode == 1, (result.stdout, result.stderr)
    assert "  sub/x.log" in result.stderr
    assert git(behind, "rev-parse", "HEAD").strip() == head
    assert (behind / "sub" / "x.log").read_text(encoding="utf-8") == "precious\n"


@pytest.mark.parametrize("name", ["sub", "-sub"])
def test_submodule_turned_into_a_file_stops_the_run_while_its_checkout_has_content(
    behind: Path, tmp_path: Path, name: str
) -> None:
    # git removes the whole checkout when a submodule becomes a file. A name
    # starting with "-" must not be taken for an option on the way.
    upstream = submodule_on_both_sides(behind, tmp_path, name)
    if (upstream / name).is_dir():
        (upstream / name).rmdir()
    push_upstream(behind, {name: "now a file\n"})
    (behind / name / "notes.txt").write_text("precious\n", encoding="utf-8")
    head = git(behind, "rev-parse", "HEAD").strip()

    result = run_script("--repo", str(behind), "--ref", "origin/main")
    assert result.returncode == 1, (result.stdout, result.stderr)
    assert f"  {name}/" in result.stderr
    assert git(behind, "rev-parse", "HEAD").strip() == head
    assert (behind / name / "notes.txt").read_text(encoding="utf-8") == "precious\n"


def test_submodule_turned_into_a_file_fast_forwards_when_its_checkout_is_empty(
    behind: Path, tmp_path: Path
) -> None:
    upstream = submodule_on_both_sides(behind, tmp_path)
    if (upstream / "sub").is_dir():
        (upstream / "sub").rmdir()
    push_upstream(behind, {"sub": "now a file\n"})
    # An uninitialized submodule leaves an empty directory.
    shutil.rmtree(behind / "sub")
    (behind / "sub").mkdir()

    result = run_script("--repo", str(behind), "--ref", "origin/main")
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert (behind / "sub").read_text(encoding="utf-8") == "now a file\n"


def submodule_under_a_directory_replaced_by_a_file(behind: Path, tmp_path: Path, parent: str = "a") -> None:
    """HEAD has the submodule <parent>/sub; origin/main removes it and adds the file <parent>."""
    library = tmp_path / "library"
    subprocess.run(["git", "init", "-q", str(library)], check=True)
    configure(library)
    (library / "t").write_text("t\n", encoding="utf-8")
    git(library, "add", "t")
    git(library, "commit", "-qm", "lib")
    upstream = behind.parent / "upstream"
    for tree in (behind, upstream):
        git(tree, "pull", "-q", "--ff-only")
    add_gitlink(behind, library, f"{parent}/sub")
    git(behind, "commit", "-qm", "submodule under a directory")
    git(behind, "push", "-q", "origin", "HEAD:main")
    git(upstream, "pull", "-q", "--ff-only")
    git(upstream, "rm", "-q", "--cached", "--", f"{parent}/sub")
    shutil.rmtree(upstream / parent)
    push_upstream(behind, {parent: "now a file\n"})


@pytest.mark.parametrize("parent", ["a", "-a"])
def test_submodule_inside_a_directory_replaced_by_a_file_stops_the_run(
    behind: Path, tmp_path: Path, parent: str
) -> None:
    submodule_under_a_directory_replaced_by_a_file(behind, tmp_path, parent)
    (behind / parent / "sub" / "untracked.txt").write_text("precious\n", encoding="utf-8")
    head = git(behind, "rev-parse", "HEAD").strip()

    result = run_script("--repo", str(behind), "--ref", "origin/main")
    assert result.returncode == 1, (result.stdout, result.stderr)
    assert f"  {parent}/sub/" in result.stderr
    assert git(behind, "rev-parse", "HEAD").strip() == head
    assert (behind / parent / "sub" / "untracked.txt").read_text(encoding="utf-8") == "precious\n"


def test_empty_submodule_inside_a_directory_replaced_by_a_file_fast_forwards(
    behind: Path, tmp_path: Path
) -> None:
    submodule_under_a_directory_replaced_by_a_file(behind, tmp_path)
    # An uninitialized submodule leaves an empty directory.
    shutil.rmtree(behind / "a" / "sub")
    (behind / "a" / "sub").mkdir()

    result = run_script("--repo", str(behind), "--ref", "origin/main")
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert (behind / "a").read_text(encoding="utf-8") == "now a file\n"
