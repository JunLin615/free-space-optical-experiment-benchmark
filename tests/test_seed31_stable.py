"""Independent regression for the stable thin-lens answer-unit contract."""

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

from tools.stable.scoring_runtime import evaluate_case as evaluate_stable, load_scored_case as load_stable
from tools.vnext.scoring_runtime import evaluate_case as evaluate_rc1, load_scored_case as load_rc1


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "benchmark/fixtures_stable/SEED-3-1"


def statuses(result: dict) -> dict[str, str]:
    return {item["check_id"]: item["status"] for item in result["validator_results"]}


class StableThinLensContract(unittest.TestCase):
    def test_stable_revision_preserves_the_scientific_question(self) -> None:
        stable = load_stable("SEED-3-1")
        rc1 = load_rc1("SEED-3-1")
        self.assertEqual(stable["case_revision"], "0.4.0")
        self.assertEqual(rc1["case_revision"], "0.3.0")
        self.assertEqual(stable["task"], rc1["task"])
        self.assertEqual(stable["gold"]["numerical_checks"], rc1["gold"]["numerical_checks"])

        manifest = json.loads((ROOT / "benchmark/releases/0.2.0-rc1.json").read_text(encoding="utf-8"))
        old_path = "benchmark/cases_vnext/SEED-3-1.yaml"
        self.assertEqual(hashlib.sha256((ROOT / old_path).read_bytes()).hexdigest(), manifest["files"][old_path])

    def test_focal_length_symbol_is_accepted_only_for_q1(self) -> None:
        case = load_stable("SEED-3-1")
        expected = {
            "alternative_two_f": ("pass", "pass", "pass"),
            "negative_wrong_f_value": ("fail", "pass", "pass"),
            "negative_wrong_f_dimension": ("fail", "pass", "pass"),
            "negative_f_magnification": ("pass", "fail", "pass"),
        }
        for name, wanted in expected.items():
            with self.subTest(name=name):
                fixture = json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))
                result = evaluate_stable(case, fixture["answer"])
                self.assertEqual(tuple(statuses(result)[key] for key in (
                    "n_image_distance", "n_magnification", "c_image_character")), wanted)
                self.assertEqual(result["scores"]["capped_total"] == 1, all(x == "pass" for x in wanted))
                self.assertNotIn(result["failure_mode"], ("validator_error", "oracle_unresolved"))

    def test_historical_rc1_rejects_exact_anomaly_while_stable_accepts_it(self) -> None:
        answer = json.loads((FIXTURES / "alternative_two_f.json").read_text(encoding="utf-8"))["answer"]
        historical = evaluate_rc1(load_rc1("SEED-3-1"), answer)
        stable = evaluate_stable(load_stable("SEED-3-1"), answer)
        self.assertEqual(statuses(historical)["n_image_distance"], "fail")
        self.assertEqual(historical["failure_mode"], "invalid_contract")
        self.assertEqual(historical["scores"]["capped_total"], 0.6)
        self.assertEqual(statuses(stable)["n_image_distance"], "pass")
        self.assertEqual(stable["scores"]["capped_total"], 1)

    def test_every_stable_fixture_resolves_under_stable_scorer(self) -> None:
        case = load_stable("SEED-3-1")
        paths = sorted(FIXTURES.glob("*.json"))
        self.assertEqual(len(paths), 17)
        for path in paths:
            with self.subTest(fixture=path.name):
                fixture = json.loads(path.read_text(encoding="utf-8"))
                result = evaluate_stable(case, fixture["answer"])
                self.assertNotIn(result["failure_mode"], ("validator_error", "oracle_unresolved", "judge_unresolved"))
                for check_id, wanted in fixture["expected"].items():
                    actual = next(item for item in result["validator_results"] if item["check_id"] == check_id)
                    self.assertEqual(actual["status"], wanted["status"])
                    if "failure_class" in wanted:
                        self.assertEqual(actual["details"].get("failure_class"), wanted["failure_class"])

    def test_missing_q1_unit_is_a_malformed_candidate_answer(self) -> None:
        fixture = json.loads((FIXTURES / "negative_missing_q1_unit.json").read_text(encoding="utf-8"))
        result = evaluate_stable(load_stable("SEED-3-1"), fixture["answer"])
        self.assertEqual(result["failure_mode"], "invalid_contract")
        self.assertEqual(result["scores"]["capped_total"], 0.49)
        self.assertEqual(statuses(result)["answer_schema"], "fail")
        self.assertEqual(statuses(result)["n_image_distance"], "fail")


if __name__ == "__main__":
    unittest.main()
