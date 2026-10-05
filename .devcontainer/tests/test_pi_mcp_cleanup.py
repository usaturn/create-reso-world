"""Behavior tests for pi-only migration; no live user files or network access."""
import json
import os
from pathlib import Path
import shutil
import re
import runpy
from unittest.mock import patch
import subprocess
import sys
import tempfile
import stat
import unittest

ROOT = Path(__file__).resolve().parents[2]
CLEANUP = ROOT / ".devcontainer/cleanup_pi_mcp.py"
MCP_FILES = (
    "mcp-cache.json", "mcp-project-approvals.json", "mcp-onboarding.json", "mcp-npx-cache.json",
)
BUILTIN_MCP_FILES = ("mcp.json", "mcp-auth.json")
REMOVED = ("pi-mcp-adapter", "@upstash/context7-pi", "pi-distill",
           "pi-extensions-tool-display", "pi-extensions-i18n")
KEPT = ["npm:keep-extension", {"source": "npm:other@1.0", "extensions": []}]


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
                "keep-extension": "^1.0", "other": "1.0", "pi-mcp-adapter": "^2.1",
                "@upstash/context7-pi": "^1.1",
                "pi-distill": "^1.0", "pi-extensions-tool-display": "^1.0",
                "pi-extensions-i18n": "^1.0",
            }})
            self.save(self.agent / "npm/package-lock.json", {"lockfileVersion": 3, "packages": {
                "": {"dependencies": {name: "*" for name in (*REMOVED, "keep-extension", "other")}},
                "node_modules/pi-mcp-adapter": {"version": "2.1.0"},
                "node_modules/@upstash/context7-pi": {"version": "1.1.0"},
                "node_modules/keep-extension": {"version": "1.0.0"},
                **{"node_modules/" + name: {"version": "1.0.0"} for name in REMOVED[2:]},
                "node_modules/other": {"version": "1.0.0"},
            }})
        if installed:
            for name in (*REMOVED, "keep-extension"):
                self.save(self.agent / "npm/node_modules" / name / "package.json", {"name": name})

    def run_cleanup(self, **overrides):
        return subprocess.run([sys.executable, str(CLEANUP)], cwd=self.project,
                              env={**self.env, **overrides}, text=True, capture_output=True)

    def run_provisioning(self, **overrides):
        installer = (ROOT / ".devcontainer/install_beforehand.bash").read_text()
        pi_step = installer.index('step "Installing pi"')
        start = installer.index('\nstep ', pi_step + 1)
        end = installer.index('step "Placing ~/.pi/agent/models.json"')
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

    def storage_snapshot(self):
        return {path.relative_to(self.agent): path.read_bytes()
                for path in self.agent.rglob("*") if path.is_file()}

    # R3-3 break: serialization/replace errors touch live output or leave staged files.
    def test_r3_shared_writer_serializes_before_temp_and_cleans_failed_replace(self):
        helper = ROOT / ".devcontainer/pi_json.py"
        self.assertTrue(helper.exists(), "shared safe JSON helper is missing")
        write_object = runpy.run_path(str(helper))["write_object"]
        path = self.agent / "models.json"
        path.write_bytes(b'{"original":true}\r\n')
        path.chmod(0o640)
        before = self.full_storage_snapshot()
        for data in ({"bad": float("nan")}, {"bad": object()}):
            with self.subTest(data=data):
                with patch("tempfile.mkstemp", side_effect=AssertionError("temp opened before serialization")):
                    with self.assertRaises((ValueError, TypeError)):
                        write_object(path, data)
                self.assertEqual(self.full_storage_snapshot(), before)
        with patch("os.replace", side_effect=PermissionError("fixture replace denied")):
            with self.assertRaises(PermissionError):
                write_object(path, {"new": "\ud800"})
        self.assertEqual(self.full_storage_snapshot(), before)
        write_object(path, {"new": "\ud800", "unicode": "日本語😀"})
        self.assertEqual(json.loads(path.read_text()), {"new": "\ud800", "unicode": "日本語😀"})
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o640)
        self.assertTrue(path.read_bytes().endswith(b"\n"))
        path.unlink()
        write_object(path, {})
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)

    def full_storage_snapshot(self):
        return {path.relative_to(self.agent): (stat.S_IMODE(path.stat().st_mode), path.read_bytes())
                for path in self.agent.rglob("*") if path.is_file()}

    def link_snapshot(self, *roots):
        """Record entries without following links, so replaced links and changed targets both show."""
        snapshot = {}
        for root in roots:
            for path in root.rglob("*"):
                info = path.lstat()
                if stat.S_ISLNK(info.st_mode):
                    snapshot[path] = ("symlink", os.readlink(path))
                elif stat.S_ISREG(info.st_mode):
                    snapshot[path] = (stat.S_IMODE(info.st_mode), info.st_nlink, path.read_bytes())
                else:
                    snapshot[path] = (stat.S_IFMT(info.st_mode),)
        return snapshot

    def fresh_agent(self, name):
        self.agent = self.home / name
        self.agent.mkdir(parents=True)
        self.env["PI_CODING_AGENT_DIR"] = str(self.agent)

    def run_provider_setup(self, provider, **overrides):
        scripts = {"deepinfra": "setup_pi.zsh", "opencode-go": "setup_pi_opencode_go.zsh",
                   "commandcode": "setup_pi_commandcode_goat.zsh"}
        # No registry/model catalog/API requests: only the external pi boundary is replaced.
        pi = self.bin / "pi"
        pi.unlink(missing_ok=True)
        pi.write_text('#!/bin/sh\n'
                      'if [ "$1" = update ]; then exit 0; fi\n'
                      'if [ "$1" = --list-models ]; then\n'
                      'printf "opencode-go %s 128k\\n" "$2"; exit 0; fi\nexit 64\n')
        pi.chmod(0o755)
        env = {**self.env, "DEEPINFRA_TOKEN": "offline-fixture", "OPENCODE_API_KEY": "offline-fixture"}
        env.pop("COMMANDCODE_API_KEY", None)
        return subprocess.run(["zsh", str(ROOT / ".devcontainer" / scripts[provider])],
                              cwd=self.project, env={**env, **overrides}, text=True, capture_output=True)

    def assert_setup_failed(self, result):
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("setup complete", result.stdout.lower())
        self.assertNotIn("JSON validation: OK", result.stdout)

    # R3-1 break: raw overflow exponent OR integer passes preflight and changes unrelated state.
    def test_r3_numeric_overflow_refused_in_every_metadata_before_mutation(self):
        paths = ("settings.json", "npm/package.json", "npm/package-lock.json",
                 "npm/npm-shrinkwrap.json", "npm/node_modules/.package-lock.json")
        tokens = ("1e999", "-1e999", "1" + "0" * 309, "-" + "1" + "0" * 309)
        for index, relative in enumerate(paths):
            for token_index, token in enumerate(tokens):
                with self.subTest(relative=relative, token=token[:16]):
                    self.fresh_agent(f"numeric-{index}-{token_index}")
                    self.seed_packages()
                    for name in paths[3:]:
                        self.save(self.agent / name, {"custom": "keep"})
                    for name in (*MCP_FILES, *BUILTIN_MCP_FILES, "auth.json", "models.json"):
                        (self.agent / name).write_bytes(b"unrelated original bytes\r\n")
                    path = self.agent / relative
                    data = json.loads(path.read_text())
                    data["nested"] = [{"number": "RAW_TOKEN"}]
                    path.write_text(json.dumps(data).replace('"RAW_TOKEN"', token) + "\n")
                    path.chmod(0o640)
                    before = self.full_storage_snapshot()
                    calls = self.base / f"numeric-calls-{index}-{token_index}"
                    result = self.run_cleanup(FAKE_PI_CALL_LOG=str(calls))
                    self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertIn(str(path), result.stderr)
                    self.assertIn("finite", result.stderr.lower())
                    self.assertFalse(calls.exists(), "pi ran before numeric preflight")
                    self.assertEqual(self.full_storage_snapshot(), before)
                    self.assertFalse((self.agent / "migration-backups").exists())

    # R3-1 break: less common cleanup branches skip strict decoding before cache unlink/backup.
    def test_r3_numeric_refusal_without_npm_prefix(self):
        for branch in ("disable-only", "settings-only", "cache-only"):
            with self.subTest(branch=branch):
                self.fresh_agent(branch)
                path = self.agent / "settings.json"
                fields = {'disable-only': '"extensions":["-builtin:mcp"],',
                          'settings-only': '"packages":["npm:pi-distill"],', 'cache-only': ''}
                path.write_text('{'+fields[branch]+'"custom":1e999}\n')
                path.chmod(0o640)
                (self.agent / "mcp-cache.json").write_bytes(b"keep cache")
                before = self.full_storage_snapshot()
                calls = self.base / f"calls-{branch}"
                result = self.run_cleanup(FAKE_PI_CALL_LOG=str(calls))
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("finite", result.stderr.lower())
                self.assertFalse(calls.exists())
                self.assertEqual(self.full_storage_snapshot(), before)

    # Positive numeric controls: no safe-integer restriction, overflow-looking zero stays valid.
    def test_r3_finite_numbers_and_quoted_overflow_remain_accepted(self):
        path = self.agent / "settings.json"
        path.write_text('{"extensions":["-builtin:mcp"],"numbers":'
                        '[1.7976931348623157e308,-1.7976931348623157e308,0e999,5e-324,'
                        '9007199254740993,42,"1e999"],"unicode":"日本語😀"}\n')
        expected = json.loads(path.read_text())
        expected["extensions"] = []
        path.chmod(0o640)
        self.assert_success(self.run_cleanup())
        self.assertEqual(json.loads(path.read_text()), expected)
        self.assertIsInstance(json.loads(path.read_text())["numbers"][4], int)
        snapshot = self.full_storage_snapshot()
        self.assert_success(self.run_cleanup(FAKE_PI_REMOVE="fail"))
        self.assertEqual(self.full_storage_snapshot(), snapshot)

    # R3-2 break: valid escaped lone surrogates in keys/values fail during UTF-8 settings save.
    def test_r3_surrogate_settings_roundtrip_backup_mode_and_noop(self):
        for packages in ([], ["npm:pi-distill"]):
            with self.subTest(packages=packages):
                self.fresh_agent(f"surrogates-{len(packages)}")
                path = self.agent / "settings.json"
                data = {"packages": packages, "extensions": ["-builtin:mcp", "./custom"],
                        "custom": {"\ud800": ["\udfff", {"\udc00": "\udbff"}],
                                   "normal": ["日本語", "😀", "\\ud800"]}}
                path.write_bytes(b"\xef\xbb\xbf" + (json.dumps(data) + "\n").encode())
                path.chmod(0o640)
                original = path.read_bytes()
                self.assert_success(self.run_cleanup())
                data["packages"] = []
                data["extensions"] = ["./custom"]
                self.assertEqual(json.loads(path.read_text()), data)
                self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o640)
                backups = list((self.agent / "migration-backups").glob("pi-retired-*"))
                self.assertEqual(len(backups), 1)
                self.assertEqual((backups[0] / "settings.json").read_bytes(), original)
                before = self.full_storage_snapshot()
                self.assert_success(self.run_cleanup(FAKE_PI_REMOVE="fail"))
                self.assertEqual(self.full_storage_snapshot(), before)
                self.assertEqual(list(self.agent.glob(".settings*")), [])

    # R3-2 control: raw invalid UTF-8 is not the valid JSON-escape case and must stop early.
    def test_r3_invalid_utf8_refused_before_changes(self):
        path = self.agent / "settings.json"
        path.write_bytes(b'{"extensions":["-builtin:mcp"],"custom":"\xed\xa0\x80"}')
        (self.agent / "mcp-cache.json").write_bytes(b"keep cache")
        before = self.full_storage_snapshot()
        calls = self.base / "calls"
        result = self.run_cleanup(FAKE_PI_CALL_LOG=str(calls))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(str(path), result.stderr)
        self.assertFalse(calls.exists())
        self.assertEqual(self.full_storage_snapshot(), before)

    # R3-4 break: npm ignores target-containing package-lock when shrinkwrap is present.
    @unittest.skipUnless(shutil.which("npm"), "real npm required for root lock regression")
    def test_r3_real_npm_shadowed_lock_stops_before_backup_or_removal(self):
        self.use_real_npm()
        # Log entry while preserving the real npm uninstall boundary.
        pi = self.bin / "pi"
        pi.write_text(pi.read_text().replace('#!/bin/sh\n',
                      '#!/bin/sh\nprintf "%s\\n" "$*" >> "$PI_LOCK_CALLS"\n'))
        for declared in (False, True):
            with self.subTest(declared=declared):
                self.seed_real_npm(f"dual-lock-{declared}", {"keep-extension": "1.0.0", "pi-mcp-adapter": "1.0.0"})
                if declared:
                    self.save(self.agent / "settings.json", {"packages": ["npm:keep-extension", "npm:pi-mcp-adapter"]})
                lock = self.agent / "npm/package-lock.json"
                shrinkwrap = self.agent / "npm/npm-shrinkwrap.json"
                shrinkwrap.write_bytes(lock.read_bytes())
                lock.chmod(0o640)
                before = self.full_storage_snapshot()
                calls = self.base / f"lock-calls-{declared}"
                result = self.run_cleanup(PI_LOCK_CALLS=str(calls))
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(str(lock), result.stderr)
                self.assertIn(str(shrinkwrap), result.stderr)
                self.assertIn("reconcile", result.stderr.lower())
                self.assertFalse(calls.exists(), "pi ran before shadowed lock preflight")
                self.assertEqual(self.full_storage_snapshot(), before)

    # R3-4 controls: single active lock and harmless shadowed lock are not refused.
    @unittest.skipUnless(shutil.which("npm"), "real npm required for root lock regression")
    def test_r3_real_npm_single_and_clean_shadowed_locks_succeed(self):
        self.use_real_npm()
        for kind in ("package-lock", "shrinkwrap", "clean-shadowed"):
            with self.subTest(kind=kind):
                original = None
                self.seed_real_npm(kind, {"keep-extension": "1.0.0", "pi-mcp-adapter": "1.0.0"})
                lock = self.agent / "npm/package-lock.json"
                if kind != "package-lock":
                    lock.rename(self.agent / "npm/npm-shrinkwrap.json")
                if kind == "clean-shadowed":
                    lock.write_bytes(b'{"lockfileVersion":3,"packages":{}}\r\n')
                    lock.chmod(0o640)
                    original = lock.read_bytes()
                kept = (self.agent / "npm/node_modules/keep-extension/extension.js").read_bytes()
                self.assert_success(self.run_cleanup())
                self.assertFalse((self.agent / "npm/node_modules/pi-mcp-adapter").exists())
                self.assertEqual((self.agent / "npm/node_modules/keep-extension/extension.js").read_bytes(), kept)
                if kind == "clean-shadowed":
                    self.assertIsNotNone(original)
                    self.assertEqual(lock.read_bytes(), original)
                    self.assertEqual(stat.S_IMODE(lock.stat().st_mode), 0o640)

    # R3-3 break: each setup corrupts valid escaped Unicode or fails to preserve existing mode.
    def test_r3_provider_models_surrogate_roundtrip_and_modes(self):
        for provider in ("deepinfra", "opencode-go", "commandcode"):
            with self.subTest(provider=provider):
                self.fresh_agent(f"provider-unicode-{provider}")
                path = self.agent / "models.json"
                custom = {"providers": {"personal": {"models": []}},
                          "custom": {"\ud800": ["\udfff", "日本語😀", "\\ud800"]}}
                self.save(path, custom)
                path.chmod(0o640)
                self.assert_success(self.run_provider_setup(provider))
                data = json.loads(path.read_text())
                self.assertEqual(data["custom"], custom["custom"])
                self.assertEqual(data["providers"]["personal"], custom["providers"]["personal"])
                self.assertIn(provider, data["providers"])
                self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o640)
                self.assertFalse((self.agent / "models.json.tmp").exists())
                path.unlink()
                self.assert_success(self.run_provider_setup(provider))
                self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)

    # R3-3 break: exponent/integer overflow and nonstandard constants are emitted as invalid JSON.
    def test_r3_provider_models_reject_unsafe_numbers_preserving_original(self):
        for provider in ("deepinfra", "opencode-go", "commandcode"):
            for index, token in enumerate(("1e999", "-1e999", "1" + "0" * 309,
                                           "-" + "1" + "0" * 309, "NaN", "Infinity", "-Infinity")):
                with self.subTest(provider=provider, token=token[:16]):
                    self.fresh_agent(f"provider-number-{provider}-{index}")
                    path = self.agent / "models.json"
                    path.write_text('{"providers":{"personal":{"models":[]}},"nested":[{"n":'+token+'}]}\n')
                    path.chmod(0o640)
                    before = self.link_snapshot(self.agent)
                    result = self.run_provider_setup(provider)
                    self.assert_setup_failed(result)
                    self.assertEqual(result.stderr.count(str(path)), 1, result.stderr)
                    # No backup, credential update or staged file may precede the refusal.
                    self.assertEqual(self.link_snapshot(self.agent), before)

    # R4-2 break: a non-object providers member passes the preflight, so a backup or a
    # credential update happens before the setup crashes with a traceback.
    def test_r4_provider_setups_refuse_non_object_providers_before_changes(self):
        for provider in ("deepinfra", "opencode-go", "commandcode"):
            for index, value in enumerate(("[]", '"x"', "1", "null")):
                with self.subTest(provider=provider, providers=value):
                    self.fresh_agent(f"providers-shape-{provider}-{index}")
                    path = self.agent / "models.json"
                    path.write_text('{"providers":' + value + ',"custom":"keep"}\n')
                    path.chmod(0o640)
                    before = self.link_snapshot(self.agent)
                    result = self.run_provider_setup(provider)
                    self.assert_setup_failed(result)
                    self.assertEqual(result.stderr.count(str(path)), 1, result.stderr)
                    self.assertIn("'providers' must be an object", result.stderr)
                    self.assertNotIn("Traceback", result.stderr)
                    self.assertEqual(self.link_snapshot(self.agent), before)

    # R3-3 break: a permissive old auth mode is inherited by staged new plaintext credentials.
    def test_r3_opencode_auth_replacement_is_private_before_publish(self):
        injection = self.base / "auth-mode"
        injection.mkdir()
        (injection / "sitecustomize.py").write_text(
            'import os, stat\n_real_replace = os.replace\n'
            'def replace(src, dst):\n'
            '    if str(dst).endswith("auth.json"):\n'
            '        assert stat.S_IMODE(os.stat(src).st_mode) == 0o600, "auth staging not private"\n'
            '    return _real_replace(src, dst)\nos.replace = replace\n')
        path = self.agent / "auth.json"
        self.save(path, {"personal": {"type": "api_key", "key": "fixture"}})
        path.chmod(0o644)
        self.assert_success(self.run_provider_setup("opencode-go", PYTHONPATH=str(injection)))
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        self.assertEqual(json.loads(path.read_text())["personal"], {"type": "api_key", "key": "fixture"})
        self.assertEqual(list(self.agent.glob("auth.json.bak.*")), [])
        self.assertEqual(list(self.agent.glob(".auth.json.*")), [])

    # R3-3 break: OpenCode auth serialization loses escaped Unicode, accepts bad numbers, or backs up credentials.
    def test_r3_opencode_auth_strict_and_unicode_no_backup(self):
        path = self.agent / "auth.json"
        original = {"personal": {"type": "api_key", "key": "fixture-only", "\ud800": ["\udfff"]}}
        self.save(path, original)
        path.chmod(0o640)
        self.assert_success(self.run_provider_setup("opencode-go"))
        self.assertEqual(json.loads(path.read_text())["personal"], original["personal"])
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        self.assertEqual(list(self.agent.glob("auth.json.bak.*")), [])
        before = self.full_storage_snapshot()
        self.assert_success(self.run_provider_setup("opencode-go"))
        self.assertEqual(self.full_storage_snapshot(), before)
        for token in ("1e999", "1" + "0" * 309, "NaN"):
            with self.subTest(token=token[:16]):
                path.write_text('{"other":'+token+'}\n')
                before = self.full_storage_snapshot()
                result = self.run_provider_setup("opencode-go")
                self.assert_setup_failed(result)
                self.assertIn(str(path), result.stderr)
                self.assertEqual(self.full_storage_snapshot(), before)

    # R3-3 break: invalid source JSON reaches save, overwrites models, or reports success.
    def test_r3_provider_invalid_source_preserves_models(self):
        for provider, script in (("deepinfra", "setup_pi.zsh"), ("opencode-go", "setup_pi_opencode_go.zsh"),
                                 ("commandcode", "setup_pi_commandcode_goat.zsh")):
            for index, token in enumerate(("1e999", "1" + "0" * 309, "NaN", "{broken", "[]",
                                           '{"providers": []}')):
                with self.subTest(provider=provider, token=token[:16]):
                    self.fresh_agent(f"source-{provider}-{index}")
                    source_dir = self.base / f"source-{provider}-{index}"
                    source_dir.mkdir()
                    for name in (script, "pi_json.py", "pigo", "pigod", "pigou", "piccg", "piccd"):
                        source = ROOT / ".devcontainer" / name
                        if source.exists():
                            shutil.copy2(source, source_dir / name)
                    source = source_dir / "pi-models.json"
                    source_data = json.loads((ROOT / ".devcontainer/pi-models.json").read_text())
                    source_data["nested"] = "RAW_TOKEN"
                    source.write_text(token if token.startswith(("{", "[")) else
                                      json.dumps(source_data).replace('"RAW_TOKEN"', token))
                    path = self.agent / "models.json"
                    self.save(path, {"providers": {"personal": {"models": []}}})
                    before = self.link_snapshot(self.agent)
                    env = {**self.env, "DEEPINFRA_TOKEN": "offline-fixture", "OPENCODE_API_KEY": "offline-fixture"}
                    result = subprocess.run(["zsh", str(source_dir / script)], cwd=self.project,
                                            env=env, text=True, capture_output=True)
                    self.assert_setup_failed(result)
                    self.assertIn(str(source), result.stderr)
                    self.assertEqual(self.link_snapshot(self.agent), before)

    # R3-3 break: replacement errors overwrite live files or leave staged JSON on disk.
    def test_r3_provider_replace_failure_preserves_models_and_cleans_temp(self):
        injection = self.base / "write-failure"
        injection.mkdir()
        (injection / "sitecustomize.py").write_text(
            'import os\n_real_replace = os.replace\n'
            'def replace(src, dst):\n'
            '    if str(dst).endswith("models.json"):\n'
            '        raise PermissionError("fixture replace denied")\n'
            '    return _real_replace(src, dst)\nos.replace = replace\n')
        for provider in ("deepinfra", "opencode-go", "commandcode"):
            with self.subTest(provider=provider):
                self.fresh_agent(f"replace-failure-{provider}")
                path = self.agent / "models.json"
                self.save(path, {"providers": {"personal": {"models": []}}})
                path.chmod(0o640)
                original = path.read_bytes()
                result = self.run_provider_setup(provider, PYTHONPATH=str(injection))
                self.assert_setup_failed(result)
                self.assertIn("fixture replace denied", result.stderr)
                self.assertEqual(path.read_bytes(), original)
                self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o640)
                self.assertEqual(list(self.agent.glob(".*json*")), [])
                self.assertFalse((self.agent / "models.json.tmp").exists())

    # R3-5 break: shared backup reservation overwrites a generation or loses source bytes/mode.
    def test_r3_shared_backup_unique_original_bytes_and_modes(self):
        from datetime import datetime

        class FrozenClock:
            @classmethod
            def now(cls):
                return datetime(2026, 10, 4, 12, 34, 56)

        with patch("datetime.datetime", FrozenClock):
            namespace = runpy.run_path(str(ROOT / ".devcontainer/pi_json.py"))
        self.assertIn("backup_file", namespace, "shared backup helper is missing")
        backup_file = namespace["backup_file"]
        path = self.agent / "models.json"
        originals = (
            (b'\xef\xbb\xbf{"generation":1}\r\n', 0o640),
            (b'{"generation":2,"custom":"\\ud800"}\n', 0o600),
        )
        backups = []
        for original, mode in originals:
            path.write_bytes(original)
            path.chmod(mode)
            backup = backup_file(path)
            self.assertIsInstance(backup, Path)
            self.assertEqual(backup.parent, path.parent)
            self.assertTrue(backup.name.startswith("models.json.bak.20261004-123456."))
            self.assertNotIn(backup, backups)
            backups.append(backup)
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), mode)
            self.assertEqual(list(self.agent.glob(".models.json.*")), [])
        self.assertCountEqual(list(self.agent.glob("models.json.bak.*")), backups)
        self.assertEqual([(backup.read_bytes(), stat.S_IMODE(backup.stat().st_mode))
                          for backup in backups], list(originals))

    # R3-5 break: a copy error leaves the reserved or partially copied backup behind.
    def test_r3_shared_backup_copy_failure_cleans_reservation(self):
        namespace = runpy.run_path(str(ROOT / ".devcontainer/pi_json.py"))
        self.assertIn("backup_file", namespace, "shared backup helper is missing")
        backup_file = namespace["backup_file"]
        path = self.agent / "models.json"
        path.write_bytes(b'{"original":true}\r\n')
        path.chmod(0o640)
        previous = backup_file(path)
        before = self.full_storage_snapshot()

        # Keep copy2's metadata path real; only the failing file-copy boundary is injected.
        def fail_copy(source, destination, **kwargs):
            Path(destination).write_bytes(b"partial copy")
            raise PermissionError("fixture backup copy denied")

        with patch("shutil.copyfile", side_effect=fail_copy):
            with self.assertRaisesRegex(PermissionError, "fixture backup copy denied"):
                backup_file(path)
        self.assertEqual(self.full_storage_snapshot(), before)
        self.assertEqual(list(self.agent.glob("models.json.bak.*")), [previous])
        self.assertEqual(list(self.agent.glob(".models.json.*")), [])

    # R3-5 break: repeated setups in a frozen second overwrite the previous backup generation.
    def test_r3_provider_backup_generations_never_overwrite(self):
        clock = self.base / "clock"
        clock.mkdir()
        (clock / "sitecustomize.py").write_text(
            'import datetime\nclass Frozen(datetime.datetime):\n'
            '    @classmethod\n    def now(cls, tz=None):\n'
            '        return cls(2026, 10, 4, 12, 34, 56)\ndatetime.datetime = Frozen\n')
        date = self.bin / "date"
        date.write_text('#!/bin/sh\nprintf "20261004-123456\\n"\n')
        date.chmod(0o755)
        for provider in ("deepinfra", "opencode-go", "commandcode"):
            with self.subTest(provider=provider):
                self.fresh_agent(f"backup-generations-{provider}")
                path = self.agent / "models.json"
                originals = []
                for generation, mode in ((1, 0o640), (2, 0o600)):
                    self.save(path, {"providers": {"personal": {"models": []}}, "generation": generation})
                    path.chmod(mode)
                    originals.append((path.read_bytes(), mode))
                    self.assert_success(self.run_provider_setup(provider, PYTHONPATH=str(clock)))
                    backups = list(self.agent.glob("models.json.bak.*"))
                    self.assertEqual(len(backups), generation)
                    self.assertCountEqual([(item.read_bytes(), stat.S_IMODE(item.stat().st_mode))
                                           for item in backups], originals)
                if provider != "deepinfra":
                    before = self.full_storage_snapshot()
                    self.assert_success(self.run_provider_setup(provider, PYTHONPATH=str(clock)))
                    self.assertEqual(self.full_storage_snapshot(), before)

    # R3-6 break: related scripts write under cwd/~ instead of exact HOME tilde expansion.
    def test_r3_related_provider_exact_home_tilde_paths(self):
        for provider in ("opencode-go", "commandcode"):
            for index, override in enumerate(("~", "~/", "~/space path/agent", "absolute", None, "", "~other/agent")):
                with self.subTest(provider=provider, override=override):
                    home = self.base / f"path-{provider}-{index}"
                    cwd = self.base / f"cwd-{provider}-{index}"
                    home.mkdir()
                    cwd.mkdir()
                    if override == "absolute":
                        override = str(self.base / f"absolute {provider}")
                        target = Path(override)
                    elif override in ("~", "~/"):
                        target = home
                    elif override is None or override == "":
                        target = home / ".pi/agent"
                    elif override == "~other/agent":
                        target = cwd / "~other/agent"
                    else:
                        target = home / override[2:]
                    path = target / "models.json"
                    self.save(path, {"providers": {"personal": {"models": []}}, "custom": "keep"})
                    auth = target / "auth.json"
                    self.save(auth, {"personal": {"type": "api_key", "key": "fixture"}})
                    auth_original = auth.read_bytes()
                    self.project = cwd
                    self.env["HOME"] = str(home)
                    self.env.pop("PI_CODING_AGENT_DIR", None)
                    options = {} if override is None else {"PI_CODING_AGENT_DIR": override}
                    self.assert_success(self.run_provider_setup(provider, **options))
                    data = json.loads(path.read_text())
                    self.assertIn(provider, data["providers"])
                    self.assertEqual(data["providers"]["personal"], {"models": []})
                    self.assertEqual(data["custom"], "keep")
                    if provider == "opencode-go":
                        data = json.loads(auth.read_text())
                        self.assertEqual(data["personal"], {"type": "api_key", "key": "fixture"})
                        self.assertEqual(data["opencode-go"]["key"], "offline-fixture")
                        self.assertEqual(stat.S_IMODE(auth.stat().st_mode), 0o600)
                        self.assertEqual(list(target.glob("auth.json.bak.*")), [])
                    else:
                        self.assertEqual(auth.read_bytes(), auth_original)
                    self.assertFalse((cwd / "~").exists())

    # R4-1 break: the shared writer replaces a link or special file instead of refusing it.
    def test_r4_shared_writer_refuses_linked_or_special_destinations(self):
        write_object = runpy.run_path(str(ROOT / ".devcontainer/pi_json.py"))["write_object"]
        shared = self.base / "shared-writer"
        shared.mkdir()
        target = shared / "models.json"
        target.write_bytes(b'{"shared":true}\r\n')
        target.chmod(0o644)
        for kind in ("symlink", "dangling", "hardlink", "fifo", "directory"):
            with self.subTest(kind=kind):
                path = self.agent / f"{kind}.json"
                if kind == "symlink":
                    path.symlink_to(target)
                elif kind == "dangling":
                    path.symlink_to(shared / "absent.json")
                elif kind == "hardlink":
                    os.link(target, path)
                elif kind == "fifo":
                    os.mkfifo(path)
                else:
                    path.mkdir()
                before = self.link_snapshot(self.agent, shared)
                with patch("tempfile.mkstemp", side_effect=AssertionError("staged before refusing")):
                    with self.assertRaisesRegex(ValueError, re.escape(str(path))):
                        write_object(path, {"new": True})
                self.assertEqual(self.link_snapshot(self.agent, shared), before)

    # R4-1 break: a provider setup detaches a linked models/auth file, writes or chmods its
    # shared target, or changes another file before refusing the linked destination.
    def test_r4_provider_setups_refuse_linked_destinations_before_changes(self):
        managed = {"deepinfra": ("models.json",), "opencode-go": ("auth.json", "models.json"),
                   "commandcode": ("models.json",)}
        seeds = {"models.json": {"providers": {"personal": {"models": []}}},
                 "auth.json": {"personal": {"type": "api_key", "key": "fixture"}}}
        for provider, names in managed.items():
            for name in names:
                for kind in ("symlink", "dangling", "hardlink"):
                    with self.subTest(provider=provider, name=name, kind=kind):
                        self.fresh_agent(f"linked-{provider}-{name}-{kind}")
                        shared = self.base / f"shared-{provider}-{name}-{kind}"
                        shared.mkdir()
                        for seed, data in seeds.items():
                            self.save(self.agent / seed, data)
                            (self.agent / seed).chmod(0o640)
                        path = self.agent / name
                        path.unlink()
                        target = shared / name
                        if kind != "dangling":
                            self.save(target, seeds[name])
                            target.chmod(0o644)
                        if kind == "hardlink":
                            os.link(target, path)
                        else:
                            path.symlink_to(target)
                        before = self.link_snapshot(self.agent, shared)
                        result = self.run_provider_setup(provider)
                        self.assert_setup_failed(result)
                        self.assertIn(str(path), result.stderr)
                        self.assertIn("Refusing hard-linked storage" if kind == "hardlink"
                                      else "Refusing symlinked storage", result.stderr)
                        self.assertEqual(self.link_snapshot(self.agent, shared), before)

    # R4-1 control: only the managed files are checked; a linked agent directory still works.
    def test_r4_provider_setups_accept_symlinked_agent_directory(self):
        for provider in ("deepinfra", "opencode-go", "commandcode"):
            with self.subTest(provider=provider):
                real = self.base / f"real-agent-{provider}"
                link = self.home / f"linked-agent-{provider}"
                self.save(real / "models.json", {"providers": {"personal": {"models": []}}})
                link.symlink_to(real, target_is_directory=True)
                self.env["PI_CODING_AGENT_DIR"] = str(link)
                self.assert_success(self.run_provider_setup(provider))
                self.assertTrue(link.is_symlink())
                data = json.loads((real / "models.json").read_text())
                self.assertIn(provider, data["providers"])
                self.assertEqual(data["providers"]["personal"], {"models": []})

    # Break caught: -builtin:mcp surviving migration or unrelated extension entries being lost.
    def test_builtin_disable_filter_preserves_other_settings_and_mode(self):
        settings = {"packages": KEPT, "extensions": ["./custom", "-builtin:mcp", "+builtin:mcp",
                                                     "-builtin:mcp", "-builtin:other"],
                    "custom": {"keep": True}}
        self.save(self.agent / "settings.json", settings)
        path = self.agent / "settings.json"
        path.write_bytes(b"\xef\xbb\xbf" + path.read_bytes())
        path.chmod(0o640)
        original = path.read_bytes()
        self.assert_success(self.run_cleanup())
        settings["extensions"] = ["./custom", "+builtin:mcp", "-builtin:other"]
        self.assertEqual(json.loads(path.read_text()), settings)
        self.assertEqual(path.stat().st_mode & 0o777, 0o640)
        backups = list((self.agent / "migration-backups").glob("pi-retired-*"))
        self.assertEqual(len(backups), 1)
        self.assertEqual((backups[0] / "settings.json").read_bytes(), original)
        snapshot = self.storage_snapshot()
        self.assert_success(self.run_cleanup(FAKE_PI_REMOVE="fail"))
        self.assertEqual(self.storage_snapshot(), snapshot)

    # Break caught: malformed extensions being discovered only after destructive package removal.
    def test_invalid_extensions_stop_before_removal(self):
        for extensions in (None, {}, "-builtin:mcp"):
            with self.subTest(extensions=extensions):
                self.seed_packages()
                path = self.agent / "settings.json"
                settings = json.loads(path.read_text())
                settings["extensions"] = extensions
                self.save(path, settings)
                before = self.storage_snapshot()
                calls = self.base / "calls"
                result = self.run_cleanup(FAKE_PI_CALL_LOG=str(calls))
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("extensions", result.stderr)
                self.assertFalse(calls.exists())
                self.assertEqual(before, self.storage_snapshot())

    # Break caught: overwriting snapshots or backing up settings after pi already rewrites them.
    def test_backups_preserve_all_original_manifests_and_are_unique(self):
        self.seed_packages()
        for relative in ("npm/npm-shrinkwrap.json", "npm/node_modules/.package-lock.json"):
            self.save(self.agent / relative, {"dependencies": {name: "1.0" for name in REMOVED}})
        # npm ignores this lock under shrinkwrap; it must not contain retired packages.
        self.save(self.agent / "npm/package-lock.json", {"custom": "preserve shadowed lock bytes"})
        paths = ("settings.json", "npm/package.json", "npm/package-lock.json",
                 "npm/npm-shrinkwrap.json", "npm/node_modules/.package-lock.json")
        original = {name: (self.agent / name).read_bytes() for name in paths}
        self.assert_success(self.run_cleanup())
        backups = list((self.agent / "migration-backups").glob("pi-retired-*"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].stat().st_mode & 0o777, 0o700)
        for name, data in original.items():
            self.assertEqual((backups[0] / name).read_bytes(), data)
        self.seed_packages()
        self.save(self.agent / "npm/package-lock.json", {"custom": "preserve shadowed lock bytes"})
        self.assert_success(self.run_cleanup())
        self.assertEqual(len(list((self.agent / "migration-backups").glob("pi-retired-*"))), 2)
        for name, data in original.items():
            self.assertEqual((backups[0] / name).read_bytes(), data)

    # Break caught: failing package removal losing recoverable input or editing MCP filters anyway.
    def test_failed_removal_keeps_backup_and_builtin_disable(self):
        self.seed_packages()
        path = self.agent / "settings.json"
        settings = json.loads(path.read_text())
        settings["extensions"] = ["-builtin:mcp", "./custom"]
        self.save(path, settings)
        original = path.read_bytes()
        result = self.run_cleanup(FAKE_PI_REMOVE="fail-after-clean")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("-builtin:mcp", json.loads(path.read_text())["extensions"])
        backups = list((self.agent / "migration-backups").glob("pi-retired-*"))
        self.assertEqual(len(backups), 1)
        self.assertEqual((backups[0] / "settings.json").read_bytes(), original)
        self.assertIn(str(backups[0]), result.stdout)

    # Break caught: linked backup destinations permitting copies outside the agent directory.
    def test_unsafe_backup_storage_stops_before_mutation(self):
        self.seed_packages()
        target = self.base / "shared-backups"
        target.mkdir()
        (self.agent / "migration-backups").symlink_to(target, target_is_directory=True)
        before = self.storage_snapshot()
        calls = self.base / "calls"
        result = self.run_cleanup(FAKE_PI_CALL_LOG=str(calls))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("symlink", result.stderr.lower())
        self.assertFalse(calls.exists())
        self.assertEqual(list(target.iterdir()), [])
        self.assertEqual(before, self.storage_snapshot())

    # Break caught: settings-only/pinned/helper-only residues escaping the generic remover.
    def test_each_retired_package_is_removed_in_all_declaration_forms(self):
        for name in REMOVED:
            for entry in ("npm:" + name, "npm:" + name + "@1.0", {"source": "npm:" + name + "@1.0", "extensions": []}):
                with self.subTest(name=name, entry=entry):
                    self.seed_packages(entries=KEPT + [entry], manifests=False, installed=False)
                    self.assert_success(self.run_cleanup())
                    self.assertEqual(json.loads((self.agent / "settings.json").read_text())["packages"], KEPT)

    # Break caught: untrimmed npm payloads escaping removal and reappearing on offline update.
    def test_whitespace_retired_sources_are_removed_without_resurrection(self):
        whitespace = (
            "\ufeff\u0009\u000a\u000b\u000c\u000d \u00a0\u1680\u2000\u2001\u2002\u2003"
            "\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u2028\u2029\u202f\u205f\u3000\ufeff"
        )
        # Similar names and whitespace that JS does not trim are not retired identities.
        kept = KEPT + ["npm:pi-distill-extra", {"source": "npm:@upstash/context7-pi-extra@1.0"},
                       "npm:\u0085pi-distill\u0085", "npm:\u001cpi-distill\u001c"]
        for form in ("string", "pinned", "object"):
            for leading, trailing in ((whitespace, ""), ("", whitespace), (whitespace, whitespace)):
                with self.subTest(form=form, leading=bool(leading), trailing=bool(trailing)):
                    entries = []
                    for name in REMOVED:
                        source = "npm:" + leading + name + ("@1.0.0" if form != "string" else "") + trailing
                        entries.append({"source": source, "extensions": []} if form == "object" else source)
                    # No manifest or installed package may hide missed settings-only declarations.
                    self.seed_packages(entries=kept + entries, manifests=False, installed=False)
                    self.assert_success(self.run_cleanup())
                    self.assertEqual(json.loads((self.agent / "settings.json").read_text())["packages"], kept)
                    result = subprocess.run(["pi", "update", "--extensions"], env=self.env,
                                            cwd=self.project, text=True, capture_output=True)
                    self.assert_success(result)
                    for name in REMOVED:
                        self.assertFalse((self.agent / "npm/node_modules" / name).exists(), name)
                    # The update double creates an npm prefix; reset it for the next settings-only case.
                    shutil.rmtree(self.agent / "npm")
        # Retained manifest safety checks must normalize whitespace too, not reject valid retained npm names.
        kept = KEPT + [{"source": "npm: \ufeff@keep/tool@1.0.0\ufeff "}]
        self.seed_packages(entries=kept + ["npm: \ufeffpi-distill@1.0.0\ufeff "], installed=False)
        manifest = self.agent / "npm/package.json"
        data = json.loads(manifest.read_text())
        data["dependencies"]["@keep/tool"] = "1.0.0"
        self.save(manifest, data)
        self.assert_success(self.run_cleanup())
        self.assertEqual(json.loads((self.agent / "settings.json").read_text())["packages"], kept)

    # Break caught: Python-only JSON constants being accepted before package/settings/cache mutation.
    def test_nonstandard_json_constants_stop_before_mutation(self):
        paths = ("settings.json", "npm/package.json", "npm/package-lock.json",
                 "npm/npm-shrinkwrap.json", "npm/node_modules/.package-lock.json")
        for index, relative in enumerate(paths):
            for constant in ("NaN", "Infinity", "-Infinity"):
                with self.subTest(relative=relative, constant=constant):
                    self.agent = self.home / f"constant-{index}-{constant}"
                    self.agent.mkdir()
                    self.env["PI_CODING_AGENT_DIR"] = str(self.agent)
                    self.seed_packages()
                    for name in paths[3:]:
                        self.save(self.agent / name, {"dependencies": {"pi-distill": "1.0.0"}})
                    settings = json.loads((self.agent / "settings.json").read_text())
                    settings["extensions"] = ["-builtin:mcp", "./custom"]
                    self.save(self.agent / "settings.json", settings)
                    for name in (*MCP_FILES, *BUILTIN_MCP_FILES, "auth.json", "models.json"):
                        (self.agent / name).write_bytes(b"preserve original state\r\n")
                    path = self.agent / relative
                    data = json.loads(path.read_text())
                    data["custom"] = "CONSTANT"
                    path.write_text(json.dumps(data).replace('"CONSTANT"', constant) + "\n")
                    before = self.storage_snapshot()
                    calls = self.base / f"calls-{index}-{constant}"
                    result = self.run_cleanup(FAKE_PI_CALL_LOG=str(calls))
                    self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertIn(str(path), result.stderr)
                    self.assertIn("invalid json constant", result.stderr.lower())
                    self.assertFalse(calls.exists(), "pi ran before strict JSON preflight")
                    self.assertEqual(self.storage_snapshot(), before)
                    self.assertFalse((self.agent / "migration-backups").exists())

    # Break caught: leaving declarations that reinstall retired extensions on the next update.
    def test_extension_update_does_not_resurrect_retired_packages(self):
        self.seed_packages()
        self.assert_success(self.run_cleanup())
        result = subprocess.run(["pi", "update", "--extensions"], env=self.env,
                                cwd=self.project, text=True, capture_output=True)
        self.assert_success(result)
        self.assert_packages_clean()
        self.assertTrue((self.agent / "npm/node_modules/keep-extension/package.json").is_file())

    # Break caught: npm pruning only registered distill but leaving its transitive helper packages.
    @unittest.skipUnless(shutil.which("npm"), "real npm is required for dependency regression")
    def test_real_npm_distill_transitive_helpers_are_removed(self):
        self.use_real_npm()
        dependencies = {"keep-extension": "1.0.0", "pi-distill": "1.0.0"}
        helpers = {"pi-extensions-tool-display": "1.0.0", "pi-extensions-i18n": "1.0.0"}
        self.save(self.agent / "settings.json", {"packages": ["npm:keep-extension"]})
        self.save(self.agent / "npm/package.json", {"dependencies": dependencies})
        packages = {"": {"dependencies": dependencies}}
        for name in (*dependencies, *helpers):
            data = {"name": name, "version": "1.0.0"}
            if name == "pi-distill":
                data["dependencies"] = helpers
            self.save(self.agent / "npm/node_modules" / name / "package.json", data)
            packages["node_modules/" + name] = {key: value for key, value in data.items() if key != "name"}
        self.save(self.agent / "npm/package-lock.json", {"lockfileVersion": 3, "packages": packages})
        self.save(self.agent / "npm/node_modules/.package-lock.json", {"lockfileVersion": 3, "packages": packages})
        self.assert_success(self.run_cleanup())
        for name in ("pi-distill", *helpers):
            self.assertFalse((self.agent / "npm/node_modules" / name).exists())
        self.assertTrue((self.agent / "npm/node_modules/keep-extension/package.json").is_file())

    # Real npm must remain real: its uninstall prunes the entire prefix, unlike the pi double.
    def use_real_npm(self):
        (self.bin / "pi").unlink()
        (self.bin / "pi").write_text(
            '#!/bin/sh\n'
            'npm uninstall "${2#npm:}" --prefix "$PI_CODING_AGENT_DIR/npm" --legacy-peer-deps\n'
            'code=$?\n'
            '[ "$code" -eq 0 ] || exit "$code"\n'
            'printf "No matching package found for %s\\n" "$2" >&2\n'
            'exit 1\n'
        )
        (self.bin / "pi").chmod(0o755)
        for key in list(self.env):
            if key.lower().startswith("npm_config_"):
                del self.env[key]
        self.env.update({
            "npm_config_cache": str(self.base / "npm-cache"),
            "npm_config_userconfig": str(self.base / "npmrc"),
            "npm_config_globalconfig": str(self.base / "global-npmrc"),
            "npm_config_offline": "true", "npm_config_ignore_scripts": "true",
            "npm_config_audit": "false", "npm_config_fund": "false",
            "npm_config_update_notifier": "false",
        })

    def seed_real_npm(self, fixture, dependencies):
        self.agent = self.home / fixture
        self.agent.mkdir()
        self.env["PI_CODING_AGENT_DIR"] = str(self.agent)
        self.save(self.agent / "settings.json", {"packages": ["npm:keep-extension"]})
        for name in ("pi-mcp-adapter", "keep-extension"):
            self.save(self.agent / "npm/node_modules" / name / "package.json",
                      {"name": name, "version": "1.0.0"})
        (self.agent / "npm/node_modules/keep-extension/extension.js").write_bytes(b"keep extension bytes\r\n")
        (self.agent / "mcp-cache.json").write_text("old state")
        if dependencies is not None:
            self.save(self.agent / "npm/package.json", {"dependencies": dependencies})
            self.save(self.agent / "npm/package-lock.json", {"lockfileVersion": 3, "packages": {
                "": {"dependencies": dependencies},
                **{"node_modules/" + name: {"version": "1.0.0"} for name in dependencies},
            }})

    # Break caught: inherited npm omit policies pruning declared retained dev/optional extensions.
    @unittest.skipUnless(shutil.which("npm"), "real npm is required for omit regression")
    def test_real_npm_omit_preserves_retained_dependency_types(self):
        self.use_real_npm()
        self.env.pop("NODE_ENV", None)
        cases = (("production", {"NODE_ENV": "production"}),
                 ("env-omit", {"npm_config_omit": "dev\n\noptional"}),
                 ("prefix-omit", {}))
        for fixture, overrides in cases:
            with self.subTest(fixture=fixture):
                self.seed_real_npm(fixture, {"pi-mcp-adapter": "1.0.0"})
                self.save(self.agent / "settings.json", {"packages": KEPT, "custom": "keep"})
                sections = {"dependencies": {"pi-mcp-adapter": "1.0.0"},
                            "devDependencies": {"keep-extension": "1.0.0"},
                            "optionalDependencies": {"other": "1.0.0"}}
                self.save(self.agent / "npm/package.json", sections)
                self.save(self.agent / "npm/node_modules/other/package.json", {"name": "other", "version": "1.0.0"})
                (self.agent / "npm/node_modules/other/extension.js").write_bytes(b"optional extension bytes\r\n")
                packages = {"": sections, "node_modules/pi-mcp-adapter": {"version": "1.0.0"},
                            "node_modules/keep-extension": {"version": "1.0.0", "dev": True},
                            "node_modules/other": {"version": "1.0.0", "optional": True}}
                for relative in ("npm/package-lock.json", "npm/node_modules/.package-lock.json"):
                    self.save(self.agent / relative, {"lockfileVersion": 3, "packages": packages})
                npmrc = self.agent / "npm/.npmrc"
                if fixture == "prefix-omit":
                    npmrc.write_bytes(b"omit[]=dev\nomit[]=optional\n")
                settings_before = (self.agent / "settings.json").read_bytes()
                retained = {path.relative_to(self.agent): path.read_bytes()
                            for name in ("keep-extension", "other")
                            for path in (self.agent / "npm/node_modules" / name).rglob("*") if path.is_file()}
                self.assert_success(self.run_cleanup(**overrides))
                for relative, original in retained.items():
                    path = self.agent / relative
                    self.assertTrue(path.is_file(), str(relative))
                    self.assertEqual(path.read_bytes(), original, str(relative))
                manifest = json.loads((self.agent / "npm/package.json").read_text())
                for section in ("devDependencies", "optionalDependencies"):
                    self.assertEqual(manifest[section], sections[section])
                self.assertNotIn("pi-mcp-adapter", manifest.get("dependencies", {}))
                for relative in ("npm/package-lock.json", "npm/node_modules/.package-lock.json"):
                    self.assertNotIn("pi-mcp-adapter", (self.agent / relative).read_text())
                self.assertFalse((self.agent / "npm/node_modules/pi-mcp-adapter").exists())
                self.assertEqual((self.agent / "settings.json").read_bytes(), settings_before)
                if fixture == "prefix-omit":
                    self.assertEqual(npmrc.read_bytes(), b"omit[]=dev\nomit[]=optional\n")
                self.assertFalse((self.agent / "mcp-cache.json").exists())

    # Break caught: cleanup invoked too late, omitted, or either removed package reinstalled.
    def test_provisioning_cleans_before_installing_only_retained_extensions(self):
        self.seed_packages()
        for name in MCP_FILES:
            (self.agent / name).write_text("old pi-only state")
        for name in BUILTIN_MCP_FILES:
            (self.agent / name).write_bytes(b"preserve builtin MCP state\r\n")
        result = self.run_provisioning(FAKE_PI_REQUIRE_CLEAN="1")
        for name in MCP_FILES:
            self.assertFalse((self.agent / name).exists(), name)
        self.assert_success(result)
        for name in BUILTIN_MCP_FILES:
            self.assertTrue((self.agent / name).is_file(), name)
            self.assertEqual((self.agent / name).read_bytes(), b"preserve builtin MCP state\r\n")
        settings = json.loads((self.agent / "settings.json").read_text())
        sources = [entry if isinstance(entry, str) else entry["source"] for entry in settings["packages"]]
        self.assertEqual(sources, [
            "npm:keep-extension", "npm:other@1.0", "npm:@teelicht/pi-superagents",
            "npm:@jc4649/notify", "npm:pi-safe-search", "npm:pi-diet-ripgrep",
            "git:github.com/obra/superpowers", "npm:pi-lens", "npm:pi-simplify",
            "npm:@howaboua/pi-skill-skill-creator",
        ])
        self.assert_success(self.run_provisioning(FAKE_PI_REQUIRE_CLEAN="1"))
        self.assertEqual(json.loads((self.agent / "settings.json").read_text()), settings)
        result = subprocess.run(["pi", "update", "--extensions"], cwd=self.project,
                                env=self.env, text=True, capture_output=True)
        self.assert_success(result)
        for name in REMOVED:
            self.assertFalse((self.agent / "npm/node_modules" / name).exists(), name)

    # Break caught: retiring existing installations but reinstalling distill on a clean postCreate.
    def test_fresh_provisioning_and_rerun_install_only_retained_extensions(self):
        for _ in range(2):
            self.assert_success(self.run_provisioning(FAKE_PI_REQUIRE_CLEAN="1"))
            settings = json.loads((self.agent / "settings.json").read_text())
            self.assertEqual(settings["packages"], [
                "npm:@teelicht/pi-superagents", "npm:@jc4649/notify", "npm:pi-safe-search",
                "npm:pi-diet-ripgrep", "git:github.com/obra/superpowers", "npm:pi-lens",
                "npm:pi-simplify", "npm:@howaboua/pi-skill-skill-creator",
            ])
        self.assertFalse((self.agent / "migration-backups").exists())

    # Break caught: missing project builtin MCP settings or a broken shared .pi link in world cwd.
    def test_project_builtin_mcp_settings_are_shared_with_worlds(self):
        for cwd in (ROOT, *(ROOT / name for name in ("MyResoniteProject", "akichi", "slum02", "slum03"))):
            with self.subTest(cwd=cwd):
                path = cwd / ".pi/settings.json"
                self.assertTrue(path.is_file(), str(path))
                settings = json.loads(path.read_text())
                self.assertEqual(settings, {"extensions": ["+builtin:mcp"]})
                mcp = json.loads((cwd / ".pi/mcp.json").read_text())
                self.assertEqual(mcp, {"mcpServers": {"google-dev-knowledge": {
                    "type": "http", "url": "https://developerknowledge.googleapis.com/mcp",
                    "headers": {"X-Goog-Api-Key": "${GOOGLE_DEV_KNOWLEDGE_API_KEY}"},
                }}})

    # Break caught: setup reintroducing the retired provider or deleting a user's custom models.
    def test_deepinfra_setup_does_not_reintroduce_distill_and_preserves_custom_models(self):
        for existing in (False, True):
            with self.subTest(existing=existing):
                path = self.agent / "models.json"
                custom = {"models": [{"id": "personal-model"}]}
                if existing:
                    self.save(path, {"providers": {"deepinfra-distill": custom, "personal": custom}})
                result = subprocess.run(["zsh", str(ROOT / ".devcontainer/setup_pi.zsh")],
                                        env={**self.env, "DEEPINFRA_TOKEN": "offline-fixture"},
                                        text=True, capture_output=True)
                self.assert_success(result)
                models = json.loads(path.read_text())["providers"]
                self.assertIn("deepinfra", models)
                self.assertNotIn("deepinfra-distill", json.loads((ROOT / ".devcontainer/pi-models.json").read_text())["providers"])
                if existing:
                    self.assertEqual(models["deepinfra-distill"], custom)
                    self.assertEqual(models["personal"], custom)
                else:
                    self.assertNotIn("deepinfra-distill", models)

    # Break caught: setup reporting success after the model synchronization rejects broken JSON.
    def test_setup_invalid_models_json_fails_without_success_banner(self):
        path = self.agent / "models.json"
        path.write_bytes(b"{broken models\r\n")
        original = path.read_bytes()
        result = subprocess.run(["zsh", str(ROOT / ".devcontainer/setup_pi.zsh")], cwd=self.project,
                                env={**self.env, "DEEPINFRA_TOKEN": "offline-fixture"},
                                text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Invalid JSON", result.stderr)
        self.assertNotIn("JSON validation: OK", result.stdout)
        self.assertNotIn("Setup complete", result.stdout)
        self.assertEqual(path.read_bytes(), original)
        self.assertEqual(list(self.agent.glob("models.json.bak.*")), [])

    # Break caught: a failed backup being ignored and the user's original model bytes overwritten.
    def test_setup_backup_failure_preserves_original_models(self):
        path = self.agent / "models.json"
        self.save(path, {"providers": {"deepinfra": {"models": []}, "personal": {"models": []}}})
        original = path.read_bytes()
        cp = self.bin / "cp"
        cp.write_text('#!/bin/sh\nprintf "backup fixture failure\\n" >&2\nexit 73\n')
        cp.chmod(0o755)
        result = subprocess.run(["zsh", str(ROOT / ".devcontainer/setup_pi.zsh")], cwd=self.project,
                                env={**self.env, "DEEPINFRA_TOKEN": "offline-fixture"},
                                text=True, capture_output=True)
        self.assertEqual(result.returncode, 73, result.stdout + result.stderr)
        self.assertNotIn("JSON validation: OK", result.stdout)
        self.assertNotIn("Setup complete", result.stdout)
        self.assertEqual(path.read_bytes(), original)
        self.assertEqual(list(self.agent.glob("models.json.bak.*")), [])

    # Break caught: failed parent directory creation falling through to setup's success banners.
    def test_setup_blocked_parent_mkdir_fails_without_success_banner(self):
        parent = self.base / "blocked-parent"
        parent.write_bytes(b"not a directory\r\n")
        target = parent / "agent"
        result = subprocess.run(["zsh", str(ROOT / ".devcontainer/setup_pi.zsh")], cwd=self.project,
                                env={**self.env, "DEEPINFRA_TOKEN": "offline-fixture",
                                     "PI_CODING_AGENT_DIR": str(target)}, text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("JSON validation: OK", result.stdout)
        self.assertNotIn("Setup complete", result.stdout)
        self.assertEqual(parent.read_bytes(), b"not a directory\r\n")
        self.assertFalse(target.exists())

    # Break caught: real Python model write errors being ignored by the surrounding zsh script.
    def test_setup_python_write_failure_fails_without_success_banner(self):
        if os.geteuid() == 0:
            self.skipTest("root bypasses directory permission bits")
        self.agent.chmod(0o500)
        try:
            result = subprocess.run(["zsh", str(ROOT / ".devcontainer/setup_pi.zsh")], cwd=self.project,
                                    env={**self.env, "DEEPINFRA_TOKEN": "offline-fixture"},
                                    text=True, capture_output=True)
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("PermissionError", result.stderr)
            self.assertNotIn("JSON validation: OK", result.stdout)
            self.assertNotIn("Setup complete", result.stdout)
            self.assertFalse((self.agent / "models.json").exists())
        finally:
            self.agent.chmod(0o700)

    # Break caught: validator failure printing a successful JSON validation and setup result anyway.
    def test_setup_python_validation_failure_fails_without_success_banner(self):
        python = self.bin / "python3"
        python.write_text('#!/bin/sh\nif [ "$1" = "-m" ]; then exit 74; fi\n'
                          + f'exec "{sys.executable}" "$@"\n')
        python.chmod(0o755)
        result = subprocess.run(["zsh", str(ROOT / ".devcontainer/setup_pi.zsh")], cwd=self.project,
                                env={**self.env, "DEEPINFRA_TOKEN": "offline-fixture"},
                                text=True, capture_output=True)
        self.assertEqual(result.returncode, 74, result.stdout + result.stderr)
        self.assertIn("deepinfra", json.loads((self.agent / "models.json").read_text())["providers"])
        self.assertNotIn("JSON validation: OK", result.stdout)
        self.assertNotIn("Setup complete", result.stdout)

    # Break caught: literal ~/cwd output instead of HOME expansion, or expansion of ~other/eval input.
    def test_setup_agent_paths_expand_only_leading_home_tilde(self):
        cases = ("~", "~/", "~/.pi-custom/agent", "~/space path/agent", "absolute", None, "", "~other/agent")
        for index, override in enumerate(cases):
            with self.subTest(override=override):
                home = self.base / f"path-home-{index}"
                cwd = self.project / f"path-cwd-{index}"
                home.mkdir()
                cwd.mkdir()
                if override == "absolute":
                    override = str(self.base / "absolute agent")
                    target = Path(override)
                elif override in ("~", "~/"):
                    target = home
                elif override is None or override == "":
                    target = home / ".pi/agent"
                elif override == "~other/agent":
                    target = cwd / "~other/agent"
                else:
                    target = home / override[2:]
                path = target / "models.json"
                custom = {"models": [{"id": "personal-model"}]}
                self.save(path, {"providers": {"personal": custom}, "customSetting": "keep"})
                original = path.read_bytes()
                env = {**self.env, "HOME": str(home), "DEEPINFRA_TOKEN": "offline-fixture"}
                if override is None:
                    env.pop("PI_CODING_AGENT_DIR", None)
                else:
                    env["PI_CODING_AGENT_DIR"] = override
                result = subprocess.run(["zsh", str(ROOT / ".devcontainer/setup_pi.zsh")], cwd=cwd,
                                        env=env, text=True, capture_output=True)
                self.assert_success(result)
                data = json.loads(path.read_text())
                self.assertIn("deepinfra", data["providers"])
                self.assertEqual(data["providers"]["personal"], custom)
                self.assertEqual(data["customSetting"], "keep")
                backups = list(target.glob("models.json.bak.*"))
                self.assertEqual(len(backups), 1)
                self.assertEqual(backups[0].read_bytes(), original)
                self.assertFalse((cwd / "~").exists())

    # Break caught: attempting removal/creating settings on a fresh installation.
    def test_fresh_environment_stays_empty(self):
        self.agent.rmdir()
        self.assert_success(self.run_cleanup())
        self.assertFalse(self.agent.exists())

    # Break caught: rejecting or rewriting BOM-prefixed settings when no packages need removal.
    def test_bom_settings_without_retired_packages_keep_original_bytes(self):
        self.seed_packages(entries=KEPT, manifests=False, installed=False)
        settings_path = self.agent / "settings.json"
        settings_bytes = b"\xef\xbb\xbf" + settings_path.read_bytes()
        settings_path.write_bytes(settings_bytes)
        for name in MCP_FILES:
            (self.agent / name).write_text("old pi-only state")
        for name in BUILTIN_MCP_FILES:
            (self.agent / name).write_bytes(b"keep native MCP bytes\r\n")
        self.assert_success(self.run_cleanup(FAKE_PI_REMOVE="fail"))
        self.assertEqual(settings_path.read_bytes(), settings_bytes)
        for name in MCP_FILES:
            self.assertFalse(os.path.lexists(self.agent / name), name)
        for name in BUILTIN_MCP_FILES:
            self.assertEqual((self.agent / name).read_bytes(), b"keep native MCP bytes\r\n")
        before = self.storage_snapshot()
        self.assert_success(self.run_cleanup(FAKE_PI_REMOVE="fail"))
        self.assertEqual(self.storage_snapshot(), before)

    # Break caught: BOM-prefixed settings preventing removal of retired package registrations.
    def test_bom_settings_with_retired_packages_are_cleaned(self):
        self.seed_packages(entries=KEPT + ["npm:pi-mcp-adapter@2.1.0", {
            "source": "npm:@upstash/context7-pi@1.1.0", "extensions": [],
        }])
        settings_path = self.agent / "settings.json"
        expected = json.loads(settings_path.read_text())
        expected["packages"] = KEPT
        settings_path.write_bytes(b"\xef\xbb\xbf" + settings_path.read_bytes())
        for name in MCP_FILES:
            (self.agent / name).write_text("old pi-only state")
        for name in BUILTIN_MCP_FILES:
            (self.agent / name).write_bytes(b"keep native MCP bytes\r\n")
        self.assert_success(self.run_cleanup())
        self.assert_packages_clean()
        self.assertEqual(json.loads(settings_path.read_text(encoding="utf-8-sig")), expected)
        for name in MCP_FILES:
            self.assertFalse(os.path.lexists(self.agent / name), name)
        for name in BUILTIN_MCP_FILES:
            self.assertEqual((self.agent / name).read_bytes(), b"keep native MCP bytes\r\n")
        before = self.storage_snapshot()
        self.assert_success(self.run_cleanup(FAKE_PI_REMOVE="fail"))
        self.assertEqual(self.storage_snapshot(), before)

    # Break caught: unlinking native MCP config/auth, even when retired packages never existed.
    def test_builtin_mcp_files_survive_initial_cleanup_and_rerun(self):
        for retired in (False, True):
            with self.subTest(retired=retired):
                if retired:
                    self.seed_packages()
                else:
                    self.save(self.agent / "settings.json", {"packages": [], "extensions": ["+builtin:mcp"]})
                for name in BUILTIN_MCP_FILES:
                    (self.agent / name).write_bytes(b'{"personal":"preserve"}\r\n')
                self.assert_success(self.run_cleanup())
                for name in BUILTIN_MCP_FILES:
                    self.assertTrue((self.agent / name).is_file(), name)
                    self.assertEqual((self.agent / name).read_bytes(), b'{"personal":"preserve"}\r\n')
                # A native server added after migration must survive the next postCreate too.
                for name in BUILTIN_MCP_FILES:
                    (self.agent / name).write_bytes(b'{"new-server":"preserve"}\r\n')
                self.assert_success(self.run_cleanup(FAKE_PI_REMOVE="fail"))
                for name in BUILTIN_MCP_FILES:
                    self.assertTrue((self.agent / name).is_file(), name)
                    self.assertEqual((self.agent / name).read_bytes(), b'{"new-server":"preserve"}\r\n')

    # Break caught: removing native MCP links, including dangling links, or their targets.
    def test_builtin_mcp_symlinks_are_untouched(self):
        target = self.project / "native-config.json"
        target.write_bytes(b"preserve linked native state\r\n")
        for name in BUILTIN_MCP_FILES:
            for destination in (target, self.base / "absent-target"):
                with self.subTest(name=name, dangling=not destination.exists()):
                    path = self.agent / name
                    path.symlink_to(destination)
                    self.assert_success(self.run_cleanup())
                    self.assertTrue(path.is_symlink(), name)
                    self.assertEqual(path.readlink(), destination)
                    self.assertEqual(target.read_bytes(), b"preserve linked native state\r\n")
                    path.unlink()

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
        self.assertTrue((self.agent / "npm/node_modules/keep-extension").is_dir())
        for name in ("auth.json", "models.json", "extensions/other/config.json", "mcp-unrelated.json"):
            self.assertEqual((self.agent / name).read_bytes(), b"keep these bytes\r\n")

    # Break caught: treating an undeclared pi remove result as failure or relying on pi list only.
    def test_manifest_only_packages_are_removed(self):
        self.seed_packages(entries=KEPT, installed=False)
        self.assert_success(self.run_cleanup())
        self.assert_packages_clean()

    # Break caught: requiring a manifest when pi will only remove settings registrations.
    def test_registered_packages_without_npm_prefix_are_removed(self):
        for removed in (["npm:" + name for name in REMOVED], [
            "npm:pi-mcp-adapter@2.1.0",
            {"source": "npm:@upstash/context7-pi@1.1.0", "extensions": []},
        ]):
            with self.subTest(removed=removed):
                self.seed_packages(entries=KEPT + removed, manifests=False, installed=False)
                expected = json.loads((self.agent / "settings.json").read_text())
                expected["packages"] = KEPT
                for name in MCP_FILES:
                    (self.agent / name).write_text("old pi-only state")
                for name in (*BUILTIN_MCP_FILES, "auth.json", "models.json"):
                    (self.agent / name).write_bytes(b"keep unrelated bytes\r\n")
                self.assertFalse((self.agent / "npm").exists())
                self.assert_success(self.run_cleanup())
                self.assertEqual(json.loads((self.agent / "settings.json").read_text()), expected)
                self.assertFalse((self.agent / "npm").exists())
                for name in MCP_FILES:
                    self.assertFalse(os.path.lexists(self.agent / name), name)
                for name in (*BUILTIN_MCP_FILES, "auth.json", "models.json"):
                    self.assertEqual((self.agent / name).read_bytes(), b"keep unrelated bytes\r\n")
                before = self.storage_snapshot()
                self.assert_success(self.run_cleanup(FAKE_PI_REMOVE="fail"))
                self.assertEqual(self.storage_snapshot(), before)
                self.assertFalse((self.agent / "npm").exists())

    # Break caught: treating an existing empty prefix like an absent prefix before npm runs.
    def test_existing_npm_prefix_without_manifest_stops_before_removal(self):
        self.seed_packages(manifests=False, installed=False)
        (self.agent / "npm").mkdir()
        (self.agent / "mcp-cache.json").write_text("keep on failed preflight")
        before = self.storage_snapshot()
        calls = self.base / "pi-calls"
        result = self.run_cleanup(FAKE_PI_CALL_LOG=str(calls))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("package.json", result.stderr)
        self.assertIn("restore", result.stderr.lower())
        self.assertFalse(calls.exists())
        self.assertEqual(self.storage_snapshot(), before)
        self.assertTrue((self.agent / "npm").is_dir())

    # Break caught: npm removal without a root manifest can prune retained extensions.
    # Previously accepted lock/installed-only fixtures now intentionally fail before mutation.
    def test_lock_only_and_installed_only_without_manifest_stop_before_removal(self):
        for fixture in ("lock", "installed"):
            with self.subTest(fixture=fixture):
                self.seed_packages(entries=KEPT, manifests=False, installed=fixture == "installed")
                if fixture == "lock":
                    self.save(self.agent / "npm/package-lock.json", {
                        "dependencies": {name: {"version": "1.0.0"} for name in REMOVED},
                    })
                (self.agent / "mcp-cache.json").write_text("keep on failed preflight")
                before = self.storage_snapshot()
                calls = self.base / "pi-calls"
                result = self.run_cleanup(FAKE_PI_CALL_LOG=str(calls))
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("package.json", result.stderr)
                self.assertIn("restore", result.stderr.lower())
                self.assertFalse(calls.exists(), "pi ran before the manifest safety check")
                self.assertEqual(self.storage_snapshot(), before)

    # Break caught: checking only root existence, or checking safety after the first removal.
    def test_undeclared_retained_dependency_stops_before_any_removal(self):
        self.seed_packages()
        self.save(self.agent / "npm/package.json", {"dependencies": {
            "pi-mcp-adapter": "1.0.0", "@upstash/context7-pi": "1.0.0", "other": "1.0.0",
        }})
        (self.agent / "mcp-cache.json").write_text("keep on failed preflight")
        before = self.storage_snapshot()
        calls = self.base / "pi-calls"
        result = self.run_cleanup(FAKE_PI_CALL_LOG=str(calls))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("keep-extension", result.stderr)
        self.assertFalse(calls.exists())
        self.assertEqual(self.storage_snapshot(), before)

    # Break caught: malformed dependency sections silently permitting destructive npm pruning.
    def test_invalid_dependency_declarations_stop_before_any_removal(self):
        for value in ([], None, "invalid", {"keep-extension": []}):
            with self.subTest(value=value):
                self.seed_packages()
                self.save(self.agent / "npm/package.json", {"dependencies": value})
                before = self.storage_snapshot()
                calls = self.base / "pi-calls"
                result = self.run_cleanup(FAKE_PI_CALL_LOG=str(calls))
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("package.json", result.stderr)
                self.assertFalse(calls.exists())
                self.assertEqual(self.storage_snapshot(), before)

    # Break caught: rejecting pinned/object/scoped retained packages or non-default dep sections.
    def test_retained_packages_in_all_dependency_sections_allow_removal(self):
        kept = ["npm:keep-extension@1.0", {"source": "npm:@keep/tool@1.0"}, "git:github.com/example/keep"]
        for section in ("dependencies", "devDependencies", "optionalDependencies"):
            with self.subTest(section=section):
                self.seed_packages(entries=kept + ["npm:" + name for name in REMOVED])
                self.save(self.agent / "npm/package.json", {
                    section: {"keep-extension": "1.0", "@keep/tool": "1.0"},
                })
                self.assert_success(self.run_cleanup())
                self.assertEqual(json.loads((self.agent / "settings.json").read_text())["packages"], kept)
                self.assertTrue((self.agent / "npm/node_modules/keep-extension").is_dir())
                for name in REMOVED:
                    self.assertFalse((self.agent / "npm/node_modules" / name).exists())

    # Break caught: applying manifest safety checks despite no target packages needing removal.
    def test_clean_registered_environment_does_not_require_manifest(self):
        self.save(self.agent / "settings.json", {"packages": KEPT})
        before = self.storage_snapshot()
        self.assert_success(self.run_cleanup(FAKE_PI_REMOVE="fail"))
        self.assertEqual(self.storage_snapshot(), before)
        self.assertFalse((self.agent / "npm").exists())

    # Break caught: a fake selective rmtree hiding real npm's prefix-wide pruning.
    @unittest.skipUnless(shutil.which("npm"), "real npm is required for prefix pruning regression")
    def test_real_npm_missing_or_incomplete_manifest_preserves_all_storage(self):
        self.use_real_npm()
        for fixture, dependencies in (("missing", None), ("incomplete", {"pi-mcp-adapter": "1.0.0"})):
            with self.subTest(fixture=fixture):
                self.seed_real_npm(fixture, dependencies)
                before = self.storage_snapshot()
                result = self.run_cleanup()
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("restore", result.stderr.lower())
                self.assertEqual(self.storage_snapshot(), before)

    # Break caught: protecting the manifest by preventing valid installed-only cleanup altogether.
    @unittest.skipUnless(shutil.which("npm"), "real npm is required for prefix pruning regression")
    def test_real_npm_consistent_manifest_removes_only_target(self):
        self.use_real_npm()
        self.seed_real_npm("consistent", {"keep-extension": "1.0.0"})
        kept_dir = self.agent / "npm/node_modules/keep-extension"
        before = {path.name: path.read_bytes() for path in kept_dir.iterdir()}
        self.assert_success(self.run_cleanup())
        self.assertFalse((self.agent / "npm/node_modules/pi-mcp-adapter").exists())
        self.assertEqual(json.loads((self.agent / "settings.json").read_text())["packages"], ["npm:keep-extension"])
        self.assertEqual({path.name: path.read_bytes() for path in kept_dir.iterdir()}, before)

    # Break caught: real npm stderr output turning completed manifest-only removal into failure.
    @unittest.skipUnless(shutil.which("npm"), "real npm is required for stderr regression")
    def test_real_npm_stderr_noise_does_not_turn_success_into_failure(self):
        self.use_real_npm()
        self.seed_real_npm("noisy", {"keep-extension": "1.0.0", "pi-mcp-adapter": "1.0.0"})
        (self.base / "npmrc").write_text("always-auth=true\n")
        self.env["npm_config_loglevel"] = "verbose"  # Also emits stderr on npm versions accepting always-auth.
        result = self.run_cleanup()
        self.assert_success(result)
        self.assertIn("npm ", result.stderr)
        self.assertIn("No matching package found for npm:pi-mcp-adapter", result.stderr)
        self.assertFalse((self.agent / "npm/node_modules/pi-mcp-adapter").exists())
        self.assertTrue((self.agent / "npm/node_modules/keep-extension/extension.js").is_file())

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

    # Break caught: exact stderr comparison rejecting npm notice/warn plus an ANSI diagnostic.
    def test_undeclared_removal_accepts_diagnostic_line_amid_stderr_noise(self):
        self.seed_packages(entries=KEPT)
        result = self.run_cleanup(FAKE_PI_REMOVE="noisy-undeclared")
        self.assert_success(result)
        self.assert_packages_clean()
        self.assertIn("npm notice", result.stderr)

    # Break caught: accepting a wrong/partial diagnostic or a non-1 exit just because residue is gone.
    def test_undeclared_removal_rejects_wrong_diagnostics_and_exit_code(self):
        for mode in ("wrong-source", "partial-diagnostic", "nonzero-undeclared"):
            with self.subTest(mode=mode):
                self.seed_packages(entries=KEPT)
                result = self.run_cleanup(FAKE_PI_REMOVE=mode)
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

    # Break caught: POSIX // is accepted although the OS treats it as forbidden /.
    def test_double_slash_root_is_refused_by_path_guard(self):
        # Exercise the real guard alone: a pre-fix RED must never clean the live root.
        result = subprocess.run(
            [sys.executable, "-c",
             "import runpy, sys; runpy.run_path(sys.argv[1])['agent_directory']()", str(CLEANUP)],
            cwd=self.project, env={**self.env, "PI_CODING_AGENT_DIR": "//"},
            text=True, capture_output=True,
        )
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("unsafe", result.stderr.lower())

    # Break caught: an extra leading slash bypasses HOME rejection and deletes home-level state.
    def test_double_slash_home_is_refused_without_mutating_state(self):
        states = {directory / filename: b"preserve root/home MCP state\r\n"
                  for directory in (self.base, self.home) for filename in MCP_FILES}
        for path, data in states.items():
            path.write_bytes(data)
        result = self.run_cleanup(PI_CODING_AGENT_DIR="/" + str(self.home))
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("unsafe", result.stderr.lower())
        for path, data in states.items():
            self.assertTrue(path.is_file(), str(path))
            self.assertEqual(path.read_bytes(), data, str(path))

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
        path = self.agent / "mcp-cache.json"
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
