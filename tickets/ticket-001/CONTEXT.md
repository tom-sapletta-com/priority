# Context selection for ticket-001

Status: **REVIEW_REQUIRED**
Request digest: `sha256:abcb28414f82643fcaefe9c4ea93a0ab9c9f53366f5dbef6dfaa6b2d84e091ee`
Ecosystem map digest: `sha256:86b6108e7aa84cf86e1a7ce390348e8dc70b2d141df22d3b7397f5a45443854b`
Context digest: `sha256:c745022ded0ce4d88f5ad74782ca976b61c788a7cacfe7919a1ed2778046d462`

## Intent

Kontynuuj rozwój Evolutionary Priority DSL na podstawie map projektów; użyj istniejącego todo2code do planowania, diagit do mapy i routingu, pyqual do bramki, zachowaj subactor/offer jako jedyne HOME wartości oferty i wellmanifest jako niezależny standard.

## Selected repositories

- `subactor/platform` — score 268.0; evidence `VERIFIED`; execution `true`; reasons: required roles: policy-instance-owner; HOME for: engineering-standardization-policy-instance; organizational-policy-instance: evolutionary, policy, priority, standardization; ticket-allocation: project, ticket; preferred by ticket
- `subactor/offer` — score 256.0; evidence `VERIFIED`; execution `true`; reasons: required roles: commercial-offer-home; HOME for: commercial-offer-values; offer-catalog-ssot: offer, plan; facade-digest-pinning: digest; preferred by ticket
- `wellmanifest/offer` — score 240.0; evidence `VERIFIED`; execution `false`; reasons: required roles: offer-standard-owner; HOME for: commercial-offer-standard; offer-standard: offer, standard; preferred by ticket
- `subactor/registry` — score 227.0; evidence `VERIFIED`; execution `true`; reasons: required roles: organization-registry; HOME for: organization-project-registry; registry-snapshot: map, project, registry; assignment-validation: home
- `wellmanifest/policy-dsl` — score 220.0; evidence `VERIFIED`; execution `false`; reasons: required roles: policy-language-standard-owner; HOME for: evolutionary-intent-policy-language; priority-policy-language: dsl, intent, policy, priority, standard
- `subactor/diagit` — score 218.0; evidence `VERIFIED`; execution `true`; reasons: required roles: fleet-observer; fleet-audit: fleet, map; project-context-routing: context, project, ticket; repair-plan-from-findings: plan, repair; preferred by ticket
- `autogrammar/todo2code` — score 188.0; evidence `VERIFIED`; execution `true`; reasons: required roles: planner; intent-evidence-graph: intent; bounded-code-change-planning: change, code, plan, planning; preferred by ticket
- `semcod/pyqual` — score 185.0; evidence `VERIFIED`; execution `true`; reasons: required roles: quality-gate; declarative-quality-gates: gate, manifest, quality; repair-loop: repair; preferred by ticket
- `subactor/validator-agent` — score 148.0; evidence `VERIFIED`; execution `true`; reasons: required roles: independent-validator; independent-patch-validation: independent, policy, validator
- `subactor/onedev-agent` — score 142.0; evidence `VERIFIED`; execution `true`; reasons: required roles: server-git-gateway; authoritative-git-gate: gate; ticket-scope-enforcement: ticket; project-trait-selection: project
- `subactor/repair-agent` — score 124.0; evidence `VERIFIED`; execution `true`; reasons: required roles: implementation-executor; hash-bound-repair: repair
- `wellmanifest/new-project` — score 56.0; evidence `VERIFIED`; execution `true`; reasons: bounded-ticket: intent, ticket; manifest-adoption: manifest, pyqual, standard

## Acceptance criteria

- Mapa ekosystemu wskazuje projekt, rolę, HOME, capability, URI i klasę dowodu.
- Router wybiera minimalny kontekst i fail-closed raportuje role bez wykonawczo zweryfikowanego kontraktu.
- Zero planów przy otwartych kryteriach daje BLOCK z kodem T2C_PLAN_GAP.
- Każdy zaakceptowany plan ma dokładne ścieżki, kryterium negatywne i granicę walidacji.
- subactor/offer pozostaje jedynym HOME wartości cenowych; wellmanifest/offer nie zawiera kwot.

## Fail-closed findings

- `ROUTER_REQUIRED_ROLE_NOT_EXECUTION_VERIFIED` — {"code":"ROUTER_REQUIRED_ROLE_NOT_EXECUTION_VERIFIED","evidenceStatus":"VERIFIED","projectId":"wellmanifest/policy-dsl","role":"policy-language-standard-owner","severity":"warning"}
- `ROUTER_REQUIRED_ROLE_NOT_EXECUTION_VERIFIED` — {"code":"ROUTER_REQUIRED_ROLE_NOT_EXECUTION_VERIFIED","evidenceStatus":"VERIFIED","projectId":"wellmanifest/offer","role":"offer-standard-owner","severity":"warning"}

The planner may use only the selected repositories as context. It must not infer completion from file or symbol presence and must emit a non-empty grounded plan while acceptance criteria remain open.
