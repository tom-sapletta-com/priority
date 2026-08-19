from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ShadowReceiptTests(unittest.TestCase):
    def test_shadow_log_does_not_authorize_promotion(self) -> None:
        index = json.loads((ROOT / "receipts" / "shadow" / "index.json").read_text())
        self.assertEqual(index["schema"], "subactor.shadow-receipt-log/v1")
        self.assertEqual(index["policyLifecycle"], "candidate")
        self.assertFalse(index["promotionAllowed"])
        self.assertGreaterEqual(index["requiredCount"], 30)
        self.assertGreaterEqual(index["recordedCount"], 1)
        self.assertLess(index["recordedCount"], index["requiredCount"])

    def test_latest_shadow_receipt_never_applied(self) -> None:
        index = json.loads((ROOT / "receipts" / "shadow" / "index.json").read_text())
        receipt = json.loads((ROOT / "receipts" / "shadow" / index["latest"]).read_text())
        self.assertFalse(receipt["applyAttempted"])
        self.assertFalse(receipt["dispatchAllowed"])
        self.assertEqual(receipt["cycleDigest"], index["latestCycleDigest"])


if __name__ == "__main__":
    unittest.main()
