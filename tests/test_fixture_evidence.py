"""Fixture labels cannot certify their own scientific outcome."""

from __future__ import annotations

import copy
import json
import shutil
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from tools import check_verification_status as status_gate
from tools.fixture_evidence import fixture_kind_issues
from tools.run_case_fixtures import run
from tools.scoring_runtime import ROOT, evaluate_case, load_scored_case


FIXTURES = ROOT / "benchmark" / "fixtures"


class FixtureEvidenceTests(unittest.TestCase):
    def test_negative_declaring_pass_fails_runner_and_challenged_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            copied = Path(temporary) / "fixtures"
            shutil.copytree(FIXTURES, copied)
            negative = copied / "SEED-1-5" / "negative_required_travel.json"
            fixture = json.loads(negative.read_text(encoding="utf-8"))
            reference = json.loads((copied / "SEED-1-5" / "reference.json").read_text(encoding="utf-8"))
            fixture["answer"] = reference["answer"]
            fixture["expected"] = {key: {"status": "pass"} for key in reference["expected"]}
            negative.write_text(json.dumps(fixture), encoding="utf-8")
            _, runner_errors = run(copied)
            self.assertTrue(any("negative fixture needs at least one scored criterion failure" in e for e in runner_errors))
            self.assertTrue(any("negative fixture achieved full success" in e for e in runner_errors))
            with patch.object(status_gate, "FIXTURES", copied):
                gate_errors = status_gate.check()
                original = status_gate.load_scored_case
                def release_case(case_id):
                    case = original(case_id)
                    if case_id == "SEED-1-5":
                        case = copy.deepcopy(case)
                        case["validation_status"] = "release_verified"
                        case["benchmark_release"] = "missing-test-release"
                        case["validation"]["positive_fixtures"] = ["reference.json"]
                        case["validation"]["negative_fixtures"] = ["negative_required_travel.json"]
                    return case
                with patch.object(status_gate, "load_scored_case", side_effect=release_case):
                    release_errors = status_gate.check()
            self.assertTrue(any("negative fixture needs at least one scored criterion failure" in e for e in gate_errors))
            self.assertTrue(any("negative fixture needs at least one scored criterion failure" in e for e in release_errors))

    def test_same_self_certifying_negative_fails_release_gate(self) -> None:
        case = load_scored_case("SEED-1-5")
        reference = json.loads((FIXTURES / "SEED-1-5" / "reference.json").read_text(encoding="utf-8"))
        malicious = {"kind": "negative", "expected": {key: {"status": "pass"} for key in reference["expected"]}}
        result = evaluate_case(case, reference["answer"])
        self.assertIn("negative fixture needs at least one scored criterion failure",
                      fixture_kind_issues(malicious, result, release_verified=True))

    def test_release_adversarial_must_fail_not_abstain(self) -> None:
        case = load_scored_case("SEED-1-5")
        fixture = json.loads((FIXTURES / "SEED-1-5" / "adversarial_false_prose.json").read_text(encoding="utf-8"))
        result = evaluate_case(case, fixture["answer"])
        self.assertEqual(fixture_kind_issues(fixture, result), [])
        self.assertIn("release adversarial fixture must resolve to an actual failure",
                      fixture_kind_issues(fixture, result, release_verified=True))

    def test_boundary_requires_declared_type(self) -> None:
        case = load_scored_case("SEED-1-5")
        fixture = json.loads((FIXTURES / "SEED-1-5" / "inclusive_delay_boundary.json").read_text(encoding="utf-8"))
        result = evaluate_case(case, fixture["answer"])
        self.assertEqual(fixture_kind_issues(fixture, result), [])
        missing = copy.deepcopy(fixture)
        del missing["boundary"]
        self.assertIn("boundary fixture needs {type, criterion_id} metadata", fixture_kind_issues(missing, result))


if __name__ == "__main__":
    unittest.main()
