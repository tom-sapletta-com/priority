#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
NOW="${NOW:-2026-08-19T10:00:00Z}"
REVISION="${REVISION:-sha256:example-head-20260819-v030}"

allow_review() {
  set +e
  "$@"
  code=$?
  set -e
  if [[ $code -ne 0 && $code -ne 3 ]]; then
    return "$code"
  fi
}

python3 adapters/ecosystemctl.py validate-registry \
  --registry registry/ecosystem-tools.yaml \
  --schema schemas/ecosystem-tool-registry.schema.json \
  > generated/registry-validation.json

allow_review python3 adapters/ecosystemctl.py index \
  --registry registry/ecosystem-tools.yaml \
  --schema schemas/ecosystem-tool-registry.schema.json \
  --map subactor=sources/indexes/subactor-2026-08-19.toon.yaml \
  --map autogrammar=sources/indexes/autogrammar-2026-08-19.toon.yaml \
  --map wellmanifest=sources/indexes/wellmanifest-2026-08-16.toon.yaml \
  --map pyqual=sources/indexes/pyqual-2026-04-25.toon.yaml \
  --out generated/ecosystem-map.json \
  --llms-out generated/llms.txt \
  --now "$NOW" > generated/ecosystem-index-run.json

python3 adapters/ecosystemctl.py diff-maps \
  --before sources/indexes/subactor-2026-07-29.toon.yaml \
  --after sources/indexes/subactor-2026-08-19.toon.yaml \
  --out generated/subactor-map-diff.json \
  > generated/map-diff-run.json

allow_review python3 adapters/ecosystemctl.py route-ticket \
  --ecosystem-map generated/ecosystem-map.json \
  --request examples/ticket-context-request.json \
  --request-schema schemas/ticket-context-request.schema.json \
  --out generated/ticket-context-selection.json \
  --now "$NOW" > generated/ticket-route-run.json

rm -rf tickets/ticket-001
allow_review python3 adapters/ecosystemctl.py prepare-ticket \
  --request examples/ticket-context-request.json \
  --request-schema schemas/ticket-context-request.schema.json \
  --route generated/ticket-context-selection.json \
  --out-dir tickets/ticket-001 \
  --now "$NOW" > generated/ticket-prepare-run.json

allow_review python3 adapters/ecosystemctl.py validate-plan-set \
  --request examples/ticket-context-request.json \
  --result examples/todo2code-zero-plan.json \
  --result-schema schemas/planner-result-envelope.schema.json \
  --out receipts/todo2code-plan-gap.json \
  --now "$NOW" > generated/plan-gap-run.json

python3 adapters/ecosystemctl.py validate-plan-set \
  --request examples/ticket-context-request.json \
  --result examples/todo2code-valid-plan.json \
  --result-schema schemas/planner-result-envelope.schema.json \
  --out receipts/todo2code-plan-valid.json \
  --now "$NOW" > generated/plan-valid-run.json

allow_review python3 adapters/statectl.py \
  --policy priority-evolution.dsl.yaml \
  --ecosystem-map generated/ecosystem-map.json \
  --route generated/ticket-context-selection.json \
  --planner-receipt receipts/todo2code-plan-gap.json \
  --base-state examples/healthy-state.json \
  --revision "$REVISION" \
  --observed-at 2026-08-19T09:59:30Z \
  --out generated/state-from-index.json \
  > generated/state-projection-run.json

allow_review python3 adapters/standardctl.py evaluate \
  --policy priority-evolution.dsl.yaml \
  --state generated/state-from-index.json \
  --now "$NOW" \
  --out receipts/index-grounded-decision.json \
  > generated/index-grounded-evaluation-run.json

python3 adapters/standardctl.py evaluate \
  --policy priority-evolution.dsl.yaml \
  --state examples/healthy-state.json \
  --now "$NOW" \
  --out receipts/healthy-decision.json \
  > generated/healthy-evaluation-run.json

allow_review python3 adapters/standardctl.py evaluate \
  --policy priority-evolution.dsl.yaml \
  --state examples/state.json \
  --now "$NOW" \
  --out receipts/priority-decision.json \
  > generated/problem-evaluation-run.json

python3 adapters/standardctl.py compile-context \
  --policy priority-evolution.dsl.yaml \
  --receipt receipts/index-grounded-decision.json \
  --out-dir . \
  > generated/context-compilation-run.json

python3 scripts/test_report.py \
  --now "$NOW" \
  --json-out generated/verification-report.json \
  --md-out generated/verification-report.md \
  > generated/verification-run.json

cp generated/state-from-index.json .wellmanifest/state/current.json
cp receipts/index-grounded-decision.json .wellmanifest/receipts/priority-decision.json
python3 - <<'PY'
import json
from pathlib import Path
receipt=json.loads(Path('receipts/index-grounded-decision.json').read_text())
Path('.wellmanifest/receipts/intent-plan-delta.json').write_text(
    json.dumps(receipt['planDelta'], ensure_ascii=False, indent=2)+'\n', encoding='utf-8'
)
PY
python3 - <<'PY'
import hashlib
from pathlib import Path
rows = []
for line in Path('MANIFEST.sha256').read_text(encoding='utf-8').splitlines():
    if not line.strip():
        continue
    _, relative = line.split(None, 1)
    path = Path(relative)
    if not path.is_file():
        continue
    rows.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {relative}")
Path('MANIFEST.sha256').write_text("\n".join(rows) + "\n", encoding="utf-8")
PY
