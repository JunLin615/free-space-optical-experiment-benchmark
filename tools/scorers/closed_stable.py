"""Stable SEED-3-1 scorer for the two equivalent focal-length representations.

The public question asks for image distance in units of f. Only its q1 quantity
may therefore use the symbol ``f`` as a *unit of one focal length*. A quantity
``{value: x, unit: f}`` denotes the same dimensionless ratio x as
``{value: x, unit: 1}``. We canonicalize that one field before the independent
thin-lens numerical oracle; no other field or physical dimension is widened.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from tools.scorers.numerical import evaluate as evaluate_numerical


SUPPORTED_CASES = frozenset({"SEED-3-1"})


def _image_character(answer: dict[str, Any]) -> dict[str, Any]:
    character = answer.get("answers", {}).get("q3") if isinstance(answer.get("answers"), dict) else None
    image_type = character.get("image_type") if isinstance(character, dict) else None
    orientation = character.get("orientation") if isinstance(character, dict) else None
    if image_type not in ("real", "virtual") or orientation not in ("inverted", "upright"):
        status, evidence, failure = "fail", "Image type and orientation must use the specified neutral enums.", "malformed_claim"
    elif image_type == "real" and orientation == "inverted":
        status, evidence, failure = "pass", "The image at 2f is real and inverted.", None
    else:
        status, evidence, failure = "fail", "The image character contradicts the positive thin-lens conjugate at 2f.", "physics_fail"
    return {
        "criterion_id": "c_image_character", "check_id": "c_image_character", "status": status,
        "score": 1 if status == "pass" else 0, "evidence": evidence,
        "details": {"failure_class": failure} if failure else {},
    }


def evaluate(case: dict[str, Any], answer: dict[str, Any]) -> list[dict[str, Any]]:
    if case.get("case_id") != "SEED-3-1" or case.get("case_revision") != "0.4.0":
        raise ValueError("stable SEED-3-1 scorer requires case revision 0.4.0")
    numerical_answer = deepcopy(answer)
    answers = numerical_answer.get("answers") if isinstance(numerical_answer, dict) else None
    q1 = answers.get("q1") if isinstance(answers, dict) else None
    quantity = q1.get("image_distance_in_focal_lengths") if isinstance(q1, dict) else None
    if isinstance(quantity, dict) and quantity.get("unit") == "f":
        quantity["unit"] = "1"
    verdicts = evaluate_numerical(case, numerical_answer)
    return [v for v in verdicts if v.get("criterion_id") != "c_image_character"] + [_image_character(answer)]
