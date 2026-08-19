# Verification report

- Version: `0.3.0`
- Generated at: `2026-08-19T10:00:00Z`
- Policy digest: `sha256:49a8d1fcf2437711aed06f59ae8533f5d508db98237052377cc27deb08cf2a4f`
- Registry digest: `sha256:4930758b69658f4de3481000e70330beed8abe312c812a8b5bcc950ff30576fd`
- Report digest: `sha256:90559c6a9cdb3f8a7a865c53b2d48ced1e239ac8dfd572e6a982ff63484fa404`
- Tests: **36/36 passed**

## Output receipts

- `generated/ecosystem-map.json` — `REVIEW_REQUIRED` — file `sha256:bdcb3f9e93797f016c02e7d0c68a6bbc215533825e51a265f73d51483b8cdc1c` — receipt `sha256:bdcb3f9e93797f016c02e7d0c68a6bbc215533825e51a265f73d51483b8cdc1c`
- `generated/ticket-context-selection.json` — `REVIEW_REQUIRED` — file `sha256:350e59ff6ee653754d025ef3b99faf1996917637f49a8008d2ff7d136a970f4b` — receipt `sha256:92d3bc5acb31e778994e66a1ed0e9beb8223c475f97885fbbaa9bea9c2e83a3b`
- `receipts/todo2code-plan-gap.json` — `BLOCK` — file `sha256:ef33cb097d93080e9e59a1ea01eb13e27ae2252a697de98cc3cb1baefb203c4d` — receipt `sha256:594185df858f6d230e3fac196677ce904577cc88e6bc58041699cd944848307e`
- `receipts/todo2code-plan-valid.json` — `PASS` — file `sha256:1fcc91aa0c9caeb8496ddaa0e3e0ac20c143b1af0e4ef868f09a92093fe08476` — receipt `sha256:8289a3e99605a7cbb1f6111d42010f3795e9c1c7b11ae5a70b49754122f57986`
- `receipts/index-grounded-decision.json` — `BLOCK` — file `sha256:4c476cb4ae33a9f02abe6d3edd2a8ee9e2f18b61036fc065b88b8b8e0c167e0f` — receipt `sha256:046d65023ea812391034cc0d9d19b30020dc56c98a0879a136a2a856b51d8bf4`
- `receipts/healthy-decision.json` — `PASS` — file `sha256:83855d0cc08f1a25877df6b681a941c2817c1c2ff6c7951d87d9817956bf6305` — receipt `sha256:b3029385da583af9cfc07b4b5c70537347298a08946e50121702b1ac799939e7`

## Test runner output

```text
test_documentation_only_tool_is_not_execution_eligible (test_ecosystemctl.EcosystemCtlTests.test_documentation_only_tool_is_not_execution_eligible) ... ok
test_duplicate_home_becomes_blocking_finding (test_ecosystemctl.EcosystemCtlTests.test_duplicate_home_becomes_blocking_finding) ... ok
test_grounded_plan_is_accepted (test_ecosystemctl.EcosystemCtlTests.test_grounded_plan_is_accepted) ... ok
test_home_owners_are_unique (test_ecosystemctl.EcosystemCtlTests.test_home_owners_are_unique) ... ok
test_llms_index_marks_documentation_boundary (test_ecosystemctl.EcosystemCtlTests.test_llms_index_marks_documentation_boundary) ... ok
test_planner_request_encodes_zero_plan_policy (test_ecosystemctl.EcosystemCtlTests.test_planner_request_encodes_zero_plan_policy) ... ok
test_registry_matches_schema (test_ecosystemctl.EcosystemCtlTests.test_registry_matches_schema) ... ok
test_router_fails_closed_for_documentation_only_required_role (test_ecosystemctl.EcosystemCtlTests.test_router_fails_closed_for_documentation_only_required_role) ... ok
test_router_selects_real_planner_and_fleet_observer (test_ecosystemctl.EcosystemCtlTests.test_router_selects_real_planner_and_fleet_observer) ... ok
test_router_tokens_are_not_split_on_polish_stroke (test_ecosystemctl.EcosystemCtlTests.test_router_tokens_are_not_split_on_polish_stroke) ... ok
test_tokenize_drops_function_words_and_maps_synonyms (test_ecosystemctl.EcosystemCtlTests.test_tokenize_drops_function_words_and_maps_synonyms) ... ok
test_tokenize_keeps_polish_l_stroke_words_intact (test_ecosystemctl.EcosystemCtlTests.test_tokenize_keeps_polish_l_stroke_words_intact) ... ok
test_verified_tools_are_execution_eligible (test_ecosystemctl.EcosystemCtlTests.test_verified_tools_are_execution_eligible) ... ok
test_zero_plan_is_blocked (test_ecosystemctl.EcosystemCtlTests.test_zero_plan_is_blocked) ... ok
test_accepts_exact_revision_with_pass_state (test_pre_receive.PreReceiveTests.test_accepts_exact_revision_with_pass_state) ... ok
test_rejects_multiple_new_revisions (test_pre_receive.PreReceiveTests.test_rejects_multiple_new_revisions) ... ok
test_rejects_policy_block_with_machine_result (test_pre_receive.PreReceiveTests.test_rejects_policy_block_with_machine_result) ... ok
test_rejects_revision_mismatch (test_pre_receive.PreReceiveTests.test_rejects_revision_mismatch) ... ok
test_active_policy_can_dispatch_bounded_delivery (test_standardctl.StandardCtlTests.test_active_policy_can_dispatch_bounded_delivery) ... ok
test_complementarity_budget_is_measured (test_standardctl.StandardCtlTests.test_complementarity_budget_is_measured) ... ok
test_healthy_state_passes_but_candidate_cannot_dispatch (test_standardctl.StandardCtlTests.test_healthy_state_passes_but_candidate_cannot_dispatch) ... ok
test_plan_gap_and_offer_pin_block (test_standardctl.StandardCtlTests.test_plan_gap_and_offer_pin_block) ... ok
test_policy_matches_schema_and_semantics (test_standardctl.StandardCtlTests.test_policy_matches_schema_and_semantics) ... ok
test_revision_mismatch_invalidates_evidence (test_standardctl.StandardCtlTests.test_revision_mismatch_invalidates_evidence) ... ok
test_separation_of_duties_is_constitutional_block (test_standardctl.StandardCtlTests.test_separation_of_duties_is_constitutional_block) ... ok
test_stale_metric_fails_closed (test_standardctl.StandardCtlTests.test_stale_metric_fails_closed) ... ok
test_tool_planning_precedes_dependent_repairs (test_standardctl.StandardCtlTests.test_tool_planning_precedes_dependent_repairs) ... ok
test_unmeasured_oscillation_requires_review (test_standardctl.StandardCtlTests.test_unmeasured_oscillation_requires_review) ... ok
test_behavioral_offer_metric_stays_missing_without_receipt (test_statectl.StateCtlTests.test_behavioral_offer_metric_stays_missing_without_receipt) ... ok
test_offer_receipt_closes_behavioral_metric_gap (test_statectl.StateCtlTests.test_offer_receipt_closes_behavioral_metric_gap) ... ok
test_offer_receipt_revision_must_match (test_statectl.StateCtlTests.test_offer_receipt_revision_must_match) ... ok
test_projection_derives_route_and_plan_gap_metrics (test_statectl.StateCtlTests.test_projection_derives_route_and_plan_gap_metrics) ... ok
test_diff_reports_added_removed_and_changed (test_toon_index.ToonIndexTests.test_diff_reports_added_removed_and_changed) ... ok
test_parses_compact_class_members (test_toon_index.ToonIndexTests.test_parses_compact_class_members) ... ok
test_parses_modules_and_header (test_toon_index.ToonIndexTests.test_parses_modules_and_header) ... ok
test_project_roots_are_counted (test_toon_index.ToonIndexTests.test_project_roots_are_counted) ... ok

----------------------------------------------------------------------
Ran 36 tests

OK
```
