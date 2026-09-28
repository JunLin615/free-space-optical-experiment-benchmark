"""Boundary and adversarial checks for the SEED-7-2 diagnostic slice."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

import yaml

from tools.scorers.diagnostic import evaluate


ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "benchmark" / "cases" / "SEED-7-2.yaml"
FIXTURES = ROOT / "benchmark" / "fixtures" / "SEED-7-2"


class DiagnosticScoringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.case = yaml.safe_load(CASE.read_text(encoding="utf-8"))

    def test_all_machine_readable_fixtures(self) -> None:
        files = sorted(FIXTURES.glob("*.json"))
        self.assertGreaterEqual(len(files), 8)
        for path in files:
            fixture = json.loads(path.read_text(encoding="utf-8"))
            with self.subTest(fixture=path.name):
                self.assertEqual(fixture["case_id"], self.case["case_id"])
                actual = {v["criterion_id"]: v for v in evaluate(self.case, fixture["answer"])}
                self.assertEqual(set(actual), set(fixture["expected"]))
                for criterion, expected in fixture["expected"].items():
                    result = actual[criterion]
                    self.assertEqual(result["status"], expected["status"])
                    self.assertEqual(result["score"], 1 if expected["status"] == "pass" else 0 if expected["status"] == "fail" else None)
                    self.assertEqual(result["check_id"], criterion)
                    self.assertIsInstance(result["evidence"], str)
                    self.assertIsInstance(result["details"], dict)
                    if "failure_class" in expected:
                        self.assertEqual(result["details"].get("failure_class"), expected["failure_class"])

    def test_missing_claims_have_local_zero_only(self) -> None:
        results = {v["criterion_id"]: v for v in evaluate(self.case, {"answers": {}})}
        self.assertEqual(set(results), {"c_causes", "c_apertures", "c_diagnosis"})
        self.assertTrue(all(v["status"] == "fail" and v["score"] == 0 for v in results.values()))
        self.assertTrue(all(v["details"].get("failure_class") == "missing_claim" for v in results.values()))

    def test_wrong_case_is_explicit_error(self) -> None:
        wrong = {"case_id": "SEED-1-1"}
        results = evaluate(wrong, {"answers": {}})
        self.assertTrue(all(v["status"] == "error" and v["score"] is None for v in results))


if __name__ == "__main__":
    unittest.main()
