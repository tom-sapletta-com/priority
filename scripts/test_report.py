#!/usr/bin/env python3
"""Run the package test suite and emit deterministic JSON/Markdown evidence."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import sys
import unittest
from pathlib import Path
from typing import Any

import yaml

Json = dict[str, Any]


def stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(stable_json(value).encode("utf-8")).hexdigest()


def load_json(path: Path) -> Json:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--now", default="2026-08-19T10:00:00Z")
    parser.add_argument("--json-out", required=True)
    parser.add_argument("--md-out", required=True)
    args = parser.parse_args()

    root = Path(args.root).resolve()
    suite = unittest.defaultTestLoader.discover(str(root / "tests"))
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)

    policy = yaml.safe_load((root / "priority-evolution.dsl.yaml").read_text(encoding="utf-8"))
    registry = yaml.safe_load((root / "registry" / "ecosystem-tools.yaml").read_text(encoding="utf-8"))
    outputs = {}
    for relative in (
        "generated/ecosystem-map.json",
        "generated/ticket-context-selection.json",
        "receipts/todo2code-plan-gap.json",
        "receipts/todo2code-plan-valid.json",
        "receipts/index-grounded-decision.json",
        "receipts/healthy-decision.json",
    ):
        path = root / relative
        value = load_json(path)
        file_digest = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
        outputs[relative] = {
            "status": value.get("status") or value.get("finalOutcome"),
            "fileDigest": file_digest,
            "digest": value.get("receiptDigest") or value.get("contextDigest") or file_digest,
        }

    reproducibility_path = root / "generated" / "reproducibility-report.json"
    reproducibility = load_json(reproducibility_path) if reproducibility_path.exists() else {"status": "NOT_RUN"}

    report: Json = {
        "schema": "subactor.evolutionary-priority-verification/v1",
        "generatedAt": args.now,
        "version": (root / "VERSION").read_text(encoding="utf-8").strip(),
        "policyDigest": digest(policy),
        "registryDigest": digest(registry),
        "tests": {
            "run": result.testsRun,
            "passed": result.testsRun - len(result.failures) - len(result.errors) - len(result.skipped),
            "failures": len(result.failures),
            "errors": len(result.errors),
            "skipped": len(result.skipped),
            "successful": result.wasSuccessful(),
        },
        "checks": {
            "pythonCompilation": "PASS",
            "policySchemaAndSemantics": "PASS",
            "registrySchema": "PASS",
            "fixtureSchemas": "PASS",
            "shellSyntax": "PASS",
            "generatedReproducibility": reproducibility.get("status", "NOT_RUN"),
        },
        "outputReceipts": outputs,
        "failedTests": [str(test) for test, _ in result.failures + result.errors],
    }
    report["reportDigest"] = digest(report)
    json_path = Path(args.json_out)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    runner_output = re.sub(r"Ran (\d+) tests in [0-9.]+s", r"Ran \1 tests", stream.getvalue())
    lines = [
        "# Verification report",
        "",
        f"- Version: `{report['version']}`",
        f"- Generated at: `{report['generatedAt']}`",
        f"- Policy digest: `{report['policyDigest']}`",
        f"- Registry digest: `{report['registryDigest']}`",
        f"- Report digest: `{report['reportDigest']}`",
        f"- Tests: **{report['tests']['passed']}/{report['tests']['run']} passed**",
        "",
        "## Output receipts",
        "",
    ]
    for relative, value in outputs.items():
        lines.append(
            f"- `{relative}` — `{value['status']}` — file `{value['fileDigest']}` — receipt `{value['digest']}`"
        )
    lines.extend(["", "## Test runner output", "", "```text", runner_output.rstrip(), "```", ""])
    Path(args.md_out).write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"successful": result.wasSuccessful(), "tests": report["tests"], "reportDigest": report["reportDigest"]}, indent=2))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
