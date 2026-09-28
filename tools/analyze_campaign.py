"""Validate and summarize a frozen, multi-system 0.2.0-rc1 campaign.

The campaign index names immutable public runs and public-safe hidden
attestations. This module never reads a private hidden bundle or invokes an
agent. Its evidence-tree digest frames sorted relative paths and exact file
bytes under the domain ``public-campaign-run-evidence-tree-v1``.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path, PureWindowsPath
import re
from statistics import mean
import sys
from typing import Any

from tools.analyze_baseline import load_run, metrics, paired_differences


ROOT = Path(__file__).resolve().parents[1]
RELEASE_ID = "0.2.0-rc1"
PROTOCOLS = ("closed_book", "case_assisted", "tool_assisted", "case_and_tool_assisted")
CASES = ("SEED-1-1", "SEED-1-5", "SEED-1-7", "SEED-2-1", "SEED-2-2",
         "SEED-3-1", "SEED-3-7", "SEED-4-2", "SEED-5-5")
TREE_DOMAIN = b"public-campaign-run-evidence-tree-v1\0"
HEX = re.compile(r"[0-9a-f]{64}\Z")


def _sha_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _indexed_path(root: Path, value: str) -> Path:
    if not isinstance(value, str) or not value or Path(value).is_absolute() or "\\" in value:
        raise ValueError("campaign paths must be repository-relative POSIX paths")
    path = (root / value).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("campaign path escapes repository")
    return path


def evidence_commitment(run_dir: Path) -> dict[str, Any]:
    """Commit to every frozen public run file, rejecting links and partials."""
    if not run_dir.is_dir() or not (run_dir / "manifest.json").is_file():
        raise ValueError(f"run directory or manifest missing: {run_dir}")
    entries = list(run_dir.rglob("*"))
    if any(path.is_symlink() for path in entries):
        raise ValueError("run evidence contains a symbolic link")
    files = sorted((path for path in entries if path.is_file()),
                   key=lambda path: path.relative_to(run_dir).as_posix())
    if any(path.name.endswith(".partial") for path in files):
        raise ValueError("run evidence contains an unfinished partial file")
    digest = hashlib.sha256(TREE_DOMAIN)
    for path in files:
        name = path.relative_to(run_dir).as_posix().encode("utf-8")
        content = path.read_bytes()
        digest.update(len(name).to_bytes(8, "big"))
        digest.update(name)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return {"manifest_sha256": _sha_bytes((run_dir / "manifest.json").read_bytes()),
            "evidence_tree_sha256": digest.hexdigest(), "file_count": len(files)}


def _run(index: dict[str, Any], root: Path) -> tuple[dict, list[dict]]:
    if set(index) != {"run_dir", "manifest_sha256", "evidence_tree_sha256"}:
        raise ValueError("run index needs run_dir, manifest_sha256, evidence_tree_sha256")
    if any(not isinstance(index[key], str) or not HEX.fullmatch(index[key])
           for key in ("manifest_sha256", "evidence_tree_sha256")):
        raise ValueError("run index contains an invalid SHA-256")
    run_dir = _indexed_path(root, index["run_dir"])
    observed = evidence_commitment(run_dir)
    for key in ("manifest_sha256", "evidence_tree_sha256"):
        if index[key] != observed[key]:
            raise ValueError(f"{index['run_dir']} {key} differs from immutable evidence")
    manifest, records = load_run(run_dir)
    if manifest["execution_class"] != "real":
        raise ValueError("dry-run evidence cannot enter a real campaign")
    expected = {(selection["case_id"], selection["track"],
                 PureWindowsPath(selection["variant_path"]).stem if selection["variant_path"] else None,
                 protocol)
                for selection in manifest["selections"] for protocol in manifest["protocol_ids"]}
    observed_rows = [(record["selection"]["case_id"], record["selection"]["track"],
                      record["selection"]["variant_id"], record["protocol"]["id"])
                     for record in records]
    if len(observed_rows) != len(expected) or set(observed_rows) != expected:
        raise ValueError(f"{manifest['run_id']} has missing, extra, or duplicate result records")
    if any(record["agent_identity"] != _identity(manifest) for record in records):
        raise ValueError("result agent identity differs from frozen manifest")
    return manifest, records


def _identity(manifest: dict) -> dict:
    agent = manifest["agent"]
    return {"provider": agent["provider"], "model_id": agent["model_id"],
            "model_version": agent["model_version"], "framework": agent["framework"],
            "scaffold_id": agent["scaffold_id"],
            "system_prompt_version": manifest["system_prompt_version"],
            "adapter_type": agent["adapter_type"]}


def _key(identity: dict) -> str:
    return json.dumps(identity, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _known_sum(values: list[Any]) -> float | int | None:
    if not values or any(isinstance(value, bool) or not isinstance(value, (int, float))
                         or not math.isfinite(value) for value in values):
        return None
    return sum(values)


def _efficiency(records: list[dict]) -> dict:
    successes = sum(record["status"] == "completed" and record["score_result"] is not None
                    and record["score_result"]["scores"]["capped_total"] == 1.0
                    for record in records)
    tokens = _known_sum([record["usage"]["total"] for record in records])
    costs = [record["cost"] for record in records]
    priced = bool(costs) and all(isinstance(cost, dict) and
                                 isinstance(cost.get("amount"), (int, float)) and
                                 not isinstance(cost.get("amount"), bool) for cost in costs)
    provenances = {(cost.get("currency"), cost.get("pricing_reference"),
                    cost.get("pricing_snapshot_utc")) for cost in costs if isinstance(cost, dict)}
    total_cost = _known_sum([cost["amount"] for cost in costs]) if priced and len(provenances) == 1 else None
    wall = sum(record["wall_time_seconds"] for record in records)
    tools = sum(len(record["tool_calls"]) for record in records)
    return {"attempted_cases": len(records), "full_successes": successes,
            "tokens_total": tokens, "wall_seconds_total": wall, "tool_calls_total": tools,
            "cost_total": total_cost,
            "cost_currency": next(iter(provenances))[0] if total_cost is not None else None,
            "cost_per_attempted_case": total_cost / len(records) if total_cost is not None else None,
            "cost_per_successful_case": total_cost / successes if total_cost is not None and successes else None,
            "tokens_per_successful_case": tokens / successes if tokens is not None and successes else None,
            "wall_seconds_per_successful_case": wall / successes if successes else None,
            "tool_calls_per_successful_case": tools / successes if successes else None}


def _retrieval(records: list[dict]) -> dict:
    selected = [record["retrieval"] for record in records if isinstance(record["retrieval"], dict)]
    return {"records_with_retrieval": len(selected),
            "items": sum(len(item.get("retrieved_ids", [])) for item in selected),
            "tokens": _known_sum([item.get("total_retrieved_tokens") for item in selected]) if selected else 0,
            "latency_seconds": _known_sum([item.get("latency_seconds") for item in selected]) if selected else 0}


def _formal(release: dict, runs: list[tuple[dict, list[dict]]]) -> list[dict]:
    groups: dict[str, dict[str, Any]] = defaultdict(lambda: {"runs": [], "records": []})
    for manifest, records in runs:
        if manifest["release_id"] != RELEASE_ID:
            raise ValueError("formal run uses the wrong frozen release")
        if (any(selection["track"] != "verified" or selection["variant_path"] is not None
                or selection["case_id"] not in CASES for selection in manifest["selections"])
                or any(protocol not in PROTOCOLS for protocol in manifest["protocol_ids"])):
            raise ValueError("formal run includes a nonverified case, variant, or protocol")
        if any(manifest["retry_policy"][key] != 0 for key in manifest["retry_policy"]):
            raise ValueError("formal comparison requires zero automatic retries")
        key = _key(_identity(manifest))
        groups[key]["runs"].append(manifest["run_id"])
        groups[key]["records"].extend(records)
    output = []
    for key, group in sorted(groups.items()):
        records = group["records"]
        rows = [(record["selection"]["case_id"], record["protocol"]["id"]) for record in records]
        required = {(case_id, protocol) for case_id in CASES for protocol in PROTOCOLS}
        if len(rows) != len(required) or set(rows) != required:
            raise ValueError("each formal system requires exactly nine cases under four protocols")
        for record in records:
            case_id = record["selection"]["case_id"]
            pinned = release["cases"][case_id]
            selection = record["selection"]
            if (selection["case_revision"] != pinned["case_revision"] or
                    selection["case_content_sha256"] != pinned["case_content_sha256"]):
                raise ValueError(f"{case_id} differs from frozen release case pin")
            score = record["score_result"]
            if score is not None and (score["evaluator_version"] != pinned["evaluator_version"] or
                                      score["evaluator_fingerprint"] != pinned["evaluator_fingerprint"]):
                raise ValueError(f"{case_id} differs from frozen evaluator pin")
        paired = paired_differences(records)
        if len(paired["per_case"]) != len(CASES) * 5:
            raise ValueError("formal paired protocol matrix is incomplete")
        per_case = []
        for case_id in CASES:
            cells = {}
            for record in records:
                if record["selection"]["case_id"] == case_id:
                    cells[record["protocol"]["id"]] = {
                        "score": (record["score_result"] or {}).get("scores", {}).get("capped_total"),
                        "status": record["status"], "failure_class": record["failure_class"],
                        "failure_mode": (record["score_result"] or {}).get("failure_mode"),
                        "first_attempt_success": record["first_attempt_success"]}
            per_case.append({"case_id": case_id, "protocols": cells})
        by_protocol = {protocol: {"metrics": metrics([record for record in records
                                                       if record["protocol"]["id"] == protocol]),
                                  "efficiency": _efficiency([record for record in records
                                                             if record["protocol"]["id"] == protocol]),
                                  "retrieval": _retrieval([record for record in records
                                                            if record["protocol"]["id"] == protocol])}
                       for protocol in PROTOCOLS}
        output.append({"agent_identity": json.loads(key), "run_ids": sorted(group["runs"]),
                       "record_count": len(records), "metrics": metrics(records),
                       "efficiency": _efficiency(records), "by_protocol": by_protocol,
                       "per_case": per_case, "paired": paired})
    return output


def _variants(runs: list[tuple[dict, list[dict]]]) -> list[dict]:
    output = []
    for manifest, records in runs:
        if manifest["release_id"] not in {"0.1.0-rc1", RELEASE_ID}:
            raise ValueError("variant probe uses an unsupported release")
        if any(selection["track"] not in {"public_variant", "verified"} for selection in manifest["selections"]):
            raise ValueError("variant probe contains a private or development selection")
        variants = [record for record in records if record["selection"]["track"] == "public_variant"]
        if not variants:
            raise ValueError("variant probe has no public variants")
        if any(record["selection"]["track"] == "private_variant" for record in records):
            raise ValueError("private variants cannot enter a public probe")
        parents = {(record["selection"]["case_id"], record["protocol"]["id"]): record
                   for record in records if record["selection"]["track"] == "verified"}
        comparisons = []
        for record in variants:
            parent = parents.get((record["selection"]["case_id"], record["protocol"]["id"]))
            score = (record["score_result"] or {}).get("scores", {}).get("capped_total")
            parent_score = (parent["score_result"] or {}).get("scores", {}).get("capped_total") if parent else None
            comparisons.append({"case_id": record["selection"]["case_id"],
                                "variant_id": record["selection"]["variant_id"],
                                "protocol": record["protocol"]["id"], "score": score,
                                "canonical_score": parent_score,
                                "score_delta": score - parent_score if score is not None and parent_score is not None else None})
        output.append({"run_id": manifest["run_id"], "release_id": manifest["release_id"],
                       "agent_identity": _identity(manifest), "public_variant_count": len(variants),
                       "metrics": metrics(variants), "efficiency": _efficiency(variants),
                       "per_variant": comparisons})
    return sorted(output, key=lambda item: item["run_id"])


def _hidden(indexes: list[dict], root: Path) -> list[dict]:
    output = []
    bundle_commitments = set()
    run_ids = set()
    for index in indexes:
        if set(index) != {"path", "sha256"} or not isinstance(index["sha256"], str) or not HEX.fullmatch(index["sha256"]):
            raise ValueError("hidden index needs path and sha256")
        path = _indexed_path(root, index["path"])
        if _sha_bytes(path.read_bytes()) != index["sha256"]:
            raise ValueError("hidden attestation bytes differ from campaign index")
        value = json.loads(path.read_text(encoding="utf-8"))
        evidence = value.get("run_evidence") or {}
        commitment = value.get("commitment") or {}
        if (value.get("execution_class") != "real" or value.get("protocol") != "closed_book" or
                commitment.get("benchmark_release_id") != RELEASE_ID or
                value.get("attestation_type") != "private_hidden_real_smoke" or
                not HEX.fullmatch(evidence.get("evidence_tree_sha256", "")) or
                not HEX.fullmatch(evidence.get("manifest_sha256", "")) or
                value.get("linked_result_records") != value.get("selected_instances") or
                value.get("selected_instances") != commitment.get("instance_count") or
                value.get("completed_instances", 0) > value.get("selected_instances", 0) or
                value.get("raw_hidden_instances_published") is not False or
                value.get("raw_model_responses_published") is not False):
            raise ValueError("hidden attestation lacks required real closed-book evidence")
        if value["run_id"] in run_ids:
            raise ValueError("duplicate hidden run attestation")
        run_ids.add(value["run_id"])
        bundle_commitments.add(json.dumps(commitment, ensure_ascii=False, sort_keys=True,
                                          separators=(",", ":")))
        output.append({"path": index["path"], "sha256": index["sha256"],
                       "run_id": value["run_id"], "bundle_id": commitment["bundle_id"],
                       "model_id": value["model_id"], "model_version": value["model_version"],
                       "adapter_type": value["adapter_type"], "protocol": value["protocol"],
                       "selected_instances": value["selected_instances"],
                       "completed_instances": value["completed_instances"],
                       "aggregate_score": value["aggregate_score"],
                       "tokens": value["tokens"], "cost": value["cost"],
                       "failure_categories": value["failure_categories"],
                       "run_evidence": evidence})
    if len(bundle_commitments) > 1:
        raise ValueError("hidden systems must share one frozen private bundle")
    return sorted(output, key=lambda item: item["run_id"])


def analyze_campaign(index_path: Path, *, root: Path = ROOT) -> dict:
    campaign = json.loads(index_path.read_text(encoding="utf-8"))
    if (campaign.get("schema_version") != "1.0.0" or campaign.get("release_id") != RELEASE_ID or
            not isinstance(campaign.get("campaign_id"), str) or
            not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{2,79}", campaign["campaign_id"])):
        raise ValueError("campaign identity or frozen release is invalid")
    for name in ("formal_runs", "variant_runs", "hidden_attestations"):
        if not isinstance(campaign.get(name), list):
            raise ValueError(f"campaign {name} must be a list")
    if not campaign["formal_runs"]:
        raise ValueError("campaign has no formal run evidence")
    paths = [item["run_dir"] for name in ("formal_runs", "variant_runs") for item in campaign[name]]
    if len(paths) != len(set(paths)):
        raise ValueError("run directory is indexed more than once")
    release = json.loads((root / "benchmark" / "releases" / f"{RELEASE_ID}.json").read_text(encoding="utf-8"))
    if set(release["cases"]) != set(CASES):
        raise ValueError("frozen release no longer contains exactly the expected nine cases")
    formal = [_run(item, root) for item in campaign["formal_runs"]]
    variant = [_run(item, root) for item in campaign["variant_runs"]]
    systems = _formal(release, formal)
    variants = _variants(variant)
    hidden = _hidden(campaign["hidden_attestations"], root)
    formal_identities = {(system["agent_identity"]["model_id"],
                          system["agent_identity"]["model_version"],
                          system["agent_identity"]["adapter_type"]) for system in systems}
    if any((item["model_id"], item["model_version"], item["adapter_type"]) not in formal_identities
           for item in hidden):
        raise ValueError("hidden attestation model/adapter is absent from formal systems")
    return {"schema_version": "1.0.0", "campaign_id": campaign["campaign_id"],
            "release_id": RELEASE_ID, "formal_case_ids": list(CASES),
            "protocol_ids": list(PROTOCOLS), "formal_system_count": len(systems),
            "formal_record_count": sum(item["record_count"] for item in systems),
            "systems": systems, "public_variant_probe": variants,
            "hidden_family_disjoint": hidden,
            "limitations": ["Nine public cases support descriptive paired comparisons, not broad model rankings.",
                            "Public development variants can use the separate 0.1.0-rc1 parent release and never enter 0.2.0-rc1 formal scores.",
                            "A public hidden attestation binds a retained private run but cannot independently reveal or validate private task content."]}


def markdown(summary: dict) -> str:
    lines = [f"# Campaign {summary['campaign_id']}", "",
             f"Formal benchmark: **{summary['release_id']}**, {summary['formal_system_count']} systems, "
             f"{summary['formal_record_count']} public verified records.", "",
             "The verified matrix, public development variants, and family-disjoint hidden runs are separate evidence tracks.", "",
             "| System | Protocol | Mean | Median | Full success | First attempt | Invalid contract | Physics failure | Unresolved | Tokens | Wall seconds | Tool calls | Retrieval tokens | Cost |",
             "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    def fmt(value: Any) -> str:
        return "null" if value is None else f"{value:.4f}" if isinstance(value, float) else str(value)
    for system in summary["systems"]:
        name = system["agent_identity"]["provider"] + "/" + system["agent_identity"]["model_id"] + "/" + system["agent_identity"]["framework"]
        for protocol in PROTOCOLS:
            row = system["by_protocol"][protocol]
            data, eff = row["metrics"], row["efficiency"]
            lines.append("| " + " | ".join(map(fmt, [name, protocol, data["mean_score"], data["median_score"],
                                                    data["task_success_rate"], data["first_attempt_success_rate"],
                                                    data["invalid_contract_rate"], data["physics_failure_rate"],
                                                    data["unresolved_rate"], eff["tokens_total"], eff["wall_seconds_total"],
                                                    eff["tool_calls_total"], row["retrieval"]["tokens"], eff["cost_total"]])) + " |")
        lines += ["", f"## {name}", "", "### Per-case scores", "",
                  "| Case | Closed | Case-assisted | Tool-assisted | Combined |",
                  "| --- | ---: | ---: | ---: | ---: |"]
        for case in system["per_case"]:
            lines.append("| " + case["case_id"] + " | " + " | ".join(fmt(case["protocols"][protocol]["score"]) for protocol in PROTOCOLS) + " |")
        lines += ["", "### Paired protocol differences", "",
                  "| Case | Contrast | Score delta | Input-token delta | Total-token delta | Wall-second delta | Tool-call delta | Cost delta |",
                  "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
        for pair in system["paired"]["per_case"]:
            contrast = pair["assisted_protocol"] + " − " + pair["baseline_protocol"]
            lines.append("| " + " | ".join(map(fmt, [pair["case_id"], contrast, pair["score_delta"],
                                                     pair["input_token_delta"], pair["total_token_delta"],
                                                     pair["wall_time_delta_seconds"], pair["tool_call_delta"],
                                                     pair["cost_delta"]])) + " |")
        lines += ["", "Resource normalization (total spend over all attempted verified cases): `" +
                  json.dumps(system["efficiency"], sort_keys=True) + "`.", ""]
    lines += ["## Public development variant probe", "",
              "These variants remain development evidence. Their parent release is reported for each run and is never pooled with the formal 0.2.0-rc1 score.", "",
              "| Run | Parent release | System | Variants | Mean score | Full successes |",
              "| --- | --- | --- | ---: | ---: | ---: |"]
    for row in summary["public_variant_probe"]:
        lines.append("| " + " | ".join(map(fmt, [row["run_id"], row["release_id"],
                                                 row["agent_identity"]["model_id"], row["public_variant_count"],
                                                 row["metrics"]["mean_score"], row["metrics"]["successes"]])) + " |")
    lines += ["", "## Family-disjoint hidden evaluation", "",
              "Only public-safe attestation aggregates appear here. Private instances and raw answers remain external.", "",
              "| Run | Model | Bundle | Protocol | Completed / selected | Aggregate score | Tokens | Cost | Evidence tree |",
              "| --- | --- | --- | --- | ---: | ---: | ---: | ---: | --- |"]
    for row in summary["hidden_family_disjoint"]:
        lines.append("| " + " | ".join(map(fmt, [row["run_id"], row["model_id"], row["bundle_id"],
                                                 row["protocol"], f"{row['completed_instances']} / {row['selected_instances']}",
                                                 row["aggregate_score"], row["tokens"].get("total"),
                                                 (row["cost"] or {}).get("amount"),
                                                 row["run_evidence"]["evidence_tree_sha256"]])) + " |")
    lines += ["", "## Limits", ""] + [f"- {item}" for item in summary["limitations"]] + [""]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("campaign", nargs="?", type=Path)
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--write", action="store_true")
    action.add_argument("--check", action="store_true")
    action.add_argument("--hash-run", type=Path, help="print hashes for one completed public run")
    args = parser.parse_args(argv)
    try:
        if args.hash_run:
            print(json.dumps(evidence_commitment(args.hash_run.resolve()), sort_keys=True))
            return 0
        if args.campaign is None:
            parser.error("campaign path is required unless --hash-run is used")
        summary = analyze_campaign(args.campaign)
        summary_path = args.campaign.parent / "summary.json"
        report_path = ROOT / "docs" / "results" / f"{summary['campaign_id']}.md"
        outputs = {summary_path: json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                   report_path: markdown(summary)}
        if args.write:
            for path, content in outputs.items():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8", newline="\n")
        if args.check:
            stale = [str(path) for path, content in outputs.items()
                     if not path.exists() or path.read_text(encoding="utf-8") != content]
            if stale:
                raise ValueError("missing or stale campaign analysis: " + ", ".join(stale))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Campaign analysis failed: {exc}", file=sys.stderr)
        return 1
    print(f"Campaign analysis: {summary['formal_record_count']} formal records across {summary['formal_system_count']} systems")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
