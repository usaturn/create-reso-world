"""S: run the documented shell, so dropped pins cannot silently publish to main.

Real Git owns objects, worktrees, diffs and pushes. Only GitHub URL discovery,
GitHub API writes and Gitleaks execution are local doubles; no models run.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import textwrap
from dataclasses import dataclass
from pathlib import Path

import pytest

SKILL = Path(__file__).resolve().parents[1]
ROOT = SKILL.parents[2]
INTEGRATION = "統合/プラグイン"


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def procedure(name: str) -> str:
    source = (SKILL / "SKILL.md").read_text()
    match = re.search(rf"<!-- base-workflow:{name} -->\s*```bash\n(.*?)\n[ \t]*```", source, re.S)
    assert match, f"missing executable base workflow: {name}"
    return textwrap.dedent(match[1])


def as_runtime(command: str, setup: str = "true") -> str:
    """Claude Code's Bash tool runs ``source <snapshot> && eval '<command>' < /dev/null && pwd -P …``.

    errexit is ignored inside that ``eval``, so a block stops only where it says so explicitly.
    """
    return f"{setup} && eval {shlex.quote(command)} < /dev/null && true"


def step(name: str) -> str:
    # The agent does not run the next block after one returns non-zero.
    return as_runtime(procedure(name)) + " || exit $?"


@dataclass
class Workflow:
    parent: Path
    target: Path
    remote: Path
    session: Path
    code: Path
    docs: Path
    repo: str

    def env(self, argument: str = "#42", required: str = "") -> dict[str, str]:
        return dict(os.environ, INPUT=argument, REQUIRED=required, TARGET_REPO=self.repo,
                    TARGET_ROOT=str(self.target), PARENT_ROOT=str(self.parent),
                    SKILL_DIR=str(self.parent / ".agents/skills/issue-to-pr"), SESSION=str(self.session), CODE_ROOT=str(self.code),
                    DOC_ROOT=str(self.docs), CODE_BRANCH="feat/issue-42-change",
                    DOC_BRANCH="docs/issue-42-change", PR_TITLE="変更の実装",
                    CODE_PR_BODY=str(self.session / "body.md"),
                    DOC_PR_BODY=str(self.session / "body.md"))

    def run(
        self, argument: str, *, required: str = "", before_target: str = "",
        before_publish: str = "", before_pr: str = "",
    ) -> subprocess.CompletedProcess[str]:
        env = self.env(argument, required)
        chunks = [step("input"),
                  # A probe between input and target must stop the flow on failure, like step().
                  *([before_target + " || exit $?"] if before_target else []),
                  step("target"),
                  # The requirement reaches capture only through SESSION, never a shell array.
                  'if [ -n "$REQUIRED" ]; then printf "%s\\n" "$REQUIRED"; fi > "$SESSION/required-bases.txt"',
                  step("capture"), step("worktree"),
                  'printf "new implementation\\n" > "$CODE_ROOT/change"',
                  'git -C "$CODE_ROOT" add change; git -C "$CODE_ROOT" commit -qm implementation',
                  'if [ "$DOC_ROOT" != "$CODE_ROOT" ]; then',
                  '  printf "draft design\\n" > "$DOC_ROOT/design.md"',
                  '  git -C "$DOC_ROOT" add design.md; git -C "$DOC_ROOT" commit -qm design',
                  'fi', step("diff"), before_publish, step("publish"), before_pr,
                  # Resume in a fresh shell with only the base values (saved as JSON
                  # by capture) and the function, not shell options. The documented
                  # block must supply its own failure propagation, and the scanned
                  # SHAs must come from the files the documented publish block writes.
                  'declare -p CODE_BASE_BRANCH CODE_BASE_SHA > "$SESSION/resume.bash"',
                  'if [ "$DOCS_SEPARATE" != false ]; then',
                  '  declare -p DOC_BASE_SHA >> "$SESSION/resume.bash"',
                  'fi', 'declare -f recheck_bases >> "$SESSION/resume.bash"',
                  'bash -c ' + shlex.quote(as_runtime(procedure("pr"), 'source "$SESSION/resume.bash"'))]
        result = subprocess.run(["bash", "-c", "\n".join(chunks)], cwd=self.target,
                                env=env, text=True, capture_output=True)
        (self.session / "stdout.log").write_text(result.stdout)
        (self.session / "stderr.log").write_text(result.stderr)
        return result


def run_shell(workflow: Workflow, commands: list[str]) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(["bash", "-c", "\n".join(commands)], cwd=workflow.target,
                            env=workflow.env(), text=True, capture_output=True)
    (workflow.session / "stdout.log").write_text(result.stdout)
    (workflow.session / "stderr.log").write_text(result.stderr)
    return result


def run_block(workflow: Workflow, name: str, setup: str = "true") -> subprocess.CompletedProcess[str]:
    return run_shell(workflow, [as_runtime(procedure(name), setup) + " || exit $?"])


@pytest.fixture
def workflow(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest) -> Workflow:
    external = getattr(request, "param", False)
    managed = external in ("managed", "managed-own-docs")
    # The tool's own committed AGENTS.md declares that it keeps its Spec/Plan.
    own_docs = external == "managed-own-docs"
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    for role in ("AUTHOR", "COMMITTER"):
        monkeypatch.setenv(f"GIT_{role}_NAME", "Workflow test")
        monkeypatch.setenv(f"GIT_{role}_EMAIL", "workflow@example.test")
    parent = tmp_path / "parent with spaces"
    session = tmp_path / "session"
    session.mkdir()
    (session / "body.md").write_text("複数行の本文\nRefs #42\n")
    pairs: list[tuple[Path, Path, Path, str]] = []
    repositories = [("docs", parent, "usaturn/create-reso-world")]
    if external:
        repositories.append(("code", parent / ("external/other-tool" if managed else "external/resoloop"),
                             "sample-owner/other-tool" if managed else "usaturn/resoloop"))
    for name, checkout, repo in repositories:
        remote, seed = tmp_path / f"{name}.git", tmp_path / f"{name}-seed"
        subprocess.run(["git", "init", "--bare", "-q", "--initial-branch=main", str(remote)], check=True)
        subprocess.run(["git", "init", "-q", "--initial-branch=main", str(seed)], check=True)
        (seed / "content").write_text(f"{name} main\n")
        git(seed, "add", "content")
        if own_docs and name == "code":
            (seed / "AGENTS.md").write_text(
                "# ツール\n\n<!-- superpowers-documents: this-repository -->\nSpec・Plan はここに置く。\n")
            git(seed, "add", "AGENTS.md")
        git(seed, "commit", "-qm", "main")
        git(seed, "switch", "-qc", INTEGRATION)
        (seed / "integration-only").write_text("統合の履歴\nsecond line\n")
        git(seed, "add", "integration-only")
        git(seed, "commit", "-qm", "integration")
        if managed and name == "code":
            git(seed, "branch", "development")
            git(seed, "branch", "release", "main")
        git(seed, "remote", "add", "origin", str(remote))
        git(seed, "push", "-q", "origin", "--all")
        subprocess.run(["git", "clone", "-q", "--single-branch", "--branch", "main",
                        str(remote), str(checkout)], check=True)
        # The documented shell drops GIT_* just like the resolver. Keep commit
        # identity in the fixture repository, not in the isolated environment.
        git(checkout, "config", "user.name", "Workflow test")
        git(checkout, "config", "user.email", "workflow@example.test")
        if repo == "usaturn/resoloop":
            git(checkout, "remote", "add", "upstream", "https://github.com/orange3134/resoloop.git")
        pairs.append((remote, seed, checkout, repo))
    # Use a deployed helper/package anchored to this fixture parent, never the real registry.
    deployed = parent / ".agents/skills/issue-to-pr"
    shutil.copytree(SKILL / "scripts", deployed / "scripts",
                    ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(ROOT / "tools/external_tools", parent / "tools/external_tools",
                    ignore=shutil.ignore_patterns("tests", "__pycache__"))
    if managed:
        from tools.external_tools.tests.conftest import ADOPTED, OTHER

        (parent / "external-tools.toml").write_bytes(ADOPTED + OTHER)
        git(parent, "add", "external-tools.toml")
        git(parent, "commit", "-qm", "adopt tools")
        git(parent, "push", "-q", "origin", "HEAD:refs/heads/main")
        git(parent, "update-ref", "refs/remotes/origin/main", "HEAD")
        git(parent, "checkout", "--detach", "-q")
    # Identity is real; only transport is redirected to the fixture bare repos.
    for _, _, checkout, repo in pairs:
        git(checkout, "remote", "set-url", "origin", f"https://github.com/{repo}.git")
    # Deployed commands deliberately use the parent's scanner, not a script
    # from the feature branch. Supply the new scanner and its version source.
    (parent / "scripts").mkdir()
    (parent / ".devcontainer").mkdir()
    shutil.copyfile(ROOT / "scripts/superpowers_context.py", parent / "scripts/superpowers_context.py")
    shutil.copyfile(ROOT / "scripts/scan-before-push.sh", parent / "scripts/scan-before-push.sh")
    shutil.copyfile(ROOT / ".devcontainer/install_gitleaks.bash", parent / ".devcontainer/install_gitleaks.bash")
    version = re.search(r'^readonly GITLEAKS_VERSION="([^"]+)"',
                        (parent / ".devcontainer/install_gitleaks.bash").read_text(), re.M)
    assert version
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    real_git = shutil.which("git")
    urls = {str(remote): f"https://github.com/{repo}.git" for remote, _, _, repo in pairs}
    wrapper = bin_dir / "git"
    wrapper.write_text(
        f"#!{sys.executable}\nimport json, os, pathlib, subprocess, sys\n"
        f"real = {real_git!r}\nurls = {urls!r}\n"
        f"transports = { {str(checkout): str(remote) for remote, _, checkout, _ in pairs}!r}\n"
        "args = sys.argv[1:]\n"
        "if 'push' in args and os.environ.get('SESSION'):\n"
        "    session = pathlib.Path(os.environ['SESSION'])\n"
        "    scans = (session / 'scans.jsonl').read_text().splitlines()\n"
        "    with (session / 'pushes.jsonl').open('a') as f:\n"
        "        f.write(json.dumps(dict(argv=args, scans=len(scans))) + '\\n')\n"
        "if 'get-url' in args and 'remote' in args:\n"
        "    p = subprocess.run([real, *args], text=True, capture_output=True)\n"
        "    print(urls.get(p.stdout.strip(), p.stdout.strip()))\n"
        "    sys.exit(p.returncode)\n"
        "transport = next((i for i, a in enumerate(args) if a in ('ls-remote', 'fetch', 'push')), None)\n"
        "if transport is not None:\n"
        "    common = subprocess.check_output([real, *args[:transport], 'rev-parse', '--path-format=absolute', '--git-common-dir'], text=True).strip()\n"
        "    remote = transports.get(str(pathlib.Path(common).parent))\n"
        "    if not remote: sys.exit('unmapped transport refused by fixture')\n"
        "    if 'origin' not in args: sys.exit('unexpected transport refused by fixture')\n"
        "    direction = ['--push'] if args[transport] == 'push' else []\n"
        "    destination = subprocess.check_output([real, *args[:transport], 'remote', 'get-url', *direction, 'origin'], text=True).strip()\n"
        "    if destination not in (remote, urls[remote]): sys.exit('unexpected effective destination refused by fixture')\n"
        "    args[args.index('origin')] = remote\n"
        "os.execv(real, [real, *args])\n"
    )
    gh = bin_dir / "gh"
    gh.write_text(
        f"#!{sys.executable}\nimport json, os, pathlib, sys\n"
        "args = sys.argv[1:]\nsession = pathlib.Path(os.environ['SESSION'])\n"
        "with (session / 'gh.jsonl').open('a') as f: f.write(json.dumps(args) + '\\n')\n"
        "repo = args[args.index('--repo') + 1]\n"
        "if args[:2] == ['issue', 'view']:\n"
        "    print(json.dumps(dict(number=42, title='実装', body='材質の変更\\n元値を保持する', state='OPEN',\n"
        "                          url=f'https://github.com/{repo}/issues/42')))\n"
        "elif args[:2] == ['pr', 'create']:\n"
        "    base = args[args.index('--base') + 1]\n"
        "    head = args[args.index('--head') + 1]\n"
        "    url = f'https://github.com/{repo}/pull/90'\n"
        "    import subprocess\n"
        "    root = os.environ['CODE_ROOT'] if repo == os.environ['TARGET_REPO'] else os.environ['DOC_ROOT']\n"
        "    sha = subprocess.check_output(['git', '-C', root, 'ls-remote', '--exit-code', '--refs',\n"
        "                                  'origin', f'refs/heads/{head}'], text=True).split()[0]\n"
        "    (session / (repo.split('/')[-1] + '-pr.json')).write_text(json.dumps(\n"
        "        dict(url=url, baseRefName=os.environ.get('RETARGET_PR', base), headRefOid=sha)))\n"
        "    print(url)\n"
        "elif args[:2] == ['pr', 'view']:\n"
        "    print((session / (repo.split('/')[-1] + '-pr.json')).read_text())\n"
        "else: sys.exit(64)\n"
    )
    leaks = bin_dir / "gitleaks"
    leaks.write_text(
        f"#!{sys.executable}\nimport json, os, pathlib, subprocess, sys\n"
        f"version = {version[1]!r}\n"
        "if sys.argv[1:] == ['version']: print(version); sys.exit(0)\n"
        "args = sys.argv[1:]\n"
        "options = next(a.split('=', 1)[1] for a in args if a.startswith('--log-opts='))\n"
        "span = options.split()[-1]\n"
        "commits = subprocess.check_output(['git', 'rev-list', span], text=True).splitlines()\n"
        "config = pathlib.Path(args[args.index('--config') + 1]).read_text()\n"
        "with (pathlib.Path(os.environ['SESSION']) / 'scans.jsonl').open('a') as f:\n"
        "    f.write(json.dumps(dict(cwd=os.getcwd(), span=span, commits=commits, config=config)) + '\\n')\n"
    )
    for executable in (wrapper, gh, leaks):
        executable.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    remote, seed, target, repo = pairs[-1]
    code = target / ".worktrees/issue-42-change"
    docs = parent / ".worktrees/issue-42-change" if external and not own_docs else code
    return Workflow(parent, target, remote, session, code, docs, repo)


@pytest.mark.parametrize("workflow,argument,base", [
    (False, "#42", "main"),
    (True, f"--base={INTEGRATION} #42 --merge", INTEGRATION),
    (False, "#42 --merge", "main"),
], indirect=["workflow"])
def test_documented_flow_pins_worktree_diff_scan_and_pr(
    workflow: Workflow, argument: str, base: str,
) -> None:
    """Hardcoding main at any consumer silently drops integration work or scans the wrong history."""
    expected = git(workflow.remote, "rev-parse", f"refs/heads/{base}")
    result = workflow.run(
        argument, required=base if base != "main" else "",
        # The input block must record the disabled merge before target runs.
        before_target='test -f "$SESSION/merge-disabled.txt"' if base != "main" and "--merge" in argument else "",
    )
    assert result.returncode == 0, result.stderr
    assert git(workflow.code, "rev-parse", "HEAD^") == expected
    assert (workflow.code / "integration-only").exists() == (base != "main")
    diff = (workflow.session / "code.diff").read_text()
    assert "+new implementation" in diff and "integration-only" not in diff
    captured = json.loads((workflow.session / "code-base.json").read_text())
    assert captured == {"repo": workflow.repo, "remote": "origin", "branch": base,
                        "ref": f"refs/heads/{base}", "sha": expected}
    scans = [json.loads(line) for line in (workflow.session / "scans.jsonl").read_text().splitlines()]
    code_sha = git(workflow.code, "rev-parse", "HEAD")
    code_scan = next(scan for scan in scans if scan["cwd"] == str(workflow.code))
    assert code_scan["span"] == f"{expected}..{code_sha}"
    assert code_scan["commits"] == [code_sha]
    assert git(workflow.remote, "rev-parse", "refs/heads/feat/issue-42-change") == code_sha
    calls = [json.loads(line) for line in (workflow.session / "gh.jsonl").read_text().splitlines()]
    creates = [call for call in calls if call[:2] == ["pr", "create"]]
    code_create = creates[0]
    assert code_create[code_create.index("--repo") + 1] == workflow.repo
    assert code_create[code_create.index("--base") + 1] == base
    assert code_create[code_create.index("--head") + 1] == "feat/issue-42-change"
    merge = json.loads((workflow.session / "issue.json").read_text())["merge"]
    assert merge == ({"loop_args": []} if "--merge" in argument else None)
    merge_disabled = workflow.session / "merge-disabled.txt"
    if "--merge" in argument and base != "main":
        # An integration base would otherwise let the loop merge and close the Issue.
        assert merge_disabled.exists()
        reason = merge_disabled.read_text()
        assert base in reason
        assert "ループ" in reason and "finalize.py" in reason and "マージ" in reason and "close" in reason
    else:
        # main + --merge (and runs without --merge) must keep the loop enabled.
        assert not merge_disabled.exists()
    pushes = [json.loads(line) for line in (workflow.session / "pushes.jsonl").read_text().splitlines()]
    # A document scan must finish before either repository is published.
    assert all(push["scans"] == len(scans) for push in pushes)
    if workflow.docs != workflow.code:
        doc_sha = git(workflow.parent, "rev-parse", "origin/main")
        assert git(workflow.docs, "rev-parse", "HEAD^") == doc_sha
        assert not (workflow.docs / "integration-only").exists()
        doc_scan = next(scan for scan in scans if scan["cwd"] == str(workflow.docs))
        assert doc_scan["span"] == f"{doc_sha}..{git(workflow.docs, 'rev-parse', 'HEAD')}"
        assert creates[1][creates[1].index("--base") + 1] == "main"
        assert creates[1][creates[1].index("--repo") + 1] == "usaturn/create-reso-world"
        assert "integration-only" not in (workflow.session / "docs.diff").read_text()


def test_required_handoff_is_not_lost_before_worktree_creation(workflow: Workflow) -> None:
    """Omitting required-base forwarding would publish to main despite the parent's integration direction."""
    result = workflow.run("#42 --base main", required=INTEGRATION)
    assert result.returncode != 0
    assert not workflow.code.exists()
    assert not (workflow.session / "scans.jsonl").exists()
    assert git(workflow.remote, "branch", "--list", "feat/issue-42-change") == ""


def test_resumed_shell_stops_before_pr_creation_when_base_moved(workflow: Workflow) -> None:
    """Losing fail-fast on shell restart must not create a PR after a stale-base check fails."""
    moved = git(workflow.remote, "rev-parse", f"refs/heads/{INTEGRATION}")
    result = workflow.run("#42", before_pr=f'git -C "{workflow.remote}" update-ref refs/heads/main {moved}')
    assert result.returncode != 0
    assert git(workflow.remote, "rev-parse", "refs/heads/feat/issue-42-change") == git(workflow.code, "rev-parse", "HEAD")
    calls = [json.loads(line) for line in (workflow.session / "gh.jsonl").read_text().splitlines()]
    assert not any(call[:2] == ["pr", "create"] for call in calls)
    assert workflow.code.exists()  # Published resources are retained, not reset/deleted.


def test_created_pr_retarget_is_not_reported_as_matching(workflow: Workflow, monkeypatch: pytest.MonkeyPatch) -> None:
    """Trusting pr create without reading the actual base can start a merge loop for the wrong target."""
    monkeypatch.setenv("RETARGET_PR", INTEGRATION)
    result = workflow.run("#42")
    assert result.returncode != 0
    assert (workflow.session / "code-pr-url.txt").read_text().strip().endswith("/pull/90")
    actual = json.loads((workflow.session / "code-pr.json").read_text())
    assert actual["baseRefName"] == INTEGRATION
    assert workflow.code.exists()
    assert git(workflow.remote, "rev-parse", "refs/heads/feat/issue-42-change") == git(workflow.code, "rev-parse", "HEAD")


@pytest.mark.parametrize("workflow", [True], indirect=True)
def test_publish_cannot_inherit_a_different_push_target(workflow: Workflow, tmp_path: Path) -> None:
    """Dropping publish-time Git isolation leaks scanned commits to an unverified pushurl."""
    unintended = tmp_path / "unintended.git"
    subprocess.run(["git", "init", "--bare", "-q", "--initial-branch=main", str(unintended)], check=True)
    # A resumed publishing shell can inherit overrides after the base was pinned.
    injected = ("export GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=remote.origin.pushurl "
                f"GIT_CONFIG_VALUE_0={shlex.quote(str(unintended))}")
    result = workflow.run(f"#42 --base={INTEGRATION}", before_publish=injected)
    assert git(unintended, "for-each-ref", "--format=%(refname)") == "", result.stderr
    assert result.returncode == 0, result.stderr
    code_sha = git(workflow.code, "rev-parse", "HEAD")
    doc_sha = git(workflow.docs, "rev-parse", "HEAD")
    assert git(workflow.remote, "rev-parse", "refs/heads/feat/issue-42-change") == code_sha
    assert git(workflow.parent, "ls-remote", "origin", "refs/heads/docs/issue-42-change").split()[0] == doc_sha
    assert json.loads((workflow.session / "code-pr.json").read_text())["headRefOid"] == code_sha
    assert json.loads((workflow.session / "docs-pr.json").read_text())["headRefOid"] == doc_sha


@pytest.mark.parametrize("workflow", ["managed"], indirect=True)
@pytest.mark.parametrize("base_explicit", [False, True])
def test_registered_tool_flows_to_issue_and_base(workflow: Workflow, base_explicit: bool) -> None:
    """S: registration-only routing must not silently publish another repo or hardcoded main."""
    argument = "#42 --base release" if base_explicit else "#42"
    expected_branch = "release" if base_explicit else "development"
    expected_sha = git(workflow.remote, "rev-parse", f"refs/heads/{expected_branch}")
    result = workflow.run(argument)
    assert result.returncode == 0, result.stderr
    issue = json.loads((workflow.session / "issue.json").read_text())
    assert issue["repo"] == "sample-owner/other-tool"
    assert issue["body"] == "材質の変更\n元値を保持する"
    assert issue["base"] == expected_branch
    captured_base = json.loads((workflow.session / "code-base.json").read_text())
    assert captured_base["repo"] == "sample-owner/other-tool"
    assert captured_base["branch"] == expected_branch
    assert captured_base["sha"] == expected_sha
    assert git(workflow.code, "rev-parse", "HEAD^") == expected_sha
    calls = [json.loads(line) for line in (workflow.session / "gh.jsonl").read_text().splitlines()]
    creates = [call for call in calls if call[:2] == ["pr", "create"]]
    assert [(call[call.index("--repo") + 1], call[call.index("--base") + 1]) for call in creates] == [
        ("sample-owner/other-tool", expected_branch), ("usaturn/create-reso-world", "main")]


@pytest.mark.parametrize("workflow", ["managed-own-docs"], indirect=True)
def test_declared_tool_keeps_documents_in_its_own_pr(workflow: Workflow) -> None:
    """S: separating documents would silently ship a declared repository's Spec/Plan in a create-reso-world PR."""
    # An Issue body may spell the target with capitals; GitHub, the resolver and gh accept it.
    workflow.repo = "Sample-Owner/Other-Tool"
    result = workflow.run("#42")
    assert result.returncode == 0, result.stderr
    target = json.loads((workflow.session / "target.json").read_text())
    assert target["document_repository"] == "sample-owner/other-tool"
    calls = [json.loads(line) for line in (workflow.session / "gh.jsonl").read_text().splitlines()]
    creates = [call for call in calls if call[:2] == ["pr", "create"]]
    assert [call[call.index("--repo") + 1] for call in creates] == ["Sample-Owner/Other-Tool"]
    assert not (workflow.parent / ".worktrees/issue-42-change").exists()
    scans = [json.loads(line) for line in (workflow.session / "scans.jsonl").read_text().splitlines()]
    assert [scan["cwd"] for scan in scans] == [str(workflow.code)]
    assert not (workflow.session / "docs-pr.json").exists()


def test_unpushed_base_advance_requires_reverify_and_pr_record(
    workflow: Workflow, tmp_path: Path,
) -> None:
    """S: a moved remote base must force a recorded rebase and reverify before publishing."""
    result = run_shell(workflow, [
        step("input"), step("target"),
        ': > "$SESSION/required-bases.txt"',
        step("capture"), step("worktree"),
        'printf "new implementation\\n" > "$CODE_ROOT/change"',
        'git -C "$CODE_ROOT" add change && git -C "$CODE_ROOT" commit -qm implementation',
    ])
    assert result.returncode == 0, result.stderr
    base_v1 = json.loads((workflow.session / "code-base.json").read_text())["sha"]
    assert (workflow.session / "code-base.initial.json").exists()
    assert (workflow.session / "base-env.bash").exists()

    # The fixture's git wrapper refuses arbitrary transports. Advance the real
    # bare remote from an unrelated seed with the system git.
    real_git = shutil.which("git", path=os.defpath)
    assert real_git
    seed = tmp_path / "advance-seed"
    subprocess.run([real_git, "clone", "-q", str(workflow.remote), str(seed)], check=True)
    subprocess.run([real_git, "-C", str(seed), "config", "user.name", "Base advance"], check=True)
    subprocess.run([real_git, "-C", str(seed), "config", "user.email", "base@example.test"], check=True)

    def advance_remote(name: str) -> str:
        (seed / name).write_text(f"{name}\n", encoding="utf-8")
        subprocess.run([real_git, "-C", str(seed), "add", name], check=True)
        subprocess.run([real_git, "-C", str(seed), "commit", "-qm", name], check=True)
        sha = subprocess.check_output([real_git, "-C", str(seed), "rev-parse", "HEAD"], text=True).strip()
        subprocess.run([real_git, "-C", str(seed), "push", "-q", "origin", "HEAD:refs/heads/main"], check=True)
        return sha

    base_v2 = advance_remote("unrelated-1.txt")
    publish = run_block(workflow, "publish", setup='source "$SESSION/base-env.bash"')
    assert publish.returncode == 2, publish.stderr
    assert git(workflow.remote, "branch", "--list", "feat/issue-42-change") == ""

    # Hand-editing the captured state must not turn the gate into a way around the advance record.
    state_path = workflow.session / "code-base.json"
    captured_state = state_path.read_bytes()
    tampered = json.loads(captured_state)
    tampered["sha"] = base_v2
    state_path.write_text(json.dumps(tampered, ensure_ascii=False), encoding="utf-8")
    tampered_publish = run_block(workflow, "publish", setup='source "$SESSION/base-env.bash"')
    assert tampered_publish.returncode == 2, tampered_publish.stderr
    assert git(workflow.remote, "branch", "--list", "feat/issue-42-change") == ""
    state_path.write_bytes(captured_state)

    (workflow.session / "owned-paths.json").write_text(json.dumps(
        {"code": ["change", "docs/superpowers/specs", "docs/superpowers/plans"]},
        ensure_ascii=False), encoding="utf-8")
    (workflow.session / "advance-premise.txt").write_text(
        "preflight・checkout_policy・外部仕様・共有インターフェース・AGENTS.md の前提は変わらない\n"
        "複数行の前提確認\n", encoding="utf-8")

    inspect = run_block(workflow, "inspect-advance")
    assert inspect.returncode == 0, inspect.stderr
    advance = run_block(workflow, "advance")
    assert advance.returncode == 0, advance.stderr
    assert json.loads((workflow.session / "code-base.json").read_text())["sha"] == base_v2
    records = [json.loads(line) for line in
               (workflow.session / "base-advances.jsonl").read_text().splitlines()]
    assert [(record["old_sha"], record["new_sha"]) for record in records] == [(base_v1, base_v2)]
    recheck = run_shell(workflow, ['source "$SESSION/base-env.bash" && recheck_bases'])
    assert recheck.returncode == 0, recheck.stderr

    # A second movement while the run continues must use the same loop and refresh base-env.bash.
    base_v3 = advance_remote("unrelated-2.txt")
    inspect = run_block(workflow, "inspect-advance")
    assert inspect.returncode == 0, inspect.stderr
    advance = run_block(workflow, "advance")
    assert advance.returncode == 0, advance.stderr
    assert json.loads((workflow.session / "code-base.json").read_text())["sha"] == base_v3
    records = [json.loads(line) for line in
               (workflow.session / "base-advances.jsonl").read_text().splitlines()]
    assert [(record["old_sha"], record["new_sha"]) for record in records] == [
        (base_v1, base_v2), (base_v2, base_v3)]
    assert base_v3 in (workflow.session / "base-env.bash").read_text()
    recheck = run_shell(workflow, ['source "$SESSION/base-env.bash" && recheck_bases'])
    assert recheck.returncode == 0, recheck.stderr

    publish = run_block(workflow, "publish", setup='source "$SESSION/base-env.bash"')
    assert publish.returncode == 2, publish.stderr
    assert git(workflow.remote, "branch", "--list", "feat/issue-42-change") == ""

    commands = [
        {"cwd": "code", "argv": ["git", "status", "--porcelain"]},
        {"cwd": "parent", "argv": ["printf", "%s", "検証 完了"]},
        {"cwd": "code", "argv": ["test", "-d", str(workflow.parent)]},
    ]
    (workflow.session / "verify-cmds.json").write_text(
        json.dumps(commands, ensure_ascii=False), encoding="utf-8")
    reverify = run_block(workflow, "reverify")
    assert reverify.returncode == 0, reverify.stderr
    assert (workflow.session / "reverified.json").exists()
    assert (workflow.session / "checks.json").exists()

    diff = run_block(workflow, "diff", setup='source "$SESSION/base-env.bash"')
    assert diff.returncode == 0, diff.stderr
    publish = run_block(workflow, "publish", setup='source "$SESSION/base-env.bash"')
    assert publish.returncode == 0, publish.stderr
    pushed = git(workflow.remote, "rev-parse", "refs/heads/feat/issue-42-change")
    assert git(workflow.remote, "rev-parse", "refs/heads/feat/issue-42-change^") == base_v3

    body = workflow.session / "body.md"
    body.write_text("複数行の本文\nRefs #42\n", encoding="utf-8")
    pr = run_block(workflow, "pr", setup='source "$SESSION/base-env.bash"')
    assert pr.returncode == 2, pr.stderr
    calls = [json.loads(line) for line in (workflow.session / "gh.jsonl").read_text().splitlines()]
    assert not any(call[:2] == ["pr", "create"] for call in calls)

    lines = ["複数行の本文", "Refs #42", "", "base 前進の記録:"]
    lines.extend(f"- {record['old_sha']} -> {record['new_sha']}" for record in records)
    lines.extend(["", "必須検証コマンド:"])
    lines.extend("- " + " ".join(command["argv"]) for command in commands)
    body.write_text("\n".join(lines) + "\n", encoding="utf-8")
    pr = run_block(workflow, "pr", setup='source "$SESSION/base-env.bash"')
    assert pr.returncode == 0, pr.stderr
    assert git(workflow.remote, "rev-parse", "refs/heads/feat/issue-42-change") == pushed
    created = json.loads((workflow.session / "code-pr.json").read_text())
    assert created == {"url": "https://github.com/usaturn/create-reso-world/pull/90",
                       "baseRefName": "main", "headRefOid": pushed}
