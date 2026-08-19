# Changelog

## 0.3.3 — 2026-08-19

### Added

- pinned `semcod/pyqual` `PyqualConfig.default_yaml()` from `2fe7e47`;
- first candidate-lifecycle shadow receipt from a live autonomy cycle;
- negative parse test: a stage cannot set both `run` and `tool`.

### Changed

- pyqual adapter records the schema pin but keeps `enforcementEnabled=false`.

## 0.3.2 — 2026-08-19

### Added

- pinned wellmanifest 2026-08-16 and pyqual 2026-04-25 TOON maps;
- `wellmanifest/git-lifecycle` as a mapped, non-required standard;
- bounded `sources/planner` graph and diagnostics for the autonomy cycle;
- default discovery of sibling offer binding `www-sub-actor` and its facade.

### Changed

- required wellmanifest and pyqual projects move from documentation-only to
  map-backed `git_ast` evidence;
- candidate standards can be `VERIFIED` without becoming `executionEligible`;
- `make cycle` invokes pinned `todo2code` and live offer pin-check when those
  files exist.

## 0.3.1 — 2026-08-19

### Added

- `adapters/autonomyctl.py` closed cycle: discover → index → route → invoke-or-abstain → evaluate;
- typed abstentions `T2C_PLANNER_NOT_PINNED` and `T2C_PLANNER_CONTRACT_UNBOUND`;
- offer pin-check invocation only when binding and facade are pinned;
- `make cycle` and negative tests that the cycle never applies a patch.

### Fixed

- unpinned planner is `not-run`, not a fake `succeeded` + zero plans;
- README still advertised 33 tests after the 0.3.0 token and report fixes.

## 0.3.0 — 2026-08-19

### Added

- deterministic TOON index reader with compact class-method extraction;
- versioned ecosystem registry for Subactor, Autogrammar, Semcod and Wellmanifest roles;
- code-backed project evidence, HOME ownership, capability and URI map;
- `ecosystem-map.json` and compact `llms.txt` generation;
- deterministic ticket context router and `todo2code` request generator;
- fail-closed planner-result gate with `T2C_PLAN_GAP`;
- state projector separating structural map evidence from behavioral receipts;
- offer SSOT and digest-pin policy invariants;
- output schemas, source snapshots, systemd templates and Git gateway contract;
- generated shared policy context for AGENTS/CLAUDE/GEMINI;
- 33 unit and negative-behavior tests.

### Fixed

- the 0.2.0 archive documented examples and tests that were not actually included;
- TOON parsing previously saw `ControlService` but missed its compressed methods;
- complementarity normalization prevented a fully satisfied standalone delivery plan from crossing the automatic-dispatch threshold;
- documentation-only projects can no longer become execution-eligible;
- file or symbol presence can no longer turn an empty planner result into approval.

### Known boundaries

- no exact `semcod/pyqual` or `wellmanifest/*` maps were attached;
- the package prepares and validates the `todo2code` contract but does not execute its unavailable checkout/CLI;
- no runtime offer pin-check receipt was attached;
- lifecycle remains `candidate`; enforcement is disabled.

## 0.2.0 — 2026-08-19

- initial Evolutionary Priority DSL;
- reference evaluator, complementarity checks, triggers and agent facades;
- implementation-vs-standard repair split.
