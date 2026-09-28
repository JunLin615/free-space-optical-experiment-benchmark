"""Conservative diagnostic and functional constraint checks.

The supported answer shape is documented in that case's ``answer_contract``.
These are bounded typed checks. Unknown credible mechanisms, tests, and analyzer
responses remain unresolved; neither scorer interprets free-form prose.
"""

from __future__ import annotations

import math
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
TRANSFER_TOLERANCE = 1e-6  # Rounding allowance for an ideal first-order cancellation claim.


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
        interpretation = step.get("interpretation")
        valid_ids = isinstance(ids, list) and bool(ids) and all(isinstance(x, str) and x in causes for x in ids)
        typed_links = (valid_ids and isinstance(interpretation, dict)
                       and all(isinstance(interpretation.get(key), list)
                               and len(interpretation[key]) == len(ids)
                               and all(isinstance(x, str) for x in interpretation[key])
                               and set(interpretation[key]) == set(ids)
                               for key in ("supports_if_present", "weakens_if_absent")))
        if (not valid_ids
                or len(ids) != len(set(ids))
                or not isinstance(controls, list) or not set(controls) <= VALID_CONTROLS
                or not controls or step.get("if_present") != positive or step.get("if_absent") != negative
                or not typed_links):
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


def _fraction(value: Any, unit: str) -> float | None:
    if not isinstance(value, dict) or value.get("unit") not in ({unit, "1/deg"} if unit == "1/rad" else {unit}):
        return None
    number = value.get("value")
    if isinstance(number, bool) or not isinstance(number, (int, float)):
        return None
    number = float(number)
    if not math.isfinite(number):
        return None
    return number * 180 / math.pi if unit == "1/rad" and value["unit"] == "1/deg" else number


def _balanced_polarization(answer: dict[str, Any]) -> list[dict[str, Any]]:
    """Check a declared two-channel response model, independent of analyzer topology.

    Fractions and slopes refer to ideal complementary analyzer outputs divided by
    incident power at the analyzer, before downstream path loss and electrical gain.
    An arbitrary slope sign is allowed because analyzer-axis labels are arbitrary.
    This bounded contract does not infer Jones behavior from unstructured prose.
    """
    q1, q2, q3 = (_question(answer, f"q{i}") for i in range(1, 4))
    results: list[dict[str, Any]] = []
    model: tuple[float, float, float, float, float, float] | None = None
    if not isinstance(q1, dict):
        results.append(_verdict("c_layout", "fail", "A two-channel analyzer model is missing.", failure_class="missing_claim"))
    else:
        channels = q1.get("channels")
        if not isinstance(channels, list) or len(channels) != 2 or any(not isinstance(c, dict) for c in channels):
            results.append(_verdict("c_layout", "fail", "Exactly two detected analyzer channels are required.", failure_class="invalid_channel_graph"))
        else:
            fractions = [_fraction(c.get("bias_power_fraction"), "1") for c in channels]
            slopes = [_fraction(c.get("rotation_slope_per_rad"), "1/rad") for c in channels]
            gains = [_fraction(c.get("effective_gain"), "1") for c in channels]
            if (any(c.get("detected") is not True or c.get("linear_unsaturated") is not True for c in channels)
                    or None in (*fractions, *slopes, *gains)):
                results.append(_verdict("c_layout", "fail", "Detected channel fractions, rotation slopes, and gains must be finite numerical claims.", failure_class="malformed_claim"))
            else:
                f1, f2 = fractions
                s1, s2 = slopes
                g1, g2 = gains
                model = f1, f2, s1, s2, g1, g2
                baseline_difference = g1 * f1 - g2 * f2
                rotation_slope = g1 * s1 - g2 * s2
                if (not 0 <= f1 <= 1 or not 0 <= f2 <= 1 or g1 <= 0 or g2 <= 0
                        or not math.isclose(f1 + f2, 1, rel_tol=0, abs_tol=TRANSFER_TOLERANCE)
                        or not math.isclose(s1 + s2, 0, rel_tol=0, abs_tol=TRANSFER_TOLERANCE)
                        or abs(s1) < 0.1 or abs(s2) < 0.1):
                    results.append(_verdict("c_layout", "fail", "Channel fractions or slopes do not form complementary, rotation-sensitive outputs.", failure_class="non_complementary_channels"))
                elif (2 * f1 - 1) ** 2 + s1 ** 2 > 1 + TRANSFER_TOLERANCE:
                    results.append(_verdict("c_layout", "fail", "The declared direct polarization-analyzer slope exceeds the Stokes/Malus bound at its bias power.", failure_class="unphysical_transfer"))
                elif (abs(baseline_difference) > TRANSFER_TOLERANCE * max(g1 * f1, g2 * f2)
                      or abs(rotation_slope) < 0.1 * max(g1, g2)):
                    results.append(_verdict("c_layout", "fail", "The analyzer is not balanced at a rotation-sensitive operating point.", failure_class="unbalanced_operating_point"))
                elif q1.get("analyzer_function") == "intensity_split_only":
                    results.append(_verdict("c_layout", "fail", "A nonpolarizing power splitter alone has no complementary polarization-rotation response.", failure_class="wrong_analyzer_function"))
                elif q1.get("analyzer_function") is None or q1.get("operating_point") is None:
                    results.append(_verdict("c_layout", "fail", "The polarization-selective analyzer function and input operating point must be identified.", failure_class="missing_claim"))
                elif q1.get("operating_point") == "equal_power" and abs(f1 - f2) > TRANSFER_TOLERANCE:
                    results.append(_verdict("c_layout", "fail", "The claimed equal-power bias disagrees with the submitted channel powers.", failure_class="inconsistent_operating_point"))
                elif (q1["analyzer_function"] not in {"orthogonal_linear_components", "complementary_polarization_components"}
                      or q1["operating_point"] not in {"equal_power", "balanced_difference"}):
                    results.append(_verdict("c_layout", "unresolved", "The analyzer function or operating-point label is unfamiliar; the transfer claim alone cannot certify its optical realization.", failure_class="unsupported_alternative"))
                else:
                    results.append(_verdict("c_layout", "pass", "Two complementary detected channels have a balanced difference and opposite nonzero rotation slopes.", details={"baseline_difference": baseline_difference, "rotation_slope_per_rad": rotation_slope}))
    if not isinstance(q2, dict):
        results.append(_verdict("c_response", "fail", "The differential rotation and power response is missing.", failure_class="missing_claim"))
    elif isinstance(q1, dict) and q1.get("analyzer_function") == "intensity_split_only":
        results.append(_verdict("c_response", "fail", "A nonpolarizing intensity split cannot by itself generate the claimed rotation signal.", failure_class="wrong_analyzer_function"))
    elif isinstance(q1, dict) and q1.get("analyzer_function") not in {"orthogonal_linear_components", "complementary_polarization_components"}:
        results.append(_verdict("c_response", "unresolved", "The unfamiliar analyzer function cannot be tied to the claimed rotation transfer without further physical specification.", failure_class="unsupported_alternative"))
    elif model is None:
        results.append(_verdict("c_response", "unresolved", "Response cannot be checked without finite two-channel transfer data.", failure_class="dependent_model_missing"))
    else:
        f1, f2, s1, s2, g1, g2 = model
        baseline_difference = g1 * f1 - g2 * f2
        rotation_slope = g1 * s1 - g2 * s2
        if q2.get("rotation_response") in {"zero", "quadratic_only"} or q2.get("common_mode_at_bias") in {"uncancelled", "all_noise_cancelled"}:
            results.append(_verdict("c_response", "fail", "The claimed differential response does not state a linear rotation signal with first-order power-noise rejection at bias.", failure_class="incorrect_response"))
        elif q2.get("rotation_response") != "nonzero_linear" or q2.get("common_mode_at_bias") != "first_order_cancelled":
            results.append(_verdict("c_response", "unresolved", "The response uses a typed formulation not covered by this bounded scorer.", failure_class="unsupported_alternative"))
        elif (not 0 <= f1 <= 1 or not 0 <= f2 <= 1 or g1 <= 0 or g2 <= 0
              or not math.isclose(f1 + f2, 1, rel_tol=0, abs_tol=TRANSFER_TOLERANCE)
              or not math.isclose(s1 + s2, 0, rel_tol=0, abs_tol=TRANSFER_TOLERANCE)
              or (2 * f1 - 1) ** 2 + s1 ** 2 > 1 + TRANSFER_TOLERANCE
              or abs(baseline_difference) > TRANSFER_TOLERANCE * max(g1 * f1, g2 * f2)
              or abs(rotation_slope) < 0.1 * max(g1, g2)):
            results.append(_verdict("c_response", "fail", "The claimed first-order behavior contradicts the submitted channel transfer model.", failure_class="physical_contradiction"))
        else:
            results.append(_verdict("c_response", "pass", "The weighted difference has zero bias offset and nonzero first-order rotation slope; common input-power changes cancel at that operating point.", details={"baseline_difference": baseline_difference, "rotation_slope_per_rad": rotation_slope}))
    if not isinstance(q3, dict):
        results.append(_verdict("c_balance", "fail", "Imbalance source and measurement check are missing.", failure_class="missing_claim"))
    else:
        sources = q3.get("imbalance_sources")
        effect = q3.get("effect")
        checks = q3.get("balance_checks")
        known_sources = {"unequal_path_loss", "detector_responsivity_mismatch", "electronic_gain_mismatch", "polarization_leakage"}
        known_checks = {"zero_rotation_offset", "source_power_modulation_leakage"}
        if not isinstance(sources, list) or not isinstance(checks, list) or not sources or not checks:
            results.append(_verdict("c_balance", "fail", "Name an imbalance source and an observable balance check.", failure_class="missing_claim"))
        elif effect in {"all_power_noise_cancelled", "no_effect"}:
            results.append(_verdict("c_balance", "fail", "Imbalance leaks common optical-power fluctuations into a raw difference.", failure_class="physical_contradiction"))
        elif effect != "common_mode_leakage":
            results.append(_verdict("c_balance", "unresolved", "The submitted imbalance effect requires an unsupported interpretation.", failure_class="unsupported_alternative"))
        elif not all(isinstance(item, str) for item in sources + checks):
            results.append(_verdict("c_balance", "unresolved", "Imbalance sources and checks need recognizable typed labels.", failure_class="unsupported_answer_shape"))
        elif not set(sources) <= known_sources or not set(checks) <= known_checks:
            results.append(_verdict("c_balance", "unresolved", "An unfamiliar but possibly valid imbalance source or test needs a broader typed contract.", failure_class="unsupported_alternative"))
        else:
            results.append(_verdict("c_balance", "pass", "Specified path, detector, or electronic imbalance creates common-mode leakage and is tested at the equal-power bias."))
    return results


def evaluate(case: dict[str, Any], answer: dict[str, Any]) -> list[dict[str, Any]]:
    """Score supported diagnostic and polarization-design contracts."""
    case_id = case.get("case_id") if isinstance(case, dict) else None
    checks = ("c_causes", "c_apertures", "c_diagnosis") if case_id != "SEED-4-8" else ("c_layout", "c_response", "c_balance")
    if case_id not in {"SEED-7-2", "SEED-4-8"}:
        return [_verdict(check, "error", "Diagnostic scorer received the wrong case.", failure_class="wrong_case") for check in checks]
    if not isinstance(answer, dict):
        return [_verdict(check, "fail", "Structured answer object is missing.", failure_class="missing_claim") for check in checks]
    if case_id == "SEED-4-8":
        return _balanced_polarization(answer)
    q1, q2, q3 = (_question(answer, f"q{i}") for i in range(1, 4))
    return [_score_causes(q1), _score_apertures(q1, q2), _score_steps(q1, q3)]
