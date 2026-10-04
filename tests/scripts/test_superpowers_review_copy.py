"""Immutable, non-replacing publication acceptance tests for review copies.

Real temporary Git fixtures cover the static safety checks.  Publication-boundary
races run the real module in patched subprocesses and synchronize on file
barriers, so no test depends on sleeps or stress loops to reproduce a race.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "scripts/superpowers_review_copy.py"
ORIGIN = "https://github.com/usaturn/create-reso-world.git"
SPEC = "docs/superpowers/specs/2026-10-03-sample-design.md"
SPEC2 = "docs/superpowers/specs/2026-10-04-sample-design.md"
PLAN = "docs/superpowers/plans/2026-10-04-sample-plan.md"
REVIEW_DIR = "tmp/superpowers-review"

# A driver runs the real module with a patched os.link so a test can stop it
# exactly at the publication boundary.  Production code gets no debug switches.
DRIVER = r'''
import json, os, sys, time
scripts, scenario_json, *argv = sys.argv[1:]
sys.path.insert(0, scripts)
import superpowers_review_copy as module
scenario = json.loads(scenario_json)
original = os.link

def wait_until(predicate, timeout=15.0):
    deadline = time.monotonic() + timeout
    while not predicate():
        if time.monotonic() > deadline:
            raise SystemExit("test driver: timed out at the publication boundary")
        time.sleep(0.002)

def link(source, link_to, *args, **kwargs):
    slots = scenario.get("arrive")
    if slots:
        open(os.path.join(slots["dir"], scenario["me"]), "w").close()
        wait_until(lambda: len(os.listdir(slots["dir"])) >= scenario["parties"])
    if scenario.get("parked"):
        open(scenario["parked"], "w").close()
        with open(scenario["go"], "r") as pipe:
            pipe.read()
    if scenario.get("raise_errno") is not None:
        raise OSError(scenario["raise_errno"], "injected link failure")
    return original(source, link_to, *args, **kwargs)

os.link = link
raise SystemExit(module.main(argv))
'''


class ReviewCopyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.env = dict(os.environ, GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL="/dev/null")
        self.parent = self.checkout("parent")
        self.doc = self.worktree("doc")
        self.v1 = self.head(self.doc)
        self.review = self.parent / REVIEW_DIR
        self.dest = self.review / "sample-doc-spec.md"

    # ------------------------------------------------------------------ fixture
    def git(self, root, *args):
        return subprocess.run(["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", *args],
                              cwd=root, env=self.env, check=True, text=True, capture_output=True).stdout.strip()

    def head(self, root):
        return self.git(root, "rev-parse", "HEAD")

    def checkout(self, name, *, ignore="tmp/"):
        path = self.root / name
        path.mkdir()
        self.git(path, "init", "-b", "main")
        (path / ".gitignore").write_text(f"{ignore}\n", encoding="utf-8")
        self.git(path, "add", ".gitignore")
        self.git(path, "commit", "-m", "initial")
        self.git(path, "remote", "add", "origin", ORIGIN)
        return path

    def worktree(self, name, parent=None):
        parent = parent or self.parent
        path = self.root / name
        self.git(parent, "worktree", "add", "-b", f"docs/{name}", str(path))
        (path / "docs/superpowers/specs").mkdir(parents=True)
        (path / SPEC).write_text("# sample v1\n", encoding="utf-8")
        self.git(path, "add", SPEC)
        self.git(path, "commit", "-m", "sample")
        return path

    def copy_args(self, name="sample-doc-spec.md", *, commit=None, doc=None, parent=None, path=SPEC):
        args = ["--doc-root", str(doc or self.doc), "--parent-root", str(parent or self.parent),
                "--path", path, "--name", name]
        if commit:
            args += ["--commit", commit]
        return args

    def run_copy(self, *args, cwd=None):
        if not MODULE.exists():
            return subprocess.CompletedProcess(list(args), 255, "", f"{MODULE.name} is missing\n")
        try:
            return subprocess.run([sys.executable, str(MODULE), *(str(a) for a in args)],
                                  cwd=cwd, env=self.env, text=True, capture_output=True, timeout=120)
        except subprocess.TimeoutExpired:
            return subprocess.CompletedProcess(list(args), -99, "", "timed out after 120s\n")

    def created(self, name, *, bytes_text, commit=None, path=SPEC):
        result = self.run_copy(*self.copy_args(name, commit=commit, path=path))
        self.assertEqual(result.returncode, 0, result.stderr)
        rel = f"{REVIEW_DIR}/{name}"
        self.assertEqual(result.stdout.splitlines()[0], f"created: {rel}", result.stdout)
        self.assertIn(f"source: {path} at {commit or self.v1}", result.stdout)
        digest = result.stdout.rsplit("sha256: ", 1)[1].strip()
        self.assertEqual(digest, hashlib.sha256(bytes_text.encode()).hexdigest())
        self.assertEqual((self.parent / rel).read_text(encoding="utf-8"), bytes_text)
        return result

    def rejected(self, needle, *args, code=1):
        result = self.run_copy(*args)
        self.assertEqual(result.returncode, code, result.stderr)
        self.assertIn(needle, result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertEqual(result.stdout, "")
        return result

    def assert_review_state(self, *names):
        self.assertEqual(sorted(os.listdir(self.review)), sorted(names))
        self.assertEqual(self.git(self.parent, "status", "--porcelain"), "",
                         "the copy must stay ignored and unstaged")

    # ------------------------------------------------------- deterministic races
    def driver(self, scenario, *copy_args):
        return subprocess.Popen(
            [sys.executable, "-c", DRIVER, str(MODULE.parent), json.dumps(scenario),
             *(str(a) for a in copy_args)],
            env=self.env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def start(self, scenario, *copy_args):
        return self.driver(scenario, *copy_args)

    def spawn(self, scenario, *copy_args):
        child = self.start(scenario, *copy_args)
        stdout, stderr = child.communicate(timeout=60)
        return child.returncode, stdout, stderr

    def parked_child(self, name, parked, go, commit=None, path=SPEC):
        scenario = {"parked": str(parked), "go": str(go)}
        child = self.driver(scenario, *self.copy_args(name, commit=commit, path=path))
        deadline = time.monotonic() + 15
        while not parked.exists():
            self.assertLess(time.monotonic(), deadline, "child never reached the publication boundary")
            time.sleep(0.002)
        self.addCleanup(child.wait)
        return child

    def release(self, go):
        with open(go, "w") as pipe:
            pipe.write("go\n")

    def test_distinct_concurrent_copies_leave_exactly_one_winner(self):
        (self.doc / SPEC2).write_text("# sample v2\n", encoding="utf-8")
        self.git(self.doc, "add", SPEC2)
        self.git(self.doc, "commit", "-m", "second spec")
        slots = self.root / "barrier-distinct"
        slots.mkdir()
        alpha = self.start({"arrive": {"dir": str(slots)}, "parties": 2, "me": "alpha"},
                           *self.copy_args(path=SPEC))
        beta = self.start({"arrive": {"dir": str(slots)}, "parties": 2, "me": "beta"},
                          *self.copy_args(path=SPEC2))
        alpha_out, beta_out = alpha.communicate(timeout=60), beta.communicate(timeout=60)
        attempts = [
            (alpha.returncode, alpha_out, "# sample v1\n"),
            (beta.returncode, beta_out, "# sample v2\n"),
        ]
        winners = [attempt for attempt in attempts if attempt[0] == 0]
        losers = [attempt for attempt in attempts if attempt[0] != 0]
        self.assertEqual(len(winners), 1, f"both children raced: {attempts}")
        self.assertEqual(len(losers), 1, f"both children failed: {attempts}")
        self.assertIn("created", winners[0][1][0])
        self.assertIn("already exists with other content", losers[0][1][1])
        self.assertNotIn("Traceback", losers[0][1][1])
        self.assertEqual(self.dest.read_text(encoding="utf-8"), winners[0][2])
        self.assert_review_state("sample-doc-spec.md")

    def test_concurrent_identical_copies_report_created_and_unchanged(self):
        slots = self.root / "barrier-identical"
        slots.mkdir()
        first = self.start({"arrive": {"dir": str(slots)}, "parties": 2, "me": "first"},
                           *self.copy_args())
        second = self.start({"arrive": {"dir": str(slots)}, "parties": 2, "me": "second"},
                            *self.copy_args())
        first_out, second_out = first.communicate(timeout=60), second.communicate(timeout=60)
        self.assertEqual([first.returncode, second.returncode], [0, 0],
                         f"a concurrent identical copy failed: {first_out} {second_out}")
        self.assertEqual(sorted([first_out[0].split(":")[0], second_out[0].split(":")[0]]),
                         ["created", "unchanged"])
        self.assertEqual(self.dest.read_text(encoding="utf-8"), "# sample v1\n")
        self.assert_review_state("sample-doc-spec.md")

    def test_user_annotation_written_before_a_paused_publish_survives(self):
        parked, go = self.root / "parked", self.root / "go.fifo"
        os.mkfifo(go)
        child = self.parked_child("sample-doc-spec.md", parked, go)
        self.dest.write_text("# sample v1\nuser note\n", encoding="utf-8")
        self.release(go)
        stdout, stderr = child.communicate(timeout=60)
        self.assertNotEqual(child.returncode, 0, stdout)
        self.assertIn("already exists with other content", stderr)
        self.assertIn("-r2-spec.md", stderr)
        self.assertEqual(self.dest.read_text(encoding="utf-8"), "# sample v1\nuser note\n")
        self.assert_review_state("sample-doc-spec.md")

    def test_destination_changed_into_a_directory_before_publish_fails(self):
        parked, go = self.root / "parked", self.root / "go.fifo"
        os.mkfifo(go)
        child = self.parked_child("sample-doc-spec.md", parked, go)
        self.dest.mkdir()
        self.release(go)
        stdout, stderr = child.communicate(timeout=60)
        self.assertNotEqual(child.returncode, 0, stdout)
        self.assertIn("is not a regular file", stderr)
        self.assertTrue(self.dest.is_dir() and not any(self.dest.iterdir()),
                        "the destination directory was modified")
        self.assert_review_state("sample-doc-spec.md")

    def test_destination_changed_into_a_symlink_before_publish_does_not_follow(self):
        outside = self.root / "outside-target.md"
        outside.write_text("victim\n", encoding="utf-8")
        parked, go = self.root / "parked", self.root / "go.fifo"
        os.mkfifo(go)
        child = self.parked_child("sample-doc-spec.md", parked, go)
        os.symlink(outside, self.dest)
        self.release(go)
        stdout, stderr = child.communicate(timeout=60)
        self.assertNotEqual(child.returncode, 0, stdout)
        self.assertIn("is a symlink", stderr)
        self.assertIn("-r2-spec.md", stderr)
        self.assertEqual(outside.read_text(encoding="utf-8"), "victim\n")
        self.assert_review_state("sample-doc-spec.md")

    def test_injected_link_failure_fails_closed_without_residue(self):
        code, stdout, stderr = self.spawn({"raise_errno": 13}, *self.copy_args())
        self.assertEqual(code, 1, stderr)
        self.assertIn("failed", stderr)
        self.assertFalse(self.dest.exists(), "a fallback replaced the destination")
        self.assert_review_state()

    def test_injected_link_failure_never_replaces_an_existing_destination(self):
        self.review.mkdir(parents=True)
        self.dest.write_text("annotated\n", encoding="utf-8")
        code, stdout, stderr = self.spawn({"raise_errno": 13}, *self.copy_args())
        self.assertEqual(code, 1, stderr)
        self.assertEqual(self.dest.read_text(encoding="utf-8"), "annotated\n")
        self.assert_review_state("sample-doc-spec.md")

    # ------------------------------------------------------------ static checks
    def test_creates_exact_committed_bytes_and_reports_metadata(self):
        result = self.created("sample-doc-spec.md", bytes_text="# sample v1\n")
        self.assertIn(f"source: {SPEC} at {self.v1}", result.stdout)
        self.assert_review_state("sample-doc-spec.md")

    def test_repeated_identical_copy_is_unchanged(self):
        self.created("sample-doc-spec.md", bytes_text="# sample v1\n")
        result = self.run_copy(*self.copy_args())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("unchanged: tmp/superpowers-review/sample-doc-spec.md", result.stdout)
        self.assertEqual(self.dest.read_text(encoding="utf-8"), "# sample v1\n")
        self.assert_review_state("sample-doc-spec.md")

    def test_pre_existing_identical_regular_file_is_unchanged(self):
        self.review.mkdir(parents=True)
        self.dest.write_text("# sample v1\n", encoding="utf-8")
        result = self.run_copy(*self.copy_args())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("unchanged", result.stdout)
        self.assert_review_state("sample-doc-spec.md")

    def test_uncommitted_worktree_or_index_changes_are_rejected(self):
        (self.doc / SPEC).write_text("# sample dirty\n", encoding="utf-8")
        self.rejected("commit it first", *self.copy_args())
        self.git(self.doc, "add", SPEC)
        self.rejected("commit it first", *self.copy_args())
        self.assertEqual(self.head(self.doc), self.v1)
        self.assertFalse(self.dest.exists())

    def test_old_committed_version_versus_new_dirty_source_is_rejected(self):
        self.created("sample-doc-spec.md", bytes_text="# sample v1\n")
        (self.doc / SPEC).write_text("# sample v2\n", encoding="utf-8")
        self.git(self.doc, "commit", "-am", "v2")
        v2 = self.head(self.doc)
        self.rejected("commit it first", *self.copy_args(commit=self.v1))
        self.created("sample-doc-r2-spec.md", bytes_text="# sample v2\n", commit=v2)
        self.assertEqual(self.dest.read_text(encoding="utf-8"), "# sample v1\n")

    def test_new_versioned_name_leaves_the_old_copy_untouched(self):
        self.created("sample-doc-spec.md", bytes_text="# sample v1\n")
        (self.doc / SPEC).write_text("# sample v2\n", encoding="utf-8")
        self.git(self.doc, "commit", "-am", "v2")
        self.created("sample-doc-r2-spec.md", bytes_text="# sample v2\n", commit=self.head(self.doc))
        self.assertEqual(self.dest.read_text(encoding="utf-8"), "# sample v1\n")
        self.assert_review_state("sample-doc-r2-spec.md", "sample-doc-spec.md")

    def test_committed_plan_copies_with_exact_bytes_full_sha_and_kind_flow(self):
        plan = self.doc / PLAN
        plan.parent.mkdir(parents=True)
        plan.write_text("# sample plan v1\n", encoding="utf-8")
        self.git(self.doc, "add", PLAN)
        self.git(self.doc, "commit", "-m", "plan")
        v1 = self.head(self.doc)
        dest = self.review / "sample-doc-plan.md"
        plan_args = self.copy_args(name="sample-doc-plan.md", path=PLAN, commit=v1)

        result = self.run_copy(*plan_args)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines()[0],
                         "created: tmp/superpowers-review/sample-doc-plan.md", result.stdout)
        self.assertIn(f"source: {PLAN} at {v1}", result.stdout)
        self.assertIn(f"sha256: {hashlib.sha256(b'# sample plan v1\n').hexdigest()}", result.stdout)
        self.assertEqual(dest.read_text(encoding="utf-8"), "# sample plan v1\n")
        self.assert_review_state("sample-doc-plan.md")

        result = self.run_copy(*plan_args)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("unchanged: tmp/superpowers-review/sample-doc-plan.md", result.stdout)
        self.assert_review_state("sample-doc-plan.md")

        plan.write_text("# sample plan v2\n", encoding="utf-8")
        self.git(self.doc, "add", PLAN)
        self.git(self.doc, "commit", "-m", "plan v2")
        v2 = self.head(self.doc)
        result = self.run_copy(*self.copy_args(name="sample-doc-plan.md", path=PLAN))
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("already exists with other content", result.stderr)
        self.assertIn("-r2-plan.md", result.stderr)
        self.assertEqual(dest.read_text(encoding="utf-8"), "# sample plan v1\n")
        result = self.run_copy(*self.copy_args(name="sample-doc-r2-plan.md", path=PLAN, commit=v2))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.review / "sample-doc-r2-plan.md").read_text(encoding="utf-8"),
                         "# sample plan v2\n")
        self.assertEqual(dest.read_text(encoding="utf-8"), "# sample plan v1\n")
        self.assert_review_state("sample-doc-plan.md", "sample-doc-r2-plan.md")

    def test_wrong_kind_suffix_or_uncommitted_path_is_rejected(self):
        self.rejected("is not committed",
                      *self.copy_args(path="docs/superpowers/specs/missing.md"))
        self.rejected("--path must be docs/superpowers/specs/*.md",
                      *self.copy_args(path="docs/superpowers/specs/sample-design.txt", name="x-spec.md"))
        self.rejected("--path must be docs/superpowers/specs/*.md",
                      *self.copy_args(path="docs/superpowers/other/sample-design.md", name="x-spec.md"))
        self.rejected("but --path is a spec", *self.copy_args(name="sample-doc-plan.md"))
        self.rejected("but --path is a plan",
                      *self.copy_args(name="sample-doc-spec.md", path=PLAN))
        self.rejected("must be a short lowercase file name", *self.copy_args(name="Spec.md"))
        self.rejected("must be a short lowercase file name", *self.copy_args(name="../escape-spec.md"))
        self.rejected("must be a short lowercase file name", *self.copy_args(name=".hidden-spec.md"))
        self.assertFalse(self.dest.exists())

    def test_non_regular_committed_entry_is_rejected(self):
        link = self.doc / "docs/superpowers/specs/linked-design.md"
        os.symlink("2026-10-03-sample-design.md", link)
        self.git(self.doc, "add", link)
        self.git(self.doc, "commit", "-m", "symlink entry")
        self.rejected("is not a regular file",
                      *self.copy_args(path="docs/superpowers/specs/linked-design.md",
                                      name="linked-doc-spec.md"))

    def test_commit_that_is_not_a_commit_is_rejected(self):
        self.rejected("--commit is not a commit", *self.copy_args(commit="main^{tree}"))
        self.assertFalse(self.dest.exists())

    def test_existing_destination_kinds_are_never_replaced(self):
        self.review.mkdir(parents=True)
        (self.review / "symlink-doc-spec.md").symlink_to(self.root / "outside.md")
        (self.review / "dir-doc-spec.md").mkdir()
        os.mkfifo(self.review / "fifo-doc-spec.md")
        self.dest.write_text("annotated\n", encoding="utf-8")
        for name, needle in (("symlink-doc-spec.md", "is a symlink"),
                             ("dir-doc-spec.md", "is not a regular file"),
                             ("fifo-doc-spec.md", "is not a regular file"),
                             ("sample-doc-spec.md", "already exists with other content")):
            with self.subTest(name=name):
                self.rejected(needle, *self.copy_args(name=name))
        self.assertTrue(stat.S_ISFIFO(os.stat(self.review / "fifo-doc-spec.md").st_mode))
        self.assertEqual(self.dest.read_text(encoding="utf-8"), "annotated\n")
        self.assert_review_state("dir-doc-spec.md", "fifo-doc-spec.md",
                                 "sample-doc-spec.md", "symlink-doc-spec.md")

    def test_replace_from_is_rejected_before_any_mutation(self):
        self.review.mkdir(parents=True)
        self.dest.write_text("annotated\n", encoding="utf-8")
        for name in ("sample-doc-spec.md", "missing-doc-spec.md"):
            with self.subTest(name=name):
                state = sorted(os.listdir(self.review))
                self.rejected("replace-from", *self.copy_args(name=name),
                              "--replace-from", self.v1, code=2)
                self.assertEqual(sorted(os.listdir(self.review)), state)
        self.assertEqual(self.dest.read_text(encoding="utf-8"), "annotated\n")

    def test_empty_required_roots_are_rejected_before_context_fallback(self):
        # A valid main checkout as cwd makes the old cwd fallback succeed and
        # publish; the guard must refuse the empty explicit root instead.
        for subtest in ("--parent-root", "--doc-root"):
            with self.subTest(flag=subtest):
                kwargs = {"--parent-root": str(self.parent), "--doc-root": str(self.doc)}
                kwargs[subtest] = ""
                args = ["--doc-root", kwargs["--doc-root"], "--parent-root", kwargs["--parent-root"],
                        "--path", SPEC, "--name", "sample-doc-spec.md"]
                result = self.run_copy(*args, cwd=self.parent)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn("usage", result.stderr)
                self.assertIn(f"{subtest} must be a nonempty explicit absolute path", result.stderr)
                self.assertNotIn("Traceback", result.stderr)
                self.assertFalse((self.parent / REVIEW_DIR).exists(),
                                 "an empty root still published through the cwd fallback")
        for left in ("--parent-root", "--doc-root"):
            for right in ("--parent-root", "--doc-root"):
                if left == right:
                    continue
                args = [left, "", right, str(self.doc), "--path", SPEC, "--name", "sample-doc-spec.md"]
                result = self.run_copy(*args, cwd=self.parent)
                self.assertEqual(result.returncode, 2, result.stderr)
        self.assertFalse((self.parent / REVIEW_DIR).exists())

    def test_usage_errors_exit_2(self):
        result = self.run_copy()
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("usage", result.stderr)
        result = self.run_copy("--unknown-flag")
        self.assertEqual(result.returncode, 2, result.stderr)

    def test_context_rejections_keep_shared_module_messages_and_change_nothing(self):
        foreign = self.checkout("foreign")
        self.git(foreign, "remote", "set-url", "origin", "https://github.com/someone/other.git")
        self.rejected("origin is not usaturn/create-reso-world", *self.copy_args(doc=foreign))
        self.rejected("must be an absolute path", *self.copy_args(parent="relative-parent"))
        self.rejected("must be the main checkout", *self.copy_args(parent=self.doc))
        self.assertFalse(self.dest.exists())

    def test_destination_must_be_ignored_and_inside_the_parent_checkout(self):
        unignored = self.checkout("unignored", ignore="nothing-ignored/")
        unignored_doc = self.worktree("unignored-doc", parent=unignored)
        self.rejected("is not ignored", *self.copy_args(parent=unignored, doc=unignored_doc))
        self.assertFalse((unignored / REVIEW_DIR).exists())
        elsewhere = self.root / "elsewhere"
        elsewhere.mkdir()
        linked = self.checkout("linked")
        (linked / SPEC).parent.mkdir(parents=True)
        (linked / SPEC).write_text("# sample v1\n", encoding="utf-8")
        self.git(linked, "add", SPEC)
        self.git(linked, "commit", "-m", "sample")
        (linked / "tmp").mkdir()
        (linked / "tmp/superpowers-review").symlink_to(elsewhere)
        self.rejected("is a symlink", *self.copy_args(parent=linked, doc=linked))
        self.assertEqual(os.listdir(elsewhere), [])


if __name__ == "__main__":
    unittest.main()
