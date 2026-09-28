"""Executable mirror-screen geometry criterion for SEED-1-1."""

from __future__ import annotations

import math
from typing import Any

from tools.physics_checks import PhysicsCheckError, to_si


VERSION = "mirror_geometry_v0.1"


def evaluate_quarter(case: dict[str, Any], answer: dict[str, Any]) -> dict[str, Any]:
    criterion = "c_quarter"
    base = {"criterion_id": criterion, "check_id": criterion, "version": VERSION}
    try:
        change = answer["answers"]["q3"]["geometry_change"]
    except (KeyError, TypeError):
        return {**base, "status": "fail", "score": 0, "evidence": "missing geometry change",
                "details": {"failure_class": "missing_claim"}}
    if not isinstance(change, dict):
        return {**base, "status": "fail", "score": 0, "evidence": "geometry change must be typed",
                "details": {"failure_class": "malformed_claim"}}
    try:
        variable = change["variable"]
        held_fixed = change["held_fixed"]
        scale = to_si(change["scale"], "dimensionless")
    except (KeyError, TypeError, PhysicsCheckError) as exc:
        return {**base, "status": "fail", "score": 0, "evidence": str(exc),
                "details": {"failure_class": "malformed_claim"}}
    if not math.isfinite(scale) or scale <= 0:
        return {**base, "status": "fail", "score": 0, "evidence": "scale must be positive",
                "details": {"failure_class": "wrong_value"}}
    if variable == "screen_distance" and held_fixed == "mirror_rotation":
        predicted_ratio = scale
    elif variable == "mirror_rotation" and held_fixed == "screen_distance":
        try:
            angle_given = next(item for item in case["task"]["givens"] if item.get("symbol") == "mirror_rotation")
            angle = to_si(angle_given, "angle")
            predicted_ratio = math.tan(2 * angle * scale) / math.tan(2 * angle)
        except (StopIteration, KeyError, TypeError, ZeroDivisionError, PhysicsCheckError) as exc:
            return {**base, "status": "error", "score": None, "evidence": str(exc),
                    "details": {"failure_class": "invalid_instance"}}
    else:
        return {**base, "status": "fail", "score": 0, "evidence": "unsupported changed/fixed variable pair",
                "details": {"failure_class": "wrong_mechanism"}}
    # Set before candidate testing: 0.005 absolute ratio permits the seed's
    # approximate quarter-angle answer while rejecting material deviations.
    passed = abs(predicted_ratio - 0.25) <= 0.005
    return {**base, "status": "pass" if passed else "fail", "score": 1 if passed else 0,
            "evidence": f"predicted screen-shift ratio {predicted_ratio:.9g} vs 0.25",
            "details": {"predicted_ratio": predicted_ratio, "tolerance": 0.005,
                        **({} if passed else {"failure_class": "wrong_value"})}}
