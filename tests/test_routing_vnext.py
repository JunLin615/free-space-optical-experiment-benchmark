"""Functional and physics challenges for dual-wavelength routing."""

from __future__ import annotations

import copy
import json
import math
import unittest
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from tools.scorers.routing_vnext import evaluate


ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "benchmark/cases_vnext/SEED-8-6.yaml"
FIXTURES = ROOT / "benchmark/fixtures_vnext/SEED-8-6"
SCHEMA = json.loads((ROOT / "benchmark/schema/pilot_answer_v0.1.schema.json").read_text(encoding="utf-8"))


class RoutingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.case = yaml.safe_load(CASE.read_text(encoding="utf-8"))

    def test_architecture_and_boundary_fixtures(self) -> None:
        paths = sorted(FIXTURES.glob("*.json"))
        self.assertGreaterEqual(len(paths), 12)
        kinds = set()
        validator = Draft202012Validator(SCHEMA)
        for path in paths:
            fixture = json.loads(path.read_text(encoding="utf-8"))
            kinds.add(fixture["kind"])
            with self.subTest(fixture=path.name):
                self.assertTrue(validator.is_valid(fixture["answer"]))
                actual = {v["criterion_id"]: v for v in evaluate(self.case, fixture["answer"])}
                self.assertEqual(set(actual), {"c_q1", "c_q2", "c_q3"})
                for criterion, expected in fixture["expected"].items():
                    self.assertEqual(actual[criterion]["status"], expected["status"])
                    self.assertEqual(actual[criterion]["score"],
                                     1 if expected["status"] == "pass" else 0 if expected["status"] == "fail" else None)
        self.assertTrue({"positive", "alternative_valid", "negative", "adversarial", "boundary"} <= kinds)

    def test_two_plane_angle_is_independent_of_common_offset(self) -> None:
        fixture = json.loads((FIXTURES / "positive_dichroic_pair.json").read_text(encoding="utf-8"))
        q2 = fixture["answer"]["answers"]["q2"]
        first, last = q2["planes"]
        dx0 = first["centroids_mm"]["nm532"]["x"]["value"] - first["centroids_mm"]["nm1064"]["x"]["value"]
        dx1 = last["centroids_mm"]["nm532"]["x"]["value"] - last["centroids_mm"]["nm1064"]["x"]["value"]
        independent_angle_mrad = abs(dx1 - dx0) / (last["z_m"]["value"] - first["z_m"]["value"])
        result = {v["criterion_id"]: v for v in evaluate(self.case, fixture["answer"])}
        self.assertTrue(math.isclose(result["c_q2"]["details"]["angle_difference_mrad"], independent_angle_mrad))
        shifted = copy.deepcopy(fixture["answer"])
        for plane in shifted["answers"]["q2"]["planes"]:
            for center in plane["centroids_mm"].values():
                center["x"]["value"] += 100
                center["y"]["value"] -= 200
        shifted_result = {v["criterion_id"]: v for v in evaluate(self.case, shifted)}
        self.assertEqual(shifted_result["c_q2"]["status"], "pass")
        self.assertAlmostEqual(shifted_result["c_q2"]["details"]["angle_difference_mrad"], independent_angle_mrad)

    def test_malformed_values_fail_without_crash(self) -> None:
        fixture = json.loads((FIXTURES / "positive_dichroic_pair.json").read_text(encoding="utf-8"))
        answer = copy.deepcopy(fixture["answer"])
        answer["answers"]["q1"]["routing_matrix"]["nm532"]["detector_532"] = True
        answer["answers"]["q3"]["leakage_test"]["measured_cross_channel_fractions"]["nm532"] = "0.005"
        results = {v["criterion_id"]: v for v in evaluate(self.case, answer)}
        self.assertEqual(results["c_q1"]["status"], "fail")
        self.assertEqual(results["c_q3"]["status"], "fail")


if __name__ == "__main__":
    unittest.main()
