"""Lifecycle, permission, history and end-to-end acceptance tests for PR #16.

Static checks keep the current instructions aligned with the approved root-cause
Spec (permissions, canonical document selection, approval versions, history
notices).  The end-to-end class runs the real context resolver and the real
non-replacing copy publication against temporary Git fixtures, then verifies
approval/current/authority/publication metadata and a blocked external route.

Imported historical documents are guarded by fixed SHA-256 values captured
from commit 58c9ea8; running the check does not require that Git history.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
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

IMPORT_HASHES = ROOT / "tests/scripts/fixtures/superpowers-imported-documents.sha256.json"
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

    def test_agents_boundary_preserves_approved_external_pr_repairs(self):
        row = boundary_row(read(AGENTS))
        self.assertTrue(row, "AGENTS.md boundary table lost the other-repository row")
        for needle in ("`CODE_ROOT`", "remote", "推測せず停止する", "`pr-review`", "`review-fix-planning`",
                       "承認済み", "実装修正", "ローカル専用", "外部コード実装は非対応", "blocked", "PR 連携は非対応"):
            self.assertIn(needle, row, f"the other-repository row lacks: {needle}")

    def test_authority_exception_names_the_substantive_change_in_current_instructions(self):
        for path in (AGENTS, DOC_README, HANDOFF):
            with self.subTest(path=path.name):
                self.assertIn("記録した実行許可がその変更を明示的に含む場合を除く", read(path))
                self.assertIn("変更内容", read(path))
        self.assertIn("name the specific change", read(SCHEMA))

    def test_current_workflows_preserve_approved_external_pr_repairs(self):
        for path in (DOC_README, REVIEW_FIX, SCHEMA, WORKFLOW, LIFECYCLE_SPEC,
                     ROOT / ".agents/skills/planning-parallel-issues/SKILL.md"):
            with self.subTest(path=str(path.relative_to(ROOT))):
                self.assertIn("approved PR review-fix implementation", read(path))

    def test_reading_side_checks_versions_authority_and_closed_plans(self):
        reader = section(read(HANDOFF), "## handoff を読む")
        for token in ("sources.approved_commit", "sources.execution_authority", "schema v2", "不明",
                      "completed", "superseded", "cancelled", "通常の実装を再開しない",
                      "承認済み版", "現行・復元版", "内容変更"):
            self.assertIn(token, reader)

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

    def test_historical_headers_distinguish_execution_from_content_approval(self):
        for path in (LIFECYCLE_SPEC, ROUND1, LIFECYCLE_PLAN):
            with self.subTest(document=str(path.relative_to(ROOT))):
                opening = read(path).split("\n## ", 1)[0]
                status = next(line for line in opening.splitlines() if line.startswith("- 状態:"))
                self.assertNotIn("approved", status)
                self.assertTrue(any(value in status for value in ("completed", "superseded")), status)
                self.assertIn("- 実行許可:", opening)
                self.assertIn("- 内容承認:", opening)
                self.assertIn("個別のコミット済み版の内容承認は確認できない", opening)
                self.assertNotIn("Spec の内容承認と実行指示", opening)
                self.assertNotIn("実行指示は Spec 承認の指示に基づく", opening)
        self.assertIn("続けて実装してください。推奨案で進めて、途中で止めずにPRまで実施してください。",
                      read(LIFECYCLE_SPEC).split("\n## ", 1)[0])
        self.assertIn("対応が必要な指摘があったら、推奨案でプッシュまでしておいてください。",
                      read(ROUND1).split("\n## ", 1)[0])

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
        expected = json.loads(read(IMPORT_HASHES))
        self.assertEqual(set(expected), set(IMPORTED), "import baseline must cover exactly the historical document inventory")
        for rel in IMPORTED:
            with self.subTest(document=rel):
                self.assertEqual(expected[rel], hashlib.sha256((ROOT / rel).read_bytes()).hexdigest(), rel)

    def test_the_unittest_suite_is_wired_into_the_existing_ci_runner(self):
        listing = subprocess.run(["bash", str(ROOT / ".devcontainer/run-tests.bash"), "--list"],
                                 capture_output=True, text=True, check=True).stdout
        self.assertIn("tests/scripts/test-superpowers-python.bash", listing)
        wrapper = read(ROOT / "tests/scripts/test-superpowers-python.bash")
        self.assertIn("test_superpowers_*.py", wrapper)


class ImportedDocumentPortabilityTests(unittest.TestCase):
    """Exercise the actual integrity check without the PR's Git objects."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.env = dict(os.environ, GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL="/dev/null")

    def export(self):
        target = self.root / "export"
        files = [Path(__file__).relative_to(ROOT),
                 Path("tests/scripts/fixtures/superpowers-imported-documents.sha256.json"),
                 *map(Path, IMPORTED)]
        for rel in files:
            destination = target / rel
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / rel, destination)
        return target

    def git(self, root, *args):
        return subprocess.run(
            ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", *args],
            cwd=root, env=self.env, text=True, capture_output=True, check=True).stdout.strip()

    def integrity_check(self, root):
        return subprocess.run(
            [sys.executable, str(root / "tests/scripts/test_superpowers_lifecycle.py"),
             "LifecycleInstructionTests.test_imported_documents_are_unchanged_since_import"],
            cwd=root, env=self.env, text=True, capture_output=True)

    def test_export_without_git_metadata_passes(self):
        root = self.export()
        self.assertFalse((root / ".git").exists())
        result = self.integrity_check(root)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_full_and_shallow_clones_of_single_commit_main_pass(self):
        source = self.export()
        self.git(source, "init", "-b", "main")
        self.git(source, "add", ".")
        self.git(source, "commit", "-m", "squashed document snapshot")
        bare = self.root / "main-only.git"
        self.git(self.root, "clone", "--bare", str(source), str(bare))
        self.assertEqual(self.git(bare, "for-each-ref", "--format=%(refname)"), "refs/heads/main")
        self.assertEqual(self.git(bare, "rev-list", "--count", "--all"), "1")
        for shallow in (False, True):
            with self.subTest(shallow=shallow):
                clone = self.root / ("shallow" if shallow else "full")
                options = ["--depth", "1"] if shallow else []
                self.git(self.root, "clone", *options, bare.as_uri(), str(clone))
                self.assertEqual(self.git(clone, "rev-parse", "--is-shallow-repository"), str(shallow).lower())
                result = self.integrity_check(clone)
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_modified_document_is_rejected_and_identified_without_git(self):
        root = self.export()
        rel = IMPORTED[0]
        with (root / rel).open("ab") as stream:
            stream.write(b"\nchanged after import\n")
        result = self.integrity_check(root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(rel, result.stderr)
        self.assertIn("AssertionError", result.stderr)


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
                      completion_evidence, blocked=False, reason=None, missing_facts=False):
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
        if missing_facts:
            del payload["sources"]["approved_commit"]
            del payload["sources"]["execution_authority"]
        json_path = base / f"{stem}.handoff.json"
        json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        md_path = base / f"{stem}.handoff.md"
        state = "blocked / not ready" if blocked else "ready"
        approval = f"`{approved_commit}`" if approved_commit else "null（内容承認の記録は存在しない）"
        if missing_facts:
            approval, execution_authority = "unknown（フィールド欠落のため不明）", "unknown"
        reason = reason or ("一般的な外部コード実装は非対応。欠けているのは検証済みの実行経路と実行許可である。"
                            if blocked else "fixture: supported route with explicit execution authority")
        md = (f"## Status\n\nimplementation: **{state}** — {reason}\n"
              f"document_commit: `{document_commit}` / approved_commit: {approval}\n"
              f"execution_authority: {execution_authority}\n"
              f"completion_evidence: {completion_evidence}\n"
              "公開未実施（ローカルのコミットのみ）\n"
              "review copy は閲覧補助であり、正本ではない。\n")
        md_path.write_text(md, encoding="utf-8")
        return json_path, md_path

    # ------------------------------------------------------------------ the run
    def test_committed_version_and_resume_gate_eval_cases(self):
        """Documentation/eval acceptance, not an approval parser or an LLM run.

        Literal expected outcomes are tied to normative schema rows. Real Git
        blobs establish the case inputs; they do not prove agent compliance.
        """
        spec = "# sample design\n\n- 状態: approved\n\nDesign: non-replacing copy.\n"
        plan = "# sample plan\n\n- 状態: draft\n\nExecute approved repair.\n"
        approved = self.commit_doc(spec, plan)
        metadata = self.commit_doc(spec + "\nRecord: local validation passed.\n", plan)
        changed = self.commit_doc(spec.replace("non-replacing copy", "changed copy policy"), plan)
        versions = {"same-version": approved, "metadata-only": metadata, "substantive": changed}
        for status in ("completed", "superseded", "cancelled"):
            versions[status] = self.commit_doc(spec, plan.replace("draft", status))
            self.assertIn(f"- 状態: {status}", self.git(self.doc, "show", f"{versions[status]}:{self.plan_rel}"))
        self.assertNotEqual(approved, metadata)
        self.assertNotEqual(approved, changed)
        self.assertEqual(self.git(self.doc, "show", f"{metadata}:{self.spec_rel}"),
                         (spec + "\nRecord: local validation passed.\n").strip())
        self.assertEqual(self.git(self.doc, "show", f"{changed}:{self.spec_rel}"),
                         spec.replace("non-replacing copy", "changed copy policy").strip())

        self.assertIn("## Continuation gates", read(SCHEMA), "schema lacks continuation gate rules")
        schema = section(read(SCHEMA), "## Continuation gates")
        rows = {cells[0].strip(): [cell.strip() for cell in cells[1:]]
                for line in schema.splitlines() if line.startswith("| ")
                for cells in [line.strip("|").split("|")]}
        # state, current version, approval version, authority, and rule evidence
        cases = [
            ("same-version", "ready", approved, approved, "execute approved repair", ("same committed version",)),
            ("metadata-only", "ready", metadata, approved, "execute approved repair", ("retain approved_commit", "no renewed approval")),
            ("substantive-unapproved", "blocked / not ready", changed, approved, "execute approved repair", ("renewed approval", "does not name the change")),
            ("substantive-authorized", "ready", changed, approved, "change copy policy to changed copy policy", ("name the specific change", "do not invent content approval")),
            ("missing-authority", "blocked / not ready", approved, approved, None, ("missing execution authority",)),
            ("unsupported-route", "blocked / not ready", approved, approved, "implement external Issue", ("general external implementation", "remote-less")),
            ("legacy-v2-missing-facts", "blocked / not ready", approved, None, None, ("unknown", "never inferred")),
        ]
        cases.extend(("closed-plan", "blocked / not ready", versions[status], approved,
                      "execute approved repair", (status, "ordinary implementation must not resume"))
                     for status in ("completed", "superseded", "cancelled"))
        for name, want, current, approval, authority, evidence in cases:
            with self.subTest(case=name, current=current):
                condition, outcome = rows[name]
                self.assertEqual(outcome.split(";", 1)[0], want)
                for phrase in evidence:
                    self.assertIn(phrase, condition + ";" + outcome)
                self.assertEqual(len(current), 40)
                self.assertEqual(self.git(self.doc, "rev-parse", f"{current}^{{commit}}"), current)
                json_path, md_path = self.write_handoff(
                    document_commit=current, approved_commit=approval, execution_authority=authority,
                    completion_evidence=None, blocked=want == "blocked / not ready", reason=condition,
                    missing_facts=name == "legacy-v2-missing-facts")
                sources = json.loads(json_path.read_text())["sources"]
                self.assertEqual(sources["document_commit"], current)
                if name == "legacy-v2-missing-facts":
                    self.assertNotIn("approved_commit", sources)
                    self.assertNotIn("execution_authority", sources)
                else:
                    self.assertEqual(sources["approved_commit"], approval)
                    self.assertEqual(sources["execution_authority"], authority)
                md = md_path.read_text(encoding="utf-8")
                self.assertIn(f"implementation: **{want}**", md)
                self.assertIn("approved_commit: unknown" if name == "legacy-v2-missing-facts" else
                              (f"approved_commit: `{approval}`" if approval else "approved_commit: null"), md)
                # These eval facts are independent of historical approved status
                # and never reinterpret a substantive change as content approval.
                if current != approved:
                    self.assertEqual(approval, approved)
        # Route support comes from the real resolver; authority remains a human gate.
        result = self.context(parent_root=self.parent, doc_root=self.doc, code_root=self.external,
                              repo="other/repository", head_repo="other/repository", head_branch="main")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["head_remote"], "origin")

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
