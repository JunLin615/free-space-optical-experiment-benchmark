"""Deterministic, gold-free public records for rc1-derived optics variants.

The on-disk record contains the scientific task and lineage, never the gold.
``load_variant`` reconstructs a scorer-compatible case only inside the evaluator.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import random
import sys
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from jsonschema import Draft202012Validator

from tools.physics_checks import SPEED_OF_LIGHT_M_PER_S, expected_si, to_si
from tools.scoring_runtime import (
    CASES, ROOT, RUNTIME_VERSION, SCORERS, _content_hash,
    _evaluator_fingerprint, evaluate_case,
)
from tools.validate_cases import load_case, semantic_issues


VERSION = "0.1.0"
RELEASE = "0.1.0-rc1"
PUBLIC_DIR = ROOT / "benchmark" / "variants" / "public_dev"
PUBLIC_PLAN = ROOT / "benchmark" / "variants" / "public_plan.json"
QUESTION_BANK = ROOT / "benchmark" / "variants" / "public_questions.md"
RELEASE_MANIFEST = ROOT / "benchmark" / "releases" / f"{RELEASE}.json"
SUPPORTED = ("SEED-1-1", "SEED-1-5", "SEED-1-7", "SEED-2-2", "SEED-4-2")
TYPES = ("parameter", "structural_unit")
PROTOCOLS = ("closed_book", "case_assisted", "tool_assisted", "case_and_tool_assisted")
CONSTRAINTS: dict[str, dict[str, Any]] = {
    "SEED-1-1": {"mirror_rotation_rad": [0, 0.017453292519943295], "screen_distance_m": [1, 3], "regime": "near_normal_small_angle"},
    "SEED-1-5": {"stage_displacement_m": [0.0005, 0.002], "target_delay_s": [50e-12, 160e-12], "passes": 2},
    "SEED-1-7": {"input_axis_separation_rad": [0, 0.7853981633974483], "plate_rotation_rad": [0, 0.2617993877991494]},
    "SEED-2-2": {"input_diameter_m": [0.001, 0.003], "expansion_ratio": [2, 8], "regime": "afocal_paraxial"},
    "SEED-4-2": {"primary_motion_wavelengths": [0, 1.5], "secondary_motion_wavelengths": 0.25,
                 "complete_primary_fringe_periods": True},
}


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def _seed_digest(source: str, kind: str, seed: str) -> str:
    return hashlib.sha256(f"variants:{VERSION}:{source}:{kind}:{seed}".encode()).hexdigest()


def _parent(source: str) -> tuple[dict[str, Any], dict[str, Any]]:
    if source not in SUPPORTED:
        raise ValueError(f"unsupported variant source: {source}")
    parent = load_case(CASES / f"{source}.yaml")
    pin = json.loads(RELEASE_MANIFEST.read_text(encoding="utf-8"))["cases"][source]
    if (parent["case_revision"] != pin["case_revision"]
            or _content_hash(parent) != pin["case_content_sha256"]
            or _evaluator_fingerprint(parent) != pin["evaluator_fingerprint"]
            or SCORERS[source] != pin["scorer"]):
        raise ValueError(f"rc1 parent/scorer pin does not match: {source}")
    return parent, pin


def _pick(rng: random.Random, choices: tuple[Any, ...]) -> Any:
    return choices[rng.randrange(len(choices))]


def _quantity(value: float, unit: str, symbol: str, **extra: Any) -> dict[str, Any]:
    return {"value": value, "unit": unit, "symbol": symbol, **extra}


def _task(source: str, kind: str, seed: str, parent: dict[str, Any]) -> dict[str, Any]:
    rng = random.Random(int(_seed_digest(source, kind, seed), 16))
    task = copy.deepcopy(parent["task"])
    if source == "SEED-1-1":
        if kind == "parameter":
            angle = _pick(rng, (0.4, 0.6, 0.75))
            distance = _pick(rng, (1.6, 2.4, 2.8))
            angular, length = _quantity(angle, "deg", "mirror_rotation"), _quantity(distance, "m", "screen_distance")
            angle_text, distance_text = f"{angle:g}°", f"{distance:g} m"
        else:
            angle = _pick(rng, (0.008, 0.010, 0.012))
            distance = _pick(rng, (1600, 2200, 2700))
            angular, length = _quantity(angle, "rad", "mirror_rotation"), _quantity(distance, "mm", "screen_distance")
            angle_text, distance_text = f"{angle:.3f} rad", f"{distance:g} mm"
        task["givens"] = [angular, length]
        task["statement"] = ("A collimated laser beam is incident nearly normally on an adjustable plane mirror. "
            f"The mirror rotates {angle_text} about a vertical axis. A viewing screen is normal to the nominal "
            f"reflected ray, {distance_text} from the mirror along that ray. Neglect higher-order corrections "
            "associated with the initial angle of incidence. Report the angle change and spot displacement as magnitudes.")
    elif source == "SEED-1-5":
        if kind == "parameter":
            stage = _pick(rng, (0.6, 1.4, 1.8))
            stage_given, stage_text = _quantity(stage, "mm", "stage_displacement"), f"{stage:g} mm"
        else:
            stage = _pick(rng, (750, 1250, 1600))
            stage_given, stage_text = _quantity(stage, "um", "stage_displacement"), f"{stage:g} μm"
        target = _pick(rng, (60, 120, 150))
        task["givens"] = [stage_given, _quantity(target, "ps", "target_delay")]
        task["statement"] = ("An ultrashort pulse enters a straight folded delay line with two reflections. "
            f"The translation stage carrying the retroreflecting mirror group moves {stage_text} along the optical axis. "
            "The beam traverses the moving-stage gap once on the outbound leg and once on the return leg; "
            "no other moving path segment changes. Report changes in optical path and time delay as magnitudes.")
        task["questions"][2]["request"] = f"Estimate the required one-way mechanical travel for a {target:g} ps delay scan."
    elif source == "SEED-1-7":
        if kind == "parameter":
            angle = _pick(rng, (11, 23, 31))
            rotation = _pick(rng, (3, 7, 9))
            angle_given, rotation_given = _quantity(angle, "deg", "input_to_fast_axis_angle"), _quantity(rotation, "deg", "plate_rotation")
            angle_text, rotation_text = f"{angle:g}°", f"{rotation:g}°"
        else:
            angle = _pick(rng, (0.20, 0.30, 0.40))
            rotation = _pick(rng, (0.05, 0.08, 0.10))
            angle_given, rotation_given = _quantity(angle, "rad", "input_to_fast_axis_angle"), _quantity(rotation, "rad", "plate_rotation")
            angle_text, rotation_text = f"{angle:.2f} rad", f"{rotation:.2f} rad"
        task["givens"] = [angle_given, rotation_given]
        task["statement"] = ("Linearly polarized light passes through an ideal half-wave plate. "
            f"The incident polarization axis makes an angle of {angle_text} with the plate's fast axis.")
        task["questions"][1]["request"] = ("If the half-wave plate itself is rotated a further "
            f"{rotation_text}, by what magnitude does the output direction change?")
    elif source == "SEED-2-2":
        ratio = _pick(rng, (3, 4, 6, 7))
        if kind == "parameter":
            diameter = _pick(rng, (1.2, 1.8, 2.4))
            input_given = _quantity(diameter, "mm", "input_diameter", definition="1/e^2 intensity diameter")
            output_given = _quantity(round(diameter * ratio, 6), "mm", "output_diameter", definition="1/e^2 intensity diameter")
        else:
            diameter = _pick(rng, (0.0012, 0.0018, 0.0024))
            input_given = _quantity(diameter, "m", "input_diameter", definition="1/e^2 intensity diameter")
            output_given = _quantity(round(diameter * ratio, 8), "m", "output_diameter", definition="1/e^2 intensity diameter")
        task["givens"] = [input_given, output_given]
        task["statement"] = ("An approximately collimated beam has a 1/e² intensity diameter near "
            f"{input_given['value']:g} {input_given['unit']}. A two-lens afocal system should expand it to "
            f"about {output_given['value']:g} {output_given['unit']}. Consider a first-order paraxial design "
            "with adequate clear apertures.")
    elif source == "SEED-4-2":
        if kind == "parameter":
            primary, secondary = 1.0, 0.25
        else:
            primary, secondary = 1.5, 0.25
        labels = {0.25: "λ/4", 0.5: "λ/2", 1.0: "λ", 1.5: "3λ/2"}
        task["givens"] = [_quantity(primary, "1", "mirror_displacement_wavelengths"),
                          _quantity(secondary, "1", "quarter_mirror_displacement_wavelengths")]
        task["statement"] = ("In a monochromatic-light Michelson interferometer, the mirror in one arm moves by "
            f"{labels[primary]} along the optical axis. Report optical-path changes as magnitudes because no direction is specified.")
        task["questions"][2]["request"] = f"What changes if the mirror moves only {labels[secondary]}?"
    else:
        raise ValueError(source)
    return task


def _materialize(record: dict[str, Any]) -> dict[str, Any]:
    source = record["parent_case_id"]
    parent, pin = _parent(source)
    if (record["parent_case_revision"] != pin["case_revision"]
            or record["parent_case_content_sha256"] != pin["case_content_sha256"]
            or record["parent_release"] != RELEASE
            or record["scorer"]["module"] != pin["scorer"]
            or record["scorer"]["evaluator_version"] != pin["evaluator_version"]
            or record["scorer"]["evaluator_fingerprint"] != pin["evaluator_fingerprint"]):
        raise ValueError("variant lineage conflicts with rc1 parent pin")
    case = copy.deepcopy(parent)
    case["task"] = copy.deepcopy(record["task"])
    case["answer_contract"] = copy.deepcopy(record["answer_contract"])
    case["benchmark_release"] = None
    case["validation_status"] = "executable"
    case["split"] = "public_dev" if record["seed_classification"] == "public_dev" else "hidden_eval"
    case["provenance"]["origin"] = "deterministic_variant"
    case["provenance"]["source_hash"] = pin["case_content_sha256"]
    case["provenance"]["seed_relationship"] = f"Derived from {source} revision {pin['case_revision']} by variant generator {VERSION}."
    case["provenance"]["derivation"] = "Parameter or equivalent-unit change; numerical reference recomputed from typed givens."
    case["validation"].pop("positive_fixtures", None)
    case["validation"].pop("negative_fixtures", None)
    case["validation"].pop("evidence_files", None)
    case["validation"].pop("adversarial_evidence", None)
    case["validation"]["notes"] = "Generated development instance; inherits rc1 scorer code, but is not itself release-verified."
    case["validation"]["independent_derivation"] = "Variant equations are crosschecked independently by tools/variants.py."
    for check in case["gold"].get("numerical_checks", []):
        value_si, dimension = expected_si(case, check["validator_id"])
        unit = check["reference"]["unit"]
        from tools.physics_checks import UNITS
        if UNITS[unit][0] != dimension:
            raise ValueError(f"reference dimension mismatch: {check['id']}")
        check["reference"]["value"] = round(value_si / UNITS[unit][1], 10)
    if source == "SEED-2-2":
        ratio = to_si(case["task"]["givens"][1], "length") / to_si(case["task"]["givens"][0], "length")
        ratio_text = f"{ratio:g}"
        case["title"] = f"Designing a {ratio_text}-fold afocal beam expander"
        case["gold"]["reference_model"]["equation"] = f"For an afocal telescope, |f_output/f_input| = D_output/D_input ≈ {ratio_text}."
        for constraint in case["gold"]["universal_constraints"]:
            if constraint["id"] == "c_ratio":
                constraint["predicate"] = f"The output-to-input beam diameter and focal-length magnitude ratios are about {ratio_text}."
            elif constraint["id"] == "c_examples":
                long = 20 * ratio
                constraint["predicate"] = ("Give a positive-short then positive-long Keplerian pair and a negative-short "
                    f"then positive-long Galilean pair, each with focal-length magnitude ratio {ratio_text}; "
                    f"+20 mm then +{long:g} mm and -20 mm then +{long:g} mm are examples.")
        for family in case["gold"].get("accepted_solution_families", []):
            long = 20 * ratio
            if family["id"] == "keplerian":
                family["example"] = f"A +20 mm input lens and +{long:g} mm output lens separated by about {20 + long:g} mm."
            elif family["id"] == "galilean":
                family["example"] = f"A -20 mm input lens and +{long:g} mm output lens separated by about {long - 20:g} mm."
    if source == "SEED-4-2":
        case["gold"]["known_failure_modes"] = ["Fringe cycles equal the round-trip optical-path change divided by one wavelength."]
    return case


def _public_contract(parent: dict[str, Any]) -> dict[str, Any]:
    """Retain answer shape while removing canonical method-shape answer hints."""
    contract = copy.deepcopy(parent["answer_contract"])
    if parent["case_id"] == "SEED-1-1":
        contract["method_shape"]["q3"] = (
            "Object geometry_change with variable, held_fixed, and dimensionless new/old scale fields."
        )
    if parent["case_id"] == "SEED-1-7":
        contract["method_shape"]["q3"] = (
            "Object with linear_rotation_rule_applies as a boolean; optional explanation may be included."
        )
    return contract


def _expected_answer(case: dict[str, Any]) -> dict[str, Any]:
    source = case["case_id"]
    def ref(check_id: str) -> dict[str, Any]:
        return next(copy.deepcopy(c["reference"]) for c in case["gold"]["numerical_checks"] if c["id"] == check_id)
    if source == "SEED-1-1":
        return {"answers": {"q1": {"angle_change": ref("n_angle")}, "q2": {"spot_displacement": ref("n_shift")},
            "q3": {"geometry_change": {"variable": "screen_distance", "held_fixed": "mirror_rotation", "scale": {"value": 0.25, "unit": "1"}}}}}
    if source == "SEED-1-5":
        return {"answers": {"q1": {"path_change": ref("n_path")}, "q2": {"delay_change": ref("n_delay")},
            "q3": {"stage_travel": ref("n_travel")}}}
    if source == "SEED-1-7":
        return {"answers": {"q1": {"rotation_magnitude": ref("n_rotation")},
            "q2": {"output_change_magnitude": ref("n_plate_effect")},
            "q3": {"linear_rotation_rule_applies": False}}}
    if source == "SEED-2-2":
        ratio = ref("n_expansion")["value"]
        pair = lambda first: {"input_focal_length": {"value": first, "unit": "mm"},
                              "output_focal_length": {"value": 20 * ratio, "unit": "mm"}}
        return {"answers": {"q1": {"expansion_factor": ref("n_expansion")},
            "q2": {"keplerian": pair(20), "galilean": pair(-20)},
            "q3": {"keplerian_real_internal_focus": True, "galilean_real_internal_focus": False}}}
    if source == "SEED-4-2":
        return {"answers": {"q1": {"opd_change_in_wavelengths": ref("n_opd_half")},
            "q2": {"fringe_cycles": ref("n_fringe_half")},
            "q3": {"opd_change_in_wavelengths": ref("n_opd_quarter"),
                   "fringe_cycles": ref("n_fringe_quarter")}}}
    raise ValueError(source)


def validate_variant(record: dict[str, Any]) -> dict[str, Any]:
    """Check lineage, physical domain, independent equations, schema, and scorer solvability."""
    if record.get("variant_schema_version") != VERSION or record.get("generator_version") != VERSION:
        raise ValueError("unsupported variant version")
    if record.get("seed_classification") not in {"public_dev", "private"}:
        raise ValueError("invalid seed classification")
    if record.get("variant_type") not in TYPES:
        raise ValueError("unsupported variant type")
    if "gold" in record or "case" in record:
        raise ValueError("stored variant records must not contain gold or a full case")
    if record.get("parameter_constraints") != CONSTRAINTS.get(record.get("parent_case_id")):
        raise ValueError("variant parameter constraints differ from generator version")
    if record.get("compatible_protocols") != [{"id": protocol, "version": "1.0.0"} for protocol in PROTOCOLS]:
        raise ValueError("variant protocol compatibility differs from this generator version")
    parent, _ = _parent(record["parent_case_id"])
    if record.get("answer_contract") != _public_contract(parent):
        raise ValueError("variant answer contract differs from leak-checked public form")
    if record["seed_classification"] == "private" and "public_seed" in record:
        raise ValueError("private variant record exposes a seed")
    case = _materialize(record)
    source = case["case_id"]
    givens = {g["symbol"]: g for g in case["task"]["givens"]}
    if source == "SEED-1-1":
        angle, distance = to_si(givens["mirror_rotation"], "angle"), to_si(givens["screen_distance"], "length")
        if not (0 < angle < math.radians(1) and 1 <= distance <= 3):
            raise ValueError("mirror geometry outside small-angle nondegenerate domain")
        independent = {"n_angle": 2 * angle, "n_shift": distance * math.tan(2 * angle)}
    elif source == "SEED-1-5":
        stage, target = to_si(givens["stage_displacement"], "length"), to_si(givens["target_delay"], "time")
        if not (0.0005 <= stage <= 0.002 and 50e-12 <= target <= 160e-12):
            raise ValueError("delay stage or target outside validated range")
        independent = {"n_path": 2 * stage, "n_delay": 2 * stage / SPEED_OF_LIGHT_M_PER_S,
                       "n_travel": SPEED_OF_LIGHT_M_PER_S * target / 2}
    elif source == "SEED-1-7":
        angle, rotation = to_si(givens["input_to_fast_axis_angle"], "angle"), to_si(givens["plate_rotation"], "angle")
        if not (0 < angle < math.pi / 4 and 0 < rotation < math.radians(15)):
            raise ValueError("half-wave angles outside unambiguous orientation range")
        independent = {"n_rotation": 2 * angle, "n_plate_effect": 2 * rotation}
    elif source == "SEED-2-2":
        first, second = to_si(givens["input_diameter"], "length"), to_si(givens["output_diameter"], "length")
        if not (0.001 <= first <= 0.003 and 2 <= second / first <= 8):
            raise ValueError("afocal beam diameters or expansion outside validated range")
        independent = {"n_expansion": second / first}
    else:
        first = to_si(givens["mirror_displacement_wavelengths"], "dimensionless")
        second = to_si(givens["quarter_mirror_displacement_wavelengths"], "dimensionless")
        if not (second == 0.25 and 0 < second < first <= 1.5
                and math.isclose(2 * first, round(2 * first), abs_tol=1e-12)):
            raise ValueError("Michelson motions degenerate or full-period question ambiguous")
        independent = {"n_opd_half": 2 * first, "n_fringe_half": 2 * first,
                       "n_opd_quarter": 2 * second, "n_fringe_quarter": 2 * second}
    for check in case["gold"]["numerical_checks"]:
        expected, _ = expected_si(case, check["validator_id"])
        if not math.isclose(expected, independent[check["id"]], rel_tol=1e-12, abs_tol=1e-15):
            raise ValueError(f"independent physics disagreement: {check['id']}")
        tolerance = to_si(check["absolute_tolerance"])
        if tolerance <= 0 or tolerance > 0.1 * abs(expected):
            raise ValueError(f"inappropriate tolerance for variant scale: {check['id']}")
    schema = json.loads((ROOT / "benchmark/schema/case_v0.1.schema.json").read_text(encoding="utf-8"))
    problems = list(Draft202012Validator(schema).iter_errors(case))
    if problems:
        raise ValueError(f"variant case schema: {problems[0].message}")
    problems = semantic_issues(case)
    if problems:
        raise ValueError(f"variant semantic checks: {problems}")
    if _content_hash(case) != record["instance_content_sha256"]:
        raise ValueError("variant case content hash mismatch")
    if _content_hash(case["task"]) != record["scientific_payload_sha256"]:
        raise ValueError("variant scientific payload hash mismatch")
    outcome = evaluate_case(case, _expected_answer(case))
    if outcome["scores"]["capped_total"] != 1.0 or outcome["failure_mode"] != "none":
        raise ValueError(f"variant scorer cannot solve independent reference: {outcome['failure_mode']}")
    return case


def generate_variant(source: str, seed: str, kind: str, *, classification: str = "public_dev") -> dict[str, Any]:
    if kind not in TYPES or classification not in {"public_dev", "private"} or not isinstance(seed, str) or not seed:
        raise ValueError("invalid variant generator arguments")
    if classification == "private" and (len(seed) < 32 or any(c not in "0123456789abcdefABCDEF" for c in seed)):
        raise ValueError("private seeds must contain at least 128 bits of hexadecimal entropy")
    parent, pin = _parent(source)
    task = _task(source, kind, seed, parent)
    digest = _seed_digest(source, kind, seed)
    record: dict[str, Any] = {
        "variant_schema_version": VERSION,
        "variant_id": f"VAR-{source}-{('P' if kind == 'parameter' else 'U')}-{digest[:12]}",
        "parent_case_id": source,
        "parent_case_revision": pin["case_revision"],
        "parent_case_content_sha256": pin["case_content_sha256"],
        "parent_release": RELEASE,
        "parameter_constraints": copy.deepcopy(CONSTRAINTS[source]),
        "compatible_protocols": [{"id": protocol, "version": "1.0.0"} for protocol in PROTOCOLS],
        "generator_version": VERSION,
        "variant_type": kind,
        "seed_classification": classification,
        "seed_commitment_sha256": digest,
        "scorer": {"module": pin["scorer"], "evaluator_version": RUNTIME_VERSION,
                   "evaluator_fingerprint": pin["evaluator_fingerprint"]},
        "task": task,
        "answer_contract": _public_contract(parent),
    }
    if classification == "public_dev":
        record["public_seed"] = seed
    case = _materialize(record)
    record["instance_content_sha256"] = _content_hash(case)
    record["scientific_payload_sha256"] = _content_hash(task)
    validate_variant(record)
    return record


def load_variant(path: str | Path) -> dict[str, Any]:
    record = json.loads(Path(path).read_text(encoding="utf-8"))
    if record["seed_classification"] == "public_dev":
        reproduced = generate_variant(record["parent_case_id"], record["public_seed"], record["variant_type"])
        if reproduced != record:
            raise ValueError("public variant does not reproduce from its seed")
    case = validate_variant(record)
    return {**record, "case": case}


def _public_outputs() -> dict[Path, str]:
    plan = json.loads(PUBLIC_PLAN.read_text(encoding="utf-8"))
    if plan["generator_version"] != VERSION:
        raise ValueError("public plan generator version differs")
    outputs: dict[Path, str] = {}
    records = []
    for entry in plan["variants"]:
        record = generate_variant(entry["parent_case_id"], entry["seed"], entry["variant_type"])
        path = PUBLIC_DIR / f"{record['variant_id']}.json"
        if path in outputs:
            raise ValueError("duplicate public variant ID")
        outputs[path] = _json(record)
        records.append(record)
    lines = ["# Public development variants", "", "These questions are public development instances. Internal gold is not rendered here.", ""]
    for record in records:
        lines.extend([f"## {record['variant_id']}", "", f"Parent: {record['parent_case_id']} revision {record['parent_case_revision']}.", "",
                      record["task"]["statement"], ""])
        for question in record["task"]["questions"]:
            lines.append(f"{question['id']}. {question['request']}")
        lines.append("")
    outputs[QUESTION_BANK] = "\n".join(lines).rstrip() + "\n"
    return outputs


def public_check_or_write(*, check: bool) -> None:
    outputs = _public_outputs()
    existing = set(PUBLIC_DIR.glob("*.json")) if PUBLIC_DIR.exists() else set()
    expected = {path for path in outputs if path.suffix == ".json"}
    if check:
        if existing != expected or any(not path.is_file() or path.read_text(encoding="utf-8") != content
                                       for path, content in outputs.items()):
            raise ValueError("public variants are missing, extra, or stale; run generate-public")
        for path in expected:
            load_variant(path)
    else:
        PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
        for stale in existing - expected:
            stale.unlink()
        for path, content in outputs.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")


def _outside_repo(path: Path) -> bool:
    return not path.resolve().is_relative_to(ROOT.resolve())


def generate_private(seed_file: str | Path, output_dir: str | Path) -> list[Path]:
    seed_path, output = Path(seed_file).resolve(), Path(output_dir).resolve()
    if not _outside_repo(seed_path) or not _outside_repo(output):
        raise ValueError("private seed and output paths must both be outside the public repository")
    seed_doc = json.loads(seed_path.read_text(encoding="utf-8"))
    seed = seed_doc["seed"]
    selections = seed_doc["selections"]
    if not isinstance(selections, list) or not selections:
        raise ValueError("private seed selections must be a nonempty list")
    records = [generate_variant(item["parent_case_id"], seed, item["variant_type"], classification="private")
               for item in selections]
    if len({record["variant_id"] for record in records}) != len(records):
        raise ValueError("private selections contain duplicate source/type entries")
    output.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for record in records:
        path = output / f"{record['variant_id']}.json"
        if path.exists():
            raise FileExistsError(f"private variant output already exists: {path}")
        path.write_text(_json(record), encoding="utf-8")
        paths.append(path)
    return paths


def verify_private(path: str | Path, seed_file: str | Path) -> dict[str, Any]:
    """Audit a private instance against a seed kept outside the repository."""
    seed_path = Path(seed_file).resolve()
    if not _outside_repo(seed_path):
        raise ValueError("private seed path must be outside the public repository")
    record = json.loads(Path(path).read_text(encoding="utf-8"))
    if record.get("seed_classification") != "private" or "public_seed" in record:
        raise ValueError("record is not a private variant")
    seed = json.loads(seed_path.read_text(encoding="utf-8"))["seed"]
    reproduced = generate_variant(record["parent_case_id"], seed, record["variant_type"], classification="private")
    if reproduced != record:
        raise ValueError("private variant does not reproduce from supplied seed")
    return load_variant(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("generate-public")
    sub.add_parser("check-public")
    private = sub.add_parser("generate-private")
    private.add_argument("--seed-file", required=True)
    private.add_argument("--output-dir", required=True)
    private_check = sub.add_parser("verify-private")
    private_check.add_argument("--seed-file", required=True)
    private_check.add_argument("--variant", required=True)
    args = parser.parse_args()
    if args.action == "generate-public":
        public_check_or_write(check=False)
        print(f"Generated {len(list(PUBLIC_DIR.glob('*.json')))} public development variants")
    elif args.action == "check-public":
        public_check_or_write(check=True)
        print(f"Verified {len(list(PUBLIC_DIR.glob('*.json')))} reproducible public development variants")
    elif args.action == "generate-private":
        paths = generate_private(args.seed_file, args.output_dir)
        print(f"Generated {len(paths)} private instances outside the public repository")
    else:
        record = verify_private(args.variant, args.seed_file)
        print(f"Verified private instance {record['variant_id']} against external seed")


if __name__ == "__main__":
    main()
