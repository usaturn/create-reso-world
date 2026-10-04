"""Lifecycle, permission, history and end-to-end acceptance tests for PR #16.

Static checks keep the current instructions aligned with the approved root-cause
Spec (permissions, canonical document selection, approval versions, history
notices).  The end-to-end class runs the real context resolver and the real
non-replacing copy publication against temporary Git fixtures, then verifies
approval/current/authority/publication metadata and a blocked external route.

Imported historical documents are guarded byte-for-byte against commit 58c9ea8.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
CONTEXT = ROOT / "scripts/superpowers_context.py"
COPY_SH = ROOT / "scripts/superpowers-review-copy.sh"
AGENTS = ROOT / "AGENTS.md"
DOC_README = ROOT / "docs/superpowers/README.md"
REVIEW_FIX = ROOT / ".agents/skills/review-fix-planning/SKILL.md"
PR_REVIEW = ROOT / ".agents/skills/pr-review/SKILL.md"
HANDOFF = ROOT / ".agents/skills/agent-handoff/SKILL.md"
SCHEMA = ROOT / ".agents/skills/agent-handoff/references/handoff-schema.md"
WORKFLOW = ROOT / ".agents/skills/planning-parallel-issues/references/session-workflow.md"
LIFECYCLE_SPEC = ROOT / "docs/superpowers/specs/2026-10-03-superpowers-document-lifecycle-design.md"
LIFECYCLE_PLAN = ROOT / "docs/superpowers/plans/2026-10-03-superpowers-document-lifecycle.md"
ROUND1 = ROOT / "docs/superpowers/specs/2026-10-03-superpowers-document-lifecycle-review-fixes-design.md"
ROUND2 = ROOT / "docs/superpowers/specs/2026-10-03-pr16-superpowers-document-lifecycle-round2-review-fixes-design.md"
ROUND3 = ROOT / "docs/superpowers/specs/2026-10-04-pr16-superpowers-document-lifecycle-round3-review-fixes-design.md"
ROOT_CAUSE = "2026-10-04-create-reso-world-pr16-document-lifecycle-root-cause-review-fixes-design.md"
SELF = "usaturn/create-reso-world"
SPEC_V1_TEXT = "# sample design\n\n- 状態: draft\n"
ORIGIN = f"https://github.com/{SELF}.git"

IMPORT_COMMIT = "58c9ea8"
IMPORTED = [
    "docs/superpowers/plans/2026-09-30-list-shrink-recreate-round6-review-fixes.md",
    "docs/superpowers/plans/2026-10-02-pr9-list-shrink-round2-review-fixes.md",
    "docs/superpowers/plans/2026-10-03-pr9-list-shrink-round3-review-fixes.md",
    "docs/superpowers/specs/2026-09-29-asset-url-save-migration-review-fixes-design.md",
    "docs/superpowers/specs/2026-09-29-asset-url-save-migration-round2-review-fixes-design.md",
    "docs/superpowers/specs/2026-09-29-asset-url-save-migration-round3-review-fixes-design.md",
    "docs/superpowers/specs/2026-09-29-list-shrink-recreate-review-fixes-design.md",
    "docs/superpowers/specs/2026-09-29-list-shrink-recreate-round2-review-fixes-design.md",
    "docs/superpowers/specs/2026-09-29-list-shrink-recreate-round3-review-fixes-design.md",
    "docs/superpowers/specs/2026-09-29-slot-snapshot-dedup-review-fixes-design.md",
    "docs/superpowers/specs/2026-09-29-slot-snapshot-dedup-round2-review-fixes-design.md",
    "docs/superpowers/specs/2026-09-30-list-shrink-recreate-round4-review-fixes-design.md",
    "docs/superpowers/specs/2026-09-30-list-shrink-recreate-round5-review-fixes-design.md",
    "docs/superpowers/specs/2026-09-30-list-shrink-recreate-round6-review-fixes-design.md",
    "docs/superpowers/specs/2026-09-30-list-shrink-recreate-round7-review-fixes-design.md",
    "docs/superpowers/specs/2026-09-30-list-shrink-recreate-round8-review-fixes-design.md",
    "docs/superpowers/specs/2026-09-30-list-shrink-recreate-round9-review-fixes-design.md",
    "docs/superpowers/specs/2026-10-02-pi-gpt-6.1-sol-review-fixes-design.md",
    "docs/superpowers/specs/2026-10-02-pr8-round7-review-fixes-design.md",
    "docs/superpowers/specs/2026-10-02-pr9-list-shrink-review-fixes-design.md",
    "docs/superpowers/specs/2026-10-02-pr9-list-shrink-round2-review-fixes-design.md",
    "docs/superpowers/specs/2026-10-03-pr9-list-shrink-round3-review-fixes-design.md",
]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def section(content: str, heading: str) -> str:
    return content.split(heading, 1)[1].split("\n## ", 1)[0]


def boundary_row(content: str) -> str:
    for line in content.splitlines():
        if line.startswith("| それ以外 |"):
            return line
    return ""


class LifecycleInstructionTests(unittest.TestCase):
    """Normative instructions must match the approved root-cause Spec."""

    def test_current_callers_do_not_invoke_replacement(self):
        for path in (AGENTS, DOC_README, WORKFLOW):
            with self.subTest(path=path.name):
                self.assertNotIn("--replace-from", read(path),
                                 f"{path.name} still instructs the removed --replace-from")
        copy_section = section(read(REVIEW_FIX), "## Spec のコミットと確認用コピー")
        self.assertNotIn("--replace-from", copy_section)
        # A re-presentation publishes a new versioned copy instead of replacing.
        self.assertIn("差し替えない", copy_section)
        self.assertIn("-r2-", copy_section)

    def test_current_callers_state_that_old_copies_and_annotations_survive(self):
        readme = read(DOC_README)
        self.assertIn("unchanged", readme)
        self.assertIn("注記は残る", readme)
        skill_section = section(read(REVIEW_FIX), "## Spec のコミットと確認用コピー")
        self.assertIn("旧コピー", skill_section)
        self.assertIn("注記", skill_section)

    def test_readme_documents_the_shared_resolver_operation_differences(self):
        readme = read(DOC_README)
        self.assertIn("review-copy", readme)
        self.assertIn("コード側の cwd", readme)

    def test_agents_boundary_limits_external_routes_to_review_and_planning(self):
        row = boundary_row(read(AGENTS))
        self.assertTrue(row, "AGENTS.md boundary table lost the other-repository row")
        for needle in ("`CODE_ROOT`", "remote", "推測せず停止する", "`pr-review`", "`review-fix-planning`",
                       "ローカル専用", "外部コード実装は非対応", "blocked", "PR 連携は非対応"):
            self.assertIn(needle, row, f"the other-repository row lacks: {needle}")

    def test_operational_spec_carries_a_current_rule_pointer(self):
        spec = read(LIFECYCLE_SPEC)
        self.assertIn("履歴", spec)
        self.assertIn(ROOT_CAUSE, spec, "the operational spec must point at the current root-cause rules")
        self.assertIn("非置換", spec)
        # Historical content stays; the notice must not rewrite the original tables.
        self.assertIn("その他の任意のリポジトリ", spec)

    def test_skills_keep_external_implementation_blocked(self):
        skill = read(ROOT / ".agents/skills/planning-parallel-issues/SKILL.md")
        self.assertIn("remote-less", skill)
        self.assertIn("execution authority", skill)
        workflow = read(WORKFLOW)
        self.assertIn("blocked", workflow)
        self.assertIn("`sources.execution_authority`", workflow)
        self.assertIn("`sources.approved_commit`", workflow)
        self.assertIn("not ready", workflow)
        # Native and verified ResoLoop routes keep their permissions.
        pr_review = read(PR_REVIEW)
        self.assertIn("推測で埋めない", pr_review)
        self.assertIn("external/resoloop", pr_review)

    def test_handoff_schema_separates_approval_current_authority_and_publication(self):
        schema = read(SCHEMA)
        for field in ("approved_commit", "execution_authority", "completion_evidence", "document_published"):
            self.assertIn(f"`{field}`", schema, f"schema lacks `{field}`")
        self.assertIn("metadata-only", schema)
        self.assertIn("do not infer", schema.lower())
        self.assertIn("blocker", schema.lower())
        self.assertIn("never a restore source", schema)
        self.assertIn("current/restore", schema)

    def test_handoff_skill_transports_the_lifecycle_facts(self):
        skill = read(HANDOFF)
        for needle in ("`sources.approved_commit`", "`sources.execution_authority`", "`sources.completion_evidence`"):
            self.assertIn(needle, skill, f"agent-handoff SKILL lacks {needle}")

    def test_session_workflow_selects_the_canonical_document_first(self):
        workflow = read(WORKFLOW)
        self.assertIn("canonical", workflow)
        self.assertIn("canonical path", workflow)
        self.assertIn("stop and ask", workflow)
        self.assertIn("roundN", workflow)
        self.assertIn("committed", workflow, "the draft-committed-before-presentation invariant must stay")

    def test_lifecycle_plan_states_its_historical_operational_truthfully(self):
        plan = read(LIFECYCLE_PLAN)
        self.assertIn("履歴", plan)
        self.assertIn(ROOT_CAUSE, plan, "the historical plan must point at the current rules")
        self.assertIn("現在実行すべき手順ではない", plan)
        status = next(line for line in plan.splitlines() if line.startswith("- 状態:"))
        self.assertIn("completed", status, f"the historical plan status must say completed: {status}")
        self.assertIn("内容承認の記録は存在しない", status)

    def test_round_specs_carry_a_current_rule_pointer(self):
        for path in (ROUND1, ROUND2, ROUND3):
            with self.subTest(path=path.name):
                content = read(path)
                self.assertIn("履歴", content)
                self.assertIn(ROOT_CAUSE, content)
        # The historical instructions stay byte-visible as history: only
        # round2 and the historical Plan ever documented --replace-from.
        self.assertIn("--replace-from", read(ROUND2))
        self.assertIn("--replace-from", read(LIFECYCLE_PLAN))

    def test_imported_documents_are_unchanged_since_import(self):
        for rel in IMPORTED:
            committed = subprocess.run(["git", "-C", str(ROOT), "show", f"{IMPORT_COMMIT}:{rel}"],
                                       capture_output=True, check=True).stdout
            self.assertEqual(hashlib.sha256(committed).hexdigest(),
                             hashlib.sha256((ROOT / rel).read_bytes()).hexdigest(), rel)

    def test_the_unittest_suite_is_wired_into_the_existing_ci_runner(self):
        listing = subprocess.run(["bash", str(ROOT / ".devcontainer/run-tests.bash"), "--list"],
                                 capture_output=True, text=True, check=True).stdout
        self.assertIn("tests/scripts/test-superpowers-python.bash", listing)
        wrapper = read(ROOT / "tests/scripts/test-superpowers-python.bash")
        self.assertIn("test_superpowers_*.py", wrapper)


class EndToEndLifecycleTests(unittest.TestCase):
    """Real fixture run: context -> committed draft -> copy -> approval metadata
    -> versioned r2 copy -> simulated publication -> restore."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.env = dict(os.environ, GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL="/dev/null")
        self.parent = self.checkout("parent", {"origin": ORIGIN})
        self.helper = self.install_helper()
        self.doc = self.worktree("doc")
        self.external = self.checkout("elsewhere/code", {"origin": "https://github.com/other/repository.git"})
        self.review = self.parent / "tmp/superpowers-review"
        self.spec_rel = "docs/superpowers/specs/2026-10-04-e2e-sample-design.md"
        self.plan_rel = "docs/superpowers/plans/2026-10-04-e2e-sample-plan.md"

    # ------------------------------------------------------------------ fixture
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
        for remote, url in remotes.items():
            self.git(path, "remote", "add", remote, url)
        return path

    def install_helper(self):
        """The context helper must be committed in the helper-origin parent."""
        (self.parent / "scripts").mkdir()
        content = CONTEXT.read_bytes()
        (self.parent / "scripts/superpowers_context.py").write_bytes(content)
        self.git(self.parent, "add", "scripts/superpowers_context.py")
        self.git(self.parent, "commit", "-m", "install context helper")
        committed = subprocess.run(["git", "-C", str(self.parent), "show",
                                    "HEAD:scripts/superpowers_context.py"],
                                   capture_output=True, check=True).stdout
        self.assertEqual(committed, content, "the fixture helper must be the committed module")
        return self.parent / "scripts/superpowers_context.py"

    def worktree(self, name):
        path = self.root / name
        self.git(self.parent, "worktree", "add", "-b", "docs/lifecycle-e2e", str(path))
        (path / "docs/superpowers/specs").mkdir(parents=True)
        (path / "docs/superpowers/plans").mkdir(parents=True)
        return path

    def context(self, **kwargs):
        args = [sys.executable, str(self.helper), "--operation", "review-fix"]
        for name, value in kwargs.items():
            args.extend(["--" + name.replace("_", "-"), str(value)])
        return subprocess.run(args, cwd=self.parent, env=self.env, text=True, capture_output=True)

    def copy(self, name, *, commit=None, path=None, cwd=None):
        args = ["bash", str(COPY_SH), "--doc-root", str(self.doc), "--parent-root", str(self.parent),
                "--path", path or self.spec_rel, "--name", name]
        if commit:
            args += ["--commit", commit]
        return subprocess.run(args, cwd=cwd or self.root, env=self.env, text=True, capture_output=True)

    def commit_doc(self, spec_text, plan_text):
        (self.doc / self.spec_rel).write_text(spec_text, encoding="utf-8")
        (self.doc / self.plan_rel).write_text(plan_text, encoding="utf-8")
        self.git(self.doc, "add", self.spec_rel, self.plan_rel)
        self.git(self.doc, "commit", "-m", "draft")
        return self.git(self.doc, "rev-parse", "HEAD")

    def write_handoff(self, *, document_commit, approved_commit, execution_authority,
                      completion_evidence, blocked=False):
        base = self.parent / "tmp/docs_draft/claude_handoffs"
        base.mkdir(parents=True, exist_ok=True)
        stem = "e2e-blocked" if blocked else "e2e-supported"
        payload = {
            "schema_version": "2",
            "generated_at": "2026-10-04T00:00:00Z",
            "project_dir": str(self.doc),
            "session": {"id": "e2e", "stop_reason": "fixture breakpoint"},
            "decisions": [], "out_of_scope": [], "verification": {"commands": [], "isolation": "temp fixtures"},
            "landing": {"branch": "docs/lifecycle-e2e", "pr": None, "prohibited": []},
            "git": {"worktree": str(self.doc), "branch": "docs/lifecycle-e2e",
                    "head": self.git(self.doc, "rev-parse", "HEAD"), "status": "clean"},
            "sources": {
                "spec": "docs/superpowers/specs/2026-10-04-e2e-sample-design.md",
                "doc_root": str(self.doc),
                "document_commit": document_commit,
                "approved_commit": approved_commit,
                "execution_authority": execution_authority,
                "completion_evidence": completion_evidence,
                "document_published": None,
                "review_copy": "tmp/superpowers-review/e2e-sample-spec.md",
            },
        }
        json_path = base / f"{stem}.handoff.json"
        json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        md_path = base / f"{stem}.handoff.md"
        if blocked:
            md = ("## Status\n\nimplementation: **blocked / not ready** — 一般的な外部コード実装は非対応 "
                  "（root `AGENTS.md` のリポジトリ境界）。欠けているのは検証済みの実行経路と承認された実行許可である。\n"
                  f"document_commit: `{document_commit}` / approved_commit: null（内容承認の記録は存在しない）\n"
                  "review copy は閲覧補助であり、正本ではない。\n")
        else:
            md = ("## Sources\n\n"
                  f"document_commit: `{document_commit}` / approved_commit: `{approved_commit}`\n"
                  f"execution_authority: {execution_authority}\n"
                  f"completion_evidence: {completion_evidence}\n"
                  "公開未実施（ローカルのコミットのみ）\n")
        md_path.write_text(md, encoding="utf-8")
        return json_path, md_path

    # ------------------------------------------------------------------ the run
    def test_supported_route_reaches_simulated_publication_with_versioned_copies(self):
        # 1. Context resolution for the own repository and an explicit external CODE_ROOT.
        own = self.context(parent_root=str(self.parent), doc_root=str(self.doc), code_root=str(self.parent),
                           repo=SELF, doc_branch="docs/lifecycle-e2e")
        self.assertEqual(own.returncode, 0, own.stderr)
        own_value = json.loads(own.stdout)
        self.assertEqual((own_value["parent_root"], own_value["doc_root"], own_value["code_root"]),
                         (str(self.parent), str(self.doc), str(self.parent)))
        external = self.context(parent_root=str(self.parent), doc_root=str(self.doc),
                                code_root=str(self.external), repo="other/repository",
                                doc_branch="docs/lifecycle-e2e")
        self.assertEqual(external.returncode, 0, external.stderr)
        self.assertEqual(json.loads(external.stdout)["code_root"], str(self.external))

        # 2. Committed draft, then a review copy with exact bytes and full SHA.
        v1 = self.commit_doc("# sample design\n\n- 状態: draft\n", "# sample plan\n\n- 状態: draft\n")
        result = self.copy("e2e-sample-spec.md")
        self.assertEqual(result.returncode, 0, result.stderr)
        dest = self.review / "e2e-sample-spec.md"
        self.assertIn(f"source: {self.spec_rel} at {v1}", result.stdout)
        self.assertIn(f"sha256: {hashlib.sha256(SPEC_V1_TEXT.encode()).hexdigest()}",
                      result.stdout)
        self.assertEqual(dest.read_bytes(), (self.doc / self.spec_rel).read_bytes())
        self.assertEqual(self.git(self.parent, "status", "--porcelain"), "")

        # 3. Approval metadata is tied to the committed content version.
        json_path, md_path = self.write_handoff(document_commit=v1, approved_commit=v1,
                                                execution_authority="fixture: user asked to execute now",
                                                completion_evidence="fixture acceptance tests passed")
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        self.assertEqual(payload["sources"]["approved_commit"], v1)
        self.assertEqual(payload["sources"]["document_published"], None)
        self.assertIn("公開未実施", md_path.read_text(encoding="utf-8"))

        # 4. A versioned r2 copy never touches the annotated old copy.
        dest.write_text(dest.read_text(encoding="utf-8") + "user note\n", encoding="utf-8")
        v2 = self.commit_doc("# sample design r2\n\n- 状態: draft\n", "# sample plan\n\n- 状態: draft\n")
        self.assertEqual(v2, self.git(self.doc, "rev-parse", "HEAD"))
        result = self.copy("e2e-sample-spec.md")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("already exists with other content", result.stderr)
        self.assertIn("-r2-spec.md", result.stderr)
        self.assertEqual(dest.read_text(encoding="utf-8"), "# sample design\n\n- 状態: draft\nuser note\n")
        result = self.copy("e2e-sample-r2-spec.md")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f"source: {self.spec_rel} at {v2}", result.stdout)
        r2 = self.review / "e2e-sample-r2-spec.md"
        self.assertEqual(r2.read_bytes(), (self.doc / self.spec_rel).read_bytes())
        self.assertIn("user note\n", dest.read_text(encoding="utf-8"))

        # 5. Publication/restore metadata: simulated only, never a real push claim.
        simulated = {"publication": "simulated", "pushed": False,
                     "note": "シミュレーション: 実際の push は行っていない"}
        sim_path = self.parent / "tmp/docs_draft/publication-simulated.json"
        sim_path.write_text(json.dumps(simulated, ensure_ascii=False), encoding="utf-8")
        sim = json.loads(sim_path.read_text(encoding="utf-8"))
        self.assertEqual(sim["publication"], "simulated")
        self.assertFalse(sim["pushed"])
        self.assertNotIn("pushed: true", md_path.read_text(encoding="utf-8"))

        # 6. Restore the canonical bytes from the committed version, not from the copy.
        fresh = self.root / "restored"
        fresh.mkdir()
        blob = subprocess.run(["git", "-C", str(self.doc), "cat-file", "blob",
                               f"{v1}:{self.spec_rel}"], capture_output=True, check=True).stdout
        (fresh / "restored-spec.md").write_bytes(blob)
        self.assertEqual(hashlib.sha256((fresh / "restored-spec.md").read_bytes()).hexdigest(),
                         hashlib.sha256(blob).hexdigest())
        self.assertEqual(blob.decode(), SPEC_V1_TEXT)

    def test_unsupported_external_implementation_route_records_blocked_state(self):
        json_path, md_path = self.write_handoff(
            document_commit="0" * 40, approved_commit=None, execution_authority=None,
            completion_evidence=None, blocked=True)
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        self.assertIsNone(payload["sources"]["approved_commit"])
        self.assertIsNone(payload["sources"]["execution_authority"])
        md = md_path.read_text(encoding="utf-8")
        self.assertIn("blocked", md)
        self.assertIn("not ready", md)
        self.assertNotIn("ready", md.replace("not ready", "").replace("blocked / not ready", ""))
        self.assertIn("内容承認の記録は存在しない", md)
        self.assertNotIn("pushed: true", md)


if __name__ == "__main__":
    unittest.main()
