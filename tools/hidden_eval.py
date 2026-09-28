"""Family-disjoint, private-seed evaluation bundles and public-safe commitments.

The private policy and bundle must live outside the checkout. No task, seed, or
raw response is written to the public commitment.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from tools.validate_cases import ROOT


DIRECTORY = ROOT / "benchmark" / "hidden_eval"
FAMILY_MAP = DIRECTORY / "family_map.v1.json"
POLICY_SCHEMA = DIRECTORY / "private_policy.v1.schema.json"
COMMITMENT_SCHEMA = DIRECTORY / "commitment.v1.schema.json"
PUBLIC_PLAN = ROOT / "benchmark" / "variants" / "public_plan.json"
REGISTRY = {("0.1.0", "0.1.0-rc1"): "tools.variants",
            ("0.2.0", "0.2.0-rc1"): "tools.variants_vnext"}
POLICY_VERSION = "1.0.0"
COMMITMENT_VERSION = "1.0.0"


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain an object")
    return value


def _write_new(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2)
        stream.write("\n")


def _validate_schema(value: dict[str, Any], path: Path) -> None:
    schema = _read(path)
    Draft202012Validator.check_schema(schema)
    errors = sorted(Draft202012Validator(schema).iter_errors(value), key=lambda e: list(map(str, e.path)))
    if errors:
        raise ValueError(f"{path.name}: {errors[0].message}")


def _external(path: Path) -> Path:
    resolved = path.resolve()
    if resolved.is_relative_to(ROOT.resolve()):
        raise ValueError("private policy and bundle paths must be outside the repository")
    return resolved


def _adapter(version: str, release: str):
    name = REGISTRY.get((version, release))
    if name is None:
        raise ValueError("generator/release combination is not registered")
    try:
        module = importlib.import_module(name)
    except ModuleNotFoundError as exc:
        if exc.name == name:
            raise ValueError(f"registered generator is unavailable: {name}") from exc
        raise
    if getattr(module, "VERSION", None) != version or getattr(module, "RELEASE", None) != release:
        raise ValueError("registered generator version/release disagrees with policy")
    for member in ("SUPPORTED", "TYPES", "generate_variant", "load_variant", "_expected_answer"):
        if not hasattr(module, member):
            raise ValueError(f"registered generator lacks {member}")
    return module


def validate_family_map(path: Path = FAMILY_MAP) -> dict[str, Any]:
    mapping = _read(path)
    if mapping.get("schema_version") != "1.0.0" or not isinstance(mapping.get("cases"), dict):
        raise ValueError("unsupported family map")
    from tools.scoring_runtime import SCORERS as RC1_SCORERS
    try:
        from tools.vnext.scoring_runtime import SCORERS as VNEXT_SCORERS
    except ModuleNotFoundError:
        VNEXT_SCORERS = {}
    case_ids = {p.stem for p in (ROOT / "benchmark" / "cases").glob("*.yaml")}
    if set(mapping["cases"]) != case_ids:
        raise ValueError("family map must cover each of the 64 canonical case IDs exactly")
    for source, row in mapping["cases"].items():
        if not isinstance(row, dict) or row.get("case_id") != source:
            raise ValueError(f"family map case mismatch: {source}")
        for field in ("concept_family", "scorer_family", "release_verification_status",
                      "public_variant_eligible", "hidden_variant_eligible"):
            if field not in row:
                raise ValueError(f"family map missing {field}: {source}")
        if not isinstance(row["concept_family"], str) or not row["concept_family"]:
            raise ValueError(f"concept family missing: {source}")
        scorer_registry = RC1_SCORERS if row.get("release_id") == "0.1.0-rc1" else VNEXT_SCORERS
        if row["scorer_family"] != scorer_registry.get(source, "none"):
            raise ValueError(f"scorer family mismatch: {source}")
        if row["release_verification_status"] not in {"release_verified", "development"}:
            raise ValueError(f"invalid release status: {source}")
        release = row.get("release_id")
        if row["release_verification_status"] == "release_verified":
            if not isinstance(release, str):
                raise ValueError(f"verified source lacks release ID: {source}")
            manifest_path = ROOT / "benchmark" / "releases" / f"{release}.json"
            if not manifest_path.is_file():
                raise ValueError(f"verified source release is unavailable: {source}")
            pin = _read(manifest_path)["cases"].get(source)
            if pin is None or pin.get("status") != "release_verified":
                raise ValueError(f"source is not release-pinned: {source}")
        elif release is not None:
            raise ValueError(f"development source cannot claim release ID: {source}")
        for field in ("public_variant_eligible", "hidden_variant_eligible"):
            if not isinstance(row[field], bool):
                raise ValueError(f"{field} must be boolean: {source}")
        if row["hidden_variant_eligible"]:
            if row["release_verification_status"] != "release_verified":
                raise ValueError(f"unverified hidden source: {source}")
            if not isinstance(row.get("generator_version"), str) or not row.get("generator_template"):
                raise ValueError(f"hidden source lacks generator metadata: {source}")
            if not isinstance(row.get("variant_types"), list) or not row["variant_types"]:
                raise ValueError(f"hidden source lacks variant types: {source}")
            if (row["generator_version"], release) not in REGISTRY:
                raise ValueError(f"hidden source has unregistered generator/release: {source}")
    return mapping


def public_development_sources(plan_path: Path = PUBLIC_PLAN) -> set[str]:
    plan = _read(plan_path)
    if not isinstance(plan.get("variants"), list):
        raise ValueError("public development manifest lacks variants")
    return {row["parent_case_id"] for row in plan["variants"]}


def check_disjoint(policy: dict[str, Any], *, family_map: dict[str, Any],
                   public_plan: Path = PUBLIC_PLAN) -> None:
    """Enforce source, concept-family, and template exclusion before generation."""
    cases = family_map["cases"]
    public_sources = public_development_sources(public_plan)
    unknown = public_sources - cases.keys()
    if unknown:
        raise ValueError(f"unknown public source: {sorted(unknown)}")
    public_families = {cases[source]["concept_family"] for source in public_sources}
    public_templates = {cases[source].get("generator_template") for source in public_sources}
    seen: set[tuple[str, str, int]] = set()
    for item in policy["selections"]:
        source, kind = item["parent_case_id"], item["variant_type"]
        if source not in cases:
            raise ValueError(f"unknown hidden source: {source}")
        row = cases[source]
        if source in public_sources:
            raise ValueError(f"same parent appears in public development: {source}")
        if row["concept_family"] in public_families:
            raise ValueError(f"concept-family overlap: {row['concept_family']}")
        if row.get("generator_template") in public_templates:
            raise ValueError(f"generator-template overlap: {source}")
        if not row["hidden_variant_eligible"]:
            raise ValueError(f"source is not hidden-eligible: {source}")
        if (row.get("release_id"), row.get("generator_version")) != (
            policy["release_id"], policy["generator_version"]
        ):
            raise ValueError(f"stale release/generator for source: {source}")
        if kind not in row["variant_types"]:
            raise ValueError(f"variant type is not approved for source: {source}")
        key = (source, kind, item.get("instance_index", 0))
        if key in seen:
            raise ValueError(f"duplicate hidden source/type/index: {source}/{kind}/{key[2]}")
        seen.add(key)


def validate_policy(policy: dict[str, Any], *, family_map: Path = FAMILY_MAP,
                    public_plan: Path = PUBLIC_PLAN):
    _validate_schema(policy, POLICY_SCHEMA)
    if len(policy["seed"]) % 2:
        raise ValueError("private seed must have an even number of hexadecimal characters")
    mapping = validate_family_map(family_map)
    adapter = _adapter(policy["generator_version"], policy["release_id"])
    for item in policy["selections"]:
        if item["parent_case_id"] not in adapter.SUPPORTED or item["variant_type"] not in adapter.TYPES:
            raise ValueError("selection is unsupported by registered generator")
    check_disjoint(policy, family_map=mapping, public_plan=public_plan)
    return adapter


def _generated(adapter: Any, policy: dict[str, Any]) -> list[dict[str, Any]]:
    records = []
    for item in policy["selections"]:
        index = item.get("instance_index", 0)
        seed = (policy["seed"] if index == 0 else hashlib.sha256(
            f"hidden-instance-v1:{policy['seed']}:{item['parent_case_id']}:{item['variant_type']}:{index}".encode()
        ).hexdigest())
        record = adapter.generate_variant(item["parent_case_id"], seed,
                                          item["variant_type"], classification="private")
        if (record.get("parent_case_id") != item["parent_case_id"] or
                record.get("parent_release") != policy["release_id"] or
                record.get("generator_version") != policy["generator_version"] or
                record.get("seed_classification") != "private"):
            raise ValueError("generator returned stale or misclassified lineage")
        if "public_seed" in record or "gold" in record or "case" in record:
            raise ValueError("private variant record exposes seed or gold")
        records.append(record)
    if len({r["variant_id"] for r in records}) != len(records):
        raise ValueError("duplicate hidden instance ID")
    if len({r["instance_content_sha256"] for r in records}) != len(records):
        raise ValueError("duplicate hidden instance content")
    return records


def _task_signature(record: dict[str, Any]) -> str:
    """A conservative lexical structure screen, not semantic equivalence."""
    task = record["task"]
    text = task["statement"] + " " + " ".join(q["request"] for q in task["questions"])
    text = re.sub(r"(?<![a-z])[-+]?\d+(?:\.\d+)?(?:e[-+]?\d+)?", "#", text.lower())
    return " ".join(re.findall(r"[a-z]+|#", text))


def _parameter_signature(record: dict[str, Any]) -> tuple[tuple[str, str], ...]:
    from tools.physics_checks import to_si
    values = []
    for given in record["task"].get("givens", []):
        if "symbol" not in given:
            continue
        try:
            value = format(to_si(given), ".12g")
        except (KeyError, TypeError, ValueError):
            value = f"{given.get('value')!r}:{given.get('unit')!r}"
        values.append((given["symbol"], value))
    return tuple(sorted(values))


def _public_records(plan_path: Path) -> list[dict[str, Any]]:
    plan = _read(plan_path)
    adapter = _adapter(plan["generator_version"],
                       "0.1.0-rc1" if plan["generator_version"] == "0.1.0" else "0.2.0-rc1")
    return [adapter.generate_variant(item["parent_case_id"], item["seed"],
                                     item["variant_type"], classification="public_dev")
            for item in plan["variants"]]


def contamination_findings(hidden_records: list[dict[str, Any]],
                           public_plan: Path = PUBLIC_PLAN) -> list[str]:
    """Reject exact prompt structure, typed parameter tuple, or payload overlap.

    This is an accidental sibling/exact-instance screen, not a semantic
    contamination detector. Family/template exclusion is checked separately.
    """
    public = _public_records(public_plan)
    findings = []
    for hidden in hidden_records:
        for exposed in public:
            label = f"{hidden['variant_id']} vs {exposed['variant_id']}"
            if hidden["scientific_payload_sha256"] == exposed["scientific_payload_sha256"]:
                findings.append(f"exact scientific payload: {label}")
            if _task_signature(hidden) == _task_signature(exposed):
                findings.append(f"normalized task structure: {label}")
            if _parameter_signature(hidden) == _parameter_signature(exposed):
                findings.append(f"typed parameter tuple: {label}")
    return findings


def _commitment(policy: dict[str, Any], records: list[dict[str, Any]],
                *, created_utc: str) -> dict[str, Any]:
    # Hashes commit to canonical private contents; no seed, task, or parent list.
    entry_hashes = [_sha(record) for record in records]
    bundle_id = "HIDDEN-" + hashlib.sha256("".join(entry_hashes).encode()).hexdigest()[:16]
    return {"schema_version": COMMITMENT_VERSION, "bundle_id": bundle_id,
            "benchmark_release_id": policy["release_id"],
            "generator_version": policy["generator_version"],
            "hidden_policy_schema_version": POLICY_VERSION,
            "instance_count": len(records),
            "concept_family_count": policy["family_count"],
            "private_policy_sha256": _sha(policy),
            "hidden_seed_sha256": hashlib.sha256(bytes.fromhex(policy["seed"])).hexdigest(),
            "instance_commitments_sha256": entry_hashes,
            "created_utc": created_utc}


def generate_bundle(policy_path: Path, output_dir: Path, *, family_map: Path = FAMILY_MAP,
                    public_plan: Path = PUBLIC_PLAN) -> dict[str, Any]:
    source = _external(policy_path)
    destination = _external(output_dir)
    if destination.exists():
        raise FileExistsError("hidden bundle destination already exists")
    policy = _read(source)
    adapter = validate_policy(policy, family_map=family_map, public_plan=public_plan)
    mapping = validate_family_map(family_map)["cases"]
    count = len({mapping[x["parent_case_id"]]["concept_family"] for x in policy["selections"]})
    if count != policy["family_count"]:
        raise ValueError("private policy family_count does not match selections")
    records = _generated(adapter, policy)
    findings = contamination_findings(records, public_plan)
    if findings:
        raise ValueError("public-development contamination: " + "; ".join(findings))
    commitment = _commitment(policy, records, created_utc=datetime.now(timezone.utc).isoformat())
    _validate_schema(commitment, COMMITMENT_SCHEMA)
    destination.mkdir(parents=True)
    _write_new(destination / "private_policy.json", policy)
    for record in records:
        _write_new(destination / "instances" / f"{record['variant_id']}.json", record)
    _write_new(destination / "commitment.json", commitment)
    return commitment


def audit_bundle(bundle_dir: Path, *, family_map: Path = FAMILY_MAP,
                 public_plan: Path = PUBLIC_PLAN) -> dict[str, Any]:
    bundle = _external(bundle_dir)
    policy = _read(bundle / "private_policy.json")
    adapter = validate_policy(policy, family_map=family_map, public_plan=public_plan)
    commitment = _read(bundle / "commitment.json")
    _validate_schema(commitment, COMMITMENT_SCHEMA)
    expected = _generated(adapter, policy)
    findings = contamination_findings(expected, public_plan)
    if findings:
        raise ValueError("public-development contamination: " + "; ".join(findings))
    paths = sorted((bundle / "instances").glob("*.json"))
    if len(paths) != len(expected) or {p.name for p in paths} != {
        f"{record['variant_id']}.json" for record in expected
    }:
        raise ValueError("bundle instance set differs from seed reproduction")
    for record in expected:
        path = bundle / "instances" / f"{record['variant_id']}.json"
        if _read(path) != record:
            raise ValueError(f"instance differs from seed reproduction: {record['variant_id']}")
        loaded = adapter.load_variant(path)
        if loaded["instance_content_sha256"] != record["instance_content_sha256"]:
            raise ValueError("scorer compatibility or instance hash mismatch")
    map_rows = validate_family_map(family_map)["cases"]
    count = len({map_rows[x["parent_case_id"]]["concept_family"] for x in policy["selections"]})
    if count != policy["family_count"]:
        raise ValueError("family count differs from private selection")
    expected_commitment = _commitment(policy, expected, created_utc=commitment["created_utc"])
    if commitment != expected_commitment:
        raise ValueError("public commitment differs from private bundle")
    return commitment


def dry_run_bundle(bundle_dir: Path, *, family_map: Path = FAMILY_MAP,
                   public_plan: Path = PUBLIC_PLAN) -> dict[str, Any]:
    """Exercise the runner's mock adapter envelope and private scorer in memory."""
    commitment = audit_bundle(bundle_dir, family_map=family_map, public_plan=public_plan)
    policy = _read(Path(bundle_dir) / "private_policy.json")
    adapter_module = _adapter(policy["generator_version"], policy["release_id"])
    from tools.baseline.adapters import MockAdapter
    if policy["release_id"] == "0.2.0-rc1":
        from tools.vnext.scoring_runtime import evaluate_case
        from tools.vnext.protocols import public_payload, payload_sha256
    else:
        from tools.scoring_runtime import evaluate_case
        from tools.protocols import public_payload, payload_sha256
    counts = {"completed": 0, "failed": 0}
    for path in sorted((Path(bundle_dir) / "instances").glob("*.json")):
        loaded = adapter_module.load_variant(path)
        case = loaded["case"]
        answer = adapter_module._expected_answer(case)
        key = loaded["variant_id"]
        script = {key + "|closed_book": [{"type": "final", "raw_response": json.dumps(answer)}]}
        request = {"selection_key": key, "protocol_id": "closed_book",
                   "scientific_payload": public_payload(case),
                   "scientific_payload_sha256": payload_sha256(case),
                   "allowed_tools": [], "retrieved_items": [], "tool_exchanges": []}
        if "gold" in request["scientific_payload"] or "reference" in request["scientific_payload"]:
            raise ValueError("public adapter payload leaks gold")
        turn = MockAdapter(script).invoke(request, 30)
        result = evaluate_case(case, json.loads(turn.raw_response or "{}"))
        counts["completed" if result["scores"]["capped_total"] == 1.0 and
               result["failure_mode"] == "none" else "failed"] += 1
    return {"bundle_id": commitment["bundle_id"], "execution_class": "dry_run",
            "adapter_type": "mock", "counts": counts}


def audit_result_linkage(bundle_dir: Path, run_dir: Path, *, family_map: Path = FAMILY_MAP,
                         public_plan: Path = PUBLIC_PLAN) -> dict[str, Any]:
    """Check private runner evidence against the committed bundle lineage."""
    commitment = audit_bundle(bundle_dir, family_map=family_map, public_plan=public_plan)
    bundle = _external(bundle_dir)
    run = _external(run_dir)
    manifest = _read(run / "manifest.json")
    if manifest.get("release_id") != commitment["benchmark_release_id"]:
        raise ValueError("run release differs from hidden bundle")
    records = {_read(path)["variant_id"]: _read(path)
               for path in (bundle / "instances").glob("*.json")}
    selected: set[str] = set()
    for selection in manifest.get("selections", []):
        if selection.get("track") != "private_variant":
            raise ValueError("hidden run contains a nonprivate selection")
        path = Path(selection["variant_path"]).resolve()
        if path.parent != (bundle / "instances").resolve() or not path.is_file():
            raise ValueError("run selection is outside the committed hidden bundle")
        variant_id = path.stem
        if variant_id not in records or variant_id in selected:
            raise ValueError("run selection has unknown or duplicate hidden instance")
        selected.add(variant_id)
    if not selected:
        raise ValueError("hidden run selects no committed instance")
    result_paths = list((run / "results").glob("*.json"))
    if not result_paths:
        raise ValueError("hidden run has no result records")
    linked = 0
    for result_path in result_paths:
        result = _read(result_path)
        selection = result.get("selection") or {}
        instance_id = selection.get("variant_id")
        if instance_id not in selected:
            raise ValueError("result references unselected hidden instance")
        instance = records[instance_id]
        if selection.get("track") != "private_variant" or selection.get("case_id") != instance["parent_case_id"]:
            raise ValueError("result selection lineage differs from hidden instance")
        if (selection.get("case_content_sha256") != instance["instance_content_sha256"] or
                (selection.get("variant_lineage") or {}).get("generator_version") != instance["generator_version"] or
                (selection.get("variant_lineage") or {}).get("instance_content_sha256") != instance["instance_content_sha256"]):
            raise ValueError("result instance hash or generator lineage differs")
        if (result.get("protocol") or {}).get("scientific_payload_sha256") != instance["scientific_payload_sha256"]:
            raise ValueError("result scientific payload differs from hidden instance")
        score = result.get("score_result")
        if score is not None and score.get("evaluator_fingerprint") != instance["scorer"]["evaluator_fingerprint"]:
            raise ValueError("result scorer fingerprint differs from hidden instance")
        linked += 1
    return {"bundle_id": commitment["bundle_id"], "run_id": manifest.get("run_id"),
            "selected_instances": len(selected), "linked_result_records": linked}


def prepare_run_manifest(bundle_dir: Path, output_root: Path, run_id: str,
                         agent_path: Path) -> Path:
    """Write a private, resumable runner input without publishing bundle data."""
    from tools.baseline import RUNNER_VERSION, SYSTEM_PROMPT_VERSION
    from tools.baseline.tools import PROFILE_ID
    from tools.baseline.runner import validate_manifest
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{2,127}", run_id):
        raise ValueError("run_id must be a 3-128 character safe slug")
    commitment = audit_bundle(bundle_dir)
    bundle = _external(bundle_dir)
    root = _external(output_root)
    agent = _read(_external(agent_path))
    execution_class = "dry_run" if agent.get("adapter_type") == "mock" else "real"
    selections = [{"case_id": item["parent_case_id"], "track": "private_variant",
                   "variant_path": str(path.resolve())}
                  for path in sorted((bundle / "instances").glob("*.json"))
                  for item in [_read(path)]]
    manifest = {"schema_version": "0.1.0", "run_id": run_id,
                "created_utc": datetime.now(timezone.utc).isoformat(),
                "execution_class": execution_class,
                "release_id": commitment["benchmark_release_id"],
                "selections": selections, "protocol_ids": ["closed_book"],
                "agent": agent, "runner_version": RUNNER_VERSION,
                "system_prompt_version": SYSTEM_PROMPT_VERSION,
                "retrieval_config": {"max_items": 0},
                "tool_config": {"profile_id": PROFILE_ID, "max_calls": 0},
                "retry_policy": {"transport_max_retries": 0,
                                 "malformed_answer_max_retries": 0,
                                 "self_correction_max_retries": 0},
                "timeout_seconds": 120, "concurrency": 1, "seed": None,
                "output_directory": run_id, "pricing_snapshot": None}
    validate_manifest(manifest)
    destination = root / "input_manifests" / f"{run_id}.json"
    _write_new(destination, manifest)
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("check-map")
    generate = sub.add_parser("generate")
    generate.add_argument("--policy", type=Path, required=True)
    generate.add_argument("--output-dir", type=Path, required=True)
    for name in ("audit", "dry-run"):
        command = sub.add_parser(name)
        command.add_argument("--bundle-dir", type=Path, required=True)
    results = sub.add_parser("audit-results")
    results.add_argument("--bundle-dir", type=Path, required=True)
    results.add_argument("--run-dir", type=Path, required=True)
    prepare = sub.add_parser("prepare-run")
    prepare.add_argument("--bundle-dir", type=Path, required=True)
    prepare.add_argument("--output-root", type=Path, required=True)
    prepare.add_argument("--run-id", required=True)
    prepare.add_argument("--agent-json", type=Path, required=True)
    args = parser.parse_args()
    if args.action == "check-map":
        print(f"family map valid: {len(validate_family_map()['cases'])} canonical cases")
    elif args.action == "generate":
        print(json.dumps(generate_bundle(args.policy, args.output_dir), indent=2))
    elif args.action == "audit":
        print(json.dumps(audit_bundle(args.bundle_dir), indent=2))
    elif args.action == "audit-results":
        print(json.dumps(audit_result_linkage(args.bundle_dir, args.run_dir), indent=2))
    elif args.action == "prepare-run":
        print(prepare_run_manifest(args.bundle_dir, args.output_root, args.run_id, args.agent_json))
    else:
        print(json.dumps(dry_run_bundle(args.bundle_dir), indent=2))


if __name__ == "__main__":
    main()
