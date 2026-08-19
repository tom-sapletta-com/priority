# ticket-006 — distinguish empty planner reasons

Read `t2c.code-change-plan-set/v1` `sourceDiagnosticCount` from live
`todo2code propose-code-change`. Do not invent plans. Do not promote
policy lifecycle from `candidate`.

`sourceDiagnosticCount=0` is `T2C_NO_IMPLEMENTATION_DIAGNOSTICS`.
A missing count, or implementation diagnostics that stay unplannable,
remains `T2C_PLAN_GAP`.

Discovery also probes `../autogrammar/todo2code` so a checkout that
moved out of `autogrammar/` still finds the live planner CLI.
