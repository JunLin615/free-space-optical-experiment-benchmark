"""Fixture-kind invariants independent of fixture-authored expected verdicts."""

from __future__ import annotations

from typing import Any


BOUNDARY_TYPES = {
    "inclusive_tolerance": "pass",
    "equal_resolution_limit": "fail",
    "missing_claim": "fail",
    "novel_alternative": "unresolved",
}
KINDS = {"positive", "alternative_valid", "negative", "adversarial", "boundary"}
EVALUATOR_FAILURES = {"validator_error", "invalid_instance"}


def fixture_kind_issues(fixture: dict[str, Any], result: dict[str, Any], *, release_verified: bool = False) -> list[str]:
    """Check scientific role of a fixture without consulting ``expected``."""
    kind = fixture.get("kind")
    if kind not in KINDS:
        return [f"unknown fixture kind {kind!r}"]
    criteria = result["criterion_scores"]
    capped = result["scores"]["capped_total"]
    failure_mode = result["failure_mode"]
    issues: list[str] = []
    if failure_mode in EVALUATOR_FAILURES:
        issues.append(f"evaluator failure {failure_mode} cannot validate a {kind} fixture")
        return issues

    scored_failure = any(item["status"] == "scored" and item["score"] == 0 for item in criteria)
    check_failure = any(item["status"] == "fail" for item in result["validator_results"] + result["judge_results"])
    if kind in {"positive", "alternative_valid"}:
        if capped != 1 or not criteria or any(item["status"] != "scored" or item["score"] != 1 for item in criteria):
            issues.append(f"{kind} fixture must resolve every criterion and score 1")
        if failure_mode != "none":
            issues.append(f"{kind} fixture has failure mode {failure_mode}")
    elif kind == "negative":
        if not scored_failure:
            issues.append("negative fixture needs at least one scored criterion failure")
        if capped == 1:
            issues.append("negative fixture achieved full success")
    elif kind == "adversarial":
        if capped == 1:
            issues.append("adversarial fixture achieved full success")
        if release_verified and (capped is None or not (scored_failure or check_failure)):
            issues.append("release adversarial fixture must resolve to an actual failure")
    else:
        boundary = fixture.get("boundary")
        if not isinstance(boundary, dict) or set(boundary) != {"type", "criterion_id"}:
            return ["boundary fixture needs {type, criterion_id} metadata"]
        boundary_type = boundary["type"]
        criterion_id = boundary["criterion_id"]
        wanted = BOUNDARY_TYPES.get(boundary_type)
        if wanted is None:
            return [f"unknown boundary type {boundary_type!r}"]
        verdicts = [item for item in result["validator_results"] if item["check_id"] == criterion_id]
        if len(verdicts) != 1:
            issues.append(f"boundary criterion {criterion_id!r} must have exactly one validator verdict")
        elif verdicts[0]["status"] != wanted:
            issues.append(f"boundary {boundary_type} requires {criterion_id}={wanted}, got {verdicts[0]['status']}")
        if release_verified and (capped is None or wanted == "unresolved"):
            issues.append("release boundary fixture must resolve")
    return issues
