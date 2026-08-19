from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "adapters"))

from toon_index import diff_toon_indexes, parse_toon_index  # noqa: E402


class ToonIndexTests(unittest.TestCase):
    def write_map(self, directory: Path, name: str, modules: list[tuple[str, int]], details: str = "") -> Path:
        body = [
            "# acme | code2llm map | 2026-08-19",
            f"M[{len(modules)}]:",
            *[f"  {path},{lines}" for path, lines in modules],
            "D:",
            details.rstrip(),
            "",
        ]
        path = directory / name
        path.write_text("\n".join(body), encoding="utf-8")
        return path

    def test_parses_modules_and_header(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write_map(Path(tmp), "map.toon", [("repo/a.py", 3), ("repo/b.ts", 7)])
            index = parse_toon_index(path)
        self.assertEqual(index.organization, "acme")
        self.assertEqual(index.generated_date, "2026-08-19")
        self.assertEqual(index.declared_module_count, 2)
        self.assertTrue(index.has_module("repo/a.py"))

    def test_parses_compact_class_members(self) -> None:
        details = """  repo/service.py:
    Service: __init__(1),close(0),generate_plan(2)
"""
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write_map(Path(tmp), "map.toon", [("repo/service.py", 10)], details)
            index = parse_toon_index(path)
        self.assertTrue(index.has_symbol("repo/service.py", "Service"))
        self.assertTrue(index.has_symbol("repo/service.py", "generate_plan"))
        self.assertTrue(index.has_symbol("repo/service.py", "close"))

    def test_project_roots_are_counted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write_map(
                Path(tmp),
                "map.toon",
                [("alpha/a.py", 1), ("alpha/b.py", 1), ("beta/c.py", 1)],
            )
            index = parse_toon_index(path)
        self.assertEqual(index.project_roots(), {"alpha": 2, "beta": 1})

    def test_diff_reports_added_removed_and_changed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            before = parse_toon_index(self.write_map(directory, "before.toon", [("a/x", 1), ("b/y", 2)]))
            after = parse_toon_index(self.write_map(directory, "after.toon", [("a/x", 3), ("c/z", 4)]))
            result = diff_toon_indexes(before, after)
        self.assertEqual(result["summary"], {"added": 1, "removed": 1, "changedLineCount": 1})
        self.assertEqual(result["addedModules"], ["c/z"])
        self.assertEqual(result["removedModules"], ["b/y"])
        self.assertEqual(result["changedModules"], ["a/x"])


if __name__ == "__main__":
    unittest.main()
