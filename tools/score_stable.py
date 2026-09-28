"""Autonomously score one typed answer against the pinned stable 0.2.0 release.

This local scoring entry point does not call a model or human reviewer. Model
execution remains a separate, protocol-governed experiment.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.qualify_stable import MANIFEST, build
from tools.scoring_runtime import _content_hash
from tools.stable.scoring_runtime import _evaluator_fingerprint, evaluate_case, load_scored_case


def score(case_id: str, answer: object, *, raw_answer: str | None = None) -> dict:
    """Refuse an unpinned case or scorer before producing a result record."""
    saved = json.loads(MANIFEST.read_text(encoding="utf-8"))
    expected, _ = build()
    if saved != expected:
        raise ValueError("stable release manifest is stale or release evidence changed")
    if case_id not in saved["cases"]:
        raise ValueError(f"case is not in stable release: {case_id}")
    case = load_scored_case(case_id)
    pin = saved["cases"][case_id]
    if (pin["case_content_sha256"] != _content_hash(case) or
            pin["evaluator_fingerprint"] != _evaluator_fingerprint(case)):
        raise ValueError("stable case/scorer differs from release pin")
    return evaluate_case(case, answer, raw_answer=raw_answer,
                         context={"benchmark_version": "0.2.0"})


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case_id", help="one of the nine stable release case IDs")
    parser.add_argument("answer", type=Path, help="UTF-8 JSON answer file")
    args = parser.parse_args(argv)
    try:
        raw = args.answer.read_text(encoding="utf-8")
        try:
            answer = json.loads(raw)
        except json.JSONDecodeError:
            answer = raw
        result = score(args.case_id, answer, raw_answer=raw)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Stable scoring failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
