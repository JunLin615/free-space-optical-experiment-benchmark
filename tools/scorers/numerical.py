"""Deterministic numerical and bounded closed-physics verdicts.

The authored reference is checked against an independently computed equation
before any candidate is graded. Quantities are converted to SI; the absolute
or relative tolerance is inclusive. The four-ULP boundary allowance only
compensates for binary conversion of an exact tolerance endpoint. Case-specific
magnitude conventions are explicit in the public task and MAGNITUDE_CHECKS;
other numerical claims retain their signed meaning.
"""

from __future__ import annotations

import math
from typing import Any

from tools.physics_checks import PhysicsCheckError, UNITS, check_numeric_claim, to_si


SUPPORTED_CASES = frozenset({"SEED-1-1", "SEED-1-5", "SEED-1-7", "SEED-2-1", "SEED-2-2", "SEED-2-4", "SEED-3-1", "SEED-3-7", "SEED-4-2", "SEED-5-5"})
MAGNITUDE_CHECKS = {"SEED-1-1": {"n_angle", "n_shift"}, "SEED-1-5": {"n_path", "n_delay"},
                    "SEED-4-2": {"n_opd_half", "n_opd_quarter"}}


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

    # The seed omits rotation/stage-motion sense. For changes explicitly
    # requested as magnitudes, opposite signed coordinates are equivalent.
    magnitude_claim = check_id in MAGNITUDE_CHECKS.get(case["case_id"], set())
    if magnitude_claim:
        candidate_si = abs(candidate_si)
        canonical_unit = {"angle": "rad", "length": "m", "time": "s",
                          "dimensionless": "1", "frequency": "Hz"}[dimension]
        candidate = {"value": candidate_si, "unit": canonical_unit}
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
        "magnitude_convention": magnitude_claim,
    }
    if not passed:
        details["failure_class"] = "physics_fail"
    return _verdict(
        criterion_id, check_id, "pass" if passed else "fail",
        f"Absolute SI error {difference:.12g} {'<=' if passed else '>'} inclusive tolerance {tolerance:.12g}.",
        details,
    )


def _closed_verdict(criterion: str, status: str, evidence: str, failure_class: str | None = None) -> dict[str, Any]:
    details = {"failure_class": failure_class} if failure_class else {}
    return _verdict(criterion, criterion, status, evidence, details)


def _field(answer: dict[str, Any], path: str) -> Any:
    present, value = _at_path(answer, path)
    return value if present else None


def _word(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    return "_".join(value.strip().lower().replace("-", " ").split())


def _typed_choice(criterion: str, value: Any, valid: set[str], invalid: set[str], label: str) -> dict[str, Any]:
    word = _word(value)
    if word is None:
        return _closed_verdict(criterion, "fail", f"Missing typed {label} claim.", "missing_claim")
    if word in valid:
        return _closed_verdict(criterion, "pass", f"Typed {label} has the expected physical direction.")
    if word in invalid:
        return _closed_verdict(criterion, "fail", f"Typed {label} contradicts the physical model.", "physics_fail")
    return _closed_verdict(criterion, "unresolved", f"Unrecognized {label} phrasing; possible alternative requires review.", "unsupported_alternative")


def _focal_pair(value: Any, expected_ratio: float, galilean: bool) -> tuple[str, str]:
    if not isinstance(value, dict):
        return "fail", "Missing typed focal-length pair."
    try:
        first = to_si(value["input_focal_length"], "length")
        second = to_si(value["output_focal_length"], "length")
    except (KeyError, TypeError, PhysicsCheckError) as exc:
        return "fail", f"Invalid focal-length quantity: {exc}"
    if first == 0 or second == 0:
        return "fail", "A focal length cannot be zero."
    if (first < 0 if galilean else first > 0) and second > 0 and abs(abs(second / first) - expected_ratio) <= 0.1:
        return "pass", "Lens signs, order, and focal-length magnitude ratio yield the requested afocal expansion."
    return "fail", "Lens signs, order, or focal-length magnitude ratio are inconsistent with the requested expander."


def _closed_physics(case: dict[str, Any], answer: dict[str, Any]) -> list[dict[str, Any]]:
    case_id = case["case_id"]
    if case_id == "SEED-1-7":
        applies = _field(answer, "answers.q3.linear_rotation_rule_applies")
        if not isinstance(applies, bool):
            return [_closed_verdict("c_circular", "fail", "Missing typed applicability boolean.", "missing_claim")]
        correct = applies is False
        return [_closed_verdict("c_circular", "pass" if correct else "fail",
                                "The linear-axis rotation rule does not apply directly to circular input.",
                                None if correct else "physics_fail")]

    if case_id == "SEED-2-1":
        try:
            from tools.physics_checks import expected_si
            waist, _ = expected_si(case, "gaussian_focus_radius")
            options = (1e-6, 10e-6, 1e-3)
            nearest = min(options, key=lambda x: abs(x - waist))
        except (KeyError, TypeError, ValueError, PhysicsCheckError) as exc:
            return [_closed_verdict(c, "error", f"Invalid case givens: {exc}", "invalid_instance")
                    for c in ("c_scale", "c_double")]
        try:
            selected = to_si(_field(answer, "answers.q2.closest_scale"), "length")
        except (TypeError, PhysicsCheckError) as exc:
            scale = _closed_verdict("c_scale", "fail", f"Invalid scale-choice quantity: {exc}", "malformed_claim")
        else:
            matches = abs(selected - nearest) <= 1e-12
            scale = _closed_verdict("c_scale", "pass" if matches else "fail",
                                    "The selected scale must be the nearest of the three offered choices.",
                                    None if matches else "physics_fail")
        try:
            ratio = to_si(_field(answer, "answers.q3.waist_radius_factor"), "dimensionless")
        except (TypeError, PhysicsCheckError) as exc:
            doubled = _closed_verdict("c_double", "fail", f"Invalid ideal waist-radius factor: {exc}", "malformed_claim")
        else:
            correct = _boundary_inclusive(abs(ratio - 0.5), 0.01, ratio, 0.5)
            doubled = _closed_verdict("c_double", "pass" if correct else "fail",
                                      "At fixed wavelength and focal length, doubled incident radius halves ideal waist.",
                                      None if correct else "physics_fail")
        return [scale, doubled]

    if case_id == "SEED-2-2":
        try:
            givens = {g["symbol"]: g for g in case["task"]["givens"]}
            ratio = to_si(givens["output_diameter"], "length") / to_si(givens["input_diameter"], "length")
            if not math.isfinite(ratio) or ratio <= 1:
                raise ValueError("invalid expansion ratio")
        except (KeyError, TypeError, ValueError, ZeroDivisionError, PhysicsCheckError) as exc:
            return [_closed_verdict(c, "error", f"Invalid case givens: {exc}", "invalid_instance") for c in ("c_examples", "c_focus")]
        pairs = _field(answer, "answers.q2")
        keplerian = pairs.get("keplerian") if isinstance(pairs, dict) else None
        galilean = pairs.get("galilean") if isinstance(pairs, dict) else None
        k_status, k_reason = _focal_pair(keplerian, ratio, False)
        g_status, g_reason = _focal_pair(galilean, ratio, True)
        examples_pass = k_status == g_status == "pass"
        examples = _closed_verdict("c_examples", "pass" if examples_pass else "fail", f"Keplerian: {k_reason} Galilean: {g_reason}", None if examples_pass else "physics_fail")
        focus = _field(answer, "answers.q3")
        if not isinstance(focus, dict) or not all(isinstance(focus.get(k), bool) for k in ("keplerian_real_internal_focus", "galilean_real_internal_focus")):
            focus_result = _closed_verdict("c_focus", "fail", "Missing typed internal-focus booleans.", "missing_claim")
        else:
            correct = focus["keplerian_real_internal_focus"] is True and focus["galilean_real_internal_focus"] is False
            focus_result = _closed_verdict("c_focus", "pass" if correct else "fail", "Internal real-focus distinction for the stated lens order.", None if correct else "physics_fail")
        return [examples, focus_result]

    if case_id == "SEED-2-4":
        tradeoff = _field(answer, "answers.q3")
        benefit = _word(tradeoff.get("benefit")) if isinstance(tradeoff, dict) else None
        cost = _word(tradeoff.get("cost")) if isinstance(tradeoff, dict) else None
        benefits = {"longer_rayleigh_range", "greater_depth_of_focus", "lower_peak_intensity", "lower_divergence"}
        costs = {"worse_spatial_resolution", "lower_local_resolution", "larger_clear_aperture", "greater_aperture_demand", "lower_peak_intensity_for_nonlinear_process"}
        false_benefits = {"shorter_rayleigh_range", "higher_divergence", "higher_peak_intensity"}
        false_costs = {"better_spatial_resolution", "smaller_clear_aperture", "less_aperture_demand"}
        if cost is None:
            return [_closed_verdict("c_tradeoff", "fail", "Missing typed application cost.", "missing_claim")]
        if benefit in false_benefits or cost in false_costs:
            return [_closed_verdict("c_tradeoff", "fail", "Tradeoff direction contradicts Gaussian-beam scaling.", "physics_fail")]
        if cost in costs and (benefit is None or benefit in benefits):
            return [_closed_verdict("c_tradeoff", "pass", "A valid application cost is identified; an optional stated benefit is physically consistent.")]
        return [_closed_verdict("c_tradeoff", "unresolved", "Unrecognized but potentially valid application tradeoff.", "unsupported_alternative")]

    if case_id == "SEED-3-1":
        character = _field(answer, "answers.q3")
        if not isinstance(character, dict):
            return [_closed_verdict("c_image_character", "fail", "Missing typed image character.", "missing_claim")]
        image_type = _word(character.get("image_type"))
        orientation = _word(character.get("orientation"))
        if image_type is None or orientation is None:
            return [_closed_verdict("c_image_character", "fail", "Image type and orientation must be supplied.", "missing_claim")]
        if image_type in {"virtual"} or orientation in {"upright", "erect"}:
            return [_closed_verdict("c_image_character", "fail", "A positive lens with object at 2f forms a real inverted image.", "physics_fail")]
        if image_type in {"real", "real_image"} and orientation in {"inverted", "upside_down"}:
            return [_closed_verdict("c_image_character", "pass", "Real image and inverted orientation agree with thin-lens conjugates.")]
        return [_closed_verdict("c_image_character", "unresolved", "Unrecognized image-character terminology.", "unsupported_alternative")]

    if case_id == "SEED-3-7":
        try:
            from tools.physics_checks import expected_si
            reference, _ = expected_si(case, "rayleigh_lateral_resolution")
            choices = [0.1e-6, 1e-6, 10e-6]
            closest = min(choices, key=lambda x: abs(x - reference))
            scale = to_si(_field(answer, "answers.q2.closest_scale"), "length")
            scale_pass = abs(scale - closest) <= 0.02 * closest
            scale_result = _closed_verdict("c_scale", "pass" if scale_pass else "fail", f"Closest stated scale is {closest:.9g} m.", None if scale_pass else "physics_fail")
        except (TypeError, PhysicsCheckError) as exc:
            scale_result = _closed_verdict("c_scale", "fail", f"Missing or invalid scale quantity: {exc}", "malformed_claim")
        depth = _field(answer, "answers.q3.depth_of_focus_change")
        depth_result = _typed_choice("c_depth", depth, {"decreases", "narrows", "shortens", "smaller"}, {"increases", "widens", "lengthens", "unchanged"}, "depth-of-focus trend")
        return [scale_result, depth_result]

    if case_id == "SEED-5-5":
        origin = _field(answer, "answers.q2")
        if not isinstance(origin, dict):
            origin_result = _closed_verdict("c_q2", "fail", "Missing typed detection mechanism.", "missing_claim")
        else:
            law = _word(origin.get("detection_law"))
            term = _word(origin.get("field_cross_term"))
            if law is None or term is None:
                origin_result = _closed_verdict("c_q2", "fail", "Detection law and field cross term are required.", "missing_claim")
            elif law in {"linear_field", "frequency_sum_only"} or term in {"no_cross_term", "optical_carrier"}:
                origin_result = _closed_verdict("c_q2", "fail", "Photocurrent origin contradicts square-law interference.", "physics_fail")
            elif law in {"square_law", "intensity_detection", "quadratic_field"} and term in {"difference_frequency", "heterodyne_cross_term", "field_interference"}:
                origin_result = _closed_verdict("c_q2", "pass", "Square-law field cross term produces the difference-frequency photocurrent.")
            else:
                origin_result = _closed_verdict("c_q2", "unresolved", "Unrecognized detection-mechanism phrasing.", "unsupported_alternative")
        orthogonal = _field(answer, "answers.q3")
        if not isinstance(orthogonal, dict) or not isinstance(orthogonal.get("ideal_cross_term"), bool):
            orthogonal_result = _closed_verdict("c_q3", "fail", "Missing typed no-projector orthogonal-polarization result.", "missing_claim")
        else:
            correct = orthogonal["ideal_cross_term"] is False
            orthogonal_result = _closed_verdict("c_q3", "pass" if correct else "fail", "Ideal orthogonality removes the beat in the stated no-projector condition.", None if correct else "physics_fail")
        return [origin_result, orthogonal_result]
    return []


def evaluate(case: dict[str, Any], answer: dict[str, Any]) -> list[dict[str, Any]]:
    """Return one verdict per numerical scoring criterion, in criterion order.

    Case-specific closed-physics checks cover the remaining typed criteria.
    An invalid case produces an error, never a zero.
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
    if case["case_id"] not in {"SEED-1-1", "SEED-1-5"}:
        verdicts.extend(_closed_physics(case, answer))
    return verdicts
