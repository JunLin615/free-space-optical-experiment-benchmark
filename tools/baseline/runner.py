"""Resumable baseline execution with immutable per-attempt evidence records."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from tools.baseline import RUNNER_VERSION, SYSTEM_PROMPT_VERSION
from tools.baseline.adapters import (AdapterFailure, CommandAdapter, CodexCliAdapter,
                                     MockAdapter)
from tools.baseline.tools import ALLOWED_TOOLS, PROFILE_ID, observed_call
from tools.validate_cases import ROOT


MANIFEST_SCHEMA = ROOT / "benchmark" / "run_schema" / "run_manifest_v0.1.schema.json"
RECORD_SCHEMA = ROOT / "benchmark" / "run_schema" / "run_record_v0.1.schema.json"
RESULT_SCHEMA = ROOT / "benchmark" / "schema" / "result.schema.json"
PROMPT_FILE = ROOT / "benchmark" / "system_prompts" / "neutral_optics_v1.txt"


def _runtime(release_id: str):
    """Select a pinned evaluator lineage without changing rc1 interpretation."""
    if release_id == "0.1.0-rc1":
        from tools import scoring_runtime
        return scoring_runtime
    if release_id == "0.2.0-rc1":
        from tools.vnext import scoring_runtime
        return scoring_runtime
    raise ValueError(f"unsupported evaluator release: {release_id}")


def _validator(path: Path) -> Draft202012Validator:
    schema = json.loads(path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def _validate(value: dict[str, Any], path: Path) -> None:
    errors = list(_validator(path).iter_errors(value))
    if errors:
        raise ValueError(f"{path.name}: {errors[0].message}")


def _hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


def _source_revision(release_id: str = "0.1.0-rc1") -> str | None:
    digest = hashlib.sha256()
    paths = sorted((ROOT / "tools" / "baseline").glob("*.py"))
    paths += [ROOT / "tools" / name for name in
              ("protocols.py", "retrieval.py", "case_library.py", "variants.py", "scoring_runtime.py")]
    paths.append(PROMPT_FILE)
    if release_id == "0.2.0-rc1":
        paths += [ROOT / relative for relative in (
            "tools/vnext/scoring_runtime.py", "tools/vnext/units.py",
            "tools/vnext/protocols.py",
            "tools/scorers/closed_vnext.py", "tools/variants_vnext.py",
            "benchmark/releases/0.2.0-rc1.json")]
    for path in paths:
        if path.exists():
            digest.update(str(path.relative_to(ROOT)).replace("\\", "/").encode("utf-8") + b"\0")
            digest.update(path.read_bytes())
    try:
        result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                text=True, capture_output=True, timeout=5, check=True)
        return (result.stdout.strip() or "unknown") + "+source-sha256:" + digest.hexdigest()
    except (OSError, subprocess.SubprocessError):
        return "source-sha256:" + digest.hexdigest()


def validate_manifest(manifest: dict[str, Any]) -> None:
    _validate(manifest, MANIFEST_SCHEMA)
    if manifest["agent"]["adapter_type"] == "mock" and manifest["execution_class"] != "dry_run":
        raise ValueError("mock adapter cannot be labeled a real baseline")
    if manifest["agent"]["adapter_type"] == "mock" and not isinstance(manifest["agent"]["mock_script"], dict):
        raise ValueError("mock adapter needs mock_script")
    if manifest["agent"]["adapter_type"] == "command" and not manifest["agent"]["command"]:
        raise ValueError("command adapter needs command argument vector")
    if manifest["agent"]["adapter_type"] == "codex_cli" and manifest["agent"]["provider"] != "openai":
        raise ValueError("Codex CLI provider identity must be openai")
    output = Path(manifest["output_directory"])
    if manifest["output_directory"] != manifest["run_id"] and not (
        output.is_absolute() and output.name == manifest["run_id"]
    ):
        raise ValueError("output_directory must be a host-absolute path ending in run_id or the logical run_id; use --output-root and --replay-suffix for a foreign-host historical manifest")
    if "replay_of" in manifest and manifest["replay_of"]["run_id"] == manifest["run_id"]:
        raise ValueError("replay must use a new run_id")
    if manifest["system_prompt_version"] != SYSTEM_PROMPT_VERSION:
        raise ValueError("unknown system prompt version")
    if manifest["tool_config"]["profile_id"] != PROFILE_ID:
        raise ValueError("unsupported tool profile")
    if manifest["pricing_snapshot"] is not None:
        pricing = manifest["pricing_snapshot"]
        required = {"currency", "provider", "model_id", "pricing_reference",
                    "pricing_snapshot_utc", "rates_per_million"}
        if not isinstance(pricing, dict) or not required <= set(pricing):
            raise ValueError("pricing snapshot lacks required provenance/rates")
        if pricing["provider"] != manifest["agent"]["provider"] or pricing["model_id"] != manifest["agent"]["model_id"]:
            raise ValueError("pricing snapshot identity differs from agent")
        rates = pricing["rates_per_million"]
        if not isinstance(rates, dict) or not {"input", "output"} <= set(rates) or any(
            isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0
            for value in rates.values()
        ):
            raise ValueError("pricing rates must be nonnegative numbers with input/output")
    from tools.protocols import load_protocol
    for protocol_id in manifest["protocol_ids"]:
        protocol = load_protocol(protocol_id)
        if manifest["timeout_seconds"] > protocol["timeout_policy"]["agent_seconds"]:
            raise ValueError(f"timeout exceeds {protocol_id} cap")
        policy = manifest["retry_policy"]
        caps = protocol["retry_policy"]
        if (policy["transport_max_retries"] > caps["transport_retries"] or
            policy["malformed_answer_max_retries"] > caps["malformed_answer_retries"] or
            policy["self_correction_max_retries"] > caps["self_correction_retries"]):
            raise ValueError(f"retry policy exceeds {protocol_id} cap")
        if manifest["retrieval_config"]["max_items"] > 0 and protocol["case_library_access"]["enabled"]:
            if manifest["retrieval_config"]["max_items"] > protocol["retrieval_policy"]["max_items"]:
                raise ValueError("retrieval max_items exceeds protocol cap")
        if protocol["tool_policy"]["allowed_tools"] and set(protocol["tool_policy"]["allowed_tools"]) != set(ALLOWED_TOOLS):
            raise ValueError("tool profile and protocol permissions differ")


def _adapter(manifest: dict[str, Any]):
    agent = manifest["agent"]
    if agent["adapter_type"] == "mock":
        return MockAdapter(agent["mock_script"])
    if agent["adapter_type"] == "command":
        return CommandAdapter(agent["command"])
    return CodexCliAdapter(agent["model_id"], agent["command_prefix"])


def _selection_key(selection: dict[str, Any], variant_id: str | None = None) -> str:
    label = selection["case_id"] + ("--" + variant_id if variant_id else "")
    return "".join(character if character.isalnum() or character in "-_" else "_" for character in label)


def _variant_source_path(raw_path: str) -> Path:
    """Interpret repository-relative variant paths from either host flavor."""
    path = Path(raw_path)
    if path.is_absolute():
        return path.resolve()
    return (ROOT / raw_path.replace("\\", "/")).resolve()


def _load_selection(selection: dict[str, Any], release_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    runtime = _runtime(release_id)
    variant_id = None
    variant_record = None
    if selection["variant_path"] is not None:
        if release_id == "0.2.0-rc1":
            from tools.variants_vnext import load_variant
        else:
            from tools.variants import load_variant
        variant_path = _variant_source_path(selection["variant_path"])
        variant_record = load_variant(variant_path)
        if variant_record["parent_case_id"] != selection["case_id"]:
            raise ValueError("variant parent ID differs from selection")
        if variant_record["parent_release"] != release_id:
            raise ValueError("variant belongs to another release")
        variant_id = variant_record["variant_id"]
        case = variant_record["case"]
    else:
        case = runtime.load_scored_case(selection["case_id"])
    if case["case_id"] not in runtime.SCORERS:
        raise ValueError("selected case has no autonomous scorer")
    if selection["track"] == "verified":
        if variant_id is not None:
            raise ValueError("a variant cannot be labeled verified canonical")
        release = json.loads((ROOT / "benchmark" / "releases" / f"{release_id}.json").read_text(encoding="utf-8"))
        pinned = release["cases"].get(case["case_id"])
        if pinned is None or pinned["case_revision"] != str(case["case_revision"]):
            raise ValueError("case is not pinned in requested release")
        if pinned["case_content_sha256"] != _hash(case):
            raise ValueError("release case content hash mismatch")
        if pinned["evaluator_fingerprint"] != runtime._evaluator_fingerprint(case):
            raise ValueError("release scorer fingerprint mismatch")
    elif selection["track"] in {"public_variant", "private_variant"}:
        if variant_record is None:
            raise ValueError("variant track requires variant_path")
        expected_class = "public_dev" if selection["track"] == "public_variant" else "private"
        if variant_record["seed_classification"] != expected_class:
            raise ValueError("variant seed classification conflicts with track")
    elif variant_record is not None:
        raise ValueError("variant_path requires variant track")
    metadata = {"case_id": case["case_id"], "case_revision": str(case["case_revision"]),
                "variant_id": variant_id, "variant_type": variant_record.get("variant_type") if variant_record else None,
                "track": selection["track"], "case_content_sha256": _hash(case)}
    if variant_record:
        metadata["variant_lineage"] = {key: variant_record.get(key) for key in
                                       ("parent_case_id", "parent_case_revision", "generator_version",
                                        "seed_classification", "instance_content_sha256")}
    return case, metadata


def _identity(manifest: dict[str, Any]) -> dict[str, Any]:
    agent = manifest["agent"]
    return {"provider": agent["provider"], "model_id": agent["model_id"],
            "model_version": agent["model_version"], "framework": agent["framework"],
            "scaffold_id": agent["scaffold_id"],
            "system_prompt_version": manifest["system_prompt_version"],
            "adapter_type": agent["adapter_type"]}


def _sum_usage(turn_usages: list[dict[str, Any]]) -> dict[str, int | None]:
    result = {}
    for field in ("input", "output", "cached_input", "reasoning"):
        values = [usage.get(field) for usage in turn_usages]
        result[field] = sum(values) if values and all(isinstance(v, int) and v >= 0 for v in values) else None
    result["total"] = (result["input"] + result["output"] if
                       result["input"] is not None and result["output"] is not None else None)
    return result


def _cost(pricing: dict[str, Any] | None, usage: dict[str, int | None]) -> dict[str, Any] | None:
    if pricing is None or usage["input"] is None or usage["output"] is None:
        return None
    rates = pricing["rates_per_million"]
    if not isinstance(rates, dict) or not {"input", "output"} <= set(rates):
        return None
    cached = usage["cached_input"]
    if cached is None:
        if "cached_input" in rates:
            return None
        cached = 0
    if cached > usage["input"]:
        return None
    amount = ((usage["input"] - cached) * rates["input"] + usage["output"] * rates["output"] +
              cached * rates.get("cached_input", rates["input"])) / 1_000_000
    return {"amount": amount, "currency": pricing["currency"],
            "pricing_reference": pricing["pricing_reference"],
            "pricing_snapshot_utc": pricing["pricing_snapshot_utc"]}


def _record_path(run_dir: Path, key: str) -> Path:
    return run_dir / "results" / (key + ".json")


def _log_path(run_dir: Path, key: str) -> Path:
    return run_dir / "logs" / (key + ".jsonl")


def _append_event(path: Path, event: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")


def _write_record(path: Path, record: dict[str, Any]) -> None:
    _validate(record, RECORD_SCHEMA)
    if record["score_result"] is not None:
        _validate(record["score_result"], RESULT_SCHEMA)
    if path.exists():
        raise FileExistsError(f"immutable result record already exists: {path}")
    pending = path.with_name(path.name + ".partial")
    pending.write_text(json.dumps(record, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    os.replace(pending, path)


def _run_one(manifest: dict[str, Any], case: dict[str, Any], selection: dict[str, Any],
             protocol: dict[str, Any], adapter: Any, key: str, run_dir: Path) -> dict[str, Any]:
    if manifest["release_id"] == "0.2.0-rc1":
        from tools.vnext.protocols import public_payload, payload_sha256
    else:
        from tools.protocols import public_payload, payload_sha256
    from tools.retrieval import retrieve
    protocol_id = protocol["protocol_id"]
    public = public_payload(case)
    science_hash = payload_sha256(case)
    log_path = _log_path(run_dir, key)
    start = time.monotonic()
    retrieval = None
    if protocol["case_library_access"]["enabled"]:
        query = public["task"]["statement"] + " " + " ".join(q["request"] for q in public["task"]["questions"])
        retrieval = retrieve(query, max_items=manifest["retrieval_config"]["max_items"], protocol_id=protocol_id)
        if retrieval["total_retrieved_tokens"] > protocol["retrieval_policy"]["max_context_tokens"]:
            raise ValueError("retrieval exceeded context cap")
        _append_event(log_path, {"kind": "retrieval", "record": retrieval})
    allowed_tools = protocol["tool_policy"]["allowed_tools"]
    tool_exchanges: list[dict[str, Any]] = []
    tool_calls: list[dict[str, Any]] = []
    turn_usages: list[dict[str, Any]] = []
    provider_usages: list[dict[str, Any]] = []
    attempts = 0
    model_turns = 0
    retries = 0
    transport_retries = 0
    malformed_retries = 0
    raw_response: str | None = None
    parsed_answer: dict[str, Any] | None = None
    score_result: dict[str, Any] | None = None
    failure_class: str | None = None
    correction: str | None = None
    request = {"system_prompt": PROMPT_FILE.read_text(encoding="utf-8").strip(),
               "scientific_payload": public, "scientific_payload_sha256": science_hash,
               "protocol_id": protocol_id, "protocol_version": protocol["version"],
               "selection_key": _selection_key(selection, selection.get("variant_id")),
               "retrieved_items": retrieval["items"] if retrieval else [],
               "allowed_tools": allowed_tools, "tool_exchanges": tool_exchanges,
               "correction": None}
    while True:
        request["correction"] = correction
        try:
            turn = adapter.invoke(request, manifest["timeout_seconds"])
        except AdapterFailure as exc:
            for event in exc.events:
                _append_event(log_path, {"kind": "adapter_event", "event": event})
            _append_event(log_path, {"kind": "adapter_failure", "failure_class": exc.failure_class,
                                     "message": str(exc)})
            if (exc.failure_class == "model_api_failure" and
                transport_retries < manifest["retry_policy"]["transport_max_retries"]):
                transport_retries += 1
                retries += 1
                continue
            failure_class = exc.failure_class
            break
        model_turns += 1
        turn_usages.append(turn.usage)
        if turn.provider_usage is not None:
            provider_usages.append(turn.provider_usage)
        for event in turn.events:
            _append_event(log_path, {"kind": "adapter_event", "event": event})
        _append_event(log_path, {"kind": "adapter_turn", "turn": model_turns,
                                 "response_type": turn.kind, "wall_time_seconds": turn.wall_time_seconds,
                                 "usage": turn.usage})
        if turn.kind == "tool_call":
            if turn.tool_name not in allowed_tools:
                failure_class = "tool_policy_violation"
                break
            if len(tool_calls) >= manifest["tool_config"]["max_calls"]:
                failure_class = "tool_limit_exceeded"
                break
            tool_result, call_log = observed_call(len(tool_calls) + 1, turn.tool_name, turn.arguments)
            tool_calls.append(call_log)
            _append_event(log_path, {"kind": "tool_call", "record": call_log, "result": tool_result})
            if call_log["status"] != "ok":
                failure_class = ("malformed_tool_call" if call_log["status"] == "malformed_call"
                                 else "tool_runtime_failure")
                break
            tool_exchanges.append({"tool_name": turn.tool_name, "arguments": call_log["arguments_summary"],
                                   "result": tool_result})
            continue
        attempts += 1
        raw_response = turn.raw_response
        try:
            parsed = json.loads(raw_response or "")
        except json.JSONDecodeError:
            parsed = None
        if not isinstance(parsed, dict):
            if malformed_retries < manifest["retry_policy"]["malformed_answer_max_retries"]:
                malformed_retries += 1
                retries += 1
                correction = "The previous final response was not one JSON object. Return the same answer as valid JSON."
                continue
            # Preserve raw bytes and let the existing runtime record an invalid contract.
            parsed_answer = None
            candidate: Any = raw_response
        else:
            parsed_answer = parsed
            candidate = parsed
        context = {"run_id": manifest["run_id"], "benchmark_version": manifest["release_id"],
                   "system": {"name": manifest["agent"]["framework"],
                              "provider": manifest["agent"]["provider"],
                              "model_id": manifest["agent"]["model_id"],
                              "model_version": manifest["agent"]["model_version"],
                              "scaffold_id": manifest["agent"]["scaffold_id"]},
                   "protocol": protocol_id,
                   "case_library_access": {"available": bool(retrieval),
                                           "snapshot_id": retrieval["library_snapshot_id"] if retrieval else None,
                                           "retrieved_document_ids": retrieval["retrieved_ids"] if retrieval else []},
                   "tools_available": allowed_tools,
                   "tools_used": sorted({call["tool_name"] for call in tool_calls}),
                   "tool_call_count": (None if manifest["agent"]["adapter_type"] == "command"
                                       else len(tool_calls)),
                   "tokens": {key: value for key, value in _sum_usage(turn_usages).items()
                              if key in {"input", "output", "total", "cached_input"}},
                   "provider_usage": {"turns": provider_usages} if provider_usages else None,
                   "cost": _cost(manifest["pricing_snapshot"], _sum_usage(turn_usages)),
                   "wall_time_seconds": time.monotonic() - start,
                   "retry_count": retries}
        try:
            score_result = _runtime(manifest["release_id"]).evaluate_case(
                case, candidate, raw_answer=raw_response, context=context)
        except Exception as exc:
            _append_event(log_path, {"kind": "scorer_exception", "error_type": type(exc).__name__})
            failure_class = "scorer_failure"
        else:
            if score_result["failure_mode"] in {"validator_error", "invalid_instance"}:
                failure_class = "scorer_failure" if score_result["failure_mode"] == "validator_error" else "invalid_benchmark_instance"
            elif score_result["failure_mode"] != "none":
                failure_class = score_result["failure_mode"]
        break
    usage = _sum_usage(turn_usages)
    record = {"run_record_version": "0.1.0", "run_id": manifest["run_id"],
              "execution_class": manifest["execution_class"], "selection": selection,
              "protocol": {"id": protocol_id, "version": protocol["version"],
                           "scientific_payload_sha256": science_hash},
              "agent_identity": _identity(manifest),
              "status": ("completed" if score_result is not None and failure_class not in
                         {"scorer_failure", "invalid_benchmark_instance"} else "failed"),
              "failure_class": failure_class, "attempt_count": attempts,
              "first_attempt_success": attempts == 1 and score_result is not None and
                                       score_result["scores"]["capped_total"] == 1 and
                                       score_result["failure_mode"] == "none",
              "retrieval": retrieval, "tool_calls": tool_calls, "usage": usage,
              "cost": _cost(manifest["pricing_snapshot"], usage),
              "wall_time_seconds": time.monotonic() - start,
              "raw_response": raw_response, "parsed_answer": parsed_answer,
              "score_result": score_result, "runner_source_revision": _source_revision(),
              "retry_count": retries, "model_turn_count": model_turns,
              "protocol_compliance_verified": manifest["agent"]["adapter_type"] != "command",
              "tool_observation_scope": ("runner_mediated_only" if manifest["agent"]["adapter_type"] == "command"
                                         else "complete_with_builtin_tools_disabled")}
    return record


def output_path(manifest: dict[str, Any], output_root: Path | None = None) -> Path:
    """Resolve an operational destination without changing frozen run configuration."""
    output = Path(manifest["output_directory"])
    if output.is_absolute():
        if output_root is not None:
            raise ValueError("absolute historical output requires --replay-suffix with --output-root")
        return output
    root = Path(output_root) if output_root is not None else ROOT / "runs"
    if not root.is_absolute():
        raise ValueError("output_root must be absolute on the current host")
    return root / manifest["run_id"]


def run_manifest(manifest_path: Path, *, retry_failed: bool = False,
                 output_root: Path | None = None) -> dict[str, int]:
    """Execute/resume one frozen manifest. Prior attempts are never overwritten."""
    raw_manifest = manifest_path.read_bytes()
    manifest = json.loads(raw_manifest)
    validate_manifest(manifest)
    run_dir = output_path(manifest, output_root)
    run_dir.mkdir(parents=True, exist_ok=True)
    for child in ("results", "logs"):
        (run_dir / child).mkdir(exist_ok=True)
    frozen = run_dir / "manifest.json"
    if frozen.exists():
        if frozen.read_bytes() != raw_manifest:
            raise ValueError("existing run manifest differs byte-for-byte")
    else:
        with frozen.open("xb") as stream:
            stream.write(raw_manifest)
    prompt_snapshot = run_dir / "system_prompt.txt"
    prompt_bytes = PROMPT_FILE.read_bytes()
    if prompt_snapshot.exists():
        if prompt_snapshot.read_bytes() != prompt_bytes:
            raise ValueError("frozen system prompt differs from current prompt version")
    else:
        with prompt_snapshot.open("xb") as stream:
            stream.write(prompt_bytes)
    protocol_snapshots = run_dir / "protocols"
    protocol_snapshots.mkdir(exist_ok=True)
    for protocol_id in manifest["protocol_ids"]:
        source = ROOT / "benchmark" / "protocols" / f"{protocol_id}.v1.json"
        frozen_protocol = protocol_snapshots / source.name
        content = source.read_bytes()
        if frozen_protocol.exists():
            if frozen_protocol.read_bytes() != content:
                raise ValueError(f"frozen protocol differs from current manifest: {protocol_id}")
        else:
            with frozen_protocol.open("xb") as stream:
                stream.write(content)
    environment_path = run_dir / "environment.json"
    frozen_source_revision = _source_revision(manifest["release_id"])
    if not environment_path.exists():
        with environment_path.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps({
                "python": platform.python_version(), "platform": platform.platform(),
                "runner_source_revision": frozen_source_revision, "captured_utc": datetime.now(timezone.utc).isoformat(),
            }, indent=2) + "\n")
    elif json.loads(environment_path.read_text(encoding="utf-8"))["runner_source_revision"] != frozen_source_revision:
        raise ValueError("runner source differs from frozen run environment; start a new run ID")
    from tools.protocols import check_matched_runs, load_protocol
    if manifest["release_id"] == "0.2.0-rc1":
        from tools.vnext.protocols import payload_sha256
    else:
        from tools.protocols import payload_sha256
    adapter = _adapter(manifest)
    counts = {"total": len(manifest["selections"]) * len(manifest["protocol_ids"]),
              "completed": 0, "failed": 0, "skipped": 0, "unresolved": 0}
    started = time.monotonic()
    observed_tokens = 0
    observed_cost = 0.0
    token_records = 0
    cost_records = 0

    def progress(case_id: str, protocol_id: str) -> None:
        processed = counts["completed"] + counts["failed"] + counts["skipped"]
        print(f"{processed}/{counts['total']} completed={counts['completed']} "
              f"failed={counts['failed']} skipped={counts['skipped']} "
              f"unresolved={counts['unresolved']} elapsed={time.monotonic() - started:.1f}s "
              f"known_tokens={observed_tokens if token_records else 'null'} "
              f"known_cost={format(observed_cost, '.6g') if cost_records else 'null'} "
              f"case={case_id} protocol={protocol_id}", flush=True)
    for selection_spec in manifest["selections"]:
        case, selection = _load_selection(selection_spec, manifest["release_id"])
        descriptors = [{"case_id": case["case_id"], "case_revision": str(case["case_revision"]),
                        "variant_id": selection["variant_id"],
                        "scientific_payload_sha256": payload_sha256(case),
                        "scorer_id": _runtime(manifest["release_id"]).SCORERS[case["case_id"]],
                        "scorer_fingerprint": _runtime(manifest["release_id"])._evaluator_fingerprint(case),
                        "result_schema_version": "0.1.0", "agent_identity": _identity(manifest),
                        "protocol_id": protocol_id, "protocol_version": load_protocol(protocol_id)["version"]}
                       for protocol_id in manifest["protocol_ids"]]
        if len(descriptors) > 1:
            issues = check_matched_runs(descriptors)
            if issues:
                raise ValueError("matched-run invariants: " + "; ".join(issues))
        for protocol_id in manifest["protocol_ids"]:
            key = _selection_key(selection, selection["variant_id"]) + "__" + protocol_id
            path = _record_path(run_dir, key)
            if path.exists():
                previous = json.loads(path.read_text(encoding="utf-8"))
                _validate(previous, RECORD_SCHEMA)
                if previous["status"] == "completed" or not retry_failed:
                    counts["skipped"] += 1
                    progress(selection["case_id"], protocol_id)
                    continue
                # Failed attempts remain immutable evidence; numbered retry
                # records are written without removing the prior failure.
                suffix = 2
                while _record_path(run_dir, key + f".attempt{suffix}").exists():
                    previous_attempt = json.loads(_record_path(run_dir, key + f".attempt{suffix}").read_text(encoding="utf-8"))
                    if previous_attempt["status"] == "completed":
                        break
                    suffix += 1
                if _record_path(run_dir, key + f".attempt{suffix}").exists():
                    counts["skipped"] += 1
                    progress(selection["case_id"], protocol_id)
                    continue
                key += f".attempt{suffix}"
                path = _record_path(run_dir, key)
            protocol = load_protocol(protocol_id)
            if _source_revision(manifest["release_id"]) != frozen_source_revision:
                raise ValueError("runner source changed during run; start a new run ID")
            record = _run_one(manifest, case, selection, protocol, adapter, key, run_dir)
            if _source_revision(manifest["release_id"]) != frozen_source_revision:
                raise ValueError("runner source changed during model execution; discard this partial attempt")
            _write_record(path, record)
            counts[record["status"]] += 1
            counts["unresolved"] += int(record["score_result"] is not None and
                                        record["score_result"]["scores"]["capped_total"] is None)
            if isinstance(record["usage"]["total"], int):
                observed_tokens += record["usage"]["total"]
                token_records += 1
            if record["cost"] is not None:
                observed_cost += record["cost"]["amount"]
                cost_records += 1
            progress(selection["case_id"], protocol_id)
    return counts
