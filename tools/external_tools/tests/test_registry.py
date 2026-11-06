"""S guards against candidate promotion and silent repository/path substitution."""
from __future__ import annotations

from pathlib import Path

import pytest

from .conftest import ADOPTED, OTHER, UNADOPTED, git


def test_active_registry_ignores_unadopted_candidate(workspace):
    # Removing the HEAD-blob read would silently promote this dirty candidate.
    from tools.external_tools.registry import load_active_registry, parse_registry

    (workspace.parent / "external-tools.toml").write_bytes(ADOPTED + UNADOPTED)
    active = load_active_registry(workspace.parent)
    assert active is not None and active.commit == workspace.adopted_sha
    assert active.find_repository("sample-owner/unadopted") is None
    assert active.find_repository("USATURN/RESONITE-EMISSION-EDITOR").relative_path == "external/emission-editor"
    # Parsing a candidate is allowed for inspection, not adoption.
    candidate = parse_registry(
        (workspace.candidate / "external-tools.toml").read_bytes(),
        parent_root=workspace.parent, commit=git(workspace.candidate, "rev-parse", "HEAD"),
    )
    assert candidate.find_repository("sample-owner/unadopted") is not None


def test_registry_rejects_escaping_or_overlapping_target(workspace, tmp_path: Path):
    # Removing any placement guard would let later operations target someone else's data.
    from tools.external_tools.models import ExternalToolsError
    from tools.external_tools.registry import parse_registry

    outside = tmp_path / "outside"
    outside.mkdir()
    (workspace.parent / "external/escape").symlink_to(outside, target_is_directory=True)
    invalid = [
        ADOPTED.replace(b"external/emission-editor", b"../outside"),
        ADOPTED.replace(b"external/emission-editor", str(outside).encode()),
        ADOPTED.replace(b"external/emission-editor", b"external/escape/child"),
        ADOPTED.replace(b"external/emission-editor", b"external/one")
        + OTHER.replace(b"external/other-tool", b"external/one/child"),
        ADOPTED.replace(b"external/emission-editor", b"external/resoloop"),
        ADOPTED.replace(b"external/emission-editor", b"external/resoloop-meshy/child"),
        ADOPTED.replace(b"external/emission-editor", b"."),
        ADOPTED.replace(b"[tools.emission-editor]", b'[tools."../key"]'),
    ]
    for data in invalid:
        with pytest.raises(ExternalToolsError):
            parse_registry(data, parent_root=workspace.parent, commit=workspace.adopted_sha)
    two_valid_entries = ADOPTED + OTHER
    parsed = parse_registry(two_valid_entries, parent_root=workspace.parent, commit=workspace.adopted_sha)
    assert parsed.find_repository("sample-owner/other-tool").relative_path == "external/other-tool"
    assert parsed.find_repository("sample-owner/other-tool").base_branch == "development"
    assert parsed.find_repository("sample-owner/other-tool").ci == "required"


def test_registry_rejects_reserved_or_duplicate_repository(workspace):
    # Duplicate/reserved repos must not select a different checkout by iteration order.
    from tools.external_tools.models import ExternalToolsError
    from tools.external_tools.registry import parse_registry

    for repository in (
        b"usaturn/create-reso-world", b"usaturn/resoloop",
        b"orange3134/resoloop", b"usaturn/resoloop-meshy",
    ):
        with pytest.raises(ExternalToolsError):
            parse_registry(
                ADOPTED.replace(b"usaturn/resonite-emission-editor", repository),
                parent_root=workspace.parent, commit=workspace.adopted_sha,
            )
    with pytest.raises(ExternalToolsError):
        parse_registry(
            ADOPTED + OTHER.replace(b"sample-owner/other-tool", b"USATURN/RESONITE-EMISSION-EDITOR"),
            parent_root=workspace.parent, commit=workspace.adopted_sha,
        )
    parsed = parse_registry(
        ADOPTED.replace(b"usaturn/resonite-emission-editor", b"USATURN/RESONITE-EMISSION-EDITOR") + OTHER,
        parent_root=workspace.parent, commit=workspace.adopted_sha,
    )
    assert parsed.find_repository(workspace.repository).repository == workspace.repository


@pytest.mark.parametrize("gate", ["attached", "not-ancestor", "linked", "subdirectory"])
def test_loader_rejects_unadopted_or_wrong_parent(workspace, gate):
    # Each gate prevents a feature checkout/commit from masquerading as the adopted parent.
    from tools.external_tools.models import ExternalToolsError
    from tools.external_tools.registry import load_active_registry

    root = workspace.parent
    if gate == "attached":
        git(root, "checkout", "fixture-base")
    elif gate == "not-ancestor":
        git(root, "checkout", "--detach", "candidate")
    elif gate == "linked":
        root = workspace.candidate
        git(root, "checkout", "--detach", workspace.adopted_sha)
    else:
        root = workspace.parent / "external"
    with pytest.raises(ExternalToolsError):
        load_active_registry(root)


def test_no_registry_preserves_legacy_routes_but_still_validates_identity(workspace):
    # Managed-only branch/ancestor gates here would break old parent routes.
    from tools.external_tools.models import ExternalToolsError
    from tools.external_tools.registry import load_active_registry

    root = workspace.parent
    git(root, "checkout", "fixture-base")
    git(root, "rm", "external-tools.toml")
    git(root, "commit", "-m", "legacy parent without registry")
    assert load_active_registry(root) is None
    git(root, "remote", "set-url", "origin", "https://github.com/sample-owner/wrong-parent.git")
    with pytest.raises(ExternalToolsError):
        load_active_registry(root)


def test_broken_adopted_registry_is_not_treated_as_absent(workspace):
    # Treating a broken blob as None would reactivate permissive legacy routing.
    from tools.external_tools.models import ExternalToolsError
    from tools.external_tools.registry import load_active_registry

    root = workspace.parent
    (root / "external-tools.toml").write_bytes(b"invalid registry")
    git(root, "add", "external-tools.toml")
    git(root, "commit", "-m", "broken adopted registry")
    git(root, "update-ref", "refs/remotes/origin/main", "HEAD")
    with pytest.raises(ExternalToolsError):
        load_active_registry(root)


def test_loader_ignores_inherited_git_selectors(workspace, monkeypatch):
    # Without isolation the other clone would supply a plausible wrong registry.
    from tools.external_tools.registry import load_active_registry

    monkeypatch.setenv("GIT_DIR", str(workspace.other_clone / ".git"))
    monkeypatch.setenv("GIT_WORK_TREE", str(workspace.other_clone))
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "remote.origin.url")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", "https://github.com/sample-owner/redirect.git")
    active = load_active_registry(workspace.parent)
    assert active is not None and active.commit == workspace.adopted_sha
    assert active.find_repository(workspace.repository).relative_path == "external/emission-editor"


@pytest.mark.parametrize("gate", ["credentials", "multiple-urls", "rewritten-destination", "push-destination"])
def test_parent_origin_rejects_unsafe_or_ambiguous_destination(workspace, gate):
    # Trusting raw origin alone would ignore credentials or different effective destinations.
    from tools.external_tools.models import ExternalToolsError
    from tools.external_tools.registry import load_active_registry

    root = workspace.parent
    secret = "fixture-" + "credential"
    if gate == "credentials":
        git(root, "remote", "set-url", "origin", f"https://{secret}@github.com/usaturn/create-reso-world.git")
    elif gate == "multiple-urls":
        git(root, "config", "--add", "remote.origin.url", "https://github.com/sample-owner/other.git")
    elif gate == "rewritten-destination":
        git(root, "config", "url.https://github.com/sample-owner/.insteadOf", "https://github.com/usaturn/")
    else:
        git(root, "config", "remote.origin.pushurl", "https://github.com/sample-owner/other.git")
    with pytest.raises(ExternalToolsError) as caught:
        load_active_registry(root)
    assert secret not in str(caught.value)
    assert secret not in caught.value.reason_code


def test_registry_rejects_lexical_parent_overlap_through_symlink(workspace):
    # S: resolving the child elsewhere must not let a parent's removal erase another tool's path.
    from tools.external_tools.models import ExternalToolsError
    from tools.external_tools.registry import parse_registry

    external = workspace.parent / "external"
    (external / "a").mkdir()
    (external / "b").mkdir()
    (external / "a/child").symlink_to(external / "b", target_is_directory=True)
    data = ADOPTED.replace(b"external/emission-editor", b"external/a")
    overlapping = data + OTHER.replace(b"external/other-tool", b"external/a/child")
    with pytest.raises(ExternalToolsError):
        parse_registry(overlapping, parent_root=workspace.parent, commit=workspace.adopted_sha)
    independent = data + OTHER.replace(b"external/other-tool", b"external/b")
    parsed = parse_registry(independent, parent_root=workspace.parent, commit=workspace.adopted_sha)
    assert parsed.find_repository("sample-owner/other-tool").relative_path == "external/b"


def test_active_registry_ignores_replacement_blob(workspace):
    # S: local refs/replace must not promote candidate contents while reporting the adopted SHA.
    from tools.external_tools.registry import load_active_registry

    root = workspace.parent
    adopted_blob = git(root, "rev-parse", f"{workspace.adopted_sha}:external-tools.toml")
    candidate_blob = git(root, "rev-parse", "candidate:external-tools.toml")
    git(root, "replace", adopted_blob, candidate_blob)
    active = load_active_registry(root)
    assert active is not None and active.commit == workspace.adopted_sha
    assert active.find_repository("sample-owner/unadopted") is None
    assert active.find_repository(workspace.repository).relative_path == "external/emission-editor"


@pytest.mark.parametrize("target", [
    ".git/control", "external/tool/.worktrees/repair", "external/redirect/tool",
])
def test_registry_restricts_targets_to_external_checkouts(workspace, target):
    # S: lexical placement, resolved placement and worktree internals are separate unsafe boundaries.
    from tools.external_tools.models import ExternalToolsError
    from tools.external_tools.registry import parse_registry

    documents = workspace.parent / "documents"
    documents.mkdir()
    (workspace.parent / "external/redirect").symlink_to(documents, target_is_directory=True)
    data = ADOPTED.replace(b"external/emission-editor", target.encode())
    with pytest.raises(ExternalToolsError):
        parse_registry(data, parent_root=workspace.parent, commit=workspace.adopted_sha)
    parsed = parse_registry(ADOPTED + OTHER, parent_root=workspace.parent, commit=workspace.adopted_sha)
    assert parsed.find_repository("sample-owner/other-tool").relative_path == "external/other-tool"
