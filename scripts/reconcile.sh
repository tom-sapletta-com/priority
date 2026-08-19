#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SUBACTOR_MAP="${SUBACTOR_MAP:?SUBACTOR_MAP is required}"
AUTOGRAMMAR_MAP="${AUTOGRAMMAR_MAP:?AUTOGRAMMAR_MAP is required}"
TICKET_REQUEST="${TICKET_REQUEST:?TICKET_REQUEST is required}"
REVISION="${REVISION:?REVISION for the observed Git state is required}"
OUT_ROOT="${OUT_ROOT:-$ROOT/runtime}"
NOW="${NOW:-$(date -u +%Y-%m-%dT%H:%M:%SZ)}"
OBSERVED_AT="${OBSERVED_AT:-$NOW}"
mkdir -p "$OUT_ROOT/generated" "$OUT_ROOT/receipts" "$OUT_ROOT/ticket"

run_observation() {
  set +e
  "$@"
  code=$?
  set -e
  if [[ $code -ne 0 && $code -ne 3 ]]; then
    return "$code"
  fi
}

run_observation python3 "$ROOT/adapters/ecosystemctl.py" index \
  --registry "$ROOT/registry/ecosystem-tools.yaml" \
  --schema "$ROOT/schemas/ecosystem-tool-registry.schema.json" \
  --map "subactor=$SUBACTOR_MAP" \
  --map "autogrammar=$AUTOGRAMMAR_MAP" \
  --out "$OUT_ROOT/generated/ecosystem-map.json" \
  --llms-out "$OUT_ROOT/generated/llms.txt" \
  --now "$NOW"

run_observation python3 "$ROOT/adapters/ecosystemctl.py" route-ticket \
  --ecosystem-map "$OUT_ROOT/generated/ecosystem-map.json" \
  --request "$TICKET_REQUEST" \
  --request-schema "$ROOT/schemas/ticket-context-request.schema.json" \
  --out "$OUT_ROOT/generated/ticket-context-selection.json" \
  --now "$NOW"

run_observation python3 "$ROOT/adapters/ecosystemctl.py" prepare-ticket \
  --request "$TICKET_REQUEST" \
  --request-schema "$ROOT/schemas/ticket-context-request.schema.json" \
  --route "$OUT_ROOT/generated/ticket-context-selection.json" \
  --out-dir "$OUT_ROOT/ticket" \
  --now "$NOW"

state_args=(
  --policy "$ROOT/priority-evolution.dsl.yaml"
  --ecosystem-map "$OUT_ROOT/generated/ecosystem-map.json"
  --route "$OUT_ROOT/generated/ticket-context-selection.json"
  --revision "$REVISION"
  --observed-at "$OBSERVED_AT"
  --out "$OUT_ROOT/generated/current-state.json"
)
[[ -n "${BASE_STATE:-}" ]] && state_args+=(--base-state "$BASE_STATE")
[[ -n "${PLANNER_RECEIPT:-}" ]] && state_args+=(--planner-receipt "$PLANNER_RECEIPT")
[[ -n "${OFFER_RECEIPT:-}" ]] && state_args+=(--offer-receipt "$OFFER_RECEIPT")
run_observation python3 "$ROOT/adapters/statectl.py" "${state_args[@]}"

set +e
python3 "$ROOT/adapters/standardctl.py" evaluate \
  --policy "$ROOT/priority-evolution.dsl.yaml" \
  --state "$OUT_ROOT/generated/current-state.json" \
  --now "$NOW" \
  --out "$OUT_ROOT/receipts/priority-decision.json"
policy_status=$?
set -e

# BLOCK/REVIEW_REQUIRED are policy outcomes, not control-loop process failures.
if [[ $policy_status -eq 0 || $policy_status -eq 3 ]]; then
  exit 0
fi
exit "$policy_status"
