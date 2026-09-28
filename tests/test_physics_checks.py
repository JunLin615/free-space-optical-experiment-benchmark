"""Equation, unit, and adversarial checks for the deterministic pilot layer."""

from __future__ import annotations

import math
import unittest
from pathlib import Path

import yaml

from tools.physics_checks import (
    PhysicsCheckError,
    check_case_numeric_claims,
    check_numeric_claim,
    expected_si,
    to_si,
)


ROOT = Path(__file__).resolve().parents[1]


def pilot(case_id: str) -> dict:
    path = ROOT / "benchmark" / "cases" / f"SEED-{case_id.replace('.', '-')}.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


class PhysicsChecksTests(unittest.TestCase):
    def test_mirror_geometry_and_independent_gold(self) -> None:
        case = pilot("1.1")
        checks = {c["id"]: c for c in case["gold"]["numerical_checks"]}
        angle, angle_dim = expected_si(case, "mirror_angle")
        shift, shift_dim = expected_si(case, "mirror_spot_shift")
        self.assertEqual(angle_dim, "angle")
        self.assertEqual(shift_dim, "length")
        self.assertAlmostEqual(angle * 180 / math.pi, 1.0)
        self.assertAlmostEqual(shift * 1000, 34.9101299, places=5)
        self.assertEqual(
            check_numeric_claim(case, checks["n_shift"], {"value": shift * 1000, "unit": "mm"})["status"],
            "pass",
        )
        self.assertEqual(
            check_numeric_claim(case, checks["n_shift"], {"value": 17.45, "unit": "mm"})["status"],
            "fail",
        )

    def test_folded_delay_path_time_and_travel(self) -> None:
        case = pilot("1.5")
        path, _ = expected_si(case, "folded_delay_path")
        delay, _ = expected_si(case, "folded_delay_time")
        travel, _ = expected_si(case, "folded_delay_stage_for_target")
        self.assertAlmostEqual(path * 1000, 2.0)
        self.assertAlmostEqual(delay * 1e12, 6.6712819, places=5)
        self.assertAlmostEqual(travel * 1000, 14.9896229, places=5)

    def test_gaussian_focus_and_michelson(self) -> None:
        radius, _ = expected_si(pilot("2.1"), "gaussian_focus_radius")
        fringes, _ = expected_si(pilot("4.2"), "michelson_fringe_count")
        self.assertAlmostEqual(radius * 1e6, 16.9340859, places=5)
        self.assertEqual(fringes, 1.0)

    def test_half_wave_plate_magnitudes(self) -> None:
        case = pilot("1.7")
        rotation, _ = expected_si(case, "half_wave_relative_rotation_magnitude")
        plate_effect, _ = expected_si(case, "half_wave_plate_rotation_effect")
        self.assertAlmostEqual(rotation * 180 / math.pi, 34)
        self.assertAlmostEqual(plate_effect * 180 / math.pi, 10)

    def test_wrong_dimensions_and_bad_gold(self) -> None:
        case = pilot("1.1")
        check = next(c for c in case["gold"]["numerical_checks"] if c["id"] == "n_angle")
        self.assertEqual(check_numeric_claim(case, check, {"value": 1, "unit": "mm"})["status"], "invalid_contract")
        corrupted = {**check, "reference": {"value": 10.0, "unit": "deg"}}
        self.assertEqual(check_numeric_claim(case, corrupted, {"value": 1, "unit": "deg"})["status"], "validator_error")
        with self.assertRaises(PhysicsCheckError):
            to_si({"value": 1, "unit": "parsec"})

    def test_multiple_claims_from_typed_answer(self) -> None:
        answer = {"answers": {"q1": {"angle_change": {"value": 1, "unit": "deg"}}, "q2": {"spot_displacement": {"value": 35, "unit": "mm"}}}}
        verdicts = check_case_numeric_claims(pilot("1.1"), answer)
        self.assertEqual([v["status"] for v in verdicts], ["pass", "pass"])


if __name__ == "__main__":
    unittest.main()
