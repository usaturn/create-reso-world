"""Behavior tests for pi-only migration; no live user files or network access."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
CLEANUP = ROOT / ".devcontainer/cleanup_pi_mcp.py"
MCP_FILES = (
    "mcp.json", "mcp-auth.json", "mcp-cache.json", "mcp-project-approvals.json",
    "mcp-onboarding.json", "mcp-npx-cache.json",
)
REMOVED = ("pi-mcp-adapter", "@upstash/context7-pi")
KEPT = ["npm:pi-distill", {"source": "npm:other@1.0", "extensions": []}]


class PiMcpCleanupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="pi-mcp-cleanup-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.home = self.base / "home"
        self.agent = self.home / ".pi/agent"
        self.agent.mkdir(parents=True)
        self.project = self.base / "project"
        self.project.mkdir()
        self.bin = self.base / "bin"
        self.bin.mkdir()
        (self.bin / "pi").symlink_to(ROOT / ".devcontainer/tests/fake_pi_packages.py")
        self.env = {**os.environ, "HOME": str(self.home), "PATH": f"{self.bin}:{os.environ['PATH']}",
                    "PI_CODING_AGENT_DIR": str(self.agent), "PI_OFFLINE": "1"}
        self.env.pop("FAKE_PI_REMOVE", None)
        self.env.pop("FAKE_PI_REQUIRE_CLEAN", None)

    def save(self, path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2) + "\n")

    def seed_packages(self, entries=None, manifests=True, installed=True):
        self.save(self.agent / "settings.json", {
            "theme": "keep-me", "defaultTools": ["+codemode"], "skills": ["./keep-skill"],
            "extensions": ["+builtin:mcp"],
            "packages": entries if entries is not None else KEPT + ["npm:" + name for name in REMOVED],
        })
        if manifests:
            self.save(self.agent / "npm/package.json", {"dependencies": {
                "pi-distill": "^1.0", "pi-mcp-adapter": "^2.1", "@upstash/context7-pi": "^1.1",
            }})
            self.save(self.agent / "npm/package-lock.json", {"lockfileVersion": 3, "packages": {
                "": {"dependencies": {name: "*" for name in REMOVED}},
                "node_modules/pi-mcp-adapter": {"version": "2.1.0"},
                "node_modules/@upstash/context7-pi": {"version": "1.1.0"},
                "node_modules/pi-distill": {"version": "1.0.0"},
            }})
        if installed:
            for name in (*REMOVED, "pi-distill"):
                self.save(self.agent / "npm/node_modules" / name / "package.json", {"name": name})

    def run_cleanup(self, **overrides):
        return subprocess.run([sys.executable, str(CLEANUP)], cwd=self.project,
                              env={**self.env, **overrides}, text=True, capture_output=True)

    def run_provisioning(self, **overrides):
        installer = (ROOT / ".devcontainer/install_beforehand.bash").read_text()
        pi_step = installer.index('step "Installing pi"')
        start = installer.index('\nstep ', pi_step + 1)
        end = installer.index('if ! uv run --no-project .devcontainer/setup_pi_tool_display.py;')
        # Execute the actual pi provisioning section, not a copy of the extension list.
        fragment = 'set -u\nstep() { :; }\nfail() { echo "ERROR: $*" >&2; exit 1; }\n'
        fragment += installer[start:end]
        return subprocess.run(["bash", "-c", fragment], cwd=ROOT,
                              env={**self.env, **overrides}, text=True, capture_output=True)

    def assert_success(self, result):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def assert_packages_clean(self):
        if (self.agent / "settings.json").exists():
            self.assertEqual(json.loads((self.agent / "settings.json").read_text())["packages"], KEPT)
        for name in REMOVED:
            self.assertFalse((self.agent / "npm/node_modules" / name).exists(), name)
        for path in (self.agent / "npm").rglob("*.json"):
            for name in REMOVED:
                self.assertNotIn(f'"{name}"', path.read_text(), str(path))
                self.assertNotIn(f'"node_modules/{name}"', path.read_text(), str(path))

    # Break caught: cleanup invoked too late, omitted, or either removed package reinstalled.
    def test_provisioning_cleans_before_installing_only_retained_extensions(self):
        self.seed_packages()
        for name in MCP_FILES:
            (self.agent / name).write_text("old pi-only state")
        result = self.run_provisioning(FAKE_PI_REQUIRE_CLEAN="1")
        for name in MCP_FILES:
            self.assertFalse((self.agent / name).exists(), name)
        self.assert_success(result)
        settings = json.loads((self.agent / "settings.json").read_text())
        sources = [entry if isinstance(entry, str) else entry["source"] for entry in settings["packages"]]
        self.assertEqual(sources, [
            "npm:pi-distill", "npm:other@1.0", "npm:@teelicht/pi-superagents",
            "npm:@jc4649/notify", "npm:pi-safe-search", "npm:pi-diet-ripgrep",
            "git:github.com/obra/superpowers", "npm:pi-lens", "npm:pi-simplify",
            "npm:@howaboua/pi-skill-skill-creator",
        ])

    # Break caught: attempting removal/creating settings on a fresh installation.
    def test_fresh_environment_stays_empty(self):
        self.agent.rmdir()
        self.assert_success(self.run_cleanup())
        self.assertFalse(self.agent.exists())

    # Break caught: skipping declared packages or deleting unrelated settings/resources.
    def test_installed_packages_are_removed_without_changing_other_settings(self):
        self.seed_packages()
        before = json.loads((self.agent / "settings.json").read_text())
        for name in ("auth.json", "models.json", "extensions/other/config.json", "mcp-unrelated.json"):
            path = self.agent / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"keep these bytes\r\n")
        self.assert_success(self.run_cleanup())
        self.assert_packages_clean()
        before["packages"] = KEPT
        self.assertEqual(json.loads((self.agent / "settings.json").read_text()), before)
        self.assertTrue((self.agent / "npm/node_modules/pi-distill").is_dir())
        for name in ("auth.json", "models.json", "extensions/other/config.json", "mcp-unrelated.json"):
            self.assertEqual((self.agent / name).read_bytes(), b"keep these bytes\r\n")

    # Break caught: treating an undeclared pi remove result as failure or relying on pi list only.
    def test_manifest_only_packages_are_removed(self):
        self.seed_packages(entries=KEPT, installed=False)
        self.assert_success(self.run_cleanup())
        self.assert_packages_clean()

    # Break caught: ignoring lock-only or installed-but-undeclared residue.
    def test_lock_only_and_installed_only_packages_are_removed(self):
        for fixture in ("lock", "installed"):
            with self.subTest(fixture=fixture):
                self.seed_packages(entries=KEPT, manifests=False, installed=fixture == "installed")
                if fixture == "lock":
                    self.save(self.agent / "npm/package-lock.json", {
                        "dependencies": {name: {"version": "1.0.0"} for name in REMOVED},
                    })
                self.assert_success(self.run_cleanup())
                self.assert_packages_clean()

    # Break caught: matching only exact strings instead of npm identity in declarations.
    def test_pinned_and_object_declarations_are_removed(self):
        self.seed_packages(entries=KEPT + ["npm:pi-mcp-adapter@2.1.0", {
            "source": "npm:@upstash/context7-pi@1.1.0", "extensions": [], "skills": [],
        }])
        self.assert_success(self.run_cleanup())
        self.assert_packages_clean()

    # Break caught: broad MCP glob, following MCP symlinks, or crossing agent directory scope.
    def test_mcp_state_cleanup_preserves_shared_files_and_symlink_targets(self):
        shared = {
            self.project / ".mcp.json": b'{ "mcpServers": {} }\r\n',
            self.project / ".codex/config.toml": b"[mcp_servers.keep]\n",
            self.project / ".cursor/mcp.json": b'{"shared":true}\n',
            self.project / ".pi/settings.json": b'{"packages":["npm:pi-mcp-adapter"]}\n',
            self.project / ".pi/mcp.json": b'{"project":"keep"}\n',
            self.home / ".npm/_npx/keep/cache": b"shared npx cache\n",
            self.home / ".config/create-reso-world/env": b"CONTEXT7_API_KEY=keep\n",
            self.project / ".agents/skills/find-docs/SKILL.md": b"shared find-docs\n",
        }
        for path, data in shared.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        skill_link = self.agent / "skills/find-docs"
        skill_link.parent.mkdir()
        skill_link.symlink_to(self.project / ".agents/skills/find-docs", target_is_directory=True)
        for index, name in enumerate(MCP_FILES):
            path = self.agent / name
            if index % 2:
                path.symlink_to(self.project / ".mcp.json")
            else:
                path.write_text("old pi state")
        self.assert_success(self.run_cleanup())
        for name in MCP_FILES:
            self.assertFalse(os.path.lexists(self.agent / name), name)
        for path, data in shared.items():
            self.assertEqual(path.read_bytes(), data, str(path))
        self.assertTrue(skill_link.is_symlink())

    # Break caught: redoing removals or rewriting clean settings on subsequent provisioning.
    def test_cleanup_is_idempotent_and_leaves_clean_bytes_untouched(self):
        self.seed_packages()
        self.assert_success(self.run_cleanup())
        self.assert_packages_clean()
        files = {path: path.read_bytes() for path in self.agent.rglob("*") if path.is_file()}
        self.assert_success(self.run_cleanup(FAKE_PI_REMOVE="fail"))
        self.assertEqual({path: path.read_bytes() for path in self.agent.rglob("*") if path.is_file()}, files)

    # Break caught: hardcoding ~/.pi/agent rather than honoring the runtime convention.
    def test_agent_directory_override_and_home_fallback(self):
        default_agent = self.agent
        (default_agent / "mcp-cache.json").write_text("keep default")
        self.agent = self.home / "custom agent"
        self.agent.mkdir()
        self.env["PI_CODING_AGENT_DIR"] = "~/custom agent"
        (self.agent / "mcp-cache.json").write_text("custom pi state")
        self.assert_success(self.run_cleanup())
        self.assertFalse((self.agent / "mcp-cache.json").exists())
        self.assertEqual((default_agent / "mcp-cache.json").read_text(), "keep default")
        env = dict(self.env)
        env.pop("PI_CODING_AGENT_DIR")
        result = subprocess.run([sys.executable, str(CLEANUP)], cwd=self.project, env=env,
                                text=True, capture_output=True)
        self.assert_success(result)
        self.assertFalse((default_agent / "mcp-cache.json").exists())

    # Break caught: swallowing package-manager errors or trusting exit 0 without postconditions.
    def test_removal_errors_and_residual_packages_fail_visibly(self):
        for mode in ("fail", "keep-settings", "keep-manifest", "keep-installed",
                     "fail-after-clean", "break-settings", "nonzero-declared"):
            with self.subTest(mode=mode):
                self.seed_packages()
                result = self.run_cleanup(FAKE_PI_REMOVE=mode)
                self.assertNotEqual(result.returncode, 0, mode)
                self.assertIn("ERROR: pi-only MCP cleanup:", result.stderr)

    # Break caught: accepting genuine errors simply because a package was undeclared.
    def test_undeclared_removal_error_fails_even_after_cleanup(self):
        self.seed_packages(entries=KEPT)
        result = self.run_cleanup(FAKE_PI_REMOVE="fail-after-clean")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("removal failed", result.stderr)

    # Break caught: silently treating unreadable/malformed declarations or manifests as absent.
    def test_invalid_or_unreadable_storage_aborts_before_mutation(self):
        for relative in ("settings.json", "npm/package.json", "npm/package-lock.json"):
            for fixture in ("invalid-json", "unreadable"):
                if fixture == "unreadable" and os.geteuid() == 0:
                    continue  # root bypasses file permission bits
                with self.subTest(relative=relative, fixture=fixture):
                    self.seed_packages()
                    state = self.agent / "mcp-cache.json"
                    state.write_text("must survive failed inspection")
                    path = self.agent / relative
                    if fixture == "invalid-json":
                        path.write_text("{broken")
                    else:
                        path.chmod(0)
                    try:
                        result = self.run_cleanup()
                        self.assertNotEqual(result.returncode, 0)
                        self.assertIn(str(path), result.stderr)
                        self.assertEqual(state.read_text(), "must survive failed inspection")
                    finally:
                        path.chmod(0o600)

    # Break caught: following settings/npm storage links and modifying shared targets.
    def test_symlinked_storage_is_refused_without_touching_shared_targets(self):
        for relative in ("settings.json", "npm", "npm/package.json", "npm/package-lock.json",
                         "npm/node_modules", "npm/node_modules/@upstash",
                         "npm/node_modules/pi-mcp-adapter", "settings.json.lock"):
            with self.subTest(relative=relative):
                self.seed_packages()
                state = self.agent / "mcp-cache.json"
                state.write_text("must survive unsafe storage")
                path = self.agent / relative
                target = self.base / ("shared-" + relative.replace("/", "-"))
                if path.exists():
                    path.rename(target)
                else:
                    target.mkdir()
                path.symlink_to(target, target_is_directory=target.is_dir())
                snapshot = {item: item.read_bytes() for item in target.rglob("*") if item.is_file()} if target.is_dir() else {target: target.read_bytes()}
                try:
                    result = self.run_cleanup()
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("symlink", result.stderr.lower())
                    self.assertEqual(state.read_text(), "must survive unsafe storage")
                    for item, data in snapshot.items():
                        self.assertEqual(item.read_bytes(), data)
                finally:
                    path.unlink()
                    target.rename(path)

    # Break caught: passing hard-linked manifests/settings to pi and mutating shared bytes.
    def test_hardlinked_storage_is_refused(self):
        for relative in ("settings.json", "npm/package.json", "npm/package-lock.json"):
            with self.subTest(relative=relative):
                self.seed_packages()
                path = self.agent / relative
                target = self.base / ("hardlink-" + relative.replace("/", "-"))
                os.link(path, target)
                before = target.read_bytes()
                try:
                    result = self.run_cleanup()
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("hard-linked", result.stderr)
                    self.assertEqual(target.read_bytes(), before)
                finally:
                    target.unlink()

    # Break caught: reading a FIFO as JSON and blocking provisioning instead of refusing it.
    def test_nonregular_settings_storage_is_refused(self):
        path = self.agent / "settings.json"
        os.mkfifo(path)
        try:
            result = subprocess.run([sys.executable, str(CLEANUP)], cwd=self.project,
                                    env=self.env, text=True, capture_output=True, timeout=1)
        except subprocess.TimeoutExpired:
            self.fail("cleanup blocked reading a FIFO settings file")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(str(path), result.stderr)

    # Break caught: normalizing dangerous root/home/relative/traversal paths into cleanup targets.
    def test_unsafe_agent_directory_is_refused(self):
        for value in ("/", str(self.home), ".", "relative-agent", str(self.agent / "..")):
            with self.subTest(value=value):
                result = self.run_cleanup(PI_CODING_AGENT_DIR=value)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("unsafe", result.stderr.lower())

    # Break caught: resolving a linked agent directory or linked ancestor before checking safety.
    def test_symlinked_agent_directory_or_parent_is_refused(self):
        (self.agent / "mcp-cache.json").write_text("must survive linked directory")
        for target in (self.agent, self.home / ".pi"):
            with self.subTest(target=str(target)):
                link = self.base / "linked-agent"
                link.symlink_to(target, target_is_directory=True)
                value = str(link if target == self.agent else link / "agent")
                try:
                    result = self.run_cleanup(PI_CODING_AGENT_DIR=value)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("symlink", result.stderr.lower())
                    self.assertEqual((self.agent / "mcp-cache.json").read_text(), "must survive linked directory")
                finally:
                    link.unlink()

    # Break caught: ignoring unlink errors or recursively deleting an unexpected state directory.
    def test_mcp_state_filesystem_errors_fail_visibly(self):
        state = self.agent / "mcp-cache.json"
        state.mkdir()
        result = self.run_cleanup()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(str(state), result.stderr)
        self.assertTrue(state.is_dir())

    # Break caught: treating a real unlink permission error as a missing file.
    def test_mcp_unlink_permission_error_fails_visibly(self):
        if os.geteuid() == 0:
            self.skipTest("root bypasses directory permission bits")
        state = self.agent / "mcp-cache.json"
        state.write_text("protected state")
        self.agent.chmod(0o500)
        try:
            result = self.run_cleanup()
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(str(state), result.stderr)
            self.assertEqual(state.read_text(), "protected state")
        finally:
            self.agent.chmod(0o700)

    # Break caught: using exists() to skip dangling MCP symlinks rather than unlinking them.
    def test_dangling_mcp_symlink_is_unlinked(self):
        path = self.agent / "mcp-auth.json"
        path.symlink_to(self.base / "absent-target")
        self.assert_success(self.run_cleanup())
        self.assertFalse(os.path.lexists(path))

    # Break caught: provisioning continuing to install unrelated extensions after cleanup fails.
    def test_provisioning_stops_on_cleanup_failure(self):
        self.seed_packages()
        result = self.run_provisioning(FAKE_PI_REMOVE="fail")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("MCP", result.stderr)
        packages = json.loads((self.agent / "settings.json").read_text())["packages"]
        self.assertNotIn("npm:@jc4649/notify", packages)


if __name__ == "__main__":
    unittest.main(verbosity=2)
