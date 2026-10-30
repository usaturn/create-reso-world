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


@dataclass
class Workflow:
    parent: Path
    target: Path
    remote: Path
    session: Path
    code: Path
    docs: Path
    repo: str

    def run(self, argument: str, *, required: str = "", before_pr: str = "") -> subprocess.CompletedProcess[str]:
        env = dict(os.environ, INPUT=argument, REQUIRED=required, TARGET_REPO=self.repo,
                   TARGET_ROOT=str(self.target), PARENT_ROOT=str(self.parent),
                   SKILL_DIR=str(SKILL), SESSION=str(self.session), CODE_ROOT=str(self.code),
                   DOC_ROOT=str(self.docs), CODE_BRANCH="feat/issue-42-change",
                   DOC_BRANCH="docs/issue-42-change", PR_TITLE="変更の実装",
                   CODE_PR_BODY=str(self.session / "body.md"),
                   DOC_PR_BODY=str(self.session / "body.md"))
        chunks = [procedure("input"),
                  'REQUIRED_BASES=(); if [ -n "$REQUIRED" ]; then REQUIRED_BASES+=("$REQUIRED"); fi',
                  procedure("capture"), procedure("worktree"),
                  'printf "new implementation\\n" > "$CODE_ROOT/change"',
                  'git -C "$CODE_ROOT" add change; git -C "$CODE_ROOT" commit -qm implementation',
                  'if [ "$DOC_ROOT" != "$CODE_ROOT" ]; then',
                  '  printf "draft design\\n" > "$DOC_ROOT/design.md"',
                  '  git -C "$DOC_ROOT" add design.md; git -C "$DOC_ROOT" commit -qm design',
                  'fi', procedure("diff"), procedure("publish"), before_pr,
                  # Resume in a fresh shell with values/functions, not shell options.
                  # The documented block must supply its own failure propagation.
                  'declare -p CODE_BASE_BRANCH CODE_BASE_SHA CODE_SHA > "$SESSION/resume.bash"',
                  'if [ "$TARGET_REPO" != usaturn/create-reso-world ]; then',
                  '  declare -p DOC_BASE_SHA DOC_SHA >> "$SESSION/resume.bash"',
                  'fi', 'declare -f recheck_bases >> "$SESSION/resume.bash"',
                  'bash -c ' + shlex.quote('source "$SESSION/resume.bash"\n' + procedure("pr"))]
        result = subprocess.run(["bash", "-c", "\n".join(chunks)], cwd=self.target,
                                env=env, text=True, capture_output=True)
        (self.session / "stdout.log").write_text(result.stdout)
        (self.session / "stderr.log").write_text(result.stderr)
        return result


@pytest.fixture
def workflow(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest) -> Workflow:
    external = getattr(request, "param", False)
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    for role in ("AUTHOR", "COMMITTER"):
        monkeypatch.setenv(f"GIT_{role}_NAME", "Workflow test")
        monkeypatch.setenv(f"GIT_{role}_EMAIL", "workflow@example.test")
    parent = tmp_path / "parent"
    session = tmp_path / "session"
    session.mkdir()
    (session / "body.md").write_text("複数行の本文\nRefs #42\n")
    pairs: list[tuple[Path, Path, Path, str]] = []
    repositories = [("docs", parent, "usaturn/create-reso-world")]
    if external:
        repositories.append(("code", parent / "external/resoloop", "usaturn/resoloop"))
    for name, checkout, repo in repositories:
        remote, seed = tmp_path / f"{name}.git", tmp_path / f"{name}-seed"
        subprocess.run(["git", "init", "--bare", "-q", "--initial-branch=main", str(remote)], check=True)
        subprocess.run(["git", "init", "-q", "--initial-branch=main", str(seed)], check=True)
        (seed / "content").write_text(f"{name} main\n")
        git(seed, "add", "content")
        git(seed, "commit", "-qm", "main")
        git(seed, "switch", "-qc", INTEGRATION)
        (seed / "integration-only").write_text("統合の履歴\nsecond line\n")
        git(seed, "add", "integration-only")
        git(seed, "commit", "-qm", "integration")
        git(seed, "remote", "add", "origin", str(remote))
        git(seed, "push", "-q", "origin", "--all")
        subprocess.run(["git", "clone", "-q", "--single-branch", "--branch", "main",
                        str(remote), str(checkout)], check=True)
        pairs.append((remote, seed, checkout, repo))
    # Deployed commands deliberately use the parent's scanner, not a script
    # from the feature branch. Supply the new scanner and its version source.
    (parent / "scripts").mkdir()
    (parent / ".devcontainer").mkdir()
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
        "args = sys.argv[1:]\n"
        "if 'push' in args and os.environ.get('SESSION'):\n"
        "    session = pathlib.Path(os.environ['SESSION'])\n"
        "    scans = (session / 'scans.jsonl').read_text().splitlines()\n"
        "    with (session / 'pushes.jsonl').open('a') as f:\n"
        "        f.write(json.dumps(dict(argv=args, scans=len(scans))) + '\\n')\n"
        "if args[:2] == ['remote', 'get-url']:\n"
        "    p = subprocess.run([real, *args], text=True, capture_output=True)\n"
        "    print(urls.get(p.stdout.strip(), p.stdout.strip()))\n"
        "    sys.exit(p.returncode)\n"
        "os.execv(real, [real, *args])\n"
    )
    gh = bin_dir / "gh"
    gh.write_text(
        f"#!{sys.executable}\nimport json, os, pathlib, sys\n"
        "args = sys.argv[1:]\nsession = pathlib.Path(os.environ['SESSION'])\n"
        "with (session / 'gh.jsonl').open('a') as f: f.write(json.dumps(args) + '\\n')\n"
        "repo = args[args.index('--repo') + 1]\n"
        "if args[:2] == ['issue', 'view']:\n"
        "    print(json.dumps(dict(number=42, title='実装', body='本文\\nsecond line', state='OPEN',\n"
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
    docs = parent / ".worktrees/issue-42-change" if external else code
    return Workflow(parent, target, remote, session, code, docs, repo)


@pytest.mark.parametrize("workflow,argument,base", [
    (False, "#42", "main"),
    (True, f"--base={INTEGRATION} #42 --merge", INTEGRATION),
], indirect=["workflow"])
def test_documented_flow_pins_worktree_diff_scan_and_pr(
    workflow: Workflow, argument: str, base: str,
) -> None:
    """Hardcoding main at any consumer silently drops integration work or scans the wrong history."""
    expected = git(workflow.remote, "rev-parse", f"refs/heads/{base}")
    result = workflow.run(argument, required=base if base != "main" else "")
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
