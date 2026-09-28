"""Bounded development checks for absorption design, noise diagnosis, and BPP.

Typed claims are checked against observables and physical limits. An unfamiliar
but noncontradictory method abstains. This scorer is not part of either rc1.
"""

from __future__ import annotations

import math
from typing import Any

from tools.scorers.structured import evaluate as evaluate_bpp_base


MISSING = object()
SCORE = {"pass": 1, "fail": 0, "unresolved": None, "error": None}


def verdict(criterion: str, status: str, evidence: str, failure_class: str | None = None) -> dict[str, Any]:
    details = {"failure_class": failure_class} if failure_class else {}
    return {"criterion_id": criterion, "check_id": criterion, "status": status,
            "score": SCORE[status], "evidence": evidence, "details": details}


def field(value: Any, key: str) -> Any:
    return value.get(key, MISSING) if isinstance(value, dict) else MISSING


def question(answer: dict[str, Any], qid: str) -> Any:
    return field(field(answer, "answers"), qid)


def name(value: Any) -> str | None:
    return value.strip().lower().replace("-", "_").replace(" ", "_") if isinstance(value, str) else None


def finite(value: Any, unit: str) -> float | None:
    factors = {
        "1": {"1": 1.0, "%": 0.01, "percent": 0.01},
        "s": {"s": 1.0, "ms": 0.001, "min": 60.0},
        "mA": {"mA": 1.0, "A": 1000.0, "uA": 0.001, "µA": 0.001},
    }
    if not isinstance(value, dict) or value.get("unit") not in factors[unit]:
        return None
    number = value.get("value")
    if isinstance(number, bool) or not isinstance(number, (int, float)):
        return None
    result = float(number) * factors[unit][value["unit"]]
    return result if math.isfinite(result) else None


def missing(criterion: str, path: str) -> dict[str, Any]:
    return verdict(criterion, "fail", f"Missing required claim at {path}.", "missing_claim")


def unknown(criterion: str, path: str) -> dict[str, Any]:
    return verdict(criterion, "unresolved", f"Unrecognized plausible claim at {path}.", "unsupported_alternative")


ARCHITECTURES = {
    "simultaneous_reference": ("sample_reference_ratio", "simultaneous_reference"),
    "sample_state_modulation": ("modulated_transmission", "sample_state_modulation"),
    "active_source_stabilization": ("sequential_transmission", "active_source_stabilization"),
}


def _design(answer: dict[str, Any]) -> list[dict[str, Any]]:
    q1, q2, q3, q4, q5 = (question(answer, f"q{i}") for i in range(1, 6))
    out: list[dict[str, Any]] = []
    if q1 is MISSING:
        out.append(missing("c_q1", "answers.q1"))
    elif not isinstance(q1, dict):
        out.append(unknown("c_q1", "answers.q1"))
    else:
        family = name(field(q1, "family"))
        observable = name(field(q1, "observable"))
        path = field(q1, "free_space_sample_path")
        linear = field(q1, "linear_detector")
        if MISSING in (field(q1, "family"), field(q1, "observable"), path, linear):
            out.append(missing("c_q1", "answers.q1.family/observable/free_space_sample_path/linear_detector"))
        elif path is False or linear is False or observable in {"source_power_only", "unreferenced_raw_power"}:
            out.append(verdict("c_q1", "fail", "The stated path or observable cannot resolve calibrated sample transmission.", "physical_contradiction"))
        elif path is not True or linear is not True:
            out.append(unknown("c_q1", "answers.q1"))
        elif family in ARCHITECTURES and observable in {entry[0] for entry in ARCHITECTURES.values()} and observable != ARCHITECTURES[family][0]:
            out.append(verdict("c_q1", "fail", "The declared observable does not follow from the named measurement function.", "physical_contradiction"))
        elif family not in ARCHITECTURES or observable != ARCHITECTURES[family][0]:
            out.append(unknown("c_q1", "answers.q1.family/observable"))
        else:
            out.append(verdict("c_q1", "pass", "A free-space sample path and linear detector yield a transmission observable."))
    if q2 is MISSING:
        out.append(missing("c_q2", "answers.q2"))
    elif not isinstance(q2, dict):
        out.append(unknown("c_q2", "answers.q2"))
    else:
        method = name(field(q2, "method"))
        matched = field(q2, "drift_control_tracks_source_variation")
        drift = finite(field(q2, "drift_timescale_s"), "s")
        cycle = finite(field(q2, "cycle_timescale_s"), "s")
        monitor = field(q2, "out_of_loop_monitor")
        if MISSING in (field(q2, "method"), matched, field(q2, "drift_timescale_s"), field(q2, "cycle_timescale_s"), monitor):
            out.append(missing("c_q2", "answers.q2 drift-control fields"))
        elif drift is None or cycle is None or drift <= 0 or cycle <= 0:
            out.append(verdict("c_q2", "fail", "Drift and comparison times must be positive finite values.", "malformed_claim"))
        elif matched is False or cycle >= drift or (method == "active_source_stabilization" and monitor is False):
            out.append(verdict("c_q2", "fail", "The proposed comparison does not track source drift on its time scale.", "physical_contradiction"))
        elif matched is not True or monitor not in (True, False):
            out.append(unknown("c_q2", "answers.q2"))
        elif method not in {v[1] for v in ARCHITECTURES.values()}:
            out.append(unknown("c_q2", "answers.q2.method"))
        elif isinstance(q1, dict) and name(field(q1, "family")) in ARCHITECTURES and method != ARCHITECTURES[name(q1["family"])][1]:
            out.append(verdict("c_q2", "fail", "The drift control does not match the claimed measurement architecture.", "physical_contradiction"))
        else:
            out.append(verdict("c_q2", "pass", "The reference or control resolves the drift faster than its characteristic time."))
    if q3 is MISSING:
        out.append(missing("c_q3", "answers.q3"))
    elif not isinstance(q3, dict):
        out.append(unknown("c_q3", "answers.q3"))
    else:
        incoming = finite(field(q3, "unattenuated_current_ma"), "mA")
        transmission = finite(field(q3, "attenuation_fraction"), "1")
        limit = finite(field(q3, "linear_limit_ma"), "mA")
        floor = finite(field(q3, "measured_fractional_noise_floor"), "1")
        if any(field(q3, key) is MISSING for key in ("unattenuated_current_ma", "attenuation_fraction", "linear_limit_ma", "measured_fractional_noise_floor")):
            out.append(missing("c_q3", "answers.q3 current, attenuation, limit, or noise floor"))
        elif None in (incoming, transmission, limit, floor) or incoming <= 0 or limit <= 0 or not 0 < transmission <= 1 or floor < 0:
            out.append(verdict("c_q3", "fail", "The numeric linearity or sensitivity claim is malformed.", "malformed_claim"))
        elif incoming * transmission >= limit or floor >= 1e-4:
            out.append(verdict("c_q3", "fail", "Attenuated current is outside the declared linear range or measured floor cannot resolve 10^-4.", "physical_contradiction"))
        else:
            out.append(verdict("c_q3", "pass", "The declared current is below the linear limit and the measured floor is below 10^-4."))
    if q4 is MISSING:
        out.append(missing("c_q4", "answers.q4"))
    elif not isinstance(q4, dict):
        out.append(unknown("c_q4", "answers.q4"))
    else:
        checks = ("blank", "dark", "linearity", "known_attenuation")
        if any(field(q4, k) is MISSING for k in checks):
            out.append(missing("c_q4", "answers.q4 blank/dark/linearity/known_attenuation"))
        elif any(field(q4, k) is False for k in checks):
            out.append(verdict("c_q4", "fail", "A required baseline or calibration check is explicitly omitted.", "missing_control"))
        elif all(field(q4, k) is True for k in checks):
            out.append(verdict("c_q4", "pass", "Blank, dark, linearity, and known-attenuation checks are specified."))
        else:
            out.append(unknown("c_q4", "answers.q4"))
    if q5 is MISSING:
        out.append(missing("c_q5", "answers.q5"))
    elif not isinstance(q5, list):
        out.append(unknown("c_q5", "answers.q5"))
    elif len(q5) < 3:
        out.append(verdict("c_q5", "fail", "Fewer than three designs are supplied.", "missing_claim"))
    else:
        known: set[str] = set()
        unresolved = False
        invalid = False
        for design in q5:
            family = name(field(design, "family"))
            observable = name(field(design, "observable"))
            drift_method = name(field(design, "drift_method"))
            # A balanced difference and a ratio on the same split-beam path are one family.
            if family == "balanced_split_beam":
                family = "simultaneous_reference"
            if field(design, "has_observable") is False or field(design, "has_drift_control") is False or field(design, "has_linearity_calibration") is False:
                invalid = True
            elif family in ARCHITECTURES and observable in {v[0] for v in ARCHITECTURES.values()} and observable != ARCHITECTURES[family][0]:
                invalid = True
            elif family in ARCHITECTURES and drift_method in {v[1] for v in ARCHITECTURES.values()} and drift_method != ARCHITECTURES[family][1]:
                invalid = True
            elif family in ARCHITECTURES and (observable, drift_method) == ARCHITECTURES[family] and all(field(design, k) is True for k in ("has_observable", "has_drift_control", "has_linearity_calibration")):
                known.add(family)
            else:
                unresolved = True
        if invalid:
            out.append(verdict("c_q5", "fail", "At least one proposed design lacks an observable, drift control, or linearity calibration.", "physical_contradiction"))
        elif len(known) >= 3:
            out.append(verdict("c_q5", "pass", "Three distinct physical measurement and drift-control families are complete."))
        elif unresolved:
            out.append(unknown("c_q5", "answers.q5 family or functional evidence"))
        else:
            out.append(verdict("c_q5", "fail", "Changing split-beam readout arithmetic does not add a third physical architecture.", "duplicate_architecture"))
    return out


PLATEAU = {
    "residual_source_rin": ("constant", "block_sample_compare_reference"),
    "channel_gain_imbalance": ("constant", "rebalance_gain"),
    "detector_nonlinearity": ("flattening_or_growth", "attenuation_linearity_scan"),
    "bandwidth_growth": ("flattening_or_growth", "hold_bandwidth_fixed"),
}


def _noise(answer: dict[str, Any]) -> list[dict[str, Any]]:
    q1, q2, q3 = (question(answer, f"q{i}") for i in range(1, 4))
    out: list[dict[str, Any]] = []
    if q1 is MISSING:
        out.append(missing("c_q1", "answers.q1"))
    elif not isinstance(q1, dict) or not isinstance(field(q1, "hypotheses"), list):
        out.append(unknown("c_q1", "answers.q1.hypotheses"))
    else:
        families: set[str] = set()
        unresolved = False
        invalid = False
        for item in q1["hypotheses"]:
            family = name(field(item, "family"))
            scaling = name(field(item, "fractional_scaling"))
            test = name(field(item, "discriminating_test"))
            if family in {"ideal_shot_noise", "fixed_electronic_noise"} and scaling == "constant":
                invalid = True
            elif family in PLATEAU and (scaling, test) == PLATEAU[family]:
                families.add(family)
            else:
                unresolved = True
        if invalid:
            out.append(verdict("c_q1", "fail", "Ideal shot or fixed electronic noise alone cannot cause a high-power fractional plateau.", "physical_contradiction"))
        elif len(families) >= 2 and not unresolved:
            out.append(verdict("c_q1", "pass", "Distinct plateau mechanisms have matching power trends and discriminating controls."))
        elif unresolved:
            out.append(unknown("c_q1", "answers.q1.hypotheses"))
        else:
            out.append(verdict("c_q1", "fail", "Synonyms or one fault mechanism do not supply distinct diagnoses.", "insufficient_distinct_causes"))
    if q2 is MISSING:
        out.append(missing("c_q2", "answers.q2"))
    elif not isinstance(q2, dict):
        out.append(unknown("c_q2", "answers.q2"))
    else:
        absolute = finite(field(q2, "absolute_power_exponent"), "1")
        fractional = finite(field(q2, "fractional_power_exponent"), "1")
        fixed_bw = field(q2, "fixed_bandwidth")
        fixed_r = field(q2, "fixed_responsivity")
        if MISSING in (field(q2, "absolute_power_exponent"), field(q2, "fractional_power_exponent"), fixed_bw, fixed_r):
            out.append(missing("c_q2", "answers.q2 scaling exponents and fixed conditions"))
        elif absolute is None or fractional is None:
            out.append(verdict("c_q2", "fail", "Scaling exponents must be finite numbers.", "malformed_claim"))
        elif fixed_bw is False or fixed_r is False or abs(absolute - 0.5) > 0.05 or abs(fractional + 0.5) > 0.05:
            out.append(verdict("c_q2", "fail", "Shot rms current scales as P^0.5 and its fractional value as P^-0.5 under fixed conditions.", "physical_contradiction"))
        elif fixed_bw is True and fixed_r is True:
            out.append(verdict("c_q2", "pass", "The absolute and fractional shot-noise trends are distinguished."))
        else:
            out.append(unknown("c_q2", "answers.q2"))
    if q3 is MISSING:
        out.append(missing("c_q3", "answers.q3"))
    elif not isinstance(q3, dict) or not isinstance(field(q3, "limits"), list):
        out.append(unknown("c_q3", "answers.q3.limits"))
    else:
        limits = {name(item) for item in q3["limits"]}
        if "unlimited_power_is_safe" in limits or field(q3, "check_linearity_before_increase") is False:
            out.append(verdict("c_q3", "fail", "Unlimited power or unchecked detector linearity contradicts physical limits.", "physical_contradiction"))
        elif limits - {"detector_saturation", "heating_or_drift", "optical_damage", "detector_damage", "gain_compression"}:
            out.append(unknown("c_q3", "answers.q3.limits"))
        elif len(limits) >= 2 and field(q3, "check_linearity_before_increase") is True:
            out.append(verdict("c_q3", "pass", "Multiple high-power limits and a linearity check are specified."))
        else:
            out.append(missing("c_q3", "answers.q3.limits/check_linearity_before_increase"))
    return out


def _bpp(case: dict[str, Any], answer: dict[str, Any]) -> list[dict[str, Any]]:
    result = evaluate_bpp_base(case, answer)
    q3 = question(answer, "q3")
    if not isinstance(q3, dict) or "same_beam_scenarios" not in q3:
        result[2] = missing("c_tradeoff", "answers.q3.same_beam_scenarios")
        return result
    scenarios = q3["same_beam_scenarios"]
    if not isinstance(scenarios, list) or len(scenarios) != 2:
        result[2] = verdict("c_tradeoff", "fail", "Two reciprocal same-beam scenarios are required.", "missing_claim")
        return result
    modes: set[str] = set()
    for scenario in scenarios:
        mode = name(field(scenario, "mode"))
        size = finite(field(scenario, "size_ratio"), "1")
        divergence = finite(field(scenario, "divergence_ratio"), "1")
        if mode not in {"reduce_size", "reduce_divergence"}:
            result[2] = unknown("c_tradeoff", "answers.q3.same_beam_scenarios.mode")
            return result
        if size is None or divergence is None or size <= 0 or divergence <= 0:
            result[2] = verdict("c_tradeoff", "fail", "Ratios must be positive finite numbers.", "malformed_claim")
            return result
        if size * divergence < 1 - 1e-9 or (mode == "reduce_size" and not (size < 1 < divergence)) or (mode == "reduce_divergence" and not (divergence < 1 < size)):
            result[2] = verdict("c_tradeoff", "fail", "The stated same-beam ratios violate the phase-space product or reciprocal direction.", "physical_contradiction")
            return result
        modes.add(mode)
    if modes != {"reduce_size", "reduce_divergence"}:
        result[2] = verdict("c_tradeoff", "fail", "The two scenarios duplicate a direction.", "missing_claim")
    return result


def evaluate(case: dict[str, Any], answer: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(answer, dict):
        return [verdict(c["id"], "fail", "Answer is not an object.", "invalid_contract") for c in case["scoring"]["criteria"]]
    case_id = case.get("case_id")
    if case_id == "SEED-8-1":
        return _design(answer)
    if case_id == "SEED-5-7":
        return _noise(answer)
    if case_id == "SEED-2-8":
        return _bpp(case, answer)
    return []
