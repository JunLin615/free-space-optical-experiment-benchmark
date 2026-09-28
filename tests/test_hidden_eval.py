"""Synthetic, secret-free tests of the hidden policy and private bundle path."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import secrets
import tempfile
import unittest

from tools.hidden_eval import (FAMILY_MAP, ROOT, audit_bundle, audit_result_linkage, check_disjoint,
                               contamination_findings, dry_run_bundle, generate_bundle, validate_family_map,
                               validate_policy)
from tools.variants import generate_variant


class HiddenEvaluationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.mapping = json.loads(FAMILY_MAP.read_text(encoding="utf-8"))
        row = self.mapping["cases"]["SEED-1-1"]
        row["hidden_variant_eligible"] = True
        row["generator_template"] = "synthetic/mirror"
        self.map_path = self.base / "map.json"
        self._save(self.map_path, self.mapping)
        self.plan_path = self.base / "public-plan.json"
        self._plan("SEED-1-5")
        self.policy = {"schema_version": "1.0.0", "release_id": "0.1.0-rc1",
                       "generator_version": "0.1.0", "seed": secrets.token_hex(32),
                       "family_count": 1, "selections": [
                           {"parent_case_id": "SEED-1-1", "variant_type": "parameter"}]}

    @staticmethod
    def _save(path: Path, value: dict) -> None:
        path.write_text(json.dumps(value), encoding="utf-8")

    def _plan(self, source: str) -> None:
        self._save(self.plan_path, {"generator_version": "0.1.0",
                                    "variants": [{"parent_case_id": source,
                                                  "variant_type": "parameter", "seed": "synthetic"}]})

    def test_public_map_covers_cases_and_fails_closed(self) -> None:
        mapping = validate_family_map()
        self.assertEqual(len(mapping["cases"]), 64)
        public_families = {mapping["cases"][source]["concept_family"]
                           for source in ("SEED-1-1", "SEED-1-5", "SEED-1-7", "SEED-2-2", "SEED-4-2")}
        self.assertFalse(any(row["hidden_variant_eligible"] and
                             row["concept_family"] in public_families
                             for row in mapping["cases"].values()))
        with self.assertRaises(ValueError):
            check_disjoint(self.policy, family_map=mapping, public_plan=self.plan_path)

    def test_rejects_same_parent_and_same_family(self) -> None:
        self._plan("SEED-1-1")
        with self.assertRaisesRegex(ValueError, "same parent"):
            validate_policy(self.policy, family_map=self.map_path, public_plan=self.plan_path)
        # A distinct public parent with the same family is still excluded.
        altered = copy.deepcopy(self.mapping)
        altered["cases"]["SEED-1-3"]["concept_family"] = "mirror_steering"
        self._save(self.map_path, altered)
        self._plan("SEED-1-3")
        with self.assertRaisesRegex(ValueError, "concept-family overlap"):
            validate_policy(self.policy, family_map=self.map_path, public_plan=self.plan_path)

    def test_rejects_template_duplicate_and_stale_lineage(self) -> None:
        altered = copy.deepcopy(self.mapping)
        altered["cases"]["SEED-1-5"]["generator_template"] = "synthetic/mirror"
        self._save(self.map_path, altered)
        with self.assertRaisesRegex(ValueError, "generator-template overlap"):
            validate_policy(self.policy, family_map=self.map_path, public_plan=self.plan_path)
        self._save(self.map_path, self.mapping)
        duplicate = copy.deepcopy(self.policy)
        duplicate["selections"].append(duplicate["selections"][0])
        with self.assertRaisesRegex(ValueError, "duplicate hidden"):
            validate_policy(duplicate, family_map=self.map_path, public_plan=self.plan_path)
        stale = copy.deepcopy(self.policy)
        stale["release_id"] = "0.2.0-rc1"
        with self.assertRaises(ValueError):
            validate_policy(stale, family_map=self.map_path, public_plan=self.plan_path)

    def test_indexed_instances_are_distinct_and_reproducible(self) -> None:
        indexed = copy.deepcopy(self.policy)
        indexed["seed"] = "ab" * 32
        indexed["selections"][0]["instance_index"] = 0
        indexed["selections"].append({"parent_case_id": "SEED-1-1",
                                      "variant_type": "parameter", "instance_index": 1})
        validate_policy(indexed, family_map=self.map_path, public_plan=self.plan_path)
        policy_path = self.base / "indexed-policy.json"
        self._save(policy_path, indexed)
        bundle_path = self.base / "indexed-bundle"
        commitment = generate_bundle(policy_path, bundle_path, family_map=self.map_path,
                                     public_plan=self.plan_path)
        self.assertEqual(commitment["instance_count"], 2)
        self.assertEqual(audit_bundle(bundle_path, family_map=self.map_path,
                                      public_plan=self.plan_path), commitment)
        indexed["selections"][1]["instance_index"] = 0
        with self.assertRaisesRegex(ValueError, "duplicate hidden"):
            validate_policy(indexed, family_map=self.map_path, public_plan=self.plan_path)

    def test_external_bundle_commitment_audit_and_mock_adapter(self) -> None:
        policy_path = self.base / "private-policy.json"
        self._save(policy_path, self.policy)
        bundle_path = self.base / "bundle"
        commitment = generate_bundle(policy_path, bundle_path, family_map=self.map_path,
                                     public_plan=self.plan_path)
        self.assertEqual(commitment["instance_count"], 1)
        self.assertEqual(commitment["concept_family_count"], 1)
        self.assertNotIn(self.policy["seed"], json.dumps(commitment))
        self.assertNotIn("task", json.dumps(commitment))
        self.assertEqual(audit_bundle(bundle_path, family_map=self.map_path,
                                      public_plan=self.plan_path), commitment)
        dry = dry_run_bundle(bundle_path, family_map=self.map_path,
                             public_plan=self.plan_path)
        self.assertEqual(dry["counts"], {"completed": 1, "failed": 0})
        self.assertEqual(dry["execution_class"], "dry_run")
        with self.assertRaises(FileExistsError):
            generate_bundle(policy_path, bundle_path, family_map=self.map_path,
                            public_plan=self.plan_path)
        record_path = next((bundle_path / "instances").glob("*.json"))
        record = json.loads(record_path.read_text(encoding="utf-8"))
        record["task"]["statement"] += " tampered"
        self._save(record_path, record)
        with self.assertRaisesRegex(ValueError, "seed reproduction"):
            audit_bundle(bundle_path, family_map=self.map_path, public_plan=self.plan_path)

    def test_private_paths_cannot_point_into_checkout(self) -> None:
        outside = self.base / "policy.json"
        self._save(outside, self.policy)
        with self.assertRaisesRegex(ValueError, "outside the repository"):
            generate_bundle(outside, ROOT / "benchmark" / "hidden_eval" / "private-test",
                            family_map=self.map_path, public_plan=self.plan_path)

    def test_private_result_linkage(self) -> None:
        policy_path = self.base / "private-policy.json"
        self._save(policy_path, self.policy)
        bundle_path = self.base / "bundle"
        generate_bundle(policy_path, bundle_path, family_map=self.map_path,
                        public_plan=self.plan_path)
        instance_path = next((bundle_path / "instances").glob("*.json"))
        instance = json.loads(instance_path.read_text(encoding="utf-8"))
        run_path = self.base / "run"
        (run_path / "results").mkdir(parents=True)
        self._save(run_path / "manifest.json", {
            "run_id": "synthetic-private", "release_id": "0.1.0-rc1",
            "selections": [{"case_id": instance["parent_case_id"],
                            "track": "private_variant", "variant_path": str(instance_path)}]})
        result_path = run_path / "results" / "first.json"
        record = {"selection": {"case_id": instance["parent_case_id"],
                                "track": "private_variant", "variant_id": instance["variant_id"],
                                "case_content_sha256": instance["instance_content_sha256"],
                                "variant_lineage": {"generator_version": instance["generator_version"],
                                                    "instance_content_sha256": instance["instance_content_sha256"]}},
                  "protocol": {"scientific_payload_sha256": instance["scientific_payload_sha256"]},
                  "score_result": {"evaluator_fingerprint": instance["scorer"]["evaluator_fingerprint"]}}
        self._save(result_path, record)
        linked = audit_result_linkage(bundle_path, run_path, family_map=self.map_path,
                                      public_plan=self.plan_path)
        self.assertEqual(linked["linked_result_records"], 1)
        record["protocol"]["scientific_payload_sha256"] = "0" * 64
        self._save(result_path, record)
        with self.assertRaisesRegex(ValueError, "scientific payload"):
            audit_result_linkage(bundle_path, run_path, family_map=self.map_path,
                                 public_plan=self.plan_path)

    def test_exact_and_parameter_sibling_screens(self) -> None:
        public = generate_variant("SEED-1-1", "synthetic", "parameter")
        self._plan("SEED-1-1")
        private_copy = copy.deepcopy(public)
        private_copy["seed_classification"] = "private"
        private_copy.pop("public_seed")
        findings = contamination_findings([private_copy], self.plan_path)
        self.assertTrue(any("exact scientific payload" in item for item in findings))
        self.assertTrue(any("normalized task structure" in item for item in findings))
        self.assertTrue(any("typed parameter tuple" in item for item in findings))


if __name__ == "__main__":
    unittest.main()
