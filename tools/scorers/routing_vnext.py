"""Versioned functional constraint checks for dual-wavelength free-space routing.

The routing matrix and two-plane data are observables; architecture names alone
cannot pass. Unknown credible optical methods abstain after hard physics checks.
"""

from __future__ import annotations

import math
from typing import Any


WAVELENGTHS = ("nm532", "nm1064")
DETECTORS = ("detector_532", "detector_1064")
COMBINERS = {"dichroic_combiner", "dispersive_recombiner"}
SEPARATORS = {"dichroic_separator", "dispersive_separator"}
PROPERTY_TESTS = {
    "coating_spectrum": "spectral_transmission_scan",
    "incidence_angle": "angle_sweep",
    "polarization_dependence": "polarization_sweep",
    "chromatic_focus": "focus_at_both_wavelengths",
    "damage_threshold": "power_margin_check",
    "detector_responsivity": "detector_calibration_both_wavelengths",
    "filter_blocking": "filter_leakage_scan",
}


def _result(check: str, status: str, evidence: str, *, failure: str | None = None,
            details: dict[str, Any] | None = None) -> dict[str, Any]:
    out = {"criterion_id": check, "check_id": check, "status": status,
           "score": 1 if status == "pass" else 0 if status == "fail" else None,
           "evidence": evidence, "details": details or {}}
    if failure:
        out["details"]["failure_class"] = failure
    return out


def _number(value: Any, unit: str) -> float | None:
    if not isinstance(value, dict) or value.get("unit") != unit:
        return None
    value = value.get("value")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _question(answer: dict[str, Any], q: str) -> Any:
    answers = answer.get("answers")
    return answers.get(q) if isinstance(answers, dict) else None


def _routing(q1: Any) -> tuple[dict[str, dict[str, float]] | None, float | None, str | None]:
    if not isinstance(q1, dict):
        return None, None, "missing_claim"
    limit = _number(q1.get("max_cross_channel_fraction"), "1")
    matrix = q1.get("routing_matrix")
    if limit is None or not 0 < limit < 1 or not isinstance(matrix, dict):
        return None, None, "malformed_claim"
    out = {}
    for wavelength in WAVELENGTHS:
        row = matrix.get(wavelength)
        if not isinstance(row, dict):
            return None, None, "malformed_claim"
        nums = {detector: _number(row.get(detector), "1") for detector in DETECTORS}
        if None in nums.values():
            return None, None, "malformed_claim"
        out[wavelength] = nums
    return out, limit, None


def _q1(q1: Any) -> dict[str, Any]:
    matrix, limit, error = _routing(q1)
    if error:
        return _result("c_q1", "fail", "A finite routing matrix and leakage requirement are required.", failure=error)
    if q1.get("common_transport") != "free_space_collinear" or not isinstance(q1.get("combiner"), str) or not isinstance(q1.get("separator"), str):
        return _result("c_q1", "fail", "Specify free-space common transport and optical combination/separation functions.",
                       failure="missing_function")
    assert matrix is not None and limit is not None
    for wavelength, row in matrix.items():
        main = row["detector_" + wavelength[2:]]
        cross = row["detector_1064" if wavelength == "nm532" else "detector_532"]
        if any(not 0 <= fraction <= 1 for fraction in row.values()) or sum(row.values()) > 1 + 1e-9:
            return _result("c_q1", "fail", "Routing fractions violate passive power conservation.",
                           failure="unphysical_routing_matrix")
        if main <= 0 or cross >= main or cross > limit + 1e-12:
            return _result("c_q1", "fail", "A channel is misrouted or exceeds the declared finite leakage requirement.",
                           failure="channel_routing_failure", details={"wavelength_nm": wavelength})
    if q1.get("perfect_extinction") is True:
        return _result("c_q1", "fail", "Literal perfect extinction is not a justified physical claim.",
                       failure="infinite_extinction_claim")
    if q1["combiner"] not in COMBINERS or q1["separator"] not in SEPARATORS:
        return _result("c_q1", "unresolved", "The measured matrix is plausible, but this optical architecture is unfamiliar.",
                       failure="unsupported_alternative")
    return _result("c_q1", "pass", "Both wavelengths have a dominant assigned detector and bounded finite cross leakage.",
                   details={"max_cross_channel_fraction": limit})


def _q2(q2: Any) -> dict[str, Any]:
    if not isinstance(q2, dict) or not isinstance(q2.get("planes"), list):
        return _result("c_q2", "fail", "Two-plane centroid measurements are required.", failure="missing_claim")
    planes = q2["planes"]
    if len(planes) < 2 or q2.get("sources_measured_separately") is not True:
        return _result("c_q2", "fail", "Operate sources separately and observe both wavelengths at two longitudinal planes.",
                       failure="insufficient_collinearity_measurements")
    pos_limit = _number(q2.get("max_position_difference_mm"), "mm")
    ang_limit = _number(q2.get("max_angle_difference_mrad"), "mrad")
    if pos_limit is None or ang_limit is None or pos_limit <= 0 or ang_limit <= 0:
        return _result("c_q2", "fail", "Finite positive position and direction tolerances are required.",
                       failure="malformed_claim")
    observations = []
    for plane in planes:
        if not isinstance(plane, dict):
            return _result("c_q2", "fail", "A plane measurement is malformed.", failure="malformed_claim")
        z = _number(plane.get("z_m"), "m")
        centers = plane.get("centroids_mm")
        if z is None or not isinstance(centers, dict):
            return _result("c_q2", "fail", "A plane needs axial position and two centroids.", failure="malformed_claim")
        coords = {}
        for wavelength in WAVELENGTHS:
            xy = centers.get(wavelength)
            if not isinstance(xy, dict) or _number(xy.get("x"), "mm") is None or _number(xy.get("y"), "mm") is None:
                return _result("c_q2", "fail", "Each wavelength needs a finite x/y centroid at every plane.",
                               failure="malformed_claim")
            coords[wavelength] = (_number(xy["x"], "mm"), _number(xy["y"], "mm"))
        observations.append((z, coords))
    observations.sort(key=lambda item: item[0])
    if any(b[0] <= a[0] for a, b in zip(observations, observations[1:])):
        return _result("c_q2", "fail", "Observation planes must have distinct axial positions.", failure="zero_plane_baseline")
    differences = [(c["nm532"][0]-c["nm1064"][0], c["nm532"][1]-c["nm1064"][1]) for _, c in observations]
    max_position = max(math.hypot(*difference) for difference in differences)
    z0, z1 = observations[0][0], observations[-1][0]
    d0, d1 = differences[0], differences[-1]
    angle_mrad = math.hypot(d1[0]-d0[0], d1[1]-d0[1]) / (z1-z0)
    details = {"maximum_position_difference_mm": max_position, "angle_difference_mrad": angle_mrad}
    if max_position > pos_limit + 1e-9 or angle_mrad > ang_limit + 1e-9:
        return _result("c_q2", "fail", "Measured position or direction mismatch exceeds the submitted tolerance.",
                       failure="noncollinear_measurement", details=details)
    return _result("c_q2", "pass", "Separate-source centroids agree in position and direction over two planes.", details=details)


def _q3(q3: Any, q1: Any) -> dict[str, Any]:
    if not isinstance(q3, dict) or not isinstance(q3.get("properties"), list):
        return _result("c_q3", "fail", "Component property tests and leakage validation are required.", failure="missing_claim")
    seen, unknown = set(), []
    for index, entry in enumerate(q3["properties"]):
        if not isinstance(entry, dict) or not isinstance(entry.get("property"), str):
            return _result("c_q3", "fail", "A component property entry is malformed.", failure="malformed_claim")
        name = entry["property"]
        if name in seen:
            continue
        seen.add(name)
        if name not in PROPERTY_TESTS:
            unknown.append(index)
        elif entry.get("test") != PROPERTY_TESTS[name]:
            return _result("c_q3", "fail", "A named component property lacks its discriminating test.",
                           failure="unverified_property", details={"property": name})
    leakage = q3.get("leakage_test")
    if not isinstance(leakage, dict) or leakage.get("method") != "one_source_at_a_time_dark_corrected":
        return _result("c_q3", "fail", "Cross-channel leakage needs separate-source dark-corrected measurements.",
                       failure="missing_leakage_measurement")
    observed = leakage.get("measured_cross_channel_fractions")
    if not isinstance(observed, dict) or any(_number(observed.get(w), "1") is None for w in WAVELENGTHS):
        return _result("c_q3", "fail", "Report finite measured cross-channel fractions for both sources.",
                       failure="malformed_claim")
    matrix, limit, error = _routing(q1)
    if error:
        return _result("c_q3", "unresolved", "The declared leakage requirement in q1 is unavailable.",
                       failure="dependent_model_missing")
    assert matrix is not None and limit is not None
    observed_fractions = {w: _number(observed[w], "1") for w in WAVELENGTHS}
    if any(not 0 <= observed_fractions[w] <= 1 or observed_fractions[w] > limit + 1e-12 for w in WAVELENGTHS):
        return _result("c_q3", "fail", "Measured cross-channel leakage exceeds the stated requirement.",
                       failure="leakage_limit_exceeded")
    known = len(seen & PROPERTY_TESTS.keys())
    if known >= 4:
        return _result("c_q3", "pass", "Four distinct wavelength-dependent properties are tested and both leakage directions satisfy the limit.",
                       details={"property_count": known})
    if known + len(unknown) >= 4:
        return _result("c_q3", "unresolved", "Novel component properties may satisfy the four-property requirement.",
                       failure="unsupported_alternative", details={"unknown_indices": unknown})
    return _result("c_q3", "fail", "Fewer than four distinct tested wavelength-dependent properties were supplied.",
                   failure="insufficient_property_checks")


def evaluate(case: dict[str, Any], answer: dict[str, Any]) -> list[dict[str, Any]]:
    checks = ("c_q1", "c_q2", "c_q3")
    if not isinstance(case, dict) or case.get("case_id") != "SEED-8-6":
        return [_result(check, "error", "Wrong case for this scorer.", failure="wrong_case") for check in checks]
    if not isinstance(answer, dict):
        return [_result(check, "fail", "Structured answer is missing.", failure="missing_claim") for check in checks]
    q1, q2, q3 = (_question(answer, f"q{i}") for i in range(1, 4))
    return [_q1(q1), _q2(q2), _q3(q3, q1)]
