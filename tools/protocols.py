"""Versioned evaluation environments and matched scientific-payload checks."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_DIR = ROOT / "benchmark" / "protocols"
PROTOCOL_IDS = (
    "closed_book", "case_assisted", "tool_assisted", "case_and_tool_assisted"
)
PUBLIC_CONTRACT_FIELDS = (
    "format", "required_result_paths", "quantity_shape",
    "permit_additional_explanation",
)
# Legacy method_shape text sometimes states the answer itself. These shapes
# describe only the JSON structure needed by the autonomous scorer.
PUBLIC_METHOD_SHAPES = {
    "SEED-1-1": {"q3": "Object geometry_change with variable (screen_distance or mirror_rotation), held_fixed (the other variable), and scale (Quantity {value, unit: '1'} giving the dimensionless new/old ratio)."},
    "SEED-1-7": {"q3": "Boolean linear_rotation_rule_applies."},
    "SEED-2-2": {"q2": "Object with keplerian and galilean, each containing signed input_focal_length and output_focal_length quantities.",
                 "q3": "Object with keplerian_real_internal_focus and galilean_real_internal_focus booleans."},
    "SEED-2-4": {"q3": "Object with a cost field naming one physically valid tradeoff; benefit is optional."},
    "SEED-3-1": {"q3": "Object with image_type (real or virtual) and orientation (inverted or upright)."},
}
MATCHED_FIELDS = (
    "case_id", "case_revision", "scientific_payload_sha256", "scorer_id",
    "result_schema_version", "agent_identity",
)
OPTIONAL_MATCHED_FIELDS = ("variant_id", "scorer_fingerprint")


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def public_payload(case: dict[str, Any]) -> dict[str, Any]:
    """Expose the task and neutral structural answer hints, never gold or validation.

    The same function supplies every protocol. Scorer-specific method shapes are
    intentionally excluded because several legacy contracts disclose solution
    choices. The runner records the hash of precisely this returned object.
    """
    contract = case.get("answer_contract", {})
    exposed = {
        "case_id": case["case_id"],
        "case_revision": str(case["case_revision"]),
        "task": case["task"],
        "answer_contract": {key: contract[key] for key in PUBLIC_CONTRACT_FIELDS
                            if key in contract},
    }
    if case["case_id"] in PUBLIC_METHOD_SHAPES:
        exposed["answer_contract"]["method_shape"] = PUBLIC_METHOD_SHAPES[case["case_id"]]
    return exposed


def payload_sha256(case: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_bytes(public_payload(case))).hexdigest()


def load_protocol(protocol_id: str) -> dict[str, Any]:
    if protocol_id not in PROTOCOL_IDS:
        raise ValueError(f"unknown protocol: {protocol_id}")
    path = PROTOCOL_DIR / f"{protocol_id}.v1.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    validate_protocol(manifest)
    if manifest["protocol_id"] != protocol_id:
        raise ValueError(f"protocol ID mismatch: {path}")
    return manifest


def validate_protocol(manifest: dict[str, Any]) -> None:
    schema = json.loads((PROTOCOL_DIR / "protocol.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    errors = sorted(Draft202012Validator(schema).iter_errors(manifest),
                    key=lambda error: list(map(str, error.path)))
    if errors:
        raise ValueError("invalid protocol manifest: " + "; ".join(error.message for error in errors))
    library = manifest["case_library_access"]["enabled"]
    tools = bool(manifest["tool_policy"]["allowed_tools"])
    expected = {
        "closed_book": (False, False),
        "case_assisted": (True, False),
        "tool_assisted": (False, True),
        "case_and_tool_assisted": (True, True),
    }[manifest["protocol_id"]]
    if (library, tools) != expected:
        raise ValueError("protocol permissions disagree with protocol ID")
    if library != (manifest["retrieval_policy"]["max_items"] > 0):
        raise ValueError("retrieval policy disagrees with library access")
    expected_snapshot = "optics-examples-v1" if library else None
    if manifest["case_library_access"]["snapshot_id"] != expected_snapshot:
        raise ValueError("library snapshot does not match v1 access policy")
    expected_profile = "generic_computation_v0.1" if tools else None
    if manifest["tool_policy"]["profile_id"] != expected_profile:
        raise ValueError("tool profile does not match v1 access policy")
    if tools and manifest["tool_policy"]["allowed_tools"] != ["calculator", "unit_convert"]:
        raise ValueError("v1 tool profile must list exactly calculator and unit_convert")
    retrieval = manifest["retrieval_policy"]
    context = manifest["context_injection_policy"]
    if retrieval["method"] != ("lexical_v1" if library else "none"):
        raise ValueError("retrieval method disagrees with library access")
    if context["mode"] != ("retrieved_items_only" if library else "none"):
        raise ValueError("context injection disagrees with library access")
    if context["max_items"] != retrieval["max_items"] or context["max_tokens"] != retrieval["max_context_tokens"]:
        raise ValueError("context injection limits disagree with retrieval limits")


def check_matched_runs(descriptors: list[dict[str, Any]]) -> list[str]:
    """Check comparability of one case/variant and agent across protocols.

    Any intentionally varied agent or variant belongs in a separate group.
    The scientific payload must be computed before protocol-specific context is
    added. The checker also catches duplicate protocols and incomplete metadata.
    """
    if len(descriptors) < 2:
        return ["matched comparison requires at least two run descriptors"]
    issues: list[str] = []
    for index, row in enumerate(descriptors):
        for field in MATCHED_FIELDS + ("protocol_id", "protocol_version"):
            if row.get(field) in (None, ""):
                issues.append(f"descriptor {index}: missing {field}")
        protocol_id = row.get("protocol_id")
        if protocol_id not in PROTOCOL_IDS:
            issues.append(f"descriptor {index}: unknown protocol_id {protocol_id}")
        elif row.get("protocol_version") != load_protocol(protocol_id)["version"]:
            issues.append(f"descriptor {index}: protocol version mismatch")
    first = descriptors[0]
    for index, row in enumerate(descriptors[1:], 1):
        for field in MATCHED_FIELDS + OPTIONAL_MATCHED_FIELDS:
            if row.get(field) != first.get(field):
                issues.append(f"descriptor {index}: {field} differs from descriptor 0")
    ids = [row.get("protocol_id") for row in descriptors]
    if len(ids) != len(set(ids)):
        issues.append("matched comparison repeats a protocol")
    return issues


def validate_all() -> list[str]:
    issues: list[str] = []
    reference = None
    frozen_fields = (
        "scientific_prompt_source", "answer_format_contract", "retry_policy",
        "timeout_policy", "system_scaffold", "logging_requirements",
    )
    for protocol_id in PROTOCOL_IDS:
        try:
            manifest = load_protocol(protocol_id)
        except (ValueError, OSError, json.JSONDecodeError) as exc:
            issues.append(f"{protocol_id}: {exc}")
            continue
        if reference is None:
            reference = manifest
        else:
            for field in frozen_fields:
                if manifest[field] != reference[field]:
                    issues.append(f"{protocol_id}: matched field {field} differs")
        if manifest["network_policy"]["external_access"]:
            issues.append(f"{protocol_id}: external network access is not allowed in v1")
    return issues


if __name__ == "__main__":
    import sys
    found = validate_all()
    for issue in found:
        print(issue)
    if not found:
        print(f"Validated {len(PROTOCOL_IDS)} protocol manifests")
    sys.exit(bool(found))
