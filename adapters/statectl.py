#!/usr/bin/env python3
"""Project indexed evidence into an Evolutionary Priority DSL state.

This adapter deliberately separates structural evidence from behavioral receipts.
A TOON map can prove that a module or symbol was indexed; it cannot prove an
offer digest check, a test outcome, or production behavior.  Metrics whose
required behavioral receipt is absent remain missing and therefore fail closed
in ``standardctl``.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Mapping

import yaml

Json = dict[str, Any]


class StateProjectionError(RuntimeError):
    pass


def stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(stable_json(value).encode("utf-8")).hexdigest()


def load_json(path: Path) -> Json:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise StateProjectionError(f"{path} must contain an object")
    return value


def load_yaml(path: Path) -> Json:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise StateProjectionError(f"{path} must contain an object")
    return value


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def metric(value: Any, observed_at: str, source_class: str, revision: str, evidence_digest: str) -> Json:
    return {
        "value": value,
        "observedAt": observed_at,
        "sourceClass": source_class,
        "revision": revision,
        "evidenceDigest": evidence_digest,
    }


_DERIVED_METRICS = {
    "governance.duplicate_home_count",
    "planning.unverified_tool_selection_count",
    "planning.todo2code_plan_gap_count",
    "routing.required_capability_gap_count",
    "routing.context_selection_coverage",
    "registry.unverified_required_project_count",
    "registry.manifest_coverage",
    "offer.facade_digest_mismatch_count",
    "offer.duplicate_price_source_count",
    "offer.catalog_binding_coverage",
}


def _route_metrics(route: Json, ecosystem_map: Json) -> dict[str, Any]:
    selected = {item["id"]: item for item in route.get("selectedProjects", []) if isinstance(item, Mapping)}
    assignments = route.get("roleAssignment", {})
    total = len(assignments) if isinstance(assignments, Mapping) else 0
    verified = 0
    if isinstance(assignments, Mapping):
        for project_id in assignments.values():
            project = selected.get(str(project_id))
            if project and project.get("executionEligible") is True:
                verified += 1
    coverage = 1.0 if total == 0 else verified / total
    blocking_codes = {
        "ROUTER_REQUIRED_ROLE_MISSING",
        "ROUTER_HOME_MISSING",
        "ROUTER_HOME_AMBIGUOUS",
        "ROUTER_REQUIRED_ROLE_NOT_EXECUTION_VERIFIED",
        "ROUTER_MAX_PROJECTS_TOO_LOW",
        "ROUTER_SEPARATION_OF_DUTIES_VIOLATION",
    }
    findings = [item for item in route.get("findings", []) if isinstance(item, Mapping)]
    gap_count = sum(1 for item in findings if item.get("code") in blocking_codes)
    unverified_count = sum(
        1 for item in findings if item.get("code") == "ROUTER_REQUIRED_ROLE_NOT_EXECUTION_VERIFIED"
    )
    return {
        "planning.unverified_tool_selection_count": unverified_count,
        "routing.required_capability_gap_count": gap_count,
        "routing.context_selection_coverage": round(coverage, 4),
    }


def _offer_structural_metrics(ecosystem_map: Json) -> dict[str, Any]:
    owners = ecosystem_map.get("homeOwners", {}).get("commercial-offer-values", [])
    owner_count = len(owners) if isinstance(owners, list) else 0
    duplicate_count = max(0, owner_count - 1) if owner_count else 1
    project = next(
        (item for item in ecosystem_map.get("projects", []) if item.get("id") == "subactor/offer"),
        None,
    )
    coverage: float | None = None
    if isinstance(project, Mapping):
        checks = [
            item
            for item in project.get("evidence", {}).get("moduleChecks", [])
            if isinstance(item, Mapping)
            and ("/catalogs/" in str(item.get("path")) or "/bindings/" in str(item.get("path")))
        ]
        if checks:
            coverage = sum(1 for item in checks if item.get("present") is True) / len(checks)
    result: dict[str, Any] = {"offer.duplicate_price_source_count": duplicate_count}
    if coverage is not None:
        result["offer.catalog_binding_coverage"] = round(coverage, 4)
    return result


def project_state(
    policy: Json,
    ecosystem_map: Json,
    revision: str,
    observed_at: str,
    *,
    base_state: Json | None = None,
    route: Json | None = None,
    planner_receipt: Json | None = None,
    offer_receipt: Json | None = None,
) -> Json:
    state: Json = copy.deepcopy(base_state) if base_state else {
        "schema": "wellmanifest.priority-state/v1alpha1",
        "metrics": {},
        "facts": {},
    }
    state["revision"] = revision
    state.setdefault("metrics", {})
    state.setdefault("facts", {})
    for metric_id in _DERIVED_METRICS:
        state["metrics"].pop(metric_id, None)

    map_digest = str(ecosystem_map.get("ecosystemMapDigest") or digest(ecosystem_map))
    map_values = {
        "governance.duplicate_home_count": int(ecosystem_map.get("metrics", {}).get("duplicateHomeCount", 0)),
        "registry.unverified_required_project_count": sum(
            1
            for project in ecosystem_map.get("projects", [])
            if project.get("required") is True and project.get("evidence", {}).get("status") != "VERIFIED"
        ),
        "registry.manifest_coverage": ecosystem_map.get("metrics", {}).get("manifestCoverage"),
        **_offer_structural_metrics(ecosystem_map),
    }
    for metric_id, value in map_values.items():
        if value is not None:
            state["metrics"][metric_id] = metric(value, observed_at, "git_ast", revision, map_digest)

    provenance: list[Json] = [{"kind": "ecosystem-map", "digest": map_digest}]
    if route is not None:
        route_digest = str(route.get("contextDigest") or digest(route))
        for metric_id, value in _route_metrics(route, ecosystem_map).items():
            state["metrics"][metric_id] = metric(value, observed_at, "runtime_receipt", revision, route_digest)
        provenance.append({"kind": "context-selection", "digest": route_digest, "status": route.get("status")})

    if planner_receipt is not None:
        planner_digest = str(planner_receipt.get("receiptDigest") or digest(planner_receipt))
        plan_gap_count = sum(
            1
            for finding in planner_receipt.get("findings", [])
            if isinstance(finding, Mapping) and finding.get("code") == "T2C_PLAN_GAP"
        )
        state["metrics"]["planning.todo2code_plan_gap_count"] = metric(
            plan_gap_count, observed_at, "test_receipt", revision, planner_digest
        )
        provenance.append({"kind": "planner-validation", "digest": planner_digest, "status": planner_receipt.get("finalOutcome")})

    if offer_receipt is not None:
        offer_digest = str(offer_receipt.get("receiptDigest") or digest(offer_receipt))
        receipt_revision = offer_receipt.get("revision")
        if receipt_revision and receipt_revision != revision:
            raise StateProjectionError(
                f"offer receipt revision {receipt_revision!r} does not match state revision {revision!r}"
            )
        values = {
            "offer.facade_digest_mismatch_count": offer_receipt.get("facadeDigestMismatchCount"),
            "offer.duplicate_price_source_count": offer_receipt.get("duplicatePriceSourceCount"),
            "offer.catalog_binding_coverage": offer_receipt.get("catalogBindingCoverage"),
        }
        for metric_id, value in values.items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                state["metrics"][metric_id] = metric(value, observed_at, "test_receipt", revision, offer_digest)
        provenance.append({"kind": "offer-pin", "digest": offer_digest, "status": offer_receipt.get("status")})

    defined = {item["id"] for item in policy["spec"]["metrics"]}
    observed = set(state["metrics"])
    state["projection"] = {
        "schema": "subactor.priority-state-projection/v1",
        "generatedAt": observed_at,
        "policyId": policy["metadata"]["id"],
        "policyVersion": policy["metadata"]["version"],
        "missingMetrics": sorted(defined - observed),
        "unknownMetrics": sorted(observed - defined),
        "provenance": provenance,
    }
    state["projection"]["projectionDigest"] = digest(state["projection"])
    return state


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    root.add_argument("--policy", required=True)
    root.add_argument("--ecosystem-map", required=True)
    root.add_argument("--route")
    root.add_argument("--planner-receipt")
    root.add_argument("--offer-receipt")
    root.add_argument("--base-state")
    root.add_argument("--revision", required=True)
    root.add_argument("--observed-at", required=True)
    root.add_argument("--out", required=True)
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        policy = load_yaml(Path(args.policy))
        ecosystem_map = load_json(Path(args.ecosystem_map))
        state = project_state(
            policy,
            ecosystem_map,
            args.revision,
            args.observed_at,
            base_state=load_json(Path(args.base_state)) if args.base_state else None,
            route=load_json(Path(args.route)) if args.route else None,
            planner_receipt=load_json(Path(args.planner_receipt)) if args.planner_receipt else None,
            offer_receipt=load_json(Path(args.offer_receipt)) if args.offer_receipt else None,
        )
        write_json(Path(args.out), state)
        missing = state["projection"]["missingMetrics"]
        print(json.dumps({
            "status": "PASS" if not missing else "REVIEW_REQUIRED",
            "missingMetricCount": len(missing),
            "missingMetrics": missing,
            "projectionDigest": state["projection"]["projectionDigest"],
            "out": args.out,
        }, ensure_ascii=False, indent=2))
        return 0 if not missing else 3
    except (OSError, ValueError, KeyError, StateProjectionError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
