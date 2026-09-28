"""End-to-end tests for contract, oracle failure, and result provenance."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator, FormatChecker

from tools.scoring_runtime import ROOT, evaluate_case, load_scored_case


ANSWER = {
    "answers": {
        "q1": {"path_change": {"value": 2, "unit": "mm"}},
        "q2": {"delay_change": {"value": 6.6712819, "unit": "ps"}},
        "q3": {"stage_travel": {"value": 14.9896229, "unit": "mm"}},
    }
}


class ScoringRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.case = load_scored_case("SEED-1-5")
        schema = json.loads((ROOT / "benchmark/schema/result.schema.json").read_text(encoding="utf-8"))
        cls.validator = Draft202012Validator(schema, format_checker=FormatChecker())

    def test_complete_numerical_path_and_resource_accounting(self) -> None:
        context = {
            "system": {"name": "Fixture runner", "model_id": "test-model", "model_version": "1", "scaffold_id": None},
            "protocol": "tool_assisted",
            "tools_available": ["calculator"], "tools_used": ["calculator"], "tool_call_count": 3,
            "tokens": {"input": 120, "output": 44, "total": 164, "cached_input": 20},
            "provider_usage": {"reasoning_tokens": 12, "cache_read_input_tokens": 20},
            "cost": {"amount": 0.0, "currency": "USD", "pricing_reference": "test-price-v1",
                     "pricing_snapshot_utc": "2026-09-28T00:00:00Z"},
            "wall_time_seconds": 2.5, "retry_count": 1,
        }
        result = evaluate_case(self.case, ANSWER, raw_answer=json.dumps(ANSWER), context=context)
        self.assertEqual(result["failure_mode"], "none")
        self.assertEqual(result["scores"]["capped_total"], 1.0)
        self.assertEqual(result["tool_call_count"], 3)
        self.assertEqual(result["provider_usage"]["reasoning_tokens"], 12)
        self.assertEqual(len(result["case_content_sha256"]), 64)
        self.assertEqual(len(result["evaluator_fingerprint"]), 64)
        self.assertTrue(all(v["version"] for v in result["validator_results"]))
        self.assertEqual(list(self.validator.iter_errors(result)), [])

    def test_corrupted_authored_gold_is_not_an_agent_failure(self) -> None:
        case = copy.deepcopy(self.case)
        case["gold"]["numerical_checks"][0]["reference"]["value"] = 3.0
        result = evaluate_case(case, ANSWER)
        self.assertEqual(result["failure_mode"], "validator_error")
        self.assertIsNone(result["scores"]["capped_total"])
        self.assertTrue(all(v["score"] is None for v in result["criterion_scores"]))
        self.assertEqual(list(self.validator.iter_errors(result)), [])

    def test_malformed_answer_is_scored_zero_and_distinct(self) -> None:
        result = evaluate_case(self.case, {"answers": {"q1": 3}}, raw_answer="malformed")
        self.assertEqual(result["failure_mode"], "invalid_contract")
        self.assertEqual(result["scores"]["capped_total"], 0)
        self.assertEqual(list(self.validator.iter_errors(result)), [])

    def test_wrong_value_is_a_normal_scored_failure(self) -> None:
        answer = copy.deepcopy(ANSWER)
        answer["answers"]["q2"]["delay_change"]["value"] = 3.0
        result = evaluate_case(self.case, answer)
        self.assertEqual(result["failure_mode"], "physics_fail")
        self.assertEqual(result["scores"]["capped_total"], 0.65)
        self.assertEqual(list(self.validator.iter_errors(result)), [])

    def test_correct_numbers_do_not_silently_validate_optional_prose(self) -> None:
        answer = copy.deepcopy(ANSWER)
        answer["explanation"] = "The delay line is single pass despite these tabulated numbers."
        result = evaluate_case(self.case, answer)
        self.assertEqual(result["failure_mode"], "judge_unresolved")
        self.assertIsNone(result["scores"]["capped_total"])
        self.assertEqual(result["judge_results"][0]["check_id"], "explanation_consistency")
        self.assertEqual(list(self.validator.iter_errors(result)), [])

    def test_bounded_judge_only_resolves_configured_residual(self) -> None:
        case = load_scored_case("SEED-2-8")
        answer = {"answers": {"q1": {"achievable": False},
                              "q2": {"invariant": "phase_space_volume", "behavior": "conserved"},
                              "q3": {"reduce_size": "divergence_increases", "reduce_divergence": "size_increases"}}}
        unresolved = evaluate_case(case, answer, judge_criteria={"c_invariant": "Explain the invariant"})
        self.assertEqual(unresolved["failure_mode"], "judge_unresolved")
        self.assertIsNone(unresolved["scores"]["capped_total"])
        def backend(prompt, config):
            return json.dumps({"verdict": "pass", "evidence_quote": "phase_space_volume",
                               "reason": "This names a conserved optical phase-space quantity."})
        resolved = evaluate_case(case, answer, judge_criteria={"c_invariant": "Explain the invariant"},
                                 judge_backend=backend)
        self.assertEqual(resolved["scores"]["capped_total"], 1.0)
        self.assertEqual(resolved["judge_results"][0]["status"], "pass")
        self.assertEqual(next(v for v in resolved["validator_results"] if v["check_id"] == "c_invariant")["status"], "unresolved")
        self.assertEqual(list(self.validator.iter_errors(resolved)), [])

    def test_judge_cannot_override_hard_physics_failure(self) -> None:
        case = load_scored_case("SEED-2-8")
        answer = {"answers": {"q1": {"achievable": True},
                              "q2": {"invariant": "etendue", "behavior": "conserved"},
                              "q3": {"reduce_size": "divergence_increases", "reduce_divergence": "size_increases"}}}
        def backend(prompt, config):
            self.fail("backend should not be called for deterministic failure")
        result = evaluate_case(case, answer, judge_criteria={"c_impossible": "Is it feasible?"},
                               judge_backend=backend)
        self.assertEqual(result["failure_mode"], "constraint_fail")
        self.assertLessEqual(result["scores"]["capped_total"], 0.49)
        self.assertEqual(result["judge_results"], [])


if __name__ == "__main__":
    unittest.main()
