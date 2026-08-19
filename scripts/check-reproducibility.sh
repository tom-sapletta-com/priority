#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
OUT="${1:-generated/reproducibility-report.json}"
NOW="${NOW:-2026-08-19T10:00:00Z}"
files=(
  generated/ecosystem-map.json
  generated/llms.txt
  generated/subactor-map-diff.json
  generated/ticket-context-selection.json
  tickets/ticket-001/context-selection.json
  tickets/ticket-001/todo2code-request.json
  tickets/ticket-001/CONTEXT.md
  tickets/ticket-001/receipt.json
  receipts/todo2code-plan-gap.json
  receipts/todo2code-plan-valid.json
  generated/state-from-index.json
  receipts/index-grounded-decision.json
  receipts/healthy-decision.json
  receipts/priority-decision.json
  .wellmanifest/generated/agent-policy.md
  AGENTS.md
  CLAUDE.md
  GEMINI.md
)

before="$(mktemp)"
after="$(mktemp)"
trap 'rm -f "$before" "$after"' EXIT
sha256sum "${files[@]}" > "$before"
NOW="$NOW" ./scripts/rebuild-generated.sh
sha256sum "${files[@]}" > "$after"
status=PASS
if ! cmp -s "$before" "$after"; then
  status=FAIL
fi
python3 - "$OUT" "$NOW" "$status" "$after" <<'PY'
import hashlib,json,sys
from pathlib import Path
out,now,status,manifest_path=sys.argv[1:]
files={}
for line in Path(manifest_path).read_text().splitlines():
    sha,path=line.split(None,1)
    files[path.strip()]=f"sha256:{sha}"
report={
    'schema':'subactor.reproducibility-report/v1',
    'generatedAt':now,
    'status':status,
    'files':files,
}
raw=json.dumps(report,sort_keys=True,separators=(',',':')).encode()
report['reportDigest']='sha256:'+hashlib.sha256(raw).hexdigest()
Path(out).parent.mkdir(parents=True,exist_ok=True)
Path(out).write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'status':status,'fileCount':len(files),'reportDigest':report['reportDigest']},indent=2))
PY
[[ "$status" == PASS ]]
