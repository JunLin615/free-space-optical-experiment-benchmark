"""Bounded semantic-judge software checks, not live reliability evidence."""

from __future__ import annotations

import json
import unittest

from tools.calibrate_judge import measure
from tools.semantic_judge import judge_criterion


class SemanticJudgeTests(unittest.TestCase):
    def test_no_backend_remains_unresolved(self) -> None:
        result = judge_criterion(criterion_id="c_test", criterion="causal test", candidate_text="an iris test")
        self.assertEqual(result["status"], "unresolved")

    def test_deterministic_failure_cannot_be_overridden(self) -> None:
        calls = []
        def backend(prompt, config):
            calls.append(prompt)
            return json.dumps({"verdict": "pass", "evidence_quote": "hello", "reason": "good"})
        result = judge_criterion(criterion_id="c_test", criterion="test", candidate_text="hello",
                                 backend=backend, deterministic_gate="fail")
        self.assertEqual(result["status"], "not_applicable")
        self.assertEqual(calls, [])

    def test_evidence_must_occur_in_candidate(self) -> None:
        def backend(prompt, config):
            return json.dumps({"verdict": "pass", "evidence_quote": "invented evidence", "reason": "good"})
        result = judge_criterion(criterion_id="c_test", criterion="test", candidate_text="other text", backend=backend)
        self.assertEqual(result["status"], "unresolved")

    def test_backend_failure_abstains(self) -> None:
        def backend(prompt, config):
            raise TimeoutError("backend unavailable")
        result = judge_criterion(criterion_id="c_test", criterion="test", candidate_text="other text", backend=backend)
        self.assertEqual(result["status"], "unresolved")

    def test_empty_evidence_abstains(self) -> None:
        def backend(prompt, config):
            return json.dumps({"verdict": "pass", "evidence_quote": "", "reason": "good"})
        result = judge_criterion(criterion_id="c_test", criterion="test", candidate_text="other text", backend=backend)
        self.assertEqual(result["status"], "unresolved")

    def test_calibration_metrics_cannot_claim_readiness_from_tiny_replay(self) -> None:
        from tools.calibrate_judge import SET
        items = json.loads(SET.read_text(encoding="utf-8"))["items"]
        replay = {item["id"]: [item["expected"], item["expected"]] for item in items}
        metrics = measure(replay)
        self.assertTrue(metrics)
        self.assertTrue(all(not item["release_ready"] for item in metrics.values()))
        self.assertTrue(all(item["false_pass_rate"] == 0 for item in metrics.values()))


if __name__ == "__main__":
    unittest.main()
