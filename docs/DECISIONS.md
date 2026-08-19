# Architecture decisions

## ADR-001 — Standard and organizational instance have different HOME

`wellmanifest/policy-dsl` owns the abstract language. `subactor/platform` owns the Subactor-specific policy instance. Repository selectors, product names and organizational routing do not move into the abstract standard.

## ADR-002 — Documentation is context, not execution evidence

A project with only documentation evidence may be selected for review or normative context, but receives `executionEligible=false` until an exact code/configuration map or runtime receipt is pinned.

## ADR-003 — Empty planner output is a planning failure

When acceptance criteria remain open, `recordCount=0` is `T2C_PLAN_GAP`. Presence of target files or symbols cannot close behavioral criteria.

## ADR-004 — Commercial values and offer standard are independent

`subactor/offer` is HOME of prices, catalogues and bindings. `wellmanifest/offer` is HOME of abstract adoption, fail-closed and versioning rules. It does not contain Subactor prices.

## ADR-005 — Structural and behavioral evidence are projected separately

A TOON map proves indexed structure. It does not prove digest equality, test behavior or production deployment. Behavioral metrics require a revision-bound receipt.

## ADR-006 — Candidate policy cannot dispatch

A `candidate`, `shadow` or `canary` policy may calculate priorities and proposed actions, but only `active` can open the execution gate.

## ADR-007 — Autonomy is a closed observe-evaluate loop, not silent execution

`autonomyctl cycle` discovers pinned tools, indexes, routes, invokes or abstains, evaluates and writes receipts. Missing `todo2code` CLI or offer pin-check is `not-run` / `NOT_MEASURED`, never a invented `succeeded` plan. The cycle never applies a source patch. `applyAttempted` is always false.
