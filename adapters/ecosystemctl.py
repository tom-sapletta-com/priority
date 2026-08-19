#!/usr/bin/env python3
"""Deterministic ecosystem index, context router and planner-result gate.

The tool never invents repository capabilities.  It combines a versioned
organizational registry with evidence from code2llm TOON indexes.  Documentation-
only entries remain useful for planning context but are not execution-eligible
until an exact repository index or receipt is pinned.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

import jsonschema
import yaml

from toon_index import ToonIndex, diff_toon_indexes, parse_toon_index

Json = dict[str, Any]


class EcosystemError(RuntimeError):
    pass


def stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(stable_json(value).encode("utf-8")).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_yaml(path: Path) -> Json:
    with path.open("r", encoding="utf-8") as handle:
        value = yaml.safe_load(handle)
    if not isinstance(value, dict):
        raise EcosystemError(f"{path} must contain an object")
    return value


def load_json(path: Path) -> Json:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise EcosystemError(f"{path} must contain an object")
    return value


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def validate_document(document: Json, schema_path: Path) -> None:
    schema = load_json(schema_path)
    jsonschema.Draft202012Validator(schema).validate(document)


def parse_map_arguments(values: Iterable[str]) -> dict[str, ToonIndex]:
    result: dict[str, ToonIndex] = {}
    for value in values:
        if "=" not in value:
            raise EcosystemError(f"--map must use ORGANIZATION=PATH, got {value!r}")
        organization, raw_path = value.split("=", 1)
        organization = organization.strip()
        if not organization:
            raise EcosystemError("--map organization cannot be empty")
        index = parse_toon_index(Path(raw_path))
        if index.organization != "unknown" and index.organization != organization:
            raise EcosystemError(
                f"Map {raw_path} declares organization {index.organization!r}, expected {organization!r}"
            )
        result[organization] = index
    return result


DEFAULT_INDEX_FILES = (
    ("subactor", "sources/indexes/subactor-2026-08-19.toon.yaml"),
    ("autogrammar", "sources/indexes/autogrammar-2026-08-19.toon.yaml"),
    ("wellmanifest", "sources/indexes/wellmanifest-2026-08-16.toon.yaml"),
    ("pyqual", "sources/indexes/pyqual-2026-04-25.toon.yaml"),
)


def default_index_maps(root: Path) -> dict[str, ToonIndex]:
    pairs = [
        f"{organization}={root / relative}"
        for organization, relative in DEFAULT_INDEX_FILES
        if (root / relative).is_file()
    ]
    return parse_map_arguments(pairs)


def _project_index(project: Json, maps: Mapping[str, ToonIndex]) -> ToonIndex | None:
    organization = str(project["organization"])
    repository = str(project.get("repository", ""))
    return maps.get(organization) or maps.get(repository)


def _manifest_assessment(project: Json, index: ToonIndex | None, manifest_files: Mapping[str, Any]) -> Json:
    if index is None or not project.get("modulePrefix"):
        return {"status": "NOT_MEASURED", "coverage": None, "categories": {}}
    prefix = str(project["modulePrefix"])
    modules = index.modules_under(prefix)
    categories: Json = {}
    passed = 0
    for category, candidates_value in manifest_files.items():
        candidates = [str(item) for item in candidates_value]
        matches = sorted(
            module
            for module in modules
            if any(module == prefix + candidate or module.endswith("/" + candidate) for candidate in candidates)
        )
        categories[str(category)] = {"present": bool(matches), "matches": matches}
        if matches:
            passed += 1
    total = len(categories)
    coverage = 1.0 if total == 0 else passed / total
    return {
        "status": "PASS" if coverage == 1.0 else "DRIFT",
        "coverage": round(coverage, 4),
        "categories": categories,
    }


def _project_evidence(project: Json, maps: Mapping[str, ToonIndex], source_ranks: Mapping[str, Any], manifest_files: Mapping[str, Any]) -> Json:
    evidence = project["evidence"]
    source_class = str(evidence["sourceClass"])
    source_rank = int(source_ranks.get(source_class, -1))
    organization = str(project["organization"])
    index = _project_index(project, maps)
    required_modules = [str(item) for item in evidence.get("requiredModules", [])]
    required_symbols = evidence.get("requiredSymbols", [])

    module_checks: list[Json] = []
    symbol_checks: list[Json] = []
    observed_module_count = 0
    map_ref: Json | None = None
    if index is not None:
        prefix = str(project.get("modulePrefix", ""))
        observed_module_count = len(index.modules_under(prefix)) if prefix else 0
        map_ref = {
            "organization": index.organization,
            "path": str(index.path),
            "sha256": index.sha256,
            "generatedDate": index.generated_date,
            "declaredModuleCount": index.declared_module_count,
            "parsedModuleCount": len(index.modules),
        }
        module_checks = [{"path": path, "present": index.has_module(path)} for path in required_modules]
        for item in required_symbols:
            path = str(item["path"])
            for symbol in item["symbols"]:
                symbol_checks.append({"path": path, "symbol": str(symbol), "present": index.has_symbol(path, str(symbol))})

    checks = module_checks + symbol_checks
    passed = sum(1 for item in checks if item["present"])
    total = len(checks)
    coverage = 1.0 if total == 0 else passed / total

    if source_class in {"runtime_receipt", "test_receipt", "git_ast", "configuration"}:
        if index is None:
            status = "MISSING_MAP"
        elif observed_module_count == 0:
            status = "MISSING"
        elif coverage == 1.0:
            status = "VERIFIED"
        else:
            status = "PARTIAL"
    elif source_class == "documentation":
        status = "DOCUMENTED"
    else:
        status = "UNTRUSTED"

    execution_eligible = (
        status == "VERIFIED"
        and source_rank >= 70
        and project["lifecycle"] == "active"
    )
    return {
        "status": status,
        "sourceClass": source_class,
        "sourceRank": source_rank,
        "coverage": round(coverage, 4),
        "executionEligible": execution_eligible,
        "observedModuleCount": observed_module_count,
        "map": map_ref,
        "moduleChecks": module_checks,
        "symbolChecks": symbol_checks,
        "documents": evidence.get("documents", []),
        "note": evidence.get("note"),
        "manifest": _manifest_assessment(project, index, manifest_files),
    }


def build_ecosystem_map(registry: Json, maps: Mapping[str, ToonIndex], generated_at: str | None = None) -> Json:
    spec = registry["spec"]
    source_ranks = spec["sourceRanks"]
    manifest_files = spec["manifestFiles"]
    projects: list[Json] = []
    findings: list[Json] = []
    project_ids = {str(project["id"]) for project in spec["projects"]}
    home_owners: dict[str, list[str]] = {}

    for project in spec["projects"]:
        project_id = str(project["id"])
        evidence = _project_evidence(project, maps, source_ranks, manifest_files)
        for concern in project.get("homeFor", []):
            home_owners.setdefault(str(concern), []).append(project_id)
        for adopted in project.get("adopts", []):
            if adopted not in project_ids:
                findings.append({
                    "code": "REGISTRY_ADOPTION_TARGET_MISSING",
                    "severity": "error",
                    "projectId": project_id,
                    "target": adopted,
                })
        if project.get("required") and evidence["status"] in {"MISSING_MAP", "MISSING", "UNTRUSTED"}:
            findings.append({
                "code": "REGISTRY_REQUIRED_PROJECT_UNVERIFIED",
                "severity": "error",
                "projectId": project_id,
                "evidenceStatus": evidence["status"],
            })
        elif project.get("required") and evidence["status"] in {"PARTIAL", "DOCUMENTED"}:
            findings.append({
                "code": "REGISTRY_REQUIRED_PROJECT_REVIEW",
                "severity": "warning",
                "projectId": project_id,
                "evidenceStatus": evidence["status"],
            })
        projects.append({
            "id": project_id,
            "organization": project["organization"],
            "repository": project["repository"],
            "lifecycle": project["lifecycle"],
            "required": project["required"],
            "roles": project["roles"],
            "homeFor": project.get("homeFor", []),
            "adopts": project.get("adopts", []),
            "capabilities": project["capabilities"],
            "interfaces": project["interfaces"],
            "evidence": evidence,
        })

    for concern, owners in sorted(home_owners.items()):
        if len(owners) != 1:
            findings.append({
                "code": "REGISTRY_DUPLICATE_HOME",
                "severity": "critical",
                "concern": concern,
                "owners": sorted(owners),
            })

    critical = any(item["severity"] == "critical" for item in findings)
    errors = any(item["severity"] == "error" for item in findings)
    warnings = any(item["severity"] == "warning" for item in findings)
    if critical:
        status = "BLOCK"
    elif errors or warnings:
        status = "REVIEW_REQUIRED"
    else:
        status = "PASS"

    manifest_coverages = [
        project["evidence"]["manifest"]["coverage"]
        for project in projects
        if isinstance(project["evidence"]["manifest"]["coverage"], (int, float))
    ]
    map_document: Json = {
        "schema": "subactor.ecosystem-map/v1",
        "generatedAt": generated_at or utc_now(),
        "registryId": registry["metadata"]["id"],
        "registryVersion": registry["metadata"]["version"],
        "registryLifecycle": registry["metadata"]["lifecycle"],
        "registryHome": registry["metadata"]["home"],
        "registryDigest": digest(registry),
        "status": status,
        "sources": {
            organization: {
                "path": str(index.path),
                "sha256": index.sha256,
                "generatedDate": index.generated_date,
                "moduleCount": len(index.modules),
            }
            for organization, index in sorted(maps.items())
        },
        "metrics": {
            "projectCount": len(projects),
            "verifiedProjectCount": sum(1 for project in projects if project["evidence"]["status"] == "VERIFIED"),
            "documentedOnlyProjectCount": sum(1 for project in projects if project["evidence"]["status"] == "DOCUMENTED"),
            "executionEligibleProjectCount": sum(1 for project in projects if project["evidence"]["executionEligible"]),
            "duplicateHomeCount": sum(1 for owners in home_owners.values() if len(owners) != 1),
            "manifestCoverage": round(sum(manifest_coverages) / len(manifest_coverages), 4) if manifest_coverages else None,
        },
        "homeOwners": {concern: sorted(owners) for concern, owners in sorted(home_owners.items())},
        "projects": sorted(projects, key=lambda item: item["id"]),
        "findings": findings,
    }
    map_document["ecosystemMapDigest"] = digest(map_document)
    return map_document


def render_llms_index(ecosystem_map: Json) -> str:
    lines = [
        "# Subactor engineering ecosystem index",
        f"registry: {ecosystem_map['registryId']}@{ecosystem_map['registryVersion']}",
        f"registry_digest: {ecosystem_map['registryDigest']}",
        f"ecosystem_map_digest: {ecosystem_map['ecosystemMapDigest']}",
        f"status: {ecosystem_map['status']}",
        "",
        "Use roles and HOME ownership below. Documentation-only tools may inform a ticket but cannot authorize execution.",
        "",
    ]
    for project in ecosystem_map["projects"]:
        capabilities = ",".join(item["id"] for item in project["capabilities"])
        roles = ",".join(project["roles"])
        homes = ",".join(project["homeFor"]) or "-"
        interfaces = ",".join(f"{name}={uri}" for name, uri in sorted(project["interfaces"].items()))
        lines.append(
            f"- {project['id']} | evidence={project['evidence']['status']} | execution={str(project['evidence']['executionEligible']).lower()} | roles={roles} | home={homes} | capabilities={capabilities} | {interfaces}"
        )
    if ecosystem_map["findings"]:
        lines.extend(["", "findings:"])
        for finding in ecosystem_map["findings"]:
            lines.append("- " + stable_json(finding))
    return "\n".join(lines) + "\n"


_POLISH_SYNONYMS = {
    "agent": "agent",
    "agenta": "agent",
    "agenty": "agent",
    "kod": "code",
    "kodu": "code",
    "zmiana": "change",
    "zmiany": "change",
    "zmian": "change",
    "plan": "plan",
    "planu": "plan",
    "planow": "plan",
    "planowanie": "planning",
    "planowania": "planning",
    "narzedzie": "tool",
    "narzedzia": "tool",
    "projekt": "project",
    "projektu": "project",
    "projekty": "project",
    "projektow": "project",
    "repozytorium": "repository",
    "repozytoria": "repository",
    "mapa": "map",
    "mape": "map",
    "kontekst": "context",
    "kontekstu": "context",
    "wybor": "select",
    "wybrac": "select",
    "intencja": "intent",
    "intencji": "intent",
    "standard": "standard",
    "standardy": "standard",
    "standaryzacja": "standardization",
    "priorytet": "priority",
    "priorytety": "priority",
    "walidacja": "validation",
    "walidowac": "validate",
    "test": "test",
    "testy": "test",
    "commit": "commit",
    "oferta": "offer",
    "oferty": "offer",
    "cena": "price",
    "ceny": "price",
    "manifest": "manifest",
    "manifesty": "manifest",
    "naprawa": "repair",
    "naprawy": "repair",
    "wdrozenie": "execution",
    "wykonanie": "execution",
    "ticket": "ticket",
    "bilet": "ticket",
}


_LETTER_TRANSLATION = str.maketrans({
    "ł": "l",
    "Ł": "l",
})

_STOPWORDS = {
    "a", "an", "and", "as", "at", "be", "by", "for", "in", "of", "on", "or", "the", "to",
    "ale", "ani", "bez", "czy", "do", "i", "jak", "jako", "lub", "na", "nie", "od", "oraz",
    "po", "przy", "tak", "te", "ten", "to", "tu", "tym", "w", "we", "z", "za", "ze",
}

_SHORT_KEEP = {"api", "ast", "ci", "dsl", "git", "map", "nl", "ssot", "t2c", "uri"}


def _ascii_token(value: str) -> str:
    mapped = value.lower().translate(_LETTER_TRANSLATION)
    normalized = unicodedata.normalize("NFKD", mapped)
    return "".join(char for char in normalized if not unicodedata.combining(char))


def _keep_token(token: str) -> bool:
    if token in _STOPWORDS:
        return False
    if len(token) < 3:
        return token in _SHORT_KEEP
    return True


def tokenize(value: str) -> set[str]:
    raw = re.findall(r"[a-zA-Z0-9]+(?:-[a-zA-Z0-9]+)*", _ascii_token(value))
    result: set[str] = set()
    candidates: list[str] = []
    for token in raw:
        candidates.append(token)
        if "-" in token:
            candidates.extend(part for part in token.split("-") if part)
    for token in candidates:
        if not _keep_token(token):
            continue
        result.add(token)
        mapped = _POLISH_SYNONYMS.get(token)
        if mapped:
            result.add(mapped)
        if token.endswith("s") and len(token) > 4 and token.isascii() and not token.endswith("ss"):
            stem = token[:-1]
            if _keep_token(stem):
                result.add(stem)
    return result


def _request_text(request: Json) -> str:
    intent = request["intent"]
    values = [intent["summary"], intent["taskKind"]]
    for field in ("objectives", "constraints", "concerns", "tags"):
        values.extend(str(item) for item in intent.get(field, []))
    return "\n".join(values)


def route_ticket(ecosystem_map: Json, request: Json, generated_at: str | None = None) -> Json:
    tokens = tokenize(_request_text(request))
    required_roles = [str(item) for item in request["requiredRoles"]]
    concerns = [str(item) for item in request["intent"].get("concerns", [])]
    preferred = set(str(item) for item in request.get("preferredProjects", []))
    excluded = set(str(item) for item in request.get("excludedProjects", []))
    max_projects = int(request.get("maxProjects", 8))
    projects_by_id = {project["id"]: project for project in ecosystem_map["projects"]}
    scores: dict[str, float] = {}
    reasons: dict[str, list[str]] = {}

    for project in ecosystem_map["projects"]:
        project_id = project["id"]
        if project_id in excluded or project["lifecycle"] in {"deprecated", "superseded"}:
            continue
        score = 0.0
        project_reasons: list[str] = []
        matched_roles = sorted(set(required_roles) & set(project["roles"]))
        if matched_roles:
            score += 100.0 * len(matched_roles)
            project_reasons.append("required roles: " + ", ".join(matched_roles))
        matched_concerns = sorted(set(concerns) & set(project["homeFor"]))
        if matched_concerns:
            score += 80.0 * len(matched_concerns)
            project_reasons.append("HOME for: " + ", ".join(matched_concerns))
        for capability in project["capabilities"]:
            keywords = set(_ascii_token(str(item)) for item in capability["keywords"])
            matched = sorted(tokens & keywords)
            if matched:
                contribution = float(capability["weight"]) * min(3, len(matched))
                score += contribution
                project_reasons.append(f"{capability['id']}: {', '.join(matched)}")
        if project_id in preferred:
            score += 30.0
            project_reasons.append("preferred by ticket")
        evidence_status = project["evidence"]["status"]
        if evidence_status == "VERIFIED":
            score += 10.0
        elif evidence_status == "PARTIAL":
            score += 2.0
        if project["lifecycle"] == "active":
            score += 2.0
        scores[project_id] = score
        reasons[project_id] = project_reasons

    findings: list[Json] = []
    mandatory_ids: set[str] = set()
    role_assignment: dict[str, str] = {}
    for role in required_roles:
        candidates = [
            project
            for project in ecosystem_map["projects"]
            if role in project["roles"] and project["id"] not in excluded and project["lifecycle"] not in {"deprecated", "superseded"}
        ]
        if not candidates:
            findings.append({"code": "ROUTER_REQUIRED_ROLE_MISSING", "severity": "critical", "role": role})
            continue
        candidates.sort(key=lambda item: (-scores.get(item["id"], 0.0), item["id"]))
        selected = candidates[0]
        role_assignment[role] = selected["id"]
        mandatory_ids.add(selected["id"])

    for concern in concerns:
        owners = ecosystem_map.get("homeOwners", {}).get(concern, [])
        if len(owners) == 0:
            findings.append({"code": "ROUTER_HOME_MISSING", "severity": "error", "concern": concern})
        elif len(owners) > 1:
            findings.append({"code": "ROUTER_HOME_AMBIGUOUS", "severity": "critical", "concern": concern, "owners": owners})
        else:
            mandatory_ids.add(owners[0])

    selected_ids = set(mandatory_ids)
    ranked = sorted(scores, key=lambda project_id: (-scores[project_id], project_id))
    for project_id in ranked:
        if len(selected_ids) >= max_projects:
            break
        if scores[project_id] <= 2.0:
            continue
        selected_ids.add(project_id)

    # Never silently drop a mandatory project because maxProjects was set too low.
    if len(selected_ids) > max_projects:
        findings.append({
            "code": "ROUTER_MAX_PROJECTS_TOO_LOW",
            "severity": "error",
            "maxProjects": max_projects,
            "mandatoryProjectCount": len(selected_ids),
        })

    for role, project_id in role_assignment.items():
        project = projects_by_id[project_id]
        if not project["evidence"]["executionEligible"] and request["intent"]["taskKind"] != "research":
            findings.append({
                "code": "ROUTER_REQUIRED_ROLE_NOT_EXECUTION_VERIFIED",
                "severity": "warning",
                "role": role,
                "projectId": project_id,
                "evidenceStatus": project["evidence"]["status"],
            })

    planner = role_assignment.get("planner")
    executor = role_assignment.get("implementation-executor")
    validator = role_assignment.get("independent-validator")
    if validator and validator in {planner, executor}:
        findings.append({
            "code": "ROUTER_SEPARATION_OF_DUTIES_VIOLATION",
            "severity": "critical",
            "planner": planner,
            "executor": executor,
            "validator": validator,
        })

    critical = any(item["severity"] == "critical" for item in findings)
    review = any(item["severity"] in {"error", "warning"} for item in findings)
    status = "BLOCK" if critical else "REVIEW_REQUIRED" if review else "PASS"
    selected_projects: list[Json] = []
    for project_id in sorted(selected_ids, key=lambda item: (-scores.get(item, 0.0), item)):
        project = projects_by_id[project_id]
        selected_projects.append({
            "id": project_id,
            "score": round(scores.get(project_id, 0.0), 3),
            "reasons": reasons.get(project_id, []),
            "roles": project["roles"],
            "homeFor": project["homeFor"],
            "interfaces": project["interfaces"],
            "evidenceStatus": project["evidence"]["status"],
            "sourceRank": project["evidence"]["sourceRank"],
            "executionEligible": project["evidence"]["executionEligible"],
            "manifestStatus": project["evidence"]["manifest"]["status"],
        })

    result: Json = {
        "schema": "subactor.ticket-context-selection/v1",
        "generatedAt": generated_at or utc_now(),
        "ticketId": request["ticketId"],
        "requestDigest": digest(request),
        "ecosystemMapDigest": ecosystem_map["ecosystemMapDigest"],
        "status": status,
        "tokens": sorted(tokens),
        "roleAssignment": role_assignment,
        "selectedProjects": selected_projects,
        "excludedProjects": sorted(excluded),
        "findings": findings,
    }
    result["contextDigest"] = digest(result)
    return result


def render_ticket_context(request: Json, route: Json) -> str:
    lines = [
        f"# Context selection for {request['ticketId']}",
        "",
        f"Status: **{route['status']}**",
        f"Request digest: `{route['requestDigest']}`",
        f"Ecosystem map digest: `{route['ecosystemMapDigest']}`",
        f"Context digest: `{route['contextDigest']}`",
        "",
        "## Intent",
        "",
        request["intent"]["summary"],
        "",
        "## Selected repositories",
        "",
    ]
    for project in route["selectedProjects"]:
        lines.append(
            f"- `{project['id']}` — score {project['score']}; evidence `{project['evidenceStatus']}`; execution `{str(project['executionEligible']).lower()}`; reasons: {'; '.join(project['reasons']) or 'mandatory context'}"
        )
    lines.extend(["", "## Acceptance criteria", ""])
    for criterion in request["acceptanceCriteria"]:
        lines.append(f"- {criterion}")
    if route["findings"]:
        lines.extend(["", "## Fail-closed findings", ""])
        for finding in route["findings"]:
            lines.append(f"- `{finding['code']}` — {stable_json(finding)}")
    lines.extend([
        "",
        "The planner may use only the selected repositories as context. It must not infer completion from file or symbol presence and must emit a non-empty grounded plan while acceptance criteria remain open.",
    ])
    return "\n".join(lines) + "\n"


def create_planner_request(request: Json, route: Json) -> Json:
    planner_project = next(
        (project for project in route["selectedProjects"] if "planner" in project["roles"]),
        None,
    )
    planner_uri = None
    if planner_project is not None:
        planner_uri = planner_project["interfaces"].get("planCodeChange")
    result: Json = {
        "schema": "todo2code.grounded-planner-request/v1",
        "ticketId": request["ticketId"],
        "intent": request["intent"],
        "intentDigest": digest(request["intent"]),
        "contextDigest": route["contextDigest"],
        "planner": {
            "projectId": planner_project["id"] if planner_project else None,
            "uri": planner_uri,
            "evidenceStatus": planner_project["evidenceStatus"] if planner_project else "MISSING",
        },
        "repositories": [project["id"] for project in route["selectedProjects"]],
        "acceptanceCriteria": request["acceptanceCriteria"],
        "scopePolicy": {
            "selectedRepositoriesOnly": True,
            "requireExactPathsBeforeEdit": True,
            "allowPathInferenceOutsideSelectedRepositories": False,
            "requireWorkspacePreflight": True,
            "requireCurrentGitAndAstEvidence": True,
        },
        "planPolicy": {
            "onZeroPlansWhenOpenCriteria": "T2C_PLAN_GAP",
            "onZeroImplementationDiagnostics": "T2C_NO_IMPLEMENTATION_DIAGNOSTICS",
            "requireNegativeBehaviorTest": True,
            "requireValidationBoundary": True,
            "requireRollback": True,
            "shapeOnlyEvidenceAccepted": False,
        },
        "executionPolicy": {
            "mode": "propose-only",
            "requiresIndependentValidator": True,
            "routeStatusRequired": "PASS",
        },
    }
    result["plannerRequestDigest"] = digest(result)
    return result


def _plans_from_result(result: Json) -> tuple[list[Json], int]:
    raw = result.get("plans")
    if not isinstance(raw, list):
        raw = result.get("records")
    plans = [item for item in raw if isinstance(item, dict)] if isinstance(raw, list) else []
    record_count = result.get("recordCount")
    if not isinstance(record_count, int):
        record_count = len(plans)
    return plans, record_count


def _plan_paths(plan: Json) -> list[str]:
    values: list[str] = []
    for field in ("files", "paths"):
        raw = plan.get(field)
        if isinstance(raw, list):
            for item in raw:
                if isinstance(item, str):
                    values.append(item)
                elif isinstance(item, Mapping) and isinstance(item.get("path"), str):
                    values.append(str(item["path"]))
    changes = plan.get("changes")
    if isinstance(changes, list):
        for item in changes:
            if isinstance(item, Mapping) and isinstance(item.get("path"), str):
                values.append(str(item["path"]))
    return sorted(dict.fromkeys(values))


def _plan_acceptance(plan: Json) -> tuple[list[str], list[str]]:
    positive: list[str] = []
    negative: list[str] = []
    direct = plan.get("acceptanceCriteria")
    if isinstance(direct, list):
        positive.extend(str(item) for item in direct if isinstance(item, str))
    acceptance = plan.get("acceptance")
    if isinstance(acceptance, Mapping):
        for key in ("positive", "criteria"):
            raw = acceptance.get(key)
            if isinstance(raw, list):
                positive.extend(str(item) for item in raw if isinstance(item, str))
        raw_negative = acceptance.get("negative")
        if isinstance(raw_negative, list):
            negative.extend(str(item) for item in raw_negative if isinstance(item, str))
    direct_negative = plan.get("negativeTests")
    if isinstance(direct_negative, list):
        negative.extend(str(item) for item in direct_negative if isinstance(item, str))
    for criterion in positive:
        lowered = _ascii_token(criterion)
        if any(term in lowered for term in ("negative", "fail", "reject", "odrzuc", "blok", "nie przechodzi")):
            negative.append(criterion)
    return list(dict.fromkeys(positive)), list(dict.fromkeys(negative))


def _plan_validation(plan: Json) -> list[str]:
    values: list[str] = []
    for field in ("validation", "validationCommands", "tests"):
        raw = plan.get(field)
        if isinstance(raw, str):
            values.append(raw)
        elif isinstance(raw, list):
            for item in raw:
                if isinstance(item, str):
                    values.append(item)
                elif isinstance(item, Mapping):
                    command = item.get("command") or item.get("uri")
                    if isinstance(command, str):
                        values.append(command)
    return list(dict.fromkeys(values))


def classify_empty_plan(result: Json) -> str:
    """Why a succeeded planner returned zero plans.

    `todo2code` materialises plans only from `PLANNED_NOT_IMPLEMENTED` and
    `CHANGELOG_WITHOUT_IMPLEMENTATION`. `sourceDiagnosticCount` is that
    filtered count. A missing count fails closed as `T2C_PLAN_GAP`.
    """
    source = result.get("sourceDiagnosticCount")
    if source == 0:
        return "T2C_NO_IMPLEMENTATION_DIAGNOSTICS"
    if isinstance(source, int) and source > 0:
        return "T2C_PLAN_GAP"
    if result.get("code") == "T2C_NO_IMPLEMENTATION_DIAGNOSTICS":
        return "T2C_NO_IMPLEMENTATION_DIAGNOSTICS"
    return "T2C_PLAN_GAP"


def validate_plan_result(request: Json, result: Json, generated_at: str | None = None) -> Json:
    criteria = request.get("acceptanceCriteria", [])
    plans, record_count = _plans_from_result(result)
    findings: list[Json] = []
    status = result.get("status")
    if status == "not-run":
        findings.append({
            "code": result.get("code") or "T2C_PLANNER_NOT_RUN",
            "severity": "critical",
            "status": status,
            "message": result.get("message") or "Planner was not invoked; no grounded plan exists.",
        })
    elif status != "succeeded":
        findings.append({
            "code": "T2C_PLANNER_FAILED",
            "severity": "critical",
            "status": status,
        })
    if record_count != len(plans):
        findings.append({
            "code": "T2C_RECORD_COUNT_MISMATCH",
            "severity": "error",
            "recordCount": record_count,
            "parsedPlans": len(plans),
        })
    if status == "succeeded" and criteria and record_count == 0:
        code = classify_empty_plan(result)
        source = result.get("sourceDiagnosticCount")
        findings.append({
            "code": code,
            "severity": "critical",
            "acceptanceCriterionCount": len(criteria),
            "sourceDiagnosticCount": source if isinstance(source, int) else None,
            "message": (
                "Planner found no PLANNED_NOT_IMPLEMENTED or CHANGELOG_WITHOUT_IMPLEMENTATION diagnostics."
                if code == "T2C_NO_IMPLEMENTATION_DIAGNOSTICS"
                else "Planner emitted zero grounded code-change plans while acceptance criteria remain open."
            ),
        })
    normalized_plans: list[Json] = []
    for index, plan in enumerate(plans):
        plan_id = plan.get("id") or plan.get("planId") or f"plan-{index + 1}"
        paths = _plan_paths(plan)
        acceptance, negative = _plan_acceptance(plan)
        validation = _plan_validation(plan)
        if not paths:
            findings.append({"code": "T2C_PATH_GAP", "severity": "critical", "planId": plan_id})
        if not acceptance:
            findings.append({"code": "T2C_CRITERION_GAP", "severity": "error", "planId": plan_id})
        if not negative:
            findings.append({"code": "T2C_NEGATIVE_TEST_GAP", "severity": "error", "planId": plan_id})
        if not validation:
            findings.append({"code": "T2C_VALIDATION_GAP", "severity": "error", "planId": plan_id})
        normalized_plans.append({
            "planId": plan_id,
            "paths": paths,
            "acceptanceCriteria": acceptance,
            "negativeTests": negative,
            "validation": validation,
        })
    final = "PASS" if not findings else "BLOCK"
    receipt: Json = {
        "schema": "todo2code.plan-validation-receipt/v1",
        "generatedAt": generated_at or utc_now(),
        "ticketId": request.get("ticketId"),
        "requestDigest": digest(request),
        "plannerResultDigest": digest(result),
        "finalOutcome": final,
        "recordCount": record_count,
        "plans": normalized_plans,
        "findings": findings,
    }
    receipt["receiptDigest"] = digest(receipt)
    return receipt


def cmd_validate_registry(args: argparse.Namespace) -> int:
    registry = load_yaml(Path(args.registry))
    validate_document(registry, Path(args.schema))
    project_ids = [project["id"] for project in registry["spec"]["projects"]]
    if len(project_ids) != len(set(project_ids)):
        raise EcosystemError("Project IDs must be unique")
    print(json.dumps({"ok": True, "registryDigest": digest(registry), "projectCount": len(project_ids)}, ensure_ascii=False, indent=2))
    return 0


def cmd_index(args: argparse.Namespace) -> int:
    registry = load_yaml(Path(args.registry))
    validate_document(registry, Path(args.schema))
    maps = parse_map_arguments(args.map)
    ecosystem_map = build_ecosystem_map(registry, maps, args.now)
    write_json(Path(args.out), ecosystem_map)
    if args.llms_out:
        llms_path = Path(args.llms_out)
        llms_path.parent.mkdir(parents=True, exist_ok=True)
        llms_path.write_text(render_llms_index(ecosystem_map), encoding="utf-8")
    print(json.dumps({
        "status": ecosystem_map["status"],
        "ecosystemMapDigest": ecosystem_map["ecosystemMapDigest"],
        "metrics": ecosystem_map["metrics"],
        "out": args.out,
        "llmsOut": args.llms_out,
    }, ensure_ascii=False, indent=2))
    return 0 if ecosystem_map["status"] == "PASS" else 3


def cmd_route(args: argparse.Namespace) -> int:
    ecosystem_map = load_json(Path(args.ecosystem_map))
    request = load_json(Path(args.request))
    validate_document(request, Path(args.request_schema))
    result = route_ticket(ecosystem_map, request, args.now)
    write_json(Path(args.out), result)
    print(json.dumps({"status": result["status"], "contextDigest": result["contextDigest"], "out": args.out}, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "PASS" else 3


def cmd_prepare_ticket(args: argparse.Namespace) -> int:
    request = load_json(Path(args.request))
    validate_document(request, Path(args.request_schema))
    route = load_json(Path(args.route))
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    write_json(out_dir / "context-selection.json", route)
    planner_request = create_planner_request(request, route)
    write_json(out_dir / "todo2code-request.json", planner_request)
    (out_dir / "CONTEXT.md").write_text(render_ticket_context(request, route), encoding="utf-8")
    receipt = {
        "schema": "subactor.ticket-context-preparation-receipt/v1",
        "generatedAt": args.now or utc_now(),
        "ticketId": request["ticketId"],
        "routeStatus": route["status"],
        "contextDigest": route["contextDigest"],
        "plannerRequestDigest": planner_request["plannerRequestDigest"],
        "artifacts": ["context-selection.json", "todo2code-request.json", "CONTEXT.md"],
    }
    receipt["receiptDigest"] = digest(receipt)
    write_json(out_dir / "receipt.json", receipt)
    print(json.dumps({"ok": True, "routeStatus": route["status"], "outDir": str(out_dir), "receiptDigest": receipt["receiptDigest"]}, ensure_ascii=False, indent=2))
    return 0 if route["status"] == "PASS" else 3


def cmd_validate_plan(args: argparse.Namespace) -> int:
    request = load_json(Path(args.request))
    result = load_json(Path(args.result))
    if args.result_schema:
        validate_document(result, Path(args.result_schema))
    receipt = validate_plan_result(request, result, args.now)
    write_json(Path(args.out), receipt)
    print(json.dumps({"finalOutcome": receipt["finalOutcome"], "receiptDigest": receipt["receiptDigest"], "out": args.out}, ensure_ascii=False, indent=2))
    return 0 if receipt["finalOutcome"] == "PASS" else 3


def cmd_diff_maps(args: argparse.Namespace) -> int:
    before = parse_toon_index(Path(args.before))
    after = parse_toon_index(Path(args.after))
    result = diff_toon_indexes(before, after)
    if not args.full:
        result = {key: value for key, value in result.items() if key not in {"addedModules", "removedModules", "changedModules"}}
    write_json(Path(args.out), result)
    print(json.dumps({"summary": result["summary"], "out": args.out}, ensure_ascii=False, indent=2))
    return 0


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    sub = root.add_subparsers(dest="command", required=True)

    validate_registry = sub.add_parser("validate-registry")
    validate_registry.add_argument("--registry", required=True)
    validate_registry.add_argument("--schema", required=True)
    validate_registry.set_defaults(func=cmd_validate_registry)

    index = sub.add_parser("index")
    index.add_argument("--registry", required=True)
    index.add_argument("--schema", required=True)
    index.add_argument("--map", action="append", default=[], help="ORGANIZATION=PATH")
    index.add_argument("--out", required=True)
    index.add_argument("--llms-out")
    index.add_argument("--now", help="Fixed ISO-8601 timestamp for reproducible receipts")
    index.set_defaults(func=cmd_index)

    route = sub.add_parser("route-ticket")
    route.add_argument("--ecosystem-map", required=True)
    route.add_argument("--request", required=True)
    route.add_argument("--request-schema", required=True)
    route.add_argument("--out", required=True)
    route.add_argument("--now", help="Fixed ISO-8601 timestamp for reproducible receipts")
    route.set_defaults(func=cmd_route)

    prepare = sub.add_parser("prepare-ticket")
    prepare.add_argument("--request", required=True)
    prepare.add_argument("--request-schema", required=True)
    prepare.add_argument("--route", required=True)
    prepare.add_argument("--out-dir", required=True)
    prepare.add_argument("--now", help="Fixed ISO-8601 timestamp for reproducible receipts")
    prepare.set_defaults(func=cmd_prepare_ticket)

    validate_plan = sub.add_parser("validate-plan-set")
    validate_plan.add_argument("--request", required=True)
    validate_plan.add_argument("--result", required=True)
    validate_plan.add_argument("--result-schema")
    validate_plan.add_argument("--out", required=True)
    validate_plan.add_argument("--now", help="Fixed ISO-8601 timestamp for reproducible receipts")
    validate_plan.set_defaults(func=cmd_validate_plan)

    diff = sub.add_parser("diff-maps")
    diff.add_argument("--before", required=True)
    diff.add_argument("--after", required=True)
    diff.add_argument("--out", required=True)
    diff.add_argument("--full", action="store_true")
    diff.set_defaults(func=cmd_diff_maps)
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        return int(args.func(args))
    except (EcosystemError, jsonschema.ValidationError, OSError, ValueError, KeyError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
