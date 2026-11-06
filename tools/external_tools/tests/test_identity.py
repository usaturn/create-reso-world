"""S: identity checks must not silently choose another repository or operation root."""
from __future__ import annotations

from pathlib import Path

import pytest

from .conftest import ADOPTED, UNADOPTED, git
from tools.external_tools.models import ExternalToolsError


def snapshot(workspace):
    """Include refs, index, configuration and user-owned file bytes, without Git writes."""
    roots = (workspace.parent, workspace.registered, workspace.linked, workspace.other_clone)
    return {
        str(root): (
            tuple(git(root, *args) for args in (
                ("rev-parse", "HEAD"), ("show-ref",), ("status", "--porcelain=v1", "--untracked-files=all"),
                ("worktree", "list", "--porcelain"),
            )),
            {str(path.relative_to(root)): path.read_bytes() for path in root.rglob("*")
             if path.is_file() and ".git" not in path.relative_to(root).parts},
            tuple(path.read_bytes() if path.exists() else None for path in (
                Path(git(root, "rev-parse", "--path-format=absolute", "--git-path", name))
                for name in ("index", "config", "config.worktree")
            )),
        ) for root in roots
    }


def test_managed_target_uses_registered_common_dir(workspace):
    # Replacing common-dir membership with origin equality admits another clone.
    from tools.external_tools.identity import resolve_managed_target

    (workspace.linked / "local.txt").write_text("材質の変更\n元値を保持する", encoding="utf-8")
    (workspace.linked / "staged.txt").write_text("keep staged\n", encoding="utf-8")
    git(workspace.linked, "add", "staged.txt")
    before = snapshot(workspace)
    resolved = resolve_managed_target(workspace.registry, workspace.repository, operation="review-workspace")
    repair = resolve_managed_target(workspace.registry, workspace.repository, operation="review-fix", code_root=workspace.linked)
    assert resolved.checkout == workspace.registered
    assert resolved.common_dir == workspace.registered / ".git"
    assert repair.checkout == workspace.linked
    assert repair.common_dir == resolved.common_dir
    assert repair.base_remote == "origin"
    assert repair.registry_commit == workspace.adopted_sha
    with pytest.raises(ExternalToolsError):
        resolve_managed_target(workspace.registry, workspace.repository, operation="review-fix", code_root=workspace.other_clone)
    assert snapshot(workspace) == before


def test_linked_checkout_requires_its_registered_root(workspace, tmp_path: Path):
    # S: accepting a copied .git file lets an unrelated directory borrow the real
    # linked worktree's index/HEAD. Common-dir and branch equality cannot catch it.
    from tools.external_tools.identity import resolve_managed_target

    decoy = tmp_path / "unrelated directory"
    decoy.mkdir()
    (decoy / ".git").write_bytes((workspace.linked / ".git").read_bytes())
    (decoy / "user.txt").write_text("keep unrelated data\n", encoding="utf-8")
    (workspace.linked / "staged.txt").write_text("材質の変更\n元値を保持する", encoding="utf-8")
    git(workspace.linked, "add", "staged.txt")
    before = snapshot(workspace)
    decoy_before = {path.name: path.read_bytes() for path in decoy.iterdir()}

    genuine = resolve_managed_target(
        workspace.registry, workspace.repository, operation="review-fix", code_root=workspace.linked)
    assert genuine.checkout == workspace.linked
    with pytest.raises(ExternalToolsError):
        resolve_managed_target(
            workspace.registry, workspace.repository, operation="review-fix", code_root=decoy)

    assert snapshot(workspace) == before
    assert {path.name: path.read_bytes() for path in decoy.iterdir()} == decoy_before


def test_git_environment_cannot_redirect_identity(workspace, monkeypatch):
    # Removing isolated Git reads silently returns the foreign repo's common dir.
    from tools.external_tools.identity import resolve_managed_target

    registry = workspace.registry
    monkeypatch.setenv("GIT_DIR", str(workspace.other_clone / ".git"))
    monkeypatch.setenv("GIT_WORK_TREE", str(workspace.other_clone))
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "remote.origin.url")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", "https://github.com/wrong/repository.git")
    result = resolve_managed_target(registry, workspace.repository, operation="review-workspace")
    assert result.checkout == workspace.registered
    assert result.common_dir == workspace.registered / ".git"


def test_managed_operations_do_not_fall_back_to_permanent_or_detached_checkout(workspace):
    # Conflating operation profiles would permit edits/cleanup on the wrong workspace.
    from tools.external_tools.identity import resolve_managed_target

    resolve = lambda operation, root: resolve_managed_target(
        workspace.registry, workspace.repository, operation=operation, code_root=root)
    assert resolve("cleanup", None).checkout == workspace.registered
    assert resolve("implement", workspace.linked).checkout == workspace.linked
    for operation, root in (("review-fix", None), ("implement", workspace.registered),
                            ("cleanup", workspace.linked), ("review-workspace", workspace.linked)):
        with pytest.raises(ExternalToolsError):
            resolve(operation, root)
    git(workspace.linked, "checkout", "--detach")
    assert resolve("base-read", workspace.linked).checkout == workspace.linked
    assert resolve("base-read", workspace.registered).checkout == workspace.registered
    with pytest.raises(ExternalToolsError):
        resolve("review-fix", workspace.linked)


@pytest.mark.parametrize("gate", ["origin", "ambiguous", "fetch-rewrite", "push-destination", "credentials"])
def test_managed_transport_rejects_wrong_or_ambiguous_destination(workspace, gate):
    # Trusting origin text/first URL alone can send credentials or changes elsewhere.
    from tools.external_tools.identity import resolve_managed_target, validate_transport_destination

    target = resolve_managed_target(workspace.registry, workspace.repository, operation="review-fix", code_root=workspace.linked)
    validate_transport_destination(target, direction="fetch")
    validate_transport_destination(target, direction="push")
    git(workspace.registered, "config", "extensions.worktreeConfig", "true")
    root = workspace.linked
    secret = "fixture-" + "private-value"
    if gate == "origin":
        git(root, "config", "--worktree", "remote.origin.url", "https://github.com/wrong/repository.git")
    elif gate == "ambiguous":
        git(root, "config", "--worktree", "remote.mirror.url", "https://example.invalid/foreign.git")
        git(root, "config", "--worktree", "--add", "remote.mirror.url", f"https://github.com/{workspace.repository}.git")
    elif gate == "fetch-rewrite":
        git(root, "config", "--worktree", "url.https://github.com/wrong/.insteadOf", "https://github.com/usaturn/")
    else:
        git(root, "config", "--worktree", "--add", "remote.origin.pushurl", f"https://github.com/{workspace.repository}.git")
        wrong = f"https://{secret}@github.com/{workspace.repository}.git" if gate == "credentials" else "https://github.com/wrong/repository.git"
        git(root, "config", "--worktree", "--add", "remote.origin.pushurl", wrong)
    before = snapshot(workspace)
    with pytest.raises(ExternalToolsError) as caught:
        validate_transport_destination(target, direction="push" if gate in {"push-destination", "credentials"} else "fetch")
    assert secret not in str(caught.value) + caught.value.reason_code
    assert snapshot(workspace) == before


def test_candidate_registry_cannot_authorize_a_target(workspace):
    # Passing a parsed candidate to identity must not promote it into operational data.
    from tools.external_tools.identity import resolve_managed_target
    from tools.external_tools.registry import parse_registry

    candidate = parse_registry(ADOPTED + UNADOPTED, parent_root=workspace.parent, commit=workspace.adopted_sha)
    with pytest.raises(ExternalToolsError):
        resolve_managed_target(candidate, workspace.repository, operation="review-workspace")
    assert resolve_managed_target(workspace.registry, workspace.repository, operation="review-workspace").checkout == workspace.registered
