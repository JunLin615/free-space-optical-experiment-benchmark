"""Independent physics challenges for the five remaining deterministic-ready cases.

These calculations do not call the production formula registry to obtain the
expected values. Scorer calls below only check whether those independently
calculated values, changed givens, and corrupt references are handled safely.
"""

from __future__ import annotations

import cmath
import copy
import json
import math
import unittest
from pathlib import Path

from tools.physics_checks import check_numeric_claim
from tools.scoring_runtime import evaluate_case, load_scored_case
from tools.scorers.closed_vnext import evaluate as evaluate_closed_vnext
from tools.vnext.units import normalize_answer_units
from tools.vnext.scoring_runtime import evaluate_case as evaluate_vnext_case
from tools.validate_cases import load_case, semantic_issues


ROOT = Path(__file__).resolve().parents[1]


def quantity(value: float, unit: str) -> dict:
    return {"value": value, "unit": unit}


def change_given(case: dict, symbol: str, value: float, unit: str) -> None:
    next(g for g in case["task"]["givens"] if g["symbol"] == symbol).update(quantity(value, unit))


def numeric_check(case: dict, check_id: str) -> dict:
    return next(check for check in case["gold"]["numerical_checks"] if check["id"] == check_id)


class RemainingDeterministicEvidence(unittest.TestCase):
    def test_vnext_focus_contract_separates_numerical_estimate_from_decade_choice(self) -> None:
        old = load_scored_case("SEED-2-1")
        case = load_case(ROOT / "benchmark/cases_vnext/SEED-2-1.yaml")
        self.assertEqual(case["case_revision"], "0.3.0")
        self.assertNotEqual(old["task"]["questions"][0], case["task"]["questions"][0])
        self.assertFalse(semantic_issues(case))

        # Fourier-limited Gaussian waist; finite q-parameter propagation gives
        # the same estimate to the stated accuracy without using scorer code.
        wavelength, focal, radius = 532e-9, 0.100, 1.0e-3
        z_rayleigh = math.pi * radius * radius / wavelength
        q_out = 1 / (1 / (1j * z_rayleigh) - 1 / focal)
        independent_waist = math.sqrt(wavelength * q_out.imag / math.pi)
        self.assertAlmostEqual(independent_waist * 1e6, 16.93, delta=0.01)

        answer = {"answers": {
            "q1": {"waist_radius": quantity(20, "um")},
            "q2": {"closest_scale": quantity(10, "um")},
            "q3": {"waist_radius_factor": quantity(0.5, "1")},
        }}
        result = evaluate_case(case, answer)
        self.assertEqual(result["scores"]["capped_total"], 1)
        self.assertEqual(evaluate_vnext_case(case, answer)["scores"]["capped_total"], 1)
        decade_in_numeric_slot = copy.deepcopy(answer)
        decade_in_numeric_slot["answers"]["q1"]["waist_radius"]["value"] = 10
        results = evaluate_case(case, decade_in_numeric_slot)
        self.assertEqual({x["check_id"]: x["status"] for x in results["validator_results"]}["n_waist"], "fail")
        self.assertEqual({x["check_id"]: x["status"] for x in results["validator_results"]}["c_scale"], "pass")

        high = copy.deepcopy(answer)
        high["answers"]["q1"]["waist_radius"]["value"] = 20.4
        self.assertEqual({x["check_id"]: x["status"] for x in evaluate_case(case, high)["validator_results"]}["n_waist"], "fail")
        wrong_dimension = copy.deepcopy(answer)
        wrong_dimension["answers"]["q1"]["waist_radius"] = quantity(20, "MHz")
        self.assertEqual({x["check_id"]: x["status"] for x in evaluate_case(case, wrong_dimension)["validator_results"]}["n_waist"], "fail")

        mutated = copy.deepcopy(case)
        change_given(mutated, "focal_length", 200, "mm")
        check = numeric_check(mutated, "n_waist")
        self.assertEqual(check_numeric_claim(mutated, check, check["reference"])["status"], "validator_error")
        check["reference"] = quantity(33.86, "um")
        self.assertEqual(check_numeric_claim(mutated, check, check["reference"])["status"], "pass")
        corrupt = copy.deepcopy(case)
        numeric_check(corrupt, "n_waist")["reference"]["value"] *= 2
        self.assertEqual(evaluate_case(corrupt, answer)["failure_mode"], "validator_error")

        for name in ("positive_reference", "positive_rounded_17um", "alternative_valid_units",
                     "alternative_valid_rounded_estimate"):
            fixture = json.loads((ROOT / "benchmark/fixtures/SEED-2-1" / f"{name}.json").read_text(encoding="utf-8"))
            self.assertEqual(evaluate_case(case, fixture["answer"])["scores"]["capped_total"], 1, name)
        old_decade = json.loads((ROOT / "benchmark/fixtures/SEED-2-1/alternative_valid_order_scale.json").read_text(encoding="utf-8"))
        self.assertLess(evaluate_case(case, old_decade["answer"])["scores"]["capped_total"], 1)
        self.assertLess(evaluate_vnext_case(case, old_decade["answer"])["scores"]["capped_total"], 1)

    def test_gaussian_range_and_divergence_from_paraxial_envelope(self) -> None:
        case = copy.deepcopy(load_scored_case("SEED-2-4"))
        # Gaussian envelope: w(z)^2=w0^2+(lambda*z/(pi*w0))^2.
        # Set w(z)^2=2*w0^2 to obtain z_R, and read the far-field slope.
        wavelength = 633e-9
        initial, final = 50e-6, 100e-6
        z = lambda waist: math.pi * waist**2 / wavelength
        slope = lambda waist: wavelength / (math.pi * waist)
        self.assertAlmostEqual(z(final) / z(initial), 4)
        self.assertAlmostEqual(slope(final) / slope(initial), 0.5)
        self.assertEqual(check_numeric_claim(case, numeric_check(case, "n_rayleigh_ratio"), quantity(4, "1"))["status"], "pass")
        self.assertEqual(check_numeric_claim(case, numeric_check(case, "n_divergence_ratio"), quantity(0.5, "1"))["status"], "pass")

        change_given(case, "final_waist_radius", 150, "um")
        for check_id, revised in (("n_rayleigh_ratio", 9), ("n_divergence_ratio", 1 / 3)):
            check = numeric_check(case, check_id)
            self.assertEqual(check_numeric_claim(case, check, check["reference"])["status"], "validator_error")
            check["reference"] = quantity(revised, "1")
            self.assertEqual(check_numeric_claim(case, check, check["reference"])["status"], "pass")

    def test_thin_lens_conjugates_from_ray_transfer(self) -> None:
        case = copy.deepcopy(load_scored_case("SEED-3-1"))
        # A ray leaving object height h with arbitrary slope a reaches the
        # image plane at h*(1-v)+a*f*(u*(1-v)+v), for u=s/f and v=s'/f.
        # Focus requires the coefficient of a to vanish.
        for u, expected_v, expected_m in ((2, 2, -1), (3, 1.5, -0.5)):
            v = u / (u - 1)
            self.assertAlmostEqual(u * (1 - v) + v, 0)
            self.assertAlmostEqual(v, expected_v)
            self.assertAlmostEqual(1 - v, expected_m)
        change_given(case, "object_distance_in_focal_lengths", 3, "1")
        for check_id, revised in (("n_image_distance", 1.5), ("n_magnification", -0.5)):
            check = numeric_check(case, check_id)
            self.assertEqual(check_numeric_claim(case, check, check["reference"])["status"], "validator_error")
            check["reference"] = quantity(revised, "1")
            self.assertEqual(check_numeric_claim(case, check, check["reference"])["status"], "pass")

    def test_airy_resolution_and_na_depth_trend(self) -> None:
        case = copy.deepcopy(load_scored_case("SEED-3-7"))
        # First Airy zero at 1.22 lambda/D, with NA approximately D/(2f).
        wavelength, na = 550e-9, 0.5
        resolution = 1.22 * wavelength / (2 * na)
        self.assertAlmostEqual(resolution * 1e6, 0.671)
        self.assertEqual(min((0.1e-6, 1e-6, 10e-6), key=lambda x: abs(x - resolution)), 1e-6)
        self.assertLess(1 / 0.7**2, 1 / 0.5**2)  # depth range scales down with increased NA
        change_given(case, "wavelength", 600, "nm")
        change_given(case, "numerical_aperture", 0.4, "1")
        check = numeric_check(case, "n_rayleigh")
        self.assertEqual(check_numeric_claim(case, check, check["reference"])["status"], "validator_error")
        check["reference"] = quantity(0.915, "um")
        self.assertEqual(check_numeric_claim(case, check, check["reference"])["status"], "pass")

    def test_heterodyne_cross_term_and_orthogonal_limit(self) -> None:
        case = copy.deepcopy(load_scored_case("SEED-5-5"))
        beat_hz = 80e6
        # Optical carrier cancels in the complex envelope. A square-law
        # detector sees a difference-frequency cross term for parallel fields.
        def intensity(t: float, overlap: complex) -> float:
            return 2 + 2 * (overlap * cmath.exp(-2j * math.pi * beat_hz * t)).real
        self.assertAlmostEqual(intensity(0, 1), 4)
        self.assertAlmostEqual(intensity(0.5 / beat_hz, 1), 0)
        self.assertAlmostEqual(intensity(0, 0), intensity(0.5 / beat_hz, 0))
        self.assertEqual(check_numeric_claim(case, numeric_check(case, "n_result"), quantity(0.08, "GHz"))["status"], "pass")
        change_given(case, "lo_frequency_offset", 125, "MHz")
        check = numeric_check(case, "n_result")
        self.assertEqual(check_numeric_claim(case, check, check["reference"])["status"], "validator_error")
        check["reference"] = quantity(125, "MHz")
        self.assertEqual(check_numeric_claim(case, check, check["reference"])["status"], "pass")

    def test_corrupted_gold_is_evaluator_error_for_each_case(self) -> None:
        for case_id in ("SEED-2-4", "SEED-3-1", "SEED-3-7", "SEED-5-5"):
            with self.subTest(case_id=case_id):
                case = copy.deepcopy(load_scored_case(case_id))
                case["gold"]["numerical_checks"][0]["reference"]["value"] *= 3
                result = evaluate_case(case, {"answers": {}})
                self.assertEqual(result["failure_mode"], "validator_error")
                self.assertIsNone(result["scores"]["capped_total"])

    def test_vnext_closed_claim_fixture_challenges(self) -> None:
        for case_id in ("SEED-3-1", "SEED-3-7", "SEED-5-5"):
            with self.subTest(case_id=case_id):
                case = load_case(ROOT / "benchmark/cases_vnext" / f"{case_id}.yaml")
                self.assertFalse(semantic_issues(case))
                fixtures = sorted((ROOT / "benchmark/fixtures_vnext" / case_id).glob("*.json"))
                self.assertEqual(len(fixtures), 12)
                counts = {}
                for path in fixtures:
                    fixture = json.loads(path.read_text(encoding="utf-8"))
                    counts[fixture["kind"]] = counts.get(fixture["kind"], 0) + 1
                    verdicts = evaluate_closed_vnext(case, normalize_answer_units(fixture["answer"]))
                    self.assertEqual({v["criterion_id"] for v in verdicts}, {c["id"] for c in case["scoring"]["criteria"]})
                    self.assertTrue(all(v["status"] in ("pass", "fail") for v in verdicts), path.name)
                    full_credit = all(v["status"] == "pass" for v in verdicts)
                    self.assertEqual(full_credit, fixture["expected"]["full_credit"], path.name)
                    integrated = evaluate_vnext_case(case, fixture["answer"])
                    self.assertNotIn(integrated["failure_mode"], ("validator_error", "oracle_unresolved", "judge_unresolved"), path.name)
                    self.assertEqual(integrated["scores"]["capped_total"] == 1,
                                     fixture["expected"]["full_credit"], path.name)
                self.assertEqual(counts, {"positive": 2, "alternative_valid": 2, "boundary": 2,
                                          "negative": 4, "adversarial": 2})


if __name__ == "__main__":
    unittest.main()
