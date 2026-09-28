"""Measure bounded-judge reliability from repeated live verdicts.

Input JSON pins judge_version, prompt_version, model_id, and a responses mapping
of calibration item IDs to repeated judge verdicts. This tool does not call a
paid API and never treats mocked outputs as live evidence.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.semantic_judge import ROOT, load_config


SET = ROOT / "benchmark" / "judge" / "calibration_v0.1.json"
VERDICTS = {"pass", "fail", "unresolved"}


def measure(responses: dict[str, list[str]]) -> dict[str, dict[str, float | int | bool]]:
    items = json.loads(SET.read_text(encoding="utf-8"))["items"]
    grouped: dict[str, list[tuple[str, list[str]]]] = defaultdict(list)
    for item in items:
        runs = responses.get(item["id"])
        if not isinstance(runs, list) or not runs or any(v not in VERDICTS for v in runs):
            raise ValueError(f"missing or invalid repeated verdicts for {item['id']}")
        grouped[item["criterion_id"]].append((item["expected"], runs))
    if set(responses) != {item["id"] for item in items}:
        raise ValueError("response IDs differ from calibration set")
    result = {}
    for criterion, data in grouped.items():
        pairs = [(expected, verdict) for expected, runs in data for verdict in runs]
        positives = [(expected, actual) for expected, actual in pairs if expected == "pass"]
        negatives = [(expected, actual) for expected, actual in pairs if expected == "fail"]
        false_pass = sum(actual == "pass" for _, actual in negatives)
        false_fail = sum(actual == "fail" for _, actual in positives)
        unresolved = sum(actual == "unresolved" for _, actual in pairs)
        unstable = sum(len(set(runs)) > 1 for _, runs in data)
        result[criterion] = {
            "positive_runs": len(positives), "negative_runs": len(negatives),
            "false_pass_rate": false_pass / len(negatives) if negatives else 1.0,
            "false_fail_rate": false_fail / len(positives) if positives else 1.0,
            "unresolved_rate": unresolved / len(pairs),
            "unstable_item_rate": unstable / len(data),
            "release_ready": len(positives) >= 50 and len(negatives) >= 50 and false_pass == 0
            and false_fail / len(positives) <= 0.05 and unresolved / len(pairs) <= 0.1
            and unstable == 0,
        }
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--responses", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        submission = json.loads(args.responses.read_text(encoding="utf-8"))
        config = load_config()
        if submission["judge_version"] != config["judge_version"] or submission["prompt_version"] != config["prompt_version"]:
            raise ValueError("judge or prompt version differs from calibration set")
        if not isinstance(submission["model_id"], str) or not submission["model_id"]:
            raise ValueError("model_id is required")
        metrics = measure(submission["responses"])
        print(json.dumps({"judge_version": submission["judge_version"],
                          "prompt_version": submission["prompt_version"],
                          "model_id": submission["model_id"], "metrics": metrics}, indent=2))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Calibration input error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
