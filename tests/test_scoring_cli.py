"""Exercise the published local entry point and its exit-code distinction."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "tools" / "evaluate_answer.py"


class ScoringCliTests(unittest.TestCase):
    def test_success_writes_schema_record(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "result.json"
            run = subprocess.run(
                [sys.executable, str(CLI), "--case", "SEED-1-5", "--answer",
                 str(ROOT / "examples" / "SEED-1-5-answer.json"), "--output", str(output)],
                cwd=ROOT, capture_output=True, text=True,
            )
            self.assertEqual(run.returncode, 0, run.stderr)
            result = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(result["failure_mode"], "none")
            self.assertEqual(result["scores"]["capped_total"], 1.0)
            self.assertIn("score=1.0", run.stderr)

    def test_invalid_json_yields_scored_failure_not_crash(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            answer = Path(temp) / "bad.json"
            answer.write_text("{bad", encoding="utf-8")
            run = subprocess.run(
                [sys.executable, str(CLI), "--case", "SEED-1-5", "--answer", str(answer)],
                cwd=ROOT, capture_output=True, text=True,
            )
            self.assertEqual(run.returncode, 0, run.stderr)
            result = json.loads(run.stdout)
            self.assertEqual(result["failure_mode"], "invalid_contract")
            self.assertEqual(result["scores"]["capped_total"], 0)

    def test_unsupported_case_is_evaluator_failure(self) -> None:
        run = subprocess.run(
            [sys.executable, str(CLI), "--case", "SEED-8-2", "--show-contract"],
            cwd=ROOT, capture_output=True, text=True,
        )
        self.assertEqual(run.returncode, 2)
        self.assertIn("Evaluator failure", run.stderr)


if __name__ == "__main__":
    unittest.main()
