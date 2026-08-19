#!/usr/bin/env python3
"""Accountable autonomy cycle for the Evolutionary Priority DSL.

The cycle observes, routes, optionally invokes pinned tools, evaluates policy
and writes receipts. It never applies a source patch, never promotes lifecycle
and never invents a planner or offer result when the tool is not pinned.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from ecosystemctl import (
    build_ecosystem_map,
    create_planner_request,
    digest,
    load_json,
    load_yaml,
    parse_map_arguments,
    render_llms_index,
    route_ticket,
    utc_now,
    validate_plan_result,
    write_json,
)
from standardctl import compile_facades, evaluate, parse_time
from statectl import project_state

Json = dict[str, Any]
ROOT = Path(__file__).resolve().parents[1]


class AutonomyError(RuntimeError):
    pass


def file_digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _first_existing(candidates: list[Path]) -> Path | None:
    for path in candidates:
        if path.is_file():
            return path
    return None


def discover_tools(root: Path, environ: dict[str, str] | None = None) -> Json:
    env = environ or dict(os.environ)
    todo2code_cli = env.get("TODO2CODE_CLI")
    todo2code_root = env.get("TODO2CODE_ROOT")
    cli_candidates: list[Path] = []
    if todo2code_cli:
        cli_candidates.append(Path(todo2code_cli))
    if todo2code_root:
        cli_candidates.append(Path(todo2code_root) / "dist" / "src" / "cli.js")
    search_siblings = env.get("AUTONOMY_DISCOVER_SIBLINGS", "1") != "0"
    if search_siblings:
        cli_candidates.append(root.parent / "todo2code" / "dist" / "src" / "cli.js")
    cli = _first_existing(cli_candidates)
    graph = Path(env["T2C_GRAPH"]) if env.get("T2C_GRAPH") else None
    diagnostics = Path(env["T2C_DIAGNOSTICS"]) if env.get("T2C_DIAGNOSTICS") else None
    offer_root = Path(env["OFFER_ROOT"]) if env.get("OFFER_ROOT") else None
    if offer_root is None and search_siblings:
        sibling = root.parent.parent / "subactor" / "offer"
        if (sibling / "scripts" / "pin-check.py").is_file():
            offer_root = sibling
    pin_check = (offer_root / "scripts" / "pin-check.py") if offer_root else None
    binding = Path(env["OFFER_BINDING"]) if env.get("OFFER_BINDING") else None
    facade = Path(env["OFFER_FACADE"]) if env.get("OFFER_FACADE") else None
    planner_ready = bool(cli and graph and diagnostics and cli.is_file() and graph.is_file() and diagnostics.is_file())
    offer_ready = bool(
        pin_check and binding and facade
        and pin_check.is_file() and binding.is_file() and facade.is_file()
    )
    report: Json = {
        "schema": "subactor.tool-discovery/v1",
        "packageRoot": str(root),
        "planner": {
            "projectId": "autogrammar/todo2code",
            "cli": str(cli) if cli else None,
            "graph": str(graph) if graph else None,
            "diagnostics": str(diagnostics) if diagnostics else None,
            "pinned": planner_ready,
            "reason": (
                "pinned"
                if planner_ready
                else "T2C_PLANNER_CONTRACT_UNBOUND"
                if cli
                else "T2C_PLANNER_NOT_PINNED"
            ),
        },
        "offer": {
            "projectId": "subactor/offer",
            "root": str(offer_root) if offer_root else None,
            "pinCheck": str(pin_check) if pin_check and pin_check.is_file() else None,
            "binding": str(binding) if binding else None,
            "facade": str(facade) if facade else None,
            "pinned": offer_ready,
            "reason": "pinned" if offer_ready else "OFFER_PIN_NOT_PINNED",
        },
        "applyAllowed": False,
    }
    report["discoveryDigest"] = digest(report)
    return report


def invoke_planner(discovery: Json, *, injected: Path | None = None, now: str) -> Json:
    if injected is not None:
        result = load_json(injected)
        result.setdefault("diagnostics", [])
        result["invocation"] = {"mode": "injected", "path": str(injected)}
        return result
    planner = discovery["planner"]
    if not planner["cli"]:
        return {
            "status": "not-run",
            "code": "T2C_PLANNER_NOT_PINNED",
            "recordCount": 0,
            "plans": [],
            "message": "todo2code CLI is not pinned; autonomy abstains instead of inventing a plan.",
            "invocation": {"mode": "abstain"},
        }
    if not planner["pinned"]:
        return {
            "status": "not-run",
            "code": "T2C_PLANNER_CONTRACT_UNBOUND",
            "recordCount": 0,
            "plans": [],
            "message": "todo2code CLI exists but T2C_GRAPH and T2C_DIAGNOSTICS are not pinned.",
            "invocation": {"mode": "abstain", "cli": planner["cli"]},
        }
    out = Path(planner["graph"]).with_name("autonomy-planner-plans.json")
    command = [
        "node",
        planner["cli"],
        "propose-code-change",
        planner["graph"],
        "--diagnostics",
        planner["diagnostics"],
        "--out",
        str(out),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0 or not out.is_file():
        return {
            "status": "failed",
            "code": "T2C_PLANNER_FAILED",
            "recordCount": 0,
            "plans": [],
            "message": completed.stderr.strip() or completed.stdout.strip() or "planner process failed",
            "invocation": {"mode": "cli", "argv": command, "exitCode": completed.returncode},
        }
    payload = load_json(out)
    plans = payload.get("plans") if isinstance(payload.get("plans"), list) else []
    return {
        "status": "succeeded",
        "recordCount": len(plans),
        "plans": plans,
        "invocation": {"mode": "cli", "argv": command, "exitCode": 0, "generatedAt": now},
    }


def invoke_offer_pin(discovery: Json, revision: str, observed_at: str, *, injected: Path | None = None) -> Json | None:
    if injected is not None:
        receipt = load_json(injected)
        receipt["invocation"] = {"mode": "injected", "path": str(injected)}
        return receipt
    offer = discovery["offer"]
    if not offer["pinned"]:
        return None
    command = ["python3", offer["pinCheck"], "--binding", offer["binding"], "--facade", offer["facade"]]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    mismatch = 0 if completed.returncode == 0 else 1
    receipt: Json = {
        "schema": "subactor.offer-pin-receipt/v1",
        "fixture": False,
        "status": "PASS" if completed.returncode == 0 else "FAIL",
        "observedAt": observed_at,
        "revision": revision,
        "facadeDigestMismatchCount": mismatch,
        "duplicatePriceSourceCount": 0,
        "catalogBindingCoverage": 1.0 if completed.returncode == 0 else 0.0,
        "stdout": completed.stdout[-2000:],
        "invocation": {"mode": "cli", "argv": command, "exitCode": completed.returncode},
    }
    receipt["receiptDigest"] = digest(receipt)
    return receipt


def run_cycle(
    root: Path,
    out_dir: Path,
    request_path: Path,
    *,
    now: str | None = None,
    revision: str | None = None,
    planner_result: Path | None = None,
    offer_receipt: Path | None = None,
    environ: dict[str, str] | None = None,
) -> Json:
    now = now or utc_now()
    revision = revision or os.environ.get("REVISION") or f"git:{_git_head(root)}"
    out_dir.mkdir(parents=True, exist_ok=True)
    generated = out_dir / "generated"
    receipts = out_dir / "receipts"
    ticket_dir = out_dir / "ticket"
    generated.mkdir(parents=True, exist_ok=True)
    receipts.mkdir(parents=True, exist_ok=True)

    discovery = discover_tools(root, environ)
    write_json(generated / "tool-discovery.json", discovery)

    registry = load_yaml(root / "registry" / "ecosystem-tools.yaml")
    maps = parse_map_arguments([
        f"subactor={root / 'sources/indexes/subactor-2026-08-19.toon.yaml'}",
        f"autogrammar={root / 'sources/indexes/autogrammar-2026-08-19.toon.yaml'}",
    ])
    ecosystem_map = build_ecosystem_map(registry, maps, now)
    write_json(generated / "ecosystem-map.json", ecosystem_map)
    (generated / "llms.txt").write_text(render_llms_index(ecosystem_map), encoding="utf-8")

    request = load_json(request_path)
    route = route_ticket(ecosystem_map, request, now)
    write_json(generated / "ticket-context-selection.json", route)
    planner_request = create_planner_request(request, route)
    write_json(ticket_dir / "todo2code-request.json", planner_request)
    write_json(ticket_dir / "context-selection.json", route)

    planner_envelope = invoke_planner(discovery, injected=planner_result, now=now)
    write_json(generated / "planner-result.json", planner_envelope)
    planner_receipt = validate_plan_result(request, planner_envelope, now)
    write_json(receipts / "planner-validation.json", planner_receipt)

    offer = invoke_offer_pin(discovery, revision, now, injected=offer_receipt)
    if offer is not None:
        write_json(receipts / "offer-pin.json", offer)

    policy = load_yaml(root / "priority-evolution.dsl.yaml")
    base_state = load_json(root / "examples" / "healthy-state.json")
    state = project_state(
        policy,
        ecosystem_map,
        revision,
        now,
        base_state=base_state,
        route=route,
        planner_receipt=planner_receipt,
        offer_receipt=offer,
    )
    write_json(generated / "current-state.json", state)
    decision = evaluate(policy, state, parse_time(now))
    write_json(receipts / "priority-decision.json", decision)
    compile_facades(policy, decision, out_dir)

    steps = [
        {"id": "discover", "status": "PASS", "pinnedPlanner": discovery["planner"]["pinned"], "pinnedOffer": discovery["offer"]["pinned"]},
        {"id": "index", "status": ecosystem_map["status"]},
        {"id": "route", "status": route["status"]},
        {"id": "planner", "status": planner_receipt["finalOutcome"], "envelope": planner_envelope.get("status"), "code": planner_envelope.get("code")},
        {"id": "offer", "status": offer["status"] if offer else "NOT_MEASURED"},
        {"id": "evaluate", "status": decision["finalOutcome"]},
    ]
    cycle: Json = {
        "schema": "subactor.autonomy-cycle/v1",
        "generatedAt": now,
        "revision": revision,
        "applyAttempted": False,
        "applyAllowed": False,
        "dispatchAllowed": bool(decision["executionGate"]["dispatchAllowed"]),
        "finalOutcome": decision["finalOutcome"],
        "discoveryDigest": discovery["discoveryDigest"],
        "plannerRequestDigest": planner_request["plannerRequestDigest"],
        "plannerReceiptDigest": planner_receipt["receiptDigest"],
        "decisionDigest": decision["receiptDigest"],
        "steps": steps,
        "abstentions": [item for item in (
            discovery["planner"]["reason"] if not discovery["planner"]["pinned"] else None,
            discovery["offer"]["reason"] if offer is None else None,
        ) if item],
    }
    cycle["cycleDigest"] = digest(cycle)
    write_json(receipts / "autonomy-cycle.json", cycle)
    return cycle


def _git_head(root: Path) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode == 0:
        return completed.stdout.strip()
    return "unknown"


def cmd_discover(args: argparse.Namespace) -> int:
    report = discover_tools(Path(args.root))
    write_json(Path(args.out), report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


def cmd_cycle(args: argparse.Namespace) -> int:
    cycle = run_cycle(
        Path(args.root),
        Path(args.out_dir),
        Path(args.request),
        now=args.now,
        revision=args.revision,
        planner_result=Path(args.planner_result) if args.planner_result else None,
        offer_receipt=Path(args.offer_receipt) if args.offer_receipt else None,
    )
    print(json.dumps({
        "finalOutcome": cycle["finalOutcome"],
        "dispatchAllowed": cycle["dispatchAllowed"],
        "applyAttempted": cycle["applyAttempted"],
        "abstentions": cycle["abstentions"],
        "cycleDigest": cycle["cycleDigest"],
        "outDir": args.out_dir,
    }, ensure_ascii=False, indent=2))
    return 0 if cycle["finalOutcome"] == "PASS" else 3


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    sub = root.add_subparsers(dest="command", required=True)
    discover = sub.add_parser("discover")
    discover.add_argument("--root", default=str(ROOT))
    discover.add_argument("--out", required=True)
    discover.set_defaults(func=cmd_discover)
    cycle = sub.add_parser("cycle")
    cycle.add_argument("--root", default=str(ROOT))
    cycle.add_argument("--out-dir", required=True)
    cycle.add_argument("--request", required=True)
    cycle.add_argument("--now")
    cycle.add_argument("--revision")
    cycle.add_argument("--planner-result")
    cycle.add_argument("--offer-receipt")
    cycle.set_defaults(func=cmd_cycle)
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        return int(args.func(args))
    except (AutonomyError, OSError, ValueError, KeyError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
