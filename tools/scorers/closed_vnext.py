"""Versioned closed-physics claims for selected deterministic vNext cases.

The numerical checks remain in the pinned numerical scorer. This module only
replaces its open-vocabulary conceptual verdicts with neutral, bounded typed
claims specified by the vNext public answer contracts.
"""

from __future__ import annotations

from typing import Any

from tools.physics_checks import PhysicsCheckError, to_si
from tools.scorers.numerical import evaluate as evaluate_numerical


SUPPORTED_CASES = frozenset({"SEED-3-1", "SEED-3-7", "SEED-5-5"})


def _verdict(check_id: str, status: str, evidence: str, failure_class: str | None = None) -> dict[str, Any]:
    return {
        "criterion_id": check_id,
        "check_id": check_id,
        "status": status,
        "score": 1 if status == "pass" else 0,
        "evidence": evidence,
        "details": {"failure_class": failure_class} if failure_class else {},
    }


def _at(answer: dict[str, Any], *parts: str) -> Any:
    current: Any = answer
    for part in parts:
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def _image_character(answer: dict[str, Any]) -> dict[str, Any]:
    image_type = _at(answer, "answers", "q3", "image_type")
    orientation = _at(answer, "answers", "q3", "orientation")
    if image_type not in ("real", "virtual") or orientation not in ("inverted", "upright"):
        return _verdict("c_image_character", "fail", "Image type and orientation must use the specified neutral enums.", "malformed_claim")
    if image_type == "real" and orientation == "inverted":
        return _verdict("c_image_character", "pass", "The image at 2f is real and inverted.")
    return _verdict("c_image_character", "fail", "The claimed image character contradicts the positive thin-lens conjugate at 2f.", "physics_fail")


def _depth_trend(answer: dict[str, Any]) -> dict[str, Any]:
    trend = _at(answer, "answers", "q3", "depth_of_focus_trend")
    if trend not in ("decreases", "unchanged", "increases"):
        return _verdict("c_depth", "fail", "Depth-of-focus trend must use the specified neutral enum.", "malformed_claim")
    if trend == "decreases":
        return _verdict("c_depth", "pass", "At fixed wavelength, increasing NA narrows diffraction-limited depth of focus.")
    return _verdict("c_depth", "fail", "The claimed depth trend reverses or ignores the fixed-wavelength NA dependence.", "physics_fail")


def _heterodyne_origin(answer: dict[str, Any]) -> dict[str, Any]:
    order_claim = _at(answer, "answers", "q2", "detector_field_response_order")
    source = _at(answer, "answers", "q2", "frequency_component_source")
    try:
        order = to_si(order_claim, "dimensionless")
    except (PhysicsCheckError, TypeError):
        order = None
    if order is None or source not in ("self_term", "interference_cross_term", "optical_carrier"):
        return _verdict("c_q2", "fail", "Response order and component source must use the specified typed fields.", "malformed_claim")
    if order == 2 and source == "interference_cross_term":
        return _verdict("c_q2", "pass", "Second-order intensity detection of the interference cross term yields the difference-frequency photocurrent.")
    return _verdict("c_q2", "fail", "The response order or component source cannot produce the stated heterodyne beat.", "physics_fail")


QUALITATIVE = {
    "SEED-3-1": ("c_image_character", _image_character),
    "SEED-3-7": ("c_depth", _depth_trend),
    "SEED-5-5": ("c_q2", _heterodyne_origin),
}


def evaluate(case: dict[str, Any], answer: dict[str, Any]) -> list[dict[str, Any]]:
    case_id = case.get("case_id")
    if case_id not in SUPPORTED_CASES:
        raise ValueError(f"unsupported vNext closed-physics case: {case_id}")
    if case.get("case_revision") != "0.3.0":
        raise ValueError("vNext closed-physics scorer requires case revision 0.3.0")
    replace_id, check = QUALITATIVE[case_id]
    legacy = evaluate_numerical(case, answer)
    results = [verdict for verdict in legacy if verdict.get("criterion_id") != replace_id]
    results.append(check(answer))
    return results
