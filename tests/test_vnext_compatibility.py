"""The vNext answer vocabulary cannot rewrite rc1 evidence or interpretation."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator

from tools import scoring_runtime as rc1
from tools.vnext import scoring_runtime as vnext


ROOT = Path(__file__).resolve().parents[1]
FROZEN_ASSETS = {
    "benchmark/releases/0.1.0-rc1.json": "2a7f04298dbe27db549ab5307e9cd4e314a8a4e4e83aa503206410c993867516",
    "runs/2026-09-28-gpt-6-luna-verified-release/manifest.json": "e2e3cc6a9559a07a7626158b7bd9f94afb171aa3c4a388a2efbbd16ccac9b11b",
    "runs/2026-09-28-gpt-6-luna-verified-release/summary.json": "bf7f182b0d96d35397288ddbf56f8dd6cb2099c96cf1513071e599795b4ed74e",
}
FROZEN_RUN_DIRS = (
    "2026-09-28-gpt-6-luna-verified-release",
    "2026-09-28-gpt-6-luna-development-release",
    "2026-09-28-gpt-6-luna-variants-release",
)
FROZEN_RUN_FILE_COUNT = 71
FROZEN_RUN_TREE_SHA256 = "3783bcd6a621709ce46558cd3f8f24dd265b41d06ad9741b6f2ba6e0efc21101"


class VNextCompatibilityTests(unittest.TestCase):
    def test_public_hidden_attestation_contains_only_commitments_and_counts(self) -> None:
        attestation = json.loads((ROOT / "benchmark/hidden_eval/attestations/first_private_dry_run.v1.json").read_text())
        commitment = attestation["commitment"]
        schema = json.loads((ROOT / "benchmark/hidden_eval/commitment.v1.schema.json").read_text())
        self.assertFalse(list(Draft202012Validator(schema).iter_errors(commitment)))
        self.assertEqual((commitment["benchmark_release_id"], commitment["concept_family_count"],
                          commitment["instance_count"]), ("0.2.0-rc1", 4, 8))
        self.assertEqual((attestation["completed_instances"], attestation["linked_result_records"]), (8, 8))
        self.assertIsNone(attestation["model_identity"])
        self.assertFalse(attestation["raw_hidden_instances_published"])
        self.assertFalse({"seed", "task", "answer", "raw_response", "parent_case_id"} & set(commitment))
        real = json.loads((ROOT / "benchmark/hidden_eval/attestations/first_real_smoke.v1.json").read_text())
        self.assertEqual(real["commitment"], commitment)
        self.assertEqual((real["selected_instances"], real["linked_result_records"]), (1, 1))
        self.assertEqual(real["aggregate_score"], 1)
        self.assertFalse(real["raw_model_responses_published"])
        self.assertFalse({"seed", "task", "answer", "raw_response", "parent_case_id"} & set(real))

    def test_rc1_artifact_bytes_are_frozen(self) -> None:
        for relative, expected in FROZEN_ASSETS.items():
            with self.subTest(relative=relative):
                self.assertEqual(hashlib.sha256((ROOT / relative).read_bytes()).hexdigest(), expected)

    def test_all_frozen_run_file_bytes_are_unchanged(self) -> None:
        paths = sorted(path for name in FROZEN_RUN_DIRS
                       for path in (ROOT / "runs" / name).rglob("*") if path.is_file())
        self.assertEqual(len(paths), FROZEN_RUN_FILE_COUNT)
        digest = hashlib.sha256()
        for path in paths:
            digest.update(path.relative_to(ROOT).as_posix().encode() + b"\0")
            digest.update(path.read_bytes())
        self.assertEqual(digest.hexdigest(), FROZEN_RUN_TREE_SHA256)

    def test_equivalent_dimensionless_claim_is_vnext_only(self) -> None:
        fixture = json.loads((ROOT / "benchmark/fixtures/SEED-2-2/positive_reference.json").read_text())
        answer = deepcopy(fixture["answer"])
        answer["answers"]["q1"]["expansion_factor"]["unit"] = "dimensionless"
        old = rc1.evaluate_case(rc1.load_scored_case("SEED-2-2"), answer)
        new = vnext.evaluate_case(vnext.load_scored_case("SEED-2-2"), answer)
        self.assertLess(old["scores"]["capped_total"], 1)
        self.assertEqual(new["scores"]["capped_total"], 1)
        self.assertEqual(old["evaluator_version"], "0.1.1")
        self.assertEqual(new["evaluator_version"], "0.2.0")
        self.assertEqual(answer["answers"]["q1"]["expansion_factor"]["unit"], "dimensionless")


if __name__ == "__main__":
    unittest.main()
