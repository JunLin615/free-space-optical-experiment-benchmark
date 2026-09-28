"""Fixture and fault-class tests for the autonomous numerical slice."""

from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

import yaml

from tools.scorers.numerical import evaluate


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "benchmark" / "fixtures"


def case_for(case_id: str) -> dict:
    with (ROOT / "benchmark" / "cases" / f"{case_id}.yaml").open(encoding="utf-8") as stream:
        return yaml.safe_load(stream)


def by_criterion(case: dict, answer: dict) -> dict[str, dict]:
    return {verdict["criterion_id"]: verdict for verdict in evaluate(case, answer)}


class NumericalScoringTests(unittest.TestCase):
    def test_machine_readable_fixture_matrix(self) -> None:
        fixture_paths = sorted(FIXTURES.glob("SEED-1-[15]/*.json"))
        self.assertEqual(len(fixture_paths), 26)
        kinds: set[str] = set()
        for path in fixture_paths:
            with self.subTest(fixture=path.name, case=path.parent.name):
                fixture = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(fixture["case_id"], path.parent.name)
                self.assertEqual(fixture["name"], path.stem)
                kinds.add(fixture["kind"])
                verdicts = by_criterion(case_for(fixture["case_id"]), fixture["answer"])
                self.assertEqual(set(verdicts), set(fixture["expected"]))
                for criterion_id, expected in fixture["expected"].items():
                    verdict = verdicts[criterion_id]
                    self.assertEqual(verdict["criterion_id"], criterion_id)
                    self.assertEqual(verdict["check_id"], criterion_id)
                    self.assertEqual(verdict["status"], expected["status"])
                    self.assertEqual(verdict["score"], 1 if expected["status"] == "pass" else 0)
                    self.assertIsInstance(verdict["evidence"], str)
                    self.assertTrue(verdict["evidence"])
                    self.assertIsInstance(verdict["details"], dict)
                    if "failure_class" in expected:
                        self.assertEqual(verdict["details"]["failure_class"], expected["failure_class"])
        self.assertEqual(kinds, {"positive", "boundary", "alternative_valid", "negative", "adversarial"})

    def test_gold_mismatch_is_error_before_missing_claim(self) -> None:
        case = case_for("SEED-1-1")
        case["gold"]["numerical_checks"][0]["reference"]["value"] = 10
        verdicts = by_criterion(case, {})
        self.assertEqual(verdicts["n_angle"]["status"], "error")
        self.assertIsNone(verdicts["n_angle"]["score"])
        self.assertEqual(verdicts["n_angle"]["details"]["failure_class"], "validator_error")
        self.assertEqual(verdicts["n_shift"]["details"]["failure_class"], "missing_claim")

    def test_invalid_instance_is_not_candidate_zero(self) -> None:
        case = case_for("SEED-1-5")
        case["task"]["givens"] = []
        verdicts = by_criterion(case, {})
        self.assertEqual(set(verdicts), {"n_path", "n_delay", "n_travel"})
        for verdict in verdicts.values():
            self.assertEqual(verdict["status"], "error")
            self.assertIsNone(verdict["score"])
            self.assertEqual(verdict["details"]["failure_class"], "invalid_instance")

    def test_broken_comparator_is_invalid_instance(self) -> None:
        case = case_for("SEED-1-5")
        case["gold"]["numerical_checks"][0]["comparator"] = "secret_comparator"
        verdict = by_criterion(case, {})["n_path"]
        self.assertEqual(verdict["status"], "error")
        self.assertEqual(verdict["details"]["failure_class"], "invalid_instance")

    def test_missing_and_malformed_envelope_are_distinct(self) -> None:
        case = case_for("SEED-1-5")
        absent = by_criterion(case, {"answers": {}})
        malformed = by_criterion(case, None)
        self.assertTrue(all(v["details"]["failure_class"] == "missing_claim" for v in absent.values()))
        self.assertTrue(all(v["details"]["failure_class"] == "malformed_claim" for v in malformed.values()))

    def test_unknown_case_is_invalid_instance(self) -> None:
        case = copy.deepcopy(case_for("SEED-1-5"))
        case["case_id"] = "SEED-2-1"
        verdicts = evaluate(case, {})
        self.assertEqual(len(verdicts), 1)
        self.assertEqual(verdicts[0]["status"], "error")
        self.assertEqual(verdicts[0]["details"]["failure_class"], "invalid_instance")


if __name__ == "__main__":
    unittest.main()
