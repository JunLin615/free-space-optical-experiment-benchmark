"""Conservative structured diagnostic scorer for SEED-7-2.

The supported answer shape is documented in that case's ``answer_contract``.
This is a bounded proof of concept: unknown credible causal mechanisms or test
methods are unresolved, never silently rejected as physically impossible.
The case remains ``specified`` until response calibration is substantially
broader than these fixtures.
"""

from __future__ import annotations

from typing import Any


PROCESSES = {
    "aperture_clipping": "hard_edge_truncation",
    "pinhole_clipping": "spatial_filter_truncation",
    "surface_defect": "scatter_from_defect",
    "aberration": "wavefront_phase_error",
    "misalignment": "beam_optic_axis_mismatch",
    "input_mode": "upstream_spatial_structure",
}

COMPONENTS = {
    "aperture_clipping": {"lens_clear_aperture", "mechanical_stop"},
    "pinhole_clipping": {"filter_pinhole"},
    "surface_defect": {"lens_surface", "coating"},
    "aberration": {"lens"},
    "misalignment": {"lens_mount", "optical_axis"},
    "input_mode": {"input_beam"},
}

CAUSE_PREDICTIONS = {
    "aperture_clipping": {
        ("inspect_near_field", "edge_truncation"),
        ("change_aperture", "rings_weaken"),
    },
    "pinhole_clipping": {
        ("remove_or_enlarge_pinhole", "rings_weaken"),
    },
    "surface_defect": {
        ("inspect_surface", "defect_visible"),
        ("substitute_optic", "rings_weaken"),
    },
    "aberration": {
        ("measure_wavefront", "wavefront_error"),
        ("substitute_optic", "rings_weaken"),
    },
    "misalignment": {
        ("realign_lenses", "rings_weaken"),
        ("inspect_geometry", "decenter_or_tilt"),
    },
    "input_mode": {
        ("inspect_input_before_expander", "rings_present_upstream"),
        ("substitute_input", "rings_weaken"),
    },
}

APERTURE_CATEGORIES = {"aperture_clipping", "pinhole_clipping"}
APERTURE_EFFECT = "edge_diffraction_or_spatial_filter_truncation"

# Diagnostic operations encode a controlled change or observation and its
# expected contrast. They express a causal test, not a list of buzzwords.
OPERATIONS = {
    "inspect_near_field": ({"aperture_clipping"}, "edge_truncation", "full_profile"),
    "remove_optional_stop": ({"aperture_clipping"}, "rings_weaken", "rings_unchanged"),
    "remove_or_enlarge_pinhole": ({"pinhole_clipping"}, "rings_weaken", "rings_unchanged"),
    "inspect_surface": ({"surface_defect"}, "defect_visible", "surface_clear"),
    "substitute_optic": ({"surface_defect", "aberration"}, "rings_weaken", "rings_unchanged"),
    "measure_wavefront": ({"aberration"}, "wavefront_error", "wavefront_clean"),
    "realign_lenses": ({"misalignment"}, "rings_weaken", "rings_unchanged"),
    "inspect_input_before_expander": ({"input_mode"}, "rings_present_upstream", "rings_absent_upstream"),
}

OBSERVATIONAL = {"inspect_near_field", "inspect_surface", "measure_wavefront", "inspect_input_before_expander"}
INTERVENTIONS = set(OPERATIONS) - OBSERVATIONAL
VALID_CONTROLS = {"fixed_input", "fixed_exposure", "one_change_at_a_time", "before_after"}


def _verdict(check: str, status: str, evidence: str, *, failure_class: str | None = None,
             details: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = {"criterion_id": check, "check_id": check, "status": status,
               "score": 1 if status == "pass" else 0 if status == "fail" else None,
               "evidence": evidence, "details": details or {}}
    if failure_class:
        payload["details"]["failure_class"] = failure_class
    return payload


def _question(answer: dict[str, Any], q: str) -> Any:
    answers = answer.get("answers")
    return answers.get(q) if isinstance(answers, dict) else None


def _substantive(value: Any) -> bool:
    return isinstance(value, str) and len(value.strip()) >= 12 and len(value.split()) >= 2


def _cause_validity(cause: dict[str, Any]) -> str:
    """Return supported, unsupported or inconsistent for a causal claim."""
    category = cause.get("category")
    if category not in PROCESSES:
        return "unsupported"
    if cause.get("physical_process") != PROCESSES[category] or cause.get("component") not in COMPONENTS[category]:
        return "inconsistent"
    prediction = cause.get("prediction")
    pair = (prediction.get("test"), prediction.get("outcome")) if isinstance(prediction, dict) else None
    if pair not in CAUSE_PREDICTIONS[category] or not _substantive(cause.get("explanation")):
        return "inconsistent"
    return "supported"


def _causes(q1: Any) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    """Return structurally usable causes and error details, without scoring."""
    if not isinstance(q1, dict) or not isinstance(q1.get("causes"), list):
        return {}, {"failure_class": "missing_claim", "reason": "answers.q1.causes must be a list"}
    causes: dict[str, dict[str, Any]] = {}
    duplicates: list[str] = []
    malformed: list[int] = []
    for i, cause in enumerate(q1["causes"]):
        if not isinstance(cause, dict) or not isinstance(cause.get("id"), str) or not cause["id"]:
            malformed.append(i)
            continue
        if cause["id"] in causes:
            duplicates.append(cause["id"])
        else:
            causes[cause["id"]] = cause
    return causes, {"duplicate_ids": duplicates, "malformed_indices": malformed}


def _score_causes(q1: Any) -> dict[str, Any]:
    causes, structural = _causes(q1)
    if structural.get("failure_class"):
        return _verdict("c_causes", "fail", structural["reason"], failure_class="missing_claim")
    if structural["duplicate_ids"] or structural["malformed_indices"]:
        return _verdict("c_causes", "fail", "Cause identifiers must be unique and each entry must be an object with an ID.",
                        failure_class="malformed_claim", details=structural)
    valid_categories: set[str] = set()
    unsupported: list[str] = []
    invalid: list[str] = []
    for cid, cause in causes.items():
        category = cause.get("category")
        validity = _cause_validity(cause)
        if validity == "unsupported":
            unsupported.append(cid)
            continue
        if validity == "inconsistent":
            invalid.append(cid)
            continue
        valid_categories.add(category)
    details = {"valid_categories": sorted(valid_categories), "unsupported_ids": unsupported,
               "invalid_ids": invalid, "distinct_count": len(valid_categories)}
    if invalid:
        return _verdict("c_causes", "fail", "Some named causes lack a compatible physical mechanism, component, prediction, or explanation.",
                        failure_class="inconsistent_causal_claim", details=details)
    if len(valid_categories) >= 5:
        return _verdict("c_causes", "pass", f"Five or more distinct physical cause categories are supported ({len(valid_categories)}).", details=details)
    if len(valid_categories) + len(unsupported) >= 5 and unsupported:
        return _verdict("c_causes", "unresolved", "Unlisted causes could satisfy the five-cause requirement but need semantic review or an expanded registry.",
                        failure_class="unsupported_alternative", details=details)
    return _verdict("c_causes", "fail", f"Only {len(valid_categories)} distinct supported cause categories are substantiated.",
                    failure_class="insufficient_distinct_causes", details=details)


def _score_apertures(q1: Any, q2: Any) -> dict[str, Any]:
    if not isinstance(q2, dict) or not isinstance(q2.get("aperture_causes"), list):
        return _verdict("c_apertures", "fail", "answers.q2.aperture_causes is missing.", failure_class="missing_claim")
    causes, _ = _causes(q1)
    listed = q2["aperture_causes"]
    claimed: set[str] = set()
    invalid: list[int] = []
    unsupported: list[int] = []
    for i, item in enumerate(listed):
        if not isinstance(item, dict) or not isinstance(item.get("cause_id"), str):
            invalid.append(i)
            continue
        cid = item["cause_id"]
        if cid not in causes:
            invalid.append(i)
            continue
        validity = _cause_validity(causes[cid])
        if validity == "inconsistent":
            invalid.append(i)
            continue
        if validity == "unsupported":
            unsupported.append(i)
            continue
        category = causes[cid].get("category")
        if category not in APERTURE_CATEGORIES or item.get("aperture_type") != causes[cid].get("component") or item.get("effect") != APERTURE_EFFECT:
            invalid.append(i)
            continue
        claimed.add(cid)
    required = {cid for cid, cause in causes.items() if cause.get("category") in APERTURE_CATEGORIES}
    details = {"required_cause_ids": sorted(required), "classified_cause_ids": sorted(claimed),
               "invalid_indices": invalid, "unsupported_indices": unsupported}
    if invalid:
        return _verdict("c_apertures", "fail", "Aperture classification is inconsistent with a listed cause or its component.",
                        failure_class="incorrect_aperture_classification", details=details)
    if unsupported:
        return _verdict("c_apertures", "unresolved", "An unlisted cause category needs interpretation before aperture classification.",
                        failure_class="unsupported_alternative", details=details)
    if not required:
        return _verdict("c_apertures", "fail", "No aperture-related cause was identified.", failure_class="missing_aperture_cause", details=details)
    if claimed != required:
        return _verdict("c_apertures", "fail", "The aperture-related causes in q1 were not all identified in q2.",
                        failure_class="incomplete_aperture_classification", details=details)
    return _verdict("c_apertures", "pass", "All listed aperture or pinhole causes are classified consistently.", details=details)


def _score_steps(q1: Any, q3: Any) -> dict[str, Any]:
    if not isinstance(q3, dict) or not isinstance(q3.get("steps"), list):
        return _verdict("c_diagnosis", "fail", "answers.q3.steps is missing.", failure_class="missing_claim")
    causes, _ = _causes(q1)
    steps = q3["steps"]
    if not steps:
        return _verdict("c_diagnosis", "fail", "No diagnostic steps were supplied.", failure_class="missing_claim")
    categories_tested: set[str] = set()
    operations_seen: set[str] = set()
    invalid: list[int] = []
    unsupported: list[int] = []
    for i, step in enumerate(steps):
        if not isinstance(step, dict):
            invalid.append(i)
            continue
        operation = step.get("operation")
        if operation not in OPERATIONS:
            unsupported.append(i)
            continue
        expected_categories, positive, negative = OPERATIONS[operation]
        ids = step.get("target_cause_ids")
        controls = step.get("controls")
        if (not isinstance(ids, list) or not ids or not all(isinstance(x, str) and x in causes for x in ids)
                or not isinstance(controls, list) or not set(controls) <= VALID_CONTROLS
                or not controls or step.get("if_present") != positive or step.get("if_absent") != negative
                or not _substantive(step.get("inference"))):
            invalid.append(i)
            continue
        target_categories = {causes[cid].get("category") for cid in ids}
        if any(_cause_validity(causes[cid]) == "inconsistent" for cid in ids):
            invalid.append(i)
            continue
        if any(_cause_validity(causes[cid]) == "unsupported" for cid in ids):
            unsupported.append(i)
            continue
        if not target_categories <= expected_categories:
            invalid.append(i)
            continue
        if operation in INTERVENTIONS and not ({"one_change_at_a_time", "before_after"} & set(controls)):
            invalid.append(i)
            continue
        operations_seen.add(operation)
        categories_tested.update(target_categories)
    details = {"operations": sorted(operations_seen), "categories_tested": sorted(categories_tested),
               "invalid_indices": invalid, "unsupported_indices": unsupported}
    if invalid:
        return _verdict("c_diagnosis", "fail", "A step lacks a controlled, cause-specific test with contrasting outcomes and an inference.",
                        failure_class="non_discriminating_test", details=details)
    if len(operations_seen) < 3 or not categories_tested & APERTURE_CATEGORIES or not categories_tested - APERTURE_CATEGORIES:
        if unsupported and len(operations_seen) + len(unsupported) >= 3:
            return _verdict("c_diagnosis", "unresolved", "An unlisted test method could complete the fault-isolation sequence.",
                            failure_class="unsupported_alternative", details=details)
        return _verdict("c_diagnosis", "fail", "The sequence does not isolate both aperture and non-aperture causes with at least three distinct tests.",
                        failure_class="incomplete_diagnostic_sequence", details=details)
    if not any(isinstance(s, dict) and s.get("operation") in OBSERVATIONAL for s in steps[:2]):
        return _verdict("c_diagnosis", "fail", "The first two steps do not establish an observational baseline before later interventions.",
                        failure_class="poor_test_order", details=details)
    if unsupported:
        return _verdict("c_diagnosis", "unresolved", "The sequence includes an unlisted diagnostic method needing semantic review.",
                        failure_class="unsupported_alternative", details=details)
    return _verdict("c_diagnosis", "pass", "The sequence begins with observation and uses controlled contrasts across aperture and non-aperture causes.", details=details)


def evaluate(case: dict[str, Any], answer: dict[str, Any]) -> list[dict[str, Any]]:
    """Score the three SEED-7-2 criteria without pretending to cover novel methods."""
    if not isinstance(case, dict) or case.get("case_id") != "SEED-7-2":
        return [_verdict(check, "error", "Diagnostic scorer received the wrong case.", failure_class="wrong_case")
                for check in ("c_causes", "c_apertures", "c_diagnosis")]
    if not isinstance(answer, dict):
        return [_verdict(check, "fail", "Structured answer object is missing.", failure_class="missing_claim")
                for check in ("c_causes", "c_apertures", "c_diagnosis")]
    q1, q2, q3 = (_question(answer, f"q{i}") for i in range(1, 4))
    return [_score_causes(q1), _score_apertures(q1, q2), _score_steps(q1, q3)]
