"""Derive and verify public-safe claims from a private hidden run.

The evidence-tree digest commits to every regular file under the frozen run
directory, including its manifest, results, protocols, logs, and environment.
No private path, task, seed, or raw answer is placed in the attestation.
"""

from __future__ import annotations

from collections import Counter
import hashlib
import math
from pathlib import Path
from typing import Any


TREE_DOMAIN = b"hidden-run-evidence-tree-v1\0"
PRICE_FIELDS = ("currency", "pricing_reference", "pricing_snapshot_utc")


def _aggregate_cost(costs: list[Any], pricing_snapshot: Any) -> dict[str, Any] | None:
    """Sum only runner cost objects from one documented price snapshot."""
    if all(cost is None for cost in costs):
        return None
    if any(cost is None for cost in costs):
        raise ValueError("known and unknown result costs cannot be aggregated")
    if not isinstance(pricing_snapshot, dict):
        raise ValueError("priced results lack a manifest pricing snapshot")
    required = {"amount", *PRICE_FIELDS}
    provenance = None
    amounts = []
    for cost in costs:
        if not isinstance(cost, dict) or set(cost) != required:
            raise ValueError("invalid runner cost object")
        amount = cost["amount"]
        if (isinstance(amount, bool) or not isinstance(amount, (int, float)) or
                not math.isfinite(amount) or amount < 0):
            raise ValueError("invalid result cost amount")
        current = tuple(cost[field] for field in PRICE_FIELDS)
        if any(not isinstance(value, str) or not value for value in current):
            raise ValueError("result cost lacks pricing provenance")
        if current != tuple(pricing_snapshot.get(field) for field in PRICE_FIELDS):
            raise ValueError("result cost differs from manifest pricing snapshot")
        if provenance is not None and current != provenance:
            raise ValueError("incompatible result cost provenance")
        provenance = current
        amounts.append(float(amount))
    return {"amount": math.fsum(amounts), **dict(zip(PRICE_FIELDS, provenance))}


def evidence_commitment(run_dir: Path) -> dict[str, Any]:
    """Hash sorted relative paths and exact file bytes with length framing."""
    from tools.hidden_eval import _external

    run = _external(run_dir)
    if not run.is_dir():
        raise ValueError("private run directory is missing")
    entries = list(run.rglob("*"))
    if any(p.is_symlink() for p in entries):
        raise ValueError("private run evidence cannot contain file links")
    paths = sorted((p for p in entries if p.is_file()),
                   key=lambda p: p.relative_to(run).as_posix())
    if not paths or not (run / "manifest.json").is_file():
        raise ValueError("private run evidence lacks a manifest")
    digest = hashlib.sha256(TREE_DOMAIN)
    for path in paths:
        if not path.resolve().is_relative_to(run):
            raise ValueError("private run evidence cannot contain file links")
        name = path.relative_to(run).as_posix().encode("utf-8")
        content = path.read_bytes()
        digest.update(len(name).to_bytes(8, "big"))
        digest.update(name)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return {"schema_version": "1.0.0", "evidence_tree_sha256": digest.hexdigest(),
            "manifest_sha256": hashlib.sha256((run / "manifest.json").read_bytes()).hexdigest(),
            "file_count": len(paths)}


def derive_real_attestation(bundle_dir: Path, run_dir: Path, *,
                            family_map: Path | None = None,
                            public_plan: Path | None = None) -> dict[str, Any]:
    """Recompute a real-run summary; never trust a hand-authored score."""
    from tools.hidden_eval import (FAMILY_MAP, PUBLIC_PLAN, _external, _read,
                                   audit_bundle, audit_result_linkage)

    kwargs = {"family_map": family_map or FAMILY_MAP, "public_plan": public_plan or PUBLIC_PLAN}
    commitment = audit_bundle(bundle_dir, **kwargs)
    linkage = audit_result_linkage(bundle_dir, run_dir, **kwargs)
    run = _external(run_dir)
    manifest = _read(run / "manifest.json")
    if manifest.get("execution_class") != "real":
        raise ValueError("public real-run attestation requires a real execution")
    results = [_read(p) for p in sorted((run / "results").glob("*.json"))]
    if len(results) != linkage["linked_result_records"]:
        raise ValueError("result count differs from linked records")
    protocols = manifest.get("protocol_ids")
    expected_count = linkage["selected_instances"] * len(protocols or [])
    if not protocols or len(results) != expected_count:
        raise ValueError("private run has missing or extra protocol results")
    identities = set()
    protocols_seen = set()
    selection_protocols = set()
    scores = []
    failures: Counter[str] = Counter()
    usage: Counter[str] = Counter()
    costs = []
    for result in results:
        if result.get("run_id") != manifest.get("run_id") or result.get("execution_class") != "real":
            raise ValueError("result run identity/class differs from manifest")
        identity = result.get("agent_identity") or {}
        identities.add((identity.get("adapter_type"), identity.get("model_id"),
                        identity.get("model_version")))
        protocol = (result.get("protocol") or {}).get("id")
        if protocol not in protocols:
            raise ValueError("result protocol differs from manifest")
        protocols_seen.add(protocol)
        key = ((result.get("selection") or {}).get("variant_id"), protocol)
        if key in selection_protocols:
            raise ValueError("duplicate result for private instance/protocol")
        selection_protocols.add(key)
        if result.get("status") != "completed":
            raise ValueError("real smoke attestation requires completed results")
        score = (result.get("score_result") or {}).get("scores", {}).get("capped_total")
        if not isinstance(score, (int, float)) or isinstance(score, bool) or not 0 <= score <= 1:
            raise ValueError("completed result lacks a bounded score")
        scores.append(float(score))
        failure = (result.get("score_result") or {}).get("failure_mode")
        if not isinstance(failure, str) or not failure:
            raise ValueError("result lacks a failure mode")
        failures[failure] += 1
        for field in ("cached_input", "input", "output", "reasoning", "total"):
            value = (result.get("usage") or {}).get(field)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError(f"result lacks valid {field} usage")
            usage[field] += value
        costs.append(result.get("cost"))
    if len(identities) != 1 or len(protocols_seen) != 1:
        raise ValueError("real smoke attestation requires one model and protocol")
    adapter, model_id, model_version = next(iter(identities))
    if (adapter, model_id, model_version) != (
        manifest.get("agent", {}).get("adapter_type"),
        manifest.get("agent", {}).get("model_id"),
        manifest.get("agent", {}).get("model_version"),
    ):
        raise ValueError("result model identity differs from manifest")
    return {"attestation_type": "private_hidden_real_smoke", "commitment": commitment,
            "run_evidence": evidence_commitment(run), "run_id": manifest["run_id"],
            "execution_class": "real", "adapter_type": adapter,
            "model_id": model_id, "model_version": model_version,
            "protocol": next(iter(protocols_seen)),
            "selected_instances": linkage["selected_instances"],
            "linked_result_records": linkage["linked_result_records"],
            "completed_instances": len(scores), "aggregate_score": sum(scores) / len(scores),
            "failure_categories": dict(sorted(failures.items())),
            "tokens": dict(usage),
            "cost": _aggregate_cost(costs, manifest.get("pricing_snapshot")),
            "raw_hidden_instances_published": False, "raw_model_responses_published": False}


def audit_real_attestation(bundle_dir: Path, run_dir: Path, attestation_path: Path, *,
                           family_map: Path | None = None,
                           public_plan: Path | None = None) -> dict[str, Any]:
    """Reject any change to public claims or to the frozen private run tree."""
    from tools.hidden_eval import _read

    actual = _read(attestation_path)
    expected = derive_real_attestation(bundle_dir, run_dir, family_map=family_map,
                                       public_plan=public_plan)
    if actual != expected:
        raise ValueError("public attestation differs from committed private run evidence")
    return {"bundle_id": expected["commitment"]["bundle_id"],
            "run_id": expected["run_id"], "evidence_tree_sha256":
            expected["run_evidence"]["evidence_tree_sha256"], "verified": True}
