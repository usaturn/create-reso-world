"""Tests for durable preparation of the live Blender integration probe."""

from __future__ import annotations

import importlib
import json
import tempfile
import unittest
from pathlib import Path

pipeline = importlib.import_module("modeling.tokyo_nova.pipeline")


class PipelineTests(unittest.TestCase):
    def test_probe_manifest_is_scoped_with_resolvable_assets_and_japanese_capture(self) -> None:
        with tempfile.TemporaryDirectory(prefix="tokyo-nova-manifest-") as temp_dir:
            root = Path(temp_dir)
            export_dir = root / "export"
            export_dir.mkdir()
            (export_dir / "probe.png").write_bytes(b"test image placeholder")
            source = export_dir / "exported.json"
            output = root / "prepared" / "probe-integration.json"
            source.write_text(
                json.dumps(
                    {
                        "ownership": {"key": "exported"},
                        "slot": {"key": "root", "name": "exported", "parent": "Root"},
                        "assets": {"image": {"kind": "texture", "source": "probe.png"}},
                        "children": [],
                    }
                ),
                encoding="utf-8",
            )
            manifest = pipeline.prepare_probe_manifest(source, output)
            # 固定値の理由: プローブは本体（tokyo-nova-west-slum）と別の所有キーで、
            # ResoLoop_Test_* のスロットに置く（AGENTS.md の Resonite safety）。後始末で本体を消さないため。
            self.assertEqual(manifest["ownership"]["key"], "tokyo-nova-probe")
            self.assertEqual(manifest["slot"]["name"], "ResoLoop_Test_TokyoNovaProbe")
            self.assertEqual(manifest["slot"]["position"], [0.0, 0.0, 80.0])
            self.assertIn("probe_front", manifest["cameras"])
            sign = next(item for item in manifest["children"] if item["slot"]["key"] == "probe_japanese_sign")
            self.assertIn("非対称", sign["components"][0]["fields"]["Text"])
            self.assertEqual((output.parent / manifest["assets"]["image"]["source"]).resolve(), (export_dir / "probe.png").resolve())
            self.assertEqual(json.loads(output.read_text(encoding="utf-8")), manifest)


if __name__ == "__main__":
    unittest.main()
