"""Versioned bounded causal scoring for two-aperture alignment (SEED-7-1).

Only typed, physically linked claims are scored. Unknown plausible mechanisms or
diagnostic methods abstain; ordinary missing and contradictory claims fail locally.
This module does not alter the rc1 evaluator or earlier diagnostic scorer.
"""

from __future__ import annotations

from typing import Any


# Each family is a distinct fault process, not a synonym or instrument name.
CAUSES = {
    "iteration_procedure": ("coupled_position_angle_not_iterated", "procedure", {
        ("alternate_near_far", "converges_after_iteration"),
    }),
    "reference_axis_mismatch": ("aperture_centers_off_intended_reference_line", "hardware", {
        ("survey_aperture_centers", "center_off_reference_line"),
    }),
    "steering_reach_limit": ("required_ray_outside_mirror_adjustment_range", "hardware", {
        ("check_mirror_travel", "required_setting_outside_range"),
    }),
    "path_obstruction": ("ray_intercepted_by_intermediate_clear_aperture", "hardware", {
        ("inspect_intermediate_pupils", "beam_truncated"),
    }),
    "mount_drift": ("optical_axis_changes_during_adjustment", "hardware", {
        ("repeat_fixed_setting", "centroid_drifts"),
    }),
    "beam_height_mismatch": ("source_ray_height_incompatible_with_reachable_path", "hardware", {
        ("measure_source_height", "height_outside_reachable_path"),
    }),
}

TESTS = {
    "survey_aperture_centers": ("center_off_reference_line", "centers_on_reference_line", "reference_axis_mismatch"),
    "check_mirror_travel": ("required_setting_outside_range", "required_setting_within_range", "steering_reach_limit"),
    "inspect_intermediate_pupils": ("beam_truncated", "clear_ray_path", "path_obstruction"),
    "repeat_fixed_setting": ("centroid_drifts", "centroid_stable", "mount_drift"),
    "measure_source_height": ("height_outside_reachable_path", "height_compatible", "beam_height_mismatch"),
    "alternate_near_far": ("converges_after_iteration", "does_not_converge", "iteration_procedure"),
}
OBSERVATIONS = set(TESTS) - {"alternate_near_far"}
CONTROLS = {"fixed_source", "fixed_reference", "fixed_apertures", "one_change_at_a_time", "before_after"}


def _result(check: str, status: str, evidence: str, *, failure: str | None = None,
            details: dict[str, Any] | None = None) -> dict[str, Any]:
    out = {"criterion_id": check, "check_id": check, "status": status,
           "score": 1 if status == "pass" else 0 if status == "fail" else None,
           "evidence": evidence, "details": details or {}}
    if failure:
        out["details"]["failure_class"] = failure
    return out


def _answer(answer: dict[str, Any], q: str) -> Any:
    answers = answer.get("answers")
    return answers.get(q) if isinstance(answers, dict) else None


def _causes(value: Any) -> tuple[dict[str, dict[str, Any]], str | None]:
    if not isinstance(value, dict) or not isinstance(value.get("causes"), list):
        return {}, "missing_claim"
    out: dict[str, dict[str, Any]] = {}
    for cause in value["causes"]:
        if (not isinstance(cause, dict) or not isinstance(cause.get("id"), str)
                or not cause["id"] or cause["id"] in out):
            return {}, "malformed_claim"
        out[cause["id"]] = cause
    return out, None


def _validity(cause: dict[str, Any]) -> str:
    family = cause.get("family")
    if not isinstance(family, str) or family not in CAUSES:
        return "unsupported"
    mechanism, fault_class, predictions = CAUSES[family]
    prediction = cause.get("prediction")
    pair = (prediction.get("test"), prediction.get("outcome")) if isinstance(prediction, dict) else None
    if (cause.get("mechanism") != mechanism or cause.get("fault_class") != fault_class
            or not isinstance(pair, tuple) or not all(isinstance(item, str) for item in pair)
            or pair not in predictions):
        return "inconsistent"
    return "supported"


def _q1(causes: dict[str, dict[str, Any]], error: str | None) -> dict[str, Any]:
    if error:
        return _result("c_q1", "fail", "A unique-ID cause array is required.", failure=error)
    supported, unknown, inconsistent = set(), [], []
    for cid, cause in causes.items():
        validity = _validity(cause)
        if validity == "supported":
            supported.add(cause["family"])
        elif validity == "unsupported":
            unknown.append(cid)
        else:
            inconsistent.append(cid)
    details = {"distinct_supported_families": sorted(supported), "unknown_ids": unknown,
               "inconsistent_ids": inconsistent}
    if inconsistent:
        return _result("c_q1", "fail", "Known fault mechanism or predicted test contradicts its family.",
                       failure="inconsistent_causal_claim", details=details)
    if len(supported) >= 4:
        return _result("c_q1", "pass", "At least four distinct supported fault processes have testable predictions.", details=details)
    if unknown and len(supported) + len(unknown) >= 4:
        return _result("c_q1", "unresolved", "Novel fault processes may meet the four-cause requirement.",
                       failure="unsupported_alternative", details=details)
    return _result("c_q1", "fail", "Fewer than four distinct supported fault processes were given.",
                   failure="insufficient_distinct_causes", details=details)


def _q2(value: Any, causes: dict[str, dict[str, Any]], error: str | None) -> dict[str, Any]:
    if not isinstance(value, dict) or not isinstance(value.get("classifications"), list):
        return _result("c_q2", "fail", "Cause classifications are required.", failure="missing_claim")
    if error:
        return _result("c_q2", "unresolved", "Cause IDs cannot be resolved from malformed q1.", failure="dependent_model_missing")
    classified, unknown = set(), []
    for entry in value["classifications"]:
        if not isinstance(entry, dict) or not isinstance(entry.get("cause_id"), str) or entry["cause_id"] not in causes:
            return _result("c_q2", "fail", "A classification has no matching cause ID.", failure="invalid_cause_link")
        cid = entry["cause_id"]
        if cid in classified:
            return _result("c_q2", "fail", "A cause is classified more than once.", failure="duplicate_cause_link")
        classified.add(cid)
        cause = causes[cid]
        validity = _validity(cause)
        if validity == "unsupported":
            unknown.append(cid)
        elif validity == "inconsistent" or entry.get("fault_class") != cause.get("fault_class"):
            return _result("c_q2", "fail", "The procedure/hardware classification contradicts the proposed mechanism.",
                           failure="incorrect_fault_classification")
        elif entry.get("corrective_action") != ("iterate_near_far" if cause["fault_class"] == "procedure" else "correct_physical_limit"):
            return _result("c_q2", "fail", "The remedy does not match the fault class.", failure="incorrect_remedy")
    if classified != set(causes):
        return _result("c_q2", "fail", "Every proposed cause must be classified.", failure="incomplete_classification")
    if unknown:
        return _result("c_q2", "unresolved", "Novel mechanisms need classification review.", failure="unsupported_alternative",
                       details={"unknown_ids": unknown})
    if not {c["fault_class"] for c in causes.values()} >= {"procedure", "hardware"}:
        return _result("c_q2", "fail", "Both a correctable procedure fault and a physical limit must be distinguished.",
                       failure="missing_fault_class")
    return _result("c_q2", "pass", "Procedure and physical limits are linked to different corrective actions.")


def _q3(value: Any, causes: dict[str, dict[str, Any]], error: str | None) -> dict[str, Any]:
    if not isinstance(value, dict) or not isinstance(value.get("steps"), list) or not value["steps"]:
        return _result("c_q3", "fail", "A diagnostic sequence is required.", failure="missing_claim")
    if error:
        return _result("c_q3", "unresolved", "Cause IDs cannot be resolved from malformed q1.", failure="dependent_model_missing")
    seen, unknown = set(), []
    sequence = value["steps"]
    for index, step in enumerate(sequence):
        if not isinstance(step, dict):
            return _result("c_q3", "fail", "Each step must be a typed causal test.", failure="malformed_claim")
        test = step.get("test")
        if not isinstance(test, str):
            return _result("c_q3", "fail", "A test code must be a string.", failure="malformed_claim",
                           details={"step_index": index})
        if test not in TESTS:
            unknown.append(index)
            continue
        present, absent, family = TESTS[test]
        ids = step.get("target_cause_ids")
        controls = step.get("controls")
        conclusions = step.get("conclusions")
        if (not isinstance(ids, list) or not ids or not all(isinstance(cid, str) for cid in ids)
                or len(ids) != len(set(ids)) or any(cid not in causes for cid in ids)
                or not isinstance(controls, list) or not controls
                or not all(isinstance(control, str) for control in controls) or not set(controls) <= CONTROLS
                or step.get("if_present") != present or step.get("if_absent") != absent
                or not isinstance(conclusions, dict)
                or conclusions.get("supports_if_present") != ids
                or conclusions.get("weakens_if_absent") != ids):
            return _result("c_q3", "fail", "A test lacks controlled contrasting outcomes tied to cause IDs.",
                           failure="non_discriminating_test", details={"step_index": index})
        if test == "alternate_near_far" and not ({"one_change_at_a_time", "before_after"} & set(controls)):
            return _result("c_q3", "fail", "Mirror iteration must preserve a controlled comparison.",
                           failure="uncontrolled_intervention", details={"step_index": index})
        for cid in ids:
            if _validity(causes[cid]) == "unsupported":
                unknown.append(index)
            elif _validity(causes[cid]) == "inconsistent" or causes[cid]["family"] != family:
                return _result("c_q3", "fail", "A diagnostic outcome is linked to the wrong cause.",
                               failure="incorrect_cause_conclusion", details={"step_index": index})
        seen.add(test)
    if sequence[0].get("test") not in TESTS:
        return _result("c_q3", "unresolved", "An unfamiliar first step may be a valid observation.",
                       failure="unsupported_alternative", details={"unknown_step_indices": unknown})
    if sequence[0].get("test") not in OBSERVATIONS:
        return _result("c_q3", "fail", "Establish an observational baseline before mirror iteration.",
                       failure="poor_test_order")
    if not ({"survey_aperture_centers"} & seen) or "alternate_near_far" not in seen:
        if unknown:
            return _result("c_q3", "unresolved", "An unfamiliar method may complete geometry and convergence checks.",
                           failure="unsupported_alternative", details={"unknown_step_indices": unknown})
        return _result("c_q3", "fail", "Check reference geometry and then controlled near/far convergence.",
                       failure="incomplete_diagnostic_sequence")
    if not ({"check_mirror_travel", "inspect_intermediate_pupils", "measure_source_height"} & seen):
        if unknown:
            return _result("c_q3", "unresolved", "An unfamiliar method may establish path reachability.",
                           failure="unsupported_alternative", details={"unknown_step_indices": unknown})
        return _result("c_q3", "fail", "Check mirror reach or an equivalent physical ray-path limit.",
                       failure="incomplete_diagnostic_sequence")
    if unknown:
        return _result("c_q3", "unresolved", "An unfamiliar diagnostic method requires review.",
                       failure="unsupported_alternative", details={"unknown_step_indices": unknown})
    return _result("c_q3", "pass", "The sequence checks reference geometry and physical reach before interpreting controlled near/far convergence.")


def evaluate(case: dict[str, Any], answer: dict[str, Any]) -> list[dict[str, Any]]:
    """Score three SEED-7-1 criteria independently."""
    checks = ("c_q1", "c_q2", "c_q3")
    if not isinstance(case, dict) or case.get("case_id") != "SEED-7-1":
        return [_result(check, "error", "Wrong case for this scorer.", failure="wrong_case") for check in checks]
    if not isinstance(answer, dict):
        return [_result(check, "fail", "Structured answer is missing.", failure="missing_claim") for check in checks]
    causes, error = _causes(_answer(answer, "q1"))
    return [_q1(causes, error), _q2(_answer(answer, "q2"), causes, error),
            _q3(_answer(answer, "q3"), causes, error)]
