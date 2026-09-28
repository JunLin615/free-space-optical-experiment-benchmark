"""Validate canonical YAML case records (Python 3.10+, PyYAML, jsonschema).

Usage: python tools/validate_cases.py [file-or-directory ...]
Without arguments, validates all YAML files below benchmark/cases.
This checks authoring consistency, not the physical correctness of a gold oracle.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError

try:
    from tools.physics_checks import (
        REGISTRY as PHYSICS_VALIDATORS,
        PhysicsCheckError,
        check_numeric_claim,
    )
except ModuleNotFoundError:  # direct `python tools/validate_cases.py` invocation
    from physics_checks import REGISTRY as PHYSICS_VALIDATORS, PhysicsCheckError, check_numeric_claim


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "benchmark" / "schema" / "case_v0.1.schema.json"
DEFAULT_CASES = ROOT / "benchmark" / "cases"


class UniqueKeyLoader(yaml.SafeLoader):
    """Safe YAML loader that rejects silently overwritten mapping keys."""


def _construct_mapping(loader: UniqueKeyLoader, node: yaml.MappingNode, deep: bool = False) -> dict:
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        try:
            repeated = key in mapping
        except TypeError as exc:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping", node.start_mark,
                "mapping key must be hashable", key_node.start_mark,
            ) from exc
        if repeated:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping", node.start_mark,
                f"duplicate key {key!r}", key_node.start_mark,
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping
)


def load_case(path: Path) -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8")
    # Aliases can conceal repeated or cyclic structures and are unnecessary in case records.
    if any(isinstance(event, yaml.events.AliasEvent) for event in yaml.parse(raw)):
        raise ValueError("YAML aliases are not allowed")
    data = yaml.load(raw, Loader=UniqueKeyLoader)
    if not isinstance(data, dict):
        raise ValueError("top-level YAML value must be a mapping")
    return data


def _duplicates(values: list[str]) -> set[str]:
    seen: set[str] = set()
    repeated: set[str] = set()
    for value in values:
        if value in seen:
            repeated.add(value)
        seen.add(value)
    return repeated


def semantic_issues(case: dict[str, Any]) -> list[str]:
    """Check cross-field invariants after successful structural validation."""
    issues: list[str] = []
    task = case["task"]
    gold = case["gold"]
    scoring = case["scoring"]
    contract = case["answer_contract"]
    questions = task["questions"]
    question_ids = [q["id"] for q in questions]
    for duplicate in sorted(_duplicates(question_ids)):
        issues.append(f"duplicate task question ID: {duplicate}")

    # Every score check resolves to exactly one oracle item; criterion IDs are also unique.
    check_ids: list[str] = []
    for field in ("numerical_checks", "universal_constraints", "forbidden_claims", "judge_rubrics"):
        check_ids.extend(item["id"] for item in gold.get(field, []))
    for duplicate in sorted(_duplicates(check_ids)):
        issues.append(f"duplicate gold check ID: {duplicate}")
    known_checks = set(check_ids)
    criteria = scoring["criteria"]
    for duplicate in sorted(_duplicates([c["id"] for c in criteria])):
        issues.append(f"duplicate scoring criterion ID: {duplicate}")
    for criterion in criteria:
        if criterion["check"] not in known_checks:
            issues.append(f"criterion {criterion['id']}: unknown check {criterion['check']}")
        if criterion.get("question_id") and criterion["question_id"] not in question_ids:
            issues.append(f"criterion {criterion['id']}: unknown question_id {criterion['question_id']}")

    # A single case score uses one normalized weight vector. Per-question scoring
    # can be added in a future schema version without silently changing this rule.
    total = sum(c["weight"] for c in criteria)
    if not math.isclose(total, 1.0, rel_tol=0, abs_tol=1e-9):
        issues.append(f"scoring criterion weights sum to {total:.12g}, expected 1")

    result_paths = set(contract["required_result_paths"])
    if contract["schema_id"] == "pilot_answer_v0.1":
        for path in result_paths:
            parts = path.split(".")
            if len(parts) < 2 or parts[0] != "answers" or parts[1] not in question_ids:
                issues.append(f"required_result_path {path}: expected answers.<task question ID>[.<field>]")
    given_symbols = [given["symbol"] for given in task.get("givens", []) if "symbol" in given]
    for duplicate in sorted(_duplicates(given_symbols)):
        issues.append(f"duplicate given symbol: {duplicate}")
    for check in gold.get("numerical_checks", []):
        name = check["id"]
        if check["answer_path"] not in result_paths:
            issues.append(f"numerical check {name}: answer_path is absent from required_result_paths")
        reference = check["reference"]
        absolute = check.get("absolute_tolerance")
        relative = check.get("relative_tolerance")
        if absolute and absolute["unit"] != reference["unit"]:
            issues.append(f"numerical check {name}: absolute tolerance unit differs from reference unit")
        if reference["value"] == 0 and absolute is None:
            issues.append(f"numerical check {name}: zero reference needs an absolute tolerance")
        comparator = check["comparator"]
        if comparator == "absolute_inclusive" and absolute is None:
            issues.append(f"numerical check {name}: absolute comparator needs absolute_tolerance")
        if comparator == "relative_inclusive" and relative is None:
            issues.append(f"numerical check {name}: relative comparator needs relative_tolerance")
        if comparator == "custom_validator" and not check.get("validator_id"):
            issues.append(f"numerical check {name}: custom comparator needs validator_id")
        if check.get("validator_id") and check["validator_id"] not in PHYSICS_VALIDATORS:
            issues.append(f"numerical check {name}: unsupported validator_id {check['validator_id']}")
        elif check.get("validator_id"):
            try:
                result = check_numeric_claim(case, check, reference)
                if result["status"] != "pass":
                    issues.append(
                        f"numerical check {name}: authored gold fails independent physics "
                        f"({result['status']}: {result.get('reason', 'claim mismatch')})"
                    )
            except PhysicsCheckError as exc:
                issues.append(f"numerical check {name}: physics validator error: {exc}")
        for symbol in check.get("inputs", []):
            if symbol not in given_symbols:
                issues.append(f"numerical check {name}: input {symbol} is absent from task.givens")

    for field in ("accepted_solution_families", "accepted_correction_families"):
        for duplicate in sorted(_duplicates([f["id"] for f in gold.get(field, [])])):
            issues.append(f"duplicate {field} ID: {duplicate}")
    if gold.get("accepted_solution_families") and not gold.get("other_valid_families_policy"):
        issues.append("accepted_solution_families require an other_valid_families_policy")

    # Public output must never reveal private reference values or grading rules.
    if case["split"] == "hidden_eval" and gold.get("visibility") == "public_dev":
        issues.append("hidden_eval case cannot mark gold as public_dev")
    if case["validation_status"] == "release_verified":
        if not case.get("benchmark_release"):
            issues.append("release_verified case needs benchmark_release")
        if not case["validation"].get("positive_fixtures"):
            issues.append("release_verified case needs positive_fixtures")
        if not case["validation"].get("negative_fixtures"):
            issues.append("release_verified case needs negative_fixtures")
    if case["validation_status"] in ("executable", "challenged", "release_verified"):
        if not case["validation"].get("implemented_checks"):
            issues.append(f"{case['validation_status']} case needs implemented_checks")
    return issues


def find_case_files(paths: list[Path]) -> list[Path]:
    files: set[Path] = set()
    for path in paths:
        if path.is_dir():
            files.update(p.resolve() for pattern in ("*.yaml", "*.yml") for p in path.rglob(pattern))
        elif path.is_file():
            files.add(path.resolve())
        else:
            raise FileNotFoundError(path)
    return sorted(files)


def validate(paths: list[Path], schema_path: Path = SCHEMA_PATH) -> list[str]:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    files = find_case_files(paths)
    if not files:
        return ["no YAML case files found"]
    issues: list[str] = []
    checked_answer_schemas: set[str] = set()
    seen_ids: dict[str, Path] = {}
    seen_legacy_ids: dict[str, Path] = {}
    for path in files:
        try:
            case = load_case(path)
        except (OSError, ValueError, yaml.YAMLError) as exc:
            issues.append(f"{path}: YAML parse error: {exc}")
            continue
        schema_errors = sorted(validator.iter_errors(case), key=lambda e: (list(map(str, e.path)), e.message))
        for error in schema_errors:
            location = ".".join(str(part) for part in error.absolute_path) or "<root>"
            issues.append(f"{path}: {location}: {error.message}")
        if schema_errors:
            continue
        answer_schema_id = case["answer_contract"]["schema_id"]
        if answer_schema_id not in checked_answer_schemas:
            answer_schema_path = schema_path.parent / f"{answer_schema_id}.schema.json"
            if not answer_schema_path.is_file():
                issues.append(f"{path}: unresolved answer_contract.schema_id {answer_schema_id}")
            else:
                try:
                    answer_schema = json.loads(answer_schema_path.read_text(encoding="utf-8"))
                    Draft202012Validator.check_schema(answer_schema)
                except (OSError, json.JSONDecodeError, SchemaError) as exc:
                    issues.append(f"{path}: invalid answer schema {answer_schema_id}: {exc}")
            checked_answer_schemas.add(answer_schema_id)
        case_id = case["case_id"]
        if case_id in seen_ids:
            issues.append(f"{path}: duplicate case_id {case_id} (also {seen_ids[case_id]})")
        else:
            seen_ids[case_id] = path
        if legacy_id := case.get("legacy_id"):
            if legacy_id in seen_legacy_ids:
                issues.append(f"{path}: duplicate legacy_id {legacy_id} (also {seen_legacy_ids[legacy_id]})")
            else:
                seen_legacy_ids[legacy_id] = path
        issues.extend(f"{path}: {issue}" for issue in semantic_issues(case))
    if not issues:
        print(f"Validated {len(files)} case file(s) against schema 0.1.0")
    return issues


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", type=Path, help="YAML files or directories; default: benchmark/cases")
    args = parser.parse_args(argv)
    try:
        issues = validate(args.paths or [DEFAULT_CASES])
    except (OSError, FileNotFoundError, json.JSONDecodeError, yaml.YAMLError) as exc:
        print(f"Validation setup error: {exc}", file=sys.stderr)
        return 2
    for issue in issues:
        print(issue, file=sys.stderr)
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
