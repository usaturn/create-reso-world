"""Read-only preflight acceptance tests using real, isolated Git repositories.

These catch cwd identity bypasses, remote ambiguity, root/operation conflation,
and accepting a same-URL clone in place of a known repository's repair worktree.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
HELPER = ROOT / "scripts/superpowers_context.py"
SELF = "usaturn/create-reso-world"
ORIGIN = f"https://github.com/{SELF}.git"


class ContextTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.env = dict(os.environ, GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL="/dev/null")
        self.parent = self.checkout("parent", {"origin": ORIGIN})
        self.external = self.checkout("external code", {"origin": "https://github.com/other/repository.git"})
        self.fork = self.checkout("parent/external/resoloop", {
            "origin": "git@github.com:usaturn/resoloop.git",
            "upstream": "ssh://git@github.com/orange3134/resoloop.git",
        })

    def git(self, root, *args):
        return subprocess.run(["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", *args],
                              cwd=root, env=self.env, check=True, text=True, capture_output=True).stdout.strip()

    def checkout(self, name, remotes):
        path = self.root / name
        path.mkdir(parents=True)
        self.git(path, "init", "-b", "main")
        (path / ".gitignore").write_text("/external/\n/tmp/\n", encoding="utf-8")
        self.git(path, "add", ".gitignore")
        self.git(path, "commit", "-m", "initial")
        for name, url in remotes.items():
            self.git(path, "remote", "add", name, url)
        return path

    def linked(self, checkout, name, branch="repair"):
        path = self.root / name
        self.git(checkout, "worktree", "add", "-b", branch, str(path))
        return path

    def snapshot(self):
        return {str(p): tuple(self.git(p, *args) for args in (
            ("rev-parse", "HEAD"), ("status", "--porcelain=v1", "--untracked-files=all"),
            ("remote", "-v"), ("show-ref",), ("worktree", "list", "--porcelain"),
        )) for p in (self.parent, self.external, self.fork)}

    def run_context(self, operation="review-workspace", cwd=None, **kwargs):
        args = [sys.executable, str(HELPER), "--operation", operation]
        kwargs.setdefault("repo", SELF)
        for name, value in kwargs.items():
            if value is not None:
                args.extend(["--" + name.replace("_", "-"), str(value)])
        before = self.snapshot()
        result = subprocess.run(args, cwd=cwd or self.parent, env=self.env, text=True, capture_output=True)
        self.assertEqual(self.snapshot(), before, "context validation mutated Git state")
        return result

    def good(self, **kwargs):
        result = self.run_context(**kwargs)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        value = json.loads(result.stdout)
        self.assertEqual(set(value), {"parent_root", "tool_root", "doc_root", "code_root", "repository",
                                     "base_remote", "head_remote", "document_branch", "document_head",
                                     "code_branch", "code_head"})
        self.assertEqual(value["tool_root"], str(self.parent))
        return value

    def bad(self, needle, **kwargs):
        result = self.run_context(**kwargs)
        self.assertEqual(result.returncode, 66, result.stderr)
        self.assertIn(needle, result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertEqual(result.stdout, "")

    def test_external_cwd_cannot_become_implicit_parent(self):
        for code in (None, self.external, self.external / "subdir"):
            with self.subTest(code=code):
                self.bad("PARENT_ROOT", cwd=self.external, repo="other/repository", code_root=code)

    def test_explicit_parent_supports_external_cwd_but_code_stays_explicit(self):
        self.bad("CODE_ROOT", cwd=self.external, parent_root=self.parent, repo="other/repository")
        value = self.good(cwd=self.external, parent_root=self.parent, code_root=self.external, repo="other/repository")
        self.assertEqual((value["code_root"], value["base_remote"]), (str(self.external), "origin"))

    def test_empty_roots_are_omitted_not_external_defaults(self):
        self.bad("PARENT_ROOT", cwd=self.external, parent_root="", code_root="", repo="other/repository")
        value = self.good(parent_root="", doc_root="", code_root="")
        self.assertIsNone(value["doc_root"])
        self.assertIsNone(value["document_head"])
        self.assertIsNone(value["document_branch"])
        self.assertIsNone(value["head_remote"])

    def test_parent_main_can_be_inferred_from_its_subdirectory(self):
        sub = self.parent / "sub"
        sub.mkdir()
        self.assertEqual(self.good(cwd=sub)["parent_root"], str(self.parent))

    def test_missing_unsupported_or_foreign_parent_origin_has_actionable_error(self):
        for url in (None, "https://example.com/usaturn/create-reso-world.git", "not-a-url", "https://github.com/other/repository"):
            with self.subTest(url=url):
                if url is None:
                    self.git(self.parent, "remote", "remove", "origin")
                else:
                    self.git(self.parent, "remote", "add" if not self.git(self.parent, "remote") else "set-url", "origin", url)
                self.bad("PARENT_ROOT origin", repo="other/repository", code_root=self.external)

    def test_linked_parent_requires_explicit_main_parent(self):
        linked = self.linked(self.parent, "parent-wt")
        for repository in (SELF, "usaturn/resoloop", "orange3134/resoloop", "other/repository"):
            with self.subTest(repository=repository):
                self.bad("linked worktree", cwd=linked, repo=repository, code_root=self.external if repository == "other/repository" else None)
        self.assertEqual(self.good(cwd=linked, parent_root=self.parent)["code_root"], str(self.parent))
        self.bad("main checkout", parent_root=linked)

    def test_explicit_roots_must_be_absolute_checkout_roots(self):
        sub = self.external / "src"
        sub.mkdir()
        for code in ("external code", sub, self.external / ".git", self.root / "missing"):
            with self.subTest(code=code):
                self.bad("CODE_ROOT", repo="other/repository", code_root=code)
        self.bad("PARENT_ROOT", parent_root=self.parent / "external")

    def test_external_remote_selection_requires_exactly_one_name(self):
        self.git(self.external, "remote", "rename", "origin", "base")
        self.assertEqual(self.good(repo="other/repository", code_root=self.external)["base_remote"], "base")
        self.git(self.external, "remote", "add", "mirror", "git@github.com:other/repository.git")
        self.bad("has 2 remotes", repo="other/repository", code_root=self.external)
        self.git(self.external, "remote", "remove", "mirror")
        self.git(self.external, "remote", "set-url", "base", "ssh://git@example.com/other/repository.git")
        self.bad("has 0 remotes", repo="other/repository", code_root=self.external)
        self.git(self.external, "remote", "remove", "base")
        self.bad("has 0 remotes", repo="other/repository", code_root=self.external)

    def test_known_routes_select_base_and_reject_conflicting_explicit_root(self):
        for repo, code, remote in ((SELF, self.parent, "origin"), ("usaturn/resoloop", self.fork, "origin"),
                                   ("orange3134/resoloop", self.fork, "upstream")):
            with self.subTest(repo=repo):
                self.assertEqual(self.good(repo=repo, code_root=code)["base_remote"], remote)
                self.bad("CODE_ROOT", repo=repo, code_root=self.external)

    def test_fork_requires_both_expected_remotes(self):
        self.git(self.fork, "remote", "set-url", "upstream", ORIGIN)
        for repository in ("usaturn/resoloop", "orange3134/resoloop"):
            self.bad("scripts/resoloop-fork.sh clone", repo=repository)

    def test_workspace_rejects_linked_code_but_fix_accepts_verified_worktrees(self):
        for checkout, repo, name in ((self.parent, SELF, "self-wt"), (self.fork, "orange3134/resoloop", "fork-wt"),
                                     (self.external, "other/repository", "external-wt")):
            with self.subTest(repo=repo):
                linked = self.linked(checkout, name)
                self.bad("linked worktree", code_root=linked, repo=repo)
                value = self.good(operation="review-fix", code_root=linked, repo=repo)
                self.assertEqual(value["code_root"], str(linked))
                self.assertEqual(value["code_branch"], "repair")
                self.assertEqual(value["code_head"], self.git(linked, "rev-parse", "HEAD"))

    def test_fix_rejects_same_url_clone_and_its_linked_worktree_for_known_routes(self):
        for repo, remotes, name in ((SELF, {"origin": ORIGIN}, "self-clone"),
                                    ("orange3134/resoloop", {"origin": "https://github.com/usaturn/resoloop",
                                                          "upstream": "https://github.com/orange3134/resoloop"}, "fork-clone")):
            clone = self.checkout(name, remotes)
            linked = self.linked(clone, name + "-wt")
            for code in (clone, linked):
                self.bad("same Git repository", operation="review-fix", repo=repo, code_root=code)

    def test_document_main_and_linked_roots_verify_requested_branch(self):
        linked = self.linked(self.parent, "docs-wt", "docs/topic")
        for doc, branch in ((self.parent, "main"), (linked, "docs/topic")):
            value = self.good(operation="review-fix", doc_root=doc, doc_branch=branch)
            self.assertEqual((value["doc_root"], value["document_branch"], value["document_head"]),
                             (str(doc), branch, self.git(doc, "rev-parse", "HEAD")))
            self.bad("DOC_ROOT branch", operation="review-fix", doc_root=doc, doc_branch="wrong")
        self.bad("DOC_ROOT", doc_root=linked / "external")
        self.bad("DOC_ROOT origin", doc_root=self.external)
        self.bad("DOC_ROOT", operation="review-fix", doc_branch="docs/topic")

    def test_copy_only_validates_document_and_parent_not_code_cwd(self):
        linked = self.linked(self.parent, "docs-wt", "docs/topic")
        value = self.good(operation="review-copy", cwd=self.external, parent_root=self.parent, doc_root=linked)
        for key in ("code_root", "code_branch", "code_head", "base_remote", "head_remote"):
            self.assertIsNone(value[key])
        self.bad("PARENT_ROOT", operation="review-copy", cwd=self.external, doc_root=linked)
        self.bad("DOC_ROOT", operation="review-copy")

    def test_base_and_head_remote_are_independent_and_head_branch_must_match(self):
        self.git(self.external, "remote", "rename", "origin", "base")
        self.git(self.external, "remote", "add", "origin", "ssh://git@github.com/contributor/repository.git")
        value = self.good(operation="review-fix", repo="other/repository", code_root=self.external,
                          head_repo="contributor/repository", head_branch="main")
        self.assertEqual((value["base_remote"], value["head_remote"]), ("base", "origin"))
        self.bad("CODE_ROOT branch", operation="review-fix", repo="other/repository", code_root=self.external,
                 head_repo="contributor/repository", head_branch="wrong")
        self.bad("head remote", operation="review-fix", repo="other/repository", code_root=self.external,
                 head_repo="missing/repository", head_branch="main")
        self.git(self.external, "remote", "add", "mirror", "git@github.com:contributor/repository.git")
        self.bad("head remote", operation="review-fix", repo="other/repository", code_root=self.external,
                 head_repo="contributor/repository", head_branch="main")
        self.bad("head", operation="review-fix", head_branch="main")
        self.bad("head", operation="review-fix", head_repo=SELF)

    def test_head_remote_accepts_fetch_base_and_effective_push_head_split(self):
        # Using fetch identity for head selection rejects this legitimate split.
        self.git(self.external, "remote", "set-url", "--push", "origin",
                 "ssh://git@github.com/contributor/repository.git")
        value = self.good(operation="review-fix", repo="other/repository", code_root=self.external,
                          head_repo="contributor/repository", head_branch="main")
        self.assertEqual((value["base_remote"], value["head_remote"]), ("origin", "origin"))

    def test_head_remote_rejects_wrong_single_pushurl_despite_matching_fetch_url(self):
        self.git(self.external, "remote", "add", "head", "https://github.com/contributor/repository.git")
        self.git(self.external, "remote", "set-url", "--push", "head", "https://github.com/wrong/repository.git")
        self.bad("effective push URLs", operation="review-fix", repo="other/repository", code_root=self.external,
                 head_repo="contributor/repository", head_branch="main")

    def test_head_remote_rejects_matching_first_pushurl_with_wrong_later_destination(self):
        # Checking only the first effective push URL misses an additional push.
        self.git(self.external, "remote", "add", "head", "https://github.com/contributor/repository.git")
        self.git(self.external, "remote", "set-url", "--push", "head", "git@github.com:contributor/repository.git")
        for wrong in ("https://github.com/wrong/repository.git", "https://example.com/contributor/repository.git"):
            with self.subTest(wrong=wrong):
                self.git(self.external, "remote", "set-url", "--push", "--add", "head", wrong)
                self.bad("effective push URLs", operation="review-fix", repo="other/repository", code_root=self.external,
                         head_repo="contributor/repository", head_branch="main")
                self.git(self.external, "config", "--fixed-value", "--unset-all", "remote.head.pushurl", wrong)

    def test_head_remote_requires_one_effective_push_candidate_name(self):
        # Distinct fetch URLs must not hide two equally valid push remote names.
        self.git(self.external, "remote", "set-url", "--push", "origin", "https://github.com/contributor/repository.git")
        self.git(self.external, "remote", "add", "mirror", "https://github.com/elsewhere/repository.git")
        self.git(self.external, "remote", "set-url", "--push", "mirror", "git@github.com:contributor/repository.git")
        self.bad("has 2 remotes", operation="review-fix", repo="other/repository", code_root=self.external,
                 head_repo="contributor/repository", head_branch="main")

    def test_head_remote_preserves_no_pushurl_fallback(self):
        value = self.good(operation="review-fix", repo="other/repository", code_root=self.external,
                          head_repo="other/repository", head_branch="main")
        self.assertEqual((value["base_remote"], value["head_remote"]), ("origin", "origin"))

    def test_head_remote_accepts_multiple_push_urls_only_when_all_target_head(self):
        self.git(self.external, "remote", "set-url", "--push", "origin", "https://github.com/contributor/repository.git")
        self.git(self.external, "remote", "set-url", "--push", "--add", "origin", "ssh://git@github.com/contributor/repository")
        value = self.good(operation="review-fix", repo="other/repository", code_root=self.external,
                          head_repo="contributor/repository", head_branch="main")
        self.assertEqual((value["base_remote"], value["head_remote"]), ("origin", "origin"))

    def test_head_remote_rejects_mixed_fetch_url_fallback_destinations(self):
        # With no pushurl, Git can use more than the first configured fetch URL.
        self.git(self.external, "remote", "set-url", "--add", "origin", "https://github.com/wrong/repository.git")
        self.bad("effective push URLs", operation="review-fix", repo="other/repository", code_root=self.external,
                 head_repo="other/repository", head_branch="main")

    def test_head_remote_uses_effective_push_instead_of_rewrite(self):
        self.git(self.external, "config", "url.ssh://git@github.com/contributor/.pushInsteadOf", "https://github.com/other/")
        value = self.good(operation="review-fix", repo="other/repository", code_root=self.external,
                          head_repo="contributor/repository", head_branch="main")
        self.assertEqual((value["base_remote"], value["head_remote"]), ("origin", "origin"))

    def test_github_remote_formats_and_pr_url_normalize(self):
        for url in (ORIGIN, f"https://github.com/{SELF}/", f"https://github.com/{SELF}.git/",
                    f"git@github.com:{SELF}.git", f"ssh://git@github.com/{SELF}", f"ssh://git@github.com/{SELF}.git/"):
            with self.subTest(url=url):
                self.git(self.parent, "remote", "set-url", "origin", url)
                self.assertEqual(self.good(repo=f"https://github.com/{SELF}/pull/16")["repository"], SELF)

    def test_invalid_repository_inputs_fail_clearly(self):
        for repo in ("other", "other/repo/extra", "../repo", "other/re po", "https://example.com/other/repo/pull/1",
                     "https://github.com/other/repo/issues/1", "https://github.com/other/repo/pull/nope",
                     "https://github.com.evil/other/repo/pull/1"):
            with self.subTest(repo=repo):
                self.bad("repository", repo=repo)


if __name__ == "__main__":
    unittest.main()
