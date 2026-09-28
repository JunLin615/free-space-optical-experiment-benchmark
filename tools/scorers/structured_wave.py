"""Bounded typed oracles for four translated conceptual seed cases.

Only explicit, recognized claims are graded. A novel representation is unresolved;
missing fields and known physical contradictions receive criterion-local failures.
The scorer does not infer physics from free-form explanation text.
"""

from __future__ import annotations

import math
from typing import Any


MISSING = object()
SCORES = {"pass": 1, "fail": 0, "unresolved": None, "error": None}


def _verdict(criterion: str, status: str, evidence: str, failure_class: str | None = None) -> dict[str, Any]:
    details = {"failure_class": failure_class} if failure_class else {}
    return {"criterion_id": criterion, "check_id": criterion, "status": status,
            "score": SCORES[status], "evidence": evidence, "details": details}


def _missing(criterion: str, path: str) -> dict[str, Any]:
    return _verdict(criterion, "fail", f"Missing structured claim at {path}.", "missing_claim")


def _unknown(criterion: str, path: str) -> dict[str, Any]:
    return _verdict(criterion, "unresolved", f"Unrecognized answer form at {path}; no physical verdict inferred.", "unsupported_alternative")


def _field(value: Any, key: str) -> Any:
    return value.get(key, MISSING) if isinstance(value, dict) else MISSING


def _q(answer: Any, qid: str) -> Any:
    return _field(_field(answer, "answers"), qid)


def _name(value: Any) -> str | None:
    return value.strip().lower().replace("-", "_").replace(" ", "_") if isinstance(value, str) else None


def _quantity_mm(value: Any) -> float | None:
    if not isinstance(value, dict):
        return None
    number = value.get("value")
    unit = _name(value.get("unit"))
    factors = {"mm": 1, "cm": 10, "m": 1000, "um": 0.001, "µm": 0.001}
    if isinstance(number, bool) or not isinstance(number, (int, float)) or unit not in factors:
        return None
    result = float(number) * factors[unit]
    return result if math.isfinite(result) else None


def _mirror_geometry(case: dict[str, Any], answer: dict[str, Any]) -> list[dict[str, Any]]:
    given = next((item for item in case.get("task", {}).get("givens", []) if item.get("symbol") == "lateral_offset"), None)
    target = _quantity_mm(given)
    if target is None or target <= 0:
        return [_verdict(c["id"], "error", "The authored lateral-offset given is invalid.", "case_data")
                for c in case["scoring"]["criteria"]]
    q1, q2, q3 = (_q(answer, key) for key in ("q1", "q2", "q3"))
    out: list[dict[str, Any]] = []
    if q1 is MISSING:
        out.append(_missing("c_dogleg", "answers.q1"))
    elif not isinstance(q1, dict):
        out.append(_unknown("c_dogleg", "answers.q1"))
    else:
        mirrors = _field(q1, "mirror_count")
        parallel = _field(q1, "output_forward_parallel")
        same_height = _field(q1, "same_height")
        displacement = _field(q1, "lateral_offset")
        if MISSING in (mirrors, parallel, same_height, displacement):
            out.append(_missing("c_dogleg", "answers.q1.mirror_count/output_forward_parallel/same_height/lateral_offset"))
        elif _name(mirrors) in {"one", "three_or_more"} or parallel is False or same_height is False:
            out.append(_verdict("c_dogleg", "fail", "The declared two-reflection forward, same-height geometry is contradicted.", "physical_contradiction"))
        elif _name(mirrors) != "two" or parallel is not True or same_height is not True:
            out.append(_unknown("c_dogleg", "answers.q1"))
        else:
            offset = _quantity_mm(displacement)
            if offset is None:
                out.append(_unknown("c_dogleg", "answers.q1.lateral_offset"))
            elif math.isclose(offset, target, rel_tol=0, abs_tol=1e-9):
                out.append(_verdict("c_dogleg", "pass", "Two reflections give a forward-parallel, same-height output with the required offset."))
            else:
                out.append(_verdict("c_dogleg", "fail", "The stated lateral displacement differs from the case given.", "physical_contradiction"))
    if q2 is MISSING:
        out.append(_missing("c_orientation", "answers.q2"))
    elif not isinstance(q2, dict):
        out.append(_unknown("c_orientation", "answers.q2"))
    else:
        cancels = _field(q2, "angular_deflections_cancel")
        geometry = _name(_field(q2, "mirror_geometry"))
        if cancels is False or geometry in {"perpendicular_planes", "same_direction_deflections"}:
            out.append(_verdict("c_orientation", "fail", "The second deflection does not restore the original forward direction.", "physical_contradiction"))
        elif cancels is True and geometry in {"parallel_planes", "equivalent_two_reflection_dogleg"}:
            out.append(_verdict("c_orientation", "pass", "The mirror geometry cancels angular deflection while allowing a lateral offset."))
        elif cancels is MISSING or geometry is None:
            out.append(_missing("c_orientation", "answers.q2.angular_deflections_cancel/mirror_geometry"))
        else:
            out.append(_unknown("c_orientation", "answers.q2"))
    if q3 is MISSING:
        out.append(_missing("c_single_reflection", "answers.q3"))
    elif not isinstance(q3, dict):
        out.append(_unknown("c_single_reflection", "answers.q3"))
    else:
        sufficient = _field(q3, "single_reflection_sufficient")
        reason = _name(_field(q3, "reason"))
        if sufficient is True or reason in {"arbitrary_translation", "forward_parallel_translation"}:
            out.append(_verdict("c_single_reflection", "fail", "One ordinary reflection cannot provide arbitrary pure forward translation.", "physical_contradiction"))
        elif sufficient is False and reason in {"changes_direction", "one_reflection_changes_direction"}:
            out.append(_verdict("c_single_reflection", "pass", "A single plane reflection changes direction rather than producing pure forward translation."))
        elif sufficient is MISSING or reason is None:
            out.append(_missing("c_single_reflection", "answers.q3.single_reflection_sufficient/reason"))
        else:
            out.append(_unknown("c_single_reflection", "answers.q3"))
    return out


def _dichroic(answer: dict[str, Any]) -> list[dict[str, Any]]:
    q1, q2, q3 = (_q(answer, key) for key in ("q1", "q2", "q3"))
    out: list[dict[str, Any]] = []
    if q1 is MISSING:
        out.append(_missing("c_routing", "answers.q1"))
    elif not isinstance(q1, dict):
        out.append(_unknown("c_routing", "answers.q1"))
    else:
        green, infrared = _name(_field(q1, "wavelength_532_nm")), _name(_field(q1, "wavelength_1064_nm"))
        if green is None or infrared is None:
            out.append(_missing("c_routing", "answers.q1.wavelength_532_nm/wavelength_1064_nm"))
        elif green in {"transmitted", "transmission"} or infrared in {"reflected", "reflection"}:
            out.append(_verdict("c_routing", "fail", "At the design angle the 532 nm beam reflects and the 1064 nm beam transmits.", "physical_contradiction"))
        elif green in {"reflected", "reflection"} and infrared in {"transmitted", "transmission"}:
            out.append(_verdict("c_routing", "pass", "The two specified wavelengths exit in the specified reflected and transmitted ports."))
        else:
            out.append(_unknown("c_routing", "answers.q1"))
    if q2 is MISSING:
        out.append(_missing("c_angle", "answers.q2"))
    elif not isinstance(q2, dict):
        out.append(_unknown("c_angle", "answers.q2"))
    else:
        spectral = _field(q2, "response_may_change")
        kind = _name(_field(q2, "change_kind"))
        if spectral is False or kind in {"no_change", "guaranteed_same_routing"}:
            out.append(_verdict("c_angle", "fail", "A substantial incidence-angle change need not preserve the coating response.", "physical_contradiction"))
        elif spectral is True and kind in {"band_shift", "cutoff_shift", "reflectance_transmittance_change", "performance_change"}:
            out.append(_verdict("c_angle", "pass", "Incidence angle can shift the coating response or change routing performance."))
        elif spectral is MISSING or kind is None:
            out.append(_missing("c_angle", "answers.q2.response_may_change/change_kind"))
        else:
            out.append(_unknown("c_angle", "answers.q2"))
    if q3 is MISSING:
        out.append(_missing("c_polarization", "answers.q3"))
    elif not isinstance(q3, dict):
        out.append(_unknown("c_polarization", "answers.q3"))
    else:
        preserved = _field(q3, "unconditionally_preserved")
        mechanism = _name(_field(q3, "mechanism"))
        if preserved is True:
            out.append(_verdict("c_polarization", "fail", "The coating does not guarantee preservation of every polarization state.", "physical_contradiction"))
        elif preserved is False and mechanism in {"s_p_amplitude_difference", "s_p_phase_difference", "s_p_response_difference"}:
            out.append(_verdict("c_polarization", "pass", "Different s and p coating responses can alter output polarization."))
        elif preserved is MISSING or mechanism is None:
            out.append(_missing("c_polarization", "answers.q3.unconditionally_preserved/mechanism"))
        else:
            out.append(_unknown("c_polarization", "answers.q3"))
    return out


def _quarter_wave(answer: dict[str, Any]) -> list[dict[str, Any]]:
    q1, q2, q3 = (_q(answer, key) for key in ("q1", "q2", "q3"))
    out: list[dict[str, Any]] = []
    for criterion, q, wanted in (("c_circular", q1, "circular"), ("c_zero", q2, "linear")):
        path = "answers.q1" if criterion == "c_circular" else "answers.q2"
        if q is MISSING:
            out.append(_missing(criterion, path))
        else:
            state = _name(q if isinstance(q, str) else _field(q, "state"))
            if state is None:
                out.append(_unknown(criterion, path))
            elif state == wanted:
                out.append(_verdict(criterion, "pass", f"Ideal quarter-wave-plate output at this angle is {wanted}."))
            elif state in {"linear", "circular", "elliptical", "unpolarized"}:
                out.append(_verdict(criterion, "fail", f"The asserted {state} output conflicts with the ideal plate at this angle.", "physical_contradiction"))
            else:
                out.append(_unknown(criterion, path))
    if q3 is MISSING:
        out.append(_missing("c_handed", "answers.q3"))
    elif not isinstance(q3, dict):
        out.append(_unknown("c_handed", "answers.q3"))
    else:
        dependencies = _field(q3, "depends_on")
        if dependencies is MISSING:
            out.append(_missing("c_handed", "answers.q3.depends_on"))
        elif not isinstance(dependencies, list) or not all(isinstance(x, str) for x in dependencies):
            out.append(_unknown("c_handed", "answers.q3.depends_on"))
        else:
            names = {_name(x) for x in dependencies}
            if "independent_of_axes" in names or "independent_of_convention" in names:
                out.append(_verdict("c_handed", "fail", "Handedness is not independent of input/axis orientation and convention.", "physical_contradiction"))
            elif names - {"input_axis_orientation", "fast_slow_phase_sign", "observation_convention"}:
                out.append(_unknown("c_handed", "answers.q3.depends_on"))
            elif {"input_axis_orientation", "fast_slow_phase_sign", "observation_convention"} <= names:
                out.append(_verdict("c_handed", "pass", "The answer identifies the physical phase/orientation and labeling convention."))
            elif names <= {"input_axis_orientation", "fast_slow_phase_sign", "observation_convention"}:
                out.append(_missing("c_handed", "answers.q3.depends_on (all dependencies)"))
            else:
                out.append(_unknown("c_handed", "answers.q3.depends_on"))
    return out


def _gaussian_focus(answer: dict[str, Any]) -> list[dict[str, Any]]:
    q1, q2, q3 = (_q(answer, key) for key in ("q1", "q2", "q3"))
    out: list[dict[str, Any]] = []
    if q1 is MISSING:
        out.append(_missing("c_q1", "answers.q1"))
    else:
        possible = q1 if isinstance(q1, bool) else _field(q1, "simultaneous_trend_possible")
        if possible is False:
            out.append(_verdict("c_q1", "pass", "At fixed wavelength and beam quality, shrinking the waist shortens Rayleigh range."))
        elif possible is True:
            out.append(_verdict("c_q1", "fail", "The proposed simultaneous trends violate the fixed-quality Gaussian relation.", "physical_contradiction"))
        else:
            out.append(_unknown("c_q1", "answers.q1"))
    if q2 is MISSING:
        out.append(_missing("c_q2", "answers.q2"))
    elif not isinstance(q2, dict):
        out.append(_unknown("c_q2", "answers.q2"))
    else:
        relation = _name(_field(q2, "relation"))
        radius = _name(_field(q2, "waist_definition"))
        assumptions = _field(q2, "assumptions")
        if relation is None or radius is None or assumptions is MISSING:
            out.append(_missing("c_q2", "answers.q2.relation/waist_definition/assumptions"))
        elif not isinstance(assumptions, list) or not all(isinstance(x, str) for x in assumptions):
            out.append(_unknown("c_q2", "answers.q2.assumptions"))
        else:
            assumptions_set = {_name(x) for x in assumptions}
            required = {"paraxial_gaussian", "fixed_wavelength", "fixed_beam_quality"}
            correct = {"z_r_equals_pi_w0_squared_over_m2_lambda", "z_r_proportional_to_w0_squared_at_fixed_lambda_m2"}
            wrong = {"z_r_inversely_proportional_to_w0_squared", "z_r_proportional_to_inverse_w0", "z_r_proportional_to_w0"}
            if relation in wrong:
                out.append(_verdict("c_q2", "fail", "The claimed Rayleigh-range dependence on waist is wrong.", "physical_contradiction"))
            elif "variable_beam_quality" in assumptions_set or "variable_wavelength" in assumptions_set:
                out.append(_verdict("c_q2", "fail", "The stated variable condition contradicts the fixed-quality or fixed-wavelength premise.", "physical_contradiction"))
            elif assumptions_set - required:
                out.append(_unknown("c_q2", "answers.q2.assumptions"))
            elif relation in correct and radius == "one_over_e_squared_intensity" and required <= assumptions_set:
                out.append(_verdict("c_q2", "pass", "The fixed-quality paraxial Gaussian Rayleigh relation is specified with the 1/e² waist convention."))
            elif relation in correct and radius == "one_over_e_squared_intensity" and assumptions_set <= required:
                out.append(_missing("c_q2", "answers.q2.assumptions (all stated conditions)"))
            else:
                out.append(_unknown("c_q2", "answers.q2"))
    if q3 is MISSING:
        out.append(_missing("c_q3", "answers.q3"))
    else:
        costs = q3 if isinstance(q3, list) else _field(q3, "costs") if isinstance(q3, dict) else [q3]
        if costs is MISSING:
            out.append(_missing("c_q3", "answers.q3.costs"))
        elif not isinstance(costs, list) or not all(isinstance(x, str) for x in costs):
            out.append(_unknown("c_q3", "answers.q3"))
        else:
            names = {_name(x) for x in costs}
            valid = {"shorter_rayleigh_range", "shorter_depth_of_focus", "greater_divergence"}
            optional = {"greater_aberration_sensitivity", "greater_focusing_sensitivity"}
            invalid = {"longer_rayleigh_range", "longer_depth_of_focus", "smaller_divergence"}
            if names & invalid:
                out.append(_verdict("c_q3", "fail", "The claimed cost reverses the fixed-quality Gaussian tradeoff.", "physical_contradiction"))
            elif names - valid - optional:
                out.append(_unknown("c_q3", "answers.q3"))
            elif names & valid:
                out.append(_verdict("c_q3", "pass", "A smaller waist has a shorter focus range or larger divergence."))
            elif not names:
                out.append(_missing("c_q3", "answers.q3.costs"))
            else:
                out.append(_unknown("c_q3", "answers.q3"))
    return out


def evaluate(case: dict[str, Any], answer: dict[str, Any]) -> list[dict[str, Any]]:
    """Evaluate registered typed cases; unsupported case IDs return no verdicts."""
    if not isinstance(answer, dict):
        return [_verdict(c["id"], "fail", "Answer is not an object.", "invalid_contract") for c in case["scoring"]["criteria"]]
    if case.get("case_id") == "SEED-1-3":
        return _mirror_geometry(case, answer)
    scorer = {
        "SEED-1-6": _dichroic,
        "SEED-4-1": _quarter_wave,
        "SEED-7-8": _gaussian_focus,
    }.get(case.get("case_id"))
    return scorer(answer) if scorer else []
