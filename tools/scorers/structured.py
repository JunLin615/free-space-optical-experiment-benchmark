"""Conservative structured checks for two conceptual pilot cases.

These checks establish internal physical consistency of declared answer fields.
They do not judge arbitrary prose or certify experimental noise claims. Unknown
plausible structures abstain (`unresolved`) rather than being silently rejected.
"""

from __future__ import annotations

import math
from typing import Any


_MISSING = object()
_BOUNDED = {"pass": 1, "fail": 0, "unresolved": None, "error": None}


def _outcome(
    criterion_id: str,
    status: str,
    evidence: str,
    *,
    failure_class: str | None = None,
    **details: Any,
) -> dict[str, Any]:
    payload = {
        "criterion_id": criterion_id,
        "check_id": criterion_id,
        "status": status,
        "score": _BOUNDED[status],
        "evidence": evidence,
        "details": details,
    }
    if failure_class:
        payload["details"]["failure_class"] = failure_class
    return payload


def _question(answer: dict[str, Any], qid: str) -> Any:
    answers = answer.get("answers")
    return answers.get(qid, _MISSING) if isinstance(answers, dict) else _MISSING


def _name(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    return value.strip().lower().replace("-", "_").replace(" ", "_")


def _fraction(value: Any) -> float | None:
    if not isinstance(value, dict) or value.get("unit") != "1":
        return None
    number = value.get("value")
    if isinstance(number, bool) or not isinstance(number, (int, float)):
        return None
    number = float(number)
    return number if math.isfinite(number) else None


def _missing(criterion: str, path: str) -> dict[str, Any]:
    return _outcome(criterion, "fail", f"Missing required structured claim at {path}.", failure_class="missing_claim")


def _beam_product(case: dict[str, Any], answer: dict[str, Any]) -> list[dict[str, Any]]:
    givens = {g.get("symbol"): g for g in case.get("task", {}).get("givens", [])}
    factor = _fraction(givens.get("target_reduction_factor"))
    if factor is None or factor <= 1:
        return [_outcome(c["id"], "error", "Invalid target reduction factor in case givens.", failure_class="case_data") for c in case["scoring"]["criteria"]]
    claimed_product_ratio = 1 / factor**2
    q1, q2, q3 = (_question(answer, key) for key in ("q1", "q2", "q3"))
    results: list[dict[str, Any]] = []

    if q1 is _MISSING:
        results.append(_missing("c_impossible", "answers.q1"))
    else:
        feasible = q1 if isinstance(q1, bool) else q1.get("achievable", _MISSING) if isinstance(q1, dict) else _MISSING
        if feasible is _MISSING:
            results.append(_outcome("c_impossible", "unresolved", "Feasibility is not expressed as a typed boolean.", failure_class="unsupported_answer_shape"))
        elif feasible is True:
            results.append(_outcome("c_impossible", "fail", "A tenfold decrease in both quantities implies a 100-fold lower product for the same beam.", failure_class="physical_contradiction", claimed_product_ratio=claimed_product_ratio))
        elif feasible is False:
            results.append(_outcome("c_impossible", "pass", "The proposed product ratio is below the passive lossless bound.", claimed_product_ratio=claimed_product_ratio, minimum_product_ratio=1.0))
        else:
            results.append(_outcome("c_impossible", "unresolved", "Feasibility value is neither true nor false.", failure_class="unsupported_answer_shape"))

    if q2 is _MISSING:
        results.append(_missing("c_invariant", "answers.q2"))
    elif not isinstance(q2, dict):
        results.append(_outcome("c_invariant", "unresolved", "The invariant is given outside the structured fields.", failure_class="unsupported_answer_shape"))
    else:
        invariant = _name(q2.get("invariant"))
        behavior = _name(q2.get("behavior"))
        invariant_families = {
            "beam_parameter_product": {"conserved", "cannot_decrease", "nondecreasing"},
            "bpp": {"conserved", "cannot_decrease", "nondecreasing"},
            "etendue": {"conserved", "cannot_decrease", "nondecreasing"},
            "brightness": {"conserved", "cannot_increase", "nonincreasing"},
            "radiance": {"conserved", "cannot_increase", "nonincreasing"},
        }
        clearly_wrong = {"decreases", "can_decrease", "improves", "can_increase_without_loss", "both_decrease"}
        if invariant is None or behavior is None:
            results.append(_missing("c_invariant", "answers.q2.invariant/behavior"))
        elif behavior in clearly_wrong:
            results.append(_outcome("c_invariant", "fail", "The declared behavior violates the passive optical invariant.", failure_class="physical_contradiction"))
        elif invariant not in invariant_families or behavior not in invariant_families[invariant]:
            results.append(_outcome("c_invariant", "unresolved", "The invariant or behavior uses an unrecognized but potentially valid formulation.", failure_class="unsupported_alternative", invariant=invariant, behavior=behavior))
        elif q2.get("same_beam") is False:
            results.append(_outcome("c_invariant", "fail", "The claimed constraint is applied to a different beam, outside the stated scenario.", failure_class="scope_mismatch"))
        elif "same_beam" in q2 and q2["same_beam"] is not True:
            results.append(_outcome("c_invariant", "fail", "same_beam must be a Boolean claim about the beam in the task.", failure_class="malformed_claim"))
        else:
            results.append(_outcome("c_invariant", "pass", "The named invariant prevents the implied 0.01 product ratio under the case assumptions.", invariant=invariant, behavior=behavior, claimed_product_ratio=claimed_product_ratio))

    if q3 is _MISSING:
        results.append(_missing("c_tradeoff", "answers.q3"))
    elif not isinstance(q3, dict):
        results.append(_outcome("c_tradeoff", "unresolved", "Tradeoff is not expressed as two structured directions.", failure_class="unsupported_answer_shape"))
    else:
        size = _name(q3.get("reduce_size"))
        divergence = _name(q3.get("reduce_divergence"))
        if size is None or divergence is None:
            results.append(_missing("c_tradeoff", "answers.q3.reduce_size/reduce_divergence"))
        elif size in {"divergence_decreases", "divergence_unchanged", "both_decrease"} or divergence in {"size_decreases", "size_unchanged", "both_decrease"}:
            results.append(_outcome("c_tradeoff", "fail", "The proposed direction does not increase the conjugate size or divergence enough to preserve the same-beam product.", failure_class="physical_contradiction"))
        elif size in {"divergence_increases", "larger_divergence"} and divergence in {"size_increases", "larger_size"}:
            results.append(_outcome("c_tradeoff", "pass", "Reciprocal size and far-field divergence changes preserve the beam-parameter constraint."))
        else:
            results.append(_outcome("c_tradeoff", "unresolved", "The declared tradeoff uses an unrecognized formulation.", failure_class="unsupported_alternative", reduce_size=size, reduce_divergence=divergence))
    return results


def _absorption(case: dict[str, Any], answer: dict[str, Any]) -> list[dict[str, Any]]:
    q1, q2, q3 = (_question(answer, key) for key in ("q1", "q2", "q3"))
    target = next((_fraction(g) for g in case.get("task", {}).get("givens", []) if g.get("symbol") == "relative_transmission_change"), None)
    if target is None or target <= 0:
        return [_outcome(c["id"], "error", "Invalid target transmission change in case givens.", failure_class="case_data") for c in case["scoring"]["criteria"]]
    results: list[dict[str, Any]] = []
    if q1 is _MISSING:
        results.append(_missing("c_channels", "answers.q1"))
    elif not isinstance(q1, dict):
        results.append(_outcome("c_channels", "unresolved", "Measurement chain is not a structured channel graph.", failure_class="unsupported_answer_shape"))
    else:
        sample = q1.get("sample")
        reference = q1.get("reference")
        core = (
            isinstance(sample, dict) and sample.get("contains_sample") is True
            and isinstance(reference, dict) and reference.get("contains_sample") is False
            and q1.get("shared_source") is True
        )
        if sample is None or reference is None or "shared_source" not in q1:
            results.append(_missing("c_channels", "answers.q1.sample/reference/shared_source"))
        elif not core:
            results.append(_outcome("c_channels", "fail", "Sample and reference must observe comparable paths from one source, with sample only in the sample arm.", failure_class="invalid_channel_graph"))
        else:
            timing = _name(q1.get("timing"))
            comparison = _name(q1.get("comparison"))
            sample_observes = _name(sample.get("observes"))
            reference_observes = _name(reference.get("observes"))
            if timing is None or comparison is None or sample_observes is None or reference_observes is None:
                results.append(_missing("c_channels", "answers.q1.sample/reference.observes/timing/comparison"))
            elif sample_observes not in {"transmitted_intensity", "transmitted_power"} or reference_observes not in {"incident_intensity", "source_power"}:
                results.append(_outcome("c_channels", "unresolved", "Declared channel observables do not establish a comparable transmission measurement.", failure_class="unsupported_alternative", sample_observes=sample_observes, reference_observes=reference_observes))
            elif timing not in {"simultaneous", "synchronized"}:
                results.append(_outcome("c_channels", "unresolved", "Timing alternative cannot be certified without a drift time scale.", failure_class="unsupported_alternative", timing=timing))
            elif comparison not in {"calibrated_ratio", "calibrated_balanced_difference"}:
                results.append(_outcome("c_channels", "unresolved", "Comparison method needs a topology-neutral physical model to certify.", failure_class="unsupported_alternative", comparison=comparison))
            elif q1.get("gain_calibrated") is not True or q1.get("baseline_calibrated") is not True:
                results.append(_outcome("c_channels", "fail", "Channel gain and baseline must be calibrated before a 1e-5 comparison.", failure_class="missing_calibration"))
            elif comparison == "calibrated_balanced_difference" and q1.get("reference_normalized") is not True:
                results.append(_outcome("c_channels", "fail", "A balanced difference needs reference scaling to report a fractional transmission change.", failure_class="missing_fractional_normalization"))
            elif q1.get("sample_response_retained") is not True:
                results.append(_outcome("c_channels", "fail", "The comparison must retain sensitivity to the sample transmission change.", failure_class="missing_sample_sensitivity"))
            else:
                resolution = q1.get("resolution")
                if not isinstance(resolution, dict):
                    results.append(_outcome("c_channels", "unresolved", "Two-channel topology is coherent, but a 1e-5 sensitivity plan is missing.", failure_class="missing_resolution_evidence"))
                else:
                    noise = _fraction(resolution.get("noise_floor_fraction"))
                    systematic = _fraction(resolution.get("systematic_floor_fraction"))
                    verification = _name(resolution.get("verification"))
                    if noise is None or systematic is None or verification is None or "linear_unsaturated" not in resolution:
                        results.append(_missing("c_channels", "answers.q1.resolution"))
                    elif noise < 0 or systematic < 0 or resolution["linear_unsaturated"] is not True:
                        results.append(_outcome("c_channels", "fail", "Declared detector operating point or uncertainty budget is invalid.", failure_class="dynamic_range"))
                    elif noise + systematic >= target or math.isclose(noise + systematic, target, rel_tol=1e-12, abs_tol=0):
                        results.append(_outcome("c_channels", "fail", "The declared noise plus systematic floor does not resolve the 1e-5 signal.", failure_class="dynamic_range", declared_floor=noise + systematic, target=target))
                    elif verification not in {"blank_and_known_step", "calibrated_attenuation", "injected_reference_change"}:
                        results.append(_outcome("c_channels", "unresolved", "Sensitivity verification method is not among the tested families.", failure_class="unsupported_alternative", verification=verification))
                    else:
                        results.append(_outcome("c_channels", "pass", "Shared-source sample and reference channels are synchronously compared with calibration and a declared sub-target uncertainty plan.", architecture=comparison, declared_floor=noise + systematic, target=target))

    if q2 is _MISSING:
        results.append(_missing("c_normalize", "answers.q2"))
    elif not isinstance(q2, dict):
        results.append(_outcome("c_normalize", "unresolved", "Normalization mechanism is not structured.", failure_class="unsupported_answer_shape"))
    else:
        tracks = _name(q2.get("tracks"))
        mechanism = _name(q2.get("mechanism"))
        if tracks is None or mechanism is None or "sample_response_retained" not in q2:
            results.append(_missing("c_normalize", "answers.q2.tracks/mechanism/sample_response_retained"))
        elif tracks in {"independent_source_power", "unrelated_reference_power", "sample_transmission", "sample_transmission_only"}:
            results.append(_outcome("c_normalize", "fail", "Reference normalization must track the same source-intensity variation.", failure_class="wrong_reference"))
        elif tracks not in {"common_source_power", "common_laser_intensity"}:
            results.append(_outcome("c_normalize", "unresolved", "The reference observable might track common source intensity but is outside the tested typed vocabulary.", failure_class="unsupported_alternative", tracks=tracks))
        elif mechanism in {"cancels_all_noise", "eliminates_every_error"} or q2["sample_response_retained"] is False:
            results.append(_outcome("c_normalize", "fail", "Normalization cannot remove all errors or the sample response itself.", failure_class="physical_contradiction"))
        elif q2["sample_response_retained"] is not True:
            results.append(_outcome("c_normalize", "fail", "sample_response_retained must be a Boolean claim.", failure_class="malformed_claim"))
        elif mechanism == "matched_gain_common_mode_rejection" and q2.get("reference_normalized") is not True:
            results.append(_outcome("c_normalize", "fail", "Matched subtraction alone does not define a fractional transmission estimate without reference scaling.", failure_class="missing_fractional_normalization"))
        elif mechanism in {"multiplicative_ratio_cancellation", "matched_gain_common_mode_rejection"}:
            results.append(_outcome("c_normalize", "pass", "The stated comparison suppresses shared source-power drift while retaining sample sensitivity.", mechanism=mechanism))
        else:
            results.append(_outcome("c_normalize", "unresolved", "The proposed normalization mechanism is not among tested families.", failure_class="unsupported_alternative", mechanism=mechanism))

    if q3 is _MISSING:
        results.append(_missing("c_residuals", "answers.q3"))
    else:
        residuals = q3 if isinstance(q3, list) else q3.get("residuals") if isinstance(q3, dict) else None
        if residuals is None:
            results.append(_missing("c_residuals", "answers.q3.residuals"))
        elif not isinstance(residuals, list):
            results.append(_outcome("c_residuals", "unresolved", "Residual errors are not an array of typed causes.", failure_class="unsupported_answer_shape"))
        else:
            known = {
                "detector_drift", "gain_mismatch", "path_mismatch", "sample_scattering_change",
                "detector_nonlinearity", "channel_specific_noise", "shot_noise", "electronic_noise",
                "polarization_mismatch", "wavelength_drift", "background_light",
            }
            names = {_name(item) for item in residuals}
            if "all_errors_cancel" in names or "no_residual_errors" in names:
                results.append(_outcome("c_residuals", "fail", "A two-channel ratio cannot cancel every independent error.", failure_class="physical_contradiction"))
            elif len(names & known) >= 2:
                results.append(_outcome("c_residuals", "pass", "At least two distinct non-common residual mechanisms are identified.", recognized=sorted(names & known)))
            elif not residuals:
                results.append(_outcome("c_residuals", "fail", "No residual error mechanisms were identified.", failure_class="missing_claim"))
            else:
                results.append(_outcome("c_residuals", "unresolved", "Residual mechanisms require review or a broader typed vocabulary.", failure_class="unsupported_alternative", supplied=sorted(str(x) for x in residuals)))
    return results


def evaluate(case: dict[str, Any], answer: dict[str, Any]) -> list[dict[str, Any]]:
    """Return per-criterion verdicts for supported conceptual cases only."""
    if not isinstance(answer, dict):
        return [_outcome(c["id"], "fail", "Answer is not a JSON object.", failure_class="invalid_contract") for c in case["scoring"]["criteria"]]
    case_id = case.get("case_id")
    if case_id == "SEED-2-8":
        return _beam_product(case, answer)
    if case_id == "SEED-5-3":
        return _absorption(case, answer)
    return []
