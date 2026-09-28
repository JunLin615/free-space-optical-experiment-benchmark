"""Offline end-to-end checks for frozen baseline execution and honest records."""

from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from tools.baseline.adapters import _codex_prompt, _safe_codex_event
from tools.baseline.runner import _cost, run_manifest, validate_manifest
from tools.baseline.tools import ToolCallError, execute_tool, observed_call
from tools.protocols import public_payload
from tools.scoring_runtime import load_scored_case


ROOT = Path(__file__).resolve().parents[1]
PROTOCOLS = ("closed_book", "case_assisted", "tool_assisted", "case_and_tool_assisted")


def reference_answer() -> dict:
    fixture = json.loads((ROOT / "benchmark/fixtures/SEED-1-1/reference.json").read_text(encoding="utf-8"))
    return fixture["answer"]


def manifest(directory: Path, *, protocols: tuple[str, ...] = ("closed_book",),
             script: dict | None = None) -> dict:
    response = {"type": "final", "raw_response": json.dumps(reference_answer())}
    if script is None:
        script = {f"SEED-1-1|{protocol}": [copy.deepcopy(response)] for protocol in protocols}
    return {
        "schema_version": "0.1.0", "run_id": "offline-test-001",
        "created_utc": "2026-09-28T00:00:00Z", "execution_class": "dry_run",
        "release_id": "0.1.0-rc1",
        "selections": [{"case_id": "SEED-1-1", "track": "verified", "variant_path": None}],
        "protocol_ids": list(protocols),
        "agent": {"adapter_type": "mock", "provider": "mock", "model_id": "scripted",
                  "model_version": "1", "framework": "local_mock", "scaffold_id": None,
                  "command": None, "command_prefix": None, "mock_script": script},
        "runner_version": "0.1.0", "system_prompt_version": "neutral_optics_v1",
        "retrieval_config": {"max_items": 3},
        "tool_config": {"profile_id": "generic_computation_v0.1", "max_calls": 3},
        "retry_policy": {"transport_max_retries": 0, "malformed_answer_max_retries": 0,
                         "self_correction_max_retries": 0},
        "timeout_seconds": 120, "concurrency": 1, "seed": None,
        "output_directory": str(directory / "offline-test-001"), "pricing_snapshot": None,
    }


def execute_temp(config: dict, directory: Path) -> tuple[dict, Path]:
    path = directory / "input.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    return run_manifest(path), path


def record(directory: Path, protocol: str = "closed_book") -> dict:
    path = directory / "offline-test-001" / "results" / f"SEED-1-1__{protocol}.json"
    return json.loads(path.read_text(encoding="utf-8"))


class BaselineRunnerTests(unittest.TestCase):
    def test_mock_cannot_masquerade_as_real_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            config = manifest(Path(temp))
            config["execution_class"] = "real"
            with self.assertRaisesRegex(ValueError, "mock adapter cannot"):
                validate_manifest(config)

    def test_four_protocols_preserve_scientific_payload_and_retrieval_scope(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            counts, path = execute_temp(manifest(directory, protocols=PROTOCOLS), directory)
            self.assertEqual(counts["completed"], 4)
            records = [record(directory, protocol) for protocol in PROTOCOLS]
            self.assertEqual(len({item["protocol"]["scientific_payload_sha256"] for item in records}), 1)
            self.assertTrue(all(item["score_result"]["scores"]["capped_total"] == 1 for item in records))
            for item in records:
                has_library = item["protocol"]["id"] in {"case_assisted", "case_and_tool_assisted"}
                has_tools = item["protocol"]["id"] in {"tool_assisted", "case_and_tool_assisted"}
                self.assertEqual(item["retrieval"] is not None, has_library)
                self.assertEqual(bool(item["score_result"]["tools_available"]), has_tools)
                self.assertEqual(item["score_result"]["case_library_access"]["available"], has_library)
                self.assertEqual(item["execution_class"], "dry_run")
            frozen = directory / "offline-test-001" / "manifest.json"
            before = frozen.read_bytes()
            self.assertEqual(before, path.read_bytes())
            self.assertEqual(run_manifest(path)["skipped"], 4)
            self.assertEqual(frozen.read_bytes(), before)

    def test_tool_call_is_runner_observed_and_out_of_profile_call_fails(self) -> None:
        answer = json.dumps(reference_answer())
        script = {"SEED-1-1|tool_assisted": [
            {"type": "tool_call", "tool_name": "calculator", "arguments": {"expression": "2*pi"}},
            {"type": "final", "raw_response": answer},
        ]}
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            execute_temp(manifest(directory, protocols=("tool_assisted",), script=script), directory)
            item = record(directory, "tool_assisted")
            self.assertEqual(item["status"], "completed")
            self.assertEqual(item["score_result"]["tool_call_count"], 1)
            self.assertEqual(item["tool_calls"][0]["tool_name"], "calculator")
            self.assertEqual(item["tool_calls"][0]["status"], "ok")
        script = {"SEED-1-1|closed_book": [
            {"type": "tool_call", "tool_name": "calculator", "arguments": {"expression": "2*pi"}},
        ]}
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            execute_temp(manifest(directory, script=script), directory)
            item = record(directory)
            self.assertEqual(item["status"], "failed")
            self.assertEqual(item["failure_class"], "tool_policy_violation")
            self.assertIsNone(item["score_result"])

    def test_malformed_answer_is_preserved_without_hand_repair(self) -> None:
        script = {"SEED-1-1|closed_book": [{"type": "final", "raw_response": "not JSON"}]}
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            execute_temp(manifest(directory, script=script), directory)
            item = record(directory)
            self.assertEqual(item["raw_response"], "not JSON")
            self.assertIsNone(item["parsed_answer"])
            self.assertEqual(item["failure_class"], "invalid_contract")
            self.assertEqual(item["score_result"]["failure_mode"], "invalid_contract")

    def test_failed_attempts_are_append_only_on_intentional_retry(self) -> None:
        script = {"SEED-1-1|closed_book": [{"type": "tool_call", "tool_name": "shell", "arguments": {}}]}
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            _, input_path = execute_temp(manifest(directory, script=script), directory)
            first_path = directory / "offline-test-001/results/SEED-1-1__closed_book.json"
            first_bytes = first_path.read_bytes()
            self.assertEqual(run_manifest(input_path)["skipped"], 1)
            self.assertEqual(run_manifest(input_path, retry_failed=True)["failed"], 1)
            second_path = directory / "offline-test-001/results/SEED-1-1__closed_book.attempt2.json"
            self.assertTrue(second_path.exists())
            self.assertEqual(first_path.read_bytes(), first_bytes)

    def test_bounded_tools_and_dated_cost(self) -> None:
        result, event = observed_call(1, "unit_convert", {"value": 180, "from_unit": "deg", "to_unit": "rad"})
        self.assertAlmostEqual(result["value"], 3.141592653589793)
        self.assertEqual(event["status"], "ok")
        with self.assertRaises(ToolCallError):
            execute_tool("calculator", {"expression": "__import__('os').system('dir')"})
        snapshot = {"currency": "USD", "provider": "example", "model_id": "m1",
                    "pricing_reference": "example-snapshot-v1", "pricing_snapshot_utc": "2026-09-28T00:00:00Z",
                    "rates_per_million": {"input": 1.0, "output": 2.0, "cached_input": 0.5}}
        usage = {"input": 1000, "output": 100, "cached_input": 200, "reasoning": 50, "total": 1100}
        self.assertAlmostEqual(_cost(snapshot, usage)["amount"], 0.0011)
        self.assertIsNone(_cost(None, usage))

    def test_codex_event_log_redacts_text_and_public_prompt_excludes_gold(self) -> None:
        case = load_scored_case("SEED-1-7")
        payload = public_payload(case)
        request = {"system_prompt": "Return JSON.", "scientific_payload": payload,
                   "allowed_tools": [], "retrieved_items": [], "tool_exchanges": [], "correction": None}
        prompt = _codex_prompt(request)
        self.assertNotIn('"gold"', prompt)
        self.assertIn("Boolean linear_rotation_rule_applies.", prompt)
        self.assertNotIn("linear_rotation_rule_applies: false", prompt)
        event = _safe_codex_event({"type": "item.completed",
                                   "item": {"id": "item_1", "type": "command_execution",
                                            "command": "secret-token-123", "output": "secret-token-123"}})
        self.assertNotIn("secret-token-123", json.dumps(event))
        self.assertEqual(event["item"]["type"], "command_execution")


if __name__ == "__main__":
    unittest.main()
