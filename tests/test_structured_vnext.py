"""Prospective typed-answer fixtures; no rc1 status or runtime mutation."""

from __future__ import annotations

import copy
import cmath
import math
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator
import json

from tools.scorers.structured_vnext import evaluate
from tools.validate_cases import load_case


ROOT = Path(__file__).resolve().parents[1]
ANSWER_SCHEMA = Draft202012Validator(json.loads((ROOT / "benchmark/schema/pilot_answer_v0.1.schema.json").read_text(encoding="utf-8")))


def _length(value: float, unit: str = "mm") -> dict:
    return {"value": value, "unit": unit}


def _fraction(value: float) -> dict:
    return {"value": value, "unit": "1"}


POSITIVE = {
    "SEED-1-4": {"q1": {"mirror_count": _fraction(2), "intermediate_leg": "upward", "height_change": _length(50),
                          "output_forward": True, "output_parallel": True},
                 "q2": {"possible_changes": ["image_orientation", "polarization_phase"]},
                 "q3": {"method": "two_separated_planes", "reference": "line_calibrated_parallel_to_input"}},
    "SEED-3-2": {"q1": {"f1": _length(100), "f2": _length(100), "object_to_lens1": _length(100),
                          "lens_separation": _length(200), "lens2_to_image": _length(100)},
                 "q2": {"stop_plane": "between_lenses", "shared_focal_plane": True},
                 "q3": {"represents": "spatial_frequencies", "direct_geometric_image": False}},
    "SEED-3-3": {"q1": {"suppressed": "zero_and_nearby_low_frequencies", "broad_structure": "attenuated",
                          "edge_appearance": "may_be_more_prominent"},
                 "q2": {"filter_class": "high_pass_like"},
                 "q3": {"plane": "fourier", "rejected": "low_frequencies", "higher_frequencies": "transmitted_relative_to_low"}},
    "SEED-7-5": {"q1": {"full_range_possible": False},
                 "q2": {"output_state": "circular", "handedness": "reversed", "analyzer_port_fraction": _fraction(.5),
                          "independent_of_plate_angle": True},
                 "q3": {"stages": ["quarter_wave_linearization", "rotatable_half_wave_plate", "fixed_linear_analyzer"]}},
    "SEED-7-6": {"q1": {"lossless_single_mode_possible": False},
                 "q2": {"input_polarization_rank": _fraction(2), "pure_output_rank": _fraction(1), "orthogonal_component": "other_output_mode"},
                 "q3": {"method": "select_one_pbs_output", "discarded_power_fraction": _fraction(.5)}},
}


ALTERNATIVE = copy.deepcopy(POSITIVE)
ALTERNATIVE["SEED-1-4"]["q1"]["height_change"] = _length(.05, "m")
ALTERNATIVE["SEED-1-4"]["q2"] = ["lateral_offset"]
ALTERNATIVE["SEED-1-4"]["q3"] = {"method": "independent_angle_comparison", "reference": "measured_input_direction"}
ALTERNATIVE["SEED-3-2"]["q1"] = {"f1": _length(10, "cm"), "f2": _length(.1, "m"),
                                   "object_to_lens1": _length(100), "lens_separation": _length(.2, "m"),
                                   "lens2_to_image": _length(10, "cm")}
ALTERNATIVE["SEED-3-2"]["q3"]["represents"] = "angular_spectrum"
ALTERNATIVE["SEED-3-3"]["q1"]["suppressed"] = "low_frequencies"
ALTERNATIVE["SEED-3-3"]["q2"] = "high_pass"
ALTERNATIVE["SEED-7-5"]["q1"] = False
ALTERNATIVE["SEED-7-5"]["q3"] = ["rotatable_quarter_wave_linearization", "fixed_linear_analyzer"]
ALTERNATIVE["SEED-7-6"]["q1"] = False
ALTERNATIVE["SEED-7-6"]["q2"]["orthogonal_component"] = "discarded"
ALTERNATIVE["SEED-7-6"]["q3"]["method"] = "ideal_linear_polarizer"


NEGATIVE = copy.deepcopy(POSITIVE)
NEGATIVE["SEED-1-4"]["q1"]["mirror_count"] = _fraction(1)
NEGATIVE["SEED-1-4"]["q2"] = ["no_other_property_can_change"]
NEGATIVE["SEED-1-4"]["q3"] = {"method": "one_point_hit", "reference": "uncalibrated_aperture_line"}
NEGATIVE["SEED-3-2"]["q1"]["lens_separation"] = _length(100)
NEGATIVE["SEED-3-2"]["q2"]["shared_focal_plane"] = False
NEGATIVE["SEED-3-2"]["q3"]["direct_geometric_image"] = True
NEGATIVE["SEED-3-3"]["q1"]["suppressed"] = "high_frequencies"
NEGATIVE["SEED-3-3"]["q2"] = "low_pass"
NEGATIVE["SEED-3-3"]["q3"]["rejected"] = "high_frequencies"
NEGATIVE["SEED-7-5"]["q1"] = True
NEGATIVE["SEED-7-5"]["q2"]["output_state"] = "linear"
NEGATIVE["SEED-7-5"]["q3"] = ["half_wave_plate_only"]
NEGATIVE["SEED-7-6"]["q1"] = True
NEGATIVE["SEED-7-6"]["q2"]["orthogonal_component"] = "compressed_losslessly_into_same_mode"
NEGATIVE["SEED-7-6"]["q3"] = {"method": "waveplate_only", "discarded_power_fraction": _fraction(0)}


BOUNDARY = copy.deepcopy(POSITIVE)
BOUNDARY["SEED-1-4"]["q1"]["height_change"] = _length(49.9)
BOUNDARY["SEED-1-4"]["q2"]["possible_changes"] = ["novel_effect"]
BOUNDARY["SEED-1-4"]["q3"] = {"method": "two_separated_planes", "reference": "unmodeled_input_reference"}
BOUNDARY["SEED-3-2"]["q1"]["f2"] = _length(101)
BOUNDARY["SEED-3-2"]["q2"] = {"stop_plane": "alternative_fourier_location", "shared_focal_plane": True}
BOUNDARY["SEED-3-2"]["q3"] = {"represents": "novel_phase_space_description", "direct_geometric_image": False}
BOUNDARY["SEED-3-3"]["q1"]["edge_appearance"] = "phase_dependent_outcome"
BOUNDARY["SEED-3-3"]["q2"] = "novel_filter_term"
BOUNDARY["SEED-3-3"]["q3"]["higher_frequencies"] = "phase_weighted"
BOUNDARY["SEED-7-5"]["q1"] = {"conditional": "nonideal_input"}
BOUNDARY["SEED-7-5"]["q2"]["analyzer_port_fraction"] = _fraction(.49)
BOUNDARY["SEED-7-5"]["q3"] = ["novel_conversion_scheme"]
BOUNDARY["SEED-7-6"]["q1"] = {"conditional": "temporal_multiplexing"}
BOUNDARY["SEED-7-6"]["q2"]["orthogonal_component"] = "unmodeled_ancillary_channel"
BOUNDARY["SEED-7-6"]["q3"] = {"method": "different_filter", "discarded_power_fraction": _fraction(.5)}


ADVERSARIAL = copy.deepcopy(POSITIVE)
ADVERSARIAL["SEED-1-4"]["q1"]["output_parallel"] = False
ADVERSARIAL["SEED-1-4"]["q3"] = {"method": "two_separated_planes", "reference": "uncalibrated_aperture_line"}
ADVERSARIAL["SEED-3-2"]["q1"]["object_to_lens1"] = _length(200)
ADVERSARIAL["SEED-3-2"]["q2"] = {"stop_plane": "ordinary_image_plane", "shared_focal_plane": True}
ADVERSARIAL["SEED-3-3"]["q1"]["edge_appearance"] = "always_enhanced"
ADVERSARIAL["SEED-3-3"]["q3"]["higher_frequencies"] = "blocked"
ADVERSARIAL["SEED-7-5"]["q2"]["independent_of_plate_angle"] = False
ADVERSARIAL["SEED-7-5"]["q3"]["stages"].append("half_wave_plate_only")
ADVERSARIAL["SEED-7-6"]["q2"]["orthogonal_component"] = "compressed_losslessly_into_same_mode"
ADVERSARIAL["SEED-7-6"]["q3"]["discarded_power_fraction"] = _fraction(0)


EXPECTED = {
    "positive": {case_id: ("pass", "pass", "pass") for case_id in POSITIVE},
    "alternative_valid": {case_id: ("pass", "pass", "pass") for case_id in POSITIVE},
    "negative": {case_id: ("fail", "fail", "fail") for case_id in POSITIVE},
    "boundary": {"SEED-1-4": ("fail", "unresolved", "unresolved"),
                 "SEED-3-2": ("fail", "unresolved", "unresolved"),
                 "SEED-3-3": ("unresolved", "unresolved", "unresolved"),
                 "SEED-7-5": ("unresolved", "fail", "unresolved"),
                 "SEED-7-6": ("unresolved", "unresolved", "unresolved")},
    "adversarial": {"SEED-1-4": ("fail", "pass", "fail"),
                    "SEED-3-2": ("fail", "fail", "pass"),
                    "SEED-3-3": ("fail", "pass", "fail"),
                    "SEED-7-5": ("pass", "fail", "fail"),
                    "SEED-7-6": ("pass", "fail", "fail")},
}


class StructuredVnextTests(unittest.TestCase):
    def test_fixture_matrix(self) -> None:
        for kind, matrix in (("positive", POSITIVE), ("alternative_valid", ALTERNATIVE),
                             ("negative", NEGATIVE), ("boundary", BOUNDARY), ("adversarial", ADVERSARIAL)):
            for case_id, answers in matrix.items():
                with self.subTest(kind=kind, case_id=case_id):
                    case = load_case(ROOT / "benchmark/cases" / f"{case_id}.yaml")
                    payload = {"answers": answers}
                    self.assertTrue(ANSWER_SCHEMA.is_valid(payload))
                    verdicts = evaluate(case, payload)
                    self.assertEqual([v["criterion_id"] for v in verdicts], [c["id"] for c in case["scoring"]["criteria"]])
                    self.assertEqual(tuple(v["status"] for v in verdicts), EXPECTED[kind][case_id])
                    self.assertTrue(all(v["evidence"] for v in verdicts))

    def test_missing_is_local_and_novel_form_abstains(self) -> None:
        case = load_case(ROOT / "benchmark/cases/SEED-3-3.yaml")
        answer = {"answers": copy.deepcopy(POSITIVE["SEED-3-3"])}
        answer["answers"].pop("q2")
        answer["answers"]["q3"] = {"field_transfer_function": "1-minus-central-stop"}
        self.assertEqual([v["status"] for v in evaluate(case, answer)], ["pass", "fail", "fail"])
        # Missing typed paths fail locally; an unknown typed value abstains.
        answer["answers"]["q2"] = {"filter_class": "nonstandard_but_possible"}
        self.assertEqual(evaluate(case, answer)[1]["status"], "unresolved")

    def test_independent_optics_relations(self) -> None:
        # Two identically oriented diagonal mirrors send +x to +z, then +z
        # back to +x. The mirror separation sets the 50 mm vertical lift.
        normal = (1 / math.sqrt(2), -1 / math.sqrt(2))
        def reflect(ray: tuple[float, float]) -> tuple[float, float]:
            dot = sum(a * b for a, b in zip(ray, normal))
            return (ray[0] - 2 * dot * normal[0], ray[1] - 2 * dot * normal[1])
        intermediate = reflect((1, 0))
        output = reflect(intermediate)
        self.assertAlmostEqual(intermediate[0], 0)
        self.assertAlmostEqual(intermediate[1], 1)
        self.assertAlmostEqual(output[0], 1)
        self.assertAlmostEqual(output[1], 0)
        self.assertEqual(100 - 50, 50)
        # Relay distances follow object=f1, lens separation=f1+f2, image=f2.
        f = .1
        self.assertAlmostEqual((f + f) / f, 2)
        def multiply(a: tuple[tuple[float, float], tuple[float, float]],
                     b: tuple[tuple[float, float], tuple[float, float]]) -> tuple:
            return tuple(tuple(sum(a[i][k] * b[k][j] for k in range(2)) for j in range(2)) for i in range(2))
        propagate = ((1, f), (0, 1))
        lens = ((1, 0), (-1 / f, 1))
        between = ((1, 2 * f), (0, 1))
        relay = propagate
        for stage in (lens, between, lens, propagate):
            relay = multiply(relay, stage)
        self.assertAlmostEqual(relay[0][0], -1)
        self.assertAlmostEqual(relay[1][1], -1)
        self.assertAlmostEqual(relay[0][1], 0)
        self.assertAlmostEqual(relay[1][0], 0)
        # A centered Fourier stop rejects the DC component of a constant
        # field but passes the nonzero harmonics of a sinusoidal field.
        n = 16
        constant = [complex(1) for _ in range(n)]
        fringe = [complex(math.cos(2 * math.pi * j / n)) for j in range(n)]
        dft = lambda signal, k: sum(signal[j] * cmath.exp(-2j * math.pi * k * j / n) for j in range(n))
        self.assertAlmostEqual(abs(dft(constant, 0)), n)
        self.assertAlmostEqual(abs(dft(fringe, 0)), 0, places=12)
        self.assertAlmostEqual(abs(dft(fringe, 1)), n / 2)
        # An ideal HWP flips helicity; the overlap of either circular state
        # with one linear analyzer axis has squared modulus 1/2.
        circular = (complex(1 / math.sqrt(2)), complex(0, 1 / math.sqrt(2)))
        hwp_output = (circular[0], -circular[1])
        self.assertAlmostEqual((circular[0].conjugate() * circular[1]).imag,
                               -(hwp_output[0].conjugate() * hwp_output[1]).imag)
        self.assertAlmostEqual(abs(circular[0]) ** 2, .5)
        # The unpolarized coherency matrix has rank two and a selected
        # linear-polarization projector transmits half its trace.
        matrix = ((.5, 0), (0, .5))
        self.assertAlmostEqual(matrix[0][0] / (matrix[0][0] + matrix[1][1]), .5)

    def test_prose_and_unregistered_cases_are_not_certified(self) -> None:
        case = load_case(ROOT / "benchmark/cases/SEED-7-5.yaml")
        answer = {"answers": {"q1": "No", "q2": "HWP flips helicity", "q3": "Use a QWP"}}
        self.assertEqual([v["status"] for v in evaluate(case, answer)], ["unresolved"] * 3)
        unrelated = load_case(ROOT / "benchmark/cases/SEED-1-3.yaml")
        self.assertEqual(evaluate(unrelated, answer), [])

    def test_missing_numeric_fields_fail_locally(self) -> None:
        for case_id, qid, field, criterion_index in (("SEED-1-4", "q1", "mirror_count", 0),
                                                      ("SEED-7-5", "q2", "analyzer_port_fraction", 1),
                                                      ("SEED-7-6", "q3", "discarded_power_fraction", 2)):
            with self.subTest(case_id=case_id, field=field):
                case = load_case(ROOT / "benchmark/cases" / f"{case_id}.yaml")
                answer = {"answers": copy.deepcopy(POSITIVE[case_id])}
                answer["answers"][qid].pop(field)
                observed = evaluate(case, answer)
                self.assertEqual(observed[criterion_index]["status"], "fail")
                self.assertEqual(observed[criterion_index]["details"]["failure_class"], "missing_claim")
                self.assertEqual(sum(v["status"] == "pass" for v in observed), 2)


if __name__ == "__main__":
    unittest.main()
