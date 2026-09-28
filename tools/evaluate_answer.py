"""Score one structured candidate answer against a supported case.

Example: python tools/evaluate_answer.py --case SEED-1-1 --answer answer.json --output result.json
Use --show-contract to inspect the case-specific answer requirements.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.scoring_runtime import evaluate_case, load_scored_case


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", required=True, help="canonical case ID")
    parser.add_argument("--answer", type=Path, help="candidate JSON answer")
    parser.add_argument("--context", type=Path, help="optional run metadata JSON")
    parser.add_argument("--output", type=Path, help="write result JSON here (default: stdout)")
    parser.add_argument("--show-contract", action="store_true", help="print case answer contract and exit")
    args = parser.parse_args(argv)
    try:
        case = load_scored_case(args.case)
        if args.show_contract:
            print(json.dumps(case["answer_contract"], indent=2, ensure_ascii=False))
            return 0
        if args.answer is None:
            parser.error("--answer is required unless --show-contract is used")
        raw = args.answer.read_text(encoding="utf-8")
        try:
            answer = json.loads(raw)
        except json.JSONDecodeError:
            answer = None
        context = json.loads(args.context.read_text(encoding="utf-8")) if args.context else None
        if context is not None and not isinstance(context, dict):
            raise ValueError("run context must be a JSON object")
        result = evaluate_case(case, answer, raw_answer=raw, context=context)
        encoded = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(encoded, encoding="utf-8")
        else:
            print(encoded, end="")
        scores = result["scores"]
        print(f"{case['case_id']}: {result['failure_mode']}; score={scores['capped_total']}", file=sys.stderr)
        return 2 if result["failure_mode"] in {"validator_error", "invalid_instance"} else 0
    except (OSError, ValueError, KeyError, RuntimeError) as exc:
        print(f"Evaluator failure: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
