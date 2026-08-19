# Generated evolutionary policy context

Policy: `engineering-standardization` `0.3.0`
Policy digest: `sha256:49a8d1fcf2437711aed06f59ae8533f5d508db98237052377cc27deb08cf2a4f`
State revision: `sha256:example-head-20260819-v030`
Decision receipt: `sha256:27b820eeef3c4060efee32d8c4ac2a766a1e993b2ee4b4d121c4142806a67f61`
Final outcome: **BLOCK**

## Non-negotiable operating order

1. Read the active ticket, exact Git revision, HOME/ADOPT ownership and fresh receipts.
2. Never treat a model claim, file name, function name or endpoint presence as behavioral proof.
3. A higher priority class cannot be displaced by deadline, feature urgency, cost or model preference.
4. Do not execute a plan when the receipt says BLOCK or REVIEW_REQUIRED.
5. Standard changes are propose-only and must pass candidate → shadow → canary → active promotion.
6. The implementer cannot validate or promote its own patch.
7. Every code-changing step must cite its intentId, rule/evidence references and exact validation command or URI.

## Current ordered priorities

1. **STD-GOVERNANCE-TRUTH** — class `constitutional` (rank 0), importance 1000.0, dispatch 100.0
   - Outcome: `PASS`; violated: `false`; evidence: `FRESH`
   - Reasons: resolved-idle: Brak bieżącego naruszenia; ważność normatywna pozostaje bez zmian.; Brak aktywnego naruszenia przy świeżych dowodach.
2. **STD-TOOL-GROUNDED-PLANNING** — class `correctness` (rank 20), importance 975.0, dispatch 960.0
   - Outcome: `REPAIR_IMPLEMENTATION`; violated: `true`; evidence: `FRESH`
   - Reasons: plan-gap-boost: Otwarta intencja nie ma ugruntowanego planu zmian.
3. **STD-OFFER-SSOT-INTEGRITY** — class `correctness` (rank 20), importance 970.0, dispatch 680.0
   - Outcome: `BLOCK`; violated: `false`; evidence: `MISSING_OR_STALE`
   - Reasons: Brak świeżych dowodów: offer.facade_digest_mismatch_count
4. **STD-VALIDATION-BEHAVIOR** — class `correctness` (rank 20), importance 950.0, dispatch 200.0
   - Outcome: `PASS`; violated: `false`; evidence: `FRESH`
   - Reasons: healthy-coverage: Brak aktywnego naruszenia.; Brak aktywnego naruszenia przy świeżych dowodach.
5. **STD-ECOSYSTEM-CONTEXT-ROUTING** — class `standardization` (rank 30), importance 900.0, dispatch 780.0
   - Outcome: `REPAIR_IMPLEMENTATION`; violated: `true`; evidence: `FRESH`
   - Reasons: required-role-gap: Ticket nie ma zweryfikowanego projektu dla wymaganej roli lub concernu HOME.
6. **STD-MANIFEST-CONFORMANCE** — class `standardization` (rank 30), importance 850.0, dispatch 150.0
   - Outcome: `PASS`; violated: `false`; evidence: `FRESH`
   - Reasons: no-drift: Standard jest zgodny; pozostaje aktywny, lecz nie zajmuje kolejki.; Brak aktywnego naruszenia przy świeżych dowodach.
7. **DELIVERY-EVOLUTION** — class `delivery` (rank 40), importance 700.0, dispatch 600.0
   - Outcome: `PASS`; violated: `false`; evidence: `FRESH`
   - Reasons: Brak aktywnego naruszenia przy świeżych dowodach.

## Proposed actions (inert until the gate authorizes them)

- `STD-TOOL-GROUNDED-PLANNING` / `PLAN` → `uri://todo2code/code-change/plan`
- `STD-TOOL-GROUNDED-PLANNING` / `EXECUTE` → `uri://repair-agent/execute/hash-bound`
- `STD-TOOL-GROUNDED-PLANNING` / `VALIDATE` → `uri://validator-agent/validate/independent`
- `STD-OFFER-SSOT-INTEGRITY` / `REFRESH_EVIDENCE` → `uri://twin/observe`
- `STD-ECOSYSTEM-CONTEXT-ROUTING` / `PLAN` → `uri://diagit/repair-plan/from-findings`
- `STD-ECOSYSTEM-CONTEXT-ROUTING` / `EXECUTE` → `uri://repair-agent/execute/hash-bound`
- `STD-ECOSYSTEM-CONTEXT-ROUTING` / `VALIDATE` → `uri://pyqual/gate/manifest-conformance`

## Required response format for every agent

Before editing, report: active intent IDs, blocking invariants, evidence freshness, selected repository/paths, and validation boundary.
After editing, report: changed paths, receipt/revision, tests including at least one negative behavior test, remaining unknowns, and whether an independent validator accepted the exact patch hash.

This file is generated. Do not edit it manually.
