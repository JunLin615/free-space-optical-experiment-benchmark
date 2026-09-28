"""Small runner-mediated computation tools; no shell, files, or network."""

from __future__ import annotations

import ast
import math
import time
from typing import Any


PROFILE_ID = "generic_computation_v0.1"
ALLOWED_TOOLS = ("calculator", "unit_convert")
UNIT_FACTORS = {
    "m": ("length", 1.0), "mm": ("length", 1e-3),
    "um": ("length", 1e-6), "µm": ("length", 1e-6), "nm": ("length", 1e-9),
    "s": ("time", 1.0), "ps": ("time", 1e-12), "fs": ("time", 1e-15),
    "rad": ("angle", 1.0), "deg": ("angle", math.pi / 180),
    "Hz": ("frequency", 1.0), "kHz": ("frequency", 1e3),
    "MHz": ("frequency", 1e6), "GHz": ("frequency", 1e9),
    "1": ("dimensionless", 1.0),
}
CONSTANTS = {"pi": math.pi, "e": math.e, "c": 299_792_458.0}
FUNCTIONS = {name: getattr(math, name) for name in
             ("sqrt", "sin", "cos", "tan", "asin", "acos", "atan", "log", "log10", "exp", "floor", "ceil")}


class ToolCallError(ValueError):
    """A candidate supplied malformed or out-of-profile tool arguments."""


def _arithmetic(node: ast.AST, depth: int = 0) -> float:
    if depth > 24:
        raise ToolCallError("expression too deep")
    if isinstance(node, ast.Expression):
        return _arithmetic(node.body, depth + 1)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
        value = float(node.value)
    elif isinstance(node, ast.Name) and node.id in CONSTANTS:
        value = CONSTANTS[node.id]
    elif isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        part = _arithmetic(node.operand, depth + 1)
        value = part if isinstance(node.op, ast.UAdd) else -part
    elif isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow)):
        left, right = _arithmetic(node.left, depth + 1), _arithmetic(node.right, depth + 1)
        if isinstance(node.op, ast.Add):
            value = left + right
        elif isinstance(node.op, ast.Sub):
            value = left - right
        elif isinstance(node.op, ast.Mult):
            value = left * right
        elif isinstance(node.op, ast.Div):
            value = left / right
        else:
            if abs(right) > 20 or abs(left) > 1e12:
                raise ToolCallError("exponent outside calculator limits")
            value = left ** right
    elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in FUNCTIONS and not node.keywords and len(node.args) == 1:
        value = FUNCTIONS[node.func.id](_arithmetic(node.args[0], depth + 1))
    else:
        raise ToolCallError("calculator accepts numeric arithmetic and approved math functions only")
    if isinstance(value, complex) or not math.isfinite(value) or abs(value) > 1e100:
        raise ToolCallError("nonfinite or excessive calculator result")
    return float(value)


def execute_tool(name: str, arguments: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return (result, safe normalized arguments); never execute arbitrary code."""
    if name not in ALLOWED_TOOLS:
        raise ToolCallError(f"tool {name!r} is not in the bounded profile")
    if not isinstance(arguments, dict):
        raise ToolCallError("tool arguments must be a JSON object")
    if name == "calculator":
        if set(arguments) != {"expression"} or not isinstance(arguments["expression"], str):
            raise ToolCallError("calculator requires one expression string")
        expression = arguments["expression"].strip()
        if len(expression) > 256:
            raise ToolCallError("expression too long")
        try:
            tree = ast.parse(expression, mode="eval")
            value = _arithmetic(tree)
        except (SyntaxError, ArithmeticError, OverflowError, ValueError) as exc:
            raise ToolCallError(f"invalid arithmetic: {type(exc).__name__}") from exc
        return {"value": value}, {"expression": expression}
    if set(arguments) != {"value", "from_unit", "to_unit"}:
        raise ToolCallError("unit_convert requires value, from_unit, and to_unit")
    value = arguments["value"]
    source, target = arguments["from_unit"], arguments["to_unit"]
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ToolCallError("value must be finite numeric")
    if source not in UNIT_FACTORS or target not in UNIT_FACTORS:
        raise ToolCallError("unsupported unit")
    source_dimension, source_factor = UNIT_FACTORS[source]
    target_dimension, target_factor = UNIT_FACTORS[target]
    if source_dimension != target_dimension:
        raise ToolCallError("unit dimensions differ")
    converted = value * source_factor / target_factor
    if not math.isfinite(converted):
        raise ToolCallError("nonfinite conversion")
    return {"value": converted, "unit": target}, {"value": value, "from_unit": source, "to_unit": target}


def observed_call(index: int, name: str, arguments: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    """Execute one call and return its result and observed audit event."""
    start = time.monotonic()
    try:
        result, safe_args = execute_tool(name, arguments)
    except ToolCallError as exc:
        event = {"call_index": index, "tool_name": name, "arguments_summary": {"invalid": True},
                 "status": "malformed_call", "wall_time_seconds": time.monotonic() - start,
                 "token_usage": None, "cost": None, "error": str(exc)}
        return {"error": str(exc)}, event
    except Exception as exc:
        event = {"call_index": index, "tool_name": name, "arguments_summary": {"unavailable": True},
                 "status": "runtime_error", "wall_time_seconds": time.monotonic() - start,
                 "token_usage": None, "cost": None, "error": type(exc).__name__}
        return {"error": "tool runtime failed"}, event
    event = {"call_index": index, "tool_name": name, "arguments_summary": safe_args,
             "status": "ok", "wall_time_seconds": time.monotonic() - start,
             "token_usage": None, "cost": None, "error": None}
    return result, event
