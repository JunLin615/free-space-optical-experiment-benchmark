"""Bounded, typed optical checks for prospective post-rc1 case families.

This module is deliberately not wired into the frozen rc1 evaluator. Unknown
representations abstain; explicit contradictions and missing claims are local
to their criterion. It certifies declared physics, not arbitrary prose.
"""

from __future__ import annotations

import math
from typing import Any


MISSING = object()
SCORES = {"pass": 1, "fail": 0, "unresolved": None, "error": None}


def _v(cid: str, status: str, evidence: str, failure_class: str | None = None) -> dict[str, Any]:
    details = {"failure_class": failure_class} if failure_class else {}
    return {"criterion_id": cid, "check_id": cid, "status": status,
            "score": SCORES[status], "evidence": evidence, "details": details}


def _missing(cid: str, path: str) -> dict[str, Any]:
    return _v(cid, "fail", f"Missing structured claim at {path}.", "missing_claim")


def _unknown(cid: str, path: str) -> dict[str, Any]:
    return _v(cid, "unresolved", f"Unrecognized representation at {path}.", "unsupported_alternative")


def _get(value: Any, key: str) -> Any:
    return value.get(key, MISSING) if isinstance(value, dict) else MISSING


def _q(answer: dict[str, Any], key: str) -> Any:
    return _get(_get(answer, "answers"), key)


def _name(value: Any) -> str | None:
    return value.strip().lower().replace("-", "_").replace(" ", "_") if isinstance(value, str) else None


def _names(value: Any) -> set[str] | None:
    if not isinstance(value, list) or any(not isinstance(x, str) for x in value):
        return None
    return {_name(x) for x in value}


def _mm(value: Any) -> float | None:
    if not isinstance(value, dict):
        return None
    unit = _name(value.get("unit"))
    factor = {"um": .001, "µm": .001, "mm": 1, "cm": 10, "m": 1000}.get(unit)
    number = value.get("value")
    if factor is None or isinstance(number, bool) or not isinstance(number, (int, float)):
        return None
    result = float(number) * factor
    return result if math.isfinite(result) else None


def _dimensionless(value: Any) -> float | None:
    if not isinstance(value, dict) or value.get("unit") != "1":
        return None
    number = value.get("value")
    if isinstance(number, bool) or not isinstance(number, (int, float)):
        return None
    return float(number) if math.isfinite(number) else None


def _periscope(case: dict[str, Any], answer: dict[str, Any]) -> list[dict[str, Any]]:
    givens = {g.get("symbol"): _mm(g) for g in case.get("task", {}).get("givens", [])}
    if givens.get("input_height") is None or givens.get("output_height") is None:
        return [_v(c["id"], "error", "Invalid authored heights.", "case_data") for c in case["scoring"]["criteria"]]
    lift = givens["output_height"] - givens["input_height"]
    q1, q2, q3 = (_q(answer, q) for q in ("q1", "q2", "q3"))
    out = []
    if q1 is MISSING:
        out.append(_missing("c_periscope", "answers.q1"))
    elif not isinstance(q1, dict):
        out.append(_unknown("c_periscope", "answers.q1"))
    else:
        count, leg = _dimensionless(_get(q1, "mirror_count")), _name(_get(q1, "intermediate_leg"))
        forward, parallel = _get(q1, "output_forward"), _get(q1, "output_parallel")
        height = _mm(_get(q1, "height_change"))
        if _get(q1, "mirror_count") is MISSING or MISSING in (forward, parallel) or _get(q1, "height_change") is MISSING or leg is None:
            out.append(_missing("c_periscope", "answers.q1.mirror_count/intermediate_leg/height_change/output_forward/output_parallel"))
        elif count == 1 or forward is False or parallel is False or leg in {"horizontal", "downward"}:
            out.append(_v("c_periscope", "fail", "The declared path cannot provide the specified two-reflection forward lift.", "physical_contradiction"))
        elif count != 2 or forward is not True or parallel is not True or leg != "upward":
            out.append(_unknown("c_periscope", "answers.q1"))
        elif height is None:
            out.append(_unknown("c_periscope", "answers.q1.height_change"))
        elif math.isclose(height, lift, abs_tol=1e-9):
            out.append(_v("c_periscope", "pass", "Two reflections with an upward leg provide the authored lift and restore forward propagation."))
        else:
            out.append(_v("c_periscope", "fail", "Declared lift differs from the required height change.", "physical_contradiction"))
    if q2 is MISSING:
        out.append(_missing("c_other_property", "answers.q2"))
    else:
        effects = _names(q2 if isinstance(q2, list) else _get(q2, "possible_changes"))
        valid = {"lateral_offset", "image_orientation", "polarization_basis", "polarization_phase"}
        if effects is None:
            out.append(_unknown("c_other_property", "answers.q2.possible_changes"))
        elif "no_other_property_can_change" in effects:
            out.append(_v("c_other_property", "fail", "The layout can alter another geometric or polarization property.", "physical_contradiction"))
        elif effects - valid:
            out.append(_unknown("c_other_property", "answers.q2.possible_changes"))
        elif effects & valid:
            out.append(_v("c_other_property", "pass", "A layout-dependent additional property is identified."))
        else:
            out.append(_missing("c_other_property", "answers.q2.possible_changes"))
    if q3 is MISSING:
        out.append(_missing("c_parallel_test", "answers.q3"))
    elif not isinstance(q3, dict):
        out.append(_unknown("c_parallel_test", "answers.q3"))
    else:
        method = _name(_get(q3, "method"))
        ref = _name(_get(q3, "reference"))
        if method is None or ref is None:
            out.append(_missing("c_parallel_test", "answers.q3.method/reference"))
        elif method == "one_point_hit" or ref == "uncalibrated_aperture_line":
            out.append(_v("c_parallel_test", "fail", "A single hit or unreferenced line does not prove parallelism.", "unreferenced_test"))
        elif (method == "two_separated_planes" and ref == "line_calibrated_parallel_to_input") or (method == "independent_angle_comparison" and ref == "measured_input_direction"):
            out.append(_v("c_parallel_test", "pass", "The angular test uses a reference tied to the input direction."))
        else:
            out.append(_unknown("c_parallel_test", "answers.q3"))
    return out


def _relay(answer: dict[str, Any]) -> list[dict[str, Any]]:
    q1, q2, q3 = (_q(answer, q) for q in ("q1", "q2", "q3"))
    out = []
    if q1 is MISSING:
        out.append(_missing("c_4f", "answers.q1"))
    elif not isinstance(q1, dict):
        out.append(_unknown("c_4f", "answers.q1"))
    else:
        values = [_mm(_get(q1, key)) for key in ("f1", "f2", "object_to_lens1", "lens_separation", "lens2_to_image")]
        if any(_get(q1, key) is MISSING for key in ("f1", "f2", "object_to_lens1", "lens_separation", "lens2_to_image")):
            out.append(_missing("c_4f", "answers.q1.f1/f2/object_to_lens1/lens_separation/lens2_to_image"))
        elif any(x is None for x in values):
            out.append(_unknown("c_4f", "answers.q1"))
        else:
            f1, f2, obj, sep, image = values
            if min(values) <= 0 or not all(math.isclose(a, b, rel_tol=1e-8, abs_tol=1e-8) for a, b in ((f1, f2), (obj, f1), (sep, f1 + f2), (image, f2))):
                out.append(_v("c_4f", "fail", "Declared distances do not form a positive unity-magnification 4f relay.", "physical_contradiction"))
            else:
                out.append(_v("c_4f", "pass", "Positive equal focal lengths and conjugate distances form a unity-magnification 4f relay."))
    if q2 is MISSING:
        out.append(_missing("c_fourier", "answers.q2"))
    elif not isinstance(q2, dict):
        out.append(_unknown("c_fourier", "answers.q2"))
    else:
        location = _name(_get(q2, "stop_plane"))
        shared = _get(q2, "shared_focal_plane")
        if location is None or shared is MISSING:
            out.append(_missing("c_fourier", "answers.q2.stop_plane/shared_focal_plane"))
        elif location == "ordinary_image_plane" or shared is False:
            out.append(_v("c_fourier", "fail", "The stop must occupy the shared focal Fourier plane.", "physical_contradiction"))
        elif location == "between_lenses" and shared is True:
            out.append(_v("c_fourier", "pass", "The stop is at the accessible shared focal plane."))
        else:
            out.append(_unknown("c_fourier", "answers.q2"))
    if q3 is MISSING:
        out.append(_missing("c_not_image", "answers.q3"))
    elif not isinstance(q3, dict):
        out.append(_unknown("c_not_image", "answers.q3"))
    else:
        represents = _name(_get(q3, "represents"))
        direct = _get(q3, "direct_geometric_image")
        if represents is None or direct is MISSING:
            out.append(_missing("c_not_image", "answers.q3.represents/direct_geometric_image"))
        elif direct is True or represents == "object_positions":
            out.append(_v("c_not_image", "fail", "The Fourier plane is not a direct ordinary object image.", "physical_contradiction"))
        elif direct is False and represents in {"spatial_frequencies", "angular_spectrum"}:
            out.append(_v("c_not_image", "pass", "The intermediate plane encodes spatial-frequency content."))
        else:
            out.append(_unknown("c_not_image", "answers.q3"))
    return out


def _fourier_stop(answer: dict[str, Any]) -> list[dict[str, Any]]:
    q1, q2, q3 = (_q(answer, q) for q in ("q1", "q2", "q3"))
    out = []
    if q1 is MISSING:
        out.append(_missing("c_effect", "answers.q1"))
    elif not isinstance(q1, dict):
        out.append(_unknown("c_effect", "answers.q1"))
    else:
        suppressed = _name(_get(q1, "suppressed"))
        broad = _name(_get(q1, "broad_structure"))
        appearance = _name(_get(q1, "edge_appearance"))
        if None in (suppressed, broad, appearance):
            out.append(_missing("c_effect", "answers.q1.suppressed/broad_structure/edge_appearance"))
        elif suppressed == "high_frequencies" or broad == "strengthened" or appearance == "always_enhanced":
            out.append(_v("c_effect", "fail", "The claimed image effect contradicts central low-frequency rejection or overpromises appearance.", "physical_contradiction"))
        elif suppressed in {"zero_and_nearby_low_frequencies", "low_frequencies"} and broad == "attenuated" and appearance == "may_be_more_prominent":
            out.append(_v("c_effect", "pass", "Broad structure is reduced; relative edge prominence remains conditional."))
        else:
            out.append(_unknown("c_effect", "answers.q1"))
    if q2 is MISSING:
        out.append(_missing("c_class", "answers.q2"))
    else:
        kind = _name(q2 if isinstance(q2, str) else _get(q2, "filter_class"))
        if kind in {"high_pass", "high_pass_like"}:
            out.append(_v("c_class", "pass", "Central obscuration is high-pass-like."))
        elif kind == "low_pass":
            out.append(_v("c_class", "fail", "Blocking the Fourier origin does not make a low-pass filter.", "physical_contradiction"))
        else:
            out.append(_unknown("c_class", "answers.q2"))
    if q3 is MISSING:
        out.append(_missing("c_mechanism", "answers.q3"))
    elif not isinstance(q3, dict):
        out.append(_unknown("c_mechanism", "answers.q3"))
    else:
        plane = _name(_get(q3, "plane"))
        rejected = _name(_get(q3, "rejected"))
        higher = _name(_get(q3, "higher_frequencies"))
        if None in (plane, rejected, higher):
            out.append(_missing("c_mechanism", "answers.q3.plane/rejected/higher_frequencies"))
        elif rejected == "high_frequencies" or higher == "blocked":
            out.append(_v("c_mechanism", "fail", "The spectral rejection direction is reversed.", "physical_contradiction"))
        elif plane == "fourier" and rejected in {"zero_and_nearby_low_frequencies", "low_frequencies"} and higher == "transmitted_relative_to_low":
            out.append(_v("c_mechanism", "pass", "The Fourier stop reduces low-frequency weight relative to transmitted higher frequencies."))
        else:
            out.append(_unknown("c_mechanism", "answers.q3"))
    return out


def _half_wave(answer: dict[str, Any]) -> list[dict[str, Any]]:
    q1, q2, q3 = (_q(answer, q) for q in ("q1", "q2", "q3"))
    out = []
    if q1 is MISSING:
        out.append(_missing("c_q1", "answers.q1"))
    else:
        possible = q1 if isinstance(q1, bool) else _get(q1, "full_range_possible")
        if possible is False:
            out.append(_v("c_q1", "pass", "An ideal half-wave plate alone cannot vary the analyzed power of circular input."))
        elif possible is True:
            out.append(_v("c_q1", "fail", "The full-range claim conflicts with ideal circular input.", "physical_contradiction"))
        else:
            out.append(_unknown("c_q1", "answers.q1"))
    if q2 is MISSING:
        out.append(_missing("c_q2", "answers.q2"))
    elif not isinstance(q2, dict):
        out.append(_unknown("c_q2", "answers.q2"))
    else:
        state = _name(_get(q2, "output_state"))
        handedness = _name(_get(q2, "handedness"))
        share = _dimensionless(_get(q2, "analyzer_port_fraction"))
        independent = _get(q2, "independent_of_plate_angle")
        if None in (state, handedness) or _get(q2, "analyzer_port_fraction") is MISSING or independent is MISSING:
            out.append(_missing("c_q2", "answers.q2.output_state/handedness/analyzer_port_fraction/independent_of_plate_angle"))
        elif state == "linear" or handedness == "preserved" or independent is False:
            out.append(_v("c_q2", "fail", "Ideal half-wave action reverses circular handedness without angle-dependent analyzer splitting.", "physical_contradiction"))
        elif state != "circular" or handedness != "reversed" or independent is not True or share is None:
            out.append(_unknown("c_q2", "answers.q2"))
        elif math.isclose(float(share), .5, abs_tol=1e-9):
            out.append(_v("c_q2", "pass", "The ideal analyzer receives one half of total power for every plate angle."))
        else:
            out.append(_v("c_q2", "fail", "The ideal linear-analyzer port fraction is one half.", "physical_contradiction"))
    if q3 is MISSING:
        out.append(_missing("c_q3", "answers.q3"))
    else:
        stages = _names(q3 if isinstance(q3, list) else _get(q3, "stages"))
        if stages is None:
            out.append(_unknown("c_q3", "answers.q3.stages"))
        elif "half_wave_plate_only" in stages:
            out.append(_v("c_q3", "fail", "The original half-wave-only proposal does not modulate circular input.", "physical_contradiction"))
        elif stages - {"quarter_wave_linearization", "rotatable_half_wave_plate", "rotatable_quarter_wave_linearization", "fixed_linear_analyzer"}:
            out.append(_unknown("c_q3", "answers.q3.stages"))
        elif {"quarter_wave_linearization", "rotatable_half_wave_plate", "fixed_linear_analyzer"} <= stages:
            out.append(_v("c_q3", "pass", "Linearization followed by controlled rotation and a fixed analyzer permits ideal full-range variation."))
        elif {"rotatable_quarter_wave_linearization", "fixed_linear_analyzer"} <= stages:
            out.append(_v("c_q3", "pass", "Rotating an ideal quarter-wave plate maps circular input to a tunable linear axis at the fixed analyzer."))
        else:
            out.append(_missing("c_q3", "answers.q3.stages (complete chain)"))
    return out


def _purification(answer: dict[str, Any]) -> list[dict[str, Any]]:
    q1, q2, q3 = (_q(answer, q) for q in ("q1", "q2", "q3"))
    out = []
    if q1 is MISSING:
        out.append(_missing("c_q1", "answers.q1"))
    else:
        possible = q1 if isinstance(q1, bool) else _get(q1, "lossless_single_mode_possible")
        if possible is False:
            out.append(_v("c_q1", "pass", "Passive single-mode lossless purification is impossible."))
        elif possible is True:
            out.append(_v("c_q1", "fail", "Full-power passive compression of unpolarized light into one pure mode is impossible.", "physical_contradiction"))
        else:
            out.append(_unknown("c_q1", "answers.q1"))
    if q2 is MISSING:
        out.append(_missing("c_q2", "answers.q2"))
    elif not isinstance(q2, dict):
        out.append(_unknown("c_q2", "answers.q2"))
    else:
        input_rank = _dimensionless(_get(q2, "input_polarization_rank"))
        output_rank = _dimensionless(_get(q2, "pure_output_rank"))
        route = _name(_get(q2, "orthogonal_component"))
        if _get(q2, "input_polarization_rank") is MISSING or _get(q2, "pure_output_rank") is MISSING or route is None:
            out.append(_missing("c_q2", "answers.q2.input_polarization_rank/pure_output_rank/orthogonal_component"))
        elif route == "compressed_losslessly_into_same_mode":
            out.append(_v("c_q2", "fail", "A passive lossless map cannot compress both incoherent components into one pure mode.", "physical_contradiction"))
        elif (input_rank, output_rank) == (2, 1) and route in {"discarded", "other_output_mode"}:
            out.append(_v("c_q2", "pass", "The rank reduction requires discarding power or routing a component elsewhere."))
        else:
            out.append(_unknown("c_q2", "answers.q2"))
    if q3 is MISSING:
        out.append(_missing("c_q3", "answers.q3"))
    elif not isinstance(q3, dict):
        out.append(_unknown("c_q3", "answers.q3"))
    else:
        method = _name(_get(q3, "method"))
        discarded = _dimensionless(_get(q3, "discarded_power_fraction"))
        if method is None or _get(q3, "discarded_power_fraction") is MISSING:
            out.append(_missing("c_q3", "answers.q3.method/discarded_power_fraction"))
        elif method == "waveplate_only" or discarded == 0:
            out.append(_v("c_q3", "fail", "A wave plate or zero-discard claim cannot passively purify this single output.", "physical_contradiction"))
        elif method not in {"ideal_linear_polarizer", "select_one_pbs_output"} or discarded is None:
            out.append(_unknown("c_q3", "answers.q3"))
        elif math.isclose(float(discarded), .5, abs_tol=1e-9):
            out.append(_v("c_q3", "pass", "An ideal analyzer selects one linear component and discards half the unpolarized power."))
        else:
            out.append(_v("c_q3", "fail", "Ideal unpolarized input yields one half of power in a selected linear component.", "physical_contradiction"))
    return out


ORACLES = {"SEED-1-4": _periscope, "SEED-3-2": _relay, "SEED-3-3": _fourier_stop,
           "SEED-7-5": _half_wave, "SEED-7-6": _purification}


def evaluate(case: dict[str, Any], answer: dict[str, Any]) -> list[dict[str, Any]]:
    scorer = ORACLES.get(case.get("case_id"))
    if scorer is None:
        return []
    if not isinstance(answer, dict):
        return [_v(c["id"], "fail", "Answer is not an object.", "invalid_contract") for c in case["scoring"]["criteria"]]
    return scorer(case, answer) if scorer is _periscope else scorer(answer)
