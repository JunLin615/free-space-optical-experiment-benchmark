"""Bounded private variants for independently qualified vNext families.

The stored record contains the public task and commitments, never the seed or
gold. Reconstruction recomputes all numerical references from typed givens.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import random
from typing import Any

from tools.physics_checks import expected_si, to_si
from tools.scoring_runtime import ROOT, _content_hash
from tools.validate_cases import load_case, semantic_issues
from tools.vnext.scoring_runtime import SCORERS, _evaluator_fingerprint, evaluate_case, load_scored_case
from tools.vnext.protocols import payload_sha256


VERSION = "0.2.0"
RELEASE = "0.2.0-rc1"
SUPPORTED = ("SEED-2-1", "SEED-3-1", "SEED-3-7", "SEED-5-5")
TYPES = ("parameter", "structural_unit")
CONSTRAINTS = {
    "SEED-2-1": {"wavelength_nm": [480, 650], "focal_length_mm": [80, 120], "incident_radius_mm": [0.8, 1.2]},
    "SEED-3-1": {"object_distance_in_focal_lengths": [1.5, 4.0]},
    "SEED-3-7": {"wavelength_nm": [550, 633], "numerical_aperture": [0.4, 0.55]},
    "SEED-5-5": {"lo_frequency_offset_MHz": [20, 120]},
}


def _digest(source: str, kind: str, seed: str) -> str:
    return hashlib.sha256(f"vnext:{VERSION}:{source}:{kind}:{seed}".encode()).hexdigest()


def _parent(source: str) -> tuple[dict[str, Any], dict[str, Any]]:
    if source not in SUPPORTED:
        raise ValueError(f"unsupported vNext source: {source}")
    parent = load_scored_case(source)
    release = ROOT / "benchmark" / "releases" / f"{RELEASE}.json"
    manifest = json.loads(release.read_text(encoding="utf-8"))
    pin = manifest["cases"].get(source)
    if not pin or pin["status"] != "release_verified":
        raise ValueError(f"source is not pinned as release verified: {source}")
    if (pin["case_revision"] != parent["case_revision"] or
            pin["case_content_sha256"] != _content_hash(parent) or
            pin["evaluator_fingerprint"] != _evaluator_fingerprint(parent) or
            pin["scorer"] != SCORERS[source]):
        raise ValueError(f"stale vNext parent pin: {source}")
    return parent, pin


def _given(task: dict[str, Any], symbol: str) -> dict[str, Any]:
    return next(item for item in task["givens"] if item.get("symbol") == symbol)


def _task(source: str, kind: str, seed: str, parent: dict[str, Any]) -> dict[str, Any]:
    rng = random.Random(int(_digest(source, kind, seed), 16))
    task = deepcopy(parent["task"])
    if source == "SEED-2-1":
        wavelength = rng.choice((488, 532, 633))
        focal = rng.choice((80, 100, 120))
        radius = rng.choice((0.8, 1.0, 1.2))
        if kind == "structural_unit":
            _given(task, "wavelength").update(value=wavelength / 1000, unit="um")
            _given(task, "focal_length").update(value=focal / 1000, unit="m")
        else:
            _given(task, "wavelength").update(value=wavelength, unit="nm")
            _given(task, "focal_length").update(value=focal, unit="mm")
        _given(task, "incident_radius").update(value=radius, unit="mm")
        task["statement"] = (f"An approximately collimated Gaussian beam at {wavelength} nm enters a thin lens of focal length {focal} mm. "
                             f"Its 1/e² intensity radius at the lens is about {radius:g} mm, and the lens aperture is sufficiently large. "
                             "Use the ideal diffraction-limited Gaussian relation for the numerical estimate.")
    elif source == "SEED-3-1":
        ratio = rng.choice((1.5, 2.0, 2.5, 3.0, 4.0))
        _given(task, "object_distance_in_focal_lengths").update(value=ratio, unit="1")
        task["statement"] = f"An object is placed at a distance {ratio:g}f in front of an ideal positive thin lens of focal length f."
        if kind == "structural_unit":
            task["coordinate_convention"] = (
                "Use s>0 for the incident-side object and s'>0 for a transmitted-side real image; "
                "report image position as the signed dimensionless ratio s'/f."
            )
            task["questions"][0]["request"] = "Solve the lens conjugate for signed s'/f under the stated coordinate convention."
        else:
            task["questions"][0]["request"] = "Where is the image formed? Express its distance behind the lens in units of f."
    elif source == "SEED-3-7":
        wavelength = rng.choice((550, 589, 633))
        na = rng.choice((0.4, 0.45, 0.5, 0.55))
        _given(task, "wavelength").update(value=wavelength if kind == "parameter" else wavelength / 1000,
                                           unit="nm" if kind == "parameter" else "um")
        _given(task, "numerical_aperture").update(value=na, unit="1")
        task["statement"] = (f"A microscope objective images at wavelength {wavelength} nm with numerical aperture {na:g}. "
                             "Neglect aberrations and use the Rayleigh lateral-resolution estimate.")
    else:
        offset = rng.choice((20, 40, 60, 100, 120))
        _given(task, "lo_frequency_offset").update(value=offset if kind == "parameter" else offset / 1000,
                                                    unit="MHz" if kind == "parameter" else "GHz")
        task["statement"] = (f"Signal light has optical frequency f0. A local-oscillator beam has frequency f0 + {offset} MHz. "
                             "The beams have matching polarization and good spatial overlap on a photodetector fast enough to resolve their beat.")
    return task


def _materialize(record: dict[str, Any]) -> dict[str, Any]:
    parent, _ = _parent(record["parent_case_id"])
    case = deepcopy(parent)
    case["task"] = deepcopy(record["task"])
    case["answer_contract"] = deepcopy(record["answer_contract"])
    case["split"] = "hidden_eval" if record["seed_classification"] == "private" else "public_dev"
    case["benchmark_release"] = RELEASE
    case["validation_status"] = "challenged"
    for check in case["gold"].get("numerical_checks", []):
        expected, dimension = expected_si(case, check["validator_id"])
        original_unit = check["reference"]["unit"]
        from tools.physics_checks import UNITS
        if UNITS[original_unit][0] != dimension:
            raise ValueError("reference dimension differs from independent equation")
        check["reference"]["value"] = round(expected / UNITS[original_unit][1], 10)
        if case["case_id"] == "SEED-2-1" and check["id"] == "n_waist":
            check["absolute_tolerance"]["value"] = round(.2 * expected / UNITS[original_unit][1], 10)
            check["tolerance_rationale"] = (
                "Twenty percent of this variant's recomputed ideal waist is an inclusive "
                "one-significant-figure reporting band, not an instrument uncertainty. "
                "The separate q2 choice scores the order scale."
            )
    return case


def _expected_answer(case: dict[str, Any]) -> dict[str, Any]:
    checks = {item["id"]: deepcopy(item["reference"]) for item in case["gold"]["numerical_checks"]}
    source = case["case_id"]
    if source == "SEED-2-1":
        return {"answers": {"q1": {"waist_radius": checks["n_waist"]},
                            "q2": {"closest_scale": {"value": 10, "unit": "um"}},
                            "q3": {"waist_radius_factor": {"value": .5, "unit": "1"}}}}
    if source == "SEED-3-1":
        return {"answers": {"q1": {"image_distance_in_focal_lengths": checks["n_image_distance"]},
                            "q2": {"lateral_magnification": checks["n_magnification"]},
                            "q3": {"image_type": "real", "orientation": "inverted"}}}
    if source == "SEED-3-7":
        return {"answers": {"q1": {"resolution_um": checks["n_rayleigh"]},
                            "q2": {"closest_scale": {"value": 1, "unit": "um"}},
                            "q3": {"depth_of_focus_trend": "decreases"}}}
    return {"answers": {"q1": {"beat_frequency": checks["n_result"]},
                        "q2": {"detector_field_response_order": {"value": 2, "unit": "1"},
                               "frequency_component_source": "interference_cross_term"},
                        "q3": {"ideal_cross_term": False}}}


def validate_variant(record: dict[str, Any]) -> dict[str, Any]:
    if record.get("variant_schema_version") != VERSION or record.get("generator_version") != VERSION:
        raise ValueError("unsupported variant schema/generator version")
    if record.get("variant_type") not in TYPES or record.get("seed_classification") not in {"private", "public_dev"}:
        raise ValueError("unsupported variant type/classification")
    if "gold" in record or "case" in record or (record["seed_classification"] == "private" and "public_seed" in record):
        raise ValueError("variant record exposes gold, a full case, or a private seed")
    parent, pin = _parent(record["parent_case_id"])
    if record.get("parent_release") != RELEASE or record.get("parent_case_revision") != pin["case_revision"] or record.get("parent_case_content_sha256") != pin["case_content_sha256"]:
        raise ValueError("stale variant source lineage")
    if record.get("answer_contract") != parent["answer_contract"] or record.get("parameter_constraints") != CONSTRAINTS[record["parent_case_id"]]:
        raise ValueError("variant contract or constraints differ from generator")
    if record.get("scorer") != {"module": pin["scorer"], "evaluator_version": pin["evaluator_version"],
                                "evaluator_fingerprint": pin["evaluator_fingerprint"]}:
        raise ValueError("scorer compatibility differs from release")
    case = _materialize(record)
    source = case["case_id"]
    givens = {g["symbol"]: g for g in case["task"].get("givens", []) if "symbol" in g}
    if source == "SEED-2-1":
        wavelength, focal, radius = (to_si(givens[k], d) for k, d in (("wavelength", "length"), ("focal_length", "length"), ("incident_radius", "length")))
        if not (480e-9 <= wavelength <= 650e-9 and .08 <= focal <= .12 and .0008 <= radius <= .0012):
            raise ValueError("Gaussian focus parameter outside tested range")
        independent = wavelength * focal / (math.pi * radius)
        if not 10e-6 <= independent <= 35e-6:
            raise ValueError("Gaussian variant changes offered scale choice")
    elif source == "SEED-3-1":
        ratio = to_si(givens["object_distance_in_focal_lengths"], "dimensionless")
        if not 1.5 <= ratio <= 4:
            raise ValueError("thin-lens object ratio outside tested range")
    elif source == "SEED-3-7":
        wavelength, na = to_si(givens["wavelength"], "length"), to_si(givens["numerical_aperture"], "dimensionless")
        if not 550e-9 <= wavelength <= 633e-9 or not .4 <= na <= .55:
            raise ValueError("Rayleigh parameters outside tested range")
        if not .55e-6 < .61 * wavelength / na <= 1e-6:
            raise ValueError("Rayleigh variant changes offered scale choice")
    else:
        offset = to_si(givens["lo_frequency_offset"], "frequency")
        if not 20e6 <= offset <= 120e6:
            raise ValueError("heterodyne offset outside tested range")
    if semantic_issues(case):
        raise ValueError("variant fails canonical semantic validation")
    if _content_hash(case) != record.get("instance_content_sha256") or payload_sha256(case) != record.get("scientific_payload_sha256"):
        raise ValueError("variant content commitment mismatch")
    result = evaluate_case(case, _expected_answer(case))
    if result["scores"]["capped_total"] != 1.0 or result["failure_mode"] != "none":
        raise ValueError("vNext scorer cannot solve independently reconstructed variant")
    return case


def generate_variant(source: str, seed: str, kind: str, *, classification: str = "private") -> dict[str, Any]:
    if source not in SUPPORTED or kind not in TYPES or classification not in {"private", "public_dev"}:
        raise ValueError("invalid generator request")
    if not isinstance(seed, str) or not seed or (classification == "private" and
            (len(seed) < 32 or any(c not in "0123456789abcdefABCDEF" for c in seed))):
        raise ValueError("private generator seed requires at least 128 hexadecimal bits")
    parent, pin = _parent(source)
    digest = _digest(source, kind, seed)
    record = {"variant_schema_version": VERSION,
              "variant_id": f"VAR-{source}-{('P' if kind == 'parameter' else 'U')}-{digest[:12]}",
              "parent_case_id": source, "parent_case_revision": pin["case_revision"],
              "parent_case_content_sha256": pin["case_content_sha256"], "parent_release": RELEASE,
              "parameter_constraints": deepcopy(CONSTRAINTS[source]),
              "compatible_protocols": [{"id": item, "version": "1.0.0"} for item in
                                       ("closed_book", "case_assisted", "tool_assisted", "case_and_tool_assisted")],
              "generator_version": VERSION, "variant_type": kind,
              "seed_classification": classification, "seed_commitment_sha256": digest,
              "scorer": {"module": pin["scorer"], "evaluator_version": pin["evaluator_version"],
                         "evaluator_fingerprint": pin["evaluator_fingerprint"]},
              "task": _task(source, kind, seed, parent), "answer_contract": deepcopy(parent["answer_contract"])}
    if classification == "public_dev":
        record["public_seed"] = seed
    case = _materialize(record)
    record["instance_content_sha256"] = _content_hash(case)
    record["scientific_payload_sha256"] = payload_sha256(case)
    validate_variant(record)
    return record


def load_variant(path: str | Path) -> dict[str, Any]:
    record = json.loads(Path(path).read_text(encoding="utf-8"))
    if record["seed_classification"] == "public_dev":
        if generate_variant(record["parent_case_id"], record["public_seed"], record["variant_type"], classification="public_dev") != record:
            raise ValueError("public variant differs from seed reproduction")
    case = validate_variant(record)
    return {**record, "case": case}
