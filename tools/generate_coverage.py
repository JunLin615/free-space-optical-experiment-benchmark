"""Generate the complete-seed coverage and migration inventories.

Canonical YAML supplies identity, taxonomy, provenance, and validation status.
The compact annotations below are reviewable scientific planning judgments, not
scoring results or a hidden evaluation split. Run with --check in CI/review.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import sys

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.scoring_runtime import SCORERS
from tools.validate_cases import ROOT


CASES = ROOT / "benchmark" / "cases"
COVERAGE = ROOT / "benchmark" / "coverage"
DOCS = ROOT / "docs"
EXPECTED = {f"{section}.{item}" for section in range(1, 9) for item in range(1, 9)}

# id | openness | prospective readiness | evaluation families | primary concept
# All labels were reviewed against the canonical task and the seed audit. A–E
# are nonexclusive scorer-development families. Openness is scientific openness.
ANNOTATIONS = """
1.1|S0|deterministic-ready|A|mirror_steering
1.2|S2|constraint-ready|C|alignment
1.3|S1|structured-ready|B,C|mirror_steering
1.4|S1|structured-ready|B,C|alignment
1.5|S0|deterministic-ready|A|optical_delay
1.6|S1|structured-ready|B|wavelength_routing
1.7|S0|deterministic-ready|A,B|polarization_transformation
1.8|S2|constraint-ready|B,C|polarization_attenuation
2.1|S0|deterministic-ready|A|gaussian_focus
2.2|S1|deterministic-ready|A,C|beam_expansion
2.3|S3|judge-required|C,E|beam_expansion
2.4|S0|deterministic-ready|A|gaussian_invariants
2.5|S2|constraint-ready|C,D|cavity_coupling
2.6|S2|constraint-ready|C|beam_shaping
2.7|S1|constraint-ready|A,C|aperture_clipping
2.8|S0|structured-ready|B|gaussian_invariants
3.1|S0|deterministic-ready|A|lens_imaging
3.2|S1|structured-ready|B,C|relay_imaging
3.3|S0|structured-ready|B|fourier_plane_filtering
3.4|S0|structured-ready|B|fourier_plane_filtering
3.5|S1|structured-ready|B|spectral_resolution
3.6|S2|constraint-ready|C|pupil_field_conjugacy
3.7|S0|deterministic-ready|A|diffraction_resolution
3.8|S1|structured-ready|B,C|angular_metrology
4.1|S0|structured-ready|B|polarization_transformation
4.2|S0|deterministic-ready|A|interferometer_phase
4.3|S2|judge-required|D|interferometer_stability
4.4|S2|constraint-ready|C|interferometer_phase
4.5|S1|structured-ready|B,C|interferometer_coherence
4.6|S0|structured-ready|B|interferometer_stability
4.7|S2|constraint-ready|C,D|cavity_coupling
4.8|S2|constraint-ready|B,C|polarization_detection
5.1|S2|constraint-ready|C|fluorescence_background
5.2|S2|constraint-ready|C|raman_background
5.3|S2|constraint-ready|C|weak_absorption
5.4|S2|constraint-ready|C|modulated_detection
5.5|S0|deterministic-ready|A,B|heterodyne_detection
5.6|S2|judge-required|D|detector_diagnostics
5.7|S0|structured-ready|B|detection_noise
5.8|S3|constraint-ready|C|spectral_background
6.1|S3|judge-required|C,E|interferometer_phase
6.2|S3|judge-required|A,C|pump_probe
6.3|S2|constraint-ready|C|multipass_absorption
6.4|S3|constraint-ready|C|nonlinear_conversion
6.5|S2|constraint-ready|C|confocal_sectioning
6.6|S3|judge-required|A,C|interferometer_phase
6.7|S3|constraint-ready|C|beam_conditioning
6.8|S4|judge-required|C,E|complex_field_measurement
7.1|S2|judge-required|D|alignment
7.2|S2|constraint-ready|D|beam_expansion
7.3|S2|judge-required|D|interferometer_stability
7.4|S1|constraint-ready|B,C|beam_expansion
7.5|S0|structured-ready|B|polarization_attenuation
7.6|S0|structured-ready|B|polarization_purity
7.7|S2|judge-required|D|pump_probe
7.8|S0|structured-ready|B|gaussian_invariants
8.1|S4|judge-required|C,E|weak_absorption
8.2|S4|judge-required|C,E|phase_imaging
8.3|S4|judge-required|C,E|polarization_imaging
8.4|S4|judge-required|C,E|pump_probe
8.5|S4|judge-required|C,E|interferometer_phase
8.6|S3|constraint-ready|C|wavelength_routing
8.7|S4|judge-required|C,E|scattering_dynamic_range
8.8|S4|judge-required|C,E|beam_conditioning
"""

OPENNESS = {
    "S0": "Fully specified or physically closed",
    "S1": "Limited design choices",
    "S2": "Multiple valid architectures or causal paths",
    "S3": "Explicit engineering trade-offs",
    "S4": "Open scientific system design",
}
READINESS = (
    "deterministic-ready", "structured-ready", "constraint-ready",
    "judge-required", "unresolved-needs-redesign",
)
FAMILIES = {
    "A": "Deterministic quantitative",
    "B": "Deterministic structured physics",
    "C": "Constraint-based experimental design",
    "D": "Diagnostic or causal reasoning",
    "E": "Semantic-heavy open design",
}
QUANTITATIVE_DOMINANT = {
    "1.1", "1.5", "1.7", "2.1", "2.2", "2.4", "3.1", "3.7", "4.2", "5.5", "6.2",
}
DETERMINISTIC_DOMINANT = QUANTITATIVE_DOMINANT - {"6.2"}
# Conservative list of seed defects/ambiguities explicitly repaired in the
# English task or gold. Other provenance notes may merely clarify wording.
SCIENTIFIC_CORRECTION_IDS = {
    "1.1", "1.2", "1.4", "1.7", "2.1", "2.7", "3.3", "4.8",
    "5.7", "6.2", "7.1", "8.1", "8.3", "8.6",
}
CRITIQUE_BOUNDARY = {"2.8", "3.4", "4.6", "7.5", "7.6", "7.8"}
FORWARD_PREDICTION = {
    "1.1", "1.5", "1.7", "2.1", "2.4", "3.1", "3.3", "3.5",
    "3.7", "4.1", "4.2", "4.5", "5.5", "5.7",
}
MODE_FROM_TAXONOMY = {
    "quantitative_inference": "quantitative_inference",
    "experimental_design": "inverse_design",
    "diagnosis": "diagnosis",
    "calibration": "calibration",
    "verification": "verification",
    "error_analysis": "error_analysis",
    "planning": "experimental_planning",
}

# Siblings indicate leakage risk in a later split, even when primary concepts
# differ. These are not a split and do not assign cases to evaluation sets.
SIBLING_CLUSTERS = {
    "alignment_and_conditioning": "1.2 6.7 7.1 8.8",
    "expansion_and_mode_quality": "2.2 2.3 2.6 2.7 7.2 7.4",
    "gaussian_invariants": "2.4 2.8 7.8",
    "cavity_coupling": "2.5 4.7",
    "polarization_attenuation": "1.7 1.8 7.5 7.6",
    "interferometer_phase_and_stability": "4.3 4.4 4.6 6.1 6.6 8.5",
    "weak_signal_detection": "5.3 5.4 5.6 5.7 5.8 8.1 8.7",
    "pump_probe": "6.2 7.7 8.4",
    "fourier_plane_filtering": "3.2 3.3 3.4",
}


def _annotations() -> dict[str, dict[str, object]]:
    rows = {}
    for line in ANNOTATIONS.strip().splitlines():
        legacy, openness, readiness, families, concept = line.split("|")
        if legacy in rows:
            raise ValueError(f"duplicate coverage annotation {legacy}")
        if openness not in OPENNESS or readiness not in READINESS:
            raise ValueError(f"invalid annotation for {legacy}")
        family_list = families.split(",")
        if any(value not in FAMILIES for value in family_list):
            raise ValueError(f"invalid evaluation family for {legacy}")
        rows[legacy] = {
            "openness": openness,
            "scoring_readiness": readiness,
            "evaluation_families": family_list,
            "primary_concept_family": concept,
        }
    if set(rows) != EXPECTED:
        raise ValueError(f"annotation IDs differ from 64-case seed: missing={sorted(EXPECTED-set(rows))}; extra={sorted(set(rows)-EXPECTED)}")
    return rows


def _modes(legacy: str, task_types: list[str]) -> list[str]:
    result = {MODE_FROM_TAXONOMY[t] for t in task_types if t in MODE_FROM_TAXONOMY}
    if legacy in CRITIQUE_BOUNDARY:
        result.add("critique_physical_boundary")
    if legacy in FORWARD_PREDICTION or not result:
        result.add("forward_prediction")
    return sorted(result)


def build() -> tuple[dict, dict, str, str]:
    annotations = _annotations()
    cases = [yaml.safe_load(path.read_text(encoding="utf-8")) for path in sorted(CASES.glob("*.yaml"))]
    legacy_ids = [case.get("legacy_id") for case in cases]
    if len(cases) != 64 or len(set(legacy_ids)) != 64 or set(legacy_ids) != EXPECTED:
        raise ValueError("canonical cases must cover all 64 unique legacy IDs 1.1–8.8")
    source_hashes = {case.get("provenance", {}).get("source_hash") for case in cases}
    if len(source_hashes) != 1 or not next(iter(source_hashes)):
        raise ValueError("all migrated cases must refer to one source seed hash")
    siblings = defaultdict(list)
    for cluster, ids in SIBLING_CLUSTERS.items():
        for legacy in ids.split():
            if legacy not in EXPECTED:
                raise ValueError(f"unknown sibling-cluster ID {legacy}")
            siblings[legacy].append(cluster)
    rows = []
    progress = []
    for case in sorted(cases, key=lambda item: tuple(map(int, item["legacy_id"].split(".")))):
        legacy = case["legacy_id"]
        case_id = case["case_id"]
        if case_id != f"SEED-{legacy.replace('.', '-')}":
            raise ValueError(f"case/legacy ID mismatch: {case_id}/{legacy}")
        taxonomy = case["taxonomy"]
        status = case["validation_status"]
        scorer = SCORERS.get(case_id)
        common = {
            "legacy_id": legacy,
            "case_id": case_id,
            "title": case["title"],
            "case_revision": case["case_revision"],
            "validation_status": status,
            "optical_domain": taxonomy["optical_domain"],
            "task_types": taxonomy["task_types"],
            "reasoning_modes": _modes(legacy, taxonomy["task_types"]),
            "modality": taxonomy["modality"],
            "provisional_difficulty": taxonomy["difficulty_hypothesis"],
            "openness": annotations[legacy]["openness"],
            "scoring_readiness": annotations[legacy]["scoring_readiness"],
            "evaluation_families": annotations[legacy]["evaluation_families"],
            "primary_concept_family": annotations[legacy]["primary_concept_family"],
            "sibling_clusters": sorted(siblings[legacy]),
            "quantitative_emphasis": "dominant" if legacy in QUANTITATIVE_DOMINANT else "secondary_or_absent",
            "scoring_dominance": "deterministic" if legacy in DETERMINISTIC_DOMINANT else "semantic_or_constraint",
            "scorer_available": scorer is not None,
            "scorer_module": scorer,
        }
        rows.append(common)
        progress.append({
            "legacy_id": legacy,
            "canonical_id": case_id,
            "migration_status": "canonical_english_record_present",
            "validation_status": status,
            "scientific_correction_made": legacy in SCIENTIFIC_CORRECTION_IDS,
            "scoring_readiness": common["scoring_readiness"],
            "scorer_available": common["scorer_available"],
        })
    counts = {
        "optical_domain": dict(sorted(Counter(row["optical_domain"] for row in rows).items())),
        "task_type": dict(sorted(Counter(t for row in rows for t in row["task_types"]).items())),
        "reasoning_mode": dict(sorted(Counter(t for row in rows for t in row["reasoning_modes"]).items())),
        "provisional_difficulty": dict(sorted(Counter(row["provisional_difficulty"] for row in rows).items())),
        "openness": {key: sum(row["openness"] == key for row in rows) for key in OPENNESS},
        "scoring_readiness": {key: sum(row["scoring_readiness"] == key for row in rows) for key in READINESS},
        "evaluation_family": {key: sum(key in row["evaluation_families"] for row in rows) for key in FAMILIES},
        "quantitative_emphasis": dict(sorted(Counter(row["quantitative_emphasis"] for row in rows).items())),
        "scoring_dominance": dict(sorted(Counter(row["scoring_dominance"] for row in rows).items())),
        "validation_status": dict(sorted(Counter(row["validation_status"] for row in rows).items())),
        "scorer_available": {"yes": sum(row["scorer_available"] for row in rows), "no": sum(not row["scorer_available"] for row in rows)},
    }
    coverage = {
        "schema_version": "0.1.0",
        "source_seed_sha256": next(iter(source_hashes)),
        "case_count": len(rows),
        "method": "Canonical YAML supplies identity, taxonomy and validation status; tools/scoring_runtime.py supplies registered scorer availability; explicitly reviewed planning annotations in tools/generate_coverage.py supply openness, readiness, evaluation families, concept family, and dominant emphasis.",
        "openness_definitions": OPENNESS,
        "evaluation_family_definitions": FAMILIES,
        "counts": counts,
        "cases": rows,
    }
    migration = {
        "schema_version": "0.1.0",
        "source_seed_sha256": next(iter(source_hashes)),
        "total_seed_cases": 64,
        "canonical_english_records": 64,
        "note": "Corpus migration is complete; scorer availability and release verification are separate gates. scientific_correction_made is a conservative reviewed seed-audit repair flag; ordinary translation clarifications may not be flagged. Consult each case's provenance.derivation for its exact change history.",
        "cases": progress,
    }
    return coverage, migration, _coverage_markdown(coverage), _readiness_markdown(coverage)


def _table(counts: dict[str, int], denominator: int = 64) -> str:
    return "\n".join(f"| `{key}` | {value} | {value/denominator:.1%} |" for key, value in counts.items())


def _coverage_markdown(coverage: dict) -> str:
    c = coverage["counts"]
    sections = [
        "# Complete-seed coverage report",
        "",
        "Generated by `python tools/generate_coverage.py` from 64 English canonical case records and reviewed coverage annotations. Run `python tools/generate_coverage.py --check` to detect stale outputs. The original Chinese HTML remains source provenance; this report creates no hidden split.",
        "",
        f"The corpus has **64/64** seed IDs (`1.1`–`8.8`). **{c['scorer_available']['yes']}** have registered scorers; **{c['scorer_available']['no']}** do not. Validation status is a separate field. Corpus completion does not establish release readiness.",
        "",
    ]
    for title, key, note in [
        ("Optical domain", "optical_domain", "Mutually exclusive canonical primary domain."),
        ("Canonical task type", "task_type", "Multi-label; totals can exceed 64."),
        ("Reasoning mode", "reasoning_mode", "Multi-label normalized from canonical task types plus reviewed prediction/boundary distinctions; totals can exceed 64."),
        ("Provisional difficulty", "provisional_difficulty", "Author hypothesis; no empirical difficulty calibration has been run."),
        ("Scientific openness", "openness", "Scientific scope, independent of present scorer implementation."),
        ("Prospective scoring readiness", "scoring_readiness", "Recommended next oracle family, not a claim of implemented scoring."),
        ("Evaluation family", "evaluation_family", "Nonexclusive A–E development families; totals can exceed 64."),
        ("Quantitative emphasis", "quantitative_emphasis", "Dominant means the main evidence is numerical or symbolic, not merely that a number occurs."),
        ("Scoring dominance", "scoring_dominance", "Deterministic dominant reflects the seed audit's criterion-level judgment; semantic or constraint cases may still contain deterministic subchecks."),
        ("Validation status", "validation_status", "Read directly from canonical YAML."),
    ]:
        sections += [f"## {title}", "", note, "", "| Label | Cases | Share of corpus |", "| --- | ---: | ---: |", _table(c[key]), ""]
    sections += [
        "## Coverage gaps and leakage-aware planning", "",
        "The seed emphasizes optical layout, qualitative physical constraints, and explanation: only 11 cases are quantitative-dominant. Primary-domain counts are particularly small for phase imaging (1), metrology (2), and beam diagnostics (2), although related ideas also appear under other domains. Dedicated numerical uncertainty propagation, calibrated noise budgets, measurement data interpretation, component tolerance/sensitivity, and safe high-power alignment are sparse. These are future coverage gaps, not authorization to add cases in this migration.", "",
        "Near-duplicate concepts are retained because they ask for different evidence. The `sibling_clusters` array in `coverage.json` marks likely leakage links for a later split. A split should group close siblings after reviewing the task bytes and answer requirements; no public/hidden assignment is made here.", "",
        "| Concept cluster | IDs | Reasoning distinction |", "| --- | --- | --- |",
        "| Alignment and conditioning | 1.2, 6.7, 7.1, 8.8 | Procedure, conditioning chain, reachability diagnosis, acceptance plan. |",
        "| Expansion and mode quality | 2.2, 2.3, 2.6, 2.7, 7.2, 7.4 | Ideal sizing, power/damage, anamorphism, clipping, fault isolation, measurement. |",
        "| Gaussian invariants | 2.4, 2.8, 7.8 | Parameter scaling and two different impossibility claims. |",
        "| Cavity coupling | 2.5, 4.7 | Diagnose higher modes versus design matching controls. |",
        "| Polarization attenuation | 1.7, 1.8, 7.5, 7.6 | Jones transformation, variable attenuation, circular-input counterexample, passive purity limit. |",
        "| Interferometer phase and stability | 4.3, 4.4, 4.6, 6.1, 6.6, 8.5 | Drift, topology, reciprocity, index, displacement, common-path design. |",
        "| Weak-signal detection | 5.3, 5.4, 5.6, 5.7, 5.8, 8.1, 8.7 | Reference, modulation, saturation, noise, spectral rejection, architecture, scatter dynamic range. |",
        "| Pump–probe | 6.2, 7.7, 8.4 | Quantitative system build, missing-signal diagnosis, open instrument design. |",
        "| Fourier-plane filtering | 3.2, 3.3, 3.4 | Relay construction, frequency suppression, wrong-plane critique. |",
        "",
        "## Interpretation limits", "",
        "Scoring-readiness and openness are reviewed planning labels. `scorer_available` means the runtime has a registered case scorer; it does not imply `release_verified`. Difficulty labels remain hypotheses. The machine-readable matrix preserves both the canonical taxonomy and these derived/planned axes per case.", "",
    ]
    return "\n".join(sections)


def _readiness_markdown(coverage: dict) -> str:
    rows = coverage["cases"]
    by_readiness = defaultdict(list)
    by_family = defaultdict(list)
    for row in rows:
        by_readiness[row["scoring_readiness"]].append(row["legacy_id"])
        for family in row["evaluation_families"]:
            by_family[family].append(row["legacy_id"])
    lines = [
        "# Scoring readiness of the complete seed", "",
        "Generated by `python tools/generate_coverage.py`. These are prospective scorer-development classes based on the scientific task. The canonical validation lifecycle and runtime registration are separate. No newly migrated case is promoted by this classification.", "",
        f"**Current implementation:** {coverage['counts']['scorer_available']['yes']} registered scorers (" + ", ".join(row["case_id"] for row in rows if row["scorer_available"]) + f"); {coverage['counts']['scorer_available']['no']} cases without one. The corpus has 64 canonical English records and {coverage['counts']['validation_status'].get('release_verified', 0)} `release_verified` cases.", "",
        "| Class | Count | Legacy IDs |", "| --- | ---: | --- |",
    ]
    for key in READINESS:
        lines.append(f"| `{key}` | {len(by_readiness[key])} | {', '.join(by_readiness[key]) or 'None'} |")
    lines += [
        "", "## Evaluation families", "",
        "These nonexclusive labels identify the type of oracle work. In particular, family D lists diagnostic/causal cases even when a constraint scorer is already registered.", "",
        "| Family | Cases | Legacy IDs |", "| --- | ---: | --- |",
    ]
    for key in FAMILIES:
        lines.append(f"| **{key}** — {FAMILIES[key]} | {len(by_family[key])} | {', '.join(by_family[key]) or 'None'} |")
    lines += [
        "", "## Development batches", "",
        "1. Extend low-risk unit-aware oracles for closed calculations, beginning with the deterministic-ready cases that have no registered scorer. Derive values from prompt givens and test boundary, alternative, and plausible wrong answers before status promotion.",
        "2. Add typed physical-relationship checks for structured-ready cases, preserving alternative sign conventions and equivalent representations. Unknown credible formulations must remain unresolved until independently tested.",
        "3. Build constraint and causal checks for constraint-ready design and diagnosis cases. Test mandatory functions, forbidden contradictions, observables, controls, and causally distinct alternatives; avoid topology-name whitelists.",
        "4. Calibrate bounded semantic judging for judge-required cases using independently reviewed criterion decisions and adversarial responses. Do not infer a pass from fluent prose or promote without live calibration evidence.",
        "", "Some cases combine A–E families; the primary readiness class identifies the current bottleneck, not the only permissible scorer. `unresolved-needs-redesign` is presently empty because each task has a canonical specification, but this can change after adversarial scientific review. The original seed audit identified uncertainty and data-evidence gaps, which future cases may address after this migration round.", "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if generated outputs are stale")
    args = parser.parse_args()
    coverage, migration, report, readiness = build()
    outputs = {
        COVERAGE / "coverage.json": json.dumps(coverage, ensure_ascii=False, indent=2) + "\n",
        COVERAGE / "migration_status.json": json.dumps(migration, ensure_ascii=False, indent=2) + "\n",
        DOCS / "coverage_report.md": report,
        DOCS / "scoring_readiness.md": readiness,
    }
    stale = []
    for path, content in outputs.items():
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != content:
                stale.append(str(path.relative_to(ROOT)))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8", newline="\n")
    if stale:
        print("Stale coverage outputs: " + ", ".join(stale), file=sys.stderr)
        return 1
    print(f"Coverage {'checked' if args.check else 'generated'}: {coverage['case_count']} cases; {coverage['counts']['scorer_available']['yes']} registered scorers.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
