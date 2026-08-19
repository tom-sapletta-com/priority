from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "adapters"))

from autonomyctl import discover_tools, run_cycle  # noqa: E402
from ecosystemctl import load_json, validate_plan_result  # noqa: E402


class AutonomyCtlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.request = load_json(ROOT / "examples" / "ticket-context-request.json")
        cls.cycle_schema = json.loads((ROOT / "schemas" / "autonomy-cycle.schema.json").read_text())
        cls.discovery_schema = json.loads((ROOT / "schemas" / "tool-discovery.schema.json").read_text())

    def test_unpinned_planner_is_not_run_not_fake_success(self) -> None:
        discovery = discover_tools(ROOT, environ={"AUTONOMY_DISCOVER_SIBLINGS": "0"})
        jsonschema.Draft202012Validator(self.discovery_schema).validate(discovery)
        self.assertFalse(discovery["applyAllowed"])
        if not discovery["planner"]["cli"]:
            self.assertEqual(discovery["planner"]["reason"], "T2C_PLANNER_NOT_PINNED")
        envelope = {
            "status": "not-run",
            "code": "T2C_PLANNER_NOT_PINNED",
            "recordCount": 0,
            "plans": [],
        }
        receipt = validate_plan_result(self.request, envelope, "2026-08-19T10:00:00Z")
        codes = {item["code"] for item in receipt["findings"]}
        self.assertIn("T2C_PLANNER_NOT_PINNED", codes)
        self.assertNotIn("T2C_PLAN_GAP", codes)
        self.assertEqual(receipt["finalOutcome"], "BLOCK")

    def test_local_planner_sources_pin_when_discovery_enabled(self) -> None:
        discovery = discover_tools(
            ROOT,
            environ={
                "AUTONOMY_DISCOVER_SIBLINGS": "1",
                "TODO2CODE_CLI": str(ROOT / "adapters" / "autonomyctl.py"),
                "OFFER_ROOT": "",
            },
        )
        self.assertTrue((ROOT / "sources" / "planner" / "intent.graph.json").is_file())
        self.assertTrue(discovery["planner"]["pinned"])
        self.assertEqual(discovery["planner"]["reason"], "pinned")

    def test_cli_without_graph_is_contract_unbound(self) -> None:
        discovery = discover_tools(
            ROOT,
            environ={
                "AUTONOMY_DISCOVER_SIBLINGS": "0",
                "TODO2CODE_CLI": str(ROOT / "adapters" / "autonomyctl.py"),
            },
        )
        self.assertTrue(discovery["planner"]["cli"])
        self.assertFalse(discovery["planner"]["pinned"])
        self.assertEqual(discovery["planner"]["reason"], "T2C_PLANNER_CONTRACT_UNBOUND")

    def test_cycle_abstains_and_never_applies(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cycle = run_cycle(
                ROOT,
                Path(tmp),
                ROOT / "examples" / "ticket-context-request.json",
                now="2026-08-19T10:00:00Z",
                revision="sha256:example-head-20260819-v030",
                environ={"AUTONOMY_DISCOVER_SIBLINGS": "0"},
            )
        jsonschema.Draft202012Validator(self.cycle_schema).validate(cycle)
        self.assertFalse(cycle["applyAttempted"])
        self.assertFalse(cycle["applyAllowed"])
        self.assertFalse(cycle["dispatchAllowed"])
        self.assertEqual(cycle["finalOutcome"], "BLOCK")
        self.assertIn("T2C_PLANNER_NOT_PINNED", cycle["abstentions"] + [cycle["steps"][3].get("code")])
        self.assertIn("OFFER_PIN_NOT_PINNED", cycle["abstentions"])

    def test_injected_zero_plan_stays_plan_gap(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cycle = run_cycle(
                ROOT,
                Path(tmp),
                ROOT / "examples" / "ticket-context-request.json",
                now="2026-08-19T10:00:00Z",
                revision="sha256:example-head-20260819-v030",
                planner_result=ROOT / "examples" / "todo2code-zero-plan.json",
                environ={"AUTONOMY_DISCOVER_SIBLINGS": "0"},
            )
            planner = json.loads((Path(tmp) / "receipts" / "planner-validation.json").read_text())
        self.assertEqual(planner["finalOutcome"], "BLOCK")
        self.assertIn("T2C_PLAN_GAP", {item["code"] for item in planner["findings"]})
        self.assertEqual(cycle["finalOutcome"], "BLOCK")

    def test_injected_offer_fixture_is_not_live_attestation_but_is_measured(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_cycle(
                ROOT,
                Path(tmp),
                ROOT / "examples" / "ticket-context-request.json",
                now="2026-08-19T10:00:00Z",
                revision="sha256:example-head-20260819-v030",
                planner_result=ROOT / "examples" / "todo2code-zero-plan.json",
                offer_receipt=ROOT / "examples" / "offer-pin-pass.fixture.json",
                environ={"AUTONOMY_DISCOVER_SIBLINGS": "0"},
            )
            state = json.loads((Path(tmp) / "generated" / "current-state.json").read_text())
            offer = json.loads((Path(tmp) / "receipts" / "offer-pin.json").read_text())
        self.assertTrue(offer["fixture"])
        self.assertEqual(state["metrics"]["offer.facade_digest_mismatch_count"]["value"], 0)


if __name__ == "__main__":
    unittest.main()
