"""Static contract tests for the canonical case authoring format."""

from __future__ import annotations

import tempfile
import unittest
import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from tools.validate_cases import SCHEMA_PATH, load_case, validate


def case_record(case_id: str = "TEST-1") -> dict:
    return {
        "schema_version": "0.1.0",
        "case_id": case_id,
        "case_revision": "0.1.0",
        "validation_status": "specified",
        "split": "unassigned",
        "title": "Test beam position",
        "language": "en",
        "taxonomy": {
            "optical_domain": "free_space_beam_geometry",
            "task_types": ["quantitative_inference"],
            "difficulty_hypothesis": "introductory",
            "modality": "text",
        },
        "provenance": {
            "origin": "test_fixture",
            "created_utc": "2026-09-28",
            "source_references": [],
            "license_status": "test_only",
        },
        "task": {
            "statement": "Report the signed position.",
            "questions": [{"id": "q1", "request": "Report x."}],
        },
        "answer_contract": {
            "format": "json_object",
            "schema_id": "pilot_answer_v0.1",
            "required_result_paths": ["answers.q1.x"],
        },
        "gold": {
            "visibility": "private",
            "numerical_checks": [{
                "id": "n_x",
                "answer_path": "answers.q1.x",
                "reference": {"value": 1.0, "unit": "mm"},
                "absolute_tolerance": {"value": 0.01, "unit": "mm"},
                "comparator": "max_abs_or_relative_inclusive",
            }],
        },
        "scoring": {
            "criteria": [{"id": "x", "weight": 1.0, "check": "n_x"}],
            "aggregation": "weighted_sum",
        },
        "validation": {"planned_checks": [], "implemented_checks": []},
    }


class CaseSchemaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)

    def write(self, name: str, record: dict) -> Path:
        path = self.directory / name
        path.write_text(yaml.safe_dump(record, sort_keys=False), encoding="utf-8")
        return path

    def test_valid_case(self) -> None:
        self.assertEqual(validate([self.write("valid.yaml", case_record())]), [])

    def test_duplicate_case_id(self) -> None:
        self.write("a.yaml", case_record())
        self.write("b.yaml", case_record())
        self.assertTrue(any("duplicate case_id" in issue for issue in validate([self.directory])))

    def test_unresolved_score_reference_and_weights(self) -> None:
        record = case_record()
        record["scoring"]["criteria"][0].update(check="missing", weight=0.8)
        issues = validate([self.write("bad.yaml", record)])
        self.assertTrue(any("unknown check" in issue for issue in issues))
        self.assertTrue(any("weights sum" in issue for issue in issues))

    def test_invalid_tolerance(self) -> None:
        record = case_record()
        check = record["gold"]["numerical_checks"][0]
        check["reference"]["value"] = 0
        del check["absolute_tolerance"]
        check["relative_tolerance"] = 0.1
        self.assertTrue(any("zero reference" in issue for issue in validate([self.write("zero.yaml", record)])))
        check["relative_tolerance"] = -0.1
        self.assertTrue(any("minimum" in issue for issue in validate([self.write("negative.yaml", record)])))

    def test_enum_and_unknown_field(self) -> None:
        record = case_record()
        record["validation_status"] = "certified"
        record["typo_gold"] = "bad"
        issues = validate([self.write("bad.yaml", record)])
        self.assertTrue(any("certified" in issue for issue in issues))
        self.assertTrue(any("typo_gold" in issue for issue in issues))

    def test_tool_access_is_not_a_scientific_case_field(self) -> None:
        record = case_record()
        record["task"]["allowed_resources"] = "Any scientific tool"
        self.assertTrue(any("allowed_resources" in issue for issue in validate([self.write("tool_access.yaml", record)])))
        del record["task"]["allowed_resources"]
        record["task"]["apparatus_constraints"] = ["Only two steering mirrors are available."]
        self.assertEqual(validate([self.write("apparatus.yaml", record)]), [])

    def test_references_and_release_metadata(self) -> None:
        record = case_record()
        record["gold"]["numerical_checks"][0]["answer_path"] = "results.missing"
        record["gold"]["numerical_checks"][0]["inputs"] = ["missing_given"]
        record["validation_status"] = "release_verified"
        record["split"] = "hidden_eval"
        record["gold"]["visibility"] = "public_dev"
        issues = validate([self.write("bad.yaml", record)])
        for expected in (
            "absent from required_result_paths", "absent from task.givens",
            "hidden_eval", "benchmark_release", "positive_fixtures",
            "negative_fixtures", "implemented_checks",
        ):
            self.assertTrue(any(expected in issue for issue in issues), expected)

    def test_validator_registry_and_independent_gold(self) -> None:
        record = case_record()
        check = record["gold"]["numerical_checks"][0]
        check["validator_id"] = "no_such_optics_check"
        self.assertTrue(any("unsupported validator_id" in issue for issue in validate([self.write("unknown.yaml", record)])))
        check["validator_id"] = "mirror_angle"
        check["reference"] = {"value": 2.0, "unit": "deg"}
        check["absolute_tolerance"] = {"value": 0.01, "unit": "deg"}
        record["task"]["givens"] = [{"symbol": "mirror_rotation", "value": 0.5, "unit": "deg"}]
        self.assertTrue(any("authored gold fails independent physics" in issue for issue in validate([self.write("wrong.yaml", record)])))

    def test_answer_schema_id_must_resolve(self) -> None:
        record = case_record()
        record["answer_contract"]["schema_id"] = "missing_answer_v0.1"
        self.assertTrue(any("unresolved answer_contract.schema_id" in issue for issue in validate([self.write("missing.yaml", record)])))

    def test_pilot_answer_schema_requires_typed_quantity(self) -> None:
        path = SCHEMA_PATH.parent / "pilot_answer_v0.1.schema.json"
        schema = json.loads(path.read_text(encoding="utf-8"))
        validator = Draft202012Validator(schema)
        good = {"answers": {"q1": {"angle": {"value": 1.0, "unit": "deg"}, "method": "two planes"}}}
        self.assertTrue(validator.is_valid(good))
        self.assertFalse(validator.is_valid({"answers": {"q1": {"angle": 1.0}}}))
        self.assertFalse(validator.is_valid({"answers": {"q1": {"angle": {"value": 1.0}}}}))

    def test_yaml_alias_and_duplicate_key_rejected(self) -> None:
        alias = self.directory / "alias.yaml"
        alias.write_text("a: &a [1]\nb: *a\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "aliases"):
            load_case(alias)
        duplicate = self.directory / "duplicate.yaml"
        duplicate.write_text("a: 1\na: 2\n", encoding="utf-8")
        with self.assertRaises(yaml.YAMLError):
            load_case(duplicate)


if __name__ == "__main__":
    unittest.main()
