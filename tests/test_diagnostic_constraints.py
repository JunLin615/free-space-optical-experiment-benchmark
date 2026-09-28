"""Independent physics and fixture checks for the diagnostic/constraint wave."""

from __future__ import annotations

import json
import math
import unittest
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from tools.scorers.diagnostic import evaluate


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "benchmark/schema/pilot_answer_v0.1.schema.json").read_text(encoding="utf-8"))


class DiagnosticConstraintTests(unittest.TestCase):
    def test_polarization_fixture_outcomes(self) -> None:
        case = yaml.safe_load((ROOT / "benchmark/cases/SEED-4-8.yaml").read_text(encoding="utf-8"))
        paths = sorted((ROOT / "benchmark/fixtures/SEED-4-8").glob("*.json"))
        self.assertGreaterEqual(len(paths), 10)
        self.assertTrue({"positive", "alternative_valid", "boundary", "negative", "adversarial"} <= {
            json.loads(path.read_text(encoding="utf-8"))["kind"] for path in paths
        })
        validator = Draft202012Validator(SCHEMA)
        for path in paths:
            with self.subTest(fixture=path.name):
                fixture = json.loads(path.read_text(encoding="utf-8"))
                self.assertTrue(validator.is_valid(fixture["answer"]))
                observed = {v["criterion_id"]: v for v in evaluate(case, fixture["answer"])}
                self.assertEqual(set(observed), {c["id"] for c in case["scoring"]["criteria"]})
                self.assertEqual({key: value["status"] for key, value in observed.items()},
                                 {key: value["status"] for key, value in fixture["expected"].items()})

    def test_linear_analyzer_independent_malus_derivative(self) -> None:
        """A finite-difference Malus model reproduces the authored transfer slopes."""
        fixture = json.loads((ROOT / "benchmark/fixtures/SEED-4-8/positive_complementary_channels.json").read_text(encoding="utf-8"))
        channels = fixture["answer"]["answers"]["q1"]["channels"]
        angle = math.pi / 4
        delta = 1e-6
        powers = (lambda theta: math.cos(theta) ** 2, lambda theta: math.sin(theta) ** 2)
        for index, power in enumerate(powers):
            numerical_slope = (power(angle + delta) - power(angle - delta)) / (2 * delta)
            self.assertAlmostEqual(power(angle), channels[index]["bias_power_fraction"]["value"], places=8)
            self.assertAlmostEqual(numerical_slope, channels[index]["rotation_slope_per_rad"]["value"], places=8)
        # An incident-power change multiplies both outputs. The difference at
        # zero rotation remains zero; a small rotation produces a nonzero slope.
        self.assertAlmostEqual(powers[0](angle) - powers[1](angle), 0, places=8)
        self.assertGreater(abs((powers[0](angle + delta) - powers[1](angle + delta)) / delta), 1)

    def test_gain_balanced_alternative_has_physical_polarization_contrast(self) -> None:
        """A partial-contrast Malus analyzer realizes the alternative transfer."""
        fixture = json.loads((ROOT / "benchmark/fixtures/SEED-4-8/positive_gain_balanced_alternative.json").read_text(encoding="utf-8"))
        q1 = fixture["answer"]["answers"]["q1"]
        first, second = q1["channels"]
        fraction = first["bias_power_fraction"]["value"]
        slope = first["rotation_slope_per_rad"]["value"]
        contrast = math.hypot(2 * fraction - 1, slope)
        angle = math.atan2(-slope, 2 * fraction - 1) / 2
        self.assertLessEqual(contrast, 1)
        self.assertAlmostEqual((1 + contrast * math.cos(2 * angle)) / 2, fraction)
        self.assertAlmostEqual(-contrast * math.sin(2 * angle), slope)
        self.assertAlmostEqual(first["effective_gain"]["value"] * fraction,
                               second["effective_gain"]["value"] * second["bias_power_fraction"]["value"])

    def test_diagnostic_typed_conclusions_reject_wrong_cause(self) -> None:
        case = yaml.safe_load((ROOT / "benchmark/cases/SEED-7-2.yaml").read_text(encoding="utf-8"))
        fixture = json.loads((ROOT / "benchmark/fixtures/SEED-7-2/negative_wrong_cause_conclusion.json").read_text(encoding="utf-8"))
        observed = {v["criterion_id"]: v for v in evaluate(case, fixture["answer"])}
        self.assertEqual(observed["c_causes"]["status"], "pass")
        self.assertEqual(observed["c_apertures"]["status"], "pass")
        self.assertEqual(observed["c_diagnosis"]["status"], "fail")
        self.assertEqual(observed["c_diagnosis"]["details"]["failure_class"], "non_discriminating_test")


if __name__ == "__main__":
    unittest.main()
