"""Synthetic evidence-chain challenges; no private smoke content is used."""

from __future__ import annotations

import json
from pathlib import Path
import secrets
import tempfile
import unittest

from tools.hidden_attestation import audit_real_attestation, derive_real_attestation
from tools.hidden_eval import FAMILY_MAP, audit_bundle, generate_bundle


class HiddenAttestationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        mapping = json.loads(FAMILY_MAP.read_text(encoding="utf-8"))
        mapping["cases"]["SEED-1-1"]["hidden_variant_eligible"] = True
        mapping["cases"]["SEED-1-1"]["generator_template"] = "synthetic/mirror"
        self.family_map = self.base / "family-map.json"
        self._save(self.family_map, mapping)
        self.public_plan = self.base / "public-plan.json"
        self._save(self.public_plan, {"generator_version": "0.1.0", "variants": [
            {"parent_case_id": "SEED-1-5", "variant_type": "parameter", "seed": "synthetic"}]})
        policy = {"schema_version": "1.0.0", "release_id": "0.1.0-rc1",
                  "generator_version": "0.1.0", "seed": secrets.token_hex(32),
                  "family_count": 1, "selections": [
                      {"parent_case_id": "SEED-1-1", "variant_type": "parameter"}]}
        policy_path = self.base / "private-policy.json"
        self._save(policy_path, policy)
        self.bundle = self.base / "bundle"
        generate_bundle(policy_path, self.bundle, family_map=self.family_map,
                        public_plan=self.public_plan)
        instance_path = next((self.bundle / "instances").glob("*.json"))
        instance = json.loads(instance_path.read_text(encoding="utf-8"))
        self.run = self.base / "run"
        (self.run / "results").mkdir(parents=True)
        (self.run / "logs").mkdir()
        self.manifest_path = self.run / "manifest.json"
        self._save(self.manifest_path, {
            "run_id": "synthetic-real", "release_id": "0.1.0-rc1",
            "execution_class": "real", "protocol_ids": ["closed_book"],
            "agent": {"adapter_type": "synthetic", "model_id": "test-model",
                      "model_version": None},
            "selections": [{"case_id": instance["parent_case_id"],
                            "track": "private_variant", "variant_path": str(instance_path)}]})
        self.result_path = self.run / "results" / "first.json"
        self._save(self.result_path, {
            "run_id": "synthetic-real", "execution_class": "real", "status": "completed",
            "agent_identity": {"adapter_type": "synthetic", "model_id": "test-model",
                               "model_version": None},
            "selection": {"case_id": instance["parent_case_id"],
                          "track": "private_variant", "variant_id": instance["variant_id"],
                          "case_content_sha256": instance["instance_content_sha256"],
                          "variant_lineage": {"generator_version": instance["generator_version"],
                                              "instance_content_sha256": instance["instance_content_sha256"]}},
            "protocol": {"id": "closed_book",
                         "scientific_payload_sha256": instance["scientific_payload_sha256"]},
            "score_result": {"evaluator_fingerprint": instance["scorer"]["evaluator_fingerprint"],
                             "scores": {"capped_total": 0.75}, "failure_mode": "none"},
            "usage": {"cached_input": 2, "input": 10, "output": 3,
                      "reasoning": 1, "total": 13}, "cost": None})
        (self.run / "logs" / "first.jsonl").write_bytes(b'{"event":"synthetic"}\n')
        self.attestation_path = self.base / "public-attestation.json"
        self.kwargs = {"family_map": self.family_map, "public_plan": self.public_plan}
        self.attestation = derive_real_attestation(self.bundle, self.run, **self.kwargs)
        self._save(self.attestation_path, self.attestation)

    @staticmethod
    def _save(path: Path, value: dict) -> None:
        path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True), encoding="utf-8")

    def _audit(self) -> dict:
        return audit_real_attestation(self.bundle, self.run, self.attestation_path, **self.kwargs)

    def test_derived_claims_and_independent_bundle_audit(self) -> None:
        self.assertTrue(self._audit()["verified"])
        self.assertEqual(self.attestation["aggregate_score"], 0.75)
        self.assertEqual(self.attestation["tokens"]["total"], 13)
        self.assertEqual(self.attestation["run_evidence"]["file_count"], 3)
        self.assertNotIn("synthetic-real", json.dumps(self.attestation["commitment"]))
        self.assertEqual(audit_bundle(self.bundle, **self.kwargs), self.attestation["commitment"])

    def test_changed_score_or_usage_fails_audit(self) -> None:
        result = json.loads(self.result_path.read_text(encoding="utf-8"))
        result["score_result"]["scores"]["capped_total"] = 0.5
        self._save(self.result_path, result)
        with self.assertRaisesRegex(ValueError, "public attestation differs"):
            self._audit()
        result["score_result"]["scores"]["capped_total"] = 0.75
        result["usage"]["total"] = 14
        self._save(self.result_path, result)
        with self.assertRaisesRegex(ValueError, "public attestation differs"):
            self._audit()

    def test_changed_manifest_or_log_byte_fails_audit(self) -> None:
        manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        manifest["timeout_seconds"] = 121
        self._save(self.manifest_path, manifest)
        with self.assertRaisesRegex(ValueError, "public attestation differs"):
            self._audit()
        del manifest["timeout_seconds"]
        self._save(self.manifest_path, manifest)
        (self.run / "logs" / "first.jsonl").write_bytes(b'{"event":"tampered"}\n')
        with self.assertRaisesRegex(ValueError, "public attestation differs"):
            self._audit()
        self.assertEqual(audit_bundle(self.bundle, **self.kwargs), self.attestation["commitment"])

    def test_changed_public_attestation_fails_audit(self) -> None:
        altered = dict(self.attestation)
        altered["aggregate_score"] = 1.0
        self._save(self.attestation_path, altered)
        with self.assertRaisesRegex(ValueError, "public attestation differs"):
            self._audit()


if __name__ == "__main__":
    unittest.main()
