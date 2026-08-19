from __future__ import annotations

import copy
import importlib.util
import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("standardctl", ROOT / "adapters" / "standardctl.py")
assert SPEC and SPEC.loader
standardctl = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = standardctl
SPEC.loader.exec_module(standardctl)


class EvolutionaryPriorityPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.policy = standardctl.load_yaml(ROOT / "priority-evolution.dsl.yaml")
        cls.state = standardctl.load_json(ROOT / "examples" / "state.json")
        cls.now = datetime(2026, 8, 19, 10, 0, tzinfo=timezone.utc)

    def evaluate(self, state=None, policy=None):
        return standardctl.evaluate(policy or self.policy, state or copy.deepcopy(self.state), self.now)

    def healthy_state(self):
        state = copy.deepcopy(self.state)
        replacements = {
            "governance.duplicate_home_count": 0,
            "evidence.stale_or_mismatched_receipts": 0,
            "governance.separation_of_duties_violations": 0,
            "evidence.shape_only_pass_count": 0,
            "standards.compliance_coverage": 1.0,
            "standards.drift_open_count": 0,
            "standards.governance_truth_false_block_rate": 0.0,
            "standards.governance_truth_false_block_sample_size": 42,
            "standards.validation_behavior_false_block_rate": 0.0,
            "standards.validation_behavior_false_block_sample_size": 42,
            "standards.manifest_conformance_false_block_rate": 0.0,
            "standards.manifest_conformance_false_block_sample_size": 42,
            "standards.conflict_density": 0.0,
            "agent.out_of_scope_action_rate": 0.0,
            "agent.rule_citation_coverage": 1.0,
        }
        for metric_id, value in replacements.items():
            state["metrics"][metric_id]["value"] = value
        state["facts"]["work"]["delivery_needed"] = False
        return state

    def test_schema_and_semantics(self) -> None:
        schema = standardctl.load_json(ROOT / "schemas" / "priority-evolution.schema.json")
        import jsonschema
        jsonschema.Draft202012Validator(schema).validate(self.policy)
        self.assertEqual([], standardctl.validate_semantics(self.policy))

    def test_lexicographic_class_order_cannot_be_crossed_by_score(self) -> None:
        receipt = self.evaluate()
        decisions = receipt["decisions"]
        self.assertEqual("STD-GOVERNANCE-TRUTH", decisions[0]["intentId"])
        self.assertEqual("constitutional", decisions[0]["priorityClass"])
        delivery = next(item for item in decisions if item["intentId"] == "DELIVERY-EVOLUTION")
        self.assertEqual(0.0, delivery["dispatchUrgency"])
        self.assertLess(decisions[0]["classRank"], delivery["classRank"])

    def test_blocking_invariant_closes_execution_gate(self) -> None:
        receipt = self.evaluate()
        self.assertEqual("BLOCK", receipt["finalOutcome"])
        self.assertFalse(receipt["executionGate"]["dispatchAllowed"])
        violated = {item["id"] for item in receipt["invariants"] if item["status"] == "VIOLATED"}
        self.assertIn("INV-FRESH-EVIDENCE", violated)
        self.assertIn("INV-NO-CLAIM-AS-PASS", violated)

    def test_high_false_block_rate_proposes_standard_change_not_self_activation(self) -> None:
        receipt = self.evaluate()
        validation = next(item for item in receipt["decisions"] if item["intentId"] == "STD-VALIDATION-BEHAVIOR")
        self.assertEqual("PROPOSE_STANDARD_CHANGE", validation["outcome"])
        action = validation["actions"][0]
        self.assertEqual(["candidate", "shadow", "canary", "active"], action["lifecycle"])
        self.assertIn("independent-validator", action["requiresHumanRoles"])

    def test_stale_metric_never_becomes_pass(self) -> None:
        state = copy.deepcopy(self.state)
        state["metrics"]["standards.compliance_coverage"]["observedAt"] = "2026-08-18T00:00:00Z"
        receipt = self.evaluate(state)
        validation = next(item for item in receipt["decisions"] if item["intentId"] == "STD-VALIDATION-BEHAVIOR")
        self.assertEqual("MISSING_OR_STALE", validation["evidenceStatus"])
        self.assertEqual("REVIEW_REQUIRED", validation["outcome"])
        self.assertNotEqual("PASS", receipt["finalOutcome"])

    def test_healthy_state_passes_without_proposed_actions(self) -> None:
        receipt = self.evaluate(self.healthy_state())
        self.assertEqual("PASS", receipt["finalOutcome"])
        self.assertEqual([], receipt["planDelta"]["actions"])
        self.assertFalse(receipt["executionGate"]["dispatchAllowed"])
        self.assertIn("policy-lifecycle:candidate", receipt["executionGate"]["reason"])

    def test_missing_plan_budget_is_a_hard_complementarity_conflict(self) -> None:
        state = copy.deepcopy(self.state)
        del state["facts"]["planEstimates"]["STD-GOVERNANCE-TRUTH"]
        receipt = self.evaluate(state)
        self.assertTrue(receipt["complementarity"]["hardConflict"])
        self.assertTrue(any(
            item["type"] == "BUDGET_NOT_MEASURED" and item.get("intentId") == "STD-GOVERNANCE-TRUTH"
            for item in receipt["complementarity"]["findings"]
        ))

    def test_dependency_cycle_is_rejected_and_blocks_dispatch(self) -> None:
        policy = copy.deepcopy(self.policy)
        governance = next(item for item in policy["spec"]["intents"] if item["id"] == "STD-GOVERNANCE-TRUTH")
        governance["relations"]["requires"].append("DELIVERY-EVOLUTION")
        self.assertTrue(any("dependency cycle" in error for error in standardctl.validate_semantics(policy)))
        receipt = self.evaluate(policy=policy)
        self.assertTrue(receipt["complementarity"]["hardConflict"])
        self.assertTrue(any(item["type"] == "DEPENDENCY_CYCLE" for item in receipt["complementarity"]["findings"]))

    def test_oscillation_guard_freezes_an_otherwise_healthy_policy(self) -> None:
        state = self.healthy_state()
        state["facts"]["control"]["priorityChangesLastHour"] = 7
        receipt = self.evaluate(state)
        self.assertEqual("TRIGGERED", receipt["oscillationGuard"]["status"])
        self.assertEqual("REVIEW_REQUIRED", receipt["finalOutcome"])
        self.assertFalse(receipt["executionGate"]["dispatchAllowed"])

    def test_intent_minimum_source_rank_is_enforced(self) -> None:
        state = copy.deepcopy(self.state)
        metric = state["metrics"]["standards.compliance_coverage"]
        metric["sourceClass"] = "documentation"
        receipt = self.evaluate(state)
        validation = next(item for item in receipt["decisions"] if item["intentId"] == "STD-VALIDATION-BEHAVIOR")
        self.assertEqual("MISSING_OR_STALE", validation["evidenceStatus"])
        self.assertEqual("REVIEW_REQUIRED", validation["outcome"])

    def test_receipt_digest_is_deterministic_for_fixed_time(self) -> None:
        first = self.evaluate()
        second = self.evaluate()
        self.assertEqual(first["receiptDigest"], second["receiptDigest"])

    def test_generated_facades_share_one_context(self) -> None:
        receipt = self.evaluate()
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            standardctl.compile_facades(self.policy, receipt, out)
            self.assertTrue((out / "AGENTS.md").exists())
            self.assertIn("@.wellmanifest/generated/agent-policy.md", (out / "CLAUDE.md").read_text())
            self.assertIn("@.wellmanifest/generated/agent-policy.md", (out / "GEMINI.md").read_text())
            context = (out / ".wellmanifest" / "generated" / "agent-policy.md").read_text()
            self.assertIn(receipt["receiptDigest"], context)


if __name__ == "__main__":
    unittest.main()
