"""Challenge the autonomous scorer with machine-readable case fixtures."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.scoring_runtime import ROOT, evaluate_case, load_scored_case


DEFAULT_FIXTURES = ROOT / "benchmark" / "fixtures"
KINDS = {"positive", "boundary", "alternative_valid", "negative", "adversarial"}


def run(path: Path = DEFAULT_FIXTURES) -> tuple[dict[str, int], list[str]]:
    paths = sorted(path.rglob("*.json"))
    counts: Counter[str] = Counter()
    errors: list[str] = []
    cases: set[str] = set()
    if not paths:
        return {}, [f"no fixture JSON files found in {path}"]
    for file in paths:
        try:
            fixture = json.loads(file.read_text(encoding="utf-8"))
            case_id = fixture["case_id"]
            kind = fixture["kind"]
            if kind not in KINDS:
                raise ValueError(f"unknown fixture kind {kind!r}")
            cases.add(case_id)
            counts[kind] += 1
            result = evaluate_case(load_scored_case(case_id), fixture["answer"])
            expected = fixture["expected"]
            actual = {v["criterion_id"]: v for v in result["criterion_scores"]}
            checks = {v["check_id"]: v for v in result["validator_results"]}
            if set(expected) != set(actual):
                errors.append(f"{file}: expected criterion IDs {sorted(expected)} != actual {sorted(actual)}")
            for criterion_id, wanted in expected.items():
                if criterion_id not in actual:
                    continue
                scored = actual[criterion_id]
                check = checks.get(criterion_id)
                status = check["status"] if check else scored["status"]
                if status != wanted["status"]:
                    errors.append(f"{file}: {criterion_id} status {status} != {wanted['status']}")
                if "score" in wanted and scored["score"] != wanted["score"]:
                    errors.append(f"{file}: {criterion_id} score {scored['score']} != {wanted['score']}")
                if "failure_class" in wanted:
                    found = (check or {}).get("details", {}).get("failure_class")
                    if found != wanted["failure_class"]:
                        errors.append(f"{file}: {criterion_id} failure class {found!r} != {wanted['failure_class']!r}")
            if "failure_mode" in fixture and result["failure_mode"] != fixture["failure_mode"]:
                errors.append(f"{file}: failure mode {result['failure_mode']} != {fixture['failure_mode']}")
            if "capped_total" in fixture and result["scores"]["capped_total"] != fixture["capped_total"]:
                errors.append(f"{file}: capped score {result['scores']['capped_total']} != {fixture['capped_total']}")
            counts["unresolved_criteria"] += sum(v["status"] == "unresolved" for v in scored_values(result))
        except (OSError, ValueError, KeyError, TypeError, RuntimeError) as exc:
            errors.append(f"{file}: {type(exc).__name__}: {exc}")
    counts["cases"] = len(cases)
    counts["fixtures"] = len(paths)
    counts["unexpected"] = len(errors)
    return dict(counts), errors


def scored_values(result: dict) -> list[dict]:
    return result["criterion_scores"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", type=Path, default=DEFAULT_FIXTURES)
    args = parser.parse_args(argv)
    counts, errors = run(args.path)
    for key in ("cases", "fixtures", "positive", "boundary", "alternative_valid", "negative", "adversarial", "unresolved_criteria", "unexpected"):
        print(f"{key}: {counts.get(key, 0)}")
    for error in errors:
        print(error, file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
