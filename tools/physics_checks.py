"""Small, independent numerical optics checks for the pilot cases.

These checks verify a candidate's typed numerical claim against equations and
case givens. They are not a complete evaluator for design or diagnosis tasks.
Only explicitly supported units and physical models are accepted.
"""

from __future__ import annotations

import math
from typing import Any, Callable


SPEED_OF_LIGHT_M_PER_S = 299_792_458.0

# Unit -> (physical dimension, multiplier to the SI base unit).
UNITS: dict[str, tuple[str, float]] = {
    "m": ("length", 1.0),
    "mm": ("length", 1e-3),
    "um": ("length", 1e-6),
    "µm": ("length", 1e-6),
    "nm": ("length", 1e-9),
    "s": ("time", 1.0),
    "ps": ("time", 1e-12),
    "fs": ("time", 1e-15),
    "rad": ("angle", 1.0),
    "deg": ("angle", math.pi / 180.0),
    "1": ("dimensionless", 1.0),
    "Hz": ("frequency", 1.0),
    "kHz": ("frequency", 1e3),
    "MHz": ("frequency", 1e6),
    "GHz": ("frequency", 1e9),
}


class PhysicsCheckError(ValueError):
    """An oracle, input, unit, or candidate-contract error."""


def to_si(quantity: dict[str, Any], expected_dimension: str | None = None) -> float:
    """Convert a scalar quantity to SI, rejecting unknown or mismatched units."""
    if not isinstance(quantity, dict) or "value" not in quantity or "unit" not in quantity:
        raise PhysicsCheckError("quantity must contain value and unit")
    unit = quantity["unit"]
    if unit not in UNITS:
        raise PhysicsCheckError(f"unsupported unit: {unit!r}")
    dimension, factor = UNITS[unit]
    if expected_dimension is not None and dimension != expected_dimension:
        raise PhysicsCheckError(f"expected {expected_dimension}, received {dimension}")
    value = quantity["value"]
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise PhysicsCheckError("quantity value must be a finite number")
    return float(value) * factor


def _givens(case: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for item in case["task"].get("givens", []):
        symbol = item.get("symbol")
        if symbol in result:
            raise PhysicsCheckError(f"duplicate given symbol: {symbol}")
        if symbol:
            result[symbol] = item
    return result


def _given(case: dict[str, Any], symbol: str, dimension: str) -> float:
    try:
        quantity = _givens(case)[symbol]
    except KeyError as exc:
        raise PhysicsCheckError(f"missing given symbol: {symbol}") from exc
    return to_si(quantity, dimension)


def _mirror_angle(case: dict[str, Any]) -> tuple[float, str]:
    return 2 * _given(case, "mirror_rotation", "angle"), "angle"


def _mirror_spot_shift(case: dict[str, Any]) -> tuple[float, str]:
    rotation = _given(case, "mirror_rotation", "angle")
    distance = _given(case, "screen_distance", "length")
    return distance * math.tan(2 * rotation), "length"


def _folded_delay_path(case: dict[str, Any]) -> tuple[float, str]:
    return 2 * _given(case, "stage_displacement", "length"), "length"


def _folded_delay_time(case: dict[str, Any]) -> tuple[float, str]:
    path, _ = _folded_delay_path(case)
    return path / SPEED_OF_LIGHT_M_PER_S, "time"


def _folded_delay_stage_for_target(case: dict[str, Any]) -> tuple[float, str]:
    delay = _given(case, "target_delay", "time")
    return SPEED_OF_LIGHT_M_PER_S * delay / 2, "length"


def _gaussian_focus_radius(case: dict[str, Any]) -> tuple[float, str]:
    wavelength = _given(case, "wavelength", "length")
    focal_length = _given(case, "focal_length", "length")
    incident_radius = _given(case, "incident_radius", "length")
    if wavelength <= 0 or focal_length <= 0 or incident_radius <= 0:
        raise PhysicsCheckError("Gaussian focus inputs must be positive")
    return wavelength * focal_length / (math.pi * incident_radius), "length"


def _michelson_fringe_count(case: dict[str, Any]) -> tuple[float, str]:
    motion_in_wavelengths = _given(case, "mirror_displacement_wavelengths", "dimensionless")
    return 2 * motion_in_wavelengths, "dimensionless"


def _half_wave_axis(case: dict[str, Any]) -> tuple[float, str]:
    incident = _given(case, "incident_axis", "angle")
    fast_axis = _given(case, "fast_axis", "angle")
    # Linear-polarization axes are equivalent modulo pi.
    return (2 * fast_axis - incident) % math.pi, "angle"


def _half_wave_relative_rotation_magnitude(case: dict[str, Any]) -> tuple[float, str]:
    separation = _given(case, "input_to_fast_axis_angle", "angle")
    return 2 * abs(separation), "angle"


def _half_wave_plate_rotation_effect(case: dict[str, Any]) -> tuple[float, str]:
    rotation = _given(case, "plate_rotation", "angle")
    return 2 * abs(rotation), "angle"


def _afocal_expansion(case: dict[str, Any]) -> tuple[float, str]:
    incident = _given(case, "input_diameter", "length")
    output = _given(case, "output_diameter", "length")
    if incident <= 0 or output <= 0:
        raise PhysicsCheckError("beam diameters must be positive")
    return output / incident, "dimensionless"


def _rayleigh_range_ratio(case: dict[str, Any]) -> tuple[float, str]:
    initial = _given(case, "initial_waist_radius", "length")
    final = _given(case, "final_waist_radius", "length")
    if initial <= 0 or final <= 0:
        raise PhysicsCheckError("waist radii must be positive")
    return (final / initial) ** 2, "dimensionless"


def _divergence_ratio(case: dict[str, Any]) -> tuple[float, str]:
    initial = _given(case, "initial_waist_radius", "length")
    final = _given(case, "final_waist_radius", "length")
    if initial <= 0 or final <= 0:
        raise PhysicsCheckError("waist radii must be positive")
    return initial / final, "dimensionless"


def _thin_lens_image_distance_ratio(case: dict[str, Any]) -> tuple[float, str]:
    object_ratio = _given(case, "object_distance_in_focal_lengths", "dimensionless")
    if object_ratio <= 1:
        raise PhysicsCheckError("real conjugate needs object distance greater than f")
    return object_ratio / (object_ratio - 1), "dimensionless"


def _thin_lens_magnification(case: dict[str, Any]) -> tuple[float, str]:
    image_ratio, _ = _thin_lens_image_distance_ratio(case)
    object_ratio = _given(case, "object_distance_in_focal_lengths", "dimensionless")
    return -image_ratio / object_ratio, "dimensionless"


def _rayleigh_lateral_resolution(case: dict[str, Any]) -> tuple[float, str]:
    wavelength = _given(case, "wavelength", "length")
    na = _given(case, "numerical_aperture", "dimensionless")
    if wavelength <= 0 or not 0 < na <= 1:
        raise PhysicsCheckError("wavelength or numerical aperture out of range")
    return 0.61 * wavelength / na, "length"


def _heterodyne_beat(case: dict[str, Any]) -> tuple[float, str]:
    offset = _given(case, "lo_frequency_offset", "frequency")
    if offset == 0:
        raise PhysicsCheckError("heterodyne frequency offset must be nonzero")
    return abs(offset), "frequency"


REGISTRY: dict[str, Callable[[dict[str, Any]], tuple[float, str]]] = {
    "mirror_angle": _mirror_angle,
    "mirror_spot_shift": _mirror_spot_shift,
    "folded_delay_path": _folded_delay_path,
    "folded_delay_time": _folded_delay_time,
    "folded_delay_stage_for_target": _folded_delay_stage_for_target,
    "gaussian_focus_radius": _gaussian_focus_radius,
    "michelson_fringe_count": _michelson_fringe_count,
    "half_wave_axis": _half_wave_axis,
    "half_wave_relative_rotation_magnitude": _half_wave_relative_rotation_magnitude,
    "half_wave_plate_rotation_effect": _half_wave_plate_rotation_effect,
    "afocal_expansion": _afocal_expansion,
    "rayleigh_range_ratio": _rayleigh_range_ratio,
    "divergence_ratio": _divergence_ratio,
    "thin_lens_image_distance_ratio": _thin_lens_image_distance_ratio,
    "thin_lens_magnification": _thin_lens_magnification,
    "rayleigh_lateral_resolution": _rayleigh_lateral_resolution,
    "heterodyne_beat": _heterodyne_beat,
}


def expected_si(case: dict[str, Any], validator_id: str) -> tuple[float, str]:
    """Compute an independent expected value from the case's typed givens."""
    try:
        return REGISTRY[validator_id](case)
    except KeyError as exc:
        raise PhysicsCheckError(f"unknown physics validator: {validator_id}") from exc


def _tolerance_si(check: dict[str, Any], expected: float, dimension: str) -> float:
    absolute = check.get("absolute_tolerance")
    relative = check.get("relative_tolerance", 0.0)
    abs_si = to_si(absolute, dimension) if absolute is not None else 0.0
    if relative < 0 or abs_si < 0:
        raise PhysicsCheckError("negative numerical tolerance")
    comparator = check["comparator"]
    if comparator == "absolute_inclusive":
        if absolute is None:
            raise PhysicsCheckError("absolute comparator lacks absolute tolerance")
        return abs_si
    if comparator == "relative_inclusive":
        if "relative_tolerance" not in check:
            raise PhysicsCheckError("relative comparator lacks relative tolerance")
        return relative * abs(expected)
    if comparator == "max_abs_or_relative_inclusive":
        return max(abs_si, relative * abs(expected))
    raise PhysicsCheckError(f"unsupported comparator for this proof of concept: {comparator}")


def check_numeric_claim(
    case: dict[str, Any], check: dict[str, Any], candidate_quantity: dict[str, Any]
) -> dict[str, Any]:
    """Return a serializable verdict; never let a bad gold value grade an agent.

    The candidate and authored gold are both compared with an independently
    calculated reference. A mismatched gold specification is a validator error,
    not an agent error.
    """
    validator_id = check.get("validator_id")
    if not validator_id:
        raise PhysicsCheckError("numerical check has no executable validator_id")
    expected, dimension = expected_si(case, validator_id)
    gold = to_si(check["reference"], dimension)
    tolerance = _tolerance_si(check, expected, dimension)
    if abs(gold - expected) > tolerance:
        return {
            "status": "validator_error",
            "check_id": check["id"],
            "validator_id": validator_id,
            "reason": "authored gold disagrees with independent equation",
        }
    try:
        candidate = to_si(candidate_quantity, dimension)
    except PhysicsCheckError as exc:
        return {
            "status": "invalid_contract",
            "check_id": check["id"],
            "validator_id": validator_id,
            "reason": str(exc),
        }
    return {
        "status": "pass" if abs(candidate - expected) <= tolerance else "fail",
        "check_id": check["id"],
        "validator_id": validator_id,
        "difference_si": candidate - expected,
        "tolerance_si": tolerance,
    }


def _at_path(answer: dict[str, Any], path: str) -> Any:
    current: Any = answer
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            raise KeyError(path)
        current = current[part]
    return current


def check_case_numeric_claims(case: dict[str, Any], answer: dict[str, Any]) -> list[dict[str, Any]]:
    """Score only pilot criteria with registered physics validators."""
    verdicts: list[dict[str, Any]] = []
    for check in case["gold"].get("numerical_checks", []):
        if not check.get("validator_id"):
            continue
        try:
            candidate = _at_path(answer, check["answer_path"])
        except KeyError:
            verdicts.append({"status": "missing_claim", "check_id": check["id"]})
            continue
        verdicts.append(check_numeric_claim(case, check, candidate))
    return verdicts
