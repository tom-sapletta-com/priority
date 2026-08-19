#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

python3 -m py_compile adapters/*.py
bash -n hooks/pre-receive scripts/rebuild-generated.sh scripts/reconcile.sh scripts/verify.sh
python3 adapters/standardctl.py validate \
  --policy priority-evolution.dsl.yaml \
  --schema schemas/priority-evolution.schema.json
python3 adapters/ecosystemctl.py validate-registry \
  --registry registry/ecosystem-tools.yaml \
  --schema schemas/ecosystem-tool-registry.schema.json
python3 - <<'PY'
import json, jsonschema
for document, schema in [
    ('examples/healthy-state.json','schemas/priority-state.schema.json'),
    ('examples/state.json','schemas/priority-state.schema.json'),
    ('generated/state-from-index.json','schemas/priority-state.schema.json'),
    ('examples/ticket-context-request.json','schemas/ticket-context-request.schema.json'),
    ('examples/todo2code-zero-plan.json','schemas/planner-result-envelope.schema.json'),
    ('examples/todo2code-valid-plan.json','schemas/planner-result-envelope.schema.json'),
    ('generated/ecosystem-map.json','schemas/ecosystem-map.schema.json'),
    ('generated/ticket-context-selection.json','schemas/ticket-context-selection.schema.json'),
    ('receipts/todo2code-plan-gap.json','schemas/plan-validation-receipt.schema.json'),
    ('receipts/todo2code-plan-valid.json','schemas/plan-validation-receipt.schema.json'),
]:
    jsonschema.Draft202012Validator(json.load(open(schema))).validate(json.load(open(document)))
print('JSON schema fixtures: PASS')
PY
python3 -m unittest discover -s tests -v
python3 scripts/test_report.py \
  --now 2026-08-19T10:00:00Z \
  --json-out generated/verification-report.json \
  --md-out generated/verification-report.md \
  > generated/verification-run.json
python3 - <<'PY'
import hashlib, json
from pathlib import Path
report = json.loads(Path('generated/verification-report.json').read_text())
errors = []
for relative, meta in report['outputReceipts'].items():
    actual = "sha256:" + hashlib.sha256(Path(relative).read_bytes()).hexdigest()
    cited = meta.get('fileDigest')
    if cited != actual:
        errors.append(f"{relative}: report {cited} != file {actual}")
if errors:
    raise SystemExit('verification-report fileDigest drift:\n' + '\n'.join(errors))
print('verification-report fileDigest: PASS')
PY
