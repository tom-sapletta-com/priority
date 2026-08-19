# Verification report

- Version: `0.3.4`
- Generated at: `2026-08-19T10:00:00Z`
- Policy digest: `sha256:49a8d1fcf2437711aed06f59ae8533f5d508db98237052377cc27deb08cf2a4f`
- Registry digest: `sha256:bbffea79164bec56bddcb1bee5aeefd09e77c330ca733e01fec59e8f0ad38cca`
- Report digest: `sha256:26f888ce9d6af2b4140f10d6034202065ebf7bb101af207ad131a4b4f9ca3ecb`
- Tests: **52/53 passed**

## Output receipts

- `generated/ecosystem-map.json` — `PASS` — file `sha256:9864dcac78b9b168ad6e28e4aa4a647cadb52db0101352a6735b740ecece036c` — receipt `sha256:9864dcac78b9b168ad6e28e4aa4a647cadb52db0101352a6735b740ecece036c`
- `generated/ticket-context-selection.json` — `REVIEW_REQUIRED` — file `sha256:8244b5c8b964813f10021bf593e1262a596210d6083c1fde74a30984358133f4` — receipt `sha256:c745022ded0ce4d88f5ad74782ca976b61c788a7cacfe7919a1ed2778046d462`
- `receipts/todo2code-plan-gap.json` — `BLOCK` — file `sha256:ef33cb097d93080e9e59a1ea01eb13e27ae2252a697de98cc3cb1baefb203c4d` — receipt `sha256:594185df858f6d230e3fac196677ce904577cc88e6bc58041699cd944848307e`
- `receipts/todo2code-plan-valid.json` — `PASS` — file `sha256:1fcc91aa0c9caeb8496ddaa0e3e0ac20c143b1af0e4ef868f09a92093fe08476` — receipt `sha256:8289a3e99605a7cbb1f6111d42010f3795e9c1c7b11ae5a70b49754122f57986`
- `receipts/index-grounded-decision.json` — `BLOCK` — file `sha256:536531498025c9a4bf2632eaa567a306cc9b7e4be34fc29defab2270aa6fed43` — receipt `sha256:27b820eeef3c4060efee32d8c4ac2a766a1e993b2ee4b4d121c4142806a67f61`
- `receipts/healthy-decision.json` — `PASS` — file `sha256:83855d0cc08f1a25877df6b681a941c2817c1c2ff6c7951d87d9817956bf6305` — receipt `sha256:b3029385da583af9cfc07b4b5c70537347298a08946e50121702b1ac799939e7`

## Test runner output

```text
test_cli_without_graph_is_contract_unbound (test_autonomyctl.AutonomyCtlTests.test_cli_without_graph_is_contract_unbound) ... ok
test_cycle_abstains_and_never_applies (test_autonomyctl.AutonomyCtlTests.test_cycle_abstains_and_never_applies) ... ok
test_injected_offer_fixture_is_not_live_attestation_but_is_measured (test_autonomyctl.AutonomyCtlTests.test_injected_offer_fixture_is_not_live_attestation_but_is_measured) ... ok
test_injected_zero_implementation_diagnostics_is_not_plan_gap (test_autonomyctl.AutonomyCtlTests.test_injected_zero_implementation_diagnostics_is_not_plan_gap) ... ok
test_injected_zero_plan_stays_plan_gap (test_autonomyctl.AutonomyCtlTests.test_injected_zero_plan_stays_plan_gap) ... ok
test_local_planner_sources_pin_when_discovery_enabled (test_autonomyctl.AutonomyCtlTests.test_local_planner_sources_pin_when_discovery_enabled) ... ok
test_unpinned_planner_is_not_run_not_fake_success (test_autonomyctl.AutonomyCtlTests.test_unpinned_planner_is_not_run_not_fake_success) ... ok
test_candidate_standard_can_be_verified_but_not_executable (test_ecosystemctl.EcosystemCtlTests.test_candidate_standard_can_be_verified_but_not_executable) ... ok
test_default_indexes_include_wellmanifest_and_pyqual (test_ecosystemctl.EcosystemCtlTests.test_default_indexes_include_wellmanifest_and_pyqual) ... ok
test_documentation_only_tool_is_not_execution_eligible (test_ecosystemctl.EcosystemCtlTests.test_documentation_only_tool_is_not_execution_eligible) ... ok
test_duplicate_home_becomes_blocking_finding (test_ecosystemctl.EcosystemCtlTests.test_duplicate_home_becomes_blocking_finding) ... ok
test_grounded_plan_is_accepted (test_ecosystemctl.EcosystemCtlTests.test_grounded_plan_is_accepted) ... ok
test_home_owners_are_unique (test_ecosystemctl.EcosystemCtlTests.test_home_owners_are_unique) ... ok
test_llms_index_marks_documentation_boundary (test_ecosystemctl.EcosystemCtlTests.test_llms_index_marks_documentation_boundary) ... ok
test_pinned_quality_gate_is_execution_eligible (test_ecosystemctl.EcosystemCtlTests.test_pinned_quality_gate_is_execution_eligible) ... ok
test_planner_request_encodes_zero_plan_policy (test_ecosystemctl.EcosystemCtlTests.test_planner_request_encodes_zero_plan_policy) ... ok
test_registry_matches_schema (test_ecosystemctl.EcosystemCtlTests.test_registry_matches_schema) ... ok
test_router_fails_closed_for_documentation_only_required_role (test_ecosystemctl.EcosystemCtlTests.test_router_fails_closed_for_documentation_only_required_role) ... ok
test_router_selects_real_planner_and_fleet_observer (test_ecosystemctl.EcosystemCtlTests.test_router_selects_real_planner_and_fleet_observer) ... ok
test_router_tokens_are_not_split_on_polish_stroke (test_ecosystemctl.EcosystemCtlTests.test_router_tokens_are_not_split_on_polish_stroke) ... ok
test_tokenize_drops_function_words_and_maps_synonyms (test_ecosystemctl.EcosystemCtlTests.test_tokenize_drops_function_words_and_maps_synonyms) ... ok
test_tokenize_keeps_polish_l_stroke_words_intact (test_ecosystemctl.EcosystemCtlTests.test_tokenize_keeps_polish_l_stroke_words_intact) ... ok
test_unplannable_implementation_diagnostics_stay_plan_gap (test_ecosystemctl.EcosystemCtlTests.test_unplannable_implementation_diagnostics_stay_plan_gap) ... ok
test_verified_tools_are_execution_eligible (test_ecosystemctl.EcosystemCtlTests.test_verified_tools_are_execution_eligible) ... ok
test_zero_implementation_diagnostics_is_not_plan_gap (test_ecosystemctl.EcosystemCtlTests.test_zero_implementation_diagnostics_is_not_plan_gap) ... ok
test_zero_plan_is_blocked (test_ecosystemctl.EcosystemCtlTests.test_zero_plan_is_blocked) ... ok
test_accepts_exact_revision_with_pass_state (test_pre_receive.PreReceiveTests.test_accepts_exact_revision_with_pass_state) ... ok
test_rejects_multiple_new_revisions (test_pre_receive.PreReceiveTests.test_rejects_multiple_new_revisions) ... ok
test_rejects_policy_block_with_machine_result (test_pre_receive.PreReceiveTests.test_rejects_policy_block_with_machine_result) ... ok
test_rejects_revision_mismatch (test_pre_receive.PreReceiveTests.test_rejects_revision_mismatch) ... ok
test_native_parser_rejects_stage_with_run_and_tool (test_pyqual_contract.PyqualContractTests.test_native_parser_rejects_stage_with_run_and_tool) ... skipped "semcod/pyqual is not importable: No module named 'nfo'"
test_pinned_default_yaml_matches_revision_digest (test_pyqual_contract.PyqualContractTests.test_pinned_default_yaml_matches_revision_digest) ... ok
test_pinned_default_yaml_parses_with_native_pyqual (test_pyqual_contract.PyqualContractTests.test_pinned_default_yaml_parses_with_native_pyqual) ... ok
test_latest_shadow_receipt_never_applied (test_shadow_receipts.ShadowReceiptTests.test_latest_shadow_receipt_never_applied) ... ok
test_shadow_log_does_not_authorize_promotion (test_shadow_receipts.ShadowReceiptTests.test_shadow_log_does_not_authorize_promotion) ... ok
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
Ran 53 tests

OK (skipped=1)
```
