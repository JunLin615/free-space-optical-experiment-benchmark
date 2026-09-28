"""Deterministic numerical verdicts for the mirror and delay-line pilot cases.

The authored reference is checked against an independently computed equation
before any candidate is graded. Quantities are converted to SI; the absolute
or relative tolerance is inclusive. The four-ULP boundary allowance only
compensates for binary conversion of an exact tolerance endpoint. These two
cases use signed beam rotation/displacement and positive path/time/travel,
without angular wrapping or an implicit absolute-value convention.
"""

from __future__ import annotations

import math
from typing import Any

from tools.physics_checks import PhysicsCheckError, UNITS, check_numeric_claim, to_si


SUPPORTED_CASES = frozenset({"SEED-1-1", "SEED-1-5"})


def _verdict(
    criterion_id: str, check_id: str, status: str, evidence: str,
    details: dict[str, Any],
) -> dict[str, Any]:
    return {
        "criterion_id": criterion_id,
        "check_id": check_id,
        "status": status,
        "score": 1 if status == "pass" else 0 if status == "fail" else None,
        "evidence": evidence,
        "details": details,
    }


def _at_path(answer: Any, path: str) -> tuple[bool, Any]:
    current = answer
    for part in path.split("."):
        if not isinstance(current, dict):
            return False, None
        if part not in current:
            return False, None
        current = current[part]
    return True, current


def _candidate_failure(candidate: Any, dimension: str) -> str:
    if isinstance(candidate, dict) and "unit" in candidate:
        unit = candidate["unit"]
        if isinstance(unit, str) and (unit not in UNITS or UNITS[unit][0] != dimension):
            return "wrong_unit"
    return "malformed_claim"


def _boundary_inclusive(difference: float, tolerance: float, candidate: float, expected: float) -> bool:
    """Include exact decimal endpoints after SI multiplication/rounding."""
    magnitude = max(abs(candidate), abs(expected), tolerance)
    return difference <= tolerance or difference - tolerance <= 4 * math.ulp(magnitude)


def _evaluate_check(
    case: dict[str, Any], answer: Any, criterion_id: str, check: dict[str, Any]
) -> dict[str, Any]:
    check_id = check["id"]
    try:
        # Gold validation precedes answer extraction, even for missing claims.
        gold_verdict = check_numeric_claim(case, check, check["reference"])
    except (PhysicsCheckError, KeyError, TypeError, ValueError) as exc:
        return _verdict(criterion_id, check_id, "error", str(exc),
                        {"failure_class": "invalid_instance"})
    except Exception as exc:  # a scorer defect must never become candidate failure
        return _verdict(criterion_id, check_id, "error", f"numerical validator failed: {exc}",
                        {"failure_class": "validator_error"})
    if gold_verdict["status"] != "pass":
        return _verdict(
            criterion_id, check_id, "error",
            gold_verdict.get("reason", "authored gold did not pass the independent equation"),
            {"failure_class": "validator_error", "validator_id": check.get("validator_id")},
        )

    if not isinstance(answer, dict):
        return _verdict(criterion_id, check_id, "fail", "Answer is not a JSON object.",
                        {"failure_class": "malformed_claim", "answer_path": check["answer_path"]})
    present, candidate = _at_path(answer, check["answer_path"])
    if not present:
        return _verdict(criterion_id, check_id, "fail",
                        f"Required quantity is missing at {check['answer_path']}.",
                        {"failure_class": "missing_claim", "answer_path": check["answer_path"]})

    try:
        dimension = UNITS[check["reference"]["unit"]][0]
    except (KeyError, TypeError) as exc:
        return _verdict(criterion_id, check_id, "error", str(exc),
                        {"failure_class": "invalid_instance"})
    try:
        candidate_si = to_si(candidate, dimension)
    except (PhysicsCheckError, TypeError) as exc:
        return _verdict(criterion_id, check_id, "fail", str(exc),
                        {"failure_class": _candidate_failure(candidate, dimension),
                         "answer_path": check["answer_path"]})

    try:
        raw = check_numeric_claim(case, check, candidate)
    except (PhysicsCheckError, KeyError, TypeError, ValueError) as exc:
        return _verdict(criterion_id, check_id, "error", str(exc),
                        {"failure_class": "invalid_instance"})
    except Exception as exc:
        return _verdict(criterion_id, check_id, "error", f"numerical validator failed: {exc}",
                        {"failure_class": "validator_error"})
    if raw["status"] not in ("pass", "fail"):
        return _verdict(criterion_id, check_id, "error",
                        raw.get("reason", "unexpected validator result"),
                        {"failure_class": "validator_error"})
    difference = abs(raw["difference_si"])
    tolerance = raw["tolerance_si"]
    passed = _boundary_inclusive(difference, tolerance, candidate_si,
                                 candidate_si - raw["difference_si"])
    details = {
        "answer_path": check["answer_path"],
        "validator_id": check["validator_id"],
        "dimension": dimension,
        "candidate_si": candidate_si,
        "difference_si": raw["difference_si"],
        "tolerance_si": tolerance,
        "comparator": check["comparator"],
    }
    if not passed:
        details["failure_class"] = "physics_fail"
    return _verdict(
        criterion_id, check_id, "pass" if passed else "fail",
        f"Absolute SI error {difference:.12g} {'<=' if passed else '>'} inclusive tolerance {tolerance:.12g}.",
        details,
    )


def evaluate(case: dict[str, Any], answer: dict[str, Any]) -> list[dict[str, Any]]:
    """Return one verdict per numerical scoring criterion, in criterion order.

    This module intentionally supports only SEED-1-1 and SEED-1-5. Other
    criteria, such as the mirror case's qualitative geometry change, belong
    to their own scorers. An invalid case produces an error, never a zero.
    """
    if not isinstance(case, dict) or case.get("case_id") not in SUPPORTED_CASES:
        return [_verdict("<case>", "<case>", "error", "Unsupported or missing numerical case ID.",
                         {"failure_class": "invalid_instance"})]
    try:
        checks = case["gold"]["numerical_checks"]
        criteria = case["scoring"]["criteria"]
        if not isinstance(checks, list) or not isinstance(criteria, list):
            raise TypeError("numerical checks and criteria must be lists")
        check_ids = [check["id"] for check in checks]
        if len(check_ids) != len(set(check_ids)):
            raise ValueError("duplicate numerical check ID")
        by_id = {check["id"]: check for check in checks}
    except (KeyError, TypeError, ValueError) as exc:
        return [_verdict("<case>", "<case>", "error", str(exc),
                         {"failure_class": "invalid_instance"})]
    verdicts = []
    for criterion in criteria:
        try:
            criterion_id = criterion["id"]
            check_id = criterion["check"]
        except (KeyError, TypeError) as exc:
            verdicts.append(_verdict("<criterion>", "<check>", "error", str(exc),
                                     {"failure_class": "invalid_instance"}))
            continue
        if check_id in by_id:
            verdicts.append(_evaluate_check(case, answer, criterion_id, by_id[check_id]))
    return verdicts
