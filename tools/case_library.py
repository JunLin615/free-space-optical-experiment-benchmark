"""Integrity and obvious-leakage checks for optional public examples."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from tools.protocols import ROOT


LIBRARY_DIR = ROOT / "benchmark" / "case_library"
INDEX_PATH = LIBRARY_DIR / "index.v1.json"
TOKEN_RE = re.compile(r"[a-z]+|\d+(?:\.\d+)?", re.I)
NUMBER_RE = re.compile(r"(?<![a-z])\d+(?:\.\d+)?(?:e[+-]?\d+)?", re.I)


def load_index() -> dict[str, Any]:
    index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    if index.get("schema_version") != "1.0.0" or index.get("snapshot_id") != "optics-examples-v1":
        raise ValueError("unsupported case-library index version")
    return index


def load_items() -> list[dict[str, Any]]:
    index = load_index()
    seen: set[str] = set()
    items = []
    required = {"item_id", "version", "path", "content_sha256", "concept_family",
                "optical_domain", "reasoning_mode", "difficulty", "source_provenance",
                "source_type", "benchmark_family_relationship", "leakage_risk_notes",
                "allowed_protocols"}
    for entry in index.get("items", []):
        missing = required - set(entry)
        if missing:
            raise ValueError(f"library item lacks metadata: {sorted(missing)}")
        item_id = entry["item_id"]
        if item_id in seen:
            raise ValueError(f"duplicate library item ID: {item_id}")
        seen.add(item_id)
        if entry["source_type"] not in ("synthetic", "external"):
            raise ValueError(f"invalid source type: {item_id}")
        if entry["allowed_protocols"] != ["case_assisted", "case_and_tool_assisted"]:
            raise ValueError(f"invalid protocol access: {item_id}")
        path = (LIBRARY_DIR / entry["path"]).resolve()
        if path.parent != LIBRARY_DIR.resolve() or path.suffix != ".md":
            raise ValueError(f"library path escapes dedicated directory: {item_id}")
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != entry["content_sha256"]:
            raise ValueError(f"library item hash mismatch: {item_id}")
        items.append({**entry, "text": raw.decode("utf-8")})
    if not items:
        raise ValueError("empty case library")
    return items


def _tokens(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


def _ngrams(text: str, size: int = 5, *, erase_digits: bool = False) -> set[tuple[str, ...]]:
    tokens = _tokens(text)
    if erase_digits:
        tokens = ["#" if NUMBER_RE.fullmatch(token) else token for token in tokens]
    return set(zip(*(tokens[index:] for index in range(size)))) if len(tokens) >= size else set()


def _task_text(task: dict[str, Any]) -> str:
    pieces = [str(task.get("statement", ""))]
    pieces.extend(str(question.get("request", "")) for question in task.get("questions", []))
    for given in task.get("givens", []):
        pieces.append(f"{given.get('symbol', '')} {given.get('value', '')} {given.get('unit', '')}")
    return "\n".join(pieces)


def _numeric_tuple(task: dict[str, Any]) -> tuple[str, ...]:
    return tuple(sorted(f"{given.get('value')}:{given.get('unit')}" for given in task.get("givens", [])))


def _overlap(a: str, b: str, erase_digits: bool = False) -> float:
    first, second = _ngrams(a, erase_digits=erase_digits), _ngrams(b, erase_digits=erase_digits)
    if not first or not second:
        return 0.0
    return len(first & second) / min(len(first), len(second))


def audit_leakage(variant_tasks: list[dict[str, Any]] | None = None) -> list[str]:
    """Detect exact/near copies, reused givens, and long answer-key passages.

    This is a low-cost screening check, not proof of semantic independence.
    Public variant files are read as task-only records. Gold is used solely as
    a local comparison target and is never returned in retrieval results.
    """
    import yaml

    library = load_items()
    targets: list[tuple[str, str, tuple[str, ...], list[str], list[tuple[str, str]]]] = []
    for path in sorted((ROOT / "benchmark" / "cases").glob("*.yaml")):
        case = yaml.safe_load(path.read_text(encoding="utf-8"))
        gold = case.get("gold", {})
        passages: list[str] = []
        def visit(value: Any) -> None:
            if isinstance(value, dict):
                for child in value.values():
                    visit(child)
            elif isinstance(value, list):
                for child in value:
                    visit(child)
            elif isinstance(value, str) and len(value.split()) >= 8:
                passages.append(value)
        visit(gold)
        task = case.get("task", {})
        reference_quantities = []
        for check in gold.get("numerical_checks", []):
            reference = check.get("reference", {})
            if isinstance(reference, dict) and "value" in reference and "unit" in reference:
                reference_quantities.append((str(reference["value"]), str(reference["unit"])))
        targets.append((case["case_id"], _task_text(task), _numeric_tuple(task),
                        passages, reference_quantities))
    if variant_tasks is None:
        variant_tasks = []
        for path in sorted((ROOT / "benchmark" / "variants" / "public_dev").glob("*.json")):
            record = json.loads(path.read_text(encoding="utf-8"))
            variant_tasks.append({"item_id": record["variant_id"], "task": record["task"]})
    for record in variant_tasks:
        task = record.get("task", {})
        targets.append((record["item_id"], _task_text(task), _numeric_tuple(task), [], []))
    issues: list[str] = []
    for example in library:
        body = example["text"]
        for target_id, task_text, givens, gold_passages, reference_quantities in targets:
            if _tokens(body) == _tokens(task_text):
                issues.append(f"{example['item_id']} duplicates {target_id} task text")
            elif _overlap(body, task_text) >= 0.72:
                issues.append(f"{example['item_id']} nearly duplicates {target_id} wording")
            elif _overlap(body, task_text, erase_digits=True) >= 0.78:
                issues.append(f"{example['item_id']} is a trivial numeric renaming of {target_id}")
            example_numbers = set(NUMBER_RE.findall(body.lower()))
            given_numbers = {part.split(":", 1)[0] for part in givens}
            if len(given_numbers) >= 2 and given_numbers <= example_numbers:
                issues.append(f"{example['item_id']} repeats {target_id} numeric givens")
            normalized = " ".join(_tokens(body))
            for passage in gold_passages:
                gold_phrase = " ".join(_tokens(passage))
                if len(gold_phrase) >= 70 and gold_phrase in normalized:
                    issues.append(f"{example['item_id']} repeats {target_id} answer-key passage")
                    break
            for value, unit in reference_quantities:
                if re.search(r"(?<![\d.])" + re.escape(value) + r"\s*" +
                             re.escape(unit) + r"\b", body, flags=re.I):
                    issues.append(f"{example['item_id']} repeats {target_id} numerical answer key")
    return sorted(set(issues))


if __name__ == "__main__":
    import sys
    problems = audit_leakage()
    for problem in problems:
        print(problem)
    if not problems:
        print(f"Validated {len(load_items())} library items; no obvious leakage found")
    sys.exit(bool(problems))
