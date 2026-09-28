"""Independent challenges for the newly executable closed optics cases."""

from __future__ import annotations

import copy
import math
import unittest

from tools.physics_checks import check_numeric_claim, expected_si
from tools.scoring_runtime import evaluate_case, load_scored_case


def quantity(value: float, unit: str) -> dict:
    return {"value": value, "unit": unit}


def change_given(case: dict, symbol: str, value: float, unit: str) -> None:
    item = next(item for item in case["task"]["givens"] if item["symbol"] == symbol)
    item.update(quantity(value, unit))


class DeterministicQualificationTests(unittest.TestCase):
    def test_folded_delay_public_geometry_is_explicit(self) -> None:
        statement = load_scored_case("SEED-1-5")["task"]["statement"]
        self.assertIn("moving-stage gap once on the outbound leg", statement)
        self.assertIn("once on the return leg", statement)

    def test_half_wave_jones_reflection_and_circular_handedness(self) -> None:
        case = load_scored_case("SEED-1-7")
        a = math.radians(17)
        # In the fast/slow Jones basis a half-wave plate maps [cos a, sin a]
        # to [cos a, -sin a], so the output angle is -a.
        incident = (math.cos(a), math.sin(a))
        output = (incident[0], -incident[1])
        angle_change = abs(math.atan2(output[1], output[0]) - a)
        self.assertAlmostEqual(angle_change, expected_si(case, "half_wave_relative_rotation_magnitude")[0])

        # Rotating the plate by 5 degrees changes the lab-frame output
        # from -17 to -7 degrees: a 10-degree displacement.
        new_axis = math.radians(5)
        new_output = 2 * new_axis - a
        self.assertAlmostEqual(abs(new_output + a), expected_si(case, "half_wave_plate_rotation_effect")[0])

        circular = (1 / math.sqrt(2), 1j / math.sqrt(2))
        after_plate = (circular[0], -circular[1])
        self.assertAlmostEqual(abs(after_plate[0]), abs(after_plate[1]))
        self.assertEqual(after_plate[1] / after_plate[0], -1j)
        self.assertNotEqual(circular[1] / circular[0], after_plate[1] / after_plate[0])

    def test_gaussian_focus_independent_q_parameter(self) -> None:
        case = load_scored_case("SEED-2-1")
        wavelength, focal, radius = 532e-9, 0.1, 1e-3
        z_rayleigh = math.pi * radius**2 / wavelength
        q_after_lens = 1 / ((1 / (1j * z_rayleigh)) - 1 / focal)
        waist = math.sqrt(wavelength * q_after_lens.imag / math.pi)
        # The authored equation is the collimated, f << z_R approximation;
        # the q-parameter calculation retains the finite input curvature.
        self.assertAlmostEqual(waist, expected_si(case, "gaussian_focus_radius")[0], delta=3e-9)
        self.assertEqual(min((1e-6, 10e-6, 1e-3), key=lambda x: abs(x - waist)), 10e-6)

    def test_michelson_phase_counts_independently(self) -> None:
        case = load_scored_case("SEED-4-2")
        for mirror_wavelengths, opd_validator, fringe_validator in (
            (0.5, "michelson_opd_change_half", "michelson_fringe_count"),
            (0.25, "michelson_opd_change_quarter", "michelson_fringe_count_quarter"),
        ):
            # The returning field accumulates k(2d), so cycles are phase/(2 pi).
            phase = 2 * math.pi * (2 * mirror_wavelengths)
            self.assertAlmostEqual(phase / (2 * math.pi), expected_si(case, opd_validator)[0])
            self.assertAlmostEqual(phase / (2 * math.pi), expected_si(case, fringe_validator)[0])
        self.assertAlmostEqual(2 * math.pi * 2 * 0.25, math.pi)

    def test_michelson_signed_opd_is_magnitude_equivalent(self) -> None:
        case = load_scored_case("SEED-4-2")
        answer = {"answers": {
            "q1": {"opd_change_in_wavelengths": quantity(-1, "1")},
            "q2": {"fringe_cycles": quantity(1, "1")},
            "q3": {"opd_change_in_wavelengths": quantity(-0.5, "1"),
                   "fringe_cycles": quantity(0.5, "1")},
        }}
        result = evaluate_case(case, answer)
        self.assertEqual(result["scores"]["capped_total"], 1)
        self.assertTrue(all(item["score"] == 1 for item in result["criterion_scores"]))

    def test_mutated_givens_invalidate_old_gold(self) -> None:
        changes = (
            ("SEED-1-1", "mirror_rotation", 1, "deg", "n_angle", 2, "deg"),
            ("SEED-1-5", "stage_displacement", 2, "mm", "n_path", 4, "mm"),
            ("SEED-1-7", "input_to_fast_axis_angle", 20, "deg", "n_rotation", 40, "deg"),
            ("SEED-1-7", "plate_rotation", 8, "deg", "n_plate_effect", 16, "deg"),
            ("SEED-2-1", "focal_length", 200, "mm", "n_waist", 33.86, "um"),
            ("SEED-4-2", "mirror_displacement_wavelengths", 0.75, "1", "n_opd_half", 1.5, "1"),
            ("SEED-4-2", "quarter_mirror_displacement_wavelengths", 0.125, "1", "n_fringe_quarter", 0.25, "1"),
        )
        for case_id, symbol, value, unit, check_id, gold_value, gold_unit in changes:
            with self.subTest(case_id=case_id, symbol=symbol):
                case = copy.deepcopy(load_scored_case(case_id))
                change_given(case, symbol, value, unit)
                check = next(c for c in case["gold"]["numerical_checks"] if c["id"] == check_id)
                self.assertEqual(check_numeric_claim(case, check, check["reference"])["status"], "validator_error")
                check["reference"] = quantity(gold_value, gold_unit)
                self.assertEqual(check_numeric_claim(case, check, check["reference"])["status"], "pass")

    def test_corrupt_gold_is_evaluator_failure(self) -> None:
        for case_id in ("SEED-1-7", "SEED-2-1", "SEED-4-2"):
            with self.subTest(case_id=case_id):
                case = copy.deepcopy(load_scored_case(case_id))
                case["gold"]["numerical_checks"][0]["reference"]["value"] *= 3
                result = evaluate_case(case, {"answers": {}})
                self.assertEqual(result["failure_mode"], "validator_error")
                self.assertIsNone(result["scores"]["capped_total"])


if __name__ == "__main__":
    unittest.main()
