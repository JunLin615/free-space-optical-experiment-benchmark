"""Causal alignment scorer challenges, including unknown alternatives."""

from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from tools.scorers.diagnostic_vnext import evaluate


ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "benchmark/cases_vnext/SEED-7-1.yaml"
FIXTURES = ROOT / "benchmark/fixtures_vnext/SEED-7-1"
SCHEMA = json.loads((ROOT / "benchmark/schema/pilot_answer_v0.1.schema.json").read_text(encoding="utf-8"))


class CausalAlignmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.case = yaml.safe_load(CASE.read_text(encoding="utf-8"))

    def test_fixtures_cover_valid_alternative_adversarial_and_abstention(self) -> None:
        validator = Draft202012Validator(SCHEMA)
        paths = sorted(FIXTURES.glob("*.json"))
        self.assertGreaterEqual(len(paths), 10)
        kinds = set()
        for path in paths:
            fixture = json.loads(path.read_text(encoding="utf-8"))
            kinds.add(fixture["kind"])
            with self.subTest(fixture=path.name):
                self.assertEqual(fixture["case_id"], self.case["case_id"])
                self.assertTrue(validator.is_valid(fixture["answer"]))
                actual = {v["criterion_id"]: v for v in evaluate(self.case, fixture["answer"])}
                self.assertEqual(set(actual), {"c_q1", "c_q2", "c_q3"})
                for criterion, expected in fixture["expected"].items():
                    self.assertEqual(actual[criterion]["status"], expected["status"])
                    self.assertEqual(actual[criterion]["score"],
                                     1 if expected["status"] == "pass" else 0 if expected["status"] == "fail" else None)
        self.assertTrue({"positive", "alternative_valid", "negative", "adversarial", "boundary"} <= kinds)

    def test_non_string_and_unhashable_claims_do_not_crash(self) -> None:
        fixture = json.loads((FIXTURES / "positive_reference_and_reach.json").read_text(encoding="utf-8"))
        answer = copy.deepcopy(fixture["answer"])
        answer["answers"]["q1"]["causes"][0]["prediction"]["test"] = ["alternate_near_far"]
        answer["answers"]["q3"]["steps"][0]["test"] = {"name": "survey_aperture_centers"}
        result = {v["criterion_id"]: v for v in evaluate(self.case, answer)}
        self.assertEqual(result["c_q1"]["status"], "fail")
        self.assertEqual(result["c_q3"]["status"], "fail")

    def test_two_aperture_geometry_is_reference_dependent(self) -> None:
        fixture = json.loads((FIXTURES / "positive_reference_and_reach.json").read_text(encoding="utf-8"))
        cause = fixture["answer"]["answers"]["q1"]["causes"][1]
        self.assertEqual(cause["family"], "reference_axis_mismatch")
        self.assertIn("reference_line", cause["mechanism"])
        self.assertEqual(cause["prediction"]["test"], "survey_aperture_centers")
        self.assertEqual(evaluate(self.case, fixture["answer"])[0]["status"], "pass")


if __name__ == "__main__":
    unittest.main()
