from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "adapters"))

from statectl import StateProjectionError, project_state  # noqa: E402


class StateCtlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.policy = yaml.safe_load((ROOT / "priority-evolution.dsl.yaml").read_text(encoding="utf-8"))
        cls.ecosystem = json.loads((ROOT / "generated" / "ecosystem-map.json").read_text(encoding="utf-8"))
        cls.route = json.loads((ROOT / "generated" / "ticket-context-selection.json").read_text(encoding="utf-8"))
        cls.plan_gap = json.loads((ROOT / "receipts" / "todo2code-plan-gap.json").read_text(encoding="utf-8"))
        cls.base = json.loads((ROOT / "examples" / "healthy-state.json").read_text(encoding="utf-8"))
        cls.revision = cls.base["revision"]
        cls.observed_at = "2026-08-19T09:59:30Z"

    def test_projection_derives_route_and_plan_gap_metrics(self) -> None:
        state = project_state(
            self.policy,
            self.ecosystem,
            self.revision,
            self.observed_at,
            base_state=self.base,
            route=self.route,
            planner_receipt=self.plan_gap,
        )
        self.assertEqual(state["metrics"]["planning.todo2code_plan_gap_count"]["value"], 1)
        self.assertEqual(state["metrics"]["planning.unverified_tool_selection_count"]["value"], 3)
        self.assertGreater(state["metrics"]["routing.required_capability_gap_count"]["value"], 0)

    def test_behavioral_offer_metric_stays_missing_without_receipt(self) -> None:
        state = project_state(
            self.policy,
            self.ecosystem,
            self.revision,
            self.observed_at,
            base_state=self.base,
        )
        self.assertNotIn("offer.facade_digest_mismatch_count", state["metrics"])
        self.assertIn("offer.facade_digest_mismatch_count", state["projection"]["missingMetrics"])

    def test_offer_receipt_closes_behavioral_metric_gap(self) -> None:
        offer = json.loads((ROOT / "examples" / "offer-pin-pass.fixture.json").read_text(encoding="utf-8"))
        state = project_state(
            self.policy,
            self.ecosystem,
            self.revision,
            self.observed_at,
            base_state=self.base,
            route=self.route,
            planner_receipt=json.loads((ROOT / "receipts" / "todo2code-plan-valid.json").read_text(encoding="utf-8")),
            offer_receipt=offer,
        )
        self.assertEqual(state["metrics"]["offer.facade_digest_mismatch_count"]["value"], 0)
        self.assertNotIn("offer.facade_digest_mismatch_count", state["projection"]["missingMetrics"])

    def test_offer_receipt_revision_must_match(self) -> None:
        offer = json.loads((ROOT / "examples" / "offer-pin-pass.fixture.json").read_text(encoding="utf-8"))
        offer["revision"] = "sha256:other"
        with self.assertRaises(StateProjectionError):
            project_state(
                self.policy,
                self.ecosystem,
                self.revision,
                self.observed_at,
                offer_receipt=offer,
            )


if __name__ == "__main__":
    unittest.main()
