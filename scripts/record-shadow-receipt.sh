#!/usr/bin/env bash
# Copy a cycle receipt into receipts/shadow without promoting lifecycle.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CYCLE_DIR="${1:-$ROOT/runtime/cycle}"
SRC="$CYCLE_DIR/receipts/autonomy-cycle.json"
if [[ ! -f "$SRC" ]]; then
  echo "missing cycle receipt: $SRC" >&2
  exit 2
fi
python3 - "$ROOT" "$SRC" <<'PY'
import json, hashlib, shutil
from pathlib import Path
import sys
root = Path(sys.argv[1])
src = Path(sys.argv[2])
shadow = root / "receipts" / "shadow"
shadow.mkdir(parents=True, exist_ok=True)
cycle = json.loads(src.read_text(encoding="utf-8"))
if cycle.get("applyAttempted") is True:
    raise SystemExit("refuse to archive a cycle that attempted apply")
if cycle.get("dispatchAllowed") is True:
    raise SystemExit("refuse to archive a dispatching cycle while policy is candidate")
existing = sorted(p for p in shadow.glob("*.json") if p.name != "index.json")
seq = len(existing) + 1
dest = shadow / f"{seq:04d}-autonomy-cycle.json"
shutil.copyfile(src, dest)
index = {
    "schema": "subactor.shadow-receipt-log/v1",
    "policyLifecycle": "candidate",
    "requiredCount": 30,
    "recordedCount": seq,
    "promotionAllowed": False,
    "latest": dest.name,
    "latestCycleDigest": cycle.get("cycleDigest"),
    "latestRevision": cycle.get("revision"),
    "latestOutcome": cycle.get("finalOutcome"),
    "note": "Shadow receipts are observations. They do not promote candidate to shadow.",
}
index["indexDigest"] = "sha256:" + hashlib.sha256(
    json.dumps(index, sort_keys=True, separators=(",", ":")).encode()
).hexdigest()
(shadow / "index.json").write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"recorded": dest.name, "recordedCount": seq, "promotionAllowed": False}, indent=2))
PY
