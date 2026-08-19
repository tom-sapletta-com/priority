from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
PYQUAL_ROOT = ROOT.parent.parent / "semcod" / "pyqual"


class PyqualContractTests(unittest.TestCase):
    def test_pinned_default_yaml_matches_revision_digest(self) -> None:
        pin = json.loads((ROOT / "sources" / "contracts" / "pyqual" / "revision.json").read_text())
        raw = (ROOT / pin["path"]).read_bytes()
        digest = "sha256:" + __import__("hashlib").sha256(raw).hexdigest()
        self.assertEqual(pin["digest"], digest)
        self.assertFalse(pin["enforcementEnabled"])
        self.assertEqual(pin["revision"], "git:2fe7e4730a6c1d5b3326faaec4e41d455891e0ef")

    def test_pinned_default_yaml_parses_with_native_pyqual(self) -> None:
        if not (PYQUAL_ROOT / "pyqual" / "config.py").is_file():
            self.skipTest("semcod/pyqual checkout is not available")
        sys.path.insert(0, str(PYQUAL_ROOT))
        try:
            from pyqual.config import PyqualConfig  # type: ignore
        except ImportError as exc:
            self.skipTest(f"semcod/pyqual is not importable: {exc}")

        raw = yaml.safe_load((ROOT / "sources" / "contracts" / "pyqual" / "default.yaml").read_text())
        config = PyqualConfig._parse(raw)
        self.assertEqual(config.name, "quality-loop")
        self.assertTrue(config.stages)

    def test_native_parser_rejects_stage_with_run_and_tool(self) -> None:
        if not (PYQUAL_ROOT / "pyqual" / "config.py").is_file():
            self.skipTest("semcod/pyqual checkout is not available")
        sys.path.insert(0, str(PYQUAL_ROOT))
        try:
            from pyqual.config import PyqualConfig  # type: ignore
        except ImportError as exc:
            self.skipTest(f"semcod/pyqual is not importable: {exc}")

        raw = {
            "pipeline": {
                "name": "negative",
                "stages": [{"name": "broken", "run": "echo x", "tool": "report"}],
            }
        }
        with self.assertRaises(ValueError):
            PyqualConfig._parse(raw)


if __name__ == "__main__":
    unittest.main()
