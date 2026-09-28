"""Challenge fixtures for conceptual and open-design structured scoring."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from tools.scorers.structured import evaluate


ROOT = Path(__file__).resolve().parents[1]
CASE_DIR = ROOT / "benchmark" / "cases"
FIXTURE_DIR = ROOT / "benchmark" / "fixtures"
ANSWER_SCHEMA = json.loads((ROOT / "benchmark" / "schema" / "pilot_answer_v0.1.schema.json").read_text(encoding="utf-8"))


class StructuredScoringTests(unittest.TestCase):
    def test_all_challenge_fixtures(self) -> None:
        validator = Draft202012Validator(ANSWER_SCHEMA)
        for case_id in ("SEED-2-8", "SEED-5-3"):
            with self.subTest(case=case_id):
                case = yaml.safe_load((CASE_DIR / f"{case_id}.yaml").read_text(encoding="utf-8"))
                paths = sorted((FIXTURE_DIR / case_id).glob("*.json"))
                self.assertGreaterEqual(len(paths), 5)
                categories = {path.stem.split("_", 1)[0] for path in paths}
                self.assertTrue({"positive", "negative", "boundary", "adversarial"} <= categories)
                for path in paths:
                    with self.subTest(fixture=path.name):
                        fixture = json.loads(path.read_text(encoding="utf-8"))
                        self.assertEqual(fixture["case_id"], case_id)
                        self.assertTrue(validator.is_valid(fixture["answer"]), path.name)
                        verdicts = evaluate(case, fixture["answer"])
                        actual = {item["criterion_id"]: item for item in verdicts}
                        self.assertEqual(set(actual), {item["id"] for item in case["scoring"]["criteria"]})
                        self.assertEqual(set(actual), set(fixture["expected"]))
                        for criterion_id, expected in fixture["expected"].items():
                            observed = actual[criterion_id]
                            self.assertEqual(observed["check_id"], criterion_id)
                            self.assertEqual(observed["status"], expected["status"])
                            self.assertEqual(observed["score"], {"pass": 1, "fail": 0, "unresolved": None, "error": None}[expected["status"]])
                            self.assertTrue(observed["evidence"])
                            self.assertIsInstance(observed["details"], dict)
                            if "failure_class" in expected:
                                self.assertEqual(observed["details"].get("failure_class"), expected["failure_class"])

    def test_missing_question_only_fails_dependent_criterion(self) -> None:
        case = yaml.safe_load((CASE_DIR / "SEED-2-8.yaml").read_text(encoding="utf-8"))
        answer = {"answers": {"q1": {"achievable": False}, "q2": {"invariant": "etendue", "behavior": "cannot_decrease"}}}
        verdicts = {item["criterion_id"]: item for item in evaluate(case, answer)}
        self.assertEqual(verdicts["c_impossible"]["status"], "pass")
        self.assertEqual(verdicts["c_invariant"]["status"], "pass")
        self.assertEqual(verdicts["c_tradeoff"]["details"]["failure_class"], "missing_claim")

    def test_unrecognized_design_alternative_abstains(self) -> None:
        case = yaml.safe_load((CASE_DIR / "SEED-5-3.yaml").read_text(encoding="utf-8"))
        fixture = json.loads((FIXTURE_DIR / "SEED-5-3" / "positive_ratio.json").read_text(encoding="utf-8"))
        fixture["answer"]["answers"]["q1"]["comparison"] = "frequency_multiplexed_reference"
        verdicts = {item["criterion_id"]: item for item in evaluate(case, fixture["answer"])}
        self.assertEqual(verdicts["c_channels"]["status"], "unresolved")
        self.assertEqual(verdicts["c_normalize"]["status"], "pass")
        self.assertEqual(verdicts["c_residuals"]["status"], "pass")


if __name__ == "__main__":
    unittest.main()
