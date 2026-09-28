"""Challenge the separate development route without touching either frozen release."""

from __future__ import annotations

import json
import unittest
from collections import Counter
from pathlib import Path

from jsonschema import Draft202012Validator

from tools.dev_scoring import REGISTERED_CASES, score
from tools.build_open_reasoning_fixtures import all_fixtures


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "benchmark" / "fixtures_vnext"
SCHEMA = json.loads((ROOT / "benchmark/schema/pilot_answer_v0.1.schema.json").read_text(encoding="utf-8"))


class OpenReasoningWaveTests(unittest.TestCase):
    def test_generated_challenges_are_committed_exactly(self) -> None:
        generated = all_fixtures()
        self.assertEqual(len(generated), 30)
        for path, content in generated:
            with self.subTest(path=path.name):
                self.assertEqual(path.read_text(encoding="utf-8"), content)

    def test_explicit_challenges_and_abstention(self) -> None:
        validator = Draft202012Validator(SCHEMA)
        for case_id in sorted(REGISTERED_CASES):
            paths = sorted((FIXTURES / case_id).glob("*.json"))
            self.assertGreaterEqual(len(paths), 8)
            kinds = Counter()
            statuses = Counter()
            for path in paths:
                fixture = json.loads(path.read_text(encoding="utf-8"))
                with self.subTest(case=case_id, fixture=path.name):
                    self.assertEqual(fixture["case_id"], case_id)
                    self.assertTrue(validator.is_valid(fixture["answer"]))
                    result = {item["criterion_id"]: item for item in score(case_id, fixture["answer"])}
                    self.assertEqual(set(result), set(fixture["expected"]))
                    for criterion, expected in fixture["expected"].items():
                        self.assertEqual(result[criterion]["status"], expected["status"])
                        self.assertEqual(result[criterion]["score"],
                                         {"pass": 1, "fail": 0, "unresolved": None}[expected["status"]])
                        statuses[result[criterion]["status"]] += 1
                    kinds[fixture["kind"]] += 1
            self.assertTrue({"positive", "alternative_valid", "negative", "adversarial", "boundary"} <= set(kinds))
            self.assertGreater(statuses["pass"], 0)
            self.assertGreater(statuses["fail"], 0)
            self.assertGreater(statuses["unresolved"], 0)

    def test_route_is_explicit_and_development_only(self) -> None:
        self.assertEqual(REGISTERED_CASES, {"SEED-2-8", "SEED-5-7", "SEED-8-1"})
        with self.assertRaises(ValueError):
            score("SEED-1-1", {"answers": {"q1": True}})
        for case_id in REGISTERED_CASES:
            case = (ROOT / "benchmark" / "cases_vnext" / f"{case_id}.yaml").read_text(encoding="utf-8")
            self.assertIn("validation_status: specified", case)
            self.assertIn("benchmark_release: null", case)

    def test_physical_quantities_behind_valid_claims(self) -> None:
        design = json.loads((FIXTURES / "SEED-8-1/positive_reference_ratio.json").read_text(encoding="utf-8"))["answer"]["answers"]
        current = design["q3"]["unattenuated_current_ma"]["value"] * design["q3"]["attenuation_fraction"]["value"]
        self.assertLess(current, design["q3"]["linear_limit_ma"]["value"])
        self.assertLess(design["q3"]["measured_fractional_noise_floor"]["value"], 1e-4)
        bpp = json.loads((FIXTURES / "SEED-2-8/positive_reciprocal_products.json").read_text(encoding="utf-8"))["answer"]["answers"]["q3"]
        for scenario in bpp["same_beam_scenarios"]:
            self.assertGreaterEqual(scenario["size_ratio"]["value"] * scenario["divergence_ratio"]["value"], 1)
        shot = json.loads((FIXTURES / "SEED-5-7/positive_rin_and_nonlinearity.json").read_text(encoding="utf-8"))["answer"]["answers"]["q2"]
        self.assertEqual(shot["absolute_power_exponent"]["value"] - 1, shot["fractional_power_exponent"]["value"])


if __name__ == "__main__":
    unittest.main()
