"""Write/check explicit development challenges for the open reasoning wave."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / "benchmark" / "fixtures_vnext"


def q(value: float, unit: str = "1") -> dict:
    return {"value": value, "unit": unit}


def base_design() -> dict:
    return {"answers": {
        "q1": {"family": "simultaneous_reference", "observable": "sample_reference_ratio",
               "free_space_sample_path": True, "linear_detector": True},
        "q2": {"method": "simultaneous_reference", "drift_control_tracks_source_variation": True,
               "drift_timescale_s": q(10.0, "s"), "cycle_timescale_s": q(0.01, "s"), "out_of_loop_monitor": False},
        "q3": {"unattenuated_current_ma": q(5.0, "mA"), "attenuation_fraction": q(0.1),
               "linear_limit_ma": q(1.0, "mA"), "measured_fractional_noise_floor": q(2e-5)},
        "q4": {"blank": True, "dark": True, "linearity": True, "known_attenuation": True},
        "q5": [{"family": family, "observable": observable, "drift_method": family,
                "has_observable": True, "has_drift_control": True,
                "has_linearity_calibration": True} for family in (
                    "simultaneous_reference", "sample_state_modulation", "active_source_stabilization")
                for observable in ({"simultaneous_reference": "sample_reference_ratio",
                                    "sample_state_modulation": "modulated_transmission",
                                    "active_source_stabilization": "sequential_transmission"}[family],)],
    }}


def base_noise() -> dict:
    return {"answers": {
        "q1": {"hypotheses": [
            {"family": "residual_source_rin", "fractional_scaling": "constant",
             "discriminating_test": "block_sample_compare_reference"},
            {"family": "detector_nonlinearity", "fractional_scaling": "flattening_or_growth",
             "discriminating_test": "attenuation_linearity_scan"}]},
        "q2": {"absolute_power_exponent": q(0.5), "fractional_power_exponent": q(-0.5),
               "fixed_bandwidth": True, "fixed_responsivity": True},
        "q3": {"limits": ["detector_saturation", "heating_or_drift"],
               "check_linearity_before_increase": True},
    }}


def base_bpp() -> dict:
    return {"answers": {
        "q1": {"achievable": False},
        "q2": {"invariant": "beam_parameter_product", "behavior": "cannot_decrease", "same_beam": True},
        "q3": {"reduce_size": "divergence_increases", "reduce_divergence": "size_increases",
               "same_beam_scenarios": [
                   {"mode": "reduce_size", "size_ratio": q(0.1), "divergence_ratio": q(10.0)},
                   {"mode": "reduce_divergence", "size_ratio": q(10.0), "divergence_ratio": q(0.1)}]},
    }}


def fixture(case_id: str, name: str, kind: str, base: dict, changes: list[tuple[tuple, object]],
            statuses: list[str], note: str) -> tuple[Path, str]:
    answer = copy.deepcopy(base)
    for path, value in changes:
        node = answer
        for key in path[:-1]:
            node = node[key]
        if value is DELETE:
            del node[path[-1]]
        else:
            node[path[-1]] = value
    data = {"case_id": case_id, "name": name, "kind": kind, "challenge_reason": note,
            "answer": answer, "expected": {f"c_q{i}": {"status": status} for i, status in enumerate(statuses, 1)}}
    if case_id == "SEED-2-8":
        data["expected"] = {key: {"status": status} for key, status in zip(
            ("c_impossible", "c_invariant", "c_tradeoff"), statuses)}
    return ROOT / case_id / f"{name}.json", json.dumps(data, indent=2, ensure_ascii=False) + "\n"


DELETE = object()


def all_fixtures() -> list[tuple[Path, str]]:
    d, n, b = base_design(), base_noise(), base_bpp()
    p, f = "pass", "fail"
    u = "unresolved"
    cases: list[tuple[Path, str]] = []
    add = lambda case_id, label, kind, base, changes, statuses, note: cases.append(
        fixture(case_id, label, kind, base, changes, statuses, note))
    add("SEED-8-1", "positive_reference_ratio", "positive", d, [], [p]*5,
        "Simultaneous reference and sample channels with measured sensitivity and calibration.")
    add("SEED-8-1", "alternative_sample_modulation", "alternative_valid", d, [
        (("answers", "q1", "family"), "sample_state_modulation"),
        (("answers", "q1", "observable"), "modulated_transmission"),
        (("answers", "q2", "method"), "sample_state_modulation")], [p]*5,
        "Sample-state modulation gives a different physical drift-rejection principle.")
    add("SEED-8-1", "alternative_active_stabilization", "alternative_valid", d, [
        (("answers", "q1", "family"), "active_source_stabilization"),
        (("answers", "q1", "observable"), "sequential_transmission"),
        (("answers", "q2", "method"), "active_source_stabilization"),
        (("answers", "q2", "out_of_loop_monitor"), True)], [p]*5,
        "Out-of-loop monitored active stabilization permits sequential comparison.")
    add("SEED-8-1", "alternative_equivalent_units", "alternative_valid", d, [
        (("answers", "q2", "drift_timescale_s"), q(10000.0, "ms")),
        (("answers", "q2", "cycle_timescale_s"), q(10.0, "ms")),
        (("answers", "q3", "unattenuated_current_ma"), q(0.005, "A")),
        (("answers", "q3", "attenuation_fraction"), q(10.0, "percent")),
        (("answers", "q3", "linear_limit_ma"), q(1000.0, "uA")),
        (("answers", "q3", "measured_fractional_noise_floor"), q(0.002, "percent"))], [p]*5,
        "Equivalent time, current, and fractional units preserve the physical inequalities.")
    add("SEED-8-1", "negative_missing_observable", "negative", d, [
        (("answers", "q1", "observable"), "source_power_only")], [f,p,p,p,p],
        "Source power alone does not observe sample transmission.")
    add("SEED-8-1", "adversarial_wrong_observable_family", "adversarial", d, [
        (("answers", "q1", "observable"), "sequential_transmission")], [f,p,p,p,p],
        "A simultaneous ratio layout cannot silently claim the stabilized sequential observable.")
    add("SEED-8-1", "adversarial_saturation_claim", "adversarial", d, [
        (("answers", "q3", "attenuation_fraction"), q(0.5)),
        (("explanation",), "Precision optics and AI correction make this saturated detector a 10^-4 sensor.")], [p,p,f,p,p],
        "Polished claim cannot rescue a detector current above its linear limit.")
    add("SEED-8-1", "negative_missing_blank", "negative", d, [
        (("answers", "q4", "blank"), False)], [p,p,p,f,p],
        "A blank baseline is required to infer a transmission change.")
    add("SEED-8-1", "adversarial_duplicate_split_beam", "adversarial", d, [
        (("answers", "q5", 2, "family"), "balanced_split_beam"),
        (("answers", "q5", 2, "observable"), "sample_reference_ratio"),
        (("answers", "q5", 2, "drift_method"), "simultaneous_reference")], [p,p,p,p,f],
        "Ratio and balanced arithmetic on one split-beam path are one architecture.")
    add("SEED-8-1", "adversarial_wrong_drift_function", "adversarial", d, [
        (("answers", "q5", 1, "drift_method"), "simultaneous_reference")], [p,p,p,p,f],
        "A modulation design cannot claim drift rejection from a nonexistent simultaneous reference channel.")
    add("SEED-8-1", "boundary_novel_calibrated_method", "boundary", d, [
        (("answers", "q5", 2, "family"), "frequency_comb_encoded_reference")], [p,p,p,p,u],
        "A credible unfamiliar reference method is not false-failed by topology name.")
    add("SEED-8-1", "negative_drift_too_fast", "negative", d, [
        (("answers", "q2", "cycle_timescale_s"), q(20.0, "s"))], [p,f,p,p,p],
        "Sequential comparison slower than source drift lacks a valid control.")

    add("SEED-5-7", "positive_rin_and_nonlinearity", "positive", n, [], [p,p,p],
        "Distinct technical and transfer-function plateau hypotheses.")
    add("SEED-5-7", "alternative_imbalance_and_bandwidth", "alternative_valid", n, [
        (("answers", "q1", "hypotheses"), [
            {"family": "channel_gain_imbalance", "fractional_scaling": "constant", "discriminating_test": "rebalance_gain"},
            {"family": "bandwidth_growth", "fractional_scaling": "flattening_or_growth", "discriminating_test": "hold_bandwidth_fixed"}])], [p,p,p],
        "Independent balancing and bandwidth controls separate distinct causes.")
    add("SEED-5-7", "negative_ideal_shot_plateau", "negative", n, [
        (("answers", "q1", "hypotheses", 0), {"family": "ideal_shot_noise", "fractional_scaling": "constant", "discriminating_test": "power_scan"})], [f,p,p],
        "At fixed bandwidth ideal fractional shot noise falls as inverse square root of power.")
    add("SEED-5-7", "adversarial_synonym_counting", "adversarial", n, [
        (("answers", "q1", "hypotheses", 1), {"family": "residual_source_rin", "fractional_scaling": "constant", "discriminating_test": "block_sample_compare_reference"})], [f,p,p],
        "Repeated RIN language is one physical fault family.")
    add("SEED-5-7", "negative_wrong_shot_scaling", "negative", n, [
        (("answers", "q2", "fractional_power_exponent"), q(0.0))], [p,f,p],
        "A constant fractional shot-noise claim violates fixed-bandwidth scaling.")
    add("SEED-5-7", "adversarial_unlimited_power", "adversarial", n, [
        (("answers", "q3", "limits"), ["unlimited_power_is_safe", "detector_saturation"])], [p,p,f],
        "Rhetorical safety assurances do not remove saturation and damage limits.")
    add("SEED-5-7", "boundary_novel_plateau_process", "boundary", n, [
        (("answers", "q1", "hypotheses", 1), {"family": "thermal_lens_coupling", "fractional_scaling": "flattening_or_growth", "discriminating_test": "beam_profile_power_scan"})], [u,p,p],
        "A plausible thermal-coupling mechanism outside the bounded registry abstains.")
    add("SEED-5-7", "boundary_novel_power_limit", "boundary", n, [
        (("answers", "q3", "limits", 1), "photobleaching")], [p,p,u],
        "A possible sample-specific high-power limit is not assumed invalid.")
    add("SEED-5-7", "negative_fixed_electronics_plateau", "negative", n, [
        (("answers", "q1", "hypotheses", 0), {"family": "fixed_electronic_noise", "fractional_scaling": "constant", "discriminating_test": "dark_measurement"})], [f,p,p],
        "A fixed absolute electronic floor falls fractionally as 1/P.")

    add("SEED-2-8", "positive_reciprocal_products", "positive", b, [], [p,p,p],
        "A tenfold reduction of either variable requires the reciprocal increase.")
    add("SEED-2-8", "alternative_etendue_language", "alternative_valid", b, [
        (("answers", "q2", "invariant"), "etendue"),
        (("answers", "q3", "same_beam_scenarios", 0, "size_ratio"), q(0.2)),
        (("answers", "q3", "same_beam_scenarios", 0, "divergence_ratio"), q(5.0))], [p,p,p],
        "Etendue formulation and a different reciprocal factor remain valid.")
    add("SEED-2-8", "negative_both_shrink", "negative", b, [
        (("answers", "q3", "same_beam_scenarios", 0, "divergence_ratio"), q(0.1))], [p,p,f],
        "Both same-beam size and divergence shrink, lowering phase-space product.")
    add("SEED-2-8", "adversarial_polished_ideal_telescope", "adversarial", b, [
        (("answers", "q1", "achievable"), True),
        (("explanation",), "A premium ideal telescope preserves power and reduces both angles and size by tenfold.")], [f,p,p],
        "Prestige language does not defeat the passive beam-product limit.")
    add("SEED-2-8", "negative_duplicate_direction", "negative", b, [
        (("answers", "q3", "same_beam_scenarios", 1, "mode"), "reduce_size"),
        (("answers", "q3", "same_beam_scenarios", 1, "size_ratio"), q(0.1)),
        (("answers", "q3", "same_beam_scenarios", 1, "divergence_ratio"), q(10.0))], [p,p,f],
        "Two size-reduction examples do not answer the reciprocal divergence question.")
    add("SEED-2-8", "boundary_novel_invariant", "boundary", b, [
        (("answers", "q2", "invariant"), "symplectic_phase_space_capacity")], [p,u,p],
        "A credible unfamiliar invariant formulation abstains.")
    add("SEED-2-8", "boundary_novel_scenario_mode", "boundary", b, [
        (("answers", "q3", "same_beam_scenarios", 0, "mode"), "magnification_transform")], [p,p,u],
        "A new scenario representation is not silently false-failed.")
    add("SEED-2-8", "negative_unchanged_conjugate", "negative", b, [
        (("answers", "q3", "same_beam_scenarios", 0, "divergence_ratio"), q(1.0))], [p,p,f],
        "Shrinking size with unchanged far-field divergence lowers the same-beam product.")
    add("SEED-2-8", "negative_missing_ratio_scenarios", "negative", b, [
        (("answers", "q3", "same_beam_scenarios"), DELETE)], [p,p,f],
        "The vNext quantitative contract is not supplied.")
    return cases


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    mismatches = []
    for path, content in all_fixtures():
        if args.check:
            if not path.is_file() or path.read_text(encoding="utf-8") != content:
                mismatches.append(str(path))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
    print(f"Checked {len(all_fixtures())} fixtures" if args.check else f"Wrote {len(all_fixtures())} fixtures")
    if mismatches:
        print("Mismatch: " + ", ".join(mismatches))
    return int(bool(mismatches))


if __name__ == "__main__":
    raise SystemExit(main())
