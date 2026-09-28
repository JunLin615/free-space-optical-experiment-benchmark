"""Bounded, criterion-level semantic judge adapter.

CI uses deterministic replay. A live backend can be supplied by an external
runner, but its results are not release evidence until separately calibrated.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from tools.validate_cases import ROOT


CONFIG_PATH = ROOT / "benchmark" / "judge" / "bounded_v0.1.json"
Backend = Callable[[str, dict[str, Any]], str]


def load_config() -> dict[str, Any]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def judge_criterion(
    *, criterion_id: str, criterion: str, candidate_text: str,
    backend: Backend | None = None, deterministic_gate: str = "pass",
) -> dict[str, Any]:
    """Judge one residual claim; never override a failed deterministic gate."""
    config = load_config()
    if deterministic_gate != "pass":
        return {"check_id": criterion_id, "version": config["judge_version"],
                "status": "not_applicable", "score": None,
                "evidence": "deterministic gate did not pass"}
    if backend is None:
        return {"check_id": criterion_id, "version": config["judge_version"],
                "status": "unresolved", "score": None,
                "evidence": "no calibrated semantic backend configured"}
    request = {
        "system": config["system_prompt"],
        "criterion_id": criterion_id,
        "criterion": criterion,
        "candidate_data": candidate_text,
        "response_fields": config["response_fields"],
    }
    try:
        reply = json.loads(backend(json.dumps(request, ensure_ascii=False), config))
        if not isinstance(reply, dict) or set(reply) != set(config["response_fields"]):
            raise ValueError("judge output fields differ from contract")
        verdict = reply["verdict"]
        quote = reply["evidence_quote"]
        reason = reply["reason"]
        if verdict not in {"pass", "fail", "unresolved"}:
            raise ValueError("unsupported judge verdict")
        if not isinstance(quote, str) or not quote.strip() or len(quote) > config["max_evidence_chars"] or quote not in candidate_text:
            raise ValueError("evidence quote must occur in candidate response")
        if not isinstance(reason, str) or not reason or len(reason) > 400:
            raise ValueError("judge reason missing or too long")
    except Exception as exc:
        return {"check_id": criterion_id, "version": config["judge_version"],
                "status": "unresolved", "score": None,
                "evidence": f"judge unavailable, unparseable, or ungrounded ({type(exc).__name__})"}
    return {"check_id": criterion_id, "version": config["judge_version"],
            "status": verdict, "score": 1 if verdict == "pass" else 0 if verdict == "fail" else None,
            "evidence": quote, "details": {"reason": reason, "prompt_version": config["prompt_version"]}}
