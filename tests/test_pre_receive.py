from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "hooks" / "pre-receive"


class PreReceiveTests(unittest.TestCase):
    def state_for(self, revision: str, *, plan_gap: int = 0) -> dict:
        state = json.loads((ROOT / "examples" / "healthy-state.json").read_text(encoding="utf-8"))
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        state["revision"] = revision
        for value in state["metrics"].values():
            value["revision"] = revision
            value["observedAt"] = now
        state["metrics"]["planning.todo2code_plan_gap_count"]["value"] = plan_gap
        return state

    def run_hook(self, state: dict, lines: str) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            state_path = directory / "state.json"
            receipt_path = directory / "receipt.json"
            state_path.write_text(json.dumps(state), encoding="utf-8")
            env = os.environ.copy()
            env.update({
                "POLICY_ROOT": str(ROOT),
                "POLICY_STATE_PATH": str(state_path),
                "POLICY_RECEIPT_PATH": str(receipt_path),
            })
            return subprocess.run(
                [str(HOOK)],
                input=lines,
                text=True,
                capture_output=True,
                env=env,
                check=False,
            )

    def test_accepts_exact_revision_with_pass_state(self) -> None:
        revision = "a" * 40
        result = self.run_hook(self.state_for(revision), f"{'0' * 40} {revision} refs/heads/main\n")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_rejects_revision_mismatch(self) -> None:
        state = self.state_for("b" * 40)
        result = self.run_hook(state, f"{'0' * 40} {'a' * 40} refs/heads/main\n")
        self.assertEqual(result.returncode, 1)
        self.assertIn("STATE_REVISION_MISMATCH", result.stderr)

    def test_rejects_multiple_new_revisions(self) -> None:
        state = self.state_for("a" * 40)
        lines = (
            f"{'0' * 40} {'a' * 40} refs/heads/main\n"
            f"{'0' * 40} {'b' * 40} refs/heads/release\n"
        )
        result = self.run_hook(state, lines)
        self.assertEqual(result.returncode, 1)
        self.assertIn("MULTI_REVISION_PUSH_UNSUPPORTED", result.stderr)

    def test_rejects_policy_block_with_machine_result(self) -> None:
        revision = "c" * 40
        result = self.run_hook(self.state_for(revision, plan_gap=1), f"{'0' * 40} {revision} refs/heads/main\n")
        self.assertEqual(result.returncode, 1)
        self.assertIn("CODEVALIDATOR_RESULT=", result.stderr)
        self.assertIn("INV-NONEMPTY-GROUNDED-PLAN", result.stderr)


if __name__ == "__main__":
    unittest.main()
