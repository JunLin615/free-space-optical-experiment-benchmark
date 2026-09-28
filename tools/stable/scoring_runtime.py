"""Stable-release scoring with a case-local SEED-3-1 unit-contract revision.

The runtime validates contracts, invokes only registered case scorers, keeps
unresolved and evaluator failures separate from candidate failures, and emits
the public result schema. It does not run a candidate model.
"""

from __future__ import annotations

import json
import hashlib
from typing import Any, Callable

from jsonschema import Draft202012Validator, FormatChecker

from tools.validate_cases import ROOT, load_case, semantic_issues
from tools.vnext.units import normalize_answer_units


RUNTIME_VERSION = "0.2.0"
CASES = ROOT / "benchmark" / "cases_stable"
VNEXT_CASES = ROOT / "benchmark" / "cases_vnext"
CANONICAL_CASES = ROOT / "benchmark" / "cases"
SCHEMAS = ROOT / "benchmark" / "schema"
SCORERS = {
    "SEED-1-1": "numerical",
    "SEED-1-5": "numerical",
    "SEED-1-7": "numerical",
    "SEED-2-1": "numerical",
    "SEED-2-2": "numerical",
    "SEED-2-4": "numerical",
    "SEED-4-2": "numerical",
    "SEED-1-3": "structured_wave",
    "SEED-1-6": "structured_wave",
    "SEED-4-1": "structured_wave",
    "SEED-7-8": "structured_wave",
    "SEED-2-8": "structured",
    "SEED-5-3": "structured",
    "SEED-7-2": "diagnostic",
    "SEED-4-8": "diagnostic",
    "SEED-3-1": "closed_stable",
    "SEED-3-7": "closed_vnext",
    "SEED-5-5": "closed_vnext",
    "SEED-1-4": "structured_vnext",
    "SEED-3-2": "structured_vnext",
    "SEED-3-3": "structured_vnext",
    "SEED-7-5": "structured_vnext",
    "SEED-7-6": "structured_vnext",
    "SEED-7-1": "diagnostic_vnext",
    "SEED-8-6": "routing_vnext",
}


def _content_hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _evaluator_fingerprint(case: dict[str, Any]) -> str:
    case_id = case["case_id"]
    scorer = SCORERS[case_id]
    scorer_path = f"tools/scorers/{scorer}.py"
    paths = ["tools/stable/scoring_runtime.py", "tools/vnext/units.py", scorer_path,
             "tools/validate_cases.py"]
    if case.get("validation", {}).get("semantic_criteria"):
        paths.extend(["tools/semantic_judge.py", "benchmark/judge/bounded_v0.1.json"])
    if SCORERS[case_id] == "numerical":
        paths.append("tools/physics_checks.py")
    if scorer in {"closed_vnext", "closed_stable"}:
        paths.extend(["tools/scorers/numerical.py", "tools/physics_checks.py"])
    if case_id == "SEED-1-1":
        paths.append("tools/scorers/geometry.py")
    digest = hashlib.sha256()
    for relative in sorted(paths):
        digest.update(relative.encode("utf-8") + b"\0")
        digest.update((ROOT / relative).read_bytes())
    return digest.hexdigest()


def _validator(name: str) -> Draft202012Validator:
    schema = json.loads((SCHEMAS / name).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def load_scored_case(case_id: str) -> dict[str, Any]:
    if case_id not in SCORERS:
        raise ValueError(f"no scorer registered for {case_id}")
    source = CASES / f"{case_id}.yaml"
    if not source.is_file():
        source = VNEXT_CASES / f"{case_id}.yaml"
    case = load_case(source if source.is_file() else CANONICAL_CASES / f"{case_id}.yaml")
    if case.get("case_id") != case_id:
        raise ValueError("case file ID mismatch")
    return case


def _context(context: dict[str, Any] | None) -> dict[str, Any]:
    supplied = context or {}
    default = {
        "benchmark_version": "0.1.0-dev",
        "system": {"name": "Local submission", "model_id": "unknown", "model_version": None, "scaffold_id": None},
        "protocol": "closed_book",
        "case_library_access": {"available": False, "snapshot_id": None, "retrieved_document_ids": []},
        "tools_available": [],
        "tools_used": [],
        "tool_call_count": None,
        "tokens": {"input": None, "output": None, "total": None},
        "provider_usage": None,
        "cost": None,
        "wall_time_seconds": None,
        "retry_count": 0,
    }
    unknown = set(supplied) - set(default) - {"run_id"}
    if unknown:
        raise ValueError(f"unsupported run context fields: {sorted(unknown)}")
    default.update(supplied)
    if "run_id" in supplied:
        default["run_id"] = supplied["run_id"]
    return default


def _dispatch(case: dict[str, Any], answer: dict[str, Any]) -> list[dict[str, Any]]:
    module = SCORERS[case["case_id"]]
    if module == "numerical":
        from tools.scorers.numerical import evaluate
        if case["case_id"] == "SEED-1-1":
            from tools.scorers.geometry import evaluate_quarter
            return evaluate(case, answer) + [evaluate_quarter(case, answer)]
    elif module == "structured":
        from tools.scorers.structured import evaluate
    elif module == "structured_wave":
        from tools.scorers.structured_wave import evaluate
    elif module == "structured_vnext":
        from tools.scorers.structured_vnext import evaluate
    elif module == "closed_vnext":
        from tools.scorers.closed_vnext import evaluate
    elif module == "closed_stable":
        from tools.scorers.closed_stable import evaluate
    elif module == "diagnostic_vnext":
        from tools.scorers.diagnostic_vnext import evaluate
    elif module == "routing_vnext":
        from tools.scorers.routing_vnext import evaluate
    else:
        from tools.scorers.diagnostic import evaluate
    return evaluate(case, answer)


def evaluate_case(
    case: dict[str, Any], answer: Any, *, raw_answer: str | None = None,
    context: dict[str, Any] | None = None,
    judge_criteria: dict[str, str] | None = None,
    judge_backend: Callable[[str, dict[str, Any]], str] | None = None,
) -> dict[str, Any]:
    """Score a parsed answer; malformed candidate data still yields a record.

    A corrupt case/oracle yields null aggregate scores and an evaluator failure.
    Never convert evaluator failure into a candidate zero.
    """
    case_id = case.get("case_id", "unknown")
    if case_id not in SCORERS:
        raise ValueError(f"no scorer registered for {case_id}")
    run = _context(context)
    criteria = case.get("scoring", {}).get("criteria", [])
    result: dict[str, Any] = {
        "result_schema_version": "0.1.0",
        "case_id": case_id,
        "case_revision": case.get("case_revision"),
        "case_content_sha256": _content_hash(case),
        "evaluator_version": RUNTIME_VERSION,
        "evaluator_fingerprint": _evaluator_fingerprint(case),
        "benchmark_version": run["benchmark_version"],
        "system": run["system"],
        "protocol": run["protocol"],
        "case_library_access": run["case_library_access"],
        "tools_available": run["tools_available"],
        "tools_used": run["tools_used"],
        "tool_call_count": run["tool_call_count"],
        "tokens": run["tokens"],
        "provider_usage": run["provider_usage"],
        "cost": run["cost"],
        "wall_time_seconds": run["wall_time_seconds"],
        "retry_count": run["retry_count"],
        "raw_answer": raw_answer,
        "structured_answer": answer if isinstance(answer, dict) else None,
        "validator_results": [],
        "judge_results": [],
        "criterion_scores": [],
        "scores": {"raw_total": None, "capped_total": None},
        "failure_mode": "none",
    }
    if "run_id" in run:
        result["run_id"] = run["run_id"]

    def finish() -> dict[str, Any]:
        record_errors = list(_validator("result.schema.json").iter_errors(result))
        if record_errors:
            raise RuntimeError(f"generated result violates schema: {record_errors[0].message}")
        return result

    def all_unresolved(failure_mode: str, check_id: str, evidence: str) -> dict[str, Any]:
        result["failure_mode"] = failure_mode
        result["validator_results"] = [{"check_id": check_id, "version": RUNTIME_VERSION,
                                        "status": "error", "score": None, "evidence": evidence}]
        result["criterion_scores"] = [
            {"criterion_id": c["id"], "score": None, "weight": c["weight"],
             "status": "unresolved", "evidence": evidence} for c in criteria
        ]
        return finish()

    def invalid_contract(check_id: str, evidence: str) -> dict[str, Any]:
        result["failure_mode"] = "invalid_contract"
        result["validator_results"] = [{"check_id": check_id, "version": RUNTIME_VERSION,
                                        "status": "fail", "score": 0, "evidence": evidence}]
        result["criterion_scores"] = [
            {"criterion_id": c["id"], "score": 0, "weight": c["weight"],
             "status": "scored", "evidence": evidence} for c in criteria
        ]
        result["scores"] = {"raw_total": 0, "capped_total": 0}
        return finish()

    case_errors = list(_validator("case_v0.1.schema.json").iter_errors(case))
    if case_errors:
        return all_unresolved("invalid_instance", "case_schema", case_errors[0].message)
    semantic_errors = semantic_issues(case)
    if semantic_errors:
        failure = "validator_error" if any("authored gold" in e or "physics validator" in e for e in semantic_errors) else "invalid_instance"
        return all_unresolved(failure, "case_consistency", "; ".join(semantic_errors))
    if not isinstance(answer, dict):
        return invalid_contract("answer_parse", "answer is not a JSON object")
    answer_schema = case["answer_contract"]["schema_id"] + ".schema.json"
    answer_errors = list(_validator(answer_schema).iter_errors(answer))

    try:
        verdicts = _dispatch(case, normalize_answer_units(answer))
    except Exception as exc:
        return all_unresolved("validator_error", "scorer_exception", f"{type(exc).__name__}: {exc}")
    by_id = {v.get("criterion_id"): v for v in verdicts}
    rubric_by_id = {item["id"]: item for item in case["gold"].get("judge_rubrics", [])}
    for criterion in criteria:
        rubric = rubric_by_id.get(criterion["check"])
        if rubric is None:
            continue
        current = answer
        for part in rubric.get("evidence_path", "").split("."):
            current = current.get(part) if isinstance(current, dict) else None
        present = isinstance(current, str) and bool(current.strip())
        by_id[criterion["id"]] = {
            "criterion_id": criterion["id"], "check_id": rubric["id"],
            "status": "unresolved" if present else "fail",
            "score": None if present else 0,
            "evidence": "Declared explanation awaits semantic judging." if present else
                        f"Required explanation is missing at {rubric.get('evidence_path')}.",
            "details": {"failure_class": "missing_claim"} if not present else {},
        }
    expected = {c["id"] for c in criteria}
    if len(by_id) != len(verdicts) + sum(c["check"] in rubric_by_id for c in criteria) or set(by_id) != expected:
        return all_unresolved("validator_error", "scorer_coverage", "scorer verdicts do not cover each criterion exactly once")
    invalid_statuses = [v for v in verdicts if v.get("status") not in {"pass", "fail", "unresolved", "error"}]
    if invalid_statuses:
        return all_unresolved("validator_error", "scorer_status", "scorer returned unsupported status")

    original_by_id = dict(by_id)
    numeric_ids = {item["id"] for item in case["gold"].get("numerical_checks", [])}
    declared_judges = {
        c["id"]: rubric_by_id[c["check"]]["criterion"] for c in criteria
        if c["check"] in rubric_by_id
    }
    if judge_criteria and judge_criteria != declared_judges:
        raise ValueError("judge criteria must match explicitly scored case rubrics")
    requested_judges = declared_judges
    if requested_judges:
        from tools.semantic_judge import judge_criterion
        candidate_text = raw_answer if raw_answer is not None else json.dumps(answer, ensure_ascii=False)
        for criterion_id, criterion_text in requested_judges.items():
            if criterion_id not in by_id or criterion_id in numeric_ids:
                raise ValueError(f"semantic judge cannot target {criterion_id}")
            if by_id[criterion_id]["status"] != "unresolved":
                continue  # Never override deterministic pass, fail, or error.
            judged = judge_criterion(criterion_id=criterion_id, criterion=criterion_text,
                                     candidate_text=candidate_text, backend=judge_backend)
            result["judge_results"].append(judged)
            if judged["status"] in {"pass", "fail"}:
                by_id[criterion_id] = {
                    "criterion_id": criterion_id, "check_id": criterion_id,
                    "version": judged["version"], "status": judged["status"],
                    "score": judged["score"], "evidence": judged["evidence"],
                    "details": {"source": "semantic_judge"},
                }

    has_unresolved = False
    has_error = False
    total = 0.0
    hard_failed = False
    hard_ids = {item["id"] for item in case["gold"].get("universal_constraints", []) if item["severity"] == "hard"}
    hard_ids.update(c["id"] for c in criteria if c["check"] in rubric_by_id and rubric_by_id[c["check"]].get("severity") == "hard")
    if answer_errors:
        result["validator_results"].append({
            "check_id": "answer_schema", "version": RUNTIME_VERSION, "status": "fail", "score": 0,
            "evidence": answer_errors[0].message,
            "details": {"failure_class": "malformed_answer"},
        })
    for c in criteria:
        verdict = by_id[c["id"]]
        status = verdict["status"]
        score = verdict.get("score")
        if status in {"unresolved", "error"}:
            score = None
            has_unresolved = True
            has_error |= status == "error"
        elif score not in (0, 1):
            return all_unresolved("validator_error", "scorer_score", "scorer returned non-binary score")
        else:
            total += c["weight"] * score
        if c["id"] in hard_ids and status == "fail":
            hard_failed = True
        evidence = str(verdict.get("evidence", ""))
        original = original_by_id[c["id"]]
        result["validator_results"].append({
            "check_id": original.get("check_id", c["check"]),
            "version": str(original.get("version", RUNTIME_VERSION)),
            "status": original["status"], "score": original.get("score"),
            "evidence": str(original.get("evidence", "")),
            "details": original.get("details", {}),
        })
        result["criterion_scores"].append({
            "criterion_id": c["id"], "score": score, "weight": c["weight"],
            "status": "unresolved" if score is None else "scored", "evidence": evidence,
        })
    if has_unresolved:
        result["failure_mode"] = (
            "validator_error" if has_error else
            "judge_unresolved" if any(v["status"] == "unresolved" for v in result["judge_results"]) else
            "oracle_unresolved"
        )
    else:
        result["scores"] = {"raw_total": round(total, 12),
                            "capped_total": round(min(total, 0.49) if hard_failed else total, 12)}
        if any(v["status"] == "fail" for v in by_id.values()):
            failure_classes = {v.get("details", {}).get("failure_class") for v in by_id.values() if v["status"] == "fail"}
            result["failure_mode"] = (
                "invalid_contract" if answer_errors or failure_classes & {"missing_claim", "malformed_claim", "malformed_answer", "wrong_unit"}
                else "constraint_fail" if hard_failed else "physics_fail"
            )
        elif answer_errors:
            result["failure_mode"] = "invalid_contract"
        if answer_errors:
            result["scores"]["capped_total"] = min(result["scores"]["capped_total"], 0.49)
    return finish()
