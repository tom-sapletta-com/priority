from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

import jsonschema
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "adapters"))

from standardctl import evaluate, parse_time, validate_semantics  # noqa: E402


class StandardCtlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.policy = yaml.safe_load((ROOT / "priority-evolution.dsl.yaml").read_text(encoding="utf-8"))
        cls.schema = json.loads((ROOT / "schemas" / "priority-evolution.schema.json").read_text(encoding="utf-8"))
        cls.healthy = json.loads((ROOT / "examples" / "healthy-state.json").read_text(encoding="utf-8"))
        cls.problem = json.loads((ROOT / "examples" / "state.json").read_text(encoding="utf-8"))
        cls.now = parse_time("2026-08-19T10:00:00Z")

    def test_policy_matches_schema_and_semantics(self) -> None:
        jsonschema.Draft202012Validator(self.schema).validate(self.policy)
        self.assertEqual(validate_semantics(self.policy), [])
        self.assertEqual(self.policy["metadata"]["version"], "0.3.0")

    def test_healthy_state_passes_but_candidate_cannot_dispatch(self) -> None:
        receipt = evaluate(self.policy, self.healthy, self.now)
        self.assertEqual(receipt["finalOutcome"], "PASS")
        self.assertFalse(receipt["executionGate"]["dispatchAllowed"])
        self.assertIn("policy-lifecycle:candidate", receipt["executionGate"]["reason"])

    def test_plan_gap_and_offer_pin_block(self) -> None:
        receipt = evaluate(self.policy, self.problem, self.now)
        self.assertEqual(receipt["finalOutcome"], "BLOCK")
        violated = {item["id"] for item in receipt["invariants"] if item["status"] == "VIOLATED"}
        self.assertIn("INV-NONEMPTY-GROUNDED-PLAN", violated)
        self.assertIn("INV-OFFER-DIGEST-PIN", violated)

    def test_tool_planning_precedes_dependent_repairs(self) -> None:
        receipt = evaluate(self.policy, self.problem, self.now)
        order = receipt["complementarity"]["sequentialOrder"]
        self.assertLess(order.index("STD-TOOL-GROUNDED-PLANNING"), order.index("STD-OFFER-SSOT-INTEGRITY"))
        self.assertLess(order.index("STD-TOOL-GROUNDED-PLANNING"), order.index("STD-ECOSYSTEM-CONTEXT-ROUTING"))

    def test_complementarity_budget_is_measured(self) -> None:
        receipt = evaluate(self.policy, self.problem, self.now)
        budget = receipt["complementarity"]["budgetAssessment"]
        self.assertEqual(budget["status"], "PASS")
        self.assertEqual(budget["concurrentRepairs"], 3)
        self.assertFalse(receipt["complementarity"]["hardConflict"])

    def test_stale_metric_fails_closed(self) -> None:
        state = copy.deepcopy(self.healthy)
        state["metrics"]["planning.todo2code_plan_gap_count"]["observedAt"] = "2026-08-19T09:00:00Z"
        receipt = evaluate(self.policy, state, self.now)
        self.assertEqual(receipt["finalOutcome"], "BLOCK")
        decision = next(item for item in receipt["decisions"] if item["intentId"] == "STD-TOOL-GROUNDED-PLANNING")
        self.assertEqual(decision["evidenceStatus"], "MISSING_OR_STALE")
        self.assertEqual(decision["outcome"], "BLOCK")

    def test_revision_mismatch_invalidates_evidence(self) -> None:
        state = copy.deepcopy(self.healthy)
        state["metrics"]["offer.catalog_binding_coverage"]["revision"] = "sha256:other-head"
        receipt = evaluate(self.policy, state, self.now)
        metric = receipt["metricFreshness"]["offer.catalog_binding_coverage"]
        self.assertFalse(metric["revisionMatches"])
        self.assertEqual(receipt["finalOutcome"], "BLOCK")

    def test_separation_of_duties_is_constitutional_block(self) -> None:
        state = copy.deepcopy(self.healthy)
        state["metrics"]["governance.separation_of_duties_violations"]["value"] = 1
        receipt = evaluate(self.policy, state, self.now)
        finding = next(item for item in receipt["invariants"] if item["id"] == "INV-NO-SELF-PROMOTION")
        self.assertEqual(finding["status"], "VIOLATED")
        self.assertEqual(receipt["finalOutcome"], "BLOCK")

    def test_active_policy_can_dispatch_bounded_delivery(self) -> None:
        policy = copy.deepcopy(self.policy)
        policy["metadata"]["lifecycle"] = "active"
        state = copy.deepcopy(self.healthy)
        state["facts"]["work"]["delivery_needed"] = True
        state["facts"]["planEstimates"]["DELIVERY-EVOLUTION"] = {"files": 2, "changedLines": 80, "agentTurns": 4}
        receipt = evaluate(policy, state, self.now)
        self.assertEqual(receipt["finalOutcome"], "ACTION_REQUIRED")
        self.assertTrue(receipt["executionGate"]["dispatchAllowed"])

    def test_unmeasured_oscillation_requires_review(self) -> None:
        state = copy.deepcopy(self.healthy)
        del state["facts"]["control"]["priorityChangesLastHour"]
        receipt = evaluate(self.policy, state, self.now)
        self.assertEqual(receipt["oscillationGuard"]["status"], "NOT_MEASURED")
        self.assertEqual(receipt["finalOutcome"], "REVIEW_REQUIRED")


if __name__ == "__main__":
    unittest.main()
