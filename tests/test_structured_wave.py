"""Fixture and independent optical checks for the bounded structured wave."""

from __future__ import annotations

import json
import math
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from tools.scorers.structured_wave import evaluate
from tools.validate_cases import load_case


ROOT = Path(__file__).resolve().parents[1]
IDS = ("SEED-1-3", "SEED-1-6", "SEED-4-1", "SEED-7-8")
SCHEMA = json.loads((ROOT / "benchmark/schema/pilot_answer_v0.1.schema.json").read_text(encoding="utf-8"))


def _case(case_id: str) -> dict:
    return load_case(ROOT / "benchmark/cases" / f"{case_id}.yaml")


def _fixture(case_id: str, kind: str) -> dict:
    return json.loads((ROOT / "benchmark/fixtures" / case_id / f"{kind}.json").read_text(encoding="utf-8"))


class StructuredWaveTests(unittest.TestCase):
    def test_fixtures_cover_each_criterion_and_question(self) -> None:
        schema = Draft202012Validator(SCHEMA)
        for case_id in IDS:
            case = _case(case_id)
            criteria = {c["id"] for c in case["scoring"]["criteria"]}
            self.assertEqual({q["id"] for q in case["task"]["questions"]}, {"q1", "q2", "q3"})
            for kind in ("positive", "alternative_valid", "negative", "boundary", "adversarial"):
                with self.subTest(case=case_id, kind=kind):
                    fixture = _fixture(case_id, kind)
                    self.assertEqual(fixture["case_id"], case_id)
                    self.assertEqual(fixture["kind"], kind)
                    self.assertTrue(schema.is_valid(fixture["answer"]))
                    observed = {v["criterion_id"]: v for v in evaluate(case, fixture["answer"])}
                    self.assertEqual(set(observed), criteria)
                    self.assertEqual(set(fixture["expected"]), criteria)
                    for cid, expected in fixture["expected"].items():
                        verdict = observed[cid]
                        self.assertEqual(verdict["check_id"], cid)
                        self.assertEqual(verdict["status"], expected["status"])
                        self.assertEqual(verdict["score"], {"pass": 1, "fail": 0, "unresolved": None}[expected["status"]])
                        self.assertTrue(verdict["evidence"])
                        if "failure_class" in expected:
                            self.assertEqual(verdict["details"].get("failure_class"), expected["failure_class"])

    def test_two_parallel_reflections_restore_forward_ray(self) -> None:
        # Reflect a +x ray through two parallel 45-degree mirror planes.
        incident = (1 / math.sqrt(2), -1 / math.sqrt(2))

        def reflect(ray: tuple[float, float]) -> tuple[float, float]:
            dot = sum(a * b for a, b in zip(ray, incident))
            return tuple(a - 2 * dot * b for a, b in zip(ray, incident))

        first = reflect((1.0, 0.0))
        second = reflect(first)
        self.assertAlmostEqual(first[0], 0)
        self.assertAlmostEqual(first[1], 1)
        self.assertAlmostEqual(second[0], 1)
        self.assertAlmostEqual(second[1], 0)
        self.assertNotEqual(first, second)

    def test_mirror_offset_uses_authored_given_and_units(self) -> None:
        case = _case("SEED-1-3")
        case["task"]["givens"][0]["value"] = 40
        fixture = _fixture("SEED-1-3", "positive")
        answer = fixture["answer"]
        answer["answers"]["q1"]["lateral_offset"] = {"value": 4, "unit": "cm"}
        self.assertEqual(evaluate(case, answer)[0]["status"], "pass")
        answer["answers"]["q1"]["lateral_offset"] = {"value": 30, "unit": "mm"}
        self.assertEqual(evaluate(case, answer)[0]["status"], "fail")

    def test_dichroic_polarization_not_unconditionally_preserved(self) -> None:
        # A 45-degree input has equal s/p components. Unequal coating amplitudes
        # alter the output normalized Jones magnitudes even if ports route correctly.
        input_jones = (1 / math.sqrt(2), 1 / math.sqrt(2))
        output_jones = (input_jones[0], 0.5 * input_jones[1])
        self.assertNotAlmostEqual(abs(output_jones[0]), abs(output_jones[1]))
        case = _case("SEED-1-6")
        answer = _fixture("SEED-1-6", "positive")["answer"]
        answer["answers"]["q3"]["unconditionally_preserved"] = True
        self.assertEqual(evaluate(case, answer)[2]["status"], "fail")

    def test_quarter_wave_jones_extremes(self) -> None:
        # At 45 degrees, J=(1,i)/sqrt(2) has equal components in quadrature.
        equal = (complex(1 / math.sqrt(2)), complex(0, 1 / math.sqrt(2)))
        s3 = 2 * (equal[0].conjugate() * equal[1]).imag
        self.assertAlmostEqual(abs(s3), 1.0)
        axis_aligned = (complex(1), complex(0))
        self.assertAlmostEqual(2 * (axis_aligned[0].conjugate() * axis_aligned[1]).imag, 0)

    def test_gaussian_relation_for_smaller_waist(self) -> None:
        wavelength = 1064e-9
        m2 = 1.2
        large = math.pi * (2e-4)**2 / (m2 * wavelength)
        small = math.pi * (1e-4)**2 / (m2 * wavelength)
        self.assertAlmostEqual(small / large, 0.25)
        self.assertLess(small, large)
        case = _case("SEED-7-8")
        answer = _fixture("SEED-7-8", "alternative_valid")["answer"]
        self.assertEqual([v["status"] for v in evaluate(case, answer)], ["pass"] * 3)

    def test_novel_forms_abstain_and_missing_claims_are_local(self) -> None:
        case = _case("SEED-4-1")
        answer = _fixture("SEED-4-1", "positive")["answer"]
        answer["answers"]["q1"] = {"stokes": [1, 0, 0, 1]}
        answer["answers"].pop("q2")
        observed = [v["status"] for v in evaluate(case, answer)]
        self.assertEqual(observed, ["unresolved", "fail", "pass"])

    def test_unknown_additional_claims_do_not_get_certified(self) -> None:
        polarization = _fixture("SEED-4-1", "positive")["answer"]
        polarization["answers"]["q3"]["depends_on"].append("some_unmodeled_dependency")
        self.assertEqual(evaluate(_case("SEED-4-1"), polarization)[2]["status"], "unresolved")
        focus = _fixture("SEED-7-8", "positive")["answer"]
        focus["answers"]["q3"]["costs"].append("unknown_tradeoff")
        self.assertEqual(evaluate(_case("SEED-7-8"), focus)[2]["status"], "unresolved")


if __name__ == "__main__":
    unittest.main()
