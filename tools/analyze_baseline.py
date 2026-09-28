"""Summarize one immutable baseline run without combining verified and development scores."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path, PureWindowsPath
from statistics import mean, median
import sys
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "benchmark" / "run_schema"
RESULT_SCHEMA = ROOT / "benchmark" / "schema" / "result.schema.json"
PAIRS = (
    ("case_assisted", "closed_book"),
    ("tool_assisted", "closed_book"),
    ("case_and_tool_assisted", "closed_book"),
    ("case_and_tool_assisted", "tool_assisted"),
    ("case_and_tool_assisted", "case_assisted"),
)


def _validator(path: Path) -> Draft202012Validator:
    return Draft202012Validator(json.loads(path.read_text(encoding="utf-8")))


def load_run(directory: Path) -> tuple[dict, list[dict]]:
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    records = [json.loads(path.read_text(encoding="utf-8"))
               for path in sorted((directory / "results").glob("*.json"))]
    if not records:
        raise ValueError("run has no completed result records")
    manifest_validator = _validator(SCHEMAS / "run_manifest_v0.1.schema.json")
    record_validator = _validator(SCHEMAS / "run_record_v0.1.schema.json")
    score_validator = _validator(RESULT_SCHEMA)
    errors = list(manifest_validator.iter_errors(manifest))
    if errors:
        raise ValueError(f"invalid run manifest: {errors[0].message}")
    for record in records:
        errors = list(record_validator.iter_errors(record))
        if errors:
            raise ValueError(f"invalid run record: {errors[0].message}")
        if record["run_id"] != manifest["run_id"] or record["execution_class"] != manifest["execution_class"]:
            raise ValueError("record identity or execution class differs from immutable manifest")
        selection = record["selection"]
        if record["protocol"]["id"] not in manifest["protocol_ids"]:
            raise ValueError("result protocol is absent from immutable manifest")
        if not any(item["case_id"] == selection["case_id"] and item["track"] == selection["track"]
                   and (item["variant_path"] is None and selection["variant_id"] is None
                        or isinstance(item["variant_path"], str)
                        and PureWindowsPath(item["variant_path"]).stem == selection["variant_id"])
                   for item in manifest["selections"]):
            raise ValueError("result selection is absent from immutable manifest")
        if record["score_result"] is not None:
            errors = list(score_validator.iter_errors(record["score_result"]))
            if errors:
                raise ValueError(f"invalid score result: {errors[0].message}")
            if (record["score_result"]["case_id"] != selection["case_id"]
                    or record["score_result"].get("case_revision") != selection["case_revision"]
                    or record["score_result"].get("case_content_sha256") != selection["case_content_sha256"]):
                raise ValueError("score result case identity differs from selection")
    return manifest, records


def _score(record: dict) -> float | None:
    result = record["score_result"]
    return None if result is None else result["scores"]["capped_total"]


def _success(record: dict) -> bool:
    return record["status"] == "completed" and _score(record) == 1.0


def _rate(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def _resource(records: list[dict], field: str) -> dict:
    values = [record["usage"].get(field) for record in records]
    known = [value for value in values if isinstance(value, int)]
    return {"known_records": len(known), "total": sum(known) if len(known) == len(values) else None}


def metrics(records: list[dict]) -> dict:
    completed = [record for record in records if record["status"] == "completed"]
    candidate = [record for record in completed if record["score_result"] is not None
                 and record["score_result"].get("failure_mode") not in {"validator_error", "invalid_instance"}
                 and record["failure_class"] not in {"scorer_failure", "invalid_benchmark_instance"}]
    scored = [_score(record) for record in candidate if _score(record) is not None]
    successes = [record for record in candidate if _success(record)]
    unresolved = [record for record in candidate if _score(record) is None]
    invalid = [record for record in candidate if record["score_result"] is not None
               and record["score_result"].get("failure_mode") == "invalid_contract"]
    physics_failures = [record for record in candidate if record["score_result"] is not None
                        and record["score_result"].get("failure_mode") in {"physics_fail", "constraint_fail"}]
    tool_counts = [len(record["tool_calls"]) for record in successes]
    success_tokens = [record["usage"].get("total") for record in successes]
    costs = [record["cost"] for record in records]
    known_costs = [value for value in costs if isinstance(value, dict) and isinstance(value.get("amount"), (int, float))]
    currencies = {value.get("currency") for value in known_costs}
    success_costs = [record["cost"] for record in successes]
    success_currencies = {value.get("currency") for value in success_costs if isinstance(value, dict)}
    return {
        "runs": len(records), "completed": len(completed), "candidate_outcomes": len(candidate),
        "infrastructure_failures": len(records) - len(candidate),
        "scored": len(scored), "mean_score": mean(scored) if scored else None,
        "median_score": median(scored) if scored else None,
        "score_distribution": sorted(scored),
        "successes": len(successes), "task_success_rate": _rate(len(successes), len(candidate)),
        "first_attempt_success_rate": _rate(sum(bool(record["first_attempt_success"]) for record in candidate), len(candidate)),
        "unresolved_rate": _rate(len(unresolved), len(candidate)),
        "invalid_contract_rate": _rate(len(invalid), len(candidate)),
        "physics_failure_rate": _rate(len(physics_failures), len(candidate)),
        "failure_classes": dict(sorted(Counter(record["failure_class"] or "none" for record in records).items())),
        "score_failure_modes": dict(sorted(Counter((record["score_result"] or {}).get("failure_mode", "none") for record in completed).items())),
        "usage": {field: _resource(records, field) for field in ("input", "output", "total", "cached_input", "reasoning")},
        "tokens_per_success": mean(success_tokens) if successes and all(isinstance(value, int) for value in success_tokens) else None,
        "tool_calls": sum(len(record["tool_calls"]) for record in records),
        "tool_failures": sum(call.get("status") not in {"ok", "success"} for record in records for call in record["tool_calls"]),
        "tool_calls_per_success": mean(tool_counts) if tool_counts else None,
        "wall_time_seconds": sum(record["wall_time_seconds"] for record in records),
        "wall_seconds_per_success": mean(record["wall_time_seconds"] for record in successes) if successes else None,
        "cost": {"amount": sum(value["amount"] for value in known_costs) if len(known_costs) == len(costs) and len(currencies) == 1 else None,
                 "currency": next(iter(currencies)) if len(currencies) == 1 else None,
                 "known_records": len(known_costs),
                 "per_success": mean(value["amount"] for value in success_costs)
                 if successes and all(isinstance(value, dict) and isinstance(value.get("amount"), (int, float)) for value in success_costs)
                 and len(success_currencies) == 1 else None},
    }


def _identity(record: dict) -> str:
    return json.dumps(record["agent_identity"], sort_keys=True, separators=(",", ":"))


def _matched_groups(records: list[dict]) -> dict[tuple, dict[str, dict]]:
    groups: dict[tuple, dict[str, dict]] = defaultdict(dict)
    for record in records:
        selection = record["selection"]
        key = (selection["case_id"], selection["case_revision"], selection["variant_id"],
               selection["track"], _identity(record))
        protocol = record["protocol"]["id"]
        if protocol in groups[key]:
            raise ValueError(f"duplicate matched run for {selection['case_id']} {protocol}")
        groups[key][protocol] = record
    for key, group in groups.items():
        hashes = {record["protocol"]["scientific_payload_sha256"] for record in group.values()}
        if len(hashes) > 1:
            raise ValueError(f"matched scientific payload differs for {key[0]}")
        versions = {record["protocol"]["version"] for record in group.values()}
        case_hashes = {record["selection"]["case_content_sha256"] for record in group.values()}
        scorer_versions = {(record["score_result"] or {}).get("evaluator_version") for record in group.values()} - {None}
        scorer_fingerprints = {(record["score_result"] or {}).get("evaluator_fingerprint") for record in group.values()} - {None}
        result_versions = {(record["score_result"] or {}).get("result_schema_version") for record in group.values()} - {None}
        if any(len(values) > 1 for values in (versions, case_hashes, scorer_versions, scorer_fingerprints, result_versions)):
            raise ValueError(f"matched case/scorer/schema/protocol version differs for {key[0]}")
    return groups


def paired_differences(records: list[dict]) -> dict:
    groups = _matched_groups(records)
    comparisons = []
    for key, group in sorted(groups.items(), key=lambda item: tuple(str(part) for part in item[0])):
        if key[3] != "verified" or key[2] is not None:
            continue
        for assisted, baseline in PAIRS:
            if assisted not in group or baseline not in group:
                continue
            a, b = group[assisted], group[baseline]
            a_score, b_score = _score(a), _score(b)
            comparisons.append({
                "case_id": key[0], "agent_identity": a["agent_identity"],
                "assisted_protocol": assisted, "baseline_protocol": baseline,
                "assisted_score": a_score, "baseline_score": b_score,
                "score_delta": a_score - b_score if a_score is not None and b_score is not None else None,
                "input_token_delta": a["usage"]["input"] - b["usage"]["input"]
                if a["usage"]["input"] is not None and b["usage"]["input"] is not None else None,
                "output_token_delta": a["usage"]["output"] - b["usage"]["output"]
                if a["usage"]["output"] is not None and b["usage"]["output"] is not None else None,
                "total_token_delta": a["usage"]["total"] - b["usage"]["total"]
                if a["usage"]["total"] is not None and b["usage"]["total"] is not None else None,
                "cost_delta": a["cost"]["amount"] - b["cost"]["amount"]
                if isinstance(a["cost"], dict) and isinstance(b["cost"], dict)
                and isinstance(a["cost"].get("amount"), (int, float))
                and isinstance(b["cost"].get("amount"), (int, float))
                and a["cost"].get("currency") == b["cost"].get("currency") else None,
                "wall_time_delta_seconds": a["wall_time_seconds"] - b["wall_time_seconds"],
                "tool_call_delta": len(a["tool_calls"]) - len(b["tool_calls"]),
            })
    aggregate = {}
    for assisted, baseline in PAIRS:
        subset = [item for item in comparisons if item["assisted_protocol"] == assisted and item["baseline_protocol"] == baseline]
        deltas = [item["score_delta"] for item in subset if item["score_delta"] is not None]
        aggregate[f"{assisted}_minus_{baseline}"] = {
            "paired_cases": len(subset), "scored_pairs": len(deltas),
            "mean_score_delta": mean(deltas) if deltas else None,
        }
    return {"per_case": comparisons, "aggregate": aggregate}


def analyze(manifest: dict, records: list[dict]) -> dict:
    verified = [record for record in records if record["selection"]["track"] == "verified"]
    development = [record for record in records if record["selection"]["track"] == "development"]
    variants = [record for record in records if record["selection"]["track"] in {"public_variant", "private_variant"}]
    by_protocol = {protocol: metrics([record for record in verified if record["protocol"]["id"] == protocol])
                   for protocol in manifest["protocol_ids"]}
    retrieval = {}
    for protocol in manifest["protocol_ids"]:
        selected = [record for record in records if record["protocol"]["id"] == protocol]
        retrieved = [record["retrieval"] for record in selected if isinstance(record["retrieval"], dict)]
        counts = [len(item.get("retrieved_ids", item.get("retrieved_document_ids", item.get("items", [])))) for item in retrieved]
        tokens = [item.get("total_retrieved_tokens", item.get("retrieved_tokens")) for item in retrieved]
        latencies = [item.get("latency_seconds", item.get("wall_time_seconds")) for item in retrieved]
        retrieval[protocol] = {
            "records_with_retrieval": len(retrieved), "items": sum(counts),
            "tokens": sum(tokens) if tokens and all(isinstance(value, int) for value in tokens) else None,
            "latency_seconds": sum(latencies) if latencies and all(isinstance(value, (int, float)) for value in latencies) else None,
        }
    canonical = {(record["selection"]["case_id"], record["protocol"]["id"], _identity(record)): record
                 for record in verified if record["selection"]["variant_id"] is None}
    variant_comparisons = []
    for record in variants:
        key = (record["selection"]["case_id"], record["protocol"]["id"], _identity(record))
        parent = canonical.get(key)
        if parent is None:
            continue
        variant_score, parent_score = _score(record), _score(parent)
        variant_comparisons.append({
            "case_id": key[0], "variant_id": record["selection"]["variant_id"],
            "protocol": key[1], "canonical_score": parent_score, "variant_score": variant_score,
            "score_delta": variant_score - parent_score
            if variant_score is not None and parent_score is not None else None,
        })
    return {
        "run_id": manifest["run_id"], "execution_class": manifest["execution_class"],
        "record_count": len(records), "declared_run_count": len(manifest["selections"]) * len(manifest["protocol_ids"]),
        "verified": {"overall": metrics(verified), "by_protocol": by_protocol},
        "development": metrics(development), "variants": metrics(variants),
        "variant_robustness": variant_comparisons,
        "paired": paired_differences(records), "retrieval": retrieval,
        "interpretation": "Observed results for this model and run only. Public variants are development probes, not hidden generalization evidence. Unknown cost or usage remains null.",
    }


def markdown(summary: dict) -> str:
    lines = [f"# Baseline run {summary['run_id']}", "",
             f"Execution class: **{summary['execution_class']}**. Records: {summary['record_count']} / {summary['declared_run_count']} declared.", "",
             "Verified-case scores and development diagnostics are reported separately. Unknown resource values remain null.", "",
             "| Track | Runs | Scored | Mean | Median | Success rate | Unresolved rate |",
             "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for label, data in (("Verified", summary["verified"]["overall"]), ("Development", summary["development"]), ("Variants", summary["variants"])):
        def value(item: Any) -> str:
            return "null" if item is None else f"{item:.4f}" if isinstance(item, float) else str(item)
        lines.append(f"| {label} | {data['runs']} | {data['scored']} | {value(data['mean_score'])} | {value(data['median_score'])} | {value(data['task_success_rate'])} | {value(data['unresolved_rate'])} |")
    lines += ["", "## Verified cases by protocol", "",
              "| Protocol | Scored | Mean score | Successes | Input tokens | Tool calls | Wall seconds | Cost |",
              "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for protocol, data in summary["verified"]["by_protocol"].items():
        def fmt(value: Any) -> str:
            return "null" if value is None else f"{value:.4f}" if isinstance(value, float) else str(value)
        lines.append(f"| {protocol} | {data['scored']} | {fmt(data['mean_score'])} | {data['successes']} | {fmt(data['usage']['input']['total'])} | {data['tool_calls']} | {fmt(data['wall_time_seconds'])} | {fmt(data['cost']['amount'])} |")
    lines += ["", "Verified score distribution: `" + json.dumps(summary["verified"]["overall"]["score_distribution"]) + "`.",
              "Verified tokens, tool calls, wall seconds, and monetary cost per successful case: `" +
              json.dumps({key: summary["verified"]["overall"][key] for key in
                          ("tokens_per_success", "tool_calls_per_success", "wall_seconds_per_success")}
                         | {"cost_per_success": summary["verified"]["overall"]["cost"]["per_success"]}) + "`."]
    lines += ["", "## Paired protocol differences", "",
              "| Case | Assisted | Baseline | Score delta | Input-token delta | Output-token delta | Cost delta | Tool-call delta |",
              "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |"]
    for item in summary["paired"]["per_case"]:
        lines.append(f"| {item['case_id']} | {item['assisted_protocol']} | {item['baseline_protocol']} | {item['score_delta']} | {item['input_token_delta']} | {item['output_token_delta']} | {item['cost_delta']} | {item['tool_call_delta']} |")
    lines += ["", "## Variant robustness", "",
              "| Parent case | Variant | Protocol | Canonical score | Variant score | Delta |",
              "| --- | --- | --- | ---: | ---: | ---: |"]
    for item in summary["variant_robustness"]:
        lines.append(f"| {item['case_id']} | {item['variant_id']} | {item['protocol']} | {item['canonical_score']} | {item['variant_score']} | {item['score_delta']} |")
    lines += ["", "## Limits", "", summary["interpretation"], ""]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--write", action="store_true")
    action.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    try:
        manifest, records = load_run(args.run_dir)
        summary = analyze(manifest, records)
        outputs = {args.run_dir / "summary.json": json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
                   args.run_dir / "summary.md": markdown(summary)}
        if args.write:
            for path, content in outputs.items():
                if path.exists() and path.read_text(encoding="utf-8") != content:
                    raise ValueError(f"derived analysis already exists with different bytes: {path}")
                path.write_text(content, encoding="utf-8", newline="\n")
        if args.check:
            stale = [str(path) for path, content in outputs.items()
                     if not path.exists() or path.read_text(encoding="utf-8") != content]
            if stale:
                raise ValueError("missing or stale analysis: " + ", ".join(stale))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Baseline analysis failed: {exc}", file=sys.stderr)
        return 1
    print(f"Analysis: {summary['record_count']} records; {summary['verified']['overall']['scored']} verified scores")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
