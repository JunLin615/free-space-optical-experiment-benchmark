"""Explicit v0.2 answer-unit aliases; the rc1 evaluator remains untouched.

Only complete Quantity objects are normalized. Unknown spellings remain unknown
and are rejected by the downstream dimensional validator. An alias never changes
the physical dimension implied by a unit.
"""

from __future__ import annotations

from copy import deepcopy
import math
from typing import Any


VERSION = "unit-normalization-0.2.0"

# Alias -> (canonical unit understood by the rc1 numerical oracle, multiplier).
# The list is deliberately finite and case-sensitive. In particular, a bare
# wavelength symbol is not converted without a reference wavelength.
ALIASES: dict[str, tuple[str, float]] = {
    "dimensionless": ("1", 1.0),
    "unitless": ("1", 1.0),
    "%": ("1", 0.01),
    "percent": ("1", 0.01),
    "metre": ("m", 1.0),
    "meter": ("m", 1.0),
    "centimeter": ("m", 0.01),
    "centimetre": ("m", 0.01),
    "cm": ("m", 0.01),
    "millimeter": ("mm", 1.0),
    "millimetre": ("mm", 1.0),
    "micrometer": ("um", 1.0),
    "micrometre": ("um", 1.0),
    "μm": ("um", 1.0),
    "nanometer": ("nm", 1.0),
    "nanometre": ("nm", 1.0),
    "millisecond": ("s", 0.001),
    "ms": ("s", 0.001),
    "microsecond": ("s", 1e-6),
    "us": ("s", 1e-6),
    "µs": ("s", 1e-6),
    "μs": ("s", 1e-6),
    "nanosecond": ("s", 1e-9),
    "ns": ("s", 1e-9),
    "picosecond": ("ps", 1.0),
    "femtosecond": ("fs", 1.0),
    "degree": ("deg", 1.0),
    "degrees": ("deg", 1.0),
    "radian": ("rad", 1.0),
    "radians": ("rad", 1.0),
    "hertz": ("Hz", 1.0),
    "kilohertz": ("kHz", 1.0),
    "megahertz": ("MHz", 1.0),
    "gigahertz": ("GHz", 1.0),
    "THz": ("GHz", 1000.0),
}


def normalize_answer_units(answer: Any) -> Any:
    """Return a detached answer with approved Quantity aliases canonicalized."""
    if isinstance(answer, list):
        return [normalize_answer_units(item) for item in answer]
    if not isinstance(answer, dict):
        return deepcopy(answer)
    result = {key: normalize_answer_units(value) for key, value in answer.items()}
    if set(result) >= {"value", "unit"} and isinstance(result["unit"], str):
        alias = ALIASES.get(result["unit"])
        value = result["value"]
        if alias is not None and isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value):
            canonical, factor = alias
            result["value"] = float(value) * factor
            result["unit"] = canonical
    return result
