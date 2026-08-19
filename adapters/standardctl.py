#!/usr/bin/env python3
"""Deterministic reference evaluator for wellmanifest EvolutionaryIntentPolicy.

This is intentionally a small reference implementation. It does not execute URI
operations. It validates policy/state, computes lexicographic priorities,
classifies implementation-vs-standard repair, checks complementarity, emits a
hash-bound receipt, and compiles model-specific instruction facades.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

import jsonschema
import yaml

Json = dict[str, Any]


class PolicyError(RuntimeError):
    pass


def load_yaml(path: Path) -> Json:
    with path.open("r", encoding="utf-8") as handle:
        value = yaml.safe_load(handle)
    if not isinstance(value, dict):
        raise PolicyError(f"{path} must contain an object")
    return value


def load_json(path: Path) -> Json:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise PolicyError(f"{path} must contain an object")
    return value


def stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(stable_json(value).encode("utf-8")).hexdigest()


def parse_time(value: str) -> datetime:
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def get_path(value: Mapping[str, Any], dotted: str) -> Any:
    current: Any = value
    for part in dotted.split("."):
        if not isinstance(current, Mapping) or part not in current:
            return None
        current = current[part]
    return current


def compare(actual: Any, op: str, expected: Any) -> bool:
    if op == "eq":
        return actual == expected
    if op == "ne":
        return actual != expected
    if actual is None:
        return False
    if op == "gt":
        return actual > expected
    if op == "gte":
        return actual >= expected
    if op == "lt":
        return actual < expected
    if op == "lte":
        return actual <= expected
    if op == "in":
        return actual in expected
    if op == "not_in":
        return actual not in expected
    if op == "matches_any":
        values = actual if isinstance(actual, list) else [actual]
        patterns = expected if isinstance(expected, list) else [expected]
        return any(fnmatch.fnmatch(str(item), str(pattern)) for item in values for pattern in patterns)
    raise PolicyError(f"Unsupported operator: {op}")


def metric_value(state: Json, metric_id: str) -> Any:
    item = state.get("metrics", {}).get(metric_id)
    return item.get("value") if isinstance(item, dict) else None


def evaluate_condition(condition: Json, state: Json) -> bool:
    if "all" in condition:
        return all(evaluate_condition(item, state) for item in condition["all"])
    if "any" in condition:
        return any(evaluate_condition(item, state) for item in condition["any"])
    if "not" in condition:
        return not evaluate_condition(condition["not"], state)
    if "metric" in condition:
        actual = metric_value(state, condition["metric"])
        return compare(actual, condition["op"], condition["value"])
    if "fact" in condition:
        actual = get_path(state.get("facts", {}), condition["fact"])
        return compare(actual, condition["op"], condition["value"])
    raise PolicyError(f"Invalid condition: {condition!r}")


def referenced_metrics(condition: Json) -> set[str]:
    if "metric" in condition:
        return {condition["metric"]}
    if "all" in condition:
        return set().union(*(referenced_metrics(item) for item in condition["all"]))
    if "any" in condition:
        return set().union(*(referenced_metrics(item) for item in condition["any"]))
    if "not" in condition:
        return referenced_metrics(condition["not"])
    return set()


def metric_freshness(policy: Json, state: Json, now: datetime) -> dict[str, Json]:
    definitions = {item["id"]: item for item in policy["spec"]["metrics"]}
    source_ranks = {item["id"]: item["rank"] for item in policy["spec"]["sourcePolicy"]["classes"]}
    output: dict[str, Json] = {}
    state_revision = state.get("revision")
    for metric_id, definition in definitions.items():
        observed = state.get("metrics", {}).get(metric_id)
        if not isinstance(observed, dict):
            output[metric_id] = {"status": "MISSING", "fresh": False, "reason": "metric not observed"}
            continue
        try:
            observed_at = parse_time(str(observed["observedAt"]))
            age = max(0.0, (now - observed_at).total_seconds())
        except (KeyError, ValueError, TypeError) as exc:
            output[metric_id] = {"status": "INVALID", "fresh": False, "reason": str(exc)}
            continue
        source_class = observed.get("sourceClass")
        source_rank = source_ranks.get(source_class, -1)
        required_classes = set(definition.get("requiredSourceClasses", []))
        source_allowed = source_class in required_classes
        revision_matches = not observed.get("revision") or not state_revision or observed.get("revision") == state_revision
        fresh = age <= definition["maxAgeSeconds"] and source_allowed and revision_matches
        output[metric_id] = {
            "status": "FRESH" if fresh else "STALE_OR_UNTRUSTED",
            "fresh": fresh,
            "ageSeconds": round(age, 3),
            "sourceClass": source_class,
            "sourceRank": source_rank,
            "sourceAllowed": source_allowed,
            "revisionMatches": revision_matches,
            "value": observed.get("value"),
        }
    return output


def validate_semantics(policy: Json) -> list[str]:
    errors: list[str] = []
    spec = policy["spec"]
    class_ids = {item["id"] for item in spec["priorityClasses"]}
    metric_ids = {item["id"] for item in spec["metrics"]}
    intent_ids = {item["id"] for item in spec["intents"]}
    if len(class_ids) != len(spec["priorityClasses"]):
        errors.append("priorityClasses IDs must be unique")
    if len(metric_ids) != len(spec["metrics"]):
        errors.append("metric IDs must be unique")
    if len(intent_ids) != len(spec["intents"]):
        errors.append("intent IDs must be unique")

    for invariant in spec["globalInvariants"]:
        unknown = referenced_metrics(invariant["when"]) - metric_ids
        if unknown:
            errors.append(f"{invariant['id']} references unknown metrics: {sorted(unknown)}")

    for intent in spec["intents"]:
        if intent["priority"]["class"] not in class_ids:
            errors.append(f"{intent['id']} references unknown priority class")
        if intent["priority"]["dispatchFloorWhenViolated"] > intent["priority"]["dispatchCeiling"]:
            errors.append(f"{intent['id']} dispatch floor exceeds ceiling")
        unknown = referenced_metrics(intent["violationWhen"]) - metric_ids
        for rule in intent["adaptation"]["rules"]:
            unknown |= referenced_metrics(rule["when"]) - metric_ids
        standard = intent["repairPolicy"]["standard"]
        if standard["mode"] != "disabled":
            unknown |= referenced_metrics(standard["trigger"]) - metric_ids
        if unknown:
            errors.append(f"{intent['id']} references unknown metrics: {sorted(unknown)}")
        relations = intent["relations"]
        relation_ids = set(relations["requires"] + relations["reinforces"] + relations["enables"] + relations["excludes"])
        missing = relation_ids - intent_ids
        if missing:
            errors.append(f"{intent['id']} references unknown intents: {sorted(missing)}")
        if intent["id"] in relation_ids:
            errors.append(f"{intent['id']} cannot relate to itself")

    dependency_graph = {intent["id"]: set(intent["relations"]["requires"]) for intent in spec["intents"]}
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str, trail: list[str]) -> None:
        if node in visited:
            return
        if node in visiting:
            start = trail.index(node) if node in trail else 0
            cycle = trail[start:] + [node]
            errors.append(f"dependency cycle: {' -> '.join(cycle)}")
            return
        visiting.add(node)
        for dependency in sorted(dependency_graph.get(node, set())):
            if dependency in dependency_graph:
                visit(dependency, trail + [node])
        visiting.remove(node)
        visited.add(node)

    for node in sorted(dependency_graph):
        visit(node, [])
    return errors


@dataclass(frozen=True)
class Decision:
    intent_id: str
    priority_class: str
    class_rank: int
    importance: float
    dispatch_urgency: float
    violated: bool
    evidence_status: str
    outcome: str
    reasons: tuple[str, ...]
    actions: tuple[Json, ...]
    expected_effects: Mapping[str, str]
    relations: Mapping[str, list[str]]

    def as_json(self) -> Json:
        return {
            "intentId": self.intent_id,
            "priorityClass": self.priority_class,
            "classRank": self.class_rank,
            "importance": self.importance,
            "dispatchUrgency": self.dispatch_urgency,
            "violated": self.violated,
            "evidenceStatus": self.evidence_status,
            "outcome": self.outcome,
            "reasons": list(self.reasons),
            "actions": list(self.actions),
            "expectedEffects": dict(self.expected_effects),
            "relations": dict(self.relations),
        }


def intent_evidence_status(intent: Json, freshness: Mapping[str, Json]) -> tuple[str, list[str]]:
    metric_ids = referenced_metrics(intent["violationWhen"])
    for rule in intent["adaptation"]["rules"]:
        metric_ids |= referenced_metrics(rule["when"])
    standard = intent["repairPolicy"]["standard"]
    if standard["mode"] != "disabled":
        metric_ids |= referenced_metrics(standard["trigger"])
    if not metric_ids:
        return "FRESH", []

    minimum_rank = float(intent["evidence"].get("minimumSourceRank", 0))
    unusable: list[str] = []
    for metric_id in sorted(metric_ids):
        item = freshness.get(metric_id, {})
        if not item.get("fresh", False):
            unusable.append(metric_id)
            continue
        if float(item.get("sourceRank", -1)) < minimum_rank:
            unusable.append(metric_id)
    if unusable:
        return "MISSING_OR_STALE", unusable
    return "FRESH", []


def build_decisions(policy: Json, state: Json, freshness: Mapping[str, Json]) -> list[Decision]:
    classes = {item["id"]: item for item in policy["spec"]["priorityClasses"]}
    decisions: list[Decision] = []
    for intent in policy["spec"]["intents"]:
        if intent["lifecycle"] not in {"active", "canary", "shadow"}:
            continue
        priority = intent["priority"]
        class_def = classes[priority["class"]]
        evidence_status, stale_metrics = intent_evidence_status(intent, freshness)
        reasons: list[str] = []
        actions: list[Json] = []

        violated = evaluate_condition(intent["violationWhen"], state)
        urgency = float(priority["dispatchBase"])
        for rule in intent["adaptation"]["rules"]:
            if evaluate_condition(rule["when"], state):
                urgency += float(rule["dispatchDelta"])
                reasons.append(f"{rule['id']}: {rule['reason']}")

        if violated:
            urgency = max(urgency, float(priority["dispatchFloorWhenViolated"]))
        urgency = min(max(0.0, urgency), float(priority["dispatchCeiling"]))

        if evidence_status != "FRESH":
            on_missing = intent["evidence"]["onMissing"]
            outcome = on_missing
            reasons.append(f"Brak świeżych dowodów: {', '.join(stale_metrics)}")
            actions.append({"type": "REFRESH_EVIDENCE", "uri": policy["spec"]["routing"]["evidenceObserver"], "metrics": stale_metrics})
        elif violated:
            standard = intent["repairPolicy"]["standard"]
            standard_defect = standard["mode"] != "disabled" and evaluate_condition(standard["trigger"], state)
            if standard_defect:
                outcome = "PROPOSE_STANDARD_CHANGE"
                reasons.append("Metryki wskazują możliwy błąd lub nadmierną restrykcyjność standardu.")
                actions.append({
                    "type": "PROPOSE_STANDARD_CHANGE",
                    "uri": standard["proposalUri"],
                    "lifecycle": standard["promotion"],
                    "requiresHumanRoles": standard["requiresHumanRoles"],
                })
            else:
                implementation = intent["repairPolicy"]["implementation"]
                outcome = "REPAIR_IMPLEMENTATION"
                actions.extend([
                    {"type": "PLAN", "uri": implementation["plannerUri"]},
                    {"type": "EXECUTE", "uri": implementation["executorUri"], "maxAttempts": implementation["maxAttempts"]},
                    {"type": "VALIDATE", "uri": implementation["validatorUri"]},
                ])
        else:
            outcome = "PASS"
            reasons.append("Brak aktywnego naruszenia przy świeżych dowodach.")

        decisions.append(Decision(
            intent_id=intent["id"],
            priority_class=priority["class"],
            class_rank=int(class_def["rank"]),
            importance=float(priority["importance"]),
            dispatch_urgency=round(urgency, 3),
            violated=violated,
            evidence_status=evidence_status,
            outcome=outcome,
            reasons=tuple(reasons),
            actions=tuple(actions),
            expected_effects=intent["expectedEffects"],
            relations=intent["relations"],
        ))
    return sorted(decisions, key=lambda item: (item.class_rank, -item.dispatch_urgency, -item.importance, item.intent_id))


def global_invariants(policy: Json, state: Json, freshness: Mapping[str, Json]) -> list[Json]:
    findings: list[Json] = []
    for invariant in policy["spec"]["globalInvariants"]:
        metrics = referenced_metrics(invariant["when"])
        stale = [metric for metric in metrics if not freshness.get(metric, {}).get("fresh", False)]
        triggered = evaluate_condition(invariant["when"], state)
        if stale:
            findings.append({
                "id": invariant["id"],
                "status": "UNKNOWN",
                "outcome": "BLOCK",
                "reason": f"Invariant cannot be proven because evidence is stale: {sorted(stale)}",
                "remediationUri": "uri://twin/receipts/refresh",
            })
        elif triggered:
            findings.append({
                "id": invariant["id"],
                "status": "VIOLATED",
                "outcome": invariant["outcome"],
                "reason": invariant["statement"],
                "remediationUri": invariant["remediationUri"],
            })
        else:
            findings.append({"id": invariant["id"], "status": "PASS", "outcome": "PASS"})
    return findings


def complementarity(policy: Json, decisions: list[Decision], state: Json) -> Json:
    config = policy["spec"]["complementarity"]
    weights = config["weights"]
    by_id = {decision.intent_id: decision for decision in decisions}
    actionable = [decision for decision in decisions if decision.actions]
    actionable_ids = {decision.intent_id for decision in actionable}
    findings: list[Json] = []
    raw_score = 0.0
    possible_positive = 0.0

    # Dependency edges are dependency -> dependent. They are later used for a
    # deterministic topological order; a cycle is a hard conflict.
    edges: dict[str, set[str]] = {intent_id: set() for intent_id in actionable_ids}
    indegree: dict[str, int] = {intent_id: 0 for intent_id in actionable_ids}

    for decision in actionable:
        for required in decision.relations.get("requires", []):
            possible_positive += max(0.0, float(weights.get("dependencySatisfied", 1.0)))
            target = by_id.get(required)
            if target is None:
                raw_score += float(weights.get("explicitConflict", -5.0))
                findings.append({"type": "MISSING_DEPENDENCY", "left": decision.intent_id, "right": required})
            elif required in actionable_ids:
                raw_score += float(weights.get("dependencySatisfied", 1.0))
                if decision.intent_id not in edges[required]:
                    edges[required].add(decision.intent_id)
                    indegree[decision.intent_id] += 1
                findings.append({
                    "type": "SEQUENCING_REQUIRED",
                    "before": required,
                    "after": decision.intent_id,
                    "reason": "The required intent also has pending remediation.",
                })
            elif target.outcome in {"BLOCK", "REVIEW_REQUIRED", "NOT_MEASURED"}:
                raw_score += float(weights.get("explicitConflict", -5.0))
                findings.append({
                    "type": "BLOCKED_DEPENDENCY",
                    "left": decision.intent_id,
                    "right": required,
                    "rightOutcome": target.outcome,
                })
            else:
                raw_score += float(weights.get("dependencySatisfied", 1.0))

        for target_id in decision.relations.get("reinforces", []):
            possible_positive += max(0.0, float(weights.get("reinforces", 2.0)))
            if target_id in by_id:
                raw_score += float(weights.get("reinforces", 2.0))
        for target_id in decision.relations.get("enables", []):
            possible_positive += max(0.0, float(weights.get("enables", 1.5)))
            if target_id in by_id:
                raw_score += float(weights.get("enables", 1.5))
        for target_id in decision.relations.get("excludes", []):
            if target_id in actionable_ids:
                raw_score += float(weights.get("explicitConflict", -5.0))
                findings.append({"type": "EXPLICIT_EXCLUSION", "left": decision.intent_id, "right": target_id})

    seen_pairs: set[tuple[str, str, str]] = set()
    for index, left in enumerate(actionable):
        for right in actionable[index + 1:]:
            shared = set(left.expected_effects) & set(right.expected_effects)
            for metric in shared:
                pair = tuple(sorted((left.intent_id, right.intent_id))) + (metric,)
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)
                a = left.expected_effects[metric]
                b = right.expected_effects[metric]
                if {a, b} == {"increase", "decrease"}:
                    raw_score += float(weights.get("oppositeMetricEffect", -3.0))
                    findings.append({
                        "type": "OPPOSITE_METRIC_EFFECT",
                        "left": left.intent_id,
                        "right": right.intent_id,
                        "metric": metric,
                        "effects": [a, b],
                    })

    # Stable topological sorting follows the already lexicographic priority order.
    order_index = {decision.intent_id: index for index, decision in enumerate(decisions)}
    queue = sorted((node for node, degree in indegree.items() if degree == 0), key=lambda node: order_index[node])
    sequential_order: list[str] = []
    while queue:
        node = queue.pop(0)
        sequential_order.append(node)
        for dependent in sorted(edges[node], key=lambda item: order_index[item]):
            indegree[dependent] -= 1
            if indegree[dependent] == 0:
                queue.append(dependent)
                queue.sort(key=lambda item: order_index[item])
    if len(sequential_order) != len(actionable_ids):
        cyclic = sorted(actionable_ids - set(sequential_order), key=lambda node: order_index[node])
        findings.append({"type": "DEPENDENCY_CYCLE", "intents": cyclic})
        sequential_order.extend(cyclic)

    budgets = policy["spec"]["budgets"]
    estimates = get_path(state.get("facts", {}), "planEstimates")
    estimates = estimates if isinstance(estimates, Mapping) else {}
    repairs = [item for item in actionable if item.outcome == "REPAIR_IMPLEMENTATION"]
    proposals = [item for item in actionable if item.outcome == "PROPOSE_STANDARD_CHANGE"]
    budget_report: Json = {
        "status": "PASS",
        "concurrentRepairs": len(repairs),
        "standardChangeProposals": len(proposals),
        "estimates": {},
    }
    if len(repairs) > int(budgets["concurrentRepairs"]):
        findings.append({
            "type": "BUDGET_OVERFLOW",
            "budget": "concurrentRepairs",
            "actual": len(repairs),
            "limit": budgets["concurrentRepairs"],
        })
    for decision in repairs:
        estimate = estimates.get(decision.intent_id)
        if not isinstance(estimate, Mapping):
            findings.append({"type": "BUDGET_NOT_MEASURED", "intentId": decision.intent_id})
            continue
        normalized_estimate = {
            "files": int(estimate.get("files", -1)),
            "changedLines": int(estimate.get("changedLines", -1)),
            "agentTurns": int(estimate.get("agentTurns", -1)),
        }
        budget_report["estimates"][decision.intent_id] = normalized_estimate
        for field, limit_key in (
            ("files", "maxFilesPerRepair"),
            ("changedLines", "maxChangedLinesPerRepair"),
            ("agentTurns", "maxAgentTurnsPerRepair"),
        ):
            actual = normalized_estimate[field]
            limit = int(budgets[limit_key])
            if actual < 0:
                findings.append({"type": "BUDGET_NOT_MEASURED", "intentId": decision.intent_id, "field": field})
            elif actual > limit:
                findings.append({
                    "type": "BUDGET_OVERFLOW",
                    "intentId": decision.intent_id,
                    "budget": limit_key,
                    "actual": actual,
                    "limit": limit,
                })
    proposals_today = get_path(state.get("facts", {}), "control.standardChangeProposalsToday")
    budget_report["standardChangeProposalsToday"] = proposals_today
    if proposals and not isinstance(proposals_today, int):
        findings.append({"type": "BUDGET_NOT_MEASURED", "budget": "standardChangeProposalsPerDay"})
    elif proposals and int(proposals_today) + len(proposals) > int(budgets["standardChangeProposalsPerDay"]):
        findings.append({
            "type": "BUDGET_OVERFLOW",
            "budget": "standardChangeProposalsPerDay",
            "actual": int(proposals_today) + len(proposals),
            "limit": budgets["standardChangeProposalsPerDay"],
        })

    budget_findings = [item for item in findings if item["type"] in {"BUDGET_OVERFLOW", "BUDGET_NOT_MEASURED"}]
    if budget_findings:
        budget_report["status"] = "BLOCK"
        raw_score += float(weights.get("budgetOverflow", -4.0)) * len(budget_findings)

    if not actionable:
        normalized = 1.0
    elif possible_positive > 0.0:
        # A plan that satisfies every declared positive relation should score
        # 1.0.  Negative weights are already applied to ``raw_score`` when a
        # concrete conflict is observed; reserving all possible negative weights
        # in the denominator made even a fully satisfied standalone delivery
        # plan unable to cross the automatic-dispatch threshold.
        normalized = max(0.0, min(1.0, raw_score / possible_positive))
    else:
        normalized = 1.0 if raw_score >= 0.0 else 0.0
    hard_types = {
        "MISSING_DEPENDENCY",
        "BLOCKED_DEPENDENCY",
        "EXPLICIT_EXCLUSION",
        "OPPOSITE_METRIC_EFFECT",
        "DEPENDENCY_CYCLE",
        "BUDGET_OVERFLOW",
        "BUDGET_NOT_MEASURED",
    }
    hard_conflict = any(item["type"] in hard_types for item in findings)
    threshold = float(config["minimumScoreForAutomaticDispatch"])
    has_dependency_edges = any(edges.values())
    allowed = not hard_conflict and normalized >= threshold
    return {
        "score": round(normalized, 4),
        "threshold": threshold,
        "hardConflict": hard_conflict,
        "parallelDispatchAllowed": allowed and not has_dependency_edges,
        "automaticSequentialDispatchAllowed": allowed,
        "automaticDispatchAllowed": allowed,
        "sequentialOrder": sequential_order,
        "budgetAssessment": budget_report,
        "findings": findings,
    }


def oscillation_guard(policy: Json, state: Json) -> Json:
    guard = policy["spec"]["changeControl"]["oscillationGuard"]
    count = get_path(state.get("facts", {}), "control.priorityChangesLastHour")
    if not isinstance(count, int):
        return {
            "status": "NOT_MEASURED",
            "outcome": "REVIEW_REQUIRED",
            "reason": "control.priorityChangesLastHour is missing",
            "limit": guard["maximumPriorityChangesPerHour"],
        }
    triggered = count > int(guard["maximumPriorityChangesPerHour"])
    return {
        "status": "TRIGGERED" if triggered else "PASS",
        "outcome": guard["outcome"] if triggered else "PASS",
        "priorityChangesLastHour": count,
        "limit": guard["maximumPriorityChangesPerHour"],
        "freezeSeconds": guard["freezeSecondsAfterLimit"] if triggered else 0,
    }


def evaluate(policy: Json, state: Json, now: datetime | None = None) -> Json:
    now = now or utc_now()
    freshness = metric_freshness(policy, state, now)
    invariants = global_invariants(policy, state, freshness)
    decisions = build_decisions(policy, state, freshness)
    comp = complementarity(policy, decisions, state)
    oscillation = oscillation_guard(policy, state)
    invariant_block = any(item["outcome"] == "BLOCK" and item["status"] != "PASS" for item in invariants)
    decision_block = any(item.outcome == "BLOCK" for item in decisions)
    review_required = any(item.outcome in {"REVIEW_REQUIRED", "NOT_MEASURED"} for item in decisions)
    has_actions = any(item.actions for item in decisions)
    oscillation_block = oscillation["status"] != "PASS" and oscillation["outcome"] == "BLOCK"
    oscillation_review = oscillation["status"] != "PASS" and oscillation["outcome"] == "REVIEW_REQUIRED"
    if invariant_block or decision_block or oscillation_block:
        final = "BLOCK"
    elif review_required or oscillation_review or not comp["automaticDispatchAllowed"]:
        final = "REVIEW_REQUIRED"
    elif has_actions:
        final = "ACTION_REQUIRED"
    else:
        final = "PASS"
    policy_lifecycle = policy["metadata"]["lifecycle"]
    lifecycle_allows_dispatch = policy_lifecycle == "active"
    dispatch_allowed = (
        final == "ACTION_REQUIRED"
        and comp["automaticSequentialDispatchAllowed"]
        and lifecycle_allows_dispatch
    )
    if dispatch_allowed:
        gate_reason = "gate-open"
    else:
        gate_reasons: list[str] = []
        if final != "ACTION_REQUIRED":
            gate_reasons.append(final.lower())
        if not lifecycle_allows_dispatch:
            gate_reasons.append(f"policy-lifecycle:{policy_lifecycle}")
        gate_reason = "gate-closed:" + ",".join(gate_reasons or ["not-authorized"])
    action_plan = []
    for decision in decisions:
        for action in decision.actions:
            action_plan.append({"intentId": decision.intent_id, "priorityClass": decision.priority_class, "dispatchUrgency": decision.dispatch_urgency, **action})
    receipt: Json = {
        "schema": "wellmanifest.priority-decision/v1alpha1",
        "generatedAt": iso(now),
        "policyId": policy["metadata"]["id"],
        "policyVersion": policy["metadata"]["version"],
        "policyLifecycle": policy_lifecycle,
        "policyDigest": digest(policy),
        "stateRevision": state.get("revision"),
        "stateDigest": digest(state),
        "finalOutcome": final,
        "executionGate": {
            "dispatchAllowed": dispatch_allowed,
            "parallelDispatchAllowed": dispatch_allowed and comp["parallelDispatchAllowed"],
            "reason": gate_reason,
        },
        "invariants": invariants,
        "oscillationGuard": oscillation,
        "metricFreshness": freshness,
        "decisions": [item.as_json() for item in decisions],
        "complementarity": comp,
        "planDelta": {
            "mode": "propose-only",
            "actions": action_plan,
        },
    }
    receipt["receiptDigest"] = digest(receipt)
    return receipt


def render_context(policy: Json, receipt: Json) -> str:
    classes = {item["id"]: item for item in policy["spec"]["priorityClasses"]}
    lines = [
        "# Generated evolutionary policy context",
        "",
        f"Policy: `{receipt['policyId']}` `{receipt['policyVersion']}`",
        f"Policy digest: `{receipt['policyDigest']}`",
        f"State revision: `{receipt.get('stateRevision')}`",
        f"Decision receipt: `{receipt['receiptDigest']}`",
        f"Final outcome: **{receipt['finalOutcome']}**",
        "",
        "## Non-negotiable operating order",
        "",
        "1. Read the active ticket, exact Git revision, HOME/ADOPT ownership and fresh receipts.",
        "2. Never treat a model claim, file name, function name or endpoint presence as behavioral proof.",
        "3. A higher priority class cannot be displaced by deadline, feature urgency, cost or model preference.",
        "4. Do not execute a plan when the receipt says BLOCK or REVIEW_REQUIRED.",
        "5. Standard changes are propose-only and must pass candidate → shadow → canary → active promotion.",
        "6. The implementer cannot validate or promote its own patch.",
        "7. Every code-changing step must cite its intentId, rule/evidence references and exact validation command or URI.",
        "",
        "## Current ordered priorities",
        "",
    ]
    for index, decision in enumerate(receipt["decisions"], start=1):
        class_def = classes[decision["priorityClass"]]
        lines.extend([
            f"{index}. **{decision['intentId']}** — class `{decision['priorityClass']}` (rank {class_def['rank']}), importance {decision['importance']}, dispatch {decision['dispatchUrgency']}",
            f"   - Outcome: `{decision['outcome']}`; violated: `{str(decision['violated']).lower()}`; evidence: `{decision['evidenceStatus']}`",
            f"   - Reasons: {'; '.join(decision['reasons'])}",
        ])
    lines.extend(["", "## Proposed actions (inert until the gate authorizes them)", ""])
    actions = receipt["planDelta"]["actions"]
    if not actions:
        lines.append("- No action is currently proposed.")
    else:
        for action in actions:
            lines.append(f"- `{action['intentId']}` / `{action['type']}` → `{action['uri']}`")
    lines.extend([
        "",
        "## Required response format for every agent",
        "",
        "Before editing, report: active intent IDs, blocking invariants, evidence freshness, selected repository/paths, and validation boundary.",
        "After editing, report: changed paths, receipt/revision, tests including at least one negative behavior test, remaining unknowns, and whether an independent validator accepted the exact patch hash.",
        "",
        "This file is generated. Do not edit it manually.",
    ])
    return "\n".join(lines) + "\n"


def compile_facades(policy: Json, receipt: Json, out_dir: Path) -> None:
    generated_dir = out_dir / ".wellmanifest" / "generated"
    generated_dir.mkdir(parents=True, exist_ok=True)
    context = render_context(policy, receipt)
    context_path = generated_dir / "agent-policy.md"
    context_path.write_text(context, encoding="utf-8")

    (out_dir / "AGENTS.md").write_text(
        "# Generated project instructions for Codex / ChatGPT coding agents\n\n" + context,
        encoding="utf-8",
    )
    (out_dir / "CLAUDE.md").write_text(
        "# Generated Claude Code project memory\n\n@.wellmanifest/generated/agent-policy.md\n",
        encoding="utf-8",
    )
    (out_dir / "GEMINI.md").write_text(
        "# Generated Gemini CLI project context\n\n@.wellmanifest/generated/agent-policy.md\n",
        encoding="utf-8",
    )


def cmd_validate(args: argparse.Namespace) -> int:
    policy = load_yaml(Path(args.policy))
    schema = load_json(Path(args.schema))
    jsonschema.Draft202012Validator(schema).validate(policy)
    semantic_errors = validate_semantics(policy)
    if semantic_errors:
        for error in semantic_errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 2
    print(json.dumps({"ok": True, "policyDigest": digest(policy), "intentCount": len(policy["spec"]["intents"])}, ensure_ascii=False, indent=2))
    return 0


def cmd_evaluate(args: argparse.Namespace) -> int:
    policy = load_yaml(Path(args.policy))
    state = load_json(Path(args.state))
    receipt = evaluate(policy, state, parse_time(args.now) if args.now else None)
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "finalOutcome": receipt["finalOutcome"],
        "receiptDigest": receipt["receiptDigest"],
        "complementarity": receipt["complementarity"],
        "out": str(output),
    }, ensure_ascii=False, indent=2))
    return 0 if receipt["finalOutcome"] == "PASS" else 3


def cmd_compile(args: argparse.Namespace) -> int:
    policy = load_yaml(Path(args.policy))
    receipt = load_json(Path(args.receipt))
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    compile_facades(policy, receipt, out_dir)
    print(json.dumps({"ok": True, "outDir": str(out_dir), "receiptDigest": receipt.get("receiptDigest")}, ensure_ascii=False, indent=2))
    return 0


def glob_matches(path: str, pattern: str) -> bool:
    return fnmatch.fnmatch(path, pattern) or (pattern.startswith("**/") and fnmatch.fnmatch(path, pattern[3:]))


def snapshot_mtimes(paths: Iterable[Path], patterns: list[str], excludes: list[str]) -> dict[str, int]:
    result: dict[str, int] = {}
    for root in paths:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            rel = path.relative_to(root).as_posix()
            if any(glob_matches(rel, pattern) for pattern in excludes):
                continue
            if patterns and not any(glob_matches(rel, pattern) or glob_matches(path.as_posix(), pattern) for pattern in patterns):
                continue
            try:
                result[str(path)] = path.stat().st_mtime_ns
            except FileNotFoundError:
                continue
    return result


def cmd_watch(args: argparse.Namespace) -> int:
    policy_path = Path(args.policy)
    state_path = Path(args.state)
    policy = load_yaml(policy_path)
    trigger = next((item for item in policy["spec"]["triggers"] if item["type"] == "fileWatch"), None)
    patterns = trigger.get("selectors", []) if trigger else []
    excludes = trigger.get("exclude", []) if trigger else []
    roots = [Path(value) for value in args.root]
    previous = snapshot_mtimes(roots, patterns, excludes)
    next_full = time.monotonic()
    print(json.dumps({"watching": [str(root) for root in roots], "patterns": patterns, "fullScanSeconds": args.full_scan_seconds}, ensure_ascii=False))
    while True:
        current = snapshot_mtimes(roots, patterns, excludes)
        changed = current != previous
        full_due = time.monotonic() >= next_full
        if changed or full_due:
            policy = load_yaml(policy_path)
            state = load_json(state_path)
            receipt = evaluate(policy, state)
            out = Path(args.out)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(json.dumps({"event": "evaluate", "reason": "file-change" if changed else "timer", "outcome": receipt["finalOutcome"], "receiptDigest": receipt["receiptDigest"]}, ensure_ascii=False), flush=True)
            previous = current
            next_full = time.monotonic() + args.full_scan_seconds
        time.sleep(args.poll_seconds)


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    sub = root.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate")
    validate.add_argument("--policy", required=True)
    validate.add_argument("--schema", required=True)
    validate.set_defaults(func=cmd_validate)

    evaluate_cmd = sub.add_parser("evaluate")
    evaluate_cmd.add_argument("--policy", required=True)
    evaluate_cmd.add_argument("--state", required=True)
    evaluate_cmd.add_argument("--out", required=True)
    evaluate_cmd.add_argument("--now", help="ISO-8601 timestamp used for deterministic tests")
    evaluate_cmd.set_defaults(func=cmd_evaluate)

    compile_cmd = sub.add_parser("compile-context")
    compile_cmd.add_argument("--policy", required=True)
    compile_cmd.add_argument("--receipt", required=True)
    compile_cmd.add_argument("--out-dir", required=True)
    compile_cmd.set_defaults(func=cmd_compile)

    watch = sub.add_parser("watch")
    watch.add_argument("--policy", required=True)
    watch.add_argument("--state", required=True)
    watch.add_argument("--out", required=True)
    watch.add_argument("--root", action="append", required=True)
    watch.add_argument("--poll-seconds", type=float, default=2.0)
    watch.add_argument("--full-scan-seconds", type=float, default=300.0)
    watch.set_defaults(func=cmd_watch)
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        return int(args.func(args))
    except (PolicyError, jsonschema.ValidationError, OSError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
