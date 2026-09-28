"""Neutral public answer hints for vNext cases, independent of rc1 payloads."""

from __future__ import annotations

import hashlib
from typing import Any

from tools.protocols import canonical_bytes, public_payload as rc1_public_payload


SHAPES = {
    "SEED-2-1": {"q3": "Object with waist_radius_factor as a dimensionless Quantity {value, unit}."},
    "SEED-3-1": {"q3": "Object with image_type (real or virtual) and orientation (inverted or upright)."},
    "SEED-3-7": {"q3": "Object with depth_of_focus_trend (decreases, unchanged, or increases)."},
    "SEED-5-5": {"q2": "Object with detector_field_response_order as a dimensionless Quantity and frequency_component_source (self_term, interference_cross_term, or optical_carrier).",
                 "q3": "Object with ideal_cross_term as a Boolean."},
}


def public_payload(case: dict[str, Any]) -> dict[str, Any]:
    payload = rc1_public_payload(case)
    if case["case_id"] in SHAPES and case.get("benchmark_release") == "0.2.0-rc1":
        payload["answer_contract"]["method_shape"] = SHAPES[case["case_id"]]
    return payload


def payload_sha256(case: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_bytes(public_payload(case))).hexdigest()
