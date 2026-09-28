"""New-family variant physics, release pins, and runner dispatch."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from tools.baseline.runner import run_manifest
from tools.variants_vnext import SUPPORTED, _expected_answer, generate_variant, load_variant, validate_variant
from tools.vnext.protocols import public_payload


class VNextVariantsTests(unittest.TestCase):
    def test_four_disjoint_families_reconstruct_and_score(self) -> None:
        for source in SUPPORTED:
            for kind in ("parameter", "structural_unit"):
                with self.subTest(source=source, kind=kind):
                    record = generate_variant(source, "0123456789abcdef0123456789abcdef", kind)
                    self.assertNotIn("gold", record)
                    self.assertNotIn("public_seed", record)
                    case = validate_variant(record)
                    self.assertEqual(case["case_id"], source)
                    self.assertEqual(record["parent_release"], "0.2.0-rc1")
                    exposed = public_payload(case)
                    self.assertNotIn("gold", exposed)
                    self.assertNotIn("reference", json.dumps(exposed).lower())

    def test_tampered_scientific_payload_is_rejected(self) -> None:
        record = generate_variant("SEED-3-7", "0123456789abcdef0123456789abcdef", "parameter")
        changed = deepcopy(record)
        changed["task"]["givens"][0]["value"] = 999
        with self.assertRaises(ValueError):
            validate_variant(changed)

    def test_thin_lens_structural_variant_changes_coordinate_task(self) -> None:
        seed = "0123456789abcdef0123456789abcdef"
        parameter = generate_variant("SEED-3-1", seed, "parameter")
        structural = generate_variant("SEED-3-1", seed, "structural_unit")
        self.assertNotIn("coordinate_convention", parameter["task"])
        self.assertIn("signed dimensionless ratio", structural["task"]["coordinate_convention"])
        self.assertNotEqual(parameter["task"]["questions"][0]["request"],
                            structural["task"]["questions"][0]["request"])

    def test_private_variant_runs_through_versioned_baseline_dispatch(self) -> None:
        record = generate_variant("SEED-5-5", "0123456789abcdef0123456789abcdef", "parameter")
        with tempfile.TemporaryDirectory(prefix="optics-vnext-run-") as temporary:
            folder = Path(temporary)
            variant_path = folder / (record["variant_id"] + ".json")
            variant_path.write_text(json.dumps(record), encoding="utf-8")
            case = load_variant(variant_path)["case"]
            key = "SEED-5-5--" + record["variant_id"] + "|closed_book"
            run_id = "vnext-private-mock-001"
            manifest = {
                "schema_version": "0.1.0", "run_id": run_id,
                "created_utc": "2026-09-28T00:00:00Z", "execution_class": "dry_run",
                "release_id": "0.2.0-rc1",
                "selections": [{"case_id": "SEED-5-5", "track": "private_variant",
                                "variant_path": str(variant_path)}],
                "protocol_ids": ["closed_book"],
                "agent": {"adapter_type": "mock", "provider": "mock", "model_id": "scripted",
                          "model_version": "1", "framework": "local_mock", "scaffold_id": None,
                          "command": None, "command_prefix": None,
                          "mock_script": {key: [{"type": "final", "raw_response": json.dumps(_expected_answer(case))}]}},
                "runner_version": "0.1.0", "system_prompt_version": "neutral_optics_v1",
                "retrieval_config": {"max_items": 0},
                "tool_config": {"profile_id": "generic_computation_v0.1", "max_calls": 0},
                "retry_policy": {"transport_max_retries": 0,
                                 "malformed_answer_max_retries": 0,
                                 "self_correction_max_retries": 0},
                "timeout_seconds": 120, "concurrency": 1, "seed": None,
                "output_directory": run_id, "pricing_snapshot": None,
            }
            input_path = folder / "input.json"
            input_path.write_text(json.dumps(manifest), encoding="utf-8")
            summary = run_manifest(input_path, output_root=folder)
            self.assertEqual(summary["completed"], 1)
            results = list((folder / run_id / "results").glob("*.json"))
            self.assertEqual(len(results), 1)
            result = json.loads(results[0].read_text())
            self.assertEqual(result["score_result"]["evaluator_version"], "0.2.0")
            self.assertEqual(result["score_result"]["scores"]["capped_total"], 1)


if __name__ == "__main__":
    unittest.main()
