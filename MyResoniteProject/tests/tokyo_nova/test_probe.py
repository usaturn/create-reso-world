"""Offline Blender integration checks for the asymmetric pipeline probe."""

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROBE_SCRIPT = PROJECT_ROOT / "modeling/tokyo_nova/probe.py"


class ProbeTests(unittest.TestCase):
    def test_probe_script_saves_an_editable_blend_with_source_textures(self) -> None:
        with tempfile.TemporaryDirectory(prefix="tokyo-nova-probe-") as temp_dir:
            output = Path(temp_dir) / "asymmetric-probe.blend"
            result = subprocess.run(
                [
                    "resoloop",
                    "blender",
                    "run",
                    str(PROBE_SCRIPT),
                    f"--arg={output}",
                    "--json",
                ],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                check=False,
                timeout=180,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertTrue(payload["ok"], payload)
            self.assertTrue(output.is_file())
            for name in ("probe-albedo.png", "probe-roughness.png", "probe-emission.png", "probe-normal.png"):
                self.assertTrue((output.parent / name).is_file(), name)
            report = json.loads((output.parent / "probe-report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["blender_dimensions_m"], [1.0, 0.6, 0.8])
            self.assertEqual(report["resonite_dimensions_m"], [1.0, 0.8, 0.6])
            self.assertTrue(report["uv_map"])
            self.assertTrue(report["packed_images"])
            self.assertTrue(report["face_normals_valid"])
            self.assertEqual(report["japanese_sign_strategy"], "Resonite TextRenderer: 非対称・1m計測面")


if __name__ == "__main__":
    unittest.main()
