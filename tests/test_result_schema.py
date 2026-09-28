"""Check the proposed run record contract with representative data."""

from __future__ import annotations

import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator, FormatChecker


SCHEMA_PATH = Path(__file__).resolve().parents[1] / "benchmark" / "schema" / "result.schema.json"


class ResultSchemaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        self.validator = Draft202012Validator(self.schema, format_checker=FormatChecker())
        self.record = {
            "result_schema_version": "0.1.0",
            "case_id": "SEED-2.1",
            "benchmark_version": "0.1.0-dev",
            "system": {"name": "Example system", "model_id": "model-x", "model_version": None, "scaffold_id": None},
            "protocol": "closed_book",
            "case_library_access": {"available": False, "snapshot_id": None, "retrieved_document_ids": []},
            "tools_available": [],
            "tools_used": [],
            "tool_call_count": 0,
            "tokens": {"input": None, "output": None, "total": None},
            "provider_usage": None,
            "cost": None,
            "wall_time_seconds": 1.2,
            "retry_count": 0,
            "raw_answer": "example",
            "structured_answer": {},
            "validator_results": [{"check_id": "numeric", "status": "pass", "score": 1.0}],
            "judge_results": [],
            "criterion_scores": [{"criterion_id": "numeric", "score": 1.0, "weight": 1.0}],
            "scores": {"raw_total": 1.0, "capped_total": 1.0},
        }

    def test_schema_and_example_record(self) -> None:
        Draft202012Validator.check_schema(self.schema)
        self.assertEqual(list(self.validator.iter_errors(self.record)), [])

    def test_unknown_usage_is_distinct_from_zero_and_bad_scores_fail(self) -> None:
        self.assertIsNone(self.record["tokens"]["input"])
        self.assertIsNone(self.record["provider_usage"])
        self.assertIsNone(self.record["cost"])
        self.assertEqual(self.record["tool_call_count"], 0)
        self.record["criterion_scores"][0]["score"] = 1.2
        self.assertTrue(list(self.validator.iter_errors(self.record)))

    def test_tool_call_count_and_provider_usage_are_independent_of_tool_names(self) -> None:
        self.record["tools_available"] = ["ray_trace"]
        self.record["tools_used"] = ["ray_trace"]
        self.record["tool_call_count"] = 3
        self.record["provider_usage"] = {
            "input_tokens": 120,
            "cache_read_input_tokens": 40,
            "reasoning_tokens": 12,
        }
        self.assertEqual(list(self.validator.iter_errors(self.record)), [])
        self.record["tool_call_count"] = None
        self.assertEqual(list(self.validator.iter_errors(self.record)), [])
        self.record["tool_call_count"] = -1
        self.assertTrue(list(self.validator.iter_errors(self.record)))

    def test_measured_cost_requires_currency_and_pricing_snapshot(self) -> None:
        self.record["cost"] = {
            "amount": 0.0,
            "currency": "USD",
            "pricing_reference": "provider-price-sheet-2026-09-28",
            "pricing_snapshot_utc": "2026-09-28T07:00:00Z",
        }
        self.assertEqual(list(self.validator.iter_errors(self.record)), [])
        del self.record["cost"]["pricing_reference"]
        self.assertTrue(list(self.validator.iter_errors(self.record)))
        self.record["cost"]["pricing_reference"] = "provider-price-sheet-2026-09-28"
        self.record["cost"]["pricing_snapshot_utc"] = "not-a-timestamp"
        self.assertTrue(list(self.validator.iter_errors(self.record)))


if __name__ == "__main__":
    unittest.main()
