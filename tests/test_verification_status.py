"""Lifecycle labels require executable evidence and pinned release assets."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools import check_verification_status as status_gate


class VerificationStatusTests(unittest.TestCase):
    def test_current_challenged_cases_meet_development_gate(self) -> None:
        self.assertEqual(status_gate.check(), [])

    def test_label_alone_cannot_promote_a_case(self) -> None:
        original = status_gate.load_scored_case
        def changed(case_id):
            case = original(case_id)
            if case_id == "SEED-1-5":
                case = copy.deepcopy(case)
                case["validation_status"] = "release_verified"
                case["benchmark_release"] = "nonexistent-release"
            return case
        with patch.object(status_gate, "load_scored_case", side_effect=changed):
            issues = status_gate.check()
        self.assertTrue(any("missing pinned release manifest" in issue for issue in issues))
        self.assertTrue(any("public development split" in issue for issue in issues))

    def test_release_manifest_must_pin_judge_and_derivation_evidence(self) -> None:
        case = status_gate.load_scored_case("SEED-1-5")
        case = copy.deepcopy(case)
        case["validation"]["semantic_criteria"] = ["c_explanation"]
        case["answer_contract"]["required_result_paths"].append("answers.q1.explanation")
        case["gold"]["judge_rubrics"] = [{"id": "j_explanation", "evidence_path": "answers.q1.explanation"}]
        case["scoring"]["criteria"].append({"id": "c_explanation", "check": "j_explanation", "weight": 0})
        required_file = status_gate.ROOT / "requirements.txt"
        manifest = {
            "cases": {"SEED-1-5": {"case_revision": case["case_revision"]}},
            "files": {"requirements.txt": hashlib.sha256(required_file.read_bytes()).hexdigest()},
            "judge": {
                "mode": "required", "criteria": ["c_explanation"],
                "config": "benchmark/judge/bounded_v0.1.json",
                "calibration_set": "benchmark/judge/calibration_v0.1.json",
                "live_calibration_results": "benchmark/judge/live/unavailable.json",
            },
        }
        with tempfile.TemporaryDirectory() as temporary:
            release_dir = Path(temporary)
            (release_dir / "test-release.json").write_text(json.dumps(manifest), encoding="utf-8")
            with patch.object(status_gate, "RELEASES", release_dir), patch.object(status_gate, "load_scored_case", return_value=case):
                issues = status_gate._manifest_issues("SEED-1-5", "test-release", ["reference.json"])
                self.assertTrue(any("does not pin benchmark/judge/bounded_v0.1.json" in issue for issue in issues))
                self.assertTrue(any("does not pin benchmark/judge/calibration_v0.1.json" in issue for issue in issues))
                self.assertTrue(any("does not pin tests/test_independent_physics.py" in issue for issue in issues))
                self.assertTrue(any("invalid live calibration evidence" in issue for issue in issues))
                manifest["files"]["tests/test_independent_physics.py"] = "0" * 64
                (release_dir / "test-release.json").write_text(json.dumps(manifest), encoding="utf-8")
                issues = status_gate._manifest_issues("SEED-1-5", "test-release", ["reference.json"])
                self.assertTrue(any("release hash mismatch: tests/test_independent_physics.py" in issue for issue in issues))
                manifest["judge"] = {"mode": "disabled"}
                (release_dir / "test-release.json").write_text(json.dumps(manifest), encoding="utf-8")
                issues = status_gate._manifest_issues("SEED-1-5", "test-release", ["reference.json"])
                self.assertTrue(any("semantic scoring path requires judge mode" in issue for issue in issues))

    def test_optional_explanation_alone_needs_no_judge_evidence(self) -> None:
        case = status_gate.load_scored_case("SEED-1-5")
        self.assertTrue(case["answer_contract"]["permit_additional_explanation"])
        files, issues = status_gate._judge_evidence_issues(case, {"judge": {"mode": "disabled"}})
        self.assertEqual(files, set())
        self.assertEqual(issues, [])
        manifest = {
            "cases": {"SEED-1-5": {"case_revision": case["case_revision"]}},
            "files": {"requirements.txt": hashlib.sha256(
                (status_gate.ROOT / "requirements.txt").read_bytes()).hexdigest()},
            "judge": {"mode": "disabled"},
        }
        with tempfile.TemporaryDirectory() as temporary:
            release_dir = Path(temporary)
            (release_dir / "test-release.json").write_text(json.dumps(manifest), encoding="utf-8")
            with patch.object(status_gate, "RELEASES", release_dir):
                manifest_issues = status_gate._manifest_issues("SEED-1-5", "test-release", [])
        self.assertFalse(any("benchmark/judge/" in issue or "calibration" in issue for issue in manifest_issues))

    def test_challenged_case_needs_executable_evidence_inventory(self) -> None:
        original = status_gate.load_scored_case
        def changed(case_id):
            case = original(case_id)
            if case_id == "SEED-1-5":
                case = copy.deepcopy(case)
                case["validation"].pop("evidence_files")
            return case
        with patch.object(status_gate, "load_scored_case", side_effect=changed):
            issues = status_gate.check()
        self.assertTrue(any("lacks executable derivation evidence inventory" in issue for issue in issues))


if __name__ == "__main__":
    unittest.main()
