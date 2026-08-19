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

from ecosystemctl import (  # noqa: E402
    build_ecosystem_map,
    classify_empty_plan,
    create_planner_request,
    default_index_maps,
    load_json,
    load_yaml,
    render_llms_index,
    route_ticket,
    tokenize,
    validate_plan_result,
)


class EcosystemCtlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = load_yaml(ROOT / "registry" / "ecosystem-tools.yaml")
        cls.registry_schema = load_json(ROOT / "schemas" / "ecosystem-tool-registry.schema.json")
        cls.ecosystem_map = build_ecosystem_map(
            cls.registry,
            default_index_maps(ROOT),
            "2026-08-19T10:00:00Z",
        )
        cls.request = load_json(ROOT / "examples" / "ticket-context-request.json")

    def test_registry_matches_schema(self) -> None:
        jsonschema.Draft202012Validator(self.registry_schema).validate(self.registry)

    def test_home_owners_are_unique(self) -> None:
        owners = self.ecosystem_map["homeOwners"]
        self.assertTrue(owners)
        self.assertTrue(all(len(value) == 1 for value in owners.values()))
        self.assertEqual(owners["commercial-offer-values"], ["subactor/offer"])
        self.assertEqual(owners["commercial-offer-standard"], ["wellmanifest/offer"])

    def test_verified_tools_are_execution_eligible(self) -> None:
        projects = {item["id"]: item for item in self.ecosystem_map["projects"]}
        for project_id in ("autogrammar/todo2code", "subactor/diagit", "subactor/onedev-agent"):
            self.assertEqual(projects[project_id]["evidence"]["status"], "VERIFIED")
            self.assertTrue(projects[project_id]["evidence"]["executionEligible"])

    def test_documentation_only_tool_is_not_execution_eligible(self) -> None:
        project = next(item for item in self.ecosystem_map["projects"] if item["id"] == "semcod/giton")
        self.assertEqual(project["evidence"]["status"], "DOCUMENTED")
        self.assertFalse(project["evidence"]["executionEligible"])

    def test_pinned_quality_gate_is_execution_eligible(self) -> None:
        project = next(item for item in self.ecosystem_map["projects"] if item["id"] == "semcod/pyqual")
        self.assertEqual(project["evidence"]["status"], "VERIFIED")
        self.assertTrue(project["evidence"]["executionEligible"])

    def test_candidate_standard_can_be_verified_but_not_executable(self) -> None:
        projects = {item["id"]: item for item in self.ecosystem_map["projects"]}
        for project_id in ("wellmanifest/policy-dsl", "wellmanifest/offer"):
            self.assertEqual(projects[project_id]["evidence"]["status"], "VERIFIED")
            self.assertFalse(projects[project_id]["evidence"]["executionEligible"])
        self.assertEqual(projects["wellmanifest/new-project"]["evidence"]["status"], "VERIFIED")
        self.assertTrue(projects["wellmanifest/new-project"]["evidence"]["executionEligible"])

    def test_default_indexes_include_wellmanifest_and_pyqual(self) -> None:
        maps = default_index_maps(ROOT)
        self.assertGreaterEqual(set(maps), {"subactor", "autogrammar", "wellmanifest", "pyqual"})

    def test_tokenize_keeps_polish_l_stroke_words_intact(self) -> None:
        tokens = tokenize("dokładnymi digestami istniejącego równoległego super-agenta")
        self.assertIn("dokladnymi", tokens)
        self.assertIn("istniejacego", tokens)
        self.assertIn("rownoleglego", tokens)
        self.assertIn("agent", tokens)
        self.assertNotIn("dok", tokens)
        self.assertNotIn("adnymi", tokens)
        self.assertNotIn("ego", tokens)
        self.assertNotIn("ale", tokens)

    def test_tokenize_drops_function_words_and_maps_synonyms(self) -> None:
        tokens = tokenize("Zbuduj mapę projektu i planowania, ale nie twórz drugiego HOME.")
        self.assertIn("map", tokens)
        self.assertIn("project", tokens)
        self.assertIn("planning", tokens)
        self.assertFalse({"ale", "i", "nie", "do", "dok", "adnymi", "ego"} & tokens)

    def test_router_tokens_are_not_split_on_polish_stroke(self) -> None:
        route = route_ticket(self.ecosystem_map, self.request)
        forbidden = {"dok", "adnymi", "ego", "ale", "ani", "bez"}
        self.assertFalse(forbidden & set(route["tokens"]))

    def test_router_selects_real_planner_and_fleet_observer(self) -> None:
        route = route_ticket(self.ecosystem_map, self.request)
        self.assertEqual(route["roleAssignment"]["planner"], "autogrammar/todo2code")
        self.assertEqual(route["roleAssignment"]["fleet-observer"], "subactor/diagit")
        self.assertEqual(route["status"], "REVIEW_REQUIRED")

    def test_router_fails_closed_for_documentation_only_required_role(self) -> None:
        route = route_ticket(self.ecosystem_map, self.request)
        codes = {item["code"] for item in route["findings"]}
        self.assertIn("ROUTER_REQUIRED_ROLE_NOT_EXECUTION_VERIFIED", codes)

    def test_planner_request_encodes_zero_plan_policy(self) -> None:
        route = route_ticket(self.ecosystem_map, self.request)
        planner_request = create_planner_request(self.request, route)
        self.assertEqual(planner_request["planner"]["projectId"], "autogrammar/todo2code")
        self.assertEqual(planner_request["planPolicy"]["onZeroPlansWhenOpenCriteria"], "T2C_PLAN_GAP")
        self.assertEqual(
            planner_request["planPolicy"]["onZeroImplementationDiagnostics"],
            "T2C_NO_IMPLEMENTATION_DIAGNOSTICS",
        )
        self.assertTrue(planner_request["planPolicy"]["requireNegativeBehaviorTest"])

    def test_zero_plan_is_blocked(self) -> None:
        result = load_json(ROOT / "examples" / "todo2code-zero-plan.json")
        receipt = validate_plan_result(self.request, result)
        self.assertEqual(receipt["finalOutcome"], "BLOCK")
        self.assertIn("T2C_PLAN_GAP", {item["code"] for item in receipt["findings"]})

    def test_zero_implementation_diagnostics_is_not_plan_gap(self) -> None:
        result = load_json(ROOT / "examples" / "todo2code-zero-implementation-diagnostics.json")
        self.assertEqual(classify_empty_plan(result), "T2C_NO_IMPLEMENTATION_DIAGNOSTICS")
        receipt = validate_plan_result(self.request, result)
        codes = {item["code"] for item in receipt["findings"]}
        self.assertEqual(receipt["finalOutcome"], "BLOCK")
        self.assertIn("T2C_NO_IMPLEMENTATION_DIAGNOSTICS", codes)
        self.assertNotIn("T2C_PLAN_GAP", codes)

    def test_unplannable_implementation_diagnostics_stay_plan_gap(self) -> None:
        result = {
            "status": "succeeded",
            "recordCount": 0,
            "sourceDiagnosticCount": 3,
            "plans": [],
        }
        self.assertEqual(classify_empty_plan(result), "T2C_PLAN_GAP")
        receipt = validate_plan_result(self.request, result)
        self.assertIn("T2C_PLAN_GAP", {item["code"] for item in receipt["findings"]})

    def test_grounded_plan_is_accepted(self) -> None:
        result = load_json(ROOT / "examples" / "todo2code-valid-plan.json")
        receipt = validate_plan_result(self.request, result)
        self.assertEqual(receipt["finalOutcome"], "PASS")
        self.assertEqual(receipt["recordCount"], 2)
        self.assertFalse(receipt["findings"])

    def test_duplicate_home_becomes_blocking_finding(self) -> None:
        registry = copy.deepcopy(self.registry)
        duplicate = copy.deepcopy(next(item for item in registry["spec"]["projects"] if item["id"] == "subactor/brand"))
        duplicate["id"] = "subactor/brand-copy"
        duplicate["repository"] = "brand-copy"
        duplicate["homeFor"] = ["commercial-offer-values"]
        duplicate["evidence"] = {"sourceClass": "documentation", "documents": ["test"]}
        registry["spec"]["projects"].append(duplicate)
        result = build_ecosystem_map(registry, {})
        codes = {item["code"] for item in result["findings"]}
        self.assertIn("REGISTRY_DUPLICATE_HOME", codes)
        self.assertEqual(result["status"], "BLOCK")

    def test_llms_index_marks_documentation_boundary(self) -> None:
        text = render_llms_index(self.ecosystem_map)
        self.assertIn("Documentation-only tools may inform a ticket but cannot authorize execution", text)
        self.assertIn("semcod/giton | evidence=DOCUMENTED | execution=false", text)
        self.assertIn("semcod/pyqual | evidence=VERIFIED | execution=true", text)


if __name__ == "__main__":
    unittest.main()
