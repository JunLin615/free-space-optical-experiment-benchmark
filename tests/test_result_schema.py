"""Check the proposed run record contract with representative data."""

from __future__ import annotations

import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator


SCHEMA_PATH = Path(__file__).resolve().parents[1] / "benchmark" / "schema" / "result.schema.json"


class ResultSchemaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        self.validator = Draft202012Validator(self.schema)
        self.record = {
            "result_schema_version": "0.1.0",
            "case_id": "SEED-2.1",
            "benchmark_version": "0.1.0-dev",
            "system": {"name": "Example system", "model_id": "model-x", "model_version": None, "scaffold_id": None},
            "protocol": "closed_book",
            "case_library_access": {"available": False, "snapshot_id": None, "retrieved_document_ids": []},
            "tools_available": [],
            "tools_used": [],
            "tokens": {"input": None, "output": None, "total": None},
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
        self.record["criterion_scores"][0]["score"] = 1.2
        self.assertTrue(list(self.validator.iter_errors(self.record)))


if __name__ == "__main__":
    unittest.main()
