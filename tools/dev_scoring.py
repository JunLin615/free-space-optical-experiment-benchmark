"""Development-only route for open reasoning challenges.

The frozen 0.2.0-rc1 runtime and its fingerprinted dispatch stay untouched.
This registry intentionally has no release-verified status or aggregate score.
"""

from __future__ import annotations

from typing import Any

from tools.validate_cases import ROOT, load_case, semantic_issues
from tools.scorers.open_reasoning_wave import evaluate


REGISTERED_CASES = frozenset({"SEED-2-8", "SEED-5-7", "SEED-8-1"})


def score(case_id: str, answer: dict[str, Any]) -> list[dict[str, Any]]:
    if case_id not in REGISTERED_CASES:
        raise ValueError(f"no development scorer registered for {case_id}")
    case = load_case(ROOT / "benchmark" / "cases_vnext" / f"{case_id}.yaml")
    issues = semantic_issues(case)
    if issues:
        raise ValueError(f"invalid development case {case_id}: {issues}")
    results = evaluate(case, answer)
    expected = {criterion["id"] for criterion in case["scoring"]["criteria"]}
    observed = {item["criterion_id"] for item in results}
    if observed != expected or len(results) != len(expected):
        raise RuntimeError(f"scorer coverage mismatch for {case_id}")
    return results
