"""Independent optics constructions and oracle-integrity tests for closed cases."""

from __future__ import annotations

import copy
import unittest

from tools.physics_checks import check_numeric_claim, expected_si
from tools.scoring_runtime import evaluate_case, load_scored_case


Q = lambda value, unit: {"value": value, "unit": unit}


def _all_pass(result: dict) -> bool:
    return result["scores"]["capped_total"] == 1 and all(
        item["score"] == 1 for item in result["criterion_scores"]
    )


class ClosedPhysicsTests(unittest.TestCase):
    def test_afocal_pairs_with_ray_matrices(self) -> None:
        # Propagate a parallel ray through each thin-lens pair. Both output
        # slopes vanish and both heights have magnitude five times the input.
        for f1, f2, spacing in ((0.020, 0.100, 0.120), (-0.020, 0.100, 0.080)):
            height, slope = 1.0, 0.0
            slope -= height / f1
            height += spacing * slope
            slope -= height / f2
            self.assertAlmostEqual(slope, 0.0, places=12)
            self.assertAlmostEqual(abs(height), 5.0, places=12)
        self.assertAlmostEqual(expected_si(load_scored_case("SEED-2-2"), "afocal_expansion")[0], 5.0)

    def test_gaussian_waist_scaling_from_dimensions(self) -> None:
        case = load_scored_case("SEED-2-4")
        # With fixed wavelength and M², z_R scales as transverse area,
        # while divergence scales as inverse transverse length.
        w1, w2 = 50.0, 100.0
        self.assertAlmostEqual((w2 * w2) / (w1 * w1), expected_si(case, "rayleigh_range_ratio")[0])
        self.assertAlmostEqual(w1 / w2, expected_si(case, "divergence_ratio")[0])

    def test_thin_lens_with_independent_ray_trace(self) -> None:
        case = load_scored_case("SEED-3-1")
        # A ray from object height 1 at x=-2f starts with slope -1/(2f)
        # toward the lens center and reaches height -1 at x=+2f.
        f, object_height = 0.10, 1.0
        ray_height_at_lens, ray_slope_at_lens = 0.0, -object_height / (2 * f)
        image_height = ray_height_at_lens + 2 * f * ray_slope_at_lens
        self.assertAlmostEqual(image_height / object_height, expected_si(case, "thin_lens_magnification")[0])
        self.assertAlmostEqual(2.0, expected_si(case, "thin_lens_image_distance_ratio")[0])

    def test_rayleigh_scale_and_heterodyne_cross_term(self) -> None:
        image_case = load_scored_case("SEED-3-7")
        self.assertAlmostEqual(0.61 * 0.55 / 0.5, expected_si(image_case, "rayleigh_lateral_resolution")[0] * 1e6)
        beat_case = load_scored_case("SEED-5-5")
        self.assertAlmostEqual(80e6, expected_si(beat_case, "heterodyne_beat")[0])
        # 2 cos(2πf1t) cos(2πf2t) contains cos(2π(f2-f1)t);
        # orthogonal Jones vectors have zero complex inner product.
        f1, f2 = 200e6, 280e6
        self.assertEqual(abs(f2 - f1), 80e6)
        signal, orthogonal_lo = (1.0, 0.0), (0.0, 1.0)
        self.assertEqual(sum(a * b for a, b in zip(signal, orthogonal_lo)), 0.0)

    def test_numeric_oracles_follow_changed_givens(self) -> None:
        cases = {
            "SEED-2-2": ("output_diameter", Q(6, "mm"), "n_expansion", Q(4, "1"), Q(4, "1")),
            "SEED-2-4": ("final_waist_radius", Q(150, "um"), "n_rayleigh_ratio", Q(9, "1"), Q(9, "1")),
            "SEED-3-1": ("object_distance_in_focal_lengths", Q(3, "1"), "n_image_distance", Q(1.5, "1"), Q(1.5, "1")),
            "SEED-3-7": ("numerical_aperture", Q(0.25, "1"), "n_rayleigh", Q(1.342, "um"), Q(1.342, "um")),
            "SEED-5-5": ("lo_frequency_offset", Q(100, "MHz"), "n_result", Q(100, "MHz"), Q(100, "MHz")),
        }
        for case_id, (symbol, new_given, check_id, new_gold, candidate) in cases.items():
            with self.subTest(case_id=case_id):
                case = copy.deepcopy(load_scored_case(case_id))
                for given in case["task"]["givens"]:
                    if given["symbol"] == symbol:
                        given.update(new_given)
                check = next(x for x in case["gold"]["numerical_checks"] if x["id"] == check_id)
                old_gold = copy.deepcopy(check["reference"])
                self.assertEqual(check_numeric_claim(case, check, old_gold)["status"], "validator_error")
                check["reference"] = new_gold
                self.assertAlmostEqual(expected_si(case, check["validator_id"])[0],
                                       candidate["value"] * {"1": 1, "um": 1e-6, "MHz": 1e6}[candidate["unit"]],
                                       delta=1e-12 if candidate["unit"] != "MHz" else 1e-3)
                self.assertEqual(check_numeric_claim(case, check, candidate)["status"], "pass")

    def test_corrupt_gold_is_evaluator_error_not_candidate_failure(self) -> None:
        for case_id in ("SEED-2-2", "SEED-2-4", "SEED-3-1", "SEED-3-7", "SEED-5-5"):
            with self.subTest(case_id=case_id):
                case = copy.deepcopy(load_scored_case(case_id))
                case["gold"]["numerical_checks"][0]["reference"]["value"] *= 2
                result = evaluate_case(case, {"answers": {"q1": "candidate"}})
                self.assertEqual(result["failure_mode"], "validator_error")
                self.assertIsNone(result["scores"]["capped_total"])

    def test_unknown_tradeoff_abstains_instead_of_rejecting(self) -> None:
        case = load_scored_case("SEED-2-4")
        answer = {"answers": {"q1": {"rayleigh_range_factor": Q(4, "1")},
                              "q2": {"divergence_factor": Q(0.5, "1")},
                              "q3": {"benefit": "longer_rayleigh_range", "cost": "less nonlinear conversion"}}}
        result = evaluate_case(case, answer)
        self.assertEqual(result["failure_mode"], "oracle_unresolved")
        self.assertIsNone(result["scores"]["capped_total"])


if __name__ == "__main__":
    unittest.main()
